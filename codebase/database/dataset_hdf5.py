import importlib
import json
import logging
import os
from sys import maxsize
import time
import uuid
import functools

from dataclasses import dataclass
from queue import Queue
from threading import Thread

from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Dict,
    List,
    Mapping,
    Optional,
    Sequence,
    Set,
    Sized,
    Tuple,
    Union,
)

import numpy
import pandas as pd
import h5py

import qcodes
from qcodes.dataset.descriptions.dependencies import InterDependencies_
from qcodes.dataset.descriptions.param_spec import ParamSpec, ParamSpecBase
from qcodes.dataset.descriptions.rundescriber import RunDescriber
from qcodes.dataset.descriptions.versioning.converters import new_to_old, old_to_new
from qcodes.dataset.descriptions.versioning.rundescribertypes import Shapes
from qcodes.dataset.descriptions.versioning.v0 import InterDependencies
from qcodes.dataset.guids import filter_guids_by_parts, generate_guid, parse_guid
from qcodes.dataset.linked_datasets.links import Link, links_to_str, str_to_links
from qcodes.dataset.data_set_cache import DataSetCache

from qcodes.instrument.parameter import _BaseParameter


from .exporters.export_to_pandas import (
    load_to_dataframe_dict,
    load_to_concatenated_dataframe,
)
from .exporters.export_to_xarray import (
    load_to_xarray_dataset,
    load_to_xarray_dataarray_dict,
)

from .exporters.export_config import (
    DataExportType,
    get_data_export_type,
    get_data_export_path,
    get_data_export_prefix,
    get_data_export_automatic,
)

from qcodes.dataset.descriptions.versioning import serialization as serial

from .hdf5_helper import *

if TYPE_CHECKING:
    import pandas as pd
    import xarray as xr

log = logging.getLogger(__name__)

##################################################################
# Data types
##################################################################
Datatype_set = (
    complex,
    int,
    float,
    numpy.integer,
    numpy.floating,
    numpy.complexfloating,
    bool,
    str,
)
Array_like_types = Union[tuple, list, numpy.ndarray]
Scalar_types = Union[
    complex, int, float, numpy.integer, numpy.floating, numpy.complexfloating
]
Data_types = Union[Scalar_types, bool, str]

Value_types = Union[Data_types, Sequence[Data_types], numpy.ndarray]
Values_type = List[Value_types]
Values_dict_type = Dict[str, Value_types]

Result_type = Tuple[Union[_BaseParameter, str], Value_types]
Setpoint_type = Sequence[Union[str, _BaseParameter]]
Hdf5_file_type = Union[h5py.File]
Hdf5_group_type = Union[h5py.Group]
Hdf5_fileorgroup_types = Union[h5py.File, h5py.Group]
Hdf5_dataset_type = Union[h5py.Dataset]
Hdf5_groupordataset_types = Union[h5py.Dataset, h5py.Group]

Attribute_types = Union[List[str], Tuple[str], str]
# According to the comment in qcodes, they will deprecate SPECS_TYPE and finally remove
# the "ParamSpec" class.
Specs_types = List[ParamSpec]
SpecsOrInterDeps = Union[Specs_types, InterDependencies_]
ParameterData = Dict[str, Dict[str, numpy.ndarray]]
##################################################################
# background writer
##################################################################


class _BackgroundWriter(Thread):
    """
    Write the results from the DataSet's data queue in a new thread
    """

    def __init__(self, queue: Queue, conn: Connection, run_group_path: str):
        super().__init__(daemon=True)

        self.queue = queue
        self.run_group_path = run_group_path
        self.keep_writing = True
        self.conn = conn

    def run(self) -> None:

        # check if keep writing
        while self.keep_writing:

            # the content of the queue has three properties
            # 1. 'keys': 'stop' or 'finalize' or a list of keys
            # 2. 'values': a list of data corresponding to the list of keys
            # 3.
            item = self.queue.get()
            if item["keys"] == "stop":
                self.keep_writing = False
                self.conn.flush()

            elif item["keys"] == "finalize":
                _WriterStatus_dict[self.run_group_path].active_datasets.remove(
                    item["values"]
                )
            else:
                self.write_results(item["keys"], item["values"], item["ds_group_name"])
            self.queue.task_done()

    def write_results(
        self, keys: Sequence[str], values: Sequence[Any], ds_group_name: str = "data"
    ) -> None:

        database = self.conn
        run_group = database[self.run_group_path]
        dataset_group = run_group.require_group(ds_group_name)

        # key is the dataset name under the dataset_group
        for index, (key, value) in enumerate(zip(list(keys), values)):
            if key in dataset_group.keys():
                if isinstance(dataset_group[key], Hdf5_dataset_type):
                    data = value[index]
                    if isinstance(data, Datatype_set):
                        data = numpy.array([data])
                    elif isinstance(data, list):
                        data = numpy.array(data)

                    if isinstance(data, numpy.ndarray):
                        dataset = dataset_group[key]

                        dataset.resize(dataset.shape[0] + data.shape[0], axis=0)
                        dataset[-data.shape[0] :] = data
                    else:
                        raise ValueError(
                            "The data is not numpy.ndarray and cannot be converted to be this type."
                        )
                else:
                    raise TypeError("The write position is not a hdf5 dataset")
            else:
                data = value[index]
                if isinstance(data, Datatype_set):
                    data = numpy.array([data])
                elif isinstance(data, list):
                    data = numpy.array(data)

                if isinstance(data, numpy.ndarray):
                    tuple_shape = data.shape
                    list_shape = list(tuple_shape)
                    list_shape.insert(0, 1)
                    new_shape = tuple(list_shape)
                    data.reshape(new_shape)
                    list_shape[0] = None
                    maxshape = tuple(list_shape)
                    dataset_group.create_dataset(
                        name=key, data=data, maxshape=maxshape, chunks=True
                    )
                else:
                    raise ValueError(
                        "The data is not numpy.ndarray and cannot be converted to be this type."
                    )

    def shutdown(self) -> None:
        """
        Send a termination signal to the data writing queue, wait for the
        queue to empty and the thread to join.

        If the background writing thread is not alive this will do nothing.
        """
        if self.is_alive():
            self.queue.put({"keys": "stop", "values": []})
            self.queue.join()
            self.join()


@dataclass
class _WriterStatus:
    bg_writer: Optional[_BackgroundWriter]
    write_in_background: Optional[bool]
    data_write_queue: Queue
    active_datasets: Set[int]


_WriterStatus_dict: Dict[str, _WriterStatus] = {}

##################################################################
# Exception
##################################################################
class CompletedError(RuntimeError):
    pass


class DataLengthException(Exception):
    pass


class DataPathException(Exception):
    pass


##################################################################
# Exception
##################################################################
def create_run(
    exp_group: Optional[Hdf5_group_type] = None,
    run_name: Optional[str] = None,
    dataset_name: Optional[str] = None,
    metadata: Optional[Mapping[str, Any]] = None,
    captured_run_id: Optional[int] = None,
    captured_counter: Optional[int] = None,
    parent_dataset_links: str = "[]",
    exp_id: Optional[int] = None,
    sample_name: Optional[str] = None,
    exp_name: Optional[str] = None,
    values: Optional[Values_type] = None,
    snapshot: Optional[str] = None,
) -> h5py.Group:

    run_info_dict = {}

    run_id = len(exp_group.keys()) + 1
    run_name = run_name or "run"
    run_group_name = run_name + "#" + str(run_id)

    create_timestamp_raw = time.time()
    run_info_dict["create_timestamp_raw"] = create_timestamp_raw

    run_info_dict["guid"] = generate_guid()

    run_info_dict["run_id"] = run_id
    run_info_dict["run_name"] = run_name
    run_info_dict["exp_id"] = exp_id
    run_info_dict["exp_name"] = exp_name
    run_info_dict["sample_name"] = sample_name

    if metadata is None:
        metadata = {}
        metadata_string = json.dumps(metadata)
    else:
        if isinstance(metadata, dict):
            metadata_string = json.dumps(metadata)
        elif isinstance(metadata, str):
            metadata_string = metadata
        else:
            raise TypeError("The type of metadata is not supported")
    run_info_dict["metadata"] = metadata_string

    run_info_dict["snapshot"] = snapshot or ""

    run_info_dict["captured_run_id"] = captured_run_id
    run_info_dict["captured_counter"] = captured_counter
    run_info_dict["parent_dataset_links"] = parent_dataset_links

    run_group = exp_group.create_group(run_group_name)
    write_dict_to_hdf5(run_info_dict, run_group)

    dataset_name = "data" or dataset_name
    run_group.require_group(dataset_name)

    return run_group


def get_attrs(
    entry_point: Hdf5_groupordataset_types,
    attributes: Optional[Attribute_types] = None,
) -> None:

    attrs_dict = {}
    required_attrs = []
    if attributes is not None:
        if isinstance(attributes, str):
            required_attrs = [attributes]
        elif isinstance(attributes, tuple):
            required_attrs = list(attributes)
        elif isinstance(attributes, list):
            required_attrs = attributes
    else:
        required_attrs = entry_point.attrs.keys()

    attrs_list = entry_point.attrs.keys()
    if len(attrs_list) == 0:
        raise ValueError(
            r"There is no attributes under this group or dataset {}".format(
                entry_point.name
            )
        )
    else:
        for _, item in enumerate(required_attrs):
            if item in attrs_list:
                value = entry_point.attrs[item]
                if value == "NoneType:__None__":
                    attrs_dict[item] = None
                else:
                    attrs_dict = value
            else:
                attrs_dict[item] = None
    return attrs_dict


def get_single_attr(
    entry_point: Hdf5_groupordataset_types,
    attribute: str,
) -> None:

    attrs_list = entry_point.attrs.keys()
    if len(attrs_list) == 0:
        raise ValueError(
            r"There is no attributes under this group or dataset {}".format(
                entry_point.name
            )
        )
    else:
        if attribute in attrs_list:
            value = entry_point.attrs[attribute]
            if value == "NoneType:__None__":
                return None
            else:
                return value
        else:
            return None


##################################################################
##################################################################
# Dataset
class HDF5DataSet:
    persistent_traits = (
        "name",
        "guid",
        "number_of_results",
        "parameters",
        "paramspecs",
        "exp_name",
        "sample_name",
        "completed",
        "snapshot",
        "run_timestamp_raw",
        "description",
        "completed_timestamp_raw",
        "metadata",
        "dependent_parameters",
        "parent_dataset_links",
        "captured_run_id",
        "captured_counter",
    )
    background_sleep_time = 1e-3

    def __init__(
        self,
        database_path: Optional[str] = None,
        name: Optional[str] = None,
        is_new_exp: bool = False,
        run_id: Optional[int] = None,
        exp_name: Optional[str] = None,
        sample_name: Optional[str] = None,
        exp_id: Optional[int] = None,
        conn: Optional[Hdf5_file_type] = None,
        run_name: Optional[str] = None,
        values: Optional[Values_type] = None,
        specs: Optional[SpecsOrInterDeps] = None,
        metadata: Optional[Mapping[str, Any]] = None,
        shapes: Optional[Shapes] = None,
        in_memory_cache: bool = True,
    ) -> None:

        # result
        self._results: List[Dict[str, Value_types]] = []

        # database name
        sample_name = sample_name or "test_sample"
        self.database_name = (sample_name + "_database") or name

        # dataset name
        self.dataset_name = "data"

        # database
        self._database_path = database_path
        if database_path is not None:
            if conn is None:
                self.conn = DatabaseFile(self.database_name, self._database_path)
            elif conn == DatabaseFile(self.database_name, self._database_path):
                self.conn = conn
        elif conn is not None:
            self.conn = conn
        else:
            raise ValueError("No provide the database path or database connection")

        # debug mode
        self._debug = False

        # links
        self._parent_dataset_links: List[Link]

        # subscribers that update the dataset
        self.subscribers: Dict[str, _Subscriber] = {}

        # in-memory cache
        self.cache: DataSetCache = DataSetCache(self)
        self._in_memory_cache = in_memory_cache
        self._export_path: Optional[str] = None

        # experim ent group
        if exp_name is None or sample_name is None:
            raise ValueError("exp_name and sample_name are not given.")
        else:
            self.exp_name = exp_name

            self.sample_name = sample_name

            if exp_id is None and is_new_exp:
                last_id = len(self.conn.keys())
                self.exp_id = last_id + 1
                self.exp_group_name = (
                    self.exp_name + "#" + self.sample_name + "#" + str(self.exp_id)
                )
                self.exp_group = self.conn.create_group(self.exp_group_name)

            elif exp_id is None and (not is_new_exp):
                prefix = self.exp_name + "#" + self.sample_name + "#"
                same_exp_sample_list = []
                id_list = []
                for key in self.conn.keys():
                    if key.startswith(prefix):
                        same_exp_sample_list.append(key)
                        id_list.append(int(key.replace(prefix, "")))
                if same_exp_sample_list and id_list:
                    max_id = max(id_list)
                    self.exp_group_name = (
                        self.exp_name + "#" + self.sample_name + "#" + str(max_id)
                    )
                    self.exp_group = self.conn.require_group(self.exp_group_name)
                else:
                    raise ValueError(
                        "The exp group does not exist in the database. "
                        'Please set "is_new_exp = True"'
                    )

            elif exp_id is not None and is_new_exp:

                prefix = self.exp_name + "#" + self.sample_name + "#"
                same_exp_sample_list = []
                id_list = []
                last_id = len(self.conn.keys())
                for key in self.conn.keys():
                    if key.startswith(prefix):
                        same_exp_sample_list.append(key)
                        id_list.append(int(key.replace(prefix, "")))

                if exp_id in id_list:
                    raise ValueError(
                        "The given exp_id exists in the exp group. "
                        "Cannot create new exp group with exp_id, please assign"
                        '"is_new_exp = False". '
                    )
                elif exp_id == last_id + 1:
                    self.exp_id = exp_id
                    self.exp_group_name = (
                        self.exp_name + "#" + self.sample_name + "#" + str(self.exp_id)
                    )
                    self.exp_group = self.conn.create_group(self.exp_group_name)
                else:
                    raise ValueError(
                        "The given exp_id does not follow the last existing id."
                    )

            elif exp_id is not None and (not is_new_exp):
                prefix = self.exp_name + "#" + self.sample_name + "#"
                same_exp_sample_list = []
                id_list = []
                for key in self.conn.keys():
                    if key.startswith(prefix):
                        same_exp_sample_list.append(key)
                        id_list.append(int(key.replace(prefix, "")))
                if exp_id in id_list:
                    self.exp_id = exp_id
                    self.exp_group_name = (
                        self.exp_name + "#" + self.sample_name + "#" + str(self.exp_id)
                    )
                    self.exp_group = self.conn.require_group(self.exp_group_name)
                else:
                    raise ValueError(
                        "The given exp_id does not correspond to an existing"
                        "exp group named by given exp_name and sample name."
                    )
            else:
                raise Exception("Unexpected error.")

        # run group
        self.run_name = run_name or "run"
        last_run_id = len(self.exp_group.keys())

        if run_id is None:
            self.run_id = last_run_id + 1
            self.run_group_name = self.run_name + "#" + str(self.run_id)

            self._metadata = metadata or {}
            self._parent_dataset_links = []

            self.run_group = create_run(
                exp_group=self.exp_group,
                run_name=self.run_name,
                metadata=self.metadata,
                captured_run_id=self.run_id,
                captured_counter=self.run_id,
                exp_id=self.exp_id,
                sample_name=self.sample_name,
                exp_name=self.exp_name,
                dataset_name=self.dataset_name,
                values=values,
            )
            self.run_group_path = self.run_group.name

            # attributes to show the satuts of run
            self._completed = False
            self._started = False
            self._create_timestamp_raw = get_single_attr(
                self.run_group, "create_timestamp_raw"
            )
            self._run_timestamp_raw = None

            # set interndependencies in the run_group
            if isinstance(specs, InterDependencies_):
                self.interdeps = specs
            elif specs is not None:
                self.interdeps = old_to_new(InterDependencies(*specs))
            else:
                self.interdeps = InterDependencies_()

            # store the interdependencies
            self.set_interdependencies(interdeps=self.interdeps, shapes=shapes)

        else:
            self.run_id = run_id
            run_group_name = self.run_name + "#" + str(run_id)

            # load from an existing run group
            if run_group_name in self.exp_group.keys():
                self.run_group = self.exp_group.require_group(run_group_name)

                self._completed = get_single_attr(self.run_group, "completed")

                self._rundescriber = self._get_run_description_from_db()
                self._metadata = self._get_metadata_from_db()

                self._parent_dataset_links = str_to_links(
                    get_single_attr(self.run_group, "parent_dataset_links")
                )
                self._create_timestamp_raw = get_single_attr(
                    self.run_group, "create_timestamp_raw"
                )
                self._run_timestamp_raw = get_single_attr(
                    self.run_group, "run_timestamp_raw"
                )
                self._completed_timestamp_raw = get_single_attr(
                    self.run_group, "completed_timestamp_raw"
                )
                self._started = self.run_timestamp_raw is not None

            # create a new run group
            elif run_id == last_run_id + 1:

                # set interndependencies
                if isinstance(specs, InterDependencies_):
                    self.interdeps = specs
                elif specs is not None:
                    self.interdeps = old_to_new(InterDependencies(*specs))
                else:
                    self.interdeps = InterDependencies_()
                self.set_interdependencies(interdeps=self.interdeps, shapes=shapes)

                self._metadata = metadata or {}
                self._parent_dataset_links = []

                self.run_group = create_run(
                    exp_group=self.exp_group,
                    run_name=self.run_name,
                    metadata=self.metadata,
                    captured_run_id=self.run_id,
                    captured_counter=self.run_id,
                    exp_id=self.exp_id,
                    sample_name=self.sample_name,
                    exp_name=self.exp_name,
                    dataset_name=self.dataset_name,
                    values=values,
                )
                self._completed = False
                self._started = False
                self._create_timestamp_raw = get_single_attr(
                    self.run_group, "create_timestamp_raw"
                )
                self._run_timestamp_raw = None

            else:
                raise ValueError(
                    "run_id is not given as the ever-increasing integer \
                    enumerating the number of the runs"
                )

        # background writer
        if _WriterStatus_dict.get(self.run_group_path) is None:

            queue = Queue()
            ws: _WriterStatus = _WriterStatus(
                bg_writer=None,
                write_in_background=None,
                data_write_queue=queue,
                active_datasets=set(),
            )
            _WriterStatus_dict[self.run_group_path] = ws

    ##################################################################
    # properties
    ##################################################################
    @property
    def path_to_db(self) -> str:
        return self.conn.filename

    @property
    def captured_run_id(self) -> int:
        return get_single_attr(self.run_group, "captured_run_id")

    @property
    def name(self) -> str:
        return self.run_group_name

    @property
    def guid(self) -> str:
        return get_single_attr(self.run_group, "guid")

    @property
    def snapshot(self) -> Optional[Dict[str, Any]]:
        """Snapshot of the run as dictionary (or None)"""
        snapshot_string = self.snapshot_raw
        if snapshot_string:
            return json.loads(snapshot_string)
        else:
            return None

    @property
    def snapshot_raw(self) -> Optional[str]:
        return get_single_attr(self.run_group, "snapshot")

    # TODO: check counter
    @property
    def counter(self) -> int:
        return get_single_attr(self.run_group, "counter")

    # @property
    # def number_of_results(self) -> int:
    #     pass

    @property
    def captured_counter(self) -> int:
        return get_single_attr(self.run_group, "captured_counter")

    @property
    def parameters(self) -> str:
        if self._rundescriber:
            psnames = [ps.name for ps in self._rundescriber.interdeps.paramspecs]
            return ",".join(psnames)

    @property
    def dependent_parameters(self) -> Tuple[ParamSpecBase, ...]:
        """
        Return all the parameters that explicitly depend on other parameters
        """
        return tuple(self._rundescriber.interdeps.dependencies.keys())

    @property
    def paramspecs(self) -> Dict[str, ParamSpec]:
        return {ps.name: ps for ps in self.get_parameters()}

    # @property
    # def exp_id(self) -> int:
    #     return self.exp_id

    # @property
    # def exp_name(self) -> str:
    #     return self.exp_name

    # @property
    # def sample_name(self) -> str:
    #     return self.sample_name

    # @property
    # def run_id(self) -> int:
    #     return self.run_id

    ##################################################################
    # timestamp
    #

    @property
    def create_timestamp(self, fmt: str = "%Y-%m-%d %H:%M:%S") -> Optional[str]:
        if self._create_timestamp_raw:
            return time.strftime(fmt, time.localtime(self._create_timestamp_raw))
        else:
            print("The create timestamp raw is not created.")
            return None

    @property
    def create_timestamp_raw(self) -> Optional[float]:
        if self._create_timestamp_raw:
            return self._create_timestamp_raw
        else:
            print("The create timestamp raw is not created.")
            return None

    @property
    def run_timestamp(self, fmt: str = "%Y-%m-%d %H:%M:%S") -> Optional[str]:
        """
        Returns run timestamp in a human-readable format

        The run timestamp is the moment when the measurement for this run
        started. If the run has not yet been started, this function returns
        None.

        Consult with :func:`time.strftime` for information about the format.
        """
        if self._run_timestamp_raw:
            return time.strftime(fmt, time.localtime(self._run_timestamp_raw))
        else:
            print("The create timestamp raw is not created.")
            return None

    @property
    def run_timestamp_raw(self) -> Optional[float]:
        if self._run_timestamp_raw:
            return self._run_timestamp_raw
        else:
            print("The run timestamp raw is not created.")
            return None

    @property
    def completed_timestamp(self, fmt: str = "%Y-%m-%d %H:%M:%S") -> Optional[str]:
        """
        Returns timestamp when measurement run was completed
        in a human-readable format

        If the run (or the dataset) is not completed, then returns None.

        Consult with ``time.strftime`` for information about the format.
        """
        if self._completed_timestamp_raw:
            time.strftime(fmt, time.localtime(self._completed_timestamp_raw))
        else:
            print("The create timestamp raw is not created.")
            return None

    @property
    def completed_timestamp_raw(self) -> Optional[float]:
        """
        Returns timestamp when measurement run was completed
        as number of seconds since the Epoch

        If the run (or the dataset) is not completed, then returns None.
        """
        if self._completed_timestamp_raw:
            return self._completed_timestamp_raw
        else:
            print("The completed timestamp raw is not created.")
            return None

    @property
    def description(self) -> RunDescriber:
        return self._rundescriber

    @property
    def metadata(self) -> Dict[str, Any]:
        return self._metadata

    @property
    def parent_dataset_links(self) -> List[Link]:
        """
        Return a list of Link objects. Each Link object describes a link from
        this dataset to one of its parent datasets
        """
        return self._parent_dataset_links

    @parent_dataset_links.setter
    def parent_dataset_links(self, links: List[Link]) -> None:
        """
        Assign one or more links to parent datasets to this dataset. It is an
        error to assign links to a non-pristine dataset

        Args:
            links: The links to assign to this dataset
        """
        if not self.pristine:
            raise RuntimeError(
                "Can not set parent dataset links on a dataset "
                "that has been started."
            )

        if not all(isinstance(link, Link) for link in links):
            raise ValueError("Invalid input. Did not receive a list of Links")

        for link in links:
            if link.head != self.guid:
                raise ValueError(
                    "Invalid input. All links must point to this dataset. "
                    "Got link(s) with head(s) pointing to another dataset."
                )

        self._parent_dataset_links = links

    @property
    def _writer_status(self) -> _WriterStatus:
        return _WriterStatus_dict[self.run_group_path]

    def the_same_dataset_as(self, other) -> bool:
        """
        Check if two datasets correspond to the same run by comparing
        all their persistent traits. Note that this method
        does not compare the data itself.

        This function raises if the GUIDs match but anything else doesn't

        Args:
            other: the dataset to compare self to
        """

        if not isinstance(other, HDF5DataSet):
            return False
        else:
            guids_match = self.guid == other.guid

            # note that the guid is in itself a persistent trait of the DataSet.
            # We therefore do not need to handle the case of guids not equal
            # but all persistent traits equal, as this is not possible.
            # Thus, if all persistent traits are the same we can safely return True
            for attr in HDF5DataSet.persistent_traits:
                if getattr(self, attr) != getattr(other, attr):
                    if guids_match:
                        raise RuntimeError(
                            "Critical inconsistency detected! "
                            "The two datasets have the same GUID, "
                            f'but their "{attr}" differ.'
                        )
                    else:
                        return False

            return True

    ##################################################################
    # dataset information printing
    ##################################################################
    def __repr__(self) -> str:
        out = []
        heading = f"{self.exp_name}#{self.sample_name}#{self.exp_id}-{self.run_name}#{self.run_id}@{self.path_to_db}"
        out.append(heading)
        ps = self.get_parameters()
        if len(ps) > 0:
            for p in ps:
                out.append(f"{p.name} - {p.type}")

        return "\n".join(out)

    ##################################################################
    # dataset status properties
    ##################################################################
    @property
    def pristine(self) -> bool:
        return not (self._started or self._completed)

    @property
    def started(self) -> bool:
        return self._started

    @started.setter
    def started(self, value: bool) -> None:
        self._started = value
        if value:
            self.run_group.attrs["started"] = value

    @property
    def completed(self) -> bool:
        return self._completed

    @property
    def running(self) -> bool:
        return self._started and not self._completed

    @completed.setter
    def completed(self, value: bool) -> None:
        self._completed = value
        if value:
            self.run_group.attrs["completed"] = value

    def _raise_if_not_writable(self) -> None:
        if self.pristine:
            raise RuntimeError(
                "This DataSet has not been marked as started. "
                "Please mark the DataSet as started before "
                "adding results to it."
            )
        if self.completed:
            raise CompletedError(
                "This DataSet is complete, no further " "results can be added to it."
            )

    ##################################################################
    # start and completion actions
    ##################################################################
    def mark_started(self, start_bg_writer: bool = False) -> None:
        """
        Mark this class as started.
        Calling this on an already started :class:`.DataSet` is a NOOP.

        Arguments:
            start_bg_writer: If True, the add_results method will write to the
                database in a separate thread.
        """
        if not self._started:
            self._perform_start_actions(start_bg_writer=start_bg_writer)
            self._started = True

    def _perform_start_actions(self, start_bg_writer: bool) -> None:
        """
        Perform a series of actions once the run has been started.

        Arguments:
        start_bg_writer: whether start background writer
        """
        # store the description
        desc_json = serial.to_json_for_storage(self._rundescriber)
        desc_str = desc_json

        self.run_group.attrs.modify("description", desc_str)

        # set time stamp
        timestamp = self.run_group.attrs.get("run_timestamp")
        if timestamp == "NoneType:__None__":
            timestamp = None
        if timestamp is not None:
            raise RuntimeError(
                "Can not set run_timestamp; it has already " f"been set to: {timestamp}"
            )
        else:
            current_time = time.time()
            self.run_group.attrs.modify("run_timestamp", current_time)

            log.info(
                f"Set the run_timestamp of run_id {self.run_id} to " f"{current_time}"
            )

        # parent dataset links
        pdl_str = links_to_str(self._parent_dataset_links)
        self.run_group.attrs.modify("parent_dataset_links", pdl_str)

        # write in background
        writer_status = self._writer_status

        write_in_background_status = writer_status.write_in_background
        if (
            write_in_background_status is not None
            and write_in_background_status != start_bg_writer
        ):
            raise RuntimeError(
                "All datasets written to the same database must "
                "be written either in the background or in the "
                "main thread. You cannot mix."
            )
        if start_bg_writer:
            writer_status.write_in_background = True
            if writer_status.bg_writer is None:
                writer_status.bg_writer = _BackgroundWriter(
                    writer_status.data_write_queue, self.run_group_full_path
                )
            if not writer_status.bg_writer.is_alive():
                writer_status.bg_writer.start()
        else:
            writer_status.write_in_background = False
        writer_status.active_datasets.add(self.run_id)

        self.conn.flush()

    def mark_completed(self) -> None:
        """
        Mark :class:`.DataSet` as complete and thus read only and notify the subscribers
        """
        if self._completed:
            print("The dataset has been marked completed.")
        if self.pristine:
            raise RuntimeError(
                "Can not mark DataSet as complete before it "
                "has been marked as started."
            )

        self._perform_completion_actions()
        self._completed = True

    def _perform_completion_actions(self) -> None:
        """
        Perform the necessary clean-up
        """
        for sub in self.subscribers.values():
            sub.done_callback()
        self._ensure_dataset_written()

        self.conn.flush()

    def _ensure_dataset_written(self) -> None:
        writer_status = self._writer_status

        if writer_status.write_in_background:
            writer_status.data_write_queue.put(
                {"keys": "finalize", "values": self.run_id}
            )
            while self.run_id in writer_status.active_datasets:
                time.sleep(self.background_sleep_time)
        else:
            if self.run_id in writer_status.active_datasets:
                writer_status.active_datasets.remove(self.run_id)
        if len(writer_status.active_datasets) == 0:
            writer_status.write_in_background = None
            if writer_status.bg_writer is not None:
                writer_status.bg_writer.shutdown()
                writer_status.bg_writer = None

    ##################################################################
    # result
    ##################################################################
    def _raise_if_not_writable(self) -> None:
        if self.pristine:
            raise RuntimeError(
                "This DataSet has not been marked as started. "
                "Please mark the DataSet as started before "
                "adding results to it."
            )
        if self.completed:
            raise CompletedError(
                "This DataSet is complete, no further " "results can be added to it."
            )

    def _ensure_dataset_written(self) -> None:
        writer_status = self._writer_status

        if writer_status.write_in_background:
            writer_status.data_write_queue.put(
                {"keys": "finalize", "values": self.run_id}
            )
            while self.run_id in writer_status.active_datasets:
                time.sleep(self.background_sleep_time)
        else:
            if self.run_id in writer_status.active_datasets:
                writer_status.active_datasets.remove(self.run_id)
        if len(writer_status.active_datasets) == 0:
            writer_status.write_in_background = None
            if writer_status.bg_writer is not None:
                writer_status.bg_writer.shutdown()
                writer_status.bg_writer = None

    def add_results(
        self,
        results: Sequence[Mapping[str, Value_types]],
        dataset_group_name: Optional[str] = None,
    ) -> None:
        """
        Adds a sequence of results to the :class:`.DataSet`.

        Arguments:
            results: list of name-value dictionaries where each dictionary
                provides the values for the parameters in that result. If some
                parameters are missing the corresponding values are assumed
                to be None

        It is an error to provide a value for a key or keyword that is not
        the name of a parameter in this :class:`.DataSet`.

        It is an error to add results to a completed :class:`.DataSet`.
        """
        self._raise_if_not_writable()

        single_dict = {}
        expected_keys = frozenset.union(*[frozenset(d) for d in results])
        for key in list(expected_keys):
            for d in results:
                if d.get(key) is not None:
                    single_dict[key] = d.get(key)
                else:
                    continue

        values = [[d.get(k, None) for k in expected_keys] for d in results]

        writer_status = self._writer_status

        if writer_status.write_in_background:
            item = {
                "keys": list(expected_keys),
                "values": values,
                "ds_group_name": dataset_group_name,
            }
            writer_status.data_write_queue.put(item)
        else:

            dataset_group_name = dataset_group_name or "data"
            dataset_group = self.run_group.require_group(dataset_group_name)

            # key is the dataset name under the dataset_group
            # for example: "I_avg" can be a name of dataset

            for key in list(expected_keys):

                if key in dataset_group.keys():

                    if isinstance(dataset_group[key], h5py.Dataset):
                        data = single_dict[key]

                        if isinstance(data, Datatype_set):
                            data = numpy.array([data])
                        elif isinstance(data, list):
                            data = numpy.array(data)

                        if isinstance(data, numpy.ndarray):
                            dataset = dataset_group[key]

                            dataset.resize(dataset.shape[0] + data.shape[0], axis=0)
                            dataset[-data.shape[0] :] = data
                        else:
                            raise ValueError(
                                "The data is not numpy.ndarray and cannot be converted to be this type."
                            )
                    else:
                        raise TypeError("The write position is not a hdf5 dataset")
                else:
                    data = single_dict[key]

                    if isinstance(data, Datatype_set):
                        data = numpy.array([data])
                    elif isinstance(data, list):
                        data = numpy.array(data)

                    if isinstance(data, numpy.ndarray):

                        tuple_shape = data.shape
                        list_shape = list(tuple_shape)
                        list_shape.insert(0, 1)
                        new_shape = tuple(list_shape)
                        data = data.reshape(new_shape)
                        list_shape[0] = None
                        maxshape = tuple(list_shape)
                        dataset_group.create_dataset(
                            name=key, data=data, maxshape=maxshape, chunks=True
                        )
                    else:
                        raise ValueError(
                            "The data is not numpy.ndarray and cannot be converted to be this type."
                        )

        self.conn.flush()

    def _enqueue_results(
        self, result_dict: Mapping[ParamSpecBase, numpy.ndarray]
    ) -> None:
        """
        Enqueue the results into self._results
        Before we can enqueue the results, all values of the results dict
        must have the same length. We enqueue each parameter tree separately,
        effectively mimicking making one call to add_results per parameter
        tree.
        Deal with 'numeric' type parameters. If a 'numeric' top level parameter
        has non-scalar shape, it must be unrolled into a list of dicts of
        single values (database).
        """

        self._raise_if_not_writable()

        interdeps = self._rundescriber.interdeps

        toplevel_params = set(interdeps.dependencies).intersection(set(result_dict))

        if self._in_memory_cache:
            new_results: Dict[str, Dict[str, numpy.ndarray]] = {}
        for toplevel_param in toplevel_params:

            inff_params = set(interdeps.inferences.get(toplevel_param, ()))
            deps_params = set(interdeps.dependencies.get(toplevel_param, ()))
            all_params = inff_params.union(deps_params).union({toplevel_param})

            if self._in_memory_cache:
                new_results[toplevel_param.name] = {}
                new_results[toplevel_param.name][
                    toplevel_param.name
                ] = self._reshape_array_for_cache(
                    toplevel_param, result_dict[toplevel_param]
                )
                for param in all_params:
                    if param is not toplevel_param:
                        new_results[toplevel_param.name][
                            param.name
                        ] = self._reshape_array_for_cache(param, result_dict[param])

            if toplevel_param.type == "array":
                res_list = self._finalize_res_dict_array(result_dict, all_params)
            elif toplevel_param.type in ("numeric", "text", "complex"):
                res_list = self._finalize_res_dict_numeric_text_or_complex(
                    result_dict, toplevel_param, inff_params, deps_params
                )
            else:
                res_dict: Dict[str, Value_types] = {
                    ps.name: result_dict[ps] for ps in all_params
                }
                res_list = [res_dict]
            self._results += res_list

        # Finally, handle standalone parameters

        standalones = set(interdeps.standalones).intersection(set(result_dict))

        if standalones:
            stdln_dict = {st: result_dict[st] for st in standalones}
            self._results += self._finalize_res_dict_standalones(stdln_dict)
            if self._in_memory_cache:
                for st in standalones:
                    new_results[st.name] = {
                        st.name: self._reshape_array_for_cache(st, result_dict[st])
                    }
        if self._in_memory_cache:
            self.cache.add_data(new_results)

    ##################################################################
    # result helper functions
    ##################################################################
    @staticmethod
    def _reshape_array_for_cache(
        param: ParamSpecBase, param_data: numpy.ndarray
    ) -> numpy.ndarray:
        """
        Shape cache data so it matches data read from database.
        This means:
        - Add an extra singleton dim to array data
        - flatten non array data into a linear array.
        """
        param_data = numpy.atleast_1d(param_data)
        if param.type == "array":
            new_data = numpy.reshape(param_data, (1,) + param_data.shape)
        else:
            new_data = param_data.ravel()
        return new_data

    @staticmethod
    def _finalize_res_dict_array(
        result_dict: Mapping[ParamSpecBase, Values_type], all_params: Set[ParamSpecBase]
    ) -> List[Dict[str, Value_types]]:
        """
        Make a list of res_dicts out of the results for a 'array' type
        parameter. The results are assumed to already have been validated for
        type and shape
        """

        def reshaper(val: Any, ps: ParamSpecBase) -> Value_types:
            paramtype = ps.type
            if paramtype == "numeric":
                return float(val)
            elif paramtype == "text":
                return str(val)
            elif paramtype == "complex":
                return complex(val)
            elif paramtype == "array":
                if val.shape:
                    return val
                else:
                    return numpy.reshape(val, (1,))
            else:
                raise ValueError(
                    f"Cannot handle unknown paramtype " f"{paramtype!r} of {ps!r}."
                )

        res_dict = {ps.name: reshaper(result_dict[ps], ps) for ps in all_params}

        return [res_dict]

    @staticmethod
    def _finalize_res_dict_numeric_text_or_complex(
        result_dict: Mapping[ParamSpecBase, numpy.ndarray],
        toplevel_param: ParamSpecBase,
        inff_params: Set[ParamSpecBase],
        deps_params: Set[ParamSpecBase],
    ) -> List[Dict[str, Value_types]]:
        """
        Make a res_dict in the format expected by DataSet.add_results out
        of the results for a 'numeric' or text type parameter. This includes
        replicating and unrolling values as needed and also handling the corner
        case of np.array(1) kind of values
        """

        res_list: List[Dict[str, Value_types]] = []
        all_params = inff_params.union(deps_params).union({toplevel_param})

        t_map = {"numeric": float, "text": str, "complex": complex}

        toplevel_shape = result_dict[toplevel_param].shape
        if toplevel_shape == ():
            # In the case of a single value, life is reasonably simple
            res_list = [{ps.name: t_map[ps.type](result_dict[ps]) for ps in all_params}]
        else:
            # We first massage all values into np.arrays of the same
            # shape
            flat_results: Dict[str, numpy.ndarray] = {}

            toplevel_val = result_dict[toplevel_param]
            flat_results[toplevel_param.name] = toplevel_val.ravel()
            N = len(flat_results[toplevel_param.name])
            for dep in deps_params:
                if result_dict[dep].shape == ():
                    flat_results[dep.name] = numpy.repeat(result_dict[dep], N)
                else:
                    flat_results[dep.name] = result_dict[dep].ravel()
            for inff in inff_params:
                if numpy.shape(result_dict[inff]) == ():
                    flat_results[inff.name] = numpy.repeat(result_dict[dep], N)
                else:
                    flat_results[inff.name] = result_dict[inff].ravel()

            # And then put everything into the list

            res_list = [
                {p.name: flat_results[p.name][ind] for p in all_params}
                for ind in range(N)
            ]

        return res_list

    @staticmethod
    def _finalize_res_dict_standalones(
        result_dict: Mapping[ParamSpecBase, numpy.ndarray]
    ) -> List[Dict[str, Value_types]]:
        """
        Massage all standalone parameters into the correct shape
        """
        res_list: List[Dict[str, Value_types]] = []
        for param, value in result_dict.items():
            if param.type == "text":
                if value.shape:
                    res_list += [{param.name: str(val)} for val in value]
                else:
                    res_list += [{param.name: str(value)}]
            elif param.type == "numeric":
                if value.shape:
                    res_list += [{param.name: number} for number in value]
                else:
                    res_list += [{param.name: float(value)}]
            elif param.type == "complex":
                if value.shape:
                    res_list += [{param.name: number} for number in value]
                else:
                    res_list += [{param.name: complex(value)}]
            else:
                res_list += [{param.name: value}]

        return res_list

    def _flush_data_to_database(self, block: bool = False) -> None:
        """
        Write the in-memory results to the database.

        Args:
            block: If writing using a background thread block until the
                background thread has written all data to disc. The
                argument has no effect if not using a background thread.

        """

        log.debug("Flushing to database")
        writer_status = self._writer_status
        if len(self._results) > 0:
            self.add_results(self._results)

            # try:
            #     self.add_results(self._results)
            #     print("add_results is perfomed in flush successfully")
            #     if writer_status.write_in_background:
            #         log.debug(f"Succesfully enqueued result for write thread")
            #     else:
            #         log.debug(f'Successfully wrote result to disk')
            #     self._results = []
            # except Exception as e:
            #     print("add_results is not perfomed")
            #     print(e)
            #     if writer_status.write_in_background:
            #         log.warning(f"Could not enqueue result; {e}")
            #     else:
            #         log.warning(f'Could not commit to database; {e}')
        else:
            log.debug("No results to flush")

        if writer_status.write_in_background and block:
            log.debug(f"Waiting for write queue to empty.")
            writer_status.data_write_queue.join()

    ##################################################################
    # metadata
    ##################################################################
    def add_metadata(self, tag: str, metadata: Any) -> None:
        """
        Adds metadata to the :class:`.DataSet`. The metadata is stored under the
        provided tag. The metadata is extracted from YAML file and is sotred as
        the attribute of experiment group. Note that None is not allowed as
        a metadata value.

        Arguments:
            tag: represents the key in the metadata dictionary
            metadata: actual metadata
        """
        if self._metadata:
            if tag in self._metadata.keys():
                self._metadata[tag] = metadata
                print("The metadata {0} has changed to {1}.".format(tag, metadata))
                log.info("The metadata {0} has changed to {1}.".format(tag, metadata))
            else:
                self._metadata[tag] = metadata
                print("The metadata {0} has set to {1}.".format(tag, metadata))
                log.info("The metadata {0} has set to {1}.".format(tag, metadata))
        else:
            self._metadata = {tag: metadata}
        self.save_metadata()

    def save_metadata(self) -> None:
        if self._metadata:
            metadata_string = json.dumps(self._metadata)
            self.run_group.attrs.modify("metadata", metadata_string)
            self.conn.flush()

    def add_snapshot(self, snapshot: str, overwrite: bool = True) -> None:
        """
        Adds a snapshot to this run

        Args:
            snapshot: the raw JSON dump of the snapshot
            overwrite: force overwrite an existing snapshot
        """
        if self.snapshot_raw is None or overwrite:
            self.run_group.attrs.modify("snapshot", snapshot)
            self.conn.flush()

        elif self.snapshot is not None and not overwrite:

            log.warning(
                "This dataset already has a snapshot. Use overwrite"
                "=True to overwrite that"
            )

    def get_metadata(self, tag: Optional[str] = None) -> None:

        if self.pristine:
            metadata_dict = self._metadata
        else:
            metadata_dict = self._get_metadata_from_db()

        if tag is None:
            return metadata_dict
        elif tag in metadata_dict.keys():
            return metadata_dict[tag]
        else:
            log.warning("The requried tag does not exist in the metadata")

    def _get_metadata_from_db(self, key="metadata") -> Dict:
        """
        Look up the metadata dict from the database
        """
        metadata_string = self.run_group.attrs[key]
        metadata_dict = json.loads(metadata_string)
        return metadata_dict

    def _get_run_description_from_db(self, key="description") -> RunDescriber:
        """
        Look up the run_description from the database
        """
        description_json = self.run_group.attrs[key]
        rundescriber = serial.from_json_to_current(description_json)
        return rundescriber

    ##################################################################
    # parameters
    ##################################################################
    def set_interdependencies(
        self, interdeps: InterDependencies_, shapes: Shapes = None
    ) -> None:
        """
        Set the interdependencies object (which holds all added
        parameters and their relationships) of this dataset and
        optionally the shapes object that holds information about
        the shape of the data to be measured.
        """
        if not isinstance(interdeps, InterDependencies_):
            raise TypeError(
                "Wrong input type. Expected InterDepencies_, " f"got {type(interdeps)}"
            )

        if not self.pristine:
            mssg = (
                "Can not set interdependencies on a DataSet that has " "been started."
            )
            raise RuntimeError(mssg)
        self._rundescriber = RunDescriber(interdeps, shapes=shapes)

    def get_parameters(self) -> Specs_types:
        old_interdeps = new_to_old(self._rundescriber.interdeps)
        return list(old_interdeps.paramspecs)

    @staticmethod
    def _validate_parameters(
        *params: Union[str, ParamSpec, _BaseParameter]
    ) -> List[str]:
        """
        Validate that the provided parameters have a name and return those
        names as a list.
        The Parameters may be a mix of strings, ParamSpecs or ordinary
        QCoDeS parameters.
        """

        valid_param_names = []
        for maybeParam in params:
            if isinstance(maybeParam, str):
                valid_param_names.append(maybeParam)
                continue
            else:
                try:
                    maybeParam = maybeParam.name
                except Exception as e:
                    raise ValueError("This parameter does not have  a name") from e
                valid_param_names.append(maybeParam)
        return valid_param_names

    def get_parameter_data(
        self,
        *params: Union[str, ParamSpec, _BaseParameter],
        start: Optional[int] = None,
        end: Optional[int] = None,
    ) -> ParameterData:
        """
        Returns the values stored in the :class:`.DataSet` for the specified parameters
        and their dependencies. If no parameters are supplied the values will
        be returned for all parameters that are not them self dependencies.

        The values are returned as a dictionary with names of the requested
        parameters as keys and values consisting of dictionaries with the
        names of the parameters and its dependencies as keys and numpy arrays
        of the data as values. If the dataset has a shape recorded
        in its metadata and the number of datapoints recorded matches the
        expected number of points the data will be returned as numpy arrays
        in this shape. If there are less datapoints recorded than expected
        from the metadata the dataset will be returned as is. This could happen
        if you call `get_parameter_data` on an incomplete dataset. See
        :py:meth:`dataset.cache.data <.DataSetCache.data>` for an implementation that
        returns the data with the expected shape using `NaN` or zeros as
        placeholders.

        If there are more datapoints than expected the dataset will be returned
        as is and a warning raised.

        If some of the parameters are stored as arrays
        the remaining parameters are expanded to the same shape as these.

        If provided, the start and end arguments select a range of results
        by result count (index). If the range is empty - that is, if the end is
        less than or equal to the start, or if start is after the current end
        of the :class:`.DataSet` – then a list of empty arrays is returned.

        Arguments:
            *params: string parameter names, QCoDeS Parameter objects, and
                ParamSpec objects. If no parameters are supplied data for
                all parameters that are not a dependency of another
                parameter will be returned.
            start: start value of selection range (by result count); ignored
                if None
            end: end value of selection range (by results count); ignored if
                None

        Returns:
            Dictionary from requested parameters to Dict of parameter names
            to numpy arrays containing the data points of type numeric,
            array or string.
        """
        if len(params) == 0:
            valid_param_names = [
                ps.name for ps in self._rundescriber.interdeps.non_dependencies
            ]
        else:
            valid_param_names = self._validate_parameters(*params)

        return get_parameter_data(
            self.conn,
            self.dataset_name,
            self.exp_name,
            self.run_name,
            valid_param_names,
            start,
            end,
        )

    ##################################################################
    # subscribe
    ##################################################################
    def subscribe(
        self,
        callback: Callable[[Any, int, Optional[Any]], None],
        min_wait: int = 0,
        min_count: int = 1,
        state: Optional[Any] = None,
        callback_kwargs: Optional[Mapping[str, Any]] = None,
    ) -> str:
        subscriber_id = uuid.uuid4().hex
        subscriber = _Subscriber(
            self, subscriber_id, callback, state, min_wait, min_count, callback_kwargs
        )
        self.subscribers[subscriber_id] = subscriber
        subscriber.start()
        return subscriber_id

    def subscribe_from_config(self, name: str) -> str:
        """
        Subscribe a subscriber defined in the `qcodesrc.json` config file to
        the data of this :class:`.DataSet`. The definition can be found at
        ``subscription.subscribers`` in the ``qcodesrc.json`` config file.

        Args:
            name: identifier of the subscriber. Equal to the key of the entry
                in ``qcodesrc.json::subscription.subscribers``.
        """
        subscribers = qcodes.config.subscription.subscribers
        try:
            subscriber_info = getattr(subscribers, name)
        # the dot dict behind the config does not convert the error and
        # actually raises a `KeyError`
        except (AttributeError, KeyError):
            keys = ",".join(subscribers.keys())
            raise RuntimeError(
                f'subscribe_from_config: failed to subscribe "{name}" to '
                f"DataSet from list of subscribers in `qcodesrc.json` "
                f"(subscriptions.subscribers). Chose one of: {keys}"
            )
        # get callback from string
        parts = subscriber_info.factory.split(".")
        import_path, type_name = ".".join(parts[:-1]), parts[-1]
        module = importlib.import_module(import_path)
        factory = getattr(module, type_name)

        kwargs = {k: v for k, v in subscriber_info.subscription_kwargs.items()}
        kwargs["callback"] = factory(self, **subscriber_info.factory_kwargs)
        kwargs["state"] = {}
        return self.subscribe(**kwargs)

    def unsubscribe(self, uuid: str) -> None:
        """
        Remove subscriber with the provided uuid
        """
        sub = self.subscribers[uuid]

        sub.schedule_stop()
        sub.join()
        del self.subscribers[uuid]

    def unsubscribe_all(self) -> None:
        """
        Remove all subscribers
        """
        for sub in self.subscribers.values():
            sub.schedule_stop()
            sub.join()
        self.subscribers.clear()

    ##################################################################
    # export a text file
    ##################################################################

    def _export_file_name(self, prefix: str, export_type: DataExportType) -> str:
        """Get export file name"""
        extension = export_type.value
        return f"{prefix}{self.run_id}.{extension}"

    def _export_as_netcdf(self, path: str, file_name: str) -> str:
        """Export data as netcdf to a given path with file prefix"""
        file_path = os.path.join(path, file_name)
        xarr_dataset = self.to_xarray_dataset()
        xarr_dataset.to_netcdf(path=file_path)
        return path

    def _export_as_csv(self, path: str, file_name: str) -> str:
        """Export data as csv to a given path with file prefix"""
        self.write_data_to_text_file(
            path=path, single_file=True, single_file_name=file_name
        )
        return os.path.join(path, file_name)

    def _export_data(
        self,
        export_type: DataExportType,
        path: Optional[str] = None,
        prefix: Optional[str] = None,
    ) -> Optional[str]:
        """Export data to disk with file name {prefix}{run_id}.{ext}.
        Values for the export type, path and prefix can also be set in the qcodes
        "dataset" config.

        Args:
            export_type: Data export type, e.g. DataExportType.NETCDF
            path: Export path, defaults to value set in config
            prefix: File prefix, e.g. "qcodes_", defaults to value set in config.

        Returns:
            str: Path file was saved to, returns None if no file was saved.
        """
        # Set defaults to values in config if the value was not set
        # (defaults to None)
        path = path if path is not None else get_data_export_path()
        prefix = prefix if prefix is not None else get_data_export_prefix()

        if DataExportType.NETCDF == export_type:
            file_name = self._export_file_name(
                prefix=prefix, export_type=DataExportType.NETCDF
            )
            return self._export_as_netcdf(path=path, file_name=file_name)

        elif DataExportType.CSV == export_type:
            file_name = self._export_file_name(
                prefix=prefix, export_type=DataExportType.CSV
            )
            return self._export_as_csv(path=path, file_name=file_name)

        else:
            return None

    def export(
        self,
        export_type: Optional[Union[DataExportType, str]] = None,
        path: Optional[str] = None,
        prefix: Optional[str] = None,
    ) -> None:
        """Export data to disk with file name {prefix}{run_id}.{ext}.
        Values for the export type, path and prefix can also be set in the "dataset"
        section of qcodes config.

        Args:
            export_type: Data export type, e.g. "netcdf" or ``DataExportType.NETCDF``,
                defaults to a value set in qcodes config
            path: Export path, defaults to value set in config
            prefix: File prefix, e.g. ``qcodes_``, defaults to value set in config.

        Raises:
            ValueError: If the export data type is not specified, raise an error
        """
        export_type = get_data_export_type(export_type)

        if export_type is None:
            raise ValueError(
                "No data export type specified. Please set the export data type "
                "by using ``qcodes.dataset.export_config.set_data_export_type`` or "
                "give an explicit export_type when calling ``dataset.export`` manually."
            )

        self._export_path = self._export_data(
            export_type=export_type, path=path, prefix=prefix
        )

    @property
    def export_path(self) -> Optional[str]:
        return self._export_path

    def write_data_to_text_file(
        self,
        path: str,
        single_file: bool = False,
        single_file_name: Optional[str] = None,
    ) -> None:
        """
        An auxiliary function to export data to a text file. When the data with more
        than one dependent variables, say "y(x)" and "z(x)", is concatenated to a single file
        it reads:

                    x1  y1(x1)  z1(x1)
                    x2  y2(x2)  z2(x2)
                    ..    ..      ..
                    xN  yN(xN)  zN(xN)

        For each new independent variable, say "k", the expansion is in the y-axis:

                    x1  y1(x1)  z1(x1)
                    x2  y2(x2)  z2(x2)
                    ..    ..      ..
                    xN  yN(xN)  zN(xN)
                    k1  y1(k1)  z1(k1)
                    k2  y2(k2)  z2(k2)
                    ..    ..      ..
                    kN  yN(kN)  zN(kN)

        Args:
            path: User defined path where the data to be exported
            single_file: If true, merges the data of same length of multiple
                         dependent parameters to a single file.
            single_file_name: User defined name for the data to be concatenated.
                              If no extension is passed (.dat, .csv or .txt),
                              .dat is automatically appended.

        Raises:
            DataLengthException: If the data of multiple parameters have not same
                                 length and wanted to be merged in a single file.
            DataPathException: If the data of multiple parameters are wanted to be merged
                               in a single file but no filename provided.
        """
        import pandas as pd

        dfdict = self.to_pandas_dataframe_dict()
        dfs_to_save = list()
        for parametername, df in dfdict.items():
            if not single_file:
                dst = os.path.join(path, f"{parametername}.dat")
                df.to_csv(path_or_buf=dst, header=False, sep="\t")
            else:
                dfs_to_save.append(df)
        if single_file:
            df_length = len(dfs_to_save[0])
            if any(len(df) != df_length for df in dfs_to_save):
                raise DataLengthException(
                    "You cannot concatenate data "
                    + "with different length to a "
                    + "single file."
                )
            if single_file_name is None:
                raise DataPathException(
                    "Please provide the desired file name "
                    + "for the concatenated data."
                )
            else:
                if not single_file_name.lower().endswith((".dat", ".csv", ".txt")):
                    single_file_name = f"{single_file_name}.dat"
                dst = os.path.join(path, single_file_name)
                df_to_save = pd.concat(dfs_to_save, axis=1)
                df_to_save.to_csv(path_or_buf=dst, header=False, sep="\t")

    def _export_as_csv(self, path: str, file_name: str) -> str:
        """Export data as csv to a given path with file prefix"""

        self.write_data_to_text_file(
            path=path, single_file=True, single_file_name=file_name
        )
        return os.path.join(path, file_name)

    ##################################################################
    # export to dataframe or xarray
    ##################################################################
    def to_pandas_dataframe_dict(
        self,
        *params: Union[str, ParamSpec, _BaseParameter],
        start: Optional[int] = None,
        end: Optional[int] = None,
    ) -> Dict[str, "pd.DataFrame"]:
        """
        Returns the values stored in the :class:`.DataSet` for the specified parameters
        and their dependencies as a dict of :py:class:`pandas.DataFrame` s
        Each element in the dict is indexed by the names of the requested
        parameters.

        Each DataFrame contains a column for the data and is indexed by a
        :py:class:`pandas.MultiIndex` formed from all the setpoints
        of the parameter.

        If no parameters are supplied data will be be
        returned for all parameters in the :class:`.DataSet` that are not them self
        dependencies of other parameters.

        If provided, the start and end arguments select a range of results
        by result count (index). If the range is empty - that is, if the end is
        less than or equal to the start, or if start is after the current end
        of the :class:`.DataSet` – then a dict of empty :py:class:`pandas.DataFrame` s is
        returned.

        Args:
            *params: string parameter names, QCoDeS Parameter objects, and
                ParamSpec objects. If no parameters are supplied data for
                all parameters that are not a dependency of another
                parameter will be returned.
            start: start value of selection range (by result count); ignored
                if None
            end: end value of selection range (by results count); ignored if
                None

        Returns:
            Dictionary from requested parameter names to
            :py:class:`pandas.DataFrame` s with the requested parameter as
            a column and a indexed by a :py:class:`pandas.MultiIndex` formed
            by the dependencies.
        """
        datadict = self.get_parameter_data(*params, start=start, end=end)
        dfs_dict = load_to_dataframe_dict(datadict)
        return dfs_dict

    def to_pandas_dataframe(
        self,
        *params: Union[str, ParamSpec, _BaseParameter],
        start: Optional[int] = None,
        end: Optional[int] = None,
    ) -> "pd.DataFrame":
        """
        Returns the values stored in the :class:`.DataSet` for the specified parameters
        and their dependencies as a concatenated :py:class:`pandas.DataFrame` s

        The DataFrame contains a column for the data and is indexed by a
        :py:class:`pandas.MultiIndex` formed from all the setpoints
        of the parameter.

        If no parameters are supplied data will be be
        returned for all parameters in the :class:`.DataSet` that are not them self
        dependencies of other parameters.

        If provided, the start and end arguments select a range of results
        by result count (index). If the range is empty - that is, if the end is
        less than or equal to the start, or if start is after the current end
        of the :class:`.DataSet` – then a dict of empty :py:class:`pandas.DataFrame` s is
        returned.

        Args:
            *params: string parameter names, QCoDeS Parameter objects, and
                ParamSpec objects. If no parameters are supplied data for
                all parameters that are not a dependency of another
                parameter will be returned.
            start: start value of selection range (by result count); ignored
                if None
            end: end value of selection range (by results count); ignored if
                None

        Returns:
            :py:class:`pandas.DataFrame` s with the requested parameter as
            a column and a indexed by a :py:class:`pandas.MultiIndex` formed
            by the dependencies.

        Example:
            Return a pandas DataFrame with
                df = ds.to_pandas_dataframe()
        """
        datadict = self.get_parameter_data(*params, start=start, end=end)
        return load_to_concatenated_dataframe(datadict)

    def to_xarray_dataarray_dict(
        self,
        *params: Union[str, ParamSpec, _BaseParameter],
        start: Optional[int] = None,
        end: Optional[int] = None,
    ) -> Dict[str, "xr.DataArray"]:
        """
        Returns the values stored in the :class:`.DataSet` for the specified parameters
        and their dependencies as a dict of :py:class:`xr.DataArray` s
        Each element in the dict is indexed by the names of the requested
        parameters.

        If no parameters are supplied data will be be
        returned for all parameters in the :class:`.DataSet` that are not them self
        dependencies of other parameters.

        If provided, the start and end arguments select a range of results
        by result count (index). If the range is empty - that is, if the end is
        less than or equal to the start, or if start is after the current end
        of the :class:`.DataSet` – then a dict of empty :py:class:`xr.DataArray` s is
        returned.

        The dependent parameters of the Dataset are normally used as coordinates of the
        XArray dataframe. However if non unique values are found for the dependent parameter
        values we will fall back to using an index as coordinates.

        Args:
            *params: string parameter names, QCoDeS Parameter objects, and
                ParamSpec objects. If no parameters are supplied data for
                all parameters that are not a dependency of another
                parameter will be returned.
            start: start value of selection range (by result count); ignored
                if None
            end: end value of selection range (by results count); ignored if
                None

        Returns:
            Dictionary from requested parameter names to :py:class:`xr.DataArray` s
            with the requested parameter(s) as a column(s) and coordinates
            formed by the dependencies.

        Example:
            Return a dict of xr.DataArray with

                dataarray_dict = ds.to_xarray_dataarray_dict()
        """
        data = self.get_parameter_data(*params, start=start, end=end)
        datadict = load_to_xarray_dataarray_dict(self, data)

        return datadict

    def to_xarray_dataset(
        self,
        *params: Union[str, ParamSpec, _BaseParameter],
        start: Optional[int] = None,
        end: Optional[int] = None,
    ) -> "xr.Dataset":
        """
        Returns the values stored in the :class:`.DataSet` for the specified parameters
        and their dependencies as a :py:class:`xr.Dataset` object.

        If no parameters are supplied data will be be
        returned for all parameters in the :class:`.DataSet` that are not then self
        dependencies of other parameters.

        If provided, the start and end arguments select a range of results
        by result count (index). If the range is empty - that is, if the end is
        less than or equal to the start, or if start is after the current end
        of the :class:`.DataSet` – then a empty :py:class:`xr.Dataset` s is
        returned.

        The dependent parameters of the Dataset are normally used as coordinates of the
        XArray dataframe. However if non unique values are found for the dependent parameter
        values we will fall back to using an index as coordinates.

        Args:
            *params: string parameter names, QCoDeS Parameter objects, and
                ParamSpec objects. If no parameters are supplied data for
                all parameters that are not a dependency of another
                parameter will be returned.
            start: start value of selection range (by result count); ignored
                if None
            end: end value of selection range (by results count); ignored if
                None

        Returns:
            :py:class:`xr.Dataset` with the requested parameter(s) data as
            :py:class:`xr.DataArray` s and coordinates formed by the dependencies.

        Example:
            Return a concatenated xr.Dataset with

                xds = ds.to_xarray_dataset()
        """
        data = self.get_parameter_data(*params, start=start, end=end)

        return load_to_xarray_dataset(self, data)


##################################################################
# parameter helper function
##################################################################


def get_parameter_data(
    conn: Connection,
    dataset_name: str,
    exp_group_name: str,
    run_group_name: str,
    columns: Sequence[str] = (),
    start: Optional[int] = None,
    end: Optional[int] = None,
) -> Dict[str, Dict[str, numpy.ndarray]]:

    exp_group = conn.require_group(exp_group_name)
    run_group = exp_group.require_group(run_group_name)

    print(run_group.attrs.keys())
    print(run_group.attrs.get("description"))
    description = run_group.attrs.get("description")
    rundescriber = serial.from_json_to_current(description)

    output = {}
    if len(columns) == 0:
        columns = [ps.name for ps in rundescriber.interdeps.non_dependencies]

    # loo over all requested parameters
    for output_param in columns:
        output[output_param] = get_parameter_data_for_one_paramtree(
            conn,
            dataset_name,
            exp_group_name,
            run_group_name,
            rundescriber,
            output_param,
            start,
            end,
        )
    return output


def get_shaped_parameter_data_for_one_paramtree(
    conn: Connection,
    dataset_name: str,
    exp_name: str,
    run_name: str,
    rundescriber: RunDescriber,
    output_param: str,
    start: Optional[int],
    end: Optional[int],
) -> Dict[str, numpy.ndarray]:
    """
    Get the data for a parameter tree and reshape it according to the
    metadata about the dataset. This will only reshape the loaded data if
    the number of points in the loaded data matches the expected number of
    points registered in the metadata.
    If there are more measured datapoints
    than expected a warning will be given.
    """

    one_param_output, _ = get_parameter_data_for_one_paramtree(
        conn, dataset_name, exp_name, run_name, rundescriber, output_param, start, end
    )
    if rundescriber.shapes is not None:
        shape = rundescriber.shapes.get(output_param)

        if shape is not None:
            total_len_shape = numpy.prod(shape)
            for name, paramdata in one_param_output.items():
                total_data_shape = numpy.prod(paramdata.shape)
                if total_data_shape == total_len_shape:
                    one_param_output[name] = paramdata.reshape(shape)
                elif total_data_shape > total_len_shape:
                    log.warning(
                        f"Tried to set data shape for {name} in "
                        f"dataset {output_param} "
                        f"from metadata when "
                        f"loading but found inconsistent lengths "
                        f"{total_data_shape} and {total_len_shape}"
                    )
    return one_param_output


def get_parameter_data_for_one_paramtree(
    conn: Connection,
    dataset_name: str,
    exp_name: str,
    run_name: str,
    rundescriber: RunDescriber,
    output_param: str,
    start: Optional[int],
    end: Optional[int],
) -> Tuple[Dict[str, numpy.ndarray], Tuple[int]]:

    interdeps = rundescriber.interdeps
    data, paramspecs, shape = _get_data_for_one_param_tree(
        conn, dataset_name, exp_name, run_name, interdeps, output_param, start, end
    )
    return data, shape


def _get_data_for_one_param_tree(
    conn: Connection,
    dataset_name: str,
    exp_name: str,
    run_name: str,
    interdeps: InterDependencies_,
    output_param: str,
    start: Optional[int],
    end: Optional[int],
) -> Tuple[List[numpy.ndarray], List[ParamSpecBase], Tuple[int]]:
    output_param_spec = interdeps._id_to_paramspec[output_param]
    # find all the dependencies of this param

    dependency_params = list(interdeps.dependencies.get(output_param_spec, ()))
    dependency_names = [param.name for param in dependency_params]
    paramspecs = [output_param_spec] + dependency_params

    res = get_parameter_tree_values(
        conn,
        dataset_name,
        exp_name,
        run_name,
        output_param,
        *dependency_names,
        start=start,
        end=end,
    )
    shape = res[0].shape
    return res, paramspecs, shape


def get_parameter_tree_values(
    conn: Connection,
    dataset_name: str,
    exp_group_name: str,
    run_group_name: str,
    toplevel_param_name: str,
    *other_param_names: str,
    start: Optional[int] = None,
    end: Optional[int] = None,
) -> List[numpy.ndarray]:
    """
    Returns:
        A list of numpy.ndarray, the index is the parameters
    """

    results = []
    columns = [toplevel_param_name] + list(other_param_names)

    exp_group = conn.require_group(exp_group_name)
    run_group = exp_group.require_group(run_group_name)
    dataset_group = run_group.require_group(dataset_name)
    for key, column in enumerate(columns):
        if column in dataset_group.keys():
            data = dataset_group.require_dataset(column)[:]
            if data.shape[0] == 1:
                shape_list = list(data.shape)
                shape_list.pop(0)
                new_tuple = tuple(shape_list)
                data = data.reshape(new_tuple)
            results.append(data[start:end])

    return results


##################################################################
# link helper function
##################################################################

##################################################################
# create dataset
##################################################################


def new_data_set(
    name: Optional[str],
    exp_id: Optional[int] = None,
    exp_name: Optional[str] = None,
    sample_name: Optional[str] = None,
    run_name: Optional[str] = None,
    specs: Optional[Specs_types] = None,
    values: Optional[Values_type] = None,
    metadata: Optional[Any] = None,
    conn: Optional[Connection] = None,
    is_new_exp: bool = False,
    in_memory_cache: bool = False,
) -> HDF5DataSet:
    """
    Create a new dataset in the currently active/selected database.

    If ``exp_id`` is not specified, the last experiment will be loaded by default.

    Args:
        name: the name of the new dataset
        exp_id: the id of the experiments this dataset belongs to, defaults
            to the last experiment
        specs: list of parameters to create this dataset with
        values: the values to associate with the parameters
        metadata: the metadata to associate with the dataset
        in_memory_cache: Should measured data be keep in memory
            and available as part of the `dataset.cache` object.

    Return:
        the newly created :class:`.DataSet`
    """
    # note that passing `conn` is a secret feature that is unfortunately used
    # in `Runner` to pass a connection from an existing `Experiment`.
    d = HDF5DataSet(
        database_path=None,
        run_id=None,
        conn=conn,
        name=name,
        is_new_exp=False,
        exp_name=exp_name,
        sample_name=sample_name,
        run_name=run_name,
        specs=specs,
        values=values,
        metadata=metadata,
        exp_id=exp_id,
        in_memory_cache=in_memory_cache,
    )

    return d


class _Subscriber(Thread):
    """
    Class to add a subscriber to a :class:`.DataSet`. The subscriber gets called every
    time an insert is made to the results_table.

    The _Subscriber is not meant to be instantiated directly, but rather used
    via the 'subscribe' method of the :class:`.DataSet`.

    NOTE: A subscriber should be added *after* all parameters have been added.

    NOTE: Special care shall be taken when using the *state* object: it is the
    user's responsibility to operate with it in a thread-safe way.
    """

    def __init__(
        self,
        dataset: HDF5DataSet,
        id_: str,
        callback: Callable[..., None],
        state: Optional[Any] = None,
        loop_sleep_time: int = 0,  # in milliseconds
        min_queue_length: int = 1,
        callback_kwargs: Optional[Mapping[str, Any]] = None,
    ) -> None:
        super().__init__()

        self._id = id_

        self.dataSet = dataset
        self.dataset_name = dataset.dataset_name
        self._data_set_len = dataset.length

        self.state = state

        self.data_queue: "Queue[Any]" = Queue()
        self._queue_length: int = 0
        self._stop_signal: bool = False
        # convert milliseconds to seconds
        self._loop_sleep_time = loop_sleep_time / 1000
        self.min_queue_length = min_queue_length

        if callback_kwargs is None or len(callback_kwargs) == 0:
            self.callback = callback
        else:
            self.callback = functools.partial(callback, **callback_kwargs)

        self.callback_id = f"callback{self._id}"
        self.trigger_id = f"sub{self._id}"

        conn = dataset.conn

        conn.create_function(self.callback_id, -1, self._cache_data_to_queue)

        parameters = dataset.get_parameters()

        self.log = logging.getLogger(f"_Subscriber {self._id}")

    def _cache_data_to_queue(self, *args: Any) -> None:
        self.data_queue.put(args)
        self._data_set_len += 1
        self._queue_length += 1

    def run(self) -> None:
        self.log.debug("Starting subscriber")
        self._loop()

    @staticmethod
    def _exhaust_queue(queue: "Queue[Any]") -> List[Any]:
        result_list = []
        # while True:
        #     try:
        #         result_list.append(queue.get(block=False))
        #     except Empty:
        #         break
        # return result_list

    def _call_callback_on_queue_data(self) -> None:
        result_list = self._exhaust_queue(self.data_queue)
        self.callback(result_list, self._data_set_len, self.state)

    def _loop(self) -> None:
        while True:
            if self._stop_signal:
                self._clean_up()
                break

            if self._queue_length >= self.min_queue_length:
                self._call_callback_on_queue_data()
                self._queue_length = 0

            time.sleep(self._loop_sleep_time)

            if self.dataSet.completed:
                self._call_callback_on_queue_data()
                break

    def done_callback(self) -> None:
        self._call_callback_on_queue_data()

    def schedule_stop(self) -> None:
        if not self._stop_signal:
            self.log.debug("Scheduling stop")
            self._stop_signal = True

    def _clean_up(self) -> None:
        self.log.debug("Stopped subscriber")


# def new_data_set( database_path: Optional[str] = None,
#                  name: Optional[str] = None,
#                  is_new_exp: bool = False,
#                  run_id: Optional[int] = None,
#                  exp_name: Optional[str] = None,
#                  sample_name: Optional[str] = None,
#                  exp_id: Optional[int] = None,
#                  conn: Optional[Hdf5_file_type] = None,
#                  run_name: Optional[str] = None,
#                  specs: Optional[SpecsOrInterDeps] = None,
#                  metadata: Optional[Mapping[str, Any]] = None,
#                  shapes: Optional[Shapes] = None,
#                  in_memory_cache: bool = True
#                  ) -> HDF5DataSet:
#     """
#     Create a new dataset in the currently active/selected database.

#     If ``exp_id`` is not specified, the last experiment will be loaded by default.

#     Args:
#         name: the name of the new dataset
#         exp_id: the id of the experiments this dataset belongs to, defaults
#             to the last experiment
#         specs: list of parameters to create this dataset with
#         values: the values to associate with the parameters
#         metadata: the metadata to associate with the dataset
#         in_memory_cache: Should measured data be keep in memory
#             and available as part of the `dataset.cache` object.

#     Return:
#         the newly created :class:`.DataSet`
#     """
#     # note that passing `conn` is a secret feature that is unfortunately used
#     # in `Runner` to pass a connection from an existing `Experiment`.
#     d = HDF5DataSet(database_path = database_path,
#                     name = name,
#                     is_new_exp = is_new_exp,
#                     run_id = run_id,
#                     exp_name = exp_name,
#                     sample_name = sample_name,
#                     exp_id = exp_id,
#                     conn = conn,
#                     run_name = run_name,
#                     specs = specs,
#                     metadata = metadata,
#                     shapes = shapes,
#                     in_memory_cache = in_memory_cache)

#     return d


def load_by_guid(guid: str, conn: Optional[Connection] = None) -> HDF5DataSet:
    """
    Load a dataset by its GUID

    If no connection is provided, lookup is performed in the database file that
    is specified in the config.

    Args:
        guid: guid of the dataset
        conn: connection to the database to load from

    Returns:
        :class:`.DataSet` with the given guid

    Raises:
        NameError: if no run with the given GUID exists in the database
        RuntimeError: if several runs with the given GUID are found
    """
    run_id = None
    exp_id = None
    for exp_group in conn.items():
        for run_group in exp_group.items():
            test = run_group.attrs["guid"]
            if test == guid:
                run_id = run_group.attrs["run_id"]
                exp_id = run_group.attrs["exp_id"]

    if run_id and exp_id:
        return HDF5DataSet(conn=conn, run_id=run_id, exp_id=exp_id)
    else:
        return None

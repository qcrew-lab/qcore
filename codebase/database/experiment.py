from collections.abc import Sized
from .database import get_DB_location, connect
from sys import prefix
from typing import Optional, List, Any
import logging
from numpy import split

import qcodes

from .hdf5_helper import DatabaseFile
from .dataset_hdf5 import*

log = logging.getLogger(__name__)

class Experiment(Sized):
    def __init__(self, data_path: Optional[str] = None,
                 exp_id: Optional[int] = None,
                 name: Optional[str] = None,
                 sample_name: Optional[str] = None,
                 conn: Optional[Connection] = None) -> None:
        """
        Create or load an experiment. If exp_id is None, a new experiment is
        created. If exp_id is not None, an experiment is loaded.

        Args:
            path_to_db: The path of the database file to create in/load from.
              If a conn is passed together with path_to_db, an exception is
              raised
            exp_id: The id of the experiment to load
            name: The name of the experiment to create. Ignored if exp_id is
              not None
            sample_name: The sample name for this experiment. Ignored if exp_id
              is not None
            conn: connection to the database. If not supplied, the constructor
              first tries to use path_to_db to figure out where to connect to.
              If path_to_db is not supplied either, a new connection
              to the DB file specified in the config is made
        """

        # create connection to the database
        if conn is None: 
            self.conn = DatabaseFile(name, data_path)
        elif conn is not None: 
            self.conn = conn

        max_id = len(self.conn.keys())
        
        if exp_id is not None:
            if exp_id not in range(1, max_id+1):
                raise ValueError('No such experiment in the database')
            else:
                self._exp_id = exp_id
                if name and sample_name:
                    test_group_name = name+"#"+sample_name+"#"+str(exp_id)

                    if test_group_name in self.conn.keys():
                        self._exp_group_name = test_group_name
                        self.exp_group = self.conn.require_group(test_group_name)
                    elif exp_id == max_id +1:
                        self._exp_group_name = test_group_name
                        self.exp_group = self.conn.require_group(test_group_name)
                    else:
                        raise ValueError('There is no experiement with given exp_id, name and sample name.')
                else:
                    for key in self.conn.keys():
                        if key.endswith(str(exp_id)):
                           self._exp_group_name = key 
                           self.exp_group = self.conn.require_group(key)

        else:
            name = name or f"test_experiment"
            sample_name = sample_name or f"test_sample"

            log.info(f"creating new experiment in {self.path_to_db}")

            self._exp_id = max_id+1
            self._exp_group_name = name+"#"+sample_name+"#"+str(self._exp_id)
            self.exp_group = self.conn.create_group(self._exp_group_name)

    @property
    def exp_id(self) -> int:
        return self._exp_id

    @property
    def path_to_db(self) -> str:
        return self.conn.filename
    
    @property
    def exp_group_name(self) -> str:
        return self.exp_group.name
    
    @property
    def name(self) -> str:
        return self.exp_name

    @property
    def exp_name(self) -> str:
        name_list = self._exp_group_name.split("#")
        return (name_list[0]).replace("/", "")

    @property
    def sample_name(self) -> str:
        name_list = self._exp_group_name.split("#")
        return name_list[1]

    @property
    def last_counter(self) -> int:
        return len(self.exp_group.keys())

    @property
    def started_at(self) -> int:
        return self.exp_group.attrs["start_time"]

    @property
    def finished_at(self) -> int:
        return self.exp_group.attrs["end_time"]

    def new_data_set(self, run_name: Optional[str],
                     specs: Optional[SpecsOrInterDeps] = None,
                     values: Optional[Values_type] = None,
                     metadata: Optional[Any] = None) -> HDF5DataSet:
        """
        Create a new dataset in this experiment

        Args:
            name: the name of the new dataset
            specs: list of parameters (as ParamSpecs) to create this data_set
                with
            values: the values to associate with the parameters
            metadata: the metadata to associate with the dataset
        """
        return new_data_set(run_name=run_name, 
                            exp_id=self.exp_id, 
                            specs=specs, 
                            values=values, 
                            metadata=metadata,
                            conn=self.conn)

    def data_set(self, counter: int) -> HDF5DataSet:
        """
        Get dataset with the specified counter from this experiment

        Args:
            counter: the counter of the run we want to load

        Returns:
            the dataset
        """
        run_id = counter
        return HDF5DataSet(exp_id=self._exp_id, run_id=run_id, conn=self.conn)

    def data_sets(self) -> List[HDF5DataSet]:
        """Get all the datasets of this experiment"""
        run_id_list = []
        for run_name in self.exp_group.keys():
            run_id_list.append(int(run_name.split("#")[-1]))
        
        return [HDF5DataSet(exp_id=self._exp_id, run_id=run_id, conn=self.conn) for run_id in run_id_list]

    def last_data_set(self) -> HDF5DataSet:
        """Get the last dataset of this experiment"""
        
        run_id = len(self.exp_group.keys())
        if run_id is None:
            raise ValueError('There are no runs in this experiment')
        return HDF5DataSet(exp_id=self._exp_id, run_id=run_id, conn=self.conn)

    def finish(self) -> None:
        """
        Marks this experiment as finished by saving the moment in time
        when this method is called
        """
        self.conn.flush()
        self.conn.close()

    def __len__(self) -> int:
        return len(self.data_sets())

    def __repr__(self) -> str:
        out = [
            f"{self.name}#{self.sample_name}#{self.exp_id}@{self.path_to_db}"
        ]
        out.append("-" * len(out[0]))
        out += [
            f"{d.run_id}-{d.name}-{d.counter}-{d.parameters}-{len(d)}"
            for d in self.data_sets()
        ]
        return "\n".join(out)


# public api

def experiments(conn: Optional[Connection] = None) -> List[Experiment]:
    """
    List all the experiments in the container (database file from config)

    Args:
        conn: connection to the database. If not supplied, a new connection
          to the DB file specified in the config is made

    Returns:
        All the experiments in the container
    """
    conn = conn or connect(get_DB_location())

    log.info(f"loading experiments from {conn.filename}")
    exp_group_name_list = conn.keys()
    exp_id_list = []
    if exp_group_name_list:
        for name in exp_group_name_list:
            exp_id_list.append(int(name.split("#")[-1]))
    else:
        raise ValueError('There are no experiments in the database file') 

    return [load_experiment(exp_id, conn) for exp_id in exp_id_list]


def new_experiment(name: str,
                   sample_name: Optional[str],
                   conn: Optional[Connection] = None) -> Experiment:
    """
    Create a new experiment (in the database file from config)

    Args:
        name: the name of the experiment
        sample_name: the name of the current sample
        format_string: basic format string for table-name
            must contain 3 placeholders.
        conn: connection to the database. If not supplied, a new connection
          to the DB file specified in the config is made
    Returns:
        the new experiment
    """
    conn = conn or connect(get_DB_location()) 
    return Experiment(name=name, sample_name=sample_name,
                      conn=conn)


def load_experiment(exp_id: int,
                    conn: Optional[Connection] = None) -> Experiment:
    """
    Load experiment with the specified id (from database file from config)

    Args:
        exp_id: experiment id
        conn: connection to the database. If not supplied, a new connection
          to the DB file specified in the config is made

    Returns:
        experiment with the specified id
    """
    conn = conn or connect(get_DB_location())
    if not isinstance(exp_id, int):
        raise ValueError('Experiment ID must be an integer')
    return Experiment(exp_id=exp_id,
                      conn=conn)


def load_last_experiment(conn: Optional[Connection] = None) -> Experiment:
    """
    Load last experiment (from database file from config)

    Returns:
        last experiment
    """
    conn = conn or connect(get_DB_location())
    if conn.keys():
        exp_group_name_list = conn.keys()
        exp_id_list = []
        for name in exp_group_name_list:
            exp_id_list.append(int(name.split("#")[-1]))
        last_exp_id = max(exp_id_list)
    else:
        raise ValueError('There are no experiments in the database file')
    return Experiment(exp_id=last_exp_id, conn=conn)


def load_experiment_by_name(name: str,
                            sample: Optional[str] = None,
                            conn: Optional[Connection]=None) -> Experiment:
    """
    Try to load experiment with the specified name.

    Nothing stops you from having many experiments with the same name and
    sample_name. In that case this won't work. And warn you.

    Args:
        name: the name of the experiment
        sample: the name of the sample
        conn: connection to the database. If not supplied, a new connection
          to the DB file specified in the config is made

    Returns:
        the requested experiment

    Raises:
        ValueError if the name is not unique and sample name is None.
    """
    conn = conn or connect(get_DB_location())
    prefix = name+"#"+sample+"#"
    exp_id_list = []

    if conn.keys():
        for exp_name in conn.keys():
            if exp_name.startswith(prefix):
                exp_id_list.append(int(exp_name.split("#")[-1]))
    
    if len(exp_id_list) == 0:
        raise ValueError("Experiment not found")
    elif len(exp_id_list) >1:
        last_exp_id = max(exp_id_list)
        e = Experiment(exp_id=last_exp_id, conn=conn)
        return e
    else:
        exp_id = exp_id_list[0]
        e = Experiment(exp_id=exp_id, conn=conn)
        return e

def load_or_create_experiment(experiment_name: str,
                              sample_name: Optional[str] = None,
                              conn: Optional[Connection]=None)->Experiment:
    """
    Find and return an experiment with the given name and sample name,
    or create one if not found.

    Args:
        experiment_name: Name of the experiment to find or create
        sample_name: Name of the sample
        conn: Connection to the database. If not supplied, a new connection
          to the DB file specified in the config is made

    Returns:
        The found or created experiment
    """
    
    conn = conn or connect(get_DB_location())
    try:
        experiment = load_experiment_by_name(experiment_name, sample_name,
                                             conn=conn)
    except ValueError as exception:
        if "Experiment not found" in str(exception):
            experiment = new_experiment(experiment_name, sample_name,
                                        conn=conn)
        else:
            raise exception
    return experiment

def create_experiment(experiment_name: str,
                    sample_name: Optional[str] = None,
                    conn: Optional[Connection]=None)->Experiment:
    
    conn = conn or connect(get_DB_location())
    experiment = new_experiment(name=experiment_name, 
                                sample_name=sample_name,
                                conn=conn)
    return experiment

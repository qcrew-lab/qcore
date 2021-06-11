from numpy import datetime_data
from qcodes.instrument.parameter import ParameterWithSetpoints
from experiment import load_or_create_experiment, create_experiment
from dataset_hdf5 import *
from measurement import Measurement
from qcodes import Parameter, Station, ArrayParameter
from database import initialise_today_database_at
from pathlib import Path
import qcodes as qc
import qcodes.utils.validators as vals
from numpy.random import rand

# from qcodes import initialise_or_create_database_at, \
#     load_or_create_experiment, Measurement, Parameter, \
#     Station
# from qcodes.dataset.plotting import plot_dataset
# database: h5 file
# group: a type of h5 structure similiar to the folder
# dataset: a type of h5 structure to store the data
# attrs: the group and dataset objects both have the attributes,
#        it can be addressed by ".attrs[__attrs_name__]"


##################################################################
# create dataset
##################################################################
# 1. If the h5 file with the given name is not given in the folder
#    named by today date,  It will create the folder named by the
#    date and the given "name".
# 2. When "exp_id" is not assigned, a new experiment group will be
#    created in the database (h5 file).
# 3. "is_new_exp" variable default to "False", the class "HDF5DataSet"
#    will create run group in the last group named by "exp_name".
#    If new experiment group is requried, "is_new_exp" should be assigned
#    to "True".
# 4. The experiment group naming convention follows
#    "exo_name#sample_name#exp_id"

# initialise the database
database_name = "test_database"
database_path = Path("C:\data")
initialise_today_database_at(name=database_name, path=database_path)
print(qc.config.core.db_location)

# load existing database
# from database import initialise_existing_database_at
# initialise_existing_database_at()

# create the station
station = Station()

# 1. if these are at least one group with name experiment and sample
#    name, it will load the last exp group with maximal exp_id
# 2. if these is no exp group with given experiment name and sample name
#    it will create a new one
experiment1 = load_or_create_experiment(
    experiment_name="time_rabi", sample_name="coax_A"
)

# create_experiment will create new exp group
# experiment2 = create_experiment(
#     experiment_name='greco',
#     sample_name='draco')

# single point data
x = Parameter(name="x", label="Voltage", unit="V", set_cmd=None, get_cmd=None)
t = Parameter(name="t", label="Time", unit="s", set_cmd=None, get_cmd=None)
y = Parameter(name="y", label="Voltage", unit="V", set_cmd=None, get_cmd=None)
y2 = Parameter(name="y2", label="Current", unit="A", set_cmd=None, get_cmd=None)

# 1 dimension data
n_points = Parameter("n_points", set_cmd=None, vals=vals.Ints())

# the number shoud be same if they are the setpoint of another parameter
n_points.set(5)


avg_n = Parameter("avg_n", set_cmd=None)
f = Parameter("f", get_cmd=None, vals=vals.Arrays(shape=(n_points,)))
a = Parameter("a", get_cmd=None, vals=vals.Arrays(shape=(n_points,)))
v = ParameterWithSetpoints(
    "v", get_cmd=None, setpoints=(f, a), vals=vals.Arrays(shape=(n_points,))
)
i_avg = ParameterWithSetpoints(
    "i_avg", get_cmd=None, setpoints=(f,), vals=vals.Arrays(shape=(n_points,))
)

meas = Measurement(exp=experiment1, name=database_name, station=station)

meas.register_parameter(v)
meas.register_parameter(a)
meas.register_parameter(f)
meas.register_parameter(avg_n)
meas.register_parameter(i_avg, setpoints=(avg_n,))

# f = Parameter('f', get_cmd=None, vals=vals.Arrays(shape=(n_points,)))
# a = Parameter('a', get_cmd=None, vals=vals.Arrays(shape=(n_points,)))
# v = Parameter('v', get_cmd=None, vals=vals.Arrays(shape=(n_points,)))
# meas.register_parameter(f)
# meas.register_parameter(a)
# meas.register_parameter(v, setpoints=(f, a))

meas.register_parameter(x)
meas.register_parameter(t)

meas.parameters

# set some parameters
x_val = 10000
t_val = 20000
f_vals = np.linspace(0, 10, 5)
a_vals = np.linspace(0, 2, 5)
v_vals = np.linspace(0, 0.1, 5)
raw_vals = np.linspace(0, 100, 5)


path_to_db = Path()
# 1. The command experiment.finish() close the connection to the h5File
#     and flush all data to the disk.
# 2. All the measurement and storage should be done before "finish()"
# 3. Individual datasaver context managers can used
with meas.run() as datasaver:

    # datasaver.add_result((f, f_vals), (a, a_vals), (v, v_vals))

    for i in np.linspace(0, 10, 11):
        datasaver.add_result(
            (avg_n, i), (i_avg, raw_vals), (f, f_vals)
        )  # raw_vals is the in each avg_n, the returned array
        # f is also setpoint of avg_n, so it should be assigned in the command
        datasaver.flush_data_to_database()
        # if the append the data to the previous data, must use flush_data_to_database()
    dataset_test = datasaver.dataset

    # get_parameter_data() cannot run
    # print(dataset_test)
    # print(dataset_test.description)

    path_to_db = Path(dataset_test.path_to_db)
    metadata = {"a": 50, "b": 100, "c": "unit"}
    dataset_test.add_metadata("config", metadata=metadata)
    dataset_test.get_parameter_data()

# # another meas.run() will create a new run group
# path_to_db = Path()
# with meas.run() as datasaver:
#     for i in range(10):
#         datasaver.add_result((x, x_vals), (t, t_vals))
#     dataset_test = datasaver.dataset
#
#     print(dataset_test)
#     path_to_db = Path(dataset_test.path_to_db)
#     print(dataset_test.path_to_db)
# experiment1.finish()

# Check the data in h5 file
import h5py

f = h5py.File(path_to_db)
print(f.keys())
f["time_rabi#coax_A#1"]
exp_group = f["time_rabi#coax_A#1"]
exp_group.keys()
run1_group = exp_group["run#19"]
run1_group.keys()
run1_group.attrs["metadata"]
run1_group.attrs.keys()
run1_group.attrs["run_timestamp"]
data_group = run1_group["data"]
data_group.keys()

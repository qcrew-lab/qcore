# Example scrpit to use database

# Important: at C:\Users\qcrew\anaconda3\envs\qcrew\Lib\site-packages\qm\__init__.py
# add from qm._results import MultipleNamedJobResult, SingleNamedJobResult

<<<<<<< HEAD
# TODO: when this script is open, it seems we can not open the file with h5py.File, but
#       the context manager has implemented the close() function. Need to check
#       Temporary solution is
from qcrew.experiments.sample_B.imports import *
from pathlib import Path
from matplotlib import pyplot as plt
from datetime import timedelta

import sys
import qcrew.experiments.sample_B.imports.stage
if "qcrew.experiments.sample_B.imports.stage" in sys.modules:
    print("True")
else:
    print("False")
    #print(sys.modules)

# # reload configuration and stage before each measurement run
# reload(cfg)
# reload(stg)

# from qcrew.codebase.datasaver.hdf5_helper import *
# from qcrew.codebase.datasaver.fetch_helper import *

# # ############################
# # # Constant
# # ############################
# rr = stg.rr
# qubit = stg.qubit
# DATAPATH_PATH = Path.cwd() / "data"
# EXP_NAME = "rr_spec"
# SAMPLE_NAME = "sample_B"
# PROJECT = "squeezed_cat"
# ############################
# #  Parameters
# ############################
# REPS = 2000
# WAIT_TIME = 10000  # in clock cycles

# # Measurement pulse
# rr = stg.rr
# F_START = -51e6
# F_STOP = -48e6
# F_STEP = 0.02e6
# rr_f_list = np.arange(F_START, F_STOP, F_STEP)
# sweep_points = len(rr_f_list)
# RR_ASCALE = 0.017
# RR_NAME = rr.name
# RR_OP = "readout"
# INTEGW1 = "integW1"  # integration weight for I
# INTEGW2 = "integW2"  # integration weight for Q
# # NOTE: The weights must be defined for the chosen measurement operation

# # Parameters for optional qubit pulse
# PLAY_QUBIT = False
# QUBIT_ASCALE = 1.0
# QUBIT_NAME = qubit.name
# QUBIT_IF = int(-48.35e6)  # IF frequency of qubit pulse
# QUBIT_OP = "gaussian"  # qubit operation as defined in config

# ############################
# # QUA program
# ############################
# with program() as rr_spec:
#     n = declare(int)
#     f = declare(int)
#     qubit_a = declare(fixed, value=QUBIT_ASCALE)
#     rr_a = declare(fixed, value=RR_ASCALE)
#     qubit_f = declare(int, value=QUBIT_IF)
#     play_qubit = declare(bool, value=PLAY_QUBIT)

#     I = declare(fixed)
#     Q = declare(fixed)
#     I_stream = declare_stream()
#     Q_stream = declare_stream()

#     with for_(n, 0, n < REPS, n + 1):  # outer averaging loop
#         with for_(f, F_START, f < F_STOP, f + F_STEP):  # inner frequency sweep
#             update_frequency(RR_NAME, f)
#             update_frequency(QUBIT_NAME, qubit_f)
#             play(QUBIT_OP * amp(qubit_a), QUBIT_NAME, condition=play_qubit)
#             align(QUBIT_NAME, RR_NAME)
#             measure(
#                 RR_OP * amp(rr_a),
#                 RR_NAME,
#                 None,
#                 demod.full(INTEGW1, I),
#                 demod.full(INTEGW2, Q),
#             )
#             wait(WAIT_TIME, RR_NAME)  # for rr to relax to vacuum state
#             save(I, I_stream)
#             save(Q, Q_stream)

#     with stream_processing():
#         I_stream.buffer(len(rr_f_list)).save_all("I_raw")
#         Q_stream.buffer(len(rr_f_list)).save_all("Q_raw")
#         I_stream.buffer(len(rr_f_list)).average().save("I_avg")
#         Q_stream.buffer(len(rr_f_list)).average().save("Q_avg")
#         I_stream.buffer(len(rr_f_list)).average().save_all("I_avg_raw")
#         Q_stream.buffer(len(rr_f_list)).average().save_all("Q_avg_raw")

# ############################
# # measurement
# ############################
# start_time = time.perf_counter()
# job = stg.qm.execute(rr_spec)

# # create the database (hdf5 file)
# db = initialise_database(
#     exp_name=EXP_NAME,
#     sample_name=SAMPLE_NAME,
#     project_name=PROJECT,
#     path=DATAPATH_PATH,
#     timesubdir=False,
#     timefilename=True,
# )

# with DataSaver(db) as datasaver:
#     ############################
#     # create figure
#     fig = plt.figure()
#     ax = fig.add_subplot(1, 1, 1)
#     hdisplay = display.display("", display_id=True)

#     ############################
#     # live fetch data and save
#     for (num_have_got, update_data_dict) in live_fetch(job=job, reps=REPS):
#         # group: create a group in hdf5 file
#         # it is more clear that we put the raw data and fit data in different group
#         datasaver.update_multiple_results(update_data_dict, group="data")

#         ############################
#         # live plot
#         counter = counter + len(update_data_dict["I_avg_raw"])
#         signal = get_last_average_data(
#             data=update_data_dict, i_tag="I_avg_raw", q_tag="Q_avg_raw"
#         )

#         ax.clear()
#         ax.plot(rr_f_list, signal)
#         params = plot_fit(rr_f_list, signal, ax, fit_func="lorentzian")
#         ax.set_title("Resonator spectroscopy, average of %d results" % (num_have_got))
#         ax.set_xlabel("Frequency (Hz)")
#         ax.set_ylabel("Signal amplitude")

#         # update figure
#         hdisplay.update(fig)

#     ############################
#     # fetch final average data
#     final_data_dict = final_fetch(job=job)
#     datasaver.add_multiple_results(final_data_dict, group="data")

#     #################################
#     # save figure
#     plt.show()
#     save_figure(fig, db)

# ############################
# # finish measurement
# ############################

# print(job.execution_report())
# elapsed_time = time.perf_counter() - start_time
# print(f"\nExecution time: {str(timedelta(seconds=elapsed_time))}")
=======
# According to http://python-notes.curiousefficiency.org/en/latest/python_concepts/import_traps.html
# "Never add a package directory, or any directory inside a package, directly to the Python path"
# 1.  "__init__" can import some modules, but no need to import stage 
# 2. I suggest to import general package in this script, so we can know the naming convention that we 
#    are using. In the "__init__" it only import the relative modules in the subfolder 
import sys
import numpy as np
from pathlib import Path
from importlib import reload
from qm.qua import*

if qcrew.experiments.sample_B.imports.stage not in sys.modules:
    import qcrew.experiments.sample_B.imports.stage as stage
else:
    reload(stage)

##############        INFO      ##############
PROJECT = "squeezed_cat"
EXP_NAME = "power_rabi"
SAMPLE_NAME =  "sample_B"
DATAPBASE_PATH = Path.cwd() / "data"

############     PARAMETERS        ############
# 1. which is better, abbreviation or complete writing
# 2. I suggest that we can package the metadata as a class 
# 3. The variable tag is not necessary, the fetcher will get all data 
mdata = {  
    "reps": 40000,  # number of sweep repetitions
    "wait": 50000,  # in ns (mutiple of 4)
    "a_start": -2.0,  #
    "a_stop": 2.0,
    "a_step": 0.1,
    "qubit_op": "gaussian", 
    "rr_op": "readout",  
    "rr_op_ampx": 0.2,  
    "fit_fn": "sine",  
    "rr_lo_freq": stage.rr.lo_freq, 
    "rr_int_freq": stage.rr.int_freq, 
    "qubit_lo_freq": stage.qubit.lo_freq,  
    "qubit_int_freq": stage.qubit.int_freq,  
}

a_list = np.arange(mdata["a_start"], mdata["a_stop"], mdata["a_step"])  
mdata["sweep_len"] = len(a_list) 

############     QUA PROGRAM        ############

with program() as power_rabi:
    
    # 1. I suggest to create a sweep variable stream, so that we can test
    #    the sweep variable with our settings and store the sweep variable 
    #    in datasaver class automatically 
    # 2. I suggest to use the complete naming, e.g. I_stream rather I_st
    n = declare(int)  
    a = declare(fixed) 
    I = declare(fixed)
    Q = declare(fixed)  
    I_stream = declare_stream()
    Q_stream = declare_stream()
    a_stream = declare_stream()

    # I don't think using dict directly in the qua program is a good chose
    # I hope the qua program should be more universal
    # perhaps, the future metadata class can imports these constants automatically
    with for_(n, 0, n < mdata["reps"], n + 1): 
        with for_(a, mdata["a_start"], a < mdata["a_stop"], a + mdata["a_step"]):
            play(mdata["qubit_op"] * amp(a), stg.qubit.name)
            align(stg.qubit.name, stg.rr.name)
            measure(
                mdata["rr_op"] * amp(mdata["rr_op_ampx"]),
                stg.rr.name,
                None,
                demod.full("integW1", I),
                demod.full("integW2", Q),
            )
            wait(int(mdata["wait"] // 4), stg.qubit.name)
            save(I, I_st)
            save(Q, Q_st)
            save(a, a_st)


    # no need to list the save_all() separately, the stream terminated with save() or save_all()
    with stream_processing():
        a_stream.buffer(mdata["sweep_len"]).save("a")
        I_raw, Q_raw = I_st.buffer(mdata["sweep_len"]), Q_st.buffer(mdata["sweep_len"])
        I_raw.save_all(datatags[0])  # save raw I values
        Q_raw.save_all(datatags[1])  # save raw Q values

        # Is the stream calculation supported by qm? 
        (I_raw * I_raw + Q_raw * Q_raw).save_all(datatags[2])  # save y^2 to get std err
        I_avg, Q_avg = I_raw.average(), Q_raw.average()  # get running averages
        (I_avg * I_avg + Q_avg * Q_avg).save_all(datatags[3])  # save avg y^2
############################
# measurement
############################
start_time = time.perf_counter()
job = stage.qm.execute(power_rabi)

# create the database (hdf5 file)
db = initialise_database(exp_name=EXP_NAME, 
                         sample_name=SAMPLE_NAME, 
                         project_name = PROJECT,
                         path = DATAPATH_PATH,
                         timesubdir=False, timefilename = True)

with DataSaver(db) as datasaver:
    ############################
    # create figure
    fig = plt.figure()
    ax = fig.add_subplot(1, 1, 1)
    hdisplay = display.display("", display_id=True)
    

    # 1. in your script, though your fetcher funciton is easy, the loop 
    #    in this script is not simple 

    # 2. the fit also can be packaged as the fucntion
    # 3. I don't think the class is necessary. fetch, plot, fit are just
    #    some helper functions, no need to use class 
    ############################
    # live fetch data and save
    for (num_have_got, update_data_dict) in live_fetch(job=job, reps=REPS):
        # group: create a group in hdf5 file
        # it is more clear that we put the raw data and fit data in different group
        datasaver.update_multiple_results(update_data_dict, group="data")
        
        ############################
        # live plot
        counter = counter + len(update_data_dict["I_avg_raw"])
        signal = get_last_average_data(data=update_data_dict,
                                       i_tag="I_avg_raw", 
                                       q_tag="Q_avg_raw")
        
        ax.clear()
        ax.plot(rr_f_list, signal)
        params = plot_fit(rr_f_list, signal, ax, fit_func="lorentzian")
        ax.set_title("Resonator spectroscopy, average of %d results" % (num_have_got))
        ax.set_xlabel("Frequency (Hz)")
        ax.set_ylabel("Signal amplitude")

        # update figure
        hdisplay.update(fig)
    
    ############################
    # fetch final average data
    final_data_dict = final_fetch(job=job)
    datasaver.add_multiple_results(final_data_dict, group = "data")
    
    #################################          
    # save figure
    save_figure(db)

############################
# finish measurement
############################

#  I will integrate the time counting in the Datasaver class 
print(job.execution_report())
elapsed_time = time.perf_counter() - start_time
print(f"\nExecution time: {str(timedelta(seconds=elapsed_time))}")
>>>>>>> 95c065a1cbfd95c68366ab59964618dae0359532

# Example scrpit to use database

from qcrew.experiments.sample_B.imports import *

from datetime import datetime, date, timedelta
import scipy as sc
from numpy import datetime_data

# import database
from qcrew.codebase.database.dataset_hdf5 import *
from qcrew.codebase.database.database import initialise_today_database_at
from pathlib import Path

reload(cfg)  # reload configuration and stage before each measurement run
reload(stg)

# ############################
# # Constant
# ############################
rr = stg.rr
qubit= stg.qubit
DATABASE_NAME = "sample_B_database"
DATAPATH_PATH = Path.cwd() / "data"
EXP_NAME = "rr_spec"
SAMPLE_NAME = "sample_B"

############################
#  Parameters
############################
# Loop parameters
REPS = 1000
WAIT_TIME = 10000  # in clock cycles

# Measurement pulse
rr = stg.rr
F_START = -51e6
F_STOP = -48e6
F_STEP = 0.01e6
rr_f_list = np.arange(F_START, F_STOP, F_STEP)
sweep_points = len(rr_f_list)
RR_ASCALE = 0.017
RR_NAME = rr.name
RR_OP = "readout"
INTEGW1 = "integW1"  # integration weight for I
INTEGW2 = "integW2"  # integration weight for Q
# NOTE: The weights must be defined for the chosen measurement operation

# Parameters for optional qubit pulse
PLAY_QUBIT = False
QUBIT_ASCALE = 1.0
QUBIT_NAME =  qubit.name
QUBIT_IF = int(-48.35e6)  # IF frequency of qubit pulse
QUBIT_OP = "gaussian"  # qubit operation as defined in config

############################
# QUA program
############################
with program() as rr_spec:
    n = declare(int)
    f = declare(int)
    qubit_a = declare(fixed, value=QUBIT_ASCALE)
    rr_a = declare(fixed, value=RR_ASCALE)
    qubit_f = declare(int, value=QUBIT_IF)
    play_qubit = declare(bool, value = PLAY_QUBIT)

    I = declare(fixed)
    Q = declare(fixed)
    I_stream = declare_stream()
    Q_stream = declare_stream()

    with for_(n, 0, n < REPS, n + 1):  # outer averaging loop
        with for_(f, F_START, f < F_STOP, f + F_STEP):  # inner frequency sweep
            update_frequency(RR_NAME, f)
            update_frequency(QUBIT_NAME, qubit_f)
            play(QUBIT_OP * amp(qubit_a), QUBIT_NAME, condition=play_qubit)
            align(QUBIT_NAME, RR_NAME)
            measure(
                RR_OP * amp(rr_a),
                RR_NAME,
                None,
                demod.full(INTEGW1, I),
                demod.full(INTEGW2, Q),
            )
            wait(WAIT_TIME, RR_NAME)  # for rr to relax to vacuum state
            save(I, I_stream)
            save(Q, Q_stream)

    with stream_processing():
        I_stream.buffer(len(rr_f_list)).save_all("I_raw")
        Q_stream.buffer(len(rr_f_list)).save_all("Q_raw")
        I_stream.buffer(len(rr_f_list)).average().save("I_avg")
        Q_stream.buffer(len(rr_f_list)).average().save("Q_avg")


############################
# measurement
############################
    
    #############################
    # implement the job
    job = stg.qm.execute(rr_spec)  # run measurement
    print(f"{EXP_NAME} in progress...")  # log message
    handle = job.result_handles


    # individual result handle
    result_I_raw = handle.get("I_raw")
    result_Q_raw = handle.get("Q_raw")
    result_I_avg = handle.get("I_avg")
    result_Q_avg = handle.get("Q_avg")
             
    ############################ 
    # create figure
    fig = plt.figure()
    ax = fig.add_subplot(1, 1, 1)
    hdisplay = display.display("", display_id=True)
    
    ############################ 
    # live plotting
    # live saving
    with... : (the live part)
    num_have_got = -1
    while handle.is_processing() or num_have_got < REPS:


        step 1: fetch available data 

        step 2: datasaver.add_results(latest block of results )

        step 3: plot and update figure (same as what we are doing right now)
    

    
    # flush to hdf5 file
    datasaver.flush_data_to_database()
    
     ###############################
    # store the metadata
    dataset = datasaver.dataset
    # store the created metadata dict
    dataset.add_metadata("metadata", metadata=metadata)



print(job.execution_report())
elapsed_time = time.perf_counter() - start_time
print(f"\nExecution time: {str(timedelta(seconds=elapsed_time))}")
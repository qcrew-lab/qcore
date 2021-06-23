# Example scrpit to use database

from qcrew.experiments.sample_B.imports import *

# import database
from qcrew.codebase.database.experiment import load_or_create_experiment,create_experiment
from qcrew.codebase.database.dataset_hdf5 import *
from qcrew.codebase.database.measurement import Measurement
from qcrew.codebase.database.database import initialise_today_database_at
from pathlib import Path
from matplotlib import pyplot as plt

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

# database has function to store creation time and finishing time
# it is shown in terminal, no need to store
start_time = time.perf_counter()
############################
#  Initilization
############################
# initilise the database
initialise_today_database_at(name=DATABASE_NAME, path=DATAPATH_PATH)
print(qc.config.core.db_location)
#structure: data/main_proj_folder (e.g. squeezed cat)/folder (today's date)/file_name.h5 (file_name = timestamp_expname_others)

# create experiment
rr_spectroscopy = load_or_create_experiment(
    experiment_name=EXP_NAME, sample_name=SAMPLE_NAME
)
# comment: get rid of this. We do not wnat to use the qcodes expeirment class now. 

# create the station
# "station" is the group of the instruments
station = Station()
#get rid of this, we have our own (e.g. the stage) - already has some meta data saving v3. to disuss with Atharv. 

# create measurement
meas = Measurement(exp=rr_spectroscopy, name=DATABASE_NAME, station=station)
# remove this, we do not want to re-instanciate another meausrement. Also, we want to elimate the dependency on the qcodes Measurment.py class object. 

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
# Metadata dict
############################

metadata = {  # metadata dict, set measurement parameters here
    "reps": REPS,  # number of sweep repetitions
    "wait_time": WAIT_TIME,  # delay between reps in ns, an integer multiple of 4 >= 16
    "f_start": F_START,  # frequency sweep range is set by f_start, f_stop, and f_step
    "f_stop": F_STOP,
    "f_step": F_STEP,
    "r_ampx": 0.25,  # readout pulse amplitude votlage
    "rr_op": RR_OP,  # readout pulse name as defined in the config
    "fit_func_name": "lorentzian",  # name of the fit function
    "rr_lo_freq": cfg.rr_LO,  # frequency of local oscillator driving rr
    "rr_int_freq": cfg.rr_IF,  # frequency played by OPX to rr
    "sweep_len": len(rr_f_list),
}

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
        I_stream.buffer(len(rr_f_list)).average().save_all("I_avg_raw")
        Q_stream.buffer(len(rr_f_list)).average().save_all("Q_avg_raw")

############################
# measurement
############################
job = stg.qm.execute(rr_spec) 
            

with datasaver:
    ############################ 
    # create figure
    fig = plt.figure()
    ax = fig.add_subplot(1, 1, 1)
    hdisplay = display.display("", display_id=True)

    for update_data_dict in live_fetch(job=job, reps=REPS):
        datasaver.update_multiple_results(update_dict, group="data")
    
    
    ax.clear()
    ax.plot(rr_f_list, avg_v_so_far)
    params = plot_fit(rr_f_list, avg_v_so_far, ax, fit_func="lorentzian")
    ax.set_title("Resonator spectroscopy, average of %d results" % (num_so_far))
    ax.set_xlabel("Frequency (Hz)")
    ax.set_ylabel("Signal amplitude")

    # update figure
    hdisplay.update(fig)

    final_data_dict = final_fetch(jo=job)
    datasaver.add_multiple_results(final_data_dict, group = "data")
   
    
    #################################          
    # save figure
    filename = EXP_NAME + "_" + SAMPLE_NAME + "_run" + str(dataset.run_id) + ".png"
    full_path = Path(dataset.path_to_db).parent.absolute() / filename
    plt.savefig(full_path, format="png", dpi=600)
    print(f"Plot saved at {full_path}")

############################
# finish measurement
############################

print(job.execution_report())
elapsed_time = time.perf_counter() - start_time
print(f"\nExecution time: {str(timedelta(seconds=elapsed_time))}")
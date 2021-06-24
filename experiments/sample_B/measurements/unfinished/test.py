# Example scrpit to use database

# Important: at C:\Users\qcrew\anaconda3\envs\qcrew\Lib\site-packages\qm\__init__.py
# add from qm._results import MultipleNamedJobResult, SingleNamedJobResult

# TODO: when this script is open, it seems we can not open the file with h5py.File, but
#       the context manager has implemented the close() function. Need to check
#       Temporary solution is 
from qcrew.experiments.sample_B.imports import *
from pathlib import Path
from matplotlib import pyplot as plt
from datetime import timedelta
# reload configuration and stage before each measurement run
reload(cfg)
reload(stg)

from qcrew.codebase.datasaver.hdf5_helper import*
from qcrew.codebase.datasaver.fetch_helper import*
# ############################
# # Constant
# ############################
rr = stg.rr
qubit= stg.qubit
DATAPATH_PATH = Path.cwd() / "data"
EXP_NAME = "rr_spec"
SAMPLE_NAME = "sample_B"
PROJECT = "squeezed_cat"
############################
#  Parameters
############################
REPS = 2000
WAIT_TIME = 10000  # in clock cycles

# Measurement pulse
rr = stg.rr
F_START = -51e6
F_STOP = -48e6
F_STEP = 0.02e6
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
        I_stream.buffer(len(rr_f_list)).average().save_all("I_avg_raw")
        Q_stream.buffer(len(rr_f_list)).average().save_all("Q_avg_raw")

############################
# measurement
############################
start_time = time.perf_counter()
job = stg.qm.execute(rr_spec)

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
    plt.show()
    save_figure(db)

############################
# finish measurement
############################

print(job.execution_report())
elapsed_time = time.perf_counter() - start_time
print(f"\nExecution time: {str(timedelta(seconds=elapsed_time))}")
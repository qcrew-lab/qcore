# Example scrpit to use database

from qcrew.experiments.sample_B.imports import *

from datetime import datetime, date, timedelta
import scipy as sc
from numpy import datetime_data

# import qcodes
from qcodes.instrument.parameter import ParameterWithSetpoints
from qcodes import Parameter, Station, ArrayParameter
import qcodes.utils.validators as vals

import qcodes as qc

# import database
from qcrew.codebase.database.experiment import load_or_create_experiment,create_experiment
from qcrew.codebase.database.dataset_hdf5 import *
from qcrew.codebase.database.measurement import Measurement
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


''''
n_points = Parameter('n_points',
                    unit='',
                    initial_value=5000,
                    vals=vals.Ints(),
                    get_cmd=None,
                    set_cmd=None)

n_points.set(sweep_points)

rr_if = Parameter("rr_if",
                    unit='Hz',
                    label='Freq Axis',
                    vals=vals.Arrays(shape=(sweep_points,)))

reps = Parameter("reps", get_cmd=None)
''''
# We dont need this for saving these experimental parameters. 


# https://github.com/QCoDeS/Qcodes/blob/master/docs/examples/Parameters/Simple-Example-of-ParameterWithSetpoints.ipynb
I_raw = ParameterWithSetpoints(
    "I_raw", get_cmd=None, setpoints=(rr_if,), vals=vals.Arrays(shape=(sweep_points,))
)
Q_raw = ParameterWithSetpoints(
    "Q_raw", get_cmd=None, setpoints=(rr_if,), vals=vals.Arrays(shape=(sweep_points,))
)
v_raw = ParameterWithSetpoints(
    "v_raw", get_cmd=None, setpoints=(rr_if,), vals=vals.Arrays(shape=(sweep_points,))
)
I_avg = ParameterWithSetpoints(
    "I_avg", get_cmd=None, setpoints=(rr_if,), vals=vals.Arrays(shape=(sweep_points,))
)
Q_avg = ParameterWithSetpoints(
    "Q_avg", get_cmd=None, setpoints=(rr_if,), vals=vals.Arrays(shape=(sweep_points,))
)
v_avg = ParameterWithSetpoints(
    "v_avg", get_cmd=None, setpoints=(rr_if,), vals=vals.Arrays(shape=(sweep_points,))
)
I_avg_raw = ParameterWithSetpoints(
    "I_avg_raw", get_cmd=None, setpoints=(rr_if,), vals=vals.Arrays(shape=(sweep_points,))
)
Q_avg_raw = ParameterWithSetpoints(
    "Q_avg_raw", get_cmd=None, setpoints=(rr_if,), vals=vals.Arrays(shape=(sweep_points,))
)
v_avg_raw = ParameterWithSetpoints(
    "v_avg_raw", get_cmd=None, setpoints=(rr_if,), vals=vals.Arrays(shape=(sweep_points,))
)
std_error = ParameterWithSetpoints(
    "std_error", get_cmd=None, setpoints=(rr_if,), vals=vals.Arrays(shape=(sweep_points,))
)
meas.register_parameter(rr_if)
meas.register_parameter(reps)
meas.register_parameter(I_avg)
meas.register_parameter(Q_avg)
meas.register_parameter(v_avg)
meas.register_parameter(I_raw, setpoints=(reps,))
meas.register_parameter(Q_raw, setpoints=(reps,))
meas.register_parameter(v_raw, setpoints=(reps,))
meas.register_parameter(I_avg_raw, setpoints=(reps,))
meas.register_parameter(Q_avg_raw, setpoints=(reps,))
meas.register_parameter(v_avg_raw, setpoints=(reps,))
meas.register_parameter(std_error, setpoints=(reps,))
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
with meas.run() as datasaver: #this handles opening and closing files, but we do not need to have dependencies on the mesaurement class. 

    #############################
    # implement the job
    job = stg.qm.execute(rr_spec)  # run measurement
    print(f"{EXP_NAME} in progress...")  # log message
    handle = job.result_handles

    ############################ 
    # individual result handle
    result_I_raw = handle.get("I_raw")
    result_Q_raw = handle.get("Q_raw")
    result_I_avg_raw = handle.get("I_avg_raw")
    result_Q_avg_raw = handle.get("Q_avg_raw")
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
    num_have_got = -1
    while handle.is_processing() or num_have_got < REPS:
        num_so_far = result_I_raw.count_so_far()
        test = result_I_raw.fetch_all(flat_struct=True)

        #step 1: fetch available data 
        #step 2: datasaver.add_results()

        # same as: num_so_far = len(result_I_raw)  # get result count so far
        if (num_so_far - num_have_got > 0) and num_so_far > 1:
            sliced_result_I_raw = result_I_raw.fetch(slice(num_have_got + 1, num_so_far +1), flat_struct=True)
            sliced_result_Q_raw = result_Q_raw.fetch(slice(num_have_got + 1, num_so_far+1), flat_struct=True)
            sliced_result_I_avg_raw = result_I_avg_raw.fetch(slice(num_have_got + 1, num_so_far +1), flat_struct=True)
            sliced_result_Q_avg_raw = result_Q_avg_raw.fetch(slice(num_have_got + 1, num_so_far +1), flat_struct=True)

            # "num_so_far + 1" make sure num_so_far is inclusive
            '''
            for index in range(num_have_got + 1, num_so_far):

                # live saving the raw data of I and Q and abs(I+jQ) 

                datasaver.add_result(
                    # the repetition number starts from 1, slice starts from 0
                    (reps,index + 1),
                    (I_raw, sliced_result_I_raw[index - num_have_got -1]),
                    (Q_raw, sliced_result_Q_raw[index - num_have_got -1]),
                    (v_raw, np.abs(sliced_result_I_raw[index - num_have_got -1]
                            + 1j * sliced_result_Q_raw[index - num_have_got -1])),(rr_if, rr_f_list))
                
                # live save the averaged I and Q and abs(I+jQ)
                # each list is the averaged over previous repetition
                datasaver.add_result(
                    (reps,index + 1), 
                    (I_avg_raw, sliced_result_I_avg_raw[index - num_have_got -1]),
                    (Q_avg_raw, sliced_result_Q_avg_raw[index - num_have_got -1]),
                    (v_avg_raw,np.abs(sliced_result_I_avg_raw[index - num_have_got -1]
                            + 1j * sliced_result_Q_avg_raw[index - num_have_got -1])),(rr_if, rr_f_list))
            ''' #redundant 
            
            # update the num_have_got to the current fetch number
            num_have_got = num_so_far

            # the last averaged to plot 
            avg_v_so_far = np.abs(sliced_result_I_avg_raw[-1] + 1j * sliced_result_Q_avg_raw[-1])

            # clear figure and update plot
            ax.clear()
            ax.plot(rr_f_list, avg_v_so_far)
            params = plot_fit(rr_f_list, avg_v_so_far, ax, fit_func="lorentzian")
            ax.set_title("Resonator spectroscopy, average of %d results" % (num_so_far))
            ax.set_xlabel("Frequency (Hz)")
            ax.set_ylabel("Signal amplitude")

            # update figure
            hdisplay.update(fig)
            
            datasaver.flush_data_to_database()

            # update frequency
            time.sleep(3)  # add a short delay before next plot refresh
    
    # # save the last single average result
    # handle.wait_for_all_values()
    # last_I_avg = result_I_avg.fetch_all(flat_struct=True)  # same as fetch
    # last_Q_avg = result_Q_avg.fetch_all(flat_struct=True)  # same as fetch
    # datasaver.add_result((f, rr_f_list), (I_avg, last_I_avg), (Q_avg, last_Q_avg))

    # # calculate std error from raw data
    # all_result_I_raw = result_I_raw.fetch_all(flat_struct=True)
    # all_result_Q_raw = result_Q_raw.fetch_all(flat_struct=True)
    # signal_raw = np.abs(all_result_I_raw + 1j * all_result_Q_raw)
    # std_error_vs_f = sc.stats.sem(signal_raw, axis=0)
    # datasaver.add_result((std_error, std_error_vs_f))
    
    # # flush to hdf5 file
    # datasaver.flush_data_to_database()
    
     ###############################
    # store the metadata
    dataset = datasaver.dataset
    # store the created metadata dict
    dataset.add_metadata("metadata", metadata=metadata)

    # # store the qua config
    # dataset.add_metadata("config", metadata=cfg.config)
    
    # # store fit
    # fit_parameter = {}
    # fit_params = fit.do_fit(metadata["fit_func_name"], freqs, signal_avg)  
    # ys_fit = fit.eval_fit(metadata["fit_func_name"], fit_params, freqs)  
    # for (name,value,) in fit_params.valuesdict().items(): 
    #     fit_parameter[f"fit_parameter_{name}"] = value

    # dataset.add_metadata("fit", metadata=fit_parameter)
    
    #################################          
    # save figure
    filename = EXP_NAME + "_" + SAMPLE_NAME + "_run" + str(dataset.run_id) + ".png"
    full_path = Path(dataset.path_to_db).parent.absolute() / filename
    plt.savefig(full_path, format="png", dpi=600)
    print(f"Plot saved at {full_path}")

############################
# finish measurement
############################
rr_spectroscopy.finish()

print(job.execution_report())
elapsed_time = time.perf_counter() - start_time
print(f"\nExecution time: {str(timedelta(seconds=elapsed_time))}")
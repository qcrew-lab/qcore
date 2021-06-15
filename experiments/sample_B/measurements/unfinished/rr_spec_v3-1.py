""" Resonator spectroscopy measurement script v3.0 """

from qcrew.experiments.coax_test.imports import *


from qcrew.experiments.sample_B.imports import *

from numpy import datetime_data
from qcodes.instrument.parameter import ParameterWithSetpoints
from qcodes import Parameter, Station, ArrayParameter
import qcodes as qc
import qcodes.utils.validators as vals


from qcrew.database.experiment import load_or_create_experiment, create_experiment
from qcrew.database.dataset_hdf5 import *
from qcrew.database.measurement import Measurement
from qcrew.database.database import initialise_today_database_at
from pathlib import Path

reload(cfg)  # reload configuration and stage before each measurement run
reload(stg)

############################      
# TOP LEVEL CONSTANTS        
############################
DATABASE_NAME = "test_database"
DATAPATH_PATH = Path.cwd()
EXP_NAME = "rr_spec"  
SAMPLE_NAME = "sample_B"
rr = stg.rr  
start_time = time.perf_counter()  

############################
#  Initilization         
############################
# initilise the database
initialise_today_database_at(name=DATABASE_NAME, path=DATAPATH_PATH)
print(qc.config.core.db_location)

# create experiment
rr_spectroscopy = load_or_create_experiment(
    experiment_name=EXP_NAME, sample_name=SAMPLE_NAME)

# create the station
station = Station()

# create measurement 
meas = Measurement(exp=rr_spectroscopy, name=DATABASE_NAME, station=station)
############################
#  Parameters        
############################
F_START = int(-50.5e6)
F_STOP = int(-48e6)
F_STEP = int(0.02e6)
REPS = 4000
WAIT_TIME = 50000
RR_ASCALE = 1
RR_LO = cfg.rr_LO
RR_OPERATION = "readout"
INTEG_WEIGHT1 = "integW1"
INTEG_WEIGHT2 = "integW2"
f_vals = np.arange(F_START,F_STOP. STEP)

n_points = Parameter("n_points", set_cmd=None, vals=vals.Ints())
n_points.set(len(f_vals))

f = Parameter("f", get_cmd=None, vals=vals.Arrays(shape=(n_points,)))
reps = Parameter("reps", get_cmd=None)

# https://github.com/QCoDeS/Qcodes/blob/master/docs/examples/Parameters/Simple-Example-of-ParameterWithSetpoints.ipynb
I_raw = ParameterWithSetpoints(
    "I_raw", get_cmd=None, setpoints=(f, ), vals=vals.Arrays(shape=(n_points,)))
Q_raw = ParameterWithSetpoints(
    "Q_raw", get_cmd=None, setpoints=(f, ), vals=vals.Arrays(shape=(n_points,)))
v_raw = ParameterWithSetpoints(
    "v_raw", get_cmd=None, setpoints=(f, ), vals=vals.Arrays(shape=(n_points,)))
I_avg = ParameterWithSetpoints(
    "I_avg", get_cmd=None, setpoints=(f, ), vals=vals.Arrays(shape=(n_points,)))
Q_avg = ParameterWithSetpoints(
    "Q_avg", get_cmd=None, setpoints=(f, ), vals=vals.Arrays(shape=(n_points,)))
v_avg = ParameterWithSetpoints(
    "v_avg", get_cmd=None, setpoints=(f, ), vals=vals.Arrays(shape=(n_points,)))
I_avg_raw = ParameterWithSetpoints(
    "I_avg_raw", get_cmd=None, setpoints=(f, ), vals=vals.Arrays(shape=(n_points,)))
Q_avg_raw = ParameterWithSetpoints(
    "Q_avg_raw", get_cmd=None, setpoints=(f, ), vals=vals.Arrays(shape=(n_points,)))
v_avg_raw = ParameterWithSetpoints(
    "v_avg_raw", get_cmd=None, setpoints=(f, ), vals=vals.Arrays(shape=(n_points,)))
std_error = ParameterWithSetpoints(
    "std_error", get_cmd=None, setpoints=(f, ), vals=vals.Arrays(shape=(n_points,)))
meas.register_parameter(f)
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
############################        
# Metadata dict      
############################

metadata = {  # metadata dict, set measurement parameters here
    "reps": REPS,  # number of sweep repetitions
    "wait_time": WAIT_TIME,  # delay between reps in ns, an integer multiple of 4 >= 16
    "f_start": F_START,  # frequency sweep range is set by f_start, f_stop, and f_step
    "f_stop": F_STOP,
    "f_step": F_STEP,
    "r_ampx": 0.25,  # readout pulse amplitude scale factor
    "rr_op": RR_OPERATION,  # readout pulse name as defined in the config
    "fit_func_name": "lorentzian",  # name of the fit function
    "rr_lo_freq": cfg.rr_LO,  # frequency of local oscillator driving rr
    "rr_int_freq": cfg.rr_IF,  # frequency played by OPX to rr
    "sweep_len": len(f_vals)
}

############################        
# QUA program
############################
with program() as rr_spec:

    #####################        QUA VARIABLE DECLARATIONS        ######################

    n = declare(int)  # averaging loop variable
    f = declare(int)  # frequency sweep variable
    rr_a = declare(fixed, value= RR_ASCALE)

    I, Q = declare(fixed), declare(fixed)  # result variables
    I_st, Q_st = declare_stream(), declare_stream()  # to save result variables

    #######################        MEASUREMENT SEQUENCE        #########################

    with for_(n, 0, n < REPS, n + 1):  # outer averaging loop, inner freq sweep
        with for_(f, F_START, f <F_STEP, f + F_STEP):
            update_frequency(rr.name, f)
            measure(
                RR_OPERATION * amp(rr_a),
                rr.name,
                None,
                demod.full(INTEG_WEIGHT1, I),
                demod.full(INTEG_WEIGHT2, Q),
            )
            wait(int(WAIT_TIME // 4), rr.name)
            save(I, I_st)
            save(Q, Q_st)

    #####################        RESULT STREAM PROCESSING        #######################

    with stream_processing():
        # save all raw I and Q values
        I_raw_st = I_st.buffer(n_points)
        Q_raw_st = Q_st.buffer(n_points)
        I_raw_st.save_all("I_raw")
        Q_raw_st.save_all("Q_raw")
   
        # save final averaged I and Q values
        I_avg_st = I_st.buffer(n_points).average()
        Q_avg_st = Q_st.buffer(n_points).average()
        I_avg_st.save("I_avg")
        Q_avg_st.save("Q_avg")
        I_avg_st.save_all("I_avg_raw")
        Q_avg_st.save_all("Q_avg_raw")
        
        # not sure if it works 
        # I thinks the power of FPGA may be liminted, so we can do this calculation on our PC 
        # But if QUA calucation is done by the server, it should be ok 

        # compute signal^2 from raw I and Q values for calculating mean standard error
        (I_raw_st * I_raw_st + Q_raw_st * Q_raw_st).save_all("signal_square_raw")

        # in this case, seems "save" is equivalent to "save_all"
        # compute signal^2 from running averages of I and Q values for live plotting
        (I_avg_st * I_avg_st + Q_avg_st * Q_avg_st).save_all("signal_square_avg")

############################        
# measurement
############################
with meas.run() as datasaver:
    
    #############################        RUN MEASUREMENT        ############################
    job = stg.qm.execute(rr_spec)  # run measurement
    print(f"{exp_name} in progress...")  # log message
    handle = job.result_handles

    ############################            POST-PROCESSING         ########################
    # result_handle
    result_I_raw = handle.get("I_raw")
    result_Q_raw = handle.get("Q_raw")
    result_I_avg_raw = handle.get("I_avg_raw")
    result_Q_avg_raw = handle.get("Q_avg_raw")
    result_I_avg = handle.get("I_avg")
    result_Q_avg = handle.get("Q_avg")

    # figure
    fig = plt.figure(figsize=(10, 8))
    ax = fig.add_subplot(1, 1, 1)
    hdisplay = display.display("", display_id=True)

    num_have_got = -1 
    # to shorter the code, if we set it initially as -1 , slice(num_have_got+1, num_so_far) is always working
    #  while handle.is_processing(): seems not good
    # 1. it will iterate too quickly
    # 2. once the job is finished, the condition will become False, but there may be several last data 
    #    that haven't been stored
    # 3. change to current "or" condition
    while handle.is_processing() or num_have_got < REPS: 

        num_so_far = result_I_raw.count_so_far()
        # same as: num_so_far = len(result_I_raw)  # get result count so far
        
    
        if (num_so_far - num_have_got > 0): 
            sliced_result_I_raw = result_I_raw.fetch(slice(num_have_got+1, num_so_far), flat_struct=True)
            sliced_result_Q_raw = result_Q_raw.fetch(slice(num_have_got+1, num_so_far), flat_struct=True)
            sliced_result_I_avg_raw = result_I_avg_raw.fetch(slice(num_have_got+1, num_so_far), flat_struct=True)
            sliced_result_Q_avg_raw = result_Q_avg_raw.fetch(slice(num_have_got+1, num_so_far), flat_struct=True)
            
            # update teh num_have got to the current fetch number
            num_have_got = num_so_far
            for index in range(num_have_got + 1, num_so_far + 1): # make sure num_so_far is inclusive
                datasaver.add_result((reps, index+1),  # the repetition number starts from 1, slice starts from 0
                (I_raw, sliced_result_I_raw[index-num_have_got]),  
                (Q_raw, sliced_result_Q_raw[index-num_have_got]),
                (v_raw, np.abs(sliced_result_I_raw[index-num_have_got] +1j*sliced_result_Q_raw[index-num_have_got])))

                datasaver.add_result((reps, index+1),  # the repetition number starts from 1, slice starts from 0
                (I_avg_raw, sliced_result_I_avg_raw[index-num_have_got]),  
                (Q_avg_raw, sliced_result_Q_avg_raw[index-num_have_got]),
                (v_avg_raw, np.abs(sliced_result_I_avg_raw[index-num_have_got] +1j*sliced_result_Q_avg_raw[index-num_have_got])))
            
            
            avg_v_so_far = np.abs(sliced_result_I_avg_raw[-1] + 1j*sliced_result_Q_avg_raw[-1])

            # clear data
            ax.clear()
            ax.plot(f_vals, avg_v_so_far)
            params = plot_fit(f_vals, avg_v_so_far, ax, fit_func="lorentzian")
            ax.set_title("Resonator spectroscopy, average of %d results" % (num_so_far))
            ax.set_xlabel("Frequency (Hz)")
            ax.set_ylabel("Signal amplitude")
             
            # update figure
            hdisplay.update(fig)
            time.sleep(10)  # add a short delay before next plot refresh
    
    handle.wait_for_all_values()
    all_result_I_avg = result_I_avg.fetch_all(flat_struct=True) # same as fetch
    all_result_Q_avg = result_Q_avg.fetch_all(flat_struct=True) # same as fetch
    datasaver.add_result((f, f_vals), (I_avg, all_result_I_avg),(Q_avg, all_result_Q_avg ))

    # calculate std error from raw data
    all_result_I_raw = result_I_raw.fetch_all(flat_struct=True)
    all_result_Q_raw = result_Q_raw.fetch_all(flat_struct=True)
    signal_raw = np.abs(all_result_I_raw + 1j*all_result_Q_raw)
    std_error_vs_f = scipy.stats.sem(signal_raw, axis=0)
    datasaver.add_result((std_error, std_error_vs_f))
    datasaver.flush_data_to_database()
    
    # store the metadata
    dataset = datasaver.dataset
    dataset.add_metadata("metadata", metadata=metadata)
  
    ###############################          FIT RESULTS       #############################
    fit_parameter = {}
    fit_params = fit.do_fit(metadata["fit_func_name"], freqs, signal_avg)  # get fit parameters
    ys_fit = fit.eval_fit(metadata["fit_func_name"], fit_params, freqs)  # get fit values
    for name, value in fit_params.valuesdict().items():  # save fit parameters to metadata
        fit_parameter[f"fit_parameter_{name}"] = value

    dataset.add_metadata("fit", metadata=fit_parameter)

    
    #################################          SAVE PLOT       #############################
    filename = EXP_NAME + "_" + SAMPLE_NAME + "_run" + str(dataset.run_id) + ".png"
    full_path = Path(dataset.filename) / filename
    plt.savefig(full_path, format="png", dpi=600)
    print(f"Plot saved at {imgpath_str}")


####################################          fin        ###############################
rr_spectroscopy.finish()


print(job.execution_report())
elapsed_time = time.perf_counter() - start_time
print(f"\nExecution time: {str(timedelta(seconds=elapsed_time))}")
print("Here's the final plot :-) \n")
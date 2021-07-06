""" Time Rabi measurement script v4.1 """
#############################           IMPORTS           ##############################
from qcrew.experiments.sample_B.imports import *
from types import SimpleNamespace

##########################        DATA SAVING VARIABLES       ##########################

SAMPLE_NAME = "sample_B"
EXP_NAME = "time_rabi"
PROJECT_NAME = "squeezed_cat"
DATAPATH = Path.cwd() / "data"
########################################################################################
########################           MEASUREMENT SEQUENCE         ########################
########################################################################################
metadata = {
    "reps": 50000,  # number of sweep repetitions
    "wait_time": 300000,  # delay between reps in ns, an integer multiple of 4 >= 16
    "t_start": 0,  # amplitude sweep range is set by start, stop, and step
    "t_stop": 1000,
    "t_step": 2,
    "rr_op": "readout",  # readout pulse name
    "rr_name": stg.rr.name,
    "rr_op_ampx": 0.0175,  # readout pulse amplitude scale factor
    "rr_integW1": "integW1",
    "rr_integW2": "integW2",
    "fit_fn": "sine",  # name of the fit function
    "rr_lo_freq": stg.rr.lo_freq,  # frequency of the local oscillator driving rr
    "rr_int_freq": stg.rr.int_freq,  # frequency played by OPX to rr
    "qubit_lo_freq": stg.qubit.lo_freq,  # frequency of local oscillator driving qubit
    "qubit_int_freq": stg.qubit.int_freq,  # frequency played by OPX to qubit
    "qubit_op": "pi_drag",  # qubit pulse name as defined in the config
    "qubit_op_ampx":1 ,
    "qubit_name": stg.qubit.name,
}

# create a namespace and convert the metadata dictionary into the parameters under this name space

t_start, t_stop, t_step = metadata["t_start"], metadata["t_stop"], metadata["t_step"]
metadata["sweep_length"] = len(np.arange(t_start, t_stop + t_step / 2, t_step))
mes = SimpleNamespace(**metadata)

# Temporary solution, in version 5 it will be a measurement object whose properties are the parameters
# The future measurement object will keep the same structure with the namep space

########################        QUA PROGRAM DEFINITION        ##########################

with program() as time_rabi:
    
    n = declare(int)
    t = declare(int)
    I = declare(fixed)
    Q = declare(fixed)

    t_stream = declare_stream()
    I_stream = declare_stream()
    Q_stream = declare_stream()

    #######################        MEASUREMENT SEQUENCE        #########################

    with for_(n, 0, n < mes.reps, n + 1):
        with for_(t, mes.t_start, t < mes.t_stop + mes.t_step/2, t + mes.t_step):  
            play(mes.qubit_op * amp(mes.qubit_op_ampx), mes.qubit_name, duration=t)

            align(mes.qubit_name, mes.rr_name)
            measure(
                mes.rr_op * amp(mes.rr_op_ampx),
                mes.rr_name,
                None,
                demod.full(mes.rr_integW1, I),
                demod.full(mes.rr_integW2, Q),
            )
            wait(int(mes.wait_time // 4), mes.qubit_name)
            save(t, t_stream)
            save(I, I_stream)
            save(Q, Q_stream)

    #####################        RESULT STREAM PROCESSING        #######################

    with stream_processing():
        t_stream.buffer(mes.sweep_length).save("T")  # to save sweep variable

        I_raw = I_stream.buffer(mes.sweep_length)
        Q_raw = Q_stream.buffer(mes.sweep_length)  # to reshape result streams

        I_avg = I_raw.average()
        Q_avg = Q_raw.average()

        # raw  I and Q
        I_raw.save_all("I")
        Q_raw.save_all("Q")

        # we need these two streams to calculate std err in a single pass
        (I_raw * I_raw + Q_raw * Q_raw).save_all("Y_SQ_RAW")
        (I_raw * I_raw + Q_raw * Q_raw).average().save_all("Y_SQ_RAW_AVG")
        (I_avg * I_avg + Q_avg * Q_avg).save("Y_AVG")

#############################        RUN MEASUREMENT        ############################

job = stg.qm.execute(time_rabi)
############################        INVOKE HELPERS        #############################
# fetch helper and plot hepler
fetcher = Fetcher(handle=job.result_handles, num_results=mes.reps)
plotter = Plotter(title=EXP_NAME, xlabel="Duration of pulse(ns) ")
stats = (None, None, None)  # to hold running stats (stderr, mean, variance * (n-1))

# initialise database under dedicated folder
db = initialise_database(
    exp_name=EXP_NAME,
    sample_name=SAMPLE_NAME,
    project_name=PROJECT_NAME,
    path=DATAPATH,
    timesubdir=False,
    timefilename=True,
)

#######################        LIVE POST-PROCESSING LOOP        ########################

with DataSaver(db) as datasaver:

    ####################        SAVE MEASUREMENT RUN METADATA       ####################

    datasaver.add_metadata(metadata)

    while fetcher.is_fetching:
        ####################            FETCH PARTIAL RESULTS         ##################

        (num_so_far, update_results) = fetcher.fetch()
        if not update_results:  # empty dict return means no new results are available
            continue
        ####################            LIVE SAVE RESULTS         ######################
        datasaver.update_multiple_results(update_results, save=["I", "Q"], group="data")

        ##########            CALCULATE RUNNING MEAN STANDARD ERROR         ############

        ys_raw = np.sqrt(update_results["Y_SQ_RAW"])
        ys_raw_avg = np.sqrt(update_results["Y_SQ_RAW_AVG"])
        stats = get_std_err(ys_raw, ys_raw_avg, num_so_far, *stats)

        #################            LIVE PLOT AVAILABLE RESULTS         ###############

        ys = np.sqrt(update_results["Y_AVG"])  # latest batch of average signal
        xs = update_results["A"]
        plotter.live_plot(xs, ys, num_so_far, fit_fn=mes.fit_fn, err=stats[0])
        time.sleep(1)  # prevent over-fetching, over-saving, ulta-fast live plotting

    #######################         SAVE REMAINING DATA         ########################

    # to save final average and sweep variables, we extract them from "update_results"
    final_save_dict = {"Y_AVG": ys, "X": xs}
    datasaver.add_multiple_results(final_save_dict, save=["Y_AVG", "X"], group="data")


###############################          fin           #################################

print(job.execution_report())

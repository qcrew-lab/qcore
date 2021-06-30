""" Power Rabi measurement script v4 """
#############################           IMPORTS           ##############################

from qcrew.experiments.coax_test.imports import *

reload(cfg)
reload(stg)  # reload stage and configuration before each measurement run

##########################        DATA SAVING VARIABLES       ##########################

SAMPLE_NAME = "coax_a"
EXP_NAME = "power_rabi"
PROJECT_FOLDER_NAME = "coax_test"
DATAPATH = Path.cwd() / "data"

#########################        MEASUREMENT PARAMETERS        #########################

metadata = {
    "reps": 20000,  # number of sweep repetitions
    "wait": 50000,  # delay between reps in ns, an integer multiple of 4 >= 16
    "start": -1.9,  # amplitude sweep range is set by start, stop, and step
    "stop": 1.9,
    "step": 0.05,
    "qubit_op": "gaussian",  # qubit pulse name as defined in the config
    "rr_op": "readout",  # readout pulse name
    "rr_op_ampx": 0.2,  # readout pulse amplitude scale factor
    "fit_fn": "sine",  # name of the fit function
    "rr_lo_freq": stg.rr.lo_freq,  # frequency of the local oscillator driving rr
    "rr_int_freq": stg.rr.int_freq,  # frequency played by OPX to rr
    "qubit_lo_freq": stg.qubit.lo_freq,  # frequency of local oscillator driving qubit
    "qubit_int_freq": stg.qubit.int_freq,  # frequency played by OPX to qubit
}

x_start, x_stop, x_step = metadata["start"], metadata["stop"], metadata["step"]
metadata["sweep_length"] = len(np.arange(x_start, x_stop + x_step / 2, x_step))

########################        QUA PROGRAM DEFINITION        ##########################

with program() as power_rabi:

    #####################        QUA VARIABLE DECLARATIONS        ######################

    n = declare(int)  # averaging loop variable
    x = declare(fixed)  # sweep variable "x"
    x_stream = declare_stream()  # to save "x"
    I = declare(fixed)  # result variable "I"
    I_stream = declare_stream()  # to save "I"
    Q = declare(fixed)  # result variable "Q"
    Q_stream = declare_stream()  # to save "Q"

    #######################        MEASUREMENT SEQUENCE        #########################

    with for_(n, 0, n < metadata["reps"], n + 1):
        with for_(x, x_start, x < x_stop + x_step / 2, x + x_step):
            play(metadata["qubit_op"] * amp(x), stg.qubit.name)
            align(stg.qubit.name, stg.rr.name)
            measure(
                metadata["rr_op"] * amp(metadata["rr_op_ampx"]),
                stg.rr.name,
                None,
                demod.full("integW1", I),
                demod.full("integW2", Q),
            )
            wait(int(metadata["wait"] // 4), stg.qubit.name)
            save(x, x_stream)
            save(I, I_stream)
            save(Q, Q_stream)

    #####################        RESULT STREAM PROCESSING        #######################

    with stream_processing():
        I_raw = I_stream.buffer(metadata["sweep_length"])
        Q_raw = Q_stream.buffer(metadata["sweep_length"])  # to reshape result streams
        I_avg = I_raw.average()
        Q_avg = Q_raw.average()  # to get running averages

        I_raw.save_all("I")
        Q_raw.save_all("Q")  # to save all raw I and Q data

        # we need these two streams to calculate std err in a single pass
        (I_raw * I_raw + Q_raw * Q_raw).save_all("Y_SQ_RAW")
        (I_raw * I_raw + Q_raw * Q_raw).average().save_all("Y_SQ_RAW_AVG")

        (I_avg * I_avg + Q_avg * Q_avg).save("Y_AVG")  # to live plot latest average
        x_stream.buffer(metadata["sweep_length"]).save("X")  # to save sweep variable

#############################        RUN MEASUREMENT        ############################

job = stg.qm.execute(power_rabi)

#############################        INVOKE HELPERS        #############################

fetcher = Fetcher(handle=job.result_handles, num_results=metadata["reps"])
plotter = Plotter(title=EXP_NAME, xlabel="Amplitude scale factor")
stats = (None, None, None)  # to hold running stats (stderr, mean, variance * (n-1))
db = initialise_database(
    exp_name=EXP_NAME,
    sample_name=SAMPLE_NAME,
    project_name=PROJECT_FOLDER_NAME,
    path=DATAPATH,
    timesubdir=False,
    timefilename=True,
)

#######################        LIVE POST-PROCESSING LOOP        ########################


with DataSaver(db) as datasaver:

    ####################        SAVE MEASUREMENT RUN METADATA       ####################

    datasaver.add_metadata(metadata)

    while fetcher.is_fetching:  # while the fetcher is not done fetching all results

        ####################            FETCH PARTIAL RESULTS         ##################

        partial_results = fetcher.fetch()  # key = tag, value = partial data
        num_results = fetcher.count  # get number of results fetched so far
        if not partial_results:  # empty dict return means no new results are available
            continue
        ####################            LIVE SAVE RESULTS         ######################

        # to only live save raw "I" and "Q" data, we extract them from "partial_results"
        live_save_dict = {"I": partial_results["I"], "Q": partial_results["Q"]}
        datasaver.update_multiple_results(live_save_dict, group="data")

        ##########            CALCULATE RUNNING MEAN STANDARD ERROR         ############

        ys_raw = np.sqrt(partial_results["Y_SQ_RAW"])
        ys_raw_avg = np.sqrt(partial_results["Y_SQ_RAW_AVG"])
        stats = get_std_err(ys_raw, ys_raw_avg, num_results, *stats)

        #################            LIVE PLOT AVAILABLE RESULTS         ###############

        ys = np.sqrt(partial_results["Y_AVG"])  # latest batch of average signal
        xs = partial_results["X"]
        plotter.live_plot(xs, ys, num_results, fit_fn=metadata["fit_fn"], err=stats[0])
        time.sleep(1)  # prevent over-fetching, over-saving, ulta-fast live plotting

    #######################         SAVE REMAINING DATA         ########################

    # to save final average and sweep variables, we extract them from "partial_results"
    final_save_dict = {"Y_AVG": ys, "X": xs}
    datasaver.add_multiple_results(final_save_dict, group="data")
    # NOTE (OPTIONAL) here, we can also save the final plot.

###############################          fin           #################################

print(job.execution_report())

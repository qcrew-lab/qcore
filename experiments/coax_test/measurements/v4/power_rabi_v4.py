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
    "reps": 10000,  # number of sweep repetitions
    "wait": 50000,  # delay between reps in ns, an integer multiple of 4 >= 16
    "start": -2.0,  # amplitude sweep range is set by start, stop, and step
    "stop": 2.0,
    "step": 0.02,
    "qubit_op": "gaussian",  # qubit pulse name as defined in the config
    "rr_op": "readout",  # readout pulse name
    "rr_op_ampx": 0.2,  # readout pulse amplitude scale factor
    "fit_fn": "sine",  # name of the fit function
    "rr_lo_freq": stg.rr.lo_freq,  # frequency of the local oscillator driving rr
    "rr_int_freq": stg.rr.int_freq,  # frequency played by OPX to rr
    "qubit_lo_freq": stg.qubit.lo_freq,  # frequency of local oscillator driving qubit
    "qubit_int_freq": stg.qubit.int_freq,  # frequency played by OPX to qubit
}

metadata["sweep_length"] = len(  # add sweep length to metadata
    np.arange(metadata["start"], metadata["stop"], metadata["step"])
)

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
    # unpack start, stop, step from the metadata dictionary for convenience
    x_start, x_stop, x_step = metadata["start"], metadata["stop"], metadata["step"]

    #######################        MEASUREMENT SEQUENCE        #########################

    with for_(n, 0, n < metadata["reps"], n + 1):
        with for_(x, x_start, x < x_stop - x_step / 2, x + x_step):
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
        (I_raw * I_raw + Q_raw * Q_raw).save_all("Y_RAW")  # to get std err
        (I_avg * I_avg + Q_avg * Q_avg).save_all("Y_AVG")  # to live plot
        x_stream.buffer(metadata["sweep_length"]).save("X")  # to save sweep variable

#############################        RUN MEASUREMENT        ############################

job = stg.qm.execute(power_rabi)

#############################        INVOKE HELPERS        #############################

fetcher = Fetcher(handle=job.result_handles, num_results=metadata["reps"])
plotter = Plotter(title=EXP_NAME, xlabel="Amplitude scale factor")
stats = tuple()  # to calculate std error in one pass
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

        # NOTE for Yifan about fetcher.fetch() method behaviour
        # fetcher.fetch() returns dict "partial_results" with key = tag, value = data
        # "partial_results" has result data for all tags defined in stream processing
        # if tag belongs to single result, data is got by calling:
        # handle.get(tag).fetch_all(flat_struct = True)
        # else if tag belongs to multiple result, data is got by calling:
        # handle.get(tag).fetch(slice(last_count, count), flat_struct=True)
        # where last_count and count are maintained by the Fetcher
        # you can get current number of results fetched by calling fetcher.count
        partial_results = fetcher.fetch()
        num_fetched_results = fetcher.count
        if not partial_results:  # empty dict return means no new results are available
            continue  # go to beginning of live post-processing loop

        ####################            LIVE SAVE RESULTS         ######################

        # to only live save raw "I" and "Q" data, we extract them from "partial_results"
        live_save_dict = {"I": partial_results["I"], "Q": partial_results["Q"]}
        datasaver.update_multiple_results(live_save_dict, group="data")

        #################            PROCESS AVAILABLE RESULTS         #################

        ys_raw = np.sqrt(partial_results["Y_RAW"])  # latest batch of raw ys
        ys_avg = np.sqrt(partial_results["Y_AVG"])  # latest batch of avg ys
        xs = partial_results["X"]

        if stats:  # stats = (y_std_err, running average, running variance * (count-1))
            stats = get_std_err(ys_raw, ys_avg, num_fetched_results, *stats)
        else:
            stats = get_std_err(ys_raw, ys_avg, num_fetched_results)

        fit_params = fit.do_fit(metadata["fit_fn"], xs, ys_avg[-1])  # get fit params
        ys_fit = fit.eval_fit(metadata["fit_fn"], fit_params, xs)  # get fit values

        #################            LIVE PLOT AVAILABLE RESULTS         ###############

        plotter.live_plot(
            x=xs, y=ys_avg[-1], n=num_fetched_results, fit=ys_fit, err=stats[0]
        )
        time.sleep(0.5)  # prevent over-fetching, over-saving, ulta-fast live plotting

    #######################         SAVE REMAINING DATA         ########################

    # to save final average and sweep variables, we extract them from "partial_results"
    final_save_dict = {"Y_AVG": ys_avg[-1], "X": xs}
    datasaver.add_multiple_results(final_save_dict, group = "data")
    # NOTE (OPTIONAL) here, we can also save the final plot.

###############################          fin           #################################

print(job.execution_report())

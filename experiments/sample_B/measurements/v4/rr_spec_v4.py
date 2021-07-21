""" RR Spectroscopy measurement script v4.1 """

from qcrew.experiments.sample_B.imports import *
from types import SimpleNamespace

stage_module_path = resolve_name(".stage", "qcrew.experiments.sample_B.imports")
if stage_module_path not in sys.modules:
    import qcrew.experiments.sample_B.imports.stage as stg
else:
    reload(stg)


#########################        DATA SAVING VARIABLES       ##########################

SAMPLE_NAME = "sample_B"
EXP_NAME = "rr_spectroscopy"
PROJECT_NAME = "squeezed_cat"
DATAPATH = Path.cwd() / "data"

#########################        MEASUREMENT PARAMETERS        #########################

metadata = {
    "reps": 1000,  # number of sweep repetitions
    "wait_time": 75000,  # delay between reps in ns, an integer multiple of 4 >= 16
    "f_start": -51e6,  # frequency sweep range is set by start, stop, and step
    "f_stop": -46e6,
    "f_step": 0.05e6,
    "rr_op": "readout",  # readout pulse name
    "rr_name": stg.rr.name,
    "rr_op_ampx": 0.0175,  # readout pulse amplitude scale factor
    "fit_fn": "lorentzian",  # name of the fit function
    "rr_lo_freq": stg.rr.lo_freq,  # frequency of the local oscillator driving rr
    "rr_int_freq": stg.rr.int_freq,  # frequency played by OPX to rr
    "rr_integW1": "integW1",
    "rr_integW2": "integW2",
}

# create a namespace and convert the metadata dictionary into the parameters under this name space


f_start, f_stop, f_step = metadata["f_start"], metadata["f_stop"], metadata["f_step"]
metadata["sweep_length"] = len(np.arange(f_start, f_stop + f_step / 2, f_step))
mes = SimpleNamespace(**metadata)

########################        QUA PROGRAM DEFINITION        ##########################


with program() as rr_spec:

    #####################        QUA VARIABLE DECLARATIONS        ######################

    n = declare(int)  # averaging loop variable
    f = declare(int)
    I = declare(fixed)
    Q = declare(fixed)

    f_stream = declare_stream()
    I_stream = declare_stream()
    Q_stream = declare_stream()

    #######################        MEASUREMENT SEQUENCE        #########################

    with for_(n, 0, n < mes.reps, n + 1):
        with for_(f, mes.f_start, f < mes.f_stop + mes.f_step / 2, f + mes.f_step):
            update_frequency(mes.rr_name, f)
            measure(
                mes.rr_op * amp(mes.rr_op_ampx),
                mes.rr_name,
                None,
                demod.full(mes.rr_integW1, I),
                demod.full(mes.rr_integW2, Q),
            )
            wait(int(mes.wait_time // 4), mes.rr_name)
            save(f, f_stream)
            save(I, I_stream)
            save(Q, Q_stream)

    #####################        RESULT STREAM PROCESSING        #######################

    with stream_processing():
        f_stream.buffer(mes.sweep_length).save("F")  # to save sweep variable

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

job = stg.qm.execute(rr_spec)

#############################        INVOKE HELPERS        #############################

# fetch helper and plot hepler
fetcher = Fetcher(handle=job.result_handles, num_results=mes.reps)
plotter = Plotter(title=EXP_NAME, xlabel="RR IF")
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
        xs = update_results["F"]
        plotter.live_plot(xs, ys, num_so_far, fit_fn=mes.fit_fn, err=stats[0])
        time.sleep(1)  # prevent over-fetching, over-saving, ulta-fast live plotting

    #######################         SAVE REMAINING DATA         ########################

    # to save final average and sweep variables, we extract them from "update_results"
    final_save_dict = {"Y_AVG": ys, "X": xs}
    datasaver.add_multiple_results(final_save_dict, save=["Y_AVG", "X"], group="data")

###############################          fin           #################################

print(job.execution_report())

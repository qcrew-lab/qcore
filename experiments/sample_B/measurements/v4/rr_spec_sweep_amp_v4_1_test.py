""" RR Spectroscopy measurement script v4.3 """

from qcrew.experiments.sample_B.imports import *  #  import all objects from init file
from types import SimpleNamespace

stage_module_path = resolve_name(".stage", "qcrew.experiments.sample_B.imports")
if stage_module_path not in sys.modules:
    import qcrew.experiments.sample_B.imports.stage as stg
else:
    reload(stg)


#########################        DATA SAVING VARIABLES       ##########################

SAMPLE_NAME = "sample_B"
EXP_NAME = "rr_spec_amp"
PROJECT_NAME = "squeezed_cat"
DATAPATH = Path.cwd() / "data"

#########################        MEASUREMENT PARAMETERS        #########################

metadata = {
    "reps": 8000,  # number of sweep repetitions
    "wait_time": 75000,  # delay between reps in ns, an integer multiple of 4 >= 16
    "f_start": -51e6,  # frequency sweep range is set by start, stop, and step
    "f_stop": -46e6,
    "f_step": 0.05e6,
    "qubit_op": "gaussian",  # qubit pulse name as defined in the config
    "qubit_name": stg.qubit.name,
    "qubit_ampx": 1,
    "rr_op": "readout",  # readout pulse name
    "rr_name": stg.rr.name,
    "a_start": 0.01,
    "a_stop": 0.02,
    "num_a": 3,
    "fit_fn": "lorentzian",  # name of the fit function
    "rr_lo_freq": stg.rr.lo_freq,  # frequency of the local oscillator driving rr
    "rr_int_freq": stg.rr.int_freq,  # frequency played by OPX to rr
    "qubit_lo_freq": stg.qubit.lo_freq,  # frequency of local oscillator driving qubit
    "qubit_int_freq": stg.qubit.int_freq,  # frequency played by OPX to qubit
    "rr_integW1": "integW1",
    "rr_integW2": "integW2",
}

# create a namespace and convert the metadata dictionary into the parameters under this name space


f_start, f_stop, f_step = metadata["f_start"], metadata["f_stop"], metadata["f_step"]
rr_f_list = np.arange(f_start, f_stop, f_step)
# if the length is L, the buffer_length is L+1, pls refer to the metadata["sweep_length_f"]
metadata["sweep_length_f"] = len(np.arange(f_start, f_stop + f_step / 2, f_step))

a_start, a_stop, num_a = metadata["a_start"], metadata["a_stop"], metadata["num_a"]
rr_ascale = np.linspace(a_start, a_stop, num_a)
metadata["sweep_length_a_ascale"] = len(rr_ascale)


qubit_ascale = 1

# rr_ascale = np.concatenate((np.linspace(0.005, 0.025, 21), np.linspace(0.026, 2, 41)))

mes = SimpleNamespace(**metadata)


parameter_list = [
    (x.flatten()) for x in np.meshgrid(metadata["qubit_ampx"], rr_ascale, indexing="ij")
]

# Defines buffer size for averaging
buffer_lengths = [
    1 if type(x).__name__ in {"int", "float"} else len(x)
    for x in [qubit_ascale, rr_ascale, rr_f_list]
]


buffer_lengths_test = [metadata["sweep_length_a_ascale"], metadata["sweep_length_f"]]


# qubit_a_vec = parameter_list[0]
# rr_a_vec = parameter_list[1]
########################        QUA PROGRAM DEFINITION        ##########################


# Rearranges the input parameters in arrays over which QUA can iterate. The arrays are given in the order of outer to inner loop.numpy

with program() as rr_spec_amp:

    #####################        QUA VARIABLE DECLARATIONS        ######################

    n = declare(int)  # averaging loop variable
    f = declare(int)
    qubit_a = declare(fixed)
    rr_a = declare(fixed)

    rr_a_vec = declare(fixed, value=rr_ascale)

    # Outpus
    I = declare(fixed)
    Q = declare(fixed)

    f_stream = declare_stream()
    I_stream = declare_stream()
    Q_stream = declare_stream()

    #######################        MEASUREMENT SEQUENCE        #########################

    with for_(n, 0, n < mes.reps, n + 1):
        # Qubit and resonator pulse amplitude scaling loop
        with for_each_((rr_a), (rr_a_vec)):
            # Frequency sweep
            with for_(f, mes.f_start, f < mes.f_stop + mes.f_step / 2, f + mes.f_step):
                update_frequency(mes.rr_name, f)

                measure(
                    mes.rr_op * amp(rr_a),
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

        ## Method 1:
        # Note: When we calculate the data before the buffer, there is something wrong with the "num_so_far" in ""LIVE SAVE RESULTS ""

        f_stream.buffer(*buffer_lengths_test).save("F")

        # I_raw1 = I_stream
        # Q_raw1 = Q_stream

        # I_raw1.save_all("I")
        # Q_raw1.save_all("Q")

        # (I_raw1 * I_raw1 + Q_raw1 * Q_raw1).buffer(*buffer_lengths_test).save_all("Y_RAW")

        # (I_raw1 * I_raw1 + Q_raw1 * Q_raw1).buffer(*buffer_lengths_test).average().save_all("Y_RAW_AVG")

        # (I_raw1 * I_raw1 + Q_raw1 * Q_raw1).buffer(*buffer_lengths_test).average().save("Y_AVG")

        # .buffer(*buffer_lengths_test).save_all("Y_RAW")
        

        ###########################################

        ##Method 2:

        # f_stream.buffer(*buffer_lengths_test).save("F")  # to save sweep variable

        I_raw = I_stream.buffer(*buffer_lengths_test)
        Q_raw = Q_stream.buffer(*buffer_lengths_test)

        I_avg = I_raw.average()
        Q_avg = Q_raw.average()

        # raw  I and Q
        I_raw.save_all("I_raw")
        Q_raw.save_all("Q_raw")

        I_avg.save_all("I_raw_avg")
        Q_avg.save_all("Q_raw_avg")

        # average I and Q

        I_avg.save("I_avg")
        Q_avg.save("Q_avg")

        ####################################################

#############################        RUN MEASUREMENT        ############################

job = stg.qm.execute(rr_spec_amp)

#############################        INVOKE HELPERS        #############################

# fetch helper and plot hepler
fetcher = Fetcher(handle=job.result_handles, num_results=mes.reps)
# plotter = Plotter(title=EXP_NAME, xlabel="RR IF")
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

    fig = plt.figure(figsize=(9, 6))
    ax = fig.add_subplot(1, 1, 1)
    hdisplay = display.display("", display_id=True)
    remaining_data = metadata["reps"]
    N = 10

    while fetcher.is_fetching:

        ####################            FETCH PARTIAL RESULTS         ##################

        (num_so_far, update_results) = fetcher.fetch()
        if not update_results:  # empty dict return means no new results are available
            continue
        ####################            LIVE SAVE RESULTS         ######################
        datasaver.update_multiple_results(update_results, save=["I", "Q"], group="data")

        ##########            CALCULATE RUNNING MEAN STANDARD ERROR         ############

        # fig = plt.figure(figsize=(9, 6))
        # ax = fig.add_subplot(1,1,1)
        # for index, rr_amplitude in enumerate(rr_ascale):
        #     # ys_raw = np.sqrt(update_results[:,index,:])
        #     # ys_raw_avg = np.sqrt(update_results[:,index,:])
        #     # stats = get_std_err(ys_raw, ys_raw_avg, num_a, *stats)
        #     xs = update_results["F"][0]
        #     ys = np.sqrt(update_results["Y_AVG"][index])
        #     plt.plot(xs, ys, label="r_a = {}".format((rr_amplitude)))

        # plt.legend()
        # plt.show()

        # time.sleep(1)

        # fig = plt.figure(figsize=(9, 6))
        # # hdisplay = display.display("", display_id=True)
        # ax = fig.add_subplot(1, 1, 1)
        # fig = plt.figure(figsize=(9, 6))
        # ax = fig.add_subplot(1, 1, 1)
        # hdisplay = display.display("", display_id=True)

        ax.clear()
        for index, rr_amplitude in enumerate(rr_ascale):

            I_raw = update_results["I_raw"][:, index, :]
            Q_raw = update_results["Q_raw"][:, index, :]
            ys_raw = np.sqrt(I_raw * I_raw + Q_raw * Q_raw)

            I_raw_avg = update_results["I_raw_avg"][:, index, :]
            Q_raw_avg = update_results["Q_raw_avg"][:, index, :]
            ys_raw_avg = np.sqrt(I_raw_avg * I_raw_avg + Q_raw_avg * Q_raw_avg)

            stats = get_std_err(ys_raw, ys_raw_avg, num_so_far, *stats)

            I_avg = update_results["I_avg"][index]
            Q_avg = update_results["Q_avg"][index]
            xs = update_results["F"][0]
            ys = np.sqrt(I_avg * I_avg + Q_avg * Q_avg)

            ax.errorbar(xs, ys, yerr=stats[0], label="r_a = {}".format((rr_amplitude)))

        plt.legend()
        hdisplay.update(fig)

        # plt.show()
        # time.sleep(1)

        #################            LIVE PLOT AVAILABLE RESULTS         ###############

    #######################         SAVE REMAINING DATA         ########################

    # to save final average and sweep variables, we extract them from "update_results"
    final_save_dict = {"Y_AVG": ys, "X": xs}
    datasaver.add_multiple_results(final_save_dict, save=["Y_AVG", "X"], group="data")

###############################          fin           #################################

print(job.execution_report())

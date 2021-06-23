""" Power Rabi measurement script v4 """
from qcrew.experiments.coax_test.imports import *

reload(cfg), reload(stg)  # reload before each measurement run
start_time = time.perf_counter()  # to get measurement execution time

##############        SPECIFY VARIABLES FOR SAVING MEASUREMENT DATA       ##############

meas_name = "power_rabi"  # appended to saved datafile name
filename_suffix = meas_name + ""  # replace "" to customise filename

datatags: tuple = ("I", "Q", "Y_RAW", "Y_AVG")  # to identify datasets
# NOTE these datatags will be used by stream processing, Fetcher, and Datasaver

######################        SET MEASUREMENT PARAMETERS        ########################

mdata = {  # metadata dictionary
    "reps": 40000,  # number of sweep repetitions
    "wait": 50000,  # delay between reps in ns, an integer multiple of 4 >= 16
    "a_start": -1.6,  # amplitude sweep range is set by a_start, a_stop, and a_step
    "a_stop": 1.6,
    "a_step": 0.05,
    "qubit_op": "gaussian",  # qubit pulse name as defined in the config
    "rr_op": "readout",  # readout pulse name
    "rr_op_ampx": 0.2,  # readout pulse amplitude scale factor
    "fit_fn": "sine",  # name of the fit function
    "rr_lo_freq": stg.rr.lo_freq,  # frequency of the local oscillator driving rr
    "rr_int_freq": stg.rr.int_freq,  # frequency played by OPX to rr
    "qubit_lo_freq": stg.qubit.lo_freq,  # frequency of local oscillator driving qubit
    "qubit_int_freq": stg.qubit.int_freq,  # frequency played by OPX to qubit
}

xs = np.arange(mdata["a_start"], mdata["a_stop"], mdata["a_step"])  # indep var list
mdata["sweep_len"] = len(xs)  # add sweep length to metadata

##########################        DEFINE QUA PROGRAM        ############################

with program() as power_rabi:

    #####################        QUA VARIABLE DECLARATIONS        ######################

    n = declare(int)  # averaging loop variable
    a = declare(fixed)  # amplitude scale factor sweep variable

    I, Q = declare(fixed), declare(fixed)  # result variables
    I_st, Q_st = declare_stream(), declare_stream()  # to save result variables

    #######################        MEASUREMENT SEQUENCE        #########################

    with for_(n, 0, n < mdata["reps"], n + 1):  # outer averaging loop, inner ampx sweep
        with for_(a, mdata["a_start"], a < mdata["a_stop"], a + mdata["a_step"]):
            play(mdata["qubit_op"] * amp(a), stg.qubit.name)
            align(stg.qubit.name, stg.rr.name)
            measure(
                mdata["rr_op"] * amp(mdata["rr_op_ampx"]),
                stg.rr.name,
                None,
                demod.full("integW1", I),
                demod.full("integW2", Q),
            )
            wait(int(mdata["wait"] // 4), stg.qubit.name)
            save(I, I_st)
            save(Q, Q_st)

    #####################        RESULT STREAM PROCESSING        #######################

    with stream_processing():
        I_raw, Q_raw = I_st.buffer(mdata["sweep_len"]), Q_st.buffer(mdata["sweep_len"])
        I_raw.save_all(datatags[0])  # save raw I values
        Q_raw.save_all(datatags[1])  # save raw Q values
        (I_raw * I_raw + Q_raw * Q_raw).save_all(datatags[2])  # save y^2 to get std err
        I_avg, Q_avg = I_raw.average(), Q_raw.average()  # get running averages
        (I_avg * I_avg + Q_avg * Q_avg).save_all(datatags[3])  # save avg y^2

#############################        RUN MEASUREMENT        ############################

job = stg.qm.execute(power_rabi)

######################        SAVE MEASUREMENT RUN METADATA       ######################



#############################        INVOKE HELPERS        #############################

datasaver = Datasaver(sample_name=STAGE_NAME, filename_suffix=filename_suffix)
fetcher = Fetcher(handle=job.result_handles, tags=datatags)
plotter = Plotter(title=meas_name, xlabel="Amplitude scale factor")
stats = tuple()  # tuple holding vars needed to calculate running std err

#############################        POST-PROCESSING        ############################

while fetcher.count != mdata["reps"]:  # while all results have not been fetched

    ######################            FETCH PARTIAL RESULTS         ####################

    partial_data = fetcher.fetch()  # return dict with (k, v) = (datatag, partial data)
    current_count = fetcher.count  # get current number of fetched results

    ######################            SAVE FETCHED RESULTS         #####################



    ####################            PROCESS AVAILABLE RESULTS         ##################

    y_avg = np.sqrt(partial_data[datatags[3]][-1])  # get latest y_avg
    y_raw = np.sqrt(partial_data[datatags[2]])  # get latest batch of y_raw

    if stats:  # track running stats so that y_std_err is calculated in a single pass
        stats = get_std_err(y_raw, current_count, *stats)
    else:
        stats = get_std_err(y_raw, current_count)
    y_std_err = stats[0]  # get latest y_std_err

    # TODO get fit

    ###################            LIVE PLOT AVAILABLE RESULTS         #################

    plotter.live_plot(x=xs, y=y_avg, fit=None, err=y_std_err, n=current_count)

# SAVE PLOT TO HDF5
# DATASAVER HOUSEKEEPING i.e flush, close, print paths
# PRINT JOB EXECUTION REPORT AND MEASUREMENT EXECUTION TIME


plt.rcParams["figure.figsize"] = (12, 8)  # adjust figure size

while handle.is_processing():  # while the measurement is running

    # calculate std error from raw data
    signal_sq_raw = handle.signal_sq_raw.fetch_all(flat_struct=True)
    signal_raw = np.sqrt(signal_sq_raw)
    mean_std_error = scipy.stats.sem(signal_raw, axis=0)

    ###################            LIVE PLOT PARTIAL RESULTS         ###################

    plt.cla()  # refresh
    plt.errorbar(
        ampxs,
        signal_avg,
        yerr=mean_std_error,
        ls="none",
        lw=1,
        ecolor="black",
        marker="o",
        ms=4,
        mfc="black",
        mec="black",
        capsize=3,
        fillstyle="none",
    )
    plt.title(f"Power Rabi: {num_results} reps")
    plt.xlabel("Amplitude scale factor")
    plt.ylabel("Signal amplitude (A.U.)")
    display.display(plt.gcf())  # display latest batch
    display.clear_output(wait=True)  # clear latest batch after new batch is available
    time.sleep(0.5)  # add a short delay before next plot refresh

###########################          FETCH FINAL RESULTS       #########################

print(f"{meas_name} completed, fetching results...")  # log message

i_avg = handle.i_avg.fetch_all(flat_struct=True)  # fetch final average I and Q values
q_avg = handle.q_avg.fetch_all(flat_struct=True)
signal_avg = np.abs(i_avg + 1j * q_avg)  # calculate final average signal

i_raw = handle.i_raw.fetch_all(flat_struct=True)  # fetch all raw I & Q values
q_raw = handle.q_raw.fetch_all(flat_struct=True)
signal_raw = np.abs(i_raw + 1j * q_raw)  # calculate final raw signal
mean_std_error = scipy.stats.sem(signal_raw, axis=0)  # for plotting errorbars

###############################          FIT RESULTS       #############################

fit_params = fit.do_fit(mdata["fit_fn"], ampxs, signal_avg)  # get fit parameters
ys_fit = fit.eval_fit(mdata["fit_fn"], fit_params, ampxs)  # get fit values
for name, value in fit_params.valuesdict().items():  # save fit parameters to metadata
    mdata[f"fit_param_{name}"] = value

##############################          PLOT RESULTS       #############################

plt.cla()  # refresh plot
plt.errorbar(  # plot final results as a scatter plot with errorbars
    ampxs,
    signal_avg,
    yerr=mean_std_error,
    ls="none",
    lw=1,
    ecolor="black",
    marker="o",
    ms=4,
    mfc="black",
    mec="black",
    capsize=3,
    label="data",
    fillstyle="none",
)
plt.plot(ampxs, ys_fit, color="m", lw=2, label="fit")  # plot fitted values
plt.title(f"Power Rabi: {mdata['reps']} reps")
plt.xlabel("Amplitude scale factor")
plt.ylabel("Signal amplitude (A.U.)")
plt.legend()

###############################         GENERATE PATHS     #############################

folderpath = Path.cwd() / f"data/{STAGE_NAME}/{str(date.today())}"
folderpath.mkdir(parents=True, exist_ok=True)  # create daily subfolder if none exists
filename = f"{datetime.now().strftime('%H-%M-%S')}_{meas_name}"
filepath = folderpath / filename

#################################          SAVE DATA       #############################

print(f"Fetched {meas_name} results, saving data...")  # log message

datapath_str = str(filepath) + ".hdf5"
with h5py.File(datapath_str, "a") as file:  # save to hdf5 file
    file.create_dataset("ampxs", data=ampxs)  # save frequency sweep values
    file.create_dataset("i_raw", data=i_raw)  # save all raw I values
    file.create_dataset("q_raw", data=q_raw)  # save all raw Q values
    file.create_dataset("i_avg", data=i_raw)  # save final average I values
    file.create_dataset("q_avg", data=i_raw)  # save final average Q values

    for name, value in mdata.items():  # save metadata as file attributes
        file.attrs[name] = value

print(f"Data saved at {datapath_str}")  # log message

#################################          SAVE PLOT       #############################

imgpath_str = str(filepath) + ".png"
plt.savefig(imgpath_str, format="png", dpi=600)
print(f"Plot saved at {imgpath_str}")

####################################          fin        ###############################

print(job.execution_report())
print("Here's the final plot :-) \n")

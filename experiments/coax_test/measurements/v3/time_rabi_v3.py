""" Time Rabi measurement script v3.0 """

from qcrew.experiments.coax_test.imports import *

reload(cfg)  # reload configuration and stage before each measurement run
reload(stg)

##########################        TOP LEVEL CONSTANTS        ###########################

meas_name = "time_rabi"  # used as the suffix for the saved data file/plot
start_time = time.perf_counter()  # to get measurement execution time

rr = stg.rr  # reference to the readout mode object
qubit = stg.qubit  # reference to the qubit object

######################        SET MEASUREMENT PARAMETERS        ########################

mdata = {  # metadata dict, set measurement parameters here
    "reps": 3000,  # number of sweep repetitions
    "wait_time": 50000,  # delay between reps in ns, an integer multiple of 4 >= 16
    "t_start": 100,  # qubit pulse length in ns
    "t_stop": 1600,  # sweep range is set by t_start, t_stop, t_step
    "t_step": 4,  # t_step must be >= 4 and an integer multiple of 4
    "q_ampx": 1.0,  # qubit pulse amplitude scale factor
    "qubit_op": "CW",  # qubit pulse name as defined in the config
    "r_ampx": 0.2,  # readout pulse amplitude scale factor
    "rr_op": "readout",  # readout pulse name
    "fit_func_name": "sine",  # name of the fit function
    "rr_lo_freq": cfg.rr_LO,  # frequency of the local oscillator driving rr
    "rr_int_freq": cfg.rr_IF,  # frequency played by OPX to rr
    "qubit_lo_freq": cfg.qubit_LO,  # frequency of local oscillator driving qubit
    "qubit_int_freq": cfg.qubit_IF,  # frequency played by OPX to qubit
}

times = np.arange(mdata["t_start"], mdata["t_stop"], mdata["t_step"])  # indep var list
mdata["sweep_len"] = len(times)  # add sweep length to metadata

with program() as time_rabi:

    #####################        QUA VARIABLE DECLARATIONS        ######################

    n = declare(int)  # averaging loop variable
    t = declare(int)  # qubit pulse duration sweep variable

    I, Q = declare(fixed), declare(fixed)  # result variables
    I_st, Q_st = declare_stream(), declare_stream()  # to save result variables

    #######################        MEASUREMENT SEQUENCE        #########################

    with for_(n, 0, n < mdata["reps"], n + 1):  # outer averaging loop, inner time sweep
        with for_(t, mdata["t_start"], t < mdata["t_stop"], t + mdata["t_step"]):
            play(
                mdata["qubit_op"] * amp(mdata["q_ampx"]),
                qubit.name,
                duration=t / 4,
            )
            align(qubit.name, rr.name)
            measure(
                mdata["rr_op"] * amp(mdata["r_ampx"]),
                rr.name,
                None,
                demod.full("integW1", I),
                demod.full("integW2", Q),
            )
            wait(int(mdata["wait_time"] // 4), qubit.name)
            save(I, I_st)
            save(Q, Q_st)

    #####################        RESULT STREAM PROCESSING        #######################

    with stream_processing():
        # save all raw I and Q values
        I_raw_st = I_st.buffer(mdata["sweep_len"])
        Q_raw_st = Q_st.buffer(mdata["sweep_len"])
        I_raw_st.save_all("i_raw")
        Q_raw_st.save_all("q_raw")

        # compute signal^2 from raw I and Q values for calculating mean standard error
        (I_raw_st * I_raw_st + Q_raw_st * Q_raw_st).save_all("signal_sq_raw")

        # save final averaged I and Q values
        I_avg_st = I_st.buffer(mdata["sweep_len"]).average()
        Q_avg_st = Q_st.buffer(mdata["sweep_len"]).average()
        I_avg_st.save("i_avg")
        Q_avg_st.save("q_avg")

        # compute signal^2 from running averages of I and Q values for live plotting
        (I_avg_st * I_avg_st + Q_avg_st * Q_avg_st).save_all("signal_sq_avg")

#############################        RUN MEASUREMENT        ############################

job = stg.qm.execute(time_rabi)  # run measurement
print(f"{meas_name} in progress...")  # log message
handle = job.result_handles

############################            POST-PROCESSING         ########################

plt.rcParams["figure.figsize"] = (12, 8)  # adjust figure size
handle.signal_sq_avg.wait_for_values(1)  # wait for at least 1 batch to be processed

while handle.is_processing():  # while the measurement is running

    ######################            FETCH PARTIAL RESULTS         ####################

    num_results = len(handle.signal_sq_avg)  # get result count so far
    signal_sq_avg = handle.signal_sq_avg.fetch(num_results - 1, flat_struct=True)
    signal_avg = np.sqrt(signal_sq_avg)  # calculate ys

    # calculate std error from raw data
    signal_sq_raw = handle.signal_sq_raw.fetch_all(flat_struct=True)
    signal_raw = np.sqrt(signal_sq_raw)
    mean_std_error = scipy.stats.sem(signal_raw, axis=0)

    ###################            LIVE PLOT PARTIAL RESULTS         ###################

    plt.cla()  # refresh
    plt.errorbar(
        times,
        signal_avg,
        yerr=mean_std_error,
        ls="none",
        lw=1,
        ecolor="red",
        marker="o",
        ms=4,
        mfc="black",
        mec="black",
        capsize=3,
    )
    plt.title(f"Time Rabi: {num_results} reps")
    plt.xlabel(f"Qubit pulse '{mdata['qubit_op']}' length (ns)")
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

fit_params = fit.do_fit(mdata["fit_func_name"], times, signal_avg)  # get fit parameters
ys_fit = fit.eval_fit(mdata["fit_func_name"], fit_params, times)  # get fit values
for name, value in fit_params.valuesdict().items():  # save fit parameters to metadata
    mdata[f"fit_param_{name}"] = value

##############################          PLOT RESULTS       #############################

plt.cla()  # refresh plot
plt.errorbar(  # plot final results as a scatter plot with errorbars
    times,
    signal_avg,
    yerr=mean_std_error,
    ls="none",
    lw=1,
    ecolor="red",
    marker="o",
    ms=4,
    mfc="black",
    mec="black",
    capsize=3,
    label="data",
)
plt.plot(times, ys_fit, color="m", lw=2, ls="--", label="fit")  # plot fitted values
plt.title(f"Time Rabi: {mdata['reps']} reps")
plt.xlabel(f"Qubit pulse '{mdata['qubit_op']}' length (ns)")
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
    file.create_dataset("ampxs", data=times)  # save frequency sweep values
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
elapsed_time = time.perf_counter() - start_time
print(f"\nExecution time: {str(timedelta(seconds=elapsed_time))}")
print("Here's the final plot :-) \n")

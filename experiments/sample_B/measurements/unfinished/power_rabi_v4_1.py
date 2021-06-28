# According to http://python-notes.curiousefficiency.org/en/latest/python_concepts/import_traps.html
# "Never add a package directory, or any directory inside a package, directly to the Python path"
# 1. the context in "__init__" in imports is not necessary, we can keep it empty 

import importlib

# importlib.reload(qcrew.experiments.sample_B.imports.configuration)
# "stage" only contains the instrument driver 
importlib.reload(qcrew.experiments.sample_B.imports.stage)
# if we want to hiden the modules imported and constants, we can import another module "info"
importlib.reload(qcrew.experiments.sample_B.imports.info)

##############        INFO      ##############
PROJECT = "squeezed_cat"
EXP_NAME = "power_rabi" 
SAMPLE_NAME =  "sample_B"
DATAPBASE_PATH = Path.cwd() / "data"

#############     PARAMETERS        ############
# which is better, abbreviation or complete writing
mdata = {  
    "reps": 40000,  # number of sweep repetitions
    "wait": 50000,  # in ns (mutiple of 4)
    "a_start": -2.0,  #
    "a_stop": 2.0,
    "a_step": 0.1,
    "qubit_op": "gaussian", 
    "rr_op": "readout",  
    "rr_op_ampx": 0.2,  
    "fit_fn": "sine",  
    "rr_lo_freq": stg.rr.lo_freq, 
    "rr_int_freq": stg.rr.int_freq, 
    "qubit_lo_freq": stg.qubit.lo_freq,  
    "qubit_int_freq": stg.qubit.int_freq,  
}

xs = np.arange(mdata["a_start"], mdata["a_stop"], mdata["a_step"])  
mdata["sweep_len"] = len(xs) 

##########################        DEFINE QUA PROGRAM        ############################

with program() as power_rabi:

    #####################        QUA VARIABLE DECLARATIONS        ######################

    n = declare(int)  
    a = declare(fixed) 

    I, Q = declare(fixed), declare(fixed)  
    I_st, Q_st = declare_stream(), declare_stream()  

    #######################        MEASUREMENT SEQUENCE        #########################

    with for_(n, 0, n < mdata["reps"], n + 1): 
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

start_time = time.perf_counter()  # to get measurement execution time

job = stg.qm.execute(power_rabi)

#############################        INVOKE HELPERS        #############################
datasaver = DummyDatasaver(sample_name=STAGE_NAME, filename_suffix=filename_suffix)
# NOTE I have written a simple __init__ method for the Datasaver class which generates folder and file paths and opens a new HDF5 file associated with this measurement run. You can add other methods e.g. save_metadata() and save_data() to this class.

fetcher = Fetcher(handle=job.result_handles, tags=datatags)
plotter = Plotter(title=meas_name, xlabel="Amplitude scale factor")
stats = tuple()  # tuple holding vars needed to calculate running std err in single pass

######################        SAVE MEASUREMENT RUN METADATA       ######################

# NOTE here, we should save the "mdata" dictionary to the HDF5 file. The idiomatic way of saving metadata in the HDF5 data model is via "Attributes". See https://docs.h5py.org/en/stable/high/attr.html.

##########################        POST-PROCESSING LOOP        ##########################

while fetcher.count < mdata["reps"]:  # while results from all reps are not fetched

    ######################            FETCH PARTIAL RESULTS         ####################

    prev_count = fetcher.count  # save previous result count before fetch() updates it
    partial_data = fetcher.fetch()  # return dict with (k, v) = (datatag, partial data)
    curr_count = fetcher.count  # get current number of fetched results
    if not partial_data:
        continue  # no new data available, go to beginning of post-processing loop

    ######################            SAVE FETCHED RESULTS         #####################

    # NOTE here, we should "live" save the latest batch of available results that "fetcher" has fetched. Fetch() returns "partial_data", where key = "datatag" and value = numpy array holding partial results from batch number "prev_count" to "curr_count". You can use "prev_count" and "curr_count" together with "mdata["sweep_len"]" and "mdata["reps"]" to track partial result array shapes. Note that the Datasaver class I've written has already opened the HDF5 file in its __init__ method, so there's no need for a with() statement, as long as the Datasaver closes the file at the end of this script. Please feel free to ask me any questions about this step, because its the most complex and critical step wrt data saving.

    ####################            PROCESS AVAILABLE RESULTS         ##################

    y_raw = np.sqrt(partial_data[datatags[2]])  # latest batch of y_raw
    y_avg = np.sqrt(partial_data[datatags[3]])  # latest batch of y_avg

    # BUG get_std_err() gives consistently higher values for std_err compared to scipy.stats.sem() or numpy.std().
    if stats:  # stats = (y_std_err, running average, running variance * (count-1))
        stats = get_std_err(y_raw, y_avg, curr_count, *stats)
    else:
        stats = get_std_err(y_raw, y_avg, curr_count)

    fit_params = fit.do_fit(mdata["fit_fn"], xs, y_avg[-1])  # get fit parameters
    y_fit = fit.eval_fit(mdata["fit_fn"], fit_params, xs)  # get fit values

    ###################            LIVE PLOT AVAILABLE RESULTS         #################

    plotter.live_plot(x=xs, y=y_avg[-1], n=curr_count, fit=y_fit, err=stats[0])
    time.sleep(0.2)  # to prevent over-querying QM and ultra-fast live plotting

###############################         SAVE PLOT         ##############################

# NOTE (OPTIONAL) here, we can save the final plot. If we want to do that, I suggest we save it in the same HDF5 file (HDF5 can save images too), so that each measurement run is associated with a single saved file.

#########################         DATASAVER WIND DOWN         ##########################

# NOTE use this block to do any final housekeeping for the Datasaver, such as flush, file close e.t.c.

###############################          fin           #################################

elapsed_time = time.perf_counter() - start_time
print(f"Measurement done! Execution time: {str(timedelta(seconds=elapsed_time))}")
print(job.execution_report())

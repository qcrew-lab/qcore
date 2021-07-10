"""
A python class describing a power rabi measurement using the QM 
system. 
This class serves as a QUA script generator with user-defined parameters. It 
also defines how the information is retrieved from result handles.
"""
# --------------------------------- Imports ------------------------------------
# Retrieves all necessary imports and initializes QM
from qcrew.experiments.coax_test.measurements.v5.BaseExperiment import *


# ---------------------------------- Class -------------------------------------


class PowerRabi(Experiment1D):
    def __init__(self, exp_params):
        super().__init__(exp_params)

    def QUA_pulse_sequence(self):
        """
        Defines pulse sequence to be played inside the experiment loop
        """

        play(self.qubit_op * amp(x), stg.qubit.name)
        align(stg.qubit.name, stg.rr.name)
        measure(
            self.rr_op * amp(self.rr_op_ampx),
            stg.rr.name,
            None,
            demod.full(self.integW1, I),
            demod.full(self.integW2, Q),
        )


# -------------------------------- Execution -----------------------------------


if __name__ == "__main__":

    #############        SETTING EXPERIMENT      ################

    exp_params = {
        "reps": 20000,  # number of sweep repetitions A
        "wait": 50000,  # delay between reps in ns, an integer multiple of 4 >= 16 A
        "x_start": -1.9,  # amplitude sweep range is set by start, stop, and step B
        "x_stop": 1.9,  # B
        "x_step": 0.1,  # B
        "qubit_op": "pi",  # qubit pulse name as defined in the config  A
        "rr_op": "readout",  # readout pulse name A
        "rr_op_ampx": 0.2,  # readout pulse amplitude scale factor A
        "fit_fn": "sine",  # name of the fit function B
        "rr_lo_freq": stg.rr.lo_freq,  # frequency of the local oscillator driving rr A
        "rr_int_freq": stg.rr.int_freq,  # frequency played by OPX to rr A
        "qubit_lo_freq": stg.qubit.lo_freq,  # frequency of local osc. driving qubit A
        "qubit_int_freq": stg.qubit.int_freq,  # frequency played by OPX to qubit A
        "integW1": "integW1",  # I integration weight A
        "integW2": "integW2",  # Q integration weight A
    }

    experiment = PowerRabi(exp_params)
    power_rabi = experiment.QUA_sequence()

    ###################        RUN MEASUREMENT        ############################

    job = stg.qm.execute(power_rabi)

    ###################        INVOKE HELPERS        #############################

    fetcher = Fetcher(handle=job.result_handles, num_results=experiment.reps)
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

    ###################        LIVE POST-PROCESSING LOOP        ##################

    with DataSaver(db) as datasaver:

        ############        SAVE MEASUREMENT RUN METADATA       ####################

        datasaver.add_metadata(exp_params)

        while fetcher.is_fetching:  # while the fetcher is not done fetching all results

            ###########            FETCH PARTIAL RESULTS         ##################

            partial_results = fetcher.fetch()  # key = tag, value = partial data
            num_results = fetcher.count  # get number of results fetched so far
            if (
                not partial_results
            ):  # empty dict return means no new results are available
                continue
            ##############            LIVE SAVE RESULTS         ######################

            # to only live save raw "I" and "Q" data, we extract them from "partial_results"
            live_save_dict = {
                "I": partial_results[experiment.I_tag],
                "Q": partial_results[experiment.Q_tag],
            }
            datasaver.update_multiple_results(live_save_dict, group="data")

            ######            CALCULATE RUNNING MEAN STANDARD ERROR         ############

            ys_raw = np.sqrt(partial_results[experiment.Y_SQ_RAW_tag])
            ys_raw_avg = np.sqrt(partial_results[experiment.Y_SQ_RAW_AVG_tag])
            stats = get_std_err(ys_raw, ys_raw_avg, num_results, *stats)

            ###########            LIVE PLOT AVAILABLE RESULTS         ###############

            ys = np.sqrt(
                partial_results[experiment.Y_AVG_tag]
            )  # latest batch of avg signal
            xs = partial_results[experiment.X_tag]
            plotter.live_plot(
                xs, ys, num_results, fit_fn=experiment.fit_fn, err=stats[0]
            )
            time.sleep(1)  # prevent over-fetching, over-saving, ulta-fast live plotting

        ###################         SAVE REMAINING DATA         ########################

        # to save final average and sweep variables, we extract them from
        # "partial_results"
        final_save_dict = {"Y_AVG": ys, "X": xs}
        datasaver.add_multiple_results(final_save_dict, group="data")
        # NOTE (OPTIONAL) here, we can also save the final plot.

    #########################          fin           #################################

    print(job.execution_report())

"""
A python class describing a power rabi measurement using the QM 
system. 
This class serves as a QUA script generator with user-defined parameters. It 
also defines how the information is retrieved from result handles.
"""
# --------------------------------- Imports ------------------------------------
# Retrieves all necessary imports and initializes QM
from qcrew.experiments.coax_test.measurements.v5.BaseExperiment_newlibs import *


# ---------------------------------- Class -------------------------------------


class PowerRabi(Experiment1D):
    def __init__(self, exp_params):

        # Retrieves operations
        self.qubit_op = exp_params.pop("qubit_op")
        self.readout_op = exp_params.pop("readout_op")

        # Passes other parameters to parent
        super().__init__(exp_params)

        # Names the modes to be used in the pulse sequence.
        self.qubit = self.mode_list[0]
        self.rr = self.mode_list[1]

    def QUA_pulse_sequence(self):
        """
        Defines pulse sequence to be played inside the experiment loop
        """

        self.qubit.play(self.qubit_op, self.x)
        align(self.qubit.name, self.rr.name)
        self.rr.measure(self.readout_op)  # This should account for intW
        wait(int(self.wait // 4), self.qubit.name)

        """
        play("pi" * amp(self.x), "qubit")
        align("qubit", "rr")
        measure(
            "readout" * amp(0.2),
            "rr",
            None,
            demod.full("integW1", self.I),
            demod.full("integW2", self.Q),
        )
        wait(int(32000 // 4), "qubit")
        """


# -------------------------------- Execution -----------------------------------


if __name__ == "__main__":

    #############        SETTING EXPERIMENT      ################

    qubit = stg.qubit  # TODO I'm assuming smth like this to get mode objects
    rr = stg.rr

    exp_params = {
        "reps": 20000,  # number of sweep repetitions
        "wait": 32000,  # delay between reps in ns, an integer multiple of 4 >= 16
        "mode_list": [qubit, rr],  # Modes to be used in the exp. (order matters)
        "qubit_op": "pi",  # Operations to be used in the exp.
        "readout_op": "readout",
        "x_start": -1.9,  # amplitude sweep range is set by start, stop, and step
        "x_stop": 1.9,
        "x_step": 0.1,
        "fit_fn": "sine",  # name eof the fit function
    }

    SAMPLE_NAME = "coax_a"
    EXP_NAME = "power_rabi"
    PROJECT_FOLDER_NAME = "coax_test"
    DATAPATH = Path.cwd() / "data"

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
            print(type(partial_results))
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

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

    #############        DATA SAVING PARAMETERS       ################

    save_params = {
        "SAMPLE_NAME": "coax_a",
        "EXP_NAME": "power_rabi",
        "PROJECT_FOLDER_NAME": "coax_test",
        "DATAPATH": Path.cwd() / "data",
    }

    ##############        PLOTTING PARAMETERS       #################

    plot_params = {
        "xlabel": "Amplitude scale factor",
    }

    #############        EXPERIMENT PARAMETERS       ################

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

    #################        RUN MEASUREMENT        ##################

    PowerRabi(exp_params, save_params).execute()

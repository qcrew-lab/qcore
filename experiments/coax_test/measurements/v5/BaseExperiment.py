from qcrew.experiments.coax_test.imports import *  # Opens QM
from abc import abstractmethod
import numpy as np

reload(cfg)
reload(stg)  # reload stage and configuration before each measurement run


class BaseExperiment:
    """
    Abstract base class for experiments using QUA sequences.
    """

    def __init__(self, exp_params):

        ### All of the lines below can be substituted by the code excerpt below.
        ### I don't know which is best, conciseness or clarity.
        """
        # Unpack dictionaries as attributes
        all_params = exp_params
        for key in all_params:
            setattr(self, key, all_params[key])
        """

        # Experiment loop variables
        self.reps = exp_params["reps"]
        self.wait_time = exp_params["wait_time"]

        ## The BaseExperiment class knows the modes and list of operations it can use.

        # List of operations to be used in the experiment
        # This will later be grouped in modes, each with multiple ops
        self.qubit_lo_freq = exp_params["qubit_lo_freq"]
        self.qubit_int_freq = exp_params["qubit_int_freq"]
        self.qubit_op = exp_params["qubit_op"]

        # Measurement at the end of each experiment
        # Hopefully this will be reduced to 2 variables: RO mode and RO op
        self.rr_op = exp_params["rr_op"]
        self.rr_op_ampx = exp_params["rr_op_ampx"]
        self.rr_lo_freq = exp_params["rr_lo_freq"]
        self.rr_int_freq = exp_params["rr_int_freq"]
        self.integW1 = exp_params["integW1"]
        self.integW2 = exp_params["integW2"]

    @abstractmethod
    def QUA_sequence(self):
        """
        Defines the QUA sequence of the experiment.
        """
        # Try making an attribute of some sort
        pass


class Experiment1D(BaseExperiment):
    def __init__(self, exp_params):

        # Get X sweep parameters
        self.x_start = exp_params.pop("x_start")
        self.x_step = exp_params.pop("x_step")
        self.x_stop = exp_params.pop("x_stop") + self.x_step / 2  # Corrects x_stop
        self.x_sweep_len = len(np.arange(x_start, x_stop + x_step / 2, x_step))
        self.fit_fn = exp_params.pop("fit_fn")

        # Send the rest to parent
        super().__init__(exp_params)

        # Result tags for stream processing 1D experiments
        self.I_tag = "I"
        self.Q_tag = "Q"
        self.Y_SQ_RAW_tag = "Y_SQ_RAW"
        self.Y_SQ_RAW_AVG_tag = "Y_SQ_RAW_AVG"
        self.Y_AVG_tag = "Y_AVG"
        self.X_tag = "X"

    @abstractmethod
    def QUA_pulse_sequence(self):
        """
        Macro that defines the QUA pulse sequence inside the experiment loop. It is
        specified by the experiment (spectroscopy, power rabi, etc.) in the child class.
        """
        pass

    def QUA_variable_declaration(self):
        """
        Macro that calls QUA variable declaration statements. 1D sweeps are concerned
        only with a x sweep variable and I, Q results. Note that variables and streams
        need to be explicitly returned to the QUA function to be in scope
        """
        n = declare(int)  # averaging loop variable
        x = declare(fixed)  # sweep variable "x"
        x_stream = declare_stream()  # to save "x"
        I = declare(fixed)  # result variable "I"
        I_stream = declare_stream()  # to save "I"
        Q = declare(fixed)  # result variable "Q"
        Q_stream = declare_stream()  # to save "Q"

        return n, x, x_stream, I, I_stream, Q, Q_stream

    def QUA_save_results_to_stream(self):
        """
        Macro that calls QUA save statements. QUA variables x, I, Q and respective
        streams are defined in method QUA_variable_declaration
        """

        save(x, x_stream)
        save(I, I_stream)
        save(Q, Q_stream)

    def QUA_stream_processing(self):
        """
        Macro that calls QUA save statements. QUA variables x, I, Q and respective
        streams are defined in method QUA_variable_declaration
        """
        # Try making an attribute of some sort
        with stream_processing():
            I_raw = I_stream.buffer(self.x_sweep_len)
            Q_raw = Q_stream.buffer(self.x_sweep_len)  # to reshape result streams
            I_avg = I_raw.average()
            Q_avg = Q_raw.average()  # to get running averages

            I_raw.save_all(self.I_tag)
            Q_raw.save_all(self.Q_tag)  # to save all raw I and Q data

            # we need these two streams to calculate std err in a single pass
            (I_raw * I_raw + Q_raw * Q_raw).save_all(self.Y_SQ_RAW_tag)
            (I_raw * I_raw + Q_raw * Q_raw).average().save_all(self.Y_SQ_RAW_AVG_tag)

            (I_avg * I_avg + Q_avg * Q_avg).save(
                self.Y_AVG_tag
            )  # to live plot latest average
            x_stream.buffer(self.x_sweep_len).save(self.X_tag)  # sweep variable

    def QUA_sequence(self):
        """
        Method that returns the QUA sequence to be executed in the quantum machine.
        """

        with program() as qua_sequence:

            # Initial variable declaration
            _ = self.QUA_variable_declaration()
            n, x, x_stream, I, I_stream, Q, Q_stream = _

            # Experiment loop
            with for_(n, 0, n < self.reps, n + 1):
                with for_(x, self.x_start, x < self.x_stop, x + self.x_step):
                    self.QUA_pulse_sequence()  # TODO check if it can be done
                    self.QUA_save_results_to_stream()
                    wait(int(self.wait_time // 4), stg.qubit.name)  # TODO hardcorded

            self.QUA_stream_processing()

        return qua_sequence

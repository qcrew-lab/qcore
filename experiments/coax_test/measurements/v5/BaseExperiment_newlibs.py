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

        # Experiment loop variables
        self.reps = exp_params["reps"]
        self.wait_time = exp_params["wait_time"]

        # List of modes to be used in the experiment. The base class does not
        # differentiate between readout and control modes.
        self.mode_list = exp_params["mode_list"]

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
        self.x_sweep_len = len(np.arange(self.x_start, self.x_stop, self.x_step))
        # Fit function
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

            # to live plot latest average
            (I_avg * I_avg + Q_avg * Q_avg).save(self.Y_AVG_tag)
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
                    self.QUA_pulse_sequence()
                    self.QUA_save_results_to_stream()

            self.QUA_stream_processing()

        return qua_sequence

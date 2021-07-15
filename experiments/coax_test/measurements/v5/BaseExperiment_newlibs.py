from qcrew.experiments.coax_test.imports import *  # Opens QM
from abc import abstractmethod
import numpy as np


class Experiment:
    """
    Abstract class for experiments using QUA sequences.
    """

    def __init__(
        self,
        reps,
        wait_time,
        x_sweep,
        is_x_explicit,
        y_sweep=None,
        is_y_explicit=None,
        extra_QUA_var=None,
    ):

        # Experiment loop variables
        self.reps = reps
        self.wait_time = wait_time

        # Sweep configurations
        self.sweep_config = {"n": (0, self.reps, 1), "x": x_sweep, "y": y_sweep}
        self.is_sweep_explicit = {"n": False, "x": is_x_explicit, "y": is_y_explicit}
        self.buffering = tuple()  # defined in _check_sweeps

        # QUA variable definitions {name:type}
        self.QUA_var_list = {
            "n": int,
            "x": None,  # defined in _check_sweeps
            "y": None,
            "I": fixed,
            "Q": fixed,
        }

        # List of variables to be sent to streams. More added in _check_sweeps
        self.QUA_stream_list = ["I", "Q"]

        # Set attributes for QUA variables (specified in QUA_variable_declaration)
        for var_name in self.QUA_var_list.keys():
            setattr(self, var_name, None)

        # Set attributes for QUA streams (specified in QUA_stream_declaration)
        # Also set attributes for server memory tags
        for stream_name in self.QUA_stream_list:
            setattr(self, stream_name + "_stream", None)
            setattr(self, stream_name + "_tag", None)

        # Extra memory tags for saving server-side stream operation results
        self.Z_SQ_RAW_tag = "Z_SQ_RAW"
        self.Z_SQ_RAW_AVG_tag = "Z_SQ_RAW_AVG"
        self.Z_AVG_tag = "Z_AVG"

    def _check_sweeps(self):
        """
        Check if each x and y sweeps are correctly configured. If so, update buffering, QUA_var_list, and QUA_stream_list accordingly.
        """

        buffering = list()
        for sweep_dim in ["x", "y"]:

            if self.sweep_config[sweep_dim] == None:
                # Sweep is not configured. No need for updates.
                continue

            # Assign stream to configured sweep
            self.QUA_stream_list.append(sweep_dim)

            # Retrieve explicit sweep values from available info
            sweep_array = list()
            if self.is_sweep_explicit[sweep_dim]:
                # Sweep values are explicitly defined
                sweep_array = self.sweep_config[sweep_dim]
            else:
                # Sweep values are not explicitly defined
                _ = self.sweep_config[sweep_dim]
                start, stop, step = _  # Unpack start, stop, step
                sweep_array = np.arange(start, stop + step / 2, step)  # Build array

            # Check data type and update QUA_var_list
            if all(isinstance(s, int) for s in sweep_array):
                self.QUA_var_list[sweep_dim] = int
            else:
                self.QUA_var_list[sweep_dim] = fixed

            buffering.append(len(sweep_array))

        # Update buffering
        self.buffering = tuple(buffering)

        return

    def QUA_sequence(self):
        """
        Method that returns the QUA sequence to be executed in the quantum machine.
        """

        # Check if the sweep configurations are sane
        self._check_sweeps()
        # print(self.QUA_var_list)
        # print(self.QUA_stream_list)
        # print(self.buffering)
        with program() as qua_sequence:

            # Initial variable and stream declarations
            self.QUA_declare_variables()
            self.QUA_declare_streams()

            # Experiment loop
            self.QUA_sweep(
                "n",
                self.QUA_sweep("x", self.QUA_sweep("y", self.QUA_play_pulse_sequence)),
            )

            # Define stream processing
            self.QUA_do_stream_processing()

        return qua_sequence

    ############### Definition of Macros used in QUA_sequence ###############

    def QUA_declare_variables(self):
        """
        Macro that calls QUA variable declaration statements. The variables are
        specified in QUA_var_list.
        """
        for key, val in self.QUA_var_list.items():
            if val:
                setattr(self, key, declare(val))

    def QUA_declare_streams(self):
        """
        Macro that calls QUA stream declaration statements. The streams are
        specified in QUA_stream_list. The "_stream" description is appended to the
        attribute name. Corresponding memory tag attributes are defined with a "_tag"
        appendix.
        """
        for var in self.QUA_stream_list:
            # Declare stream
            setattr(self, var + "_stream", declare_stream())
            # Define a memory tag for data saving
            setattr(self, var + "_tag", var)

    def QUA_sweep(self, sweep_dim, QUA_function):
        """
        Macro that sets up configured sweeps with qua.for_ or qua.for_all_ loops
        depending on the need.
        """

        # If sweep is not configured, simply play function
        if self.QUA_var_list[sweep_dim] == None:
            QUA_function()
            return

        # Get sweep variable
        sweep_var = getattr(self, sweep_dim)

        # Check the type of the loop
        if self.is_sweep_explicit[sweep_dim]:
            # Get array of values to sweep over
            loop_array = self.sweep_config[sweep_dim]
            # Wrap function in qua.for_all_ loop
            with for_all_(sweep_var, loop_array):
                QUA_function()
        else:
            # Wrap function in qua.for_ loop
            start, stop, step = self.sweep_config[sweep_dim]
            with for_(sweep_var, start, sweep_var < stop + step / 2, sweep_var + step):
                QUA_function()

    @abstractmethod
    def QUA_play_pulse_sequence(self):
        """
        Macro that defines the QUA pulse sequence inside the experiment loop. It is
        specified by the experiment (spectroscopy, power rabi, etc.) in the child class.
        """
        pass

    def QUA_stream_results(self):
        """
        Macro that calls QUA save statements. This streams variable values flagged in
        QUA_stream_list to corresponding streams. It should be called in
        QUA_play_pulse_sequence.
        """
        for var in self.QUA_stream_list:
            save(getattr(self, var), getattr(self, var + "_stream"))

    def QUA_do_stream_processing(self):
        """
        Macro that opens QUA stream_processing() context manager and executes (1) the
        results (I, Q) stream processing and (2) other variable's processing.
        """
        with stream_processing():
            self.QUA_process_IQ()
            self.QUA_process_other()

    def QUA_process_IQ(self):
        """
        Macro that stores I and Q results from corresponding streams in server memory
        locations identified by tags. Also set up extra server-side stream calculations
        and save those in memory for live plot and standard error estimation.
        """
        # Is and Qs
        I_raw = self.I_stream.buffer(**self.buffering)
        Q_raw = self.Q_stream.buffer(**self.buffering)  # to reshape result streams
        I_avg = I_raw.average()
        Q_avg = Q_raw.average()
        I_raw.save_all(self.I_tag)
        Q_raw.save_all(self.Q_tag)

        # we need these two streams to calculate std err in a single pass
        (I_raw * I_raw + Q_raw * Q_raw).save_all(self.Z_SQ_RAW_tag)
        (I_raw * I_raw + Q_raw * Q_raw).average().save_all(self.Z_SQ_RAW_AVG_tag)

        # to live plot latest average
        (I_avg * I_avg + Q_avg * Q_avg).save(self.Z_AVG_tag)

    def QUA_process_other(self):
        """
        Macro that stores non-I,Q results from corresponding streams in server memory
        locations identified by tags.
        """
        for var in self.QUA_stream_list:
            if var in {"I", "Q"}:
                # This processing is done in QUA_process_IQ
                continue
            stream = getattr(self, var + "_stream")
            memory_tag = getattr(self, var + "_tag")
            stream.buffer(**self.buffering).save(memory_tag)

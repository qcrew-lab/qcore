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

        # ExpVariable definitions. This list is updated in _check_sweeps and after
        # stream and variable declaration.
        self.var_list = {
            "n": macros.ExpVariable(var_type=int),
            "x": macros.ExpVariable(average=False, save_all=False),
            "y": macros.ExpVariable(average=False, save_all=False),
            "I": macros.ExpVariable(tag="I", var_type=fixed),
            "Q": macros.ExpVariable(tag="Q", var_type=fixed),
        }

        # Extra memory tags for saving server-side stream operation results
        self.Z_SQ_RAW_tag = "Z_SQ_RAW"
        self.Z_SQ_RAW_AVG_tag = "Z_SQ_RAW_AVG"
        self.Z_AVG_tag = "Z_AVG"

    def _check_sweeps(self):
        """
        Check if each x and y sweeps are correctly configured. If so, update buffering, variable type, and tag of x and y in var_list accordingly.
        """

        buffering = list()
        for sweep_dim in ["x", "y"]:

            if self.sweep_config[sweep_dim] is None:
                # Sweep is not configured. No need for updates.
                continue

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

            # Check data type and update var_list
            if all(isinstance(s, int) for s in sweep_array):
                self.var_list[sweep_dim].type = int
            else:
                self.var_list[sweep_dim].type = fixed

            # Since sweep is configure, define memory tag for data saving
            self.var_list[sweep_dim].tag = sweep_dim
            buffering.append(len(sweep_array))

        # Update buffering
        self.buffering = tuple(buffering)

        return

    @abstractmethod
    def QUA_play_pulse_sequence(self):
        """
        Macro that defines the QUA pulse sequence inside the experiment loop. It is
        specified by the experiment (spectroscopy, power rabi, etc.) in the child class.
        """
        pass

    def QUA_sequence(self):
        """
        Method that returns the QUA sequence to be executed in the quantum machine.
        """

        # Check if the sweep configurations are sane
        self._check_sweeps()

        with program() as qua_sequence:

            # Initial variable and stream declarations
            self.var_list = macros.declare_variables(self.var_list)
            self.var_list = macros.declare_streams(self.var_list)

            # Stores QUA variables as attributes for easy use
            for key, value in self.var_list.items():
                setattr(self, key, value.var)

            # Experiment loop
            # Repetition loop
            with for_(self.n, 0, self.n < self.reps, self.n + 1):

                sweep_types = [self.is_sweep_explicit["x"], self.is_sweep_explicit["y"]]

                # If only x sweep is configured
                if self.var_list["y"].var is None:
                    if sweep_types[0] == False:
                        x_loop_array = x_start, x_stop, x_step = self.sweep_config["x"]
                        with for_(
                            self.x,
                            x_start,
                            self.x < x_stop + x_step / 2,
                            self.x + x_step,
                        ):
                            self.QUA_play_pulse_sequence()
                    else:
                        x_loop_array = self.sweep_config["x"]
                        with for_each_(self.x, x_loop_array):
                            self.QUA_play_pulse_sequence()

                # If both x and y sweeps are configured

                # Neither x nor y sweep values are explicitly defined
                elif sweep_types == [False, False]:
                    x_loop_array = x_start, x_stop, x_step = self.sweep_config["x"]
                    y_loop_array = y_start, y_stop, y_step = self.sweep_config["y"]
                    x_stop += x_step / 2
                    y_stop += y_step / 2
                    with for_(self.x, x_start, self.x < x_stop, self.x + x_step):
                        with for_(self.y, y_start, self.y < y_stop, self.y + y_step):
                            self.QUA_play_pulse_sequence()

                # y sweep values are explicitly defined
                elif sweep_types == [False, True]:
                    x_loop_array = x_start, x_stop, x_step = self.sweep_config["x"]
                    y_loop_array = self.sweep_config["y"]
                    x_stop += x_step / 2
                    with for_(self.x, x_start, self.x < x_stop, self.x + x_step):
                        with for_each_(self.y, y_loop_array):
                            self.QUA_play_pulse_sequence()

                # x sweep values are explicitly defined
                elif sweep_types == [True, False]:
                    x_loop_array = self.sweep_config["x"]
                    y_loop_array = y_start, y_stop, y_step = self.sweep_config["y"]
                    y_stop += y_step / 2
                    with for_each_(self.x, x_loop_array):
                        with for_(self.y, y_start, self.y < y_stop, self.y + y_step):
                            self.QUA_play_pulse_sequence()

                # Both x and y sweep values are explicitly defined
                elif sweep_types == [True, True]:
                    x_loop_array = self.sweep_config["x"]
                    y_loop_array = self.sweep_config["y"]
                    with for_each_(self.x, x_loop_array):
                        with for_each_(self.y, y_loop_array):
                            self.QUA_play_pulse_sequence()

            # Define stream processing
            buffer_len = np.prod(self.buffering)
            with stream_processing():
                macros.process_streams(self.var_list, buffer_len=buffer_len)
                macros.process_Z_values(
                    self.var_list["I"].stream,
                    self.var_list["Q"].stream,
                    buffer_len=buffer_len,
                )
        return qua_sequence

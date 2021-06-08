""" Run this script as-is. It prints results to stdout"""
""" Please copy-paste the offsets into the config file in the appropriate place """
""" So that the OPX can apply them the next time you run a measurement """
import time

import matplotlib.pyplot as plt
import numpy as np
from qm.qua import infinite_loop_, play, program
from scipy.optimize import minimize

from qcrew.codebase.instruments import MetaInstrument, QuantumElement, Sa124
from qcrew.experiments.coax_test.imports.stage import qubit, rr, qm, lb_qubit, lb_rr

DEFAULT_NAME = "mixer_tuner"

# default minimization parameters
# these will be used only if initial guesses from prior tuning are not available

# Nelder-Mead works well in our case, so let's not to change it unless necessary
DEFAULT_METHOD = "Nelder-Mead"

# initial simplex guess
# the guesses below have been informed by the offset bounds and scans of the
# entire function landscape and by the values used by QM in their script
# the global minimum is very likely inside this initial simplex, which is ideal
DEFAULT_INIT_SIMPLEX_LO = np.array([[0.0, 0.0], [0.0, 0.1], [0.1, 0.0]])
DEFAULT_INIT_SIMPLEX_SB = np.array([[0.0, 0.0], [0.0, 0.1], [0.1, 0.0]])

# absolute error in xopt between iterations that is acceptable for convergence
# algo stops as soon as |x(n) - x(n+1)| < xatol
DEFAULT_XATOL = 0.0001

# absolute error in func(xopt) between iterations that is acceptable
# algo stops as soon as |f(x_n) - f(x_(n+1))| < fatol
# if no prior tuning, mixer tuner tunes to within this tolerance
# if prior tuning, mixer tuner tunes only if frequency component > stdev
DEFAULT_FATOL = 1

DEFAULT_MAXITER = 100  # hundred iterations should be more than enough

# sweep acquisition parameters
COARSE_SWEEP_RBW = 250e3
COARSE_SWEEP_SPAN_SCALAR = 4
FINE_SWEEP_RBW = 50e3
FINE_SWEEP_SPAN_SCALAR = 1e-3

# get qua program to run
# assume element has pulse 'CW' defined - pls change this in the future
def get_qua_program(element: QuantumElement):
    with program() as qua_program:
        with infinite_loop_():
            play("CW", element.name)  # TODO remove hard coding
    return qua_program


# this fn must be a property of OPX
def mixer_correction(gain_offset, phase_offset):
    # returns mixer correction matrix from gain and phase imbalances
    cos = np.cos(phase_offset)
    sin = np.sin(phase_offset)
    coeff = 1 / ((1 - gain_offset ** 2) * (2 * cos ** 2 - 1))
    return [
        float(coeff * x)
        for x in [
            (1 - gain_offset) * cos,
            (1 + gain_offset) * sin,
            (1 - gain_offset) * sin,
            (1 + gain_offset) * cos,
        ]
    ]


class MixerTuner(MetaInstrument):
    """
    TODO write proper docu
    """

    def __init__(self, sa: Sa124, qm, name: str = DEFAULT_NAME, **parameters):
        self.sa = sa
        self.qm = qm
        super().__init__(name, **parameters)

    # public methods
    def tune(self, *elements):
        self._tune(*elements, is_tune_lo=True, is_tune_sb=True)

    def tune_lo(self, *elements):
        self._tune(*elements, is_tune_lo=True, is_tune_sb=False)

    def tune_sb(self, *elements):
        self._tune(*elements, is_tune_lo=False, is_tune_sb=True)

    # internal methods
    def _tune(self, *elements, is_tune_lo: bool, is_tune_sb: bool):
        if not elements:
            print("ERROR: no elements passed, what are you even tuning?")
            return

        for element in elements:
            if not isinstance(element, QuantumElement):
                print(type(element))
                print("ERROR: element must be QuantumElement... moving on...")
                continue

            # TODO break assumption that carrier freq is being played to element
            job = self.qm.execute(get_qua_program(element))  # play int freq to element

            # show coarse sweep before tuning
            print("Coarse sweep before tuning {} mixer...".format(element.name))
            self._get_coarse_sweep(element)

            if is_tune_lo:
                self._tune_lo(element)
            if is_tune_sb:
                self._tune_sb(element)

            job.halt()

    def _tune_lo(self, element: QuantumElement):
        # int freq is alr playing to element

        # get and show fine sweep
        # this also configures the SA for minimization (desired side effect)
        print("Zooming in to {} LO leakage...".format(element.name))
        freqs, amps = self._get_fine_sweep(element.lo_freq)

        # find signal floor and stdev from fine sweep
        floor, stdev = np.mean(amps), np.std(amps)
        print("Floor (~mean): {:.5}dB, stdev: {:.5}dB".format(floor, stdev))

        # check if already tuned
        init_amp = amps[np.searchsorted(freqs, element.lo_freq)]
        init_contrast = init_amp - floor
        print("amp: {:.5}dB, contrast: {:.5}dB".format(init_amp, init_contrast))
        print()  # spacer

        is_tuned = False  # temp hotfix
        # is_tuned = abs(init_contrast) < abs(stdev)

        objective_fn = self._get_lo_callback_fn(element)

        if is_tuned:
            # already tuned, apply current offsets, show coarse sweep, exit
            # print("Already tuned! Applying offsets...")
            offsets = [element.mixer.i_offset, element.mixer.q_offset]
            objective_fn(offsets, floor)
        else:
            # use default guesses if none available as attributes
            init_simplex = getattr(self, "init_simplex_lo", DEFAULT_INIT_SIMPLEX_LO)
            # perform minimization
            results = self._minimize(element, objective_fn, init_simplex, floor)
            # save results
            element.mixer.i_offset = results[0]
            element.mixer.q_offset = results[1]

    def _get_lo_callback_fn(self, element: QuantumElement):
        elem_name = element.name
        lo_freq = element.lo_freq

        def objective_fn(offsets, *args):
            floor = args[0]
            self.qm.set_output_dc_offset_by_element(elem_name, "I", offsets[0])
            self.qm.set_output_dc_offset_by_element(elem_name, "Q", offsets[1])
            freqs, amps = self.sa.sweep()  # guaranteed to be configured properly
            # guaranteed that sa output is sorted
            amp_at_lo_freq = amps[np.searchsorted(freqs, lo_freq)]
            contrast = abs(amp_at_lo_freq - floor)
            # print string for debugging
            print(
                "I: {:.5}, Q: {:.5}, contrast: {:.5}".format(
                    offsets[0], offsets[1], contrast
                )
            )
            return contrast

        return objective_fn

    def _tune_sb(self, element: QuantumElement):
        # int freq is alr playing to element

        # get and show fine sweep
        # this also configures the SA for minimization (desired side effect)
        print("Zooming in to {} SB leakage...".format(element.name))
        # int_freq is the sideband we want to keep, we want to remove sb_freq
        sb_freq = element.lo_freq - element.int_freq
        freqs, amps = self._get_fine_sweep(sb_freq)

        # find signal floor and stdev from fine sweep
        floor, stdev = np.mean(amps), np.std(amps)
        print("Floor (~mean): {:.5}dB, stdev: {:.5}dB".format(floor, stdev))

        # check if already tuned
        init_amp = amps[np.searchsorted(freqs, sb_freq)]
        init_contrast = init_amp - floor
        print("amp: {:.5}dB, contrast: {:.5}dB".format(init_amp, init_contrast))
        print()  # spacer
        # is_tuned = abs(init_contrast) < abs(stdev)
        is_tuned = False  # temp hotfix

        objective_fn = self._get_sb_callback_fn(element)

        if is_tuned:
            # already tuned, apply current offsets, show coarse sweep, exit
            # print("Already tuned! Applying offsets...")
            offsets = [element.mixer.gain_offset, element.mixer.phase_offset]
            objective_fn(offsets, floor)
        else:
            # use default guesses if none available as attributes
            init_simplex = getattr(self, "init_simplex_sb", DEFAULT_INIT_SIMPLEX_SB)
            # perform minimization
            results = self._minimize(element, objective_fn, init_simplex, floor)
            # save results
            element.mixer.gain_offset = results[0]
            element.mixer.phase_offset = results[1]

    def _get_sb_callback_fn(self, element: QuantumElement):
        mixer_name = element.mixer.name  # assume element has only 1 mixer
        sb_freq = element.lo_freq - element.int_freq

        def objective_fn(offsets, *args):
            floor = args[0]
            self.qm.set_mixer_correction(
                mixer_name,
                int(element.int_freq),
                int(element.lo_freq),
                mixer_correction(offsets[0], offsets[1]),
            )
            freqs, amps = self.sa.sweep()  # guaranteed to be configured properly
            # guaranteed that sa output is sorted
            amp_at_sb_freq = amps[np.searchsorted(freqs, sb_freq)]
            contrast = abs(amp_at_sb_freq - floor)

            # print string for debugging
            print(
                "G: {:.5}, P: {:.5}, contrast: {:.5}".format(
                    offsets[0], offsets[1], contrast
                )
            )
            return contrast

        return objective_fn

    def _minimize(self, element, objective_fn, init_simplex, floor):
        # start_time = time.perf_counter()
        # print("Performing minimization...")

        # set minimization parameters
        # set to default if none available as attributes
        method = getattr(self, "method", DEFAULT_METHOD)
        xatol = getattr(self, "xatol", DEFAULT_XATOL)
        fatol = getattr(self, "fatol", DEFAULT_FATOL)
        max_iter = getattr(self, "max_iter", DEFAULT_MAXITER)
        # print(
        #    "method: {}, init_simplex: {}, xatol: {}, fatol: {}, max_iter: {}".format(
        #        method, init_simplex, xatol, fatol, max_iter
        #    )
        # )

        # perform minimization and give results, time it, plot final sweep
        # call scipy optimize minimize fn with nelder-mead method
        result = minimize(
            objective_fn,
            [0, 0],
            args=(floor),
            method=method,
            options={
                "xatol": xatol,
                "fatol": fatol,
                "initial_simplex": init_simplex,
                "maxiter": max_iter,
                "disp": True,
            },
        )

        if result.success:
            results = result.x
            # apply the offsets
            # print("Applying offsets...")
            objective_fn(results, floor)
        else:
            # TODO get best results from minimization routine and apply them
            print("Sorry, tuning failed...")
            # print(
            #    "Meanwhile, please inspect the print stream and "
            #    + "set offsets manually..."
            # )

        # show time elapsed
        # elapsed_time = time.perf_counter() - start_time
        # print("Minimization took {:.5}s".format(elapsed_time))

        # show a coarse sweep after tuning
        print("Coarse sweep after tuning {} mixer...".format(element.name))
        self._get_coarse_sweep(element)

        return results

    def _get_sweep(self, **parameters):
        # start_time = time.perf_counter()
        freqs, amps = self.sa.sweep(**parameters)
        plt.plot(freqs, amps)
        plt.show()
        # elapsed_time = time.perf_counter() - start_time
        # print("Sweep took {:.5}s".format(elapsed_time))
        # print()  # spacer
        return (freqs, amps)

    def _get_coarse_sweep(self, element: QuantumElement):
        return self._get_sweep(
            center=element.lo_freq,
            span=abs(element.int_freq * COARSE_SWEEP_SPAN_SCALAR),
            rbw=COARSE_SWEEP_RBW,
        )

    def _get_fine_sweep(self, center):
        return self._get_sweep(
            center=center, span=center * FINE_SWEEP_SPAN_SCALAR, rbw=FINE_SWEEP_RBW
        )

    def _create_yaml_map(self):
        return {"name": self.name}

    @property
    def parameters(self):
        return "WORK IN PROGRESS"


if __name__ == "__main__":
    # AJ - I wrote this in a hurry, please pardon the bad coding practices
    sa = Sa124(name="sa", serial_number=19184645)
    lb_qubit.frequency = qubit.lo_freq
    lb_rr.frequency = rr.lo_freq
    mixer_tuner = MixerTuner(sa=sa, qm=qm)

    print("\n" * 30)
    print("Mixer Tuner is running, please wait for about 30s...")
    start_time = time.perf_counter()

    mixer_tuner.tune_sb(rr)

    print("\n" * 3)

    elapsed_time = time.perf_counter() - start_time
    print(f"MixerTuner took {elapsed_time:.3}s!!!")

    print("\n" * 3)

    print(f"Results for '{qubit.name}':")
    print(f'"I": {qubit.mixer.i_offset},')
    print(f'"Q": {qubit.mixer.q_offset},')
    print(f'"G": {qubit.mixer.gain_offset},')
    print(f'"P": {qubit.mixer.phase_offset}')

    print("\n" * 3)

    print(f"Results for '{rr.name}':")
    print(f'"I": {rr.mixer.i_offset},')
    print(f'"Q": {rr.mixer.q_offset},')
    print(f'"G": {rr.mixer.gain_offset},')
    print(f'"P": {rr.mixer.phase_offset}')

    print("\n" * 3)

    print("Please copy paste these results in the QM config!")
    print("\n" * 20)

    sa.disconnect()

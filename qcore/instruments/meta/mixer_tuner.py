"""
Mixer Tuner meta instrument

Has access to foll. instruments:
- sa, to acquire spectrums
- qm, to play int freq signal
- the element whose mixer is being tuned

FOR NOW, ASSUME THAT LABBRICKS ARE ALR PLAYING APPROPRIATELY!!! THIS WILL
CHANGE IN THE NEAR FUTURE AS THE LBS BECOME PROPERTIES OF ELEMENTS.

CURRENTLY, OFFSETS ARE PROPERTY OF ELEMENT
"""
import time

import matplotlib.pyplot as plt
import numpy as np
from qm.qua import infinite_loop_, play, program
from scipy.optimize import minimize

from instruments import MetaInstrument, QuantumElement, Sa124

# minimization parameters
# absolute error in xopt between iterations that is acceptable for convergence
XATOL = 1e-4 # change in DC offset or gain/phase, number obtained from qm

# absolute error in func(xopt) between iterations that is acceptable
FATOL = 3

MAXITER = 50 # should be more than enough

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
            play('CW', element.name) # TODO remove hard coding
    return qua_program

# this fn must be a property of OPX
def mixer_correction(gain_offset, phase_offset):
    cos = np.cos(phase_offset)
    sin = np.sin(phase_offset)
    coeff = 1 / ((1 - gain_offset ** 2) * (2 * cos ** 2 - 1))
    return [float(coeff * x) for x in [(1 - gain_offset) * cos,
                                   (1 + gain_offset) * sin,
                                   (1 - gain_offset) * sin,
                                   (1 + gain_offset) * cos]]

class MixerTuner(MetaInstrument):
    """
    TODO write proper docu

    what should be inputs - the instruments, some sweep params, some optim
    params?
    """
    def __init__(self, name: str, sa: Sa124, qm, **parameters):
        self.sa = sa
        self.qm = qm
        super().__init__(name, **parameters)

    # public methods
    def tune(self, elements: set[QuantumElement]):
        self._tune(elements, is_tune_lo=True, is_tune_sb=True)

    def tune_lo(self, elements: set[QuantumElement]):
        self._tune(elements, is_tune_lo=True, is_tune_sb=False)

    def tune_sb(self, elements: set[QuantumElement]):
        self._tune(elements, is_tune_lo=False, is_tune_sb=True)

    # internal methods
    def _tune(self, elements: set[QuantumElement], is_tune_lo: bool,
              is_tune_sb: bool):
        if elements is None:
            print('ERROR: elements cannot be None, what are you even tuning?')
            return

        for element in elements:
            if not isinstance(element, QuantumElement):
                print('ERROR: element must be QuantumElement... moving on...')
                continue

            # TODO break assumption that carrier freq is being played to element
            self.qm.execute(get_qua_program(element)) # play int freq to element

            if is_tune_lo:
                self._tune_lo(element)
            if is_tune_sb:
                self._tune_sb(element)

    def _tune_lo(self, element: QuantumElement):
        # int freq is alr playing to element
        # show a fine sweep before tuning
        # this also configures the SA for minimization (desired side effect)
        print('Here is the current {} LO leakage...'.format(element.name))
        self._show_fine_sweep(element.lo_freq)

        # remove hard coding, get element to return its offsets...
        init_guesses = [element.mixer.i_offset, element.mixer.q_offset]
        objective_fn = self._get_lo_callback_fn(element)

        # get and save minimization results
        results = self._minimize(element, objective_fn, init_guesses)
        element.mixer.i_offset, element.mixer.q_offset = results[0], results[1]

    def _get_lo_callback_fn(self, element: QuantumElement):
        elem_name = element.name
        lo_freq = element.lo_freq
        def objective_fn(offsets):
            self.qm.set_output_dc_offset_by_element(elem_name, 'I', offsets[0])
            self.qm.set_output_dc_offset_by_element(elem_name, 'Q', offsets[1])
            freqs, amps = self.sa.sweep() # must already be configured properly
            # guaranteed that sa output is sorted
            amp_to_minimize = amps[np.searchsorted(freqs, lo_freq)]
            # print string for debugging
            print('I: {:.5}, Q: {:.5}, amp: {:.5}'.format(offsets[0],
                                                          offsets[1],
                                                          amp_to_minimize))
            return amp_to_minimize
        return objective_fn

    def _tune_sb(self, element: QuantumElement):
        # int freq is alr playing to element
        # show a fine sweep before tuning
        # this also configures the SA for minimization (desired side effect)
        print('Here is the current {} SB to suppress...'.format(element.name))
        # int_freq is the sideband we want to keep
        self._show_fine_sweep(element.lo_freq - element.int_freq)

        # remove hard coding, get element to return its offsets...
        init_guesses = [element.mixer.gain_offset, element.mixer.phase_offset]
        objective_fn = self._get_sb_callback_fn(element)

        results = self._minimize(element, objective_fn, init_guesses)
        element.mixer.gain_offset = results[0]
        element.mixer.phase_offset = results[1]

    def _get_sb_callback_fn(self, element: QuantumElement):
        mixer_name = element.mixer.name # assume element has only 1 mixer
        sb_freq = element.lo_freq - element.int_freq
        def objective_fn(offsets):
            self.qm.set_mixer_correction(mixer_name, element.int_freq,
                                         element.lo_freq,
                                         mixer_correction(offsets[0],
                                                       offsets[1]))
            freqs, amps = self.sa.sweep() # must already be configured properly
            # guaranteed that sa output is sorted
            amp_to_minimize = amps[np.searchsorted(freqs, sb_freq)]
            # print string for debugging
            print('G: {:.5}, P: {:.5}, amp: {:.5}'.format(offsets[0],
                                                          offsets[1],
                                                          amp_to_minimize))
            return amp_to_minimize
        return objective_fn

    def _minimize(self, element, objective_fn, init_guesses):
        start_time = time.perf_counter()

        # perform minimization and give results, time it, plot final sweep
        # call scipy optimize minimize fn with nelder-mead method
        result = minimize(objective_fn, init_guesses, method='Nelder-Mead',
                          options={'xatol': XATOL, 'fatol': FATOL,
                                   'maxiter': MAXITER, 'disp': True,
                                   'return_all': True})
        if result.success:
            results = result.x
            # apply the offsets
            min_amp = objective_fn(results)
        else:
            results = init_guesses
            # apply init guesses as offsets
            min_amp = objective_fn(results)
            print('Applied initial guesses as offsets, amp: {:.5}'
                  .format(min_amp))

        # show time elapsed
        elapsed_time = time.perf_counter() - start_time
        print('Minimization took {:.5}s'.format(elapsed_time))

        # show a coarse sweep after tuning
        print('After tuning {} LO leakage...'.format(element.name))
        self._show_coarse_sweep(element)

        return results

    def _show_sweep(self, **parameters):
        start_time = time.perf_counter()

        freqs, amps = self.sa.sweep(**parameters)
        plt.plot(freqs, amps)
        plt.show()

        elapsed_time = time.perf_counter() - start_time
        print('Sweep took {:.5}s'.format(elapsed_time))

    def _show_coarse_sweep(self, element: QuantumElement):
        self._show_sweep(center = element.lo_freq,
                        span = abs(element.int_freq * COARSE_SWEEP_SPAN_SCALAR),
                        rbw = COARSE_SWEEP_RBW)

    def _show_fine_sweep(self, center):
        self._show_sweep(center = center,
                        span = center * FINE_SWEEP_SPAN_SCALAR,
                        rbw = FINE_SWEEP_RBW)

    def _create_yaml_map(self):
        return {
            'name': self.name
        }

    @property
    def parameters(self):
        return 'WORK IN PROGRESS'

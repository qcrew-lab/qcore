"""
Pulse lib. Classes - Pulse, Waveform.
Utils - gauss, other funcs for generating arbitrary waveforms.
Globals (dicts defining instances of pulse and waveform)
these globals will be used by elements to define their operations, and then the
qm config builder will build config based on the elements' defined operations.
the user can add more pulses to this library and add them to the elements as
well.
"""
import numpy as np

from utils.yamlizer import Yamlable

# --------------------- Waveform generator functions ---------------------------
# constant value function
def constant_fn(amp):
    return amp

# gaussian function
def gauss_fn(max_amp: float, sigma: float, multiple_of_sigma: int):
    length = int(multiple_of_sigma*sigma)
    mu = int(np.floor(length / 2))
    t = np.linspace(0, length - 1, length)
    gaussian = max_amp * np.exp(-((t - mu) ** 2) / (2 * sigma ** 2))
    return [float(x) for x in gaussian]

func_map = {
    'constant_fn': constant_fn,
    'gauss_fn': gauss_fn,
    constant_fn: 'constant_fn',
    gauss_fn: 'gauss_fn'
}

# --------------------------- Waveform classes ---------------------------------
# TODO validate waveform params (max, min amp etc) against QM accepted range
class Waveform(Yamlable):
    """
    Encapsulates a waveform.
    Accepts a func that basically tells it how to generate the waveform
    sample/samples. Func is a lambda.
    """
    def __init__(self, func=None, func_name: str=None, func_params: dict=None):
        # TODO better error handling
        if func and func_params is None:
            print('YOU MUST PROVIDE EITHER A FUNCTION OR THE NAME OF A VALID' +
                  'FUNCTION TO INITIALIZE A WAVEFORM')
            return
        elif func is None:
            # TODO handle key error
            self.func = func_map[func_name]
        else:
            self.func = func

        self._func_params = func_params

    def _create_yaml_map(self):
        yaml_map = {
            'func': func_map[self.func],
            'func_params': self.func_params
        }
        return yaml_map

    @property # func params getter
    def func_params(self):
        return self._func_params

    @func_params.setter
    def func_params(self, new_func_params: dict):
        self._func_params = new_func_params

class ConstantWaveform(Waveform):
    """
    The func is defined. For constant waveforms, the func will return a
    constant value no matter what args are supplied in get_samples.

    """
    def __init__(self, func_params=None):
        super().__init__(func=constant_fn, func_params=func_params)

DEFAULT_MAX_ALLOWED_ERROR = 1e-3 # set by QM
DEFAULT_SAMPLING_RATE = 1 # in gigasamples per second, set by QM
class ArbitraryWaveform(Waveform):
    """
    The func is arbitrary and passed in with the init method.
    Extra params - sampling rate and max error allowed (acc to QM)
    For arbitrary waveforms, the func will return the values corresponding to
    the args given.
    """
    def __init__(self, func, func_params=None,
                 max_allowed_error=None, sampling_rate=None):
        # default set by QM is 1e-3 for max_error_allowed
        # and 1 gigasamples per second for sampling rate
        self.max_allowed_error = (DEFAULT_MAX_ALLOWED_ERROR
                                  if max_allowed_error is None
                                  else max_allowed_error)
        self.sampling_rate = (DEFAULT_SAMPLING_RATE if sampling_rate is None
                              else sampling_rate)
        super().__init__(func=func, func_params=func_params)

# ------------------------ Archetypical waveforms ------------------------------
ZERO_WF = ConstantWaveform(func_params={'amp': 0.0})
DEFAULT_CONSTANT_WF = ConstantWaveform(func_params={'amp': 0.25})
DEFAULT_GAUSS_WF = ArbitraryWaveform(func=gauss_fn,
                                      func_params={'max_amp': 0.25,
                                                   'sigma': 1000,
                                                   'multiple_of_sigma': 4})

# ----------------------------- Pulse classes ----------------------------------
# all pulses are control pulses, some are also measurement pulses.
class Pulse(Yamlable):
    """
    Encapsulates a pulse.
    Assume MIX INPUTS!!!
    """
    def __init__(self, name: str, length: int, waveforms: dict):
        self.name = name
        # TODO validate against QM type rules for pulse lengths
        self.length = length
        self.waveforms = waveforms

    def _create_yaml_map(self):
        yaml_map = {
            'name': self.name,
            'length': self.length,
            'waveforms': self.waveforms
        }
        return yaml_map

class MeasurementPulse(Pulse):
    """
    Encapsulates a measurement pulse.
    Has a getter method for integration weights, weights are calculated acc to
    the pulse length.
    """
    @property # integration weights getter
    def integration_weights(self):
        # TODO remove hard-coded global 4, and ones and zeros in sine/cosine
        num_clock_cycles = int(self.length / 4)
        integration_weights = {
            'iw1': {
                'cosine': np.ones(num_clock_cycles),
                'sine': np.zeros(num_clock_cycles)
                },
            'iw2': {
                'cosine': np.zeros(num_clock_cycles),
                'sine': np.ones(num_clock_cycles)
                }
            }
        return integration_weights

# ------------------------- Archetypical pulses --------------------------------
# provide three default pulses - CW, readout, Gaussian
DEFAULT_PULSE_LENGTH = 1000 # can be changed later by Quantum Element objects
DEFAULT_CW_PULSE = Pulse(name='CW_pulse', length=DEFAULT_PULSE_LENGTH,
                 waveforms={'I': DEFAULT_CONSTANT_WF, 'Q': ZERO_WF})
DEFAULT_READOUT_PULSE = MeasurementPulse(name='readout_pulse',
                                 length=DEFAULT_PULSE_LENGTH,
                                 waveforms={'I': DEFAULT_CONSTANT_WF,
                                            'Q': ZERO_WF})
DEFAULT_GAUSSIAN_PULSE = Pulse(name='gaussian_pulse',
                               length=DEFAULT_PULSE_LENGTH,
                               waveforms={'I': DEFAULT_GAUSS_WF, 'Q': ZERO_WF})

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
    """
    Constant valued fn. TODO write proper docu.
    """
    return amp

# gaussian function
def gauss_fn(max_amp: float, sigma: float, multiple_of_sigma: int):
    """
    Gaussian fn. TODO write proper docu.
    """
    length = int(multiple_of_sigma*sigma)
    mu = int(np.floor(length / 2))
    t = np.linspace(0, length - 1, length)
    gaussian = max_amp * np.exp(-((t - mu) ** 2) / (2 * sigma ** 2))
    return [float(x) for x in gaussian]

# map of strings to functions
# even though functions can be passed into methods in Python, it might be more
# convenient to work with function name strings
func_map = {
    'constant_fn': constant_fn,
    'gauss_fn': gauss_fn,
}

# --------------------------- Waveform classes ---------------------------------
# pylint: disable=abstract-method
# TODO validate waveform params (max, min amp etc) against QM accepted range
class Waveform(Yamlable):
    """
    Encapsulates a waveform.
    Accepts a func that basically tells it how to generate the waveform
    sample/samples. Func is a lambda.
    """
    def __init__(self, name: str, func: str, func_params: dict):
        # TODO better error handling
        self.func_name = func
        try:
            self.func = func_map[func]
        except KeyError:
            print('func_name does not correspond to a func defined in pulselib')

        self.func_params = func_params

        super().__init__(name=name)

    def get_samples(self):
        return self.func(**self.func_params)

class ConstantWaveform(Waveform):
    """
    The func is defined. For constant waveforms, the func will return a
    constant value no matter what args are supplied in get_samples.

    """
    def __init__(self, name: str, amp: float):
        self.amp = amp
        super().__init__(name=name, func='constant_fn',
                         func_params={'amp': amp})

    def _create_yaml_map(self):
        yaml_map = {
            'amp': self.amp
        }
        return yaml_map

class ArbitraryWaveform(Waveform):
    """
    Supplied with a string that corresponds to a valid fn name in the pulselib,
    and **kwargs which are all arguments that the function will accept.

    In the future, we will add support for user to change max_allowed_error and
    sampling_rate, for now these will be default values set by QM.
    """
    def __init__(self, name: str, func: str, **parameters):
        self.parameters = parameters
        super().__init__(name=name, func=func, func_params=parameters)

    def _create_yaml_map(self):
        yaml_map = dict()
        yaml_map['name'] = self.name
        yaml_map['func'] = self.func_name
        yaml_map.update(self.parameters)
        return yaml_map

# ------------------------ Archetypical waveforms ------------------------------
ZERO_WF = ConstantWaveform(name='zero_wf', amp=0.0)
DEFAULT_CONSTANT_WF = ConstantWaveform(name='constant_wf', amp=0.25)
DEFAULT_GAUSS_WF = ArbitraryWaveform(name='gauss_wf', func='gauss_fn',
                                     max_amp=0.25, sigma=1000,
                                     multiple_of_sigma=4)

# ----------------------------- Pulse classes ----------------------------------
# all pulses are control pulses, some are also measurement pulses.
class Pulse(Yamlable):
    """
    Encapsulates a pulse.
    Assume MIX INPUTS!!!
    """
    def __init__(self, name: str, length: int, waveforms: dict):
        # TODO validate against QM type rules for pulse lengths
        self.length = length
        self.waveforms = waveforms
        super().__init__(name=name)

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
        """
        Default integration weights for a measurement pulse.
        """
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
                },
            'optw1': {
                'cosine': np.ones(num_clock_cycles),
                'sine': np.zeros(num_clock_cycles)
                },
            'optw2': {
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

"""
A utility for building a QM config file (which is a highly nested Python dict)
from the attributes of Quantum Element objects. We use the QM config schema
(available at https://qm-docs.s3.amazonaws.com/v0.8/config/index.html) to first
create a schema dict from whose structure the config file for the given
elements is built step by step.

This module is designed for convenience, and is not meant to be a comprehensive
utility for building a config file for all possible use cases. But it can be
extended easily to cover more cases. Global defaults, wherever used, are
explicitly declared before defining public methods.

Dc offsets are set to 0.0 and and mixer correction matrix is set to identity by
default. These values are instead to be changed during mixer tuning via the QM
API.

Here's where this module is not comprehensive:
1. No support for building digital_outputs in controllers config
2. No support for building digitalInputs, singleInputCollection,
outputPulseParameters, hold_offset, measurement_qe, frequency in elements
config.
3. 
"""
from copy import deepcopy
from pathlib import Path
import yaml

from instruments import QuantumElement
from utils.pulselib import (Pulse, MeasurementPulse, Waveform,
                            ConstantWaveform, ArbitraryWaveform)

# --------------------------------- Globals ------------------------------------
CONTROLLER = 'con1'
MAX_ANALOG_OUTPUTS = 10
MAX_ANALOG_INPUTS = 2
DEFAULT_DC_OFFSET_DICT = {'offset': 0.0}
DEFAULT_MIXER_CORRECTION = (1.0, 0.0, 0.0, 1.0)
DEFAULT_TIME_OF_FLIGHT = 180
DEFAULT_SMEARING = 0
MIXER_PREFIX = 'mixer_' # mixer naming convention is MIXER_PREFIX + element.name
NUM_MIXERS_PER_ELEMENT = 1
DEFAULT_DIGITAL_MARKER = 'ON'
DEFAULT_DIGITAL_ON_SAMPLES = [(1, 0)] # must be list of tuples
DEFAULT_SAMPLING_RATE = 1 # for arbitrary waveforms, in gigacycles per second
DEFAULT_MAX_ALLOWED_ERROR = 1e3 # for auto-compression of arbitrary waveforms

# ------------------------------- Base config ----------------------------------
# base config must be in the same directory as this module
CONFIG_SCHEMA_FILENAME = 'qm_config_schema.yaml'
CONFIG_SCHEMA_PATH = Path(__file__).resolve().parent / CONFIG_SCHEMA_FILENAME
with open(CONFIG_SCHEMA_PATH, 'r') as base_config_file:
    QM_CONFIG_SCHEMA = yaml.safe_load(base_config_file)

# ------------------------------ Public method ---------------------------------
def build_qm_config(elements: set[QuantumElement]) -> dict:
    """
    Builds qm config from a base config file. The qm config to be built is
    passed on to helper methods, which build it step by step. This works
    because dicts are mutable and passed by reference in Python.
    """
    qm_config = dict() # the config to be built
    qm_config['version'] = QM_CONFIG_SCHEMA['version'] # is currently 1
    _build_elements_config(elements, qm_config)
    _build_controllers_config(elements, qm_config)    
    _build_mixers_config(elements, qm_config)
    _build_pulses_and_waveforms_config(elements, qm_config)
    _build_digital_waveforms_config(qm_config)
    return qm_config

# ------------------------- Private helper methods -----------------------------
def _build_elements_config(elements: set, qm_config: dict):
    elements_config = dict()
    for element in elements:
        element_schema = deepcopy(QM_CONFIG_SCHEMA['elements']['element_name'])
        _build_element_config(element, element_schema)
        elements_config[element.name] = element_schema
    qm_config['elements'] = elements_config

def _build_element_config(element: QuantumElement, element_schema: dict):
    _build_element_ports_config(element, element_schema)
    _build_element_freq_config(element, element_schema)
    _build_element_ops_config(element, element_schema)

    if hasattr(element, 'time_of_flight') or hasattr(element, 'smearing'):
        _build_readout_element_config(element, element_schema)

def _build_element_ports_config(element: QuantumElement, element_schema: dict):
    # TODO make this error handling more robust
    if not hasattr(element, 'ports'):
        raise RuntimeError('No ports defined for element ' + element.name)

    if 'in' in element.ports: # single input
        element_schema['singleInput']['port'] = (CONTROLLER,
                                                 element.ports['in'])
    elif 'I' in element.ports and 'Q' in element.ports: # mixed inputs
        element_schema['mixInputs']['I'] = (CONTROLLER, element.ports['I'])
        element_schema['mixInputs']['Q'] = (CONTROLLER, element.ports['Q'])

    # output port, if available
    if 'out' in element.ports:
        element_schema['outputs']['out1'] = (CONTROLLER, element.ports['out'])

def _build_element_freq_config(element: QuantumElement, element_schema: dict):
    # TODO error handling if element does not have lo_freq, int_freq attributes
    # TODO decide if 'frequency' in elements config is to be updated with omega
    element_schema['mixInputs']['lo_frequency'] = element.lo_freq
    element_schema['intermediate_frequency'] = element.int_freq

def _build_element_ops_config(element: QuantumElement, element_schema: dict):
    # TODO make this error handling more robust
    if not hasattr(element, 'operations'):
        raise RuntimeError('No operations defined for element ' + element.name)

    for op_name, pulse in element.operations.items():
        element_schema['operations'][op_name] = pulse.name

def _build_readout_element_config(element: QuantumElement,
                                  element_schema: dict):
    tof = (element.time_of_flight if element.time_of_flight is not None
           else DEFAULT_TIME_OF_FLIGHT)
    element_schema['time_of_flight'] = tof

    smearing = (element.smearing if element.smearing is not None
                else DEFAULT_SMEARING)
    element_schema['smearing'] = smearing

def _build_controllers_config(elements: set, qm_config: dict):
    controller_schema = deepcopy(QM_CONFIG_SCHEMA['controllers'])
    for element in elements:
        for port_name, port_num in element.ports.items():
            if port_name == 'out': # build analog inputs config
                ai_config = controller_schema[CONTROLLER]['analog_inputs']
                ai_config[port_num] = DEFAULT_DC_OFFSET_DICT
            else: # build analog outputs config
                ao_config = controller_schema[CONTROLLER]['analog_outputs']
                ao_config[port_num] = DEFAULT_DC_OFFSET_DICT
    qm_config['controllers'] = controller_schema

def _build_mixers_config(elements: set, qm_config: dict):
    # also updates mixer name in elements config
    mixers_config = dict()
    for element in elements:
        # build mixer config only if mixed inputs found
        if 'I' in element.ports and 'Q' in element.ports:
            mixer_schema = deepcopy(QM_CONFIG_SCHEMA['mixers']['mixer_name'])
            mixer_name = MIXER_PREFIX + element.name
            # update mixer_name in elements' mixed inputs config
            mix_inputs_config = qm_config['elements'][element.name]['mixInputs']
            mix_inputs_config['mixer'] = mixer_name
            _build_mixer_config(element, mixer_schema)
            mixers_config[mixer_name] = mixer_schema
    qm_config['mixers'] = mixers_config

def _build_mixer_config(element: QuantumElement, mixer_schema: dict):
    for i in range(NUM_MIXERS_PER_ELEMENT):
        mixer_schema[i]['intermediate_frequency'] = element.int_freq
        mixer_schema[i]['lo_frequency'] = element.lo_freq 
        mixer_schema[i]['correction'] = DEFAULT_MIXER_CORRECTION

def _build_pulses_and_waveforms_config(elements: set, qm_config: dict):
    pulses_config = dict()
    waveforms_config = dict()
    for element in elements:
        for pulse in element.operations.values():
            if pulse.name not in pulses_config: # only add unique pulses
                pulse_schema = deepcopy(QM_CONFIG_SCHEMA['pulses']
                                        ['pulse_name'])
                _build_pulse_config(pulse, pulse_schema, qm_config)
                pulses_config[pulse.name] = pulse_schema
                for waveform in pulse.waveforms.values():
                    if waveform.name not in waveforms_config:
                        _build_waveform_config(waveform, waveforms_config)
    qm_config['pulses'] = pulses_config
    qm_config['waveforms'] = waveforms_config

def _build_pulse_config(pulse: Pulse, pulse_schema: dict, qm_config: dict):
    if not hasattr(pulse, 'waveforms'):
        raise RuntimeError('No waveforms defined for pulse ' + pulse.name)

    _build_pulse_waveform_config(pulse, pulse_schema)
    pulse_schema['length'] = pulse.length

    if isinstance(pulse, MeasurementPulse):
        pulse_schema['operation'] = 'measurement'
        _build_meas_pulse_config(pulse, pulse_schema, qm_config)
    else:
        pulse_schema['operation'] = 'control'
        del pulse_schema['digital_marker'], pulse_schema['integration_weights']

def _build_pulse_waveform_config(pulse: Pulse, pulse_schema: dict):
    if 'single' in pulse.waveforms: # single input
        pulse_schema['waveforms']['single'] = pulse.waveforms['single'].name
        del pulse_schema['waveforms']['I'], pulse_schema['waveforms']['Q']
    elif 'I' in pulse.waveforms and 'Q' in pulse.waveforms: # mixed inputs
        pulse_schema['waveforms']['I'] = pulse.waveforms['I'].name
        pulse_schema['waveforms']['Q'] = pulse.waveforms['Q'].name
        del pulse_schema['waveforms']['single']

def _build_meas_pulse_config(pulse: Pulse, pulse_schema: dict, qm_config: dict):
    pulse_schema['digital_marker'] = DEFAULT_DIGITAL_MARKER
    iw_names = pulse.integration_weights.keys()
    pulse_schema['integration_weights'] = dict.fromkeys(iw_names, iw_names)
    _build_integration_weights_config(pulse, qm_config)

def _build_integration_weights_config(pulse: MeasurementPulse, qm_config: dict):
    qm_config['integration_weights'] = pulse.integration_weights

def _build_waveform_config(waveform: Waveform, waveforms_config: dict):
    if isinstance(waveform, ConstantWaveform):
        const_wf_schema = deepcopy(QM_CONFIG_SCHEMA['waveforms']['constant_wf'])
        const_wf_schema['type'] = 'constant'
        const_wf_schema['sample'] = waveform.get_samples()
        waveforms_config[waveform.name] = const_wf_schema
    elif isinstance(waveform, ArbitraryWaveform):
        arb_wf_schema = deepcopy(QM_CONFIG_SCHEMA['waveforms']['arbitrary_wf'])
        arb_wf_schema['type'] = 'arbitrary'
        arb_wf_schema['max_allowed_error'] = DEFAULT_MAX_ALLOWED_ERROR
        arb_wf_schema['sampling_rate'] = DEFAULT_SAMPLING_RATE
        arb_wf_schema['samples'] = waveform.get_samples()
        waveforms_config[waveform.name] = arb_wf_schema

def _build_digital_waveforms_config(qm_config: dict):
    # for now, assume only one default digital waveform 'ON'
    # this method can be extended if we require multiple digital waveforms
    # simply make the element remember its digital waveforms
    digital_waveforms_config = dict()
    digital_waveform_schema = (QM_CONFIG_SCHEMA['digital_waveforms']
                                ['digital_wf_name'].copy())
    digital_waveform_schema['samples'] = DEFAULT_DIGITAL_ON_SAMPLES
    digital_waveforms_config[DEFAULT_DIGITAL_MARKER] = digital_waveform_schema
    qm_config['digital_waveforms'] = digital_waveforms_config

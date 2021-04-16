"""
A utility class that builds a QM config (which is a highly nested Python dict)
from the attributes of Quantum Element objects and a pulse lib.

Sets default values to critical config parameters that are not explicitly
specified by the Elements and the pulse lib.

Assume all elements have mixed inputs. Assume all elements are associated with
only 1 mixer.
"""
from copy import deepcopy
from pathlib import Path
import yaml

# QM config schema is at https://qm-docs.s3.amazonaws.com/v0.8/config/index.html

# defaults
CONTROLLER = 'con1'
MAX_ANALOG_OUTPUTS = 10
MAX_ANALOG_INPUTS = 2
DEFAULT_OFFSET = 0.0
DEFAULT_MIXER_CORRECTION = (1.0, 0.0, 0.0, 1.0)
DEFAULT_TIME_OF_FLIGHT = 180
DEFAULT_SMEARING = 0
MIXER_PREFIX = 'mixer_' # mixer naming convention is MIXER_PREFIX + element.name
NUM_MIXERS_PER_ELEMENT = 1
DEFAULT_DIGITAL_ON_SAMPLES = [(1, 0)] # must be list of tuples
DEFAULT_SAMPLING_RATE = 1 # for arbitrary waveforms, in gigacycles per second.

# base config must be in the same directory as this module
BASE_CONFIG_FILENAME = 'base_config.yaml'
BASE_CONFIG_FILEPATH = Path(__file__).resolve().parent / BASE_CONFIG_FILENAME

class QmConfigBuilder():
    """
    Builds qm config.
    """
    def __init__(self):
        self._base_config = self._create_base_config() # schema
        self._config = dict() # the config to be built

    def _create_base_config(self):
        with open(BASE_CONFIG_FILEPATH, 'r') as base_config_file:
            return yaml.safe_load(base_config_file)

    def build_config(self, elements):
        self._config['version'] = self._base_config['version']
        self._config['elements'] = self._build_elements_config(elements)
        self._config['controllers'] = self._build_controllers_config(elements)
        self._config['mixers'] = self._build_mixers_config(elements)
        self._config['pulses'] = self._build_pulses_config(elements)
        self._config['integration_weights'] = self._build_iw_config(elements)
        self._config['waveforms'] = self._build_waveforms_config(elements)
        self._config['digital_waveforms'] = self._build_digi_waveforms_config()
        return self._config

    def _build_elements_config(self, elements):
        # TODO add operations!!!
        elements_config = dict()
        for element in elements:
            element_schema = deepcopy(self._base_config['elements']
                                      ['element_name'])
            self._build_element_config(element, element_schema)
            elements_config[element.name] = element_schema
        return elements_config

    def _build_element_config(self, element, element_schema):
        self._build_element_ports_config(element, element_schema)
        self._build_element_frequencies_config(element, element_schema)

        if hasattr(element, 'time_of_flight') or hasattr(element, 'smearing'):
            self._build_measurable_element_config(element, element_schema)
        else:
            del (element_schema['outputs'], element_schema['smearing'],
                 element_schema['time_of_flight'])

    def _build_element_ports_config(self, element, element_schema):
        # input ports
        # TODO relax assumption of mixInputs
        element_schema['mixInputs']['I'] = (CONTROLLER, element.ports['I'])
        element_schema['mixInputs']['Q'] = (CONTROLLER, element.ports['Q'])

        # output port, if available
        if 'out' in element.ports:
            element_schema['outputs']['out1'] = (CONTROLLER,
                                                 element.ports['out'])

    def _build_element_frequencies_config(self, element, element_schema):
        element_schema['mixInputs']['lo_frequency'] = element.lo_freq
        element_schema['intermediate_frequency'] = element.int_freq

    def _build_measurable_element_config(self, element, element_schema):
        tof = (element.time_of_flight if element.time_of_flight is not None
               else DEFAULT_TIME_OF_FLIGHT)
        element_schema['time_of_flight'] = tof

        smearing = (element.smearing if element.smearing is not None
                    else DEFAULT_SMEARING)
        element_schema['smearing'] = smearing

    def _build_controllers_config(self, elements):
        controller_schema = deepcopy(self._base_config['controllers'])
        for element in elements:
            self._build_analog_outputs_config(element, controller_schema)
            if 'out' in element.ports:
                self._build_analog_inputs_config(element, controller_schema)
        return controller_schema

    def _build_analog_outputs_config(self, element, controller_schema):
        ao_config = controller_schema[CONTROLLER]['analog_outputs']

        i_offset = (DEFAULT_OFFSET if element.offsets['I'] is None
                    else element.offsets['I'])
        q_offset = (DEFAULT_OFFSET if element.offsets['Q'] is None
                    else element.offsets['Q'])

        ao_config[element.ports['I']] = {'offset': i_offset}
        ao_config[element.ports['Q']] = {'offset': q_offset}

    def _build_analog_inputs_config(self, element, controller_schema):
        ai_config = controller_schema[CONTROLLER]['analog_inputs']
        ai_config[element.ports['out']] = {'offset': element.offsets['out']}

    def _build_mixers_config(self, elements):
        # also updates mixer name in elements config
        mixers_config = dict()
        for element in elements:
            mixer_schema = deepcopy(self._base_config['mixers']['mixer_name'])
            mixer_name = MIXER_PREFIX + element.name
            self._update_element_mixer_name(element.name, mixer_name)
            self._build_mixer_config(element, mixer_schema)
            mixers_config[mixer_name] = mixer_schema
        return mixers_config

    def _build_mixer_config(self, element, mixer_schema):
        for i in range(NUM_MIXERS_PER_ELEMENT):
            mixer_schema[i]['intermediate_frequency'] = element.int_freq
            mixer_schema[i]['lo_frequency'] = element.lo_freq
            mixer_correction = (DEFAULT_MIXER_CORRECTION
                                if element.offsets['mixer'] is None
                                else element.offsets['mixer'])
            mixer_schema[i]['correction'] = mixer_correction

    def _update_element_mixer_name(self, elmt_name, mixer_name):
        # elements config has already been built
        # elmt_name refers to element name
        self._config['elements'][elmt_name]['mixInputs']['mixer'] = mixer_name

    def _build_pulses_config(self, elements):
        return {}

    def _build_iw_config(self, elements):
        return {}

    def _build_digi_waveforms_config(self):
        digital_waveforms_config = self._base_config['digital_waveforms']
        digital_waveforms_config['ON']['samples'] = DEFAULT_DIGITAL_ON_SAMPLES
        return digital_waveforms_config

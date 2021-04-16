"""
Quantum element, subclass of MetaInstrument.
By default, assign it pulses from pulse lib (depending on whether it is control
or control/mesaure element)
"""
from instruments import MetaInstrument
from utils.pulselib import (DEFAULT_CW_PULSE, DEFAULT_GAUSSIAN_PULSE,
                            DEFAULT_READOUT_PULSE)

# constructor argument names
NAME = 'name'
PARAMETERS = 'parameters'
OPERATIONS = 'operations'

class QuantumElement(MetaInstrument):
    """
    e.g. qubit, resonator. This class simply provides a generic
    _create_parameters method that allows the user to supply a variable number
    of properties in a dict.

    Intended use case is to load a Quantum Element object from a given yaml
    configuration (which is based on a given yaml schema). This Element will be
    updated during experiments, qm config files will be built based on it, and
    will eventually be saved to disk.
    """
    def __init__(self, name: str, parameters: dict, operations: dict=None):
        self._create_parameters(parameters)
        self._operations = self._add_default_operations()
        if operations is not None:
            self._operations.update(operations)
        super().__init__(name=name, parameters=parameters)

    def _create_parameters(self, parameters):
        if parameters is None:
            print('Element config does not exist, cannot create parameters...')
            return
        else:
            for parameter in parameters:
                setattr(self, parameter, parameters[parameter])

    def _create_yaml_map(self):
        # TODO can we ensure the map adheres to constructor without hard coding?
        yaml_map = {NAME: self._name,
                    PARAMETERS: self._parameters,
                    OPERATIONS: self._operations
                    }
        return yaml_map

    @property # parameters getter
    def parameters(self):
        return self._parameters

    @property # operations getter
    def operations(self):
        return self._operations

    def _add_default_operations(self):
        default_operations = {'CW': DEFAULT_CW_PULSE,
                              'gaussian': DEFAULT_GAUSSIAN_PULSE}
        # include readout pulse only if element has an 'out' port defined
        # TODO relax constraint that ports must be defined (fix AttributeError)
        if 'out' in self.ports:
            default_operations['readout'] = DEFAULT_READOUT_PULSE
        return default_operations

    def set_op_length(self, op_name: str, length: int):
        # TODO validate new_op_length against QM specs
        try:
            self.operations[op_name].length = length
        except KeyError:
            print('No such operation defined for this element')

    # TODO figure out a better way to handle this update
    def set_op_params(self, op_name: str, wf_name: str, params: dict):
        if not isinstance(params, dict):
            print('params must have the form { ''param_name'': param_value }')
            return

        try:
            self.operations[op_name].waveforms[wf_name].func_params = params
        except KeyError:
            # TODO remove this hard coded comparison check
            if wf_name != 'I' or wf_name != 'Q':
                print('wf_name must be either ''I'' or ''Q''')
            else:
                print('No such operation defined for this element')

class QuantumDevice(MetaInstrument):
    """
    Encapsulates a quantum device, which contains multiple quantum elements
    performing specific functions.

    For now, this class has been created simply to ensure we can write the info
    of all elements in a device into a single yaml.
    """
    def __init__(self, name: str, elements: dict):
        self.elements = elements
        # TODO add more parameters to this object
        # currently I'm simply making its elements be its parameters as well
        super().__init__(name=name, parameters=elements)

    @property # parameters getter
    def parameters(self):
        return self._parameters

    def _create_yaml_map(self):
        # TODO can we ensure the map adheres to constructor without hard coding?
        yaml_map = {NAME: self._name,
                    'elements': self.elements,
                    }
        return yaml_map

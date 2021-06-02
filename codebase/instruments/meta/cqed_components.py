"""
This module defines base classes for encapsulating cqed components in qcrew's
lab.
"""
from qcrew.codebase.instruments import MetaInstrument
from qcrew.codebase.utils.pulselib import Pulse

# constructor argument names
NAME = "name"
PARAMETERS = "parameters"
OPERATIONS = "operations"


class QuantumElement(MetaInstrument):
    """
    e.g. qubit, resonator. For now, supports **kwargs where each becomes an
    attribute, and is stored in an internal parameters dict (that can be
    accessed by .parameters property). All such parameters are public for now
    to facilitate easy updating.

    Currently, it is the user's responsibility to supply suitable parameters
    (e.g. frequencies, operations) for configuring QM OPX. The qm config
    builder relies on quantum elements having suitable attributes, if they
    don't, it throws up attribute errors.
    """

    @property  # parameters getter
    def parameters(self):
        # must return up-to-date values of parameters
        for param_name in self._parameters:
            current_param_value = getattr(self, param_name)
            self._parameters[param_name] = current_param_value
        return self._parameters

    def add_parameter(self, name: str, value):
        """Add a parameter to quantum element. Also sets it as attribute.

        Args:
            name (str): param name to be added
            value ([type]): param value to be added
        """
        if name in self._parameters:
            print("param of this name alr exists in element...")
            return

        self._parameters[name] = value
        setattr(self, name, value)

    def add_operation(self, name: str, pulse: Pulse):
        """Add an operation with the given name and Pulse.

        Checks if operation alr exists in this element. If element does not
        have any defined operations, creates an attribute and adds given
        operation.

        Args:
            name (str): name of the operation.
            pulse (Pulse): pulse object for the operation.
        """
        # TODO enforce that operations must be a dict
        if hasattr(self, OPERATIONS):
            if name in getattr(self, OPERATIONS):
                print("Operation with given name alr exists in this element...")
            else:
                getattr(self, OPERATIONS)[name] = pulse
        else:
            setattr(self, OPERATIONS, dict())
            getattr(self, OPERATIONS)[name] = pulse

    def set_op_length(self, op_name: str, length: int):
        """Set operation with given name to given length.

        Args:
            op_name (str): name of operation whose length is to be changed
            length (int): new length of operation
        """
        # TODO validate new_op_length against QM specs
        if not hasattr(self, OPERATIONS):
            print("No operations defined for this element")
            return

        try:
            getattr(self, OPERATIONS)[op_name].length = length
        except KeyError:
            print("No such operation defined for this element")

    # TODO figure out a better way to handle this update
    def set_op_params(self, op_name: str, wf_name: str, params: dict):
        """[summary]

        Args:
            op_name (str): operation whose waveform params are to be updated
            wf_name (str): waveform ('I' or 'Q') whose params are to be updated
            params (dict): new param dict to update waveform with
        """
        if not isinstance(params, dict):
            print("params must have the form { " "param_name" ": param_value }")
            return

        if not hasattr(self, OPERATIONS):
            print("No operations defined for this element")
            return

        try:
            pulse = getattr(self, OPERATIONS)[op_name]
            pulse.waveforms[wf_name].func_params = params
        except KeyError:
            # TODO remove this hard coded comparison check
            if wf_name != "I" or wf_name != "Q":
                print("wf_name must be either " "I" " or " "Q" "")
            else:
                print("No such operation defined for this element")

    def _create_yaml_map(self):
        yaml_map = dict()
        yaml_map["name"] = self._name
        # call parameters getter for latest values
        yaml_map.update(self.parameters)
        return yaml_map


class QuantumDevice(MetaInstrument):
    """
    Encapsulates a quantum device, which contains multiple quantum elements
    performing specific functions.
    """

    def __init__(self, name: str, **elements):
        self._elements = dict()
        # check that kwargs are indeed QuantumElement objects
        for element in elements.values():
            if not isinstance(element, QuantumElement):
                raise ValueError("Value of kwargs must be QuantumElement type")
            self._elements[element.name] = element
        super().__init__(name=name, **elements)

    @property  # parameters getter
    def parameters(self):
        parameters = dict()
        for element in self._elements.values():
            parameters[element.name] = element.parameters
        return parameters

    @property  # elements getter
    def elements(self) -> set:
        """
        Get the dict of elements part of this quantum device.
        """
        return self._elements

    def _create_yaml_map(self):
        yaml_map = dict()
        yaml_map["name"] = self._name
        yaml_map.update(self._elements)
        return yaml_map

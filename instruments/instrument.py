"""
Instrument.
"""
from abc import ABC, abstractmethod

from parameter import Parameter
from utils.yamlizer import Yamlable

class Instrument(ABC, Yamlable):
    """
    Abstract base class for Instrument.

    An Instrument has a name and is a container of Parameters. It has methods to
    add, remove, create a given parameter. Can be loaded from or saved to yaml
    file as it inherits from yamlable.
    """
    def __init__(self, name: str):
        self._name = name

    @abstractmethod
    def _create_parameters(self):
        pass

    def create_parameter(self, name: str, value = None, unit: str = None,
                         maximum = None, minimum = None):
        new_parameter = Parameter(name, value, unit, maximum, minimum)
        self.add_parameter(new_parameter)

    def add_parameter(self, parameter: Parameter):
        # raise error if param alr exists, do error logging instead of print
        if parameter.name in self._parameters:
            raise ValueError("Parameter of this name alr exists in instrument.")
        else:
            self._parameters[parameter.name] = parameter

    def remove_parameter(self, parameter: Parameter):
        # do error logging instead of print statement
        try:
            del self._parameters[parameter.name]
        except KeyError:
            print("Parameter does not exist in the Instrument.")

class PhysicalInstrument(Instrument):
    """
    Abstract class for a physical instrument, one associated with a piece of
    hardware.

    A PhysicalInstrument provides the methods _connect, _initialize, and
    disconnect, which must be implemented by subclasses. First two methods are
    internal, meant to be called within the __init__() method.
    """
    def __init__(self, name: str, identifier):
        self._identifier = identifier
        super().__init__(name=name)

    @abstractmethod
    def _connect(self):
        """
        Establish a connection to the hardware. 
        """
        pass

    @abstractmethod
    def _initialize(self):
        """
        Set the initial configuration of the instrument.
        """
        pass

    @abstractmethod
    def disconnect(self):
        """
        Disconnect the hardware.
        """
        pass

class MetaInstrument(Instrument):
    """
    Abstract class for a meta instrument, one corresponding to a model of a
    physical or simulated system. A meta instrument may be controlled by many
    physical instruments. A meta instrument may have its own internal state
    and generate results much like a physical instrument.
    """
    # find a way to make this class less useless

"""
Instrument.
"""
from abc import abstractmethod

from utils.yamlizer import Yamlable

class Instrument(Yamlable):
    """
    Base class for Instrument.

    An Instrument has a name and is a container of parameters. It has methods to
    add, remove, create a given parameter. Can be loaded from or saved to yaml
    file as it inherits from yamlable.
    """
    def __init__(self, name: str):
        self._name = name

    @abstractmethod
    def _create_parameters(self):
        pass

    @property # parameters info getter
    def parameters(self):
        pass

    @property # name getter
    def name(self):
        return self._name

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

    Initialised with a config dict that specifies its parameters and initial
    values.
    """
    def __init__(self, name: str, parameters: dict):
        self._parameters = parameters
        super().__init__(name=name)

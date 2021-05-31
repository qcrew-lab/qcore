"""
This module defines base classes for encapsulating instruments in qcrew's lab.
"""
from abc import abstractmethod

from qcrew.codebase.utils.yamlizer import Yamlable


class Instrument(Yamlable):
    """
    Abstract class that encapsulates an instrument.

    An instrument has a `name` and is a container of parameters. All parameters
    are gettable, some are settable. Subclasses decide which parameters to
    create as their attributes, and whether to make them internal or part of
    their API. Name is set once and only gettable thereafter.

    Instrument inherits from Yamlable, and can thus be saved into and loaded
    from yaml files.

    Instrument specifies one abstract property `parameters()` which is part of
    its API. It is meant to inform the user about the parameters of this
    instrument, and provide a current snapshot of the instrument. Subclasses
    decide which information to provide and how to populate its parameters dict.
    """

    def __init__(self, name: str):
        """
        Args:
            name (str): name of this instrument.
        """
        super().__init__(name=name)

    @property  # parameters info getter
    @abstractmethod
    def parameters(self):
        """
        Get the parameter dict of this instrument.
        """


class PhysicalInstrument(Instrument):
    """
    Abstract class that encapsulates a physical instrument. A physical
    instrument is one associated with a piece of controllable hardware.

    Provides three methods for subclasses to implement - `_connect()`,
    `_initialize()`, and `disconnect()`. In other words, subclasses decide how
    to connect, initialize, and disconnect themselves. The first two methods
    are meant to be internal and called within the __init__() method, that is,
    at the moment of initialization of an instance.

    This class requires subclasses to have an additional property - a `uid`
    which is a unique identifier required to connect to that instrument. This
    may be a serial number, or a machine id, or any other unique id specified
    by the instrument vendor.
    """

    def __init__(self, name: str, uid):
        """
        Args:
            name (str): name of this physical instrument.
            uid ([type]): unique identifier of this instrument. can be any type
            (depends on the specifications of instrument vendor).
        """
        self._uid = uid
        super().__init__(name=name)

    @abstractmethod
    def _connect(self, uid):
        """
        Establish a connection to the controllable hardware of this instrument.
        Typically requires the uid... but not always...
        """

    @abstractmethod
    def _initialize(self):
        """
        Set the initial configuration of this instrument.
        """

    @abstractmethod
    def disconnect(self):
        """
        Disconnect this instrument.
        """


# pylint: disable=abstract-method
# although MetaInstrument implements _create_yaml_map(), each subclass still
# has to decide how to implement its parameters() property.
class MetaInstrument(Instrument):
    """
    Abstract class that encapsulates a meta instrument. A meta instrument can
    take many forms. It may be composed of many physical instruments. It may be
    an element of an experiment that is controlled by multiple physical
    instruments. It might even correspond to a model of a physical or simulated
    system. Typically, all meta instruments have an internal state that can be
    parametrized.

    Examples of meta instruments include - quantum element (qubit, resonator),
    mixer tuner, and experimental stage.

    Meta instrument class packages all keyword arguments to __init__() in a
    parameters dict. Additionally, all parameters are also made into attributes
    of the instrument that can be accessed by `meta_instrument_name.
    parameter_name`

    Subclasses just pass all their parameters as keyword arguments to this
    class in their __init__() method. They still have the responsibility of
    creating attributes for any new parameter added.
    """

    def __init__(self, name: str, **parameters):
        """
        Args:
            name (str): the name of this meta instrument.
        """
        # TODO proper handling. 'name' is a reserved key for instrument name
        super().__init__(name=name)
        if "name" in parameters:
            raise ValueError("Cannot have parameter named str(name)")
        self._parameters = dict()
        if parameters:
            self._create_attributes(parameters)

    def _create_attributes(self, parameters: dict):
        """
        Set every parameter as an attribute. Meant to be called once within the
        __init__() method. Very useful when initialising objects from yaml
        files.
        """
        for param_name in parameters:
            param_value = parameters[param_name]
            setattr(self, param_name, param_value)
            self._parameters[param_name] = param_value

"""
Base class for a parameter.

A parameter can have a single value or multiple values.
"""
from utils.yamlizer import Yamlable

class Parameter(Yamlable):
    """
    Base class for Parameter.

    TODO what about discrete value parameters? add validators
    """
    def __init__(self, name: str = None, value = None, unit: str = None,
                 maximum = None, minimum = None):
        self._name = name
        self._value = value
        self._unit = unit
        self._maximum = maximum
        self._minimum = minimum

    def __repr__(self):
        return ('{}{}'.format(self._value, self._unit))

    def _create_yaml_map(self):
        # TODO can we refactor this without hard coding? is that desirable?
        yaml_map = {
            'value': self._value
            }
        return yaml_map

    @property # getter
    def name(self):
        return self._name

    @property # getter
    def value(self):
        return self._value

    @value.setter
    def value(self, new_value):
        self._value = new_value

    @property # getter
    def unit(self):
        return self._unit

    @property # getter
    def maximum(self):
        return self._maximum

    @maximum.setter
    def maximum(self, new_maximum):
        self._maximum = new_maximum

    @property # getter
    def minimum(self):
        return self._minimum

    @minimum.setter
    def minimum(self, new_minimum):
        self._minimum = new_minimum

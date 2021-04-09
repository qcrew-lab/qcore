"""
TODO write better docu
Yamlable inherits YAMLOBject and defines methods to save and load subclasses
from yaml files. Subclasses can define a dictionary of parameters that gets
written to and read from yaml file.
"""
from abc import ABCMeta, abstractmethod
import yaml

YAML_TAG_PREFIX = u'!'

THRESHOLD = 1e3 # use scientific notation if abs(value) >= threshold
def sci_not_representer(dumper, value):
    yaml_float_tag = u'tag:yaml.org,2002:float'
    value_in_sci_not = ('{:.2e}'.format(value) if abs(value) >= THRESHOLD
                        else str(value))
    return dumper.represent_scalar(yaml_float_tag, value_in_sci_not)

class AbstractYamlable(ABCMeta):
    """
    Defines yaml tag, loader, dumper for all inheriting classes. Registration
    of class to yaml is done by inheriting from this metaclass.
    """
    def __init__(cls, name, bases, kwds):
        super(AbstractYamlable, cls).__init__(name, bases, kwds)
        # set a consistent format for subclass yaml tags
        cls.yaml_tag = YAML_TAG_PREFIX + name
        # register loader
        yaml.SafeLoader.add_constructor(cls.yaml_tag, cls.from_yaml)
        # register dumper
        yaml.SafeDumper.add_representer(cls, cls.to_yaml)
        # custom dumper for representing float in scientific notation
        yaml.SafeDumper.add_representer(float, sci_not_representer)

class Yamlable(metaclass = AbstractYamlable):
    """
    All Yamlables are abstract, need to define create yaml map method.
    """
    @abstractmethod
    def _create_yaml_map(self):
        """
        Create a yaml map that defines how the instance will be stored and
        retrieved from a yaml file.
        """
        pass

    @classmethod
    def load(cls, path):
        """
        Return instance of cls from given path to yaml file.
        """
        with path.open(mode='r') as file:
            return yaml.safe_load(file)

    @classmethod
    def from_yaml(cls, loader, node):
        """
        Constructor
        """
        # TODO error handling if unable to create instance from saved map
        yaml_map = loader.construct_mapping(node)
        return cls(**yaml_map)

    def save(self, path):
        """
        Save instance to given yaml file Path. Do not sort keys.
        """
        with path.open(mode='w') as file:
            yaml.safe_dump(self, file, sort_keys=False)

    @classmethod
    def to_yaml(cls, dumper, data):
        """
        Representer
        """
        return dumper.represent_mapping(data.yaml_tag, data.yaml_map)

    @property # yaml_map getter
    def yaml_map(self):
        return self._create_yaml_map()

"""
Driver for QM Operator-X.

A first attempt to decouple the Opx from qm's concept of a 'Quantum Machine.'
A 'hot-fix' that bypasses the need to manually update parameters in qm config.
"""
# --------------------------------- Imports ------------------------------------
from qm.QuantumMachinesManager import QuantumMachinesManager
from qm.QuantumMachine import QuantumMachine

from instruments.instrument import MetaInstrument, PhysicalInstrument
from parameter import Parameter

# --------------------------------- Globals ------------------------------------

# -------------------------------- Parameters ----------------------------------
# constructor argument names
NAME = 'name'
ELEMENTS = 'elements'
CONFIG = 'config'

# parameter names
READOUT_PULSE_LEN = 'readout_pulse_len'

# ---------------------------------- Class -------------------------------------
class Opx(PhysicalInstrument):
    """
    Is part of a Quantum Machine, has access to qm object. Has access to its
    Quantum Machine Manager. The qmm is used to establish connection to the qm
    server PC. The qmm is only created once per instance.

    Initialised from yaml file if given, else from a default config dict.

    Instead of qm.execute(), we will add job to queue. This allows us to do lazy
    retrieval of qm jobs. And bypass the side effects of qm.execute().

    Has parameters that are a subset of the config parameters that are exposed
    to user to update. On an update, the instance's qmm will open a new qm
    with the updated config and replace the reference to the current qm.

    Also has set of elements, and updates and/or uses their properties.
    """
    def __init__(self, name: str, config: dict=None,
                 elements: dict[str, MetaInstrument]=None,):
        self._qmm = self._connect()
        self._config = DEFAULT_CONFIG if config is None else config
        self._create_parameters() # TODO decide if this class needs this method?
        # the qm and its id will be renewed each time the config is updated
        self._qm = self._initialize()
        super().__init__(name=name, identifier=self._qm.id)
        self._elements = elements

    def _create_yaml_map(self):
        # must correspond with constructor arguments
        yaml_map = {NAME: self._name,
                    CONFIG: self._config,
                    ELEMENTS: self._elements
                    }
        return yaml_map

    def _create_parameters(self):
        """
        Create parameters. 
        """
        # TODO is this method useful for the opx??
        # esp if the config file is there alr ???
        self._parameters = dict() # for now, let's return an empty dictionary
        return self._parameters

    def _connect(self) -> QuantumMachinesManager:
        return QuantumMachinesManager()

    def _initialize(self):
        return self._qmm.open_qm(self._config)

    def _update_qm(self):
        """
        Update internal qm by opening new one with qmm and remembering id.
        Called everytime internal config is updated.
        """
        self._qm = self._initialize()
        self._identifier = self._qm.id

    def disconnect(self):
        self._qm.close()

    def add_element(self, new_element: MetaInstrument):
        # raise error if element alr exists, do error logging instead of print
        if new_element.name in self._elements:
            raise ValueError('Element of this name alr exists in opx.')
        else:
            self._elements[new_element.name] = new_element

    def remove_element(self, element: MetaInstrument):
        # do error logging instead of print statement
        try:
            del self._elements[element.name]
        except KeyError:
            print('Element does not exist in the opx.')

# -------------------------- Getters and setters -------------------------------
    @property # qm getter
    def qm(self) -> QuantumMachine:
        return self._qm

    @property # qm config getter
    def config(self) -> dict:
        return self._qm.get_config()

    @property # readout pulse length getter
    def readout_pulse_length(self):
        return self._config['pulses']['readout_pulse']['length']

    @readout_pulse_length.setter
    def readout_pulse_length(self, new_length):
        self._config = self.config # get latest config
        self._config['pulses']['readout_pulse']['length'] = new_length
        self._update_qm()

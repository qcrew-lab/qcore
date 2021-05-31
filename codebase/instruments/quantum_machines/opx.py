"""
Driver for QM Operator-X.

A first attempt to decouple the Opx from qm's concept of a 'Quantum Machine.'
A 'hot-fix' that bypasses the need to manually update parameters in qm config.
"""
# --------------------------------- Imports ------------------------------------
from qm.QuantumMachinesManager import QuantumMachinesManager
from qm.QuantumMachine import QuantumMachine

from codebase.instruments import QuantumElement, PhysicalInstrument, qm_config_builder

# ----------------------- Constructor argument names ---------------------------
NAME = "name"
ELEMENTS = "quantum_elements"

# ---------------------------------- Class -------------------------------------
class Opx(PhysicalInstrument):
    """
    This class is a wrapper around the QuantumMachine object. It receives a
    variable number of QuantumElement objects and builds its config using the
    qm_config_builder utility. It then connects to the QM server PC via a
    QuantumMachinesManager and opens a new QuantumMachine with the built
    config.

    This QuantumMachine is available as an attribute (.qm), and must be
    accessed in order to run any code that's part of the QuantumMachine API.

    Currently, the mixer tuning step is not integrated with this driver, so you
    have to run it separately and update the DC offsets and mixer correction
    using the QM API.
    """

    def __init__(self, name: str, **quantum_elements):
        self._quantum_elements = dict()
        # check that kwargs are indeed QuantumElement objects
        for quantum_element in quantum_elements.values():
            if not isinstance(quantum_element, QuantumElement):
                raise ValueError("Value of kwargs must be QuantumElement type")
            self._quantum_elements[quantum_element.name] = quantum_element

        self._qmm = self._connect()

        elements_set = set(self._quantum_elements.values())
        self._config = qm_config_builder.build_qm_config(elements_set)
        print(self._elements_set)
        print(self._config)

        # self._qm = self._initialize()
        super().__init__(name=name, uid=self._qm.id)

    def _create_yaml_map(self):
        yaml_map = dict()
        yaml_map["name"] = self._name
        yaml_map.update(self._quantum_elements)
        return yaml_map

    def _connect(self) -> QuantumMachinesManager:
        return QuantumMachinesManager()

    def _initialize(self):
        return self._qmm.open_qm(self._config)

    def disconnect(self):
        self._qm.close()

    @property  # qm getter
    def qm(self) -> QuantumMachine:
        return self._qm

    @property  # qm config getter
    def config(self) -> dict:
        return self._qm.get_config()

    @property  # parameters getter
    def parameters(self):
        """
        TODO think of a better way to provide a snapshot of the opx
        """
        return {"qm": self._qm}

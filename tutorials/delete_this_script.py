# --------------------------------- Imports ------------------------------------

from pathlib import Path

from instruments import Stage, qm_config_builder
from qm.qua import *
from qm.QuantumMachinesManager import QuantumMachinesManager

# ---------------------------------- Stage -------------------------------------

stage_yaml_file_name = 'example_stage.yaml'
stage_yaml_file_path = Path.cwd() / 'tutorials' / stage_yaml_file_name

stage = Stage.load(stage_yaml_file_path)

# ----------------------------- Instrument init --------------------------------
device = stage.device_A
qubit = stage.device_A.qubit
rr = stage.device_A.rr
lb_qubit = stage.lb_qubit
lb_rr = stage.lb_rr
sa = stage.sa

element_set = {qubit, rr}
qm_config = qm_config_builder.build_qm_config(element_set)

qmm = QuantumMachinesManager()
qm = qmm.open_qm(qm_config)

# ----------------------------- Run experiments --------------------------------

# play CW on qm
with program() as cw:
    with infinite_loop_():
        play('CW', qubit.name)
        play('CW', rr.name)

job = qm.execute(cw)

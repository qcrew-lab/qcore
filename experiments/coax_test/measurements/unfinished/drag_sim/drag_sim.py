""" Check drag pulse waveforms with the QM simulator """
from qm.QuantumMachinesManager import QuantumMachinesManager
from qm.qua import program, play, amp, wait, declare, for_
from qm import SimulationConfig
from qcrew.experiments.coax_test.measurements.unfinished.drag_sim.configuration import (
    qm_config,
    DRAG_COEFFICIENT,
    DRAG_PULSE_LEN,
)
from qcrew.experiments.coax_test.measurements.unfinished.drag_sim.helpers import (
    plot_waveforms,
    get_processed_samples,
)

qmm = QuantumMachinesManager()

################################     QUA PROGRAMS     ##################################

# in "test1", we scale "drag1" Q waveform in qua loop
with program() as test1:
    i = declare(int)
    with for_(i, 0, i < 1, i+1):
        play("drag1" * amp(1.0, 0.0, 0.0, DRAG_COEFFICIENT), "qubit")

# in "test2", we play "drag2", whose Q waveform is scaled in the QM config
with program() as test2:
    i = declare(int)
    with for_(i, 0, i < 1, i+1):
        play("drag2" * amp(1.0), "qubit")

##############################     SIMULATION SETUP     ################################

DELAY = 100
sim_duration = int(DELAY + (DRAG_PULSE_LEN // 4))
sim_config = SimulationConfig(duration=sim_duration, include_analog_waveforms=True)

###############################     RUN SIMULATIONS     ################################

job1 = qmm.simulate(qm_config, test1, sim_config)
samples1 = job1.get_simulated_samples()
job2 = qmm.simulate(qm_config, test2, sim_config)
samples2 = job2.get_simulated_samples()

###############################     POST-PROCESSING     ################################

PADDING = 100  # plot timestamps before and after pulse is played

waveforms = {
    "i_1": get_processed_samples(samples1, job1, "1", PADDING),
    "q_1": get_processed_samples(samples1, job1, "2", PADDING),
    "i_2": get_processed_samples(samples2, job2, "1", PADDING),
    "q_2": get_processed_samples(samples2, job2, "2", PADDING),
}  # these waveforms have been sliced so that they now share the same time axis

plot_waveforms(waveforms)

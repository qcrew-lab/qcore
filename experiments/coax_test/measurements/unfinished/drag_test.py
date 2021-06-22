""" Simulate obtained drag pulse waveforms with the QM simulator"""
from qcrew.experiments.coax_test.imports import *
from qm import SimulationConfig
from pprint import pp

configuration = {
    "version": 1,
    "controllers": {
        "con1": {
            "type": "opx1",
            "analog_outputs": {
                1: {"offset": 0.0},
                2: {"offset": 0.0},
            },
        },
    },
    "elements": {
        "qubit": {
            "mixInputs": {
                "I": ("con1", 1),
                "Q": ("con1", 2),
                "lo_frequency": int(5e9),
                "mixer": "mixer_qubit",
            },
            "intermediate_frequency": int(-50e6),
            "operations": {
                "CW": "CW",
                "gaussian":"gaussian",
                "drag": "drag",
            },
        },
    },
    "pulses": {
        "CW": {
            "operation": "control",
            "length": 700,
            "waveforms": {"I": "const_wf", "Q": "zero_wf"},
        },
        "gaussian": {
            "operation": "control",
            "length": 700,
            "waveforms": {"I": "gauss_wf", "Q": "zero_wf"}
        },
        "drag": {
            "operation": "control",
            "length": 700,
            "waveforms": {"I": "gauss_wf", "Q": "dgauss_wf"}
        },
    },
    "waveforms": {
        "const_wf": {
            "type": "constant",
            "sample": 0.5,
        },
        "zero_wf": {
            "type": "constant",
            "sample": 0.0,
        },
        "gauss_wf": {
            "type": "arbitrary",
            "samples": cfg.gaussian_fn(0.2 * 1.9164, 175, 4),
        },
        "dgauss_wf": {
            "type": "arbitrary",
            "samples": cfg.gaussian_derivative_fn(0.2 * 1.9164, 13.27, 175, 4),
        },
    },
    "mixers": {
        "mixer_qubit": [
            {
                "intermediate_frequency": int(-50e6),
                "lo_frequency": int(5e9),
                "correction": (1.0, 0.0, 0.0, 1.0),
            },
        ],
    },
}

with program() as test1:
    play("gaussian", "qubit")

with program() as test2:
    play("drag", "qubit")

job1 = stg.qmm.simulate(configuration, test1, SimulationConfig(duration=300, include_analog_waveforms=True))

gsamples = job1.get_simulated_samples()

fig = plt.figure(figsize=(12, 8))
ax1, ax2 = plt.subplot(211), plt.subplot(212)

ax1.plot(gsamples.con1.analog["1"], label="gaussian AO1", color="blue")
ax1.plot(gsamples.con1.analog["2"], label="gaussian AO2", color="orange")

job2 = stg.qmm.simulate(configuration, test2, SimulationConfig(duration=300, include_analog_waveforms=True))

dsamples = job2.get_simulated_samples()
ax2.plot(dsamples.con1.analog["1"], label="drag AO1", color="blue")
ax2.plot(dsamples.con1.analog["2"], label="drag AO2", color="orange")

plt.xlabel("Time [ns]")
plt.ylabel("Signal [V]")
ax1.legend()
ax2.legend()

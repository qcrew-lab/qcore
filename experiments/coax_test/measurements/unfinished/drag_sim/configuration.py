""" QM config for drag pulse simulation """
import numpy as np
import matplotlib.pyplot as plt

DRAG_COEFFICIENT = 0.5  # used for scaling the DRAG Q waveform

########################     WAVEFORM SAMPLE GENERATOR FNS     #########################

BASE_AMP = 0.25


def drag_wfs(ampx: float, drag: float, sigma: float, chop: int) -> tuple[np.ndarray]:
    ts = np.linspace(-chop / 2 * sigma, chop / 2 * sigma, chop * sigma)
    i_wf = BASE_AMP * ampx * np.exp(-(ts ** 2) / (2.0 * sigma ** 2))
    q_wf = drag * (np.exp(0.5) / sigma) * -ts * i_wf
    return i_wf, q_wf


#############################     TOP LEVEL CONSTANTS     ##############################

QUBIT_LO_FREQ = 5e9
QUBIT_INT_FREQ = -50e6

AMPX, DRAG = 1.0, 1.0
SIGMA, CHOP = 175, 4
DRAG1_WF_SAMPLES_I, DRAG1_WF_SAMPLES_Q = drag_wfs(AMPX, DRAG, SIGMA, CHOP)
DRAG_PULSE_LEN = SIGMA * CHOP

################################      QM CONFIG      ###################################

qm_config = {
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
                "lo_frequency": int(QUBIT_LO_FREQ),
                "mixer": "mixer_qubit",
            },
            "intermediate_frequency": int(QUBIT_INT_FREQ),
            "operations": {
                "drag1": "drag1",
                "drag2": "drag2",
            },
        },
    },
    "pulses": {
        "drag1": {
            "operation": "control",
            "length": DRAG_PULSE_LEN,
            "waveforms": {"I": "gauss_wf", "Q": "dgauss_wf_1"},
        },
        "drag2": {
            "operation": "control",
            "length": DRAG_PULSE_LEN,
            "waveforms": {"I": "gauss_wf", "Q": "dgauss_wf_2"},
        },
    },
    "waveforms": {
        "zero_wf": {
            "type": "constant",
            "sample": 0.0,
        },
        "gauss_wf": {
            "type": "arbitrary",
            "samples": DRAG1_WF_SAMPLES_I,
        },
        "dgauss_wf_1": {
            "type": "arbitrary",
            "samples": DRAG1_WF_SAMPLES_Q,  # will be scaled in QUA loop
        },
        "dgauss_wf_2": {
            "type": "arbitrary",
            "samples": DRAG1_WF_SAMPLES_Q * DRAG_COEFFICIENT,  # scale in QM config
        },
    },
    "mixers": {
        "mixer_qubit": [
            {
                "intermediate_frequency": int(QUBIT_INT_FREQ),
                "lo_frequency": int(QUBIT_LO_FREQ),
                "correction": (1.0, 0.0, 0.0, 1.0),
            },
        ],
    },
}

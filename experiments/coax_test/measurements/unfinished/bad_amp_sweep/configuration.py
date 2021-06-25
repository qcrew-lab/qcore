""" QM config for bad_sweep.py """
import numpy as np

def gaussian_fn(maximum: float, sigma: float, multiple_of_sigma: int) -> np.ndarray:
    length = int(multiple_of_sigma * sigma)
    mu = int(np.floor(length / 2))
    t = np.linspace(0, length - 1, length)
    gaussian = maximum * np.exp(-((t - mu) ** 2) / (2 * sigma ** 2))
    return [float(x) for x in gaussian]

def IQ_imbalance(gain: float, phase: float) -> list[float]:
    cos = np.cos(phase)
    sin = np.sin(phase)
    coeff = 1 / ((1 - gain ** 2) * (2 * cos ** 2 - 1))
    matrix = [(1 - gain) * cos, (1 + gain) * sin, (1 - gain) * sin, (1 + gain) * cos]
    correction_matrix = [float(coeff * x) for x in matrix]
    return correction_matrix

config = {
    "version": 1,
    "controllers": {
        "con1": {
            "type": "opx1",
            "analog_outputs": {
                1: {"offset": 0.007179423904744908},
                2: {"offset": -0.006429361237678677},
                3: {"offset": 0.0017933552153408532},
                4: {"offset": -0.010745931230485443},
            },
            "analog_inputs": {
                1: {"offset": 0.0},
            },
        },
    },
    "elements": {
        "qubit": {
            "mixInputs": {
                "I": ("con1", 1),
                "Q": ("con1", 2),
                "lo_frequency": int(5.01685e9),
                "mixer": "mixer_qubit",
            },
            "intermediate_frequency": int(-50e6),
            "operations": {
                "CW": "CW",
            },
        },
    },
    "pulses": {
        "CW": {
            "operation": "control",
            "length": 800,
            "waveforms": {"I": "constant_wf", "Q": "zero_wf"},
        },
    },
    "waveforms": {
        "constant_wf": {
            "type": "constant",
            "sample": 0.25,
        },
        "zero_wf": {
            "type": "constant",
            "sample": 0.0,
        },
    },
    "mixers": {
        "mixer_qubit": [
            {
                "intermediate_frequency": int(-50e6),
                "lo_frequency": int(5.01685e9),
                "correction": IQ_imbalance(-0.18545837402343757, 0.09413375854492195),
            },
        ],
    },
}

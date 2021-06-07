import numpy as np


######################
# AUXILIARY FUNCTIONS:
######################


def gaussian_fn(maximum: float, sigma: float, multiple_of_sigma: int) -> np.ndarray:
    length = int(multiple_of_sigma * sigma)
    mu = int(np.floor(length / 2))
    t = np.linspace(0, length - 1, length)
    gaussian = maximum * np.exp(-((t - mu) ** 2) / (2 * sigma ** 2))
    return [float(x) for x in gaussian]


def IQ_imbalance(g, phi):
    c = np.cos(phi)
    s = np.sin(phi)
    N = 1 / ((1 - g ** 2) * (2 * c ** 2 - 1))
    return [float(N * x) for x in [(1 - g) * c, (1 + g) * s, (1 - g) * s, (1 + g) * c]]


################
# CONFIGURATION:
################

saturation_pulse_len = 15000
saturation_pulse_amp = 0.25

cw_pulse_len = 15000
cw_pulse_amp = 0.2

readout_len = 4000
readout_pulse_amp = 0.2

gaussian_pulse_wf_I_samples = gaussian_fn(0.25, 150, 6)  # (amp, sigma, multiple_sigma)
gaussian_pulse_len = len(gaussian_pulse_wf_I_samples)

rr_time_of_flight = 1200

rr_LO = int(9.453e9)
rr_IF = int(-49.25e6)  # int(-49.35e6)  # int(-49.51e6)

qubit_LO = int(4.1255e9)  # int(4.1286e+9)
qubit_IF = int(-50e6)

rr_mixer_gain = 0.048832416534423814
rr_mixer_phase = -0.10307483673095706
rr_offset_I = 0.10078125
rr_offset_Q = -0.008203125

qubit_mixer_gain = 0.01411627754569054
qubit_mixer_phase = 0.07736417464911938
qubit_offset_I = -0.011938131041824819
qubit_offset_Q = -0.0015285410918295388


qubit_mixer_offsets = {
    "I": qubit_offset_I,
    "Q": qubit_offset_Q,
    "G": qubit_mixer_gain,
    "P": qubit_mixer_phase,
}

rr_mixer_offsets = {
    "I": rr_offset_I,
    "Q": rr_offset_Q,
    "G": rr_mixer_gain,
    "P": rr_mixer_phase,
}

config = {
    "version": 1,
    "controllers": {
        "con1": {
            "type": "opx1",
            "analog_outputs": {
                1: {"offset": rr_offset_I},  # RR I
                2: {"offset": rr_offset_Q},  # RR Q
                3: {"offset": qubit_offset_Q},  # qubit Q
                4: {"offset": qubit_offset_I},  # qubit I
                5: {"offset": 0.0},
                6: {"offset": 0.0},
                7: {"offset": 0.0},
                8: {"offset": 0.0},
                9: {"offset": 0.0},
                10: {"offset": 0.0},
            },
            "digital_outputs": {},
            "analog_inputs": {1: {"offset": 0.0}},
        }
    },
    "elements": {
        "qubit": {
            "mixInputs": {
                "I": ("con1", 4),
                "Q": ("con1", 3),
                "lo_frequency": qubit_LO,
                "mixer": "mixer_qubit",
            },
            "intermediate_frequency": qubit_IF,
            "operations": {
                "CW": "CW",
                "saturation": "saturation_pulse",
                "gaussian": "gaussian_pulse",
            },
        },
        "rr": {
            "mixInputs": {
                "I": ("con1", 1),
                "Q": ("con1", 2),
                "lo_frequency": rr_LO,
                "mixer": "mixer_rr",
            },
            "intermediate_frequency": rr_IF,
            "operations": {
                "CW": "CW",
                "gaussian": "gaussian_pulse",
                "readout": "readout_pulse",
            },
            "outputs": {"out1": ("con1", 1)},
            "time_of_flight": rr_time_of_flight,  # 1200,
            "smearing": 12,
        },
    },
    "pulses": {
        "CW": {
            "operation": "control",
            "length": cw_pulse_len,
            "waveforms": {"I": "const_wf", "Q": "zero_wf"},
        },
        "saturation_pulse": {
            "operation": "control",
            "length": saturation_pulse_len,  # 15000,  # several T1s
            "waveforms": {"I": "saturation_wf", "Q": "zero_wf"},
        },
        "gaussian_pulse": {
            "operation": "control",
            "length": gaussian_pulse_len,
            "waveforms": {"I": "gauss_wf", "Q": "zero_wf"},
        },
        "readout_pulse": {
            "operation": "measurement",
            "length": readout_len,
            "waveforms": {"I": "readout_wf", "Q": "zero_wf"},
            "integration_weights": {
                "integW1": "integW1",
                "integW2": "integW2",
                "optW1": "optW1",
                "optW2": "optW2",
            },
            "digital_marker": "ON",
        },
    },
    "waveforms": {
        "saturation_wf": {
            "type": "constant",
            "sample": saturation_pulse_amp,
        },
        "const_wf": {
            "type": "constant",
            "sample": cw_pulse_amp,
        },
        "zero_wf": {
            "type": "constant",
            "sample": 0.0,
        },
        "gauss_wf": {
            "type": "arbitrary",
            "samples": gaussian_pulse_wf_I_samples,
        },
        "readout_wf": {
            "type": "constant",
            "sample": readout_pulse_amp,
        },
    },
    "digital_waveforms": {"ON": {"samples": [(1, 0)]}},
    "integration_weights": {
        "integW1": {
            "cosine": [1.0] * int(readout_len / 4),
            "sine": [0.0] * int(readout_len / 4),
        },
        "integW2": {
            "cosine": [0.0] * int(readout_len / 4),
            "sine": [1.0] * int(readout_len / 4),
        },
        "optW1": {
            "cosine": [1.0] * int(readout_len / 4),
            "sine": [0.0] * int(readout_len / 4),
        },
        "optW2": {
            "cosine": [0.0] * int(readout_len / 4),
            "sine": [1.0] * int(readout_len / 4),
        },
    },
    "mixers": {
        "mixer_qubit": [
            {
                "intermediate_frequency": qubit_IF,
                "lo_frequency": qubit_LO,
                "correction": IQ_imbalance(qubit_mixer_gain, qubit_mixer_phase),
            },
        ],
        "mixer_rr": [
            {
                "intermediate_frequency": rr_IF,
                "lo_frequency": rr_LO,
                "correction": IQ_imbalance(rr_mixer_gain, rr_mixer_phase),
            }
        ],
    },
}

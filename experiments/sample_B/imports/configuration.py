import numpy as np


######################
# AUXILIARY FUNCTIONS:
######################

##### Gauss wf format as given by QM.
# def gauss(amplitude, mu, sigma, length):
#    t = np.linspace(-length / 2, length / 2, length)
#    gauss_wave = amplitude * np.exp(-((t - mu) ** 2) / (2 * sigma ** 2))
#    return [float(x) for x in gauss_wave]


def gauss(amplitude, sigma, multiple_of_sigma):
    length = int(multiple_of_sigma * sigma)  # multiple of sigma should be an integer
    mu = int(np.floor(length / 2))  # instant of gaussian peak
    t = np.linspace(0, length - 1, length)  # time array ::length:: number of elements
    gauss_wave = amplitude * np.exp(-((t - mu) ** 2) / (2 * sigma ** 2))
    return [float(x) for x in gauss_wave]


def IQ_imbalance(g, phi):
    c = np.cos(phi)
    s = np.sin(phi)
    N = 1 / ((1 - g ** 2) * (2 * c ** 2 - 1))
    return [float(N * x) for x in [(1 - g) * c, (1 + g) * s, (1 - g) * s, (1 + g) * c]]


################
# CONFIGURATION:
################

long_readout_len = 4000
readout_len = 4000

rr_LO = int(9.453e9)
rr_IF = int(-50e6)

qubit_LO = int(4e9)  # int(4.1286e+9)
qubit_IF = int(-50e6)

gaussian_length = 150 * 6
gaussian_length2 = 12 * 10

delta2 = 12
mutiple_delta2 = 10
amplitude_pi_gate = 0.931


rr_mixer_gain = 0.048832416534423814
rr_mixer_phase = -0.10307483673095706
rr_offset_I = 0.10078125
rr_offset_Q = -0.008203125

# rr_mixer_gain = 0
# rr_mixer_phase =  0
# rr_offset_I = 0
# rr_offset_Q = 0

qubit_mixer_gain = -0.03290181159973145
qubit_mixer_phase = 0.12228269577026368

qubit_offset_I = -0.057408704025874606
qubit_offset_Q = 0.01968084935542721

# qubit_mixer_gain = 0
# qubit_mixer_phase = 0

# qubit_offset_I = 0
# qubit_offset_Q =  0

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
                "gaussian2": "gaussian_pulse2",
                "pi": "pi_pulse",
                "pi2": "pi2_pulse",
                "minus_pi2": "minus_pi2_pulse",
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
                "long_readout": "long_readout_pulse",
                "readout": "readout_pulse",
            },
            "outputs": {"out1": ("con1", 1)},
            "time_of_flight": 800,
            "smearing": 12,
        },
    },
    "pulses": {
        "CW": {
            "operation": "control",
            "length": 60000,
            "waveforms": {"I": "const_wf", "Q": "zero_wf"},
        },
        "saturation_pulse": {
            "operation": "control",
            "length": 20000,  # 15000,  # several T1s
            "waveforms": {"I": "saturation_wf", "Q": "zero_wf"},
        },
        "gaussian_pulse": {
            "operation": "control",
            "length": gaussian_length,
            "waveforms": {"I": "gauss_wf", "Q": "zero_wf"},
        },
        "gaussian_pulse2": {
            "operation": "control",
            "length": gaussian_length2,
            "waveforms": {"I": "gauss_wf2", "Q": "zero_wf2"},
        },
        "pi_pulse": {
            "operation": "control",
            "length": gaussian_length,
            "waveforms": {"I": "pi_wf", "Q": "zero_wf"},
        },
        "pi2_pulse": {
            "operation": "control",
            "length": gaussian_length,
            "waveforms": {"I": "pi2_wf", "Q": "zero_wf"},
        },
        "minus_pi2_pulse": {
            "operation": "control",
            "length": 60,
            "waveforms": {"I": "minus_pi2_wf", "Q": "zero_wf"},
        },
        "long_readout_pulse": {
            "operation": "measurement",
            "length": long_readout_len,
            "waveforms": {"I": "long_readout_wf", "Q": "zero_wf"},
            "integration_weights": {
                "long_integW1": "long_integW1",
                "long_integW2": "long_integW2",
            },
            "digital_marker": "ON",
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
        "const_wf": {"type": "constant", "sample": 0.25},
        "zero_wf": {"type": "constant", "sample": 0.0},
        "saturation_wf": {"type": "constant", "sample": 0.25},
        "gauss_wf": {
            "type": "arbitrary",
            "samples": gauss(0.25, 150.0, 6),  # gauss(0.25, 0.0, 6.0, 60)
        },
        "gauss_wf2": {
            "type": "arbitrary",
            "samples": gauss(0.25, delta2, mutiple_delta2),
        },
        "zero_wf2": {"type": "constant", "sample": 0.0},
        "pi_wf": {
            "type": "arbitrary",
            "samples": gauss(amplitude_pi_gate * 0.25, 150.0, 6),
        },
        "pi2_wf": {
            "type": "arbitrary",
            "samples": gauss(
                0.5 * amplitude_pi_gate * 0.25, 150.0, 6
            ),  # gauss(0.15, 6.0, 10)
        },
        "minus_pi2_wf": {"type": "arbitrary", "samples": gauss(-0.15, 6.0, 10)},
        "long_readout_wf": {"type": "constant", "sample": 0.32},
        "readout_wf": {"type": "constant", "sample": 0.25},
    },
    "digital_waveforms": {"ON": {"samples": [(1, 0)]}},
    "integration_weights": {
        "long_integW1": {
            "cosine": [1.0] * int(long_readout_len / 4),
            "sine": [0.0] * int(long_readout_len / 4),
        },
        "long_integW2": {
            "cosine": [0.0] * int(long_readout_len / 4),
            "sine": [1.0] * int(long_readout_len / 4),
        },
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

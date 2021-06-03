""" DO NOT DUPLICATE THIS FILE WHILE YOU ARE CONDUCTING THE EXPERIMENT 'COAX_TEST'"""
"""This file is the one and only place to change parameters between measurement runs"""
########################################################################################
#############           HELPER FUNCTIONS - DO NOT EDIT THIS SECTION        #############
########################################################################################
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


########################################################################################
##############################           ELEMENTS         ##############################
########################################################################################
# NOTE: you may change these parameters between measurement runs

qubit_LO = 4e9
qubit_IF = -50e6

rr_LO = 8.5993e9
rr_IF = -45.2e6

rr_time_of_flight = 444  # must be integer multiple of 4 >= 180

# NOTE: please copy paste results of mixer tuning in the respective dicts below
qubit_mixer_offsets = {
    "I": -0.0016439652070403096,
    "Q": -0.013795564696192742,
    "G": -0.1732239723205567,
    "P": 0.08982601165771487,
}
rr_mixer_offsets = {
    "I": -0.011920919595286253,
    "Q": 0.0013048585737124095,
    "G": 0.1681966945528984,
    "P": -0.1174593359231949,
}

########################################################################################
##############################            PULSES          ##############################
########################################################################################
# NOTE: consider changing pulse parameters 'on-the-fly' within a qua script (will be in clock cycles)
# NOTE: read http://qm-docs.s3.amazonaws.com/v0.90/python/qua/dsl_main.html to know how

cw_pulse_len = 1000  # must be an integer multiple of 4 >= 16
cw_pulse_amp = 0.2  # must be float in the interval (-0.5, 0.5)

readout_pulse_len = 1000  # must be an integer multiple of 4 >= 16
readout_pulse_amp = 0.2  # must be float in the interval (-0.5, 0.5)

saturation_pulse_len = 15000  # must be an integer multiple of 4 >= 16
saturation_pulse_amp = 0.2  # must be float in the interval (-0.5, 0.5)

gaussian_pulse_wf_I_samples = gaussian_fn(0.25, 150, 6)  # (amp, sigma, multiple_sigma)
gaussian_pulse_len = len(gaussian_pulse_wf_I_samples)

########################################################################################
################################           PORTS         ###############################
########################################################################################
# NOTE: change these accordingly if you change the connections of the OPX outputs/inputs

qubit_ports = {"I": 1, "Q": 2}  # from OPX's point of view, these are analog outputs
rr_ports = {"I": 4, "Q": 3, "out": 1}  # "out" is analog input from the OPX's POV

########################################################################################
###############################           CONFIG         ###############################
########################################################################################
# NOTE: edit the config only if you want to add new operations, pulses, waveforms

config = {
    "version": 1,
    "controllers": {
        "con1": {
            "type": "opx1",
            "analog_outputs": {
                qubit_ports["I"]: {"offset": qubit_mixer_offsets["I"]},
                qubit_ports["Q"]: {"offset": qubit_mixer_offsets["Q"]},
                rr_ports["I"]: {"offset": rr_mixer_offsets["I"]},
                rr_ports["Q"]: {"offset": rr_mixer_offsets["Q"]},
            },
            "analog_inputs": {
                rr_ports["out"]: {"offset": 0.0},
            },
        },
    },
    "elements": {
        "qubit": {
            "mixInputs": {
                "I": ("con1", qubit_ports["I"]),
                "Q": ("con1", qubit_ports["Q"]),
                "lo_frequency": int(qubit_LO),
                "mixer": "mixer_qubit",
            },
            "intermediate_frequency": int(qubit_IF),
            "operations": {
                "CW": "CW",
                "gaussian": "gaussian_pulse",
                "saturation": "saturation_pulse",
            },
        },
        "rr": {
            "mixInputs": {
                "I": ("con1", rr_ports["I"]),
                "Q": ("con1", rr_ports["Q"]),
                "lo_frequency": int(rr_LO),
                "mixer": "mixer_rr",
            },
            "intermediate_frequency": int(rr_IF),
            "operations": {
                "CW": "CW",
                "gaussian": "gaussian_pulse",
                "readout": "readout_pulse",
            },
            "outputs": {"out1": ("con1", rr_ports["out"])},
            "time_of_flight": rr_time_of_flight,
            "smearing": 0,
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
            "length": saturation_pulse_len,
            "waveforms": {"I": "saturation_wf", "Q": "zero_wf"},
        },
        "gaussian_pulse": {
            "operation": "control",
            "length": gaussian_pulse_len,
            "waveforms": {"I": "gauss_wf", "Q": "zero_wf"},
        },
        "readout_pulse": {
            "operation": "measurement",
            "length": readout_pulse_len,
            "waveforms": {"I": "readout_wf", "Q": "zero_wf"},
            "integration_weights": {
                "integW1": "integW1",
                "integW2": "integW2",
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
            "cosine": [1.0] * int(readout_pulse_len / 4),
            "sine": [0.0] * int(readout_pulse_len / 4),
        },
        "integW2": {
            "cosine": [0.0] * int(readout_pulse_len / 4),
            "sine": [1.0] * int(readout_pulse_len / 4),
        },
    },
    "mixers": {
        "mixer_qubit": [
            {
                "intermediate_frequency": int(qubit_IF),
                "lo_frequency": int(qubit_LO),
                "correction": IQ_imbalance(
                    qubit_mixer_offsets["G"], qubit_mixer_offsets["P"]
                ),
            },
        ],
        "mixer_rr": [
            {
                "intermediate_frequency": int(rr_IF),
                "lo_frequency": int(rr_LO),
                "correction": IQ_imbalance(
                    rr_mixer_offsets["G"], rr_mixer_offsets["P"]
                ),
            }
        ],
    },
}

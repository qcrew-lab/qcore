""" DO NOT DUPLICATE THIS FILE WHILE YOU ARE CONDUCTING THE EXPERIMENT'COAX_TEST_CAVITY'
This file is the one and only place to change parameters between measurement runs"""

BASE_AMP = 0.2

########################################################################################
##########################           HELPER FUNCTIONS        ###########################
########################################################################################
import numpy as np


def gaussian_fn(maximum: float, sigma: float, multiple_of_sigma: int) -> np.ndarray:
    length = int(multiple_of_sigma * sigma)
    mu = int(np.floor(length / 2))
    t = np.linspace(0, length - 1, length)
    gaussian = maximum * np.exp(-((t - mu) ** 2) / (2 * sigma ** 2))
    return [float(x) for x in gaussian]


def gaussian_derivative_fn(
    gauss_A: float, drag: float, sigma: float, multiple_of_sigma: int
) -> np.ndarray:
    length = int(multiple_of_sigma * sigma)
    mu = int(np.floor(length / 2))
    t = np.linspace(0, length - 1, length)
    gaussian = gauss_A * np.exp(-((t - mu) ** 2) / (2 * sigma ** 2))
    gaussian_derivative = drag * gaussian * (t - mu) / (sigma ** 2)
    return gaussian_derivative


def IQ_imbalance(gain: float, phase: float):
    cos = np.cos(phase)
    sin = np.sin(phase)
    coeff = 1 / ((1 - gain ** 2) * (2 * cos ** 2 - 1))
    matrix = [(1 - gain) * cos, (1 + gain) * sin, (1 - gain) * sin, (1 + gain) * cos]
    correction_matrix = [float(coeff * x) for x in matrix]
    return correction_matrix


def get_gaussian_waveforms(ampx: float, drag: float, sigma: float, chop: int):
    ts = np.linspace(-chop / 2 * sigma, chop / 2 * sigma, chop * sigma)
    i_wf = BASE_AMP * ampx * np.exp(-(ts ** 2) / (2.0 * sigma ** 2))
    q_wf = drag * (np.exp(0.5) / sigma) * -ts * i_wf
    return i_wf, q_wf


#### Yvonne added this for a quick test, will remove later.
def get_gaussian_waveforms_test(ampx: float, drag: float, sigma: float, chop: int):
    ts = np.linspace(-chop / 2 * sigma, chop / 2 * sigma, chop * sigma)
    i_wf = BASE_AMP * ampx * np.exp(-(ts ** 2) / (2.0 * sigma ** 2))
    q_wf = drag * (0.5 / sigma ** 2) * (-ts) * i_wf
    return i_wf, q_wf


########################################################################################
##############################           ELEMENTS         ##############################
########################################################################################

# e-f transition
# qubit_LO = 4.77685e9
# qubit_IF = -45.1e6

# g-e transition
qubit_LO = 5.01685e9
qubit_IF = -50e6

rr_LO = 8.60385e9
rr_IF = -50e6

cavity_LO = 6.6e9
cavity_IF = -50e6

rr_time_of_flight = 444  # must be integer multiple of 4 >= 180

qubit_mixer_offsets = {  # NOTE: copy paste results of mixer tuning here
    "I": 0.0,
    "Q": 0.0,
    "G": 0.0,
    "P": 0.0,
}
rr_mixer_offsets = {  # NOTE: copy paste results of mixer tuning here
    "I": -0.010745931230485443,
    "Q": 0.0017933552153408532,
    "G": 0.15548596382141114,
    "P": -0.12139883041381835,
}

cavity_mixer_offsets = {  # NOTE: copy paste results of mixer tuning here
    "I": -0.001608397328527644,
    "Q": -0.020106111897621307,
    "G": 0.18236725628376008,
    "P": -0.19818171858787537,
}

########################################################################################
##############################            PULSES          ##############################
########################################################################################

################################### ARBITRARY PULSES ###################################

cw_pulse_len = 1000  # must be an integer multiple of 4 >= 16
cw_pulse_amp = BASE_AMP  # must be float in the interval (-0.5, 0.5)

readout_pulse_len = 1000  # must be an integer multiple of 4 >= 16
readout_pulse_amp = BASE_AMP  # must be float in the interval (-0.5, 0.5)

saturation_pulse_len = 3000  # must be an integer multiple of 4 >= 16
saturation_pulse_amp = BASE_AMP  # must be float in the interval (-0.5, 0.5)

# NOTE use get_gaussian_waveforms() to get I and Q waveforms for Gaussian pulses
# set drag = 0.0, if you want no drag correction
# gauss_I_wf_samples, gauss_Q_wf_samples = get_gaussian_waveforms(1.0, 0.0, 200, 4)


# (maximum, sigma, multiple_of_sigma)
gaussian_pulse_wf_I_samples = gaussian_fn(0.2, 200, 4)
gaussian_pulse_len = len(gaussian_pulse_wf_I_samples)

# (maximum, drag, sigma, multiple_of_sigma)
gaussian_derivative_wf_samples = gaussian_derivative_fn(0.2, 1, 200, 4)
gaussian_drag_pulse_len = len(gaussian_derivative_wf_samples)

################################### EXCLUSIVE PULSES ###################################

# qubit square pi and pi2 pulses
sq_pi_len = 588  # must be an integer multiple of 4 >= 16
sq_pi2_len = 292  # must be an integer multiple of 4 >= 16
sq_pi_pi2_amp = 0.3444  # must be float in the interval (-0.5, 0.5)

# qubit gaussian pi pulse
gauss_pi_amp = 0.2  # * 1.9164
gauss_pi_sigma = 107  # 175
gauss_pi_chop = 4
gauss_pi_samples = gaussian_fn(gauss_pi_amp, gauss_pi_sigma, gauss_pi_chop)
gauss_pi_len = len(gauss_pi_samples)
# DRAG correction
drag_coeff = 13
gauss_pi_drag_samples = gaussian_derivative_fn(
    gauss_pi_amp, drag_coeff, gauss_pi_sigma, gauss_pi_chop
)

test_gauss_I, test_gauss_Q = get_gaussian_waveforms_test(1 * 1.5, 20, 250, 4)
test_gauss_len = len(test_gauss_I)

# qubit gaussian pi2 pulse
gauss_pi2_samples = gaussian_fn(0.2 * 1.877, 90, 4)  # (amp, sigma, multiple_sigma)
gauss_pi2_len = len(gauss_pi2_samples)


########################################################################################
################################           PORTS         ###############################
########################################################################################

qubit_ports = {"I": 1, "Q": 2}  # from OPX's point of view, these are analog outputs
rr_ports = {"I": 4, "Q": 3, "out": 1}  # "out" is analog input from the OPX's POV
cavity_ports = {"I": 5, "Q": 6}
########################################################################################
###############################           CONFIG         ###############################
########################################################################################

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
                cavity_ports["I"]: {"offset": rr_mixer_offsets["I"]},
                cavity_ports["Q"]: {"offset": rr_mixer_offsets["Q"]},
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
                "pi": "pi",
                "pi_drag": "pi_drag",
                "pi2": "pi2",
                "sqpi": "sqpi",
                "sqpi2": "sqpi2",
                "gaussian": "gaussian_pulse",
                "drag": "gaussian_drag_pulse",
                "saturation": "saturation_pulse",
                "test_pi": "test_pi",
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
        "cavity": {
            "mixInputs": {
                "I": ("con1", cavity_ports["I"]),
                "Q": ("con1", cavity_ports["Q"]),
                "lo_frequency": int(cavity_LO),
                "mixer": "mixer_cavity",
            },
            "intermediate_frequency": int(cavity_IF),
            "operations": {
                "CW": "CW",
                "gaussian": "gaussian_pulse",
                "saturation": "saturation_pulse",
            },
        },
    },
    "pulses": {
        "CW": {
            "operation": "control",
            "length": cw_pulse_len,
            "waveforms": {"I": "const_wf", "Q": "zero_wf"},
        },
        "pi": {
            "operation": "control",
            "length": gauss_pi_len,
            "waveforms": {"I": "gauss_pi_wf", "Q": "zero_wf"},
        },
        ### test
        "test_pi": {
            "operation": "control",
            "length": test_gauss_len,
            "waveforms": {"I": "gauss_I", "Q": "gauss_Q"},
        },
        "pi_drag": {
            "operation": "control",
            "length": gauss_pi_len,
            "waveforms": {"I": "gauss_pi_wf", "Q": "gauss_pi_drag"},
        },
        "pi2": {
            "operation": "control",
            "length": gauss_pi2_len,
            "waveforms": {"I": "gauss_pi2_wf", "Q": "zero_wf"},
        },
        "sqpi": {
            "operation": "control",
            "length": sq_pi_len,
            "waveforms": {"I": "sq_pi_pi2_wf", "Q": "zero_wf"},
        },
        "sqpi2": {
            "operation": "control",
            "length": sq_pi2_len,
            "waveforms": {"I": "sq_pi_pi2_wf", "Q": "zero_wf"},
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
        "gaussian_drag_pulse": {
            "operation": "control",
            "length": gaussian_drag_pulse_len,
            "waveforms": {"I": "gauss_wf", "Q": "gauss_derivative_wf"},
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
        "gauss_derivative_wf": {
            "type": "arbitrary",
            "samples": gaussian_derivative_wf_samples,
        },
        "readout_wf": {
            "type": "constant",
            "sample": readout_pulse_amp,
        },
        "gauss_pi_wf": {
            "type": "arbitrary",
            "samples": gauss_pi_samples,
        },
        "gauss_pi_drag": {
            "type": "arbitrary",
            "samples": gauss_pi_drag_samples,
        },
        "gauss_pi2_wf": {
            "type": "arbitrary",
            "samples": gauss_pi2_samples,
        },
        "sq_pi_pi2_wf": {
            "type": "constant",
            "sample": sq_pi_pi2_amp,
        },
        ###### test
        "gauss_I": {
            "type": "arbitrary",
            "samples": test_gauss_I,
        },
        "gauss_Q": {
            "type": "arbitrary",
            "samples": test_gauss_Q,
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
        "mixer_cavity": [
            {
                "intermediate_frequency": int(cavity_IF),
                "lo_frequency": int(cavity_LO),
                "correction": IQ_imbalance(
                    cavity_mixer_offsets["G"], cavity_mixer_offsets["P"]
                ),
            }
        ],
    },
}

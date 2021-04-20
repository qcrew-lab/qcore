import numpy as np

def gauss(amplitude, sigma, multiple_of_sigma):
    length = int(multiple_of_sigma*sigma)  # multiple of sigma should be an integer
    mu = int(np.floor(length/2))  # instant of gaussian peak
    t = np.linspace(0, length-1, length)  # time array ::length:: number of elements
    gauss_wave = amplitude * np.exp(-((t - mu) ** 2) / (2 * sigma ** 2))
    return [float(x) for x in gauss_wave]

def IQ_imbalance(g, phi):
    c = np.cos(phi)
    s = np.sin(phi)
    N = 1 / ((1-g**2)*(2*c**2-1))
    return [float(N * x) for x in [(1-g)*c, (1+g)*s, (1-g)*s, (1+g)*c]]

################
# CONFIGURATION:
################

readout_len = 400

qubit_IF = int(-50e6)
rr_IF = int(-47.25e6)

qubit_LO = int(4.165e9)
rr_LO = int(8.7571e9)

config1 = {

    'version': 1,

    'controllers': {

        'con1': {
            'type': 'opx1',
            'analog_outputs': {
                1: {'offset': 0.0},  # qubit I
                2: {'offset': 0.0},  # qubit Q
                3: {'offset': 0.0},  # RR I
                4: {'offset': 0.0},  # RR Q
                5: {'offset': 0.0},  
                6: {'offset': 0.0},  
                7: {'offset': 0.0},  
                8: {'offset': 0.0},  
                9: {'offset': 0.0},  
                10: {'offset': 0.0},  
            },
            'digital_outputs': {},
            'analog_inputs': {
                1: {'offset': 0.0},
                2: {'offset': 0.0}
            }
        }
    },

    'elements': {

        'qubit': {
            'mixInputs': {
                'I': ('con1', 1),
                'Q': ('con1', 2),
                'lo_frequency': qubit_LO,
                'mixer': 'mixer_qubit'
            },
            'intermediate_frequency': qubit_IF,
            'operations': {
                'CW': 'CW',
                'gaussian': 'gaussian_pulse',
            }
        },

        'rr': {
            'mixInputs': {
                'I': ('con1', 3),
                'Q': ('con1', 4),
                'lo_frequency': rr_LO,
                'mixer': 'mixer_rr'
            },
            'intermediate_frequency': rr_IF,
            'operations': {
                'CW': 'CW',
                'readout': 'readout_pulse',
            },
            "outputs": {
                'out1': ('con1', 1)
            },
            'time_of_flight': 824,
            'smearing': 0
        },
    },

    "pulses": {

        "CW": {
            'operation': 'control',
            'length': 60000,
            'waveforms': {
                'I': 'const_wf',
                'Q': 'zero_wf'
            }
        },

        "gaussian_pulse": {
            'operation': 'control',
            'length': int(150*4),
            'waveforms': {
                'I': 'gauss_wf',
                'Q': 'zero_wf'
            }
        },

        'readout_pulse': {
            'operation': 'measurement',
            'length': readout_len,
            'waveforms': {
                'I': 'readout_wf',
                'Q': 'zero_wf'
            },
            'integration_weights': {
                'integW1': 'integW1',
                'integW2': 'integW2',
            },
            'digital_marker': 'ON'
        },

    },

    'waveforms': {

        'const_wf': {
            'type': 'constant',
            'sample': 0.2
        },

        'zero_wf': {
            'type': 'constant',
            'sample': 0.0
        },

        'gauss_wf': {
            'type': 'arbitrary',
            'samples': gauss(0.25, 150, 4) #gauss(0.25, 0.0, 6.0, 60)
        },

        'readout_wf': {
            'type': 'constant',
            'sample': 0.25
        },
    },

    'digital_waveforms': {
        'ON': {
            'samples': [(1, 0)]
        }
    },

    'integration_weights': {

        'integW1': {
            'cosine': [1.0] * int(readout_len / 4),
            'sine': [0.0] * int(readout_len / 4),
        },

        'integW2': {
            'cosine': [0.0] * int(readout_len / 4),
            'sine': [1.0] * int(readout_len / 4),
        },
    },

    'mixers': {
        'mixer_qubit': [
            {'intermediate_frequency': qubit_IF, 'lo_frequency': qubit_LO,
             'correction':  IQ_imbalance(0.0, 0.0)},
        ],
        'mixer_rr': [
            {'intermediate_frequency': rr_IF, 'lo_frequency': rr_LO,
             'correction': IQ_imbalance(0.0, 0.0)}
        ],
    }
}


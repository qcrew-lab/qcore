import numpy as np


######################
# AUXILIARY FUNCTIONS:
######################

##### Gauss wf format as given by QM. 
#def gauss(amplitude, mu, sigma, length):
#    t = np.linspace(-length / 2, length / 2, length)
#    gauss_wave = amplitude * np.exp(-((t - mu) ** 2) / (2 * sigma ** 2))
#    return [float(x) for x in gauss_wave]

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

long_readout_len = 1000
readout_len = 400

qubit_IF = int(-54e6)
rr_IF = int(-47.5e6) #int(-50e6)

qubit_LO = int(4.165e9)
rr_LO = int(8.7571e9)

rr_mixer_gain = 0.011903211805555558
rr_mixer_phase = -0.007454427083333335
rr_offset_I = -0.1584092881944445
rr_offset_Q = 0.03345269097222221

config = {

    'version': 1,

    'controllers': {

        'con1': {
            'type': 'opx1',
            'analog_outputs': {
                1: {'offset': 0.0},  # qubit I
                2: {'offset': 0.0},  # qubit Q
                3: {'offset': rr_offset_I},  # RR I
                4: {'offset': rr_offset_Q},  # RR Q
                5: {'offset': 0.0},  
                6: {'offset': 0.0},  
                7: {'offset': 0.0},  
                8: {'offset': 0.0},  
                9: {'offset': 0.0},  
                10: {'offset': 0.0},  
            },
            'digital_outputs': {},
            'analog_inputs': {
                1: {'offset': 0.0}
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
                'saturation': 'saturation_pulse',
                'gaussian': 'gaussian_pulse',
                'pi': 'pi_pulse',
                'pi2': 'pi2_pulse',
                'minus_pi2': 'minus_pi2_pulse',
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
                'long_readout': 'long_readout_pulse',
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

        "saturation_pulse": {
            'operation': 'control',
            'length': 1000,  # several T1s
            'waveforms': {
                'I': 'saturation_wf',
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

        'pi_pulse': {
            'operation': 'control',
            'length': 60,
            'waveforms': {
                'I': 'pi_wf',
                'Q': 'zero_wf'
            }
        },

        'pi2_pulse': {
            'operation': 'control',
            'length': 60,
            'waveforms': {
                'I': 'pi2_wf',
                'Q': 'zero_wf'
            }
        },

        'minus_pi2_pulse': {
            'operation': 'control',
            'length': 60,
            'waveforms': {
                'I': 'minus_pi2_wf',
                'Q': 'zero_wf'
            }
        },

        'long_readout_pulse': {
            'operation': 'measurement',
            'length': long_readout_len,
            'waveforms': {
                'I': 'long_readout_wf',
                'Q': 'zero_wf'
            },
            'integration_weights': {
                'long_integW1': 'long_integW1',
                'long_integW2': 'long_integW2',
            },
            'digital_marker': 'ON'
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
                'optW1': 'optW1',
                'optW2': 'optW2'
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

        'saturation_wf': {
            'type': 'constant',
            'sample': 0.25
        },

        'gauss_wf': {
            'type': 'arbitrary',
            'samples': gauss(0.25, 150, 4) #gauss(0.25, 0.0, 6.0, 60)
        },

        'pi_wf': {
            'type': 'arbitrary',
            'samples': gauss(0.3, 6.0, 10)
        },

        'pi2_wf': {
            'type': 'arbitrary',
            'samples': gauss(0.15, 6.0, 10)
        },

        'minus_pi2_wf': {
            'type': 'arbitrary',
            'samples': gauss(-0.15, 6.0, 10)
        },

        'long_readout_wf': {
            'type': 'constant',
            'sample': 0.32
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

        'long_integW1': {
            'cosine': [1.0] * int(long_readout_len / 4),
            'sine': [0.0] * int(long_readout_len / 4)
        },

        'long_integW2': {
            'cosine': [0.0] * int(long_readout_len / 4),
            'sine': [1.0] * int(long_readout_len / 4)
        },

        'integW1': {
            'cosine': [1.0] * int(readout_len / 4),
            'sine': [0.0] * int(readout_len / 4),
        },

        'integW2': {
            'cosine': [0.0] * int(readout_len / 4),
            'sine': [1.0] * int(readout_len / 4),
        },

        'optW1': {
            'cosine': [1.0] * int(readout_len / 4),
            'sine': [0.0] * int(readout_len / 4)
        },

        'optW2': {
            'cosine': [0.0] * int(readout_len / 4),
            'sine': [1.0] * int(readout_len / 4)
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


# do not use


""" Run this script as-is. It prints results to stdout"""
""" Please copy-paste the offsets into the config file in the appropriate place """
""" So that the OPX can apply them the next time you run a measurement """
import time

import matplotlib.pyplot as plt
import numpy as np
from qm.qua import infinite_loop_, play, program
from scipy.optimize import minimize

from qcrew.codebase.instruments import MetaInstrument, QuantumElement, Sa124
from qcrew.experiments.sample_B.imports.stage import qubit, rr, qm, lb_qubit, lb_rr
from qcrew.experiments.sample_B.imports.configuration import qubit_IF, qubit_LO, rr_IF, rr_LO, qubit_mixer_offsets, rr_mixer_offsets


class MixerTuner(object):
    def __init__(self, qm, sa, element, lo_freq, if_freq, ref_power):
        self.qm = qm
        self.element = element
        self.sa = sa 
        self.lo_freq = lo_freq
        self.if_freq = if_freq
        self.ref_power = ref_power
        self.threshold = 0
        
        self.path_iq_imbalance = None
        self.offset_i_list = []
        self.offset_q_list = []
        self.value_lo_leakage = []
        self.value_iq_imbalance = []

        self.no_offset_correction()

    
    def no_offset_correction(self):
        self.qm.set_output_dc_offset_by_element(self.element, "I", float(0)) 
        self.qm.set_output_dc_offset_by_element(self.element, "Q", float(0))
        self.qm.set_mixer_correction("mixer_"+self.element, int(self.if_freq), int(self.lo_freq), self.IQ_imbalance(0, 0))

        with program() as cw:
            with infinite_loop_():
                play("CW", self.element)
        self.job = self.qm.execute(cw)
        freqs, amps = self.sa.sweep(center=self.lo_freq, span= 250e6, ref_power = self.ref_power)
        self.threshold = np.mean(amps)
        self.job.halt()

        plt.figure()
        plt.title("{0} signal without any offsets and correction".format(self.element))
        plt.plot(freqs, amps)
        plt.show()
        
    def offset_lo_leakage(self, fatol=3):  
        # fatol = 1dB
        print('-----------------------------------------------------')
        print('Offset Lo leakage')
        with program() as cw:
            with infinite_loop_():
                play("CW", self.element)
        self.job = self.qm.execute(cw)


        freqs_i, amps_i = sa.sweep(center=self.lo_freq, span= 250e6, ref_power = self.ref_power)
        plt.figure()
        plt.title("{0} signal before lo offsets".format(self.element))
        plt.plot(freqs_i, amps_i)
        plt.show()

        
        def objective_func(variables):
            offset_I = variables[0]
            offset_Q = variables[1]
            self.qm.set_output_dc_offset_by_element(self.element, "I", float(offset_I)) 
            self.qm.set_output_dc_offset_by_element(self.element, "Q", float(offset_Q))
        
            freqs, amps = self.sa.sweep(center=self.lo_freq, span= 250e6, ref_power = self.ref_power)
            
            # around postion of lo, required_sideband, removed_sideband
            # np.searchsorted(list, threshold, side='right') most fast way 
            # index_required_sideband = np.argmax(freq>= (self.lo_freq+self.if_freq))
            # index_removed_sideband = np.argmax(freq>= (self.lo_freq-self.if_freq))
            
            index_lo = np.argmax(freqs>= self.lo_freq)
            lo_peak_amps = amps[index_lo]
            
            
            self.value_lo_leakage.append(lo_peak_amps)
            self.offset_i_list.append(offset_I)
            self.offset_q_list.append(offset_Q)
            contrast = lo_peak_amps - self.threshold
            return np.abs(contrast)

        
        self.sa.sweep(center=self.lo_freq, span=1e6, rbw=50e3, ref_power = self.ref_power)
        result = minimize(objective_func, [0.1, 0.1], method='Nelder-Mead', options={'fatol':fatol})
        
        if result.success:
            fitted_params = result.x

            self.qm.set_output_dc_offset_by_element(self.element, "I", float(fitted_params[0])) 
            self.qm.set_output_dc_offset_by_element(self.element, "Q", float(fitted_params[1]))
            freqs_f, amps_f = self.sa.sweep(center=self.lo_freq, span= 250e6, ref_power = self.ref_power)
            plt.figure()
            plt.plot(freqs_f, amps_f)
            plt.show()
       
            print("The I Q offsets are ",fitted_params)
            self.job.halt()
            
        else:
            self.job.halt()
            raise ValueError(result.message)

    
    def lo_leakage_minimize_plot(self):
        
        plt.figure(figsize=(8, 5))
        ax = plt.axes(projection='3d')
        
        ax.scatter3D(self.offset_i_list, self.offset_q_list, self.value_lo_leakage, '-ok');

        ax.set_xlabel('$Offset I$')
        ax.set_ylabel('$Offset Q$')
        ax.set_zlabel('$Amplitdue of LO$')
        plt.show()
        
        
    def offset_iq_imbalance(self, fatol=3):  
        # fatol = 1dB
        print('Offset IQ imbalance')
        freqs_i, amps_i = sa.sweep(center=self.lo_freq, span= 250e6, ref_power = self.ref_power)
        plt.figure()
        plt.plot(freqs_i, amps_i)

        plt.show()
        
        
        def objective_func(variables):
            gain = variables[0] 
            phase = variables[1]
            self.qm.set_mixer_correction("mixer_"+self.element, int(self.if_freq), int(self.lo_freq), self.IQ_imbalance(gain, phase))
        
            freqs, amps = self.sa.sweep()
            
            # around postion of lo, required_sideband, removed_sideband
            # np.searchsorted(list, threshold, side='right') most fast way 
            # index_required_sideband = np.argmax(freq>= (self.lo_freq+self.if_freq))
            index_removed_sideband = np.argmax(freqs>= (self.lo_freq-self.if_freq))
            
            removed_sideband_peak_amps = amps[index_removed_sideband]
            contrast = removed_sideband_peak_amps - self.threshold
            print(removed_sideband_peak_amps, contrast)
            return np.abs(contrast) 
        
        self.sa.sweep(center=self.lo_freq-self.if_freq, span=1e6, rbw=50e3, ref_power = self.ref_power)
        result = minimize(objective_func, [0.1, 0.1], method='Nelder-Mead', options={'fatol':fatol})
        
        if result.success:
            fitted_params = result.x
            self.qm.set_mixer_correction("mixer_"+self.element, int(self.if_freq), int(self.lo_freq), self.IQ_imbalance(fitted_params[0], fitted_params[1]))
            
            freqs_f, amps_f = self.sa.sweep(center=self.lo_freq, span= 200e6, ref_power = self.ref_power)

            plt.figure()
            plt.plot(freqs_f, amps_f)
            plt.show()
            
            print("The mixer correction is ",fitted_params)

        else:
            raise ValueError(result.message)
        
        self.close_job()

    def IQ_imbalance(self, g, phi):
        c = np.cos(phi)
        s = np.sin(phi)
        N = 1 / ((1-g**2)*(2*c**2-1))
        return [float(N * x) for x in [(1-g)*c, (1+g)*s, (1-g)*s, (1+g)*c]]
###############################################
# sa 
############################################### 
sa = Sa124(name="sa", serial_number=20234154)
###############################################
# rr 
###############################################  
rr_lo_freq = rr_LO
rr_if_freq = rr_IF
rr_mixertunning = MixerTuner(qm, sa, "rr", rr_lo_freq, rr_if_freq, ref_power=-20 )
rr_mixertunning.offset_lo_leakage()
rr_mixertunning.offset_iq_imbalance()



with program() as cw:
    with infinite_loop_():
        play("CW","rr")

job = qm.execute(cw)
freqs, amps = sa.sweep(center = rr.lo_freq, span = 200e6, ref_power = 0)
plt.plot(freqs, amps)
job.halt()


    
with program() as cw:
    with infinite_loop_():
        play("CW","qubit")
job = qm.execute(cw)
freqs, amps = sa.sweep(center = qubit_LO, span = 200e6, ref_power = 0)
plt.plot(freqs, amps)
job.halt()

sa.disconnect()


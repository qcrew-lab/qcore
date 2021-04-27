"""
A python class describing a power rabi measurement using the QM 
system. 
This class serves as a QUA script generator with user-defined parameters. It 
also defines how the information is retrieved from result handles.
"""
# --------------------------------- Imports ------------------------------------
import numpy as np
import itertools

from measurements.measurement import Measurement
from parameter import Parameter
from qm.qua import *

# ---------------------------------- Class -------------------------------------

class QubitT2(Measurement):
    """
    TODO - WRITE CLASS DOCU
    """
    def __init__(self, name, quantum_machine, reps, wait_time, tau,
                 rr_f, rr_ascale, qubit_f, qubit_ascale, qubit_pulse):
    
        super().__init__(name=name, quantum_machine = quantum_machine)
        
        self._create_parameters(reps, wait_time, tau, rr_f, rr_ascale, 
                                qubit_f, qubit_ascale, qubit_pulse)
        self._setup()
        self.queued_job = None

        # Tags referring to the memory locations where the results are saved.
        # Defined in self._script() function.
        self._result_tags = []

    def _script(self):
        """
        This function generates and returns a power rabi QUA script
        with user-defined parameters. 
        
        Returns: TODO
            [type]: QUA script for power rabi experiment.
        """

        # Defines buffer size for averaging
        tau_buf = len(self._tau.value)
        
        with program() as qubit_T2:
            # Iteration variable
            n = declare(int)
            
            # QUA variables
            t = declare(int)
            qu_a = declare(fixed, value = self._qubit_ascale.value)
            rr_a = declare(fixed, value = self._rr_ascale.value)

            # Arrays for sweeping
            tau = declare(int, value=self._tau.value)
            
            # Outputs
            I = declare(fixed)
            Q = declare(fixed)
            
            # Streams
            I_st_avg = declare_stream()
            Q_st_avg = declare_stream()
            I_st = declare_stream()
            Q_st = declare_stream()
            
            update_frequency('qubit', self._qubit_f.value)
            update_frequency('rr', self._rr_f.value)

            with for_(n, 0, n < self._reps.value, n + 1):
                with for_each_(t, tau):
                    play(self._qubit_pulse.value * amp(qu_a), 'qubit')
                    wait(t, 'qubit')
                    play(self._qubit_pulse.value * amp(qu_a), 'qubit')
                    align('qubit', 'rr')
                    measure("long_readout" * amp(rr_a), 
                            "rr", None, 
                            demod.full('long_integW1', I), 
                            demod.full('long_integW2', Q))
                    wait(self._wait_time.value, "rr")
                    save(I, I_st_avg)
                    save(Q, Q_st_avg) 
                    save(I, I_st)
                    save(Q, Q_st) 
                                            
            with stream_processing():
                I_st_avg.buffer(tau_buf).average().save_all('I_avg')
                Q_st_avg.buffer(tau_buf).average().save_all('Q_avg')
                I_st.buffer(tau_buf).save_all('I')
                Q_st.buffer(tau_buf).save_all('Q')

        self._result_tags = ['I', 'Q', 'I_avg', 'Q_avg']

        return qubit_T2

    def _create_parameters(self, reps, wait_time, tau, rr_f, rr_ascale, 
                           qubit_f, qubit_ascale, qubit_pulse):
        """
        TODO create better variable check
        """
            
        if type(tau).__name__ not in ['list', 'ndarray']:
            tau = [tau]
        
        qubit_f = int(qubit_f)
        rr_f = int(rr_f)
        wait_time = int(wait_time)

        self._parameters = dict()
        self.create_parameter(name='Repetitions', value=reps)
        self.create_parameter(name='Wait time', value=wait_time, unit='cc')
        self.create_parameter(name='Qubit relaxation time', 
                              value=tau, unit='cc')
        self.create_parameter(name='Resonator frequency', 
                              value=rr_f, unit='Hz')
        self.create_parameter(name='Resonator pulse amp. scaling', 
                              value=rr_ascale, unit='unit')
        self.create_parameter(name='Qubit frequency', 
                              value=qubit_f, unit='Hz')
        self.create_parameter(name='Qubit pulse amp. scaling', 
                              value=qubit_ascale, unit='unit')
        self.create_parameter(name='Qubit pulse name', 
                              value=qubit_pulse)

        self._reps = self._parameters['Repetitions']
        self._wait_time = self._parameters['Wait time']
        self._tau= self._parameters['Qubit relaxation time']
        self._rr_f = self._parameters['Resonator frequency']
        self._rr_ascale = self._parameters['Resonator pulse amp. scaling']
        self._qubit_f = self._parameters['Qubit frequency']
        self._qubit_ascale = self._parameters['Qubit pulse amp. scaling']
        self._qubit_pulse = self._parameters['Qubit pulse name']

    def _setup(self):
        """
        TODO Makes sure all necessary devices are set up with correct parameters
        """
        
        return    
        
    def _create_yaml_map(self):
        # TODO
        return


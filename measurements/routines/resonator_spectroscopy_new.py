"""
A python class describing a resonator spectroscopy measurement using the QM 
system. 

This class serves as a QUA script generator with user-defined parameters. It 
also defines how jobs are placed in queue and how the information is retrieved.
"""
# --------------------------------- Imports ------------------------------------
import numpy as np

from measurements.measurement import PhysicalMeasurement
from parameter import Parameter
from qm.qua import *

# ---------------------------------- Class -------------------------------------
class ResonatorSpectroscopy(PhysicalMeasurement):
    """
    TODO - WRITE CLASS DOCU
    """
    def __init__(self, name: str, reps: int, wait_time: int, rr_f_vec,
                 rr_ascale: float, qubit_ascale = None, 
                 qubit_pulse = None):
    
        super().__init__(name=name)
        
        self._create_parameters(reps, wait_time, rr_f_vec, rr_ascale, 
                                qubit_ascale, qubit_pulse)
        self._setup()
        self.queued_job = None

    def _script(self):
        # TODO add more parameter sweep
        play_qubit_pulse = True if self.qubit_ascale else False
        buffer_len = len(self.rr_f_vec)
        
        with program() as rr_spec:
            
            n = declare(int)
            f = declare(int)
            I = declare(fixed)
            Q = declare(fixed)
            
            I_st = declare_stream()
            Q_st = declare_stream()
            
            with for_(n, 0, n < self.reps, n + 1):
                with for_each_(f, self.rr_f_vec):
                    update_frequency("rr", f)
                    play(self.qubit_pulse * amp(self.qubit_ascale), 
                        'qubit', condition = play_qubit_pulse)
                    align('qubit', 'rr')
                    measure("long_readout" * amp(self.rr_ascale), "rr", None, 
                            demod.full('long_integW1', I), 
                            demod.full('long_integW2', Q))
                    wait(self.wait_time, "rr")
                    save(I, I_st)
                    save(Q, Q_st)   
            
            with stream_processing():
                I_st.buffer(buffer_len).average().save('I')
                Q_st.buffer(buffer_len).average().save('Q')

        return rr_spec

    def results(wait = False, timeout:float = None):
        '''
        Retrieves the experiment results if the job is complete. Else, throws 
        an error message and returns None. If wait = True, halts script 
        execution until the job is completed.
        '''
        
        res_handles = self._result_handles(wait = wait, timeout = timeout)
        
        if not res_handles:
            return
        
        I_handle = res_handles.get('I')
        Q_handle = res_handles.get('Q')

        I_list = I_handle.fetch_all()
        Q_list = Q_handle.fetch_all()
        
        return I_list, Q_list

    def _setup(self):
        """
        TODO Makes sure all necessary devices are set up with correct parameters
        """
        
        return    
    
    def _create_parameters(self, reps, wait_time, rr_f_vec, rr_ascale, 
                           qubit_ascale, qubit_pulse):
        
        self._parameters = dict()
        self.create_parameter(name='repetitions', value=reps, unit='unit')
        self.create_parameter(name='wait time', value=wait_time, unit='us')
        self.create_parameter(name='Resonator frequency sweep vector', 
                              value=rr_f_vec, unit='Hz')
        self.create_parameter(name='Resonator pulse amp. scaling', 
                              value=rr_ascale, unit='unit')
        self.create_parameter(name='Qubit pulse amplitude scaling', 
                              value=qubit_ascale, unit='unit')
        self.create_parameter(name='Qubit pulse name', 
                              value=qubit_pulse)

        self._reps = self._parameters['repetitions']
        self._wait_time = self._parameters['wait time']
        self._rr_f_vec = self._parameters['Resonator frequency sweep vector']
        self._rr_ascale = self._parameters['Resonator pulse amp. scaling']
        self._qubit_ascale = self._parameters['Qubit pulse amp. scaling']
        self._qubit_pulse = self._parameters['Qubit pulse name']


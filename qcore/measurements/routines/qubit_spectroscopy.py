"""
A python class describing a qubit spectroscopy measurement using the QM 
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

class QubitSpectroscopy(Measurement):
    """
    TODO - WRITE CLASS DOCU
    """
    def __init__(self, name, quantum_machine, reps, wait_time, rr_f
                 rr_ascale, qubit_f, qubit_ascale, qubit_pulse, average = True):
    
        super().__init__(name=name, quantum_machine = quantum_machine)
        
        self._create_parameters(reps, wait_time, rr_f, rr_ascale, 
                                qubit_f, qubit_ascale, qubit_pulse, average)
        self._setup()
        self.queued_job = None

        # Tags referring to the memory locations where the results are saved.
        # Defined in self._script() function.
        self._result_tags = []

    def _script(self):
        """
        This function generates and returns a qubit spectroscopy QUA script
        with user-defined parameters. 
        
        Returns: TODO
            [type]: QUA script for qubit spectroscopy experiment.
        """

        # Rearranges the input parameters in arrays over which QUA can 
        # iterate. The arrays are given in the order of outer to inner
        # loop.
        parameter_list = [(x.flatten()) 
                          for x in np.meshgrid(self._qubit_ascale.value,
                                               self._qubit_f.value,
                                               indexing = 'ij')]
        
        # Names each parameter list and converts types when necessary
        qu_a_vec_py = parameter_list[0]
        qu_f_vec_py = [int(x) for x in parameter_list[1]]
        
        # Defines buffer size for averaging
        qu_a_buf = len(self._qubit_ascale.value)
        qu_f_buf = len(self._qubit_f.value)
        
        with program() as qubit_spec:
            # Iteration variable
            n = declare(int)
            
            # Spectroscopy parameters
            qu_a = declare(fixed)
            qu_f = declare(int)
            
            # Arrays for sweeping
            qu_a_vec = declare(fixed, value=qu_a_vec_py)
            qu_f_vec = declare(int, value=qu_f_vec_py)
            
            # Outputs
            I = declare(fixed)
            Q = declare(fixed)
            
            # Streams
            I_st = declare_stream()
            Q_st = declare_stream()
            
            update_frequency('rr', rr_f)

            with for_(n, 0, n < self._reps.value, n + 1):
                with for_each_((qu_a, qu_f), (qu_a_vec, qu_f_vec)):
                    update_frequency('qubit', qu_f)
                    play(self._qubit_pulse.value * amp(qu_a), 'qubit')
                    align('qubit', 'rr')
                    measure("long_readout" * amp(self._rr_ascale.value), 
                            "rr", None, 
                            demod.full('long_integW1', I), 
                            demod.full('long_integW2', Q))
                    wait(self._wait_time.value, "rr")
                    save(I, I_st)
                    save(Q, Q_st) 
                          
            if self._average.value:
                with stream_processing():
                    (I_st.buffer(qu_a_buf, qu_f_buf)
                     .average().save('I'))
                    (Q_st.buffer(qu_a_buf, qu_f_buf)
                     .average().save('Q'))
            else:
                with stream_processing():
                    I_st.buffer(qu_a_buf, qu_f_buf).save_all('I')
                    Q_st.buffer(qu_a_buf, qu_f_buf).save_all('Q')

        self._result_tags = ['I', 'Q']

        return qubit_spec

    def _create_parameters(self, reps, wait_time, rr_f, rr_ascale, 
                           qubit_f, qubit_ascale, qubit_pulse, average):
        """
        TODO create better variable check
        """
        
        if type(qubit_f).__name__ not in ['list', 'ndarray']:
            qubit_f = [int(x) for x in qubit_f]
            
        if type(qubit_ascale).__name__ not in ['list', 'ndarray']:
            qubit_ascale = [qubit_ascale]
        
        rr_f = int(rr_f)
        wait_time = int(wait_time)

        self._parameters = dict()
        self.create_parameter(name='Repetitions', value=reps)
        self.create_parameter(name='Wait time', value=wait_time, unit='cc')
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
        self.create_parameter(name='Compute average result bool', 
                              value=average)

        self._reps = self._parameters['Repetitions']
        self._wait_time = self._parameters['Wait time']
        self._rr_f = self._parameters['Resonator frequency']
        self._rr_ascale = self._parameters['Resonator pulse amp. scaling']
        self._qubit_f = self._parameters['Qubit frequency']
        self._qubit_ascale = self._parameters['Qubit pulse amp. scaling']
        self._qubit_pulse = self._parameters['Qubit pulse name']
        self._average = self._parameters['Compute average result bool']

    def _setup(self):
        """
        TODO Makes sure all necessary devices are set up with correct parameters
        """
        
        return  
        
    def _create_yaml_map(self):
        # TODO
        return


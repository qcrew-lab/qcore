"""
A python class describing a resonator spectroscopy measurement using the QM 
system. 

This class serves as a QUA script generator with user-defined parameters. It 
also defines how the information is retrieved from result handles.
"""
# --------------------------------- Imports ------------------------------------
import numpy as np
from scipy.stats import norm
import itertools

from measurements.measurement import Measurement
from parameter import Parameter
from qm.qua import *

# ---------------------------------- Class -------------------------------------
class ResonatorSpectroscopy(Measurement):
    """
    TODO - WRITE CLASS DOCU
    """
    def __init__(self, name: str, quantum_machine, reps: int, wait_time,
                 rr_f_vec, rr_ascale, qubit_ascale = 0.0, 
                 qubit_pulse = None, amp_error = False):
    
        super().__init__(name=name, quantum_machine = quantum_machine)
        
        self._create_parameters(reps, wait_time, rr_f_vec, rr_ascale, 
                                qubit_ascale, qubit_pulse, amp_error)
        self._setup()
        self.queued_job = None

class ResonatorSpectroscopy(Measurement):
    """
    TODO - WRITE CLASS DOCU
    """
    def __init__(self, name: str, quantum_machine, reps: int, wait_time,
                 rr_f_vec, rr_ascale, qubit_ascale = 0.0, 
                 qubit_pulse = None, amp_error = False):
    
        super().__init__(name=name, quantum_machine = quantum_machine)
        
        self._create_parameters(reps, wait_time, rr_f_vec, rr_ascale, 
                                qubit_ascale, qubit_pulse, amp_error)
        self._setup()
        self.queued_job = None

    def _script(self):
        """
        This function generates and returns a resonator spectroscopy QUA script
        with user-defined parameters. 
        
        Besides rr_f_vec, the input parameters wait_time, rr_ascale, and
        qubit_ascale also admit lists of values. In such case, the script will iterate over all possible parameter configurations.

        Returns: TODO
            [type]: QUA script for resonator spectroscopy experiment.
        """
        
        # Checks whether a qubit pulse is played and whether the information is 
        # complete.
        play_qubit_pulse = True if self._qubit_pulse.value else False
        if play_qubit_pulse and not self._qubit_ascale.value:
            print('ERROR: Define the qubit pulse amplitude scaling.')
            return

        # Rearranges the input parameters in arrays over which QUA can 
        # iterate. The arrays are given in the order of outer to inner
        # loop.
        parameter_list = [(x.flatten()) 
                          for x in np.meshgrid(self._qubit_ascale.value,
                                               self._rr_ascale.value, 
                                               self._rr_f_vec.value,
                                               indexing = 'ij')]
        
        # Names each parameter list and converts types when necessary
        qu_a_vec_py = parameter_list[0]
        rr_a_vec_py = parameter_list[1]
        rr_f_vec_py = [int(x) for x in parameter_list[2]]
        
        # Defines buffer size for averaging
        qu_a_buf = len(self._qubit_ascale.value)
        rr_a_buf = len(self._rr_ascale.value)
        rr_f_buf = len(self._rr_f_vec.value)
        
        with program() as rr_spec:
            # Iteration variable
            n = declare(int)
            
            # Spectroscopy parameters
            wt = declare(int, value = self._wait_time.value)
            qu_a = declare(fixed)
            rr_a = declare(fixed)
            rr_f = declare(int)
            
            # Arrays for sweeping
            qu_a_vec = declare(fixed, value=qu_a_vec_py)
            rr_a_vec = declare(fixed, value=rr_a_vec_py)
            rr_f_vec = declare(int, value=rr_f_vec_py)
            
            # Outputs
            I = declare(fixed)
            Q = declare(fixed)
            
            # Streams
            I_st = declare_stream()
            Q_st = declare_stream()
            
            with for_(n, 0, n < self._reps.value, n + 1):
                with for_each_((qu_a, rr_a, rr_f), 
                               (qu_a_vec, rr_a_vec, rr_f_vec)):
                    update_frequency("rr", rr_f)
                    if play_qubit_pulse:
                        play(self._qubit_pulse.value * amp(qu_a),
                                'qubit')
                    align('qubit', 'rr')
                    measure("long_readout" * amp(rr_a), "rr", None, 
                            demod.full('long_integW1', I), 
                            demod.full('long_integW2', Q))
                    wait(wt, "rr")
                    save(I, I_st)
                    save(Q, Q_st) 
                          
            if self._amp_error.value:
                with stream_processing():
                    I_st.buffer(qu_a_buf, rr_a_buf, rr_f_buf).save_all('I')
                    Q_st.buffer(qu_a_buf, rr_a_buf, rr_f_buf).save_all('Q')
            else:
                with stream_processing():
                    (I_st.buffer(qu_a_buf, rr_a_buf, rr_f_buf)
                     .average().save('I'))
                    (Q_st.buffer(qu_a_buf, rr_a_buf, rr_f_buf)
                     .average().save('Q'))

        return rr_spec
    
    
    def results(self, wait = False, timeout:float = None):
        '''
        Retrieves the experiment results if the job is complete. Else, throws 
        an error message and returns None. If wait = True, halts script 
        execution until the job is completed.
        
        Returns: [TODO] 
        '''
        
        # Get result handles and I and Q lists.
        res_handles = self._result_handles(wait = wait, timeout = timeout)
        
        if not res_handles:
            return
        
        I_handle = res_handles.get('I')
        Q_handle = res_handles.get('Q')
        
        I_list = I_handle.fetch_all(flat_struct=True)
        Q_list = Q_handle.fetch_all(flat_struct=True)
        
        if self._amp_error.value:
            # Loop over inner matrix, calculate the amplitude of I + 1jQ
            # and fit it to gaussian.
            
            qu_a_len = len(self._qubit_ascale.value)
            rr_a_len = len(self._rr_ascale.value)
            rr_f_len = len(self._rr_f_vec.value)
            
            qu_a_range = range(qu_a_len)
            rr_a_range = range(rr_a_len)
            rr_f_range = range(rr_f_len)
            
            amp_std_list = np.zeros(qu_a_len, rr_a_len, rr_f_len)
            for i,j,k in itertools.product(qu_a_range, rr_a_range, rr_f_range):
                rep_I_list = I_list[:, i, j, k]
                rep_I_list = Q_list[:, i, j, k]
                rep_amp_list = np.abs(rep_I_list + 1j*rep_I_list)
                amp_std_list[i,j,k] = norm.fit(rep_amp_list)[1]
                
            avg_I_list = np.average(I_list, axis = 0)
            avg_Q_list = np.average(Q_list, axis = 0)
            
            return {'I':avg_I_list, 'Q':avg_Q_list, 'amp_error':amp_std_list} 
        else:
            return {'I':I_list, 'Q':Q_list}

    def save_results(self, filename, wait = False, timeout:float = None):
        '''
        Retrieves the experiment results if the job is complete and saves 
        them in a .npz file with the given name. If the job is not complete, 
        throws an error message. If wait = True, it waits for the job to be 
        concluded.
        '''
        
        # Gets measurement results
        results = self.results(wait = wait, timeout = timeout)
        
        # If None, tells the user
        if not results:
            print('Results are not saved.')
            return
        
        # Builds the dictionaries to be saved into .npz file.
        
        # freq_range_dict['rr_f_vec'] contains the spectroscopy frequency
        # points. The i-th value of this list corresponds to the frequency of 
        # measurement pulse for the results stored in the i-th elements of 
        # I_list_i and Q_list_i.
        freq_range_dict = {'rr_f_vec': self._rr_f_vec}
        
        # parameters_dict track the parameters used for obtaining each I_list 
        # and Q_list. For example, parameters_dict['wait_time'][i] contains the 
        # wait_time value related to I_list_i and Q_list_i stored in 
        # results_dict
        parameters_dict = {'wait_time': [],
                           'rr_ascale': [],
                           'qubit_ascale': [],
                           'reps': [], 
                           'qubit_pulse': []}
        
        # results_dict saves I and Q arrays labeled by integers (e.g. I_list_1)
        # , where each value corresponds to a frequency in rr_f_vec. The 
        # integer corresponds to the index of the corresponding parameter in 
        # the parameters_dict arrays.
        results_dict = dict()
        
        for indx, params in enumerate(results.keys()):
            
            # Save parameters
            parameters_dict['wait_time'].append(params[0])
            parameters_dict['rr_ascale'].append(params[1])
            parameters_dict['qubit_ascale'].append(params[2])
            parameters_dict['reps'].append(self._reps)
            parameters_dict['qubit_pulse'].append(self._qubit_pulse)
            
            # Save results
            results_dict['I_list_%d' % indx] = results[params]['I']
            results_dict['Q_list_%d' % indx] = results[params]['Q']
        
        # Saves the dictionaries to the file with given name
        np.savez(filename, **results_dict, **parameters_dict, **freq_range_dict)
        
        return 

    def _setup(self):
        """
        TODO Makes sure all necessary devices are set up with correct parameters
        """
        
        return    
    
    def _create_parameters(self, reps, wait_time, rr_f_vec, rr_ascale, 
                           qubit_ascale, qubit_pulse, amp_error):
        """
        TODO create better variable check
        """
        
        if type(rr_f_vec).__name__ not in ['list', 'ndarray']:
            rr_f_vec = [rr_f_vec]
            
        if type(rr_ascale).__name__ not in ['list', 'ndarray']:
            rr_ascale = [rr_ascale]
            
        if type(qubit_ascale).__name__ not in ['list', 'ndarray']:
            qubit_ascale = [qubit_ascale]
        
        self._parameters = dict()
        self.create_parameter(name='repetitions', value=reps, unit='unit')
        self.create_parameter(name='wait time', value=wait_time, unit='cc')
        self.create_parameter(name='Resonator frequency sweep vector', 
                              value=rr_f_vec, unit='Hz')
        self.create_parameter(name='Resonator pulse amp. scaling', 
                              value=rr_ascale, unit='unit')
        self.create_parameter(name='Qubit pulse amp. scaling', 
                              value=qubit_ascale, unit='unit')
        self.create_parameter(name='Qubit pulse name', 
                              value=qubit_pulse)
        self.create_parameter(name='Amplitude error bar bool', 
                              value=amp_error)

        self._reps = self._parameters['repetitions']
        self._wait_time = self._parameters['wait time']
        self._rr_f_vec = self._parameters['Resonator frequency sweep vector']
        self._rr_ascale = self._parameters['Resonator pulse amp. scaling']
        self._qubit_ascale = self._parameters['Qubit pulse amp. scaling']
        self._qubit_pulse = self._parameters['Qubit pulse name']
        self._amp_error = self._parameters['Amplitude error bar bool']
        
    def _create_yaml_map(self):
        # TODO
        return



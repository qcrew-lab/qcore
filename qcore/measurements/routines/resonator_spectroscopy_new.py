"""
A python class describing a resonator spectroscopy measurement using the QM 
system. 

This class serves as a QUA script generator with user-defined parameters. It 
also defines how the information is retrieved from result handles.
"""
# --------------------------------- Imports ------------------------------------
import numpy as np

from measurements.measurement import Measurement
from parameter import Parameter
from qm.qua import *

# ---------------------------------- Class -------------------------------------
class ResonatorSpectroscopy(Measurement):
    """
    TODO - WRITE CLASS DOCU
    """
    def __init__(self, name: str, quantum_machine, reps: int, wait_time: int,
                 rr_f_vec, rr_ascale: float, qubit_ascale = None, 
                 qubit_pulse = None):
    
        super().__init__(name=name, quantum_machine = quantum_machine)
        
        self._create_parameters(reps, wait_time, rr_f_vec, rr_ascale, 
                                qubit_ascale, qubit_pulse)
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
        play_qubit_pulse = True if self._qubit_ascale.value else False
        if play_qubit_pulse and not self._qubit_pulse.value:
            print('ERROR: Pass the qubit pulse name using qubit_pulse input.')
            return

        # Rearranges the input parameters in arrays over which QUA can 
        # iterate.         
        parameter_list = [(x.flatten()) 
                          for x in np.meshgrid(self._wait_time.value,
                                               self._rr_ascale.value, 
                                               self._qubit_ascale.value)]
        print(self._rr_f_vec.value)
        print(parameter_list[0])
        # Defines buffer size for averaging
        buffer_size = len(self._rr_f_vec.value)*len(parameter_list[0])
        
        with program() as rr_spec:
            # Iteration variable
            n = declare(int)
            
            # Spectroscopy parameters
            wt = declare(int)
            rr_f = declare(int)
            rr_a = declare(fixed)
            qu_a = declare(fixed)
            
            # Arrays for sweeping
            rr_f_vec = declare(fixed, value=self._rr_f_vec.value)
            rr_a_vec = declare(fixed, value=parameter_list[1])
            qu_a_vec = declare(fixed, value=parameter_list[2])
            wt_vec = declare(int, value=parameter_list[0])
            
            # Outputs
            I = declare(fixed)
            Q = declare(fixed)
            
            # Streams
            I_st = declare_stream()
            Q_st = declare_stream()
            
            with for_(n, 0, n < self._reps.value, n + 1):
                # Should first loop over the parameters for adequate buffering
                with for_each_((wt, rr_a, qu_a), (wt_vec, rr_a_vec, qu_a_vec)):
                    with for_each_(rr_f, rr_f_vec):
                        update_frequency("rr", rr_f)
                        play(self._qubit_pulse.value * amp(qu_a), 
                            'qubit', condition = play_qubit_pulse)
                        align('qubit', 'rr')
                        measure("long_readout" * amp(rr_a), "rr", None, 
                                demod.full('long_integW1', I), 
                                demod.full('long_integW2', Q))
                        wait(wt, "rr")
                        save(I, I_st)
                        save(Q, Q_st)   
            
            with stream_processing():
                I_st.buffer(buffer_size).average().save('I')
                Q_st.buffer(buffer_size).average().save('Q')

        return rr_spec

    def results(wait = False, timeout:float = None):
        '''
        Retrieves the experiment results if the job is complete. Else, throws 
        an error message and returns None. If wait = True, halts script 
        execution until the job is completed.
        
        Returns:
            results: a dictionary which keys are tuples of parameter values
            (wait_time, rr_ascale, qubit_ascale) and values are dictionaries 
            {'I': [], 'Q': []} returning the measured I and Q values for the 
            frequency range defined in rr_f_vec. 
        '''
        
        # Get result handles and I and Q lists.
        res_handles = self._result_handles(wait = wait, timeout = timeout)
        
        if not res_handles:
            return
        
        I_handle = res_handles.get('I')
        Q_handle = res_handles.get('Q')
        
        I_list = I_handle.fetch_all()
        Q_list = Q_handle.fetch_all()
        
        # Slice the spectroscopy results and index with the corresponding
        # parameters used.
        parameter_list = [list(x.flatten()) 
                           for x in np.meshgrid(self._wait_time.value,
                                                self._rr_ascale.value, 
                                                self._qubit_ascale.value)]
        
        results = {}
        for i, par in enumerate(zip(*parameter_list)):
            start_index = len(self._rr_f_vec.value)*i
            end_index = len(self._rr_f_vec.value)*(i+1)
            sliced_I = I_list[start_index:end_index]
            sliced_Q = Q_list[start_index:end_index]
            results[par] = {'I': sliced_I, 'Q': sliced_Q}
        
        return results

    def save_results(filename, wait = False, timeout:float = None):
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
                           qubit_ascale, qubit_pulse):
        
        self._parameters = dict()
        self.create_parameter(name='repetitions', value=reps, unit='unit')
        self.create_parameter(name='wait time', value=wait_time, unit='us')
        self.create_parameter(name='Resonator frequency sweep vector', 
                              value=rr_f_vec, unit='Hz')
        self.create_parameter(name='Resonator pulse amp. scaling', 
                              value=rr_ascale, unit='unit')
        self.create_parameter(name='Qubit pulse amp. scaling', 
                              value=qubit_ascale, unit='unit')
        self.create_parameter(name='Qubit pulse name', 
                              value=qubit_pulse)

        self._reps = self._parameters['repetitions']
        self._wait_time = self._parameters['wait time']
        self._rr_f_vec = self._parameters['Resonator frequency sweep vector']
        self._rr_ascale = self._parameters['Resonator pulse amp. scaling']
        self._qubit_ascale = self._parameters['Qubit pulse amp. scaling']
        self._qubit_pulse = self._parameters['Qubit pulse name']
        
    def _create_yaml_map(self):
        # TODO
        return



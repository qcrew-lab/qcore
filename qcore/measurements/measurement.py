"""
Measurement.
"""
from abc import abstractmethod
import time
import numpy as np

from parameter import Parameter
from utils.yamlizer import Yamlable

class Measurement(Yamlable):
    """
    Abstract base class for Measurement.
    A Measurement has a name and is a container of Parameters. It has methods to
    add, remove, create a given parameter. Can be loaded from or saved to yaml
    file as it inherits from yamlable.
    
    The class provides the methods to queue a job and to diagnose its status.
    """
    def __init__(self, name: str, quantum_machine):
        self._name = name
        self._quantum_machine = quantum_machine
        self._job = None
        self._queued_job = None
        self.saved_results = {}

    @abstractmethod
    def _create_parameters(self):
        pass

    def create_parameter(self, name: str, value = None, unit: str = None,
                         maximum = None, minimum = None):
        new_parameter = Parameter(name, value, unit, maximum, minimum)
        self.add_parameter(new_parameter)

    def add_parameter(self, parameter: Parameter):
        # raise error if param alr exists, do error logging instead of print
        if parameter.name in self._parameters:
            raise ValueError("Parameter of this name alr exists in instrument.")
        else:
            self._parameters[parameter.name] = parameter

    def remove_parameter(self, parameter: Parameter):
        # do error logging instead of print statement
        try:
            del self._parameters[parameter.name]
        except KeyError:
            print("Parameter does not exist in the Instrument.")

    
    @abstractmethod
    def _setup(self):
        """
        Makes sure all instruments are connected and correctly set up. 
        """
        pass

    @abstractmethod
    def _script(self):
        """
        Performs the measurement and saves the results in a database.
        """
        pass
    
    def queue_job(self):
        """
        TODO
        """
         
        current_status = self._current_status()
        
        if current_status == 'in execution':
            print('Cleaning last job.')
            self._job.halt()
        
        if current_status == 'queued':
            print('Cleaning last job.')
            self._queued_job.cancel()
        
        if current_status == 'concluded':
            print('Cleaning last job.')
        
        self._job = None
        self._queued_job = None
        self.saved_results = {}
        
        print('Queueing new job.')
        self._queued_job = self._quantum_machine.queue.add(self._script())
        # Waits for it to start excecution if queue is empty
        time.sleep(3)
        q_posit = self._queued_job.position_in_queue()
        job_id = self._queued_job.id()
        
        if q_posit == None:
            self._job = self._queued_job.wait_for_execution()
            print('Job in execution. (ID: %s)' % (job_id))
        if type(q_posit).__name__ == 'int':
            print('Job in queue position #%d. (ID: %s)' % (q_posit, job_id))
        
        return
    
    def cancel_job(self):
        """
        TODO
        """
        current_status = self._current_status()
        if current_status == 'not queued':
            print('Job was not queued.')
            return
        
        if current_status == 'in execution':
            self._job.halt()
            self._job = None
            self._queued_job = None
            self.saved_results = {}
            print('Job was interrupted and erased.')
            return
        
        if current_status == 'queued':
            self._queued_job.cancel()
            self._job = None
            self._queued_job = None
            self.saved_results = {}
            print('Queued Job was removed and erased.')
            return
        
        if current_status == 'concluded':
            print('Last job is already complete.')
            return
    
    def status(self):
        """
        TODO
        """
        current_status = self._current_status()
        
        if current_status == 'not queued':
            print('Job was not queued.')
            
        if current_status == 'in execution':
            print('Job is in execution.')
            
        if current_status == 'concluded':
            print('Job has concluded.')
            
        if current_status == 'queued':
            q_posit = self._queued_job.position_in_queue()
            print('Job is queued in position #%d' % q_posit)
        
        return
    
    def _current_status(self):
        """
        TODO
        """
        
        was_queued = True if self._queued_job else False
        
        if not was_queued:
            return 'not queued'
        
        q_posit = self._queued_job.position_in_queue()
        
        if q_posit == None:
            self._job = self._queued_job.wait_for_execution()
            try: 
                # The is_paused() function is a poor workaround to know if the
                # job has concluded, because QM documentation doesn't have any
                # function for this.
                self._job.is_paused()
                return 'in execution'
            except:
                return 'concluded'
        if type(q_posit).__name__ == 'int':
            return 'queued'

    def result_handles(self):
        """
        TODO
        """
        
        current_status = self._current_status()
        
        if current_status == 'not queued':
            print('Job was not queued.')
            return
        
        if current_status == 'queued':
            print('Job still in queue.')
            return
        
        return self._job.result_handles

    def results(self):
        '''
        Returns: [TODO] 
        '''
        
        current_status = self._current_status()
            
        if current_status == 'queued':
            print('Job still in queue.')
            return
            
        if current_status == 'not queued':
            print('Job was not queued.')
            return
        
        res_handles = self.result_handles()
        
        if not res_handles:
            return
        
        results = self.saved_results
        if not results:
            results = {tag:np.array([]) for tag in self._result_tags}
        
        random_result_tag = self._result_tags[0] 
        
        # Counts how many new datapoints to fetch
        prev_count = results[random_result_tag].shape[0]
        new_count = res_handles.get(random_result_tag).count_so_far()
        
        if prev_count == new_count:
            return results

        for tag in self._result_tags:
            new_results = res_handles.get(tag) \
                                     .fetch(slice(prev_count, new_count), 
                                            flat_struct = True) 
            if prev_count - new_count == 1:
                new_results = np.array([new_results])
                # TODO correct this
            if list(results[tag]):
                results[tag] = np.append(results[tag], new_results, 
                                         axis = 0)     
            else:
                results[tag] = new_results
                  
        self.saved_results = results

        if current_status == 'in execution':
            print('Returning partial results of %d ' % new_count + \
                  'iterations (job not concluded).')

        return results



"""
Measurement.
"""
from abc import abstractmethod

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

    @abstractmethod
    def results(self):
        """
        Retrieves the results.
        """
        pass
    
    def queue_job(self):
        """
        TODO
        """
        
        if self.queued_job:
            print('Overwriting last job. ')
        
        self.queued_job = self._quantum_machine.queue.add(self._script())
        q_position = self.queued_job.position_in_queue()
        job_id = self.queued_job.id()
        
        print('Job in queue position #%d (ID: %s)' % (q_position, job_id))
        
        return
    
    def cancel_job(self):
        """
        TODO
        """
        
        if not self.queued_job:
            print('Job was not queued.')
            return
        
        has_canceled = self.queued_job.cancel()
        if has_canceled:
            print('Job was canceled successfully')
        else:
            print('Job is running or has already been completed.')
            
        return
    
    def position_in_queue(self):
        """
        TODO
        """
        
        job_exists = True if self.queued_job else False
        
        if not job_exists:
            print('Job was not queued.')
            return
        
        position = self.queued_job.position_in_queue()
        
        if not position:
            print('The job is not in the queue.')
            return
        else:
            print('Job is in position #%d' % position)
            
        return position
    
    def job_status(self):
        """
        TODO
        """
        
        job_exists = True if self.queued_job else False
        
        if job_exists:
            position = self.queued_job.position_in_queue()
            if not position:
                return 'concluded'
            if position == 1:
                return 'in execution'
            if position > 1:
                return 'queued'
        else:
            return 'inexistent'
        
    def job(self, wait = False, timeout:float = None):
        """
        TODO
        """
        
        if wait:
            return self.queued_job.wait_for_execution(timeout = timeout)
        
        if self.job_status() == 'queued':
            print('Job still in queue. Use wait = True to wait for conclusion')
            return 
        
        if self.job_status() == 'in execution':
            print('Job still in exec. Use wait = True to wait for conclusion')
            return 
        
        if self.job_status() == 'concluded':
            return self.queued_job.wait_for_execution()
        
        if self.job_status() == 'inexistent':
            print('Job was not queued. Use queue_job().')
            return 

    def _result_handles(wait = False, timeout:float = None):
        """
        TODO
        """
        
        job = self.job(wait = wait, timeout = timeout)
        
        if not job:
            return
        
        res_handles = job.result_handles
        res_handles.wait_for_all_values()
        
        return res_handles
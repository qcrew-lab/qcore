import numpy as np
from qm.qua import *

def script(AMP_START, AMP_STOP, AMP_STEP, REPS, WAIT_TIME, rr_amp_scale, 
           pulse = 'saturation'):
    
    AMP_VEC = np.arange(AMP_START, AMP_STOP, AMP_STEP)
    
    with program() as power_Rabi:
        
        n = declare(int)
        a = declare(fixed)
        I = declare(fixed)
        Q = declare(fixed)
        
        I_st = declare_stream()
        Q_st = declare_stream()
        
        with for_(n, 0, n < REPS, n + 1): # do each amp N times
            with for_(a, AMP_START, a <= AMP_STOP, a + AMP_STEP): # sweep amps
            # play('gaussian' * amp(a), 'qubit')
                play(pulse*amp(a), 'qubit')
                align('qubit', 'rr')
                measure('long_readout' * amp(rr_amp_scale), 'rr', None,
                        demod.full('long_integW1', I),
                        demod.full('long_integW2', Q))
                wait(WAIT_TIME, 'rr')
                save(I, I_st)
                save(Q, Q_st)
        
        with stream_processing():
            I_st.buffer(len(AMP_VEC)).average().save('I_mem')
            Q_st.buffer(len(AMP_VEC)).average().save('Q_mem')

    return power_Rabi

def run(qm, AMP_START, AMP_STOP, AMP_STEP, REPS, WAIT_TIME, rr_frequency, 
        pulse = 'saturation'):

    qua_script = script(AMP_START, AMP_STOP, AMP_STEP, REPS, WAIT_TIME, 
                        rr_frequency, pulse = pulse)
    
    queued_job = qm.queue.add(qua_script)
    job = queued_job.wait_for_execution()
    
    res_handles = job.result_handles
    res_handles.wait_for_all_values()
    
    I_handle = res_handles.get('I_mem')
    Q_handle = res_handles.get('Q_mem')
    
    I_list = I_handle.fetch_all()
    Q_list = Q_handle.fetch_all()
    
    return I_list, Q_list
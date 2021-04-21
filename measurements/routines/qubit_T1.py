import numpy as np
from qm.qua import *


def script(TAU_START, TAU_STOP, TAU_STEP, REPS, WAIT_TIME,
           rr_amp_scale, qubit_amp_scale):
    
    TAU_VEC = np.arange(TAU_START, TAU_STOP, TAU_STEP)
    print(rr_amp_scale, qubit_amp_scale)
    with program() as T1_energy_relaxation:
            
        n = declare(int)
        tau = declare(int)
        I = declare(fixed)
        Q = declare(fixed)
        
        I_st = declare_stream()
        Q_st = declare_stream()
                
        with for_(n, 0, n < REPS, n + 1):
            with for_(tau, TAU_START, tau < TAU_STOP, tau + TAU_STEP):
                play('gaussian'*amp(qubit_amp_scale), 'qubit')
                wait(tau, 'qubit')
                align('qubit', 'rr')
                measure('long_readout' * amp(rr_amp_scale), 'rr', None,
                        demod.full('long_integW1', I),
                        demod.full('long_integW2', Q))
                wait(WAIT_TIME, 'qubit', 'rr')
                save(I, I_st)
                save(Q, Q_st)   
        
        with stream_processing():
            I_st.buffer(len(TAU_VEC)).average().save('I_mem')
            Q_st.buffer(len(TAU_VEC)).average().save('Q_mem')
    
    return T1_energy_relaxation

def run(qm, TAU_START, TAU_STOP, TAU_STEP, REPS, WAIT_TIME,
        rr_amp_scale, qubit_amp_scale):
    
    qua_script = script(TAU_START, TAU_STOP, TAU_STEP, REPS, WAIT_TIME,
                        rr_amp_scale, qubit_amp_scale)
    
    queued_job = qm.queue.add(qua_script)
    job = queued_job.wait_for_execution()
    
    res_handles = job.result_handles
    res_handles.wait_for_all_values()
    
    I_handle = res_handles.get('I_mem')
    Q_handle = res_handles.get('Q_mem')
    
    I_list = I_handle.fetch_all()
    Q_list = Q_handle.fetch_all()
    
    return I_list, Q_list
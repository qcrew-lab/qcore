import numpy as np
from qm.qua import *

def script(F_START, F_STOP, F_STEP, REPS, WAIT_TIME,
                   rr_amp_scale, qubit_amp_scale = None):
    
    F_VEC = np.arange(F_START, F_STOP, F_STEP)
    
    if qubit_amp_scale:
        with program() as rr_spec:
            
            n = declare(int)
            f = declare(int)
            I = declare(fixed)
            Q = declare(fixed)
            
            I_st = declare_stream()
            Q_st = declare_stream()
            
            with for_(n, 0, n < REPS, n + 1):
                with for_(f, F_START, f > F_STOP, f + F_STEP):
                    update_frequency("rr", f)
                    play('saturation'*amp(qubit_amp_scale), 'qubit')
                    align('qubit', 'rr')
                    measure("long_readout" * amp(rr_amp_scale), "rr", None, 
                            demod.full('long_integW1', I), 
                            demod.full('long_integW2', Q))
                    wait(WAIT_TIME, "rr")
                    save(I, I_st)
                    save(Q, Q_st)   
            
            with stream_processing():
                I_st.buffer(len(F_VEC)).average().save('I_mem')
                Q_st.buffer(len(F_VEC)).average().save('Q_mem')
    
    else:        
        with program() as rr_spec:
            n = declare(int)
            f = declare(int)
            I = declare(fixed)
            Q = declare(fixed)
            
            I_st = declare_stream()
            Q_st = declare_stream()
            
            
            with for_(n, 0, n < REPS, n + 1):
                with for_(f, F_START, f > F_STOP, f + F_STEP):
                    update_frequency("rr", f)
                    measure("long_readout" * amp(rr_amp_scale), "rr", None,
                            demod.full('long_integW1', I), 
                            demod.full('long_integW2', Q))
                    wait(WAIT_TIME, "rr")
                    save(I, I_st)
                    save(Q, Q_st)   
            
            with stream_processing():
                I_st.buffer(len(F_VEC)).average().save('I_mem')
                Q_st.buffer(len(F_VEC)).average().save('Q_mem')

    return rr_spec

def run(qm, F_START, F_STOP, F_STEP, REPS, WAIT_TIME, rr_amp_scale, 
        qubit_amp_scale = None):
    qua_script = script(F_START, F_STOP, F_STEP, REPS, WAIT_TIME, rr_amp_scale,
                        qubit_amp_scale)
    
    queued_job = qm.queue.add(qua_script)
    job = queued_job.wait_for_execution()
    
    res_handles = job.result_handles
    res_handles.wait_for_all_values()
    
    I_handle = res_handles.get('I_mem')
    Q_handle = res_handles.get('Q_mem')
    
    I_list = I_handle.fetch_all()
    Q_list = Q_handle.fetch_all()
    
    return I_list, Q_list
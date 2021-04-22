import numpy as np
from qm.qua import *

def script(TAU_START, TAU_STOP, TAU_STEP, REPS, WAIT_TIME,
           rr_amp_scale=1, qubit_amp_scale=1, RECOVERY_DELAY = 1000, THRES = 0):
    
    TAU_VEC = np.arange(TAU_START, TAU_STOP, TAU_STEP)
    print("RR Amp Scale:", rr_amp_scale,"Qubit Amp Scale:", qubit_amp_scale)
    
    with program() as T2:
        n = declare(int)
        tau = declare(int)
        state = declare(bool)
        I = declare(fixed)
        Q = declare(fixed)
        
        tau_vec = declare_stream()
        I_res = declare_stream()
        Q_res = declare_stream()
        state_res = declare_stream()

        # T2
        with for_(n, 0, n < REPS, n + 1):
            with for_(tau, TAU_START, tau < TAU_STOP, tau + TAU_STEP):

                play("pi2", "qubit")
                wait(tau, "qubit")
                play("pi2", "qubit")
                align("rr", "qubit")
                measure('long_readout' * amp(rr_amp_scale), 'rr', None,
                        demod.full('long_integW1', I),
                        demod.full('long_integW2', Q))
                save(I, I_res)
                save(Q, Q_res)
                assign(state, I > THRES)
                save(state, state_res)
                save(tau, tau_vec)
                wait(RECOVERY_DELAY // 4, "qubit")

        with stream_processing():
            tau_vec.buffer(len(TAU_VEC)).save("tau_vec")
            I_res.buffer(len(TAU_VEC)).average().save("I_res")
            Q_res.buffer(len(TAU_VEC)).average().save("Q_res")
            state_res.boolean_to_int().buffer(len(TAU_VEC)).average().save("state_res")
    
    return T2

def run(qm, TAU_START, TAU_STOP, TAU_STEP, REPS, WAIT_TIME,
        rr_amp_scale=1, qubit_amp_scale=1, RECOVERY_DELAY = 1000, THRES = 0):
    
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
import numpy as np
from qm.qua import *

def script(T_START, T_STOP, T_STEP, REPS, WAIT_TIME, qubit_amp_scale, rr_amp_scale, pulse = 'gaussian'):
    
    T_VEC = np.arange(T_START, T_STOP, T_STEP)
    
    with program() as timeRabiProg:
        I = declare(fixed)  # QUA variables declaration
        Q = declare(fixed)
        t = declare(int)  # Sweeping parameter over the set of durations
        Nrep = declare(int)  # Number of repetitions of the experiment
        I_stream = declare_stream()  # Declare streams to store I and q components
        Q_stream = declare_stream()
        t_stream = declare_stream()
        
        with for_(Nrep, 0, Nrep< REPS, Nrep + 1): # do each amp N times
            with for_(t, T_START, t <= T_STOP, t + T_STEP): # sweep from 0 to T_STOP in clock cycle unit
                play(pulse *amp(qubit_amp_scale), "qubit", duration=t)
                align("qubit", "rr")
                measure('long_readout' * amp(rr_amp_scale), 'rr', None,
                        demod.full('long_integW1', I),
                        demod.full('long_integW2', Q))
                save(I, I_stream)
                save(Q, Q_stream)
                save(t, t_stream)
                wait(WAIT_TIME, 'rr')
        
        with stream_processing():
            I_stream.buffer(len(T_VEC)).average().save("I")
            Q_stream.buffer(len(T_VEC)).average().save("Q")
            t_stream.buffer(len(T_VEC)).save("t")

    return timeRabiProg

def run(qm, T_START, T_STOP, T_STEP, REPS, WAIT_TIME, qubit_amp_scale,    rr_amp_scale, pulse = 'gaussian'):

    qua_script = script(T_START, T_STOP, T_STEP, REPS, WAIT_TIME, qubit_amp_scale, rr_amp_scale, pulse = pulse)
    
    queued_job = qm.queue.add(qua_script)
    job = queued_job.wait_for_execution()
    
    res_handles = job.result_handles
    res_handles.wait_for_all_values()
    
    I_list = res_handles.get('I').fetch_all()
    Q_list = res_handles.get('Q').fetch_all()
    t_list = res_handles.get('t').fetch_all()
    
    return I_list, Q_list, t_list
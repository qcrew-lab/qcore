# import all objects defined in the __init__.py file in the 'imports' folder
from qcrew.experiments.coax_test.imports import *

reload(cfg), reload(stg)  # reloads modules before executing the code below

# NOTE: make changes to lo, if, tof, mixer offsets in 'configuration.py'
# NOTE: make changes to constant pulse amp and pulse duration in the qua script below

MEAS_NAME = "power_rabi"  # used for naming the saved data file

########################################################################################
########################           MEASUREMENT SEQUENCE         ########################
########################################################################################

reps = 100
a_start = -0.1
a_stop = 0.1
a_step = 0.005
a_vec = np.arange(a_start, a_stop, a_step)
a_vec_len = len(a_vec)
wait_time = 1000  # int, in multiples of 4 ns

with program() as power_rabi:
    n = declare(int)
    a = declare(fixed)
    a_stream = declare_stream()

    I = declare(fixed)
    I_stream = declare_stream()
    Q = declare(fixed)
    Q_stream = declare_stream()

    with for_(n, 0, n < reps, n + 1):
        with for_(a, a_start, a < a_stop, a + a_step):
            play("gaussian" * amp(a), "qubit")  # TODO: remove hard-coded pulse
            align("qubit", "rr")  # TODO: remove hard-coded element name
            measure("readout", "rr", None, ("integW1", I), ("integW2", Q))
            wait(wait_time, "rr")
            save(I, I_stream)
            save(Q, Q_stream)
            save(a, a_stream)

    with stream_processing():
        I_stream.buffer(a_vec_len).save_all("I_mem")
        Q_stream.buffer(a_vec_len).save_all("Q_mem")
        a_stream.buffer(a_vec_len).save_all("a_mem")

########################################################################################
############################           GET RESULTS         #############################
########################################################################################

job = stg.qm.execute(power_rabi)
job_result = job.result_handles

# please see "qm_get_results.py" in "analysis" package in "codebase" for an attempt
# to get partial results from QM

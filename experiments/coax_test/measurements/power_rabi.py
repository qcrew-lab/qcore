# import all objects defined in the __init__.py file in the 'imports' folder
from qcrew.experiments.coax_test.imports import *

# NOTE: make changes to lo, if, tof, mixer offsets in 'configuration.py'
# NOTE: make changes to constant pulse amp and pulse duration in the qua script below

MEAS_NAME = "power_rabi"  # used for naming the saved data file

########################################################################################
########################           MEASUREMENT SEQUENCE         ########################
########################################################################################

reps = 10
a_start = 0.0
a_stop = None
a_step = 0.01
a_vec = np.arange(a_start, a_stop, a_step)
wait_time = None

with program() as power_rabi:
    n = declare(int)
    a = declare(fixed)

    I = declare(fixed)
    I_stream = declare_stream()
    Q = declare(fixed)
    Q_stream = declare_stream()

    with for_(n, 0, n < reps, n + 1):
        with for_(a, a_start, a < a_stop, a + a_step):
            play("gaussian" * amp(a), "qubit")
            align("qubit", "rr")
            measure("readout", "rr", None, ("integW1", I), ("integW2", Q))
            wait(wait_time, "rr")
            save(I, I_stream)
            save(Q, Q_stream)

    with stream_processing():
        I_stream.buffer(len(a_vec)).save_all('I_mem')
        Q_stream.buffer(len(a_vec)).save_all('Q_mem')

# we are saving all data in qua loop
# so, we need to do the averaging outside the loop

# QM Results API
# start a loop (while SOMETHING)
# wait_for_values (say, 100 iterations)
# fetch
# average
# save in results container (contains both raw and averaged results, later, this becomes datasaver)
# send to plotter

# now, we save both raw and average

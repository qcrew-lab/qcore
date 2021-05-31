import numpy as np
from qm.qua import *
from qm import generate_qua_script


sourceFile = open("debug.py", "w")

reps = 5000
f_start = -100e6
f_stop = -20e6
f_step = 0.02e6
f_vec = np.arange(f_start, f_stop, f_step)
f_vec_int = [int(x) for x in f_vec]
wait_time = 8000
amp_scale = 1.0
with program() as debug_prog:
    n = declare(int)
    f = declare(int)

    I = declare(fixed)
    I_stream = declare_stream()
    Q = declare(fixed)
    Q_stream = declare_stream()

    with for_(n, 0, n < reps, n + 1):  # outer averaging loop
        # with for_(f, f_start, f < f_stop, f + f_step):  # doesn't cause issue
        with for_each_(f, f_vec_int):  # causes insufficient data memory
            update_frequency("rr", f)
            measure(
                "readout" * amp(amp_scale),
                "rr",
                None,
                demod.full("integW1", I),
                demod.full("integW2", Q),
            )
            wait(wait_time, "rr")
            save(I, I_stream)
            save(Q, Q_stream)

    with stream_processing():
        I_stream.buffer(len(f_vec)).average().save("I_mem")
        Q_stream.buffer(len(f_vec)).average().save("Q_mem")


print(generate_qua_script(debug_prog, , file=sourceFile))
sourceFile.close()

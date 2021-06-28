""" Minimum working example for investigating the inconsistency between numpy.arange() and qm.qua.for_() for certain sweep range settings while sweeping amplitudes in a QUA loop with amp() """
import numpy as np
from qm.qua import (
    amp,
    declare,
    declare_stream,
    fixed,
    for_,
    play,
    program,
    save,
    stream_processing,
)
from qm.QuantumMachinesManager import QuantumMachinesManager

from qcrew.experiments.coax_test.measurements.unfinished.bad_amp_sweep.configuration import config

# sweep range settings for a, our sweep variable
start = -0.1
stop = 0.1
step = 0.02  # NOTE use step = 0.02 to reproduce the inconsistency in sweep points!

a_guess = np.arange(start, stop, step)  # what I believe the amp sweep points to be

with program() as bad_amp_sweep:

    n = declare(int)  # averaging loop variable
    a = declare(fixed)  # sweep variable
    a_st = declare_stream()  # to save the actual amps swept by the OPX

    with for_(a, start, a < stop, a + step):
        play("CW" * amp(a), "qubit")
        save(a, a_st)

    with stream_processing():
        a_st.save_all("a")  # to obtain raw values - what the OPX actually sweeps

qmm = QuantumMachinesManager()
qm = qmm.open_qm(config)
job = qm.execute(bad_amp_sweep)
handle = job.result_handles
handle.wait_for_all_values()

# find out what points are actually swept by OPX
a_actual = handle.a.fetch_all(flat_struct=True)

# find out what QM thinks was swept
a_qm_guess = handle.a.stream_metadata.iteration_values[0].iteration_values

# compare length and contents of a_guess and a_actual and log them
print(f"Sweep setting: {start = }, {stop = }, {step = }")
print(f"Number of points I want to sweep: {len(a_guess)}")
print(f"Actual number of points swept by OPX: {len(a_actual)}")
print(f"Number of points QM thinks were swept: {len(a_qm_guess)}")
print(f"Points swept: {a_actual}")
print(f"Points I want to sweep: {a_guess}")
print(f"Points QM thinks were swept: {a_qm_guess}")

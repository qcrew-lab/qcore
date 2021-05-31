# import all objects defined in the __init__.py file in the 'imports' folder
from qcrew.experiments.coax_test.imports import *

# NOTE: make changes to lo, if, tof, mixer offsets in 'configuration.py'
# NOTE: make changes to constant pulse amp and pulse duration in the qua script below

MEAS_NAME = "rr_spec"  # used for naming the saved data file

########################################################################################
########################           MEASUREMENT SEQUENCE         ########################
########################################################################################

reps = 5000
f_start = -100e6
f_stop = -20e6
f_step = 0.02e6
f_vec = np.arange(f_start, f_stop, f_step)
f_vec_int = [int(x) for x in f_vec]
wait_time = 8000
amp_scale = 1.0
with program() as rr_spec:
    n = declare(int)
    f = declare(int)

    I = declare(fixed)
    I_stream = declare_stream()
    Q = declare(fixed)
    Q_stream = declare_stream()

    with for_(n, 0, n < reps, n + 1):  # outer averaging loop
        # with for_(f, f_start, f < f_stop, f + f_step):  # inner frequency sweep
        with for_each_(f, f_vec_int):  # causes insufficient data memory
            update_frequency("rr", f)
            measure(
                "readout" * amp(amp_scale),
                "rr",
                None,
                demod.full("integW1", I),
                demod.full("integW2", Q),
            )
            wait(wait_time, "rr")  # for rr to relax to vacuum state
            save(I, I_stream)
            save(Q, Q_stream)

    with stream_processing():
        I_stream.buffer(len(f_vec)).average().save("I_mem")
        Q_stream.buffer(len(f_vec)).average().save("Q_mem")

########################################################################################
############################           GET RESULTS         #############################
########################################################################################

job = qm.execute(rr_spec)
result_handle = job.result_handles
result_handle.wait_for_all_values()
I_handle = result_handle.get("I_mem")
Q_handle = result_handle.get("Q_mem")
results = np.abs(I_handle.fetch_all() + 1j * Q_handle.fetch_all())
plt.plot(f_vec, results)

########################################################################################
############################           SAVE RESULTS         ############################
########################################################################################

metadata = (
    f"{reps = }, {f_start = }, {f_stop = }, {f_step = }, {wait_time = }, {amp_scale = }"
)
filename = f"{datetime.now().strftime('%H-%M-%S')}_{MEAS_NAME}"
datapath = DATA_FOLDER_PATH / (filename + ".csv")
imgpath = DATA_FOLDER_PATH / (filename + ".png")

with datapath.open("w") as f:
    f.write(metadata)
    np.savetxt(datapath, [f_vec, results], delimiter=",")
plt.savefig(imgpath)

########################################################################################
########################################################################################
########################################################################################
plt.show()  # this blocks execution, and is hence run at the end of the script

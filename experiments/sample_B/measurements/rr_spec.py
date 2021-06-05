# import all objects defined in the __init__.py file in the 'imports' folder
from qcrew.experiments.sample_B.imports import *

reload(cfg), reload(stg)  # reloads modules before executing the code below

# NOTE: make changes to lo, if, tof, mixer offsets in 'configuration.py'
# NOTE: make changes to constant pulse amp and pulse duration in the qua script below

MEAS_NAME = "rr_spec"  # used for naming the saved data file

########################################################################################
########################           MEASUREMENT SEQUENCE         ########################
########################################################################################

# Loop parameters
reps = 20000
wait_time = 5000  # in clock cycles

# Measurement pulse
rr = stg.rr
f_start = -52e6
f_stop = -45e6
f_step = 0.01e6
rr_f_list = np.arange(f_start, f_stop, f_step)
rr_ascale = 0.03
rr_op = 'readout'
integW1 = "integW1"  # integration weight for I
integW2 = "integW2"  # integration weight for Q
# NOTE: The weights must be defined for the chosen measurement operation

with program() as rr_spec:
    n = declare(int)
    f = declare(int)

    I = declare(fixed)
    I_stream = declare_stream()
    Q = declare(fixed)
    Q_stream = declare_stream()

    with for_(n, 0, n < reps, n + 1):  # outer averaging loop
        with for_(f, f_start, f < f_stop, f + f_step):  # inner frequency sweep
            update_frequency(rr.name, f)
            measure(
                rr_op * amp(rr_ascale),
                rr.name,
                None,
                demod.full(integW1, I),
                demod.full(integW2, Q),
            )
            wait(wait_time, rr.name)  # for rr to relax to vacuum state
            save(I, I_stream)
            save(Q, Q_stream)

    with stream_processing():
        I_stream.buffer(len(rr_f_list)).average().save("I_mem")
        Q_stream.buffer(len(rr_f_list)).average().save("Q_mem")

########################################################################################
############################           GET RESULTS         #############################
########################################################################################

job = stg.qm.execute(rr_spec)
result_handle = job.result_handles
result_handle.wait_for_all_values()
I_handle = result_handle.get("I_mem")
Q_handle = result_handle.get("Q_mem")
results = np.abs(I_handle.fetch_all() + 1j * Q_handle.fetch_all())
plt.figure(figsize=(10, 8))
plt.plot(rr_f_list, results)

# from scipy.signal import find_peaks
# peaks, _ = find_peaks(results, height = 1.75e-5)
# print("peak is at", rr_f_list[peaks])
# print("peak is at", results[peaks])
########################################################################################
############################           SAVE RESULTS         ############################
########################################################################################

metadata = (
    f"{reps = }, {f_start = }, {f_stop = }, {f_step = }, {wait_time = }, {rr_ascale = }"
)
filename = f"{datetime.now().strftime('%H-%M-%S')}_{MEAS_NAME}"
datapath = DATA_FOLDER_PATH / (filename + ".csv")
imgpath = DATA_FOLDER_PATH / (filename + ".png")

with datapath.open("w") as f:
    f.write(metadata)
    np.savetxt(datapath, [rr_f_list, results], delimiter=",")
plt.savefig(imgpath)

########################################################################################
########################################################################################
########################################################################################
plt.show()  # this blocks execution, and is hence run at the end of the script

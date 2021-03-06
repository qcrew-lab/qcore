# import all objects defined in the __init__.py file in the 'imports' folder
from qcrew.experiments.sample_B.imports import *

reload(cfg), reload(stg)  # reloads modules before executing the code below

# NOTE: make changes to lo, if, tof, mixer offsets in 'configuration.py'
# NOTE: make changes to constant pulse amp and pulse duration in the qua script below

MEAS_NAME = "rr_spectroscopy_low_power_sweep"  # used for naming the saved data file

########################################################################################
########################           MEASUREMENT SEQUENCE         ########################
########################################################################################

# Required parameters
reps = 20000
f_start = -51e6
f_stop = -48.5e6
f_step = 0.01e6
rr_f_list = np.arange(f_start, f_stop, f_step)
wait_time = 10000  # in clock cycles
rr_ascale = np.array([0.01, 0.02, 0.03, 0.04])


# Parameters for optional qubit pulse
play_qubit = False
qubit_ascale = 0.0
qubit_f = -50e6  # IF frequency of qubit pulse
qubit_op = "gaussian"  # qubit operation as defined in config

# Rearranges the input parameters in arrays over which QUA can
# iterate. The arrays are given in the order of outer to inner
# loop.
parameter_list = [
    (x.flatten()) for x in np.meshgrid(qubit_ascale, rr_ascale, indexing="ij")
]

# Defines buffer size for averaging
buffer_lengths = [
    1 if type(x).__name__ in {"int", "float"} else len(x)
    for x in [qubit_ascale, rr_ascale, rr_f_list]
]

with program() as rr_spec:
    # Iteration variable
    n = declare(int)

    # Spectroscopy parameters
    qubit_a = declare(fixed)
    rr_a = declare(fixed)
    rr_f = declare(int)

    # Arrays for sweeping
    qubit_a_vec = declare(fixed, value=parameter_list[0])
    rr_a_vec = declare(fixed, value=parameter_list[1])
    # rr_f_vec = declare(int, value=[int(x) for x in parameter_list[2]])  # freq is int

    # Outputs
    I = declare(fixed)
    Q = declare(fixed)

    # Streams
    I_st = declare_stream()
    Q_st = declare_stream()

    # Averaging loop
    with for_(n, 0, n < reps, n + 1):
        # Qubit and resonator pulse amplitude scaling loop
        with for_each_((qubit_a, rr_a), (qubit_a_vec, rr_a_vec)):
            # Frequency sweep
            with for_(rr_f, f_start, rr_f < f_stop, rr_f + f_step):
                update_frequency("rr", rr_f)
                play(qubit_op * amp(qubit_a), "qubit", condition=play_qubit)
                align("qubit", "rr")
                measure(
                    "readout" * amp(rr_a),
                    "rr",
                    None,
                    demod.full("integW1", I),
                    demod.full("integW2", Q),
                )
                wait(wait_time, "rr")
                save(I, I_st)
                save(Q, Q_st)

    with stream_processing():
        I_st.buffer(*buffer_lengths).average().save("I_mem")
        Q_st.buffer(*buffer_lengths).average().save("Q_mem")

########################################################################################
############################           GET RESULTS         #############################
########################################################################################

job = stg.qm.execute(rr_spec)
result_handle = job.result_handles
result_handle.wait_for_all_values()

fig = plt.figure(figsize=(10, 8))
for index, rr_amplitude in enumerate(rr_ascale):
    I_list = result_handle.get("I_mem").fetch_all()[0, index]
    Q_list = result_handle.get("Q_mem").fetch_all()[0, index]
    results = np.abs(I_list + 1j * Q_list)
    plt.plot(rr_f_list, results, label="r_a = {}".format((rr_amplitude)))
plt.legend()
plt.show()

# I_list = result_handle.get("I_mem").fetch_all()[0, 0]
# Q_list = result_handle.get("Q_mem").fetch_all()[0, 0]
# results = np.abs(I_list + 1j * Q_list)
# from scipy.signal import find_peaks
# peaks, _ = find_peaks(results, height = 0.5e-5)
# print("peak is at", rr_f_list[peaks])
# print("peak is at", results[peaks])
#######################################################################################
############################           SAVE RESULTS         ############################
########################################################################################

metadata = f"{reps = }, {wait_time = }, {rr_ascale = }, {play_qubit = }"
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

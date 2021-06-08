# import all objects defined in the __init__.py file in the 'imports' folder
from qcrew.experiments.coax_test.imports import *

reload(cfg), reload(stg)  # reloads modules before executing the code below

# NOTE: make changes to lo, if, tof, mixer offsets in 'configuration.py'
# NOTE: make changes to constant pulse amp and pulse duration in the qua script below

MEAS_NAME = "rr_spec_sweep_amp"  # used for naming the saved data file

########################################################################################
########################           MEASUREMENT SEQUENCE         ########################
########################################################################################

reps = 20000
wait_time = 12500  # in clock cycles, found after rough T1

# readout parameters
f_start, f_stop, f_step = -53e6, -47e6, 0.02e6
rr_f_list = np.arange(f_start, f_stop, f_step)
a_start, a_stop, num_a = 0.01, 2.0, 60
rr_ascale = np.linspace(a_start, a_stop, num_a)  # for sweeping measurement power

# Parameters for optional qubit pulse
play_qubit = True
qubit_ascale = 1.13  # found after a power rabi fit
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

with program() as rr_spec_sweep_amp:
    # Iteration variable
    n = declare(int)

    # Spectroscopy parameters
    qubit_a = declare(fixed)
    rr_a = declare(fixed)
    rr_f = declare(int)

    # Arrays for sweeping
    qubit_a_vec = declare(fixed, value=parameter_list[0])
    rr_a_vec = declare(fixed, value=parameter_list[1])

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

job = stg.qm.execute(rr_spec_sweep_amp)
result_handle = job.result_handles
result_handle.wait_for_all_values()

all_results = dict()  # added to save all results

fig = plt.figure(figsize=(10, 8))
for index, rr_amp in enumerate(rr_ascale):
    I_list = result_handle.get("I_mem").fetch_all()[0, index]
    Q_list = result_handle.get("Q_mem").fetch_all()[0, index]
    results = np.abs(I_list + 1j * Q_list)
    all_results[rr_amp] = results
    #plt.plot(rr_f_list, results, label="r_a = {}".format((rr_amp)))
#plt.legend()
#plt.show()

#######################################################################################
############################           SAVE RESULTS         ############################
########################################################################################

metadata = f"{reps = }, {wait_time = }, {rr_ascale = }, {play_qubit = }, {qubit_ascale = }, {qubit_op = }"
filename = f"{datetime.now().strftime('%H-%M-%S')}_{MEAS_NAME}"
datapath = DATA_FOLDER_PATH / (filename + ".csv")
imgpath = DATA_FOLDER_PATH / (filename + ".png")

with datapath.open("w") as f:
    f.write(metadata)
    f.write("\n")
    f.write("rr_f_list\n")
    np.savetxt(f, rr_f_list, delimiter=",")
    for rr_amp, result in all_results.items():
        f.write(f"{rr_amp = }\n")
        np.savetxt(f, result, delimiter=",")
#plt.savefig(imgpath)

########################################################################################
########################################################################################
########################################################################################
# plt.show()

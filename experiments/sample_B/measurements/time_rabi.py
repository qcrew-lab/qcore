# import all objects defined in the __init__.py file in the 'imports' folder
from qcrew.experiments.sample_B.imports import *
from scipy.signal import find_peaks
from scipy.optimize import curve_fit

reload(cfg), reload(stg)  # reloads modules before executing the code below

# NOTE: make changes to lo, if, tof, mixer offsets in 'configuration.py'
# NOTE: make changes to constant pulse amp and pulse duration in the qua script below

MEAS_NAME = "time_rabi"  # used for naming the saved data file

########################################################################################
########################           MEASUREMENT SEQUENCE         ########################
########################################################################################

# Loop parameters
reps = 8000
wait_time = 20000  # in clock cycles

# Measurement pulse
update_rr_if = True
rr = stg.rr
rr_if = rr.int_freq
rr_ascale = 0.0195
rr_op = "readout"
integW1 = "integW1"  # integration weight for I
integW2 = "integW2"  # integration weight for Q
# NOTE: The weights must be defined for the chosen measurement operation

# wait time between two pluse
t_start = 0
t_stop = 800
t_step = 1  # in clock cycle
t_list = np.arange(t_start, t_stop, t_step)

qubit_ascale = 1.0
qubit = stg.qubit
qubit_f = qubit.int_freq  # IF frequency of qubit pulse
qubit_op = "gaussian"  # qubit operation as defined in config

# Rearranges the input parameters in arrays over which QUA can
# iterate. The arrays are given in the order of outer to inner
# loop.
# parameter_list = [
#     (x.flatten()) for x in np.meshgrid(qubit_ascale, rr_ascale, indexing="ij")
# ]

# # Defines buffer size for averaging
# buffer_lengths = [
#     1 if type(x).__name__ in {"int", "float"} else len(x)
#     for x in [qubit_ascale, rr_ascale, rr_f_list]
# ]

with program() as time_rabi:
    # Iteration variable
    n = declare(int)
    qubit_a = declare(fixed, value=qubit_ascale)
    rr_a = declare(fixed, value=rr_ascale)

    update_rr_if = declare(bool, value=update_rr_if)

    # sweep variable
    t = declare(int)

    # Outputs
    I = declare(fixed)
    Q = declare(fixed)

    # Streams
    I_st = declare_stream()
    Q_st = declare_stream()
    I_st_avg = declare_stream()
    Q_st_avg = declare_stream()

    with if_(update_rr_if):
        rr_freq = declare(int, value=rr_if)
        update_frequency("rr", rr_freq)

    # Averaging loop
    with for_(n, 0, n < reps, n + 1):  # outer averaging loop
        with for_(t, t_start, t < t_stop, t + t_step):  # inner frequency sweep

            play(qubit_op * amp(qubit_a), "qubit", duration=t)

            align("qubit", "rr")
            measure(
                rr_op * amp(rr_a),
                "rr",
                None,
                demod.full(integW1, I),
                demod.full(integW2, Q),
            )

            wait(wait_time, "qubit")
            save(I, I_st)
            save(Q, Q_st)

    with stream_processing():
        I_st_avg.buffer(len(t_list)).average().save_all("I_avg")
        Q_st_avg.buffer(len(t_list)).average().save_all("Q_avg")
        I_st.buffer(len(t_list)).average().save("I_mem")
        Q_st.buffer(len(t_list)).average().save("Q_mem")


########################################################################################
############################           GET RESULTS         #############################
########################################################################################

job = stg.qm.execute(time_rabi)
result_handle = job.result_handles
result_handle.wait_for_all_values()

I_handle = result_handle.get("I_mem")
Q_handle = result_handle.get("Q_mem")
results = np.abs(I_handle.fetch_all() + 1j * Q_handle.fetch_all())

plt.plot(t_list, results)
plt.show()


########################################################################################
############################           SAVE RESULTS         ############################
########################################################################################


metadata = f"{reps = }, {t_start = }, {t_stop = }, {t_step = }, {wait_time = }, \
    {rr_ascale = }, {qubit_ascale = }, { qubit_op= }"
filename = f"{datetime.now().strftime('%H-%M-%S')}_{MEAS_NAME}"
datapath = DATA_FOLDER_PATH / (filename + ".csv")
imgpath = DATA_FOLDER_PATH / (filename + ".png")


with datapath.open("w") as f:
    f.write(metadata)
    np.savetxt(datapath, [t_list, results], delimiter=",")
plt.savefig(imgpath)

########################################################################################
########################################################################################
########################################################################################
plt.show()  # this blocks execution, and is hence run at the end of the script

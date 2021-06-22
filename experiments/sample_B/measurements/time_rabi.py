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
reps = 20000
wait_time = 75000  # in clock cycles

# Measurement pulse
update_rr_if = True

rr = stg.rr
rr_if = rr.int_freq
rr_ascale = 0.0175
rr_op = "readout"
integW1 = "integW1"  # integration weight for I
integW2 = "integW2"  # integration weight for Q
# NOTE: The weights must be defined for the chosen measurement operation

# wait time between two pluse
t_start = 4
t_stop = 400
t_step = 4  # in clock cycle
t_list = np.arange(t_start, t_stop, t_step)

qubit_ascale = 2
qubit = stg.qubit
qubit_f = qubit.int_freq  # IF frequency of qubit pulse
qubit_op = "pi"  # qubit operation as defined in config

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

            save(I, I_st_avg)
            save(Q, Q_st_avg)
            save(I, I_st)
            save(Q, Q_st)

    with stream_processing():
        I_st_avg.buffer(len(t_list)).average().save_all("I_avg")
        Q_st_avg.buffer(len(t_list)).average().save_all("Q_avg")
        I_st.buffer(len(t_list)).save_all("I")
        Q_st.buffer(len(t_list)).save_all("Q")


########################################################################################
############################           GET RESULTS         #############################
########################################################################################


job = stg.qm.execute(time_rabi)

fig = plt.figure()
ax = fig.add_subplot(1, 1, 1)
hdisplay = display.display("", display_id=True)
raw_data = {}
result_handles = job.result_handles
N = 100  # Maximum size of data batch for each refresh
remaining_data = reps
while remaining_data != 0:
    # clear data
    ax.clear()

    # update data
    N = min(N, remaining_data)  # don't wait for more than there's left
    raw_data = update_results(raw_data, N, result_handles, ["I_avg", "Q_avg", "I", "Q"])
    I_avg = raw_data["I_avg"][-1]
    Q_avg = raw_data["Q_avg"][-1]
    amps = np.abs(I_avg + 1j * Q_avg)

    I = raw_data["I"]
    Q = raw_data["Q"]
    d = np.abs(I + 1j * Q)
    std_err = np.std(d, axis=0) / np.sqrt(d.shape[0])
    remaining_data -= N

    # plot averaged data
    #ax.plot(t_list, amps)

    # plot fitted curve
    #params = plot_fit(t_list, amps, ax, yerr=std_err, fit_func="sine")
    ax.errorbar(t_list, amps, yerr=std_err, fmt='o')
    params = plot_fit(t_list, amps, ax, fit_func="sine")
    ax.set_title("average of %d results" % (reps - remaining_data))
    # update figure
    hdisplay.update(fig)


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
    np.savetxt(datapath, [t_list, amps], delimiter=",")
plt.savefig(imgpath)

########################################################################################
########################################################################################
########################################################################################
plt.show()  # this blocks execution, and is hence run at the end of the script

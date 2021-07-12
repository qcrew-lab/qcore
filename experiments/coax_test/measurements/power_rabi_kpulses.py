# import all objects defined in the __init__.py file in the 'imports' folder
from qcrew.experiments.coax_test.imports import *

reload(cfg), reload(stg)  # reloads modules before executing the code below

# NOTE: make changes to lo, if, tof, mixer offsets in 'configuration.py'
# NOTE: make changes to constant pulse amp and pulse duration in the qua script below

MEAS_NAME = "power_rabi_kpulses"  # used for naming the saved data file

########################################################################################
########################           MEASUREMENT SEQUENCE         ########################
########################################################################################
# hello HI
# Loop parameters
reps = 10000
wait_time = 12500  # in clock cycles

# Qubit pulse (this will play k times)
qubit = stg.qubit
a_start = -1.00
a_stop = 1.00
a_step = 0.05
qubit_a_list = np.arange(a_start, a_stop, a_step)
qubit_f = qubit.int_freq
qubit_op = "pi_drag"  # qubit operation as defined in config
k = 2  # Number of times the pulse will repeat

# Measurement pulse
rr = stg.rr
rr_f = rr.int_freq
rr_ascale = 0.2
rr_op = "readout"
integW1 = "integW1"  # integration weight for I
integW2 = "integW2"  # integration weight for Q
# NOTE: The weights must be defined in configuration.py for the chosen msmt operation


with program() as power_rabi:
    n = declare(int)
    a = declare(fixed)
    K = declare(int, value=0)

    I = declare(fixed)
    Q = declare(fixed)
    I_st = declare_stream()
    Q_st = declare_stream()
    I_st_avg = declare_stream()
    Q_st_avg = declare_stream()

    update_frequency(rr.name, rr_f)
    update_frequency(qubit.name, qubit_f)

    with for_(n, 0, n < reps, n + 1):
        with for_(a, a_start, a < a_stop, a + a_step):
            with while_(K < k):
                play(qubit_op * amp(a), qubit.name)
                assign(K, K + 1)
            assign(K, 0)
            align(qubit.name, rr.name)
            measure(
                rr_op * amp(rr_ascale),
                rr.name,
                None,
                demod.full(integW1, I),
                demod.full(integW2, Q),
            )
            wait(wait_time, rr.name)
            save(I, I_st_avg)
            save(Q, Q_st_avg)
            save(I, I_st)
            save(Q, Q_st)

    with stream_processing():
        I_st_avg.buffer(len(qubit_a_list)).average().save_all("I_avg")
        Q_st_avg.buffer(len(qubit_a_list)).average().save_all("Q_avg")
        I_st.buffer(len(qubit_a_list)).save_all("I")
        Q_st.buffer(len(qubit_a_list)).save_all("Q")

########################################################################################
############################           GET RESULTS         #############################
########################################################################################

job = stg.qm.execute(power_rabi)

fig = plt.figure()
ax = fig.add_subplot(1, 1, 1)
hdisplay = display.display("", display_id=True)
raw_data = {}
result_handles = job.result_handles
N = 500  # Maximum size of data batch for each refresh
remaining_data = reps
while remaining_data != 0:
    # clear data from plot
    ax.clear()

    # update data
    N = min(N, remaining_data)  # don't wait for more than there's left
    raw_data = update_results(raw_data, N, result_handles, ["I", "Q"])
    I = raw_data["I"]
    Q = raw_data["Q"]
    I_avg = np.average(I, axis=0)
    Q_avg = np.average(Q, axis=0)

    # process data
    amps = np.abs(I + 1j * Q)
    amps_avg = np.abs(I_avg + 1j * Q_avg)  # Must average before taking the amp
    std_err = np.std(amps, axis=0) / np.sqrt(amps.shape[0])
    remaining_data -= N

    # plot fitted curve with errorbars
    params = plot_fit(qubit_a_list, amps_avg, ax, yerr=std_err, fit_func="sine")

    # customize figure
    ax.set_title("average of %d results" % (reps - remaining_data))
    ax.legend(loc="upper left", bbox_to_anchor=(0, -0.1))  # Relocate legend box

    # update figure
    hdisplay.update(fig)

# please see "qm_get_results.py" in "analysis" package in "codebase" for an attempt
# to get partial results from QM

########################################################################################
############################           SAVE RESULTS         ############################
########################################################################################

metadata = f"{reps = }, {a_start = }, {a_stop = }, {a_step = }, {wait_time = }, \
      {qubit_f = }, {qubit_op = }, {rr_f = }, {rr_ascale = }, {rr_op = }"
filename = f"{datetime.now().strftime('%H-%M-%S')}_{MEAS_NAME}"
datapath = DATA_FOLDER_PATH / (filename + ".csv")
imgpath = DATA_FOLDER_PATH / (filename + ".png")
print(datapath)
print(imgpath)
with datapath.open("w") as f:
    f.write(metadata)
    np.savetxt(datapath, [qubit_a_list, amps_avg], delimiter=",")

plt.savefig(imgpath)

########################################################################################
########################################################################################
########################################################################################

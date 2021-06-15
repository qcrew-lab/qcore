# import all objects defined in the __init__.py file in the 'imports' folder
from qcrew.experiments.sample_B.imports import *


reload(cfg), reload(stg)  # reloads modules before executing the code below

# NOTE: make changes to lo, if, tof, mixer offsets in 'configuration.py'
# NOTE: make changes to constant pulse amp and pulse duration in the qua script below

MEAS_NAME = "power_rabi"  # used for naming the saved data file

########################################################################################
########################           MEASUREMENT SEQUENCE         ########################
########################################################################################

# Loop parameters
reps = 20000
wait_time = 75000  # in clock cycles

# Qubit pulse
qubit = stg.qubit
a_start = -2
a_stop = 2
a_step = 0.02
qubit_a_list = np.arange(a_start, a_stop, a_step)
qubit_f = qubit.int_freq
qubit_op = "CW"  # qubit operation as defined in config

# Measurement pulse
rr = stg.rr
rr_f = rr.int_freq
rr_ascale = 0.0195
rr_op = "readout"
integW1 = "integW1"  # integration weight for I
integW2 = "integW2"  # integration weight for Q
# NOTE: The weights must be defined in configuration.py for the chosen msmt operation


with program() as power_rabi:
    n = declare(int)
    a = declare(fixed)

    I = declare(fixed)
    Q = declare(fixed)
    I_st = declare_stream()
    Q_st = declare_stream()
    I_st_avg = declare_stream()
    Q_st_avg = declare_stream()

    # update_frequency(rr.name, rr_f)
    # update_frequency(qubit.name, qubit_f)

    with for_(n, 0, n < reps, n + 1):
        with for_(a, a_start, a < a_stop, a + a_step):
            update_frequency(qubit.name, qubit_f)  # just a test, will remove later
            play(qubit_op * amp(a), qubit.name)
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
N = 100  # Maximum size of data batch for each refresh
remaining_data = reps
while remaining_data != 0:
    # clear data
    ax.clear()

    # update data
    N = min(N, remaining_data)  # don't wait for more than there's left
    raw_data = update_results(raw_data, N, result_handles, ["I_avg", "Q_avg",'I','Q'])
    I_avg = raw_data["I_avg"][-1]
    Q_avg = raw_data["Q_avg"][-1]
    amps = np.abs(I_avg + 1j * Q_avg)

    I = raw_data["I"]
    Q = raw_data["Q"]
    d = np.abs(I + 1j * Q)
    std_err = np.std(d, axis=0) / np.sqrt(d.shape[0])
    remaining_data -= N

    # plot averaged data
    ax.plot(qubit_a_list, amps, ls="None", marker="s")

    # plot fitted curve
    params = plot_fit(qubit_a_list, amps, ax, yerr=std_err, fit_func="sine")
    ax.set_title("average of %d results" % (reps - remaining_data))
    # ax.legend(['pi-amp scaling = '% (0.5/params['f0'])])

    # update figure
    hdisplay.update(fig)

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
    np.savetxt(datapath, [qubit_a_list, amps], delimiter=",")

plt.savefig(imgpath)

########################################################################################
########################################################################################
########################################################################################

# import all objects defined in the __init__.py file in the 'imports' folder
from qcrew.experiments.coax_test.imports import *

reload(cfg), reload(stg)  # reloads modules before executing the code below

# NOTE: make changes to lo, if, tof, mixer offsets in 'configuration.py'
# NOTE: make changes to constant pulse amp and pulse duration in the qua script below

MEAS_NAME = "t1"  # used for naming the saved data file

########################################################################################
########################           MEASUREMENT SEQUENCE         ########################
########################################################################################

# Loop parameters
reps = 400000
wait_time = 12500  # in multiples of 4ns

# Measurement pulse
rr = stg.rr
rr_f = rr.int_freq
rr_ascale = 0.2
rr_op = "readout"
integW1 = "integW1"  # integration weight for I
integW2 = "integW2"  # integration weight for Q
# NOTE: The weights must be defined in configuration.py for the chosen msmt operation

# Wait time between two pulses in clock cycles
t_start = 4  # must be integer >= 4, this is in multiples of 4 ns.
t_stop = 1200
t_step = 12
t_list = np.arange(t_start, t_stop, t_step)

# Qubit pulse
qubit = stg.qubit
qubit_ascale = 1.0  # based on power rabi fit
qubit_f = qubit.int_freq  # IF of qubit pulse
qubit_op = "pi"  # qubit operation as defined in config

with program() as t1:
    # Iteration variable
    n = declare(int)

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

    update_frequency(rr.name, rr_f)

    # Averaging loop
    with for_(n, 0, n < reps, n + 1):  # outer averaging loop
        with for_(t, t_start, t < t_stop, t + t_step):  # inner wait time loop

            play(qubit_op * amp(qubit_ascale), qubit.name)
            wait(t, qubit.name)
            align(qubit.name, rr.name)
            measure(
                rr_op * amp(rr_ascale),
                rr.name,
                None,
                demod.full(integW1, I),
                demod.full(integW2, Q),
            )
            wait(wait_time, qubit.name, rr.name)

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

job = stg.qm.execute(t1)

fig = plt.figure()
ax = fig.add_subplot(1, 1, 1)
hdisplay = display.display("", display_id=True)
raw_data = {}
result_handles = job.result_handles
N = 500  # Maximum size of data batch for each refresh
remaining_data = reps
while remaining_data != 0:
    # clear data
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
    params = plot_fit(t_list, amps_avg, ax, yerr=std_err, fit_func="exp_decay")

    # customize figure
    ax.set_title("average of %d results" % (reps - remaining_data))
    ax.legend(loc="upper left", bbox_to_anchor=(0, -0.1))  # Relocate legend box

    # update figure
    hdisplay.update(fig)


########################################################################################
############################           SAVE RESULTS         ############################
########################################################################################

metadata = f"{reps = }, {qubit_ascale = }, {t_start = }, {t_stop = }, {t_step = }, {wait_time = }, {rr_ascale = }"

filename = f"{datetime.now().strftime('%H-%M-%S')}_{MEAS_NAME}"
datapath = DATA_FOLDER_PATH / (filename + ".csv")
imgpath = DATA_FOLDER_PATH / (filename + ".png")

with datapath.open("w") as f:
    f.write(metadata)
    np.savetxt(datapath, [t_list, amps_avg], delimiter=",")
plt.savefig(imgpath)

########################################################################################
########################################################################################
########################################################################################

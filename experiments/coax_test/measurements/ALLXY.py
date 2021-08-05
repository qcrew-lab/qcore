# import all objects defined in the __init__.py file in the 'imports' folder
from qcrew.experiments.coax_test.imports import *

reload(cfg), reload(stg)  # reloads modules before executing the code below

# NOTE: make changes to lo, if, tof, mixer offsets in 'configuration.py'
# NOTE: make changes to constant pulse amp and pulse duration in the qua script below

MEAS_NAME = "allxy"  # used for naming the saved data file

########################################################################################
########################           MEASUREMENT SEQUENCE         ########################
########################################################################################

# Loop parameters
reps = 2000000
wait_time = 15000  # in clock cycles

# Qubit pulse
qubit = stg.qubit
qubit_pi_op = "gaussian"  # qubit pi operation as defined in config.
qubit_f = 190e6  # qubit.int_freq

# Measurement pulse
rr = stg.rr
rr_f = rr.int_freq
rr_ascale = 0.2
rr_op = "readout"
integW1, integW2 = "integW1", "integW2"  # integration weight for I
# NOTE: The weights must be defined in configuration.py for the chosen msmt operation

gate_list = np.array(
    [
        [0.0, 0, 0.0, 0, "IdId"],  # IdId
        [1.0, 0, 1.0, 0, "XpXp"],  # XpXp
        [1.0, 0.25, 1.0, 0.25, "YpYp"],  # YpYp
        [1.0, 0, 1.0, 0.25, "XpYp"],  # XpYp
        [1.0, 0.25, 1.0, 0, "YpXp"],  # YpXp
        [0.5, 0, 0.0, 0, "X9Id"],  # X9Id
        [0.5, 0.25, 0.0, 0, "Y9Id"],  # Y9Id
        [0.5, 0, 0.5, 0.25, "X9Y9"],  # X9Y9
        [0.5, 0.25, 0.5, 0, "Y9X9"],  # Y9X9
        [0.5, 0, 1.0, 0.25, "X9Yp"],  # X9Yp
        [0.5, 0.25, 1.0, 0, "Y9Xp"],  # Y9Xp
        [1.0, 0, 0.5, 0.25, "XpY9"],  # XpY9
        [1.0, 0.25, 0.5, 0, "YpX9"],  # YpX9
        [0.5, 0, 1.0, 0, "X9Xp"],  # X9Xp
        [1.0, 0, 0.5, 0, "XpX9"],  # XpX9
        [0.5, 0.25, 1.0, 0.25, "Y9Yp"],  # Y9Yp
        [1.0, 0.25, 0.5, 0.25, "YpY9"],  # YpY9
        [1.0, 0, 0.0, 0, "XpId"],  # XpId
        [1.0, 0.25, 0.0, 0, "YpId"],  # YpId
        [0.5, 0, 0.5, 0, "X9X9"],  # X9X9
        [0.5, 0.25, 0.5, 0.25, "Y9Y9"],  # Y9Y9
    ]
)

# Repeat each gate twice
# gate_list = np.repeat(gate_list, 2, axis=0)
gate_number = gate_list.shape[0]

# Separate into arrays over which to loop
fg_amp_array = [float(x) for x in gate_list.T[0]]
fg_angle_array = [float(x) for x in gate_list.T[1]]
sg_amp_array = [float(x) for x in gate_list.T[2]]
sg_angle_array = [float(x) for x in gate_list.T[3]]
gate_name_list = list(gate_list.T[4])

with program() as power_rabi:
    n = declare(int)

    # Variables indicating which gate to be applied
    fg_amp = declare(float)
    fg_angle = declare(float)
    sg_amp = declare(float)
    sg_angle = declare(float)

    # gate selection arrays
    fg_amp_array = declare(float, value=fg_amp_array)
    fg_angle_array = declare(float, value=fg_angle_array)
    sg_amp_array = declare(float, value=sg_amp_array)
    sg_angle_array = declare(float, value=sg_angle_array)

    I = declare(fixed)
    Q = declare(fixed)
    I_st = declare_stream()
    Q_st = declare_stream()
    I_st_avg = declare_stream()
    Q_st_avg = declare_stream()

    update_frequency(rr.name, rr_f)
    update_frequency(qubit.name, qubit_f)

    with for_(n, 0, n < reps, n + 1):

        # Loop over ALLXY gate sequence
        with for_each_(
            (fg_amp, fg_angle, sg_amp, sg_angle),
            (fg_amp_array, fg_angle_array, sg_amp_array, sg_angle_array),
        ):

            reset_frame(qubit.name)
            align(qubit.name, rr.name)

            # First pulse
            frame_rotation_2pi(fg_angle, qubit.name)
            play(qubit_pi_op * amp(fg_amp), qubit.name)

            # Second pulse
            frame_rotation_2pi(-fg_angle + sg_angle, qubit.name)
            play(qubit_pi_op * amp(sg_amp), qubit.name)
            frame_rotation_2pi(-sg_angle, qubit.name)

            # Measurement pulse
            align(qubit.name, rr.name)
            measure(
                rr_op * amp(rr_ascale),
                rr.name,
                None,
                demod.full(integW1, I),
                demod.full(integW2, Q),
            )
            wait(wait_time, rr.name, qubit.name)
            save(I, I_st_avg)
            save(Q, Q_st_avg)
            save(I, I_st)
            save(Q, Q_st)

    with stream_processing():
        I_st_avg.buffer(gate_number).average().save_all("I_avg")
        Q_st_avg.buffer(gate_number).average().save_all("Q_avg")
        I_st.buffer(gate_number).save_all("I")
        Q_st.buffer(gate_number).save_all("Q")


########################################################################################
############################           GET RESULTS         #############################
########################################################################################

job = stg.qm.execute(power_rabi)

fig = plt.figure()
ax = fig.add_subplot(1, 1, 1)
hdisplay = display.display("", display_id=True)
raw_data = {}
result_handles = job.result_handles
N = 1000  # Maximum size of data batch for each refresh
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

    # plot data with errorbars
    x_axis = list(range(gate_number))
    ax.errorbar(
        x_axis,
        amps_avg,
        yerr=std_err,
        marker="o",
        ls="none",
        markersize=6,
        color="b",
        label="average error = {:.3e}".format(np.average(std_err)),
    )

    # customize figure
    ax.set_title("average of %d results" % (reps - remaining_data))
    ax.legend(loc="upper left", bbox_to_anchor=(0, -0.15))  # Relocate legend box
    ax.set_xticks(x_axis)
    ax.set_xticklabels(gate_name_list)
    ax.tick_params(axis="x", labelrotation=45)

    # update figure
    hdisplay.update(fig)

# please see "qm_get_results.py" in "analysis" package in "codebase" for an attempt
# to get partial results from QM

########################################################################################
############################           SAVE RESULTS         ############################
########################################################################################

metadata = f"{reps = }, {wait_time = }, {qubit_pi_op = },\
      {qubit_f = }, {rr_f = }, {rr_ascale = }, {rr_op = }"
filename = f"{datetime.now().strftime('%H-%M-%S')}_{MEAS_NAME}"
datapath = DATA_FOLDER_PATH / (filename + ".csv")
imgpath = DATA_FOLDER_PATH / (filename + ".png")
print(datapath)
print(imgpath)
with datapath.open("w") as f:
    f.write(metadata)
    np.savetxt(datapath, amps_avg, delimiter=",")

plt.savefig(imgpath)

########################################################################################
########################################################################################
########################################################################################

# import all objects defined in the __init__.py file in the 'imports' folder
from qcrew.experiments.coax_test.imports import *

reload(cfg), reload(stg)  # reloads modules before executing the code below

# NOTE: make changes to lo, if, tof, mixer offsets in 'configuration.py'
# NOTE: make changes to constant pulse amp and pulse duration in the qua script below

MEAS_NAME = "allxy"  # used for naming the saved data file

########################################################################################
########################           MEASUREMENT SEQUENCE         ########################
########################################################################################
# hello
# Loop parameters
reps = 100000
wait_time = 12500  # in clock cycles

# Qubit pulse
qubit = stg.qubit
qubit_pi_op = "pi"  # qubit pi operation as defined in config.
qubit_pi2_op = "pi2"  # qubit pi/2 operation as defined in config
qubit_f = qubit.int_freq

# Measurement pulse
rr = stg.rr
rr_f = rr.int_freq
rr_ascale = 0.2
rr_op = "readout"
integW1, integW2 = "integW1", "integW2"  # integration weight for I
# NOTE: The weights must be defined in configuration.py for the chosen msmt operation

gate_list = np.array(
    [
        [0, 0],  # IdId
        [1, 1],  # XpXp
        [3, 3],  # YpYp
        [1, 3],  # XpYp
        [3, 1],  # YpXp
        [2, 0],  # X9Id
        [4, 0],  # Y9Id
        [2, 4],  # X9Y9
        [4, 2],  # Y9X9
        [2, 3],  # X9Yp
        [4, 1],  # Y9Xp
        [1, 4],  # XpY9
        [3, 2],  # YpX9
        [2, 1],  # X9Xp
        [1, 2],  # XpX9
        [4, 3],  # Y9Yp
        [3, 4],  # YpY9
        [1, 0],  # XpId
        [3, 0],  # YpId
        [2, 2],  # X9X9
        [4, 4],  # Y9Y9
    ]
)

gate_number = gate_list.shape[0]
first_gate_array = [int(x) for x in gate_list.T[0]]
second_gate_array = [int(x) for x in gate_list.T[1]]

with program() as power_rabi:
    n = declare(int)

    # Int variables indicating which gate to be applied
    first_gate = declare(int)
    second_gate = declare(int)
    play_pi = declare(bool)
    play_pi2 = declare(bool)

    # gate selection arrays
    first_gate_array = declare(int, value=first_gate_array)
    second_gate_array = declare(int, value=second_gate_array)

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
            (first_gate, second_gate), (first_gate_array, second_gate_array)
        ):

            ## First gate
            with if_(first_gate > 2):
                # Rotate frame to apply Y gate
                frame_rotation_2pi(0.25, qubit.name)  # Virtual frame rotation

            assign(play_pi, (first_gate == 1) or (first_gate == 3))
            assign(play_pi2, (first_gate == 2) or (first_gate == 4))
            with if_(first_gate > 0):
                # Play either pi or pi/2 pulse. Else, don't play anything
                play(qubit_pi_op, qubit.name, condition=play_pi)  # pi
                play(qubit_pi2_op, qubit.name, condition=play_pi2)  # pi/2

            reset_frame(qubit.name)  # Reverts the virtual frame rotation

            ## Second gate
            with if_(second_gate > 2):
                # Rotate frame to apply Y gate
                frame_rotation_2pi(0.25, qubit.name)  # Virtual frame rotation

            play_pi = (second_gate == 1) or (second_gate == 3)
            play_pi2 = (second_gate == 2) or (second_gate == 4)
            with if_(second_gate > 0):
                # Play either pi or pi/2 pulse. Else, don't play anything
                play(qubit_pi_op, qubit.name, condition=play_pi)  # pi
                play(qubit_pi2_op, qubit.name, condition=play_pi2)  # pi/2

            reset_frame(qubit.name)  # Reverts the virtual frame rotation

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
N = 200  # Maximum size of data batch for each refresh
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
        marker="s",
        ls="none",
        markersize=3,
        color="b",
        label="average error = {:.3e}".format(np.average(std_err)),
    )

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

metadata = f"{reps = }, {wait_time = }, {qubit_pi_op = }, {qubit_pi2_op = }\
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

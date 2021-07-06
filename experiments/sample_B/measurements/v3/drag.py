# based on ALLXY.py
from qcrew.experiments.sample_B.imports import *

reload(cfg)
reload(stg)

MEAS_NAME = "drag"  # used for naming the saved data file

########################################################################################
########################           MEASUREMENT SEQUENCE         ########################
########################################################################################

# Loop parameters
reps = 1000000
wait_time = 75000  # in clock cycles

# Qubit pulse
qubit = stg.qubit
qubit_pi_op = "pi_drag"  # same as pi pulse, but with gaussian derivative q wf

# drag coefficient beta scaling sweep range
b_start = 0.15
b_stop = 0.4
b_step = 0.01
b_list = np.arange(b_start, b_stop, b_step)

# I plan to buffer by sweep, each sweep point has 2 outputs (one  from each pulse seq)
buffer_len = 2 * len(b_list)
# we will separate the values corresponding to each pulse seq in post-processing

# Measurement pulse
rr = stg.rr
rr_f = rr.int_freq

qubit = stg.qubit
qubit_f = qubit.int_freq

rr_ascale = 0.0175
rr_op = "readout"
integW1 = "integW1"  # integration weight for I
integW2 = "integW2"  # integration weight for Q
# NOTE: The weights must be defined in configuration.py for the chosen msmt operation

gate_list = np.array(
    [
        [1.0, 0.25, 0.5, 0, "YpX9"],  # YpX9
        [1.0, 0, 0.5, 0.25, "XpY9"],  # XpY9
    ]
)
gate_number = gate_list.shape[0]

# Separate into arrays over which to loop
fg_amp_array = [float(x) for x in gate_list.T[0]]
fg_angle_array = [float(x) for x in gate_list.T[1]]
sg_amp_array = [float(x) for x in gate_list.T[2]]
sg_angle_array = [float(x) for x in gate_list.T[3]]
gate_name_list = list(gate_list.T[4])

with program() as drag:
    n = declare(int)
    b = declare(fixed)  # drag coefficient beta

    # Variables indicating which gate to be applied
    fg_amp = declare(fixed)
    fg_angle = declare(fixed)
    sg_amp = declare(fixed)
    sg_angle = declare(fixed)

    # gate selection arrays
    fg_amp_array = declare(fixed, value=fg_amp_array)
    fg_angle_array = declare(fixed, value=fg_angle_array)
    sg_amp_array = declare(fixed, value=sg_amp_array)
    sg_angle_array = declare(fixed, value=sg_angle_array)

    I = declare(fixed)
    Q = declare(fixed)
    I_st = declare_stream()
    Q_st = declare_stream()

    update_frequency(rr.name, rr_f)
    # update_frequency(qubit.name, qubit_f)

    with for_(n, 0, n < reps, n + 1):
        with for_(b, b_start, b < b_stop - b_step / 2, b + b_step):  # sweep beta
            # Loop over chosen ALLXY gate sequences
            with for_each_(
                (fg_amp, fg_angle, sg_amp, sg_angle),
                (fg_amp_array, fg_angle_array, sg_amp_array, sg_angle_array),
            ):

                reset_frame(qubit.name)
                align(qubit.name, rr.name)

                # First pulse
                frame_rotation_2pi(fg_angle, qubit.name)
                play(qubit_pi_op * amp(fg_amp, 0.0, 0.0, b*fg_amp), qubit.name)

                # Second pulse
                frame_rotation_2pi(-fg_angle + sg_angle, qubit.name)
                play(qubit_pi_op * amp(sg_amp, 0.0, 0.0,  b*sg_amp), qubit.name)
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
                save(I, I_st)
                save(Q, Q_st)

    with stream_processing():
        I_st.buffer(buffer_len).average().save_all("I_avg")
        Q_st.buffer(buffer_len).average().save_all("Q_avg")
        I_st.buffer(buffer_len).save_all("I")
        Q_st.buffer(buffer_len).save_all("Q")

########################################################################################
############################           GET RESULTS         #############################
########################################################################################

job = stg.qm.execute(drag)

fig = plt.figure(figsize=(12, 12))
ax = fig.add_subplot(1, 1, 1)
hdisplay = display.display("", display_id=True)
raw_data = {}
result_handles = job.result_handles
N = 2000  # Maximum size of data batch for each refresh
remaining_data = reps
while remaining_data != 0:
    # clear data from plot
    ax.clear()

    # update data
    N = min(N, remaining_data)  # don't wait for more than there's left
    raw_data = update_results(raw_data, N, result_handles, ["I", "Q"])
    I = raw_data["I"]
    Q = raw_data["Q"]

    YpX9_I = I[:, ::2]  # group all even column indices
    XpY9_I = I[:, 1::2]  # group all odd column indices
    YpX9_Q = Q[:, ::2]
    XpY9_Q = Q[:, 1::2]

    YpX9_I_avg = np.average(YpX9_I, axis=0)
    XpY9_I_avg = np.average(XpY9_I, axis=0)
    YpX9_Q_avg = np.average(YpX9_Q, axis=0)
    XpY9_Q_avg = np.average(XpY9_Q, axis=0)

    YpX9_amps = np.abs(YpX9_I + 1j * YpX9_Q)
    YpX9_std_err = np.std(YpX9_amps, axis=0) / np.sqrt(YpX9_amps.shape[0])
    YpX9_amps_avg = np.abs(YpX9_I_avg + 1j * YpX9_Q_avg)

    XpY9_amps = np.abs(XpY9_I + 1j * XpY9_Q)
    XpY9_std_err = np.std(XpY9_amps, axis=0) / np.sqrt(XpY9_amps.shape[0])
    XpY9_amps_avg = np.abs(XpY9_I_avg + 1j * XpY9_Q_avg)

    remaining_data -= N

    # plot data with errorbars
    ax.errorbar(  # Plot YpX9
        b_list,
        YpX9_amps_avg,
        yerr=YpX9_std_err,
        marker="o",
        fillstyle="none",
        ls="none",
        markersize=6,
        color="blue",
        label="YpX9",
    )

    ax.errorbar(  # Plot XpY9
        b_list,
        XpY9_amps_avg,
        yerr=XpY9_std_err,
        marker="o",
        fillstyle="none",
        ls="none",
        markersize=6,
        color="red",
        label="XpY9",
    )

    # do fit and plot fit
    YpX9_fit_params = fit.do_fit("linear", b_list, YpX9_amps_avg)
    YpX9_fit = fit.eval_fit("linear", YpX9_fit_params, b_list)
    ax.plot(b_list, YpX9_fit, color="blue", lw=2, label="YpX9_fit")

    XpY9_fit_params = fit.do_fit("linear", b_list, XpY9_amps_avg)
    XpY9_fit = fit.eval_fit("linear", XpY9_fit_params, b_list)
    ax.plot(b_list, XpY9_fit, color="red", lw=2, label="XpY9_fit")

    # customize figure
    ax.set_title(f"DRAG: {reps - remaining_data} reps")
    ax.set_xlabel("Drag coefficient")
    ax.set_ylabel("Signal amplitude")
    ax.legend()

    # update figure
    hdisplay.update(fig)

########################################################################################
############################           SAVE RESULTS         ############################
########################################################################################

print(job.execution_report())

metadata = f"{reps = }, {wait_time = }, {b_start = }, {b_stop = }, {b_step = }, {qubit_pi_op = }, {qubit_f = }, {rr_f = }, {rr_ascale = }, {rr_op = }"
filename = f"{datetime.now().strftime('%H-%M-%S')}_{MEAS_NAME}"
datapath = DATA_FOLDER_PATH / (filename + ".csv")
imgpath = DATA_FOLDER_PATH / (filename + ".png")
print(datapath)
print(imgpath)
with datapath.open("w") as f:
    f.write(metadata)
    f.write("\n YpX9 \n")
    np.savetxt(datapath, YpX9_amps_avg, delimiter=",")
    f.write("\n XpY9 \n")
    np.savetxt(datapath, XpY9_amps_avg, delimiter=",")

plt.savefig(imgpath)

########################################################################################
########################################################################################
########################################################################################

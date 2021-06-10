# import all objects defined in the __init__.py file in the 'imports' folder
from qcrew.experiments.coax_test.imports import *

reload(cfg), reload(stg)  # reloads modules before executing the code below

# NOTE: make changes to lo, if, tof, mixer offsets in 'configuration.py'
# NOTE: make changes to constant pulse amp and pulse duration in the qua script below

MEAS_NAME = "rr_spec"  # used for naming the saved data file

########################################################################################
########################           MEASUREMENT SEQUENCE         ########################
########################################################################################

# Loop parameters
reps = 10000
wait_time = 12500  # in clock cycles

# Measurement pulse
rr = stg.rr
f_start = -54e6
f_stop = -48e6
f_step = 0.02e6
rr_f_list = np.arange(f_start, f_stop, f_step)
rr_f_list_len = len(rr_f_list)
rr_ascale = 0.2
rr_op = "readout"
integW1 = "integW1"  # integration weight for I
integW2 = "integW2"  # integration weight for Q
# NOTE: The weights must be defined in configuration.py for the chosen msmt operation

with program() as rr_spec:
    n = declare(int)

    rr_f = declare(int)
    f_st = declare_stream()

    I = declare(fixed)
    Q = declare(fixed)

    I_st = declare_stream()
    Q_st = declare_stream()

    with for_(n, 0, n < reps, n + 1):  # outer averaging loop
        with for_(rr_f, f_start, rr_f < f_stop, rr_f + f_step):  # inner frequency sweep
            update_frequency(rr.name, rr_f)
            measure(
                rr_op * amp(rr_ascale),
                rr.name,
                None,
                demod.full(integW1, I),
                demod.full(integW2, Q),
            )
            wait(wait_time, rr.name)  # for rr to relax to vacuum state
            save(I, I_st)
            save(Q, Q_st)
            save(rr_f, f_st)

    with stream_processing():
        f_st.buffer(rr_f_list_len).average().save("f")
        I_st.buffer(rr_f_list_len).save_all("I")
        Q_st.buffer(rr_f_list_len).save_all("Q")

        I_st.buffer(rr_f_list_len).average().save_all("I_avg")
        Q_st.buffer(rr_f_list_len).average().save_all("Q_avg")
        I_st.buffer(rr_f_list_len).average().save("I_avg_single")
        Q_st.buffer(rr_f_list_len).average().save("Q_avg_single")

# run measurement
job = stg.qm.execute(rr_spec)

########################################################################################
########################           GET AND PLOT RESULTS         ########################
########################################################################################

# QM data fetching preparation
result_handles = job.result_handles

# partial result fetching and "fake" live plotting routine
flp = FakeLivePlotter()
while result_handles.is_processing():  # while measurement is still running
    rr_f_list = result_handles.f.fetch_all(flat_struct=True)
    cum_avg_I = result_handles.I_avg_single.fetch_all(flat_struct=True)
    cum_avg_Q = result_handles.Q_avg_single.fetch_all(flat_struct=True)
    amps = np.abs(cum_avg_I + 1j * cum_avg_Q)
    flp.plot(rr_f_list, amps, fit_func="lorentzian")

# get raw data
raw_I = result_handles.I.fetch_all(flat_struct=True)
raw_Q = result_handles.Q.fetch_all(flat_struct=True)

########################################################################################
############################           SAVE RESULTS         ############################
########################################################################################

metadata = f"{reps = }, {f_start = }, {f_stop = }, {f_step = }, {wait_time = }, {rr_ascale = }\n"
filename = f"{datetime.now().strftime('%H-%M-%S')}_{MEAS_NAME}"

datapath = DATA_FOLDER_PATH / (filename + ".csv")
imgpath = DATA_FOLDER_PATH / (filename + ".png")

with datapath.open("w") as f:
    f.write(metadata)
    f.write("AVG f, amps\n")
    np.savetxt(f, [rr_f_list, amps], delimiter=",")
    f.write("\nRAW\n")
    for i in range(reps):
        f.write(f"\nREP {i} I, Q\n")
        np.savetxt(f, [raw_I[i], raw_Q[i]], delimiter=",")

plt.savefig(imgpath)
print("DONE!!!")

########################################################################################
########################################################################################
########################################################################################

"""fig = plt.figure()
ax = fig.add_subplot(1, 1, 1)
hdisplay = display.display("", display_id=True)
raw_data = {}
remaining_data = reps

while remaining_data != 0:
    # clear data
    ax.clear()

    # update data
    batch_size = min(batch_size, remaining_data)  # don't wait for more than there's left
    raw_data = update_results(
        raw_data, batch_size, result_handles, ["I_avg", "Q_avg"]
    )
    I_avg = np.average(raw_data["I_avg"], axis=0)
    Q_avg = np.average(raw_data["Q_avg"], axis=0)
    amps = np.abs(I_avg + 1j * Q_avg)

    remaining_data -= batch_size

    # plot averaged data
    ax.plot(rr_f_list, amps)

    # plot fitted curve
    params = plot_fit(rr_f_list, amps, ax, fit_func="lorentzian")
    ax.set_title("average of %d results" % (reps - remaining_data))

    # update figure
    hdisplay.update(fig)
    
"""

from qcrew.experiments.coax_test.imports import *  #  import all objects from init file

reload(cfg)  # reload config before running the script
reload(stg)  # reload stage before running the script

MEAS_NAME = "rr_spec"  # used for naming the saved data file

########################################################################################
########################           MEASUREMENT SEQUENCE         ########################
########################################################################################
rr = stg.rr  # reference to the readout mode object

reps = 40000  # number of sweep repetitions

# sweep parameters
wait_time = 12500  # in clock cycles, for readout mode to relax before next repetition
f_start, f_stop, f_step = -55e6, -45e6, 0.02e6
rr_f_list = np.arange(f_start, f_stop, f_step)
rr_f_list_len = len(rr_f_list)

rr_ascale = 0.2
rr_op = "readout"
integW1, integW2 = "integW1", "integW2"  # integration weight for I and Q respectively

with program() as rr_spec:
    n = declare(int)

    rr_f = declare(int)
    f_st = declare_stream()

    I = declare(fixed)
    Q = declare(fixed)

    I_st = declare_stream()
    Q_st = declare_stream()
    I_st_avg = declare_stream()
    Q_st_avg = declare_stream()

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
            save(I, I_st_avg)
            save(Q, Q_st_avg)
            save(I, I_st)
            save(Q, Q_st)
            save(rr_f, f_st)

    with stream_processing():
        I_st_avg.buffer(len(rr_f_list)).average().save_all("I_avg")
        Q_st_avg.buffer(len(rr_f_list)).average().save_all("Q_avg")
        f_st.buffer(len(rr_f_list)).average().save_all("f")
        I_st.buffer(len(rr_f_list)).save_all("I")
        Q_st.buffer(len(rr_f_list)).save_all("Q")

########################################################################################
############################           GET RESULTS         #############################
########################################################################################

job = stg.qm.execute(rr_spec)

fig = plt.figure()
ax = fig.add_subplot(1, 1, 1)
hdisplay = display.display("", display_id=True)
raw_data = {}
result_handles = job.result_handles
N = 100  # max size of data batch for each refresh, must be integer > 1
remaining_data = reps
while remaining_data != 0:
    # clear data
    ax.clear()

    # update data
    N = min(N, remaining_data)  # don't wait for more than there's left
    raw_data = update_results(raw_data, N, result_handles, ["I_avg", "Q_avg", "f"])
    I_avg = raw_data["I_avg"][-1]
    Q_avg = raw_data["Q_avg"][-1]
    amps = np.abs(I_avg + 1j * Q_avg)

    rr_f = np.average(
        raw_data["f"], axis=0
    )  # just to make sure the I and Q measured is for the rr_f stored on the OPX
    remaining_data -= N

    # plot averaged data
    ax.plot(rr_f, amps)

    # plot fitted curve
    params = plot_fit(rr_f_list, amps, ax, fit_func="lorentzian")
    ax.set_title("average of %d results" % (reps - remaining_data))

    # update figure
    hdisplay.update(fig)

########################################################################################
############################           SAVE RESULTS         ############################
########################################################################################

metadata = f"{reps = }, {f_start = }, {f_stop = }, {f_step = }, {wait_time = }, {rr_ascale = }\n"
filename = f"{datetime.now().strftime('%H-%M-%S')}_{MEAS_NAME}"
datapath = DATA_FOLDER_PATH / (filename + ".csv")
imgpath = DATA_FOLDER_PATH / (filename + ".png")

with datapath.open("w") as f:
    f.write(metadata)
    np.savetxt(datapath, [rr_f_list, amps], delimiter=",")
plt.savefig(imgpath)

########################################################################################
########################################################################################
########################################################################################

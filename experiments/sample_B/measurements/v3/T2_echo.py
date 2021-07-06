# import all objects defined in the __init__.py file in the 'imports' folder
from qcrew.experiments.sample_B.imports import *

reload(cfg), reload(stg)  # reloads modules before executing the code below

# NOTE: make changes to lo, if, tof, mixer offsets in 'configuration.py'
# NOTE: make changes to constant pulse amp and pulse duration in the qua script below

MEAS_NAME = "t2_echo"  # used for naming the saved data file

########################################################################################
########################           MEASUREMENT SEQUENCE         ########################
########################################################################################

# Loop parameters
reps = 100000
wait_time = 75000  # in multiples of 4ns

# Measurement pulse
rr = stg.rr
rr_f = rr.int_freq
rr_ascale = 0.0175
rr_op = "readout"
integW1 = "integW1"  # integration weight for I
integW2 = "integW2"  # integration weight for Q
# NOTE: The weights must be defined in configuration.py for the chosen msmt operation

# Wait time between two pulses in clock cycles
t_start = 4  # in ns 
t_stop = 800
t_step = 20
t_list = np.arange(t_start, t_stop, t_step)


# Qubit pulse
detuning = 0.0e6  # 0.7e6  # 700e3  # 0.05e6  # Qubit drive detuning
qubit = stg.qubit
qubit_ascale = 2  # -1.1 / 2
qubit_f = qubit.int_freq - detuning  # IF of qubit pulse
qubit_op_pi2 = "sqpi2"  # pi/2 qubit operation as defined in config
qubit_op_pi = "sqpi" 
# qubit_op = "pi2" 

with program() as t2:
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
    update_frequency(qubit.name, qubit_f)

    # Averaging loop
    with for_(n, 0, n < reps, n + 1):  # outer averaging loop
        with for_(t, t_start, t < t_stop, t + t_step):  # inner frequency sweep

            play(qubit_op_pi2, qubit.name)
            wait(t, qubit.name) #Yvonne added the /2, check if you understand why. 

            play(qubit_op_pi, qubit.name)
            wait(t, qubit.name)
            
            play(qubit_op_pi2, qubit.name)

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
        I_st_avg.buffer(len(t_list)).average().save_all("I_avg")
        Q_st_avg.buffer(len(t_list)).average().save_all("Q_avg")
        I_st.buffer(len(t_list)).save_all("I")
        Q_st.buffer(len(t_list)).save_all("Q")


########################################################################################
############################           GET RESULTS         #############################
########################################################################################

job = stg.qm.execute(t2)

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
    # ax.scatter(t_list, amps, s=4)

    # plot fitted curve
    params = plot_fit(t_list, amps, ax, yerr=std_err, fit_func="exp_decay_sine")
    ax.set_title("average of %d results" % (reps - remaining_data))

    # update figure
    hdisplay.update(fig)

########################################################################################
############################           SAVE RESULTS         ############################
########################################################################################

metadata = f"{reps = }, {qubit_ascale = }, {t_start = }, {t_stop = }, {t_step = }, {wait_time = }, {rr_ascale = }, {detuning = }"

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

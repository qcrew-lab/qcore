# import all objects defined in the __init__.py file in the 'imports' folder
from qcrew.experiments.sample_B.imports import *

reload(cfg), reload(stg)  # reloads modules before executing the code below

# NOTE: make changes to lo, if, tof, mixer offsets in 'configuration.py'
# NOTE: make changes to constant pulse amp and pulse duration in the qua script below

MEAS_NAME = "qubit_spec_live"  # used for naming the saved data file
from qcrew.codebase.instruments import MetaInstrument, QuantumElement, Sa124

########################################################################################
########################           MEASUREMENT SEQUENCE         ########################
########################################################################################

# Loop parameters
reps = 15000
wait_time = 80000  # in clock cycles

# Qubit pulse
qubit = stg.qubit
f_start = -190e6
f_stop = -159e6
f_step = 0.05e6
qubit_f_list = np.arange(f_start, f_stop, f_step)

qubit_ascale = 2
qubit_op = "CW"  # qubit operation as defined in config

qubit_pi_f = 75.95e6
qubit_pi = "pi"

# Measurement pulse
rr = stg.rr
rr_f = rr.int_freq
rr_ascale = 0.0175
rr_op = "readout"
integW1 = "integW1"  # integration weight for I
integW2 = "integW2"  # integration weight for Q
# NOTE: The weights must be defined in configuration.py for the chosen msmt operation

with program() as qubit_spec:
    # Iteration variable
    n = declare(int)

    # Spectroscopy loop variable
    qu_f = declare(int)

    # Outputs
    I = declare(fixed)
    Q = declare(fixed)

    # Streams
    I_st = declare_stream()
    Q_st = declare_stream()
    I_st_avg = declare_stream()
    Q_st_avg = declare_stream()

    update_frequency(rr.name, rr_f)

    with for_(n, 0, n < reps, n + 1):
        with for_(qu_f, f_start, qu_f < f_stop, qu_f + f_step):

            ## pi pulse: to excite qubit from g to e
            update_frequency(qubit.name, qubit_pi_f)
            play(qubit_pi, qubit.name)

            ## CW pulse: 
            update_frequency(qubit.name, qu_f)
            play(qubit_op * amp(qubit_ascale), qubit.name)


            ## pi pulse: to release qubit from e to g
            update_frequency(qubit.name, qubit_pi_f)
            play(qubit_pi, qubit.name)

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
        I_st_avg.buffer(len(qubit_f_list)).average().save_all("I_avg")
        Q_st_avg.buffer(len(qubit_f_list)).average().save_all("Q_avg")
        I_st.buffer(len(qubit_f_list)).save_all("I")
        Q_st.buffer(len(qubit_f_list)).save_all("Q")

########################################################################################
############################           GET RESULTS         #############################
########################################################################################

job = stg.qm.execute(qubit_spec)


fig = plt.figure(figsize=(20, 5))
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
    raw_data = update_results(raw_data, N, result_handles, ["I_avg", "Q_avg"])
    I_avg = raw_data["I_avg"][-1]
    Q_avg = raw_data["Q_avg"][-1]
    amps = np.abs(I_avg + 1j * Q_avg)
    remaining_data -= N

    # plot averaged data
    ax.scatter(qubit_f_list / 1e6, amps)

    # plot fitted curve
    params = plot_fit(qubit_f_list/1e6, amps, ax, fit_func='lorentzian')
    ax.set_title("average of %d results" % (reps - remaining_data))

    # update figure
    hdisplay.update(fig)

I = result_handles.get("I_avg").fetch_all(flat_struct=True)[-1]
Q = result_handles.get("Q_avg").fetch_all(flat_struct=True)[-1]
result = np.abs(I + 1j * Q)

plt.figure(figsize=(15, 5))
plt.plot(qubit_f_list, result)
plt.show()
########################################################################################
############################           SAVE RESULTS         ############################
########################################################################################

metadata = f"{reps = }, {f_start = }, {f_stop = }, {f_step = }, {wait_time = }, \
      {qubit_ascale = }, {qubit_op = }, {rr_f = }, {rr_ascale = }, {rr_op = }"
filename = f"{datetime.now().strftime('%H-%M-%S')}_{MEAS_NAME}"
datapath = DATA_FOLDER_PATH / (filename + ".csv")
imgpath = DATA_FOLDER_PATH / (filename + ".png")

with datapath.open("w") as f:
    f.write(metadata)
    np.savetxt(datapath, [qubit_f_list, amps], delimiter=",")
plt.savefig(imgpath)

########################################################################################
########################################################################################
########################################################################################

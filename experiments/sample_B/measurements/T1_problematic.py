# import all objects defined in the __init__.py file in the 'imports' folder
from qcrew.experiments.sample_B.imports import *
from scipy.signal import find_peaks
from scipy.optimize import curve_fit

reload(cfg), reload(stg)  # reloads modules before executing the code below

# NOTE: make changes to lo, if, tof, mixer offsets in 'configuration.py'
# NOTE: make changes to constant pulse amp and pulse duration in the qua script below

MEAS_NAME = "t1"  # used for naming the saved data file

########################################################################################
########################           MEASUREMENT SEQUENCE         ########################
########################################################################################

# Loop parameters
reps = 5000
wait_time = 100000  # in clock cycles

# Measurement pulse
update_rr_if = True
rr = stg.rr
rr_if = rr.int_freq
rr_ascale = 0.0195
rr_op = 'readout'
integW1 = "integW1"  # integration weight for I
integW2 = "integW2"  # integration weight for Q
# NOTE: The weights must be defined for the chosen measurement operation

# wait time between two pluse 
t_start = 4
t_stop = 25000
t_step = 200 # in clock cycle
t_list = np.arange(t_start, t_stop, t_step)

# Qubit pulse
qubit = stg.qubit
qubit_ascale = 1.0
qubit_f = qubit.int_freq  # IF frequency of qubit pulse
qubit_op = "gaussian"  # qubit operation as defined in config


with program() as t1:
    # Iteration variable
    n = declare(int)
    
    update_rr_if = declare(bool, value=update_rr_if)
    
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
    

    with if_(update_rr_if):
        rr_freq = declare(int, value=rr_if)
        update_frequency('rr', rr_freq)

    # Averaging loop   
    with for_(n, 0, n < reps, n + 1): # outer averaging loop
        with for_(t, t_start, t < t_stop, t + t_step): # inner frequency sweep
            
            play(qubit_op * amp(qubit_ascale), "qubit")
            wait(t, "qubit")
            align('qubit', 'rr')
            measure(rr_op * amp(rr_ascale), 'rr', None,
                    demod.full(integW1, I),
                    demod.full(integW2, Q))
            
            wait(wait_time, "qubit", 'rr')
            save(I, I_st_avg)
            save(Q, Q_st_avg)
            save(I, I_st)
            save(Q, Q_st)
            

    with stream_processing():
        I_st.buffer(len(t_list)).average().save('I_avg')
        Q_st.buffer(len(t_list)).average().save('Q_avg')
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
    ax.scatter(t_list, amps, s=4)

    # plot fitted curve
    params = plot_fit(t_list, amps, ax, fit_func="exp_decay")
    ax.set_title("average of %d results" % (reps - remaining_data))

    # update figure
    hdisplay.update(fig)


########################################################################################
############################           SAVE RESULTS         ############################
########################################################################################

metadata = (
    f"{reps = }, {f_start = }, {f_stop = }, {f_step = }, {wait_time = }, {rr_ascale = }"
)
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
plt.show()  # this blocks execution, and is hence run at the end of the script

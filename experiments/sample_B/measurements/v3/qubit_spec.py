# import all objects defined in the __init__.py file in the 'imports' folder
from qcrew.experiments.sample_B.imports import *
from scipy.signal import find_peaks
from scipy.optimize import curve_fit

reload(cfg), reload(stg)  # reloads modules before executing the code below

# NOTE: make changes to lo, if, tof, mixer offsets in 'configuration.py'
# NOTE: make changes to constant pulse amp and pulse duration in the qua script below

MEAS_NAME = "qubit_spec"  # used for naming the saved data file

########################################################################################
########################           MEASUREMENT SEQUENCE         ########################
########################################################################################

# Loop parameters
reps = 8000
wait_time = 75000  # in clock cycles

# Measurement pulse
update_rr_if = True
rr_if =  int(-49.4e6) #-49.5e+6
rr_if = int(rr_if)
rr = stg.rr

rr_ascale = 0.0175
rr_op = 'readout'
integW1 = "integW1"  # integration weight for I
integW2 = "integW2"  # integration weight for Q
# NOTE: The weights must be defined for the chosen measurement operation

# Parameters for optional qubit pulse
play_qubit = True
qubit_ascale = 1.5
# qubit_f = -50e+6  # IF frequency of qubit pulse
qubit_op = "saturation"  # qubit operation as defined in config
f_start = -50e+6
f_stop = -45e+6
f_step = 0.02e+6
qubit_f_list = np.arange(f_start, f_stop, f_step)

# Rearranges the input parameters in arrays over which QUA can
# iterate. The arrays are given in the order of outer to inner
# loop.
# parameter_list = [
#     (x.flatten()) for x in np.meshgrid(qubit_ascale, rr_ascale, indexing="ij")
# ]

# # Defines buffer size for averaging
# buffer_lengths = [
#     1 if type(x).__name__ in {"int", "float"} else len(x)
#     for x in [qubit_ascale, rr_ascale, qubit_f_list]
# ]

with program() as qubit_spec:
    # Iteration variable
    n = declare(int)
    qubit_f = declare(int)

    qubit_a = declare(fixed, value=qubit_ascale)
    rr_a = declare(fixed, value=rr_ascale)
    update_rr_if = declare(bool, value=update_rr_if)

    # Outputs
    I = declare(fixed)
    Q = declare(fixed)

    # Streams
    I_st = declare_stream()
    Q_st = declare_stream()
    

    with if_(update_rr_if):
        rr_if = declare(int, value=rr_if)
        update_frequency('rr', rr_if)

    # Averaging loop   
    with for_(n, 0, n < reps, n + 1): # outer averaging loop
        with for_(qubit_f, f_start, qubit_f < f_stop, qubit_f + f_step): # inner frequency sweep
            
            update_frequency('qubit', qubit_f)
            play(qubit_op * amp(qubit_a), "qubit", condition=play_qubit)
        
            align('qubit', 'rr')
            measure(rr_op * amp(rr_a), 'rr', None,
                    demod.full(integW1, I),
                    demod.full(integW2, Q))
            
            wait(wait_time, "qubit")
            save(I, I_st)
            save(Q, Q_st)
            

    with stream_processing():
        I_st.buffer(len(qubit_f_list)).average().save('I_mem')
        Q_st.buffer(len(qubit_f_list)).average().save('Q_mem')


########################################################################################
############################           GET RESULTS         #############################
########################################################################################

job = stg.qm.execute(qubit_spec)
result_handle = job.result_handles
result_handle.wait_for_all_values()

I_handle = result_handle.get("I_mem")
Q_handle = result_handle.get("Q_mem")
results = np.abs(I_handle.fetch_all() + 1j * Q_handle.fetch_all())

plt.plot(qubit_f_list, results)
plt.show()

########################################################################################
############################        TEMPORARY ANALYSIS      ############################
########################################################################################
def lorentzian(f, offset, a, f0, kappa):
    
    val = offset + (a / np.pi) * (kappa / ((f - f0) ** 2 + kappa ** 2))
    return val

# Initial guess of the parameters (you must find them some way!)
pguess = [9e-7, -4e-7, -54, 2]

# Fit the data
popt, pcov = curve_fit(lorentzian, qubit_f_list, results, p0 = pguess)

# Results
offset_fit, a_fit, f0_fit, kappa_fit = popt[0], popt[1], popt[2], popt[3]
print(a_fit, offset_fit, f0_fit, kappa_fit)


# from matplotlib.ticker import FormatStrFormatter
# fig, axe = plt.subplots()
# plt.tight_layout()
# plt.style.use("classic")   
# axe.plot(freq_if , amps_qubit,'r', label='qubit spectrum')
# axe.plot(freq_if , lorentzian(freq_if , offset_fit, a_fit, f0_fit, kappa_fit),'b', label='fitted curve')

# axe.yaxis.set_major_formatter(FormatStrFormatter('%.2E'))
# axe.legend()
# axe.grid('on')
# plt.show()

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
    np.savetxt(datapath, [qubit_f_list, results], delimiter=",")
plt.savefig(imgpath)

########################################################################################
########################################################################################
########################################################################################
plt.show()  # this blocks execution, and is hence run at the end of the script

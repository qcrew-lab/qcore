from qcrew.experiments.coax_test.imports import *

reload(cfg), reload(stg)  # reloads modules before executing the code below

# NOTE: make changes to lo, if, tof, mixer offsets in 'configuration.py'
# NOTE: make changes to constant pulse amp and pulse duration in the qua script below

MEAS_NAME = "tof_calib"  # used for naming the saved data file

SAMPLING_RATE = 1e9  # how many samples the OPX registers per second
ADC_RESOLUTION = 2 ** 12  # used for converting ADC reading to analog voltage measured.
########################################################################################
########################           MEASUREMENT SEQUENCE         ########################
########################################################################################

# Loop parameters
reps = 20000
wait_time = 8000  # in clock cycles

# Measurement pulse
rr = stg.rr
rr_f = rr.int_freq
rr_ascale = 1.0
rr_op = "readout"
integW1 = "integW1"  # integration weight for I
integW2 = "integW2"  # integration weight for Q
# NOTE: The weights must be defined for the chosen measurement operation

with program() as tof_calib:
    adc_stream = declare_stream(adc_trace=True)
    n = declare(int)

    with for_(n, 0, n < reps, n + 1):
        reset_phase(rr.name)
        align(rr.name)
        measure(rr_op * amp(rr_ascale), rr.name, adc_stream)
        wait(wait_time, rr.name)

    with stream_processing():
        adc_stream.input1().average().save("adc_results")
        adc_stream.input1().average().fft().save("adc_fft")

########################################################################################
############################           GET RESULTS         #############################
########################################################################################
job = stg.qm.execute(tof_calib)
result_handle = job.result_handles
result_handle.wait_for_all_values()
results = result_handle.get("adc_results").fetch_all()
results_fft = job.result_handles.get("adc_fft").fetch_all()

# converting FFT results
# readout_pulse_len is defined in configuration.py script.
pulse_len = cfg.readout_pulse_len
results_fft = np.sqrt(np.sum(np.squeeze(results_fft) ** 2, axis=1)) / pulse_len
fft_freqs = np.arange(0, 0.5, 1 / pulse_len)[:] * SAMPLING_RATE
fft_amps = results_fft[: int(np.ceil(pulse_len / 2))]

f, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5))
ax1.plot(results / ADC_RESOLUTION)
# NOTE: The FFT plot ignores the DC offset
ax2.plot(fft_freqs[5:] / 1e6, fft_amps[5:])

########################################################################################
############################           SAVE RESULTS         ############################
########################################################################################

metadata = f"{reps = }, {wait_time = }, {rr_ascale = }, {rr_f = }"
filename = f"{datetime.now().strftime('%H-%M-%S')}_{MEAS_NAME}"
datapath = DATA_FOLDER_PATH / (filename + ".csv")
imgpath = DATA_FOLDER_PATH / (filename + ".png")

with datapath.open("w") as f:
    f.write(metadata)
    np.savetxt(datapath, results, delimiter=",")  # won't work for non 1D and 2D nparray
plt.savefig(imgpath)

########################################################################################
########################################################################################
########################################################################################
plt.show()  # this blocks execution, and is hence run at the end of the script

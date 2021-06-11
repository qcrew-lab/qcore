import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

freqs = np.arange(-50e6, -49e6, 0.015e6)
len_freqs = len(freqs)
#pows = np.concatenate((np.linspace(0.005, 0.025, 21), np.linspace(0.026, 2, 41)))
pows = np.linspace(0.01, 0.02, 60) ## check if this is correct
len_pows = len(pows)
signal_with = np.empty((len_pows, len_freqs))  # y, x; measured signal with qubit pulse
signal_without = np.empty((len_pows, len_freqs))  # y, x; without qubit pulse


##Read csv
filepath_with = (
    Path.cwd()
    / "data/sample_B/2021-06-10/15-12-32_rr_spec_sweep_amp-Copy-withqubit.csv"
)
with filepath_with.open() as f:
    lines_with = f.readlines()

filepath_without = (
    Path.cwd()
    / "data/sample_B/2021-06-10/13-10-41_rr_spec_sweep_amp-Copy-withoutqubit.csv"
)
with filepath_without.open() as f:
    lines_without = f.readlines()


##Extract data from csvs
counter = 0
for amp in range(len_pows):
    counter += 1  # skip rr_amp line
    signal_with[amp] = lines_with[counter : counter + len_freqs]
    signal_without[amp] = lines_without[counter : counter + len_freqs]
    counter += len_freqs


contrast = np.subtract(signal_with, signal_without)

plot = plt.pcolormesh(freqs, pows, contrast, cmap="terrain")
plt.xlabel("Readout IF (Hz)")
plt.ylabel("Readout pulse a_scale")
plt.title("Contrast")
plt.colorbar(plot, extend="max")
plt.show()

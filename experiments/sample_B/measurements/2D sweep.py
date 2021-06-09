
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

freqs = np.arange(-51e6, -48.5e6, 0.02e6)
len_freqs = len(freqs)
pows = np.linspace(0.01, 2.0, 60)
len_pows = len(pows)
signal_with = np.empty((len_pows, len_freqs))  # y, x; measured signal with qubit pulse
#signal_without = np.empty((len_pows, len_freqs))  # y, x; without qubit pulse


##Read csv
filepath_with = Path.cwd() / "data/sample_B/2021-06-09/20-31-58_rr_spec_sweep_amp-Copy-withoutqubit.csv"
with filepath_with.open() as f:
    lines_with = f.readlines()

# filepath_without = Path.cwd() / "data/sample_B/2021-06-09/ 20-31-58_rr_spec_sweep_amp-Copy-withoutqubit.csv"
# with filepath_without.open() as f:
#     lines_without = f.readlines()


##Extract data from csvs
counter = 0
for amp in range(len_pows):
    counter += 1  # skip rr_amp line
    signal_with[amp] = lines_with[counter:counter + len_freqs]
    #signal_without[amp] = lines_without[counter:counter + len_freqs]
    counter += len_freqs

##Plot data in 2D colormap
fig, axis = plt.subplots(nrows=1, ncols=1, sharex=True, sharey=True, figsize=(12, 8))
axis.set_title("With pi pulse")
colormap = axis.pcolormesh(freqs, pows[:], signal_with[:], shading="auto", cmap="terrain",#vmin = 1e-7, vmax = 5e-5
)
fig.supxlabel("Readout IF (Hz)")
fig.supylabel("Readout pulse a_scale")
fig.suptitle("RR spectroscopy with measurement power sweep")
fig.colorbar(colormap, extend='max')
plt.show()

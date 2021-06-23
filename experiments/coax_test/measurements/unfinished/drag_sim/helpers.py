""" Helper functions for drag pulse simulation """
import matplotlib.pyplot as plt
import numpy as np
from .configuration import DRAG_COEFFICIENT


def plot_waveforms(wfs):
    fig = plt.figure(figsize=(12, 8))
    ax1, ax2, ax3, ax4 = (
        plt.subplot(411),
        plt.subplot(412),
        plt.subplot(413),
        plt.subplot(414),
    )

    fig.suptitle("DRAG pulse simulation")

    ax1.set_title(f"Scaled by [1, 0, 0, {DRAG_COEFFICIENT}] in QUA loop")
    ax2.set_title(f"Scaled by {DRAG_COEFFICIENT} in QM config")
    ax3.set_title("Difference in I and Q output")
    ax4.set_title("Difference in amplitude")

    ax1.plot(wfs["i_1"], label="I: AO1", color="blue")
    ax1.plot(wfs["q_1"], label="Q: AO2", color="orange")

    ax2.plot(wfs["i_2"], label="I: AO1", color="blue")
    ax2.plot(wfs["q_2"], label="Q: AO2", color="orange")

    i_diff, q_diff = wfs["i_1"] - wfs["i_2"], wfs["q_1"] - wfs["q_2"]
    ax3.plot(i_diff, label="Diff I: AO1", color="blue")
    ax3.plot(q_diff, label="Diff Q: AO2", color="orange")

    amp_diff = np.abs(wfs["i_1"] + 1j * wfs["q_1"]) - np.abs(
        wfs["i_2"] + 1j * wfs["q_2"]
    )
    ax4.plot(amp_diff, label="Diff amp", color="green")

    ax1.legend(loc="upper right")
    ax2.legend(loc="upper right")
    ax3.legend(loc="upper right")
    ax4.legend(loc="upper right")

    ax1.set_xticks([])
    ax2.set_xticks([])
    ax3.set_xticks([])

    plt.xlabel("Time [ns]")
    ax1.set_ylabel("Signal [V]")
    ax2.set_ylabel("Signal [V]")
    ax3.set_ylabel("Signal [V]")
    ax4.set_ylabel("Amplitude")
    plt.show()


def get_processed_samples(sample_object, job, port_str, pad):
    samples = sample_object.con1.analog[port_str]
    analog_waveforms = job.simulated_analog_waveforms()
    start = int(analog_waveforms["elements"]["qubit"][0]["timestamp"])
    stop = start + int(analog_waveforms["elements"]["qubit"][0]["duration"])
    return samples[start - pad : stop + pad]

""" Qcrew plotter v1.0 """

import matplotlib.pyplot as plt
from IPython import display
from qcrew.codebase.analysis import fit


class Plotter:
    """ Single axis x-y plotter. Supports line, scatter, and errorbar plot. Provides a rudimentary live plotting routine. """
    def __init__(self, title: str, xlabel: str, ylabel: str = "Signal (A.U.)"):
        plt.rcParams["figure.figsize"] = (12, 8)  # adjust figure size

        self.figtitle: str = title
        self.xlabel: str = xlabel
        self.ylabel: str = ylabel

    def live_plot(self, x, y, n, fit_fn = None, err = None):
        """" If `live_plot(data)` is called in an IPython terminal context, the axis is refreshed and plotted with the new data using IPython `display` tools. """
        plt.cla()

        if err is not None:
            self.plot_errorbar(x, y, err, "data")
        else:
            self.plot_scatter(x, y)

        if fit_fn is not None:
            fit_params = fit.do_fit(fit_fn, x, y)  # get fit params
            y_fit = fit.eval_fit(fit_fn, fit_params, x)  # get fit values
            self.plot_line(x, y_fit, label="fit")

        plt.title(self.figtitle + f": {n} reps")
        plt.xlabel(self.xlabel)
        plt.ylabel(self.ylabel)
        plt.legend()

        display.display(plt.gcf())  # plot latest batch
        display.clear_output(wait=True)  # clear plot when new plot is available

    def plot_errorbar(self, x, y, err, label):
        plt.errorbar(
            x,
            y,
            yerr=err,
            label=label,
            ls="none",
            lw=1,
            ecolor="black",
            marker="o",
            ms=4,
            mfc="black",
            mec="black",
            capsize=3,
            fillstyle="none",
        )

    def plot_scatter(self, x, y):
        plt.scatter(x, y, s=4, c="black", marker="o")

    def plot_line(self, x, y, label):
        plt.plot(x, y, color="m", lw=2, label=label)

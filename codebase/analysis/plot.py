import numpy as np
import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib import gridspec
from IPython import display

from qcrew.codebase.analysis import fit


def plot_fit(xs, ys, axis, yerr=None, fit_func="sine"):

    if yerr is not None:
        # Calculate average error throughout all datapoints
        avg_yerr = np.average(yerr)
        error_label = "average error = {:.3e}".format(avg_yerr)

        axis.errorbar(
            xs,
            ys,
            yerr=yerr,
            marker="s",
            ls="none",
            markersize=3,
            color="b",
            label=error_label,
        )

    params = fit.do_fit(fit_func, xs, ys)
    fit_ys = fit.eval_fit(fit_func, params, xs)

    # Convert param values into conveniently formatted strings
    param_val_list = [
        key + " = {:.3e}".format(val.value) for key, val in params.items()
    ]
    # Join list in a single block of text
    label_text = "\n".join(param_val_list)

    axis.plot(xs, fit_ys, color="m", lw=3, label=label_text)

    return params


class FakeLivePlotter:
    def __init__(self):
        self.fig = plt.figure()
        self.ax = self.fig.add_subplot(1, 1, 1)
        self.hdisplay = display.display("", display_id=True)

    def plot(self, x, y, N: int = None, fit_func: str = None):  # 2D plots only
        """ """
        self.ax.clear()
        self.ax.plot(x, y)  # plot data
        if fit_func is not None:
            plot_fit(x, y, self.ax, fit_func=fit_func)  # plot fit
        if N is not None:
            self.ax.set_title(f"Rolling average after {N} reps")

        self.hdisplay.update(self.fig)  # update figure

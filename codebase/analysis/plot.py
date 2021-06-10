import numpy as np
import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib import gridspec
from IPython import display

from qcrew.codebase.analysis import fit


def plot_fit(xs, ys, axis, y_errs=None, fit_func="sine"):

    if y_errs:
        axis.errorbar(
            xs, ys, yerr=y_errs, marker="s", ls="none", markersize=3, color="b"
        )

    params = fit.do_fit(fit_func, xs, ys)
    fit_ys = fit.eval_fit(fit_func, params, xs)

    axis.plot(
        xs,
        fit_ys,
        color="m",
        lw=3,
    )

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

import numpy as np
import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib import gridspec

from qcrew.codebase.analysis import fit


def plot_fit(xs, ys, axis, y_errs=None, fit_func="sine"):

    if y_errs:
        axis.errorbar(
            xs, ys, yerr=y_errs, marker="s", ls="none", markersize=3, color="b"
        )

    params = fit.do_fit(fit_func, xs, ys)
    fit_ys = fit.eval_fit(fit_func, params, xs)

    axis.plot(xs, fit_ys)

    return params

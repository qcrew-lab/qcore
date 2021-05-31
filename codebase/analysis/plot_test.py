# -*- coding: utf-8 -*-

import numpy as np
import matplotlib as mpl
import matplotlib.pyplot as plt
import qcrew.codebase.analysis.fit
from matplotlib import gridspec

xs = np.linspace(-1, 1, 101)
ys = (np.cos(2 * np.pi * xs) + 1) / 2
y_errs = 0.05 * ys
# plt.figure(figsize=(6,4))
# plt.plot(xs, ys)
# plt.draw()
# plt.pause(0.1)
# print('plot completed')


def analysis(xs, ys, y_errs=None, fig=None, repeat_pulse=1, fit_func="sine", txt=""):

    if fig is None:
        fig = plt.figure()
        gs = gridspec.GridSpec(2, 1, height_ratios=[3, 1])
        fig.add_subplot(gs[0])
        fig.add_subplot(gs[1])

    fig.axes[0].errorbar(
        xs, ys, yerr=y_errs, marker="s", ls="none", markersize=3, color="b"
    )

    params = fit.do_fit(fit_func, xs, ys)
    fit_ys = fit.eval_fit(fit_func, params, xs)

    pi_amp = repeat_pulse / (2.0 * params["f0"].value)
    txt = "test"
    txt += "pi amp = %0.4f; pi/2 amp = %0.4f" % (pi_amp, pi_amp / 2.0)
    fig.axes[0].plot(xs, fit_ys, label=txt)
    fig.axes[1].plot(xs, ys - fit_ys, marker="s", markersize=3, color="b")

    fig.axes[0].set_ylabel("contrast [AU]")
    fig.axes[0].set_xlabel("Pulse amplitude")
    fig.axes[0].legend(loc="best")
    fig.axes[1].set_ylabel("residual")

    fig.canvas.draw()
    plt.tight_layout()
    return params


params = analysis(xs, ys, y_errs=y_errs)

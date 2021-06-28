import numpy as np
from qcrew.codebase.analysis.fit import do_fit, eval_fit

def fit_analysis(data: dict, i_tag: str, q_tag: str, x: np.ndarray, fit_function: str) -> None:

    if i_tag in data.keys():
        last_avg_i = data[i_tag][-1]
    else:
        raise ValueError(f"No data for the tag {i_tag}")

    if q_tag in data.keys():
        last_avg_q = data[q_tag][-1]
    else:
        raise ValueError(f"No data for the tag {q_tag}")

    signal = np.abs(last_avg_i + 1j * last_avg_q)

    fit_params = do_fit(fit_function, x, signal)  # get fit parameters
    y_fit = eval_fit(fit_function, fit_params, x)  # get fit values

    return signal, y_fit, fit_params

def live_plot(ax, x, y, fit_y, yerr=None, fit_function):
    pass

def plot_fit(xs, ys, axis, yerr=None, fit_func="sine"):

    if yerr is not None:
        # Calculate average error throughout all datapoints
        avg_yerr = np.average(yerr)
        error_label = "average error = {:.3e}".format(avg_yerr)

        axis.errorbar(
            xs,
            ys,
            yerr=yerr,
            marker="o",
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
    # plt.xlabel("time clock")
    # plt.ylabel("amps")

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

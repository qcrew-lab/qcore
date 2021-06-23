""" Qcrew plotter v1.0 """

import matplotlib.pyplot as plt

class Plotter:
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

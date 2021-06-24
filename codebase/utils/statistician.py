""" Utility to calculate statistics in a single pass """
import numpy as np

# Python implementation of Welford's online algorithm
# Inspired by http://www.johndcook.com/standard_deviation.html
def get_std_err(xs, ms, n, std_err=None, m=None, s=None):
    if std_err is None:
        old_m, old_s = ms[0], np.zeros(ms.shape[1])
        xs, ms = xs[1:], ms[1:]
    else:
        old_m, old_s = m, s
    new_deltas, old_deltas = xs - ms, xs - np.insert(ms, 0, old_m, 0)[:-1]
    new_m, new_s = ms[-1], old_s + np.sum(new_deltas * old_deltas, axis=0)
    std_err = new_s / (n * (n - 1))
    return std_err, new_m, new_s

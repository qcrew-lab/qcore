""" Utility to calculate statistics in a single pass """

# Python implementation of Welford's online algorithm
# Inspired by http://www.johndcook.com/standard_deviation.html
def get_std_err(xs, n, old_std_err=None, old_m=None, old_s=None):
    if old_std_err is None:
        new_m, new_s = _get_m_s(xs[1:], xs.shape[0] - 1, xs[0], 0)
    else:
        new_m, new_s = _get_m_s(xs, xs.shape[0], old_m, old_s)
    new_std_err = new_s / (n * (n - 1))
    return new_std_err, new_m, new_s

def _get_m_s(xs, k, old_m, old_s):
    for i in range(k):
        new_m = old_m + (xs[i] - old_m) / (i + 1)
        new_s = old_s + (xs[i] - old_m) * (xs[i] - new_m)
    return new_m, new_s

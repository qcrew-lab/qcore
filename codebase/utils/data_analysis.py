import numpy as np

def data_analysis(i_raw: Optional[np.narray], 
                  q_raw: Optional[np.ndarray], 
                  y_sq_raw: Optional[np.ndarray],
                  i_avg: Optional[np.narray], 
                  q_avg: Optional[np.ndarray], 
                  y_sq_raw_avg: Optional[np.ndarray],) -> tuple:

    if i_raw and q_raw and not y_sq_raw:
        ys_raw = np.sqrt(np.multiply(i_raw, i_raw) + np.multiply(q_raw, q_raw))
    elif y_sq_raw:
        ys_raw = np.sqrt(y_sq_raw)
    
    if i_avg and q_avg and not y_sq_raw_avg:
        ys_raw_avg = np.sqrt(np.multiply(i_avg, i_avg) + np.multiply(q_avg, q_avg))
    elif y_sq_raw_avg:
        ys_raw_avg = np.sqrt(y_sq_raw_avg)
        stats = get_std_err(ys_raw, ys_raw_avg, num_so_far, *stats)
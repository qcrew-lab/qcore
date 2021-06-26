from qm.QmJob import QmJob
from qm import MultipleNamedJobResult, SingleNamedJobResult
from qcrew.codebase.analysis.fit import do_fit, eval_fit
from pathlib import Path
import numpy as np
import time
import h5py
from matplotlib import pyplot as plt
from typing import Optional

def live_fetch(job: QmJob, reps: int, interval: Optional[int]) -> None:
    
    job_results = job.result_handles

    # Mode 1: fetch the data by fixed interval 
    if interval: 
        num_have_got = 0
        while job_results.is_processing() or num_have_got < reps:
            update_result_dict = {}
            for name, handle in job_results:
                if isinstance(handle, MultipleNamedJobResult):
                    handle.wait_for_values(num_have_got + interval)
                    
                    if (reps - num_have_got) > interval:
                        
                        num_sor_far = num_have_got + interval
                        update_result_dict[name] = handle.fetch(
                            slice(num_have_got , num_sor_far), flat_struct=True)
                    # fetch the residual data
                    else:
                        num_update = reps
                        update_result_dict[name] = handle.fetch(
                            slice(num_have_got , num_sor_far), flat_struct=True)
                    
            yield(num_sor_far, update_result_dict)
            num_have_got = num_sor_far
            time.sleep(2)
    
    # Mode 2: fetch the data when result handle is updated 
    else:
        num_have_got_dict = {name: 0 for (name, handle) in job_results if isinstance(handle, MultipleNamedJobResult)}

        # the minimal number of data that we have got in different stream
        min_num_have_got = min(list(num_have_got_dict.values()))
        while job_results.is_processing() or min_num_have_got < reps:
            
            update_result_dict = {}
            num_so_far_dict = {}
            for name, handle in job_results:
                if isinstance(handle, MultipleNamedJobResult):
                    
                    num_so_far = handle.count_so_far() 
                    num_so_far_dict[name] = num_so_far
                    if (num_so_far - num_have_got_dict[name]) > 0:

                        num_so_far = handle.count_so_far()
                        update_result_dict[name] = handle.fetch(
                                slice(num_have_got_dict[name] , num_so_far), flat_struct=True)
            
            min_num_so_far = min(list(num_so_far_dict.values()))
            yield (min_num_so_far, update_result_dict)

            for key in num_so_far_dict.keys():
                if key in num_have_got_dict.keys():
                    num_have_got_dict[key] = num_so_far[key]


def final_fetch(job: QmJob) -> None:
    job_results = job.result_handles
    result_dict = {}

    # wait for all the data
    job_results.wait_for_all_values()
    for name, handle in job_results:
        if isinstance(handle, SingleNamedJobResult):
            result_dict[name] = handle.fetch_all(flat_struct=True)
    return result_dict


def live_analysis(data: dict, i_tag: str, q_tag: str, x: np.ndarray, fit_function: str) -> None:

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


def save_figure(database: h5py.File) -> None:
    p = Path(database.filename)
    name = p.stem
    folder = Path(database.filename).parent.absolute()
    print(name)
    print(folder)
    filename = name + ".png"
    full_path = folder / filename
    plt.savefig(full_path, format="png", dpi=600)
    print(f"Plot saved at {full_path}")

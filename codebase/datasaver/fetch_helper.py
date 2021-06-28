from qm.QmJob import QmJob
from qm import MultipleNamedJobResult, SingleNamedJobResult

from pathlib import Path
import numpy as np
import time
import h5py
from matplotlib import pyplot as plt


def live_fetch(job: QmJob, reps: int, interval: int=100) -> None:
    job_results = job.result_handles

    num_have_got = 0

    while job_results.is_processing() or num_have_got < reps:

        # print(f"fetch_iteration {num_have_got}")
        update_result_dict = {}
        for name, handle in job_results:
            if isinstance(handle, MultipleNamedJobResult):
                handle.wait_for_values(num_have_got + interval)
                
                if (reps - num_have_got) > interval:
                    update_result_dict[name] = handle.fetch(
                        slice(num_have_got , num_have_got + interval), flat_struct=True
                    )
                else:
                     update_result_dict[name] = handle.fetch(
                        slice(num_have_got , reps), flat_struct=True
                    )

        yield (num_have_got, update_result_dict)
        num_have_got = num_have_got + interval
        time.sleep(2)


def final_fetch(job: QmJob) -> None:
    job_results = job.result_handles
    result_dict = {}

    # wait for all the data
    job_results.wait_for_all_values()
    for name, handle in job_results:
        if isinstance(handle, SingleNamedJobResult):
            result_dict[name] = handle.fetch_all(flat_struct=True)
    return result_dict


def get_last_average_data(data: dict, i_tag: str, q_tag: str) -> None:

    if i_tag in data.keys():
        last_avg_i = data[i_tag][-1]
    else:
        raise ValueError(f"No data for the tag {i_tag}")

    if q_tag in data.keys():
        last_avg_q = data[q_tag][-1]
    else:
        raise ValueError(f"No data for the tag {q_tag}")

    signal = np.abs(last_avg_i + 1j * last_avg_q)
    return signal


def save_figure(fig, database: h5py.File) -> None:
    p = Path(database.filename)
    name = p.stem
    folder = Path(database.filename).parent.absolute()
    print(name)
    print(folder)
    filename = name + ".png"
    full_path = folder / filename
    fig.savefig(full_path, format="png", dpi=600)
    print(f"Plot saved at {full_path}")

""" Work in progress """
import numpy as np


def update_results(raw_data, N, result_handles, handle_tags):

    if not raw_data:
        raw_data = {tag: np.array([]) for tag in handle_tags}

    result_handles = [result_handles.get(tag) for tag in handle_tags]

    start_idx = len(raw_data[handle_tags[0]])
    slice_obj = slice(start_idx, start_idx + N)

    for indx, handle in enumerate(result_handles):
        tag = handle_tags[indx]

        # Wait until the batch is ready
        handle.wait_for_values(start_idx + N)

        # Fetching partial results. It is ideal to use flat_struct so to
        # receive a numpy array.
        partial_results = handle.fetch(slice_obj, flat_struct=True)

        # Update data
        raw_data[tag] = np.array(list(raw_data[tag]) + list(partial_results))

    return raw_data


""" Dumping the code for getting stdev of data here
# get stdev of data over N to check if we are averaging correctly
result_handles.wait_for_all_values()
I_raw = result_handles.I.fetch_all(flat_struct = True)
Q_raw = result_handles.Q.fetch_all(flat_struct = True)
amps_raw = np.abs((I_raw + 1j * Q_raw)).T
stdevs_raw = np.zeros((reps, len(qubit_a_list)))

I_avg = result_handles.I_avg.fetch_all(flat_struct = True)
Q_avg = result_handles.Q_avg.fetch_all(flat_struct = True)
amps_avg = np.abs((I_avg + 1j * Q_avg)).T
stdevs_avg = np.zeros((reps, len(qubit_a_list)))

for i in range(1, reps + 1):
    stdevs_raw[i - 1] = np.std(amps_raw[:,:i], axis=1)
    stdevs_avg[i - 1] = np.std(amps_avg[:,:i], axis=1)

stdevs_raw_avg = np.mean(stdevs_raw, axis = 1)
stdevs_avg_avg = np.mean(stdevs_avg, axis = 1)
"""
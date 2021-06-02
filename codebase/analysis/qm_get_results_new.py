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

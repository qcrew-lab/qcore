""" Work in progress """
import numpy as np

# the goal of this script is to periodically extract partial results from QM
# having these partial results can help us live plot them
# or do other processing on them (without waiting for ALL results)

# we want to save both raw data ("raw_results") and rolling averages
# we want to periodically check if the job has produced new results
# we want to plot the rolled-over average ("processed_results")

# this method was written with power_rabi in mind
# method name and signature must be improved once it is implemented properly


def get_results(job_result, reps, a_vec_len):
    # TODO: do not hard-code the handle name
    I_handle = job_result.get("I_mem")
    Q_handle = job_result.get("Q_mem")
    a_handle = job_result.get("a_mem")

    raw_results = np.empty([3, reps * a_vec_len])  # [0] -> I, [1] -> Q, [2] -> avg
    processed_results = np.zeros([a_vec_len])  # holds avg(abs(I + iQ))
    # counter to evaluate indices within the loop, we can probably also use python's enumerate for this
    counter = 1
    while job_result.is_processing():
        num_values_to_wait_for = a_vec_len * counter
        start_idx = ((counter - 1) * num_values_to_wait_for) + 1
        # QM docu for fetch() suggests slice is 1-indexed
        # really confused whether slice is 1-indexed or 0-indexed, will need to test...
        slice_obj = slice(start_idx, num_values_to_wait_for)

        # NEED TO TEST IF THESE SLICES INDEED GIVE US THE DATA WE WANT
        I_handle.wait_for_values(num_values_to_wait_for)
        I_partial_results = I_handle.fetch(slice_obj)
        # numpy arrays are 0-indexed
        raw_results[0][start_idx - 1, num_values_to_wait_for - 1] = I_partial_results

        # not sure if the handles are populated serially or in parallel, it shouldn't matter either way I think
        Q_handle.wait_for_values(num_values_to_wait_for)
        Q_partial_results = I_handle.fetch(slice_obj)
        raw_results[1][start_idx - 1, num_values_to_wait_for - 1] = Q_partial_results

        a_handle.wait_for_values(num_values_to_wait_for)
        a_partial_results = I_handle.fetch(slice_obj)
        raw_results[2][start_idx - 1, num_values_to_wait_for - 1] = a_partial_results

        abs_I_Q = np.abs(I_partial_results + 1j * Q_partial_results)
        # have I used the mean() function correctly ???
        processed_results = np.mean(np.array([processed_results, abs_I_Q]), axis=0)

        counter = counter + 1  # increment counter for next loop iteration

    # Concern - the current while loop condition might not allow us to fetch the last few data points, because the job_result will already be processed by then...

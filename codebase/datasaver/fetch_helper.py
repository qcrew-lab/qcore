from qm.qua import *



def live_fetch(job: qm.QMjob, reps: int) -> None:

    job_results = job.result_handles

    num_have_got = -1
    num_so_far = 0
    while handle.is_processing() or num_have_got < reps:
        update_result_dict = {}
        for name, handle in job_results:
            if isinstance(handle, qm.MultipleNamedJobResult): 
                num_so_far = handle.count_so_far()
                if (num_so_far - num_have_got > 0) and num_so_far > 1:
                    update_result_dict[name] = handle.fetch(slice(num_have_got + 1, num_so_far +1), flat_struct=True)
        yield update_result_dict
        
        num_have_got = num_so_far
        time.sleep(2)



def final_fetch(job: qm.QMjob) ->None:
    job_results = job.result_handles
    result_dict = {}
    job_results.wait_for_all()
    for name, handle in job_results:
        if isinstance(handle, qm.SingleNamedJobResult): 
            result_dict[name] = handle.fetch_all(flat_struct=True)
    return result_dict
            
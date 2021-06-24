""" Qcrew QM result fetcher v1.0 """

import numpy as np
from qm.QmJob import JobResults


class Fetcher:
    """ """

    def __init__(self, handle: JobResults, tags: tuple[str]) -> None:
        self.count: int = 0  # number of results fetched so far

        self.handle: JobResults = handle
        self.tags: tuple[str] = tags
        for tag in tags:  # wait for at least 2 results to be processed
            handle.get(tag).wait_for_values(2)


    def fetch(self) -> dict[str, np.ndarray]:
        """ Fetch next batch of available results for all tags in result handle """
        count = min(len(self.handle.get(tag)) for tag in self.tags)
        slc = slice(self.count, count)
        self.count = count
        return {t: self.handle.get(t).fetch(slc, flat_struct=True) for t in self.tags}

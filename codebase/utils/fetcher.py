""" Qcrew QM result fetcher v1.0 """
from typing import Callable
import numpy as np
from qm.QmJob import JobResults
from qm._results import SingleNamedJobResult, MultipleNamedJobResult


class Fetcher:

    def __init__(self, handle: JobResults, num_results: int) -> None:
        self.total_count: int = num_results  # tota number of results to fetch
        self.count: int = 0  # current number of results fetched
        self.last_count: int = None  # last known result count

        self.handle: JobResults = handle
        self._spec: dict[str, Callable] = {"single": dict(), "multiple": dict()}
        self._pre_process_results()

        self.is_fetching: bool = True  # to indicate fetching has started

    def _pre_process_results(self):
        for tag, result in self.handle:
            if isinstance(result, SingleNamedJobResult):
                self._spec["single"][tag] = self._fetch_single
            elif isinstance(result, MultipleNamedJobResult):
                self._spec["multiple"][tag] = self._fetch_multiple
                result.wait_for_values(2)

    def fetch(self) -> dict[str, np.ndarray]:
        self.last_count = self.count  # get and update counts
        self.count = min(len(self.handle.get(tag)) for tag in self._spec["multiple"])

        if self.count == self.last_count:  # no new results to fetch
            if not self.handle.is_processing() and self.count >= self.total_count:
                self.is_fetching = False  # fetching is complete
            return dict()  # return empty dict because no new results to fetch

        partial_results = dict()  # populate and return partial results dictionary
        for result_type in self._spec:
            for tag in self._spec[result_type]:
                partial_results[tag] = self._spec[result_type][tag](tag)
        return partial_results

    def _fetch_single(self, tag):
        return self.handle.get(tag).fetch_all(flat_struct=True)

    def _fetch_multiple(self, tag):
        slc = slice(self.last_count, self.count)
        return self.handle.get(tag).fetch(slc, flat_struct=True)

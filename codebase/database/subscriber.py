import functools
import logging
import time

from threading import Thread
from typing import Any, Callable, List, Mapping, Optional, TYPE_CHECKING
from queue import Empty, Queue

import dataset_hdf5 as ds


class _Subscriber(Thread):
    """
    Class to add a subscriber to a :class:`.DataSet`. The subscriber gets called every
    time an insert is made to the results_table.

    The _Subscriber is not meant to be instantiated directly, but rather used
    via the 'subscribe' method of the :class:`.DataSet`.

    NOTE: A subscriber should be added *after* all parameters have been added.

    NOTE: Special care shall be taken when using the *state* object: it is the
    user's responsibility to operate with it in a thread-safe way.
    """

    def __init__(self,
                 dataset: ds.HDF5DataSet,
                 id_: str,
                 callback: Callable[..., None],
                 state: Optional[Any] = None,
                 loop_sleep_time: int = 0,  # in milliseconds
                 min_queue_length: int = 1,
                 callback_kwargs: Optional[Mapping[str, Any]] = None
                 ) -> None:
        super().__init__()

""" Qcrew datasaver v1.0 """

from datetime import date, datetime
from pathlib import Path

import h5py


class DummyDatasaver:
    """ """

    datapath: Path = Path.cwd() / "data"
    file_extension: str = ".hdf5"


    def __init__(self, sample_name: str, filename_suffix: str) -> None:
        """ """
        self.folderpath: Path = self.datapath / sample_name / str(date.today())
        self.folderpath.mkdir(parents=True, exist_ok=True)  # make folder if none exists

        filename = f"{datetime.now().strftime('%H-%M-%S')}_{filename_suffix}"
        self.filepath: Path = self.folderpath / (filename + self.file_extension)

        self.file = h5py.File(str(self.filepath), "a")  # open file in append mode


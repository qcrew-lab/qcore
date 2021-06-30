from importlib import reload
from pathlib import Path
import time

import numpy as np
from qm.qua import *

from qcrew.experiments.coax_test.imports import configuration as cfg
from qcrew.experiments.coax_test.imports import stage as stg
from qcrew.codebase.datasaver.hdf5_helper import initialise_database, DataSaver
from qcrew.codebase.utils.fetcher import Fetcher
from qcrew.codebase.utils.plotter import Plotter
from qcrew.codebase.utils.statistician import get_std_err


################           IMPORTS NOT NEEDED FOR V4 SCRIPTS           #################
# NOTE WE NEED TO GET RID OF THESE ASAP!

import matplotlib.pyplot as plt
from IPython import display
import scipy
import h5py
from qcrew.codebase.analysis.plot import plot_fit
from qcrew.codebase.analysis.qm_get_results import update_results
from qcrew.codebase.analysis.plot import FakeLivePlotter
from qcrew.codebase.analysis import fit
from qcrew.codebase.utils.fixed_point_library import Fixed, Int
from datetime import datetime, date, timedelta

STAGE_NAME = "coax_test"  # this is used to save experimental data to the correct folder
DAILY_SUBFOLDER = str(date.today())
DATA_FOLDER_PATH = Path().resolve() / "data" / STAGE_NAME / DAILY_SUBFOLDER
DATA_FOLDER_PATH.mkdir(parents=True, exist_ok=True)

test_var = 5

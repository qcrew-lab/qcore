import matplotlib.pyplot as plt
import numpy as np
from IPython import display
import time
import scipy
from qm.qua import *
import h5py

from importlib import reload
from qcrew.experiments.coax_test.imports import configuration as cfg
from qcrew.experiments.coax_test.imports import stage as stg
from qcrew.codebase.analysis.plot import plot_fit
from qcrew.codebase.analysis.qm_get_results import update_results
from qcrew.codebase.analysis.plot import LivePlotter
from qcrew.codebase.analysis import fit

from datetime import datetime, date, timedelta
from pathlib import Path

STAGE_NAME = "coax_test"  # this is used to save experimental data to the correct folder
DAILY_SUBFOLDER = str(date.today())
DATA_FOLDER_PATH = Path().resolve() / "data" / STAGE_NAME / DAILY_SUBFOLDER
DATA_FOLDER_PATH.mkdir(parents=True, exist_ok=True)

test_var = 5

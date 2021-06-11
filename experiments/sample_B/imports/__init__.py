import matplotlib.pyplot as plt
import numpy as np
from IPython import display

from qm.qua import *

from importlib import reload
from qcrew.experiments.sample_B.imports import configuration as cfg
from qcrew.experiments.sample_B.imports import stage as stg
from qcrew.codebase.analysis.plot import plot_fit
from qcrew.codebase.analysis.qm_get_results import update_results
from qcrew.codebase.analysis.plot import FakeLivePlotter


from datetime import datetime, date
from pathlib import Path

STAGE_NAME = "sample_B"  # this is used to save experimental data to the correct folder
DAILY_SUBFOLDER = str(date.today())
DATA_FOLDER_PATH = Path().resolve() / "data" / STAGE_NAME / DAILY_SUBFOLDER
DATA_FOLDER_PATH.mkdir(parents=True, exist_ok=True)

test_var = 5

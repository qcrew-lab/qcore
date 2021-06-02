import matplotlib.pyplot as plt
import numpy as np
from importlib import reload
from qm.qua import *

from qcrew.experiments.sample_B.imports import configuration as cfg
from qcrew.experiments.sample_B.imports import stage as stg

from qcrew.experiments.sample_B.imports.stage import (
    STAGE_NAME,
    qubit,
    lb_qubit,
    rr,
    lb_rr,
    qmm,
    qm,
)

from datetime import datetime, date
from pathlib import Path

DAILY_SUBFOLDER = str(date.today())
DATA_FOLDER_PATH = Path.cwd() / "data" / STAGE_NAME / DAILY_SUBFOLDER
DATA_FOLDER_PATH.mkdir(parents=True, exist_ok=True)

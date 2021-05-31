import matplotlib.pyplot as plt
import numpy as np

from qm.qua import *

from qcrew.experiments.coax_test.imports.stage import (
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
DATA_FOLDER_PATH = Path().resolve() / "data" / STAGE_NAME / DAILY_SUBFOLDER
DATA_FOLDER_PATH.mkdir(parents=True, exist_ok=True)

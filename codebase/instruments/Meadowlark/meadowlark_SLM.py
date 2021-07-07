"""
Python driver for Meadowlark SLM.
"""
# --------------------------------- Imports ------------------------------------
from ctypes import (CDLL, c_int)
from pathlib import Path

# from instruments.instrument import Phy
#sicalInstrument

# --------------------------------- Driver -------------------------------------
DLL_NAME = 'Blink_C_wrapper.dll' # dll must be in the same directory as this driver
PATH_TO_DLL = Path(__file__).resolve().parent / DLL_NAME # returns Path object
MDL = CDLL(str(PATH_TO_DLL)) # cast Path to string

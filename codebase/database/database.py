"""
This module provides means of connecting to a QCoDeS database file and
initialising it. Note that connecting/initialisation take into account
database version and possibly perform database upgrades.
"""
import io
import time
import os
from dataset_hdf5 import Connection
from contextlib import contextmanager
from os.path import expanduser, normpath
from typing import Union, Iterator, Tuple, Optional
import qcodes as qc

from pathlib import Path
from hdf5_helper import DateTimeGenerator, DatabaseFile, validate

def connect(name: Union[str, Path], debug: bool = False,
            ) -> Connection:
    if isinstance(name, str):
        name = Path(name)
        return Connection(name, "a")
    else: 
        return Connection(name, "a")

def get_DB_location() -> str:
    return normpath(expanduser(qc.config["core"]["db_location"]))

def get_DB_debug() -> bool:
    return bool(qc.config["core"]["db_debug"])

def initialise_today_database_at(name: str, 
                                 path: Union[str,Path],
                                 timesubdir: bool = False, 
                                 timefilename: bool = False) -> Path:
    """ initialise the database in the date folder under the given main path.
    """
    conn = DatabaseFile(name=name, 
                        datadir =path,
                        timesubdir=timesubdir, 
                        timefilename = timefilename)
    db_location = Path(conn.filename)
    qc.config.core.db_location = db_location
    conn.close()
    return db_location

def initialise_existing_database_at(name: Optional[str], 
                                    path: Optional[Union[str,Path]],
                                    full_path: Optional[Union[str,Path]],
                                    date: Optional[str]) -> Path:
    if (full_path is not None) and (name is None) and (path is None):
       conn = Connection(full_path)
       qc.config.core.db_location = full_path
       conn.close()
    elif (full_path is None) and (name is not None) and (path is not None) (date is not None):
        subfolder = Path(validate(date))
        if name.endswith('.h5'):
            file_path = Path(path)/subfolder / name 
        else: 
            name = name + '.h5'
            file_path = Path(path)/subfolder / name
        conn = Connection(file_path)
        qc.config.core.db_location = file_path
        conn.close()
        return file_path
        
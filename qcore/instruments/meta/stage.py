"""
Encapsulates a measurement stage. The stage is a group of instruments needed to
run a given measurement. These instruments may be physical hardware (e.g. opx)
or may be meta-instruments (e.g. qubit, rr).

Instruments part of a stage must be unique Python objects, that is, no
duplicate instances can be added to stage.
"""
from pathlib import Path
import yaml

from instruments import Instrument, MetaInstrument, PhysicalInstrument

DEFAULT_STAGE_NAME = 'stage'

class Stage(MetaInstrument):
    """
    Contains two methods - enter and exit.
    Its parameters method is essentially the current 'snapshot' of its
    instruments.

    Job is to initialize instruments from a yaml config.

    Can be itself initialised from a yaml and written and saved into it, as it
    inherits from MetaInstrument. Initialising a stage this way has the added
    advantage that one does not need to call enter() explicitly!
    """
    def __init__(self, name: str=DEFAULT_STAGE_NAME, **instruments):
        self._instruments = instruments
        # check that kwargs are indeed Instrument objects
        for instrument in instruments.values():
            if not isinstance(instrument, Instrument):
                raise ValueError('Value of kwargs must be Instrument type')
        super().__init__(name=name, **instruments)

    @classmethod
    def load(cls, path):
        """
        Return instance of Stage from given path to yaml file.
        """
        with path.open(mode='r') as file:
            return yaml.safe_load(file)

    def enter(self, path: Path=None, paths: set[Path]=None,
              instrument: Instrument=None, instruments: set[Instrument]=None):
        """
        Add an instrument to stage. Make it available as an attribute.
        Accept -
        Path object to yaml file containing instrument config. In this case,
        the yaml needs to be parsed and the instruments therein need to be
        initialized.
        Instrument object (if physical, they are alr connected) or set of such
        instrument objects.
        """
        if path is not None:
            self._enter_by_path(path)
        if paths is not None:
            for path_ in paths:
                self._enter_by_path(path_)
        if instrument is not None:
            self._add_instrument(instrument)
        if instruments is not None:
            for instrument_ in instruments:
                self._add_instrument(instrument_)

    def _enter_by_path(self, path):
        with open(path, 'r') as file:
            instr_generator = yaml.safe_load_all(file)
            for instrument in instr_generator:
                if isinstance(instrument, Instrument):
                    self._add_instrument(instrument)
                else:
                    # TODO proper error handling
                    print('You are adding a non-instrument to stage... WTF')

    def _add_instrument(self, instrument):
        if not isinstance(instrument, Instrument):
            print('Cannot add a non-Instrument type to stage... wtf')
            return

        if instrument in self._instruments.values():
            print('This instrument already exists on the stage... wtf')
        elif instrument.name in self._instruments:
            print('Instrument with this name alr exists on the stage... wtf')
        else:
            self._instruments[instrument.name] = instrument
            setattr(self, instrument.name, instrument)

    def exit(self, instrument: Instrument=None, exit_all: bool=False):
        """
        Remove instrument from stage AND disconnect it if it is a physical
        instrument. Delete attribute too. Option to exit all instruments and
        reset stage.
        """
        if exit_all:
            for instr_name in self._instruments:
                delattr(self, instr_name)
                instrument_ = self._instruments[instr_name]
                if isinstance(instrument_, PhysicalInstrument):
                    instrument_.disconnect()
            self._instruments = dict()
            return

        # TODO catch error if instrument is None
        if instrument in self._instruments.values():
            if isinstance(instrument, PhysicalInstrument):
                instrument.disconnect()
            del self._instruments[instrument.name]
            delattr(self, instrument.name)
        else:
            print('This instrument is not even part of the stage wot u doin ?!')

    @property # parameters getter
    def parameters(self):
        """
        Dict where key is instrument name, value is instrument.parameters. Each
        instrument has the responsibility of presenting its own updated
        parameters.
        """
        parameters = dict()
        for instrument in self._instruments.values():
            parameters[instrument.name] = instrument.parameters
        return parameters

    def _create_yaml_map(self):
        yaml_map = dict()
        yaml_map['name'] = self._name
        # call parameters getter for latest values
        yaml_map.update(self._instruments)
        return yaml_map

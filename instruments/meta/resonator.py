"""
Encapsulates a resonator.
"""
# --------------------------------- Imports ------------------------------------
from instruments.instrument import MetaInstrument

# ------------------------------- Parameters -----------------------------------
# parameter names
LO_FREQ = 'lo_freq'

# parameter default values
DEFAULT_LO_FREQ = 8e9

# ----------------------------- Default config ---------------------------------
DEFAULT_CONFIG = {
    DEFAULT_LO_FREQ: DEFAULT_LO_FREQ
}

class Resonator(MetaInstrument):
    """
    Encapsulates a resonator.

    Includes properties to facilitate easy getting and setting.
    """
    def __init__(self, name: str, config: dict=None):
        super().__init__(name=name)
        self._create_parameters(config)

    def _create_parameters(self, config):
        init_config = DEFAULT_CONFIG if config is None else config
        self._parameters = dict()

        for key, value in init_config:
            self.create_parameter(name=key, value=value, unit='Hz')

    @property # lo_freq getter
    def lo_freq(self):
        return self._parameters[LO_FREQ].value

    @lo_freq.setter
    def lo_freq(self, new_lo_freq):
        self._parameters[LO_FREQ].value = new_lo_freq

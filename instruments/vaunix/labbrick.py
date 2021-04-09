"""
Python driver for Vaunix Signal Generator LMS (LabBrick).
"""
# --------------------------------- Imports ------------------------------------
from ctypes import (CDLL, c_int)
from pathlib import Path

from instruments.instrument import MetaInstrument, PhysicalInstrument
from parameter import Parameter

# --------------------------------- Driver -------------------------------------
DLL_NAME = 'vnx_fmsynth.dll' # dll must be in the same directory as this driver
PATH_TO_DLL = Path(__file__).resolve().parent / DLL_NAME # returns Path object
VNX = CDLL(str(PATH_TO_DLL)) # cast Path to string

# --------------------------------- Globals ------------------------------------
IS_TEST_MODE = False # we are using actual hardware
USE_INTERNAL_REF = False # we are using an external timebase
RF_ON = True
RF_OFF = False
FREQ_SCALAR = 10 # frequency is encoded as an integer of 10Hz steps
POW_SCALAR = 0.25 # power level is encoded as an integer of 0.25dB steps

# --------------------------------- Mappings -----------------------------------
close_device = VNX.fnLMS_CloseDevice
connect_to_device = VNX.fnLMS_InitDevice
get_devices_info = VNX.fnLMS_GetDevInfo
get_frequency = VNX.fnLMS_GetFrequency
get_max_frequency = VNX.fnLMS_GetMaxFreq
get_max_power = VNX.fnLMS_GetMaxPwr
get_min_frequency = VNX.fnLMS_GetMinFreq
get_min_power = VNX.fnLMS_GetMinPwr
get_num_connected_devices = VNX.fnLMS_GetNumDevices
get_power = VNX.fnLMS_GetPowerLevel
get_serial_numbers = VNX.fnLMS_GetSerialNumber
set_frequency = VNX.fnLMS_SetFrequency
set_power_level = VNX.fnLMS_SetPowerLevel
set_rf_on = VNX.fnLMS_SetRFOn
set_test_mode = VNX.fnLMS_SetTestMode
set_use_internal_reference = VNX.fnLMS_SetUseInternalRef

# ------------------------------- Parameters -----------------------------------
# parameter names
NAME = 'name' # gettable
SERIAL_NUMBER = 'serial_number' # gettable
ELEMENT = 'element' # gettable
FREQUENCY = 'frequency' # gettable and settable
POWER = 'power' # gettable and settable

# parameter default values
DEFAULT_FREQUENCY = 5e9 
DEFAULT_POWER = -140

# ---------------------------------- Class -------------------------------------
class LabBrick(PhysicalInstrument):
    """
    TODO write class docstring.
    Has element as it functions as the element's LO. Updates element's LO freq
    whenever frequency is updated.
    """
    def __init__(self, name: str, serial_number: int,
                 element: MetaInstrument=None, frequency: float=None,
                 power: int=DEFAULT_POWER):
        # TODO use try catch block in case device not authenticated
        print('Trying to initialize ' + name)
        self._device_handle = self._connect(serial_number)
        super().__init__(name=name, identifier=serial_number)
        self._element = element
        self._create_parameters(frequency, power)
        self._initialize()

    def _create_yaml_map(self):
        # TODO can we ensure the map adheres to constructor without hard coding?
        yaml_map = {NAME: self._name,
                    SERIAL_NUMBER: self._identifier,
                    ELEMENT: self._element,
                    FREQUENCY: self._frequency.value,
                    POWER: self._power.value
                    }
        return yaml_map

    def _connect(self, serial_number: int):
        set_test_mode(IS_TEST_MODE) # use a real LabBrick, not a simulated one

        # find serial numbers of all available labbricks
        num_devices = get_num_connected_devices()
        active_device_array = (c_int * num_devices)() # initialize the array
        get_devices_info(active_device_array) # fill the array with info
        serial_numbers = [get_serial_numbers(active_device_array[i])
               for i in range(num_devices)]

        # TODO error handling and proper logging
        # connect to device and return device handle if available
        if serial_number in serial_numbers:
            device_idx = serial_numbers.index(serial_number)
            device_handle = active_device_array[device_idx]
            connect_to_device(device_handle)
            print('Connnected to LabBrick ' + str(serial_number))
            return device_handle
        else:
            print('Failed to connect to LabBrick.')

    def _create_parameters(self, frequency, power):
        print('creating parameters...')
        self._parameters = dict()

        init_freq = self._element.lo_freq if frequency is None else frequency
        self.create_parameter(name=FREQUENCY, value=init_freq, unit='Hz')
        self.create_parameter(name=POWER, value=power, unit='dBm')

        self._frequency = self._parameters[FREQUENCY]
        self._frequency.value = self._element.lo_freq.value
        self._power = self._parameters[POWER]

    def _initialize(self):
        print('Initializing device...')
        # always use external 10MHz reference
        set_use_internal_reference(self._device_handle, USE_INTERNAL_REF)

        # update maximum and minimum frequency and power for this labbrick
        self._update_frequency_bounds()
        self._update_power_bounds()

        # start labbrick at the initial frequency and power level
        self.frequency = (DEFAULT_FREQUENCY if self._frequency.value is None
                          else self._frequency.value)
        self.power = self._power.value
        set_rf_on(self._device_handle, RF_ON)

    def disconnect(self):
        print('disconnecting device...')
        set_rf_on(self._device_handle, RF_OFF)
        close_device(self._device_handle)

    def _update_frequency_bounds(self):
        min_freq = get_min_frequency(self._device_handle) * FREQ_SCALAR
        self._frequency.minimum = min_freq
        max_freq = get_max_frequency(self._device_handle) * FREQ_SCALAR
        self._frequency.maximum = max_freq

    def _update_power_bounds(self):
        min_pow = get_min_power(self._device_handle) * POW_SCALAR
        self._power.minimum = min_pow
        max_pow = get_max_power(self._device_handle) * POW_SCALAR
        self._frequency.maximum = max_pow

    @property # frequency getter
    def frequency(self):
        # TODO add logging and error handling
        current_freq = get_frequency(self._device_handle) * FREQ_SCALAR * 1.0
        print('Current freq is {:.2E}'.format(current_freq))
        return current_freq

    @frequency.setter
    def frequency(self, new_frequency: float):
        if self._frequency.minimum <= new_frequency <= self._frequency.maximum:
            freq_steps = int(new_frequency / FREQ_SCALAR)
            set_frequency(self._device_handle, freq_steps)
            # TODO make setter for element lo freq and check for None
            self._frequency.value = self._element.lo_freq = new_frequency
            print('Successfully set frequency to '
                  + '{:.2E}'.format(new_frequency))
        else:
            print('Failed to set frequency - out of bounds')

    @property # power getter
    def power(self):
        power_level = get_power(self._device_handle)
        max_power = self._power.maximum
        current_power = max_power - (power_level * POW_SCALAR)
        self._power.value = current_power
        print('Current power is {}'.format(current_power))
        return current_power

    @power.setter
    def power(self, new_power: int):
        if self._power.minimum <= new_power <= self._power.maximum:
            power_level = int(new_power / POW_SCALAR)
            set_power_level(self._device_handle, power_level)
            self._power.value = new_power
            print('Successfully set power to '
                  + '{0:{1}}'.format(new_power, '+' if new_power else ''))
        else:
            print('Failed to set power - out of bounds')

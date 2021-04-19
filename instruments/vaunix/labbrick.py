"""
Python driver for Vaunix Signal Generator LMS (LabBrick).
"""
# --------------------------------- Imports ------------------------------------
from ctypes import (CDLL, c_int)
from pathlib import Path

from instruments.instrument import PhysicalInstrument

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

# ----------------------- Constructor argument names ---------------------------
NAME = 'name' # gettable
SERIAL_NUMBER = 'serial_number' # gettable
FREQUENCY = 'frequency' # gettable and settable
POWER = 'power' # gettable and settable

# ---------------------------------- Class -------------------------------------
# pylint: disable=too-many-instance-attributes
# we recognize this as a code smell and in a future implementation will address
# this by making frequency and power a Parameter type with max & min attributes.
class LabBrick(PhysicalInstrument):
    """
    TODO write class docstring.
    """
    def __init__(self, name: str, serial_number: int, frequency: float,
                 power: int):
        print('Trying to initialize ' + name)
        self._device_handle = self._connect(serial_number)
        super().__init__(name=name, uid=serial_number)

        if frequency is None or power is None:
            raise RuntimeError('initial freq and power cannot be None type...')

        self._frequency = frequency
        self._min_freq = None # will be updated in _initialize()
        self._max_freq = None # will be updated in _initialize()

        self._power = power
        self._min_pow = None # will be updated in _initialize()
        self._max_pow = None # will be updated in _initialize()
        self._initialize()

    def _create_yaml_map(self):
        yaml_map = {NAME: self._name,
                    SERIAL_NUMBER: self._uid
                    }
        yaml_map.update(self.parameters)
        return yaml_map

    def _connect(self, uid: int):
        set_test_mode(IS_TEST_MODE) # use a real LabBrick, not a simulated one

        # find serial numbers of all available labbricks
        num_devices = get_num_connected_devices()
        active_device_array = (c_int * num_devices)() # initialize the array
        get_devices_info(active_device_array) # fill the array with info
        serial_numbers = [get_serial_numbers(active_device_array[i])
               for i in range(num_devices)]

        # TODO proper error handling and logging
        # connect to device and return device handle if available
        if uid in serial_numbers:
            device_idx = serial_numbers.index(uid)
            device_handle = active_device_array[device_idx]
            connect_to_device(device_handle)
            print('Connnected to LabBrick ' + str(uid))
            return device_handle

        raise RuntimeError('Failed to connect to LabBrick.')

    def _initialize(self):
        print('Setting initial parameters...')
        # always use external 10MHz reference
        set_use_internal_reference(self._device_handle, USE_INTERNAL_REF)

        # update maximum and minimum frequency and power for this labbrick
        self._update_frequency_bounds()
        self._update_power_bounds()

        # set labbrick at initial frequency and power level
        self.frequency = self._frequency
        self.power = self._power
        set_rf_on(self._device_handle, RF_ON)

        print('LabBrick is ready to use.')

    def _update_frequency_bounds(self):
        self._min_freq = get_min_frequency(self._device_handle) * FREQ_SCALAR
        self._max_freq = get_max_frequency(self._device_handle) * FREQ_SCALAR

    def _update_power_bounds(self):
        self._min_pow = get_min_power(self._device_handle) * POW_SCALAR
        self._max_pow = get_max_power(self._device_handle) * POW_SCALAR

    @property # frequency getter
    def frequency(self):
        """Get current freq from device.

        Returns:
            [float]: current freq
        """
        # TODO add logging and error handling
        current_freq = get_frequency(self._device_handle) * FREQ_SCALAR * 1.0
        self._frequency = current_freq # just to make sure its up to date
        print('Current freq is {:.2E}'.format(current_freq))
        return current_freq

    @frequency.setter
    def frequency(self, new_frequency: float):
        """set new freq on device (must be within bounds)

        Args:
            new_frequency (float): new freq to set
        """
        if self._min_freq <= new_frequency <= self._max_freq:
            freq_steps = int(new_frequency / FREQ_SCALAR)
            set_frequency(self._device_handle, freq_steps)
            self._frequency = new_frequency
            print('Successfully set frequency to '
                  + '{:.2E}'.format(new_frequency))
        else:
            print('Failed to set frequency - out of bounds')

    @property # power getter
    def power(self):
        """get current power from device

        Returns:
            [int]: current power
        """
        power_level = get_power(self._device_handle)
        current_power = int(self._max_pow - (power_level * POW_SCALAR))
        self._power = current_power # just to make sure its up to date
        print('Current power is {}'.format(current_power))
        return current_power

    @power.setter
    def power(self, new_power: int):
        """set power on device (must be within bounds)

        Args:
            new_power (int): new power to set
        """
        if self._min_pow <= new_power <= self._max_pow:
            power_level = int(new_power / POW_SCALAR)
            set_power_level(self._device_handle, power_level)
            self._power = new_power
            print('Successfully set power to '
                  + '{0:{1}}'.format(new_power, '+' if new_power else ''))
        else:
            print('Failed to set power - out of bounds')

    @property # parameters getter
    def parameters(self):
        """get current snapshot of device.

        Returns:
            [dict]: current freq and power on device
        """
        return {
            FREQUENCY: self.frequency,
            POWER: self.power
            }

    def disconnect(self):
        set_rf_on(self._device_handle, RF_OFF)
        close_device(self._device_handle)
        print('device disconnected')

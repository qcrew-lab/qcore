"""
Python driver for Signal Hound USB-SA124B spectrum analyser.

Based on the API provided by the vendor.

Currently, this driver only supports swept analysis mode, that is, frequency
domain sweeps. A frequency domain sweep displays amplitude on the vertical axis
and frequency on the horizontal axis.
"""
# --------------------------------- Imports ------------------------------------
import numpy as np

from instruments.instrument import PhysicalInstrument
from instruments.signal_hound.sa_api import (
    SA_AVERAGE, SA_FALSE, SA_IDLE, SA_LOG_SCALE, SA_LOG_UNITS,
    SA_RBW_SHAPE_FLATTOP, SA_REF_EXTERNAL_IN, SA_SWEEPING, SA_TRUE,
    sa_close_device, sa_config_acquisition, sa_config_center_span,
    sa_config_level, sa_config_proc_units, sa_config_RBW_shape,
    sa_config_sweep_coupling, sa_get_sweep_64f, sa_initiate,
    sa_open_device_by_serial, sa_query_sweep_info, sa_set_timebase)

# ----------------------------------- Globals ----------------------------------
# detector parameter decides if overlapping results from signal processing
# should be averaged (`SA_AVERAGE`) or if minimum and maximum values should be
# maintained (`SA_MIN_MAX`)
DETECTOR = SA_AVERAGE

# scale parameter changes units of returned amplitudes. Use `SA_LOG_SCALE` for
# dBm, `SA_LIN_SCALE` for millivolts, `SA_LOG_FULL_SCALE` and
# `SA_LIN_FULL_SCALE` for amplitudes to be returned from the full scale input
SCALE = SA_LOG_SCALE

# Specify the RBW filter shape, which is achieved by changing the window
# function. When specifying SA_RBW_SHAPE_FLATTOP, a custom bandwidth flat-top
# window is used measured at the 3dB cutoff point. When specifying
# SA_RBW_SHAPE_CISPR, a Gaussian window with zero-padding is used to achieve
# the specified RBW. The Gaussian window is measured at the 6dB cutoff point.
RBW_SHAPE = SA_RBW_SHAPE_FLATTOP

# specify units for video processing. For “average power” measurements,
# SA_POWER_UNITS should be selected. For cleaning up an amplitude modulated
# signal, SA_VOLT_UNITS would be a good choice. To emulate a traditional
# spectrum analyzer, select SA_LOG_UNITS. To minimize processing power and
# bypass video bandwidth processing, select SA_BYPASS.
VID_PROCESSING_UNITS = SA_LOG_UNITS

# image reject determines whether software image reject will be performed.
# generally, set reject to true for continuous signals, and false to catch
# short duration signals at a known frequency.
DOES_IMAGE_REJECT = SA_TRUE

# ------------------------------- Parameters -----------------------------------
NAME = 'name' # gettable
SERIAL_NUMBER = 'serial_number' # gettable

# frequency sweep center in Hz
CENTER = 'center' # gettable and settable

# frequency sweep span in Hz
SPAN = 'span' # gettable and settable

# resolution bandwidth in Hz. Available values are [0.1Hz-100kHz], 250kHz, 6MHz.
# see _is_valid_rbw() for exceptions to available values.
# definition: amplitude value for each frequency bin represents total energy
# from rbw / 2 below and above the bin's center. 
RBW = 'rbw' # gettable and settable

# reference power level of device in dBm.
# set it at or slightly about your expected input power for best sensitivity.
REF_POWER = 'ref_power' # gettable and settable

PARAMETERS = 'parameters' # gettable
DEFAULT_PARAMETERS = {
    CENTER: 8e9,
    SPAN: 2e9,
    RBW: 250e3,
    REF_POWER: 0
}

# ---------------------------------- Class -------------------------------------
class Sa124(PhysicalInstrument):
    """
    SA124. TODO - WRITE CLASS DOCU
    """
    def __init__(self, name: str, serial_number: int, parameters: dict=None):
        # TODO use try catch block in case device not authenticated
        print('Trying to initialize ' + name)
        self._device_handle = self._connect(serial_number)
        super().__init__(name=name, identifier=serial_number)
        self._create_parameters(parameters)
        self._initialize()

    def _create_yaml_map(self):
        # TODO can we ensure the map adheres to constructor without hard coding?
        yaml_map = {NAME: self._name,
                    SERIAL_NUMBER: self._identifier,
                    PARAMETERS: self._parameters
                    }
        return yaml_map

    def _connect(self, serial_number: int):
        # throw error if device with given serial number is already open
        try:
            return sa_open_device_by_serial(serial_number)['handle']
        except NameError:
            print('WARNING: Device was already open')
            print('Closing and reinitializing it. Use configure_sweep() to'
                  + 'change sweep parameters instead of __init__()')
            # TODO THIS ERROR HANDLING IS VERY HACKY, NEED TO IMPROVE
            sa_close_device(0) # we own one SA, which is always assigned 0
            return sa_open_device_by_serial(serial_number)['handle']

    def _create_parameters(self, parameters):
        # TODO find a way to remove hard coding - is that desirable?
        print('Connnected to SA124B ' + str(self._identifier))
        print('creating parameters...')

        if parameters is None:
            self._parameters = DEFAULT_PARAMETERS
            print('no parameters supplied, setting default values...')
        else:
            self._parameters = parameters
            print('parameters found!')

        self._center = self._parameters[CENTER]
        self._span = self._parameters[SPAN]
        self._rbw = self._parameters[RBW]
        self._ref_power = self._parameters[REF_POWER]
        print('created parameters: ')
        print(self._parameters)

    def _initialize(self):
        # this group of settings is set to global default values
        # always use external 10MHz reference
        sa_set_timebase(self._device_handle, SA_REF_EXTERNAL_IN)
        # configure acquisition settings
        sa_config_acquisition(self._device_handle, DETECTOR, SCALE)
        # configure rbw filter shape
        sa_config_RBW_shape(self._device_handle, RBW_SHAPE)
        # configure video processing unit type
        sa_config_proc_units(self._device_handle, VID_PROCESSING_UNITS)

        # sweep parameters are set to user defined values, if given
        # else set to default values
        self.configure_sweep(center=self._center, span=self._span,
                             rbw=self._rbw, ref_power=self._ref_power)

    def _is_valid_rbw(self, rbw: float):
        # TODO remove hard coding, do proper logging and error handling, DRY
        start_freq = self._center - (self._span / 2)

        # these two conditions are obtained from the manual
        if ((self._span >= 100e6 or (self._span > 200e3 and start_freq < 16e6))
            and rbw < 6.5e3):
            is_valid_rbw = False
        elif ((0.1 <= rbw <= 100e3) or (rbw == 250e3) or
              (rbw == 6e6 and start_freq >= 200e6 and self._span >= 200e6)):
            is_valid_rbw = True
        else:
            is_valid_rbw = False

        if not is_valid_rbw:
            print('Bad RBW value given, default to{:.2E}.'
                  .format(DEFAULT_PARAMETERS[RBW]))

        return is_valid_rbw

    def configure_sweep(self, center: float=DEFAULT_PARAMETERS[CENTER],
                        span: float=DEFAULT_PARAMETERS[SPAN],
                        rbw: float=DEFAULT_PARAMETERS[RBW],
                        ref_power: float=DEFAULT_PARAMETERS[REF_POWER]):
        # device must be in idle mode before it is configured
        # the third argument is an inconsequential flag that can be ignored
        sa_initiate(self._device_handle, SA_IDLE, SA_FALSE)

        sa_config_center_span(self._device_handle, center, span)
        new_rbw = rbw if self._is_valid_rbw(rbw) else DEFAULT_PARAMETERS[RBW]
        sa_config_sweep_coupling(self._device_handle, new_rbw, new_rbw,
                                 DOES_IMAGE_REJECT)
        sa_config_level(self._device_handle, ref_power)

        # device is ready to sweep
        sa_initiate(self._device_handle, SA_SWEEPING, SA_FALSE)

        # update internal parameters
        self._center = center
        self._span = span
        self._rbw = new_rbw
        self._ref_power = ref_power

        print('Configured sweep! Sweep info: ')
        print(self.sweep_info)

    @property # sweep info getter
    def sweep_info(self):
        sweep_parameters = self._parameters
        more_sweep_parameters = sa_query_sweep_info(self._device_handle)
        return {**sweep_parameters, **more_sweep_parameters}

    def sweep(self):
        # TODO logging
        # error handling in case device is not initialised
        sweep_info = sa_query_sweep_info(self._device_handle)
        frequencies = [sweep_info['start_freq'] + i * sweep_info['bin_size']
                                for i in range(sweep_info['sweep_length'])]
        amplitudes = sa_get_sweep_64f(self._device_handle)['max']
        return (np.array(frequencies), np.array(amplitudes))

    def disconnect(self):
        sa_close_device(self._device_handle)

    @property # parameters getter
    def parameters(self):
        print('.' + CENTER + ' (GET and SET)')
        print('.' + SPAN + ' (GET and SET)')
        print('.' + RBW + ' (GET and SET)')
        print('.' + REF_POWER + ' (GET and SET)')
        return self._parameters

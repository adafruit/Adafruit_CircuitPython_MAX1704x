# SPDX-FileCopyrightText: 2017 Scott Shawcroft, written for Adafruit Industries
# SPDX-FileCopyrightText: Copyright (c) 2022 ladyada for Adafruit Industries
#
# SPDX-License-Identifier: MIT
"""
`adafruit_max1704x`
================================================================================

MAX17048 or MAX17049 battery fuel gauge library


* Author(s): ladyada

Implementation Notes
--------------------

**Hardware:**

* `Adafruit MAX17048 Battery Fuel Gauge <https://www.adafruit.com/product/5580>`

**Software and Dependencies:**

* Adafruit CircuitPython firmware for the supported boards:
  https://circuitpython.org/downloads
* Adafruit's Bus Device library: https://github.com/adafruit/Adafruit_CircuitPython_BusDevice
* Adafruit's Register library: https://github.com/adafruit/Adafruit_CircuitPython_Register
"""

import time
from micropython import const
from adafruit_bus_device import i2c_device
from adafruit_register.i2c_struct import ROUnaryStruct, UnaryStruct
from adafruit_register.i2c_bit import RWBit, ROBit

__version__ = "0.0.0-auto.0"
__repo__ = "https://github.com/adafruit/Adafruit_CircuitPython_MAX1704x.git"

MAX1704X_I2CADDR_DEFAULT: int = const(0x36)  # Default I2C address

_MAX1704X_VCELL_REG = const(0x02)
_MAX1704X_SOC_REG = const(0x04)
_MAX1704X_MODE_REG = const(0x06)
_MAX1704X_VERSION_REG = const(0x08)
_MAX1704X_HIBRT_REG = const(0x0A)
_MAX1704X_CONFIG_REG = const(0x0C)
_MAX1704X_VALERT_REG = const(0x14)
_MAX1704X_CRATE_REG = const(0x16)
_MAX1704X_VRESET_REG = const(0x18)
_MAX1704X_CHIPID_REG = const(0x19)
_MAX1704X_STATUS_REG = const(0x1A)
_MAX1704X_CMD_REG = const(0xFE)

class MAX17048:
    """Driver for the MAX1704X battery fuel gauge.
    :param ~busio.I2C i2c_bus: The I2C bus the MAX1704X is connected to.
    :param address: The I2C device address. Defaults to :const:`0x36`
    """

    chip_version = ROUnaryStruct(_MAX1704X_VERSION_REG, ">H")
    _config = ROUnaryStruct(_MAX1704X_CONFIG_REG, ">H")
    _cmd = UnaryStruct(_MAX1704X_CMD_REG, ">H")
    _status = ROUnaryStruct(_MAX1704X_STATUS_REG, ">B")
    _cell_voltage = ROUnaryStruct(_MAX1704X_VCELL_REG, ">H")
    _cell_SOC = ROUnaryStruct(_MAX1704X_SOC_REG, ">B")
    _hibrt_actthr = UnaryStruct(_MAX1704X_HIBRT_REG+1, ">B")
    _hibrt_hibthr = UnaryStruct(_MAX1704X_HIBRT_REG, ">B")
    # expose the alert bits
    reset_alert = ROBit(_MAX1704X_STATUS_REG, 0)
    voltage_high_alert = ROBit(_MAX1704X_STATUS_REG, 1)
    voltage_low_alert = ROBit(_MAX1704X_STATUS_REG, 2)
    voltage_reset_alert = ROBit(_MAX1704X_STATUS_REG, 3)
    SOC_change_alert = ROBit(_MAX1704X_STATUS_REG, 5)

    chip_id = ROUnaryStruct(_MAX1704X_CHIPID_REG, ">B")
    
    def __init__(self, i2c_bus, address=MAX1704X_I2CADDR_DEFAULT):
        # pylint: disable=no-member
        self.i2c_device = i2c_device.I2CDevice(i2c_bus, address)

        if self.chip_version & 0xFFF0 != 0x0010:
            raise RuntimeError("Failed to find MAX1704X - check your wiring!")
        self.reset()

    def reset(self):
        try:
            self._cmd = 0x5400    
        except OSError:
            # aha! we NACKed, which is CORRECT!
            return self.reset_alert # we should have reset
        raise RuntimeException("Reset did not succeed")

    @property
    def cell_voltage(self):
        return self._cell_voltage * 78.125 / 1_000_000

    @property
    def cell_percent(self):
        return self._cell_SOC

    @property
    def activity_threshold(self):
        return self._hibrt_actthr * 0.00125  # 1.25mV per LSB

    @activity_threshold.setter
    def activity_threshold(self, threshold_voltage):
        if (not 0 <= threshold_voltage <= (255 * 0.00125)):
            raise ValueError("Activity voltage change must be between 0 and 0.31875 Volts")
        self._hibrt_actthr  = int(threshold_voltage / 0.00125) # 1.25mV per LSB


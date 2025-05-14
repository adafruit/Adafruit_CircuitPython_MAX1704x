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

* `Adafruit MAX17048 Battery Fuel Gauge <https://www.adafruit.com/product/5580>`_

**Software and Dependencies:**

* Adafruit CircuitPython firmware for the supported boards:
  https://circuitpython.org/downloads
* Adafruit's Bus Device library: https://github.com/adafruit/Adafruit_CircuitPython_BusDevice
* Adafruit's Register library: https://github.com/adafruit/Adafruit_CircuitPython_Register
"""

from adafruit_bus_device import i2c_device
from adafruit_register.i2c_bit import ROBit, RWBit
from adafruit_register.i2c_bits import RWBits
from adafruit_register.i2c_struct import ROUnaryStruct, UnaryStruct
from micropython import const

try:
    from busio import I2C
except ImportError:
    pass

__version__ = "0.0.0+auto.0"
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

ALERTFLAG_SOC_CHANGE = 0x20
ALERTFLAG_SOC_LOW = 0x10
ALERTFLAG_VOLTAGE_RESET = 0x08
ALERTFLAG_VOLTAGE_LOW = 0x04
ALERTFLAG_VOLTAGE_HIGH = 0x02
ALERTFLAG_RESET_INDICATOR = 0x01


class MAX17048:
    """Driver for the MAX1704X battery fuel gauge.
    :param ~busio.I2C i2c_bus: The I2C bus the MAX1704X is connected to.
    :param address: The I2C device address. Defaults to :const:`0x36`
    """

    chip_version = ROUnaryStruct(_MAX1704X_VERSION_REG, ">H")
    chip_id = ROUnaryStruct(_MAX1704X_CHIPID_REG, ">B")

    _config = ROUnaryStruct(_MAX1704X_CONFIG_REG, ">H")
    # expose the config bits
    sleep = RWBit(_MAX1704X_CONFIG_REG + 1, 7, register_width=2, lsb_first=False)
    _alert_status = RWBit(_MAX1704X_CONFIG_REG + 1, 5, register_width=2, lsb_first=False)
    enable_sleep = RWBit(_MAX1704X_MODE_REG, 5)
    hibernating = ROBit(_MAX1704X_MODE_REG, 4)
    quick_start = RWBit(_MAX1704X_MODE_REG, 6)

    _cmd = UnaryStruct(_MAX1704X_CMD_REG, ">H")
    _status = ROUnaryStruct(_MAX1704X_STATUS_REG, ">B")
    _cell_voltage = ROUnaryStruct(_MAX1704X_VCELL_REG, ">H")
    _cell_SOC = ROUnaryStruct(_MAX1704X_SOC_REG, ">H")
    _cell_crate = ROUnaryStruct(_MAX1704X_CRATE_REG, ">h")
    _vreset = ROUnaryStruct(_MAX1704X_VRESET_REG, ">B")
    _hibrt_actthr = UnaryStruct(_MAX1704X_HIBRT_REG + 1, ">B")
    _hibrt_hibthr = UnaryStruct(_MAX1704X_HIBRT_REG, ">B")
    _valrt_min = UnaryStruct(_MAX1704X_VALERT_REG, ">B")
    _valrt_max = UnaryStruct(_MAX1704X_VALERT_REG + 1, ">B")

    # expose the alert bits
    reset_alert = RWBit(_MAX1704X_STATUS_REG, 0)
    voltage_high_alert = RWBit(_MAX1704X_STATUS_REG, 1)
    voltage_low_alert = RWBit(_MAX1704X_STATUS_REG, 2)
    voltage_reset_alert = RWBit(_MAX1704X_STATUS_REG, 3)
    SOC_low_alert = RWBit(_MAX1704X_STATUS_REG, 4)
    SOC_change_alert = RWBit(_MAX1704X_STATUS_REG, 5)

    _reset_voltage = RWBits(7, _MAX1704X_VRESET_REG, 1)
    comparator_disabled = RWBit(_MAX1704X_VRESET_REG, 0)

    def __init__(self, i2c_bus: I2C, address: int = MAX1704X_I2CADDR_DEFAULT) -> None:
        self.i2c_device = i2c_device.I2CDevice(i2c_bus, address)

        if self.chip_version & 0xFFF0 != 0x0010:
            raise RuntimeError("Failed to find MAX1704X - check your wiring!")
        self.reset()
        self.enable_sleep = False
        self.sleep = False

    def reset(self) -> None:
        """Perform a soft reset of the chip"""
        try:
            self._cmd = 0x5400
        except OSError:
            # aha! we NACKed, which is CORRECT!
            pass
        else:
            raise RuntimeError("Reset did not succeed")
        for _ in range(3):
            try:
                self.reset_alert = False  # clean up RI alert
                return
            except OSError:
                # With CircuitPython 8.0.0-beta.6 and ESP32-S3, the first
                # attempt to reset the alert fails.
                continue
        raise RuntimeError("Clearing reset alert did not succeed")

    @property
    def cell_voltage(self) -> float:
        """The state of charge of the battery, in volts"""
        return self._cell_voltage * 78.125 / 1_000_000

    @property
    def cell_percent(self) -> float:
        """The state of charge of the battery, in percentage of 'fullness'"""
        return self._cell_SOC / 256.0

    @property
    def charge_rate(self) -> float:
        """Charge or discharge rate of the battery in percent/hour"""
        return self._cell_crate * 0.208

    @property
    def reset_voltage(self) -> float:
        """The voltage that will determine whether the chip will consider it a reset/swap"""
        return self._reset_voltage * 0.04  # 40mV / LSB

    @reset_voltage.setter
    def reset_voltage(self, reset_v: float) -> None:
        if not 0 <= reset_v <= (127 * 0.04):
            raise ValueError("Reset voltage must be between 0 and 5.1 Volts")
        self._reset_voltage = int(reset_v / 0.04)  # 40mV / LSB

    @property
    def voltage_alert_min(self) -> float:
        """The lower-limit voltage for the voltage alert"""
        return self._valrt_min * 0.02  # 20mV / LSB

    @voltage_alert_min.setter
    def voltage_alert_min(self, minvoltage: float) -> None:
        if not 0 <= minvoltage <= (255 * 0.02):
            raise ValueError("Alert voltage must be between 0 and 5.1 Volts")
        self._valrt_min = int(minvoltage / 0.02)  # 20mV / LSB

    @property
    def voltage_alert_max(self) -> float:
        """The upper-limit voltage for the voltage alert"""
        return self._valrt_max * 0.02  # 20mV / LSB

    @voltage_alert_max.setter
    def voltage_alert_max(self, maxvoltage: float) -> None:
        if not 0 <= maxvoltage <= (255 * 0.02):
            raise ValueError("Alert voltage must be between 0 and 5.1 Volts")
        self._valrt_max = int(maxvoltage / 0.02)  # 20mV / LSB

    @property
    def active_alert(self) -> bool:
        """Whether there is an active alert to be checked"""
        return self._alert_status

    @property
    def alert_reason(self) -> int:
        """The 7 bits of alert-status that can be checked at once for flags"""
        return self._status & 0x3F

    @property
    def activity_threshold(self) -> float:
        """The absolute change in battery voltage that will trigger hibernation"""
        return self._hibrt_actthr * 0.00125  # 1.25mV per LSB

    @activity_threshold.setter
    def activity_threshold(self, threshold_voltage: float) -> None:
        if not 0 <= threshold_voltage <= (255 * 0.00125):
            raise ValueError("Activity voltage change must be between 0 and 0.31875 Volts")
        self._hibrt_actthr = int(threshold_voltage / 0.00125)  # 1.25mV per LSB

    @property
    def hibernation_threshold(self) -> float:
        """The absolute-value percent-per-hour change in charge rate
        that will trigger hibernation"""
        return self._hibrt_hibthr * 0.208  # 0.208% per hour

    @hibernation_threshold.setter
    def hibernation_threshold(self, threshold_percent: float) -> None:
        if not 0 <= threshold_percent <= (255 * 0.208):
            raise ValueError("Activity percentage/hour change must be between 0 and 53%")
        self._hibrt_hibthr = int(threshold_percent / 0.208)  # 0.208% per hour

    def hibernate(self) -> None:
        """Setup thresholds for hibernation to go into hibernation mode immediately.

        See datasheet: HIBRT Register (0x0A) To disable hibernate mode, set
        HIBRT = 0x0000. To always use hibernate mode, set HIBRT = 0xFFFF.
        Can check status with :py:attr:`hibernating`
        """

        self._hibrt_hibthr = 0xFF
        self._hibrt_actthr = 0xFF

    def wake(self) -> None:
        """Setup thresholds for hibernation to leave hibernation mode immediately.

        See datasheet: HIBRT Register (0x0A) To disable hibernate mode, set
        HIBRT = 0x0000. To always use hibernate mode, set HIBRT = 0xFFFF.
        Can check status with :py:attr:`hibernating`
        """

        self._hibrt_hibthr = 0
        self._hibrt_actthr = 0

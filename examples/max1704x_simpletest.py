# SPDX-FileCopyrightText: 2017 Scott Shawcroft, written for Adafruit Industries
# SPDX-FileCopyrightText: Copyright (c) 2022 ladyada for Adafruit Industries
#
# SPDX-License-Identifier: Unlicense

import time
import board
import adafruit_max1704x 


i2c = board.I2C()  # uses board.SCL and board.SDA

from adafruit_debug_i2c import DebugI2C
debug_i2c = DebugI2C(i2c)
max17 = adafruit_max1704x.MAX17048(debug_i2c)

print("Found MAX1704x with chip version", hex(max17.chip_version))

#max17.activity_threshold = 0.15
#print("MAX1704x activity threshold = %0.2f V" % max17.activity_threshold)

#max17.hibernation_threshold = 5
#print("MAX1704x hibernation threshold = %0.2f %%" % max17.hibernation_threshold)

#max17.hibernate()

#max17.enable_sleep = True
#max17.sleep = True

max17.voltage_alert_min = 3.7
print("Voltage alert minimum = %0.2f V" % max17.voltage_alert_min)
#max17.voltage_alert_max = 3.8
#print("Voltage alert maximum = %0.2f V" % max17.voltage_alert_max)

while True:
    print("Battery voltage:", max17.cell_voltage, "V")
    print("Battery state  :", max17.cell_percent, "%")

    if max17.hibernating:
        print("Hibernating!")

    if max17.active_alert:
        print("Alert!")
        if max17.reset_alert:
            print("  Reset indicator")
            max17.reset_alert = False # clear the alert

        if max17.voltage_high_alert:
            print("  Voltage high")
            max17.voltage_high_alert = False # clear the alert

        if max17.voltage_low_alert:
            print("  Voltage low")
            max17.voltage_low_alert = False # clear the alert

        if max17.voltage_reset_alert:
            print("  Voltage reset")
            max17.voltage_reset_alert = False # clear the alert

        if max17.SOC_low_alert:
            print("  Charge low")
            max17.SOC_low_alert = False # clear the alert

        if max17.SOC_change_alert:
            print("  Charge changed")
            max17.SOC_change_alert = False # clear the alert

    time.sleep(1)

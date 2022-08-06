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

max17.hibernation_threshold = 5
print("MAX1704x hibernation threshold = %0.2f %%" % max17.hibernation_threshold)


while True:
    print("Battery voltage:", max17.cell_voltage, "V")
    print("Battery state  :", max17.cell_percent, "%")
    time.sleep(1)

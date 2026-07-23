# SPDX-FileCopyrightText: 2026 for Adafruit Industries
#
# SPDX-License-Identifier: MIT
"""
hw_tests/00_max17048.py

Hardware-validated on: Unexpected Maker S3 (S3[D]) and Adafruit Feather ESP32-S3
N4R2, both with the MAX17048 fuel gauge.

On-hardware regression tests for the PR1 fixes to adafruit_max1704x.py:
  - Issue #16: reset()/__init__ must block ~192ms before returning, so an
    immediate read doesn't hit the uninitialized VCELL sentinel (0V).
  - sleep / active_alert must address the real CONFIG LSB byte (0x0D), not
    the undocumented byte one past it (0x0E).
  - Threshold setters must round() to the nearest code, not truncate.
"""

import time

import board
import busio

import adafruit_max1704x

passed = 0
failed = 0


def test(name, condition):
    global passed, failed
    if condition:
        print(f"PASS: {name}")
        passed += 1
    else:
        print(f"FAIL: {name}")
        failed += 1


try:
    i2c = board.STEMMA_I2C()
except Exception:
    i2c = None

try:
    if i2c is None:
        i2c = busio.I2C(board.SCL, board.SDA)

    # --- Issue #16: reset() must block for the datasheet's OCV+SOC-ready window ---
    t0 = time.monotonic()
    sensor = adafruit_max1704x.MAX17048(i2c)
    elapsed = time.monotonic() - t0
    test("Sensor found", True)
    test(f"__init__ blocked for tPOR_MAX, elapsed={elapsed:.3f}s [Issue #16]", elapsed >= 0.19)

    voltage = sensor.cell_voltage
    print(f"  cell_voltage immediately after construction: {voltage:.4f}V")
    test("cell_voltage nonzero immediately after construction [Issue #16]", voltage > 0.5)

    # --- BugFix #2: sleep / active_alert must hit the real CONFIG byte (0x0D) ---
    # _config is a raw ground-truth read of the whole 16-bit CONFIG register,
    # independent of the (formerly incorrect) sleep/active_alert descriptors.
    #
    # Datasheet: "SLEEP forces the IC in or out of sleep mode if MODE.EnSleep is
    # set." __init__ leaves EnSleep disarmed, so CONFIG.SLEEP must be armed here
    # first -- this is a real chip gate, not a workaround for the address fix.
    sensor.enable_sleep = True
    sensor.sleep = True
    raw_after_set = sensor._config
    test(
        "CONFIG.SLEEP bit (0x0D bit7) set via `.sleep = True` w/ EnSleep armed [BugFix #2]",
        bool(raw_after_set & 0x0080),
    )

    sensor.sleep = False
    raw_after_clear = sensor._config
    test(
        "CONFIG.SLEEP bit clears via `.sleep = False` [BugFix #2]",
        not bool(raw_after_clear & 0x0080),
    )
    sensor.enable_sleep = False  # restore __init__'s disarmed default

    raw_alrt = bool(sensor._config & 0x0020)
    test(
        "active_alert agrees with raw CONFIG.ALRT bit (0x0D bit5) [BugFix #2]",
        sensor.active_alert == raw_alrt,
    )

    # --- BugFix #3: threshold setters must round(), not truncate ---
    # 0.002 / 0.00125 = 1.6 -> round()=2 (readback 0.0025V); the old int()
    # behavior would truncate to 1 (readback 0.00125V). Only readback can
    # distinguish the two, so this is a genuine regression guard.
    sensor.activity_threshold = 0.002
    readback = sensor.activity_threshold
    test(
        f"activity_threshold rounds 0.002V to nearest code, readback={readback:.5f}V, "
        + "expect ~0.0025V [BugFix #3]",
        abs(readback - 0.0025) < 1e-9,
    )

except Exception as e:
    print(f"FAIL: Unhandled exception: {e}")
    failed += 1

print(f"=== Summary: {passed} passed, {failed} failed ===")
print("ALL TESTS PASSED" if passed > 0 and failed == 0 else "SOME TESTS FAILED")
print("~~END~~")

# SPDX-FileCopyrightText: 2026 for Adafruit Industries
#
# SPDX-License-Identifier: MIT
"""Characterization probe (NOT a pass/fail test): MAX1704x post-POR register readiness.

Question under test
--------------------
The datasheet (19-6171 Rev 7, 11/16) states two competing readiness figures:
  * Battery Insertion Debounce (p.8, applies to "powers on or resets"):
    OCV ready 17ms after insertion/POR, SOC ready 175ms after that (= ~192ms).
    These describe the internal ModelGauge pipeline being seeded.
  * SOC Register 0x04 (p.10): "The first update is available approximately 1s
    after POR of the IC." This describes the register the driver reads.
The datasheet does not say whether the SOC register is (a) seeded with the
debounce estimate at ~192ms (with ~1s being the first recalculation), or
(b) sentinel/undefined until ~1s. This probe answers that empirically.

Method
------
Issues the POR command (0x5400 -> CMD 0xFE) *raw*, bypassing adafruit_max1704x
so the library's built-in 192ms sleep does not hide the window, then samples
VCELL (0x02) and SOC (0x04) every SAMPLE_MS out to WINDOW_S, timestamped from
the moment the reset write is clocked in. Repeats N_RUNS times.

What to look for in the output
------------------------------
  * t_first_nonzero(SOC): if consistently < ~250ms -> interpretation (a);
    the existing 192ms wait is adequate for a first plausible cell_percent.
  * SOC zero/garbage until ~1s -> interpretation (b); open decision for the
    PR (block __init__ ~1.05s vs. document a validity horizon on cell_percent).
  * t_first_change(SOC) after the initial nonzero value ~= the "first update"
    the datasheet means; compare against ~1s +/- 3.5% timebase.
  * Run at 2-3 different battery states (e.g. ~30%, ~70%, near-full) so a
    legitimately-low SOC isn't mistaken for a sentinel.

Caveat: sampling starts after the 16x1ms debounce window (FIRST_READ_MS) to
avoid perturbing OCV acquisition with bus traffic; the datasheet is silent on
whether reads during debounce interfere.
"""

import struct
import time
import traceback

import board
import busio
from adafruit_bus_device import i2c_device

ADDR = 0x36
REG_VCELL = 0x02
REG_SOC = 0x04
REG_CMD = 0xFE

N_RUNS = 3
FIRST_READ_MS = 25  # stay clear of the 16x1ms debounce sampling window
SAMPLE_MS = 25
WINDOW_S = 1.5

try:
    i2c = board.STEMMA_I2C()
except Exception:  # noqa: BLE001 - STEMMA-first, fall back to plain busio
    i2c = busio.I2C(board.SCL, board.SDA)

dev = i2c_device.I2CDevice(i2c, ADDR)


def read_u16(reg):
    buf = bytearray(2)
    with dev:
        dev.write_then_readinto(bytes([reg]), buf)
    return struct.unpack(">H", buf)[0]


def por():
    """Write 0x5400 to CMD. Datasheet: no ACK follows -> OSError is success."""
    try:
        with dev:
            dev.write(bytes([REG_CMD, 0x54, 0x00]))
    except OSError:
        return  # NACK expected: reset took effect
    raise RuntimeError("CMD 0x5400 was ACKed - reset did not take effect?")


def run(idx):
    print("=== run %d ===" % idx)
    print("t_ms,vcell_raw,vcell_V,soc_raw,soc_pct")
    t0 = time.monotonic_ns()
    por()
    first_nonzero_soc = None
    first_change_soc = None
    prev_soc = None
    next_t = FIRST_READ_MS / 1000
    while True:
        now = (time.monotonic_ns() - t0) / 1e9
        if now < next_t:
            continue
        try:
            vcell = read_u16(REG_VCELL)
            soc = read_u16(REG_SOC)
        except OSError as e:
            print("%.1f,READ-ERR:" % (now * 1000), end=" ")
            traceback.print_exception(e)
            next_t += SAMPLE_MS / 1000
            continue
        t_ms = (time.monotonic_ns() - t0) / 1e6
        fields = (t_ms, vcell, vcell * 78.125e-6, soc, soc / 256.0)
        print("%.1f,0x%04X,%.4f,0x%04X,%.3f" % fields)
        if first_nonzero_soc is None and soc != 0:
            first_nonzero_soc = t_ms
        if prev_soc is not None and first_change_soc is None:
            if soc != prev_soc and prev_soc != 0:
                first_change_soc = t_ms
        prev_soc = soc
        next_t += SAMPLE_MS / 1000
        if next_t > WINDOW_S:
            break
    print("run %d: t_first_nonzero(SOC) = %s ms" % (idx, first_nonzero_soc))
    print("run %d: t_first_change(SOC)  = %s ms" % (idx, first_change_soc))


def main():
    for i in range(1, N_RUNS + 1):
        run(i)
        time.sleep(2.0)  # let ModelGauge settle between PORs


try:
    main()
except Exception as e:  # noqa: BLE001 - report anything, this is a probe
    traceback.print_exception(e)
print("~~END~~")

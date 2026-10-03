# RD6006 firmware flash stuck at 03%? Remove the WiFi module.

Notes from recovering a Riden RD6006 power supply whose firmware update kept
freezing at **03%**. Writing this down in case it saves someone else an
evening.

**TL;DR:** if flashing an RD60xx stalls a few percent in and the screen freezes
(typically at "03%"), **power everything off, unplug the WiFi module from the
unit, and flash again.** That fixed it here. You can put the module back
afterwards.

## Setup

| | |
|---|---|
| Unit | Riden RD6006 (model ID 60062), with the WiFi module installed |
| Bootloader | V1.09 (screen showed `Bootloader V1.09`, firmware `V-.--`, i.e. no valid firmware) |
| Host | Windows 11, unit's built-in USB (CH340 USB-serial) |
| Flash tool | [tjko/riden-flashtool](https://github.com/tjko/riden-flashtool) (`flash-rd.py`) |
| Firmware | UniSoft custom firmware `RD60062_V1.42.1p.bin` (also tried `RD60062_V1.38.1h.bin`) |

## Symptoms

* The unit is in bootloader mode (hold **ENTER** while powering on) and the
  flash tool detects it and reads the model/serial number fine.
* Flashing starts, then stops after about **7-8 KB** (around 110-130 of
  ~3300 64-byte blocks). The tool gets no `OK` ack for the next block.
* The unit's screen freezes at **03%** and stays there.
* The unit ignores everything on the serial port until it's power-cycled.
* The official Windows flasher (RDFlasher) never managed to connect at all.

## What it was *not*

Each of these was tried and the stall still happened at ~3%:

| Tried | Result |
|---|---|
| Different firmware image (1.42.1p, 1.38.1h) | Same stall (images are scrambled and differ from byte 0, so not content-related) |
| Different USB port | Same stall |
| CH340 driver 3.9 (2024) → 3.4 (2014) | Same stall |
| Waiting up to 20 s for each ack | Unit never acks again |
| 50 ms pause after every block | Stalled even *earlier* in bytes (~2 KB) |
| Toggling DTR/RTS, other baud rates | No effect |

The useful clue was **timing**. Ack latency was a steady ~22 ms per block right
up to the stall. Every stall happened about **2.5-5 seconds after serial
traffic started**, no matter how many bytes had been sent. Even sending only
harmless `queryd\r\n` bootloader queries, the unit answered for about 4-5
seconds and then went silent. The bootloader itself was fine while idle: it
still answered after sitting untouched for a long time. It only stopped once
traffic had been flowing for a few seconds.

## Fix

1. Disconnect DC power and USB.
2. Unplug the WiFi module from its header inside the unit. Note its
   orientation so you can reinstall it later.
3. Reconnect USB and enter bootloader mode (hold **ENTER** while powering on).
4. Flash again.

With the WiFi module removed, the same firmware flashed all the way through and
the unit booted normally on 1.42.

## Probable cause

I didn't verify this on the PCB. On these units the WiFi module appears to share
the MCU's UART with the USB-serial interface. A few seconds after power-up or
activity, the module starts transmitting and collides with the data coming
from the PC. The bootloader then receives corrupted or missing bytes and waits
forever for the rest of a 64-byte block, so it never acks. This fits
everything above: the stall is time-based rather than byte-based, independent
of the host, driver and image, and the screen freezes on the progress
percentage.

## Other gotchas hit along the way

* **`AttributeError: module 'serial' has no attribute 'Serial'`**: The wrong
  Python package is installed. `flash-rd.py` needs
  [`pyserial`](https://pypi.org/project/pyserial/), not the unrelated `serial`
  package. Both install a module named `serial`, so remove `serial` and
  install `pyserial`:

  ```
  pip uninstall serial
  pip install pyserial
  ```

* **Stray `0xFC` byte:** When the unit (re)starts, it can send a `0xFC` byte
  before answering the bootloader query with `boot`. A tool that reads exactly
  4 bytes once can see `b'\xfcboo'` and decide the unit isn't in bootloader
  mode. If detection fails while the screen clearly shows the bootloader, retry.
  Better still, make the tool poll and search the received bytes for `boot`.
  For this recovery I used a locally patched copy of `flash-rd.py` that did
  that and waited for the user to power-cycle the unit.

* **COM port can change:** After replugging, or using a different USB port,
  the unit came back as a different COM port (COM5 → COM6). Check Device
  Manager under "USB-SERIAL CH340".

* **Unit unbootable after a failed flash:** That's expected and recoverable.
  The bootloader is separate, so you can always re-enter it (hold **ENTER**
  while powering on) and flash again.

## Link test script

[`probe_link.py`](probe_link.py) checks whether the serial link to the
bootloader stays healthy, without flashing anything. Start it, then
power-cycle the unit into bootloader mode. It polls with `queryd` and reports
how long the bootloader keeps answering.

```
pip install pyserial
python probe_link.py COM6
```

* **Healthy link:** The bootloader keeps answering for the whole run (default
  20 s).
* **Affected unit (like this one, before removing the WiFi module):** Replies
  stop after a few seconds.

## Credits

* [tjko/riden-flashtool](https://github.com/tjko/riden-flashtool), the flash
  tool used here.
* UniSoft, author of the RD60xx custom firmware used here. This repo does not
  include any firmware files.

#!/usr/bin/env python3
"""Check how long a Riden RD60xx bootloader keeps answering on the serial port.

Sends the harmless bootloader query "queryd\\r\\n" repeatedly and reports how
long "boot" replies keep coming. Does not write any flash.

Usage: python probe_link.py <port> [seconds]
  e.g. python probe_link.py COM6
       python probe_link.py /dev/ttyUSB0 30

Start it, then power-cycle the unit while holding ENTER (bootloader mode).
"""

import sys
import time

import serial  # pip install pyserial


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    port = sys.argv[1]
    run_for = float(sys.argv[2]) if len(sys.argv) > 2 else 20.0

    ser = serial.Serial(port, 115200, timeout=0.1)
    print(f'Listening on {port}; power-cycle the unit into bootloader mode now '
          '(waiting up to 90 s)...', flush=True)

    deadline = time.time() + 90
    t_first = None
    last_boot = None
    replies = 0
    while time.time() < deadline:
        ser.write(b'queryd\r\n')
        res = ser.read(16)
        now = time.time()
        if b'boot' in res:
            if t_first is None:
                t_first = now
                deadline = now + run_for
                print(f'Bootloader answered. Polling for {run_for:.0f} s...',
                      flush=True)
            last_boot = now
            replies += 1
        elif last_boot and now - last_boot > 3:
            break

    if t_first is None:
        print('No reply from the bootloader.')
        return 1

    alive = last_boot - t_first
    print(f'Bootloader answered {replies} queries over {alive:.1f} s.')
    if alive < run_for - 1:
        print('Replies STOPPED early. The serial link to the bootloader is '
              'unreliable (on RD6006, try removing the WiFi module).')
        return 2
    print('Link looks healthy for the whole run.')
    return 0


if __name__ == '__main__':
    sys.exit(main())

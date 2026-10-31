"""
Share one Pico serial port between several PC programs (the eye and mouth slider windows, Frank).

    uv run --no-project --with pyserial python firmware/share_port.py /dev/cu.usbmodem2101 [N]

Opens the real port once and makes N (default 2) virtual ports, printing their paths. Point each
program at one of them in place of the real port. Whatever any program writes goes to the board;
whatever the board prints goes to every program. macOS and Linux (pseudo-terminals); on
Windows use com0com or run the programs one at a time. Ctrl-C ends it.
"""

import os
import select
import sys

import serial

REAL = sys.argv[1]
N = int(sys.argv[2]) if len(sys.argv) > 2 else 2

board = serial.Serial(REAL, 115200, timeout=0)
masters = []
for _ in range(N):
    m, s = os.openpty()
    os.set_blocking(m, False)
    masters.append((m, s))          # keep the slave open too, so writes never fail with no reader
    print(os.ttyname(s), flush=True)
print(f"sharing {REAL} between {N} virtual ports; Ctrl-C to stop", flush=True)

fds = [board.fileno()] + [m for m, _ in masters]
try:
    while True:
        ready, _, _ = select.select(fds, [], [], 1.0)
        for fd in ready:
            if fd == board.fileno():
                data = board.read(4096)
                for m, _ in masters:
                    try:
                        os.write(m, data)
                    except (BlockingIOError, OSError):
                        pass
            else:
                try:
                    data = os.read(fd, 4096)
                except (BlockingIOError, OSError):
                    continue
                if data:
                    board.write(data)
except KeyboardInterrupt:
    pass

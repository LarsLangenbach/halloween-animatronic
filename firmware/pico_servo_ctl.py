"""
Live servo control from the PC (servo_controls.py). Runs on the Pico as main.py.
Reads lines "<GP pin> <angle>" or "<GP pin> off" from the USB serial port and drives that
servo; 0..180 deg -> 500..2500 us. Every servo is loose (no pulses) until it gets a command.
"off" sets the pulse to 0 instead of deinit(): pins share PWM slices in pairs (GP10/GP11 and
so on), and deinit() would stop the other servo of the pair too.
"""

import sys
from machine import Pin, PWM

PINS = (4, 5, 6, 7, 8, 9, 10, 11, 12, 13)
for p in PINS:
    Pin(p, Pin.OUT, value=0)
pwm = {}

while True:
    parts = sys.stdin.readline().split()
    if len(parts) != 2:
        continue
    try:
        p = int(parts[0])
    except ValueError:
        continue
    if p not in PINS:
        continue
    if parts[1] == "off":
        if p in pwm:
            pwm[p].duty_ns(0)
        continue
    try:
        a = max(0.0, min(180.0, float(parts[1])))
    except ValueError:
        continue
    if p not in pwm:
        pwm[p] = PWM(Pin(p), freq=50)
    pwm[p].duty_ns(int((500 + a * 2000 / 180) * 1000))

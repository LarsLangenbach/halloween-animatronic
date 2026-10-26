"""
Bench test for the EyeMech and the brows on ONE mouth board: one servo at a time, no master.

Run it from Thonny ("Run current script", do NOT save it as main.py). It centres every servo
at 90 and then waits; type the commands in Thonny's shell:
  test_all()       wiggle each servo +-10 deg in turn and print its name (find out which is which)
  wiggle("TL")     wiggle one servo +-10 deg around 90
  sweep("TL")      move one servo slowly to both of its limits and back to 90
  go("TL", 120)    move one servo to an angle (held inside its limits)
  center()         all servos to 90 (the calibration pose for fitting horns)
  off()            stop all pulses (servos go limp)

Names are Cogley's: LR look left/right (the servo between the eyes), UD look up/down (the
centre servo behind it); LO/LI left brow outer/inner, RO/RI right brow outer/inner. The lid
sockets follow manual step 2.13's pictures. Seen from the front, facing the eyes: top-lid servo
on your left = TL, on your right = TR; bottom-lid servo on your left = BL, on your right = BR.
Whether that is the side his code means is not proven yet: lids are closed at 90 and open
towards 160 (TL), 30 (TR), 30 (BL), 140 (BR). If go() pushes a lid shut instead of opening it,
that pair is swapped.
The eyes sit on the sockets they keep on the eyes board. The brows sit on GP4-GP7 only for
this test: on their own board (brows_mouthboard.py) they use GP8/GP9/GP12/GP13.
Limits are Cogley's from eyes.py and Brows.py. Give the board 5 V through the XT60; USB alone
cannot move the servos.
"""

import time
from machine import Pin, PWM

# Socket each servo is plugged into (GP number). Edit to match the board.
PINS = {
    "LR": 8,
    "UD": 9,
    "BR": 10,
    "TR": 11,
    "BL": 12,
    "TL": 13,
    "LO": 4,
    "RO": 5,
    "LI": 6,
    "RI": 7,
}

LIMITS = {
    "LR": (40, 140),
    "UD": (60, 140),
    "TL": (90, 160),
    "BL": (90, 30),
    "TR": (90, 30),
    "BR": (90, 140),
    "LO": (80, 100),
    "LI": (100, 80),
    "RI": (80, 100),
    "RO": (100, 80),
}

try:
    from servo import Servo  # Cogley's library, so angles match his programs
    servos = {n: Servo(pin_id=p) for n, p in PINS.items()}
    write = lambda n, a: servos[n].write(a)
    print("using Cogley's servo library")
except ImportError:
    # Fallback: plain 50 Hz PWM, 0..180 deg -> 500..2500 us (90 deg = 1500 us either way)
    servos = {n: PWM(Pin(p), freq=50) for n, p in PINS.items()}
    write = lambda n, a: servos[n].duty_ns(int((500 + a * 2000 / 180) * 1000))
    print("servo library not found, using plain PWM")

pos = {}


def go(name, angle, step_ms=15):
    lo, hi = min(LIMITS[name]), max(LIMITS[name])
    angle = max(lo, min(hi, angle))
    start = pos.get(name, angle)
    step = 1 if angle >= start else -1
    for a in range(int(start), int(angle), step):
        write(name, a)
        time.sleep_ms(step_ms)
    write(name, angle)
    pos[name] = angle


def center(gap_ms=0):
    for n in PINS:
        if gap_ms:
            print("GP%d  %s -> 90" % (PINS[n], n))
        write(n, 90)
        pos[n] = 90
        time.sleep_ms(gap_ms)


def wiggle(name, times=3):
    for _ in range(times):
        go(name, 100)
        go(name, 80)
    go(name, 90)


def sweep(name):
    lo, hi = LIMITS[name]
    print(name, "->", lo)
    go(name, lo)
    time.sleep_ms(500)
    print(name, "->", hi)
    go(name, hi)
    time.sleep_ms(500)
    go(name, 90)


def test_all():
    for n, p in PINS.items():
        print("GP%d  %s" % (p, n))
        wiggle(n)
        time.sleep_ms(1000)


def off():
    for n in PINS:
        try:
            servos[n].deinit()
        except AttributeError:
            servos[n].duty_ns(0)


center(500)  # one at a time on start-up, so a jam shows which servo it was
print("all at 90. try test_all(), wiggle('TL'), sweep('TL'), go('TL', 120), center(), off()")

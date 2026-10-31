"""
Live servo control from the PC (servo_controls.py, mouth_controls.py, frank/mouth.py). Runs on
BOTH Picos as main.py: the mouth board (Board 1, on the laptop's USB) and the eye board (Board 2,
reached through the mouth board over the link wires).

Lines "<GP pin> <angle>" or "<GP pin> off" drive that servo; 0..180 deg -> 500..2500 us, and
-27..207 is allowed (200..2800 us) for a lid that needs the last few degrees (2026-10-29: -9..189
was not far enough for the left eye's top lid). Past the servo's own stop it only buzzes. Every
servo is loose (no pulses) until it gets a command. "off" sets the pulse to 0 instead of deinit():
pins share PWM slices in pairs (GP10/GP11 and so on), and deinit() would stop the other servo of
the pair too.

The link (2026-10-29): a line "e <anything>" is not acted on here but sent on as "<anything>\n"
over UART0 TX on GP16 to the other board, which handles it as if it had come over USB. So the
laptop, plugged into the mouth board, moves an eye servo with "e 8 90". The other board listens
on UART0 RX, GP17, so the link wires must CROSS: mouth GP16 (Pico pin 21) to eye GP17 (pin 22),
and GND to GND. GP16 is only driven once a board has received its first "e" line over USB, so a
board that nobody talks to over USB (the eye board) never drives the wire, and a straight wire
(16 to 16) cannot put two outputs against each other. The link is one way; nothing comes back.
A board also keeps reading USB, so two USB cables (one per board) still work with no "e" prefix.
"""

import sys
import select
from machine import Pin, PWM, UART

PINS = tuple(range(4, 16))  # GP4..GP15, the twelve servo sockets of a mouth board
led = Pin(25, Pin.OUT, value=0)   # the Pico's LED: heartbeat blink; solid for 1 s after a link line
LINK_TX, LINK_RX, LINK_BAUD = 16, 17, 115200
for p in PINS:
    Pin(p, Pin.OUT, value=0)
pwm = {}

# Listen on the link. tx is a pin nothing is wired to (GP0): GP16 is driven only by the board
# that forwards (see link_out()).
uart = UART(0, LINK_BAUD, tx=Pin(0), rx=Pin(LINK_RX), rxbuf=512)
link = None   # the forwarding UART, made on the first "e" line from USB


def link_out():
    global uart, link
    if link is None:
        link = UART(0, LINK_BAUD, tx=Pin(LINK_TX), rx=Pin(LINK_RX), txbuf=1024, rxbuf=512)
        uart = link
    return link


def handle(line, from_usb=True):
    """One command line. Returns what it did, for tests: ("set", pin, us), ("off", pin),
    ("link", text) or None."""
    parts = line.split()
    if not parts:
        return None
    if parts[0] == "e":
        if not from_usb or len(parts) < 2:
            return None
        text = " ".join(parts[1:])
        link_out().write(text + "\n")
        return ("link", text)
    if len(parts) != 2:
        return None
    try:
        p = int(parts[0])
    except ValueError:
        return None
    if p not in PINS:
        return None
    if parts[1] == "off":
        if p in pwm:
            pwm[p].duty_ns(0)
        return ("off", p)
    try:
        a = max(-27.0, min(207.0, float(parts[1])))   # -27..207: 200..2800 us, past the usual ends
    except ValueError:
        return None
    if p not in pwm:
        pwm[p] = PWM(Pin(p), freq=50)
    us = int(500 + a * 2000 / 180)
    pwm[p].duty_ns(us * 1000)
    return ("set", p, us)


def main():
    """USB is read a character at a time and only when the poll says a character is there, so a
    board with no laptop on its USB can never block in a read and stop serving the link. The LED
    blinks once a second while this runs (a heartbeat) and stays on for a second after every
    line that arrives over the link."""
    import time
    poll = select.poll()
    poll.register(sys.stdin, select.POLLIN)
    usb, rx, led_until = "", b"", 0
    while True:
        n = uart.any()
        if n:                                 # bytes from the link: split on newlines ourselves
            rx += uart.read(n)
            led_until = time.ticks_add(time.ticks_ms(), 1000)
            while b"\n" in rx:
                raw, rx = rx.split(b"\n", 1)
                try:
                    handle(raw.decode(), from_usb=False)
                except UnicodeError:
                    pass
            if len(rx) > 200:                 # garbage with no newline: drop it
                rx = b""
        for _ in range(64):                   # up to 64 characters from USB per pass
            if not poll.poll(0):
                break
            ch = sys.stdin.read(1)
            if ch in "\r\n":
                line, usb = usb, ""
                if line:
                    handle(line)
            else:
                usb += ch
                if len(usb) > 200:
                    usb = ""
        now = time.ticks_ms()
        led.value(1 if time.ticks_diff(led_until, now) > 0 else (now % 1000) < 100)
        time.sleep_ms(2)


if __name__ == "__main__":
    main()

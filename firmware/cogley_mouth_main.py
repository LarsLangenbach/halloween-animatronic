"""
Pico program for the Cogley mouth (Halloween head) on his mouth board: his MouthMaster.py
(Robot Head a2.0.33, Patreon; keep private) with smooth moves and a talk mode.
TalkingHead.py drives it with --head cogley (it is found automatically).

Same pins, poses and USB serial commands as his MouthMaster.py (so his HeadControlUI.py
still works), and the same eyes/brows link outputs on GP16-GP19. Changes from his file:
  - every servo glides to its target at a set speed instead of jumping, so the MG996R jaw
    servos don't kick the supply
  - each servo is clamped to the range his poses use (LIMITS below); a command outside it
    is cut to the limit and reported
  - new commands: jaw, jawdeg, jawdir, talk, stop, set, speed, rest, relax, where, help
  - the jaw's direction is a setting (JAW_DIR): on the team's bench his direction shut it
  - no `servo` library needed: the pulse mapping is built in

  - (2026-10-29, this repo) "e <anything>" sends "<anything>\n" over UART0 TX, GP16, 115200 baud,
    to the eye board (Board 2, running pico_servo_ctl.py, which listens on its GP17; so the
    GP16/GP17 link wires cross). GP16 becomes the UART on the first "e" line; from then on
    the eyes_* link commands (his 2-bit eyes link on the same two pins) are ignored.

Install as main.py on the Pico (a Pico 2 takes the RPI_PICO2 MicroPython build):
    .venv\\Scripts\\python.exe -m mpremote cp cogley_mouth_main.py :main.py + reset
Commands are lines of text over USB serial at any baud; mouth_send.py sends them by hand.
"""

import sys
import time
import random
import select
from machine import Pin, PWM, UART

led = Pin(25, Pin.OUT)
mode = Pin(28, Pin.IN, Pin.PULL_UP)
SDA = Pin(16, Pin.OUT)
SCL = Pin(17, Pin.OUT)
BSDA = Pin(18, Pin.OUT)
BSCL = Pin(19, Pin.OUT)
LINK_TX, LINK_RX, LINK_BAUD = 16, 17, 115200
link = None   # UART0 to the eye board, made on the first "e" line (takes GP16 from SDA)


def link_out():
    global link
    if link is None:
        link = UART(0, LINK_BAUD, tx=Pin(LINK_TX), rx=Pin(LINK_RX), txbuf=1024)
    return link

# Pulse width over 0-180 deg. The same mapping as the `servo` library MouthMaster.py uses,
# so his pose angles mean the same here.
MIN_US = 544
MAX_US = 2400

TICK_MS = 20          # update rate, one servo frame
SPEED = 90            # deg/s for commands (the jaw opens fully in about 0.45 s)
TALK_SPEED = 300      # deg/s for the jaw while talking
TALK_OPEN = 0.7       # how far the jaw opens while talking, 0..1 of fully open
JAW_DEG = 40          # jaw servo travel at "jaw 1" / mouth_open (his pose: 40); jawdeg changes it
JAW_CAP = 70          # jawdeg never goes past this
JAW_DIR = -1          # 1: his direction (JL 90 -> 50 opens). -1: reversed; on the bench
                      # (2026-10-25) his direction drove the jaw shut. jawdir changes it


def jaw_range(side):
    """(low, high) limit of JL (side -1) or JR (side 1): 90 closed, JAW_DEG away open."""
    a = 90 + side * JAW_DIR * JAW_DEG
    return (min(90, a), max(90, a))


# Servo name: (pin, low limit, high limit). The limits are the range his poses use.
LIMITS = {
    "JL":  (4,) + jaw_range(-1),    # jaw, left MG996R: 90 closed (his: 50 open)
    "JR":  (5,) + jaw_range(1),     # jaw, right MG996R: 90 closed (his: 130 open)
    "LUL": (6, 40, 110),    # upper lip, left
    "LUR": (7, 70, 140),    # upper lip, right
    "LLL": (8, 55, 110),    # lower lip, left
    "LLR": (9, 60, 110),    # lower lip, right
    "CUL": (10, 60, 100),   # upper corner, left
    "CUR": (11, 75, 105),   # upper corner, right
    "CLL": (12, 90, 120),   # lower corner, left
    "CLR": (13, 65, 90),    # lower corner, right
    "TON": (14, 55, 130),   # tongue
}

poses = {
    "mouth_closed": {"JL": 90, "JR": 90},
    "mouth_open":   {"JL": 50, "JR": 130},
    "lips_down":    {"LUL": 110, "LUR": 70, "LLL": 55, "LLR": 110},
    "lips_up":      {"LUL": 40, "LUR": 140, "LLL": 110, "LLR": 60},
    "tongue_down":  {"TON": 130},
    "tongue_up":    {"TON": 55},
    "smile":        {"CUL": 60, "CUR": 105, "CLL": 90, "CLR": 90},
    "frown":        {"CUL": 100, "CUR": 75, "CLL": 90, "CLR": 90},
    "wide":         {"CUL": 65, "CUR": 105, "CLL": 120, "CLR": 65},
    "narrow":       {"CUL": 90, "CUR": 80, "CLL": 90, "CLR": 90},
}

# His start-up pose. Lip servos stay unpowered until a lip command, as in his file.
REST = ("mouth_closed", "tongue_down", "narrow")

# Eyes and brows link: the two output levels for each command (his MouthMaster.py)
LINK = {
    "eyes_move":   (SDA, SCL, 1, 1),
    "eyes_open":   (SDA, SCL, 1, 0),
    "eyes_close":  (SDA, SCL, 0, 0),
    "brows_up":    (BSDA, BSCL, 1, 1),
    "brows_down":  (BSDA, BSCL, 0, 0),
    "brows_happy": (BSDA, BSCL, 0, 1),
    "brows_angry": (BSDA, BSCL, 1, 0),
}

HELP = """commands:
  mouth_closed mouth_open lips_down lips_up tongue_down tongue_up
  smile frown wide narrow          his poses, now gliding
  jaw <0..1>                       0 closed, 1 fully open
  e <pin> <angle>                  on to the eye board over the link (GP16 -> its GP17)
  jawdeg [deg]                     jaw travel at fully open (now {}, max {})
  jawdir [1|-1]                    jaw direction: 1 his, -1 reversed (now {})
  talk [0..1]                      jaw chatters until stop (opening, default 0.7)
  stop                             stop talking, close the jaw
  set <servo> <deg>                one servo, e.g. set TON 100
  speed <deg/s>                    glide speed (now {})
  rest                             back to the start-up pose
  relax                            all servos unpowered (limp)
  where                            print every servo's angle
  on off  eyes_*  brows_*          as in MouthMaster.py"""


class Joint:
    """One servo that glides toward its target at a set speed."""

    def __init__(self, pin, lo, hi):
        self.pwm = PWM(Pin(pin))
        self.pwm.freq(50)
        self.pwm.duty_ns(0)
        self.lo, self.hi = lo, hi
        self.pos = 90.0         # the horns were fitted with every servo at 90
        self.target = 90.0
        self.live = False       # sending pulses
        self.sent = None

    def aim(self, angle):
        """Set the target, clamped to the limits. Returns the angle used."""
        a = min(max(angle, self.lo), self.hi)
        self.target = float(a)
        self.live = True
        return a

    def update(self, step):
        if not self.live:
            return
        d = self.target - self.pos
        self.pos = self.target if abs(d) <= step else self.pos + (step if d > 0 else -step)
        us = MIN_US + self.pos * (MAX_US - MIN_US) / 180
        ns = int(us * 1000)
        if ns != self.sent:
            self.pwm.duty_ns(ns)
            self.sent = ns

    def relax(self):
        # duty 0, not deinit: on the RP2040 two pins share a PWM slice, so deinit would
        # also stop the neighbouring servo
        self.pwm.duty_ns(0)
        self.live = False
        self.sent = None


# MicroPython dicts don't keep their order, so lists follow this one
NAMES = ("JL", "JR", "LUL", "LUR", "LLL", "LLR", "CUL", "CUR", "CLL", "CLR", "TON")
servos = {name: Joint(*LIMITS[name]) for name in NAMES}


def report(name, asked, got):
    if got != asked:
        print("{} {} is past its limit; using {}".format(name, asked, got))


def apply_pose(pose_name):
    for name, angle in poses[pose_name].items():
        report(name, angle, servos[name].aim(angle))


def set_jaw(f):
    f = min(max(f, 0.0), 1.0)
    servos["JL"].aim(90 - JAW_DIR * JAW_DEG * f)
    servos["JR"].aim(90 + JAW_DIR * JAW_DEG * f)


def set_jaw_limits():
    servos["JL"].lo, servos["JL"].hi = jaw_range(-1)
    servos["JR"].lo, servos["JR"].hi = jaw_range(1)


def set_jaw_deg(deg):
    """Jaw travel at fully open; the jaw servos' limits follow it."""
    global JAW_DEG
    JAW_DEG = min(max(deg, 10), JAW_CAP)
    set_jaw_limits()
    return JAW_DEG


class Talk:
    """Jaw chatter: words of 1-4 syllables with short pauses between them."""

    def __init__(self):
        self.on = False
        self.amount = TALK_OPEN
        self.next_ms = 0
        self.left = 0           # syllables left in this word
        self.open = False

    def start(self, amount):
        self.on = True
        self.amount = min(max(amount, 0.0), 1.0)
        self.next_ms = time.ticks_ms()
        self.left = 0
        self.open = False

    def stop(self):
        self.on = False
        set_jaw(0)

    def update(self, now):
        if not self.on or time.ticks_diff(now, self.next_ms) < 0:
            return
        if self.open:
            set_jaw(random.uniform(0.0, 0.1) * self.amount)
            wait = random.randint(60, 140)
            self.open = False
        elif self.left > 0:
            set_jaw(random.uniform(0.4, 1.0) * self.amount)
            wait = random.randint(90, 220)
            self.open = True
            self.left -= 1
        else:
            set_jaw(0)
            wait = random.randint(150, 600)
            self.left = random.randint(1, 4)
        self.next_ms = time.ticks_add(now, wait)


talk = Talk()


def do(line):
    global SPEED, JAW_DIR
    words = line.split()
    if not words:
        return
    cmd, args = words[0], words[1:]
    if cmd == "on":
        led.value(1)
    elif cmd == "off":
        led.value(0)
    elif cmd == "e":
        if args:
            link_out().write(" ".join(args) + "\n")
    elif cmd in LINK:
        a, b, va, vb = LINK[cmd]
        if a is SDA and link is not None:
            return                      # GP16/GP17 are the UART to the eye board now
        a.value(va)
        b.value(vb)
    elif cmd == "mouth_open":
        talk.on = False
        set_jaw(1)
    elif cmd in poses:
        if cmd == "mouth_closed":
            talk.on = False
        apply_pose(cmd)
    elif cmd == "jaw":
        talk.on = False
        set_jaw(float(args[0]))
    elif cmd == "jawdeg":
        if args:
            set_jaw_deg(float(args[0]))
        print("jawdeg {}".format(JAW_DEG))
    elif cmd == "jawdir":
        if args:
            talk.on = False
            set_jaw(0)                  # close first, then turn the direction round
            JAW_DIR = -1 if float(args[0]) < 0 else 1
            set_jaw_limits()
        print("jawdir {}".format(JAW_DIR))
    elif cmd == "talk":
        talk.start(float(args[0]) if args else TALK_OPEN)
    elif cmd == "stop":
        talk.stop()
    elif cmd == "set":
        name = args[0].upper()
        if name not in servos:
            print("no servo {}; servos: {}".format(name, " ".join(NAMES)))
            return
        if name in ("JL", "JR"):
            talk.on = False
        angle = float(args[1])
        report(name, angle, servos[name].aim(angle))
    elif cmd == "speed":
        SPEED = min(max(float(args[0]), 5), 600)
    elif cmd == "rest":
        talk.on = False
        for pose in REST:
            apply_pose(pose)
    elif cmd == "relax":
        talk.on = False
        for s in servos.values():
            s.relax()
    elif cmd == "where":
        print(" ".join("{}={}".format(n, int(servos[n].pos + 0.5) if servos[n].live else "off")
                       for n in NAMES))
    elif cmd == "help":
        print(HELP.format(JAW_DEG, JAW_CAP, JAW_DIR, SPEED))
    else:
        print("Unknown command")


print("Ready to receive commands (help for a list)")

SDA.value(0)
SCL.value(0)
BSDA.value(0)
BSCL.value(0)
for pose in REST:
    apply_pose(pose)

poll = select.poll()
poll.register(sys.stdin, select.POLLIN)
buf = ""
last = time.ticks_ms()

while True:
    while poll.poll(0):
        ch = sys.stdin.read(1)
        if ch in "\r\n":
            line, buf = buf.strip(), ""
            if line:
                if not line.startswith("e "):
                    print("Received: " + line)
                try:
                    do(line)
                except Exception as e:
                    print("Error:", e)
        else:
            buf += ch

    now = time.ticks_ms()
    dt = time.ticks_diff(now, last) / 1000
    last = now
    talk.update(now)
    jaw_speed = TALK_SPEED if talk.on else SPEED
    for name, s in servos.items():
        s.update((jaw_speed if name in ("JL", "JR") else SPEED) * dt)
    time.sleep_ms(TICK_MS)

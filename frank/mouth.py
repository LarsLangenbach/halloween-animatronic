"""
Frank's mouth follows his voice: jaw, lips, mouth corners and tongue.

The voice player (voice.py) hands every 20 ms slice of audio it plays to Mouth.feed(), and the
expression tag of each piece to Mouth.face(). From each slice:
  - loudness opens the jaw (between the CLOSED and OPEN poses) and, more slowly, parts the
    lips (the upper lip up, the lower lip down, LIP_PART of the way to Cogley's lips_up /
    lips_down);
  - brightness (the spectral centroid) sets the mouth's width: bright sounds like "ee" and "s"
    pull the corners towards WIDE, dark ones like "oo" and "oh" leave them NARROW;
  - a loud syllable onset now and then flicks the tongue up (TONGUE_CHANCE), once a tongue
    servo is fitted (TONGUE; none on 2026-10-29).
The expression tag puts a smile (amused, excited, curious) or a frown (irritated, skeptical,
concentrating) under the corners. The poses are the mouth board's (firmware/mouth_poses.json,
saved from the mouth slider window; Cogley's own angles until then), and every angle is kept
inside the board program's servo limits. Once the three vowel shapes (Vowel AH, EE, OO rows of
the mouth slider window) are saved, the mouth blends between those instead: brightness picks
the shape (OO dark .. AH .. EE bright) and loudness moves the whole mouth from rest to it. A thread sends the servos their angles 50 times a
second (the jaw) and 25 times a second (the rest), only when they change.

The eyes are alive the whole time (gaze.py, eye_anim.py through the link): looking around and
blinking from the moment the mouth is up, also while he speaks, until close(). Mouth(eyes=False)
or --still-eyes leaves them still.

The Pico runs pico_servo_ctl.py as main.py (lines "<GP pin> <deg>": the jaw angles are sent
per servo; Mouth.link("<pin> <deg>") reaches the eye board through the same board, 2026-10-29) or TalkingHead's cogley_mouth_main.py (it answers `where`; then its own `jaw <0..1>`
moves both jaw servos in its jawdir and jawdeg, and `rest` is its start-up pose). The same two
programs the mouth slider window drives. The board program glides at `speed` deg/s; GLIDE sets
it fast enough for syllables.

    uv run --no-project --with pyserial --with numpy python frank/mouth.py [PORT] --test
        flaps the jaw on a made-up speech envelope, no voice needed
    uv run --no-project --with pyserial --with numpy --with httpx --with sounddevice --with scipy python frank/mouth.py [PORT] --say "Hello. [amused] Who's there?"
        speaks the line in his voice with the jaw moving
PORT: the Pico's serial port, or "auto" (the default) to pick the first USB serial port.
--still-eyes: no eye animation. In chat.py: --mouth auto (or the port).
"""

import glob
import json
import math
import os
import sys
import threading
import time
from collections import deque

HERE = os.path.dirname(os.path.abspath(__file__))
POSES_FILE = os.path.join(HERE, "..", "firmware", "mouth_poses.json")

# Cogley's MouthMaster.py angles, as in firmware/mouth_controls.py; mouth_poses.json overrides.
POSES = {
    "mouth_closed": {"JL": 90, "JR": 90},
    "mouth_open": {"JL": 50, "JR": 130},
    "lips_rest": {"LUL": 90, "LUR": 90, "LLL": 90, "LLR": 90},
    "lips_down": {"LUL": 110, "LUR": 70, "LLL": 55, "LLR": 110},
    "lips_up": {"LUL": 40, "LUR": 140, "LLL": 110, "LLR": 60},
    "tongue_down": {"TON": 130},
    "tongue_up": {"TON": 55},
    "narrow": {"CUL": 90, "CUR": 80, "CLL": 90, "CLR": 90},
    "wide": {"CUL": 65, "CUR": 105, "CLL": 120, "CLR": 65},
    "smile": {"CUL": 60, "CUR": 105, "CLL": 90, "CLR": 90},
    "frown": {"CUL": 100, "CUR": 75, "CLL": 90, "CLR": 90},
}
# The board program's servo limits (cogley_mouth_main.py; firmware/mouth_controls.py BOARD_LIMITS).
LIMITS = {
    "LUL": (40, 110), "LUR": (70, 140), "LLL": (55, 110), "LLR": (60, 110),
    "CUL": (60, 100), "CUR": (75, 105), "CLL": (90, 120), "CLR": (65, 90), "TON": (55, 130),
}
UPPER, LOWER = ("LUL", "LUR"), ("LLL", "LLR")
CORNERS = ("CUL", "CUR", "CLL", "CLR")
# Smile (+) or frown (-) under the corners per expression tag (speech.FACES)
MOOD = {"amused": 0.8, "excited": 0.6, "curious": 0.3, "surprised": 0.2,
        "irritated": -0.8, "skeptical": -0.5, "concentrating": -0.3, "confused": -0.2}
PIN = {"JL": 4, "JR": 5, "LUL": 6, "LUR": 7, "LLL": 8, "LLR": 9,
       "CUL": 10, "CUR": 11, "CLL": 12, "CLR": 13, "TON": 14}
RATE = 24000      # the voice's PCM: 16-bit mono

FLOOR_DB = -42.0  # a slice quieter than this (dBFS) shuts the mouth
LOUD_DB = -16.0   # this loud opens it to MAX_OPEN
MAX_OPEN = 0.85   # fraction of the OPEN pose the loudest syllables reach
ATTACK = 0.035    # s: how quickly the jaw opens towards a louder level
RELEASE = 0.09    # s: how quickly it closes again
DELAY = 0.05      # s the jaw runs behind the audio it was fed (the sound card's buffer)
HOLD = 0.12       # s without audio after which the mouth shuts
TICK = 0.02       # s between servo commands
LOOSE_AFTER = 3.0  # s after the last sound: let the jaw servos go so they do not hum (pin program only)
LIP_PART = 0.6     # how far the lips part at full opening: fraction of lips_up (upper) / lips_down (lower)
LIP_ATTACK, LIP_RELEASE = 0.06, 0.15   # s: the lips move more lazily than the jaw
DARK_HZ, BRIGHT_HZ = 400.0, 2500.0     # spectral centroid: narrow mouth .. wide mouth
WIDTH_SMOOTH = 0.12  # s: how quickly the corners follow the brightness
WIDTH_MAX = 0.7      # fraction of the WIDE pose the brightest sounds reach
MOOD_SMOOTH = 0.5    # s: a smile or frown comes on gradually
TONGUE = False       # False: no tongue servo fitted (2026-10-29), nothing is sent to TON
TONGUE_CHANCE = 0.2  # share of loud syllable onsets that flick the tongue
TONGUE_UP = 0.45     # how far up it flicks (fraction of tongue_up), for this long:
TONGUE_SECS = 0.14
GLIDE = 720       # deg/s glide speed asked of the board program (its default 90 is too slow to talk)


def find_port():
    """The first USB serial device, or None."""
    try:
        from serial.tools import list_ports
        ports = list(list_ports.comports())
        for p in ports:
            if "pico" in (p.description or "").lower() or "micropython" in (p.description or "").lower():
                return p.device
        for p in ports:
            if "usbmodem" in p.device or "USB" in (p.description or "") or p.device.startswith("COM"):
                return p.device
    except ImportError:
        pass
    found = sorted(glob.glob("/dev/cu.usbmodem*"))
    return found[0] if found else None


def analyse(pcm):
    """(loudness in dBFS, spectral centroid in Hz) of a 16-bit PCM slice; (-100, 0) for silence."""
    import numpy as np
    x = np.frombuffer(pcm[: len(pcm) // 2 * 2], dtype=np.int16).astype(np.float64)
    if not len(x):
        return -100.0, 0.0
    rms = math.sqrt(float(np.mean(x * x))) / 32768.0
    if rms <= 1e-5:
        return -100.0, 0.0
    spec = np.abs(np.fft.rfft(x * np.hanning(len(x))))
    freqs = np.fft.rfftfreq(len(x), 1.0 / RATE)
    power = spec * spec
    centroid = float((freqs * power).sum() / max(power.sum(), 1e-9))
    return 20 * math.log10(rms), centroid


def level_db(pcm):
    return analyse(pcm)[0]


class Mouth:
    def __init__(self, port="auto", log=None, eyes=True):
        import serial
        if port in (None, "auto"):
            port = find_port()
            if not port:
                raise OSError("no USB serial port: is the mouth Pico plugged in?")
        self.port = port
        self.log = log or (lambda **k: None)
        self.poses = {k: dict(v) for k, v in POSES.items()}
        self.vowels = {}   # saved vowel shapes from the mouth slider window, when all three exist
        if os.path.exists(POSES_FILE):
            with open(POSES_FILE) as f:
                saved = json.load(f)
            for k, v in saved.items():
                if k in self.poses:
                    self.poses[k].update(v)
            if all(k in saved for k in ("vowel_ah", "vowel_ee", "vowel_oo")):
                self.vowels = {k: dict(saved[k]) for k in ("vowel_ah", "vowel_ee", "vowel_oo")}
        self.ser = serial.serial_for_url(port, 115200, timeout=0)   # also socket:// (perform/body.py)
        self.cogley = self._ask_where() is not None
        if not self.cogley:
            self.ser.write(b"\x03\x03")   # a REPL left by Thonny, for one
            time.sleep(0.3)
            self.ser.write(b"\x04")       # soft reset: main.py starts
            time.sleep(1.5)
            self.cogley = self._ask_where() is not None
        self.ser.reset_input_buffer()
        self.program = "cogley_mouth_main.py" if self.cogley else "pico_servo_ctl.py"
        if self.cogley:
            self.ser.write(f"speed {GLIDE}\n".encode())
        self.lock = threading.Lock()
        self.levels = deque()         # (play at, open fraction 0..1, brightness 0..1) from feed()
        self.last_audio = 0.0
        self.open = 0.0               # where the jaw is now, 0 shut .. 1 the OPEN pose
        self.lips = 0.0               # how far the lips are parted, 0..1
        self.width = 0.0              # mouth width, 0 narrow .. 1 wide
        self.bright = 0.0             # latest brightness while loud
        self.mood = self.mood_target = 0.0   # smile + .. frown -
        self.asym = 0.0               # + his left corners more, - his right (the face engine)
        self.jaw_floor = 0.0          # the jaw open at least this much, 0..1 (the face engine)
        self.engine = False           # True once the face engine sets the expression
        self.tongue_until = 0.0
        self.sent = {}
        self.awake = False
        self.closed = False
        self.gaze = None   # gaze.Gaze: the eyes looking around and blinking, through the link
        self.rest()
        threading.Thread(target=self._run, daemon=True).start()
        if eyes:
            self.eyes_alive()

    def eyes_alive(self):
        """Start the eyes looking around and blinking (gaze.py) until close(). Without the saved
        eye poses they stay still, and the reason is printed and logged."""
        if self.gaze:
            return self.gaze
        sys.path.insert(0, HERE)
        import gaze
        try:
            self.gaze = gaze.Gaze(self, log=self.log)
        except ValueError as e:
            print(f"eyes stay still: {e}")
            self.log(what="eyes", state="still", why=str(e))
        return self.gaze

    def _ask_where(self):
        self.ser.reset_input_buffer()
        self.ser.write(b"where\n")
        reply, end = b"", time.time() + 1.0
        while time.time() < end:
            reply += self.ser.read(self.ser.in_waiting or 1)
            if b"JL=" in reply and reply.endswith(b"\n"):
                return reply
        return reply if b"JL=" in reply else None

    def send(self, socket, value):
        with self.lock:
            if self.cogley:
                self.ser.write(b"relax\n" if value == "off" else f"set {socket} {value}\n".encode())
            else:
                self.ser.write(f"{PIN[socket]} {value}\n".encode())
            self.ser.reset_input_buffer()

    def link(self, text):
        """Send a line to the eye board through the mouth board's link (pico_servo_ctl.py passes
        "e <text>" on over UART0, GP16 to GP17): link("8 90") moves the eyes' left/right servo.
        Both board programs (pico_servo_ctl.py, cogley_mouth_main.py) forward it."""
        with self.lock:
            self.ser.write(f"e {text}\n".encode())
            self.ser.reset_input_buffer()

    def rest(self):
        """Mouth closed, lips at rest; the servos hold."""
        if self.cogley:
            with self.lock:
                self.ser.write(b"rest\n")   # its start-up pose, gliding
            time.sleep(0.6)
            self.sent = {"jaw": 0.0}
            for socket, a in self.poses["lips_rest"].items():   # `rest` leaves the lips unpowered
                self.send(socket, a)
                self.sent[socket] = a
                time.sleep(0.12)
        else:
            for socket, a in list(self.poses["mouth_closed"].items()) + list(self.poses["lips_rest"].items()):
                self.send(socket, a)
                self.sent[socket] = a
                time.sleep(0.12)   # one servo at a time, so they don't all start together on the supply
        self.awake = True

    def feed(self, pcm):
        """A slice of the voice's PCM that is being played now."""
        db, centroid = analyse(pcm)
        frac = max(0.0, min(1.0, (db - FLOOR_DB) / (LOUD_DB - FLOOR_DB)))
        bright = max(0.0, min(1.0, (centroid - DARK_HZ) / (BRIGHT_HZ - DARK_HZ)))
        t = time.monotonic()
        self.levels.append((t + DELAY, frac, bright))
        self.last_audio = t

    def face(self, name):
        """The expression tag of the piece starting now: a smile or a frown under the corners.
        Ignored once the face engine (frank/engine) drives the expression."""
        if self.engine:
            return
        self.mood_target = MOOD.get(name or "", 0.0)
        self.log(what="face", face=name, mood=self.mood_target)

    def expression(self, smile, asym=0.0, jaw_floor=0.0):
        """The face engine's emotion part of the mouth, every tick: smile (+) or frown (-) under
        the corners, how one-sided it is, and a jaw floor (surprise). Already smoothed."""
        self.engine = True
        self.mood = self.mood_target = max(-1.0, min(1.0, smile))
        self.asym = max(-1.0, min(1.0, asym))
        self.jaw_floor = max(0.0, min(1.0, jaw_floor))

    def _corner(self, s, a):
        """A corner's angle with the one-sided part of the expression: Cogley's L corners take
        more of it when asym > 0 (his L and R are not yet matched to the face: check on the head)."""
        if not self.asym:
            return a
        side = 1.0 + self.asym if s in ("CUL", "CLL") else 1.0 - self.asym
        rest = self.poses["narrow"][s]
        return rest + (a - rest) * side

    def flush(self):
        """An interruption: forget what was queued, shut now."""
        self.levels.clear()
        self.last_audio = 0.0

    def _set(self, socket, a):
        lo, hi = LIMITS.get(socket, (0, 180))
        a = round(max(lo, min(hi, a)))
        if self.sent.get(socket) != a:
            self.send(socket, a)
            self.sent[socket] = a

    def _lips(self, t):
        """Lips, corners and tongue from the smoothed lips / width / mood state."""
        P = self.poses
        if self.vowels:
            return self._vowel_lips(t)
        part = self.lips * LIP_PART
        for s in UPPER:
            self._set(s, P["lips_rest"][s] + part * (P["lips_up"][s] - P["lips_rest"][s]))
        for s in LOWER:
            self._set(s, P["lips_rest"][s] + part * (P["lips_down"][s] - P["lips_rest"][s]))
        mood_pose = P["smile"] if self.mood >= 0 else P["frown"]
        for s in CORNERS:
            a = P["narrow"][s] + self.width * WIDTH_MAX * (P["wide"][s] - P["narrow"][s])
            a += abs(self.mood) * (mood_pose[s] - P["narrow"][s])
            self._set(s, self._corner(s, a))
        if TONGUE:
            down, up = P["tongue_down"]["TON"], P["tongue_up"]["TON"]
            self._set("TON", down + (TONGUE_UP * (up - down) if t < self.tongue_until else 0))

    def _vowel_shape(self):
        """The saved vowel shape for the current brightness: OO (dark) .. AH .. EE (bright)."""
        b = self.width   # smoothed brightness, 0..1
        if b < 0.5:
            lo, hi, k = self.vowels["vowel_oo"], self.vowels["vowel_ah"], b * 2
        else:
            lo, hi, k = self.vowels["vowel_ah"], self.vowels["vowel_ee"], (b - 0.5) * 2
        return {s: lo[s] + k * (hi.get(s, lo[s]) - lo[s]) for s in lo}

    def _vowel_lips(self, t):
        """Lips and corners: the rest face moved `lips` of the way to the vowel shape, plus the mood."""
        P = self.poses
        shape = self._vowel_shape()
        rest = dict(P["lips_rest"]); rest.update(P["narrow"])
        mood_pose = P["smile"] if self.mood >= 0 else P["frown"]
        for s in UPPER + LOWER + CORNERS:
            if s not in shape:
                continue
            a = rest[s] + self.lips * (shape[s] - rest[s])
            if s in CORNERS:
                a += abs(self.mood) * (mood_pose[s] - P["narrow"][s])
                a = self._corner(s, a)
            self._set(s, a)
        if TONGUE:
            down, up = P["tongue_down"]["TON"], P["tongue_up"]["TON"]
            self._set("TON", down + (TONGUE_UP * (up - down) if t < self.tongue_until else 0))

    def _jaw(self, frac):
        if self.vowels and "JL" in self.vowels["vowel_ah"]:
            # the jaw opening of the vowel shape, scaled by how open the mouth is
            closed, opened = self.poses["mouth_closed"]["JL"], self.poses["mouth_open"]["JL"]
            shape_jaw = (self._vowel_shape()["JL"] - closed) / ((opened - closed) or 1)
            frac = max(0.0, min(1.0, frac / MAX_OPEN * shape_jaw))
        if self.cogley:
            v = round(frac, 2)
            if self.sent.get("jaw") != v:
                with self.lock:
                    self.ser.write(f"jaw {v}\n".encode())
                    self.ser.reset_input_buffer()
                self.sent["jaw"] = v
            return
        if frac == 0.0 and getattr(self, "loose", False):
            return   # let go after LOOSE_AFTER: stays loose until the mouth opens again
        self.loose = False
        for socket, closed in self.poses["mouth_closed"].items():
            opened = self.poses["mouth_open"].get(socket, closed)
            a = round(closed + frac * (opened - closed))
            if self.sent.get(socket) != a:
                self.send(socket, a)
                self.sent[socket] = a

    def _run(self):
        import random
        target, tick = 0.0, 0
        while not self.closed:
            t = time.monotonic()
            while self.levels and self.levels[0][0] <= t:
                _, target, bright = self.levels.popleft()
                if target > 0.3:
                    self.bright = bright
            if t - self.last_audio > HOLD + DELAY:
                target = 0.0
            was = self.open
            k = TICK / (ATTACK if target > self.open else RELEASE)
            self.open += (target - self.open) * min(1.0, k)
            if self.open < 0.005:
                self.open = 0.0
            if TONGUE and was < 0.35 <= self.open and random.random() < TONGUE_CHANCE:   # a syllable onset
                self.tongue_until = t + TONGUE_SECS
            k = TICK / (LIP_ATTACK if target > self.lips else LIP_RELEASE)
            self.lips += (target - self.lips) * min(1.0, k)
            width_target = self.bright if target > 0.15 else self.width * 0.5
            self.width += (width_target - self.width) * min(1.0, TICK / WIDTH_SMOOTH)
            self.mood += (self.mood_target - self.mood) * min(1.0, TICK / MOOD_SMOOTH)
            tick += 1
            if self.awake:
                self._jaw(max(self.open * MAX_OPEN, self.jaw_floor))
                if tick % 2 == 0:
                    self._lips(t)
                if self.open == 0.0 and self.jaw_floor == 0.0 and t - self.last_audio > LOOSE_AFTER and not self.cogley \
                        and any(s in self.sent for s in self.poses["mouth_closed"]):
                    for socket in self.poses["mouth_closed"]:
                        self.send(socket, "off")
                        self.sent.pop(socket, None)
                    self.loose = True   # it switched them on again the next tick (2026-10-30)
            time.sleep(TICK)

    def close(self):
        if self.gaze:
            self.gaze.stop()
        self.closed = True
        time.sleep(TICK * 2)
        self.open = self.lips = self.width = self.mood = 0.0
        self.tongue_until = 0.0
        self._jaw(0.0)
        self._lips(time.monotonic())
        time.sleep(0.4)
        if not self.cogley:   # the board program keeps holding the rest pose
            for socket in list(self.sent):
                self.send(socket, "off")
        self.ser.close()


def _test(mouth):
    """Flap the jaw on a made-up envelope: syllables of 120 to 220 ms with gaps."""
    import random
    import numpy as np
    random.seed(2)
    print("test: 6 s of pretend syllables")
    end = time.monotonic() + 6.0
    while time.monotonic() < end:
        loud = random.uniform(0.3, 1.0)
        dark = random.random() < 0.5                 # "oo" (narrow) or "ee" (wide)
        for _ in range(random.randint(6, 11)):      # one syllable, 20 ms slices
            amp = loud * random.uniform(0.7, 1.0) * 32767 * 10 ** (LOUD_DB / 20)
            x = np.random.uniform(-1, 1, RATE // 50)
            if dark:
                x = np.convolve(x, np.ones(24) / 24, mode="same") * 4   # low-passed: a dark vowel
            mouth.feed((np.clip(x, -1, 1) * amp).astype(np.int16).tobytes())
            time.sleep(0.02)
        time.sleep(random.uniform(0.04, 0.25))
    time.sleep(0.5)


def _say(mouth, text):
    sys.path.insert(0, HERE)
    import speech
    import voice
    v = voice.Voice.from_config()
    if not v:
        sys.exit("No voice yet (frank/voice.json).")
    v.mouth = mouth
    face, chuckle = None, False
    for kind, value in speech.parse(text):
        if kind == "face":
            face = value
        elif kind == "sound":
            chuckle = True
        else:
            v.say(value, face, chuckle)
            chuckle = False
    v.wait()
    time.sleep(0.5)
    if v.error:
        print(v.error)


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    port = args[0] if args else "auto"
    m = Mouth(port, eyes="--still-eyes" not in sys.argv)
    print(f"mouth: {m.port}, board program {m.program}; closed {m.poses['mouth_closed']}, open {m.poses['mouth_open']}; "
          f"eyes {'alive' if m.gaze else 'still'}")
    try:
        if "--say" in sys.argv:
            _say(m, sys.argv[sys.argv.index("--say") + 1])
        else:
            _test(m)
    finally:
        m.close()

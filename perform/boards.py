"""
Models of the servo-board programs: what a board does with each command line it is sent, so the
body server (body.py) knows every servo's pulse without asking the board. The boards say almost
nothing back (the eye board nothing at all), so the twin follows the commands, through the same
rules the board program applies: its clamps, its glide, its jaw and pose commands, its link to
the next board. With no board plugged in (body.py --sim) the model is the board, and answers
the way the real one would.

Each model keeps, per output pin, the pulse the board sends (us) and whether it sends one at
all (live). The servo's own travel time (deg/s from robot.json's servo types) is applied on top
in the body server, since the board doesn't know it.

  pico_servo_ctl  firmware/pico_servo_ctl.py: "<pin> <deg>", "<pin> off", "e <line>" on to the
                  next board. Pulses jump; -27..207 deg = 200..2800 us.
  cogley_mouth    firmware/cogley_mouth_main.py (TalkingHead's gliding MouthMaster): servo names,
                  each clamped to his poses' range and gliding at `speed` deg/s; jaw, poses,
                  talk, rest, relax, where; 0..180 deg = 544..2400 us. "e <line>" as above.

A new board program gets a class here with the same three methods (line, tick, reset) and an
entry in FIRMWARE.
"""
import random

FIRMWARE = {}


def firmware(name):
    def reg(cls):
        cls.name = name
        FIRMWARE[name] = cls
        return cls
    return reg


class Board:
    """Base: pins -> {"us": pulse, "live": bool}. line() returns (reply text or None, forwarded
    line or None); tick(dt) advances anything the board does over time."""
    US0, US_PER_DEG = 500.0, 2000.0 / 180.0
    PINS = ()

    def __init__(self, seed=None):
        self.rng = random.Random(seed)
        self.pins = {}
        self.running = True        # False after a Ctrl-C: main.py stopped, the REPL waits
        self.reset()

    def pulse(self, deg):
        return self.US0 + deg * self.US_PER_DEG

    def degrees(self, us):
        return (us - self.US0) / self.US_PER_DEG

    def control(self, byte):
        """A control character from the PC: Ctrl-C stops main.py, Ctrl-D soft-resets and runs it."""
        if byte == b"\x03":
            self.running = False
            return None
        if byte == b"\x04":
            self.running = True
            self.reset()
            return self.banner()
        return None

    def banner(self):
        return None

    def reset(self):
        raise NotImplementedError

    def line(self, text):
        raise NotImplementedError

    def tick(self, dt):
        pass

    def state(self):
        return {p: dict(s) for p, s in self.pins.items()}


@firmware("pico_servo_ctl")
class PicoServoCtl(Board):
    PINS = tuple(range(4, 16))

    def reset(self):
        self.pins = {p: {"us": self.pulse(90), "live": False} for p in self.PINS}

    def line(self, text):
        if not self.running:
            return None, None
        w = text.split()
        if not w:
            return None, None
        if w[0] == "e":
            return None, (" ".join(w[1:]) if len(w) > 1 else None)
        if len(w) != 2:
            return None, None
        try:
            pin = int(w[0])
        except ValueError:
            return None, None
        if pin not in self.pins:
            return None, None
        if w[1] == "off":
            self.pins[pin]["live"] = False
            return None, None
        try:
            a = max(-27.0, min(207.0, float(w[1])))
        except ValueError:
            return None, None
        self.pins[pin] = {"us": float(int(self.pulse(a))), "live": True}
        return None, None


@firmware("cogley_mouth")
class CogleyMouth(Board):
    """Port of cogley_mouth_main.py's command handling and glide (keep the two in step)."""
    US0, US_PER_DEG = 544.0, (2400.0 - 544.0) / 180.0
    SPEED, TALK_SPEED, TALK_OPEN, JAW_DEG, JAW_CAP, JAW_DIR = 90.0, 300.0, 0.7, 40.0, 70.0, -1
    LIMITS = {"JL": 4, "JR": 5, "LUL": (6, 40, 110), "LUR": (7, 70, 140), "LLL": (8, 55, 110),
              "LLR": (9, 60, 110), "CUL": (10, 60, 100), "CUR": (11, 75, 105), "CLL": (12, 90, 120),
              "CLR": (13, 65, 90), "TON": (14, 55, 130)}
    NAMES = ("JL", "JR", "LUL", "LUR", "LLL", "LLR", "CUL", "CUR", "CLL", "CLR", "TON")
    POSES = {
        "mouth_closed": {"JL": 90, "JR": 90}, "mouth_open": {"JL": 50, "JR": 130},
        "lips_down": {"LUL": 110, "LUR": 70, "LLL": 55, "LLR": 110},
        "lips_up": {"LUL": 40, "LUR": 140, "LLL": 110, "LLR": 60},
        "tongue_down": {"TON": 130}, "tongue_up": {"TON": 55},
        "smile": {"CUL": 60, "CUR": 105, "CLL": 90, "CLR": 90}, "frown": {"CUL": 100, "CUR": 75, "CLL": 90, "CLR": 90},
        "wide": {"CUL": 65, "CUR": 105, "CLL": 120, "CLR": 65}, "narrow": {"CUL": 90, "CUR": 80, "CLL": 90, "CLR": 90}}
    REST = ("mouth_closed", "tongue_down", "narrow")
    LINK = ("eyes_move", "eyes_open", "eyes_close", "brows_up", "brows_down", "brows_happy", "brows_angry")
    PINS = (4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14)

    def reset(self):
        self.speed, self.jaw_deg, self.jaw_dir = self.SPEED, self.JAW_DEG, self.JAW_DIR
        self.j = {}
        for n in self.NAMES:
            lim = self.LIMITS[n]
            pin, lo, hi = (lim,) + self.jaw_range(-1 if n == "JL" else 1) if isinstance(lim, int) else lim
            self.j[n] = {"pin": pin, "lo": lo, "hi": hi, "pos": 90.0, "target": 90.0, "live": False}
        self.talk_on, self.talk_amount, self.talk_next, self.talk_left, self.talk_open = False, self.TALK_OPEN, 0.0, 0, False
        self.clock = 0.0
        for pose in self.REST:
            self.apply_pose(pose)
        self._pins()

    def banner(self):
        return "Ready to receive commands (help for a list)"

    def jaw_range(self, side):
        a = 90 + side * self.jaw_dir * self.jaw_deg
        return (min(90, a), max(90, a))

    def aim(self, n, angle):
        s = self.j[n]
        a = min(max(angle, s["lo"]), s["hi"])
        s["target"], s["live"] = float(a), True
        return a

    def report(self, n, asked, got):
        return None if got == asked else f"{n} {asked:g} is past its limit; using {got:g}"

    def apply_pose(self, pose):
        out = [self.report(n, a, self.aim(n, a)) for n, a in self.POSES[pose].items()]
        return "\n".join(r for r in out if r) or None

    def set_jaw(self, f):
        f = min(max(f, 0.0), 1.0)
        self.aim("JL", 90 - self.jaw_dir * self.jaw_deg * f)
        self.aim("JR", 90 + self.jaw_dir * self.jaw_deg * f)

    def set_jaw_limits(self):
        self.j["JL"]["lo"], self.j["JL"]["hi"] = self.jaw_range(-1)
        self.j["JR"]["lo"], self.j["JR"]["hi"] = self.jaw_range(1)

    def line(self, text):
        """(reply, forwarded line). The reply is what the board prints: "Received: ..." for every
        line except the link's, then the command's own answer."""
        if not self.running:
            return None, None
        w = text.split()
        if not w:
            return None, None
        cmd, args = w[0], w[1:]
        echo = None if cmd == "e" else "Received: " + text.strip()
        try:
            reply, fwd = self.do(cmd, args)
        except (ValueError, IndexError) as e:   # the board prints the exception
            reply, fwd = f"Error: {e}", None
        self._pins()
        return "\n".join(r for r in (echo, reply) if r) or None, fwd

    def do(self, cmd, args):
        if cmd in ("on", "off") or cmd in self.LINK:
            return None, None
        if cmd == "e":
            return None, (" ".join(args) if args else None)
        if cmd == "mouth_open":
            self.talk_on = False
            self.set_jaw(1)
        elif cmd in self.POSES:
            if cmd == "mouth_closed":
                self.talk_on = False
            return self.apply_pose(cmd), None
        elif cmd == "jaw":
            self.talk_on = False
            self.set_jaw(float(args[0]))
        elif cmd == "jawdeg":
            if args:
                self.jaw_deg = min(max(float(args[0]), 10), self.JAW_CAP)
                self.set_jaw_limits()
            return f"jawdeg {self.jaw_deg:g}", None
        elif cmd == "jawdir":
            if args:
                self.talk_on = False
                self.set_jaw(0)
                self.jaw_dir = -1 if float(args[0]) < 0 else 1
                self.set_jaw_limits()
            return f"jawdir {self.jaw_dir}", None
        elif cmd == "talk":
            self.talk_on, self.talk_amount = True, min(max(float(args[0]) if args else self.TALK_OPEN, 0.0), 1.0)
            self.talk_next, self.talk_left, self.talk_open = self.clock, 0, False
        elif cmd == "stop":
            self.talk_on = False
            self.set_jaw(0)
        elif cmd == "set":
            n = args[0].upper()
            if n not in self.j:
                return f"no servo {n}; servos: {' '.join(self.NAMES)}", None
            if n in ("JL", "JR"):
                self.talk_on = False
            a = float(args[1])
            return self.report(n, a, self.aim(n, a)), None
        elif cmd == "speed":
            self.speed = min(max(float(args[0]), 5), 600)
        elif cmd == "rest":
            self.talk_on = False
            for pose in self.REST:
                self.apply_pose(pose)
        elif cmd == "relax":
            self.talk_on = False
            for s in self.j.values():
                s["live"] = False
        elif cmd == "where":
            return " ".join(f"{n}={int(self.j[n]['pos'] + 0.5)}" if self.j[n]["live"] else f"{n}=off"
                            for n in self.NAMES), None
        elif cmd == "help":
            return "commands: (see firmware/cogley_mouth_main.py)", None
        else:
            return "Unknown command", None
        return None, None

    def where(self, text):
        """The real board's answer to `where` (JL=90 JR=off ...): take its positions as true."""
        for item in text.split():
            n, _, v = item.partition("=")
            if n in self.j:
                if v == "off":
                    self.j[n]["live"] = False
                else:
                    try:
                        self.j[n]["pos"] = float(v)
                    except ValueError:
                        pass
        self._pins()

    def tick(self, dt):
        if not self.running:
            return
        self.clock += dt
        if self.talk_on and self.clock >= self.talk_next:
            if self.talk_open:
                self.set_jaw(self.rng.uniform(0.0, 0.1) * self.talk_amount)
                wait, self.talk_open = self.rng.randint(60, 140), False
            elif self.talk_left > 0:
                self.set_jaw(self.rng.uniform(0.4, 1.0) * self.talk_amount)
                wait, self.talk_open = self.rng.randint(90, 220), True
                self.talk_left -= 1
            else:
                self.set_jaw(0)
                wait, self.talk_left = self.rng.randint(150, 600), self.rng.randint(1, 4)
            self.talk_next = self.clock + wait / 1000.0
        jaw_speed = self.TALK_SPEED if self.talk_on else self.speed
        for n, s in self.j.items():
            if not s["live"]:
                continue
            step = (jaw_speed if n in ("JL", "JR") else self.speed) * dt
            d = s["target"] - s["pos"]
            s["pos"] = s["target"] if abs(d) <= step else s["pos"] + (step if d > 0 else -step)
        self._pins()

    def _pins(self):
        self.pins = {s["pin"]: {"us": self.pulse(s["pos"]), "live": s["live"]} for s in self.j.values()}

"""
Brow animation for the four brow servos: the expressions of CHARACTER.md section 6, and an
idle layer of small random brow movements.

Plain Python (only `random`), like eye_anim.py, so it runs in servo_controls.py on the PC and
in MicroPython on a Pico. BrowAnim.step(t) takes the time in seconds and returns
{socket: angle} for the four brow servos, named by their mouth-board sockets (bench layout:
JL left outer, LUL left inner, JR right outer, LUR right inner, sides as seen from the front).

A pose is {socket: fraction}: +1 = fully raised, -1 = fully lowered (furrowed), 0 = level.
The angle is level + DIR * fraction * RAISE (or LOWER) degrees, and never goes past the
level by more than RAISE up or LOWER down, so the animation cannot push a brow bar further
than those two numbers, which are set on the slider window.
"""

import random

LEFT_OUTER, LEFT_INNER, RIGHT_OUTER, RIGHT_INNER = "JL", "LUL", "JR", "LUR"
SOCKETS = (LEFT_OUTER, LEFT_INNER, RIGHT_OUTER, RIGHT_INNER)

# Which way each servo turns to RAISE its end of the brow bar, from Cogley's Brows.py (Up: LO
# 120, LI 60, RI 120, RO 60 around a level 90). Not yet checked on the team's build: if a brow
# goes down on CURIOUS, flip its sign here.
DIR = {LEFT_OUTER: +1, LEFT_INNER: -1, RIGHT_OUTER: -1, RIGHT_INNER: +1}

RAISE = 35.0   # deg a brow end goes up from level at fraction +1 (Cogley's Brows.py: 30)
LOWER = 20.0   # deg a brow end goes down from level at fraction -1 (his: 10, which barely showed)

# Idle layer (BROWS ALIVE): small random movements on top of the expression.
IDLE_AMOUNT = 0.2         # fraction: how far the idle twitches go
IDLE_GAP = (1.5, 6.0)     # s between idle movements
TWITCH_CHANCE = 0.25      # share of idle moves that are a quick flick and back


def ease(x):
    x = min(1.0, max(0.0, x))
    return x * x * (3 - 2 * x)


def clamp(x, lo=-1.0, hi=1.0):
    return min(hi, max(lo, x))


def pose(lo=0.0, li=0.0, ro=0.0, ri=0.0):
    return {LEFT_OUTER: lo, LEFT_INNER: li, RIGHT_OUTER: ro, RIGHT_INNER: ri}


def both(up):
    """Both brows up (or down, if up < 0) by the same amount."""
    return pose(up, up, up, up)


LEVEL = both(0.0)

# Each expression is a list of keyframes (move_time s, hold s, pose). The brows ease to the
# pose over move_time, hold it, then go on to the next keyframe; they stay on the last pose
# until another expression is played. The shapes follow CHARACTER.md section 6.
EXPRESSIONS = {
    "neutral": [(0.6, 0.0, LEVEL)],
    # Curiosity: raised eyebrows
    "curious": [(0.35, 0.0, both(0.6))],
    # Excitement: strong bilateral brow lift
    "excited": [(0.2, 0.0, both(1.0))],
    # Skepticism: one brow higher than the other
    "skeptical": [(0.4, 0.0, pose(lo=0.8, li=0.6, ro=-0.2, ri=-0.4))],
    # Amusement: raised brow (one), the other relaxed
    "amused": [(0.4, 0.0, pose(lo=0.5, li=0.3, ro=0.1, ri=0.0))],
    # Concentration: subtle brow furrow (inner ends down more than the outer)
    "concentrating": [(0.7, 0.0, pose(lo=-0.2, li=-0.5, ro=-0.2, ri=-0.5))],
    # Confusion: brow furrow followed by a questioning lift (one brow leads)
    "confused": [(0.4, 0.6, pose(lo=-0.3, li=-0.7, ro=-0.3, ri=-0.7)),
                 (0.3, 0.0, pose(lo=0.7, li=0.5, ro=0.2, ri=0.1))],
    # Irritation: lowered eyebrows, controlled and deliberate
    "irritated": [(0.8, 0.0, both(-0.8))],
    # Surprise: sharp brow elevation, then a gradual return to relaxed
    "surprised": [(0.12, 0.8, both(1.0)), (2.0, 0.0, both(0.15))],
    # Vulnerability: subtle inward brow lift (inner ends up, outer ends a little down)
    "vulnerable": [(0.9, 0.0, pose(lo=-0.15, li=0.5, ro=-0.15, ri=0.5))],
    # Greeting: both eyebrows rise, then settle a little while he studies the visitor
    "greeting": [(0.25, 0.7, both(0.9)), (0.8, 0.0, both(0.4))],
    # Furrow and release: a plain test of the down direction
    "furrow": [(0.5, 0.0, both(-1.0))],
}
ORDER = ("neutral", "curious", "excited", "skeptical", "amused", "concentrating",
         "confused", "irritated", "surprised", "vulnerable", "greeting")


class BrowAnim:
    def __init__(self, level, t, raise_deg=RAISE, lower_deg=LOWER, idle=False):
        self.level = level                 # {socket: angle of the level brows}
        self.raise_deg, self.lower_deg = raise_deg, lower_deg
        self.idle = idle
        self.start = self.target = dict(LEVEL)   # expression pose, fractions
        self.move_at, self.move_time = t, 0.0
        self.queue = []                    # keyframes still to play: (move_time, hold, pose)
        self.next_key = t
        self.idle_start = self.idle_target = dict(LEVEL)
        self.idle_move_at, self.idle_move_time = t, 0.0
        self.idle_return = None            # time a twitch flicks back, or None
        self.next_idle = t + random.uniform(*IDLE_GAP)

    def play(self, name, t):
        """Start an expression (a key of EXPRESSIONS), replacing any that is still playing."""
        self.start = self.current(t)
        self.queue = list(EXPRESSIONS[name])
        self.next_key = t
        self.move_time = 0.0

    def current(self, t):
        k = ease((t - self.move_at) / self.move_time) if self.move_time else 1.0
        return {s: self.start[s] + (self.target[s] - self.start[s]) * k for s in SOCKETS}

    def idle_pose(self, t):
        k = ease((t - self.idle_move_at) / self.idle_move_time) if self.idle_move_time else 1.0
        return {s: self.idle_start[s] + (self.idle_target[s] - self.idle_start[s]) * k for s in SOCKETS}

    def idle_move(self, t, target, move_time):
        self.idle_start = self.idle_pose(t)
        self.idle_target = target
        self.idle_move_at, self.idle_move_time = t, move_time

    def step(self, t):
        if self.queue and t >= self.next_key:
            move_time, hold, target = self.queue.pop(0)
            self.start = self.current(t)
            self.target = dict(target)
            self.move_at, self.move_time = t, move_time
            self.next_key = t + move_time + hold
        if self.idle:
            if self.idle_return is not None and t >= self.idle_return:
                self.idle_move(t, dict(LEVEL), 0.25)
                self.idle_return = None
            elif t >= self.next_idle:
                r = random.random()
                a = IDLE_AMOUNT
                if r < TWITCH_CHANCE:       # a quick flick of one brow, and back
                    side = random.choice(((LEFT_OUTER, LEFT_INNER), (RIGHT_OUTER, RIGHT_INNER)))
                    target = dict(LEVEL)
                    for s in side:
                        target[s] = random.uniform(0.5, 1.0) * a
                    self.idle_move(t, target, 0.12)
                    self.idle_return = t + 0.12 + random.uniform(0.15, 0.4)
                elif r < 0.6:               # a slow drift of both brows, asymmetric
                    target = {s: random.uniform(-a, a) for s in SOCKETS}
                    self.idle_move(t, target, random.uniform(0.6, 1.5))
                else:                       # settle back towards level
                    self.idle_move(t, dict(LEVEL), random.uniform(0.5, 1.0))
                self.next_idle = t + random.uniform(*IDLE_GAP)
        elif self.idle_target != LEVEL:
            self.idle_move(t, dict(LEVEL), 0.5)
        return self.angles(self.current(t), self.idle_pose(t) if self.idle or self.idle_move_time else None)

    def rest(self):
        """The level brows, for when the animation stops."""
        return self.angles(dict(LEVEL), None)

    def angles(self, expr, idle):
        out = {}
        for s in SOCKETS:
            f = clamp(expr[s] + (idle[s] if idle else 0.0))
            deg = f * (self.raise_deg if f > 0 else self.lower_deg)
            out[s] = self.level[s] + DIR[s] * deg
        return out

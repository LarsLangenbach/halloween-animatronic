"""
Random idle animation for the EyeMech: the eyes look around and blink.

Plain Python (only `random`), so the same file runs on the PC in servo_controls.py and in
MicroPython on a Pico. EyeAnim.step(t) takes the time in seconds and returns
{socket: angle} for the six eye servos, named by their mouth-board sockets (bench layout).

The poses come from the slider window (eye_poses.json): each lid's SHUT and OPEN angles
and the gaze CENTRE. A lid only ever moves between its SHUT and OPEN angles, so the
animation cannot drive it past a pose that was set by hand.
"""

import random

LR, UD = "LLL", "LLR"           # gaze: left / right, up / down
TOP_LIDS = ("CUR", "CLR")       # top lid of the eye on your right, on your left
BOTTOM_LIDS = ("CUL", "CLL")    # bottom lid of the eye on your right, on your left

LOOK_LR = 30      # deg the eyes look to each side of the centre
LOOK_UD = 15      # deg the eyes look up and down from the centre
UD_UP = 1         # +1: a higher UD angle looks up (Cogley's eyes.py); -1 if it looks down
LID_REST = 0.85   # how open the lids sit: 0 = SHUT pose, 1 = OPEN pose
LID_FOLLOW_TOP = 0.25     # looking up opens the top lids this much; looking down lowers them
LID_FOLLOW_BOTTOM = 0.15  # looking up raises the bottom lids this much; looking down drops them
WAKE = 1.0        # s for the lids to open from shut when the animation starts
MOVE_BOTTOM_LIDS = True   # False: the bottom lids hold their OPEN angle and only the top lids blink

# Blink shapes: (close, hold, open) in s. Lids shut faster than they open.
BLINK = (0.08, 0.05, 0.15)
SLOW_BLINK = (0.25, 0.25, 0.45)


def ease(x):
    x = min(1.0, max(0.0, x))
    return x * x * (3 - 2 * x)


def clamp(x, lo=-1.0, hi=1.0):
    return min(hi, max(lo, x))


class EyeAnim:
    def __init__(self, shut, opened, centre, t):
        self.shut, self.open, self.centre = shut, opened, centre
        self.t0 = t
        self.start = self.target = (0.0, 0.0)   # gaze, -1..1 each way; (0, 0) = centre
        self.move_at, self.move_time = t, 0.0
        self.next_look = t + WAKE + 0.5
        self.blinks = []                         # (start, close, hold, open)
        self.next_blink = t + WAKE + random.uniform(1.5, 4.0)

    def gaze(self, t):
        k = ease((t - self.move_at) / self.move_time) if self.move_time else 1.0
        return tuple(a + (b - a) * k for a, b in zip(self.start, self.target))

    def look(self, t):
        gx, gy = self.start = self.gaze(t)
        r = random.random()
        if r < 0.3:      # a small shift near where it already looks
            x, y = gx + random.uniform(-0.15, 0.15), gy + random.uniform(-0.1, 0.1)
        elif r < 0.55:   # back to about straight ahead
            x, y = random.uniform(-0.2, 0.2), random.uniform(-0.15, 0.15)
        else:            # anywhere
            x, y = random.uniform(-1, 1), random.uniform(-0.8, 0.8)
        self.target = (clamp(x), clamp(y))
        dist = ((self.target[0] - gx) ** 2 + (self.target[1] - gy) ** 2) ** 0.5
        self.move_at, self.move_time = t, 0.08 + 0.15 * dist
        if dist > 0.7 and random.random() < 0.3:   # big glances often come with a blink
            self.blink(t, BLINK)
        hold = random.uniform(0.3, 1.5) if random.random() < 0.7 else random.uniform(1.5, 4.0)
        self.next_look = t + self.move_time + hold

    def blink(self, t, shape):
        self.blinks.append((t,) + shape)

    def closure(self, t):
        """How shut the blinks make the lids at time t: 0 open, 1 shut."""
        c = 0.0
        for s, close, hold, opening in self.blinks:
            d = t - s
            if d < 0:
                continue
            if d < close:
                c = max(c, ease(d / close))
            elif d < close + hold:
                c = 1.0
            else:
                c = max(c, 1 - ease((d - close - hold) / opening))
        self.blinks = [b for b in self.blinks if t < b[0] + sum(b[1:])]
        return c

    def step(self, t):
        if t >= self.next_look:
            self.look(t)
        if t >= self.next_blink:
            shape = SLOW_BLINK if random.random() < 0.1 else BLINK
            self.blink(t, shape)
            if random.random() < 0.15:   # double blink
                self.blink(t + sum(shape) + 0.08, BLINK)
            self.next_blink = t + random.uniform(2.5, 7.0)
        x, y = self.gaze(t)
        lids = (1 - self.closure(t)) * ease((t - self.t0) / WAKE)
        return self.pose(x, y, lids)

    def rest(self):
        """Centred and shut (the neutral face), for when the animation stops."""
        return self.pose(0.0, 0.0, 0.0)

    def pose(self, x, y, lids):
        out = {LR: self.centre[LR] + x * LOOK_LR, UD: self.centre[UD] + UD_UP * y * LOOK_UD}
        top = clamp(LID_REST + LID_FOLLOW_TOP * y, 0.0, 1.0) * lids
        bottom = clamp(LID_REST - LID_FOLLOW_BOTTOM * y, 0.0, 1.0) * lids if MOVE_BOTTOM_LIDS else 1.0
        for sockets, frac in ((TOP_LIDS, top), (BOTTOM_LIDS, bottom)):
            for s in sockets:
                out[s] = self.shut[s] + frac * (self.open[s] - self.shut[s])
        return out

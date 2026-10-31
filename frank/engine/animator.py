"""
The animator, the puppeteer's hands (docs/FACE_ENGINE.md, "Animator"). Fifty times a second it
takes the synthesiser's face target and the orchestrator's cue and returns the joint channels
of channels.JOINTS, smoothed and inside their ranges. rig.py turns those into servo angles.

Layers, lowest first (reports/Robot face emotion animation.md, "The animator composes layers"):
  L0 rest            channels.rest_joints()
  L1 alive           blinks (state rates, refractory, skewed gaps, gaze-evoked, doubles),
                     saccades (idle look-around, engaged eye-eye-nose jumps around a target),
                     slow noise drift on brows, corners and lids
  L2 face            the synthesiser's brows, lids, corners, jaw floor and gaze bias
  L3 state           aversions while listening and speaking, the thinking look, the entry
                     reactions of greeting, interrupted and farewell
  L4 speech          brow beats on loud onsets of his own voice (cue["talk"])
  L5 one-shots       cue["events"]: blink, long_blink, flinch, greet, beat, phrase_end

Then per channel: clamp, a short delay line (stagger: lids first, brows, then the mouth, his
favoured side leading), a critically damped spring (Daniel Holden's half-life form, frame-rate
independent, shorter with arousal) and a speed cap. Saccades and blink closures skip the
spring: a 10 deg saccade takes ~43 ms, one or two ticks.

Plain standard-library Python. Time is passed in (time.monotonic() seconds); the random source
is a random.Random you can seed (Animator(seed=...)), so tests are repeatable.

The eye and brow logic is absorbed from firmware/eye_anim.py and firmware/brow_anim.py (copied,
not imported: the engine must not depend on the slider tools).
"""

import math
import random

from .channels import BROWS, JOINTS, LIDS_BOT, LIDS_TOP, STATES, clamp, rest_joints

# --- Gaze ---------------------------------------------------------------------------------
GAZE_DEG_X = 30.0     # deg of target yaw for gaze_x = 1 (eye_anim.LOOK_LR: 30 deg of servo)
GAZE_DEG_Y = 20.0     # deg of target pitch for gaze_y = 1 (start value; LOOK_UD is 15 deg)
SACCADE_SPEED = 400.0     # deg/s eye travel in a saccade: 21 ms + 2.2 ms/deg (arXiv 1906.07183)
                          # gives 43 ms for 10 deg, 87 ms for 30 deg
PURSUIT_HALF_LIFE = 0.08  # s: a moving target is followed smoothly
TARGET_JUMP_DEG = 6.0     # deg: a target that jumps further is a new fixation (saccade)
GAZE_BLINK_FROM_DEG = 12.0   # deg: gaze shifts above this may carry a blink...
GAZE_BLINK_FULL_DEG = 33.0   # ...97 % of shifts over 33 deg do (Evinger et al. 1994)
GAZE_BLINK_MAX = 0.97

# Engaged saccades (Pan et al. 2020, Disney): jumps between his visitor's eyes and nose.
ENGAGE_POINTS_DEG = ((1.2, 0.3), (-1.2, 0.3), (0.0, -1.2))   # (yaw, pitch) offsets, deg
ENGAGE_GAP = (0.1, 0.5)       # s between engaged saccades
FIXATE_GAP = (0.6, 2.0)       # s between small fixational saccades when nobody is targeted
FIXATE_DEG = 1.0              # deg, their size (microsaccades are below servo deadband)
STEADY_SLOW = 2.5             # gaze_steady = 1 makes the gaps this much longer...
STEADY_SMALL = 0.6            # ...and the jumps this much smaller (as a share)

# Idle look-around (eye_anim.look): fixations near, back to centre, or anywhere.
LOOK_NEAR = (0.15, 0.1)       # gaze units: a small shift near the current point
LOOK_CENTRE = (0.2, 0.15)     # gaze units: back to about straight ahead
LOOK_ANY = (0.6, 0.5)         # gaze units: anywhere; eyes-only shifts read best within +-15-20 deg
LOOK_HOLD_SHORT = (0.5, 2.0)  # s, 70 % of fixations
LOOK_HOLD_LONG = (2.0, 5.0)   # s, the rest
LOOK_BORED = 0.8              # low arousal (-1) lengthens the holds by this share

# Alternating glances (confused): brief looks to the side or at other people.
ALT_GAP = (0.9, 1.8)          # s between glances at gaze_alternate = 1
ALT_HOLD = 0.35               # s each glance lasts
ALT_SIZE = 0.25               # gaze units, when nobody else is in view

# --- Blinks -------------------------------------------------------------------------------
BLINK_RATE = {                # blinks/min per state (Bentivoglio et al. 1997: 17 rest, 26 talk)
    "idle": 17, "person": 18, "greeting": 18, "listening": 20, "thinking": 8,
    "speaking": 26, "interrupted": 20, "farewell": 12,
}
BLINK_REFRACTORY = 1.0        # s: no spontaneous blink sooner than this after the last one
BLINK_SPREAD = 0.5            # sigma of the lognormal gap: skewed, a long tail of long gaps
BLINK = (0.08, 0.05, 0.15)    # s close, hold, open: eye_anim.BLINK, 280 ms (Trutoiu et al. 2011)
SLOW_BLINK = (0.25, 0.25, 0.45)   # eye_anim.SLOW_BLINK
LONG_BLINK = (0.10, 0.30, 0.20)   # ~600 ms listener "got it" blink (Homke et al. 2018: 607 ms)
SLOW_CHANCE = 0.08            # share of spontaneous blinks that are slow
LONG_CHANCE = 0.10            # share of spontaneous blinks while listening that are long
DOUBLE_CHANCE = 0.12          # share followed by a second quick blink
DOUBLE_GAP = 0.08             # s between the two
PHRASE_END_DELAY = (0.1, 0.3)  # s after a phrase_end event
BOTTOM_LID_BLINK = 0.0        # share of a blink the bottom lids take (firmware/README: top only)

# --- Lids ---------------------------------------------------------------------------------
LID_REST = JOINTS["lid_top_L"][2]   # 0.85, eye_anim.LID_REST
LID_FOLLOW_TOP = 0.25         # looking up opens the top lids this much (eye_anim)
LID_FOLLOW_BOTTOM = 0.15      # looking up raises the bottom lids this much (eye_anim)
LID_ASYM = 0.3                # openness difference per unit of face lid_asym
LID_SQUINT = 0.6              # bottom-lid openness lost at lid_squint = 1

# --- Noise drift (L1): amplitude in channel units; 1-3 % of range -------------------------
NOISE = {"brow": 0.04, "smile": 0.02, "smile_asym": 0.015, "lid": 0.015}
NOISE_FREQS = (0.07, 0.17, 0.31)    # Hz: three slow sines per channel, random phases

# --- State behaviours (L3; Andrist et al. 2014) -------------------------------------------
# state: (mean gap s, mean hold s, size in gaze units). Speaking is 0.4 of a full 0.75 look.
AVERT = {"listening": (7.21, 1.14, 0.35), "speaking": (4.75, 1.96, 0.3)}
AVERT_OTHER = (8.0, 1.2, 0.3)        # other engaged states, only when gaze_avert > 0
AVERT_FREQ = 1.5                     # gaze_avert = 1 makes aversions this much more frequent...
AVERT_BIG = 0.6                      # ...this share bigger...
AVERT_LONG = 0.5                     # ...and this share longer
THINK_LOOK = (0.35, 0.5)             # gaze units (sideways, up) of the thinking look
THINK_FAVOURED = 0.65                # chance the thinking look goes to his favoured side
GREET_FLASH = (0.25, 0.7, 0.8, 0.5, 0.5)   # attack, hold, release s; brow lift; lid widening
FLINCH = (0.05, 0.12, 0.3, -0.5, -0.2, -0.3)   # attack, hold, release s; inner, outer brows; lids

# --- Speech beats (L4; Cave et al. 1996, Krahmer et al. 2002) -----------------------------
BEAT_UP = 0.25                # brow raise of a beat, both brows
BEAT_FAVOURED = 0.08          # extra on his favoured side
BEAT_SHAPE = (0.08, 0.17, 0.35)   # attack, hold, release s (~0.25 s up, then decay)
BEAT_GAP = 2.5                # s: at most one beat per this long
BEAT_CHANCE = 0.4             # chance a loud onset after a dip gets a beat
TALK_DIP = 0.2                # his loudness below this...
DIP_TIME = 0.25               # ...for this long (s; a pause, not the gap between syllables) arms
TALK_ONSET = 0.5              # the onset detector, and a loudness above this is then a loud onset

# --- Smoothing (Holden, "Spring-It-On") ---------------------------------------------------
HALF_LIFE = {                 # s
    "gaze_x": 0.0, "gaze_y": 0.0,                         # saccades: no spring
    "lid_top_L": 0.04, "lid_top_R": 0.04, "lid_bot_L": 0.05, "lid_bot_R": 0.05,
    "brow_in_L": 0.12, "brow_out_L": 0.12, "brow_in_R": 0.12, "brow_out_R": 0.12,
    "smile": 0.15, "smile_asym": 0.15, "jaw_floor": 0.08,
}
LID_DOWN_FASTER = 0.75        # lids lower with this share of the half-life (Malbouisson 2005)
AROUSAL_SPEED = 0.35          # arousal +1 shortens half-lives by this share, -1 lengthens them
SPEED_CAP = {                 # channel units per second
    "lid_top_L": 12.0, "lid_top_R": 12.0, "lid_bot_L": 8.0, "lid_bot_R": 8.0,
    "brow_in_L": 6.0, "brow_out_L": 6.0, "brow_in_R": 6.0, "brow_out_R": 6.0,
    "smile": 5.0, "smile_asym": 5.0, "jaw_floor": 6.0,
}
# Stagger (FACE_ENGINE.md rules): delay in s per channel, on his favoured side / the other side.
DELAY = {"lid": (0.0, 0.02), "brow": (0.05, 0.11), "mouth": (0.15, 0.15)}

PERSONALITY = {
    "blink_rate": 1.0,      # scales every state's blink rate
    "saccade_rate": 1.0,    # scales how often the eyes jump (look-around, engaged, fixational)
    "aversion": 1.0,        # scales how often and how far he looks away
    "idle": 1.0,            # scales noise drift and the look-around range
    "favoured": "L",        # his favoured side: L (his left, the skeptic's brow) or R
}

TICK = 1 / 50


def ease(x):
    x = min(1.0, max(0.0, x))
    return x * x * (3 - 2 * x)


def envelope(d, attack, hold, release):
    """0..1 of a one-shot overlay d seconds after it started; < 0 once it is over."""
    if d < 0:
        return 0.0
    if d < attack:
        return ease(d / attack)
    if d < attack + hold:
        return 1.0
    if d < attack + hold + release:
        return 1.0 - ease((d - attack - hold) / release)
    return -1.0


def spring(x, v, goal, half_life, dt):
    """Holden's critically damped spring: (x, v) one step of dt towards goal."""
    y = 2 * math.log(2) / max(half_life, 1e-5)
    j0 = x - goal
    j1 = v + j0 * y
    e = math.exp(-y * dt)
    return e * (j0 + j1 * dt) + goal, e * (v - j1 * y * dt)


class Animator:
    def __init__(self, personality=None, seed=None):
        self.p = dict(PERSONALITY, **(personality or {}))
        self.rng = random.Random(seed)
        fav = self.p["favoured"]
        self.fav_sign = 1.0 if fav == "L" else -1.0      # +x is his left
        self.t = None
        self.out = rest_joints()
        self.vel = {k: 0.0 for k in JOINTS}
        self.history = []          # (t, target dict) for the stagger delay line
        self.delay = {}
        for k in JOINTS:
            side = k[-1] if k[-2] == "_" else None
            group = "lid" if k.startswith("lid") else "brow" if k.startswith("brow") else (
                "mouth" if k in ("smile", "smile_asym", "jaw_floor") else None)
            if group:
                lead, lag = DELAY[group]
                self.delay[k] = lead if side in (None, fav) else lag
        self.max_delay = max(self.delay.values())
        rng = self.rng
        self.noise = {k: [(f * rng.uniform(0.8, 1.25), rng.uniform(0, 2 * math.pi)) for f in NOISE_FREQS]
                      for k in list(BROWS) + ["smile", "smile_asym", "lid_top", "lid_bot"]}
        # state
        self.state = None
        self.state_at = 0.0
        # gaze
        self.gaze = [0.0, 0.0]            # output, gaze units
        self.base = None                   # smoothed target, gaze units
        self.base_vel = [0.0, 0.0]
        self.desired_prev = (0.0, 0.0)
        self.look = (0.0, 0.0)             # idle look-around fixation
        self.next_look = 0.0
        self.micro = (0.0, 0.0)            # engaged or fixational saccade offset, gaze units
        self.next_micro = 0.0
        self.micro_i = 0
        self.avert = None                  # (start, end, (dx, dy))
        self.next_avert = None
        self.think = None                  # (dx, dy) while thinking
        self.glance = None                 # (start, end, (x, y) absolute or offset, absolute?)
        self.next_glance = 0.0
        self.alt_sign = 1.0
        # blinks
        self.blinks = []                   # (start, close, hold, open)
        self.last_blink = -1e9
        self.next_blink = None
        self.blink_count = 0
        self.pending = []                  # (time, shape): blinks to start later
        # overlays: (start, attack, hold, release, {key: amount}); keys are brows and "lid_open"
        self.overlays = []
        # speech beats
        self.armed = False
        self.dip_at = None
        self.last_beat = -1e9
        self.beats = []                    # times of brow beats (for tests and the log)

    # --- helpers ---------------------------------------------------------------------------
    def _gap(self, lo_hi, scale=1.0):
        return self.rng.uniform(*lo_hi) * scale

    def _blink_gap(self, state):
        rate = BLINK_RATE.get(state, 17) * self.p["blink_rate"]
        mean = 60.0 / max(rate, 0.1) * (1 + DOUBLE_CHANCE) - sum(BLINK)   # doubles count too
        s = BLINK_SPREAD
        return BLINK_REFRACTORY + max(0.05, mean - BLINK_REFRACTORY) * self.rng.lognormvariate(-s * s / 2, s)

    def blink(self, t, shape=BLINK, double=None):
        """Start a blink now (and maybe a double); resets the spontaneous schedule."""
        if self.blinks and t < self.blinks[-1][0] + self.blinks[-1][1] + self.blinks[-1][2]:
            return   # already closing or shut: this blink merges with it
        self.blinks.append((t,) + tuple(shape))
        self.blink_count += 1
        self.last_blink = t
        if double is None:
            double = self.rng.random() < DOUBLE_CHANCE
        if double:
            self.pending.append((t + sum(shape) + DOUBLE_GAP, BLINK))
        self.next_blink = t + sum(shape) + self._blink_gap(self.state)

    def _closure(self, t):
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

    def _overlay(self, t, attack, hold, release, amounts, delay=0.0):
        self.overlays.append((t + delay, attack, hold, release, amounts))

    def _beat(self, t):
        if t - self.last_beat < BEAT_GAP:
            return False
        self.last_beat = t
        self.beats.append(t)
        fav = self.p["favoured"]
        amounts = {b: BEAT_UP + (BEAT_FAVOURED if b.endswith(fav) else 0.0) for b in BROWS}
        self._overlay(t, *BEAT_SHAPE, amounts)
        return True

    def _greet(self, t):
        a, h, r, brow, lid = GREET_FLASH
        amounts = {b: brow for b in BROWS}
        amounts["lid_open"] = lid
        self._overlay(t, a, h, r, amounts)

    def _flinch(self, t):
        a, h, r, inner, outer, lid = FLINCH
        amounts = {b: inner if "_in_" in b else outer for b in BROWS}
        amounts["lid_open"] = lid
        self._overlay(t, a, h, r, amounts)
        self.blink(t, BLINK, double=False)

    def _noise(self, key, t, amp):
        return amp * sum(math.sin(2 * math.pi * f * t + ph) for f, ph in self.noise[key]) / len(NOISE_FREQS)

    # --- state entry and exit --------------------------------------------------------------
    def _enter(self, state, t, prev):
        self.state, self.state_at = state, t
        self.avert = None
        self.next_avert = None
        self.glance = None
        self.next_blink = max(t, self.last_blink + BLINK_REFRACTORY) + self._blink_gap(state)
        if prev == "thinking":
            self.think = None
            self.blink(t, BLINK, double=self.rng.random() < 0.5)    # the burst on return
        if state == "thinking":
            side = self.fav_sign if self.rng.random() < THINK_FAVOURED else -self.fav_sign
            self.think = (side * THINK_LOOK[0] * self.rng.uniform(0.7, 1.2),
                          THINK_LOOK[1] * self.rng.uniform(0.8, 1.2))
        elif state == "greeting":
            self._greet(t)
        elif state == "interrupted":
            self._flinch(t)
        elif state == "farewell":
            self.blink(t + 0.2, SLOW_BLINK, double=False)

    # --- gaze ------------------------------------------------------------------------------
    def _look_around(self, t, face):
        gx, gy = self.look
        rng = self.rng
        amt = min(1.5, self.p["idle"])
        r = rng.random()
        if r < 0.3:
            x, y = gx + rng.uniform(-1, 1) * LOOK_NEAR[0], gy + rng.uniform(-1, 1) * LOOK_NEAR[1]
        elif r < 0.55:
            x, y = rng.uniform(-1, 1) * LOOK_CENTRE[0], rng.uniform(-1, 1) * LOOK_CENTRE[1]
        else:
            x, y = rng.uniform(-1, 1) * LOOK_ANY[0] * amt, rng.uniform(-1, 1) * LOOK_ANY[1] * amt
        self.look = (max(-1.0, min(1.0, x)), max(-1.0, min(1.0, y)))
        hold = self._gap(LOOK_HOLD_SHORT) if rng.random() < 0.7 else self._gap(LOOK_HOLD_LONG)
        bored = 1 + LOOK_BORED * max(0.0, -face.get("arousal", 0.0))
        self.next_look = t + hold * bored / self.p["saccade_rate"]

    def _micro_step(self, t, face, engaged):
        steady = face.get("gaze_steady", 0.0)
        slow = (1 + STEADY_SLOW * steady) / self.p["saccade_rate"]
        small = 1 - STEADY_SMALL * steady
        if engaged:
            pts = ENGAGE_POINTS_DEG
            self.micro_i = (self.micro_i + self.rng.choice((1, 2))) % len(pts)
            dx, dy = pts[self.micro_i]
            self.micro = (dx * small / GAZE_DEG_X, dy * small / GAZE_DEG_Y)
            self.next_micro = t + self._gap(ENGAGE_GAP, slow)
        else:
            a = self.rng.uniform(0, 2 * math.pi)
            self.micro = (math.cos(a) * FIXATE_DEG * small / GAZE_DEG_X,
                          math.sin(a) * FIXATE_DEG * small / GAZE_DEG_Y)
            self.next_micro = t + self._gap(FIXATE_GAP, slow)

    def _aversion(self, t, face, engaged):
        avert = face.get("gaze_avert", 0.0)
        params = AVERT.get(self.state)
        if not engaged:          # an aversion is a look away from someone
            self.avert = None
            return None
        if params is None:
            if avert <= 0.0 or self.state == "thinking":
                self.avert = None
                return None
            params = AVERT_OTHER
        gap, hold, size = params
        scale = self.p["aversion"]
        freq = (1 + AVERT_FREQ * avert) * scale
        if self.next_avert is None:
            self.next_avert = t + gap / max(freq, 0.05) * self.rng.uniform(0.3, 1.0)
        if self.avert and t >= self.avert[1]:
            self.avert = None
        if self.avert is None and t >= self.next_avert:
            side = self.rng.choice((-1.0, 1.0))
            sz = size * (1 + AVERT_BIG * avert) * min(1.5, scale)
            dur = hold * (1 + AVERT_LONG * avert) * self.rng.uniform(0.7, 1.3)
            dy = sz * self.rng.uniform(-0.3, 0.15) - 0.1 * avert   # mostly sideways; vulnerable lower
            self.avert = (t, t + dur, (side * sz, dy))
            self.next_avert = t + dur + gap / max(freq, 0.05) * self.rng.uniform(0.6, 1.4)
        return self.avert[2] if self.avert else None

    def _glance(self, t, face, cue, target):
        alt = face.get("gaze_alternate", 0.0)
        if self.glance and t >= self.glance[1]:
            self.glance = None
        if alt < 0.1 or target is None:
            return None
        if self.glance is None and t >= self.next_glance:
            others = cue.get("others") or []
            if others:
                o = others[self.rng.randrange(len(others))]
                point = (o[0] / GAZE_DEG_X, o[1] / GAZE_DEG_Y)
            else:
                self.alt_sign = -self.alt_sign
                point = (target[0] + self.alt_sign * ALT_SIZE * (0.6 + 0.4 * alt), target[1])
            self.glance = (t, t + ALT_HOLD, point)
            self.next_glance = t + ALT_HOLD + self._gap(ALT_GAP, 1 / max(alt, 0.1))
        return self.glance[2] if self.glance else None

    def _gaze(self, t, dt, face, cue):
        tgt = cue.get("target")
        bias = (face.get("gaze_bias_x", 0.0), face.get("gaze_bias_y", 0.0))
        engaged = tgt is not None
        if engaged:
            raw = (max(-1.0, min(1.0, tgt[0] / GAZE_DEG_X)), max(-1.0, min(1.0, tgt[1] / GAZE_DEG_Y)))
            if self.base is None or math.hypot((raw[0] - self.base[0]) * GAZE_DEG_X,
                                               (raw[1] - self.base[1]) * GAZE_DEG_Y) > TARGET_JUMP_DEG:
                self.base, self.base_vel = list(raw), [0.0, 0.0]
            else:
                for i in (0, 1):
                    self.base[i], self.base_vel[i] = spring(self.base[i], self.base_vel[i], raw[i],
                                                            PURSUIT_HALF_LIFE, dt)
            point = (self.base[0], self.base[1])
        else:
            self.base = None
            if self.state == "thinking":
                point = (0.0, 0.0)
            else:
                if t >= self.next_look:
                    self._look_around(t, face)
                point = self.look
        if t >= self.next_micro:
            self._micro_step(t, face, engaged and self.state != "thinking")
        x, y = point[0] + bias[0], point[1] + bias[1]
        if self.state == "thinking" and self.think:
            x, y = x + self.think[0], y + self.think[1]
        else:
            g = self._glance(t, face, cue, (x, y) if engaged else None)
            av = self._aversion(t, face, engaged)
            if g is not None:
                x, y = g
            elif av is not None:
                x, y = x + av[0], y + av[1]
        x, y = x + self.micro[0], y + self.micro[1]
        desired = (max(-1.0, min(1.0, x)), max(-1.0, min(1.0, y)))
        # a jump in the desired point is a saccade: maybe a blink with it, sized by the shift
        jump = math.hypot((desired[0] - self.desired_prev[0]) * GAZE_DEG_X,
                          (desired[1] - self.desired_prev[1]) * GAZE_DEG_Y)
        if jump > 1.5:
            shift = math.hypot((desired[0] - self.gaze[0]) * GAZE_DEG_X, (desired[1] - self.gaze[1]) * GAZE_DEG_Y)
            k = (shift - GAZE_BLINK_FROM_DEG) / (GAZE_BLINK_FULL_DEG - GAZE_BLINK_FROM_DEG)
            if k > 0 and t - self.last_blink > 0.6 and self.rng.random() < GAZE_BLINK_MAX * min(1.0, k):
                self.blink(t, BLINK)
        self.desired_prev = desired
        # step at saccade speed (no spring); small target motion is already smooth
        dxd, dyd = (desired[0] - self.gaze[0]) * GAZE_DEG_X, (desired[1] - self.gaze[1]) * GAZE_DEG_Y
        dist = math.hypot(dxd, dyd)
        step = SACCADE_SPEED * (1 + 0.25 * face.get("arousal", 0.0)) * dt
        if dist <= step or dist == 0:
            self.gaze = [desired[0], desired[1]]
        else:
            k = step / dist
            self.gaze = [self.gaze[0] + dxd * k / GAZE_DEG_X, self.gaze[1] + dyd * k / GAZE_DEG_Y]
        return self.gaze

    # --- the tick --------------------------------------------------------------------------
    def step(self, t, face, cue):
        dt = TICK if self.t is None else max(0.0, min(0.1, t - self.t))
        self.t = t
        state = cue.get("state", "idle")
        if state not in STATES:
            state = "idle"
        if state != self.state:
            self._enter(state, t, self.state)
        arousal = face.get("arousal", 0.0)
        idle = self.p["idle"]

        # L5 one-shot events and L4 speech
        for ev in cue.get("events") or ():
            if ev == "blink":
                self.blink(t, BLINK)
            elif ev == "long_blink":
                self.blink(t, LONG_BLINK, double=False)
            elif ev == "flinch":
                self._flinch(t)
            elif ev == "greet":
                self._greet(t)
            elif ev == "beat":
                self._beat(t)
            elif ev == "phrase_end":
                self.pending.append((t + self._gap(PHRASE_END_DELAY), BLINK))
        talk = cue.get("talk", 0.0) or 0.0
        if talk < TALK_DIP:
            if self.dip_at is None:
                self.dip_at = t
            if t - self.dip_at >= DIP_TIME:
                self.armed = True
        else:
            self.dip_at = None
        if self.armed and talk > TALK_ONSET:
            self.armed = False
            if t - self.last_beat >= BEAT_GAP and self.rng.random() < BEAT_CHANCE:
                self._beat(t)

        # L1 blinks
        if self.pending:
            due = [p for p in self.pending if p[0] <= t]
            self.pending = [p for p in self.pending if p[0] > t]
            for _, shape in due:
                self.blink(t, shape, double=False)
        if self.next_blink is None:
            self.next_blink = t + self._blink_gap(self.state)
        if t >= self.next_blink:
            r = self.rng.random()
            if self.state == "listening" and r < LONG_CHANCE:
                shape = LONG_BLINK
            elif r < LONG_CHANCE + SLOW_CHANCE:
                shape = SLOW_BLINK
            else:
                shape = BLINK
            self.blink(t, shape)
        closure = self._closure(t)

        # gaze (L1 saccades, L2 bias, L3 aversions and the thinking look)
        gx, gy = self._gaze(t, dt, face, cue)

        # overlays (greeting flash, flinch, beats)
        over = {}
        live = []
        for o in self.overlays:
            e = envelope(t - o[0], o[1], o[2], o[3])
            if e < 0:
                continue
            live.append(o)
            for k, a in o[4].items():
                over[k] = over.get(k, 0.0) + a * e
        self.overlays = live

        # targets before smoothing
        tgt = {}
        nz = idle * (1 + 0.5 * max(0.0, arousal))
        for b in BROWS:
            tgt[b] = face.get(b, 0.0) + over.get(b, 0.0) + self._noise(b, t, NOISE["brow"] * nz)
        tgt["smile"] = face.get("smile", 0.0) + self._noise("smile", t, NOISE["smile"] * nz)
        tgt["smile_asym"] = face.get("smile_asym", 0.0) + self._noise("smile_asym", t, NOISE["smile_asym"] * nz)
        tgt["jaw_floor"] = face.get("jaw_floor", 0.0)
        lid_open = max(-1.0, min(1.0, face.get("lid_open", 0.0) + over.get("lid_open", 0.0)))
        opened = LID_REST + lid_open * ((1 - LID_REST) if lid_open > 0 else LID_REST)
        asym = face.get("lid_asym", 0.0) * LID_ASYM
        follow_limit = 1.0 + LID_FOLLOW_TOP * min(gy, 0.0)
        lid_noise = self._noise("lid_top", t, NOISE["lid"] * nz)
        for k, a in (("lid_top_L", -asym), ("lid_top_R", asym)):
            tgt[k] = min(opened + a + LID_FOLLOW_TOP * gy, follow_limit) + lid_noise
        bot = 1.0 - face.get("lid_squint", 0.0) * LID_SQUINT - LID_FOLLOW_BOTTOM * max(gy, 0.0)
        bot_noise = self._noise("lid_bot", t, NOISE["lid"] * nz)
        for k in LIDS_BOT:
            tgt[k] = bot + min(0.0, bot_noise)
        for k in tgt:
            tgt[k] = clamp(k, tgt[k])

        # stagger: read each channel's target from the delay line
        self.history.append((t, tgt))
        while len(self.history) > 2 and self.history[1][0] <= t - self.max_delay - 1e-9:
            self.history.pop(0)
        delayed = {}
        for k in tgt:
            d = self.delay.get(k, 0.0)
            if d <= 0:
                delayed[k] = tgt[k]
                continue
            v = self.history[0][1][k]
            for ht, h in reversed(self.history):
                if ht <= t - d + 1e-9:
                    v = h[k]
                    break
            delayed[k] = v

        # spring and speed cap
        speed = 1 - AROUSAL_SPEED * max(-1.0, min(1.0, arousal))
        out = self.out
        for k, goal in delayed.items():
            x0 = out[k]
            hl = HALF_LIFE[k] * speed
            if k in LIDS_TOP and goal < x0:
                hl *= LID_DOWN_FASTER
            if dt > 0:
                x, v = spring(x0, self.vel[k], goal, hl, dt)
                cap = SPEED_CAP[k] * dt
                if x - x0 > cap:
                    x, v = x0 + cap, SPEED_CAP[k]
                elif x0 - x > cap:
                    x, v = x0 - cap, -SPEED_CAP[k]
                out[k], self.vel[k] = x, v

        # compose: gaze straight through, blinks on top of the smoothed lids
        joints = dict(out)
        joints["gaze_x"], joints["gaze_y"] = gx, gy
        for k in LIDS_TOP:
            joints[k] = out[k] * (1 - closure)
        for k in LIDS_BOT:
            joints[k] = out[k] * (1 - BOTTOM_LID_BLINK * closure)
        return {k: clamp(k, v) for k, v in joints.items()}

"""
Frank's emotion synthesiser: the inner state of the face performance engine
(docs/FACE_ENGINE.md, "Synthesiser").

The orchestrator calls Synth.feel() when a tag's words reach the speaker, Synth.nudge() for
events (someone arrived, he was moved), and Synth.step(t) 50 times a second; the animator
(animator.py) takes the face target step() returns and adds blinks, gaze and speech on top.
It keeps two layers, after the research report's section "The synthesiser keeps a mood and a
mixture, never a single face":
  - a slow mood, a point in pleasure, arousal, dominance (PAD) space that rests at Frank's
    dry, slightly disdainful home and relaxes back there on a critically damped spring over
    minutes; every tag pulls it a step towards that tag's anchor and events push it;
  - ten transient weights, one per tag, each rising and fading on its own envelope (attack,
    overshoot, hold, decay) towards a floor that leaks from the mood, so the resting face is a
    faint version of whatever the mood is near (usually skeptical), never blank.
step() renders the mixture in pose space, region by region: same-sign pulls mix by weight with
neutral taking the remainder, opposing pulls on one channel go to the larger one, raised and
lowered inner brows never share the brows above a weight of 0.3, and the one-sided terms
(brow difference, lid_asym, smile_asym) are blended apart and added after, so they survive.

Poses are written for Frank's favoured side, his left (L = +x, the character's own side), and
mirrored when PERSONALITY["side"] is -1. Time is always passed in (time.monotonic() seconds)
and nothing is random, so tests are deterministic. Standard library only.
"""

import math

from . import channels

TAGS = channels.TAGS
FACE = channels.FACE

# Tunables. Synth(personality) overrides any of them (the nested tables key by key).
PERSONALITY = {
    # Home mood (P, A, D), each -1..1: dry, slightly disdainful (report, "The synthesiser...").
    "home": (-0.18, -0.20, 0.33),
    # Overall expressivity, a factor on every pose: below 1 is restraint ("Frank's face should
    # not perform every movement at once", CHARACTER.md).
    "gain": 0.8,
    # Per-tag factor on top of gain. The earned tags make up for the restraint, so they are
    # still big when they fire; vulnerable stays small (he hides it).
    "tag_gain": {"neutral": 1.0, "curious": 1.0, "excited": 1.25, "skeptical": 1.0,
                 "amused": 1.15, "concentrating": 1.0, "confused": 1.0, "irritated": 1.0,
                 "surprised": 1.25, "vulnerable": 0.9},
    "mood_half_life": 120.0,   # s, the mood's spring home (report: 1-5 min)
    "mood_pull": 0.15,         # share of the way to a tag's anchor one feel moves the mood, x intensity (ALMA-style)
    "repeat_boost": 0.15,      # intensity a repeated tag adds while still active (report: 10-20 %)
    "intensity_cap": 1.3,      # most intensity a tag can build up to by repeats
    # Floor: a leakage weight per tag from the mood's PAD distance to its anchor, WASABI-style:
    # full at floor_full or nearer, none at floor_none or further, linear between, x floor_max.
    "floor_full": 0.2,         # PAD distance (WASABI's saturation threshold)
    "floor_none": 0.64,        # PAD distance (WASABI's activation threshold)
    "floor_max": 0.25,         # weight 0..1: the most any tag leaks into the resting face
    # Share of the floor per tag (default 1). His resting faces are neutral, skeptical and
    # concentrating (CHARACTER.md, expression states), so irritation leaks less.
    "floor_scale": {"concentrating": 0.6, "irritated": 0.3},
    # Boredom 0..1 rises when no tag fires: it lowers arousal (slower look-arounds) and makes
    # the lids heavier, with a floor so he never looks asleep (report, state table "Idle").
    "boredom_after": 30.0,     # s without a tag before boredom starts
    "boredom_rate": 1 / 240,   # per s: full boredom 4 min later
    "boredom_arousal": 0.5,    # arousal taken off at full boredom
    "boredom_floor": -0.6,     # boredom never takes arousal below this
    "boredom_lids": 0.15,      # lid_open taken off at full boredom
    # +1: his left brow is the skeptic's brow (brow_anim.py's tuned skeptical); -1 mirrors
    # every one-sided pose.
    "side": +1,
    "brow_conflict": 0.3,      # weight above which raised and lowered inner brows never share the brows (report: ~0.3)
    "brow_class": 0.15,        # mean inner-brow pose above which a tag counts as raising them (below minus: lowering)
}


def brows(lo=0.0, li=0.0, ro=0.0, ri=0.0):
    """Brow ends by the character's sides: lo/li his left outer/inner, ro/ri his right."""
    return {"brow_out_L": lo, "brow_in_L": li, "brow_out_R": ro, "brow_in_R": ri}


def both(up):
    return brows(up, up, up, up)


# Per tag: the PAD anchor, the envelope and the full-intensity pose over the face-target keys
# (missing keys are 0 = rest). attack: s to full weight (smoothstep); overshoot: fraction past
# full at the end of the attack, settling over the next attack time (Convai's micro-burst);
# hold: s at full weight after the attack; decay: half-life in s afterwards (report: 2-10 s).
# "then" adds later keys (s after the tag fired, s to ease there, pose). Anchors, timings and
# recipes are the report's tag table; brow fractions start from firmware/brow_anim.py.
RECIPES = {
    "neutral": dict(anchor=(0.0, 0.0, 0.0), attack=0.6, overshoot=0.0, hold=1.0, decay=3.0,
                    pose={}),
    "curious": dict(anchor=(0.3, 0.4, 0.0), attack=0.35, overshoot=0.05, hold=1.5, decay=4.0,
                    pose={**both(0.6), "lid_open": 0.3, "gaze_steady": 0.6}),
    "excited": dict(anchor=(0.62, 0.75, 0.38), attack=0.2, overshoot=0.15, hold=1.2, decay=3.0,
                    pose={**both(1.0), "lid_open": 0.6, "smile": 0.6, "gaze_steady": 0.3}),
    # His left brow up, the right one down; the eye under the lowered brow (his right) narrows,
    # and the corner on the raised side lifts a little.
    "skeptical": dict(anchor=(-0.25, 0.1, 0.45), attack=0.4, overshoot=0.0, hold=3.0, decay=6.0,
                      pose={**brows(lo=0.8, li=0.6, ro=-0.2, ri=-0.4), "lid_asym": -0.35,
                            "lid_squint": 0.1, "smile": 0.05, "smile_asym": 0.3,
                            "gaze_steady": 0.7}),
    "amused": dict(anchor=(0.45, 0.25, 0.35), attack=0.4, overshoot=0.1, hold=1.5, decay=4.0,
                   pose={**brows(lo=0.5, li=0.3, ro=0.1, ri=0.0), "lid_squint": 0.5,
                         "smile": 0.5, "smile_asym": 0.25}),
    # Furrow, lids a touch lower, eyes away and up, then back when ready.
    "concentrating": dict(anchor=(0.0, 0.0, 0.0), attack=0.7, overshoot=0.0, hold=2.5, decay=5.0,
                          pose={**brows(lo=-0.2, li=-0.5, ro=-0.2, ri=-0.5), "lid_open": -0.15,
                                "smile": -0.05, "gaze_bias_x": 0.35, "gaze_bias_y": 0.4,
                                "gaze_avert": 0.5},
                          then=[(2.0, 0.6, {**brows(lo=-0.2, li=-0.5, ro=-0.2, ri=-0.5),
                                            "lid_open": -0.15, "smile": -0.05,
                                            "gaze_avert": 0.1})]),
    # Furrow first; 0.7 s later (the furrow reached at 0.4 s and read briefly) a questioning
    # lift with his left brow leading, eased in over 0.3 s.
    "confused": dict(anchor=(-0.2, 0.35, -0.25), attack=0.4, overshoot=0.0, hold=1.5, decay=4.0,
                     pose={**brows(lo=-0.3, li=-0.7, ro=-0.3, ri=-0.7), "lid_open": -0.1,
                           "lid_squint": 0.3, "gaze_alternate": 0.7},
                     then=[(0.7, 0.3, {**brows(lo=0.7, li=0.5, ro=0.2, ri=0.1), "lid_open": 0.15,
                                       "lid_squint": 0.1, "jaw_floor": 0.05,
                                       "gaze_alternate": 0.7})]),
    "irritated": dict(anchor=(-0.28, 0.17, 0.04), attack=0.8, overshoot=0.0, hold=2.5, decay=6.0,
                      pose={**both(-0.8), "lid_open": -0.2, "lid_squint": 0.35, "smile": -0.5,
                            "gaze_steady": 0.8}),
    # Lids and brows up fast with a brief jaw drop; the jaw closes after 0.45 s and the rest
    # returns over about 2 s (decay half-life 0.7 s, shorter than the others on purpose).
    "surprised": dict(anchor=(0.40, 0.67, -0.13), attack=0.12, overshoot=0.1, hold=0.8, decay=0.7,
                      pose={**both(1.0), "lid_open": 1.0, "jaw_floor": 0.35},
                      then=[(0.45, 0.3, {**both(1.0), "lid_open": 0.6})]),
    # Inner ends up, outer a little down (the one deliberate worry brow), softer, lower gaze.
    "vulnerable": dict(anchor=(-0.3, 0.1, -0.55), attack=0.9, overshoot=0.0, hold=2.0, decay=6.0,
                       pose={**brows(lo=-0.15, li=0.5, ro=-0.15, ri=0.5), "lid_open": -0.25,
                             "smile": -0.1, "gaze_bias_y": -0.3, "gaze_avert": 0.6}),
}

# Pose space: the symmetric channels and the one-sided ones. A pose's brow ends become a mean
# (sym) and a half-difference, his left minus his right (asym).
_SYM = ("brow_in", "brow_out", "lid_open", "lid_squint", "smile", "jaw_floor",
        "gaze_bias_x", "gaze_bias_y", "gaze_steady", "gaze_avert", "gaze_alternate")
_ASYM = ("brow_in", "brow_out", "lid_asym", "smile_asym")
_NSYM, _NASYM = len(_SYM), len(_ASYM)
_ZERO = 1e-9


def _split(pose):
    bad = set(pose) - set(FACE)
    assert not bad, f"pose keys not in channels.FACE: {bad}"
    li, ri = pose.get("brow_in_L", 0.0), pose.get("brow_in_R", 0.0)
    lo, ro = pose.get("brow_out_L", 0.0), pose.get("brow_out_R", 0.0)
    sym = ((li + ri) / 2, (lo + ro) / 2) + tuple(pose.get(k, 0.0) for k in _SYM[2:])
    asym = ((li - ri) / 2, (lo - ro) / 2, pose.get("lid_asym", 0.0), pose.get("smile_asym", 0.0))
    return sym, asym


# Each tag's keys as (at s, ease s, sym, asym), the first at 0 (its rise is the envelope).
_KEYS = {tag: [(0.0, 0.0) + _split(r["pose"])] + [(at, ease) + _split(p) for at, ease, p in r.get("then", ())]
         for tag, r in RECIPES.items()}
assert set(RECIPES) == set(TAGS)


def ease(x):
    x = 0.0 if x < 0.0 else 1.0 if x > 1.0 else x
    return x * x * (3 - 2 * x)


def _pose_at(keys, rel):
    """The (sym, asym) pose of a tag rel seconds after it fired."""
    sym, asym = keys[0][2], keys[0][3]
    for at, dur, s2, a2 in keys[1:]:
        if rel <= at:
            break
        u = ease((rel - at) / dur) if dur > 0 else 1.0
        sym = tuple(a + (b - a) * u for a, b in zip(sym, s2))
        asym = tuple(a + (b - a) * u for a, b in zip(asym, a2))
    return sym, asym


def _merge(base, over):
    out = dict(base)
    for k, v in (over or {}).items():
        out[k] = {**base[k], **v} if isinstance(v, dict) and isinstance(base.get(k), dict) else v
    return out


class _Transient:
    """One tag's envelope: rise from start to peak over attack, settle to 1, hold, decay."""
    __slots__ = ("born", "t0", "start", "peak", "attack", "hold_end", "decay", "intensity")

    def __init__(self, recipe, t, intensity):
        self.born = t
        self.t0, self.start, self.peak = t, 0.0, 1.0 + recipe["overshoot"]
        self.attack = max(recipe["attack"], 0.01)
        self.hold_end = t + self.attack + recipe["hold"]
        self.decay = recipe["decay"]
        self.intensity = intensity

    def value(self, t):
        ta = self.t0 + self.attack
        if t < ta:
            return self.start + (self.peak - self.start) * ease((t - self.t0) / self.attack)
        settle = lambda x: 1.0 + (self.peak - 1.0) * (1.0 - ease((x - ta) / self.attack))
        if t <= self.hold_end:
            return settle(t)
        return settle(self.hold_end) * 0.5 ** ((t - self.hold_end) / self.decay)


def _resolve(entries, j, total):
    """One channel: same-sign pulls add, opposing pulls go to the larger side (no blank
    mouth). The winner is shared with neutral and the tags that do not pull against it."""
    pos = neg = wpos = wneg = 0.0
    for w, c, vals in entries:
        v = c * vals[j]
        if v > _ZERO:
            pos += v
            wpos += w
        elif v < -_ZERO:
            neg += v
            wneg += w
    if pos >= -neg:
        return pos / max(1.0, total - wneg)
    return neg / max(1.0, total - wpos)


class Synth:
    def __init__(self, personality=None):
        self.p = _merge(PERSONALITY, personality)
        self.mood = list(self.p["home"])
        self.vel = [0.0, 0.0, 0.0]
        self.boredom = 0.0
        self.active = {}                 # tag -> _Transient
        self.t = None                    # time of the last advance
        self.last_feel = None
        self.weights = {tag: 0.0 for tag in TAGS}

    # -- inputs ----------------------------------------------------------------------------

    def feel(self, tag, t, intensity=1.0):
        """Fire a tag at time t. Unknown tags are ignored. The same tag again while it is still
        active extends its hold and builds up intensity instead of restarting."""
        tag = str(tag).strip().lower()
        if tag not in RECIPES:
            return
        intensity = min(float(intensity), self.p["intensity_cap"])
        if not intensity > 0:
            return
        self._advance(t)
        rec = RECIPES[tag]
        tr = self.active.get(tag)
        if tr is None:
            self.active[tag] = _Transient(rec, t, intensity)
        else:
            if t <= tr.hold_end:
                tr.hold_end = max(tr.hold_end, t + rec["hold"])
            else:                        # decaying: rise again from where it is, no replay
                tr.start, tr.t0, tr.peak = tr.value(t), t, 1.0
                tr.hold_end = t + tr.attack + rec["hold"]
            tr.intensity = min(self.p["intensity_cap"], tr.intensity + self.p["repeat_boost"] * intensity)
        k = self.p["mood_pull"] * min(intensity, 1.0)
        for i, a in enumerate(rec["anchor"]):
            self.mood[i] = _clamp1(self.mood[i] + k * (a - self.mood[i]))
        self.last_feel = t
        self.boredom = 0.0

    def nudge(self, t, p=0.0, a=0.0, d=0.0):
        """Push the mood by (p, a, d) at time t (an arrival, being moved, darkness)."""
        self._advance(t)
        for i, x in enumerate((p, a, d)):
            self.mood[i] = _clamp1(self.mood[i] + x)

    # -- output ----------------------------------------------------------------------------

    def step(self, t):
        """The face target at time t: every channels.FACE key plus "weights" {tag: 0..1}."""
        self._advance(t)
        P = self.p
        gain, tag_gain = P["gain"], P["tag_gain"]
        entries = []                     # (tag, w, scale, sym, asym)
        trans = []                       # (weight, anchor) of the transients alone, for PAD
        for tag in TAGS:
            tr = self.active.get(tag)
            e = 0.0
            if tr is not None:
                e = tr.value(t) * tr.intensity
                if t > tr.hold_end and e < 0.005:
                    del self.active[tag]
                    tr, e = None, 0.0
            w = max(e, self._floor(tag))
            self.weights[tag] = min(w, 1.0)
            if e > 0:
                trans.append((min(e, 1.0), RECIPES[tag]["anchor"]))
            if w <= 0:
                continue
            keys = _KEYS[tag]
            sym, asym = _pose_at(keys, t - tr.born) if tr is not None else (keys[-1][2], keys[-1][3])
            entries.append((tag, w, w * gain * tag_gain.get(tag, 1.0), sym, asym))

        # Brows: above the conflict weight, a tag raising the inner brows and one lowering
        # them never share; the stronger takes the brows (no accidental worry brow).
        cls = P["brow_class"]
        brow_entries = entries
        strong = [(c, 1 if s[0] > cls else -1) for _, w, c, s, _ in entries
                  if min(w, 1.0) > P["brow_conflict"] and abs(s[0]) > cls]
        if strong and len({side for _, side in strong}) == 2:
            winner = max(strong)[1]
            brow_entries = [e for e in entries if not (abs(e[3][0]) > cls and (1 if e[3][0] > 0 else -1) != winner)]

        def mix(group, j, part):
            rows = [(min(w, 1.0), c, s) for _, w, c, s, _ in group] if part == 0 else \
                [(min(w, 1.0), c, a) for _, w, c, _, a in group if abs(a[j]) > _ZERO]
            # The asymmetry blends only among the tags that carry it, so it survives mixing.
            return _resolve(rows, j, sum(r[0] for r in rows))

        sym = [mix(brow_entries if j < 2 else entries, j, 0) for j in range(_NSYM)]
        asym = [mix(brow_entries if j < 2 else entries, j, 1) * P["side"] for j in range(_NASYM)]

        out = {}
        out["brow_in_L"], out["brow_in_R"] = sym[0] + asym[0], sym[0] - asym[0]
        out["brow_out_L"], out["brow_out_R"] = sym[1] + asym[1], sym[1] - asym[1]
        for j in range(2, _NSYM):
            out[_SYM[j]] = sym[j]
        out["lid_asym"], out["smile_asym"] = asym[2], asym[3]
        out["lid_open"] -= P["boredom_lids"] * self.boredom

        # PAD: the mood mixed with the anchors of the active transients.
        tw = sum(w for w, _ in trans)
        pad = list(self.mood)
        for w, anchor in trans:
            for i in range(3):
                pad[i] += w * (anchor[i] - self.mood[i]) / max(1.0, tw)
        drop = P["boredom_arousal"] * self.boredom
        arousal = max(pad[1] - drop, min(pad[1], P["boredom_floor"]))
        out["valence"], out["arousal"], out["dominance"] = pad[0], arousal, pad[2]

        face = {k: channels.clamp(k, out[k], FACE) for k in FACE}
        face["weights"] = dict(self.weights)
        return face

    def snapshot(self):
        """{"mood": (p, a, d), "weights": {tag: 0..1}, "boredom": 0..1} for the preview and log."""
        return {"mood": tuple(self.mood), "weights": dict(self.weights), "boredom": self.boredom}

    # -- internals -------------------------------------------------------------------------

    def _floor(self, tag):
        if tag == "neutral":             # its pose is rest: neutral is the remainder anyway
            return 0.0
        P = self.p
        d = math.dist(self.mood, RECIPES[tag]["anchor"])
        full, none = P["floor_full"], P["floor_none"]
        leak = 1.0 if d <= full else 0.0 if d >= none else (none - d) / (none - full)
        return P["floor_max"] * leak * P["floor_scale"].get(tag, 1.0)

    def _advance(self, t):
        """Run the mood spring and boredom forward to t (never backwards)."""
        if self.t is None:
            self.t = self.last_feel = t
            return
        dt = t - self.t
        if dt <= 0:
            return
        # Critically damped spring home, exact for any dt (Holden, "Spring-It-On").
        y = 2.0 * math.log(2.0) / max(self.p["mood_half_life"], 1e-3)
        eydt = math.exp(-y * dt)
        for i, goal in enumerate(self.p["home"]):
            j0 = self.mood[i] - goal
            j1 = self.vel[i] + j0 * y
            self.mood[i] = eydt * (j0 + j1 * dt) + goal
            self.vel[i] = eydt * (self.vel[i] - j1 * y * dt)
        idle = t - self.last_feel - self.p["boredom_after"]
        if idle > 0:
            self.boredom = min(1.0, self.boredom + self.p["boredom_rate"] * min(dt, idle))
        self.t = t


def _clamp1(x):
    return -1.0 if x < -1.0 else 1.0 if x > 1.0 else x

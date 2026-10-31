"""
Offline test of the emotion synthesiser (frank/engine/synth.py): no head, no keys, no clock.

    .venv\\Scripts\\python.exe frank\\engine\\tests\\test_synth.py

Plain asserts; prints "synth OK" when everything passes.
"""

import math
import os
import random
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from engine import channels                       # noqa: E402
from engine.synth import PERSONALITY, TAGS, Synth  # noqa: E402

DT = 1 / 50       # s, the engine's 50 Hz tick
GAIN = PERSONALITY["gain"]


def frames(s, t0, t1):
    """Step s from t0 to t1 at 50 Hz; [(t, face), ...]."""
    out, n = [], int(round((t1 - t0) / DT))
    for i in range(n + 1):
        t = t0 + i * DT
        out.append((t, s.step(t)))
    return out


def brow_mean(f):
    return sum(f[b] for b in channels.BROWS) / 4


def test_rest_is_faint_skeptical():
    s = Synth()
    for t in (0.0, 5.0, 20.0):
        f = s.step(t)
        assert set(channels.FACE) <= set(f) and set(f["weights"]) == set(TAGS)
        assert f["brow_out_L"] > f["brow_out_R"] + 0.02, f
        assert f["brow_in_L"] > f["brow_in_R"], f
        assert all(abs(f[b]) < 0.3 for b in channels.BROWS), f
        assert abs(f["lid_open"]) < 0.1 and f["jaw_floor"] == 0.0
        w = f["weights"]
        assert max(w, key=w.get) == "skeptical", w
        assert 0.05 < w["skeptical"] <= PERSONALITY["floor_max"] + 1e-9, w


def test_surprised_fast_and_back():
    s = Synth()
    rest = s.step(0.0)
    s.feel("surprised", 1.0)
    early = frames(s, 1.0, 1.3)
    assert max(brow_mean(f) for _, f in early) >= 0.9 * GAIN
    assert max(f["jaw_floor"] for _, f in early) > 0.1
    assert max(f["lid_open"] for _, f in early) > 0.5
    late = s.step(7.0)
    assert late["weights"]["surprised"] < 0.05, late["weights"]
    assert late["jaw_floor"] < 0.01
    assert all(abs(late[b] - rest[b]) < 0.15 for b in channels.BROWS), (late, rest)


def test_skeptical_right_way_round():
    for side in (+1, -1):
        s = Synth({"side": side})
        s.step(0.0)
        s.feel("skeptical", 0.0)
        f = s.step(1.0)
        hi, lo = ("L", "R") if side > 0 else ("R", "L")
        assert f[f"brow_out_{hi}"] - f[f"brow_out_{lo}"] > 0.5 * GAIN, f
        assert f[f"brow_in_{hi}"] > f[f"brow_in_{lo}"], f
        assert f[f"brow_out_{hi}"] > 0.3 and f[f"brow_in_{lo}"] < 0, f
        # The eye under the lowered brow narrows; the corner on the raised side lifts.
        assert f["lid_asym"] * side < -0.1 and f["smile_asym"] * side > 0.1, f


def test_no_worry_brow_from_curious_and_irritated():
    for gap in (0.0, 0.3, 0.8, 1.5, 3.0):
        for ic, ii in ((1, 1), (0.5, 1), (1, 0.5), (0.6, 0.7), (0.35, 0.4), (1.3, 1.3)):
            for first in ("curious", "irritated"):
                second = "irritated" if first == "curious" else "curious"
                s = Synth()
                s.step(0.0)
                s.feel(first, 0.0, ic)
                s.feel(second, gap, ii)
                for t, f in frames(s, 0.0, 12.0):
                    for side in "LR":
                        inner, outer = f[f"brow_in_{side}"], f[f"brow_out_{side}"]
                        assert not (inner > 0.02 and outer < -0.02), (first, gap, ic, ii, t, f)


def test_smile_and_frown_do_not_cancel():
    for a, b in (("amused", "irritated"), ("excited", "irritated"), ("amused", "vulnerable")):
        s = Synth()
        s.step(0.0)
        s.feel(a, 0.0)
        s.feel(b, 0.0)
        f = s.step(1.5)
        assert abs(f["smile"]) > 0.2, (a, b, f["smile"])


def test_repeat_extends_not_restarts():
    once, twice = Synth(), Synth()
    for s in (once, twice):
        s.step(0.0)
        s.feel("skeptical", 0.0)
    a = dict(frames(once, 0.0, 10.0))
    b = {}
    for t in a:
        if abs(t - 1.5) < 1e-9:
            twice.feel("skeptical", t)
        b[t] = twice.step(t)
    for t in a:
        assert b[t]["weights"]["skeptical"] >= a[t]["weights"]["skeptical"] - 1e-9, t
    t6 = min(a, key=lambda t: abs(t - 6.0))
    assert b[t6]["weights"]["skeptical"] > a[t6]["weights"]["skeptical"] + 0.1
    # Fired again while decaying: it rises from where it is, never drops back to zero.
    s = Synth()
    s.step(0.0)
    s.feel("curious", 0.0)
    w_before = s.step(5.0)["weights"]["curious"]
    s.feel("curious", 5.0)
    assert all(f["weights"]["curious"] >= w_before - 1e-9 for _, f in frames(s, 5.0, 6.0))


def test_mood_pulls_and_relaxes():
    from engine.synth import RECIPES
    home, anchor = PERSONALITY["home"], RECIPES["irritated"]["anchor"]
    s = Synth()
    s.step(0.0)
    for t in (0.0, 3.0, 6.0, 9.0, 12.0):
        s.feel("irritated", t)
    s.step(13.0)
    mood = s.snapshot()["mood"]
    assert math.dist(mood, anchor) < math.dist(home, anchor) - 0.1, mood
    s.step(13.0 + 900.0)
    assert math.dist(s.snapshot()["mood"], home) < 0.05, s.snapshot()
    a0 = s.snapshot()["mood"][1]
    s.nudge(913.0, a=0.3)
    assert s.snapshot()["mood"][1] > a0 + 0.29


def test_boredom_and_unknown_tags():
    s = Synth()
    f0 = s.step(0.0)
    s.feel("bogus", 0.0)
    s.feel("", 0.0)
    s.feel("skeptical", 0.0, 0.0)
    assert s.step(0.0) == f0 and not s.active
    bored = s.step(600.0)
    assert s.snapshot()["boredom"] > 0.9
    assert bored["arousal"] < f0["arousal"] - 0.2
    assert bored["arousal"] >= PERSONALITY["boredom_floor"] - 1e-9
    assert bored["lid_open"] < -0.1
    s.feel("Curious", 600.0)
    assert s.snapshot()["boredom"] == 0.0 and "curious" in s.active


def test_ranges_and_speed():
    rng = random.Random(1)
    names = TAGS + ("bogus", "Amused", "")
    s = Synth()
    took, t = [], 0.0
    for i in range(120 * 50):
        t = i * DT
        if rng.random() < 0.03:
            s.feel(rng.choice(names), t, rng.uniform(0.0, 1.6))
        if rng.random() < 0.003:
            s.nudge(t, rng.uniform(-0.5, 0.5), rng.uniform(-0.5, 0.5), rng.uniform(-0.5, 0.5))
        t0 = time.perf_counter()
        f = s.step(t)
        took.append(time.perf_counter() - t0)
        for k, (lo, hi, _) in channels.FACE.items():
            assert math.isfinite(f[k]) and lo <= f[k] <= hi, (t, k, f[k])
        assert all(0.0 <= w <= 1.0 for w in f["weights"].values()), f["weights"]
        assert all(-1.0 <= m <= 1.0 for m in s.snapshot()["mood"])
    mean = sum(took) / len(took)
    print(f"step: mean {mean * 1e6:.0f} us, max {max(took) * 1e6:.0f} us over {len(took)} ticks")
    assert mean < 0.5e-3, mean


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
    print("synth OK")

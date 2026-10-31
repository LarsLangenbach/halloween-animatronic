"""
Offline tests for the animator (frank/engine/animator.py). No head, no network.

    .venv\\Scripts\\python.exe frank\\engine\\tests\\test_animator.py
"""

import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))

import engine.animator as A  # noqa: E402
from engine.animator import Animator  # noqa: E402
from engine.channels import JOINTS, blank_cue, rest_face  # noqa: E402
from engine.rig import Rig  # noqa: E402

DT = 1 / 50
SMOOTH = ("brow_in_L", "brow_out_L", "brow_in_R", "brow_out_R", "smile", "smile_asym", "jaw_floor")


def run(seconds, state="idle", target=None, face=None, talk=None, seed=1, start=100.0, check=True):
    an = A.Animator(seed=seed)
    f = rest_face()
    f.update(face or {})
    out = []
    prev = None
    n = int(seconds / DT)
    for i in range(n):
        t = start + i * DT
        cue = blank_cue()
        cue["state"], cue["target"] = state, target
        if talk:
            cue["talk"] = talk(t - start)
        j = an.step(t, f, cue)
        if check:
            for k, (lo, hi, _) in JOINTS.items():
                assert lo - 1e-9 <= j[k] <= hi + 1e-9, (k, j[k])
            if prev:
                for k in SMOOTH:
                    assert abs(j[k] - prev[k]) <= A.SPEED_CAP[k] * DT + 1e-6, (k, prev[k], j[k])
        prev = j
        out.append(j)
    return an, out


def test_blink_rates():
    for state, rate in A.BLINK_RATE.items():
        if state in ("interrupted", "farewell", "person", "greeting"):
            continue
        target = (5.0, 0.0) if state in ("listening", "speaking") else None
        an, _ = run(300, state, target, seed=7, check=False)
        per_min = an.blink_count / 5.0
        print(f"  blinks {state:10s} {per_min:5.1f}/min (target {rate})")
        assert 0.75 * rate <= per_min <= 1.3 * rate, (state, per_min, rate)


def test_ranges_and_steps():
    face = {"brow_in_L": 0.9, "brow_out_L": 1.0, "smile": 0.8, "lid_open": 0.7, "lid_squint": 0.5,
            "arousal": 1.0, "gaze_alternate": 0.6, "gaze_avert": 0.8, "lid_asym": 1.0}
    for state in ("greeting", "speaking", "interrupted", "listening", "thinking", "farewell"):
        run(20, state, (10.0, 5.0), face=face, talk=lambda s: 1.0 if int(s * 3) % 2 else 0.0)
    run(20, "idle", None, face={"brow_in_R": -1.0, "arousal": -1.0, "jaw_floor": 1.0})


def test_gaze_target():
    _, out = run(30, "greeting", (15.0, 0.0), seed=3)
    xs = [j["gaze_x"] for j in out[50:]]
    mean = sum(xs) / len(xs)
    print(f"  gaze_x mean at yaw 15 deg: {mean:.3f}")
    assert abs(mean - 0.5) < 0.05, mean
    jumps = sum(1 for a, b in zip(xs, xs[1:]) if abs(b - a) > 0.02)
    assert jumps > 30, jumps   # engaged saccades are happening


def test_thinking_looks_up():
    _, out = run(10, "thinking", (0.0, 0.0), seed=4)
    ys = [j["gaze_y"] for j in out[25:]]
    mean = sum(ys) / len(ys)
    print(f"  gaze_y mean while thinking: {mean:.3f}")
    assert mean > 0.3, mean
    an, out = run(10, "listening", (0.0, 0.0), seed=4)
    ys = [j["gaze_y"] for j in out[25:]]
    assert sum(ys) / len(ys) < 0.1


def test_snap_back_from_thinking():
    an = A.Animator(seed=5)
    f = rest_face()
    cue = blank_cue()
    cue["target"] = (0.0, 0.0)
    t = 0.0
    cue["state"] = "thinking"
    for _ in range(100):
        j = an.step(t, f, cue)
        t += DT
    assert j["gaze_y"] > 0.3
    cue["state"] = "speaking"
    for _ in range(6):
        j = an.step(t, f, cue)
        t += DT
    assert abs(j["gaze_y"]) < 0.1, j["gaze_y"]


def test_brow_beats():
    def talk(s):   # syllables at ~4 Hz, phrases of 2 s with 0.5 s pauses
        if s % 2.5 > 2.0:
            return 0.0
        return 0.8 if (s * 4) % 1 < 0.6 else 0.1
    an, out = run(120, "speaking", (0.0, 0.0), talk=talk, seed=9)
    b = an.beats
    print(f"  brow beats in 120 s of talk: {len(b)}")
    assert len(b) >= 5, len(b)
    assert all(y - x >= A.BEAT_GAP - 1e-9 for x, y in zip(b, b[1:])), b
    an, _ = run(30, "speaking", (0.0, 0.0), seed=9)
    assert not an.beats


def test_events():
    an = A.Animator(seed=2)
    f = rest_face()
    cue = blank_cue()
    t = 0.0
    for _ in range(10):
        an.step(t, f, cue)
        t += DT
    n = an.blink_count
    cue["events"] = ["long_blink"]
    an.step(t, f, cue)
    cue["events"] = []
    lows = []
    for _ in range(40):
        t += DT
        lows.append(an.step(t, f, cue)["lid_top_L"])
    assert an.blink_count == n + 1
    shut = sum(1 for v in lows if v < 0.05)
    assert shut >= 12, shut     # ~0.3 s fully shut
    t += 2.0
    cue["events"] = ["flinch"]
    j0 = an.step(t, f, cue)
    cue["events"] = []
    for _ in range(15):
        t += DT
        j = an.step(t, f, cue)
    assert j["brow_in_L"] < -0.2 and j["brow_in_R"] < -0.2, j
    t += 2.0
    cue["events"] = ["phrase_end"]
    n = an.blink_count
    an.step(t, f, cue)
    cue["events"] = []
    for _ in range(30):
        t += DT
        an.step(t, f, cue)
    assert an.blink_count >= n + 1


def test_greeting_and_asym():
    _, out = run(1.2, "greeting", (0.0, 0.0), seed=6)
    peak = max(j["brow_in_L"] for j in out)
    assert peak > 0.35, peak
    _, out = run(3, "person", (0.0, 0.0), face={"lid_asym": 1.0}, seed=6)
    j = out[-1]
    assert j["lid_top_L"] < j["lid_top_R"] or min(j["lid_top_L"], j["lid_top_R"]) < 0.3, j


def test_personality():
    an = A.Animator({"blink_rate": 0.5, "favoured": "R"}, seed=1)
    f = rest_face()
    cue = blank_cue()
    for i in range(int(300 / DT)):
        an.step(i * DT, f, cue)
    assert an.blink_count / 5 < 0.75 * A.BLINK_RATE["idle"], an.blink_count / 5


def test_speed():
    an = A.Animator(seed=1)
    class W:
        def link(self, text):
            pass

        def expression(self, *a):
            pass

    rig = Rig(W())
    f = rest_face()
    f["brow_in_L"] = 0.4
    cue = blank_cue()
    cue["state"], cue["target"] = "speaking", (8.0, 2.0)
    n = 3000
    t0 = time.perf_counter()
    for i in range(n):
        cue["talk"] = (i % 13) / 13
        rig.apply(an.step(i * DT, f, cue), i * DT)
    ms = (time.perf_counter() - t0) / n * 1000
    print(f"  step + apply: {ms:.3f} ms")
    assert ms < 2.0, ms


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
    print("animator OK")

"""
Offline tests for the rig (frank/engine/rig.py), with a fake writer that records its lines.

    .venv\\Scripts\\python.exe frank\\engine\\tests\\test_rig.py
"""

import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))

from engine.channels import rest_joints  # noqa: E402
from engine.rig import CONFIG, Rig  # noqa: E402


class Fake:
    def __init__(self):
        self.lines = []
        self.expr = []

    def link(self, text):
        self.lines.append(text)

    def expression(self, smile, asym=0.0, jaw_floor=0.0):
        self.expr.append((smile, asym, jaw_floor))


def poses():
    rig = Rig()
    with open(rig.cfg["poses_file"], encoding="utf-8") as f:
        return rig, json.load(f)


def test_rest_angles():
    rig, p = poses()
    q = rig.apply(rest_joints(), 0.0)
    for s in ("LLL", "LLR"):
        assert q[s] == rig.quantise(p["centre"][s]), (s, q[s])
    for s in ("CUR", "CLR"):   # top lids at 0.85 between SHUT and OPEN
        want = p["shut"][s] + 0.85 * (p["open"][s] - p["shut"][s])
        assert abs(q[s] - want) <= 0.25, (s, q[s], want)
    for s in ("CUL", "CLL"):   # bottom lids at OPEN
        assert q[s] == p["open"][s], (s, q[s])
    for s in ("JL", "JR", "LUL", "LUR"):
        assert q[s] == p["level"][s], (s, q[s])
    w = Fake()
    r = Rig(w)
    r.rest(pause=0)
    assert len(w.lines) == 10 and w.expr == [(0.0, 0.0, 0.0)], (w.lines, w.expr)
    assert "8 %g" % rig.quantise(p["centre"]["LLL"]) in w.lines


def test_mapping():
    rig, p = poses()
    j = rest_joints()
    j.update(gaze_x=1.0, gaze_y=-1.0, lid_top_L=0.0, lid_top_R=1.0, brow_in_L=1.0, brow_out_R=-1.0)
    q = rig.apply(j, 0.0)
    assert q["LLL"] == p["centre"]["LLL"] + 30 and q["LLR"] == p["centre"]["LLR"] - 15
    assert q["CUR"] == p["shut"]["CUR"] and q["CLR"] == p["open"]["CLR"]      # lid_top_L, lid_top_R
    assert q["LUR"] == p["level"]["LUR"] + p["brow_travel"]["raise"]           # brow_in_L, dir +1
    assert q["JL"] == p["level"]["JL"] - p["brow_travel"]["lower"]             # brow_out_R, dir +1


def test_send_on_change_and_budget():
    w = Fake()
    rig = Rig(w)
    budget = rig.budget
    j = rest_joints()
    rig.apply(j, 0.0)                       # tick 0: everything is new
    rig.apply(j, 0.02)                      # tick 1: the rest of the first frame
    assert len(w.lines) == 10, w.lines
    n = len(w.lines)
    rig.apply(j, 0.04)
    rig.apply(j, 0.06)
    assert len(w.lines) == n, "nothing changed, nothing sent"
    j["gaze_x"] = 0.01                      # 0.3 deg: inside the deadband
    rig.apply(j, 0.08)
    assert len(w.lines) == n
    j["gaze_x"] = 0.1                       # 3 deg
    rig.apply(j, 0.10)
    assert len(w.lines) == n + 1 and w.lines[-1].startswith("8 "), w.lines[-1]
    # everything moves at once: at most the budget per tick, the largest change first
    old = rig.angles(j)
    for k, v in (("gaze_x", -1.0), ("gaze_y", 1.0), ("lid_top_L", 0.0), ("lid_top_R", 0.0),
                 ("lid_bot_L", 0.3), ("lid_bot_R", 0.5), ("brow_in_L", 1.0), ("brow_in_R", 0.8),
                 ("brow_out_L", -0.6), ("brow_out_R", 0.2)):
        j[k] = v
    n = len(w.lines)
    sizes = []
    for i in range(4):
        before = len(w.lines)
        rig.apply(j, 0.12 + i * 0.02)
        sizes.append(len(w.lines) - before)
    assert all(s <= budget for s in sizes), sizes
    assert sum(sizes) == 10, sizes
    after = rig.angles(j)
    big = max(after, key=lambda s: abs(after[s] - old[s]))
    assert w.lines[n].split()[0] == str(rig.pin[big]), (w.lines[n], big)
    # a brow change waits for a brow tick (every other tick)
    if rig.ticks % 2 == 0:
        rig.apply(j, 1.0)
    n = len(w.lines)
    j["brow_in_L"] = 0.0
    rig.apply(j, 1.02)                      # odd tick: no brows
    assert len(w.lines) == n, w.lines[n:]
    rig.apply(j, 1.04)
    assert len(w.lines) == n + 1 and w.lines[-1].startswith("7 "), w.lines[n:]


def test_expression():
    w = Fake()
    rig = Rig(w)
    j = rest_joints()
    rig.apply(j, 0.0)
    rig.apply(j, 0.02)
    j["smile"], j["jaw_floor"] = 0.5, 0.2
    rig.apply(j, 0.04)
    rig.apply(j, 0.06)
    rig.apply(j, 0.08)
    assert w.expr == [(0.0, 0.0, 0.0), (0.5, 0.0, 0.2)], w.expr

    class LinkOnly:
        def __init__(self):
            self.lines = []

        def link(self, text):
            self.lines.append(text)
    r = Rig(LinkOnly())
    r.apply(j, 0.0)                         # no expression() yet: fine


def test_disabled_and_swap():
    with open(CONFIG, encoding="utf-8") as f:
        cfg = json.load(f)
    cfg["disabled"] = ["CLR", "JR"]
    cfg["swap_brow_sides"] = True
    cfg["poses"] = os.path.normpath(os.path.join(os.path.dirname(CONFIG), cfg["poses"]))
    with tempfile.TemporaryDirectory() as d:
        path = os.path.join(d, "rig.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(cfg, f)
        w = Fake()
        rig = Rig(w, path)
        rig.rest(pause=0)
        j = rest_joints()
        for i in range(20):
            j["lid_top_R"] = (i % 2) * 0.5
            j["brow_out_L"] = (i % 3) * 0.4
            j["brow_in_L"] = (i % 2) * 0.7
            rig.apply(j, i * 0.02)
        pins = {line.split()[0] for line in w.lines}
        assert "13" not in pins and "5" not in pins, pins
        assert rig.socket_of["brow_in_L"] == "LUL" and rig.socket_of["brow_out_L"] == "JL"
        assert "6" in pins


def test_preview():
    rig = Rig()
    q = rig.apply(rest_joints(), 0.0)
    assert len(q) == 10 and rig.lines == 0


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
    print("rig OK")

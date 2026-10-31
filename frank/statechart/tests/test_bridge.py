"""
The chart-driven engine against the hand-written one: the same evening, on a fake clock, must
give the same states and the same expressions. Also: a chart edited on disk is picked up by the
next tick, and a broken one is refused. No head, no keys.

    .venv\\Scripts\\python.exe frank\\statechart\\tests\\test_bridge.py
"""

import json
import os
import shutil
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
sys.stdout.reconfigure(encoding="utf-8")

import engine.orchestrator as orchestrator  # noqa: E402
import statechart.bridge as bridge  # noqa: E402
from engine.orchestrator import Engine  # noqa: E402
from statechart.bridge import DEFAULT_CHART, ChartedEngine  # noqa: E402

TICK = 0.02


class Clock:
    """Stands in for the time module inside the orchestrator and the bridge."""

    def __init__(self):
        self.t = 1000.0

    def monotonic(self):
        return self.t

    def perf_counter(self):
        return self.t

    def time(self):
        return 1.8e9 + self.t

    def sleep(self, s):
        self.t += s


def person(pid, engaged=False, talking=False):
    return {"id": pid, "yaw": 5.0, "pitch": 0.0, "dist": 1.2, "engaged": engaged, "talking": talking}


def script():
    """(at seconds, what, value): one visitor's evening, with every kind of event."""
    return [
        (0.5, "vision", {"people": [], "session": False}),
        (1.0, "vision", {"people": [person(1)], "session": False}),
        (1.5, "event", "arrived"),
        (2.0, "vision", {"people": [person(1, engaged=True)], "session": True}),
        (4.0, "ui", {"kind": "hearing", "text": "hello"}),
        (5.0, "ui", {"kind": "visitor", "said": "hello Frank"}),
        (5.4, "ui", {"kind": "face", "tag": "amused"}),
        (6.2, "talk", 0.6), (6.4, "talk", 0.5), (6.6, "talk", 0.6),
        (6.7, "ui", {"kind": "interrupted", "heard": "Well"}),
        (6.72, "event", "interrupted"),   # the voice's flush, a moment later: still one interruption
        (8.0, "ui", {"kind": "sound", "tag": "chuckle"}),
        (9.0, "ui", {"kind": "seen", "what": "moved"}),
        (11.0, "ui", {"kind": "seen", "what": "still"}),
        (12.0, "ui", {"kind": "seen", "what": "dark"}),
        (13.0, "ui", {"kind": "seen", "what": "light"}),
        (14.0, "vision", {"people": [], "session": False}),
        (14.1, "event", "left"),
        (18.0, "event", "arrived"),
    ]


def run(cls, **kw):
    clock = Clock()
    orchestrator.time, bridge.time = clock, clock
    e = cls(writer=None, **kw)
    e.watch(None)
    felt, cues = [], []
    real_feel, real_step = e.synth.feel, e.anim.step

    def feel(tag, t, intensity=1.0):
        felt.append((round(t - 1000, 2), tag, round(intensity, 2)))
        return real_feel(tag, t, intensity)

    def step(t, face, cue):
        cues.append((round(t - 1000, 2), cue["state"], tuple(cue["events"])))
        return real_step(t, face, cue)

    e.synth.feel, e.anim.step = feel, step
    events = sorted(script(), key=lambda x: x[0])
    end = 21.0
    while clock.t - 1000 < end:
        now = clock.t - 1000
        while events and events[0][0] <= now + 1e-9:
            _, what, value = events.pop(0)
            if what == "vision":
                e.vision(value)
            elif what == "event":
                e.event(value)
            elif what == "ui":
                e.on_ui(value)
            elif what == "talk":
                e.talk(value)
        e._tick(clock.monotonic())
        clock.t += TICK
    return e, felt, cues


def changes(cues):
    out, last = [], None
    for t, state, _ in cues:
        if state != last:
            out.append((t, state))
            last = state
    return out


def close(a, b, slack=0.05):
    """Two lists of (time, value...) equal, with the times within slack."""
    if len(a) != len(b):
        return False
    return all(abs(x[0] - y[0]) <= slack and x[1:] == y[1:] for x, y in zip(a, b))


def test_same_evening():
    _, felt0, cues0 = run(Engine)
    _, felt1, cues1 = run(ChartedEngine)
    s0, s1 = changes(cues0), changes(cues1)
    assert close(s0, s1), f"states differ:\n engine {s0}\n chart  {s1}"
    assert close(felt0, felt1), f"expressions differ:\n engine {felt0}\n chart  {felt1}"
    ev0 = [(t, ev) for t, _, evs in cues0 for ev in evs]
    ev1 = [(t, ev) for t, _, evs in cues1 for ev in evs]
    assert close(ev0, ev1), f"animator events differ:\n engine {ev0}\n chart  {ev1}"
    return s1, felt1


def test_reload_on_save():
    tmp = tempfile.mkdtemp()
    try:
        path = os.path.join(tmp, "frank.json")
        shutil.copy(DEFAULT_CHART, path)
        e, _, _ = run(ChartedEngine, chart=path)
        doc = json.load(open(path, encoding="utf-8"))
        doc["root"]["states"]["social"]["states"]["auto"]["states"]["idle"]["profile"] = "person"
        with open(path, "w", encoding="utf-8") as f:
            json.dump(doc, f)
        os.utime(path, (e.chart_mtime + 5, e.chart_mtime + 5))
        e.chart_checked -= bridge.RELOAD_EVERY
        e._tick(orchestrator.time.monotonic())
        assert e.mode == "person", f"the edited chart was not picked up: {e.mode}"
        doc["root"]["states"]["social"]["initial"] = "nowhere"
        with open(path, "w", encoding="utf-8") as f:
            json.dump(doc, f)
        os.utime(path, (e.chart_mtime + 10, e.chart_mtime + 10))
        e.chart_checked -= bridge.RELOAD_EVERY
        e._tick(orchestrator.time.monotonic())
        assert e.mode == "person", "a broken chart must not replace a working one"
    finally:
        shutil.rmtree(tmp)


if __name__ == "__main__":
    states, felt = test_same_evening()
    test_reload_on_save()
    print(f"bridge OK: {len(states)} state changes and {len(felt)} expressions match the hand-written engine; "
          f"reload on save works")

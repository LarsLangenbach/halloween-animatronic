"""
End-to-end test of the face engine (orchestrator + synthesiser + animator + rig) in real time,
with a stand-in for mouth.Mouth that records what would go down the wire. About 10 s.

    .venv\\Scripts\\python.exe frank\\engine\\tests\\test_engine.py
"""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
sys.stdout.reconfigure(encoding="utf-8")

from engine import Engine  # noqa: E402


class FakeMouth:
    """What the engine needs of mouth.Mouth: link(), expression(), feed(), face(), flush(), open."""
    port, program = "fake", "pico_servo_ctl.py"

    def __init__(self):
        self.lines, self.expressions, self.fed, self.faces, self.flushed = [], [], 0, [], 0
        self.open = 0.0

    def link(self, text):
        self.lines.append(text)

    def expression(self, smile, asym=0.0, jaw_floor=0.0):
        self.expressions.append((smile, asym, jaw_floor))

    def feed(self, pcm):
        self.fed += 1

    def face(self, name):
        self.faces.append(name)

    def flush(self):
        self.flushed += 1

    def close(self):
        pass


def wait_for(cond, timeout, what):
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        if cond():
            return
        time.sleep(0.02)
    raise AssertionError(f"timed out: {what}")


def main():
    log = []
    mouth = FakeMouth()
    e = Engine(writer=mouth, log=lambda **k: log.append(k)).start()
    wait_for(lambda: e.snapshot().get("joints"), 1.0, "first tick")
    s = e.snapshot()
    assert s["state"] == "idle", s["state"]
    assert set(s["joints"]) >= {"gaze_x", "lid_top_L", "brow_in_L", "smile"}, s["joints"].keys()

    # the visitor finishes a line: he thinks, and previews his reply's first tag
    e.on_ui({"kind": "visitor", "said": "Hello Frank"})
    e.on_ui({"kind": "frank_start"})
    e.on_ui({"kind": "face", "tag": "amused"})
    wait_for(lambda: e.snapshot()["state"] == "thinking", 0.5, "thinking")
    time.sleep(0.2)
    assert e.snapshot()["face"]["weights"]["amused"] > 0.05, "no preview of the first tag"

    # his voice plays: speaking, and the tag lands on the audio clock
    e.face("amused")
    for _ in range(40):
        e.feed(b"\0" * 960)
        mouth.open = 0.6
        time.sleep(0.02)
    assert e.snapshot()["state"] == "speaking", e.snapshot()["state"]
    assert e.snapshot()["face"]["weights"]["amused"] > 0.3, e.snapshot()["face"]["weights"]
    assert mouth.fed == 40 and mouth.faces[-1] == "amused"

    # cut off: interrupted, then back to listening
    e.flush()
    mouth.open = 0.0
    wait_for(lambda: e.snapshot()["state"] == "interrupted", 0.3, "interrupted")
    wait_for(lambda: e.snapshot()["state"] == "listening", 1.5, "listening after the interruption")
    assert mouth.flushed == 1

    # someone talking on his left: the eyes go there
    e.vision({"session": True, "people": [
        {"id": 1, "engaged": True, "talking": True, "yaw": 15.0, "pitch": 0.0, "dist": 1.0}]})
    time.sleep(0.8)
    xs = []
    for _ in range(25):
        xs.append(e.snapshot()["joints"]["gaze_x"])
        time.sleep(0.02)
    assert e.snapshot()["target"] == (15.0, 0.0), e.snapshot()["target"]
    assert sum(xs) / len(xs) > 0.2, f"gaze_x mean {sum(xs) / len(xs):.2f} for a target 15 deg to his left"

    # a different tag straight after another waits its turn (MIN_DWELL)
    e.tag("skeptical")
    time.sleep(0.1)
    t_ask = time.monotonic()
    e.tag("irritated")
    wait_for(lambda: e.fired[0] == "irritated", 2.0, "irritated fired")
    assert time.monotonic() - t_ask > 0.9, "irritated replaced skeptical before the dwell"
    e.tag("surprised")
    time.sleep(0.1)
    assert e.fired[0] == "surprised", "surprised should cut in"

    # a tag-only reply holds its face
    e.on_ui({"kind": "visitor", "said": "What do you think of me?"})
    e.on_ui({"kind": "face", "tag": "skeptical"})
    e.on_ui({"kind": "frank_end", "silent": True, "interrupted": False})
    time.sleep(0.5)
    assert e.snapshot()["face"]["weights"]["skeptical"] > 0.3, e.snapshot()["face"]["weights"]

    # what went down the wire
    assert mouth.lines, "nothing sent to the eye board"
    pins = {int(line.split()[0]) for line in mouth.lines}
    assert pins <= {4, 5, 6, 7, 8, 9, 10, 11, 12, 13}, pins
    assert mouth.expressions, "no expression sent to the mouth"
    rate = e.ticks / (time.monotonic() - s["t"])
    assert rate > 40, f"tick rate {rate:.1f} Hz"
    assert e.snapshot()["error"] is None, e.snapshot()["error"]
    states = [r["state"] for r in log if r.get("what") == "engine_state"]
    e.stop()
    print(f"engine OK: {e.ticks} ticks at {rate:.0f} Hz, {len(mouth.lines)} eye-board lines, "
          f"{len(mouth.expressions)} mouth expressions, states {' > '.join(states)}")


if __name__ == "__main__":
    main()

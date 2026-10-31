"""
Prompt to face animation, offline: a stand-in for Claude returns a timeline, clean() makes it
safe, and the Player runs it on a real Engine (no head): tags fire, the emotion map glides, the
eyes hold, events happen, and the face is handed back at the end. About 6 s.

    .venv\\Scripts\\python.exe frank\\engine\\tests\\test_animate.py
"""

import json
import sys
import time
import types
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
sys.stdout.reconfigure(encoding="utf-8")

from engine import Engine, animate  # noqa: E402

TIMELINE = {
    "title": "the terrible pun",
    "duration": 3.2,
    "keys": [
        {"t": 0.0, "kind": "look", "tag": "", "intensity": 0, "p": 0, "a": 0, "d": 0, "event": "", "yaw": 0, "pitch": 0},
        {"t": 0.2, "kind": "feel", "tag": "", "intensity": 0, "p": -0.3, "a": 0.1, "d": 0.4, "event": "", "yaw": 0, "pitch": 0},
        {"t": 0.4, "kind": "tag", "tag": "skeptical", "intensity": 0.8, "p": 0, "a": 0, "d": 0, "event": "", "yaw": 0, "pitch": 0},
        {"t": 1.0, "kind": "look", "tag": "", "intensity": 0, "p": 0, "a": 0, "d": 0, "event": "", "yaw": 15, "pitch": 12},
        {"t": 1.1, "kind": "event", "tag": "", "intensity": 0, "p": 0, "a": 0, "d": 0, "event": "long_blink", "yaw": 0, "pitch": 0},
        {"t": 2.2, "kind": "feel", "tag": "", "intensity": 0, "p": 0.45, "a": 0.25, "d": 0.35, "event": "", "yaw": 0, "pitch": 0},
        {"t": 2.4, "kind": "tag", "tag": "amused", "intensity": 0.9, "p": 0, "a": 0, "d": 0, "event": "", "yaw": 0, "pitch": 0},
        # junk the cleaner must drop or clamp
        {"t": 99, "kind": "tag", "tag": "furious", "intensity": 5, "p": 0, "a": 0, "d": 0, "event": "", "yaw": 0, "pitch": 0},
        {"t": 1.5, "kind": "look", "tag": "", "intensity": 0, "p": 0, "a": 0, "d": 0, "event": "", "yaw": 400, "pitch": -90},
        {"t": 1.6, "kind": "dance", "tag": "", "intensity": 0, "p": 0, "a": 0, "d": 0, "event": "", "yaw": 0, "pitch": 0},
    ],
}


class FakeClient:
    """What generate() uses of anthropic.Anthropic: client.beta.messages.create(...)."""

    def __init__(self, reply):
        self.kw = None
        self.beta = types.SimpleNamespace(messages=types.SimpleNamespace(create=self._create))
        self.reply = reply

    def _create(self, **kw):
        self.kw = kw
        block = types.SimpleNamespace(type="text", text=json.dumps(self.reply))
        return types.SimpleNamespace(content=[block], stop_reason="end_turn", model=kw["model"])


def main():
    # clean(): junk dropped, numbers clamped, keys in order
    anim = animate.clean(TIMELINE)
    kinds = [k["kind"] for k in anim["keys"]]
    assert "dance" not in kinds and not any(k.get("tag") == "furious" for k in anim["keys"]), kinds
    wild = [k for k in anim["keys"] if k["kind"] == "look" and k["t"] == 1.5][0]
    assert wild["yaw"] == animate.LOOK_MAX[0] and wild["pitch"] == -animate.LOOK_MAX[1], wild
    assert [k["t"] for k in anim["keys"]] == sorted(k["t"] for k in anim["keys"])

    # generate() with a stand-in client: the request asks for JSON matching the schema
    client = FakeClient(TIMELINE)
    got = animate.generate("he hears a terrible pun", client=client)
    assert got["title"] == "the terrible pun" and got["prompt"] == "he hears a terrible pun"
    fmt = client.kw["output_config"]["format"]
    assert fmt["type"] == "json_schema" and fmt["schema"]["properties"]["keys"]["items"]["required"]
    assert client.kw["model"] == animate.MODEL and "emotion map" in client.kw["system"]

    # the glide between feel keys
    feels = [k for k in anim["keys"] if k["kind"] == "feel"]
    assert animate.glide(feels, 0.1) is None
    mid = animate.glide(feels, 1.2)
    assert -0.3 < mid[0] < 0.45, mid
    assert animate.glide(feels, 5.0) == (0.45, 0.25, 0.35)

    # play it on a real engine
    e = Engine(writer=None).start()
    time.sleep(0.2)
    player = animate.Player(e).play(got)
    seen = {"steered": False, "looked_up": False, "skeptical": 0.0, "amused": 0.0}
    t_end = time.monotonic() + got["duration"] + 1.5
    while time.monotonic() < t_end:
        s = e.snapshot()
        w = s["face"]["weights"]
        seen["skeptical"] = max(seen["skeptical"], w["skeptical"])
        seen["amused"] = max(seen["amused"], w["amused"])
        seen["steered"] |= s.get("steered") is not None
        seen["looked_up"] |= s["target"] is not None and s["target"][1] > 5
        time.sleep(0.05)
    s = e.snapshot()
    assert seen["steered"] and seen["looked_up"], seen
    assert seen["skeptical"] > 0.3 and seen["amused"] > 0.3, seen
    assert s.get("steered") is None and not player.playing, "the face wasn't handed back"
    assert e.gaze_override is None
    events = [r.get("name") for r in e.recent if r.get("what") == "engine_event"]
    assert "long_blink" in events, events

    # stop() mid-performance hands the face back too
    player.play(got)
    time.sleep(0.6)
    player.stop()
    time.sleep(0.1)
    assert e.snapshot().get("steered") is None and e.gaze_override is None
    e.stop()
    print(f"animate OK: {len(anim['keys'])} keys after cleaning, peaks skeptical {seen['skeptical']:.2f} "
          f"amused {seen['amused']:.2f}")


if __name__ == "__main__":
    main()

"""
The studio's live robot: Frank's face engine driving perform/body.py's board models in this
process, as the public site does in Pyodide. frank/online/browser.py is imported as it is (its
engine, mouth, board models and preview.Api); it starts no threads, so one ticker here steps it
50 times a second. Don't call engine.start(): the engine would tick twice.

On top of it:
  - servo limits and speeds: each servo's soft limits (robot.json `soft`, [min, max] horn
    degrees in the board program's own degrees) and its speed, applied where the horn moves
    (Limited.tick). An animation that asks for more shows on the twin as a servo held at its
    limit, and the page names it.
  - holds: a servo or an animation channel pinned by the Constraints page's try sliders.
  - one lock: the ticker and every request that touches the engine or the player take it.

    rt = Runtime()          # imports the engine (about 0.2 s), nothing runs yet
    rt.start()              # the 50 Hz ticker
    with rt.lock: rt.api.post("/tag", {"name": "curious"})
"""

import json
import os
import sys
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "frank" / "online"))
import browser as B  # noqa: E402   (Frank's engine, mouth, board models and Api; no threads)

HZ = 50


class Limited(B.BODY.Robot):
    """body.Robot with soft limits, per-servo speeds and holds where the horns move. The board
    models still say what was asked (cmd); the horns go only as far as the limits let them."""

    def setup(self):
        self.soft, self.hold, self.want, self.clamped = {}, {}, {}, {}
        for sid, s in self.servos.items():
            lo, hi = self.firmware_range(sid)
            soft = s.get("soft") or [lo, hi]
            self.soft[sid] = (max(lo, float(soft[0])), min(hi, float(soft[1])))

    def firmware_range(self, sid):
        """The angles the board program itself allows this servo, in its own degrees."""
        s = self.servos[sid]
        b = self.boards[s["board"]]
        j = getattr(b, "j", {}).get(sid)   # cogley_mouth keeps each servo's limits by name
        if j:
            return float(j["lo"]), float(j["hi"])
        return -27.0, 207.0                # pico_servo_ctl clamps every pin to this

    def tick(self, dt):
        with self.lock:
            for b in self.boards.values():
                b.tick(dt)
            for (board, pin), sid in self.by_pin.items():
                b = self.boards[board]
                st = b.pins.get(pin)
                if not st:
                    continue
                if sid in self.hold:
                    want, live = b.pulse(self.hold[sid]), True
                    self.clamped[sid] = False
                else:
                    deg, (lo, hi) = b.degrees(st["us"]), self.soft[sid]
                    self.clamped[sid] = st["live"] and (deg < lo - 0.25 or deg > hi + 0.25)
                    want, live = b.pulse(min(max(deg, lo), hi)), st["live"]
                self.want[sid] = want
                cur = self.phys[sid]
                if cur is None:
                    self.phys[sid] = want
                elif live:
                    step = self.speed[sid] * B.BODY.US_PER_HORN_DEG * dt
                    d = want - cur
                    self.phys[sid] = want if abs(d) <= step else cur + (step if d > 0 else -step)

    def frame(self):
        f = super().frame()
        with self.lock:
            for sid, s in f["servos"].items():
                if sid in self.want:
                    s["cmd"] = round(self.want[sid], 1)
                s["clamped"] = bool(self.clamped.get(sid))
                s["held"] = sid in self.hold
        return f


class Runtime:
    def __init__(self):
        self.B = B
        self.robot, self.engine, self.api = B.robot, B.engine, B.api
        self.api.info["online"] = False      # real prompt-to-animation here: frank/.env has the key
        self.robot.__class__ = Limited       # the same object the mouth's wire feeds
        self.robot.setup()
        self.lock = threading.RLock()
        self.channel_hold = {}               # animation channel -> value, from the try sliders
        self.on_tick = []                    # f(now), stepped under the lock (the state machine)
        self.running = False
        rig = self.engine.rig
        apply = rig.apply

        def held_apply(joints, t=None):      # a held channel overrides the animator's output
            return apply({**joints, **self.channel_hold} if self.channel_hold else joints, t)
        rig.apply = held_apply

    @property
    def player(self):
        return self.api.player

    def start(self):
        if not self.running:
            self.running = True
            threading.Thread(target=self._run, name="studio-ticker", daemon=True).start()
        return self

    def stop(self):
        self.running = False

    def _run(self):
        period = 1.0 / HZ
        nxt = time.monotonic()
        while self.running:
            with self.lock:
                now = time.monotonic()
                try:
                    B.tick()
                except Exception as e:      # the face never stops for a bug
                    print(f"tick: {type(e).__name__}: {e}")
                for f in list(self.on_tick):
                    try:
                        f(now)
                    except Exception as e:
                        print(f"tick hook: {type(e).__name__}: {e}")
            nxt += period
            time.sleep(max(0.0, nxt - time.monotonic()))
            if nxt < time.monotonic() - 0.5:   # fell far behind (a breakpoint, a sleep): catch up
                nxt = time.monotonic()

    def body_frame(self):
        f = self.robot.frame()
        f.update(kind="frame", lines=[], ports={"mouth": {"device": "simulated", "programs": 1}})
        return f

    def twin_file(self, name):
        """(bytes, content type) for the twin page's /robot, /rig, /camera and /model, or None."""
        spec = self.robot.spec
        if name == "robot":
            return json.dumps(spec).encode(), "application/json"
        rig = self.robot.file("rig")
        if name == "rig" and rig and rig.exists():
            return rig.read_bytes(), "application/json"
        if name == "model" and rig and rig.exists():
            glb = rig.parent / json.loads(rig.read_text(encoding="utf-8"))["model"]
            if glb.exists():
                return glb.read_bytes(), "model/gltf-binary"
        cam = self.robot.file("camera")
        if name == "camera" and cam and cam.exists():
            return cam.read_bytes(), "application/json"
        return None

    def play(self, anim):
        """Play a timeline on the face (the caller holds the lock)."""
        return self.api.post("/play", {"anim": anim})

    def generate(self, prompt):
        """Claude writes a performance (about 10 s; don't hold the lock). The site's pre-written
        examples answer their own prompts when there is no key. Returns (anim, note)."""
        from engine import animate as A
        canned = B.CANNED.get(B.prompt_key(prompt))
        try:
            anim = A.generate(prompt)
            return anim, None
        except RuntimeError as e:
            if canned:
                return dict(canned, prompt=prompt), f"{e}; played the pre-written one"
            raise


def key_available():
    try:
        import brain
        brain.load_env()
        return brain.available("opus-5.5")
    except Exception:
        return bool(os.environ.get("ANTHROPIC_API_KEY"))

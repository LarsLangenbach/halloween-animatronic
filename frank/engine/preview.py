"""
Frank's face engine, live in the browser: a local page that draws his face from the joint
channels 30 times a second, with buttons for every tag, state and event, a pad for where the
visitor stands and a Talk switch that feeds a fake voice into the engine. It needs no head,
no camera, no microphone and no API keys.

    python frank/engine/preview.py                 then open http://localhost:8820
    python frank/engine/preview.py --head          the real head too: the mouth board (auto port)
    python frank/engine/preview.py --head COM5     ... on that port (needs pyserial:
                                                   uv run --no-project --with pyserial python ...)

    --port N      default 8820
    --stand-in    use the stand-in engine below even when the real one imports

Without --head the Engine runs with writer=None (no servos). With --head it gets a
mouth.Mouth as its writer, so the page drives the real eyes, lids, brows and mouth corners.

The page (preview.html) asks GET /snapshot for engine.snapshot() and draws it with
face_draw.js. Its actions are POSTs: /tag {name, intensity?}, /state {name}, /event {name},
/target {yaw, pitch} or {clear: true} (the visitor, in degrees: yaw + to his left, pitch + up),
/talk {on}. GET /meta lists the names and ranges from channels.py.

While Talk is on, a fake syllable loudness envelope (about 5 syllables a second, in phrases
with pauses) goes into the engine as his voice, 50 times a second: engine.talk(level) when
the Engine has that method, else engine.talk_level = level.

If `from engine import Engine` fails (it is being written in parallel), a small stand-in
with the same methods makes a plausible moving face, so the page works anyway.

It listens on 127.0.0.1 only, so other computers can't open it. Its actions need the X-Frank
header and a localhost address, so other websites open in the same browser can't use it
either (the same rule as web.py).
"""

import argparse
import json
import math
import random
import re
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

HERE = Path(__file__).parent
FRANK = HERE.parent
sys.path.insert(0, str(FRANK))   # from engine import Engine; import mouth
sys.path.insert(0, str(HERE))    # import channels, even while engine/__init__.py is half-written
import channels  # noqa: E402
from channels import JOINTS, STATES, TAGS, EVENTS, clamp, rest_face, rest_joints  # noqa: E402

PAGE = HERE / "preview.html"
FILES = {"/": (PAGE, "text/html; charset=utf-8"),
         "/face_draw.js": (HERE / "face_draw.js", "text/javascript; charset=utf-8")}
HOSTS = ("localhost", "127.0.0.1")
ENGINE_EVENTS = ("arrived", "left", "moved", "interrupted", "dark")   # Engine.event(), per the contract
NAME = re.compile(r"^[a-z_]{1,32}$")


# ----- the stand-in engine -----

# Tag -> joint offsets from rest, roughly the recipes in docs/FACE_ENGINE.md "The ten tags".
RECIPES = {
    "neutral": {},
    "curious": dict(brow_in_L=.6, brow_out_L=.6, brow_in_R=.6, brow_out_R=.6, lid_top=.15),
    "excited": dict(brow_in_L=1, brow_out_L=1, brow_in_R=1, brow_out_R=1, lid_top=.15, smile=.8),
    "skeptical": dict(brow_in_L=.6, brow_out_L=.8, brow_in_R=-.4, brow_out_R=-.2, lid_top_L=-.3,
                      smile_asym=.6, smile=.1),
    "amused": dict(brow_in_L=.3, brow_out_L=.5, lid_bot=-.45, smile=.6, smile_asym=.35),
    "concentrating": dict(brow_in_L=-.5, brow_in_R=-.5, lid_top=-.15, gaze_x=.35, gaze_y=.45),
    "confused": dict(brow_in_L=-.3, brow_out_L=-.1, brow_in_R=.5, brow_out_R=.4, smile=-.2,
                     smile_asym=-.3),
    "irritated": dict(brow_in_L=-.8, brow_out_L=-.5, brow_in_R=-.8, brow_out_R=-.5, lid_top=-.25,
                      lid_bot=-.3, smile=-.6),
    "surprised": dict(brow_in_L=1, brow_out_L=1, brow_in_R=1, brow_out_R=1, lid_top=.15, jaw_floor=.5),
    "vulnerable": dict(brow_in_L=.7, brow_out_L=-.5, brow_in_R=.7, brow_out_R=-.5, lid_top=-.2,
                       smile=-.3, gaze_x=-.3, gaze_y=-.35),
}
ANCHORS = {"neutral": (0, 0, 0), "curious": (.3, .4, 0), "excited": (.62, .75, .38),
           "skeptical": (-.25, .1, .45), "amused": (.45, .25, .35), "concentrating": (0, 0, 0),
           "confused": (-.2, .35, -.25), "irritated": (-.28, .17, .04), "surprised": (.4, .67, -.13),
           "vulnerable": (-.3, .1, -.55)}
HOME = (-0.1, -0.15, 0.3)   # dry, slightly disdainful


class StandIn:
    """Not the engine: the same methods as orchestrator.Engine and a face that moves, for
    building and testing the page before the real one exists. It steps when asked for a
    snapshot, so it needs no thread."""

    def __init__(self, writer=None, hz=50, log=None):
        self.lock = threading.Lock()
        self.talk_level = 0.0
        self._state, self._target, self.mood = "idle", None, list(HOME)
        self.weights = {t: 0.0 for t in TAGS}
        self.fired = {t: -9.0 for t in TAGS}
        self.joints = rest_joints()
        self.t = time.monotonic()
        self.next_blink, self.blink_until = self.t + 2, 0.0
        self.next_saccade, self.look = self.t + 1, (0.0, 0.0)
        self.flinch_until = 0.0

    def start(self):
        return self

    def stop(self):
        pass

    def state(self, name):
        with self.lock:
            self._state = name

    def tag(self, name, at=None, intensity=None):
        if name in TAGS:
            with self.lock:
                self.weights[name] = min(1.0, max(self.weights[name], 1.0 if intensity is None else intensity))
                self.fired[name] = time.monotonic()

    def vision(self, state):
        people = [p for p in (state or {}).get("people", []) if p.get("engaged", True)]
        with self.lock:
            self._target = (people[0]["yaw"], people[0]["pitch"]) if people else None

    def event(self, name):
        with self.lock:
            if name in ("blink", "long_blink", "interrupted"):
                self.blink_until = time.monotonic() + (0.6 if name == "long_blink" else 0.15)
            if name in ("flinch", "interrupted"):
                self.flinch_until = time.monotonic() + 0.35

    def _step(self, now):
        dt, self.t = min(0.2, now - self.t), now
        for tag in TAGS:   # hold 1.5 s, then fade
            if now - self.fired[tag] > 1.5:
                self.weights[tag] *= math.exp(-dt / 2.0)
        goal = rest_joints()
        for tag, w in self.weights.items():
            for k, v in RECIPES[tag].items():
                keys = [k + "_L", k + "_R"] if k in ("lid_top", "lid_bot") else [k]
                for key in keys:
                    goal[key] += w * v
        if now < self.flinch_until:
            for b in channels.BROWS:
                goal[b] -= 0.7
        if now >= self.next_saccade:
            self.look = (random.uniform(-.5, .5), random.uniform(-.3, .3))
            self.next_saccade = now + random.uniform(0.6, 2.5)
        if self._target:
            gx, gy = self._target[0] / 30 + self.look[0] * 0.1, self._target[1] / 15 + self.look[1] * 0.1
        else:
            gx, gy = self.look
        goal["gaze_x"] += gx
        goal["gaze_y"] += gy
        if now >= self.next_blink:
            self.blink_until, self.next_blink = now + 0.15, now + random.uniform(2.0, 5.0)
        k = 1 - math.exp(-dt * (6 + 6 * max(0.0, self.mood[1])))
        for name in JOINTS:
            fast = name.startswith("gaze")   # saccades jump
            self.joints[name] = clamp(name, goal[name] if fast else self.joints[name] + k * (goal[name] - self.joints[name]))
        if now < self.blink_until:
            self.joints["lid_top_L"] = self.joints["lid_top_R"] = 0.0
        total = sum(self.weights.values())
        pull = [sum(w * ANCHORS[t][i] for t, w in self.weights.items()) for i in range(3)]
        for i in range(3):
            aim = HOME[i] + (pull[i] / total - HOME[i]) * min(1.0, total) if total > 0.01 else HOME[i]
            self.mood[i] += (aim - self.mood[i]) * (1 - math.exp(-dt / 1.5))

    def snapshot(self):
        with self.lock:
            now = time.monotonic()
            self._step(now)
            face = rest_face()
            face.update({k: self.joints[k] for k in channels.BROWS + ("smile", "smile_asym", "jaw_floor")})
            face.update(weights=dict(self.weights), valence=self.mood[0], arousal=self.mood[1],
                        dominance=self.mood[2])
            return dict(t=now, state=self._state, joints=dict(self.joints), face=face,
                        mood=tuple(self.mood), cue=dict(target=self._target, talk=self.talk_level),
                        stand_in=True)


# ----- the fake voice and the visitor -----

class Preview:
    """What the page adds to the engine: the fake voice (50 Hz) and the visitor's position,
    sent as an eyes.Eyes.state-shaped dict (10 Hz) while one is set."""

    def __init__(self, engine):
        self.engine = engine
        self.talking, self.level, self.target = False, 0.0, None
        self.hook = "engine.talk(level)" if callable(getattr(engine, "talk", None)) else "engine.talk_level"
        self.running = True
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()

    def stop(self):
        self.running = False

    def talk(self, on):
        self.talking = bool(on)

    def aim(self, yaw=None, pitch=None):
        """The visitor at (yaw, pitch) degrees, or nobody (None)."""
        self.target = None if yaw is None else (float(yaw), float(pitch))
        self._send_vision()

    def _voice(self, level):
        self.level = level
        if callable(getattr(self.engine, "talk", None)):
            self.hook = "engine.talk(level)"
            self.engine.talk(level)
        else:
            self.hook = "engine.talk_level"
            self.engine.talk_level = level

    def _send_vision(self):
        people = []
        if self.target:
            yaw, pitch = self.target
            people.append(dict(id=1, engaged=True, level="stranger", stranger=True, figure=False, name=None,
                               score=0.0, dist=1.2, yaw=round(yaw, 1), pitch=round(pitch, 1),
                               place="left" if yaw > 10 else "right" if yaw < -10 else "centre",
                               talking=False, mouth=None))
        state = dict(t=time.monotonic(), moving=False, settling=False, background=0.0,
                     people_share=1.0 if people else 0.0, blind=False, session=None, far=False,
                     people=people, enrolling=None)
        try:
            self.engine.vision(state)
        except Exception as e:
            print(f"(engine.vision: {type(e).__name__}: {e})")

    def _run(self):
        syllable_end, syllable_len, amp, left_in_phrase, pause_until = 0.0, 0.2, 0.0, 0, 0.0
        last_vision, was_talking = 0.0, False
        while self.running:
            now = time.monotonic()
            if self.talking:
                if now >= syllable_end and now >= pause_until:
                    if left_in_phrase <= 0:
                        left_in_phrase = random.randint(4, 10)
                        pause_until = now + (random.uniform(0.25, 0.7) if was_talking else 0.0)
                    if now >= pause_until:
                        syllable_len = random.uniform(0.12, 0.28)
                        syllable_end, amp = now + syllable_len, random.uniform(0.45, 1.0)
                        left_in_phrase -= 1
                if now < syllable_end:
                    u = 1 - (syllable_end - now) / syllable_len
                    level = amp * math.sin(math.pi * min(1.0, max(0.0, u))) ** 0.7
                else:
                    level = 0.0
                self._voice(round(level, 3))
                was_talking = True
            elif was_talking:
                self._voice(0.0)
                was_talking, left_in_phrase = False, 0
            if self.target and now - last_vision >= 0.1:
                last_vision = now
                self._send_vision()
            time.sleep(0.02)


# ----- the page -----

def clean(x):
    """JSON-safe and short: floats rounded, NaN and infinity as null, tuples as lists."""
    if isinstance(x, float):
        return round(x, 4) if math.isfinite(x) else None
    if isinstance(x, dict):
        return {str(k): clean(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [clean(v) for v in x]
    return x


def handler(engine, preview, info):
    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"   # keep-alive: the page asks 30 times a second

        def log_message(self, *args):  # the terminal stays quiet
            pass

        def _local(self):
            host = (self.headers.get("Host") or "").rsplit(":", 1)[0]
            return host in HOSTS

        def _send(self, code, body, kind):
            self.send_response(code)
            self.send_header("Content-Type", kind)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def _json(self, data, code=200):
            self._send(code, json.dumps(clean(data), ensure_ascii=False, default=str).encode(), "application/json")

        def do_GET(self):
            if not self._local():
                return self._send(403, b"local only", "text/plain")
            path = self.path.split("?")[0]
            if path in FILES:
                file, kind = FILES[path]
                self._send(200, file.read_bytes(), kind)
            elif path == "/snapshot":
                try:
                    snap = dict(engine.snapshot() or {})
                except Exception as e:
                    return self._json(dict(ok=False, why=f"{type(e).__name__}: {e}"), 500)
                snap["preview"] = dict(talk=preview.level, talking=preview.talking, target=preview.target,
                                       hook=preview.hook)
                self._json(snap)
            elif path == "/meta":
                self._json(dict(info, talk_hook=preview.hook))
            else:
                self._send(404, b"not found", "text/plain")

        def do_POST(self):
            if not self._local() or self.headers.get("X-Frank") != "1":
                return self._send(403, b"local page only", "text/plain")
            try:
                body = json.loads(self.rfile.read(int(self.headers.get("Content-Length") or 0)) or b"{}")
                if not isinstance(body, dict):
                    raise ValueError
            except ValueError:
                return self._json(dict(ok=False, why="bad request"), 400)
            name = str(body.get("name", "")).strip()
            try:
                if self.path == "/tag":
                    if name not in TAGS:
                        return self._json(dict(ok=False, why=f"unknown tag {name!r}"), 400)
                    level = body.get("intensity")
                    engine.tag(name, intensity=None if level is None else max(0.0, min(1.0, float(level))))
                elif self.path == "/state":
                    if name not in STATES:
                        return self._json(dict(ok=False, why=f"unknown state {name!r}"), 400)
                    engine.state(name)
                elif self.path == "/event":
                    if not NAME.match(name):
                        return self._json(dict(ok=False, why="an event name, a-z and _"), 400)
                    engine.event(name)
                elif self.path == "/target":
                    if body.get("clear"):
                        preview.aim(None)
                    else:
                        yaw, pitch = float(body["yaw"]), float(body["pitch"])
                        if not (math.isfinite(yaw) and math.isfinite(pitch)):
                            raise ValueError("not a number")
                        preview.aim(max(-90.0, min(90.0, yaw)), max(-60.0, min(60.0, pitch)))
                elif self.path == "/talk":
                    preview.talk(body.get("on"))
                else:
                    return self._send(404, b"not found", "text/plain")
            except (KeyError, TypeError, ValueError) as e:
                return self._json(dict(ok=False, why=f"bad request: {e}"), 400)
            except Exception as e:   # the engine's own trouble: say it, keep serving
                return self._json(dict(ok=False, why=f"{type(e).__name__}: {e}"), 500)
            self._json(dict(ok=True))

    return Handler


def serve(engine, port=8820, head=None):
    """Start the page for this engine in a thread: (server, preview). server.server_address[1]
    is the port (0 picks a free one)."""
    preview = Preview(engine)
    info = dict(tags=TAGS, states=STATES, events=EVENTS, engine_events=ENGINE_EVENTS,
                joints={k: dict(low=v[0], high=v[1], rest=v[2]) for k, v in JOINTS.items()},
                engine="stand-in" if isinstance(engine, StandIn) else type(engine).__name__,
                head=head)
    server = ThreadingHTTPServer(("127.0.0.1", port), handler(engine, preview, info))
    server.daemon_threads = True
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server, preview


def load_engine(force_stand_in=False):
    if not force_stand_in:
        try:
            from engine import Engine
            return Engine
        except Exception as e:   # being written in parallel: half a file is a SyntaxError, not an ImportError
            print(f"(the engine didn't import, so the stand-in: {type(e).__name__}: {e})")
    return StandIn


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="Frank's face engine, live in the browser")
    ap.add_argument("--port", type=int, default=8820)
    ap.add_argument("--head", nargs="?", const="auto", default=None, metavar="PORT",
                    help="drive the real head through the mouth board (auto, or its serial port)")
    ap.add_argument("--stand-in", action="store_true", help="the stand-in engine even if the real one imports")
    args = ap.parse_args()

    writer = None
    if args.head:
        import mouth
        writer = mouth.Mouth(args.head)
        print(f"Head: mouth board on {writer.port} ({writer.program}).")
    Engine = load_engine(args.stand_in)
    engine = Engine(writer=writer)
    engine.start()
    server, preview = serve(engine, args.port, writer.port if writer else None)
    kind = "the stand-in engine" if isinstance(engine, StandIn) else "the engine"
    print(f"\nFrank's face ({kind}, {'the head on' if writer else 'no servos'}) is at "
          f"http://localhost:{server.server_address[1]}  (Ctrl+C here to stop)\n"
          f"Talk feeds his voice through {preview.hook}.")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        preview.stop()
        engine.stop()
        if writer:
            writer.close()
        server.shutdown()


if __name__ == "__main__":
    main()

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
import socket
import sys
import threading
import time
from pathlib import Path
from urllib.parse import urlparse

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


class Head:
    """The real head, through perform/body.py's socket (body.py owns the USB port; never open the
    board here). Every whole line the studio's mouth writes goes there too, each servo angle first
    clamped to its soft limits: `set NAME deg` (mouth board) and `e PIN deg` (eye board). `jaw f`
    stays inside the board program's own jaw limits. Reconnects every 2 s while body.py is away."""

    def __init__(self, url, robot):
        u = urlparse(url)
        if u.scheme != "socket" or not u.port:
            raise ValueError("--head takes perform/body.py's socket, e.g. socket://127.0.0.1:8811")
        self.addr, self.url, self.robot = (u.hostname or "127.0.0.1", u.port), url, robot
        self.sock, self.lines, self.error, self.buf = None, 0, None, b""
        self.lock = threading.Lock()
        threading.Thread(target=self._keep, name="studio-head", daemon=True).start()

    def _keep(self):
        while True:
            if self.sock is None:
                try:
                    s = socket.create_connection(self.addr, timeout=2)
                    s.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
                    s.settimeout(None)
                    with self.lock:
                        self.sock, self.error = s, None
                    self._send_raw(f"speed {B.M.GLIDE}\nrest\n".encode())   # as mouth.Mouth starts
                except OSError as e:
                    self.error = f"body.py not reachable at {self.url}: {e}"
            if self.sock is not None:
                try:
                    if not self.sock.recv(4096):   # the board's replies: not needed, just drained
                        raise OSError("closed")
                    continue
                except OSError as e:
                    with self.lock:
                        self.sock, self.error = None, f"lost body.py: {e}"
            time.sleep(2.0)

    def _send_raw(self, data):
        with self.lock:
            if self.sock is None:
                return
            try:
                self.sock.sendall(data)
            except OSError as e:
                self.sock, self.error = None, f"lost body.py: {e}"

    def clamp(self, text):
        w = text.split()
        try:
            if len(w) == 3 and w[0] == "set" and w[1] in self.robot.soft:
                lo, hi = self.robot.soft[w[1]]
                return f"set {w[1]} {min(max(float(w[2]), lo), hi):g}"
            if len(w) == 3 and w[0] == "e" and w[2] != "off":
                sid = self.robot.by_pin.get(("eyes", int(w[1])))
                if sid:
                    lo, hi = self.robot.soft[sid]
                    return f"e {w[1]} {min(max(float(w[2]), lo), hi):g}"
        except ValueError:
            pass
        return text

    def write(self, data):
        """The mouth's bytes: control characters as they are, lines clamped."""
        self.buf += data
        out = b""
        while b"\n" in self.buf:
            line, self.buf = self.buf.split(b"\n", 1)
            text = line.decode("utf-8", "replace").strip()
            if text:
                out += (self.clamp(text) + "\n").encode()
                self.lines += 1
        if out:
            self._send_raw(out)

    def servo(self, sid, deg):
        """A try slider on the real head: one servo straight to an angle."""
        s = self.robot.servos[sid]
        line = f"e {s['pin']} {deg:g}" if s["board"] == "eyes" else f"set {sid} {deg:g}"
        self.write((line + "\n").encode())

    def status(self):
        return {"url": self.url, "connected": self.sock is not None, "lines": self.lines, "error": self.error}


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
        self.head = None                     # Head, when --head drives the real one
        rig = self.engine.rig
        apply = rig.apply

        def held_apply(joints, t=None):      # a held channel overrides the animator's output
            return apply({**joints, **self.channel_hold} if self.channel_hold else joints, t)
        rig.apply = held_apply

    @property
    def player(self):
        return self.api.player

    def connect_head(self, url):
        """Also drive the real head through perform/body.py: every line the mouth writes to the
        board models goes to body.py's socket too (clamped), so the head and the twin move together."""
        self.head = Head(url, self.robot)
        wire, head = self.B.jaw.ser, self.head
        feed = wire.write

        def write(data):
            feed(data)
            head.write(data)
        wire.write = write
        return self.head

    def start(self):
        if not self.running:
            self.running = True
            threading.Thread(target=self._run, name="studio-ticker", daemon=True).start()
        return self

    def stop(self):
        self.running = False

    def step(self):
        """One tick: the voice, the mouth, the player, the engine, the boards, then the hooks.
        The ticker calls it here; in the browser (studio/online) the page does, 50 times a second."""
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

    def _run(self):
        period = 1.0 / HZ
        nxt = time.monotonic()
        while self.running:
            self.step()
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

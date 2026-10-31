"""
Frank's face engine in a browser tab (frank/online). The page is frank/engine/preview.html,
unchanged; browser.js answers its requests from this module instead of preview.py's server,
through preview.Api, so every route preview.py answers works here too. Pyodide runs this file
and the real engine. A page has no threads, so browser.js calls tick() 50 times a second,
which does what preview.Preview's thread, mouth.Mouth's thread and Engine._run do.

The engine drives a mouth.Mouth (Jaw below) whose serial lines go into perform/body.py's
board models, as `preview.py --head socket://127.0.0.1:8811` with `body.py --sim` does on the
laptop; the 3D twin (twin.js) reads those models' frames from body_frame().

The engine is statechart.bridge.ChartedEngine: a chart decides his states. The statechart
editor's /api calls (editor.html in the State machine tab) go to statechart.api.handle with its
FileStore on Pyodide's file system, so a chart saved in the editor reaches the face the way a
save on disk does (ChartedEngine reloads it within a second), and the face follows the chart
saved last. browser.js keeps each visitor's saves in their own browser (localStorage) and copies
them into SAVED before this module loads.

Prompt to animation: writing a performance needs a key, so Api runs online (/animate 501);
the page's example prompts play the hand-written timelines in performances.json instead,
through /play and a Performer (animate.Player without its thread).

    tick()             step the fake voice, the mouth, the engine and the boards (no return)
    get(path)          a GET, as JSON text: [code, data], or null for a path Api doesn't know
    post(path, body)   a POST, body as JSON text; the same answer
    body_frame()       the boards' servos, as body.py's /events sends them, JSON text
    editor(method, path, body)   the editor's /api calls, as JSON text: [code, data]
"""

import json
import math
import os
import random
import re
import sys
import threading
import time
from collections import deque
from pathlib import Path

FRANK = Path(__file__).resolve().parent.parent
ROOT = FRANK.parent
CHARTS = FRANK / "statechart" / "charts"
SAVED = ROOT / "saved_charts"   # the visitor's own saved charts, from localStorage (browser.js)
CHART_NAME = re.compile(r"^[A-Za-z0-9_-]{1,60}$")
PERFORMANCES = Path(__file__).resolve().parent / "performances.json"
sys.path[:0] = [str(FRANK), str(FRANK / "engine"), str(ROOT / "perform")]
import body as BODY  # noqa: E402   (its Robot: the board models; no server starts here)
import mouth as M  # noqa: E402
import preview as P  # noqa: E402   (its Api and helpers: its server never starts here)
from engine import animate as A  # noqa: E402

try:
    import js   # Pyodide: the page's globals
except ImportError:
    js = None


class Voice(P.Preview):
    """preview.Preview's fake voice and visitor, stepped by tick() instead of its own thread.
    Its syllables also go to the mouth (jaw), as the voice player's feed() would."""

    def __init__(self, engine):
        self.engine = engine
        self.talking, self.level, self.target = False, 0.0, None
        self.hook = "engine.talk(level)" if callable(getattr(engine, "talk", None)) else "engine.talk_level"
        self.running = False
        self.syllable_end, self.syllable_len, self.amp, self.bright = 0.0, 0.2, 0.0, 0.5
        self.left_in_phrase, self.pause_until = 0, 0.0
        self.last_vision, self.was_talking = 0.0, False
        self.jaw = None

    def _voice(self, level):
        super()._voice(level)
        if self.jaw and level > 0:
            self.jaw.hear(level, self.bright)

    def step(self, now):
        """One pass of Preview._run's loop."""
        if self.talking:
            if now >= self.syllable_end and now >= self.pause_until:
                if self.left_in_phrase <= 0:
                    self.left_in_phrase = random.randint(4, 10)
                    self.pause_until = now + (random.uniform(0.25, 0.7) if self.was_talking else 0.0)
                if now >= self.pause_until:
                    self.syllable_len = random.uniform(0.12, 0.28)
                    self.syllable_end, self.amp = now + self.syllable_len, random.uniform(0.45, 1.0)
                    self.bright = random.random()   # the vowel: dark OO .. bright EE
                    self.left_in_phrase -= 1
            if now < self.syllable_end:
                u = 1 - (self.syllable_end - now) / self.syllable_len
                level = self.amp * math.sin(math.pi * min(1.0, max(0.0, u))) ** 0.7
            else:
                level = 0.0
            self._voice(round(level, 3))
            self.was_talking = True
        elif self.was_talking:
            self._voice(0.0)
            self.was_talking, self.left_in_phrase = False, 0
        if self.target and now - self.last_vision >= 0.1:
            self.last_vision = now
            self._send_vision()


class Wire:
    """The serial port mouth.Mouth writes to, joined to body.py's board models: each whole line
    goes to the mouth board (which passes "e ..." lines on to the eye board)."""
    in_waiting = 0

    def __init__(self, robot, board="mouth"):
        self.robot, self.board, self.buf = robot, board, b""

    def write(self, data):
        self.buf += data
        while b"\n" in self.buf:
            line, self.buf = self.buf.split(b"\n", 1)
            text = line.decode("utf-8", "replace").strip()
            if text:
                self.robot.feed(self.board, text)

    def read(self, n=1):
        return b""

    def reset_input_buffer(self):
        pass

    def close(self):
        pass


class Jaw(M.Mouth):
    """mouth.Mouth for the twin: the board program is cogley_mouth_main.py, its lines go down a
    Wire, and step() is one pass of its thread's loop."""

    def __init__(self, robot):   # Mouth.__init__ without the port search, the waits and the thread
        self.port, self.program, self.cogley = "twin", "cogley_mouth_main.py", True
        self.log = lambda **k: None
        self.poses = {k: dict(v) for k, v in M.POSES.items()}
        self.vowels = {}
        if os.path.exists(M.POSES_FILE):
            with open(M.POSES_FILE) as f:
                saved = json.load(f)
            for k, v in saved.items():
                if k in self.poses:
                    self.poses[k].update(v)
            if all(k in saved for k in ("vowel_ah", "vowel_ee", "vowel_oo")):
                self.vowels = {k: dict(saved[k]) for k in ("vowel_ah", "vowel_ee", "vowel_oo")}
        self.ser = Wire(robot)
        self.lock = threading.Lock()
        self.levels, self.last_audio = deque(), 0.0
        self.open = self.lips = self.width = self.bright = self.mood = self.mood_target = 0.0
        self.asym = self.jaw_floor = 0.0
        self.engine, self.tongue_until, self.closed, self.gaze = False, 0.0, False, None
        self.target, self.ticks = 0.0, 0
        self.ser.write(f"speed {M.GLIDE}\n".encode())
        self.ser.write(b"rest\n")
        self.sent = {"jaw": 0.0}
        for socket, a in self.poses["lips_rest"].items():   # `rest` leaves the lips unpowered
            self.send(socket, a)
            self.sent[socket] = a
        self.awake = True

    def hear(self, frac, bright):
        """feed() without the PCM: how open (0..1) and how bright (0..1) the sound is now."""
        t = time.monotonic()
        self.levels.append((t + M.DELAY, frac, bright))
        self.last_audio = t

    def step(self, t):
        """One pass of Mouth._run's loop (its TICK, 20 ms: tick() runs at 50 Hz)."""
        while self.levels and self.levels[0][0] <= t:
            _, self.target, bright = self.levels.popleft()
            if self.target > 0.3:
                self.bright = bright
        if t - self.last_audio > M.HOLD + M.DELAY:
            self.target = 0.0
        k = M.TICK / (M.ATTACK if self.target > self.open else M.RELEASE)
        self.open += (self.target - self.open) * min(1.0, k)
        if self.open < 0.005:
            self.open = 0.0
        k = M.TICK / (M.LIP_ATTACK if self.target > self.lips else M.LIP_RELEASE)
        self.lips += (self.target - self.lips) * min(1.0, k)
        width_target = self.bright if self.target > 0.15 else self.width * 0.5
        self.width += (width_target - self.width) * min(1.0, M.TICK / M.WIDTH_SMOOTH)
        self.mood += (self.mood_target - self.mood) * min(1.0, M.TICK / M.MOOD_SMOOTH)
        self.ticks += 1
        self._jaw(max(self.open * M.MAX_OPEN, self.jaw_floor))
        if self.ticks % 2 == 0:
            self._lips(t)


class Performer(A.Player):
    """animate.Player stepped by tick() instead of its own thread: play() sets the tags on the
    engine's clock as Player._run does, step() is one pass of its loop, stop() its ending."""

    def play(self, anim):
        self.stop()
        self.anim = A.clean(anim)
        self.t0, self.playing, self.steered = time.monotonic(), True, False
        keys = self.anim["keys"]
        for k in keys:   # tags at their own times, through the engine's clock (its dwell rules apply)
            if k["kind"] == "tag":
                self.engine.tag(k["tag"], at=self.t0 + k["t"], intensity=k["intensity"])
        self.feels = [k for k in keys if k["kind"] == "feel"]
        self.pending = [k for k in keys if k["kind"] in ("event", "look")]
        return self

    def step(self, now):
        if not self.playing:
            return
        e, t = self.engine, now - self.t0
        while self.pending and self.pending[0]["t"] <= t:
            k = self.pending.pop(0)
            if k["kind"] == "event":
                e.event(k["event"])
            else:
                e.look_at(k["yaw"], k["pitch"], hold=self.anim["duration"] - k["t"] + 0.5)
        point = A.glide(self.feels, t)
        if point is not None:
            e.steer(*point, tags=True)
            self.steered = True
        if t >= self.anim["duration"]:
            self.stop()

    def stop(self):
        if self.playing:
            if self.steered:
                self.engine.release()
            self.engine.look_at(None)
        self.playing = False


def prompt_key(prompt):
    return " ".join(str(prompt or "").lower().split()).rstrip(".!?")


def make_engine(writer):
    """ChartedEngine on charts/frank.json (the visitor's saved one if any; Frank's own if that
    one can't run), or the engine with its own states if the statechart package doesn't load."""
    seeds = {p.name: p.read_text(encoding="utf-8") for p in CHARTS.glob("*.json")}
    for p in SAVED.glob("*.json") if SAVED.is_dir() else ():
        if CHART_NAME.match(p.stem):
            (CHARTS / p.name).write_text(p.read_text(encoding="utf-8"), encoding="utf-8")
    try:
        from statechart.bridge import ChartedEngine
    except Exception as e:   # being written in parallel: the engine's own states
        print(f"(statechart didn't import, so the engine's own states: {type(e).__name__}: {e})")
        return P.load_engine()(writer=writer)
    try:
        return ChartedEngine(writer=writer)
    except Exception as e:
        print(f"(the saved frank chart can't run, so Frank's own: {type(e).__name__}: {e})")
        for name, text in seeds.items():
            (CHARTS / name).write_text(text, encoding="utf-8")
        return ChartedEngine(writer=writer)


def chart_store():
    """statechart.api's FileStore on charts/; a save also points the face at that chart (it
    runs it from ChartedEngine's next reload) and keeps it in the visitor's browser."""
    class Store(SA.FileStore):
        def put(self, name, text):
            super().put(name, text)
            if hasattr(engine, "chart_path"):
                engine.chart_path, engine.chart_mtime, engine.watch_file = self._path(name), None, True
            keep = getattr(js, "frankSaveChart", None) if js else None
            if keep:
                keep(name, text)
    return Store(str(CHARTS))


robot = BODY.Robot(ROOT / "robots" / "frank" / "robot.json")
jaw = Jaw(robot)
engine = make_engine(jaw)
try:
    import statechart.api as SA
    SA.ONLINE = True   # Asking Claude needs a key: off here
    store, SA_ERROR = chart_store(), None
except Exception as e:
    SA, store, SA_ERROR = None, None, f"{type(e).__name__}: {e}"
P.Preview = Voice   # Api makes its Preview by this name: the thread-free one here
api = P.Api(engine, head="the 3D twin")
api.info["online"] = True   # /animate: 501, it needs a key
if hasattr(engine, "steer"):
    api.player = Performer(engine)   # Api plays /play on this one instead of a threaded Player
CANNED = {prompt_key(k): v for k, v in json.loads(PERFORMANCES.read_text(encoding="utf-8"))["performances"].items()}
voice = api.preview
voice.jaw = jaw
last = time.monotonic()


def tick():
    global last
    now = time.monotonic()
    voice.step(now)
    jaw.step(now)
    if isinstance(api.player, Performer):
        api.player.step(now)
    if hasattr(engine, "_tick"):   # the stand-in steps inside snapshot() instead
        try:
            engine._tick(now)
            engine.error = None
        except Exception as e:   # as Engine._run: the face never stops for a bug
            engine.error = str(e)
    robot.tick(min(0.2, now - last))
    last = now


def body_frame():
    f = robot.frame()
    f.update(kind="frame", lines=[], ports={"mouth": {"device": "simulated", "programs": 1}})
    return json.dumps(f)


def _answer(result):
    return json.dumps(None if result is None else [result[0], P.clean(result[1])], ensure_ascii=False, default=str)


def get(path):
    return _answer(api.get(path))


def post(path, body):
    try:
        body = json.loads(body or "{}")
        if not isinstance(body, dict):
            raise ValueError
    except ValueError:
        return _answer((400, dict(ok=False, why="bad request")))
    if path == "/animate":   # the examples play their pre-written performance; anything else needs a key
        anim = CANNED.get(prompt_key(body.get("prompt")))
        if anim is None:
            return _answer((501, dict(ok=False, why="not available online: a new performance needs a key, "
                                                    "so it is written on the laptop. Try the examples.")))
        return _answer(api.post("/play", {"anim": anim}))
    return _answer(api.post(path, body))


def editor(method, path, body):
    if SA is None:
        return json.dumps([503, {"error": f"the editor's back end didn't load: {SA_ERROR}"}])
    try:
        body = json.loads(body) if body else None
    except ValueError:
        return json.dumps([400, {"error": "bad request"}])
    try:
        status, data = SA.handle(method, path, body, store)
    except Exception as e:   # its own trouble: say it, keep the face going
        status, data = 500, {"error": f"{type(e).__name__}: {e}"}
    return json.dumps([status, data], ensure_ascii=False, default=str)

"""
Frank's face engine in a browser tab (frank/online). The page is frank/engine/preview.html,
unchanged; browser.js answers its requests from this module instead of preview.py's server,
through preview.Api, so every route preview.py answers works here too. Pyodide runs this file
and the real engine. A page has no threads, so browser.js calls tick() 50 times a second,
which does what preview.Preview's thread and Engine._run do.

    tick()             step the fake voice, the visitor and the engine (no return)
    get(path)          a GET, as JSON text: [code, data], or null for a path Api doesn't know
    post(path, body)   a POST, body as JSON text; the same answer
"""

import json
import math
import random
import sys
import time
from pathlib import Path

FRANK = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(FRANK), str(FRANK / "engine")]
import preview as P  # noqa: E402   (its Api and helpers: its server never starts here)


class Voice(P.Preview):
    """preview.Preview's fake voice and visitor, stepped by tick() instead of its own thread."""

    def __init__(self, engine):
        self.engine = engine
        self.talking, self.level, self.target = False, 0.0, None
        self.hook = "engine.talk(level)" if callable(getattr(engine, "talk", None)) else "engine.talk_level"
        self.running = False
        self.syllable_end, self.syllable_len, self.amp = 0.0, 0.2, 0.0
        self.left_in_phrase, self.pause_until = 0, 0.0
        self.last_vision, self.was_talking = 0.0, False

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


engine = P.load_engine()(writer=None)
P.Preview = Voice   # Api makes its Preview by this name: the thread-free one here
api = P.Api(engine)
voice = api.preview


def tick():
    now = time.monotonic()
    voice.step(now)
    if hasattr(engine, "_tick"):   # the stand-in steps inside snapshot() instead
        try:
            engine._tick(now)
            engine.error = None
        except Exception as e:   # as Engine._run: the face never stops for a bug
            engine.error = str(e)


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
    return _answer(api.post(path, body))

"""
The orchestrator: Frank's stage manager (docs/FACE_ENGINE.md).

One thread, 50 times a second: it works out what is happening (idle, someone arrived, the
visitor talking, Frank thinking, speaking, cut off, someone leaving), fires each expression
tag when its words reach the speaker, picks who to look at from the vision, and passes the
synthesiser's face and its own cue to the animator, whose joints the rig sends to the servos.

It plugs into the chat program three ways:
- the voice player's mouth hook: `voice.mouth = engine`. The player calls feed() with every
  20 ms slice it plays (passed on to the real mouth.Mouth, the jaw and lips) and face() as each
  tagged stretch of words starts playing (voice.py, `faces`), so tags land on the audio clock;
- `chat.listeners.append(engine.on_ui)`: the chat loop's events (hearing, visitor, frank_start,
  face, say, frank_end, interrupted, seen, new) set the state;
- `engine.watch(lambda: chat.eyes.state)`: the vision snapshot (5 Hz) gives the gaze target.

    engine = Engine(writer=mouth.Mouth("auto")).start()   # or writer=None: preview only
    engine.tag("curious"); engine.state("listening"); engine.snapshot()
"""

import random
import threading
import time
from collections import deque

from . import channels
from .animator import Animator
from .rig import Rig
from .synth import Synth

HZ = 50
MIN_DWELL = 1.2        # s a tag holds before a different one replaces it (surprised may cut in)
CUT_IN = {"surprised"}
PREVIEW = 0.3          # intensity of the reply's first tag shown while he is still thinking
OPENING = 0.1          # extra intensity for the first tag of a reply
SILENT_HOLD = 2.2      # s a tag-only reply holds the gaze on the speaker before he looks about
SPEAKING_GAP = 0.45    # s without a voice slice after which he is no longer speaking
INTERRUPTED_S = 0.6    # s of the interrupted state before listening again
GREETING_S = 1.8       # s of the greeting state after an arrival
FAREWELL_S = 2.5       # s of the farewell state after the last person leaves
TARGET_HOLD = 0.4      # s a new choice of whom to look at must persist before the eyes switch
GLANCE_EVERY = (6.0, 14.0)  # s between glances at someone other than the one he is engaged with
GLANCE_S = (0.6, 1.2)  # s a glance lasts
TALK_HOLD = 0.3        # s a preview talk() level counts as his voice
IN_CONVERSATION = ("greeting", "listening", "thinking", "speaking", "interrupted")


class EyeHold:
    """The engine's stand-in for gaze.Gaze, so chat.py's /eyes and the page's Pause eyes / Eyes
    alive buttons work the same with the engine: pause() holds the eyes centred with the lids at
    their OPEN pose (photographs, fitting the skin, setting the lids); alive() lets them go."""

    def __init__(self, log):
        self.paused, self.log = False, log

    @property
    def state(self):
        return "paused" if self.paused else "alive"

    def pause(self):
        self.paused = True
        self.log(what="eyes", state="paused")
        return self.state

    def alive(self):
        self.paused = False
        self.log(what="eyes", state="alive")
        return self.state

    def hold(self, joints):
        joints.update(gaze_x=0.0, gaze_y=0.0, lid_top_L=1.0, lid_top_R=1.0, lid_bot_L=1.0, lid_bot_R=1.0)
        return joints


class Engine:
    def __init__(self, writer=None, hz=HZ, log=None, personality=None):
        self.writer = writer  # a mouth.Mouth (the real jaw, lips and corners), or None
        self.hz = hz
        self._log = log or (lambda **k: None)
        self.recent = deque(maxlen=16)  # the engine's last decisions, for the editor's live feed
        self.session = dict(heard="", said="", visitor="", tags=[])  # the conversation, for the editor
        self.vision_at = 0.0           # when vision() was last called by hand (the editor's pad)
        self.synth = Synth(personality)
        self.anim = Animator(personality)
        self.rig = Rig(writer)
        self.gaze = EyeHold(self.log)  # /eyes pause | alive (chat.py), as gaze.Gaze
        self.lock = threading.RLock()
        self.rng = random.Random()
        self.mode, self.mode_since = "idle", time.monotonic()
        self.thinking = False          # the visitor's turn is over and the reply isn't playing yet
        self.until = {}                # timed states: name -> monotonic end
        self.pending = []              # tags to fire: (at, name, intensity)
        self.fired = ("neutral", 0.0)  # the last tag shown and when
        self.reply_tags = []           # tags seen in the current reply's text (ui "face")
        self.reply_started = False
        self.events = []               # one-shot animator events for the next tick
        self.last_feed = 0.0
        self.talk_level, self.talk_at = 0.0, 0.0
        self.look = None               # callable returning eyes.Eyes.state, or None
        self.vision_state = None
        self.target = self.target_id = None
        self.candidate, self.candidate_at = None, 0.0
        self.glance_until, self.next_glance = 0.0, time.monotonic() + self.rng.uniform(*GLANCE_EVERY)
        self.glance_at = None
        self.forced = None             # a state set by hand (state()), until state("auto")
        self.snap = {}
        self.error = None
        self.ticks, self.running = 0, False

    # ----- running -----

    def start(self):
        if self.writer is not None:
            try:
                self.rig.rest()   # one servo at a time (~1.2 s), not all ten on the supply at once
            except Exception as e:
                self.error = f"rest: {e}"
        self.running = True
        threading.Thread(target=self._run, daemon=True, name="face-engine").start()
        return self

    def stop(self):
        self.running = False
        time.sleep(2.0 / self.hz)
        try:
            self.rig.rest()
        except Exception as e:
            self.error = f"rest: {e}"

    def close(self):
        """Stop and close the mouth (chat.py and web.py call this as they would mouth.close())."""
        self.stop()
        if self.writer and hasattr(self.writer, "close"):
            self.writer.close()

    def log(self, **rec):
        self.recent.append(dict(t=round(time.time(), 2), **rec))
        self._log(**rec)

    def __getattr__(self, name):
        """Anything else asked of the mouth (port, program, ...) goes to the real one."""
        writer = self.__dict__.get("writer")
        if writer is None:
            raise AttributeError(name)
        return getattr(writer, name)

    def _run(self):
        period = 1.0 / self.hz
        next_at = time.perf_counter()
        while self.running:
            try:
                self._tick(time.monotonic())
                self.error = None
            except Exception as e:  # the face never stops for a bug: log it and carry on
                if self.error != str(e):
                    self.log(what="engine_error", error=str(e)[:200])
                self.error = str(e)
            self.ticks += 1
            next_at += period
            delay = next_at - time.perf_counter()
            if delay > 0:
                time.sleep(delay)
            else:
                next_at = time.perf_counter()  # fell behind: don't try to catch up

    def _tick(self, t):
        with self.lock:
            self._fire_tags(t)
            state = self._state(t)
            self._watch(t)
            target, others = self._gaze_target(t, state)
            events, self.events = self.events, []
        face = self.synth.step(t)
        cue = {"state": state, "target": target, "others": others, "talk": self._talk(t), "events": events}
        joints = self.anim.step(t, face, cue)
        if self.gaze.paused:
            joints = self.gaze.hold(dict(joints))
        angles = self.rig.apply(joints, t)
        self.snap = dict(t=t, state=state, joints=joints, face=face, angles=angles,
                         mood=self.synth.snapshot().get("mood"), target=target,
                         last_tag=self.fired[0], error=self.error)

    # ----- the public calls -----

    def state(self, name):
        """Set a conversation state by hand (preview, tests): idle, person, greeting, listening,
        thinking, speaking, interrupted, farewell; "auto" hands it back to the events."""
        t = time.monotonic()
        if name == "auto":
            with self.lock:
                self.forced, self.thinking = None, False
            return
        if name not in channels.STATES:
            return
        with self.lock:
            self.until.clear()
            self.thinking = name == "thinking"
            if name in ("interrupted", "greeting", "farewell"):
                self.until[name] = t + {"interrupted": INTERRUPTED_S, "greeting": GREETING_S,
                                        "farewell": FAREWELL_S}[name]
                self.events.append({"interrupted": "flinch", "greeting": "greet",
                                    "farewell": "long_blink"}[name])
            self.forced = name if name not in self.until else None
        self._set_mode(name, t)

    def tag(self, name, at=None, intensity=None):
        """Show an expression at time `at` (monotonic; now if None)."""
        if name not in channels.TAGS:
            return
        t = time.monotonic()
        with self.lock:
            self.pending.append((t if at is None else at, name, intensity))

    def event(self, name):
        """Something happened: arrived, left, moved, still, dark, light, interrupted,
        session_end, or an animator event (blink, long_blink, flinch, greet, beat, phrase_end)."""
        t = time.monotonic()
        with self.lock:
            if name in channels.EVENTS:
                self.events.append(name)
            elif name == "arrived":
                self.synth.nudge(t, p=0.05, a=0.25)
                if self.mode in ("idle", "person", "farewell"):
                    self.until = {"greeting": t + GREETING_S}
                    self.events.append("greet")
                    self.pending.append((t + 0.15, "curious", 0.6))
            elif name in ("left", "session_end"):
                self.synth.nudge(t, a=-0.1)
                people = [p for p in (self.vision_state or {}).get("people", []) if not p.get("figure")]
                if name == "session_end" or not people:
                    self.until = {"farewell": t + FAREWELL_S}
                    self.events.append("long_blink")
            elif name == "moved":
                self.pending += [(t, "surprised", 0.8), (t + 1.6, "irritated", 0.6)]
                self.synth.nudge(t, p=-0.1, a=0.3, d=-0.1)
            elif name == "still":
                self.pending.append((t + 0.3, "curious", 0.5))
            elif name == "dark":
                self.synth.nudge(t, a=-0.3)
                self.pending.append((t + 0.4, "confused", 0.5))
            elif name == "light":
                self.events.append("blink")
            elif name == "interrupted":
                if t < self.until.get("interrupted", 0.0):
                    return   # the voice's flush and the chat's event: one interruption, one flinch
                self.until = {"interrupted": t + INTERRUPTED_S}
                self.thinking = False
                self.events.append("flinch")
                self.synth.nudge(t, p=-0.05, a=0.1)
        self.log(what="engine_event", name=name)

    def talk(self, level):
        """His voice's loudness now, 0..1, when there is no voice player (the preview)."""
        self.talk_level, self.talk_at = max(0.0, min(1.0, float(level))), time.monotonic()
        if self.talk_level > 0.05:
            self.last_feed = self.talk_at

    def watch(self, look):
        """Where to read the vision from: a callable returning eyes.Eyes.state (or None)."""
        self.look = look

    def vision(self, state):
        """Or hand the vision snapshot over directly."""
        with self.lock:
            self.vision_state = state
            self.vision_at = time.monotonic()

    def snapshot(self):
        snap = dict(self.snap)
        vis = self.vision_state or {}
        people = [dict(name=p.get("name"), yaw=p.get("yaw"), pitch=p.get("pitch"), dist=p.get("dist"),
                       engaged=p.get("engaged"), talking=p.get("talking"))
                  for p in vis.get("people", []) if not p.get("figure")]
        snap["session"] = dict(self.session, people=people, seeing=self.look is not None and self.vision_state is not None,
                               recent=list(self.recent), tags=list(self.session["tags"])[-8:])
        return snap

    # ----- the voice player's mouth hook (voice.mouth = engine) -----

    def feed(self, pcm):
        self.last_feed = time.monotonic()
        with self.lock:
            self.thinking = False
        if self.writer:
            self.writer.feed(pcm)

    def face(self, name):
        """A tagged stretch of his words starts playing now."""
        if name:
            intensity = None
            if not self.reply_started:
                self.reply_started = True
                intensity = OPENING
            self.tag(name, intensity=None if intensity is None else self._base(name) + intensity)
        if self.writer and hasattr(self.writer, "face"):
            self.writer.face(name)  # ignored by the mouth once the engine sets its expression

    def flush(self):
        """Cut off: the voice stopped."""
        if self.writer:
            self.writer.flush()
        self.last_feed = 0.0
        self.event("interrupted")

    # ----- the chat loop's events (chat.listeners) -----

    def on_ui(self, ev):
        kind = ev.get("kind")
        t = time.monotonic()
        if kind in ("hearing", "visitor", "say", "frank_start", "face"):
            self._session(kind, ev)
        if kind == "hearing":
            with self.lock:
                if not self.thinking and not self._speaking(t):
                    self.until.pop("greeting", None)
        elif kind == "visitor":  # their line is complete: he thinks
            with self.lock:
                self.thinking, self.reply_tags, self.reply_started = True, [], False
                self.until.pop("greeting", None)
        elif kind == "face":  # a tag in his reply's text, ahead of the audio
            name = ev.get("tag")
            if name in channels.TAGS:
                with self.lock:
                    first = not self.reply_tags
                    self.reply_tags.append(name)
                    if first and self.thinking:
                        self.synth.feel(name, t, PREVIEW)
        elif kind == "sound" and ev.get("tag") == "chuckle":
            self.tag("amused", intensity=0.7)
        elif kind == "frank_end":
            with self.lock:
                self.thinking = False
                if ev.get("silent") and self.reply_tags and not ev.get("interrupted"):
                    # a tag-only reply: the face is the reply
                    self.synth.feel(self.reply_tags[-1], t, 1.0)
                    self.until["silent"] = t + SILENT_HOLD
                self.reply_tags, self.reply_started = [], False
        elif kind == "interrupted":
            self.event("interrupted")
        elif kind == "seen":
            what = ev.get("what")
            if what in ("arrived", "left", "moved", "still", "dark", "light", "session_end"):
                self.event(what)
        elif kind == "new":
            with self.lock:
                self.thinking, self.reply_tags = False, []

    # ----- inside the tick -----

    def _base(self, name):
        return 0.8 if name != "neutral" else 0.6

    def _fire_tags(self, t):
        if not self.pending:
            return
        self.pending.sort(key=lambda p: p[0])
        keep = []
        for at, name, intensity in self.pending:
            last, last_at = self.fired
            if at > t:
                keep.append((at, name, intensity))
                continue
            if name != last and name not in CUT_IN and t - last_at < MIN_DWELL:
                keep.append((last_at + MIN_DWELL, name, intensity))  # wait its turn
                continue
            self.synth.feel(name, t, self._base(name) if intensity is None else intensity)
            self.fired = (name, t)
            self.log(what="engine_tag", tag=name, late=round(t - at, 3))
        self.pending = keep

    def _speaking(self, t):
        return t - self.last_feed < SPEAKING_GAP

    def _state(self, t):
        for name in ("interrupted", "greeting", "farewell"):
            end = self.until.get(name)
            if end is not None:
                if t < end:
                    return self._set_mode(name, t)
                del self.until[name]
        forced = self.forced
        if forced:
            if forced == "speaking" and self._speaking(t):
                return self._set_mode("speaking", t)
            if forced != "speaking":
                return self._set_mode(forced, t)
        if self._speaking(t):
            return self._set_mode("speaking", t)
        if self.thinking:
            return self._set_mode("thinking", t)
        vis = self.vision_state or {}
        people = [p for p in vis.get("people", []) if not p.get("figure")]
        if vis.get("session") or any(p.get("engaged") for p in people):
            return self._set_mode("listening", t)
        if people:
            return self._set_mode("person", t)
        if self.vision_state is None and self.mode in IN_CONVERSATION:
            return self._set_mode("listening", t)  # no eyes: assume someone's there once spoken to
        return self._set_mode("idle", t)

    def _set_mode(self, name, t):
        if name != self.mode:
            self.log(what="engine_state", state=name, was=self.mode, held=round(t - self.mode_since, 2))
            self.mode, self.mode_since = name, t
        return name

    def _session(self, kind, ev):
        s = self.session
        if kind == "hearing":
            s["heard"] = ev.get("text", "")
        elif kind == "visitor":
            s["visitor"], s["heard"] = ev.get("said", ""), ""
        elif kind == "frank_start":
            s["said"] = ""
        elif kind == "say":
            s["said"] = (s["said"] + " " + ev.get("text", "")).strip()[-300:]
        elif kind == "face" and ev.get("tag"):
            s["tags"] = (s["tags"] + [ev["tag"]])[-8:]

    def _watch(self, t):
        if self.look is not None:
            try:
                seen = self.look()
            except Exception:
                seen = None
            if seen is not None or t - self.vision_at > 1.0:  # the pad stands in while the camera is off
                self.vision_state = seen

    def _gaze_target(self, t, state):
        """Whom to look at, as (yaw, pitch) degrees, and the others in view. The speaker wins;
        then the engaged person nearest; now and then a glance at someone else."""
        vis = self.vision_state
        if vis is None:  # no eyes running: in a conversation, the visitor is straight ahead
            self.target = (0.0, 0.0) if state in IN_CONVERSATION else None
            return self.target, []
        if vis.get("blind") or vis.get("moving"):
            return None, []
        people = [p for p in vis.get("people", []) if not p.get("figure")]
        if not people:
            self.target = self.target_id = None
            return None, []
        talking = [p for p in people if p.get("talking")]
        engaged = [p for p in people if p.get("engaged")]
        pick = min(talking or engaged or people, key=lambda p: p.get("dist", 9.0))
        if pick.get("id") != self.target_id:
            if self.candidate != pick.get("id"):
                self.candidate, self.candidate_at = pick.get("id"), t
            # the speaker changing, or him starting to talk, switches at once; otherwise wait a moment
            if talking or t - self.candidate_at >= TARGET_HOLD or self.target_id is None:
                self.target_id = pick.get("id")
        current = next((p for p in people if p.get("id") == self.target_id), pick)
        others = [(p["yaw"], p["pitch"]) for p in people if p.get("id") != self.target_id]
        aim = (current["yaw"], current["pitch"])
        if others and state in ("listening", "idle", "person") and not talking:
            if t >= self.next_glance:
                self.glance_at = self.rng.choice(others)
                self.glance_until = t + self.rng.uniform(*GLANCE_S)
                self.next_glance = t + self.rng.uniform(*GLANCE_EVERY)
            if t < self.glance_until and self.glance_at:
                aim = self.glance_at
        self.target = aim
        return aim, others

    def _talk(self, t):
        level = 0.0
        if self.writer is not None and hasattr(self.writer, "open"):
            level = float(getattr(self.writer, "open", 0.0) or 0.0)
        if t - self.talk_at < TALK_HOLD:
            level = max(level, self.talk_level)
        return level

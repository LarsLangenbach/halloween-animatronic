"""
Prompt to face animation: a sentence ("he hears a terrible pun, groans, then can't help
smiling") becomes a short timed performance for Frank's face, written by Claude in the engine's
own vocabulary, and a player runs it on the live engine (so the 3D twin and the head follow).

    anim = animate.generate("he spots a spider on the camera and freezes")   # needs a key
    player = animate.Player(engine).play(anim)                              # runs in a thread

A timeline is {"title", "duration", "keys": [...]}, each key at a time t (s) and of one kind:
    tag    an expression tag (channels.TAGS) at an intensity, as Claude's replies send them
    feel   a point on the emotion map (pleasure p, arousal a, dominance d, each -1..1); the face
           glides between successive feel keys (Engine.steer), so arcs through the map are smooth
    event  blink, long_blink, flinch, greet, beat or phrase_end
    look   where his eyes go: yaw (deg, + his left) and pitch (deg, + up); 0, 0 is straight ahead
When it ends, the face goes back to the conversation (Engine.release).

Generation is laptop-only: it needs ANTHROPIC_API_KEY (frank/.env, as brain.py). The public
site never has a key, so there it answers "not available".
"""

import json
import math
import threading
import time

from . import channels

MODEL = "claude-opus-5-5"   # the animator; low effort keeps it to a few seconds
EFFORT = "low"
MAX_SECONDS = 20.0          # the longest performance
MAX_KEYS = 60
KINDS = ("tag", "feel", "event", "look")
EVENTS = ("blink", "long_blink", "flinch", "greet", "beat", "phrase_end")
LOOK_MAX = (40.0, 25.0)     # deg: yaw and pitch are kept inside this
STEER_HZ = 25.0             # the player's rate while gliding between feel keys

SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["title", "duration", "keys"],
    "properties": {
        "title": {"type": "string"},
        "duration": {"type": "number"},
        "keys": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["t", "kind", "tag", "intensity", "p", "a", "d", "event", "yaw", "pitch"],
                "properties": {
                    "t": {"type": "number"},
                    "kind": {"type": "string", "enum": list(KINDS)},
                    "tag": {"type": "string", "enum": list(channels.TAGS) + [""]},
                    "intensity": {"type": "number"},
                    "p": {"type": "number"},
                    "a": {"type": "number"},
                    "d": {"type": "number"},
                    "event": {"type": "string", "enum": list(EVENTS) + [""]},
                    "yaw": {"type": "number"},
                    "pitch": {"type": "number"},
                },
            },
        },
    },
}


def system_prompt():
    from .synth import STEER_MAP
    places = "\n".join(f"- {tag}: p {p:+.2f}, a {a:+.2f}, d {d:+.2f}" for tag, (p, a, d) in STEER_MAP.items())
    return f"""You animate the face of Frank, a life-size animatronic head: a newly conscious, bioengineered
human head in a jar. He is dry, skeptical and mildly unimpressed by default, curious underneath, slightly
arrogant, and theatrical when genuinely fascinated. His brows are his signature. He has eyes (left/right,
up/down), upper and lower eyelids, four brow ends, and mouth corners; he has no neck.

Turn the director's prompt into a short timed performance of his face, in his character. Write keys, each
at a time t in seconds from the start, each of one kind (fill the fields a kind doesn't use with "" or 0):
- "tag": an expression tag with an intensity 0.3 to 1.0. Tags: {", ".join(channels.TAGS)}.
- "feel": a point on his emotion map: p pleasure (-1 unpleasant .. +1 pleasant), a arousal (-1 calm .. +1
  aroused), d dominance (-1 small .. +1 in control). The face glides smoothly between consecutive feel keys,
  so use a few feel keys to draw an arc of feeling; tags are punctuation on top. The tags sit at:
{places}
- "event": one of {", ".join(EVENTS)} (flinch: a start; greet: a brow flash; beat: a brow beat on a word;
  long_blink: a slow "got it" blink).
- "look": where his eyes go, yaw in degrees (+ his left, - his right, up to 40) and pitch (+ up, up to 25);
  0, 0 is straight at the visitor. Thinking looks go up and to one side.

Timing: a performance lasts 3 to {int(MAX_SECONDS)} seconds (duration), with keys every 0.3 to 2 seconds,
at most {MAX_KEYS}. Give the face time to read: hold a feeling 0.6 s or more; real surprise is fast (0.1 s),
dawning realisation slow (1-2 s). Don't do everything at once: eyes move first, then lids, then brows.
Blink now and then (a blink after a big glance, at a change of thought). Keep his restraint: big faces are
rare and earned. Start from his resting face and end settled. Title: a few words naming the performance."""


def generate(prompt, client=None, model=MODEL):
    """Claude writes a performance for the prompt. Raises RuntimeError with a readable reason."""
    prompt = str(prompt or "").strip()
    if not prompt:
        raise RuntimeError("write what Frank should do")
    if client is None:
        try:
            import anthropic
        except ImportError:
            raise RuntimeError("prompt-to-animation needs the anthropic package (add --with anthropic)")
        import brain   # frank/.env, as the conversation does
        brain.load_env()
        if not brain.available("opus-5.5"):
            raise RuntimeError("prompt-to-animation needs an Anthropic key: put ANTHROPIC_API_KEY in "
                               "frank/.env (the Mac has one), then restart Frank")
        try:
            client = anthropic.Anthropic()
        except Exception as e:
            raise RuntimeError(f"prompt-to-animation needs an Anthropic key in frank/.env ({e})")
    msg = client.beta.messages.create(
        model=model, max_tokens=8000,
        betas=["server-side-fallback-2026-07-01"], fallbacks="default",   # a declined request retries on another model
        output_config={"effort": EFFORT, "format": {"type": "json_schema", "schema": SCHEMA}},
        system=system_prompt(),
        messages=[{"role": "user", "content": f"Director's prompt: {prompt}"}],
    )
    if msg.stop_reason == "refusal":
        raise RuntimeError("Claude declined that prompt")
    if msg.stop_reason == "max_tokens":
        raise RuntimeError("the performance came out too long: ask for something shorter")
    text = next((b.text for b in msg.content if getattr(b, "type", "") == "text"), "")
    anim = clean(json.loads(text))
    anim["prompt"], anim["model"] = prompt, getattr(msg, "model", model)
    return anim


def clean(anim):
    """A timeline made safe to play: known kinds, tags and events only, numbers clamped, keys in
    time order, at most MAX_KEYS, nothing after MAX_SECONDS."""
    num = lambda x, lo, hi, default=0.0: max(lo, min(hi, float(x))) if isinstance(x, (int, float)) and math.isfinite(x) else default  # noqa: E731
    keys = []
    for k in (anim or {}).get("keys", [])[:MAX_KEYS * 2]:
        if not isinstance(k, dict) or k.get("kind") not in KINDS:
            continue
        key = {"t": num(k.get("t"), 0.0, MAX_SECONDS), "kind": k["kind"]}
        if key["kind"] == "tag":
            if k.get("tag") not in channels.TAGS:
                continue
            key.update(tag=k["tag"], intensity=num(k.get("intensity"), 0.1, 1.0, 0.8))
        elif key["kind"] == "feel":
            key.update(p=num(k.get("p"), -1, 1), a=num(k.get("a"), -1, 1), d=num(k.get("d"), -1, 1, 0.3))
        elif key["kind"] == "event":
            if k.get("event") not in EVENTS:
                continue
            key.update(event=k["event"])
        else:
            key.update(yaw=num(k.get("yaw"), -LOOK_MAX[0], LOOK_MAX[0]), pitch=num(k.get("pitch"), -LOOK_MAX[1], LOOK_MAX[1]))
        keys.append(key)
    keys.sort(key=lambda k: k["t"])
    keys = keys[:MAX_KEYS]
    last = keys[-1]["t"] if keys else 0.0
    duration = num((anim or {}).get("duration"), last, MAX_SECONDS, last + 1.0)
    return {"title": str((anim or {}).get("title") or "untitled")[:80], "duration": max(duration, last), "keys": keys}


class Player:
    """Plays a timeline on a live Engine, in a thread: tags and events at their times, a smooth
    glide between feel keys (Engine.steer), the eyes held where look keys put them; at the end
    (or stop()) the face goes back to the conversation."""

    def __init__(self, engine):
        self.engine = engine
        self.anim, self.t0, self.playing = None, 0.0, False
        self._stop = threading.Event()
        self.thread = None

    def play(self, anim):
        self.stop()
        self.anim = clean(anim)
        self._stop = threading.Event()
        self.t0, self.playing = time.monotonic(), True
        self.thread = threading.Thread(target=self._run, args=(self.anim, self._stop), daemon=True)
        self.thread.start()
        return self

    def stop(self):
        if self.thread and self.thread.is_alive():
            self._stop.set()
            self.thread.join(1.0)
        self.playing = False

    def status(self):
        elapsed = time.monotonic() - self.t0 if self.playing else None
        return {"playing": self.playing, "elapsed": elapsed,
                "title": self.anim["title"] if self.anim else None,
                "duration": self.anim["duration"] if self.anim else None}

    def _run(self, anim, stop):
        e, keys = self.engine, anim["keys"]
        feels = [k for k in keys if k["kind"] == "feel"]
        steered = False
        try:
            for k in keys:   # tags at their own times, through the engine's clock (its dwell rules apply)
                if k["kind"] == "tag":
                    e.tag(k["tag"], at=self.t0 + k["t"], intensity=k["intensity"])
            pending = [k for k in keys if k["kind"] in ("event", "look")]
            while not stop.is_set():
                t = time.monotonic() - self.t0
                while pending and pending[0]["t"] <= t:
                    k = pending.pop(0)
                    if k["kind"] == "event":
                        e.event(k["event"])
                    else:
                        e.look_at(k["yaw"], k["pitch"], hold=anim["duration"] - k["t"] + 0.5)
                point = glide(feels, t)
                if point is not None:
                    e.steer(*point, tags=True)
                    steered = True
                if t >= anim["duration"]:
                    break
                stop.wait(1.0 / STEER_HZ)
        finally:
            if steered:
                e.release()
            e.look_at(None)
            self.playing = False


def glide(feels, t):
    """The emotion-map point at time t: before the first feel key nothing (the face is free),
    then linear between keys (eased), then the last one held."""
    if not feels or t < feels[0]["t"]:
        return None
    for a, b in zip(feels, feels[1:]):
        if a["t"] <= t < b["t"]:
            u = (t - a["t"]) / max(1e-6, b["t"] - a["t"])
            u = u * u * (3 - 2 * u)
            return tuple(a[x] + (b[x] - a[x]) * u for x in ("p", "a", "d"))
    last = feels[-1]
    return last["p"], last["a"], last["d"]

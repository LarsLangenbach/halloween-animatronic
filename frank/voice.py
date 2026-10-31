"""
Frank's voice (ElevenLabs): design it, keep one, and speak with it.

    uv run --no-project --with httpx --with sounddevice python frank/voice.py design
    uv run ... frank/voice.py design "a description of your own"
    uv run ... frank/voice.py save 2       keep preview 2 of the latest batch as Frank's voice
    uv run ... frank/voice.py remix "deeper and wetter"   three variations on the saved voice
    uv run ... frank/voice.py gargle 0.55  the liquid effect on his voice (gargle.py), 0 = off
    uv run ... frank/voice.py speed 1.15   talking speed, 0.7 to 1.2; 0 = the voice's own
    uv run ... frank/voice.py say "[amused] Oh, hello. [chuckle] I don't think we've met."

"design" makes three previews from DESCRIPTION and opens a page to listen to them (run it
again for three more). "save" stores the chosen one in the ElevenLabs account and writes
its ID to frank/voice.json, which chat.py then uses. The key is ELEVENLABS_API_KEY in
frank/.env; it needs the Text to Speech, Voices and Text to Voice permissions.

Speech: sentences are grouped into pieces (a short first one, then longer ones), each
piece a streamed request started as soon as it's ready and played in order, so Frank
starts talking before the reply is finished. With
eleven_v4 models every line goes with a dry, weary delivery cue that the face tag only
shades (delivery_text); other models get the plain text. [chuckle] is not voiced.
"""

import base64
import json
import os
import queue
import subprocess
import sys
import threading
import time
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
import brain  # noqa: E402
import speech  # noqa: E402

API = "https://api.elevenlabs.io/v1"
CONFIG = HERE / "voice.json"
PREVIEWS = HERE.parent / "output" / "frank" / "voice"
MODEL = "eleven_v4_turbo"  # ~100 ms, reads bracketed delivery cues
RATE = 24000               # pcm_24000: 16-bit mono
FIRST_CHARS, NEXT_CHARS = 30, 160  # sentences are grouped into pieces at least this long
SLICE = RATE // 50 * 2             # 20 ms of audio per write, so a stop is near-instant
STALL_S = 1.0                      # a 20 ms write that takes this long means the output is dead (_watch)
# Backchannel: short sounds in his own voice, played while the brain is still thinking, so
# a slow reply sounds like a pause rather than a freeze. All are fillers to the ears
# (ears.FILLERS), so coming back through the microphone they can't interrupt him.
FILLERS = ["Hmm.", "Hm.", "Well...", "Right.", "Let me think.", "Hm?", "Now then."]  # "Mm." and "Ah." came out as drones
# v3 performs bracketed acting tags in the text. Frank's face tags (speech.py) become these,
# at the start of each piece, so [amused] on his face is an amused delivery too. Stability 0
# ("Creative") is the expressive setting; it makes every take different.
V3_TAGS = {"curious": "[curious]", "excited": "[excited]", "skeptical": "[skeptical]", "amused": "[amused]",
           "concentrating": "[thoughtful]", "confused": "[confused]", "irritated": "[irritated]",
           "surprised": "[surprised]", "vulnerable": "[hesitant]", "neutral": ""}
V3_SETTINGS = {"stability": 0.0}
FILLER_DIR = PREVIEWS / "fillers"
CHARS_PER_SEC = 14                 # rough speaking rate, to guess what was heard when cut off

# From CHARACTER.md §5.
DESCRIPTION = (
    "A middle-aged British man with a refined, understated accent and a low-to-mid pitch. "
    "His voice is noticeably raspy and a little breathy, strained and worn, as if his vocal "
    "cords are not fully formed, with an unusual resonance and occasionally imperfect "
    "articulation. He often sounds slightly tired, then turns animated and theatrical when "
    "something fascinates him. Dry, wry and intelligent.")
PREVIEW_TEXT = (
    "Oh, hello. I don't think we've met. I'm Frank. I know how I was made, you see... "
    "it's the rest I'm trying to understand. Hmm. Well, that was unexpected. Lars? Is that "
    "you? I've been meaning to get out more. Well. You know what I mean.")

# Delivery cues for eleven_v4 models. Every line carries BASE; a face only shades it.
# Literal cues ("amused", "excited", a chuckle) made him giddy (2026-10-26), so the shades
# are understated and the chuckle is silent: the face shows it, the voice doesn't.
BASE = "dry, weary, understated"
DELIVERY = {"neutral": None, "curious": "quietly intrigued", "excited": "more animated",
            "skeptical": "skeptical", "amused": "wry", "concentrating": "thoughtful",
            "confused": "puzzled", "irritated": "clipped", "surprised": "taken aback",
            "vulnerable": "soft, hesitant"}


def delivery_text(sentence, face=None):
    shade = DELIVERY.get(face)
    return f"[{BASE}{', ' + shade if shade else ''}] {sentence}"


def key():
    brain.load_env()
    k = os.environ.get("ELEVENLABS_API_KEY")
    if not k:
        sys.exit("Set ELEVENLABS_API_KEY in frank/.env")
    return k


def _check(r, what):
    if r.status_code >= 400:
        detail = r.text
        try:
            detail = r.json().get("detail", detail)
            detail = detail.get("message", detail) if isinstance(detail, dict) else detail
        except ValueError:
            pass
        sys.exit(f"{what} failed ({r.status_code}): {detail}")


def design(description=DESCRIPTION):
    import httpx
    r = httpx.post(f"{API}/text-to-voice/design", headers={"xi-api-key": key()}, timeout=120,
                   json={"voice_description": description, "model_id": "eleven_ttv_v3",
                         "text": PREVIEW_TEXT, "loudness": 0.8})  # 0.5 default came out whispery
    _check(r, "Voice design")
    _batch(r.json()["previews"], description, description)


def remix(change):
    """Three variations on Frank's saved voice, changed as described."""
    import httpx
    if not CONFIG.exists():
        sys.exit("No saved voice to remix: save one first.")
    cfg = json.loads(CONFIG.read_text(encoding="utf-8"))
    r = httpx.post(f"{API}/text-to-voice/{cfg['voice_id']}/remix", headers={"xi-api-key": key()},
                   timeout=120, json={"voice_description": change, "text": PREVIEW_TEXT,
                                      "loudness": 0.8, "guidance_scale": 3})
    _check(r, "Remix")
    _batch(r.json()["previews"], f"{cfg['description']} Remixed: {change}",
           f"Remix of {cfg['from_preview']}: {change}")


def _batch(previews, description, asked):
    folder = PREVIEWS / datetime.now().strftime("%Y-%m-%d_%H%M%S")
    folder.mkdir(parents=True)
    rows = []
    for i, p in enumerate(previews, 1):
        (folder / f"preview_{i}.mp3").write_bytes(base64.b64decode(p["audio_base_64"]))
        rows.append(f'<p><b>{i}</b> <audio controls src="preview_{i}.mp3"></audio></p>')
    (folder / "previews.json").write_text(json.dumps(dict(
        description=description, ids=[p["generated_voice_id"] for p in previews]), indent=1),
        encoding="utf-8")
    (folder / "listen.html").write_text(
        "<!doctype html><meta charset=utf-8><title>Frank voice previews</title>"
        "<body style='font:16px system-ui;margin:2em'><h2>Which one is Frank?</h2>"
        f"<p style='color:#666'>Asked for: {asked}</p>{''.join(rows)}"
        "<p style='color:#666'>Then: frank/voice.py save &lt;number&gt;, or design again.</p>",
        encoding="utf-8")
    print(f"{len(previews)} previews in {folder}")
    if sys.platform == "darwin":
        subprocess.run(["open", str(folder / "listen.html")])


def save(n):
    import httpx
    latest = sorted(PREVIEWS.glob("*/previews.json"))[-1]
    batch = json.loads(latest.read_text(encoding="utf-8"))
    if isinstance(batch, list):  # the first batch stored only the IDs
        batch = dict(description=DESCRIPTION, ids=batch)
    r = httpx.post(f"{API}/text-to-voice", headers={"xi-api-key": key()}, timeout=60,
                   json={"voice_name": "Frank", "voice_description": batch["description"][:1000],
                         "generated_voice_id": batch["ids"][n - 1]})
    _check(r, "Saving the voice")
    old = json.loads(CONFIG.read_text(encoding="utf-8")) if CONFIG.exists() else {}
    CONFIG.write_text(json.dumps(dict(
        voice_id=r.json()["voice_id"], model_id=MODEL, name="Frank",
        from_preview=f"{latest.parent.name} #{n}", description=batch["description"],
        gargle=old.get("gargle", 0)), indent=1) + "\n", encoding="utf-8")
    print(f"Saved as Frank's voice: {CONFIG}")


def compare(text):
    """The same line through each speech model, to hear what the model does to the voice."""
    import httpx
    import wave
    cfg = json.loads(CONFIG.read_text(encoding="utf-8"))
    events = speech.parse(text)
    plain = " ".join(v for k, v in events if k == "say")
    cued, face = [], None
    for k, v in events:
        if k == "face":
            face = v
        elif k == "say":
            cued.append(delivery_text(v, face))
    versions = [("eleven_multilingual_v2", plain, "multilingual v2, plain (how library samples are usually made)"),
                ("eleven_v4_turbo", plain, "v4 turbo, plain"),
                ("eleven_v4_turbo", " ".join(cued), "v4 turbo with Frank's dry delivery cues (what the chat uses)"),
                ("eleven_flash_v2_5", plain, "flash v2.5, plain (fastest)")]
    folder = PREVIEWS / f"compare_{datetime.now():%Y-%m-%d_%H%M%S}"
    folder.mkdir(parents=True)
    rows = []
    for i, (model, line, label) in enumerate(versions, 1):
        r = httpx.post(f"{API}/text-to-speech/{cfg['voice_id']}", timeout=60,
                       params={"output_format": f"pcm_{RATE}"}, headers={"xi-api-key": key()},
                       json={"text": line, "model_id": model})
        if r.status_code >= 400:
            rows.append(f"<p><b>{i}</b> {label}: failed ({r.status_code})</p>")
            continue
        with wave.open(str(folder / f"{i}.wav"), "wb") as w:
            w.setnchannels(1), w.setsampwidth(2), w.setframerate(RATE)
            w.writeframes(r.content[: len(r.content) // 2 * 2])
        rows.append(f"<p><b>{i}</b> {label}<br><audio controls src='{i}.wav'></audio></p>")
    (folder / "listen.html").write_text(
        "<!doctype html><meta charset=utf-8><title>Frank voice: models</title>"
        "<body style='font:16px system-ui;margin:2em'><h2>Same voice, different models</h2>"
        f"<p style='color:#666'>{cfg['name']}: \"{plain}\"</p>" + "".join(rows), encoding="utf-8")
    print(f"Comparison in {folder}")
    if sys.platform == "darwin":
        subprocess.run(["open", str(folder / "listen.html")])


def set_gargle(strength):
    cfg = json.loads(CONFIG.read_text(encoding="utf-8"))
    cfg["gargle"] = strength
    CONFIG.write_text(json.dumps(cfg, indent=1) + "\n", encoding="utf-8")
    print(f"Gargle effect set to {strength}")


def set_speed(speed):
    """0 = the voice's own settings; otherwise 0.7 to 1.2."""
    cfg = json.loads(CONFIG.read_text(encoding="utf-8"))
    cfg["speed"] = speed or None
    CONFIG.write_text(json.dumps(cfg, indent=1) + "\n", encoding="utf-8")
    print(f"Speed set to {speed or 'the voice default'}")


class Voice:
    """Speaks sentences in order while later ones are still being fetched."""

    def __init__(self, voice_id, model_id=MODEL, gargle=0, speed=None, speaker=None):
        self.voice_id, self.model_id, self.speed = voice_id, model_id, speed
        self.fx = None
        if gargle:
            from gargle import Gargle
            self.fx = Gargle(gargle)
        self.headers = {"xi-api-key": key()}
        import audio
        self.up = audio.Up2()
        self.lock = threading.Lock()  # the speaker can change while he talks (use_speaker)
        self.speaker, self.out = speaker, self._open(speaker)
        self.writing = (None, 0.0)    # (play thread, when its current write began), for the watchdog
        self.player = None            # the play thread; a stalled one is abandoned (_recover)
        import aec  # everything played is the echo canceller's reference (aec.py)
        self.aec = aec if aec.available() else None
        if self.aec:
            aec.output_latency = getattr(self.out, "latency", 0.05)
        self.order = queue.Queue()  # (gen, text, chunk queue) per piece, in speaking order
        self.log = lambda **k: None  # chat.py sets this: every piece and stop goes to the chat log
        self.mouth = None  # mouth.Mouth: fed every slice played, so the jaw follows the voice
        self.fillers = self._load_fillers()
        self.last_filler = None
        self.error, self.gen = None, 0  # stop() bumps gen; older pieces are dropped
        self.go = threading.Event()    # clear while paused (pause()): the play thread holds a slice
        self.go.set()
        self.paused = None             # when the pause began (monotonic), or None
        self.quiet = False             # after stop(): say() and filler() are ignored until start_reply()
        self.start_reply()
        self.player = threading.Thread(target=self._play, daemon=True)
        self.player.start()
        threading.Thread(target=self._watch, daemon=True).start()

    @staticmethod
    def _open(speaker):
        """An output stream at the sound card's own 48 kHz (audio.py: at 24 kHz the system
        buffered ~0.44 s). speaker: a device number or name (speakers()), None for the Mac's
        default output."""
        import sounddevice
        import audio
        out = sounddevice.RawOutputStream(samplerate=audio.DEVICE_RATE, channels=1, dtype="int16",
                                          latency="high", device=speaker)  # ~56 ms
        out.start()
        return out

    def use_speaker(self, speaker):
        """Play through another output device from the next slice on."""
        new = self._open(speaker)
        if not self.lock.acquire(timeout=STALL_S):   # the play thread is stuck in a write
            self._recover(f"switching the speaker while the output was stuck", speaker, new)
            return
        try:
            old, self.out, self.speaker = self.out, new, speaker
        finally:
            self.lock.release()
        old.stop()
        old.close()
        if self.aec:
            self.aec.output_latency = getattr(new, "latency", 0.05)

    def _watch(self):
        """Every so often: has the play thread been inside one 20 ms write for over STALL_S? That
        is the sound card stream no longer taking audio (2026-10-30: plugging the EarPods in
        while Frank ran left every piece fetched and never played), and a blocked write never
        returns. Then the stream and the thread are abandoned and new ones take over."""
        while True:
            time.sleep(STALL_S / 4)
            thread, began = self.writing
            if thread is not None and thread is self.player and time.monotonic() - began > STALL_S:
                self._recover("the sound output stopped taking audio (did the output device change?)")
            elif self.player is not None and not self.player.is_alive():   # it died (a bug): carry on
                self.log(what="player_died")
                print("voice: the play thread died; starting another")
                self.player = threading.Thread(target=self._play, daemon=True)
                self.player.start()

    def _recover(self, why, speaker=None, new=None):
        """Abandon the stuck play thread and its stream; open a new stream (on `speaker`, else the
        one in use, else the Mac's default output) and start a new play thread on the queue. The
        piece that was playing is lost; the rest of the reply follows on the new stream."""
        speaker = self.speaker if speaker is None and new is None else speaker
        if new is None:
            try:
                new = self._open(speaker)
            except Exception as e:  # that device is gone: the Mac's current default output
                speaker, new = None, self._open(None)
                why += f"; speaker {self.speaker!r} not available ({e})"
        lost = (self.current or {}).get("text", "")[:40]
        self.log(what="stalled", why=why, lost=lost, speaker=speaker)
        print(f"voice: {why}; playing on again through {speaker or 'the default output'}")
        self.lock = threading.Lock()   # the stuck thread holds the old one
        self.out, self.speaker = new, speaker
        if self.aec:
            self.aec.output_latency = getattr(new, "latency", 0.05)
        self.current = None
        if self.mouth:
            self.mouth.flush()
        self.player = threading.Thread(target=self._play, daemon=True)
        self.order.task_done()        # the stuck thread's piece, which it will never finish
        self.player.start()

    def beep(self):
        """A short tone through the speaker: is it the right one, and loud enough?"""
        import numpy as np
        import audio
        t = np.arange(int(audio.DEVICE_RATE * 0.35)) / audio.DEVICE_RATE
        tone = 0.3 * np.sin(2 * np.pi * 440 * t) * np.minimum(1, np.minimum(t, t[-1] - t) / 0.02)
        if not self.lock.acquire(timeout=STALL_S):   # the play thread is stuck in a write
            self._recover("the sound output was stuck when the test sound was asked for")
            self.lock.acquire()
        try:
            self.out.write((tone * 32767).astype(np.int16).tobytes())
        finally:
            self.lock.release()

    @classmethod
    def from_config(cls):
        if not CONFIG.exists():
            return None
        cfg = json.loads(CONFIG.read_text(encoding="utf-8"))
        return cls(cfg["voice_id"], cfg.get("model_id", MODEL), cfg.get("gargle", 0), cfg.get("speed"))

    def start_reply(self):
        self.t0, self.first_sound, self.said, self.buf = time.perf_counter(), None, [], []
        self.last_face, self.quiet = None, False
        self.heard, self.current = [], None  # pieces played in full; the piece playing now

    @property
    def busy(self):
        return self.order.unfinished_tasks > 0 or bool(self.buf)

    def pause(self, why=""):
        """Hold the voice where it is (someone may be talking over him): the slice being
        written finishes, then nothing more plays until resume() or stop(). Returns False if
        nothing was playing."""
        if self.paused is not None or self.current is None:
            return False
        self.paused = time.monotonic()
        self.go.clear()
        if self.mouth:
            self.mouth.flush()
        self.log(what="pause", why=why, playing=(self.current or {}).get("text", "")[:60],
                 at=round((self.current or {}).get("played", 0) / 2 / RATE, 2))
        return True

    def resume(self, why=""):
        """Carry on from where pause() held him."""
        if self.paused is None:
            return
        held = time.monotonic() - self.paused
        self.paused = None
        self.go.set()
        self.log(what="resume", why=why, held=round(held, 2))

    def stop(self, reason=""):
        """Go quiet now (an interruption) and return roughly what the listener heard."""
        self.log(what="stop", reason=reason, playing=(self.current or {}).get("text", "")[:60])
        self.gen += 1
        self.buf, self.quiet, self.paused = [], True, None
        self.go.set()  # a paused play thread wakes, sees the new gen and drops its piece
        if self.mouth:
            self.mouth.flush()
        heard, cur = list(self.heard), self.current
        if cur and cur["played"]:
            if cur["done"] and cur["received"]:
                frac = cur["played"] / cur["received"]
            else:  # still downloading: estimate from speaking time
                frac = cur["played"] / 2 / RATE * CHARS_PER_SEC / max(1, len(cur["text"]))
            cut = cur["text"][: int(len(cur["text"]) * min(1.0, frac))]
            heard.append(cut.rsplit(" ", 1)[0] if " " in cut else cut)
        return " ".join(heard).strip()

    def say(self, sentence, face=None, chuckle=False):
        """Queue a sentence. Sentences are grouped into pieces of at least FIRST_CHARS
        (the first) and NEXT_CHARS (the rest): one-word requests ("Oh.") come out in a
        different intonation, so the voice stops sounding like itself."""
        if self.quiet:  # stopped: a sentence that was already on its way is dropped
            return
        if self.model_id == "eleven_v3":
            tag = V3_TAGS.get(face or "", "") if face != getattr(self, "last_face", None) or not self.buf else ""
            self.last_face = face
            if chuckle:
                tag = ("[chuckles] " + tag).strip()
            sentence = f"{tag} {sentence}".strip() if tag else sentence
        elif self.model_id.startswith("eleven_v4"):
            sentence = delivery_text(sentence, face)
        if not self.buf:
            self.buf_faces = [(0, face)]  # the piece's expressions, for the face: (character, tag)
        elif face != self.buf_faces[-1][1]:
            self.buf_faces.append((sum(len(s) + 1 for s in self.buf), face))  # a tag mid-piece
        self.buf.append(sentence)
        need = FIRST_CHARS if not self.said else NEXT_CHARS
        if sum(len(s) + 1 for s in self.buf) >= need:
            self._send()

    def _load_fillers(self):
        """The filler clips for this voice and model, made on first use (fillers())."""
        folder = FILLER_DIR / f"{self.voice_id}_{self.model_id}"
        clips = ([(p.stem.split("_", 1)[1], p.read_bytes()) for p in sorted(folder.glob("*.pcm"))]
                 if folder.exists() else [])
        if len(clips) < len(FILLERS):
            try:
                clips = list(zip([_slug(t) for t in FILLERS], make_fillers(self.voice_id, self.model_id, self.headers)))
            except Exception as e:
                self.error = f"no filler clips: {e}"
        return clips

    def filler(self):
        """Play a short "Hmm." now, before whatever the reply sends next, and return its
        words (for the echo filter). Only when nothing of the reply has been sent yet, so it
        never lands in the middle of a sentence; never the same one twice running."""
        if not self.fillers or self.said or self.quiet:
            return None
        import random
        name, clip = random.choice([f for f in self.fillers if f[0] != self.last_filler] or self.fillers)
        self.last_filler = name
        chunks = queue.Queue()
        chunks.put(clip)
        chunks.put(None)
        self.order.put((self.gen, "", chunks, []))  # no text: not part of what he said; no face
        return name.replace("_", " ")

    def end_reply(self):
        if self.buf:
            self._send()

    def _send(self):
        text, self.buf = " ".join(self.buf), []
        body = {"model_id": self.model_id, "text": text}
        if self.model_id == "eleven_v3":
            body["voice_settings"] = dict(V3_SETTINGS)  # speed is ignored at Creative, so not sent
        elif self.speed:
            # Setting any voice setting puts the voice's other settings back to the account
            # defaults for this request (heard on 2026-10-27), so only set it when chosen.
            body["voice_settings"] = {"speed": self.speed}
        if self.said and not self.model_id.startswith(("eleven_v4", "eleven_v3")):
            # Keeps the intonation flowing. v3 and v4 reject it (400 "not yet supported"): on v3
            # that silently lost every piece after the first of each reply (2026-10-28).
            body["previous_text"] = " ".join(self.said)[-300:]
        self.said.append(text)
        self.log(what="piece", text=text[:80], chars=len(text))
        chunks = queue.Queue()
        self.order.put((self.gen, text, chunks, getattr(self, "buf_faces", [(0, None)])))
        threading.Thread(target=self._fetch, args=(body, chunks, self.gen), daemon=True).start()

    def wait(self):
        self.end_reply()
        self.order.join()

    def _fetch(self, body, chunks, gen):
        import httpx
        try:
            for attempt in range(4):
                with httpx.stream("POST", f"{API}/text-to-speech/{self.voice_id}/stream",
                                  params={"output_format": f"pcm_{RATE}"}, headers=self.headers,
                                  json=body, timeout=30) as r:
                    # 409: a library voice's first use adds it to the account, and parallel
                    # sentences collide with that; wait and retry.
                    if r.status_code == 409 and attempt < 3:
                        time.sleep(0.5 * (attempt + 1))
                        continue
                    if r.status_code >= 400:
                        r.read()
                        raise RuntimeError(f"{r.status_code}: {r.text[:200]}")
                    got = 0
                    for b in r.iter_bytes():
                        if gen != self.gen:  # stopped: no need for the rest
                            return
                        chunks.put(b)
                        got += len(b)
                    self.log(what="fetched", text=body["text"][:40], seconds=round(got / 2 / RATE, 1))
                    return
        except Exception as e:
            self.error = f"voice: {e}"
            self.log(what="fetch_error", text=body["text"][:40], error=str(e)[:160])
        finally:
            chunks.put(None)

    def _play(self):
        me = threading.current_thread()
        while me is self.player:
            item = self.order.get()
            try:
                self._play_one(me, item)
            except Exception as e:
                self.error = f"voice: a piece failed ({e!r})"
                self.log(what="piece_failed", error=repr(e), text=str(item[1:2])[:40])
                print(self.error)
                if me is self.player:
                    self.order.task_done()

    def _play_one(self, me, item):
        gen, text, chunks, faces = item
        rec = {"text": text, "played": 0, "received": 0, "done": False}
        faces = list(faces or [])  # (character, tag): each goes to the face when its words play
        if gen == self.gen:
            self.current = rec
            if self.mouth and faces:
                self.mouth.face(faces.pop(0)[1])
        odd = b""
        # A stopped piece is left where it is, not drained: its fetch thread stops at its next
        # chunk, and nothing waits on it (draining held wait() until the download finished,
        # so his answer to the interruption was late, 2026-10-30).
        while gen == self.gen and (b := chunks.get()) is not None:
            rec["received"] += len(b)
            b, n = odd + b, (len(odd) + len(b)) // 2 * 2
            b, odd = b[:n], b[n:]
            for i in range(0, len(b), SLICE):  # small slices, so stop() and pause() are quick
                while not self.go.wait(0.05):  # paused: hold here until resume() or stop()
                    if gen != self.gen:
                        break
                if gen != self.gen:
                    break
                if self.first_sound is None:
                    self.first_sound = time.perf_counter() - self.t0
                s = b[i:i + SLICE]
                out = self.fx.process(s) if self.fx else s
                lock, stream = self.lock, self.out
                self.writing = (me, time.monotonic())
                with lock:
                    stream.write(self.up(out))
                if self.writing[0] is me:
                    self.writing = (None, 0.0)
                if me is not self.player:   # abandoned by _recover while that write hung
                    return
                if self.mouth:
                    self.mouth.feed(out)
                if self.aec:
                    try:
                        self.aec.render(out, RATE)
                    except Exception as e:
                        self.aec, self.error = None, f"echo cancellation off ({e})"
                rec["played"] += len(s)
                if faces and self.mouth:  # where the voice has got to, as stop() estimates it
                    if rec["played"] / 2 / RATE * CHARS_PER_SEC >= faces[0][0]:
                        self.mouth.face(faces.pop(0)[1])
        rec["done"] = gen == self.gen
        self.log(what="played" if gen == self.gen else "dropped", text=text[:40],
                 seconds=round(rec["played"] / 2 / RATE, 1), of=round(rec["received"] / 2 / RATE, 1))
        if gen == self.gen:
            self.heard.append(text)
            self.current = None
        self.order.task_done()


def _slug(text):
    return "".join(c if c.isalnum() else "_" for c in text.strip(".?!").lower()).strip("_")


def make_fillers(voice_id, model_id, headers):
    """Fetch the filler clips for a voice once (pcm, 24 kHz) into FILLER_DIR."""
    import httpx
    folder = FILLER_DIR / f"{voice_id}_{model_id}"
    folder.mkdir(parents=True, exist_ok=True)
    clips = []
    for i, text in enumerate(FILLERS):
        r = httpx.post(f"{API}/text-to-speech/{voice_id}", timeout=60, params={"output_format": f"pcm_{RATE}"},
                       headers=headers, json={"text": text, "model_id": model_id})
        if r.status_code >= 400:
            raise RuntimeError(f"{r.status_code}: {r.text[:120]}")
        pcm = r.content[: len(r.content) // 2 * 2]
        (folder / f"{i}_{_slug(text)}.pcm").write_bytes(pcm)
        clips.append(pcm)
    return clips


def speakers():
    """The output devices: (list of {id, name}, the number of the Mac's default)."""
    import sounddevice
    found = [dict(id=i, name=d["name"]) for i, d in enumerate(sounddevice.query_devices())
             if d["max_output_channels"] > 0]
    return found, sounddevice.default.device[1]


def say(text):
    v = Voice.from_config()
    if not v:
        sys.exit("No voice yet: run design, then save <n>.")
    face, chuckle = None, False
    for kind, value in speech.parse(text):
        if kind == "face":
            face = value
        elif kind == "sound":
            chuckle = True
        else:
            v.say(value, face, chuckle)
            chuckle = False
    v.wait()
    time.sleep(0.3)  # let the last buffer drain
    if v.error:
        print(v.error)
    print(f"first sound after {v.first_sound:.2f}s" if v.first_sound else "no sound")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "design":
        design(" ".join(sys.argv[2:]) or DESCRIPTION)
    elif cmd == "remix" and len(sys.argv) > 2:
        remix(" ".join(sys.argv[2:]))
    elif cmd == "gargle" and len(sys.argv) > 2:
        set_gargle(float(sys.argv[2]))
    elif cmd == "speed" and len(sys.argv) > 2:
        set_speed(float(sys.argv[2]))
    elif cmd == "compare":
        compare(" ".join(sys.argv[2:]) or "[curious] Oh, hello. I don't think we've met. I'm Frank. "
                "[amused] I know how I was made, you see... it's the rest I'm trying to understand.")
    elif cmd == "save" and len(sys.argv) > 2:
        save(int(sys.argv[2]))
    elif cmd == "fillers":
        cfg = json.loads(CONFIG.read_text(encoding="utf-8"))
        clips = make_fillers(cfg["voice_id"], cfg.get("model_id", MODEL), {"xi-api-key": key()})
        print(f"{len(clips)} filler clips: " + ", ".join(f"{t} ({len(c) / 2 / RATE:.1f} s)" for t, c in zip(FILLERS, clips)))
    elif cmd == "say" and len(sys.argv) > 2:
        say(" ".join(sys.argv[2:]))
    else:
        print(__doc__)

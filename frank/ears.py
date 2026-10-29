"""
Frank's ears: streaming speech-to-text from the microphone (ElevenLabs Scribe, realtime).

    uv run --no-project --with httpx --with sounddevice --with websockets python frank/ears.py
    (prints what it hears, live, until Ctrl+C: a quick microphone test)

The microphone streams 100 ms chunks of 16 kHz audio over a websocket. The service sends
partial text while someone talks and commits a sentence after `silence` seconds of quiet.
People pause between sentences, so a turn only ends when `grace` more seconds pass after a
commit with no new speech (a third of that after a question). Callbacks:
    on_partial(text)   the turn so far, live
    on_early(text)     a sentence just ended: the turn may be over (start thinking)
    on_resumed()       they carried on talking after on_early (drop that thought)
    on_final(text)     the turn is over
    on_barge(text)     while Frank talks: someone talking over him, not his own echo
While Frank talks (speaking(is_echo)) the mic keeps listening. Two layers keep him from
hearing himself through the speakers: echo cancellation (aec.py, when the livekit package
is installed) takes his voice out of the mic signal, and whatever still gets through is
checked against his words (echo_check): mostly his words, fillers like "mm-hmm", or a
single stray word are echo; two or more new words, or "wait" / "stop", interrupt him.
off() sends silence.
The key is ELEVENLABS_API_KEY in frank/.env; it needs the Speech to Text permission.
"""

import array
import asyncio
import base64
import json
import queue
import re
import sys
import threading
import time
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
import voice  # noqa: E402  (shares the key loading)

URL = "wss://api.elevenlabs.io/v1/speech-to-text/realtime"
RATE = 16000
CHUNK = RATE // 10    # 100 ms
LOUD = 0.015 * 32768  # RMS above this counts as someone talking
ECHO_WINDOW = 2.0     # seconds after Frank stops in which his own words are still echo (1.0 let his own
                      # sentence back in as a visitor's line through the laptop speakers, 2026-10-28)
DEBUG = bool(__import__("os").environ.get("FRANK_EARS_DEBUG"))  # print every message
# One word is enough to interrupt if it's one of these (and not one Frank is saying).
STOP_WORDS = {"stop", "wait", "frank", "sorry", "hang", "excuse", "hold", "no", "hey"}
# Sounds that never interrupt: his "Hmm." comes back through the speakers as "Mm-hmm".
FILLERS = {"mm", "hmm", "mhm", "mmm", "hm", "uh", "um", "ah", "oh", "er", "erm", "huh",
           "yeah", "yes", "okay", "ok", "right", "well", "so", "and", "the", "a", "i"}


def words(text):
    return re.findall(r"[a-z']+", text.lower().replace("-", " "))


def echo_check(reply_text):
    """is_echo(heard) for a reply: True unless the heard text is clearly someone else.

    Frank's voice through the speakers comes back slightly misheard, so a word close to
    one of his (difflib ratio >= 0.75) counts as his. An interruption needs three or more
    new, non-filler words making up at least half of what was heard, or a stop word (two
    let his own sentence through the laptop speakers cut him off, 2026-10-28).
    is_echo.why(heard) says what it saw, for the log."""
    import difflib
    own = set(words(reply_text))

    def his(word):
        return word in own or bool(difflib.get_close_matches(word, own, n=1, cutoff=0.75))

    def judge(heard):
        w = [x for x in words(heard) if x not in FILLERS]
        foreign = [x for x in w if not his(x)]
        stop = [x for x in foreign if x in STOP_WORDS]
        echo = not stop and (len(foreign) < 3 or len(foreign) / len(w) < 0.5)
        return echo, dict(new=foreign, stop=stop, of=len(w))

    def is_echo(heard):
        return judge(heard)[0]
    is_echo.why = lambda heard: judge(heard)[1]
    return is_echo


class Ears:
    def __init__(self, on_partial, on_final, on_early=None, on_resumed=None, on_barge=None,
                 on_error=print, silence=0.3, grace=0.25):
        self.on_partial, self.on_final, self.on_error = on_partial, on_final, on_error
        self.on_early = on_early or (lambda text: None)
        self.on_resumed = on_resumed or (lambda: None)
        self.on_barge = on_barge or (lambda text: None)
        self.silence, self.grace = silence, grace
        self.audio = queue.Queue()
        self.mode = "listen"         # "listen", "speaking" (Frank talking) or "off"
        self.is_echo, self.echo_until = None, 0.0
        self.last_voice = 0.0        # when the microphone last heard someone (perf_counter)
        self.loud_since = None       # when the current run of loud chunks began (perf_counter)
        self.on_while_speaking = lambda text, echo: None  # chat.py logs what arrives while he talks
        self.on_trace = lambda **k: None  # chat.py logs the turn-ending steps (partial, commit, resumed, final)
        self.ready = threading.Event()
        self._clear()

    def _clear(self):
        self.pending, self.last_commit, self.last_partial, self.told_resumed = [], 0.0, 0.0, False

    def start(self):
        import sounddevice
        import aec
        import audio
        self.aec = aec if aec.available() else None
        # The sound card's own 48 kHz, converted down here (audio.py): opened at 16 kHz the
        # system buffered 0.35-1.2 s.
        self.down, self.buf16 = audio.Down3(), b""
        self.mic = sounddevice.RawInputStream(samplerate=audio.DEVICE_RATE, channels=1,
                                              dtype="int16", latency="low", callback=self._mic48)
        self.mic.start()
        if self.aec:
            aec.set_delay(aec.output_latency, self.mic.latency)
        threading.Thread(target=lambda: asyncio.run(self._run()), daemon=True).start()
        if not self.ready.wait(10):
            self.on_error("ears: no connection to the speech-to-text service after 10 s")

    def loud_for(self):
        """How long the microphone has been continuously loud, in seconds (0 if it isn't)."""
        return time.perf_counter() - self.loud_since if self.loud_since else 0.0

    def off(self):
        self.mode = "off"

    def speaking(self, is_echo):
        """Frank is replying: listen for interruptions only."""
        self.is_echo = is_echo
        self.mode = "speaking"

    def listen(self, after=0.0):
        """A new turn: listen normally (after a short wait for the speaker's tail)."""
        time.sleep(after)
        self._clear()
        self.echo_until = time.perf_counter() + ECHO_WINDOW
        self.mode = "listen"

    def _mic48(self, data, frames, t, status):
        """The sound card's callback: 48 kHz in, 100 ms chunks of 16 kHz on to _mic."""
        self.buf16 += self.down(bytes(data))
        while len(self.buf16) >= CHUNK * 2:
            chunk, self.buf16 = self.buf16[:CHUNK * 2], self.buf16[CHUNK * 2:]
            self._mic(chunk, None, None, None)

    def _mic(self, data, frames, t, status):
        pcm = bytes(data)
        if self.mode == "off":
            pcm = bytes(len(pcm))
        else:
            if getattr(self, "aec", None):
                try:
                    pcm = self.aec.capture(pcm, RATE)  # Frank's own voice taken out (aec.py)
                except Exception as e:  # an exception here would stop the microphone stream
                    self.aec = None
                    self.on_error(f"ears: echo cancellation off ({e}); listening without it")
            a = array.array("h", pcm)
            rms = (sum(x * x for x in a) / len(a)) ** 0.5 if a else 0.0
            # The room's noise floor: drops at once, rises slowly (about 2 % a second), so
            # a noisy event doesn't count as someone talking all the time.
            self.floor = min(rms, getattr(self, "floor", rms) * 1.002) or 1.0
            if rms > max(LOUD, 3 * self.floor):
                self.last_voice = time.perf_counter()
                self.loud_since = self.loud_since or self.last_voice
            else:
                self.loud_since = None
        self.audio.put(pcm)

    async def _run(self):
        import websockets
        params = (f"?model_id=scribe_v2_realtime&audio_format=pcm_{RATE}&language_code=en"
                  f"&commit_strategy=vad&vad_silence_threshold_secs={self.silence}")
        try:
            async with websockets.connect(URL + params, max_size=2**22,
                                          additional_headers={"xi-api-key": voice.key()}) as ws:
                await asyncio.gather(self._send(ws), self._receive(ws), self._turns())
        except Exception as e:
            self.on_error(f"ears: {type(e).__name__}: {e}")
            self.ready.set()

    async def _send(self, ws):
        while True:
            try:
                pcm = self.audio.get_nowait()
            except queue.Empty:  # polled, so no worker thread is left blocking at exit
                await asyncio.sleep(0.01)
                continue
            await ws.send(json.dumps({"message_type": "input_audio_chunk", "commit": False,
                                      "sample_rate": RATE,
                                      "audio_base_64": base64.b64encode(pcm).decode()}))

    async def _receive(self, ws):
        async for raw in ws:
            msg = json.loads(raw)
            kind, text = msg.get("message_type"), (msg.get("text") or "").strip()
            now = time.perf_counter()
            if DEBUG:
                print(f"\n[ears {now:.2f} {self.mode}] {kind}: {text!r}")
            if kind == "session_started":
                self.ready.set()
                continue
            if "error" in msg or kind == "warning":
                self.on_error(f"ears: {kind}: {msg.get('error') or msg.get('warning')}")
                continue
            if kind not in ("partial_transcript", "committed_transcript", "session_started") and DEBUG is False:
                self.on_trace(step="message", kind=kind)
            if kind not in ("partial_transcript", "committed_transcript") or not text:
                continue
            if self.mode == "off":
                continue
            if self.mode == "speaking":
                self.on_while_speaking(text, bool(self.is_echo and self.is_echo(text)))
                if self.is_echo and not self.is_echo(text):
                    self.mode = "listen"
                    self._clear()
                    self.echo_until = now + ECHO_WINDOW  # his last words are still in the air
                    if kind == "committed_transcript":
                        self.pending, self.last_commit = [text], now
                    else:
                        self.last_partial = now
                    self.on_barge(text)
                continue
            # listening; his own words can still arrive just after he stops
            if now < self.echo_until and self.is_echo and self.is_echo(text):
                continue
            if kind == "partial_transcript":
                if not self.last_partial or now - self.last_partial > 1.0:
                    self.on_trace(step="partial", text=text[:60])
                self.last_partial = now
                self.on_partial(" ".join(self.pending + [text]))
            else:
                self.pending.append(text)
                self.last_commit, self.told_resumed = now, False
                self.on_trace(step="commit", text=text[:60], floor=round(self.floor), loud=round(self.last_voice - now, 2))
                self.on_partial(" ".join(self.pending))
                self.on_early(" ".join(self.pending))

    async def _turns(self):
        """End the turn once a commit has stood for `grace` seconds with no new speech.
        New speech is whatever comes first: the microphone getting loud again, or a new
        partial (which lags speech by a few hundred ms)."""
        while True:
            await asyncio.sleep(0.05)
            if not self.pending or self.mode != "listen":
                continue
            resumed = self.last_voice > self.last_commit or self.last_partial > self.last_commit
            if resumed:
                if not self.told_resumed:
                    self.told_resumed = True
                    self.on_trace(step="resumed", by="voice" if self.last_voice > self.last_commit else "partial",
                                  floor=round(self.floor))
                    self.on_resumed()
                continue
            grace = self.grace / 3 if self.pending[-1].endswith("?") else self.grace
            if time.perf_counter() - self.last_commit >= grace:
                text = " ".join(self.pending)
                self._clear()
                self.on_trace(step="final", text=text[:60])
                self.on_final(text)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    ears = Ears(on_partial=lambda t: print(f"\r  … {t}\033[K", end="", flush=True),
                on_final=lambda t: print(f"\r  heard: {t}\033[K"))
    ears.start()
    print("Listening. Talk, then pause. Ctrl+C to stop.")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass

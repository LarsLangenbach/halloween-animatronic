"""
A liquid-in-the-throat effect on Frank's voice, applied on the laptop as the audio streams.

    uv run --no-project --with httpx --with sounddevice --with numpy --with scipy python frank/gargle.py demo
    (renders Frank's saved voice at several strengths and opens a page to compare them)

Three layers, all scaled by one strength from 0 (off) to 1:
  - warble: the pitch wobbles irregularly (a delay line swept by a jittery 6-11 Hz LFO);
  - gurgle: the level flutters at an irregular 12-30 Hz, like liquid breaking up the sound;
  - fluid: a resonant low-pass muffles the top end, like a throat half full,
plus small bubbles (short rising blips) while he is speaking.
Everything keeps its state between chunks, so streamed audio has no seams or extra delay.
The chosen strength goes in frank/voice.json as "gargle".
"""

import json
import subprocess
import sys
from pathlib import Path

import numpy as np
from scipy.signal import butter, lfilter, lfilter_zi

HERE = Path(__file__).parent
RATE = 24000


class Gargle:
    def __init__(self, strength=0.5, rate=RATE, seed=1):
        s = float(np.clip(strength, 0, 1))
        self.s, self.rate = s, rate
        self.rng = np.random.default_rng(seed)
        # warble
        self.depth = s * 0.0022 * rate  # up to 2.2 ms of delay swing
        self.base = self.depth + 2
        self.hist = np.zeros(int(self.base + self.depth) + 4)
        self.phase, self.freq = 0.0, 8.0
        # gurgle: smoothed noise, low-passed around 25 Hz
        self.gb, self.ga = butter(2, 25 / (rate / 2))
        self.gz = lfilter_zi(self.gb, self.ga) * 0
        # fluid: resonant-ish low-pass, lower cutoff as strength rises
        cutoff = 5500 - 3300 * s
        self.lb, self.la = butter(2, cutoff / (rate / 2))
        self.lz = lfilter_zi(self.lb, self.la) * 0
        # loudness envelope for the bubbles
        self.eb, self.ea = butter(1, 15 / (rate / 2))
        self.ez = lfilter_zi(self.eb, self.ea) * 0
        self.tail = np.zeros(0)  # bubble sound that runs into the next chunk

    def process(self, pcm):
        """16-bit mono PCM bytes in, the same length out."""
        if self.s == 0 or not pcm:
            return pcm
        x = np.frombuffer(pcm, dtype=np.int16).astype(np.float64) / 32768
        n = len(x)

        # warble: read the signal back through a swept delay
        self.freq = float(np.clip(self.freq + self.rng.normal(0, 0.8), 6, 11))
        ph = self.phase + 2 * np.pi * self.freq * np.arange(1, n + 1) / self.rate
        self.phase = float(ph[-1] % (2 * np.pi))
        d = self.base + self.depth * np.sin(ph)
        ext = np.concatenate([self.hist, x])
        pos = len(self.hist) + np.arange(n) - d
        i = np.floor(pos).astype(int)
        frac = pos - i
        y = ext[i] * (1 - frac) + ext[i + 1] * frac
        self.hist = ext[-len(self.hist):]

        # gurgle: irregular level flutter
        noise, self.gz = lfilter(self.gb, self.ga, self.rng.standard_normal(n), zi=self.gz)
        flutter = np.clip(0.5 + 9 * noise, 0, 1)
        y = y * (1 - 0.75 * self.s * flutter)

        # fluid: muffle the top end
        y, self.lz = lfilter(self.lb, self.la, y, zi=self.lz)

        # bubbles while speaking
        env, self.ez = lfilter(self.eb, self.ea, np.abs(x), zi=self.ez)
        out = np.zeros(n + int(0.04 * self.rate))
        out[:len(self.tail)] += self.tail
        for k in np.nonzero(self.rng.random(n) < 7 * self.s / self.rate)[0]:
            if env[k] > 0.02:
                b = self._bubble()
                out[k:k + len(b)] += b * env[k] * 6 * self.s
        y = y + out[:n]
        self.tail = out[n:]
        return (np.clip(y * (1 + 0.6 * self.s), -1, 1) * 32767).astype(np.int16).tobytes()

    def _bubble(self):
        """A short blip that rises in pitch, like air coming up through liquid."""
        t = np.arange(int(self.rng.uniform(0.012, 0.03) * self.rate)) / self.rate
        f0 = self.rng.uniform(350, 900)
        f = f0 * (1 + 6 * t / t[-1])
        return np.sin(2 * np.pi * np.cumsum(f) / self.rate) * np.exp(-t / (t[-1] / 3))


def demo(strengths=(0, 0.3, 0.55, 0.8, 1.0)):
    import httpx
    import voice
    cfg = json.loads(voice.CONFIG.read_text(encoding="utf-8"))
    r = httpx.post(f"{voice.API}/text-to-speech/{cfg['voice_id']}", timeout=60,
                   params={"output_format": f"pcm_{RATE}"}, headers={"xi-api-key": voice.key()},
                   json={"text": voice.PREVIEW_TEXT, "model_id": cfg.get("model_id", voice.MODEL)})
    voice._check(r, "Speech")
    raw = r.content[: len(r.content) // 2 * 2]
    folder = voice.PREVIEWS / "gargle_demo"
    folder.mkdir(parents=True, exist_ok=True)
    rows = []
    for s in strengths:
        g = Gargle(s)
        step = 2400 * 2  # process in 100 ms chunks, as streaming does
        pcm = b"".join(g.process(raw[i:i + step]) for i in range(0, len(raw), step))
        name = f"gargle_{int(s * 100):03d}.wav"
        _wav(folder / name, pcm)
        rows.append(f"<p><b>{s:.2f}</b>{' (off)' if s == 0 else ''} "
                    f"<audio controls src='{name}'></audio></p>")
    (folder / "listen.html").write_text(
        "<!doctype html><meta charset=utf-8><title>Frank gargle</title>"
        "<body style='font:16px system-ui;margin:2em'><h2>How much gargle?</h2>"
        "<p style='color:#666'>The same line in Frank's saved voice, with the liquid effect "
        "at different strengths.</p>" + "".join(rows), encoding="utf-8")
    print(f"Demo in {folder}")
    if sys.platform == "darwin":
        subprocess.run(["open", str(folder / "listen.html")])


def _wav(path, pcm):
    import wave
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes(pcm)


if __name__ == "__main__":
    sys.path.insert(0, str(HERE))
    if len(sys.argv) > 1 and sys.argv[1] == "demo":
        demo()
    else:
        print(__doc__)

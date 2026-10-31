"""
Sample-rate conversion for the sound card.

Macs run their audio at 48 kHz. Opening a stream at the voice's 24 kHz or the ears'
16 kHz made the system add conversion buffers that delayed everything by 0.4 to 1.2 s
(measured 2026-10-27: 441 ms out, 352-1219 ms in, against 56 and 118 ms at 48 kHz) and
pushed the echo delay past what the echo canceller accepts. So the streams run at 48 kHz
and these convert, keeping their filter state between chunks so there are no clicks.
"""

import numpy as np
from scipy.signal import firwin, lfilter

DEVICE_RATE = 48000


def _pcm(x):
    return np.clip(np.round(x), -32768, 32767).astype(np.int16).tobytes()


class Up2:
    """24 kHz -> 48 kHz: zero-stuff, then low-pass at the old Nyquist."""

    def __init__(self):
        self.h = firwin(48, 0.5) * 2
        self.z = np.zeros(len(self.h) - 1)

    def __call__(self, pcm):
        x = np.frombuffer(pcm, dtype=np.int16).astype(np.float64)
        up = np.zeros(2 * len(x))
        up[::2] = x
        y, self.z = lfilter(self.h, 1.0, up, zi=self.z)
        return _pcm(y)


class Down3:
    """48 kHz -> 16 kHz: low-pass below 8 kHz, then keep every third sample."""

    def __init__(self):
        self.h = firwin(64, 0.3)
        self.z = np.zeros(len(self.h) - 1)
        self.phase = 0  # which sample of the next chunk is the next one kept

    def __call__(self, pcm):
        x = np.frombuffer(pcm, dtype=np.int16).astype(np.float64)
        y, self.z = lfilter(self.h, 1.0, x, zi=self.z)
        out = y[self.phase::3]
        self.phase = (self.phase - len(x)) % 3
        return _pcm(out)


class Tempo:
    """Speech faster (or slower) at its own pitch, streamed: WSOLA time-stretching.

    ElevenLabs' own speed setting stops at 1.2 and the v3 model ignores it at Creative
    (2026-10-30: 1.2 came out no shorter than plain over three takes each), so the voice
    is sped up here, after it arrives. Half-overlapping Hann-windowed frames are taken
    from the input every hop*factor samples and laid down every hop; each frame is
    slid up to `tol` either way to where it best continues the previous one (normalised
    cross-correlation), so the waveform stays joined and the pitch and timbre are his.
    Feed it the PCM as it arrives; it returns what is ready. flush() ends a piece.
    """

    def __init__(self, factor, rate=24000, frame_ms=30, tol_ms=7):
        self.factor = factor
        self.n = int(rate * frame_ms / 1000) // 2 * 2
        self.hop = self.n // 2
        self.tol = int(rate * tol_ms / 1000)
        self.win = np.hanning(self.n + 1)[:-1]  # periodic: two half-overlapped copies sum to 1
        self._reset()

    def _reset(self):
        self.buf = np.zeros(0)        # input not yet used
        self.pos = 0.0                # where the next frame nominally starts in buf
        self.ref = None               # where the last frame's natural continuation starts in buf
        self.tail = np.zeros(self.hop)  # the second half of the last frame laid down, not yet complete

    def __call__(self, pcm):
        x = np.frombuffer(pcm, dtype=np.int16).astype(np.float64)
        self.buf = np.concatenate([self.buf, x])
        out = []
        while True:
            start = int(round(self.pos))
            lo, hi = max(0, start - self.tol), start + self.tol
            need = max(hi + self.n, (self.ref or 0) + self.n)
            if need > len(self.buf):
                break
            if self.ref is None:
                best = start
            else:
                ref = self.buf[self.ref:self.ref + self.n]
                region = self.buf[lo:hi + self.n]
                c = np.correlate(region, ref, "valid")
                sq = np.concatenate([[0.0], np.cumsum(region * region)])
                energy = np.sqrt(sq[self.n:] - sq[:-self.n]) + 1e-9  # of each candidate frame
                best = lo + int(np.argmax(c / energy))
            frame = self.buf[best:best + self.n] * self.win
            out.append(self.tail + frame[:self.hop])
            self.tail = frame[self.hop:].copy()
            self.ref = best + self.hop
            self.pos += self.hop * self.factor
        drop = max(0, min(int(self.pos) - self.tol, self.ref if self.ref is not None else 0))
        if drop:
            self.buf, self.pos, self.ref = self.buf[drop:], self.pos - drop, self.ref - drop
        return _pcm(np.concatenate(out)) if out else b""

    def flush(self):
        """The end of a piece: the rest of the input, then a fresh start for the next."""
        rest = self(np.zeros(self.n + 2 * self.tol, dtype=np.int16).tobytes()) + _pcm(self.tail)
        self._reset()
        return rest

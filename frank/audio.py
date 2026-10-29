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

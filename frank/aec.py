"""
Echo cancellation: WebRTC's audio processing (from LiveKit's Python package), so the
microphone stops hearing Frank's own voice from the speakers.

The voice player passes everything it plays to render(); the ears pass every microphone
chunk through capture(), which subtracts the echo (plus steady background noise). WebRTC
works in 10 ms frames, so leftovers are carried between calls. delay_ms is the time from
audio being handed to the speakers until it comes back in through the microphone: the
output and input buffer latencies (set from the real streams by set_delay()) plus a
little for the air and the drivers.
"""

import threading

_lock = threading.Lock()
_apm = None
_left = {"render": b"", "capture": b""}
delay_ms = 120
output_latency = 0.05  # set by the voice player from its stream


def available():
    try:
        from livekit import rtc  # noqa: F401
        return True
    except ImportError:
        return False


def _get():
    global _apm
    with _lock:
        if _apm is None:
            from livekit import rtc
            _apm = rtc.AudioProcessingModule(echo_cancellation=True, noise_suppression=True,
                                             high_pass_filter=True)
    return _apm


def set_delay(output_latency_s, input_latency_s):
    """WebRTC refuses delays over 500 ms ("Failed to set stream delay"), which the default
    (high-latency) audio streams exceeded at 776 ms; the streams now ask for low latency."""
    global delay_ms
    delay_ms = max(0, min(480, int((output_latency_s + input_latency_s) * 1000) + 20))


def _frames(kind, pcm, rate):
    from livekit import rtc
    step = rate // 100 * 2  # bytes in 10 ms of 16-bit mono
    data = _left[kind] + pcm
    whole = len(data) // step * step
    _left[kind] = data[whole:]
    for i in range(0, whole, step):
        yield rtc.AudioFrame(bytearray(data[i:i + step]), rate, 1, step // 2)


def render(pcm, rate):
    """Audio just sent to the speakers (the echo canceller's reference)."""
    apm = _get()
    for frame in _frames("render", pcm, rate):
        apm.process_reverse_stream(frame)


def capture(pcm, rate):
    """Microphone audio in, the same audio with Frank's echo removed out. The output is
    10 ms frames, so it can lag the input by up to 10 ms (the leftover)."""
    apm = _get()
    out = []
    for frame in _frames("capture", pcm, rate):
        apm.set_stream_delay_ms(delay_ms)
        apm.process_stream(frame)
        out.append(bytes(frame.data))
    return b"".join(out)

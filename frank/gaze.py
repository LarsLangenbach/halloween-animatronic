"""
Frank's eyes are alive the whole time he is on: they look around and blink, also while he
speaks. The same animation as the slider window's EYES ALIVE (firmware/eye_anim.py), run from
inside Frank instead of from the window, so nothing else has to hold the port and nothing
pauses it during a reply.

Gaze(mouth) starts a thread that steps the animation every 20 ms and sends each changed angle
to the eye board through the mouth board's link (Mouth.link: "e <pin> <angle>", D28). The
poses are the ones saved from the slider window (firmware/eye_poses.json: the lids' SHUT and
OPEN angles and the gaze CENTRE); a lid only ever moves between its SHUT and OPEN, so this can
never drive one past a pose set by hand. If a pose is missing the eyes stay still and Frank
says so: never guess an OPEN pose. stop() puts the eyes back to centre with the lids shut (the
neutral face), as STOP EYES does.

pause() holds the eyes centred with the lids at their OPEN pose, no looking around and no
blinking (for photographs, fitting the skin, setting the lids); alive() has them look around and
blink again. On the page: the Pause eyes and Eyes alive buttons; on the console: /eyes.

The mouth starts it itself (Mouth(eyes=True), the default), so `chat.py --mouth`, `web.py
--mouth` and `mouth.py --test / --say` all have the eyes alive; --still-eyes turns it off.
"""

import json
import os
import random
import sys
import threading
import time

HERE = os.path.dirname(os.path.abspath(__file__))
FIRMWARE = os.path.join(HERE, "..", "firmware")
if FIRMWARE not in sys.path:
    sys.path.insert(0, FIRMWARE)
from eye_anim import EyeAnim, TOP_LIDS, BOTTOM_LIDS  # noqa: E402  (plain Python, shared with the Pico)

POSES_FILE = os.path.join(FIRMWARE, "eye_poses.json")
# The eye board's sockets (firmware/README.md, "Eyes board 2"): LR, UD, then the lids.
PIN = {"LLL": 8, "LLR": 9, "CUL": 10, "CUR": 11, "CLL": 12, "CLR": 13}
LID_RANGE = (-9, 189)   # the slider window's lid range; the Pico program allows -27..207
TICK = 0.02             # s between animation steps, as the slider window


def load_poses():
    """The saved eye poses, or a ValueError naming what is missing."""
    if not os.path.exists(POSES_FILE):
        raise ValueError(f"no {POSES_FILE}: set the lid SHUT / OPEN and CENTRE poses in "
                         "firmware/servo_controls.py and save them")
    with open(POSES_FILE) as f:
        saved = json.load(f)
    missing = [k for k in ("shut", "open", "centre") if not saved.get(k)]
    if missing:
        raise ValueError(f"eye_poses.json has no {', '.join(missing).upper()} pose: save it in "
                         "firmware/servo_controls.py first")
    return saved


class Gaze:
    def __init__(self, mouth, log=None):
        self.mouth = mouth
        self.log = log or (lambda **k: None)
        poses = load_poses()
        self.anim = EyeAnim(poses["shut"], poses["open"], poses["centre"], time.monotonic())
        self.sent = {}
        self.lines = 0        # link lines sent, for the log
        self.paused = False   # pause(): held centred with the lids open, no blinking
        self.closed = False
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()
        self.log(what="eyes", state="alive", shut=poses["shut"], open=poses["open"], centre=poses["centre"])

    def _send(self, pose):
        for socket, a in pose.items():
            lo, hi = LID_RANGE if socket not in ("LLL", "LLR") else (0, 180)
            a = round(max(lo, min(hi, a)))
            if self.sent.get(socket) != a:
                self.mouth.link(f"{PIN[socket]} {a}")
                self.sent[socket] = a
                self.lines += 1

    def _run(self):
        while not self.closed:
            self._send(self.held() if self.paused else self.anim.step(time.monotonic()))
            time.sleep(TICK)

    @property
    def state(self):
        return "rest" if self.closed else "paused" if self.paused else "alive"

    def held(self):
        """The paused pose: centred, every lid exactly at its saved OPEN angle."""
        pose = self.anim.pose(0.0, 0.0, 1.0)
        pose.update({s: self.anim.open[s] for s in TOP_LIDS + BOTTOM_LIDS if s in self.anim.open})
        return pose

    def pause(self):
        """Hold the eyes open and still (centred, lids at OPEN, no blinks) until alive()."""
        if self.closed or self.paused:
            return self.state
        self.paused = True
        a = self.anim                  # so alive() starts from the centre, not the last glance
        a.start = a.target = (0.0, 0.0)
        a.move_time = 0.0
        a.blinks = []
        self.log(what="eyes", state="paused")
        return self.state

    def alive(self):
        """Look around and blink again, from the held pose (no re-opening from shut)."""
        if self.closed or not self.paused:
            return self.state
        t = time.monotonic()
        a = self.anim
        a.blinks = []
        a.next_look = t + random.uniform(0.5, 1.5)
        a.next_blink = t + random.uniform(1.0, 3.0)
        self.paused = False
        self.log(what="eyes", state="alive")
        return self.state

    def stop(self):
        """Centre the eyes and shut the lids (the neutral face); the servos keep holding."""
        if self.closed:
            return
        self.closed = True
        self.thread.join(TICK * 5)
        self._send(self.anim.rest())
        self.log(what="eyes", state="rest", lines=self.lines)

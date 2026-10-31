"""
The rig: the animator's joint channels to servo angles, and the one place that sends them
(docs/FACE_ENGINE.md, "Signal chain per channel"). Rig.apply(joints, t) returns
{socket: angle} for the ten eye-board servos and sends what changed.

The angles stay inside the poses saved on the slider window (firmware/eye_poses.json):
  - eyes:  LR = CENTRE + gaze_x_sign * gaze_x * LOOK_LR, UD = CENTRE + UD_UP * gaze_y * LOOK_UD
           (eye_anim.pose);
  - lids:  SHUT + openness * (OPEN - SHUT), per socket;
  - brows: LEVEL + dir * f * (raise if f > 0 else lower), brow_travel from the same file
           (brow_anim.angles).
The socket, pin and direction of every joint are in rig.json, with the checks to make on the
head; swap_brow_sides and swap_lid_sides turn a pair round in one line.

Sending (the writer is a mouth.Mouth): eye-board lines go through writer.link("<pin> <angle>")
(the mouth board forwards "e <pin> <angle>" over its UART, 115200 baud, PLAN D28), quantised to
quantum_deg and only when an angle moved by deadband_deg or more since it was last sent. Eyes
and lids go every tick, brows every brow_every ticks, and at most max_lines_per_tick lines a
tick, the largest change first; the rest wait for the next tick. smile, smile_asym and
jaw_floor go to writer.expression(smile, smile_asym, jaw_floor) when they change, if the writer
has it. writer=None sends nothing (the preview) but apply() still returns the angles.
"""

import json
import math
import os
import time

from .channels import JOINTS, rest_joints

HERE = os.path.dirname(os.path.abspath(__file__))
CONFIG = os.path.join(HERE, "rig.json")

# Used when eye_poses.json lacks a key: firmware/servo_controls.py's hand-set poses, 2026-10-29.
DEFAULT_POSES = {
    "shut": {"CUR": 183, "CLR": 134, "CUL": 108, "CLL": 117},
    "open": {"CUR": 139, "CLR": 188, "CUL": 143, "CLL": 53},
    "centre": {"LLL": 107, "LLR": 62},
    "level": {"JL": 90, "LUL": 90, "JR": 90, "LUR": 90},
    "brow_travel": {"raise": 35.0, "lower": 20.0},   # brow_anim.RAISE, LOWER
}
EXPRESSION_STEP = 0.01   # smile, smile_asym, jaw_floor: resend when one moves this much
REFRESH_S = 1.0          # s: a servo not sent for this long gets its angle again (the link is one way)
PAIRS = {"brow": (("brow_in_L", "brow_in_R"), ("brow_out_L", "brow_out_R")),
         "lid": (("lid_top_L", "lid_top_R"), ("lid_bot_L", "lid_bot_R"))}


def load(config=None):
    path = config or CONFIG
    with open(path, encoding="utf-8") as f:
        cfg = json.load(f)
    joints = {k: dict(v) for k, v in cfg["joints"].items()}
    for group, flag in (("brow", "swap_brow_sides"), ("lid", "swap_lid_sides")):
        if cfg.get(flag):
            for a, b in PAIRS[group]:
                joints[a], joints[b] = joints[b], joints[a]
    cfg["joints"] = joints
    poses = {k: dict(v) for k, v in DEFAULT_POSES.items()}
    ppath = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(path)), cfg["poses"]))
    if os.path.exists(ppath):
        with open(ppath, encoding="utf-8") as f:
            for k, v in json.load(f).items():
                if isinstance(v, dict):
                    poses.setdefault(k, {}).update(v)
    cfg["poses_file"] = ppath
    return cfg, poses


class Rig:
    def __init__(self, writer=None, config=None):
        self.writer = writer
        self.cfg, self.poses = load(config)
        c = self.cfg
        self.disabled = set(c.get("disabled", []))
        self.quantum = float(c.get("quantum_deg", 0.5))
        self.deadband = float(c.get("deadband_deg", 0.5))
        self.brow_every = max(1, int(c.get("brow_every", 2)))
        self.budget = max(1, int(c.get("max_lines_per_tick", 6)))
        self.lo, self.hi = c.get("angle_limits", (-27, 207))
        self.servos = {j: m for j, m in c["joints"].items() if m.get("board") == "eye"}
        self.socket_of = {j: m["socket"] for j, m in self.servos.items()}
        self.pin = {m["socket"]: m["pin"] for m in self.servos.values()}
        self.kind = {m["socket"]: m["kind"] for m in self.servos.values()}
        self.sent = {}            # socket -> angle last sent
        self.sent_at = {}         # socket -> when it was last sent (REFRESH_S)
        self.waiting = set()      # sockets that changed but did not fit in the last tick's budget
        self.expr_sent = None
        self.ticks = 0
        self.lines = 0            # lines sent so far (for the log and tests)

    def angles(self, joints):
        """{socket: angle} for the eye-board servos, unquantised, inside the saved poses."""
        c, p = self.cfg, self.poses
        rest = rest_joints()
        out = {}
        for j, m in self.servos.items():
            lo, hi, _ = JOINTS[j]
            v = joints.get(j, rest[j])
            v = lo if v < lo else hi if v > hi else v
            s, kind = m["socket"], m["kind"]
            if kind == "look_lr":
                a = p["centre"][s] + c.get("gaze_x_sign", 1) * v * c.get("LOOK_LR", 30)
            elif kind == "look_ud":
                a = p["centre"][s] + c.get("UD_UP", 1) * v * c.get("LOOK_UD", 15)
            elif kind == "lid":
                a = p["shut"][s] + v * (p["open"][s] - p["shut"][s])
            else:   # brow
                travel = p["brow_travel"]
                a = p["level"][s] + m.get("dir", 1) * v * (travel["raise"] if v > 0 else travel["lower"])
            out[s] = min(self.hi, max(self.lo, a))
        return out

    def quantise(self, a):
        q = round(a / self.quantum) * self.quantum
        return float(q)

    def apply(self, joints, t=None):
        ang = self.angles(joints)
        q = {s: self.quantise(a) for s, a in ang.items()}
        if self.writer is None:
            return q
        brow_tick = self.ticks % self.brow_every == 0
        due = []
        for s, a in ang.items():
            if s in self.disabled:
                continue
            if self.kind[s] == "brow" and not brow_tick and s not in self.waiting:
                continue
            last = self.sent.get(s)
            if last is None or abs(a - last) >= self.deadband:
                due.append((math.inf if last is None else abs(a - last), s))
        due.sort(reverse=True)
        now = time.monotonic() if t is None else t
        if len(due) < self.budget:
            # the link is one way: a lost line stays wrong, so one servo a tick that hasn't been
            # sent for REFRESH_S gets its angle again (all ten about once a second)
            stale = [(now - self.sent_at.get(s, -math.inf), s) for s in ang
                     if s not in self.disabled and s in self.sent and s not in {x for _, x in due}]
            stale = [x for x in stale if x[0] >= REFRESH_S]
            if stale:
                due.append((0.0, max(stale)[1]))
        for _, s in due[:self.budget]:
            self.writer.link(f"{self.pin[s]} {q[s]:g}")
            self.sent[s] = q[s]
            self.sent_at[s] = now
            self.lines += 1
        self.waiting = {s for _, s in due[self.budget:]}
        if brow_tick and hasattr(self.writer, "expression"):
            e = tuple(joints.get(k, 0.0) for k in ("smile", "smile_asym", "jaw_floor"))
            if self.expr_sent is None or max(abs(a - b) for a, b in zip(e, self.expr_sent)) >= EXPRESSION_STEP:
                self.writer.expression(*e)
                self.expr_sent = e
        self.ticks += 1
        return q

    def rest(self, pause=None):
        """Eyes centred, lids at rest, brows level, mouth neutral: one servo at a time."""
        pause = self.cfg.get("rest_pause", 0.12) if pause is None else pause
        q = {s: self.quantise(a) for s, a in self.angles(rest_joints()).items()}
        if self.writer is None:
            return q
        for s, a in q.items():
            if s in self.disabled:
                continue
            self.writer.link(f"{self.pin[s]} {a:g}")
            self.sent[s] = a
            self.sent_at[s] = time.monotonic()
            self.lines += 1
            if pause:
                time.sleep(pause)   # so they don't all start together on the supply
        self.waiting = set()
        if hasattr(self.writer, "expression"):
            self.writer.expression(0.0, 0.0, 0.0)
            self.expr_sent = (0.0, 0.0, 0.0)
        return q

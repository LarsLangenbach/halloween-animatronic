"""
The Constraints page: the robot's degrees of freedom, read from its files, and the limits the
animation runs inside. Two levels, both editable, both applied to the running engine at once:

  servos     the hardware: each servo's board, pin, type, what it moves in the CAD rig (and
             which servos share a body), the range its board program allows, its soft limits
             (robot.json `soft`, kept there for every tool) and its speed.
  channels   the animation: the face engine's joint channels (frank/engine/channels.py), each
             with its range and rest, how smoothly it moves (spring half-life) and how fast
             (speed cap), the servo angles it reaches, and the travels that turn it into degrees
             (gaze LOOK_LR and LOOK_UD, brow raise and lower).

Channel and speed edits are the studio's own (robots/<name>/studio/constraints.json); they patch
the engine's tables in this process only, so Frank's own runs are unchanged until someone copies
a value into the engine. Soft limits go into robot.json, merged like the twin's calibration save.
"""

import json
import os
from pathlib import Path

from engine import animator as AN
from engine import channels as CH

FORMAT = "studio-constraints/1"

LABELS = {
    "gaze_x": ("Eyes left / right", "eyes", "-1 his right, +1 his left"),
    "gaze_y": ("Eyes up / down", "eyes", "-1 down, +1 up"),
    "lid_top_L": ("Upper lid, his left", "lids", "0 shut, 1 open"),
    "lid_top_R": ("Upper lid, his right", "lids", "0 shut, 1 open"),
    "lid_bot_L": ("Lower lid, his left", "lids", "1 down (open), lower = squint"),
    "lid_bot_R": ("Lower lid, his right", "lids", "1 down (open), lower = squint"),
    "brow_in_L": ("Brow inner end, his left", "brows", "-1 lowered, +1 raised"),
    "brow_out_L": ("Brow outer end, his left", "brows", "-1 lowered, +1 raised"),
    "brow_in_R": ("Brow inner end, his right", "brows", "-1 lowered, +1 raised"),
    "brow_out_R": ("Brow outer end, his right", "brows", "-1 lowered, +1 raised"),
    "smile": ("Smile / frown", "mouth", "-1 frown, +1 smile"),
    "smile_asym": ("One-sided smile", "mouth", "+ his left corner more"),
    "jaw_floor": ("Jaw held open", "mouth", "0 closed, 1 open (speech can open it more)"),
}
MOUTH_SERVOS = {"smile": ("CUL", "CUR", "CLL", "CLR"), "smile_asym": ("CUL", "CUR", "CLL", "CLR"),
                "jaw_floor": ("JL", "JR")}   # through frank/mouth.py, not the engine's rig
TRAVEL = {"LOOK_LR": "Eyes: degrees of servo travel at gaze_x = 1",
          "LOOK_UD": "Eyes: degrees of servo travel at gaze_y = 1",
          "brow_raise": "Brows: degrees a brow end turns at +1",
          "brow_lower": "Brows: degrees a brow end turns at -1"}
CONTRACT = {k: tuple(v) for k, v in CH.JOINTS.items()}   # the engine's own ranges, before any edit
DEFAULT_HL = dict(AN.HALF_LIFE)
DEFAULT_CAP = dict(AN.SPEED_CAP)


def path_for(robot):
    return Path(robot.path).parent / "studio" / "constraints.json"


def load(robot):
    p = path_for(robot)
    if p.exists():
        try:
            doc = json.loads(p.read_text(encoding="utf-8"))
            if doc.get("format") == FORMAT:
                return doc
        except ValueError:
            pass
    return {"format": FORMAT, "channels": {}, "travel": {}, "servos": {}}


def save(robot, doc):
    p = path_for(robot)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(doc, indent=1) + "\n", encoding="utf-8")
    os.replace(tmp, p)


def _num(x, lo=None, hi=None):
    x = float(x)
    if x != x or x in (float("inf"), float("-inf")):
        raise ValueError("not a number")
    if lo is not None:
        x = max(lo, x)
    if hi is not None:
        x = min(hi, x)
    return x


# ---------------------------------------------------------------------------------- the rig
def rig_bodies(robot):
    """{servo: [bodies it moves]} and {body: [servos]} from the twin's rig (perform-rig/1)."""
    rp = robot.file("rig")
    if not rp or not rp.exists():
        return {}, {}
    rig = json.loads(rp.read_text(encoding="utf-8"))
    pts = rig.get("points", {})
    bodies = {b["name"]: b for b in rig.get("bodies", [])}

    def deps(pid, seen=()):
        p = pts.get(pid) or {}
        if "on" in p:
            return {p["on"]}
        out = set()
        for q in p.get("dyad", []):
            if q not in seen:
                out |= deps(q, seen + (pid,))
        return out

    by_servo = {}
    for name, b in bodies.items():          # in solve order: horns first, then what they drive
        m = b.get("motion", {})
        if m.get("type") == "revolute":
            sids = {s["id"] for s in m.get("servos", [])}
        else:   # a link hangs on two pins; a bend spans two bodies
            needs = (deps(m.get("a")) | deps(m.get("b")) if m.get("type") == "link"
                     else {m.get("a"), m.get("b")} if m.get("type") == "bend" else set())
            sids = {sid for sid, got in by_servo.items() if needs & set(got)}
        for sid in sids:
            by_servo.setdefault(sid, []).append(name)
    by_body = {}
    for sid, names in by_servo.items():
        for n in names:
            by_body.setdefault(n, []).append(sid)
    roles = {n: b.get("role") for n, b in bodies.items()}
    shown = {sid: [n for n in names if roles.get(n) not in ("horn", "link")] or names
             for sid, names in by_servo.items()}
    return shown, by_body


# ---------------------------------------------------------------------------------- read
def describe(rt):
    robot, rig = rt.robot, rt.engine.rig
    doc = load(robot)
    eye_servo = {m["socket"]: robot.by_pin.get(("eyes", m["pin"])) for m in rig.servos.values()}
    moves, by_body = rig_bodies(robot)

    channels, used = [], {}
    rest = CH.rest_joints()
    for name, (lo, hi, r) in CH.JOINTS.items():
        label, group, meaning = LABELS.get(name, (name, "other", ""))
        servos = []
        if name in rig.servos:
            sock = rig.servos[name]["socket"]
            at = [round(rig.angles({**rest, name: v})[sock], 1) for v in (lo, r, hi)]
            sid = eye_servo.get(sock)
            servos.append({"id": sid, "at": at})
            u = used.setdefault(sid, [min(at), max(at)])
            u[0], u[1] = min(u[0], *at), max(u[1], *at)
        else:
            servos += [{"id": sid, "at": None} for sid in MOUTH_SERVOS.get(name, ())]
        travel = ("LOOK_LR" if name == "gaze_x" else "LOOK_UD" if name == "gaze_y"
                  else "brow" if name.startswith("brow") else "poses" if name.startswith("lid") else None)
        channels.append({
            "name": name, "label": label, "group": group, "meaning": meaning,
            "low": lo, "high": hi, "rest": r, "contract": CONTRACT[name],
            "half_life": AN.HALF_LIFE.get(name), "speed_cap": AN.SPEED_CAP.get(name),
            "defaults": {"half_life": DEFAULT_HL.get(name), "speed_cap": DEFAULT_CAP.get(name)},
            "servos": servos, "travel": travel, "held": rt.channel_hold.get(name),
            "edited": name in doc["channels"],
        })

    servos = []
    types = robot.spec.get("servo_types", {})
    for sid, s in robot.servos.items():
        fw = robot.firmware_range(sid)
        coupled = sorted({o for b in moves.get(sid, []) for o in by_body.get(b, []) if o != sid})
        servos.append({
            "id": sid, "label": s.get("label", sid), "board": s["board"], "pin": s["pin"],
            "type": s.get("type"), "zero": s.get("zero"), "sign": s.get("sign", 1),
            "speed": round(robot.speed[sid], 1),
            "speed_default": types.get(s.get("type", ""), {}).get("deg_per_s", 500.0),
            "firmware": list(fw), "soft": list(robot.soft[sid]), "used": used.get(sid),
            "moves": moves.get(sid, []), "coupled": coupled, "held": robot.hold.get(sid),
            "edited": bool(s.get("soft")) or sid in doc["servos"],
        })

    p = rig.poses
    travel = {"LOOK_LR": rig.cfg.get("LOOK_LR", 30), "LOOK_UD": rig.cfg.get("LOOK_UD", 15),
              "brow_raise": p["brow_travel"]["raise"], "brow_lower": p["brow_travel"]["lower"]}
    bodies = sorted({b for names in moves.values() for b in names})
    return {
        "robot": robot.spec.get("name"), "about": robot.spec.get("about"),
        "boards": {n: {"firmware": b.get("firmware"), "label": b.get("label"), "via": b.get("via")}
                   for n, b in robot.spec.get("boards", {}).items()},
        "channels": channels, "servos": servos,
        "travel": travel, "travel_doc": TRAVEL,
        "poses": {k: p.get(k) for k in ("open", "shut", "centre", "level")},
        "summary": {"servos": len(servos), "channels": len(channels), "bodies": len(bodies),
                    "coupled": sum(1 for s in servos if s["coupled"])},
        "saved": str(path_for(robot).relative_to(Path(robot.path).parent.parent.parent)).replace("\\", "/"),
    }


# ---------------------------------------------------------------------------------- write
def apply_doc(rt, doc):
    """Put a constraints document into the running engine and the body (the caller holds the lock)."""
    for name, c in doc.get("channels", {}).items():
        if name not in CH.JOINTS:
            continue
        lo0, hi0, r0 = CONTRACT[name]
        lo = _num(c.get("low", lo0), lo0, hi0)
        hi = _num(c.get("high", hi0), lo, hi0)
        CH.JOINTS[name] = (lo, hi, _num(c.get("rest", r0), lo, hi))
        if "half_life" in c and name in DEFAULT_HL:
            AN.HALF_LIFE[name] = _num(c["half_life"], 0.0, 2.0)
        if "speed_cap" in c and name in DEFAULT_CAP:
            AN.SPEED_CAP[name] = _num(c["speed_cap"], 0.1, 100.0)
    rig, t = rt.engine.rig, doc.get("travel", {})
    if "LOOK_LR" in t:
        rig.cfg["LOOK_LR"] = _num(t["LOOK_LR"], 0, 60)
    if "LOOK_UD" in t:
        rig.cfg["LOOK_UD"] = _num(t["LOOK_UD"], 0, 45)
    if "brow_raise" in t:
        rig.poses["brow_travel"]["raise"] = _num(t["brow_raise"], 0, 60)
    if "brow_lower" in t:
        rig.poses["brow_travel"]["lower"] = _num(t["brow_lower"], 0, 60)
    for sid, s in doc.get("servos", {}).items():
        if sid in rt.robot.servos and "speed" in s:
            rt.robot.speed[sid] = _num(s["speed"], 5, 2000)


def startup(rt):
    """Keep the engine's own travels (for Reset), then apply the saved constraints."""
    rig = rt.engine.rig
    rt.travel_default = {"LOOK_LR": rig.cfg.get("LOOK_LR", 30), "LOOK_UD": rig.cfg.get("LOOK_UD", 15),
                         "brow_raise": rig.poses["brow_travel"]["raise"],
                         "brow_lower": rig.poses["brow_travel"]["lower"]}
    with rt.lock:
        apply_doc(rt, load(rt.robot))


def edit(rt, change):
    """One edit from the page: {"channel": name, "field": low|high|rest|half_life|speed_cap, "value"},
    {"travel": key, "value"}, {"servo": id, "field": soft|speed, "value"}, or {"reset": channel|servo id}."""
    robot = rt.robot
    with rt.lock:
        doc = load(robot)
        if "channel" in change:
            name, field = change["channel"], change["field"]
            if name not in CH.JOINTS or field not in ("low", "high", "rest", "half_life", "speed_cap"):
                raise ValueError("unknown channel or field")
            doc["channels"].setdefault(name, {})[field] = _num(change["value"])
        elif "travel" in change:
            if change["travel"] not in TRAVEL:
                raise ValueError("unknown travel")
            doc["travel"][change["travel"]] = _num(change["value"])
        elif "servo" in change:
            sid, field = change["servo"], change["field"]
            if sid not in robot.servos:
                raise ValueError("unknown servo")
            if field == "speed":
                doc["servos"].setdefault(sid, {})["speed"] = _num(change["value"], 5, 2000)
            elif field == "soft":
                lo, hi = robot.firmware_range(sid)
                a, b = sorted(_num(v, lo, hi) for v in change["value"])
                robot.soft[sid] = (a, b)
                write_soft(robot, {sid: None if (a, b) == (lo, hi) else [round(a, 1), round(b, 1)]})
            else:
                raise ValueError("unknown field")
        elif "reset" in change:
            k = change["reset"]
            if k in CH.JOINTS:
                doc["channels"].pop(k, None)
                CH.JOINTS[k] = CONTRACT[k]
                if k in DEFAULT_HL:
                    AN.HALF_LIFE[k] = DEFAULT_HL[k]
                if k in DEFAULT_CAP:
                    AN.SPEED_CAP[k] = DEFAULT_CAP[k]
            elif k in robot.servos:
                doc["servos"].pop(k, None)
                types = robot.spec.get("servo_types", {})
                robot.speed[k] = types.get(robot.servos[k].get("type", ""), {}).get("deg_per_s", 500.0)
                robot.soft[k] = robot.firmware_range(k)
                write_soft(robot, {k: None})
            elif k == "travel":
                doc["travel"] = {}
                apply_doc(rt, {"travel": rt.travel_default})
        else:
            raise ValueError("nothing to change")
        apply_doc(rt, doc)
        save(robot, doc)


def write_soft(robot, changes):
    """{servo: [min, max] or None} into robot.json's servos, keeping everything else as it is."""
    p = Path(robot.path)
    spec = json.loads(p.read_text(encoding="utf-8"))
    for sid, v in changes.items():
        if v is None:
            spec["servos"][sid].pop("soft", None)
        else:
            spec["servos"][sid]["soft"] = v
    tmp = p.with_suffix(".tmp")
    tmp.write_text(dumps_compact(spec), encoding="utf-8")
    os.replace(tmp, p)
    robot.spec, robot.servos = spec, spec["servos"]


def dumps_compact(spec):
    """robot.json in its hand-kept layout: one key a line, and each board, servo type and servo
    on a line of its own, so a changed limit is a one-line diff."""
    out = []
    for k, v in spec.items():
        if isinstance(v, dict) and v and all(isinstance(x, dict) for x in v.values()):
            pad = max(len(json.dumps(n)) for n in v) + 1 if k == "servos" else 0   # servo ids line up
            rows = [f"  {(json.dumps(n, ensure_ascii=False) + ':').ljust(pad)} {json.dumps(x, ensure_ascii=False)}"
                    for n, x in v.items()]
            out.append(f" {json.dumps(k)}: {{\n" + ",\n".join(rows) + "\n }")
        else:
            out.append(f" {json.dumps(k)}: {json.dumps(v, ensure_ascii=False)}")
    return "{\n" + ",\n".join(out) + "\n}\n"

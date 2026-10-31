"""
The studio's routes without a server: Studio(rt).get(path) and .post(path, body) return
(status, data), or None for a path they don't know. app.py serves them over HTTP; the online
site (studio/online) runs them in the browser with Pyodide, the way frank/online does.

    /engine/...        preview.Api's routes: /meta /snapshot /tag /event /steer /play /stop,
                       and /animate (Claude writes a performance; the examples need no key)
    /s/status          everything the page polls
    /s/robots          Frank, the other onboarded robots, whether Claude is available
    /s/constraints     GET the degrees of freedom; POST one edit
    /s/hold            a try slider: {servo, deg} | {channel, value} | {clear}
    /s/library[/id/rename|delete|play]
    /s/machines, /s/machine/<name>[/save|delete]
    /s/run/start|stop|event|goto
"""

import runtime as R
import constraints as C
import library as L
import machine as M


class Studio:
    def __init__(self, rt, robot_dir, seed, others=lambda: [], online=False):
        self.rt, self.online, self.others = rt, online, others
        self.lib = L.Library(robot_dir, seed=seed)
        self.machines = M.Store(robot_dir)
        self.runner = M.Runner(rt, self.lib)
        rt.on_tick.append(self.runner.step)
        C.startup(rt)

    def status(self):
        rt = self.rt
        with rt.lock:
            code, snap = rt.api.get("/snapshot")
            frame = rt.robot.frame()
        return {"snapshot": R.B.P.clean(snap) if code == 200 else None,
                "runner": self.runner.status(),
                "head": rt.head.status() if rt.head else None,
                "servos": {sid: {"deg": s["deg"], "clamped": s.get("clamped"), "held": s.get("held")}
                           for sid, s in frame["servos"].items()}}

    # ------------------------------------------------------------------------------ GET
    def get(self, path):
        rt = self.rt
        if path.startswith("/engine/"):
            with rt.lock:
                got = rt.api.get(path[len("/engine"):])
            return (got[0], R.B.P.clean(got[1])) if got else None
        if not path.startswith("/s/"):
            return None
        parts = path[3:].split("/")
        if parts == ["status"]:
            return 200, self.status()
        if parts == ["robots"]:
            spec = rt.robot.spec
            return 200, {"frank": {"name": spec.get("name"), "about": spec.get("about"),
                                   "servos": len(rt.robot.servos), "boards": len(spec.get("boards", {}))},
                         "others": [r for r in self.others() if r.get("name") != "frank"],
                         "key": False if self.online else R.key_available(), "online": self.online}
        if parts == ["constraints"]:
            with rt.lock:
                return 200, C.describe(rt)
        if parts == ["library"]:
            return 200, {"animations": self.lib.all()}
        if parts == ["machines"]:
            return 200, {"names": self.machines.names()}
        if len(parts) == 2 and parts[0] == "machine":
            m = self.machines.get(parts[1])
            if m is None:
                return 404, {"error": "no such machine"}
            return 200, {"machine": m, "problems": M.clean(m)[1]}
        return None

    # ------------------------------------------------------------------------------ POST
    def post(self, path, body):
        try:
            if path.startswith("/engine/"):
                return self._engine(path[len("/engine"):], body)
            if path.startswith("/s/"):
                return self._studio(path[3:].split("/"), body)
        except (KeyError, ValueError, TypeError) as e:
            return 400, {"ok": False, "why": str(e)}
        return None

    def _engine(self, path, body):
        """Playing anything by hand stops the state machine, so the two never fight over the face."""
        rt, runner = self.rt, self.runner
        if path == "/animate":
            prompt = str(body.get("prompt") or "").strip()
            if not prompt:
                raise ValueError("write what he does")
            try:
                anim, note = rt.generate(prompt)              # ~10 s, outside the lock
            except RuntimeError as e:
                why = ("Online, only the examples play: a new performance needs Claude, which runs in "
                       "the laptop app.") if self.online else str(e)
                return 400, {"ok": False, "why": why}
            with rt.lock:
                runner.stop("stopped: a new animation played")
                code, out = rt.play(anim)
            return code, dict(R.B.P.clean(out), note=note)
        with rt.lock:
            if path in ("/play", "/tag", "/steer") and runner.running:
                runner.stop("stopped: the studio took the face")
            got = rt.api.post(path, body)
        return (got[0], R.B.P.clean(got[1])) if got else None

    def _studio(self, parts, body):
        rt, runner, lib, machines = self.rt, self.runner, self.lib, self.machines
        if parts == ["constraints"]:
            C.edit(rt, body)
            with rt.lock:
                return 200, C.describe(rt)
        if parts == ["hold"]:
            with rt.lock:
                if body.get("clear"):
                    rt.robot.hold.clear()
                    rt.channel_hold.clear()
                elif "servo" in body:
                    sid = body["servo"]
                    if sid not in rt.robot.servos:
                        raise ValueError("unknown servo")
                    if body.get("deg") is None:
                        rt.robot.hold.pop(sid, None)
                    else:
                        lo, hi = rt.robot.firmware_range(sid)
                        rt.robot.hold[sid] = max(lo, min(hi, float(body["deg"])))
                        if rt.head:
                            rt.head.servo(sid, rt.robot.hold[sid])
                elif "channel" in body:
                    ch = body["channel"]
                    if ch not in C.CH.JOINTS:
                        raise ValueError("unknown channel")
                    if body.get("value") is None:
                        rt.channel_hold.pop(ch, None)
                    else:
                        rt.channel_hold[ch] = float(body["value"])
            return 200, {"ok": True}
        if parts == ["library"]:
            return 200, {"ok": True, "entry": lib.save(body)}
        if len(parts) == 3 and parts[0] == "library":
            aid, what = parts[1], parts[2]
            if what == "rename":
                return 200, {"ok": True, "entry": lib.rename(aid, body.get("title", ""))}
            if what == "delete":
                lib.delete(aid)
                return 200, {"ok": True}
            if what == "play":
                e = lib.get(aid)
                if not e:
                    raise KeyError(aid)
                with rt.lock:
                    runner.stop("stopped: the studio took the face")
                    code, out = rt.play(e["anim"])
                return code, R.B.P.clean(out)
        if len(parts) == 3 and parts[0] == "machine":
            name, what = parts[1], parts[2]
            if what == "save":
                m, problems = machines.put(name, body.get("machine") or {})
                return 200, {"ok": True, "machine": m, "problems": problems}
            if what == "delete":
                machines.delete(name)
                return 200, {"ok": True}
        if parts == ["run", "start"]:
            with rt.lock:
                runner.start(body.get("machine") or {}, at=body.get("at"))
            return 200, {"ok": True, "runner": runner.status()}
        if parts == ["run", "stop"]:
            with rt.lock:
                runner.stop()
                if rt.player:
                    rt.player.stop()
            return 200, {"ok": True}
        if parts == ["run", "event"]:
            with rt.lock:
                fired = runner.event(str(body.get("name", "")))
            return 200, {"ok": True, "fired": fired}
        if parts == ["run", "goto"]:
            with rt.lock:
                runner.goto(body.get("state"))
            return 200, {"ok": True}
        return None

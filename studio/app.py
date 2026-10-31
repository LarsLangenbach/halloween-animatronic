"""
The animatronic studio: one local app for the whole job, in four steps.

    1 Model          use Frank's CAD, or upload your own (STEP, STL, OBJ, 3MF, GLB, PLY)
    2 Constraints    the degrees of freedom read from the robot's files: servos, what each one
                     moves, limits, speeds, and the animation channels; edit them and the
                     animation runs inside them at once
    3 Animation      the emotion synthesiser (the emotion map, tags, events), prompt to
                     animation, recording, and the library of saved animations
    4 State machine  states as nodes joined by arrows; each state plays one of its animations

    .venv\\Scripts\\python.exe studio\\app.py --open           (http://localhost:8840)

Frank's face engine runs inside this process on perform/body.py's board models (no head, no
serial port: the 3D twin is the body), as the public site runs it in a browser. Writing an
animation from a prompt needs ANTHROPIC_API_KEY in frank/.env; without it the site's three
pre-written examples still play. An uploaded robot goes through perform/onboard (mounted here at
/onboard/), which converts the CAD and rigs it; the engine's animation pages run on Frank.

Local only: it answers localhost and nothing else. Ports in use elsewhere: web.py 8800, the body
twin 8810/8811, the engine preview and onboarding 8820, the statechart editor 8830.
"""

import argparse
import json
import sys
import time
import traceback
import webbrowser
from http.server import ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "perform" / "onboard"))

import server as onboard  # noqa: E402   (perform/onboard's Handler, its workspaces and its pool)
import runtime as R  # noqa: E402   (Frank's engine and board models; imports frank/online/browser.py)
import constraints as C  # noqa: E402
import library as L  # noqa: E402
import machine as M  # noqa: E402

WEB = HERE / "web"
ONBOARD_WEB = ROOT / "perform" / "onboard" / "web"
KINDS = {".js": "text/javascript; charset=utf-8", ".css": "text/css; charset=utf-8",
         ".html": "text/html; charset=utf-8", ".json": "application/json", ".svg": "image/svg+xml"}
FRAME_S = 1 / 30

rt = R.Runtime()
ROBOT_DIR = Path(rt.robot.path).parent
lib = L.Library(ROBOT_DIR, seed=ROOT / "frank" / "online" / "performances.json")
machines = M.Store(ROBOT_DIR)
runner = M.Runner(rt, lib)
rt.on_tick.append(runner.step)
C.startup(rt)


def status():
    """Everything the page polls: the engine, the performance, the state machine, the servos."""
    with rt.lock:
        code, snap = rt.api.get("/snapshot")
        frame = rt.robot.frame()
    return {"snapshot": R.B.P.clean(snap) if code == 200 else None,
            "runner": runner.status(),
            "servos": {sid: {"deg": s["deg"], "clamped": s.get("clamped"), "held": s.get("held")}
                       for sid, s in frame["servos"].items()}}


class Handler(onboard.Handler):
    """The studio's routes first; everything else is perform/onboard's (its /api/..., /web/...
    and /twin/...), so its page works here at /onboard/."""

    def _static_file(self, f):
        if f.is_file():
            return self._send(200, f.read_bytes(), KINDS.get(f.suffix, "application/octet-stream"))
        self._send(404, b"not found", "text/plain")

    def do_GET(self):
        if not self._local():
            return
        p = urlparse(self.path).path
        try:
            if p in ("/", "/index.html"):
                return self._static_file(WEB / "index.html")
            if p.startswith("/studio/"):
                f = (WEB / p[len("/studio/"):]).resolve()
                return self._static_file(f) if WEB in f.parents else self._send(404, b"", "text/plain")
            if p in ("/onboard", "/onboard/"):
                return self._static_file(ONBOARD_WEB / "index.html")
            if p in ("/robot", "/rig", "/camera", "/model"):   # the twin page's data (perform/twin)
                got = rt.twin_file(p[1:])
                return self._send(200, *got) if got else self._send(404, b"", "text/plain")
            if p == "/events":
                return self._events()
            if p.startswith("/engine/"):
                with rt.lock:
                    got = rt.api.get(p[len("/engine"):])
                return self._json(R.B.P.clean(got[1]), got[0]) if got else self._send(404, b"", "text/plain")
            if p.startswith("/s/"):
                return self._studio_get(p[3:].split("/"))
        except Exception as e:                                   # noqa: BLE001
            traceback.print_exc()
            return self._json({"error": f"{type(e).__name__}: {e}"}, 500)
        return super().do_GET()

    def do_POST(self):
        if not self._local():
            return
        p = urlparse(self.path).path
        if not (p.startswith("/s/") or p.startswith("/engine/")):
            return super().do_POST()
        if self.headers.get("X-Studio") != "1":                 # a page on another site can't set it
            return self._send(403, b"studio pages only", "text/plain")
        try:
            body = json.loads(self._body() or b"{}")
            if not isinstance(body, dict):
                raise ValueError("send an object")
            if p.startswith("/engine/"):
                return self._engine_post(p[len("/engine"):], body)
            return self._studio_post([unquote(x) for x in p[3:].split("/")], body)
        except (KeyError, ValueError, TypeError) as e:
            return self._json({"ok": False, "why": str(e)}, 400)
        except Exception as e:                                   # noqa: BLE001
            traceback.print_exc()
            return self._json({"ok": False, "why": f"{type(e).__name__}: {e}"}, 500)

    # ------------------------------------------------------------------------------ the twin
    def _events(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        try:
            while True:
                self.wfile.write(b"data: " + json.dumps(rt.body_frame()).encode() + b"\n\n")
                self.wfile.flush()
                time.sleep(FRAME_S)
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError, OSError):
            pass

    # ------------------------------------------------------------------------------ the engine
    def _engine_post(self, path, body):
        """preview.Api's routes (/tag /event /steer /play /stop ...). Playing anything by hand
        stops the state machine, so the two never fight over the face."""
        if path == "/animate":
            prompt = str(body.get("prompt") or "").strip()
            if not prompt:
                raise ValueError("write what he does")
            try:
                anim, note = rt.generate(prompt)              # ~10 s, outside the lock
            except RuntimeError as e:
                return self._json({"ok": False, "why": str(e)}, 400)
            with rt.lock:
                runner.stop("stopped: a new animation played")
                code, out = rt.play(anim)
            return self._json(dict(out, note=note), code)
        with rt.lock:
            if path in ("/play", "/tag", "/steer") and runner.running:
                runner.stop("stopped: the studio took the face")
            got = rt.api.post(path, body)
        if got is None:
            return self._send(404, b"not found", "text/plain")
        return self._json(R.B.P.clean(got[1]), got[0])

    # ------------------------------------------------------------------------------ studio
    def _studio_get(self, parts):
        if parts == ["status"]:
            return self._json(status())
        if parts == ["robots"]:
            others = [r for r in onboard.W.list_robots() if r.get("name") != "frank"]
            return self._json({"frank": {"name": rt.robot.spec.get("name"), "about": rt.robot.spec.get("about"),
                                         "servos": len(rt.robot.servos), "boards": len(rt.robot.spec.get("boards", {}))},
                               "others": others, "key": R.key_available()})
        if parts == ["constraints"]:
            with rt.lock:
                return self._json(C.describe(rt))
        if parts == ["library"]:
            return self._json({"animations": lib.all()})
        if parts == ["machines"]:
            return self._json({"names": machines.names()})
        if len(parts) == 2 and parts[0] == "machine":
            m = machines.get(unquote(parts[1]))
            if m is None:
                return self._json({"error": "no such machine"}, 404)
            return self._json({"machine": m, "problems": M.clean(m)[1]})
        return self._send(404, b"not found", "text/plain")

    def _studio_post(self, parts, body):
        if parts == ["constraints"]:
            C.edit(rt, body)
            with rt.lock:
                return self._json(C.describe(rt))
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
                elif "channel" in body:
                    ch = body["channel"]
                    if ch not in C.CH.JOINTS:
                        raise ValueError("unknown channel")
                    if body.get("value") is None:
                        rt.channel_hold.pop(ch, None)
                    else:
                        rt.channel_hold[ch] = float(body["value"])
            return self._json({"ok": True})
        if parts == ["library"]:
            return self._json({"ok": True, "entry": lib.save(body)})
        if len(parts) == 3 and parts[0] == "library":
            aid, what = parts[1], parts[2]
            if what == "rename":
                return self._json({"ok": True, "entry": lib.rename(aid, body.get("title", ""))})
            if what == "delete":
                lib.delete(aid)
                return self._json({"ok": True})
            if what == "play":
                e = lib.get(aid)
                if not e:
                    raise KeyError(aid)
                with rt.lock:
                    runner.stop("stopped: the studio took the face")
                    code, out = rt.play(e["anim"])
                return self._json(R.B.P.clean(out), code)
        if len(parts) == 3 and parts[0] == "machine":
            name, what = parts[1], parts[2]
            if what == "save":
                m, problems = machines.put(name, body.get("machine") or {})
                return self._json({"ok": True, "machine": m, "problems": problems})
            if what == "delete":
                machines.delete(name)
                return self._json({"ok": True})
        if parts == ["run", "start"]:
            with rt.lock:
                runner.start(body.get("machine") or {}, at=body.get("at"))
            return self._json({"ok": True, "runner": runner.status()})
        if parts == ["run", "stop"]:
            with rt.lock:
                runner.stop()
                if rt.player:
                    rt.player.stop()
            return self._json({"ok": True})
        if parts == ["run", "event"]:
            with rt.lock:
                fired = runner.event(str(body.get("name", "")))
            return self._json({"ok": True, "fired": fired})
        if parts == ["run", "goto"]:
            with rt.lock:
                runner.goto(body.get("state"))
            return self._json({"ok": True})
        return self._send(404, b"not found", "text/plain")


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--port", type=int, default=8840)
    ap.add_argument("--open", action="store_true", help="open the page in the browser")
    a = ap.parse_args()
    rt.start()
    srv = ThreadingHTTPServer(("127.0.0.1", a.port), Handler)
    srv.daemon_threads = True
    url = f"http://localhost:{a.port}"
    print(f"studio on {url}  (prompt to animation {'on' if R.key_available() else 'off: no key in frank/.env'})")
    if a.open:
        webbrowser.open(url)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        rt.stop()


if __name__ == "__main__":
    main()

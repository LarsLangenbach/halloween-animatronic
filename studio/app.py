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
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "perform" / "onboard"))

import runtime as R  # noqa: E402   (Frank's engine and board models; imports frank/online/browser.py)
import routes  # noqa: E402

WEB = HERE / "web"
ONBOARD_WEB = ROOT / "perform" / "onboard" / "web"
KINDS = {".js": "text/javascript; charset=utf-8", ".css": "text/css; charset=utf-8",
         ".html": "text/html; charset=utf-8", ".json": "application/json", ".svg": "image/svg+xml"}
FRAME_S = 1 / 30

try:
    import server as onboard  # perform/onboard's Handler, its workspaces and its pool
    Base, others = onboard.Handler, onboard.W.list_robots
except ImportError as e:      # a checkout without perform/onboard: Frank works, upload doesn't
    print(f"(no onboarding here, so no CAD upload: {e})")

    class Base(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def _local(self):
            if self.headers.get("Host", "").split(":")[0] not in ("localhost", "127.0.0.1"):
                self._send(403, b"local only", "text/plain")
                return False
            return True

        def _send(self, code, body, kind):
            self.send_response(code)
            self.send_header("Content-Type", kind)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def _json(self, data, code=200):
            self._send(code, json.dumps(data, default=str).encode(), "application/json")

        def _body(self):
            n = int(self.headers.get("Content-Length") or 0)
            return self.rfile.read(n) if n else b""

        def do_GET(self):
            if self.path.startswith("/twin/"):   # the twin page, which onboarding would serve
                f = (ROOT / "perform" / "twin" / self.path.split("?")[0][len("/twin/"):]).resolve()
                if f.is_file():
                    return self._send(200, f.read_bytes(), KINDS.get(f.suffix, "application/octet-stream"))
            self._json({"ok": False, "why": "CAD upload needs perform/onboard, which isn't in this checkout"}, 501)

        def do_POST(self):
            self._json({"ok": False, "why": "CAD upload needs perform/onboard, which isn't in this checkout"}, 501)
    others = lambda: []  # noqa: E731

rt = R.Runtime()
studio = routes.Studio(rt, Path(rt.robot.path).parent, ROOT / "frank" / "online" / "performances.json",
                       others=others)


class Handler(Base):
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
            got = studio.get(unquote(p))
            if got:
                return self._json(got[1], got[0])
            if p.startswith("/s/") or p.startswith("/engine/"):
                return self._send(404, b"not found", "text/plain")
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
            got = studio.post(unquote(p), body)
            return self._json(got[1], got[0]) if got else self._send(404, b"not found", "text/plain")
        except ValueError as e:
            return self._json({"ok": False, "why": str(e)}, 400)
        except Exception as e:                                   # noqa: BLE001
            traceback.print_exc()
            return self._json({"ok": False, "why": f"{type(e).__name__}: {e}"}, 500)

    def _events(self):   # the twin's frames, 30 a second (body.py's /events)
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

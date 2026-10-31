"""
The studio in a browser tab (studio/online): Pyodide runs this file, the studio's own modules and
Frank's engine (frank/online/browser.py, as the frank-face site does), and shim.js answers the
page's /s/... and /engine/... requests from here. A page has no threads, so shim.js calls tick()
50 times a second.

What's saved (animations, machines, constraints) lives in Pyodide's file system under
robots/frank/studio/; shim.js copies those files into the visitor's localStorage after every
change and back before this module loads, so each visitor keeps their own. Online there is no
Claude key: the three pre-written examples play, a new prompt says it needs the laptop app.
Uploading CAD needs the laptop too (perform/onboard converts STEP with build123d).

    tick()                       one step of everything
    handle(method, path, body)   JSON text in and out: [status, data], or null for an unknown path
    body_frame()                 the board models' servos, for the twin (twin_shim.js)
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path[:0] = [str(ROOT / "studio")]

import runtime as R  # noqa: E402
import routes  # noqa: E402

rt = R.Runtime()
studio = routes.Studio(rt, Path(rt.robot.path).parent, ROOT / "frank" / "online" / "performances.json", online=True)


def tick():
    rt.step()


def body_frame():
    return json.dumps(rt.body_frame())


def handle(method, path, body):
    try:
        if method == "POST":
            data = json.loads(body or "{}")
            if not isinstance(data, dict):
                return json.dumps([400, {"ok": False, "why": "send an object"}])
            got = studio.post(path, data)
        else:
            got = studio.get(path)
    except Exception as e:   # its own trouble: say it, keep the face going
        got = (500, {"ok": False, "why": f"{type(e).__name__}: {e}"})
    return json.dumps(None if got is None else [got[0], got[1]], ensure_ascii=False, default=str)

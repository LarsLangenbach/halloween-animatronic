"""
The preview page, offline: start it on a free port with the stand-in engine, fetch the page,
the drawing script and a snapshot, and check that actions need the X-Frank header.

    python frank/engine/tests/test_preview.py
"""

import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import preview  # noqa: E402


def get(base, path):
    with urllib.request.urlopen(base + path, timeout=5) as r:
        return r.status, r.headers.get("Content-Type", ""), r.read()


def post(base, path, body, header=True):
    req = urllib.request.Request(base + path, data=json.dumps(body).encode(), method="POST",
                                 headers={"Content-Type": "application/json", **({"X-Frank": "1"} if header else {})})
    try:
        with urllib.request.urlopen(req, timeout=5) as r:
            return r.status, json.loads(r.read() or b"{}")
    except urllib.error.HTTPError as e:
        return e.code, e.read()


def main():
    engine = preview.StandIn()
    engine.start()
    server, pv = preview.serve(engine, port=0)
    base = f"http://127.0.0.1:{server.server_address[1]}"
    try:
        code, kind, body = get(base, "/")
        assert code == 200 and "text/html" in kind and b"face_draw.js" in body, (code, kind)
        code, kind, body = get(base, "/face_draw.js")
        assert code == 200 and "javascript" in kind and b"function drawFace" in body, (code, kind)

        code, _, body = get(base, "/snapshot")
        snap = json.loads(body)
        assert code == 200 and isinstance(snap.get("joints"), dict), snap
        assert set(preview.JOINTS) <= set(snap["joints"]), sorted(snap["joints"])
        meta = json.loads(get(base, "/meta")[2])
        assert list(meta["tags"]) == list(preview.TAGS) and meta["engine"] == "stand-in", meta

        code, body = post(base, "/tag", {"name": "surprised", "intensity": 0.8}, header=False)
        assert code == 403, (code, body)
        assert engine.weights["surprised"] == 0.0, "a POST without the header got through"
        code, body = post(base, "/tag", {"name": "surprised", "intensity": 0.8})
        assert code == 200 and body.get("ok"), (code, body)
        assert abs(engine.weights["surprised"] - 0.8) < 1e-9, engine.weights
        code, body = post(base, "/tag", {"name": "bored"})
        assert code == 400, (code, body)

        assert post(base, "/state", {"name": "listening"})[0] == 200
        assert post(base, "/state", {"name": "asleep"})[0] == 400
        assert post(base, "/event", {"name": "blink"})[0] == 200
        assert post(base, "/target", {"yaw": 20, "pitch": 5})[0] == 200
        assert engine._target == (20.0, 5.0), engine._target
        assert post(base, "/target", {"clear": True})[0] == 200 and engine._target is None
        assert post(base, "/target", {"yaw": "left"})[0] == 400

        assert post(base, "/talk", {"on": True})[0] == 200
        time.sleep(0.6)
        snap = json.loads(get(base, "/snapshot")[2])
        assert snap["state"] == "listening" and snap["preview"]["talking"], snap.get("preview")
        assert engine.talk_level >= 0.0 and pv.hook == "engine.talk_level", pv.hook
        post(base, "/talk", {"on": False})
        time.sleep(0.1)
        assert engine.talk_level == 0.0, engine.talk_level
        try:
            get(base, "/nothing")
            raise AssertionError("404 expected")
        except urllib.error.HTTPError as e:
            assert e.code == 404
    finally:
        pv.stop()
        server.shutdown()
    print("preview OK")


if __name__ == "__main__":
    main()

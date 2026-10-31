"""
The node editor for Frank's statecharts: a local page to draw charts, run them in a simulator
and change them by asking Claude in plain words. The charts are the JSON files in charts/; the
face engine (bridge.py) runs them, and picks a saved change up within a second.

    uv run --no-project --with anthropic python frank/statechart/editor.py     # http://localhost:8830
    python frank/statechart/editor.py                                          # no vibe-coding

Local only: it listens on 127.0.0.1, and every change needs a header other websites can't send.
The page polls the open chart's file, so an edit made elsewhere (Claude Code, a text editor)
shows up in the editor by itself.
"""

import argparse
import json
import os
import re
import sys
import threading
import time
import uuid
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.stdout.reconfigure(encoding="utf-8")

from statechart import vibe  # noqa: E402
from statechart.chart import Chart, ChartError, check, load, save  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
CHARTS = os.path.join(HERE, "charts")
PAGE = os.path.join(HERE, "editor.html")
VOCAB = os.path.join(HERE, "vocab.json")
PORT = 8830
HEADER = "X-Statechart-Editor"
NAME = re.compile(r"^[A-Za-z0-9_-]{1,60}$")
SIM_IDLE = 30 * 60   # s before an unused simulation is dropped


class State:
    def __init__(self, vibe_on, model):
        self.vocab = load(VOCAB)
        self.vibe_on, self.model = vibe_on, model
        self.sims, self.jobs = {}, {}
        self.lock = threading.Lock()


def chart_path(name):
    if not NAME.match(name or ""):
        raise ValueError("a chart name is letters, digits, - and _")
    return os.path.join(CHARTS, f"{name}.json")


def charts():
    out = []
    for f in sorted(os.listdir(CHARTS)):
        if f.endswith(".json"):
            out.append({"name": f[:-5], "mtime": os.path.getmtime(os.path.join(CHARTS, f))})
    return out


class Sim:
    """A chart running on a clock of its own, for the page's simulator."""

    def __init__(self, doc, vocab, context=None):
        self.chart = Chart(doc, vocab, context=context)
        self.t, self.seen, self.used = 0.0, 0, time.time()
        self.lock = threading.Lock()
        self.chart.start(0.0)

    def report(self):
        log = [e for e in self.chart.log if e["n"] > self.seen]
        self.seen = self.chart.logged
        return {"snap": self.chart.snapshot(), "log": log, "out": self.chart.drain()}

    def op(self, body):
        self.used = time.time()
        with self.lock:
            op = body.get("op")
            if op == "send":
                self.chart.send(str(body.get("event", "")), body.get("data") or {})
            elif op == "set":
                self.chart.update(body.get("vars") or {})
            elif op == "advance":
                self.t += max(0.0, min(60.0, float(body.get("dt", 0.0))))
            self.chart.step(self.t)
            return self.report()


def make_handler(state):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, fmt, *args):
            pass

        def _send(self, code, obj=None, body=None, ctype="application/json"):
            data = body if body is not None else json.dumps(obj, ensure_ascii=False).encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(data)

        def _body(self):
            n = int(self.headers.get("Content-Length") or 0)
            return json.loads(self.rfile.read(n) or b"{}") if n else {}

        def _allowed(self):
            if self.headers.get(HEADER) != "1":
                self._send(403, {"error": "missing editor header"})
                return False
            return True

        def do_GET(self):
            path = urlparse(self.path).path
            try:
                if path in ("/", "/index.html"):
                    with open(PAGE, "rb") as f:
                        return self._send(200, body=f.read(), ctype="text/html; charset=utf-8")
                if path == "/api/info":
                    return self._send(200, {"vocab": state.vocab, "charts": charts(), "vibe": state.vibe_on,
                                            "model": state.model})
                if path == "/api/charts":
                    return self._send(200, charts())
                m = re.match(r"^/api/charts/([^/]+)(/stat)?$", path)
                if m:
                    p = chart_path(m.group(1))
                    if not os.path.exists(p):
                        return self._send(404, {"error": "no such chart"})
                    if m.group(2):
                        return self._send(200, {"mtime": os.path.getmtime(p)})
                    doc = load(p)
                    return self._send(200, {"chart": doc, "mtime": os.path.getmtime(p),
                                            "issues": check(doc, state.vocab)})
                m = re.match(r"^/api/vibe/([0-9a-f]+)$", path)
                if m:
                    job = state.jobs.get(m.group(1))
                    return self._send(200, job.status()) if job else self._send(404, {"error": "no such job"})
                return self._send(404, {"error": "not found"})
            except (ValueError, OSError) as e:
                return self._send(400, {"error": str(e)})

        def do_PUT(self):
            if not self._allowed():
                return
            path = urlparse(self.path).path
            m = re.match(r"^/api/charts/([^/]+)$", path)
            if not m:
                return self._send(404, {"error": "not found"})
            try:
                p = chart_path(m.group(1))
                body = self._body()
                doc = body.get("chart")
                if not isinstance(doc, dict):
                    return self._send(400, {"error": "no chart"})
                base = body.get("base_mtime")
                if base is not None and os.path.exists(p) and abs(os.path.getmtime(p) - base) > 1e-6:
                    return self._send(409, {"error": "the file changed on disk since you opened it",
                                            "mtime": os.path.getmtime(p)})
                save(doc, p)
                return self._send(200, {"mtime": os.path.getmtime(p), "issues": check(doc, state.vocab)})
            except (ValueError, OSError) as e:
                return self._send(400, {"error": str(e)})

        def do_POST(self):
            if not self._allowed():
                return
            path = urlparse(self.path).path
            try:
                body = self._body()
                if path == "/api/check":
                    return self._send(200, {"issues": check(body.get("chart"), state.vocab)})
                if path == "/api/sim":
                    with state.lock:
                        for sid in [s for s, sim in state.sims.items() if time.time() - sim.used > SIM_IDLE]:
                            del state.sims[sid]
                    try:
                        sim = Sim(body.get("chart"), state.vocab, body.get("context"))
                    except ChartError as e:
                        return self._send(400, {"error": str(e), "issues": e.issues})
                    sid = uuid.uuid4().hex[:12]
                    with state.lock:
                        state.sims[sid] = sim
                    with sim.lock:
                        return self._send(200, {"sid": sid, **sim.report()})
                m = re.match(r"^/api/sim/([0-9a-f]+)$", path)
                if m:
                    sim = state.sims.get(m.group(1))
                    if not sim:
                        return self._send(404, {"error": "the simulation has ended: start it again"})
                    return self._send(200, sim.op(body))
                if path == "/api/vibe":
                    if not state.vibe_on:
                        return self._send(400, {"error": "vibe-coding is off: start the editor with "
                                                         "uv run --no-project --with anthropic python frank/statechart/editor.py"})
                    if not isinstance(body.get("chart"), dict) or not str(body.get("request", "")).strip():
                        return self._send(400, {"error": "send the chart and a request"})
                    job = vibe.Job(body["chart"], str(body["request"]), body.get("history") or [], state.vocab,
                                   state.model)
                    state.jobs[job.id] = job
                    return self._send(200, {"job": job.id})
                return self._send(404, {"error": "not found"})
            except (ValueError, OSError, json.JSONDecodeError) as e:
                return self._send(400, {"error": str(e)})

    return Handler


def main():
    ap = argparse.ArgumentParser(description="Frank's statechart editor")
    ap.add_argument("--port", type=int, default=PORT)
    ap.add_argument("--model", default=vibe.MODEL, help="the Claude model for vibe-coding")
    ap.add_argument("--no-browser", action="store_true", help="don't open the page")
    args = ap.parse_args()
    try:
        import anthropic  # noqa: F401
        vibe_on = True
    except ImportError:
        vibe_on = False
    os.makedirs(CHARTS, exist_ok=True)
    state = State(vibe_on, args.model)
    server = ThreadingHTTPServer(("127.0.0.1", args.port), make_handler(state))
    url = f"http://localhost:{args.port}"
    print(f"Statechart editor on {url}" + ("" if vibe_on else
          "  (vibe-coding off: add --with anthropic to the uv run line)"))
    if not args.no_browser:
        threading.Timer(0.5, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()

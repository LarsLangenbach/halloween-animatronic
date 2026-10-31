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
import sys
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.stdout.reconfigure(encoding="utf-8")

from statechart import api, vibe  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
PAGE = os.path.join(HERE, "editor.html")
PORT = 8830
HEADER = "X-Statechart-Editor"


def make_handler(store):
    """The page, and api.handle() for /api/*: the routes themselves live in api.py, which the
    public site (frank/online) runs in the browser too."""
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

        def _api(self, method):
            path = urlparse(self.path).path
            try:
                body = self._body() if method in ("PUT", "POST") else None
            except ValueError as e:
                return self._send(400, {"error": str(e)})
            if method != "GET" and self.headers.get(HEADER) != "1":
                return self._send(403, {"error": "missing editor header"})
            code, data = api.handle(method, path, body, store)
            self._send(code, data)

        def do_GET(self):
            if urlparse(self.path).path in ("/", "/index.html"):
                with open(PAGE, "rb") as f:
                    return self._send(200, body=f.read(), ctype="text/html; charset=utf-8")
            self._api("GET")

        def do_PUT(self):
            self._api("PUT")

        def do_POST(self):
            self._api("POST")

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
    api.configure(vibe_on, args.model)
    server = ThreadingHTTPServer(("127.0.0.1", args.port), make_handler(api.FileStore()))
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

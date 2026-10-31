"""
Frank's public gateway: one password-gated door in front of his page (web.py, 8800) and the
3D twin (perform/body.py, 8810), so a tunnel can carry the live Frank off this Mac.

    uv run --no-project --with aiohttp python frank/public.py --key <password>
    cloudflared tunnel --url http://127.0.0.1:8801        (prints the public link)

Share  https://<link>/?key=<password>  . The key becomes a cookie; the link without it shows a
password box. Everything else is proxied as it is:
  /            Frank's page and its routes (/state, /events, /frame, /engine/..., /say ...),
               sent on with Host localhost:8800 so web.py's local-only check stays satisfied,
               with the page's 127.0.0.1 links to the twin and the editor rewritten to /twin and /editor.
  /twin/...    the body server's twin page, its API (/robot, /model, /rig, /camera, /events,
               /calibration) and its files, with the twin's absolute paths rewritten under /twin/.
  /editor      not public (the face editor is the same engine; its controls are on the page).

Nothing in web.py or body.py changes, so Frank need not restart. Stop with Ctrl+C.
"""
import argparse
import asyncio
import secrets
import sys

from aiohttp import ClientSession, ClientTimeout, web

FRANK = "http://127.0.0.1:8800"
TWIN = "http://127.0.0.1:8810"
COOKIE = "frank_key"
TWIN_API = ("robot", "model", "rig", "camera", "events", "calibration")
HOP = {"host", "connection", "keep-alive", "transfer-encoding", "content-length", "content-encoding",
       "cookie", "accept-encoding"}
TEXT = ("text/html", "javascript", "text/css", "application/json")
PAD = b": " + b" " * 8192 + b"\n\n"  # an SSE comment the browser ignores; pushes the stream through the tunnel's buffer

GATE = """<!doctype html><meta charset="utf-8"><title>Frank</title>
<body style="background:#050806;color:#8df0a0;font:16px/1.5 ui-monospace,Menlo,monospace;display:grid;place-items:center;height:100vh;margin:0">
<form method="get" style="text-align:center"><p>Frank is behind a password.</p>
<input name="key" type="password" autofocus style="background:#0a120c;color:#8df0a0;border:1px solid #2a5a34;padding:8px 12px;font:inherit">
<button style="background:#1a3a22;color:#8df0a0;border:1px solid #2a5a34;padding:8px 14px;font:inherit;margin-left:6px">Enter</button>
{msg}</form>"""


def rewrite_frank(body: bytes) -> bytes:
    return body.replace(b"http://127.0.0.1:8810", b"/twin").replace(b"http://localhost:8810", b"/twin") \
               .replace(b"http://127.0.0.1:8820", b"/editor").replace(b"http://localhost:8820", b"/editor")


def rewrite_twin(body: bytes) -> bytes:
    for name in TWIN_API:
        body = body.replace(f'"/{name}"'.encode(), f'"/twin/{name}"'.encode())
        body = body.replace(f"'/{name}'".encode(), f"'/twin/{name}'".encode())
    return body


def make_app(key: str) -> web.Application:
    session: ClientSession | None = None

    async def on_start(app):
        nonlocal session
        session = ClientSession(timeout=ClientTimeout(total=None, sock_connect=5), auto_decompress=False)

    async def on_stop(app):
        if session:
            await session.close()

    def allowed(request: web.Request) -> bool:
        return secrets.compare_digest(request.cookies.get(COOKIE, ""), key)

    async def proxy(request: web.Request, base: str, path: str, host: str, rewrite):
        headers = {k: v for k, v in request.headers.items() if k.lower() not in HOP}
        headers["Host"] = host
        data = await request.read() if request.can_read_body else None
        url = base + path + (("?" + request.query_string) if request.query_string else "")
        try:
            upstream = await session.request(request.method, url, headers=headers, data=data)
        except Exception as e:  # the program behind it isn't running
            return web.Response(status=502, text=f"{base} is not answering ({e}). "
                                "8800 is frank, 8810 is the body server: start it.")
        kind = upstream.headers.get("Content-Type", "")
        out_headers = {k: v for k, v in upstream.headers.items()
                       if k.lower() not in HOP and k.lower() != "access-control-allow-origin"}
        if rewrite and any(t in kind for t in TEXT) and "event-stream" not in kind:
            body = rewrite(await upstream.read())
            upstream.release()
            return web.Response(status=upstream.status, body=body, headers=out_headers)
        resp = web.StreamResponse(status=upstream.status, headers=out_headers)
        await resp.prepare(request)
        sse = "event-stream" in kind
        try:
            if sse:  # Cloudflare holds a slow stream back until enough bytes have arrived (the
                await resp.write(PAD)  # twin's 30/s stream gets through; Frank's few/s doesn't)
            unflushed = False
            while True:
                try:
                    chunk = await asyncio.wait_for(upstream.content.readany(),
                                                   timeout=0.15 if (sse and unflushed) else None)
                except asyncio.TimeoutError:  # the stream went quiet with events still in the tunnel's buffer
                    await resp.write(PAD)
                    unflushed = False
                    continue
                if not chunk:
                    break
                await resp.write(chunk)
                unflushed = True
        except (ConnectionResetError, asyncio.CancelledError, Exception):
            pass
        finally:
            upstream.release()
        try:
            await resp.write_eof()
        except Exception:
            pass
        return resp

    async def handle(request: web.Request):
        if "key" in request.query:  # the shared link: set the cookie, then show the page without it
            if secrets.compare_digest(request.query["key"], key):
                resp = web.HTTPFound(request.path)
                resp.set_cookie(COOKIE, key, httponly=True, samesite="Lax", max_age=12 * 3600)
                raise resp
            return web.Response(text=GATE.format(msg="<p style='color:#e06060'>Wrong password.</p>"),
                                content_type="text/html", status=401)
        if not allowed(request):
            return web.Response(text=GATE.format(msg=""), content_type="text/html", status=401)
        path = request.path
        if path == "/editor" or path.startswith("/editor/"):
            return web.Response(text="The face editor is not public; its controls are on Frank's page.",
                                status=404)
        if path == "/twin" or path.startswith("/twin/"):
            rest = path[len("/twin/"):] if path.startswith("/twin/") else ""
            if rest == "":
                target = "/"
            elif rest in TWIN_API:
                target = "/" + rest
            else:
                target = "/twin/" + rest  # twin.js, kinematics.js, vendor/...
            return await proxy(request, TWIN, target, "localhost:8810", rewrite_twin)
        return await proxy(request, FRANK, path, "localhost:8800", rewrite_frank)

    app = web.Application(client_max_size=64 * 1024 * 1024)
    app.on_startup.append(on_start)
    app.on_cleanup.append(on_stop)
    app.router.add_route("*", "/{tail:.*}", handle)
    return app


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--key", required=True, help="the password visitors need")
    ap.add_argument("--port", type=int, default=8801)
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    print(f"Frank's public gateway on http://127.0.0.1:{args.port}  (key: {args.key})\n"
          f"  tunnel it:  cloudflared tunnel --url http://127.0.0.1:{args.port}", flush=True)
    web.run_app(make_app(args.key), host="127.0.0.1", port=args.port, print=None, access_log=None)


if __name__ == "__main__":
    main()

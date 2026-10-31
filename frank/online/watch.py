"""
Frank online, kept up to date: watches the files the face demo is built from (build.sources():
frank/engine, frank/statechart, browser.py and browser.js). When they change and then sit
still for QUIET seconds, it rebuilds output/online, opens the page in headless Edge
(check.mjs) and deploys it to https://frank-face.vercel.app only if the page works. A
half-written file from a session still editing the engine never reaches the public page.

    python frank/online/watch.py                 watch until stopped (Ctrl+C)
    python frank/online/watch.py --once          build, check and deploy if changed, then exit
    python frank/online/watch.py --log FILE      also append the lines to FILE

One line per event: HELD (the check failed: the page stays as it was), DEPLOYED, LIVE OK or
LIVE FAILED (the public page checked after a deploy), WARN (build.py: something will not work
online). The page's routes are preview.Api's (browser.py), so new ones need nothing here. At most one deploy every GAP seconds (Vercel's free plan allows
100 a day). Only one watcher runs at a time: it holds 127.0.0.1:LOCK_PORT. What was deployed
is recorded in output/online/.vercel/frank_deployed.json, which never uploads.
"""

import argparse
import hashlib
import json
import re
import shutil
import socket
import subprocess
import sys
import threading
import time
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import build as B

HERE = Path(__file__).parent
URL = "https://frank-face.vercel.app/"
QUIET = 60.0     # s the sources must sit still before a build
GAP = 300.0      # s at least between deploys
POLL = 3.0       # s between looks at the sources
LOCK_PORT = 8839
STATE = B.OUT / ".vercel" / "frank_deployed.json"
NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)
BROWSERS = (r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
            r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
            r"C:\Program Files\Google\Chrome\Application\chrome.exe")
LOG = None


def say(line):
    line = f"{time.strftime('%H:%M:%S')} {line}"
    print(line, flush=True)
    if LOG:
        with open(LOG, "a", encoding="utf-8") as f:
            f.write(line + "\n")


def signature():
    sig = {}
    for p in B.sources():
        try:
            st = p.stat()
            sig[str(p)] = (st.st_mtime_ns, st.st_size)
        except OSError:
            pass
    return sig


def digests(out=B.OUT):
    return {p.relative_to(out).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(out.rglob("*")) if p.is_file() and ".vercel" not in p.relative_to(out).parts}


def free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def browser():
    for b in BROWSERS:
        if Path(b).exists():
            return b
    return shutil.which("msedge") or shutil.which("chrome")


def check(url):
    """check.mjs's result for url, and whether it passes."""
    node = shutil.which("node")
    r = subprocess.run([node, str(HERE / "check.mjs"), browser(), url, str(free_port())],
                       capture_output=True, text=True, encoding="utf-8", timeout=240, creationflags=NO_WINDOW)
    try:
        res = json.loads(r.stdout.strip().splitlines()[-1])
    except (ValueError, IndexError):
        return {"errors": [f"check.mjs: {(r.stderr or r.stdout).strip()[-300:]}"]}, False
    twin = res.get("twin")   # shown: the 3D twin is the face, and must load and move
    drawn = twin.get("loaded") and twin.get("driven", 0) > 0 if twin else res.get("lit", 0) > 5000
    ed = res.get("editor")   # the State machine tab, where the page has one
    editing = not ed or (ed.get("status") == 200 and ed.get("charts", 0) > 0
                         and (ed.get("page") or {}).get("drawn", 0) > 20 and not (ed.get("page") or {}).get("error"))
    ok = (res.get("live") and (res.get("engine") or "").endswith("Engine") and res.get("tags", 0) > 0
          and drawn and editing and not res.get("errors"))
    return res, bool(ok)


class Quiet(SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


def check_local():
    server = ThreadingHTTPServer(("127.0.0.1", 0), partial(Quiet, directory=str(B.OUT)))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        return check(f"http://127.0.0.1:{server.server_address[1]}/")
    finally:
        server.shutdown()


def deploy():
    vercel = shutil.which("vercel")
    r = subprocess.run([vercel, "deploy", str(B.OUT), "--prod", "--yes"], capture_output=True, text=True,
                       encoding="utf-8", timeout=600, creationflags=NO_WINDOW)
    found = re.search(r"https://frank-face-[a-z0-9]+-[a-z0-9-]+\.vercel\.app", r.stdout + r.stderr)
    return r.returncode == 0, found.group(0) if found else (r.stderr or r.stdout).strip()[-300:]


def short(res):
    return (f"live={res.get('live')} in {res.get('seconds')} s, {res.get('engine')}, tags={res.get('tags')}, "
            f"state={res.get('state')}, strongest={res.get('strongest')}, lit={res.get('lit')}, twin={res.get('twin')}, "
            f"editor={res.get('editor')}"
            + (f", errors: {' | '.join(str(e)[:160] for e in res['errors'][:3])}" if res.get("errors") else ""))


def cycle():
    """Build; if it differs from what is deployed, check it and deploy it. True if deployed."""
    for w in B.build():
        say(f"WARN {w}")
    now = digests()
    state = json.loads(STATE.read_text(encoding="utf-8")) if STATE.exists() else {}
    old = state.get("files", {})
    if now == old:
        return False
    changed = sorted(k for k in now.keys() | old.keys() if now.get(k) != old.get(k))
    res, ok = check_local()
    if not ok:
        say(f"HELD {len(changed)} changed file(s) ({', '.join(changed[:6])}): the page failed its check: {short(res)}")
        return False
    done, where = deploy()
    if not done:
        say(f"DEPLOY FAILED: {where}")
        return False
    STATE.write_text(json.dumps(dict(files=now, at=time.strftime("%Y-%m-%d %H:%M:%S"), url=where), indent=1),
                     encoding="utf-8")
    say(f"DEPLOYED {where} ({len(changed)} changed: {', '.join(changed[:8])}{' ...' if len(changed) > 8 else ''})")
    time.sleep(5)
    res, ok = check(URL)
    say(f"LIVE {'OK' if ok else 'FAILED'} {URL}: {short(res)}")
    return True


def main():
    global LOG
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="Keep https://frank-face.vercel.app up to date")
    ap.add_argument("--once", action="store_true", help="build, check and deploy if changed, then exit")
    ap.add_argument("--log", help="also append each line to this file")
    a = ap.parse_args()
    LOG = a.log
    if a.once:
        cycle() or say("nothing new to deploy")
        return
    lock = socket.socket()
    try:
        lock.bind(("127.0.0.1", LOCK_PORT))
    except OSError:
        say(f"another watcher is already running (127.0.0.1:{LOCK_PORT} is taken)")
        return
    say(f"watching {len(B.sources())} files for {URL} (quiet {QUIET:.0f} s, at most one deploy per {GAP:.0f} s)")
    last_sig, changed_at, built_sig, deployed_at = None, 0.0, None, 0.0
    while True:
        sig = signature()
        if sig != last_sig:
            last_sig, changed_at = sig, time.monotonic()
        now = time.monotonic()
        if sig != built_sig and now - changed_at >= QUIET and now - deployed_at >= GAP:
            built_sig = sig
            try:
                if cycle():
                    deployed_at = time.monotonic()
            except (Exception, SystemExit) as e:   # keep watching: the next change may fix it
                say(f"ERROR {type(e).__name__}: {e}")
        time.sleep(POLL)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass

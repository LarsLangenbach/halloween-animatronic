"""
The body server: the one program that holds a robot's servo boards, so everything else talks to
the robot through it, and the digital twin (twin/, http://localhost:8810) moves with it.

    uv run --no-project --with pyserial python perform/body.py robots/frank/robot.json --port /dev/cu.usbmodem2101
    uv run --no-project python perform/body.py robots/frank/robot.json --sim       (no board: the twin is the body)

Then point every program that moves the robot at socket://127.0.0.1:8811 in place of the board's
port (frank/web.py --mouth socket://127.0.0.1:8811, firmware/servo_controls.py
socket://127.0.0.1:8811 --link, firmware/mouth_controls.py socket://127.0.0.1:8811). On a Mac or
Linux, --pty N also makes N virtual serial ports, for programs that only open a device path
(as firmware/share_port.py does). Any number of programs at once: each one's lines go to the
board whole, never mixed with another's; what the board prints goes to all of them.

Every line sent is also run through a model of the board's program (boards.py), so the body
server knows every servo's pulse, and the servo's own speed (robot.json servo_types) is applied
on top. The twin page reads that 30 times a second (/events) and moves the CAD model through
its linkages (twin/kinematics.js). It shows what the robot was told to do and how far it has
got, not a measurement: nothing on the boards reports a servo's real position.

  --sim          no board: the models answer as the boards would (the mouth board's "where",
                 "Received:", its start-up line), so Frank, the slider windows and recorded
                 performances all run against the twin alone
  --record F     append every line sent, with its time and sender, to F (JSON lines)
  --tcp N        first TCP port (default 8811)    --http N   the twin's port (default 8810)
  --firmware B=F the program board B runs, if not robot.json's (B=cogley_mouth / pico_servo_ctl)

The twin page's calibration (each servo's zero and direction) is saved into robot.json.
Local only: everything listens on 127.0.0.1, and the page's POSTs need the X-Perform header
that other websites can't send.
"""
import argparse
import json
import os
import queue
import socket
import sys
import threading
import time
from collections import deque
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import boards as B  # noqa: E402

ROOT = HERE.parent
TICK = 0.01                      # model and servo update, s
FRAME = 1 / 30                   # twin frame rate, s
US_PER_HORN_DEG = 2000.0 / 180   # ASSUMPTION: hobby servos turn about 180 deg over 500..2500 us
ECHO_WAIT = 1.0                  # s a cogley_mouth board takes at most to echo "Received:"


class Robot:
    """robot.json: boards, servos and their calibration, and the board models' live state."""

    def __init__(self, path, firmware=None, seed=None):
        self.path = Path(path).resolve()
        self.base = self.path.parent
        self.spec = json.loads(self.path.read_text(encoding="utf-8"))
        self.lock = threading.RLock()
        self.boards = {}
        for name, b in self.spec["boards"].items():
            fw = (firmware or {}).get(name, b["firmware"])
            self.boards[name] = B.FIRMWARE[fw](seed=seed)
        self.via = {name: b.get("via") for name, b in self.spec["boards"].items()}
        self.next = {v: name for name, v in self.via.items() if v}           # board -> the board it forwards to
        self.servos = self.spec["servos"]
        self.by_pin = {(s["board"], s["pin"]): sid for sid, s in self.servos.items()}
        types = self.spec.get("servo_types", {})
        self.speed = {sid: types.get(s.get("type", ""), {}).get("deg_per_s", 500.0) for sid, s in self.servos.items()}
        self.phys = {sid: None for sid in self.servos}                        # where each horn is, us
        self.t0 = time.time()

    def file(self, key):
        p = self.spec.get(key)
        return (self.base / p).resolve() if p else None

    def roots(self):
        return [n for n, v in self.via.items() if not v]

    def feed(self, board, text):
        """One line arrives at `board`. Returns its reply (sim) and every (board, line) it reached."""
        with self.lock:
            reply, fwd = self.boards[board].line(text)
            reached = [(board, text)]
            nxt = self.next.get(board)
            if fwd and nxt:
                _, sub = self.feed(nxt, fwd)
                reached += sub
            return reply, reached

    def control(self, board, byte):
        with self.lock:
            return self.boards[board].control(byte)

    def switch(self, board, fw):
        with self.lock:
            self.boards[board] = B.FIRMWARE[fw]()

    def tick(self, dt):
        with self.lock:
            for b in self.boards.values():
                b.tick(dt)
            for (board, pin), sid in self.by_pin.items():
                st = self.boards[board].pins.get(pin)
                if not st:
                    continue
                cur = self.phys[sid]
                if cur is None:
                    self.phys[sid] = st["us"]
                elif st["live"]:
                    step = self.speed[sid] * US_PER_HORN_DEG * dt
                    d = st["us"] - cur
                    self.phys[sid] = st["us"] if abs(d) <= step else cur + (step if d > 0 else -step)

    def frame(self):
        with self.lock:
            servos = {}
            for (board, pin), sid in self.by_pin.items():
                b = self.boards[board]
                st = b.pins.get(pin, {"us": b.pulse(90), "live": False})
                us = self.phys[sid] if self.phys[sid] is not None else st["us"]
                servos[sid] = {"us": round(us, 1), "cmd": round(st["us"], 1), "live": st["live"],
                               "deg": round(b.degrees(us), 1)}
            boards = {n: {"firmware": b.name, "us0": b.US0, "us_per_deg": b.US_PER_DEG, "running": b.running}
                      for n, b in self.boards.items()}
            return {"t": round(time.time() - self.t0, 3), "servos": servos, "boards": boards}

    def calibrate(self, changes):
        """{servo: {zero, sign}} into robot.json, keeping everything else as it is."""
        with self.lock:
            spec = json.loads(self.path.read_text(encoding="utf-8"))
            for sid, c in changes.items():
                if sid not in spec["servos"]:
                    raise KeyError(sid)
                for k in ("zero", "sign"):
                    if k in c:
                        v = float(c[k])
                        if k == "sign" and v not in (1.0, -1.0):
                            raise ValueError("sign must be 1 or -1")
                        spec["servos"][sid][k] = int(v) if k == "sign" else round(v, 1)
            tmp = self.path.with_suffix(".tmp")
            tmp.write_text(json.dumps(spec, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
            os.replace(tmp, self.path)
            self.spec, self.servos = spec, spec["servos"]


class Hub:
    """Events for the twin pages: the latest frame and recent lines, to every open page."""

    def __init__(self):
        self.lock = threading.Lock()
        self.pages = []
        self.lines = deque(maxlen=200)
        self.notes = deque(maxlen=50)

    def subscribe(self):
        q = queue.Queue(maxsize=200)
        with self.lock:
            self.pages.append(q)
        return q

    def unsubscribe(self, q):
        with self.lock:
            if q in self.pages:
                self.pages.remove(q)

    def publish(self, ev):
        with self.lock:
            for q in self.pages:
                try:
                    q.put_nowait(ev)
                except queue.Full:
                    pass

    def line(self, **ev):
        ev["t"] = round(time.time(), 3)
        with self.lock:
            self.lines.append(ev)

    def note(self, text):
        print(text, flush=True)
        ev = {"kind": "note", "text": text, "t": round(time.time(), 3)}
        with self.lock:
            self.notes.append(ev)
        self.publish(ev)


class Port:
    """One root board: its serial port (or the model alone, --sim) and the programs sharing it."""

    def __init__(self, robot, hub, board, device, record=None):
        self.robot, self.hub, self.board, self.device = robot, hub, board, device
        self.clients = {}            # id -> send(bytes)
        self.cid = 0
        self.lock = threading.Lock()
        self.ser = None
        self.record = record
        self.echo_due = deque()      # times a "Received:" echo is expected by (cogley_mouth)
        self.misses = 0
        if device:
            import serial
            self.ser = serial.serial_for_url(device, 115200, timeout=0.05)
            threading.Thread(target=self._read_board, daemon=True).start()
            threading.Thread(target=self._watch_echo, daemon=True).start()

    # -------------------------------------------------------------------- programs
    def attach(self, send):
        with self.lock:
            self.cid += 1
            self.clients[self.cid] = send
            return self.cid

    def detach(self, cid):
        with self.lock:
            self.clients.pop(cid, None)

    def to_clients(self, data):
        with self.lock:
            sends = list(self.clients.values())
        for send in sends:
            try:
                send(data)
            except OSError:
                pass

    def from_client(self, cid, buf, data):
        """Bytes from a program: control characters at once, lines whole. Returns the unfinished line."""
        for ch in data:
            c = bytes([ch])
            if c in (b"\x03", b"\x04"):
                self._write(c)
                reply = self.robot.control(self.board, c)
                self.hub.line(kind="control", sender=cid, board=self.board, text="Ctrl-" + ("C" if c == b"\x03" else "D"))
                if reply and not self.ser:
                    self.to_clients((reply + "\r\n").encode())
            elif c in (b"\r", b"\n"):
                if buf.strip():
                    self._line(cid, buf.decode("utf-8", "replace").strip())
                buf = b""
            else:
                buf += c
                if len(buf) > 400:
                    buf = b""
        return buf

    def _line(self, cid, text):
        self._write((text + "\n").encode())
        reply, reached = self.robot.feed(self.board, text)
        for board, t in reached:
            self.hub.line(kind="line", sender=cid, board=board, text=t)
        if self.record:
            self.record.write(json.dumps({"t": round(time.time(), 3), "sender": cid, "board": self.board,
                                          "line": text}) + "\n")
            self.record.flush()
        if self.ser:
            if self.robot.boards[self.board].name == "cogley_mouth" and not text.startswith("e "):
                self.echo_due.append(time.time() + ECHO_WAIT)
        elif reply:
            self.to_clients((reply.replace("\n", "\r\n") + "\r\n").encode())

    def _write(self, data):
        if self.ser:
            with self.lock:
                self.ser.write(data)

    # -------------------------------------------------------------------- the board
    def _read_board(self):
        buf = b""
        while True:
            try:
                data = self.ser.read(4096)
            except OSError as e:
                self.hub.note(f"{self.board}: the board's port failed ({e}); restart the body server")
                return
            if not data:
                continue
            self.to_clients(data)
            buf += data
            while b"\n" in buf:
                raw, buf = buf.split(b"\n", 1)
                self._board_said(raw.decode("utf-8", "replace").strip())
            if len(buf) > 2000:
                buf = b""

    def _board_said(self, text):
        if not text:
            return
        self.hub.line(kind="reply", board=self.board, text=text)
        fw = self.robot.boards[self.board].name
        cogley = text.startswith("Received:") or "JL=" in text or text.startswith("Ready to receive commands")
        if cogley and fw != "cogley_mouth":
            self.robot.switch(self.board, "cogley_mouth")
            self.hub.note(f"{self.board}: the board answers as cogley_mouth_main.py; following that program now")
        if text.startswith("Received:") and self.echo_due:
            self.echo_due.popleft()
            self.misses = 0
        if "JL=" in text and self.robot.boards[self.board].name == "cogley_mouth":
            with self.robot.lock:
                self.robot.boards[self.board].where(text)

    def _watch_echo(self):
        """A cogley_mouth board echoes every line. Two lines in a row with no echo: it runs
        pico_servo_ctl.py (which prints nothing), or main.py has stopped."""
        while True:
            time.sleep(0.2)
            now = time.time()
            while self.echo_due and self.echo_due[0] < now:
                self.echo_due.popleft()
                self.misses += 1
            if self.misses >= 2 and self.robot.boards[self.board].name == "cogley_mouth":
                self.misses = 0
                self.echo_due.clear()
                self.robot.switch(self.board, "pico_servo_ctl")
                self.hub.note(f"{self.board}: no echo from the board; following pico_servo_ctl.py now")


def serve_tcp(port, number):
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind(("127.0.0.1", number))
    srv.listen(8)

    def client(conn):
        conn.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        cid = port.attach(conn.sendall)
        port.hub.note(f"program {cid} connected to {port.board} (tcp {number})")
        buf = b""
        try:
            while True:
                data = conn.recv(4096)
                if not data:
                    break
                buf = port.from_client(cid, buf, data)
        except OSError:
            pass
        finally:
            port.detach(cid)
            conn.close()
            port.hub.note(f"program {cid} left {port.board}")

    def accept():
        while True:
            conn, _ = srv.accept()
            threading.Thread(target=client, args=(conn,), daemon=True).start()

    threading.Thread(target=accept, daemon=True).start()


def serve_pty(port, n):
    """Virtual serial ports (macOS, Linux), as firmware/share_port.py makes them."""
    import select
    masters = []
    for _ in range(n):
        m, s = os.openpty()
        os.set_blocking(m, False)
        masters.append((m, s, port.attach(lambda d, m=m: os.write(m, d))))
        port.hub.note(f"virtual port for {port.board}: {os.ttyname(s)}")

    def loop():
        bufs = {m: b"" for m, _, _ in masters}
        ids = {m: cid for m, _, cid in masters}
        while True:
            ready, _, _ = select.select(list(bufs), [], [], 1.0)
            for m in ready:
                try:
                    data = os.read(m, 4096)
                except (BlockingIOError, OSError):
                    continue
                bufs[m] = port.from_client(ids[m], bufs[m], data)

    threading.Thread(target=loop, daemon=True).start()


def handler(robot, hub, ports):
    twin = HERE / "twin"
    files = {"/rig": robot.file("rig"), "/camera": robot.file("camera")}

    class H(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def _send(self, code, body, kind):
            self.send_response(code)
            self.send_header("Content-Type", kind)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def _json(self, data, code=200):
            self._send(code, json.dumps(data).encode(), "application/json")

        def do_GET(self):
            if self.headers.get("Host", "").split(":")[0] not in ("localhost", "127.0.0.1"):
                return self._send(403, b"local only", "text/plain")
            path = self.path.split("?")[0]
            if path == "/":
                return self._send(200, (twin / "index.html").read_bytes(), "text/html; charset=utf-8")
            if path == "/robot":
                return self._json(robot.spec)
            if path == "/model":
                rig = robot.file("rig")
                glb = rig.parent / json.loads(rig.read_text(encoding="utf-8"))["model"]
                return self._send(200, glb.read_bytes(), "model/gltf-binary")
            if path in files and files[path] and files[path].exists():
                return self._send(200, files[path].read_bytes(), "application/json")
            if path == "/events":
                return self._events()
            if path.startswith("/twin/"):
                f = (twin / path[len("/twin/"):]).resolve()
                if twin in f.parents and f.is_file():
                    kind = {".js": "text/javascript", ".mjs": "text/javascript", ".css": "text/css",
                            ".json": "application/json"}.get(f.suffix, "application/octet-stream")
                    return self._send(200, f.read_bytes(), kind)
            self._send(404, b"not found", "text/plain")

        def do_POST(self):
            if self.headers.get("X-Perform") != "1" or self.headers.get("Host", "").split(":")[0] not in ("localhost", "127.0.0.1"):
                return self._send(403, b"local only", "text/plain")
            n = int(self.headers.get("Content-Length", "0") or 0)
            try:
                body = json.loads(self.rfile.read(n) or b"{}")
                if self.path == "/calibration":
                    robot.calibrate(body)
                    hub.note("calibration saved to " + robot.path.name + ": " + ", ".join(
                        f"{k} {v}" for k, v in body.items()))
                    return self._json({"ok": True, "servos": robot.servos})
            except (ValueError, KeyError) as e:
                return self._json({"ok": False, "error": str(e)}, 400)
            self._send(404, b"not found", "text/plain")

        def _events(self):
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            q = hub.subscribe()
            sent_line = 0.0
            try:
                for ev in list(hub.notes):
                    self._event(ev)
                while True:
                    try:
                        ev = q.get(timeout=FRAME)
                        self._event(ev)
                        continue
                    except queue.Empty:
                        pass
                    f = robot.frame()
                    with hub.lock:
                        lines = [ln for ln in hub.lines if ln["t"] > sent_line]
                    if lines:
                        sent_line = lines[-1]["t"]
                    f.update(kind="frame", lines=lines[-60:], ports={p.board: {
                        "device": p.device or "simulated", "programs": len(p.clients)} for p in ports})
                    self._event(f)
            except (BrokenPipeError, ConnectionResetError, OSError):
                pass
            finally:
                hub.unsubscribe(q)

        def _event(self, ev):
            self.wfile.write(b"data: " + json.dumps(ev).encode() + b"\n\n")
            self.wfile.flush()

    return H


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("robot", help="the robot's robot.json")
    ap.add_argument("--port", action="append", default=[],
                    help="a root board's serial port, BOARD=PORT, or just PORT for the first root board")
    ap.add_argument("--sim", action="store_true", help="no boards: the models answer")
    ap.add_argument("--tcp", type=int, default=8811)
    ap.add_argument("--http", type=int, default=8810)
    ap.add_argument("--pty", type=int, default=0)
    ap.add_argument("--record")
    ap.add_argument("--firmware", action="append", default=[], help="BOARD=PROGRAM")
    a = ap.parse_args()
    fw = dict(x.split("=", 1) for x in a.firmware)
    robot = Robot(a.robot, firmware=fw)
    hub = Hub()
    roots = robot.roots()
    devices = {}
    for i, p in enumerate(a.port):
        b, d = p.split("=", 1) if "=" in p.split("://")[0] else (roots[min(i, len(roots) - 1)], p)
        devices[b] = d
    if not a.sim:
        for b in roots:
            devices.setdefault(b, robot.spec["boards"][b].get("port"))
            if devices[b] in (None, "auto"):
                devices[b] = find_port()
            if not devices[b]:
                sys.exit(f"no serial port for {b}: plug the board in, give --port, or run with --sim")
    record = open(a.record, "a", encoding="utf-8") if a.record else None
    ports = []
    for i, b in enumerate(roots):
        port = Port(robot, hub, b, None if a.sim else devices[b], record=record)
        serve_tcp(port, a.tcp + i)
        if a.pty:
            serve_pty(port, a.pty)
        ports.append(port)
        hub.note(f"{b}: {'simulated' if a.sim else devices[b]} ({robot.boards[b].name}); programs connect to "
                 f"socket://127.0.0.1:{a.tcp + i}")

    def ticker():
        last = time.time()
        while True:
            time.sleep(TICK)
            now = time.time()
            robot.tick(now - last)
            last = now

    threading.Thread(target=ticker, daemon=True).start()
    http = ThreadingHTTPServer(("127.0.0.1", a.http), handler(robot, hub, ports))
    http.daemon_threads = True
    hub.note(f"{robot.spec.get('name', 'robot')}'s twin: http://localhost:{a.http}")
    try:
        http.serve_forever()
    except KeyboardInterrupt:
        pass


def find_port():
    """The first USB serial device, or None (the same choice as frank/mouth.py's find_port)."""
    import glob
    try:
        from serial.tools import list_ports
        ports = list(list_ports.comports())
        for p in ports:
            if "pico" in (p.description or "").lower() or "micropython" in (p.description or "").lower():
                return p.device
        for p in ports:
            if "usbmodem" in p.device or "USB" in (p.description or "") or p.device.startswith("COM"):
                return p.device
    except ImportError:
        pass
    found = sorted(glob.glob("/dev/cu.usbmodem*"))
    return found[0] if found else None


if __name__ == "__main__":
    main()

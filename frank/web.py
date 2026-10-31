"""
Frank in the browser: a page on this laptop to watch him and talk to him.

    uv run --no-project --with anthropic --with openai --with httpx --with sounddevice --with numpy --with scipy --with websockets --with livekit --with opencv-python --with mediapipe python frank/web.py
    then open http://localhost:8800

Everything still runs here in Python, through chat.py's Chat: the camera, the microphone,
the voice and the brain. The page (web.html) shows what his camera sees with the faces
marked, who is in view, and the conversation as it happens: what he hears, what he says,
the face he makes and what his senses report. It has his switches too: type to him,
microphone, voice, a new conversation, the brain, a silence, a note, feedback, enrolling
someone and forgetting people. The terminal shows what chat.py always shows.

    --talk        microphone on from the start   --mute       no voice
    --no-see      no camera                      --video F    a clip instead of the camera
    --model M     the brain (default sonnet-5.5)   --place P    where he is, for his notes
    --speaker S   his voice's output device, by name (part of it will do) or number;
                  default: the Mac's own output. The page can change it.
    --port N      default 8800
    --mouth PORT  the mouth Pico (or auto): the jaw follows his voice (mouth.py; add --with pyserial)

It listens on 127.0.0.1 only, so other computers can't open it. Its actions need the
X-Frank header and a localhost address, so other websites open in the same browser can't
use it either.
"""

import argparse
import json
import queue
import sys
import threading
import time
from collections import deque
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
import brain  # noqa: E402
import chat as chat_mod  # noqa: E402

PAGE = HERE / "web.html"
HOSTS = ("localhost", "127.0.0.1")


class Hub:
    """Sends chat's ui() events to every open page. A page that opens late gets the most
    recent ones first; seq lets it skip what it already has after a reconnect."""

    def __init__(self, keep=400):
        self.lock = threading.Lock()
        self.recent, self.pages, self.seq = deque(maxlen=keep), [], 0

    def publish(self, ev):
        with self.lock:
            self.seq += 1
            ev = dict(ev, seq=self.seq)
            self.recent.append(ev)
            for q in self.pages:
                q.put(ev)

    def subscribe(self):
        q = queue.Queue()
        with self.lock:
            self.pages.append(q)
            return q, list(self.recent)

    def unsubscribe(self, q):
        with self.lock:
            self.pages.remove(q)


class People:
    """The stored people, read and forgotten from the page. The vision process notices a
    change within 2 s (faces.Gallery.refresh)."""

    def __init__(self):
        import faces
        self.gallery, self.lock = faces.Gallery(), threading.Lock()

    def list(self):
        with self.lock:
            db = self.gallery.db
            counts = dict(db.execute("SELECT person_id, COUNT(*) FROM face_templates GROUP BY person_id"))
            return [dict(id=pid, name=name, role=role, enrolled=at[:16].replace("T", " "),
                         prints=counts.get(pid, 0))
                    for pid, name, role, at in db.execute(
                        "SELECT id, name, role, enrolled_at FROM people ORDER BY role, name")]

    def forget(self, pid):
        """The name of whoever was forgotten, or None if nobody has that number."""
        with self.lock:
            self.gallery.refresh()
            if pid not in self.gallery.people:
                return None
            name = self.gallery.name(pid)
            self.gallery.forget(pid)
            return name


def handler(chat, hub, people):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):  # the terminal is for the conversation
            pass

        def _local(self):
            host = (self.headers.get("Host") or "").rsplit(":", 1)[0]
            return host in HOSTS

        def _send(self, code, body, kind):
            self.send_response(code)
            self.send_header("Content-Type", kind)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def _json(self, data, code=200):
            self._send(code, json.dumps(data, ensure_ascii=False, default=str).encode(), "application/json")

        def do_GET(self):
            if not self._local():
                return self._send(403, b"local only", "text/plain")
            path = self.path.split("?")[0]
            if path == "/":
                self._send(200, PAGE.read_bytes(), "text/html; charset=utf-8")
            elif path == "/state":
                self._json(dict(chat.status(), sight=chat.eyes.state if chat.eyes else None,
                                people=people.list()))
            elif path == "/events":
                self._events()
            elif path == "/frame":  # the newest preview picture; the page asks 10 times a second
                jpeg = chat.eyes.jpeg if chat.eyes else None
                self._send(200, jpeg, "image/jpeg") if jpeg else self._send(204, b"", "image/jpeg")
            else:
                self._send(404, b"not found", "text/plain")

        def do_POST(self):
            if not self._local() or self.headers.get("X-Frank") != "1":
                return self._send(403, b"local page only", "text/plain")
            try:
                body = json.loads(self.rfile.read(int(self.headers.get("Content-Length") or 0)) or b"{}")
            except json.JSONDecodeError:
                return self._json(dict(ok=False, why="bad request"), 400)
            if self.path == "/say":  # a line to Frank, or a chat.py command (/new, /talk, ...)
                text = str(body.get("text", "")).strip()
                if text and text.split()[0] not in ("/quit", "/exit", "/q"):
                    chat.events.put(("typed", text))
                self._json(dict(ok=True))
            elif self.path == "/enrol":
                name = str(body.get("name", "")).strip()
                if not name or not chat.eyes:
                    return self._json(dict(ok=False, why="a name, and the camera on, are needed"))
                role = "creator" if body.get("creator") else "visitor"
                self._json(chat.eyes.start_enrol(name, role))
            elif self.path in ("/speaker", "/beep"):
                if not chat.voice:
                    return self._json(dict(ok=False, why="the voice didn't load: see the terminal"))
                try:
                    if self.path == "/speaker":
                        speaker = body.get("id")
                        chat.voice.use_speaker(None if speaker in (None, "") else int(speaker))
                        chat.info(f"voice now plays through {self._speaker_name(speaker)}")
                    else:
                        chat.voice.beep()
                    self._json(dict(ok=True))
                except Exception as e:
                    self._json(dict(ok=False, why=f"{type(e).__name__}: {e}"))
            elif self.path == "/forget":
                name = people.forget(int(body.get("id", -1)))
                if name:
                    chat.info(f"forgot {name} from the page")
                self._json(dict(ok=bool(name), name=name))
            else:
                self._send(404, b"not found", "text/plain")

        def _speaker_name(self, speaker):
            speakers, default = chat.status()["speakers"], chat.status()["default_speaker"]
            pick = default if speaker in (None, "") else int(speaker)
            return next((d["name"] for d in speakers if d["id"] == pick), f"device {pick}")

        def _events(self):
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            q, past = hub.subscribe()
            try:
                for ev in past:
                    self._event(ev)
                while True:
                    try:
                        self._event(q.get(timeout=15))
                    except queue.Empty:
                        self.wfile.write(b": still here\n\n")
                        self.wfile.flush()
            except (BrokenPipeError, ConnectionResetError):
                pass
            finally:
                hub.unsubscribe(q)

        def _event(self, ev):
            self.wfile.write(f"data: {json.dumps(ev, ensure_ascii=False, default=str)}\n\n".encode())
            self.wfile.flush()

    return Handler


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="Frank in the browser")
    ap.add_argument("--model", default="sonnet-5.5", choices=list(brain.MODELS))
    ap.add_argument("--place", default="The lab, SCAD Satellite Lab, Savannah")
    ap.add_argument("--mute", action="store_true", help="no voice")
    ap.add_argument("--talk", action="store_true", help="microphone on from the start")
    ap.add_argument("--no-see", action="store_true", help="no camera")
    ap.add_argument("--video", help="a video file instead of the camera")
    ap.add_argument("--speaker", help="the voice's output device, by name or number")
    ap.add_argument("--port", type=int, default=8800)
    ap.add_argument("--mouth", help="the mouth Pico's serial port, or auto: the jaw follows his voice (mouth.py)")
    args = ap.parse_args()
    brain.load_env()
    if not brain.available(args.model):
        sys.exit(f"No key for {args.model}: add it to frank/.env")

    chat = chat_mod.Chat(args.model, None, args.place, args.mute)
    hub = Hub()
    chat.listeners.append(hub.publish)
    hub.publish(dict(kind="new", t=time.time(), model=chat.model))  # Chat started before the page could hear
    if args.speaker and chat.voice:
        try:
            chat.voice.use_speaker(int(args.speaker) if args.speaker.isdigit() else args.speaker)
        except Exception as e:  # not plugged in here: the Mac's own output, and the page can change it
            print(f"(speaker {args.speaker!r} not found, so the Mac's default output: {e})")
    if args.mouth and chat.voice:
        import mouth
        chat.voice.mouth = mouth.Mouth(args.mouth, log=lambda **k: chat.write(event="mouth", **k))
        print(f"Mouth on {chat.voice.mouth.port} ({chat.voice.mouth.program}).")
    if not args.no_see:
        chat.see(preview="web", source=args.video)
    if args.talk:
        chat.listen()
    server = ThreadingHTTPServer(("127.0.0.1", args.port), handler(chat, hub, People()))
    server.daemon_threads = True
    threading.Thread(target=server.serve_forever, daemon=True).start()
    print(f"\nFrank is at http://localhost:{args.port}  (Ctrl+C here to stop)\n")
    try:
        chat.run()
    except EOFError:
        pass
    finally:
        if chat.eyes:
            chat.eyes.stop()
        if chat.voice and chat.voice.mouth:
            chat.voice.mouth.close()
        server.shutdown()
        print(f"Saved to {chat.log}")


if __name__ == "__main__":
    main()

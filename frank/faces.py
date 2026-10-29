"""
Frank's face recognition: the face models, and the gallery of people he may recognise.

    uv run --no-project --with opencv-python python frank/faces.py list
    uv run --no-project --with opencv-python python frank/faces.py forget <name or number>

Faces are found with OpenCV's YuNet and turned into a fingerprint of 128 numbers with
SFace (both from the OpenCV model zoo, MIT and Apache 2.0). Fingerprints of the same face
score about 0.5-0.8 in cosine similarity; different people score about 0-0.3. The models
download into output/frank/models/ on first use and are checked against their hashes.

The gallery holds only the creators (eyes.py --enroll NAME --creator) and visitors who
said yes to being remembered (remember_person). It is one SQLite file in
output/frank/memory/, which git ignores: it holds face data, so never commit or share it.
Strangers' fingerprints never come here; eyes.py keeps them in memory and drops them.
"""

import hashlib
import sqlite3
import sys
import urllib.request
from datetime import datetime
from pathlib import Path

import cv2
import numpy as np

HERE = Path(__file__).parent
MODELS_DIR = HERE.parent / "output" / "frank" / "models"
DB = HERE.parent / "output" / "frank" / "memory" / "frank.db"
ZOO = "https://github.com/opencv/opencv_zoo/raw/main/models"
MODELS = {  # file: (url, sha256 of the file downloaded 2026-10-28)
    "face_detection_yunet_2023mar.onnx": (
        f"{ZOO}/face_detection_yunet/face_detection_yunet_2023mar.onnx",
        "8f2383e4dd3cfbb4553ea8718107fc0423210dc964f9f4280604804ed2552fa4"),
    "face_recognition_sface_2021dec.onnx": (
        f"{ZOO}/face_recognition_sface/face_recognition_sface_2021dec.onnx",
        "0ba9fbfa01b5270c96627c4ef784da859931e02f04419c829e83484087c34e79"),
    "face_landmarker.task": (  # MediaPipe, used by eyes.py for the mouths
        "https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task",
        "64184e229b263107bc2b804c6625db1341ff2bb731874b0bcc2fe6544e0bc9ff"),
    "selfie_segmenter_landscape.tflite": (  # MediaPipe: which pixels are people (eyes.py)
        "https://storage.googleapis.com/mediapipe-models/image_segmenter/selfie_segmenter_landscape/float16/1/selfie_segmenter_landscape.tflite",
        "490e9ea734313e0de10fa0cd9e3c6133e36ea4db2b7a49bde9ef019f72796b8e"),
}

# Deciding who a face is, from the mean similarity of its last few fingerprints to each
# person. Strict on purpose: a wrong name would hand a stranger someone else's memories.
KNOWN = 0.45       # recognised at or above this ...
MARGIN = 0.08      # ... and this far ahead of the next person ...
KNOWN_PRINTS = 3   # ... over at least this many fingerprints (5 took 1.3 s+; 'incredibly slow', 2026-10-29)
POSSIBLE = 0.363   # OpenCV's published SFace threshold: more likely the same person than not
MAX_TEMPLATES = 40  # fingerprints kept per person (the newest)

SCHEMA = """
CREATE TABLE IF NOT EXISTS people (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    role TEXT NOT NULL,            -- 'creator' or 'visitor'
    enrolled_at TEXT NOT NULL,
    consent TEXT NOT NULL DEFAULT '',   -- when and how they said yes
    first_note TEXT NOT NULL DEFAULT '' -- remember_person's notes, until the memory store exists
);
CREATE TABLE IF NOT EXISTS face_templates (
    id INTEGER PRIMARY KEY,
    person_id INTEGER NOT NULL REFERENCES people(id) ON DELETE CASCADE,
    print BLOB NOT NULL,           -- 128 float32, unit length
    taken_at TEXT NOT NULL
);
"""


def model(name):
    """The path to a model file, downloaded on first use and checked against its hash."""
    path = MODELS_DIR / name
    url, sha = MODELS[name]
    if not path.exists():
        MODELS_DIR.mkdir(parents=True, exist_ok=True)
        print(f"downloading {name} ...")
        part = path.with_name(path.name + ".part")
        urllib.request.urlretrieve(url, part)
        part.rename(path)
    if hashlib.sha256(path.read_bytes()).hexdigest() != sha:
        raise SystemExit(f"{path} doesn't match its checksum: delete it to download it again")
    return str(path)


class Recogniser:
    """YuNet finds faces; SFace fingerprints them."""

    def __init__(self, detect_width=960):
        self.det = cv2.FaceDetectorYN.create(model("face_detection_yunet_2023mar.onnx"), "",
                                             (320, 320), 0.75, 0.3, 50)
        self.rec = cv2.FaceRecognizerSF.create(model("face_recognition_sface_2021dec.onnx"), "")
        self.width = detect_width  # frames are shrunk to this width to look for faces

    def detect(self, frame):
        """The faces in a BGR frame, each a row of 15 numbers in frame pixels: the box
        (x, y, w, h), five points (right eye, left eye, nose tip, right and left mouth
        corner, as x, y) and the detector's score."""
        h, w = frame.shape[:2]
        s = min(1.0, self.width / w)
        small = cv2.resize(frame, (round(w * s), round(h * s))) if s < 1 else frame
        self.det.setInputSize((small.shape[1], small.shape[0]))
        _, faces = self.det.detect(small)
        if faces is None:
            return []
        faces = faces.copy()
        faces[:, :14] /= s
        return list(faces)

    def fingerprint(self, frame, face):
        e = self.rec.feature(self.rec.alignCrop(frame, face)).ravel()
        return (e / np.linalg.norm(e)).astype(np.float32)


def identify(scores, n):
    """("known" | "possible" | None, person id, score) from Gallery.scores over n prints."""
    if not scores:
        return None, None, 0.0
    pid, best = scores[0]
    second = scores[1][1] if len(scores) > 1 else 0.0
    if best >= KNOWN and best - second >= MARGIN and n >= KNOWN_PRINTS:
        return "known", pid, best
    if best >= POSSIBLE and n >= 2:
        return "possible", pid, best
    return None, pid, best


class Gallery:
    """The stored people and their face fingerprints."""

    def __init__(self, path=DB):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(path, check_same_thread=False)
        self.db.execute("PRAGMA foreign_keys = ON")
        self.db.execute("PRAGMA journal_mode = WAL")
        self.db.executescript(SCHEMA)
        self.version = None
        self.refresh()

    def refresh(self):
        """Reload if another program (faces.py forget, say) changed the file."""
        version = self.db.execute("PRAGMA data_version").fetchone()[0]
        if version != self.version:
            self.version = version
            self._load()

    def _load(self):
        self.people = {pid: dict(name=name, role=role) for pid, name, role in
                       self.db.execute("SELECT id, name, role FROM people")}
        rows = self.db.execute("SELECT person_id, print FROM face_templates").fetchall()
        self.owner = np.array([r[0] for r in rows], dtype=int)
        self.prints = (np.stack([np.frombuffer(r[1], np.float32) for r in rows]) if rows
                       else np.zeros((0, 128), np.float32))

    def scores(self, prints):
        """Each person's mean similarity to these fingerprints (their best template for
        each), best first: [(person id, score)]."""
        if not len(self.prints) or not len(prints):
            return []
        sims = np.asarray(prints, np.float32) @ self.prints.T
        out = [(int(pid), float(sims[:, self.owner == pid].max(axis=1).mean()))
               for pid in np.unique(self.owner)]
        return sorted(out, key=lambda x: -x[1])

    def name(self, pid):
        return self.people.get(pid, {}).get("name", "?")

    def role(self, pid):
        return self.people.get(pid, {}).get("role")

    def add(self, name, role, prints, consent="", note=""):
        with self.db:
            pid = self.db.execute(
                "INSERT INTO people (name, role, enrolled_at, consent, first_note) VALUES (?, ?, ?, ?, ?)",
                (name, role, _now(), consent, note)).lastrowid
        self.add_prints(pid, prints)
        return pid

    def add_prints(self, pid, prints):
        with self.db:
            self.db.executemany("INSERT INTO face_templates (person_id, print, taken_at) VALUES (?, ?, ?)",
                                [(pid, np.asarray(p, np.float32).tobytes(), _now()) for p in prints])
            self.db.execute("""DELETE FROM face_templates WHERE person_id = ? AND id NOT IN
                               (SELECT id FROM face_templates WHERE person_id = ? ORDER BY id DESC LIMIT ?)""",
                            (pid, pid, MAX_TEMPLATES))
        self._load()

    def forget(self, pid):
        """Delete the person and every fingerprint of them."""
        with self.db:
            self.db.execute("DELETE FROM people WHERE id = ?", (pid,))
        self._load()

    def find(self, key):
        """People whose number or name (any case) is key."""
        return [pid for pid, p in self.people.items()
                if str(pid) == key or p["name"].casefold() == key.casefold()]


def _now():
    return datetime.now().isoformat(timespec="seconds")


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    args = sys.argv[1:]
    g = Gallery()
    if not args or args[0] == "list":
        counts = dict(g.db.execute("SELECT person_id, COUNT(*) FROM face_templates GROUP BY person_id"))
        rows = g.db.execute("SELECT id, name, role, enrolled_at, consent FROM people ORDER BY id").fetchall()
        for pid, name, role, at, consent in rows:
            print(f"{pid:>4}  {name:<16} {role:<8} {at}  {counts.get(pid, 0):>2} prints  {consent}")
        print(f"{len(rows)} people in {DB}")
    elif args[0] == "forget" and len(args) == 2:
        found = g.find(args[1])
        if not found:
            sys.exit(f"nobody called {args[1]!r}")
        for pid in found:
            if input(f"Delete {g.name(pid)} ({pid}, {g.role(pid)}) and their face prints? [y/N] ").lower() == "y":
                g.forget(pid)
                print("deleted")
    else:
        print(__doc__.split("\n\n")[1])


if __name__ == "__main__":
    main()

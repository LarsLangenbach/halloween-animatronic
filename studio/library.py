"""
The animation library: the performances made in the Animation studio (written from a prompt,
or recorded from the emotion map and the tag buttons), saved with a name. The state machine's
states play them. One file per robot: robots/<name>/studio/animations.json.

Each entry is {id, title, source, prompt?, created, anim}; anim is the face engine's timeline
(frank/engine/animate.py: {title, duration, keys}), cleaned by animate.clean() on the way in.
A new library starts with the public site's pre-written examples (frank/online/performances.json).
"""

import json
import os
import re
import threading
import time
from pathlib import Path

from engine import animate as A

FORMAT = "studio-animations/1"
SOURCES = ("prompt", "recorded", "example", "edited")
LOCK = threading.Lock()


class Library:
    def __init__(self, robot_dir, seed=None):
        self.path = Path(robot_dir) / "studio" / "animations.json"
        self.seed = seed

    def _read(self):
        if self.path.exists():
            try:
                doc = json.loads(self.path.read_text(encoding="utf-8"))
                if doc.get("format") == FORMAT:
                    return doc
            except ValueError:
                pass
        doc = {"format": FORMAT, "animations": {}}
        if self.seed and Path(self.seed).exists():
            for prompt, anim in json.loads(Path(self.seed).read_text(encoding="utf-8"))["performances"].items():
                title = re.sub(r"\s*\(pre-written\)$", "", anim.get("title") or prompt)
                self._put(doc, {"title": title, "source": "example", "prompt": prompt, "anim": anim})
        return doc

    def _write(self, doc):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(doc, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
        os.replace(tmp, self.path)

    @staticmethod
    def _id(doc, title):
        base = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")[:40] or "anim"
        n, aid = 1, base
        while aid in doc["animations"]:
            n += 1
            aid = f"{base}-{n}"
        return aid

    def _put(self, doc, entry):
        anim = A.clean(entry["anim"])
        title = str(entry.get("title") or anim["title"] or "untitled").strip()[:80]
        anim["title"] = title
        aid = entry.get("id") if entry.get("id") in doc["animations"] else self._id(doc, title)
        doc["animations"][aid] = {
            "id": aid, "title": title,
            "source": entry.get("source") if entry.get("source") in SOURCES else "edited",
            "prompt": entry.get("prompt"), "created": entry.get("created") or time.strftime("%Y-%m-%d %H:%M"),
            "anim": anim,
        }
        return doc["animations"][aid]

    def all(self):
        with LOCK:
            return list(self._read()["animations"].values())

    def get(self, aid):
        with LOCK:
            return self._read()["animations"].get(aid)

    def save(self, entry):
        """A new animation, or a changed one when entry["id"] is already in the library."""
        with LOCK:
            doc = self._read()
            out = self._put(doc, entry)
            self._write(doc)
            return out

    def rename(self, aid, title):
        with LOCK:
            doc = self._read()
            e = doc["animations"].get(aid)
            if not e:
                raise KeyError(aid)
            e["title"] = e["anim"]["title"] = str(title).strip()[:80] or e["title"]
            self._write(doc)
            return e

    def delete(self, aid):
        with LOCK:
            doc = self._read()
            doc["animations"].pop(aid, None)
            self._write(doc)

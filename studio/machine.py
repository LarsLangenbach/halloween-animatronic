"""
The State machine page: a few named states joined by arrows. Each state holds animations from
the library (any number: its variations); entering it plays one of them, picked at random or in
turn, and plays another when that one ends unless an arrow leaves first. Arrows fire on:

    done     the state's animation has finished
    after    N seconds in the state
    event    a named event (arrived, left, hearing, a word of your own...), sent from the
             page's Run panel, or by the engine's events once this runs inside Frank

One file per machine: robots/<name>/studio/machines/<machine>.json, format studio-states/1:

    {"format": "studio-states/1", "name": "evening", "start": "idle",
     "states": {"idle": {"name": "Idle", "x": 80, "y": 120, "anims": ["yawn", "look-around"],
                         "pick": "random", "loop": true}},
     "links": [{"id": "l1", "from": "idle", "to": "greet", "on": "event", "event": "arrived"},
               {"id": "l2", "from": "greet", "to": "idle", "on": "done"}]}

The Runner plays it on the studio's engine, stepped by the studio's ticker.
"""

import json
import os
import random
import re
import time
from pathlib import Path

FORMAT = "studio-states/1"
ONS = ("done", "after", "event")
NAME = re.compile(r"^[A-Za-z0-9_-]{1,60}$")
EVENT = re.compile(r"^[a-z0-9_]{1,40}$")


def clean(doc):
    """A machine made safe: known fields only, links between states that exist. Returns
    (machine, problems), problems being sentences for the page."""
    doc = doc if isinstance(doc, dict) else {}
    problems, states = [], {}
    for sid, s in (doc.get("states") or {}).items():
        if not isinstance(s, dict) or not NAME.match(str(sid)):
            continue
        num = lambda v, d: float(v) if isinstance(v, (int, float)) else d  # noqa: E731
        states[sid] = {"name": str(s.get("name") or sid)[:60], "x": num(s.get("x"), 0.0), "y": num(s.get("y"), 0.0),
                       "anims": [str(a) for a in s.get("anims", []) if isinstance(a, str)][:40],
                       "pick": "order" if s.get("pick") == "order" else "random",
                       "loop": s.get("loop", True) is not False}
    links = []
    for i, ln in enumerate(doc.get("links") or []):
        if not isinstance(ln, dict) or ln.get("from") not in states or ln.get("to") not in states:
            continue
        on = ln.get("on") if ln.get("on") in ONS else "done"
        out = {"id": str(ln.get("id") or f"l{i}")[:40], "from": ln["from"], "to": ln["to"], "on": on}
        if on == "after":
            s = ln.get("seconds")
            out["seconds"] = max(0.1, min(3600.0, float(s))) if isinstance(s, (int, float)) else 5.0
        elif on == "event":
            ev = str(ln.get("event") or "").strip().lower().replace(" ", "_")
            out["event"] = ev if EVENT.match(ev) else "go"
        links.append(out)
    start = doc.get("start") if doc.get("start") in states else next(iter(states), None)
    m = {"format": FORMAT, "name": str(doc.get("name") or "machine")[:60], "start": start,
         "states": states, "links": links}
    if not states:
        problems.append("No states yet: press Create state.")
    for sid, s in states.items():
        if not s["anims"]:
            problems.append(f"{s['name']} has no animation: drag one in from the library, or write a prompt.")
        outs = [ln for ln in links if ln["from"] == sid]
        if sum(1 for ln in outs if ln["on"] == "done") > 1:
            problems.append(f"{s['name']} has more than one 'when done' arrow: only the first fires.")
        if not s["loop"] and not outs:
            problems.append(f"{s['name']} doesn't loop and has no way out: the face goes still there.")
    reach, todo = set(), [start] if start else []
    while todo:
        sid = todo.pop()
        if sid not in reach:
            reach.add(sid)
            todo += [ln["to"] for ln in links if ln["from"] == sid]
    for sid in states:
        if sid not in reach:
            problems.append(f"{states[sid]['name']} can't be reached from the start state.")
    return m, problems


class Store:
    def __init__(self, robot_dir):
        self.dir = Path(robot_dir) / "studio" / "machines"

    def names(self):
        return sorted(p.stem for p in self.dir.glob("*.json")) if self.dir.is_dir() else []

    def get(self, name):
        p = self.dir / f"{name}.json"
        if not NAME.match(name) or not p.exists():
            return None
        return clean(json.loads(p.read_text(encoding="utf-8")))[0]

    def put(self, name, doc):
        if not NAME.match(name):
            raise ValueError("a machine name is letters, digits, - and _")
        m, problems = clean(doc)
        m["name"] = name
        self.dir.mkdir(parents=True, exist_ok=True)
        p = self.dir / f"{name}.json"
        tmp = p.with_suffix(".tmp")
        tmp.write_text(json.dumps(m, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
        os.replace(tmp, p)
        return m, problems

    def delete(self, name):
        p = self.dir / f"{name}.json"
        if NAME.match(name) and p.exists():
            p.unlink()


class Runner:
    """Plays a machine on the studio's engine. step(now) runs on the ticker, under its lock."""

    def __init__(self, rt, library):
        self.rt, self.library = rt, library
        self.m, self.cur, self.since, self.anim_id = None, None, 0.0, None
        self.playing_mine, self.turn, self.log = False, {}, []

    @property
    def running(self):
        return self.m is not None

    def _say(self, text):
        self.log.append({"t": time.strftime("%H:%M:%S"), "text": text})
        del self.log[:-40]

    def start(self, doc, at=None):
        self.m, _ = clean(doc)
        self.turn = {}
        if not self.m["start"]:
            self.m = None
            raise ValueError("the machine has no states")
        self._say(f"started {self.m['name']}")
        self.enter(at if at in self.m["states"] else self.m["start"], time.monotonic())

    def stop(self, why="stopped"):
        if self.m:
            self._say(why)
        if self.playing_mine and self.rt.player:
            self.rt.player.stop()
        self.m, self.cur, self.playing_mine, self.anim_id = None, None, False, None

    def enter(self, sid, now, why=None):
        self.cur, self.since = sid, now
        self._say(f"→ {self.m['states'][sid]['name']}" + (f"  ({why})" if why else ""))
        self.play_variant()

    def play_variant(self):
        s = self.m["states"][self.cur]
        found = [a for a in s["anims"] if self.library.get(a)]
        if not found:
            self.playing_mine, self.anim_id = False, None
            return
        if s["pick"] == "order":
            i = self.turn.get(self.cur, 0)
            aid = found[i % len(found)]
            self.turn[self.cur] = i + 1
        else:
            choices = [a for a in found if a != self.anim_id] or found
            aid = random.choice(choices)
        entry = self.library.get(aid)
        self.rt.play(entry["anim"])
        self.playing_mine, self.anim_id = True, aid
        self._say(f"   plays {entry['title']}")

    def event(self, name):
        if not self.m:
            return False
        for ln in self.m["links"]:
            if ln["from"] == self.cur and ln["on"] == "event" and ln["event"] == name:
                self.enter(ln["to"], time.monotonic(), f"event {name}")
                return True
        self._say(f"   event {name}: no arrow for it here")
        return False

    def goto(self, sid):
        if self.m and sid in self.m["states"]:
            self.enter(sid, time.monotonic(), "by hand")

    def step(self, now):
        if not self.m:
            return
        p = self.rt.player
        done = self.playing_mine and not (p and p.playing)
        if not self.playing_mine and self.anim_id is None:
            done = True                                   # nothing to play: done at once
        outs = [ln for ln in self.m["links"] if ln["from"] == self.cur]
        for ln in outs:
            if ln["on"] == "after" and now - self.since >= ln["seconds"]:
                return self.enter(ln["to"], now, f"after {ln['seconds']:g} s")
        if done:
            for ln in outs:
                if ln["on"] == "done":
                    return self.enter(ln["to"], now, "done")
            if self.playing_mine and self.m["states"][self.cur]["loop"]:
                self.play_variant()
            else:
                self.playing_mine = False

    def status(self):
        if not self.m:
            return {"running": False, "log": self.log[-20:]}
        p = self.rt.player
        st = p.status() if p else {}
        return {"running": True, "name": self.m["name"], "state": self.cur,
                "in_state": round(time.monotonic() - self.since, 1), "anim": self.anim_id,
                "elapsed": st.get("elapsed"), "duration": st.get("duration"), "log": self.log[-20:]}

"""
The statechart editor's routes without a server: editor.py serves them over HTTP on the laptop,
and the public site (frank/online) calls them in the browser through Pyodide. One function:

    status, data = api.handle(method, path, body, store)

    GET  /api/info                   vocab, charts, whether vibe-coding is on, the model
    GET  /api/charts                 [{name, mtime}]
    GET  /api/charts/<name>[/stat]   {chart, mtime, issues} (or just {mtime})
    PUT  /api/charts/<name>          {chart, base_mtime?} -> {mtime, issues}; 409 if it changed meanwhile
    POST /api/check                  {chart} -> {issues}
    POST /api/sim                    {chart, context?} -> {sid, snap, log, out}
    POST /api/sim/<sid>              {op: send|set|advance, ...} -> {snap, log, out}
    POST /api/vibe, GET /api/vibe/<id>   change a chart by asking Claude (laptop only)

`store` holds the charts: FileStore (the JSON files in charts/, for editor.py) or MemoryStore
(a dict, for the browser; the page can mirror it to localStorage). Set `api.ONLINE = True` on
the public site: vibe-coding then answers 501, and no key is ever needed or asked for.
"""

import copy
import json
import os
import re
import threading
import time
import uuid

from .chart import Chart, ChartError, check, index, load

HERE = os.path.dirname(os.path.abspath(__file__))
CHARTS = os.path.join(HERE, "charts")
VOCAB = os.path.join(HERE, "vocab.json")
NAME = re.compile(r"^[A-Za-z0-9_-]{1,60}$")
SIM_IDLE = 30 * 60   # s before an unused simulation is dropped
ONLINE = False       # the public site: no vibe-coding (it needs a key)


# ----- where the charts live -----

def dumps(doc):
    """The chart as readable JSON, dropping layout entries for states that are gone (as chart.save)."""
    doc = copy.deepcopy(doc)
    ids = set(index(doc)) if isinstance(doc.get("root"), dict) else set()
    if isinstance(doc.get("layout"), dict):
        doc["layout"] = {k: v for k, v in doc["layout"].items() if k in ids}
    return json.dumps(doc, indent=2, ensure_ascii=False) + "\n"


class FileStore:
    """The JSON files in a folder (charts/)."""

    def __init__(self, folder=CHARTS):
        self.folder = folder
        os.makedirs(folder, exist_ok=True)

    def _path(self, name):
        return os.path.join(self.folder, f"{name}.json")

    def list(self):
        return sorted(f[:-5] for f in os.listdir(self.folder) if f.endswith(".json"))

    def get(self, name):
        p = self._path(name)
        if not os.path.exists(p):
            return None
        with open(p, encoding="utf-8") as f:
            return f.read()

    def put(self, name, text):
        p = self._path(name)
        tmp = f"{p}.tmp"
        with open(tmp, "w", encoding="utf-8", newline="\n") as f:
            f.write(text)
        os.replace(tmp, p)

    def stat(self, name):
        p = self._path(name)
        return {"mtime": os.path.getmtime(p), "size": os.path.getsize(p)} if os.path.exists(p) else None


class MemoryStore:
    """Charts in a dict, {name: JSON text}: the browser's store, seeded from the shipped charts."""

    def __init__(self, seed=None):
        now = time.time()
        self.charts = {name: (text, now) for name, text in (seed or {}).items()}

    def list(self):
        return sorted(self.charts)

    def get(self, name):
        return self.charts[name][0] if name in self.charts else None

    def put(self, name, text):
        self.charts[name] = (text, time.time())

    def stat(self, name):
        if name not in self.charts:
            return None
        text, mtime = self.charts[name]
        return {"mtime": mtime, "size": len(text)}


def seed_from_files(folder=CHARTS):
    """{name: text} of the shipped charts, to seed a MemoryStore."""
    store = FileStore(folder)
    return {name: store.get(name) for name in store.list()}


# ----- the simulator -----

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


class State:
    """What the routes share: the vocabulary, the running simulations and vibe jobs."""

    def __init__(self, vibe_on=False, model=None):
        self.vocab = load(VOCAB)
        self.vibe_on, self.model = vibe_on, model
        self.sims, self.jobs = {}, {}
        self.lock = threading.Lock()


_state = None


def state():
    global _state
    if _state is None:
        _state = State()
    return _state


def configure(vibe_on=False, model=None):
    """editor.py: vibe-coding on or off, and the model it uses."""
    global _state
    _state = State(vibe_on and not ONLINE, model)
    return _state


# ----- the routes -----

def _name(name):
    if not NAME.match(name or ""):
        raise ValueError("a chart name is letters, digits, - and _")
    return name


def _charts(store):
    return [{"name": n, "mtime": (store.stat(n) or {}).get("mtime")} for n in store.list()]


def handle(method, path, body, store):
    """One request: (status, JSON-able data). Never raises for a bad request."""
    st = state()
    body = body if isinstance(body, dict) else {}
    try:
        if method == "GET":
            if path == "/api/info":
                return 200, {"vocab": st.vocab, "charts": _charts(store), "vibe": st.vibe_on,
                             "model": st.model, "online": ONLINE}
            if path == "/api/charts":
                return 200, _charts(store)
            m = re.match(r"^/api/charts/([^/]+)(/stat)?$", path)
            if m:
                name = _name(m.group(1))
                info = store.stat(name)
                if info is None:
                    return 404, {"error": "no such chart"}
                if m.group(2):
                    return 200, {"mtime": info["mtime"]}
                doc = json.loads(store.get(name))
                return 200, {"chart": doc, "mtime": info["mtime"], "issues": check(doc, st.vocab)}
            m = re.match(r"^/api/vibe/([0-9a-f]+)$", path)
            if m:
                job = st.jobs.get(m.group(1))
                return (200, job.status()) if job else (404, {"error": "no such job"})
            return 404, {"error": "not found"}

        if method == "PUT":
            m = re.match(r"^/api/charts/([^/]+)$", path)
            if not m:
                return 404, {"error": "not found"}
            name = _name(m.group(1))
            doc = body.get("chart")
            if not isinstance(doc, dict):
                return 400, {"error": "no chart"}
            base, info = body.get("base_mtime"), store.stat(name)
            if base is not None and info is not None and abs(info["mtime"] - base) > 1e-6:
                return 409, {"error": "the chart changed since you opened it", "mtime": info["mtime"]}
            store.put(name, dumps(doc))
            return 200, {"mtime": store.stat(name)["mtime"], "issues": check(doc, st.vocab)}

        if method == "POST":
            if path == "/api/check":
                return 200, {"issues": check(body.get("chart"), st.vocab)}
            if path == "/api/sim":
                with st.lock:
                    for sid in [s for s, sim in st.sims.items() if time.time() - sim.used > SIM_IDLE]:
                        del st.sims[sid]
                try:
                    sim = Sim(body.get("chart"), st.vocab, body.get("context"))
                except ChartError as e:
                    return 400, {"error": str(e), "issues": e.issues}
                sid = uuid.uuid4().hex[:12]
                with st.lock:
                    st.sims[sid] = sim
                with sim.lock:
                    return 200, {"sid": sid, **sim.report()}
            m = re.match(r"^/api/sim/([0-9a-f]+)$", path)
            if m:
                sim = st.sims.get(m.group(1))
                if not sim:
                    return 404, {"error": "the simulation has ended: start it again"}
                return 200, sim.op(body)
            if path == "/api/vibe":
                if ONLINE:
                    return 501, {"ok": False, "error": "not available online: vibe-coding runs on the laptop's editor",
                                 "why": "not available online"}
                if not st.vibe_on:
                    return 400, {"error": "vibe-coding is off: start the editor with "
                                          "uv run --no-project --with anthropic python frank/statechart/editor.py"}
                if not isinstance(body.get("chart"), dict) or not str(body.get("request", "")).strip():
                    return 400, {"error": "send the chart and a request"}
                from . import vibe   # only here: it talks to Claude
                job = vibe.Job(body["chart"], str(body["request"]), body.get("history") or [], st.vocab, st.model)
                st.jobs[job.id] = job
                return 200, {"job": job.id}
            return 404, {"error": "not found"}

        return 405, {"error": f"{method} not allowed"}
    except (ValueError, OSError) as e:   # json.JSONDecodeError is a ValueError
        return 400, {"error": str(e)}

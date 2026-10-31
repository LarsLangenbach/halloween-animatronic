"""
Frank's face engine with its conversation states taken from a statechart file instead of the
code in frank/engine/orchestrator.py. Everything else (synthesiser, animator, rig, tag timing,
gaze) is the engine's own.

    from statechart.bridge import ChartedEngine
    engine = ChartedEngine(writer=mouth.Mouth("auto")).start()       # charts/frank.json
    engine = ChartedEngine(chart="statechart/charts/mine.json").start()

It is a drop-in for engine.Engine: the same hooks (voice.mouth = engine, chat.listeners,
engine.watch) feed it. Each tick it:
  - updates the chart's context from the engine (speaking, thinking, people, present, no_vision);
  - runs the chart up to now;
  - carries out the chart's actions: tag (on the engine's tag clock, honouring delay), nudge
    (the mood), anim (a one-shot animator event), log;
  - hands the chart's profile to the animator as its state.
Events (arrived, left, interrupted, hearing, visitor, frank_end, ...) go into the chart instead
of the hand-written reactions. When the chart file changes on disk (saved in the editor, or
edited by Claude), the next tick loads it; a chart with errors is logged and the old one kept.
"""

import os
import time

from engine import channels
from engine.orchestrator import FAREWELL_S, GREETING_S, INTERRUPTED_S, Engine

from .chart import Chart, ChartError, load

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_CHART = os.path.join(HERE, "charts", "frank.json")
VOCAB = os.path.join(HERE, "vocab.json")
RELOAD_EVERY = 1.0   # s between looks at the chart file's modification time
TIMED = {"interrupted": INTERRUPTED_S, "greeting": GREETING_S, "farewell": FAREWELL_S}
UI_EVENTS = ("hearing", "visitor", "frank_end", "new")


class ChartedEngine(Engine):
    def __init__(self, writer=None, hz=50, log=None, personality=None, chart=DEFAULT_CHART, watch_file=True):
        super().__init__(writer=writer, hz=hz, log=log, personality=personality)
        self.vocab = load(VOCAB)
        self.chart_path = chart if isinstance(chart, str) else None
        self.chart_mtime = os.path.getmtime(chart) if self.chart_path else None
        self.watch_file = watch_file and self.chart_path is not None
        self.chart_checked = time.monotonic()
        self.forced_until = None
        self.chart = Chart(load(chart) if self.chart_path else chart, self.vocab)

    # ----- the chart -----

    def use_chart(self, doc):
        """Swap in another chart now, keeping the context. Raises ChartError if it can't run."""
        new = Chart(doc, self.vocab, context=dict(self.chart.ctx))
        with self.lock:
            self.chart = new
        self.log(what="chart", loaded=doc.get("name"))

    def _reload(self, t):
        if not self.watch_file or t - self.chart_checked < RELOAD_EVERY:
            return
        self.chart_checked = t
        try:
            mtime = os.path.getmtime(self.chart_path)
        except OSError:
            return
        if mtime == self.chart_mtime:
            return
        self.chart_mtime = mtime
        try:
            self.chart = Chart(load(self.chart_path), self.vocab, context=dict(self.chart.ctx))
            self.log(what="chart", reloaded=self.chart_path)
        except (ChartError, ValueError, OSError) as e:
            self.log(what="chart_error", error=str(e)[:300])
        except Exception as e:  # a half-written or odd file never stops the face
            self.log(what="chart_error", error=f"{type(e).__name__}: {e}"[:300])

    def _act(self, a, t):
        do = a.get("do")
        at = a.get("t", t) + float(a.get("delay") or 0)
        if do == "tag" and a.get("tag") in channels.TAGS:
            self.pending.append((at, a["tag"], a.get("intensity")))
        elif do == "nudge":
            self.synth.nudge(t, p=a.get("p", 0), a=a.get("a", 0), d=a.get("d", 0))
        elif do == "anim" and a.get("event") in channels.EVENTS:
            self.events.append(a["event"])
        elif do == "log":
            self.log(what="chart", text=a.get("text"))

    # ----- the engine's hooks, rerouted -----

    def _state(self, t):
        self._reload(t)
        vis = self.vision_state or {}
        people = [p for p in vis.get("people", []) if not p.get("figure")]
        self.chart.update(
            speaking=self._speaking(t), thinking=self.thinking, people=len(people),
            present=bool(vis.get("session") or any(p.get("engaged") for p in people)),
            no_vision=self.vision_state is None)
        self.chart.step(t)
        for a in self.chart.drain():
            self._act(a, t)
        forced = self.forced
        if forced and self.forced_until is not None and t >= self.forced_until:
            self.forced = self.forced_until = forced = None
        if forced and (forced != "speaking" or self._speaking(t)):
            return self._set_mode(forced, t)
        return self._set_mode(self.chart.profile() or "idle", t)

    def state(self, name):
        """Set a state by hand (preview, tests); "auto" hands it back to the chart. The timed
        ones (interrupted, greeting, farewell) last as long as they do in the engine."""
        t = time.monotonic()
        with self.lock:
            if name == "auto":
                self.forced = self.forced_until = None
                self.thinking = False
                return
            if name not in channels.STATES:
                return
            self.thinking = name == "thinking"
            self.forced = name
            self.forced_until = t + TIMED[name] if name in TIMED else None
            ev = {"interrupted": "flinch", "greeting": "greet", "farewell": "long_blink"}.get(name)
            if ev:
                self.events.append(ev)
        self._set_mode(name, t)

    def event(self, name, data=None):
        with self.lock:
            if name in channels.EVENTS:
                self.events.append(name)
            else:
                if name == "interrupted":
                    self.thinking = False
                self.chart.send(name, data)
        self.log(what="engine_event", name=name)

    def on_ui(self, ev):
        kind = ev.get("kind")
        if kind == "sound" and ev.get("tag") == "chuckle":
            self.event("chuckle")
            return
        super().on_ui(ev)   # the engine's own bookkeeping; its events come back through event()
        if kind in UI_EVENTS:
            self.event(kind, {k: ev[k] for k in ("silent", "interrupted") if k in ev})

    def snapshot(self):
        snap = super().snapshot()
        with self.lock:
            snap["chart"] = {"name": self.chart.doc.get("name"), "leaves": self.chart.leaves(),
                             "error": self.chart.error}
        return snap

"""
Frank's statecharts: the file format, the checks and the runtime (README.md in this folder).

A chart is a JSON file, close to XState and SCXML, so a person, the node editor and Claude can
all read and write it:

    {"format": "frank-statechart/1", "name": "frank", "host": "frank-engine",
     "context": {"speaking": {"type": "bool", "default": false}, ...},
     "root": {"id": "frank", "type": "parallel", "states": {...}},
     "layout": {"<state id>": {"x": 0, "y": 0, "w": 160, "h": 56}, ...}}

Every state has an id that is unique in the whole chart (its key in its parent's "states"). A
state may have:
  type         atomic (no children) | compound (children, one of them active) | parallel (all
               children active at once) | final | history. Left out: compound if it has
               children, else atomic
  initial      compound: the child entered first (default: the first child)
  states       {id: state, ...}
  profile      what the face engine does in this state (the animator's state name). A state
               without one takes its nearest ancestor's
  priority     when parallel regions each give a profile or knobs, the higher priority wins
  knobs        {name: value}: other settings for the host, merged by priority
  entry, exit  lists of actions
  transitions  checked in order; each has exactly one trigger:
                 event "name"     when that event arrives
                 after seconds    once the state has been active that long
                 when "expr"      as soon as the expression is true (checked every step)
               and may have: target (a state id; left out = stay put and only run the actions),
               guard "expr", actions [...], reenter (leave and re-enter the source even though
               the target is inside it; a transition to its own source does this by default),
               note
  history      in a history state: "shallow" (default) or "deep"; its "target" is where to go
               when there is no history yet
  note         free text

Actions are objects with a "do". The chart runs two itself: raise (send an event to this chart,
optionally after "delay" seconds) and set (a context variable, from "value" or an "expr").
Every other action (tag, nudge, anim, log, ...) goes to the host through drain(), stamped with
the time it was taken; the host honours its "delay".

Guards and "when" are small Python expressions over the context variables: and, or, not,
comparisons, + - * / %, numbers, strings, True, False, in_state("id"), and data["key"] for the
current event's data. Nothing else (no attributes, no other calls), so a chart can't run code.

    chart = Chart(json.load(open("charts/frank.json")))
    chart.update(speaking=False, people=1)
    chart.send("arrived")
    chart.step(time.monotonic())
    chart.profile(); chart.drain()
"""

import ast
import copy
import json
import os
import re
from collections import deque

FORMAT = "frank-statechart/1"
KINDS = ("atomic", "compound", "parallel", "final", "history")
ID_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
OWN_ACTIONS = ("raise", "set")
MAX_MICROSTEPS = 100   # eventless transitions in a row before the chart is called stuck


class ChartError(ValueError):
    """A chart that can't run (its errors are in .issues)."""

    def __init__(self, message, issues=()):
        super().__init__(message)
        self.issues = list(issues)


# ----- files -----

def load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def save(chart, path):
    """Write the chart as readable JSON, dropping layout entries for states that are gone."""
    doc = copy.deepcopy(chart)
    ids = set(index(doc)) if isinstance(doc.get("root"), dict) else set()
    if isinstance(doc.get("layout"), dict):
        doc["layout"] = {k: v for k, v in doc["layout"].items() if k in ids}
    tmp = f"{path}.tmp"
    with open(tmp, "w", encoding="utf-8", newline="\n") as f:
        json.dump(doc, f, indent=2, ensure_ascii=False)
        f.write("\n")
    os.replace(tmp, path)


def without_layout(chart):
    doc = copy.deepcopy(chart)
    doc.pop("layout", None)
    return doc


# ----- structure -----

def kind(state):
    t = state.get("type")
    if t:
        return t
    return "compound" if state.get("states") else "atomic"


class Node:
    __slots__ = ("id", "state", "parent", "depth", "order", "children", "kind")

    def __init__(self, sid, state, parent, depth, order):
        self.id, self.state, self.parent, self.depth, self.order = sid, state, parent, depth, order
        self.children = list((state.get("states") or {}).keys())
        self.kind = kind(state)


def index(chart):
    """{id: Node} in document order (a parent comes before its children). Duplicate ids keep
    the first; check() reports them."""
    root = chart["root"]
    out = {}
    stack = [(root.get("id", "root"), root, None, 0)]
    while stack:
        sid, state, parent, depth = stack.pop()
        if sid in out:
            continue
        out[sid] = Node(sid, state, parent, depth, len(out))
        kids = list((state.get("states") or {}).items())
        for cid, child in reversed(kids):
            if isinstance(child, dict):
                stack.append((cid, child, sid, depth + 1))
    return out


def ancestors(idx, sid):
    """Proper ancestors of sid, nearest first."""
    out = []
    p = idx[sid].parent
    while p is not None:
        out.append(p)
        p = idx[p].parent
    return out


def is_descendant(idx, sid, of):
    return of in ancestors(idx, sid)


def subtree(idx, sid):
    out, stack = [], [sid]
    while stack:
        s = stack.pop()
        out.append(s)
        stack.extend(idx[s].children)
    return out


# ----- expressions -----

_ALLOWED = (ast.Expression, ast.BoolOp, ast.And, ast.Or, ast.UnaryOp, ast.Not, ast.USub, ast.UAdd,
            ast.BinOp, ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Mod, ast.Compare, ast.Eq, ast.NotEq,
            ast.Lt, ast.LtE, ast.Gt, ast.GtE, ast.In, ast.NotIn, ast.Is, ast.IsNot, ast.Name,
            ast.Load, ast.Constant, ast.IfExp, ast.Tuple, ast.List)
_COMPILED = {}


def parse_expr(text):
    """(compiled code, names used, in_state ids). Raises ValueError for anything not allowed."""
    if text in _COMPILED:
        return _COMPILED[text]
    if not isinstance(text, str) or not text.strip():
        raise ValueError("empty expression")
    try:
        tree = ast.parse(text.strip(), mode="eval")
    except SyntaxError as e:
        raise ValueError(f"not an expression: {e.msg}") from None
    names, states = set(), set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            if not (isinstance(node.func, ast.Name) and node.func.id == "in_state" and len(node.args) == 1
                    and not node.keywords and isinstance(node.args[0], ast.Constant)
                    and isinstance(node.args[0].value, str)):
                raise ValueError('the only call allowed is in_state("state id")')
            states.add(node.args[0].value)
        elif isinstance(node, ast.Subscript):
            if not (isinstance(node.value, ast.Name) and node.value.id == "data"
                    and isinstance(node.slice, ast.Constant) and isinstance(node.slice.value, str)):
                raise ValueError('the only subscript allowed is data["key"]')
        elif isinstance(node, ast.Name):
            if node.id not in ("in_state", "data", "True", "False", "None"):
                names.add(node.id)
        elif not isinstance(node, _ALLOWED):
            raise ValueError(f"{type(node).__name__} is not allowed in an expression")
    code = compile(tree, "<chart>", "eval")
    _COMPILED[text] = (code, names, states)
    return _COMPILED[text]


class _Data(dict):
    def __missing__(self, key):
        return None


# ----- checks -----

def trigger(tr):
    """The transition's trigger kind, or None if it has none or more than one."""
    kinds = [k for k in ("event", "after", "when") if k in tr]
    return kinds[0] if len(kinds) == 1 else None


def label(tr):
    k = trigger(tr)
    if k == "event":
        text = tr["event"]
    elif k == "after":
        text = f"after {tr['after']}s"
    elif k == "when":
        text = f"when {tr['when']}"
    else:
        text = "?"
    if tr.get("guard"):
        text += f" [{tr['guard']}]"
    return text


def check(chart, vocab=None):
    """Every problem found, as [{"level": "error"|"warning", "id": state id or None,
    "tr": transition index or None, "msg": text}]. Errors stop the chart from running."""
    issues = []

    def add(level, msg, sid=None, tr=None):
        issues.append({"level": level, "id": sid, "tr": tr, "msg": msg})

    if not isinstance(chart, dict):
        add("error", "a chart is a JSON object")
        return issues
    if chart.get("format") not in (None, FORMAT):
        add("warning", f'format is "{chart.get("format")}", expected "{FORMAT}"')
    root = chart.get("root")
    if not isinstance(root, dict):
        add("error", 'the chart has no "root" state')
        return issues
    root_id = root.get("id", "root")

    # every state, with duplicate ids found by walking the tree ourselves
    seen = {}
    stack = [(root_id, root, None)]
    while stack:
        sid, st, parent = stack.pop()
        if not isinstance(st, dict):
            add("error", f'state "{sid}" is not an object', parent)
            continue
        if sid in seen:
            add("error", f'two states are called "{sid}": ids must be unique in the whole chart', sid)
            continue
        seen[sid] = st
        if not isinstance(sid, str) or not ID_RE.match(sid):
            add("error", f'"{sid}" is not a valid id (letters, digits and _, not starting with a digit)', sid)
        kids = st.get("states")
        if kids is not None and not isinstance(kids, dict):
            add("error", '"states" must be an object of id: state', sid)
            continue
        for cid, child in reversed(list((kids or {}).items())):
            stack.append((cid, child, sid))
    if any(i["level"] == "error" for i in issues):
        return issues

    idx = index(chart)
    vocab = vocab or {}
    v_events = set(vocab.get("events", {}))
    v_actions = vocab.get("actions", {})
    v_profiles = set(vocab.get("profiles", {}))
    context = set((chart.get("context") or {}).keys()) | set((vocab.get("context") or {}).keys())
    raised, set_vars, targeted = set(), set(), set()

    def check_expr(text, what, sid, ti):
        try:
            _, names, states = parse_expr(text)
        except ValueError as e:
            add("error", f"{what} `{text}`: {e}", sid, ti)
            return
        for s in states:
            if s not in idx:
                add("error", f'{what} `{text}`: in_state("{s}") names no state', sid, ti)
        for n in sorted(names - context - set_vars):
            add("warning", f"{what} `{text}`: `{n}` is not a context variable", sid, ti)

    def check_actions(actions, where, sid, ti=None):
        if actions is None:
            return
        if not isinstance(actions, list):
            add("error", f"{where} must be a list of actions", sid, ti)
            return
        for a in actions:
            if not isinstance(a, dict) or not isinstance(a.get("do"), str):
                add("error", f'{where}: every action is an object with a "do"', sid, ti)
                continue
            do = a["do"]
            if do == "raise":
                if not isinstance(a.get("event"), str) or not a["event"]:
                    add("error", f'{where}: raise needs an "event"', sid, ti)
            elif do == "set":
                if not isinstance(a.get("var"), str) or not a["var"]:
                    add("error", f'{where}: set needs a "var"', sid, ti)
                if "expr" in a:
                    check_expr(a["expr"], f"{where} set {a.get('var')}", sid, ti)
            elif v_actions and do not in v_actions:
                add("warning", f'{where}: "{do}" is not an action the host knows', sid, ti)
            spec = (v_actions.get(do) or {}).get("params", {})
            for p, ps in spec.items():
                if p not in a:
                    if ps.get("required"):
                        add("error", f"{where}: {do} needs {p}", sid, ti)
                    continue
                val = a[p]
                if ps.get("type") == "number":
                    if not isinstance(val, (int, float)) or isinstance(val, bool):
                        add("error", f"{where}: {do} {p} must be a number", sid, ti)
                    elif ("min" in ps and val < ps["min"]) or ("max" in ps and val > ps["max"]):
                        add("warning", f"{where}: {do} {p} = {val} is outside {ps.get('min')}..{ps.get('max')}",
                            sid, ti)
                elif ps.get("type") == "enum" and val not in ps.get("values", []):
                    add("warning", f'{where}: {do} {p} = "{val}" is not one of {", ".join(ps.get("values", []))}',
                        sid, ti)
            if "delay" in a and (not isinstance(a["delay"], (int, float)) or a["delay"] < 0):
                add("error", f"{where}: delay must be a number of seconds, 0 or more", sid, ti)

    # names set by the chart itself count as context
    for sid, n in idx.items():
        for acts in [n.state.get("entry"), n.state.get("exit")] + [
                t.get("actions") for t in n.state.get("transitions") or [] if isinstance(t, dict)]:
            for a in acts or []:
                if isinstance(a, dict) and a.get("do") == "set" and isinstance(a.get("var"), str):
                    set_vars.add(a["var"])
                if isinstance(a, dict) and a.get("do") == "raise" and isinstance(a.get("event"), str):
                    raised.add(a["event"])
    raised |= set(chart.get("events") or {})   # events the chart says its host sends, beyond the vocabulary

    for sid, n in idx.items():
        st = n.state
        k = n.kind
        if k not in KINDS:
            add("error", f'type "{k}" is not one of {", ".join(KINDS)}', sid)
            continue
        if k in ("atomic", "final", "history") and n.children:
            add("error", f"a {k} state can't have child states", sid)
        if k in ("compound", "parallel") and not n.children:
            add("error", f"a {k} state needs child states", sid)
        if k == "parallel" and st.get("initial"):
            add("warning", "a parallel state enters all its children; its initial is ignored", sid)
        if k == "compound":
            init = st.get("initial")
            if init is not None and init not in n.children:
                add("error", f'initial "{init}" is not a child of this state', sid)
            first = init or (n.children[0] if n.children else None)
            if first and idx.get(first) and idx[first].kind == "history":
                add("error", "the initial child can't be a history state", sid)
        if k == "history":
            if n.parent is None or idx[n.parent].kind != "compound":
                add("error", "a history state must sit inside a compound state", sid)
            if st.get("history", "shallow") not in ("shallow", "deep"):
                add("error", 'history must be "shallow" or "deep"', sid)
            tgt = st.get("target")
            if tgt is not None:
                if tgt not in idx:
                    add("error", f'history target "{tgt}" names no state', sid)
                elif n.parent is not None and not is_descendant(idx, tgt, n.parent):
                    add("error", f'history target "{tgt}" must be inside "{n.parent}"', sid)
                else:
                    targeted.add(tgt)
            if st.get("transitions") or st.get("entry") or st.get("exit"):
                add("warning", "a history state only redirects; its transitions and actions are ignored", sid)
        if n.parent is None and k in ("final", "history"):
            add("error", f"the root can't be a {k} state", sid)
        if v_profiles and st.get("profile") is not None and st["profile"] not in v_profiles:
            add("warning", f'profile "{st["profile"]}" is not one the host knows ({", ".join(sorted(v_profiles))})', sid)
        if "priority" in st and not isinstance(st["priority"], (int, float)):
            add("error", "priority must be a number", sid)
        if "knobs" in st and not isinstance(st["knobs"], dict):
            add("error", "knobs must be an object", sid)
        check_actions(st.get("entry"), "entry", sid)
        check_actions(st.get("exit"), "exit", sid)
        trs = st.get("transitions")
        if trs is None:
            continue
        if not isinstance(trs, list):
            add("error", "transitions must be a list", sid)
            continue
        for ti, tr in enumerate(trs):
            if not isinstance(tr, dict):
                add("error", "a transition is an object", sid, ti)
                continue
            kinds = [x for x in ("event", "after", "when") if x in tr]
            if len(kinds) != 1:
                add("error", "a transition needs exactly one trigger: event, after or when", sid, ti)
            kk = kinds[0] if len(kinds) == 1 else None
            if kk == "event":
                ev = tr["event"]
                if not isinstance(ev, str) or not ev:
                    add("error", "event must be a name", sid, ti)
                elif v_events and ev not in v_events and ev not in raised and not ev.startswith("done.state."):
                    add("warning", f'nothing sends the event "{ev}" (not a host event, never raised)', sid, ti)
            elif kk == "after":
                if not isinstance(tr["after"], (int, float)) or isinstance(tr["after"], bool) or tr["after"] < 0:
                    add("error", "after must be a number of seconds, 0 or more", sid, ti)
            elif kk == "when":
                check_expr(tr["when"], "when", sid, ti)
                if tr.get("target") == sid and not tr.get("guard"):
                    add("warning", "a when-transition back to its own state fires again at once while true", sid, ti)
            if tr.get("guard") is not None:
                check_expr(tr["guard"], "guard", sid, ti)
            tgt = tr.get("target")
            if tgt is not None:
                if tgt not in idx:
                    add("error", f'target "{tgt}" names no state', sid, ti)
                else:
                    targeted.add(tgt)
                    if idx[tgt].parent is None:
                        add("warning", "a transition to the root restarts the whole chart", sid, ti)
            elif not tr.get("actions"):
                add("warning", "a transition with no target and no actions does nothing", sid, ti)
            check_actions(tr.get("actions"), f"transition {label(tr)}", sid, ti)

    # reachability: entered by default, or targeted (and so are its ancestors)
    reach = set()

    def enter_default(s):
        if s not in idx or s in reach:
            return
        reach.add(s)
        n = idx[s]
        if n.kind == "compound" and n.children:
            init = n.state.get("initial")
            enter_default(init if init in n.children else n.children[0])
        elif n.kind == "parallel":
            for c in n.children:
                enter_default(c)

    enter_default(root_id)
    changed = True
    while changed:
        changed = False
        for s in list(targeted):
            if s in idx and s not in reach:
                for a in [s] + ancestors(idx, s):
                    if a not in reach:
                        reach.add(a)
                        changed = True
                if idx[s].kind in ("compound", "parallel"):
                    before = len(reach)
                    enter_default(s)
                    changed = changed or len(reach) != before
        for s in list(reach):
            n = idx[s]
            if n.kind == "parallel":
                for c in n.children:
                    if c not in reach:
                        enter_default(c)
                        changed = True
    for sid, n in idx.items():
        if sid not in reach and n.kind != "history":
            add("warning", "nothing ever enters this state", sid)
    return issues


def errors(issues):
    return [i for i in issues if i["level"] == "error"]


# ----- the runtime -----

class Chart:
    """One running chart. Not thread-safe: the host calls it from one thread (or under a lock)."""

    def __init__(self, chart, vocab=None, context=None, log_size=400):
        issues = check(chart, vocab)
        bad = errors(issues)
        if bad:
            raise ChartError(f"{len(bad)} error(s): " + "; ".join(i["msg"] for i in bad[:3]), issues)
        self.doc = chart
        self.issues = issues
        self.idx = index(chart)
        self.root = chart["root"].get("id", "root")
        self.ctx = {}
        for name, spec in {**((vocab or {}).get("context") or {}), **(chart.get("context") or {})}.items():
            self.ctx[name] = spec.get("default") if isinstance(spec, dict) else spec
        self.ctx.update(context or {})
        self.active = set()
        self.entered_at = {}
        self.timers = []          # (due, seq, kind, a, b): kind "tr" (state id, index) or "raise" (event, data)
        self.seq = 0
        self.queue = deque()      # external events: (name, data)
        self.internal = deque()
        self.history = {}
        self.out = []
        self.log = deque(maxlen=log_size)
        self.logged = 0           # log entries ever written (each entry's "n")
        self.fired = []           # transitions taken since the last snapshot(): (source, index)
        self.now = 0.0
        self.started = False
        self.error = None

    # --- host calls ---

    def start(self, t=0.0):
        self.now = t
        self.started = True
        entering = self._entry_set_default(self.root)
        self._enter(entering, None)
        self._settle()
        return self

    def send(self, event, data=None):
        self.queue.append((event, dict(data or {})))

    def update(self, values=None, **kw):
        self.ctx.update(values or {}, **kw)

    def step(self, t):
        """Run everything due by time t: timers first (in time order), then the queued events,
        then any eventless transitions."""
        if not self.started:
            self.start(t)
        while self.timers:
            self.timers.sort()
            due, _, k, a, b = self.timers[0]
            if due > t:
                break
            self.timers.pop(0)
            self.now = max(self.now, due)
            if k == "tr":
                if a in self.active:
                    tr = self.idx[a].state["transitions"][b]
                    if self._guard(tr, {}):
                        self._microstep([(a, b)], {}, f"after {tr['after']}s")
            else:
                self.internal.append((a, b))
            self._settle()
        self.now = max(self.now, t)
        while self.queue:
            name, data = self.queue.popleft()
            self._event(name, data)
            self._settle()
        self._settle()

    def drain(self):
        out, self.out = self.out, []
        return out

    def configuration(self):
        return sorted(self.active, key=lambda s: self.idx[s].order)

    def leaves(self):
        return [s for s in self.configuration() if not any(c in self.active for c in self.idx[s].children)]

    def profile(self):
        best = None
        for s in self.active:
            st = self.idx[s].state
            if st.get("profile") is None:
                continue
            key = (self._priority(s), self.idx[s].depth, -self.idx[s].order)
            if best is None or key > best[0]:
                best = (key, st["profile"])
        return best[1] if best else None

    def knobs(self):
        out = {}
        for s in sorted(self.active, key=lambda s: (self._priority(s), self.idx[s].depth, self.idx[s].order)):
            out.update(self.idx[s].state.get("knobs") or {})
        return out

    def in_state(self, sid):
        return sid in self.active

    def snapshot(self):
        fired, self.fired = self.fired, []
        return {
            "t": round(self.now, 4),
            "active": self.configuration(),
            "leaves": self.leaves(),
            "profile": self.profile(),
            "knobs": self.knobs(),
            "context": dict(self.ctx),
            "timers": [{"due": round(d, 3), "state": a, "tr": b} if k == "tr" else
                       {"due": round(d, 3), "raise": a} for d, _, k, a, b in sorted(self.timers)],
            "fired": fired,
            "error": self.error,
        }

    # --- inside ---

    def _priority(self, sid):
        """A state's priority: its own, else its nearest ancestor's, else 0."""
        for s in [sid] + ancestors(self.idx, sid):
            p = self.idx[s].state.get("priority")
            if p is not None:
                return p
        return 0

    def _note(self, kind, **kw):
        self.logged += 1
        self.log.append(dict(n=self.logged, t=round(self.now, 4), kind=kind, **kw))

    def _eval(self, text, data):
        code, _, _ = parse_expr(text)
        names = dict(self.ctx)
        names.update(in_state=self.in_state, data=_Data(data or {}))
        try:
            return eval(code, {"__builtins__": {}}, names)  # noqa: S307 - parse_expr allows only plain expressions
        except Exception as e:
            self.error = f"`{text}`: {type(e).__name__}: {e}"
            self._note("error", msg=self.error)
            return False

    def _guard(self, tr, data):
        g = tr.get("guard")
        return True if g is None else bool(self._eval(g, data))

    def _event(self, name, data):
        self._note("event", event=name, data=data or None)
        picks = self._select(lambda tr: tr.get("event") == name and trigger(tr) == "event", data)
        if picks:
            self._microstep(picks, data, name)

    def _settle(self):
        """Eventless transitions and raised events, until nothing more happens."""
        for _ in range(MAX_MICROSTEPS):
            picks = self._select(lambda tr: trigger(tr) == "when", {}, when=True)
            if picks:
                self._microstep(picks, {}, "when")
                continue
            if self.internal:
                name, data = self.internal.popleft()
                self._event(name, data)
                continue
            return
        self.error = "eventless transitions kept firing: stopped after %d in a row" % MAX_MICROSTEPS
        self._note("error", msg=self.error)

    def _select(self, match, data, when=False):
        """The enabled transitions, one per active leaf (its own first, then its ancestors'),
        minus any whose exit sets overlap an earlier one."""
        picks, seen = [], set()
        for leaf in self.leaves():
            for s in [leaf] + ancestors(self.idx, leaf):
                found = None
                for i, tr in enumerate(self.idx[s].state.get("transitions") or []):
                    if not match(tr):
                        continue
                    if when and not self._eval(tr["when"], data):
                        continue
                    if self._guard(tr, data):
                        found = (s, i)
                        break
                if found:
                    if found not in seen:
                        seen.add(found)
                        picks.append(found)
                    break
        kept, exits = [], set()
        for p in picks:
            ex = set(self._exit_set(*p))
            if ex & exits:
                continue
            exits |= ex
            kept.append(p)
        return kept

    def _target(self, src, i):
        return self.idx[src].state["transitions"][i].get("target")

    def _child_towards(self, top, sid):
        """The child of top that is sid or contains it."""
        for a in [sid] + ancestors(self.idx, sid):
            if self.idx[a].parent == top:
                return a
        return None

    def _plan(self, src, i):
        """What a transition leaves and enters: (scopes, entries). Every active state in a
        scope's subtree (the scope included) is exited; each entry is (state, top): that state,
        its default descendants and its ancestors below top are entered. The rules:
          - to its own source: leave and re-enter the source (unless reenter is false);
          - to a state inside the source: leave only the source's child on the way (the active
            child of a compound source; the target's region of a parallel one), unless reenter;
          - elsewhere: below the nearest common ancestor, leave the source's branch; if that
            ancestor is a parallel state, also re-enter the target's region and send the
            source's region back to its initial state. Other regions are left alone."""
        tr = self.idx[src].state["transitions"][i]
        tgt = tr.get("target")
        if tgt is None:
            return [], []
        idx = self.idx
        if tgt == src or is_descendant(idx, tgt, src):
            if tr.get("reenter", tgt == src):
                return [src], [(tgt, idx[src].parent)]
            if tgt == src:   # reenter: false on a transition to itself: nothing leaves or enters
                return [], []
            c = self._child_towards(src, tgt)
            if idx[src].kind == "parallel":
                return [c], [(tgt, src)]
            return [k for k in idx[src].children if k in self.active] + [c], [(tgt, src)]
        tanc = set([tgt] + ancestors(idx, tgt))
        common = next((a for a in ancestors(idx, src) if a in tanc), None)
        cs, ct = self._child_towards(common, src), self._child_towards(common, tgt)
        if idx[common].kind == "parallel":
            return [cs, ct], [(tgt, common), (cs, common)]
        return [cs], [(tgt, common)]

    def _exit_set(self, src, i):
        scopes, _ = self._plan(src, i)
        return [s for s in self.active if any(s == r or is_descendant(self.idx, s, r) for r in scopes)]

    def _entry_set_default(self, sid):
        out = []
        self._add_descendants(sid, out)
        return out

    def _add_descendants(self, sid, out):
        n = self.idx[sid]
        if n.kind == "history":
            stored = self.history.get(sid)
            if stored:
                for s in stored:
                    self._add_descendants(s, out)
                    self._add_ancestors(s, n.parent, out)
            else:
                dflt = n.state.get("target") or self._initial(n.parent)
                self._add_descendants(dflt, out)
                self._add_ancestors(dflt, n.parent, out)
            return
        if sid not in out:
            out.append(sid)
        if n.kind == "compound":
            if not any(c in out or any(is_descendant(self.idx, o, c) for o in out) for c in n.children):
                self._add_descendants(self._initial(sid), out)
        elif n.kind == "parallel":
            for c in n.children:
                if not any(o == c or is_descendant(self.idx, o, c) for o in out):
                    self._add_descendants(c, out)

    def _add_ancestors(self, sid, top, out):
        for a in ancestors(self.idx, sid):
            if a == top:
                break
            if a not in out:
                out.append(a)
            if self.idx[a].kind == "parallel":
                for c in self.idx[a].children:
                    if not any(o == c or is_descendant(self.idx, o, c) for o in out):
                        self._add_descendants(c, out)

    def _initial(self, sid):
        n = self.idx[sid]
        return n.state.get("initial") or n.children[0]

    def _microstep(self, picks, data, why):
        exits, entering = set(), []
        for src, i in picks:
            exits |= set(self._exit_set(src, i))
        for src, i in picks:
            for state, top in self._plan(src, i)[1]:
                path = []
                self._add_descendants(state, path)
                if top is not None:
                    self._add_ancestors(state, top, path)
                for s in path:
                    if s not in entering:
                        entering.append(s)
        self._exit(exits)
        for src, i in picks:
            tr = self.idx[src].state["transitions"][i]
            self.fired.append([src, i])
            self._note("transition", source=src, index=i, target=tr.get("target"), trigger=label(tr), why=why)
            self._run(tr.get("actions"), data, f"{src} → {tr.get('target') or '(stay)'}")
        self._enter([s for s in entering if s not in self.active or s in exits], data)

    def _exit(self, states):
        states = sorted((s for s in states if s in self.active), key=lambda s: self.idx[s].order, reverse=True)
        for s in states:   # history first, while the whole configuration is still there
            n = self.idx[s]
            for h in n.children:
                hn = self.idx[h]
                if hn.kind == "history":
                    if hn.state.get("history", "shallow") == "deep":
                        self.history[h] = [x for x in self.configuration() if is_descendant(self.idx, x, s)
                                           and not any(c in self.active for c in self.idx[x].children)]
                    else:
                        self.history[h] = [c for c in n.children if c in self.active]
        for s in states:
            n = self.idx[s]
            self._run(n.state.get("exit"), {}, f"exit {s}")
            self.active.discard(s)
            self.entered_at.pop(s, None)
            self.timers = [x for x in self.timers if not (x[2] == "tr" and x[3] == s)]
            self._note("exit", state=s)

    def _enter(self, states, data):
        for s in sorted(set(states), key=lambda s: self.idx[s].order):
            n = self.idx[s]
            if n.kind == "history":
                continue
            self.active.add(s)
            self.entered_at[s] = self.now
            self._note("enter", state=s)
            for i, tr in enumerate(n.state.get("transitions") or []):
                if trigger(tr) == "after":
                    self.seq += 1
                    self.timers.append((self.now + float(tr["after"]), self.seq, "tr", s, i))
            self._run(n.state.get("entry"), data, f"enter {s}")
            if n.kind == "final" and n.parent is not None:
                self.internal.append((f"done.state.{n.parent}", {}))
                gp = self.idx[n.parent].parent
                if gp is not None and self.idx[gp].kind == "parallel":
                    regions = self.idx[gp].children
                    if all(any(c in self.active and self.idx[c].kind == "final" for c in self.idx[r].children)
                           or r == n.parent for r in regions):
                        self.internal.append((f"done.state.{gp}", {}))

    def _run(self, actions, data, where):
        for a in actions or []:
            do = a.get("do")
            if do == "raise":
                delay = float(a.get("delay") or 0)
                if delay > 0:
                    self.seq += 1
                    self.timers.append((self.now + delay, self.seq, "raise", a["event"], dict(a.get("data") or {})))
                else:
                    self.internal.append((a["event"], dict(a.get("data") or {})))
                self._note("raise", event=a["event"], delay=delay or None, where=where)
            elif do == "set":
                value = self._eval(a["expr"], data) if "expr" in a else a.get("value")
                self.ctx[a["var"]] = value
                self._note("set", var=a["var"], value=value, where=where)
            else:
                act = {k: v for k, v in a.items()}
                self.out.append({"t": self.now, **act})
                self._note("action", action=act, where=where)

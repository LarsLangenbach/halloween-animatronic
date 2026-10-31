"""
Offline tests for the statechart runtime and checks (frank/statechart/chart.py).

    .venv\\Scripts\\python.exe frank\\statechart\\tests\\test_chart.py
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
sys.stdout.reconfigure(encoding="utf-8")

from statechart.chart import Chart, ChartError, check, errors, load, parse_expr  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
VOCAB = load(os.path.join(HERE, "..", "vocab.json"))


def chart(states, root_type="compound", **root):
    return {"format": "frank-statechart/1", "name": "t",
            "root": {"id": "root", "type": root_type, "states": states, **root}}


def test_compound_initial_and_event():
    c = Chart(chart({"a": {"transitions": [{"event": "go", "target": "b"}]}, "b": {}})).start(0)
    assert c.leaves() == ["a"]
    c.send("go")
    c.step(0.1)
    assert c.leaves() == ["b"], c.leaves()


def test_after_timer_and_cancel_on_exit():
    c = Chart(chart({
        "a": {"transitions": [{"after": 1.0, "target": "b"}, {"event": "away", "target": "c"}]},
        "b": {}, "c": {"transitions": [{"event": "back", "target": "a"}]}})).start(0)
    c.step(0.5)
    assert c.leaves() == ["a"]
    c.send("away")
    c.step(0.6)
    c.step(2.0)
    assert c.leaves() == ["c"], "the timer of a state that was left must not fire"
    c.send("back")
    c.step(2.1)
    c.step(3.0)
    assert c.leaves() == ["a"]
    c.step(3.15)
    assert c.leaves() == ["b"], "re-entering restarts the timer"


def test_chained_timers_within_one_step():
    c = Chart(chart({"a": {"transitions": [{"after": 0.5, "target": "b"}]},
                     "b": {"transitions": [{"after": 0.3, "target": "c"}]}, "c": {}})).start(0)
    c.step(1.0)
    assert c.leaves() == ["c"]
    entered = [e for e in c.log if e["kind"] == "enter" and e["state"] == "c"][0]
    assert abs(entered["t"] - 0.8) < 1e-9, entered


def test_parallel_regions_and_priority():
    doc = chart({
        "talk": {"priority": 1, "initial": "quiet", "states": {
            "quiet": {"profile": "idle", "knobs": {"blink": 17}},
            "loud": {"profile": "speaking", "knobs": {"blink": 26}}},
            "transitions": [{"event": "speak", "target": "loud"}]},
        "body": {"initial": "still", "states": {
            "still": {}, "carried": {"profile": "carried", "knobs": {"blink": 30, "alarm": 1}}},
            "transitions": [{"event": "lift", "target": "carried"}]},
    }, root_type="parallel")
    c = Chart(doc).start(0)
    assert set(c.leaves()) == {"quiet", "still"}
    assert c.profile() == "idle"
    c.send("lift")
    c.step(0.1)
    assert c.profile() == "idle", "the higher-priority region's profile wins"
    assert c.knobs() == {"blink": 17, "alarm": 1}, c.knobs()
    c.send("speak")
    c.step(0.2)
    assert set(c.leaves()) == {"loud", "carried"}, "a transition in one region leaves the other alone"


def test_cross_region_reenters_parallel():
    doc = chart({
        "r1": {"initial": "x", "states": {"x": {"transitions": [{"event": "jump", "target": "q"}]}, "y": {}}},
        "r2": {"initial": "p", "states": {"p": {}, "q": {}}},
    }, root_type="parallel")
    c = Chart(doc).start(0)
    c.send("jump")
    c.step(0.1)
    assert set(c.leaves()) == {"x", "q"}, c.leaves()


def test_when_and_guard_and_in_state():
    doc = chart({
        "idle": {"transitions": [{"when": "people > 0", "target": "seen"}]},
        "seen": {"transitions": [{"event": "hi", "guard": "in_state(\"seen\") and loud", "target": "talk"},
                                 {"when": "people == 0", "target": "idle"}]},
        "talk": {}}, context={"people": {"type": "number", "default": 0}, "loud": {"type": "bool", "default": False}})
    doc["context"] = doc["root"].pop("context")
    c = Chart(doc).start(0)
    c.update(people=2)
    c.step(0.1)
    assert c.leaves() == ["seen"]
    c.send("hi")
    c.step(0.2)
    assert c.leaves() == ["seen"], "guard false: stay"
    c.update(loud=True)
    c.send("hi")
    c.step(0.3)
    assert c.leaves() == ["talk"]


def test_child_transition_beats_ancestor():
    doc = chart({"outer": {"initial": "a", "states": {
        "a": {"transitions": [{"event": "e", "target": "b"}]}, "b": {}},
        "transitions": [{"event": "e", "target": "c"}]}, "c": {}})
    c = Chart(doc).start(0)
    c.send("e")
    c.step(0.1)
    assert c.leaves() == ["b"]
    c.send("e")
    c.step(0.2)
    assert c.leaves() == ["c"], "b has no handler, so its ancestor's fires"


def test_history_shallow_and_deep():
    def doc(depth):
        return chart({
            "work": {"initial": "one", "states": {
                "h": {"type": "history", "history": depth},
                "one": {"transitions": [{"event": "next", "target": "two"}]},
                "two": {"initial": "two_a", "states": {
                    "two_a": {"transitions": [{"event": "next", "target": "two_b"}]}, "two_b": {}}}},
                "transitions": [{"event": "pause", "target": "break"}]},
            "break": {"transitions": [{"event": "resume", "target": "h"}]}})
    for depth, expect in (("shallow", "two_a"), ("deep", "two_b")):
        c = Chart(doc(depth)).start(0)
        for i, ev in enumerate(("next", "next", "pause", "resume")):
            c.send(ev)
            c.step(i * 0.1 + 0.1)
        assert c.leaves() == [expect], (depth, c.leaves())


def test_self_transition_reenters_and_inside_does_not():
    doc = chart({"a": {"entry": [{"do": "log", "text": "in"}], "initial": "a1", "states": {"a1": {}, "a2": {}},
                       "transitions": [{"event": "again", "target": "a"},
                                       {"event": "down", "target": "a2"}]}})
    c = Chart(doc).start(0)
    c.drain()
    c.send("down")
    c.step(0.1)
    assert c.leaves() == ["a2"] and not c.drain(), "a child target doesn't re-enter the parent"
    c.send("again")
    c.step(0.2)
    assert c.leaves() == ["a1"] and [a["text"] for a in c.drain()] == ["in"], "a self-target re-enters"


def test_actions_raise_set_and_host():
    doc = chart({"a": {"entry": [{"do": "set", "var": "n", "value": 1},
                                 {"do": "raise", "event": "later", "delay": 0.5},
                                 {"do": "tag", "tag": "curious", "intensity": 0.6, "delay": 0.15}],
                       "transitions": [{"event": "later", "target": "b",
                                        "actions": [{"do": "set", "var": "n", "expr": "n + 1"}]}]},
                 "b": {}})
    c = Chart(doc).start(0)
    out = c.drain()
    assert out == [{"t": 0, "do": "tag", "tag": "curious", "intensity": 0.6, "delay": 0.15}], out
    c.step(0.4)
    assert c.leaves() == ["a"]
    c.step(0.6)
    assert c.leaves() == ["b"] and c.ctx["n"] == 2, (c.leaves(), c.ctx)


def test_done_event():
    doc = chart({"job": {"initial": "s1", "states": {
        "s1": {"transitions": [{"event": "fin", "target": "end"}]}, "end": {"type": "final"}},
        "transitions": [{"event": "done.state.job", "target": "after"}]}, "after": {}})
    c = Chart(doc).start(0)
    c.send("fin")
    c.step(0.1)
    assert c.leaves() == ["after"], c.leaves()


def test_eventless_loop_is_stopped():
    doc = chart({"a": {"transitions": [{"when": "True", "target": "b"}]},
                 "b": {"transitions": [{"when": "True", "target": "a"}]}})
    c = Chart(doc).start(0)
    assert c.error and "kept firing" in c.error


def test_expressions_are_sandboxed():
    for bad in ("__import__('os')", "x.__class__", "open('f')", "[i for i in x]", "lambda: 1", "a[0]"):
        try:
            parse_expr(bad)
        except ValueError:
            continue
        raise AssertionError(f"accepted {bad!r}")
    _, names, states = parse_expr('speaking and not thinking or in_state("idle") and data["n"] > 1')
    assert names == {"speaking", "thinking"} and states == {"idle"}


def test_checks():
    bad = chart({
        "a": {"transitions": [{"event": "go", "target": "nowhere"},
                              {"event": "x", "after": 1, "target": "b"},
                              {"when": "speaking +", "target": "b"},
                              {"event": "go", "actions": [{"do": "tag", "tag": "happy"}]}]},
        "b": {"type": "atomic", "states": {"c": {}}},
        "lonely": {}})
    msgs = [(i["level"], i["msg"]) for i in check(bad, VOCAB)]
    text = " | ".join(m for _, m in msgs)
    for want in ('target "nowhere" names no state', "exactly one trigger", "not an expression",
                 "can't have child states", "nothing ever enters this state", "is not one of"):
        assert want in text, (want, text)
    try:
        Chart(bad)
    except ChartError as e:
        assert e.issues
    else:
        raise AssertionError("a chart with errors must not run")
    dup = chart({"a": {"states": {"x": {}}}, "b": {"states": {"x": {}}}})
    assert any("two states are called" in i["msg"] for i in errors(check(dup)))


def test_seed_chart_is_clean():
    doc = load(os.path.join(HERE, "..", "charts", "frank.json"))
    issues = check(doc, VOCAB)
    assert not issues, issues


if __name__ == "__main__":
    tests = [(n, f) for n, f in sorted(globals().items()) if n.startswith("test_") and callable(f)]
    for name, fn in tests:
        fn()
    print(f"chart OK: {len(tests)} tests")

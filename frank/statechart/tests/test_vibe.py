"""
Offline tests for vibe-coding (frank/statechart/vibe.py), with a stand-in for the anthropic
package: no key and no network. A real request needs `--with anthropic` and frank/.env.

    .venv\\Scripts\\python.exe frank\\statechart\\tests\\test_vibe.py
"""

import json
import os
import sys
import time
import types

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
sys.stdout.reconfigure(encoding="utf-8")

from statechart import vibe  # noqa: E402
from statechart.chart import load  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
VOCAB = load(os.path.join(HERE, "..", "vocab.json"))
CHART = load(os.path.join(HERE, "..", "charts", "frank.json"))


class Block:
    def __init__(self, text):
        self.type, self.text = "text", text


class Usage:
    def to_dict(self):
        return {"input_tokens": 1, "output_tokens": 1}


class Msg:
    def __init__(self, text, stop="end_turn"):
        self.content, self.stop_reason, self.usage = [Block(text)], stop, Usage()


class Stream:
    def __init__(self, msg):
        self.msg = msg
        self.text_stream = iter([msg.content[0].text])

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def get_final_message(self):
        return self.msg


def fake_anthropic(replies, seen):
    """A module that answers each stream() call with the next reply."""
    mod = types.ModuleType("anthropic")
    for name in ("AuthenticationError", "RateLimitError", "APIConnectionError", "APIStatusError"):
        setattr(mod, name, type(name, (Exception,), {}))

    class Messages:
        def stream(self, **kw):
            seen.append(kw)
            return Stream(replies.pop(0))

    class Client:
        def __init__(self):
            self.beta = types.SimpleNamespace(messages=Messages())

    mod.Anthropic = Client
    return mod


def ask(replies, request="make it sleepy"):
    seen = []
    sys.modules["anthropic"] = fake_anthropic(list(replies), seen)
    job = vibe.Job(CHART, request, [{"request": "earlier", "summary": "did a thing"}], VOCAB)
    for _ in range(200):
        if job.state != "running":
            break
        time.sleep(0.01)
    return job, seen


def with_sleepy(target="sleepy"):
    doc = json.loads(json.dumps(CHART))
    auto = doc["root"]["states"]["social"]["states"]["auto"]["states"]
    auto["sleepy"] = {"profile": "idle", "note": "bored"}
    auto["idle"]["transitions"].append({"after": 120, "target": target})
    return doc


def test_edit():
    reply = "Added a sleepy state after two minutes alone.\n```json\n" + json.dumps(with_sleepy()) + "\n```"
    job, seen = ask([Msg(reply)])
    r = job.result
    assert job.state == "done" and r["ok"], r
    assert r["summary"].startswith("Added a sleepy state") and "```" not in r["summary"]
    assert "sleepy" in r["chart"]["root"]["states"]["social"]["states"]["auto"]["states"]
    kw = seen[0]
    assert kw["model"] == vibe.MODEL and kw["fallbacks"] == "default" and kw["output_config"] == {"effort": "medium"}
    assert kw["system"][0]["cache_control"] == {"type": "ephemeral"}
    first = kw["messages"][0]
    assert first == {"role": "user", "content": "earlier"}, "the earlier exchange comes first"
    last = kw["messages"][-1]["content"]
    assert '"layout"' not in last and "My request: make it sleepy" in last


def test_repair_round():
    broken = "Here.\n```json\n" + json.dumps(with_sleepy(target="snoozing")) + "\n```"
    fixed = "Fixed the target.\n```json\n" + json.dumps(with_sleepy()) + "\n```"
    job, seen = ask([Msg(broken), Msg(fixed)])
    assert job.result["ok"] and len(seen) == 2, job.result
    assert 'target "snoozing" names no state' in seen[1]["messages"][-1]["content"]


def test_words_only_and_refusal():
    job, _ = ask([Msg("It has three regions: social, body and senses.")], "explain it")
    assert job.result["ok"] and job.result["chart"] is None and "three regions" in job.result["summary"]
    job, _ = ask([Msg("", stop="refusal")])
    assert not job.result["ok"] and "declined" in job.result["error"]


def test_system_prompt():
    text = vibe.system_prompt(VOCAB)
    for want in ("frank-statechart/1", '"arrived"', "COMPLETE updated chart", "Expressions"):
        assert want in text, want
    assert "FACE AND EXPRESSIONS" in text, "the character bible's face section is included"


if __name__ == "__main__":
    real = sys.modules.get("anthropic")
    try:
        tests = [(n, f) for n, f in sorted(globals().items()) if n.startswith("test_") and callable(f)]
        for name, fn in tests:
            fn()
    finally:
        if real is not None:
            sys.modules["anthropic"] = real
    print(f"vibe OK: {len(tests)} tests")

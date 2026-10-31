"""
Vibe-coding a chart: a request in plain words in, Claude's new version of the whole chart out.

The editor sends the current chart (without its layout) and the request; Claude answers with a
short summary in plain words and the complete updated chart in one ```json block, or with words
only when the request is a question. The chart is checked; if it has errors, Claude gets them
and one more go. The editor then shows what changed and the human accepts or rejects it.

Needs the anthropic package and a key in frank/.env (or the environment), as frank/brain.py.
"""

import json
import re
import threading
import time
import uuid
from pathlib import Path

from .chart import FORMAT, check, errors, without_layout

MODEL = "claude-opus-5-5"
EFFORT = "medium"
MAX_TOKENS = 64000
HERE = Path(__file__).resolve().parent
CHARACTER = HERE.parent.parent / "docs" / "CHARACTER.md"
JSON_BLOCK = re.compile(r"```json\s*(.*?)```", re.S)

FORMAT_SPEC = f"""\
A chart is JSON:
{{"format": "{FORMAT}", "name": "...", "host": "frank-engine", "description": "...",
 "context": {{"var": {{"type": "bool"|"number"|"string", "default": ..., "doc": "..."}}}},
 "root": {{"id": "...", "type": "parallel"|"compound", "states": {{...}}}}}}

States. Every state id is unique in the whole chart (its key in its parent's "states"; letters,
digits and _, not starting with a digit). A state may have:
- type: atomic (no children) | compound (children, one active at a time) | parallel (all
  children active at once; its children are "regions") | final | history. Leave it out for
  atomic and compound: it is inferred from whether there are "states".
- initial: for a compound state, the child entered first (default: the first child).
- states: {{id: state}}
- profile: the face engine's behaviour in this state (one of the host's profiles). A state
  without one takes its nearest ancestor's. Exactly one profile drives the face at a time.
- priority: number; when several active states give a profile or knobs, the highest priority
  wins (ancestors' priority is inherited). The social region uses priority 1.
- knobs: {{name: value}} extra settings for the host, merged by priority (the engine ignores
  knobs it doesn't know, so only use them when asked).
- entry, exit: lists of actions run on entering and leaving.
- transitions: a list, checked in order (the first enabled one fires). Each has exactly ONE
  trigger: "event": "name" | "after": seconds (since the state was entered) | "when": "expr"
  (fires as soon as it is true; checked every 20 ms tick). Optional: "target" (a state id; left
  out = stay put and only run the actions), "guard": "expr", "actions": [...],
  "reenter": true|false, "note": "plain words".
- history: in a history state, "shallow" or "deep"; its "target" is the default.
- note: plain words about the state.

How transitions run: an event is offered to each active leaf state first, then to its
ancestors, so a transition on a parent applies to all its children unless a child handles the
event itself. A transition to a state inside its source leaves only the source's child on the
way; a transition to its own source leaves and re-enters it (restarting its "after" timers);
leaving one region of a parallel state for another sends the source's region back to its
initial state; other regions are never disturbed. After every change, "when" transitions run
until nothing more fires (a when-transition whose expression stays true and leads back to
itself would loop; the runtime stops it after 100 steps).

Expressions (guard, when, set expr) are small Python expressions over the context variables:
and, or, not, == != < <= > >=, + - * / %, numbers, strings, True, False, in_state("id"),
data["key"] (the current event's data). No other calls, attributes or subscripts.

Actions are objects with a "do": "raise" (send an event to this chart, optional "delay"
seconds) and "set" ("var" and "value", or "expr") are run by the chart; tag, nudge, anim and log
go to the face engine (see the vocabulary for their parameters; "delay" is honoured)."""

RULES = """\
How to answer:
1. Start with a short summary in plain, everyday words of what you changed and why (2 to 6
   short lines; the person reading it is not a programmer). Mention anything you couldn't do
   because the engine doesn't offer it, and what you did instead.
2. Then give the COMPLETE updated chart in one ```json block, every state included, ready to
   save. Leave out "layout" (the editor keeps positions). Keep everything the request doesn't
   touch exactly as it was: same ids, same order, same notes.
3. If the request is a question, a request for an explanation or review, or too unclear to
   act on, answer in words only, with no JSON block. For a review, list concrete problems.
4. Only use the host's events, context variables, actions and profiles from the vocabulary,
   plus events the chart raises itself. Give new states clear snake_case ids and a short note.
5. Keep it valid: one trigger per transition, existing targets, unique ids, a compound
   state's initial among its children, and no when-transition that can loop.
6. Frank's character (below) decides what feels right. Timing matters: no two big changes at
   once, expressions that settle, nothing flip-flopping faster than about a second."""


def character_excerpt():
    """CHARACTER.md section 6 (the face), so creative requests stay in character."""
    try:
        text = CHARACTER.read_text(encoding="utf-8")
    except OSError:
        return ""
    m = re.search(r"^# 6\. FACE AND EXPRESSIONS.*?(?=^# 7\.)", text, re.S | re.M)
    return m.group(0).strip() if m else ""


def system_prompt(vocab):
    parts = [
        "You edit statecharts for Frank's face engine. Frank is a talking animatronic head in a "
        "jar (a Frankenstein-style character, life size) at a Halloween hackathon. A chart decides "
        "which conversation state his face is in and which expressions and mood nudges fire on "
        "events; the engine does the moving (gaze, blinks, springs, servos). A human edits the "
        "chart in a node editor and asks you for changes in plain words.",
        FORMAT_SPEC,
        "The host's vocabulary (what the face engine sends and does):\n```json\n"
        + json.dumps(vocab, indent=1, ensure_ascii=False) + "\n```",
        RULES,
    ]
    ch = character_excerpt()
    if ch:
        parts.append("Frank's face, from his character bible:\n" + ch)
    return "\n\n".join(parts)


def _text(msg):
    """The reply's text. After a fallback switch, only the model that finished the reply counts."""
    blocks = list(msg.content)
    last = max((i for i, b in enumerate(blocks) if b.type == "fallback"), default=-1)
    return "".join(b.text for i, b in enumerate(blocks) if i > last and b.type == "text")


def split_reply(text):
    """(summary, chart or None, parse error or None)."""
    blocks = JSON_BLOCK.findall(text)
    summary = JSON_BLOCK.sub("", text).strip()
    if not blocks:
        return summary, None, None
    try:
        chart = json.loads(blocks[-1])
    except json.JSONDecodeError as e:
        return summary, None, f"the chart isn't valid JSON: {e}"
    if not isinstance(chart, dict):
        return summary, None, "the chart isn't a JSON object"
    return summary, chart, None


class Job:
    """One request to Claude, run in a thread; the editor polls it."""

    def __init__(self, chart, request, history, vocab, model=MODEL):
        self.id = uuid.uuid4().hex[:12]
        self.state, self.partial, self.result, self.started = "running", "", None, time.time()
        self.chart, self.request, self.history, self.vocab, self.model = chart, request, history, vocab, model
        threading.Thread(target=self._run, daemon=True).start()

    def status(self):
        return {"id": self.id, "state": self.state, "partial": self.partial,
                "seconds": round(time.time() - self.started, 1), "result": self.result}

    def _run(self):
        try:
            self.result = self._ask()
            self.state = "done" if self.result.get("ok") else "error"
        except Exception as e:  # anything unexpected still reaches the page
            self.result = {"ok": False, "error": f"{type(e).__name__}: {e}"}
            self.state = "error"

    def _call(self, client, system, messages):
        import anthropic
        self.partial = ""
        try:
            with client.beta.messages.stream(
                model=self.model,
                max_tokens=MAX_TOKENS,
                betas=["server-side-fallback-2026-07-01"],
                fallbacks="default",
                output_config={"effort": EFFORT},
                system=[{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}],
                messages=messages,
            ) as stream:
                for delta in stream.text_stream:
                    self.partial += delta
                msg = stream.get_final_message()
        except anthropic.AuthenticationError:
            return None, "the API key was refused: check ANTHROPIC_API_KEY in frank/.env"
        except anthropic.RateLimitError:
            return None, "rate limited by the API: try again in a minute"
        except anthropic.APIConnectionError:
            return None, "couldn't reach the API: is the internet on?"
        except anthropic.APIStatusError as e:
            return None, f"the API said {e.status_code}: {e.message}"
        if msg.stop_reason == "refusal":
            return None, "Claude declined this request"
        if msg.stop_reason == "max_tokens":
            return None, "the reply was cut off (the chart is too long for one reply)"
        return msg, None

    def _ask(self):
        try:
            import anthropic
        except ImportError:
            return {"ok": False, "error": "the anthropic package isn't installed: start the editor with "
                                          "uv run --no-project --with anthropic python frank/statechart/editor.py"}
        import sys
        sys.path.insert(0, str(HERE.parent))
        from brain import load_env   # frank/.env holds the keys
        load_env()
        client = anthropic.Anthropic()
        system = system_prompt(self.vocab)
        current = without_layout(self.chart)
        issues = check(self.chart, self.vocab)
        problems = "\n".join(f"- {i['level']}: {i['id'] or 'chart'}: {i['msg']}" for i in issues) or "none"
        messages = []
        for turn in self.history[-6:]:
            if turn.get("request") and turn.get("summary"):
                messages += [{"role": "user", "content": turn["request"]},
                             {"role": "assistant", "content": turn["summary"]}]
        messages.append({"role": "user", "content":
                         f"The chart as it is now:\n```json\n{json.dumps(current, indent=1, ensure_ascii=False)}\n```\n\n"
                         f"What the checker says about it now:\n{problems}\n\nMy request: {self.request}"})
        msg, err = self._call(client, system, messages)
        if err:
            return {"ok": False, "error": err}
        text = _text(msg)
        summary, chart, perr = split_reply(text)
        usage = [msg.usage.to_dict()]
        if chart is None and perr is None:
            return {"ok": True, "summary": summary, "chart": None, "issues": [], "usage": usage}
        bad = [perr] if perr else [i["msg"] for i in errors(check(chart, self.vocab))]
        if bad:   # one more go, with the checker's errors
            messages += [{"role": "assistant", "content": text},
                         {"role": "user", "content": "The checker found these errors in that chart:\n"
                          + "\n".join(f"- {b}" for b in bad)
                          + "\nSend the corrected complete chart (summary line, then the json block)."}]
            msg, err = self._call(client, system, messages)
            if err:
                return {"ok": False, "error": err}
            usage.append(msg.usage.to_dict())
            fixed_summary, chart, perr = split_reply(_text(msg))
            summary = summary or fixed_summary
            if perr or chart is None:
                return {"ok": False, "error": perr or "Claude didn't send a corrected chart", "summary": summary}
        chart.setdefault("format", FORMAT)
        return {"ok": True, "summary": summary, "chart": chart, "issues": check(chart, self.vocab), "usage": usage}

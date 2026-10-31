"""
Frank's brain: one conversation with one AI model, streamed.

The same code drives Claude and OpenAI models, so the bake-off (bakeoff.py) and the
live loop use the same calls. API keys come from the environment or from frank/.env
(copy .env.example): ANTHROPIC_API_KEY, OPENAI_API_KEY.

A turn is what the visitor said (or "(no speech)"), then any context notes, then
Frank's streamed reply. The history is append-only (README, "One turn"):

    convo = Conversation("haiku-5.5")
    convo.add_turn("Hello!", notes=["Present: one stranger."])
    for event in convo.stream():
        ...   # ("text", delta), ("tool", name, input), then ("done", info)
"""

import json
import os
from pathlib import Path

HERE = Path(__file__).parent
SYSTEM_PROMPT = (HERE / "system_prompt.md").read_text(encoding="utf-8")

# The candidate brains. IDs and settings are from the providers' docs (2026-10-26).
# Reasoning is off or as low as each model allows, because it delays the first word.
MODELS = {
    "haiku-5.5": dict(provider="anthropic", model="claude-haiku-5-5",
                      effort="low", thinking={"type": "disabled"}),
    "sonnet-5.5": dict(provider="anthropic", model="claude-sonnet-5-5",
                       effort="low", thinking={"type": "between_tools"}, fallbacks=True),
    "opus-5.5": dict(provider="anthropic", model="claude-opus-5-5",  # thinking can't be turned off
                     effort="low", fallbacks=True),
    "gpt-5.4-mini": dict(provider="openai", model="gpt-5.4-mini", reasoning_effort="none"),
}
KEY_ENV = {"anthropic": "ANTHROPIC_API_KEY", "openai": "OPENAI_API_KEY"}
MAX_TOKENS = 4096  # replies are a few sentences; this is only a ceiling

TOOLS = [
    dict(name="remember_person",
         description="Remember the visitor Frank is talking to, as soon as they have told him "
                     "their first name. Links their face to the name so he knows them next time, "
                     "and starts a memory of them. Not for children, and not for anyone already "
                     "recognised.",
         schema={"type": "object", "additionalProperties": False,
                 "required": ["first_name", "notes"],
                 "properties": {
                     "first_name": {"type": "string"},
                     "notes": {"type": "string",
                               "description": "A few words on them: how you met, what they said "
                                              "so far. One or two sentences at most."}}}),
    dict(name="forget_person",
         description="Delete everything stored about the visitor Frank is talking to "
                     "(face and memories), because they asked.",
         schema={"type": "object", "additionalProperties": False, "properties": {}}),
    dict(name="go_quiet",
         description="Fall silent because someone asked Frank to be quiet, to stop talking or "
                     "to give them a moment. From the end of this reply he hears nothing and "
                     "answers nothing until someone says his name (\"Frank, are you there?\") "
                     "or the time they asked for is up. Say at most a word or two in the same "
                     "reply, or nothing.",
         schema={"type": "object", "additionalProperties": False,
                 "properties": {
                     "minutes": {"type": "number",
                                 "description": "How long they asked for, if they said. Leave "
                                                "it out when they didn't."}}}),
]
# Tool inputs stream as they're generated, so they arrive unvalidated: check before acting.
ANTHROPIC_TOOLS = [{"name": t["name"], "description": t["description"],
                    "input_schema": t["schema"], "eager_input_streaming": True} for t in TOOLS]
OPENAI_TOOLS = [{"type": "function", "function": {"name": t["name"], "description": t["description"],
                                                  "parameters": t["schema"]}} for t in TOOLS]


def load_env(path=HERE / ".env"):
    """KEY=VALUE lines from frank/.env into the environment (real env vars win)."""
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            key, sep, value = line.strip().partition("=")
            if sep and not key.startswith("#"):
                os.environ.setdefault(key.strip(), value.strip().strip("\"'"))


def available(name):
    """Whether credentials for this model's provider are set up."""
    provider = MODELS[name]["provider"]
    if os.environ.get(KEY_ENV[provider]):
        return True
    # The Anthropic SDK also finds an auth token or an `ant auth login` profile.
    return provider == "anthropic" and bool(
        os.environ.get("ANTHROPIC_AUTH_TOKEN") or (Path.home() / ".config" / "anthropic").exists())


def valid_input(name, args):
    if name == "remember_person":
        return (isinstance(args, dict) and isinstance(args.get("first_name"), str)
                and args["first_name"].strip() != "" and isinstance(args.get("notes"), str))
    if name == "go_quiet":
        minutes = args.get("minutes") if isinstance(args, dict) else None
        return isinstance(args, dict) and (minutes is None or (isinstance(minutes, (int, float))
                                                                and not isinstance(minutes, bool)
                                                                and 0 <= minutes <= 24 * 60))
    return isinstance(args, dict)


def _echo(msg):
    """A Claude reply as it goes back into the history. Unchanged, except: a refusal's
    partial text is discarded, and after a mid-reply switch to the fallback model only the
    text from before the switch is kept (the API's rule for echoing fallback turns)."""
    if msg.stop_reason == "refusal":
        return [{"type": "text", "text": "[neutral]"}]
    blocks = list(msg.content)
    last = max((i for i, b in enumerate(blocks) if b.type == "fallback"), default=-1)
    kept = [b for i, b in enumerate(blocks) if i > last or b.type == "text"]
    return kept or [{"type": "text", "text": "[neutral]"}]


def _client(provider):
    if provider == "anthropic":
        import anthropic
        return anthropic.Anthropic()
    import openai
    return openai.OpenAI(api_key=os.environ["OPENAI_API_KEY"])


class Conversation:
    def __init__(self, name):
        self.name = name
        self.cfg = MODELS[name]
        self.provider = self.cfg["provider"]
        self.client = _client(self.provider)
        self.messages = []  # in the provider's own format, append-only
        self.pending = []   # tool calls from the last reply, as (id, name, input)

    def add_turn(self, said, notes=(), tool_results=None):
        """What the visitor said (or "(no speech)"), then context notes as system messages.
        tool_results answers the last reply's tool calls ({call id: text}); unanswered
        calls get "done"."""
        results = [(cid, (tool_results or {}).get(cid, "done")) for cid, _, _ in self.pending]
        self.pending = []
        if self.provider == "anthropic":
            content = [{"type": "tool_result", "tool_use_id": cid, "content": text}
                       for cid, text in results]
            content.append({"type": "text", "text": said})
            self.messages.append({"role": "user", "content": content})
        else:
            self.messages += [{"role": "tool", "tool_call_id": cid, "content": text}
                              for cid, text in results]
            self.messages.append({"role": "user", "content": said})
        self.messages += [{"role": "system", "content": note} for note in notes]

    def fork(self):
        """A copy to run a reply on that may be thrown away (a speculative or interruptible
        turn); the caller adopts it once the reply counts."""
        twin = Conversation.__new__(Conversation)
        twin.__dict__.update(self.__dict__)
        twin.messages, twin.pending = list(self.messages), list(self.pending)
        return twin

    def stream(self):
        if self.provider == "anthropic":
            yield from self._stream_anthropic()
        else:
            yield from self._stream_openai()

    def _stream_anthropic(self):
        cfg = self.cfg
        kw = dict(model=cfg["model"], max_tokens=MAX_TOKENS, tools=ANTHROPIC_TOOLS,
                  system=[{"type": "text", "text": SYSTEM_PROMPT,
                           "cache_control": {"type": "ephemeral"}}],
                  messages=self.messages, output_config={"effort": cfg["effort"]})
        if "thinking" in cfg:
            kw["thinking"] = cfg["thinking"]
        api = self.client.messages
        if cfg.get("fallbacks"):  # a declined request is retried server-side on another model
            api = self.client.beta.messages
            kw.update(betas=["server-side-fallback-2026-07-01"], fallbacks="default")
        written, msg = [], None
        try:
            with api.stream(**kw) as s:
                for ev in s:
                    if ev.type == "text":
                        written.append(ev.text)
                        yield ("text", ev.text)
                msg = s.get_final_message()
        finally:
            if msg is None:  # stopped early (interrupted) or failed: keep what he wrote
                self.messages.append({"role": "assistant", "content": "".join(written) or "[neutral]"})

        content = _echo(msg)
        self.messages.append({"role": "assistant", "content": content})
        for b in content:
            if getattr(b, "type", None) == "tool_use":
                self.pending.append((b.id, b.name, b.input))
                yield ("tool", b.name, b.input)
        u = msg.usage
        yield ("done", dict(stop_reason=msg.stop_reason, served_by=msg.model,
                            input_tokens=u.input_tokens, output_tokens=u.output_tokens,
                            cache_read=getattr(u, "cache_read_input_tokens", 0) or 0))

    def _stream_openai(self):
        cfg = self.cfg
        kw = dict(model=cfg["model"], tools=OPENAI_TOOLS, stream=True,
                  stream_options={"include_usage": True},
                  messages=[{"role": "system", "content": SYSTEM_PROMPT}] + self.messages)
        if cfg.get("reasoning_effort"):
            kw["reasoning_effort"] = cfg["reasoning_effort"]
        text, calls, finish, usage, served_by = [], {}, None, None, cfg["model"]
        complete = False
        try:
            for chunk in self.client.chat.completions.create(**kw):
                served_by = chunk.model or served_by
                if chunk.usage:
                    usage = chunk.usage
                if not chunk.choices:
                    continue
                choice = chunk.choices[0]
                if choice.delta.content:
                    text.append(choice.delta.content)
                    yield ("text", choice.delta.content)
                for tc in choice.delta.tool_calls or []:
                    c = calls.setdefault(tc.index, {"id": "", "name": "", "args": ""})
                    c["id"] = tc.id or c["id"]
                    if tc.function:
                        c["name"] += tc.function.name or ""
                        c["args"] += tc.function.arguments or ""
                finish = choice.finish_reason or finish
            complete = True
        finally:
            if not complete:  # stopped early (interrupted) or failed: keep what he wrote
                self.messages.append({"role": "assistant", "content": "".join(text) or "[neutral]"})

        msg = {"role": "assistant", "content": "".join(text)}
        if calls:
            msg["tool_calls"] = [{"id": c["id"], "type": "function",
                                  "function": {"name": c["name"], "arguments": c["args"]}}
                                 for c in calls.values()]
        self.messages.append(msg)
        for c in calls.values():
            try:
                args = json.loads(c["args"] or "{}")
            except json.JSONDecodeError:
                args = {"INVALID_JSON": c["args"]}
            self.pending.append((c["id"], c["name"], args))
            yield ("tool", c["name"], args)
        yield ("done", dict(stop_reason=finish, served_by=served_by,
                            input_tokens=getattr(usage, "prompt_tokens", None),
                            output_tokens=getattr(usage, "completion_tokens", None),
                            cache_read=getattr(getattr(usage, "prompt_tokens_details", None),
                                               "cached_tokens", 0) or 0))

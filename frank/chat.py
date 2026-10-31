"""
Talk to Frank in the terminal, and leave feedback as you go.

    uv run --no-project --with anthropic --with openai --with httpx --with sounddevice --with numpy --with scipy --with websockets --with livekit python frank/chat.py --talk
    uv run ... --with pyserial python frank/chat.py --mouth auto     (the jaw follows his voice: mouth.py)
    uv run ... frank/chat.py --model gpt-5.4-mini --as Anushhka --mute
    uv run ... --with opencv-python --with mediapipe python frank/chat.py --talk --see

With --talk (or /talk) he listens on the microphone (ears.py): speak, pause, and he
answers. He starts thinking as soon as a sentence of yours ends and drops that thought if
you carry on. Talk over him and he stops, and is told how much of his reply you heard.
With --see he watches through the camera (eyes.py, in a process of its own, with a
preview window): what he sees arrives as context notes, he reacts unprompted when someone
arrives, when he's picked up or when his vision goes dark, each line is credited to
whoever's mouth was moving, remember_person and forget_person really store and delete
faces, and a new conversation starts once everyone has gone. --video plays a clip instead.
You can always type too. Frank's face cues show in brackets, with the time to his first
sentence, to his first sound and, when you spoke, from you stopping to his first sound.
Once frank/voice.json exists he speaks aloud. Commands:
    /fb <text>      feedback on Frank's last reply (saved with the transcript for tuning)
    /note <text>    a context note, e.g.  /note Present: Lars (recognised).
    /as <name>      speak as someone Frank recognises; "/as" alone = a stranger again
    /gate           with --see: answer only lines from a mouth that moved in front of him
                    (on), or everything the microphone hears (off)
    /silence        let a silence pass ("(no speech)")
    /quiet [min]    as if he'd been told to be quiet: he ignores everything until a line
                    says his name or asks him to talk again (or, with a number, until that
                    many minutes are up); everyone leaving doesn't end it
    /wake           bring him back from quiet yourself
    /model <name>   switch brain (a new conversation): haiku-5.5, sonnet-5.5, opus-5.5, gpt-5.4-mini
    /new            a new conversation (the next visitor)
    /mute           voice off or on again
    /talk           microphone on or off
    /eyes [pause|alive]  with --mouth: hold the eyes open and still (pause), or let them look
                    around and blink again (alive); alone, it switches
    /quit
Edits to system_prompt.md apply from the next turn. Every session is saved to
output/frank/chats/<date_time>.jsonl.
"""

import argparse
import json
import queue
import re
import sys
import threading
import time
from datetime import date, datetime
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
import brain  # noqa: E402
import speech  # noqa: E402

try:
    import readline  # noqa: F401  (arrow keys and history, where available)
except ImportError:
    pass

AWAKENING = date(2026, 10, 26)  # provisional until the creators set it (README, "Still open")
TOOL_RESULTS = {"remember_person": "Remembered.", "forget_person": "Forgotten: face and memories deleted.",
                "go_quiet": "Quiet: you hear nothing more until someone says your name."}
LOGS = HERE.parent / "output" / "frank" / "chats"
# Where he is and what he's lived through lately, for his opening notes (--place, --recent).
# Set for tonight (2026-10-30); the lab was "The lab, SCAD Satellite Lab, Savannah".
PLACE = "NightHack at Founders Inc., San Francisco"
RECENT = ("Your recent experiences: Anushhka and Lars brought you from the lab in Savannah to "
          "San Francisco for NightHack, a night-long hackathon at Founders Inc. You were asleep "
          "for the whole journey, the flight included, so you know nothing of it firsthand: you "
          "remember the lab, and then waking here, on 30 October 2026.")
DIM, BOLD, OFF = "\033[2m", "\033[1m", "\033[0m"


def now_note(place):
    d = datetime.now()
    clock = f"{d.hour % 12 or 12}:{d.minute:02d} {'am' if d.hour < 12 else 'pm'}"
    awake = (d.date() - AWAKENING).days + 1
    return (f"Now: {d:%A} {d.day} {d:%B %Y}, {clock}. {place}. "
            f"Awake {awake} day{'s' if awake != 1 else ''}.")


def present_note(speaker):
    return f"Present: {speaker} (recognised)." if speaker else "Present: one stranger."


# What the brain is told after it calls a tool with the eyes on (eyes.Vision's answers).
REMEMBERED = dict(
    ok="Remembered: their face is now linked to the name {name}.",
    already="Already remembered: you know them as {name}.",
    ambiguous="Not remembered: you couldn't tell which face was theirs. Ask them to look straight "
              "at you, then try again.",
    unclear="Not remembered: you couldn't see their face clearly enough. Ask them to look straight "
            "at you for a moment, then try again.")
FORGOTTEN = dict(
    ok="Forgotten: {name}'s face and everything stored about them are deleted.",
    nothing="Nothing to forget: nothing is stored about them.",
    creator="Not done: {name} is one of your creators, who are remembered by design.",
    ambiguous="Not done: you couldn't tell which face was theirs. Ask them to look straight at you, "
              "then try again.",
    unclear="Not done: you couldn't see their face clearly enough to be sure who they are. Ask "
            "them to look straight at you, then try again.")
NO_EYES = "Not done: your vision isn't working right now."
FILLER_AFTER = 1.2   # s after the visitor's turn ends: if nothing's been said, a "Hmm." (voice.FILLERS) ...
FILLER_SHARE = 0.4   # ... on this share of such turns, never two turns running ("he says hmm too much")
# Speech the eyes say wasn't to him (eyes.Vision.heard): he isn't told what was said, only
# that the room is busy, at most once a minute.
BUSY_NOTE_S = 60
BUSY_VISITOR = ("Background: there's talking nearby that isn't to you, and your visitor isn't the "
                "one speaking: a video, perhaps, or people behind them.")
BUSY_ROOM = "Background: people nearby are talking, but nobody is talking to you."
ASKED_S = 10.0       # after Frank asks something, any answer counts for this long, mouths or not
PROMPT_QUIET_S = 1.0  # a held reaction waits until nobody has spoken for this long
HARD_STOP = {"stop", "wait", "frank", "hold"}  # these interrupt him whatever the mouths say
OVER_HIM_S = 0.3     # the microphone loud this long while a mouth in front of him moves: an
                     # interruption, without waiting for words (the echo canceller can swallow a
                     # visitor's words while his voice plays; none reached the code, 2026-10-29)
OVER_HIM = "(someone talking over him)"
# Before any of that: the microphone loud (after echo cancellation) for PAUSE_AFTER_S while
# he talks pauses his voice at once, and the words that follow decide. A visitor's words
# interrupt him for good; his own echo, or nothing within PAUSE_HOLD_S, or the microphone
# quiet again for PAUSE_QUIET_S, and he carries on where he left off (a hesitation). The
# first partial transcripts are too short for the echo filter, so waiting for the words
# alone left him talking over the visitor for a second or two (2026-10-30). Once paused
# his voice isn't in the microphone, so the echo filter needs only two new words.
PAUSE_LOUD = 0.006 * 32768  # RMS; lower than ears.LOUD, since the echo canceller thins a
                            # visitor's voice while his plays. Raised when a pause proves false
PAUSE_AFTER_S = 0.25        # loud this long: pause (100 ms microphone chunks, so 3 of them)
PAUSE_HOLD_S = 1.5          # paused this long with no verdict: carry on
PAUSE_QUIET_S = 0.3         # paused and the microphone quiet again this long: carry on
PAUSE_LEARN = 1.5           # a false pause raises the level to this times the run that caused it ...
PAUSE_LOUD_MAX = 0.03 * 32768  # ... up to this: a visitor over him read 1624 RMS (2026-10-30)
PAUSE_WORDS_S = 0.7         # a transcript this recent means someone is talking: keep holding ...
PAUSE_HOLD_MAX_S = 3.0      # ... up to this long in all
PAUSE_LEARN_S = 1.0         # a pause is judged false this long after the resume, if no words came
SILENCE_S = 25       # someone's there and nobody has spoken this long: he may say something ...
SILENCE_SHARE = 0.5  # ... this often (CHARACTER.md: not every silence needs speech)
# Told to be quiet (the go_quiet tool, or /quiet), he drops everything he hears until a line
# has his name in it ("Hey Frank, are you there?") or asks him to talk again, or the time he
# was given is up and someone speaks again. Nothing else ends it: not everyone leaving, not a
# new conversation (the eyes lost sight of Anushhka for a moment and he came back talking,
# 2026-10-30). The ears' transcript spells him Frank; "Frankie" and "Franky" count too.
WAKE = re.compile(r"\bfrank(?:ie|y)?\b"
                  r"|\byou (?:can|may) (?:talk|speak)\b|\b(?:talk|speak) (?:now|again)\b"
                  r"|\bwake up\b|\bcome back\b", re.IGNORECASE)
QUIET_WHY = "he was asked to be quiet"


def load_voice():
    try:
        import voice
        return voice.Voice.from_config()
    except (ImportError, OSError, SystemExit) as e:
        print(f"{DIM}(no voice: {e}){OFF}")
        return None


def start_face(chat, port=None, face=True, still_eyes=False, editor=8820):
    """The mouth board (mouth.py) on `port`, and the face engine (frank/engine) driving the eyes,
    lids, brows and the emotion part of the mouth: it takes the voice player's mouth hook,
    hears the chat's events and watches the eyes. The engine is then the eyes, so the mouth
    doesn't start gaze.py, and /eyes pause | alive go to the engine (engine.gaze).
    face=False: the mouth alone with gaze.py's eyes, as before. still_eyes: eyes held still."""
    writer = None
    if port:
        import mouth
        writer = mouth.Mouth(port, log=lambda **k: chat.write(event="mouth", **k),
                             eyes=not face and not still_eyes)
        print(f"{DIM}Mouth on {writer.port} ({writer.program}).{OFF}")
    chat.engine = chat.face_api = None
    if face:
        from engine import Engine
        chat.engine = Engine(writer=writer, log=lambda **k: chat.write(event="face", **k)).start()
        chat.listeners.append(chat.engine.on_ui)
        chat.engine.watch(lambda: chat.eyes.state if chat.eyes else None)
        if still_eyes:
            chat.engine.gaze.pause()
        print(f"{DIM}Face engine on ({'the head' if writer else 'no head: preview only'}); "
              f"eyes {chat.engine.gaze.state}.{OFF}")
        # The editor's routes on this engine (frank/engine/preview.py): web.py's page asks for
        # them under /engine/, and the editor page serves them on its own port.
        from engine import preview as engine_page
        chat.face_api = engine_page.Api(chat.engine, head=writer.port if writer else None, live=True)
        if editor:  # the engine's editor page, live on this session
            try:
                engine_page.serve(chat.engine, editor, api=chat.face_api)
                print(f"{DIM}Face editor, live: http://127.0.0.1:{editor}{OFF}")
            except OSError as e:
                print(f"{DIM}(no face editor on {editor}: {e}; is preview.py still running?){OFF}")
    if chat.voice:
        chat.voice.mouth = chat.engine or writer
    return chat.engine or writer


def stop_face(chat):
    face = getattr(chat, "engine", None) or (chat.voice.mouth if chat.voice else None)
    if face:
        face.close()


class Turn:
    """One reply from Frank, on its own thread and its own copy of the conversation.

    A speculative turn starts as soon as the visitor's sentence ends but shows and says
    nothing until release(); if they carry on talking it is cancelled and thrown away. A
    released turn can be interrupted: the voice stops, and the turn ends with what he had
    written so far. Either way the copy becomes the conversation only once it counts."""

    def __init__(self, chat, said, released, heard_at=None):
        self.chat, self.said, self.heard_at = chat, said, heard_at
        self.window, self.early = None, False  # when the line was said; released on a still mouth
        self.convo = chat.convo.fork()
        self.notes = list(chat.notes)
        self.go = threading.Event()
        self.showing = threading.Lock()  # _show runs from the reply thread and the filler timer
        self.cancelled = self.interrupted = False
        self.text, self.tools, self.waiting = "", [], []  # waiting: output held until release
        self.t0 = time.perf_counter()
        self.released_at = self.first_say = self.first_say_at = None
        if released:
            self.release(heard_at)
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()

    def release(self, heard_at=None):
        self.heard_at = heard_at or self.heard_at
        self.released_at = time.perf_counter()
        self.chat.notes = []
        self.go.set()
        threading.Thread(target=self._fill, daemon=True).start()

    def _fill(self):
        """Backchannel: if his first words aren't out FILLER_AFTER s after the visitor
        stopped, a short "Hmm." in his voice covers the thinking."""
        import random
        time.sleep(FILLER_AFTER)
        voice = self.chat.active_voice()
        chat = self.chat
        if (voice and self.first_say_at is None and not self.cancelled and not self.interrupted
                and self.thread.is_alive() and not chat.filled_last and random.random() < FILLER_SHARE):
            if not getattr(self, "shown", False):  # the reply hasn't started showing: open it
                self._show()
            words = voice.filler()
            if words:
                self.filler_words = words  # the echo filter must know he said it
                chat.filled_last = True
                print(f"{DIM}({words}){OFF} ", end="", flush=True)
                chat.ui("sound", tag=words)
                return
        chat.filled_last = False

    def cancel(self):
        self.cancelled = True

    def interrupt(self, reason="interrupted"):
        self.interrupted = True
        voice = self.chat.active_voice()
        return voice.stop(reason) if voice else ""

    @property
    def is_echo(self):
        """is_echo(heard) against what he has written so far (read at call time, since the
        ears get this before he has written anything); .why(heard) explains."""
        import ears
        spoken = lambda: f"{getattr(self, 'filler_words', '')} {self.text}"  # noqa: E731
        voice = self.chat.active_voice()
        min_new = lambda: 2 if voice and voice.paused is not None else 3  # noqa: E731  (chat.PAUSE_*)
        check = lambda heard: ears.echo_check(spoken(), min_new())(heard)  # noqa: E731
        check.why = lambda heard: ears.echo_check(spoken(), min_new()).why(heard)
        return check

    def _run(self):
        chat = self.chat
        chat.reload_prompt()
        results = {cid: chat.tool_results.get(cid) or TOOL_RESULTS.get(name, "done")
                   for cid, name, _ in self.convo.pending}
        self.convo.add_turn(self.said, self.notes, results)
        tags, stream, error = speech.TagStream(), self.convo.stream(), None
        try:
            for ev in stream:
                if self.cancelled or self.interrupted:
                    break
                if ev[0] == "text":
                    self.text += ev[1]
                    self.waiting += tags.feed(ev[1])
                elif ev[0] == "tool":
                    self.tools.append({"name": ev[1], "input": ev[2]})
                    self.waiting.append(("tool", f"{ev[1]} {json.dumps(ev[2], ensure_ascii=False)}"))
                else:
                    self.waiting += tags.flush()
                if self.go.is_set():
                    self._show()
        except Exception as e:
            error = f"{type(e).__name__}: {e}"
        finally:
            stream.close()  # an early stop keeps what he wrote (brain.Conversation.stream)
        while not self.go.wait(0.05):  # finished before the visitor had certainly finished
            if self.cancelled:
                return  # thrown away: this copy never becomes the conversation
        if self.cancelled:
            return
        self._show()
        self._finish(tags, error)

    def _show(self):
        """Print and speak whatever is waiting (only once released)."""
        with self.showing:
            self._show_locked()

    def _show_locked(self):
        voice = self.chat.active_voice()
        if self.first_say_at is None and not getattr(self, "shown", False):
            self.shown = True
            print(f"{BOLD}Frank:{OFF} ", end="", flush=True)
            self.chat.ui("frank_start")
            self.face, self.chuckle = None, False
            if voice:
                voice.start_reply()
        for kind, value in self.waiting:
            if self.interrupted:
                break
            if kind == "say":
                if self.first_say_at is None:
                    self.first_say_at = time.perf_counter()
                    self.first_say = self.first_say_at - self.t0
                print(value, end=" ", flush=True)
                self.chat.ui("say", text=value)
                if voice:
                    voice.say(value, self.face, self.chuckle)
                self.chuckle = False
            elif kind == "tool":
                print(f"{DIM}(calls {value}){OFF} ", end="", flush=True)
                self.chat.ui("tool_call", text=value)
            else:
                self.face = value if kind == "face" else self.face
                self.chuckle = self.chuckle or kind == "sound"
                print(f"{DIM}({value}){OFF} ", end="", flush=True)
                self.chat.ui(kind, tag=value)  # "face" or "sound"
        self.waiting = []

    def _finish(self, tags, error):
        chat, voice = self.chat, self.chat.active_voice()
        if error:
            print(f"\n{DIM}error: {error}{OFF}")
            chat.ui("error", text=error)
        if self.first_say_at is None and not self.interrupted:
            print(f"{DIM}(says nothing){OFF}", end=" ")
        if voice and self.first_say_at:
            voice.wait()
        parts = []
        if self.first_say:
            parts.append(f"{self.first_say:.2f}s to first sentence")
        heard_wait = None
        if voice and voice.first_sound and self.first_say_at:
            sound_at = voice.t0 + voice.first_sound
            parts.append(f"{sound_at - self.released_at:.2f}s from go to first sound")
            heard_wait = sound_at - self.heard_at if self.heard_at else None
        elif self.heard_at and self.first_say_at:
            heard_wait = self.first_say_at - self.heard_at
        if heard_wait:
            parts.append(f"{heard_wait:.2f}s from you stopping to his {'sound' if voice else 'reply'}")
        head_start = self.released_at - self.t0
        if head_start > 0.05:
            parts.append(f"started thinking {head_start:.2f}s early")
        if voice and voice.error:
            parts.append(voice.error)
            voice.error = None
        print(f"{' (interrupted)' if self.interrupted else ''} {DIM}[{'; '.join(parts) or 'silent'}]{OFF}\n")
        chat.ui("frank_end", timing="; ".join(parts), interrupted=self.interrupted,
                silent=self.first_say_at is None)
        chat.convo = self.convo  # this reply counts now
        chat.last_reply = self.text
        chat.quiet_since = time.time()
        spoken = " ".join(v for k, v in speech.parse(self.text) if k == "say").strip()
        chat.asked_at = time.time() if spoken.endswith("?") and not self.interrupted else 0.0
        chat.tool_results = {}   # the last ones went with this turn
        chat.run_tools(self.convo.pending)
        chat.write(event="turn", model=chat.model, said=self.said, notes=self.notes, reply=self.text,
                   first_say=self.first_say and round(self.first_say, 3), tools=self.tools,
                   unknown_tags=tags.unknown, spoken=self.heard_at is not None,
                   heard_wait=heard_wait and round(heard_wait, 3),
                   head_start=round(head_start, 3), interrupted=self.interrupted, error=error,
                   mouths=(chat.turn_mouths or None), early=self.early)
        chat.events.put(("done", self))


class Chat:
    def __init__(self, model, speaker, place, mute, recent=RECENT):
        self.place, self.speaker, self.recent = place, speaker, recent
        self.voice = None if mute else load_voice()
        if self.voice:
            self.voice.log = lambda **k: self.write(event="voice", **k)
        self.muted = mute
        self.ears, self.listening = None, False
        self.eyes, self.new_due = None, False
        self.speech_t0 = None    # when the visitor's current line began (wall clock)
        self.turn_who = None     # whom the eyes credit with the line being heard
        self.last_line = ("", None)  # the visitor's last line and when they said it
        self.tool_results = {}   # call id: what the brain is told about it
        self.gate, self.busy_note_at = True, 0.0  # with the eyes: answer only lines said to him
        self.turn_mouths = {}  # the mouth readings behind the current line, for the log
        self.prompt_due = False  # the eyes gave him a reason to speak while he was busy
        self.filled_last = False  # the last turn had a "Hmm."
        self.asked_at = 0.0      # when his last reply ended, if it was a question
        self.quiet_since, self.silence_said = time.time(), 0.0
        self.shushed = None      # told to be quiet: dict(since, until, dropped) until he's called back
        self.listeners = []      # web.py's: each gets every ui() event
        self.events = queue.Queue()  # (kind, value) from the keyboard, the ears, the eyes and turns
        self.prompt_mtime = (HERE / "system_prompt.md").stat().st_mtime
        LOGS.mkdir(parents=True, exist_ok=True)
        self.log = LOGS / f"{datetime.now():%Y-%m-%d_%H%M%S}.jsonl"
        self.start(model)

    def start(self, model):
        self.model = model
        self.convo = brain.Conversation(model)
        self.notes = [now_note(self.place)] + ([self.recent] if self.recent else [])
        present = self.eyes.present_note() if self.eyes else present_note(self.speaker)
        self.notes += [present] if present else []
        self.last_reply = None
        print(f"{DIM}-- new conversation with {model} --{OFF}")
        if self.shushed:
            self.info("still quiet: he was asked to be; a line with his name brings him back")
        self.ui("new", model=model)
        self.write(event="new", model=model)

    def see(self, preview=True, source=None):  # preview: a window, or "web" for web.py
        import eyes
        self.eyes = eyes.Eyes(lambda ev: self.events.put(("seen", ev)), preview=preview,
                              source=source).start()
        self.notes = [n for n in self.notes if not n.startswith("Present:")]  # the eyes will say
        self.info("watching: the eyes start in a few seconds")

    def run_tools(self, calls):
        """go_quiet, and (with the eyes on) remember_person and forget_person, done on
        whoever said the last line. What happened goes to the brain with the next turn."""
        said, window = self.last_line
        window = window or (time.time() - 20, time.time())  # a typed line
        for cid, name, args in calls:
            if not brain.valid_input(name, args):
                text = "Not done: the request was malformed."
            elif name == "go_quiet":
                text = self.shush(args.get("minutes"), who="asked by the visitor")
            elif not self.eyes:
                continue  # the fixed answers in TOOL_RESULTS, as in the bake-off
            elif name == "remember_person":
                consent = f'{datetime.now():%Y-%m-%d %H:%M}, gave their name when asked, saying: "{said}"'
                r = self.eyes.enroll(args["first_name"].strip(), *window, consent=consent,
                                     note=args.get("notes", ""))
                why = "already" if r.get("already") else "ok" if r.get("ok") else r.get("why")
                text = REMEMBERED.get(why, NO_EYES).format(name=r.get("name", ""))
            elif name == "forget_person":
                r = self.eyes.forget(*window)
                text = FORGOTTEN.get("ok" if r.get("ok") else r.get("why"), NO_EYES).format(name=r.get("name", ""))
            else:
                continue
            self.tool_results[cid] = text
            print(f"{DIM}({name}: {text}){OFF}")
            self.ui("tool", name=name, text=text)
            self.write(event="tool", name=name, input=args, result=text)

    def shush(self, minutes=None, who="the console"):
        """Be quiet from now: nothing he hears gets an answer until wake(). Returns what
        the brain is told."""
        minutes = minutes or None
        until = time.time() + minutes * 60 if minutes else None
        self.shushed = dict(since=time.time(), until=until, dropped=0)
        self.prompt_due = False  # nothing he saw is worth breaking the quiet for
        span = f" or {minutes:g} minute{'s' if minutes != 1 else ''} have passed" if minutes else ""
        self.info(f"quiet ({who}): he ignores everything until a line says his name{span}")
        self.ui("quiet", on=True, until=until)
        self.write(event="quiet", on=True, minutes=minutes, who=who)
        return f"Quiet: you hear nothing more until someone says your name{span}."

    def wake(self, why):
        """Back from quiet. The brain is told how long it was and why it ended."""
        q, self.shushed = self.shushed, None
        if not q:
            return
        mins = max(1, round((time.time() - q["since"]) / 60))
        missed = (f" {q['dropped']} thing{'s' if q['dropped'] != 1 else ''} were said meanwhile "
                  "that you didn't take in." if q["dropped"] else "")
        self.notes.append(f"Quiet over: you were asked to be quiet about {mins} minute"
                          f"{'s' if mins != 1 else ''} ago and kept it; {why}.{missed} "
                          "Carry on without making a thing of it.")
        self.asked_at = time.time()  # the line that called him counts, whatever the mouths say
        self.info(f"awake: {why}")
        self.ui("quiet", on=False)
        self.write(event="quiet", on=False, why=why, minutes=mins, dropped=q["dropped"])

    def hushed(self, text, final):
        """While he's been told to be quiet: True if this line is to be let pass. His name,
        or being asked to talk again, brings him back at once; the time being up brings him
        back on the next line. A final line that passes is shown greyed on the page and logged."""
        q = self.shushed
        if not q:
            return False
        if WAKE.search(text):
            self.wake("they've just called you back")
            return False
        if q["until"] and time.time() > q["until"]:
            self.wake("the time they asked for is up and someone is speaking again")
            return False
        if final:
            q["dropped"] += 1
            print(f"\r\033[K{DIM}(quiet) {text}{OFF}")
            self.ui("ignored", text=text, why=QUIET_WHY, quiet=True)
            self.write(event="ignored", said=text, why="quiet")
        return True

    def saw(self, ev, busy, spec):
        """What the eyes report; True if Frank should react now, though nobody spoke."""
        if ev["kind"] == "error":
            self.info(f"eyes: {ev.get('error')}")
            return False
        if ev.get("message"):  # enrolling, from the web page: not for the brain
            self.info(ev["message"])
            self.ui("enrol", text=ev["message"], done=ev.get("done", False))
        for note in ev["notes"]:
            print(f"\r\033[K{DIM}(sees) {note}{OFF}")
        if ev["notes"] or ev["kind"] == "session_end":  # the face engine needs the end too
            self.ui("seen", what=ev["kind"], notes=ev["notes"], prompt=ev["prompt"])
        self.write(event="seen", kind=ev["kind"], notes=ev["notes"], prompt=ev["prompt"])
        if ev["kind"] == "session_end":  # everyone has gone: the next visitor gets a new conversation
            if busy:
                self.new_due = True
            else:
                self.start(self.model)
            self.prompt_due = False
            return False
        self.notes += ev["notes"]
        if ev["prompt"]:
            if self.shushed:
                return False  # he was told to be quiet: what he saw waits in the notes
            if not busy and not spec and self.speech_t0 is None:
                return True
            self.prompt_due = True  # held until he's free (it was dropped before, 2026-10-28)
        return False

    def free_prompt(self):
        """A held reason to speak, once he's free and the room has been quiet a moment (it
        fired the instant he was cut off, into the visitor's next words, 2026-10-28)."""
        quiet = time.time() - max(self.quiet_since, self.last_voice_at()) >= PROMPT_QUIET_S
        if self.prompt_due and self.speech_t0 is None and quiet:
            self.prompt_due = False
            return True
        return False

    def last_voice_at(self):
        """When the microphone last heard a voice, as wall-clock time (the ears count in
        perf_counter seconds)."""
        if not self.ears or not getattr(self.ears, "last_voice", 0):
            return 0.0
        return time.time() - (time.perf_counter() - self.ears.last_voice)

    def silence_prompt(self):
        """Someone's with him and nobody has spoken for SILENCE_S: now and then he fills it."""
        import random
        present = self.eyes and self.eyes.state and self.eyes.state.get("session")
        if not present or time.time() - self.quiet_since < SILENCE_S or self.speech_t0 is not None:
            return False
        if time.time() - self.silence_said < SILENCE_S * 2:
            return False
        self.silence_said = time.time()
        if random.random() > SILENCE_SHARE:
            return False
        self.notes.append(f"Silence: {int(time.time() - self.quiet_since)} seconds since anyone spoke.")
        return True

    def active_voice(self):
        return None if self.muted else self.voice

    def ui(self, kind, **data):
        """Tell web.py's page what's happening (the terminal has its prints)."""
        ev = dict(kind=kind, t=time.time(), **data)
        for listener in self.listeners:
            listener(ev)

    def info(self, text):
        print(f"\r\033[K{DIM}({text}){OFF}")
        self.ui("info", text=text)

    def status(self):
        """The switches, for web.py."""
        if self.voice and not hasattr(self, "speakers"):  # the sound library lists them once, at start
            import voice
            self.speakers = voice.speakers()
        speakers, default = getattr(self, "speakers", ([], None))
        return dict(model=self.model, models=list(brain.MODELS), listening=self.listening,
                    voice=bool(self.voice) and not self.muted, voice_loaded=bool(self.voice),
                    speakers=speakers, speaker=self.voice.speaker if self.voice else None,
                    default_speaker=default, seeing=bool(self.eyes),
                    eyes_error=self.eyes.error if self.eyes else None, gate=self.gate,
                    quiet=bool(self.shushed), place=self.place, gaze=self.gaze_state())

    def gaze_state(self):
        """The eye animation: 'alive', 'paused', 'still' (no saved poses) or None (no mouth)."""
        mouth = self.voice.mouth if self.voice else None
        if not mouth:
            return None
        return mouth.gaze.state if mouth.gaze else "still"

    def write(self, **rec):
        with self.log.open("a", encoding="utf-8") as f:
            f.write(json.dumps(dict(t=datetime.now().isoformat(timespec="milliseconds"), **rec),
                               ensure_ascii=False, default=str) + "\n")

    def reload_prompt(self):
        path = HERE / "system_prompt.md"
        if path.stat().st_mtime != self.prompt_mtime:
            self.prompt_mtime = path.stat().st_mtime
            brain.SYSTEM_PROMPT = path.read_text(encoding="utf-8")
            self.info("system prompt reloaded")

    def who(self):
        return self.speaker or "You"

    def look(self, window):
        """Ask the eyes who said a line and whether it was to Frank (eyes.Vision.heard),
        once per line, so a speculative turn and the final one agree. The words began a
        little before their first text, hence the extra half second."""
        if self.turn_who is None:
            self.turn_who = who = self.eyes.heard(window[0] - 0.5, window[1])
            self.turn_mouths = who.get("mouths") or {}
            if who.get("to_him", True):
                if who["overlapping"] >= 2:
                    self.notes.append(f"Overlapping speech: {who['overlapping']} people talking at once.")
                elif who["label"] and not who["name"] and who.get("engaged", 0) >= 2:
                    self.notes.append(f"Speaking: {who['label']}.")
        return self.turn_who

    def to_him(self, text, window, final):
        """Whether a heard line was said to Frank: someone in front of him moved their mouth
        (or can't be seen to). A final line that wasn't is shown greyed on the page and
        logged, and now and then he's told the room is busy."""
        if not (self.eyes and self.gate and window):
            return True
        if time.time() - self.asked_at < ASKED_S:
            self.look(window)  # still find out who it was
            return True  # he asked; this is the answer (Sonal's "I'm Sonal" was dropped, 2026-10-28)
        who = self.look(window)
        if who.get("to_him", True):
            return True
        self.turn_who = None  # the next line is looked at afresh
        if final:
            why = who.get("why", "")
            print(f"\r\033[K{DIM}(not to him: {why}) {text}{OFF}")
            self.ui("ignored", text=text, why=why, mouths=who.get("mouths"))
            self.write(event="ignored", said=text, why=why, mouths=who.get("mouths"))
            if time.time() - self.busy_note_at > BUSY_NOTE_S:
                self.busy_note_at = time.time()
                self.notes.append(BUSY_VISITOR if who.get("engaged") else BUSY_ROOM)
        return False

    def as_said(self, text, window=None):
        """The visitor's line as the brain gets it, with their name first when it's known:
        with the eyes on, whoever's mouth was moving."""
        name = self.speaker
        if self.eyes and window:
            name = self.look(window)["name"]
        return f"{name}: {text}" if name else text

    def listen(self):
        import ears
        put = self.events.put

        def window():  # when this line was said, for the eyes to see who said it
            return (self.speech_t0 or time.time() - 3, time.time())

        def partial(text):
            if self.speech_t0 is None:
                self.speech_t0 = time.time() - 0.5  # the words began a little before their text
            print(f"\r\033[K{DIM}(hearing) {text}{OFF}", end="", flush=True)
            self.ui("hearing", text=text)

        def final(text):
            said_when, self.speech_t0 = window(), None
            print(f"\r\033[K{BOLD}{self.who()}:{OFF} {text}")
            put(("heard", (text, said_when)))

        self.ears = ears.Ears(partial, final, on_early=lambda t: put(("early", (t, window()))),
                              on_resumed=lambda: put(("resumed", None)),
                              on_barge=lambda t: put(("barge", t)),
                              on_error=lambda m: self.info(m))
        self.ears.on_while_speaking = self.while_speaking
        self.ears.on_trace = lambda **k: self.write(event="ears", mode=self.ears.mode, **k)
        self.ears.start()
        self.listening = True
        threading.Thread(target=self._over_him, daemon=True).start()
        self.write(event="audio", echo_cancellation=bool(getattr(self.ears, "aec", None)),
                   voice_aec=bool(self.voice and self.voice.aec), speaker=self.voice.speaker if self.voice else None)
        if not getattr(self.ears, "aec", None):
            self.info("echo cancellation is OFF: his own voice will reach the microphone")
        self.info("listening: speak, then pause; talk over Frank to interrupt him")

    def group_note(self):
        """A note when the number of people with him changes to two or more."""
        state = self.eyes.state if self.eyes else None
        n = sum(1 for p in (state or {}).get("people", []) if p.get("engaged") and not p.get("figure"))
        if n != getattr(self, "group_n", 0):
            self.group_n = n
            if n >= 2:
                self.notes.append(f"Group: {n} people with you now. One short sentence at a time, to one of them.")

    def talking_now(self):
        """Whether the eyes see a mouth in front of him moving right now."""
        state = self.eyes.state if self.eyes else None
        return bool(state) and any(p.get("talking") and not p.get("figure") for p in state.get("people", []))

    def while_speaking(self, text, echo):
        """What the speech service hears while he talks (the ears' echo verdict with it). Words
        that aren't his mean someone is talking, whatever the verdict: the pause holds for them."""
        why = self.ears.is_echo.why(text) if self.ears and self.ears.is_echo else {}
        if why.get("new"):
            self.words_at = time.monotonic()
        self.write(event="while_speaking", heard=text, echo=echo, new=why.get("new"))

    def _over_him(self):
        """While he talks: a loud microphone for PAUSE_AFTER_S pauses his voice at once, and
        the words decide (PAUSE_*); loud for OVER_HIM_S plus a moving mouth in view is an
        interruption without words, posted as a barge the run loop handles like any other."""
        last = resumed_at = 0.0
        self.pause_level, self.pause_run = PAUSE_LOUD, 0.0  # the level, and the peak of the run that paused him
        self.words_at, judge = 0.0, None  # when words that weren't his last arrived; (paused_at, resumed_at, run) to judge
        while True:
            time.sleep(0.05)
            ears, voice = self.ears, self.active_voice()
            if not ears:
                continue
            now = time.monotonic()
            if judge and now - judge[1] >= PAUSE_LEARN_S:
                # No words around the pause: a false alarm (his own echo, a noise), so next time
                # the microphone must beat that run. Words, even too few to stop him, were a
                # visitor, and the level stays (fillers taught it 2437 RMS, 2026-10-30).
                paused_at, _, run = judge
                judge = None
                if self.words_at < paused_at:
                    self.pause_level = min(PAUSE_LOUD_MAX, max(self.pause_level, PAUSE_LEARN * run))
                    self.write(event="pause_level", level=round(self.pause_level), run=round(run))
            speaking = ears.mode == "speaking"
            if voice and voice.paused is not None:
                held = now - voice.paused
                words = now - self.words_at < PAUSE_WORDS_S  # someone is talking: the verdict is coming
                # While the ears are no longer in speaking mode a barge is on its way (the run
                # loop stops him, or resumes him if the eyes block it): hold, but never for ever.
                if speaking and not words and held >= PAUSE_QUIET_S and ears.quiet_for(self.pause_level) >= PAUSE_QUIET_S:
                    why = "the microphone went quiet"
                elif held >= PAUSE_HOLD_S and (not words or held >= PAUSE_HOLD_MAX_S):
                    why = "no more than fillers" if self.words_at >= now - held else "nothing heard"
                else:
                    continue
                voice.resume(why)
                resumed_at = now
                judge = (now - held, now, self.pause_run)  # looked at PAUSE_LEARN_S from now
                self.write(event="resume", why=why, held=round(held, 2), level=round(self.pause_level))
                self.ui("resumed")
                continue
            if (speaking and voice and time.monotonic() - resumed_at > PAUSE_QUIET_S
                    and ears.loud_for(self.pause_level) >= PAUSE_AFTER_S):
                self.pause_run = ears.peak(PAUSE_AFTER_S + 0.1)
                if voice.pause("loud microphone"):
                    self.write(event="pause", level=round(self.pause_level), peak=round(self.pause_run),
                               floor=round(ears.floor), mouths=self.talking_now() if self.eyes else None)
                    self.ui("paused")
            if (speaking and self.eyes and self.gate and ears.loud_for() >= OVER_HIM_S
                    and self.talking_now() and time.time() - last > 2.0):
                last = time.time()
                self.events.put(("barge", OVER_HIM))

    def command(self, line, busy):
        cmd, _, arg = line[1:].partition(" ")
        arg = arg.strip()
        if cmd in ("model", "new", "silence", "as") and busy:
            self.info("wait until Frank has finished")
        elif cmd == "fb":
            if not arg:
                self.info("usage: /fb what you thought of that reply")
                return
            self.write(event="feedback", model=self.model, feedback=arg, on=self.last_reply)
            self.info("feedback saved")
        elif cmd == "note":
            self.notes.append(arg)
            self.info(f"note goes with the next line: {arg}")
        elif cmd == "as":
            self.speaker = arg or None
            self.notes.append(present_note(self.speaker))
            self.info(f"you are now {self.speaker or 'a stranger'}")
        elif cmd == "silence":
            self.notes.append("Silence: 15 seconds since anyone spoke.")
            return "(no speech)"
        elif cmd == "quiet":
            try:
                minutes = float(arg) if arg else None
            except ValueError:
                self.info("usage: /quiet, or /quiet <minutes>")
                return
            self.shush(minutes)
        elif cmd == "wake":
            if self.shushed:
                self.wake("the console called you back")
            else:
                self.info("he isn't quiet")
        elif cmd == "model":
            if arg not in brain.MODELS:
                self.info(f"choose from {', '.join(brain.MODELS)}")
                return
            self.start(arg)
        elif cmd == "new":
            self.start(self.model)
        elif cmd == "mute":
            if not self.voice and self.muted:
                self.voice = load_voice()
            self.muted = not self.muted
            self.info(f"voice {'off' if self.muted or not self.voice else 'on'}")
        elif cmd == "gate":
            self.gate = not self.gate
            self.info("answering only lines from a mouth that moved in front of him" if self.gate
                      else "answering everything the microphone hears")
        elif cmd == "eyes":
            gaze = self.voice and self.voice.mouth and self.voice.mouth.gaze
            if not gaze:
                self.info("the eyes aren't running: start with --mouth, with the eye poses saved")
                return
            if arg == "pause":
                state = gaze.pause()
            elif arg == "alive":
                state = gaze.alive()
            elif not arg:
                state = gaze.alive() if gaze.paused else gaze.pause()
            else:
                self.info("usage: /eyes pause, /eyes alive, or /eyes to switch")
                return
            self.info("eyes paused: open, centred and still" if state == "paused"
                      else "eyes alive: looking around and blinking")
        elif cmd == "talk":
            if not self.ears:
                self.listen()
                return
            self.listening = not self.listening
            if self.listening:
                self.ears.listen()
            else:
                self.ears.off()
            self.info(f"microphone {'on' if self.listening else 'off'}")
        elif cmd in ("quit", "exit", "q"):
            raise EOFError
        else:
            print(__doc__.split("Commands:")[1].split("Edits to")[0])

    def run(self):
        spec = current = None  # a speculative turn (not yet released); the turn under way

        def settle():  # the previous turn must have finished before the next one copies the conversation
            if current and current.thread.is_alive():
                current.thread.join(timeout=5)

        def begin(said, heard_at=None, from_spec=None, window=None, early=False):
            nonlocal current
            self.last_line, self.turn_who = (said, window), None
            self.quiet_since = time.time()
            self.group_note()
            self.ui("visitor", said=said)
            if from_spec:
                current = from_spec
                current.early = early
                current.release(heard_at)
            else:
                settle()
                current = Turn(self, said, released=True, heard_at=heard_at)
            current.window = window
            if self.ears and self.listening:
                self.ears.speaking(current.is_echo)

        def watch_mouth(turn):
            """A sentence ended: once every mouth in front of him has been still for
            MOUTH_STILL_S, the turn is over as far as the eyes can tell. Posts ("still", turn)."""
            deadline = time.time() + 1.5  # the ears will end the turn themselves by then
            while time.time() < deadline and not turn.cancelled and not turn.go.is_set():
                time.sleep(0.1)
                if self.eyes.mouth_still(time.time()):
                    self.events.put(("still", turn))
                    return

        while True:
            if not self.listening and not current:
                print(f"{BOLD}{self.who()}:{OFF} ", end="", flush=True)
            try:
                while True:
                    try:
                        kind, value = self.events.get(timeout=0.5)
                        break
                    except queue.Empty:
                        if self.eyes:
                            kind, value = "tick", None  # a held reaction, or a long silence
                            break
                        continue
            except KeyboardInterrupt:
                return
            if kind == "eof":
                return
            busy = bool(current and current.thread.is_alive())
            if kind == "early":
                text, window = value
                if busy and not current.interrupted:
                    continue
                if self.shushed:
                    if self.hushed(text, final=False):
                        continue  # his name wakes him now, so the early turn gets the note
                elif not self.to_him(text, window, final=False):
                    continue
                if spec:
                    spec.cancel()
                settle()
                spec = Turn(self, self.as_said(text, window), released=False)
                spec.window = window
                if self.eyes:
                    threading.Thread(target=watch_mouth, args=(spec,), daemon=True).start()
            elif kind == "resumed":
                self.turn_who = None  # they carried on: look again at the end
                if spec:
                    spec.cancel()
                    spec = None
            elif kind == "still":  # their mouth stopped: don't wait for the ears to be sure
                if value is spec and not spec.cancelled and not busy:
                    begin(spec.said, self.ears.last_voice, from_spec=spec, window=spec.window, early=True)
                    spec = None
            elif kind == "heard":
                text, window = value
                if self.shushed:
                    passed = self.hushed(text, final=True)  # a wake sets asked_at: the line counts
                else:
                    passed = not self.to_him(text, window, final=True)  # a video, or people behind them
                if passed:
                    if spec:
                        spec.cancel()
                        spec = None
                    continue
                said = self.as_said(text, window)
                if current and current.early and current.thread.is_alive() and not current.interrupted:
                    if current.said == said:
                        continue  # already answering it, from the still mouth
                    # They said more after the mouth seemed still: answer the whole line instead.
                    current.interrupt("more words after an early start")
                    self.notes.append("Interrupted: you started answering before they had finished; "
                                      "answer their whole line now.")
                if spec and spec.said == said:
                    begin(said, self.ears.last_voice, from_spec=spec, window=window)
                else:
                    if spec:
                        spec.cancel()
                    begin(said, self.ears.last_voice, window=window)
                spec = None
            elif kind == "seen":
                if self.saw(value, busy, spec):
                    begin("(no speech)")
            elif kind == "barge":
                if busy and not current.interrupted:
                    why = current.is_echo.why(value) if hasattr(current.is_echo, "why") else {}
                    self.turn_who = None
                    now = time.time()
                    who = self.eyes.heard(now - 2.5, now) if self.eyes and self.gate else {}
                    # His own voice through the speakers is the usual false interruption. A
                    # stop word always counts; otherwise a solid reading that no mouth in
                    # front of him is moving means it wasn't a visitor.
                    hard = set(why.get("stop") or []) & HARD_STOP
                    blocked = (not hard and who.get("to_him") is False and value != OVER_HIM)
                    self.write(event="barge", heard=value, new=why.get("new"), stop=why.get("stop"),
                               mouths=who.get("mouths"), why=who.get("why"), blocked=blocked)
                    if blocked:
                        print(f"\r\033[K{DIM}(not an interruption: {who.get('why')}) {value}{OFF}")
                        self.ui("ignored", text=value, why=f"while he spoke; {who.get('why')}", mouths=who.get("mouths"))
                        if self.ears:
                            self.ears.speaking(current.is_echo)  # carry on
                        voice = self.active_voice()
                        if voice and voice.paused is not None:
                            voice.resume("not an interruption")
                            self.ui("resumed")
                        continue
                    self.turn_who = None  # the interrupting line is looked at when it ends
                    heard = current.interrupt(f"visitor: {value[:40]}")
                    self.notes.append(f'Interrupted: the visitor heard only "{heard}—".' if heard
                                      else "Interrupted: the visitor started talking before Frank said anything.")
                    self.ui("interrupted", heard=heard)
            elif kind == "done":
                if value is current:
                    current = None
                if self.new_due:
                    self.new_due = False
                    self.start(self.model)
                if self.ears and self.listening and not value.interrupted:
                    self.ears.listen(after=0.4)
            elif kind == "tick":
                if self.shushed:
                    continue  # told to be quiet: no filling silences, no reacting to the eyes
                if not busy and not spec and (self.free_prompt() or self.silence_prompt()):
                    begin("(no speech)")
            elif kind == "typed":
                if not value:
                    continue
                if value.startswith("/"):
                    said = self.command(value, busy)
                    if said:
                        begin(said)
                elif busy:
                    self.info("Frank is talking: speak to interrupt him, or type when he's done")
                elif self.hushed(value, final=True):
                    continue
                else:
                    begin(self.as_said(value))


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="Talk to Frank")
    ap.add_argument("--model", default="sonnet-5.5", choices=list(brain.MODELS))
    ap.add_argument("--as", dest="speaker", help="speak as a recognised person, e.g. Anushhka")
    ap.add_argument("--place", default=PLACE, help="where he is, for his notes")
    ap.add_argument("--recent", default=RECENT, help="what he's lived through lately, for his notes ('' for nothing)")
    ap.add_argument("--mute", action="store_true", help="text only, no voice")
    ap.add_argument("--talk", action="store_true", help="listen on the microphone")
    ap.add_argument("--see", action="store_true", help="watch through the camera (eyes.py)")
    ap.add_argument("--video", help="with --see: a video file instead of the camera")
    ap.add_argument("--no-preview", action="store_true", help="with --see: no camera window")
    ap.add_argument("--mouth", help="the mouth Pico's serial port, or auto: the jaw follows his voice (mouth.py)")
    ap.add_argument("--still-eyes", action="store_true", help="with --mouth: the eyes do not look around and blink (gaze.py)")
    ap.add_argument("--no-face", action="store_true", help="no face engine: the mouth alone (frank/engine)")
    ap.add_argument("--editor-port", type=int, default=8820, help="the face editor page, live on this session (0: none)")
    args = ap.parse_args()
    brain.load_env()
    if not brain.available(args.model):
        sys.exit(f"No key for {args.model}: add it to frank/.env")

    chat = Chat(args.model, args.speaker, args.place, args.mute, recent=args.recent)
    start_face(chat, args.mouth, face=not args.no_face, still_eyes=args.still_eyes,
               editor=args.editor_port)
    print(f"{DIM}Talk or type to Frank. /fb <text> gives feedback on his last reply; /help for more.{OFF}\n")
    if args.see or args.video:
        chat.see(preview=not args.no_preview, source=args.video)
    if args.talk:
        chat.listen()

    def read_lines():  # typing works alongside the microphone
        for line in sys.stdin:
            chat.events.put(("typed", line.strip()))
        chat.events.put(("eof", None))
    threading.Thread(target=read_lines, daemon=True).start()

    try:
        chat.run()
    except EOFError:
        pass
    if chat.eyes:
        chat.eyes.stop()
    stop_face(chat)
    print(f"\n{DIM}Saved to {chat.log}{OFF}")


if __name__ == "__main__":
    main()

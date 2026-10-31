# Frank: the conversation contract

What the laptop software needs in order to run Frank. The character itself is defined in
[docs/CHARACTER.md](../docs/CHARACTER.md), the creators' bible. Change him there first, then here.

| File | What it is |
|---|---|
| `system_prompt.md` | The static system prompt, sent exactly as written. Nothing in it changes per turn, so it caches. |
| `README.md` | This file: tags, tools, context notes and the turn loop. |
| `brain.py` | One streamed conversation with any candidate model (Claude or OpenAI). Shared by the bake-off and the live loop. |
| `speech.py` | Splits the streamed reply into face commands, sounds and whole sentences for the voice. |
| `scenarios.py` | The bake-off's test conversations. |
| `bakeoff.py` | Runs the scenarios through each model, times them and writes a blind rating page. |
| `chat.py` | Talk to Frank in the terminal, out loud (`--talk`) or typed, and leave feedback as you go (`/fb`). Each reply is a `Turn` on its own copy of the conversation:<br>• it starts as soon as a sentence of yours ends, and is thrown away if you carry on talking;<br>• it can be interrupted, and the next turn gets the note `Interrupted: the visitor heard only "…—"`.<br>Sessions are saved to `output/frank/chats/`. |
| `voice.py` | His ElevenLabs voice: design, remix, compare models, and the streaming player the chat uses. |
| `ears.py` | Streaming speech-to-text from the microphone (ElevenLabs Scribe realtime, `scribe_v2_realtime`), with live partial text. A turn ends after 0.4 s of silence plus 0.35 s of grace following the last sentence (sooner after a question). While Frank talks it keeps listening for interruptions. His own voice through the speakers comes back as his own words, so text that is mostly his words is ignored as echo; other words, or "wait" / "stop", interrupt him. |
| `aec.py` | Echo cancellation (WebRTC's audio processing, from the `livekit` package). Frank's playback is the reference, and his voice is subtracted from the microphone before transcription. Offline test: echo 43–46 dB quieter, a visitor's voice kept. |
| `audio.py` | Runs the sound card at its own 48 kHz and converts to the voice's 24 kHz and the ears' 16 kHz. At those rates the system added 0.4–1.2 s of buffering. |
| `voice.json` | The chosen voice: "Mossbeard" from the ElevenLabs Voice Library (chosen 2026-10-26), on `eleven_v3` at stability 0 ("Creative") since 2026-10-28 because the other models were flat. v3 performs bracketed acting tags, so his face tags become delivery tags too (`voice.V3_TAGS`: [amused] → [amused], [concentrating] → [thoughtful], [chuckle] → [chuckles]) at each face change and at the start of each piece; punctuation, ellipses and capitals are performed. First audio about 0.6–0.7 s (turbo v2.5 was 0.3, multilingual v2 0.66). At Creative every take differs, and speed isn't sent; neither is `previous_text`, which v3 rejects (that silently dropped every piece after the first, 2026-10-28). Every piece and every stop is logged (`voice` events in the chat log). A watchdog catches the sound card stream going dead (a 20 ms write that takes over a second; 2026-10-30: plugging the EarPods in while he ran left every piece fetched and never played, and the picker and the test sound would have hung on the same lock): the stuck thread and stream are abandoned, a new stream opens on the chosen speaker (or the Mac's current default output) and the reply carries on from the next piece (`stalled` in the log). Earlier models are kept in the file. |
| `gargle.py` | A liquid-in-the-throat audio effect. Built and tried, but switched off (`"gargle": 0`). |
| `mouth.py` | His mouth follows his voice. The voice player hands it every 20 ms slice it plays and each piece's expression tag. Loudness opens the jaw (floor −42 dBFS shut, −16 dBFS at 85 % of OPEN; opens in 35 ms, closes in 90 ms) and, more lazily, parts the lips (60 % of the way to Cogley's lips_up / lips_down). The sound's brightness (spectral centroid, 400 to 2500 Hz) sets the width: bright "ee" and "s" pull the corners towards WIDE, dark "oo" leaves them NARROW. The tag puts a smile (amused, excited, curious) or a frown (irritated, skeptical, concentrating) under the corners, The tongue is off (`TONGUE`) until a tongue servo is fitted. Once the three vowel shapes are saved in the mouth slider window (`firmware/mouth_controls.py`, rows Vowel AH, EE, OO), the mouth blends between those instead: brightness picks the shape (OO dark, AH, EE bright) and loudness moves the whole mouth from rest to it. Every angle stays inside the board program's servo limits. The Pico may run `pico_servo_ctl.py` (angles per servo from `firmware/mouth_poses.json`) or TalkingHead's `cogley_mouth_main.py` (its `jaw <0..1>` for the jaw, `set` for the rest, glide speed 720 deg/s). `chat.py --mouth auto` or `web.py --mouth auto` (add `--with pyserial`); on its own, `--test` moves the mouth on a pretend envelope and `--say "text"` speaks a line with it. The thresholds are constants at the top of the file. |
| `gaze.py` | His eyes are alive the whole time he is on: the same looking-around-and-blinking as the slider window's EYES ALIVE (`firmware/eye_anim.py`), run from inside Frank and sent to the eye board through the mouth board's link, so it keeps going while he speaks. The mouth starts it (`Mouth(eyes=True)`), so `--mouth` is enough; `--still-eyes` leaves the eyes still. It uses the poses saved from the slider window (`firmware/eye_poses.json`) and never guesses one: without them the eyes stay still and it says why. `pause()` holds them centred with the lids at their OPEN pose, not blinking (the page's Pause eyes button, `/eyes pause`), and `alive()` has them look around and blink again (Eyes alive, `/eyes alive`); the two buttons show only while the eyes are running. On exit the eyes go to centre with the lids shut. |
| `engine/` | The face performance engine ([docs/FACE_ENGINE.md](../docs/FACE_ENGINE.md), 2026-10-30): the orchestrator (states, tags on the audio clock, gaze from the vision), the synthesiser (a mood plus one fading weight per tag, blended region by region) and the animator (blinks, saccades, aversion, idle drift, brow beats, springs), with the rig sending the eyes, lids and brows through the mouth board's link and the emotion part of the corners to `mouth.py`. Starts with `chat.py` and `web.py` (`--no-face` turns it off, and `gaze.py` has the eyes again); with the engine on, it is the eyes, and `/eyes pause` / `alive` and the page's buttons go to it (`engine.gaze`); `engine/preview.py` is a page to try every tag and state without keys or the head. |
| `eyes.py` | His vision, from the webcam on top of the jar (see Vision below): faces, who is talking, being moved, darkness, and the scene. Runs in its own process under `chat.py --see`, with a preview window. Also enrols the creators (`--enroll NAME --creator`). |
| `faces.py` | Face finding and fingerprints (OpenCV YuNet and SFace), and the gallery of people he may recognise: one SQLite file in `output/frank/memory/`, never committed. `faces.py list` and `faces.py forget NAME`. |
| `scene.py` | Snapshots now and then to a vision model (Claude Haiku 5.5) for a short description: costumes, what people hold and do, the room. |
| `camera.json` | Which camera, its field of view, and where it sits relative to his eyes. |
| `web.py`, `web.html` | Frank in the browser, at http://localhost:8800, served by the laptop: his camera with the faces marked, who is in view, the conversation live (what he hears, says and senses, with his face tags and timings), and his switches (microphone, voice, brain, new conversation, a silence, notes, feedback, enrolling people, forgetting them). Runs the same `Chat` as `chat.py`, which still prints to the terminal. Local only: 127.0.0.1, and its actions need a header other websites can't send. |
| `.env.example` | Copy to `frank/.env` (git-ignored) and add the API keys. |

## Bake-off: choosing the brain

```
uv run --no-project --with anthropic --with openai python frank/bakeoff.py
```

1. **Run it.** Every model with a key in `frank/.env` goes through all 23 scenarios. It prints each model's time to the first whole sentence and writes a run folder under `output/frank/bakeoff/`.
2. **Rate it.** Anushhka and Lars each open `rate.html` from the run folder in a browser, rate every reply 1 to 5 without knowing which model wrote it, and press "Save ratings". Put each saved `ratings_<name>.json` into the run folder.
3. **Score it.** `uv run --no-project --with anthropic --with openai python frank/bakeoff.py --score output/frank/bakeoff/<run>` reveals which model wrote what, prints ratings beside the timings, flagged replies and tool behaviour, and writes `summary.md`.

To test fewer, use `--models haiku-5.5,gpt-5.4-mini` and `--only child,inject`. `--dry-run` checks the plumbing without any API calls.

## One turn

1. **Listening.** Streaming speech-to-text runs while the visitor talks. The face controller shows Listening.
2. **Thinking.** When end-of-speech is detected, the controller switches to Thinking straight away: eyes drift off, a slight furrow, maybe a soft "hmm" clip. This covers the time until the first audio arrives, so Frank looks like he's considering instead of freezing.
3. The transcript goes to the model as the user message, followed by any new context notes. The model streams its reply.
4. **Parse the stream.** Each `[tag]` goes to the face controller at once and is stripped from the text. The text goes to ElevenLabs streaming TTS in sentence-sized chunks. Send the first sentence as soon as it ends; the prompt keeps that sentence short.
5. **Speaking.** The jaw, lips and tongue follow the audio. Expression tags set the brows, lids and eyes on top.
6. **Barge-in.** If the visitor talks over Frank, stop the audio and add a context note saying what they actually heard (see below). Leave Frank's reply in the history as he wrote it. The history is append-only: editing an earlier turn breaks the prompt cache, and the newest models reject edited history when thinking is on.

## Expression tags

`[neutral] [curious] [excited] [skeptical] [amused] [concentrating] [confused] [irritated] [surprised] [vulnerable]` set the face. `[chuckle]` plays a short laugh in Frank's voice: a pre-made clip, or an ElevenLabs audio tag if the chosen voice model supports one.

Rules for the parser:
- Every reply starts with a tag. More can follow mid-reply.
- A reply that is only tags means Frank stays silent and just makes the face.
- Drop any bracketed word not on the list. Never send it to TTS.

What each expression looks like is in CHARACTER.md §6. The controller owns timing, blending, intensity and the servo limits.

The controller's own states (Idle, Person detected, Greeting, Listening, Thinking, Speaking, Interrupted, Farewell) are driven by the vision and audio events, not by the model.

## Tools

All three are client tools, defined in `brain.py`. Their inputs stream as they are generated and arrive unvalidated, so the laptop checks each one (`brain.valid_input`) before acting on it.

```json
{"name": "remember_person",
 "description": "Remember the visitor Frank is talking to, as soon as they have told him their first name. Links their face to the name so he knows them next time, and starts a memory of them. Not for children, and not for anyone already recognised.",
 "input_schema": {"type": "object", "additionalProperties": false,
   "required": ["first_name", "notes"],
   "properties": {
     "first_name": {"type": "string"},
     "notes": {"type": "string", "description": "A few words on them: how you met, what they said so far. One or two sentences at most."}}}}

{"name": "forget_person",
 "description": "Delete everything stored about the visitor Frank is talking to (face and memories), because they asked.",
 "input_schema": {"type": "object", "additionalProperties": false, "properties": {}}}

{"name": "go_quiet",
 "description": "Fall silent because someone asked Frank to be quiet, to stop talking or to give them a moment. From the end of this reply he hears nothing and answers nothing until someone says his name (\"Frank, are you there?\") or the time they asked for is up. Say at most a word or two in the same reply, or nothing.",
 "input_schema": {"type": "object", "additionalProperties": false,
   "properties": {"minutes": {"type": "number", "description": "How long they asked for, if they said. Leave it out when they didn't."}}}}
```

**Being quiet** (`go_quiet`, `chat.shush` / `wake` / `hushed`, 2026-10-30). "Be quiet for a bit, Frank" gets a word or two ("As you like.") and the tool call; from the end of that reply the loop drops every line it hears (shown greyed on the page, "quiet: he ignores it…", logged as `ignored` with `why: quiet`), fills no silences and doesn't react to what the eyes see (their notes still queue up). A line with his name in it (`chat.WAKE`: Frank, Frankie, Franky, as the ears spell it) brings him back at once, and counts as said to him whatever the mouths say (it sets `asked_at`, like a question of his); with `minutes`, the first line after the time is up does too. He gets a note (`Quiet over: you were asked to be quiet about N minutes ago and kept it; they've just said your name. K things were said meanwhile that you didn't take in. …`) and answers that line. A new conversation (everyone gone, `/new`) ends the quiet without a note. `/quiet [minutes]` and `/wake` do it from the console; the page's status pill reads Quiet. Checked against Sonnet 5.5 with the real prompt: "be quiet for a bit", "shush for five minutes" (`minutes: 5`) and "hold on, give us a minute" (`minutes: 1`) all called the tool with a one-line answer; "can you be quiet? No, not you, sorry" and "I've been quiet about it for years" didn't; called back, he answered in one dry line.

The laptop decides whose face "the visitor" is: the person the vision system has as the current speaker. When unsure (a group, a turned face), it returns an error in the `tool_result` and Frank asks them to look at him. With `--see` (`chat.run_tools`, `eyes.Vision.enroll` and `forget`):
- `remember_person` stores the best 4–12 fingerprints of whoever said the last line, taken in the 15 s before (100 px wide or so, facing him, sharp), with the time and their words (the line with their name) as the consent record. A face that already matches someone stored gets "Already remembered".
- **The stranger flow** (D29, 2026-10-30): a stranger arrives → `Arrived: a stranger…` wakes him ("(no speech)") → he greets them, says he's Frank and asks who they are (one question) → their answer counts as said to him for 10 s whatever the mouths say (`ASKED_S`) → he calls `remember_person` in the reply that uses their name and tells them, once, that he'll remember them and that they can ask him to forget them → `run_tools` enrols the speaker of that line. If the eyes couldn't tell whose face it was, the tool result says so and he asks them to look at him and tries again next turn. Next time they come, `Arrived:` / `Recognised:` carry a `Memory of NAME: met DATE; NOTE.` line (`faces.Gallery.memory`, from `remember_person`'s note). Checked against Sonnet on 2026-10-30 with a scripted conversation: greeting with one question and no tool; name → `remember_person`; a later "don't remember me" → `forget_person`; a six-year-old, a creator and a returning visitor with a memory note → no tool.
- `forget_person` deletes that person and every fingerprint of them. It won't delete a creator, and does nothing when the face only possibly matches someone.
- Without `--see` the tools get fixed answers, as in the bake-off.

Put the `tool_result` at the start of the next user message, before that turn's transcript. That costs no extra model call.

## Context notes

The visitor's words go in the user message as plain transcript. Prefix the speaker's name when the vision system knows who is talking ("Lars: ..."). Send "(no speech)" when Frank should react with nobody having spoken, such as on an arrival or a long silence.

Notes are sent as mid-conversation system messages (`{"role": "system", ...}`), right after the user message they belong to. The API needs a system message to follow a user message, and this keeps the cached prefix unedited. Never edit or delete an earlier note; append a new one. One short note per change, for example:

```
Now: Thursday 30 October 2026, 9:40 pm. NightHack at Founders Inc., San Francisco. Awake 4 days.
Present: Lars (recognised), one stranger. The stranger is speaking.
Overlapping speech: three voices at once.
Silence: 12 seconds since anyone spoke.
Interrupted: the visitor heard only "Well, I've met a few people, and they're all—".
Observation: the stranger is wearing a lab coat and holding a laptop.
Arrived: a stranger, in front of you, about 1.4 m away.
Recognised: the person on your left is Lars.
Left: a stranger.
Speaking: a stranger on your right.
Moved: you're being picked up or carried; your view is swinging about. Just before, Lars was right in front of you.
Still again: you've been set down; the view is different, so you're somewhere new.
Dark: your vision has gone black. Something may be covering your eyes, or the lights are off.
Observation: in front of you, someone wearing a vampire cape, holding a coffee cup. Long tables with people at laptops, orange string lights.
Memory of Amelia: met 2026-10-30; talked about her garden, her tomatoes weren't growing.
Your recent experiences: flew to San Francisco in a padded crate on 2026-10-29.
Belief (fairly sure, formed 2026-10-30): people at hackathons rarely sleep.
```

Only send an Observation line if the vision system really reports it. The prompt forbids describing anything that isn't in a note. With `--see`, `eyes.py` writes all of these: the `Memory of` line comes with a remembered visitor's arrival or recognition, from `remember_person`'s note (the experiences and beliefs wait for the memory store).

## Memory

Write memory **after** a conversation ends (the visitor leaves), with a separate, non-live model call over the transcript. Never write it inside the live turn: it keeps latency down and keeps the memory selective (CHARACTER.md §11).
- **Relationship memory:** only for people stored through `remember_person` (they gave their name when he asked, D29). Store topics, preferences they shared and shared moments.
- **Autobiographical memory:** places, conversations that changed his mind, open questions, and beliefs with their wording, supporting experiences, confidence, dates and whether they've been contradicted.
- The "thoughts he's turning over" in the prompt are the starting beliefs. Once the belief store exists, they move into it and out of the prompt.

## Vision

`eyes.py`, from the USB webcam on top of the jar. Everything runs on the laptop except the scene snapshots. Each frame:

| What | How | Gives |
|---|---|---|
| Being moved | MediaPipe's selfie segmenter cuts the people out of the picture. Corners in the rest, the room, are followed (optical flow). When they move together faster than 5°/s in 70 % of the frames for 0.8 s, the camera, and so the jar, is moving. If less than 30 % of the picture is room (someone right up close), he can't tell, so he says nothing; that's what made a sweater pulled on at 0.35 m look like a move. After 3 s still, the view is compared with the one from before (ORB features). | `Moved:` and `Still again:` (same place or somewhere new) |
| Sight | Mean brightness and detail of the picture | `Dark:` and "Your vision is back." |
| Faces | OpenCV YuNet on a 960-wide copy, followed from frame to frame. Distance from the face's width (`face_width_m`), direction from the camera's field of view and position. | who is where, and who is engaged: within 2 m and facing him (head turned under 0.35, about 30°) for 0.7 s |
| Who it is | OpenCV SFace fingerprints, 4 a second until recognised. Recognised needs a mean similarity of 0.45 over 5 prints and a 0.08 lead over the next person. 0.363–0.45 is "someone you may have met before (not sure)", with no name. | `Arrived:`, `Recognised:`, `Left:`, `Present:` |
| Mouths | MediaPipe's face landmarker on the 4 nearest faces within 3 m: `jawOpen`, and a steadier head turn than YuNet's. A line is judged by its busiest 0.6 s of mouth movement (`mouth_peak`), so pauses don't water it down. | who said each line (`Lars: …`), `Speaking:` and `Overlapping speech:`, and whether it was said to him at all (below) |
| The scene | A snapshot to Claude Haiku 5.5 (`scene.py`) when someone arrives, when he's set down somewhere new, every 40 s while someone's there and every 150 s when nobody is. Costumes, what people hold and do, the room. Never bodies, age, race, gender or health, and never names from badges or screens. | `Observation:` |

**Who he listens to** (`Vision.heard`, `chat.to_him`). The microphone hears the whole room: reels on a phone, people behind the visitor, his own voice from the speakers. Each line, early guess and interruption is checked against the mouths:
- **said to him:** someone within 2.5 m (engaged or not) moved their mouth (`MOUTH_ACTIVE`, 0.1 jawOpen a second: real mouths at 0.4 m read 0.05–0.26 on real lines, 2026-10-28). Also when the reading is in between (0.05–0.1), when he can't see (dark, being moved), or when someone is right there but their mouth can't be read (a mask, a hand, a turned head; people fill 15 % of the picture).
- **not to him:** every mouth in front of him stayed still (under `MOUTH_STILL`, 0.05), or nobody is there. No reply. The page shows the line greyed out with the reason. "Still" needs evidence: a face followed for at least 1 s and read at least 8 times during the line; a face he's only just found, or a line said while he couldn't see properly, is listened to. (Sonal's face kept being lost while he was handled, read 0.0, and he dropped her name three times, 2026-10-28.)
- **For 10 s after he asks a question**, any line counts as the answer, mouths or not (`chat.ASKED_S`).
- **Interruptions** (`barge`): his own voice through the speakers is the usual false one. The ears' echo filter drops it (3 or more new words, or a stop word, are needed; `ears.echo_check`), then a solid reading that no mouth in front of him moved blocks it unless a hard stop word was said (`chat.HARD_STOP`: stop, wait, Frank, hold). Each decision is logged with the new words and the mouths. A second channel needs no words at all: the microphone loud for 0.3 s while a mouth in front of him is moving (`chat.OVER_HIM_S`) stops him, since the echo canceller can swallow a visitor's words during his speech; what the speech service does hear while he talks is logged as `while_speaking`. After he stops, his words are still echo for 2 s (`ears.ECHO_WINDOW`).
- **Pause first, then decide** (`chat.PAUSE_*`, `voice.Voice.pause`). The first partial transcripts are too short for the echo filter ("Do you have" is two new words), so waiting for words alone left him talking over the visitor for a second or two (2026-10-30). Now the microphone loud (after echo cancellation) for 0.25 s while he talks pauses his voice at once, mid-word; the jaw shuts. Paused, his voice is out of the microphone, so the echo filter needs only two new words to stop him for good. If the words say it was his own echo, or the eyes block the barge, or nothing comes within 1.5 s, or the microphone goes quiet again for 0.3 s, he carries on where he left off: a hesitation. A false pause raises the level the microphone must beat next time (1.5x the run that caused it, for the session), so his own residual echo can't make him stutter all evening. Logged as `pause` (level, peak, floor, whether a mouth moved) and `resume` (why, held); the page's status pill reads Paused. The log's timestamps now carry milliseconds for this.
- A stopped piece is no longer drained: its download is abandoned, so his answer to the interruption isn't held up by it, and a sentence that was already on its way to the voice is dropped (`Voice.quiet`).
- **Pause first, then decide** (`chat.PAUSE_*`, `voice.Voice.pause`). The first partial transcripts are too short for the echo filter ("Do you have" is two new words), so waiting for words alone left him talking over the visitor for a second or two (2026-10-30). Now the microphone loud (after echo cancellation) for 0.25 s while he talks pauses his voice at once, mid-word; the jaw shuts. Paused, his voice is out of the microphone, so the echo filter needs only two new words to stop him for good. If the words say it was his own echo, or the eyes block the barge, or nothing comes within 1.5 s, or the microphone goes quiet again for 0.3 s, he carries on where he left off: a hesitation. A false pause raises the level the microphone must beat next time (1.5x the run that caused it, for the session), so his own residual echo can't make him stutter all evening. Logged as `pause` (level, peak, floor, whether a mouth moved) and `resume` (why, held); the page's status pill reads Paused. The log's timestamps now carry milliseconds for this.
- A stopped piece is no longer drained: its download is abandoned, so his answer to the interruption isn't held up by it, and a sentence that was already on its way to the voice is dropped (`Voice.quiet`).
- **Figures:** a face pixel-still for 20 s (`FIGURE_S`, `FIGURE_DRIFT`) is a printed head or a poster, not a person: not engaged, not counted, not listened to.
- Every turn's log entry carries the mouth readings (`mouths`), so the thresholds can be set from a real session.
- He's told at most once a minute, without the words: "Background: there's talking nearby that isn't to you, and your visitor isn't the one speaking…", or "…nobody is talking to you" when nobody's there.
- `/gate`, or the Mouth check switch on the page, turns the check off.
- **Told to be quiet** (`go_quiet`, above), nothing is answered until a line says his name, which then counts as said to him.

Tested 2026-10-28 on the clip with lines put in by hand:
- reel lines while the visitor's mouth was still: not answered;
- an interruption from a reel: not interrupted, and his reply went on;
- a line with the check off: answered.

Anushhka's first session, before this, had 9 of its 12 heard lines from reels.

**Identity never travels by position.** When a face vanishes and one reappears in the same spot, the new one is "someone's there"; it gets the old name only if the faces match (`_inherit(matched=True)`). By position alone, Lars became Anushhka. Lines said while he's being carried can't be credited by mouth at all; that needs voice recognition (open).

**Speaking unasked** (`chat.saw`, `free_prompt`, `silence_prompt`). He reacts, with "(no speech)", to: the first arrival of a session; any new person arriving mid-conversation (at most every 15 s); being picked up; being set down (once per bout); going dark. If the reason comes while he's busy or someone's talking, it's held and fires when he's free. And when someone's with him and nobody has spoken for 25 s, half the time he says something (`Silence:` note).

**Reply length is the main latency with a group.** v3 speaks this voice at about 11 characters a second regardless of settings, so a 30-word reply plays for 15 s. The prompt caps replies at one sentence (two at most) and one short sentence to one person when a `Group:` note says several people are there.

**Sessions.** The first engaged person starts one, and 20 s with nobody engaged ends it. `chat.py` then starts a new conversation, so history doesn't pile up all night, and the system prompt stays cached. When someone arrives, Frank studies them for up to 3–4 s while the scene snapshot comes back, then reacts unprompted ("(no speech)"). He also reacts unprompted when he's picked up, set down, or goes dark, at most once every 30 s per kind.

**Privacy.**
- Strangers' fingerprints exist only in the vision process and go when the session ends.
- Only the creators and the visitors who gave Frank their name when he asked (D29) are in the gallery (`output/frank/memory/frank.db`, git-ignored). He tells each one that he'll remember them and that they can ask to be forgotten; `forget_person` deletes them on the spot. It holds face data: never commit or share it.
- Snapshots go to the API as JPEGs and are never saved.
- The native libraries' messages go to `output/frank/eyes.log`.

**Commands** (add `--with opencv-python --with mediapipe` to the usual `uv run` line):
- `frank/eyes.py --cameras` lists the cameras; put the right number in `camera.json` as `source`.
- `frank/eyes.py` opens a preview window: faces with names, scores, distance, turn and mouth movement, and whether he's moving. The notes print in the terminal.
- `frank/eyes.py --enroll Anushhka --creator` enrols a creator: one person in view, turning their head a little; 20 prints.
- `frank/faces.py list` and `frank/faces.py forget NAME`.
- `frank/chat.py --talk --see` runs the whole thing in the terminal. `--video clip.mp4` plays a recording instead of the camera, and `--no-preview` hides the window.
- `frank/web.py` runs the whole thing with the browser page instead (http://localhost:8800). It takes `--talk`, `--mute`, `--model`, `--place`, `--speaker`, `--video`, `--no-see` and `--port`. The page's Speaker menu chooses where his voice plays (default: the Mac's output), and Test sound plays a short tone through it.
- **Camera permission on a Mac:** the first time, macOS has to allow the app that runs Frank (Visual Studio Code if it's started in VS Code's terminal, or Terminal) under System Settings › Privacy & Security › Camera. Until then OpenCV reports "not authorized" and the page says so. The vision process tries the camera again every 3 s, so switching it on needs no restart. It also exits by itself if `chat.py` or `web.py` dies.

**Tuning** (constants at the top of `eyes.py` and `faces.py`, checked in the preview):
- `face_width_m`: until the preview's distances match a tape measure.
- `ENGAGE_M` and `FACING`: who counts as there to see him.
- `MOUTH_ACTIVE` (0.4): the preview's "mouth" figure while someone talks, against when they're quiet.
- `faces.KNOWN` (0.45): the match scores of enrolled people against strangers, best checked on a clip recorded at the venue.
- `MOVE_SHIFT` and `MOVE_ROT`: if flashing or moving party lights ever count as him being moved.

**Tested (2026-10-28)** offline on made-up frames (`Vision.step` on a clock of its own) and end to end with `chat.py --see --video`. These all behaved: arrival, recognition after enrolling (0.93 at a different size and place), leaving, session end, two people with the speaker picked by mouth movement, a person walking past (not "moved"), being carried and set down (same place, and somewhere new), darkness, the preview, `--enroll`, and an unprompted greeting. Real faces, the webcam, real mouths and the venue lighting haven't been tried yet.

## Feeling quick

Time to his first sound is what visitors notice. Three things shorten it (2026-10-28):
- **The brain.** Measured with his prompt, median time to the first whole sentence: Opus 2.35 s, Sonnet 1.50 s, GPT-5.4 mini 1.41 s, Haiku 0.71 s. The default is now **Sonnet**; `--model` changes it.
- **Ending the turn on a still mouth** (`chat.watch_mouth`, `eyes.Vision.mouth_still`). When a sentence ends, the eyes watch the mouths in front of him; once they've been still for 0.3 s he answers, instead of waiting for the speech service's own silence plus grace (about 0.75 s). If more words then arrive, that answer is cut and the whole line answered (`early` in the log says a turn started this way).
- **Backchannel** (`voice.FILLERS`, `chat.FILLER_AFTER`). Clips are per voice and model, so they were remade for v3. If nothing of his reply is out 0.9 s after the visitor stops, a "Hmm.", "Hm." or "Well..." in his own voice plays (on 70 % of such turns). The clips are made once per voice and model (`voice.py fillers`, into `output/frank/voice/fillers/`) and go through the same queue as his sentences, so they always come before the reply, never inside it. They're filler words to the ears, so coming back through the microphone they can't interrupt him.
- The prompt now tells him not to report on his own senses or on being interrupted: that cost a sentence every turn.

## Model and latency

Time to first audio is what visitors notice: end-of-speech detection + model first token + first TTS audio. Measure it with this prompt before choosing.

The candidates are set up in `brain.MODELS`. A wrong model name or setting is a one-line fix there.

| Candidate | Reasoning setting used | Note |
|---|---|---|
| Claude Haiku 5.5 (`claude-haiku-5-5`) | thinking disabled, effort low | the fastest Claude first token |
| Claude Sonnet 5.5 (`claude-sonnet-5-5`) | `thinking: {type: "between_tools"}`, effort low | stronger character work, still quick |
| Claude Opus 5.5 (`claude-opus-5-5`) | thinking can't be disabled; effort low | best quality, slowest first token |
| GPT-5.4 mini (`gpt-5.4-mini`) | `reasoning_effort: "none"` | OpenAI's small, fast model |

xAI's Grok was dropped from the candidates on 2026-10-26.

- **Refusal fallback:** Sonnet and Opus requests carry the server-side refusal fallback (`fallbacks: "default"`). If a request is declined, it is retried on another Claude model. The bake-off flags any reply served by a different model.

- **Prompt caching:** put `cache_control` after the tools and the system prompt, and check that `usage.cache_read_input_tokens` is above zero from the second turn on. A timestamp or anything else that varies per turn inside the system prompt silently breaks the cache. Those go in context notes.
- **Sampling settings:** since 2026-10-21 the API rejects `temperature` / `top_p` / `top_k` on every model. Leave them out.

## Still open

- **Awakening date.** Suggested: the day the full system first holds a conversation. The laptop computes "Awake N days" from it.
- **Children and remembering.** Since D29 there is no age question: the prompt says never to remember a child, and he goes by the voice and the scene observations. Whether that is enough is for the creators to watch at the first event.
- **`[chuckle]`:** not voiced for now. A voiced laugh made him sound giggly, so it only shows on his face.
- **A sign at the jar** stating that it's an AI character and that the camera and microphone are on, and that snapshots go to an AI service to describe the scene. Frank remembers visitors who tell him their name (D29), and they can ask him to forget them. It needs a contact for visitors who want to be forgotten after they've left, and how long profiles are kept.
- **On site, before the doors open:** measure the camera's position (`camera.json`), enrol Anushhka and Lars under the event lighting, and check distances and the recognition and mouth thresholds in the preview (Vision, "Tuning").
- **Forgetting transcripts.** `forget_person` deletes the face and the profile, but the session's chat log in `output/frank/chats/` still holds what they said. It goes with the memory store.
- **The memory store** (relationship and autobiographical memory, Memory above) isn't built yet. Until it is, `remember_person`'s notes are kept with the profile (`people.first_note`).
- **The face controller** is v1 (`engine/`, 2026-10-30). Still to do: exact tag timing from ElevenLabs' stream-with-timestamps, the jaw sent ahead by the measured servo lag, and tuning on the head with the skin on (docs/FACE_ENGINE.md, "After").

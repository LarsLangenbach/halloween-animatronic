# Face performance engine: integration map

Read-only survey of the repo on 2026-10-30 (commit dee78bd plus the working tree). The question is how an orchestrator, a synthesiser and an animator would plug into Frank's laptop software (`frank/`) and the Pico firmware (`firmware/`). References are `file:line`.

## 0. The short version

- **Fix this first: a bug that kills the voice.** `voice.filler()` puts a 3-tuple on the play queue (`frank/voice.py:358`), but `_play` unpacks 4 values (`voice.py:419`, `gen, text, chunks, face`). The face was added to `_send` (`voice.py:381`) in dee78bd, and the filler line was never updated (b08a3a8 had 3 and 3). The first "Hmm." raises ValueError in the player thread, and the thread dies. No more audio plays, `voice.wait()` blocks forever in `Turn._finish` (`chat.py:263`), the turn never ends, and Frank stays "busy". It fires on 40 % of turns where nothing is said 1.2 s after release (`chat.py:89-90`). The fix is one line: `(self.gen, "", chunks, None)`.
- **Timing hook:** `voice.mouth` is a duck-typed object with `feed(pcm)`, `face(name)` and `flush()`. `feed` is called for every 20 ms slice actually written to the sound card (`voice.py:439-442`), so it gives a true playback clock. Any engine object with those three methods can replace `mouth.Mouth` without touching `voice.py`.
- **Dialogue events:** subscribe through `chat.listeners`: every `Chat.ui()` call fans out to them (`chat.py:320, 431-435`). The `events` queue has a single consumer (`Chat.run`) and must not be read by anyone else. A few lifecycle moments have no `ui()` call yet (speculative start and cancel, first sound, session start and end; §2).
- **Vision:** `chat.eyes.state` holds a snapshot dict, refreshed 5 times a second from the vision process (`eyes.py:1013-1015, 1112-1113`). Each face has yaw and pitch in degrees from the midpoint between his eyes (+yaw is his left, +pitch is up), plus distance, engaged and talking.
- **The serial port has one owner today:** `mouth.Mouth` (`mouth.py:153`). It is attached only when the voice is loaded (`chat.py:790`, `web.py:235`). `Mouth.link("<pin> <deg>")` already reaches the eye and brow board (`mouth.py:198-204`), and the path was proven on the head on 2026-10-29 and 2026-10-30 (`BUILD_LOG.md:66, 34`).
- **Already built, PC only, not used by Frank:** `eye_anim.EyeAnim` (gaze wander, blinks, lid follow) and `brow_anim.BrowAnim` (one keyframe expression per speech tag, plus an idle layer). Both have `step(t) -> {socket: angle}`. Today only the tkinter slider window runs them (`servo_controls.py:157-162, 224-232`).

## 1. Expression tags: from the stream to the servos

1. **Parsing.** `speech.TagStream.feed(delta)` (`speech.py:47-74`) emits `("face", tag)`, `("sound", "chuckle")` and `("say", sentence)` in order. A tag in the middle of a sentence comes out before that sentence (the finished sentences are flushed first at `speech.py:67`, then the tag at `68-71`). There are ten faces (`speech.py:17-18`), and the aliases are mapped to them (`22-32`). Unknown bracketed words go to `.unknown` and are never spoken. `flush()` ends the reply (`76-83`).
2. **The Turn.** `Turn._run` feeds every text delta into a TagStream and collects the events in `self.waiting` (`chat.py:192-206`). Nothing is shown until the turn is released (`go`, `chat.py:141-146, 205-216`). `_show_locked` (`chat.py:224-253`) then does three things:
   - For `face`, it sets `self.face` and calls `chat.ui("face", tag=...)` (`248-252`). This happens **at text time**, often a second or more before the audio, because the brain streams ahead of the TTS.
   - For `sound`, it sets `self.chuckle` and calls `ui("sound")`.
   - For `say`, it calls `ui("say")` and `voice.say(sentence, self.face, self.chuckle)` (`236-244`).
   - A tag-only reply ("[concentrating]", allowed by `system_prompt.md:73`) produces **only** `ui("face")`. Nothing reaches the voice or `mouth.face()`.
3. **The voice's piece queue.** `Voice.say` groups sentences into pieces: the first at least 30 characters, the rest at least 160 (`voice.py:45, 315-332`). The piece's face is the face of its **first** sentence (`buf_face`, `voice.py:327-328`). A later tag inside the same piece reaches v3 as an inline delivery tag (`voice.py:319-324`, `V3_TAGS` `54-56`) but never reaches the mouth. `_send` queues `(gen, text, chunks, face)` and fetches the audio in parallel (`voice.py:365-382`).
4. **When a piece actually starts.** `_play` takes the next piece only after the previous one has finished playing (`voice.py:417-455`). At that moment it calls `mouth.face(face)` (`423-424`). This is **before** the piece's first audio, which arrives after the TTS latency (0.6–0.7 s for v3's first piece, `frank/README.md:19`). Later pieces are usually already buffered.
   - `first_sound` is set once per reply, at the first slice (`voice.py:435-436`, relative to `voice.t0` from `start_reply`, `289-292`). It also counts a filler. No callback fires for it.
   - Each slice goes through `out.write` (blocking, about 56 ms of output latency, `voice.py:259`), then `mouth.feed(out)` (`441-442`). `mouth.DELAY = 0.05` compensates for the latency (`mouth.py:80`).
   - Position inside the current piece is `voice.current["played"] / 2 / 24000` seconds (`voice.py:420, 448`). Finished pieces are in `voice.heard`.
   - Pieces queued, fetched, played and dropped are logged only to the jsonl file (`voice.log`, `chat.py:306`), not to `ui()`.
5. **`mouth.face()`** (`mouth.py:233-236`) sets `mood_target` from `MOOD` (`mouth.py:69-70`): smile +0.8 amused, +0.6 excited, +0.3 curious, +0.2 surprised; frown −0.8 irritated, −0.5 skeptical, −0.3 concentrating, −0.2 confused. The mood eases in over 0.5 s and **persists until the next piece's face**, including after speech ends. `flush()` (`238-241`) clears the queued levels on a stop.

**Timing a tag to the audio.**
- Per piece: `face()` fires at the piece boundary, and the first `feed()` after it is the first audible slice.
- Mid-piece tags: the information is lost today. Two options:
  - Carry `(char_offset, tag)` per piece in the order tuple and fire each tag when the played fraction passes its offset. `voice.stop()` already estimates the played fraction this way (`voice.py:306-312`): bytes played over bytes received, or `CHARS_PER_SEC`; v3 measured about 11 characters a second, `README.md:157`.
  - Use ElevenLabs' streaming-with-timestamps endpoint for per-character times. Check that v3 supports it. Lars's TalkingHead.py, outside the repo at `Desktop\Machine Monks\LARS 9001\HeadTest\TalkingHead.py`, uses the non-streaming `convert_with_timestamps` alignment to place visemes. It is the same idea.
- A sensible split: show the first tag on `ui("face")` (a reaction during the TTS wait, which suits Thinking into Speaking), and time later tags to playback.

## 2. Lifecycle events and the controller states

The events go to two places:
- the `ui()` listeners (synchronous, called from whichever thread raised them: Turn threads, the run loop, and the ears' asyncio thread for partials; a listener must return at once);
- the internal `events` queue (`chat.py:321`), consumed only by `Chat.run` (`625-769`).

`web.html:236-243` already turns `ui()` kinds into a status line: hearing becomes "Hearing", visitor "Thinking", say "Speaking".

| Moment | Where it happens | Visible to a listener? | State |
|---|---|---|---|
| Nobody there / session over | Vision `session_end` (`eyes.py:638-643`). Its notes are empty, so `Chat.saw` emits **no** `ui("seen")` (`chat.py:381-390`). The conversation restarts at once, or after the turn (`new_due`, `751-753`) | only as `ui("new")` (`chat.py:335`); `eyes.state["session"]` turns False | Idle |
| Someone engages (within 2 m, facing, 0.5 s) | `Vision._engage` sets `session = True` and starts the arrival study (`eyes.py:657-668`). **No event** | poll `eyes.state["people"][i]["engaged"]` / `["session"]` | Person detected |
| First arrival, after studying them (up to 1.5–2.5 s, `STUDY_S` `eyes.py:72, 773-775`) | `_arrive` emits `arrived` with `prompt` (`eyes.py:670-684`), then `Chat.saw` returns True and `begin("(no speech)")` (`chat.py:721-723`) | `ui("seen", what="arrived")`, then `ui("visitor", said="(no speech)")` | Greeting (the study window is CHARACTER §6 "briefly studies the visitor", `CHARACTER.md:361-367`) |
| Later arrivals, recognised, left, moved, still again, dark, light, observation | `_emit` calls (`eyes.py:609-611, 654-655, 686-688, 732-734, 747, 753-756, 769`) | `ui("seen", what=kind, notes, prompt)` (`chat.py:382`) | `left` of the last engaged person is a Farewell cue (prompt False: he doesn't speak, `eyes.py:688`) |
| Visitor starts talking | The mic gets loud: `ears.last_voice` / `loud_since` (`ears.py:165-169`, 100 ms chunks); then the first partial sets `chat.speech_t0` (`chat.py:521-525`) | poll `chat.ears.loud_for()`; then `ui("hearing", text)` for every partial | Listening |
| A sentence ends (speculative turn starts) | `on_early` puts "early" on the queue, which makes `spec = Turn(..., released=False)` (`chat.py:532, 677-689`) | **no** | (pre-think; may be cancelled) |
| They carry on (speculative turn thrown away) | "resumed" (`chat.py:690-694`) | **no** | back to Listening |
| Mouth still 0.3 s (early release) | `watch_mouth` puts "still", then `begin(..., early=True)` (`chat.py:649-657, 695-698`) | `ui("visitor")` | Thinking |
| Turn ends by silence | `on_final`, then "heard", then `begin` (`chat.py:527-530, 699-720`); `speech_t0` goes back to None (`528`) | `ui("visitor", said)` (`chat.py:637`) | Thinking |
| Line not said to him | `to_him` False (`chat.py:483-504`) | `ui("ignored")` (`499`) | stay Listening / Idle |
| Filler "Hmm." | `Turn._fill`, 1.2 s after release, 40 % of the time, never twice running (`chat.py:148-166`) | `ui("sound", tag=words)` (`164`: the same kind as `[chuckle]`) | Thinking (the filler audio goes through `mouth.feed`) |
| Reply opens / first sentence | `frank_start` on the first show (`chat.py:226-232`), usually at the first token after release; `first_say_at` (`238-239`) | `ui("frank_start")`, `ui("face")`, `ui("say")` | Thinking, then Speaking |
| First sound | `voice.first_sound` (`voice.py:435-436`) | **no** (only the first `feed()` on the mouth hook) | Speaking |
| Barge-in | `on_barge` or `_over_him` puts "barge" (`chat.py:534, 561-571`). Blocked barges go to `ui("ignored", why="while he spoke…")` (`736-742`). Real ones: `current.interrupt()`, then `voice.stop()`, then `mouth.flush()` (`chat.py:171-174`, `voice.py:298-313`) | `ui("interrupted", heard)` (`chat.py:747`) and `flush()` on the mouth hook | Interrupted |
| Turn done | after `voice.wait()` (`chat.py:262-263`) | `ui("frank_end", interrupted, silent)` (`283-284`); ("done", turn) on the queue (`298`) | Speaking ends, back to Listening (the ears re-listen after 0.4 s, `754-755`) |
| Unprompted reactions | held prompts (`free_prompt` `398-405`) and silence (`silence_prompt` `414-426`, after 25 s, half the time) on the 0.5 s "tick" (`756-758`) | `ui("visitor", said="(no speech)")` | Thinking, then Speaking |

**Where the engine subscribes:**
- `chat.listeners.append(engine.on_ui)`. The listener only enqueues; the engine thread does the work.
- `voice.mouth = engine` for the audio clock and flush.
- Poll `chat.eyes.state`, `chat.ears.mode` / `loud_for()` and `chat.ears.last_voice` from the engine's own tick.

**Small additions needed in chat.py:**
- `ui("listening_maybe_done")` and `ui("resumed")` at `chat.py:686` and `693`.
- `ui("session", on=…)`, or poll `state["session"]`.
- Keep the addressee: `begin()` clears `turn_who` (`chat.py:634`), which held the speaker's track id (`474`), so during his reply nothing records whom he is answering. Store `who["track"]` on the Turn before the clear.
- A per-piece "audio started" callback in `voice._play`, if `feed()` isn't enough.

**Clocks are mixed:**
- eyes: `time.time()` (`eyes.py:178`)
- ears and voice: `perf_counter`
- mouth: `monotonic`
- `chat.last_voice_at` converts between them (`chat.py:407-412`).

## 3. What vision gives gaze

- **Process and transport.** `eyes.Eyes` spawns a separate process (`multiprocessing` "spawn", `eyes.py:1085-1088`). The child runs `run()` and puts `("state", snapshot)` on a Queue at most every 0.2 s of frame time (`eyes.py:993-1015, 1058-1059`). The reader thread stores it as `Eyes.state` (`1112-1113`). If the process dies, `state` becomes None (`1104-1108`).
- **Rates.**
  - The camera is asked for 30 fps (`eyes.py:157`). Processing ran at about 15 fps on the Mac (`BUILD_LOG.md:314`); detection takes 5 ms and a fingerprint 7 ms (`280`). The preview overlay shows the actual fps.
  - Snapshots arrive at 5 Hz. Raising them is a one-number change (`0.2` at `eyes.py:1013`).
  - Latency is about the snapshot age, `time.time() - state["t"]`. `t` is the frame's capture time.
- **Snapshot (`Vision.snapshot`, `eyes.py:894-910`).** Top level: `t, moving, settling, background, people_share, blind, session, far, people[], enrolling`. Each person: `id` (track id; a lost and re-found face gets a new id, `eyes.py:524-528, 562-572`), `engaged`, `level` (known/possible/None), `stranger`, `figure`, `name`, `score`, `dist` (m), `yaw` (deg), `pitch` (deg), `place`, `talking` (mouth activity over the last 1 s at least `MOUTH_ACTIVE` 0.1), `mouth`. Head turn (`tr.turn`) and the box are **not** included.
- **Who is speaking:** `talking` per person. The speaker credited for a line is `chat.turn_who["track"]` (`chat.py:473-475`, from `Vision.speaker` `eyes.py:789-810`), which is cleared at `begin` (§2).
- **Frame.** `Geometry.locate` (`eyes.py:195-218`) gives the direction from the midpoint between his eyes in the head frame (PLAN §4: +x his left, +y front, +z up). +yaw is to his left, +pitch is up. The camera's offset and tilt are applied, so these are parallax-corrected eye angles, not camera angles.
  - `camera.json:2-10`: `offset_mm [0,0,250]` (lens 250 mm above the eyes), `tilt_deg 10` down, `hfov_deg 78`, `face_width_m 0.16` (distance from face width), `mirrored false`. **All of these are assumptions until measured on site** (`camera.json:10`, `README.md:219`).
- **Gaps.**
  - While he is being moved or is blind, faces aren't processed (`eyes.py:483-486`), and a move empties `tracks` (`eyes.py:724`). `people` goes empty or stale, so gaze must hold or wander rather than snap to the centre.
  - Figures (still faces after 20 s) carry `figure: True` (`eyes.py:548-560`); skip them.
- **Eye servo mapping is not calibrated.**
  - Centre: LLL 107 (LR), LLR 62 (UD) (`eye_poses.json:14-17`). The idle range is ±30 servo degrees LR and ±15 UD (`eye_anim.py:19-20`).
  - Unknowns: which LR direction is his left, the sign of UD (`UD_UP = +1` is assumed, `eye_anim.py:21`, never checked, `BUILD_LOG.md:450`), and the servo-to-eye gain (the CAD sweeps treat the linkages as 1:1 as an upper bound, `cad/params.py:159-163`).
  - Both eyes share one LR and one UD servo, so there is no vergence.
  - The system prompt promises the controller "keeps your eyes on whoever is speaking" (`system_prompt.md:62`).

## 4. Servo ownership and the wire protocol

**Today's owner.** `mouth.Mouth` (`frank/mouth.py:134-362`):
- Opens pyserial at 115200 (USB CDC, so the baud rate does nothing) on `find_port()` (`97-111`: a Pico or MicroPython description, else the first usbmodem or COM port).
- Asks `where` to detect `cogley_mouth_main.py` (`180-188`). If that fails it sends Ctrl-C Ctrl-C and Ctrl-D and asks again (`154-160`).
- With the Cogley program it sends `speed 720` (`163-164`). The board **clamps this to 600** (`cogley_mouth_main.py:297-298`).
- One `threading.Lock` guards every write (`mouth.py:165, 191-196, 202-204, 304-306`), and each write is followed by `reset_input_buffer()`, which discards the board's echoes.
- The thread `_run` (`mouth.py:316-349`) ticks every `TICK` 0.02 s plus its work time, so the period drifts slightly over 20 ms.
  - The jaw goes every tick (50 Hz); lips, corners and tongue every second tick (25 Hz). Nothing is sent unless it changed (`_set` `243-248`, `_jaw` `295-314`).
  - Jaw envelope: a −42 to −16 dBFS map to 0 to 0.85 of open, attack 35 ms, release 90 ms, shut after 120 ms of quiet (`75-83`).
  - Lips use attack 60 ms and release 150 ms at 60 % of lips_up / lips_down. Corner width follows the spectral centroid, 400–2500 Hz (`84-89`).
  - Vowel blend once AH, EE and OO are saved (`269-293`); mood on the corners (`260-264, 288-289`).
  - The tongue is off (`TONGUE = False`, `90`).
  - On `pico_servo_ctl` the jaw is let go 3 s after the last sound (`344-348`).
- There is no reconnect. A SerialException inside `_run` ends the daemon thread silently. `close()` (`351-362`).

**Board 1 (mouth), on the laptop's USB.**
- It runs `cogley_mouth_main.py` (TalkingHead's gliding MouthMaster plus the link). The 2026-10-29 and 10-30 entries call it a Pico 2 (`BUILD_LOG.md:34, 64`); `firmware/README.md:53` still says RP2040.
- Commands (`HELP` `cogley_mouth_main.py:111-125`, `do()` `244-313`):
  - Cogley's pose names (smile, frown, wide, narrow, mouth_open and the rest);
  - `jaw <0..1>` (`182-185`, using the board's `JAW_DIR -1`, `JAW_DEG 40`, `59-60`; not persisted, the defaults match);
  - `jawdeg`, `jawdir`;
  - `talk [0..1]` / `stop` (Pico-side random chatter, `201-238`);
  - `set <NAME> <deg>` (`288-296`);
  - `speed <deg/s>`;
  - `rest` (closed, tongue down, narrow; lips unpowered, `98, 299-302`);
  - `relax` (all servos limp, with no per-servo off, `303-306`);
  - `where` (`307-309`);
  - `e <text>`, which forwards over UART0 (`254-256`).
- It clamps every servo to `LIMITS` (`70-82`) and glides at `SPEED` (boot default 90 deg/s, `54`) with a 20 ms loop (`53, 330-352`).
- It prints `Received: …` for every line that isn't an `e` line (`336-337`).
- Pulses run 544–2400 µs over 0–180 (`50-51`).
- REST is applied at boot (`322-323`).

**Board 2 (eyes and brows), reached over the link.**
- It runs `pico_servo_ctl.py`.
- Commands: `<GP pin> <angle>` (clamped to −27..207, 200–2800 µs, `pico_servo_ctl.py:72-79`), `<pin> off` (pulse 0, `68-71`), and `e …` (forwarded only if it came over USB, `54-59`).
- Pulses run 500–2500 µs over 0–180 (`78`). This is **not the same mapping as Board 1**, so an angle number is only meaningful for the program it was measured on.
- No glide and no per-servo limits: every safety limit for Board 2 lives on the PC.
- The main loop reads the UART and up to 64 USB characters per pass, sleeping 2 ms (`83-119`).
- Link: UART0, GP16 TX to GP17 RX, 115200 8N1, one way, no acknowledgement (`29-45`; `firmware/README.md:45-47`). A link fault shows only as eyes that don't move (`BUILD_LOG.md:72`).
- Bandwidth: a line `"8 107\n"` is about 6 bytes. All 10 Board 2 servos at 50 Hz come to about 3 kB/s, roughly a quarter of the UART (about 11.5 kB/s). Sending only on change cuts that further.
- End-to-end delay: Board 1's 20 ms loop, then the UART, then Board 2's 2 ms loop, then the 20 ms PWM frame, so up to about 40 ms.

**`share_port.py`** (`firmware/share_port.py:1-50`) opens the real port once and fans it out to N pseudo-terminals (`os.openpty`, `24`): **macOS and Linux only**; Windows needs com0com. Opening `servo_controls.py` **soft-resets** the board on its port (`servo_controls.py:86-91`). On Board 1 that reapplies REST and resets `speed` to 90 under Frank; `mouth.py` sends `speed` only once, at start.

**Pins and sockets.**
- Socket names are the mouth board's silkscreen names, also on Board 2.
- Sides on Board 2 are **as seen from the front** (`servo_controls.py:11`, labels `46-57`; `brow_anim.py:7-8`). The viewer's left is the character's right (−x), which breaks CLAUDE.md's character-side rule. Verify every side with Wiggle before trusting it.
- `mouth.PIN` maps socket names to GP pins (`mouth.py:71-72`).

| GP | Board 1 (mouth) socket and part | Board 2 socket | Board 2 part (viewer side) | Character side (derived) |
|---|---|---|---|---|
| 4 | JL jaw (MG996R) | JL | brow outer, viewer's left | brow_R outer |
| 5 | JR jaw (MG996R) | JR | brow outer, viewer's right | brow_L outer |
| 6 | LUL upper lip | LUL | brow inner, viewer's left | brow_R inner |
| 7 | LUR upper lip | LUR | brow inner, viewer's right | brow_L inner |
| 8 | LLL lower lip | LLL | eyes left/right (both eyes) | - |
| 9 | LLR lower lip | LLR | eyes up/down (both eyes) | - |
| 10 | CUL upper corner | CUL | bottom lid, eye on viewer's right | left eye, bottom |
| 11 | CUR upper corner | CUR | top lid, eye on viewer's right | left eye, top |
| 12 | CLL lower corner | CLL | bottom lid, eye on viewer's left | right eye, bottom |
| 13 | CLR lower corner | CLR | top lid, eye on viewer's left | right eye, top |
| 14 | TON tongue (no servo fitted) | - | - | - |
| 15 | spare (EXA) | - | - | - |

Sources: `firmware/README.md:11-31`, `mouth_controls.py:37-48`, `servo_controls.py:46-57`, `eye_anim.py:15-17`, `brow_anim.py:18-19`. Cogley's mouth L and R are **not matched to face sides** yet (`mouth_controls.py:35-36`).

**Where limits, neutral and poses live (scattered: five places).**
- Board 1 limits: on the Pico in `cogley_mouth_main.LIMITS` (`70-82`), copied in `mouth.LIMITS` (`mouth.py:62-65`) and `mouth_controls.BOARD_LIMITS` (`93-96`). There are three copies to keep in sync.
- Board 1 poses: `mouth.POSES` (Cogley's angles, `mouth.py:48-60`), overridden by `firmware/mouth_poses.json`, **which does not exist yet**. So mouth.py runs on Cogley's numbers, and the vowel blend is inactive (`mouth.py:144-152`).
- The team's measured mouth neutral (LUL 90, LUR 90, LLL 55, LLR 78, CUL 90, CUR 80, CLL 120, CLR 70; `BUILD_LOG.md:456`) is outside the repo, in `Machine Monks\LARS 9001\HeadTest\cogley_neutral.json`. mouth.py's rest uses lips 90 and Cogley's `narrow` instead (`mouth.py:51, 56`).
- Board 2: `firmware/eye_poses.json`:
  - `shut` / `open` per lid; currently shut CUR 183, CLR 134, CUL 108, CLL 117 and open CUR 139, CLR 188, CUL 143, CLL 53. The file was re-saved on 2026-10-30 at 17:18, after the build-log numbers;
  - `centre` (LLL 107, LLR 62);
  - brow `level` (all 90: **never set**);
  - `brow_travel` raise 35, lower 20 (assumptions).
- The defaults in `servo_controls.POSES` (`servo_controls.py:67-76`).
- Slider ranges as the de-facto Board 2 limits: LR 40–140, UD 60–140, lids −9..189, brows 0..180 (`servo_controls.py:46-57`).
- `eye_anim` keeps the lids between SHUT and OPEN. `brow_anim` keeps each brow within level +RAISE / −LOWER (`brow_anim.py:157-163`).

## 5. What to absorb rather than rebuild

- **`firmware/eye_anim.py`** (PC; plain `random`, so it could run in MicroPython, but no Pico program imports it).
  - `EyeAnim(shut, opened, centre, t)`; `step(t)` returns angles for LLL, LLR, CUR, CLR, CUL, CLL (`92-103`); `rest()` centres the eyes with the lids shut (`105-107`).
  - `pose(x, y, lids)` (`109-116`) is the reusable core: gaze from −1 to 1, lid openness from 0 to 1, lid follow on the top lids (0.25) and bottom lids (0.15).
  - Random saccades with eased moves (`52-71`), blinks with close/hold/open shapes, double and slow blinks (`28-30, 73-100`), and a wake-up (`25`). `MOVE_BOTTOM_LIDS = True` now (`26`); `firmware/README.md:37` still says only the top lids blink.
  - To become the gaze and blink layer it needs a target override (vision or Thinking aversion), a blink trigger (on gaze shifts and emotion), and `LID_REST` (`22`, 0.85) as the input for lid narrowing and widening. Widening has little headroom: OPEN is the maximum, and "never guess an OPEN pose" (`servo_controls.py:64-65`).
- **`firmware/brow_anim.py`** (PC; plain `random`).
  - `BrowAnim(level, t, raise_deg, lower_deg, idle)`, `play(name, t)` (`102-107`), `step(t)` returns angles for JL, LUL, JR, LUR (`122-151`), `rest()`.
  - `EXPRESSIONS` (`58-83`) is keyed by the ten `speech.FACES`, plus `greeting` and `furrow`, as fraction keyframes drawn from CHARACTER §6.
  - The idle layer adds drifts and one-brow flicks (`30-32, 129-148`).
  - `DIR` (`24`) is Cogley's and **unverified** on this build. This is the synthesiser's brow output nearly as it stands; it needs blending with weights instead of a hard replace on `play`.
- **`frank/mouth.py`** (PC). Already the speech layer, apart from owning the port:
  - `analyse()` (dBFS and spectral centroid, `114-127`);
  - the envelope followers;
  - the vowel blend;
  - `MOOD` as a crude emotion-on-corners layer;
  - `find_port`, program detection, `speed`.
  - Split it into `step(t) -> targets` and leave the transport to the rig.
- **`servo_controls.py` and `mouth_controls.py`** remain the calibration tools that write the pose files. The engine reads those files and must not run at the same time (only one process can hold the port, `BUILD_LOG.md:114`).
- **Cogley's own code** (`inputs/reference/head_a2.0.33/Code/`; Patreon, summarised only):
  - `MouthMaster.py`: reads named commands on USB, jumps 11 mouth servos to fixed poses, and drives the eye and brow boards through two 2-bit GPIO pairs.
  - `eyes.py`: an autonomous random mode (blink, random UD with the lids following UD, random LR, 0.4–1 s sleeps), plus open, closed and calibrate states.
  - `Brows.py`: four fixed poses (up, down, happy, angry) or a test sweep.
  - `Mouth.py`: a test stub.
  - `HeadControlUI.py`: a PySide6 button panel sending pose names.
  - No lip sync, gaze tracking or blending. Worth keeping: only the limit numbers (already in the repo copies `eyes_mouthboard.py:34-41`, `brows_mouthboard.py:49-54`).
  - `cad/params.py:159-160` cites a `Code/NewFaceFollower.py` as the source of the eye limits. It is **not** in the repo.
- **Lars's TalkingHead.py** (outside the repo):
  - per-character ElevenLabs alignment, turned into phonemes and then visemes (m/b/p closed, f/v lower lip tucked, s/t upper lip lifted);
  - 30 FPS frames;
  - `SERVO_LEAD` 0.06 s;
  - a `CogleyHead` class for this board program.
  - It is the obvious upgrade for the speech layer if the voice can get timestamps (§1).

## 6. Conflicts and constraints

- **Mouth corners and lips: speech against emotion.** mouth.py already adds width from brightness plus |mood| × (smile or frown − narrow) on the same four corner servos (`mouth.py:260-264, 288-289`). It is symmetric, Cogley's smile and frown move only the upper corners (`57-59`), and it is set only at piece start. CHARACTER §6 wants an asymmetric smile (skepticism, amusement), tighter lips (irritation) and parted lips (curiosity, confusion) (`CHARACTER.md:386-407, 409-413`). Resolve it in one place: corner = neutral + speech offset + emotion offset per side, then one clamp.
- **Jaw.** Speech owns it, but surprise wants a brief opening (`CHARACTER.md:418`), and confusion and curiosity want it slightly parted. Use an additive bias under the speech envelope.
- **Lids.** Three things want them: blink closure, gaze lid-follow and emotion narrowing or widening (skeptical, irritated, amused squint against surprised, excited, curious). `eye_anim` has the right structure (openness × (1 − closure)) and needs one external openness input.
- **Gaze.** Four things want it: random idle, the vision target, Thinking aversion ("gaze shifts away", `CHARACTER.md:400`; "eyes drift off", `README.md:44`) and confusion's alternating glances. Give it one priority stack.
- **Board 1 does things on its own.** REST at boot (`cogley_mouth_main.py:322-323`); `talk` chatter if commanded; glide at `SPEED`, which starts at 90 deg/s after any reset (too slow, so re-send `speed` after a reconnect or soft reset); limit clamps narrower than the PC's for some angles. Board 2 does nothing on its own.
  - Never flash Cogley's `eyes_mouthboard.py` / `brows_mouthboard.py` on Board 2: they move by themselves and don't understand `<pin> <deg>`.
  - Never run `cogley_mouth_main.py` on Board 2: its `set` clamps to mouth limits (CUR 75..105 against lid poses around 183), and it would answer "Unknown command" to the forwarded `8 107` lines.
- **Brown-outs, USB drops and power.**
  - The Pico dropped off USB twice while servos moved (`BUILD_LOG.md:114`, "check the XT60 5 V").
  - Without the BOARD POWER jumper a Pico runs on USB power only, so Board 2 dies off USB (`firmware/README.md:62-68`, `BUILD_LOG.md:66`).
  - A lid stalled buzzing past its stop (CLR at 196, `BUILD_LOG.md:203`).
  - The slider window threw a SerialException after the USB was pulled (`BUILD_LOG.md:462`).
  - The engine needs: staggered power-up (mouth.py 120 ms per servo, `mouth.py:221`; the slider 150 ms, `servo_controls.py:292`); per-joint speed limits (Board 2 has no glide, so a 6-servo saccade starts every motor at once); poses kept inside SHUT/OPEN; reconnect with re-detection, `speed`, re-init and a staggered resend (the Mac port name can change on re-enumeration); and safe positions on exit (CHARACTER §11, `CHARACTER.md:889-890`).
- **Faulty or unknown hardware.**
  - TON: no servo (`mouth.py:90`).
  - The JL brow servo (Board 2 GP4, the viewer's-left outer brow) turned far less than JR and not at all from 90 towards 0 on 2026-10-26 (`BUILD_LOG.md:466-478`). Its replacement is not recorded, and on 2026-10-29 it "may still be the weak one" (`126`).
  - CUL lid (Board 2 GP10) found dead on 2026-10-30 and being replaced; its SHUT and OPEN must be re-saved (`BUILD_LOG.md:38`). The current `eye_poses.json` values may or may not be the new servo's.
  - Unverified: brow `DIR`, brow LEVEL, `UD_UP`, the LR sign and gain, the mouth poses, the mouth L/R sides, and `camera.json`.
  - The engine should carry an `enabled` flag per joint.
- **The serial port has a single owner.** Frank with `--mouth`, the slider windows and `share_port.py` exclude each other. `share_port` is POSIX-only. Today the mouth exists only when the voice loaded (`chat.py:790`), so a muted run has no face.
- **Platform.**
  - The team runs on the Mac: `start.sh` uses zsh, `uv run --no-project`, `/dev/cu.usbmodem*`, AVFoundation and the camera permission (`README.md:174`); the Homebrew and venv Pythons have no tkinter (`firmware/README.md:35`).
  - This repo also lives on Windows (COM9 defaults, `servo_controls.py:35`, `mouth_controls.py:31`).
  - The engine should be pure Python (numpy, pyserial, threading, `time.monotonic`), with no tkinter and no openpty. `find_port` already handles both platforms (`mouth.py:97-111`).
- **Doc drift noticed along the way:**
  - `firmware/README.md:37` (top lids only) against `eye_anim.py:26`;
  - `firmware/README.md:53` (Board 1 RP2040) against `BUILD_LOG.md:64` (Pico 2);
  - `frank/README.md:217` ("[chuckle] not voiced") against `voice.py:322-323` (it is voiced on v3).

## 7. Recommendation

**The seam.** A new `frank/face.py` (a FaceEngine) owns the serial port and every joint, and `mouth.py` becomes its speech layer.
- **Rig.**
  - Port open, detection, `speed`, lock, reconnect.
  - Board 1 through `set <NAME> <deg>` and `jaw <f>`; Board 2 through `e <pin> <deg>`.
  - One joints table named by character side, holding socket, board, neutral, min and max, gathered from `eye_poses.json`, `mouth_poses.json` / `cogley_neutral` and the board limits.
  - One output thread at 50 Hz with send-on-change, a 1° deadband and per-joint speed limits.
- **Inputs.**
  - `voice.mouth = engine` (implement `feed`, `face` and `flush`; no change to voice.py beyond the §0 fix);
  - `chat.listeners.append(engine.on_ui)` for the dialogue events;
  - poll `chat.eyes.state` and `chat.ears` each tick;
  - the few new `ui()` calls from §2.
- **Layers, in normalised units.** Gaze plus blinks (EyeAnim, refactored to take a target), brows (BrowAnim with blend weights), lids (openness), corners (speech plus emotion per side) and speech (mouth.py's math with the serial code removed).
- Attach the engine independently of the voice, so a `--mute` run still has a face.

**The smallest visible first step** (no firmware change, on the proven link path): in `chat.py` / `web.py` `main()`, after the Mouth is created, start a 50 Hz thread that:
- runs `EyeAnim(**eye_poses)` and `BrowAnim(level, …, idle=True)`;
- sends each changed, rounded angle as `mouth.link(f"{mouth.PIN[socket]} {angle}")`;
- adds a listener that calls `brows.play(tag)` on `ui("face")`.

About 40 lines. Frank then blinks, looks around and moves his brows with every tag while he talks; this is the 2026-10-29 "Next" (`BUILD_LOG.md:74`).

Before it runs:
1. Fix `voice.py:358`.
2. Fit the BOARD POWER jumpers.
3. Press "curious" once in `servo_controls.py --link` to check `brow_anim.DIR`, and save brows LEVEL.
4. Re-save CUL's SHUT and OPEN on the new servo.
5. Keep the JL brow's travel low, or disable it, if it is still the weak servo.

Step 2 is gaze to the speaker from `eyes.state`. It needs the LR sign, `UD_UP` and the gain measured with the slider window (about 5 minutes), and the measured `camera.json` offset. Step 3 is the orchestrator's states and the per-side corner mood.

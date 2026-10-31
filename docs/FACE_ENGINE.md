# Frank's face performance engine (v1)

Plan and interface contract, 2026-10-30, built for NightHack (Founders Inc., San Francisco) the same evening. The research behind it is [reports/Robot face emotion animation.md](../reports/Robot%20face%20emotion%20animation.md); its section "Frank's engine" is the long version of this page and holds the sources for every number below. The character is [CHARACTER.md](CHARACTER.md) §6 and §11; the conversation software is [frank/README.md](../frank/README.md).

## What it does

Claude decides what Frank feels (the expression tags in his replies). The engine decides how and when his face shows it, and moves every eye, lid and brow servo, plus the emotion part of the mouth, 50 times a second. Claude never touches a servo.

Three parts, one job each:

- **Orchestrator** (`frank/engine/orchestrator.py`), the stage manager. Knows what is happening (someone arrived, they are talking, Frank is thinking, speaking, was cut off) and fires each tag when its words reach the speaker, not when it is parsed. Picks who to look at from the vision. Enforces "not everything at once" and "no flip-flopping".
- **Synthesiser** (`frank/engine/synth.py`), the inner state. A slow mood (a point in pleasure, arousal, dominance space, resting at Frank's dry, slightly disdainful home) and ten transient weights, one per tag, each rising and fading on its own envelope. Turns the mixture into a target face, blended region by region. Emotion is a continuous spectrum: a face is always a weighted mix, never one switched pose.
- **Animator** (`frank/engine/animator.py`), the puppeteer's hands. Adds blinks, saccades, gaze aversion, idle drift and speech beats to the synthesiser's face, then smooths every channel with a critically damped spring and a speed cap. `frank/engine/rig.py` turns the result into servo angles inside the saved poses and sends them.

`frank/mouth.py` stays the speech layer: it still owns the jaw and lips from the audio. The engine gives it the emotion part of the corners (smile, one-sided smile) and a jaw floor (surprise). Everything is standard-library Python, so it runs on the Mac, on Windows and in the preview without the head.

## Files

| File | Owner | What |
|---|---|---|
| `frank/engine/__init__.py` | orchestrator | `from engine import Engine` |
| `frank/engine/channels.py` | contract | channel names, ranges, rest values (below) |
| `frank/engine/synth.py` | synthesiser | `Synth`: mood, transients, personality, face target |
| `frank/engine/animator.py` | animator | `Animator`: layers, blinks, gaze, springs |
| `frank/engine/rig.py`, `rig.json` | animator | `Rig`: channels to servo angles, the one writer |
| `frank/engine/orchestrator.py` | orchestrator | `Engine`: the 50 Hz thread, states, tag timing, chat and vision hooks |
| `frank/engine/preview.py`, `preview.html` | preview | a local page that draws the face live from the channels, with buttons for every tag and state; runs with no head and no API keys |
| `frank/engine/tests/` | each | offline tests, `python frank/engine/tests/test_<part>.py` |

## Frame and channels

Sides are the character's own (project rule): L is Frank's left (+x). Gaze follows `eyes.py`: yaw + to his left, pitch + up, in degrees from the midpoint between his eyes.

**Joint channels** (the animator's output, the rig's input). All normalised; the rig owns the degrees.

| Channel | Range | Rest | Meaning |
|---|---|---|---|
| `gaze_x` | −1..1 | 0 | eyes left/right; +1 = fully to his left (`eye_anim.LOOK_LR` = 30° of servo travel) |
| `gaze_y` | −1..1 | 0 | eyes up/down; +1 = fully up (`LOOK_UD` = 15°) |
| `lid_top_L`, `lid_top_R` | 0..1 | 0.85 | upper lid openness: 0 = the saved SHUT pose, 1 = the saved OPEN pose |
| `lid_bot_L`, `lid_bot_R` | 0..1 | 1.0 | lower lid openness: 1 = the saved OPEN pose (down), lower = raised (squint) |
| `brow_in_L`, `brow_out_L`, `brow_in_R`, `brow_out_R` | −1..1 | 0 | brow ends: +1 raised by RAISE (35°), −1 lowered by LOWER (20°), as `brow_anim.py` |
| `smile` | −1..1 | 0 | mouth corners: + smile, − frown (to `mouth.py`) |
| `smile_asym` | −1..1 | 0 | one-sided: + his left corner more, − his right corner more |
| `jaw_floor` | 0..1 | 0 | jaw opened at least this much (surprise); speech can open it more |

**Face target** (the synthesiser's output, the animator's input): the same brow, `smile`, `smile_asym` and `jaw_floor` channels, plus

| Key | Range | Meaning |
|---|---|---|
| `lid_open` | −1..1 | upper lids: + wider (towards OPEN), − heavier (towards SHUT), 0 = rest |
| `lid_squint` | 0..1 | lower lids raised |
| `lid_asym` | −1..1 | + his left eye narrower than his right (skeptical) |
| `gaze_bias_x`, `gaze_bias_y` | −1..1 | where the feeling pulls the eyes (concentrating: away and up) |
| `gaze_steady` | 0..1 | fewer, smaller saccades (skeptical, irritated, curious) |
| `gaze_avert` | 0..1 | more and longer looks away (vulnerable, concentrating) |
| `gaze_alternate` | 0..1 | brief alternating glances (confused) |
| `arousal`, `valence`, `dominance` | −1..1 | the current PAD point: arousal sets speed (shorter spring half-lives, quicker saccades, bigger idle) |
| `weights` | {tag: 0..1} | the current mixture, for the preview and the log |

**Cue** (the orchestrator's per-tick input to the animator):

```python
cue = {
    "state": "idle",        # idle | person | greeting | listening | thinking | speaking | interrupted | farewell
    "target": None,         # (yaw_deg, pitch_deg) of whoever he should look at, or None (look around)
    "others": [],           # [(yaw_deg, pitch_deg), ...] other people in view, for glances
    "talk": 0.0,            # loudness of his own voice now, 0..1 (mouth.Mouth.open)
    "events": [],           # one-shot this tick: "blink", "long_blink", "flinch", "greet", "beat", "phrase_end"
}
```

## Interfaces

```python
# synth.py
TAGS = ("neutral", "curious", "excited", "skeptical", "amused",
        "concentrating", "confused", "irritated", "surprised", "vulnerable")
class Synth:
    def __init__(self, personality: dict | None = None): ...   # PERSONALITY defaults in synth.py
    def feel(self, tag: str, t: float, intensity: float = 1.0) -> None   # unknown tag: ignored
    def nudge(self, t: float, p: float = 0, a: float = 0, d: float = 0) -> None   # events push the mood
    def step(self, t: float) -> dict      # the face target above
    def snapshot(self) -> dict            # {"mood": (p, a, d), "weights": {...}} for the preview/log

# animator.py
class Animator:
    def __init__(self, personality: dict | None = None): ...
    def step(self, t: float, face: dict, cue: dict) -> dict   # joint channels, smoothed

# rig.py
class Rig:
    def __init__(self, writer=None, config: str | None = None): ...   # writer: a mouth.Mouth, or None (preview only)
    def apply(self, joints: dict, t: float) -> dict   # servo angles by socket; sends what changed
    def rest(self) -> None                            # eyes centred, lids at rest, brows level, mouth neutral

# orchestrator.py
class Engine:
    def __init__(self, writer=None, hz: float = 50, log=None): ...
    def start(self) -> "Engine"; def stop(self) -> None
    def state(self, name: str) -> None                # chat loop: listening, thinking, speaking, ...
    def tag(self, name: str, at: float | None = None, intensity: float | None = None) -> None
    def vision(self, state: dict) -> None             # eyes.Eyes.state: who is where, who speaks
    def event(self, name: str) -> None                # "arrived", "left", "moved", "dark", "interrupted", ...
    def snapshot(self) -> dict                        # joints, face, state, mood: for the preview and web.py
```

Times are `time.monotonic()` seconds. The writer is a `mouth.Mouth`: the rig sends the eye-board servos with `writer.link(f"{pin} {angle}")` (`e <pin> <angle>` through the mouth board, PLAN D28) and the corners and jaw floor with `writer.expression(smile, smile_asym, jaw_floor)` (new in `mouth.py`).

## The ten tags

Anchors (P, A, D) and recipes from the research report's table; four anchors are published, six proposed. `brow_anim.py`'s tuned brow fractions are the starting brow poses.

| Tag | Anchor | Face recipe | Attack, overshoot |
|---|---|---|---|
| neutral | (0, 0, 0) | level brows, lids at rest | 0.6 s |
| curious | (0.3, 0.4, 0.0) | brows both up 0.6, lids a little wider, gaze steady on the target | 0.35 s, small |
| excited | (0.62, 0.75, 0.38) | brows fully up, lids wide, smile, faster gaze | 0.2 s, yes |
| skeptical | (−0.25, 0.1, 0.45) | one brow up (out 0.8, in 0.6), the other down (−0.2, −0.4), one lid narrower, steady gaze, one-sided smile | 0.4 s, none, long hold |
| amused | (0.45, 0.25, 0.35) | lower lids up (squint), one brow up, uneven smile | 0.4 s |
| concentrating | (0, 0, 0) | inner brows down 0.5, lids a touch lower, gaze away and up, then back | 0.7 s |
| confused | (−0.2, 0.35, −0.25) | furrow first, then a lift with one brow leading; alternating glances | 0.4 s then 0.3 s |
| irritated | (−0.28, 0.17, 0.04) | brows down 0.8, lids narrowed, frown, slow gaze | 0.8 s, none |
| surprised | (0.40, 0.67, −0.13) | upper lids wide first, then brows to 1.0, brief jaw drop | 0.12 s, then 2 s back |
| vulnerable | (−0.3, 0.1, −0.55) | inner brows up, outer down, lids lower, gaze softer and away | 0.9 s, none |

Blending rules (synthesiser): within each region the active tags mix by weight and neutral takes the remainder; above a weight of 0.3, a tag raising the inner brows and one lowering them never share the brows (the stronger wins: no accidental worry brow); opposing pulls on one channel resolve by the larger magnitude, not the sum (no blank mouth); asymmetry is a separate signed term added after the blend (it survives mixing). Frank's favoured side: his left brow is the skeptic's brow.

## The states

From the report's state table. Profiles set gaze behaviour, blink rate, idle size and how much expression is allowed.

| State | Entered when | Gaze | Blinks |
|---|---|---|---|
| idle | nobody engaged | look-around fixations, slower with boredom | ~17/min |
| person | an arrival | a glance at them | gaze-evoked |
| greeting | he engages them | on their face, eye-eye-nose saccades every 0.1–0.5 s; brows up, eyes wide | blink on the big shift |
| listening | the visitor is talking | mostly on them; away sideways ~1.1 s every ~7 s | after their pauses; a long ~600 ms "got it" blink now and then |
| thinking | their turn ended, Claude is working | up and away ~3.5 s, back as his audio starts | fewer, then a burst on return |
| speaking | his audio plays | on them; away ~2 s every ~5 s at 0.4 size; back for the last of the reply | ~26/min at phrase ends |
| interrupted | barge-in | snap to the speaker, reflex blink, brow flinch | then listening |
| farewell | departure | follow them out, hold | one slow blink |

Rules: a tag holds at least 1.2 s before another replaces it (surprised may cut in); a repeated tag extends the hold and adds 15 % intensity instead of replaying; features start staggered (eyes, lids +0–50 ms, brows +50–150 ms, mouth +100–300 ms; one side leads by 30–80 ms); a tag-only reply holds its face 1.5–3 s with the gaze on the speaker.

## Signal chain per channel

target → soft-limit clamp → critically damped spring (half-life per channel, shorter with arousal) → speed cap → quantise to 0.5° → send if changed by more than 0.5°. Saccades and blink closures skip the spring (a 10° saccade is ~43 ms, one or two ticks). Eyes and lids go out at 50 Hz; brows at 25 Hz (the link UART is 115200 baud and carries every eye-board line).

## Running it

The engine starts by itself with the chat program; `--no-face` turns it off (the mouth alone, as before).

```
# the whole of Frank, in the browser: the 3D twin, the conversation, and the editor's Face and Engine tabs
uv run --no-project --with anthropic --with openai --with httpx --with sounddevice --with numpy --with scipy --with websockets --with livekit --with opencv-python --with mediapipe --with pyserial python frank/web.py --talk --mouth auto

# the face alone: a page with buttons for every tag, state and event, no API keys
python frank/engine/preview.py                 # drawn only
uv run --no-project --with pyserial --with numpy python frank/engine/preview.py --head   # and on the head

# the tests (no head, no keys)
python frank/engine/tests/test_synth.py
python frank/engine/tests/test_animator.py
python frank/engine/tests/test_rig.py
python frank/engine/tests/test_preview.py
python frank/engine/tests/test_engine.py
```

**The 3D twin as the hero figure** (perform/body.py, the body-twin session, PLAN D32): the twin is the CAD head moved by the very servo lines the engine sends. Start the body server first, then point Frank (or the preview) at its socket. `web.py`'s page shows only the 3D head (with how to start the twin while it isn't running); the preview shows it in place of the 2D sketch, which comes back by itself when the twin isn't running (the online demo has no twin, so the preview keeps its sketch).

```
# on the head: the body server holds the mouth board's port; everything else goes through it
uv run --no-project --with pyserial python perform/body.py robots/frank/robot.json --port /dev/cu.usbmodem2101
# no head: the twin is the body
uv run --no-project --with pyserial python perform/body.py robots/frank/robot.json --sim

uv run --no-project --with pyserial --with numpy python frank/engine/preview.py --head socket://127.0.0.1:8811   # http://127.0.0.1:8820
uv run ... python frank/web.py --talk --mouth socket://127.0.0.1:8811                                             # http://127.0.0.1:8800
```

**The editor, live on the session:** `chat.py` and `web.py` start the editor page with Frank's own engine at http://127.0.0.1:8820 (`--editor-port N` moves it, `0` turns it off), so every bar, the chart and the 3D twin follow the real conversation: the state, the mood, the tag weights, every joint, who is in view, what he hears and says, his tags, and the engine's decisions as they happen (the Live session card). Its buttons still nudge him. Don't run `preview.py` beside it: it wants the same port.

**`web.py`'s page has the editor in it too** (http://127.0.0.1:8800): the 3D twin and his camera on the left, the conversation in the middle, and a side panel with three tabs: *People* (in view, remembered, enrol), *Face* (the emotion map, the tags with keys 1–0, the visitor pad and fake voice, states, events) and *Engine* (state, the last 10 s, mood, tag weights, joints, decisions). The brain, the speaker, the mouth check and the eyes are under *Settings*. The bar at the bottom lists its keys (M mic, V voice, / type, P F E the tabs, 1–0 the tags on the Face tab, C colour, S settings); the twin and the camera show in green until *Colour* is on, and only in colour do the twin's red parts (a servo that can't reach) show. It asks for the editor's routes under `/engine/` (`/engine/meta`, `/engine/snapshot`, `POST /engine/tag` ...), answered by the same `preview.Api` the editor page uses (`chat.face_api`), so the two pages share one visitor pad and fake voice.

**The emotion map** (the editor's first card): pleasure left to right, arousal bottom to top, the ten tags at their map positions (`synth.STEER_MAP`: the anchors, with concentrating moved to calm and focused so the centre stays his plain face) and a dominance slider (skeptical, irritated and vulnerable share a corner and differ in dominance). Drag a point and his face becomes the mix of the tags near it (a Gaussian of the PAD distance, sigma 0.28, through the same region-by-region blending), plus the map's own axes so the calm half reads too (heavier lids when calm, the corners up when pleasant); the mood sits at the point, so arousal also sets how fast he moves. The 3D twin and the real head follow. While steering, Claude's tags wait unseen; *Release* hands the face back. `Engine.steer(p, a, d=None)` and `Engine.release()`; `POST /steer {p, a, d?}` or `{release: true}`.

The twin alone, full screen, is http://127.0.0.1:8810/?hero=1 (`&spin=0` stops its slow sway).

**Before the first run on the head:** in the preview with `--head`, press *curious*: both brows must rise. Then *skeptical*: Frank's own left brow (the one on your right as you face him) goes up. If a brow end goes down, flip its `dir` in `frank/engine/rig.json`; if the wrong side rises, swap the brow sides there. Do the same for the lids (*surprised* opens both; a blink shuts both) and the eyes (drag the visitor to your right on the pad, which is Frank's left: his eyes must follow). Servos marked faulty go in `disabled` in `rig.json`.

## v1 tonight, then later

**v1 (NightHack, 2026-10-30):** all three parts, the eight states, the ten tags with mood and transients, gaze from the vision, blinks, aversion, idle drift, speech brow beats from his loudness, tags timed to the audio (mid-piece tags estimated from the share of the piece played), the preview page, and the face in `web.py`'s page. Offline tests for each part.

**After:** ElevenLabs stream-with-timestamps for exact tag and phrase-end timing; audio-arousal modulation of intensity; the jaw sent early by the measured servo lag; MediaPipe puppeteering to record clips; a Pico-side fallback idle when laptop frames stop; tuning on the head with the skin on.

## Status

| Part | State |
|---|---|
| Contract (this page) | written 2026-10-30 |
| Synthesiser (`synth.py`) | built, `synth OK` |
| Animator and rig (`animator.py`, `rig.py`, `rig.json`) | built, `animator OK`, `rig OK` |
| Preview (`preview.py`, `preview.html`, `face_draw.js`) | built, `preview OK`; port 8820 (8810 is the body twin's) |
| Orchestrator and chat integration | built, `engine OK` (50 Hz end to end with a stand-in mouth board) |
| Live editor (8820 inside `chat.py` / `web.py`), the 3D twin as the hero view, the emotion map | built and pushed 2026-10-30 |
| On the head | not yet: sides and directions to check ([HANDOVER_2026-10-30.md](HANDOVER_2026-10-30.md), step 3) |

The body server and digital twin (`perform/`, another session, 2026-10-30) sit under this without changes: `web.py --mouth socket://127.0.0.1:8811` sends everything the engine and the mouth send through `perform/body.py`, to the board and the twin.

# Animation state machines for Frank's face engine

Research and a recommended design, 2026-10-30. This builds on the notes in `research_notes/Robot face emotion animation/` (the layer stack, springs, blink and gaze numbers, and the split between what the LLM decides and what the engine decides) and answers a narrower question: what kind of state machine should run Frank's face, and how to build it well.

The face controller is still unbuilt. `frank/README.md` ("Still open") leaves it to the creators, and today the face is three separate animators that don't know about each other: `firmware/eye_anim.py` (EYES ALIVE), `firmware/brow_anim.py` (expressions and BROWS ALIVE) and `frank/mouth.py` (the mouth following the voice, with a smile or frown from the tag).

## The short version

- **One big state machine is the classic mistake.** Game studios and Disney both moved away from it. Every new feature multiplies the states: 10 emotions × 9 conversation phases × carried or not × dark or not is already 360 states, and each one needs arrows to the others.
- **Frank needs four kinds of machinery, each doing the job it is good at:**
  1. A **small statechart** (a state machine with nesting and parallel regions) for the things that really are modes: is anyone there, whose turn it is, is he being carried, can he see. About fifteen states in all.
  2. A **blend space** for emotion. Emotions are not states. They mix, fade and have strengths, so the ten tags become ten poses blended by weight.
  3. A **layer stack** (the games' "anim graph") that adds or overrides per face part: rest pose, emotion, what the current state wants, life (blinks, glances, drift), speech, one-shot reactions, blink, safety.
  4. A **per-servo output stage** with springs, so any switch upstream, however sudden, comes out as smooth motion. This is what lets the state machine switch instantly when someone interrupts him.
- **The state machine never sets a servo angle.** It only turns knobs (where to look, how often to blink, how much idle motion, which reactions to fire) and the layers read those knobs. This rule comes from game engines, where gameplay logic sets parameters and the animation graph only reads them, and it is what keeps the whole thing debuggable.

```
 vision events        chat events               voice player
 (eyes.py)            (chat.ui kinds)           (tag + audio slices at playback time)
     │                    │                          │
     └──────────► INBOX: one queue, drained at the start of every 20 ms tick ◄──┘
                          │
                          ▼
   STATECHART  (who's there, whose turn, carried?, dark?)  ──► knobs + one-shot reactions
                          │
        ┌─────────────────┼─────────────────────┬──────────────────────┐
        ▼                 ▼                     ▼                      ▼
   EMOTION blend     ATTENTION             LIFE generators         SPEECH
   (tags → weights)  (who to look at)      (blink, saccades,       (audio → jaw, lips,
                                            drift, idle glances)    corners, brow beats)
        └─────────────────┴──────────┬──────────┴──────────────────────┘
                                     ▼
                LAYER STACK per face part: rest → emotion → state → life →
                speech → one-shots → blink → safety
                                     ▼
                OUTPUT: calibrate → spring → limits → whole degrees → send changes
                        → Board 1 (mouth)  /  Board 2 via "e …" (eyes, lids, brows)
```

---

## 1. What "animation state machine" means, in games and in animatronics

### 1.1 Flat state machines

The textbook version: each state plays a clip or holds a pose, and arrows between states carry conditions ("speed > 0.1", "Jump pressed"). Unity's Animator and the state machines in Unreal's Anim Blueprints both start here. Common extras:

- **Blend duration** on each arrow: the old and new clips are cross-faded for that long.
- **Exit time:** the arrow can only fire once the clip has played to a given point.
- **Any State:** an arrow that leaves from every state, for things like "got hit".

On paper Frank's conversation fits a flat machine: Idle → Listening → Thinking → Speaking → Listening. The trouble starts when the second and third concerns arrive (section 2).

### 1.2 Hierarchical state machines and statecharts

David Harel's statecharts (1987) added three things to the flat machine, and they are the three that matter for Frank:

- **Nesting.** States live inside superstates, and an arrow on the superstate applies to every child. "Anything inside Engaged → on `session_end` → Farewell" is one arrow instead of five.
- **Parallel (orthogonal) regions.** Independent concerns run side by side in their own regions, so their states add up instead of multiplying. "Carried or not" lives in its own two-state region instead of doubling every conversation state.
- **History.** Re-entering a superstate can resume the child that was active when it was left.

Statecharts also give entry and exit actions and a clear rule for event handling (each event is processed to completion before the next one starts). The W3C standardised them as SCXML in 2015. Games have pieces of this: Unity's sub-state machines give nesting, and Unreal's StateTree (UE5) is "a general-purpose hierarchical state machine that combines the Selectors from behavior trees with States and Transitions from state machines".

### 1.3 Layers and masks

A game character is not in one state. The legs run, the upper body aims, the face talks. Engines handle this with **layers**:

- Unity: each Animator layer runs its own state machine, with a weight, a blend mode (**Override** or **Additive**) and an **Avatar Mask** that says which bones it may touch. Sync layers reuse another layer's states with different clips.
- Unreal: montages play in named **slots**, and **Layered Blend per Bone** applies a branch from a chosen bone downwards.

For Frank, face parts play the role of bones: gaze, top lids, bottom lids, brows, jaw, lips, corners.

### 1.4 Blend trees and blend spaces

When states differ by amount rather than by kind, the answer is a parameter, not more states. Walk, jog and run become one blend tree driven by speed. Unity has 1D, 2D and "Direct" blend trees (Direct sets each clip's weight from its own parameter); Unreal has blend spaces.

Robot faces got there first. Kismet (MIT, late 1990s) placed its emotion as a point in an affect space and blended nine basis poses by distance, which is a blend space in all but name. This is the right model for Frank's ten tags.

### 1.5 One-shots: montages and slots

A reload, a hit reaction or a wave is played as a **montage** in a slot: it takes over the parts it needs, plays once and hands back to the graph underneath. Frank's equivalents are the chuckle, the startle when interrupted, the eyebrow flash on recognising someone and the greeting.

### 1.6 Transitions: cross-fade or inertialization

A cross-fade keeps the old state running alongside the new one for the blend time. Interrupting a cross-fade halfway (a third state arrives mid-blend) is where a lot of game animation bugs live; Unity has a whole "Interruption Source" setting for which arrows may cut in, and Any State arrows bypass it.

**Inertialization** (David Bollo, Gears of War 4, GDC 2018) switches to the new state at once, records the offset between where the pose was and where the new state wants it, and decays that offset to zero over a short time. Nothing has to run twice, and interruptions are free because there is no blend in progress to interrupt. Daniel Holden's spring articles turn it into a few lines of maths.

For servos it falls out naturally: run each channel through a critically damped spring and every switch upstream becomes a smooth, interruptible move.

### 1.7 Decision layers: behaviour trees, utility, StateTree

These decide *what* to do, and the animation system decides *how it moves*.

- **Behaviour trees** (popularised by Damian Isla's Halo 2 talk, GDC 2005) re-evaluate a priority-ordered tree every tick and fall back down the list: "look at the speaker; else at whoever is nearest and engaged; else look around".
- **Utility AI** scores every option and picks the best. Disney's 2020 gaze figure does this for attention: each person gets a curiosity score (movement, distance) times a habituation factor that drops while the figure looks at them, and the figure glances or engages above two thresholds.
- **StateTree** (UE5) mixes the two: a hierarchical state machine whose children are chosen like a behaviour tree.

### 1.8 Data-driven selection

Recent Unreal (the 5.4 Game Animation Sample) replaces much of the hand-built locomotion graph with **motion matching** (search a large mocap database for the best next pose) and **chooser tables** (pick a clip by looking up the current context in a table). Frank has no mocap library, so motion matching is out, but chooser tables are a good idea for variety: "Thinking + concentrating → pick one of six glance-away clips, never the last one used".

### 1.9 The animatronic tradition: timelines

Theme-park figures run **timelines**: every servo is keyframed against the soundtrack and played back the same way each show (show control systems, Bottango, Disney's show programming). That is perfect for a fixed show and has no interactivity. Interactive figures put a small state machine over always-on layers. Disney's 2020 gaze bust has a hand-made state machine (Read, Glance, Engage, Acknowledge) over a stack of "subsumption" layers, from L0 zero pose and L1 alive (breathing, blinks, saccades) up to L5 acknowledge (a nod overlaid on engage). Frank is fully interactive, so timelines survive only as authored clips inside the engine (the greeting, the confused brow, the chuckle).

### 1.10 Which family does which job for Frank

| Family | Good at | Bad at | Use in Frank |
|---|---|---|---|
| Flat state machine | a few clear modes | grows as N × M; arrows everywhere | only for tiny local machines: one blink, one saccade |
| Statechart (nesting, parallel regions) | many modes with shared exits; independent concerns side by side | continuous things like emotion | **yes**: Social, Body, Senses and Puppet regions |
| Layers with masks | many things moving at once on different parts | deciding anything | **yes**: the compositor |
| Blend space | mixes, strengths, fading | discrete events | **yes**: emotion |
| One-shot slots (montages) | reactions on top of whatever is going on | long behaviours | **yes**: startle, flash, chuckle, greeting |
| Inertialization / springs | instant, interruptible switches | authored overshoot (do that in clips) | **yes**: every servo channel |
| Behaviour tree | prioritised fallbacks | holding a mode, reacting mid-action | later, if idle behaviour grows |
| Utility scoring | choosing among competing targets | modes | **yes**: who to look at |
| Timeline playback | exact, repeatable shows | interaction | authored clips only |
| Motion matching / choosers | huge data sets | needs data | chooser tables for variants |

---

## 2. What goes wrong, and what it would look like on Frank

| Pitfall | In games | On Frank | The fix in this design |
|---|---|---|---|
| **State explosion** | "Crouch-walk-aim-reload" states | Speaking-amused-carried, Speaking-amused-dark, ... (360 states) | Parallel regions for independent concerns; emotion as a blend, never as states |
| **Arrow spaghetti** | Any State arrows with hidden priorities | Barge-in, session end and "picked up" each needing arrows from every state | Nesting: one arrow on the superstate; explicit region priorities |
| **Waiting on the animation** | Exit time holds a transition until the clip finishes | The visitor interrupts and the face finishes its "surprised" keyframes before reacting | Nothing in the statechart waits on motion. Clips are layers, and the spring absorbs any switch |
| **Interrupted blends pop** | A third transition arrives mid-cross-fade | Interrupted arrives 100 ms after Speaking started | Inertialization: there is no blend to interrupt |
| **Two sources of truth** | Gameplay and anim graph disagree whether the character is grounded | `chat.py` thinks he's done speaking while audio is still playing, or the other way round | One event stream. The face only listens; Speaking is driven by the audio actually playing |
| **Event races** | A trigger set and consumed on different frames | `audio_done` and `barge` in the same 20 ms | All events go into one queue, drained in order at the start of each tick, each processed to completion |
| **Frozen in a waiting state** | Idle that doesn't idle | Thinking for 2.4 s (Opus's median first sentence) with a dead face, which reads as a crash | Every state keeps the life layers running, and every waiting state has a timeout and a "still waiting" behaviour |
| **Identical loops** | The same idle fidget every 8 s | The same glance pattern all night at the hackathon | Random intervals from skewed distributions, chooser tables with no-repeat, randomised amplitudes |
| **Everything at once** | Whole-body pose snaps on state entry | CHARACTER.md §6: "should not perform every movement at once" | State entry schedules each part with an offset: eyes first, lids and brows 50–150 ms later, mouth last |

---

## 3. What the engine has to handle

**Channels** (19 servos, tongue off). The engine should work in the same normalised units the current code already uses, and only turn them into degrees at the output:

| Group | Servos | Unit in the engine | Calibration it maps through |
|---|---|---|---|
| Gaze | LR, UD (Board 2) | degrees of eye turn, ±30 LR, ±15 UD (`eye_anim.LOOK_LR`, `LOOK_UD`) | `eye_poses.json` CENTRE |
| Top lids | 2 (Board 2) | openness 0 = SHUT, 1 = OPEN | `eye_poses.json` SHUT / OPEN |
| Bottom lids | 2 (Board 2) | openness, held for now (`MOVE_BOTTOM_LIDS`) | same |
| Brows | LO, LI, RO, RI (Board 2) | −1 fully lowered … +1 fully raised (`brow_anim`) | LEVEL, Raise / Lower deg, `DIR` |
| Jaw | JL, JR (Board 1) | 0 closed … 1 OPEN pose | `mouth_poses.json` |
| Lips | 4 (Board 1) | parting 0 … 1, or the vowel blend | `mouth_poses.json` lips_rest / up / down, vowels |
| Corners | 4 (Board 1) | width 0 … 1 and mood −1 (frown) … +1 (smile) | narrow / wide / smile / frown |

**Events that exist today** (nothing new has to be sensed to start):

| Source | Today | Engine event |
|---|---|---|
| `eyes.py` `_emit` → `chat.saw` | `arrived`, `left`, `recognised`, `session_end` | `arrived(person)`, `left`, `recognised(name)`, `session_end` |
| same | `moved`, `still`, `dark`, `light` | Body and Senses regions |
| same | `Eyes.state` (everyone's distance, yaw, pitch) | read every tick by Attention |
| `chat.ui(...)` (the listener list web.py already uses) | `hearing` (partial words) | `visitor_talking` |
| same | `visitor` (line released) | `turn_released` |
| same | `ignored` (not said to him) | `background_talk` (optional glance) |
| same | `frank_start` (brain call started) | `reply_started` |
| same | `interrupted` | `barge` |
| same | `frank_end` | `reply_finished(asked=…)` |
| `voice.py` player, which already calls `mouth.face(tag)` at each piece's start and `mouth.feed(pcm)` per 20 ms slice played | tag, audio | `tag(name)` at playback time, `audio_started`, audio slices, `audio_done` |

**Timing facts from the code:** first whole sentence 0.71 s (Haiku) to 2.35 s (Opus), Sonnet 1.50 s; a filler "Hmm." after `FILLER_AFTER` = 1.2 s on 40 % of turns; the voice at about 11 characters a second; jaw attack 35 ms and release 90 ms; the mouth loop already ticks every 20 ms.

**Hardware facts:** Board 2 is reached only through Board 1's one-way UART link at 115200 baud, so nothing confirms that a line arrived. TalkingHead's `cogley_mouth_main.py` glides on the board (`speed 720`), which is a second smoother after anything the laptop does. With `pico_servo_ctl.py` on the board, `mouth.py` lets the jaw servos go after 3 s of silence so they don't hum.

---

## 4. The recommended design

### 4.1 The statechart

```
Frank  (all regions run at once)
├── Social
│   ├── Alone
│   │   └── Idle
│   ├── Noticing ............... max 1.0 s
│   ├── Greeting ............... max 4 s
│   ├── Engaged
│   │   ├── Attending           (someone's there, nobody talking)
│   │   ├── Listening
│   │   ├── Thinking ........... after 6 s: Thinking.Struggling
│   │   ├── Speaking
│   │   └── Interrupted ........ max 0.6 s
│   └── Farewell ............... max 3 s
├── Body:    Settled ⇄ Handled          (moved / still)
├── Senses:  Seeing  ⇄ Blind            (dark / light)
└── Puppet:  Off     ⇄ On               (sliders or web page take over)
```

**Arrows in Social:**

| From | Event | To | Note |
|---|---|---|---|
| Alone.Idle | `arrived` | Noticing | |
| Noticing | after 0.6–1.0 s | Greeting | |
| Greeting | `reply_started` | Engaged.Thinking | his unprompted greeting (README: he studies them 3–4 s, then reacts) |
| Greeting | `visitor_talking` | Engaged.Listening | they spoke first |
| Greeting | after 4 s | Engaged.Attending | |
| Engaged.Attending, Engaged.Listening | `reply_started` | Engaged.Thinking | covers "(no speech)" reactions too |
| Engaged.Attending, Engaged.Thinking | `visitor_talking` | Engaged.Listening | |
| Engaged.Thinking | `audio_started` (reply, not filler) | Engaged.Speaking | the filler's audio moves the mouth through the speech layer, but the state stays Thinking |
| Engaged.Speaking | `barge` | Engaged.Interrupted | `chat.py` already decides what counts as a barge |
| Engaged.Speaking | `audio_done` | Engaged.Attending | with the "expectant" one-shot if he asked a question |
| Engaged.Interrupted | after 0.6 s | Engaged.Listening | |
| Engaged (any child) | `session_end` | Farewell | one arrow, thanks to nesting |
| Farewell | after 3 s | Alone.Idle | |
| Farewell | `arrived` | Noticing | |

A new person arriving mid-conversation is not a state change. It is a one-shot glance (at most every 15 s, as `chat.py` already limits the spoken reaction), so the conversation state is untouched.

**What each state sets** (starting guesses, to be tuned on the head):

| State | Gaze policy | Blinks/min | Life amount | Face bias | Mouth | On entry |
|---|---|---|---|---|---|---|
| Idle | wander: look around, study movement | 17 | 1.0 | mood only | closed | — |
| Noticing | snap to the newcomer, eyes first | gaze-evoked blink | 0.5 | — | closed | small brow flick |
| Greeting | hold on the newcomer, scan face → costume → face | 10 (studying) | 0.4 | greeting clip: brows up, eyes wide, corners up a little | lips part slightly | greeting clip |
| Attending | addressee, with occasional sideways aversions | 17–20 | 0.8 | mood | closed | — |
| Listening | speaker, triangle saccades (their eyes and mouth, 0.1–0.5 s dwell); a sideways aversion every ~7 s for ~1 s | 20 | 0.5 | a listening style per turn (below) | closed or parted | — |
| Thinking | cognitive aversion up and to the side; back on the addressee before his audio starts | 6–10, plus one on each aversion | 0.3 | slight furrow | closed unless a filler plays | aversion |
| Thinking.Struggling | longer, wandering aversions | 10 | 0.5 | concentrating, stronger | closed | — |
| Speaking | addressee, small sideways aversions every ~5 s for ~2 s; mutual gaze for the last ~2 s of a turn | 26, placed at piece boundaries | 0.4 on brows, 0 on mouth | tag emotion | speech layer | pre-speech "breath": jaw and lips part 100–150 ms before the first sound |
| Interrupted | snap to the interrupter | one fast blink | 0 | surprised at 0.4 | shut fast | startle |
| Farewell | follow where the leaver went, then drift | 17 | 0.8 | per CHARACTER.md "Farewells" | closed | — |
| Handled (Body) | fast, wide searching saccades | 25 | 1.0 | alarmed: brows up, eyes wide | slightly open | — |
| Blind (Senses) | slow searching | 10 | 0.6 | lids at 0.6, worried brows | closed | — |

The aversion and blink figures come from Andrist et al. 2014 and Bentivoglio et al. 1997, as summarised in `animation_craft.md` §3–4.

**Region priority.** When regions disagree about a knob, the higher one wins: Puppet > Body.Handled > Senses.Blind > Social. Each region returns its knobs, and the engine takes each knob from the highest region that sets it. This is Disney's subsumption idea in its simplest form.

**History.** Frank barely needs it, because Body and Senses run beside Social instead of interrupting it. It becomes useful if being carried ever pauses the conversation: Social would leave Engaged, and on `still` the history state would resume Listening or Attending, whichever was active.

**Listening needs a signal.** CHARACTER.md asks for listening that varies with what he hears, but the LLM gives no tags while the visitor talks. Three cheap sources, in order of effort:

1. A **listening style picked per turn** from a chooser table (attentive, intrigued, skeptical squint), biased by his current mood and never the same twice running.
2. **The visitor's own face:** MediaPipe's landmarker already runs on their mouth (`jawOpen`), and its blendshapes include smiles, so a visitor smiling for a second can tip him a little towards amused.
3. **The visitor's voice:** a brow lift or long blink when their pitch drops late in a phrase (Ward's backchannel cue), at most once every 3–5 s.

### 4.2 Emotion: a blend space, not states

Each tag is a **pose** over the expressive channels (brows ×4, top-lid openness offset, bottom lids, corner mood, jaw parting, eye widening) plus a few **style knobs** that change how other layers behave:

| Style knob | Example |
|---|---|
| gaze speed and saccade rate | excited: faster gaze changes; irritated: steady, deliberate gaze |
| blink rate multiplier | concentrating: fewer; surprised: one hard blink then few |
| mouth gain | excited: bigger mouth; vulnerable: smaller ("reduced mouth exaggeration") |
| life amount | irritated: less fidgeting ("controlled, deliberate") |

The starting poses already exist: `brow_anim.EXPRESSIONS` for the brows and `mouth.MOOD` for the corners. Store them as data so they can be tuned with the slider windows ("SAVE as curious").

**Two speeds.** The face is a weighted blend of the neutral pose, a slow **mood** and a fast **transient**:

```
face = neutral + Σ w_mood(e) · (pose(e) − neutral) + Σ w_transient(e) · (pose(e) − neutral)
```

- **Transient:** each tag starts an envelope: attack (per emotion: surprised 0.12 s, irritated 0.8 s, roughly the move times already in `brow_anim`), hold (at least 1.2 s), then decay towards the mood with a half-life of 3–6 s.
- **Mood:** a leaky average of recent tags, half-life about 45 s, capped at about 35 % weight. After a run of amused replies he stays a little amused; one irritated tag doesn't make him sulk for a minute.
- **Weights are normalised** so the transient weights sum to at most 1. Two strong tags in quick succession blend instead of stacking past the servo limits.
- **Blend in pose space**, not in a valence-arousal space. Interpolating between two emotions in an affect space can pass through a third, wrong emotion on the way (Ribeiro & Paiva 2012).

**Rules against flip-flopping:**

- A new tag within the 1.2 s hold doesn't replace the old one; both get weight.
- The same tag again re-accents (a small extra pulse) instead of restarting.
- An optional intensity in the tag (for example `[amused:2]`, 1–3) scales the pose's offset from neutral, multiplied by one global **theatricality gain** (CHARACTER.md: "very theatrical").

**Shaped emotions are clips.** Confused (furrow, then a questioning lift) and surprised (sharp lift, then a slow return) have a shape in time. Play them as one-shot clips (4.6) whose last frame is the sustained pose, so the blend takes over without a seam. `brow_anim` already writes them as keyframes.

**Timing against the audio.** Tags arrive in the text stream before the audio they belong to, and `voice.py` applies each piece's tag when that piece starts playing. The engine should start the transient about 100–200 ms *before* the piece's first sound. That is possible because the next piece is queued before it plays. On Ameca, expressions that came after the speech were judged "not correctly timed" (Mindtrek '25). A reply that is only tags (he stays silent and makes the face) applies at once.

### 4.3 Attention: who to look at

The state sets the **gaze policy** (wander, target, avert, search). **Attention** picks the target, from `Eyes.state`:

- Every visible person gets a score: engaged (within 2 m and facing him), currently speaking (mouth activity), being answered, distance, how recently they arrived, and a habituation term that falls while he looks at them and recovers when he doesn't (Disney's curiosity score).
- **Hysteresis:** switch target only when a new score beats the current one by about 30 % and the current target has been held for at least 0.8 s, or else his eyes flick between two people standing together.
- **While speaking, look at the person being answered.** Looking at one person while replying to another confused people in a multi-party Furhat study (Abbo et al. 2025).
- Turn each target into eye angles from the camera's position relative to his eyes (`camera.json`) and clamp to ±30° / ±15°. Frank has no neck, so a target outside that range leaves the eyes at the edge, which reads as side-eye. That suits the character.
- **Background talk** that `chat.py` ignored can earn a brief glance towards the noise (if a face is there) and back. He shows he heard without answering.

### 4.4 The layer stack

Each layer writes values for the channels it cares about, each with a **mode** and a **weight**. They are applied in this order every tick:

| # | Layer | Mode | Notes |
|---|---|---|---|
| 0 | Rest | set | the saved neutral pose: lids at `LID_REST`, brows LEVEL, mouth closed |
| 1 | Emotion | override by weight | mood + transient blend (4.2) |
| 2 | State behaviour | override (gaze) / add (face bias) | gaze target from policy and Attention; the state's face bias (slight furrow in Thinking) |
| 3 | Life | add, scaled by the state's life amount | saccades and microsaccades on gaze, noise drift on brows and corners, idle glances |
| 4 | Speech | jaw: max; lips and corners: override, faded in and out over 100–200 ms; brows: add | from the audio, as `mouth.py` does now, plus brow beats on stressed peaks |
| 5 | One-shots | per clip: add or override | startle, flash, greeting, chuckle, expectant; one slot per face part |
| 6 | Blink | multiply (lid openness × (1 − closure)) | always wins on the top lids |
| 7 | Safety | clamp and couple | lid limits that depend on gaze, limits from the pose sweep, Puppet overrides last |

**Rules per channel:**

- **Gaze:** the highest layer that sets a target owns it (override, never add), plus the Life layer's saccade offsets. No heavy smoothing; see 4.7.
- **Top lids:** `openness = clamp(emotion + state + gaze_follow(UD)) × (1 − blink)`. The lids rise when the eyes look up and drop when they look down, as `eye_anim.LID_FOLLOW_TOP` already does.
- **Brows:** emotion + clip deltas + speech beats + drift, all added, then clamped to −1 … +1 and never past the Raise / Lower degrees.
- **Jaw:** while he talks, speech wins (the larger of the speech and emotion openings), so surprise can still drop the jaw in a pause.
- **Corners:** the speech width plus the mood offset, as in `mouth.py` today.

`mouth.py`'s present logic is already a small two-layer compositor (speech for the jaw and lips, mood for the corners). It becomes layer 4, and its serial code moves to the output stage.

### 4.5 Small local machines: blink, saccade, idle

Flat state machines are the right tool here, because each one is small and self-contained.

**Blink:**

```
Open ──(timer | gaze shift > 15° | phrase boundary | reflex)──► Closing ~70 ms
Closing ──► Closed ~40 ms ──► Opening ~180 ms (ease-out) ──► Open
```

- Intervals come from a skewed random distribution with the state's rate and a minimum gap of about 1 s, never a fixed period.
- About 10 % are double blinks and a few are slow (`eye_anim.SLOW_BLINK`).
- The event triggers reset the timer.
- Always close fully: half blinks look wrong (Trutoiu et al. 2011).
- On `light` after Blind, two quick blinks.

**Saccade:** `Fixate (dwell) → Jump → Fixate`.

- The dwell depends on the policy: 0.1–0.5 s across a face when engaged (Disney's triangle between the eyes and nose, which also hides that Frank's eyes are linked and can't converge), 0.5–3 s when wandering.
- Jumps are commanded in one step and the servo slews at full speed. At 50 Hz a 15° saccade lasts only a frame or two.
- Microsaccades of 1° (a smaller step may fall inside the servo deadband).
- A big jump asks the Blink machine for a gaze-evoked blink.

**Idle selector:** a chooser table of idle actions (glance at movement, look up as if contemplating, squint at something, one-brow twitch, settle), each with a weight and a cooldown, never repeating the last one. The weights shift with how long he's been alone.

### 4.6 One-shot clips

A clip is a short authored motion on a few channels, written as keyframes `(time, channel, value, ease)`, with random ranges on the numbers so no two plays are identical. Disney's "show objects" combine clips by grouping (run together), sequencing, looping, random selection, adding, scaling and subtracting. Python generators that yield channel values each tick do all of these in a few lines.

Each face part has one **slot**. A new clip takes a slot if its priority is the same or higher; the old one is dropped, and the spring smooths the switch. When a clip ends, its slot goes quiet and the layers below show through. Every clip has a cooldown so a twitchy event can't machine-gun it.

The first clips: greeting, recognised-flash, startle (Interrupted), expectant (after he asks a question: brows up a little, steady gaze), chuckle (the face part of `[chuckle]`), confused and surprised shapes, reorient (looking around after being set down somewhere new).

### 4.7 Transitions: springs instead of cross-fades

Every channel ends in a **critically damped spring** (Holden's `critical_spring_damper_exact`) with its own half-life. Any jump in the composed target, from a state switch, a new tag or a clip being cut, becomes a smooth, interruptible move with continuous speed. That is inertialization done per servo.

| Channel | Smoothing | Why |
|---|---|---|
| Eyes, saccades | none: step, let the servo slew | a real saccade is 40–90 ms; the MG90S (0.1 s per 60°) is about the same speed |
| Eyes, slow theatrical glances | min-jerk curve with a set duration (clips) | deliberate looks should ease |
| Top lids | very short half-life (~20 ms); the blink shape is authored | blinks must be fast |
| Brows | 60–120 ms | the signature feature: lively, not twitchy |
| Corners, lips | 80–120 ms | |
| Jaw while speaking | attack 35 ms, release 90 ms (as in `mouth.py`) | intelligibility |

Emotional change is slow because of the weight envelopes (4.2), not because of the springs. Keep the springs short, or everything feels mushy and late.

Anticipation and overshoot are authored into clips (a small dip before a big brow lift), never left to the springs. A critically damped spring never overshoots, by design.

Set the board's own glide fast (`cogley_mouth_main.py` `speed`) so the laptop is the only smoother. Two smoothers in a row add their lags.

### 4.8 The output stage

Per channel, every tick:

1. normalised value → degrees through the saved calibration (`eye_poses.json`, `mouth_poses.json`, brow LEVEL, Raise / Lower, `DIR`);
2. clamp to the soft limit, which sits inside the hard cap found by sweeping the real head (the same idea as the CAD pose sweep: rest, each axis at ± its limit, the combined corners);
3. spring;
4. velocity cap (degrees per second), so no target jump can slam a lid into the skin;
5. round to whole degrees, which is what the board programs take today;
6. send only if changed, and route Board 1 channels directly and Board 2 channels as `e <pin> <angle>`;
7. **resend every channel about once a second**, because the link to Board 2 is one-way and a lost line would otherwise stick until that servo's next change;
8. let servos go when the policy says so (the jaw after 3 s of silence, as now), and on start-up and shutdown move one servo at a time, as `mouth.rest()` does, so they don't all start together on the supply.

**Link budget:** Board 2 has 10 servos. At 50 Hz, with about 9 bytes per `e 8 123\n` line, that is about 4.5 kB/s if every servo changes every tick, against roughly 11.5 kB/s for 115200 baud. Sending only changes keeps it far lower, but measure how fast Board 1's MicroPython loop can forward lines before relying on this.

### 4.9 Threads and clocks

- **One engine thread** ticking at a fixed 50 Hz. Wake at `perf_counter` deadlines rather than `sleep(0.02)`, which drifts (that is how `mouth._run` works now). Pass the measured dt to the springs so a late tick doesn't change speeds.
- **One inbox.** The vision process, the ears, `chat.py` and the voice player all only post events. The engine drains the queue at the start of each tick, in order, and finishes each event before the next. Nothing else touches engine state.
- **One clock.** Convert every event's timestamp (`eyes.py`'s own `t`, `chat.ui`'s wall-clock `t`, the ears' `perf_counter`) to the engine's monotonic clock on arrival. Key the speech layer and tag onsets to audio playback time, as `mouth.feed` does with its `DELAY`.
- **The engine owns the serial port.** Today `Mouth` owns it and `voice.py` calls into it. The engine replaces that thread, and `voice.py` posts to the engine instead.
- **It reports back.** On every state change, and a few times a second otherwise, the engine posts its states, the top emotion weights and the channel values to `chat.listeners`, so the web page can show them and the chat log records them.

---

## 5. Design rules

1. The statechart sets knobs and fires clips. It never writes a servo angle.
2. Emotion is never a state. Anything that has an amount is a parameter.
3. Independent concerns get their own parallel region, not more states.
4. An arrow that leaves every child belongs on the superstate.
5. Nothing in the statechart waits for motion to finish. Motion follows the state; it never holds it.
6. Every transient state has a maximum time and somewhere to go when it runs out.
7. Every waiting state keeps the face alive, with purpose (CHARACTER.md: "avoid arbitrary facial motion during response delays", so Thinking looks like thinking, not random twitching).
8. The face follows what is actually happening: Speaking means audio is playing, not that the brain has replied.
9. All events go through one queue, in order, one at a time.
10. Per channel, one owner per layer; layers combine by declared modes, never by whoever writes last.
11. No fixed periods and no identical repeats: random intervals, chooser tables, randomised clip ranges.
12. Stagger the parts: eyes lead, lids and brows follow 50–150 ms later, the mouth last.
13. Poses, clips, rates and limits are data, tuned on the real head with the slider windows, not constants buried in code.
14. Everything can be replayed offline from a log, without servos.

---

## 6. Building it in Python

**Statechart library.** `python-statemachine` 3.x added full statechart support in February 2026 (3.2.2 now): `State.Compound` for nesting, `State.Parallel` for regions, `HistoryState`, and SCXML event semantics checked against the W3C test cases. That covers exactly the parts that are easy to get wrong by hand. `transitions` (`HierarchicalMachine`, 0.9.3) is the older alternative. A hand-written one is about 150 lines and gives full control over the tick. Recommendation: start with `python-statemachine` 3.x's `StateChart`, and keep timeouts in the engine (each state declares a maximum time; the engine posts `timeout` when it passes) so they run on the engine's own clock. Before adding it, do the dry run the project asks for (`uv pip install --dry-run`); `frank` runs as `uv run --no-project --with …`, so it only joins that list.

**Files** (a suggestion):

```
frank/face/
  engine.py      the 50 Hz loop, inbox, clocks, reporting
  states.py      the statechart and each state's knobs
  emotion.py     tags → weights → pose
  attention.py   who to look at
  layers.py      rest, life (blink, saccade, idle), speech (from mouth.py), one-shots
  output.py      calibration, springs, limits, serial routing to both boards
  face.json      poses per tag, clips, rates, half-lives, limits
```

**The core loop**, to show the shape (not tested code):

```python
TICK = 0.02  # s: 50 Hz

def compose(layers, t, dt, knobs):
    face = dict(REST)  # channel -> value, in engine units
    for layer in layers:  # rest, emotion, state, life, speech, oneshots, blink, safety
        for ch, (mode, value, weight) in layer.update(t, dt, knobs).items():
            if mode == "override":
                face[ch] += (value - face[ch]) * weight
            elif mode == "add":
                face[ch] += value * weight
            elif mode == "multiply":  # blink: openness × (1 − closure)
                face[ch] *= value
            elif mode == "max":       # jaw: whichever opens more
                face[ch] = max(face[ch], value)
    return face

def run(engine):
    next_tick = last = time.perf_counter()
    while engine.alive:
        t = time.perf_counter()
        for ev in engine.inbox.drain():  # every event, in order, before anything moves
            engine.chart.send(ev.name, **ev.data)
        engine.post_timeouts(t)          # states that have run past their maximum time
        knobs = engine.knobs()           # each knob from the highest region that sets it
        face = compose(engine.layers, t, t - last, knobs)
        engine.output.write(face, t, t - last)  # calibrate, spring, limit, send changes
        last = t
        next_tick += TICK
        time.sleep(max(0.0, next_tick - time.perf_counter()))
```

---

## 7. Testing and tools

- **Replay.** The chat logs in `output/frank/chats/` already hold timed `seen`, `voice`, `barge` and `mouth` events. Feed them into the engine on a clock of its own (as `Vision.step` is tested), write every channel and state to a file and plot them. Check automatically:
  - no channel outside its limits;
  - no step larger than its velocity cap;
  - every transient state leaves within its maximum time;
  - lids are never open during a blink;
  - Speaking only while audio plays;
  - no clip plays twice within its cooldown.
- **A face on the web page.** `web.html` can draw a simple 2D face from the channel values, with the active states and the top emotion weights beside it, so everything can be tuned without the head plugged in.
- **Puppet region.** The slider windows or the web page can take over any channel at the top of the stack (Disney applies the joystick last). Useful for the show and for finding limits.
- **A diagram** generated from the statechart, so the docs never drift from the code.
- **The pose sweep on the real head:** rest, each channel at ± its limit, the combined corners (eyes up + lids open + brows up, and so on). Record the first collision, the hard cap and a lower soft limit.

---

## 8. Build order

Each step works on its own before the next starts.

1. **Engine and output stage.** 50 Hz loop, channel model, calibration, springs, limits, serial routing to both boards, resend. Port `eye_anim` and `brow_anim` into it as layers. Done when EYES ALIVE and BROWS ALIVE run together from the laptop through one port.
2. **Speech layer.** Move `mouth.py`'s analysis in; `voice.py` posts slices and tags to the engine. Done when he talks as he does now, through the engine.
3. **Statechart, conversation only.** Idle, Attending, Listening, Thinking, Speaking, Interrupted, from the `chat.ui` events. Done when a replayed session shows the right states at the right times.
4. **Emotion blend.** Tags → transient + mood, onsets against audio playback. Done when all ten tags look right on the head and quick tag changes blend instead of snapping.
5. **Attention and gaze.** Scores from `Eyes.state`, policies per state, triangle saccades, aversions. Done when he looks at the right person in a two-person test.
6. **The rest of the states and clips.** Noticing, Greeting, Farewell, Handled, Blind, the one-shots and chooser tables.
7. **Tools.** The web face, replay checks, puppet mode.
8. **Tune on the head** under the venue lighting, then write the chosen numbers back into `face.json` and the docs.

---

## 9. Open questions

- **Listening signal:** which of the three (chooser table only, the visitor's face, the visitor's voice) is worth building for the event?
- **Tag intensity:** add `[amused:2]`-style intensities to the system prompt, or keep plain tags and let the engine pick strength from context?
- **Audio timing:** whether ElevenLabs v3 streaming gives word timestamps (it would place brow beats and tag onsets exactly) is still unconfirmed.
- **Servo latency:** measure command-to-motion with a slow-motion phone video, then lead the jaw by that much.
- **Brow directions:** `brow_anim.DIR` is still Cogley's and unchecked on the team's build.
- **Bottom lids:** hold them (as now) or use them for squints (amused, skeptical, irritated)?
- **Letting go:** which servos can be released without drifting under the silicone skin?
- **Board 2 link throughput:** how many forwarded lines per second Board 1's loop really handles.

---

## Sources

New in this note:

- Epic Games, StateTree overview — <https://dev.epicgames.com/documentation/en-us/unreal-engine/overview-of-state-tree-in-unreal-engine>
- python-statemachine 3.0.0 release notes (compound, parallel, history, SCXML) — <https://python-statemachine.readthedocs.io/en/latest/releases/3.0.0.html>; project page <https://github.com/fgmacedo/python-statemachine>; PyPI 3.2.2 <https://pypi.org/project/python-statemachine/3.2.2/>
- David Bollo, "Inertialization: High-Performance Animation Transitions in Gears of War", GDC 2018 — <https://www.gdcvault.com/play/1025165/Inertialization>; Daniel Holden on inertialization cost — <https://theorangeduck.com/page/inertialization-transition-cost>
- Unity Manual, Animation transitions (exit time, interruption source) — <https://docs.unity3d.com/ru/2017.4/Manual/class-Transition.html>; the Any State interruption report — <https://discussions.unity.com/t/case-893600-any-state-transitions-to-sub-state-machines-ignore-interruption-source/664860>
- D. Harel, "Statecharts: a visual formalism for complex systems", Science of Computer Programming 8(3), 1987 (general knowledge, not fetched here).

From the earlier notes in `research_notes/Robot face emotion animation/` (their links are there): Pan et al. 2020 (Disney gaze figure, layers and attention engine), Andrist et al. 2014 (gaze aversion), Bentivoglio et al. 1997 and Trutoiu et al. 2011 (blinks), Ribeiro & Paiva 2012 (animation principles, PAD caveat), Holden's "Spring-It-On", the Kismet affect space, the Mindtrek '25 Ameca study (expressions after speech) and Abbo et al. 2025 (gaze–speech mismatch).

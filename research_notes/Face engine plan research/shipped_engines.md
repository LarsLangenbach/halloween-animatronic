# Shipped expressive-character engines: Anki Cozmo/Vector internals, plus Furhat, Engineered Arts, Disney, Reachy Mini, Jibo and aibo (research notes for Frank's face performance engine)

Research date: 2026-10-30. The code was read directly: files fetched raw from GitHub and grepped. Excerpts are short, and numbers are quoted verbatim from source.

**Provenance and licence of the Anki/DDL code (read this first):**
- `digital-dream-labs/vector` is DDL's official "rolling release" of the Vector source. It is only a partial release: it has `animProcess/`, `cannedAnimLib/`, the CLAD types, the docs and part of `engine/`, but no `engine/moodSystem/` and no `resources/config/`. Last push 2022-05-28. Its licence is the "Digital Dream Labs Software Asset License, Version 1.0, Revised 5/25/2021" (GitHub reports it as NOASSERTION). It grants "a non-exclusive, personal License to use the provided Assets or Derivative Works … provided that the Assets and Derivative Works are used with the Covered Products [Vector] and with no other products". Derivative works may be redistributed only if they are "designed for use with, or to accompany, the Covered Products." — [DDL vector repo](https://github.com/digital-dream-labs/vector), [LICENSE](https://github.com/digital-dream-labs/vector/blob/main/LICENSE)
- `kercre123/victor` (branch `snowboy`) holds the full Anki source, with Anki's PRs and commit history. Its README calls this source "the leak" and points to a wiki "for more information about the leak". It is archived (last push 2025-05-25), the project moved to os-vector/wire-os, and the repo has no LICENSE file. The mood system, mood config, emotion events, behaviour cooldowns and `proceduralFaceTypes.clad` quoted below are available only from this repo. — [kercre123/victor](https://github.com/kercre123/victor)
- `digital-dream-labs/vector-animations-raw` (the Maya scenes and animation tools, under the same DDL licence) was last pushed 2021-06-03. — [vector-animations-raw](https://github.com/digital-dream-labs/vector-animations-raw)
- Consequence for Frank: the code is useful as a reference for structure and parameter values. Copying the code or data files into Frank would fall outside the DDL licence, because Frank is not a "Covered Product", and the leaked repo carries no grant at all. Re-implement the ideas; do not paste the files. (This is a licence reading, not legal advice.)

---

## Q1. Vector/Cozmo mood system: dimensions, ranges, decay graphs, emotion events, and how mood selects or modulates animations

### Takeaway
Vector tracks five scalar emotions (Happy, Confident, Social, Stimulated, Trust). They range over −1..1, except Stimulated and Trust, which range over 0..1. Each decays towards 0 along a per-emotion JSON piecewise-linear graph. Named, data-driven "emotion events" bump them, and a per-event repetition-penalty graph scales each bump. Downstream, mood is mostly collapsed into a 4-value "SimpleMood" that filters weighted animation-group entries, and the engine also sends it continuously to audio parameters. Anki's own docs say the mood system ended up far less central than first planned.

### Cited Findings
**Dimensions and ranges**
- `enum uint_8 EmotionType { Happy = 0, Confident, Social, Stimulated, Trust, Count }` (author Mark Wesley, 10/14/15). — [emotionTypes.clad](https://github.com/digital-dream-labs/vector/blob/main/clad/src/clad/types/emotionTypes.clad)
- In `emotion.cpp`: `kEmotionValueMin = -1.0f`, `kEmotionValueDefault = 0.0f`, `kEmotionValueMax = 1.0f`. Each emotion keeps a history ring buffer (`kMaxEmotionHistorySamples` = 128 ticks) that answers "value N ticks / N seconds ago". — [emotion.cpp (leak)](https://github.com/kercre123/victor/blob/snowboy/engine/moodSystem/emotion.cpp)
- `mood_config.json` sets `"valueRanges"`: Stimulated min 0.0 / max 1.0, Trust min 0.0 / max 1.0. The others keep −1..1. — [mood_config.json (leak)](https://github.com/kercre123/victor/blob/snowboy/resources/config/engine/mood_config.json)
- The docs give the opposites: "The opposite of `Happy` is `Sad`", "The opposite of `Confident` is `Frustrated`… updated primarily when Victor succeeds or fails", "The opposite of `Social` is `Lonely`". Also: "Note that 'default' for Cozmo was happy-go-lucky, 'default' doesn't mean 'boring'." — [docs/architecture/emotions.md](https://github.com/digital-dream-labs/vector/blob/main/docs/architecture/emotions.md)
- The original Cozmo design doc (Andrew Stein, last updated Apr 24, 2017) proposed far more global emotions: Happy/Sad, Calm/Angry, Brave/Scared, Confident/Shameful, Charged (battery), Excited/Bored, Social/Lonely, Winning/Losing, WantToPlay. It also proposed per-entity emotions (Like/Hate, Appreciate/Envy). Only five survived into Vector. — [Cozmo Emotion Behavior Architecture.md](https://github.com/digital-dream-labs/vector/blob/main/docs/behavior/archive/Cozmo%20Emotion%20Behavior%20Architecture.md)

**Decay graphs (`decayGraphs` in mood_config.json)**
- There are two graph types (`MoodDecayEvaulator`, sic):
  - `"TimeRatio"`: "x here is the time in seconds since the most recent event… y is the ratio of the original value that should be reached by the given time". The graph must be non-increasing and x ≥ 0.
  - `"ValueSlope"`: "x here is the emotion value; y is the amount it decays (towards zero) per _minute_ as a fixed amount… Decay will never cross… 0".
  — [mood_config.json](https://github.com/kercre123/victor/blob/snowboy/resources/config/engine/mood_config.json), [moodDecayEvaluator.cpp](https://github.com/kercre123/victor/blob/snowboy/engine/moodSystem/moodDecayEvaluator.cpp)
- Shipped nodes (x → y):
  - default, used for Happy: TimeRatio (0→1, 10→1, 30→0.9, 75→0.6, 150→0)
  - Social: TimeRatio (0→1, 10→1, 20→0.6, 60→0.2, 100→0)
  - Confident: TimeRatio (0→1, 30→1, 60→0.5, 70→0)
  - Stimulated: ValueSlope (0→0.6, 0.2→0.12, 0.8→0.12, 0.8→0.4) per minute
  - Trust: ValueSlope (0→0.0), i.e. no decay

  The hard-coded fallback in code is (0→1, 15→1, 60→0.9, 150→0.6, 300→0). — [mood_config.json](https://github.com/kercre123/victor/blob/snowboy/resources/config/engine/mood_config.json), [staticMoodData.cpp](https://github.com/kercre123/victor/blob/snowboy/engine/moodSystem/staticMoodData.cpp)
- TimeRatio evaluation is `newValue = currentValue * (graph(t+dt)/graph(t))`, i.e. the curve is applied as a ratio of the value at the last event. — [moodDecayEvaluator.cpp](https://github.com/kercre123/victor/blob/snowboy/engine/moodSystem/moodDecayEvaluator.cpp)
- When the decay clock resets (`Emotion::Add`): `_timeDecaying` returns to 0 only if `|delta| > 0.05` and the delta pushes the value away from zero, or if the value crosses zero. Small or opposing nudges do not restart the "hold" plateau. — [emotion.cpp](https://github.com/kercre123/victor/blob/snowboy/engine/moodSystem/emotion.cpp)
- The update tick uses wall-clock delta times a console var `kTimeMultiplier`, which fast-forwards mood for testing. — [moodManager.cpp](https://github.com/kercre123/victor/blob/snowboy/engine/moodSystem/moodManager.cpp)

**Emotion events**
- Events live in JSON files grouped by domain under `resources/config/engine/emotionevents/`: action, charger, cliff, cube, face, game, interaction, reaction, system, utility and voice events. Each event has `"name"`, `"emotionAffectors": [{"emotionType", "value"}]` and an optional `"repetitionPenalty"` graph. — [emotionevents dir (leak)](https://github.com/kercre123/victor/tree/snowboy/resources/config/engine/emotionevents), [emotionEvent.cpp](https://github.com/kercre123/victor/blob/snowboy/engine/moodSystem/emotionEvent.cpp)
- Examples:
  - `LookAtFaceVerified`: Social +0.2, Happy +0.15, Stimulated +0.1, with repetitionPenalty nodes (0 s→0.0, 30 s→0.5, 300 s→1.0).
  - `InteractWithNamedFace`: Social +0.8, Happy +0.5, Stimulated +0.4.
  - `InteractWithFaceRetry`: Confident −0.1.

  — [face_events.json](https://github.com/kercre123/victor/blob/snowboy/resources/config/engine/emotionevents/face_events.json)
- More examples:
  - `ReactToTriggerWord`: Stimulated +1.0, Social +0.5, repetitionPenalty flat 1.0 (no penalty).
  - `RespondToShortVoiceCommand`: Stimulated +0.1, Social +0.2, Happy +0.15.

  — [voice_events.json](https://github.com/kercre123/victor/blob/snowboy/resources/config/engine/emotionevents/voice_events.json)
- `defaultRepetitionPenalty` nodes are (0.0→0.0, 0.5→0.0, 10.0→1.0): the same event repeated within 0.5 s has no effect, and it reaches full effect again after 10 s. Applied as `penalizedDeltaValue = affector.GetValue() * repetitionPenalty`, where x is the time since that event last fired. — [mood_config.json](https://github.com/kercre123/victor/blob/snowboy/resources/config/engine/mood_config.json), [moodManager.cpp](https://github.com/kercre123/victor/blob/snowboy/engine/moodSystem/moodManager.cpp)
- `actionResultEmotionEvents` maps action outcomes to events, e.g. `"DRIVE_TO_POSE": {"RETRY": "DrivingActionFailedWithRetry", "ABORT": "DrivingActionFailedWithAbort"}`. — [mood_config.json](https://github.com/kercre123/victor/blob/snowboy/resources/config/engine/mood_config.json)
- The design rationale for repetition penalties, from the Cozmo design doc: "if showing a block to Cozmo added 0.1 happiness generally, showing the block 5 times in a row shouldn't add (5 * 0.1) but… (0.1 + 0.05 + 0.025 + 0.01 + 0)". The doc also says every change carries a `uniqueIdString` for debug logging ("why" an emotion changed). — [Cozmo Emotion Behavior Architecture.md](https://github.com/digital-dream-labs/vector/blob/main/docs/behavior/archive/Cozmo%20Emotion%20Behavior%20Architecture.md)

**SimpleMood (the thing animations actually use)**
- `enum SimpleMoodType { Default = 0, LowStim, MedStim, HighStim, Frustrated, Count }`. — [simpleMoodTypes.clad](https://github.com/digital-dream-labs/vector/blob/main/clad/src/clad/types/simpleMoodTypes.clad)
- `GetSimpleMood(stimulated, confident)`:
  - `stimulated <= 0.2` → LowStim ("low stim takes precedence because we don't want to annoy people")
  - else `confident < -0.29` → Frustrated ("this is the value used on Cozmo, may need tuning")
  - else `stimulated <= 0.8` → MedStim
  - else → HighStim

  "Never returns Default (default is used by the animation group selector if more specific anims aren't provided)". `DidSimpleMoodTransitionThisTick(from, to)` uses the emotion history. — [moodManager.cpp](https://github.com/kercre123/victor/blob/snowboy/engine/moodSystem/moodManager.cpp)
- Behaviour conditions can read mood directly: `ConditionEmotion` takes keys `"emotion"`, `"min"`, `"max"` and `"value"`, and `ConditionSimpleMood` also exists. — [conditionEmotion.cpp](https://github.com/kercre123/victor/blob/snowboy/engine/aiComponent/beiConditions/conditions/conditionEmotion.cpp)
- High-level AI states can force a mood floor, e.g. state `"Exploring"` has `"ensureMinStimValue": 0.5 // will bring stim up to this value if it's below when this state starts`. — [highLevelAI.json](https://github.com/kercre123/victor/blob/snowboy/resources/config/engine/behaviorComponent/behaviors/victorBehaviorTree/highLevelAI.json)

**Continuous modulation (not just selection)**
- `audioParameterMap`: `"Stimulated": "Robot_Vic_Stimulation"`, `"Trust": "Robot_Vic_Held_Trust"`. These are sent to the audio engine every `kMoodManager_AudioSendPeriod_s` = 0.5 s, and immediately after any event. A commented-out alternative maps SimpleMood to audio values instead (LowStim −1, MedStim 0, HighStim 1, Frustrated −2). — [mood_config.json](https://github.com/kercre123/victor/blob/snowboy/resources/config/engine/mood_config.json), [moodManager.cpp](https://github.com/kercre123/victor/blob/snowboy/engine/moodSystem/moodManager.cpp)
- `StimulationFaceDisplay` maps Stimulated to face colour saturation through an exponential moving average (`kStimFace_ema_N` = 20, alpha = 2/(1+N)) and a graph (0→`kStimFace_minSaturation` 0.25, 1→1.0). It only sends when the change is > `kStimFace_sendThresh` 0.01. Its console var `kStimFace_enabled` defaults to `false`, and it is disabled in the PR demo. — [stimulationFaceDisplay.cpp](https://github.com/kercre123/victor/blob/snowboy/engine/moodSystem/stimulationFaceDisplay.cpp)
- The `DrivingAnimationHandler` "chooses a set of driving animations based on the current mood". — [emotions.md](https://github.com/digital-dream-labs/vector/blob/main/docs/architecture/emotions.md)

### Inferences
- The decay "hold plateau, then fall" shape (TimeRatio) maps well onto Frank's "mood underneath, transients on top". A transient spikes the value, holds 10–30 s, then fades. Using a different graph per dimension gives each dimension its own temperament (Social fades in ~100 s; Confident snaps back at 60–70 s).
- Repetition penalty keyed by event name is a cheap anti-spam measure for LLM expression tags. If the LLM emits `[laugh]` five times in a minute, each later one should move mood less (and probably animate smaller).
- Collapsing the continuous mood into a few discrete "SimpleMood" buckets, used only to choose among authored variants, is how Anki made a small authored library cover the mood space. Frank can do the same: keep a continuous mood for procedural modulation (brow baseline, lid aperture, blink rate, gaze-dart amplitude), and discrete buckets for variant selection.
- The mood→audio RTPC path (sent every 0.5 s) is the analogue of mood→TTS prosody for Frank, and of mood→procedural-layer gains.
- `kTimeMultiplier` (a fast-forward clock for the whole mood system) is worth copying for Frank's offline tests of decay and habituation.

### Gaps
- Anki's per-behaviour emotion scorers for Vector (`emotionScorer.cpp` / `moodScorer.cpp` exist) were not read in detail. The JSON configs of behaviours that still use mood scoring were not enumerated.
- The repo does not show whether `kStimFace_enabled` was switched on in production by a config or feature flag.
- The full emotion-event list (all 11 files) was not tabulated; only face, voice and part of interaction were read.

---

## Q2. The animation engine: anim process, AnimationStreamer, track layers, ProceduralFace parameters, keep-face-alive, combining authored and procedural, interruptions and priorities, frame rate, avoiding snaps

### Takeaway
Vector runs animation in a separate process on a fixed 33 ms tick, with audio samples as the clock. One "streaming" authored animation owns the tracks at a time. Named procedural layers (blink, eye dart, eye noise, squint, eye shift, glitch) are combined onto the face each tick with per-parameter rules: add, multiply, average or replace. "Keep face alive" runs blinks and darts on random timers only when no authored animation is streaming, starting 0.5 s after one ends. When an animation starts, the persistent layers ramp out over 3 frames. Anki's own docs admit there was no automatic smoothing between consecutive authored animations, which caused eye "pops".

### Cited Findings
**Process, tick and clock**
- "Because timing and coordination is a fundamental element of animations, they run on a very specific tick: 33 Hz… there is a separate animation process… The audio samples from WWise are used as the 'clock' for the rest of the tracks". Also: "Animations are scaled by 99% so that keyframes fall on integer boundaries, multiples of 33ms, rather than 33.33ms". (Note that the doc's "33 Hz" conflicts with the 33 ms step, which is about 30 Hz.) — [animations.md](https://github.com/digital-dream-labs/vector/blob/main/docs/architecture/animations.md)
- `const u32 ANIM_TIME_STEP_MS = 33;` and the face display is `184 x 96` px (Xray variant 160 × 80). — [cozmoConfig.h (leak)](https://github.com/kercre123/victor/blob/snowboy/robot/include/anki/cozmo/shared/cozmoConfig.h)
- Architecture summit notes (Kevin Yoon, Jun 23, 2017): the anim process is "the only component that directly controls Face display [and] wwise (audio)". "Engine remains the authority of which tracks are locked… this information is sent down to Anim Process… where the track locked state is mirrored". A separate process "potentially enables us to apply some tricks to enforce the 33ms tic rate". — [V2 Animation System.md](https://github.com/digital-dream-labs/vector/blob/main/docs/architecture/V2%20Animation%20System.md)
- Track types: Head, Lift, BodyMotion, Face (ProceduralFace or FaceAnimation image sequences), Audio, Backpack Lights, Event ("special" keyframes signalling the engine). "All keyframes have a trigger time, in milliseconds… and most have a duration". — [animations.md](https://github.com/digital-dream-labs/vector/blob/main/docs/architecture/animations.md)
- Authoring: animations are made in Maya on a robot rig, exported to JSON/FlatBuffers (.bin), and grouped into `AnimationGroup`s named `ag_featurename_animationname`. Code plays an `AnimationTrigger` (CLAD enum), mapped to a group in `AnimationTriggerMap.json`, e.g. `{"CladEvent": "AlexaIdle2Listen", "AnimName": "ag_avs_l_getin_01"}`. — [animations.md](https://github.com/digital-dream-labs/vector/blob/main/docs/architecture/animations.md), [AnimationTriggerMap.json (leak)](https://github.com/kercre123/victor/blob/snowboy/resources/assets/cladToFileMaps/AnimationTriggerMap.json)
- Audio latency compensation: "VIC-4224: Due to audio engine playback latency the animation audio keyframes are not in sync with the rest of the animation tracks… we have introduced a variable to offset that latency by playing audio keyframes earlier". The variable is `kAudioAnimationOffset_ms` = 200 (range 0–300). — [trackLayerComponent.cpp](https://github.com/digital-dream-labs/vector/blob/main/animProcess/src/cozmoAnim/animation/trackLayerComponent.cpp)

**ProceduralFace parameters**
- In Vector's CLAD, `ProceduralEyeParameter` has 25 per-eye values (all angles in degrees):
  - EyeCenterX, EyeCenterY (px)
  - EyeScaleX, EyeScaleY ("1.0 means nominal")
  - EyeAngle
  - Lower/Upper Inner/Outer RadiusX/Y (8 corner radii, fractions of eye width/height)
  - UpperLidY ("0=… open, 1=… closed"), UpperLidAngle, UpperLidBend ("0 for straight, >0 to bend down into eye")
  - LowerLidY, LowerLidAngle, LowerLidBend
  - Saturation, Lightness, GlowSize
  - HotSpotCenterX/Y ("pupil"… fraction [−1,+1])
  - GlowLightness

  The whole-face struct adds `faceAngle_deg, faceCenX, faceCenY, faceScaleX, faceScaleY, scanlineOpacity`, plus `leftEye[25], rightEye[25]`. — [proceduralFaceTypes.clad (leak)](https://github.com/kercre123/victor/blob/snowboy/robot/clad/src/clad/types/proceduralFaceTypes.clad)
- Older (Cozmo-era) authored keyframes carry 19 values per eye (the first 19 shape and lid params), e.g. a `"ProceduralFaceKeyFrame"` with `leftEye` [19 floats], `rightEye` [19], `faceCenterX/Y`, `faceScaleX/Y`, `faceAngle`, `triggerTime_ms`, `durationTime_ms`. This matches the "~19 coefficients" figure; Vector extended it with 6 colour/glow/hotspot values. — [anim_eyes_blink_line.json (leak)](https://github.com/kercre123/victor/blob/snowboy/resources/test/animProcessTests/anim_eyes_blink_line.json)
- Anki's note: "a ProceduralFace is just a rig with a bunch of parameters and is also stored in 'canned' animations". Rendering (`ProceduralFaceDrawer`) is separate, and hue is a global user setting, not animated. — [proceduralFace.md](https://github.com/digital-dream-labs/vector/blob/main/docs/architecture/proceduralFace.md)

**How layers combine (the key mechanism)**
- Each parameter has an `EyeParamCombineMethod` in a lookup table (`kEyeParamInfoLUT`), with clip limits:
  - **Add:** EyeCenterX/Y, EyeAngle, UpperLidAngle, LowerLidAngle
  - **Multiply:** EyeScaleX/Y
  - **Average:** HotSpotCenterX/Y
  - **None** (the layer cannot change it): all corner radii, UpperLidY, LowerLidY, both lid bends, Saturation, Lightness, GlowSize, GlowLightness

  At the face level, `Combine()` does `_faceAngle_deg += …; _faceScale *= …; _faceCenter += …`. — [proceduralFace.cpp](https://github.com/digital-dream-labs/vector/blob/main/cannedAnimLib/proceduralFace/proceduralFace.cpp)
- Per tick, `ApplyFaceLayersToAnim` starts from the last procedural face. If an animation has a face keyframe, it replaces that face (`kShouldReplace = true`), interpolated between the current and next keyframe. Then each layer's interpolated frame is `Combine()`d on top. — [trackLayerComponent.cpp](https://github.com/digital-dream-labs/vector/blob/main/animProcess/src/cozmoAnim/animation/trackLayerComponent.cpp), [faceLayerManager.cpp](https://github.com/digital-dream-labs/vector/blob/main/animProcess/src/cozmoAnim/animation/trackLayerManagers/faceLayerManager.cpp)
- Interpolation between keyframes is linear per parameter, with shortest-path wrap for angles (`BlendAngleHelper`, ±180°). — [proceduralFace.cpp](https://github.com/digital-dream-labs/vector/blob/main/cannedAnimLib/proceduralFace/proceduralFace.cpp)
- Layers come in two kinds:
  - One-shot layers: `AddLayer`, e.g. "Glitch".
  - Persistent layers: `AddPersistentLayer` / `AddToPersistentLayer`, e.g. "KeepAliveEyeDart", squint, eye shift.

  `RemovePersistentLayer(name, streamTime, duration_ms)` does not cut the layer. It adds a ramp track "that takes us back from where this persistent frame leaves off to no adjustment at all" over `duration_ms`. — [iTrackLayerManager.cpp](https://github.com/digital-dream-labs/vector/blob/main/animProcess/src/cozmoAnim/animation/trackLayerManagers/iTrackLayerManager.cpp)
- Named procedural APIs: `AddSquint(name, squintScaleX, squintScaleY, upperLidAngle)`, `AddOrUpdateEyeShift(name, xPix, yPix, …, outerEyeScaleIncrease)`, `AddGlitch(glitchDegree)`. The glitch is driven continuously from the needs system's "desired distortion" ("glitchy" face when repair need is high). — [trackLayerComponent.cpp](https://github.com/digital-dream-labs/vector/blob/main/animProcess/src/cozmoAnim/animation/trackLayerComponent.cpp), [animations.md](https://github.com/digital-dream-labs/vector/blob/main/docs/architecture/animations.md)

**Gaze (LookAt) as a procedural pose**
- `ProceduralFace::LookAt(xShift, yShift, xmax, ymax, lookUpMaxScale, lookDownMinScale, outerEyeScaleIncrease)` does four things:
  - shifts the whole face
  - enlarges the "outer" eye when looking sideways (`1 + outerEyeScaleIncrease * min(1,|x|/xmax)`) and shrinks the other by the complement
  - scales both eyes up when looking up and down when looking down
  - "If looking down… push eyes together (IOD=interocular distance)" by up to `MaxIOD = 2` px

  — [proceduralFace.cpp](https://github.com/digital-dream-labs/vector/blob/main/cannedAnimLib/proceduralFace/proceduralFace.cpp)

**Keep face alive: blinks, darts, noise**
- Layer names are `"KeepAliveEyeBlink"`, `"KeepAliveEyeDart"` and `"KeepAliveEyeNoise"`. Each keep-alive activity has a perform function and a next-time function. Every tick, `nextPerformanceTime_ms -= ANIM_TIME_STEP_MS`, and the activity fires at ≤ 0. If no face layer fired that tick, the eye-noise layer is added. Blinks and darts also emit procedural audio (`AddEyeBlinkToAudioTrack`, `AddEyeDartToAudioTrack`). — [trackLayerComponent.cpp](https://github.com/digital-dream-labs/vector/blob/main/animProcess/src/cozmoAnim/animation/trackLayerComponent.cpp)
- Eye dart parameters:
  - `kKeepAliveEyeDart_SpacingMinTime_ms` 1000, `…SpacingMaxTime_ms` 2250 (uniform random)
  - `…MaxDistFromCenter_pix` 15; `…MaxDistFromCenterFocused_pix` 1 (when "focused", e.g. on a face)
  - `…UpMaxScale` 1.05, `…DownMinScale` 0.9, `…OuterEyeScaleIncrease` 0.03
  - `…HotSpotPositionMultiplier` 1.5
  - Medium dart (> 5 px): one intermediate frame at shift 0.2 with vertical squash 0.85
  - Long dart (> 10 px): two intermediate frames at shift 0.2 / 0.4 with squash 0.7 / 0.85
  - Then the final position at full scale. Target = uniform random int in ±maxDist for x and y.

  — [faceLayerManager.cpp](https://github.com/digital-dream-labs/vector/blob/main/animProcess/src/cozmoAnim/animation/trackLayerManagers/faceLayerManager.cpp)
- Blink parameters: `kKeepAliveBlink_SpacingMinTime_ms` 3000, `…MaxTime_ms` 10000 (uniform). `kMaxBlinkSpacingTimeForScreenProtection_ms` 30000 is used as a fallback if the params are bad. — [faceLayerManager.cpp](https://github.com/digital-dream-labs/vector/blob/main/animProcess/src/cozmoAnim/animation/trackLayerManagers/faceLayerManager.cpp)
- The procedural blink is 7 frames of (height, width, t):

  | Height | Width | t | Phase |
  |---|---|---|---|
  | .85 | 1.05 | 33 ms | Closing |
  | .6 | 1.2 | 33 ms | Closing |
  | .1 | 2.5 | 33 ms | Closing |
  | .05 | 5.0 | 33 ms | Closed |
  | .15 | 2.0 | 33 ms | JustOpened |
  | .7 | 1.2 | 33 ms | Opening |
  | .9 | 1.0 | 100 ms | Opening |

  That is about 300 ms total: a fast ~100 ms close and a slower ~170 ms open. — [proceduralFaceDrawer.cpp](https://github.com/digital-dream-labs/vector/blob/main/cannedAnimLib/proceduralFace/proceduralFaceDrawer.cpp)

**Authored vs procedural ownership, interruption and snap avoidance**
- Gating comment: "Always keep face alive, unless we have a streaming animation, since we rely on it to do all face updating and we don't want to step on it's hand-designed toes. Wait a 1/2 second before running after we finish the last streaming animation to help reduce stepping on the next animation's toes when we have things sequenced." The value is `kDefaultLongEnoughSinceLastStreamTimeout_s = 0.5f`. — [animationStreamer.cpp](https://github.com/digital-dream-labs/vector/blob/main/animProcess/src/cozmoAnim/animation/animationStreamer.cpp)
- When an animation starts: `_proceduralTrackComponent->RemoveKeepFaceAlive(_relativeStreamTime_ms, (3 * ANIM_TIME_STEP_MS))`, a ~100 ms ramp-out of the blink and dart layers. Also `kMinTimeBetweenLastNonProcFaceAndNextProcFace_ms = 2 * ANIM_TIME_STEP_MS`. — [animationStreamer.cpp](https://github.com/digital-dream-labs/vector/blob/main/animProcess/src/cozmoAnim/animation/animationStreamer.cpp)
- `SetStreamingAnimation(anim, tag, numLoops, startAt_ms, interruptRunning, …)`: if something is streaming and `!interruptRunning`, it logs "Already streaming %s, will not interrupt with %s". Otherwise it `Abort`s the current one. `Abort(tag)` only aborts if `tag == _tag || tag == kNotAnimatingTag`, so a stale cancel cannot kill a newer animation. — [animationStreamer.cpp](https://github.com/digital-dream-labs/vector/blob/main/animProcess/src/cozmoAnim/animation/animationStreamer.cpp)
- Safety fallback: if an animation was "interrupted with nothing", the next keep-alive pass first streams `_neutralFaceAnimation` ("we'll stream neutral face for safety"). — [animationStreamer.cpp](https://github.com/digital-dream-labs/vector/blob/main/animProcess/src/cozmoAnim/animation/animationStreamer.cpp)
- Track locks: `_lockedTracks` is mirrored from the engine. Behaviours declare `"tracksToLockWhileActivated"` in JSON, and the streamer skips locked tracks when sending keyframes. `_lockFaceTrackAtEndOfStreamingAnimation` can hold the face after an animation. — [animationStreamer.cpp](https://github.com/digital-dream-labs/vector/blob/main/animProcess/src/cozmoAnim/animation/animationStreamer.cpp), [iCozmoBehavior.cpp (leak)](https://github.com/kercre123/victor/blob/snowboy/engine/aiComponent/behaviorComponent/behaviors/iCozmoBehavior.cpp)
- Dev tooling: the console function `ToggleKeepFaceAlive` exists "for the animators to disable KeepFaceAlive while testing eye shapes". The console var page `ProcFace_OverrideEyeParams` provides sliders for live eye tuning, and `playanimation.py` plays animations "on host" at a fixed 33 ms frame and pushes faces to the robot. — [animationStreamer.cpp](https://github.com/digital-dream-labs/vector/blob/main/animProcess/src/cozmoAnim/animation/animationStreamer.cpp), [animations.md](https://github.com/digital-dream-labs/vector/blob/main/docs/architecture/animations.md)
- Documented limitations:
  - "Gapless playback: … there are often small pauses or 'hiccups' between two animations (e.g. from a one-engine-tick delay…)"
  - "Automatic smooth transitions: there is not yet any mechanism to ensure a smooth transition from the final keyframe of one animation to the starting one of the next… This is particular try [sic] for the eyes, which can exhibit undesirable 'pops'."

  — [animations.md](https://github.com/digital-dream-labs/vector/blob/main/docs/architecture/animations.md)

### Inferences
- Frank's animator can copy the structure almost one-to-one, with servo channels in place of eye-shape parameters:
  - one base "performance" clip at a time, with a tag
  - named additive/multiplicative layers (blink, dart, brow offset, lid offset, speech jaw), each with a declared combine rule per channel
  - layer removal always as a ramp to identity, never a cut
  - keep-alive only when no clip owns the channel
  - a 0.5 s grace period after a clip ends
- The combine-rule table is the transferable idea. Frank needs per-channel rules:
  - gaze yaw/pitch: Add
  - lid aperture: Multiply, or min() for blinks
  - brow: Add with clip limits
  - jaw: max() or Add
  - Each needs clip limits equal to the servo soft limits. Vector's "None" category (lid Y could not be layered) is a weakness to avoid on a physical face, where blink must override lid aperture.
- Scaling Vector's dart numbers: 15 px of a 184 px-wide face is ~16 % of the half-width. Darts every 1–2.25 s; blinks every 3–10 s with a fast close and slow open (~100 ms / ~170 ms). These are good starting values for MG90S eyes and lids, re-expressed in degrees. The "focused" dart range (1 px) means darts shrink to almost nothing while attending a face.
- The audio-early offset (200 ms) is directly relevant to Frank's jaw/lip sync. Measure the TTS→speaker latency and servo lag, then shift either audio or motion.
- Anki's admitted "pops" between consecutive authored clips argue for Frank always cross-fading the start of a new clip from the current pose. Reachy Mini does this; see Q4.

### Gaps
- `streamingAnimationModifier.h/.cpp` (runtime edits to a playing animation) and `ProceduralFaceDrawer` lid geometry were not read in detail.
- The squint and eye-shift parameter values used by specific behaviours were not traced.
- Whether a tick overrun is caught up or dropped: only a drift warning (`timeDrift > 2 * ANIM_TIME_STEP_MS`) was seen.

---

## Q3. Behaviour selection, cooldowns, and anti-repetition (animation groups, weights, habituation)

### Takeaway
Cozmo's original design was utility-style: each behaviour bid a score from emotion graphs, plus a 10 % random factor and a recency multiplier. Vector moved to an explicit behaviour stack and tree with JSON-declared conditions and a hand-authored high-level state machine with long cooldowns and boredom timers. At the animation level, repetition is fought with weighted random choice among animation-group variants filtered by SimpleMood, with per-variant cooldowns, a fallback to "Default" mood, and a "least recently used" emergency pick.

### Cited Findings
- Cozmo design (2017), behaviour selection:
  - "Each behavior is responsible for scoring itself based on the current emotion state… score is a float in the 0='never' to 1='perfect match' range."
  - "the overall score is the average (not the product) of the scores for each emotion that it cares about… if any single emotion scores 0… the overall score is force[d] to 0."
  - "A scaled random number is added (e.g. 'kRandomFactor * randomInZeroToOneRange()', where kRandomFactor = 0.1…)"
  - "A multiplier (0..1) that scales based on recency that this behavior was played"
  - "External systems… can request a behavior to run with a priority - higher priority behaviors automatically trump anything being randomly chosen."

  — [Cozmo Emotion Behavior Architecture.md](https://github.com/digital-dream-labs/vector/blob/main/docs/behavior/archive/Cozmo%20Emotion%20Behavior%20Architecture.md)
- Vector behaviour system:
  - "Multiple behaviors are *active* in the stack, only the last one is *in control*"
  - "At least one behavior is always active. There is a `Wait` behavior… there is never 'no behavior'"
  - "Behaviors will only become active if `WantsToBeActivated()` returns true"

  Each behaviour instance is a JSON file with `BehaviorClass` and `BehaviorID`. — [behaviors.md](https://github.com/digital-dream-labs/vector/blob/main/docs/architecture/behaviors.md)
- Behaviour JSON keys in `ICozmoBehavior`: `behaviorClass`, `behaviorID`, `wantsToBeActivatedCondition`, `wantsToCancelSelfCondition`, `respondToUserIntents`, `resetTimers`, `emotionEventOnActivated`, `postBehaviorSuggestion`, `tracksToLockWhileActivated`, `alterStreamAfterWakeword`, `pushTriggerWordResponse`, `anonymousBehaviors`, `behaviorModifiers`. — [iCozmoBehavior.cpp (leak)](https://github.com/kercre123/victor/blob/snowboy/engine/aiComponent/behaviorComponent/behaviors/iCozmoBehavior.cpp)
- Cooldowns: `BehaviorCooldownInfo` reads `"cooldown_s"` and `"cooldown_random_factor"`, where the actual cooldown = `cooldown_s * U[max(0,1−f), 1+f]`. A negative cooldown means "forever", and `"ignoreFastForward"` controls whether the cooldown follows `kTimeMultiplier`. — [behaviorCooldownInfo.cpp (leak)](https://github.com/kercre123/victor/blob/snowboy/engine/aiComponent/behaviorComponent/behaviors/dispatch/helpers/behaviorCooldownInfo.cpp)
- `HighLevelAI` is a JSON state machine:
  - `"socializeKnownFaceCooldown_s": 1800.0`, `"playWithCubeCooldown_s": 600.0`, `"playWithCubeOnChargerCooldown_s": 2400.0`
  - states with `behavior`, optional `getInBehavior` (a transition animation into the state), `resetBehaviorTimer` and `ensureMinStimValue`
  - `"stateTimerConditions"` such as `"BoredOfObserving" begin_s 1100.0`, `"BoredOfExploring" 600.0`, `"NoLongerRecentlyPlaced" 150.0`
  - `"transitionDefinitions"` and `"postBehaviorSuggestionResumeOverrides"`

  — [highLevelAI.json (leak)](https://github.com/kercre123/victor/blob/snowboy/resources/config/engine/behaviorComponent/behaviors/victorBehaviorTree/highLevelAI.json)
- Animation group entry JSON keys: `"Name"`, `"Weight"`, `"Mood"` (a SimpleMoodType string), `"CooldownTime_Sec"`, `"UseHeadAngle"`, `"HeadAngleMin_Deg"`, `"HeadAngleMax_Deg"`. — [animationGroupEntry.cpp](https://github.com/digital-dream-labs/vector/blob/main/engine/animations/animationGroup/animationGroupEntry.cpp)
- Example group: `{"Animations": [{"Name": "majorWin", "Mood": "Default", "Weight": 1.0, "CooldownTime_Sec": 10.0}, {"Name": "majorWinBeatBox", "Mood": "Default", "Weight": 0.01}]}`. — [testAnimationGroup.cpp (leak)](https://github.com/kercre123/victor/blob/snowboy/test/engine/testAnimationGroup.cpp)
- The selection algorithm (`AnimationGroup::GetAnimationName`):
  1. Keep entries whose `Mood` == the current SimpleMood, whose head angle is valid, and that are not on cooldown.
  2. Pick by weighted random (`_rng.RandDbl(totalWeight)`) and set that entry's cooldown to `now + CooldownTime_Sec`.
  3. If nothing matched, retry with `SimpleMoodType::Default`.
  4. If everything is on cooldown and not `strictCooldown`, "choose the animation closest to being off cooldown".
  5. Otherwise return empty and log an error.

  The cooldown state is shared across groups through `AnimationGroupContainer`. — [animationGroup.cpp](https://github.com/digital-dream-labs/vector/blob/main/engine/animations/animationGroup/animationGroup.cpp)
- At the mood level, anti-repetition is the per-event `repetitionPenalty` graph (see Q1). The Cozmo design roadmap lists both "Penalize repeated emotion effectors" and "Penalize repeated behavior selection" as completed. — [Cozmo Emotion Behavior Architecture.md](https://github.com/digital-dream-labs/vector/blob/main/docs/behavior/archive/Cozmo%20Emotion%20Behavior%20Architecture.md)
- Disney's habituation is the gaze-attention analogue. A person's curiosity score is multiplied by a habituation factor η(t) ∈ [0,1] with dη = (B·m_hab + B̄·m_rest)·dt, where B = 1 while looked at, m_hab is a negative decay rate and m_rest a positive restoration rate. This "limits the character from repeatedly responding to a single guest and ignoring others". — [Pan et al. 2020, Realistic and Interactive Robot Gaze (PDF)](https://la.disneyresearch.com/wp-content/uploads/root.pdf)

### Inferences
- For Frank's orchestrator, Vector's shape fits a talking head better than Cozmo's utility bidding. It amounts to explicit controller states with get-in transitions, minimum dwell and cooldowns (Vector state machine; Disney's min-timeout in Engage), plus mood as a modulator and a variant selector.
- For LLM expression tags, the animation-group mechanism is the right resolver. A tag such as `smile` maps to a group; variants are filtered by the current mood bucket; the choice is weighted random with per-variant cooldowns, falls back to Default variants, and picks the least-recently-used variant when everything is on cooldown.
- `cooldown_random_factor` (jittered cooldowns) and uniform-random keep-alive intervals both serve to avoid visible periodicity. Use the same jitter on Frank's idle glances and brow flicks.

### Gaps
- How Vector's behaviour stack arbitrates simultaneous `WantsToBeActivated` candidates in "dispatcher" behaviours (priority list vs. random dispatchers) was not read.
- No public data on how many variants per animation group Anki typically shipped.

---

## Q4. Other shipped or published systems with enough detail (Furhat, Engineered Arts Tritium, Disney show objects, Reachy Mini conversation app, Jibo SDK, Sony aibo)

### Takeaway
- **Disney (Pan et al. 2020)** gives the most transferable architecture: composable "show objects" with group, sequence, loop, random and arithmetic operators, layered by subsumption levels L0 Zero → L1 Alive (breathing, blinks, saccades) → L2 Read (default) → L3 Glance → L4 Engage → L5 Acknowledge (overlay). It quotes concrete motion-bandwidth numbers.
- **Jibo's ESML** is a ready-made precedent for LLM-tag-style markup. It has blocking, bounded and unbounded animations, `endNeutral`, per-MetaLayer conflict rules and auto-tagging (beat blinks, question posture) at lower priority than explicit tags.
- **Reachy Mini's open-source app** shows a Python, single-writer control loop: sequential primary moves, idle breathing, a listening freeze with blend-back, and audio-driven speech sway.
- **Furhat** exposes keyframed gestures over named face parameters.
- **Engineered Arts** publishes only user-level docs; its arbitration internals sit behind a login.
- **aibo's** model is published only at a high level.

### Cited Findings
**Disney Research: "Realistic and Interactive Robot Gaze" (IROS 2020, DOI 10.1109/IROS45743.2020.9341297)**
- The platform is a WDI Audio-Animatronics bust with 19 DOF, of which nine are used: neck (3), eyes (2), eyelids (2), eyebrows (2). It runs on "a custom proprietary software stack operating on a 100Hz real-time loop", with perception from an external RGB-D camera. — [Pan et al. PDF](https://la.disneyresearch.com/wp-content/uploads/root.pdf)
- There are three components: an attention engine (skeletons → curiosity score with habituation), a behaviour selection engine ("handcrafted state machine" holding states, curiosity thresholds, state timeout durations and a guest database) and a behaviour library (show objects). — [Pan et al. PDF](https://la.disneyresearch.com/wp-content/uploads/root.pdf)
- The curiosity score is η(t)·[w_raised_hand·(h_r + h_l) + w_hand·(v̂_r + v̂_l) + w_nose·v̂_nose + w_distance·e^(−a·d_nose)]. The authors call the weights a way for "character creators to shape the interactive personality". Their example: "a nervous character that responds to the slightest sound or movement, whereas a character falling asleep may respond only to the most arousing stimuli". — [Pan et al. PDF](https://la.disneyresearch.com/wp-content/uploads/root.pdf)
- States:
  - Read (default)
  - Glance (score above a threshold but below Engage; returns after a timeout that is a function of the score)
  - Engage (eyes and head on the person; exits only after a minimum timeout AND once the score drops below threshold: "the timeout guarantees a minimum time length for this behavior to ensure character believability")
  - Acknowledge (familiar person)

  — [Pan et al. PDF](https://la.disneyresearch.com/wp-content/uploads/root.pdf)
- Show objects "can be grouped (made to run simultaneously), sequenced…, looped…, and randomly selected… Additionally, show objects can be added together, multiplied by scalars, or subtracted from each other." The example is a read show, built as `sequence(read_pose, loop(group(head_read, random_select(eyes_read_A, B, C))))` with poses like "lids down 70% for 1.0s". — [Pan et al. PDF](https://la.disneyresearch.com/wp-content/uploads/root.pdf)
- Subsumption levels:
  - L0 Zero Show (default zero pose, e.g. jaw closed)
  - L1 Alive Show ("breathing, eye blinking, saccades… 'secondary action'… do not interfere with higher level behaviors")
  - L2 Read Show ("always running… default fallback")
  - L3 Glance (head tilt scales with the score)
  - L4 Engage ("Normal eye saccading from the L1 alive show is interrupted to saccade based on a person's eye and nose locations… Eyebrows are furrowed")
  - L5 Acknowledge (randomly selected nod from mocap, "played as an overlay on top of the engage show")

  — [Pan et al. PDF](https://la.disneyresearch.com/wp-content/uploads/root.pdf)
- Motion numbers:
  - The figure "is able to saccade with a frequency of 20 Hz".
  - During mutual gaze, "the eyes saccade randomly between three points forming a triangle on a person-of-interest: the eyes and nose. Timing of saccadic movements is random with a range of 0.1 to 0.5s."
  - "eyelid motion had a frequency of 10 Hz, whereas head/neck motion was limited to 5 Hz or less".
  - "the eyes reach the gaze position first at a high rate of speed, followed by the head at a lower rate".

  — [Pan et al. PDF](https://la.disneyresearch.com/wp-content/uploads/root.pdf)
- Background coverage: Rodney Brooks commented that Disney's use of subsumption for eye control is "better and smoother now than our 1995 implementations on Cog and Kismet"; the pandemic prevented user studies. — [IEEE Spectrum](https://spectrum.ieee.org/amp/disney-research-robotic-gaze-2650233027)

**Jibo SDK: Embodied Speech Markup Language (ESML); doc hosted by MIT Media Lab's Jibo HRI 2024 site, file dated "121023"**
- Animation requests:
  - `<es name='Eye_Curious_01'/>` names a specific animation.
  - `<es cat='curious'>…</es>` requests a category; the "AnimDB" is searchable by "name, layers, categories, and meta terms".
  - `filter='!ssa-only, !happy'` filters on meta terms, with `&(…)` required, `?(…)` optional and `!(…)` excluded.
  - `path='my-anim.keys'` plays a custom .keys file.

  — [Jibo SDK ESML PDF](https://hri2024.jibo.media.mit.edu/attachments/SDK-SDK---ESML-121023-203758.pdf)
- Timing modes:
  - Blocking (no text inside the tag): "nothing else will happen while the animation is playing".
  - Bounded non-blocking (text inside the tag): "the length of the animation will be automatically derived based on what text it surrounds".
  - Unbounded non-blocking (`nonBlocking='true'`, the native duration).
  - `loop='0'` with bounded "fit[s] as many loops as it can".

  — [Jibo SDK ESML PDF](https://hri2024.jibo.media.mit.edu/attachments/SDK-SDK---ESML-121023-203758.pdf)
- End state: "By default, when animations complete, Jibo will stay in the final pose (until something else takes over, usually his Attention System)". `endNeutral='true'` returns to neutral instead. — [Jibo SDK ESML PDF](https://hri2024.jibo.media.mit.edu/attachments/SDK-SDK---ESML-121023-203758.pdf)
- Layering: MetaLayers are Body (Body), Screen (Eye, Eye Texture, Overlay, Overlay Texture, Pixi, Background Texture) and Audio (Audio Event). "multiple animations can play at the same time if and only if they occupy different MetaLayers… If… they would then conflict on the Body layer and one animation would be rejected." `layers='!screen'` strips a layer, and `+` adds empty layers "so that it blends with other content differently". — [Jibo SDK ESML PDF](https://hri2024.jibo.media.mit.edu/attachments/SDK-SDK---ESML-121023-203758.pdf)
- Auto-tagging, which decorates plain text automatically:
  - "Timeline modifying" rules (EmotionalVoice: "Modifies the TTS voice parameters around sentences based on Jibo's emotional state").
  - "Standard" rules, which "are always of lower priority to the animations and sounds that were requested via tags… will never take the place of an animation that you requested":
    - Initiate ("At the beginning of sentences, Jibo will shift his weight")
    - Question ("change posture at the end")
    - BeatBlink ("throughout a sentence, based on heuristics around when it makes sense… to blink while speaking")
    - Blink & DoubleBlink ("sometimes blink at the end of period and exclamation sentences, and will DoubleBlink at the end of question sentences")
    - Comma
    - HotWords

  Rule classes can be toggled through `AutoRuleConfig`. Speaking styles: `<style set="enthusiastic">`, with neutral, enthusiastic, sheepish, confused and confident available. — [Jibo SDK ESML PDF](https://hri2024.jibo.media.mit.edu/attachments/SDK-SDK---ESML-121023-203758.pdf)
- Community copies of the older Jibo SDK samples describe the Behavior Editor's `LookAt` with single-shot vs continuous modes and `.keys` animations that "dispatch generic events at specific keyframes". This is a community copy, not official. — [apoorva11029/sample-code](https://github.com/apoorva11029/sample-code)

**Reachy Mini conversation app (Pollen Robotics; Apache-2.0; last push 2026-10-26)**
- `moves.py` design overview:
  - "Primary moves (emotions, dances, goto, breathing) are mutually exclusive and run sequentially."
  - "There is a single control point to the robot: `ReachyMini.set_target`."
  - "Idle behaviour starts an infinite `BreathingMove` after a short inactivity delay unless listening is active."
  - "Listening freezes antennas, then blends them back on unfreeze."
  - "Interpolations and blends are used to avoid jumps at all times."

  `CONTROL_LOOP_FREQUENCY_HZ = 60.0`, but the docstrings still say "near 100 Hz" / "attempts 100 Hz", an internal inconsistency. — [moves.py](https://github.com/pollen-robotics/reachy_mini_conversation_app/blob/main/src/reachy_mini_conversation_app/moves.py)
- Parameters:
  - `idle_inactivity_delay = 0.3` s
  - BreathingMove first interpolates to neutral over `interpolation_duration = 1.0` s, then `breathing_z_amplitude = 0.005` (5 mm) at `breathing_frequency = 0.1` Hz ("6 breaths per minute") and `antenna_sway_amplitude` 15° at 0.5 Hz
  - `_antenna_blend_duration = 0.4` s to blend back after listening
  - Between moves, "reuse the last primary pose so we avoid jumps"
  - The loop uses `time.monotonic()` and a command queue; one worker thread owns all real-time state

  — [moves.py](https://github.com/pollen-robotics/reachy_mini_conversation_app/blob/main/src/reachy_mini_conversation_app/moves.py)
- Speaking and gaze hand-off: `set_speaking(True)` captures "the current look-at pose… as an anchor so queued moves stay on the user" and sets head tracking `weight=0.0`. Emotion moves are composed on top of the anchor with `compose_world_offset(self._track_anchor, head_pose)`. "Pause only once a face is locked, else speech blocks acquisition." — [moves.py](https://github.com/pollen-robotics/reachy_mini_conversation_app/blob/main/src/reachy_mini_conversation_app/moves.py)
- Idle policy weights: "IdleDoNothing: 60%, Dance: 16%, PlayEmotion: 16%, MoveHead: 8%", renormalised over the available tools. Emotions are recorded moves from the HF dataset `RecordedMoves("pollen-robotics/reachy-mini-emotions-library")`, exposed to the LLM as a `play_emotion` tool. — [idle_policy.py](https://github.com/pollen-robotics/reachy_mini_conversation_app/blob/main/src/reachy_mini_conversation_app/idle_policy.py), [play_emotion.py](https://github.com/pollen-robotics/reachy_mini_conversation_app/blob/main/src/reachy_mini_conversation_app/tools/play_emotion.py)
- Speech-driven sway (in the app until 2026-06-04, then moved: commit "head wobbler is now handled on the core side (#336)"). `HeadWobbler` uses `MOVEMENT_LATENCY_S = 0.2` ("seconds between audio and robot movement"). `SwayRollRT` parameters:
  - `HOP_MS=50`
  - VAD hysteresis `VAD_DB_ON=-35.0` / `VAD_DB_OFF=-45.0`, `VAD_ATTACK_MS=40`, `VAD_RELEASE_MS=250`
  - loudness mapped between `SWAY_DB_LOW=-46.0` and `SWAY_DB_HIGH=-18.0`, `LOUDNESS_GAMMA=0.9`
  - envelope `ENV_FOLLOW_GAIN=0.65`
  - sinusoids at incommensurate frequencies with random phases: pitch 2.2 Hz / 4.5°, yaw 0.6 Hz / 7.5°, roll 1.3 Hz / 2.25°, x 0.35 Hz / 4.5 mm, y 0.45 Hz / 3.75 mm, z 0.25 Hz / 2.25 mm
  - `SWAY_MASTER=1.5`

  — [speech_tapper.py @9f45935](https://github.com/pollen-robotics/reachy_mini_conversation_app/blob/9f459355883e5fb32f6894bf510db486e599ac78/src/reachy_mini_conversation_app/audio/speech_tapper.py), [head_wobbler.py @9f45935](https://github.com/pollen-robotics/reachy_mini_conversation_app/blob/9f459355883e5fb32f6894bf510db486e599ac78/src/reachy_mini_conversation_app/audio/head_wobbler.py), [commit d631c67](https://github.com/pollen-robotics/reachy_mini_conversation_app/commit/d631c67fa87940901f36d7d168073182799e7236)
- The core SDK repo `pollen-robotics/reachy_mini` is Apache-2.0 and was last pushed 2026-10-30. Where the wobbler now lives in core was not located. — [reachy_mini](https://github.com/pollen-robotics/reachy_mini)

**Furhat**
- The official docs (docs.furhat.io) returned HTTP 403 "AccessDenied" during this research, so the official gesture and persona reference could not be read (see Gaps).
- Gesture JSON from the Remote API README: `furhat.gesture(definition={"frames": [{"time": [0.33], "params": {"BLINK_LEFT": 1.0}}, {"time": [0.67], "params": {"reset": True}}], "class": "furhatos.gestures.Gesture"})`. Named gestures are invoked like `furhat.gesture(name="BrowRaise")`; gaze is set with `furhat.attend(user="CLOSEST")` or a location. — [furhat-remote-api on PyPI](https://pypi.org/project/furhat-remote-api/)
- The parameter vocabulary used by the Expressive Furhat project:
  - expressions: EXPR_ANGER, EXPR_DISGUST, EXPR_FEAR, EXPR_SAD, SMILE_CLOSED, SMILE_OPEN, SURPRISE
  - eyes: LOOK_DOWN/LEFT/RIGHT/UP and combinations
  - brows: BROW_DOWN_LEFT/RIGHT, BROW_IN_LEFT/RIGHT, BROW_UP_LEFT/RIGHT
  - EYE_SQUINT_LEFT/RIGHT, BLINK_LEFT/RIGHT
  - NECK_TILT/PAN/ROLL in degrees
  - frames often end with `{"reset": True}`

  — [expressive-furhat prompts.py](https://github.com/giubots/expressive-furhat/blob/master/expressive_furhat/prompts.py)
- Expressive Furhat (Abbo, Janssens, Van de Vreken, Belpaeme; listed for HRI 2026; Apache-2.0; last push 2026-05-19) runs a multi-stage LLM pipeline: "1. Detect mood changes… 2. Quickly generate a gesture when a mood change is detected. 3. Reason about the robot's behavior… 4. Generate multiple gestures". It has two threads:
  - **Background gestures:** samples a cache "every `self.wait_seconds`" (`DEFAULT_WAIT_SECONDS = 1.0`) with geometric recency weighting (`weighting_factor**i`, `DEFAULT_WEIGHTING_FACTOR = 1.4`, so newer gestures dominate).
  - **Gaze aversion:** `DEFAULT_ENGAGED_DURATION_RANGE = [2.0, 5.0]` s, `DEFAULT_EVERSION_DURATION_RANGE = [0.5, 4.0]` s, `DEFAULT_PAN_RANGE = [-20, 20]`, `DEFAULT_TILT_RANGE = [-30, 30]`, `DEFAULT_EYE_MOVEMENT_SPEED = 0.2`.

  — [expressive-furhat repo](https://github.com/giubots/expressive-furhat), [gesture_generation.py](https://github.com/giubots/expressive-furhat/blob/master/expressive_furhat/gesture_generation.py), [background_gestures.py](https://github.com/giubots/expressive-furhat/blob/master/expressive_furhat/background_gestures.py), [gaze_aversion.py](https://github.com/giubots/expressive-furhat/blob/master/expressive_furhat/gaze_aversion.py)
- Search-snippet-level claims only (pages not opened):
  - Furhat's vendor page says the robot "has built in automatic behaviours such as blinking, micro movements of the face and eyes that provides a feeling that the face is alive" — [furhatrobotics.com/furhat](https://furhatrobotics.com/furhat)
  - an arXiv paper says Furhat face control uses "BasicParams, for example MOUTH SMILE LEFT and MOUTH SMILE RIGHT" — [arXiv 2402.08837](https://arxiv.org/pdf/2402.08837)
  - another says Furhat "employs Apple's ARKit parameters… between 0… and 1" — [arXiv 2410.14337](https://arxiv.org/pdf/2410.14337)

**Engineered Arts (Tritium / Ameca)**
- Public user docs:
  - Built-in expressions (Ameca, Ami, Azi): Content, Happy, Sad, Disgust, Surprise, Anger, Fear, Confused, Thinking, Joy, Sneer, Worried. "Further expressions can be created using Animator". — [EA Expressions](https://docs.engineeredarts.co.uk/guide/reference/software/expressions)
  - "Tritium AI" stack lists ASR, LLMs, TTS, computer vision and "Expressions – drives facial expressions in real time during conversation"; behaviour is configured through "Agents". — [EA Tritium AI](https://docs.engineeredarts.co.uk/guide/reference/software/tritium-ai)
  - Operating modes: Startup, Active ("Conversation, telepresence, and built-in behaviour are available"), Manual, Stopped; older Tritium 3.0 used "Idle" instead of "Active". — [EA Operational modes](https://docs.engineeredarts.co.uk/guide/reference/software/operational_modes)
- Animator: keyframes are stored in "tracks". "Limit Control restricts which body parts this clip controls during playback, so other robot movement can continue on unselected parts. For how this interacts with playback and motor sharing, see Sequence Player and arbitration (developer docs)." The animation-principles page recommends pose-to-pose in passes (key poses → breakdowns → inbetweens) and stepped, linear and Bezier keys. — [EA Animator](https://docs.engineeredarts.co.uk/guide/reference/software/tritium_ui_animator), [EA Animation principles](https://docs.engineeredarts.co.uk/guide/reference/software/animation_principles)
- The developer pages `/guide/developer/arbitration`, `/guide/developer/sequence_player` and `/guide/developer/state_engine` returned "Unauthorized". — [EA developer: arbitration](https://docs.engineeredarts.co.uk/guide/developer/arbitration)

**Sony aibo**
- The ERS-111 owner's manual: "AIBO is sensitive to and can feel emotions such as joy, sadness, anger, surprise, fear and discontent". Triggers include joy ("receives approval… plays with a ball"), sadness ("cannot find anyone to play with") and fear ("finds a large gap on the floor, or… unable to get up from a fall"). "These emotions will change in accordance with contributing factors and affect the behaviour and maturation of AIBO." Instincts are covered in a separate section of the manual that was not retrieved. — [ERS-111 manual (manualslib)](https://www.manualslib.de/manual/109479/Sony-Ers-111-Aibo.html?page=55)
- Academic description: Arkin, Fujita, Takagi, Hasegawa, "Ethological Modeling and Architecture for an Entertainment Robot", ICRA 2001 (DOI 10.1109/ROBOT.2001.932592), presents "a functional, not physiological, model" of a dog on AIBO (from the search summary; the full text was not retrieved). — [GaTech repository entry](https://repository.gatech.edu/entities/publication/5f2f97cb-07d6-4f74-8d8b-f4c0428e0691)

### Inferences
- Disney's show-object algebra (group, sequence, loop, random-select, +, ×scalar, −) is a compact design for Frank's animator clip library. It also matches Vector's layer combine rules and Jibo's MetaLayers, so the three shipped systems converge on one shape: base performance plus additive secondary layers plus subsumption overrides.
- Disney's bandwidth numbers can serve as initial per-channel low-pass and slew limits for Frank: lids ~10 Hz, gaze saccades fast, head ≤ 5 Hz (Frank has no neck, so brows and jaw sit between). Its saccade timing (random 0.1–0.5 s among the eyes/nose triangle) gives a "listening/looking at you" micro-gaze for Frank's eyes.
- Jibo ESML's bounded vs unbounded vs blocking distinction, with `endNeutral` and "auto-tags never override explicit tags", maps directly onto Frank's LLM expression tags. It is a proven answer to "how long does `[smile]` last" (bounded to the following text span) and "what happens after" (hold the final pose until attention takes over, or return to neutral).
- Reachy's listening freeze plus blend-back, the 0.3 s idle delay and the speaking anchor are small, tested rules for a conversation loop in Python. Its speech sway (VAD hysteresis, loudness envelope, incommensurate sinusoids) could drive Frank's brow and eye micro-motion during speech, since Frank has no neck. Pollen moved the wobbler into the core daemon, which suggests audio-coupled motion belongs next to the audio clock, not in the app layer.
- Expressive Furhat's gaze aversion (2–5 s engaged, 0.5–4 s averted) gives published defaults for Frank's conversational gaze aversion.

### Gaps
- Furhat's official gesture DSL (Kotlin `defineGesture`, `persist`, priority) and its "persona" and emotion parameters: docs.furhat.io returned 403, and no alternative primary source was found.
- Engineered Arts "Human Behaviours", Tritium arbitration and the state engine are behind a login; no public technical description of lookaround, blink or saccade layering was found.
- Jibo's attention system internals (target selection, salience, timing) and the `.keys` format: only the ESML doc and a community sample were found.
- aibo's instinct variables and update equations were not verified, because the full texts were not retrieved (core.ac.uk returned an HTML wrapper).
- The location and current parameters of Reachy Mini's core-side head wobbler after 2026-06 were not found.

---

## Q5. Lessons and failure modes reported by these teams

### Takeaway
The strongest primary-source lesson is Anki's own: the emotion system "was originally intended to be very broad and the main driver of behavior" but shrank. Designers could not author enough variation for mixed states and needed explicit, cooldown-guarded transitions. Other reported failure modes: hiccups and eye "pops" between consecutive authored animations, audio latency desync, procedural layers stepping on authored animation, believability that degrades with proximity and time, and eye motion that has to be faster than head motion.

### Cited Findings
- Anki on the emotion system: "Over time, it's role decreased because we either didn't have enough variation to cover the states (e.g. what does a 'bored' + 'happy' + 'frustrated' greeting look like?), or because we wanted more direct control over behavior. For example an explicit 'search for faces' transition rather than having the robot automatically search for faces when lonely. The explicit transition can then have a cooldown… The resulting system is less modular and emergent, but easier to control and handle specific design requirements and edge cases." — [docs/behavior/emotions.md](https://github.com/digital-dream-labs/vector/blob/main/docs/behavior/emotions.md)
- "Note that many of these emotions exist but aren't really used for anything (e.g. 'excited')." — [docs/architecture/emotions.md](https://github.com/digital-dream-labs/vector/blob/main/docs/architecture/emotions.md)
- Transitions: "there is not yet any mechanism to ensure a smooth transition from the final keyframe of one animation to the starting one of the next… particular[ly] for the eyes, which can exhibit undesirable 'pops'". Also "small pauses or 'hiccups' between two animations… from a one-engine-tick delay". — [animations.md](https://github.com/digital-dream-labs/vector/blob/main/docs/architecture/animations.md)
- Procedural vs authored contention is handled in code comments: keep-alive must not "step on it's hand-designed toes", and a 0.5 s delay helps "reduce stepping on the next animation's toes when we have things sequenced". — [animationStreamer.cpp](https://github.com/digital-dream-labs/vector/blob/main/animProcess/src/cozmoAnim/animation/animationStreamer.cpp)
- Audio sync: "VIC-4224: Due to audio engine playback latency the animation audio keyframes are not in sync", fixed by a 200 ms early-audio offset. — [trackLayerComponent.cpp](https://github.com/digital-dream-labs/vector/blob/main/animProcess/src/cozmoAnim/animation/trackLayerComponent.cpp)
- Mood tuning priority: "low stim takes precedence because we don't want to annoy people". — [moodManager.cpp](https://github.com/kercre123/victor/blob/snowboy/engine/moodSystem/moodManager.cpp)
- GDC 2017, "Cozmo: Animation Pipeline for a Physical Robot" (Molly Jameson, Daria Jerjomina, Anki): animations must obey real-world physics, so squash-and-stretch is unavailable. The talk covers fast animator iteration tools, test and debug scripts, Maya-to-physical translation, streaming audio and animation to the robot, and "when programmatic corrections were needed" (paraphrased abstract). — [GDC Vault 1024221](https://gdcvault.com/play/1024221/Cozmo-Animation-Pipeline-for-a)
- Disney's lessons:
  - "believability of this implementation is a function of time and distance… At closer distances and for longer periods of time, more complex behaviors are required"; their system "is satisfactory at close distances, but for a relatively short period of time (one or two minutes)".
  - "saccades appear to significantly improve character realism", and saccading between the eyes and nose gives an "illusion of vergence" on mechanically linked eyes.
  - "Changing something like how fast the robot saccades, blinks or breathes only involves changing a single behavioral layer, rather than requiring the regeneration of an entire set of motor trajectories."
  - "the lack of emotional range is a limitation".

  — [Pan et al. PDF](https://la.disneyresearch.com/wp-content/uploads/root.pdf)
- Disney on eye cameras: in-eye cameras force "slow, smooth eye motion profiles that lack fidelity". An external static camera allows human-like saccades. — [Pan et al. PDF](https://la.disneyresearch.com/wp-content/uploads/root.pdf)
- Reachy Mini: a speech-time rule, "Pause only once a face is locked, else speech blocks acquisition". The project moved speech wobble from the app to the core daemon (#336, 2026-06-04). — [moves.py](https://github.com/pollen-robotics/reachy_mini_conversation_app/blob/main/src/reachy_mini_conversation_app/moves.py), [commit d631c67](https://github.com/pollen-robotics/reachy_mini_conversation_app/commit/d631c67fa87940901f36d7d168073182799e7236)
- Jibo: the ESML doc notes that timeline-modifying auto-rules "do not conflict with content that you've requested, but we cannot guarantee that to be true in every case", an admitted edge case in automatic speech decoration. — [Jibo SDK ESML PDF](https://hri2024.jibo.media.mit.edu/attachments/SDK-SDK---ESML-121023-203758.pdf)

### Inferences
- For Frank: keep the mood model small, and use it mainly as a modulator of procedural layers and as a variant filter. Do not make it the sole driver of the controller states (Anki's experience). Explicit orchestrator transitions with cooldowns, plus LLM tags, should decide what happens; mood should decide how it looks.
- Build cross-fade-from-current-pose into clip starts from day one (Anki never had it and reported pops). Measure audio-to-motion latency early (Anki 200 ms, Reachy 0.2 s).
- Frank will be seen up close for a long time, so plan for Disney's warning: L1 "alive" behaviours (blinks, saccades, micro-brow motion) must have enough variation not to read as loops over many minutes. Use jittered intervals, habituation and mood-dependent rates.

### Gaps
- No talk or interview by Carlos Baena or Doug Dooley with technical content on Cozmo/Vector's procedural eyes or mood system was found. The GDC 2017 talk's content is paywalled (abstract only).
- Unverified search-snippet claims, not used as findings: Hanns Tappeiner's "Cozmo never gives you the same reaction twice", and the claim that pupils made Cozmo feel "too human" so they were removed. The source articles were not opened.
- No postmortem from Jibo, Inc. or Engineered Arts on expression-engine failures was found.

---

## Q6. Which ideas transfer to Frank (servo face, 25–50 Hz Python, orchestrator / synthesiser / animator)

### Takeaway
Copy Vector's layered animator pattern: one tagged base clip, named persistent procedural layers with per-channel combine rules, ramped layer removal, and keep-alive gated by clip ownership. Add a Vector-style mood store: five-ish dimensions, JSON decay graphs, named events with repetition penalties, collapsed to buckets for variant choice. Use Vector's animation-group resolver for LLM tags, Disney's subsumption levels and bandwidth limits, Jibo's tag timing semantics, and Reachy's single-writer loop with blend-back.

### Cited Findings
- Base clip plus layers with combine rules (Add / Multiply / Average / None, plus clip limits) and ramped layer removal. — [proceduralFace.cpp](https://github.com/digital-dream-labs/vector/blob/main/cannedAnimLib/proceduralFace/proceduralFace.cpp), [iTrackLayerManager.cpp](https://github.com/digital-dream-labs/vector/blob/main/animProcess/src/cozmoAnim/animation/trackLayerManagers/iTrackLayerManager.cpp)
- Keep-alive timers (blink 3–10 s, dart 1–2.25 s, focused dart range tiny) gated by "no streaming animation + 0.5 s"; layers ramp out over 3 ticks when a clip starts. — [faceLayerManager.cpp](https://github.com/digital-dream-labs/vector/blob/main/animProcess/src/cozmoAnim/animation/trackLayerManagers/faceLayerManager.cpp), [animationStreamer.cpp](https://github.com/digital-dream-labs/vector/blob/main/animProcess/src/cozmoAnim/animation/animationStreamer.cpp)
- Mood store: TimeRatio/ValueSlope decay graphs, event JSON with affectors and repetition penalty, SimpleMood thresholds (0.2 / 0.8 on Stimulated, −0.29 on Confident). — [mood_config.json](https://github.com/kercre123/victor/blob/snowboy/resources/config/engine/mood_config.json), [moodManager.cpp](https://github.com/kercre123/victor/blob/snowboy/engine/moodSystem/moodManager.cpp)
- Tag resolver: groups of (Name, Mood, Weight, CooldownTime_Sec), weighted random, Default fallback, closest-off-cooldown emergency pick. — [animationGroup.cpp](https://github.com/digital-dream-labs/vector/blob/main/engine/animations/animationGroup/animationGroup.cpp)
- Subsumption levels and motion bandwidth (lids 10 Hz, head ≤ 5 Hz, eyes lead), saccade timing 0.1–0.5 s, habituation equation. — [Pan et al. PDF](https://la.disneyresearch.com/wp-content/uploads/root.pdf)
- Tag timing semantics (blocking / bounded / unbounded, `endNeutral`, layer conflicts, auto-tags below explicit tags: BeatBlink, end-of-sentence Blink/DoubleBlink, Question posture). — [Jibo SDK ESML PDF](https://hri2024.jibo.media.mit.edu/attachments/SDK-SDK---ESML-121023-203758.pdf)
- Python control loop: single `set_target` writer thread, command queue, monotonic clock, hold last pose between moves, 0.3 s idle delay, 0.4 s blend-back after listening, speech sway from the loudness envelope with 0.2 s latency. — [moves.py](https://github.com/pollen-robotics/reachy_mini_conversation_app/blob/main/src/reachy_mini_conversation_app/moves.py), [speech_tapper.py @9f45935](https://github.com/pollen-robotics/reachy_mini_conversation_app/blob/9f459355883e5fb32f6894bf510db486e599ac78/src/reachy_mini_conversation_app/audio/speech_tapper.py)

### Inferences
- **Mapping to Frank's three parts:**
  - Orchestrator ≈ Vector HighLevelAI (states, get-in transitions, cooldowns, timers) + Jibo ESML tag semantics.
  - Synthesiser ≈ Vector MoodManager (decay graphs, events, repetition penalty, history buffer) + continuous outputs (like Vector's mood→audio RTPC and StimFace EMA) feeding layer gains.
  - Animator ≈ Vector AnimationStreamer + TrackLayerComponent, organised by Disney's subsumption levels: L0 neutral, L1 alive (blink, saccade, breathing-like brow drift), base performance clip, attention/gaze, speech (jaw, lips), overrides.
- **Frank-specific deviations:**
  - Blinks must be able to override lid aperture (Vector's lid Y was "None", i.e. not layerable).
  - Physical channels need slew-rate and acceleration limits per channel (Disney bandwidths) on top of combine rules.
  - At 25–50 Hz, Vector's 33 ms frame tables (blink 7 frames) resample cleanly at 30 Hz; at 50 Hz, interpolate.
- **Licence:** use Apache-2.0 Reachy and Expressive Furhat code freely, with attribution. Re-implement, do not copy, anything from the DDL or leaked Anki repos.

### Gaps
- No shipped system found has Frank's exact channel set (four lids, a four-servo brow, lips and mouth corners) with published per-channel combine rules. Disney used brows (2) and lids (2) but published no mouth or brow layering. The brow and mouth layering rules will need original design and testing.

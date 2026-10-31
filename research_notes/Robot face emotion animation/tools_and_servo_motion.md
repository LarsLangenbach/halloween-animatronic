# Tools, open-source code and servo-motion techniques for a real-time animatronic face engine (Frank)

Context for the report writer: Frank is a life-size talking head on hobby servos (MG90S / SG90 class). The servos are eyes (left/right, up/down), 4 lids, a 4-servo brow, a 2-servo jaw, 4 lips and 4 mouth corners, about 20 channels in all. A Python 3.12 laptop program streams "<pin> <angle>" lines over USB serial to a Raspberry Pi Pico (MicroPython) at 25-50 Hz, and a second Pico is reached over UART. Research date: 2026-10-30. Star counts and versions are as shown on the pages fetched that day.

## 1. Animatronic animation tools (Bottango, Will Cogley's code, VSA, show control, Blender-to-servo, Arduino/Python libraries, community projects)

### Takeaway
Bottango is the most reusable tool. Its drivers are BSD-3, the desktop app is free but beta under an EULA, and its serial protocol is published down to the command level, so it could author clips for Frank or talk to a custom Pico or Python driver. Blender Servo Animation (GPL-3.0) is the best Blender-to-servo pipeline, with a simple documented live-serial frame and JSON export. VSA is a closed, paid, Windows-only timeline tool and fits poorly. Cogley's public code has no stated licence, and his Patreon material must stay private.

### Cited Findings
**Bottango (desktop app plus open-source drivers)**
- Bottango describes itself as a "visual, 3D tool" for robot control that runs in real time, with keyframe animation and Bezier interpolation. It is hardware-agnostic, runs on Windows, macOS and Linux (mostly tested on Ubuntu), and is free to download but in beta under a Beta Software EULA. The docs warn against safety-critical use. — [Bottango docs: What is Bottango](https://docs.bottango.com)
- The driver repository (EvanBottango/Bottango) is under the BSD 3-Clause licence (Copyright 2026 Bottango LLC) and had 61 stars and 50 commits. It holds `BottangoArduinoDriver` (C++, Arduino framework, serial over USB, "the most basic and most supported route"), `BottangoNetworkedDriver` (a "fully functional" Python WebSocket driver example) and `REST_API_Examples` (Python). — [GitHub EvanBottango/Bottango](https://github.com/EvanBottango/Bottango)
- The docs (version 0.8.0b) split external control into three parts. The REST API lets your own scripts control the app. The "Bottango Protocol" is documented so you can write your own firmware. The Network Driver is a custom client, often used for inter-process communication. REST endpoints include GET /Animations/, GET and PUT /PlaybackState/, PUT /ControlInput/, GET /Animations/AnimationCommands/ and PUT /Stop/. — [Bottango docs: APIs and Comms](https://docs.bottango.com/apis-and-comms/)
- Protocol details:
  - Commands are ASCII lines ending in `\n`, with comma-separated parameters and a trailing hash `h<number>` for integrity. The exchange is call-and-response: Bottango waits for `OK` before it sends the next command.
  - Handshake: `hrq,<challenge>` is answered with `btngoHSK,<firmwareVersion>,<challenge>`. A `CUSTOMX` key such as `CUSTOM9` is accepted in place of the version.
  - Servo registration: `rSVPin,pin,minPWM,maxPWM,maxPWMChangePerSec,startPWM`. A custom motor: `rMTR,id,minSignal,maxSignal,maxChangePerSec,startSignal`.
  - Bezier curve: `upE,id,startTimeMS,durationMS,startPos,startTangentX,startTangentY,endPos,endTangentX,endTangentY`, with positions 0-8192. Instant move: `sCI,id,targetPos`.
  - Time sync: `tSYN,ms`. The desktop is the time authority and re-syncs every 30 s.
  - The firmware evaluates curves locally (`src/BezierCurve.cpp`). By default Bottango caches up to three curves ahead and sends curves due within one second.
  - The page labels some tangent parameters inconsistently. — [Bottango Protocol: Commands](https://docs.bottango.com/apis-and-comms/bottango-protocol/commands/)
- Supported boards: any Arduino-framework board "has a good chance, though not a guarantee". Named boards are the Uno R3 and Nano (up to 8 servos), the Mega (up to 16), ESP32 dev boards (the recommended custom-build choice), Bottango's own ESP32 control boards, and community reports of Teensy, Uno R4, MKR/Zero, ESP8266 and ESP32-S3. The Raspberry Pi Pico / RP2040 and MicroPython are not named. — [Bottango docs: Supported microcontrollers](https://docs.bottango.com/learn-bottango/hardware-drivers/supported-microcontrollers/)
- The REST API runs as a local HTTP server, toggled by "API Access". It can list, start and stop animations, set playback time, read every effector's live signal, and feed recorded live controller input. The docs warn that HTTP "adds overhead and can become a bottleneck" for streaming, and that a socket-based option is planned. — [Bottango docs: REST API](https://docs.bottango.com/learn-bottango/external-control/rest-api/)
- A PyPI package, `bottango_playback_interface`, wraps the Bottango Web API from Python (list animations, resume, read state, emergency stop). — [PyPI bottango-playback-interface](https://pypi.org/project/bottango-playback-interface)
- Bottango's 0.6.x documentation PDFs have chapters on Custom Motors, Custom Events (both need changes to the microcontroller code) and "implementing your own custom driver". — [Bottango Documentation v0.6.1 PDF](https://s3.us-west-1.amazonaws.com/bottango.com/version+0.6.1/Documentation/BottangoDocumentation.pdf)
- DigiKey's getting-started tutorial uploads `BottangoArduinoDriver.ino` to an Arduino from the Arduino IDE. — [DigiKey Maker.io: How to get started with Bottango](https://www.digikey.dk/en/maker/tutorials/2024/how-to-get-started-with-bottango)

**Blender-to-servo pipelines**
- Blender Servo Animation (timhendriks93) is GPL-3.0, with 86 stars and 249 commits. The current add-on needs Blender 4.2 or newer and installs as a Blender Extension.
  - Servos are armature bones, so constraints and IK work.
  - Live mode sends positions over serial (UART/USB) or a TCP WebSocket. Each serial frame is `<` (0x3C), servo ID, position high byte, position low byte, `>` (0x3E). Example: servo 0 at 375 is `0x00 0x01 0x77`. The author reports 16 servos at 60 fps "smoothly" at 115200 baud.
  - Exports: Arduino `.h`, `.json` (a list of positions) and `.bin` (for an SD card).
  - Per-servo settings: ID, position min/max (PCA9685 pulse units or degrees), neutral angle, rotation range, Euler axis, multiplier, reverse.
  - A per-frame "Threshold" plus "Position Jump Handling" (on by default) sends small steps when a jump exceeds the threshold. Calibration bypasses jump handling and can move servos at full speed.
  - No Python, MicroPython or Pico receiver is mentioned. — [GitHub timhendriks93/blender-servo-animation](https://github.com/timhendriks93/blender-servo-animation)
- A companion Arduino library plays exported animations and parses the live-mode stream. — [GitHub timhendriks93/blender-servo-animation-arduino](https://github.com/timhendriks93/blender-servo-animation-arduino)
- The add-on is also listed on the official Blender Extensions platform. — [extensions.blender.org: Servo Animation](https://extensions.blender.org/add-ons/servo-animation/versions/)
- Hanson Robotics used Blender shape keys to drive physical faces. `robo_blender` (an older ROS node) "gets mesh shapekeys and publishes them as pau2motors/pau" messages. Its README says it was superseded by the "Eva" architecture in `blender_api` and `blender_api_msgs`. — [hansonrobotics/robo_blender (mirror)](https://github.kxpsado.workers.dev/hansonrobotics/robo_blender); [relatedrepos: robo_blender](https://relatedrepos.com/gh/hansonrobotics/robo_blender)

**Visual Show Automation (Brookshire Software)**
- VSA is a Windows timeline program. Events set servo positions, relays and dimmers, and they line up against a displayed WAV/MP3 waveform for lip sync. Supported controllers include the Mini SSC II, Pontech SV203, Pololu, Parallax and Lynxmotion SSC-32. Editions are Hobbyist, Professional and Ultimate, with the Ultimate listed at $259.95. One review says VSA "may not provide enough control" for large shows, and a forum user reports no reply from Brookshire. — [roborobotics: Brookshire VSA](https://roborobotics.com/Animatronics/show-control-software/Brookshire-VSA.html); [RobotShop VSA Ultimate](https://robotshop.com/en/visual-show-automation-software-vsa-ultimate.html); [Light-O-Rama forum thread](https://forums.lightorama.com/topic/6902-servo-animation-software)

**Arduino servo-motion libraries (as design references)**
- ServoEasing (ArminJo) is GPL-3.0, with 386 stars and a commercial licence granted to one company in 2024.
  - Easings: linear, quadratic, cubic, quartic, sine, circular, back, elastic, bounce and "precision" (a small negative bounce to take up backlash), each as In, Out, InOut or Bouncing, plus user-defined curves.
  - Speed is set in degrees per second or as a move duration; the default is 5 deg/s.
  - All servos can be synchronised to stop together.
  - Non-blocking, interrupt-driven moves work on RP2040 under Arduino.
  - On a PCA9685 the resolution is about 0.5 deg (a 4.88 µs step). Digital servos have a deadband of about 5 µs (0.5 deg) that causes stutter at slow speeds.
  - The library does not know a servo's starting position, so the first move can be abrupt. — [GitHub ArminJo/ServoEasing](https://github.com/ArminJo/ServoEasing)
- Pololu Maestro servo controllers limit each channel's speed (units of 0.25 µs per 10 ms) and acceleration (units of 0.25 µs / 10 ms / 80 ms). Acceleration "ramps velocity rather than capping it". At start-up the output does not move smoothly because the controller has no record of the previous position. — [Pololu Maestro User's Guide 4.b](https://www.pololu.com/docs/0J40/4.b)

**Will Cogley's code**
- Cogley's free eye mechanism is on Instructables, with code, instructions and STLs to download. The search found no licence for the code. — [Instructables: Animatronic Eyes (Double and Single, 3D Printed, Compact, With Arduino)](https://www.instructables.com/Animatronic-Eyes-Double-and-Single-Fully-3D-Printe); [Make: Simple Animatronic Eyes](https://makezine.com/projects/simple-animatronic-eyes/)
- His original eye tutorial reads a joystick and buttons on an Arduino and drives servos through a 16-channel PCA9685 board with the Adafruit servo driver library. — [Gitee RV4Kids/Cogley_EyeMech](https://gitee.com/RV4Kids/Cogley_EyeMech)
- A third-party fork, Cogley_EyeMech (SyberxSpace on GitHub, mirrored on Gitee), adds "a more public-friendly remote" and simple automatic movement. It is C++ and marked MIT. — [Gitee RV4Kids/Cogley_EyeMech](https://gitee.com/RV4Kids/Cogley_EyeMech)
- Hackster reports that files for Cogley's "Coglet" companion bot (programmed in Python) are on GitHub "under an unspecified license". The article itself returned HTTP 403 when fetched, so this rests on the search snippet. — [Hackster: Will Cogley's Coglet](https://www.hackster.io/news/will-cogley-s-coglet-is-a-3d-printable-expressive-twin-camera-companion-bot-5cc02a04b718)
- Cogley keeps a public Notion site. — [willcogley.notion.site](https://willcogley.notion.site/)

**Community talking-head and emotion-face projects**
- A Make article on InMoov's facial expressions prompts an LLM with named servos and values 0-180 (neutral is all servos at 90), and the model picks an expression per reply. — [Make: Skin Deep, Evolving InMoov's Facial Expressions With AI](https://makezine.com/article/technology/robotics/skin-deep-evolving-inmoovs-facial-expressions-with-ai)
- MaidReal Head runs llama.cpp in a ROS2 node that decides movement as well as text, with eye, mouth and head servos, lip sync and gaze tracking. — [Devpost: MaidReal Head v1](https://devpost.com/software/maidreal-head-v1)
- Circuit Digest's "Skully" has an ESP32 receive LLM commands and drive eye, jaw and neck servos, with eye tracking. — [Circuit Digest: Animatronic Human-like Home Assistant (Skully)](https://circuitdigest.com/microcontroller-projects/animatronic-human-like-home-assistant-skully)
- Fritz is an open-source hackable head with 13 movable facial parts (not LLM-driven). — [RobotShop community: Fritz](https://community.robotshop.com/forum/t/fritz-a-robotic-puppet/5082)

### Inferences
- **Two ways to reuse Bottango.** These are inferences from the protocol docs and have not been tested.
  - (a) Bottango talks to a Python "networked driver" on the laptop that re-emits Frank's `<pin> <angle>` lines. This keeps the Pico firmware unchanged and lets an animator keyframe clips (blinks, brow raises, "Frank laughs") in Bottango's GUI.
  - (b) Implement the Bottango protocol in MicroPython on the Pico. The handshake accepts a `CUSTOMX` key, but the Pico would then have to evaluate Bezier curves itself.
  - Option (a) suits the existing architecture better. Bottango's `maxPWMChangePerSec` registration field is a ready-made per-joint velocity cap to copy.
- Bottango's REST API is HTTP-only for now. It suits triggering pre-made clips ("play animation X") from the emotion orchestrator, not 50 Hz streaming.
- **Blender Servo Animation's JSON export** (a list of positions per servo per frame) could be loaded by the Python engine as authored clips. The GPL-3.0 would bind code derived from the add-on, not the animation data it exports. That is a common reading, not legal advice. Its live-serial framing is simpler than Frank's ASCII lines but would need a new Pico parser.
- **Show-control pattern.** The VSA, Bottango and Blender tools all use the same pattern: a timeline of per-channel curves locked to an audio track. For Frank, the takeaway is to keep authored clips as timed curves keyed to audio time, not wall-clock time.
- **Licence risk with Cogley code.** No public Cogley code with an explicit licence turned up. The MIT label on the SyberxSpace fork belongs to the fork's author and does not establish Cogley's terms. Write Frank's eye and mouth control from scratch, and never commit or redistribute Patreon code.

### Gaps
- Disney / Garner Holt show-control specifics (protocols, products) were not researched in depth. I found no open-source material from them.
- The Bottango serial baud rate and the full network-driver message format were not on the pages fetched. The REST endpoint semantics (for example, whether PUT /ControlInput can set live motor positions) were not detailed.
- No confirmed Bottango support for RP2040 or MicroPython.
- Will Cogley's own GitHub account and licence terms could not be confirmed. The Coglet repo link was not retrieved.
- Last-commit dates for Blender Servo Animation, ServoEasing and Bottango were not shown on the fetched pages.

## 2. Robot-face and social-robot open source (Furhat, Blossom, Anki Vector/Cozmo, Reachy Mini, Poppy, InMoov, Hanson, ROS)

### Takeaway
Reachy Mini (Pollen Robotics / Hugging Face, Apache-2.0) is the most current and useful code to learn from. It offers named interpolation methods with min-jerk as the default, an Apache-2.0 library of 81 recorded emotion clips (JSON at 50 Hz plus audio), and a conversation app with a layered motion system: a queue of primary moves, speech-reactive head wobble blended on top, and face tracking. Anki's code is only partly public and stale. Hanson's and ROS face packages are effectively abandoned. Blossom is MIT but old (tested on Python 3.5). Furhat's gesture-frame format is a good schema to copy, but its SDK is commercial.

### Cited Findings
**Reachy Mini (Pollen Robotics / Hugging Face)**
- The SDK `pollen-robotics/reachy_mini` is Apache 2.0, with 1.6k stars and 3,027 commits. Hardware design files are CC BY-SA-NC. There are Python and JavaScript (WebRTC) SDKs. The Wireless version runs on a Raspberry Pi CM4 and the Lite version from a PC over USB. — [GitHub pollen-robotics/reachy_mini](https://github.com/pollen-robotics/reachy_mini)
- `goto_target(head=..., antennas=..., duration=..., method=InterpolationTechnique.MIN_JERK, body_yaw=...)` has `MIN_JERK` as its default method. The docs reference stable v1.9.0. — [Hugging Face docs: Reachy Mini API](https://huggingface.co/docs/reachy_mini/main/API/reachymini)
- Community API mirrors list the four methods as "linear", "minjerk", "ease_in_out" and "cartoon". One SDK guide calls MIN_JERK the "smoothest" and CARTOON an "exaggerated animation style". — [Seeed wiki: Reachy Mini API](https://wiki.seeedstudio.com/reachymini_api_reachymini/); [gary149 reachy-mini skill](https://cdn.jsdelivr.net/gh/gary149/reachy-mini-skill@main/SKILL.md)
- The emotions library is the Hugging Face dataset `pollen-robotics/reachy-mini-emotions-library`, under Apache-2.0. It has 81 moves, each a `<emotion>.json` trajectory (head pose, antennas, body yaw, sampled at 50 Hz) plus a mono Ogg/Opus sound of about 2-19 s. Examples: amazed1, anxiety1, attentive1, boredom1, cheerful1, fear1, laughing1, sad1, shy1. — [HF dataset: reachy-mini-emotions-library](https://huggingface.co/datasets/pollen-robotics/reachy-mini-emotions-library)
- Moves play by name with an initial goto duration. A separate `reachy_mini_dances_library` exists, and the `recorded_moves.py` example plays every move from a library. — [Seeed wiki: Reachy Mini dev guide for AI agents](https://wiki.seeedstudio.com/reachymini_agents/); [Seeed wiki: recorded moves example](https://wiki.seeedstudio.com/reachymini_examples_recorded_moves/)
- The conversation app `reachy_mini_conversation_app` is Apache 2.0, with 342 stars and 693 commits.
  - It uses a "layered motion system". A queue holds primary moves (dances, emotions, goto poses, breathing). Speech-reactive head wobble is blended on top, and a `head_tracking` tool follows the user's face.
  - While the listener detects speech, antennas freeze and idle motion stops.
  - Audio runs Silero VAD every 32 ms and plays in 20 ms chunks. The page does not state the motion-loop rate. — [GitHub pollen-robotics/reachy_mini_conversation_app](https://github.com/pollen-robotics/reachy_mini_conversation_app); [HF Space commit](https://huggingface.co/spaces/pollen-robotics/reachy_mini_conversation_app/commit/1acbcb348e7c6c7b4aba2f8d817338b1064011db)
- A community fork describes a "multi-frequency head wobble during speech". — [reachy-mlx-vlm README](https://git.ddq.nl/Pocket-science/reachy-mlx-vlm/raw/branch/main/README.md)

**Blossom (Cornell HRC2 / Google Creative Technologies)**
- `hrc2/blossom-public` is MIT, with 52 stars and 47 commits. The README says it was tested on Python 3.5.2 (Ubuntu 16.04, Mac).
  - Named "sequences" (for example `yes` and `no`) can be played or looped.
  - A phone app (`BlossomApp`) puppeteers the robot from the phone's pitch, yaw and roll, with a mirror toggle.
  - A browser editor (`blossom_blockly`) choreographs reactions. — [GitHub hrc2/blossom-public](https://github.com/hrc2/blossom-public)
- The founding paper is Suguitan and Hoffman, ACM THRI 2019. New behaviours can be defined "without requiring programming or computer animation skills", and parts cost under $250. — [Suguitan & Hoffman THRI 2019 (PDF)](https://hrc2.github.io/assets/pdfs/papers/SuguitanHoffmanTHRI19.pdf); [Cornell Chronicle](https://news.cornell.edu/node/311226)

**Anki Cozmo / Vector (Digital Dream Labs)**
- `digital-dream-labs/vector` is a "rolling release" of the main Vector robot code, with 119 stars and 11 commits. Its top-level folders include `animProcess`, `cannedAnimLib` and `engine`, and there is no assets folder. The README says the release continues "until all non-third-party licensed code is released". The page did not name the licence type. — [GitHub digital-dream-labs/vector](https://github.com/digital-dream-labs/vector)
- A third-party listing shows the repo's last push as 2022-05-28. — [ecosyste.ms: digital-dream-labs/vector](https://awesome.ecosyste.ms/projects/github.com%2Fdigital-dream-labs%2Fvector)
- DDL also open-sourced `vector-cloud` and `chipper` (the voice server). The community `wire-pod` builds on chipper. — [Anki Vector documentation: software repositories](https://randym32.github.io/Anki.Vector.Documentation/software-design/SDKs.html); [GitHub kercre123/wire-pod](https://github.com/kercre123/wire-pod)
- GDC 2017 had the talk "Cozmo: Animation Pipeline for a Physical Robot" (Daria Jerjomina, Molly Jameson). It covered moving Maya animation onto a robot with physical constraints. — [GDC Vault](https://gdcvault.com/play/1024221/Cozmo-Animation-Pipeline-for-a); [GDC news](https://gdconf.com/news/gdc-2017-get-animation-tips-folks-animated-actual-robot)
- Community documentation says Anki animated in Maya with a plugin that exported JSON, which the engine read through flatbuffers. — [Anki Vector docs: Animation tool](https://randym32.github.io/Anki.Vector.Documentation/tools/Animation%20tool.html)
- Cozmo's face is generated procedurally from 43 parameters (5 for the face, 19 per eye). — [PyCozmo docs: off-board functions](https://pycozmo.readthedocs.io/en/stable/external/offboard_functions.html)
- PyCozmo is a community pure-Python Cozmo library, not affiliated with Anki or DDL. — [ecosyste.ms: zayfod/pycozmo](https://awesome.ecosyste.ms/projects/github.com%2Fzayfod%2Fpycozmo)

**Furhat**
- `furhat-remote-api` (Python) accepts custom gestures as a dict whose frames each have a `time` list and a `params` dict (for example `BLINK_LEFT`), with class `furhatos.gestures.Gesture`. It also plays named gestures such as `BrowRaise`. — [PyPI furhat-remote-api 0.3](https://pypi.org/project/furhat-remote-api/0.3/)
- `furhat-realtime-api` offers sync and async clients with `request_gesture_start(name, intensity, duration, wait)`, `request_face_params(params)`, `request_face_headpose(yaw, pitch, roll, relative)` and `request_face_reset()`. The Realtime API is part of the paid FurhatAI subscription. — [PyPI furhat-realtime-api](https://pypi.org/project/furhat-realtime-api/); [Furhat Realtime API page](https://www.furhatrobotics.com/furhat-realtime-api)

**InMoov / MyRobotLab**
- InMoov scripts set jaw range and rest in the head script (for example `head.jaw.setMinMax(42,101)` with rest 42). A `MouthControl` service attaches to a speech service and moves the jaw during speech, with tweak settings such as `MouthControlJawdelaytimeletter`. Method names differ between MRL versions. — [MyRobotLab forum node 3497](https://myrobotlab.org/node/3497); [pyrobotlab InMoov3 script](https://github.com/MyRobotLab/pyrobotlab/blob/master/home/hairygael/InMoov3.Deep.AB.V9.py)

**Hanson Robotics and ROS**
- `blender_api_msgs` is the ROS interface to the `blender_api` head and body rig. `HEAD` is Hanson's integrated codebase, which includes a Blender model for facial expressions and supports only Ubuntu 14.04. — [ecosyste.ms: linas/blender_api_msgs](https://awesome.ecosyste.ms/projects/github.com%2Flinas%2Fblender_api_msgs); [GitHub yenat/HEAD (fork)](https://github.com/yenat/HEAD); [GitHub hansonrobotics/face_tools](https://github.com/hansonrobotics/face_tools)
- The ROS wiki page for `robot_face` says it is "Only released in EOL distros". — [ROS wiki: robot_face](https://wiki.ros.org/robot_face)

**PyLips (USC Interaction Lab)**
- PyLips is MIT, with 30 stars. It is "a Python-based interface for developing screen-based conversational agents": an animated face for TTS output, served by Flask on port 8000 and shown in a browser. It uses system TTS and downloads an Allosaurus model on first run. — [GitHub interaction-lab/PyLips](https://github.com/interaction-lab/PyLips)
- Its teleoperation tutorial maps MediaPipe blendshapes, including `jawOpen`, to facial action units with a weight per blendshape. — [PyLips docs: Teleoperate the Face](https://pylips.readthedocs.io/en/latest/tutorials/teleoperate.html)

**Philips iCat (academic pattern)**
- The iCat animation engine was built "to combine multiple interactive robot behaviors with believable robot animations". The demo speaks while tracking the user's head, lip-syncing, blinking and showing expressions. — [AAMAS 2005 demo: iCat](https://www.ifaamas.org/AAMAS/aamas05/demos/demo02.htm)
- A related van Breemen patent application notes that starting a second animation from neutral "may lead to delays and therefore less-interactive behaviour". An abrupt transition results if the first animation does not end where the second begins. — [US patent application 20070191986](https://uspto.report/patent/app/20070191986)
- The detailed paper is "Advanced Animation Engine for User-Interface Robots" (van Breemen and Xue, IROS 2006). — [dblp record](https://dblp1.uni-trier.de/rec/conf/iros/BreemenX06.html)

### Inferences
- **Architecture to copy: Reachy Mini's layers.** One primary clip at a time, secondary additive layers (speech wobble, breathing, gaze tracking) on top, and an idle layer suppressed while listening. This maps onto Frank's orchestrator, synthesiser and animator. The Apache-2.0 licence allows code reuse with attribution.
- The emotions dataset is a reference for clip length, sample rate (50 Hz, the top of Frank's 25-50 Hz stream) and naming, not for joint data. Its joints (head pose, antennas) do not match Frank's.
- **Gesture format to copy: Furhat.** Named gestures with intensity and duration, defined as timed frames of named parameters, make a good clip schema. Frank's parameters would be the abstract channels (`brow_inner_L`, `jaw_open`) rather than servo pins.
- **iCat lesson for clip transitions.** Never snap back to neutral between clips. Start each clip from the current pose, either by inertialization (see section 5) or by blending.
- Anki's `animProcess` source may be worth reading for streaming design, but the licence is unclear, it is C++ and it has been stale since 2022. Treat it as reading material, not reusable code.
- Hanson, ROS `robot_face` and Blossom are too old (Ubuntu 14.04, EOL ROS distros, Python 3.5) to install. Their ideas (Blender shape keys driving motors, phone puppeteering) still apply.

### Gaps
- Poppy / pypot licence and maintenance status were not confirmed. Only a forum statement that pypot's `goto_position` supports min-jerk (see section 5).
- Reachy Mini's CARTOON curve and its wobble algorithm (the `head_wobbler` module) are not documented on the fetched pages. The source tree was not opened.
- Furhat's full list of face parameter names was not retrieved.
- Last-commit dates for Blossom, PyLips and Reachy Mini were not visible.
- No primary Anki document confirmed the Maya-to-flatbuffers pipeline; that claim comes from community documentation.

## 3. Retargeting from human faces (MediaPipe blendshapes, ARKit / Live Link Face, OpenFace)

### Takeaway
MediaPipe Face Landmarker (Apache-2.0 code, Python, webcam LIVE_STREAM mode) gives 52 ARKit-style blendshape scores per frame and is the practical choice on a laptop. The mapping to servos (per-channel weights, ranges, mirroring) has to be written by hand, following the pattern of PyLips and hobby Arduino projects. The iPhone Live Link Face stream can be parsed in Python with a community deserializer. OpenFace gives action units but carries licence strings.

### Cited Findings
- **MediaPipe Face Landmarker.**
  - Outputs 478 3D landmarks, 52 blendshape scores and optional facial transformation matrices. Blendshapes and matrices are off by default.
  - Running modes are IMAGE, VIDEO and LIVE_STREAM. LIVE_STREAM delivers results asynchronously through a result listener.
  - The model bundle `face_landmarker.task` packs a BlazeFace detector, FaceMesh-V2 and the blendshape model. Python is supported.
  - Code samples are Apache 2.0.
  - Smoothing applies only when `num_faces` is 1. Left and right refer to the subject's face, so mirrored input swaps them. — [Google AI Edge: Face Landmarker](https://developers.google.com/edge/mediapipe/solutions/vision/face_landmarker)
- A tutorial shows enabling `output_face_blendshapes=True` with `face_landmarker_v2_with_blendshapes.task` and reading the scores per frame. — [Medium: MediaPipe blendshape coefficients visualization](https://medium.com/studio-neiro-ai/mediapipe-blendshape-coefficients-visualization-e01e6295c087)
- The full ARKit-style name list (eyeBlinkLeft ... jawOpen, mouthSmileLeft, browInnerUp, browOuterUpLeft, cheekPuff, noseSneerLeft, tongueOut and so on) is printed in Azure's blend-shape table. Azure adds headRoll, leftEyeRoll and rightEyeRoll for 55 in all. — [Microsoft Learn: viseme and blend shapes](https://learn.microsoft.com/en-us/azure/ai-services/speech-service/how-to-speech-synthesis-viseme)
- Kalidokit is a blendshape and kinematics solver for MediaPipe / TensorFlow.js face, eye, pose and hand tracking, aimed at avatars. — [gittrend: kalidokit](https://gittrend.io/repo/yeemachine/kalidokit)
- **Hobby hardware examples.**
  - A Fab Academy 2025 animatronic head tracks people with MediaPipe on a Raspberry Pi 5 and drives SG90/MG90S servos through a PCA9685 "to offload the processing and ensure reliable timing". — [Fab Academy 2025: Erwin Vivar final project](https://fabacademy.org/2025/labs/puebla/students/erwin-vivar/final-project.html)
  - An Instructables "Eye Tracking Animatronic Face" runs MediaPipe in Python and sends serial commands to an Arduino that drives the servos, including a mouth servo with set open and closed angles. — [Instructables: Eye Tracking Animatronic Face](https://www.instructables.com/Eye-Tracking-Animatronic-Face)
- PyLips maps MediaPipe blendshapes (including jawOpen) to facial action units with a weight per blendshape. — [PyLips docs: Teleoperate the Face](https://pylips.readthedocs.io/en/latest/tutorials/teleoperate.html)
- **Live Link Face (iPhone ARKit).**
  - The Python deserializer `livelink.py` binds UDP port 11111 and exposes blendshapes as a numpy array indexed by a `BlendShapes` enum. It was reverse-engineered from Unreal's `AppleARKitLiveLinkSource.cpp`. — [GitHub aelzeiny/Live-Link-Face-iPhone-App-Deserialization](https://www.github.com/aelzeiny/Live-Link-Face-iPhone-App-Deserialization)
  - The LLV project documents the packet: version byte, 16-byte frame time, blendshape count, 4-byte floats (up to 61 blendshapes), subject name and device ID. Frames are at most 774 bytes, so a 500-byte receive buffer can truncate. — [GitHub think-biq/LLV](https://www.github.com/think-biq/LLV)
- **OpenFace.**
  - Gives facial landmarks, head pose, action-unit recognition, eye gaze and aligned faces. It runs from "a simple webcam" and has 7.8k stars.
  - The page calls it "research code"; the README says it is still developed at CMU MultiComp Lab.
  - Licensing points to Copyright.txt and a separate commercial-licensing route, and users must respect the dlib, OpenBLAS and OpenCV licences. — [GitHub TadasBaltrusaitis/OpenFace](https://github.com/TadasBaltrusaitis/OpenFace)
- **1€ filter.** The standard filter for jittery tracking input is the 1€ filter (Casiez, Roussel and Vogel, CHI 2012), with an official Python package `OneEuroFilter`. A low cutoff cuts jitter at low speed, and the cutoff rises with speed to cut lag. Tuning: lower `mincutoff` for slow-speed jitter, raise `beta` for high-speed lag. The example defaults are mincutoff 1.0 Hz and beta 0.1, with dcutoff 1 Hz. — [GitHub casiez/OneEuroFilter](https://github.com/casiez/OneEuroFilter); [PyPI OneEuroFilter](https://pypi.org/project/OneEuroFilter)
- **Disney Research (no reusable code).** "Physical Face Cloning" (SIGGRAPH 2012) optimises synthetic skin design and actuation parameters to match a human's expressions on an animatronic. "Vibration-Minimizing Motion Retargeting for Robotic Characters" adjusts input motion to suppress visible low-frequency vibration. — [Disney Research: Physical Face Cloning](https://la.disneyresearch.com/publication/physical-face-cloning/); [Disney Research: Vibration-Minimizing Motion Retargeting](https://la.disneyresearch.com/publication/publication-process-vibration-minimizing-motion-retargeting-for-robotic-characters/)

### Inferences
- **Mapping to Frank.** A puppeteering mode for Frank would be:
  - MediaPipe LIVE_STREAM on a webcam.
  - A per-channel linear map with gains and offsets from blendshapes to abstract channels: `jawOpen` to jaw, `mouthSmileL/R` to corners, `browInnerUp` and `browOuterUpL/R` to brows, `eyeBlinkL/R` to lids, `eyeLook*` to gaze.
  - A 1€ filter per channel, then the same velocity and acceleration limiter as the autonomous path.
- Because blendshapes refer to the subject's left and right, decide explicitly whether puppeteering mirrors. The project's +x convention is the character's left.
- The 52 ARKit-style names are a sensible internal "face channel" vocabulary. Azure TTS blend shapes, Live Link Face and MediaPipe all use them, so any of these sources can drive the same retargeting table.
- Puppeteering can also record clips. Captured blendshape streams saved as timed curves could become authored emotion clips, the same idea as Reachy Mini's recorded emotions.
- Measure MediaPipe latency on the target laptop. It was not documented.

### Gaps
- No published MediaPipe-on-laptop latency figures were found.
- No open-source project was found that maps the full 52 blendshapes onto a multi-servo animatronic face (lips, corners, brows) with calibration. Only jaw and eye examples exist.
- OpenFace's exact licence text (academic or non-commercial) was not read. The ARKit / Live Link packet format has no official Epic documentation.

## 4. Lip-sync tools (Rhubarb, OVR LipSync, ElevenLabs and Azure timestamps, amplitude jaw followers)

### Takeaway
Three tiers fit Frank:
- **Amplitude follower.** ChatterPi / Scary Terry style: volume per chunk, optionally band-passed to 500-2500 Hz, sets jaw opening. It works with any audio, live.
- **TTS timing.** Azure gives 22 viseme IDs with 100 ns-tick audio offsets, or 55 ARKit-style blend shapes at 60 fps, from the Python SDK. ElevenLabs gives only character timings, which must be mapped to mouth shapes.
- **Offline viseme timing.** Rhubarb Lip Sync (MIT, file-based, English plus a phonetic mode).

Meta's OVR LipSync is end-of-life.

### Cited Findings
- **Rhubarb Lip Sync (DanielSWolf).**
  - Licence and project: MIT (bundled components are BSD, Boost and similar). About 2.7k stars and 510 commits. — [Rhubarb LICENSE.md](https://raw.githubusercontent.com/DanielSWolf/rhubarb-lip-sync/master/LICENSE.md); [GitHub DanielSWolf/rhubarb-lip-sync](https://github.com/DanielSWolf/rhubarb-lip-sync)
  - Mouth shapes: A closed (P/B/M), B slightly open with clenched teeth, C open (EH/AE), D wide open (AA), E slightly rounded (AO/ER), F puckered (UW/OW/W). The optional shapes are G (F/V), H (L) and X (idle).
  - Recognizers: PocketSphinx (English only) and phonetic (language-independent, less precise).
  - A `--dialogFile` text improves accuracy. Inputs are WAV or OGG; outputs are TSV (default), XML, JSON or DAT.
  - The README describes whole-file analysis. No streaming or real-time mode is documented. — [GitHub DanielSWolf/rhubarb-lip-sync](https://github.com/DanielSWolf/rhubarb-lip-sync)
  - Latest release v1.14.0 ("03 Apr"; the page did not show the year), after v1.13.0 and v1.12.0. The Windows build has been 64-bit since v1.11.0. — [Rhubarb releases](https://github.com/DanielSWolf/rhubarb-lip-sync/releases)
- **Meta OVR LipSync.** Meta's viseme reference (last updated April 17, 2026) says the Oculus Lipsync Plugin "is in end-of-life stage and will not receive further updates or support". The replacement is the Movement SDK, which gives the same 15 MPEG-4-derived visemes through the `XR_META_face_tracking_visemes` OpenXR extension. — [Meta developers: OVRLipSync viseme reference](https://developers.meta.com/horizon/documentation/unreal/audio-ovrlipsync-viseme-reference/)
- **Azure Speech TTS.**
  - 22 viseme IDs (0 is silence, 21 is p/b/m). Each comes with an `Audio offset` in ticks of 100 ns.
  - Blend-shape output is a JSON matrix of frames at 60 fps, each with 55 facial positions (0-1) in a fixed order. Groups of frames should be rendered "immediately before the corresponding audio chunk".
  - Python SDK: `speech_synthesizer.viseme_received.connect(cb)`, with `evt.audio_offset`, `evt.viseme_id` and `evt.animation`. SVG output is en-US only.
  - Page dated 2026-02-25. — [Microsoft Learn: Get facial position with viseme](https://learn.microsoft.com/en-us/azure/ai-services/speech-service/how-to-speech-synthesis-viseme)
- **ElevenLabs.** `POST /v1/text-to-speech/{voice_id}/stream/with-timestamps` streams chunks containing `audio_base64`, plus `alignment` and `normalized_alignment` objects with `characters`, `character_start_times_seconds` and `character_end_times_seconds`. The page does not mention visemes. — [ElevenLabs API: Stream with timestamps](https://elevenlabs.io/docs/api-reference/text-to-speech/stream-with-timestamps)
  - Conflict: a third-party provider summary gives field names in milliseconds (`char_start_times_ms`). The official page uses seconds. — [Bifrost docs: ElevenLabs](https://docs.getbifrost.ai/providers/supported-providers/elevenlabs.md)
  - A third-party guide claims Azure is "the only major provider" with timestamped viseme IDs and uses a rough letter-to-viseme table for ElevenLabs. This is a secondary, possibly dated claim. — [OpenHuman TTS / lip-sync guide](https://humandeveloper.pages.dev/tts-lipsync-integration)
  - Inworld's docs warn that in some modes timestamps can arrive after their audio. — [Inworld TTS timestamps](https://docs.inworld.ai/tts/capabilities/timestamps.md)
- **ChatterPi (ViennaMike).** Python 3 software that turns a Raspberry Pi into an audio servo controller from a WAV file or a live mic or line input.
  - Per chunk, a callback computes the average volume. Thresholds in config.ini set jaw levels, so louder audio opens the jaw further.
  - STYLE 2 applies a SciPy band-pass removing content below 500 Hz and above 2500 Hz. Stereo channels are analysed separately.
  - It uses pigpio DMA-timed PWM because software PWM "is not precise enough for servos". A USB sound card is recommended because the Pi's audio jack conflicts with PWM timing.
  - Article dated 2021-09-09; the licence is not named on the page. — [Hackaday.io: ChatterPi](https://hackaday.io/project/181612-chatterpi/details); [GitHub ViennaMike/ChatterPi](https://github.com/ViennaMike/ChatterPi)
- **Scary Terry / Cowlacious ST-400.** A modified servo-tester circuit that turns audio into jaw servo commands while passing the audio through. Its setup tunes a level pot and a "Jaw Min" pot so the jaw closes to rest in silence. One builder quotes $60 for a completed board. — [Cowlacious ST-400 manual](https://manuals.online/cowlacious-designs/servo-drive/scary-terry-st-400/user-manual/1ekj2); [Instructables: Automated Talking Skull](https://www.instructables.com/Automated-Talking-Skull)
- Forum users name ChatterPi and an Arduino "Jawduino" as open alternatives. — [Synthiam: alternative to the Scary Terry board](https://synthiam.com/Community/Questions/alternative-to-the-Scary-Terry-sound-board-to-drive-a-jaw-18851)
- The Yorick Project is another open talking-skull build by the ChatterPi author. — [Hackster: The Yorick Project](https://www.hackster.io/ViennaMike/the-yorick-project-f9bac7)
- InMoov / MyRobotLab's `MouthControl` drives the jaw from the speech service, with per-letter delay tweaks. — [MyRobotLab forum node 3497](https://myrobotlab.org/node/3497)

### Inferences
- **Hybrid for Frank.** The amplitude envelope (band-passed 500-2500 Hz as in ChatterPi) drives the jaw for energy, while viseme or character timing drives lip and corner shapes (rounding for F/UW, closure for P/B/M, stretch for EE). Lips and corners are what an amplitude follower cannot do, and Frank has 8 servos there.
- **With Azure TTS.** The 55 blend-shape frames at 60 fps can feed the same ARKit-name retargeting table as MediaPipe (section 3), so one mapping serves puppeteering and speech.
- **With ElevenLabs.** Convert characters to phonemes, phonemes to a Rhubarb-like A-F/X set, then shapes to channel targets. Smooth the result with springs (section 5), because character timings make step changes.
- **Rhubarb is file-based.** It suits pre-rendered lines (a canned Halloween greeting) or clip authoring, not low-latency conversation unless each TTS utterance is fully generated first.
- **Timing source.** Schedule mouth events from audio-device time, not from when the TTS chunk arrived (see section 5). Sources warn that timestamps can lag audio.

### Gaps
- No published comparison of lip-sync accuracy for amplitude, viseme and Rhubarb methods on physical servos.
- Whether ElevenLabs' WebSocket API also returns alignment was not confirmed from official docs.
- ChatterPi's exact thresholds and level counts and its licence were not on the fetched page.
- Azure's per-locale viseme support beyond en-US was not checked.

## 5. Motion smoothing and servo control for expressive motion at 25-50 Hz (springs, minimum jerk, easing, slew limits, jitter and hum, brown-outs, per-joint limits, latency)

### Takeaway
Use frame-rate-independent, half-life-parameterised critically damped springs (Daniel Holden's "Spring-It-On") as the per-channel smoother. Put velocity and acceleration caps per joint in front of them (Pololu Maestro / Bottango `maxPWMChangePerSec` style). Use min-jerk curves (Reachy Mini's default) for deliberate point-to-point gestures. Use inertialization to blend between clips without snapping.

On the hardware side:
- Expect deadband stutter on slow moves, holding hum under load, and current spikes that brown out the logic. MG90S stall current is 0.7 A per the datasheet but up to 1.2-1.6 A by vendor estimates.
- On the Pico, `duty_u16(0)` releases one servo, but `deinit()` kills both channels of a PWM slice.
- On Windows, Python 3.11+ `time.sleep` uses a high-resolution timer, so a 50 Hz loop is feasible. Measure jitter anyway.

### Cited Findings
**Springs and damping (Daniel Holden, "Spring-It-On: The Game Developer's Spring-Roll-Call", dated 04/03/2021)**
- `lerp(x, g, factor*dt)` depends on frame rate and goes unstable when `damping*dt > 1`. The exact, frame-rate-independent damper is `lerp(x, g, 1 - exp(-(ln2*dt)/(halflife+eps)))`; a fast approximation `fast_negexp` can replace `exp`. — [theorangeduck.com: Spring-It-On](https://theorangeduck.com/page/spring-roll-call)
- `spring_damper_exact` solves the under-, critically and over-damped cases analytically (parameters: frequency and halflife, or damping ratio). `critical_spring_damper_exact` is preferred for most uses: no oscillation, fewer parameters, fast. Simpler versions exist for zero goal velocity and zero goal position. — [theorangeduck.com: Spring-It-On](https://theorangeduck.com/page/spring-roll-call)
- Variants from the same article:
  - Timed springs reach the goal at roughly a requested time by tracking a lerp offset by `halflife/ln2` of lag.
  - Velocity springs track a target that moves at a fixed speed.
  - Double springs (two chained at half the half-life) give an S-curve.
  - Springs can smooth any noisy real-time signal, with the half-life trading smoothness against responsiveness. — [theorangeduck.com: Spring-It-On](https://theorangeduck.com/page/spring-roll-call)
- Inertialization records the offset between source and destination animation at a transition and decays it with `decay_spring_damper_exact`. One shared half-life and dt can serve many joints. — [theorangeduck.com: Spring-It-On](https://theorangeduck.com/page/spring-roll-call)
- Practical tips from the article: tune by half-life, not raw stiffness and damping; precompute values shared by channels with the same half-life and dt; guard divisions with a small epsilon (about 1e-5). — [theorangeduck.com: Spring-It-On](https://theorangeduck.com/page/spring-roll-call)
- The companion repo `orangeduck/Spring-It-On` (C, raylib demos) has 155 stars and 14 commits. It has a LICENSE file whose type was not shown. — [GitHub orangeduck/Spring-It-On](https://github.com/orangeduck/Spring-It-On)
- Unreal Engine's `FCriticalDamper` is documented as converging "as fast as possible towards its state of equilibrium without overshooting and/or oscillating", which shows the technique is standard in production engines. — [Unreal Engine API: FCriticalDamper](https://dev.epicgames.com/documentation/unreal-engine/API/Plugins/GameplayCameras/FCriticalDamper)

**Minimum-jerk and easing**
- The minimum-jerk trajectory between two points is a fifth-degree polynomial with zero velocity and acceleration at both ends (Flash and Hogan 1985). — [Duarte, "The minimum jerk hypothesis" notebook](https://nbviewer.jupyter.org/github/demotu/BMC/blob/master/notebooks/MinimumJerkHypothesis.ipynb); [Flash & Hogan 1985 (PDF)](https://newmanlab-mit-edu.ezproxyberklee.flo.org/wp-content/uploads/2017/09/1985-the-coordination-of-arm-movements-an-experimentally-confirmed-mathematical-model.pdf)
- For a minimum-jerk profile the peak-to-average speed ratio is 1.875. Human reaching measures about 1.75. — [Wada & Kaneko 2001 (PDF)](https://bicr.atr.jp/~osu/pdf/WadaKaneko_NN2001.pdf)
- The minimum-jerk model was defined on endpoint (hand) coordinates, not joint angles. — [core.ac.uk PDF](https://core.ac.uk/download/83695829.pdf)
- Online (re-plannable) minimum-jerk trajectory generation is covered by Ghazaei Ardakani, Robertsson and Johansson. — [Online Minimum Jerk Trajectory Generation (PDF)](https://cdn.ima.org.uk/wp/wp-content/uploads/2017/12/Ghazaei-Ardakani-Robertsson-Johansson-Online-Minimum-Jerk-Trajectory-Generation.pdf)
- pypot (Poppy) supports `goto_behavior = 'minjerk'` per motor. A forum user found the duration had no effect in V-REP, and the maintainer said it only sets goal position. — [Poppy forum](https://poppy.discourse.group/t/howto-connect-pypot-to-your-simulated-version-of-a-poppy-humanoid-in-v-rep/332); [Poppy notebook](https://nbviewer.jupyter.org/github/jjehl/poppy_education/blob/master/poppy-4dof-arm-mini/poppy-4dof-arm-mini_speed_and_%20position.ipynb)
- `py-min-jerk` is a Python port of Todorov's MATLAB fifth-order spline minimum-jerk generator. — [GitHub dkebude/py-min-jerk](https://github.com/dkebude/py-min-jerk)
- Reachy Mini's `goto_target` defaults to MIN_JERK and also offers linear, ease_in_out and cartoon. — [Hugging Face docs: Reachy Mini API](https://huggingface.co/docs/reachy_mini/main/API/reachymini)

**Velocity and acceleration limits, jump handling**
- Pololu Maestro: per-channel speed in 0.25 µs per 10 ms (speed 4 is 100 µs/s), and acceleration in 0.25 µs / 10 ms / 80 ms (acceleration 4 lets speed change by up to 1250 µs/s each second). — [Pololu Maestro guide 4.b](https://www.pololu.com/docs/0J40/4.b)
- Bottango registers each servo with `maxPWMChangePerSec`. — [Bottango Protocol: Commands](https://docs.bottango.com/apis-and-comms/bottango-protocol/commands/)
- Blender Servo Animation has a per-frame "Threshold" and "Position Jump Handling" that turns large jumps into small steps. — [GitHub timhendriks93/blender-servo-animation](https://github.com/timhendriks93/blender-servo-animation)
- ServoEasing works in degrees per second (default 5 deg/s) and can synchronise multi-servo moves to finish together. — [GitHub ArminJo/ServoEasing](https://github.com/ArminJo/ServoEasing)

**Jitter, hum and detaching**
- Digital servos have a deadband of about 5 µs (about 0.5 deg) that causes stutter on slow moves, and a PCA9685 makes it worse. Interrupt-blocking libraries can cause twitching. A detached servo gets no signal, stays LOW and can be moved by hand. — [GitHub ArminJo/ServoEasing](https://github.com/ArminJo/ServoEasing)
- A servo holding against a load hums as it makes micro-corrections. Stopping the pulses usually silences it but drops holding torque; some servos go limp, others drift. — [Electric Imp forum: Servo Buzz](https://forums.electricimp.com/t/servo-buzz/2012); [Synthiam: constant servo noise](https://synthiam.com/Community/Questions/Motor-Gripper-Constant-Servo-Noise-2797)
- A buzz before the servo reaches its target signals binding or stall. Low-authority blog, treat as indicative. — [maker-questions-daily blog](https://maker-questions-daily.blogspot.com/2026/01/why-do-my-servos-buzz-loudly-even-when_01725927998.html)
- PCA9685 users ask about deactivating channels to stop holding. — [Arduino forum: Servo deactivation on PCA9685](https://forum.arduino.cc/t/servo-deactivation-on-pca9685/1278849)

**Raspberry Pi Pico / MicroPython**
- The RP2 has 8 PWM slices, each with two channels (16 in all), on adjacent even/odd GPIO pairs. Both channels of a slice share one frequency but have separate duties.
- `duty_u16(0)` stops output on that channel. `deinit()` turns off the whole slice (both channels).
- Two UARTs: UART0 on GPIO 0/1, 12/13 or 16/17; UART1 on GPIO 4/5 or 8/9. Changing `machine.freq()` changes the baud of existing UARTs.
- Timer callbacks run as soft IRQs by default. `hard=True` reduces jitter but has restrictions. — [MicroPython docs: rp2 quick reference](https://docs.micropython.org/en/latest/rp2/quickref.html)
- `duty_ns` sets the pulse width in nanoseconds regardless of frequency, which is convenient for servo pulses. Community source. — [Wokwi project](https://wokwi.com/projects/450061348999397377)
- Guides disagree on the duty_u16 endpoint values for 0.5-2.5 ms pulses. — [circuitdigest: Pico servo PWM](https://circuitdigest.com/microcontroller-projects/control-a-servo-motor-with-raspberry-pi-pico-using-pwm-in-micropython); [microcontrollerslab: Pico servo](https://microcontrollerslab.com/servo-motor-raspberry-pi-pico-micropython/)

**Power and brown-outs**
- Servo current spikes can reset the microcontroller (brown-out). Guides advise an external 5 V supply with a common ground for multiple servos and a capacitor (about 100 µF) near the servos. — [luisllamas: MicroPython servomotors](https://www.luisllamas.es/en/micropython-servomotors-pwm/); [SunFounder: py_servo](https://docs.sunfounder.com/projects/newton-lab-kit/en/latest/pyproject/py_servo.html); [tech-18g blog (low authority)](https://tech-18g.pages.dev/blogs/raspberry-pi-pico/how-to-control-a-servo-motor-with-raspberry-pi-pico-using-micropython-complete-guide/)
- MG90S stall current: 700 mA in a datasheet-style sheet. — [TinyTronics MG90S datasheet](https://www.tinytronics.nl/product_files/000263_Data_Sheet_of_MG90S_Analog_Servo_Motor.pdf)
  - Conflict: a servo vendor's blog estimates 700-1,000 mA at 4.8 V and 1,200-1,600 mA "or more" at 6.0 V. These are vendor estimates, not manufacturer specs. — [Kpower: MG90S current draw](https://www.kpower.com/insight_bldc/7870.html)
- Torque is quoted at 1.8 kg-cm at 4.8 V and about 2.2 kg-cm at 6 V. — [components101: MG90S](https://components101.com/motors/mg90s-metal-gear-servo-motor)

**Laptop timing and latency compensation**
- Python 3.11 changed `time.sleep()` on Windows to use `CREATE_WAITABLE_TIMER_HIGH_RESOLUTION` where available. The release notes say best resolution went from 1 ms (3.10) to under 1 ms. — [python-checkins bpo-45429](https://www.python.org/pipermail/python-checkins/2021-November/173356.html); [issue 45429](https://www.python.org/pipermail/new-bugs-announce/2021-October/044192.html)
  - Conflict: a Stack Overflow report on 3.11.4 / Windows 11 still sees about 0.5 ms steps, and the earlier implementation was around 15.6 ms. — [Stack Overflow archive: Python 3.11 poor time.sleep resolution on Windows](https://kiwix.lema.org/stackoverflow.com_en_all_2023-11/questions/76506785/python-3-11-poor-time-sleep-resolution-on-windows); [discuss.python.org: higher resolution timers on Windows](https://discuss.python.org/t/higher-resolution-timers-on-windows/16153)
- In `python-sounddevice`, the stream callback receives `outputBufferDacTime` and `currentTime` in the stream's time base, and `stream.latency` reports actual latency. One user found ADC time returned 0 and latency drifted between runs, so they measured it. — [python-sounddevice: Streams](https://python-sounddevice.readthedocs.io/api/streams.html); [Stack Overflow archive: inputBufferAdcTime returns 0](https://kiwix.lema.org/stackoverflow.com_en_all_2023-11/questions/52283147/python-sounddevice-callback-time-inputbufferadctime-returns-0)
- Azure says to render each blend-shape frame group "immediately before the corresponding audio chunk". — [Microsoft Learn: viseme](https://learn.microsoft.com/en-us/azure/ai-services/speech-service/how-to-speech-synthesis-viseme)
- Bottango makes the desktop the time authority (`tSYN`, every 30 s) and sends curves up to 1 s ahead for the device to evaluate locally. — [Bottango Protocol: Commands](https://docs.bottango.com/apis-and-comms/bottango-protocol/commands/)

### Inferences
- **Proposed per-channel pipeline** for Frank's animator at 50 Hz, my synthesis of the sources above:
  1. Target from orchestrator, clip or lip sync.
  2. Clamp to the joint's soft limits.
  3. `critical_spring_damper_exact` with a per-joint half-life (short for lids and blinks, longer for brows and eyes' slow drift).
  4. Velocity and acceleration clamp per joint (Maestro-style).
  5. Quantise to whole or 0.5 deg.
  6. Send only if the change exceeds a deadband (about 0.5 deg) to avoid stutter and serial traffic.
- **Inertialization for clip transitions** avoids iCat's "return to neutral" delay and the snap Pololu and ServoEasing warn about.
- **Normalised min-jerk ease.** The standard normalised form is s(t) = 10t^3 - 15t^4 + 6t^5. It follows from the boundary conditions above; this is from general knowledge, and the sources fetched did not print it. It gives Reachy-style deliberate gestures (head nods, eye saccade returns) with a fixed duration.
- **Saccades.** Real eyes make fast saccades followed by fixation. A very short half-life or a near-instant step for eye targets, with smoothing only on micro-drift, is likely more lifelike than heavy smoothing. This is an animation-practice inference, not sourced here.
- **Idle release on the Pico.** Since `deinit()` stops both channels of a slice, release an idle servo with `duty_u16(0)` (or `duty_ns(0)`), never `deinit()`. Only release joints that hold position unpowered under the silicone skin's load. Lids and jaw under skin tension may drift. Re-attaching must start from the last commanded angle to avoid a jump.
- **Current budget.** About 20 servos at 0.7 A datasheet stall (up to 1.6 A by vendor estimate at 6 V) gives a worst-case total of roughly 14-32 A if all stall together. That argues for the servo rail being separate from the Picos' logic supply, bulk capacitance near the servo headers, and staggering big simultaneous moves. The project's power design docs (a 20 A buck) should be checked against this.
- **Serial stream.** At 50 Hz, about 20 channels of `<pin> <angle>\n` (about 8 bytes each) is about 8 kB/s, well within USB CDC. Sending only changed channels keeps it smaller. Bottango-style "curves ahead" streaming would also let the Pico smooth between packets if the laptop stalls.
- **Latency compensation.** Lead servo commands ahead of the audio clock by the measured audio output latency plus servo mechanical lag. Servo lag was not sourced here; measure it with a phone slow-motion video. Calibrate the lead once and store it in config.

### Gaps
- No measured end-to-end latency figures for hobby servos (command to visible motion) were found.
- No authoritative MG90S current figures from TowerPro were found; the values conflict, as noted.
- The licence of the Spring-It-On demo code was not confirmed.
- No sources were found on brown-out behaviour specific to the RP2040, or on hard-IRQ PWM updates in MicroPython for servo smoothing on-device.

## 6. Python libraries useful for the engine (tweening, noise, behaviour trees, state machines, real-time scheduling)

### Takeaway
All the candidate libraries are permissively licensed and pure Python, so they work on Windows and macOS. py_trees (BSD-3, v2.6.0, September 2026) is actively maintained. transitions (MIT, v0.9.3, July 2025) is maintained and has hierarchical, async and timeout features. pytweening (MIT, v1.2.0, February 2024) and opensimplex (MIT, v0.4.5.1, May 2024) are small and stable but not recently released. The spring and min-jerk maths is short enough to write in-house from Holden's article.

### Cited Findings
- py_trees: latest 2.6.0 (Sep 10, 2026), BSD-3-Clause, badges list Python 3.10, 3.12 and 3.14; "pythonic implementation of behaviour trees". — [PyPI py-trees](https://pypi.org/project/py-trees/)
- transitions: latest 0.9.3 (July 2, 2025), MIT, classifiers to Python 3.13; "a lightweight, object-oriented Python state machine implementation". Extensions:
  - `HierarchicalMachine` (nested and parallel states)
  - `AsyncMachine` and `AsyncTimeout`
  - timeout states
  - `GraphMachine` diagrams (Mermaid, Graphviz)
  - `LockedMachine` (thread-safe). — [PyPI transitions](https://pypi.org/project/transitions/)
- opensimplex: latest 0.4.5.1 (May 1, 2024), MIT (the original algorithm was public domain by Kurt Spencer), Python 3.8 or newer. Has NumPy array functions `noise2array`, `noise3array` and `noise4array`; Numba acceleration is optional and untested. — [PyPI opensimplex](https://pypi.org/project/opensimplex/)
- pytweening: latest 1.2.0 (Feb 20, 2024), MIT. 34 easing functions: linear, plus quad, cubic, quart, quint, sine, expo, circ, elastic, back, bounce and poly, each in In, Out and InOut forms. — [PyPI pytweening](https://pypi.org/project/pytweening/)
- OneEuroFilter: official Python implementation of the 1€ filter on PyPI. — [PyPI OneEuroFilter](https://pypi.org/project/OneEuroFilter); [GitHub casiez/OneEuroFilter](https://github.com/casiez/OneEuroFilter)
- py-min-jerk: Python minimum-jerk generator. — [GitHub dkebude/py-min-jerk](https://github.com/dkebude/py-min-jerk)
- reachy_mini (Apache 2.0) contains Python implementations of linear, minjerk, ease_in_out and cartoon interpolation to study or adapt. — [GitHub pollen-robotics/reachy_mini](https://github.com/pollen-robotics/reachy_mini); [Hugging Face docs: Reachy Mini API](https://huggingface.co/docs/reachy_mini/main/API/reachymini)
- Bottango ships Python examples for its REST API and a Python WebSocket networked driver (BSD-3). — [GitHub EvanBottango/Bottango](https://github.com/EvanBottango/Bottango)
- Azure Speech SDK for Python exposes `viseme_received`. — [Microsoft Learn: viseme](https://learn.microsoft.com/en-us/azure/ai-services/speech-service/how-to-speech-synthesis-viseme)
- `python-sounddevice` exposes DAC timestamps and stream latency for audio-clock sync. — [python-sounddevice: Streams](https://python-sounddevice.readthedocs.io/api/streams.html)
- Windows timing: Python 3.11+ `time.sleep()` uses a high-resolution waitable timer when the OS supports it. Observed granularity is still about 0.5 ms on one Windows 11 machine. — [python-checkins bpo-45429](https://www.python.org/pipermail/python-checkins/2021-November/173356.html); [Stack Overflow archive](https://kiwix.lema.org/stackoverflow.com_en_all_2023-11/questions/76506785/python-3-11-poor-time-sleep-resolution-on-windows)

### Inferences
- **Suggested mapping** onto Frank's three engine layers:
  - transitions (hierarchical) for the orchestrator's conversational states (idle, listening, thinking, speaking, reacting).
  - py_trees if behaviour selection grows (gaze targets, idle fidgets, boredom).
  - opensimplex `noise2` sampled along time for low-amplitude "alive" drift on brows, eyes and lids, layered additively before the spring stage.
  - pytweening or a hand-written min-jerk for authored gesture shapes.
  - Holden's critical spring, about 20 lines of Python, as the final smoother.
  - OneEuroFilter for any tracked input (MediaPipe, Live Link).
- **Loop scheduling.** Run the 50 Hz animator on a fixed-timestep loop driven by `time.perf_counter()` deadlines, sleeping until the next tick, not `sleep(0.02)` drift. Feed the measured dt into the frame-rate-independent springs so jitter in the laptop loop does not change motion speed. This follows from Holden's dt-exact formulation and the Windows timer findings.
- Python 3.12 (the project venv) has the 3.11 high-resolution sleep on Windows. macOS sleep granularity was not researched.
- **Caution:** pytweening and opensimplex have had no release since 2024. They are small and stable but effectively feature-frozen. Vendoring the few functions needed is low-risk.

### Gaps
- macOS-specific timer behaviour and real-time thread priority options for Python were not researched.
- No benchmark was found of pyserial write latency to a Pico's USB CDC at 50 Hz.
- No dedicated, maintained Python "animatronic animation engine" library was found that combines clips, layering, lip sync and servo output. The closest whole systems are Reachy Mini's SDK and conversation app (robot-specific) and Bottango (a GUI app plus drivers).

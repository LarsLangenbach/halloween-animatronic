# perform: the body layer and the digital twin

The part of the performance engine that sits between a character's brain and its servos, for
any of our robots. Frank is the first robot on it (`robots/frank/`). PLAN D32.

```
 brain + face engine          body server (perform/body.py)                 the robot
 (frank/chat.py, web.py,  ─►  one owner of the serial port(s)          ─►   Board 1 (mouth) ─► Board 2 (eyes, brows)
  frank/engine, sliders,      ├─ every program's lines, whole, in order
  play.py ...)                ├─ a model of each board's program (boards.py): clamps, glide, jaw, link
  socket://127.0.0.1:8811     ├─ each servo's travel time (robot.json)
                              ├─ --record: every line, timed (a performance you can replay)
                              └─ /events, 30 a second ─► the twin page (http://localhost:8810)
                                                         the CAD head moving through its linkages
```

The twin shows what the robot has been told to do and how far each servo has got by now. No
board reports a servo's real position (the eye board sends nothing back), so the twin follows
the commands through the same rules the board programs apply. When the two disagree, either
the calibration is off or the body didn't do what it was told (a stalled servo, a dead link
wire, a board that reset), and that's worth knowing.

## Run it (Mac, at the show)

```
# 1. the body server, on the mouth board's port (or --sim with no head: the twin is the body)
uv run --no-project --with pyserial python perform/body.py robots/frank/robot.json --port /dev/cu.usbmodem2101

# 2. Frank, through it
uv run --no-project ... python frank/web.py --mouth socket://127.0.0.1:8811     (the usual --with list, plus pyserial)

# 3. the twin: open http://localhost:8810
```

The slider windows work through it too, at the same time as Frank:
`firmware/servo_controls.py socket://127.0.0.1:8811 --link` and
`firmware/mouth_controls.py socket://127.0.0.1:8811`. (servo_controls.py resets the board it
opens, as it always has, so start it before Frank, not during a show.) A program that only
takes a device path gets a virtual port with `--pty 1` (macOS, Linux).

- `--record perf.jsonl` keeps every line with its time and sender. `perform/play.py perf.jsonl`
  plays it back: into `--sim` to watch it, or onto the head.
- `--sim`: no board. The models answer the way the boards do (the mouth board's `Received:`
  echo, its `where`, its start-up line), so `frank/mouth.py --test`, the engine and the slider
  windows all run against the twin alone.
- The body server works out which program the mouth board runs from what it says
  (`Received:` echoes mean `cogley_mouth_main.py`; silence means `pico_servo_ctl.py`) and
  says so on the page.

## The page

- **Servos**: one row per servo, by board. Blue tick = the pulse the board sends now; yellow =
  where the horn has got to at the servo's own speed. Green dot = powered; grey = loose.
- **Click a part** to see what it is and which servo moves it (that servo gets selected).
- **Calibration** (a selected servo): `zero` is the angle, in the board program's own degrees, at
  which the part sits as in the CAD; `direction` flips if a horn turns the other way. Move the
  real servo (slider window or Frank), change zero until the twin's part matches the real one,
  then Save. It writes into `robots/frank/robot.json`.
- **Red parts and "can't reach"**: the linkage can't get where the servo is driving it. On the
  real head that servo is stalled against its own mechanism: back the angle off.
- **Gaze rays** (yellow) from each eye, and the **webcam** (blue frustum, from `frank/camera.json`),
  at true size in the head's frame: where he looks and what he sees, in the same space.
- Layers: the mechanism; Cogley's shell; the face mask (it doesn't move); the enclosure.
- **Hero view** `http://127.0.0.1:8810/?hero=1`: the moving head alone, full-bleed, looked at square on
  from a little below his eyes, swaying gently side to side (`&spin=0` holds it still), with only a
  connection dot. Made for an iframe (the engine's preview, `frank/web.html`); nothing blocks framing.
  It refits the head to any frame size.

## Frank's calibration (2026-10-30)

From the CAD plus the datasheet direction (a servo turns counter-clockwise, seen from the shaft
end, as its angle grows), every check available agrees, so every sign is +1: Cogley's smile,
frown and tongue poses; his jaw direction shutting the team's jaw (why `JAW_DIR` is −1); his
brow raise directions; and all four of the team's saved lid poses. Zeros: mouth 90 (Cogley fits
every horn at 90), eyes the saved CENTRE (LR 107, UD 62), brows the saved LEVEL (90), each lid
the angle that shuts it in the CAD at its saved SHUT pose (TR 155.8, BR 135.3, TL 161.3, BL 89.8).
The OPEN poses then open every lid, the top lids 13° and 21° past the CAD's, the bottom lids 6° and 29°.

Not yet checked on the head: the eyes' left/right and up/down directions, and the mouth zeros.
Move each on the head and in the twin together; fix what differs with the calibration panel.

## Files

| File | What |
|---|---|
| `body.py` | the body server: serial port(s), TCP and virtual ports, board models, servo speed, the twin's web page and event stream, calibration saves |
| `boards.py` | models of the board programs (`pico_servo_ctl`, `cogley_mouth`); a new program is a class here |
| `play.py` | replays a `--record` file |
| `twin/index.html`, `twin/twin.js` | the twin page (three.js 0.170.0 in `twin/vendor/`, MIT, so it needs no internet) |
| `twin/kinematics.js` | the linkage solver, no three.js, shared by the page and the node test |
| `test_boards.py`, `twin/test_kinematics.mjs` | offline tests: `python perform/test_boards.py`, `node perform/twin/test_kinematics.mjs` |
| `../robots/frank/robot.json` | Frank: boards, servos, sockets, labels, servo speeds, calibration |
| `../cad/twin_export.py` | builds Frank's model and rig from the CAD: `output/twin/frank.glb`, `frank_rig.json` |

## Another robot

A robot is three files:

1. **`robots/<name>/robot.json`** (`perform-robot/1`): its boards (`firmware`: a program in
   `boards.py`; `via`: the board that forwards to it), its servos (`board`, `pin`, `type`,
   `label`, `zero`, `sign`), its servo types' speeds, and the paths of its rig and camera.
2. **A GLB** with one node `body:<name>` per moving body, its parts as child meshes
   (`part:<label>`), and any static extras as `layer:<layer>:<name>`. Bodies are modelled where
   they stand at rest; the twin moves each by a world transform.
3. **A rig** (`perform-rig/1`, JSON): the servos' shafts (`hub`, `shaft`), pins (`on` a body, or
   a `dyad` where two links meet), and bodies in solve order: `revolute` (a horn, or a part
   turned 1:1 or geared by `gain`), `link` (placed by two pins: couplers, rockers, parallelograms),
   `bend` (a flexible part between two bodies), each with an optional `parent`. Header comments
   in `twin/kinematics.js` give the rules.

Frank's GLB and rig come from code (`cad/twin_export.py`, which finds the pins in the CAD). A
robot modelled elsewhere can be exported from Blender or Onshape with the same node names and a
hand-written rig.

## Privacy

Frank's model is Will Cogley's Patreon CAD. The twin runs on 127.0.0.1 only; keep the GLB and
the rig private like the rest of his files (no public site, no claude.ai artifact, no public
remote).

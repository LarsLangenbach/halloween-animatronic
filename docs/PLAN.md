# Build plan: Frankenstein animatronic head

Living plan for the mechanical skull, eyebrows and skin interfaces described in
[BRIEF.md](BRIEF.md). It is updated whenever a milestone moves, a decision is
made or an input arrives. The day-to-day record is [BUILD_LOG.md](BUILD_LOG.md).

Plan version: v2, 2026-10-16 (re-based on Cogley's Robot Head α2.0.33, D14). Last updated 2026-10-30. The conversational character (Frank) is defined in [CHARACTER.md](CHARACTER.md); his prompt and the software contract are in [frank/](../frank/).

## 1. Status

| Milestone | Brief ref | Status | Exit criterion |
|---|---|---|---|
| M0 Inputs and foundations | — | **in progress**: Cogley STEP files in; printer known; coupon STL built, not yet printed | Both Cogley mechanisms in the repo and measured; servo models in; printer known; calibration coupon printed |
| M1 Mechanical layout | §12 M1 | **re-opening for D14**: v1 done 2026-10-15 at 1.2× (D4). Cogley's head α2.0.33 is imported and fit-checked against our head; the layout moves onto his frame (§6, Re-base) | Both modules and the brows placed on his frame; every motion clear; the proportions decided (Q16) |
| M2 Eyebrow prototype | §12 M2 | **switching to Cogley's brows (D15)**: our v1.1 is printed and becomes the bench backup. His 4-servo brows with flexible (TPU) brow bars come with his frame | Both brows bench-tested on MG90S servos through their full range; pull and travel measured under a silicone sample |
| M3 Integrated skull | §12 M3 | **eyes and mouth working (team report, 2026-10-26)**; the whole head is being assembled. Re-planned (D17): Cogley's head is built as he designed it, outer shell included; our skull pieces retire. Left for us: the neck mount, skin attachment points on his parts, and the fan's air path | Head printed and assembled; all servos move through their full range with no skin fitted; each servo can be swapped |
| M4 Snap attachment prototype | §12 M4 | not started | Snap size, adapter and pad chosen from measured pull-off and cycle tests on cast samples |
| M5 Sculpting integration | §12 M5 | **mold base ready to print (D20)**: the face mask (v9) is printed and sculpted in clay; a printed base seats it face up for the plaster mold and later holds it as the silicone core ([PLASTER_MOLD.md](PLASTER_MOLD.md)) | Registered armature printed; datums and attachment coordinates handed to the sculptor |
| M6 Silicone skin integration | §12 M6 | **skin cast; fitting started 2026-10-26** (team report). First public appearance: NightHack, San Francisco, 2026-10-30 | First skin fitted and connected; attachment positions revised where needed |
| M7 Final mechanical validation | §12 M7 | not started | Every motion with the skin on, no collisions or overstretch; skin removable for service |
| M8 Enclosure (added 2026-10-28, outside the brief's deliverables) | BRIEF §10 (fit inside a future enclosure) | **modelled, v1 (2026-10-29, D26)**: `cad/enclosure.py`, 11 thin prints plus two PETG sheets, about 27 printer-hours; `enclosure_check.py` passes (head, sheet, band, his parts, the jaw sweep, the bay, the bed); v0 (31 prints, 130 h) is in git at b0597cd | Base, cap, back column and sheet printed and fitted; the head bolted on its pedestal; the electronics in the base; the fan's air out through the base's slots |

## 2. How the CAD is built

- **The CAD is written as code.** Parts are Python programs (build123d on OpenCascade) in `cad/`, and every dimension lives in `cad/params.py`, tagged DATASHEET, ASSUMPTION or MEASURED.
- **One command checks the model.** `.venv\Scripts\python.exe cad\check.py` rebuilds every part, checks for overlaps, printability and size targets, and renders standard views. Nothing goes to the printer until it passes and the renders have been looked at.
- **Moving parts get pose sweeps.** Every mechanism is checked at rest, at each limit, at the combined extremes, and 30° past each limit to learn the real margin.
- **The brief asks for Onshape.** The code exports one coloured, labelled STEP of the whole assembly that opens in Onshape, Fusion 360 and FreeCAD. It arrives in Onshape as solid bodies without a feature history, so it can be viewed, mated and measured but not edited by changing a sketch. Whether that is enough is decision **D1**.

## 3. Inputs: what exists and what we need

### Team-supplied STEP files (received 2026-10-15)
The team exported both mechanisms from Onshape as STEP. Both are true solid models (B-rep), not meshes, so the "meshes only" problem in the research below no longer blocks M1. They are in `inputs/reference/`, with a survey in [inputs/reference/README.md](../inputs/reference/README.md).

| | EyeMech | Mouth |
|---|---|---|
| File | `eyemech/EyeMech_e3.1.step` | `mouth/MouthAssembly.step` |
| Version | **ε3.1**. Its outer geometry matches ε3.2 (see below), so it serves the layout | most likely the Robot Head α2.0.33 mouth (see below; Q3) |
| Solids | 38, all valid | 107 including screws; the compound reports **invalid** solids, still to be traced |
| Envelope (x × y × z) | 145.4 × 132.3 × 62.8 | 112.4 × 118.6 × 86.9 |
| Servos | 6, modelled as SG90 | **9 × MG90S** plus 2 bodies that look like the MG996R jaw servos. The brief says 8 × MG90S, so the ninth is probably the tongue (Q13) |
| Facing | −y | −y |

**ε3.1 vs ε3.2 (compared 2026-10-15).** Cogley's ε3.2 assembly guide describes two variants. "ε2" is snap-fit. "ε3.2-PIP" has print-in-place pivots and is recommended with MG90S servos. Every part in the team's ε3.1 STEP was compared with the public `EyeMech ε3.2 MG90s - A.3mf`, by size and volume:
- **Identical within 0.1 mm and 0.5 % volume:** the base plate, eyes, lids, lid levers, pivots, horns, eye adaptors and lateral frame.
- **Changed:** the central pivot holders and servo retainers differ by 0.4–0.6 mm and 50–190 mm³. That fits redesigned print-in-place joints and the A fit size.
- **Extra:** the 3MF has one more 66.3 × 33.2 × 5.6 base piece.

Everything the skull touches is the same, so the ε3.1 STEP is a valid layout reference for an ε3.2-PIP build. The changed joint parts sit inside the module; check them against the printed parts.

**First fit flag (R1).**
- **Eye spacing is wide:** the eyeball centres sit 75.0 apart, where an adult averages about 63.
- **Eyes are large:** each eyeball part is about Ø32, where a human eye is about 24.
- **The module is wide:** the EyeMech base is 145.4 wide, close to the full outer width of an average adult head (about 155) before any skull wall or skin is added.

A true life-size head will not hold the EyeMech unchanged. Scaling the whole head by about 1.2 brings the eye spacing back to human proportion: 75 / 63 = 1.19. A heavy, oversized head also suits the character. This is the first input to decision D4.

### Cogley's Robot Head α2.0.33 (received 2026-10-16)

The team's Patreon download of his whole head, now in `inputs/reference/head_a2.0.33/`: his reference assembly (Onshape OBJ, 191 parts), every printed part (Bambu 3MF, 8 plates), his control code and both PCBs. **No STEP:** only meshes. `cad/cogley_head.py` imports the assembly into our frame, eyes on ours; the study `cad/studies/cogley_fit.py` fits it inside our head.

What's in it:
- **Frame:** `SkullFrame`, a cage: a band round the front at eye level and ribs over the crown. Everything bolts to it. "Frame - Extras" adds a `CheekBone` band under the eyes and a `FanBracket` for a 50 mm fan.
- **Robot outer shell:** `FrontPlate`, `FrontVent`, `RearPlate`, `RearVent`. It is screwed to the frame's sides (M3 × 10); our skin-support shell replaces it.
- **Eyes:** the EyeMech. The base plate, side plates, bases and one pivot holder are identical to the ε3.2 MG90s-A set the team printed (to 0.3 mm). The moving parts are slimmer: levers 4.0 mm instead of 7.1, lids 1.4 mm thinner, a thinner lateral frame, a longer second pivot holder, different horns and eye adaptors. It is fitted with SG90 servos.
- **Mouth:** the same module as our `MouthAssembly.step`. Its `TopBase` bolts into the frame and the EyeMech's base plate sits 0.2 mm above it, so **the mouth's top plate is the eye shelf** (this answers Q14).
- **Brows:** 4 MG90S servos, an inner and an outer one per brow (`Brows.py`: ±20° around centre, with up, down, angry and happy poses). Each brow bar (`Part 11` / `Part 14`) prints in TPU ("Brows - Flexible"), so it bends when its two servos differ. The OBJ is missing 2 of the 4 brow servos; the 3MF has all the brow parts.
- **Electronics:** a Mouth board and an Eyes/Brow/Neck board (EasyEDA Pro), and MicroPython control code for the eyes, the brows and the mouth.
- **No neck:** the assembly ends at the jaw.

**Fit in our head (eyes on ours, 1.2×):**
- His EyeMech lands within 1.7 mm of ours. His mouth sits **13.4 mm higher** than ours.
- 26 of 191 parts poke past our skull's inside:
  - the brow bars (7.6 mm) and the lips (3.5 mm), which work through openings anyway
  - the `CheekBone` (8.2 mm, 0.8 through our face at the nose bridge)
  - the frame's side screw heads (up to 5.1 mm) and the frame itself (3.2 mm at the temples, z 180)
- Our printed EyeMech set on his base plate clears all his other parts: lids swept ≥ 5.7 mm, eyes swept ≥ 8.2 mm, and at rest it touches only the frame (its mount).

### Public downloads (researched 2026-10-14/15)
Items marked **unconfirmed** could not be checked.

### EyeMech ε3.2
- **Source:** [GitHub](https://github.com/will-cogley/EyeMech_Epsilon) and [Printables 1220172](https://www.printables.com/model/1220172-animatronic-eye-mechanism-e31/files). The Printables page was renamed from ε3.1 to ε3.2 on 2025-03-09. What changed between the two is **unconfirmed**, because no changelog is published.
- **CAD format: 3MF meshes only.** There is no STEP, Fusion file or Onshape link. The files are `EyeMech ε3.2 MG90s - A.3mf` and `- B.3mf` (two fit sizes, chosen with `Testing Plate.3mf`), the SG90 variants, an all-plates file, and an assembly PDF.
- **Construction:** no screws apart from the servo horn screws. Servos sit in snap retainers, the pivots snap in from under a single printed base, and the board clips into two printed holders. The PDF recommends the print-in-place "ε3.2-PIP" variant with MG90S servos.
- **Servos:** 6 (eye left/right, eye up/down, four lids), matching the brief.
- **Not published:** the overall envelope, the eyeball diameter, the eye spacing, and any external mounting holes. These come from measuring the mesh in M0/M1.
- **Controller:** NM Robotics Eye Mechanism Controller Board (RP2040, Pico-compatible), or a bare Pico.
- **Licence:** CC BY-NC-SA 4.0. The GitHub licence file adds: "Contact enquiries@willcogley.com if you would like to use this design for a commercial application."

### Mouth mechanism: two candidates (Q3)

| | A. Mouth Mechanism (2020) | B. Robot Head α2.0.33 (April 2025, work in progress) |
|---|---|---|
| Servos | 7 × MG90S + 2 × MG996R | mouth board drives 2 × MG996R jaw, 4 lip, 4 cheek, tongue and one spare |
| Matches the brief's "8 × MG90S + 2 × MG996R" | no | yes: 4 lip + 4 cheek + 2 jaw |
| Custom PCB | none (Arduino + PCA9685) | Mouth Board, plus an Eyes/Brow/Neck board (EasyEDA Pro files published) |
| CAD | **STEP** (`Animatronic Mouth CAD.step`, 22.8 MB) + STLs | **meshes only**: STL, 3MF, OBJ reference assembly |
| Licence | **unconfirmed** | **unconfirmed** |
| Links | [video](https://youtu.be/lY83q531gHk), [page](https://willcogley.notion.site/Mouth-Mechanism-3d2605cc99ff45a9b2994c1e3b8cd4a4) | [page](https://willcogley.notion.site/Robot-Head-2-0-33-1d724779b64d8056) |

**Working assumption: B, the Robot Head α2.0.33 mouth.** It is the only candidate with 8 + 2 servos and a mouth PCB, which is what the brief describes. Two consequences follow:
- **B is a whole head, not a standalone mouth.** Its mouth has to be separated from the rest of the head, and where its mounting interfaces sit is found by measuring the meshes.
- **B already has an Eyes/Brow/Neck board,** so Cogley's own head appears to include eyebrows. Whether its brow mechanism can inform or replace our custom design is **unconfirmed** and worth checking before M2. Its 12-channel mouth board would also cover eyes (6) plus brows (2) if a second one is used as brief §10 suggests.

The older head with magnetic skin attachments, which the brief refers to, is from December 2024 (14 servos, Arduino Mega). Its files are on Patreon only. The α2.0.33 page says the magnetic skin is "not included for legal reasons".

### What working from meshes means
This applies only where a part is missing from the team's STEP files.
- Meshes import fine for placement, measurement, overlap checks, pose sweeps and renders.
- They cannot be edited cleanly. Any interface we design to (mounting faces, the jaw pivot, lip endpoints) is re-modelled as clean geometry from measurements of the mesh, then checked against the mesh and the printed part.
- The EyeMech has no external mounting holes. The upper module will grip or clamp its printed base rather than screw into it. Changing their base would create a derivative work under the share-alike licence (Q10).

### Servo models
- **MG90S:** Adafruit's MIT-licensed `1143 Micro Servo High Torque Metal Gear.step` ([Adafruit_CAD_Parts](https://github.com/adafruit/Adafruit_CAD_Parts)) has the same body as the MG90S. Datasheet: body 22.8 × 12.2 × 28.5, mounting tab span 32.1–32.5, tab top 21 above the base.
- **MG996R:** no trusted model was found. GrabCAD has community models whose accuracy and licence are unconfirmed. Datasheet: body 40.7 × 19.7 × 42.9, tab span 53.6–54, tab top 26.6 above the base.
- **Neither datasheet gives** the mounting hole spacing, the hole diameter, or the output shaft offset. These come from calipers (M0).

### Still needed
| Input | From | Goes to |
|---|---|---|
| ~~EyeMech CAD~~ | received 2026-10-15 as STEP (ε3.1) | `inputs/reference/eyemech/` |
| EyeMech **ε3.2** STEP (D11) | the team, from Cogley's Onshape, if a ε3.2 document exists there | `inputs/reference/eyemech/` |
| ~~Mouth CAD~~ | received 2026-10-15 as STEP | `inputs/reference/mouth/` |
| EyeMech assembly PDF (servo ranges, lid travel) | GitHub (public) | `inputs/reference/eyemech/` |
| MG90S STEP (Adafruit 1143) | GitHub (MIT) | `inputs/components/` |
| MG996R model | to be found, or modelled from calipers | `inputs/components/` |
| Caliper values for both servos and both snap halves | the team | `params.py` (MEASURED) |
| Photos or measurements of any already-built Cogley modules | the team | `inputs/reference/` |

## 4. Coordinate frame and datums

One frame is shared by the skull, the Cogley modules, the sculpting armature, the mold core and the skin attachment coordinates (brief §7). Proposed as decision **D2**:

- Units: mm and degrees.
- **x = 0** is the facial midline (the symmetry plane).
- **y = 0** is the plane through both eyeball centres at rest; **+y** points forward, out of the face.
- **z = 0** is the underside of the neck/base interface, where the head meets the enclosure support; **+z** is up.
- **+x is the character's left.** That is the viewer's right when looking at the face. Parts are named by the character's side: `brow_L` sits at +x.

Datums kept in `params.py`, all ASSUMPTION until M1 sets them:

| Datum | Set by | Starting value |
|---|---|---|
| Eye centre spacing (IPD) | EyeMech module | the module's own spacing; an adult averages about 63 mm |
| Eye centre height | head proportions | eye line at about half the chin-to-crown height |
| Mouth line (stomion) | mouth module | where the module's lip line sits at rest |
| Jaw pivot axis | mouth module | the module's pivot, compared with where a human jaw hinges (just in front of the ear) |
| Brow line | brow mechanism | above the upper eyelid, clear of its full travel |
| Outer face reference | proxy head in M1, the sculpt in M5 | about 155 wide, 195 front-to-back, 230 chin-to-crown (approximate adult averages), probably scaled about 1.2 (D4). The jar is chosen to suit the head, so it sets no limit (Q5) |
| Skin thickness zones | sculptor + M4 samples | forehead, brows, cheeks, lips and chin each get their own value |

The skull's outer surface is the skin's inner surface offset inward by a clearance. The skull is not the sculpt surface (brief §7).

## 5. Architecture

**Servos:** 19 in total. 17 × MG90S (9 mouth: 4 lip, 4 cheek, tongue; 6 eyes and lids; 2 brows) and 2 × MG996R (jaw). The brief counted 18; the tongue was added per D10.

**Modules** (brief §5), proposed as decision **D9**:

- **Rear backbone.** The structural spine everything bolts to. It carries the neck/base interface, the main cable route, the rear access panel and the rear skin attachments.
- **Upper module.** Mounts the EyeMech frame and both brow units, and forms the forehead and temples. It has shim or slot provision to adjust eye depth and alignment.
- **Lower module.** Mounts the mouth mechanism unchanged and carries the cheek, lip-corner and chin skin interfaces.
- **Neck/base interface.** Holds the head rigidly in the enclosure and carries the cable bundle down into the base.

Each module comes off on its own, so a servo can be reached without taking the head apart. Every servo lead ends in a connector at its module boundary.

**Fasteners:** M3 socket head screws into heat-set inserts for skull joints (decision **D6**). The Cogley modules keep their own hardware.

**Electronics:** both Cogley PCBs sit in the base (brief §10). Assuming the α2.0.33 mouth board (12 channels), a second one covers the eyes (6) and brows (2) with channels to spare. That puts 18 three-wire leads through the neck. The neck channel starts as a 25 mm clear bore (ASSUMPTION) until the real bundle is measured.

## 6. Milestones

### Re-base on Cogley's head (D14, started 2026-10-16)

The mechanical base is now his head. His frame, mouth position, eye mount, brows and fan bracket are kept. We build what goes on top: the skin-support shell, the neck, the skin attachments and the sculpt base. Our own parts that his head replaces (shelf, cradle, strap, brow mounts) retire with the skull v0.

- [x] Import: `cad/cogley_head.py` (in the pipeline), 191 parts in our frame, grouped frame / extras / shell / eyes / mouth / brows / hardware.
- [x] Fit study `cad/studies/cogley_fit.py`: his head inside our current head (above).
- [x] Eyes: the printed ε3.2 set fits his head (D16).
- [x] **Proportions (Q16):** keep his mouth where he put it (D17). It only looked too high against our placeholder face.
- [x] Print status (2026-10-16): the team has printed the eyes (ε3.2 MG90s-A), the mouth, the teeth and tongue, and his "Brows - Main" plate. **Cleared to print now:** "Frame - Main" (the skull frame), "Frame - Extras" (cheek bone, fan bracket) and "Outer Shell", all as he designed them. The brow bars wait for TPU (Q18).
- [ ] Our module placements moved onto his (mouth, EyeMech), his brows added as a module with their motion, and the sweeps re-run inside his frame.
- [x] Sculpt base v2 (D17, `cad/sculpt_base.py`, `cad/wrap.py`). It is a wrap of his complete head at rest, ≥ 3 mm out from every part:
  - tight over the lips, brows and lids, where the skin must stay thin enough to move
  - smoothed and inflated over the rest of the face
  - tight over his shell
  It has eye sockets showing the real eyes, and sculpting guides: the midline, the eye line, the brow lines, the nose bottom and width, the lip line and mouth corners, the chin, the hairline and the ears. The mold core will be the same wrap less the 3 mm.
- [ ] Skin attachment points on his parts: snaps on the brow bars, the lips and the jaw; fixed points on his shell and cheek bone (M4).
- [ ] Neck and stand: his assembly has none (Q17).
- [ ] Fan and venting under the skin (R6): his vents are in the robot shell we drop.
- [ ] Sculpt base regenerated from the re-fitted face.


### M0 — Inputs and foundations (now)
- Answer the open questions in §7. Q1 (deadline) and Q3 (which mouth mechanism) come first.
- ~~Get both Cogley mechanisms into the repo~~ (STEP received 2026-10-15). Measure their mounting faces, eye spacing, jaw pivot and lip endpoints into `params.py`, and trace the mouth file's invalid solids.
- Get the MG90S STEP and an MG996R model into `inputs/components/` (sources in §3), and caliper the real servos: body, mounting tab span, hole spacing, output shaft offset. Clones differ from the datasheet.
- Buy a pack of the 7 mm sew-on snaps and caliper both halves.
- Print the calibration coupon on the printer that will make the skull, and record the hole and insert sizes it picks.
- Replace the example builder with the project's params skeleton: the frame, the datums, and the servo sizes.

### M1 — Mechanical layout
Goal: prove both Cogley modules and the brow mechanism fit a life-size head before designing any skull.
- A `modules` builder imports the EyeMech and mouth STEP files and places each one in the head frame with one position and one rotation from `params.py`.
- A proxy head stands in for the sculpt until M5: a simple smooth surface with eye sockets and the mouth line at the datums. Offsetting it inward by the skin zones gives the space the skull must stay inside.
- A `pose_sweep` check covers jaw open and closed, eye pan and tilt corners, lids open and closed, and a placeholder box for the brow swept volume.
- Checks: the modules never overlap at any pose; every moving part stays inside the skin's inner surface with margin; the eyeball centres sit on the socket datums; a cable path to the neck exists.
- Output: a fit table of the smallest clearance per pair at the worst pose, front, side and section renders, and the head proportions for sign-off (decision **D4**).
- If the modules don't fit, the options are a slightly larger head (plausible for this character), moving the modules, or trimming non-working frame material from them. Each option goes into a design note with numbers.

**Progress (2026-10-15):**
- [x] Frame, datums and module placement in `params.py` and `geom.py`. Example builder removed.
- [x] `modules.py` places both Cogley assemblies (one mesh per solid, to `output/ref/`, gitignored).
- [x] `head.py` builds the proxy head and its skin and skull envelopes.
- [x] `layout_check.py` runs in the pipeline. At rest at 1.2× with `boxy_temples` and the lip line at −70.5, every part is inside its envelope. Tightest gaps: EyeMech side plates 0.7 mm, mouth frame 0.9 mm, eye module to mouth 5.5 mm. See [DESIGN_NOTES.md](DESIGN_NOTES.md#d4-head-size-and-shape).
- [x] Fresh-eyes review done. The numbers were confirmed independently. Fixed:
  - section renders now show a 12 mm slab, not everything behind the cut
  - the mouth surface parts are now checked
  - the lip line and the loft now share one interpolation
  - the chin and neck no longer pinch into a waist
- [x] D4 signed off 2026-10-15: A2.
- [x] `pose_sweep.py`: jaw (47 parts: grouped by contact, plus the MG996R horns), eyes, and top and bottom lids, at the assumed ranges.
  - The tongue's back corner touches a fixed mouth servo in CAD (up to 8.6 mm³, 3°–25° open). **D12: accepted.** The team's printed mouth runs without trouble. It is listed in `ACCEPTED_CONTACTS`; anything bigger, or any other pair, still fails.
  - Everything else on the jaw is clean to 35°. At 25° the chin drops 16.3 mm, the lip plates open from 12.0 to 41.1 mm, and the jaw stays at least 1.3 mm inside the skull.
  - Eyes and lids stay 8–10 mm behind the outer skin.
- [x] `reserve.py`: a brow bay per side (48 × 67 × 55, at least 2.4 from the EyeMech, 3.5 from the open lids) and a Ø25 cable channel down the back of the neck (16 mm behind the open jaw, inside the skull).
- [x] Proxy neck and nape thickened, because the cable channel didn't fit between the open jaw and the back of the neck. The neck is about 144 × 128 at 1.2×.
- [x] Eye and lid ranges from Cogley's firmware: servo limits 40..140 for left/right and up/down; lids 70–80° of travel. Swept as ±50° eyes and 80° lids (1:1, a safe upper bound). Everything stays clear.
- [ ] Jaw range: still the ASSUMPTION of 25°. **Bench:** measure how far the team's built mouth opens (degrees, or the lip gap in mm).
- [ ] The lip and cheek servos' own motions (small; checked with the skin in M4/M6).
- [x] Eye sockets **moved to M3/M5.** They depend on D7 (separate eyelid skins) and on the sculpt. Number for the sculptor: the eyeball fronts sit 10 mm behind the boxy proxy face, so the face must come back about 8–9 mm around each eye for the lid skin to sit on the lids.
- [ ] Before M3: replace the section-shrink inset with a true offset. The reviewer measured the skin as thin as 1.4 mm at the crown shoulders and 1.9 mm under the chin, where 5.0 is intended. That doesn't matter for the module fit (at most 0.5 mm at the worst points), but `skull_inner` can't be the skull boundary as it is.

### M2 — Eyebrow prototype
Goal: a brow that deforms the skin convincingly, built and tested on the bench before the skull is final.
- **First, look at Cogley's own brows.** His Robot Head α2.0.33 has an Eyes/Brow/Neck board, so it likely has a brow mechanism worth learning from (§3).
- **Motion spec** (ASSUMPTION until agreed): about 8 mm up and 4 mm down at mid-brow from neutral.
- **One servo per brow gives one degree of freedom.** Whether the inner end rises more than the outer end is fixed by the mechanism's path. The proposal is that raising reads as surprise or worry (the inner end lifts more) and lowering reads as anger (the inner end drops and moves toward the midline). That is decision **D5**.
- **Three mechanism concepts** are compared by pose sweep before printing (decision **D3**):
  - A. Carrier on the servo horn: fewest parts, but the brow swings in an arc away from the forehead.
  - B. Four-bar linkage (servo crank, coupler, carrier rocker): the path can be shaped to follow the forehead.
  - C. Carrier on a curved track, pushed by a rod: closest to the skin surface, but more friction and more parts.
- They are judged on how far the carrier strays from the skin's inner surface, fit above the EyeMech lids, part count and backlash.
- **Carrier:** a curved plate following the skin's inner surface with a 1–2 mm gap and edges rounded to at least R2, so no hard point shows through. It has one or two snap adapters to spread the load.
- **Neutral adjustment:** a slotted horn clamp or a choice of spline positions. **Hard stops:** adjustable screw stops, so the skin can't be overstretched.
- **Bench rig:** a standalone printed frame that holds one brow unit and a curved skin-sample holder, so a silicone sample can be fitted and snapped on.
- Exit: both brows printed and run on MG90S servos. Travel is measured against the spec, the neutral position adjusts, the stops hold, and nothing binds. Results go in the build log, and D3 is decided.

**Progress (2026-10-15):**
- [x] Concept study (`cad/studies/brow_concepts.py`). A whole-brow plate fails. Two snap pads on one skewed pivot meet every limit ([design note D3/D5](DESIGN_NOTES.md#d3-and-d5-eyebrow-mechanism-concept-and-motion)).
- [x] Mechanism v1: `browgeom.py` (shared geometry), `brow.py` (carrier and bracket per side, plus servo, horn, pushrod and screw references), and `brow_check.py` (both brows through the travel against everything). All in the pipeline.
- [x] Adafruit MG90 model in `inputs/components/` (MIT); servo sizes measured from it.
- [x] Print orientations: bracket upside down without supports, carrier with its hub axis vertical on tree supports.
- [x] Fresh-eyes review: ball-stud room, a stock shoulder-screw length, flange inserts, bed contact and the horn reference fixed (v1.1).
- [x] Adjustable hard stops: two M3 set screws on the double-arm horn, set from above. Checked: no contact inside the travel, engaged just past each end.
- [x] Bench rig (`brow_rig.py`): a printed forehead fragment around the left brow, with the pad window, clamp-strip inserts for a skin sample, and a screwdriver hole in line with the pivot. Checked: moving parts ≥ 1.1 clear.
- [x] [PRINT_GUIDE.md](PRINT_GUIDE.md), [BOM.md](BOM.md) and [ASSEMBLY.md](ASSEMBLY.md) started. `cad/export_print.py` writes slicer-ready files to `output/print/`.
- [ ] Snap adapters on the pads (with M4).
- [ ] **Team:** print the coupon, then the brow set and the rig; bench test travel, neutral adjustment, stops, binding and servo load (record in the build log).

### M3 — Integrated skull
- Split the skull into the backbone, upper module, lower module, access panel and neck interface. A split table lists each item that must come out against the opening it comes out through.
- `fasteners.py` holds every insert and screw, so builders and checks read the same positions.
- **Service checks:** each of the 19 servos has a clear path for its screwdriver and a straight-line way out; each module slides out along a checked path.
- **Cable channels:** a planned route from every servo to the neck, with connector pockets at module boundaries and slack where a lead crosses a moving joint.
- **Fixed skin attachments:** perimeter clamp strips and hidden tabs on non-moving areas, with their coordinates exported (brief §6).
- **Pose sweep of everything together:** jaw open, eyes down, lids closed and brows down at once, plus the other corners.
- **Print check:** orientations, supports and bed fit. Structural walls are at least 2.4 mm, with ribs where servo loads go in.
- Exit: the check passes with every sweep clean; the skull is printed and assembled; all 19 servos move through their full range with no skin; one servo of each type is swapped as a test. The jar requirement (inner diameter and height, with clearance) is written from the final head and neck envelope.

**Progress (2026-10-15):**
- [x] True-offset envelopes (`head.py`). Every check re-run on them; all still pass.
- [x] Skull v0 (`skull.py`): a 2.4 mm wall between the skin's inner and the skull's inner surfaces.
  - Eye-and-brow openings and a mouth opening, cut square to the wall (normal-walled convex cutters; the first box and cylinder cuts left slivers).
  - Split at z 186 / y −60 into 4 pieces that fit the bed, plus a shelf between the EyeMech and the mouth.
  - The brow brackets' mount plates.
- [x] `skull_check.py`: every module and brow part at rest, and the jaw, lid, eye and brow sweeps, against every skull piece. All clear: ≥ 1.0 at rest (the shelf to the mouth's top plate), ≥ 1.4 in motion.
- [x] Joints: 23 screwed tabs along the 4 seams (2 / 4 / 9 / 8).
  - Each tab is a 5.5 mm patch of thickened inner wall on one piece, reaching behind the other piece's wall. It holds an M3 insert; an M3 countersunk screw comes from outside, its head flush under the skin.
  - Tabs are placed automatically: wall on both sides, ≥ 1.5 from every module, brow part, motion sweep, the shelf and the brow plates, countersinks ≥ 2 from any opening, and no tabs where the wall lies nearly in the seam plane.
- [x] EyeMech cradle. The EyeMech stands on feet (three plates and a rear block, all at z 185.2), not on its base plate, so:
  - The shelf carries pads under the feet. A stop hanging from the strap, behind the base plate's rear lip, sets the eye depth with shims (it moved off the shelf so the EyeMech's way out is clear).
  - The temple walls (about 1 mm off its side plates) locate it sideways.
  - A printed strap 0.4 over the back of its base plate keeps it down. It bolts to two ledges on the back upper piece.
  - The shelf bolts down onto four ledges on the side walls (M3 inserts).
  - ASSUMPTION until the printed EyeMech is on the bench. A first try with rails and zip ties hit the bottom-lid levers.
- [ ] Mouth mount. **Waiting on Q14:** how Cogley fixes the mouth's top plate into his own head frame.
- [x] Neck/base interface: `skull_neck_plate`, a 6 mm plate 0.4 inside the wall with an 18 mm collar up its inside.
  - Six countersunk M3 screws through the wall into inserts in the collar; it also ties the two lower pieces together at the bottom.
  - 4 × M4 on a 50 mm square for the stand (ASSUMPTION until the jar and its stand are chosen), and the cable channel's exit.
- [x] Rear access panel: `skull_access_panel`, a 96 × 74 opening centred at z 268 on the back of the head.
  - It rests on a 4 mm lip inside the opening, with a pad behind each side's midpoint for an M3 insert.
  - 4 countersunk M3 × 6 screws from outside, heads flush under the skin.
  - With it off, the brows and the back of the EyeMech are in view.
- [ ] Cable channel features, fan room and vent (R6), and fixed skin attachments (with M4).
- [x] Service paths, found with a direction search (straight-line moves, point clouds confirmed exactly against the meshes):
  - **Back upper piece** (with the access panel and the eye strap): lifts off up and back at about 50° (47.5–55° is clear).
    - The first design came off straight back only. The tabs on its seams are now placed per tab (`BACK_UPPER_OUT_DEG`): on whichever piece they can't hook as it leaves.
    - The back seam's tabs now belong to the back upper piece, so they leave with it.
  - **EyeMech and both brows: together.** They interlock; neither passes the other.
    - Unbolt the brows' flanges, then slide the three back 50 mm, lift 4 mm and take them out the back.
    - The cradle's rear stop now hangs from the strap, behind the base plate's rear lip, so it leaves with the back piece too.
    - The back seam's tabs used to stand in that path.
  - **Shelf:** up 8, then back.
  - **Neck plate:** straight down.
  - **Mouth:** no clear path yet. It hits the back lower piece going back and the front upper piece going up. This is part of the mouth mount (Q14).
- [x] `service_check.py` in the pipeline. It runs the paths above as a teardown sequence, and puts an L hex key on every screw that must come out on the way, which must swing at least 60°.
  - The two front brow flange screws have only 16.3 mm under the crown. They need a **stubby 2.5 mm key** (short arm cut to 12 mm), which gets 125° of swing.
  - Every other screw takes a standard key.
- [ ] Print poses optimised; the v0 poses are a first guess.

### M4 — Snap attachment prototype
- Caliper the 7 mm snaps and design a printed adapter that holds the socket half on a linkage end.
- **Orientation rule:** the snap axis is normal to the skin, and linkage motion runs along the skin. Normal motion then loads the snap sideways (shear) rather than pulling it straight off (brief §6).
- **Test molds:** small printed two-part molds for silicone pads (a fabric pad with a snap sewn in), with a plug that keeps the snap's mating face free of silicone.
- **Material:** cast the pads in Dragon Skin FX-Pro (D21), mixed exactly as the face will be (same Slacker or THI-VEX, if any), so the measured forces carry over.
- **Tests:** straight pull-off and sideways pull-off force (a luggage scale is enough), and a cycle test driven by a servo on the rig.
- **Unsnap tool:** a printed fork that braces the skin around the snap while it is pulled off (brief §6).
- **Pad template:** a printable stencil that places the fabric pads in the mold at the CAD coordinates.
- Exit: snap size, adapter and pad layout chosen, with measured forces and a cycle count without tearing (target set in M4).

### M5 — Sculpting integration
- **Armature:** the skull's outer surface plus the minimum skin thickness, so the clay is never thinner than the skin. It carries embossed datums: centreline, eye centres, mouth line and snap points.
- **Mold core:** for a hollow skin, the mold core is the skin's inner surface. That surface comes straight from the CAD (skull plus clearance), so the core can be printed and registers to the skull exactly.
- **Exports:** armature STL, skin clearance envelope STEP, outer face reference, and a CSV of attachment coordinates in the head frame.
- **Registration keys** on the armature base carry into the mold.
- Exit: armature printed and the datums checked against the skull.

**Progress:**
- [x] Sculpt base v1 (`cad/sculpt_base.py`, checked by `cad/sculpt_check.py`), started early so sculpting can begin (D13):
  - The whole head as a solid: the skull's outside raised by `SCULPT_MIN_SKIN` (3 mm, ASSUMPTION), so the skin is never thinner than that.
  - Eye sockets inside the skull's own eye openings, with the lids' sphere and a pupil dimple at the true eye positions.
  - Grooves: the midline, the brow windows, the mouth opening and the lip line.
  - Split at z 186 for the bed and joined by dowels, standing on a base plate with 4 mold registration keys. M4 bolts go into inserts in the neck.
  - The check confirms no skull point stands outside the base, the eyes sit on the EyeMech's eyeballs, and every piece fits the bed.
- [ ] Mold core (the skull's outside itself, with the same plate and keys), exports, and the attachment-point CSV.
- [x] Mold base (D20, 2026-10-20; `cad/mold_base.py`, checked by `cad/mold_check.py`): the clay-covered face mask lies face up in a printed collar (a ledge under its rim, a lip 6 mm up its inside that stands straight up where the mask flares out, 0.4 clear of the STL; the mask lowers straight in), with posts under the forehead and cheeks. The collar's skirt flares down at 12° to a flat flange with 4 registration cones and 8 loose pry wedges in gaps in the rib (pulled out to leave screwdriver slots under the flange). The walls (45 mm) are 4 separate L-shaped corners clipped together at ears, standing outside a rib on the plate, so they come off outward before the plaster is lifted. Four base pieces split at X = 0 and through the ears, with dovetails in the plate; every seam is vertical, so they drop together. Nothing the plaster touches faces down; the mask's own tucks by the ears and jaw (96 cm²) are filled with clay or taken by side pieces (R13). The same base holds the cleaned mask as the core for the silicone cast.

### M6 — Silicone skin integration
Fit the first skin, connect the snaps, film each motion, and move attachment points where the skin bunches or overstretches. CAD changes go through the normal check loop, and every move is logged.

### M7 — Final mechanical validation
Run every motion and the combined extremes with the skin on. Confirm no collisions or overstretch, confirm the face comes off and goes back on without damage, and finish the print guide, assembly guide and motion notes.

## 7. Open questions

| # | Question | Why it matters | Answer |
|---|---|---|---|
| Q1 | What is the deadline? Today is 2026-10-14. If this is for Halloween 2026, that is 17 days away. | Sculpting, mold-making and casting alone take weeks. A 31 October date needs a reduced scope. | **Aiming for before Halloween, but the team owns the schedule:** plan the full scope, and work in the milestone order. (2026-10-15) |
| Q2 | Which printer(s), bed size and nozzle? Which materials are on hand? | Sets the split lines, tolerances and the print check. | **2 × Bambu Lab P2S** (written "PS2"; read as P2S), 256 × 256 × 256 bed. Cogley designed the EyeMech on the P1S, which has the same bed. Nozzle assumed 0.4. Materials still open. (2026-10-15) |
| Q3 | Which mouth mechanism exactly? Working assumption: the Robot Head α2.0.33 mouth (§3). | Its mounting points, jaw pivot and lip endpoints drive the lower module. | |
| Q4 | Are the EyeMech and mouth already built, or still to print? Are the servos on hand, and are they genuine TowerPro or clones? | Built modules and real servos can be measured. | **Partly:** the team has printed this mouth before (2026-10-15). The ε3.2 MG90s-A eye set is printed (2026-10-16). Servos on hand: **3 × SG90, plastic gear** (2026-10-16), for bench tests only. The head needs 19 × MG90S (metal gear) + 2 × MG996R, to buy, genuine TowerPro (BOM: *SG90 or MG90S*). |
| Q5 | Specimen jar: inner diameter and height, or still open? | Sets the head size limit and the neck height. | **Not chosen. The jar will be picked to suit the head**, so it sets no size limit. The design hands over a jar requirement in M3. (2026-10-15) **2026-10-28: no bought jar. The enclosure is printed round the head (D23)**: a canister with a rolled clear sheet, sized from the sculpt wrap. |
| Q6 | What is the editable Onshape assembly for: viewing and mating, or another designer editing features? | Decides D1. | |
| Q7 | Fasteners and inserts on hand (M2, M2.5, M3; heat-set inserts)? | Decides D6. | |
| Q8 | Which 7 mm snaps (link)? | Sizes the adapters. | |
| Q9 | True life size, or slightly oversized for the character? Any reference images? (Put them in `inputs/reference/`.) | Sets the proxy head in M1. | |
| Q10 | Personal Halloween prop, or a commercial piece? | EyeMech is CC BY-NC-SA 4.0: no commercial use without Cogley's permission, and modified versions must be shared under the same licence. The mouth's licence is unconfirmed (§3). | |
| Q11 | Who sculpts, and what skin thickness are they aiming for? Separate moving eyelid skins (brief §3B)? | Sets the skin zones and decision D7. | |
| Q12 | Where did the two Onshape models come from (Cogley's own Onshape document, or rebuilt or converted by the team)? | Provenance and licence record; whether they match the parts that will be printed. | **Will Cogley's own Onshape documents, through the team's paid Patreon membership.** These are member-only files, so the repo stays private and the STEP files are never redistributed. (2026-10-15) |
| Q15 | Who sculpts, with which clay, and what is the thinnest skin they want? The sculpt base assumes 3 mm (`SCULPT_MIN_SKIN`). The clay must be sulfur-free if the skin is platinum-cure silicone. | Sets the armature offset; sulfur in the clay stops platinum silicone from curing. | **Partly answered:** the clay is Monster Clay (sulfur-free, 6 lb, 2026-10-15), and the face is sculpted (2026-10-21) by the team. The skin is Dragon Skin FX-Pro (D21). Thinnest skin still open. |
| Q14 | How does Cogley fix the mouth module's top plate (TopBase) into his Robot Head α2.0 frame? An Onshape STEP export of the full α2.0 head would show it, and the α2.0 brow mechanism too. | The mouth mount in M3; the top plate has pockets and shallow holes but no obvious mounting points. | **Answered 2026-10-16 by his head files (§3):** the TopBase is held in his `SkullFrame`, and the EyeMech's base plate sits on it (0.2 mm gap): the mouth's top plate is the eye shelf. |
| Q16 | (Answered: keep his mouth, D17.) Proportions on his head: his mechanism puts the lips 71 mm below the eyes, with the eyes 75 mm apart. A normal face with eyes that far apart has its lips about 85 mm below them. Keep his mouth where it is (a short mid-face, a little cartoonish, no mechanical change), or lower it 13.4 mm (normal proportions, but his frame's mouth mounts must be cut and redrawn, and the EyeMech needs a shelf again)? | Sets the face, the shell and the sculpt base. | |
| Q17 | Does Cogley have a neck or mount for the α2.0 head (his Eyes/Brow/Neck board suggests one)? If not, we design the neck from his frame down to the stand. | The neck/base interface and the cable route. | **No neck in his assembly (2026-10-16). Proposal 2026-10-28 (D25):** a printed neck spine. His head's only fixed structure low down is the frame: its lowest bar is at z 134.6 (x ±34, y −84..−74) and its nape ribs reach down to z 135 at x ±77, y −165..−95. The jaw hangs from the frame on its links; at rest it spans y −75..10, z 106..182, open 25° it reaches y −85 and z 88 (overtravel 35°: y −92.5, z 82). So: a Ø100 column on the pedestal from z 0 to 70, under the jaw's swing, then a 30 × 80 spine at y −125..−95 rising to z 190, bolted into the frame's nape ribs. The jaw swings in front of it and never touches it. The skin's neck stub (z 40 up) covers both. Cables and the fan air come down through an opening in the spine's top plate, inside the spine, into the tube and out through the Ø25 bore. |
| Q19 | What goes in the base, and how big is each item? | Sets the base's height and the floor tray's layout (D23). | **Answered 2026-10-28 (human + the Head Power Wiring doc, claude.ai, 2026-10-26):** only the power box and the boards. UGREEN Nexode 25,000 mAh 145 W power bank (at a wall, the JUYOON 140 W charger outside instead), USB-C 240 W cable, PD trigger set to 20 V, F1 7.5 A, ACEIRMC 20 A buck at 5.30 V, WAGO 221 buses, F2/F3 10 A, 1000 µF, two XT60 leads to Board 1 (mouth) and Board 2 (eyes + brows). The laptop stays outside: Board 1's micro-USB and the webcam's USB lead go out through a hatch at the back of the base. A speaker in the base (human, later the same day), ready-made, no soldering (human: no time): the human's own Sony SRS-XB12 (Ø74 × 92, 243 g, 3.5 mm aux, micro-USB charge), on its side in a printed cradle at the front of the tray, its driver end at a snap-out grille panel (about 110 × 84, like the inset panel on the reference picture's base) in the base's front wall; the panel comes out to reach the power button and the aux socket; a 3.5 mm lead from the laptop, charge lead from the bank's USB-A port. Nothing to buy. To test at home: that it plays on aux while charging, and whether it switches itself off after about 15 min of silence (Sony's auto standby); if it does, the laptop keeps a faint sound playing. Bluetooth is not used (delay behind the mouth). Earlier picks, dropped: Dayton ND65-4 + PAM8403 (soldering), Anker S330 (price), Amazon Basics pair (not needed). Sizes assumed until measured: bank 161 × 55 × 50, buck 85 × 60 × 28, boards 95 × 65 × 20; the bay is 96 tall. |
| Q20 | The clear sheet: rolled 1 mm PETG or polycarbonate (cheap, bends to R150 cold), or a bought Ø300 cast acrylic tube (no seam, no column needed for the sheet, dear)? | Sets the slit width and whether the back column carries the cap. Acrylic sheet is out: it crazes and cracks when cold-bent tighter than about 330 × its thickness. | **Answered 2026-10-28: the human left it to us; D24, 1 mm clear PETG.** |
| Q21 | Which camera, and does the computer that reads it sit in the base or outside? | Sets the pocket in the cap's front band (D23) and the cable. No lights in the enclosure (human, 2026-10-28): the room is lit. | **Answered 2026-10-28: a Logitech 1080p webcam** (taken as a C920-class bar, 94 × 29 × 24, 78°, fixed 1.5 m USB lead; if it is the StreamCam, 58 × 48 × 66, the cradle changes), on the laptop outside. Its lead runs round the cap ring, down the column and out of the base's back hatch. |
| Q22 | Do the keyed lids (D27) hold a brushed FX-Pro skin? Test: brush one keyed lid as PRINT_GUIDE says, cure, then peel at the lash edge and work the lid through its travel. | Proves the only thing holding the lid skin on; sets whether the holes need to be larger, denser or joined by a lash-edge feature; peel is the weak mode (each 2A rivet head holds about 1 N through its neck, and the first row at the lash edge takes the peel), the clamped-edge option is the fallback. | Open: print `cogley_lids_keyed_plate.stl` and cast one lid first |
| Q18 | Is there TPU filament (about 95A) for his flexible brow bars? | His brows need it (D15). | **No (2026-10-16): buy TPU 95A.** Not PLA: each bar is a pleated strip (walls 1.5–3.4 mm) that stretches and bends every time its two servos move differently. PLA would be stiff, load the servos, and crack at the pleats. A PLA bar is fine for a fit test with both servos of a brow moving together. |
| Q13 | The EyeMech STEP is ε3.1, and the brief says ε3.2: which one will be printed? The mouth STEP has 9 MG90S servos, and the brief says 8: is the ninth the tongue, and is it kept? | The printed parts must match the CAD the skull is built around. | **Eyes:** ε3.1 and ε3.2 have the same outer geometry (see the comparison in §3). Print ε3.2-PIP MG90s and lay out with the ε3.1 STEP (D11). **Tongue:** keep it if it is no hassle (D10). (2026-10-15) |

## 8. Decisions

| ID | Decision | Options | Recommendation | Status |
|---|---|---|---|---|
| D1 | Where the CAD lives | A: code in this repo, STEP opens in Onshape. B: model in Onshape, this repo only checks exports. C: custom parts in code, references and sculpt work in Onshape. | A. All checks and renders run from the code; Onshape gets a fresh STEP after each accepted change. | open (Q6) |
| D2 | Frame and side naming | §4 | as §4 | proposed |
| D3 | Brow mechanism concept | A whole-brow plate / P two snap pads on one pivot / B four-bar / C curved track | **P** with a 2:1 four-bar drive ([design note](DESIGN_NOTES.md#d3-and-d5-eyebrow-mechanism-concept-and-motion)) | **working design 2026-10-15**; the bench test confirms it |
| D4 | Head size and proportions | 1.0 / 1.1 / 1.2 / 1.3 × an average adult; average or boxy temples; lip line ([design note](DESIGN_NOTES.md#d4-head-size-and-shape)) | **A2: 1.2 × with `boxy_temples`, lip line 3 mm lower**: the smallest head where everything fits at rest with room for a skull shelf between the modules. Head 187 wide, 252 deep, 284 chin to crown | **decided 2026-10-15**: A2 ("loving this... let's move to the next phase") |
| D5 | Brow motion coupling | §6 M2 | raise = surprise/worry, lower = anger | **implemented** in v1 (inner/outer 1.43); the team hasn't commented yet |
| D6 | Skull fasteners | M3 + heat-set inserts; M2.5 + inserts; self-tapping | M3 + heat-set inserts | proposed (Q7) |
| D7 | Eyelid skin | separate moving eyelid skins / main skin forms the lids | decide in M1 from lid clearance | open (Q11) |
| D8 | Electronics location | PCBs in the base / PCBs in the head | in the base, per brief §10 | proposed |
| D9 | Skull modules | backbone with bolt-on upper and lower modules (§5) | as §5 | proposed |
| D10 | Tongue servo | keep / leave out | keep: it sits inside the mouth module and the α2.0 mouth board has a channel for it. It costs one more lead through the neck. If it fights the jaw sweep or the skin, raise it again | **decided 2026-10-15**: keep if no hassle |
| D13 | Art style and the sculpt base | campy flat-top Frankenstein built into the skull / a normally proportioned head / sculpt it all in clay | — | **decided 2026-10-16:** a normally proportioned head, not the traditional campy look. The style may change later. The sculpt base covers the whole head (face, cranium, nape, neck). |
| D14 | The mechanical base | our own skull frame around Cogley's modules / Cogley's whole Robot Head α2.0.33 as the base, with ours built on top | — | **decided 2026-10-16 (team):** his head is the base. We keep his frame, mouth, eye mount, brows and fan; our skin-support shell replaces his robot outer shell. The face stays normally proportioned (D13). |
| D17 | The face's base shape | our placeholder face (a proxy made from a few cross-sections) / Cogley's own head | — | **decided 2026-10-16 (team):** Cogley's. Our placeholder looked nothing like a human. The sculpt base and the skin follow his complete head, outer shell included, and his mouth stays where he put it (Q16). Our skull pieces, shelf, cradle, strap and sculpt base v1 retire. |
| D18 | Electronics for the eyes and brows | Cogley's 2 Eyes/Brow/Neck boards / one mouth board with a merged program / a mouth board in place of each | A mouth board in place of each: the team has many mouth boards and Picos, and his eye and brow programs run on one with only the mode switch moved (`firmware/`) | **decided 2026-10-16:** 3 mouth boards (mouth master, eyes, brows); see `firmware/README.md` |
| D19 | What the sculptor works on | the sculpt base v2 (a wrap of Cogley's head) / a face mask shell | — | **decided 2026-10-16 (team):** a face mask: a thin shell of a man's face (MakeHuman CC0 face, `cad/face_mask.py`), its eyes on the eye mechanism and its lips on Cogley's lips, clear of his head (≥ 6.9 mm). The sculpt base pieces are not printed. |
| D15 | Brows | our v1.1 (1 servo per brow, already printed) / Cogley's (2 servos per brow, flexible TPU bars) | Cogley's: they are designed and proven in his frame (ours would need new mounts there), and an inner and outer servo per brow gives angry and happy shapes. They cost 2 more MG90S and a TPU print | **decided 2026-10-16:** Cogley's (the team would print his if it is the safer option, and it is). Ours stays as the bench backup. |
| D16 | Eyes | reprint his head's EyeMech variant / keep the printed ε3.2 MG90s-A set | Keep: the structural parts are identical, and the printed set's motion clears his frame (§3). If a part doesn't mount on the bench, reprint only that one from his Eyes plate (the long pivot holder and the eye adaptors are the likely ones) | **decided 2026-10-16:** keep the printed set. **Amended 2026-10-25:** the A horns (shaft hole Ø4.92) slip on the team's servos and B (Ø4.72) grips (sizing plate), so the 6 horn-carrying objects are reprinted in size B (`output/plates/eyemech_B_horn_parts_plate.stl`) |
| D20 | How the plaster mold is made over the clay face | a mold box poured solid / a printed base with a plaster and burlap shell laid up over it | The mask's rim is a saddle (8 mm above the base by the ears, about 130 at the chin and forehead ends), so a flat board leaves the ends open; a solid pour would take about 15 L of plaster. A shell 15-20 mm thick is about 3 L, and the printed base seats the mask the same way again for the silicone cast | **proposed 2026-10-20:** the printed base (`cad/mold_base.py`, [PLASTER_MOLD.md](PLASTER_MOLD.md)); one-piece shell with the tucks filled in clay, or three pieces, is the team's call |
| D21 | Skin silicone | Ecoflex 00-30 / PlatSil Gel-OO30 (the brief's candidates, BRIEF §6) / Smooth-On Dragon Skin FX-Pro | — | **decided 2026-10-15 (team; recorded here 2026-10-24): Dragon Skin FX-Pro** (in hand by 10/19; a unit also on the Blick receipt 10/21), for the M4 snap pads and every face cast, brushed on in layers; replaces the brief's two candidates. Smooth-On TB: Shore 2A; mix 1A:1B by weight or volume; pot life 12 min, demold 40 min at 23 °C; don't cure below 18 °C (65 °F); tear 61 pli (Die B); elongation 763 %; tensile 288 psi; shrinkage <0.1 %; SG 1.062; mixed viscosity 18,000 cps. It is firmer and tougher than a 00-30 silicone: better at the snaps (R4), more pull on the servos (R11). Kit: Ease Release 200 (release); mold sealer acrylic spray, thinned petroleum jelly or SuperSeal, **never shellac** (Smooth-On: it makes silicone bond); THI-VEX (brush-on layers, 0.5-2 % of Part A); Silc Pig (colour); Slacker (optional, softens it but lowers tear strength). Platinum-cure, so no sulfur clay and no latex near it |
| D25 | The neck (Q17) | a column up the middle (hits the jaw) / a spine behind the jaw into the frame's nape / hang the head from the cap | The jaw's swing leaves only the back of the neck free: y behind −92.5 at overtravel. The frame's nape ribs are the nearest fixed structure (z 135 at the sides). The head is bolted, not balanced: its mass (about 3 kg with skin) sits about 50 in front of the spine, a 1.5 N·m lean that 4 × M4 into the pedestal carry easily; the whole canister (about 5 kg, Ø340 footprint) needs a 13 N push at the top to tip | **proposed and modelled 2026-10-28** (`neck` in `cad/enclosure.py`): a Ø100 tube to z 70 on a 12 mm foot (4 × M4 inserts), a 30 × 80 hollow spine at y −125..−95 up to z 170, its top just under the frame's nape members (a cross member at y −101..−95, x ±24, underside 172; side rails at x ±36..40, underside 173..176), notched at x ±29..41, y −117..−94 for his two ribs that come down to z 150 there. No overlap with any of his parts at rest; the jaw clears it by 9.6 mm at 25° and 2.5 mm at 35°. ASSUMPTION: 4 × M3 up into inserts heat-set into his members, shimmed |
| D26 | Enclosure built in a day (2026-10-29) | v0 as modelled (31 prints, about 130 printer-hours) / thin halves plus sheets | Two printers and under 24 hours. Every big area becomes a 1 mm PETG sheet: the window is one full tube (the back see-through, the human's call), the base's wall a painted band between two printed rims; the prints are 1.2-1.6 mm plates with ribs, in halves turned 45° on the bed, the pedestal a D 90 tube; the back column, the deck ring, the slit rings, the lid, the inserts are gone. About 27 printer-hours | **decided 2026-10-29**: v1, `cad/enclosure.py` |
| D24 | The enclosure's clear sheet | rolled 1 mm PETG / rolled 1 mm polycarbonate / a bought Ø300 cast acrylic tube | PETG is the cheapest, clear, cuts with a knife and cold-bends to R150 without crazing; polycarbonate is tougher but dearer and tints; acrylic sheet cracks at this bend, and a cast tube costs over US$100 and needs no column for the sheet. The blank is 644 × 458 (the arc plus 7 into each fork), so a 610 × 914 (24 × 36 in) sheet does it | **decided 2026-10-28** (the human left the choice to us): 1 mm clear PETG; v1 (D26) stands it between 1.8 mm lips, channel 2.4 wide, and adds a second sheet for the base's band |
| D23 | Enclosure (M8) | a bought specimen jar (Q5) / a printed canister: base drum and top cap in 4 quadrants each, a Ø240 deck disc and lid disc, a rolled 1 mm clear sheet (240°) standing in slits in both rings, a 120° opaque back column in 2 × 2 prints that hides the head's rear hatch and ties the cap to the base, a pedestal on the deck taking the neck's 4 × M4 and the Ø25 bore; the camera in the cap's front band, its lens flush behind a Ø8 hole among the vents, 10° down, the cable round the cap ring and down the column | Round, like the human's reference picture (2026-10-28); every piece fits the 256 bed; the base is a hollow bay for the power, the boards and the speaker, serviced through a floor tray; the fan's air leaves through the base's slots. Axis on the neck (y −70): the head clears the sheet by 31 at the face, 33 behind, 47 at the ears. The neck column from his frame to z 0 is still Q17 | **proposed 2026-10-28**, sizes fixed the same day with Q19, Q20 and Q21 answered: Ø340 outside, 638 tall, sheet Ø300 (the human left the size to us). Base bay: the power box and the two boards of the Head Power Wiring doc, a back hatch for the bank and the leads, the Sony SRS-XB12 on its side at the front behind a snap-out grille panel; the laptop stays outside; no lights. `cad/studies/enclosure_concept.py`, [process_images/2026-10-28_48_enclosure-concept-front-grille](../process_images/2026-10-28_48_enclosure-concept-front-grille/studies_enclosure_concept.png). Next: model it (`cad/enclosure.py`) with the neck spine (D25) |
| D22 | The eyeball's front | his eyeball as printed (a concave iris dish 14.4 mm across and 1.8 deep, with a 4 mm pupil hole) / the same eyeball with a plain round front | Plain: the dish and the hole are filled out to the eyeball's own R16 sphere, 8.5 mm and more in front of its centre; his socket, clips and back are unchanged. The lids' inside is R16.5 about the same centre, so the 0.5 mm gap holds at every pose, and nothing else in his mechanism or head reaches the filled part (`cad/studies/cogley_eyeball.py`) | **decided 2026-10-25 (team):** plain round front, `output/plates/cogley_eyeball_smooth.stl`. The iris and pupil are painted on |
| D27 | Keying the silicone skin to the eyelids | glue (Sil-Poxy, cures 40A, weak on PLA) / a printed interlock lattice on the lid / counterbored through-holes the silicone rivets through / a retaining lip at the lash edge | Through-holes: platinum silicone has no bond to PLA, so only geometry holds; a lattice can't print on a 1.6 mm shell standing on its edge, and the lash edge has no room for a lip (eyeball 0.5 mm behind, skull opening 1.9 mm in front). Each hole fills from the outside and cures into a mushroom rivet whose head sits in a counterbore inside the wall, so nothing protrudes and the lids move as before | **decided 2026-10-29:** `cad/lid_keyed.py`: 21–24 radial Ø2.2 holes per lid, Ø3.4 × 0.7 counterbores flush with the inner face, 5.0 pitch (0.97 mm rib between counterbores), 1.1 mm margin to every edge, through plain wall only (`LID_KEY_*` in params.py, ASSUMPTION until the test cast, Q22). Plate: `output/plates/cogley_lids_keyed_plate.stl`, his 4 print-in-place sets, size B |
| D28 | How the laptop reaches the eye board (Board 2) now that the head runs on two mouth boards off one battery (wiring guide 2026-10-26) | Cogley's `MouthMaster.py` on Board 1 with his 2-bit GPIO link and a merged eyes-and-brows program / two USB cables, one per board / one program on both boards with a UART link, Board 1 forwarding | The 2-bit link carries four states per function, but the slider tools, `frank/mouth.py` and Friday's performance engine move every servo by name at a steady frame rate, and the eye poses and brow expressions already live on the laptop. UART0 TX is GP16 and RX GP17 on a Pico, which are two of the five link jumpers already run, so only the GP16/GP17 pair has to cross | **decided 2026-10-29:** `firmware/pico_servo_ctl.py` on Board 2, and on Board 1 either that or `cogley_mouth_main.py` (TalkingHead's gliding MouthMaster, found on the mouth board, now with the same forwarding): a line `e <pin> <angle>` from USB is sent on over UART0 (GP16, 115200) to the other board, which runs it; GP16 is only driven after the first `e` line, so a straight wire is safe but carries nothing. `servo_controls.py --link`, `Mouth.link()`. Nothing comes back from Board 2 yet |
| D29 | When Frank remembers a stranger | offer near the end of a good conversation, after a yes and an age check (the bible v1.0, the prompt until 2026-10-30) / remember them the moment they give their first name when he asks who they are, and tell them so with the way out / never without a signed form | The creators want every stranger greeted, asked who they are and saved. Giving a name to someone who has just asked for it, and being told at once that he'll remember you and will forget you on request, is a lighter consent than a question-and-answer, and it keeps the greeting to one question (the bible: no interview). Children are still never stored; the age question goes | **decided 2026-10-30 (Anushhka):** remember on the name. `frank/system_prompt.md` ("Remembering people"), `brain.TOOLS`, CHARACTER.md §§ Strangers, Personal information, Facial recognition. A remembered visitor's return now carries a `Memory of NAME: met DATE; NOTE.` note (`faces.Gallery.memory`). Open: the sign at the jar must say it, and the memory store (README, Memory) still isn't built, so the note is the one written when they met |
| D12 | Tongue clash with a mouth servo when the jaw opens (M1 sweep) | A: trim ~3 mm off the tongue's back corner. B: leave it; the team's built mouth is the evidence. C: drop the tongue (18 servos) | A, then confirm on the bench | **decided 2026-10-15: B.** "Leave in the tongue, no need to modify it; I've printed this before and it's fine" |
| D11 | Which EyeMech to print and model | ε3.1 / ε3.2 snap-fit / ε3.2-PIP | ε3.2-PIP MG90s (A or B, chosen with Cogley's test plate) for both the print and the CAD. Source, in order of preference: a ε3.2 STEP exported from Cogley's Onshape; otherwise the public ε3.2 print parts, each snapped onto the matching ε3.1 part's position | **decided 2026-10-15**: use ε3.2 |

## 9. Risks

| # | Risk | Mitigation |
|---|---|---|
| R1 | The two Cogley modules were designed separately and may not fit one life-size head together. **Confirmed:** at 1.0× they overlap by 17 mm and stick out of the skull (§3, design note D4). | **Mitigated at rest** by 1.2× with boxy temples (D4); the margins are thin (0.7–2.5 mm), so the motion sweeps must confirm them. |
| R2 | The public Cogley downloads are meshes only. **Mostly resolved** by the team's STEP exports; the mouth file still has invalid solids. The EyeMech has no external mounting holes. | Trace the invalid solids in M1; clamp the EyeMech base rather than modify it. |
| R3 | Clone servos differ from the datasheet by about 1 mm. | Caliper real servos; slotted mounts. |
| R4 | Soft silicone tears at the snaps. | Fabric pads, shear loading, and the M4 cycle tests before the full skin. Dragon Skin FX-Pro (D21) tears less easily than a 00-30 silicone (61 pli), but the pads still get tested. |
| R5 | The module's jaw pivot may not sit where a human jaw hinges, which stretches the cheeks oddly. | Compare in M1; adjust skin fixing points or add slack zones. |
| R6 | 19 servos inside a closed skin inside a jar build up heat, and the MG996R jaw servos draw high current. Cogley's α2.0 head uses a 50 mm fan and a 5 V 10 A supply. | Room for a 50 mm fan and a vent path in the rear panel; flag current to the electronics plan. **D14:** his head has a fan bracket, but its vents are in the robot shell we drop, so under the skin the air path has to go out through the neck. |
| R7 | Schedule (Q1). | A reduced-scope plan if the date is fixed. |
| R8 | Licence terms on the Cogley designs (Q10). | Confirm before any commercial use. |
| R10 | The brow concept's working window is narrow: 3 of 2,431 pivots meet every limit, and it rests on the proxy forehead shape and assumed skin limits. | The sculpt replaces the proxy in M5. The study re-runs from `params.py` in about a minute; the bench test with a real skin sample sets the limits. |
| R12 | Cogley's head comes as meshes only (no STEP), so changing his parts means mesh booleans, and the OBJ is incomplete (2 brow servos missing). | Change his parts only where we must; check every mesh edit for watertightness; take missing parts from his 3MF. |
| R11 | MG90S torque against the unknown skin forces. Dragon Skin FX-Pro (Shore 2A, D21) is firmer than the 00-30 silicones first planned, so expect more pull. | The 2:1 four-bar halves the load; measure the brow force on the bench rig (M2/M4) with an FX-Pro sample. If the servos struggle, soften the mix with Slacker or thin the skin locally. |
| R9 | Cogley's mouth may have other near-contacts that only show up under motion. The tongue clash had a 0.49 mm gap at rest. | `pose_sweep` treats only touching pairs as designed contacts and flags any designed overlap that grows; it is re-run whenever a range or a placement changes. |
| R13 | The face mask wraps past its widest line by the ears (up to 22 mm) and along the jaw (6-9 mm), so a one-piece rigid mold locks onto it. | Fill those strips with clay down to the base (one piece; the skin comes out thicker there and is trimmed) or make the mold in three pieces (front and two sides). `mold_check.py` reports the strips. |

## 10. Deliverables map

| Brief §11 deliverable | Milestone | Produced as |
|---|---|---|
| A. Skull assembly | M1, M3 | `cad/skull_*.py` builders, STLs in `output/stl/`, assembly STEP |
| B. Eyebrow mechanism | M2 | `cad/brow.py`, `cad/brow_rig.py`, exploded view |
| C. Snap attachment system | M4 | `cad/snap.py`, test molds, pad stencil, unsnap tool |
| D. Sculpt and mold reference | M5 | `cad/armature.py`, mold core, skin envelope STEP, `attach_points.csv` |
| E. Documentation | all | `docs/`: BOM, PRINT_GUIDE, ASSEMBLY, MOTION_NOTES; STEP for Onshape (D1); exploded diagrams |

**Checks to add to the pipeline as the model grows:**

| Check | Added in | Verifies |
|---|---|---|
| `pose_sweep` (**running**) | M1 | No collisions at any pose; clean limit per axis, naming the first pair to collide; reserved volumes against every part and every swept pose |
| `layout_check` (**running**) | M1 | Rest pose: eyes and lids inside the outer skin, lip plates inside the skin's inner surface, everything else inside the skull; closest approach between the modules; fit table for each head scale |
| `skin_clearance` | M1–M3 | The skull itself and every moving part at every pose stay inside the skin's inner surface (extends `layout_check` once the skull and the sweeps exist) |
| `service_check` | M3 | Every servo and module has a tool path and a way out |
| `cable_check` | M3 | Every lead has a route to the neck that clears the parts at every pose |

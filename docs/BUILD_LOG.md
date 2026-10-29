# Build log

A dated record of every design session, test print and bench test for the
Frankenstein animatronic head. Newest entry first. The plan it works through
is [PLAN.md](PLAN.md); the brief is [BRIEF.md](BRIEF.md).

## How entries are written

One entry per working session or physical test. Use this shape, and leave out
any heading that has nothing under it:

```
## YYYY-MM-DD — <milestone> — <one-line summary>

**Done:** what changed, in a few bullets.
**Numbers:** params that changed, old → new (name = value), and why.
**Check:** the check.py result line, e.g. `check: PASS (0 hard failure(s), 1 warning(s), 31 s)`.
**Renders:** links to the views and print-check images looked at.
**Physical:** what was printed or tested, on which printer and material, and what was measured.
**Decisions:** decision IDs from PLAN.md that were made or changed, with the answer.
**Problems:** what went wrong or is still open.
**Next:** the next concrete step.
```

Rules:
- Record measured values with the param they replace, e.g. `MG90S_BODY_L = 22.8 (MEASURED, was 22.5 DATASHEET)`.
- Bench results override CAD. Record them with the date and the conditions (e.g. "brow travel 9.5 mm bare, 7.0 mm under the 4 mm silicone sample").
- Note every print that is kept as a reference part, so later changes to its params are known to break it.

---

## 2026-10-29 — M8 — Enclosure redesigned to print in a day (v1)

**Done:**
- The human has two P2S printers and under 24 hours; v0's 31 prints were about 130 printer-hours. v1 (`cad/enclosure.py`, D26) is eleven thin prints plus two 1 mm PETG sheets, about 27 printer-hours: cap halves (1.2 mm top, ribs, vents, a 40 mm skirt, two hanging lips for the window's top edge, three stops for the webcam, seam walls), deck halves (1.6 mm plate round the pedestal, the window's lower lip, a rim the base's band wraps, ribs, the lead slot), bottom ring halves (a narrow plate with the band's lower rim and four ears to the tray), the tray (ribs, bosses, speaker saddles, bank rails), a D 90 pedestal tube with an inward flange, the two panels (built from bars), and the neck (walls 2 to 2.5 mm). The halves turn 45° on the bed (a D 292 half spans 249). The window is one clear tube, the back see-through (the human dropped the column); the base's wall is a painted PETG band between the rims.
- `enclosure_check.py` follows: the band is checked like the sheet, the bed test uses the print pose, the renders are redrawn. `cad.yaml` lists the eleven parts; the 24 superseded v0 print files are removed.
- Found and fixed on the way: the bank and buck collided with a conical pedestal (now a D 90 tube; the bay laid out round it, the boards on the bank, the bank and buck riding on the tray's ribs); the cap's flat facet cut through the window (the webcam now hangs inside the window and looks out through it); the speaker's belly sat on a rib (the saddles lift it 6.5); a D 2.6 self-tapping hole in a 3 mm rib left 0.2 mm walls (bosses, set 0.5 inside the tray's edge: tangent to it they broke the mesh); a slotted curved panel tessellated with dents again (built from bars instead); the tray's radial ribs now sit 0.5 under the ring ribs (coplanar tops broke the mesh).

**Numbers:** ENC_* rewritten (`ENC_R_OUT` 170 → 146, `ENC_SHEET_R` 150 → 138.2, lips 1.8 × 8, rims 2 × 10, plates 1.6, cap top 1.2); the head's clearance 31 → 19 at the face, 21 at the nape; the sheet blank 891 × 477 (a full tube) and the band 928 × 109 derived in params.

**Check:** fast checks on the enclosure: builder clean (11 watertight bodies), `NO OVERLAPS`, `PRINT CHECK OK`, `ENCLOSURE OK`. Full `check.py`: see below.

**Renders:** `output/check/enclosure/enclosure.png` (snapshot after the full run).

**Decisions:** D26 (the one-day version); D23 and D25 stand, D24 extended (lips instead of slits, a second sheet).

**Problems:** the bank's rails, the boards' standoffs and the power box's fixing are tape and assumption; the webcam looks through 1 mm of PETG; the spine's bolting into his frame is still an assumption.

**Next:** print the neck and the pedestal first and offer them up to the head; the tray and bottom rings next; then the rest. Buy the two PETG sheets, paint, M3 screws and nuts.

## 2026-10-29 — M3 — Mouth sliders: set the mouth's open and closed angles by hand

**Done:**
- `firmware/mouth_controls.py`: a slider window for the mouth board's eleven servos (jaw, lips, corners, tongue), the mouth's counterpart of `servo_controls.py`. Under the sliders a table of Cogley's poses from `MouthMaster.py` (mouth closed and open, lips rest, down and up, tongue down and up, corners narrow and wide, smile, frown), each with GO (eases the servos to the pose over 0.4 s) and SAVE (stores the sliders as that pose). Saved poses go to `firmware/mouth_poses.json`, keyed as his `poses` dict, so they can be pasted into a team copy of his program. REST FACE sends his start-up pose plus the lips at rest, one group every 300 ms; OPEN / CLOSE x3 chews between the saved OPEN and CLOSED. The port `demo` runs it without a Pico, and `demo --selftest` presses every button and checks the saved file.
- `firmware/pico_servo_ctl.py`: drives GP4–GP15 (was GP4–GP13), for the tongue on GP14. It has to be copied to the Pico again as `main.py`.
- `firmware/README.md`: the mouth window.

**Check:** no CAD change. SELFTEST_RESULT

**Problems:** Cogley's L and R for the mouth servos are not matched to the face's sides yet. Which of his angles fit our horns is unknown until the mouth is on the bench; the sliders run 20..160, 20° past his angles each way, so go slowly near the ends and Loose a servo that buzzes. The eye window (`servo_controls.py`, EYES ALIVE) is still uncommitted from 2026-10-28.

**Next:** plug the mouth servos into the mouth board, find CLOSED (teeth just together, no servo buzzing) and OPEN (the jaw's stop) on the two jaw sliders and SAVE them; then the lips and corners; then put the saved angles into a team copy of `MouthMaster.py`.

## 2026-10-28 — M8 — Enclosure and neck modelled (v0)

**Done:**
- `cad/enclosure.py` builds the canister and the neck in the assembled pose, 31 prints, all inside the 256 bed: base wall quadrants (seams at 45/135/225/315) with the bottom lip, an inward top flange with a 51° chamfer under it, seam tabs (M3 insert one side, clearance the other), segmented vent slots in the side walls, the speaker opening in the front and the hatch opening in the back; deck ring quadrants (seams at 0/90/180/270, staggered from the walls) with the lower slit for the sheet, the lip the deck drops into and the column's foot inserts; the floor tray with the speaker saddles and the bank's rails; the deck disc; the solid pedestal (prints upside down); the grille and hatch panels (4 × M3 each from outside, the hatch with a lead notch); the back column in 2 × 2 pieces with forks the sheet's ends tuck into, lap tabs under both seams (radial screws from outside), a foot flange down into the deck ring, a top flange screwed from inside the cap, the centre rib; the cap's slit ring quadrants, cap wall quadrants with a flat front band for the webcam (lens hole Ø12, cradle stops), the cap top ring quadrants with the lid recess, the lid; the neck (foot with 4 × M4 inserts, Ø100 tube to z 70, hollow spine to z 170 with a 45° roof, notched for two of Cogley's ribs). The clear sheet and the bay's contents are reference shapes in `output/ref/enclosure/`.
- `cad/enclosure_check.py`: the head's clearance to the sheet and cap, the sheet against every part, the neck against every one of Cogley's parts at rest, the jaw swept 0 to 35° against the neck, the bay's contents against the parts and each other, and every piece against the bed; a sheet of renders. In the pipeline (soft, `ENCLOSURE OK`), parts in `cad.yaml`.
- The skull v0 pieces (retired, D17) are out of the assembly in `cad.yaml`: the neck and pedestal stand where its neck was.
- Docs: PRINT_GUIDE (M8 table and print order), ASSEMBLY (the enclosure's assembly order), BOM (inserts and screws counted: 86 M3 inserts, 86 M3 screws in four lengths, 4 M4; about 3 kg PLA), PLAN (M8 status, D25 as modelled).

**Numbers:** the ENC_* and NECK_* sections of params.py are new. Found by the checks on the way: the spine's top 190 → 170 (his nape members' undersides are at 171–176 over the spine's footprint; two ribs come down to z 150 at x ±32, so the spine is notched at |x| 29–41, y −117..−94); the chamfers 45° → 51° (`ENC_CHAMFER` 1.25; at 45° print_check flagged them); the vents in 20 mm segments (bridges of 20, not 145) and below the chamfers; the openings' tops at −72 (under the flange chamfer), their 110 mm bridges on supports; the tray Ø250 (the bed), so the bank sits at y' −68 and the buck under the pedestal, turned 90°; the webcam on the slit ring (z 416) with the band set in 9 so its corners clear the top flange's wedge.

**Check:** fast checks on the enclosure alone: builder clean (31 watertight single bodies), `NO OVERLAPS`, `PRINT CHECK OK` (the 31 parts), `ENCLOSURE OK` (head 31.2 inside the sheet, crown 48.7 under the cap; the jaw clears the neck by 9.6 mm at 25° and 2.5 mm at 35°; no overlap with any of his parts, the spine's top 1.5 under the frame). Full run after the review fixes: `check: PASS  (0 hard failure(s), 12 warning(s), 2571 s)`; the 12 warnings are the sculpt base's old thin spots. A full run takes 43 min, 41 of them print_check.

**Renders:** [process_images/2026-10-29_50_enclosure-v0](../process_images/2026-10-29_50_enclosure-v0/enclosure.png) (the enclosure sheet, the design views, the print check).

**Review:** the cad-reviewer ran the full check on the first complete model and found five things, all fixed before the final run: the webcam cradle's three stops were loose bodies (now on a floor joined to the cap wall); the webcam lead's slot landed on the column's top flange (notched); the cap's column screws were unreachable in the written order (the slit ring now goes on first); the sheet blank omitted the forks' tucks (644 × 458, derived once as `ENC_SHEET_BLANK` and checked); the spine's top had no way in for the leads (a 40 × 16 opening). It also noted the bank does not pass the hatch (reach only) and that the tray comes out only with the column and cap off; both are in ASSEMBLY.md.

**Decisions:** D23 and D25 as modelled. Three tessellation surprises worth remembering: the panels' slotted curved face and the cap's cut front band exported with dents and open edges at tolerance 0.05 (the shapes were valid); they export at 0.01.

**Problems:** the webcam's tilt (10° down) is not modelled: the cradle holds it level. The spine's bolting into his frame and the inserts in his nape members are an assumption until the printed neck is offered up to the printed frame. The sizes of the bank, buck and boards are listing sizes.

**Next:** print the neck and the pedestal first and offer them up to the head; then one base wall quadrant and one deck ring quadrant to prove the slit (with a strip of the PETG), the seam tabs and the flange screws; then the rest.

## 2026-10-28 — M8 — Enclosure concept: a printed canister round the head

**Done:**
- The human wants the display case printed, not bought: a round canister like a sci-fi specimen tube (reference picture in the session), with a printed base and top, a clear sheet standing in slits in both, a hollow base for the power and the boards, the head mounted on the base, and a printed, opaque back that hides the mechanism's rear. `cad/studies/enclosure_concept.py` draws the idea to scale around the sculpt wrap and the face mask: side section, front view and plan view, with the numbers in `enclosure_concept.md` beside it.
- Concept (D23): axis on the neck's axis (y −70). Sheet Ø300 inside, 1 mm rolled PETG or polycarbonate, 240° of the circle (blank 630 × 458), in a 6 deep slit in the base and a 12 deep slit in the cap. Rings Ø340 outside, each in 4 quadrants (170 × 170 boxes), with a Ø240 deck disc and lid disc printed whole. Base 118 tall with a 96 mm bay; window 440; cap 80; overall 638. A 120° back column, 2 wide × 2 tall prints with a centre rib over the seam, hides the rear hatch and ties the cap to the base. A pedestal Ø130 to Ø110 × 40 on the deck takes the neck's 4 × M4 (50 square) and the Ø25 cable and air bore; the fan's air goes out through the base's slots. The head clears the sheet by 31 at the face, 33 behind and 47 at the ears; the crown is 49 under the cap.
- No lights in the enclosure (human): the room is lit. The LED ring under the cap's lip is dropped, and the camera is a plain module, not NoIR with IR LEDs.
- Camera (the human asked for a hiding place): in the cap's front band at z 425, the lens flush behind a Ø8 hole among the cap's vent slots, tilted 10° down at a standing visitor; the board sits in a pocket in the front cap quadrant and its cable runs round the cap ring and down the hollow back column to the base. That height is about the visitor's eye level on a table; the base front would look up at 40°. Not inside the head: the eyes are now plain (D22) and move, and the skin covers everything else.

- Camera named: a Logitech 1080p webcam (taken as a C920-class bar, 94 × 29 × 24, 78°, fixed 1.5 m USB lead). It sits in a cradle against the cap's front wall, lens behind a Ø12 hole (a Ø8 hole would clip its view: the lens is a few mm behind its glass). Its two mics hear through the vent slots, so no mic in the base.
- Base contents settled (human; the Head Power Wiring doc on claude.ai, 2026-10-26): the power box (UGREEN 145 W power bank or the JUYOON 140 W charger, PD trigger at 20 V, 20 A buck at 5.30 V, fuses, WAGO buses, 1000 µF) and the two mouth boards, all on the floor tray. The laptop stays outside: Board 1's micro-USB and the webcam's USB lead leave through a hatch at the back of the base under the column's foot, where the bank is reached too. The sheet is 1 mm clear PETG (D24, our choice). Size fixed at Ø340 × 638.
- Speaker in the base after all (human): nothing ordered yet. First pick was a Dayton ND65-4 driver with a PAM8403 amp; the human has no time to solder, so a ready-made speaker. The Anker S330 speakerphone was too dear, the Amazon Basics pair was the fallback, and in the end the human uses the Sony SRS-XB12 already at home: a Ø74 × 92 cylinder on its side in a cradle at the front of the tray, driver end at a snap-out grille panel (about 110 × 84) in the base's front wall, which also gives access to its buttons and aux socket (the human wants the sound out of the front, through a grille); 3.5 mm aux lead from the laptop, charged from the bank's USB-A port. Aux, not Bluetooth: its delay would put the voice behind the mouth. To test: plays while charging; auto standby after about 15 min of silence (keep a faint sound playing if so).

- Neck (the human asked how a head with no neck and a swinging jaw sits on the pedestal): Cogley's frame is the head's only fixed structure; the jaw hangs from it and swings in front. Measured from his parts in our frame: frame's lowest bar z 134.6 (x ±34, y −84..−74), nape ribs down to z 135 at the sides; jaw at rest y −75..10, z 106..182; open 25° y −85, z 88; overtravel 35° y −92.5, z 82. Proposal (D25): a Ø100 column on the pedestal to z 70, then a 30 × 80 spine at y −125..−95 up to z 190 bolted into the nape ribs; the skin's neck stub covers it from z 40. The head is bolted, not balanced; the canister's weight and Ø340 footprint hold it.

**Renders:** [process_images/2026-10-28_49_enclosure-concept-neck-spine](../process_images/2026-10-28_49_enclosure-concept-neck-spine/studies_enclosure_concept.png) (earlier versions: [48, front grille](../process_images/2026-10-28_48_enclosure-concept-front-grille/studies_enclosure_concept.png), [47, speaker by the hatch](../process_images/2026-10-28_47_enclosure-concept-sony-xb12/studies_enclosure_concept.png), [46, Amazon Basics pair](../process_images/2026-10-28_46_enclosure-concept-cheap-speakers/studies_enclosure_concept.png), [45, Anker speakerphone](../process_images/2026-10-28_45_enclosure-concept-usb-speaker/studies_enclosure_concept.png), [44, soldered driver](../process_images/2026-10-28_44_enclosure-concept-speaker/studies_enclosure_concept.png), [43, no speaker](../process_images/2026-10-28_43_enclosure-concept-power-box/studies_enclosure_concept.png), [39, no camera](../process_images/2026-10-28_39_enclosure-concept/studies_enclosure_concept.png), [40, with an LED ring](../process_images/2026-10-28_40_enclosure-concept-camera/studies_enclosure_concept.png), [41, no lights](../process_images/2026-10-28_41_enclosure-concept-no-lights/studies_enclosure_concept.png), [42, webcam](../process_images/2026-10-28_42_enclosure-concept-webcam/studies_enclosure_concept.png)).

**Decisions:** D23 proposed and sized (the printed canister, Ø340 × 638); D24 (1 mm clear PETG sheet); D25 proposed (the neck spine, Q17). Q5 closed (no bought jar). Q19, Q20 and Q21 opened and answered the same day (base contents; sheet; a Logitech 1080p webcam on the laptop outside).

**Problems:** the neck spine (D25) is a drawing, not a model yet; where exactly it bolts into the nape ribs comes from his frame's mesh when it is modelled. The bay's contents are listing sizes, not measured; the webcam model is assumed C920-class. PLAN D18 says three boards; the wiring doc (newer) has two.

**Next:** model the base, cap, column, pedestal and webcam cradle in build123d (`cad/enclosure.py`) with a check against the head at every pose; measure the bank, buck and boards when they arrive and put them in params.py.

## 2026-10-28 — M3 — Eyes shut when the animation stops

**Done:**
- `eye_anim.py`: `rest()` (what STOP EYES sends) now centres the eyes with the lids at the saved SHUT pose, the same eye pose as NEUTRAL FACE. It used to leave them open. Checked against `eye_poses.json`: LLL 84, LLR 67, CUR 160, CLR 130, CUL 30, CLL 105.

**Problems:** Cogley's `neutral()` in `eyes_mouthboard.py` is his "Open Eye" command and still opens the lids, and his "Closed Eye" (`calibrate()`) sends 90 to every servo, which on the team's build is not shut. Both wait for the measured poses to go into that file.

## 2026-10-27 — M3 — Eyes alive: random look-around and blinking

**Done:**
- `firmware/eye_anim.py`: a random idle animation for the EyeMech. The eyes make small shifts, glances and returns to centre with eased moves, and the lids blink about 18 times a minute (simulated over 10 min), with some double and slow blinks and a blink on some big glances. The top lids follow the gaze up and down (UD_UP = +1 assumes a higher UD angle looks up, as in Cogley's `eyes.py`). The lids move only between their saved SHUT and OPEN angles. It uses only `random`, so it can also run in MicroPython.
- `servo_controls.py`: an EYES ALIVE / STOP EYES button runs it at 50 Hz through the slider link. New buttons save the eye sliders as the lids' SHUT pose, the lids' OPEN pose or the eyes' CENTRE, in `firmware/eye_poses.json`. NEUTRAL FACE now uses the saved shut and centre angles for the eyes, in place of 90.
- Tested with a stand-in serial port: the animation drives only GP8–GP13, the lid angles stay between shut and open, and stop, NEUTRAL FACE and close all work.

**Physical:** the human set the eye poses on the sliders (now the defaults and in `eye_poses.json`): shut CUR 160, CUL 30, CLR 130, CLL 105; open CUR 128, CUL 118, CLR 160, CLL 31; centre LLL 84, LLR 67. Each lid opens the way Cogley's `eyes.py` does (top right and bottom left down, the other two up). The right eye's shut angles sit at the ends of their sliders, far from Cogley's 90, so those horns sit well off his angle. A second "Lids SHUT" save by mistake stored a near-open pose; it was put back by hand from the screenshot.

**Next:** run EYES ALIVE and check that the top lids rise when the eyes look up (otherwise set UD_UP = -1).

## 2026-10-27 — M4 — Neutral face for fitting the skin

**Done:**
- `servo_controls.py` has a NEUTRAL FACE button: eyes straight ahead, lids shut, brows level, one servo every 150 ms. It first sent 90 to every servo (Cogley's `neutral()` and `Brows.py`). The eyes now use the measured shut and centre angles (entry above); the brows stay at 90.
- The mouth neutral was set by eye in `lip_tester.py` (mouth board, COM8) and saved to `LARS 9001/HeadTest/cogley_neutral.json`: LUL 90, LUR 90, LLL 55, LLR 78, CUL 90, CUR 80, CLL 120, CLR 70. The tongue is at 130 (down) and the jaw is at 0.00 (closed), with the jaw width at 40. TalkingHead.py now rests the lips and corners on these angles, in place of 90 for the lips and his narrow pose for the corners (CLL 90 → 120, CLR 90 → 70).

**Physical:** the human called this the perfect neutral (eyes closed, mouth closed) for working out the skin attachment. The eyes' shut and centre angles are in the entry above.

**Problems:**
- The mouth board's own start-up and `rest` pose (`cogley_mouth_main.py` REST: jaw closed, tongue down, his narrow corners, lips unpowered) is not this neutral. After a power-up, "All to neutral" in `lip_tester.py` sets it.
- The slider window raised a SerialException on close after the eye board's USB was pulled: `close()` sends "off" to every servo and the port was gone. The window had to be killed. It does no harm, but `close()` should ignore a missing port.

**Next:** check that the brows sit level at 90.

## 2026-10-26 — M3 — Slider bench test: JR brow good, the JL brow servo is faulty

**Done:**
- Slider window (`servo_controls.py`) run on the bench board's Pico 2 at COM9, with `pico_servo_ctl.py` as `main.py`.
- Eye socket labels checked against the silkscreen in Cogley's mouth board PCB file (`ProDoc_Mouth Board_2025-04-16.epro`): JL, JR, LUL, LUR, LLL, LLR, CUL, CUR, CLL, CLR, TON, EXA in one row, each socket marked S / + / −. The eyes use LLL (left/right), LLR (up/down), CUL (bottom lid, head's right), CUR (top lid, head's right), CLL (bottom lid, head's left), CLR (top lid, head's left).

**Physical:**
- The brow on JR (right outer, GP5) runs well.
- The brow servo on JL (left outer, GP4) turns far less than JR for the same command, and not at all from 90 toward 0. With the horn off, the bare shaft still turned only a little. With the JL and JR plugs swapped, the weak servo stayed weak on the JR socket and the good one ran fully on the JL socket. The fault is in that servo, not the board, the socket or the code.

**Problems:** the eye limits in `eyes_mouthboard.py` are still Cogley's (LR 40–140, UD 60–140, TL 90–160, BL 90–30, TR 90–30, BR 90–140; lids shut at 90). They have not been measured on the team's build.

**Next:** mark the faulty servo and replace it. Press 90 before fitting the new servo's horn, so the brow sits mid-travel. Then measure each eye servo's free range with the sliders and put the numbers in `eyes_mouthboard.py`.

## 2026-10-25 — M3 — EyeMech and brow servos on the bench: electronics work, horns slip on the shafts

**Done:**
- One spare mouth board drives all 10 eye and brow servos for the bench. The eyes are on their usual sockets (LLL left/right, LLR up/down, CUR/CUL right-eye top/bottom lid, CLR/CLL left-eye top/bottom lid, sides as seen from the front). The brows are on JL/JR/LUL/LUR for this test only.
- Its Pico is a **Pico 2 (RP2350)**. It was blank, so it got MicroPython v1.29.0 for RPI_PICO2. Cogley's guide links the RP2040 build, which does not run on it.
- New in `firmware/`: `eyes_brows_bench_test.py` (one servo at a time from Thonny), `pico_servo_ctl.py` (on the Pico as `main.py`, takes slider positions over USB) and `servo_controls.py` (slider window on the PC, one slider per servo, every servo loose until touched).
- Read Cogley's ε3.2 assembly guide and compared his MG90s A and B print files part by part.

**Physical:** all 10 servos turn when commanded, so the wiring, power and program are fine. The eye mechanism does not follow: the servo shafts turn inside the printed horns, even with the horn screws tight. On first power-up at 90° something buzzed; everything was switched off and then tested one servo at a time.

**Problems:**
- **The horns hold the shaft by a press fit only.** Each printed horn has a plain round shaft hole with no teeth, 2.9 mm deep, and a Ø2.6 hole behind it for the screw. The servo's splines have to cut into the plastic. The screw only keeps the horn on and cannot stop it turning. The horns come joined to their parts (print-in-place): the 4 lid horns to the lid sets, the up/down horn to the Y-axis set, the left/right horn to X-axis part B.
- **Size A was printed without his fit test.** A and B differ only in those 6 horns: shaft hole Ø4.92 (A) or Ø4.72 (B). Every other part is identical. His `Testing Plate.3mf` (the servo sizing plate, 3.6 mm thick like a horn) has one hole of each size, to try on a real servo before choosing.
- Manual step 2.13's sides: its pictures call x < 0 the head's left, but PLAN §4 has +x as the head's left. The socket for each servo position is unaffected. Which side Cogley's code means by L/R in TL/TR/BL/BR is still unconfirmed; the lid directions will show it once the horns grip.
- **Mouth (same evening, mouth board on COM8, `HeadTest/cogley_mouth_main.py`):** the jaw ran backwards (slider toward open closed it, smoothly). That is the symptom of JL and JR on each other's sockets. The manual puts every "L" mouth servo (JL, LUL, LLL, CUL, CLL) at x < 0, which is the head's right in our frame. If the mouth was plugged by the manual, its sides are mirrored, and the lip and corner pairs are swapped too. The jaw was still reported backwards after the plug swap was suggested (whether the plugs were swapped is not recorded), so the board now turns the jaw the other way in software (`JAW_DIR = -1`, command `jawdir`), matching the plugs as they are now. Whether the lip and corner pairs are swapped is checked against his poses (lips_up should raise every lip). Until that is known, the manual's side labels stay as they are. **Lower lips:** LLL was dead and LLR barely moved; their plugs were on each other's sockets. The team swapped them back (2026-10-26). That is the second mouth pair found mirrored. After that, both plugs had been put on the wrong way round (no power, silent); once turned round, LLL still barely moved. One of its M2 tab screws in the jaw base had stripped, so the servo rocked. The team refitted its horn and hot-glued the servo body. It moves fully now. **To do:** re-set or replace that M2 insert and screw it down properly.
- TalkingHead's lips barely showed next to the jaw; they now move ×2 of the planned shapes (`--lip-gain`, default 2).
- The mouth board's jaw width is now a setting (`jawdeg`, default his 40°, capped at 70°), with a "Jaw width" slider and pose buttons in `HeadTest/lip_tester.py`. The CAD sweep only covers the jaw up to 35°.
- `output/plates/` now also has his `eyemech_e3.2_MG90s_B_cogley.3mf`, `eyemech_e3.2_servo_sizing_plate_cogley.3mf` and the assembly guide PDF (all public on his EyeMech_Epsilon GitHub, CC BY-NC-SA 4.0).

**Fit test (same day):** printed Cogley's servo sizing plate (`output/plates/eyemech_servo_sizing_plate.stl`). On the team's servo shaft **B (Ø4.72) grips tight**; A (Ø4.92) is the size that slipped. Size B is the team's size (MEASURED).

**Decisions:** D16 amended: keep the printed set, but reprint the 6 horn-carrying objects in size B.

**Next:** print `output/plates/eyemech_B_horn_parts_plate.stl` (4 lid sets, Y-axis set, X-axis part B; tree supports), swap them in for the A ones, calibrate at 90° (eyes forward, lids shut and meeting in the middle), press the horns on, screw, and re-run the sliders.

## 2026-10-25 — M3 — Assembly manual: EyeMech step by step; M3 inserts in the linkages

**Done (team: eye assembly instructions in the manual, and the threaded inserts in the mouth and brow linkages):**
- Stage 2 of the manual (https://claude.ai/artifact/PMPYGv9TJCFZaYW4FzNEWQ) is now 13 steps with a picture each (2.2–2.13), in the order of Cogley's ε3.2 assembly PDF: X-axis part A with the left/right servo, Y-axis part, central pivot holders, X-axis part B, onto the base, eyes, lids, outer lid pivots, the other 5 servos, retainers, horns, cable labels.
- The pictures come from his EyeMech ε3.1 model (`output/ref/eyemech`, from `modules.py`). His head export lacks the lateral frame, two eye adaptors and a pivot holder. ε3.1 lacks one central pivot holder, so it is mirrored from the other.
- Linkages: every M3 shoulder joint now threads into an M3 insert, not a nut. That is 28: lip plates 2 each, corner links 2 each, corner pieces 1 each, tongue arm 1, tongue link 1, brow arms 3 each. New manual step 1.6 shows where they go. Steps 3.5, 3.6, 3.9, 3.10, 4.3 and 4.4 were redrawn and reworded.
- Counts: 95 inserts (107 with his shell), M3 inserts 16 → 44, no nuts. The 5.5 mm nut driver is off the tools list. The old 1.6 (frame inserts for his shell) is now 1.7.
- `cad/studies/assembly_manual.py`: `inserts_link()`, `steps_link_inserts()`, `eyemech()`, `eye_steps()`. A view can now draw only some of the meshes (4th element of `v()`).

**Physical:** the team's linkage parts already have their M3 inserts set (reported 2026-10-25), so the bench result overrides the CAD.

**Problems:**
- In Cogley's geometry these are nut pockets, not insert holes. The part is 4 mm thick there (2.9 at the corner pieces): a round Ø3.4–3.6 hole only 1.0–1.4 mm deep, then a hex pocket 5.7 mm across the flats and 2.6–3.0 mm deep. His print file has the same parts (volumes match the reference within 0.2 %).
- His parts list has no nuts ("Around 25x M3 Shoulder Screws (optionally use standard M3 with lock nut)", "Various threaded inserts").
- The manual says to check each insert sits flush and square, and that an M3 nut fits the same pocket if one spins.
- His reference assembly's left brow arms (Part 12, Part 13) are an older version without the pocket. His print file's left arms are mirrors of Part 8 and Part 9, so step 1.6 draws only the head's right arms.

**Renders:** [process_images/2026-10-25_37_assembly-manual-eyes-inserts](../process_images/2026-10-25_37_assembly-manual-eyes-inserts/) (20 images; `s1_06_linkage_mouth.png`, `s1_06_linkage_brows.png`, `s2_02`–`s2_13`).

**Next:** build the EyeMech along Stage 2; note any step where the printed ε3.2 set differs from the ε3.1 pictures.

## 2026-10-24 — M2 — Cogley's TPU brow bars ready to print

**Done:**
- Took Cogley's two flexible brow bars (Part 11 = left, Part 14 = right) out of plate 5, "Brows - Flexible", of his `BambuPrintfile.3mf`. Their geometry and his print pose are unchanged. Both meshes are watertight, 66.9 × 25.1 × 18.9 mm and 1.73 cm³ each, and the top view matches his plate thumbnail.
- New files: `output/plates/cogley_brow_bar_L.stl`, `cogley_brow_bar_R.stl` and `cogley_brow_bars_tpu_plate.stl` (both bars, 171 × 26 mm). PRINT_GUIDE has his TPU settings.

**Problems:** In his pose each bar touches the bed only at its ends, so the arch needs tree supports. TPU supports stick hard and the pleats are 1.5–3.4 mm thick, so take the supports off gently.

**Next:** Print both bars in TPU 95A, then fit them on the "Brows - Main" parts with one screw at each end (manual step 4.4).

## 2026-10-24 — M4/M5/M6 — Skin silicone set to Dragon Skin FX-Pro (D21)

**Done:**
- The team confirmed the skin silicone is Smooth-On Dragon Skin FX-Pro (chosen 2026-10-15 in a claude.ai chat, in hand by 10/19, a unit on the Blick receipt 10/21). It replaces the brief's candidates, Ecoflex 00-30 and PlatSil Gel-OO30, everywhere.
- PLAN: new D21 with the TB numbers; Q15 partly answered; R4 and R11 updated; M4 pads to be cast in the same mix as the face. Last-updated line moved to 2026-10-24.
- BOM: new *Silicone skin* section (FX-Pro, Ease Release 200, Bulls Eye shellac, THI-VEX, Silc Pig, Slacker optional, Sil-Poxy).
- PLASTER_MOLD.md: new section *Getting the mold ready for the silicone*: dry checks without a scale (plastic-wrap, touch, colour), cleaning, sealing, a cure-and-release test on sealed scrap, Ease Release 200, casting at 18 °C or warmer within the 12-minute pot life.
- **Correction, same session:** the sealer was first written as Zinsser Bulls Eye shellac (bought on the advice of earlier chats). Smooth-On's sealer guide says never use shellac with silicone (its alcohol makes the rubber bond), and not to wipe the mold with alcohol. Changed everywhere to acrylic spray, thinned petroleum jelly or SuperSeal, then Ease Release 200.
- Budget workbook: the Ecoflex 00-30 row is marked not buying (status cleared, so it leaves the totals); the FX-Pro row notes it is the project's skin silicone.
- CLAUDE.md: one line naming the silicone. BRIEF.md left verbatim, as the rules require.
**Numbers:** none in params.py. `SKIN_T` 5.0 and `LIP_SKIN_T` 8.0 stay ASSUMPTIONs until FX-Pro samples are tested on the brows and lips.
**Physical:** the face was sculpted in Monster Clay on the printed mask (done 2026-10-21). The plaster mold is one piece (splash coat, then a thick plaster-bandage shell, Ease Release 200 on the clay), laid up the night of Wed 2026-10-21 to Thu 10-22. At 2026-10-24 17:30 (about 2.7 days) it is likely not fully dry; plastic-wrap test before sealing. Tiny clay specks remain in it. Whether the plaster was Ultracal 30 and whether the printed mold base (D20) was used is not recorded.
**Decisions:** D21 decided (team): Dragon Skin FX-Pro.
**Problems:** FX-Pro (Shore 2A) is firmer than a 00-30 silicone, so the servo loads are higher than first assumed (R11). Whether the one unit bought is enough for the pads and the face casts has not been checked.
**Next:** wrap-test the mold; once dry, seal it (not shellac), release it, test-cure FX-Pro on sealed scrap, then cast the M4 snap pads (snaps arrive 10/25, THI-VEX 10/26).

---

## 2026-10-22 — M3 — Step-by-step assembly manual for Cogley's head (eyes, brows, mouth)

**Done (team: a picture manual to build his Robot Head α2.0.33 one step at a time):**
- Researched what exists: no written manual for the full head. His Notion download page calls the documentation minimal and lists only supplies (2 MG996R, 19 MG90S, ~25 M3 and ~10 M4 shoulder screws, threaded inserts, 50 mm fan, 5 V 10 A). Only the EyeMech ε3.2 has an assembly PDF.
- Worked out the build from his reference assembly instead:
  - **Screws:** each screw traced to the parts it passes through.
  - **Inserts:** hole sizes measured along every screw axis. Ø3.2 holes take M2 inserts, Ø4.3 M3, Ø5.3 M4: 24 + 16 + 27 inserts.
  - **Brows and tongue (no screws in his export):** the joints were found by matching coaxial holes. Ø5.2 pivots take M4 shoulder screws; Ø4.3 pivots take M3 shoulder screws with a nut in a hex pocket.
  - **Order:** each module was slid out of the assembly along 8 directions to find the order and direction it goes in. Mouth from below, cheek bone from the front, EyeMech from above-front, brows from the front, fan bracket from the back.
  - **Sockets:** from `MouthMaster.py`: JL GP4, JR GP5, LUL GP6, LUR GP7, LLL GP8, LLR GP9, CUL GP10, CUR GP11, CLL GP12, CLR GP13, TON GP14.
- New study `cad/studies/assembly_manual.py`: one picture per step. Inserts are coloured by size, and each label is placed on a part the camera can see (depth-buffer test).
- The manual is a Claude doc (private, Cogley's Patreon CAD in its pictures): https://claude.ai/artifact/PMPYGv9TJCFZaYW4FzNEWQ

**Renders:** [process_images/2026-10-22_36_assembly-manual](../process_images/2026-10-22_36_assembly-manual/) (28 step images; `s3_12_mouth_servo_map.png` is the mouth's socket map).

**Problems:**
- Not in his model, so still open:
  - which screws hold the fan bracket
  - the M4 length for the brow body (~12 mm, from the hole depths)
  - whether his code's "left" is the head's own left (Stage 6 of the manual checks it by swapping plugs)
- By geometry, in this frame (+y front, +z up, right-handed) the character's left is −x. Cogley's `UpperLeftLip` sits at −x. PLAN §4 says +x is the character's left, so names like `brow_L` and `mold_base_chin_L` may be mirrored. To check.

**Next:** the team builds along the manual, step by step.

---

## 2026-10-20 — M5 — Mold base for the plaster mold of the clay face (D20)

**Done (team: a structurally sound base and watertight walls to cast plaster and burlap over the clay head tomorrow):**
- Researched the process (plaster and burlap shells over clay, flanges, keys, release, Ultracal 30 mix 38:100 by weight, set 25–35 min) and wrote it up for the team: [PLASTER_MOLD.md](PLASTER_MOLD.md).
- **Found:** lying face up, the mask wraps past its widest line. By the ears it is widest 14 mm above its edge and tucks back in by up to 22 mm; along the jaw, 6–9 mm. A one-piece rigid mold would lock on (96 cm² hidden from above). The rim is also a saddle: 8 mm above the plate by the ears, about 125 at the chin and 118 at the forehead end, so on a flat board the plaster would run under the edge into the mask. The team pictured a single pour; they get the choice instead: fill the tucks with clay for a one-piece shell (recommended for tomorrow), or make a three-piece mold. The base is the same for both.
- **`cad/mold_base.py`:** the mask face up in a collar swept round its rim, read back exactly from `face_mask.stl`'s own sampling grid. The collar has a ledge under the rim face, a lip 6 mm up the inside (a wedge, 5 → 2.4 mm), 0.4 clear of the STL, and a skirt flaring down at 12° to a 6 mm plate. 4 posts under the forehead and cheeks (tops 1 mm under the inside, a pea of clay on each). 4 registration cones and 4 pry blocks on the flange. Walls 45 high, 6 thick, inner face drafted 2°. Four pieces, split at X = 0 and through the ears (Y −200), with dovetails in the plate and the walls half-lapped. Mold pose = print pose.
- **`cad/mold_check.py`:** the base against the mask, hooks, overlaps, bed fit, the hidden strips, a plaster estimate (about 3 L mixed, about 4 kg Ultracal), and renders.

**Review (cad-reviewer) found two blockers, both fixed:**
- **The pieces couldn't be put together.** The wall laps only ran above the plate, so each wall tongue stood over the other piece's plate. Lifting chin_L straight off chin_R overlapped up to 305 mm³ until 60 mm up. Fix: the laps run down through the plate too. Every seam is now a vertical prism, and the tongues no longer overhang.
- **The mask couldn't be lowered in.** The 6 mm lip followed the mask's inside, which flares out going up by the ears and jaw. Lowering the mask hit the lip from 0.5–1 mm above its seat (465 mm³ at 3 mm). Fix: wherever the inside flares out, the lip stands straight up from the rim's inner edge; at the chin and forehead it still follows the inside.
- mold_check now lowers the mask, and every piece onto every other, from 0.25 to 60 mm: 0.000 mm³ worst overlap. Pushing the mask 0.5 mm into its seat overlaps 11 mm³ (the ledge carries it); it has under 0.6 mm of play in X and under 1 mm in Y.

**Numbers:** new `MOLD_*` block in params.py. The lip's root went 2.4 → 5.0 (`MOLD_LIP_ROOT`): at the forehead middle its inside leaned 49° and print_check flagged 157 mm² of overhang on each top piece; that is now 0.

**Check:** `check: PASS (0 hard failure(s), 2 warning(s), 981 s)`. The 2 warnings were that lip overhang, fixed after the run. After the lip and review fixes, on the mold pieces alone: `PRINT CHECK OK`, and `MOLD OK` (base vs mask: overlap 0.000 mm³, closest 0.23 mm; drop-in 0.000 mm³; 0.0 mm² of the base faces down on the plaster side).

**Renders:** [process_images/2026-10-20_33_mold-base](../process_images/2026-10-20_33_mold-base/) (`mold.png`, `mold_sections.png`, `mold_seat_closeups.png`, `mold_why_one_piece_locks.png`, `print_check.png`).

**Demolding (team: make it come apart easily without breaking the plaster):** the walls were part of the base pieces, with only 2° of draft. The flange would have had to be pried up out of a fixed box, and plaster expands slightly as it sets, so it grips walls like that. Mold boxes come off before the mold is lifted, so:
- The walls are now 4 separate L-shaped corners (`mold_wall_*`, 168 × 224 × 45, quick prints). They stand on the plate outside a 4 × 4 mm rib (20° draft on the plaster side) and are held together by ears at each seam (2 × Ø3.4 holes for M3 bolts or zip ties, or binder clips).
- Order: undo the clips, pull each corner straight outward, lever the flange up at 8 pry pockets (2 per side; there were 4, on the ends only), lift the shell.
- mold_check also moves each wall corner outward from 0.25 to 60 mm against every other piece: 0.000 mm³. The base pieces lost their walls and laps: 360/355/335/332 cm³ (were 434/430/407/406).
- The mask seat, the drop-in and the hooks results are unchanged.
- **Second review (cad-reviewer):** the walls come off and the shell lifts clear. It modelled the flange plaster (1260–1585 cm³) and both moves overlapped it by 0.000 mm³, and the ears' holes are coaxial. But the pry blocks were fixed to the base and filled their pockets, so the plaster sat right on them with no slot for a blade. Levering there would chip the flange. Fix: 8 loose `mold_pry_wedge` prints (18 × 14 × 7, tapered 18 → 14 wide and 7 → 5 high, with an M3 hole in the end) stand in gaps in the rib. After the walls are off, an M3 screw pulls each one out and leaves a 7 mm slot. mold_check pulls them out 0.25–60 mm: 0.000 mm³. Also: two binder clips don't fit on one 45 mm ear; the doc now says one per joint, or the bolts or zip ties.
- Renders: [process_images/2026-10-20_34_mold-base-removable-walls](../process_images/2026-10-20_34_mold-base-removable-walls/) (`mold.png`), and with the wedges [process_images/2026-10-20_35_mold-pry-wedges](../process_images/2026-10-20_35_mold-pry-wedges/) (`mold.png`, `mold_pry_wedge.png`).

**Plates (team: print on the 2 P2S overnight):** `make_plates.py` now writes 4 plates. Each is one base piece, its wall corner nested round its outer corner (4.0 mm apart) and 2 wedges: 206–218 × 217–246 mm. Two base pieces can't share a 256 bed (each is up to 164 × 220), so the set is 2 plates per printer.

**Decisions:** D20 (proposed): the printed base with a laid-up plaster and burlap shell; one piece with the tucks filled, or three pieces, is the team's call. R13 added: the mask's tucks.

**Next:** print the 4 pieces (PLA, 4 walls, no supports, about 1 kg); assemble, seal and release them; make the mold (PLASTER_MOLD.md). Keep the base: it holds the cleaned mask as the core for the silicone cast.

---

## 2026-10-17 — M5 — Printed mask (v9): the lip line is 5–7 mm low

**Found (cad-reviewer on v6, then measured on v9):** the parting line printed on the mask is at z 134–137, not on Cogley's lip plates (z 141.2).
- Cause: the push clear of his head runs along rays from c, and at the mouth those rays point 21–26° down, so the lips slid down as they moved out.
- The eyes are not affected: their centres measured (37.46, 212.42) and (−37.45, 212.42) on v6.

**Team:** keep the print, no corrected file. The marked image shows where to sculpt the lip line: 71.2 mm below the eye-centre line, 69 mm corner to corner, about 6 mm above the printed groove.
- A fix was tried and set aside: warp the lips higher until the finished line lands on the plates. It converged at z 142.5 with +2.6 mm.
- Do it if the mask is ever reprinted.

**Also from the review:**
- The tree supports touch the outside too (the backs of the ears, the rim edges), not only the inside.
- `print_check.py` takes `output/stl`, not `output/print` (it applies `print_rotate` itself).

**Renders:** process_images snapshot 31 (`sculpt_where_lips_sit.png`).

---

## 2026-10-16 — M5 — Face mask v8: thin shell, flat eyes and nose guide

**Done (team: save filament; eyes and nose only as guides):**
- **Shell:** 2 mm, was 3. The inside follows the deepest point within 2 mm, was 4. Volume 207 cm³, was 364.
- **Eyes:** flat (no eyeballs, no lids) over 21 × 13 mm each side of each eye centre. The iris ring (R 4) and pupil mark the eye axes.
- **Nose:** kept at 35 % of its height over a smooth base, as a guide for where to build it.
- **Mouth:** flat, with the parting line and a line round each lip (v7b).

**Numbers:**
- MASK_T = 2.0, was 3.0.
- MASK_EYE_FLAT = (21, 13), new.
- MASK_NOSE_KEEP = 0.35, new.

**Check:** not run (building closing). face_mask is watertight, 1 body, 206 × 250 × 157 in print pose. Before the eyes were flattened, print_check found 8 thin spots of 6.7 mm² or less at the inner eye corners; those corners are now inside the flat eye areas.

**Renders:** process_images snapshot 29 (`sculpt_mask_flat*.png`).

---

## 2026-10-16 — M5 — Face mask v7: flat lips with marks, smaller iris rings

**Done (team, building closing):**
- **Lips:** the mouth area is flat, refilled as a smooth membrane from under the nose to above the chin (MASK_LIP_FLAT = 18 mm each way), because the sculptor shapes the lips. A first, smaller patch left the upper lip's bulge as a ledge. Three lines are cut into the flat area:
  - the long parting line where the lips meet, out to the corners, 0.7 mm deep
  - a line round the upper lip (9 mm high in the middle, with a slight Cupid's bow), 0.5 mm deep
  - a line round the lower lip (11 mm), 0.5 mm deep
- **Eyes:** the iris ring ran onto the eyelids. It is now R 4.0 (was 6.5), the pupil R 1.6 (was 2.4).

**Numbers:**
- MASK_IRIS = (4.0, 1.6, 0.8), was (6.5, 2.4, 1.2).
- MASK_LIP_MARKS = (9.0, 11.0, 0.5), new.

**Check:** not run (no time); face_mask build watertight, 1 body, 206 × 250 × 169 in print pose. The surface changes only in the mouth and the eye marks.

**Renders:** process_images snapshot 27 (`sculpt_mask_flat_lips*.png`).

---

## 2026-10-16 — M5 — Face mask v6: eyes exactly on the eye axes, MakeHuman's real lips

**Done (team: "ensure the eye placement matches exactly the mechanic and show me"; the lips still didn't look like v1's real lips):**
- **Eyes:** MakeHuman's eyeballs are placed rigidly on the eye mechanism's eye centres after the warp (the warp had bent them 0.3–0.7 mm off). Measured centre: x ±37.500, z 212.400, 0.000 mm off. The iris ring and pupil marks were drawn along rays from the head's centre point, which put them about 8 mm outboard of the real axis. They are now circles round the eye axis itself: pupil measured within 0.5 mm of it.
- **Lips:**
  - The "where the lips meet" landmark had picked the crease under the lower lip, 14 mm too low. It now finds the narrow dip between the lips (31 mm below MakeHuman's nose tip), and the corners where that dip fades (±26.5 mm).
  - The lips scale ×1.11, not ×1.21, so the corners reach just past Cogley's plates.
  - The gap between them is closed (a grey closing, then a smooth fill along the gap's own curve) with a 0.7 mm line cut along it that fades at the corners. The comb of "teeth" is gone.
- **Skin:** the surface is now traced exactly from MakeHuman's mesh (triangle rasterisation, not sampling). The plain skin is smoothed; the eyes, nose and lips keep their detail.
- **Shell inside:** it was offset 3 mm along smoothed normals, and it crossed the skin in the eyelid creases (walls of 0.00 mm over 82 regions). It is now a smooth surface of its own over the same directions: under the deepest point within 4 mm, 3 mm in along the normal, and never nearer the skin than 1.5 mm along the ray.
- **print_check:** ran out of memory on the 1.04 M-face mask (a full-length ray cast tests about 59 k triangles per ray). Meshes over 200 k faces now get a short-range wall test (`local_thickness`). It agreed with the full ray cast on an eye crop.

**Numbers:** MASK_LINE = (0.9, 0.55) mm (was a width in degrees); MASK_LIP_ZONE = 8.0 (new; replaces MASK_SLIT_DIP); MASK_LIP_LINE = 0.7; MASK_GRID_DEG = 0.25; MASK_FINAL_SMOOTH = 2; MASK_HEAD_SMOOTH = 8; MASK_SKIN_SMOOTH = 0.9.

**Check:** `check: PASS (0 hard failure(s), 5 warning(s), 474 s)`. The 5 warnings were the print_check memory crash, fixed after this run. Then print_check on the mask alone: 17 thin spots of 2 mm² or less at the steep inner eye corners (was 82, down to 0.00 mm).

**Renders:** [process_images/2026-10-16_26_face-mask-v6](../process_images/2026-10-16_26_face-mask-v6/) (`sculpt_mask_eyes*.png`: the eye axes through the pupils, cuts through each eye axis and at eye height; `sculpt_mask_closeups*.png`: eyes, lips, whole mask).

**Problems:** the inside touches Cogley's eye frame (EyeCorePivotHolder, LidTR) at the inner eye corners, and brow parts at the forehead sides. The mask is a standalone sculpting piece, so it doesn't matter for the sculpt; it won't sit over the assembled mechanism. Print size 206 × 250 × 169, 364 cm³ solid.

**Next:** print it (face up, tree supports inside); the team sculpts on it.

---

## 2026-10-16 — M5 — Face mask v5: MakeHuman's own eyes and lips

**Done (team feedback on v4):** the designed eyes and lips looked inhuman; use the reference mesh's own.
- **Eyes:** MakeHuman's eyelids, with its eyeball helpers (`helper-l-eye`, `helper-r-eye`) added to the head before the warp, so they fill the openings: open eyes, no holes. The eye centres are pinned onto the EyeMech's. The designed almond, eyeball and eye-region fill are gone. An iris ring and a pupil still mark the axis.
- **Lips:** MakeHuman's own, scaled evenly across and up (×1.21, not deeper) about where they meet. The corners land 1 mm past the ends of Cogley's lip plates (team's choice over natural size, 2026-10-16). Pinned on a 5 × 5 grid round the mouth, so the shape is kept.
- **Print pose:** 206 × 239 × 169, about 270 g, watertight.

**Decisions:** the lips scaled to span the plates (asked, answered "scaled to the plates").

**Renders:** process_images snapshot 25 (`sculpt_face_mask.png`).

---

## 2026-10-16 — M5 — Face mask v4: open eyes, real lips

**Done (team feedback on v3):** the lips didn't look human or made for the mechanism; the eyes had to be clearly marked, and open with no holes.
- **Lips:** MakeHuman's own lips are kept. The eye openings are filled; the line between the lips is no longer filled or grooved, and its fronts are no longer pulled back.
  - Pinned: where the lips meet (onto the gap between Cogley's lip plates, z 141.2), the corners (1 mm past the plates' ends, ±34.3), and the lips' fronts 1.35× further above and below the lip line (fuller).
  - A half cut-away render shows his upper plates behind the upper lip and his lower plates behind the lower lip.
- **Eyes:** each eye region is replaced by a designed open eye:
  - an almond opening 32 × 11 mm, the outer corner 1.5 up, on the eye mechanism's axis
  - an eyeball (R 17) 2 mm behind the lids, never more than 3 mm behind them
  - an iris ring (R 6.5) and a pupil (R 2.4, 1.2 deep)
  - a 2 mm soft lid margin
  The finishing smooth spares the eyes (60 %) and the lips (60 %).
- **Print pose:** 206 × 240 × 169, about 270 g, watertight.

**Open:** small ridges at the inner eye corners; a faint crease across one cheek where the clearance push fades out.

**Renders:** process_images snapshot 24 (`sculpt_face_mask.png`).

---

## 2026-10-16 — M5 — Face mask v3

**Done (team feedback on v2):**
- **Asked for:** a smooth, printable surface; extended to the ears, with ears; natural eye slits; lips that make sense on Cogley's mechanism; MakeHuman's proportions kept.
- **Changes:**
  - The head is smoothed before it is read (subdivided twice, Taubin), and read 40 points per mm². Openings are filled before the grain is filtered out (median 5). The finished skin gets 20 Taubin passes. The pushes clear of his head spread wider (14°, smoothed 4°), and the eye band is smoothed into calm closed lids (2.5°).
  - **Mouth:** its corners sit 1 mm past the ends of Cogley's lip plates (±34.3). The lips' fronts are pinned `LIP_SKIN_T` (8 mm) in front of the plates and 1.25× fuller. The lash lines are 31.5 mm long, with a 1 mm lid dome.
  - **Outline:** ±112° in azimuth, taking in MakeHuman's ears. The scale is 1.15.
- **Print pose:** 202 × 240 × 168, about 260 g, watertight; it fits the bed face up.

**Open:**
- A small pinch remains at the top of the nose bridge, and a sharp notch in the upper lip's middle.
- The first idea of pinning the eye-slit corners at the eye centres folded the skin round the eyes. Those pins are gone.

**Renders:** process_images snapshot 23 (`sculpt_face_mask.png`).

---

## 2026-10-16 — M5 — Face mask v2

**Done (team feedback on v1):**
- **Asked for:** the edges smoothed, no holes, the lips and nose narrower, closed eyes instead of eye holes, and the mask reaching up toward the skull.
- **`cad/face_mask.py` v2:**
  - It reads the warped MakeHuman head as a radius over a grid of directions from a point 75 mm behind the eyes: the outermost skin, from surface samples binned by direction.
  - Openings (radius dips) are filled smoothly. Closed lids get a 2 mm dome and a lash line, and the lips get a lip line.
  - The whole face moves 5.5 mm forward; the outside is then pushed out smoothly where it would come within 3 mm of Cogley's parts (the sculpt base's new tight wrap, `output/ref/sculpt/tight.stl`).
  - The forehead and skull are smoothed hard, so the helmet's facets don't show.
  - Trimmed to an egg outline (±72° wide, from −55° to +55° in elevation) and thickened 3 mm.
- **Landmarks** now come from a dense front height map. The point-by-point read had taken the back of the head for the lips.
- **Widths:** the nose and mouth are pinned to MakeHuman's width × 1.05 (nose wings ±16.8, mouth ±25.9). The scale is a fixed 1.2.
- **Print pose:** 170 × 243 × 108, about 190 g; it fits the 256 bed lengthwise. An outline topping out at 70° was 268 long.

**Numbers:**
- New: `MASK_SCALE` 1.2 (was `MASK_SCALE_TRIM`), `MASK_FEATURE_SCALE` 1.05, `MASK_CENTRE_BACK` 75, `MASK_GRID_DEG` 0.5, `MASK_DIP` 2, `MASK_LID_DOME` 2, `MASK_SMOOTH` 0.7, `MASK_PUSH_SMOOTH` 2.5, `MASK_TOP_SMOOTH` 4, `MASK_CORE_OK` 0.05, `MASK_BULGE` 10, `MASK_LINE` (0.6, 0.35), `MASK_OUTLINE` (72, 55, −55, 0.12).
- Gone: `MASK_INSIDE_OK`, `MASK_SUBDIVIDE`.

**Problems along the way:**
- Rays through the 500k-triangle wrap took over 10 minutes. Binning surface samples by direction takes seconds.
- Checking against the sculpt base's surface (inflated up to 11 mm at the face) pushed the face 50 mm forward. The tight wrap fixed it.
- The face is a reference to sculpt on, so its outside (not its inside) keeps 3 mm from his parts.

**Renders:** process_images snapshot 22 (`sculpt_face_mask.png`).

---

## 2026-10-16 — M5 — Face mask (D19)

**Done:**
- The team turned down the sculpt base v2 (a wrap of Cogley's head) and asked for a face mask instead: a thin shell of a man's face, like a theatrical mask, with its features where the mechanism puts them.
- **`cad/face_mask.py`** builds it from the MakeHuman base mesh (CC0, `inputs/reference/makehuman/`):
  - Scaled 1.208: the geometric mean of what fits the eye spacing and what fits eyes-to-lips.
  - Warped with a thin-plate spline: the eye centres onto the EyeMech's, the lips onto where Cogley's lip plates meet (z 141.2), the nose at the same share of eyes-to-lips, and the chin following the lips.
  - A man's proportions: the jaw angles 10 mm wider each side, the chin corners wider, the brow ridge 4 mm forward.
  - Moved forward 16 mm to clear his head, with smooth local bulges where needed.
  - Trimmed to an oval from forehead to chin, keeping only the face's outer skin, and thickened 3 mm inward. The eye holes are the face's own.
- **Clearance:** the closest of Cogley's parts is 6.9 mm from the mask (the left brow bar).

**Numbers:** `MASK_SCALE_TRIM` 1, `MASK_MALE` (10, 4), `MASK_OUTLINE` (78, 106, −24), `MASK_T` 3, `MASK_INSIDE_OK` 0.01, `MASK_BULGE` 12, `MASK_SUBDIVIDE` 1.

**Renders:** process_images snapshot 21 (`sculpt_face_mask.png`).

**Problems:**
- trimesh's Loop subdivision threw the trimmed edge's points 60 mm out (spikes). It is now midpoint subdivision plus a gentle smooth.
- Points at the edge and the nostrils with poor normals kept being pushed out. The push is now a smooth bulge along smoothed normals.
- Open: the shell folds over itself slightly at the eyelid rims and the lip line (`print_check` reports 0 mm walls there). The slicer repairs it on import. A cleaner rebuild (a voxel slab) is the next step if it matters.

**Decisions:** D19 (the face mask is what the sculptor works on).

---

## 2026-10-16 — M5 — Sculpt base v2 on Cogley's head; eye mount; firmware

**Done:**
- **Sculpt base v2** (`cad/sculpt_base.py`, with the new `cad/wrap.py`). Our proxy face is gone (D17). The base is a wrap of Cogley's complete head at rest: shell, frame, cheek bone, eyes, brows, mouth and screws.
  - **How the wrap is made:** voxels at 1 mm. A tight wrap (closed by 7 mm) hugs every part. A smooth wrap (closed by 32 mm, blurred by 10) gives a head-like form, inflated by up to 11 mm at the face so it swallows the mechanism's lumps. The inflation is held off near the lips, brows and lids (8 mm, full at 23), where the skin must stay thin. The two are soft-unioned, with the surface 3 mm out.
  - **Features:** eye sockets show the real eyes (the lids' sphere), with ceilings at 55° and stopping at his other parts. Sculpting guides as grooves: midline, eye line, brow lines along his bars, nose bottom (0.7 of eyes-to-lips) and width, lip line and mouth corners (his lip plates), chin, hairline, ears. A neck stub, the base plate, a split at z 186, and dowels.
  - **Guide heights (z):** eyes 212.4, lips 141.2, nose bottom 162.6, chin 98.5, brow 244.8, hairline 308.9. The mouth is ±33.3 wide and the nose ±21.2.
- **Surface extractor** `cad/wrap.py`: written here, because there is no marching-cubes package.
- **`sculpt_check`** now checks his head against the base's outer surface:
  - none of his parts come through
  - the thinnest skin is 2.58 mm, over a frame screw head (the target is 3 less the grooves)
  - both eye spheres sit 0.00 off his eyeballs
- **Eye mount** (ASSEMBLY.md): the printed eye mechanism sits on the mouth's top plate between the frame's walls. Two M3 screws per side go through the frame into inserts in the base plate's end holes, which the printed plate already has. The cheek bone sits under it. MG90S servos clear the top plate by 2.7 mm.
- **Firmware (D18):** 3 mouth boards stand in for Cogley's 1 mouth board + 2 Eyes/Brow/Neck boards. His eye and brow programs run on them with the mode switch moved to GP28 (`firmware/`).

**Numbers:**
- New: `SCULPT_GRID` 1, `SCULPT_TIGHT` (7, 2), `SCULPT_SMOOTH` (32, 10), `SCULPT_FACE_INFLATE` 11, `SCULPT_FACE_FADE_Y` (−50, 0), `SCULPT_MOVING_CLEAR` (8, 15), `SCULPT_BLEND` 10, `SCULPT_NECK` (50, 54, −70, 40), `SCULPT_SPLIT_Z` 186, `SCULPT_EYE_CAP` 4.
- Gone: `SCULPT_EYE_SOCKET`.

**Problems and fixes along the way:**
- The first wraps followed every mechanism lump. Smoothing alone shrank the bumps until the tight wrap showed through again. Inflating everywhere thickened the skin over the lips and brows. The fix was face-only inflation, held off near the moving parts.
- The surface pinched where a crevice was narrower than a voxel (the midline between the lips and between the brow bars). A light last blur fixed it, and the pieces now reload watertight.
- The brow guide wiggled along the TPU bar's pleats. It is now a smooth fitted curve.

**Next:** print the sculpt base; then the mold core, the neck (Q17) and the skin attachment points.

---

## 2026-10-16 — Re-base — Cogley's whole head as designed (D17)

**Done:**
- The team found our placeholder face (the proxy head in the fit study) nothing like a human. The face is now based on Cogley's own head (D17).
- Rendered his complete head with his outer shell ([process_images](../process_images/README.md) snapshot 18, `studies_cogley_complete.png`). His shell is a helmet over the top and back of the head. The face below it is open mechanics, with the cheek-bone band under the eyes.
- **Q16 answered: keep his mouth where it is.** It only looked 13.4 mm too high against our placeholder face.
- The `CheekBone` conflict is gone with it: it only poked 0.8 mm through the placeholder face.
- Printed so far: the eyes (ε3.2 MG90s-A), the mouth, the teeth and tongue, and his "Brows - Main" plate. **Cleared to print, as he designed them:** "Frame - Main", "Frame - Extras" and "Outer Shell". The brow bars wait for TPU.
- Retired: our skull pieces, shelf, EyeMech cradle and strap, and the sculpt base v1. The methods (service check, sculpt check, the importer) carry over.

**Decisions:** D17 (Cogley's head is the face's base), Q16 (keep his mouth).

**Next:** sculpt base v2, a smooth wrap of his complete head raised by the thinnest skin; then the neck mount (Q17) and skin attachment points.

---

## 2026-10-16 — Re-base — Cogley's Robot Head α2.0.33 as the base (D14); SG90 vs MG90S

**Done:**
- **His head's files** (the team's Patreon download) moved to `inputs/reference/head_a2.0.33/` with ASCII names. Contents: his reference assembly (Onshape OBJ, 191 parts), every printed part (Bambu 3MF, 8 plates), his code and both PCBs. No STEP.
- **`cad/cogley_head.py`** (in the pipeline) imports the assembly into our frame, his eye centres on ours, in 7 groups: frame, extras, robot shell, eyes, mouth, brows, hardware.
- **`cad/read3mf.py`** reads Bambu 3MFs without lxml. networkx 3.7 is now in the venv, after a uv dry run: trimesh needs it for sections, hole filling and 3MF loading.
- **Fit study** `cad/studies/cogley_fit.py`:
  - His EyeMech lands within 1.7 mm of ours. His mouth sits 13.4 mm higher.
  - His mouth's top plate is the eye shelf (Q14 answered).
  - 26 parts poke past our skull's inside: the brow bars, the lips, the `CheekBone`, the frame's side screws and the frame at the temples.
- **Eyes (D16):** the printed ε3.2 MG90s-A set's structural parts are identical to his head's eye parts. With our EyeMech on his base plate, the lids clear his other parts by ≥ 5.7 mm swept, and the eyes by ≥ 8.2. No reprint.
- **Brows (D15):** his brows: 4 servos, an inner and outer per brow, and flexible TPU bars. Ours stay as the bench backup.
- **Proportions (Q16, open):** his lips are 71 mm below the eyes, with the eyes 75 mm apart; a normal face would be about 85 mm.
  - Lowering his mouth 13.4 mm pushes it into his frame (580 sample points inside), so it would mean redrawing his mouth mounts.
  - The sculpt base v1 is on hold until this is decided.
- **SG90 vs MG90S:** datasheets and 3D models compared (BOM, *SG90 or MG90S*).
  - Same footprint and spline size. The MG90S has metal gears, a ball bearing and a tapped metal shaft; it sits about 1.5 mm deeper below its tabs and weighs 13.4 g against 9 g.
  - The head needs 19 × MG90S. The team's 3 plastic-gear SG90s are for bench tests.
- Plan v2: D14–D16, Q16–Q18, R12, and the re-base work list (§6).

**Numbers:** his head in our frame: R = diag(−1, −1, 1), t = (0, −67.04, 212.4).

**Check:** `check: PASS (0 hard failure(s), 0 warning(s), 226 s)`.

**Renders:** [process_images](../process_images/README.md) snapshot 16 (`studies_cogley_fit.png`).

**Decisions:** D14 (his head is the base), D15 (his brows), D16 (keep the printed eye set).

**Sources for the servo comparison:**
- TowerPro: https://www.towerpro.com.tw/product/sg90-7/ and https://www.towerpro.com.tw/product/mg90s-3/
- Aus Electronics' measured SG90 drawing: https://www.auselectronicsdirect.com.au/assets/brochures/TA0132.pdf
- servodatabase.com: https://servodatabase.com/servo/towerpro/sg90 and https://servodatabase.com/servo/towerpro/mg90s
- Electronicos Caldas MG90S sheet: https://www.electronicoscaldas.com/datasheet/MG90S_Tower-Pro.pdf
- ProtoSupplies (measured currents): https://protosupplies.com/product/servo-motor-micro-sg90/ and https://protosupplies.com/product/servo-motor-micro-mg90s/
- Horn fit: https://newscrewdriver.com/2020/12/27/notes-on-micro-servo-output-shaft/
- Spotting clones: https://vorpalrobotics.com/wiki/index.php/Tower_Pro_MG90S_Vs._Clones

**Models checked:**
- SG90: FreeCAD library (Gafeju, CC-BY-3.0) and Printables 1404346 (CC0)
- MG90S: Printables 569094 (GPL-3.0) and Printables 1836987 (CC0)
- MG90D: Adafruit 1143 (MIT)
- Cogley's own SG90 and MG90S meshes

Their overall heights including the spline: SG90 29.9–30.0, MG90S 31.1–32.4.

**Problems:** the OBJ is missing 2 of his 4 brow servos (R12).

**Next:**
- The team answers Q16 (proportions), Q17 (neck) and Q18 (TPU), and buys the MG90S servos.
- Then: move the module placements onto his head, add his brows with their motion, and re-fit the face and the shell.

## 2026-10-16 — M3 / M5 — Sculpt base; service paths for the back, the EyeMech and the brows

**Done:**
- **Sculpt base v1** (`cad/sculpt_base.py`, `cad/sculpt_check.py`), started early so the sculptor can begin (D13: normal proportions, whole head):
  - Its surface is the skull's outside raised by 3 mm (`SCULPT_MIN_SKIN`, ASSUMPTION). The clay can't make the skin thinner than that.
  - Eye sockets sit inside the skull's own eye openings, with the lids' sphere (R 18.1) and a pupil dimple at the true eye positions. The socket ceilings slope at 55° so the upper piece prints without supports.
  - Grooves mark the midline, the brow windows, the mouth opening and the lip line.
  - Three prints: `sculpt_upper` (upright), `sculpt_lower` (upside down) and `sculpt_plate`. They join with 4 Ø6 dowels. The plate has 4 conical mold keys, 4 board screw holes, and 4 × M4 into inserts in the neck.
- **EyeMech supports:** Cogley's own 3MF has tree (auto) supports on at 30°. His original file is now in `output/plates/` (commit `9433581`).
- **Service paths**, from a direction search:
  - **Back upper piece:** lifts off at about 50° up and back.
  - **EyeMech and both brows:** they come out together (brows unbolted). Slide back 50, lift 4, then out the back.
  - **Shelf:** up and back.
  - **Neck plate:** down.
  - **Mouth:** no path yet (Q14).
- **`cad/service_check.py`** (new, in the pipeline): runs the teardown in order and checks tool access with an L hex key on the brow flange and shelf screws. The two front brow flange screws have only 16.3 mm of headroom under the crown, so they need a stubby 2.5 mm key (short arm cut to 12 mm, 125° of swing).
- **To make those paths clear:**
  - The tabs on the back upper piece's two seams are placed per tab, on whichever piece they can't hook as it leaves (`BACK_UPPER_OUT_DEG` 52).
  - The EyeMech's rear stop moved from the shelf to a fin on the strap, behind the base plate's rear lip, so it leaves with the back piece.

**Numbers:**
- New: `BACK_UPPER_OUT_DEG` 52, `CRADLE_STOP` (2.4, 60) (thickness, width; was (2.4, 4.0): thickness, height).
- New: `SCULPT_MIN_SKIN` 3, `SCULPT_GROOVE` 1.2, `SCULPT_GROOVE_GAP` 2, `SCULPT_EYE_SOCKET` 10, `SCULPT_PUPIL` 3, `SCULPT_SOCKET_CEILING_DEG` 55.
- New: `SCULPT_PLATE` (8, 25), `SCULPT_PLATE_CBORE` (8.5, 4.5), `SCULPT_KEY` (12, 6), `SCULPT_BOARD_SCREW` 5, `SCULPT_DOWEL` (6.3, 13), `M4_INSERT_HOLE` 5.6 (ASSUMPTION), `M4_INSERT_DEPTH` 10.
- New: `EYEMECH_EYE_R` (16.5, 18.1) (MEASURED).
- New: `SERVICE_EYE_OUT`, `SERVICE_SHELF_OUT`, `SERVICE_TOL` 0.3, `SERVICE_KEY` (20, 65, 2), `SERVICE_STUBBY_KEY` (12, 65, 2), `SERVICE_KEY_SWING` 60, `SERVICE_HEAD_H` 3.
- Sculpt base estimate (not sliced yet): upper ~8 h, lower ~6 h, plate ~2 h; about 0.8 kg of PLA.

**Check:** `check: PASS (0 hard failure(s), 0 warning(s), 268 s)`.

**Renders:** [process_images](../process_images/README.md) snapshot 15 (`sculpt.png`, `skull.png`).

**Decisions:** D13 (art style: normally proportioned, not campy; sculpt base covers the whole head).

**Problems and fixes along the way:**
- With every tab of the back upper's vertical seam on the front piece, its side tabs locked the back piece in every direction. With them all on the back piece, the crown tabs locked it going up. The fix was the per-tab rule.
- A first try hung the stop from the strap behind the rear foot, but that foot sits under the base plate. The stop now bears on the base plate's rear lip instead.
- The eyes sit 3.4 mm under the skull's outside, so nothing of them showed on the base; it needed sockets.
- The socket ceilings were overhangs (7.4 mm along the normal; the 45° corners still too). A hull of the rims flattened them to 11° until each rim line was tilted.
- One socket reached 0.7 mm into the skull's wall under the eye. Sockets are now clipped to the skull's own opening.
- The plate's round offset left near-duplicate points that opened the mesh on reload (and crashed `check.py`'s measure step). It is simplified before extruding.
- The reviewer found the plate screws too long: an M4 × 16 would bottom out in the insert holes before clamping. Now M4 × 12. The dowel holes were exactly the dowel's length (12 + 12 for a 24 mm dowel); they are now 13 deep a side.
- `print_check` ran out of memory on the solid head pieces: every inward ray crosses the whole part. It now casts its rays in batches of 2000 faces (the skill's toolkit has the same code).

**Next:**
- Print the sculpt base once the printers are free.
- Mouth mount (Q14).

## 2026-10-16 — M3 — Neck base plate and rear access panel

**Done:**
- **Neck base:** `skull_neck_plate`, 128.4 × 112.8 × 18.
  - A 6 mm plate closes the bottom of the neck, 0.4 inside the wall, with an 18 mm collar up the wall's inside.
  - Six countersunk M3 screws go through the wall at z 10 into inserts in the collar, so the plate also ties both lower pieces together at the bottom.
  - 4 × M4 clearance holes on a 50 mm square for the stand (ASSUMPTION), and an exit for the cable channel (its Ø25 plus 1.5 all round).
- **Rear access panel:** `skull_access_panel`, a 96 × 74 opening (corner radius 12) centred at z 268 on the back of the head.
  - It is cut from the back upper piece with a 0.3 gap all round.
  - It rests on a 4 mm lip inside the opening. A 13 mm pad behind each side's midpoint holds an M3 insert.
  - 4 countersunk M3 × 6 screws from outside, heads flush under the skin.
  - With it off, the brows and the back of the EyeMech are in view.
- **Screw lengths:** the neck and panel screws are M3 × 6. An M3 × 8 would bottom out in the neck's insert holes and poke through the back of the panel's lip.
- **Renders:** `skull_check` now adds a 3/4 view from the back and a back view with the panel off (4 columns).

**Numbers (all new):**
- `NECK_PLATE_T` 6, `NECK_COLLAR` (6, 18), `NECK_SCREW_Z` 10, `NECK_SCREWS` 6.
- `NECK_BOLT_SQUARE` 50, `M4_CLEAR` 4.5, `CABLE_EXIT_CLEAR` 1.5.
- `PANEL_CENTRE_Z` 268, `PANEL_SIZE` (96, 74, 12), `PANEL_GAP` 0.3.
- `PANEL_LIP` (4, 5.5), `PANEL_SCREW_IN` 5.5, `PANEL_PAD` 13.

**Check:** `check: PASS (0 hard failure(s), 0 warning(s), 158 s)`.

**Renders:** [process_images](../process_images/README.md) snapshot 14 (`skull.png`).

**Problems and fixes along the way:**
- The first lip was built in two halves, one behind the wall and one behind the panel, that only met along a face. The back upper piece came out as 4 bodies and not watertight, and the overlap check's boolean failed. The panel half now reaches 1 mm under the wall half.
- The first lip was 7 mm wide with the screws midway across it. Each insert was left with 0.67 mm of wall, and each countersink broke through the panel's edge. Now there is a narrow lip plus a pad at each screw, with the screw 5.5 in from the edge: the countersink stays 2 inside the panel, and 4.5 of wall stands beside each insert.

**Next:**
- Fan room and vent (R6), probably in the access panel.
- Fixed skin attachments (with M4).
- `service_check`.
- The mouth mount waits on Q14.

## 2026-10-16 — M3 — EyeMech cradle and strap; print plates; first commit

**Done:**
- **Print plates for the team** (`output/plates/`, preview `plates_preview.png`):
  - `eyebrows_plate.stl`: both carriers and both brackets in their print poses, laid out by the new tool `cad/make_plates.py`.
  - `eyemech_e3.2_MG90s_A_plate.stl`: Cogley's public ε3.2 MG90s size-A file. All 34 parts are kept exactly in his Bambu layout (some print in place and interlock), centred on the bed: 244 × 247.
- **First commit** `ed2d371` on branch `dev`. Git LFS tracks *.step, *.stl, *.3mf and the process images. The team's own `Halloween_Animatronic_Budget.xlsx` is left out.
- **EyeMech cradle:** pads under its four feet, a rear stop, the shelf extended to y +8 under its side plates, and four shelf ledges on the side walls.
- **Retaining strap:** `skull_eye_strap`, 161.6 × 9 × 4, 0.4 over the back of the base plate, bolted to two ledges on the back upper piece.
- `skull_check` treats the feet on the pads as a designed contact. The front horizontal seam may have 2 tabs (it's crowded; that piece is held mainly by its 9-tab back seam).

**Numbers:**
- `SHELF_Y` (−118, 8).
- `CRADLE_PAD_MARGIN` 1, `CRADLE_STOP` (2.4, 4), `CRADLE_CLEAR` 0.4.
- `STRAP_Y` (−113, −104), `STRAP_GAP` 0.4, `STRAP_T` 4.
- `SHELF_LEDGES_Y` (−40, −95), `SHELF_LEDGE` (12, 24, 6).
- Joints: 23 screws (2 / 4 / 9 / 8).

**Check:** `check: PASS (0 hard failure(s), 0 warning(s), 172 s)`.

**Renders:** [process_images](../process_images/README.md) snapshot 13.

**Problems and fixes along the way:**
- The first cradle had rails beside the side plates and zip-tie slots. The inner rails hit the bottom-lid levers, and the outer plates are only ~1 mm from the temple walls. Replaced by the stop, the wall location and the strap.
- Pads reaching the shelf's curved front edge left slivers. They now stop 2 short of it.
- The designed 0.4 strap gap measured 0.399. The check now allows 0.02 for rounding.

**Next:** Neck base and the rear access panel. The mouth mount waits on Q14.

## 2026-10-15 — M3 — Skull joints

**Done:**
- 24 screwed seam tabs in `skull.py`. Each seam is sliced from the wall's mid-surface, a candidate is tested every 2 mm, and a tab is kept where:
  - there is wall on both sides of the seam
  - its countersink keeps 2 mm of wall to any opening
  - it is ≥ 1.5 from everything (the modules sampled about 1 per mm², the brows, the motion sweeps, the shelf, the brow plates)
  - it is 40 from the last tab on its seam and 20 from tabs on other seams
  - the wall doesn't lie nearly in the seam plane
- Per seam: front 3, back 4, upper front|back 9, lower front|back 8. On the front horizontal seam the tabs are on the upper piece and the screws go into the lower one, which has room between the mouth opening and the seam.
- `skull_check.motion_clouds()` is factored out for the builder to reuse. A small segment chainer in `skull.py` replaces trimesh's path code, which needs networkx (not installed).

**Numbers:** `SEAM_TAB_T` 5.5, `SEAM_TAB_W` 12, `SEAM_TAB_OVER` (6, 10), `SEAM_TAB_SPACING` 40, `SEAM_TAB_CLEAR` 1.5, `M3_CSK` (6.3, 1.75).

**Check:** `check: PASS (0 hard failure(s), 0 warning(s), 196 s)`. `NO OVERLAPS` (the tabs sit 0.1 behind the neighbouring wall), `SKULL OK`, `PRINT CHECK OK`.

**Renders:** [process_images](../process_images/README.md) snapshot 12.

**Problems and fixes along the way:**
- Test points on the steep occiput fell off the 2.4 wall. They are now snapped back onto the mid-surface.
- Axis-aligned tab boxes cut leaning walls obliquely and left slivers. Tab boxes are now built in the wall's frame, with the far edges square to the wall.
- Sparse keep-out samples (2.4 spacing) let a tab clip the EyeMech's base. Keep-out is now dense, with a 1.5 margin.
- Tabs clashed with the shelf and the brow plates. Both are now in the keep-out.
- A countersink at an eye opening's edge left a thin web. Screw spots now need 2 mm of wall all round.

**Next:** EyeMech cradle on the shelf, the shelf's own mounting, the neck base, the rear access panel. The mouth mount waits on Q14.

## 2026-10-15 — M3 — True-offset envelopes; skull v0

**Done:**
- **Envelopes are now true offsets** (`head.py`): every vertex of the outer skin moves inward along its normal. The outer surface is first extended 30 mm below the neck base, then cut flat at z = 0.
  - `geom.envelope_margin` is now "margin to the outer skin minus the inset". `geom.front_y` finds the outer point whose inward normal lands on (x, z).
  - `geom.row_fit` is cached. Without the cache the brow study went from 54 s to more than 10 min.
  - The analytic surface and the mesh agree within ±0.2 mm.
  - The brow study re-run gives the same pick, with 5 passing pivots instead of 3; the pivot moved about 1 mm. Every check still passes.
- **Skull v0** (`skull.py`, mesh booleans):
  - the wall
  - eye-and-brow openings (the hull of the eye circle and the brow window) and a mouth opening (rounded rectangle)
  - 4 pieces split at z 186 / y −60: front upper 175 × 87 × 166, front lower 160 × 84 × 186, back upper 177 × 155 × 166, back lower 162 × 122 × 186
  - a shelf (154 × 106 × 2.4) 1.0 above the mouth's top plate and 2.0 under the EyeMech
  - brow mount plates
- **`skull_check.py`**: static parts and sweeps against the skull, plus renders. In the pipeline.
- `snapshot.py` now also saves the skull and study images; `export_print.py` writes 11 print-ready files.

**Numbers:**
- `SKULL_SPLIT_Z` 186, `SKULL_SPLIT_Y` −60, `EYE_OPEN_R` 20.
- `MOUTH_OPEN_X` 46, `MOUTH_OPEN_Z` (88, 168).
- `SHELF_*`, `BROW_MOUNT_T` 4.
- `MOUTH_TOP_SRC_Z` −19.25 (MEASURED).
- `BROW_RIG_Z` (0, 82), lowered so the clamp bosses clear the base.

**Check:** `check: PASS (0 hard failure(s), 0 warning(s), 147 s)`. `LAYOUT OK`, `SWEEP OK`, `BROW OK`, `SKULL OK`, `PRINT CHECK OK`, `NO OVERLAPS`.
- Skull to the parts at rest: ≥ 1.0. Sweeps: jaw 3.3, lids 2.5, eyes 5.7, brow carriers 1.4.

**Renders:** [process_images](../process_images/README.md) snapshots 10 (true offsets) and 11 (skull v0).

**Problems and fixes along the way:**
- Box and cylinder openings crossed the curved wall obliquely and left slivers. The openings now come from outlines on the surface extruded along the normal.
- A fan-capped cutter left the lip patch behind as a loose body, and a self-crossing fan left 0.02 mm flaps. Cutters are now convex hulls of two rims.
- The eye circle and the brow window cut separately left sharp points; they are merged into one hull.
- The mouth opening's edge on the chin's curve, and an outer rim following the chin's downward normals, both grazed the chin. The opening bottom moved to z 88, and the outer rim never points down.
- Clamp bosses on the rig touched its base, leaving zero-thickness walls. The base is lowered.

**Decisions:** none new. Q14 added (Cogley's mouth mounting).

**Next:** Joints between the skull pieces, the EyeMech cradle, the neck base and the rear access panel. The mouth mount waits on Q14.

## 2026-10-15 — M2 — v1.1: review fixes, hard stops, bench rig, print documents

**Done:**
- **Second fresh-eyes review** (the first attempt stalled after 10 min; the retry with a tighter brief finished).
  - It confirmed: the pads track the skin, the bias works, everything clears at every pose, and the servo sits in its cutout with 0.4 all round.
  - It found:
    1. The ball links had 2.5 mm of stand-off, not the 3.5 a stud needs.
    2. The shoulder screw needed a non-stock 8.6 mm shoulder.
    3. The outer flange hole had no room for a screw head.
    4. The carrier floated 0.1 mm off the bed.
    5. The horn reference was turned 90°, so the check measured the wrong outline.
    6. Low strength margin on the lever and arm, but OK in this print pose.
    7. A straight hex key to the pivot screw is blocked by the EyeMech's centre post, so the brows go in first.
  - All fixed or written into the assembly order.
- **Hard stops** on the double-arm horn (see the design note). `brow_check` now confirms no contact inside the travel and engagement just past each end.
- **Bench rig** `cad/brow_rig.py` added to the pipeline (assembly: false; prints on its side with supports).
- **New documents:** [PRINT_GUIDE.md](PRINT_GUIDE.md), [BOM.md](BOM.md) and [ASSEMBLY.md](ASSEMBLY.md). `cad/export_print.py` writes slicer-ready files to `output/print/`.

**Numbers:**
- `SHOULDER_L` 10, `INSERT_RECESS` 0.3, `PIVOT_PLAY` 0.4 → `BROW_HUB_L` 9.3.
- `BALL_STUD_H` 3.5 → `LINK_X` 3.5, `LEVER_X` (−4, 0).
- `BROW_FLANGE_T` 7, `BROW_MOUNTS` (15, 3.5) and (15, −15.5).
- `BROW_STOPS_Y` (−2.5, −24), `BROW_STOP_MARGIN` 0.5, `HORN_FRONT_R` 9.5 (cut), `HORN_BACK_R` 17.5.
- `BROW_RIG_*`.

**Check:** `check: PASS (0 hard failure(s), 0 warning(s), 136 s)`. `LAYOUT OK`, `SWEEP OK`, `BROW OK`, `PRINT CHECK OK`, `NO OVERLAPS`, `COMPONENTS MATCH PARAMS`.
- The horn stays ≥ 0.31 from the stops inside the travel.
- The drive is ≥ 1.5 clear of parts it must not touch.
- The rig is ≥ 1.1 clear of every moving part.
- The carrier's bed contact is now 64 mm², on the hub's end face.

**Renders:** [process_images](../process_images/README.md) snapshot 09 (`brow.png` now includes the rig).

**Problems and fixes along the way:**
- The horn's full-length front arm ran into the bracket upright. It is cut to 9.5, and the raise stop moved to y′ −2.5 so the cut arm still reaches it at full raise.
- The free-hanging stop ledge would need support when printed upside down. It is now filled up to the flange.
- The rig's flat side cuts left slivers on the curved shell; it now uses square cuts. A first try with a thickened strip made new slivers and was reverted.
- The clamp-strip insert holes were 5 deep in a 2.4 mm shell. They now have bosses.
- At −10° (beyond the stop) the lower pad met the window edge. The window has 3 mm extra at each end.
- The reviewer's check run spent 50 min in the coupon build. That didn't repeat here (3.7 s); watch for it.

**Next:** The team prints the coupon, then the brows and the rig, and bench tests (see [ASSEMBLY.md](ASSEMBLY.md)). On the CAD side: snap adapters for the pads (M4), then the integrated skull (M3).

## 2026-10-15 — M2 — Eyebrow concept chosen; mechanism v1 modelled and checked

**Done:**
- **Concept study** (`cad/studies/brow_concepts.py`).
  - The first version measured a whole-brow rigid plate. It drifts 2–7 mm from the skin, and point-by-point it took 6.7 min.
  - Reworked: two snap pads per brow on a recessed bar, push and pull limits judged separately, the full pivot space searched (distance, height, skew), and vectorised to run in under a minute.
  - 3 of 2,431 pivots pass. Pick: r 45, offset +4, skew +12°. [Design note D3/D5](DESIGN_NOTES.md#d3-and-d5-eyebrow-mechanism-concept-and-motion).
- **Mechanism v1:**
  - `browgeom.py`: shared pivot, frame and four-bar maths.
  - `brow.py`: per side, a carrier (pads, bar, arm, hub on an M3 shoulder screw, rocker lever) and a bracket (cheek with M3 insert, upright, MG90S plate, top flange). The servo, horn, pushrod and screw are written as reference meshes.
  - `brow_check.py`: both brows through −7..+13.9° plus 3° overtravel, against the EyeMech, the lid and eye sweeps, the brackets and servos. It also measures pad push/pull and the four-bar.
- **Adafruit MG90 STEP** downloaded (MIT) to `inputs/components/` and listed in `components.yaml`. Servo sizes measured from it: case 22.6 × 12.0, shaft 6.0 from the end, tabs 31.3 × 2.0, holes 29.7 apart.
- **Toolkit fix:** `components_check.py` broke on OCP 8 (`TopoDS.Solid_s` → `TopoDS.Solid`, and `Bnd_Box.Get()`). Patched in the project copy; **the code-cad skill's toolkit has the same bug.**

**Numbers:**
- New params: `BROW_*`, `MG90_*`, `SHOULDER_*`, `M2_PILOT`, `M3_CLEAR`, `M3_INSERT_HOLE`.
- `BROW_CHEEK_T` 4 → 7, so an M3 × 4 insert fits.
- Four-bar: servo −14.0..+28.8° for carrier −7.0..+13.9°; transmission angle 75–90°.

**Check:** `check: PASS (0 hard failure(s), 0 warning(s), 92 s)`, the first fully clean run. `LAYOUT OK`, `SWEEP OK`, `BROW OK`, `PRINT CHECK OK`, `NO OVERLAPS`.
- Carrier ≥ 3.8 from the EyeMech, ≥ 4.3 from the lid and eye sweeps, ≥ 2.1 from its bracket.
- Drive ≥ 1.5 clear. Pads 0.88 toward / 1.55 away from the skin.

**Renders:** [process_images](../process_images/README.md) snapshot 08: the study, `brow.png`, the first real `views.png`, and `print_check.png`.

**Problems and fixes along the way:**
- The servo reference was rotated wrong (case length pointing forward). It is now placed with explicit axes and verified against its intended local extents.
- The carrier arm crossed the bracket upright. It now comes down to the hub inboard of the upright (x′ ≤ 2.4 against 4.4), which holds at every angle because the carrier turns about x′.
- The hub's designed 0.4 thrust gap to the cheek read as a near-miss. The hub is now left out of the gap measurement; overlaps there still count.
- Printed upside down, the bracket had two unsupported overhangs. Fixed with a 45° slope from the cheek up into the upright and a 45° brace in place of the beam.
- With its hub upright, the carrier sits on almost no bed area. It needs tree supports in any orientation; it prints hub-down.

**Decisions:** D3 = P, a working design for the bench to confirm. D5 implemented. R10 (narrow concept window) and R11 (servo torque) added.

**Next:** Fresh-eyes review. Then adjustable hard stops and the bench rig.

## 2026-10-15 — M1 done — firmware ranges, tongue accepted

**Done:**
- **D12 decided: keep the tongue unmodified.** The team has printed this mouth before and it runs fine, and the bench outranks CAD. Added `ACCEPTED_CONTACTS` in `params.py`, so `pose_sweep` reports the tongue/servo contact as info (up to 8.3 mm³) and still fails anything bigger or any other pair.
- Eye and lid ranges come from Cogley's firmware (`Code/NewFaceFollower.py`): LR and UD 40..140, lids 90..170 / 90..10 / 90..160. They are swept 1:1 as ±50° eyes and 80° lids, a safe upper bound.
- Eye sockets moved to M3/M5 (they depend on D7 and the sculpt). Number for the sculptor: the face must come back about 8–9 mm around each eye.
- M1 marked done. One bench number is outstanding: the real jaw opening.

**Check:** `check: PASS (0 hard failure(s), 1 warning(s), 115 s)`. `LAYOUT OK`, `SWEEP OK`.
- Eyes stay ≥9.8 behind the outer skin, lids ≥8.4.
- Brow bays are 3.5 from the lid sweep, unchanged at 80°: the lids turn inside their own sphere.

**Renders:** [process_images](../process_images/README.md) snapshot 07 (M1 complete).

**Decisions:** D12 = B (keep the tongue as is).

**Next:** M2, the eyebrow concept study.

## 2026-10-15 — M1 — Motion sweeps and reserved space; process images folder

**Done:**
- D4 signed off as A2.
- New `process_images/` folder with `cad/snapshot.py`, which saves every check image permanently. Re-created and saved the earlier layout stages as snapshots 01–03.
- New `cad/reserve.py`:
  - brow bays per side: a servo bay above the EyeMech plus a carrier band down to the brow line, trimmed by the skin's inner surface
  - a Ø25 cable channel to the neck
- New `cad/pose_sweep.py`:
  - the jaw opens about its axis, with 10° of overtravel
  - eyes pan and tilt; top and bottom lids open
  - reserved volumes are checked against every part at rest and every swept pose
  - lip plate opening and chin travel are reported
- Both scripts are in the pipeline.
- Refactored the drawing helpers in `layout_check.py` so the motion check can reuse them.

**Numbers:**
- Motion ranges (ASSUMPTION): jaw 25° (+10° overtravel), eyes ±30° pan and ±25° tilt, top lids 60°, bottom lids 35°.
- `JAW_GROUP_CORE` = JawBase, JawLink, Part_33, Part_22 (the tongue).
- Neck and nape rows thickened: y_back at rows −45 / −68 / −92 / −112 / −130 went from −120 / −108 / −102 / −98 / −100 to −138 / −126 / −120 / −117 / −117. The neck half-width went from 56 to 60, and its front from −15 to −10.
- `CABLE_PATH` set (5 points, ending square through the base).

**Check:** `check: PASS (0 hard failure(s), 1 warning(s), 117 s)`. `LAYOUT OK`, `SWEEP OK`.
- The jaw is clean to 35° (smallest gap 1.1 mm, an M2 screw to an MG996R body at 20°). At 25° the chin drops 16.3 mm and the lip plates open from 12.0 to 41.1 mm.
- Brow bays: 2.4 mm from the EyeMech pivot at rest, 3.5 mm from the open top lids.
- Cable channel: 16.1 mm behind the open jaw, inside the skull.
- Layout margins with the thicker neck: mouth frame +0.6, jaw +3.3, eye module ↔ mouth +5.5.

**Renders:** [process_images](../process_images/README.md) snapshots 05 (first motion run) and 06 (after review, tongue clash visible).

**Problems and fixes along the way:**
- A height-only jaw grouping put eight frame screws on the jaw, and they "collided" at 5°. Now parts join the jaw by contact.
- The tongue sits above the height cut, so its links got dragged onto the frame. The tongue is now in the jaw core.
- The contact grouping first took 9 minutes; a KD-tree brought the whole sweep to about 1 minute.
- The rest pose counted as a failure because the jaw is 0.8 mm from its frame by Cogley's design. Rest-pose gaps are no longer judged.
- The cable channel didn't fit between the open jaw and the thin proxy neck. The neck is now thicker.
- A "beyond closed skin" column always read 0, because the proxy is solid under the chin. It is replaced by the lip plate opening.

**Review:** `cad-reviewer` result `check: PASS (0 hard failure(s), 1 warning(s), 109 s)`.
- It answered yes to all 5 questions, and confirmed the jaw axis is concentric within 0.1 mm with the JawLink bores, the MG996R spline and the horn.
- **Serious finding: the tongue (Part_22) clashes with a fixed MG90S** (x −24) from about 2.5° to 25°, by up to 8.6 mm³. My check hid it: the pair's rest gap is 0.49 mm, just under the 0.5 mm "designed contact" threshold, so it was skipped.
- Fixes applied:
  - designed contacts now mean touching at rest (0.05 mm), and their overlap may not grow
  - the MG996R horn, spline and horn screws now turn with the jaw (`JAW_HORN_R` 14, `JAW_HORN_X_MIN` 44)
  - 12 exact candidates per part, up from 7
  - the cable's skull margin skips its exit at the base (now +2.0)
  - new "inside skull" column for the jaw (+1.3 to +3.5)
  - the jaw-link render now cuts through the link near its bore
- After the fixes: `SWEEP: 1 issue(s)`, the tongue clash, 5 / 8 / 2 / 1 mm³ at 5 / 10 / 15 / 20°. Everything else on the jaw is clean to 35°.
- Snapshot 06.

**Decisions:** D12 (tongue clash) opened. Recommended: trim about 3 mm off the tongue's back corner, then confirm on the bench.

**Next:** D12. Then the M1 sign-off items: motion ranges from Cogley's code or the bench, and the proxy eye sockets. Then M2 (eyebrow prototype) inside the reserved brow bays.

## 2026-10-15 — M1 — First layout: both Cogley modules fit at 1.2× with boxy temples

**Done:**
- Replaced the example project with the real one.
  - `params.py` now holds the frame, the proxy head sections (two shapes), the head scale, the skin and skull thickness, and the measured module datums.
  - The example builder `enclosure.py` and its Pico params are deleted.
- Measured the module datums from the STEP files.
  - EyeMech: eye centres (±37.5, 0, 0), eyeball R16.0, lids are 1.6 shells (R16.5/18.1) pivoting on the x axis.
  - Mouth: lip plates' front y −92.6, lip line z −71.2, jaw pivot on the x axis at (y −2.4, z −40.7), driven straight off the MG996R outputs.
- New scripts:
  - `geom.py`: shared landmarks, sections and placements.
  - `modules.py`: places both assemblies, one mesh per solid, in `output/ref/` (gitignored).
  - `head.py`: proxy head plus the skin and skull envelopes.
  - `layout_check.py`: containment, module clearance, fit table for scales 1.0–1.3, and renders.
- All four are in the `cad.yaml` pipeline. Built the coupon STL.
- The mouth file's "invalid solids" are only its 4 tessellated surface parts (`Part_1`); every real solid is valid.
- Wrote design note [D4](DESIGN_NOTES.md#d4-head-size-and-shape).

**Numbers:**
- `HEAD_SCALE = 1.2` (ASSUMPTION, D4).
- `HEAD_SHAPE = "boxy_temples"` (was "average"). Front-half exponent 2.6 → 3.4 at the eye line. Half-width +2 at the eye line and cheekbones, +1 at the brow.
- `EYE_Z = 212.4`. Lip line at z 130.8. Jaw axis at y −65.8, z 161.3.
- `SKIN_T = 5.0`, `LIP_SKIN_T = 8.0`, `SKULL_WALL = 2.4` (ASSUMPTION).

**Check:** `check: PASS (0 hard failure(s), 2 warning(s), 94 s)`. Layout: `LAYOUT OK`.
- The warnings are expected: no assembled print parts exist yet, so the standard views are empty, and the coupon STL was stale until it was rebuilt.
- At 1.2× boxy, margins are: EyeMech frame +0.7, eyes +10.0, lids +8.4, lip plates +1.9, jaw +3.6, mouth frame +1.6, eye module ↔ mouth +2.5.

**Renders:** [process_images/](../process_images/README.md) snapshots 01–04: life size crashing, temples poking out at 1.2× average, boxy temples with the tight gap, and the approved A2 layout.

**Problems and fixes along the way:**
- A smooth loft through the sparse head sections overshot to 497 mm wide. Now the sections are interpolated with PCHIP every 4 mm and joined with a ruled loft.
- Mesh signed distance took over 10 minutes. Now each point is screened against the section formula and only the worst candidates are measured exactly: 40 s for four scales.
- The first render showed the modules at the last scale evaluated. Placement is now explicit before rendering.
- 1.2× with the average head left the EyeMech side plates 7.2 mm through the temples, so I added the boxy-temple shape (two tuning rounds).

**Review:** `cad-reviewer` result `Check: PASS (0 hard failure(s), 1 warning(s), 92 s)`.
- It confirmed every 1.2 number to within 0.4 mm with an independent recompute, and answered its 5 questions yes except the neck shape.
- Fixed from the review:
  - sections now draw a 12 mm slab, so parts behind the cut no longer look like they poke out
  - the `mouth surfaces` group is now checked (+9.0)
  - the lip line uses the same PCHIP fit as the loft
  - the chin and jaw rows now span to the back of the neck (w 50/52, pointed front n 1.5–2.0), so the "lightbulb" neck waist is gone
- Not fixed yet, and listed in PLAN M1: the section-shrink inset is not a true offset (the skin is as thin as 1.4 mm where the surface leans); the proxy has no eye sockets.

**Numbers:** `STOMION_DZ_1X` −68.0 → −70.5. The reviewer found the 2.5 mm eye-to-mouth gap too small for a skull shelf (3.2 needed). At 1.2× the change gives eye ↔ mouth +5.5, mouth frame +0.9, jaw +2.8, lip plates +2.4. `LAYOUT OK`.

**Decisions:** Q1 answered (aim for Halloween; the team owns the schedule). **D4 decided: A2**, 1.2×, boxy temples, lip line −70.5 (signed off the same day).

**Next:** D4 sign-off. Then group the moving parts and write `pose_sweep` (jaw, eye pan/tilt, lids), add a brow placeholder volume, and find a cable path.

## 2026-10-15 — M0 — Answers on printer, jar, CAD source and versions; ε3.1 vs ε3.2 compared

**Done:**
- Recorded the team's answers in [PLAN.md](PLAN.md#7-open-questions):
  - Q2: 2 × Bambu Lab P2S, 256 mm bed.
  - Q5: no jar yet; it will be chosen to fit the head.
  - Q12: the STEP files come from Cogley's own Onshape, through Patreon.
  - Q13: answered below.
- Compared the team's ε3.1 STEP with the public ε3.2 `MG90s - A.3mf` part by part, by size and volume. I also read the ε3.2 assembly guide.
- Set the printer bed in `cad.yaml` to the P2S (DATASHEET).
- Marked the reference files as Patreon-only: the repo stays private.

**Numbers:** ε3.1 vs ε3.2.
- Base plate, eyes, lids, levers, pivots, horns, eye adaptors and lateral frame: identical within 0.1 mm and 0.5 % volume.
- Central pivot holders and servo retainers: differ by 0.4–0.6 mm and 50–190 mm³, which fits the print-in-place joints and the A fit size.

**Decisions:**
- D10 tongue servo: keep it if it is no hassle. That makes 19 servos.
- D11 (decided): use ε3.2-PIP MG90s for both the print and the CAD. The ε3.2 model is to come from Cogley's Onshape if it is there; otherwise it will be rebuilt from the public print files.
- D4: the jar sets no limit, so the head scale (probably about 1.2) is driven by the mechanisms and proportions.

**Next:** Start M1, unless Q1 (the deadline) changes the scope.

## 2026-10-15 — M0 — Cogley STEP files received and surveyed

**Done:**
- The team supplied `EyeMech ε3.1.step` and `MouthAssembly.step`, both exported from Onshape today.
- Moved them to `inputs/reference/eyemech/EyeMech_e3.1.step` (renamed to ASCII, because the ε broke a Windows console script) and `inputs/reference/mouth/MouthAssembly.step`.
- Recorded both in [inputs/reference/README.md](../inputs/reference/README.md).
- Loaded both with build123d and surveyed them: part names, solid counts, bounding boxes and servo positions.
- Updated PLAN §3, R1, R2 and the M0 status, and added Q12 and Q13.

**Numbers** (first survey, bounding boxes in each file's own frame; nothing is in `params.py` yet):
- EyeMech: 38 valid solids, envelope 145.4 × 132.3 × 62.8. Eyeballs about Ø32, centres at x = ±37.5, so the eye spacing is 75.0.
- Mouth: 107 solids, envelope 112.4 × 118.6 × 86.9. 9 × MG90S. The two `Component2` bodies (40.0 × 28.8 × 57.1) are probably the MG996R jaw servos. Four tessellated surface parts (`Part_1`). The compound reports invalid solids.

**Problems:**
- The EyeMech does not fit a life-size head unchanged: its eye spacing is 75 against about 63 for an adult, and its base is 145 wide against an outer head width of about 155. Scaling the head about 1.2 is the likely answer (D4).
- The EyeMech file is ε3.1, but the brief names ε3.2 (Q13).
- The mouth has 9 MG90S servos, but the brief says 8 (Q13).
- The mouth file has invalid solids, still to be traced.

**Next:** Answer Q1–Q3, Q12 and Q13. Then start M1: set up the frame and datums in `params.py`, and write the `modules` builder that places both assemblies in the head frame.

## 2026-10-14/15 — M0 — Repo set up, brief received, plan v1

**Done:**
- Started the repo with the code-cad toolkit: a Python 3.12 venv, build123d 0.13, the check pipeline, the `cad-reviewer` agent, and the calibration coupon.
- Smoke-tested the toolkit on the skill's example part (a box for a Raspberry Pi Pico). The full pipeline ran: build, overlap check, print check, renders.
- Saved the project brief as [BRIEF.md](BRIEF.md).
- Researched the two Will Cogley mechanisms the brief names: what CAD is published for them, in which formats, and under which licence. Findings are in [PLAN.md](PLAN.md#3-inputs-what-exists-and-what-we-need).
- Wrote build plan v1: [PLAN.md](PLAN.md).

**Check:** `check: PASS (0 hard failure(s), 2 warning(s), 25 s)` on the example part. Both warnings are expected: the example's Pico STEP model is not downloaded, and no print files have been built yet.

**Findings from research:**
- Neither Cogley mechanism is published as STEP. EyeMech ε3.2 is 3MF only, and the Robot Head α2.0.33 is STL, 3MF and OBJ. Interfaces will be re-modelled from mesh measurements (PLAN R2).
- The brief's mouth (8 × MG90S + 2 × MG996R, with a mouth PCB) matches the Robot Head α2.0.33 mouth: 4 lip, 4 cheek and 2 jaw servos. The 2020 Mouth Mechanism has 7 + 2 servos, no PCB, and is the only one with a STEP. α2.0.33 is the working assumption until Q3 is answered.
- EyeMech has no external mounting holes, so the skull will clamp its base.
- EyeMech is licensed CC BY-NC-SA 4.0 (Q10).
- Cogley's α2.0 head has an Eyes/Brow/Neck board, so it likely contains a brow mechanism to study before M2.
- MG90S: Adafruit has an MIT STEP of the same body. MG996R: no trusted model found.

**Problems:** Nothing in the repo is project geometry yet. The example builder (`cad/enclosure.py`) and its Pico params stay until the first real builder exists.

**Next:** Answer the open questions in [PLAN.md](PLAN.md#7-open-questions), starting with the deadline, the printer, which mouth mechanism, and the jar size. Then gather the M0 inputs.

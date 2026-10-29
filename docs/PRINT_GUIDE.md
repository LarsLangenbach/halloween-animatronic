# Print guide

The parts that are ready to print, how to orient them, and the slicer settings.

**Ready-made plates:** `output/plates/eyebrows_plate.stl` (both brows) and `output/plates/eyemech_e3.2_MG90s_A_plate.stl` (Cogley's ε3.2 eye mechanism, size A, in his own layout; don't rearrange the parts, some print in place). In Bambu Studio: Split > To objects, then supports per the table below (tree supports on the brow carriers and on the whole EyeMech plate). Rebuild the brow plate after a change with `cad/make_plates.py`.

**EyeMech size A or B: test first.** A and B differ only in the shaft hole of the 6 printed servo horns: Ø4.92 mm (A) or Ø4.72 mm (B). The horn grips the servo by that press fit alone; the screw does not stop it turning. Print `output/plates/eyemech_servo_sizing_plate.stl` (from his `Testing Plate.3mf`; no supports) and push a real servo's shaft into each hole. Pick the letter that is tight without cracking. Size A slipped on the team's servos (2026-10-25). For B, `output/plates/eyemech_B_horn_parts_plate.stl` holds only the 6 objects that carry horns, in his layout (216 × 135 mm): the 4 lid sets, the Y-axis set (vertical horn) and X-axis part B (central horn). Split > To objects, tree supports as below.

**EyeMech supports: on.** Cogley's own project file has supports enabled for every part: tree (auto), threshold angle 30°, not limited to the build plate, 0.2 mm layers, 15 % infill, auto brim. It has no per-part overrides or painted supports. Bambu Studio warns when they are off. Easiest: open his original `output/plates/eyemech_e3.2_MG90s_A_cogley.3mf` (from his EyeMech_Epsilon GitHub, CC BY-NC-SA 4.0), which carries those settings. It was set up for the P1S: pick the P2S when asked and keep the project's process settings.

**Cogley's brow bars, TPU 95A (D15):** `output/plates/cogley_brow_bars_tpu_plate.stl` (both bars), or `cogley_brow_bar_L.stl` / `cogley_brow_bar_R.stl` one at a time. L is his Part 11, R is Part 14. They are taken unchanged from plate 5 ("Brows - Flexible") of his `BambuPrintfile.3mf`, in his print pose: each bar arches up off the bed and touches it only at its ends, so supports must be on. His settings: Generic TPU, tree supports (auto), threshold 30°, 0.2 mm layers, 6 walls, 25 % infill, auto brim. Each bar is 67 × 25 × 19 mm and weighs about 2 g. On the P2S, feed the TPU from the external spool, not the AMS, and use the Bambu TPU 95A preset. Take the supports off gently so the pleats don't tear.

**Smooth eyeball (D22):** `output/plates/cogley_eyeball_smooth.stl`, one eye; print two so they match (the part fits either side). It is Cogley's eyeball (`Component74`) with the iris dish and pupil hole filled to a plain round front; the socket and clips are his, unchanged. It sits in his print pose, flat back down and front up, 32 × 32 × 21.6 mm, under 11 g in PLA. Use his EyeMech settings (tree supports on, which go inside the socket) with 0.08 mm layers, or variable layer height, so the dome's top doesn't print as stepped rings. Turn on scarf seams if your Bambu Studio has them. Sand lightly before painting the iris and pupil. Rebuild with `cad/studies/cogley_eyeball.py`.

**Slice the files in `output/print/`.** They are already rotated into their print pose and sitting on the bed. Run `.venv\Scripts\python.exe cad\export_print.py` after any change to refresh them. The files in `output/stl/` are in the assembled pose; they are used for the checks.

Printer: Bambu Lab P2S, 0.4 nozzle, 256 × 256 × 256 bed. Every part fits the bed.

## Print first: the calibration coupon

| Part | Qty | Orientation | Supports | Why |
|---|---|---|---|---|
| `test_coupon` | 1 | flat, as exported | none | Picks the heat-set insert hole size (3.9 / 4.0 / 4.1) and the M2.5 / M3 clearance holes for this printer and filament. Put the result in `cad/params.py` (`INSERT_HOLE_D`, `M3_INSERT_HOLE`) before printing anything with inserts. |

## M2: eyebrow mechanism (one set = both brows)

| Part | Qty | Size (print pose) | Orientation | Supports | Notes |
|---|---|---|---|---|---|
| `brow_bracket_L` / `_R` | 1 each | 22 × 38 × 71 | upside down, on the top flange | none | The flange takes 2 M3 inserts from the bed side; the stop-screw ledge and slopes are designed for this pose. |
| `brow_carrier_L` / `_R` | 1 each | 70 × 21 × 41 | hub axis vertical, hub end face on the bed | tree supports (about 330 mm²) | Puts the pivot bore and ball-stud hole round. Remove the supports carefully from the pads' faces: those faces carry the skin. |
| `brow_rig` | 1 (left brow only) | 88 × 111 × 72 | lying on its inner wall (the open side faces up) | supports under the inside of the shell's curve (about 320 mm²) | Bench fixture only: it is not part of the head. |

## M3: skull (not ready to print)

`skull_front_upper`, `skull_front_lower`, `skull_back_upper`, `skull_back_lower`, `skull_shelf`, `skull_eye_strap`, `skull_neck_plate` and `skull_access_panel` have their joints, the EyeMech cradle, the neck base and the access panel. The mouth mount isn't in yet (Q14), so print them only as a fit or look test. Each piece fits the bed (199 mm tallest).

## M5: face mask (ready to print, D19)

`output/print/face_mask.stl` (v6): a 3 mm shell of a man's face with ears, 206 × 250 × 157 in its print pose, a 2 mm shell, about 250 g (v8). The eyes and mouth are flat with marks (eye axes, lip parting line and lip outlines); the nose is a low guide. It is a standalone sculpting piece: its inside touches Cogley's eye frame at the inner eye corners, so it doesn't sit down over the assembled mechanism.
- **Eyes and lips:** MakeHuman's own.
  - Its eyelids, with its own eyeballs filling the openings (open eyes, no holes). Each eyeball is centred exactly on the eye mechanism's eye centre (±37.5, z 212.4). An iris ring and a pupil are marked round each eye axis.
  - Its lips, scaled evenly (×1.11) about where they meet, so the corners reach just past the ends of Cogley's lip plates. The lip line sits on the gap between his upper and lower plates. The gap between MakeHuman's lips is closed, with a clean line where they meet.
- **Outline and surface:** from the chin over the forehead onto the skull, and round to the ears. Smooth for printing.
- **Print pose:** face up (as exported), with tree supports (they also touch the backs of the ears and the rim edges). The printed lip groove is about 6 mm low: sculpt the lip line 71.2 mm below the eye-centre line (`process_images/*lips-on-printed-mask*`).

**The old sculpt base pieces (`sculpt_upper`, `sculpt_lower`, `sculpt_plate`) are replaced by the mask: don't print them.**

## M5: mold base (ready to print)

The base the clay-covered face mask lies in, face up, for the plaster mold, and later the jig that holds the mask as the core for the silicone cast. Four base pieces that drop together (dovetails in the plate), and four wall corners that stand on the plate and clip together, so they come off before the plaster is lifted (L = the character's left, +X):

| Part | Size (print pose) | Orientation | Supports |
|---|---|---|---|
| `mold_base_chin_L` / `_chin_R` | up to 164 × 220 × 150 | plate on the bed, as exported | none |
| `mold_base_top_L` / `_top_R` | up to 164 × 191 × 152 | plate on the bed, as exported | none |
| `mold_wall_chin_L` / `_chin_R` | 168 × 224 × 45 | standing, as exported | none |
| `mold_wall_top_L` / `_top_R` | 168 × 207 × 45 | standing, as exported | none |
| `mold_pry_wedge` | 18 × 14 × 7, **8 off** | flat, as exported | none |

PLA, 0.2 mm layers (0.28 for speed), **4 walls** so the skirt and walls hold water, 5 top and 4 bottom layers, 15 % infill. Base pieces two per printer, then the wall corners and the 8 wedges.

**Ready-made plates (easiest):** `output/plates/mold_plate_chin_L.stl`, `_chin_R`, `_top_L`, `_top_R`. Each is one base piece, its wall corner nested round it 4 mm away, and 2 of the 8 pry wedges: 206–218 × 217–246 mm on the 256 bed. A base piece is too big to share a bed with another, so it is 4 plates, two per printer: the two `chin` plates overnight, the two `top` plates next. All parts print with the same settings and no supports. Splitting the plate into objects (right-click > Split > To objects) is optional. Preview: `output/plates/mold_plates_preview.png`. Rebuild with `cad/make_plates.py` after any change. How to put it together and use it: [PLASTER_MOLD.md](PLASTER_MOLD.md).

## M5: sculpt base (superseded by the face mask)

The head the clay face is sculpted on: the skull's outside raised by 3 mm. Three prints, one per printer at a time:

| Part | Size (print pose) | Orientation | Supports | Estimate |
|---|---|---|---|---|
| `sculpt_upper` | 183 × 248 × 168 | upright, on its flat cut face (as exported) | none (the eye sockets are shaped to print without) | ~8 h, ~410 g |
| `sculpt_lower` | 168 × 216 × 186 | upside down, on its flat cut face (as exported) | none | ~6 h, ~310 g |
| `sculpt_plate` | 190 × 174 × 8 | flat, keys up (as exported) | none | ~2 h, ~95 g |

Print them solid: PLA, 0.2 mm layers (0.28 is fine for speed), 3 walls, 4 top and bottom layers, lightning infill at 10 %. The estimates are rough; trust the slicer's. Assembly: [ASSEMBLY.md](ASSEMBLY.md#sculpt-base).

## M8: enclosure and neck (modelled 2026-10-28, v0, not printed yet)

The canister round the head (PLAN D23-D25): 31 prints, every one inside the 256 bed. Built by `cad/enclosure.py`; the sizes are in the print pose. All PLA. Sparse infill (15 %) and 3 walls everywhere; the flat rings and discs are thick and would be heavy solid.

| Part | Qty | Size (print pose) | Orientation | Supports | Notes |
|---|---|---|---|---|---|
| enc_base_F / L / B / R | 4 | 240 × 89 × 98 | as modelled: bottom lip on the bed | no | the wall quadrants; the inward flange at the top has a 45° chamfer under it. F has the speaker opening, B the hatch opening, L and R the vent slots |
| enc_ring_1..4 | 4 | 170 × 170 × 12 | as modelled: flat, slit up | no | deck ring quadrants: the sheet's lower slit, the lip the deck drops into, the column's foot inserts (3 and 4) |
| enc_tray | 1 | 250 × 250 × 33 | as modelled: flat | no | the speaker saddles and the bank's rails stand up from it |
| enc_deck | 1 | 239 × 239 × 8 | as modelled | no | M3 inserts go in from its underside |
| enc_pedestal | 1 | 130 × 130 × 40 | upside down (top face on the bed) | no | solid model: let the slicer fill it (15 %); the bolt pockets open at the print's top |
| enc_grille, enc_hatch | 2 | 96 tall standing on a short edge (126 × 15 footprint) | print_rotate [0, 90, 0] | no (brim) | the slots then print vertical; the hatch has the lead notch |
| enc_column_R_lower / L_lower | 2 | 159 × 97 × 232 | standing, foot flange on the bed, with a brim | no | the lap tabs have 51° chamfers under them |
| enc_column_R_upper / L_upper | 2 | 159 × 97 × 220 | standing, with a brim (bed contact is a 3 mm arc) | no | the wedge under the top flange prints without support |
| enc_capring_1..4 | 4 | 170 × 170 × 16 | as modelled: slit face on the bed | no | the slit's roof bridges 1.4 mm; 4 has the webcam lead's slot |
| enc_cap_F / L / B / R | 4 | 240 × 71 × 52 | as modelled: bottom flange on the bed | no | F has the flat front band with the lens hole and the webcam cradle |
| enc_captop_1..4 | 4 | 170 × 170 × 12 | as modelled: flat, recess up | no | |
| enc_lid | 1 | 239 × 239 × 8 | as modelled | no | vent slots, finger hole at the back |
| neck | 1 | 100 × 105 × 170 | as modelled: foot on the bed | no | the spine's inside is roofed at 45°; the tube's top is open |

Print order for a first fit: the neck and the pedestal (the head's mount, check the M4 pattern against the head), then one base wall quadrant and one deck ring quadrant (check the slit with a strip of the PETG sheet, the seam tab fit and the flange screws), then the rest.

## Suggested slicer settings

| | Brackets, carriers | Bench rig | Coupon |
|---|---|---|---|
| Material | PETG (or PLA for a first fit test) | PLA | the same filament as the parts |
| Layer height | 0.2 mm | 0.2 mm | 0.2 mm |
| Walls | 4 | 3 | 3 |
| Infill | 30 % gyroid | 15 % | 20 % |
| Notes | 4 walls around the pivot bore and the insert holes | | |

These are ASSUMPTIONs. Change them after the first prints, and log what worked in [BUILD_LOG.md](BUILD_LOG.md).

## Parts that are not printed here

The Will Cogley EyeMech and mouth are printed from Cogley's own files: ε3.2-PIP for the eyes (D11), and the mouth as you've printed it before (D12). The hardware is in [BOM.md](BOM.md).

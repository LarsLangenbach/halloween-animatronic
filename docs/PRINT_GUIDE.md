# Print guide

The parts that are ready to print, how to orient them, and the slicer settings.

**Ready-made plates:** `output/plates/eyebrows_plate.stl` (both brows) and `output/plates/eyemech_e3.2_MG90s_A_plate.stl` (Cogley's ε3.2 eye mechanism, size A, in his own layout; don't rearrange the parts, some print in place). In Bambu Studio: Split > To objects, then supports per the table below (tree supports on the brow carriers and on the whole EyeMech plate). Rebuild the brow plate after a change with `cad/make_plates.py`.

**EyeMech size A or B: test first.** A and B differ only in the shaft hole of the 6 printed servo horns: Ø4.92 mm (A) or Ø4.72 mm (B). The horn grips the servo by that press fit alone; the screw does not stop it turning. Print `output/plates/eyemech_servo_sizing_plate.stl` (from his `Testing Plate.3mf`; no supports) and push a real servo's shaft into each hole. Pick the letter that is tight without cracking. Size A slipped on the team's servos (2026-10-25). For B, `output/plates/eyemech_B_horn_parts_plate.stl` holds only the 6 objects that carry horns, in his layout (216 × 135 mm): the 4 lid sets, the Y-axis set (vertical horn) and X-axis part B (central horn). Split > To objects, tree supports as below.

**Just the eyelids:** `output/plates/cogley_lids_plate.stl` is the 4 lid sets alone, from his size-B file (`eyemech_e3.2_MG90s_B_cogley.3mf`): top lid and bottom lid for each eye, each set a lid with its top-lid horn and its lever already in the pivot (print in place, don't split a set). They sit as he prints them, lid standing on its hinge edge and lever flat on the bed, 10 mm apart, 152 × 97 × 41 mm. Split > To objects, tree supports on as below. Preview: `output/plates/cogley_lids_plate.png`. Rebuild with `cad/cogley_plate.py`.

**Keyed lids for the skin (D27):** `output/plates/cogley_lids_keyed_plate.stl` is the same 4 lid sets with each lid perforated so the brushed silicone locks on (PLA gives platinum silicone no bond): 21–24 radial Ø2.2 through-holes per lid, each opening into a Ø3.4 × 0.7 counterbore flush with the inner face, 5 mm apart, only through plain wall and never nearer than 1.1 mm to the lash edge, the side flange or the pivot. Nothing protrudes, so the lids move as before; the horns and levers are his, untouched. Print it instead of `cogley_lids_plate.stl` once the eyes get a skin: same pose, same settings (Split > To objects, tree supports on), 10 % less plastic. The hole axes point at the eye centre, so on the upper and lower parts of each lid they tilt up to about 60° from the bed and the tree supports land in or over roughly a quarter of the holes: pick the support interface out of every counterbore and check every neck is open before skinning. Skinning: stipple the first coat of FX-Pro through the holes from the outside with a stiff brush until it shows in every counterbore, wipe the inside flush with a card (the eyeball is 0.5 mm behind the lid), let it tack, then build the skin in layers; the cured rivets hold it. No release and no Sil-Poxy on the lid. Thickness budget (measured 2026-10-29 against the skull and the face mask through the lids' closing travel): the skull is never nearer than 3.9 mm, but the face skin's lid margins pass 0.7 mm over the lid at the inner eye corner once a lid has closed 20° or more, so feather the lid skin to under 0.4 mm within about 12 mm of the inner corner and keep it under about 1.5 mm elsewhere; and the lids meet edge to edge, so every millimetre of silicone on a lash edge stops the blink about 3° short of where the bare lids met (set the closed pose with the skin on). Close-ups: `output/plates/cogley_lids_keyed.png`; numbers: `cogley_lids_keyed.md`. Rebuild with `cad/lid_keyed.py` (needs the STEP in `inputs/reference`).

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

## M8: enclosure and neck, v1 (2026-10-29, the one-day version)

Eleven prints plus two PETG sheets (PLAN D26). Built by `cad/enclosure.py`; sizes in the print pose; slicer-ready files in `output/print/`. PLA, 3 walls, 15 % infill. Nothing needs support. Rough times are for a P2S on its standard profile: about 27 printer-hours in all, 13 per printer with two.

| Part | Qty | Size (print pose) | Orientation | Rough time | Notes |
|---|---|---|---|---|---|
| neck | 1 | 100 × 105 × 170 | as modelled, foot on the bed | 5 h | print first: offer it up to the head's frame |
| enc_pedestal | 1 | 90 × 90 × 142 | upside down (top plate on the bed), as the file lies | 3 h | a D 90 tube, 1.6 wall; print first with the neck |
| enc_tray | 1 | 250 × 250 × 53 | as modelled, flat | 3 h | the floor: ribs, bosses, speaker saddles, bank rails |
| enc_bottom_F / B | 2 | 249 × 249 × 12 (turned 45°) | as the file lies, lips and rim up | 1 h each | the band's lower rim; 4 ears to the tray |
| enc_top_F / B | 2 | 249 × 249 × 12 (turned 45°) | as the file lies, lip and rim up | 2.5 h each | the deck: the window's lower lip, the band's upper rim, ribs |
| enc_cap_F / B | 2 | 249 × 249 × 41 (turned 45°) | upside down, as the file lies | 3.5 h each | 1.2 mm top with ribs and vents, 40 mm skirt, the window's upper lips, the webcam stops |
| enc_grille, enc_hatch | 2 | 96 × 16 × 126, standing on a short edge | as the file lies, with a brim | 0.7 h each | the hatch has the lead notch |

Order: neck and pedestal on one printer, tray then bottom halves on the other; then the top halves, the cap halves and the panels, split across both.

The sheets (buy 1 mm clear PETG, two 1000 × 500 mm sheets):
- the window: a 891 × 477 mm blank rolled into a full tube, 20 mm overlap at the back, taped on the inside; it stands on the deck between the lip and the cap's lips. The back is see-through.
- the base's band: a 928 × 109 mm blank wrapped round the two rims, 20 mm overlap at the back, M3 + nut through the rims (6 top, 6 bottom); cut the two 110 × 64 openings (front, back) before fitting; paint it or use black sheet.

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

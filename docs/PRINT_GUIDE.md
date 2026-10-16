# Print guide

The parts that are ready to print, how to orient them, and the slicer settings.

**Ready-made plates:** `output/plates/eyebrows_plate.stl` (both brows) and `output/plates/eyemech_e3.2_MG90s_A_plate.stl` (Cogley's ε3.2 eye mechanism, size A, in his own layout; don't rearrange the parts, some print in place). In Bambu Studio: Split > To objects, then supports per the table below (tree supports on the brow carriers and on the whole EyeMech plate). Rebuild the brow plate after a change with `cad/make_plates.py`.

**EyeMech supports: on.** Cogley's own project file has supports enabled for every part: tree (auto), threshold angle 30°, not limited to the build plate, 0.2 mm layers, 15 % infill, auto brim. It has no per-part overrides or painted supports. Bambu Studio warns when they are off. Easiest: open his original `output/plates/eyemech_e3.2_MG90s_A_cogley.3mf` (from his EyeMech_Epsilon GitHub, CC BY-NC-SA 4.0), which carries those settings. It was set up for the P1S: pick the P2S when asked and keep the project's process settings.

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

## M5: sculpt base (ready to print)

The head the clay face is sculpted on: the skull's outside raised by 3 mm. Three prints, one per printer at a time:

| Part | Size (print pose) | Orientation | Supports | Estimate |
|---|---|---|---|---|
| `sculpt_upper` | 183 × 248 × 168 | upright, on its flat cut face (as exported) | none (the eye sockets are shaped to print without) | ~8 h, ~410 g |
| `sculpt_lower` | 168 × 216 × 186 | upside down, on its flat cut face (as exported) | none | ~6 h, ~310 g |
| `sculpt_plate` | 190 × 174 × 8 | flat, keys up (as exported) | none | ~2 h, ~95 g |

Print them solid: PLA, 0.2 mm layers (0.28 is fine for speed), 3 walls, 4 top and bottom layers, lightning infill at 10 %. The estimates are rough; trust the slicer's. Assembly: [ASSEMBLY.md](ASSEMBLY.md#sculpt-base).

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

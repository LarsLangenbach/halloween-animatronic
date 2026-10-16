# Print guide

The parts that are ready to print, how to orient them, and the slicer settings.

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

`skull_front_upper`, `skull_front_lower`, `skull_back_upper`, `skull_back_lower` and `skull_shelf` are v0. They have no joints or mounts yet, so don't print them except as a fit or look test. Each piece fits the bed (186 mm tallest).

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

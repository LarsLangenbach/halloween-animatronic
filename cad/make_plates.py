"""
Build plates: several print-ready parts (output/print, from export_print.py)
laid out on one bed as a single STL, for printing a set in one go.

  output/plates/<plate>.stl

In Bambu Studio, import the plate, then right-click > Split > To objects, so
each part keeps its own settings (supports only where PRINT_GUIDE.md says).

Run after export_print.py:  python cad/make_plates.py
"""
import os
import sys

import numpy as np
import trimesh

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import cadkit as K  # noqa: E402

GAP = 10.0                     # mm between parts
PLATES = {
    "eyebrows_plate": ["brow_carrier_L", "brow_carrier_R", "brow_bracket_L", "brow_bracket_R"],
}


def layout(meshes, bed):
    """Rows, left to right, largest footprint first; returns the placed meshes."""
    order = sorted(meshes, key=lambda m: -m.extents[0] * m.extents[1])
    x = y = row_h = 0.0
    placed = []
    for m in order:
        w, d = m.extents[0], m.extents[1]
        if x and x + w > bed[0]:
            x, y, row_h = 0.0, y + row_h + GAP, 0.0
        lo = m.bounds[0]
        mm = m.copy()
        mm.apply_translation([x - lo[0], y - lo[1], -lo[2]])
        placed.append(mm)
        x += w + GAP
        row_h = max(row_h, d)
    plate = trimesh.util.concatenate(placed)
    lo, hi = plate.bounds
    plate.apply_translation([-(lo[0] + hi[0]) / 2, -(lo[1] + hi[1]) / 2, 0.0])
    return plate


def main():
    src = os.path.join(K.PROJECT, "output", "print")
    out = os.path.join(K.PROJECT, "output", "plates")
    os.makedirs(out, exist_ok=True)
    bed = K.printer()["bed"]
    for name, parts in PLATES.items():
        meshes = [trimesh.load(os.path.join(src, p + ".stl"), force="mesh") for p in parts]
        plate = layout(meshes, bed)
        e = plate.extents
        fits = e[0] <= bed[0] - 6 and e[1] <= bed[1] - 6
        plate.export(os.path.join(out, name + ".stl"))
        print(f"{'' if fits else 'WARN  '}wrote plates/{name}.stl: {len(parts)} parts, "
              f"{e[0]:.1f} x {e[1]:.1f} x {e[2]:.1f} mm{'' if fits else ' (does not fit the bed)'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

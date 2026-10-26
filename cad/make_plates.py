"""
Build plates: several print-ready parts (output/print, from export_print.py)
laid out on one bed as a single STL, for printing a set in one go.

  output/plates/<plate>.stl

In Bambu Studio, import the plate, then right-click > Split > To objects, so
each part keeps its own settings (supports only where PRINT_GUIDE.md says).

The mold base gets one plate per quarter (mold_plate_<quarter>.stl): the base piece, its wall
corner wrapped round its outside corner, and two pry wedges beside its split edge. A base piece
is too big to share a bed with another, so the set is 4 plates, two per printer.

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
MOLD_WALL_GAP = 4.0            # mm between a mold base piece and the wall corner nested round it
MOLD_EDGE = 3.0                # keep this far in from the bed's edge
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


def mold_plate(quarter, bed):
    """One mold quarter as a plate: the base piece as it stands, its wall corner moved out past its
    two outer edges (wall thickness + MOLD_WALL_GAP) and down onto the bed, and two pry wedges
    beyond its split edge. Built from output/stl (the mold pose), where they share a frame.
    Returns (plate mesh, closest wall-to-base gap)."""
    import mold_base as MB
    P = K.params()
    stl = K.stl_dir()
    base = trimesh.load(os.path.join(stl, f"mold_base_{quarter}.stl"), force="mesh")
    wall = trimesh.load(os.path.join(stl, f"mold_wall_{quarter}.stl"), force="mesh")
    wedge = trimesh.load(os.path.join(stl, "mold_pry_wedge.stl"), force="mesh")
    sx = 1.0 if quarter.endswith("L") else -1.0
    sy = 1.0 if quarter.startswith("chin") else -1.0
    d = P.MOLD_WALL[1] + MOLD_WALL_GAP
    wall.apply_translation((sx * d, sy * d, -wall.bounds[0][2]))
    gap = MB.to_mf(base).min_gap(MB.to_mf(wall), 50.0)
    lo, hi = base.bounds
    x = (lo[0] - GAP - wedge.extents[0] / 2) if sx > 0 else (hi[0] + GAP + wedge.extents[0] / 2)
    yc = (lo[1] + hi[1]) / 2
    parts = [base, wall]
    for y in (yc - 20.0, yc + 20.0):
        w = wedge.copy()
        w.apply_translation((x - (w.bounds[0][0] + w.bounds[1][0]) / 2, y - (w.bounds[0][1] + w.bounds[1][1]) / 2,
                             -w.bounds[0][2]))
        parts.append(w)
    plate = trimesh.util.concatenate(parts)
    lo, hi = plate.bounds
    plate.apply_translation([-(lo[0] + hi[0]) / 2, -(lo[1] + hi[1]) / 2, 0.0])
    return plate, gap


def preview(plates, path, bed):
    """Top views of the mold plates, each on its bed square."""
    import render_views as RV
    from PIL import Image, ImageDraw, ImageFont
    sys.path.insert(0, HERE)
    import mold_check as MC
    tiles = []
    for name, (plate, colours) in plates.items():
        acts = [RV.surface_actor(MC.poly(m), c) for m, c in colours]
        bedbox = trimesh.creation.box((bed[0], bed[1], 1.0))
        bedbox.apply_translation((0, 0, -0.6))
        acts.append(RV.surface_actor(MC.poly(bedbox), (0.85, 0.85, 0.85)))
        tiles.append((name, RV.render(acts, np.array([0.0, 0.0, 0.0]), (0, 0, 1), (0, 1, 0), bed[1] / 2 + 6)))
    W = RV.TILE
    sheet = Image.new("RGB", (len(tiles) * W, W + 70), "white")
    dr = ImageDraw.Draw(sheet)
    try:
        f1, f2 = ImageFont.truetype("arial.ttf", 20), ImageFont.truetype("arial.ttf", 15)
    except OSError:
        f1 = f2 = ImageFont.load_default()
    dr.text((10, 8), "Mold plates on the 256 x 256 bed (grey): base piece, its wall corner, 2 pry wedges", fill="black", font=f1)
    for k, (t, im) in enumerate(tiles):
        sheet.paste(im, (k * W, 60))
        dr.text((k * W + 8, 40), t, fill="black", font=f2)
    sheet.save(path)


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
    ok = True
    shown = {}
    for q in ("chin_L", "chin_R", "top_L", "top_R"):
        plate, gap = mold_plate(q, bed)
        e = plate.extents
        fits = e[0] <= bed[0] - 2 * MOLD_EDGE and e[1] <= bed[1] - 2 * MOLD_EDGE and e[2] <= bed[2]
        apart = gap >= MOLD_WALL_GAP - 1.0
        ok &= fits and apart
        plate.export(os.path.join(out, f"mold_plate_{q}.stl"))
        bodies = plate.split(only_watertight=False)
        cols = [(b, (0.45, 0.62, 0.78) if b.extents[2] > 100 else (0.62, 0.62, 0.66) if b.extents[2] > 20
                 else (0.95, 0.55, 0.15)) for b in bodies]
        shown[f"mold_plate_{q}"] = (plate, cols)
        print(f"{'' if fits and apart else 'FAIL  '}wrote plates/mold_plate_{q}.stl: {len(bodies)} parts, "
              f"{e[0]:.1f} x {e[1]:.1f} x {e[2]:.1f} mm, wall {gap:.1f} mm from the base piece")
    preview(shown, os.path.join(out, "mold_plates_preview.png"), bed)
    print("wrote plates/mold_plates_preview.png")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())

"""
Build plates of Will Cogley's own parts, taken from one of his Bambu Studio project files in
his print pose, laid out on one bed as a single STL, for printing a few of his parts without
opening the whole file.

  output/plates/cogley_<plate>.stl   and a preview  cogley_<plate>.png (top view and iso)

A plate names whole objects by a part they contain, so a print-in-place set (a lid with its
horn and lever already in its pivot) comes out complete. The meshes are taken as he saved
them: his print pose, his mesh, nothing re-oriented. In Bambu Studio, import the plate, then
right-click > Split > To objects and turn on the supports his file uses (PRINT_GUIDE.md).

Not in the pipeline. Run:  python cad/cogley_plate.py
"""
import os
import re
import sys
import xml.etree.ElementTree as ET
import zipfile

import numpy as np
import trimesh

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import cadkit as K  # noqa: E402
import read3mf  # noqa: E402
from make_plates import GAP  # noqa: E402

PLATES_DIR = os.path.join(K.PROJECT, "output", "plates")
EYEMECH_B = os.path.join(PLATES_DIR, "eyemech_e3.2_MG90s_B_cogley.3mf")   # his EyeMech e3.2, size B horns
PLATES = {
    # plate: (source 3MF, part names; every object holding one of these parts goes on the plate, whole)
    "lids_plate": (EYEMECH_B, ["LidTR", "LidBR"]),   # the 4 lid sets: lid + top-lid horn + lever, print in place
}


def build_transforms(path):
    """Object id -> 4x4 build-item transform (his print pose and placement), which read3mf leaves out."""
    z = zipfile.ZipFile(path)
    main = ET.fromstring(z.read("3D/3dmodel.model"))
    return {it.get("objectid"): read3mf._transform(it.get("transform"))
            for it in main.iter(f"{{{read3mf.NS['m']}}}item")}


def posed_objects(path):
    """Every object in its print pose: object id -> [(part name, mesh), ...]."""
    tf = build_transforms(path)
    objs = {}
    for p in read3mf.parts(path):
        m = p["mesh"].copy()
        m.apply_transform(tf[p["object_id"]])
        objs.setdefault(p["object_id"], []).append((p["part"], m))
    return objs


def on_bed_area(m, tol=0.3):
    """Area of the faces lying on the bed (z within tol of the lowest point), mm^2."""
    z = m.vertices[m.faces][:, :, 2]
    return float(m.area_faces[np.all(z < m.bounds[0][2] + tol, axis=1)].sum())


def layout(groups, bed):
    """Rows, left to right, largest footprint first. A group is a list of meshes that keep their
    relative pose (one print-in-place object). Returns the placed groups, centred on the bed."""
    def ext(g):
        b = np.array([m.bounds for m in g])
        return b[:, 0].min(0), b[:, 1].max(0)
    order = sorted(groups, key=lambda g: -np.prod((ext(g)[1] - ext(g)[0])[:2]))
    x = y = row_h = 0.0
    placed = []
    for g in order:
        lo, hi = ext(g)
        w, d = hi[0] - lo[0], hi[1] - lo[1]
        if x and x + w > bed[0]:
            x, y, row_h = 0.0, y + row_h + GAP, 0.0
        placed.append([m.copy() for m in g])
        for m in placed[-1]:
            m.apply_translation([x - lo[0], y - lo[1], -lo[2]])
        x += w + GAP
        row_h = max(row_h, d)
    lo, hi = ext([m for g in placed for m in g])
    for g in placed:
        for m in g:
            m.apply_translation([-(lo[0] + hi[0]) / 2, -(lo[1] + hi[1]) / 2, 0.0])
    return placed


def preview(groups, path, bed, title):
    import render_views as RV
    import mold_check as MC
    from PIL import Image, ImageDraw
    pal = [(0.85, 0.45, 0.35), (0.35, 0.55, 0.85), (0.45, 0.75, 0.45), (0.85, 0.75, 0.35),
           (0.6, 0.4, 0.7), (0.4, 0.7, 0.7)]
    acts = [RV.surface_actor(MC.poly(m), pal[i % len(pal)]) for i, g in enumerate(groups) for m in g]
    bedbox = trimesh.creation.box((bed[0], bed[1], 1.0))
    bedbox.apply_translation((0, 0, -0.6))
    acts.append(RV.surface_actor(MC.poly(bedbox), (0.85, 0.85, 0.85)))
    allm = trimesh.util.concatenate([m for g in groups for m in g])
    half = max(allm.extents[0], allm.extents[1]) / 2 + 15
    top = RV.render(acts, np.array([0.0, 0.0, 0.0]), (0, 0, 1), (0, 1, 0), half)
    iso = RV.render(acts, np.array([0.0, 0.0, 0.0]), (1, -1, 1), (0, 0, 1), half)
    W = RV.TILE
    sheet = Image.new("RGB", (2 * W, W + 40), "white")
    ImageDraw.Draw(sheet).text((10, 10), title, fill="black")
    sheet.paste(top, (0, 40))
    sheet.paste(iso, (W, 40))
    sheet.save(path)


def main():
    os.makedirs(PLATES_DIR, exist_ok=True)
    bed = K.printer()["bed"]
    rc = 0
    for name, (src, wanted) in PLATES.items():
        objs = posed_objects(src)
        groups, labels = [], []
        for oid, parts in objs.items():
            hit = [pn for pn, _ in parts if pn in wanted]
            if hit:
                groups.append([m for _, m in parts])
                labels.append((hit[0], [pn for pn, _ in parts]))
        if not groups:
            print(f"FAIL  {name}: no object in {os.path.basename(src)} holds {wanted}")
            rc = 1
            continue
        placed = layout(groups, bed)
        plate = trimesh.util.concatenate([m for g in placed for m in g])
        path = os.path.join(PLATES_DIR, f"cogley_{name}.stl")
        plate.export(path)
        e = plate.extents
        ok = e[0] <= bed[0] and e[1] <= bed[1]
        print(f"wrote plates/cogley_{name}.stl  {len(groups)} objects from {os.path.basename(src)}, "
              f"{e[0]:.1f} x {e[1]:.1f} x {e[2]:.1f} mm on a {bed[0]} x {bed[1]} bed  {'OK' if ok else 'FAIL: over the bed'}")
        for (lead, pns), g in zip(labels, placed):
            allm = trimesh.util.concatenate(g)
            ex = allm.extents
            wt = all(m.is_watertight for m in g)
            print(f"  {lead:6s} set: {', '.join(pns)}  {ex[0]:.1f} x {ex[1]:.1f} x {ex[2]:.1f} mm, "
                  f"{'watertight' if wt else 'OPEN'}, {on_bed_area(allm):.0f} mm^2 on the bed")
        png = os.path.join(PLATES_DIR, f"cogley_{name}.png")
        preview(placed, png, bed, f"cogley_{name} from {os.path.basename(src)} (his print pose): top view, iso")
        print(f"  preview plates/cogley_{name}.png")
        rc |= 0 if ok else 1
    return rc


if __name__ == "__main__":
    sys.exit(main())

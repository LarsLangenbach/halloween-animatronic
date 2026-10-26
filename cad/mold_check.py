"""
Mold base check (M5): the four printed base pieces against the printed face mask, in the
mold pose (face up, plate on the table).

  1. the mask seats in the collar without touching it, and goes in and out straight up and down
  2. no face of the base that the plaster can reach points down (it would hook the jacket):
     outside the skirt's foot, above the plate, inside the walls
  3. the four base pieces and four wall corners don't overlap, drop together from above, the
     wall corners come off outward (away from the plaster) before it is lifted, each fits the bed
  4. how much of the mask hides from straight above (the strips by the ears and along the jaw
     that the team fills with clay or covers with side pieces), and a rough plaster estimate
Renders: output/check/mold/mold.png (assembled, from above, exploded) and mold_sections.png.

Run:  python cad/mold_check.py   -> last line "MOLD OK" when every item passes
"""
import os
import sys

import manifold3d as mf
import numpy as np
import trimesh
from matplotlib.path import Path

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import cadkit as K  # noqa: E402
import mold_base as MB  # noqa: E402

sys.stdout.reconfigure(encoding="utf-8")
P = K.params()
COLOURS = {"mold_base_chin_L": (0.45, 0.62, 0.78), "mold_base_chin_R": (0.38, 0.55, 0.72),
           "mold_base_top_L": (0.55, 0.70, 0.62), "mold_base_top_R": (0.48, 0.64, 0.56),
           "mold_wall_chin_L": (0.62, 0.62, 0.66), "mold_wall_chin_R": (0.55, 0.55, 0.60),
           "mold_wall_top_L": (0.66, 0.64, 0.58), "mold_wall_top_R": (0.60, 0.58, 0.52)}
MASK_RGB = (0.90, 0.82, 0.72)
RED = (0.85, 0.15, 0.12)
LIFTS = (0.25, 0.5, 1.0, 2.0, 3.0, 5.0, 8.0, 12.0, 20.0, 40.0, 60.0)   # mm above the seated position


def load_pieces(info=None):
    """{name: mesh}: the four base pieces, the four wall corners and (given the layout) the
    eight pry wedges in their places."""
    out = {}
    for kind in ("mold_base", "mold_wall"):
        for n in MB.PIECES:
            path = os.path.join(K.stl_dir(), f"{kind}_{n}.stl")
            if not os.path.exists(path):
                raise SystemExit(f"FAIL  {path} missing: run mold_base.py first")
            out[f"{kind}_{n}"] = trimesh.load(path, force="mesh")
    if info is not None:
        wedge = trimesh.load(os.path.join(K.stl_dir(), "mold_pry_wedge.stl"), force="mesh")
        for k, m in enumerate(MB.pry_placements(info["xi"], info["y0"], info["y1"])):
            w = wedge.copy()
            w.apply_transform(np.vstack([m, (0, 0, 0, 1.0)]))
            out[f"mold_pry_wedge_{k + 1}"] = w
    return out


def outward(name, info=None):
    """The direction a wall corner comes off in (out from its corner of the base), or a pry
    wedge (straight out through its wall)."""
    if name.startswith("mold_pry_wedge"):
        m = MB.pry_placements(info["xi"], info["y0"], info["y1"])[int(name.rsplit("_", 1)[1]) - 1]
        return -m[:, 1]
    return np.array([1.0 if name.endswith("L") else -1.0, 1.0 if "chin" in name else -1.0, 0.0])


def outer_faces(m, zs):
    """The mask's outside: faces pointing away from the point its directions start from."""
    c = MB.mold_pose(MB.centre(), zs)
    return ((m.triangles_center - c) * m.face_normals).sum(axis=1) > 0


def hidden_from_above(m, outer):
    """Outer faces of the mask that a ray straight down doesn't reach first."""
    c = m.triangles_center
    cand = np.where(outer)[0]
    hit = m.ray.intersects_first(c[cand] + (0, 0, 500.0), np.tile((0, 0, -1.0), (len(cand), 1)))
    hid = np.zeros(len(m.faces), bool)
    hid[cand[hit != cand]] = True
    return hid


def poly(mesh):
    import vtk
    from vtkmodules.util.numpy_support import numpy_to_vtk, numpy_to_vtkIdTypeArray
    pts = vtk.vtkPoints()
    pts.SetData(numpy_to_vtk(np.ascontiguousarray(mesh.vertices, dtype=float), deep=True))
    f = np.hstack([np.full((len(mesh.faces), 1), 3), mesh.faces]).astype(np.int64).ravel()
    cells = vtk.vtkCellArray()
    cells.ImportLegacyFormat(numpy_to_vtkIdTypeArray(f, deep=True))
    p = vtk.vtkPolyData()
    p.SetPoints(pts)
    p.SetPolys(cells)
    return p


def render(pieces, mask, red, out_dir):
    import render_views as RV
    from PIL import Image, ImageDraw, ImageFont
    os.makedirs(out_dir, exist_ok=True)
    allv = np.vstack([p.vertices for p in pieces.values()])
    cen = (allv.min(axis=0) + allv.max(axis=0)) / 2
    plain = mask.submesh([np.where(~red)[0]], append=True)
    hook = mask.submesh([np.where(red)[0]], append=True) if red.any() else None

    def actors(explode=0.0, with_mask=True):
        acts = []
        for n, p in pieces.items():
            q = p.copy()
            if explode:
                q.apply_translation(outward(n, render.info) * explode * (2.0 if "wall" in n else 1.0))
            acts.append(RV.surface_actor(poly(q), COLOURS.get(n, (0.95, 0.55, 0.15))))
        if with_mask:
            acts.append(RV.surface_actor(poly(plain), MASK_RGB))
            if hook is not None:
                acts.append(RV.surface_actor(poly(hook), RED))
        return acts

    views = [("assembled: the mask (v9) face up in the base", actors(), (0.85, 0.75, 0.75), (0, 0, 1), 260),
             ("from above: red = hidden from above (clay fill or side pieces)", actors(), (0, 0, 1), (0, 1, 0), 230),
             ("the base alone: collar, skirt, posts, keys, walls, pry wedges (orange)", actors(with_mask=False), (0.6, -0.9, 1.1), (0, 0, 1), 260),
             ("pulled apart: 4 base pieces, 4 wall corners, 8 pry wedges", actors(30.0, False), (0, 0, 1), (0, 1, 0), 260),
             ("chin end", actors(), (0, 1, 0.25), (0, 0, 1), 230),
             ("side (character's left)", actors(), (1, 0, 0.25), (0, 0, 1), 230)]
    tiles = [(t, RV.render(a, cen, d, u, s)) for t, a, d, u, s in views]
    W = RV.TILE
    sheet = Image.new("RGB", (3 * W, 50 + 2 * W), "white")
    dr = ImageDraw.Draw(sheet)
    try:
        f1, f2 = ImageFont.truetype("arial.ttf", 22), ImageFont.truetype("arial.ttf", 15)
    except OSError:
        f1 = f2 = ImageFont.load_default()
    dr.text((10, 12), "Mold base: 4 base pieces + 4 removable wall corners; the clay-covered mask lies face up in the collar", fill="black", font=f1)
    for k, (t, im) in enumerate(tiles):
        x, y = (k % 3) * W, 50 + (k // 3) * W
        sheet.paste(im, (x, y))
        dr.text((x + 8, y + 6), t, fill="black", font=f2)
    path = os.path.join(out_dir, "mold.png")
    sheet.save(path)
    return path


def sections(pieces, mask, out_dir, info):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    T = P.MOLD_PLATE_T
    cuts = [("across at the ears (Y -185)", (0, 1, 0), -185.0, 0),
            ("across at the jaw (Y -125)", (0, 1, 0), -125.0, 0),
            ("along, through the forehead post (X 40)", (1, 0, 0), 40.0, 1),
            ("along the middle (X 0)", (1, 0, 0), 0.5, 1)]
    fig, axs = plt.subplots(2, 2, figsize=(15, 10.5), dpi=110)
    for ax, (title, n, off, horiz) in zip(axs.ravel(), cuts):
        o = np.array(n, float) * off
        for name, p in pieces.items():
            s = p.section(plane_origin=o, plane_normal=n)
            if s is None:
                continue
            for e in s.discrete:
                ax.fill(e[:, horiz], e[:, 2], color=COLOURS.get(name, (0.95, 0.55, 0.15)), alpha=0.9, lw=0.6, ec="k")
        s = mask.section(plane_origin=o, plane_normal=n)
        if s is not None:
            for e in s.discrete:
                ax.fill(e[:, horiz], e[:, 2], color=MASK_RGB, ec="k", lw=0.6)
        ax.axhline(0, color="0.4", lw=2)
        ax.set_aspect("equal")
        ax.set_title(title, fontsize=10)
        ax.set_xlabel("mm (X)" if horiz == 0 else "mm (Y: chin end right)")
        ax.grid(alpha=0.25)
    fig.suptitle("Mold base sections: blue/green = printed base, tan = printed mask (clay not shown). "
                 f"Plate {T:.0f} mm, walls {P.MOLD_WALL[0]:.0f} high", fontsize=11)
    fig.tight_layout()
    path = os.path.join(out_dir, "mold_sections.png")
    fig.savefig(path)
    plt.close(fig)
    return path


def closeups(pieces, mask, out_dir):
    """The seat up close: where the mask flares out the lip stands straight up, so it drops in."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    cuts = [("by the ear, character's left (Y -185)", (0, -185.0, 0), (0, 1, 0), 0, (60, 105), (0, 45)),
            ("jaw, left (Y -125)", (0, -125.0, 0), (0, 1, 0), 0, (55, 95), (55, 95)),
            ("chin end, near the midline (X 3)", (3.0, 0, 0), (1, 0, 0), 1, (-95, -50), (115, 160)),
            ("forehead end, near the midline (X 3)", (3.0, 0, 0), (1, 0, 0), 1, (-335, -290), (100, 145))]
    fig, axs = plt.subplots(1, 4, figsize=(19, 5.2), dpi=110)
    for ax, (title, o, n, h, xl, zl) in zip(axs, cuts):
        for name, p in pieces.items():
            sec = p.section(plane_origin=o, plane_normal=n)
            if sec is not None:
                for e in sec.discrete:
                    ax.fill(e[:, h], e[:, 2], color=COLOURS.get(name, (0.95, 0.55, 0.15)), ec="k", lw=0.6)
        sec = mask.section(plane_origin=o, plane_normal=n)
        if sec is not None:
            for e in sec.discrete:
                ax.fill(e[:, h], e[:, 2], color=MASK_RGB, ec="k", lw=0.6)
        ax.set_xlim(*xl)
        ax.set_ylim(*zl)
        ax.set_aspect("equal")
        ax.grid(alpha=0.3)
        ax.set_title(title, fontsize=10)
    fig.suptitle("The seat up close: blue/green = base (ledge, lip, skirt), tan = printed mask. The rim rests on "
                 "the ledge; the lip follows the inside where it can and stands straight up where the mask flares out",
                 fontsize=10)
    fig.tight_layout()
    path = os.path.join(out_dir, "mold_seat_closeups.png")
    fig.savefig(path)
    plt.close(fig)
    return path


def main():
    out_dir = os.path.join(K.check_out(), "mold")
    _, info, mask = MB.build()
    pieces = load_pieces(info)
    T = P.MOLD_PLATE_T
    fails, warns = [], []
    bed = K.printer()["bed"]

    # 1. clearance to the mask
    base = MB.union([MB.to_mf(p) for p in pieces.values()])
    mk = MB.to_mf(mask)
    inter = (base ^ mk).volume()
    gap = base.min_gap(mk, 5.0)
    print(f"base vs mask: overlap {inter:.3f} mm3, closest {gap:.2f} mm (seat gap {P.MOLD_SEAT[0]})")
    if inter > 0.01:
        fails.append(f"the base cuts into the mask ({inter:.2f} mm3)")
    if gap < 0.5 * P.MOLD_SEAT[0]:
        warns.append(f"the base comes within {gap:.2f} mm of the mask")

    # 1b. the mask drops in straight from above (and lifts straight out)
    worst = max(((base ^ mk.translate((0, 0, t))).volume(), t) for t in LIFTS)
    print(f"mask lowered in from above: worst overlap {worst[0]:.3f} mm3 (at {worst[1]} mm above its seat)")
    if worst[0] > 0.05:
        fails.append(f"the mask can't be lowered straight in: {worst[0]:.1f} mm3 overlap {worst[1]} mm above its seat")

    # 2. hooks: downward faces the plaster can reach
    allm = trimesh.util.concatenate([p for n, p in pieces.items() if not n.startswith("mold_pry_wedge")])   # out by then
    foot = Path(info["foot"])
    c = allm.triangles_center
    down = allm.face_normals[:, 2] < -0.05
    outside = ~foot.contains_points(c[:, :2])
    inwall = (np.abs(c[:, 0]) < info["xi"] - 0.5) & (c[:, 1] > info["y0"] + 0.5) & (c[:, 1] < info["y1"] - 0.5)
    hook = down & outside & inwall & (c[:, 2] > T + 0.2)
    ha = allm.area_faces[hook].sum()
    print(f"plaster side: {ha:.1f} mm2 of the base faces down (hooks)")
    if ha > 1.0:
        fails.append(f"{ha:.1f} mm2 of the base would hook the plaster")

    # 3. pieces: overlap and bed
    names = list(pieces)
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            v = (MB.to_mf(pieces[names[i]]) ^ MB.to_mf(pieces[names[j]])).volume()
            if v > 0.01:
                fails.append(f"{names[i]} and {names[j]} overlap {v:.2f} mm3")
    # assembly: the base pieces drop onto each other, then the wall corners onto the base;
    # demolding: each wall corner comes off outward, away from the plaster
    mfp = {n: MB.to_mf(p) for n, p in pieces.items()}
    bases = [n for n in names if n.startswith("mold_base")]
    wall_n = [n for n in names if n.startswith("mold_wall")]
    wedges = [n for n in names if n.startswith("mold_pry_wedge")]
    moves = [(a, b, (0, 0, t)) for a in bases for b in bases if a != b for t in LIFTS]
    moves += [(a, b, (0, 0, t)) for a in names for b in wall_n + wedges if a != b for t in LIFTS]
    moves += [(a, b, tuple(outward(b, info) * t)) for a in names for b in wall_n if a != b for t in LIFTS]
    moves += [(a, b, tuple(outward(b, info) * t)) for a in bases + wedges for b in wedges if a != b
              for t in LIFTS]                                         # the wedges come out once the walls are off
    worst = max(((mfp[a] ^ mfp[b].translate(v)).volume(), v, a, b) for a, b, v in moves)
    print(f"pieces lowered together, wall corners and pry wedges pulled off outward: worst overlap {worst[0]:.3f} mm3")
    if worst[0] > 0.01:
        fails.append(f"{worst[3]} can't move {tuple(round(x, 1) for x in worst[1])} past {worst[2]}: "
                     f"{worst[0]:.1f} mm3 overlap")
    for n, p in pieces.items():
        if n.startswith("mold_pry_wedge_") and not n.endswith("_1"):
            continue                                                  # one print file, 8 copies
        e = p.extents
        if not (sorted(e[:2]) <= sorted(bed[:2]) and e[2] <= bed[2]):
            fails.append(f"{n} ({e[0]:.0f} x {e[1]:.0f} x {e[2]:.0f}) does not fit the bed")
        if not p.is_watertight or p.body_count != 1:
            fails.append(f"{n} is not one watertight body")
        print(f"  {n}: {e[0]:.0f} x {e[1]:.0f} x {e[2]:.0f} mm, {p.volume / 1000:.0f} cm3 solid")

    # 4. the mask's strips hidden from above, and the plaster
    outer = outer_faces(mask, info["zs"])
    red = hidden_from_above(mask, outer)
    ra = mask.area_faces[red].sum() / 100
    rc = mask.triangles_center[red]
    print(f"mask hidden from above: {ra:.0f} cm2 (by the ears and along the jaw: fill with clay, or side pieces)")
    for side, s in (("left (+X)", rc[:, 0] > 0), ("right (-X)", rc[:, 0] < 0)):
        if s.any():
            print(f"  {side}: Y {rc[s, 1].min():.0f} .. {rc[s, 1].max():.0f}, Z {rc[s, 2].min():.0f} .. {rc[s, 2].max():.0f}")
    face_cm2 = mask.area_faces[outer].sum() / 100
    flange_cm2 = 2 * info["xi"] * (info["y1"] - info["y0"]) / 100
    loop = info["foot"]
    foot_cm2 = 0.5 * abs(np.dot(loop[:, 0], np.roll(loop[:, 1], 1)) - np.dot(loop[:, 1], np.roll(loop[:, 0], 1))) / 100
    jacket_l = (face_cm2 * 1.15 + (flange_cm2 - foot_cm2)) * 2.0 / 1000                # 20 mm thick
    print(f"plaster, roughly: face and skirts ~{face_cm2 * 1.15:.0f} cm2 + flange {flange_cm2 - foot_cm2:.0f} cm2, "
          f"20 mm thick -> ~{jacket_l:.1f} L mixed (~{jacket_l * 1.3:.0f} kg Ultracal/Hydrocal powder, "
          f"~{jacket_l * 0.95:.0f} kg plaster of Paris)")

    try:
        render.info = info
        print("render:", render(pieces, mask, red, out_dir))
        print("render:", sections(pieces, mask, out_dir, info))
        print("render:", closeups(pieces, mask, out_dir))
    except Exception as e:                                            # renders are evidence, not a pass item
        warns.append(f"render failed: {e}")
    for f in fails:
        print("FAIL ", f)
    for w in warns:
        print("WARN ", w)
    print("MOLD OK" if not fails and not warns else "MOLD NOT OK")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())

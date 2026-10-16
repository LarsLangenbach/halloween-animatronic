"""
M1 layout check: do Will Cogley's modules fit together inside the proxy head?

For every head scale in HEAD_SCALES_COMPARED (decision D4):
  - eyemech vs mouth: boolean overlap and closest approach between their
    solids (rest pose).
  - containment: every solid must stay inside the envelope its group allows,
    measured as the margin of its worst point (mm, + = inside):
        eyes, lids       inside head_outer   (seen through the eye openings)
        lips, surfaces   inside skin_inner   (under the silicone)
        jaw, frame       inside skull_inner  (inside the skull)
At HEAD_SCALE it also renders sections and views to <out>/layout/ and
writes the fit table to <out>/layout/layout.md.

Rest pose only. Pose sweeps (jaw open, eye and lid travel) come later in M1.
Sampling is seeded, so numbers repeat run to run.

Run:  python cad/layout_check.py      (after modules.py and head.py)
Final line: LAYOUT OK, or LAYOUT: n issue(s), each listed as a WARN line.
"""
import json
import os
import sys
import warnings

import numpy as np
import trimesh

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import cadkit as K  # noqa: E402
import geom as G  # noqa: E402
import head as H  # noqa: E402

warnings.filterwarnings("ignore", category=RuntimeWarning)
sys.stdout.reconfigure(encoding="utf-8")
P = K.params()

INSETS = H.INSETS
ENVELOPE_OF = {"eyes": "head_outer", "lids": "head_outer", "lips": "skin_inner",
               "surfaces": "skin_inner", "jaw": "skull_inner", "frame": "skull_inner"}
MODULE_GAP_MIN = 2.0      # mm, ASSUMPTION: least static gap between the eye and mouth modules
NOISE = 1.0               # mm3: boolean slivers below this are numerical noise
SAMPLES_PER_MM2 = 1 / 6.0
SEED = 7
SLAB = 12.0               # mm of geometry drawn behind each section cut
COLOURS = {
    ("eyemech", "eyes"): (0.96, 0.96, 0.92), ("eyemech", "lids"): (0.86, 0.62, 0.55),
    ("eyemech", "frame"): (0.35, 0.55, 0.85), ("mouth", "frame"): (0.50, 0.72, 0.42),
    ("mouth", "jaw"): (0.95, 0.68, 0.28), ("mouth", "lips"): (0.85, 0.32, 0.38),
    ("mouth", "surfaces"): (0.80, 0.55, 0.65),
}
LINES = {"head_outer": ((0, 0, 0), 3), "skin_inner": ((0.45, 0.45, 0.45), 2),
         "skull_inner": ((0.85, 0.1, 0.1), 2)}


# ---------------------------------------------------------------------------
# loading
# ---------------------------------------------------------------------------
def load_parts():
    ref = G.ref_dir()
    with open(os.path.join(ref, "modules.json"), encoding="utf-8") as f:
        index = json.load(f)
    rng = np.random.default_rng(SEED)
    parts = []
    for e in index["parts"]:
        m = trimesh.load(os.path.join(ref, e["file"]), force="mesh")
        n = int(np.clip(m.area * SAMPLES_PER_MM2, 30, 600))
        idx = rng.choice(len(m.faces), n, p=m.area_faces / m.area_faces.sum())
        u, v = rng.random((2, n))
        flip = u + v > 1
        u[flip], v[flip] = 1 - u[flip], 1 - v[flip]
        tri = m.triangles[idx]
        pts = tri[:, 0] + u[:, None] * (tri[:, 1] - tri[:, 0]) + v[:, None] * (tri[:, 2] - tri[:, 0])
        stride = max(1, len(m.vertices) // 300)
        pts = np.vstack([pts, m.vertices[::stride]])
        parts.append(dict(e, mesh=m, pts=pts))
    return index["head_scale"], parts


def moved(mesh, delta):
    m = mesh.copy()
    m.apply_translation(delta)
    return m


# ---------------------------------------------------------------------------
# measuring
# ---------------------------------------------------------------------------
def gap(b1, b2):
    return float(np.max(np.maximum(b2[0] - b1[1], b1[0] - b2[1])))


def module_clearance(eyes, mouth):
    """Closest approach between any eyemech solid and any mouth solid.
    Returns (clearance, pair); clearance < 0 means overlap (-cbrt of the volume).
    Overlaps: manifold booleans on solid pairs whose boxes intersect.
    Distance: KD-tree over the sample points, then an exact closest-point
    query for the nearest few, so the result is surface-accurate."""
    from scipy.spatial import cKDTree
    best = (np.inf, None)
    for a in eyes:
        for b in mouth:
            if gap(a["m"].bounds, b["m"].bounds) > 0.0:
                continue
            if a["watertight"] and b["watertight"] and not a["shell"] and not b["shell"]:
                try:
                    inter = trimesh.boolean.intersection([a["m"], b["m"]], engine="manifold")
                    vol = float(inter.volume) if inter is not None and len(inter.faces) else 0.0
                except Exception:                     # noqa: BLE001
                    vol = 0.0
                if vol > NOISE and -vol ** (1 / 3) < best[0]:
                    best = (-vol ** (1 / 3), f"{a['label']} / {b['label']} overlap {vol:.0f} mm3")
    if best[0] < 0:
        return best
    pa = np.vstack([p["p"] for p in eyes])
    ia = np.concatenate([[i] * len(p["p"]) for i, p in enumerate(eyes)])
    pb = np.vstack([p["p"] for p in mouth])
    ib = np.concatenate([[i] * len(p["p"]) for i, p in enumerate(mouth)])
    d, j = cKDTree(pb).query(pa)
    for k in np.argsort(d)[:40]:                      # refine the nearest candidates exactly
        a, b = eyes[ia[k]], mouth[ib[j[k]]]
        dd = float(trimesh.proximity.closest_point(b["m"], pa[k:k + 1])[1][0])
        dd = min(dd, float(trimesh.proximity.closest_point(a["m"], pb[j[k]:j[k] + 1])[1][0]))
        if dd < best[0]:
            best = (dd, f"{a['label']} / {b['label']}")
    return best


def containment(parts, scale, envs):
    """{(module, group): (worst margin, label, n solids outside)}; sets p['margin'].
    geom.envelope_margin screens every sample point (fast, inside/outside
    exact, but it overstates distances where the surface leans); each part's
    16 worst candidates are then measured exactly against the envelope mesh."""
    out = {}
    for p in parts:
        env = ENVELOPE_OF[p["group"]]
        rough = G.envelope_margin(p["p"], scale, INSETS[env])
        cand = p["p"][np.argsort(rough)[:16]]
        worst = float(trimesh.proximity.signed_distance(envs[env], cand).min())
        p["margin"] = worst
        key = (p["module"], p["group"])
        cur = out.get(key, (np.inf, "", 0))
        out[key] = (min(cur[0], worst), p["label"] if worst < cur[0] else cur[1],
                    cur[2] + (worst < 0))
    return out


def place(parts, base_scale, scale):
    """Move every part (mesh 'm', sample points 'p') to where it sits at `scale`."""
    delta = {mod: G.module_translation(mod, scale) - G.module_translation(mod, base_scale)
             for mod in ("eyemech", "mouth")}
    for p in parts:
        p["m"] = moved(p["mesh"], delta[p["module"]])
        p["p"] = p["pts"] + delta[p["module"]]


def evaluate(parts, base_scale, scale):
    place(parts, base_scale, scale)
    eyes = [p for p in parts if p["module"] == "eyemech"]
    mouth = [p for p in parts if p["module"] == "mouth"]
    envs = H.envelopes(scale)
    clear = module_clearance(eyes, mouth)
    contain = containment(parts, scale, envs)
    res = dict(scale=scale, clear=clear, contain=contain, envs=envs,
               margins=[(p["module"], p["group"], p["label"], p["margin"]) for p in parts])
    xs = [max(abs(x) for x, _ in pts) for _, pts in G.sections(scale)]
    ys = [y for _, pts in G.sections(scale) for _, y in pts]
    res["size"] = np.array([2 * max(xs), max(ys) - min(ys), G.z_abs(P.HEAD_SECTIONS_1X[0][0], scale)])
    return res


# ---------------------------------------------------------------------------
# rendering (VTK, reusing render_views' actors and camera)
# ---------------------------------------------------------------------------
def poly(mesh):
    """trimesh -> vtkPolyData."""
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


def plane(o, n):
    import vtk
    pl = vtk.vtkPlane()
    pl.SetOrigin(*o)
    pl.SetNormal(*n)
    return pl


def clip(p, o, n, depth=SLAB):
    """Keep a slab `depth` mm thick just behind the cut plane, so parts far
    behind it can't be drawn over the envelope lines at the plane."""
    import vtk
    c = vtk.vtkClipPolyData()
    c.SetInputData(p)
    c.SetClipFunction(plane(o, n))
    c.InsideOutOn()
    c.Update()
    back = np.asarray(o, float) - depth * np.asarray(n, float)
    c2 = vtk.vtkClipPolyData()
    c2.SetInputData(c.GetOutput())
    c2.SetClipFunction(plane(back, n))
    c2.Update()
    return c2.GetOutput()


def cut(p, o, n):
    import vtk
    c = vtk.vtkCutter()
    c.SetInputData(p)
    c.SetCutFunction(plane(o, n))
    c.Update()
    return c.GetOutput()


def sheet(tiles, out_dir, prefix, header_lines, cols=3):
    """Paste (title, image) tiles into <prefix>.png with header lines; also saves each tile."""
    from PIL import Image, ImageDraw, ImageFont
    import render_views as RV
    os.makedirs(out_dir, exist_ok=True)
    T, head = RV.TILE, 14 + 28 * len(header_lines)
    rows = (len(tiles) + cols - 1) // cols
    img = Image.new("RGB", (T * cols, T * rows + head), "white")
    draw = ImageDraw.Draw(img)
    font = ImageFont.load_default(size=20)
    for i, (title, tile) in enumerate(tiles):
        tile.save(os.path.join(out_dir, f"{prefix}_{i + 1}.png"))
        x, y = (i % cols) * T, (i // cols) * T + head
        img.paste(tile, (x, y))
        draw.text((x + 10, y + 8), title, fill=(0, 0, 0), font=font)
    for k, line in enumerate(header_lines):
        draw.text((10, 8 + 28 * k), line, fill=(0, 0, 0), font=font)
    path = os.path.join(out_dir, f"{prefix}.png")
    img.save(path)
    return path


def render_sheet(parts, res, out_dir):
    import render_views as RV

    groups = {}
    for p in parts:
        groups.setdefault((p["module"], p["group"]), []).append(p["m"])
    gpolys = {k: poly(trimesh.util.concatenate(v)) for k, v in groups.items()}
    epolys = {k: poly(m) for k, m in res["envs"].items()}
    s = res["scale"]
    ez, st = G.eye_z(s), G.stomion(s)
    b = res["envs"]["head_outer"].bounds
    centre = (b[0] + b[1]) / 2
    view_scale = 0.55 * float(max(b[1] - b[0]))

    sections = [
        ("side section x = 0", (0, 0, 0), (1, 0, 0), (0, 0, 1)),
        ("front section y = 0 (eye centres)", (0, 0, 0), (0, 1, 0), (0, 0, 1)),
        (f"top section z = {ez:.0f} (eye line)", (0, 0, ez), (0, 0, 1), (0, 1, 0)),
        (f"top section z = {st[2]:.0f} (lip line)", (0, 0, st[2]), (0, 0, 1), (0, 1, 0)),
    ]
    tiles = []
    for title, o, n, up in sections:
        actors = []
        for k, gp in gpolys.items():
            actors.append(RV.surface_actor(clip(gp, o, n), COLOURS[k]))
            actors.append(RV.line_actor(cut(gp, o, n), (0, 0, 0), 2))
        for k, ep in epolys.items():
            rgb, w = LINES[k]
            actors.append(RV.line_actor(cut(ep, o, n), rgb, w))
        c = np.array(centre, float)
        c[int(np.argmax(np.abs(n)))] = o[int(np.argmax(np.abs(n)))]
        tiles.append((title, RV.render(actors, c, n, up, view_scale)))
    for title, d in (("front, head 15 % opaque", (0, 1, 0)), ("3/4 from the left, head 15 % opaque", (0.8, 1.0, 0.45))):
        actors = [RV.surface_actor(gp, COLOURS[k]) for k, gp in gpolys.items()]
        ha = RV.surface_actor(epolys["head_outer"], (0.85, 0.80, 0.72))
        ha.GetProperty().SetOpacity(0.15)
        actors.append(ha)
        tiles.append((title, RV.render(actors, np.array(centre, float), d, (0, 0, 1), view_scale)))

    sz = res["size"]
    return sheet(tiles, out_dir, "layout", [
        f"M1 layout at head scale {s}: head {sz[0]:.0f} x {sz[1]:.0f} x {sz[2]:.0f} mm (x, y, z incl. neck), "
        f"same scale in every tile, +y = face, +x = character's left",
        f"sections show a {SLAB:.0f} mm slab behind the cut | lines: black = outer skin, grey = skin inner "
        "surface, red = skull inner surface | blue = EyeMech, green = mouth frame, orange = jaw, red = lip plates"])


# ---------------------------------------------------------------------------
def fmt_contain(c, key):
    v = c.get(key)
    if v is None:
        return "-"
    return f"{v[0]:+.1f} ({v[1]}{', ' + str(v[2]) + ' out' if v[2] else ''})"


def main():
    base_scale, parts = load_parts()
    scales = sorted(set(P.HEAD_SCALES_COMPARED) | {P.HEAD_SCALE})
    results = {s: evaluate(parts, base_scale, s) for s in scales}

    keys = [("eyemech", "eyes"), ("eyemech", "lids"), ("eyemech", "frame"),
            ("mouth", "lips"), ("mouth", "surfaces"), ("mouth", "jaw"), ("mouth", "frame")]
    head = ["scale", "head W x L x H", "eye <-> mouth closest"] + [f"{m} {g}" for m, g in keys]
    rows = []
    for s in scales:
        r = results[s]
        sz = r["size"]
        rows.append([f"{s:.2f}", f"{sz[0]:.0f} x {sz[1]:.0f} x {sz[2]:.0f}",
                     f"{r['clear'][0]:+.1f} ({r['clear'][1]})"] + [fmt_contain(r["contain"], k) for k in keys])
    md = ["# M1 layout fit table", "",
          "Margins in mm: + = inside the allowed envelope, - = sticking out; the part named is the worst one.",
          "Envelopes: eyes and lids inside the outer skin; lip plates inside the skin's inner surface;",
          "jaw and frame inside the skull's inner surface. Eye <-> mouth: closest approach, - = overlap.", "",
          "| " + " | ".join(head) + " |", "|" + "---|" * len(head)]
    md += ["| " + " | ".join(r) + " |" for r in rows]

    print("\n".join(md[6:]))
    r = results[P.HEAD_SCALE]
    issues = []
    if r["clear"][0] < MODULE_GAP_MIN:
        issues.append(f"eye and mouth modules {r['clear'][0]:+.1f} mm apart (want >= {MODULE_GAP_MIN}): {r['clear'][1]}")
    for k in keys:
        v = r["contain"].get(k)
        if v and v[0] < 0:
            issues.append(f"{k[0]} {k[1]}: {v[2]} part(s) outside {ENVELOPE_OF[k[1]]}, worst {v[0]:+.1f} mm ({v[1]})")
    print()
    for i in issues:
        print("WARN ", i)

    out_dir = os.path.join(K.check_out(), "layout")
    os.makedirs(out_dir, exist_ok=True)
    worst = sorted((m for m in r["margins"] if m[3] < 0), key=lambda m: m[3])[:15]
    md += ["", f"## Parts outside their envelope at scale {P.HEAD_SCALE}", ""]
    md += [f"- {mod} {grp} `{lab}`: {mg:+.1f} mm outside {ENVELOPE_OF[grp]}"
           for mod, grp, lab, mg in worst] or ["none"]
    place(parts, base_scale, P.HEAD_SCALE)
    try:
        img = render_sheet(parts, r, out_dir)
        md += ["", f"Renders: {os.path.basename(img)} (and layout_1..6.png)"]
        print("wrote", img)
    except Exception as e:                            # noqa: BLE001
        print(f"WARN  render failed: {e}")
        issues.append("render failed")
    with open(os.path.join(out_dir, "layout.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(md) + "\n")
    print("\nLAYOUT OK" if not issues else f"\nLAYOUT: {len(issues)} issue(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())

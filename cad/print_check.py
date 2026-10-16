"""
Printability of the print files, in their print orientation. Supports and
orientation come from `parts` in cad.yaml (keep it in step with the print
guide): a part prints as modelled unless it has a `print_rotate`. Thresholds
come from `printer` in cad.yaml (defaults in cadkit.PRINTER_DEFAULTS).

  overhang   faces pointing down more steeply than OVERHANG_DEG from the
             vertical, away from the bed, grouped into regions. A region
             prints without support if it is
               - a ledge: no wider than LEDGE_W (2 x area / perimeter) -- a
                 flange lip, a counterbore roof; or
               - a bridge: its whole rim sits on walls going down, and its
                 shortest span (the narrow side of its outline) is at most
                 BRIDGE_SPAN -- a pocket roof.
             Anything else needs support: a WARN on parts printed without
             supports, info (support area) on the others.
  thin wall  local wall thickness from a ray cast inward from every face to
             the opposite wall; regions under MIN_WALL mm are reported.
  bed        first-layer contact area.

Writes print_check.png next to the report: every part from below and from a
low 3/4 angle, overhangs red, thin walls blue, bed contact green.

Run:  python <source>/print_check.py [stl_dir]
  defaults: the project's stl_dir -> <out>/print_check.png
"""
import glob
import os
import sys

import numpy as np
import trimesh
import vtk
from PIL import Image, ImageDraw, ImageFont
from vtkmodules.util.numpy_support import numpy_to_vtk, numpy_to_vtkIdTypeArray

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import cadkit as K  # noqa: E402
import render_views as RV  # noqa: E402

_P = K.printer()
OVERHANG_DEG = float(_P["overhang_deg"])  # from vertical; flatter downward faces need support
LEDGE_W = float(_P["ledge_w"])            # mm; narrower one-sided overhangs print (heuristic)
BRIDGE_SPAN = float(_P["bridge_span"])    # mm; roofs held by walls all round print this far
MIN_WALL = float(_P["min_wall"])          # mm; two extrusion widths
MIN_REGION = 10.0       # mm2; smaller overhang regions bridge or sag harmlessly
BED_Z = 0.05
COLOURS = dict(plain=(225, 215, 220), over=(220, 40, 40), thin=(40, 90, 230), bed=(60, 170, 80))
TILE = 400
WARNS = []


def say(level, msg):
    print(f"{level:6s}{msg}")
    if level == "WARN":
        WARNS.append(msg)


def regions(mesh, mask):
    """Connected groups of the faces in `mask` -> list of face-index arrays."""
    idx = np.flatnonzero(mask)
    if not len(idx):
        return []
    adj = mesh.face_adjacency
    keep = mask[adj[:, 0]] & mask[adj[:, 1]]
    groups = trimesh.graph.connected_components(adj[keep], nodes=idx, min_len=1)
    return sorted(groups, key=lambda g: -mesh.area_faces[g].sum())


def width(mesh, faces):
    """2 x area / perimeter: the width of a strip, the radius of a disc."""
    edges = mesh.edges_sorted[np.isin(mesh.edges_face, faces)]
    uniq, count = np.unique(edges, axis=0, return_counts=True)
    rim = uniq[count == 1]
    perimeter = np.linalg.norm(mesh.vertices[rim[:, 0]] - mesh.vertices[rim[:, 1]], axis=1).sum()
    return 2 * mesh.area_faces[faces].sum() / perimeter if perimeter > 0 else 0.0


def bridge_span(mesh, faces):
    """Shortest span of a roof held up by walls all round, or None when part of
    its rim (more than 5 % of its length) isn't on a wall going down -- then it
    is a cantilever, not a bridge."""
    inside = np.zeros(len(mesh.faces), bool)
    inside[faces] = True
    adj = mesh.face_adjacency
    a_in, b_in = inside[adj[:, 0]], inside[adj[:, 1]]
    rim = a_in ^ b_in
    if not rim.any():
        return None
    outside = np.where(a_in[rim], adj[rim, 1], adj[rim, 0])
    edges = mesh.face_adjacency_edges[rim]
    p0, p1 = mesh.vertices[edges[:, 0]], mesh.vertices[edges[:, 1]]
    length = np.linalg.norm(p1 - p0, axis=1)
    below = mesh.triangles_center[outside][:, 2] < (p0[:, 2] + p1[:, 2]) / 2 - 0.01
    if length[below].sum() < 0.95 * length.sum():
        return None
    xy = mesh.vertices[np.unique(mesh.faces[faces])][:, :2]
    xy = xy - xy.mean(axis=0)
    axes = np.linalg.svd(xy, full_matrices=False)[2]
    proj = xy @ axes.T
    return float((proj.max(axis=0) - proj.min(axis=0)).min())


def prints_unsupported(mesh, faces):
    if width(mesh, faces) <= LEDGE_W:
        return True
    span = bridge_span(mesh, faces)
    return span is not None and span <= BRIDGE_SPAN


def where(mesh, faces):
    c = mesh.triangles_center[faces].mean(axis=0)
    return f"({c[0]:+.1f}, {c[1]:+.1f}, z {c[2]:.1f})"


def analyse(name, mesh, settings):
    mesh = mesh.copy()
    for axis, deg in enumerate(settings.get("print_rotate", [0, 0, 0])):
        if deg:
            mesh.apply_transform(trimesh.transformations.rotation_matrix(np.radians(deg), np.eye(3)[axis]))
    mesh.apply_translation([0, 0, -mesh.bounds[0][2]])     # on the bed
    n = mesh.face_normals
    tri_z = mesh.triangles[:, :, 2]
    bed = (n[:, 2] < -0.99) & (tri_z.max(axis=1) < BED_Z)
    over = (n[:, 2] < -np.cos(np.radians(OVERHANG_DEG))) & ~bed

    c = mesh.triangles_center
    loc, ray, tri = mesh.ray.intersects_location(c - n * 1e-3, -n, multiple_hits=False)
    thick = np.full(len(c), np.inf)
    opposite = (mesh.face_normals[tri] * n[ray]).sum(axis=1) < -0.5   # a facing wall, not a corner
    thick[ray[opposite]] = np.linalg.norm(loc[opposite] - c[ray[opposite]], axis=1)
    thin = thick < MIN_WALL - 0.01

    supports = settings.get("supports")
    if supports is None:
        say("WARN", f"{name}: no `supports` for it in `parts` in cad.yaml -- add it from the print guide")
        supports = True
    found = [g for g in regions(mesh, over) if mesh.area_faces[g].sum() >= MIN_REGION]
    ok = [prints_unsupported(mesh, g) for g in found]
    ledges = [g for g, fine in zip(found, ok) if fine]
    big = [g for g, fine in zip(found, ok) if not fine]
    for g in ledges:
        over[g] = False                      # drawn plain: prints without support
    area = sum(mesh.area_faces[g].sum() for g in big)
    note = f" ({len(ledges)} ledge/bridge region(s) left out)" if ledges else ""
    if supports:
        say("info", f"{name}: {area:.0f} mm2 of overhang needs support, {len(big)} region(s){note}")
    elif big:
        for g in big[:5]:
            say("WARN", f"{name}: prints without supports but has a {mesh.area_faces[g].sum():.0f} mm2 "
                        f"overhang, {width(mesh, g):.1f} mm wide, at {where(mesh, g)}")
    else:
        say("ok", f"{name}: no overhang that needs support{note}")

    thin_regions = [g for g in regions(mesh, thin) if mesh.area_faces[g].sum() >= 0.5]
    if thin_regions:
        for g in thin_regions[:5]:
            say("WARN", f"{name}: wall {thick[g].min():.2f} mm thin over {mesh.area_faces[g].sum():.1f} mm2 "
                        f"at {where(mesh, g)} (want >= {MIN_WALL})")
        if len(thin_regions) > 5:
            say("WARN", f"{name}: ... {len(thin_regions) - 5} more thin region(s)")
    else:
        say("ok", f"{name}: no wall under {MIN_WALL} mm")
    finite = thick[np.isfinite(thick)]
    say("info", f"{name}: bed contact {mesh.area_faces[bed].sum():.0f} mm2, "
                f"typical wall {np.median(finite):.2f} mm" if len(finite) else f"{name}: no wall readings")

    colour = np.tile(COLOURS["plain"], (len(c), 1))
    colour[bed] = COLOURS["bed"]
    colour[over] = COLOURS["over"]
    colour[thin] = COLOURS["thin"]
    return mesh, colour.astype(np.uint8)


def coloured_actor(mesh, colour):
    pts = vtk.vtkPoints()
    pts.SetData(numpy_to_vtk(np.ascontiguousarray(mesh.vertices), deep=True))
    polys = vtk.vtkCellArray()
    polys.SetData(numpy_to_vtkIdTypeArray(np.arange(0, 3 * len(mesh.faces) + 1, 3, dtype=np.int64), deep=True),
                  numpy_to_vtkIdTypeArray(mesh.faces.astype(np.int64).ravel(), deep=True))
    poly = vtk.vtkPolyData()
    poly.SetPoints(pts)
    poly.SetPolys(polys)
    rgb = numpy_to_vtk(colour, deep=True)
    rgb.SetName("rgb")
    poly.GetCellData().SetScalars(rgb)
    m = vtk.vtkPolyDataMapper()
    m.SetInputData(poly)
    m.SetScalarModeToUseCellData()
    m.SetColorModeToDirectScalars()
    a = vtk.vtkActor()
    a.SetMapper(m)
    a.GetProperty().SetAmbient(0.15)
    return a


def main(stl_dir, out_dir):
    os.makedirs(out_dir, exist_ok=True)
    spec = RV.spec_parts()
    tiles = []
    for path in sorted(glob.glob(os.path.join(stl_dir, "*.stl"))):
        name = os.path.splitext(os.path.basename(path))[0]
        mesh, colour = analyse(name, trimesh.load(path), spec.get(name, {}))
        actor = coloured_actor(mesh, colour)
        centre = (mesh.bounds[0] + mesh.bounds[1]) / 2
        scale = 0.6 * max(mesh.extents)
        # from below, and from a low angle -- per part `inspect_from` in cad.yaml, e.g.
        # the open side of a shell half, so the roofs inside it show
        low = tuple(spec.get(name, {}).get("inspect_from", (0.6, 1.0, -0.6)))
        for label, d, up in (("below", (0, 0, -1), (0, 1, 0)), ("low 3/4", low, (0, 0, 1))):
            tiles.append((f"{name} {label}", RV.render([actor], centre, d, up, scale)))

    cols = 4
    rows = (len(tiles) + cols - 1) // cols
    head = 36
    sheet = Image.new("RGB", (TILE * cols, TILE * rows + head), "white")
    draw = ImageDraw.Draw(sheet)
    font = ImageFont.load_default(size=18)
    for i, (label, img) in enumerate(tiles):
        x, y = (i % cols) * TILE, (i // cols) * TILE + head
        sheet.paste(img.resize((TILE, TILE)), (x, y))
        draw.text((x + 8, y + 6), label, fill=(0, 0, 0), font=font)
    draw.text((8, 8), f"print pose (per `parts` in cad.yaml, on the bed). red = overhang > {OVERHANG_DEG:.0f} deg "
                      f"from vertical (ledges <= {LEDGE_W} mm and bridges <= {BRIDGE_SPAN:.0f} mm left out), "
                      f"blue = wall < {MIN_WALL} mm, green = bed contact",
              fill=(0, 0, 0), font=font)
    path = os.path.join(out_dir, "print_check.png")
    sheet.save(path)
    print(f"\nwrote {path}")
    print("PRINT CHECK OK" if not WARNS else f"{len(WARNS)} PRINT ISSUE(S)")
    return 0 if not WARNS else 1


if __name__ == "__main__":
    stl_dir = sys.argv[1] if len(sys.argv) > 1 else K.stl_dir()
    out_dir = K.check_out()
    sys.exit(main(stl_dir, out_dir))

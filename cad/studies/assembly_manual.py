"""
Pictures for the assembly manual of Cogley's Robot Head a2.0.33 (PLAN D14-D16): one image
per build step, drawn from his reference assembly in our frame (cogley_head.py).

Grey = already built, colour = added in the step, dark = screws. Heat-set inserts are
coloured by size: yellow M2, orange M3, red M4. A label's dot sits on an insert, screw or
part that faces the camera in that view.

His export leaves out the screws for the brows and the tongue, two brow servos and one
jaw horn. Those are drawn here: brow and tongue screws on the axes of the holes they go
through (holes found by slicing his parts), the missing parts mirrored from the other
side. Sizes follow the holes: M2 inserts in 3.2 holes, M3 in 4.3, M4 in 5.3; shoulder
screws through 4.3 (M3, 4 mm shoulder) and 5.2 (M4, 5 mm shoulder) holes.

Every M3 shoulder joint (lips, corners, tongue, brow arms, brow bar ends) ends in a part 4 mm
thick there (2.9 at the corner pieces): a round hole 1.0-1.4 mm deep, then a pocket shaped
for an M3 nut. The team's printed parts carry an M3 insert there instead of a nut (they were
set before 2026-10-25), so the pictures draw one in each, 2.8 mm long from the face the
moving part sits on.

The EyeMech steps use his EyeMech e3.1 assembly (modules.py -> output/ref/eyemech): the head
export lacks its lateral frame, two eye adaptors and a pivot holder. e3.1 lacks one central
pivot holder, mirrored here from the other.

Run:  python cad/studies/assembly_manual.py [inserts eyes mouth brows mount]
      (after cogley_head.py and modules.py)  -> output/manual/<step>.png
"""
import json
import os
import sys

import numpy as np
import trimesh
import vtk
from PIL import Image, ImageDraw, ImageFont
from vtkmodules.util.numpy_support import vtk_to_numpy

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import cadkit as K  # noqa: E402
import cogley_head as C  # noqa: E402
import render_views as RV  # noqa: E402

sys.stdout.reconfigure(encoding="utf-8")
OUT = os.path.join(K.PROJECT, "output", "manual")

GREY = (0.82, 0.82, 0.82)
DARK = (0.16, 0.16, 0.18)
SIZE_COLOUR = {"M2": (0.98, 0.85, 0.15), "M3": (0.98, 0.52, 0.08), "M4": (0.85, 0.12, 0.12)}
PALETTE = [(0.20, 0.45, 0.85), (0.90, 0.35, 0.20), (0.20, 0.65, 0.35), (0.80, 0.25, 0.60),
           (0.95, 0.65, 0.10), (0.15, 0.65, 0.75), (0.55, 0.35, 0.80), (0.60, 0.50, 0.25)]
W, H = 1000, 700

_PARTS = None
_SAMPLES = {}


# ---------------------------------------------------------------- parts and hardware

def parts():
    """{label 'Name#k': (group, mesh)} from his reference assembly in our frame."""
    global _PARTS
    if _PARTS is None:
        _PARTS = {f"{n}#{k}": (g, m) for n, k, g, m in C.load()}
    return _PARTS


def get(label):
    return parts()[label][1]


def mx(mesh):
    """Mirrored across the midline (x -> -x): the far side of a part his export has once."""
    m = mesh.copy()
    m.apply_transform(np.diag([-1.0, 1.0, 1.0, 1.0]))
    m.invert()
    if "mouth" in mesh.metadata:
        m.metadata["mouth"] = mesh.metadata["mouth"] * [-1, 1, 1]
        m.metadata["axis"] = mesh.metadata["axis"] * [-1, 1, 1]
    return m


def screw_axis(mesh):
    """(head point, unit axis head -> tip) of a screw mesh."""
    v = mesh.vertices
    cen = v.mean(axis=0)
    _, _, vt = np.linalg.svd(v - cen, full_matrices=False)
    ax = vt[0]
    t = (v - cen) @ ax
    lo, hi = t.min(), t.max()
    r = np.linalg.norm((v - cen) - np.outer(t, ax), axis=1)
    if r[t > hi - 0.15 * (hi - lo)].max() > r[t < lo + 0.15 * (hi - lo)].max():
        ax, lo = -ax, -hi
    return cen + ax * lo, ax


def hw(*labels):
    """His screws, with the head point and axis kept for labels."""
    out = []
    for lab in labels:
        m = get(lab).copy()
        head, ax = screw_axis(m)
        m.metadata["mouth"], m.metadata["axis"] = head, ax
        out.append(m)
    return out


def cylinder(point, axis, dia, length):
    a = np.asarray(axis, float) / np.linalg.norm(axis)
    cyl = trimesh.creation.cylinder(radius=dia / 2, height=length, sections=28)
    cyl.apply_transform(trimesh.geometry.align_vectors([0, 0, 1.0], a))
    cyl.apply_translation(np.asarray(point, float) + a * length / 2)
    return cyl


def screw(head, axis, d, length, shoulder=None):
    """A socket-head screw drawn from its head face along `axis`; shoulder = (dia, length)."""
    a = np.asarray(axis, float) / np.linalg.norm(axis)
    head = np.asarray(head, float)
    hd = d * 1.75 if shoulder is None else shoulder[0] * 1.6
    pieces = [cylinder(head - a * d, a, hd, d)]
    if shoulder:
        pieces += [cylinder(head, a, shoulder[0], shoulder[1]), cylinder(head + a * shoulder[1], a, d, length)]
    else:
        pieces.append(cylinder(head, a, d, length))
    m = trimesh.util.concatenate(pieces)
    m.metadata["mouth"], m.metadata["axis"] = head - a * d, a
    return m


def m3_shoulder(head, axis):
    return screw(head, axis, 3.0, 4.0, shoulder=(4.0, 4.0))


def m4_shoulder(head, axis):
    return screw(head, axis, 4.0, 5.0, shoulder=(5.0, 5.0))


INSERT = {"M2": (3.6, 3.5, 1.6), "M3": (5.0, 4.5, 2.15), "M4": (6.0, 6.0, 2.65)}


def samples(label):
    if label not in _SAMPLES:
        m = get(label)
        _SAMPLES[label] = np.vstack([m.vertices, m.sample(60000)])
    return _SAMPLES[label]


def seat(label, point, axis, hole_r):
    """Distance along `axis` from `point` to where `label`'s hole of radius hole_r starts."""
    a = np.asarray(axis, float) / np.linalg.norm(axis)
    q = samples(label) - point
    t = q @ a
    r = np.linalg.norm(q - np.outer(t, a), axis=1)
    return float(t[(t > -1) & (t < 40) & (r < hole_r + 0.6)].min())


def insert(point, axis, size, length=None):
    od, ln, _ = INSERT[size]
    m = cylinder(point, axis, od, length or ln)
    m.metadata.update(mouth=np.asarray(point, float), axis=np.asarray(axis, float) / np.linalg.norm(axis),
                      size=size)
    return m


def insert_on_screw(screw_label, part, size):
    """The insert a screw of his threads into, seated where `part`'s hole starts on its axis."""
    head, ax = screw_axis(get(screw_label))
    return insert(head + ax * seat(part, head, ax, INSERT[size][2]), ax, size)


def insert_on_line(part, point, axis, size, mirrored=False):
    p, a = np.array(point, float), np.array(axis, float)
    if mirrored:
        p[0], a[0] = -p[0], -a[0]
    a /= np.linalg.norm(a)
    return insert(p + a * seat(part, p, a, INSERT[size][2]), a, size)


# ---------------------------------------------------------------- rendering

def poly(mesh):
    pts = vtk.vtkPoints()
    for p in mesh.vertices:
        pts.InsertNextPoint(*p)
    cells = vtk.vtkCellArray()
    for f in mesh.faces:
        cells.InsertNextCell(3)
        for i in f:
            cells.InsertCellPoint(int(i))
    pd = vtk.vtkPolyData()
    pd.SetPoints(pts)
    pd.SetPolys(cells)
    return pd


def basis(direction, up):
    d = np.asarray(direction, float)
    d /= np.linalg.norm(d)
    u = np.asarray(up, float)
    u = u - d * (u @ d)
    u /= np.linalg.norm(u)
    return d, u, np.cross(-d, u)


def render(items, direction, up, focus, size, pad=1.12, probes=()):
    """items: [(mesh, rgb, opacity)]. -> (image, project(point) -> (x, y) pixels, visible flags
    for `probes`: True where nothing nearer the camera covers the point)."""
    d, u, right = basis(direction, up)
    pts = np.vstack([m.vertices for m in focus])
    c = (pts.max(axis=0) + pts.min(axis=0)) / 2
    x, y = (pts - c) @ right, (pts - c) @ u
    c = c + right * (x.max() + x.min()) / 2 + u * (y.max() + y.min()) / 2
    half_h = max((y.max() - y.min()) / 2, (x.max() - x.min()) / 2 * size[1] / size[0]) * pad
    ren = vtk.vtkRenderer()
    ren.SetBackground(1, 1, 1)
    ren.UseFXAAOn()
    for m, rgb, op in items:
        pd = poly(m)
        a = RV.surface_actor(pd, rgb)
        a.GetProperty().SetOpacity(op)
        ren.AddActor(a)
        if op >= 1.0:
            ren.AddActor(RV.line_actor(RV.feature_edges(pd), (0.25, 0.25, 0.25), 1))
    vtk.vtkLightKit().AddLightsToRenderer(ren)
    cam = ren.GetActiveCamera()
    cam.SetFocalPoint(*c)
    cam.SetPosition(*(c + d * 1500))
    cam.SetViewUp(*u)
    cam.ParallelProjectionOn()
    cam.SetParallelScale(half_h)
    ren.ResetCameraClippingRange()
    win = vtk.vtkRenderWindow()
    win.SetOffScreenRendering(1)
    win.SetSize(*size)
    win.AddRenderer(ren)
    win.Render()
    grab = vtk.vtkWindowToImageFilter()
    grab.SetInput(win)
    grab.SetInputBufferTypeToRGB()
    grab.ReadFrontBufferOff()
    grab.Update()
    img = grab.GetOutput()
    w, h, _ = img.GetDimensions()
    arr = vtk_to_numpy(img.GetPointData().GetScalars()).reshape(h, w, 3)[::-1]
    zgrab = vtk.vtkWindowToImageFilter()
    zgrab.SetInput(win)
    zgrab.SetInputBufferTypeToZBuffer()
    zgrab.ReadFrontBufferOff()
    zgrab.Update()
    zb = vtk_to_numpy(zgrab.GetOutput().GetPointData().GetScalars()).reshape(h, w)
    near, far = cam.GetClippingRange()
    tol = 1.2 / (far - near)                   # 1.2 mm in depth units
    vis = []
    for p in probes:
        ren.SetWorldPoint(*p, 1.0)
        ren.WorldToDisplay()
        x, y, z = ren.GetDisplayPoint()
        xi, yi = int(round(x)), int(round(y))
        if not (2 <= xi < w - 2 and 2 <= yi < h - 2):
            vis.append(False)
            continue
        vis.append(z <= zb[yi - 1:yi + 2, xi - 1:xi + 2].max() + tol)
    win.Finalize()
    k = size[1] / 2 / half_h

    def project(p):
        q = np.asarray(p, float) - c
        return size[0] / 2 + (q @ right) * k, size[1] / 2 - (q @ u) * k

    return Image.fromarray(np.ascontiguousarray(arr)), project, vis


def font(sz):
    for name in ("segoeui.ttf", "arial.ttf"):
        try:
            return ImageFont.truetype(name, sz)
        except OSError:
            pass
    return ImageFont.load_default(size=sz)


def candidates(a, d):
    """Points a label could sit on, best first; the first one the camera can see is used.
    Hardware: the open end (insert mouth, screw head), facing the camera first. A part: points
    on its surface, nearest its middle (as seen) first. A list: its members in turn."""
    if isinstance(a, (list, tuple)) and len(a) and isinstance(a[0], trimesh.Trimesh):
        ms = sorted(a, key=lambda m: -((-(m.metadata["axis"] @ d) if "axis" in m.metadata else 0)
                                       + 0.004 * (m.centroid @ d)))
        return [p for m in ms for p in candidates(m, d)]
    if isinstance(a, trimesh.Trimesh):
        if "mouth" in a.metadata:
            ax = a.metadata["axis"]
            return [a.metadata["mouth"] - ax * 0.4, a.metadata["mouth"] + ax * 1.0]
        pts = np.vstack([a.sample(400, seed=1) if hasattr(a, "sample") else a.vertices])
        cen = a.centroid
        flat = (pts - cen) - np.outer((pts - cen) @ d, d)
        order = np.argsort(np.linalg.norm(flat, axis=1))
        return [pts[i] + d * 0.3 for i in order[:200]]
    return [np.asarray(a, float)]


def place(dr, f, labels, size, taken):
    """Boxes pushed out from the picture's middle along each anchor's direction, kept apart
    and off every label's dot."""
    out = []
    cx, cy = size[0] / 2, size[1] / 2
    taken = taken + [(x - 9, y - 9, x + 9, y + 9) for (x, y), _, _ in labels]
    for (ax, ay), text, off in labels:
        bb = dr.multiline_textbbox((0, 0), text, font=f)
        tw, th = bb[2] - bb[0], bb[3] - bb[1]
        if off is None:
            vx, vy = ax - cx, ay - cy
            n = np.hypot(vx, vy) or 1.0
            base = np.arctan2(vy / n, vx / n)
            tries = [(r, base + da) for r in (150, 210, 270, 330) for da in (0, 0.45, -0.45, 0.9, -0.9)]
        else:
            tries = [(np.hypot(*off), np.arctan2(off[1], off[0]))] + \
                    [(r, np.arctan2(off[1], off[0]) + da) for r in (150, 220, 290) for da in (0.5, -0.5, 1.0, -1.0)]
        for r, ang in tries:
            bx = min(max(ax + r * np.cos(ang) - tw / 2, 8), size[0] - tw - 16)
            by = min(max(ay + r * np.sin(ang) - th / 2, 8), size[1] - th - 52)
            box = (bx - 8, by - 6, bx + tw + 8, by + th + 10)
            if not any(box[0] < t[2] and box[2] > t[0] and box[1] < t[3] and box[3] > t[1] for t in taken):
                break
        taken.append(box)
        out.append(((ax, ay), (bx, by), box, text))
    return out


def callouts(img, project, labels):
    """labels: [(3D point, text, (dx, dy) or None)]."""
    dr = ImageDraw.Draw(img)
    f = font(25)
    pts = [(project(p), t, o) for p, t, o in labels]
    placed = place(dr, f, pts, img.size, [])
    for (ax, ay), _, box, _ in placed:
        cx, cy = (box[0] + box[2]) / 2, (box[1] + box[3]) / 2
        dr.line([(ax, ay), (cx, cy)], fill=(20, 20, 20), width=2)
    for (ax, ay), (bx, by), box, text in placed:
        dr.ellipse([ax - 5, ay - 5, ax + 5, ay + 5], fill=(255, 255, 255), outline=(20, 20, 20), width=3)
        dr.rectangle(box, fill=(255, 255, 255), outline=(20, 20, 20), width=2)
        dr.multiline_text((bx, by), text, fill=(10, 10, 10), font=f)


def arrow(img, project, p0, p1, colour=(215, 40, 40)):
    dr = ImageDraw.Draw(img)
    x0, y0 = project(p0)
    x1, y1 = project(p1)
    vec = np.array([x1 - x0, y1 - y0])
    n = np.linalg.norm(vec)
    if n < 1:
        return
    vec /= n
    w = np.array([-vec[1], vec[0]])
    tip = np.array([x1, y1])
    dr.line([(x0, y0), tuple(tip - vec * 20)], fill=colour, width=9)
    dr.polygon([tuple(tip), tuple(tip - vec * 34 + w * 18), tuple(tip - vec * 34 - w * 18)], fill=colour)


def step_image(name, title, views, built=(), new=(), hardware=(), inserts=(), labels=(), arrows=(),
               focus=None, colours=None, ghost=False, legend=True, size=(W, H), pad=1.12):
    """views: [(direction, up, caption)]. labels: [(view index or None for all, anchor, text, offset)].
    arrows: [(view index, p0, p1)]. New parts take the palette in order, or `colours`."""
    items = [(m, GREY, 0.28 if ghost else 1.0) for m in built]
    for i, m in enumerate(new):
        items.append((m, colours[i] if colours else PALETTE[i % len(PALETTE)], 1.0))
    items += [(m, DARK, 1.0) for m in hardware]
    items += [(m, SIZE_COLOUR[m.metadata["size"]], 1.0) for m in inserts]
    fm = focus if focus is not None else (list(new) + list(hardware) + list(inserts))
    tiles = []
    for vi, view in enumerate(views):
        dvec, up, cap = view[:3]
        only = view[3] if len(view) > 3 else None      # this view draws only these meshes
        its = items if only is None else [it for it in items if any(it[0] is k for k in only)]
        d = basis(dvec, up)[0]
        mine = [(candidates(a, d), t, o) for lvi, a, t, o in labels if lvi is None or lvi == vi]
        probes = [p for cand, _, _ in mine for p in cand]
        img, pr, vis = render(its, dvec, up, fm if only is None else only, size, pad=pad, probes=probes)
        for avi, p0, p1 in arrows:
            if avi == vi:
                arrow(img, pr, p0, p1)
        chosen, k = [], 0
        for cand, t, o in mine:
            seen = [p for p, ok in zip(cand, vis[k:k + len(cand)]) if ok]
            k += len(cand)
            if seen:
                chosen.append((seen[0], t, o))
            else:
                print(f"  {name} view {vi}: nothing visible for '{t.splitlines()[0]}', label left out")
        callouts(img, pr, chosen)
        if cap:
            ImageDraw.Draw(img).text((14, size[1] - 40), cap, fill=(110, 110, 110), font=font(24))
        tiles.append(img)
    # views stacked top to bottom, so the picture stays readable at a document's column width
    head = 52 + (40 if legend and inserts else 0)
    sheet = Image.new("RGB", (size[0], head + sum(t.height for t in tiles) + 6 * (len(tiles) - 1)), "white")
    dr = ImageDraw.Draw(sheet)
    y = head
    for i, t in enumerate(tiles):
        if i:
            dr.line([(30, y - 3), (size[0] - 30, y - 3)], fill=(210, 210, 210), width=2)
        sheet.paste(t, (0, y))
        y += t.height + 6
    dr.text((14, 10), title, fill=(0, 0, 0), font=font(30))
    if legend and inserts:
        f = font(24)
        x = 16
        for s in ("M2", "M3", "M4"):
            if any(m.metadata["size"] == s for m in inserts):
                dr.rectangle([x, 58, x + 26, 84], fill=tuple(int(255 * c) for c in SIZE_COLOUR[s]), outline=(0, 0, 0))
                dr.text((x + 34, 55), f"{s} insert", fill=(0, 0, 0), font=f)
                x += 170
    os.makedirs(OUT, exist_ok=True)
    path = os.path.join(OUT, f"{name}.png")
    sheet.save(path)
    print("wrote", os.path.relpath(path, K.PROJECT))
    return path


FRONT = ((0, 1, 0), (0, 0, 1))
BACK = ((0, -1, 0), (0, 0, 1))
SIDE_L = ((-1, 0, 0), (0, 0, 1))       # looking at the head's left side (x < 0)
SIDE_R = ((1, 0, 0), (0, 0, 1))
BELOW = ((0, 0.35, -1), (0, 1, 0))
Q_FL = ((-0.8, 1.0, 0.45), (0, 0, 1))   # 3/4 from the front, head's left
Q_FR = ((0.8, 1.0, 0.45), (0, 0, 1))
Q_BL = ((-0.8, -1.0, 0.5), (0, 0, 1))
Q_BR = ((0.8, -1.0, 0.5), (0, 0, 1))
Q_FL_LOW = ((-0.8, 1.0, -0.35), (0, 0, 1))
Q_FR_LOW = ((0.8, 1.0, -0.35), (0, 0, 1))


def v(view, cap="", only=None):
    return (view[0], view[1], cap) if only is None else (view[0], view[1], cap, only)


def P(*labels):
    return [get(l) for l in labels]


# ---------------------------------------------------------------- what goes where

M2_6 = "Hex socket head cap screw M2x0.40 x 6"
M2_8 = "Hex socket head cap screw M2x0.40 x 8"
M25 = "Hex socket head cap screw M2.5x0.45 x 8"
M3_6 = "Hex socket head cap screw M3x0.50 x 6"
M3_8 = "Hex socket head cap screw M3x0.50 x 8"
M4_6 = "Hex socket head cap screw M4x0.70 x 6"
M4_8 = "Hex socket head cap screw M4x0.70 x 8"
M4_16 = "Hex socket head cap screw M4x0.70 x 16"
M3S = "M3 Shoulder"
M4S = "M4 Shoulder SSHE-M4-5-5-A2"

# mouth servos by board socket (MouthMaster.py), his MG90S instance -> socket
MOUTH_SERVO = {"MG90s_servo_FIX v1(Mirror)#9": "GP6 LUL  upper lip, head's left",
               "MG90s_servo_FIX v1(Mirror)#3": "GP7 LUR  upper lip, head's right",
               "MG90s_servo_FIX v1(Mirror)#2": "GP8 LLL  lower lip, head's left",
               "MG90s_servo_FIX v1(Mirror)#7": "GP9 LLR  lower lip, head's right",
               "MG90s_servo_FIX v1(Mirror)#4": "GP10 CUL  corner upper, head's left",
               "MG90s_servo_FIX v1(Mirror)#8": "GP11 CUR  corner upper, head's right",
               "MG90s_servo_FIX v1(Mirror)#5": "GP12 CLL  corner lower, head's left",
               "MG90s_servo_FIX v1(Mirror)#6": "GP13 CLR  corner lower, head's right",
               "MG90s_servo_FIX v1(Mirror)#10": "GP14 TON  tongue",
               "Component2#1": "GP4 JL  jaw, head's left (MG996R)",
               "Component2#0": "GP5 JR  jaw, head's right (MG996R)"}


def inserts_top():
    tb = "TopBase#0"
    return {"frame": [insert_on_screw(f"{M4_16}#{i}", tb, "M4") for i in range(6)],
            "cheek": [insert_on_screw(f"{M4_6}#{i}", tb, "M4") for i in range(2)],
            "pivot": [insert_on_screw(f"{M4S}#{i}", tb, "M4") for i in (1, 2)],
            "jaw": [insert_on_screw(f"{M3_6}#{i}", tb, "M3") for i in range(8)],
            "tabs": [insert_on_screw(f"{M2_6}#{i}", tb, "M2") for i in (2, 9, 7, 10, 11, 4, 18, 20)]
            + [insert_on_screw(f"{M2_8}#{i}", tb, "M2") for i in (0, 1)]}


def inserts_jaw():
    jb = "JawBase#0"
    return {"arms": [insert_on_screw(f"{M4_8}#{i}", jb, "M4") for i in range(4)],
            "pivot": [insert_on_screw(f"{M4S}#{i}", jb, "M4") for i in (0, 3)],
            "tongue": [insert_on_line(jb, (10, -6.3, 120.0), (-1, 0, 0), "M4")],
            "tabs": [insert_on_screw(f"{M2_6}#{i}", jb, "M2") for i in (15, 21, 16, 17, 1, 8)]}


BROW_FRAME = [((80, -60.5, z), (-1, 0, 0)) for z in (250.8, 261.9, 272.9)]
BROW_IDLER = [((70, -44.8, 278.2), (-1, 0, 0)), ((5, -9.8, 278.1), (1, 0, 0))]
BROW_TABS = [((20, -9.8, z), (1, 0, 0)) for z in (242.9, 270.9)] + [((62, -44.8, z), (-1, 0, 0)) for z in (242.9, 270.9)]


def inserts_brow():
    bb = "Part 4#0"
    both = lambda lines, size: ([insert_on_line(bb, p, a, size) for p, a in lines]
                                + [insert_on_line(bb, p, a, size, mirrored=True) for p, a in lines])
    return {"frame": both(BROW_FRAME, "M4"), "idler": both(BROW_IDLER, "M4"), "tabs": both(BROW_TABS, "M2")}


def tongue_screws():
    """Horn screw, the two M3 shoulder joints and the M4 pivot of the tongue (none in his export)."""
    return [screw((15.8, -54.3, 119.2), (-1, 0, 0), 2.5, 8.0),
            m3_shoulder((15.8, -64.4, 132.5), (-1, 0, 0)),
            m3_shoulder((-1.2, -16.4, 133.6), (-1, 0, 0)),
            m4_shoulder((-4.4, -6.3, 120.0), (-1, 0, 0))]


# his M3 shoulder screws in the mouth -> the part each one threads into
MOUTH_JOINTS = {0: "UpperLeftLip#0", 2: "UpperLeftLip#0", 5: "Part 34#0", 8: "Part 34#0",
                1: "LowerLeftLip#0", 13: "LowerLeftLip#0", 4: "Part 37#0", 12: "Part 37#0",
                3: "Part 30#0", 9: "Part 30#0", 6: "Part 29#0", 7: "Part 41#0", 10: "Part 41#0", 11: "Part 40#0"}
MOUTH_GROUP = {"UpperLeftLip#0": "upper_lip", "Part 34#0": "upper_lip", "LowerLeftLip#0": "lower_lip",
               "Part 37#0": "lower_lip", "Part 30#0": "corners", "Part 29#0": "corners", "Part 41#0": "corners",
               "Part 40#0": "corners"}
ARM_JOINTS = ["Part 8#0", "Part 8#0", "Part 9#0", "Part 9#0", "Part 12#0", "Part 12#0", "Part 13#0", "Part 13#0"]
BAR_JOINTS = ["Part 8#0", "Part 9#0", "Part 12#0", "Part 13#0"]
LINK_INSERT_L = 2.8


def link_insert(head, axis, part):
    """The M3 insert a linkage's shoulder screw threads into, from the face of `part` it meets."""
    a = np.asarray(axis, float) / np.linalg.norm(axis)
    face = np.asarray(head, float) + a * seat(part, head, a, 1.8)
    return insert(face + a * LINK_INSERT_L, -a, "M3", LINK_INSERT_L)


def inserts_link():
    """[(group, part label, insert)] for all 28 M3 shoulder joints."""
    out = []
    for i, part in MOUTH_JOINTS.items():
        out.append((MOUTH_GROUP[part], part, link_insert(*screw_axis(get(f"{M3S}#{i}")), part)))
    for s, part in zip(tongue_screws()[1:3], ("Part 21#0", "Part 19#0")):
        out.append(("tongue", part, link_insert(s.metadata["mouth"], s.metadata["axis"], part)))
    b = brow_parts()
    for group, screws, parts_ in (("brow_arms", b["arm_s"], ARM_JOINTS), ("brow_bars", b["bar_s"], BAR_JOINTS)):
        for s, part in zip(screws, parts_):
            out.append((group, part, link_insert(s.metadata["mouth"], s.metadata["axis"], part)))
    return out


def link_of(links, *groups):
    return [m for g, _, m in links if g in groups]


def steps_link_inserts():
    li = inserts_link()
    on = lambda *ps: [m for _, p, m in li if p in ps]
    left = ["UpperLeftLip#0", "LowerLeftLip#0", "Part 30#0", "Part 29#0"]
    right = ["Part 34#0", "Part 37#0", "Part 41#0", "Part 40#0", "Part 21#0", "Part 19#0"]
    pale = [(0.62, 0.74, 0.90), (0.60, 0.82, 0.62), (0.80, 0.72, 0.92), (0.88, 0.78, 0.58)]
    new = P(*left, *right)
    mL, mR = [get(p) for p in left], [get(p) for p in right]
    step_image("s1_06_linkage_mouth", "Step 1.6  Mouth linkage parts: 16 x M3, where the shoulder screws end",
               [v(((1, 0.3, 0.2), (0, 0, 1)), "head's left side, seen from the middle", mL + on(*left)),
                v(((-1, 0.3, 0.2), (0, 0, 1)), "head's right side and the tongue, seen from the middle",
                  mR + on(*right))],
               new=new, colours=pale * 2 + [pale[2], pale[1]], inserts=[m for _, p, m in li if p in left + right],
               labels=[(0, get("UpperLeftLip#0"), "upper lip plate: 2", None),
                       (0, get("LowerLeftLip#0"), "lower lip plate: 2", None),
                       (0, get("Part 30#0"), "corner link: 2", None), (0, get("Part 29#0"), "corner piece: 1", None),
                       (1, get("Part 34#0"), "upper lip plate: 2", None), (1, get("Part 37#0"), "lower lip plate: 2", None),
                       (1, get("Part 41#0"), "corner link: 2", None), (1, get("Part 40#0"), "corner piece: 1", None),
                       (1, get("Part 21#0"), "tongue arm: 1", None), (1, get("Part 19#0"), "tongue link: 1", None)])
    # the head's right arms only: his print file's left arms are their mirror images (his
    # assembly's left arms are an older version without the nut pocket)
    inner, outer = get("Part 8#0"), get("Part 9#0")
    ii, oi = on("Part 8#0"), on("Part 9#0")
    step_image("s1_06_linkage_brows", "Step 1.6  Brow arms: 3 x M3 in each of the 4, 12 in all",
               [v(((0.6, -1.0, 0.3), (0, 0, 1)), "inner arm, head's right; the left one is its mirror image",
                  [inner] + ii),
                v(((-1, -0.4, 0.35), (0, 0, 1)), "outer arm, head's right; the left one is its mirror image",
                  [outer] + oi)],
               new=[inner, outer], colours=[pale[0], pale[1]], inserts=ii + oi,
               labels=[(0, inner, "inner brow arm", None), (0, ii[:2], "from the horn arm\nand the idler", None),
                       (0, ii[2:], "from the brow bar", None),
                       (1, outer, "outer brow arm", None), (1, oi[:2], "from the horn arm\nand the idler", None),
                       (1, oi[2:], "from the brow bar", None)])


def steps_inserts():
    steps_link_inserts()
    t = inserts_top()
    step_image("s1_01_top_plate", "Step 1.1  Mouth top plate (TopBase): 10 x M4, 8 x M3, 10 x M2",
               [v(Q_FL, "front, head's left"), v(Q_BR, "back, head's right")],
               new=[get("TopBase#0")], colours=[(0.62, 0.74, 0.90)], inserts=sum(t.values(), []),
               labels=[(None, t["frame"], "M4: frame screws\n3 per side", None),
                       (0, t["cheek"], "M4: cheek bone\n2 at the front", None),
                       (0, t["pivot"], "M4: upper-lip pivot\n1 per side", None),
                       (None, t["jaw"], "M3: jaw servo\n4 per side", None),
                       (None, t["tabs"], "M2: servo tabs\n5 per side", None)])
    j = inserts_jaw()
    step_image("s1_02_jaw_base", "Step 1.2  Jaw base: 7 x M4, 6 x M2",
               [v(Q_FL, "front, head's left"), v(Q_BR, "back, head's right")],
               new=[get("JawBase#0")], colours=[(0.60, 0.82, 0.62)], inserts=sum(j.values(), []),
               labels=[(None, j["arms"], "M4: jaw arms\n2 per side", None),
                       (0, j["pivot"], "M4: lower-lip pivot\n1 per side", None),
                       (1, j["pivot"], "M4: lower-lip pivot", None),
                       (None, j["tongue"], "M4: tongue pivot\n(1, inner wall)", None),
                       (None, j["tabs"], "M2: servo tabs\n2 per servo, 3 servos", None)])
    cb = [insert_on_screw(f"{M3_8}#{i}", "CheekBone#0", "M3") for i in (1, 2, 4, 7)]
    eb = [insert_on_screw(f"{M3_8}#{i}", "SnapEyemech v20#1", "M3") for i in (0, 3, 5, 6)]
    step_image("s1_03_cheek_bone", "Step 1.3  Cheek bone: 4 x M3, 2 in each end",
               [v(Q_FL, "front, head's left"), v(Q_FR, "front, head's right")],
               new=[get("CheekBone#0")], colours=[(0.88, 0.78, 0.58)], inserts=cb,
               labels=[(None, cb, "M3: 2 per end,\nfrom the outside", None)])
    step_image("s1_04_eye_base", "Step 1.4  EyeMech base plate: 4 x M3, the front 2 holes in each end",
               [v(Q_FL, "front, head's left"), v(Q_FR, "front, head's right")],
               new=[get("SnapEyemech v20#1")], colours=[(0.62, 0.74, 0.90)], inserts=eb,
               labels=[(None, eb, "M3: front 2 of the 3\nholes in each end", None)])
    b = inserts_brow()
    step_image("s1_05_brow_body", "Step 1.5  Brow body: 10 x M4, 8 x M2",
               [v(Q_FR, "front, head's right"), v(Q_BL, "back, head's left")],
               new=[get("Part 4#0")], colours=[(0.92, 0.66, 0.60)], inserts=sum(b.values(), []),
               labels=[(None, b["frame"], "M4: frame screws\n3 per end", None),
                       (0, b["idler"][:1] + b["idler"][2:3], "M4: outer idler pivot\n1 per end", None),
                       (0, b["idler"][1:2] + b["idler"][3:], "M4: inner idler pivot\n(faces the middle)", None),
                       (None, b["tabs"], "M2: servo tabs\n2 per servo, 4 servos", None)])


# ---------------------------------------------------------------- mouth

def mouth_steps():
    S = lambda i: get(f"MG90s_servo_FIX v1(Mirror)#{i}")
    tb, jb = get("TopBase#0"), get("JawBase#0")
    t, j = inserts_top(), inserts_jaw()
    li = inserts_link()
    built = [tb]
    mg = P("Component2#1", "Component2#0")
    s = hw(*[f"{M3_6}#{i}" for i in range(8)])
    step_image("s3_01_jaw_servos", "Step 3.1  Jaw servos: 2 x MG996R onto the top plate, 4 x M3x6 each",
               [v(Q_FL, "head's left"), v(Q_FR, "head's right")], built=built, new=mg, hardware=s,
               labels=[(0, mg[0], "MG996R, shaft\npointing out", None), (1, mg[1], "MG996R, shaft\npointing out", None),
                       (None, s, "M3 x 6 into the\nM3 inserts", None)])
    built += mg
    ul = [S(9), S(3)]
    s = hw(*[f"{M2_6}#{i}" for i in (7, 10, 2, 9)])
    step_image("s3_02_upper_lip_servos", "Step 3.2  Upper-lip servos: 2 x MG90S at the front, 2 x M2x6 each",
               [v(Q_FL_LOW, "from below, head's left"), v(Q_FR_LOW, "from below, head's right")],
               built=built, new=ul, hardware=s, focus=ul + s, pad=2.0,
               labels=[(0, ul[0], "upper lip, head's left\n(GP6)", None), (1, ul[1], "upper lip, head's right\n(GP7)", None),
                       (None, s, "M2 x 6", None)])
    built += ul
    cs = [S(4), S(5), S(8), S(6)]
    s = hw(f"{M2_6}#11", f"{M2_6}#4", f"{M2_6}#18", f"{M2_6}#20", f"{M2_8}#0", f"{M2_8}#1")
    step_image("s3_03_corner_servos",
               "Step 3.3  Corner servos: 2 x MG90S per side, stacked; one M2x8 goes through both",
               [v(SIDE_L, "head's left side"), v(SIDE_R, "head's right side")], built=built, new=cs, hardware=s,
               focus=[tb] + cs, colours=[PALETTE[0], PALETTE[1], PALETTE[0], PALETTE[1]],
               labels=[(0, cs[0], "corner UPPER (GP10)", None), (0, cs[1], "corner LOWER (GP12)", None),
                       (1, cs[2], "corner UPPER (GP11)", None), (1, cs[3], "corner LOWER (GP13)", None),
                       (0, hw(f"{M2_8}#0"), "M2 x 8 through\nboth servo tabs", None),
                       (1, hw(f"{M2_8}#1"), "M2 x 8 through\nboth servo tabs", None),
                       (None, hw(f"{M2_6}#11", f"{M2_6}#18"), "M2 x 6", None),
                       (None, hw(f"{M2_6}#4", f"{M2_6}#20"), "M2 x 6", None)])
    built += cs
    teeth_u = P("Part 1#1", "Part 1#2")
    step_image("s3_04_upper_teeth", "Step 3.4  Upper teeth: dry-fit both pieces under the top plate",
               [v(FRONT, "front"), v(SIDE_L, "head's left side")], built=built, new=teeth_u,
               colours=[(0.96, 0.96, 0.90), (0.85, 0.55, 0.55)], focus=[tb] + teeth_u,
               labels=[(None, teeth_u[0], "teeth", None), (None, teeth_u[1], "gum / back piece", None)])
    built += teeth_u
    lipL = P("ULLLinkA#0", "ULLLinkB#0", "UpperLeftLip#0")
    lipR = P("Part 35#0", "Part 36#0", "Part 34#0")
    s = hw(f"{M25}#1", f"{M25}#0", f"{M4S}#2", f"{M4S}#1", f"{M3S}#0", f"{M3S}#2", f"{M3S}#8", f"{M3S}#5")
    step_image("s3_05_upper_lip", "Step 3.5  Upper lip: horn arm, pivot link and lip plate, each side",
               [v(Q_FL, "head's left"), v(Q_FR, "head's right")], built=built, new=lipL + lipR, hardware=s,
               inserts=link_of(li, "upper_lip"),
               colours=[PALETTE[0], PALETTE[2], PALETTE[1]] * 2, focus=lipL + lipR + [tb],
               labels=[(0, lipL[0], "horn arm on the servo\nM2.5 x 8", None), (1, lipR[0], "horn arm on the servo\nM2.5 x 8", None),
                       (0, lipL[1], "pivot link\nM4 shoulder", None), (1, lipR[1], "pivot link\nM4 shoulder", None),
                       (0, lipL[2], "upper lip plate\n2 x M3 shoulder into\nits M3 inserts", None),
                       (1, lipR[2], "upper lip plate\n2 x M3 shoulder into\nits M3 inserts", None)])
    built += lipL + lipR
    cL = P("Part 31#0", "Part 32#0", "Part 30#0", "Part 29#0")
    cR = P("Part 42#0", "Part 43#0", "Part 41#0", "Part 40#0")
    s = hw(f"{M25}#6", f"{M25}#5", f"{M25}#2", f"{M25}#7", *[f"{M3S}#{i}" for i in (9, 6, 3, 7, 11, 10)])
    step_image("s3_06_corners", "Step 3.6  Mouth corners: 2 horn arms, a link and the corner piece, each side",
               [v(SIDE_L, "head's left side"), v(SIDE_R, "head's right side")], built=built,
               new=cL + cR, hardware=s, colours=[PALETTE[0], PALETTE[1], PALETTE[2], PALETTE[3]] * 2,
               inserts=link_of(li, "corners"), focus=cL + cR + [tb],
               labels=[(0, cL[0], "upper horn arm\nM2.5 x 8", None), (0, cL[1], "lower horn arm\nM2.5 x 8", None),
                       (0, cL[2], "link", None), (0, cL[3], "corner piece", None),
                       (1, cR[0], "upper horn arm", None), (1, cR[1], "lower horn arm", None),
                       (1, cR[2], "link", None), (1, cR[3], "corner piece", None),
                       (0, hw(f"{M3S}#3"), "3 x M3 shoulder per side,\ninto the M3 inserts", None)])
    built += cL + cR
    # jaw base on its own
    js = [S(2), S(7), S(10)]
    s = hw(*[f"{M2_6}#{i}" for i in (15, 21, 16, 17, 1, 8)])
    step_image("s3_07_jaw_base_servos", "Step 3.7  Jaw base: 3 x MG90S (2 lower lip, 1 tongue), 2 x M2x6 each",
               [v(Q_FL, "front, head's left"), v(Q_BR, "back, head's right")], built=[jb], new=js, hardware=s,
               focus=[jb] + js,
               labels=[(None, js[0], "lower lip, head's left\n(GP8)", None),
                       (None, js[1], "lower lip, head's right\n(GP9)", None),
                       (None, js[2], "tongue (GP14)", None)])
    jbuilt = [jb] + js
    teeth_l = P("Part 1#3", "Part 1#0")
    step_image("s3_08_lower_teeth", "Step 3.8  Lower teeth: dry-fit both pieces on the jaw base",
               [v(FRONT, "front"), v(Q_FL, "head's left")], built=jbuilt, new=teeth_l,
               colours=[(0.96, 0.96, 0.90), (0.85, 0.55, 0.55)], focus=[jb] + teeth_l,
               labels=[(None, teeth_l[0], "teeth", None), (None, teeth_l[1], "gum / back piece", None)])
    jbuilt += teeth_l
    llL = P("Part 27#0", "Part 28#0", "LowerLeftLip#0")
    llR = P("Part 38#0", "Part 39#0", "Part 37#0")
    s = hw(f"{M25}#4", f"{M25}#3", f"{M4S}#0", f"{M4S}#3", *[f"{M3S}#{i}" for i in (13, 1, 12, 4)])
    step_image("s3_09_lower_lip", "Step 3.9  Lower lip: horn arm, pivot link and lip plate, each side",
               [v(Q_FL, "head's left"), v(Q_FR, "head's right")], built=jbuilt, new=llL + llR, hardware=s,
               inserts=link_of(li, "lower_lip"),
               colours=[PALETTE[0], PALETTE[2], PALETTE[1]] * 2, focus=llL + llR + [jb],
               labels=[(0, llL[0], "horn arm\nM2.5 x 8", None), (1, llR[0], "horn arm\nM2.5 x 8", None),
                       (0, llL[1], "pivot link\nM4 shoulder", None), (1, llR[1], "pivot link\nM4 shoulder", None),
                       (0, llL[2], "lower lip plate\n2 x M3 shoulder into\nits M3 inserts", None),
                       (1, llR[2], "lower lip plate\n2 x M3 shoulder into\nits M3 inserts", None)])
    jbuilt += llL + llR
    tg = P("Part 20#0", "Part 21#0", "Part 19#0")
    ts = tongue_screws()
    step_image("s3_10_tongue", "Step 3.10  Tongue: horn arm, tongue arm and link (tongue glued on the front later)",
               [v(SIDE_R, "head's right side"), v(Q_FR, "front, head's right")], built=jbuilt, new=tg, hardware=ts,
               inserts=link_of(li, "tongue"), focus=tg + [jb],
               labels=[(None, tg[0], "horn arm on the\ntongue servo, M2.5 x 8", None),
                       (None, tg[1], "tongue arm", None), (0, tg[2], "link (inside)", None),
                       (0, ts[1], "M3 shoulder into the\ntongue arm's insert", None),
                       (1, ts[3], "M4 shoulder into\nthe tongue-pivot insert", None)])
    jbuilt += tg
    arms = P("JawLink#0", "Part 33#0")
    horns = [get("Component1#0"), mx(get("Component1#0"))]
    s = hw(*[f"{M2_6}#{i}" for i in (5, 6, 12, 13, 0, 3, 14, 19)]) + hw(*[f"{M4_8}#{i}" for i in range(4)])
    step_image("s3_11_jaw", "Step 3.11  Jaw: horn discs on the MG996R, jaw arms to the discs and the jaw base",
               [v(SIDE_L, "head's left side"), v(Q_FR, "head's right")], built=built + jbuilt,
               new=arms + horns, hardware=s, colours=[PALETTE[0], PALETTE[0], PALETTE[4], PALETTE[4]],
               focus=built + jbuilt,
               labels=[(None, horns, "round horn disc\n(mouth closed, servo centred)", None),
                       (None, arms, "jaw arm", None),
                       (None, hw(f"{M2_6}#5", f"{M2_6}#0"), "4 x M2 x 6 into\nthe horn disc", None),
                       (None, hw(f"{M4_8}#2", f"{M4_8}#0"), "2 x M4 x 8 into\nthe jaw base", None)])
    allm = built + jbuilt + arms + horns
    return allm


def mouth_overview(allm):
    servos = {k: get(k) for k in MOUTH_SERVO}
    others = [m for m in allm if not any(m is s for s in servos.values())]
    names = list(servos)
    cols = [PALETTE[i % len(PALETTE)] for i in range(len(names))]
    side = lambda k: 0 if "head's left" in MOUTH_SERVO[k] else 1 if "head's right" in MOUTH_SERVO[k] else 2
    step_image("s3_12_mouth_servo_map", "Step 3.12  The finished mouth: which servo plugs into which socket",
               [v(Q_FL, "head's left side servos"), v(Q_FR, "head's right side servos"),
                v(BELOW, "from below: the tongue servo")],
               built=others, new=list(servos.values()), colours=cols, focus=allm,
               labels=[(side(k), servos[k], MOUTH_SERVO[k], None) for k in names])


# ---------------------------------------------------------------- brows

def brow_parts():
    """Both brows complete: his right-hand servos mirrored to the left, screws drawn on the hole axes."""
    S0, S1 = get("MG90s_servo_FIX v1(Mirror)#0"), get("MG90s_servo_FIX v1(Mirror)#1")
    servos = [S0, S1, mx(S0), mx(S1)]
    tabs = []
    # tab screws: inner servos from the shaft side outward, outer from outside inward
    for z in (242.9, 270.9):
        tabs += [screw((22.0, -9.8, z), (1, 0, 0), 2.0, 6.0), screw((54.0, -44.8, z), (-1, 0, 0), 2.0, 6.0)]
    tabs += [mx(m) for m in list(tabs)]
    horns = P("Part 3#2", "Part 3#3", "Part 3#0", "Part 3#1")
    horn_s = [screw((10.0, -9.8, 262.2), (1, 0, 0), 2.5, 8.0), screw((67.2, -45.0, 262.3), (-1, 0, 0), 2.5, 8.0)]
    horn_s += [mx(m) for m in list(horn_s)]
    idlers = P("Part 2#3", "Part 2#1", "Part 2#2", "Part 2#0")
    idl_s = [m4_shoulder((13.0, -9.8, 278.1), (1, 0, 0)), m4_shoulder((64.1, -44.8, 278.2), (-1, 0, 0))]
    idl_s += [mx(m) for m in list(idl_s)]
    arms = P("Part 8#0", "Part 9#0", "Part 12#0", "Part 13#0")
    arm_s = [m3_shoulder((10.0, 2.2, 261.8), (1, 0, 0)), m3_shoulder((13.0, 2.2, 277.8), (1, 0, 0)),
             m3_shoulder((67.2, -33.0, 262.8), (-1, 0, 0)), m3_shoulder((64.1, -33.3, 278.4), (-1, 0, 0)),
             m3_shoulder((-10.0, 0.6, 261.6), (-1, 0, 0)), m3_shoulder((-13.0, 0.6, 277.6), (-1, 0, 0)),
             m3_shoulder((-67.2, -33.0, 263.0), (1, 0, 0)), m3_shoulder((-64.1, -33.0, 279.0), (1, 0, 0))]
    bars = P("Part 11#0", "Part 14#0")
    bar_s = [m3_shoulder((23.8, 26.0, 249.0), (0, -1, 0)), m3_shoulder((70.5, -12.5, 236.8), (-1, 0, 0)),
             m3_shoulder((-24.5, 26.0, 249.1), (0, -1, 0)), m3_shoulder((-71.5, -13.0, 237.7), (1, 0, 0))]
    return dict(body=get("Part 4#0"), servos=servos, tabs=tabs, horns=horns, horn_s=horn_s, idlers=idlers,
                idl_s=idl_s, arms=arms, arm_s=arm_s, bars=bars, bar_s=bar_s)


def brow_steps():
    b = brow_parts()
    body = b["body"]
    built = [body]
    step_image("s4_01_brow_servos", "Step 4.1  Brow servos: 4 x MG90S into the brow body, 2 x M2x6 each",
               [v(Q_FR, "front, head's right"), v(Q_FL, "front, head's left")], built=built, new=b["servos"],
               hardware=b["tabs"], colours=[PALETTE[0], PALETTE[1], PALETTE[0], PALETTE[1]],
               labels=[(0, b["servos"][0], "inner servo\nshaft to the middle", None),
                       (0, b["servos"][1], "outer servo\nshaft to the outside", None),
                       (1, b["servos"][2], "inner (LI / RI)", None), (1, b["servos"][3], "outer (LO / RO)", None),
                       (0, b["tabs"][1], "M2 x 6", None)])
    built += b["servos"] + b["tabs"]
    step_image("s4_02_brow_horns_idlers",
               "Step 4.2  Horn arms on the 4 servos (M2.5x8), idler links on the body (M4 shoulder)",
               [v(Q_FR, "front, head's right"), v(Q_FL, "front, head's left")], built=built,
               new=b["horns"] + b["idlers"], hardware=b["horn_s"] + b["idl_s"],
               colours=[PALETTE[2]] * 4 + [PALETTE[5]] * 4, focus=[body] + b["horns"] + b["idlers"],
               labels=[(None, b["horns"][0:1] + b["horns"][2:3], "horn arm, inner\n(on the servo)", None),
                       (None, b["horns"][1:2] + b["horns"][3:4], "horn arm, outer", None),
                       (None, b["idlers"][0:1] + b["idlers"][2:3], "idler link, inner\nM4 shoulder", None),
                       (None, b["idlers"][1:2] + b["idlers"][3:4], "idler link, outer\nM4 shoulder", None)])
    built += b["horns"] + b["idlers"] + b["horn_s"] + b["idl_s"]
    li = inserts_link()
    step_image("s4_03_brow_arms", "Step 4.3  Brow arms: each to its horn arm and idler, 2 x M3 shoulder",
               [v(Q_FR, "front, head's right"), v(Q_FL, "front, head's left")], built=built,
               new=b["arms"], hardware=b["arm_s"], inserts=link_of(li, "brow_arms"),
               colours=[PALETTE[4], PALETTE[3]] * 2, focus=[body] + b["arms"],
               labels=[(None, b["arms"][0:1] + b["arms"][2:3], "inner brow arm", None),
                       (None, b["arms"][1:2] + b["arms"][3:4], "outer brow arm", None),
                       (0, b["arm_s"][2:4], "M3 shoulder into\nthe arm's insert", None)])
    built += b["arms"] + b["arm_s"]
    step_image("s4_04_brow_bars", "Step 4.4  TPU brow bars: one screw at each end",
               [v(Q_FR, "front, head's right"), v(FRONT, "front")], built=built, new=b["bars"],
               hardware=b["bar_s"], inserts=link_of(li, "brow_bars"), colours=[(0.10, 0.62, 0.70)] * 2,
               focus=[body] + b["bars"],
               labels=[(None, b["bars"], "brow bar (TPU)", None),
                       (0, b["bar_s"][0:1], "M3 shoulder into the\narm's insert (inner end)", None),
                       (0, b["bar_s"][1:2], "M3 shoulder into the\narm's insert (outer end)", None)])
    return built + b["bars"] + b["bar_s"]


# ---------------------------------------------------------------- into the frame

def mount_steps(mouth, brows):
    frame = get("SkullFrame#0")
    s = hw(*[f"{M4_16}#{i}" for i in range(6)])
    lo = np.array([0, 0, -70.0])
    step_image("s5_01_mouth_in", "Step 5.1  Lift the mouth up into the frame from below; 3 x M4x16 per side",
               [v(SIDE_L, "head's left side"), v(Q_FR, "front, head's right")], built=[frame], new=mouth,
               hardware=s, colours=[(0.55, 0.78, 0.58)] * len(mouth), focus=[frame] + mouth,
               arrows=[(0, (-80, -60, 95), (-80, -60, 140)), (1, (60, 10, 80), (60, 10, 125))],
               labels=[(0, s, "M4 x 16 through the frame\ninto the top plate", None)])
    cheek = get("CheekBone#0")
    s = hw(*[f"{M3_8}#{i}" for i in (1, 2, 4, 7)]) + hw(f"{M4_6}#0", f"{M4_6}#1")
    step_image("s5_02_cheek_bone", "Step 5.2  Cheek bone: slide in from the front; 2 x M3x8 per side, 2 x M4x6 at the front",
               [v(Q_FL, "front, head's left"), v(SIDE_R, "head's right side")], built=[frame] + mouth, new=[cheek],
               hardware=s, colours=[(0.90, 0.72, 0.40)], focus=[frame],
               arrows=[(0, (-45, 110, 205), (-45, 55, 200)), (1, (85, 60, 165), (85, 15, 180))],
               labels=[(None, s[:4], "M3 x 8 through the frame", None),
                       (0, s[4:], "M4 x 6 up into\nthe top plate", None)])
    eyes = [m for g, m in parts().values() if g == "eyes"]
    s = hw(*[f"{M3_8}#{i}" for i in (0, 3, 5, 6)])
    step_image("s5_03_eyes_in", "Step 5.3  EyeMech: lower it in from above the front onto the top plate; 2 x M3x8 per side",
               [v(Q_FL, "front, head's left"), v(SIDE_R, "head's right side")], built=[frame] + mouth + [cheek],
               new=eyes, hardware=s, colours=[(0.45, 0.62, 0.92)] * len(eyes), focus=[frame],
               arrows=[(0, (0, 60, 300), (0, 20, 245)), (1, (85, 50, 290), (85, 5, 240))],
               labels=[(None, s, "M3 x 8 through the frame\ninto the base plate inserts", None)])
    bs = [screw((50.5, -60.5, z), (-1, 0, 0), 4.0, 12.0) for z in (250.8, 261.9, 272.9)]
    bs += [mx(m) for m in list(bs)]
    step_image("s5_04_brows_in", "Step 5.4  Brow unit: slide in from the front above the eyes; 3 x M4x12 per side",
               [v(Q_FL, "front, head's left"), v(SIDE_R, "head's right side")],
               built=[frame] + mouth + [cheek] + eyes, new=brows, hardware=bs,
               colours=[(0.92, 0.50, 0.42)] * len(brows), focus=[frame],
               arrows=[(0, (0, 90, 262), (0, 40, 262)), (1, (85, 70, 262), (85, 20, 262))],
               labels=[(None, bs, "M4 x 12 through the frame's\ninner plate into the brow body", None)])
    fan = get("FanBracket#0")
    step_image("s5_05_fan_bracket", "Step 5.5  Fan bracket: from the back, onto the frame's rear ribs",
               [v(Q_BR, "back, head's right"), v(SIDE_R, "head's right side")],
               built=[frame] + mouth + [cheek] + eyes + brows, new=[fan], colours=[(0.70, 0.55, 0.85)],
               focus=[frame], arrows=[(0, (0, -200, 284), (0, -150, 284)), (1, (85, -190, 284), (85, -145, 284))],
               labels=[(None, fan, "fan bracket; 50 mm fan\non its 4 corner holes", None)])
    step_image("s5_06_complete", "The complete head, without the outer shell",
               [v(Q_FL, "front, head's left"), v(Q_BR, "back, head's right")], built=[frame],
               new=[fan, cheek] + eyes + brows + mouth,
               colours=[(0.70, 0.55, 0.85), (0.90, 0.72, 0.40)] + [(0.45, 0.62, 0.92)] * len(eyes)
               + [(0.92, 0.50, 0.42)] * len(brows) + [(0.55, 0.78, 0.58)] * len(mouth),
               focus=[frame], labels=[])


# ---------------------------------------------------------------- eyes (on the bench)

# his EyeMech e3.1 parts by modules.py's file number, grouped the way his e3.2 guide builds
# them (the print-in-place set joins each group's parts)
EM = {"part_a": [("027", "EyeCorePivotHolder"), ("018", "EyeAdaptor"), ("034", "EyeAdaptor")],
      "lr": [("005", "SG90")],
      "part_y": [("024", "EyeCorePivotHolder"), ("016", "PivotLarge")],
      "pivots": [("020", "Base")],
      "part_b": [("030", "LateralFrame"), ("021", "EyeAdaptor"), ("028", "EyeAdaptor"), ("026", "CentralServoHorn")],
      "base": [("014", "SnapEyemech_v20")],
      "eyes": [("023", "Component74"), ("036", "Component74")],
      "lids_top": [("013", "LidBR"), ("001", "PivotLarge"), ("019", "LidBR"), ("025", "PivotLarge")],
      "lids_bottom": [("007", "LidTR"), ("033", "2xBottomLidLever"), ("015", "LidTR"), ("003", "2xBottomLidLever")],
      "outer": [("009", "Base"), ("012", "Base")],
      "servos": [("010", "SG90"), ("035", "SG90"), ("022", "SG90"), ("002", "SG90"), ("029", "SG90")],
      "retainers": [("000", "SnapEyemech_v20"), ("008", "SnapEyemech_v20"), ("011", "SnapEyemech_v20")],
      "horns": [("037", "VerticalHorn"), ("031", "4xTopLidHorn"), ("006", "4xTopLidHorn"),
                ("032", "4xTopLidHorn"), ("017", "4xTopLidHorn")]}
# the mouth board's eye sockets (D18), servos in the order of EM's "lr" + "servos"
EYE_SOCKET = ["GP8 LR  look left/right", "GP9 UD  look up/down", "GP11 TR  top lid, head's right",
              "GP13 TL  top lid, head's left", "GP10 BR  bottom lid, head's right",
              "GP12 BL  bottom lid, head's left"]
E_FL = ((-0.7, 1.0, 0.85), (0, 0, 1))
E_FR = ((0.7, 1.0, 0.85), (0, 0, 1))
E_BL = ((-0.7, -1.0, 0.9), (0, 0, 1))
E_BR = ((0.7, -1.0, 0.9), (0, 0, 1))
E_UNDER = ((0.25, 0.6, -1.0), (0, 1, 0))
SERVO_BLUE = (0.22, 0.36, 0.78)


def eyemech():
    """{group: [meshes]} of his EyeMech e3.1, with the missing central pivot holder mirrored."""
    ref = os.path.join(K.PROJECT, "output", "ref")
    with open(os.path.join(ref, "modules.json"), encoding="utf-8") as f:
        files = {os.path.basename(p["file"])[:3]: p for p in json.load(f)["parts"] if p["module"] == "eyemech"}
    out = {}
    for g, members in EM.items():
        out[g] = []
        for n, label in members:
            if files[n]["label"] != label:
                sys.exit(f"output/ref/eyemech/{n}: expected {label}, found {files[n]['label']}; update EM")
            out[g].append(trimesh.load(os.path.join(ref, files[n]["file"]), force="mesh"))
    out["pivots"].append(mx(out["pivots"][0]))
    return out


def eye_steps():
    e = eyemech()
    a, y, cp, b = e["part_a"], e["part_y"], e["pivots"], e["part_b"]
    core = a + e["lr"] + y + cp + b
    step_image("s2_02_x_axis_a", "Step 2.2  Left/right servo into X-axis part A",
               [v(E_FL, "front, head's left"), v(E_BR, "back, head's right")], new=a + e["lr"],
               colours=[PALETTE[5]] * 3 + [SERVO_BLUE],
               labels=[(None, a[1:], "X-axis part A: its end clips\nswivel (print-in-place)", None),
                       (None, e["lr"], "left/right servo, shaft up;\nthe wire gap shows which way", None)])
    built = a + e["lr"]
    step_image("s2_03_y_axis", "Step 2.3  Y-axis part: clip it over the servo",
               [v(E_FL, "front, head's left"), v(E_BR, "back, head's right")], built=built, new=y,
               colours=[PALETTE[1]] * 2, focus=built + y,
               labels=[(None, y[0], "Y-axis part: clips over\nthe servo and locks it in", None),
                       (None, y[1], "its arch lever goes back\nto the up/down servo", None)])
    built += y
    step_image("s2_04_pivot_holders", "Step 2.4  Both central pivot holders",
               [v(E_FL, "front, head's left"), v(E_BR, "back, head's right")], built=built, new=cp,
               colours=[PALETTE[2]] * 2, focus=built + cp,
               labels=[(None, cp, "central pivot holder (2): a little\nstiff, then it turns freely", None)])
    built += cp
    step_image("s2_05_x_axis_b", "Step 2.5  X-axis part B onto the servo, loosely",
               [v(E_FL, "front, head's left"), v(E_BR, "back, head's right")], built=built, new=b,
               colours=[PALETTE[3]] * 4, focus=built + b,
               labels=[(None, b[0], "X-axis part B", None),
                       (None, b[3], "its middle goes on the servo\nshaft; it comes off again\nto set the centre", None)])
    built += b
    step_image("s2_06_into_base", "Step 2.6  Onto the base: the pivot holders snap in from underneath",
               [v(E_FL, "front, head's left"), v(E_UNDER, "from below")], built=built, new=e["base"],
               colours=[(0.62, 0.74, 0.90)], focus=built + e["base"],
               labels=[(1, cp, "pivot holders: snap into\nthe base from underneath", None),
                       (0, e["base"], "base plate, with its\nM3 inserts (step 1.4)", None)])
    built += e["base"]
    step_image("s2_07_eyes", "Step 2.7  The eyes onto their adaptors",
               [v(E_FL, "front, head's left"), v(E_FR, "front, head's right")], built=built, new=e["eyes"],
               colours=[(0.95, 0.95, 0.90)] * 2, focus=built,
               labels=[(None, e["eyes"], "eye: paint it first,\nit won't come off again", None)])
    built += e["eyes"]
    lids = e["lids_top"] + e["lids_bottom"]
    step_image("s2_08_lids", "Step 2.8  Eyelids: top lids have the short levers, bottom lids the long ones",
               [v(E_FL, "front, head's left"), v(E_BR, "back, head's right")], built=built, new=lids,
               colours=[PALETTE[4]] * 4 + [PALETTE[5]] * 4, focus=built,
               labels=[(None, e["lids_top"][0::2], "top lid", None), (None, e["lids_top"][1::2], "short lever", None),
                       (None, e["lids_bottom"][0::2], "bottom lid", None),
                       (None, e["lids_bottom"][1::2], "long lever", None)])
    built += lids
    step_image("s2_09_outer_pivots", "Step 2.9  Outer lid pivots: snap them into the underside of the base",
               [v(E_FL, "front, head's left"), v(E_UNDER, "from below")], built=built, new=e["outer"],
               colours=[PALETTE[6]] * 2, focus=built,
               labels=[(None, e["outer"], "outer lid pivot", None)])
    built += e["outer"]
    sv = e["servos"]
    step_image("s2_10_servos", "Step 2.10  The other 5 servos",
               [v(E_BL, "back, head's left"), v(E_BR, "back, head's right")], built=built, new=sv,
               colours=[SERVO_BLUE] * 5, focus=built,
               labels=[(None, sv[0], "up/down (GP9)", None),
                       (1, sv[1], "top lid, head's right\n(GP11)", None), (0, sv[2], "top lid, head's left\n(GP13)", None),
                       (1, sv[3], "bottom lid, head's right\n(GP10)", None),
                       (0, sv[4], "bottom lid, head's left\n(GP12)", None)])
    built += sv
    rt = e["retainers"]
    step_image("s2_11_retainers", "Step 2.11  Retainers over the servos",
               [v(E_BL, "back, head's left"), v(E_BR, "back, head's right")], built=built, new=rt,
               colours=[PALETTE[7]] * 3, focus=built,
               labels=[(None, rt[0], "up/down retainer", None), (None, rt[1:], "lid servo retainer", None)])
    built += rt
    hn = e["horns"]
    step_image("s2_12_horns", "Step 2.12  Horns, with the servos centred",
               [v(E_BL, "back, head's left"), v(E_BR, "back, head's right")], built=built, new=hn,
               colours=[PALETTE[1]] * 5, focus=built,
               labels=[(None, hn[0], "up/down horn\n(pop the servo out first)", None),
                       (None, hn[1:3], "top lid horn", None), (None, hn[3:], "bottom lid horn", None)])
    built += hn
    servos = e["lr"] + sv
    rest = [m for m in built if not any(m is s for s in servos + rt)]     # retainers off: they hide the servos
    step_image("s2_13_eye_servo_map", "Step 2.13  The EyeMech's 6 servos and their sockets (retainers left out)",
               [v(E_BL, "back, head's left"), v(E_BR, "back, head's right")], built=rest, new=servos,
               colours=PALETTE[:6], focus=built,
               labels=[(None, servos[0], EYE_SOCKET[0], None), (None, servos[1], EYE_SOCKET[1], None),
                       (1, servos[2], EYE_SOCKET[2], None), (0, servos[3], EYE_SOCKET[3], None),
                       (1, servos[4], EYE_SOCKET[4], None), (0, servos[5], EYE_SOCKET[5], None)])


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    which = set(sys.argv[1:]) or {"inserts", "eyes", "mouth", "brows", "mount"}
    if "inserts" in which:
        steps_inserts()
    if "eyes" in which:
        eye_steps()
    mouth = brows = None
    if which & {"mouth", "mount"}:
        mouth = mouth_steps()
        mouth_overview(mouth)
    if which & {"brows", "mount"}:
        brows = brow_steps()
    if "mount" in which:
        mount_steps(mouth, brows)

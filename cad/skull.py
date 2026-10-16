"""
Skull v0 (M3): the printed skull the skin sits on and the mechanisms mount in.

The wall is the shell between the skin's inner surface (the skull's outside:
the silicone sits on it) and the skull's inner surface, SKULL_WALL thick,
both true offsets of the proxy face (head.py). It is opened where the
mechanisms meet the skin:

  eyes and brows   one opening per side: the convex hull of the eye's circle
                   (EYE_OPEN_R around the eye axis; the lids' sphere is 18.1)
                   and the bench rig's brow window (brow_rig.window_bounds)
  mouth            a rounded rectangle in front of the mouth module, where the
                   lips, the jaw and the skin's attachments work (MOUTH_OPEN_*)
  Every opening is cut by normal_cutter(): its outline is extruded along the
  surface normal, so its edge is square to the wall (no slivers).
  neck    open at the base (the envelopes are cut flat at z = 0)

and split into printable pieces at SKULL_SPLIT_Z and SKULL_SPLIT_Y:

  skull_front_upper   forehead, brows, eyes, the brow brackets' mount plates
  skull_front_lower   cheeks, upper lip, chin and the front of the neck
  skull_back_upper    the back of the cranium
  skull_back_lower    the nape and the back of the neck
  skull_access_panel  the rear access panel: cut from the back upper piece,
                      resting on a lip inside the opening, 4 countersunk screws
  skull_neck_plate    the neck base: closes the bottom of the neck, screwed to
                      both lower pieces, bolts to the jar's stand (4 x M4)
  skull_eye_strap     a printed strap 0.4 over the back of the EyeMech's base
                      plate, bolted to two ledges on the back upper piece
  skull_shelf         a separate plate between the EyeMech (on top) and the
                      mouth module (underneath), clear of the wall by 0.4: the
                      EyeMech's cradle, screwed down onto four ledges on the
                      side walls

v0 has no joints, fasteners, access panel or module mounts yet: it is the
layout to check them against (PLAN M3).

Built as meshes with manifold booleans; written to output/stl/ in the
assembled pose.

Run:  python cad/skull.py
"""
import os
import sys

import manifold3d as mf
import numpy as np
import trimesh

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import cadkit as K  # noqa: E402
import browgeom as B  # noqa: E402
import brow_rig as BR  # noqa: E402
import geom as G  # noqa: E402
import head as H  # noqa: E402
import reserve as R  # noqa: E402

P = K.params()
S = P.HEAD_SCALE
BIG = 1000.0
MIRROR_X = np.diag([-1.0, 1.0, 1.0, 1.0])


def box(lo, hi):
    return BR.box(lo, hi)


def cyl(r, a, b, sections=64):
    return BR.cyl(r, a, b, sections)


def mirrored(man):
    """A manifold mirrored in x (left brow -> right brow)."""
    return man.mirror((1.0, 0.0, 0.0))


def mouth_top():
    """z of the mouth module's top plate (its highest point) in the head frame."""
    t = G.module_translation("mouth", S)
    return float(t[2] + P.MOUTH_TOP_SRC_Z)


def normal_cutter(outline, outside=40.0, inside=P.SKULL_WALL + 4.0):
    """A cutter for an opening in the face side of the skull: the outline, given as (x, z)
    points around it, is placed on the skin's inner surface and extruded along the local
    surface normal (outside mm out, inside mm in). Its walls are square to the skull wall,
    so the opening's edge has no slivers (a box or cylinder crosses the curved wall obliquely).
    `outside` must clear the face's bulge across the opening: at 4 mm the lip area of a 92 mm
    mouth opening stayed behind as a loose patch. Outlines must be convex."""
    xz = np.asarray(outline, float)
    y = G.front_y(xz[:, 0], xz[:, 1], S, P.SKIN_T)
    pts = np.column_stack([xz[:, 0], y, xz[:, 1]])
    nx, ny, nz = G._outer_normal(xz[:, 0], xz[:, 1], S)
    n = np.column_stack([nx, ny, nz])
    # the outer rim never points downward: where the face turns under (the chin) a rim following
    # the normal down grazed the wall below the opening
    up = n.copy()
    up[:, 2] = np.maximum(up[:, 2], 0.0)
    up /= np.linalg.norm(up, axis=1, keepdims=True)
    outer, inner = pts + outside * up, pts - inside * n
    # the convex hull of the two rims (every outline here is convex): a fan-capped band
    # crossed itself where the surface curves hard and left 0.02 mm flaps at the edge
    return R.to_mf(trimesh.convex.convex_hull(np.vstack([outer, inner])))


def circle(cx, cz, r, n=96):
    a = np.linspace(0.0, 2 * np.pi, n, endpoint=False)
    return np.column_stack([cx + r * np.cos(a), cz + r * np.sin(a)])


def densify(outline, step=1.5):
    """Resample a closed (x, z) outline every `step` mm, so it follows the curved surface."""
    pts = np.asarray(outline, float)
    out = []
    for a, b in zip(pts, np.roll(pts, -1, axis=0)):
        n = max(1, int(np.ceil(np.linalg.norm(b - a) / step)))
        out += [a + (b - a) * t for t in np.arange(n) / n]
    return np.array(out)


def rounded_rectangle(x0, x1, z0, z1, r):
    """A rectangle in (x, z) with corners rounded to r: sharp corners left slivers."""
    pts = []
    for cx, cz, a0 in ((x1 - r, z0 + r, -90), (x1 - r, z1 - r, 0), (x0 + r, z1 - r, 90), (x0 + r, z0 + r, 180)):
        for a in np.radians(np.arange(a0, a0 + 91, 10)):
            pts.append((cx + r * np.cos(a), cz + r * np.sin(a)))
    return densify(pts)


def hull(*outlines):
    """Convex hull of several (x, z) outlines, as one outline: an eye circle and its brow
    window cut as two openings left a sharp point of wall where they meet."""
    from scipy.spatial import ConvexHull
    pts = np.vstack(outlines)
    return densify(pts[ConvexHull(pts).vertices])


def openings():
    ez = G.eye_z(S)
    wx0, wx1, wz0, wz1 = BR.window_bounds()
    cuts = []
    for sx in (+1, -1):
        xa, xb = sorted((sx * wx0, sx * (wx1 + 1.5)))                  # +1.5: see brow_rig.window_cut
        eye = circle(sx * P.EYE_SPACING / 2, ez, P.EYE_OPEN_R)
        window = rounded_rectangle(xa, xb, wz0, wz1, 4.0)
        cuts.append(normal_cutter(hull(eye, window)))
    # 15 out is enough for the hull to take in the lips; 40 grazed the wall under the chin
    cuts.append(normal_cutter(rounded_rectangle(-P.MOUTH_OPEN_X, P.MOUTH_OPEN_X, *P.MOUTH_OPEN_Z, 6.0), outside=15.0))
    return mf.Manifold.batch_boolean(cuts, mf.OpType.Add)


def brow_mounts(skull_in_bite):
    """Plates the two brow brackets bolt up into: the bracket flange's footprint and more,
    at the flange's top, biting 0.5 into the wall so they join it."""
    plates = []
    for side in (+1, -1):
        top = float(B.to_head((0.0, 0.0, B.FLANGE_Z[1]))[2])
        plate = box((2.0, -55.0, top), (85.0, 60.0, top + P.BROW_MOUNT_T)) ^ skull_in_bite
        for c in B.bracket_mounts():
            plate -= cyl(P.M3_CLEAR / 2, c - [0, 0, 1.0], c + [0, 0, P.BROW_MOUNT_T + 1.0])
        for y in P.BROW_STOPS_Y:
            c = B.to_head((B.HORN_X, y, B.FLANGE_Z[1]))
            plate -= cyl(P.HEX_KEY_D / 2 + 0.5, c - [0, 0, 1.0], c + [0, 0, P.BROW_MOUNT_T + 1.0])
        plates.append(plate if side > 0 else mirrored(plate))
    return plates


def eyemech_feet(tol=0.1):
    """The EyeMech stands on feet (its side plates, an inner plate and a rear block), not on
    its base plate: [(x0, y0, x1, y1)] footprints of the parts within tol of its lowest point,
    and that height."""
    import layout_check as L
    base_scale, parts = L.load_parts()
    L.place(parts, base_scale, S)
    eye = [p for p in parts if p["module"] == "eyemech"]
    zmin = min(p["m"].bounds[0][2] for p in eye)
    feet = [(b[0][0], b[0][1], b[1][0], b[1][1]) for b in (p["m"].bounds for p in eye) if b[0][2] < zmin + tol]
    return feet, zmin


def shelf_z():
    z0 = mouth_top() + P.SHELF_GAP_BELOW
    return z0, z0 + P.SHELF_T


def shelf_ledge_points(skull_in_clear_mesh):
    """(x, y) of the shelf's screws over the four ledges: SHELF_LEDGE[0] / 2 in from the side
    wall at each SHELF_LEDGES_Y."""
    z0, _ = shelf_z()
    out = []
    for sx in (+1, -1):
        for y in P.SHELF_LEDGES_Y:
            x = 40.0
            while x < 120 and G.envelope_margin(np.array([[sx * x, y, z0 - 1.0]]), S,
                                                 P.SKIN_T + P.SKULL_WALL)[0] > 0:
                x += 0.5
            out.append((sx * (x - P.SHELF_LEDGE[0] / 2), y, sx))
    return out


def shelf(skull_in_clear):
    """The shelf: a plate between the mouth (under it) and the EyeMech (on it), clear of the
    wall by 0.4, with the EyeMech cradle on top (pads under its feet, a stop behind its rear
    foot) and clearance holes for the screws into the ledges on the side walls."""
    z0, z1 = shelf_z()
    plate = box((-BIG, P.SHELF_Y[0], z0), (BIG, P.SHELF_Y[1], z1)) ^ skull_in_clear
    feet, zf = eyemech_feet()
    m, c = P.CRADLE_PAD_MARGIN, P.CRADLE_CLEAR
    st, sh = P.CRADLE_STOP
    adds, cuts = [], []
    for x0, y0, x1, y1 in feet:
        # pads overhang the foot except toward a side wall (the outer side plates sit ~1 mm from it)
        px0 = x0 if x0 < -40 else x0 - m
        px1 = x1 if x1 > 40 else x1 + m
        py1 = min(y1 + m, P.SHELF_Y[1] - 2.0)                                     # off the shelf's curved front
        adds.append(box((px0, y0 - m, z1 - 0.01), (px1, py1, zf)))                # feet rest on it
        if y1 - y0 < 30:                                                         # the rear foot: a stop
            adds.append(box((x0, y0 - c - st, z1 - 0.01), (x1, y0 - c, zf + sh)))
    plate = mf.Manifold.batch_boolean([plate] + adds, mf.OpType.Add) ^ skull_in_clear
    for x, y, _ in shelf_ledge_points(None):
        cuts.append(cyl(P.M3_CLEAR / 2, (x, y, z0 - 1), (x, y, z1 + 1)))
    cable = trimesh.load(os.path.join(G.ref_dir(), "reserve", "cable.stl"), force="mesh")
    cuts.append(R.to_mf(cable))
    return plate - mf.Manifold.batch_boolean(cuts, mf.OpType.Add)


def eyemech_top():
    """Highest point of the EyeMech's base plate inside the strap's band (STRAP_Y)."""
    import layout_check as L
    base_scale, parts = L.load_parts()
    L.place(parts, base_scale, S)
    top = -np.inf
    for p in parts:
        if p["module"] != "eyemech":
            continue
        v = p["m"].vertices
        band = v[(v[:, 1] >= P.STRAP_Y[0] - 1) & (v[:, 1] <= P.STRAP_Y[1] + 1)]
        if len(band):
            top = max(top, float(band[:, 2].max()))
    return top


def strap_parts(skull_in_clear, bite):
    """The retaining strap across the back of the EyeMech's base plate (STRAP_GAP above it),
    clear of the wall by 0.4, and its two ledges on the back upper piece: (strap, [(piece,
    ledge, insert hole)])."""
    z0 = eyemech_top() + P.STRAP_GAP
    y0, y1 = P.STRAP_Y
    strap = box((-BIG, y0, z0), (BIG, y1, z0 + P.STRAP_T)) ^ skull_in_clear
    ledges = []
    ym = (y0 + y1) / 2
    for sx in (+1, -1):
        x = 40.0
        while x < 120 and G.envelope_margin(np.array([[sx * x, ym, z0 - 1.0]]), S, P.SKIN_T + P.SKULL_WALL)[0] > 0:
            x += 0.5
        xc = sx * (x - 6.0)
        xa, xb = sorted((xc - sx * 6.0, xc + sx * 12.0))
        ledge = box((xa, y0 - 3.0, z0 - 6.0), (xb, y1 + 3.0, z0 - 0.01)) ^ bite
        hole = cyl(P.M3_INSERT_HOLE / 2, (xc, ym, z0 + 0.5), (xc, ym, z0 - 5.0))
        strap -= cyl(P.M3_CLEAR / 2, (xc, ym, z0 - 1.0), (xc, ym, z0 + P.STRAP_T + 1.0))
        piece = "skull_back_upper" if z0 >= P.SKULL_SPLIT_Z else "skull_back_lower"
        ledges.append((piece, ledge, hole))
    return strap, ledges


def back_points(outline, mid):
    """Points on the wall's mid-surface behind (x, z) outline points (rays toward -y from
    inside the head), and the outward normals there."""
    xz = np.asarray(outline, float)
    origins = np.column_stack([xz[:, 0], np.full(len(xz), P.SKULL_SPLIT_Y), xz[:, 1]])
    dirs = np.tile([0.0, -1.0, 0.0], (len(xz), 1))
    loc, ray, tri = mid.ray.intersects_location(origins, dirs, multiple_hits=False)
    order = np.argsort(ray)
    return loc[order], mid.face_normals[tri[order]]


def back_cutter(outline, mid, outside=15.0, inside=P.SKULL_WALL + 6.0):
    """normal_cutter() for the back of the head: the convex hull of the outline's rims,
    outside and inside the wall along its normals."""
    pts, n = back_points(outline, mid)
    half = P.SKULL_WALL / 2
    return R.to_mf(trimesh.convex.convex_hull(np.vstack([pts + (half + outside) * n, pts - (inside - half) * n])))


def access_panel(bite, clear_layer_in):
    """The rear access panel: (panel, opening cutter, lip, panel screw holes, lip insert holes).
    The panel is the wall inside the outline, PANEL_GAP smaller all round; it rests on a narrow
    lip behind the opening's edge (biting into the back upper piece's wall around it), held by
    4 countersunk M3 screws into inserts in pads on the lip, one at each side's midpoint."""
    inset = P.SKIN_T + P.SKULL_WALL
    mid = H.envelope(S, P.SKIN_T + P.SKULL_WALL / 2)
    w, h, r = P.PANEL_SIZE
    zc = P.PANEL_CENTRE_Z
    g = P.PANEL_GAP
    reach, lt = P.PANEL_LIP

    def outline(grow):
        return rounded_rectangle(-w / 2 - grow, w / 2 + grow, zc - h / 2 - grow, zc + h / 2 + grow, max(r + grow, 1.0))

    opening = back_cutter(outline(0.0), mid)
    panel_cut = back_cutter(outline(-g), mid)
    lip_out = back_cutter(outline(reach), mid, inside=P.SKULL_WALL + lt + 2.0)
    lip_in = back_cutter(outline(-reach), mid, inside=P.SKULL_WALL + lt + 2.0)
    deep = R.to_mf(H.envelope(S, inset + lt))
    behind_wall = (bite - deep) ^ (lip_out - opening)                   # bites into the wall round the opening
    grown = back_cutter(outline(1.0), mid)                              # overlaps the wall part by 1 mm
    si, pad = P.PANEL_SCREW_IN, P.PANEL_PAD / 2
    points = ((0.0, zc + h / 2 - si), (0.0, zc - h / 2 + si), (w / 2 - si, zc), (-w / 2 + si, zc))
    pads = [back_cutter(rounded_rectangle(x - pad, x + pad, z - pad, z + pad, 3.0), mid) for x, z in points]
    pads = mf.Manifold.batch_boolean(pads, mf.OpType.Add) ^ grown
    behind_panel = (clear_layer_in - deep) ^ ((grown - lip_in) + pads)  # 0.1 behind the panel
    lip = behind_wall + behind_panel
    screws, inserts = [], []
    for x, z in points:
        (q,), (n,) = back_points([(x, z)], mid)
        o, i = q + n * P.SKULL_WALL / 2, q - n * P.SKULL_WALL / 2
        inserts.append(cyl(P.M3_INSERT_HOLE / 2, i + 0.3 * n, i - (lt - 1.0) * n, 32))
        rr = P.M3_CSK[0] / 2 + 0.6
        cone = trimesh.creation.cone(rr, rr, sections=32)
        cone.apply_transform(trimesh.geometry.align_vectors([0.0, 0.0, 1.0], -n))
        cone.apply_translation(o + 0.6 * n)
        screws.append(cyl(P.M3_CLEAR / 2, i - 1.0 * n, o + 1.0 * n, 32) + R.to_mf(cone))
    return panel_cut, opening, lip, screws, inserts


def neck_plate(clear):
    """The neck base: a plate closing the bottom of the neck (inside the wall by 0.4) with a
    collar up the wall's inside; NECK_SCREWS countersunk M3 screws through the wall into
    inserts in the collar; 4 x M4 holes on NECK_BOLT_SQUARE for the jar's stand; an exit for
    the cable channel. Returns (plate, {piece: [screw holes]})."""
    inset = P.SKIN_T + P.SKULL_WALL
    t, (ct, ch) = P.NECK_PLATE_T, P.NECK_COLLAR
    inner = R.to_mf(H.envelope(S, inset + 0.4 + ct))
    plate = (clear ^ box((-BIG, -BIG, 0.0), (BIG, BIG, t))) + ((clear - inner) ^ box((-BIG, -BIG, 0.0), (BIG, BIG, ch)))
    lo, hi = R.from_mf(plate).bounds
    cx, cy = (lo[0] + hi[0]) / 2, (lo[1] + hi[1]) / 2
    cuts, screws = [], {}
    h = P.NECK_BOLT_SQUARE / 2
    for dx in (-h, h):
        for dy in (-h, h):
            cuts.append(cyl(P.M4_CLEAR / 2, (cx + dx, cy + dy, -1.0), (cx + dx, cy + dy, t + 1.0)))
    a, b = np.array(P.CABLE_PATH[-2]), np.array(P.CABLE_PATH[-1])
    cuts.append(cyl(P.CABLE_D / 2 + P.CABLE_EXIT_CLEAR, (b[0], b[1], -1.0), (b[0], b[1], ch + 1.0)))
    mid = H.envelope(S, P.SKIN_T + P.SKULL_WALL / 2)
    for k in range(P.NECK_SCREWS):
        ang = 2 * np.pi * (k + 0.5) / P.NECK_SCREWS
        d = np.array([np.cos(ang), np.sin(ang), 0.0])
        # where a ray from the neck's centre at the screw height meets the wall's mid-surface
        loc, _, tri = mid.ray.intersects_location([(cx, cy, P.NECK_SCREW_Z)], [d], multiple_hits=False)
        if not len(loc):
            continue
        q, n = loc[0], mid.face_normals[tri[0]]
        o, i = q + n * P.SKULL_WALL / 2, q - n * P.SKULL_WALL / 2
        cuts.append(cyl(P.M3_INSERT_HOLE / 2, i + 0.1 * n, i - (0.4 + ct - 1.0) * n, 32))   # insert
        r = P.M3_CSK[0] / 2 + 0.6
        cone = trimesh.creation.cone(r, r, sections=32)
        cone.apply_transform(trimesh.geometry.align_vectors([0.0, 0.0, 1.0], -n))
        cone.apply_translation(o + 0.6 * n)
        piece = "skull_front_lower" if q[1] >= P.SKULL_SPLIT_Y else "skull_back_lower"
        screws.setdefault(piece, []).append(cyl(P.M3_CLEAR / 2, i - 1.0 * n, o + 1.0 * n, 32) + R.to_mf(cone))
    return plate - mf.Manifold.batch_boolean(cuts, mf.OpType.Add), screws


def shelf_ledges(bite):
    """Ledges under the shelf on the side walls, biting into the wall, each with an M3 insert
    from the top: [(piece, ledge, insert hole)]."""
    z0, _ = shelf_z()
    reach, length, depth = P.SHELF_LEDGE
    out = []
    for x, y, sx in shelf_ledge_points(None):
        xa, xb = sorted((x - sx * reach / 2, x + sx * (reach / 2 + 6.0)))
        ledge = box((xa, y - length / 2, z0 - depth), (xb, y + length / 2, z0 - 0.01)) ^ bite
        hole = cyl(P.M3_INSERT_HOLE / 2, (x, y, z0 + 0.5), (x, y, z0 - depth + 1.0))
        piece = "skull_front_lower" if y >= P.SKULL_SPLIT_Y else "skull_back_lower"
        out.append((piece, ledge, hole))
    return out


# ---------------------------------------------------------------------------
# joints: screwed tabs along the four seams
# ---------------------------------------------------------------------------
# (name, axis, value, piece with the tab (A), piece with the screw (B), A's side of the seam,
#  fewest tabs accepted)
SEAMS = (
    # tabs on the upper piece, screws into the lower one: there is room for countersinks
    # between the mouth opening and the seam, but not under the eye openings
    # the front seam is short and crowded (eye openings above, the shelf's cradle behind); the
    # front upper piece is held mainly by its back seam
    ("front, upper | lower", 2, P.SKULL_SPLIT_Z, "skull_front_upper", "skull_front_lower", +1, 2),
    ("back, upper | lower", 2, P.SKULL_SPLIT_Z, "skull_back_lower", "skull_back_upper", -1, 3),
    ("upper, front | back", 1, P.SKULL_SPLIT_Y, "skull_back_upper", "skull_front_upper", -1, 3),
    ("lower, front | back", 1, P.SKULL_SPLIT_Y, "skull_back_lower", "skull_front_lower", -1, 3),
)


def chain(segs, tol=1e-4):
    """Join line segments (n, 2, 3) that share end points into ordered polylines (a plane cut
    through a mesh). Written here so the project needs no graph library."""
    key = lambda p: tuple(np.round(p / tol).astype(np.int64))         # noqa: E731
    ends = {}
    for i, (a, b) in enumerate(segs):
        ends.setdefault(key(a), []).append((i, 1))
        ends.setdefault(key(b), []).append((i, 0))
    used = np.zeros(len(segs), bool)
    lines = []
    for start in range(len(segs)):
        if used[start]:
            continue
        used[start] = True
        line = [segs[start][0], segs[start][1]]
        for forward in (True, False):
            while True:
                tip = line[-1] if forward else line[0]
                nxt = next(((i, other) for i, other in ends.get(key(tip), []) if not used[i]), None)
                if nxt is None:
                    break
                i, other = nxt
                used[i] = True
                (line.append if forward else (lambda p: line.insert(0, p)))(segs[i][other])
        lines.append(np.array(line))
    return lines


def seam_runs(mid, axis, value, keep):
    """Ordered runs of points (every ~2 mm) along the wall's mid-surface where the split plane
    cuts it, kept where keep(points) is True."""
    normal = np.eye(3)[axis]
    segs = trimesh.intersections.mesh_plane(mid, normal, normal * value)
    runs = []
    for line in chain(segs):
        line = np.asarray(line, float)
        d = np.r_[0, np.cumsum(np.linalg.norm(np.diff(line, axis=0), axis=1))]
        t = np.arange(0, d[-1], 2.0)
        pts = np.column_stack([np.interp(t, d, line[:, i]) for i in range(3)])
        ok = keep(pts)
        cur = []
        for q, k in zip(pts, ok):
            if k:
                cur.append(q)
            elif cur:
                runs.append(np.array(cur))
                cur = []
        if cur:
            runs.append(np.array(cur))
    return runs


def frame_box(origin, axes, lo, hi):
    """Box with extents lo..hi along the given unit axes (columns), placed at origin."""
    lo, hi = np.asarray(lo, float), np.asarray(hi, float)
    b = trimesh.creation.box(extents=hi - lo)
    b.apply_translation((lo + hi) / 2)
    tf = np.eye(4)
    tf[:3, :3] = np.column_stack(axes)
    tf[:3, 3] = origin
    b.apply_transform(tf)
    return R.to_mf(b)


def tab_geometry(q, n, axis, value, side, layers, mid):
    """(tab, insert hole, screw hole, B point) for a tab at seam point q (mid-wall), wall
    normal n. The tab sits on piece A's side (`side` -1 = the lower/back side) and reaches
    across the seam behind piece B's wall; the screw goes through B's wall into the tab.
    Its box is built in the wall's frame (along the seam, across it, along the normal): an
    axis-aligned box cut the tab obliquely where the wall leans and left slivers."""
    bite_layer, clear_layer = layers
    e = np.eye(3)[axis]                                                # across the seam (plane normal)
    t = np.cross(n, e)
    t /= np.linalg.norm(t)                                             # along the seam
    ew = np.cross(t, n)
    ew *= np.sign(ew @ e) / np.linalg.norm(ew)                         # across the seam, in the wall
    origin = q - e * (q[axis] - value)                                 # on the seam plane
    w = P.SEAM_TAB_W / 2
    a_over, b_over = P.SEAM_TAB_OVER
    # the far edges run square to the wall (axes t, ew, n); the edge at the seam is the seam
    # plane itself (the half-spaces below), matching the wall's split
    far = 2.0 * max(a_over, b_over)
    a_rng = (-a_over, far) if side < 0 else (-far, a_over)
    b_rng = (-far, b_over) if side < 0 else (-b_over, far)
    lo_side = box((-BIG, -BIG, -BIG), np.where(np.arange(3) == axis, value, BIG))
    hi_side = box(np.where(np.arange(3) == axis, value, -BIG), (BIG, BIG, BIG))
    lo_over = box((-BIG, -BIG, -BIG), np.where(np.arange(3) == axis, value + 0.5, BIG))
    hi_over = box(np.where(np.arange(3) == axis, value - 0.5, -BIG), (BIG, BIG, BIG))
    a_half, b_half = (lo_side, hi_over) if side < 0 else (hi_side, lo_over)   # B overlaps A by 0.5
    box_a = frame_box(origin, (t, ew, n), (-w, a_rng[0], -30.0), (w, a_rng[1], 30.0)) ^ a_half
    box_b = frame_box(origin, (t, ew, n), (-w, b_rng[0], -30.0), (w, b_rng[1], 30.0)) ^ b_half
    tab = (bite_layer ^ box_a) + (clear_layer ^ box_b)
    qb = q.copy()
    qb[axis] = value - side * (b_over / 2 + 0.5)
    # back onto the wall's mid-surface: where the wall leans (the occiput) a straight shift
    # leaves it; the screw runs along the normal there
    pt, _, tri = mid.nearest.on_surface([qb])
    qb, n = pt[0], mid.face_normals[tri[0]]
    o = qb + n * P.SKULL_WALL / 2                                      # B's outer surface
    i = qb - n * P.SKULL_WALL / 2                                      # B's inner surface
    insert = cyl(P.M3_INSERT_HOLE / 2, i + 0.3 * n, i - (P.SEAM_TAB_T - 1.0) * n, 32)
    r = P.M3_CSK[0] / 2 + 0.6
    cone = trimesh.creation.cone(r, r, sections=32)                    # 90 deg: height = radius
    cone.apply_transform(trimesh.geometry.align_vectors([0.0, 0.0, 1.0], -n))   # apex inward
    cone.apply_translation(o + 0.6 * n)
    screw = cyl(P.M3_CLEAR / 2, i - 1.0 * n, o + 1.0 * n, 32) + R.to_mf(cone)
    return tab, insert, screw, qb


def ring(c, mid, r=P.M3_CSK[0] / 2 + 2.0, k=8):
    """Points on the wall's mid-surface around c at radius r: a screw is only placed where all
    of them are wall, so its countersink keeps 2 mm of wall to any opening."""
    n = mid.face_normals[mid.nearest.on_surface([c])[2][0]]
    u = np.cross(n, [0.0, 0.0, 1.0] if abs(n[2]) < 0.9 else [1.0, 0.0, 0.0])
    u /= np.linalg.norm(u)
    v = np.cross(n, u)
    a = np.linspace(0, 2 * np.pi, k, endpoint=False)
    pts = c + r * (np.outer(np.cos(a), u) + np.outer(np.sin(a), v))
    return mid.nearest.on_surface(pts)[0]


def joints(wall_mesh, keepout):
    """Tabs, insert holes and screw holes for every seam: {piece: [adds]}, {piece: [cuts]},
    and a report. A candidate tab is kept when there is wall on both sides of the seam, it
    stays SEAM_TAB_CLEAR from everything in `keepout`, and it is SEAM_TAB_SPACING from the
    last tab on its seam (20 from tabs on other seams)."""
    from scipy.spatial import cKDTree
    inset = P.SKIN_T + P.SKULL_WALL
    mid = H.envelope(S, P.SKIN_T + P.SKULL_WALL / 2)
    layers = (R.to_mf(H.envelope(S, inset - 0.5)) - R.to_mf(H.envelope(S, inset + P.SEAM_TAB_T)),
              R.to_mf(H.envelope(S, inset + 0.1)) - R.to_mf(H.envelope(S, inset + P.SEAM_TAB_T)))
    tree = cKDTree(keepout)
    adds, cuts, report, placed = {}, {}, [], []
    for name, axis, value, piece_a, piece_b, side, fewest in SEAMS:
        if axis == 2:
            front = "front" in piece_a

            def keep(p, f=front):
                return (p[:, 1] >= P.SKULL_SPLIT_Y + 8) if f else (p[:, 1] <= P.SKULL_SPLIT_Y - 8)
        else:
            upper = piece_a.endswith("upper")

            def keep(p, u=upper):
                if u:
                    return p[:, 2] >= P.SKULL_SPLIT_Z + 8
                return (p[:, 2] <= P.SKULL_SPLIT_Z - 8) & (p[:, 2] >= 10.0)
        count = 0
        for run in seam_runs(mid, axis, value, keep):
            last = None
            for q in run:
                if last is not None and np.linalg.norm(q - last) < P.SEAM_TAB_SPACING:
                    continue
                if any(np.linalg.norm(q - p) < 20.0 for p in placed):
                    continue
                n = mid.face_normals[mid.nearest.on_surface([q])[2][0]]
                if abs(n[axis]) > 0.6:                                   # wall nearly in the seam plane:
                    continue                                             # the tab edges would be slivers
                qa = q.copy()
                qa[axis] = value + side * (P.SEAM_TAB_OVER[0] / 2)
                qa = mid.nearest.on_surface([qa])[0][0]
                tab, insert, screw, qb = tab_geometry(q, n, axis, value, side, layers, mid)
                if not wall_mesh.contains([qa, qb]).all():               # an opening on either side
                    continue
                if not wall_mesh.contains(ring(qb, mid)).all():           # the countersink near an opening
                    continue
                tm = R.from_mf(tab)
                if len(tm.faces) == 0 or tree.query(tm.vertices)[0].min() < P.SEAM_TAB_CLEAR:
                    continue
                adds.setdefault(piece_a, []).append(tab)
                cuts.setdefault(piece_a, []).append(insert)
                cuts.setdefault(piece_b, []).append(screw)
                placed.append(q)
                last = q
                count += 1
        report.append((name, count, fewest))
    return adds, cuts, report


def keepout_points(extra=()):
    """Points the joint tabs keep clear of: every module and brow part sampled densely (about
    1 per mm2: at the modules' own 2.4 mm spacing a tab slipped into the EyeMech's base), the
    meshes in `extra` (the shelf, the brow mount plates), and everything that moves
    (skull_check.motion_clouds)."""
    import brow_check as BC
    import layout_check as L
    import pose_sweep as PS
    import skull_check as SC
    base_scale, parts = L.load_parts()
    L.place(parts, base_scale, S)
    gr = PS.groups(parts)
    brow = BC.load()
    meshes = [p["m"] for p in parts]
    meshes += [m for k, m in brow.items() if m is not None and not k.startswith("rig")]
    meshes += list(extra)
    pts = [trimesh.sample.sample_surface(m, int(np.clip(m.area, 200, 60000)), seed=8)[0] for m in meshes]
    pts += list(SC.motion_clouds(gr, brow).values())
    return np.vstack(pts)


def pieces(with_joints=True):
    skin_in = R.to_mf(H.envelope(S, P.SKIN_T))
    skull_in = R.to_mf(H.envelope(S, P.SKIN_T + P.SKULL_WALL))
    bite = R.to_mf(H.envelope(S, P.SKIN_T + P.SKULL_WALL - 0.5))      # 0.5 into the wall
    clear = R.to_mf(H.envelope(S, P.SKIN_T + P.SKULL_WALL + 0.4))     # 0.4 off the wall
    wall = (skin_in - skull_in) - openings()
    wall_mesh = R.from_mf(wall)
    plates = brow_mounts(bite)
    wall = mf.Manifold.batch_boolean([wall] + plates, mf.OpType.Add)
    shelf_part = shelf(clear)
    strap_part, strap_ledges = strap_parts(clear, bite)
    ledges = shelf_ledges(bite) + strap_ledges
    zs, ys = P.SKULL_SPLIT_Z, P.SKULL_SPLIT_Y
    out = {
        "skull_front_upper": wall ^ box((-BIG, ys, zs), (BIG, BIG, BIG)),
        "skull_front_lower": wall ^ box((-BIG, ys, -BIG), (BIG, BIG, zs)),
        "skull_back_upper": wall ^ box((-BIG, -BIG, zs), (BIG, ys, BIG)),
        "skull_back_lower": wall ^ box((-BIG, -BIG, -BIG), (BIG, ys, zs)),
    }
    for piece, ledge, hole in ledges:
        out[piece] = (out[piece] + ledge) - hole
    neck, neck_screws = neck_plate(clear)
    for piece, holes in neck_screws.items():
        out[piece] -= mf.Manifold.batch_boolean(holes, mf.OpType.Add)
    clear_in = R.to_mf(H.envelope(S, P.SKIN_T + P.SKULL_WALL + 0.1))
    panel_cut, opening, lip, panel_screws, lip_inserts = access_panel(bite, clear_in)
    panel = (out["skull_back_upper"] ^ panel_cut) - mf.Manifold.batch_boolean(panel_screws, mf.OpType.Add)
    out["skull_back_upper"] = ((out["skull_back_upper"] - opening) + lip) - mf.Manifold.batch_boolean(
        lip_inserts, mf.OpType.Add)
    if with_joints:
        extra = ([R.from_mf(shelf_part), R.from_mf(strap_part), R.from_mf(neck), R.from_mf(lip)]
                 + [R.from_mf(pl) for pl in plates]
                 + [R.from_mf(l) for _, l, _ in ledges])
        adds, cuts, report = joints(wall_mesh, keepout_points(extra))
        for name in out:
            out[name] = mf.Manifold.batch_boolean([out[name]] + adds.get(name, []), mf.OpType.Add)
            if cuts.get(name):
                out[name] -= mf.Manifold.batch_boolean(cuts[name], mf.OpType.Add)
        for seam, count, fewest in report:
            print(f"{'' if count >= fewest else 'WARN  '}seam {seam}: {count} screwed tab(s)")
        print(f"joints: {sum(c for _, c, _ in report)} M3 countersunk screws + inserts")
    out["skull_shelf"] = shelf_part
    out["skull_eye_strap"] = strap_part
    out["skull_neck_plate"] = neck
    out["skull_access_panel"] = panel
    return out


def main():
    out = K.stl_dir()
    os.makedirs(out, exist_ok=True)
    ok = True
    for name, man in pieces().items():
        m = R.from_mf(man)
        m.merge_vertices()
        m.update_faces(m.nondegenerate_faces())
        m.remove_unreferenced_vertices()
        good = bool(m.is_watertight) and m.body_count == 1
        ok &= good
        m.export(os.path.join(out, name + ".stl"))
        e = m.extents
        print(f"{'' if good else 'FAIL  '}wrote {name}.stl  {e[0]:.1f} x {e[1]:.1f} x {e[2]:.1f} mm  "
              f"watertight={m.is_watertight} bodies={m.body_count}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())

"""
Sculpt base (M5, early): the head the sculptor builds the clay face on.

Its surface is the skull's outside (head.py's envelope SKIN_T in from the proxy face, the
surface the silicone sits on) raised by SCULPT_MIN_SKIN, the thinnest the skin may be: the
sculptor can't carve the skin thinner than that, and the skin is that plus the clay. (The
mold core the skin is cast on is the skull's outside itself, made later, M5.) The whole
head is there (face, cranium, nape, neck); the ears and everything else of the character
are sculpted in clay. On it, at rest:

  eyes          the eyes sit behind the skull's outside (the lids' sphere, R 18.1, is 3.4
                under it), so each gets a socket: the skull's eye opening (EYE_OPEN_R round
                the eye axis) SCULPT_EYE_SOCKET under the skull's outside, its ceiling sloped
                (SCULPT_SOCKET_CEILING_DEG) so the upper piece prints upright without
                supports, with the lids' sphere in it and a dimple at its front pole (the
                gaze straight ahead)
  grooves       SCULPT_GROOVE wide and half as deep: the face's midline, the brow windows
                (where the moving brow pads sit under the skin), the outline of the skull's
                mouth opening (the lip plates sit behind it, LIP_SKIN_T under the skin) and
                the line where the lips meet (the stomion)

It stands on its neck on a separate base plate, SCULPT_PLATE[1] wider than the neck, with
conical registration keys for the mold and 4 holes to screw it to a board or turntable. 4 x
M4 bolts from under the plate on NECK_BOLT_SQUARE go into heat-set inserts in the neck.

Split for the bed at SKULL_SPLIT_Z into two solid pieces, joined by dowels and glue:

  sculpt_upper  the cranium, eyes and brows (prints upright, on its cut face)
  sculpt_lower  the rest of the face and the neck (prints upside down, on its cut face)
  sculpt_plate  the base plate

Print them solid: 3 walls and lightning infill (the slicer fills the inside).

Run:  python cad/sculpt_base.py  -> <stl_dir>/sculpt_*.stl
"""
import os
import sys

import manifold3d as mf
import numpy as np
import trimesh

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import cadkit as K  # noqa: E402
import geom as G  # noqa: E402
import head as H  # noqa: E402
import reserve as R  # noqa: E402
import skull as SK  # noqa: E402

P = K.params()
S = P.HEAD_SCALE
BIG = SK.BIG
INSET = P.SKIN_T - P.SCULPT_MIN_SKIN     # the base's surface, in from the proxy face


def socket_cutter(cx, cz, r, depth, outside=40.0):
    """An eye socket in the solid base: the circle on the surface, extruded out and `depth`
    in, each rim point along its normal turned horizontal, then tilted up more the higher on
    the circle it is, to SCULPT_SOCKET_CEILING_DEG at the top. Straight along the normal the
    ceiling was a 7.4 mm overhang printed upright; at 45 deg its corners, tilted sideways
    too, still were. The sides and floor stay square to the face. (Lowering only the inner
    rim of a normal_cutter() flattened the hull's ceiling to 11 deg.)"""
    xz = SK.circle(cx, cz, r)
    y = G.front_y(xz[:, 0], xz[:, 1], S, INSET)
    pts = np.column_stack([xz[:, 0], y, xz[:, 1]])
    n = np.column_stack(G._outer_normal(xz[:, 0], xz[:, 1], S))
    n[:, 2] = 0.0
    n /= np.linalg.norm(n, axis=1, keepdims=True)
    s = np.clip((xz[:, 1] - cz) / r, 0.0, 1.0)
    lift = np.tan(np.radians(P.SCULPT_SOCKET_CEILING_DEG)) * s
    v = n + np.column_stack([np.zeros_like(s), np.zeros_like(s), lift])
    v /= np.linalg.norm(v, axis=1, keepdims=True)
    return R.to_mf(trimesh.convex.convex_hull(np.vstack([pts + outside * v, pts - depth * v])))


def eyes():
    """(socket cutters, eye solids): the skull's eye opening SCULPT_EYE_SOCKET deep, and the
    lids' sphere with a pupil dimple at its front pole. Each socket stays inside the skull's
    own opening there (skull.openings(): the eye circle and the brow window, cut along the
    normal), so no clay goes where the skull has wall: cut along the horizontal normal alone,
    it reached 0.7 into the wall under the eye."""
    import brow_rig as BR
    ez = G.eye_z(S)
    r_lid = P.EYEMECH_EYE_R[1]
    wx0, wx1, wz0, wz1 = BR.window_bounds()
    sockets, solids = [], []
    for sx in (+1, -1):
        x = sx * P.EYE_SPACING / 2
        xa, xb = sorted((sx * wx0, sx * (wx1 + 1.5)))
        skull_opening = SK.normal_cutter(SK.hull(SK.circle(x, ez, P.EYE_OPEN_R),
                                                 SK.rounded_rectangle(xa, xb, wz0, wz1, 4.0)),
                                         inside=P.SCULPT_EYE_SOCKET)
        sockets.append(socket_cutter(x, ez, P.EYE_OPEN_R, P.SCULPT_EYE_SOCKET + P.SCULPT_MIN_SKIN)
                       ^ skull_opening)
        ball = mf.Manifold.sphere(r_lid, 96).translate((x, 0.0, ez))
        pupil = mf.Manifold.sphere(P.SCULPT_PUPIL / 2, 32).translate((x, r_lid, ez))
        solids.append(ball - pupil)
    return sockets, solids


def groove(points):
    """A groove along a polyline on the surface: hulls of small spheres at consecutive
    points, SCULPT_GROOVE wide, centred on the surface (so half as deep)."""
    r = P.SCULPT_GROOVE / 2
    ball = trimesh.creation.icosphere(subdivisions=1, radius=r).vertices
    segs = [mf.Manifold.hull_points(np.vstack([ball + a, ball + b]))
            for a, b in zip(points[:-1], points[1:])]
    return mf.Manifold.batch_boolean(segs, mf.OpType.Add)


def resample(points, step=1.5):
    pts = np.asarray(points, float)
    d = np.r_[0.0, np.cumsum(np.linalg.norm(np.diff(pts, axis=0), axis=1))]
    t = np.arange(0.0, d[-1], step)
    return np.column_stack([np.interp(t, d, pts[:, k]) for k in range(3)])


def on_face(xz):
    """(x, z) points on the front of the face -> points on the base's surface."""
    xz = np.asarray(xz, float)
    return np.column_stack([xz[:, 0], G.front_y(xz[:, 0], xz[:, 1], S, INSET), xz[:, 1]])


def midline(core_mesh):
    """The face's midline: the x = 0 section of the base, in front of SKULL_SPLIT_Y and
    above the neck's foot, ordered from the crown down to the neck."""
    segs = trimesh.intersections.mesh_plane(core_mesh, (1.0, 0.0, 0.0), (0.0, 0.0, 0.0))
    loop = max(SK.chain(segs), key=len)
    keep = (loop[:, 1] >= P.SKULL_SPLIT_Y) & (loop[:, 2] >= 10.0)
    # the kept run may wrap round the loop's start: roll so it starts after a gap
    k = int(np.argmin(keep))
    loop, keep = np.roll(loop, -k, axis=0), np.roll(keep, -k)
    run = loop[keep]
    if run[0, 2] < run[-1, 2]:
        run = run[::-1]
    return resample(run)


def face_marks(parts_lips_x):
    """The brow windows, the skull's mouth opening outline and the stomion line, on the face."""
    import brow_rig as BR

    def closed(outline):
        return resample(on_face(np.vstack([outline, outline[:1]])))

    wx0, wx1, wz0, wz1 = BR.window_bounds()
    marks = []
    for sx in (+1, -1):
        xa, xb = sorted((sx * wx0, sx * wx1))
        marks.append(closed(SK.rounded_rectangle(xa, xb, wz0, wz1, 4.0)))
    marks.append(closed(SK.rounded_rectangle(-P.MOUTH_OPEN_X, P.MOUTH_OPEN_X, *P.MOUTH_OPEN_Z, 6.0)))
    zs = G.stomion(S)[2]
    x0, x1 = parts_lips_x
    marks.append(resample(on_face(np.column_stack([np.linspace(x0, x1, 60), np.full(60, zs)]))))
    return marks


def lip_extent():
    """x range of the Cogley lip plates (the mouth's width) at rest."""
    import layout_check as L
    base_scale, parts = L.load_parts()
    L.place(parts, base_scale, S)
    names = set(P.UPPER_LIP_PLATES) | set(P.LOWER_LIP_PLATES)
    b = [p["m"].bounds for p in parts if p["module"] == "mouth" and p["label"] in names]
    return min(x[0][0] for x in b), max(x[1][0] for x in b)


def plate(core):
    """The base plate under the neck: (plate, neck centre (x, y), insert holes)."""
    t, margin = P.SCULPT_PLATE
    foot = core.slice(0.5)
    lo, hi = np.array(foot.bounds()[:2]), np.array(foot.bounds()[2:])
    cx, cy = (lo + hi) / 2
    # simplified: the round offset left near-duplicate points that fused when the STL was
    # read back with merged vertices, and opened the mesh
    body = foot.offset(margin, mf.JoinType.Round).simplify(0.05).extrude(t).translate((0.0, 0.0, -t))
    cuts, inserts = [], []
    h = P.NECK_BOLT_SQUARE / 2
    cd, cdepth = P.SCULPT_PLATE_CBORE
    for dx in (-h, h):
        for dy in (-h, h):
            x, y = cx + dx, cy + dy
            cuts.append(SK.cyl(P.M4_CLEAR / 2, (x, y, -t - 1.0), (x, y, 1.0)))
            cuts.append(SK.cyl(cd / 2, (x, y, -t - 1.0), (x, y, -t + cdepth)))     # head under the plate
            inserts.append(SK.cyl(P.M4_INSERT_HOLE / 2, (x, y, -1.0), (x, y, P.M4_INSERT_DEPTH)))
    # registration keys (cones into the top face) and board screws, in the margin round the neck
    half = (hi - lo) / 2
    key_d, key_h = P.SCULPT_KEY
    for ang in np.radians([0, 90, 180, 270]):
        d = np.array([np.cos(ang), np.sin(ang)])
        q = np.array([cx, cy]) + d * (np.abs(d) @ half + margin / 2)
        cone = trimesh.creation.cone(key_d / 2, key_h + 0.01, sections=48)
        cone.apply_transform(trimesh.transformations.rotation_matrix(np.pi, (1, 0, 0)))   # apex down
        cone.apply_translation((q[0], q[1], 0.01))
        cuts.append(R.to_mf(cone))
    for ang in np.radians([45, 135, 225, 315]):
        d = np.array([np.cos(ang), np.sin(ang)])
        q = np.array([cx, cy]) + d * half + d * margin * 0.55
        cuts.append(SK.cyl(P.SCULPT_BOARD_SCREW / 2, (q[0], q[1], -t - 1.0), (q[0], q[1], 1.0)))
    return body - mf.Manifold.batch_boolean(cuts, mf.OpType.Add), (cx, cy), inserts


def dowels():
    """Dowel holes across the split, both halves: SCULPT_DOWEL (diameter, depth each side)."""
    d, depth = P.SCULPT_DOWEL
    z = P.SKULL_SPLIT_Z
    return [SK.cyl(d / 2, (x, y, z - depth), (x, y, z + depth)) for x, y in P.SCULPT_DOWELS_XY]


def pieces():
    core = R.to_mf(H.envelope(S, INSET))
    core_mesh = R.from_mf(core)
    sockets, eye_solids = eyes()
    body = core - mf.Manifold.batch_boolean(sockets, mf.OpType.Add)
    body = mf.Manifold.batch_boolean([body] + eye_solids, mf.OpType.Add)
    marks = [midline(core_mesh)] + face_marks(lip_extent())
    grooves = mf.Manifold.batch_boolean([groove(m) for m in marks], mf.OpType.Add)
    # the brow windows' grooves stop short of the sockets: crossing the rim they left 0.03 slivers
    near = [socket_cutter(sx * P.EYE_SPACING / 2, G.eye_z(S), P.EYE_OPEN_R + P.SCULPT_GROOVE_GAP,
                          P.SCULPT_EYE_SOCKET + P.SCULPT_MIN_SKIN + 2.0) for sx in (+1, -1)]
    body -= grooves - mf.Manifold.batch_boolean(near, mf.OpType.Add)
    base, _, inserts = plate(core)
    for x, y in P.SCULPT_DOWELS_XY:                  # each dowel well inside the cut face
        m = G.envelope_margin(np.array([[x, y, P.SKULL_SPLIT_Z]]), S, INSET)[0]
        assert m >= P.SCULPT_DOWEL[0], f"dowel at ({x}, {y}) only {m:.1f} inside the surface"
    body -= mf.Manifold.batch_boolean(dowels() + inserts, mf.OpType.Add)
    z = P.SKULL_SPLIT_Z
    return {
        "sculpt_upper": body ^ SK.box((-BIG, -BIG, z), (BIG, BIG, BIG)),
        "sculpt_lower": body ^ SK.box((-BIG, -BIG, -BIG), (BIG, BIG, z)),
        "sculpt_plate": base,
    }


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
              f"watertight={m.is_watertight} bodies={m.body_count}  {m.volume / 1000:.0f} cm3")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())

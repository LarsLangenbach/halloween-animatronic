"""
Sculpt base v2 (M5, D17): the head the sculptor builds the clay face on, made from Will
Cogley's complete head (cogley_head.py: his outer shell, frame, cheek bone, eyes, brows and
mouth at rest).

The surface is a wrap of all his parts, SCULPT_MIN_SKIN out from them: the clay on it plus
that is the skin, and no part of his head can poke through a skin sculpted on it.
  tight wrap    closed by SCULPT_TIGHT[0]: hugs every part
  smooth wrap   closed by SCULPT_SMOOTH[0] and blurred: a head-like form. At the face it is
                inflated by SCULPT_FACE_INFLATE so it swallows the mechanism's lumps, except
                near the lips, brows and lids (SCULPT_MOVING_CLEAR), where the skin must stay
                thin to move with them
  the two are blended (soft union, SCULPT_BLEND), so the tight wrap shows only where a part
  would otherwise poke through.

On it:
  eyes      a socket in front of each eye, SCULPT_EYE_CAP behind the lids' front, showing the
            lids' sphere (R 18.1) at the true eye position, with a pupil dimple (gaze ahead);
            the socket stops at his other parts, and its ceiling slopes
            (SCULPT_SOCKET_CEILING_DEG) so the piece prints upright
  grooves   sculpting guides, SCULPT_GROOVE wide and half as deep:
              midline
              eye line through both eye centres
              brow line along his brow bars
              nose: the bottom of the nose, 0.7 of the way from the eyes to the lips, and its
                    width (the inner eye corners)
              mouth: the lip line (between his lip plates) and both corners
              chin: the lips sit a third of the way from the nose to the chin
              hairline: the forehead as tall as the nose-to-chin third
              ears: from the brow line down to the nose line, behind the jaw
  neck      an elliptic stub (SCULPT_NECK, ASSUMPTION until the neck is designed, Q17)

It stands on a separate base plate (SCULPT_PLATE wider than the neck) with conical mold
keys and 4 board holes; 4 x M4 from under the plate on NECK_BOLT_SQUARE go into inserts in
the neck. Split at SCULPT_SPLIT_Z for the bed into two pieces joined by dowels and glue:

  sculpt_upper  the cranium and the eyes (prints upright, on its cut face)
  sculpt_lower  the mouth, chin and neck (prints upside down, on its cut face)
  sculpt_plate  the base plate

Print them solid: 3 walls and lightning infill.

Run:  python cad/sculpt_base.py  -> <stl_dir>/sculpt_*.stl, output/ref/sculpt/wrap.stl
"""
import os
import sys

import manifold3d as mf
import numpy as np
import trimesh
from scipy import ndimage

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import cadkit as K  # noqa: E402
import cogley_head as C  # noqa: E402
import geom as G  # noqa: E402
import reserve as R  # noqa: E402
import wrap as W  # noqa: E402

sys.stdout.reconfigure(encoding="utf-8")
P = K.params()
S = P.HEAD_SCALE
BIG = 1000.0
UPPER_LIPS = ("UpperLeftLip", "Part 34")
LOWER_LIPS = ("LowerLeftLip", "Part 37")
BROW_BARS = ("Part 11", "Part 14")


def box(lo, hi):
    lo, hi = np.asarray(lo, float), np.asarray(hi, float)
    return mf.Manifold.cube(hi - lo).translate(lo)


def cyl(r, a, b, sections=48):
    return R.to_mf(trimesh.creation.cylinder(radius=r, segment=[a, b], sections=sections))


def neck_mesh():
    ax, ay, cy, z0 = P.SCULPT_NECK
    m = trimesh.creation.cylinder(radius=1.0, height=160.0, sections=96)
    m.apply_scale((ax, ay, 1.0))
    m.apply_translation((0.0, cy, z0 + 80.0))
    return m


def smin(a, b, k):
    hh = np.clip(k - np.abs(a - b), 0.0, None) / k
    return np.minimum(a, b) - hh * hh * k / 4.0


def wrap_surface(parts):
    """The base's surface (a trimesh): the soft union of the tight and the smooth wraps,
    SCULPT_MIN_SKIN out, cut flat at the neck's bottom."""
    h = P.SCULPT_GRID
    meshes = [m for *_, m in parts] + [neck_mesh()]
    b = np.array([m.bounds for m in meshes])
    pad = P.SCULPT_SMOOTH[0] + 18.0
    z0 = P.SCULPT_NECK[3]
    lo = np.array([b[:, 0, 0].min() - pad, b[:, 0, 1].min() - pad, z0 - 4.0])
    hi = b[:, 1].max(axis=0) + pad
    shape = tuple(np.ceil((hi - lo) / h).astype(int) + 1)
    occ = W.occupancy(meshes, lo, shape, h)
    moving = [m for n, k, g, m in parts if (g == "mouth" and n in UPPER_LIPS + LOWER_LIPS + ("JawBase",))
              or (g == "brows" and n in BROW_BARS) or (g == "eyes" and n.startswith(("Lid", "Component74")))]
    occ_moving = W.occupancy(moving, lo, shape, h)
    floor = int(round(4.0 / h))                                          # z0: the neck's flat bottom

    def closed(r):
        sol = W.closed_solid(occ, h, r)
        sol[:, :, :floor] = False
        return W.signed_distance(sol, h)

    tight = ndimage.gaussian_filter(closed(P.SCULPT_TIGHT[0]), P.SCULPT_TIGHT[1])
    smooth = ndimage.gaussian_filter(closed(P.SCULPT_SMOOTH[0]), P.SCULPT_SMOOTH[1])
    y = lo[1] + np.arange(shape[1]) * h
    f0, f1 = P.SCULPT_FACE_FADE_Y
    face = np.clip((y - f0) / (f1 - f0), 0.0, 1.0)[None, :, None]
    near, full = P.SCULPT_MOVING_CLEAR
    d_move = ndimage.distance_transform_edt(~occ_moving) * h
    away = np.clip((d_move - near) / full, 0.0, 1.0)
    F = smin(smooth - P.SCULPT_FACE_INFLATE * face * away, tight, P.SCULPT_BLEND)
    # a light last blur: a crevice narrower than a voxel (the midline between the lips and
    # between the brow bars) put two sheets in one cell and pinched the surface there
    F = ndimage.gaussian_filter(F, 1.0)
    for sl in ((slice(0, 2),), (slice(-2, None),), (slice(None), slice(0, 2)), (slice(None), slice(-2, None)),
               (slice(None), slice(None), slice(0, 2)), (slice(None), slice(None), slice(-2, None))):
        F[sl] = 50.0                                                     # closed at the grid's edges
    m = W.surface_nets(F, lo, h, level=P.SCULPT_MIN_SKIN)
    trimesh.smoothing.filter_taubin(m, iterations=10)
    body = R.to_mf(m) ^ box((-BIG, -BIG, z0), (BIG, BIG, BIG))
    # the tight wrap alone (his parts + SCULPT_MIN_SKIN, no inflation): what the face mask
    # must clear
    T = ndimage.gaussian_filter(tight, 1.0)
    for sl in ((slice(0, 2),), (slice(-2, None),), (slice(None), slice(0, 2)), (slice(None), slice(-2, None)),
               (slice(None), slice(None), slice(0, 2)), (slice(None), slice(None), slice(-2, None))):
        T[sl] = 50.0
    out_ref = os.path.join(G.ref_dir(), "sculpt")
    os.makedirs(out_ref, exist_ok=True)
    W.surface_nets(T, lo, h, level=P.SCULPT_MIN_SKIN).export(os.path.join(out_ref, "tight.stl"))
    return body


def ray_onto(mesh, origins, direction):
    """Where rays from the origins along direction first hit the mesh: (points, normals, ok)."""
    d = np.tile(np.asarray(direction, float), (len(origins), 1))
    loc, ri, ti = mesh.ray.intersects_location(origins, d, multiple_hits=False)
    pts = np.full((len(origins), 3), np.nan)
    nrm = np.full((len(origins), 3), np.nan)
    pts[ri] = loc
    nrm[ri] = mesh.face_normals[ti]
    return pts, nrm, ~np.isnan(pts[:, 0])


def on_front(mesh, xz):
    """(x, z) points -> points on the base's front (rays toward -y from in front)."""
    xz = np.asarray(xz, float)
    o = np.column_stack([xz[:, 0], np.full(len(xz), 400.0), xz[:, 1]])
    pts, _, ok = ray_onto(mesh, o, (0.0, -1.0, 0.0))
    return pts[ok]


def on_side(mesh, yz, sx):
    """(y, z) points -> points on the base's side (rays toward the midline from x = sx * 400)."""
    yz = np.asarray(yz, float)
    o = np.column_stack([np.full(len(yz), sx * 400.0), yz[:, 0], yz[:, 1]])
    pts, _, ok = ray_onto(mesh, o, (-sx, 0.0, 0.0))
    return pts[ok]


def socket_cutter(mesh, cx, cz, r, depth, outside=40.0):
    """An eye socket: the circle projected onto the base's front, cut `depth` in along each rim
    point's normal turned level, tilted up more the higher on the circle (to the ceiling angle
    at the top), so the ceiling prints without supports."""
    a = np.linspace(0.0, 2 * np.pi, 96, endpoint=False)
    xz = np.column_stack([cx + r * np.cos(a), cz + r * np.sin(a)])
    o = np.column_stack([xz[:, 0], np.full(len(xz), 400.0), xz[:, 1]])
    pts, nrm, ok = ray_onto(mesh, o, (0.0, -1.0, 0.0))
    pts, nrm, xz = pts[ok], nrm[ok], xz[ok]
    n = nrm.copy()
    n[:, 2] = 0.0
    n /= np.linalg.norm(n, axis=1, keepdims=True)
    s = np.clip((xz[:, 1] - cz) / r, 0.0, 1.0)
    v = n + np.column_stack([np.zeros_like(s), np.zeros_like(s), np.tan(np.radians(P.SCULPT_SOCKET_CEILING_DEG)) * s])
    v /= np.linalg.norm(v, axis=1, keepdims=True)
    return R.to_mf(trimesh.convex.convex_hull(np.vstack([pts + outside * v, pts - depth * v])))


def eyes(mesh, parts):
    """(socket cutters, eye solids, socket outlines for the grooves to keep clear of)."""
    ez = G.eye_z(S)
    r_lid = P.EYEMECH_EYE_R[1]
    others = [R.to_mf(m) for n, k, g, m in parts if g in ("frame", "extras", "brows", "mouth", "shell")
              and m.is_watertight and np.all(m.bounds[0] < [80, 40, ez + 40]) and np.all(m.bounds[1] > [-80, -40, ez - 40])]
    keep_out = mf.Manifold.batch_boolean(others, mf.OpType.Add) if others else None
    sockets, solids, near = [], [], []
    for sx in (+1, -1):
        x = sx * P.EYE_SPACING / 2
        (front,), _, _ = ray_onto(mesh, np.array([[x, 400.0, ez]]), (0.0, -1.0, 0.0))
        depth = front[1] - r_lid + P.SCULPT_EYE_CAP
        cut = socket_cutter(mesh, x, ez, P.EYE_OPEN_R, depth)
        if keep_out is not None:
            cut -= keep_out                                              # never into his other parts
        sockets.append(cut)
        near.append(socket_cutter(mesh, x, ez, P.EYE_OPEN_R + P.SCULPT_GROOVE_GAP, depth + 2.0))
        ball = mf.Manifold.sphere(r_lid, 96).translate((x, 0.0, ez))
        pupil = mf.Manifold.sphere(P.SCULPT_PUPIL / 2, 32).translate((x, r_lid, ez))
        solids.append(ball - pupil)
    return sockets, solids, near


def groove(points):
    """A groove along a polyline on the surface: hulls of spheres at consecutive points."""
    r = P.SCULPT_GROOVE / 2
    ball = trimesh.creation.icosphere(subdivisions=1, radius=r).vertices
    pts = resample(points)
    segs = [mf.Manifold.hull_points(np.vstack([ball + a, ball + b])) for a, b in zip(pts[:-1], pts[1:])]
    return mf.Manifold.batch_boolean(segs, mf.OpType.Add)


def resample(points, step=1.5):
    pts = np.asarray(points, float)
    d = np.r_[0.0, np.cumsum(np.linalg.norm(np.diff(pts, axis=0), axis=1))]
    t = np.arange(0.0, d[-1] + 1e-9, step)
    return np.column_stack([np.interp(t, d, pts[:, k]) for k in range(3)])


def landmarks(parts):
    """Heights and widths of the face guides, from his parts and standard proportions."""
    lip = {n: m for n, k, g, m in parts if n in UPPER_LIPS + LOWER_LIPS}
    upper_bottom = min(lip[n].bounds[0][2] for n in UPPER_LIPS if n in lip)
    lower_top = max(lip[n].bounds[1][2] for n in LOWER_LIPS if n in lip)
    mouth_x = max(max(abs(lip[n].bounds[0][0]), abs(lip[n].bounds[1][0])) for n in lip)
    bars = [m for n, k, g, m in parts if n in BROW_BARS]
    ez = G.eye_z(S)
    st = (upper_bottom + lower_top) / 2                              # where the lips meet
    nose = ez - 0.7 * (ez - st)                                      # bottom of the nose
    chin = st - 2.0 * (nose - st)                                    # lips a third of the way down
    brow_line = []                                                   # along the brow bars' fronts
    for bar in bars:
        v = bar.vertices
        xs = np.arange(np.ceil(v[:, 0].min()) + 2, np.floor(v[:, 0].max()) - 2, 2.0)
        for x in xs:
            sel = v[np.abs(v[:, 0] - x) < 1.0]
            front = sel[sel[:, 1] > sel[:, 1].max() - 2.0]
            brow_line.append((x, float(front[:, 2].mean())))
    brow_line.sort()
    glabella = min(z for x, z in brow_line if abs(x) < 30) if brow_line else ez + 25.0
    hair = glabella + (nose - chin)
    inner_corner = P.EYE_SPACING / 2 - 0.45 * 2 * P.EYEMECH_EYE_R[1]   # the lids' inner edge
    return dict(eye=ez, stomion=st, nose=nose, chin=chin, glabella=glabella, hair=hair,
                mouth_x=mouth_x, inner_corner=inner_corner, brow_line=brow_line)


def guides(mesh, parts):
    """The sculpting guide polylines on the base's surface, and the landmarks."""
    lm = landmarks(parts)
    out = []
    # midline: the x = 0 section in front of the ears, above the neck's foot
    import skull as SK                                                # its chain() joins section segments
    segs = trimesh.intersections.mesh_plane(mesh, (1.0, 0.0, 0.0), (0.0, 0.0, 0.0))
    loop = max(SK.chain(segs), key=len)
    keep = (loop[:, 1] >= P.SCULPT_FACE_FADE_Y[0]) & (loop[:, 2] >= P.SCULPT_NECK[3] + 15.0)
    k = int(np.argmin(keep))
    loop, keep = np.roll(loop, -k, axis=0), np.roll(keep, -k)
    out.append(loop[keep])
    xs = np.linspace(-80.0, 80.0, 161)

    def front_line(z, x0, x1):
        xx = xs[(xs >= x0) & (xs <= x1)]
        return on_front(mesh, np.column_stack([xx, np.full(len(xx), z)]))

    out.append(front_line(lm["eye"], -78.0, 78.0))                                    # eye line
    for side in (+1, -1):                                                              # brow line
        bl = np.array([(x, z) for x, z in lm["brow_line"] if np.sign(x) == side])
        if len(bl) > 2:
            # a smooth curve through the bar's front (the TPU bar's pleats made it wiggle)
            fit = np.polyfit(bl[:, 0], bl[:, 1], 2)
            xx = np.linspace(bl[:, 0].min(), bl[:, 0].max(), 40)
            out.append(on_front(mesh, np.column_stack([xx, np.polyval(fit, xx)])))
    out.append(front_line(lm["nose"], -lm["inner_corner"], lm["inner_corner"]))         # nose bottom
    for sx in (+1, -1):                                                                # nose width
        out.append(on_front(mesh, np.column_stack([np.full(12, sx * lm["inner_corner"]),
                                                   np.linspace(lm["nose"], lm["nose"] + 18.0, 12)])))
    out.append(front_line(lm["stomion"], -lm["mouth_x"], lm["mouth_x"]))                # lip line
    for sx in (+1, -1):                                                                # mouth corners
        out.append(on_front(mesh, np.column_stack([np.full(8, sx * lm["mouth_x"]),
                                                   np.linspace(lm["stomion"] - 6.0, lm["stomion"] + 6.0, 8)])))
    out.append(front_line(lm["chin"], -25.0, 25.0))                                   # chin
    out.append(front_line(lm["hair"], -55.0, 55.0))                                   # hairline
    top, bottom = lm["glabella"], lm["nose"]                                           # ears
    height = top - bottom
    y0 = P.SCULPT_FACE_FADE_Y[0] - 10.0
    rect = [(y0, top), (y0 - 0.55 * height, top), (y0 - 0.55 * height, bottom), (y0, bottom), (y0, top)]
    for sx in (+1, -1):
        edge = []
        for (ya, za), (yb, zb) in zip(rect[:-1], rect[1:]):
            n = 20
            edge += [(ya + (yb - ya) * t, za + (zb - za) * t) for t in np.linspace(0, 1, n, endpoint=False)]
        edge.append(rect[-1])
        out.append(on_side(mesh, np.array(edge), sx))
    return [o for o in out if len(o) > 2], lm


def plate(body):
    """The base plate under the neck: (plate, insert holes in the neck)."""
    t, margin = P.SCULPT_PLATE
    z0 = P.SCULPT_NECK[3]
    foot = body.slice(z0 + 0.5)
    lo, hi = np.array(foot.bounds()[:2]), np.array(foot.bounds()[2:])
    cx, cy = (lo + hi) / 2
    base = foot.offset(margin, mf.JoinType.Round).simplify(0.05).extrude(t).translate((0.0, 0.0, z0 - t))
    cuts, inserts = [], []
    h = P.NECK_BOLT_SQUARE / 2
    cd, cdepth = P.SCULPT_PLATE_CBORE
    for dx in (-h, h):
        for dy in (-h, h):
            x, y = cx + dx, cy + dy
            cuts.append(cyl(P.M4_CLEAR / 2, (x, y, z0 - t - 1.0), (x, y, z0 + 1.0)))
            cuts.append(cyl(cd / 2, (x, y, z0 - t - 1.0), (x, y, z0 - t + cdepth)))
            inserts.append(cyl(P.M4_INSERT_HOLE / 2, (x, y, z0 - 1.0), (x, y, z0 + P.M4_INSERT_DEPTH)))
    half = (hi - lo) / 2
    key_d, key_h = P.SCULPT_KEY
    for ang in np.radians([0, 90, 180, 270]):
        d = np.array([np.cos(ang), np.sin(ang)])
        q = np.array([cx, cy]) + d * (np.abs(d) @ half + margin / 2)
        cone = trimesh.creation.cone(key_d / 2, key_h + 0.01, sections=48)
        cone.apply_transform(trimesh.transformations.rotation_matrix(np.pi, (1, 0, 0)))
        cone.apply_translation((q[0], q[1], z0 + 0.01))
        cuts.append(R.to_mf(cone))
    for ang in np.radians([45, 135, 225, 315]):
        d = np.array([np.cos(ang), np.sin(ang)])
        q = np.array([cx, cy]) + d * half + d * margin * 0.55
        cuts.append(cyl(P.SCULPT_BOARD_SCREW / 2, (q[0], q[1], z0 - t - 1.0), (q[0], q[1], z0 + 1.0)))
    return base - mf.Manifold.batch_boolean(cuts, mf.OpType.Add), inserts


def dowels(body_mesh):
    d, depth = P.SCULPT_DOWEL
    z = P.SCULPT_SPLIT_Z
    out = []
    for x, y in P.SCULPT_DOWELS_XY:
        q = np.array([[x, y, z]])
        assert body_mesh.contains(q)[0], f"dowel at ({x}, {y}) is outside the base at the split"
        gap = float(trimesh.proximity.closest_point(body_mesh, q)[1][0])
        assert gap >= d, f"dowel at ({x}, {y}) is only {gap:.1f} inside the base's surface"
        out.append(cyl(d / 2, (x, y, z - depth), (x, y, z + depth)))
    return out


def pieces():
    parts = C.load({"frame", "extras", "shell", "eyes", "mouth", "brows", "hardware"})
    body = wrap_surface(parts)
    surf = R.from_mf(body)
    out_ref = os.path.join(G.ref_dir(), "sculpt")
    os.makedirs(out_ref, exist_ok=True)
    surf.export(os.path.join(out_ref, "wrap.stl"))                    # the base's surface, for the checks
    sockets, solids, near = eyes(surf, parts)
    body = body - mf.Manifold.batch_boolean(sockets, mf.OpType.Add)
    body = mf.Manifold.batch_boolean([body] + solids, mf.OpType.Add)
    lines, lm = guides(surf, parts)
    print("guides (z): " + ", ".join(f"{k} {v:.1f}" for k, v in lm.items() if k != "brow_line"))
    grooves = mf.Manifold.batch_boolean([groove(p) for p in lines], mf.OpType.Add)
    body -= grooves - mf.Manifold.batch_boolean(near, mf.OpType.Add)
    base, inserts = plate(body)
    body -= mf.Manifold.batch_boolean(dowels(surf) + inserts, mf.OpType.Add)
    z = P.SCULPT_SPLIT_Z
    return {
        "sculpt_upper": body ^ box((-BIG, -BIG, z), (BIG, BIG, BIG)),
        "sculpt_lower": body ^ box((-BIG, -BIG, -BIG), (BIG, BIG, z)),
        "sculpt_plate": base,
    }


def main():
    out = K.stl_dir()
    os.makedirs(out, exist_ok=True)
    ok = True
    for name, man in pieces().items():
        # simplify: where grooves meet, manifold leaves vertices a hair apart that fuse when the
        # STL is read back (merged vertices) and open the mesh
        m = R.from_mf(man.simplify(0.01))
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

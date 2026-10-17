"""
Face mask (M5, D19): a thin shell of a man's face, its features where the mechanism puts
them: a reference piece to sculpt the skin on. It replaces the sculpt base.

Source face: the MakeHuman base mesh (inputs/reference/makehuman/base.obj, CC0): a
realistic, neutral adult. Its units are decimetres, +y up, the face toward +z.

  1. turn into our frame and scale it by MASK_SCALE (the head's own scale: Cogley's head is
     about 1.2 times a person's)
  2. warp it smoothly (thin-plate spline): the eye centres onto the EyeMech's eyes, the lips
     onto where Cogley's lip plates meet, the nose and mouth held at their natural width
     (MASK_FEATURE_SCALE), a man's jaw (MASK_MALE: wider jaw angles and chin, brow forward)
  3. read its skin as a radius over a grid of directions from a point inside the head
     (MASK_CENTRE_BACK behind the eyes): the outermost surface along each direction. That
     covers the face, the forehead and the front of the skull in one smooth sheet
  4. close it: where a direction looks into the eye openings or between the lips, the radius
     dips. Those dips are filled smoothly. The eyes become closed lids (a slight dome) with a
     lash line, and the lips get a lip line (MASK_LINE)
  5. move it forward, then push it out smoothly, wherever its outside would come within
     SCULPT_MIN_SKIN of Cogley's head (sculpt_base.py's tight wrap)
  6. trim it to a smooth egg outline (MASK_OUTLINE, in directions: half width, top and bottom
     elevation, egg) and thicken it MASK_T inward

Run:  python cad/face_mask.py  -> <stl_dir>/face_mask.stl
"""
import os
import sys

import numpy as np
import trimesh
from scipy import ndimage
from scipy.interpolate import RBFInterpolator, RegularGridInterpolator

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import cadkit as K  # noqa: E402
import cogley_head as C  # noqa: E402
import geom as G  # noqa: E402
import reserve as R  # noqa: E402

sys.stdout.reconfigure(encoding="utf-8")
P = K.params()
S = P.HEAD_SCALE
SRC = os.path.join(K.PROJECT, "inputs", "reference", "makehuman", "base.obj")


def read_makehuman():
    """(vertices mm in our frame, body faces, {joint: centre}) from MakeHuman's base.obj.
    Ours: x = -x_mh (a turn, not a mirror), y = z_mh (front), z = y_mh (up)."""
    V, groups, cur = [], {}, None
    with open(SRC, encoding="utf-8", errors="replace") as f:
        for line in f:
            if line.startswith("v "):
                V.append([float(t) for t in line.split()[1:4]])
            elif line.startswith("g "):
                cur = line[2:].strip()
                groups.setdefault(cur, [])
            elif line.startswith("f "):
                groups[cur].append([int(t.split("/")[0]) - 1 for t in line.split()[1:]])
    V = np.array(V) * 100.0
    V = np.column_stack([-V[:, 0], V[:, 2], V[:, 1]])
    tris = []
    for f in groups["body"]:
        tris += [(f[0], f[k], f[k + 1]) for k in range(1, len(f) - 1)]
    joints = {}
    for g in ("joint-l-eye", "joint-r-eye"):
        idx = np.unique(np.concatenate([np.array(f) for f in groups[g]]))
        joints[g] = V[idx].mean(axis=0)
    return V, np.array(tris), joints


def front_height(mesh, eye_y, ez, st=0.5):
    """The face seen from the front: the front-most y of the skin over an (x, z) grid, from
    dense surface samples (MakeHuman's mesh is too sparse to read point by point)."""
    near = (mesh.triangles_center[:, 1] > eye_y - 30.0) & (np.abs(mesh.triangles_center[:, 2] - ez) < 160.0)
    sub = mesh.submesh([np.where(near)[0]], append=True)
    pts = trimesh.sample.sample_surface(sub, int(sub.area * 25.0), seed=5)[0]
    xs = np.arange(-80.0, 80.0 + st, st)
    zs = np.arange(ez - 160.0, ez + 160.0 + st, st)
    ix = np.round((pts[:, 0] - xs[0]) / st).astype(int)
    iz = np.round((pts[:, 2] - zs[0]) / st).astype(int)
    ok = (ix >= 0) & (ix < len(xs)) & (iz >= 0) & (iz < len(zs))
    H = np.full((len(xs), len(zs)), -np.inf)
    np.maximum.at(H, (ix[ok], iz[ok]), pts[ok, 1])
    H[np.isinf(H)] = np.nan
    gaps = np.isnan(H)
    Hf = ndimage.maximum_filter(np.nan_to_num(H, nan=-1e9), size=3)
    H[gaps] = Hf[gaps]
    return xs, zs, ndimage.gaussian_filter(np.nan_to_num(H, nan=np.nanmin(H)), 0.7)


def landmarks(mesh, joints):
    """Eyes, lips (where they meet, and their corners), nose tip and wings, chin, jaw angles
    and brow, on MakeHuman's head in our frame (its own scale)."""
    v = mesh.vertices
    eyes = np.array([joints["joint-l-eye"], joints["joint-r-eye"]])
    ez, ey = eyes[:, 2].mean(), eyes[:, 1].mean()
    xs, zs, H = front_height(mesh, ey, ez)

    def at(x, z):
        return H[np.argmin(np.abs(xs - x)), np.argmin(np.abs(zs - z))]

    col = H[np.argmin(np.abs(xs))]
    sel = (zs > ez - 120.0) & (zs < ez - 20.0)
    k = np.where(sel)[0][np.argmax(col[sel])]
    nose = np.array([0.0, col[k], zs[k]])
    sel = (zs > nose[2] - 45.0) & (zs < nose[2] - 12.0)
    k = np.where(sel)[0][np.argmin(col[sel])]                        # the dent between the lips
    stomion = np.array([0.0, col[k], zs[k]])
    sel = (zs < stomion[2] - 25.0) & (zs > stomion[2] - 55.0)        # the chin's front, below the lower lip
    k = np.where(sel)[0][np.argmax(col[sel])]
    chin = np.array([0.0, col[k], zs[k]])
    # mouth corners: MakeHuman's closed lips barely show a slit, so the standard proportion,
    # the mouth 0.8 of the eye spacing wide
    corner = 0.4 * abs(eyes[0, 0] - eyes[1, 0])
    mouth = np.array([[sx * corner, at(sx * corner, stomion[2]), stomion[2]] for sx in (+1, -1)])
    zw = stomion[2] + 16.0                                            # nose wings, 16 above the lips
    row = np.array([at(x, zw) for x in xs])
    wing = max(abs(x) for x, h in zip(xs, row) if h > nose[1] - 16.0 and abs(x) < 30.0)
    wings = np.array([[sx * wing, at(sx * wing, zw), zw] for sx in (+1, -1)])
    band = v[(np.abs(v[:, 2] - (stomion[2] - 22.0)) < 2.0) & (v[:, 1] > ey - 40.0)]
    jaw = np.array([band[np.argmax(band[:, 0])], band[np.argmin(band[:, 0])]])
    brow = np.array([0.0, at(0.0, ez + 18.0), ez + 18.0])
    return dict(eyes=eyes, nose=nose, stomion=stomion, chin=chin, mouth=mouth, wings=wings, jaw=jaw, brow=brow)


def lip_target():
    """Where Cogley's lip plates meet, in our frame (z)."""
    lips = {n: m for n, k, g, m in C.load({"mouth"}) if n in ("UpperLeftLip", "Part 34", "LowerLeftLip", "Part 37")}
    upper = min(lips[n].bounds[0][2] for n in ("UpperLeftLip", "Part 34"))
    lower = max(lips[n].bounds[1][2] for n in ("LowerLeftLip", "Part 37"))
    return (upper + lower) / 2


def warp(mesh, lm):
    """Scale, then thin-plate-spline the landmarks onto the mechanism with a man's
    proportions and a natural nose and mouth. Returns the warped mesh, its eyes' y, notes."""
    ez = G.eye_z(S)
    st_z = lip_target()
    s = P.MASK_SCALE
    centre = np.array([0.0, lm["eyes"][:, 1].mean(), lm["eyes"][:, 2].mean()])

    def sim(p):
        return (np.asarray(p) - centre) * s + np.array([0.0, 0.0, ez])

    src, dst = [], []

    def pin(p, q):
        src.append(np.asarray(p, float))
        dst.append(np.asarray(q, float))

    for e in lm["eyes"]:                                              # eyes onto the EyeMech's
        pin(sim(e), (np.sign(e[0]) * P.EYE_SPACING / 2, sim(e)[1], ez))
    st = sim(lm["stomion"])
    dz = st_z - st[2]                                                 # the lips move this far up
    pin(st, (0.0, st[1], st_z))
    nose = sim(lm["nose"])                                            # nose: same share of eyes-to-lips
    f = (ez - nose[2]) / (ez - st[2])
    nose_z = ez - f * (ez - st_z)
    pin(nose, (0.0, nose[1], nose_z))
    nat = P.MASK_FEATURE_SCALE                                        # natural mouth and nose widths
    for m in lm["mouth"]:
        q = sim(m)
        pin(q, (m[0] * nat, q[1], q[2] + dz))
    for w in lm["wings"]:
        q = sim(w)
        pin(q, (w[0] * nat, q[1], nose_z - (nose[2] - q[2]) * nat / s))
    wide, fwd = P.MASK_MALE
    chin = sim(lm["chin"])                                            # chin: same drop below the lips
    pin(chin, chin + (0.0, 2.0, dz))
    for j in lm["jaw"]:                                               # a man's jaw: wider, squarer
        q = sim(j)
        pin(q, q + (np.sign(q[0]) * wide, 0.0, dz))
    for sx in (+1, -1):                                               # chin corners wider too
        cc = chin + (sx * 14.0, -3.0, 4.0)
        pin(cc, cc + (sx * wide * 0.6, 1.0, dz))
    b = sim(lm["brow"])                                               # brow ridge forward
    pin(b, b + (0.0, fwd, 0.0))
    for p in ((0, -80, ez + 110), (0, -160, ez), (90, -60, ez), (-90, -60, ez), (0, -60, ez - 200),
              (0, 40, ez + 90), (70, 0, ez + 60), (-70, 0, ez + 60)):   # far anchors keep the head
        pin(p, p)
    src, dst = np.array(src), np.array(dst)
    rbf = RBFInterpolator(src, dst - src, kernel="thin_plate_spline")
    v = sim(mesh.vertices)
    v = v + rbf(v)
    eye_y = sim(lm["eyes"][0])[1]
    return trimesh.Trimesh(v, mesh.faces, process=False), eye_y, dict(
        scale=s, stomion=st_z, mouth=lm["mouth"][0, 0] * nat, wing=lm["wings"][0, 0] * nat)


def directions(phi, psi):
    """Unit vectors for azimuth phi (0 = straight ahead, +y; positive toward +x) and
    elevation psi (positive up), in degrees, broadcast."""
    a, e = np.radians(phi), np.radians(psi)
    return np.stack([np.cos(e) * np.sin(a), np.cos(e) * np.cos(a), np.sin(e)], axis=-1)


def outer_radius(mesh, c, phi, psi, per_mm2=6.0, reach=260.0):
    """The outermost radius of the mesh's surface in each direction from c (nan: nothing
    there): surface samples binned by direction, the farthest kept. (Rays through the
    500k-triangle wrap took over ten minutes.)"""
    near = np.linalg.norm(mesh.triangles_center - c, axis=1) < reach
    sub = mesh.submesh([np.where(near)[0]], append=True)
    pts = trimesh.sample.sample_surface(sub, int(sub.area * per_mm2), seed=3)[0]
    v = pts - c
    r = np.linalg.norm(v, axis=1)
    a = np.degrees(np.arctan2(v[:, 0], v[:, 1]))
    e = np.degrees(np.arcsin(np.clip(v[:, 2] / r, -1.0, 1.0)))
    st = phi[1] - phi[0]
    ia = np.round((a - phi[0]) / st).astype(int)
    ie = np.round((e - psi[0]) / st).astype(int)
    ok = (ia >= 0) & (ia < len(phi)) & (ie >= 0) & (ie < len(psi))
    grid = np.full((len(phi), len(psi)), -np.inf)
    np.maximum.at(grid, (ia[ok], ie[ok]), r[ok])
    grid[np.isinf(grid)] = np.nan
    gaps = np.isnan(grid)                                             # a cell no sample fell in
    filled = ndimage.maximum_filter(np.nan_to_num(grid, nan=-1.0), size=3)
    grid[gaps & (filled > 0)] = filled[gaps & (filled > 0)]
    return grid


def inpaint(r, bad, iters=1500):
    """Fill the cells marked bad with a smooth membrane (repeated neighbour averaging)."""
    r = r.copy()
    r[bad] = np.nanmean(r[~bad])
    for _ in range(iters):
        avg = 0.25 * (np.roll(r, 1, 0) + np.roll(r, -1, 0) + np.roll(r, 1, 1) + np.roll(r, -1, 1))
        r[bad] = avg[bad]
    return r


def skin(warped, wrap, c, eye_y):
    """The mask's outer skin as a radius over (phi, psi) from c: closed, smooth, clear of
    Cogley's head. Returns (phi, psi, radius grid, how far it was pushed out)."""
    st = P.MASK_GRID_DEG
    phi = np.arange(-100.0, 100.0 + st, st)
    psi = np.arange(-75.0, 88.0 + st, st)
    r = outer_radius(warped, c, phi, psi, per_mm2=20.0)
    # dips (the eye openings, between the lips) and misses: well below their neighbourhood
    filled = np.where(np.isnan(r), np.nanmedian(r), r)
    near = ndimage.median_filter(filled, size=int(round(8.0 / st)) * 2 + 1)
    bad = np.isnan(r) | (r < near - P.MASK_DIP)
    bad = ndimage.binary_dilation(bad, iterations=2)
    r = inpaint(r, bad)
    A, E = np.meshgrid(phi, psi, indexing="ij")
    ez = G.eye_z(S)
    lines = []
    lab, _ = ndimage.label(bad)
    for sx in (+1, -1):                                               # closed eyes
        eye = np.array([sx * P.EYE_SPACING / 2, eye_y, ez]) - c
        a = np.degrees(np.arctan2(eye[0], eye[1]))
        e = np.degrees(np.arcsin(eye[2] / np.linalg.norm(eye)))
        k = lab[np.argmin(np.abs(phi - a)), np.argmin(np.abs(psi - e))]
        if not k:
            continue
        region = lab == k
        dist = ndimage.distance_transform_edt(region)
        r += np.where(region, P.MASK_LID_DOME * np.sqrt(np.clip(dist / max(dist.max(), 1), 0, 1)), 0.0)
        cols = np.where(region.any(axis=1))[0]
        a0, a1 = phi[cols.min()], phi[cols.max()]
        la = np.linspace(a0 + 1.5, a1 - 1.5, 40)
        lines.append(("lash", la, e - 1.0 - 1.5 * np.sin(np.linspace(0, np.pi, 40))))
    r = ndimage.gaussian_filter(r, P.MASK_SMOOTH / st)
    st_z = lip_target()                                               # lip line
    lp = np.array([0.0, eye_y + 10.0, st_z]) - c
    e_l = np.degrees(np.arcsin(lp[2] / np.linalg.norm(lp)))
    half = np.degrees(np.arctan2(P.MASK_FEATURE_SCALE * 22.0, np.linalg.norm(lp[1:])))
    lines.append(("lip", np.linspace(-half, half, 40), np.full(40, e_l)))
    # clear of Cogley's head: the outside at least SCULPT_MIN_SKIN from his parts (a reference
    # to sculpt on: the clay goes on top, and the skin is cast on a core of his head)
    rw = ndimage.gaussian_filter(np.nan_to_num(outer_radius(wrap, c, phi, psi, per_mm2=10.0), nan=0.0), 2.0)
    need = np.clip(np.nan_to_num(rw + 0.5 - r, nan=0.0), 0.0, None)
    push = need.copy()
    for _ in range(8):                                                # a smooth envelope over it
        push = np.maximum(need, ndimage.gaussian_filter(push, P.MASK_BULGE / st))
    push = ndimage.gaussian_filter(push, P.MASK_PUSH_SMOOTH / st)
    r = r + push
    # the forehead and skull follow Cogley's faceted helmet: smooth them hard, fading in
    # above the brows (the face below keeps its detail)
    brow = np.array([0.0, eye_y + 12.0, ez + 25.0]) - c
    e_b = np.degrees(np.arcsin(brow[2] / np.linalg.norm(brow)))
    w = np.clip((E - e_b) / 12.0, 0.0, 1.0)
    r = (1 - w) * r + w * ndimage.gaussian_filter(r, P.MASK_TOP_SMOOTH / st)
    for kind, la, le in lines:                                        # grooves
        depth, w = P.MASK_LINE
        if kind == "lip":
            depth *= 1.3
        d2 = np.full(r.shape, np.inf)
        for a_, e_ in zip(la, le):
            d2 = np.minimum(d2, (A - a_) ** 2 + (E - e_) ** 2)
        r -= depth * np.exp(-d2 / (2 * w ** 2))
    return phi, psi, r, float(push.max())


def forward(warped, wrap, c):
    """How far to move the whole face forward so its middle (the eyes, nose and mouth) clears
    Cogley's head without local pushes, which made lumps: on a coarse grid of directions."""
    phi = np.arange(-35.0, 35.0 + 1.0, 1.0)
    psi = np.arange(-45.0, 25.0 + 1.0, 1.0)
    r = outer_radius(warped, c, phi, psi, per_mm2=2.0)
    rw = outer_radius(wrap, c, phi, psi, per_mm2=1.0)
    A, E = np.meshgrid(np.radians(phi), np.radians(psi), indexing="ij")
    ahead = np.cos(E) * np.cos(A)                                     # how much of a move along y is radial
    for dy in np.arange(0.0, 60.0, 0.5):
        need = np.nan_to_num(rw + 0.5 - (r + dy * ahead), nan=-1.0)
        if np.percentile(need, 100 * (1 - P.MASK_CORE_OK)) <= 0.0:
            return float(dy)
    return 60.0


def mesh_from(phi, psi, r, c):
    """The shell: the skin inside the egg outline, sampled on rings, thickened inward."""
    hw, top, bottom, egg = P.MASK_OUTLINE
    cz = (top + bottom) / 2
    hz = (top - bottom) / 2
    f = RegularGridInterpolator((phi, psi), r)
    nr, nt = 120, 480
    rho = np.linspace(0.0, 1.0, nr + 1)[1:]
    th = np.linspace(0.0, 2 * np.pi, nt, endpoint=False)
    Rh, Th = np.meshgrid(rho, th, indexing="ij")
    E = cz + hz * Rh * np.sin(Th)
    A = hw * Rh * np.cos(Th) * (1.0 + egg * Rh * np.sin(Th))
    rad = f(np.stack([A.ravel(), E.ravel()], axis=1)).reshape(A.shape)
    pts = c + directions(A, E) * rad[..., None]
    centre = c + directions(0.0, cz) * f([[0.0, cz]])[0]
    V = np.vstack([centre[None], pts.reshape(-1, 3)])

    def vid(i, j):
        return 1 + i * nt + (j % nt)

    F = [(0, vid(0, j + 1), vid(0, j)) for j in range(nt)]
    for i in range(nr - 1):
        for j in range(nt):
            a, b, cc, d = vid(i, j), vid(i, j + 1), vid(i + 1, j + 1), vid(i + 1, j)
            F += [(a, b, cc), (a, cc, d)]
    outer = trimesh.Trimesh(V, np.array(F), process=False)
    if (outer.face_normals[:, 1] > 0).mean() < 0.5:                   # face outward (+y at the front)
        outer.invert()
    sm = outer.copy()
    trimesh.smoothing.filter_laplacian(sm, lamb=0.5, iterations=10)
    inner = outer.vertices - sm.vertex_normals * P.MASK_T
    nv = len(V)
    rim = [vid(nr - 1, j) for j in range(nt)]
    side = []
    for j in range(nt):
        a, b = rim[j], rim[(j + 1) % nt]
        side += [(a, b, b + nv), (a, b + nv, a + nv)]
    m = trimesh.Trimesh(np.vstack([outer.vertices, inner]),
                        np.vstack([outer.faces, outer.faces[:, ::-1] + nv, np.array(side)]), process=True)
    trimesh.repair.fix_normals(m)
    return m


def build():
    V, F, joints = read_makehuman()
    head = trimesh.Trimesh(V, F, process=True)
    lm = landmarks(head, joints)
    warped, eye_y, info = warp(head, lm)
    ez = G.eye_z(S)
    c = np.array([0.0, eye_y - P.MASK_CENTRE_BACK, ez - 15.0])
    # his parts + SCULPT_MIN_SKIN (sculpt_base.py's tight wrap; its wrap.stl is inflated at the face)
    wrap = trimesh.load(os.path.join(G.ref_dir(), "sculpt", "tight.stl"), force="mesh")
    dy = forward(warped, wrap, c)
    warped.apply_translation((0.0, dy, 0.0))
    phi, psi, r, pushed = skin(warped, wrap, c, eye_y)
    shell = mesh_from(phi, psi, r, c)
    print(f"scale {info['scale']:.3f}; lips at z {info['stomion']:.1f}, mouth +-{info['mouth']:.1f}, "
          f"nose wings +-{info['wing']:.1f}; moved forward {dy:.1f}, then pushed out up to {pushed:.1f} mm")
    return shell


def main():
    shell = build()
    out = K.stl_dir()
    m = R.from_mf(R.to_mf(shell))
    m.merge_vertices()
    m.update_faces(m.nondegenerate_faces())
    m.remove_unreferenced_vertices()
    good = bool(m.is_watertight) and m.body_count == 1
    m.export(os.path.join(out, "face_mask.stl"))
    e = m.extents
    print(f"{'' if good else 'FAIL  '}wrote face_mask.stl  {e[0]:.1f} x {e[1]:.1f} x {e[2]:.1f} mm  "
          f"watertight={m.is_watertight} bodies={m.body_count}  {m.volume / 1000:.0f} cm3")
    return 0 if good else 1


if __name__ == "__main__":
    sys.exit(main())

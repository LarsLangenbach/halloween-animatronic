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
  4. the eyes and lips are MakeHuman's own: its eyelids, with its eyeballs (helper-l/r-eye)
     placed rigidly on the eye mechanism's eye centres and filling the openings, so open eyes
     without holes, marked with an iris ring and a pupil round each eye axis (MASK_IRIS); its
     lips, scaled evenly about where they meet so their corners reach just past the ends of
     Cogley's lip plates, the gap between them closed with a clean line (MASK_LIP_LINE)
  5. move it forward, then push it out smoothly, wherever its outside would come within
     SCULPT_MIN_SKIN of Cogley's head (sculpt_base.py's tight wrap)
  6. trim it to a smooth egg outline (MASK_OUTLINE, in directions: half width, top and bottom
     elevation, egg) and thicken it MASK_T inward (the inside a smooth surface of its own, never
     crossing the skin)

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
    for g in ("body", "helper-l-eye", "helper-r-eye"):                 # the skin, and its own eyeballs
        for f in groups[g]:
            tris += [(f[0], f[k], f[k + 1]) for k in range(1, len(f) - 1)]
    joints = {}
    # the eye centres: the middle of MakeHuman's eyeballs (its eye joints sit a little off),
    # and the eyeballs' vertices, placed rigidly later
    for g, h in (("joint-l-eye", "helper-l-eye"), ("joint-r-eye", "helper-r-eye")):
        idx = np.unique(np.concatenate([np.array(f) for f in groups[h]]))
        joints[g] = (V[idx].min(axis=0) + V[idx].max(axis=0)) / 2
        joints[h] = idx
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
    eyeballs = [joints["helper-l-eye"], joints["helper-r-eye"]]
    ez, ey = eyes[:, 2].mean(), eyes[:, 1].mean()
    xs, zs, H = front_height(mesh, ey, ez)

    def at(x, z):
        return H[np.argmin(np.abs(xs - x)), np.argmin(np.abs(zs - z))]

    col = H[np.argmin(np.abs(xs))]
    sel = (zs > ez - 120.0) & (zs < ez - 20.0)
    k = np.where(sel)[0][np.argmax(col[sel])]
    nose = np.array([0.0, col[k], zs[k]])
    # where the lips meet: the narrow dip between them (the crease under the nose is above the
    # window, the broad crease under the lower lip, which is deeper, below it)
    hp = H - ndimage.gaussian_filter1d(H, 4.0, axis=1)
    sel = (zs > nose[2] - 40.0) & (zs < nose[2] - 18.0)
    k = np.where(sel)[0][np.argmin(hp[np.argmin(np.abs(xs)), sel])]
    stomion = np.array([0.0, col[k], zs[k]])
    sel = (zs < stomion[2] - 25.0) & (zs > stomion[2] - 55.0)        # the chin's front, below the lower lip
    k = np.where(sel)[0][np.argmax(col[sel])]
    chin = np.array([0.0, col[k], zs[k]])
    # mouth corners: where that dip fades out sideways
    band = np.abs(zs - stomion[2]) < 7.0
    dip = -hp[:, band].min(axis=1)
    corner = min(max(abs(x) for x, d in zip(xs, dip) if d > 0.3 and sx * x > 0 and abs(x) < 45.0)
                 for sx in (+1, -1))
    mouth = np.array([[sx * corner, at(sx * corner, stomion[2]), stomion[2]] for sx in (+1, -1)])
    zw = stomion[2] + 16.0                                            # nose wings, 16 above the lips
    row = np.array([at(x, zw) for x in xs])
    wing = max(abs(x) for x, h in zip(xs, row) if h > nose[1] - 16.0 and abs(x) < 30.0)
    wings = np.array([[sx * wing, at(sx * wing, zw), zw] for sx in (+1, -1)])
    band = v[(np.abs(v[:, 2] - (stomion[2] - 22.0)) < 2.0) & (v[:, 1] > ey - 40.0)]
    jaw = np.array([band[np.argmax(band[:, 0])], band[np.argmin(band[:, 0])]])
    brow = np.array([0.0, at(0.0, ez + 18.0), ez + 18.0])
    sel = (zs > stomion[2]) & (zs < stomion[2] + 12.0)                # the lips' fronts
    k = np.where(sel)[0][np.argmax(col[sel])]
    upper = np.array([0.0, col[k], zs[k]])
    sel = (zs < stomion[2]) & (zs > stomion[2] - 14.0)
    k = np.where(sel)[0][np.argmax(col[sel])]
    lower = np.array([0.0, col[k], zs[k]])
    return dict(eyes=eyes, eyeballs=eyeballs, nose=nose, stomion=stomion, chin=chin, mouth=mouth, wings=wings,
                jaw=jaw, brow=brow, upper=upper, lower=lower)


def lip_half_width():
    """Half the mouth's width: the outer ends of Cogley's lip plates, plus MASK_MOUTH_PAST."""
    lips = [m for n, k, g, m in C.load({"mouth"}) if n in ("UpperLeftLip", "Part 34", "LowerLeftLip", "Part 37")]
    return max(max(abs(m.bounds[0][0]), abs(m.bounds[1][0])) for m in lips) + P.MASK_MOUTH_PAST


def lip_front():
    """The front of Cogley's lip plates (y)."""
    lips = [m for n, k, g, m in C.load({"mouth"}) if n in ("UpperLeftLip", "Part 34", "LowerLeftLip", "Part 37")]
    return max(m.bounds[1][1] for m in lips)


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
    nat = P.MASK_FEATURE_SCALE
    # the lips: MakeHuman's own, scaled evenly (across and up, not deeper) about where they
    # meet, so their corners reach just past the ends of Cogley's lip plates (team, 2026-10-16)
    half = lip_half_width()
    corner = sim(lm["mouth"][0])
    f_lip = half / abs(corner[0])
    for ux in (-1.0, -0.5, 0.0, 0.5, 1.0):
        for vz in (-10.0, -5.0, 0.0, 5.0, 10.0):
            q = st + (ux * abs(corner[0]), 0.0, vz)
            if abs(ux) == 1.0 and vz != 0.0:
                continue                                              # the corners themselves only
            pin(q, (q[0] * f_lip, q[1], st_z + vz * f_lip))
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
    # MakeHuman's eyeballs placed rigidly, exactly on the eye mechanism's eye centres (the
    # warp bent them, and their middles drifted up to 0.6 mm)
    for e, ids in zip(lm["eyes"], lm["eyeballs"]):
        target = np.array([np.sign(e[0]) * P.EYE_SPACING / 2, sim(e)[1], ez])
        v[ids] = (mesh.vertices[ids] - e) * s + target
    eye_y = sim(lm["eyes"][0])[1]
    return trimesh.Trimesh(v, mesh.faces, process=False), eye_y, dict(
        scale=s, stomion=st_z, mouth=half, wing=lm["wings"][0, 0] * nat, lip_scale=f_lip)


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


def radial_exact(mesh, c, phi, psi):
    """The outermost radius of the mesh in each direction from c, exactly: every triangle is
    rasterised over the (phi, psi) grid and its radius interpolated (a max-buffer). No
    sampling, so no grain to smooth away (smoothing it blurred the eyes and lips)."""
    v = mesh.vertices - c
    rr = np.linalg.norm(v, axis=1)
    aa = np.degrees(np.arctan2(v[:, 0], v[:, 1]))
    ee = np.degrees(np.arcsin(np.clip(v[:, 2] / rr, -1.0, 1.0)))
    f = mesh.faces
    A, E, Rr = aa[f], ee[f], rr[f]
    ok = (np.ptp(A, axis=1) < 30.0)                                   # not across the back seam
    A, E, Rr = A[ok], E[ok], Rr[ok]
    st = phi[1] - phi[0]
    fa, fe = (A - phi[0]) / st, (E - psi[0]) / st
    i0, j0 = np.floor(fa.min(axis=1)).astype(int), np.floor(fe.min(axis=1)).astype(int)
    wi = np.ceil(fa.max(axis=1)).astype(int) - i0
    wj = np.ceil(fe.max(axis=1)).astype(int) - j0
    grid = np.full((len(phi), len(psi)), -np.inf)
    (x0, y0), (x1, y1), (x2, y2) = (fa[:, 0], fe[:, 0]), (fa[:, 1], fe[:, 1]), (fa[:, 2], fe[:, 2])
    den = (y1 - y2) * (x0 - x2) + (x2 - x1) * (y0 - y2)
    den = np.where(np.abs(den) < 1e-12, 1e-12, den)
    for di in range(int(min(wi.max(), 12)) + 1):
        for dj in range(int(min(wj.max(), 12)) + 1):
            gi, gj = i0 + di, j0 + dj
            sel = (di <= wi) & (dj <= wj) & (gi >= 0) & (gi < len(phi)) & (gj >= 0) & (gj < len(psi))
            if not sel.any():
                continue
            px, py = gi[sel].astype(float), gj[sel].astype(float)
            l0 = ((y1 - y2)[sel] * (px - x2[sel]) + (x2 - x1)[sel] * (py - y2[sel])) / den[sel]
            l1 = ((y2 - y0)[sel] * (px - x2[sel]) + (x0 - x2)[sel] * (py - y2[sel])) / den[sel]
            l2 = 1.0 - l0 - l1
            inside = (l0 >= -1e-6) & (l1 >= -1e-6) & (l2 >= -1e-6)
            if not inside.any():
                continue
            rv = (l0 * Rr[sel, 0] + l1 * Rr[sel, 1] + l2 * Rr[sel, 2])[inside]
            np.maximum.at(grid, (gi[sel][inside], gj[sel][inside]), rv)
    grid[np.isinf(grid)] = np.nan
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
    phi = np.arange(-125.0, 125.0 + st, st)
    psi = np.arange(-75.0, 88.0 + st, st)
    r = radial_exact(warped, c, phi, psi)
    A, E = np.meshgrid(phi, psi, indexing="ij")
    ez = G.eye_z(S)

    def on_axis(r):
        """For each eye: the grid direction whose skin point lies on the eye mechanism's eye
        axis (x = +-EYE_SPACING/2 at eye height, along y), and every skin point's distance
        from that axis, mm (far off for points not on the eye's front)."""
        pts = c + directions(A, E) * r[..., None]
        out = []
        for sx in (+1, -1):
            rho = np.hypot(pts[..., 0] - sx * P.EYE_SPACING / 2, pts[..., 2] - ez)
            rho = np.where(pts[..., 1] > c[1] + 40.0, rho, 1e3)
            i, j = np.unravel_index(np.argmin(rho), rho.shape)
            out.append((sx, phi[i], psi[j], rho))
        return out

    r = inpaint(r, np.isnan(r))                                       # directions that missed
    eyes = [(sx, a, e) for sx, a, e, _ in on_axis(r)]
    # the lips: MakeHuman's mouth is a little open, and traced into, the gap came out as a
    # jagged, tooth-like edge. Close it (a grey closing up and down, within the mouth) and cut
    # a clean line where the lips meet, along the gap's own curve, fading out at the corners
    st_z = lip_target()
    i0 = int(np.argmin(np.abs(phi)))
    z0 = c[2] + np.sin(np.radians(psi)) * r[i0]
    j0 = int(np.argmin(np.where(psi < 0.0, np.abs(z0 - st_z), np.inf)))
    e_l = psi[j0]                                                     # the lips, seen from c
    k_l = np.radians(1.0) * r[i0, j0]                                 # mm per degree there
    half = lip_half_width()
    mouth = (np.abs(A) * k_l < half + 6.0) & (np.abs(E - e_l) * k_l < P.MASK_LIP_ZONE)
    closed = ndimage.grey_closing(r, size=(1, int(round(4.0 / (k_l * st))) | 1))
    gap = np.where(mouth, closed - r, 0.0)
    wm = np.clip(ndimage.gaussian_filter(mouth.astype(float), 1.0 / (k_l * st)) * 2.0, 0.0, 1.0)
    r = r + wm * (closed - r)
    cols = gap.max(axis=1) > 0.3
    a_c = np.abs(phi[cols]).max()                                     # the corners
    e_s = np.polyfit(phi[cols], psi[np.argmax(gap[cols], axis=1)], 4, w=np.sqrt(gap.max(axis=1)[cols]))
    line = np.polyval(e_s, A)
    band = (np.abs(E - line) * k_l < 1.2) & (np.abs(A) < a_c + 1.0 / k_l)
    band |= ndimage.binary_dilation(gap > 0.15, iterations=2)
    r = inpaint(r, band & mouth, iters=600)                           # no comb of ridges along it
    # the lips flattened (team, 2026-10-16: the sculptor shapes them): a smooth surface with
    # the long parting line where they meet, and a line round each lip (MASK_LIP_MARKS)
    up, low, depth = P.MASK_LIP_MARKS
    # flat: the lips' area refilled as a smooth membrane from the skin round it (no lip shapes)
    # from just under the nose to the crease above the chin (a smaller patch left the upper
    # lip's bulge standing above it as a ledge)
    zone = ((A * k_l) / (half + 6.0)) ** 4 + (((E - line) * k_l) / P.MASK_LIP_FLAT) ** 4 < 1.0
    ii, jj = np.where(zone)
    box = np.s_[ii.min() - 3:ii.max() + 4, jj.min() - 3:jj.max() + 4]
    sub, z = r[box].copy(), zone[box]
    sub[z] = ndimage.gaussian_filter(r, 4.0 / (k_l * st))[box][z]
    for _ in range(3000):
        avg = 0.25 * (np.roll(sub, 1, 0) + np.roll(sub, -1, 0) + np.roll(sub, 1, 1) + np.roll(sub, -1, 1))
        sub[z] = avg[z]
    r[box] = sub
    edge = ndimage.gaussian_filter(zone.astype(float), 1.5 / (k_l * st))
    edge = 4.0 * edge * (1.0 - edge)                                  # soften the rim of the refill
    r = r + edge * (ndimage.gaussian_filter(r, 1.5 / (k_l * st)) - r)
    fade = np.clip((a_c - np.abs(A)) * k_l / 2.0, 0.0, 1.0)
    r -= P.MASK_LIP_LINE * fade * np.exp(-(((E - line) * k_l) ** 2) / (2 * 0.45 ** 2))
    shape = np.sqrt(np.clip(1.0 - (A / a_c) ** 2, 0.0, 1.0))
    bow = 1.0 - 0.15 * np.exp(-((A * k_l / 4.0) ** 2))                # a slight dip in the middle (Cupid's bow)
    inside = np.abs(A) < a_c
    for edge in (line + up * shape * bow / k_l, line - low * shape / k_l):
        r -= depth * inside * np.exp(-(((E - edge) * k_l) ** 2) / (2 * 0.4 ** 2))
    # the eyes flat (no eyeballs: the sculptor builds them; the marks below show the axes) and
    # the nose low, a guide for where to build it (team, 2026-10-16)
    pts = c + directions(A, E) * r[..., None]
    X, Y, Z = pts[..., 0], pts[..., 1], pts[..., 2]
    front = Y > c[1] + 40.0
    flat = np.zeros(r.shape, bool)
    for sx in (+1, -1):
        flat |= front & (((X - sx * P.EYE_SPACING / 2) / P.MASK_EYE_FLAT[0]) ** 4 + ((Z - ez) / P.MASK_EYE_FLAT[1]) ** 4 < 1.0)
    top, bottom = ez - 12.0, st_z + P.MASK_LIP_FLAT - 1.0
    nose = front & ((X / 20.0) ** 4 + ((Z - (top + bottom) / 2) / ((top - bottom) / 2)) ** 4 < 1.0)
    flat |= nose
    ii, jj = np.where(flat)
    box = np.s_[ii.min() - 3:ii.max() + 4, jj.min() - 3:jj.max() + 4]
    sub, z = r[box].copy(), flat[box]
    sub[z] = ndimage.gaussian_filter(r, 4.0 / (k_l * st))[box][z]
    for _ in range(5000):
        avg = 0.25 * (np.roll(sub, 1, 0) + np.roll(sub, -1, 0) + np.roll(sub, 1, 1) + np.roll(sub, -1, 1))
        sub[z] = avg[z]
    base = r.copy()
    base[box] = sub
    wn = ndimage.gaussian_filter(nose.astype(float), 1.0 / (k_l * st))
    height = ndimage.gaussian_filter(r - base, 1.5 / (k_l * st))
    r = np.where(flat, base + P.MASK_NOSE_KEEP * wn * np.clip(height, 0.0, None), r)
    edge = ndimage.gaussian_filter(flat.astype(float), 1.5 / (k_l * st))
    edge = 4.0 * edge * (1.0 - edge)
    r = r + edge * (ndimage.gaussian_filter(r, 1.5 / (k_l * st)) - r)
    # the plain skin smoothed (MakeHuman's low-poly facets rippled the cheeks); the eyes, nose
    # and lips kept sharp
    feat = np.zeros(r.shape)
    for _, a, e in eyes:
        feat = np.maximum(feat, np.exp(-(((A - a) / 12.0) ** 4 + ((E - e) / 8.0) ** 4)))
    feat = np.maximum(feat, np.exp(-(((A * k_l) / (lip_half_width() + 10.0)) ** 4 + (((E - e_l) * k_l) / 16.0) ** 4)))
    nz = np.array([0.0, eye_y + 30.0, (ez + st_z) / 2]) - c
    e_n = np.degrees(np.arcsin(nz[2] / np.linalg.norm(nz)))
    feat = np.maximum(feat, np.exp(-(((A * k_l) / 22.0) ** 4 + (((E - e_n) * k_l) / 30.0) ** 4)))
    r = feat * r + (1 - feat) * ndimage.gaussian_filter(r, P.MASK_SKIN_SMOOTH / st)
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
    # MakeHuman's own eyes: its eyelids, and its eyeballs in the openings (no holes). Marks on
    # each eyeball, centred on the eye mechanism's eye axis (circles round it seen from the
    # front, measured on the skin): an iris ring and a pupil
    eyes = on_axis(r)
    depth, width = P.MASK_LINE
    for sx, a, e, rho in eyes:
        r -= depth * np.exp(-((rho - P.MASK_IRIS[0]) ** 2) / (2 * width ** 2)) * (rho < P.MASK_IRIS[0] + 3 * width)
        r -= P.MASK_IRIS[2] * np.clip(1.0 - (rho / P.MASK_IRIS[1]) ** 2, 0.0, 1.0)
    return phi, psi, r, float(push.max()), [(a, e) for _, a, e, _ in eyes]


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


def inner_radius(phi, psi, r):
    """The inside of the shell, as a radius over the same directions as the skin: MASK_T in
    from it along its normal, smooth, following its deepest creases, and never nearer to it
    than half MASK_T along the ray, so the two can't cross (an offset along the vertex
    normals crossed the skin in the eyelid creases)."""
    st = phi[1] - phi[0]
    k = np.radians(1.0) * float(np.median(r))                         # mm per degree
    # under the deepest point within 2 mm (the inner eye corners are deep, steep notches)
    low = ndimage.gaussian_filter(ndimage.minimum_filter(r, size=int(round(4.0 / (k * st))) | 1), 1.5 / (k * st))
    d_a, d_e = np.gradient(low, np.radians(st))
    tan = np.hypot(d_a / np.cos(np.radians(psi))[None, :], d_e) / low   # the normal's tilt from the ray
    cos = np.clip(1.0 / np.sqrt(1.0 + tan ** 2), 0.35, 1.0)
    return np.minimum(low - P.MASK_T / cos, r - 0.5 * P.MASK_T)


def mesh_from(phi, psi, r, c, keep=()):
    """The shell: the skin inside the egg outline, sampled on rings, thickened inward. The
    finishing smooth spares the zones in `keep` ((azimuth, elevation, half width, half height,
    how much), degrees): the eyes' iris marks and the lips' detail."""
    hw, top, bottom, egg = P.MASK_OUTLINE
    cz = (top + bottom) / 2
    hz = (top - bottom) / 2
    f = RegularGridInterpolator((phi, psi), r)
    nr, nt = 260, 1000
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
    rim_ids = np.array([vid(nr - 1, j) for j in range(nt)])
    before = outer.vertices.copy()
    trimesh.smoothing.filter_taubin(outer, lamb=0.5, nu=-0.53, iterations=P.MASK_FINAL_SMOOTH)
    va = np.r_[0.0, A.ravel()]
    ve = np.r_[cz, E.ravel()]
    w = np.zeros(len(va))
    for a0, e0, ha, he, how in keep:
        w = np.maximum(w, how * np.exp(-(((va - a0) / ha) ** 4 + ((ve - e0) / he) ** 4)))
    outer.vertices = w[:, None] * before + (1 - w[:, None]) * outer.vertices
    outer.vertices[rim_ids] = before[rim_ids]                         # keep the outline where it is
    fi = RegularGridInterpolator((phi, psi), inner_radius(phi, psi, r))
    rin = fi(np.stack([A.ravel(), E.ravel()], axis=1)).reshape(A.shape)
    inner = np.vstack([(c + directions(0.0, cz) * fi([[0.0, cz]])[0])[None],
                       (c + directions(A, E) * rin[..., None]).reshape(-1, 3)])
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
    head = trimesh.Trimesh(V, F, process=False)                       # keep the indices (the eyeballs)
    lm = landmarks(head, joints)
    warped, eye_y, info = warp(head, lm)
    ez0 = G.eye_z(S)
    keep = warped.triangles_center[:, 2] > ez0 - 260.0                # the head: smooth it (MakeHuman is low-poly)
    warped = warped.submesh([np.where(keep)[0]], append=True)
    warped = warped.subdivide().subdivide()
    trimesh.smoothing.filter_taubin(warped, lamb=0.5, nu=-0.53, iterations=P.MASK_HEAD_SMOOTH)
    ez = G.eye_z(S)
    c = np.array([0.0, eye_y - P.MASK_CENTRE_BACK, ez - 15.0])
    # his parts + SCULPT_MIN_SKIN (sculpt_base.py's tight wrap; its wrap.stl is inflated at the face)
    wrap = trimesh.load(os.path.join(G.ref_dir(), "sculpt", "tight.stl"), force="mesh")
    dy = forward(warped, wrap, c)
    warped.apply_translation((0.0, dy, 0.0))
    phi, psi, r, pushed, eye_dirs = skin(warped, wrap, c, eye_y)
    keep = [(a, e, 9.0, 6.0, 0.6) for a, e in eye_dirs]               # the eyes' marks, the lips' detail
    v = np.array([0.0, eye_y + 20.0, info["stomion"]]) - c
    keep.append((0.0, np.degrees(np.arcsin(v[2] / np.linalg.norm(v))), 16.0, 5.0, 0.6))
    shell = mesh_from(phi, psi, r, c, keep)
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

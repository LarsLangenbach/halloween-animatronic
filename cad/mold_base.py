"""
Mold base (M5): the printed base the clay-covered face mask lies on, face up, while the
plaster negative is made over it.

The face mask (face_mask.py, printed as v9) is sculpted over in oil-based clay. For the mold:
  - a collar seats it exactly: a ledge under its rim face and a lip up its inside, MOLD_SEAT
    clear of the STL. The base keeps the mask in the same place for the silicone cast later,
    when the mask is the core and the mold's keys find the base again
  - the collar's skirt closes the space under the rim (the rim is a saddle: MOLD_RIM_LIFT above
    the plate by the ears, about 130 at the chin and forehead ends) and flares down at
    MOLD_SKIRT's draft to the flat plate: the mold's flange, with registration cones
  - posts under the forehead and cheeks carry the thin shell under the plaster's weight
  - walls round the flange (inner face drafted) hold the flange plaster; pry blocks against the
    end walls leave notches for a screwdriver
Everything the plaster touches faces up or flares out, so the jacket lifts straight up. The
mask itself wraps past its widest line by the ears and along the jaw: those strips are
filled with clay (one-piece mold) or taken by side pieces; the base serves both.

Mold pose = print pose: X = x, Y = -z (chin toward +Y), Z = y + lift (face up); the plate's
underside is on the table at Z = 0. Split in four at X = 0 and Y = MOLD_SPLIT_Y to fit the bed:
dovetails in the plate, the walls lapped (inner half / outer half) across each split.

Run:  python cad/mold_base.py  -> <stl_dir>/mold_base_{chin,top}_{L,R}.stl
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

sys.stdout.reconfigure(encoding="utf-8")
P = K.params()
NR, NT = 260, 1000          # face_mask.mesh_from's rings and points per ring: keep in step with it
LIP_RINGS = 24              # inner-surface rings read in from the rim (the lip needs about 13)
PIECES = ("chin_L", "chin_R", "top_L", "top_R")   # L = the character's left, +X
BIG = 2000.0


def to_mf(mesh):
    return mf.Manifold(mf.Mesh(vert_properties=np.asarray(mesh.vertices, np.float32),
                               tri_verts=np.asarray(mesh.faces, np.uint32)))


def from_mf(man):
    m = man.to_mesh()
    return trimesh.Trimesh(np.asarray(m.vert_properties)[:, :3], np.asarray(m.tri_verts), process=True)


def centre():
    """The point the mask's directions start from (face_mask.build: c)."""
    return np.array([0.0, -P.MASK_CENTRE_BACK, G.eye_z(P.HEAD_SCALE) - 15.0])


def outline_dirs(rho, th):
    """Unit vectors at outline parameter (rho, th): rho = 1 on the rim (face_mask.mesh_from)."""
    hw, top, bottom, egg = P.MASK_OUTLINE
    cz, hz = (top + bottom) / 2, (top - bottom) / 2
    a = np.radians(hw * rho * np.cos(th) * (1.0 + egg * rho * np.sin(th)))
    e = np.radians(cz + hz * rho * np.sin(th))
    return np.stack([np.cos(e) * np.sin(a), np.cos(e) * np.cos(a), np.sin(e)], axis=-1)


def load_mask():
    """The printed mask (face_mask.stl, assembled pose)."""
    return trimesh.load(os.path.join(K.stl_dir(), "face_mask.stl"), force="mesh")


def grid_radii(mask, c):
    """Read the mask's own sampling grid back from its vertices: the rim's outer and inner
    radius at each of the NT rim directions, and the inside's radius on the last LIP_RINGS
    rings (the inside is exactly on the grid; only the outside was smoothed)."""
    hw, top, bottom, egg = P.MASK_OUTLINE
    assert egg == 0.0, "mold_base reads the outline back assuming no egg term"
    cz, hz = (top + bottom) / 2, (top - bottom) / 2
    v = mask.vertices - c
    r = np.linalg.norm(v, axis=1)
    a = np.degrees(np.arctan2(v[:, 0], v[:, 1]))
    e = np.degrees(np.arcsin(np.clip(v[:, 2] / r, -1, 1)))
    u, w = a / hw, (e - cz) / hz
    i = np.hypot(u, w) * NR
    j = (np.arctan2(w, u) % (2 * np.pi)) * NT / (2 * np.pi)
    on = (np.abs(i - np.round(i)) < 0.02) & (np.abs(j - np.round(j)) < 0.02)
    I, J = np.round(i).astype(int), np.round(j).astype(int) % NT
    rim = on & (I == NR)
    r_out = np.full(NT, -np.inf)
    np.maximum.at(r_out, J[rim], r[rim])
    rin = np.full((LIP_RINGS + 1, NT), np.inf)                       # row k = ring NR - k
    sel = on & (I >= NR - LIP_RINGS) & (I <= NR)
    np.minimum.at(rin, (NR - I[sel], J[sel]), r[sel])
    if np.isinf(r_out).any() or np.isinf(rin).any() or (r_out - rin[0] < 0.5).any():
        raise SystemExit("FAIL  could not read the mask's rim grid back (face_mask.mesh_from changed?)")
    return r_out, rin


def lift(c, r_out, rin):
    """Z added to y in the mold pose: the lowest rim point MOLD_RIM_LIFT above the plate."""
    th = np.arange(NT) * 2 * np.pi / NT
    d = outline_dirs(1.0, th)
    low = min((c + d * r_out[:, None])[:, 1].min(), (c + d * rin[0][:, None])[:, 1].min())
    return P.MOLD_PLATE_T + P.MOLD_RIM_LIFT - low


def mold_pose(p, zs):
    """Assembled frame -> mold pose (face up): X = x, Y = -z, Z = y + zs."""
    p = np.asarray(p, float)
    return np.stack([p[..., 0], -p[..., 2], p[..., 1] + zs], axis=-1)


def mask_in_mold_pose(mask=None):
    """(mask mesh in the mold pose, Z lift, rim data) -- shared with mold_check."""
    mask = load_mask() if mask is None else mask
    c = centre()
    r_out, rin = grid_radii(mask, c)
    zs = lift(c, r_out, rin)
    m = mask.copy()
    m.vertices = mold_pose(m.vertices, zs)
    m.fix_normals()
    return m, zs, (c, r_out, rin)


def collar(c, r_out, rin, zs, step=2):
    """The ring the mask sits in, swept round the rim: one cross-section per rim direction,
    [ledge's outer end, skirt foot outside, skirt foot inside, skirt's inside top, lip root
    inside, lip middle inside, lip tip inside, lip tip outside, lip middle outside, lip root
    outside]. Also returns the skirt foot's outer loop (plan, mold pose)."""
    g, tl, ll = P.MOLD_SEAT
    ts, draft = P.MOLD_SKIRT
    T = P.MOLD_PLATE_T
    js = np.arange(0, NT, step)
    th = js * 2 * np.pi / NT
    d0 = outline_dirs(1.0, th)
    tang = outline_dirs(1.0, th + 1e-4) - outline_dirs(1.0, th - 1e-4)
    out = outline_dirs(1.001, th) - d0
    N = np.cross(d0, tang)
    N /= np.linalg.norm(N, axis=1)[:, None]
    N *= np.sign((N * out).sum(axis=1))[:, None]                     # the rim face's outward normal
    rI, rO = rin[0, js], r_out[js]
    per_rho = np.linalg.norm(d0 - outline_dirs(0.999, th), axis=1) / 0.001 * rI   # mm along the inside per unit rho

    def inner_at(s):
        """The point s mm in from the rim along the inside, and the inside's radius there."""
        rho = 1.0 - s / per_rho
        k = (1.0 - rho) * NR                                          # rings in from the rim
        k0 = np.floor(k).astype(int)
        f = k - k0
        if (k0 + 1 > LIP_RINGS).any():
            raise SystemExit("FAIL  the lip reaches past the rings read (raise LIP_RINGS)")
        rr = rin[k0, js] * (1 - f) + rin[k0 + 1, js] * f
        return outline_dirs(rho, th), rr

    sec = []
    L4 = c + d0 * rO[:, None] + g * N                                 # the ledge's outer end
    L3 = c + d0 * (rI - g)[:, None] + g * N                           # the lip's outside meets the ledge
    root = P.MOLD_LIP_ROOT
    L5 = c + d0 * (rI - g - root)[:, None] + g * N                    # the lip's inside at its root (a wedge)
    dm, rm = inner_at(ll / 2)
    dt, rt = inner_at(ll)
    lip = [c + dm * (rm - g - (root + tl) / 2)[:, None], c + dt * (rt - g - tl)[:, None],
           c + dt * (rt - g)[:, None], c + dm * (rm - g)[:, None]]
    L4m, L3m, L5m = (mold_pose(p, zs) for p in (L4, L3, L5))
    lipm = [mold_pose(p, zs) for p in lip]
    # the skirt flares out in plan, square to the ledge's loop
    xy = L4m[:, :2]
    t2 = np.roll(xy, -1, axis=0) - np.roll(xy, 1, axis=0)
    n2 = np.stack([t2[:, 1], -t2[:, 0]], axis=1)
    n2 /= np.linalg.norm(n2, axis=1)[:, None]
    n2 *= np.sign(((xy - xy.mean(axis=0)) * n2).sum(axis=1))[:, None]
    for _ in range(3):
        n2 = (np.roll(n2, 1, axis=0) + 2 * n2 + np.roll(n2, -1, axis=0))
        n2 /= np.linalg.norm(n2, axis=1)[:, None]
    foot_z = T - 0.5                                                  # bites into the plate
    h = L4m[:, 2] - foot_z
    f_out = np.column_stack([xy + n2 * (h * np.tan(np.radians(draft)))[:, None], np.full(len(h), foot_z)])
    f_in = f_out.copy()
    f_in[:, :2] -= n2 * ts
    # the mask drops in from above: where its inside flares out going up (by the ears and the
    # jaw), a lip that followed it would sit over the rim's way down. There it stands straight
    # up from the rim's inner edge instead (its outside never further out than the root)
    for o, i in ((3, 0), (2, 1)):                                     # (outside, inside) at the middle, the tip
        out_by = np.maximum(((lipm[o] - L3m)[:, :2] * n2).sum(axis=1), 0.0)
        for q in (o, i):
            lipm[q][:, :2] -= n2 * out_by[:, None]
    s_in = L5m.copy()
    s_in[:, 2] -= P.MOLD_SEAT_DROP
    if (s_in[:, 2] < foot_z + 0.5).any():
        raise SystemExit("FAIL  the collar is too low by the ears (raise MOLD_RIM_LIFT)")
    secs = np.stack([L4m, f_out, f_in, s_in, L5m, lipm[0], lipm[1], lipm[2], lipm[3], L3m], axis=1)
    ns, M = secs.shape[:2]
    V = secs.reshape(-1, 3)
    F = []
    for k in range(ns):
        k1 = (k + 1) % ns
        for m in range(M):
            a, b = k * M + m, k * M + (m + 1) % M
            cc, dd = k1 * M + (m + 1) % M, k1 * M + m
            F += [(a, b, cc), (a, cc, dd)]
    mesh = trimesh.Trimesh(V, np.array(F), process=False)
    if mesh.volume < 0:
        mesh.invert()
    return mesh, f_out[:, :2]


def rect(x0, x1, y0, y1):
    return mf.CrossSection([np.array([(x0, y0), (x1, y0), (x1, y1), (x0, y1)], float)], mf.FillRule.EvenOdd)


def poly(pts):
    return mf.CrossSection([np.asarray(pts, float)], mf.FillRule.EvenOdd)


def union(items):
    out = items[0]
    for it in items[1:]:
        out = out + it
    return out


def heightfield_post(mask_m, x, y):
    """A post from the plate to MOLD_POST_GAP under the mask's inside at (x, y): its top
    follows the inside (rays up from below hit the inside first)."""
    T, R, gap = P.MOLD_PLATE_T, P.MOLD_POST_R, P.MOLD_POST_GAP
    near = np.linalg.norm(mask_m.triangles_center[:, :2] - (x, y), axis=1) < R + 6
    sub = mask_m.submesh([np.where(near)[0]], append=True)
    na, radii = 48, (0.0, 4.0, 8.0, R)
    ang = np.arange(na) * 2 * np.pi / na
    pts = [(x, y)] + [(x + rr * np.cos(a), y + rr * np.sin(a)) for rr in radii[1:] for a in ang]
    pts = np.array(pts)
    origins = np.column_stack([pts, np.full(len(pts), 0.0)])
    loc, idx, _ = sub.ray.intersects_location(origins, np.tile([0, 0, 1.0], (len(pts), 1)))
    top = np.full(len(pts), np.inf)
    np.minimum.at(top, idx, loc[:, 2])
    if np.isinf(top).any():
        raise SystemExit(f"FAIL  post at ({x}, {y}) is not under the mask")
    top -= gap
    zb = T - 0.5
    V = np.vstack([np.column_stack([pts, top]), np.column_stack([pts[-na:], np.full(na, zb)]), [(x, y, zb)]])
    F = []
    ring = lambda k: 1 + (k - 1) * na                                 # noqa: E731  first index of ring k (k >= 1)
    for a in range(na):                                               # top: fan, then quads between rings
        F.append((0, ring(1) + a, ring(1) + (a + 1) % na))
        for k in (1, 2):
            p0, p1 = ring(k) + a, ring(k) + (a + 1) % na
            q0, q1 = ring(k + 1) + a, ring(k + 1) + (a + 1) % na
            F += [(p0, q0, q1), (p0, q1, p1)]
    ob, bc = len(pts), len(V) - 1                                     # bottom ring start, bottom centre
    for a in range(na):
        t0, t1 = ring(3) + a, ring(3) + (a + 1) % na
        b0, b1 = ob + a, ob + (a + 1) % na
        F += [(t0, b0, b1), (t0, b1, t1), (bc, b1, b0)]
    m = trimesh.Trimesh(V, np.array(F), process=False)
    if m.volume < 0:
        m.invert()
    return m, float(top.max() + gap)


def layout(mask_m, foot):
    """The walls' inner rectangle (mold pose): MOLD_ROOM outside the mask seen from above and
    MOLD_FLANGE outside the skirt's foot."""
    v = mask_m.vertices
    xi = np.ceil(max(np.abs(v[:, 0]).max() + P.MOLD_ROOM, np.abs(foot[:, 0]).max() + P.MOLD_FLANGE))
    y1 = np.ceil(max(v[:, 1].max() + P.MOLD_ROOM, foot[:, 1].max() + P.MOLD_FLANGE))
    y0 = np.floor(min(v[:, 1].min() - P.MOLD_ROOM, foot[:, 1].min() - P.MOLD_FLANGE))
    return float(xi), float(y0), float(y1)


def ownership():
    """{piece: (plate-band region, upper region)} as 2D cross-sections: straight splits at X = 0
    and Y = MOLD_SPLIT_Y, with dovetails in the plate band. Every seam is a vertical prism, so
    the pieces drop together from above."""
    ys, (nw, hw, dep) = P.MOLD_SPLIT_Y, P.MOLD_TAB
    base = {"chin_L": rect(0, BIG, ys, BIG), "chin_R": rect(-BIG, 0, ys, BIG),
            "top_L": rect(0, BIG, -BIG, ys), "top_R": rect(-BIG, 0, -BIG, ys)}
    tabs = []                                                         # (owner, region)
    for ty in P.MOLD_TABS_X:                                          # along X = 0, owned by +X
        owner = "chin_L" if ty > ys else "top_L"
        tabs.append((owner, poly([(0.5, ty - nw / 2), (0.5, ty + nw / 2), (-dep, ty + hw / 2), (-dep, ty - hw / 2)])))
    for tx in P.MOLD_TABS_Y:                                          # along the Y split, owned by the chin side
        for s, owner in ((1, "chin_L"), (-1, "chin_R")):
            x = s * tx
            tabs.append((owner, poly([(x - nw / 2, ys + 0.5), (x + nw / 2, ys + 0.5),
                                      (x + hw / 2, ys - dep), (x - hw / 2, ys - dep)])))

    def own(name, extra):
        region = base[name]
        if extra:
            region = region - union([r for _, r in extra])
            mine = [r for o, r in extra if o == name]
            if mine:
                region = region + union(mine)
        return region.offset(-P.MOLD_FIT, mf.JoinType.Miter)

    return {n: (own(n, tabs), own(n, [])) for n in PIECES}


def walls(xi, y0, y1, outline):
    """The four L-shaped wall corners, standing on the plate (separate prints), with ears at
    each seam to clip, bolt or tie them together. {name: manifold}."""
    T, (H, wt) = P.MOLD_PLATE_T, P.MOLD_WALL
    el, et, hd, hz = P.MOLD_EAR
    xo, yo0, yo1 = xi + wt, y0 - wt, y1 + wt
    ys, fit = P.MOLD_SPLIT_Y, P.MOLD_FIT
    ring = mf.Manifold.extrude(outline, H).translate((0, 0, T)) - \
        mf.Manifold.extrude(rect(-xi, xi, y0, y1), H + 2).translate((0, 0, T - 1))
    own = ownership()
    out = {}
    for name in PIECES:
        sx = 1 if name.endswith("L") else -1
        chin = name.startswith("chin")
        piece = ring ^ mf.Manifold.extrude(own[name][1], H + 2).translate((0, 0, T - 1))
        # ear at the end wall (seam X = 0), reaching out past the wall in Y
        ye = (yo1 - 0.5, yo1 + el) if chin else (yo0 - el, yo0 + 0.5)
        xe = (fit, fit + et) if sx > 0 else (-fit - et, -fit)
        ear_x = mf.Manifold.cube((xe[1] - xe[0], ye[1] - ye[0], H)).translate((xe[0], ye[0], T))
        # ear at the side wall (seam Y = MOLD_SPLIT_Y), reaching out past the wall in X
        xs = (xo - 0.5, xo + el) if sx > 0 else (-xo - el, -xo + 0.5)
        yse = (ys + fit, ys + fit + et) if chin else (ys - fit - et, ys - fit)
        ear_y = mf.Manifold.cube((xs[1] - xs[0], yse[1] - yse[0], H)).translate((xs[0], yse[0], T))
        piece = piece + ear_x + ear_y
        yh = (yo1 + el / 2) if chin else (yo0 - el / 2)
        xh = sx * (xo + el / 2)
        for z in hz:
            hx = mf.Manifold.cylinder(40, hd / 2, hd / 2, 32, True).rotate((0, 90, 0)).translate((0, yh, T + z))
            hy = mf.Manifold.cylinder(40, hd / 2, hd / 2, 32, True).rotate((90, 0, 0)).translate((xh, ys, T + z))
            piece = piece - hx - hy
        out["mold_wall_" + name] = piece
    return out


def pry_placements(xi, y0, y1):
    """4x3 transforms from a pry wedge's own frame (outer end face centred on X = 0, Y = 0,
    running in along +Y, on Z = 0) to its 8 places against the walls: two on each wall."""
    g, T = P.MOLD_FIT, P.MOLD_PLATE_T
    spots = []
    for sx in (-1, 1):
        spots.append((sx * P.MOLD_PRY_X, y1 - g, (0.0, 1.0)))         # chin end wall (it faces +Y)
        spots.append((sx * P.MOLD_PRY_X, y0 + g, (0.0, -1.0)))        # forehead end wall
        for y in P.MOLD_PRY_Y:
            spots.append((sx * (xi - g), y, (float(sx), 0.0)))       # side walls
    out = []
    for x, y, (nx, ny) in spots:
        inward = np.array([-nx, -ny, 0.0])
        across = np.array([inward[1], -inward[0], 0.0])
        out.append(np.column_stack([across, inward, (0, 0, 1.0), (x, y, T)]))
    return out


def pry_wedge():
    """A loose wedge (print 8): tapered in width and height toward its inner end so it slides
    straight out of the plaster once the walls are off, with a hole in its outer end for an M3
    screw to pull it by. Its own frame: outer end face on Y = 0, running in along +Y, on Z = 0."""
    w0, w1, ln, h0, h1 = P.MOLD_PRY
    pts = [(sx * w0 / 2, 0.0, z) for sx in (-1, 1) for z in (0.0, h0)] + \
          [(sx * w1 / 2, ln, z) for sx in (-1, 1) for z in (0.0, h1)]
    wedge = mf.Manifold.hull_points(np.array(pts, float))
    hole = mf.Manifold.cylinder(9.0, P.M3_TAP / 2, P.M3_TAP / 2, 24).rotate((-90, 0, 0)).translate((0, -1.0, 3.0))
    return wedge - hole


def build():
    mask = load_mask()
    mask_m, zs, (c, r_out, rin) = mask_in_mold_pose(mask)
    T = P.MOLD_PLATE_T
    H, wt = P.MOLD_WALL
    ring, foot = collar(c, r_out, rin, zs)
    ring_mf = to_mf(ring)
    if ring_mf.status() != mf.Error.NoError or abs(ring_mf.volume() - ring.volume) > 1.0:
        raise SystemExit(f"FAIL  collar sweep is not a clean solid ({ring_mf.status()})")
    xi, y0, y1 = layout(mask_m, foot)
    xo, yo0, yo1 = xi + wt, y0 - wt, y1 + wt
    rr = 8.0
    outline = rect(-xo + rr, xo - rr, yo0 + rr, yo1 - rr).offset(rr, mf.JoinType.Round, 2.0, 64)
    plate = mf.Manifold.extrude(outline, T)
    rw, rh, rd = P.MOLD_RIB                                           # the rib narrows going up (draft)
    g = P.MOLD_FIT
    lean = rh * np.tan(np.radians(rd))
    rib = mf.Manifold.extrude(rect(-xi + g, xi - g, y0 + g, y1 - g), rh + 0.5).translate((0, 0, T - 0.5)) - \
        mf.Manifold.hull_points(np.array(
            [(sx * (xi - g - rw), y, T - 1) for sx in (-1, 1) for y in (y0 + g + rw, y1 - g - rw)] +
            [(sx * (xi - g - rw + lean + 0.1), y, T + rh + 0.1) for sx in (-1, 1)
             for y in (y0 + g + rw - lean - 0.1, y1 - g - rw + lean + 0.1)], float))
    kd0, kd1, kh = P.MOLD_KEY
    keys = []
    for y in (y1 - P.MOLD_FLANGE / 2, y0 + P.MOLD_FLANGE / 2):
        for sx in (-1, 1):
            keys.append(mf.Manifold.cylinder(kh + 0.5, kd0 / 2, kd1 / 2, 64).translate((sx * P.MOLD_KEYS_X, y, T - 0.5)))
    gaps = [mf.Manifold.cube((P.MOLD_PRY[0] + 2 * P.MOLD_PRY_GAP, rw + g + 2.0, rh + 2.0))
            .translate((-P.MOLD_PRY[0] / 2 - P.MOLD_PRY_GAP, -1.0, -1.0)).transform(m)
            for m in pry_placements(xi, y0, y1)]                      # the wedges stand in gaps in the rib
    rib = rib - union(gaps)
    posts, post_h = [], []
    for x, y in P.MOLD_POSTS:
        pm, ztop = heightfield_post(mask_m, x, y)
        posts.append(to_mf(pm))
        post_h.append(ztop)
    base = union([plate, rib, ring_mf] + keys + posts)
    if base.status() != mf.Error.NoError:
        raise SystemExit(f"FAIL  base union failed ({base.status()})")
    own = ownership()
    parts = {}
    for name in PIECES:
        lo, up = own[name]
        cut = mf.Manifold.extrude(lo, T + 1).translate((0, 0, -1)) + mf.Manifold.extrude(up, 400).translate((0, 0, T))
        bodies = [b for b in (base ^ cut).decompose() if b.volume() > 1.0]   # the bands meet at Z = T:
        parts["mold_base_" + name] = union(bodies)                           # drop zero-volume sheets there
    parts.update(walls(xi, y0, y1, outline))
    parts["mold_pry_wedge"] = pry_wedge()
    info = dict(xi=xi, y0=y0, y1=y1, zs=zs, foot=foot, post_h=post_h)
    return parts, info, mask_m


def parts():
    return {k: from_mf(v) for k, v in build()[0].items()}


def main():
    pieces, info, mask_m = build()
    out = K.stl_dir()
    ok = True
    bed = K.printer()["bed"]
    xi, y0, y1 = info["xi"], info["y0"], info["y1"]
    print(f"mask lifted {info['zs']:.1f} (lowest rim {P.MOLD_RIM_LIFT:.0f} above the plate); walls inside "
          f"X +-{xi:.0f}, Y {y0:.0f} .. {y1:.0f} ({2 * xi:.0f} x {y1 - y0:.0f}); posts to Z "
          + ", ".join(f"{h:.0f}" for h in info["post_h"]))
    for name, man in pieces.items():
        m = from_mf(man)
        m.merge_vertices()
        m.update_faces(m.nondegenerate_faces())
        m.remove_unreferenced_vertices()
        good = bool(m.is_watertight) and m.body_count == 1
        e = m.extents
        fits = sorted(e[:2]) <= sorted(bed[:2]) and e[2] <= bed[2]
        ok &= good
        m.export(os.path.join(out, name + ".stl"))
        print(f"{'' if good else 'FAIL  '}{'' if fits else 'WARN  does not fit the bed: '}wrote {name}.stl  "
              f"{e[0]:.1f} x {e[1]:.1f} x {e[2]:.1f} mm  watertight={m.is_watertight} bodies={m.body_count}  "
              f"{m.volume / 1000:.0f} cm3")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())

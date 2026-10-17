"""
Face mask (M5, D19): a thin shell of a man's face, its features where the mechanism puts
them, to sculpt the skin on. It replaces the sculpt base.

Source face: the MakeHuman base mesh (inputs/reference/makehuman/base.obj, CC0). Its head
is a realistic, neutral adult; units are decimetres, +y up, the face toward +z.

  1. turn into our frame and scale (MASK_SCALE: the geometric mean of what fits the eye
     spacing and what fits the eye-to-lips distance)
  2. warp smoothly (thin-plate spline) so the eye centres land on the EyeMech's eyes and
     the lips meet where Cogley's lip plates meet, with a man's proportions: the jaw and chin
     wider and squarer (MASK_MALE), the brow ridge forward
  3. move it forward until its inside clears Cogley's head by SCULPT_MIN_SKIN everywhere
     (outside the sculpt base's wrap of his parts), pushing out locally where a few points
     still don't
  4. trim to a mask outline (forehead to chin, cheek to cheek) and keep only the face's
     outer skin (no inside of the mouth or eye sockets)
  5. thicken inward by MASK_T into a solid shell. The eye openings are the face's own,
     on the real eyes.

Run:  python cad/face_mask.py  -> <stl_dir>/face_mask.stl
"""
import os
import sys

import manifold3d as mf
import numpy as np
import trimesh
from scipy.interpolate import RBFInterpolator

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
    for g in ("joint-l-eye", "joint-r-eye", "joint-jaw", "joint-head"):
        idx = np.unique(np.concatenate([np.array(f) for f in groups[g]]))
        joints[g] = V[idx].mean(axis=0)
    return V, np.array(tris), joints


def landmarks(mesh, joints):
    """Eyes, where the lips meet, nose tip, chin, jaw angles and brow (our frame, MakeHuman's
    scale)."""
    v = mesh.vertices
    eyes = np.array([joints["joint-l-eye"], joints["joint-r-eye"]])
    ez = eyes[:, 2].mean()
    mid = v[np.abs(v[:, 0]) < 1.0]
    front = mid[mid[:, 1] > np.percentile(mid[:, 1], 40)]
    # the lips: the deepest point of the front profile between the nose and the chin
    prof = []
    for z in np.arange(ez - 120.0, ez - 20.0, 0.5):
        sel = front[np.abs(front[:, 2] - z) < 0.6]
        if len(sel):
            prof.append((z, sel[:, 1].max()))
    prof = np.array(prof)
    nose_i = int(np.argmax(prof[:, 1]))
    nose = np.array([0.0, prof[nose_i, 1], prof[nose_i, 0]])
    below = prof[prof[:, 0] < nose[2] - 12.0]
    lips = below[below[:, 0] > nose[2] - 45.0]
    # stomion: the dent between the upper and lower lip (a local minimum of depth)
    k = int(np.argmin(lips[:, 1][2:-2])) + 2
    stomion = np.array([0.0, lips[k, 1], lips[k, 0]])
    chin_zone = prof[prof[:, 0] < stomion[2] - 15.0]
    c = int(np.argmax(chin_zone[:, 1]))
    chin = np.array([0.0, chin_zone[c, 1], chin_zone[c, 0]])
    # jaw angles: the widest points of the face 25 below the lips, in its front half
    band = v[(np.abs(v[:, 2] - (stomion[2] - 22.0)) < 2.0) & (v[:, 1] > eyes[0, 1] - 40.0)]
    jaw = np.array([band[np.argmax(band[:, 0])], band[np.argmin(band[:, 0])]])
    brow = front[np.abs(front[:, 2] - (ez + 18.0)) < 1.0]
    brow = brow[np.argmax(brow[:, 1])]
    return dict(eyes=eyes, nose=nose, stomion=stomion, chin=chin, jaw=jaw, brow=brow)


def lip_target():
    """Where Cogley's lip plates meet, in our frame: (x 0, z)."""
    lips = {n: m for n, k, g, m in C.load({"mouth"}) if n in ("UpperLeftLip", "Part 34", "LowerLeftLip", "Part 37")}
    upper = min(lips[n].bounds[0][2] for n in ("UpperLeftLip", "Part 34"))
    lower = max(lips[n].bounds[1][2] for n in ("LowerLeftLip", "Part 37"))
    front = max(m.bounds[1][1] for m in lips.values())
    return (upper + lower) / 2, front


def warp(mesh, lm):
    """Scale, then thin-plate-spline the landmarks onto the mechanism with a man's
    proportions. Returns the warped mesh and the landmarks' targets."""
    ez = G.eye_z(S)
    st_z, _ = lip_target()
    ipd = abs(lm["eyes"][0, 0] - lm["eyes"][1, 0])
    e2l = lm["eyes"][:, 2].mean() - lm["stomion"][2]
    s = np.sqrt((P.EYE_SPACING / ipd) * ((ez - st_z) / e2l)) * P.MASK_SCALE_TRIM
    centre = np.array([0.0, lm["eyes"][:, 1].mean(), lm["eyes"][:, 2].mean()])

    def sim(p):
        return (np.asarray(p) - centre) * s + np.array([0.0, 0.0, ez])

    src, dst = [], []
    for e in lm["eyes"]:                                              # eyes onto the EyeMech's
        src.append(sim(e))
        dst.append(np.array([np.sign(e[0]) * P.EYE_SPACING / 2, sim(e)[1], ez]))
    st = sim(lm["stomion"])                                           # the lips onto his
    src.append(st)
    dst.append(np.array([0.0, st[1], st_z]))
    nose = sim(lm["nose"])                                            # nose: same share of eyes-to-lips
    f = (ez - nose[2]) / (ez - st[2])
    src.append(nose)
    dst.append(np.array([0.0, nose[1], ez - f * (ez - st_z)]))
    wide, fwd = P.MASK_MALE
    chin = sim(lm["chin"])                                            # chin: same drop below the lips
    src.append(chin)
    dst.append(chin + np.array([0.0, 2.0, st_z - st[2]]))
    for j in lm["jaw"]:                                               # a man's jaw: wider, squarer
        jp = sim(j)
        src.append(jp)
        dst.append(jp + np.array([np.sign(jp[0]) * wide, 0.0, st_z - st[2]]))
    for sx in (+1, -1):                                               # chin corners wider too
        cc = chin + np.array([sx * 14.0, -3.0, 4.0])
        src.append(cc)
        dst.append(cc + np.array([sx * wide * 0.6, 1.0, st_z - st[2]]))
    b = sim(lm["brow"])                                               # brow ridge forward
    src.append(b)
    dst.append(b + np.array([0.0, fwd, 0.0]))
    # anchors far from the face keep the head's shape
    for p in ((0, -80, ez + 110), (0, -160, ez), (90, -60, ez), (-90, -60, ez), (0, -60, ez - 200),
              (0, 40, ez + 90), (70, 0, ez + 60), (-70, 0, ez + 60)):
        q = np.array(p, float)
        src.append(q)
        dst.append(q)
    src, dst = np.array(src), np.array(dst)
    rbf = RBFInterpolator(src, dst - src, kernel="thin_plate_spline")
    v = sim(mesh.vertices)
    v = v + rbf(v)
    return trimesh.Trimesh(v, mesh.faces, process=False), dict(scale=s, stomion_z=st_z)


def crop(mesh):
    """The face's outer skin inside the mask outline: front-facing, visible from the front,
    inside an oval from the forehead to the chin and cheek to cheek."""
    ez = G.eye_z(S)
    v, f = mesh.vertices, mesh.faces
    c = mesh.triangles_center
    n = mesh.face_normals
    cx, cz = 0.0, ez + P.MASK_OUTLINE[2]
    ax, az = P.MASK_OUTLINE[0], P.MASK_OUTLINE[1]
    inside = ((c[:, 0] - cx) / ax) ** 2 + ((c[:, 2] - cz) / az) ** 2 <= 1.0
    keep = inside & (n[:, 1] > -0.3) & (c[:, 1] > -60.0)
    # visible from the front: the first hit of a ray from far in front at the centroid
    idx = np.where(keep)[0]
    o = np.column_stack([c[idx, 0], np.full(len(idx), 500.0), c[idx, 2]])
    loc, ri, ti = mesh.ray.intersects_location(o, np.tile([0.0, -1.0, 0.0], (len(idx), 1)), multiple_hits=False)
    first = np.full(len(idx), -1)
    first[ri] = ti
    hity = np.full(len(idx), np.nan)
    hity[ri] = loc[:, 1]
    vis = (first == idx) | (np.abs(hity - c[idx, 1]) < 0.8)
    keep_idx = idx[vis]
    face = trimesh.Trimesh(v, f[keep_idx], process=True)
    face.remove_unreferenced_vertices()
    # keep the biggest connected piece (drops stray bits behind the ears)
    parts = face.split(only_watertight=False)
    face = max(parts, key=lambda m: m.area)
    return face


def clear_of(mask, wrap):
    """Move the mask forward until its inside surface (MASK_T in) is outside Cogley's wrap
    (his parts + SCULPT_MIN_SKIN); then push the last few points out along their normals.
    Inside/outside from the nearest wrap sample's normal (fast on a 500k-triangle wrap)."""
    from scipy.spatial import cKDTree
    pts, fi = trimesh.sample.sample_surface(wrap, 600000, seed=1)
    nrm = wrap.face_normals[fi]
    tree = cKDTree(pts)

    def depth_inside(q):
        d, i = tree.query(q)
        sd = np.einsum("ij,ij->i", q - pts[i], nrm[i])
        return np.where(sd < 0, d, 0.0)                               # > 0: inside, by about this

    n0 = smooth_normals(mask)
    for dy in np.arange(-20.0, 60.0, 0.5):
        v = mask.vertices + [0.0, dy, 0.0]
        if (depth_inside(v - n0 * P.MASK_T) > 0.2).mean() < P.MASK_INSIDE_OK:
            break
    m = mask.copy()
    m.vertices = mask.vertices + [0.0, dy, 0.0]
    n = smooth_normals(m)
    for _ in range(30):                                               # smooth bulges where still inside
        dep = depth_inside(m.vertices - n * P.MASK_T)
        bad = dep > 0.2
        if not bad.any():
            break
        src, amt = m.vertices[bad], dep[bad] + 0.3
        d2 = ((m.vertices[:, None, :] - src[None, :, :]) ** 2).sum(-1)
        push = (amt[None, :] * np.exp(-d2 / (2 * P.MASK_BULGE ** 2))).max(axis=1)
        m.vertices = m.vertices + n * push[:, None]
    return m, dy


def smooth_normals(mesh):
    """Vertex normals of a well-smoothed copy: offsets along them don't cross in the nostrils
    or at the trimmed edge."""
    sm = mesh.copy()
    trimesh.smoothing.filter_laplacian(sm, lamb=0.5, iterations=25)
    return sm.vertex_normals


def solidify(face, t):
    """A shell: the surface and a copy t inward along smoothed vertex normals, joined round
    the edge. Returns a watertight trimesh."""
    v, f = face.vertices, face.faces
    n = smooth_normals(face)
    inner = v - n * t
    nv = len(v)
    faces = [f, f[:, ::-1] + nv]
    edges = face.edges_sorted
    uniq, cnt = np.unique(edges, axis=0, return_counts=True)
    boundary = set(map(tuple, uniq[cnt == 1]))
    side = []
    for a, b in face.edges:                                           # directed, as in the faces
        if (min(a, b), max(a, b)) in boundary:
            side += [(b, a, a + nv), (b, a + nv, b + nv)]
    faces.append(np.array(side))
    m = trimesh.Trimesh(np.vstack([v, inner]), np.vstack(faces), process=True)
    if m.volume < 0:
        m.invert()
    return m


def build():
    V, F, joints = read_makehuman()
    head = trimesh.Trimesh(V, F, process=False)
    lm = landmarks(head, joints)
    warped, info = warp(head, lm)
    face = crop(warped)
    for _ in range(P.MASK_SUBDIVIDE):
        # midpoint subdivision, then a gentle smooth: Loop subdivision mishandled the trimmed
        # edge and threw edge points 60 mm out (spikes)
        face = face.subdivide()
        trimesh.smoothing.filter_taubin(face, lamb=0.5, nu=-0.53, iterations=10)
    wrap = trimesh.load(os.path.join(G.ref_dir(), "sculpt", "wrap.stl"), force="mesh")
    face, dy = clear_of(face, wrap)
    shell = solidify(face, P.MASK_T)
    print(f"scale {info['scale']:.3f}, lips at z {info['stomion_z']:.1f}, moved forward {dy:.1f} mm")
    return shell, face


def main():
    shell, face = build()
    out = K.stl_dir()
    man = R.to_mf(shell)
    m = R.from_mf(man)
    m.merge_vertices()
    m.update_faces(m.nondegenerate_faces())
    m.remove_unreferenced_vertices()
    good = bool(m.is_watertight) and m.body_count == 1
    m.export(os.path.join(out, "face_mask.stl"))
    face.export(os.path.join(G.ref_dir(), "sculpt", "face_mask_surface.stl"))
    e = m.extents
    print(f"{'' if good else 'FAIL  '}wrote face_mask.stl  {e[0]:.1f} x {e[1]:.1f} x {e[2]:.1f} mm  "
          f"watertight={m.is_watertight} bodies={m.body_count}  {m.volume / 1000:.0f} cm3")
    return 0 if good else 1


if __name__ == "__main__":
    sys.exit(main())

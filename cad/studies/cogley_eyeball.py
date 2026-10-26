"""
Cogley's eyeball (EyeMech `Component74`, the same part in e3.1 and e3.2) with a plain round
front: its iris dish (a concave R15 cap 14.4 across, 1.8 deep) and the 4 mm pupil hole in it
are filled out to the eyeball's own R16 sphere. Everything more than EYEBALL_FILL_FROM behind
the front pole -- the socket the eye core pivots in, the clips, the flat back -- is his,
untouched.

Why the mechanism can't tell the difference:
  - the eye turns about its sphere centre, and the lids are spheres about the same centre,
    inner radius EYEMECH_EYE_R[0] (16.5). The filled front stays inside the eye's own R16
    sphere, so the 0.5 gap to the lids is the same at every eye and lid pose.
  - a turn about the centre keeps every point at its radius. Parts outside R16 never get
    inside it; parts inside R16 sit in the socket (behind EYE_SOCKET_FRONT), and on every
    sphere about the centre his own solid lies between the socket and the filled front.
    So a part could only reach the new plastic by first passing through his eyeball: if
    his eyeball moves freely, this one does, whatever the eye's range.

Checks (exit 1 if one fails):
  1. the new eyeball is one valid solid that contains his, and every bit of added plastic is
     inside R16 and in front of EYEBALL_FILL_FROM (so the back is unchanged).
  2. his e3.1 eyeball (the STEP this is built from) is the one in his e3.2 print file.
  3. in his e3.1 mechanism and his a2.0.33 head, with the eyes straight ahead, no other part
     reaches into the filled region; the closest part outside the socket (the lids) is reported.

Run:  python cad/studies/cogley_eyeball.py   (after modules.py and cogley_head.py)
  -> output/plates/cogley_eyeball_smooth.stl (print pose: his, flat back on the bed, front up)
     <out>/studies/cogley_eyeball.png and .md
"""
import itertools
import json
import os
import sys

import numpy as np
import trimesh

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import cadkit as K  # noqa: E402
import geom as G  # noqa: E402
import layout_check as L  # noqa: E402
import modules as M  # noqa: E402
import read3mf  # noqa: E402

sys.stdout.reconfigure(encoding="utf-8")
P = K.params()
R = P.EYE_R
E32 = os.path.join(K.PROJECT, "output", "plates", "eyemech_e3.2_MG90s_A_cogley.3mf")
OUT = os.path.join(K.PROJECT, "output", "plates", "cogley_eyeball_smooth.stl")
TOL, ANG = 0.01, 0.05          # tessellation of the print file: mm, rad (a smooth sphere)
SAMPLE = 0.25                  # mm between surface samples in the neighbour check
EYE_RGB, NEW_RGB, OLD_RGB = (0.93, 0.92, 0.88), (0.95, 0.55, 0.15), (0.6, 0.6, 0.6)


def his_eyeball():
    """His eyeball as a solid in our eye frame: centred on its sphere, looking +y."""
    from build123d import Axis, Location, import_step
    root = import_step(os.path.join(K.inputs(), P.EYEMECH_FILE))
    eye = min((s for s in M.leaves(root) if s.label == "Component74"), key=lambda s: s.center().X)
    eye = eye.moved(Location((P.EYEMECH_EYE_SRC[0], 0, 0)))          # his right eye, centre (-37.5, 0, 0)
    return eye.rotate(Axis.Z, P.EYEMECH_ROT_Z)


def smooth(eye):
    """His eyeball cut square at EYEBALL_FILL_FROM, his back kept, a plain R16 cap in front. The two
    meet only on that flat face (fusing the cap straight onto his eyeball fails: their R16 faces
    lie on one sphere). The cap's sphere has its pole on the gaze axis, like his; with the pole
    on z the fuse comes out invalid."""
    from build123d import Box, Pos, Rot, Sphere
    f = P.EYEBALL_FILL_FROM
    (back,) = eye.intersect(Pos(0, f - 2 * R, 0) * Box(4 * R, 4 * R, 4 * R))
    cap = Rot(90, 0, 0) * Sphere(R) & Pos(0, f + R, 0) * Box(4 * R, 2 * R, 4 * R)
    return back.fuse(cap.solid()).clean()


def mesh(shape, tol=TOL, ang=ANG):
    """Mesh a solid, dropping the zero-area triangle OCC leaves at a sphere's pole."""
    v, f = shape.tessellate(tol, ang)
    m = trimesh.Trimesh(np.array([tuple(p) for p in v]), np.array(f), process=True)
    m.merge_vertices()
    m.update_faces(m.nondegenerate_faces())
    m.remove_unreferenced_vertices()
    return m


def print_pose(m):
    """Our eye frame -> his print pose: front (+y) up, the flat back on the bed, centred on x, y."""
    m = m.copy()
    m.apply_transform(trimesh.transformations.rotation_matrix(np.pi / 2, (1, 0, 0)))
    lo, hi = m.bounds
    m.apply_translation((-(lo[0] + hi[0]) / 2, -(lo[1] + hi[1]) / 2, -lo[2]))
    return m


def check_new(old, new, old_m, new_m):
    """Check 1 (on meshes: booleans between the two fail on their shared R16 sphere): valid, holds
    all of his, the same as his behind EYEBALL_FILL_FROM, inside R16."""
    f = P.EYEBALL_FILL_FROM
    pts = trimesh.sample.sample_surface_even(old_m, 20000, seed=1)[0]
    outside = float(-trimesh.proximity.signed_distance(new_m, pts).min())       # > 0: his surface outside the new
    back = []
    for a, b in ((old_m, new_m), (new_m, old_m)):
        v = a.vertices[a.vertices[:, 1] < f - 0.05]
        back.append(float(trimesh.proximity.closest_point(b, v)[1].max()))
    r_max = float(np.linalg.norm(new_m.vertices, axis=1).max())
    rows = [
        ("one valid solid", new.is_valid and len(new.solids()) == 1, f"{len(new.solids())} solid(s)"),
        ("his eyeball inside it (nothing removed)", outside < 0.05,
         f"his surface at most {max(outside, 0.0):.3f} outside the new one (mesh tolerance)"),
        ("his back and socket unchanged", max(back) < 0.05,
         f"behind y {f}: surfaces within {max(back):.3f} of each other; added {new.volume - old.volume:.1f} mm3 "
         f"in front of it (his socket stops at {P.EYE_SOCKET_FRONT:.1f})"),
        ("inside its R16 sphere", r_max <= R + 1e-3,
         f"furthest point {r_max:.3f} from the centre; lids' inside R{P.EYEMECH_EYE_R[0]}: "
         f"gap {P.EYEMECH_EYE_R[0] - r_max:.2f} at every pose"),
        ("print mesh watertight", None, ""),
    ]
    return rows


def split_added(old_m, new_m):
    """The new eyeball's surface as (his part, the filled front), to draw in two colours."""
    d = trimesh.proximity.closest_point(old_m, new_m.triangles_center)[1]
    return [new_m.submesh([np.where(sel)[0]], append=True) for sel in (d <= 0.05, d > 0.05)]


def check_e32(old_m):
    """Check 2: the e3.2 print file's eyeball against his e3.1 STEP eyeball (all 24 axis turns tried)."""
    e32 = [p["mesh"] for p in read3mf.parts(E32) if p["part"] == "Component74"][0]
    a = old_m.copy()
    a.apply_translation(-a.bounds.mean(axis=0))
    best = None
    for perm in itertools.permutations(range(3)):
        for signs in itertools.product((1, -1), repeat=3):
            T = np.eye(4)
            T[:3, :3] = np.eye(3)[list(perm)] * np.array(signs)[:, None]
            if np.linalg.det(T[:3, :3]) < 0:
                continue
            b = e32.copy()
            b.apply_transform(T)
            b.apply_translation(-b.bounds.mean(axis=0))
            if np.abs(a.extents - b.extents).max() > 0.5:
                continue
            _, d, _ = trimesh.proximity.closest_point(a, b.vertices)
            if best is None or d.max() < best[0]:
                best = (float(d.max()), abs(b.volume - a.volume) / a.volume)
    ok = best is not None and best[0] < 0.05 and best[1] < 0.005
    return ("his e3.2 print file has this eyeball", ok,
            f"its corners lie within {best[0]:.3f} of the STEP's surface, volume within {100 * best[1]:.2f} %")


def eye_centre(m):
    """Centre of an eyeball mesh's R16 sphere: x, z from its 32 mm box, y from its equator, then a
    least-squares fit to the vertices on the sphere."""
    v = m.vertices
    c = m.bounds.mean(axis=0)
    eq = np.abs(v[:, 0] - c[0]) > R - 0.1
    c[1] = v[eq, 1].mean()
    for band in (0.5, 0.05):
        s = v[np.abs(np.linalg.norm(v - c, axis=1) - R) < band]
        A = np.c_[2 * s, np.ones(len(s))]
        c = np.linalg.lstsq(A, (s ** 2).sum(axis=1), rcond=None)[0][:3]
    return c


def neighbours():
    """(source, name, mesh) for every part of his e3.1 mechanism and his a2.0.33 head, in our frame."""
    ref = G.ref_dir()
    with open(os.path.join(ref, "modules.json"), encoding="utf-8") as f:
        for e in json.load(f)["parts"]:
            if e["module"] == "eyemech":
                yield "EyeMech e3.1", e["label"], trimesh.load(os.path.join(ref, e["file"]), force="mesh")
    hd = os.path.join(ref, "head_a2")
    with open(os.path.join(hd, "index.json"), encoding="utf-8") as f:
        for e in json.load(f)["parts"]:
            yield "head a2.0.33", e["name"], trimesh.load(os.path.join(hd, "parts", e["file"]), force="mesh")


def check_neighbours():
    """Check 3: no part reaches the filled region at rest; per source, the parts inside R16 (the
    socket) and the closest part outside it."""
    parts = list(neighbours())
    rows = []
    for src in ("EyeMech e3.1", "head a2.0.33"):
        mine = [(n, m) for s, n, m in parts if s == src]
        centres = [eye_centre(m) for n, m in mine if n.startswith("Component74")]
        hits, inside, outside = [], {}, (np.inf, "")
        for c in centres:
            for n, m in mine:
                if n.startswith("Component74") or np.any(m.bounds[0] > c + R + 3) or np.any(m.bounds[1] < c - R - 3):
                    continue
                d = float(trimesh.proximity.closest_point(m, [c])[1][0])
                if d >= R:
                    if d < outside[0]:
                        outside = (d, n)
                    continue
                pts = np.vstack([m.vertices, trimesh.sample.sample_surface_even(m, int(m.area / SAMPLE ** 2) + 1)[0]])
                q = pts - c
                near = np.linalg.norm(q, axis=1) <= R
                reach = float(q[near, 1].max()) if near.any() else -np.inf
                inside[n] = max(inside.get(n, -np.inf), reach)
                if reach >= P.EYEBALL_FILL_FROM:
                    hits.append(n)
        rows.append((f"{src}: {len(centres)} eyes, nothing in the filled region", not hits and len(centres) == 2,
                     ("reaches in: " + ", ".join(sorted(set(hits)))) if hits else
                     "inside R16 (the socket): " + ", ".join(f"{n} to {y:+.1f}" for n, y in sorted(inside.items()))
                     + f"; closest outside: {outside[1]} at R{outside[0]:.2f}"))
    return rows


def render(old_m, new_m, out_dir):
    import render_views as RV
    po, pn = L.poly(old_m), L.poly(new_m)
    ph, pa = (L.poly(m) for m in split_added(old_m, new_m))
    c, sc = np.zeros(3), 1.15 * R
    three_q = (0.55, 1.0, 0.45)
    tiles = [
        ("his eyeball: iris dish + pupil hole", RV.render([RV.surface_actor(po, OLD_RGB)], c, three_q, (0, 0, 1), sc)),
        ("smooth eyeball (orange = added)", RV.render([RV.surface_actor(ph, EYE_RGB), RV.surface_actor(pa, NEW_RGB)],
                                                      c, three_q, (0, 0, 1), sc)),
        ("smooth eyeball from the back: his socket", RV.render([RV.surface_actor(pn, EYE_RGB)], c, (0.3, -1.0, 0.25),
                                                                (0, 0, 1), sc)),
    ]
    for title, n in (("side section through the centre", (1, 0, 0)), ("top section through the centre", (0, 0, 1))):
        acts = [RV.surface_actor(L.clip(ph, c, n, 2 * R), EYE_RGB), RV.surface_actor(L.clip(pa, c, n, 2 * R), NEW_RGB),
                RV.line_actor(L.cut(pn, c, n), (0, 0, 0), 2), RV.line_actor(L.cut(po, c, n), (0.1, 0.3, 0.9), 2)]
        up = (0, 0, 1) if n[2] == 0 else (0, 1, 0)
        tiles.append((title, RV.render(acts, c, n, up, sc)))
    pp = print_pose(new_m)
    tiles.append(("print pose: flat back on the bed", RV.render([RV.surface_actor(L.poly(pp), EYE_RGB)],
                                                               pp.bounds.mean(axis=0), (1.0, -0.6, 0.35), (0, 0, 1), sc)))
    return L.sheet(tiles, out_dir, "cogley_eyeball", cols=3, header_lines=[
        "Cogley's eyeball (Component74) with a plain round front: iris dish and pupil hole filled out to its R16 sphere",
        f"front up (+y); sections: black = smooth eyeball, blue = his; added plastic only in front of "
        f"{P.EYEBALL_FILL_FROM} (his socket stops at {P.EYE_SOCKET_FRONT})"])


def main():
    old = his_eyeball()
    new = smooth(old)
    old_m, new_m = mesh(old), mesh(new)
    rows = check_new(old, new, old_m, new_m)

    out_m = print_pose(new_m)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    out_m.export(OUT)
    rows[-1] = ("print mesh watertight", out_m.is_watertight and out_m.is_volume,
                f"{len(out_m.faces)} triangles, {out_m.extents[0]:.1f} x {out_m.extents[1]:.1f} x "
                f"{out_m.extents[2]:.2f}, {out_m.volume / 1000:.2f} cm3 (his {old.volume / 1000:.2f})")

    rows.append(check_e32(old_m))
    rows += check_neighbours()

    out_dir = os.path.join(K.check_out(), "studies")
    os.makedirs(out_dir, exist_ok=True)
    render(old_m, new_m, out_dir)
    ok = all(r[1] for r in rows)
    lines = ["# Cogley's eyeball, smooth front", "",
             f"Print file: `output/plates/cogley_eyeball_smooth.stl`. Result: **{'PASS' if ok else 'FAIL'}**", "",
             "| check | result | detail |", "|---|---|---|"]
    lines += [f"| {n} | {'pass' if r else 'FAIL'} | {d} |" for n, r, d in rows]
    with open(os.path.join(out_dir, "cogley_eyeball.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    for n, r, d in rows:
        print(f"{'ok   ' if r else 'FAIL '} {n}: {d}")
    print(f"wrote {os.path.relpath(OUT, K.PROJECT)} and studies/cogley_eyeball.png")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())

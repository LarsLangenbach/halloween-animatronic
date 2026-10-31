"""
Cogley's eyelids with mechanical keying for the brushed-on silicone skin (Dragon Skin FX-Pro, D21).

PLA gives platinum silicone no bond, so the grip has to come from geometry (D27). Each lid is a
1.6 mm shell between the R16.5 and R18.1 spheres about the eye centre. It gets a field of radial
through-holes: a LID_KEY_NECK_D neck from the outer face opening into a LID_KEY_HEAD_D x
LID_KEY_HEAD_H counterbore flush with the inner face. Silicone stippled through from the outside
fills the neck and the counterbore and cures into a mushroom-headed rivet; the rigid shoulder
between neck and head is the undercut the cured skin cannot pull back through. Nothing protrudes
inside (the eyeball is 0.5 mm behind the lid) or outside (the skull's eye opening is 1.9 mm away),
and the lids' motion is unchanged: material is only removed, within the existing shell.

Holes go only where the shell is plain two-face wall: the hole axis and two rings of rays round it
(at the counterbore's edge and LID_KEY_MARGIN beyond it) must all cross exactly the inner sphere and
an outer face between R18.1 and R_OUT_MAX (the flank thickens outward), nothing else: no pivot
flange, lever bore, lash edge or rim.

Built from, and written back into, his size-B print file's four lid sets (eyemech_e3.2_MG90s_B),
in his print pose, so each set stays print-in-place: lid, top-lid horn and lever in the pivot, the
horn and lever untouched.

Checks (exit 1 on a failure):
  1. the 3MF lid is his STEP lid (registered onto it, every vertex within FIT_TOL), which fixes the sphere centre
  2. the pattern: every hole passes the ring test, the nearest two counterbores leave >= MIN_WALL
  3. each cut lid is one watertight manifold, the cutters don't touch the horn or lever, and the
     volume removed is the holes' (within 10 %)
Writes output/plates/cogley_lids_keyed_plate.stl (the 4 sets on one bed), cogley_lids_keyed_plate.png,
cogley_lids_keyed.png (close-ups: outside, inside, section) and cogley_lids_keyed.md.

Not in the pipeline (his part, his print pose). Run:  python cad/lid_keyed.py
"""
import os
import sys

import manifold3d as mf
import numpy as np
import trimesh

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import cadkit as K  # noqa: E402
import cogley_plate as CP  # noqa: E402
from mold_base import from_mf, to_mf  # noqa: E402

sys.stdout.reconfigure(encoding="utf-8")
P = K.params()
R_IN, R_OUT = P.EYEMECH_EYE_R
WALL = R_OUT - R_IN
LIDS = ("LidTR", "LidBR")
OUT = os.path.join(K.PROJECT, "output", "plates")
FIT_TOL = 0.15                 # mm: max vertex distance of the 3MF lid from his STEP lid
RAY_TOL = 0.12                 # mm: a ray hit counts as "on the sphere" within this
R_OUT_MAX = 20.6               # the shell's flank thickens outward to about R20.5 (still plain two-face wall); beyond that is the pivot flange
SEGS = 32


_STEP = None


def step_lids():
    """His STEP lids (both sides), meshed, with their sphere centre: label -> [(mesh, centre), ...]."""
    global _STEP
    if _STEP is None:
        import modules as M
        from build123d import export_stl, import_step
        root = import_step(os.path.join(K.inputs(), P.EYEMECH_FILE))
        _STEP = {}
        tmp = os.path.join(K.PROJECT, "output", "plates", "_step_lid.stl")
        for s in M.leaves(root):
            if s.label in LIDS:
                export_stl(s, tmp, tolerance=0.02, angular_tolerance=0.1)
                c = np.array([np.sign(s.center().X) * P.EYEMECH_EYE_SRC[0], 0.0, 0.0])
                _STEP.setdefault(s.label, []).append((trimesh.load(tmp, force="mesh"), c))
        os.remove(tmp)
    return _STEP


def sphere_centre(m, label):
    """The lid's sphere centre in the print-file frame, by registering the 3MF lid onto his STEP
    lid (whichever side matches: the print file holds a mirror pair) and carrying the STEP's
    centre back. Returns (centre, median and max vertex distance to the STEP lid)."""
    best = None
    for ref, c_ref in step_lids()[label]:
        T, _ = trimesh.registration.mesh_other(m, ref, samples=3000, scale=False, icp_first=10, icp_final=40)
        moved = m.copy()
        moved.apply_transform(T)
        d = trimesh.proximity.closest_point(ref, moved.vertices)[1]
        if best is None or np.median(d) < best[1]:
            best = (T, float(np.median(d)), float(d.max()), c_ref)
    T, med, mx, c_ref = best
    c = (np.linalg.inv(T) @ np.r_[c_ref, 1.0])[:3]
    return c, med, mx


def plain_wall(m, c, dirs):
    """True for each direction whose ray from c crosses exactly two faces: the inner sphere, and an
    outer face between the R18.1 sphere and R_OUT_MAX (the shell's flank thickens outward)."""
    n = len(dirs)
    loc, ray, _ = m.ray.intersects_location(np.repeat(c[None], n, 0), dirs, multiple_hits=True)
    ok = np.zeros(n, bool)
    rs = [[] for _ in range(n)]
    for L, i in zip(loc, ray):
        rs[i].append(np.linalg.norm(L - c))
    for i, r in enumerate(rs):
        r = sorted(r)
        ok[i] = len(r) == 2 and abs(r[0] - R_IN) < RAY_TOL and R_OUT - RAY_TOL < r[1] < R_OUT_MAX
    return ok


def ring(d, radius, k=12):
    """k unit directions round d, `radius` mm away from its axis on the mid-wall sphere."""
    a = radius / (R_IN + WALL / 2)
    u = np.cross(d, [0, 0, 1.0])
    if np.linalg.norm(u) < 0.1:
        u = np.cross(d, [1.0, 0, 0])
    u /= np.linalg.norm(u)
    v = np.cross(d, u)
    out = []
    for t in np.linspace(0, 2 * np.pi, k, endpoint=False):
        w = np.cos(a) * d + np.sin(a) * (np.cos(t) * u + np.sin(t) * v)
        out.append(w / np.linalg.norm(w))
    return np.array(out)


def fibonacci(n):
    i = np.arange(n) + 0.5
    phi = np.arccos(1 - 2 * i / n)
    th = np.pi * (1 + 5 ** 0.5) * i
    return np.c_[np.cos(th) * np.sin(phi), np.sin(th) * np.sin(phi), np.cos(phi)]


def pattern(m, c):
    """Hole directions: a Fibonacci set at LID_KEY_PITCH on the mid-wall sphere, kept where the
    axis, the counterbore's rim and the margin ring all pass through plain wall."""
    r_mid = R_IN + WALL / 2
    n = int(round(4 * np.pi * r_mid ** 2 / (0.866 * P.LID_KEY_PITCH ** 2)))
    dirs = fibonacci(n)
    head_r = P.LID_KEY_HEAD_D / 2
    keep = []
    for d in dirs:
        test = np.vstack([d[None], ring(d, head_r), ring(d, head_r + P.LID_KEY_MARGIN)])
        if plain_wall(m, c, test).all():
            keep.append(d)
    return np.array(keep)


def cutters(c, dirs):
    """One manifold: for each hole the neck (through the whole wall) and the counterbore."""
    parts = []
    r0 = R_IN - 1.0
    for d in dirs:
        z = d / np.linalg.norm(d)
        x = np.cross(z, [0, 0, 1.0])
        if np.linalg.norm(x) < 0.1:
            x = np.cross(z, [1.0, 0, 0])
        x /= np.linalg.norm(x)
        y = np.cross(z, x)
        M = np.c_[np.c_[x, y, z], c + z * r0]                                  # 3x4: columns x y z, origin
        neck = mf.Manifold.cylinder(R_OUT_MAX + 1.0 - r0, P.LID_KEY_NECK_D / 2, P.LID_KEY_NECK_D / 2, SEGS)
        head = mf.Manifold.cylinder(1.0 + P.LID_KEY_HEAD_H, P.LID_KEY_HEAD_D / 2, P.LID_KEY_HEAD_D / 2, SEGS)
        parts += [neck.transform(M), head.transform(M)]
    return mf.Manifold.batch_boolean(parts, mf.OpType.Add)


def hole_volume(m, c, dirs):
    """The holes' volume from the local wall under each: neck through the wall minus the head's depth, plus the head."""
    n = len(dirs)
    loc, ray, _ = m.ray.intersects_location(np.repeat(c[None], n, 0), dirs, multiple_hits=True)
    rs = [[] for _ in range(n)]
    for L, i in zip(loc, ray):
        rs[i].append(np.linalg.norm(L - c))
    walls = np.array([max(r) - min(r) for r in rs])
    return float((np.pi * (P.LID_KEY_NECK_D / 2) ** 2 * (walls - P.LID_KEY_HEAD_H)
                  + np.pi * (P.LID_KEY_HEAD_D / 2) ** 2 * P.LID_KEY_HEAD_H).sum()), walls


def key_lid(lid, label, others):
    """Returns (cut lid mesh, report dict, list of failures)."""
    fails = []
    c, med, mx = sphere_centre(lid, label)
    rep = dict(centre=c, fit_med=med, fit_max=mx)
    if mx > FIT_TOL:
        fails.append(f"lid is not his STEP lid: vertex distance median {med:.3f}, max {mx:.3f} > {FIT_TOL}")
    dirs = pattern(lid, c)
    rep["holes"] = len(dirs)
    if len(dirs) < 2:
        fails.append(f"only {len(dirs)} hole(s) found")
        return lid, rep, fails
    r_mid = R_IN + WALL / 2
    pts = c + dirs * r_mid
    dd = np.linalg.norm(pts[:, None] - pts[None], axis=2) + np.eye(len(pts)) * 1e9
    rep["min_pitch"] = float(dd.min())
    rep["min_wall"] = float(dd.min() - P.LID_KEY_HEAD_D)
    if rep["min_wall"] < P.MIN_WALL:
        fails.append(f"counterbores too close: {rep['min_wall']:.2f} wall < MIN_WALL {P.MIN_WALL}")
    cut = cutters(c, dirs)
    for name, o in others:
        v = (to_mf(o) ^ cut).volume()
        if v > 1e-3:
            fails.append(f"cutters reach into {name}: {v:.2f} mm^3")
    lid_mf = to_mf(lid)
    out = lid_mf - cut
    if out.status() != mf.Error.NoError or out.decompose().__len__() != 1:
        fails.append(f"cut lid is not one manifold: {out.status()}, {len(out.decompose())} piece(s)")
    removed = lid_mf.volume() - out.volume()
    rep["removed"] = removed
    rep["expected"], walls = hole_volume(lid, c, dirs)
    rep["wall_range"] = (float(walls.min()), float(walls.max()))
    if abs(removed - rep["expected"]) > 0.10 * rep["expected"]:
        fails.append(f"volume removed {removed:.1f} vs the holes' {rep['expected']:.1f}")
    m = from_mf(out)
    if not m.is_watertight:
        fails.append("cut lid mesh is not watertight")
    rep["dirs"] = dirs
    return m, rep, fails


def closeups(lid_old, lid_new, c, dirs, path):
    """Three tiles of one top lid: outside, inside (into the counterbores), and a section through
    the eye centre and the hole nearest the lid's middle, seen square on."""
    import render_views as RV
    import mold_check as MC
    from PIL import Image, ImageDraw
    rgb_new = (0.95, 0.55, 0.15)
    look = lid_new.centroid - c                     # from the eye centre out through the lid
    look /= np.linalg.norm(look)
    up = np.cross(np.cross(look, [0, 0, 1.0]), look)
    up /= np.linalg.norm(up)
    half = 16.0
    tiles = []
    acts = [RV.surface_actor(MC.poly(lid_new), rgb_new)]
    tiles.append(("outside: the necks", RV.render(acts, lid_new.centroid, look, up, half)))
    tiles.append(("inside: the counterbores", RV.render(acts, lid_new.centroid, -look, up, half)))
    d0 = dirs[np.argmax(dirs @ look)]               # the hole nearest the lid's middle
    nrm = np.cross(d0, up)
    nrm /= np.linalg.norm(nrm)
    kept = from_mf(to_mf(lid_new).trim_by_plane(tuple(-nrm), float(-nrm @ c)))   # the half behind the plane
    acts = [RV.surface_actor(MC.poly(kept), rgb_new)]
    tiles.append(("section through the eye centre and a hole", RV.render(acts, lid_new.centroid, nrm, up, half)))
    W = RV.TILE
    sheet = Image.new("RGB", (3 * W, W + 70), "white")
    dr = ImageDraw.Draw(sheet)
    dr.text((10, 8), f"Keyed lid: {P.LID_KEY_NECK_D} necks, {P.LID_KEY_HEAD_D} x {P.LID_KEY_HEAD_H} counterbores "
                     f"flush with the inner face, {P.LID_KEY_PITCH} pitch; radial from the eye centre", fill="black")
    for k, (t, im) in enumerate(tiles):
        sheet.paste(im, (k * W, 60))
        dr.text((k * W + 8, 40), t, fill="black")
    sheet.save(path)


def main():
    os.makedirs(OUT, exist_ok=True)
    bed = K.printer()["bed"]
    objs = CP.posed_objects(CP.EYEMECH_B)
    groups, rows, fails = [], [], []
    first = None
    for oid, parts in objs.items():
        lids = [(pn, m) for pn, m in parts if pn in LIDS]
        if not lids:
            continue
        pn, lid = lids[0]
        others = [(q, m) for q, m in parts if q not in LIDS]
        new, rep, f = key_lid(lid, pn, others)
        fails += [f"{pn} (object {oid}): {x}" for x in f]
        rows.append((pn, oid, rep))
        groups.append([new] + [m for _, m in others])
        print(f"{pn} (object {oid}): {rep['holes']} holes, STEP fit median {rep['fit_med']:.3f} max {rep['fit_max']:.3f}, "
              f"nearest holes {rep.get('min_pitch', 0):.2f} apart ({rep.get('min_wall', 0):.2f} wall), "
              f"removed {rep.get('removed', 0):.0f} mm^3 of {lid.volume:.0f}, wall under the holes {rep.get('wall_range', (0, 0))[0]:.1f}..{rep.get('wall_range', (0, 0))[1]:.1f}"
              + (f"  FAIL: {'; '.join(f)}" if f else ""))
        if first is None and pn == "LidTR":
            first = (lid, new, rep["centre"], rep["dirs"])
    placed = CP.layout(groups, bed)
    plate = trimesh.util.concatenate([m for g in placed for m in g])
    plate.export(os.path.join(OUT, "cogley_lids_keyed_plate.stl"))
    e = plate.extents
    print(f"wrote plates/cogley_lids_keyed_plate.stl  {len(groups)} sets, {e[0]:.1f} x {e[1]:.1f} x {e[2]:.1f} mm")
    CP.preview(placed, os.path.join(OUT, "cogley_lids_keyed_plate.png"), bed,
               "cogley_lids_keyed_plate: his 4 lid sets, lids perforated for the skin (his print pose): top view, iso")
    if first:
        closeups(*first, os.path.join(OUT, "cogley_lids_keyed.png"))
    ok = not fails
    lines = ["# Keyed lids (D27)", "",
             f"Cogley's four lid sets from `eyemech_e3.2_MG90s_B_cogley.3mf`, each lid perforated for the brushed "
             f"silicone skin: Ø{P.LID_KEY_NECK_D} radial through-holes with a Ø{P.LID_KEY_HEAD_D} × {P.LID_KEY_HEAD_H} "
             f"counterbore flush with the inner face, {P.LID_KEY_PITCH} mm apart, only through plain {WALL:.1f} mm wall "
             f"with {P.LID_KEY_MARGIN} mm kept round each counterbore. Built by `cad/lid_keyed.py`. "
             f"Result: **{'PASS' if ok else 'FAIL'}**", "",
             "| set | holes | STEP fit median / max | nearest holes | wall between counterbores | removed mm³ |", "|---|---|---|---|---|---|"]
    for pn, oid, rep in rows:
        lines.append(f"| {pn} (object {oid}) | {rep['holes']} | {rep['fit_med']:.3f} / {rep['fit_max']:.3f} | {rep.get('min_pitch', 0):.2f} | "
                     f"{rep.get('min_wall', 0):.2f} | {rep.get('removed', 0):.0f} |")
    lines += ["", "Plate: `cogley_lids_keyed_plate.stl` (preview `cogley_lids_keyed_plate.png`); close-ups "
              "`cogley_lids_keyed.png`.", ""]
    if fails:
        lines += ["Failures:"] + [f"- {x}" for x in fails]
    with open(os.path.join(OUT, "cogley_lids_keyed.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    for x in fails:
        print("FAIL ", x)
    print("LIDS KEYED OK" if ok else "LIDS KEYED FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())

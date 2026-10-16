"""
M1 pose sweeps and reserved space: move what moves and check what it hits.
(The rest pose is layout_check's job.)

  jaw    opens about the jaw axis (x direction through geom.jaw_axis) from 0
         to JAW_OPEN_DEG in SWEEP_STEP_DEG steps, then JAW_OVERTRAVEL_DEG more.
         Jaw group: see groups(). "Inside skull": the worst jaw point against the
         skull's inner surface (lip plates: the skin's inner surface). At each angle: new overlap with everything
         that doesn't ride on the jaw (contacts already there at rest are
         designed and ignored), the closest gap, and how far the chin drops.
  eyes   pan +-EYE_PAN_DEG and tilt +-EYE_TILT_DEG about each eye centre.
  lids   top lids open 0..LID_TOP_OPEN_DEG, bottom lids 0..LID_BOTTOM_OPEN_DEG,
         about the lid axis (x direction through both eye centres).
  space  the reserved volumes (reserve.py: brows, cable) against every part
         at rest and every swept pose of the jaw, eyes and lids.

Overlaps are manifold booleans. Gaps come from a KD-tree over seeded surface
samples, with exact distances for the 12 nearest candidates per part; they can
read up to ~0.4 mm high.

Run:  python cad/pose_sweep.py      (after modules.py, head.py and reserve.py)
  -> <out>/sweep/sweep.md, sweep.png (+ tiles); output/ref/sweep/*.stl
Final line: SWEEP OK, or SWEEP: n issue(s), each listed as a WARN line.
"""
import os
import sys
import warnings

import manifold3d as mf
import numpy as np
import trimesh
from scipy.spatial import cKDTree

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import cadkit as K  # noqa: E402
import geom as G  # noqa: E402
import head as H  # noqa: E402
import layout_check as L  # noqa: E402
import reserve as R  # noqa: E402

warnings.filterwarnings("ignore", category=RuntimeWarning)
sys.stdout.reconfigure(encoding="utf-8")
P = K.params()
S = P.HEAD_SCALE
NOISE = 1.0               # mm3
CONTACT = 0.05            # mm: pairs touching at rest (or overlapping, e.g. a screw in its hole) are
                          # designed contacts; their overlap may not grow. 0.5 hid a real tongue
                          # collision whose rest gap is 0.49 (review 2026-10-15)
RESERVE_COLOURS = {"brow_L": (0.62, 0.42, 0.85), "brow_R": (0.62, 0.42, 0.85), "cable": (0.95, 0.85, 0.2)}


# ---------------------------------------------------------------------------
# motion groups and transforms
# ---------------------------------------------------------------------------
def rot_x(deg, point):
    return trimesh.transformations.rotation_matrix(np.radians(deg), [1, 0, 0], point)


def rot_z(deg, point):
    return trimesh.transformations.rotation_matrix(np.radians(deg), [0, 0, 1], point)


def dist_to(p, others):
    """Closest distance between part p's samples and any of `others`' samples
    (KD-tree; good to the sample spacing, ~2 mm, which is enough to tell which
    side a part is fastened to)."""
    pts = [o["p"] for o in others if o is not p]
    if not pts:
        return np.inf
    return float(cKDTree(np.vstack(pts)).query(p["p"])[0].min())


def groups(parts):
    """Motion groups. The jaw starts from JAW_GROUP_CORE; a mouth part centred at
    least JAW_GROUP_BELOW_AXIS below the axis joins it when it sits closer to the
    jaw's parts than to the frame's, chained outward (a screw on a servo on the
    jaw base). A height rule alone put eight frame screws on the jaw."""
    ya, za = G.jaw_axis(S)
    ez = G.eye_z(S)
    out = {"jaw": [], "eyes": [], "lids_top": [], "lids_bottom": [], "static": []}
    mouth = [p for p in parts if p["module"] == "mouth"]
    jaw = [p for p in mouth if p["label"] in P.JAW_GROUP_CORE]
    cand = [p for p in mouth if p not in jaw and p["m"].bounds.mean(axis=0)[2] < za - P.JAW_GROUP_BELOW_AXIS]
    frame = [p for p in mouth if p not in jaw and p not in cand]
    for _ in range(4):
        moved_any = False
        for p in list(cand):
            dj, df = dist_to(p, jaw), dist_to(p, frame)
            if dj < df:
                jaw.append(p)
                cand.remove(p)
                moved_any = True
        if not moved_any:
            break
    for p in frame:                                   # MG996R output: horn, spline, horn screws
        c = p["m"].bounds.mean(axis=0)
        if abs(c[0]) >= P.JAW_HORN_X_MIN and np.hypot(c[1] - ya, c[2] - za) <= P.JAW_HORN_R:
            jaw.append(p)
    out["jaw"] = jaw
    for p in parts:
        if p in jaw:
            continue
        c = p["m"].bounds.mean(axis=0)
        if p["group"] == "eyes":
            out["eyes"].append(p)
        elif p["group"] == "lids":
            out["lids_top" if c[2] > ez else "lids_bottom"].append(p)
        else:
            out["static"].append(p)
    return out


def jaw_tf(angle):
    ya, za = G.jaw_axis(S)
    return rot_x(-angle, (0.0, ya, za))             # opening swings the chin down and back


def lid_tf(which, angle):
    return rot_x(angle if which == "lids_top" else -angle, (0.0, 0.0, G.eye_z(S)))


def eye_tfs(p_deg, t_deg):
    """Per-eye transforms: tilt about x, then pan about z, each about its own centre."""
    ez = G.eye_z(S)
    out = {}
    for sx in (+1, -1):
        c = (sx * P.EYE_SPACING / 2, 0.0, ez)
        out[sx] = rot_z(p_deg, c) @ rot_x(t_deg, c)
    return out


def apply(pts, tf):
    return pts @ tf[:3, :3].T + tf[:3, 3]


def to_mf(mesh, tf=None):
    m = R.to_mf(mesh)
    return m.transform(tf[:3, :].tolist()) if tf is not None else m


def union(meshes, tf=None):
    ms = [to_mf(m, tf) for m in meshes]
    return mf.Manifold.batch_boolean(ms, mf.OpType.Add) if ms else mf.Manifold()


def solid(p):
    return p["watertight"] and not p["shell"]


# ---------------------------------------------------------------------------
# measuring
# ---------------------------------------------------------------------------
def nearest_gap(moving, tf, targets, skip_pairs=frozenset(), refine=48):
    """Closest gap between the moving parts (under tf) and the target parts,
    ignoring designed-contact pairs. Returns (gap, moving label, target label)."""
    tp = np.vstack([t["p"] for t in targets])
    ti = np.concatenate([[i] * len(t["p"]) for i, t in enumerate(targets)])
    tree = cKDTree(tp)
    best = (np.inf, "", "")
    for mi, m in enumerate(moving):
        pts = apply(m["p"], tf) if tf is not None else m["p"]
        d, j = tree.query(pts, k=4)
        order = np.dstack(np.unravel_index(np.argsort(d, axis=None), d.shape))[0]
        tried = 0
        for k, col in order:
            tj = ti[j[k, col]]
            if (m["label"], targets[tj]["label"], mi, tj) in skip_pairs:
                continue
            exact = float(trimesh.proximity.closest_point(targets[tj]["m"], pts[k:k + 1])[1][0])
            if exact < best[0]:
                best = (exact, m["label"], targets[tj]["label"])
            tried += 1
            if tried >= refine // 4:
                break
    return best


def contact_pairs(moving, targets, within=CONTACT):
    """(moving label, target label, i, j) of pairs already within `within` at rest."""
    tp = np.vstack([t["p"] for t in targets])
    ti = np.concatenate([[i] * len(t["p"]) for i, t in enumerate(targets)])
    tree = cKDTree(tp)
    pairs = set()
    for mi, m in enumerate(moving):
        d, j = tree.query(m["p"])
        for k in np.where(d < within + 2.0)[0]:
            t = targets[ti[j[k]]]
            exact = float(trimesh.proximity.closest_point(t["m"], m["p"][k:k + 1])[1][0])
            if exact < within:
                pairs.add((m["label"], t["label"], mi, int(ti[j[k]])))
    # also pairs whose solids overlap at rest (a screw through a hole) without a close sample
    for mi, m in enumerate(moving):
        for tj, t in enumerate(targets):
            if L.gap(m["m"].bounds, t["m"].bounds) > 0 or not (solid(m) and solid(t)):
                continue
            if (to_mf(m["m"]) ^ to_mf(t["m"])).volume() > 0.01:
                pairs.add((m["label"], t["label"], mi, tj))
    return frozenset(pairs)


def overlap_volumes(moving, tf, targets):
    """{(i, j): mm3} for solid (moving, target) pairs that overlap under tf (None = rest)."""
    out = {}
    for mi, m in enumerate(moving):
        if not solid(m):
            continue
        mm = m["m"].copy()
        if tf is not None:
            mm.apply_transform(tf)
        for tj, t in enumerate(targets):
            if not solid(t) or L.gap(mm.bounds, t["m"].bounds) > 0:
                continue
            v = (to_mf(m["m"], tf) ^ to_mf(t["m"])).volume()
            if v > 0.01:
                out[(mi, tj)] = v
    return out


def accepted(a, b, extra):
    """The ACCEPTED_CONTACTS entry covering this clash, or None."""
    for (la, lb), vmax, why in P.ACCEPTED_CONTACTS:
        if (a, b) == (la, lb) and extra <= vmax:
            return why
    return None


def pair_overlaps(moving, tf, targets, rest_vol):
    """Pairs whose overlap under tf exceeds their overlap at rest by more than
    NOISE. Designed overlaps (a screw in its hole) may stay, but may not grow.
    Returns (hits, accepted): lists of (extra mm3, a, b[, why])."""
    hits, ok = [], []
    for (mi, tj), v in overlap_volumes(moving, tf, targets).items():
        extra = v - rest_vol.get((mi, tj), 0.0)
        if extra > NOISE:
            a, b = moving[mi]["label"], targets[tj]["label"]
            why = accepted(a, b, extra)
            (ok if why else hits).append((extra, a, b) + ((why,) if why else ()))
    return sorted(hits, reverse=True), sorted(ok, reverse=True)


def inside_count(mesh, pts):
    lo, hi = mesh.bounds
    near = np.all((pts >= lo - 1) & (pts <= hi + 1), axis=1)
    if not near.any():
        return 0
    return int(mesh.contains(pts[near]).sum())


def gap_to(mesh, pts, tree=None):
    """Closest unsigned distance from points to a mesh surface (KD screen, exact refine)."""
    surf = tree if tree is not None else cKDTree(trimesh.sample.sample_surface(mesh, 20000, seed=3)[0])
    d, _ = surf.query(pts)
    cand = pts[np.argsort(d)[:40]]
    return float(trimesh.proximity.closest_point(mesh, cand)[1].min())


# ---------------------------------------------------------------------------
def main():
    base_scale, parts = L.load_parts()
    L.place(parts, base_scale, S)
    gr = groups(parts)
    moving_all = gr["jaw"] + gr["eyes"] + gr["lids_top"] + gr["lids_bottom"]
    static = gr["static"]
    not_jaw = [p for p in parts if p not in gr["jaw"]]
    issues, md = [], ["# M1 pose sweeps and reserved space", "",
                      f"Head scale {S}. Angles from the modelled pose (jaw closed, lids closed, eyes ahead). "
                      "Gaps in mm; overlaps in mm3. Contacts already present at rest are designed and ignored; "
                      "pairs already closer than MOTION_CLEAR_MIN at rest are only checked for overlap.", ""]
    print(f"groups: jaw {len(gr['jaw'])}, eyes {len(gr['eyes'])}, top lids {len(gr['lids_top'])}, "
          f"bottom lids {len(gr['lids_bottom'])}, static {len(static)}")
    md += ["Jaw group: " + ", ".join(sorted({p['label'] for p in gr['jaw']})), ""]

    # ---- jaw -------------------------------------------------------------
    rest_vol = overlap_volumes(gr["jaw"], None, not_jaw)                 # designed overlaps at rest
    near_rest = contact_pairs(gr["jaw"], not_jaw, P.MOTION_CLEAR_MIN) | frozenset(
        (gr["jaw"][i]["label"], not_jaw[j]["label"], i, j) for i, j in rest_vol)  # already this tight at
                                                                           # rest: skipped for gaps only
    jaw_solids = [p["m"] for p in gr["jaw"] if solid(p)]
    jaw_pts0 = np.vstack([p["p"] for p in gr["jaw"]])
    z0, y0 = jaw_pts0[:, 2].min(), jaw_pts0[:, 1].max()
    angles = np.arange(0.0, P.JAW_OPEN_DEG + P.JAW_OVERTRAVEL_DEG + 1e-6, P.SWEEP_STEP_DEG)
    upper = np.vstack([p["p"] for p in parts if p["label"] in P.UPPER_LIP_PLATES])
    lower_idx = [i for i, p in enumerate(gr["jaw"]) if p["label"] in P.LOWER_LIP_PLATES]
    md += ["## Jaw", "", "| open deg | new overlap (pair) | closest gap (pair) | chin drop | chin back | lip plate opening | inside skull |",
           "|---|---|---|---|---|---|---|"]
    jaw_inset = [P.SKIN_T if p["group"] == "lips" else P.SKIN_T + P.SKULL_WALL for p in gr["jaw"]]
    jaw_limit, jaw_rows, swept, accepted_seen = None, [], [], {}
    for a in angles:
        tf = jaw_tf(a)
        hits, ok = pair_overlaps(gr["jaw"], tf, not_jaw, rest_vol) if a > 0 else ([], [])
        for extra, la, lb, why in ok:
            accepted_seen.setdefault((la, lb, why), []).append((a, extra))
        g = nearest_gap(gr["jaw"], tf, not_jaw, near_rest)
        pts = apply(jaw_pts0, tf)
        swept.append(pts)
        drop, back = z0 - pts[:, 2].min(), y0 - pts[:, 1].max()
        lower = np.vstack([apply(gr["jaw"][i]["p"], tf) for i in lower_idx])
        front = lambda q: q[q[:, 1] > q[:, 1].max() - 8.0]     # the front 8 mm of the plates
        opening = float(front(upper)[:, 2].min() - front(lower)[:, 2].max())
        inside = min(float(G.envelope_margin(apply(p["p"], tf), S, ins).min())
                     for p, ins in zip(gr["jaw"], jaw_inset))
        ov = (f"{hits[0][0]:.0f} ({hits[0][1]} / {hits[0][2]})" if hits
              else f"accepted {ok[0][0]:.0f} ({ok[0][1]} / {ok[0][2]})" if ok else "none")
        jaw_rows.append((a, hits, g))
        md.append(f"| {a:.0f} | {ov} | {g[0]:.1f} ({g[1]} / {g[2]}) | {drop:.1f} | {back:.1f} | {opening:.1f} | {inside:+.1f} |")
        if jaw_limit is None and (hits or g[0] < P.MOTION_CLEAR_MIN) and a > 0:
            jaw_limit = a
        print(f"jaw {a:4.0f} deg: overlap {ov}, gap {g[0]:.1f} ({g[1]} / {g[2]}), chin drop {drop:.1f}")
    clean = [a for a, h, g in jaw_rows if a == 0 or (not h and g[0] >= P.MOTION_CLEAR_MIN)]
    last_clean = max([a for a in clean if all(b in clean for b in angles[angles <= a])], default=0.0)
    for (la, lb, why), hits_at in accepted_seen.items():
        md += ["", f"Accepted contact: {la} / {lb}, up to {max(v for _, v in hits_at):.1f} mm3 between "
                   f"{min(a for a, _ in hits_at):.0f} and {max(a for a, _ in hits_at):.0f} deg ({why})."]
        print(f"info  accepted: {la} / {lb} up to {max(v for _, v in hits_at):.1f} mm3 ({why})")
    md += ["", f"Jaw clean to {last_clean:.0f} deg (needed {P.JAW_OPEN_DEG:.0f}). "
               "Lip plate opening: vertical gap between the front 8 mm of the upper and lower lip plates "
               "(the silicone lips add their own thickness). Chin drop and chin back: the lowest and "
               "frontmost jaw points.", ""]
    if last_clean < P.JAW_OPEN_DEG:
        a, h, g = next(r for r in jaw_rows if r[0] == min(x for x in angles if x > last_clean))
        what = f"{h[0][1]} hits {h[0][2]} ({h[0][0]:.0f} mm3)" if h else f"{g[1]} within {g[0]:.1f} of {g[2]}"
        issues.append(f"jaw clean only to {last_clean:.0f} deg of {P.JAW_OPEN_DEG:.0f}: at {a:.0f} deg {what}")
    jaw_swept = np.vstack([s for a, s in zip(angles, swept) if a <= P.JAW_OPEN_DEG])

    # ---- eyes and lids ----------------------------------------------------
    eye_pts, eye_margin = [], np.inf
    for pd in (-P.EYE_PAN_DEG, 0.0, P.EYE_PAN_DEG):
        for td in (-P.EYE_TILT_DEG, 0.0, P.EYE_TILT_DEG):
            tfs = eye_tfs(pd, td)
            for p in gr["eyes"]:
                sx = 1 if p["m"].bounds.mean(axis=0)[0] > 0 else -1
                pts = apply(p["p"], tfs[sx])
                eye_pts.append(pts)
                eye_margin = min(eye_margin, float(G.envelope_margin(pts, S, 0.0).min()))
    eye_pts = np.vstack(eye_pts)
    lid_pts, lid_margin = [], np.inf
    for which, top in (("lids_top", P.LID_TOP_OPEN_DEG), ("lids_bottom", P.LID_BOTTOM_OPEN_DEG)):
        for a in np.arange(0.0, top + 1e-6, P.SWEEP_STEP_DEG):
            pts = apply(np.vstack([p["p"] for p in gr[which]]), lid_tf(which, a))
            lid_pts.append(pts)
            lid_margin = min(lid_margin, float(G.envelope_margin(pts, S, 0.0).min()))
    lid_pts = np.vstack(lid_pts)
    md += ["## Eyes and lids", "",
           f"- Eyes, pan +-{P.EYE_PAN_DEG:.0f}, tilt +-{P.EYE_TILT_DEG:.0f}: closest to the outer skin {eye_margin:+.1f} (+ = behind it).",
           f"- Lids, top 0..{P.LID_TOP_OPEN_DEG:.0f}, bottom 0..{P.LID_BOTTOM_OPEN_DEG:.0f}: closest to the outer skin {lid_margin:+.1f}.",
           "- Lids, eyes and the EyeMech's own parts are Cogley's design; only what they sweep into outside the module is checked here.", ""]
    for what, m in (("eyes", eye_margin), ("lids", lid_margin)):
        if m < 0:
            issues.append(f"{what} reach {-m:.1f} past the outer skin during their sweep")

    # ---- reserved space ---------------------------------------------------
    rdir = os.path.join(G.ref_dir(), "reserve")
    reserves = {n: trimesh.load(os.path.join(rdir, n + ".stl"), force="mesh") for n in ("brow_L", "brow_R", "cable")}
    all_static_solid = union([p["m"] for p in parts if solid(p)])
    md += ["## Reserved space", "", "| volume | size (x, y, z) | overlap with parts at rest | closest part at rest | jaw sweep | lid sweep | eye sweep | inside skull |",
           "|---|---|---|---|---|---|---|---|"]
    for name, rm in reserves.items():
        ov = (R.to_mf(rm) ^ all_static_solid).volume()
        g_rest = nearest_gap([dict(p=trimesh.sample.sample_surface(rm, 4000, seed=5)[0], label=name)], None, parts)
        tree = cKDTree(trimesh.sample.sample_surface(rm, 20000, seed=3)[0])
        res = {}
        for what, pts in (("jaw", jaw_swept), ("lids", lid_pts), ("eyes", eye_pts)):
            n_in = inside_count(rm, pts)
            res[what] = (n_in, gap_to(rm, pts, tree))
        sp = trimesh.sample.sample_surface(rm, 6000, seed=6)[0]
        sp = sp[sp[:, 2] > 2.0]                       # the cable exits through the base at z = 0
        skull = float(G.envelope_margin(sp, S, P.SKIN_T + P.SKULL_WALL).min())
        ext = rm.extents
        md.append(f"| {name} | {ext[0]:.0f} x {ext[1]:.0f} x {ext[2]:.0f} | {ov:.0f} | {g_rest[0]:.1f} ({g_rest[2]}) | "
                  + " | ".join(f"{'HIT ' + str(n) + ' pts' if n else f'{d:.1f}'}" for n, d in res.values())
                  + f" | {skull:+.1f} |")
        if ov > NOISE:
            issues.append(f"{name} overlaps parts at rest ({ov:.0f} mm3, nearest {g_rest[2]})")
        elif g_rest[0] < P.MOTION_CLEAR_MIN:
            issues.append(f"{name} only {g_rest[0]:.1f} from {g_rest[2]} at rest")
        for what, (n_in, d) in res.items():
            if n_in:
                issues.append(f"{name}: the {what} sweep enters it ({n_in} sample points)")
            elif d < P.MOTION_CLEAR_MIN:
                issues.append(f"{name}: the {what} sweep comes within {d:.1f}")
        if name == "cable" and skull < 0:
            issues.append(f"cable channel {-skull:.1f} outside the skull's inner surface")
        print(f"{name}: rest overlap {ov:.0f} mm3, gap {g_rest[0]:.1f} ({g_rest[2]}); "
              + ", ".join(f"{w} {'HIT' if n else f'{d:.1f}'}" for w, (n, d) in res.items()) + f"; skull {skull:+.1f}")
    md += ["", "Brow volumes are trimmed by the skin's inner surface on purpose (the carrier works under the skin), "
               "so only the cable channel is held to the skull's inner surface.", ""]

    # ---- swept volumes for later milestones, renders --------------------------
    sdir = os.path.join(G.ref_dir(), "sweep")
    os.makedirs(sdir, exist_ok=True)
    jaw_open = trimesh.util.concatenate([p["m"].copy().apply_transform(jaw_tf(P.JAW_OPEN_DEG)) for p in gr["jaw"]])
    jaw_open.export(os.path.join(sdir, "jaw_open.stl"))
    out_dir = os.path.join(K.check_out(), "sweep")
    try:
        img = render(parts, gr, reserves, out_dir)
        md += [f"Renders: {os.path.basename(img)} (and sweep_1..6.png)"]
        print("wrote", img)
    except Exception as e:                            # noqa: BLE001
        print(f"WARN  render failed: {e}")
        issues.append("render failed")

    md += ["", "## Issues", ""] + ([f"- {i}" for i in issues] or ["none"])
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, "sweep.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(md) + "\n")
    print()
    for i in issues:
        print("WARN ", i)
    print("\nSWEEP OK" if not issues else f"\nSWEEP: {len(issues)} issue(s)")
    return 0


# ---------------------------------------------------------------------------
def render(parts, gr, reserves, out_dir):
    import render_views as RV
    s = S
    envs = H.envelopes(s)
    epolys = {k: L.poly(m) for k, m in envs.items()}
    b = envs["head_outer"].bounds
    centre = (b[0] + b[1]) / 2
    view_scale = 0.32 * float(max(b[1] - b[0]))           # zoomed on the face
    ez = G.eye_z(s)
    focus = np.array([0.0, -30.0, ez - 40.0])

    def cat(ps, tf=None):
        ms = [p["m"].copy() for p in ps]
        if tf is not None:
            for m in ms:
                m.apply_transform(tf)
        return L.poly(trimesh.util.concatenate(ms))

    static_eye = [p for p in gr["static"] if p["module"] == "eyemech"]
    static_mouth = [p for p in gr["static"] if p["module"] == "mouth"]
    base = [(cat(static_eye), L.COLOURS[("eyemech", "frame")]), (cat(static_mouth), L.COLOURS[("mouth", "frame")]),
            (cat(gr["eyes"]), L.COLOURS[("eyemech", "eyes")])]
    jaw_poses = [(0.0, (0.98, 0.80, 0.45)), (P.JAW_OPEN_DEG / 2, (0.95, 0.62, 0.25)), (P.JAW_OPEN_DEG, (0.80, 0.35, 0.10))]
    lid_closed = [(cat(gr["lids_top"] + gr["lids_bottom"]), L.COLOURS[("eyemech", "lids")])]
    lid_open = [(cat(gr["lids_top"], lid_tf("lids_top", P.LID_TOP_OPEN_DEG)), (0.75, 0.30, 0.30)),
                (cat(gr["lids_bottom"], lid_tf("lids_bottom", P.LID_BOTTOM_OPEN_DEG)), (0.75, 0.30, 0.30))]
    rpolys = [(L.poly(m), RESERVE_COLOURS[n]) for n, m in reserves.items()]

    def section(title, o, n, up, items, centre_at, scale=view_scale):
        actors = []
        for pp, rgb in items:
            actors.append(RV.surface_actor(L.clip(pp, o, n), rgb))
            actors.append(RV.line_actor(L.cut(pp, o, n), (0, 0, 0), 2))
        for k, ep in epolys.items():
            rgb, w = L.LINES[k]
            actors.append(RV.line_actor(L.cut(ep, o, n), rgb, w))
        c = np.array(centre_at, float)
        ax = int(np.argmax(np.abs(n)))
        c[ax] = o[ax]
        return (title, RV.render(actors, c, n, up, scale))

    tiles = []
    jaw_items = [(cat(gr["jaw"], jaw_tf(a)), rgb) for a, rgb in jaw_poses]
    tiles.append(section(f"jaw 0 / {P.JAW_OPEN_DEG / 2:.0f} / {P.JAW_OPEN_DEG:.0f} deg, side section x = 0",
                         (0, 0, 0), (1, 0, 0), (0, 0, 1), base + jaw_items + rpolys, focus))
    x_link = float(next(p for p in gr["jaw"] if p["label"] == "Part_33")["m"].bounds[1][0]) - 6.0  # near its bore
    tiles.append(section(f"jaw sweep, side section x = {x_link:.0f} (jaw link)", (x_link, 0, 0), (1, 0, 0), (0, 0, 1),
                         base + jaw_items, focus))
    xe = P.EYE_SPACING / 2
    tiles.append(section(f"lids closed and open, brow bay, section x = {xe:.1f} (left eye)", (xe, 0, 0), (1, 0, 0), (0, 0, 1),
                         base + lid_closed + lid_open + rpolys, focus + np.array([0, 20, 40])))
    tiles.append(section(f"brow bays, front section y = 10", (0, 10, 0), (0, 1, 0), (0, 0, 1),
                         base + lid_open + rpolys, focus + np.array([0, 0, 40])))
    for title, d in (("reserved space: brows purple, cable yellow, head 15 %", (0.8, 1.0, 0.45)),
                     ("from behind: cable channel to the neck", (-0.6, -1.0, 0.3))):
        actors = [RV.surface_actor(pp, rgb) for pp, rgb in base + [(cat(gr['jaw']), jaw_poses[0][1])] + lid_closed + rpolys]
        ha = RV.surface_actor(epolys["head_outer"], (0.85, 0.80, 0.72))
        ha.GetProperty().SetOpacity(0.15)
        actors.append(ha)
        tiles.append((title, RV.render(actors, np.array(centre, float), d, (0, 0, 1), 0.55 * float(max(b[1] - b[0])))))
    return L.sheet(tiles, out_dir, "sweep", [
        f"M1 motion and space at head scale {s}: jaw sweep (light to dark = closed to {P.JAW_OPEN_DEG:.0f} deg open), "
        f"lids closed (pink) and open (dark red), reserved brow bays (purple) and cable channel (yellow)",
        f"sections show a {L.SLAB:.0f} mm slab | black = outer skin, grey = skin inner surface, red = skull inner surface"])


if __name__ == "__main__":
    sys.exit(main())

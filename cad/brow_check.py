"""
M2 eyebrow check: the brow mechanism (brow.py) in place, at rest and through
its whole travel, for both sides.

  moving   carrier (turns THETA_LOWER..THETA_RAISE about the pivot, plus
           OVERTRAVEL_DEG either way), servo horn (turns the matching crank
           angle about the servo shaft), pushrod (between the two balls)
  against  the EyeMech (every part at rest, plus the swept eyes and lids from
           pose_sweep), the brackets and servos, the other brow
  skin     the pad faces' push / pull against the skin over the travel
           (limits BROW_PUSH_MAX / BROW_PULL_MAX), and every fixed brow part
           inside the skull's inner surface (pads: inside the skin's inner surface)
  drive    servo angle range and the worst pushrod transmission angle
  stops    the two hard-stop set screws: no contact with the horn inside the
           travel, contact within OVERTRAVEL_DEG past each end
  rig      the bench rig (brow_rig.py, left brow): every moving part clear of it

Designed contacts (hub on its shoulder screw, horn on its spline, pushrod in its
ball links, servo tabs on the bracket plate) are allowed to overlap as much as
they do at rest, but not more.

Run:  python cad/brow_check.py      (after modules.py and brow.py)
  -> <out>/brow/brow.md, brow.png (+ tiles)
Final line: BROW OK, or BROW: n issue(s), each listed as a WARN line.
"""
import math
import os
import sys
import warnings

import numpy as np
import trimesh
from scipy.spatial import cKDTree

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import cadkit as K  # noqa: E402
import browgeom as B  # noqa: E402
import geom as G  # noqa: E402
import head as H  # noqa: E402
import layout_check as L  # noqa: E402
import pose_sweep as PS  # noqa: E402
import reserve as R  # noqa: E402

warnings.filterwarnings("ignore", category=RuntimeWarning)
sys.stdout.reconfigure(encoding="utf-8")
P = K.params()
S = P.HEAD_SCALE
NOISE = 1.0
OVERTRAVEL_DEG = 3.0
STEPS = 9
SEED = 11
DESIGNED = {frozenset(p) for p in (("carrier", "shoulder_screw"), ("horn", "servo"), ("pushrod", "carrier"),
                                   ("pushrod", "horn"), ("shoulder_screw", "bracket"), ("servo", "bracket"))}
COLOURS = {"carrier": (0.85, 0.35, 0.40), "bracket": (0.62, 0.62, 0.66), "servo": (0.15, 0.15, 0.15),
           "horn": (0.95, 0.95, 0.95), "pushrod": (0.95, 0.75, 0.10), "shoulder_screw": (0.80, 0.70, 0.20),
           "stop_screws": (0.30, 0.30, 0.30)}


def samples(m, n=None):
    n = n or int(np.clip(m.area / 3.0, 200, 6000))
    return trimesh.sample.sample_surface(m, n, seed=SEED)[0]


def kind(name):
    return name.rsplit("_", 1)[0].replace("brow_", "")


def load():
    stl, ref = K.stl_dir(), os.path.join(G.ref_dir(), "brow")
    out = {}
    for side in ("L", "R"):
        for k in ("carrier", "bracket"):
            out[f"{k}_{side}"] = trimesh.load(os.path.join(stl, f"brow_{k}_{side}.stl"), force="mesh")
        for k in ("servo", "horn", "pushrod", "shoulder_screw", "stop_screws"):
            out[f"{k}_{side}"] = trimesh.load(os.path.join(ref, f"{k}_{side}.stl"), force="mesh")
    rig = os.path.join(stl, "brow_rig.stl")
    out["rig"] = trimesh.load(rig, force="mesh") if os.path.exists(rig) else None
    return out


def mirror_tf(tf, side):
    if side == "L":
        return tf
    m = np.diag([-1.0, 1.0, 1.0, 1.0])
    return m @ tf @ m


def poses():
    lo = B.THETA_LOWER - math.radians(OVERTRAVEL_DEG)
    hi = B.THETA_RAISE + math.radians(OVERTRAVEL_DEG)
    return np.linspace(lo, hi, STEPS)


def drive_tfs(theta):
    """{part kind: 4x4 head transform} for the left side at carrier angle theta."""
    psi = B.crank_angle(theta)
    shaft = B.to_head((B.HORN_X, *B.SERVO_AXIS))
    return {"carrier": B.carrier_tf(theta),
            "horn": trimesh.transformations.rotation_matrix(psi, B.AXIS, shaft)}, psi


def pushrod_mesh(theta, psi, side):
    a = B.to_head((B.LINK_X, *B.rocker_ball(theta)))
    b = B.to_head((B.LINK_X, *B.crank_ball(psi)))
    d = (b - a) / np.linalg.norm(b - a)
    ext = P.BALL_LINK_D / 2
    m = trimesh.creation.cylinder(P.BALL_LINK_D / 2, segment=[a - ext * d, b + ext * d], sections=24)
    if side == "R":
        m.apply_transform(np.diag([-1.0, 1.0, 1.0, 1.0]))
        m.invert()
    return m


def overlap(a, b):
    try:
        return (R.to_mf(a) ^ R.to_mf(b)).volume()
    except Exception:                                  # noqa: BLE001
        return 0.0


def gap(pa, mb, treeb):
    d, _ = treeb.query(pa)
    cand = pa[np.argsort(d)[:30]]
    return float(trimesh.proximity.closest_point(mb, cand)[1].min())


# ---------------------------------------------------------------------------
def main():
    brow = load()
    base_scale, parts = L.load_parts()
    L.place(parts, base_scale, S)
    gr = PS.groups(parts)
    eye_static = [p for p in parts if p["module"] == "eyemech" and p["group"] == "frame"]
    eye_mesh = trimesh.util.concatenate([p["m"] for p in eye_static])
    eye_tree = cKDTree(np.vstack([p["p"] for p in eye_static]))
    # swept lids and eyes (pose_sweep ranges) as point clouds
    sweep_pts = []
    for which, top in (("lids_top", P.LID_TOP_OPEN_DEG), ("lids_bottom", P.LID_BOTTOM_OPEN_DEG)):
        for a in np.arange(0.0, top + 1e-6, 5.0):
            sweep_pts.append(PS.apply(np.vstack([p["p"] for p in gr[which]]), PS.lid_tf(which, a)))
    for pd in (-P.EYE_PAN_DEG, 0.0, P.EYE_PAN_DEG):
        for td in (-P.EYE_TILT_DEG, 0.0, P.EYE_TILT_DEG):
            tfs = PS.eye_tfs(pd, td)
            for p in gr["eyes"]:
                sx = 1 if p["m"].bounds.mean(axis=0)[0] > 0 else -1
                sweep_pts.append(PS.apply(p["p"], tfs[sx]))
    sweep_pts = np.vstack(sweep_pts)
    sweep_tree = cKDTree(sweep_pts)

    issues, md = [], ["# M2 eyebrow mechanism check", "",
                      f"Head scale {S}. Carrier travel {math.degrees(B.THETA_LOWER):.1f}..{math.degrees(B.THETA_RAISE):+.1f} deg "
                      f"(+-{OVERTRAVEL_DEG:.0f} overtravel checked), mid-brow -{P.BROW_LOWER}/+{P.BROW_RAISE} mm. "
                      "Gaps in mm, overlaps in mm3.", ""]

    # ---- rest: fixed parts against the EyeMech, the skull and each other -----
    fixed = ["bracket", "servo"]
    md += ["## At rest", "", "| part | closest EyeMech part | inside skull | notes |", "|---|---|---|---|"]
    for side in ("L", "R"):
        for k in fixed + ["carrier"]:
            m = brow[f"{k}_{side}"]
            pts = samples(m)
            d, j = eye_tree.query(pts)
            ov = overlap(m, eye_mesh) if m.is_watertight else 0.0
            near = float(trimesh.proximity.closest_point(eye_mesh, pts[np.argsort(d)[:40]])[1].min())
            inset = P.SKIN_T if k == "carrier" else P.SKIN_T + P.SKULL_WALL
            inside = float(G.envelope_margin(pts, S, inset).min())
            note = []
            if ov > NOISE:
                issues.append(f"{k}_{side} overlaps the EyeMech at rest ({ov:.0f} mm3)")
                note.append(f"overlap {ov:.0f}")
            elif near < P.MOTION_CLEAR_MIN:
                issues.append(f"{k}_{side} only {near:.1f} from the EyeMech at rest")
            if inside < 0:
                issues.append(f"{k}_{side} {-inside:.1f} outside the {'skin' if k == 'carrier' else 'skull'}'s inner surface")
            md.append(f"| {k}_{side} | {near:.1f} | {inside:+.1f} | {', '.join(note)} |")

    # ---- motion ------------------------------------------------------------
    md += ["", "## Through the travel", "",
           "| carrier deg | servo deg | transmission deg | carrier gap to EyeMech | to lid/eye sweep | to own bracket | to own servo | horn / pushrod gap | pad push / pull |",
           "|---|---|---|---|---|---|---|---|---|"]
    rest_ov = {}
    worst = dict(eye=np.inf, sweep=np.inf, bracket=np.inf, servo=np.inf, drive=np.inf, push=0.0, pull=0.0, trans=90.0,
                 rig=np.inf)
    stop_rows = {}
    rig = brow["rig"]
    rig_tree = cKDTree(samples(rig, 20000)) if rig is not None else None
    pad_pts0 = np.vstack([B.surface_point(px + dx, B.ZB + dz) for px in P.BROW_PADS_X
                          for dx in np.linspace(-P.BROW_PAD / 2, P.BROW_PAD / 2, 5)
                          for dz in np.linspace(-P.BROW_PAD / 2, P.BROW_PAD / 2, 5)])
    for i, theta in enumerate(poses()):
        tfl, psi = drive_tfs(theta)
        row = {}
        for side in ("L", "R"):
            moved = {}
            for k in ("carrier", "horn"):
                m = brow[f"{k}_{side}"].copy()
                m.apply_transform(mirror_tf(tfl[k], side))
                moved[k] = m
            moved["pushrod"] = pushrod_mesh(theta, psi, side)
            cpts = samples(moved["carrier"])
            g_eye = gap(cpts, eye_mesh, eye_tree)
            g_sweep = float(sweep_tree.query(cpts)[0].min())
            fixed_parts = {k: brow[f"{k}_{side}"] for k in ("bracket", "servo", "shoulder_screw")}
            # the hub's end face runs 0.4 from the cheek by design (thrust face): leave the hub out
            loc = B.to_local(cpts if side == "L" else B.mirror(cpts))
            off_hub = np.hypot(loc[:, 1], loc[:, 2]) > P.BROW_HUB_D / 2 + 0.3
            g_br = gap(cpts[off_hub], fixed_parts["bracket"], cKDTree(samples(fixed_parts["bracket"])))
            g_sv = gap(cpts, fixed_parts["servo"], cKDTree(samples(fixed_parts["servo"])))
            # drive parts against everything they must not touch
            g_drive = np.inf
            for dk in ("horn", "pushrod"):
                dpts = samples(moved[dk], 800)
                for tk, tm in (("carrier", moved["carrier"]), ("bracket", fixed_parts["bracket"]),
                               ("servo", fixed_parts["servo"]), ("eyemech", eye_mesh)):
                    if frozenset((dk, tk)) in DESIGNED:
                        key = (side, dk, tk)
                        v = overlap(moved[dk], tm)
                        if i == 0 or key not in rest_ov:
                            rest_ov[key] = v
                        if v > rest_ov[key] + NOISE + 2.0:
                            issues.append(f"{dk}_{side} digs into {tk} at {math.degrees(theta):+.1f} deg "
                                          f"({v - rest_ov[key]:.0f} mm3 more than designed)")
                        continue
                    g_drive = min(g_drive, gap(dpts, tm, cKDTree(samples(tm, 3000))))
            # hard stops: the horn must not touch them inside the travel, and must reach them just past it
            stops = brow[f"stop_screws_{side}"]
            g_stop = gap(samples(moved["horn"], 800), stops, cKDTree(samples(stops, 2000)))
            touching = overlap(moved["horn"], stops) > 0.05 or g_stop < 0.05
            stop_rows.setdefault(side, []).append((theta, touching, g_stop))
            # the bench rig (left brow): every moving part clear of it
            if side == "L" and rig is not None:
                for mk in ("carrier", "horn", "pushrod"):
                    g = gap(samples(moved[mk], 1500), rig, rig_tree)
                    worst["rig"] = min(worst["rig"], g)
                    row["rig"] = min(row.get("rig", np.inf), g)
            # carrier overlaps with designed-contact-free fixed parts
            for tk in ("bracket", "servo"):
                if overlap(moved["carrier"], fixed_parts[tk]) > NOISE:
                    issues.append(f"carrier_{side} hits its {tk} at {math.degrees(theta):+.1f} deg")
            if overlap(moved["carrier"], eye_mesh) > NOISE:
                issues.append(f"carrier_{side} hits the EyeMech at {math.degrees(theta):+.1f} deg")
            for k, v in (("eye", g_eye), ("sweep", g_sweep), ("bracket", g_br), ("servo", g_sv), ("drive", g_drive)):
                worst[k] = min(worst[k], v)
                row[k] = min(row.get(k, np.inf), v)
        # pad tracking (left; the right is its mirror image)
        pads = PS.apply(pad_pts0, tfl["carrier"])
        gch = (pads[:, 1] - B.carrier_y(pads[:, 0], pads[:, 2])) * B.normals(pads[:, 0], pads[:, 2])[:, 1]
        in_travel = B.THETA_LOWER - 1e-9 <= theta <= B.THETA_RAISE + 1e-9
        if in_travel:
            worst["push"] = max(worst["push"], float(gch.max()))
            worst["pull"] = max(worst["pull"], float(-gch.min()))
            worst["trans"] = min(worst["trans"], B.transmission_angle(theta))
        md.append(f"| {math.degrees(theta):+.1f}{'' if in_travel else ' (over)'} | {math.degrees(psi):+.1f} | "
                  f"{B.transmission_angle(theta):.0f} | {row['eye']:.1f} | {row['sweep']:.1f} | {row['bracket']:.1f} | "
                  f"{row['servo']:.1f} | {row['drive']:.1f} | {gch.max():+.2f} / {-gch.min():.2f} |")
        print(f"carrier {math.degrees(theta):+6.1f}: eye {row['eye']:.1f}, sweep {row['sweep']:.1f}, bracket "
              f"{row['bracket']:.1f}, servo {row['servo']:.1f}, drive {row['drive']:.1f}")

    for k, label in (("eye", "the EyeMech"), ("sweep", "the swept lids/eyes"), ("bracket", "its bracket"),
                     ("servo", "its servo")):
        if worst[k] < P.MOTION_CLEAR_MIN:
            issues.append(f"carrier comes within {worst[k]:.1f} of {label} over the travel")
    if worst["drive"] < 0.5:
        issues.append(f"horn or pushrod comes within {worst['drive']:.1f} of a part it must not touch")
    if worst["push"] > P.BROW_PUSH_MAX:
        issues.append(f"pads push {worst['push']:.2f} toward the skin (limit {P.BROW_PUSH_MAX})")
    if worst["pull"] > P.BROW_PULL_MAX:
        issues.append(f"pads pull {worst['pull']:.2f} away from the skin (limit {P.BROW_PULL_MAX})")
    if worst["trans"] < 45:
        issues.append(f"pushrod transmission angle drops to {worst['trans']:.0f} deg")
    stop_txt = []
    for side, rows in stop_rows.items():
        for theta, touching, g in rows:
            inside = B.THETA_LOWER - 1e-9 <= theta <= B.THETA_RAISE + 1e-9
            if inside and touching:
                issues.append(f"a hard stop touches the horn ({side}) inside the travel, at {math.degrees(theta):+.1f} deg")
        for end, theta, touching, g in (("lower", *rows[0]), ("raise", *rows[-1])):
            if not touching:
                issues.append(f"the {end} stop ({side}) does not engage within {OVERTRAVEL_DEG:.0f} deg past the travel "
                              f"(horn still {g:.1f} away)")
            elif side == "L":
                stop_txt.append(f"the {end} stop engages within {OVERTRAVEL_DEG:.0f} deg past the travel")
    inside_gap = min(g for rows in stop_rows.values() for th, t, g in rows
                     if B.THETA_LOWER - 1e-9 <= th <= B.THETA_RAISE + 1e-9)
    md += ["", f"Hard stops (set {P.BROW_STOP_MARGIN} past each end): the horn stays >= {inside_gap:.2f} from them "
               f"inside the travel; " + ("; ".join(stop_txt) or "see issues") + "."]
    if rig is not None:
        if worst["rig"] < P.MOTION_CLEAR_MIN:
            issues.append(f"a moving part comes within {worst['rig']:.1f} of the bench rig")
        ov = overlap(brow["bracket_L"], rig)
        if ov > NOISE:
            issues.append(f"the left bracket overlaps the bench rig ({ov:.0f} mm3)")
        md += [f"Bench rig: the moving parts stay >= {worst['rig']:.1f} from it over the travel; the bracket "
               f"overlaps it by {ov:.1f} mm3 (its flange sits on the rig's ceiling)."]
    psi_lo, psi_hi = math.degrees(B.crank_angle(B.THETA_LOWER)), math.degrees(B.crank_angle(B.THETA_RAISE))
    md += ["", f"Servo turns {psi_lo:+.1f}..{psi_hi:+.1f} deg for the full brow travel (2:1 four-bar); worst "
               f"transmission angle {worst['trans']:.0f} deg (90 is ideal). Pads move {worst['push']:.2f} toward / "
               f"{worst['pull']:.2f} away from the skin.", ""]

    # left/right brows apart
    lr = gap(samples(brow["carrier_L"]), brow["carrier_R"], cKDTree(samples(brow["carrier_R"])))
    md.append(f"Left and right carriers are {lr:.1f} apart at rest.")
    out_dir = os.path.join(K.check_out(), "brow")
    try:
        img = render(brow, parts, out_dir)
        md += ["", f"Renders: {os.path.basename(img)} (and brow_1..6.png)"]
        print("wrote", img)
    except Exception as e:                            # noqa: BLE001
        print(f"WARN  render failed: {e}")
        issues.append("render failed")
    md += ["", "## Issues", ""] + ([f"- {i}" for i in issues] or ["none"])
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, "brow.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(md) + "\n")
    print()
    for i in issues:
        print("WARN ", i)
    print("\nBROW OK" if not issues else f"\nBROW: {len(issues)} issue(s)")
    return 0


# ---------------------------------------------------------------------------
def render(brow, parts, out_dir):
    import render_views as RV
    envs = H.envelopes(S)
    epolys = {k: L.poly(m) for k, m in envs.items()}
    eye = L.poly(trimesh.util.concatenate([p["m"] for p in parts if p["module"] == "eyemech"]))
    focus = np.array([25.0, -5.0, B.EZ + 35.0])
    ghost = {B.THETA_LOWER: (0.55, 0.65, 0.95), 0.0: COLOURS["carrier"], B.THETA_RAISE: (0.55, 0.15, 0.20)}

    def items_at(theta, sides=("L", "R"), all_poses=False):
        out = [(eye, (0.35, 0.55, 0.85))]
        for side in sides:
            for k in ("bracket", "servo", "shoulder_screw", "stop_screws"):
                out.append((L.poly(brow[f"{k}_{side}"]), COLOURS[k]))
            thetas = ghost if all_poses else {theta: COLOURS["carrier"]}
            for th, rgb in thetas.items():
                tfl, psi = drive_tfs(th)
                c = brow[f"carrier_{side}"].copy()
                c.apply_transform(mirror_tf(tfl["carrier"], side))
                h = brow[f"horn_{side}"].copy()
                h.apply_transform(mirror_tf(tfl["horn"], side))
                out += [(L.poly(c), rgb), (L.poly(h), COLOURS["horn"]),
                        (L.poly(pushrod_mesh(th, psi, side)), COLOURS["pushrod"])]
        return out

    def section(title, o, n, up, items, centre, scale=52.0):
        acts = []
        for pp, rgb in items:
            acts.append(RV.surface_actor(L.clip(pp, o, n, 8.0), rgb))
            acts.append(RV.line_actor(L.cut(pp, o, n), (0, 0, 0), 2))
        for k, ep in epolys.items():
            rgb, w = L.LINES[k]
            acts.append(RV.line_actor(L.cut(ep, o, n), rgb, w))
        c = np.array(centre, float)
        ax = int(np.argmax(np.abs(n)))
        c[ax] = o[ax]
        return (title, RV.render(acts, c, n, up, scale))

    every = items_at(0.0, sides=("L",), all_poses=True)
    tiles = [section(f"left brow lowered / rest / raised, section x = {B.XM:.0f} (mid-brow)", (B.XM, 0, 0), (1, 0, 0),
                     (0, 0, 1), every, focus),
             section(f"section x = {B.PIVOT[0]:.0f} (pivot, hub, lever)", (B.PIVOT[0], 0, 0), (1, 0, 0), (0, 0, 1),
                     every, focus),
             section("top section at the brow line", (0, 0, B.ZB), (0, 0, 1), (0, 1, 0),
                     items_at(0.0), np.array([0.0, -10.0, B.ZB]), 70.0)]
    for title, d, th in (("3/4 from the front left, at rest", (0.8, 1.0, 0.45), 0.0),
                         ("3/4, brows raised", (0.8, 1.0, 0.45), B.THETA_RAISE),
                         ("from behind, the drive", (0.5, -1.0, 0.6), 0.0)):
        acts = [RV.surface_actor(pp, rgb) for pp, rgb in items_at(th)]
        tiles.append((title, RV.render(acts, np.array([0.0, -5.0, B.EZ + 35.0]), d, (0, 0, 1), 70.0)))
    if brow["rig"] is not None:                                     # the bench rig with the left brow
        rig_item = (L.poly(brow["rig"]), (0.80, 0.78, 0.70))
        left = [it for it in items_at(0.0, sides=("L",)) if it[1] != (0.35, 0.55, 0.85)]   # no EyeMech
        tiles.append(section(f"bench rig, section x = {B.XM:.0f}", (B.XM, 0, 0), (1, 0, 0), (0, 0, 1),
                             [rig_item] + left, focus + np.array([0, 0, 10.0]), 62.0))
        acts = [RV.surface_actor(pp, rgb) for pp, rgb in [rig_item] + left]
        tiles.append(("bench rig, 3/4 from the front (outer side open)",
                      RV.render(acts, np.array([38.0, -10.0, B.EZ + 45.0]), (0.7, 1.0, 0.35), (0, 0, 1), 68.0)))
    return L.sheet(tiles, out_dir, "brow", [
        f"M2 eyebrow mechanism v1 at head scale {S}: red carrier (blue = lowered, dark red = raised), grey bracket, "
        "black MG90S, yellow pushrod, white horn, blue EyeMech",
        f"sections show an 8 mm slab | black = outer skin, grey = skin inner surface, red = skull inner surface"])


if __name__ == "__main__":
    sys.exit(main())

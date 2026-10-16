"""
M3 skull check: the skull pieces (skull.py) against everything inside them.

  at rest   every Cogley module part and every brow part against every skull
            piece: overlap (manifold booleans) and closest gap. The brow
            brackets' flanges sit on their mount plates by design (contact,
            no overlap).
  moving    the swept jaw (pose_sweep's ranges), lids, eyes and brow carriers
            (brow_check's travel + overtravel) as point clouds: no point inside
            a skull piece, and the closest gap.

Run:  python cad/skull_check.py      (after the builders)
  -> <out>/skull/skull.md
Final line: SKULL OK, or SKULL: n issue(s), each listed as a WARN line.
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
import brow_check as BC  # noqa: E402
import browgeom as B  # noqa: E402
import layout_check as L  # noqa: E402
import pose_sweep as PS  # noqa: E402
import reserve as R  # noqa: E402

warnings.filterwarnings("ignore", category=RuntimeWarning)
sys.stdout.reconfigure(encoding="utf-8")
P = K.params()
S = P.HEAD_SCALE
NOISE = 1.0
PIECES = ("skull_front_upper", "skull_front_lower", "skull_back_upper", "skull_back_lower", "skull_shelf")
STATIC_MIN = 0.4          # mm: fixed parts against the skull (a print fit class)


def motion_clouds(gr, brow):
    """{name: points} of everything that moves: the jaw (0..JAW_OPEN_DEG), the lids and eyes
    (pose_sweep's ranges) and both brow carriers (brow_check's travel + overtravel)."""
    clouds = {}
    pts = []
    for a in np.arange(0.0, P.JAW_OPEN_DEG + 1e-6, P.SWEEP_STEP_DEG):
        pts.append(PS.apply(np.vstack([p["p"] for p in gr["jaw"]]), PS.jaw_tf(a)))
    clouds["jaw 0..%.0f deg" % P.JAW_OPEN_DEG] = np.vstack(pts)
    pts = []
    for which, top in (("lids_top", P.LID_TOP_OPEN_DEG), ("lids_bottom", P.LID_BOTTOM_OPEN_DEG)):
        for a in np.arange(0.0, top + 1e-6, 5.0):
            pts.append(PS.apply(np.vstack([p["p"] for p in gr[which]]), PS.lid_tf(which, a)))
    clouds["lids"] = np.vstack(pts)
    pts = []
    for pd in (-P.EYE_PAN_DEG, 0.0, P.EYE_PAN_DEG):
        for td in (-P.EYE_TILT_DEG, 0.0, P.EYE_TILT_DEG):
            tfs = PS.eye_tfs(pd, td)
            for p in gr["eyes"]:
                sx = 1 if p["m"].bounds.mean(axis=0)[0] > 0 else -1
                pts.append(PS.apply(p["p"], tfs[sx]))
    clouds["eyes"] = np.vstack(pts)
    pts = []
    for theta in BC.poses():
        tfl, psi = BC.drive_tfs(theta)
        for side in ("L", "R"):
            c = trimesh.sample.sample_surface(brow[f"carrier_{side}"], 4000, seed=6)[0]
            pts.append(PS.apply(c, BC.mirror_tf(tfl["carrier"], side)))
    clouds["brow carriers (with overtravel)"] = np.vstack(pts)
    return clouds


def main():
    stl = K.stl_dir()
    skull = {n: trimesh.load(os.path.join(stl, n + ".stl"), force="mesh") for n in PIECES}
    trees = {n: cKDTree(trimesh.sample.sample_surface(m, 60000, seed=4)[0]) for n, m in skull.items()}
    base_scale, parts = L.load_parts()
    L.place(parts, base_scale, S)
    gr = PS.groups(parts)
    brow = BC.load()
    issues, md = [], ["# M3 skull check", "", f"Head scale {S}. Gaps in mm, overlaps in mm3.", "",
                      "## At rest", "", "| piece | closest module part | closest brow part | overlaps |", "|---|---|---|---|"]

    def closest(pts, name):
        d, _ = trees[name].query(pts)
        cand = pts[np.argsort(d)[:30]]
        return float(trimesh.proximity.closest_point(skull[name], cand)[1].min())

    static = [p for p in parts]                                   # every module part at rest
    brow_static = {k: v for k, v in brow.items() if v is not None and not k.startswith("rig")}
    for name, sm in skull.items():
        ov_list = []
        best_mod, best_brow = (np.inf, ""), (np.inf, "")
        lo, hi = sm.bounds
        for p in static:
            if L.gap(p["m"].bounds, (lo, hi)) > 3.0:
                continue
            g = closest(p["p"], name)
            if g < best_mod[0]:
                best_mod = (g, f"{p['module']} {p['label']}")
            if g < 0.05 and p["watertight"] and not p["shell"]:
                v = (R.to_mf(p["m"]) ^ R.to_mf(sm)).volume()
                if v > NOISE:
                    ov_list.append(f"{p['label']} {v:.0f}")
        for k, m in brow_static.items():
            if L.gap(m.bounds, (lo, hi)) > 3.0:
                continue
            pts = trimesh.sample.sample_surface(m, 3000, seed=5)[0]
            g = closest(pts, name)
            if k.startswith("bracket") and name == "skull_front_upper":
                v = (R.to_mf(m) ^ R.to_mf(sm)).volume() if m.is_watertight else 0.0
                if v > NOISE:
                    ov_list.append(f"{k} {v:.0f}")
                continue                                          # flange on its plate: contact by design
            if g < best_brow[0]:
                best_brow = (g, k)
        md.append(f"| {name} | {best_mod[0]:.1f} ({best_mod[1]}) | {best_brow[0]:.1f} ({best_brow[1]}) | "
                  f"{', '.join(ov_list) or 'none'} |")
        for o in ov_list:
            issues.append(f"{name} overlaps {o} mm3")
        if best_mod[0] < STATIC_MIN and not ov_list:
            issues.append(f"{name} only {best_mod[0]:.2f} from {best_mod[1]}")
        if best_brow[0] < STATIC_MIN:
            issues.append(f"{name} only {best_brow[0]:.2f} from {best_brow[1]}")
        print(f"{name}: module {best_mod[0]:.1f} ({best_mod[1]}), brow {best_brow[0]:.1f} ({best_brow[1]}), "
              f"overlaps {', '.join(ov_list) or 'none'}")

    # ---- moving -------------------------------------------------------------
    clouds = motion_clouds(gr, brow)

    md += ["", "## Moving parts", "", "| sweep | closest skull piece | gap | points inside a piece |", "|---|---|---|---|"]
    for what, cl in clouds.items():
        best, inside = (np.inf, ""), 0
        for name, sm in skull.items():
            lo, hi = sm.bounds
            near = np.all((cl >= lo - 3) & (cl <= hi + 3), axis=1)
            if not near.any():
                continue
            sub = cl[near]
            d, _ = trees[name].query(sub)
            inside += int(sm.contains(sub[d < 3.0]).sum()) if (d < 3.0).any() else 0
            g = float(d.min())
            if g < best[0]:
                best = (g, name)
        md.append(f"| {what} | {best[1]} | {best[0]:.1f} | {inside} |")
        print(f"{what}: closest {best[1]} {best[0]:.1f}, inside {inside}")
        if inside:
            issues.append(f"the {what} sweep enters the skull ({inside} points, nearest {best[1]})")
        elif best[0] < P.MOTION_CLEAR_MIN:
            issues.append(f"the {what} sweep comes within {best[0]:.1f} of {best[1]}")

    out_dir = os.path.join(K.check_out(), "skull")
    os.makedirs(out_dir, exist_ok=True)
    try:
        img = render(skull, parts, brow, out_dir)
        md += ["", f"Renders: {os.path.basename(img)} (and skull_1..6.png)"]
        print("wrote", img)
    except Exception as e:                            # noqa: BLE001
        print(f"WARN  render failed: {e}")
        issues.append("render failed")
    md += ["", "## Issues", ""] + ([f"- {i}" for i in issues] or ["none"])
    with open(os.path.join(out_dir, "skull.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(md) + "\n")
    print()
    for i in issues:
        print("WARN ", i)
    print("\nSKULL OK" if not issues else f"\nSKULL: {len(issues)} issue(s)")
    return 0


BONE = {"skull_front_upper": (0.93, 0.89, 0.78), "skull_front_lower": (0.88, 0.84, 0.72),
        "skull_back_upper": (0.80, 0.76, 0.66), "skull_back_lower": (0.75, 0.71, 0.62),
        "skull_shelf": (0.55, 0.75, 0.75)}
EXPLODE = {"skull_front_upper": (0, 40, 40), "skull_front_lower": (0, 40, -40), "skull_back_upper": (0, -40, 40),
           "skull_back_lower": (0, -40, -40), "skull_shelf": (0, 0, 0)}


def render(skull, parts, brow, out_dir):
    import head as H
    import render_views as RV
    groups = {}
    for p in parts:
        groups.setdefault((p["module"], p["group"]), []).append(p["m"])
    mods = [(L.poly(trimesh.util.concatenate(v)), L.COLOURS[k]) for k, v in groups.items()]
    brows = [(L.poly(m), BC.COLOURS["carrier" if k.startswith("carrier") else "bracket"])
             for k, m in brow.items() if m is not None and k.split("_")[0] in ("carrier", "bracket")]
    skp = [(L.poly(m), BONE[n]) for n, m in skull.items()]
    outer = H.envelope(S, 0.0)
    ep = L.poly(outer)
    b = outer.bounds
    c = (b[0] + b[1]) / 2
    sc = 0.55 * float(max(b[1] - b[0]))
    tiles = []
    for title, d in (("front", (0, 1, 0)), ("3/4 from the front left", (0.8, 1.0, 0.4))):
        tiles.append((title, RV.render([RV.surface_actor(pp, rgb) for pp, rgb in skp + mods + brows],
                                       c, d, (0, 0, 1), sc)))
    for title, o, n in (("side section x = 0", (0, 0, 0), (1, 0, 0)),
                        (f"side section x = {P.EYE_SPACING / 2:.1f} (left eye)", (P.EYE_SPACING / 2, 0, 0), (1, 0, 0)),
                        ("front section y = 0 (eye centres)", (0, 0, 0), (0, 1, 0))):
        acts = []
        for pp, rgb in skp + mods + brows:
            acts.append(RV.surface_actor(L.clip(pp, o, n, 10.0), rgb))
            acts.append(RV.line_actor(L.cut(pp, o, n), (0, 0, 0), 2))
        rgb, w = L.LINES["head_outer"]
        acts.append(RV.line_actor(L.cut(ep, o, n), rgb, w))
        cc = c.copy()
        ax = int(np.argmax(np.abs(n)))
        cc[ax] = o[ax]
        tiles.append((title, RV.render(acts, cc, n, (0, 0, 1), sc)))
    acts = []
    for name, m in skull.items():
        mm = m.copy()
        mm.apply_translation(EXPLODE[name])
        acts.append(RV.surface_actor(L.poly(mm), BONE[name]))
    tiles.append(("exploded: the printed skull pieces", RV.render(acts, c, (1.0, 0.6, 0.4), (0, 0, 1), sc * 1.25)))
    return L.sheet(tiles, out_dir, "skull", [
        f"M3 skull at head scale {S}: bone = printed skull pieces (shelf teal), with the Cogley modules and the brows inside",
        "sections show a 10 mm slab | black line = outer skin"])


if __name__ == "__main__":
    sys.exit(main())

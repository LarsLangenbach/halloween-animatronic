"""
Sculpt base check (M5, D17): the base the clay face is sculpted on must leave room for
Cogley's head inside the skin.

  his head inside   no part of his head (at rest; the eyes excepted, they show in their
                    sockets by design) comes through the base's outer surface (the wrap
                    sculpt_base.py writes, before the sockets, grooves and inside holes)
  skin              how close his parts come to that surface (SCULPT_MIN_SKIN, less the
                    grooves' depth)
  eyes              each eye sphere's centre on his eyeball's centre (`Component74`)
  bed               each piece fits the printer's bed in its print pose

Run:  python cad/sculpt_check.py      (after cogley_head.py and sculpt_base.py)
  -> <out>/sculpt/sculpt.md, sculpt.png
Final line: SCULPT OK, or SCULPT: n issue(s), each listed as a WARN line.
"""
import os
import sys

import manifold3d as mf
import numpy as np
import trimesh
from scipy.spatial import cKDTree

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import cadkit as K  # noqa: E402
import cogley_head as C  # noqa: E402
import geom as G  # noqa: E402
import layout_check as L  # noqa: E402
import reserve as R  # noqa: E402

sys.stdout.reconfigure(encoding="utf-8")
P = K.params()
S = P.HEAD_SCALE
PIECES = ("sculpt_upper", "sculpt_lower", "sculpt_plate")
BED = 256.0
SKIN_MIN = P.SCULPT_MIN_SKIN - P.SCULPT_GROOVE / 2 - 0.3     # grooves cut in; 0.3 for the wrap's voxels


def main():
    stl = K.stl_dir()
    base = {n: trimesh.load(os.path.join(stl, n + ".stl"), force="mesh") for n in PIECES}
    head = trimesh.util.concatenate([base["sculpt_upper"], base["sculpt_lower"]])
    issues, md = [], ["# Sculpt base check", ""]
    # against the base's outer surface (sculpt_base.py's wrap, before the sockets, grooves and
    # holes): the dowel and insert holes are inside, and the sockets stop at his parts by design
    wrap = trimesh.load(os.path.join(G.ref_dir(), "sculpt", "wrap.stl"), force="mesh")
    body = R.to_mf(wrap)
    parts = C.load({"frame", "extras", "shell", "mouth", "brows", "hardware", "eyes"})

    # his head inside the base (the eyes show in their sockets by design)
    outside, open_parts = [], 0
    for n, k, g, m in parts:
        if g == "eyes":
            continue
        if not m.is_watertight:
            open_parts += 1
            continue
        v = (R.to_mf(m) - body).volume()
        if v > 1.0:
            outside.append((v, f"{n} {k}"))
    md.append(f"- his parts coming through the base: {len(outside)}"
              + ("" if not outside else " (" + ", ".join(f"{n} {v:.0f} mm3" for v, n in sorted(outside)[::-1][:6]) + ")")
              + f"; {open_parts} open meshes checked by distance only")
    for v, n in outside:
        issues.append(f"{n} comes {v:.0f} mm3 through the sculpt base")

    # skin: how close his parts (the eyes excepted) come to the base's surface
    tree = cKDTree(trimesh.sample.sample_surface(wrap, 400000, seed=2)[0])
    worst = (np.inf, "", None)
    for n, k, g, m in parts:
        if g == "eyes":
            continue
        pts = trimesh.sample.sample_surface(m, int(np.clip(m.area * 0.5, 200, 30000)), seed=3)[0]
        d, _ = tree.query(pts)
        j = int(np.argmin(d))
        if d[j] < worst[0]:
            worst = (float(d[j]), f"{n} {k}", pts[j])
    md.append(f"- thinnest skin over his parts (to the base's surface): {worst[0]:.2f} mm ({worst[1]} at "
              f"{np.round(worst[2], 0).tolist()}); want >= {SKIN_MIN:.1f}")
    if worst[0] < SKIN_MIN:
        issues.append(f"only {worst[0]:.2f} mm between {worst[1]} and the base's surface at {np.round(worst[2], 0).tolist()}")

    # eyes on his eyeballs
    ez = G.eye_z(S)
    for sx in (+1, -1):
        want = np.array([sx * P.EYE_SPACING / 2, 0.0, ez])
        balls = [m for n, k, g, m in parts if n == "Component74" and (m.bounds.mean(axis=0)[0] > 0) == (sx > 0)]
        lo, hi = balls[0].bounds
        c = np.array([(lo[0] + hi[0]) / 2, hi[1] - P.EYE_R, (lo[2] + hi[2]) / 2])
        err = float(np.linalg.norm(c - want))
        md.append(f"- eye {'left' if sx > 0 else 'right'}: sphere at {np.round(want, 1).tolist()}, "
                  f"his eyeball at {np.round(c, 1).tolist()} ({err:.2f} off)")
        if err > 0.5:
            issues.append(f"the {'left' if sx > 0 else 'right'} eye sphere is {err:.2f} off his eyeball")

    # bed
    for n, m in base.items():
        e = np.sort(m.extents)
        md.append(f"- {n}: {m.extents[0]:.1f} x {m.extents[1]:.1f} x {m.extents[2]:.1f} mm, {m.volume / 1000:.0f} cm3")
        if e[-1] > BED:
            issues.append(f"{n} is {e[-1]:.0f} mm long: over the {BED:.0f} mm bed")

    out_dir = os.path.join(K.check_out(), "sculpt")
    os.makedirs(out_dir, exist_ok=True)
    try:
        img = render(base, out_dir)
        md += ["", f"Renders: {os.path.basename(img)}"]
        print("wrote", img)
    except Exception as e:                            # noqa: BLE001
        print(f"WARN  render failed: {e}")
        issues.append("render failed")
    md += ["", "## Issues", ""] + ([f"- {i}" for i in issues] or ["none"])
    with open(os.path.join(out_dir, "sculpt.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(md) + "\n")
    print("\n".join(md[2:]))
    print()
    for i in issues:
        print("WARN ", i)
    print("\nSCULPT OK" if not issues else f"\nSCULPT: {len(issues)} issue(s)")
    return 0


COLOURS = {"sculpt_upper": (0.80, 0.62, 0.52), "sculpt_lower": (0.76, 0.58, 0.48), "sculpt_plate": (0.45, 0.45, 0.50)}


def render(base, out_dir):
    import render_views as RV
    polys = [(L.poly(m), COLOURS[n]) for n, m in base.items()]
    allm = trimesh.util.concatenate(list(base.values()))
    b = allm.bounds
    c = (b[0] + b[1]) / 2
    sc = 0.55 * float(max(b[1] - b[0]))
    tiles = []
    for title, d in (("front", (0, 1, 0)), ("3/4 from the front left", (0.8, 1.0, 0.25)),
                     ("left side", (1, 0, 0)), ("3/4 from the back right", (-0.8, -1.0, 0.3))):
        tiles.append((title, RV.render([RV.surface_actor(pp, rgb) for pp, rgb in polys], c, d, (0, 0, 1), sc)))
    ez = G.eye_z(S)
    eye_c = np.array([0.0, 0.0, ez])
    tiles.append(("eyes, eye line, brow lines, close", RV.render([RV.surface_actor(pp, rgb) for pp, rgb in polys],
                                                                 eye_c, (0.25, 1.0, 0.15), (0, 0, 1), sc * 0.45)))
    import sculpt_base as SB
    lm = SB.landmarks(C.load({"mouth", "brows"}))
    mouth_c = np.array([0.0, 0.0, (lm["nose"] + lm["chin"]) / 2])
    tiles.append(("nose, lip line, mouth corners, chin, close", RV.render([RV.surface_actor(pp, rgb) for pp, rgb in polys],
                                                                          mouth_c, (0.25, 1.0, -0.1), (0, 0, 1), sc * 0.45)))
    pm = base["sculpt_plate"]
    tiles.append(("base plate from above (keys, bolt and board holes)",
                  RV.render([RV.surface_actor(L.poly(pm), COLOURS["sculpt_plate"])], pm.bounds.mean(axis=0),
                            (0, -0.3, 1), (0, 1, 0), 0.6 * float(pm.extents.max()))))
    mm = {n: m.copy() for n, m in base.items()}
    mm["sculpt_upper"].apply_translation((0, 0, 60))
    mm["sculpt_plate"].apply_translation((0, 0, -50))
    tiles.append(("exploded: upper, lower, plate", RV.render([RV.surface_actor(L.poly(m), COLOURS[n])
                                                              for n, m in mm.items()], c, (1.0, 0.8, 0.3),
                                                             (0, 0, 1), sc * 1.25)))
    return L.sheet(tiles, out_dir, "sculpt", cols=4, header_lines=[
        "Sculpt base v2: a smooth wrap of Cogley's whole head, 3 mm out from every part (clay on it + 3 mm = the skin)",
        "eye sockets with the real eyes; grooves: midline, eye line, brow lines, nose bottom and width, lip line, "
        "mouth corners, chin, hairline, ears"])


if __name__ == "__main__":
    sys.exit(main())

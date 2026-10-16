"""
Sculpt base check (M5, early): the base the clay face is sculpted on must match the skull
the cast skin goes onto.

  skull inside   no point of any skull piece's outside stands proud of the base's surface
                 (more than the grooves' depth): a skin sculpted on the base fits the skull
  eyes           each eye sphere's centre on the EyeMech's eyeball centre at rest
  bed            each piece fits the printer's bed in its print pose

Run:  python cad/sculpt_check.py      (after skull.py and sculpt_base.py)
  -> <out>/sculpt/sculpt.md, sculpt.png
Final line: SCULPT OK, or SCULPT: n issue(s), each listed as a WARN line.
"""
import os
import sys

import numpy as np
import trimesh

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import cadkit as K  # noqa: E402
import geom as G  # noqa: E402
import layout_check as L  # noqa: E402
import pose_sweep as PS  # noqa: E402

sys.stdout.reconfigure(encoding="utf-8")
P = K.params()
S = P.HEAD_SCALE
PIECES = ("sculpt_upper", "sculpt_lower", "sculpt_plate")
SKULL = ("skull_front_upper", "skull_front_lower", "skull_back_upper", "skull_back_lower", "skull_access_panel")
BED = 256.0
TOL = P.SCULPT_GROOVE / 2 + 0.05     # the grooves cut this deep into the skull's outside


def main():
    stl = K.stl_dir()
    base = {n: trimesh.load(os.path.join(stl, n + ".stl"), force="mesh") for n in PIECES}
    head = trimesh.util.concatenate([base["sculpt_upper"], base["sculpt_lower"]])
    issues, md = [], ["# Sculpt base check", ""]

    # skull inside the base: whatever of each skull piece is outside the base (manifold
    # booleans), and how far its farthest point stands from the base's surface
    import reserve as R
    import manifold3d as mf
    body = mf.Manifold.batch_boolean([R.to_mf(base["sculpt_upper"]), R.to_mf(base["sculpt_lower"])], mf.OpType.Add)
    worst = (0.0, None, "")
    for n in SKULL:
        m = trimesh.load(os.path.join(stl, n + ".stl"), force="mesh")
        diff = R.to_mf(m) - body
        if diff.volume() < 1e-3:
            continue
        v = np.asarray(diff.to_mesh().vert_properties)[:, :3]
        if len(v) > 20000:
            v = v[np.random.default_rng(3).choice(len(v), 20000, replace=False)]
        d = trimesh.proximity.closest_point(head, v)[1]
        j = int(np.argmax(d))
        if d[j] > worst[0]:
            worst = (float(d[j]), v[j], n)
    md.append(f"- skull outside the base: at most {worst[0]:.2f} mm"
              + (f" ({worst[2]} at {np.round(worst[1], 1).tolist()})" if worst[1] is not None else ""))
    if worst[0] > TOL:
        issues.append(f"{worst[2]} stands {worst[0]:.2f} proud of the sculpt base at {np.round(worst[1], 1).tolist()}")

    # eyes on the EyeMech's eyeballs
    base_scale, parts = L.load_parts()
    L.place(parts, base_scale, S)
    gr = PS.groups(parts)
    ez = G.eye_z(S)
    for sx in (+1, -1):
        want = np.array([sx * P.EYE_SPACING / 2, 0.0, ez])
        balls = [p for p in gr["eyes"] if (p["m"].bounds.mean(axis=0)[0] > 0) == (sx > 0)]
        c = np.mean([p["m"].bounding_sphere.primitive.center for p in balls
                     if p["m"].extents.max() > 2 * P.EYE_R - 1.0], axis=0)
        err = float(np.linalg.norm(c - want))
        md.append(f"- eye {'left' if sx > 0 else 'right'}: sphere at {np.round(want, 1).tolist()}, "
                  f"EyeMech eyeball at {np.round(c, 1).tolist()} ({err:.2f} off)")
        if err > 0.5:
            issues.append(f"the {'left' if sx > 0 else 'right'} eye sphere is {err:.2f} off the EyeMech's eyeball")

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
    tiles.append(("eyes and brow windows, close", RV.render([RV.surface_actor(pp, rgb) for pp, rgb in polys],
                                                            eye_c, (0.25, 1.0, 0.15), (0, 0, 1), sc * 0.45)))
    mouth_c = np.array([0.0, 0.0, G.stomion(S)[2]])
    tiles.append(("mouth marks, close", RV.render([RV.surface_actor(pp, rgb) for pp, rgb in polys],
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
        f"Sculpt base at head scale {S}: the skull's outside as a solid head (clay on it = the skin)",
        "eye sockets with the lids' sphere; grooves: midline, brow windows, mouth opening, lip line"])


if __name__ == "__main__":
    sys.exit(main())

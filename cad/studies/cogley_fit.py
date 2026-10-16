"""
Study (D14): Cogley's Robot Head a2.0.33 inside our current head (the proxy face, the
skull's outside and inside), its eyes on ours. What fits, what pokes through, and where
his mouth sits against ours.

His robot outer shell (group `shell`) is left out: our skin-support shell replaces it.
Margins are to our envelopes, positive inside: the skull's inside (SKIN_T + SKULL_WALL in
from the face) for parts that must stay behind the wall, the skull's outside (SKIN_T in)
for parts that work through openings (eyes, brows, lips).

Run:  python cad/studies/cogley_fit.py   (after cogley_head.py, head.py, modules.py)
  -> <out>/studies/cogley_fit.md and cogley_fit.png
"""
import os
import sys

import numpy as np
import trimesh

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import cadkit as K  # noqa: E402
import cogley_head as C  # noqa: E402
import geom as G  # noqa: E402
import head as H  # noqa: E402
import layout_check as L  # noqa: E402

sys.stdout.reconfigure(encoding="utf-8")
P = K.params()
S = P.HEAD_SCALE
COLOURS = {"frame": (0.93, 0.93, 0.90), "extras": (0.75, 0.75, 0.72), "eyes": (0.35, 0.55, 0.85),
           "mouth": (0.45, 0.72, 0.40), "brows": (0.85, 0.35, 0.30), "hardware": (0.40, 0.40, 0.40),
           "ours_mouth": (0.95, 0.75, 0.20)}


def main():
    parts = C.load({"frame", "extras", "eyes", "mouth", "brows", "hardware"})
    md = ["# Cogley head a2.0.33 in our head (study, D14)", "",
          f"His eye centres on ours: (+-{P.EYE_SPACING / 2:.1f}, 0, {G.eye_z(S):.1f}). Margins in mm, "
          "positive = inside. Robot outer shell left out (our shell replaces it).", "",
          "| group | parts | worst vs skull inside | worst vs skull outside | worst part |", "|---|---|---|---|---|"]
    rng = np.random.default_rng(1)
    worst_rows = []
    for g in ("frame", "extras", "eyes", "mouth", "brows", "hardware"):
        rows = [r for r in parts if r[2] == g]
        w_in, w_out, wp = np.inf, np.inf, ""
        for name, k, _, m in rows:
            v = m.vertices if len(m.vertices) < 15000 else m.vertices[rng.choice(len(m.vertices), 15000, replace=False)]
            mi = G.envelope_margin(v, S, P.SKIN_T + P.SKULL_WALL)
            mo = mi + P.SKULL_WALL
            j = int(np.argmin(mi))
            if mi[j] < w_in:
                w_in, w_out, wp = float(mi[j]), float(mo[j]), f"{name} {k} at {np.round(v[j], 0).tolist()}"
            if mi[j] < 0:
                worst_rows.append((float(mi[j]), g, name, k, v[j]))
        md.append(f"| {g} | {len(rows)} | {w_in:.1f} | {w_out:.1f} | {wp} |")
    md += ["", "Parts standing outside the skull's inside (negative margins):", ""]
    for mi, g, name, k, q in sorted(worst_rows)[:30]:
        md.append(f"- {mi:6.1f}  {g:8s} {name} {k} at {np.round(q, 0).tolist()}")

    base_scale, ours = L.load_parts()
    L.place(ours, base_scale, S)
    ours_mouth = trimesh.util.concatenate([p["m"] for p in ours if p["module"] == "mouth"])
    his_mouth = trimesh.util.concatenate([m for n, k, g, m in parts if n == "TopBase"])
    our_top = [p["m"] for p in ours if p["module"] == "mouth" and p["label"] == "TopBase"][0]
    d = his_mouth.bounds[0] - our_top.bounds[0]
    md += ["", f"His mouth (TopBase) against ours: {np.round(d, 1).tolist()} mm (x, y, z). "
           f"His EyeMech base plate sits {his_eye_gap(parts):.1f} mm above his TopBase's top."]

    out_dir = os.path.join(K.check_out(), "studies")
    os.makedirs(out_dir, exist_ok=True)
    img = render(parts, ours_mouth, out_dir)
    md += ["", f"Renders: {os.path.basename(img)}"]
    with open(os.path.join(out_dir, "cogley_fit.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(md) + "\n")
    print("\n".join(md))
    print("wrote", img)
    return 0


def his_eye_gap(parts):
    plate = max((m for n, k, g, m in parts if n == "SnapEyemech v20"), key=lambda m: m.extents[0])
    top = [m for n, k, g, m in parts if n == "TopBase"][0]
    return float(plate.bounds[0][2] - top.bounds[1][2])


def render(parts, ours_mouth, out_dir):
    import render_views as RV
    polys = [(L.poly(m), COLOURS[g]) for n, k, g, m in parts]
    env = {k: L.poly(H.envelope(S, inset)) for k, inset in
           (("head_outer", 0.0), ("skin_inner", P.SKIN_T), ("skull_inner", P.SKIN_T + P.SKULL_WALL))}
    outer = H.envelope(S, 0.0)
    b = outer.bounds
    c = (b[0] + b[1]) / 2
    sc = 0.55 * float(max(b[1] - b[0]))
    tiles = []
    for title, dvec in (("front (his robot shell left out)", (0, 1, 0)), ("3/4 from the front left", (0.8, 1.0, 0.3))):
        tiles.append((title, RV.render([RV.surface_actor(pp, rgb) for pp, rgb in polys], c, dvec, (0, 0, 1), sc)))
    om = L.poly(ours_mouth)
    for title, o, n in (("side section x = 0 (orange: our mouth's place)", (0, 0, 0), (1, 0, 0)),
                        (f"side section x = {P.EYE_SPACING / 2:.1f} (left eye)", (P.EYE_SPACING / 2, 0, 0), (1, 0, 0)),
                        ("front section y = 0 (eye centres)", (0, 0, 0), (0, 1, 0)),
                        ("top section z = 255 (brows)", (0, 0, 255.0), (0, 0, 1))):
        acts = []
        for pp, rgb in polys:
            acts.append(RV.surface_actor(L.clip(pp, o, n, 10.0), rgb))
            acts.append(RV.line_actor(L.cut(pp, o, n), (0, 0, 0), 1))
        if "x = 0" in title:
            acts.append(RV.line_actor(L.cut(om, o, n), COLOURS["ours_mouth"], 3))
        for k, pe in env.items():
            rgb, w = L.LINES.get(k, ((0.6, 0.6, 0.6), 2))
            acts.append(RV.line_actor(L.cut(pe, o, n), rgb, w))
        cc = c.copy()
        ax = int(np.argmax(np.abs(n)))
        cc[ax] = o[ax]
        up = (0, 0, 1) if ax != 2 else (0, 1, 0)
        tiles.append((title, RV.render(acts, cc, n, up, sc)))
    return L.sheet(tiles, out_dir, "cogley_fit", cols=3, header_lines=[
        f"Cogley Robot Head a2.0.33 in our head at scale {S}, eyes on ours: white frame, grey extras, blue eyes, "
        "green mouth, red brows",
        "lines: black = our face, grey = the skull's outside (skin's inside), lighter = the skull's inside"])


if __name__ == "__main__":
    sys.exit(main())

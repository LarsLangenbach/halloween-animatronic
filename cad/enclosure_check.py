"""
Enclosure check (M8): the canister and the neck against the head, Cogley's parts, the moving
jaw, the clear sheet and what lives in the base.

  1. The head (sculpt wrap + face mask) clears the sheet's inside and the cap's underside.
  2. The clear sheet (output/ref/enclosure/sheet.stl) overlaps no printed part: the slits and the
     column's forks are right.
  3. The neck and its two clamp plates against Cogley's head at rest (D30): no overlap with any of
     his parts, each within 0.5 of the frame's nape ring (so the clamp grips), and room for a hex
     key over each clamp screw (his rear plate off).
  4. The jaw swept from 0 to JAW_OPEN_DEG + JAW_OVERTRAVEL_DEG against the neck: the gap at every
     step, the clean limit, the first touching pair.
  5. What lives in the base (bank, buck, boards, speaker, the webcam in the cap) fits: inside the
     bay, under the deck, overlapping no printed part and not each other.
  6. Every piece fits the bed (print_check does the same; here with the numbers).

Run:  python cad/enclosure_check.py   (after enclosure.py, cogley_head.py, sculpt_base.py, face_mask.py)
  -> <out>/enclosure/enclosure.md, enclosure.png
"""
import os
import sys

import manifold3d as mf
import numpy as np
import trimesh

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import cadkit as K  # noqa: E402
import cogley_head as C  # noqa: E402
import geom as G  # noqa: E402
import layout_check as L  # noqa: E402

sys.stdout.reconfigure(encoding="utf-8")
P = K.params()
S = P.HEAD_SCALE
AY = P.ENC_AXIS_Y
SEED = 7
JAW_PARTS = ("JawBase", "JawLink", "Part 33", "Part 22")
NAMES = ["enc_cap_F", "enc_cap_B", "enc_top_F", "enc_top_B", "enc_bottom_F", "enc_bottom_B", "enc_band_F", "enc_band_B",
         "enc_tray", "enc_pedestal", "enc_grille", "enc_hatch", "neck", "neck_clamp_L", "neck_clamp_R"]


def to_mf(mesh):
    return mf.Manifold(mf.Mesh(vert_properties=np.asarray(mesh.vertices, np.float32),
                               tri_verts=np.asarray(mesh.faces, np.uint32)))


def overlap_volume(a, b):
    try:
        return float((to_mf(a) ^ to_mf(b)).volume())
    except Exception:
        return float("nan")


def gap(a, b, n=600):
    """Minimum surface distance between two meshes from n seeded samples on each (0 if they overlap)."""
    rng = np.random.default_rng(SEED)
    pa, _ = trimesh.sample.sample_surface(a, n, seed=SEED)
    pb, _ = trimesh.sample.sample_surface(b, n, seed=SEED + 1)
    da = np.abs(trimesh.proximity.signed_distance(b, pa)) if len(pa) else np.array([np.inf])
    db = np.abs(trimesh.proximity.signed_distance(a, pb)) if len(pb) else np.array([np.inf])
    return float(min(da.min(), db.min()))


def rot_x(deg, point):
    t = np.radians(deg)
    R = np.array([[1, 0, 0], [0, np.cos(t), -np.sin(t)], [0, np.sin(t), np.cos(t)]])
    p = np.asarray(point)
    tf = np.eye(4)
    tf[:3, :3] = R
    tf[:3, 3] = p - R @ p
    return tf


def jaw_tf(angle):
    ya, za = G.jaw_axis(S)
    return rot_x(-angle, (0.0, ya, za))


def load_parts():
    d = K.stl_dir()
    out = {}
    for n in NAMES:
        p = os.path.join(d, n + ".stl")
        if os.path.exists(p):
            out[n] = trimesh.load(p, force="mesh")
    return out


def load_refs():
    d = os.path.join(G.ref_dir(), "enclosure")
    return {os.path.splitext(f)[0]: trimesh.load(os.path.join(d, f), force="mesh") for f in sorted(os.listdir(d))
            if f.endswith(".stl")}


def head_meshes():
    d = K.stl_dir()
    return [trimesh.load(os.path.join(d, f), force="mesh") for f in ("sculpt_upper.stl", "sculpt_lower.stl", "face_mask.stl")]


def main():
    parts = load_parts()
    refs = load_refs()
    heads = head_meshes()
    missing = [n for n in NAMES if n not in parts]
    issues, notes = [], []
    if missing:
        issues.append(f"missing print files: {', '.join(missing)}")
    md = ["# Enclosure check", ""]

    # 1. the head inside the window
    V = np.vstack([m.vertices for m in heads])
    r = np.hypot(V[:, 0], V[:, 1] - AY)
    i = np.argmax(r)
    clear = P.ENC_SHEET_R - r[i]
    crown = V[:, 2].max()
    md += [f"- Head about the axis: widest r {r[i]:.1f} at ({V[i, 0]:.0f}, {V[i, 1]:.0f}, {V[i, 2]:.0f}); "
           f"{clear:.1f} inside the sheet (D {2 * P.ENC_SHEET_R:.0f}). Crown z {crown:.1f}, {P.ENC_CAP_Z - crown:.1f} under the cap."]
    if clear < 10.0:
        issues.append(f"head within {clear:.1f} of the sheet (want >= 10)")
    if P.ENC_CAP_Z - crown < 10.0:
        issues.append(f"crown within {P.ENC_CAP_Z - crown:.1f} of the cap (want >= 10)")

    # 2. the sheet overlaps nothing (the band is printed now, D31: assembly_check covers it)
    sheet, blank = refs.get("sheet"), P.ENC_SHEET_BLANK
    if sheet is not None:
        for n, m in parts.items():
            v = overlap_volume(sheet, m)
            if v > 1.0:
                issues.append(f"the sheet runs {v:.0f} mm3 into {n}")
        b = sheet.bounds
        md.append(f"- Sheet: {b[1][2] - b[0][2]:.0f} tall, z {b[0][2]:.0f}..{b[1][2]:.0f}; "
                  f"blank {blank[0]} x {blank[1]} mm (a full tube, 20 overlap, 1 play in height).")
        if abs((b[1][2] - b[0][2]) - 1.0 - blank[1]) > 0.6:
            issues.append(f"the sheet is {b[1][2] - b[0][2]:.0f} tall but the blank says {blank[1]} (+1)")
    # the printed band: the panels' four screws each go through it, and it is no taller than its rims
    band = [parts[n] for n in ("enc_band_F", "enc_band_B") if n in parts]
    if band:
        bm = trimesh.util.concatenate(band)
        b = bm.bounds
        md.append(f"- Band (printed, two halves): z {b[0][2]:.1f}..{b[1][2]:.1f}, r {P.ENC_BAND_R + P.ENC_BAND_PLAY:.1f}.."
                  f"{P.ENC_BAND_R + P.ENC_BAND_PLAY + P.ENC_BAND_T:.1f}")
        x, zs = P.ENC_PANEL_SCREWS[0], P.ENC_PANEL_SCREWS[1:]
        r_panel = P.ENC_BAND_R + P.ENC_BAND_PLAY + P.ENC_BAND_T + P.ENC_FIT

        def wall_hit(o, d):
            """Does a ray from o along d meet the band within 8 mm (its near wall, not the far side)?"""
            loc, _, _ = bm.ray.intersects_location([o], [d])
            return bool(len(loc)) and float(np.linalg.norm(loc - o, axis=1).min()) < 8.0

        for a, pn in ((90.0, "enc_grille"), (270.0, "enc_hatch")):
            for sx in (-1, 1):
                for z in zs:
                    # rays in along the screw's axis from just outside the band: through the hole on the axis, into
                    # the band's wall 3.5 above and below it (a nut and a head have something to clamp)
                    ah = np.radians(a + np.degrees(np.arcsin(sx * x / r_panel)))
                    d = np.array([np.cos(ah), np.sin(ah), 0.0])
                    o = d * (P.ENC_BAND_R + 5.0) + np.array([0.0, AY, z])
                    if wall_hit(o, -d) or not all(wall_hit(o + np.array([0.0, 0.0, dz]), -d) for dz in (-3.5, 3.5)):
                        issues.append(f"{pn}'s screw at ({sx * x:+.0f}, z {z:.0f}): no clear hole with band round it")
        md.append(f"- The panels' 8 screws each pass a hole in the band with band round it"
                  if not any("no clear hole" in s for s in issues) else "- The panels' screws: see the result")

    # 3. the neck and its clamp plates against Cogley's head at rest (D30: they clamp his frame's nape ring between
    # the spine's saddle and the plates, the collar in the ring's hole; nothing may overlap any of his parts)
    neck = parts.get("neck")
    his = C.load()
    if neck is not None:
        md += ["", "## The neck and its clamp against Cogley's head (at rest)", ""]
        frame = [m for n, _, _, m in his if n == "SkullFrame"]
        for pn in ("neck", "neck_clamp_L", "neck_clamp_R"):
            pm = parts.get(pn)
            if pm is None:
                continue
            worst = []
            for name, inst, group, m in his:
                v = overlap_volume(pm, m)
                if v > 1.0:
                    worst.append((v, name, inst, group))
            worst.sort(reverse=True)
            for v, name, inst, group in worst[:12]:
                md.append(f"- {name} #{inst} ({group}): {v:.0f} mm3 into {pn}")
            if worst:
                issues.append(f"{pn} runs into " + ", ".join(f"{n} ({g}, {v:.0f} mm3)" for v, n, _, g in worst[:4]))
            g = to_mf(pm).min_gap(to_mf(frame[0]), 5.0) if frame else float("nan")
            md.append(f"- {pn}: no overlap with his parts; {g:.2f} mm from the frame's nape ring (modelled gap "
                      f"{P.NECK_SADDLE_GAP:.1f}: it sits on the ring)" if not worst else f"- {pn}: {g:.2f} mm from the frame")
            if not worst and g > 0.5:
                issues.append(f"{pn} is {g:.1f} mm off the nape ring: the clamp would not grip")
        md.append(f"- The clamp: the collar's top stays {P.NECK_COLLAR_GAP + P.NECK_SADDLE_GAP:.1f} under the plates, so four "
                  f"M4 x 12 pull the plates down onto the ring and the ring onto the saddle")
        # a hex key from above: clear height over each screw head along the ring's normal, his rear plate off
        th = np.radians(P.NAPE_TILT)
        nrm = np.array([0.0, np.sin(th), np.cos(th)])
        cy, cz = P.NAPE_CENTRE
        above = trimesh.util.concatenate([m for n, _, _, m in his if n not in ("RearPlate", "RearVent")])
        w_head = P.NAPE_T + P.NECK_SADDLE_GAP + P.NECK_CLAMP_T + 4.0
        for u, v in P.NECK_CLAMP_SCREWS:
            clear = np.inf
            for du in (-3.5, 0.0, 3.5):
                for dv in (-3.5, 0.0, 3.5):
                    o = np.array([u + du, cy + (v + dv) * np.cos(th) + w_head * np.sin(th), cz - (v + dv) * np.sin(th) + w_head * np.cos(th)])
                    loc, _, _ = above.ray.intersects_location([o], [nrm])
                    if len(loc):
                        clear = min(clear, float(np.linalg.norm(loc - o, axis=1).min()))
            md.append(f"- Screw ({u:+.0f}, {v:+.0f}): {clear:.0f} mm clear over its head for the hex key (rear plate off)")
            if clear < 25.0:
                issues.append(f"no room for a hex key over the clamp screw at ({u:+.0f}, {v:+.0f}): {clear:.0f} mm")

    # 4. the jaw sweep against the neck and its clamp plates
    if neck is not None:
        jaw = [m for n, _, _, m in his if any(n.startswith(j) for j in JAW_PARTS)]
        jaw_m = trimesh.util.concatenate(jaw)
        neck = trimesh.util.concatenate([parts[n] for n in ("neck", "neck_clamp_L", "neck_clamp_R") if n in parts])
        md += ["", "## The jaw swept against the neck and its clamp plates", "", "| angle | gap to the neck |", "|---|---|"]
        limit = None
        full = P.JAW_OPEN_DEG + P.JAW_OVERTRAVEL_DEG
        for a in np.arange(0.0, full + 1e-6, P.SWEEP_STEP_DEG):
            jm = jaw_m.copy().apply_transform(jaw_tf(a))
            v = overlap_volume(jm, neck)
            g = -np.cbrt(v) if v > 1.0 else gap(jm, neck)
            md.append(f"| {a:.0f} | {g:.1f} |")
            if v > 1.0 and limit is None:
                limit = a
        if limit is not None and limit <= P.JAW_OPEN_DEG:
            issues.append(f"the jaw hits the neck at {limit:.0f} deg (needs {P.JAW_OPEN_DEG:.0f})")
        elif limit is not None:
            notes.append(f"the jaw touches the neck at {limit:.0f} deg, past its {P.JAW_OPEN_DEG:.0f} deg limit")
        else:
            notes.append(f"the jaw clears the neck through {full:.0f} deg")

    # 5. what lives in the base and the cap
    md += ["", "## What lives in the base and the cap", ""]
    items = {n: m for n, m in refs.items() if n != "sheet"}
    deck_under = P.ENC_TOP_Z - P.ENC_PLATE_T     # the deck's underside
    for n, m in items.items():
        b = m.bounds
        for pn, pm in parts.items():
            v = overlap_volume(m, pm)
            if v > 1.0:
                issues.append(f"{n} runs {v:.0f} mm3 into {pn}")
        if n != "webcam":
            V = m.vertices
            rr = np.hypot(V[:, 0], V[:, 1] - AY).max()
            if b[1][2] > deck_under - 2.0:
                issues.append(f"{n} reaches z {b[1][2]:.0f}, into the deck ring (under {deck_under:.0f})")
            md.append(f"- {n}: z {b[0][2]:.0f}..{b[1][2]:.0f}, out to r {rr:.0f}")
        else:
            md.append(f"- webcam: z {b[0][2]:.0f}..{b[1][2]:.0f}, y {b[0][1]:.0f}..{b[1][1]:.0f}")
    names = list(items)
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            v = overlap_volume(items[names[i]], items[names[j]])
            if v > 1.0:
                issues.append(f"{names[i]} and {names[j]} overlap ({v:.0f} mm3)")

    # 6. bed fit
    bed = K.printer()["bed"]
    table = K.parts_table()
    md += ["", "## Pieces on the bed (in the print pose)", "", "| part | x | y | z |", "|---|---|---|---|"]
    for n, m in parts.items():
        pm = m.copy()
        for axis, deg in enumerate(table.get(n, {}).get("print_rotate", [0, 0, 0])):
            if deg:
                ax = [0, 0, 0]
                ax[axis] = 1
                pm.apply_transform(trimesh.transformations.rotation_matrix(np.radians(deg), ax))
        e = pm.extents
        md.append(f"| {n} | {e[0]:.0f} | {e[1]:.0f} | {e[2]:.0f} |")
        if sorted(e)[2] > bed[2] or sorted(e)[1] > bed[1] or sorted(e)[0] > bed[0]:
            issues.append(f"{n} ({e[0]:.0f} x {e[1]:.0f} x {e[2]:.0f}) does not fit the bed")

    out_dir = os.path.join(K.check_out(), "enclosure")
    os.makedirs(out_dir, exist_ok=True)
    png = render(parts, refs, heads, his, out_dir)
    md += ["", "## Result", ""] + [f"- FAIL {s}" for s in issues] + [f"- note: {s}" for s in notes]
    md.append(f"\nRender: {os.path.basename(png)}")
    with open(os.path.join(out_dir, "enclosure.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(md) + "\n")
    for s in issues:
        print("FAIL " + s)
    for s in notes:
        print("note: " + s)
    print("ENCLOSURE OK" if not issues else f"ENCLOSURE: {len(issues)} issue(s)")
    return 0


COLOURS = {"cap": (0.55, 0.60, 0.66), "top": (0.62, 0.66, 0.72), "bottom": (0.45, 0.50, 0.56), "band": (0.30, 0.33, 0.38), "tray": (0.45, 0.50, 0.56),
           "pedestal": (0.60, 0.66, 0.72), "grille": (0.25, 0.28, 0.32), "hatch": (0.25, 0.28, 0.32), "neck": (0.80, 0.64, 0.30),
           "neck_clamp_L": (0.70, 0.52, 0.22), "neck_clamp_R": (0.70, 0.52, 0.22)}
REF_COLOURS = {"sheet": (0.55, 0.80, 0.95), "speaker": (0.85, 0.85, 0.85), "bank": (0.96, 0.76, 0.48),
               "buck": (0.97, 0.86, 0.63), "board_1": (0.62, 0.83, 0.62), "board_2": (0.62, 0.83, 0.62),
               "webcam": (0.15, 0.15, 0.15)}


def colour_of(name):
    key = name.split("_")[1] if name.startswith("enc_") else name
    return COLOURS.get(key, (0.6, 0.6, 0.6))


def render(parts, refs, heads, his, out_dir):
    import render_views as RV

    def actors(names, extra=(), head=True, his_groups=None):
        acts = [RV.surface_actor(L.poly(parts[n]), colour_of(n)) for n in names if n in parts]
        for n in extra:
            if n in refs:
                acts.append(RV.surface_actor(L.poly(refs[n]), REF_COLOURS.get(n, (0.7, 0.7, 0.7))))
        if head:
            for m in heads:
                acts.append(RV.surface_actor(L.poly(m), (0.86, 0.80, 0.74)))
        if his_groups:
            for n, _, g, m in his:
                if g in his_groups:
                    acts.append(RV.surface_actor(L.poly(m), (0.75, 0.30, 0.28) if g == "mouth" else (0.5, 0.5, 0.55)))
        return acts

    allp = trimesh.util.concatenate(list(parts.values()))
    b = allp.bounds
    c = (b[0] + b[1]) / 2
    sc = 0.55 * float(max(b[1] - b[0]))
    everything = list(parts)
    bandless = [n for n in everything if not n.startswith("enc_band")]
    tiles = []
    tiles.append(("front, with the sheet", RV.render(actors(everything, ("sheet",)), c, (0, 1, 0), (0, 0, 1), sc)))
    tiles.append(("3/4 from the front right", RV.render(actors(everything, ("sheet",)), c, (-0.8, 1.0, 0.3), (0, 0, 1), sc)))
    tiles.append(("from the back (see-through)", RV.render(actors(everything, ("sheet",)), c, (0, -1, 0.1), (0, 0, 1), sc)))
    tiles.append(("left side, sheet and band off", RV.render(actors(bandless), c, (1, 0, 0), (0, 0, 1), sc)))
    base_names = [n for n in everything if n.startswith(("enc_bottom", "enc_tray", "enc_grille", "enc_hatch", "enc_pedestal"))]
    bc = np.array([0.0, AY, -95.0])
    tiles.append(("base from above, deck off: the bay", RV.render(actors(base_names, ("speaker", "bank", "buck", "board_1", "board_2"), head=False),
                                                                 bc, (0.2, 0.3, 1.0), (0, 1, 0), 200.0)))
    tiles.append(("base with the deck and the band, 3/4", RV.render(actors(base_names + ["enc_top_F", "enc_top_B", "enc_band_F", "enc_band_B"], head=False),
                                                                   bc, (0.8, 1.0, 0.5), (0, 0, 1), 200.0)))
    tiles.append(("the band from the back, panels off: hatch opening, leads' notch", RV.render(
        actors(["enc_bottom_F", "enc_bottom_B", "enc_tray", "enc_top_F", "enc_top_B", "enc_band_F", "enc_band_B"], head=False),
        bc, (0.3, -1.0, 0.25), (0, 0, 1), 200.0)))
    tiles.append(("band halves from inside: seam walls", RV.render(actors(["enc_band_F", "enc_band_B", "enc_bottom_F", "enc_bottom_B"], head=False),
                                                                   bc, (0.15, 0.6, 1.0), (0, 0, 1), 200.0)))
    cap_names = [n for n in everything if n.startswith("enc_cap")]
    cc = np.array([0.0, AY, 420.0])
    tiles.append(("cap from below: lips, ribs, webcam", RV.render(actors(cap_names, ("webcam",), head=False), cc, (0.2, 0.4, -1.0), (0, 1, 0), 200.0)))
    tiles.append(("cap from the front", RV.render(actors(cap_names, ("webcam",), head=False), cc, (0.3, 1.0, 0.5), (0, 0, 1), 200.0)))
    nc = np.array([0.0, AY - 30.0, 110.0])
    tiles.append(("neck and pedestal with Cogley's mouth and frame", RV.render(actors(["neck", "neck_clamp_L", "neck_clamp_R", "enc_pedestal", "enc_top_F", "enc_top_B"], (), head=False, his_groups={"mouth", "frame"}),
                                                                             nc, (1.0, 0.3, 0.2), (0, 0, 1), 160.0)))
    if "neck" in parts:
        jaw = [m for n, _, _, m in his if any(n.startswith(j) for j in JAW_PARTS)]
        jm = trimesh.util.concatenate(jaw).apply_transform(jaw_tf(P.JAW_OPEN_DEG))
        acts = actors(["neck", "neck_clamp_L", "neck_clamp_R", "enc_pedestal"], (), head=False, his_groups={"frame"})
        acts.append(RV.surface_actor(L.poly(jm), (0.85, 0.35, 0.30)))
        tiles.append((f"jaw open {P.JAW_OPEN_DEG:.0f} deg against the neck, from the left", RV.render(acts, nc, (1.0, 0.0, 0.0), (0, 0, 1), 140.0)))
    tiles.append(("deck halves from above: lip, rim, ribs, lead slot", RV.render(actors(["enc_top_F", "enc_top_B"], (), head=False),
                                                                           np.array([0.0, AY, -40.0]), (0.1, 0.2, 1.0), (0, 1, 0), 170.0)))
    return L.sheet(tiles, out_dir, "enclosure", cols=4, header_lines=[
        f"Enclosure M8 v1: D {2 * P.ENC_R_OUT:.0f} canister, window D {2 * P.ENC_SHEET_R:.0f}, z {P.ENC_TRAY_Z:.0f}..{P.ENC_CAP_Z + P.ENC_CAP_T:.0f}; "
        f"the neck spine (D25) behind the jaw",
        "15 thin prints (the base's band, dark, printed in two halves: D31); the window sheet (blue) is PETG, not a print"])


if __name__ == "__main__":
    sys.exit(main())

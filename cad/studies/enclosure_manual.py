"""
Pictures for the enclosure build manual (M8 v1, D26, D30, D31): one image per build step, drawn from the
print files in output/stl, the reference shapes in output/ref/enclosure and Cogley's frame.

Grey = already built, colour = added in the step, dark = screws and nuts, red = M4 inserts. The
drawing style and the helpers are the head manual's (assembly_manual.py).

Two fixes the human makes by hand are drawn in, because the v1 pedestal needs them (found
2026-10-30 while writing the manual):
  - a lead door in the pedestal's tube (its inside was closed all round by the tube and the
    tray's inner rib, so the head's leads and the fan's air had no way into the bay);
  - glue where the tray's four short ribs pass under the tube, instead of the flange's four
    screws, which sit under the pedestal's solid top plate where no driver reaches.

Run:  python cad/studies/enclosure_manual.py   (after enclosure.py and cogley_head.py)
      -> output/manual/enclosure/<step>.png
"""
import os
import sys

import numpy as np
import trimesh

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, HERE)
import cadkit as K  # noqa: E402
import cogley_head as C  # noqa: E402
import enclosure as E  # noqa: E402
import assembly_manual as AM  # noqa: E402

sys.stdout.reconfigure(encoding="utf-8")
P = K.params()
AM.OUT = os.path.join(K.PROJECT, "output", "manual", "enclosure")
AY = P.ENC_AXIS_Y
STL = os.path.join(K.PROJECT, "output", "stl")
REF = os.path.join(K.PROJECT, "output", "ref", "enclosure")

# the lead door (by hand, see the docstring): centred on the left side as seen from the front (-x),
# above the buck, under the deck
DOOR = dict(angle=180.0, width=40.0, z0=-100.0, z1=-50.0)
GLUE = (0.98, 0.80, 0.10)
FOOT = (0.20, 0.20, 0.20)
RED = (0.85, 0.12, 0.12)

_M = {}


def part(name):
    if name not in _M:
        path = os.path.join(STL, name + ".stl")
        if not os.path.exists(path):
            path = os.path.join(REF, name + ".stl")
        _M[name] = trimesh.load(path, force="mesh")
    return _M[name]


def pedestal_with_door():
    if "ped_door" not in _M:
        a = np.radians(DOOR["angle"])
        box = trimesh.creation.box(extents=(12.0, DOOR["width"], DOOR["z1"] - DOOR["z0"]))
        box.apply_transform(trimesh.transformations.rotation_matrix(a, (0, 0, 1)))
        box.apply_translation((45.0 * np.cos(a), AY + 45.0 * np.sin(a), (DOOR["z0"] + DOOR["z1"]) / 2))
        _M["ped_door"] = part("enc_pedestal").difference(box, engine="manifold")
    return _M["ped_door"]


def at(r, deg, z):
    a = np.radians(deg)
    return np.array([r * np.cos(a), AY + r * np.sin(a), z])


def radial(deg, inward=True):
    a = np.radians(deg)
    d = np.array([np.cos(a), np.sin(a), 0.0])
    return -d if inward else d


def nut(centre, axis):
    """An M3 hex nut, 2.4 thick, starting at `centre` along `axis`."""
    a = np.asarray(axis, float) / np.linalg.norm(axis)
    m = trimesh.creation.cylinder(radius=5.5 / np.cos(np.radians(30)) / 2, height=2.4, sections=6)
    m.apply_transform(trimesh.geometry.align_vectors([0, 0, 1.0], a))
    m.apply_translation(np.asarray(centre, float) + a * 1.2)
    m.metadata["mouth"], m.metadata["axis"] = np.asarray(centre, float), a
    return m


def blob(point, r=4.0, colour_key=None):
    m = trimesh.creation.icosphere(subdivisions=2, radius=r)
    m.apply_translation(point)
    return m


def ring_point(u, v, w):
    """A point in the nape ring's frame (enclosure.ring_loc), in the head frame; and the ring's normal."""
    loc = E.ring_loc(w) * E.Pos(u, v, 0)
    p = loc.position
    t = np.radians(P.NAPE_TILT)
    normal = np.array([0.0, np.sin(t), np.cos(t)])   # Rot(-tilt) about x tips +z toward +y
    return np.array([p.X, p.Y + AY, p.Z]), normal


# ---------------------------------------------------------------- views

V = AM.v
FRONT, BACK, BELOW = AM.FRONT, AM.BACK, AM.BELOW
Q_FL, Q_FR, Q_BL, Q_BR = AM.Q_FL, AM.Q_FR, AM.Q_BL, AM.Q_BR
SIDE_MX = ((-1, 0, 0), (0, 0, 1))                    # the -x side: your right as you face the front (the buck's side)
TOP = ((0, 0.35, 1), (0, 1, 0))
TOP_BACK = ((0, -0.55, 1), (0, -1, 0))
UNDER = ((0, 0.25, -1), (0, 1, 0))
INSIDE_L = ((0.45, -0.25, 0.85), (0, 0, 1))          # from above, looking into the base toward the left


def step(name, title, views, **kw):
    return AM.step_image(name, title, views, **kw)


# ---------------------------------------------------------------- stage 1: neck and pedestal

def stage1():
    ped, neck = pedestal_with_door(), part("neck")
    d = DOOR
    door_mid = at(45.0, d["angle"], (d["z0"] + d["z1"]) / 2)
    step("s1_01_lead_door", "Step 1.5  Cut a lead door in the pedestal",
         [V(SIDE_MX, "the door's side: your right as you face the neck's front"), V(Q_FL, "front, from your right")], built=[part("neck")], new=[ped],
         colours=[(0.60, 0.66, 0.72)], focus=[ped],
         labels=[(0, door_mid, "door 40 x 50\ntop edge 50 mm\nunder the top face", (230, -40))])

    sq = P.NECK_BOLT_SQUARE / 2
    foot = [AM.insert((sx * sq, AY + sy * sq, 0.0), (0, 0, 1), "M4", 8.0) for sx in (-1, 1) for sy in (-1, 1)]
    step("s1_02_foot_inserts", "Step 1.1  Four M4 inserts into the neck's foot",
         [V(UNDER, "from below")], new=[neck], inserts=foot, colours=[(0.80, 0.64, 0.30)], focus=[neck],
         labels=[(0, foot, "M4 insert, flush\nwith the foot", None)])

    wt = P.NAPE_T - P.NECK_COLLAR_GAP
    col = []
    for u, v in P.NECK_CLAMP_SCREWS:
        p, n = ring_point(u, v, wt)
        col.append(AM.insert(p, -n, "M4", 8.0))
    top_view = ((0, -0.35, 1), (0, 1, 0))
    step("s1_03_collar_inserts", "Step 1.2  Four M4 inserts into the collar's top",
         [V(top_view, "from above, the back at the bottom")], new=[neck], inserts=col, colours=[(0.80, 0.64, 0.30)],
         focus=col + [neck], pad=0.9,
         labels=[(0, col, "M4 insert, square\nto the collar's top", None)])

    bolts = [AM.screw((sx * sq, AY + sy * sq, -P.ENC_PEDESTAL_TOP_T), (0, 0, 1), 4.0, 12.0)
             for sx in (-1, 1) for sy in (-1, 1)]
    step("s1_04_neck_on_pedestal", "Step 1.4  Neck on the pedestal: 4 x M4x12",
         [V(((0.0, 0.001, -1.0), (0, 1, 0)), "from below, up the pedestal's open end"), V(Q_FL, "front, from your right")],
         built=[ped], new=[neck], hardware=bolts, colours=[(0.80, 0.64, 0.30)], focus=[ped, neck],
         labels=[(0, bolts, "M4 x 12, long\n3 mm hex driver", None)])


# ---------------------------------------------------------------- stage 2: the base shell

def stage2():
    tray, ped, neck = part("enc_tray"), pedestal_with_door(), part("neck")
    feet = []
    for a in (45.0, 135.0, 225.0, 315.0):
        f = AM.cylinder(at(105.0, a, P.ENC_TRAY_Z), (0, 0, -1), 20.0, 20.0)
        feet.append(f)
    step("s2_01_feet", "Step 2.1  Four rubber feet under the tray",
         [V(((0.3, 0.6, -1.0), (0, 1, 0)), "from below, the front at the top")], built=[tray], new=feet,
         colours=[FOOT] * 4, focus=[tray],
         labels=[(0, feet[0], "20 mm foot, about\n20 mm in from the edge", None)])

    glue = [blob(at(44.2, a, -142.0), 3.5) for a in (0.0, 90.0, 180.0, 270.0)]
    step("s2_02_pedestal_on_tray", "Step 2.2  Pedestal on the tray, centred and glued",
         [V(Q_FL, "front, from your right"), V(((0.9, 0.9, 0.25), (0, 0, 1)), "front, from your left, low")],
         built=[tray], new=[ped, neck] + glue, colours=[(0.60, 0.66, 0.72), (0.80, 0.64, 0.30)] + [GLUE] * 4,
         focus=[tray, ped],
         labels=[(0, at(95.0, 180.0, P.ENC_TRAY_Z + 2.5), "80 mm from the tray's\nedge to the tube,\nall round", None),
                 (None, glue, "glue where the short\nrib runs under the tube", None)])

    bf, bb = part("enc_bottom_F"), part("enc_bottom_B")
    z_ear = E.RIB_TOP + P.ENC_PLATE_T
    ears = [AM.screw(at(P.ENC_TRAY_RIBS[0][0] + 1.0, a, z_ear), (0, 0, -1), 3.0, 8.0) for a in P.ENC_EARS_DEG]
    zs = E.RIB_TOP + P.ENC_PLATE_T + P.ENC_SEAM_WALL[1] / 2
    seam = [AM.screw((sx * 139.0, AY + P.ENC_SEAM_WALL[0], zs), (0, -1, 0), 3.0, 8.0) for sx in (-1, 1)]
    seam_n = [nut((sx * 139.0, AY - P.ENC_SEAM_WALL[0], zs), (0, -1, 0)) for sx in (-1, 1)]
    step("s2_03_bottom_rings", "Step 2.3  Bottom ring halves onto the tray",
         [V(TOP, "from above, the front at the bottom"), V(((0.8, 1.0, 0.6), (0, 0, 1)), "front, from your left")],
         built=[tray, ped, neck], new=[bf, bb], hardware=ears + seam + seam_n,
         colours=[(0.45, 0.50, 0.56), (0.62, 0.55, 0.45)], focus=[tray, bf, bb],
         labels=[(0, ears, "M3 x 8 self-tapping\ninto the tray's boss", None),
                 (0, seam, "M3 x 8 + nut\nthrough both seam walls", None)])

    band_f, band_b = part("enc_band_F"), part("enc_band_B")
    r_in, zb, zt, szs = P.ENC_BAND_SEAM
    xs = (r_in + E.BAND_RI) / 2
    bseam = [AM.screw((sx * xs, AY + P.ENC_SEAM_WALL[0], z), (0, -1, 0), 3.0, 8.0) for sx in (-1, 1) for z in szs]
    bseam_n = [nut((sx * xs, AY - P.ENC_SEAM_WALL[0], z), (0, -1, 0)) for sx in (-1, 1) for z in szs]
    built = [tray, ped, neck, bf, bb]
    step("s2_04_band", "Step 2.4  The band's two halves round the rims",
         [V(Q_FL, "front, from your right"), V(((0.35, 0.2, 0.9), (0, 0, 1)), "from above: the seam walls on your left")],
         built=built, new=[band_f, band_b], hardware=bseam + bseam_n,
         colours=[(0.30, 0.33, 0.38), (0.42, 0.36, 0.30)], focus=[band_f, band_b],
         labels=[(1, bseam[:2], "M3 x 8 + nut, turned\nwith a 2.5 mm L key", None),
                 (0, at(146.0, 90.0, -90.0), "F: the front opening\n(the speaker)", None)])

    z_rim = E.RIB_TOP + P.ENC_PLATE_T + P.ENC_BAND_SCREW_Z
    r_out = E.BAND_RI + P.ENC_BAND_T
    rim = [AM.screw(at(r_out, a, z_rim), radial(a), 3.0, 8.0) for a in P.ENC_EARS_DEG]
    rim_n = [nut(at(E.RIM_R, a, z_rim), radial(a)) for a in P.ENC_EARS_DEG]
    slot_n = []
    for a in (90.0, 270.0):
        for ah, z in E.panel_screws(a):
            if z == max(P.ENC_PANEL_SCREWS[1:]):
                slot_n.append(nut(at(E.BAND_RI, ah, z), radial(ah)))
    built += [band_f, band_b]
    step("s2_05_band_screws", "Step 2.5  Band to the rims; nuts into the 4 slots",
         [V(((0.55, 0.75, 0.45), (0, 0, 1)), "front, from your left"), V(((0.0, -0.12, 1.0), (0, 1, 0)), "the front half from above (the rest hidden)",
                       [band_f, bf, tray] + rim[:2] + rim_n[:2] + slot_n)],
         built=built, hardware=rim + rim_n + slot_n, focus=[band_f, band_b],
         labels=[(0, rim[:2], "M3 x 8 through band and\nrim, nut inside the rim", None),
                 (1, [at(E.BAND_RI - 1.2, ah, z + 3.4) for ah, z in E.panel_screws(90.0) if z == max(P.ENC_PANEL_SCREWS[1:])][0],
                  "M3 nut dropped into\nthe slot, flat on the band", None)])

    grille = part("enc_grille")
    gs = [AM.screw(at(E.PANEL_R + P.ENC_PANEL[3], ah, z), radial(ah), 3.0, 8.0) for ah, z in E.panel_screws(90.0)]
    step("s2_06_grille", "Step 2.6  Grille over the front opening",
         [V(FRONT, "front")], built=built, new=[grille], hardware=gs, colours=[(0.25, 0.28, 0.32)],
         focus=[band_f, grille],
         labels=[(0, gs[2:], "upper: into the nuts\nin the band's slots", None),
                 (0, gs[:2], "lower: nut held from\nunder the band's edge", None)])
    return built + [grille]


# ---------------------------------------------------------------- stage 3: the bay

def stage3(built):
    bay = [part(n) for n in ("bank", "board_1", "board_2", "buck", "speaker")]
    cols = [(0.96, 0.76, 0.48), (0.62, 0.83, 0.62), (0.40, 0.70, 0.45), (0.97, 0.86, 0.63), (0.85, 0.85, 0.85)]
    shell = [m for m in built if m is not part("enc_band_F") and m is not part("enc_band_B") and m is not part("enc_grille")]
    step("s3_01_bay", "Step 3.1  The bay",
         [V(((0, -0.2, 1), (0, -1, 0)), "from above, the front at the bottom (band hidden)"),
          V(((-0.6, 0.9, 0.55), (0, 0, 1)), "front, from your right (band hidden)")],
         built=shell, new=bay, colours=cols, focus=[part("enc_tray")],
         labels=[(0, bay[0], "power bank, between\nits rails", None), (0, bay[2], "board 2 on 25 mm\nstandoffs over board 1", None),
                 (0, bay[3], "buck, on its side", None), (0, bay[4], "speaker in its saddles", None)])
    return bay


# ---------------------------------------------------------------- stage 4: the head

def stage4(built, bay):
    frame = [m for n, k, g, m in C.load({"frame"})]
    plates = [part("neck_clamp_L"), part("neck_clamp_R")]
    t0 = P.NAPE_T + P.NECK_SADDLE_GAP + P.NECK_CLAMP_T
    bolts = []
    for u, v in P.NECK_CLAMP_SCREWS:
        p, n = ring_point(u, v, t0)
        bolts.append(AM.screw(p, -n, 4.0, 12.0))
    neck = part("neck")
    view_back = ((0.25, -1.0, 0.55), (0, 0, 1))
    step("s4_01_head_on_neck", "Step 1.3  Test-fit: the head down onto the neck",
         [V(((1, -0.35, 0.15), (0, 0, 1)), "from the side, a little behind (only his frame drawn)")],
         built=[neck], new=frame, colours=[(0.75, 0.75, 0.80)] * len(frame), focus=[neck] + frame, ghost=False,
         arrows=[(0, (130, -120, 330), (130, -120, 250))],
         labels=[(0, neck, "neck (collar hidden\ninside the frame)", None)])
    step("s4_02_clamp_plates", "Step 4.4  Clamp plates and their 4 x M4x12",
         [V(view_back, "from behind, the head's rear plate off")],
         built=[neck] + frame, new=plates, hardware=bolts, colours=[(0.70, 0.52, 0.22), (0.92, 0.62, 0.20)],
         focus=plates + bolts, pad=2.2,
         labels=[(0, bolts, "M4 x 12, 3 mm hex key\nfrom behind", None), (0, plates[0], "clamp plate", None)])


# ---------------------------------------------------------------- stage 5: close the base

def stage5(built, bay):
    tf, tb = part("enc_top_F"), part("enc_top_B")
    zs = E.TOP_Z + P.ENC_SEAM_WALL[1] / 2
    seam = [AM.screw((sx * 100.0, AY + P.ENC_SEAM_WALL[0], zs), (0, -1, 0), 3.0, 8.0) for sx in (-1, 1)]
    seam_n = [nut((sx * 100.0, AY - P.ENC_SEAM_WALL[0], zs), (0, -1, 0)) for sx in (-1, 1)]
    z_rim = E.TOP_Z + P.ENC_BAND_SCREW_Z
    r_out = E.BAND_RI + P.ENC_BAND_T
    rim = [AM.screw(at(r_out, a, z_rim), radial(a), 3.0, 6.0) for a in P.ENC_BAND_SCREWS_DEG]
    rim_n = [nut(at(E.RIM_R, a, z_rim), radial(a)) for a in P.ENC_BAND_SCREWS_DEG]
    step("s5_01_deck", "Step 5.1  The deck's two halves",
         [V(((0.3, 0.6, 0.9), (0, 0, 1)), "from above, front, from your left")], built=built + bay, new=[tf, tb],
         hardware=seam + seam_n + rim + rim_n, colours=[(0.62, 0.66, 0.72), (0.70, 0.62, 0.52)], focus=[tf, tb],
         labels=[(0, seam, "M3 x 8 + nut\nthrough the seam walls", None),
                 (0, rim[:3], "M3 x 6 (not 8) + nut,\nnut inside the rim", None)])
    built = built + [tf, tb]
    hatch = part("enc_hatch")
    hs = [AM.screw(at(E.PANEL_R + P.ENC_PANEL[3], ah, z), radial(ah), 3.0, 8.0) for ah, z in E.panel_screws(270.0)]
    step("s5_02_hatch", "Step 6.6  Hatch over the back opening",
         [V(BACK, "back")], built=built, new=[hatch], hardware=hs, colours=[(0.25, 0.28, 0.32)],
         focus=[part("enc_band_B"), hatch],
         labels=[(0, at(E.PANEL_R + 2.0, 270.0, -146.0), "leads' notch", (0, 90)),
                 (0, hs[2:], "upper: into the\nslot nuts", None)])
    return built + [hatch]


# ---------------------------------------------------------------- stage 6: window and cap

def stage6(built):
    sheet = part("sheet")
    neck = part("neck")
    step("s6_01_window", "Step 6.3  The window on the deck",
         [V(Q_FL, "front, from your right")],
         built=built, new=[sheet], colours=[(0.55, 0.80, 0.95)], focus=[sheet, part("enc_tray")],
         labels=[])
    cf, cb = part("enc_cap_F"), part("enc_cap_B")
    cam = part("webcam")
    zs = E.CAP_Z - P.ENC_SEAM_WALL[1] / 2
    seam = [AM.screw((x, AY + P.ENC_SEAM_WALL[0], zs), (0, -1, 0), 3.0, 8.0) for x in (-120.0, -70.0, 70.0, 120.0)]
    seam_n = [nut((x, AY - P.ENC_SEAM_WALL[0], zs), (0, -1, 0)) for x in (-120.0, -70.0, 70.0, 120.0)]
    step("s6_02_cap", "Step 6.4  Webcam and cap halves",
         [V(((0, 0.45, -1), (0, 1, 0)), "the cap from below, the front at the top")], new=[cf, cb, cam], hardware=seam + seam_n,
         colours=[(0.55, 0.60, 0.66), (0.66, 0.60, 0.52), (0.15, 0.15, 0.15)], focus=[cf, cb],
         labels=[(0, cam, "webcam, lens to the front", None), (0, seam[:2], "M3 x 8 + nut", None)])
    step("s6_03_complete", "The finished enclosure (the head not drawn)",
         [V(Q_FL, "front"), V(Q_BR, "back")], built=[], new=built + [sheet, cf, cb],
         colours=[(0.62, 0.64, 0.68)] * len(built) + [(0.55, 0.80, 0.95), (0.55, 0.60, 0.66), (0.55, 0.60, 0.66)],
         focus=[part("enc_tray"), cf], labels=[])


def main():
    which = set(sys.argv[1:])
    stage1()
    built = stage2()
    bay = stage3(built)
    if not which or "head" in which:
        stage4(built, bay)
    built = stage5(built, bay)
    stage6(built)
    return 0


if __name__ == "__main__":
    sys.exit(main())

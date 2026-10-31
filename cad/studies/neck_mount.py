"""
Renders of how the head attaches to the base (M8, D25 and D30): the neck's foot bolted to the pedestal, the
pedestal on the tray, and at the top the clamp on Cogley's frame. Nothing is drilled in his parts: the frame's
nape is a flat ring round a hexagonal hole; the spine's top (the saddle) sits under the ring, a collar rises
from it into the hole, and two plates on top of the ring screw down into the collar (4 x M4 x 12 into heat-set
M4 inserts), so the ring is clamped between them. Reads the print files in output/stl and his parts from
output/ref/head_a2.

Run:  python cad/studies/neck_mount.py   (after enclosure.py and cogley_head.py)
  -> <out>/studies/neck_mount.png
"""
import os
import sys

import numpy as np
import trimesh

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import cadkit as K  # noqa: E402
import cogley_head as C  # noqa: E402
import layout_check as L  # noqa: E402
import render_views as RV  # noqa: E402

sys.stdout.reconfigure(encoding="utf-8")
P = K.params()
AY = P.ENC_AXIS_Y
GOLD, AMBER, GREY, BLUE, RED, STEEL = ((0.80, 0.64, 0.30), (0.62, 0.42, 0.16), (0.62, 0.66, 0.72), (0.45, 0.50, 0.56),
                                       (0.85, 0.30, 0.25), (0.25, 0.25, 0.28))
BRASS, EYE = (0.95, 0.80, 0.35), (0.55, 0.62, 0.80)
TH = np.radians(P.NAPE_TILT)
NRM = np.array([0.0, np.sin(TH), np.cos(TH)])


def load(name):
    return trimesh.load(os.path.join(K.stl_dir(), name + ".stl"), force="mesh")


def half(mesh, x_cut=0.0):
    """The x <= x_cut part of a mesh, capped (a cut-away), by a manifold boolean."""
    import manifold3d as mf
    m = mf.Manifold(mf.Mesh(vert_properties=np.asarray(mesh.vertices, np.float32), tri_verts=np.asarray(mesh.faces, np.uint32)))
    box = mf.Manifold.cube((1000.0, 1000.0, 2000.0), True).translate((x_cut - 500.0, AY, 100.0))
    r = (m ^ box).to_mesh()
    return trimesh.Trimesh(np.asarray(r.vert_properties)[:, :3], np.asarray(r.tri_verts), process=True)


def cylinder(r, z0, z1, x, y):
    c = trimesh.creation.cylinder(radius=r, height=z1 - z0, sections=32)
    c.apply_translation((x, y, (z0 + z1) / 2))
    return c


def ring_point(u, v, w):
    """A point in the nape ring's frame (origin on its underside at the hole's centre, w along its normal)."""
    cy, cz = P.NAPE_CENTRE
    return np.array([u, cy + v * np.cos(TH) + w * np.sin(TH), cz - v * np.sin(TH) + w * np.cos(TH)])


def ring_cylinder(r, u, v, w0, w1):
    c = trimesh.creation.cylinder(radius=r, height=w1 - w0, sections=32)
    c.apply_transform(trimesh.transformations.rotation_matrix(-TH, (1, 0, 0)))
    c.apply_translation(ring_point(u, v, (w0 + w1) / 2))
    return c


def foot_screws():
    """M4 x 12 up through the pedestal's top plate into the neck's foot."""
    out = []
    sq = P.NECK_BOLT_SQUARE / 2
    for sx in (-1, 1):
        for sy in (-1, 1):
            out.append(cylinder(2.0, -P.ENC_PEDESTAL_TOP_T - 3.0, P.M4_INSERT_DEPTH - 1.0, sx * sq, AY + sy * sq))
            out.append(cylinder(3.5, -P.ENC_PEDESTAL_TOP_T - 3.0, -P.ENC_PEDESTAL_TOP_T, sx * sq, AY + sy * sq))
    return trimesh.util.concatenate(out)


def clamp_screws():
    """4 x M4 x 12 down through the plates into the collar's inserts."""
    out = []
    top = P.NAPE_T + P.NECK_SADDLE_GAP + P.NECK_CLAMP_T                 # the plates' top face
    for u, v in P.NECK_CLAMP_SCREWS:
        out.append(ring_cylinder(2.0, u, v, top - 12.0, top))
        out.append(ring_cylinder(3.5, u, v, top, top + 4.0))
    return trimesh.util.concatenate(out)


def inserts():
    wt = P.NAPE_T - P.NECK_COLLAR_GAP
    return trimesh.util.concatenate([ring_cylinder(P.M4_INSERT_HOLE / 2 + 0.2, u, v, wt - 8.0, wt) for u, v in P.NECK_CLAMP_SCREWS])


def actors(items):
    return [RV.surface_actor(L.poly(m), rgb) for m, rgb in items if m is not None and len(m.faces)]


def main():
    neck, ped, tray = load("neck"), load("enc_pedestal"), load("enc_tray")
    plates = trimesh.util.concatenate([load("neck_clamp_L"), load("neck_clamp_R")])
    deck = trimesh.util.concatenate([load("enc_top_F"), load("enc_top_B")])
    his = C.load({"frame", "mouth", "eyes"})
    frame = trimesh.util.concatenate([m for n, _, g, m in his if n == "SkullFrame"])
    mouth = trimesh.util.concatenate([m for n, _, g, m in his if g == "mouth"])
    eyeplate = trimesh.util.concatenate([m for n, _, g, m in his if n == "SnapEyemech v20"])
    feet, bolts, ins = foot_screws(), clamp_screws(), inserts()
    both = trimesh.util.concatenate([feet, bolts])
    top_c = ring_point(0.0, 0.0, 3.0)
    tiles = []
    # 1. the whole chain from the left, cut at x = 0
    cut = [(half(neck), GOLD), (half(plates), AMBER), (half(ped), BLUE), (half(deck), GREY), (half(tray), BLUE),
           (half(frame), STEEL), (both, RED)]
    tiles.append(("the chain, cut at the midline: tray, pedestal, neck, his frame's ring clamped at the top",
                  RV.render(actors(cut), np.array([0.0, AY - 25.0, 60.0]), (1.0, 0.0, 0.0), (0, 0, 1), 230.0)))
    # 2. the clamp, cut through the back screws, close
    x = P.NECK_CLAMP_SCREWS[2][0]
    close = [(half(neck, x), GOLD), (half(plates, x), AMBER), (half(frame, x), STEEL), (half(bolts, x), RED), (half(ins, x), BRASS)]
    tiles.append((f"cut at x = {x:.0f}: the ring between the saddle and a plate, the collar in its hole, an M4 in its insert",
                  RV.render(actors(close), top_c, (1.0, 0.0, 0.0), (0, 0, 1), 45.0)))
    # 3. from behind and above, his rear plate off: the plates on the ring, the four screw heads, the EyeMech's plate
    tiles.append(("from behind, his rear plate off: two plates on the ring, 4 x M4 behind the EyeMech's base plate (blue)",
                  RV.render(actors([(neck, GOLD), (plates, AMBER), (frame, STEEL), (bolts, RED), (eyeplate, EYE)]),
                            top_c + np.array([0.0, 0.0, 10.0]), (0.25, -1.0, 0.9), (0, 0, 1), 85.0)))
    # 4. exploded: the frame lifted, the plates lifted further, the screws above them
    lift_f, lift_p = 45.0, 75.0
    ex = [(neck, GOLD), (ins, BRASS), (frame.copy().apply_translation(NRM * lift_f), STEEL),
          (plates.copy().apply_translation(NRM * lift_p), AMBER), (bolts.copy().apply_translation(NRM * (lift_p + 25.0)), RED)]
    tiles.append(("exploded: the head drops on (the collar into the ring's hole), the plates go on, 4 screws",
                  RV.render(actors(ex), top_c + np.array([0.0, 0.0, 30.0]), (0.8, -1.0, 0.5), (0, 0, 1), 140.0)))
    # 5. the neck's top alone: saddle, collar, inserts, the way down for the leads
    tiles.append(("the neck's top: the saddle (cut to the ring's underside), the collar, 4 inserts, the leads' hole",
                  RV.render(actors([(neck, GOLD), (ins, BRASS)]), top_c, (0.5, -0.8, 1.0), (0, 0, 1), 60.0)))
    # 6. from the right, cut at x = 0, with the mouth: the jaw swings in front of the spine
    tiles.append(("from the right, cut: the spine behind the jaw, the ring clamped over it",
                  RV.render(actors([(half(neck), GOLD), (half(plates), AMBER), (half(frame), STEEL), (half(mouth), (0.75, 0.30, 0.28)),
                                    (bolts, RED)]), np.array([0.0, AY - 25.0, 140.0]), (1.0, 0.0, 0.0), (0, 0, 1), 110.0)))
    out_dir = os.path.join(K.check_out(), "studies")
    png = L.sheet(tiles, out_dir, "neck_mount", cols=3, header_lines=[
        "How the head attaches (D25, D30): pedestal -> 4 x M4 x 12 up into the neck's foot -> neck -> his frame's nape ring,",
        "clamped between the spine's saddle and two plates, the collar in the ring's hole, 4 x M4 x 12 into inserts. "
        "Gold: neck. Amber: plates. Red: screws. Nothing drilled in his parts"])
    print("wrote", png)
    return 0


if __name__ == "__main__":
    sys.exit(main())

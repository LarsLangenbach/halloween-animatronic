"""
Renders of how the head attaches to the base (M8 v1, D25): Cogley's frame on the neck's spine, the
neck's foot bolted to the pedestal, the pedestal on the tray. Reads the print files in output/stl and
his parts from output/ref/head_a2.

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
GOLD, GREY, BLUE, RED, STEEL = (0.80, 0.64, 0.30), (0.62, 0.66, 0.72), (0.45, 0.50, 0.56), (0.85, 0.30, 0.25), (0.25, 0.25, 0.28)


def load(name):
    return trimesh.load(os.path.join(K.stl_dir(), name + ".stl"), force="mesh")


def half(mesh):
    """The x <= 0 half of a mesh, capped (a cut-away at the midline), by a manifold boolean."""
    import manifold3d as mf
    m = mf.Manifold(mf.Mesh(vert_properties=np.asarray(mesh.vertices, np.float32), tri_verts=np.asarray(mesh.faces, np.uint32)))
    box = mf.Manifold.cube((1000.0, 1000.0, 2000.0), True).translate((-500.0, AY, 100.0))
    r = (m ^ box).to_mesh()
    return trimesh.Trimesh(np.asarray(r.vert_properties)[:, :3], np.asarray(r.tri_verts), process=True)


def cylinder(r, z0, z1, x, y):
    c = trimesh.creation.cylinder(radius=r, height=z1 - z0, sections=32)
    c.apply_translation((x, y, (z0 + z1) / 2))
    return c


def screws():
    """The bolts and screws of the chain, as solids: M4 up into the foot, M3 up into his frame."""
    out = []
    sq = P.NECK_BOLT_SQUARE / 2
    for sx in (-1, 1):
        for sy in (-1, 1):
            out.append(cylinder(2.0, -P.ENC_PEDESTAL_TOP_T - 3.0, P.M4_INSERT_DEPTH - 1.0, sx * sq, AY + sy * sq))   # M4 x 12
            out.append(cylinder(3.5, -P.ENC_PEDESTAL_TOP_T - 3.0, -P.ENC_PEDESTAL_TOP_T, sx * sq, AY + sy * sq))   # its head
    for x, y in P.NECK_SPINE_SCREWS:
        out.append(cylinder(1.5, P.NECK_SPINE_TOP - P.NECK_SPINE_TOP_T - 3.0, P.NECK_SPINE_TOP + 6.0, x, y))        # M3 x 10
    return trimesh.util.concatenate(out)


def actors(items):
    return [RV.surface_actor(L.poly(m), rgb) for m, rgb in items if m is not None and len(m.faces)]


def main():
    neck, ped, tray = load("neck"), load("enc_pedestal"), load("enc_tray")
    deck = trimesh.util.concatenate([load("enc_top_F"), load("enc_top_B")])
    his = C.load({"frame", "mouth"})
    frame = trimesh.util.concatenate([m for n, _, g, m in his if g == "frame" and n == "SkullFrame"])
    mouth = trimesh.util.concatenate([m for n, _, g, m in his if g == "mouth"])
    bolts = screws()
    tiles = []
    c_chain = np.array([0.0, AY - 20.0, 30.0])
    # 1. the whole chain from the left, cut at x = 0 so the bolts and the hollow spine show
    cut = [(half(neck), GOLD), (half(ped), BLUE), (half(deck), GREY), (half(tray), BLUE), (half(frame), STEEL), (bolts, RED)]
    tiles.append(("the chain, cut at the midline: tray, pedestal, foot, tube, spine, his frame",
                  RV.render(actors(cut), c_chain, (1.0, 0.0, 0.0), (0, 0, 1), 200.0)))
    # 2. the foot on the pedestal, close, cut
    tiles.append(("the neck's foot bolted to the pedestal's top plate (4 x M4 x 12 from inside the tube), cut",
                  RV.render(actors(cut), np.array([0.0, AY, 0.0]), (1.0, 0.4, 0.3), (0, 0, 1), 60.0)))
    # 3. the spine's top under his frame's nape, from behind and above
    top = [(neck, GOLD), (frame, STEEL), (bolts, RED)]
    tiles.append(("the spine's top under his frame's nape, from behind: notches round two ribs, 4 x M3 up",
                  RV.render(actors(top), np.array([0.0, AY - 40.0, 160.0]), (0.3, -1.0, 0.6), (0, 0, 1), 70.0)))
    # 4. the same from the front, with the mouth, cut at the midline
    tiles.append(("from the right, cut: the spine behind the jaw, the top plate under the nape bar",
                  RV.render(actors([(half(neck), GOLD), (half(frame), STEEL), (half(mouth), (0.75, 0.30, 0.28)), (bolts, RED)]),
                            np.array([0.0, AY - 20.0, 120.0]), (1.0, 0.0, 0.0), (0, 0, 1), 110.0)))
    # 5. exploded, 3/4 from the back left
    ex = [(frame.copy().apply_translation((0, 0, 60.0)), STEEL), (neck, GOLD),
          (ped.copy().apply_translation((0, 0, -50.0)), BLUE), (deck.copy().apply_translation((0, 0, -50.0)), GREY),
          (tray.copy().apply_translation((0, 0, -90.0)), BLUE)]
    tiles.append(("exploded: frame lifted 60, pedestal and deck dropped 50, tray dropped 90",
                  RV.render(actors(ex), np.array([0.0, AY - 20.0, 60.0]), (-0.8, -1.0, 0.5), (0, 0, 1), 260.0)))
    # 6. the leads' path: the spine's top opening and the bore, from above
    tiles.append(("from above: the spine's top opening for the leads, the bore through the foot",
                  RV.render(actors([(neck, GOLD), (ped, BLUE)]), np.array([0.0, AY - 20.0, 100.0]), (0.2, -0.3, 1.0), (0, 1, 0), 90.0)))
    out_dir = os.path.join(K.check_out(), "studies")
    png = L.sheet(tiles, out_dir, "neck_mount", cols=3, header_lines=[
        "How the head attaches to the base (M8 v1, D25): his frame -> spine (4 x M3 into inserts in his nape members) -> tube -> foot",
        "(4 x M4 inserts) -> pedestal top plate (M4 x 12 from inside) -> pedestal tube -> tray (4 x M3 self-tapping). Gold: neck. Red: screws"])
    print("wrote", png)
    return 0


if __name__ == "__main__":
    sys.exit(main())

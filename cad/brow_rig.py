"""
M2 bench rig for one eyebrow (the character's left): a printed fragment of the
skull's forehead around the brow, so the brow mechanism can be run, adjusted
and tested with a silicone sample before the skull exists.

  shell     the skull wall (between the skin's inner surface and the skull's
            inner surface, SKULL_WALL thick) around the left brow, with a
            window where the pads travel
  frame     a base, the inner side wall and a ceiling the brow bracket bolts
            to (2 x M3 down into the heat-set inserts in the bracket's flange),
            hex-key holes over the two hard-stop screws, an access hole in line
            with the pivot's shoulder screw, and M3 insert holes around the
            window for the skin sample's clamp strips (M4). The outer side is
            open: it prints lying on the inner wall with no bridges, and the
            servo lead and fingers get in from there.

Built as a mesh (manifold booleans on the proxy envelopes) and written to
output/stl/brow_rig.stl in the assembled pose.

Run:  python cad/brow_rig.py
"""
import os
import sys

import manifold3d as mf
import numpy as np
import trimesh

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import cadkit as K  # noqa: E402
import browgeom as B  # noqa: E402
import head as H  # noqa: E402
import reserve as R  # noqa: E402

P = K.params()
S = P.HEAD_SCALE


def box(lo, hi):
    lo, hi = np.asarray(lo, float), np.asarray(hi, float)
    b = trimesh.creation.box(extents=hi - lo)
    b.apply_translation((lo + hi) / 2)
    return R.to_mf(b)


def cyl(r, a, b, sections=48):
    return R.to_mf(trimesh.creation.cylinder(r, segment=[np.asarray(a, float), np.asarray(b, float)],
                                             sections=sections))


def square_cut(x):
    """Half-space beyond a plane through the skin's inner surface at (x, brow line) whose
    normal runs along the face toward the temple: cuts the shell square to its surface."""
    n = B.normals(x, B.ZB)[0]
    t = np.array([n[1], -n[0], 0.0])
    t = t / np.linalg.norm(t) * (1 if n[1] > 0 else -1)
    cut = trimesh.creation.box(extents=(400.0, 400.0, 400.0))
    cut.apply_translation((200.0, 0.0, 0.0))
    cut.apply_transform(trimesh.transformations.rotation_matrix(np.arctan2(t[1], t[0]), (0, 0, 1)))
    cut.apply_translation(B.surface_point(x, B.ZB, -P.BROW_GAP))
    return R.to_mf(cut)


def window_bounds():
    """(x0, x1, z0, z1) of the left brow's window: the pads over their whole travel, plus
    BROW_RIG_WINDOW_CLEAR all round and BROW_RIG_WINDOW_OVER of overtravel at each end."""
    m = P.BROW_RIG_WINDOW_CLEAR
    wx0 = P.BROW_PADS_X[0] - P.BROW_PAD / 2 - m
    wx1 = P.BROW_PADS_X[1] + P.BROW_PAD / 2 + m
    wz0 = B.ZB - P.BROW_PAD / 2 - P.BROW_LOWER - m - P.BROW_RIG_WINDOW_OVER
    wz1 = B.ZB + P.BROW_PAD / 2 + P.BROW_RAISE + 2.0 + m + P.BROW_RIG_WINDOW_OVER   # inner pad rises ~1 more
    return wx0, wx1, wz0, wz1


def window_cut():
    """The left brow's window as a cutter (the skull uses the same one, mirrored for the right).
    Its outer side is cut square to the surface: a cut at x = const crosses the shell obliquely
    there and leaves slivers; +1.5 because the outer pad slides ~1 mm toward the temple as it
    rises (the skewed axis)."""
    wx0, wx1, wz0, wz1 = window_bounds()
    return box((wx0, -60.0, wz0), (wx1 + 40.0, 80.0, wz1)) - square_cut(wx1 + 1.5)


def rig():
    ez = B.EZ
    x0, x1 = P.BROW_RIG_X
    zb, zt = ez + P.BROW_RIG_Z[0], ez + P.BROW_RIG_Z[1]
    skin_in = R.to_mf(H.envelope(S, P.SKIN_T))
    skull_in = R.to_mf(H.envelope(S, P.SKIN_T + P.SKULL_WALL))
    region = box((x0, P.BROW_RIG_Y[0], zb), (x1, P.BROW_RIG_Y[1], zt + 2.0))
    shell = (skin_in - skull_in) ^ region
    # end the shell short of the open side with a cut square to its surface: a flat cut at
    # x = const crosses the shell at a grazing angle round the temple and leaves slivers
    shell -= square_cut(x1 - 6.0)

    wx0, wx1, wz0, wz1 = window_bounds()
    shell -= window_cut()

    # frame: base, side walls, ceiling over the bracket flange
    flange_top = float(B.to_head((0.0, 0.0, B.FLANGE_Z[1]))[2])
    t = P.BROW_RIG_T
    yb = P.BROW_RIG_Y[0]
    base = box((x0, yb, zb - t), (x1, P.BROW_RIG_Y[1], zb + 0.5))
    walls = [box((x0, yb, zb - t), (x0 + t, P.BROW_RIG_Y[1] - 18.0, flange_top + t))]
    ceiling = box((x0, yb, flange_top), (x1, P.BROW_RIG_Y[1] - 6.0, flange_top + t))
    # keep the ceiling off the skin side: trim it with the skin's inner surface
    ceiling ^= skin_in
    solid = mf.Manifold.batch_boolean([shell, base, ceiling] + walls, mf.OpType.Add)

    # bracket screws: the flange carries 2 M3 inserts (facing up); clearance holes in the ceiling
    for c in B.bracket_mounts():
        solid -= cyl(P.M3_CLEAR / 2, c - [0, 0, 1.0], c + [0, 0, t + 1.0])
    # hex-key access to the two hard-stop set screws
    for y in P.BROW_STOPS_Y:
        c = B.to_head((B.HORN_X, y, B.FLANGE_Z[1]))
        solid -= cyl(P.HEX_KEY_D / 2 + 0.5, c - [0, 0, 1.0], c + [0, 0, t + 1.0])
    # screwdriver access to the shoulder screw, in line with the pivot axis
    a = B.PIVOT + B.AXIS * ((x0 - 5.0 - B.PIVOT[0]) / B.AXIS[0])
    b = B.PIVOT + B.AXIS * ((x0 + t + 5.0 - B.PIVOT[0]) / B.AXIS[0])
    solid -= cyl(P.BROW_RIG_ACCESS_D / 2, a, b)
    # clamp-strip inserts (M3) above and below the window: the shell is only SKULL_WALL thick,
    # so each insert gets a boss behind it (insert hole + INSERT_WALL all round, 1 deeper than it)
    depth = P.INSERT_HOLE_DEPTH
    clamp = [(x, z) for x in (wx0 + 4.0, (wx0 + wx1) / 2, wx1 - 4.0) for z in (wz0 - 5.0, wz1 + 5.0)]
    for x, z in clamp:
        p = B.surface_point(x, z, -P.BROW_GAP)                        # on the skin's inner surface
        n = B.normals(x, z)[0]
        solid += cyl(P.INSERT_BOSS_D / 2, p - 0.5 * n, p - (depth + 1.0) * n)
    for x, z in clamp:
        p = B.surface_point(x, z, -P.BROW_GAP)
        n = B.normals(x, z)[0]
        solid -= cyl(P.M3_INSERT_HOLE / 2, p + 0.5 * n, p - depth * n)
    return solid


def main():
    m = R.from_mf(rig())
    m.merge_vertices()
    m.update_faces(m.nondegenerate_faces())
    m.remove_unreferenced_vertices()
    out = K.stl_dir()
    os.makedirs(out, exist_ok=True)
    path = os.path.join(out, "brow_rig.stl")
    m.export(path)
    ok = bool(m.is_watertight) and m.body_count == 1
    e = m.extents
    print(f"wrote brow_rig.stl  {e[0]:.1f} x {e[1]:.1f} x {e[2]:.1f} mm  watertight={m.is_watertight} "
          f"bodies={m.body_count}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())

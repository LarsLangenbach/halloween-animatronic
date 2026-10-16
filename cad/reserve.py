"""
Reserved space: placeholder volumes that later milestones design inside, so
the layout keeps room for them. They are not parts and never get printed.

  brow_L, brow_R  the brow mechanisms (M2), one per side: a servo bay above
                  the EyeMech plus a carrier band in front of it reaching down
                  to the brow line, both trimmed by the skin's inner surface
  cable           the channel every servo lead takes to the neck (M3): a tube
                  of CABLE_D along CABLE_PATH

Writes output/ref/reserve/<name>.stl (watertight) at HEAD_SCALE; pose_sweep.py
checks them against every part at every pose.

Run:  python cad/reserve.py
"""
import os
import sys

import manifold3d as mf
import numpy as np
import trimesh

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import cadkit as K  # noqa: E402
import geom as G  # noqa: E402
import head as H  # noqa: E402

P = K.params()


def to_mf(mesh):
    return mf.Manifold(mf.Mesh(vert_properties=np.asarray(mesh.vertices, np.float32),
                               tri_verts=np.asarray(mesh.faces, np.uint32)))


def from_mf(man):
    m = man.to_mesh()
    return trimesh.Trimesh(np.asarray(m.vert_properties)[:, :3], np.asarray(m.tri_verts), process=True)


def box(xs, ys, zs):
    lo, hi = np.array([xs[0], ys[0], zs[0]]), np.array([xs[1], ys[1], zs[1]])
    b = trimesh.creation.box(extents=hi - lo)
    b.apply_translation((lo + hi) / 2)
    return to_mf(b)


def brow(side, skin_inner):
    """side +1 = the character's left (+x), -1 = right."""
    ez = G.eye_z(P.HEAD_SCALE)
    x0, x1 = P.BROW_X
    xs = (x0, x1) if side > 0 else (-x1, -x0)
    bay = box(xs, P.BROW_BAY_Y, (ez + P.BROW_BAY_Z[0], ez + P.BROW_BAY_Z[1]))
    band = box(xs, (P.BROW_BAND_Y_MIN, P.BROW_BAY_Y[1]), (ez + P.BROW_BAND_Z[0], ez + P.BROW_BAND_Z[1]))
    return (bay + band) ^ skin_inner


def cable():
    r = P.CABLE_D / 2
    pts = [np.array(p, float) for p in P.CABLE_PATH]
    pieces = [to_mf(trimesh.creation.cylinder(r, segment=[a, b], sections=48)) for a, b in zip(pts, pts[1:])]
    for p in pts[1:-1]:
        s = trimesh.creation.icosphere(subdivisions=3, radius=r)
        s.apply_translation(p)
        pieces.append(to_mf(s))
    return mf.Manifold.batch_boolean(pieces, mf.OpType.Add)


def volumes():
    skin_inner = to_mf(H.envelope(P.HEAD_SCALE, P.SKIN_T))
    return {"brow_L": brow(+1, skin_inner), "brow_R": brow(-1, skin_inner), "cable": cable()}


def main():
    out = os.path.join(G.ref_dir(), "reserve")
    os.makedirs(out, exist_ok=True)
    ok = True
    for name, man in volumes().items():
        m = from_mf(man)
        good = bool(m.is_watertight) and m.volume > 0
        ok &= good
        m.export(os.path.join(out, name + ".stl"))
        lo, hi = m.bounds
        print(f"{'' if good else 'FAIL  '}{name}: x {lo[0]:.1f}..{hi[0]:.1f} y {lo[1]:.1f}..{hi[1]:.1f} "
              f"z {lo[2]:.1f}..{hi[2]:.1f}, volume {m.volume / 1000:.1f} cm3, watertight={m.is_watertight}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())

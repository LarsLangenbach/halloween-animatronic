"""
The proxy head: a ruled loft through densely interpolated sections
(geom.sections), standing in for the sculpt until M5. It gives three nested
envelopes, as watertight meshes:

  head_outer   the outer skin surface
  skin_inner   head_outer moved in by SKIN_T: the silicone's inner surface
  skull_inner  head_outer moved in by SKIN_T + SKULL_WALL: the space inside the skull

The inner envelopes are true offsets: every vertex of the outer surface moves
inward along its normal (exact wherever the surface's radius of curvature is
larger than the offset, i.e. everywhere but tight concave corners such as under
the chin). The outer surface is first extended below the neck base and the
offsets are cut flat at z = 0, so the neck stays open at the base. The first
version shrank each horizontal section instead, which made the skin as thin
as 1.4 mm where the head leans (review 2026-10-15).

envelopes(scale) builds them at any head scale (layout_check compares several);
running the file writes them at HEAD_SCALE to output/ref/ as reference meshes.
They are not print files.

Run:  python cad/head.py
"""
import functools
import os
import sys

import numpy as np
import trimesh

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import cadkit as K  # noqa: E402
import geom as G  # noqa: E402

P = K.params()
INSETS = {"head_outer": 0.0, "skin_inner": P.SKIN_T, "skull_inner": P.SKIN_T + P.SKULL_WALL}
NECK_EXT = 30.0          # mm the outer surface is extended below z = 0 before offsetting


def loft(scale, ext=0.0):
    """B-rep ruled loft of the outer surface; `ext` mm of extra neck below z = 0."""
    from build123d import Solid, Spline, Wire
    secs = G.sections(scale, 0.0)
    if ext:
        secs = [(secs[0][0] - ext, secs[0][1])] + secs
    wires = [Wire([Spline(*[(x, y, z) for x, y in pts], periodic=True)]) for z, pts in secs]
    return Solid.make_loft(wires, ruled=True)


def to_mesh(shape, tol=0.1, ang=0.1):
    verts, tris = shape.tessellate(tol, ang)
    m = trimesh.Trimesh(np.array([(v.X, v.Y, v.Z) for v in verts]), np.array(tris), process=True)
    m.merge_vertices()
    m.update_faces(m.nondegenerate_faces())
    m.remove_unreferenced_vertices()
    if m.volume < 0:
        m.invert()
    return m


@functools.lru_cache(maxsize=16)
def _envelope(scale, inset):
    import manifold3d as mf
    if inset == 0.0:
        return to_mesh(loft(scale))
    m = to_mesh(loft(scale, NECK_EXT))
    m.vertices = m.vertices - inset * m.vertex_normals
    man = mf.Manifold(mf.Mesh(vert_properties=np.asarray(m.vertices, np.float32),
                              tri_verts=np.asarray(m.faces, np.uint32)))
    lo, hi = m.bounds
    keep = trimesh.creation.box(bounds=[[lo[0] - 10, lo[1] - 10, 0.0], [hi[0] + 10, hi[1] + 10, hi[2] + 10]])
    man = man ^ mf.Manifold(mf.Mesh(vert_properties=np.asarray(keep.vertices, np.float32),
                                    tri_verts=np.asarray(keep.faces, np.uint32)))
    out = man.to_mesh()
    r = trimesh.Trimesh(np.asarray(out.vert_properties)[:, :3], np.asarray(out.tri_verts), process=True)
    if r.volume < 0:
        r.invert()
    return r


def envelope(scale, inset):
    """Watertight mesh of the envelope `inset` mm inside the outer skin (a copy: safe to modify)."""
    return _envelope(float(scale), float(inset)).copy()


def envelopes(scale):
    return {name: envelope(scale, inset) for name, inset in INSETS.items()}


def margin_min(points, scale, inset, k=64):
    """Worst signed margin (mm, + = inside) of points against an envelope: screened with
    geom.envelope_margin, then the k worst measured exactly against the mesh."""
    pts = np.asarray(points, float)
    rough = G.envelope_margin(pts, scale, inset)
    cand = pts[np.argsort(rough)[:k]]
    return float(trimesh.proximity.signed_distance(_envelope(float(scale), float(inset)), cand).min())


def main():
    out = G.ref_dir()
    os.makedirs(out, exist_ok=True)
    ok = True
    for name, m in envelopes(P.HEAD_SCALE).items():
        good = bool(m.is_watertight) and m.volume > 0
        ok &= good
        m.export(os.path.join(out, name + ".stl"))
        e = m.extents
        print(f"{'' if good else 'FAIL  '}{name}: {e[0]:.1f} x {e[1]:.1f} x {e[2]:.1f} mm, "
              f"volume {m.volume / 1000:.0f} cm3, watertight={m.is_watertight}")
    s = P.HEAD_SCALE
    st = G.stomion(s)
    print(f"scale {s}: eye line z {G.eye_z(s):.1f}, stomion y {st[1]:.1f} z {st[2]:.1f}, "
          f"chin z {G.z_abs(P.CHIN_Z_1X, s):.1f}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())

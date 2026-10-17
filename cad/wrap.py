"""
Shrink-wrap meshes into one smooth closed surface (for the sculpt base, D17).

  occupancy(meshes, lo, h)     voxels (spacing h, corner lo) the meshes' surfaces pass through
  closed_solid(occ, h, r)      morphological closing by r, filled: a ball of radius r can't
                               reach into any gap narrower than about 2 r, so the gaps between
                               parts are bridged and the inside is solid
  signed_distance(solid, h)    distance to the solid's surface, negative inside
  surface_nets(F, lo, h, lvl)  the surface F = lvl as a triangle mesh (inside: F < lvl)

Surface nets: one vertex per cell the surface crosses, at the mean of its edge crossings,
and one quad per grid edge the surface crosses. Written here so the project needs no
marching-cubes package.

Not in the pipeline: helpers for sculpt_base.py.
"""
import numpy as np
import trimesh
from scipy import ndimage

CORNERS = np.array([(i, j, k) for i in (0, 1) for j in (0, 1) for k in (0, 1)])
EDGES = [(a, b) for a in range(8) for b in range(a + 1, 8) if np.abs(CORNERS[a] - CORNERS[b]).sum() == 1]


def occupancy(meshes, lo, shape, h, per_mm2=None):
    """Voxels the meshes' surfaces pass through (sampled at least 4 points per voxel face)."""
    occ = np.zeros(shape, bool)
    dens = per_mm2 or 4.0 / h ** 2
    for m in meshes:
        n = int(max(500, m.area * dens))
        p = trimesh.sample.sample_surface(m, n, seed=7)[0]
        p = np.vstack([p, m.vertices])
        ijk = np.floor((p - lo) / h).astype(np.int64)
        ok = np.all((ijk >= 0) & (ijk < np.array(shape)), axis=1)
        ijk = ijk[ok]
        occ[ijk[:, 0], ijk[:, 1], ijk[:, 2]] = True
    return occ


def closed_solid(occ, h, r):
    """Close the occupied voxels by radius r (dilate, fill the inside, erode)."""
    near = ndimage.distance_transform_edt(~occ) * h <= r
    solid = ndimage.binary_fill_holes(near)
    return ndimage.distance_transform_edt(solid) * h > r


def signed_distance(solid, h):
    out = ndimage.distance_transform_edt(~solid) * h
    inn = ndimage.distance_transform_edt(solid) * h
    return (out - inn).astype(np.float32)


def surface_nets(F, lo, h, level=0.0):
    """Triangle mesh of the surface F = level on a grid (corner lo, spacing h); outward normals."""
    s = (F - level).astype(np.float32)
    nx, ny, nz = s.shape
    c = np.stack([s[i:nx - 1 + i, j:ny - 1 + j, k:nz - 1 + k] for i, j, k in CORNERS], axis=-1)   # cells x 8
    neg = c < 0
    active = neg.any(axis=-1) & ~neg.all(axis=-1)
    cells = np.argwhere(active)
    cv = c[active]                                                    # (m, 8)
    acc = np.zeros((len(cells), 3))
    cnt = np.zeros(len(cells))
    for a, b in EDGES:
        sa, sb = cv[:, a], cv[:, b]
        x = (sa < 0) != (sb < 0)
        t = np.where(x, sa / np.where(x, sa - sb, 1.0), 0.0)
        p = CORNERS[a] + t[:, None] * (CORNERS[b] - CORNERS[a])
        acc[x] += p[x]
        cnt[x] += 1
    verts = lo + (cells + acc / cnt[:, None]) * h
    vid = -np.ones(active.shape, np.int64)
    vid[tuple(cells.T)] = np.arange(len(cells))
    faces = []
    for ax in range(3):
        b1, b2 = [d for d in range(3) if d != ax]
        sl0 = [slice(None)] * 3
        sl1 = [slice(None)] * 3
        sl0[ax] = slice(0, -1)
        sl1[ax] = slice(1, None)
        s0, s1 = s[tuple(sl0)], s[tuple(sl1)]
        cross = (s0 < 0) != (s1 < 0)
        # an edge from grid point g to g + e_ax: its 4 cells are g - (0/1) e_b1 - (0/1) e_b2
        g = np.argwhere(cross)
        keep = (g[:, b1] >= 1) & (g[:, b2] >= 1) & (g[:, b1] <= s.shape[b1] - 2) & (g[:, b2] <= s.shape[b2] - 2)
        g = g[keep]
        inside_first = (s0[tuple(g.T)] < 0)
        q = []
        for d1, d2 in ((0, 0), (1, 0), (1, 1), (0, 1)):
            cc = g.copy()
            cc[:, b1] -= d1
            cc[:, b2] -= d2
            q.append(vid[tuple(cc.T)])
        q = np.stack(q, axis=1)
        # the loop runs one way round b1 x b2, which is +ax for x and z and -ax for y; every
        # face must point the same way through the surface (the overall sign is fixed below)
        flip = inside_first if ax in (0, 2) else ~inside_first
        q[flip] = q[flip][:, ::-1]
        faces.append(np.vstack([q[:, [0, 1, 2]], q[:, [0, 2, 3]]]))
    m = trimesh.Trimesh(verts, np.vstack(faces), process=True)
    if m.volume < 0:
        m.invert()
    return m

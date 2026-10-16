"""
Shared geometry that builders and checks both read, so they can never
disagree: the proxy head's sections, landmark positions, and where each
Will Cogley module sits for a given head scale.

Everything here is a pure function of params.py and a head scale, so a check
can evaluate other scales (decision D4) without rebuilding anything.
"""
import functools
import math
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import cadkit as K  # noqa: E402

P = K.params()


# ---------------------------------------------------------------------------
# landmarks
# ---------------------------------------------------------------------------
def eye_z(scale):
    """Height of the eye line above the base interface (z = 0)."""
    return -P.NECK_BASE_Z_1X * scale


def z_abs(z_1x, scale):
    """A height given relative to the eye line at scale 1.0 -> frame z."""
    return eye_z(scale) + z_1x * scale


def head_rows():
    """Proxy section rows bottom to top, with the base section added at the neck base."""
    rows = sorted(P.HEAD_SECTIONS_1X, key=lambda r: r[0])
    return [(P.NECK_BASE_Z_1X,) + tuple(rows[0][1:])] + rows


@functools.lru_cache(maxsize=1)
def row_fit():
    """PCHIP fit of the section rows over height (scale 1.0, z from the eye line).
    The loft, the margins and the landmarks all read the head through this one fit
    (built once per run: params don't change inside a run)."""
    from scipy.interpolate import PchipInterpolator
    rows = np.array(head_rows())
    return PchipInterpolator(rows[:, 0], rows[:, 1:], axis=0, extrapolate=False)


def face_front_y(z_1x, scale):
    """Front of the proxy face at the midline, at a height relative to the eye line."""
    return float(row_fit()(z_1x)[1]) * scale


def stomion(scale):
    """The lip line on the skin surface: (0, y, z)."""
    return np.array([0.0, face_front_y(P.STOMION_DZ_1X, scale), z_abs(P.STOMION_DZ_1X, scale)])


# ---------------------------------------------------------------------------
# proxy head sections
# ---------------------------------------------------------------------------
def section_points(w, yf, yc, yb, n, count=48):
    """Closed outline of one horizontal section, counter-clockwise from +x.
    The front half (y >= yc) is a superellipse with exponent n, so the face
    reads flatter than an ellipse; the back half is an ellipse."""
    pts = []
    for t in np.linspace(0.0, 2 * math.pi, count, endpoint=False):
        c, s = math.cos(t), math.sin(t)
        if s >= 0:                                    # front half
            e = 2.0 / n
            x = w * math.copysign(abs(c) ** e, c)
            y = yc + (yf - yc) * abs(s) ** e
        else:                                         # back half
            x = w * c
            y = yc + (yc - yb) * s
        pts.append((x, y))
    return pts


def sections(scale, inset=0.0, step_1x=4.0):
    """[(z, [(x, y), ...])] of the proxy head, bottom to top, shrunk inward by
    `inset` mm.

    The rows in params.py are interpolated in height with PCHIP (monotone, so
    it never overshoots between rows) into sections about `step_1x` apart;
    joined by a ruled loft these read as a smooth surface. A smooth loft
    through the sparse rows overshot by 150 mm at the chin-to-neck step.

    Shrinking each section's half-width, front and back by `inset` (and
    lowering the crown by it) approximates a true offset surface; it is exact
    where the surface is vertical and errs by up to inset*(1-cos a) where it
    leans by a. Good enough for a proxy that the sculpt replaces in M5."""
    rows = np.array(head_rows())
    z_1x = rows[:, 0]
    fit = row_fit()
    count = int(math.ceil((z_1x[-1] - z_1x[0]) / step_1x)) + 1
    zs = np.linspace(z_1x[0], z_1x[-1], count)
    crown = z_abs(z_1x[-1], scale) - inset            # the crown moves down by the inset
    out = []
    for i, z in enumerate(zs):
        top = i == len(zs) - 1
        if not top and z_abs(z, scale) >= crown - 0.5:
            continue                                  # would sit above the lowered crown
        w, yf, yc, yb, n = fit(z)
        out.append((float(crown if top else z_abs(z, scale)),
                    section_points(w * scale - inset, yf * scale - inset, yc * scale,
                                   yb * scale + inset, n)))
    return out


def _front_y_outer(x, z, scale):
    """y of the outer skin's front surface at (x, z); NaN beyond the section's half-width."""
    x, z = np.broadcast_arrays(np.asarray(x, float), np.asarray(z, float))
    w, yf, yc, yb, n = row_fit()(np.clip((z - eye_z(scale)) / scale, head_rows()[0][0],
                                         head_rows()[-1][0])).T
    w, yf, yc = w * scale, yf * scale, yc * scale
    c = np.clip(np.abs(x) / w, 0, None)
    with np.errstate(invalid="ignore"):
        cc = np.where(c <= 1, c ** (n / 2.0), np.nan)      # |cos t|
        s = np.sqrt(1 - cc ** 2)
        return yc + (yf - yc) * s ** (2.0 / n)


def _outer_normal(x, z, scale, h=0.25):
    dydx = (_front_y_outer(x + h, z, scale) - _front_y_outer(x - h, z, scale)) / (2 * h)
    dydz = (_front_y_outer(x, z + h, scale) - _front_y_outer(x, z - h, scale)) / (2 * h)
    nrm = np.sqrt(dydx ** 2 + 1 + dydz ** 2)
    return -dydx / nrm, 1 / nrm, -dydz / nrm


def front_y(x, z, scale, inset=0.0):
    """y of the proxy envelope's front surface (the face side) at (x, z), `inset`
    mm inside the outer skin. The inner envelopes are true offsets (head.py), so
    this finds the outer point whose inward normal, `inset` long, lands on (x, z)
    (fixed-point, 3 rounds) and returns that point's y. NaN beyond the section's
    half-width."""
    x, z = np.broadcast_arrays(np.asarray(x, float), np.asarray(z, float))
    if inset == 0.0:
        return _front_y_outer(x, z, scale)
    xo, zo = x.copy(), z.copy()
    for _ in range(3):
        nx, ny, nz = _outer_normal(xo, zo, scale)
        xo, zo = x + inset * nx, z + inset * nz
    nx, ny, nz = _outer_normal(xo, zo, scale)
    return _front_y_outer(xo, zo, scale) - inset * ny


def envelope_margin(points, scale, inset):
    """Signed margin (mm, + = inside) of points against the proxy envelope
    `inset` mm inside the outer skin, from the same section formula the loft
    is built from (no mesh queries, so it is fast). It is the 2D distance to
    the outer section outline at the point's height, capped by the vertical
    distance to the crown, minus the inset, and capped at the base z = 0.
    Where the surface leans (crown, under the chin) the 2D distance overstates
    the true 3D clearance, so callers use it to screen points and measure the
    worst ones exactly (head.margin_min)."""
    pts = np.asarray(points, float)
    rows = np.array(head_rows())
    z_1x = (pts[:, 2] - eye_z(scale)) / scale
    fit = row_fit()
    zc = np.clip(z_1x, rows[0, 0], rows[-1, 0])
    w, yf, yc, yb, n = fit(zc).T
    # the inner envelopes are true offsets of the outer skin (head.py), so the margin to one
    # is the margin to the outer skin minus the inset
    w, yf, yb = w * scale, yf * scale, yb * scale
    yc = yc * scale
    t = np.linspace(0.0, 2 * math.pi, 96, endpoint=False)
    c, s_ = np.cos(t)[None, :], np.sin(t)[None, :]
    e = (2.0 / n)[:, None]
    front = s_ >= 0
    x = np.where(front, w[:, None] * np.sign(c) * np.abs(c) ** e, w[:, None] * c)
    y = np.where(front, yc[:, None] + (yf - yc)[:, None] * np.abs(s_) ** e,
                 yc[:, None] + (yc - yb)[:, None] * s_)
    # distance from each point to its own outline (closed polyline)
    ax, ay = x, y
    bx, by = np.roll(x, -1, axis=1), np.roll(y, -1, axis=1)
    px, py = pts[:, 0:1], pts[:, 1:2]
    dx, dy = bx - ax, by - ay
    tt = np.clip(((px - ax) * dx + (py - ay) * dy) / np.maximum(dx * dx + dy * dy, 1e-12), 0, 1)
    d = np.hypot(ax + tt * dx - px, ay + tt * dy - py).min(axis=1)
    # inside test: even-odd ray crossing along +x
    cross = ((ay > py) != (by > py)) & (px < ax + (py - ay) * dx / np.where(dy == 0, 1e-12, dy))
    inside = cross.sum(axis=1) % 2 == 1
    margin = np.where(inside, d, -d)
    crown = z_abs(rows[-1, 0], scale)
    margin = np.minimum(margin, crown - pts[:, 2])
    margin = margin - inset
    margin = np.minimum(margin, pts[:, 2] - 0.0)                      # the neck is cut flat at z = 0
    return margin


# ---------------------------------------------------------------------------
# module placement: rotate about z, then translate
# ---------------------------------------------------------------------------
def rot_z(v, deg):
    a = math.radians(deg)
    c, s = math.cos(a), math.sin(a)
    x, y, z = v
    return np.array([c * x - s * y, s * x + c * y, z])


def module_rot(name):
    return {"eyemech": P.EYEMECH_ROT_Z, "mouth": P.MOUTH_ROT_Z}[name]


def module_translation(name, scale):
    """Translation that puts a module's datum on its target after the rotation.
    eyemech: both eye centres on y = 0 at the eye line (x stays +-EYE_SPACING/2).
    mouth:   the lip plates' front LIP_SKIN_T behind the skin at the lip line."""
    if name == "eyemech":
        src = rot_z(P.EYEMECH_EYE_SRC, P.EYEMECH_ROT_Z)
        return np.array([0.0, -src[1], eye_z(scale) - src[2]])
    if name == "mouth":
        src = rot_z(P.MOUTH_STOMION_SRC, P.MOUTH_ROT_Z)
        target = stomion(scale) - np.array([0.0, P.LIP_SKIN_T, 0.0])
        return target - src
    raise KeyError(name)


def module_matrix(name, scale):
    """4x4 transform from the module's STEP frame to the head frame."""
    a = math.radians(module_rot(name))
    m = np.eye(4)
    m[:2, :2] = [[math.cos(a), -math.sin(a)], [math.sin(a), math.cos(a)]]
    m[:3, 3] = module_translation(name, scale)
    return m


def jaw_axis(scale):
    """(y, z) of the jaw pivot axis (parallel to x) in the head frame."""
    y, z = P.MOUTH_JAW_AXIS_SRC
    p = rot_z((0.0, y, z), P.MOUTH_ROT_Z) + module_translation("mouth", scale)
    return float(p[1]), float(p[2])


# ---------------------------------------------------------------------------
# reference meshes (Cogley modules, proxy head): not print files
# ---------------------------------------------------------------------------
def ref_dir():
    """Where builders write reference meshes: output/ref under the current run's root."""
    return os.path.join(K.root(), "output", "ref")

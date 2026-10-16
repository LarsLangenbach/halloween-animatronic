"""
Brow mechanism geometry shared by the concept study, the builder (brow.py)
and its check (brow_check.py), so they can never disagree: the carrier
surface under the skin, the pivot and its axis, the mechanism's local frame,
and the four-bar that drives the carrier.

Everything is for the character's LEFT brow (+x); the right one is its mirror
image in x (mirror()).

Local frame at the pivot (the head frame turned BROW_PIVOT_SKEW about z):
  x'  along the pivot axis, outboard
  y'  forward, toward the face
  z'  up
A carrier rotation of +theta about x' raises the brow (front points go up).

Four-bar, in the plane x' = LINK_X (all angles in the y'z' plane):
  rocker  the carrier's lever, pivot at the origin, ball at (-ROCKER_R, 0) at rest
  coupler the pushrod, COUPLER_L long, vertical at rest
  crank   the servo horn, shaft at SERVO_AXIS, ball at SERVO_AXIS + (-CRANK_R, 0) at rest
"""
import math
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import cadkit as K  # noqa: E402
import geom as G  # noqa: E402

P = K.params()
S = P.HEAD_SCALE
EZ = G.eye_z(S)
ZB = EZ + P.BROW_LINE_Z                   # brow line height
INSET = P.SKIN_T + P.BROW_GAP             # pad faces below the outer skin
XM = (P.BROW_INNER_X + P.BROW_OUTER_X) / 2

# x' planes of the drive, inboard to outboard (see brow.py for the parts in them)
HUB_X = (-P.BROW_HUB_L / 2, P.BROW_HUB_L / 2)
HORN_X = 8.0                              # servo horn mid-plane (horn 2 thick: faces at 7 and 9)
LINK_X = HORN_X - 1.0 - P.BALL_STUD_H     # 3.5: pushrod plane, one ball stud off the horn's face
LEVER_X = (LINK_X - P.BALL_STUD_H - 4.0, LINK_X - P.BALL_STUD_H)   # (-4, 0): the lever plate, its
                                          # face one stud height from the pushrod plane (review fix)
TAB_X = HORN_X + P.MG90_HORN_Z            # 18.4: servo tabs' underside (the bracket plate's face)
CHEEK_X = (HUB_X[1] + P.PIVOT_PLAY, HUB_X[1] + P.PIVOT_PLAY + P.BROW_CHEEK_T)   # bracket cheek
SERVO_AXIS = np.array([-P.BROW_ROCKER_R + P.BROW_CRANK_R, P.BROW_COUPLER_L])   # (y', z'): (-9, 30)
FLANGE_Z = (56.0, 56.0 + P.BROW_FLANGE_T)    # z' of the bracket's top flange


# ---------------------------------------------------------------------------
# the skin side
# ---------------------------------------------------------------------------
def carrier_y(x, z):
    return G.front_y(x, z, S, INSET)


def normals(x, z, h=0.5):
    """Outward unit normals of the pad-face surface at points (x, z)."""
    x, z = np.atleast_1d(x).astype(float), np.atleast_1d(z).astype(float)
    dydx = (carrier_y(x + h, z) - carrier_y(x - h, z)) / (2 * h)
    dydz = (carrier_y(x, z + h) - carrier_y(x, z - h)) / (2 * h)
    n = np.column_stack([-dydx, np.ones_like(dydx), -dydz])
    return n / np.linalg.norm(n, axis=1, keepdims=True)


def surface_point(x, z, depth=0.0):
    """Point on the pad-face surface at (x, z), moved `depth` mm inward."""
    p = np.array([x, float(carrier_y(x, z)), z])
    return p - depth * normals(x, z)[0]


# ---------------------------------------------------------------------------
# pivot, axis, local frame
# ---------------------------------------------------------------------------
def pivot_for(r, offset, beta_deg):
    """Pivot r behind mid-brow along the normal, moved `offset` up the face;
    axis turned beta in plan. Returns (pivot, axis)."""
    ref = surface_point(XM, ZB)
    n = normals(XM, ZB)[0]
    up = np.cross(np.array([1.0, 0.0, 0.0]), n)
    up /= np.linalg.norm(up)
    b = math.radians(beta_deg)
    return ref - r * n + offset * up, np.array([math.cos(b), math.sin(b), 0.0])


PIVOT, AXIS = pivot_for(P.BROW_PIVOT_R, P.BROW_PIVOT_OFFSET, P.BROW_PIVOT_SKEW)
FWD = np.cross(np.array([0.0, 0.0, 1.0]), AXIS)   # y': forward
UP = np.array([0.0, 0.0, 1.0])                    # z'
FRAME = np.column_stack([AXIS, FWD, UP])          # local -> head rotation (columns x', y', z')


def to_head(local):
    return PIVOT + np.asarray(local, float) @ FRAME.T


def to_local(head):
    return (np.asarray(head, float) - PIVOT) @ FRAME


def rotate(pts, origin, axis, angle):
    axis = axis / np.linalg.norm(axis)
    p = np.asarray(pts, float) - origin
    c, s = math.cos(angle), math.sin(angle)
    return origin + p * c + np.cross(axis, p) * s + np.outer(p @ axis, axis) * (1 - c)


def carrier_tf(theta):
    """4x4 head-frame transform of the carrier turned theta (rad) about the pivot axis."""
    import trimesh
    return trimesh.transformations.rotation_matrix(theta, AXIS, PIVOT)


def mid_radius():
    d = surface_point(XM, ZB) - PIVOT
    return float(np.linalg.norm(d - (d @ AXIS) * AXIS))


def theta_for(travel):
    """Carrier rotation (rad) that moves mid-brow `travel` mm along its arc."""
    return travel / mid_radius()


THETA_RAISE = theta_for(P.BROW_RAISE)
THETA_LOWER = -theta_for(P.BROW_LOWER)


# ---------------------------------------------------------------------------
# four-bar
# ---------------------------------------------------------------------------
def rocker_ball(theta):
    c, s = math.cos(theta), math.sin(theta)
    y, z = -P.BROW_ROCKER_R, 0.0
    return np.array([y * c - z * s, y * s + z * c])


def crank_angle(theta):
    """Servo horn rotation (rad, same sense as theta) that keeps the pushrod at
    COUPLER_L for a carrier rotation theta; the branch nearest the rest pose."""
    b = rocker_ball(theta)
    best = None
    for psi in np.linspace(-1.5, 1.5, 3001):
        c, s = math.cos(psi), math.sin(psi)
        tip = SERVO_AXIS + np.array([-P.BROW_CRANK_R * c, -P.BROW_CRANK_R * s])
        err = abs(np.linalg.norm(tip - b) - P.BROW_COUPLER_L)
        if best is None or err < best[0]:
            best = (err, psi)
    return best[1]


def crank_ball(psi):
    return SERVO_AXIS + np.array([-P.BROW_CRANK_R * math.cos(psi), -P.BROW_CRANK_R * math.sin(psi)])


def transmission_angle(theta):
    """Angle between the pushrod and the rocker lever (90 deg is ideal), degrees."""
    b = rocker_ball(theta)
    t = crank_ball(crank_angle(theta))
    rod, lever = t - b, b
    cosang = abs(rod @ lever) / (np.linalg.norm(rod) * np.linalg.norm(lever))
    return math.degrees(math.acos(min(1.0, cosang)))


def bracket_mounts():
    """Head-frame points on the flange's top face where the 2 M3 inserts are (left brow)."""
    return [to_head((x, y, FLANGE_Z[1])) for x, y in P.BROW_MOUNTS]


def stop_tips():
    """z' of the two stop screws' tips, set BROW_STOP_MARGIN past the travel ends:
    (raise stop over the front arm at y' BROW_STOPS_Y[0], lower stop over the back arm)."""
    half = P.HORN_ARM_W / 2
    sy, sz = SERVO_AXIS
    out = []
    for y, theta in zip(P.BROW_STOPS_Y, (THETA_RAISE, THETA_LOWER)):
        psi = crank_angle(theta)
        r = y - sy                                   # along the arm from the shaft (+ front, - back)
        top = sz + r * math.tan(psi) + half / math.cos(psi)
        out.append(top + P.BROW_STOP_MARGIN)
    return out


def mirror(pts):
    """Left-brow points -> right brow."""
    q = np.array(pts, float)
    q[..., 0] *= -1
    return q

"""
Enclosure (M8, D23-D25): a printed canister round the head, and the neck that stands the
head in it. Everything is modelled in the assembled pose in the head frame.

The canister, bottom to top (axis x 0, y ENC_AXIS_Y):
  enc_base_{F,L,B,R}   base wall quadrants (seams at 45/135/225/315): the 3 mm skin, the bottom lip
                       the tray sits on, an inward flange at the top (45 deg chamfer under it) the deck
                       ring screws to, seam tabs (M3 insert one side, clearance the other), vent slots
                       in the side walls, the speaker opening in the front, the hatch opening in the back
  enc_ring_{1..4}      deck ring quadrants (seams at 0/90/180/270): a flat annulus with the lower slit
                       for the sheet, the lip the deck disc drops into, the column's foot inserts
  enc_tray             floor tray: the power bank's rails, the speaker's saddle; 4 ears to the lip
  enc_deck             deck disc, drops into the ring; the bore and the pedestal's screw holes
  enc_pedestal         the collar under the neck: 4 x M4 up into the neck's foot; printed upside down, solid
  enc_grille, enc_hatch  the two panels over the openings, 4 x M3 each from outside
  enc_column_{R,L}_{lower,upper}   the opaque back column, 120 deg, in 2 x 2 prints: forks at its edges
                       the sheet's ends tuck into, lap tabs under the seams (radial screws from
                       outside), a foot flange screwed down into the deck ring, a top flange screwed
                       up into the cap's slit ring, the centre rib on the left pieces
  enc_capring_{1..4}   the cap's slit ring (z 400..416), 4 quadrants: the upper slit, the column's
                       screws, the webcam lead's slot
  enc_cap_{F,L,B,R}    cap wall quadrants: skin, flanges top and bottom, seam tabs, vents, the flat
                       front band with the webcam's lens hole and its cradle
  enc_captop_{1..4}    cap top ring with the lid's recess
  enc_lid              lid disc with vent slots and a finger hole
  neck                 the neck: a foot with 4 x M4 inserts, a tube to z 70 under the jaw's swing, and a
                       hollow spine behind the jaw up into Cogley's frame's nape
Not printed, written to output/ref/enclosure/: the clear sheet (a 240 deg shell) and the boxes of
what lives in the base, for the checks and renders.

Run:  python cad/enclosure.py   -> output/stl/enc_*.stl, neck.stl, output/ref/enclosure/*.stl
"""
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import cadkit as K  # noqa: E402
import geom as G  # noqa: E402

from build123d import (Align, Axis, Box, Cone, Cylinder, Plane, Polygon, Pos, Rot,  # noqa: E402
                       export_stl, extrude, revolve)

sys.stdout.reconfigure(encoding="utf-8")
P = K.params()
C, MN = Align.CENTER, Align.MIN
EPS = 0.01
BIG = 1000.0

AY = P.ENC_AXIS_Y
R_OUT = P.ENC_R_OUT
WALL = P.ENC_WALL
R_IN = R_OUT - WALL                       # 167: the skins' inside
R_FL = R_IN - P.ENC_FLANGE + WALL         # 155: the flanges' inner radius
SLIT = (P.ENC_SHEET_R - (P.ENC_SLIT_W - P.ENC_SHEET_T) / 2,
        P.ENC_SHEET_R + P.ENC_SHEET_T + (P.ENC_SLIT_W - P.ENC_SHEET_T) / 2)   # 149.8 .. 151.2
BASE_Z0, BASE_Z1 = P.ENC_BASE_Z           # -150, -52
RING_Z1 = BASE_Z1 + P.ENC_DECK_RING[1]    # -40: the deck ring's top = the window's floor
LIP_T = P.ENC_BOTTOM_LIP[1]
TRAY_TOP = BASE_Z0 + LIP_T + P.ENC_TRAY[1]   # -134
CAP_Z0 = P.ENC_WINDOW_TOP                 # 400
CAPRING_Z1 = CAP_Z0 + P.ENC_CAP_SLIT_RING[1]   # 416
CAPWALL_Z0, CAPWALL_Z1 = P.ENC_CAP_WALL_Z      # 416, 468
CAPTOP_Z1 = CAPWALL_Z1 + P.ENC_CAP_TOP_RING[1]  # 480
COL_Z0, COL_Z1 = RING_Z1, CAP_Z0          # -40 .. 400
COL_A0 = 270.0 - P.ENC_COLUMN_DEG / 2     # 210
COL_A1 = 270.0 + P.ENC_COLUMN_DEG / 2     # 330
WALL_QUADS = {"R": (-45.0, 45.0), "F": (45.0, 135.0), "L": (135.0, 225.0), "B": (225.0, 315.0)}
RING_QUADS = {"1": (0.0, 90.0), "2": (90.0, 180.0), "3": (180.0, 270.0), "4": (270.0, 360.0)}
INS_R, INS_D = P.M3_INSERT_HOLE / 2, P.M3_INSERT_DEPTH
LEAD_SLOT_DEG = (286.0, 294.0)             # the webcam lead's slot: through the cap's slit ring and the column's top flange
CLR_R = P.M3_CLEAR / 2


# ---------------------------------------------------------------------------
# helpers, all about the axis at the origin (shifted to y = AY at the end)
# ---------------------------------------------------------------------------
def cyl(r, z0, z1, x=0.0, y=0.0):
    return Pos(x, y, z0) * Cylinder(r, z1 - z0, align=(C, C, MN))


def ring(r0, r1, z0, z1):
    return cyl(r1, z0, z1) - cyl(r0, z0 - 1, z1 + 1)


def rz_solid(pts):
    """Revolve a closed (r, z) profile about the z axis."""
    return revolve(Plane.XZ * Polygon(*pts), Axis.Z, 360)


def wedge(a0, a1, z0=-BIG, z1=BIG, R=600.0):
    n = max(2, int(abs(a1 - a0) / 10.0) + 2)
    pts = [(0.0, 0.0)] + [(R * np.cos(np.radians(a)), R * np.sin(np.radians(a))) for a in np.linspace(a0, a1, n)]
    return Pos(0, 0, z0) * extrude(Polygon(*pts), z1 - z0)


def at(r, a, z=0.0):
    return (r * np.cos(np.radians(a)), r * np.sin(np.radians(a)), z)


def vcyl(rad, r, a, z0, z1):
    x, y, _ = at(r, a)
    return cyl(rad, z0, z1, x, y)


def radial_cyl(rad, a, r0, r1, z):
    """A cylinder along the radial line at angle a, from radius r0 to r1, at height z."""
    return Pos(0, 0, z) * Rot(0, 0, a) * Rot(0, 90, 0) * Pos(0, 0, r0) * Cylinder(rad, r1 - r0, align=(C, C, MN))


def tangent_cyl(rad, r, a, z, t0, t1):
    """A cylinder along the tangent (increasing angle) through (r, a, z), from t0 to t1 along it."""
    x, y, _ = at(r, a)
    return Pos(x, y, z) * Rot(0, 0, a + 90.0) * Rot(0, 90, 0) * Pos(0, 0, t0) * Cylinder(rad, t1 - t0, align=(C, C, MN))


def tangent_box(r0, r1, a, t0, t1, z0, z1):
    """A box between radii r0..r1 across the seam line at angle a, t0..t1 along the tangent, z0..z1."""
    rc, tc = (r0 + r1) / 2, (t0 + t1) / 2
    return (Rot(0, 0, a) * Pos(rc, tc, (z0 + z1) / 2)
            * Box(r1 - r0, t1 - t0, z1 - z0))


def seam_tabs(a0, a1, z0, z1, hole_zs, r_in=None):
    """The tabs of the quadrant a0..a1: inserts on its a1 face, clearance on its a0 face."""
    r1 = R_IN + 1.0                              # the tabs bite 1 mm into the skin
    r0 = R_IN - P.ENC_TAB[0] if r_in is None else r_in
    t = P.ENC_TAB[1]
    rc = (r0 + r1) / 2
    add = tangent_box(r0, r1, a1, -t, 0.0, z0, z1) + tangent_box(r0, r1, a0, 0.0, t, z0, z1)
    cut = None
    for z in hole_zs:
        h = tangent_cyl(INS_R, rc, a1, z, -INS_D, EPS) + tangent_cyl(CLR_R, rc, a0, z, -EPS, t + EPS)
        cut = h if cut is None else cut + h
    return add, cut


def slots_arc(a_centre, zs, r0, r1):
    """Horizontal vent slots through a wall at the heights zs: a group `arc` degrees wide, in segments."""
    h, _, arc, seg, web = P.ENC_VENT
    seg_deg, web_deg = np.degrees(seg / R_OUT), np.degrees(web / R_OUT)
    n = int((arc + web_deg) // (seg_deg + web_deg))
    a_start = a_centre - (n * seg_deg + (n - 1) * web_deg) / 2
    out = None
    for z in zs:
        for i in range(n):
            a0 = a_start + i * (seg_deg + web_deg)
            s = ring(r0, r1, z - h / 2, z + h / 2) & wedge(a0, a0 + seg_deg)
            out = s if out is None else out + s
    return out


def chord_box(r_mid, w, z0, z1, a=90.0, depth=40.0):
    """A box across the skin at angle a: `w` wide along the tangent, `depth` radially about r_mid."""
    return Rot(0, 0, a) * Pos(r_mid, 0, (z0 + z1) / 2) * Box(depth, w, z1 - z0)


def quadrant_holes(angles, r, rad, z0, z1):
    out = None
    for a in angles:
        h = vcyl(rad, r, a, z0, z1)
        out = h if out is None else out + h
    return out


def flange_angles(a0, a1):
    """The two screw positions of the wall flange in the quadrant a0..a1 (20 deg in from each seam)."""
    return (a0 + 20.0, a1 - 20.0)


def in_quad(a, a0, a1):
    return a0 <= (a - a0) % 360.0 + a0 < a1


# ---------------------------------------------------------------------------
# base wall quadrants
# ---------------------------------------------------------------------------
def base_wall_full():
    lip_r = P.ENC_BOTTOM_LIP[0]
    ft = P.ENC_FLANGE_T
    prof = [(lip_r, BASE_Z0), (R_OUT, BASE_Z0), (R_OUT, BASE_Z1), (R_FL, BASE_Z1), (R_FL, BASE_Z1 - ft),
            (R_IN, BASE_Z1 - ft - P.ENC_CHAMFER * (R_IN - R_FL)), (R_IN, BASE_Z0 + LIP_T), (lip_r, BASE_Z0 + LIP_T)]
    s = rz_solid(prof)
    # vents in the side walls (0 and 180 deg)
    zs = np.arange(P.ENC_VENT_Z[0][0], P.ENC_VENT_Z[0][1], P.ENC_VENT[1])
    s -= slots_arc(0.0, zs, R_IN - 1, R_OUT + 1) + slots_arc(180.0, zs, R_IN - 1, R_OUT + 1)
    # the speaker's opening in the front, the hatch in the back
    w, h, zc = P.ENC_GRILLE_OPEN
    s -= chord_box(R_IN + WALL / 2, w, zc - h / 2, zc + h / 2, 90.0)
    w, h, zc = P.ENC_HATCH_OPEN
    s -= chord_box(R_IN + WALL / 2, w, zc - h / 2, zc + h / 2, 270.0)
    # the panels' screw inserts: radial from the skin, into the bottom lip and the top flange
    for a in (90.0, 270.0):
        for sx in (-1, 1):
            for z in P.ENC_PANEL_SCREWS[1:]:
                x = sx * P.ENC_PANEL_SCREWS[0]
                # the hole at chord position x on the skin at angle a: its own radial line
                ah = a + np.degrees(np.arcsin(x / R_OUT)) * (1 if a == 90.0 else -1)
                s -= radial_cyl(INS_R, ah, R_OUT - INS_D, R_OUT + 1, z)
    # the flange's insert holes for the deck ring, from the top
    for a0, a1 in WALL_QUADS.values():
        for a in flange_angles(a0, a1):
            s -= vcyl(INS_R, R_OUT - 8.0, a, BASE_Z1 - INS_D, BASE_Z1 + 1)
    # the tray ears' inserts in the bottom lip, at the wall seams
    for a in P.ENC_WALL_SEAMS:
        s -= vcyl(INS_R, P.ENC_TRAY_SCREW_R, a, BASE_Z0 + LIP_T - INS_D, BASE_Z0 + LIP_T + 1)
    return s


def base_walls():
    full = base_wall_full()
    out = {}
    for name, (a0, a1) in WALL_QUADS.items():
        piece = full & wedge(a0, a1)
        add, cut = seam_tabs(a0, a1, BASE_Z0 + LIP_T, BASE_Z1 - P.ENC_FLANGE_T - 6.0, (-128.0, -101.0, -74.0))
        piece = piece + add - cut
        out[f"enc_base_{name}"] = piece
    return out


# ---------------------------------------------------------------------------
# deck ring quadrants, tray, deck, pedestal
# ---------------------------------------------------------------------------
def deck_ring_full():
    r_lip, t = P.ENC_DECK_RING
    z0, z1 = BASE_Z1, RING_Z1
    rec = P.ENC_DISC_D / 2 + P.ENC_FIT
    d = P.ENC_SLIT_D[0]
    prof = [(r_lip, z0), (R_OUT, z0), (R_OUT, z1), (SLIT[1], z1), (SLIT[1], z1 - d), (SLIT[0], z1 - d), (SLIT[0], z1),
            (rec, z1), (rec, z1 - P.ENC_DISC_T), (r_lip, z1 - P.ENC_DISC_T)]
    s = rz_solid(prof)
    # screws down into the wall flanges
    for a0, a1 in WALL_QUADS.values():
        for a in flange_angles(a0, a1):
            s -= vcyl(CLR_R, R_OUT - 8.0, a, z0 - 1, z1 + 1) + vcyl(P.M3_HEAD[0] / 2, R_OUT - 8.0, a, z1 - P.M3_HEAD[1], z1 + 1)
    # the deck's screws up through the lip
    for a in P.ENC_WALL_SEAMS:
        s -= vcyl(CLR_R, 114.0, a, z0 - 1, z1 + 1)
    # the column's foot: inserts from the top
    for a in P.ENC_COLUMN_SCREWS_DEG:
        s -= vcyl(INS_R, R_OUT - 11.0, a, z1 - INS_D, z1 + 1)
    return s


def deck_rings():
    full = deck_ring_full()
    return {f"enc_ring_{n}": full & wedge(a0, a1) for n, (a0, a1) in RING_QUADS.items()}


def tray():
    d, t = P.ENC_TRAY
    z0 = BASE_Z0 + LIP_T
    s = cyl(d / 2, z0, z0 + t)
    for a in P.ENC_WALL_SEAMS:
        s -= vcyl(CLR_R, P.ENC_TRAY_SCREW_R, a, z0 - 1, z0 + t + 1)
        s -= vcyl(P.M3_HEAD[0] / 2, P.ENC_TRAY_SCREW_R, a, z0 + t - P.M3_HEAD[1], z0 + t + 1)
    # speaker saddle: two ribs across x with a round seat
    sw, st, sh, ys = P.ENC_SADDLE
    sr = P.ENC_SPEAKER[0] / 2 + 0.5
    zc = z0 + t + sr + 1.0                       # the speaker's axis
    for y in ys:
        rib = Pos(0, y, z0 + t - EPS) * Box(sw, st, sh + EPS, align=(C, C, MN))
        rib -= Pos(0, y, zc) * Rot(90, 0, 0) * Cylinder(sr, st + 2)
        s += rib
    # the bank's rails
    bx, by, _ = P.ENC_LAYOUT["bank"]
    bl, bw, _ = P.ENC_BANK
    rt, rh, shorter = P.ENC_BANK_RAIL
    for sy in (-1, 1):
        y = by + sy * (bw / 2 + 0.5 + rt / 2)
        s += Pos(bx, y, z0 + t - EPS) * Box(bl - shorter, rt, rh + EPS, align=(C, C, MN))
    return s


def deck():
    d, t = P.ENC_DISC_D - 2 * P.ENC_FIT, P.ENC_DISC_T
    z1 = RING_Z1
    s = cyl(d / 2, z1 - t, z1)
    s -= cyl(P.ENC_BORE / 2, z1 - t - 1, z1 + 1)
    for a in P.ENC_WALL_SEAMS:                   # M3 inserts from below (screws up through the ring's lip)
        s -= vcyl(INS_R, 114.0, a, z1 - t - 1, z1 - t + INS_D)
    for a in (45.0, 135.0, 225.0, 315.0):        # M3 up into the pedestal
        s -= vcyl(CLR_R, P.ENC_PEDESTAL_SCREW_R, a, z1 - t - 1, z1 + 1)
    sq = P.NECK_BOLT_SQUARE / 2
    for sx in (-1, 1):                           # reach the M4 heads in the pedestal from below
        for sy in (-1, 1):
            s -= cyl(5.0, z1 - t - 1, z1 + 1, sx * sq, sy * sq)
    return s


def pedestal():
    d0, d1, h = P.ENC_PEDESTAL
    z0 = RING_Z1
    s = Pos(0, 0, z0) * Cone(d0 / 2, d1 / 2, h, align=(C, C, MN))
    s -= cyl(P.ENC_BORE / 2, z0 - 1, z0 + h + 1)
    sq = P.NECK_BOLT_SQUARE / 2
    cb_depth = h - 12.0                          # the top plate under the bolt heads stays 12 thick
    for sx in (-1, 1):
        for sy in (-1, 1):
            x, y = sx * sq, sy * sq
            s -= cyl(P.M4_CLEAR / 2, z0 - 1, z0 + h + 1, x, y)
            s -= cyl(P.SCULPT_PLATE_CBORE[0] / 2, z0 - 1, z0 + cb_depth, x, y)
    for a in (45.0, 135.0, 225.0, 315.0):
        s -= vcyl(INS_R, P.ENC_PEDESTAL_SCREW_R, a, z0 - 1, z0 + INS_D)
    return s


# ---------------------------------------------------------------------------
# panels
# ---------------------------------------------------------------------------
def panel(a, lead_notch=False):
    w, h, zc, t = P.ENC_PANEL
    s = ring(R_OUT + P.ENC_FIT, R_OUT + P.ENC_FIT + t, zc - h / 2, zc + h / 2) & chord_box(R_OUT, w, zc - h / 2 - 1, zc + h / 2 + 1, a, 60.0)   # a fit off the skin
    if lead_notch:                               # first, and deep: cut last it dented the panel between two slots (OCC)
        nw, nh = P.ENC_PANEL_LEAD_NOTCH
        s -= chord_box(R_OUT, nw, zc - h / 2 - 20.0, zc - h / 2 + nh, a, 60.0)
    # grille slots
    for z in np.arange(zc - h / 2 + 14.0, zc + h / 2 - 12.0, P.ENC_VENT[1]):
        s -= chord_box(R_OUT, w - 26.0, z - 1.5, z + 1.5, a, 60.0)
    for sx in (-1, 1):
        for z in P.ENC_PANEL_SCREWS[1:]:
            x = sx * P.ENC_PANEL_SCREWS[0]
            ah = a + np.degrees(np.arcsin(x / R_OUT)) * (1 if a == 90.0 else -1)
            s -= radial_cyl(CLR_R, ah, R_OUT - 2, R_OUT + t + 1, z)
    return s


# ---------------------------------------------------------------------------
# the back column
# ---------------------------------------------------------------------------
def column_pieces():
    fork_deg = np.degrees((P.ENC_SHEET_TUCK + 2.0) / R_OUT)
    slot_deg = np.degrees(P.ENC_SHEET_TUCK / R_OUT)
    lap_t, lap_w = P.ENC_COLUMN_LAP
    lap_deg = np.degrees(lap_w / R_OUT)
    fl = P.ENC_COLUMN_FLANGE
    r_fl = R_IN - fl                             # 152
    r_fork = SLIT[0] - 4.0                       # 145.8: the fork reaches inside the sheet
    zs = P.ENC_COLUMN_SPLIT_Z
    skin = ring(R_IN, R_OUT, COL_Z0, COL_Z1)
    out = {}
    seam = P.ENC_COLUMN_SEAM_DEG
    for side, (a0, a1) in (("R", (COL_A0, seam)), ("L", (seam, COL_A1))):
        for level, (z0, z1) in (("lower", (COL_Z0, zs)), ("upper", (zs, COL_Z1))):
            s = skin & wedge(a0, a1, z0, z1)
            # fork at the column's outer edge: a block the sheet's end slides into
            fa = (COL_A0, COL_A0 + fork_deg) if side == "R" else (COL_A1 - fork_deg, COL_A1)
            fork = ring(r_fork, R_IN + 1.0, z0, z1) & wedge(*fa)
            sa = (COL_A0 - 1.0, COL_A0 + slot_deg) if side == "R" else (COL_A1 - slot_deg, COL_A1 + 1.0)   # open at the sheet's side
            fork -= ring(SLIT[0], SLIT[1], z0 - 1, z1 + 1) & wedge(*sa)
            s += fork
            if level == "lower":
                # foot flange, screwed down into the deck ring
                if side == "R":                                    # R's reaches under its lap tab, a fit under the L skin
                    flange = (ring(r_fl, R_IN + 1.0, COL_Z0, COL_Z0 + 6.0) & wedge(a0, seam - 0.05)
                              + ring(r_fl, R_IN - P.ENC_FIT, COL_Z0, COL_Z0 + 6.0) & wedge(seam - 0.5, seam + lap_deg + 0.05))
                else:
                    flange = ring(r_fl, R_IN + 1.0, COL_Z0, COL_Z0 + 6.0) & wedge(seam + lap_deg + 0.1, a1)
                s += flange
                for a in P.ENC_COLUMN_SCREWS_DEG:
                    if in_quad(a, a0, a1):
                        s -= vcyl(CLR_R, R_OUT - 11.0, a, COL_Z0 - 1, COL_Z0 + 7.0)
                # lap tab under the horizontal seam (the upper piece's skin sits over it), chamfered under
                la = (a0 + fork_deg + 0.1, seam - 1.05) if side == "R" else (a0 + lap_deg + 0.1, a1 - fork_deg - 0.1)   # clear of the forks and the vertical tab
                fit = P.ENC_FIT
                tab = rz_solid([(R_IN - lap_t, zs - lap_w), (R_IN + 1.0, zs - lap_w), (R_IN + 1.0, zs), (R_IN - fit, zs),
                                (R_IN - fit, zs + lap_w), (R_IN - lap_t, zs + lap_w)]) & wedge(*la)   # under the upper skin: a fit
                ch = P.ENC_CHAMFER * (lap_t + 1.5)
                tab -= rz_solid([(R_IN - lap_t - 1, zs - lap_w - 1), (R_IN - lap_t - 1, zs - lap_w - 1 + ch),
                                 (R_IN + 0.5, zs - lap_w - 1)]) & wedge(a0 - 1, a1 + 1)   # chamfer under
                s += tab
                for a in (a0 + 18.0, a1 - 18.0):                   # the upper piece's screws into it
                    s -= radial_cyl(INS_R, a, R_IN - lap_t - 1, R_IN + 1, zs + lap_w / 2)
            else:
                # the skin's screw holes into the lower piece's lap tab
                for a in (a0 + 18.0, a1 - 18.0):
                    s -= radial_cyl(CLR_R, a, R_IN - 1, R_OUT + 1, zs + lap_w / 2)
                # top flange with inserts (screwed from inside the cap, down through the slit ring)
                zb = COL_Z1 - 10.0 - P.ENC_CHAMFER * (R_IN - r_fl)           # a wedge under the flange: 51 deg from the skin
                prof = rz_solid([(r_fl, COL_Z1 - 10.0), (R_IN + 1.0, COL_Z1 - 10.0), (R_IN + 1.0, COL_Z1), (r_fl, COL_Z1)])
                prof += rz_solid([(R_IN + 1.0, zb), (R_IN + 1.0, COL_Z1 - 10.0 + 0.5), (r_fl, COL_Z1 - 10.0 + 0.5)])
                if side == "R":                                    # past the seam: a fit under the L skin
                    flange = (prof & wedge(a0, seam - 0.05)
                              + (prof - ring(R_IN - P.ENC_FIT, R_OUT + 2, COL_Z0 - 1, COL_Z1 + 1)) & wedge(seam - 0.5, seam + lap_deg + 0.05))
                else:
                    flange = prof & wedge(seam + lap_deg + 0.1, a1)
                    flange -= ring(r_fl - 2.0, R_IN - 0.5, COL_Z0 - 1, COL_Z1 + 1) & wedge(*LEAD_SLOT_DEG)   # the webcam lead drops through
                s += flange
                for a in P.ENC_COLUMN_SCREWS_DEG:
                    if in_quad(a, a0, a1):
                        s -= vcyl(INS_R, R_OUT - 11.0, a, COL_Z1 - INS_D, COL_Z1 + 1)
            if side == "R":
                # vertical lap tab past the centre seam (the left piece's skin sits over it)
                zt0 = z0 + (6.0 if level == "lower" else 0.0)
                zt1 = z1 - (10.0 if level == "upper" else 0.0)
                tab = (ring(R_IN - lap_t, R_IN + 1.0, zt0, zt1) & wedge(seam - 1.0, seam - 0.05)
                       + ring(R_IN - lap_t, R_IN - P.ENC_FIT, zt0, zt1) & wedge(seam - 0.5, seam + lap_deg))   # a fit under the L skin
                s += tab
                for z in np.linspace(zt0 + 25.0, zt1 - 25.0, 3):
                    s -= radial_cyl(INS_R, seam + lap_deg * 0.6, R_IN - lap_t - 1, R_IN + 1, z)
            else:
                zt0 = z0 + (6.0 if level == "lower" else 0.0)
                zt1 = z1 - (10.0 if level == "upper" else 0.0)
                for z in np.linspace(zt0 + 25.0, zt1 - 25.0, 3):
                    s -= radial_cyl(CLR_R, seam + lap_deg * 0.6, R_IN - 1, R_OUT + 1, z)
                rw, rp = P.ENC_COLUMN_RIB
                rib_deg = np.degrees(rw / 2 / R_OUT)
                s += ring(R_OUT - EPS, R_OUT + rp, z0, z1) & wedge(270.0 - rib_deg, 270.0 + rib_deg)
            out[f"enc_column_{side}_{level}"] = s
    return out


# ---------------------------------------------------------------------------
# the cap
# ---------------------------------------------------------------------------
def capring_full():
    r_in, t = P.ENC_CAP_SLIT_RING
    z0, z1 = CAP_Z0, CAPRING_Z1
    d = P.ENC_SLIT_D[1]
    prof = [(r_in, z0), (SLIT[0], z0), (SLIT[0], z0 + d), (SLIT[1], z0 + d), (SLIT[1], z0), (R_OUT, z0),
            (R_OUT, z1), (r_in, z1)]
    s = rz_solid(prof)
    for a in P.ENC_COLUMN_SCREWS_DEG:            # down into the column's top flange, heads counterbored from above
        s -= vcyl(CLR_R, R_OUT - 11.0, a, z0 - 1, z1 + 1) + vcyl(P.M3_HEAD[0] / 2, R_OUT - 11.0, a, z1 - 6.0, z1 + 1)
    for a0, a1 in WALL_QUADS.values():           # inserts for the cap wall's bottom flange
        for a in flange_angles(a0, a1):
            s -= vcyl(INS_R, R_OUT - 8.0, a, z1 - INS_D, z1 + 1)
    s -= ring(r_fl_cap(), R_IN - 1.0, z0 - 1, z1 + 1) & wedge(*LEAD_SLOT_DEG)   # the webcam lead's slot into the column
    return s


def r_fl_cap():
    return R_IN - P.ENC_COLUMN_FLANGE + 1.0


def cap_rings():
    full = capring_full()
    return {f"enc_capring_{n}": full & wedge(a0, a1) for n, (a0, a1) in RING_QUADS.items()}


def cap_wall_full():
    ft = P.ENC_FLANGE_T
    z0, z1 = CAPWALL_Z0, CAPWALL_Z1
    prof = [(R_FL, z0), (R_OUT, z0), (R_OUT, z1), (R_FL, z1), (R_FL, z1 - ft), (R_IN, z1 - ft - P.ENC_CHAMFER * (R_IN - R_FL)),
            (R_IN, z0 + ft), (R_FL, z0 + ft)]
    s = rz_solid(prof)
    zs = np.arange(P.ENC_VENT_Z[1][0], P.ENC_VENT_Z[1][1], P.ENC_VENT[1])
    s -= slots_arc(0.0, zs, R_IN - 1, R_OUT + 1) + slots_arc(180.0, zs, R_IN - 1, R_OUT + 1)
    # the flat front band: the skin is cut away and a flat plate set in, closed above by a 45 deg lip
    bw, bz0, bz1, setin = P.ENC_WEBCAM_BAND
    yb = R_OUT - setin                           # the plate's outer face
    s -= Pos(0, R_OUT + 5.0, (bz0 + bz1) / 2) * Box(bw, 2 * (R_OUT + 5.0 - yb) + 2 * EPS, bz1 - bz0 + 2 * EPS)
    w, h, d = P.ENC_WEBCAM
    yi = yb - WALL - P.ENC_FIT                   # the body's front face
    gy0, gy1 = yi - d - 8.0, yb - WALL                                 # up to the plate's inner face
    s -= Pos(0, (gy0 + gy1) / 2, z0 - 1.0) * Box(bw, gy1 - gy0, ft + 1.0 + EPS, align=(C, C, MN))   # a gap in the bottom flange for the body
    s += Pos(0, yb - WALL / 2, (bz0 + bz1) / 2) * Box(bw + 6.0, WALL, bz1 - bz0 + EPS) & cyl(R_OUT - EPS, bz0 - 1, bz1 + 1)
    lip = Plane.YZ * Polygon((yb - WALL, bz1 - 2.0), (R_OUT - EPS, z1), (yb - WALL, z1))   # the slope is the underside, 49 deg
    s += (Pos(-(bw + 6.0) / 2, 0, 0) * extrude(lip, bw + 6.0)) & cyl(R_OUT - EPS, bz0 - 1, z1 + 1)
    s -= Pos(0, yb - 2.0, P.ENC_WEBCAM_Z) * Rot(90, 0, 0) * Cylinder(P.ENC_WEBCAM_HOLE / 2, 2 * setin + 10.0)
    # the webcam's cradle: a 2 mm floor across the gap (joined to the plate and the flange's edges), the body on it
    # against the plate's inside, three stops standing on the floor
    s += Pos(0, (gy0 + gy1 + 1.0) / 2, z0) * Box(bw + 2.0, gy1 - gy0 + 1.0, 2.0, align=(C, C, MN))
    for sx in (-1, 1):
        s += Pos(sx * (w / 2 + P.ENC_FIT + 1.5), yi - d / 2, z0 + 2.0 - EPS) * Box(3.0, d, 22.0, align=(C, C, MN))
    s += Pos(0, yi - d - P.ENC_FIT - 1.5, z0 + 2.0 - EPS) * Box(w, 3.0, 22.0, align=(C, C, MN))
    # screws: the bottom flange down into the slit ring, the top ring down into the top flange
    for a0, a1 in WALL_QUADS.values():
        for a in flange_angles(a0, a1):
            s -= vcyl(CLR_R, R_OUT - 8.0, a, z0 - 1, z0 + ft + 1) + vcyl(P.M3_HEAD[0] / 2, R_OUT - 8.0, a, z0 + ft - P.M3_HEAD[1], z0 + ft + 1)
            s -= vcyl(INS_R, R_OUT - 8.0, a, z1 - INS_D, z1 + 1)
    return s


def cap_walls():
    full = cap_wall_full()
    out = {}
    for name, (a0, a1) in WALL_QUADS.items():
        piece = full & wedge(a0, a1)
        add, cut = seam_tabs(a0, a1, CAPWALL_Z0, CAPWALL_Z1 - P.ENC_FLANGE_T - 6.0, (432.0, 452.0))
        out[f"enc_cap_{name}"] = piece + add - cut
    return out


def captop_full():
    r_lip, t = P.ENC_CAP_TOP_RING
    z0, z1 = CAPWALL_Z1, CAPTOP_Z1
    rec = P.ENC_DISC_D / 2 + P.ENC_FIT
    prof = [(r_lip, z0), (R_OUT, z0), (R_OUT, z1), (rec, z1), (rec, z1 - P.ENC_DISC_T), (r_lip, z1 - P.ENC_DISC_T)]
    s = rz_solid(prof)
    for a0, a1 in WALL_QUADS.values():
        for a in flange_angles(a0, a1):
            s -= vcyl(CLR_R, R_OUT - 8.0, a, z0 - 1, z1 + 1) + vcyl(P.M3_HEAD[0] / 2, R_OUT - 8.0, a, z1 - P.M3_HEAD[1], z1 + 1)
    return s


def cap_tops():
    full = captop_full()
    return {f"enc_captop_{n}": full & wedge(a0, a1) for n, (a0, a1) in RING_QUADS.items()}


def lid():
    d, t = P.ENC_DISC_D - 2 * P.ENC_FIT, P.ENC_DISC_T
    z1 = CAPTOP_Z1
    s = cyl(d / 2, z1 - t, z1)
    vw, vl, vp, n = P.ENC_LID_VENTS
    for i in range(n):
        y = (i - (n - 1) / 2) * vp
        s -= Pos(0, y, z1 - t / 2) * Box(vl, vw, t + 2)
    fd, fy = P.ENC_LID_FINGER
    s -= cyl(fd / 2, z1 - t - 1, z1 + 1, 0.0, fy)
    return s


# ---------------------------------------------------------------------------
# the neck
# ---------------------------------------------------------------------------
def neck():
    od, wall, ztop = P.NECK_TUBE
    ft = P.NECK_FOOT_T
    y0, y1 = (v - AY for v in P.NECK_SPINE_Y)                        # axis coordinates
    hx = P.NECK_SPINE_X
    s = cyl(od / 2, 0.0, ft)                                         # foot...
    s += Pos(0, (y0 + y1) / 2, 0.0) * Box(2 * hx, y1 - y0, ft, align=(C, C, MN))   # ...under the whole spine
    s += ring(od / 2 - wall, od / 2, ft - EPS, ztop)                 # tube
    s -= cyl(P.ENC_BORE / 2, -1.0, ft + 1)
    sq = P.NECK_BOLT_SQUARE / 2
    for sx in (-1, 1):
        for sy in (-1, 1):
            s -= cyl(P.M4_INSERT_HOLE / 2, -1.0, P.M4_INSERT_DEPTH, sx * sq, sy * sq)
    # spine: a hollow box behind the jaw, its inside roofed at 45 deg under the top plate
    top, sw, tt = P.NECK_SPINE_TOP, P.NECK_SPINE_WALL, P.NECK_SPINE_TOP_T
    s += Pos(0, (y0 + y1) / 2, ft - EPS) * Box(2 * hx, y1 - y0, top - ft + EPS, align=(C, C, MN))
    zr = top - tt                                                    # the roof's ridge
    half = (y1 - y0) / 2 - sw
    zstep, hx2 = P.NECK_SPINE_HOLLOW_STEP
    hollow = Plane.YZ * Polygon((y0 + sw, ft), (y1 - sw, ft), (y1 - sw, zr - half),
                                ((y0 + y1) / 2, zr), (y0 + sw, zr - half))
    s -= Pos(-hx2, 0, 0) * extrude(hollow, 2 * hx2)                  # the narrow part, full height
    wx = hx - sw
    wide = Plane.XZ * Polygon((-wx, ft), (wx, ft), (wx, zstep - (wx - hx2)), (hx2, zstep), (-hx2, zstep), (-wx, zstep - (wx - hx2)))
    s -= Pos(0, y1 - sw, 0) * extrude(wide, y1 - y0 - 2 * sw)          # the wide part below the step, its corners at 45 deg
    # the opening between the spine and the tube
    jz0, jz1 = P.NECK_SPINE_JOIN_Z
    s -= Pos(0, (y0 + sw + y1 - sw) / 2 + 2.0, (jz0 + jz1) / 2) * Box(2 * (hx - sw) - 6.0, y1 - y0 - 2 * sw + 4.0, jz1 - jz0)
    # notches for the frame's two ribs that come down through the spine's footprint
    (nx0, nx1), (ny0, ny1), nz = P.NECK_SPINE_NOTCH
    for sx in (-1, 1):
        s -= Pos(sx * (nx0 + nx1) / 2, (ny0 + ny1) / 2 - AY, nz) * Box(nx1 - nx0, ny1 - ny0, top - nz + 1, align=(C, C, MN))
    # the leads' way in: an opening in the top plate, through the roof into the hollow
    ow, od, oy = P.NECK_SPINE_TOP_OPENING
    s -= Pos(0, oy - AY, top - 30.0) * Box(ow, od, 31.0, align=(C, C, MN))
    # ASSUMPTION: 4 x M3 through the top plate up into inserts in the frame's nape members
    for x, y in P.NECK_SPINE_SCREWS:
        s -= cyl(CLR_R, top - tt - 1, top + 1, x, y - AY)
    return s


# ---------------------------------------------------------------------------
# reference shapes (not printed)
# ---------------------------------------------------------------------------
def ref_parts():
    out = {}
    tuck_deg = np.degrees((P.ENC_SHEET_TUCK - 0.5) / R_OUT)      # the forks' slots are cut by angle at the skin
    out["sheet"] = ring(P.ENC_SHEET_R, P.ENC_SHEET_R + P.ENC_SHEET_T, RING_Z1 - P.ENC_SLIT_D[0],
                        CAP_Z0 + P.ENC_SLIT_D[1]) & wedge(COL_A1 - tuck_deg, COL_A0 + 360.0 + tuck_deg)   # into both forks
    zt = TRAY_TOP
    for name, (x, y, turn) in P.ENC_LAYOUT.items():
        if name == "speaker":
            dia, ln = P.ENC_SPEAKER
            out[name] = Pos(x, y, zt + dia / 2 + 1.0) * Rot(90, 0, 0) * Cylinder(dia / 2, ln)
        else:
            size = {"bank": P.ENC_BANK, "buck": P.ENC_BUCK}.get(name, P.ENC_BOARD)
            out[name] = Pos(x, y, zt + EPS) * Rot(0, 0, turn) * Box(*size, align=(C, C, MN))
    w, h, d = P.ENC_WEBCAM
    yb = R_OUT - P.ENC_WEBCAM_BAND[3]
    yi = yb - WALL - P.ENC_FIT
    out["webcam"] = Pos(0, yi - d / 2, P.ENC_WEBCAM_Z - h / 2 + 0.0) * Box(w, d, h, align=(C, C, MN))
    return out


# ---------------------------------------------------------------------------
def shift(d):
    return {n: Pos(0, AY, 0) * s for n, s in d.items()}


def parts():
    out = {}
    for fn in (base_walls, deck_rings, column_pieces, cap_rings, cap_walls, cap_tops):
        out.update(fn())
    out["enc_tray"] = tray()
    out["enc_deck"] = deck()
    out["enc_pedestal"] = pedestal()
    out["enc_grille"] = panel(90.0)
    out["enc_hatch"] = panel(270.0, lead_notch=True)
    out["enc_lid"] = lid()
    out["neck"] = neck()
    return shift(out)


def main():
    ok = True
    for name, shp in parts().items():
        if not shp.is_valid:
            print(f"FAIL  {name}: not a valid solid")
            ok = False
        if name in ("enc_grille", "enc_hatch", "enc_cap_F"):   # slotted or cut curved faces: at 0.05 the tessellation dents or opens them
            ok &= K.write_stl(shp, name, tolerance=0.01, angular_tolerance=0.05)
        else:
            ok &= K.write_stl(shp, name)
    rdir = os.path.join(G.ref_dir(), "enclosure")
    os.makedirs(rdir, exist_ok=True)
    refs = shift(ref_parts())
    for name, shp in refs.items():
        export_stl(shp, os.path.join(rdir, name + ".stl"), tolerance=0.05, angular_tolerance=0.2)
    print(f"reference shapes -> output/ref/enclosure ({len(refs)})")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())

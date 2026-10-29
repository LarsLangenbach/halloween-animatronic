"""
Enclosure (M8, D23-D26), v1: a canister round the head that prints in a day, and the neck that
stands the head in it. Everything is modelled in the assembled pose in the head frame.

Eleven prints (thin plates with ribs; the big areas are two PETG sheets):
  enc_cap_{F,B}      the cap in two halves (split on the y = 0 line): a 1.2 mm top with ribs and vent
                     slots, a 40 mm skirt, two lips under it that make the window's upper channel, the
                     flat front facet with the webcam's lens hole and its stops, seam walls (2 x M3 + nut)
  enc_top_{F,B}      the deck in two halves: a 1.6 mm plate from the pedestal out to a rim the base's
                     PETG band wraps (M3 + nut through both), the window's lower lip on top, ribs, seam
                     walls, the webcam lead's slot (B)
  enc_bottom_{F,B}   the bottom ring halves: a plate on the tray's outer rib (4 x M3 self-tapping) with
                     the band's lower rim
  enc_tray           the floor: the pedestal, the speaker's saddles, the bank's rails and the rings stand on it
  enc_pedestal       a hollow cone from the tray up to z 0, 4 x M4 up into the neck's foot; printed upside down
  enc_grille, enc_hatch  the panels over the two openings cut in the band, 4 x M3 + nut each
  neck               the neck: a foot with 4 x M4 inserts, a tube to z 70 under the jaw's swing, a hollow
                     spine behind the jaw up under Cogley's frame's nape (D25)
Not printed, written to output/ref/enclosure/: the window sheet (a full tube), the base's band, the
boxes of what lives in the base, the webcam.

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
LIP_T, LIP_H = P.ENC_LIP
LIP_RI, LIP_RO = P.ENC_LIP_R                 # inner lip's inner radius, outer lip's inner radius
RIM_T, RIM_H = P.ENC_RIM
RIM_R = P.ENC_BAND_R - RIM_T                 # 142: the rims' inner radius
PLATE_T = P.ENC_PLATE_T
RIB_T, RIB_H = P.ENC_RIB
SEAM_T, SEAM_H = P.ENC_SEAM_WALL
FIT = P.ENC_FIT
TRAY_Z0 = P.ENC_TRAY_Z
TRAY_TOP = TRAY_Z0 + P.ENC_TRAY[1]           # -147.5
RIB_TOP = TRAY_TOP + P.ENC_TRAY_RIBS[0][2]   # -141.5: the rings and the pedestal's flange stand on the tray's ribs
TOP_Z = P.ENC_TOP_Z                          # -40
CAP_Z = P.ENC_CAP_Z                          # 440
CAP_TOP = CAP_Z + P.ENC_CAP_T
CLR_R = P.M3_CLEAR / 2
HALVES = {"F": (0.0, 180.0), "B": (180.0, 360.0)}
LEAD_SLOT_DEG = 270.0


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


def ycyl(rad, x, y0, y1, z):
    """A cylinder along y at (x, z), from y0 to y1."""
    return Pos(x, y0, z) * Rot(-90, 0, 0) * Cylinder(rad, y1 - y0, align=(C, C, MN))


def chord_box(r_mid, w, z0, z1, a=90.0, depth=40.0):
    """A box across the skin at angle a: `w` wide along the tangent, `depth` radially about r_mid."""
    return Rot(0, 0, a) * Pos(r_mid, 0, (z0 + z1) / 2) * Box(depth, w, z1 - z0)


def radial_ribs(angles, r0, r1, z0, h):
    out = None
    for a in angles:
        rib = Rot(0, 0, a) * Pos((r0 + r1) / 2, 0, z0) * Box(r1 - r0, RIB_T, h, align=(C, C, MN))
        out = rib if out is None else out + rib
    return out


def seam_walls(half, x_ranges, z0, h, hole_xs, up=True):
    """Walls along the y = 0 seam on this half's side, `h` tall from z0 (up or down), with M3 holes along y."""
    sy = 1 if half == "F" else -1
    zb = z0 if up else z0 - h
    add = None
    for x0, x1 in x_ranges:
        w = Pos((x0 + x1) / 2, sy * SEAM_T / 2, zb) * Box(x1 - x0, SEAM_T, h, align=(C, C, MN))
        add = w if add is None else add + w
    cut = None
    for x in hole_xs:
        c = ycyl(CLR_R, x, -SEAM_T - 1, SEAM_T + 1, zb + h / 2)
        cut = c if cut is None else cut + c
    return add, cut


# ---------------------------------------------------------------------------
# the cap halves
# ---------------------------------------------------------------------------
def cap_full():
    s = cyl(R_OUT, CAP_Z, CAP_TOP)                                           # the top plate
    s += ring(R_OUT - P.ENC_PLATE_T, R_OUT, P.ENC_WINDOW_TOP, CAP_Z + EPS)      # the skirt (1.6)
    s += ring(LIP_RI, LIP_RI + LIP_T, CAP_Z - LIP_H, CAP_Z + EPS)               # the channel's lips, hanging
    s += ring(LIP_RO, LIP_RO + LIP_T, CAP_Z - LIP_H, CAP_Z + EPS)
    s += radial_ribs((30.0, 60.0, 120.0, 150.0, 210.0, 240.0, 300.0, 330.0), 20.0, LIP_RI - 1.0, CAP_Z - RIB_H, RIB_H + EPS)
    # vent slots, a group at the front and one at the back
    vw, vl, vp, n = P.ENC_CAP_VENTS
    for sy in (-1, 1):
        for i in range(n):
            y = sy * (70.0 + i * vp)
            s -= Pos(0, y, CAP_Z - 1) * Box(vl, vw, P.ENC_CAP_T + 2, align=(C, C, MN))
    # the webcam hangs under the top inside the window (taped), looking out through the clear sheet: three stops
    w, h, d = P.ENC_WEBCAM
    yi = P.ENC_WEBCAM_Y                                                      # the body's front face
    for sx in (-1, 1):
        s += Pos(sx * (w / 2 + FIT + 1.5), yi - d / 2, CAP_Z - h - 1.0) * Box(3.0, d, h + 1.0 + EPS, align=(C, C, MN))
    s += Pos(0, yi - d - FIT - 1.5, CAP_Z - h - 1.0) * Box(w, 3.0, h + 1.0 + EPS, align=(C, C, MN))
    return s


def cap_halves():
    full = cap_full()
    out = {}
    for half, (a0, a1) in HALVES.items():
        s = full & wedge(a0, a1)
        add, cut = seam_walls(half, ((-LIP_RI + 1.0, LIP_RI - 1.0),), CAP_Z + EPS, SEAM_H, (-120.0, -70.0, 70.0, 120.0), up=False)
        s = s + add - cut
        out[f"enc_cap_{half}"] = s
    return out


# ---------------------------------------------------------------------------
# the deck (top ring) halves and the bottom ring halves
# ---------------------------------------------------------------------------
def top_full():
    r_in, r_rim = P.ENC_TOP_RING
    s = ring(r_in, r_rim + EPS, TOP_Z - PLATE_T, TOP_Z)                       # the plate
    s += ring(RIM_R, P.ENC_BAND_R, TOP_Z - PLATE_T, TOP_Z + RIM_H)              # the rim the band wraps
    s += ring(LIP_RI, LIP_RI + LIP_T, TOP_Z - EPS, TOP_Z + LIP_H)                 # the window's lower lip
    s += radial_ribs((22.5, 67.5, 112.5, 157.5, 202.5, 247.5, 292.5, 337.5), r_in + 6.0, LIP_RI - 1.0, TOP_Z - EPS, RIB_H + EPS)
    for a in P.ENC_BAND_SCREWS_DEG:                                          # M3 + nut through the rim and the band
        s -= radial_cyl(CLR_R, a, RIM_R - 1.0, P.ENC_BAND_R + 1.0, TOP_Z + P.ENC_BAND_SCREW_Z)
    sw, sr0, sr1 = P.ENC_LEAD_SLOT                                           # the webcam lead's slot, at the back
    s -= Rot(0, 0, LEAD_SLOT_DEG) * Pos((sr0 + sr1) / 2, 0, TOP_Z - PLATE_T - 1) * Box(sr1 - sr0, sw, PLATE_T + 2, align=(C, C, MN))
    return s


def top_halves():
    full = top_full()
    r_in, r_rim = P.ENC_TOP_RING
    out = {}
    for half, (a0, a1) in HALVES.items():
        s = full & wedge(a0, a1)
        add, cut = seam_walls(half, ((-LIP_RI + 1.0, -r_in - 0.5), (r_in + 0.5, LIP_RI - 1.0)), TOP_Z - EPS, SEAM_H, (-100.0, 100.0))
        out[f"enc_top_{half}"] = s + add - cut
    return out


def bottom_full():
    r_in, r_rim = P.ENC_BOTTOM_RING
    z0 = RIB_TOP
    s = ring(r_in, r_rim + EPS, z0, z0 + PLATE_T)
    s += ring(RIM_R, P.ENC_BAND_R, z0, z0 + PLATE_T + RIM_H)
    ear_r, ear_w = P.ENC_BOTTOM_EAR
    for a in P.ENC_EARS_DEG:                                                 # ears down onto the tray's outer rib, M3 self-tapping
        s += Rot(0, 0, a) * Pos((ear_r + r_in + 1.0) / 2, 0, z0) * Box(r_in + 1.0 - ear_r, ear_w, PLATE_T, align=(C, C, MN))
        s -= vcyl(CLR_R, P.ENC_TRAY_RIBS[0][0] + 1.0, a, z0 - 1, z0 + PLATE_T + 1)   # the bosses sit 0.5 inside the tray's edge
    for a in P.ENC_BAND_SCREWS_DEG:
        s -= radial_cyl(CLR_R, a, RIM_R - 1.0, P.ENC_BAND_R + 1.0, z0 + PLATE_T + P.ENC_BAND_SCREW_Z)
    return s


def bottom_halves():
    full = bottom_full()
    r_in, r_rim = P.ENC_BOTTOM_RING
    out = {}
    for half, (a0, a1) in HALVES.items():
        s = full & wedge(a0, a1)
        add, cut = seam_walls(half, ((-r_rim + 0.5, -r_in - 0.5), (r_in + 0.5, r_rim - 0.5)), RIB_TOP + PLATE_T - EPS, SEAM_H, (-139.0, 139.0))
        out[f"enc_bottom_{half}"] = s + add - cut
    return out


# ---------------------------------------------------------------------------
# tray, pedestal, panels
# ---------------------------------------------------------------------------
def tray():
    d, t = P.ENC_TRAY
    s = cyl(d / 2, TRAY_Z0, TRAY_TOP)
    for r0, rt, rh in P.ENC_TRAY_RIBS:
        s += ring(r0, r0 + rt, TRAY_TOP - EPS, TRAY_TOP + rh)
    (r0, rt, rh), (q0, qt, qh) = P.ENC_TRAY_RIBS
    for a in P.ENC_EARS_DEG:                                                 # self-tapping M3: the bottom rings' ears, in bosses
        s += vcyl(P.ENC_BOSS_D / 2, r0 + 1.0, a, TRAY_TOP - EPS, TRAY_TOP + rh)
        s -= vcyl(P.M3_SELF_TAP / 2, r0 + 1.0, a, TRAY_TOP + rh - 7.0, TRAY_TOP + rh + 1)
    for a in (45.0, 135.0, 225.0, 315.0):                                    # self-tapping M3: the pedestal's flange, in bosses
        s += vcyl(P.ENC_BOSS_D / 2, q0 + qt / 2, a, TRAY_TOP - EPS, TRAY_TOP + qh)
        s -= vcyl(P.M3_SELF_TAP / 2, q0 + qt / 2, a, TRAY_TOP + qh - 7.0, TRAY_TOP + qh + 1)
    s += radial_ribs((0.0, 90.0, 180.0, 270.0), q0 + qt - 1.5, r0 + 1.5, TRAY_TOP - EPS, rh - 0.5)   # 1.5 into both ring ribs, 0.5 lower (no coplanar tops)
    # speaker saddles: two ribs along y (the speaker lies along x at the front) with a round seat
    sw, st, sh, xs, lift = P.ENC_SADDLE
    sr = P.ENC_SPEAKER[0] / 2 + 0.5
    _, sy, _ = P.ENC_LAYOUT["speaker"]
    zc = TRAY_TOP + lift + sr                                                # the speaker's axis
    for x in xs:
        rib = Pos(x, sy, TRAY_TOP - EPS) * Box(st, sw, sh + EPS, align=(C, C, MN))
        rib -= Pos(x, sy, zc) * Rot(0, 90, 0) * Cylinder(sr, st + 2)
        s += rib
    # the bank's rails
    bx, by, _ = P.ENC_LAYOUT["bank"]
    bl, bw, _ = P.ENC_BANK
    rt, rh, shorter = P.ENC_BANK_RAIL
    for sy in (-1, 1):
        y = by + sy * (bw / 2 + 0.5 + rt / 2)
        s += Pos(bx, y, TRAY_TOP - EPS) * Box(bl - shorter, rt, rh + EPS, align=(C, C, MN))
    return s


def pedestal():
    r = P.ENC_PEDESTAL / 2
    wall = P.ENC_PEDESTAL_WALL
    z0 = RIB_TOP
    s = cyl(r, z0, 0.0)
    s -= cyl(r - wall, z0 - 1, -P.ENC_PEDESTAL_TOP_T)
    s -= cyl(P.ENC_BORE / 2, -P.ENC_PEDESTAL_TOP_T - 1, 1.0)
    sq = P.NECK_BOLT_SQUARE / 2
    for sx in (-1, 1):
        for sy in (-1, 1):
            s -= cyl(P.M4_CLEAR / 2, -P.ENC_PEDESTAL_TOP_T - 1, 1.0, sx * sq, sy * sq)
    reach, ft = P.ENC_PEDESTAL_FLANGE
    s += ring(r - wall - reach, r - wall + 0.5, z0, z0 + ft)                    # the bottom flange, inward, on the tray's inner rib
    s += rz_solid([(r - wall - reach, z0 + ft - EPS), (r - wall + 0.5, z0 + ft - EPS),
                   (r - wall + 0.5, z0 + ft - EPS + 1.25 * (reach + 0.5))])      # 51 deg wedge over it: printable upside down
    (q0, qt, qh) = P.ENC_TRAY_RIBS[1]
    for a in (45.0, 135.0, 225.0, 315.0):
        s -= vcyl(CLR_R, q0 + qt / 2, a, z0 - 1, z0 + ft + reach + 2)
    return s


def panel(a, lead_notch=False):
    """A slotted curved panel built from bars (a curved face with eleven holes tessellates with dents)."""
    w, h, zc, t = P.ENC_PANEL
    r0 = P.ENC_BAND_R + 0.3 + P.ENC_SHEET_T + FIT           # off the band (which has 0.3 play on its rims)
    z_lo, z_hi = zc - h / 2, zc + h / 2
    rail = 13.0                                              # the side rails' width (the slots are w - 26 long)

    def bar(z0, z1, width):
        return ring(r0, r0 + t, z0, z1) & chord_box(r0, width, z0 - 1, z1 + 1, a, 60.0)

    slot_zs = list(np.arange(z_lo + 14.0, z_hi - 12.0, P.ENC_VENT[1]))
    s = bar(z_lo, slot_zs[0] - 1.5, w)                         # the bottom band
    s += bar(slot_zs[-1] + 1.5, z_hi, w)                       # the top band
    for z0, z1 in zip(slot_zs[:-1], slot_zs[1:]):             # the bars between the slots
        s += bar(z0 + 1.5 - EPS, z1 - 1.5 + EPS, w - 2 * rail + 1.0)
    for sx in (-1, 1):                                         # the side rails
        s += (ring(r0, r0 + t, z_lo, z_hi) & chord_box(r0, w, z_lo - 1, z_hi + 1, a, 60.0)
              - chord_box(r0, w - 2 * rail, z_lo - 1, z_hi + 1, a, 60.0)) & wedge(a - 30.0, a + 30.0) if sx == 1 else s
    if lead_notch:
        nw, nh = P.ENC_PANEL_LEAD_NOTCH
        s -= chord_box(r0, nw, z_lo - 20.0, z_lo + nh, a, 60.0)
    for sx in (-1, 1):
        for z in P.ENC_PANEL_SCREWS[1:]:
            x = sx * P.ENC_PANEL_SCREWS[0]
            ah = a + np.degrees(np.arcsin(x / r0)) * (1 if a == 90.0 else -1)
            s -= radial_cyl(CLR_R, ah, r0 - 2, r0 + t + 1, z)
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
    ow, od_, oy = P.NECK_SPINE_TOP_OPENING
    s -= Pos(0, oy - AY, top - 30.0) * Box(ow, od_, 31.0, align=(C, C, MN))
    # ASSUMPTION: 4 x M3 through the top plate up into inserts in the frame's nape members
    for x, y in P.NECK_SPINE_SCREWS:
        s -= cyl(CLR_R, top - tt - 1, top + 1, x, y - AY)
    return s


# ---------------------------------------------------------------------------
# reference shapes (not printed)
# ---------------------------------------------------------------------------
def ref_parts():
    out = {}
    out["sheet"] = ring(P.ENC_SHEET_R, P.ENC_SHEET_R + P.ENC_SHEET_T, TOP_Z, P.ENC_SHEET_TOP)
    out["band"] = ring(P.ENC_BAND_R + 0.3, P.ENC_BAND_R + 0.3 + P.ENC_SHEET_T, RIB_TOP + PLATE_T, TOP_Z + RIM_H)
    for name, (x, y, turn) in P.ENC_LAYOUT.items():
        lift = P.ENC_LAYOUT_Z.get(name, 0.0)
        if name == "speaker":
            dia, ln = P.ENC_SPEAKER
            out[name] = Pos(x, y, TRAY_TOP + P.ENC_SADDLE[4] + dia / 2 + 0.5) * Rot(0, 0, turn) * Rot(90, 0, 0) * Cylinder(dia / 2, ln)   # in its seat
        else:
            size = {"bank": P.ENC_BANK, "buck": P.ENC_BUCK}.get(name, P.ENC_BOARD)
            out[name] = Pos(x, y, TRAY_TOP + EPS + lift) * Rot(0, 0, turn) * Box(*size, align=(C, C, MN))
    w, h, d = P.ENC_WEBCAM
    yi = P.ENC_WEBCAM_Y
    out["webcam"] = Pos(0, yi - d / 2, CAP_Z - 1.0 - h) * Box(w, d, h, align=(C, C, MN))
    return out


# ---------------------------------------------------------------------------
def shift(d):
    return {n: Pos(0, AY, 0) * s for n, s in d.items()}


def parts():
    out = {}
    for fn in (cap_halves, top_halves, bottom_halves):
        out.update(fn())
    out["enc_tray"] = tray()
    out["enc_pedestal"] = pedestal()
    out["enc_grille"] = panel(90.0)
    out["enc_hatch"] = panel(270.0, lead_notch=True)
    out["neck"] = neck()
    return shift(out)


def main():
    ok = True
    for name, shp in parts().items():
        if not shp.is_valid:
            print(f"FAIL  {name}: not a valid solid")
            ok = False
        fine = name in ("enc_grille", "enc_hatch", "enc_cap_F", "enc_cap_B", "enc_tray")   # slotted or cut curved faces tessellate badly at 0.05
        ok &= K.write_stl(shp, name, tolerance=0.01 if fine else 0.05, angular_tolerance=0.05 if fine else 0.2)
    rdir = os.path.join(G.ref_dir(), "enclosure")
    os.makedirs(rdir, exist_ok=True)
    refs = shift(ref_parts())
    for name, shp in refs.items():
        export_stl(shp, os.path.join(rdir, name + ".stl"), tolerance=0.05, angular_tolerance=0.2)
    print(f"reference shapes -> output/ref/enclosure ({len(refs)})")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())

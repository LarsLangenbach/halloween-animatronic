"""
Eyebrow mechanism v1 (M2), both sides, in the assembled pose (brow at rest).

Per side (built for the left brow, mirrored for the right):
  brow_carrier_<side>  one print: two snap pads on the skin side, a bar between
                       them set BROW_BAR_RECESS deeper, an arm arching over the
                       lids, and the hub that turns on an M3 shoulder screw, with
                       the rocker lever for the pushrod ball
  brow_bracket_<side>  one print: the cheek holding the shoulder screw (M3
                       heat-set insert), an upright, the MG90S plate under the
                       servo's tabs, and a top flange that bolts to the skull
                       (or to the bench rig)
Not printed, written to output/ref/brow/ for the checks and renders: the
servo (Adafruit MG90 model), its horn, the pushrod, the shoulder screw.

All placements come from browgeom.py (pivot, axis, four-bar); the numbers live
in params.py.

Run:  python cad/brow.py      -> output/stl/brow_*.stl, output/ref/brow/*.stl
"""
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import cadkit as K  # noqa: E402
import browgeom as B  # noqa: E402
import geom as G  # noqa: E402

from build123d import (Align, Box, Cylinder, Location, Plane, Polygon, Pos, Rot, Sphere,  # noqa: E402
                       Vector, export_stl, extrude, import_step, mirror)

P = K.params()
EPS = 0.01
LOCAL = Location(tuple(B.PIVOT), (0, 0, P.BROW_PIVOT_SKEW))   # local (x', y', z') -> head frame


def lbox(x0, x1, y0, y1, z0, z1):
    """Axis-aligned box in the local frame, from its extents."""
    return Pos((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2) * Box(x1 - x0, y1 - y0, z1 - z0)


def xcyl(r, x0, x1, y=0.0, z=0.0):
    """Cylinder along x' in the local frame."""
    return Pos((x0 + x1) / 2, y, z) * (Rot(0, 90, 0) * Cylinder(r, x1 - x0))


def beam(a, b, w, t, up=(0.0, 0.0, 1.0), extra=0.6):
    """Box from point a to b (any frame), w wide (along up x dir) and t thick."""
    a, b = np.asarray(a, float), np.asarray(b, float)
    d = b - a
    length = float(np.linalg.norm(d))
    x = d / length
    z = np.cross(x, np.asarray(up, float))
    if np.linalg.norm(z) < 1e-6:
        z = np.cross(x, np.array([1.0, 0.0, 0.0]))
    z /= np.linalg.norm(z)
    pl = Plane(origin=Vector(*((a + b) / 2)), x_dir=Vector(*x), z_dir=Vector(*z))
    return pl * Box(length + extra, w, t)


# ---------------------------------------------------------------------------
def carrier():
    # skin side, in the head frame
    parts = []
    for px in P.BROW_PADS_X:
        c = B.surface_point(px, B.ZB)
        n = B.normals(px, B.ZB)[0]
        tx = np.array([1.0, 0.0, 0.0]) - n * n[0]
        pl = Plane(origin=Vector(*c), x_dir=Vector(*(tx / np.linalg.norm(tx))), z_dir=Vector(*n))
        pad = pl * Box(P.BROW_PAD, P.BROW_PAD, P.BROW_PAD_T, align=(Align.CENTER, Align.CENTER, Align.MAX))
        hole = pl * Cylinder(1.1, 3 * P.BROW_PAD_T)         # snap adapter screw (M4 sizes it)
        parts.append((pad, hole))
    depth = P.BROW_BAR_RECESS + P.BROW_BAR[1] / 2
    xs = np.linspace(P.BROW_PADS_X[0], P.BROW_PADS_X[1], 6)
    line = [B.surface_point(x, B.ZB, depth) for x in xs]
    bar = None
    for a, b, x in zip(line, line[1:], (xs[:-1] + xs[1:]) / 2):
        seg = beam(a, b, P.BROW_BAR[0], P.BROW_BAR[1], up=B.normals(x, B.ZB)[0])
        bar = seg if bar is None else bar + seg
    skin_side = bar
    for pad, _ in parts:
        skin_side += pad

    # drive side, in the local frame
    rise = B.EZ + P.BROW_ARM_RISE - B.PIVOT[2]
    a0 = B.to_local(B.surface_point(B.XM, B.ZB, P.BROW_BAR_RECESS + P.BROW_BAR[1] - 0.6))
    a1 = np.array([a0[0], a0[1] - 4.0, rise])
    # come down to the hub inboard of the bracket's upright (x' >= CHEEK_X[0]) and in
    # front of it (y' > 8): the carrier turns about x', so this gap holds at every angle
    a2 = np.array([-1.0, 14.0, rise])
    a3 = np.array([0.0, 0.0, 0.0])
    w, t = P.BROW_ARM
    arm = beam(a0, a1, w, t, up=(1, 0, 0)) + beam(a1, a2, w, t, up=(1, 0, 0)) + beam(a2, a3, w, t, up=(1, 0, 0))
    arm += Pos(*a1) * Sphere(w * 0.62) + Pos(*a2) * Sphere(w * 0.62)
    hub = xcyl(P.BROW_HUB_D / 2, *B.HUB_X)
    lever = lbox(*B.LEVER_X, -P.BROW_ROCKER_R, -P.BROW_HUB_D / 2 + 1.0, -3.0, 3.0)
    lever += xcyl(3.5, *B.LEVER_X, y=-P.BROW_ROCKER_R)
    drive = arm + hub + lever
    drive -= xcyl(P.SHOULDER_BORE / 2, B.HUB_X[0] - 1, B.HUB_X[1] + 1)
    drive -= xcyl(P.M2_PILOT / 2, B.LEVER_X[0] - 1, B.LEVER_X[1] + 1, y=-P.BROW_ROCKER_R)   # ball stud

    shape = skin_side + LOCAL * drive
    for _, hole in parts:
        shape -= hole
    return shape


def bracket():
    cx0, cx1 = B.CHEEK_X
    sy, sz = B.SERVO_AXIS
    tab = B.TAB_X
    cheek = lbox(cx0, cx1, -12.0, 8.0, -8.0, 10.0)
    cheek -= xcyl(P.M3_INSERT_HOLE / 2, cx0 - 1, cx0 + 5.0)              # M3 x 4 insert from the hub side
    cheek -= xcyl(P.M3_INSERT_HOLE / 2 + 1.0, cx0 - 1, cx0 + P.INSERT_RECESS)   # its recess
    upright = lbox(cx0, cx1, 2.0, 8.0, 8.0, 56.0 + EPS)
    plate = lbox(tab, tab + 3.0, -20.0, 8.0, sz - 14.0, 56.0 + EPS)
    cut = lbox(tab - 1, tab + 4, sy - P.MG90_W / 2 - 0.4, sy + P.MG90_W / 2 + 0.4,
               sz - P.MG90_SHAFT_FROM_END - 0.4, sz - P.MG90_SHAFT_FROM_END + P.MG90_CASE_L + 0.4)
    plate -= cut
    for dz in (P.MG90_HOLE_OFFSET, P.MG90_HOLE_OFFSET + P.MG90_HOLE_SPACING):
        plate -= xcyl(P.M2_PILOT / 2, tab - 1, tab + 4, y=sy, z=sz + dz)
    # printed upside down (top flange on the bed): every face that points up here
    # points down on the printer, so the cheek's top and the plate brace are 45+ deg slopes
    cheek_slope = extrude(Plane.YZ.offset(cx0) * Polygon((-12.0, 9.5), (2.5, 9.5), (2.5, 24.0), align=None),
                          amount=cx1 - cx0)
    brace = extrude(Plane.XZ.offset(-8.0) * Polygon((cx1 - 0.5, sz - 14.0), (tab + 0.5, sz - 14.0),
                                                    (cx1 - 0.5, sz - 14.0 + 1.2 * (tab - cx1 + 1.0)), align=None),
                    amount=6.0)
    f0, f1 = B.FLANGE_Z
    flange = lbox(cx0, tab + 3.0, -20.0, 8.0, f0, f1)
    # the stop ledge is filled up to the flange: printed upside down, a free ledge would hang
    ledge = lbox(cx0, cx1 - 1.0, P.BROW_STOPS_Y[1] - 3.0, 2.5, P.BROW_STOP_LEDGE_Z[0], f0 + EPS)
    shape = cheek + cheek_slope + upright + plate + brace + flange + ledge
    for x, y in P.BROW_MOUNTS:                                          # M3 x 4 inserts, from the top
        shape -= Pos(x, y, f1 - 2.5) * Cylinder(P.M3_INSERT_HOLE / 2, 5.0 + 0.02)
    for y in P.BROW_STOPS_Y:                                           # stop screws + key access
        z0, z1 = P.BROW_STOP_LEDGE_Z
        shape -= Pos(B.HORN_X, y, (z0 + z1) / 2) * Cylinder(P.M3_TAP / 2, z1 - z0 + 2.0)
        shape -= Pos(B.HORN_X, y, (z1 + f1) / 2 + 0.5) * Cylinder(P.HEX_KEY_D / 2, f1 - z1 + 2.0)
    return LOCAL * shape


# ---------------------------------------------------------------------------
# reference parts (not printed)
# ---------------------------------------------------------------------------
def servo():
    """Adafruit MG90 model: its shaft (model z) points inboard (-x'), its case
    length (model y) runs up (+z'), model x runs -y'; tab underside on TAB_X."""
    m = import_step(os.path.join(K.inputs(), "components", "adafruit_1143_micro_servo.step"))
    sy, sz = B.SERVO_AXIS
    # model X -> -y', model Z -> -x', so model Y -> z' (x_dir x z_dir handedness checked)
    place = Plane(origin=(B.TAB_X, sy, sz), x_dir=(0, -1, 0), z_dir=(-1, 0, 0))
    return LOCAL * (place * m)


def horn():
    """Double-arm horn: the back arm carries the pushrod ball and meets the lower stop; the front
    arm, cut down to HORN_FRONT_R, meets the raise stop."""
    sy, sz = B.SERVO_AXIS
    tip = B.crank_ball(0.0)
    # up=z' puts the arm's width in the y'z' plane and its 2 mm thickness along the shaft (review fix)
    half = P.HORN_ARM_W / 2                  # beam() adds half a width beyond each end: arms end at R
    back = beam((B.HORN_X, sy, sz), (B.HORN_X, sy - P.HORN_BACK_R + half, sz), P.HORN_ARM_W, 2.0, up=(0, 0, 1),
                extra=P.HORN_ARM_W)
    front = beam((B.HORN_X, sy, sz), (B.HORN_X, sy + P.HORN_FRONT_R - half, sz), P.HORN_ARM_W, 2.0, up=(0, 0, 1),
                 extra=P.HORN_ARM_W)
    return LOCAL * (back + front)


def stop_screws():
    """The two M3 set screws, from the ledge's top down to their set tips."""
    out = None
    for y, tip in zip(P.BROW_STOPS_Y, B.stop_tips()):
        top = P.BROW_STOP_LEDGE_Z[1]
        s = Pos(B.HORN_X, y, (top + tip) / 2) * Cylinder(1.5, top - tip)
        out = s if out is None else out + s
    return LOCAL * out


def pushrod():
    a = B.rocker_ball(0.0)
    b = B.crank_ball(0.0)
    return LOCAL * beam((B.LINK_X, a[0], a[1]), (B.LINK_X, b[0], b[1]), P.BALL_LINK_D, P.BALL_LINK_D,
                        up=(1, 0, 0), extra=P.BALL_LINK_D)


def shoulder_screw():
    head = xcyl(P.SHOULDER_HEAD[0] / 2, B.HUB_X[0] - P.SHOULDER_HEAD[1], B.HUB_X[0] - 0.05)
    seat = B.CHEEK_X[0] + P.INSERT_RECESS                                # shoulder end on the insert
    shoulder = xcyl(P.SHOULDER_D / 2, B.HUB_X[0] - 0.1, seat)
    thread = xcyl(1.5, seat - 0.1, seat + 4.0)
    return LOCAL * (head + shoulder + thread)


def sides(shape_left):
    return {"L": shape_left, "R": mirror(shape_left, about=Plane.YZ)}


def parts():
    out = {}
    for name, fn in (("carrier", carrier), ("bracket", bracket)):
        for side, shp in sides(fn()).items():
            out[f"brow_{name}_{side}"] = shp
    return out


def ref_parts():
    out = {}
    for name, fn in (("servo", servo), ("horn", horn), ("pushrod", pushrod), ("shoulder_screw", shoulder_screw),
                     ("stop_screws", stop_screws)):
        for side, shp in sides(fn()).items():
            out[f"{name}_{side}"] = shp
    return out


def main():
    ok = True
    for name, shp in parts().items():
        if not shp.is_valid:
            print(f"FAIL  {name}: not a valid solid")
            ok = False
        ok &= K.write_stl(shp, name)
    rdir = os.path.join(G.ref_dir(), "brow")
    os.makedirs(rdir, exist_ok=True)
    for name, shp in ref_parts().items():
        export_stl(shp, os.path.join(rdir, name + ".stl"), tolerance=0.05, angular_tolerance=0.2)
    print(f"reference parts -> output/ref/brow ({len(ref_parts())})")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())

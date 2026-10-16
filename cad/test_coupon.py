"""
Calibration coupon for the holes: print it first, flat (dimples up), in the
same material and settings as the real parts. Printed holes come out
0.1-0.2 mm small and horizontal holes print differently from vertical ones,
so pick the winners here instead of guessing in the model.

  top face   3 heat-set insert holes  INSERT_HOLE_D - 0.1 / +0 / +0.1   (1 / 2 / 3 dimples)
             3 clearance holes        M25_CLEAR - 0.2 / +0 / +0.2      (1 / 2 / 3 dimples)
             the middle clearance hole has the counterbore from below
  side face  3 insert holes, horizontal, same three sizes, small to large from -x to +x

Melt an insert into each insert hole (iron at print temperature + 10-20 C,
push 90 %, press the rest flush with a cold flat tool): pick the size where
it goes in straight with light pressure and the plastic just wells up to its
rim. Run a screw through the clearance holes. Set the winners in params.py.

Run:  python cad/test_coupon.py  -> <stl_dir>/test_coupon.stl
"""
import os
import sys

from build123d import Align, Axis, Box, Cylinder, Pos, Rot, Sphere, chamfer

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import cadkit as K  # noqa: E402

P = K.params()
UP = (Align.CENTER, Align.CENTER, Align.MIN)
L, W, H = 46.0, 14.0, 10.0
STEPS = (-1, 0, 1)


def coupon():
    part = Box(L, W, H, align=UP)
    part = chamfer(part.edges().group_by(Axis.Z)[0], P.EF_CHAMFER)
    xs = [-18.0, -10.0, -2.0, 6.0, 14.0, 20.0]
    for i, s in enumerate(STEPS):                       # vertical insert holes, top face
        x, d = xs[i], P.INSERT_HOLE_D + 0.1 * s
        part -= Pos(x, -1.5, H - P.INSERT_HOLE_DEPTH) * Cylinder(d / 2, P.INSERT_HOLE_DEPTH + 1, align=UP)
        part = dimples(part, x, -1.5 + 4.5, i + 1)
    for i, s in enumerate(STEPS):                       # clearance holes, through
        x, d = xs[3 + i], P.M25_CLEAR + 0.2 * s
        part -= Pos(x, 3.0, -1) * Cylinder(d / 2, H + 2, align=UP)
        if s == 0:
            cd, cdepth = P.M25_CBORE
            part -= Pos(x, 3.0, -1) * Cylinder(cd / 2, cdepth + 1, align=UP)
        part = dimples(part, x, 3.0 - 4.0, i + 1)
    for i, s in enumerate(STEPS):                       # horizontal insert holes, -y face,
        x, d = xs[3 + i], P.INSERT_HOLE_D + 0.1 * s     # under the clearance holes, small to large
        part -= Pos(x, -W / 2 - 1, H / 2) * (Rot(-90, 0, 0) * Cylinder(d / 2, P.INSERT_HOLE_DEPTH + 1, align=UP))
    return part


def dimples(part, x, y, n):
    for k in range(n):
        part -= Pos(x - (n - 1) * 0.9 + k * 1.8, y, H) * Sphere(0.6)
    return part


def parts():
    return {"test_coupon": coupon()}


if __name__ == "__main__":
    sys.exit(0 if K.write_stl(coupon(), "test_coupon") else 1)

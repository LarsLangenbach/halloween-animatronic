"""
Real parts against the params file: measures the manufacturer 3D models in
<inputs>/components (listed in components.yaml) and compares them with the
sizes the design was built around.

Per model: board length x width x thickness (the PCB is the largest thin
solid), overall thickness with components, connectors that stick out past
the board outline, and mounting holes. For a `match: exact` model a
difference that would bind is a WARN; `match: reference` models (a different
board of the same kind) only print info.

Works on raw OCP, so either CadQuery or build123d being installed is enough.

Run:  python <source>/components_check.py
"""
import itertools
import os
import sys

import yaml
from OCP.Bnd import Bnd_Box
from OCP.BRepAdaptor import BRepAdaptor_Surface
from OCP.BRepBndLib import BRepBndLib
from OCP.BRepGProp import BRepGProp
from OCP.GeomAbs import GeomAbs_Cylinder
from OCP.GProp import GProp_GProps
from OCP.IFSelect import IFSelect_RetDone
from OCP.STEPControl import STEPControl_Reader
from OCP.TopAbs import TopAbs_FACE, TopAbs_SOLID
from OCP.TopExp import TopExp_Explorer
from OCP.TopoDS import TopoDS

# OCP 7.7 names the downcasts Solid_s / Face_s; OCP 7.8+ / 8 drop the suffix.
SOLID = getattr(TopoDS, "Solid_s", None) or TopoDS.Solid
FACE = getattr(TopoDS, "Face_s", None) or TopoDS.Face

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import cadkit as K  # noqa: E402

P = K.params()
COMP = os.path.join(K.inputs(), "components")
THIN = 2.0          # a solid whose smallest side is at most this is a PCB candidate
MIN_SIDE_GAP = 0.3  # least per-side room for a part in a pocket
OVERHANG = 0.5      # a connector further past the board edge than this needs room
HOLE_D = (1.8, 4.0)  # mounting holes; smaller cylinders are pin and via holes
WARNS = []


def say(level, msg):
    print(f"{level:6s}{msg}")
    if level == "WARN":
        WARNS.append(msg)


def read_step(path):
    r = STEPControl_Reader()
    if r.ReadFile(path) != IFSelect_RetDone:
        raise SystemExit(f"can't read {path}")
    r.TransferRoots()
    return r.OneShape()


def items(shape, kind, cast):
    exp = TopExp_Explorer(shape, kind)
    while exp.More():
        yield cast(exp.Current())
        exp.Next()


def lo_hi(shape):
    box = Bnd_Box()
    BRepBndLib.AddOptimal_s(shape, box, True, False)
    p0, p1 = box.CornerMin(), box.CornerMax()       # Bnd_Box.Get() no longer converts in OCP 8
    return [p0.X(), p0.Y(), p0.Z()], [p1.X(), p1.Y(), p1.Z()]


def ext(shape):
    lo, hi = lo_hi(shape)
    return [hi[i] - lo[i] for i in range(3)]


def volume(solid):
    props = GProp_GProps()
    BRepGProp.VolumeProperties_s(solid, props)
    return props.Mass()


def analyse(path):
    shape = read_step(path)
    solids = list(items(shape, TopAbs_SOLID, SOLID))
    all_lo, all_hi = lo_hi(shape)
    thin = [s for s in solids if min(ext(s)) <= THIN]
    if not thin:                                   # a block (battery, motor): no PCB
        e = sorted(ext(shape), reverse=True)
        return dict(board=None, L=e[0], W=e[1], t=e[2], total=e[2], overhangs=[], holes=[])
    board = max(thin, key=volume)
    e = ext(board)
    n = e.index(min(e))                            # board normal axis
    a, b = sorted((i for i in range(3) if i != n), key=lambda i: -e[i])
    b_lo, b_hi = lo_hi(board)
    centre = [(b_lo[i] + b_hi[i]) / 2 for i in range(3)]

    overhangs = []                                 # (end, mm, offset across, width across)
    for s in solids:
        if s.IsSame(board):
            continue
        s_lo, s_hi = lo_hi(s)
        for axis, label, across in ((a, "L", b), (b, "W", a)):
            for sign, past in ((-1, b_lo[axis] - s_lo[axis]), (+1, s_hi[axis] - b_hi[axis])):
                if past > 0.05:
                    mid = (s_lo[across] + s_hi[across]) / 2 - centre[across]
                    overhangs.append((("-" if sign < 0 else "+") + label, past, mid,
                                      s_hi[across] - s_lo[across]))

    holes = []
    for f in items(board, TopAbs_FACE, FACE):
        surf = BRepAdaptor_Surface(f)
        if surf.GetType() != GeomAbs_Cylinder:
            continue
        cyl = surf.Cylinder()
        d = cyl.Axis().Direction()
        d = [d.X(), d.Y(), d.Z()]
        if abs(abs(d[n]) - 1) > 1e-3 or not HOLE_D[0] <= 2 * cyl.Radius() <= HOLE_D[1]:
            continue
        p = cyl.Location()
        p = [p.X(), p.Y(), p.Z()]
        u, v = p[a] - centre[a], p[b] - centre[b]
        if not all(abs(h[0] - u) > 0.05 or abs(h[1] - v) > 0.05 for h in holes):
            continue
        holes.append((u, v, 2 * cyl.Radius()))
    return dict(board=True, L=e[a], W=e[b], t=e[n], total=all_hi[n] - all_lo[n],
                overhangs=overhangs, holes=holes)


def check(name, c):
    exact = c.get("match") == "exact"
    warn = "WARN" if exact else "info"
    print(f"\n== {name}: {c['part']} [{c['match']}]")
    path = os.path.join(COMP, c["file"])
    if not os.path.exists(path):
        say("WARN", f"{name}: model file missing: {c['file']}")
        return
    m = analyse(path)
    kind = "board" if m["board"] else "body"
    say("info", f"{kind} {m['L']:.2f} x {m['W']:.2f} x {m['t']:.2f}"
                + (f", {m['total']:.2f} thick with components" if m["board"] else ""))

    spec = c.get("board", {})
    clear = getattr(P, c["clear"]) if "clear" in c else None
    if "size" in spec:
        names = spec["size"]
        want = sorted(((getattr(P, k), k) for k in names), reverse=True)
        for real, (par, key) in zip((m["L"], m["W"]), want):
            if clear is not None:
                side = (par + 2 * clear - real) / 2
                ok = side >= MIN_SIDE_GAP
                say("ok" if ok else warn, f"{name}: {real:.2f} in a pocket of {key} {par} + 2 x "
                    f"{c['clear']} {clear} -> {side:.2f} per side (want >= {MIN_SIDE_GAP})")
            elif real > par + 0.05:
                say(warn, f"{name}: real {real:.2f} is bigger than {key} {par}")
            elif par - real > 2.0:
                say("info", f"{name}: {key} {par} is {par - real:.1f} longer than the real {real:.2f}")
            else:
                say("ok", f"{name}: real {real:.2f} fits {key} {par}")
    if "thickness" in spec:
        key = spec["thickness"]
        par = getattr(P, key)
        real = m["total"]
        if clear is not None:
            side = (par + 2 * clear - real) / 2
            say("ok" if side >= MIN_SIDE_GAP else warn,
                f"{name}: thickness {real:.2f} in {key} {par} + 2 x {clear} -> {side:.2f} per side")
        else:
            say("ok" if real <= par + 0.05 else warn,
                f"{name}: overall thickness {real:.2f} vs {key} {par}")

    worst = {}
    for end, past, mid, width in m["overhangs"]:
        if past > worst.get(end, (0,))[0]:
            worst[end] = (past, mid, width)
    allowed = c.get("overhang", {})               # {edge: params name of the room left for it}
    for end, (past, mid, width) in sorted(worst.items()):
        msg = (f"{name}: a part sticks out {past:.2f} past the {end} edge "
               f"({width:.2f} wide, centred {mid:+.2f} from the board centreline)")
        if end in allowed:
            room = getattr(P, allowed[end])
            say("ok" if past <= room + 0.05 else warn, msg + f"; {allowed[end]} leaves {room}")
        elif past > OVERHANG and "size" in spec:
            say(warn, msg + " -- the params size is the bare board; make room at that end")
        else:
            say("info", msg)

    if m["holes"]:
        hs = ", ".join(f"({u:+.2f}, {v:+.2f}) d{d:.2f}" for u, v, d in m["holes"])
        say("info", f"{name}: {len(m['holes'])} mounting hole(s) at (along L, along W): {hs}")
        if "holes" in c:
            par = getattr(P, c["holes"])
            pairs = [((p[0] - q[0]) ** 2 + (p[1] - q[1]) ** 2) ** 0.5
                     for p, q in itertools.combinations(m["holes"], 2)]
            near = min(pairs, key=lambda s: abs(s - par)) if pairs else None
            say("info", f"{name}: hole spacings {', '.join(f'{s:.2f}' for s in sorted(pairs))}; "
                        f"{c['holes']} = {par}" + (f" (closest {near:.2f})" if near else ""))


def main():
    listing = os.path.join(COMP, "components.yaml")
    if not os.path.exists(listing):
        print(f"info  no {listing}: no component models to compare yet")
        print("\nCOMPONENTS MATCH PARAMS")
        return 0
    with open(listing, encoding="utf-8") as f:
        comps = yaml.safe_load(f) or {}
    for name, c in comps.items():
        check(name, c)
    print("\nCOMPONENTS MATCH PARAMS" if not WARNS else f"\n{len(WARNS)} COMPONENT MISMATCH(ES)")
    return 0 if not WARNS else 1


if __name__ == "__main__":
    sys.exit(main())

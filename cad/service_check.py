"""
M3 service check (brief: access for maintenance, servos removable): can each module come
out of the skull, and can a tool reach the screws that hold it?

  teardown   STEPS run in order; at each step everything not yet out stays where it is.
             A step moves its units along a polyline of translations. It passes when
             nothing moving passes more than SERVICE_TOL into anything staying: point
             clouds (with normals) pick candidates, exact containment against watertight
             meshes confirms them; on an open mesh a candidate counts. Sliding contact
             (a foot along its pad) is allowed.
  alone      single moves from the assembled head (the access panel, the neck plate).
  tools      an L-shaped hex key on each screw that must come out on the way (the brow
             flanges, from above under the crown; the shelf): its short arm along the
             screw's axis, its long arm level, turned all the way round. It passes when
             the long arm can swing through SERVICE_KEY_SWING without touching anything
             (a hex key needs 60 deg per bite). Where a standard key has no headroom, a
             stubby one (SERVICE_STUBBY_KEY: the short arm cut down) is tried.
  pending    moves with no path yet, listed (the mouth: its mount waits on Q14).

Run:  python cad/service_check.py      (after the builders)
  -> <out>/service/service.md, service.png
Final line: SERVICE OK, or SERVICE: n issue(s), each listed as a WARN line.
"""
import os
import sys
import warnings

import numpy as np
import trimesh
from scipy.spatial import cKDTree

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import cadkit as K  # noqa: E402
import brow_check as BC  # noqa: E402
import browgeom as B  # noqa: E402
import layout_check as L  # noqa: E402

warnings.filterwarnings("ignore", category=RuntimeWarning)
sys.stdout.reconfigure(encoding="utf-8")
P = K.params()
S = P.HEAD_SCALE
PIECES = ("skull_front_upper", "skull_front_lower", "skull_back_upper", "skull_back_lower", "skull_shelf",
          "skull_eye_strap", "skull_neck_plate", "skull_access_panel")
DENSITY = 0.3                    # cloud points per mm2 (about 1.8 mm apart)
_a = np.radians(P.BACK_UPPER_OUT_DEG)
BACK_OUT = np.array([0.0, -np.cos(_a), np.sin(_a)])

# (what, units moved together, path of translations from where they sit)
STEPS = (
    ("back upper piece, with the access panel and the eye strap",
     ("skull_back_upper", "skull_access_panel", "skull_eye_strap"), (tuple(250.0 * BACK_OUT),)),
    ("EyeMech and both brows together (brow flanges unbolted)",
     ("eyemech", "brow_L", "brow_R"), P.SERVICE_EYE_OUT),
    ("shelf", ("skull_shelf",), P.SERVICE_SHELF_OUT),
)
ALONE = (
    ("neck plate (head off its stand)", ("skull_neck_plate",), ((0.0, 0.0, -80.0),)),
)
PENDING = (("mouth module", "no path yet: it hits the back lower piece going back and the front upper piece "
            "going up; its mount and way out wait on Q14"),)


def load_units():
    stl = K.stl_dir()
    units = {n: [trimesh.load(os.path.join(stl, n + ".stl"), force="mesh")] for n in PIECES}
    base_scale, parts = L.load_parts()
    L.place(parts, base_scale, S)
    units["eyemech"] = [p["m"] for p in parts if p["module"] == "eyemech"]
    units["mouth"] = [p["m"] for p in parts if p["module"] == "mouth"]
    brow = {k: v for k, v in BC.load().items() if v is not None and not k.startswith("rig")}
    for side in "LR":
        units["brow_" + side] = [m for k, m in brow.items() if k.endswith("_" + side)]
    return units


class Cloud:
    """Surface samples of a unit's meshes, their normals, and which came from open meshes."""

    def __init__(self, meshes, seed=1):
        pts, nrm, opn = [], [], []
        for m in meshes:
            p, fi = trimesh.sample.sample_surface(m, int(max(200, m.area * DENSITY)), seed=seed)
            pts.append(p)
            nrm.append(m.face_normals[fi])
            opn.append(np.full(len(p), not m.is_watertight))
        self.p, self.n, self.open = np.vstack(pts), np.vstack(nrm), np.concatenate(opn)
        self.tree = cKDTree(self.p)
        self.lo, self.hi = self.p.min(axis=0), self.p.max(axis=0)
        self.meshes = meshes


def depth_inside(meshes, q, tol):
    """The deepest point of q inside a watertight mesh, if deeper than tol (exact)."""
    best = (0.0, None)
    for m in meshes:
        if not m.is_watertight:
            continue
        lo, hi = m.bounds
        sel = np.all((q > lo) & (q < hi), axis=1)
        if not sel.any():
            continue
        qi = q[sel][m.contains(q[sel])]
        if len(qi):
            dep = trimesh.proximity.closest_point(m, qi)[1]
            j = int(np.argmax(dep))
            if dep[j] > best[0]:
                best = (float(dep[j]), qi[j])
    return best if best[0] > tol else None


def into(q, cloud, tol):
    """Points q that pass more than tol into a unit: (depth, point) or None (-1 depth: by
    the normals of an open mesh)."""
    near = np.all((q > cloud.lo - 2) & (q < cloud.hi + 2), axis=1)
    if not near.any():
        return None
    qn = q[near]
    dist, idx = cloud.tree.query(qn)
    sd = np.einsum("ij,ij->i", qn - cloud.p[idx], cloud.n[idx])
    hit = (dist < 1.5) & (sd < -tol)
    if not hit.any():
        return None
    r = depth_inside(cloud.meshes, qn[hit], tol)
    if r is not None:
        return r
    if cloud.open[idx[hit]].any():
        return -1.0, qn[hit][cloud.open[idx[hit]]][0]
    return None


def move(moving, static, clouds, path, step=1.0, tol=P.SERVICE_TOL):
    """None if the moving units travel the path clear of the static ones, else (t along
    the path, unit hit, depth, point)."""
    mc = Cloud([m for k in moving for m in clouds[k].meshes])
    o, done = np.zeros(3), 0.0
    for w in path:
        w = np.asarray(w, float)
        seg = w - o
        length = float(np.linalg.norm(seg))
        d = seg / length
        for t in np.arange(min(step, length), length + 1e-6, step):
            off = o + t * d
            for k in static:
                sc = clouds[k]
                r = into(mc.p + off, sc, tol)
                if r is None:                                        # and the static unit into the moving one
                    s2 = sc.p[np.all((sc.p > mc.lo + off - 2) & (sc.p < mc.hi + off + 2), axis=1)]
                    if len(s2):
                        r = into(s2 - off, mc, tol)
                        if r is not None:
                            r = (r[0], r[1] + off)
                if r is not None:
                    return done + t, k, r[0], r[1]
        done += length
        o = w
    return None


def key_swing(head, axis, static, clouds, key=P.SERVICE_KEY):
    """An L hex key on a screw head: the short arm key[0] along the axis, the long arm
    key[1] level at its end. (widest clear swing in deg, azimuth at its middle)."""
    short, long_, r = key
    axis = np.asarray(axis, float) / np.linalg.norm(axis)
    pts = [head + axis * s for s in np.arange(0.5, short + 1e-6, 1.0)]
    if blocked_points(np.array(pts), r, static, clouds):
        return 0.0, None
    elbow = head + axis * short
    e1 = np.cross(axis, [1.0, 0.0, 0.0] if abs(axis[0]) < 0.9 else [0.0, 1.0, 0.0])
    e1 /= np.linalg.norm(e1)
    e2 = np.cross(axis, e1)
    angles = np.arange(0, 360, 5)
    clear = []
    for a in np.radians(angles):
        u = np.cos(a) * e1 + np.sin(a) * e2
        arm = np.array([elbow + u * s for s in np.arange(1.0, long_ + 1e-6, 1.0)])
        clear.append(not blocked_points(arm, r, static, clouds))
    clear = np.array(clear)
    if clear.all():
        return 360.0, 0.0
    best, mid = 0, None
    k = int(np.argmin(clear))                                   # start the scan at a blocked azimuth
    run = 0
    for i in range(1, len(angles) + 1):
        j = (k + i) % len(angles)
        run = run + 1 if clear[j] else 0
        if run > best:
            best, mid = run, angles[j] - 2.5 * run
    return 5.0 * best, mid


def blocked_points(pts, r, static, clouds):
    for k in static:
        sc = clouds[k]
        near = np.all((pts > sc.lo - r - 2) & (pts < sc.hi + r + 2), axis=1)
        if not near.any():
            continue
        dist, _ = sc.tree.query(pts[near])
        if (dist < r).any():
            return True
        cand = pts[near][dist < r + 2.0]                         # the cloud is ~1.8 apart: exact near it
        if len(cand):
            for m in sc.meshes:
                if m.is_watertight and m.contains(cand).any():
                    return True
                if trimesh.proximity.closest_point(m, cand)[1].min() < r:
                    return True
    return False


def screws():
    """{after step index: [(what, head point, axis)]}: the screws that must come out before
    that step, with their heads' tops and the direction a key comes from."""
    brow = []
    for side, sx in (("left", 1.0), ("right", -1.0)):
        for c in B.bracket_mounts():
            h = np.array([sx * c[0], c[1], c[2] + P.BROW_MOUNT_T + P.SERVICE_HEAD_H])
            brow.append((f"{side} brow flange screw at ({h[0]:.0f}, {h[1]:.0f})", h, (0.0, 0.0, 1.0)))
    import skull as SK
    _, z1 = SK.shelf_z()
    shelf = [(f"shelf screw at ({x:.0f}, {y:.0f})", np.array([x, y, z1 + P.SERVICE_HEAD_H]), (0.0, 0.0, 1.0))
             for x, y, _ in SK.shelf_ledge_points(None)]
    return {1: brow, 2: shelf}


def main():
    units = load_units()
    clouds = {k: Cloud(v) for k, v in units.items()}
    issues, md = [], ["# M3 service check", "", f"Head scale {S}. Paths in mm in the head frame.", "",
                      "## Teardown, in order", "", "| step | moves | path | result |", "|---|---|---|---|"]
    gone = set()
    tools = screws()
    tool_rows = []
    for i, (what, moving, path) in enumerate(STEPS):
        static = [k for k in units if k not in gone and k not in moving]
        for name, head, axis in tools.get(i, ()):
            tool = "hex key"
            swing, mid = key_swing(head, axis, static, clouds)
            if swing < P.SERVICE_KEY_SWING:                         # too little headroom: a stubby key
                tool = "stubby hex key"
                swing, mid = key_swing(head, axis, static, clouds, P.SERVICE_STUBBY_KEY)
            ok = swing >= P.SERVICE_KEY_SWING
            tool_rows.append(f"| before: {what} | {name} | {tool} | {swing:.0f} deg"
                             + (f" round {mid:.0f} deg" if mid is not None and swing < 360 else "") + f" | {'ok' if ok else 'BLOCKED'} |")
            print(f"{tool} on the {name}: {swing:.0f} deg of swing")
            if not ok:
                issues.append(f"a {tool} on the {name} swings only {swing:.0f} deg (want {P.SERVICE_KEY_SWING:.0f})")
        r = move(moving, static, clouds, path)
        p = " -> ".join(f"({w[0]:.0f}, {w[1]:.0f}, {w[2]:.0f})" for w in path)
        res = "clear" if r is None else f"BLOCKED at {r[0]:.0f} mm by {r[1]} ({r[2]:.2f} deep at {np.round(r[3], 1).tolist()})"
        md.append(f"| {i + 1}. {what} | {', '.join(moving)} | {p} | {res} |")
        print(f"{i + 1}. {what}: {res}")
        if r is not None:
            issues.append(f"{what}: {res}")
        gone |= set(moving)
    md += ["", "## Alone, from the assembled head", "", "| part | path | result |", "|---|---|---|"]
    for what, moving, path in ALONE:
        static = [k for k in units if k not in moving]
        r = move(moving, static, clouds, path)
        res = "clear" if r is None else f"BLOCKED at {r[0]:.0f} mm by {r[1]}"
        md.append(f"| {what} | {path} | {res} |")
        print(f"{what}: {res}")
        if r is not None:
            issues.append(f"{what}: {res}")
    md += ["", f"## Tool access (L hex key: short arm {P.SERVICE_KEY[0]:.0f}, long arm {P.SERVICE_KEY[1]:.0f}; "
           f"stubby: short arm {P.SERVICE_STUBBY_KEY[0]:.0f}; clearance radius {P.SERVICE_KEY[2]:.1f})", "",
           "| when | screw | tool | clear swing | result |", "|---|---|---|---|---|"]
    md += tool_rows
    md += ["", "## Pending", ""] + [f"- {w}: {why}" for w, why in PENDING]
    md += ["", "## Issues", ""] + ([f"- {i}" for i in issues] or ["none"])
    out_dir = os.path.join(K.check_out(), "service")
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, "service.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(md) + "\n")
    for w, why in PENDING:
        print(f"pending  {w}: {why}")
    print()
    for i in issues:
        print("WARN ", i)
    print("\nSERVICE OK" if not issues else f"\nSERVICE: {len(issues)} issue(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())

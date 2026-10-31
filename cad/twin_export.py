"""
Frank's digital twin model (perform/, PLAN D32): Cogley's head a2.0.33 as one GLB with a node
per moving body, and the linkage that moves those bodies from the servo horn angles, for the
twin page (perform/twin/). Reference geometry from his Patreon CAD: keep it private, never
publish it (no claude.ai artifact, no public remote).

Every servo is a crank: its horn turns about the servo's output shaft by the horn angle (CCW
seen from the shaft end for a growing pulse, the SG90 / MG90S / MG996R datasheet direction).
The rest of each mechanism follows from pins found on his parts (the shoulder screws, and the
holes in sections through the levers):
  jaw      both MG996R horns are bolted to the jaw arms (JawLink, Part 33), which are bolted to
           JawBase: the jaw turns 1:1 with the horns about their shaft. With the horns as his
           CAD has them, his opening direction (JL 90 -> 50) drives the jaw shut, as the team
           found on the bench (2026-10-25, JAW_DIR -1 in cogley_mouth_main.py).
  lips     each lip plate hangs on two arms, a horn and an idler on a shoulder screw: a
           parallelogram, so the plate moves without turning. The lower lips ride on the jaw.
  corners  a five-bar per side: the corner piece is pinned to the lower corner horn and, through
           a link, to the upper corner horn; both servos together place it.
  tongue   a four-bar on the jaw: horn, push link, tongue lever on an M4 shoulder.
  eyes     tilt and pan are parallelograms (horn and eye arms both 17 mm): the eyes turn 1:1
           with the horns. Pan turns each eye about its own vertical axis, inside the tilt.
  lids     a four-bar per lid: horn 13.1, lever 42.6, lid arm 17.2, about the lid axis
           (x through y 1.7, z 212.4, the holes in the lids' inner ends).
  brows    each arm is a parallelogram (horn and idler, 12 mm); the TPU bar between the inner and
           the outer arm bends, drawn as a blend of the two arms' motions along the bar.
His export has the -x side of the EyeMech's levers and horns, and the -x brow horns, in other
places than the +x side (one lever twice), so the eyes' and the brows' -x halves are mirrored
from +x here. The mouth is used as exported.

Which servo is on which socket: the mouth from the assembly manual (MOUTH_SERVO) and his part
names; the eyes and brows from the slider window's labels (servo_controls.py), whose "your right"
(standing in front of the face) is -x here (see SERVOS). Body names use Frank's own sides, as the
face engine's channels do (lid_top_L: his left eye). His left is -x in this frame (right-handed,
face toward +y; Cogley's UpperLeftLip is there too), the mirror of CLAUDE.md's "+x is the
character's LEFT"; only the names differ, every servo is still addressed by its socket.

Run:  python cad/twin_export.py    (after cogley_head.py; face_mask.py and enclosure.py for the
                                     skin and enclosure layers)
  -> output/twin/frank.glb, output/twin/frank_rig.json
"""
import json
import os
import sys

import fast_simplification
import numpy as np
import trimesh

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import cadkit as K  # noqa: E402
import cogley_head as C  # noqa: E402
import geom as G  # noqa: E402

sys.stdout.reconfigure(encoding="utf-8")
P = K.params()
S = P.HEAD_SCALE
OUT = os.path.join(K.root(), "output", "twin")
X = [1.0, 0.0, 0.0]
Z = [0.0, 0.0, 1.0]

# triangles kept per part: the 2.0 M of his export is far more than a browser needs
FACES_MIN, FACES_PER_MM = 300, 40      # per part: FACES_MIN + FACES_PER_MM x its bounding diagonal
SKIN_FACES = 60000                     # the face mask (1.04 M as built)

# ---------------------------------------------------------------------------------- servos
# servo id -> (his part whose hole is the horn hub, shaft direction out of the servo, hub point,
# kind). Hub points are the horn screws' axes and the spline holes (2.46 mm) in his horns.
# Ids are the robot's (robots/frank/robot.json): mouth board servos by their MouthMaster.py
# names, eye board servos by firmware/README.md's names for board 2.
SERVOS = {
    "JL": ("jaw horn", [-1, 0, 0], [-49.0, -64.7, 171.7], "MG996R"),
    "JR": ("jaw horn", [1, 0, 0], [49.0, -64.7, 171.7], "MG996R"),
    "LUL": ("ULLLinkA#0", [-1, 0, 0], [-39.3, -14.3, 177.9], "MG90S"),
    "LUR": ("Part 35#0", [1, 0, 0], [40.3, -14.3, 177.9], "MG90S"),
    "LLL": ("Part 27#0", [-1, 0, 0], [-39.2, -23.6, 115.6], "MG90S"),
    "LLR": ("Part 38#0", [1, 0, 0], [40.3, -24.1, 115.4], "MG90S"),
    "CUL": ("Part 31#0", [-1, 0, 0], [-49.4, -46.8, 168.0], "MG90S"),
    "CUR": ("Part 42#0", [1, 0, 0], [49.4, -46.8, 168.0], "MG90S"),
    "CLL": ("Part 32#0", [-1, 0, 0], [-46.8, -43.7, 150.8], "MG90S"),
    "CLR": ("Part 43#0", [1, 0, 0], [46.8, -43.7, 150.8], "MG90S"),
    "TON": ("Part 20#0", [1, 0, 0], [15.8, -54.3, 119.2], "MG90S"),
    "LR": ("CentralServoHorn#0", [0, 0, 1], [0.0, 1.6, 224.5], "MG90S"),
    "UD": ("VerticalHorn#0", [1, 0, 0], [14.2, -43.7, 212.4], "MG90S"),
    "TL": ("4xTopLidHorn#3", [1, 0, 0], [56.3, -43.7, 216.4], "MG90S"),     # +x eye, top lid
    "BL": ("4xTopLidHorn#1", [1, 0, 0], [56.3, -73.6, 208.4], "MG90S"),     # +x eye, bottom lid
    "TR": ("4xTopLidHorn#3~mx", [-1, 0, 0], [-56.3, -43.7, 216.4], "MG90S"),
    "BR": ("4xTopLidHorn#1~mx", [-1, 0, 0], [-56.3, -73.6, 208.4], "MG90S"),
    "LI": ("Part 3#2", [-1, 0, 0], [10.0, -9.8, 262.1], "MG90S"),            # +x brow, inner
    "LO": ("Part 3#3", [1, 0, 0], [67.2, -45.0, 262.3], "MG90S"),            # +x brow, outer
    "RI": ("Part 3#2~mx", [1, 0, 0], [-10.0, -9.8, 262.1], "MG90S"),
    "RO": ("Part 3#3~mx", [-1, 0, 0], [-67.2, -45.0, 262.3], "MG90S"),
}
# The eye board's L and R are as you stand in front of the face (servo_controls.py), and that
# viewer's right is -x in this frame (right-handed, face toward +y). Cogley's names agree: his
# UpperLeftLip and his "LEFT" brow servos (Brows.py) sit at -x / +x the same way. With these
# sides every check there is comes out with the datasheet direction (sign +1): the team's lid
# SHUT and OPEN poses (eye_poses.json), his brow raise directions (brow_anim.DIR), his smile,
# frown and tongue poses, and the jaw shutting on his JL 90 -> 50.

LID_AXIS = [0.0, 1.7, 212.4]         # the lids' pivot holes (y, z), eye tilt shares it
EYE_PIVOT_Y = 1.6                    # the eye adaptors' pivot holes
JAW_AXIS = [0.0, -64.7, 171.7]       # the MG996R shaft: centre of the four horn screws


def p(x, y, z):
    return [float(x), float(y), float(z)]


# ---------------------------------------------------------------------------------- the rig
def rig_spec():
    """(bodies, points): bodies in solve order; each {name, parts, motion, parent?, layer, role}.
    Points: {name: {"on": body, "at": xyz} or {"dyad": [a, b], "at": xyz, "normal", "frame"}}."""
    B, pts = [], {}

    def body(name, parts, motion, parent=None, role="link", layer="mech"):
        B.append(dict(name=name, parts=parts, motion=motion, parent=parent, role=role, layer=layer))

    def on(name, b, xyz):
        pts[name] = {"on": b, "at": list(map(float, xyz))}

    def dyad(name, a, b, xyz, frame=None):
        pts[name] = {"dyad": [a, b], "at": list(map(float, xyz)), "normal": X, "frame": frame}

    def horn(sid, parts, parent=None):
        _, shaft, hub, _ = SERVOS[sid]
        body(f"horn_{sid}", parts, {"type": "revolute", "origin": hub, "axis": shaft,
                                    "servos": [{"id": sid, "gain": 1.0}]}, parent=parent, role="horn")

    def link(name, parts, a, b, parent=None, role="link"):
        body(name, parts, {"type": "link", "a": a, "b": b, "normal": X}, parent=parent, role=role)

    # jaw: both horns bolted to it; jaw opening = chin down = negative about +x
    body("jaw", ["JawBase#0", "JawLink#0", "Part 33#0", "Component1#0", "MG996R v6#0", "Part 1#0", "Part 1#3",
                 "MG90s_servo_FIX v1(Mirror)#2", "MG90s_servo_FIX v1(Mirror)#7", "MG90s_servo_FIX v1(Mirror)#10"],
         {"type": "revolute", "origin": JAW_AXIS, "axis": X,
          "servos": [{"id": "JL", "gain": -1.0}, {"id": "JR", "gain": 1.0}]}, role="jaw")

    # upper lips (on the frame): horn arm + idler arm, plate on both
    for side, sid, hornp, idler, plate, pa, pb, piv in (
            ("L", "LUL", "ULLLinkA#0", "ULLLinkB#0", "UpperLeftLip#0", p(-39.8, -1.0, 174.7), p(-39.8, -1.0, 162.7),
             p(-33.6, -14.3, 166.0)),
            ("R", "LUR", "Part 35#0", "Part 36#0", "Part 34#0", p(40.8, -1.0, 174.7), p(40.8, -1.0, 162.7),
             p(34.6, -14.3, 166.0))):
        horn(sid, [hornp])
        on(f"lipU{side}_a", f"horn_{sid}", pa)
        on(f"lipU{side}_pivot", "frame", piv)
        dyad(f"lipU{side}_b", f"lipU{side}_a", f"lipU{side}_pivot", pb)
        link(f"idlerU{side}", [idler], f"lipU{side}_pivot", f"lipU{side}_b")
        link(f"lipU{side}", [plate], f"lipU{side}_a", f"lipU{side}_b", role="plate")

    # lower lips (on the jaw)
    for side, sid, hornp, idler, plate, pa, pb, piv in (
            ("L", "LLL", "Part 27#0", "Part 28#0", "LowerLeftLip#0", p(-37.7, -10.5, 118.7), p(-37.8, -10.5, 130.7),
             p(-34.3, -23.5, 127.5)),
            ("R", "LLR", "Part 38#0", "Part 39#0", "Part 37#0", p(38.8, -11.0, 118.4), p(38.8, -10.9, 130.3),
             p(35.3, -24.0, 127.3))):
        horn(sid, [hornp], parent="jaw")
        on(f"lipD{side}_a", f"horn_{sid}", pa)
        on(f"lipD{side}_pivot", "jaw", piv)
        dyad(f"lipD{side}_b", f"lipD{side}_a", f"lipD{side}_pivot", pb, frame="jaw")
        link(f"idlerD{side}", [idler], f"lipD{side}_pivot", f"lipD{side}_b", parent="jaw")
        link(f"lipD{side}", [plate], f"lipD{side}_a", f"lipD{side}_b", parent="jaw", role="plate")

    # corners (on the frame): five-bar
    for side, up, lo, h_up, h_lo, linkp, corner, p_up, p_lo, p_mid in (
            ("L", "CUL", "CLL", "Part 31#0", "Part 32#0", "Part 30#0", "Part 29#0",
             p(-50.4, -36.1, 177.8), p(-47.8, -29.9, 138.3), p(-44.9, -12.4, 146.1)),
            ("R", "CUR", "CLR", "Part 42#0", "Part 43#0", "Part 41#0", "Part 40#0",
             p(50.4, -36.1, 177.8), p(47.8, -29.7, 138.5), p(42.7, -12.3, 146.3))):
        horn(up, [h_up])
        horn(lo, [h_lo])
        on(f"corner{side}_up", f"horn_{up}", p_up)
        on(f"corner{side}_lo", f"horn_{lo}", p_lo)
        dyad(f"corner{side}_mid", f"corner{side}_lo", f"corner{side}_up", p_mid)
        link(f"cornerlink{side}", [linkp], f"corner{side}_up", f"corner{side}_mid")
        link(f"corner{side}", [corner], f"corner{side}_lo", f"corner{side}_mid", role="plate")

    # tongue (on the jaw): four-bar
    horn("TON", ["Part 20#0"], parent="jaw")
    on("tongue_a", "horn_TON", p(15.8, -64.4, 132.5))
    on("tongue_pivot", "jaw", p(-4.4, -6.3, 120.0))
    dyad("tongue_b", "tongue_a", "tongue_pivot", p(-1.2, -16.4, 133.6), frame="jaw")
    link("tonguelink", ["Part 21#0"], "tongue_a", "tongue_b", parent="jaw")
    link("tongue", ["Part 19#0"], "tongue_pivot", "tongue_b", parent="jaw", role="plate")

    # eyes: tilt (both), then pan (each), 1:1 parallelograms
    ez = G.eye_z(S)
    horn("UD", ["VerticalHorn#0"])
    body("eye_tilt", [], {"type": "revolute", "origin": p(0, EYE_PIVOT_Y, ez), "axis": X,
                          "servos": [{"id": "UD", "gain": 1.0}]}, role="frame")
    on("tilt_horn", "horn_UD", p(11.7, -43.6, 229.5))
    on("tilt_frame", "eye_tilt", p(11.7, 1.7, 229.4))
    link("tiltlever", ["VerticalLever#0"], "tilt_horn", "tilt_frame")
    horn("LR", ["CentralServoHorn#0"])
    for side, sx, ball, adaptors in (("R", 1, "Component74#1", ["EyeAdaptor#0", "EyeAdaptor#1"]),
                                     ("L", -1, "Component74#0", ["EyeAdaptor#0~mx", "EyeAdaptor#1~mx"])):
        body(f"eye_{side}", [ball] + adaptors,
             {"type": "revolute", "origin": p(sx * P.EYE_SPACING / 2, EYE_PIVOT_Y, ez), "axis": Z,
              "servos": [{"id": "LR", "gain": 1.0}]}, parent="eye_tilt", role="eye")

    # lids: four-bar each, about the lid axis; -x mirrored from +x
    for side, sx, m in (("R", 1, ""), ("L", -1, "~mx")):
        for which, sid, hornp, lever, lid, h_pin, l_pin in (
                ("top", "TL" if sx > 0 else "TR", "4xTopLidHorn#3", "2xTopLidLever#1", "LidBR#1",
                 (-43.6, 229.5), (-1.0, 229.4)),
                ("bottom", "BL" if sx > 0 else "BR", "4xTopLidHorn#1", "2xBottomLidLever#0", "LidTR#0",
                 (-73.6, 195.35), (-1.0, 195.4))):
            n = f"lid_{which}_{side}"
            horn(sid, [hornp + m])
            on(f"{n}_h", f"horn_{sid}", p(sx * 53.9, *h_pin))
            on(f"{n}_pivot", "frame", p(sx * 37.7, LID_AXIS[1], LID_AXIS[2]))
            dyad(f"{n}_l", f"{n}_h", f"{n}_pivot", p(sx * 53.9, *l_pin))
            link(f"{n}_lever", [lever + m], f"{n}_h", f"{n}_l")
            link(n, [lid + m], f"{n}_pivot", f"{n}_l", role="lid")

    # brows: two parallelogram arms per side, the TPU bar bent between them
    for side, sx, m, inner, outer in (("R", 1, "", "LI", "LO"), ("L", -1, "~mx", "RI", "RO")):
        for which, sid, hornp, idler, arm, h_pin, i_piv, i_pin in (
                ("in", inner, "Part 3#2", "Part 2#3", "Part 8#0", (2.2, 261.8), (-9.8, 278.1), (2.2, 277.8)),
                ("out", outer, "Part 3#3", "Part 2#1", "Part 9#0", (-33.0, 262.8), (-44.8, 278.2), (-33.3, 278.4))):
            n = f"brow{side}_{which}"
            xh = 12.0 if which == "in" else 64.1
            horn(sid, [hornp + m])
            on(f"{n}_h", f"horn_{sid}", p(sx * xh, *h_pin))
            on(f"{n}_pivot", "frame", p(sx * xh, *i_piv))
            dyad(f"{n}_i", f"{n}_h", f"{n}_pivot", p(sx * xh, *i_pin))
            link(f"{n}_idler", [idler + m], f"{n}_pivot", f"{n}_i")
            link(f"{n}_arm", [arm + m], f"{n}_h", f"{n}_i", role="brow")
        body(f"brow{side}_bar", ["Part 11#0" + m],
             {"type": "bend", "a": f"brow{side}_in_arm", "b": f"brow{side}_out_arm",
              "pa": p(sx * 23.8, 26.0, 249.0), "pb": p(sx * 70.5, -12.5, 236.8)}, role="brow")
    return B, pts


# ---------------------------------------------------------------------------------- parts
DROP = {  # his -x copies that are out of place; the mirrored +x parts replace them
    "4xTopLidHorn#0", "4xTopLidHorn#2", "2xTopLidLever#0", "2xBottomLidLever#1", "2xBottomLidLever#2",
    "LidTR#1", "LidBR#0", "Part 3#0", "Part 3#1", "Part 2#0", "Part 2#2", "Part 12#0", "Part 13#0", "Part 14#0"}
MIRROR_EXTRA = ["MG90s_servo_FIX v1(Mirror)#0", "MG90s_servo_FIX v1(Mirror)#1"]   # the 2 brow servos his export lacks

ROLE_COLOURS = {  # sRGB 0..1
    "frame": (0.42, 0.43, 0.46), "servo": (0.16, 0.33, 0.62), "horn": (0.95, 0.80, 0.22),
    "link": (0.92, 0.52, 0.20), "plate": (0.80, 0.27, 0.27), "jaw": (0.55, 0.50, 0.44),
    "eye": (0.95, 0.95, 0.92), "lid": (0.86, 0.68, 0.58), "brow": (0.36, 0.66, 0.40),
    "hardware": (0.70, 0.71, 0.74), "shell": (0.62, 0.66, 0.70), "skin": (0.55, 0.68, 0.52),
    "enclosure": (0.80, 0.80, 0.84)}


def mirror_x(mesh):
    m = mesh.copy()
    m.vertices[:, 0] *= -1
    m.invert()
    return m


def cluster(v, f, cell):
    """Vertex clustering: snap vertices to a grid of `cell` mm and drop the faces that collapse."""
    key = np.floor(v / cell).astype(np.int64)
    _, inv = np.unique(key, axis=0, return_inverse=True)
    inv = inv.ravel()
    nv = np.zeros((inv.max() + 1, 3))
    np.add.at(nv, inv, v)
    nv /= np.bincount(inv)[:, None]
    nf = inv[f]
    nf = nf[(nf[:, 0] != nf[:, 1]) & (nf[:, 1] != nf[:, 2]) & (nf[:, 0] != nf[:, 2])]
    _, first = np.unique(np.sort(nf, axis=1), axis=0, return_index=True)
    return nv, nf[np.sort(first)]


def decimate(mesh, keep=None):
    """At most about `keep` triangles (default from the part's size). Quadric decimation first; his
    vents and servos stall on their open edges, so vertex clustering finishes the job."""
    n = len(mesh.faces)
    keep = keep or int(FACES_MIN + FACES_PER_MM * float(np.linalg.norm(mesh.extents)))
    if n <= keep * 1.2:
        return mesh
    v, f = fast_simplification.simplify(mesh.vertices.astype(np.float32), mesh.faces.astype(np.int32),
                                        target_reduction=1.0 - keep / n)
    v, f = v.astype(np.float64), f.astype(np.int64)
    cell = float(np.linalg.norm(mesh.extents)) / 400
    while len(f) > keep * 1.5:
        v2, f2 = cluster(v, f, cell)
        if len(f2) <= keep * 1.5 or cell > 2.0:
            v, f = v2, f2
            break
        cell *= 1.4
    return trimesh.Trimesh(v, f, process=True)


def screw_tip(mesh):
    """The threaded end of a screw: the end of its long axis where the radius is smaller."""
    v = mesh.vertices
    cen = v.mean(axis=0)
    _, vec = np.linalg.eigh(np.cov((v - cen).T))
    ax = vec[:, 2]
    t = (v - cen) @ ax
    r = np.linalg.norm((v - cen) - np.outer(t, ax), axis=1)
    hi, lo = r[t > np.percentile(t, 80)].mean(), r[t < np.percentile(t, 20)].mean()
    return cen + ax * (t.min() if hi > lo else t.max())


def his_parts():
    """{label: (group, mesh)} with the out-of-place -x parts dropped and the mirrors added."""
    out = {}
    for name, inst, group, mesh in C.load():
        out[f"{name}#{inst}"] = (group, mesh)
    for lab in ["4xTopLidHorn#3", "4xTopLidHorn#1", "2xTopLidLever#1", "2xBottomLidLever#0", "LidBR#1", "LidTR#0",
                "EyeAdaptor#0", "EyeAdaptor#1", "Part 3#2", "Part 3#3", "Part 2#3", "Part 2#1", "Part 8#0",
                "Part 9#0", "Part 11#0"] + MIRROR_EXTRA:
        g, m = out[lab]
        out[lab + "~mx"] = (g, mirror_x(m))
    for lab in DROP:
        out.pop(lab, None)
    return out


def assign(parts, bodies):
    """{label: body name}: listed parts to their body, servos on the frame, every screw to the body of
    the part its tip sits in, everything else to the frame (or the shell layer)."""
    owner = {}
    for b in bodies:
        for lab in b["parts"]:
            if lab not in parts:
                raise KeyError(f"rig part {lab} not in his export")
            owner[lab] = b["name"]
    solid = [(lab, m) for lab, (g, m) in parts.items() if g != "hardware"]
    samples = {lab: trimesh.sample.sample_surface(m, 2000, seed=1)[0] for lab, m in solid}
    from scipy.spatial import cKDTree
    trees = {lab: cKDTree(s) for lab, s in samples.items()}
    for lab, (g, m) in parts.items():
        if lab not in owner and g != "hardware":
            owner[lab] = "shell" if g == "shell" else "frame"
    for lab, (g, m) in parts.items():
        if g == "hardware":
            tip = screw_tip(m)
            owner[lab] = owner[min(trees, key=lambda k: trees[k].query(tip)[0])]
    return owner


def role_of(lab, group, body_role):
    if group == "hardware":
        return "hardware"
    if lab.startswith(("MG90s", "SG90", "Component2")):
        return "servo"
    return body_role


# ---------------------------------------------------------------------------------- export
def layer_meshes():
    """Static extra layers: [(layer, label, mesh)]: the skin (the face mask) and the enclosure."""
    out = []
    d = K.stl_dir()
    fm = os.path.join(d, "face_mask.stl")
    if os.path.exists(fm):
        out.append(("skin", "face_mask", trimesh.load(fm, force="mesh")))
    for f in sorted(os.listdir(d)):
        if f.startswith(("enc_", "neck")) and f.endswith(".stl"):
            out.append(("enclosure", f[:-4], trimesh.load(os.path.join(d, f), force="mesh")))
    return out


def main():
    bodies, points = rig_spec()
    parts = his_parts()
    owner = assign(parts, bodies)
    roles = {b["name"]: b["role"] for b in bodies}
    roles.update(frame="frame", shell="shell")
    layers = {b["name"]: b["layer"] for b in bodies}
    layers.update(frame="mech", shell="shell")
    scene = trimesh.Scene()
    node_of = {}
    for name in ["frame", "shell"] + [b["name"] for b in bodies]:
        node_of[name] = f"body:{name}"
        scene.graph.update(frame_from=scene.graph.base_frame, frame_to=node_of[name])
    faces_in, faces_out, index = 0, 0, []
    for lab in sorted(parts, key=lambda k: (owner[k], k)):
        group, mesh = parts[lab]
        faces_in += len(mesh.faces)
        m = decimate(mesh)
        faces_out += len(m.faces)
        role = role_of(lab, group, roles[owner[lab]])
        rgb = ROLE_COLOURS[role]
        m.visual = trimesh.visual.TextureVisuals(material=trimesh.visual.material.PBRMaterial(
            baseColorFactor=[int(c * 255) for c in rgb] + [255], metallicFactor=0.05, roughnessFactor=0.75,
            name=role))
        node = f"part:{lab}"
        scene.add_geometry(m, node_name=node, geom_name=node, parent_node_name=node_of[owner[lab]])
        index.append({"part": lab, "body": owner[lab], "role": role})
    extra = []
    for layer, lab, mesh in layer_meshes():
        m = decimate(mesh, keep=SKIN_FACES if layer == "skin" else None)
        rgb = ROLE_COLOURS[layer]
        m.visual = trimesh.visual.TextureVisuals(material=trimesh.visual.material.PBRMaterial(
            baseColorFactor=[int(c * 255) for c in rgb] + [255], metallicFactor=0.0, roughnessFactor=0.9,
            name=layer))
        node = f"layer:{layer}:{lab}"
        scene.add_geometry(m, node_name=node, geom_name=node)
        extra.append({"part": lab, "layer": layer, "faces": len(m.faces)})
    os.makedirs(OUT, exist_ok=True)
    glb = trimesh.exchange.gltf.export_glb(scene, include_normals=False)
    with open(os.path.join(OUT, "frank.glb"), "wb") as fh:
        fh.write(glb)
    servos = {sid: {"part": part, "shaft": [float(a) for a in shaft], "hub": [float(a) for a in hub], "kind": kind}
              for sid, (part, shaft, hub, kind) in SERVOS.items()}
    rig = {
        "format": "perform-rig/1",
        "robot": "frank",
        "source": "Will Cogley, Robot Head a2.0.33 (Patreon): private reference geometry",
        "units": "mm", "up": Z, "front": [0.0, 1.0, 0.0],
        "model": "frank.glb",
        "servos": servos,
        "points": points,
        "bodies": [{k: b[k] for k in ("name", "parent", "motion", "role", "layer") if b[k] is not None}
                   for b in bodies],
        "static": {"frame": {"layer": "mech"}, "shell": {"layer": "shell"}},
        "layers": {"mech": "Mechanism", "shell": "Cogley's robot shell (our skin replaces it)",
                   "skin": "Face mask (does not move)", "enclosure": "Enclosure and neck"},
        "layers_on": ["mech"],
        "eye_centres": [[sx * P.EYE_SPACING / 2, 0.0, G.eye_z(S)] for sx in (1, -1)],
        # where each eye looks: a ray from its centre along +y, moved with its body
        "gaze": [{"body": f"eye_{side}", "from": [sx * P.EYE_SPACING / 2, 0.0, G.eye_z(S)], "dir": [0.0, 1.0, 0.0]}
                 for side, sx in (("R", 1), ("L", -1))],
        "parts": index, "extra": extra,
    }
    with open(os.path.join(OUT, "frank_rig.json"), "w", encoding="utf-8") as fh:
        json.dump(rig, fh, indent=1)
    by_body = {}
    for e in index:
        by_body[e["body"]] = by_body.get(e["body"], 0) + 1
    print(f"wrote {os.path.relpath(OUT, K.PROJECT)}/frank.glb ({len(glb) / 1e6:.1f} MB): {len(index)} parts, "
          f"{faces_in} -> {faces_out} triangles, {len(bodies)} moving bodies, {len(points)} pins; "
          f"layers: {', '.join(sorted({e['layer'] for e in extra}))}")
    print("parts per body: " + ", ".join(f"{k} {v}" for k, v in sorted(by_body.items())))
    return 0


if __name__ == "__main__":
    sys.exit(main())

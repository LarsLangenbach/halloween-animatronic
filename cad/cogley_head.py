"""
Will Cogley's Robot Head a2.0.33 (inputs/reference/head_a2.0.33, Patreon) as reference
meshes in our head frame: the base the head is now built on (PLAN D14).

Source: printing/reference_assembly.obj, Onshape's export of his main head assembly
(metres; +z up, the face toward -y, the eyes at about z 0). One mesh per OBJ group
instance, in mm, turned to face +y and moved so his eye centres (the eyeballs,
`Component74`, EYE_R behind their fronts) land on ours: (+-EYE_SPACING/2, 0, eye_z).

Each part gets a group:
  frame     SkullFrame: the structure everything mounts to (his plate "Frame - Main")
  extras    CheekBone, FanBracket ("Frame - Extras")
  shell     FrontPlate, FrontVent, RearPlate, RearVent: his robot face's outer shell
            ("Outer Shell"); our skin-support shell replaces it
  eyes      the EyeMech as he fits it (SG90 servos)
  mouth     the mouth module, its servos, teeth and tongue
  brows     his brow mechanism: 4 servos, flexible (TPU) brow bars Part 11 / Part 14
  hardware  screws, shoulder screws, washers, inserts

The export is not complete: only 2 of the 4 brow servos are in it. Parts are reference
geometry, not print files.

Run:  python cad/cogley_head.py  -> output/ref/head_a2/parts/*.stl, index.json
"""
import json
import os
import re
import sys

import numpy as np
import trimesh

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import cadkit as K  # noqa: E402
import geom as G  # noqa: E402

sys.stdout.reconfigure(encoding="utf-8")
P = K.params()
S = P.HEAD_SCALE
SRC = os.path.join(K.PROJECT, "inputs", "reference", "head_a2.0.33", "printing", "reference_assembly.obj")

FRAME = {"SkullFrame"}
EXTRAS = {"CheekBone", "FanBracket"}
SHELL = {"FrontPlate", "FrontVent", "RearPlate", "RearVent"}
EYES = {"SnapEyemech v20", "Base", "EyeCorePivotHolder", "EyeAdaptor", "LidTR", "LidBR", "2xBottomLidLever",
        "2xTopLidLever", "VerticalLever", "VerticalHorn", "CentralServoHorn", "4xTopLidHorn", "Component74",
        "LateralFrame", "SG90"}
BROWS = {"Part 2", "Part 3", "Part 4", "Part 8", "Part 9", "Part 11", "Part 12", "Part 13", "Part 14"}
HARDWARE = ("Hex socket", "M3 Shoulder", "M4 Shoulder", "Chamfered plain washer", "M4Insert")


def group_of(name, bounds_his):
    if name in FRAME:
        return "frame"
    if name in EXTRAS:
        return "extras"
    if name in SHELL:
        return "shell"
    if name in EYES:
        return "eyes"
    if name in BROWS:
        return "brows"
    if name.startswith(HARDWARE):
        return "hardware"
    if name.startswith("MG90s") and bounds_his[0][2] > 15.0:       # the brow servos sit above the eyes
        return "brows"
    return "mouth"


def read_obj(path):
    """[(group name, vertices (n, 3) in mm, faces (m, 3))] in his frame."""
    verts, groups, cur, faces = [], [], None, []
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            if line.startswith("v "):
                verts.append(line[2:].split()[:3])
            elif line.startswith("f "):
                idx = [int(t.split("/")[0]) for t in line[2:].split()]
                faces += [(idx[0], idx[k], idx[k + 1]) for k in range(1, len(idx) - 1)]
            elif line.startswith("g "):
                if cur is not None:
                    groups.append((cur, faces))
                cur, faces = line[2:].strip(), []
    if cur is not None:
        groups.append((cur, faces))
    V = np.array(verts, dtype=np.float64) * 1000.0                     # metres -> mm
    out = []
    for name, fl in groups:
        if not fl:
            continue
        F = np.array(fl, dtype=np.int64) - 1
        used = np.unique(F)
        remap = np.full(len(V), -1, dtype=np.int64)
        remap[used] = np.arange(len(used))
        out.append((name, V[used], remap[F]))
    return out


def to_ours_transform(raw):
    """(R, t): his frame -> ours. Turned 180 deg about z (face -y -> +y), his eye centre on ours."""
    eyes = [(v.min(axis=0), v.max(axis=0)) for n, v, _ in raw if n == "Component74"]
    c = np.mean([(lo + hi) / 2 for lo, hi in eyes], axis=0)
    front = min(lo[1] for lo, _ in eyes)
    his_eye = np.array([0.0, front + P.EYE_R, c[2]])
    R = np.diag([-1.0, -1.0, 1.0])
    return R, np.array([0.0, 0.0, G.eye_z(S)]) - R @ his_eye


def main():
    raw = read_obj(SRC)
    R, t = to_ours_transform(raw)
    out = os.path.join(G.ref_dir(), "head_a2")
    os.makedirs(os.path.join(out, "parts"), exist_ok=True)
    index, counts = [], {}
    for name, v, f in raw:
        bounds_his = [v.min(axis=0).tolist(), v.max(axis=0).tolist()]
        m = trimesh.Trimesh(v @ R.T + t, f, process=True)
        k = counts.get(name, 0)
        counts[name] = k + 1
        fn = f"{len(index):03d}_{re.sub(r'[^A-Za-z0-9]+', '_', name).strip('_')}_{k}.stl"
        m.export(os.path.join(out, "parts", fn))
        index.append({"name": name, "instance": k, "group": group_of(name, bounds_his), "file": fn,
                      "watertight": bool(m.is_watertight), "bounds": m.bounds.round(2).tolist()})
    with open(os.path.join(out, "index.json"), "w", encoding="utf-8") as fh:
        json.dump({"source": os.path.relpath(SRC, K.PROJECT), "R": R.tolist(), "t": t.tolist(), "parts": index},
                  fh, indent=1)
    n = {}
    for p in index:
        n[p["group"]] = n.get(p["group"], 0) + 1
    print(f"wrote {len(index)} parts to {os.path.relpath(out, K.PROJECT)}: "
          + ", ".join(f"{g} {c}" for g, c in sorted(n.items())))
    print(f"his eye centre -> ours: R diag {np.diag(R).tolist()}, t {np.round(t, 2).tolist()}")
    return 0


def load(groups=None):
    """[(name, instance, group, mesh)] from output/ref/head_a2, in our frame."""
    out = os.path.join(G.ref_dir(), "head_a2")
    with open(os.path.join(out, "index.json"), encoding="utf-8") as fh:
        idx = json.load(fh)["parts"]
    return [(p["name"], p["instance"], p["group"], trimesh.load(os.path.join(out, "parts", p["file"]), force="mesh"))
            for p in idx if groups is None or p["group"] in groups]


if __name__ == "__main__":
    sys.exit(main())

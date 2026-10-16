"""
Places Will Cogley's EyeMech and mouth assemblies (inputs/reference, read
only) in the head frame at HEAD_SCALE, using one rotation and one translation
per module from geom.py.

Writes one mesh per solid to output/ref/<module>/ and an index,
output/ref/modules.json, that records each solid's label, its role group, and
whether it is valid and watertight. These are reference meshes, not print
files: they never go into output/stl, and the folder is gitignored (the
models are Patreon-member files).

Groups say what each solid must stay inside (see layout_check.py):
  eyes, lids   the visible eye: inside the outer skin
  lips         the lip plates: inside the skin's inner surface
  surfaces     tessellated surface parts in the mouth file: inside the skin's inner surface
  jaw, frame   everything else: inside the skull's inner surface

Run:  python cad/modules.py
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

FILES = {"eyemech": P.EYEMECH_FILE, "mouth": P.MOUTH_FILE}
GROUPS = {
    "eyemech": {"eyes": {"Component74"}, "lids": {"LidTR", "LidBR"}},
    # Part_34 / Part_37 are the mirrored upper / lower lip plates, Part_33 the
    # mirrored jaw link (matched by mirrored bounding boxes, 2026-10-15).
    "mouth": {"lips": {"UpperLeftLip", "LowerLeftLip", "Part_34", "Part_37"},
              "jaw": {"JawBase", "JawLink", "Part_33"}},
}
TOL, ANG = 0.1, 0.3          # tessellation: mm, rad


def group_of(module, label, is_shell):
    if is_shell:
        return "surfaces"
    for g, labels in GROUPS[module].items():
        if label in labels:
            return g
    return "frame"


def mesh_of(shape, tmp):
    """Mesh one solid. build123d's tessellate() trips over a face OCC leaves
    untriangulated, so this goes through export_stl (which skips such a face)
    and reloads the file; the watertight flag then shows any gap."""
    from build123d import export_stl
    export_stl(shape, tmp, tolerance=TOL, angular_tolerance=ANG)
    m = trimesh.load(tmp, force="mesh")
    m.merge_vertices()
    m.update_faces(m.nondegenerate_faces())
    m.remove_unreferenced_vertices()
    return m


def leaves(node):
    kids = list(getattr(node, "children", []) or [])
    if not kids:
        yield node
    for k in kids:
        yield from leaves(k)


def main():
    from build123d import import_step
    out = G.ref_dir()
    index, ok = [], True
    for module, rel in FILES.items():
        path = os.path.join(K.inputs(), rel)
        if not os.path.exists(path):
            print(f"FAIL  {module}: {path} missing")
            ok = False
            continue
        shape = import_step(path)
        mat = G.module_matrix(module, P.HEAD_SCALE)
        mdir = os.path.join(out, module)
        os.makedirs(mdir, exist_ok=True)
        n_invalid, n_open = 0, 0
        for i, leaf in enumerate(leaves(shape)):
            label = getattr(leaf, "label", "") or "unlabelled"
            is_shell = len(leaf.solids()) == 0
            valid = bool(leaf.is_valid)
            m = mesh_of(leaf, os.path.join(mdir, "_tmp.stl"))
            m.apply_transform(mat)
            name = f"{i:03d}_{re.sub(r'[^A-Za-z0-9_.-]', '_', label)}.stl"
            m.export(os.path.join(mdir, name))
            entry = dict(module=module, file=f"{module}/{name}", label=label,
                         group=group_of(module, label, is_shell), valid=valid,
                         watertight=bool(m.is_watertight), shell=is_shell)
            index.append(entry)
            if not valid:
                n_invalid += 1
                print(f"info  {module}: '{label}' is not a valid solid in the STEP")
            if not entry["watertight"] and not is_shell:
                n_open += 1
                print(f"info  {module}: '{label}' meshes open (not watertight)")
        os.remove(os.path.join(mdir, "_tmp.stl"))
        t = G.module_translation(module, P.HEAD_SCALE)
        groups = {}
        for e in index:
            if e["module"] == module:
                groups[e["group"]] = groups.get(e["group"], 0) + 1
        print(f"{module}: {sum(groups.values())} parts {groups}, rotate z {G.module_rot(module):.0f}, "
              f"translate ({t[0]:.1f}, {t[1]:.1f}, {t[2]:.1f}); {n_invalid} invalid, {n_open} open")
    y, z = G.jaw_axis(P.HEAD_SCALE)
    print(f"eye centres (+-{P.EYE_SPACING / 2:.1f}, 0, {G.eye_z(P.HEAD_SCALE):.1f}); "
          f"jaw axis y {y:.1f} z {z:.1f}; stomion {np.round(G.stomion(P.HEAD_SCALE), 1).tolist()}")
    with open(os.path.join(out, "modules.json"), "w", encoding="utf-8") as f:
        json.dump(dict(head_scale=P.HEAD_SCALE, parts=index), f, indent=1)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())

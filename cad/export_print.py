"""
Print-ready copies of the print files: every part in output/stl rotated into
its print pose (`print_rotate` in cad.yaml, the same rotation print_check
uses), dropped onto the bed (z = 0) and centred on x = y = 0, written to
output/print/<name>.stl. Drag these straight into the slicer; the parts in
output/stl stay in the assembled pose for the checks and the STEP export.

Run after the builders (or after check.py --accept):  python cad/export_print.py
"""
import glob
import os
import sys

import numpy as np
import trimesh

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import cadkit as K  # noqa: E402


def main():
    table = K.parts_table()
    out = os.path.join(K.PROJECT, "output", "print")
    os.makedirs(out, exist_ok=True)
    n = 0
    for path in sorted(glob.glob(os.path.join(K.stl_dir(), "*.stl"))):
        name = os.path.splitext(os.path.basename(path))[0]
        if name not in table:
            print(f"skip  {name}: not in cad.yaml parts")
            continue
        m = trimesh.load(path, force="mesh")
        for axis, deg in enumerate(table[name].get("print_rotate", [0, 0, 0])):
            if deg:
                m.apply_transform(trimesh.transformations.rotation_matrix(np.radians(deg), np.eye(3)[axis]))
        lo, hi = m.bounds
        m.apply_translation([-(lo[0] + hi[0]) / 2, -(lo[1] + hi[1]) / 2, -lo[2]])
        m.export(os.path.join(out, name + ".stl"))
        e = m.extents
        sup = "supports" if table[name].get("supports") else "no supports"
        print(f"wrote print/{name}.stl  {e[0]:.1f} x {e[1]:.1f} x {e[2]:.1f} mm, {sup}")
        n += 1
    print(f"{n} print-ready file(s) in output/print")
    return 0


if __name__ == "__main__":
    sys.exit(main())

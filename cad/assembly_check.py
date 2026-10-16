"""
Assembled parts must not overlap: boolean intersection volume of every pair
of parts that sit in their assembled place (`assembly` not false in cad.yaml's
`parts`). Faces that merely touch -- a lid resting on a rim -- give ~0 mm3;
anything over NOISE is a clash. Also reports the smallest gap between each
pair that is closer than NEAR (sampled surface distance, fixed seed).

This is the generic floor. Project-specific checks (insert walls, screw
engagement, fits per interface, mechanism pose sweeps) go in their own
scripts -- see references/verification.md in the code-cad skill.

Run:  python <source>/assembly_check.py [stl_dir]
"""
import glob
import itertools
import os
import sys
import warnings

import numpy as np
import trimesh

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import cadkit as K  # noqa: E402

warnings.filterwarnings("ignore", category=RuntimeWarning)   # trimesh: volume of an empty mesh
NOISE = 1.0        # mm3; boolean slivers below this are numerical noise
NEAR = 0.3         # mm; report pairs closer than this (FDM "clear" class minimum)
SAMPLES = 3000


def main(stl_dir):
    table = K.parts_table()
    parts = {}
    for path in sorted(glob.glob(os.path.join(stl_dir, "*.stl"))):
        name = os.path.splitext(os.path.basename(path))[0]
        if table.get(name, {}).get("assembly", True):
            parts[name] = trimesh.load(path)
    fails = 0
    for (a, ma), (b, mb) in itertools.combinations(parts.items(), 2):
        if not _boxes_touch(ma, mb):
            continue
        try:
            inter = trimesh.boolean.intersection([ma, mb], engine="manifold")
            vol = float(inter.volume) if inter is not None and len(inter.faces) else 0.0
        except Exception as e:                       # noqa: BLE001
            print(f"WARN  {a} / {b}: boolean failed ({e}); check by eye")
            continue
        if vol > NOISE:
            fails += 1
            print(f"FAIL  {a} / {b}: overlap {vol:.1f} mm3")
            continue
        pts, _ = trimesh.sample.sample_surface(ma, SAMPLES, seed=1)
        gap = float(np.abs(trimesh.proximity.signed_distance(mb, pts)).min())
        tag = "touch" if gap < 0.02 else ("near " if gap < NEAR else "ok   ")
        print(f"{'ok' if gap >= NEAR or gap < 0.02 else 'info':6s}{a} / {b}: overlap {vol:.2f} mm3, "
              f"closest {gap:.2f} mm ({tag.strip()})")
    print("\nNO OVERLAPS" if not fails else f"\n{fails} OVERLAP(S)")
    return 0 if not fails else 1


def _boxes_touch(ma, mb):
    return bool(np.all(ma.bounds[0] <= mb.bounds[1] + 0.5) and np.all(mb.bounds[0] <= ma.bounds[1] + 0.5))


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else K.stl_dir()))

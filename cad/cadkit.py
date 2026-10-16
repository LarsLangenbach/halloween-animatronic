"""
Shared helpers for the code-CAD toolkit: find the project (the folder that
holds cad.yaml), read the spec, resolve the paths every script uses, load the
params file, and write STL files that are cleaned and checked the same way
every time.

Every path can be overridden by an environment variable. check.py sets them
when it runs a script inside its private copy of the source:
  CAD_SPEC       path of cad.yaml
  CAD_ROOT       project root the script should treat as its own
  CAD_STL_DIR    where builders write STLs
  CAD_CHECK_OUT  where checks write reports and images
  CAD_INPUTS     inputs folder (components/ lives in it)
  CAD_PARAMS     the params.py to load
"""
import os
import runpy
import sys
import types

import yaml

HERE = os.path.dirname(os.path.abspath(__file__))

PRINTER_DEFAULTS = dict(
    bed=[256, 256, 256],     # mm; Bambu X1/P1/A1. Prusa MK4: 250 x 210 x 220
    nozzle=0.4,
    min_wall=0.8,            # two extrusion widths
    overhang_deg=45.0,       # from vertical
    ledge_w=3.0,             # one-sided overhangs this narrow print without support
    bridge_span=10.0,        # roofs held by walls all round print this far (PLA)
)


def find_spec():
    env = os.environ.get("CAD_SPEC")
    if env:
        return env
    d = HERE
    while True:
        p = os.path.join(d, "cad.yaml")
        if os.path.exists(p):
            return p
        parent = os.path.dirname(d)
        if parent == d:
            sys.exit(f"cad.yaml not found in {HERE} or any folder above it")
        d = parent


SPEC_PATH = find_spec()
PROJECT = os.path.dirname(SPEC_PATH)          # the real project root
_spec = None


def spec():
    global _spec
    if _spec is None:
        with open(SPEC_PATH, encoding="utf-8") as f:
            _spec = yaml.safe_load(f) or {}
    return _spec


def root():
    """Root the current run works in: the private copy under check.py, else the project."""
    return os.environ.get("CAD_ROOT", PROJECT)


def stl_dir():
    return os.environ.get("CAD_STL_DIR") or os.path.join(root(), spec().get("stl_dir", "output/stl"))


def check_out():
    return os.environ.get("CAD_CHECK_OUT") or os.path.join(PROJECT, spec().get("out", "output/check"))


def inputs():
    return os.environ.get("CAD_INPUTS") or os.path.join(PROJECT, spec().get("inputs", "inputs"))


def params():
    """The params file as a namespace of its UPPERCASE names (empty if there is none)."""
    path = os.environ.get("CAD_PARAMS") or (
        os.path.join(root(), spec()["params"]) if spec().get("params") else None)
    if not path or not os.path.exists(path):
        return types.SimpleNamespace()
    sys.path.insert(0, os.path.dirname(path))
    values = runpy.run_path(path)
    return types.SimpleNamespace(**{k: v for k, v in values.items() if k.isupper()})


def parts_table():
    return spec().get("parts", {}) or {}


def printer():
    return {**PRINTER_DEFAULTS, **(spec().get("printer") or {})}


def write_stl(shape, name, tolerance=0.05, angular_tolerance=0.2):
    """Tessellate a build123d or CadQuery shape to <stl_dir>/<name>.stl, then
    merge vertices, drop degenerate faces and report watertightness. Returns
    True if the mesh is watertight."""
    import trimesh
    out = stl_dir()
    os.makedirs(out, exist_ok=True)
    path = os.path.join(out, name + ".stl")
    if hasattr(shape, "val"):                         # CadQuery Workplane
        shape = shape.val()
    if type(shape).__module__.startswith("build123d"):
        from build123d import export_stl
        export_stl(shape, path, tolerance=tolerance, angular_tolerance=angular_tolerance)
    else:
        import cadquery as cq
        cq.exporters.export(cq.Workplane(obj=shape), path, tolerance=tolerance,
                            angularTolerance=angular_tolerance)
    m = trimesh.load(path)
    m.merge_vertices()
    m.update_faces(m.nondegenerate_faces())
    m.remove_unreferenced_vertices()
    m.export(path)
    ok = bool(m.is_watertight)
    size = " x ".join(f"{v:.1f}" for v in m.extents)
    print(f"wrote {name}.stl  {size} mm  watertight={ok}")
    return ok

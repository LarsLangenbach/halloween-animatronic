# Halloween Animatronic

A 3D-printed Halloween animatronic, modelled as code (build123d on
OpenCascade). Every part is a Python script, every dimension lives in
`cad/params.py`, and one command rebuilds and checks the whole model before
anything is printed.

The project brief is in [docs/BRIEF.md](docs/BRIEF.md).

## Layout

```
cad.yaml               what the check builds, checks and grades; printer settings
cad/params.py          every dimension (tagged DATASHEET / ASSUMPTION / MEASURED)
cad/<part>.py          one builder per part family
cad/check.py ...       the check toolkit (views, print check, overlap check, STEP export)
inputs/components/     manufacturer STEP models of bought parts + components.yaml
inputs/reference/      reference photos, sketches, meshes
output/stl/            print files (committed)
output/check/          check results and renders (not committed)
docs/                  brief, plan, print guide, assembly notes
```

## Setup (Windows)

Needs [uv](https://docs.astral.sh/uv/).

```
uv venv --python 3.12 .venv
uv pip install --python .venv\Scripts\python.exe build123d trimesh manifold3d rtree scipy vtk pillow pyyaml
```

## Check the model

```
.venv\Scripts\python.exe cad\check.py
```

This rebuilds every part in a private copy, checks overlaps and printability,
and writes `output/check/report.md` plus renders in `output/check/views/` and
`output/check/print_check.png`. Exit code 0 means every hard check passed.

- `--no-render` skips the renders (faster).
- `--accept` stores the current state as the baseline that later runs diff
  against. Run it only once a design is accepted.

## Print files

Each builder writes its STLs to `output/stl/` when run directly, e.g.
`.venv\Scripts\python.exe cad\test_coupon.py`. Print the calibration coupon
first: it picks the hole and insert sizes for your printer.

`.venv\Scripts\python.exe cad\export_step.py` writes one coloured STEP of the
whole assembly to `output/step/` for Fusion 360, FreeCAD or Onshape.

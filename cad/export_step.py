"""
One labelled, coloured STEP of the assembled model, for Fusion 360, FreeCAD,
Onshape or any other CAD viewer.

Calls parts() on every `build` step in cad.yaml's pipeline (the builder
convention: parts() returns {part name: shape}), keeps the parts that sit in
their assembled place (`assembly` not false in `parts`), colours them from the
same table, and writes one STEP. Uses build123d when it is installed,
otherwise CadQuery's Assembly.

Run:  python <source>/export_step.py  -> <out>/../step/<project>.step
"""
import importlib
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import cadkit as K  # noqa: E402

GREY = (0.7, 0.7, 0.7)


def collect():
    shapes = {}
    for step in K.spec().get("pipeline", []):
        if step.get("kind") != "build":
            continue
        mod = importlib.import_module(step["script"])
        if not hasattr(mod, "parts"):
            print(f"skip  {step['script']}.py has no parts() -- see the part template")
            continue
        shapes.update(mod.parts())
    return shapes


def main():
    table = K.parts_table()
    keep = {}
    for name, shape in collect().items():
        settings = table.get(name, {})
        if not settings.get("assembly", True):
            print(f"{name:16s} left out (not in its assembled place)")
            continue
        keep[name] = (shape.val() if hasattr(shape, "val") else shape, tuple(settings.get("colour", GREY)))
    if not keep:
        sys.exit("nothing to export")
    project = K.spec().get("project", "model").replace(" ", "_")
    out = os.path.join(os.path.dirname(K.check_out()), "step")
    os.makedirs(out, exist_ok=True)
    path = os.path.join(out, project + ".step")
    try:
        import build123d as bd
        children = []
        for name, (shape, rgb) in keep.items():
            s = bd.Solid(shape.wrapped) if shape.wrapped.ShapeType().name == "TopAbs_SOLID" \
                else bd.Compound(shape.wrapped)
            s.label, s.color = name, bd.Color(*rgb)
            children.append(s)
        bd.export_step(bd.Compound(children=children, label=project), path)
    except ImportError:
        import cadquery as cq
        assy = cq.Assembly(name=project)
        for name, (shape, rgb) in keep.items():
            assy.add(cq.Shape.cast(shape.wrapped), name=name, color=cq.Color(*rgb))
        assy.save(path)
    print(f"wrote {path} ({os.path.getsize(path) / 1e6:.1f} MB, {len(keep)} parts)")


if __name__ == "__main__":
    main()

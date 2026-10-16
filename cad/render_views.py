"""
Shaded views of the print files (VTK, offscreen), made to be looked at after
every change: front, right, back, left and bottom at one shared scale, a 3/4
view, and two sections -- y = 0 seen from the front and x = 0 seen from the
right -- with the cut edge drawn black, so wall thickness and the parts
inside show. Frame: +y = front, +z = up.

Colours, and which parts sit where they go in the assembly, come from `parts`
in cad.yaml; parts with `assembly: false` are left out.

print_check.py imports spec_parts(), colour(), surface_actor() and render()
from here: keep those signatures stable.

Run:  python <source>/render_views.py [stl_dir] [out_dir]
  defaults: the project's stl_dir -> <out>/views
  -> views.png (all eight on one sheet) + one PNG per view
"""
import glob
import os
import sys

import numpy as np
import vtk
from PIL import Image, ImageDraw, ImageFont
from vtkmodules.util.numpy_support import vtk_to_numpy

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import cadkit as K  # noqa: E402

TILE = 560
GREY = (0.7, 0.7, 0.7)               # parts not listed in the spec
# name: (camera direction from the model centre, view-up)
VIEWS = [
    ("front", (0, 1, 0), (0, 0, 1)),
    ("right", (1, 0, 0), (0, 0, 1)),
    ("back", (0, -1, 0), (0, 0, 1)),
    ("left", (-1, 0, 0), (0, 0, 1)),
    ("bottom", (0, 0, -1), (0, 1, 0)),
    ("three_quarter", (0.75, 1.0, 0.55), (0, 0, 1)),
    ("section_y0", (0, 1, 0), (0, 0, 1)),     # cut at y = 0, back half kept
    ("section_x0", (1, 0, 0), (0, 0, 1)),     # cut at x = 0, left half kept
]
SECTIONS = {"section_y0": 1, "section_x0": 0}   # view -> axis of the cut plane


def spec_parts():
    """{part name: settings} from `parts` in cad.yaml."""
    return K.parts_table()


def colour(settings):
    return tuple(settings.get("colour", GREY))


def load_parts(stl_dir):
    spec = spec_parts()
    parts = []
    for path in sorted(glob.glob(os.path.join(stl_dir, "*.stl"))):
        name = os.path.splitext(os.path.basename(path))[0]
        if not spec.get(name, {}).get("assembly", True):
            continue
        r = vtk.vtkSTLReader()
        r.SetFileName(path)
        r.Update()
        parts.append((name, r.GetOutput()))
    if not parts:
        sys.exit(f"no STLs in {stl_dir}")
    return parts


def bounds_of(polys):
    b = np.array([p.GetBounds() for p in polys])
    return np.array([b[:, 0].min(), b[:, 1].max(), b[:, 2].min(),
                     b[:, 3].max(), b[:, 4].min(), b[:, 5].max()])


def surface_actor(poly, rgb):
    n = vtk.vtkPolyDataNormals()
    n.SetInputData(poly)
    n.SetFeatureAngle(40)
    n.SplittingOn()
    m = vtk.vtkPolyDataMapper()
    m.SetInputConnection(n.GetOutputPort())
    a = vtk.vtkActor()
    a.SetMapper(m)
    pr = a.GetProperty()
    pr.SetColor(*rgb)
    pr.SetSpecular(0.25)
    pr.SetSpecularPower(30)
    pr.SetAmbient(0.12)
    pr.BackfaceCullingOff()
    return a


def line_actor(poly, rgb, width):
    m = vtk.vtkPolyDataMapper()
    m.SetInputData(poly)
    m.ScalarVisibilityOff()
    a = vtk.vtkActor()
    a.SetMapper(m)
    a.GetProperty().SetColor(*rgb)
    a.GetProperty().SetLineWidth(width)
    a.GetProperty().LightingOff()
    return a


def feature_edges(poly):
    f = vtk.vtkFeatureEdges()
    f.SetInputData(poly)
    f.BoundaryEdgesOn()
    f.FeatureEdgesOn()
    f.SetFeatureAngle(50)
    f.ManifoldEdgesOff()
    f.NonManifoldEdgesOff()
    f.Update()
    return f.GetOutput()


def axis_plane(axis):
    plane = vtk.vtkPlane()
    plane.SetOrigin(0, 0, 0)
    plane.SetNormal(*np.eye(3)[axis])
    return plane


def clip(poly, axis):
    """Keep the half on the negative side of the axis plane through 0."""
    c = vtk.vtkClipPolyData()
    c.SetInputData(poly)
    c.SetClipFunction(axis_plane(axis))
    c.InsideOutOn()
    c.Update()
    return c.GetOutput()


def cut(poly, axis):
    c = vtk.vtkCutter()
    c.SetInputData(poly)
    c.SetCutFunction(axis_plane(axis))
    c.Update()
    return c.GetOutput()


def render(actors, centre, direction, up, scale):
    ren = vtk.vtkRenderer()
    ren.SetBackground(1, 1, 1)
    ren.UseFXAAOn()
    for a in actors:
        ren.AddActor(a)
    kit = vtk.vtkLightKit()
    kit.AddLightsToRenderer(ren)
    cam = ren.GetActiveCamera()
    d = np.asarray(direction, float)
    d /= np.linalg.norm(d)
    cam.SetFocalPoint(*centre)
    cam.SetPosition(*(centre + d * 1000))
    cam.SetViewUp(*up)
    cam.ParallelProjectionOn()
    cam.SetParallelScale(scale)
    ren.ResetCameraClippingRange()

    win = vtk.vtkRenderWindow()
    win.SetOffScreenRendering(1)
    win.SetSize(TILE, TILE)
    win.AddRenderer(ren)
    win.Render()
    grab = vtk.vtkWindowToImageFilter()
    grab.SetInput(win)
    grab.SetInputBufferTypeToRGB()
    grab.ReadFrontBufferOff()
    grab.Update()
    img = grab.GetOutput()
    w, h, _ = img.GetDimensions()
    arr = vtk_to_numpy(img.GetPointData().GetScalars()).reshape(h, w, 3)[::-1]
    win.Finalize()
    return Image.fromarray(np.ascontiguousarray(arr))


def main(stl_dir, out_dir):
    os.makedirs(out_dir, exist_ok=True)
    parts = load_parts(stl_dir)
    b = bounds_of([p for _, p in parts])
    size = b[1::2] - b[0::2]
    centre = (b[0::2] + b[1::2]) / 2
    scale = 0.55 * max(size)             # half-height of the view in mm, all views
    spec = spec_parts()

    tiles = []
    for name, direction, up in VIEWS:
        actors = []
        if name in SECTIONS:
            axis = SECTIONS[name]
            for pname, poly in parts:
                actors.append(surface_actor(clip(poly, axis), colour(spec.get(pname, {}))))
                actors.append(line_actor(cut(poly, axis), (0, 0, 0), 3))
        else:
            for pname, poly in parts:
                actors.append(surface_actor(poly, colour(spec.get(pname, {}))))
                actors.append(line_actor(feature_edges(poly), (0.2, 0.2, 0.2), 1))
        img = render(actors, centre, direction, up, scale)
        img.save(os.path.join(out_dir, f"{name}.png"))
        tiles.append((name, img))

    cols, head = 4, 40
    sheet = Image.new("RGB", (TILE * cols, TILE * 2 + head), "white")
    draw = ImageDraw.Draw(sheet)
    font = ImageFont.load_default(size=22)
    for i, (name, img) in enumerate(tiles):
        x, y = (i % cols) * TILE, (i // cols) * TILE + head
        sheet.paste(img, (x, y))
        draw.text((x + 10, y + 8), name, fill=(0, 0, 0), font=font)
    draw.text((10, 8), f"{K.spec().get('project', 'model')}: {', '.join(n for n, _ in parts)} | bbox "
                       f"{size[0]:.1f} x {size[1]:.1f} x {size[2]:.1f} mm (x, y, z) | "
                       f"same scale in every view, +y = front", fill=(0, 0, 0), font=font)
    path = os.path.join(out_dir, "views.png")
    sheet.save(path)
    print("wrote", path)


if __name__ == "__main__":
    stl_dir = sys.argv[1] if len(sys.argv) > 1 else K.stl_dir()
    out_dir = sys.argv[2] if len(sys.argv) > 2 else os.path.join(K.check_out(), "views")
    main(stl_dir, out_dir)

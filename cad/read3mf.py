"""
Read a Bambu Studio 3MF without lxml: every part of every object, named, with the plate
it sits on.

  parts(path) -> [{"plate": n, "plate_name": str, "object": str, "part": str, "mesh": trimesh}]

Bambu writes the meshes into 3D/Objects/*.model; 3D/3dmodel.model lists each object's
components (path, object id, transform), and Metadata/model_settings.config names the
objects and their parts and puts the objects on plates. Meshes are in the object's own
frame (component transforms applied, build transforms not), which is enough to measure
and compare parts.

Not in the pipeline: a reader used by the reference studies.
"""
import re
import zipfile
import xml.etree.ElementTree as ET

import numpy as np
import trimesh

NS = {"m": "http://schemas.microsoft.com/3dmanufacturing/core/2015/02",
      "p": "http://schemas.microsoft.com/3dmanufacturing/production/2015/06"}
P_PATH = "{http://schemas.microsoft.com/3dmanufacturing/production/2015/06}path"


def _transform(text):
    if not text:
        return np.eye(4)
    v = [float(x) for x in text.split()]
    m = np.eye(4)
    m[:3, :3] = np.array(v[:9]).reshape(3, 3)          # 3MF: row vectors, rotation then translation
    m[:3, 3] = v[9:12]
    m[:3, :3] = m[:3, :3].T
    return m


def _meshes(root):
    out = {}
    for obj in root.iter(f"{{{NS['m']}}}object"):
        mesh = obj.find("m:mesh", NS)
        if mesh is None:
            continue
        v = np.array([[float(e.get("x")), float(e.get("y")), float(e.get("z"))]
                      for e in mesh.find("m:vertices", NS)])
        f = np.array([[int(e.get("v1")), int(e.get("v2")), int(e.get("v3"))]
                      for e in mesh.find("m:triangles", NS)])
        out[obj.get("id")] = (v, f)
    return out


def parts(path):
    z = zipfile.ZipFile(path)
    files = {}
    for n in z.namelist():
        if n.endswith(".model"):
            files["/" + n] = _meshes(ET.fromstring(z.read(n)))
    main = ET.fromstring(z.read("3D/3dmodel.model"))
    comps = {}
    for obj in main.iter(f"{{{NS['m']}}}object"):
        cs = obj.find("m:components", NS)
        if cs is None:
            continue
        comps[obj.get("id")] = [(c.get(P_PATH) or "/3D/3dmodel.model", c.get("objectid"), _transform(c.get("transform")))
                                for c in cs.findall("m:component", NS)]
    cfg = z.read("Metadata/model_settings.config").decode("utf-8", "replace")
    names, part_names = {}, {}
    for oid, body in re.findall(r'<object id="(\d+)">(.*?)</object>', cfg, re.S):
        n = re.search(r'<metadata key="name" value="([^"]*)"', body)
        names[oid] = n.group(1) if n else oid
        part_names[oid] = re.findall(r'<part id="(\d+)"[^>]*>\s*<metadata key="name" value="([^"]*)"', body)
    plates = {}
    for i, pl in enumerate(re.findall(r"<plate>(.*?)</plate>", cfg, re.S)):
        pname = re.search(r'key="plater_name" value="([^"]*)"', pl)
        for oid in re.findall(r'key="object_id" value="(\d+)"', pl):
            plates[oid] = (i + 1, pname.group(1) if pname else "")
    out = []
    for oid, cl in comps.items():
        pn = dict(part_names.get(oid, []))
        for path_, sub, tf in cl:
            v, f = files[path_][sub]
            m = trimesh.Trimesh(v, f, process=True)
            m.apply_transform(tf)
            plate, plate_name = plates.get(oid, (0, ""))
            out.append({"plate": plate, "plate_name": plate_name, "object": names.get(oid, oid),
                        "part": pn.get(sub, names.get(oid, oid)), "mesh": m})
    return out

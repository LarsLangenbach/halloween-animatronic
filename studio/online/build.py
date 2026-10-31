"""
The studio online: builds a static copy of studio/ that runs entirely in the browser (Pyodide),
into output/frank-studio/, for its own Vercel project.

    .venv\\Scripts\\python.exe studio\\online\\build.py
    vercel deploy output/frank-studio --prod --yes --scope larzlarsenator-9296s-projects

It reuses frank/online's pieces (its file list for Frank's engine, the 3D twin with
twin_shim.js and its data) and adds the studio's page, its Python modules and shim.js. Online
there is no Claude key (the pre-written examples play) and no CAD upload (that needs build123d).

The twin's GLB is Will Cogley's Robot Head a2.0.33, shown publicly for NightHack as on
frank-face (Lars's decision, 2026-10-30). Deploy only this folder, never the repo root, and
never connect the Vercel project to Git: the repo holds Cogley's private CAD.
"""

import json
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
STUDIO = HERE.parent
ROOT = STUDIO.parent
OUT = ROOT / "output" / "frank-studio"
sys.path.insert(0, str(ROOT / "frank" / "online"))
import build as FB  # noqa: E402   (frank/online/build.py: python_files, twin_files, twin_data)

INJECT = ('<script src="https://cdn.jsdelivr.net/pyodide/v0.27.2/full/pyodide.js"></script>\n'
          '<script src="/studio/shim.js"></script>\n')
STUDIO_PY = ("runtime.py", "routes.py", "constraints.py", "library.py", "machine.py", "online/web.py")


def build(out=OUT):
    out.mkdir(parents=True, exist_ok=True)
    for old in out.iterdir():
        if old.name != ".vercel":
            shutil.rmtree(old) if old.is_dir() else old.unlink()

    page = (STUDIO / "web" / "index.html").read_text(encoding="utf-8")
    (out / "index.html").write_text(page.replace("</head>", INJECT + "</head>", 1), encoding="utf-8")
    shutil.copytree(STUDIO / "web", out / "studio", ignore=shutil.ignore_patterns("index.html"))
    shutil.copy2(HERE / "shim.js", out / "studio" / "shim.js")

    for src in FB.twin_files():
        dst = out / "twin" / src.relative_to(FB.TWIN)
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
    twin_page = out / "twin" / "index.html"
    twin_page.write_text(twin_page.read_text(encoding="utf-8").replace(
        "</head>", '<script src="/twin/shim.js"></script>\n</head>', 1), encoding="utf-8")
    shutil.copy2(FB.HERE / "twin_shim.js", out / "twin" / "shim.js")
    (out / "twin" / "data").mkdir()
    for name, src in FB.twin_data().items():
        shutil.copy2(src, out / "twin" / "data" / name)

    srcs = FB.python_files() + [STUDIO / f for f in STUDIO_PY]
    studio_data = ROOT / "robots" / "frank" / "studio"
    srcs += sorted(p for p in studio_data.rglob("*.json")) if studio_data.is_dir() else []
    srcs.append(FB.twin_data()["rig.json"])   # the Constraints page reads what each servo moves from it
    files = []
    for src in srcs:
        rel = src.relative_to(ROOT).as_posix()
        (out / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, out / rel)
        files.append(rel)
    (out / "files.json").write_text(json.dumps(files, indent=1), encoding="utf-8")
    return out


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    print(f"Built {build()}.")

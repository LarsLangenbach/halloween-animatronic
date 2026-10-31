"""
Frank online: builds the static face demo that Vercel serves, into output/online/.

    python frank/online/build.py
    vercel deploy output/online --prod --yes        (by hand; watch.py does it when the engine changes)

The page is frank/engine/preview.html with two script tags added in <head> (Pyodide from the
jsDelivr CDN, and browser.js, which runs the engine in the page and answers the page's requests
from browser.py), and its 3D twin pointed at /twin/ here instead of perform/body.py on
127.0.0.1:8810. The twin is perform/twin with twin_shim.js added, its data (robot.json, the rig
and the GLB cad/twin_export.py writes) under /twin/data/. The State machine tab is
frank/statechart/editor.html at /statechart/ with statechart_shim.js added. Pyodide gets the engine's packages
(PACKAGES: their .py and .json, not their tests) and the board models and mouth code the twin
needs (EXTRA), copied as they are now; watch.py rebuilds and deploys when any of them change.
performances.json holds the example prompts' pre-written performances (no key online); the
build warns about an example on the page that has none.

The GLB is Will Cogley's Robot Head a2.0.33, which his own page marks Public; Lars chose to show
it here for NightHack (2026-10-30), credited on the page. Everything else in inputs/reference/
stays private: deploy only output/online, never the repo root. The Vercel project link
(output/online/.vercel/) survives rebuilds.
"""

import json
import re
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).parent
FRANK = HERE.parent
ROOT = FRANK.parent
ENGINE = FRANK / "engine"
EDITOR = FRANK / "statechart" / "editor.html"
TWIN = ROOT / "perform" / "twin"
ROBOT = ROOT / "robots" / "frank" / "robot.json"
OUT = ROOT / "output" / "online"
PACKAGES = (ENGINE, FRANK / "statechart")
EXTRA = (ROOT / "perform" / "body.py", ROOT / "perform" / "boards.py", ROBOT, FRANK / "mouth.py",
         ROOT / "firmware" / "eye_poses.json", ROOT / "firmware" / "mouth_poses.json",
         HERE / "performances.json")
EXAMPLE = re.compile(r'class="anim-eg[^"]*">([^<]+)<')   # preview.html's example prompts
INJECT = ('<script src="https://cdn.jsdelivr.net/pyodide/v0.27.2/full/pyodide.js"></script>\n'
          '<script src="/browser.js"></script>\n')
TWIN_LOCAL = '"http://127.0.0.1:8810/?hero=1"'         # preview.html's default twin address
TWIN_HERE = '(location.origin + "/twin/index.html?hero=1")'


def python_files():
    """The files Pyodide gets: the packages' .py and .json (not tests), EXTRA, then browser.py."""
    files = []
    for pkg in PACKAGES:
        if pkg.is_dir():
            files += [p for p in sorted(pkg.rglob("*")) if p.suffix in (".py", ".json")
                      and not {"tests", "__pycache__"} & set(p.relative_to(pkg).parts)]
    return files + [p for p in EXTRA if p.exists()] + [HERE / "browser.py"]


def twin_data():
    """{name under /twin/data/: source}: robot.json, the rig, its GLB and the camera."""
    spec = json.loads(ROBOT.read_text(encoding="utf-8"))
    rig = (ROBOT.parent / spec["rig"]).resolve()
    data = {"robot.json": ROBOT, "rig.json": rig,
            "model.glb": rig.parent / json.loads(rig.read_text(encoding="utf-8"))["model"]}
    if spec.get("camera"):
        data["camera.json"] = (ROBOT.parent / spec["camera"]).resolve()
    return data


def twin_files():
    return [p for p in sorted(TWIN.rglob("*")) if p.is_file() and not p.name.startswith("test_")]


def sources():
    """Every file the site is built from."""
    return ([ENGINE / "preview.html", ENGINE / "face_draw.js", HERE / "browser.js", HERE / "twin_shim.js",
             EDITOR, HERE / "statechart_shim.js"]
            + python_files() + twin_files() + list(twin_data().values()))


def build(out=OUT):
    """Write the site. Returns its warnings (things that will not work on it)."""
    warnings = []
    out.mkdir(parents=True, exist_ok=True)
    for old in out.iterdir():
        if old.name != ".vercel":
            shutil.rmtree(old) if old.is_dir() else old.unlink()

    page = (ENGINE / "preview.html").read_text(encoding="utf-8")
    if "</head>" not in page:
        raise SystemExit("preview.html has no </head> to put the scripts before")
    if TWIN_LOCAL in page:
        page = page.replace(TWIN_LOCAL, TWIN_HERE)
    else:
        warnings.append(f"preview.html no longer has {TWIN_LOCAL}: the 3D twin stays off online")
    canned = json.loads((HERE / "performances.json").read_text(encoding="utf-8"))["performances"]
    key = lambda s: " ".join(s.lower().split()).rstrip(".!?")  # noqa: E731   (browser.prompt_key)
    for example in EXAMPLE.findall(page):
        if key(example) not in {key(k) for k in canned}:
            warnings.append(f"no performance in performances.json for the example {example.strip()!r}: "
                            "online it says 'not available'")
    (out / "index.html").write_text(page.replace("</head>", INJECT + "</head>", 1), encoding="utf-8")
    shutil.copy2(ENGINE / "face_draw.js", out / "face_draw.js")
    shutil.copy2(HERE / "browser.js", out / "browser.js")

    for src in twin_files():
        dst = out / "twin" / src.relative_to(TWIN)
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
    twin_page = out / "twin" / "index.html"
    text = twin_page.read_text(encoding="utf-8")
    twin_page.write_text(text.replace("</head>", '<script src="/twin/shim.js"></script>\n</head>', 1),
                         encoding="utf-8")
    shutil.copy2(HERE / "twin_shim.js", out / "twin" / "shim.js")
    (out / "twin" / "data").mkdir()
    for name, src in twin_data().items():
        shutil.copy2(src, out / "twin" / "data" / name)

    (out / "statechart").mkdir()
    editor = EDITOR.read_text(encoding="utf-8")
    if "</head>" not in editor:
        raise SystemExit("editor.html has no </head> to put its shim before")
    (out / "statechart" / "index.html").write_text(
        editor.replace("</head>", '<script src="/statechart/shim.js"></script>\n</head>', 1), encoding="utf-8")
    shutil.copy2(HERE / "statechart_shim.js", out / "statechart" / "shim.js")

    files = []
    for src in python_files():
        rel = src.relative_to(ROOT).as_posix()
        (out / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, out / rel)
        files.append(rel)
    (out / "files.json").write_text(json.dumps(files, indent=1), encoding="utf-8")
    return warnings


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    for w in build():
        print("warning:", w)
    print(f"Built {OUT}.")

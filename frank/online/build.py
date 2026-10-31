"""
Frank online: builds the static face demo that Vercel serves, into output/online/.

    python frank/online/build.py
    vercel deploy output/online --prod --yes        (by hand; watch.py does it when the engine changes)

The page is frank/engine/preview.html, unchanged except for two script tags in <head>:
Pyodide (from the jsDelivr CDN) and browser.js, which runs the engine in the page and answers
the page's requests from browser.py. The engine's packages (PACKAGES: their .py and .json,
not their tests) are copied as they are now; watch.py rebuilds and deploys when they change.

Deploy only output/online, never the repo root: inputs/reference/ holds Will Cogley's
Patreon CAD, which must not be uploaded anywhere. The Vercel project link
(output/online/.vercel/) survives rebuilds.
"""

import json
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).parent
FRANK = HERE.parent
ENGINE = FRANK / "engine"
OUT = FRANK.parent / "output" / "online"
PACKAGES = (ENGINE, FRANK / "statechart")
INJECT = ('<script src="https://cdn.jsdelivr.net/pyodide/v0.27.2/full/pyodide.js"></script>\n'
          '<script src="/browser.js"></script>\n')


def python_files():
    """The files Pyodide gets: the packages' .py and .json (not tests), then browser.py."""
    files = []
    for pkg in PACKAGES:
        if pkg.is_dir():
            files += [p for p in sorted(pkg.rglob("*")) if p.suffix in (".py", ".json")
                      and not {"tests", "__pycache__"} & set(p.relative_to(pkg).parts)]
    return files + [HERE / "browser.py"]


def sources():
    """Every file the site is built from."""
    return [ENGINE / "preview.html", ENGINE / "face_draw.js", HERE / "browser.js"] + python_files()


def build(out=OUT):
    out.mkdir(parents=True, exist_ok=True)
    for old in out.iterdir():
        if old.name != ".vercel":
            shutil.rmtree(old) if old.is_dir() else old.unlink()

    page = (ENGINE / "preview.html").read_text(encoding="utf-8")
    if "</head>" not in page:
        raise SystemExit("preview.html has no </head> to put the scripts before")
    (out / "index.html").write_text(page.replace("</head>", INJECT + "</head>", 1), encoding="utf-8")
    shutil.copy2(ENGINE / "face_draw.js", out / "face_draw.js")
    shutil.copy2(HERE / "browser.js", out / "browser.js")

    files = []
    for src in python_files():
        rel = src.relative_to(FRANK.parent).as_posix()
        (out / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, out / rel)
        files.append(rel)
    (out / "files.json").write_text(json.dumps(files, indent=1), encoding="utf-8")
    return files


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    files = build()
    print(f"Built {OUT} (index.html, face_draw.js, browser.js and {len(files)} Python and JSON files).")

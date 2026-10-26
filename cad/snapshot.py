"""
Save the current check images into process_images/, the project's permanent
picture record. output/check is overwritten by every run and is not
committed; process_images/ is committed and only grows.

Each snapshot is a folder process_images/<date>_<nn>_<label>/ holding every
image the last check produced (design views, print check, layout sheet and
tiles, sweep images) plus layout.md when there is one, and one line in
process_images/README.md.

Run:  python cad/snapshot.py <label> --note "one line on what the images show"
      [--from <check output folder>] [--date YYYY-MM-DD] [--main <file the index links to>]
"""
import argparse
import datetime
import glob
import os
import re
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import cadkit as K  # noqa: E402

STALE_S = 900              # s: images older than report.md by more than this are from an earlier run
SOURCES = ["views/views.png", "print_check.png", "layout/layout.png", "layout/layout_*.png",
           "layout/layout.md", "sweep/*.png", "sweep/sweep.md", "brow/*.png", "brow/brow.md",
           "studies/*.png", "studies/*.md", "skull/*.png", "skull/skull.md", "sculpt/*.png",
           "sculpt/sculpt.md", "service/service.md", "mold/*.png"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("label")
    ap.add_argument("--note", default="")
    ap.add_argument("--from", dest="src", default=K.check_out())
    ap.add_argument("--date", default=datetime.date.today().isoformat())
    ap.add_argument("--main", default="", help="file the index links to (default: the newest kind of sheet)")
    a = ap.parse_args()

    root = os.path.join(K.PROJECT, "process_images")
    os.makedirs(root, exist_ok=True)
    n = len([d for d in os.listdir(root) if os.path.isdir(os.path.join(root, d))]) + 1
    label = re.sub(r"[^A-Za-z0-9._-]+", "-", a.label).strip("-")
    name = f"{a.date}_{n:02d}_{label}"
    dest = os.path.join(root, name)
    os.makedirs(dest)
    report = os.path.join(a.src, "report.md")
    fresh_after = os.path.getmtime(report) - STALE_S if os.path.exists(report) else 0.0
    copied, stale = [], []
    for pattern in SOURCES:
        for f in sorted(glob.glob(os.path.join(a.src, pattern))):
            if os.path.getmtime(f) < fresh_after:
                stale.append(os.path.relpath(f, a.src))   # left over from an earlier run
                continue
            sub = os.path.dirname(os.path.relpath(f, a.src)).replace(os.sep, "_")
            base = os.path.basename(f)
            out = os.path.join(dest, base if not sub or base.startswith(sub) else f"{sub}_{base}")
            shutil.copy2(f, out)
            copied.append(os.path.basename(out))
    for f in stale:
        print(f"skipped {f}: older than the last check's report")
    if not copied:
        os.rmdir(dest)
        sys.exit(f"no check images found in {a.src}; run cad/check.py first")

    index = os.path.join(root, "README.md")
    if not os.path.exists(index):
        with open(index, "w", encoding="utf-8") as f:
            f.write("# Process images\n\nThe picture record of the build, oldest first. One folder per "
                    "snapshot, made with `python cad/snapshot.py <label> --note \"...\"` after a check.\n"
                    "The build log ([docs/BUILD_LOG.md](../docs/BUILD_LOG.md)) links here.\n\n")
    main_img = a.main if a.main in copied else next(
        (c for c in ("skull.png", "brow.png", "sweep.png", "layout.png", "views.png") if c in copied), copied[0])
    with open(index, "a", encoding="utf-8") as f:
        f.write(f"- **{name}**: {a.note or label} ([{main_img}]({name}/{main_img}), "
                f"{len(copied)} file(s))\n")
    print(f"saved {len(copied)} file(s) to process_images/{name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

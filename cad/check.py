"""
One command for the whole model check.

Copies the source folder into a private workspace, rebuilds every printed part
there, runs the checks listed in cad.yaml, grades the parts against its
targets, renders the views and lists what changed since the last accepted
run. It never writes to the project's STL folder, so it is safe to run while
someone else is working, and it always checks the current source, never a
stale STL.

Run:  python <source>/check.py [--no-render] [--accept]
  --no-render  skip the views
  --accept     if every hard item passed, store this run as the new baseline;
               do this when the human accepts the design state
  -> <out>/report.md, metrics.json, logs/, stl/, views/views.png
Exit code: 0 = every hard item passed, 1 = something hard failed.
"""
import argparse
import concurrent.futures
import datetime
import glob
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time

import trimesh

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import cadkit as K  # noqa: E402

ROOT = K.PROJECT
OUT = K.check_out()
SOURCE = os.path.relpath(HERE, ROOT)
TOOLKIT = {"cadkit", "check", "render_views", "print_check", "components_check", "assembly_check",
           "export_step"}
MAX_DIFF_LINES = 12


def baseline_path(spec):
    return os.path.join(ROOT, spec.get("baseline", os.path.join(SOURCE, "check_baseline.json")))


# ---------------------------------------------------------------------------
# private copy and pipeline
# ---------------------------------------------------------------------------
def make_work(spec):
    """Fresh copy of the source folder (plus `copy_also`) under <out>/work/<pid>.
    Copies left behind by a crashed run are removed once they are an hour old."""
    base = os.path.join(OUT, "work")
    os.makedirs(base, exist_ok=True)
    for old in glob.glob(os.path.join(base, "*")):
        if time.time() - os.path.getmtime(old) > 3600:
            shutil.rmtree(old, ignore_errors=True)
    work = os.path.join(base, str(os.getpid()))
    shutil.rmtree(work, ignore_errors=True)
    shutil.copytree(HERE, os.path.join(work, SOURCE),
                    ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "check_baseline.json"))
    for extra in spec.get("copy_also", []):
        src, dst = os.path.join(ROOT, extra), os.path.join(work, extra)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        (shutil.copytree if os.path.isdir(src) else shutil.copy2)(src, dst)
    os.makedirs(os.path.join(work, spec.get("stl_dir", "output/stl")), exist_ok=True)
    return work


def step_env(work, spec):
    env = dict(os.environ, PYTHONHASHSEED="0", PYTHONIOENCODING="utf-8", MPLBACKEND="Agg",
               CAD_SPEC=K.SPEC_PATH, CAD_ROOT=work,
               CAD_STL_DIR=os.path.join(work, spec.get("stl_dir", "output/stl")),
               CAD_CHECK_OUT=OUT, CAD_INPUTS=K.inputs())
    if spec.get("params"):
        env["CAD_PARAMS"] = os.path.join(work, spec["params"])
    return env


def normalise(lines, work):
    """Log lines without the run-specific folder, for diffing against the baseline."""
    variants = {work, work.replace("\\", "/"), os.path.realpath(work)}
    out = []
    for line in lines:
        for v in variants:
            line = line.replace(v, "<work>")
        out.append(line)
    return out


def run_script(work, spec, step):
    path = os.path.join(work, SOURCE, step["script"] + ".py")
    t0 = time.time()
    p = subprocess.run([sys.executable, path], cwd=work, env=step_env(work, spec),
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    text = (p.stdout + p.stderr).replace("\r", "")
    lines = normalise([l.rstrip() for l in text.splitlines()], work)
    ok = p.returncode == 0
    fails = [l.strip() for l in lines if re.search(step.get("fail", r"^\s*(FAIL|WARN)"), l)]
    if ok and step.get("pass") and not re.search(step["pass"], p.stdout.replace("\r", ""), re.M):
        ok = False
        fails.append(f"no line matching /{step['pass']}/ in the output")
    if not ok and not fails:
        fails = [l for l in lines if l.strip()][-5:]
    with open(os.path.join(OUT, "logs", step["script"] + ".txt"), "w", encoding="utf-8") as f:
        f.write(text)
    return dict(script=step["script"], kind=step["kind"], level=step.get("level", "hard"),
                ok=ok, exit=p.returncode, seconds=round(time.time() - t0, 1),
                fails=fails, log=lines)


def run_pipeline(work, spec, jobs=0):
    """Builds in order; consecutive checks in parallel (at most `jobs` at once, 0 = all). Stops after a failed build."""
    results, batch = [], []

    def flush():
        if batch:
            with concurrent.futures.ThreadPoolExecutor(min(jobs, len(batch)) if jobs > 0 else len(batch)) as pool:
                results.extend(pool.map(lambda s: run_script(work, spec, s), batch))
            batch.clear()

    for step in spec.get("pipeline", []):
        if step["kind"] == "check":
            batch.append(step)
            continue
        flush()
        r = run_script(work, spec, step)
        results.append(r)
        if not r["ok"]:
            return results, False
    flush()
    return results, True


# ---------------------------------------------------------------------------
# measuring and grading
# ---------------------------------------------------------------------------
def sha(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def measure(stl_dir, spec):
    parts = {}
    for path in sorted(glob.glob(os.path.join(stl_dir, "*.stl"))):
        name = os.path.splitext(os.path.basename(path))[0]
        m = trimesh.load(path)
        ext = m.bounds[1] - m.bounds[0]
        parts[name] = dict(
            watertight=bool(m.is_watertight),
            bodies=len(m.split(only_watertight=False)),
            volume=round(float(m.volume), 1),
            x=round(float(ext[0]), 2), y=round(float(ext[1]), 2), z=round(float(ext[2]), 2),
            bounds=[[round(float(v), 2) for v in row] for row in m.bounds],
            sha256=sha(path),
        )
    table = spec.get("parts", {}) or {}
    toy = [p for n, p in parts.items() if table.get(n, {}).get("assembly", True)]
    assembly = {}
    if toy:
        lo = [min(p["bounds"][0][i] for p in toy) for i in range(3)]
        hi = [max(p["bounds"][1][i] for p in toy) for i in range(3)]
        assembly = dict(x=round(hi[0] - lo[0], 2), y=round(hi[1] - lo[1], 2),
                        z=round(hi[2] - lo[2], 2), z_min=lo[2])
    return dict(parts=parts, assembly=assembly)


def metric(metrics, key):
    """'assembly.z' or 'part.lid.volume' -> value, or None."""
    bits = key.split(".")
    try:
        if bits[0] == "assembly":
            return metrics["assembly"][bits[1]]
        if bits[0] == "part":
            return metrics["parts"][bits[1]][bits[2]]
    except (KeyError, IndexError):
        pass
    return None


def grade(metrics, spec, params):
    items = []

    def add(id_, level, ok, measured, wanted, status="", note=""):
        items.append(dict(id=id_, level=level, ok=ok, measured=measured, wanted=wanted,
                          status=status, note=note))

    rules = spec.get("every_part", {}) or {}
    bed = K.printer()["bed"]
    for name, p in metrics["parts"].items():
        if "watertight" in rules:
            add(f"{name}.watertight", rules["watertight"], p["watertight"], p["watertight"], True)
        if "single_body" in rules:
            add(f"{name}.single_body", rules["single_body"], p["bodies"] == 1,
                f"{p['bodies']} bodies", "1 body")
        if "fits_bed" in rules:
            fits = all(a <= b for a, b in zip(sorted([p["x"], p["y"], p["z"]]), sorted(bed)))
            add(f"{name}.fits_bed", rules["fits_bed"], fits,
                f"{p['x']} x {p['y']} x {p['z']}", " x ".join(map(str, bed)))

    for t in spec.get("targets", []) or []:
        v = metric(metrics, t["metric"])
        target = getattr(params, t["param"], None) if "param" in t else t.get("target")
        if v is None or ("param" in t and target is None):
            add(t["id"], t.get("level", "soft"), False, "missing", t["metric"],
                t.get("status", ""), t.get("note", ""))
            continue
        ok, wanted = True, []
        if target is not None:
            tol = t.get("tol", 0.0)
            ok &= abs(v - target) <= tol
            wanted.append(f"{target} +/- {tol}" + (f" ({t['param']})" if "param" in t else ""))
        if "min" in t:
            ok &= v >= t["min"]
            wanted.append(f">= {t['min']}")
        if "max" in t:
            ok &= v <= t["max"]
            wanted.append(f"<= {t['max']}")
        add(t["id"], t.get("level", "soft"), ok, v, ", ".join(wanted),
            t.get("status", ""), t.get("note", ""))
    return items


# ---------------------------------------------------------------------------
# housekeeping checks and the baseline
# ---------------------------------------------------------------------------
def housekeeping(spec, metrics):
    warnings = []
    known = {s["script"] for s in spec.get("pipeline", [])} | set(spec.get("not_in_pipeline", []) or []) | TOOLKIT
    have = {os.path.splitext(os.path.basename(f))[0] for f in glob.glob(os.path.join(HERE, "*.py"))}
    warnings += [f"{SOURCE}/{s}.py is not in cad.yaml (add it to pipeline or not_in_pipeline)"
                 for s in sorted(have - known)]
    listed, built = set(spec.get("parts", {}) or {}), set(metrics["parts"])
    if listed:
        warnings += [f"{n}.stl is not in `parts` in cad.yaml (add its colour and print settings)"
                     for n in sorted(built - listed)]
        warnings += [f"`parts` lists {n}, but no {n}.stl was built (renamed or removed?)"
                     for n in sorted(listed - built)]
    repo_stl = os.path.join(ROOT, spec.get("stl_dir", "output/stl"))
    stale = [n for n, p in metrics["parts"].items()
             if not os.path.exists(os.path.join(repo_stl, n + ".stl"))
             or sha(os.path.join(repo_stl, n + ".stl")) != p["sha256"]]
    if stale:
        warnings.append(f"{spec.get('stl_dir', 'output/stl')} doesn't match the source for: "
                        + ", ".join(stale) + " (rebuild the print files before committing)")
    return warnings


def git_state():
    def git(*args):
        try:
            return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True,
                                  timeout=20).stdout.strip()
        except (OSError, subprocess.SubprocessError):
            return ""
    rev = git("rev-parse", "--short", "HEAD") or "no git"
    dirty = git("status", "--porcelain", "--", SOURCE, os.path.basename(K.SPEC_PATH))
    return rev + (" + uncommitted changes" if dirty else "")


def baseline_diff(spec, metrics, steps):
    path = baseline_path(spec)
    if not os.path.exists(path):
        return None, []
    with open(path, encoding="utf-8") as f:
        base = json.load(f)
    changes = []
    for key, now in metrics["assembly"].items():
        old = base["metrics"]["assembly"].get(key)
        if old is not None and abs(now - old) > 0.01:
            changes.append(f"assembly.{key}: {old} -> {now}")
    old_parts = base["metrics"]["parts"]
    for name, p in metrics["parts"].items():
        if name not in old_parts:
            changes.append(f"{name}: new part")
            continue
        o = old_parts[name]
        for k in ("x", "y", "z"):
            if abs(p[k] - o[k]) > 0.01:
                changes.append(f"{name}.{k}: {o[k]} -> {p[k]}")
        if abs(p["volume"] - o["volume"]) > max(0.5, 1e-4 * o["volume"]):
            pct = 100 * (p["volume"] - o["volume"]) / o["volume"]
            changes.append(f"{name}.volume: {o['volume']} -> {p['volume']} mm3 ({pct:+.2f} %)")
    for name in old_parts:
        if name not in metrics["parts"]:
            changes.append(f"{name}: part no longer built")
    for s in steps:
        old = base.get("logs", {}).get(s["script"])
        if old is None:
            continue
        gone = [l for l in old if l not in s["log"]]
        new = [l for l in s["log"] if l not in old]
        if gone or new:
            shown = [f"  - {l.strip()}" for l in gone[:MAX_DIFF_LINES // 2]]
            shown += [f"  + {l.strip()}" for l in new[:MAX_DIFF_LINES // 2]]
            more = len(gone) + len(new) - len(shown)
            changes.append(f"{s['script']} output changed:\n" + "\n".join(shown)
                           + (f"\n  ... {more} more" if more > 0 else ""))
    return base.get("accepted", "?") + ", " + base.get("git", "?"), changes


# ---------------------------------------------------------------------------
# report
# ---------------------------------------------------------------------------
def rel(path):
    return os.path.relpath(path, ROOT).replace("\\", "/")


def write_report(spec, state, steps, built, grades, warnings, base_info, changes, views):
    hard = [s for s in steps if not s["ok"] and s["level"] == "hard"]
    soft = [s for s in steps if not s["ok"] and s["level"] != "hard"]
    hard_g = [g for g in grades if not g["ok"] and g["level"] == "hard"]
    soft_g = [g for g in grades if not g["ok"] and g["level"] != "hard"]
    passed = built and not hard and not hard_g
    n_warn = len(soft_g) + len(warnings) + sum(len(s["fails"]) for s in soft)
    title = "PASS" if passed else "FAIL"
    when = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    name = spec.get("project", os.path.basename(ROOT))

    md = [f"# {name} check: {title}" + (f" ({n_warn} warning(s))" if n_warn else ""), "",
          f"{when}, source {state}", "", "## Hard failures", ""]
    if passed:
        md.append("none")
    for s in hard:
        md.append(f"- **{s['script']}** (exit {s['exit']}):")
        md += [f"  - {l}" for l in s["fails"][:20]]
    if not built:
        md.append("- the build stopped; later steps did not run")
    for g in hard_g:
        md.append(f"- **{g['id']}**: measured {g['measured']}, wanted {g['wanted']}"
                  + (f" ({g['note']})" if g["note"] else ""))
    md += ["", "## Warnings", ""]
    if not n_warn:
        md.append("none")
    for g in soft_g:
        md.append(f"- {g['id']}: measured {g['measured']}, wanted {g['wanted']}"
                  + (f" [{g['status']}]" if g["status"] else "")
                  + (f" ({g['note']})" if g["note"] else ""))
    md += [f"- {w}" for w in warnings]
    for s in soft:
        md.append(f"- {s['script']}:")
        md += [f"  - {l}" for l in s["fails"]]
    md += ["", "## Steps", "", "| step | kind | result | time |", "|---|---|---|---|"]
    for s in steps:
        res = "ok" if s["ok"] else ("FAIL" if s["level"] == "hard" else "warn")
        md.append(f"| {s['script']} | {s['kind']} | {res} | {s['seconds']} s |")
    md += ["", "## Targets", "", "| item | measured | wanted | level | result |", "|---|---|---|---|---|"]
    for g in grades:
        if "." in g["id"] and g["ok"]:
            continue                      # per-part health only listed when it fails
        md.append(f"| {g['id']} | {g['measured']} | {g['wanted']} | {g['level']}"
                  f"{' ' + g['status'] if g['status'] else ''} | {'ok' if g['ok'] else 'FAIL'} |")
    md += ["", "## Changed since the baseline", ""]
    if base_info is None:
        md.append("no baseline yet (run with --accept once the design state is accepted)")
    else:
        md += [f"baseline: {base_info}", ""] + ([f"- {c}" for c in changes] or ["nothing"])
    md += ["", "## Images", "", "- design views: " + (views or "not rendered")]
    pc = os.path.join(OUT, "print_check.png")
    if os.path.exists(pc):
        md.append(f"- printability: {rel(pc)} (red = needs support, blue = thin wall, green = bed contact)")
    md.append("")
    with open(os.path.join(OUT, "report.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(md))
    return passed, title, n_warn, hard, hard_g, soft


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--no-render", action="store_true")
    ap.add_argument("--accept", action="store_true")
    ap.add_argument("--jobs", type=int, default=0, help="run at most this many checks at once (0 = all; lower it when memory runs out)")
    args = ap.parse_args()

    spec = K.spec()
    os.makedirs(os.path.join(OUT, "logs"), exist_ok=True)
    for old in glob.glob(os.path.join(OUT, "logs", "*.txt")) + [os.path.join(OUT, "print_check.png")]:
        if os.path.exists(old):
            os.remove(old)
    state = git_state()
    t0 = time.time()

    work = make_work(spec)
    work_stl = os.path.join(work, spec.get("stl_dir", "output/stl"))
    steps, built = run_pipeline(work, spec, args.jobs)

    metrics, grades, warnings, views = dict(parts={}, assembly={}), [], [], ""
    if built:
        metrics = measure(work_stl, spec)
        os.environ.update({k: v for k, v in step_env(work, spec).items() if k.startswith("CAD_")})
        grades = grade(metrics, spec, K.params())
        warnings = housekeeping(spec, metrics)
        stl_keep = os.path.join(OUT, "stl")
        shutil.rmtree(stl_keep, ignore_errors=True)
        shutil.copytree(work_stl, stl_keep)
        if not args.no_render:
            vdir = os.path.join(OUT, "views")
            r = subprocess.run([sys.executable, os.path.join(HERE, "render_views.py"), stl_keep, vdir],
                               capture_output=True, text=True, encoding="utf-8", errors="replace",
                               env=dict(os.environ, CAD_SPEC=K.SPEC_PATH))
            if r.returncode == 0:
                views = rel(os.path.join(vdir, "views.png"))
            else:
                warnings.append("render_views.py failed: " + (r.stderr.strip().splitlines() or ["?"])[-1])
    base_info, changes = baseline_diff(spec, metrics, steps) if built else (None, [])

    passed, title, n_warn, hard, hard_g, soft = write_report(
        spec, state, steps, built, grades, warnings, base_info, changes, views)
    with open(os.path.join(OUT, "metrics.json"), "w", encoding="utf-8") as f:
        json.dump(dict(passed=passed, source=state, metrics=metrics, grades=grades,
                       steps=[{k: v for k, v in s.items() if k != "log"} for s in steps]), f, indent=1)
    shutil.rmtree(work, ignore_errors=True)

    print(f"check: {title}  ({len(hard) + len(hard_g)} hard failure(s), {n_warn} warning(s), "
          f"{time.time() - t0:.0f} s)")
    for s in hard:
        more = f" (+{len(s['fails']) - 1} more)" if len(s["fails"]) > 1 else ""
        print(f"  FAIL {s['script']}: " + (s["fails"][0] if s["fails"] else f"exit {s['exit']}") + more)
    for g in hard_g:
        print(f"  FAIL {g['id']}: measured {g['measured']}, wanted {g['wanted']}")
    for s in soft:
        print(f"  warn {s['script']}: {len(s['fails'])} item(s), see the report")
    if base_info is not None:
        print(f"  {len(changes)} change(s) since the baseline")
    print("  report:", rel(os.path.join(OUT, "report.md")))
    if views:
        print("  views: ", views)

    if args.accept:
        if not passed:
            print("not accepted: fix the hard failures first")
        else:
            with open(baseline_path(spec), "w", encoding="utf-8") as f:
                json.dump(dict(accepted=datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
                               git=state, metrics=metrics,
                               logs={s["script"]: s["log"] for s in steps}), f, indent=1)
            print("  baseline updated:", rel(baseline_path(spec)))
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())

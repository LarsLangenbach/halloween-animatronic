# Notes for Claude: Halloween animatronic (CAD project)

A 3D-printed Halloween animatronic. Parts are Python programs (build123d 0.13 on OpenCascade). Units mm and degrees. Frame: z = 0 on the bed / flat base, +z up, +y front, +x right.

A life-size Frankenstein head: a printed skull carrying Will Cogley's mouth mechanism and EyeMech ε3.2, two custom MG90S eyebrow mechanisms, and snap attachments for a cast silicone skin. Use the `code-cad` skill for all modelling work. Reference images go in `inputs/reference/`.

## Project documents (keep them current)
- `docs/BRIEF.md`: the client brief, verbatim. Never edit it; answers and changes go in the plan.
- `docs/PLAN.md`: the living build plan, covering milestone status, inputs, frame and datums, architecture, open questions (Q#), decisions (D#) and risks (R#). Update it whenever a milestone moves, a question is answered, a decision is made or an input arrives, and bump the plan version line when its structure changes.
- `docs/BUILD_LOG.md`: newest entry first, one entry per working session or physical test, in the format at its top. Add an entry before ending any session that changed the model, the plan or the physical build. Quote the check.py result line and link the renders.
- Read the plan's status table and the latest log entry at the start of every session.
- `process_images/`: the permanent picture record (committed; `output/check` is overwritten every run). After every check worth keeping (a new result, a decision, a fix the human will want to see), run `.venv\Scripts\python.exe cad\snapshot.py <label> --note "<plain one-liner>"`. Build log entries link to the snapshot folder, never to `output/check`. The human asked for every image to be kept (2026-10-15).

## Status
- Scaffolded 2026-10-14; plan v1 written. Cogley EyeMech and mouth STEP files are in `inputs/reference/` (surveyed in its README.md); the reference files are read-only. Non-ASCII file names break scripts on the Windows console, so keep names ASCII and call `sys.stdout.reconfigure(encoding="utf-8")` in scripts that print part labels. M1 layout running (2026-10-15): `modules.py` and `head.py` write reference meshes (Cogley modules, proxy head envelopes) to `output/ref/`, which is not `output/stl` and not print files. `reserve.py` writes the reserved volumes (brow bays, cable channel). `layout_check.py` checks the rest pose (fit table and renders in `output/check/layout/`). `pose_sweep.py` moves the jaw, eyes and lids and checks the reserved volumes (`output/check/sweep/`). M2: `brow.py` builds the eyebrow mechanism (shared maths in `browgeom.py`; the concept study is in `cad/studies/`), and `brow_check.py` runs both brows through their travel, hard stops and the bench rig (`brow_rig.py`) (`output/check/brow/`). M3: `skull.py` builds the skull pieces as meshes (manifold): wall = skin_inner − skull_inner, with openings from `normal_cutter()` (outline on the surface, extruded along the normal; no box cuts on curved walls: they leave slivers). `skull_check.py` checks it against everything, at rest and in motion. Envelopes are true offsets (`head.envelope`); `geom.front_y` and `geom.envelope_margin` follow them. Human-facing docs: `docs/PRINT_GUIDE.md`, `docs/BOM.md`, `docs/ASSEMBLY.md`; keep them current when parts change. `cad/export_print.py` writes slicer-ready STLs to `output/print/`. The standard `views.png` stays empty until the first assembled skull part exists, so look at `output/check/layout/layout.png` instead. Shared numbers live in `geom.py` (landmarks, sections, module placement); never recompute them in a builder.
- `cad.yaml` printer settings and the fasteners in params.py are ASSUMPTIONs until the plan's open questions name the printer, material and hardware.

## Environment
- Python is the project venv: `.venv\Scripts\python.exe` (uv, Python 3.12). Run checks with `.venv\Scripts\python.exe cad\check.py`.
- Add packages only after a `uv pip install --dry-run` against `.venv` (see the skill's setup.md). CadQuery is not installed; adding it alongside build123d needs the OCP override.

## Workflow
- Design numbers live in `cad/params.py` (tags DATASHEET / ASSUMPTION / MEASURED). Change numbers there, not in part code.
- After any change run the check. It rebuilds every part in a private copy, runs every check, grades `cad.yaml` and writes `output/check/report.md`, `views/views.png` and `print_check.png`. Exit 0 = every hard item passed. Read the report and look at the images before calling a change done.
- Builders: `parts()` returns `{name: shape}` in the assembled pose; running the file writes the STLs. A new builder or check goes into `pipeline` in `cad.yaml`; a new or renamed part goes into `parts` there.
- `check.py --accept` stores the accepted state as the baseline. Only run it when the human accepts the design.
- Rebuild the print files (each builder, then commit `output/stl`) before committing geometry; check.py warns when they are stale.
- Before telling the human a change is done, have the `cad-reviewer` agent look at it.
- Link every render in replies (workspace-relative markdown links) so the human can click through.

## Animatronic specifics
- Frame (plan §4): x = 0 facial midline, y = 0 plane through the eye centres, z = 0 underside of the neck interface; +x is the character's LEFT. Name parts by the character's side (`brow_L` at +x).
- Everything that moves (jaw, lips, eyes, lids, brows) gets a pose-sweep check per the skill's mechanisms.md: rest, each axis at ± its limit, the combined corners, and the clean limit with the first colliding pair named. Record the hard cap and a lower firmware soft limit in the docs.
- Servo horns and pivots bear on printed stubs or pins; screws only retain.
- Every servo, sensor, speaker and LED fixed in a shell ends in a connector, and the wiring through moving joints gets a planned path with slack.
- Manufacturer STEP models for servos and boards go in `inputs/components/` and are listed in `components.yaml` with source and licence.

## Git
- The repo must stay private. `inputs/reference/` holds Will Cogley's Patreon-member CAD; never push it to a public remote or share it.
- Stage your own files by name; never `git add -A` (another session may be working here).
- `output/check/` and `*.step` under output/ are not committed.

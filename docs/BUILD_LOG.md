# Build log

A dated record of every design session, test print and bench test for the
Frankenstein animatronic head. Newest entry first. The plan it works through
is [PLAN.md](PLAN.md); the brief is [BRIEF.md](BRIEF.md).

## How entries are written

One entry per working session or physical test. Use this shape, and leave out
any heading that has nothing under it:

```
## YYYY-MM-DD — <milestone> — <one-line summary>

**Done:** what changed, in a few bullets.
**Numbers:** params that changed, old → new (name = value), and why.
**Check:** the check.py result line, e.g. `check: PASS (0 hard failure(s), 1 warning(s), 31 s)`.
**Renders:** links to the views and print-check images looked at.
**Physical:** what was printed or tested, on which printer and material, and what was measured.
**Decisions:** decision IDs from PLAN.md that were made or changed, with the answer.
**Problems:** what went wrong or is still open.
**Next:** the next concrete step.
```

Rules:
- Record measured values with the param they replace, e.g. `MG90S_BODY_L = 22.8 (MEASURED, was 22.5 DATASHEET)`.
- Bench results override CAD. Record them with the date and the conditions (e.g. "brow travel 9.5 mm bare, 7.0 mm under the 4 mm silicone sample").
- Note every print that is kept as a reference part, so later changes to its params are known to break it.

---

## 2026-10-16 — M3 / M5 — Sculpt base; service paths for the back, the EyeMech and the brows

**Done:**
- **Sculpt base v1** (`cad/sculpt_base.py`, `cad/sculpt_check.py`), started early so the sculptor can begin (D13: normal proportions, whole head):
  - Its surface is the skull's outside raised by 3 mm (`SCULPT_MIN_SKIN`, ASSUMPTION). The clay can't make the skin thinner than that.
  - Eye sockets sit inside the skull's own eye openings, with the lids' sphere (R 18.1) and a pupil dimple at the true eye positions. The socket ceilings slope at 55° so the upper piece prints without supports.
  - Grooves mark the midline, the brow windows, the mouth opening and the lip line.
  - Three prints: `sculpt_upper` (upright), `sculpt_lower` (upside down) and `sculpt_plate`. They join with 4 Ø6 dowels. The plate has 4 conical mold keys, 4 board screw holes, and 4 × M4 into inserts in the neck.
- **EyeMech supports:** Cogley's own 3MF has tree (auto) supports on at 30°. His original file is now in `output/plates/` (commit `9433581`).
- **Service paths**, from a direction search:
  - **Back upper piece:** lifts off at about 50° up and back.
  - **EyeMech and both brows:** they come out together (brows unbolted). Slide back 50, lift 4, then out the back.
  - **Shelf:** up and back.
  - **Neck plate:** down.
  - **Mouth:** no path yet (Q14).
- **`cad/service_check.py`** (new, in the pipeline): runs the teardown in order and checks tool access with an L hex key on the brow flange and shelf screws. The two front brow flange screws have only 16.3 mm of headroom under the crown, so they need a stubby 2.5 mm key (short arm cut to 12 mm, 125° of swing).
- **To make those paths clear:**
  - The tabs on the back upper piece's two seams are placed per tab, on whichever piece they can't hook as it leaves (`BACK_UPPER_OUT_DEG` 52).
  - The EyeMech's rear stop moved from the shelf to a fin on the strap, behind the base plate's rear lip, so it leaves with the back piece.

**Numbers:**
- New: `BACK_UPPER_OUT_DEG` 52, `CRADLE_STOP` (2.4, 60) (thickness, width; was (2.4, 4.0): thickness, height).
- New: `SCULPT_MIN_SKIN` 3, `SCULPT_GROOVE` 1.2, `SCULPT_GROOVE_GAP` 2, `SCULPT_EYE_SOCKET` 10, `SCULPT_PUPIL` 3, `SCULPT_SOCKET_CEILING_DEG` 55.
- New: `SCULPT_PLATE` (8, 25), `SCULPT_PLATE_CBORE` (8.5, 4.5), `SCULPT_KEY` (12, 6), `SCULPT_BOARD_SCREW` 5, `SCULPT_DOWEL` (6.3, 13), `M4_INSERT_HOLE` 5.6 (ASSUMPTION), `M4_INSERT_DEPTH` 10.
- New: `EYEMECH_EYE_R` (16.5, 18.1) (MEASURED).
- New: `SERVICE_EYE_OUT`, `SERVICE_SHELF_OUT`, `SERVICE_TOL` 0.3, `SERVICE_KEY` (20, 65, 2), `SERVICE_STUBBY_KEY` (12, 65, 2), `SERVICE_KEY_SWING` 60, `SERVICE_HEAD_H` 3.
- Sculpt base estimate (not sliced yet): upper ~8 h, lower ~6 h, plate ~2 h; about 0.8 kg of PLA.

**Check:** `check: PASS (0 hard failure(s), 0 warning(s), 268 s)`.

**Renders:** [process_images](../process_images/README.md) snapshot 15 (`sculpt.png`, `skull.png`).

**Decisions:** D13 (art style: normally proportioned, not campy; sculpt base covers the whole head).

**Problems and fixes along the way:**
- With every tab of the back upper's vertical seam on the front piece, its side tabs locked the back piece in every direction. With them all on the back piece, the crown tabs locked it going up. The fix was the per-tab rule.
- A first try hung the stop from the strap behind the rear foot, but that foot sits under the base plate. The stop now bears on the base plate's rear lip instead.
- The eyes sit 3.4 mm under the skull's outside, so nothing of them showed on the base; it needed sockets.
- The socket ceilings were overhangs (7.4 mm along the normal; the 45° corners still too). A hull of the rims flattened them to 11° until each rim line was tilted.
- One socket reached 0.7 mm into the skull's wall under the eye. Sockets are now clipped to the skull's own opening.
- The plate's round offset left near-duplicate points that opened the mesh on reload (and crashed `check.py`'s measure step). It is simplified before extruding.
- The reviewer found the plate screws too long: an M4 × 16 would bottom out in the insert holes before clamping. Now M4 × 12. The dowel holes were exactly the dowel's length (12 + 12 for a 24 mm dowel); they are now 13 deep a side.
- `print_check` ran out of memory on the solid head pieces: every inward ray crosses the whole part. It now casts its rays in batches of 2000 faces (the skill's toolkit has the same code).

**Next:**
- Print the sculpt base once the printers are free.
- Mouth mount (Q14).

## 2026-10-16 — M3 — Neck base plate and rear access panel

**Done:**
- **Neck base:** `skull_neck_plate`, 128.4 × 112.8 × 18.
  - A 6 mm plate closes the bottom of the neck, 0.4 inside the wall, with an 18 mm collar up the wall's inside.
  - Six countersunk M3 screws go through the wall at z 10 into inserts in the collar, so the plate also ties both lower pieces together at the bottom.
  - 4 × M4 clearance holes on a 50 mm square for the stand (ASSUMPTION), and an exit for the cable channel (its Ø25 plus 1.5 all round).
- **Rear access panel:** `skull_access_panel`, a 96 × 74 opening (corner radius 12) centred at z 268 on the back of the head.
  - It is cut from the back upper piece with a 0.3 gap all round.
  - It rests on a 4 mm lip inside the opening. A 13 mm pad behind each side's midpoint holds an M3 insert.
  - 4 countersunk M3 × 6 screws from outside, heads flush under the skin.
  - With it off, the brows and the back of the EyeMech are in view.
- **Screw lengths:** the neck and panel screws are M3 × 6. An M3 × 8 would bottom out in the neck's insert holes and poke through the back of the panel's lip.
- **Renders:** `skull_check` now adds a 3/4 view from the back and a back view with the panel off (4 columns).

**Numbers (all new):**
- `NECK_PLATE_T` 6, `NECK_COLLAR` (6, 18), `NECK_SCREW_Z` 10, `NECK_SCREWS` 6.
- `NECK_BOLT_SQUARE` 50, `M4_CLEAR` 4.5, `CABLE_EXIT_CLEAR` 1.5.
- `PANEL_CENTRE_Z` 268, `PANEL_SIZE` (96, 74, 12), `PANEL_GAP` 0.3.
- `PANEL_LIP` (4, 5.5), `PANEL_SCREW_IN` 5.5, `PANEL_PAD` 13.

**Check:** `check: PASS (0 hard failure(s), 0 warning(s), 158 s)`.

**Renders:** [process_images](../process_images/README.md) snapshot 14 (`skull.png`).

**Problems and fixes along the way:**
- The first lip was built in two halves, one behind the wall and one behind the panel, that only met along a face. The back upper piece came out as 4 bodies and not watertight, and the overlap check's boolean failed. The panel half now reaches 1 mm under the wall half.
- The first lip was 7 mm wide with the screws midway across it. Each insert was left with 0.67 mm of wall, and each countersink broke through the panel's edge. Now there is a narrow lip plus a pad at each screw, with the screw 5.5 in from the edge: the countersink stays 2 inside the panel, and 4.5 of wall stands beside each insert.

**Next:**
- Fan room and vent (R6), probably in the access panel.
- Fixed skin attachments (with M4).
- `service_check`.
- The mouth mount waits on Q14.

## 2026-10-16 — M3 — EyeMech cradle and strap; print plates; first commit

**Done:**
- **Print plates for the team** (`output/plates/`, preview `plates_preview.png`):
  - `eyebrows_plate.stl`: both carriers and both brackets in their print poses, laid out by the new tool `cad/make_plates.py`.
  - `eyemech_e3.2_MG90s_A_plate.stl`: Cogley's public ε3.2 MG90s size-A file. All 34 parts are kept exactly in his Bambu layout (some print in place and interlock), centred on the bed: 244 × 247.
- **First commit** `ed2d371` on branch `dev`. Git LFS tracks *.step, *.stl, *.3mf and the process images. The team's own `Halloween_Animatronic_Budget.xlsx` is left out.
- **EyeMech cradle:** pads under its four feet, a rear stop, the shelf extended to y +8 under its side plates, and four shelf ledges on the side walls.
- **Retaining strap:** `skull_eye_strap`, 161.6 × 9 × 4, 0.4 over the back of the base plate, bolted to two ledges on the back upper piece.
- `skull_check` treats the feet on the pads as a designed contact. The front horizontal seam may have 2 tabs (it's crowded; that piece is held mainly by its 9-tab back seam).

**Numbers:**
- `SHELF_Y` (−118, 8).
- `CRADLE_PAD_MARGIN` 1, `CRADLE_STOP` (2.4, 4), `CRADLE_CLEAR` 0.4.
- `STRAP_Y` (−113, −104), `STRAP_GAP` 0.4, `STRAP_T` 4.
- `SHELF_LEDGES_Y` (−40, −95), `SHELF_LEDGE` (12, 24, 6).
- Joints: 23 screws (2 / 4 / 9 / 8).

**Check:** `check: PASS (0 hard failure(s), 0 warning(s), 172 s)`.

**Renders:** [process_images](../process_images/README.md) snapshot 13.

**Problems and fixes along the way:**
- The first cradle had rails beside the side plates and zip-tie slots. The inner rails hit the bottom-lid levers, and the outer plates are only ~1 mm from the temple walls. Replaced by the stop, the wall location and the strap.
- Pads reaching the shelf's curved front edge left slivers. They now stop 2 short of it.
- The designed 0.4 strap gap measured 0.399. The check now allows 0.02 for rounding.

**Next:** Neck base and the rear access panel. The mouth mount waits on Q14.

## 2026-10-15 — M3 — Skull joints

**Done:**
- 24 screwed seam tabs in `skull.py`. Each seam is sliced from the wall's mid-surface, a candidate is tested every 2 mm, and a tab is kept where:
  - there is wall on both sides of the seam
  - its countersink keeps 2 mm of wall to any opening
  - it is ≥ 1.5 from everything (the modules sampled about 1 per mm², the brows, the motion sweeps, the shelf, the brow plates)
  - it is 40 from the last tab on its seam and 20 from tabs on other seams
  - the wall doesn't lie nearly in the seam plane
- Per seam: front 3, back 4, upper front|back 9, lower front|back 8. On the front horizontal seam the tabs are on the upper piece and the screws go into the lower one, which has room between the mouth opening and the seam.
- `skull_check.motion_clouds()` is factored out for the builder to reuse. A small segment chainer in `skull.py` replaces trimesh's path code, which needs networkx (not installed).

**Numbers:** `SEAM_TAB_T` 5.5, `SEAM_TAB_W` 12, `SEAM_TAB_OVER` (6, 10), `SEAM_TAB_SPACING` 40, `SEAM_TAB_CLEAR` 1.5, `M3_CSK` (6.3, 1.75).

**Check:** `check: PASS (0 hard failure(s), 0 warning(s), 196 s)`. `NO OVERLAPS` (the tabs sit 0.1 behind the neighbouring wall), `SKULL OK`, `PRINT CHECK OK`.

**Renders:** [process_images](../process_images/README.md) snapshot 12.

**Problems and fixes along the way:**
- Test points on the steep occiput fell off the 2.4 wall. They are now snapped back onto the mid-surface.
- Axis-aligned tab boxes cut leaning walls obliquely and left slivers. Tab boxes are now built in the wall's frame, with the far edges square to the wall.
- Sparse keep-out samples (2.4 spacing) let a tab clip the EyeMech's base. Keep-out is now dense, with a 1.5 margin.
- Tabs clashed with the shelf and the brow plates. Both are now in the keep-out.
- A countersink at an eye opening's edge left a thin web. Screw spots now need 2 mm of wall all round.

**Next:** EyeMech cradle on the shelf, the shelf's own mounting, the neck base, the rear access panel. The mouth mount waits on Q14.

## 2026-10-15 — M3 — True-offset envelopes; skull v0

**Done:**
- **Envelopes are now true offsets** (`head.py`): every vertex of the outer skin moves inward along its normal. The outer surface is first extended 30 mm below the neck base, then cut flat at z = 0.
  - `geom.envelope_margin` is now "margin to the outer skin minus the inset". `geom.front_y` finds the outer point whose inward normal lands on (x, z).
  - `geom.row_fit` is cached. Without the cache the brow study went from 54 s to more than 10 min.
  - The analytic surface and the mesh agree within ±0.2 mm.
  - The brow study re-run gives the same pick, with 5 passing pivots instead of 3; the pivot moved about 1 mm. Every check still passes.
- **Skull v0** (`skull.py`, mesh booleans):
  - the wall
  - eye-and-brow openings (the hull of the eye circle and the brow window) and a mouth opening (rounded rectangle)
  - 4 pieces split at z 186 / y −60: front upper 175 × 87 × 166, front lower 160 × 84 × 186, back upper 177 × 155 × 166, back lower 162 × 122 × 186
  - a shelf (154 × 106 × 2.4) 1.0 above the mouth's top plate and 2.0 under the EyeMech
  - brow mount plates
- **`skull_check.py`**: static parts and sweeps against the skull, plus renders. In the pipeline.
- `snapshot.py` now also saves the skull and study images; `export_print.py` writes 11 print-ready files.

**Numbers:**
- `SKULL_SPLIT_Z` 186, `SKULL_SPLIT_Y` −60, `EYE_OPEN_R` 20.
- `MOUTH_OPEN_X` 46, `MOUTH_OPEN_Z` (88, 168).
- `SHELF_*`, `BROW_MOUNT_T` 4.
- `MOUTH_TOP_SRC_Z` −19.25 (MEASURED).
- `BROW_RIG_Z` (0, 82), lowered so the clamp bosses clear the base.

**Check:** `check: PASS (0 hard failure(s), 0 warning(s), 147 s)`. `LAYOUT OK`, `SWEEP OK`, `BROW OK`, `SKULL OK`, `PRINT CHECK OK`, `NO OVERLAPS`.
- Skull to the parts at rest: ≥ 1.0. Sweeps: jaw 3.3, lids 2.5, eyes 5.7, brow carriers 1.4.

**Renders:** [process_images](../process_images/README.md) snapshots 10 (true offsets) and 11 (skull v0).

**Problems and fixes along the way:**
- Box and cylinder openings crossed the curved wall obliquely and left slivers. The openings now come from outlines on the surface extruded along the normal.
- A fan-capped cutter left the lip patch behind as a loose body, and a self-crossing fan left 0.02 mm flaps. Cutters are now convex hulls of two rims.
- The eye circle and the brow window cut separately left sharp points; they are merged into one hull.
- The mouth opening's edge on the chin's curve, and an outer rim following the chin's downward normals, both grazed the chin. The opening bottom moved to z 88, and the outer rim never points down.
- Clamp bosses on the rig touched its base, leaving zero-thickness walls. The base is lowered.

**Decisions:** none new. Q14 added (Cogley's mouth mounting).

**Next:** Joints between the skull pieces, the EyeMech cradle, the neck base and the rear access panel. The mouth mount waits on Q14.

## 2026-10-15 — M2 — v1.1: review fixes, hard stops, bench rig, print documents

**Done:**
- **Second fresh-eyes review** (the first attempt stalled after 10 min; the retry with a tighter brief finished).
  - It confirmed: the pads track the skin, the bias works, everything clears at every pose, and the servo sits in its cutout with 0.4 all round.
  - It found:
    1. The ball links had 2.5 mm of stand-off, not the 3.5 a stud needs.
    2. The shoulder screw needed a non-stock 8.6 mm shoulder.
    3. The outer flange hole had no room for a screw head.
    4. The carrier floated 0.1 mm off the bed.
    5. The horn reference was turned 90°, so the check measured the wrong outline.
    6. Low strength margin on the lever and arm, but OK in this print pose.
    7. A straight hex key to the pivot screw is blocked by the EyeMech's centre post, so the brows go in first.
  - All fixed or written into the assembly order.
- **Hard stops** on the double-arm horn (see the design note). `brow_check` now confirms no contact inside the travel and engagement just past each end.
- **Bench rig** `cad/brow_rig.py` added to the pipeline (assembly: false; prints on its side with supports).
- **New documents:** [PRINT_GUIDE.md](PRINT_GUIDE.md), [BOM.md](BOM.md) and [ASSEMBLY.md](ASSEMBLY.md). `cad/export_print.py` writes slicer-ready files to `output/print/`.

**Numbers:**
- `SHOULDER_L` 10, `INSERT_RECESS` 0.3, `PIVOT_PLAY` 0.4 → `BROW_HUB_L` 9.3.
- `BALL_STUD_H` 3.5 → `LINK_X` 3.5, `LEVER_X` (−4, 0).
- `BROW_FLANGE_T` 7, `BROW_MOUNTS` (15, 3.5) and (15, −15.5).
- `BROW_STOPS_Y` (−2.5, −24), `BROW_STOP_MARGIN` 0.5, `HORN_FRONT_R` 9.5 (cut), `HORN_BACK_R` 17.5.
- `BROW_RIG_*`.

**Check:** `check: PASS (0 hard failure(s), 0 warning(s), 136 s)`. `LAYOUT OK`, `SWEEP OK`, `BROW OK`, `PRINT CHECK OK`, `NO OVERLAPS`, `COMPONENTS MATCH PARAMS`.
- The horn stays ≥ 0.31 from the stops inside the travel.
- The drive is ≥ 1.5 clear of parts it must not touch.
- The rig is ≥ 1.1 clear of every moving part.
- The carrier's bed contact is now 64 mm², on the hub's end face.

**Renders:** [process_images](../process_images/README.md) snapshot 09 (`brow.png` now includes the rig).

**Problems and fixes along the way:**
- The horn's full-length front arm ran into the bracket upright. It is cut to 9.5, and the raise stop moved to y′ −2.5 so the cut arm still reaches it at full raise.
- The free-hanging stop ledge would need support when printed upside down. It is now filled up to the flange.
- The rig's flat side cuts left slivers on the curved shell; it now uses square cuts. A first try with a thickened strip made new slivers and was reverted.
- The clamp-strip insert holes were 5 deep in a 2.4 mm shell. They now have bosses.
- At −10° (beyond the stop) the lower pad met the window edge. The window has 3 mm extra at each end.
- The reviewer's check run spent 50 min in the coupon build. That didn't repeat here (3.7 s); watch for it.

**Next:** The team prints the coupon, then the brows and the rig, and bench tests (see [ASSEMBLY.md](ASSEMBLY.md)). On the CAD side: snap adapters for the pads (M4), then the integrated skull (M3).

## 2026-10-15 — M2 — Eyebrow concept chosen; mechanism v1 modelled and checked

**Done:**
- **Concept study** (`cad/studies/brow_concepts.py`).
  - The first version measured a whole-brow rigid plate. It drifts 2–7 mm from the skin, and point-by-point it took 6.7 min.
  - Reworked: two snap pads per brow on a recessed bar, push and pull limits judged separately, the full pivot space searched (distance, height, skew), and vectorised to run in under a minute.
  - 3 of 2,431 pivots pass. Pick: r 45, offset +4, skew +12°. [Design note D3/D5](DESIGN_NOTES.md#d3-and-d5-eyebrow-mechanism-concept-and-motion).
- **Mechanism v1:**
  - `browgeom.py`: shared pivot, frame and four-bar maths.
  - `brow.py`: per side, a carrier (pads, bar, arm, hub on an M3 shoulder screw, rocker lever) and a bracket (cheek with M3 insert, upright, MG90S plate, top flange). The servo, horn, pushrod and screw are written as reference meshes.
  - `brow_check.py`: both brows through −7..+13.9° plus 3° overtravel, against the EyeMech, the lid and eye sweeps, the brackets and servos. It also measures pad push/pull and the four-bar.
- **Adafruit MG90 STEP** downloaded (MIT) to `inputs/components/` and listed in `components.yaml`. Servo sizes measured from it: case 22.6 × 12.0, shaft 6.0 from the end, tabs 31.3 × 2.0, holes 29.7 apart.
- **Toolkit fix:** `components_check.py` broke on OCP 8 (`TopoDS.Solid_s` → `TopoDS.Solid`, and `Bnd_Box.Get()`). Patched in the project copy; **the code-cad skill's toolkit has the same bug.**

**Numbers:**
- New params: `BROW_*`, `MG90_*`, `SHOULDER_*`, `M2_PILOT`, `M3_CLEAR`, `M3_INSERT_HOLE`.
- `BROW_CHEEK_T` 4 → 7, so an M3 × 4 insert fits.
- Four-bar: servo −14.0..+28.8° for carrier −7.0..+13.9°; transmission angle 75–90°.

**Check:** `check: PASS (0 hard failure(s), 0 warning(s), 92 s)`, the first fully clean run. `LAYOUT OK`, `SWEEP OK`, `BROW OK`, `PRINT CHECK OK`, `NO OVERLAPS`.
- Carrier ≥ 3.8 from the EyeMech, ≥ 4.3 from the lid and eye sweeps, ≥ 2.1 from its bracket.
- Drive ≥ 1.5 clear. Pads 0.88 toward / 1.55 away from the skin.

**Renders:** [process_images](../process_images/README.md) snapshot 08: the study, `brow.png`, the first real `views.png`, and `print_check.png`.

**Problems and fixes along the way:**
- The servo reference was rotated wrong (case length pointing forward). It is now placed with explicit axes and verified against its intended local extents.
- The carrier arm crossed the bracket upright. It now comes down to the hub inboard of the upright (x′ ≤ 2.4 against 4.4), which holds at every angle because the carrier turns about x′.
- The hub's designed 0.4 thrust gap to the cheek read as a near-miss. The hub is now left out of the gap measurement; overlaps there still count.
- Printed upside down, the bracket had two unsupported overhangs. Fixed with a 45° slope from the cheek up into the upright and a 45° brace in place of the beam.
- With its hub upright, the carrier sits on almost no bed area. It needs tree supports in any orientation; it prints hub-down.

**Decisions:** D3 = P, a working design for the bench to confirm. D5 implemented. R10 (narrow concept window) and R11 (servo torque) added.

**Next:** Fresh-eyes review. Then adjustable hard stops and the bench rig.

## 2026-10-15 — M1 done — firmware ranges, tongue accepted

**Done:**
- **D12 decided: keep the tongue unmodified.** The team has printed this mouth before and it runs fine, and the bench outranks CAD. Added `ACCEPTED_CONTACTS` in `params.py`, so `pose_sweep` reports the tongue/servo contact as info (up to 8.3 mm³) and still fails anything bigger or any other pair.
- Eye and lid ranges come from Cogley's firmware (`Code/NewFaceFollower.py`): LR and UD 40..140, lids 90..170 / 90..10 / 90..160. They are swept 1:1 as ±50° eyes and 80° lids, a safe upper bound.
- Eye sockets moved to M3/M5 (they depend on D7 and the sculpt). Number for the sculptor: the face must come back about 8–9 mm around each eye.
- M1 marked done. One bench number is outstanding: the real jaw opening.

**Check:** `check: PASS (0 hard failure(s), 1 warning(s), 115 s)`. `LAYOUT OK`, `SWEEP OK`.
- Eyes stay ≥9.8 behind the outer skin, lids ≥8.4.
- Brow bays are 3.5 from the lid sweep, unchanged at 80°: the lids turn inside their own sphere.

**Renders:** [process_images](../process_images/README.md) snapshot 07 (M1 complete).

**Decisions:** D12 = B (keep the tongue as is).

**Next:** M2, the eyebrow concept study.

## 2026-10-15 — M1 — Motion sweeps and reserved space; process images folder

**Done:**
- D4 signed off as A2.
- New `process_images/` folder with `cad/snapshot.py`, which saves every check image permanently. Re-created and saved the earlier layout stages as snapshots 01–03.
- New `cad/reserve.py`:
  - brow bays per side: a servo bay above the EyeMech plus a carrier band down to the brow line, trimmed by the skin's inner surface
  - a Ø25 cable channel to the neck
- New `cad/pose_sweep.py`:
  - the jaw opens about its axis, with 10° of overtravel
  - eyes pan and tilt; top and bottom lids open
  - reserved volumes are checked against every part at rest and every swept pose
  - lip plate opening and chin travel are reported
- Both scripts are in the pipeline.
- Refactored the drawing helpers in `layout_check.py` so the motion check can reuse them.

**Numbers:**
- Motion ranges (ASSUMPTION): jaw 25° (+10° overtravel), eyes ±30° pan and ±25° tilt, top lids 60°, bottom lids 35°.
- `JAW_GROUP_CORE` = JawBase, JawLink, Part_33, Part_22 (the tongue).
- Neck and nape rows thickened: y_back at rows −45 / −68 / −92 / −112 / −130 went from −120 / −108 / −102 / −98 / −100 to −138 / −126 / −120 / −117 / −117. The neck half-width went from 56 to 60, and its front from −15 to −10.
- `CABLE_PATH` set (5 points, ending square through the base).

**Check:** `check: PASS (0 hard failure(s), 1 warning(s), 117 s)`. `LAYOUT OK`, `SWEEP OK`.
- The jaw is clean to 35° (smallest gap 1.1 mm, an M2 screw to an MG996R body at 20°). At 25° the chin drops 16.3 mm and the lip plates open from 12.0 to 41.1 mm.
- Brow bays: 2.4 mm from the EyeMech pivot at rest, 3.5 mm from the open top lids.
- Cable channel: 16.1 mm behind the open jaw, inside the skull.
- Layout margins with the thicker neck: mouth frame +0.6, jaw +3.3, eye module ↔ mouth +5.5.

**Renders:** [process_images](../process_images/README.md) snapshots 05 (first motion run) and 06 (after review, tongue clash visible).

**Problems and fixes along the way:**
- A height-only jaw grouping put eight frame screws on the jaw, and they "collided" at 5°. Now parts join the jaw by contact.
- The tongue sits above the height cut, so its links got dragged onto the frame. The tongue is now in the jaw core.
- The contact grouping first took 9 minutes; a KD-tree brought the whole sweep to about 1 minute.
- The rest pose counted as a failure because the jaw is 0.8 mm from its frame by Cogley's design. Rest-pose gaps are no longer judged.
- The cable channel didn't fit between the open jaw and the thin proxy neck. The neck is now thicker.
- A "beyond closed skin" column always read 0, because the proxy is solid under the chin. It is replaced by the lip plate opening.

**Review:** `cad-reviewer` result `check: PASS (0 hard failure(s), 1 warning(s), 109 s)`.
- It answered yes to all 5 questions, and confirmed the jaw axis is concentric within 0.1 mm with the JawLink bores, the MG996R spline and the horn.
- **Serious finding: the tongue (Part_22) clashes with a fixed MG90S** (x −24) from about 2.5° to 25°, by up to 8.6 mm³. My check hid it: the pair's rest gap is 0.49 mm, just under the 0.5 mm "designed contact" threshold, so it was skipped.
- Fixes applied:
  - designed contacts now mean touching at rest (0.05 mm), and their overlap may not grow
  - the MG996R horn, spline and horn screws now turn with the jaw (`JAW_HORN_R` 14, `JAW_HORN_X_MIN` 44)
  - 12 exact candidates per part, up from 7
  - the cable's skull margin skips its exit at the base (now +2.0)
  - new "inside skull" column for the jaw (+1.3 to +3.5)
  - the jaw-link render now cuts through the link near its bore
- After the fixes: `SWEEP: 1 issue(s)`, the tongue clash, 5 / 8 / 2 / 1 mm³ at 5 / 10 / 15 / 20°. Everything else on the jaw is clean to 35°.
- Snapshot 06.

**Decisions:** D12 (tongue clash) opened. Recommended: trim about 3 mm off the tongue's back corner, then confirm on the bench.

**Next:** D12. Then the M1 sign-off items: motion ranges from Cogley's code or the bench, and the proxy eye sockets. Then M2 (eyebrow prototype) inside the reserved brow bays.

## 2026-10-15 — M1 — First layout: both Cogley modules fit at 1.2× with boxy temples

**Done:**
- Replaced the example project with the real one.
  - `params.py` now holds the frame, the proxy head sections (two shapes), the head scale, the skin and skull thickness, and the measured module datums.
  - The example builder `enclosure.py` and its Pico params are deleted.
- Measured the module datums from the STEP files.
  - EyeMech: eye centres (±37.5, 0, 0), eyeball R16.0, lids are 1.6 shells (R16.5/18.1) pivoting on the x axis.
  - Mouth: lip plates' front y −92.6, lip line z −71.2, jaw pivot on the x axis at (y −2.4, z −40.7), driven straight off the MG996R outputs.
- New scripts:
  - `geom.py`: shared landmarks, sections and placements.
  - `modules.py`: places both assemblies, one mesh per solid, in `output/ref/` (gitignored).
  - `head.py`: proxy head plus the skin and skull envelopes.
  - `layout_check.py`: containment, module clearance, fit table for scales 1.0–1.3, and renders.
- All four are in the `cad.yaml` pipeline. Built the coupon STL.
- The mouth file's "invalid solids" are only its 4 tessellated surface parts (`Part_1`); every real solid is valid.
- Wrote design note [D4](DESIGN_NOTES.md#d4-head-size-and-shape).

**Numbers:**
- `HEAD_SCALE = 1.2` (ASSUMPTION, D4).
- `HEAD_SHAPE = "boxy_temples"` (was "average"). Front-half exponent 2.6 → 3.4 at the eye line. Half-width +2 at the eye line and cheekbones, +1 at the brow.
- `EYE_Z = 212.4`. Lip line at z 130.8. Jaw axis at y −65.8, z 161.3.
- `SKIN_T = 5.0`, `LIP_SKIN_T = 8.0`, `SKULL_WALL = 2.4` (ASSUMPTION).

**Check:** `check: PASS (0 hard failure(s), 2 warning(s), 94 s)`. Layout: `LAYOUT OK`.
- The warnings are expected: no assembled print parts exist yet, so the standard views are empty, and the coupon STL was stale until it was rebuilt.
- At 1.2× boxy, margins are: EyeMech frame +0.7, eyes +10.0, lids +8.4, lip plates +1.9, jaw +3.6, mouth frame +1.6, eye module ↔ mouth +2.5.

**Renders:** [process_images/](../process_images/README.md) snapshots 01–04: life size crashing, temples poking out at 1.2× average, boxy temples with the tight gap, and the approved A2 layout.

**Problems and fixes along the way:**
- A smooth loft through the sparse head sections overshot to 497 mm wide. Now the sections are interpolated with PCHIP every 4 mm and joined with a ruled loft.
- Mesh signed distance took over 10 minutes. Now each point is screened against the section formula and only the worst candidates are measured exactly: 40 s for four scales.
- The first render showed the modules at the last scale evaluated. Placement is now explicit before rendering.
- 1.2× with the average head left the EyeMech side plates 7.2 mm through the temples, so I added the boxy-temple shape (two tuning rounds).

**Review:** `cad-reviewer` result `Check: PASS (0 hard failure(s), 1 warning(s), 92 s)`.
- It confirmed every 1.2 number to within 0.4 mm with an independent recompute, and answered its 5 questions yes except the neck shape.
- Fixed from the review:
  - sections now draw a 12 mm slab, so parts behind the cut no longer look like they poke out
  - the `mouth surfaces` group is now checked (+9.0)
  - the lip line uses the same PCHIP fit as the loft
  - the chin and jaw rows now span to the back of the neck (w 50/52, pointed front n 1.5–2.0), so the "lightbulb" neck waist is gone
- Not fixed yet, and listed in PLAN M1: the section-shrink inset is not a true offset (the skin is as thin as 1.4 mm where the surface leans); the proxy has no eye sockets.

**Numbers:** `STOMION_DZ_1X` −68.0 → −70.5. The reviewer found the 2.5 mm eye-to-mouth gap too small for a skull shelf (3.2 needed). At 1.2× the change gives eye ↔ mouth +5.5, mouth frame +0.9, jaw +2.8, lip plates +2.4. `LAYOUT OK`.

**Decisions:** Q1 answered (aim for Halloween; the team owns the schedule). **D4 decided: A2**, 1.2×, boxy temples, lip line −70.5 (signed off the same day).

**Next:** D4 sign-off. Then group the moving parts and write `pose_sweep` (jaw, eye pan/tilt, lids), add a brow placeholder volume, and find a cable path.

## 2026-10-15 — M0 — Answers on printer, jar, CAD source and versions; ε3.1 vs ε3.2 compared

**Done:**
- Recorded the team's answers in [PLAN.md](PLAN.md#7-open-questions):
  - Q2: 2 × Bambu Lab P2S, 256 mm bed.
  - Q5: no jar yet; it will be chosen to fit the head.
  - Q12: the STEP files come from Cogley's own Onshape, through Patreon.
  - Q13: answered below.
- Compared the team's ε3.1 STEP with the public ε3.2 `MG90s - A.3mf` part by part, by size and volume. I also read the ε3.2 assembly guide.
- Set the printer bed in `cad.yaml` to the P2S (DATASHEET).
- Marked the reference files as Patreon-only: the repo stays private.

**Numbers:** ε3.1 vs ε3.2.
- Base plate, eyes, lids, levers, pivots, horns, eye adaptors and lateral frame: identical within 0.1 mm and 0.5 % volume.
- Central pivot holders and servo retainers: differ by 0.4–0.6 mm and 50–190 mm³, which fits the print-in-place joints and the A fit size.

**Decisions:**
- D10 tongue servo: keep it if it is no hassle. That makes 19 servos.
- D11 (decided): use ε3.2-PIP MG90s for both the print and the CAD. The ε3.2 model is to come from Cogley's Onshape if it is there; otherwise it will be rebuilt from the public print files.
- D4: the jar sets no limit, so the head scale (probably about 1.2) is driven by the mechanisms and proportions.

**Next:** Start M1, unless Q1 (the deadline) changes the scope.

## 2026-10-15 — M0 — Cogley STEP files received and surveyed

**Done:**
- The team supplied `EyeMech ε3.1.step` and `MouthAssembly.step`, both exported from Onshape today.
- Moved them to `inputs/reference/eyemech/EyeMech_e3.1.step` (renamed to ASCII, because the ε broke a Windows console script) and `inputs/reference/mouth/MouthAssembly.step`.
- Recorded both in [inputs/reference/README.md](../inputs/reference/README.md).
- Loaded both with build123d and surveyed them: part names, solid counts, bounding boxes and servo positions.
- Updated PLAN §3, R1, R2 and the M0 status, and added Q12 and Q13.

**Numbers** (first survey, bounding boxes in each file's own frame; nothing is in `params.py` yet):
- EyeMech: 38 valid solids, envelope 145.4 × 132.3 × 62.8. Eyeballs about Ø32, centres at x = ±37.5, so the eye spacing is 75.0.
- Mouth: 107 solids, envelope 112.4 × 118.6 × 86.9. 9 × MG90S. The two `Component2` bodies (40.0 × 28.8 × 57.1) are probably the MG996R jaw servos. Four tessellated surface parts (`Part_1`). The compound reports invalid solids.

**Problems:**
- The EyeMech does not fit a life-size head unchanged: its eye spacing is 75 against about 63 for an adult, and its base is 145 wide against an outer head width of about 155. Scaling the head about 1.2 is the likely answer (D4).
- The EyeMech file is ε3.1, but the brief names ε3.2 (Q13).
- The mouth has 9 MG90S servos, but the brief says 8 (Q13).
- The mouth file has invalid solids, still to be traced.

**Next:** Answer Q1–Q3, Q12 and Q13. Then start M1: set up the frame and datums in `params.py`, and write the `modules` builder that places both assemblies in the head frame.

## 2026-10-14/15 — M0 — Repo set up, brief received, plan v1

**Done:**
- Started the repo with the code-cad toolkit: a Python 3.12 venv, build123d 0.13, the check pipeline, the `cad-reviewer` agent, and the calibration coupon.
- Smoke-tested the toolkit on the skill's example part (a box for a Raspberry Pi Pico). The full pipeline ran: build, overlap check, print check, renders.
- Saved the project brief as [BRIEF.md](BRIEF.md).
- Researched the two Will Cogley mechanisms the brief names: what CAD is published for them, in which formats, and under which licence. Findings are in [PLAN.md](PLAN.md#3-inputs-what-exists-and-what-we-need).
- Wrote build plan v1: [PLAN.md](PLAN.md).

**Check:** `check: PASS (0 hard failure(s), 2 warning(s), 25 s)` on the example part. Both warnings are expected: the example's Pico STEP model is not downloaded, and no print files have been built yet.

**Findings from research:**
- Neither Cogley mechanism is published as STEP. EyeMech ε3.2 is 3MF only, and the Robot Head α2.0.33 is STL, 3MF and OBJ. Interfaces will be re-modelled from mesh measurements (PLAN R2).
- The brief's mouth (8 × MG90S + 2 × MG996R, with a mouth PCB) matches the Robot Head α2.0.33 mouth: 4 lip, 4 cheek and 2 jaw servos. The 2020 Mouth Mechanism has 7 + 2 servos, no PCB, and is the only one with a STEP. α2.0.33 is the working assumption until Q3 is answered.
- EyeMech has no external mounting holes, so the skull will clamp its base.
- EyeMech is licensed CC BY-NC-SA 4.0 (Q10).
- Cogley's α2.0 head has an Eyes/Brow/Neck board, so it likely contains a brow mechanism to study before M2.
- MG90S: Adafruit has an MIT STEP of the same body. MG996R: no trusted model found.

**Problems:** Nothing in the repo is project geometry yet. The example builder (`cad/enclosure.py`) and its Pico params stay until the first real builder exists.

**Next:** Answer the open questions in [PLAN.md](PLAN.md#7-open-questions), starting with the deadline, the printer, which mouth mechanism, and the jar size. Then gather the M0 inputs.

# Current design audit: Frank, the Frankenstein animatronic head (project files as of 2026-10-30)

Scope: an internal audit of the project's own files only (no web sources). Every citation is a repo path with a line number, written as a link relative to this file (`../../` is the project root, `C:\Users\Lars Langenbach\Desktop\Halloween Animatronic`). One non-repo source is used: the team's own claude.ai artifact "Head Power Wiring" (2026-10-26), which the plan names as the power design (PLAN Q19). Anything marked **(inferred)** is a reading of the files, not a statement in them.

Naming used below: the mouth board's socket names come from Cogley's `MouthMaster.py` and are reused on the eye/brow board, so on Board 2 the socket "JL" is a brow servo and "CUR" is an eyelid. Sides are "as seen from the front" unless stated; the project's own frame says +x is the character's left, and the files flag that Cogley's L/R labels may be mirrored relative to that frame ([docs/BUILD_LOG.md:648](../../docs/BUILD_LOG.md#L648), [docs/BUILD_LOG.md:247](../../docs/BUILD_LOG.md#L247)).

---

## 1. Every moving degree of freedom: what moves, which actuator, travel, limits, L/R independence

### Takeaway
The face has 20 fitted servos driving about 15 independent motions: conjugate eye pan and tilt (one servo each for both eyes), four independent eyelids, a two-servo-per-brow eyebrow (inner and outer end of a flexible TPU bar, all four independent), a single-DOF jaw on two mirrored MG996Rs, four independent lip servos and four mouth-corner servos. There is no neck, no cheek raise, no tongue servo fitted, and almost every range is set by hand on slider tools rather than measured against hard stops.

### Cited Findings

**Overall architecture and servo count**
- The mechanical base is Will Cogley's whole Robot Head α2.0.33 (frame, mouth, eye mount, brows, fan bracket kept) — [docs/PLAN.md:388](../../docs/PLAN.md#L388) (D14); built as he designed it, outer shell included, and the team's own skull pieces retired — [docs/PLAN.md:389](../../docs/PLAN.md#L389) (D17), [docs/PLAN.md:16](../../docs/PLAN.md#L16).
- Servo bill: 19 × MG90S (mouth 9 incl. tongue, EyeMech 6, Cogley's brows 4) + 2 × MG996R (jaw) — [docs/BOM.md:9](../../docs/BOM.md#L9), [docs/BOM.md:13](../../docs/BOM.md#L13). The power design calls it "all 21 servos" — [Head Power Wiring artifact](https://claude.ai/artifact/NNjtnRuZohye1SKmWCQ5Gw) (header). PLAN §5 still says "19 in total. 17 × MG90S … 2 brows", which predates D15 — [docs/PLAN.md:157](../../docs/PLAN.md#L157) (stale; contradicted by BOM).
- No tongue servo is fitted as of 2026-10-29: `TONGUE = False  # False: no tongue servo fitted (2026-10-29)` — [frank/mouth.py:90](../../frank/mouth.py#L90); "there is no tongue servo (`TONGUE = False`, nothing goes to TON)" — [docs/BUILD_LOG.md:110](../../docs/BUILD_LOG.md#L110).
- Cogley's head has no neck: "the assembly ends at the jaw" — [docs/PLAN.md:69](../../docs/PLAN.md#L69). The brief says "The design does not currently require motorized neck motion" — [docs/BRIEF.md:178](../../docs/BRIEF.md#L178). The system prompt tells Frank "You have no neck, so you can't nod or turn your head" — [frank/system_prompt.md:71](../../frank/system_prompt.md#L71). The head is clamped rigidly to a printed neck spine (D27) — [docs/PLAN.md:398](../../docs/PLAN.md#L398).

**DOF table (servo degrees unless stated)**

| DOF | Actuator / socket (board) | Range in use | Limits and where they live | L/R independent? |
|---|---|---|---|---|
| Eye pan (both eyes) | 1 × MG90S, socket LLL GP8 (Board 2) | centre 107; idle animation ±30 → 77..137 (inferred arithmetic) | slider 40..140 ([firmware/servo_controls.py:47](../../firmware/servo_controls.py#L47)); Cogley LR 40–140 ([docs/BUILD_LOG.md:476](../../docs/BUILD_LOG.md#L476)); CAD swept ±50° as a 1:1 upper bound ([cad/params.py:159-163](../../cad/params.py#L159)) | No: one servo for both eyes ("Both eyes: left / right", [firmware/servo_controls.py:47](../../firmware/servo_controls.py#L47)) |
| Eye tilt (both eyes) | 1 × MG90S, LLR GP9 (Board 2) | centre 62; idle ±15 | slider 60..140 ([firmware/servo_controls.py:48](../../firmware/servo_controls.py#L48)); Cogley UD 60–140 ([docs/BUILD_LOG.md:476](../../docs/BUILD_LOG.md#L476)) | No ("Both eyes: up / down") |
| Upper lid, eye on viewer's right | MG90S, CUR GP11 | shut 183 / open 139 (44°) | saved poses [firmware/eye_poses.json:2-13](../../firmware/eye_poses.json#L2); slider −9..189 ([firmware/servo_controls.py:49](../../firmware/servo_controls.py#L49)) | Yes, each lid has its own servo |
| Lower lid, eye on viewer's right | MG90S, CUL GP10 | shut 108 / open 143 (35°) | same file; this servo died and was being replaced 2026-10-30 ([docs/BUILD_LOG.md:38](../../docs/BUILD_LOG.md#L38)) | Yes |
| Upper lid, eye on viewer's left | MG90S, CLR GP13 | shut 134 / open 188 (54°) | same file; CLR stalled buzzing at 196 (≈2678 µs) on 2026-10-29 ([docs/BUILD_LOG.md:203](../../docs/BUILD_LOG.md#L203)) | Yes |
| Lower lid, eye on viewer's left | MG90S, CLL GP12 | shut 117 / open 53 (64°) | same file | Yes |
| Brow, left outer end | MG90S, JL GP4 (Board 2) | level 90, +35 raise / −20 lower | `RAISE = 35.0`, `LOWER = 20.0` ([firmware/brow_anim.py:26-27](../../firmware/brow_anim.py#L26)), saved travel ([firmware/eye_poses.json:18-27](../../firmware/eye_poses.json#L18)); slider 0..180 ([firmware/servo_controls.py:53](../../firmware/servo_controls.py#L53)) | Yes: 4 independent servos, inner + outer per brow |
| Brow, left inner end | MG90S, LUL GP6 | as above | as above | Yes |
| Brow, right outer end | MG90S, JR GP5 | as above | as above | Yes |
| Brow, right inner end | MG90S, LUR GP7 | as above | as above | Yes |
| Jaw open/close | 2 × MG996R, JL GP4 + JR GP5 (Board 1), mirrored | 90 closed, `JAW_DEG = 40` servo deg open by default | firmware cap `JAW_CAP = 70` ([firmware/cogley_mouth_main.py:57-58](../../firmware/cogley_mouth_main.py#L57)); CAD assumes 25° jaw rotation, swept to 35° ([cad/params.py:149-152](../../cad/params.py#L149), [docs/BUILD_LOG.md:570](../../docs/BUILD_LOG.md#L570)) | No: one command drives both mirrored servos (`set_jaw`, [firmware/cogley_mouth_main.py:182-185](../../firmware/cogley_mouth_main.py#L182)) |
| Upper lip left / right | MG90S, LUL GP6 / LUR GP7 (Board 1) | LUL 40–110, LUR 70–140 | board clamp `LIMITS` ([firmware/cogley_mouth_main.py:70-82](../../firmware/cogley_mouth_main.py#L70)) | Yes (separate servos) |
| Lower lip left / right | MG90S, LLL GP8 / LLR GP9 | LLL 55–110, LLR 60–110 | same | Yes |
| Upper mouth corner left / right | MG90S, CUL GP10 / CUR GP11 | CUL 60–100, CUR 75–105 | same | Yes |
| Lower mouth corner left / right | MG90S, CLL GP12 / CLR GP13 | CLL 90–120, CLR 65–90 | same | Yes |
| Tongue | MG90S socket TON GP14 (not fitted) | limits 55–130 if fitted | [firmware/cogley_mouth_main.py:81](../../firmware/cogley_mouth_main.py#L81) | n/a |

**Eyes**
- EyeMech ε3.2 (printed MG90s-A set, horns reprinted to size B because A slipped on the shafts) — [docs/PLAN.md:393](../../docs/PLAN.md#L393) (D16), [docs/BUILD_LOG.md:573](../../docs/BUILD_LOG.md#L573). Six servos: eye left/right, eye up/down, four lids — [docs/PLAN.md:86](../../docs/PLAN.md#L86).
- Eyeballs are Ø32 at 75.0 mm centre spacing (adult ≈63, eye ≈24) — [inputs/reference/README.md:24](../../inputs/reference/README.md#L24), [docs/PLAN.md:52-54](../../docs/PLAN.md#L52).
- The eyeball front was filled smooth (no iris dish, no pupil hole); iris and pupil are painted — [docs/PLAN.md:402](../../docs/PLAN.md#L402) (D22).
- Eye limits in Cogley's own program are LR 40–140, UD 60–140, TL 90–160, BL 90–30, TR 90–30, BR 90–140, "not measured on the team's build" — [docs/BUILD_LOG.md:476](../../docs/BUILD_LOG.md#L476). An earlier read of his firmware gave lids "90..170 / 90..10 / 90..160" — [cad/params.py:159-161](../../cad/params.py#L159) (minor inconsistency between the two readings).
- The lids now run far past Cogley's angles: the Pico program accepts −27..207 (200..2800 µs) because a lid needed the last few degrees — [firmware/pico_servo_ctl.py:6-8](../../firmware/pico_servo_ctl.py#L6), [firmware/pico_servo_ctl.py:73](../../firmware/pico_servo_ctl.py#L73); the right eye's shut angles sat at the ends of their sliders, "far from Cogley's 90" — [docs/BUILD_LOG.md:448](../../docs/BUILD_LOG.md#L448). Past the servo's stop the lid "only buzzes"; the fix is moving the horn by a few teeth — [docs/BUILD_LOG.md:205](../../docs/BUILD_LOG.md#L205), [docs/BUILD_LOG.md:215](../../docs/BUILD_LOG.md#L215).
- The two upper lids were matched by eye because "equal travel still left the two eyes open by different amounts (the horns sit differently on their splines)" — [docs/BUILD_LOG.md:203](../../docs/BUILD_LOG.md#L203).
- The saved lid poses on disk ([firmware/eye_poses.json:2-13](../../firmware/eye_poses.json#L2): shut CUR 183, CLR 134, CUL 108, CLL 117; open CUR 139, CLR 188, CUL 143, CLL 53) differ from the poses the 2026-10-30 log entry says were restored (shut CUR 160, CUL 30, CLR 130, CLL 105; open CUR 128, CUL 118, CLR 160, CLL 31) — [docs/BUILD_LOG.md:36](../../docs/BUILD_LOG.md#L36). Contradiction between log and file.
- Lid skin limits blink travel: "every millimetre of silicone on a lash edge stops the blink about 3° short" — [docs/PRINT_GUIDE.md:11](../../docs/PRINT_GUIDE.md#L11), [docs/BUILD_LOG.md:90](../../docs/BUILD_LOG.md#L90).

**Brows**
- Cogley's brows: 4 MG90S, an inner and outer per brow, each bar printed in TPU so it bends when its two servos differ; his `Brows.py` has up, down, angry and happy poses — [docs/PLAN.md:67](../../docs/PLAN.md#L67). Chosen because "an inner and outer servo per brow gives angry and happy shapes" — [docs/PLAN.md:392](../../docs/PLAN.md#L392) (D15).
- Cogley's own brow poses move each end ±30 up / ±10 down about 90 (e.g. Up: LO 120, LI 60, RI 120, RO 60; Down: LO 80, LI 100, RI 80, RO 100) — [inputs/reference/head_a2.0.33/Code/Brows.py:52-71](../../inputs/reference/head_a2.0.33/Code/Brows.py#L52). The plan summarises it as "±20° around centre" — [docs/PLAN.md:67](../../docs/PLAN.md#L67) (minor mismatch).
- The team's travel (35 up / 20 down) is an ASSUMPTION; Cogley's 10° down "barely showed"; the direction table `DIR` is "unchecked on the team's build" — [docs/BUILD_LOG.md:122](../../docs/BUILD_LOG.md#L122), [firmware/brow_anim.py:21-24](../../firmware/brow_anim.py#L21).
- The brow bars need TPU 95A; BOM still marks TPU "[buy]" and the bars were "ready to print" on 2026-10-24 — [docs/BOM.md:12](../../docs/BOM.md#L12), [docs/BUILD_LOG.md:600-608](../../docs/BUILD_LOG.md#L600). A PLA bar is acceptable only "for a fit test with both servos of a brow moving together" — [docs/PLAN.md:370](../../docs/PLAN.md#L370).
- The left outer brow servo (JL socket) was found faulty on 2026-10-26 and "may still be the weak one" on 2026-10-29 — [docs/BUILD_LOG.md:474](../../docs/BUILD_LOG.md#L474), [docs/BUILD_LOG.md:126](../../docs/BUILD_LOG.md#L126).
- The team's own custom brow (1 servo per brow, skewed pivot so the inner end travels 1.43× the outer; 2:1 four-bar; +10/−5 mm mid-brow target; adjustable set-screw hard stops) is printed but is now only the bench backup — [docs/PLAN.md:15](../../docs/PLAN.md#L15), [docs/DESIGN_NOTES.md:78-86](../../docs/DESIGN_NOTES.md#L78), [cad/params.py:198-209](../../cad/params.py#L198), [docs/PLAN.md:256](../../docs/PLAN.md#L256).

**Mouth**
- Cogley's mouth board drives "2 × MG996R jaw, 4 lip, 4 cheek, tongue and one spare" — [docs/PLAN.md:95](../../docs/PLAN.md#L95). The firmware and wiring docs name the four "cheek" servos as mouth corners (upper corner L/R, lower corner L/R) — [firmware/README.md:41](../../firmware/README.md#L41), [Head Power Wiring artifact](https://claude.ai/artifact/NNjtnRuZohye1SKmWCQ5Gw) (Board 1 socket table).
- Cogley's corner poses: smile moves only the upper corners (CUL 60, CUR 105), frown the upper corners the other way (CUL 100, CUR 75), wide moves all four (CUL 65, CUR 105, CLL 120, CLR 65), narrow is the rest — [firmware/cogley_mouth_main.py:84-95](../../firmware/cogley_mouth_main.py#L84), matching [inputs/reference/head_a2.0.33/Code/MouthMaster.py:56-86](../../inputs/reference/head_a2.0.33/Code/MouthMaster.py#L56).
- Lips: lips_up (LUL 40, LUR 140, LLL 110, LLR 60) and lips_down (110, 70, 55, 110) — [firmware/cogley_mouth_main.py:87-88](../../firmware/cogley_mouth_main.py#L87).
- The board program clamps every mouth servo to "the range his poses use" and glides at a set speed (default 90 deg/s, 300 deg/s while chattering) — [firmware/cogley_mouth_main.py:8-12](../../firmware/cogley_mouth_main.py#L8), [firmware/cogley_mouth_main.py:53-56](../../firmware/cogley_mouth_main.py#L53). Frank's driver asks for 720 deg/s because 90 "is too slow to talk" — [frank/mouth.py:94](../../frank/mouth.py#L94).
- The jaw ran backwards on the bench, so the direction is reversed in software (`JAW_DIR = -1`) — [firmware/cogley_mouth_main.py:59-60](../../firmware/cogley_mouth_main.py#L59), [docs/BUILD_LOG.md:568](../../docs/BUILD_LOG.md#L568). Two mouth servo pairs were found plugged mirrored; a lower-lip servo's M2 insert stripped and the servo was hot-glued — [docs/BUILD_LOG.md:568](../../docs/BUILD_LOG.md#L568).
- Jaw in CAD at 25°: "the chin drops 16.3 mm, the lip plates open from 12.0 to 41.1 mm"; the jaw range is still the ASSUMPTION of 25° pending a bench measurement — [docs/PLAN.md:225](../../docs/PLAN.md#L225), [docs/PLAN.md:230](../../docs/PLAN.md#L230).
- A hand-set "neutral" mouth for skin fitting: LUL 90, LUR 90, LLL 55, LLR 78, CUL 90, CUR 80, CLL 120, CLR 70, tongue 130, jaw closed — [docs/BUILD_LOG.md:456](../../docs/BUILD_LOG.md#L456).
- Lips were weak visually: "the lips and corners hardly showed with his angles" — [docs/BUILD_LOG.md:112](../../docs/BUILD_LOG.md#L112); TalkingHead's lips already move ×2 of the planned shapes (`--lip-gain`) — [docs/BUILD_LOG.md:569](../../docs/BUILD_LOG.md#L569).

**Hard caps vs firmware soft limits**
- The plan's rule is a hard cap plus a lower firmware soft limit per moving part ([CLAUDE.md, "Animatronic specifics"](../../CLAUDE.md)); the custom brow had adjustable set-screw hard stops — [docs/ASSEMBLY.md:32](../../docs/ASSEMBLY.md#L32). For Cogley's mechanisms in use, no physical hard stops are documented; the only limits are software: board clamps on Board 1 ([firmware/cogley_mouth_main.py:70-82](../../firmware/cogley_mouth_main.py#L70)), a global −27..207 clamp on Board 2 ([firmware/pico_servo_ctl.py:73](../../firmware/pico_servo_ctl.py#L73)), and the PC-side slider ranges, saved SHUT/OPEN poses and RAISE/LOWER numbers ([firmware/servo_controls.py:46-57](../../firmware/servo_controls.py#L46), [firmware/eye_anim.py:8-10](../../firmware/eye_anim.py#L8), [firmware/brow_anim.py:10-13](../../firmware/brow_anim.py#L10)).

### Inferences
- **(inferred)** Independent motions fitted today: eye pan, eye tilt, 4 lids, 4 brow ends, jaw, 4 lips, 4 corners = 15 DOF from 20 servos (the jaw uses two).
- **(inferred)** Because both eyes share one pan and one tilt servo, there is no vergence (eyes cannot converge on a near visitor) and no independent eye motion.
- **(inferred)** Four independent lids permit winks, asymmetric squints and lower-lid raises mechanically, but only lid open/close between two saved poses is used in software.
- **(inferred)** Each mouth corner has two servos (upper and lower), so a corner can likely be widened and raised/lowered; Cogley's smile/frown use only the upper pair.
- **(inferred)** The eye idle animation can command tilt below Cogley's lower limit: centre 62 minus `LOOK_UD` 15 gives 47, below the slider's 60, and Board 2 only clamps at −27 ([firmware/eye_anim.py:20](../../firmware/eye_anim.py#L20), [firmware/eye_poses.json:14-17](../../firmware/eye_poses.json#L14), [firmware/pico_servo_ctl.py:73](../../firmware/pico_servo_ctl.py#L73)).
- **(inferred)** Jaw servo degrees and jaw rotation degrees are different quantities: the firmware's 40° is servo travel on a linkage (`JawLink` on the MG996R spline, [cad/params.py:140-141](../../cad/params.py#L140)) whose ratio is not stated, so the CAD's 25° jaw sweep cannot be compared with the firmware number directly.

### Gaps
- No measured hard-stop angles for any Cogley mechanism, no measured jaw opening (degrees or mm), and no measured brow travel in mm under silicone.
- The servo-to-output ratios of the eye, lid, jaw and brow linkages are not documented, so output-side ranges (eye degrees, lid degrees, brow mm) are unknown.
- Whether the TPU brow bars were printed and fitted is not recorded.
- Whether a tongue servo will be fitted is not recorded after 2026-10-29.

---

## 2. Skin plan: material, thickness, fabrication, anchors, connections, known issues

### Takeaway
The skin is Smooth-On Dragon Skin FX-Pro (Shore 2A), cast from a one-piece plaster/bandage mold of a Monster Clay sculpt on a printed MakeHuman-derived face mask; it was cast and fitting began 2026-10-26, but the snap-attachment milestone (M4) was never started, so how the moving skin is tied to the lips, brows and jaw is not documented beyond plans, and only the eyelids have a designed (untested) keying method.

### Cited Findings

**Material**
- Dragon Skin FX-Pro, "brushed on in layers", for the snap pads and every face cast; Shore 2A; mix 1A:1B; pot life 12 min; demold 40 min at 23 °C; do not cure below 18 °C; tear 61 pli; elongation 763 %; "firmer and tougher than a 00-30 silicone: better at the snaps (R4), more pull on the servos (R11)"; kit: Ease Release 200, acrylic/petroleum-jelly/SuperSeal sealer (never shellac), THI-VEX, Silc Pig, optional Slacker — [docs/PLAN.md:395](../../docs/PLAN.md#L395) (D21).
- It overrides the brief's Ecoflex 00-30 / PlatSil Gel-OO30 candidates — [docs/BUILD_LOG.md:613](../../docs/BUILD_LOG.md#L613).
- Quantity: "Trial, 2 lb", "1 or 2 units [confirm]" — [docs/BOM.md:114](../../docs/BOM.md#L114); "Whether the one unit bought is enough for the pads and the face casts has not been checked" — [docs/BUILD_LOG.md:623](../../docs/BUILD_LOG.md#L623).

**Thickness**
- `SKIN_T = 5.0` (ASSUMPTION, one value for M1) and `LIP_SKIN_T = 8.0` (ASSUMPTION, in front of the lip plates) — [cad/params.py:110-111](../../cad/params.py#L110); these "stay ASSUMPTIONs until FX-Pro samples are tested on the brows and lips" — [docs/BUILD_LOG.md:620](../../docs/BUILD_LOG.md#L620).
- Thinnest skin assumed 3 mm (`SCULPT_MIN_SKIN`) — [cad/params.py:348](../../cad/params.py#L348); "Thinnest skin still open" — [docs/PLAN.md:362](../../docs/PLAN.md#L362) (Q15).
- The mold base allows clay "(ASSUMPTION up to 12)" over the mask — [cad/params.py:428-429](../../cad/params.py#L428).
- Eyelid skin budget: feather to under 0.4 mm within about 12 mm of the inner eye corner and under about 1.5 mm elsewhere, because the face skin passes 0.7 mm over the lid at the inner corner once a lid has closed 20° — [docs/PRINT_GUIDE.md:11](../../docs/PRINT_GUIDE.md#L11), [docs/BUILD_LOG.md:90](../../docs/BUILD_LOG.md#L90).

**How it is made**
- What the sculptor worked on: a printed face mask, a thin shell of a man's face (MakeHuman CC0), eyes on the eye mechanism and lips on Cogley's lips — [docs/PLAN.md:391](../../docs/PLAN.md#L391) (D19). Shell thickness `MASK_T = 2.0` — [cad/params.py:410](../../cad/params.py#L410). Its outside keeps 3 mm from Cogley's parts (v2 on) — [docs/BUILD_LOG.md:827](../../docs/BUILD_LOG.md#L827), [docs/BUILD_LOG.md:841](../../docs/BUILD_LOG.md#L841); v1 was 6.9 mm from the nearest part (left brow bar) — [docs/BUILD_LOG.md:857](../../docs/BUILD_LOG.md#L857).
- The printed mask (v9)'s lip groove is 5–7 mm low; the lip line had to be sculpted 71.2 mm below the eye line, 69 mm corner to corner — [docs/BUILD_LOG.md:689-695](../../docs/BUILD_LOG.md#L689), [docs/PRINT_GUIDE.md:48](../../docs/PRINT_GUIDE.md#L48).
- The face was sculpted in Monster Clay on the mask (2026-10-21); the plaster mold is one piece (splash coat, then plaster-bandage shell, Ease Release 200 on the clay), laid up 2026-10-21/22; whether Ultracal 30 and the printed mold base were used "is not recorded" — [docs/BUILD_LOG.md:621](../../docs/BUILD_LOG.md#L621).
- The mold procedure and the printed mold base, which later holds the cleaned mask "as the core for the silicone cast" so "the skin's thickness equal[s] the clay's" — [docs/PLASTER_MOLD.md:30-32](../../docs/PLASTER_MOLD.md#L30); one-piece option A thickens the skin by the ears and jaw, trimmed after casting — [docs/PLASTER_MOLD.md:45-48](../../docs/PLASTER_MOLD.md#L45).
- Mold prep and casting: dry fully, seal (no shellac, no alcohol), test-cure on scrap, Ease Release 200, cast at ≥18 °C, THI-VEX for brush-on layers — [docs/PLASTER_MOLD.md:175-209](../../docs/PLASTER_MOLD.md#L175).
- Status: "skin cast; fitting started 2026-10-26 (team report)" — [docs/PLAN.md:19](../../docs/PLAN.md#L19); "the skin is cast, and it goes on today with the whole head assembled" (team report, "not checked here") — [docs/BUILD_LOG.md:544](../../docs/BUILD_LOG.md#L544).
- Coverage: Cogley's outer shell is "a helmet over the top and back of the head. The face below it is open mechanics, with the cheek-bone band under the eyes" — [docs/BUILD_LOG.md:904](../../docs/BUILD_LOG.md#L904). The mask's outline runs "from the chin over the forehead onto the skull, and round to the ears" — [docs/PRINT_GUIDE.md:47](../../docs/PRINT_GUIDE.md#L47).

**Anchors and connections**
- The brief's attachment concept: fabric pads cast into the skin with 7 mm sew-on snaps, the mating half on a printed linkage adapter, snap axis normal to the skin so motion loads it in shear, plus an unsnap support tool — [docs/BRIEF.md:204-224](../../docs/BRIEF.md#L204), [docs/PLAN.md:313-321](../../docs/PLAN.md#L313). Fixed areas get "low-profile clips or snap attachments at the rear skull" — [docs/BRIEF.md:234](../../docs/BRIEF.md#L234).
- Plan for Cogley's head: "snaps on the brow bars, the lips and the jaw; fixed points on his shell and cheek bone (M4)" — unchecked — [docs/PLAN.md:189](../../docs/PLAN.md#L189).
- BOM snap quantity: "4 for the brows (+ the lips, M4)"; product not chosen (Q8) — [docs/BOM.md:127](../../docs/BOM.md#L127), [docs/PLAN.md:357](../../docs/PLAN.md#L357).
- M4 (snap prototype) "not started" — [docs/PLAN.md:17](../../docs/PLAN.md#L17); "Snap adapters on the pads (with M4)" unchecked — [docs/PLAN.md:259](../../docs/PLAN.md#L259).
- The custom (now backup) brow had two 10 mm snap pads per brow at |x| 22 and 52 — [cad/params.py:208-209](../../cad/params.py#L208).
- Eyelids: keyed lids (D27), 21–24 radial Ø2.2 through-holes per lid with Ø3.4 × 0.7 counterbores, so the brushed silicone cures into rivets; platinum silicone has no bond to PLA; ASSUMPTION until a test cast (Q22) — [docs/PLAN.md:403](../../docs/PLAN.md#L403). Q22 is open: "print `cogley_lids_keyed_plate.stl` and cast one lid first" — [docs/PLAN.md:369](../../docs/PLAN.md#L369). Reviewer: "proven in shear but not in peel for a Shore 2A silicone (a 0.7 mm head through a Ø2.2 neck holds about 1 N…)"; a clamped lash edge is the fallback — [docs/BUILD_LOG.md:90](../../docs/BUILD_LOG.md#L90).
- Whether lids get separate moving skins or the main skin forms them is still open (D7) — [docs/PLAN.md:383](../../docs/PLAN.md#L383); the brief raised separate eyelid skins — [docs/BRIEF.md:101](../../docs/BRIEF.md#L101).
- A "perfect neutral" pose (eyes closed, mouth closed) was set for working out the skin attachment — [docs/BUILD_LOG.md:452-458](../../docs/BUILD_LOG.md#L452).
- Sil-Poxy is listed only for silicone-to-silicone repair (re-attaching a pad) — [docs/BOM.md:120](../../docs/BOM.md#L120).

**Known issues and risks**
- R4: soft silicone tears at the snaps — [docs/PLAN.md:415](../../docs/PLAN.md#L415).
- R11: MG90S torque against unknown skin forces; FX-Pro is firmer than planned; fix by Slacker or thinning the skin locally — [docs/PLAN.md:422](../../docs/PLAN.md#L422).
- R5: the jaw pivot may not sit where a human jaw hinges, stretching the cheeks oddly — [docs/PLAN.md:416](../../docs/PLAN.md#L416).
- R13: mold undercuts at the ears and jaw (96 cm²) — [docs/PLAN.md:424](../../docs/PLAN.md#L424).
- The mold had "tiny clay specks" — [docs/BUILD_LOG.md:621](../../docs/BUILD_LOG.md#L621).
- Proportions: Cogley's lips sit 71 mm below the eyes at 75 mm eye spacing, where a normal face would be about 85 mm ("a short mid-face, a little cartoonish") — [docs/PLAN.md:364](../../docs/PLAN.md#L364), [docs/BUILD_LOG.md:928](../../docs/BUILD_LOG.md#L928).

### Inferences
- **(inferred)** Because the skin's inner surface (the mask's outer surface) was kept at least 3 mm off Cogley's parts, any snap on a lip plate, brow bar or jaw has to bridge that gap with a standoff or adapter; the mechanism does not touch the skin by default.
- **(inferred)** With M4 never started, the skin on the head at NightHack is either attached by an undocumented method or only draped/fixed at its edges; the files do not say which.
- **(inferred)** There is a tension between "brushed on in layers" ([docs/PLAN.md:395](../../docs/PLAN.md#L395)) and the mold base's "core" casting that sets skin thickness to the clay's ([docs/PLASTER_MOLD.md:30-32](../../docs/PLASTER_MOLD.md#L30)); which process produced the cast skin is not recorded.

### Gaps
- No record of the cast skin's actual thickness, weight, colour, or where and how it was attached on 2026-10-26 onward.
- No pull-off or cycle-test data for any attachment (M4 not started).
- No measured servo load with skin on (R11), and no skin-on motion test (M7 not started, [docs/PLAN.md:20](../../docs/PLAN.md#L20)).
- Whether the keyed lids were printed or skinned is not recorded.

---

## 3. Control: servos and channels, Picos, UART link, update rate, power, and how software turns emotion into poses

### Takeaway
A laptop runs everything and talks over USB to the mouth Pico (Board 1), which forwards `e <pin> <angle>` lines one-way over UART to the eye/brow Pico (Board 2). Only the mouth is driven by Frank's conversation software today (loudness-driven jaw and lips, brightness-driven corner width, a tag-driven smile/frown on the corners); eye idle/blink animation and brow expressions exist as separate bench tools and are not connected to Frank's expression tags or to vision.

### Cited Findings

**Boards and channels**
- Two Cogley mouth boards run the head: Board 1 mouth (11 mouth servos, on the laptop's USB) and Board 2 eyes + brows (6 eye + 4 brow servos, reached through Board 1) — [firmware/README.md:3-5](../../firmware/README.md#L3). Each board has 12 servo outputs GP4–GP15 and an XT60 power input — [docs/BOM.md:14](../../docs/BOM.md#L14).
- Board 1 sockets: JL GP4, JR GP5 (jaw MG996R), LUL GP6, LUR GP7, LLL GP8, LLR GP9, CUL GP10, CUR GP11, CLL GP12, CLR GP13, TON GP14, EXA GP15 empty — [Head Power Wiring artifact](https://claude.ai/artifact/NNjtnRuZohye1SKmWCQ5Gw), [docs/BUILD_LOG.md:637](../../docs/BUILD_LOG.md#L637). Board 2: JL/JR/LUL/LUR brows, LLL/LLR eyes, CUL/CUR/CLL/CLR lids, TON and EXA empty — same artifact; [firmware/README.md:11](../../firmware/README.md#L11).
- Channel use: Board 1 "11 of 12 outputs" (with the tongue), Board 2 "10 of 12" — [docs/BOM.md:14](../../docs/BOM.md#L14). With no tongue servo fitted, Board 1 drives 10 servos (inferred from [frank/mouth.py:90](../../frank/mouth.py#L90)).
- Pico models: README says Board 1 is an RP2040 Pico and Board 2 a Pico 2 (RP2350) — [firmware/README.md:53](../../firmware/README.md#L53); the build log says the mouth board "turned out to be a Pico 2" — [docs/BUILD_LOG.md:64](../../docs/BUILD_LOG.md#L64), [docs/BUILD_LOG.md:34](../../docs/BUILD_LOG.md#L34) (contradiction).
- D18 originally decided three boards; the wiring doc and firmware now use two — [docs/PLAN.md:390](../../docs/PLAN.md#L390), [docs/BUILD_LOG.md:430](../../docs/BUILD_LOG.md#L430).

**Programs and link**
- Board 1 runs TalkingHead's `cogley_mouth_main.py` (Cogley's MouthMaster with gliding, clamping, `jaw`, `set`, `talk`, `speed`, `where`) or `pico_servo_ctl.py`; Board 2 runs `pico_servo_ctl.py` — [firmware/README.md:7](../../firmware/README.md#L7), [firmware/cogley_mouth_main.py:1-24](../../firmware/cogley_mouth_main.py#L1). As of 2026-10-30 Board 1 runs `cogley_mouth_main.py` — [docs/BUILD_LOG.md:34](../../docs/BUILD_LOG.md#L34).
- UART link (D28): a line `e <pin> <angle>` is forwarded over UART0 (GP16 TX, 115200 baud) to the other board's GP17; the wires cross; "Nothing comes back from Board 2 yet" — [docs/PLAN.md:404](../../docs/PLAN.md#L404), [firmware/README.md:47](../../firmware/README.md#L47). Cogley's original 2-bit link (four states per function: eyes_move/open/close, brows up/down/happy/angry) was dropped because the laptop moves "every servo by name at a steady frame rate" — [docs/PLAN.md:404](../../docs/PLAN.md#L404), [firmware/cogley_mouth_main.py:101-109](../../firmware/cogley_mouth_main.py#L101).
- End-to-end test 2026-10-29: "jaw, eyes, lids and brows ran together for 30 s through the mouth board's port alone … the link works end to end" — [docs/BUILD_LOG.md:66](../../docs/BUILD_LOG.md#L66).
- Pulse mapping: Board 1 544–2400 µs over 0–180 — [firmware/cogley_mouth_main.py:50-51](../../firmware/cogley_mouth_main.py#L50); Board 2 500–2500 µs, extended to 200–2800 µs — [firmware/pico_servo_ctl.py:6-8](../../firmware/pico_servo_ctl.py#L6), [firmware/pico_servo_ctl.py:78](../../firmware/pico_servo_ctl.py#L78).

**Update rates**
- Servo PWM 50 Hz — [firmware/cogley_mouth_main.py:133](../../firmware/cogley_mouth_main.py#L133); board glide loop `TICK_MS = 20` — [firmware/cogley_mouth_main.py:53](../../firmware/cogley_mouth_main.py#L53).
- Frank's mouth driver sends the jaw 50 times a second and the lips/corners 25 times a second, only on change — [frank/mouth.py:18-19](../../frank/mouth.py#L18), [frank/mouth.py:82](../../frank/mouth.py#L82), [frank/mouth.py:340-343](../../frank/mouth.py#L340).
- EYES ALIVE runs at 50 Hz through the slider link — [docs/BUILD_LOG.md:445](../../docs/BUILD_LOG.md#L445); the laptop sends "every servo by name, 25–50 times a second" — [docs/BUILD_LOG.md:64](../../docs/BUILD_LOG.md#L64).

**Power**
- Power chain: UGREEN Nexode 25,000 mAh 145 W bank (or JUYOON 140 W charger) → USB-C PD trigger at 20 V → F1 7.5 A → ACEIRMC 20 A buck at 5.30 V → WAGO buses → F2/F3 10 A → two XT60 leads, 1000 µF on the bus — [docs/PLAN.md:366](../../docs/PLAN.md#L366) (Q19).
- Budget from the wiring artifact: buck "15 A continuous (20 A peak)" against "Cogley spec 10 A; likely 3–8 A while talking"; 20 V side "5.3 V × 15 A ÷ 0.92 ≈ 86 W → 4.3 A"; servo voltage after the board's diode "4.8–5.0 V"; board fuses 10 A protect the board diode (SS1045, 10 A) — [Head Power Wiring artifact](https://claude.ai/artifact/NNjtnRuZohye1SKmWCQ5Gw) (Compatibility checks). The artifact's own banner says it was superseded for step order by the Build Guide the same day.
- MG90S stall ≈700 mA measured (SG90 360 mA) — [docs/BOM.md:31](../../docs/BOM.md#L31); "An MG90S can draw about 0.7 A when stalled, and a board drives up to 10 servos. Cogley powers the whole head from 5 V 10 A" — [firmware/README.md:67-68](../../firmware/README.md#L67).
- Field issues: the Pico "dropped off USB twice today while servos moved (a brown-out…)" — [docs/BUILD_LOG.md:114](../../docs/BUILD_LOG.md#L114); without the BOARD POWER jumper the Pico is powered only by USB — [firmware/README.md:64](../../firmware/README.md#L64), [docs/BUILD_LOG.md:66](../../docs/BUILD_LOG.md#L66). The board program glides servos "so the MG996R jaw servos don't kick the supply" — [firmware/cogley_mouth_main.py:9-10](../../firmware/cogley_mouth_main.py#L9).
- R6: 19+ servos in a closed skin build heat; Cogley uses a 50 mm fan; under the skin the air must leave through the neck — [docs/PLAN.md:417](../../docs/PLAN.md#L417).

**Character and software contract**
- The character bible asks for "Very theatrical" facial movement with "natural timing, asymmetry, and relaxed transitions"; signature expression "Dramatically animated eyebrows" — [docs/CHARACTER.md:343-347](../../docs/CHARACTER.md#L343), [docs/CHARACTER.md:370](../../docs/CHARACTER.md#L370). It lists available mechanics as eye H/V, lid blinking and narrowing, independent brow raise and furrow, jaw, lips, tongue — [docs/CHARACTER.md:333-338](../../docs/CHARACTER.md#L333).
- Nine expression states are specified feature by feature (curiosity, excitement, skepticism, amusement, concentration, confusion, irritation, surprise, vulnerability), plus a greeting sequence and listening/speech rules — [docs/CHARACTER.md:362-435](../../docs/CHARACTER.md#L362). Animation principle: not every movement at once; distinct timing — [docs/CHARACTER.md:438](../../docs/CHARACTER.md#L438).
- Architecture: "Hybrid control. The AI determines the intended emotional expression … A motor-control system translates that intent …"; suggested states Idle, Person detected, Greeting, Listening, Thinking, Speaking, Interrupted, Farewell, Returning to idle — [docs/CHARACTER.md:865-882](../../docs/CHARACTER.md#L865).
- Tag vocabulary: `[neutral] [curious] [excited] [skeptical] [amused] [concentrating] [confused] [irritated] [surprised] [vulnerable]` plus `[chuckle]` — [frank/README.md:52](../../frank/README.md#L52), [frank/speech.py:17-18](../../frank/speech.py#L17). Every reply starts with a tag; at most one change after the first; resting faces are neutral, skeptical, concentrating — [frank/system_prompt.md:54](../../frank/system_prompt.md#L54), [frank/system_prompt.md:64-67](../../frank/system_prompt.md#L64). Off-list words are mapped by aliases (e.g. puzzled → confused, worried → vulnerable) or dropped — [frank/speech.py:20-32](../../frank/speech.py#L20).
- Tags are categorical events (`("face", "curious")`) with no intensity parameter — [frank/speech.py:6-9](../../frank/speech.py#L6). "The controller owns timing, blending, intensity and the servo limits" — [frank/README.md:59](../../frank/README.md#L59). The face controller "(states, expressions, gaze, lip sync to the servos) is the creators' to design" — [frank/README.md:222](../../frank/README.md#L222), team decision [docs/BUILD_LOG.md:372](../../docs/BUILD_LOG.md#L372).
- Tags also become ElevenLabs v3 delivery tags (`[concentrating]` → `[thoughtful]`, etc.) — [frank/README.md:19](../../frank/README.md#L19).

**What actually drives servos from Frank today (mouth only)**
- `frank/mouth.py`: loudness (−42 dBFS shut … −16 dBFS at 85 % of OPEN; attack 35 ms, release 90 ms, 50 ms delay, shut after 120 ms silence) opens the jaw; lips part more lazily (60 % of lips_up/lips_down; 60/150 ms); spectral centroid 400–2500 Hz pulls the corners toward WIDE (max 70 %); the tag adds smile or frown under the corners — [frank/mouth.py:1-19](../../frank/mouth.py#L1), [frank/mouth.py:75-94](../../frank/mouth.py#L75).
- Tag → corner mood map: amused 0.8, excited 0.6, curious 0.3, surprised 0.2, irritated −0.8, skeptical −0.5, concentrating −0.3, confused −0.2; neutral and vulnerable get 0; mood eases in over 0.5 s — [frank/mouth.py:69-70](../../frank/mouth.py#L69), [frank/mouth.py:89](../../frank/mouth.py#L89).
- Vowel blending (AH/EE/OO shapes picked by brightness, scaled by loudness) runs only once all three are saved in `firmware/mouth_poses.json` — [frank/mouth.py:151-152](../../frank/mouth.py#L151), [docs/BUILD_LOG.md:110](../../docs/BUILD_LOG.md#L110). No `mouth_poses.json` exists in the repo (Glob search, 2026-10-30), so Cogley's angles and the loudness/brightness mode are what runs.
- `Mouth.link()` can reach the eye board — [frank/mouth.py:198-204](../../frank/mouth.py#L198) — but a search of `frank/` found no caller of `link()` and no brow, eye or lid output; the only consumers of a face tag are `Mouth.face()` (corners) and the voice — [frank/voice.py:424](../../frank/voice.py#L424), [frank/mouth.py:233-236](../../frank/mouth.py#L233).
- Board-side "talk" chatter mode (random syllables of 1–4 with pauses) also exists — [firmware/cogley_mouth_main.py:201-238](../../firmware/cogley_mouth_main.py#L201).

**Eye and brow behaviour (bench tools in `firmware/`, driven from the slider window)**
- `eye_anim.py`: random look-around (small shifts, returns to centre, big glances), ±30° pan and ±15° tilt about centre, eased moves of 0.08 + 0.15 × distance s; blinks about 18 a minute (gap 2.5–7 s), 10 % slow blinks, 15 % double blinks, 30 % blink on big glances; blink shape close 0.08 / hold 0.05 / open 0.15 s; lids rest at 0.85 of open; top lids follow gaze ±0.25, bottom ±0.15; `MOVE_BOTTOM_LIDS = True` — [firmware/eye_anim.py:19-31](../../firmware/eye_anim.py#L19), [firmware/eye_anim.py:56-100](../../firmware/eye_anim.py#L56), [docs/BUILD_LOG.md:444](../../docs/BUILD_LOG.md#L444).
- `brow_anim.py`: the CHARACTER.md §6 shapes as keyframes in fractions of RAISE/LOWER per servo — neutral, curious (both 0.6), excited (both 1.0), skeptical (left up 0.8/0.6, right down), amused, concentrating (inner ends down more), confused (furrow then lift), irritated (both −0.8), surprised (fast lift then slow return), vulnerable (inner up, outer slightly down), greeting, furrow; smoothstep easing; an additive idle layer (drifts, one-brow flicks, settling, ±0.2) — [firmware/brow_anim.py:30-85](../../firmware/brow_anim.py#L30), [firmware/brow_anim.py:122-163](../../firmware/brow_anim.py#L122). "Not yet watched on the brows" as of 2026-10-29 — [docs/BUILD_LOG.md:124](../../docs/BUILD_LOG.md#L124).
- Both are run by buttons in `servo_controls.py` (EYES ALIVE, BROWS ALIVE, BROW SHOW) — [firmware/README.md:37-39](../../firmware/README.md#L37).

**Vision available for gaze**
- `eyes.py` tracks faces with distance, yaw and pitch "from his eyes" and knows who is speaking via MediaPipe `jawOpen` — [frank/README.md:131-133](../../frank/README.md#L131), [frank/eyes.py:209](../../frank/eyes.py#L209), [frank/README.md:222](../../frank/README.md#L222) ("`eyes.Eyes.state` already holds where everyone is … for its gaze").
- The system prompt tells Frank the controller "keeps your eyes on whoever is speaking" — [frank/system_prompt.md:62](../../frank/system_prompt.md#L62).

### Inferences
- **(inferred)** The face as a whole is not yet a "face engine": mouth lip-sync is live, eyes/brows have standalone procedural animation, and no layer combines tags, controller states, gaze and idle into one stream. The system prompt's promise of speaker-following gaze is not implemented in the files.
- **(inferred)** Lip-sync is amplitude-and-brightness based, with no phoneme or viseme timing from the TTS; with the vowel shapes unsaved, mouth shape varies only in width and opening.
- **(inferred)** The one-way, open-loop link (no position, current or temperature feedback) means stalls (like the lid buzzing at 196) are found by ear only.
- **(inferred)** Channel headroom is small: Board 1 has EXA (and TON, if the tongue stays out) free; Board 2 has TON and EXA free. Adding more than about 3–4 servos needs a third board or a PWM expander.
- **(inferred)** At ~0.7 A stall per MG90S, 19 MG90S stalled at once would be about 13 A plus the two MG996Rs, above the 10 A per-board fuse if concentrated on one board; the wiring artifact expects 3–8 A in normal talking.

### Gaps
- The Head Power Wiring Build Guide (the newer doc, a Claude Doc) was not read; only the superseded first artifact's compatibility table was.
- The "performance engine" planned for Friday ([docs/BUILD_LOG.md:64](../../docs/BUILD_LOG.md#L64), [docs/BUILD_LOG.md:74](../../docs/BUILD_LOG.md#L74)) is not in the repo, and `research_notes/Face engine plan research/` is empty.
- No measured current draw, runtime or thermal data for the head (the artifact lists these as tests to run).
- MG996R current figures are not given in the files.

---

## 4. Space and structure: reserved volumes, free space, cable channels, built vs CAD-only, what is expensive to change

### Takeaway
The head is Cogley's printed cage frame with his modules packed tightly inside, a cast skin over the face and his helmet shell over the back, clamped onto a printed neck inside a printed canister. The reserved-volume work (brow bays, cable channel) belongs to the retired custom skull; for Cogley's head the files give clearances between parts but no inventory of free space, and every lead plus the fan air shares one ~530 mm² hole and a Ø25 bore through the neck.

### Cited Findings

**Frame and packing**
- `SkullFrame` is "a cage: a band round the front at eye level and ribs over the crown. Everything bolts to it"; `CheekBone` band under the eyes and a `FanBracket` for a 50 mm fan — [docs/PLAN.md:63](../../docs/PLAN.md#L63).
- The mouth's top plate is the eye shelf (EyeMech base plate 0.2 mm above it) — [docs/PLAN.md:66](../../docs/PLAN.md#L66); the nearest part to any eye servo is the mouth's top plate, 2.7 mm away — [docs/ASSEMBLY.md:17](../../docs/ASSEMBLY.md#L17).
- The printed EyeMech set clears all his other parts: lids swept ≥ 5.7 mm, eyes swept ≥ 8.2 mm — [docs/PLAN.md:77](../../docs/PLAN.md#L77).
- Face skin to lid: 0.7 mm at the inner corner once a lid has closed 20°; skull front pieces ≥ 3.9 mm through the lid travel — [docs/BUILD_LOG.md:90](../../docs/BUILD_LOG.md#L90).
- Head mass about 3 kg with skin, about 50 mm in front of the spine — [docs/PLAN.md:396](../../docs/PLAN.md#L396).
- Inside the enclosure, the window sheet is 19 mm clear of the face and 21 mm of the nape — [cad/params.py:471](../../cad/params.py#L471).

**Reserved volumes (historical, custom skull)**
- `reserve.py`: a brow bay per side (48 × 67 × 55, ≥ 2.4 from the EyeMech, 3.5 from the open lids) and a Ø25 cable channel down the back of the neck — [docs/PLAN.md:227](../../docs/PLAN.md#L227), [cad/params.py:183-191](../../cad/params.py#L183). These were sized for the proxy head and skull v0, which D17 retired — [docs/BUILD_LOG.md:908](../../docs/BUILD_LOG.md#L908).

**Cable and air path**
- Leads go "down through the hexagonal hole in the frame's bottom ring at the back of the head, then through the hole in the collar, down the spine and the tube, through the bore into the pedestal and out of the lead door"; "Leave slack at the head for the jaw and the eyes" — [docs/ASSEMBLY.md:84](../../docs/ASSEMBLY.md#L84).
- The cable/air hole through the clamp plates, collar and spine top is 28 wide, y −121..−101, "about 530 mm²" — [cad/params.py:591-593](../../cad/params.py#L591); the bore through the neck foot and pedestal top is Ø25 — [cad/params.py:518](../../cad/params.py#L518). The pedestal had no way into the bay until a hand-cut 40 × 50 mm door (R14) — [docs/PLAN.md:425](../../docs/PLAN.md#L425).
- The jaw clears the neck by 9.6 mm at 25° and 2.5 mm at 35° — [docs/PLAN.md:396](../../docs/PLAN.md#L396); asserts keep the neck under the jaw's overtravel sweep — [cad/params.py:596-597](../../cad/params.py#L596).
- The neck spine's back corners stick out of the sculpt's neck by up to about 10 mm; "the skin's neck will need room there" — [docs/BUILD_LOG.md:193](../../docs/BUILD_LOG.md#L193).
- The fan's air path under the skin is still open — [docs/PLAN.md:16](../../docs/PLAN.md#L16), [docs/PLAN.md:191](../../docs/PLAN.md#L191).

**Built vs CAD-only**
- Printed: the eyes (ε3.2 MG90s-A), mouth, teeth and tongue, "Brows - Main"; frame, extras and outer shell cleared to print (2026-10-16) — [docs/PLAN.md:182](../../docs/PLAN.md#L182). Eyes and mouth working; whole head being assembled (team report 2026-10-26) — [docs/PLAN.md:16](../../docs/PLAN.md#L16).
- Custom brow v1.1 printed (bench backup) — [docs/PLAN.md:15](../../docs/PLAN.md#L15).
- Face mask v9 printed and sculpted; mold made; skin cast — [docs/PLAN.md:18-19](../../docs/PLAN.md#L18).
- Enclosure v1 modelled; build manual written 2026-10-30; "the pedestal may already be printed" — [docs/PLAN.md:21](../../docs/PLAN.md#L21), [docs/BUILD_LOG.md:49](../../docs/BUILD_LOG.md#L49).
- Not started or CAD-only: M4 snaps, M7 validation — [docs/PLAN.md:17](../../docs/PLAN.md#L17), [docs/PLAN.md:20](../../docs/PLAN.md#L20); mold core, exports and attachment CSV — [docs/PLAN.md:337](../../docs/PLAN.md#L337); keyed lids (next print, Q22) — [docs/BUILD_LOG.md:92](../../docs/BUILD_LOG.md#L92); skull v0 "not ready to print" — [docs/PRINT_GUIDE.md:39](../../docs/PRINT_GUIDE.md#L39).
- Servo health: lower lid CUL dead, being replaced (2026-10-30) — [docs/BUILD_LOG.md:38](../../docs/BUILD_LOG.md#L38); JL brow servo faulty (2026-10-26) — [docs/BUILD_LOG.md:474](../../docs/BUILD_LOG.md#L474); a lower-lip servo hot-glued after a stripped insert — [docs/BUILD_LOG.md:568](../../docs/BUILD_LOG.md#L568).

**What constrains changes**
- Cogley's head comes as meshes only (no STEP); changing his parts means mesh booleans, and the OBJ lacks 2 brow servos (R12) — [docs/PLAN.md:60](../../docs/PLAN.md#L60), [docs/PLAN.md:421](../../docs/PLAN.md#L421).
- Lowering his mouth 13.4 mm "pushes it into his frame (580 sample points inside)", so it would mean redrawing his mouth mounts — [docs/BUILD_LOG.md:929](../../docs/BUILD_LOG.md#L929); decided to keep his mouth (D17/Q16) — [docs/PLAN.md:389](../../docs/PLAN.md#L389).
- EyeMech is CC BY-NC-SA 4.0: modified versions must be shared alike; changing their base "would create a derivative work" — [docs/PLAN.md:89](../../docs/PLAN.md#L89), [docs/PLAN.md:112](../../docs/PLAN.md#L112), [docs/PLAN.md:359](../../docs/PLAN.md#L359). The repo is private because the Cogley files are Patreon member files — [inputs/reference/README.md:7-9](../../inputs/reference/README.md#L7).
- The neck clamps his frame's nape ring with nothing drilled (D27) — [docs/PLAN.md:398](../../docs/PLAN.md#L398).

### Inferences
- **(inferred)** The most expensive things to change now are the ones already physical and mutually fitted: the skin (cast from a one-piece mold of a sculpt registered to this mechanism), the mouth position, the eye spacing (75 mm, fixed by the EyeMech), and the enclosure (sized around the head with about 19–21 mm clearance). Any added mechanism that moves the skin's inner surface outward, or needs skin anchors where none were cast, implies a new sculpt or at least a new cast.
- **(inferred)** Adding motors inside the head is constrained by (a) the tight module packing (2.7 mm, 5.7 mm, 8.2 mm clearances), (b) only ~3 mm between Cogley's parts and the skin's inner surface, (c) the single ~530 mm² lead/air hole and Ø25 bore, and (d) 3–4 free PWM channels.
- **(inferred)** A neck (pan/tilt/nod) would sit between the clamp and the pedestal, where the leads and fan air already run, and would change the enclosure clearances; it is outside the brief.

### Gaps
- No volumetric free-space map of Cogley's head exists in the files (the reserved-volume check was for the retired skull).
- No record of which Cogley parts are printed in which material, or of the fan actually fitted.

---

## 5. Project constraints: deadlines, budget, tools, materials bought

### Takeaway
The first public appearance is NightHack, San Francisco, on 2026-10-30 (today), with Halloween as the other target; but the character is meant to be ongoing and transportable, so a post-event redesign horizon exists. The maker has two Bambu P2S printers and a soldering iron, no drill; the budget sheet is kept outside the repo.

### Cited Findings
- First public appearance: NightHack, San Francisco, 2026-10-30 — [docs/PLAN.md:19](../../docs/PLAN.md#L19), [docs/BUILD_LOG.md:550](../../docs/BUILD_LOG.md#L550).
- Q1: "Aiming for before Halloween, but the team owns the schedule: plan the full scope" — [docs/PLAN.md:350](../../docs/PLAN.md#L350). R7 schedule risk — [docs/PLAN.md:418](../../docs/PLAN.md#L418).
- Frank is "an ongoing character rather than a one-night Halloween attraction", permanent home the SCAD Satellite Lab, Savannah, transportable to events — [docs/CHARACTER.md:40-48](../../docs/CHARACTER.md#L40). Scare level 2/10 — [docs/CHARACTER.md:52](../../docs/CHARACTER.md#L52).
- Team: creators Anushhka and Lars — [docs/BUILD_LOG.md:483](../../docs/BUILD_LOG.md#L483).
- Printers: 2 × Bambu Lab P2S, 256 × 256 × 256 bed, 0.4 nozzle assumed — [docs/PLAN.md:351](../../docs/PLAN.md#L351).
- Tools: "The human has no drill (2026-10-29)"; inserts set with the soldering iron in printed holes — [docs/PLAN.md:398](../../docs/PLAN.md#L398); "Nothing is drilled" — [docs/ASSEMBLY.md:65](../../docs/ASSEMBLY.md#L65); the speaker was chosen ready-made because there was "no time" to solder — [docs/PLAN.md:366](../../docs/PLAN.md#L366).
- Laptop: a Mac (M5 Pro) runs the software — [docs/BUILD_LOG.md:280](../../docs/BUILD_LOG.md#L280); "the full system runs from the laptop … the Pi does nothing on its own" — [docs/BUILD_LOG.md:546](../../docs/BUILD_LOG.md#L546) (the bible's Raspberry Pi architecture is not used, [docs/CHARACTER.md:772-786](../../docs/CHARACTER.md#L772)).
- Budget: the team's `Halloween_Animatronic_Budget.xlsx` is kept out of the repo — [docs/BUILD_LOG.md:1056](../../docs/BUILD_LOG.md#L1056); the budget workbook marks Ecoflex as not buying — [docs/BUILD_LOG.md:618](../../docs/BUILD_LOG.md#L618). The power parts still to buy totalled "about $189" (2026-10-26) — [Head Power Wiring artifact](https://claude.ai/artifact/NNjtnRuZohye1SKmWCQ5Gw) ("Still to buy").
- Materials on hand or bought: Dragon Skin FX-Pro (1–2 Trial units), Ease Release 200 [have]; THI-VEX and Silc Pig ordered; Sil-Poxy in cart; mold sealer to buy; Bulls Eye shellac bought but not for the mold — [docs/BOM.md:114-120](../../docs/BOM.md#L114). Monster Clay 6 lb — [docs/PLAN.md:362](../../docs/PLAN.md#L362). Sony SRS-XB12 speaker and Logitech webcam [have] — [docs/BOM.md:143-144](../../docs/BOM.md#L143). TPU 95A [buy] — [docs/BOM.md:12](../../docs/BOM.md#L12). The BOM still lists MG90S as "[buy]" and MG996R as "[confirm]" — [docs/BOM.md:9](../../docs/BOM.md#L9), [docs/BOM.md:13](../../docs/BOM.md#L13).
- Cogley's own supply list for the head: 2 MG996R, 19 MG90S, ~25 M3 and ~10 M4 shoulder screws, inserts, 50 mm fan, 5 V 10 A — [docs/BUILD_LOG.md:631](../../docs/BUILD_LOG.md#L631).

### Inferences
- **(inferred)** The servos must have been bought since the head runs, so the BOM's "[buy]" status is stale.
- **(inferred)** Without a drill or CNC, any upgrade must be printable with holes modelled in, fixed by clamps, heat-set inserts or existing screws (the project's memory and D27 say the same).

### Gaps
- No total spend, remaining budget or per-item costs are in the repo.
- No date for any post-NightHack milestone is recorded.

---

## 6. Open questions, risks and decisions that touch expressiveness

### Takeaway
The open items that bear on how lifelike the face can be are mostly about the skin-to-mechanism interface (snaps, lid keying, skin thickness, servo load) and about unmeasured ranges; the decisions that fixed today's expressive envelope are D14/D17 (Cogley's head and proportions), D15 (two-servo brows), D16/D22 (eyes, painted iris) and D27/D28.

### Cited Findings

**Open questions**
- Q22: do keyed lids hold a brushed FX-Pro skin (peel at the lash edge is the weak mode) — [docs/PLAN.md:369](../../docs/PLAN.md#L369).
- Q15: thinnest skin still open — [docs/PLAN.md:362](../../docs/PLAN.md#L362).
- Q11: who sculpts, skin thickness, separate moving eyelid skins (D7) — [docs/PLAN.md:360](../../docs/PLAN.md#L360), [docs/PLAN.md:383](../../docs/PLAN.md#L383).
- Q8: which 7 mm snaps — [docs/PLAN.md:357](../../docs/PLAN.md#L357).
- Q18: TPU for the brow bars (answer: buy TPU 95A; PLA cracks at the pleats) — [docs/PLAN.md:370](../../docs/PLAN.md#L370).
- Jaw range still the 25° assumption; lip and cheek servo motions "checked with the skin in M4/M6" — [docs/PLAN.md:230-231](../../docs/PLAN.md#L230).
- Brow directions and travel "need the human's eye on the real brows" — [docs/BUILD_LOG.md:126](../../docs/BUILD_LOG.md#L126); Cogley's L/R for mouth servos not matched to face sides — [docs/BUILD_LOG.md:247](../../docs/BUILD_LOG.md#L247).
- Bible open technical decisions include "Motor-control communication protocol" and "Facial lip-sync implementation" — [docs/CHARACTER.md:899-901](../../docs/CHARACTER.md#L899).

**Risks**
- R4 tearing at snaps; R5 jaw hinge vs human hinge stretching the cheeks; R6 heat; R10 narrow brow working window (custom brow); R11 servo torque vs FX-Pro; R12 meshes-only Cogley parts — [docs/PLAN.md:415-422](../../docs/PLAN.md#L415).
- R1: modules fit only with thin margins (0.7–2.5 mm at rest) — [docs/PLAN.md:412](../../docs/PLAN.md#L412).

**Decisions**
- D13 normally proportioned head, not the campy flat-top look — [docs/PLAN.md:387](../../docs/PLAN.md#L387).
- D14/D17 Cogley's head as base, outer shell included, mouth where he put it — [docs/PLAN.md:388-389](../../docs/PLAN.md#L388).
- D15 Cogley's 4-servo TPU brows over the team's 1-servo brows — [docs/PLAN.md:392](../../docs/PLAN.md#L392). (D3/D5, the custom brow concept and its "raise = surprise/worry, lower = anger" coupling, now apply only to the backup — [docs/PLAN.md:379](../../docs/PLAN.md#L379), [docs/PLAN.md:381](../../docs/PLAN.md#L381).)
- D10/D12 keep the tongue (but none is fitted now) — [docs/PLAN.md:386](../../docs/PLAN.md#L386), [docs/PLAN.md:405](../../docs/PLAN.md#L405).
- D16 keep the printed eye set (size-B horns) — [docs/PLAN.md:393](../../docs/PLAN.md#L393); D22 plain eyeball front, painted iris — [docs/PLAN.md:402](../../docs/PLAN.md#L402).
- D19 face mask as the sculpt base — [docs/PLAN.md:391](../../docs/PLAN.md#L391); D21 FX-Pro — [docs/PLAN.md:395](../../docs/PLAN.md#L395).
- D27 (lids) keyed through-holes — [docs/PLAN.md:403](../../docs/PLAN.md#L403); D28 (link) UART forwarding — [docs/PLAN.md:404](../../docs/PLAN.md#L404). Note the plan reuses IDs: D27 and D28 each name two different decisions (neck clamp and band print vs lid keying and UART) — [docs/PLAN.md:398-399](../../docs/PLAN.md#L398), [docs/PLAN.md:403-404](../../docs/PLAN.md#L403).

### Inferences
- **(inferred)** The expressive envelope was set by adopting Cogley's head wholesale (D14/D17): the team traded custom control over proportions and DOF for a proven mechanism, and the remaining open items are integration, not mechanism design.

### Gaps
- No open question in the plan asks for additional DOF (cheeks, neck, vergence, lower-face); expressiveness beyond Cogley's set is not on the plan.

---

## 7. Frank list of current expressive gaps (from the files only)

### Takeaway
Mechanically the head covers eyes, lids, brows, jaw, lips and corners; it lacks neck motion, cheeks, nose, vergence, pupils and a tongue, and the brows lack a medial (corrugator) pull. In software, only the mouth is tied to Frank's emotions; eyes, lids and brows are not yet driven by tags, controller states or vision.

### Cited Findings and gaps, each with its basis
- **No neck or head motion** (no pan, tilt, nod, tilt-to-listen) — [docs/PLAN.md:69](../../docs/PLAN.md#L69), [docs/BRIEF.md:178](../../docs/BRIEF.md#L178), [frank/system_prompt.md:71](../../frank/system_prompt.md#L71); the head is clamped rigid — [docs/PLAN.md:398](../../docs/PLAN.md#L398).
- **Eyes are conjugate only** (one pan, one tilt servo for both), so no vergence on a near visitor — [firmware/servo_controls.py:47-48](../../firmware/servo_controls.py#L47).
- **Eyes are oversized and wide-set** (Ø32 at 75 mm vs ≈24 mm and ≈63 mm human) — [docs/PLAN.md:52-54](../../docs/PLAN.md#L52).
- **No pupil or iris change**; iris painted on a smooth eyeball — [docs/PLAN.md:402](../../docs/PLAN.md#L402).
- **No cheek raise / Duchenne smile:** the `CheekBone` is a static band of the frame — [docs/PLAN.md:63](../../docs/PLAN.md#L63); Cogley's "4 cheek" servos are the mouth corners — [docs/PLAN.md:95](../../docs/PLAN.md#L95), [firmware/README.md:41](../../firmware/README.md#L41). **(inferred)** no lower-lid push from the cheek either, beyond the lid servos.
- **No nose or nostril motion, no forehead wrinkling beyond the brow bars, no chin/mentalis, no neck skin motion** — no actuator for these appears in any servo table ([docs/BOM.md:9](../../docs/BOM.md#L9), [firmware/README.md:11-20](../../firmware/README.md#L11)) **(inferred from absence)**.
- **Brows: two DOF each (inner end and outer end, vertical), no explicit medial pull toward the midline** — Cogley's poses move each end up or down only ([inputs/reference/head_a2.0.33/Code/Brows.py:52-71](../../inputs/reference/head_a2.0.33/Code/Brows.py#L52)); the custom brow's skewed pivot that pulled the inner end toward the midline for anger is only the backup ([docs/PLAN.md:239](../../docs/PLAN.md#L239), [docs/PLAN.md:392](../../docs/PLAN.md#L392)). **(inferred)** whether the TPU bar shows a true corrugator furrow under skin is untested.
- **Brow travel unproven:** Cogley's 10° down "barely showed"; the 35/20 travel is an assumption; directions unchecked; one brow servo faulty — [docs/BUILD_LOG.md:122](../../docs/BUILD_LOG.md#L122), [docs/BUILD_LOG.md:126](../../docs/BUILD_LOG.md#L126).
- **Lips weak on screen:** "the lips and corners hardly showed with his angles" — [docs/BUILD_LOG.md:112](../../docs/BUILD_LOG.md#L112); the three vowel shapes are not yet saved, so no shaped visemes — [frank/mouth.py:151-152](../../frank/mouth.py#L151).
- **No tongue servo fitted** — [frank/mouth.py:90](../../frank/mouth.py#L90).
- **Jaw is one DOF (open/close only)**, no lateral or protrusion; its real range is unmeasured — [firmware/cogley_mouth_main.py:182-185](../../firmware/cogley_mouth_main.py#L182), [docs/PLAN.md:230](../../docs/PLAN.md#L230).
- **Lid travel will shrink under skin** (about 3° per mm on the lash edge) and lid-skin attachment is unproven (Q22) — [docs/PRINT_GUIDE.md:11](../../docs/PRINT_GUIDE.md#L11), [docs/PLAN.md:369](../../docs/PLAN.md#L369).
- **Skin coupling to moving parts is unbuilt:** M4 not started, snap product not chosen, no attachment coordinates exported — [docs/PLAN.md:17](../../docs/PLAN.md#L17), [docs/PLAN.md:357](../../docs/PLAN.md#L357), [docs/PLAN.md:337](../../docs/PLAN.md#L337); the skin sits ≥ 3 mm off the mechanism by design — [docs/BUILD_LOG.md:841](../../docs/BUILD_LOG.md#L841).
- **Software: tags reach only the mouth corners.** `Mouth.face()` is the only servo consumer of a tag; no code sends tags to eyes, lids or brows — [frank/mouth.py:233-236](../../frank/mouth.py#L233), [frank/voice.py:424](../../frank/voice.py#L424); the face controller is "the creators' to design" — [frank/README.md:222](../../frank/README.md#L222).
- **No gaze following** even though vision supplies yaw/pitch per person and the prompt claims it — [frank/README.md:222](../../frank/README.md#L222), [frank/system_prompt.md:62](../../frank/system_prompt.md#L62).
- **No controller states** (Idle, Listening, Thinking, …) implemented; `chat.py` has only a microphone "listening" flag — [frank/README.md:61](../../frank/README.md#L61), [frank/chat.py:308](../../frank/chat.py#L308).
- **Expression tags are categorical with no intensity,** and the prompt limits replies to one tag change — [frank/speech.py:6-9](../../frank/speech.py#L6), [frank/system_prompt.md:54](../../frank/system_prompt.md#L54).
- **Lip-sync is amplitude plus spectral centroid,** not phoneme/viseme timing — [frank/mouth.py:1-19](../../frank/mouth.py#L1).
- **Eye idle is random,** not attention-driven; the brow idle and expressions are bench tools — [firmware/eye_anim.py:56-71](../../firmware/eye_anim.py#L56), [firmware/README.md:37-39](../../firmware/README.md#L37).
- **Open-loop actuation:** no position/current feedback; link is one-way — [docs/PLAN.md:404](../../docs/PLAN.md#L404).
- **Asymmetric hardware calibration:** horns sit differently on splines, so symmetric commands give asymmetric faces; lids were matched by eye — [docs/BUILD_LOG.md:203](../../docs/BUILD_LOG.md#L203).

### Inferences
- **(inferred)** Of the bible's nine expression states, the hardware can approximate most brow and lid components, but "eye widening", "lid narrowing", "squint", "uneven smile" and "gaze toward the person" require software that maps tags to lids, eyes and asymmetric corners, which does not yet exist.
- **(inferred)** The fastest gains without new hardware would come from the controller layer (tag → brows/lids/gaze, vision-driven gaze, saved visemes, intensity), since 15 DOF are already wired and reachable over the link.

### Gaps
- No video, photo or measurement of the skinned face in motion is referenced in the files, so how expressive the face reads with skin on is unknown.

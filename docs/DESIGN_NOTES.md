# Design notes

One entry per big decision: the constraint, the options with numbers, the
recommendation, and the team's answer. Decision IDs match [PLAN.md](PLAN.md#8-decisions).

## D4: head size and shape

**Constraint.** Neither Cogley module scales; they are real printed parts.
The head has to grow around them. The EyeMech has a 75.0 eye spacing (an adult
averages about 63) and a 145.4 wide base, and its mouth assembly is 112.4 wide.
They must fit with the skin (SKIN_T 5.0) and the skull wall (SKULL_WALL 2.4)
around them.

**Method.** `cad/layout_check.py`, run 2026-10-15, at rest pose only.
- Both modules are placed by their datums: eye centres on the eye line; lip plates 8.0 behind the skin at the lip line, 68 × scale below the eyes.
- They are checked against a proxy head built from average adult sections, scaled 1.0–1.3.
- Margins are in mm: + means inside the allowed envelope, − means sticking out.
- Full table: `output/check/layout/layout.md`. Renders: `output/check/layout/layout.png`.

**Results.**

| Option | Scale, shape | Eye module ↔ mouth | EyeMech frame vs skull | Mouth frame vs skull | Jaw vs skull | Head W × L × chin-to-crown |
|---|---|---|---|---|---|---|
| D | 1.0, average | −17.3 (overlap 5161 mm³) | −16.1 | −5.6 | −10.2 | 156 × 210 × 237 |
| D | 1.1, average | −4.3 (overlap 80 mm³) | −11.6 | −0.9 | −2.9 | 172 × 231 × 261 |
| C | 1.2, average | +2.5 | **−7.2** (side plates through the temples) | +1.6 | +3.6 | 187 × 252 × 284 |
| **A** | **1.2, boxy temples** | **+2.5** | **+0.7** | **+1.6** | **+3.6** | **187 × 252 × 284** |
| B | 1.3, boxy temples | +9.3 | +5.6 | +3.0 | +9.0 | 203 × 273 × 308 |

The neck stub adds 60 × scale below the chin (72 at 1.2).

**Options.**
- **A. 1.2× with boxy temples (recommended).**
  - This is the smallest head where everything fits.
  - The eye spacing reads as a normal human's, scaled 1.19.
  - The flatter, fuller temples and forehead are the classic Frankenstein silhouette (brief §8: "slightly unnatural skull silhouette").
  - Cost: thin margins (0.7 at the EyeMech side plates, 2.5 between the modules). The motion sweeps must confirm them before the skull is drawn.
- **B. 1.3× with boxy temples.**
  - Every margin is 3 mm or more, with more room for brows, cables and a fan.
  - The head is 8 % bigger in every direction, with more print time and more silicone.
  - The eyes read slightly close-set (75 / 1.3 = 58 equivalent).
- **C. 1.2× with an average head.** The EyeMech side plates come 7.2 through the skull line. That is through the wall and most of the 5 mm skin, so they would show. Not viable without cutting Cogley's parts.
- **D. 1.0× or 1.1×.** The modules collide. Not viable.

**Review (cad-reviewer, 2026-10-15).**
- The reviewer recomputed every 1.2 number independently and agreed within 0.4.
- It raised one problem with A: the 2.5 gap between the modules is too small for any skull structure between them. A 2.4 wall plus 2 × 0.4 clearance needs 3.2.

- **A2. A with the lip line 3 mm lower** (`STOMION_DZ_1X` −68.0 → −70.5 at scale 1.0, which is 84.6 below the eyes at 1.2×).
  - Eye module ↔ mouth opens to **+5.5**, so a shelf fits with 2.3 to spare.
  - The other margins are EyeMech frame +0.7, mouth frame +0.9 (an M3 shoulder screw), jaw +2.8, lip plates +2.4.
  - At 1.3× the same change gives +12.5 between the modules.
  - The face is barely changed: the eye-to-lip distance is at the long end of normal, which suits a long-faced monster.

**Recommendation: A2** (1.2×, boxy temples, lip line −70.5). That is what `params.py` now holds.

**Side effect of A.** The flatter face puts the proxy's outer skin 10 mm in front of the eyeball fronts, so the eyes are deep-set. The sculpt carves the eye sockets, so this is a sculpting note, not a fit problem.

**Answer (2026-10-15):** A2 accepted ("loving this... let's move to the next phase").

## D3 and D5: eyebrow mechanism concept and motion

**Constraint.**
- One MG90S per brow, so each brow has one degree of freedom (brief §4).
- The silicone must be moved over a region, without visible hard points.
- The mechanism must fit in the brow bay above the EyeMech and clear the lids at every pose.
- Targets (`params.py`, ASSUMPTION): the brow line sits 26 above the eye line. Mid-brow moves +10 / −5 along the skin.
- The carrier may move at most 1.0 toward the skin (keeping 0.5 of its 1.5 gap) and at most 3.0 away from it.
- D5: the inner end travels 1.5 × the outer end. Raising then reads as worried or surprised (inner end higher), and lowering reads as angry (inner end lower).

**Method.** `cad/studies/brow_concepts.py`, 2026-10-15, on the proxy forehead at 1.2×. A rigid carrier turns about one axis, and its gap to the skin is measured over the whole travel.

**Options.**
- **A. One plate across the whole brow (x 14..60), axis along x.**
  - It meets the push/pull limits only with the pivot at least 50 behind the brow (push 0.6, pull 2.9).
  - The inner/outer ratio is then only 1.2, not 1.5.
  - With the pivot closer, the plate lifts off the skin by 3.6–6.9 or digs in by up to 1.8. The face curves back toward the temple too much for a 46 mm rigid plate.
- **P. Two snap pads (|x| 22 and 52, 10 mm square) joined by a recessed bar, on one pivot axis.**
  - A search of 2,431 pivots (distance, height and plan skew) found 3 that meet every limit inside the brow bay.
  - Pick: r 45, offset +4, skew +12°. Push 0.90, pull 1.62; the inner pad rises 10.9 and the outer 7.6 (ratio 1.43).
  - The window is narrow, so the bench test matters (R10).
- **B. Four-bar path generator, or C. curved track.** Not needed: P meets the limits with one pivot. B and C add parts and friction.

**Decision: P (2026-10-15, working design; the M2 bench test confirms it).**
- The carrier turns about a pivot on a printed bracket. The hub runs on an M3 shoulder screw.
- An MG90S in the bay above drives it through a 2:1 four-bar: horn 9, pushrod 30 with M2 ball links, lever 18. The servo turns −14..+29° for a carrier travel of −7..+13.9°.
- Why 2:1: it halves the servo torque, which matters because skin forces are unknown until M4. It also turns the servo's deadband into half the brow error.
- The adjustable ball links set the neutral position (brief §4).

**v1 check results (`cad/brow_check.py`, 2026-10-15).** These include ±3° of overtravel.
- The carrier stays ≥ 3.8 from the EyeMech, ≥ 4.3 from the swept lids and eyes, and ≥ 2.1 from its bracket.
- The horn and pushrod stay ≥ 1.5 clear.
- Transmission angle ≥ 75°.
- Pads: 0.88 toward / 1.55 away from the skin.
- The left and right carriers are 33.6 apart.

**Open for M2:**
- adjustable hard stops
- the bench rig with a forehead-shaped skin sample holder
- snap adapters on the pads (M4 sizes the 7 mm snaps)

**D5 answer:** implemented as proposed (raise = worried/surprised, lower = angry). The team hasn't commented yet.

**v1.1 (2026-10-15), after the second review:**
- **Ball links:** the pushrod plane moved to one ball-stud height (3.5, ASSUMPTION) off both the lever and the horn face. The lever is now at x′ −4..0 and the horn faces 7 mm apart.
- **Pivot:** the hub is sized to a stock 10 mm ISO 7379 shoulder: 9.3 hub + 0.3 insert recess + 0.4 play.
- **Flange:** 7 thick, with 2 M3 inserts from the top. The screws come from above, because a head under the flange had no room.
- **Hard stops:** two M3 set screws in a ledge filled up to the flange.
  - One is over the double-arm horn's front arm, which is cut to 9.5 so it clears the upright; it limits raise.
  - The other is over the back arm 15 out from the shaft, where it moves 3.5 mm; it limits lower.
  - Both are set 0.5 past the travel ends. The check confirms no contact inside the travel and contact within 3° past each end.
- **Bench rig:** a forehead fragment (the skull wall between the skin's inner and the skull's inner surfaces).
  - It has a pad window with 3 mm of overtravel room and 6 clamp-strip inserts on bosses.
  - It bolts to the bracket from above, with key holes over the stops and a screwdriver hole in line with the pivot.
  - The outer side is open, so it prints lying on its inner wall.
  - Edges that cross the curved shell are cut square to the surface, because flat cuts left slivers.

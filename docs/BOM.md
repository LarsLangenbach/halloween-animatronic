# Bill of materials

Bought parts and hardware for what is designed so far. Status: `[have]` on hand, `[buy]` to order, `[confirm]` to check what you have. The quantities cover one head. Sizes marked ASSUMPTION are in `cad/params.py`; caliper what you buy and update them.

## Electronics and actuators

| Item | Qty | For | Status | Notes |
|---|---|---|---|---|
| MG90S micro servo (metal gear), with its horns | 19 + 2 spare | mouth 9 (incl. tongue), EyeMech 6, Cogley's brows 4 (D15) | [buy] | Genuine TowerPro: see *SG90 or MG90S* below for spotting fakes. Caliper one when they arrive (`MG90_*` in params.py came from Adafruit's MG90D model, 31.3 tab span; TowerPro says 32.1). |
| SG90 micro servo (plastic gear) | 3 | bench tests only | [have] | Not for the head: see below. |
| TPU filament, about 95A | 1 spool (the bars take a few grams) | Cogley's flexible brow bars (Part 11, Part 14) | [buy] | Not PLA (PLAN Q18). On the P2S, feed it from the external spool, not the AMS, and use Bambu's TPU 95A preset. |
| MG996R servo | 2 | jaw | [confirm] | |
| Will Cogley mouth PCB | 2 | mouth; eyes and brows | [confirm] | Brief §10 |

### SG90 or MG90S

They are not the same servo with a different shaft. Both have the same footprint and about the same spline (Ø4.9). The differences are inside and below the tabs:

| | SG90 | MG90S |
|---|---|---|
| Gears | plastic (POM) | metal (aluminium) |
| Output shaft | plastic, the horn screw self-taps into it | metal, tapped for a machine screw |
| Bearing | bushing | ball bearing |
| Body (L × W) | 22.7 × 12.2 | 22.8 × 12.2–12.4 |
| Tab to tab | 32.3 | 32.1–32.5 |
| Bottom to tab underside | 15.9–17 | 18.5 (about 1.5 deeper) |
| Bottom to spline top | 30.3–30.7 | 32.5 |
| Stall torque, 4.8 V | 1.8 kg·cm | 1.8 kg·cm (2.2 at 6 V) |
| Speed, 4.8 V | 0.10–0.12 s/60° | 0.10 s/60° |
| Stall current (measured) | 360 mA | 700 mA |
| Weight | 9 g | 13.4 g |

**What this means for the head:**
- The rated torque is the same. The difference is durability: the skin loads the gears all the time, and the mouth and brows run into hard stops. Plastic gears strip under that; metal gears don't. Use MG90S everywhere in the head.
- The 3 SG90s are fine for bench tests, but 3 is far short of the 19 the head needs.
- **Horns don't swap reliably.** Sources split between 20 and 21 teeth for both servos, and the horn screws differ. The printed ε3.2 eye set has horns for the MG90S.
- **Pockets:** an MG90S pocket takes an SG90 in plan, but the SG90 sits about 1.5 mm higher. An SG90 pocket is too shallow for an MG90S unless its bottom is open. Cogley's own head runs its eyes on SG90s with its own eye parts. Our printed set is the MG90S version.
- **Power:** an MG90S stalls at about twice the current of an SG90. Size the supply for it; Cogley uses 5 V 10 A.

**Fakes.** "MG90S" units with plastic gears are sold openly. Warning signs:
- a price under about US$4.50
- photos that hide the label
- a weight near 9 g instead of 13.4 g
- no tapped metal shaft
- a copper-coloured washer under the shaft

Weigh one and check the shaft before installing a batch.

Sources: TowerPro's SG90 and MG90S pages, Aus Electronics' measured SG90 drawing (TA0132), servodatabase.com, Electronicos Caldas' MG90S sheet, ProtoSupplies (measured currents), newscrewdriver.com (horn fit), vorpalrobotics.com (spotting clones). Collected 2026-10-16; the URLs are in the build log.

## Eyebrow mechanism (M2), both brows

| Item | Qty | Where | Status | Notes |
|---|---|---|---|---|
| M3 shoulder screw, ISO 7379, Ø4 × 10 shoulder | 2 | the carrier's pivot | [buy] | DATASHEET size. The head is assumed Ø8 × 4: caliper it (`SHOULDER_HEAD`). |
| M3 heat-set insert, short (M3 × 4) | 6 | bracket cheek 1 + flange 2, per brow | [confirm] | Hole Ø4.0 until the coupon says otherwise |
| M3 × 8 socket head screw | 4 | bracket flange to the skull (or the bench rig), from above | [confirm] | |
| M3 × 8 set screw (grub screw) | 4 | hard stops, 2 per brow | [buy] | Self-tapped into the printed ledge; set with a 1.5 mm hex key from above |
| M2 ball link | 4 | pushrods, 2 per brow | [buy] | RC-car type; ball about 3.5 above its mounting face (`BALL_STUD_H`, ASSUMPTION) |
| M2 threaded rod | 2 × ~20 mm | pushrods | [buy] | Ball-to-ball length 30; the links' thread sets the brow's neutral position |
| M2 × 6 self-tapping screw | 4 | servo tabs | [have] | Supplied with the MG90S |

## Bench rig (M2)

| Item | Qty | Notes |
|---|---|---|
| M3 heat-set insert (M3 × 4) | 6 | Clamp-strip holes above and below the window, for the skin sample (M4) |
| M3 × 8 socket head screw | 2 | Bracket flange to the rig's ceiling |

## Skull (M3, v0 joints)

| Item | Qty | Notes |
|---|---|---|
| M3 × 8 countersunk screw (ISO 10642) | 23 | seam joints, from outside; heads flush under the skin |
| M3 heat-set insert (M3 × 4) | 23 + 6 + 6 + 4 | seam tabs (installed from the tab's outer face before assembly), 4 shelf ledges, 2 strap ledges, 6 in the neck plate's collar, 4 in the access panel's lip |
| M3 × 8 socket head screw | 6 | shelf to its 4 ledges, strap to its 2 ledges |
| M3 × 6 countersunk screw (ISO 10642) | 6 + 4 | neck plate (6, through the wall into its collar) and access panel (4); an M3 × 8 would bottom out in their insert holes |
| M4 bolt | 4 | neck plate to the stand, on a 50 mm square. Length set by the stand (ASSUMPTION) |

## Sculpt base (M5)

| Item | Qty | Notes |
|---|---|---|
| Ø6 × 24 dowel (wood or steel) | 4 | joins the two head pieces at the split, glued |
| M4 heat-set insert (M4 × 8) | 4 | in the neck's underside. Hole Ø5.6 is an ASSUMPTION: check it against the inserts you have |
| M4 × 12 socket head screw | 4 | plate to the neck, from below (heads in counterbores). Not longer: an M4 × 16 bottoms out in the insert holes before the plate is clamped |
| Wood screw, Ø4–4.5 | 4 | plate to a board or turntable |
| Sulfur-free oil-based clay | as needed | e.g. Monster Clay. Sulfur stops platinum-cure silicone from curing (Q15) |
| PLA | about 0.8 kg | upper ~410 g, lower ~310 g, plate ~95 g (estimate) |

## Skin attachment (M4, not designed yet)

| Item | Qty | Notes |
|---|---|---|
| 7 mm sew-on snap, both halves | 4 for the brows (+ the lips, M4) | Which product (Q8)? Caliper both halves before M4 starts. |

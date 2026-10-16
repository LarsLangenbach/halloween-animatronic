# Bill of materials

Bought parts and hardware for what is designed so far. Status: `[have]` on hand, `[buy]` to order, `[confirm]` to check what you have. The quantities cover one head. Sizes marked ASSUMPTION are in `cad/params.py`; caliper what you buy and update them.

## Electronics and actuators

| Item | Qty | For | Status | Notes |
|---|---|---|---|---|
| MG90S micro servo, with its double-arm horn | 17 | mouth 9 (incl. tongue), EyeMech 6, brows 2 | [confirm] | Genuine TowerPro or clone (Q4)? Clones differ by up to 1 mm; caliper one. **Brows: cut the horn's front arm to 9.5 mm from the shaft.** |
| MG996R servo | 2 | jaw | [confirm] | |
| Will Cogley mouth PCB | 2 | mouth; eyes and brows | [confirm] | Brief §10 |

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
| M3 × 8 countersunk screw (ISO 10642) | 24 | seam joints, from outside; heads flush under the skin |
| M3 heat-set insert (M3 × 4) | 24 | in the seam tabs, installed from the tab's outer face before assembly |

## Skin attachment (M4, not designed yet)

| Item | Qty | Notes |
|---|---|---|
| 7 mm sew-on snap, both halves | 4 for the brows (+ the lips, M4) | Which product (Q8)? Caliper both halves before M4 starts. |

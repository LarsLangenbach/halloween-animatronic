# M2 brow concept study

Left brow, head scale 1.2. Brow line z 238.4 (26.0 above the eye line). Carrier face 1.5 behind the skin's inner surface. Travel at mid-brow (x 37): +10.0 / -5.0 along the skin. Limits: push <= 1.0, pull <= 3.0, inner/outer rise 1.5 +- 0.1 (D5).

## A: one plate across the whole brow, axis along x (reference)

| r behind the brow | worst push | worst pull | inner / outer rise |
|---|---|---|---|
| 20 | 1.8 | 6.9 | 9.7 / 6.4 |
| 30 | 1.1 | 4.8 | 9.9 / 7.5 |
| 40 | 0.8 | 3.7 | 9.9 / 8.1 |
| 50 | 0.6 | 3.0 | 9.9 / 8.5 |
| 70 | 0.5 | 2.3 | 9.9 / 8.9 |

A rigid plate 46 mm wide can't follow the face as it curves back toward the temple: it either digs into the skin or lifts off by several mm. Hence the two-pad carrier.

## P: two snap pads (|x| 22 and 52, 10 mm square) on one axis

Searched 2431 pivots (r 15..75, offset along the face -20..20, skew -24..24 deg); 5 meet every limit with the pivot inside the brow bay. Best ones:

| r | offset | skew deg | pivot (y, z above eyes) | push | pull | inner / outer rise |
|---|---|---|---|---|---|---|
| 45 | +4 | +12 | (-22.1, 20.8) | 0.87 | 1.72 | 10.8 / 7.7 |
| 45 | +4 | +15 | (-22.1, 20.8) | 0.88 | 1.74 | 11.0 / 7.5 |
| 45 | +4 | +18 | (-22.1, 20.8) | 0.90 | 1.76 | 11.2 / 7.3 |
| 40 | +4 | +12 | (-17.3, 21.8) | 0.98 | 1.90 | 11.0 / 7.5 |
| 40 | +4 | +15 | (-17.3, 21.8) | 1.00 | 1.92 | 11.2 / 7.2 |

**Pick: r 45, offset +4, skew +12 deg.** Pivot at x 28.2, y -22.1, z 233.2 (eye line + 20.8), 46.3 behind the carrier face; axis (0.978, 0.208, 0). Pads move 0.87 toward / 1.72 away from the skin; inner pad rises 10.8, outer 7.7 at full raise. Servo rotation for full travel: +12 / -6 deg (approx.).

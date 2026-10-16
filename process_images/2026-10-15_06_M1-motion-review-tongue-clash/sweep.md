# M1 pose sweeps and reserved space

Head scale 1.2. Angles from the modelled pose (jaw closed, lids closed, eyes ahead). Gaps in mm; overlaps in mm3. Contacts already present at rest are designed and ignored; pairs already closer than MOTION_CLEAR_MIN at rest are only checked for overlap.

Jaw group: Component1, Hex_socket_head_cap_screw_M2_5x0_45_x_8, Hex_socket_head_cap_screw_M2x0_40_x_6, Hex_socket_head_cap_screw_M4x0_70_x_8, JawBase, JawLink, LowerLeftLip, M3_Shoulder, M4Insert, M4_Shoulder_SSHE-M4-5-5-A2, MG90s_servo_FIX_v1_Mirror_, MG996R_v6, Part_1, Part_19, Part_20, Part_21, Part_22, Part_27, Part_28, Part_33, Part_37, Part_38, Part_39

## Jaw

| open deg | new overlap (pair) | closest gap (pair) | chin drop | chin back | lip plate opening | inside skull |
|---|---|---|---|---|---|---|
| 0 | none | 1.6 (Part_22 / MG90s_servo_FIX_v1_Mirror_) | 0.0 | 0.0 | 12.0 | +1.3 |
| 5 | 5 (Part_22 / MG90s_servo_FIX_v1_Mirror_) | 1.4 (Part_22 / MG90s_servo_FIX_v1_Mirror_) | 1.3 | 3.6 | 18.7 | +2.3 |
| 10 | 8 (Part_22 / MG90s_servo_FIX_v1_Mirror_) | 1.4 (Part_22 / MG90s_servo_FIX_v1_Mirror_) | 5.7 | 7.7 | 24.9 | +3.3 |
| 15 | 2 (Part_22 / MG90s_servo_FIX_v1_Mirror_) | 1.4 (Part_22 / MG90s_servo_FIX_v1_Mirror_) | 9.6 | 12.5 | 30.8 | +3.5 |
| 20 | 1 (Part_22 / MG90s_servo_FIX_v1_Mirror_) | 1.1 (Hex_socket_head_cap_screw_M2x0_40_x_6 / Component2) | 13.2 | 17.8 | 36.2 | +3.4 |
| 25 | none | 1.4 (Part_22 / MG90s_servo_FIX_v1_Mirror_) | 16.3 | 23.6 | 41.1 | +3.4 |
| 30 | none | 2.2 (Part_22 / MG90s_servo_FIX_v1_Mirror_) | 18.7 | 29.9 | 45.2 | +3.4 |
| 35 | none | 2.8 (Part_21 / Component2) | 20.7 | 36.6 | 48.8 | +3.5 |

Jaw clean to 0 deg (needed 25). Lip plate opening: vertical gap between the front 8 mm of the upper and lower lip plates (the silicone lips add their own thickness). Chin drop and chin back: the lowest and frontmost jaw points.

## Eyes and lids

- Eyes, pan +-30, tilt +-25: closest to the outer skin +9.8 (+ = behind it).
- Lids, top 0..60, bottom 0..35: closest to the outer skin +8.4.
- Lids, eyes and the EyeMech's own parts are Cogley's design; only what they sweep into outside the module is checked here.

## Reserved space

| volume | size (x, y, z) | overlap with parts at rest | closest part at rest | jaw sweep | lid sweep | eye sweep | inside skull |
|---|---|---|---|---|---|---|---|
| brow_L | 48 x 67 x 55 | 0 | 2.4 (PivotLarge) | 85.1 | 3.5 | 5.6 | -2.8 |
| brow_R | 48 x 67 x 55 | 0 | 3.9 (LidBR) | 85.1 | 3.5 | 5.6 | -2.8 |
| cable | 25 x 74 x 209 | 0 | 8.0 (SnapEyemech_v20) | 16.1 | 109.5 | 112.8 | +2.0 |

Brow volumes are trimmed by the skin's inner surface on purpose (the carrier works under the skin), so only the cable channel is held to the skull's inner surface.

Renders: sweep.png (and sweep_1..6.png)

## Issues

- jaw clean only to 0 deg of 25: at 5 deg Part_22 hits MG90s_servo_FIX_v1_Mirror_ (5 mm3)

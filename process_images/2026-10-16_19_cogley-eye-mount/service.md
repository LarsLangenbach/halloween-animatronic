# M3 service check

Head scale 1.2. Paths in mm in the head frame.

## Teardown, in order

| step | moves | path | result |
|---|---|---|---|
| 1. back upper piece, with the access panel and the eye strap | skull_back_upper, skull_access_panel, skull_eye_strap | (0, -154, 197) | clear |
| 2. EyeMech and both brows together (brow flanges unbolted) | eyemech, brow_L, brow_R | (0, -50, 0) -> (0, -50, 4) -> (0, -220, 4) | clear |
| 3. shelf | skull_shelf | (0, 0, 8) -> (0, -250, 8) | clear |

## Alone, from the assembled head

| part | path | result |
|---|---|---|
| neck plate (head off its stand) | ((0.0, 0.0, -80.0),) | clear |

## Tool access (L hex key: short arm 20, long arm 65; stubby: short arm 12; clearance radius 2.0)

| when | screw | tool | clear swing | result |
|---|---|---|---|---|
| before: EyeMech and both brows together (brow flanges unbolted) | left brow flange screw at (42, -16) | stubby hex key | 125 deg round 138 deg | ok |
| before: EyeMech and both brows together (brow flanges unbolted) | left brow flange screw at (46, -34) | hex key | 135 deg round 132 deg | ok |
| before: EyeMech and both brows together (brow flanges unbolted) | right brow flange screw at (-42, -16) | stubby hex key | 125 deg round 218 deg | ok |
| before: EyeMech and both brows together (brow flanges unbolted) | right brow flange screw at (-46, -34) | hex key | 145 deg round 218 deg | ok |
| before: shelf | shelf screw at (68, -40) | hex key | 190 deg round 110 deg | ok |
| before: shelf | shelf screw at (70, -95) | hex key | 340 deg round 165 deg | ok |
| before: shelf | shelf screw at (-68, -40) | hex key | 190 deg round 245 deg | ok |
| before: shelf | shelf screw at (-70, -95) | hex key | 340 deg round -170 deg | ok |

## Pending

- mouth module: no path yet: it hits the back lower piece going back and the front upper piece going up; its mount and way out wait on Q14

## Issues

none

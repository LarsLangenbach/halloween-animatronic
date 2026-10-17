# Assembly

Steps for the parts designed so far, in order. Hardware is in [BOM.md](BOM.md) and print settings in [PRINT_GUIDE.md](PRINT_GUIDE.md).

## Eye mechanism into Cogley's skull frame

The printed EyeMech (ε3.2 MG90s-A) fits his head the way his own does: its base plate is the same part, with the same mounting holes. It isn't screwed from inside; it sits on three supports and two screws per side hold it.

1. **Inserts.** Each end of the base plate has 3 holes, Ø4–4.5 × 6 deep, at 22.9, 39.6 and 56.5 mm from the plate's front long edge. Heat-set an M3 insert into the front two at each end (22.9 and 39.6). The hole size suits an M3 × 4 insert: check yours against it. His frame uses those two.
2. **Mouth first.** The mouth's top plate (`TopBase`) sits in the frame. The eye mechanism rests on it, with its two inner feet in the top plate's pockets.
3. **Drop the eye mechanism in** between the frame's side walls. Its base plate's ends sit against the walls, lined up with the frame's side holes.
4. **Screw it in** from outside: one M3 × 8 socket screw through each frame side hole into the inserts. That's 2 per side.
5. **Cheek bone** (from "Frame - Extras"): bolt it to the frame. It sits just under the base plate's side edges (0.4 mm) and supports them.

It uses MG90S servos (the printed set's pockets are for MG90S). The nearest part to any eye servo is the mouth's top plate, 2.7 mm away, so the MG90S's extra 1.5 mm of depth fits.

Renders: process_images snapshot 19 (`studies_cogley_eye_mount.png`, `studies_cogley_eye_slot.png`).

## Eyebrow unit (one per side), on the bench rig or in the skull

**Assembly order in the head:** build each brow unit completely on the bench first (steps 1–6): in the head, the EyeMech's centre post blocks a straight hex key to the pivot screw. On the bench rig, the round hole in the inner wall gives the key a straight line. The brows and the EyeMech interlock, so neither can pass the other. They go into the head **together**, from the back, with the back upper piece off. Hold the brows in place over the EyeMech, slide the three in, set the EyeMech down on its pads, then bolt the brows up to their plates (step 7). Removal is the reverse: unbolt the brows, slide the three back 50 mm, lift 4 mm, and take them out.

1. **Inserts.** Heat-set one M3 insert into the bracket's cheek, from the hub side. It sits in a 0.3 mm recess; push it flush with the bottom of that recess, not proud of it. Heat-set two M3 inserts into the top face of the flange.
2. **Servo.** Centre the MG90S (90°, or 1500 µs) before fitting anything. Pass its case through the bracket plate's cutout from the inboard side, so the tabs rest on the plate, and fix it with the two M2 screws that came with it.
3. **Horn.** Cut the double-arm horn's front arm to 9.5 mm from the shaft with flush cutters. Screw an M2 ball stud into the back arm's hole at 9 mm. Press the horn onto the spline with the back arm pointing straight back (away from the face) and the servo still centred.
4. **Carrier.** Screw an M2 ball stud into the hole at the end of the carrier's lever. Hold the carrier's hub against the cheek and pass the M3 shoulder screw through the hub (head on the inboard side) into the cheek's insert. Tighten until the shoulder seats on the insert. The hub should then turn freely, with about 0.4 mm of axial play.
5. **Pushrod.** Thread a ball link onto each end of the M2 rod, about 30 mm ball to ball, and snap it onto both studs.
6. **Neutral position.** With the servo centred, turn the pushrod (or one link) until the pads sit at their rest position: pad faces flush with the brow line on the rig, or touching the skin with no pull in the head.
7. **Mount.** Bolt the bracket's flange to the rig's ceiling (or the skull) with two M3 × 8 screws from above, into the flange inserts. In the head, the front screw has only about 16 mm under the crown: use a stubby 2.5 mm hex key (or cut a key's short arm down to 12 mm).
8. **Hard stops.** Drive the servo slowly to the full raise. Through the key hole over the front arm, turn the first set screw down until it just touches the arm, then back it off 0.5 mm. Repeat at the full lower with the screw over the back arm's end. Then set the firmware limits just inside these stops: the stops are a safety, not a working end position.
9. **Check.** Run the brow end to end slowly. Nothing may rub or bind. The pads should slide along the window (rig) or under the skin (head) without lifting off or digging in.

Log what you measured in [BUILD_LOG.md](BUILD_LOG.md): servo angles at both stops, the pushrod length at neutral, and anything that rubbed.

## Sculpt base

The head the clay face is sculpted on (print guide: M5). It is a smooth wrap of Cogley's whole head, at least 3 mm out from every part of it. Clay on it plus that 3 mm is the skin, so nothing of his head can come through a skin sculpted on it. **Don't sand or carve into it.**

1. **Inserts.** Heat-set four M4 inserts into the holes in the neck's underside (`sculpt_lower`).
2. **Join the head.** Glue four Ø6 × 24 dowels into the lower piece's top face. Then glue the upper piece on (epoxy, or thick CA), lining up the midline groove across the joint. Fill the seam flush.
3. **Plate.** Bolt the plate under the neck with four M4 × 12 socket head screws from below (not longer: they would bottom out in the insert holes), heads in the counterbores, the cone keys facing up. Screw the plate to a board or turntable through its four corner holes.
4. **Seal.** Seal the print (shellac or a primer), so the clay's oils don't soak into it and the clay grips evenly.
5. **Sculpt** in sulfur-free oil-based clay (Q15). The guide grooves on the base:

   | Groove | What it marks | Where it comes from |
   |---|---|---|
   | Midline | the centre of the face, for symmetry | — |
   | Eye line | through both eye centres (z 212) | the eyes |
   | Eyes | each sphere is the eye mechanism's lids at their true position; the dimple is the gaze, straight ahead | Sculpt the eyelids round them |
   | Brow lines | along Cogley's brow bars | The brows move here. Keep the skin over them thin so it moves with them |
   | Nose bottom | the bottom of the nose (z 163) | 0.7 of the way from the eyes to the lips: standard proportions |
   | Nose width | two short uprights above the nose bottom (±21) | the inner corners of the eyes: standard proportions |
   | Lip line | where the lips meet (z 141), with a short mark at each mouth corner (±33) | Cogley's lip plates: the lips must be sculpted here |
   | Chin | the bottom of the chin (z 99) | the lips sit a third of the way from the nose to the chin |
   | Hairline | the top of the forehead (z 309) | the forehead as tall as the nose-to-chin third |
   | Ears | a box on each side, from the brow height down to the nose bottom, behind the jaw | standard proportions |

   The lumps round the mouth and over the eyes are Cogley's lips, teeth and brow bars under 3 mm of base. Lay the clay over them. Keep the lips and brows thin there so the skin moves with them.
6. **Mold.** Leave the plate's keys clear of clay. The mold registers on them, and so will the mold core later.

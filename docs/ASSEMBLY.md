# Assembly

Steps for the parts designed so far, in order. Hardware is in [BOM.md](BOM.md) and print settings in [PRINT_GUIDE.md](PRINT_GUIDE.md).

## Eyebrow unit (one per side), on the bench rig or in the skull

**Assembly order in the head:** fit both brow units to the skull **before** the EyeMech. The EyeMech's centre post blocks a straight hex key to the pivot screw. On the bench rig, the round hole in the inner wall gives the key a straight line.

1. **Inserts.** Heat-set one M3 insert into the bracket's cheek, from the hub side. It sits in a 0.3 mm recess; push it flush with the bottom of that recess, not proud of it. Heat-set two M3 inserts into the top face of the flange.
2. **Servo.** Centre the MG90S (90°, or 1500 µs) before fitting anything. Pass its case through the bracket plate's cutout from the inboard side, so the tabs rest on the plate, and fix it with the two M2 screws that came with it.
3. **Horn.** Cut the double-arm horn's front arm to 9.5 mm from the shaft with flush cutters. Screw an M2 ball stud into the back arm's hole at 9 mm. Press the horn onto the spline with the back arm pointing straight back (away from the face) and the servo still centred.
4. **Carrier.** Screw an M2 ball stud into the hole at the end of the carrier's lever. Hold the carrier's hub against the cheek and pass the M3 shoulder screw through the hub (head on the inboard side) into the cheek's insert. Tighten until the shoulder seats on the insert. The hub should then turn freely, with about 0.4 mm of axial play.
5. **Pushrod.** Thread a ball link onto each end of the M2 rod, about 30 mm ball to ball, and snap it onto both studs.
6. **Neutral position.** With the servo centred, turn the pushrod (or one link) until the pads sit at their rest position: pad faces flush with the brow line on the rig, or touching the skin with no pull in the head.
7. **Mount.** Bolt the bracket's flange to the rig's ceiling (or the skull) with two M3 × 8 screws from above, into the flange inserts.
8. **Hard stops.** Drive the servo slowly to the full raise. Through the key hole over the front arm, turn the first set screw down until it just touches the arm, then back it off 0.5 mm. Repeat at the full lower with the screw over the back arm's end. Then set the firmware limits just inside these stops: the stops are a safety, not a working end position.
9. **Check.** Run the brow end to end slowly. Nothing may rub or bind. The pads should slide along the window (rig) or under the skin (head) without lifting off or digging in.

Log what you measured in [BUILD_LOG.md](BUILD_LOG.md): servo angles at both stops, the pushrod length at neutral, and anything that rubbed.

# Assembly

Steps for the parts designed so far, in order. Hardware is in [BOM.md](BOM.md) and print settings in [PRINT_GUIDE.md](PRINT_GUIDE.md).

**Cogley's whole head (D14-D16):** the step-by-step picture manual for his Robot Head α2.0.33 is a private Claude doc: https://claude.ai/artifact/PMPYGv9TJCFZaYW4FzNEWQ. It covers inserts, the EyeMech, the mouth, his brows, mounting, wiring and first power-up. Its pictures come from `cad/studies/assembly_manual.py` and are saved in [process_images/2026-10-22_36_assembly-manual](../process_images/2026-10-22_36_assembly-manual/), with the EyeMech steps and the linkage inserts added in [process_images/2026-10-25_37_assembly-manual-eyes-inserts](../process_images/2026-10-25_37_assembly-manual-eyes-inserts/). Every M3 shoulder joint in the mouth and brows threads into an M3 insert (28 in all), not a nut.

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

## Enclosure and neck (M8, v1 of 2026-10-29)

Fifteen prints and one PETG sheet, the window (PLAN D26, D30, D31). The step-by-step picture manual is the claude.ai doc [Enclosure Build Manual](https://claude.ai/artifact/RCCkXzUb8Ans9ELzX8U4rN) (pictures from `cad/studies/enclosure_manual.py`); this is the same order in brief. Screws: M3 × 8 with nuts unless said otherwise; the bottom rings' ears take M3 × 8 self-tapping into the tray's bosses; the neck takes eight M4 inserts (M4 × 8 heat-set: four in its foot, four in its collar) and eight M4 × 12 bolts. Nothing is drilled. The [print guide](PRINT_GUIDE.md) lists the parts. Left and right are as you stand facing the front (the face and the speaker side): the buck is on the right (−x).

Two faults in the printed v1 pedestal, found 2026-10-30 while writing the manual, are fixed by hand in steps 4 and 5: its inside is closed all round (the tube stands on the tray's inner rib), so the head's leads and the fan's air had no way into the bay; and its four flange screws sit under its solid top plate, where no driver reaches.

1. **Neck inserts.** Heat-set four M4 inserts into the neck's foot from below, flush. Heat-set four more into the holes in the top of the neck's collar (the raised hexagon on the spine's top), square to its tilted top face, flush. The collar has only 0.4 mm to spare in the ring's hole: shave off any plastic the inserts pushed out of its sides.
2. **Test-fit the head** on the bare neck, with no leads in the way. Take his rear plate off (its screws at the sides of the head). Lower the head so the collar goes up into the frame's hexagonal hole, the two ribs either side of the mouth module go down into the spine's side notches, and the ring sits flat on the spine's top. The ring sits 8° off level (its back higher), so the last 5 mm go down and a little backward: let the collar's chamfer push the head back as it drops. If it does not seat, do not force it: lift, look which edge touches, and shave it. Lift it off again.
3. **Neck on the pedestal.** Four M4 × 12 up through the pedestal's top plate into the foot's inserts, heads inside the tube. They are 138 mm in from its open end: use a 3 mm hex driver with a 150 mm shaft, or a bit on an extension.
4. **Lead door** (by hand, until the pedestal is reprinted with one). Facing the neck's front (away from its spine), on the pedestal's right side, a quarter turn round: a 40 × 50 mm door, from 50 to 100 mm below the pedestal's top face. Melt through the 1.6 mm wall with the soldering iron round the outline, snip what is left, trim the edges smooth. It sits above the buck, under the deck.
5. **Feet and pedestal on the tray.** Four 20 mm rubber feet under the tray at the diagonals (not at the front or back, where the panels' lower nuts are reached from below). Stand the pedestal's flange on the tray's inner rib, the neck's spine to the back (the bank's rails) and the door on the right; centre it, 80 mm from the tray's edge to the tube all round. Glue it (hot glue or super glue gel, or weld with the iron and a piece of filament) where the tray's four short radial ribs pass under the tube's edge, 0.5 mm below it. The flange's four screws are not used. The deck's hole holds the tube's top to 1 mm; lift the finished enclosure by its base, never by the head.
6. **Bottom rings on the tray.** The two halves are the same. Their ears sit on the tray's outer rib: four M3 × 8 self-tapping into the bosses at 30°, 150°, 210° and 330°. Their seam walls meet at the sides; one M3 + nut through each pair.
7. **The band** (two printed halves, D31). `enc_band_F` (the plain opening) goes at the front, `enc_band_B` (the opening with the notch down to its bottom edge) at the back. With the base on its feet, stand each half round the bottom rims, its bottom edge level with the tray's underside; the seam walls on its ends meet inside at the left and right.
   1. Two M3 × 8 socket heads + nut through each seam wall pair. The band's inside is only 33 mm from them, so turn them with a 2.5 mm L hex key.
   2. Four M3 × 8 + nut through the bottom rims (30°, 150°, 210°, 330°). The rims' holes at the front and back are behind the openings and stay empty.
   3. Drop an M3 nut into the slot at the top of each of the four small bosses inside the band, two beside each opening. They hold the panels' upper screws, which can't be reached from inside once the deck is on.
   Every hole is printed in. The band's top edge rises 10 mm above the plates' level, where the deck's rims will wrap inside it.
8. **Grille** over the front opening: four M3 × 8 from outside. The upper two go into the nuts in the band's slots. The lower two nuts sit 4 mm above the band's bottom edge, under the bottom ring: with the base on its feet, reach in under the band's edge and hold each nut with a fingertip.
9. **The bay.** The bank lies across the back on the tray's ribs between its rails, ports to the back; board 1 lies on top of it (foam tape), board 2 over board 1 on four 25 mm standoffs (side by side, their back corners would poke through the band); the buck stands on its side at the right; the trigger, fuses and WAGO buses go at the left, clear of the band's seam wall there; the speaker lies along x in its saddles at the front, with its aux and charge leads plugged in first. Wire the power as the Head Power Wiring Build Guide says, leaving the servo sockets free, and lead the outside cables (Board 1 USB, the speaker's 3.5 mm, the charger's USB-C) to the back opening.
10. **Head** (D30: the neck clamps his frame; nothing is drilled in his parts). It goes on before the deck, so its leads can be plugged in with the bay open.
    1. Tag every lead with its board socket. His rear plate is still off from step 2.
    2. Feed every lead from the head, connectors first, down through the hexagonal hole in the frame's bottom ring at the back of the head, then through the hole in the collar, down the spine and the tube, through the bore into the pedestal and out of the lead door into the bay. Leave slack at the head for the jaw and the eyes.
    3. Lower the head onto the neck as in step 2, holding the leads to one side.
    4. Reach in from the back with the two clamp plates (`neck_clamp_L`, `neck_clamp_R`: mirror images, flat both sides, so either fits either side), one each side of the leads. They will not slide in flat (the frame's back bars are in the way) or drop in from above (the EyeMech's base plate and the mouth module's top are). Hold the plate front end first and lower, its back end tipped up about 30 to 40°; when it is two or three fingers short of its place, slide the front end in under the EyeMech's base plate and lay the back end down as it slides home. Hold the leads over to the other side while each plate goes in; the two plates' notches meet round them.
    5. Four M4 × 12 socket head bolts through the plates into the inserts, with a 3 mm hex key from behind. Snug them in turn, then tight: the plates press the ring down onto the spine. The head must not rock or turn.
    6. Plug every lead into its socket and tie the bundle clear of the buck and the speaker. Power up and run every axis (the head manual's Stage 6): nothing stalls, no lead goes tight as the jaw opens. Power down.
    7. Rear plate back on.
11. **The deck.** First push the webcam's USB plug through the 12 × 30 mm lead slot in `enc_top_B`: most plugs are wider than 12 mm, so widen the slot with the soldering iron if it does not pass. Hold each half level just above the band's top edge, slide it in under the head and round the pedestal (F from the front, B from the back, its slot at the back), and lower it about 12 mm into the band until its rim is flush with the band's top edge. One M3 + nut through each seam wall pair; six **M3 × 6** + nut through the rims and the band, nuts inside the rim (hold them with tweezers or a dab of Blu-Tack). Not M3 × 8: their tips would stick into the window sheet's place.
12. **Window.** Cut the 892 × 477 blank from the 1000 × 500 sheet (score deeply and flex it apart, or heavy scissors). Roll it into a tube, 20 mm overlap, taped inside; lower it over the head and stand it on the deck outside the lip, the overlap at the back.
13. **Cap.** Tape the webcam under the cap's top between its three stops (lens toward the front, looking out through the sheet). Join the two cap halves with four M3 + nut through the seam walls. Run the webcam lead down the inside of the window at the back and push its plug through the deck's slot into the bay, with slack to lift the cap. Lower the cap over the window: its two lips take the sheet's top edge. It rests there, lift-off.
14. **Hatch.** Reach in through the back opening, gather the outside cables (Board 1 USB, the webcam's USB, the speaker's 3.5 mm, the charger's USB-C) and lay them in the band's notch. The hatch goes over the back opening, its notch over the band's: four M3 × 8, the upper two into the slot nuts, the lower two held from under the band's edge. If the cables are tight, snip B's 2 mm tie under the notch off with flush cutters.

To open: lift the cap; lift the window out; the panels come off from outside (their upper nuts stay in the band's slots, the lower ones are held from under the band's edge) for the speaker's buttons and the bank's ports; the deck halves come off (two seam screws, six band screws) and slide out under the head for the bay. To take the head off: unplug its leads in the bay, rear plate off, the four bolts out, the plates out, lift the head straight up and pull the leads up after it.

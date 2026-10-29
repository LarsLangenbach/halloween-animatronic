Enclosure v1 print files for tonight (2026-10-29). Everything except the neck.
All files are already in their print pose, lying flat on the bed: import and print as they land.
PLA. 3 walls, 15 % infill, 0.2 mm layers, no supports on any part. Brim on the two panels only.

Plates (one file per plate unless listed together; the half-rings and discs fill the whole bed):

  Printer 1                              Printer 2
  1. enc_tray.stl             ~3 h       1. enc_pedestal.stl + enc_grille.stl + enc_hatch.stl   ~4.5 h
  2. enc_top_F.stl            ~2.5 h     2. enc_bottom_F.stl        ~1 h
  3. enc_cap_F.stl            ~3.5 h     3. enc_bottom_B.stl        ~1 h
                                         4. enc_top_B.stl           ~2.5 h
                                         5. enc_cap_B.stl           ~3.5 h

Printer 1 total about 9 h, printer 2 about 12.5 h. Times are estimates; the slicer decides.
The pedestal and the two panels fit on one plate together: pedestal in the middle, a panel standing
either side of it. Leave the panels standing on their short edge as imported (their slots print vertical).

What each part is:
  enc_tray      the base's floor; ribs, screw bosses, speaker saddles, bank rails stand up from it
  enc_pedestal  the D 90 tube the neck bolts onto; imported upside down, that is its print pose
  enc_bottom_*  the two halves of the base's lower ring; the painted PETG band wraps their rim
  enc_top_*     the two halves of the deck; the window sheet stands on them inside the lip
  enc_cap_*     the two halves of the cap; imported upside down (top on the bed), lips and skirt up
  enc_grille / enc_hatch   the panels over the openings in the band (front speaker, back hatch)

The neck (neck.stl in output/print) is left out on purpose; it prints later.
Sheets to buy: two 1000 x 500 mm sheets of 1 mm clear PETG. The window blank is 891 x 477 mm,
the base's band 928 x 109 mm (see docs/PRINT_GUIDE.md and docs/ASSEMBLY.md).

UPDATE: enclosure_small_plate.stl is the pedestal and the two panels already laid out on one bed
(10 mm apart, centred). Import it, right-click > Split > To objects, give the two panels a brim, print.
The other seven files each fill a whole bed on their own, so they stay one part per plate:
enc_tray, enc_bottom_F, enc_bottom_B, enc_top_F, enc_top_B, enc_cap_F, enc_cap_B. Eight plates in all.

UPDATE 2: the two panels now lie flat in enclosure_small_plate.stl, inside (concave) face down, so the
slicer can put supports under the arch and the outside face stays clean. Split the plate to objects and
enable supports (tree or normal) for the two panels; the pedestal needs none.

# Plaster mold of the clay face

How to make the plaster negative of the clay face sculpted on the printed face mask (v9), using
the printed mold base (`cad/mold_base.py`). Pictures: the newest `process_images/*mold-base*`
folder (`mold.png`, `mold_sections.png`, `mold_seat_closeups.png`, `mold_why_one_piece_locks.png`).

**Video to watch first:** Toxic Image Studios,
["Ultracal 30 part 1: Simple open face molds"](https://www.youtube.com/watch?v=FeFBY9UFZD4). It
uses Ultracal 30 and burlap and makes a one-piece open mold (option A below). Skip its board
and clay walls; the printed base does that job. It casts latex; yours is Dragon Skin FX-Pro, a platinum silicone (PLAN D21), so
never let latex touch this mold (platinum silicone won't cure in a mold that has had latex in it).

**What the base does**
- The mask lies face up in a printed collar. A ledge sits under its edge and a lip fits just
  inside it, so it can only sit one way.
- Four posts hold up the forehead and cheeks, so the thin plastic shell doesn't sag under the
  plaster.
- A skirt closes the gap under the mask's edge. The edge is low by the ears and about 13 cm
  high at the chin and forehead ends, so without the skirt plaster would run under the edge
  into the inside of the mask. The skirt flares outward toward the bottom so the plaster lifts
  straight off it.
- The flat plate around the skirt is where the mold's flange goes. The four cones on it are
  the registration keys.
- The walls hold the flange plaster in. They are four separate L-shaped corners standing on the
  plate, clipped together where they meet, so they **come off before you lift the plaster**. A
  low rib on the plate just inside them locates them and stops plaster running underneath.
- Eight small loose wedges stand in gaps in the rib, against the walls (two per side). Once the
  walls are off, you pull each wedge out with an M3 screw threaded into its end. That leaves a
  slot under the edge of the flange, where a flat screwdriver can lever the mold up evenly.
- **Keep the base after the mold is made.** When you cast the silicone, the cleaned mask goes
  back in the same collar as the core, and the mold's keys find the same cones. That is what
  keeps the skin's thickness equal to the clay's.

## Why it can't simply be poured over in one piece

Lying face up, the mask is widest about 1.5 cm above the plate by the ears, and below that its
sides tuck back in toward the edge. The jaw does the same, less deeply. Plaster that runs into
those tucks (and behind the ears) sets under an overhang. Plaster and the printed mask are
both rigid, so the mold then can't be lifted off. In `mold.png` (from above) and
`mold_why_one_piece_locks.png`, those areas are red: about 96 cm², up to about 22 mm deep under
the ears and 6–9 mm along the jaw.

You can deal with that in one of two ways. The base is the same for both.

| | A. One-piece mold, tucks filled (recommended for tomorrow) | B. Three-piece mold (front + two sides) |
|---|---|---|
| What you do | Fill the red strips with clay so the surface drops straight down (or flares out) from the widest line to the base. Then make one plaster shell. | Set a wall of brass shims, or a clay wall about 2 cm tall, along the widest line on each side. Make the front piece first, then the two side pieces. |
| Skin result | Thicker silicone along the back edge by the ears and jaw, and no gap behind the ears. Trim the extra off with a blade after casting. | The skin follows the sculpt everywhere, including the backs of the ears. |
| Time | One lay-up, about 1.5 h plus the set. | Three lay-ups, plus about 1 h of set time between the front and the sides. |
| Risk | Low | The pieces can stick together. They need release on every parting face, and keys cut into the front piece's edges. |

**How to check that A is done:** look straight down from above. If you can see all of the clay,
with nothing tucked under, the shell will lift off.

## Shopping list

- **Plaster:** Ultracal 30 is the best choice (hard, takes fine detail). Hydrocal is next best.
  Plaster of Paris works, but it is softer and sets faster. The shell needs about 3 L of mixed
  plaster, which is about 4 kg of Ultracal powder, so buy 10 kg to allow for waste and a spare
  batch.
- **Burlap (jute hessian):** about 1 m². Cut it before you mix anything: strips of about
  5 × 15 cm, and squares of 10 × 10 cm.
- **Release for the printed base:** petroleum jelly thinned with a little mineral oil, or
  Murphy's oil soap, or paste wax. Plaster can grip the layer lines in the print.
- **Sealing:** a hot glue gun, plus some of your clay.
- **Mixing:** flexible buckets, a kitchen scale, chip brushes, a spatula, nitrile gloves, a dust
  mask for mixing (Ultracal contains crystalline silica), and a tarp.
- **Wall clips:** 8 M3 × 20 bolts with nuts, or 8 zip ties, two through the holes at each of the
  four joints between the wall corners. Or one medium binder clip per joint (two won't fit on
  one 45 mm ear).
- **One M3 screw** (any length over 10 mm) to pull the pry wedges out.
- **Demolding:** two flat screwdrivers or wooden wedges.
- **Option B only:** brass shim stock (or cut drink-can aluminium) in pieces of about 2 × 4 cm.
- **Optional:** a wooden stick about 30 cm long, plastered across the back of the shell as a
  handle and stiffener.

## 1. Print the base (tonight)

Eight pieces in `output/print/`, all as exported (flat side down, no supports); L = the
character's left:
- **Base:** `mold_base_chin_L`, `_chin_R`, `_top_L`, `_top_R`, each up to 164 × 220 × 152 mm. Two on
  each printer.
- **Wall corners:** `mold_wall_chin_L`, `_chin_R`, `_top_L`, `_top_R`, each up to 168 × 224 × 45 mm.
  These are quick; print them after the base pieces.
- **Pry wedges:** `mold_pry_wedge`, **8 off**, 18 × 14 × 7 mm. All 8 fit on one plate.
- **Or use the ready-made plates** in `output/plates/`: `mold_plate_chin_L`, `_chin_R`, `_top_L`,
  `_top_R`. Each holds one base piece, its wall corner and 2 wedges. Print the two `chin` plates
  overnight (one per printer) and the two `top` plates next.

- **Material:** PLA. A shell 20 mm thick heats up as it sets: casting studies measured
  32–42 °C, higher for thick layups. PLA softens at about 55 °C. So don't build the plaster
  thicker than about 25 mm in one go, and keep the mold out of the sun.
- **Settings:** 0.2 mm layers (0.28 is fine for speed), **4 walls** (this keeps the skirt and
  walls watertight), 5 top and 4 bottom layers, 15 % infill.

## 2. Put the base together

1. Set the four base pieces on a flat table and lower each one onto its neighbours from above.
   The dovetails in the plate only go together straight down.
2. Seal the base's seams. Run hot glue along them underneath, and up the inside of the tall
   skirt at the chin and forehead ends (that also stops the two halves of the skirt from moving
   apart). Then press a thin line of clay into every seam the plaster will touch: the plate and
   the outside of the skirt.
3. Stand the four wall corners on the plate, just outside the rib, so their ears meet at the
   middle of each side. Clip each pair of ears together at the top and the bottom (binder
   clips, M3 bolts through the holes, or zip ties).
4. Stand a pry wedge in each of the 8 gaps in the rib, wide end against the wall. Press a
   little clay into the screw hole in its end so no plaster gets in.
5. Press a clay snake into the inside corner where each wall meets the rib, round the wedges,
   and up the inside of each joint between the wall corners. That is what makes the walls
   watertight.
6. Coat everything the plaster will touch with a thin, even film of release: the plate, the
   rib, the skirt, the cones, the wedges and the insides of the walls. Don't let it pool,
   because the pools will show in the mold.
7. Press a pea-sized ball of clay onto the top of each of the four posts.

## 3. Set the mask in

1. Clear any clay off the bare plastic edge of the mask, and trim the clay flush with the
   outside of that edge. The plastic edge has to sit on the printed ledge. The clean clay edge
   you leave becomes the edge of the silicone skin.
2. Lower the mask face up straight down into the collar, with the chin toward the `chin`
   pieces. It should drop onto the ledge with the lip inside it, and it should not rock. The
   clay on the posts squeezes flat. Along the sides the lip stands straight up, because the
   mask flares out there; at the chin and forehead it follows the inside of the mask. If the
   print came out a little different and it binds, sand the lip there. Don't force it: the mask
   is only 2 mm thick.
3. **A:** fill the tucks with clay (see above). **B:** set the shim wall along the widest line,
   with a few V-notches in it for keys.

## 4. Make the plaster shell

Ultracal 30: **38 parts water to 100 parts plaster by weight** (380 g water to 1 kg plaster). It
sets 25–35 minutes after mixing. Sift the plaster into the water, let it soak for 1–2 minutes,
then mix by hand until it is smooth. Mix small batches. For plaster of Paris, follow the bag,
and expect much less working time.

1. **Detail coat.** Mix about 0.5 kg. Brush and flick a thin coat (3–5 mm) over all the clay,
   down the skirts and onto the flange. Work it into the deep spots (nostrils, eye corners,
   ears) and blow out any bubbles.
2. **Burlap.** As the next batch starts to thicken, dip burlap strips in it and lay them on,
   overlapping. Press each one down so no air is trapped. Run strips from the face down the
   skirts onto the flange. Lay 2–3 layers.
3. **Flange.** Fill the flat area inside the walls over the cones and wedges, 20–25 mm deep,
   with burlap in it too. Over the wedges the plaster is 7 mm thinner, so don't go under 20. If
   you like, plaster the wooden stick across the back.
4. **Finish** with a last coat to smooth it, 15–20 mm thick overall. Make it a little thicker
   at the edge of the flange.
5. **Wait** at least 1 hour; 2 hours is better. It warms up as it sets, then cools.
6. **Take the walls off.** Undo the clips, then pull each wall corner straight outward, away
   from its corner of the base. A light tap with your hand frees it if the release didn't
   cover everything. The edge of the plaster flange is now open all the way round.
7. **Pull the pry wedges.** Each wedge's end shows in the edge of the flange. Pick the clay out
   of its hole, turn an M3 screw in a few turns, and pull the wedge straight out with pliers. It
   is tapered, so it comes easily. That leaves a slot 7 mm high under the flange.
8. **Demold.** Put a flat screwdriver into a slot and twist it, so the flange lifts off the
   plate. Work round all 8 slots a little at a time until the whole flange has let go, then
   lift the shell straight up. Don't lever hard in one place: that is how flanges crack.
9. **Get the head out.** The mask usually stays in the collar, and you lift it straight out. If it
   comes up inside the shell, turn the shell over on a towel, take the mask out from the back,
   and dig the clay out of the mold with wooden tools. Clay that stays in the mold is normal.
10. **B only:** before making the side pieces, coat the front piece's edges with release. When
   demolding, pull the side pieces off sideways first, then lift the front piece.

## Afterwards

- Let the mold dry for several days before any silicone goes in. It holds a lot of water. See
  *Getting the mold ready for the silicone* below.
- Clean the clay off the mask and keep the mask and the base together. They are the core and
  the jig for the silicone cast. The base doesn't need to come apart. To store it, lift the four
  pieces apart straight up; they go back together the same way.
- Don't pour leftover plaster down a drain: let it set in the bucket, then flex it out into the
  bin.

## Getting the mold ready for the silicone (Dragon Skin FX-Pro)

The skin is cast in Smooth-On Dragon Skin FX-Pro (PLAN D21), brushed on in layers. The mold is
sealed with an acrylic spray (e.g. Krylon Crystal Clear), thinned petroleum jelly or Smooth-On
SuperSeal, then released with Ease Release 200.

**Never shellac.** Smooth-On's sealer guide: "Don't Use Shellac! - shellac contains alcohol and
the rubber will bond to the model." And don't wipe the mold with alcohol before silicone goes on.

1. **Dry it completely.** A 15-20 mm Ultracal shell with burlap takes several days, longer in humid
   air, and the flange dries last. Stand it on edge so air reaches both sides, with a fan in a warm
   room (under about 50 °C / 120 °F). Checks:
   - **Plastic-wrap test (the reliable one):** tape a square of plastic wrap tight over the back of
     the flange, all four edges sealed, for 1-2 hours. Fog or droplets under it mean it is still wet.
     Repeat on the back of the face area.
   - **Touch:** wet plaster feels cool against your wrist (evaporation); dry plaster feels like the room.
   - **Colour:** wet Ultracal is darker and greyish; dry is an even, lighter off-white.
   - With a scale: weigh it daily; it is dry when the weight stops dropping.
   Sealer on damp plaster won't bond and can peel.
2. **Clean it.** Pick out leftover Monster Clay specks with a toothpick or skewer and a dry soft
   brush (a low flashlight raking across the surface shows them; a few seconds of hair dryer on low
   softens a stubborn bit). No alcohol. Blow out dust and crumbs, and knock flashing off the edges.
3. **Fix chips and pinholes now,** before sealing.
4. **Seal.** Acrylic spray: several light mist coats, turning the mold to reach every surface; let
   each dry per the can. Puddles fill the skin texture. Stop when the surface no longer soaks it in
   and a drop of water beads. Or petroleum jelly thinned with a little mineral spirits, brushed very
   thin and wiped smooth (brush strokes transfer to the skin).
5. **Let the sealer dry fully,** then **test before the face:** release a sealed scrap of the same
   plaster (or a hidden spot on the flange), brush a little mixed FX-Pro on it, and after the cure
   time check that it is fully cured and peels off clean. If it sticks or stays tacky, stop and
   change the sealer before casting.
6. **Ease Release 200:** a light, even coat over the sealed mold and the core, then let it dry.
7. **Cast warm.** Mold, core and silicone at room temperature, not below 18 °C (65 °F). The pot life is
   12 minutes, so mix small batches for brush-on layers (THI-VEX thickens them so they stay on the
   walls). Demold after 40 minutes at 23 °C; longer if the room is cool.

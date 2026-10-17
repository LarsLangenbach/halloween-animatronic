# Reference models

Third-party assemblies that the skull is designed around. They are not printed
from here; the skull mounts them. Never edit these files. Re-export them from
the source and replace the file if they change.

**Patreon member files.** Both models come from Will Cogley's own Onshape
documents, through the team's paid Patreon membership. Keep this repository
private, and never publish or share these STEP files.

| File | What | Origin | Licence |
|---|---|---|---|
| `eyemech/EyeMech_e3.1.step` | Will Cogley EyeMech ε3.1, full assembly: 38 solids, 6 servos (modelled as SG90) | STEP export from Will Cogley's Onshape (Patreon), 2026-10-15. Originally named `EyeMech ε3.1.step`. Same outer geometry as ε3.2 (PLAN §3) | CC BY-NC-SA 4.0 (Will Cogley); Patreon access |
| `head_a2.0.33/` | Will Cogley Robot Head α2.0.33, the whole head: `printing/reference_assembly.obj` (his Onshape assembly, 191 parts, metres), `printing/AllComponents.stl`, `printing/BambuPrintfile.3mf` (8 plates), `Code/` (MicroPython: eyes, brows, mouth, UI), `electronics/` (EasyEDA Pro: Mouth board, Eyes/Brow/Neck board). No STEP | The team's Patreon download, 2026-10-16. Renamed to ASCII: the folder was `Head_α2.0.33`, `printing/` was `Printing and Assembly`, `electronics/` was `Electronics (Open in EasyEDA)`, and the OBJ was `Reference Assembly (Open with Microsoft 3D Viewer or Blender).obj`. Its code is reference only: never run it from here | Patreon access; licence as his α2.0 page |
| `makehuman/base.obj` | MakeHuman base mesh: a realistic neutral adult body (decimetres, +y up, face +z). The face mask (D19) is warped from its head | https://github.com/makehumancommunity/makehuman (`makehuman/data/3dobjs/base.obj`), downloaded 2026-10-16 | **CC0** (stated in the file's header) |
| `mouth/MouthAssembly.step` | Will Cogley mouth assembly: 107 solids including screws, 9 × MG90S, 2 bodies that look like the MG996R jaw servos, 4 tessellated surface parts | STEP export from Will Cogley's Onshape (Patreon), 2026-10-15. Most likely the Robot Head α2.0.33 mouth (PLAN Q3) | unconfirmed; Patreon access |

## First survey (2026-10-15, bounding boxes in each file's own frame)

Both files face **−y**, with +z up. Whether they share an origin is not yet known.

**EyeMech ε3.1**
- Overall: 145.4 × 132.3 × 62.8 (x × y × z), x from −72.7 to 72.7.
- Eyeballs (part `Component74`): 32.0 × 20.0 × 32.0 each, centred at x = ±37.5. That is a 75.0 eye spacing.
- The widest part is the base (`SnapEyemech_v20`), at 145.4.
- Every solid is valid.

**Mouth**
- Overall: 112.4 × 118.6 × 86.9 (x × y × z).
- Lips reach y = −92.6 at the front, and the top base reaches y = 26.0 at the back.
- `import_step` reports the compound as **not valid**. Which solids are invalid is still to be found (M1).

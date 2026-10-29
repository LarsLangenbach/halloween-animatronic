"""
Enclosure concept study (2026-10-28): a printed canister round the head.

The human wants a round, tubular display case like a sci-fi specimen canister:
a printed base drum and top cap, a clear sheet rolled into a cylinder between
them (held in slits in both), and a printed, opaque back column that hides the
mechanism's rear and ties the cap to the base. The base is hollow for the power
and the boards; the head stands on a pedestal on the base's deck.

This script only draws the idea to scale around the real head (the sculpt
wrap and the face mask) so the sizes can be judged. The numbers below are the
concept's; when the enclosure is modelled they move to params.py.

Run:  python cad/studies/enclosure_concept.py
  -> output/check/enclosure/studies/enclosure_concept.png and .md
"""
import os
import sys

import glob

import numpy as np
import trimesh
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Rectangle, Circle, Wedge, Polygon  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import cadkit as K  # noqa: E402
import params as P  # noqa: E402

# ---------------------------------------------------------------------------
# concept numbers (mm, head frame: x 0 midline, y 0 eye centres, z 0 neck interface)
# ---------------------------------------------------------------------------
AXIS_Y = P.SCULPT_NECK[2]      # -70: the canister's axis is the neck's axis
R_SHEET = 150.0                # inside of the clear sheet (D 300)
SHEET_T = 1.0                  # rolled PETG or polycarbonate; acrylic cracks at this bend
GROOVE_W = 1.4                 # slit width for the sheet
R_OUT = 170.0                  # outside of the rings and the back column (D 340)
R_LIP = 140.0                  # the rings' inner lips overhang the sheet by 10
DISC_D = 240.0                 # one-piece deck disc and lid disc: they fit the 256 bed
BED = P.__dict__.get("BED", 256.0)

GROUND = -158.0
FEET = 8.0
FLOOR_T = 6.0                  # the floor tray (D 250, one print): the electronics bolt to it
BASE_Z = (-150.0, -40.0)       # base drum, 110 tall; its top face carries the lower slit
DECK_T = 8.0                   # deck disc, its top at BASE_Z[1]
GROOVE_LOW = 6.0               # slit depth in the base (the sheet lifts out of it)
PEDESTAL = (130.0, 110.0, 40.0)   # bottom D, top D, height: from the deck up to z 0
NECK_Q17 = (104.0, 40.0)       # the skin's neck stub starts at z 40 (sculpt base); the spine below is proposed for Q17
SPINE_Y = (-125.0, -95.0)      # neck spine (proposed, Q17): a 30 thick plate behind the jaw's swing (overtravel reaches y -92.5)
SPINE_X = 40.0                 # half width: it meets Cogley's frame at the nape (frame x +-77 there, lowest bar z 134.6)
SPINE_TOP = 190.0              # it rises into the frame's nape ribs and bolts to them
COLUMN_TOP = 70.0              # the round D 100 column stops here: the open jaw's lowest point is z 82 (88 at 25 deg)
WINDOW_TOP = 400.0             # underside of the top cap
GROOVE_TOP = 12.0              # slit depth in the cap (deeper: the sheet goes up into it first)
CAP_Z = (400.0, 480.0)         # top cap ring, 80 tall
LID_T = 8.0
SPINE_ARC = 120.0              # the back column's arc, centred on -y
SPINE_T = 10.0                 # column shell: 3 mm wall plus ribs
SPINE_SPLIT_Z = 180.0          # the column prints in 2 x 2 pieces: a centre rib hides the vertical seam
QUADRANT_SEAMS = (45.0, 135.0, 225.0, 315.0)   # ring pieces: 4 per ring, seams off the column's centre

# what lives in the base: the power box of the human's Head Power Wiring doc (claude.ai, 2026-10-26)
# and its two boards. Sizes are from the listings, to be measured when they arrive (PLAN Q19).
BANK = (161.0, 55.0, 50.0)     # UGREEN Nexode 25,000 mAh 145 W power bank; the JUYOON 140 W charger takes its place at a wall
BUCK = (85.0, 60.0, 28.0)      # ACEIRMC 20 A CC/CV buck with its heatsink; the PD trigger (25 x 25), 4 fuse holders,
                               # 4 WAGO 221 nuts and the 1000 uF capacitor sit beside it
BOARD = (95.0, 65.0, 20.0)     # a Cogley mouth board with its Pico: Board 1 mouth, Board 2 eyes + brows
SHEET = "1 mm clear PETG"      # D24 (2026-10-28): rolled; acrylic cracks at this bend, polycarbonate costs more
SPEAKER = (74.0, 92.0)         # Sony SRS-XB12 (the human's own): a D 74 x 92 cylinder, 243 g, 3.5 mm aux, micro-USB
                               # charge; on its side in a cradle at the front, driver end at a removable grille panel
GRILLE = (110.0, 84.0)         # the grille panel in the base's front: width, height; snaps out to reach the buttons
CAMERA = (94.0, 29.0, 24.0)    # Logitech 1080p webcam (Q21: C920-class bar, clip removed): w, h, depth. The
                               # StreamCam is a 58 x 48 x 66 cube; say so if it is that one
CAMERA_FOV = 78.0              # degrees, diagonal (C920/C922: 78; C930e: 90)
CAMERA_Z = 430.0               # lens height: in the cap's front band, between its slots
CAMERA_TILT = 10.0             # degrees down: a table-top canister looking at a standing visitor
CAMERA_HOLE = 12.0             # the only sign of it: a hole among the cap's vents, the lens glass flush behind it
                               # (the lens sits a few mm behind the glass, so D 8 would clip a 78 deg view)


def silhouette(meshes, axis, bins):
    """min/max of the vertices' coordinate `axis` per z bin, over all meshes."""
    V = np.vstack([m.vertices for m in meshes])
    z = V[:, 2]
    idx = np.digitize(z, bins)
    lo, hi, zs = [], [], []
    for i in range(1, len(bins)):
        sel = V[idx == i]
        if len(sel) < 3:
            continue
        lo.append(sel[:, axis].min())
        hi.append(sel[:, axis].max())
        zs.append(0.5 * (bins[i - 1] + bins[i]))
    return np.array(zs), np.array(lo), np.array(hi)


def plan_outline(meshes, cx, cy, n=180):
    """max radius about (cx, cy) per angle bin: the head seen from above."""
    V = np.vstack([m.vertices for m in meshes])
    th = np.degrees(np.arctan2(V[:, 1] - cy, V[:, 0] - cx)) % 360.0
    r = np.hypot(V[:, 0] - cx, V[:, 1] - cy)
    idx = (th / (360.0 / n)).astype(int)
    rmax = np.zeros(n)
    for i in range(n):
        sel = r[idx == i]
        rmax[i] = sel.max() if len(sel) else 0.0
    ang = (np.arange(n) + 0.5) * (360.0 / n)
    return ang, rmax


def jaw_meshes():
    """the jaw group at rest (Cogley's parts in our frame) and the swept open jaw from pose_sweep."""
    d = os.path.join(K.root(), "output", "ref")
    rest = [trimesh.load(f) for f in glob.glob(os.path.join(d, "head_a2", "parts", "*"))
            if any(k in os.path.basename(f) for k in ("JawBase", "JawLink", "Part_33"))]
    # the open jaw: his parts turned about the jaw axis (geom.jaw_axis) by JAW_OPEN_DEG, chin down
    import geom as G
    yc, zc = G.jaw_axis(P.HEAD_SCALE)
    t = np.radians(-P.JAW_OPEN_DEG)
    R = np.array([[1, 0, 0], [0, np.cos(t), -np.sin(t)], [0, np.sin(t), np.cos(t)]])
    opn = []
    for m in rest:
        V = m.vertices - np.array([0.0, yc, zc])
        opn.append(trimesh.Trimesh(V @ R.T + np.array([0.0, yc, zc]), m.faces, process=False))
    return rest, (trimesh.util.concatenate(opn) if opn else None)


def side_view(ax, zs, ylo, yhi):
    c = AXIS_Y
    # head
    ax.fill_betweenx(zs, ylo, yhi, color="#c9c9c9", lw=0, label="head with skin (sculpt wrap + mask)")
    ax.plot(ylo, zs, color="#777", lw=0.8)
    ax.plot(yhi, zs, color="#777", lw=0.8)
    # neck placeholder and pedestal
    # neck (proposed for Q17): a round column up to z 70, then a spine behind the jaw up into the frame's nape
    ax.add_patch(Rectangle((c - NECK_Q17[0] / 2, 0), NECK_Q17[0], COLUMN_TOP, fc="#e8d9a8", ec="#8a7a40",
                           label="neck column D 100, z 0 to 70, under the jaw's swing (proposed, Q17)"))
    ax.add_patch(Rectangle((SPINE_Y[0], 0), SPINE_Y[1] - SPINE_Y[0], SPINE_TOP, fc="#c9a24a", ec="#8a7a40",
                           label=f"neck spine {SPINE_Y[1] - SPINE_Y[0]:.0f} thick, {2 * SPINE_X:.0f} wide, bolted into the frame's nape ribs (z 135 to 190)"))
    rest, opn = jaw_meshes()
    if rest:
        JV = np.vstack([m.vertices for m in rest])
        jz, jlo, jhi = silhouette(rest, 1, np.arange(100.0, 190.0, 2.0))
        ax.fill_betweenx(jz, jlo, jhi, color="#b0413e", alpha=0.35, lw=0, label="jaw group at rest (Cogley's JawBase and links)")
    if opn is not None:
        oz, olo, ohi = silhouette([opn], 1, np.arange(80.0, 190.0, 2.0))
        ax.plot(olo, oz, color="#b0413e", lw=1.2, ls="--", label="jaw open 25 deg: rearmost y -85, lowest z 88")
        ax.plot(ohi, oz, color="#b0413e", lw=1.2, ls="--")
    ax.plot([-84, -74], [134.6, 134.6], color="k", lw=3, label="Cogley's frame: its lowest bar, z 134.6 (x +-34)")
    z0 = BASE_Z[1]
    ax.add_patch(Polygon([(c - PEDESTAL[0] / 2, z0), (c + PEDESTAL[0] / 2, z0), (c + PEDESTAL[1] / 2, z0 + PEDESTAL[2]),
                          (c - PEDESTAL[1] / 2, z0 + PEDESTAL[2])], closed=True, fc="#9aa8b8", ec="k",
                         label="pedestal: 4 x M4 on a 50 square, cable bore, air slots"))
    # base drum walls, deck, floor tray, feet
    kw = dict(fc="#8d99a6", ec="k", lw=0.8)
    ax.add_patch(Rectangle((c - R_OUT, BASE_Z[0]), R_OUT - R_SHEET - GROOVE_W, BASE_Z[1] - BASE_Z[0], **kw))
    ax.add_patch(Rectangle((c + R_SHEET + GROOVE_W, BASE_Z[0]), R_OUT - R_SHEET - GROOVE_W, BASE_Z[1] - BASE_Z[0], **kw))
    ax.add_patch(Rectangle((c - R_SHEET - GROOVE_W, BASE_Z[0]), 2 * (R_SHEET + GROOVE_W), BASE_Z[1] - GROOVE_LOW - BASE_Z[0],
                           fc="#b9c2cc", ec="k", lw=0.8))                                 # inner shell (slit above)
    ax.add_patch(Rectangle((c - DISC_D / 2, BASE_Z[1] - DECK_T), DISC_D, DECK_T, fc="#6f7d8c", ec="k", lw=0.8,
                           label="deck disc D 240 (one print)"))
    ax.add_patch(Rectangle((c - 125, BASE_Z[0]), 250, FLOOR_T, fc="#6f7d8c", ec="k", lw=0.8,
                           label="floor tray D 250 (one print): boards and power bolt to it"))
    for yy in (c - 140, c + 140):
        ax.add_patch(Rectangle((yy - 10, GROUND), 20, FEET, fc="#333", ec="k"))
    # hollow bay: electronics
    zf = BASE_Z[0] + FLOOR_T
    ax.add_patch(Rectangle((c - 135, zf), BANK[0], BANK[2], fc="#f4c27a", ec="k",
                           label="UGREEN 145 W power bank (or the 140 W wall charger outside), in a cradle on the tray"))
    ax.add_patch(Rectangle((c - 40, zf + BANK[2] + 8), BUCK[0] * 0.7, BUCK[2], fc="#f7dca0", ec="k",
                           label="power box: PD trigger, 20 A buck, fuses, WAGO buses, capacitor"))
    ax.add_patch(Rectangle((c - 135, zf + BANK[2] + 8), BOARD[0] * 0.9, BOARD[2], fc="#9fd49f", ec="k",
                           label="Cogley boards x 2 (Board 1 mouth, Board 2 eyes + brows) on standoffs, side by side across x"))
    # speaker: the driver faces the front slots from a sealed printed chamber; the slots are its grille
    ax.add_patch(Rectangle((c + R_SHEET - 3 - SPEAKER[1], zf), SPEAKER[1], SPEAKER[0], fc="#ddd", ec="k",
                           label="speaker: Sony SRS-XB12 on its side in a cradle at the front, driver end at the grille; 3.5 mm aux from the laptop"))
    ax.add_patch(Rectangle((c + R_OUT - 4, zf - 2), 4, GRILLE[1], fc="w", ec="k", hatch="----",
                           label=f"grille panel {GRILLE[0]:.0f} x {GRILLE[1]:.0f} in the base's front, snaps out: reach the speaker's buttons and aux"))
    # back hatch under the column's foot: the bank and the leads out (webcam USB, Board 1 USB, charger USB-C)
    ax.add_patch(Rectangle((c - R_OUT - 1, BASE_Z[0] + 18), 4, 70, fc="#333", ec="k",
                           label="back hatch: reach the bank; leads out to the laptop (webcam USB, Board 1 USB) and the charger"))
    # vents in the base and the cap (the drawn side: slots)
    for zz in np.arange(BASE_Z[0] + 30, BASE_Z[1] - 25, 8):
        ax.plot([c + R_OUT - 2, c + R_OUT + 1], [zz, zz], color="k", lw=1.2)
    # clear sheet (front and back; the back is behind the column)
    ax.plot([c + R_SHEET + SHEET_T / 2] * 2, [BASE_Z[1] - GROOVE_LOW, WINDOW_TOP + GROOVE_TOP], color="#1f77b4", lw=2,
            label=f"{SHEET}, rolled, in slits {GROOVE_LOW:.0f} deep below and {GROOVE_TOP:.0f} above")
    ax.plot([c - R_SHEET - SHEET_T / 2] * 2, [BASE_Z[1] - GROOVE_LOW, WINDOW_TOP + GROOVE_TOP], color="#1f77b4", lw=2, ls=":")
    # back column
    ax.add_patch(Rectangle((c - R_OUT, BASE_Z[1]), SPINE_T, WINDOW_TOP - BASE_Z[1], fc="#5a6572", ec="k",
                           label=f"back column, {SPINE_ARC:.0f} deg arc, 2 x 2 prints, hides the rear + ties cap to base"))
    ax.plot([c - R_OUT - 2, c - R_OUT + SPINE_T + 2], [SPINE_SPLIT_Z] * 2, color="w", lw=1)
    # top cap: ring walls, lips, lid
    ax.add_patch(Rectangle((c - R_OUT, CAP_Z[0]), R_OUT - R_LIP, CAP_Z[1] - CAP_Z[0], **kw))
    ax.add_patch(Rectangle((c + R_LIP, CAP_Z[0]), R_OUT - R_LIP, CAP_Z[1] - CAP_Z[0], **kw))
    ax.add_patch(Rectangle((c - R_SHEET - GROOVE_W, CAP_Z[0]), 2 * (R_SHEET + GROOVE_W), GROOVE_TOP, fc="w", ec="none"))
    ax.add_patch(Rectangle((c - R_SHEET + GROOVE_W, CAP_Z[0]), 2 * (R_SHEET - GROOVE_W), GROOVE_TOP, fc="#8d99a6", ec="none"))
    ax.add_patch(Rectangle((c - R_LIP, CAP_Z[1] - LID_T - 2), 2 * R_LIP, 2, fc="#8d99a6", ec="k", lw=0.5))   # lid ledge
    ax.add_patch(Rectangle((c - DISC_D / 2, CAP_Z[1] - LID_T), DISC_D, LID_T, fc="#6f7d8c", ec="k", lw=0.8,
                           label="lid disc D 240 (one print), vents"))
    # camera in the cap's front band, looking out through a hole, tilted down
    ax.add_patch(Rectangle((c + R_OUT - 3 - CAMERA[2], CAMERA_Z - CAMERA[1] / 2), CAMERA[2], CAMERA[1], fc="#222", ec="k",
                           label=f"Logitech webcam in a cradle against the cap's front wall, lens behind a D {CAMERA_HOLE:.0f} hole, {CAMERA_TILT:.0f} deg down; USB via the column to the laptop"))
    for a in (-CAMERA_FOV / 2, CAMERA_FOV / 2):
        t = np.radians(-CAMERA_TILT + a)
        ax.plot([c + R_OUT, c + R_OUT + 90 * np.cos(t)], [CAMERA_Z, CAMERA_Z + 90 * np.sin(t)], color="#222", lw=0.8, ls="--")
    # cable and air path
    ax.annotate("", xy=(c, BASE_Z[0] + FLOOR_T + BANK[2] + 30), xytext=(c, 30),
                arrowprops=dict(arrowstyle="->", color="#d62728", lw=1.5, ls="--"))
    ax.text(c + 6, -12, "leads + fan air\nthrough the neck bore", color="#d62728", fontsize=7, va="top")
    # dimensions
    ax.annotate("", xy=(c - R_OUT, GROUND - 14), xytext=(c + R_OUT, GROUND - 14), arrowprops=dict(arrowstyle="<->"))
    ax.text(c, GROUND - 22, f"D {2 * R_OUT:.0f} outside", ha="center", va="top", fontsize=8)
    ax.annotate("", xy=(c - R_SHEET, WINDOW_TOP - 14), xytext=(c + R_SHEET, WINDOW_TOP - 14), arrowprops=dict(arrowstyle="<->"))
    ax.text(c, WINDOW_TOP - 18, f"D {2 * R_SHEET:.0f} inside the sheet", ha="center", va="top", fontsize=8)
    yd = c + R_OUT + 22
    for (za, zb, txt) in ((GROUND, BASE_Z[1], f"base {BASE_Z[1] - GROUND:.0f}"),
                          (BASE_Z[1], WINDOW_TOP, f"window {WINDOW_TOP - BASE_Z[1]:.0f}"),
                          (CAP_Z[0], CAP_Z[1], f"cap {CAP_Z[1] - CAP_Z[0]:.0f}"),
                          (GROUND, CAP_Z[1], f"overall {CAP_Z[1] - GROUND:.0f}")):
        ax.annotate("", xy=(yd, za), xytext=(yd, zb), arrowprops=dict(arrowstyle="<->"))
        ax.text(yd + 4, 0.5 * (za + zb), txt, fontsize=8, va="center", rotation=90)
        yd += 22
    crown = zs[np.argmax(zs)]
    ax.text(c + 60, crown + 4, f"crown z {zs.max():.0f}, {WINDOW_TOP - zs.max():.0f} under the cap", fontsize=7, va="bottom")
    gap_f = R_SHEET - (yhi.max() - c)
    gap_b = R_SHEET - (c - ylo.min())
    ax.text(c + R_SHEET - 4, 140, f"{gap_f:.0f} clear", fontsize=7, ha="right", color="#1f77b4")
    ax.text(c - R_SHEET + 4, 140, f"{gap_b:.0f} clear", fontsize=7, ha="left", color="#1f77b4")
    ax.set_xlim(c - R_OUT - 100, c + R_OUT + 40)
    ax.set_ylim(GROUND - 30, CAP_Z[1] + 20)
    ax.set_aspect("equal")
    ax.set_title("side section through the axis (front is +y, right)", fontsize=9)
    ax.set_xlabel("y")
    ax.set_ylabel("z")


def front_view(ax, zs, xlo, xhi):
    ax.fill_betweenx(zs, xlo, xhi, color="#c9c9c9", lw=0)
    ax.add_patch(Rectangle((-NECK_Q17[0] / 2, 0), NECK_Q17[0], COLUMN_TOP, fc="#e8d9a8", ec="#8a7a40"))
    ax.add_patch(Rectangle((-SPINE_X, 0), 2 * SPINE_X, SPINE_TOP, fc="#c9a24a", ec="#8a7a40", alpha=0.6))
    z0 = BASE_Z[1]
    ax.add_patch(Polygon([(-PEDESTAL[0] / 2, z0), (PEDESTAL[0] / 2, z0), (PEDESTAL[1] / 2, z0 + PEDESTAL[2]),
                          (-PEDESTAL[1] / 2, z0 + PEDESTAL[2])], closed=True, fc="#9aa8b8", ec="k"))
    kw = dict(fc="#8d99a6", ec="k", lw=0.8)
    ax.add_patch(Rectangle((-R_OUT, BASE_Z[0]), 2 * R_OUT, BASE_Z[1] - BASE_Z[0], **kw))
    ax.add_patch(Rectangle((-R_OUT, CAP_Z[0]), 2 * R_OUT, CAP_Z[1] - CAP_Z[0], **kw))
    for xx in (-140, 140):
        ax.add_patch(Rectangle((xx - 10, GROUND), 20, FEET, fc="#333", ec="k"))
    # the column behind, seen through the sheet
    half = R_OUT * np.sin(np.radians(SPINE_ARC / 2))
    ax.add_patch(Rectangle((-half, BASE_Z[1]), 2 * half, WINDOW_TOP - BASE_Z[1], fc="#5a6572", ec="k", alpha=0.35))
    ax.plot([0, 0], [BASE_Z[1], WINDOW_TOP], color="#3a4450", lw=2)          # centre rib
    ax.plot([-half, half], [SPINE_SPLIT_Z] * 2, color="#3a4450", lw=1)
    for sx in (-1, 1):
        ax.plot([sx * (R_SHEET + SHEET_T / 2)] * 2, [BASE_Z[1] - GROOVE_LOW, WINDOW_TOP + GROOVE_TOP], color="#1f77b4", lw=2)
    gz = BASE_Z[0] + FLOOR_T - 2
    ax.add_patch(Rectangle((-GRILLE[0] / 2, gz), GRILLE[0], GRILLE[1], fc="#3a4450", ec="k", lw=0.8))
    for zz in np.arange(gz + 6, gz + GRILLE[1] - 4, 6):
        ax.plot([-GRILLE[0] / 2 + 5, GRILLE[0] / 2 - 5], [zz, zz], color="#8d99a6", lw=1.6)
    ax.text(GRILLE[0] / 2 + 6, gz + GRILLE[1] / 2, "speaker grille\n(snaps out)", fontsize=7, va="center")
    for zz in np.arange(CAP_Z[0] + 40, CAP_Z[1] - 15, 8):
        ax.plot([-50, 50], [zz, zz], color="k", lw=1.0)
    ax.add_patch(Circle((0, CAMERA_Z), CAMERA_HOLE / 2, fc="#111", ec="k"))
    ax.add_patch(Rectangle((-CAMERA[0] / 2, CAMERA_Z - CAMERA[1] / 2), CAMERA[0], CAMERA[1], fc="none", ec="#222", lw=0.8, ls=":"))
    ax.text(10, CAMERA_Z, "webcam behind the wall, 94 wide; its mics hear through the slots", fontsize=6.5, va="center")
    ax.set_xlim(-R_OUT - 40, R_OUT + 40)
    ax.set_ylim(GROUND - 30, CAP_Z[1] + 20)
    ax.set_aspect("equal")
    ax.set_title("front view: the column shows behind the head", fontsize=9)
    ax.set_xlabel("x")


def plan_view(ax, ang, rmax):
    c = (0.0, AXIS_Y)
    ax.add_patch(Circle(c, R_OUT, fc="#dfe4ea", ec="k", lw=0.8))
    ax.add_patch(Circle(c, R_SHEET + GROOVE_W, fc="w", ec="k", lw=0.5))
    ax.add_patch(Circle(c, DISC_D / 2, fc="#eef1f4", ec="k", lw=0.8, ls="--"))
    # ring quadrant seams
    for q in QUADRANT_SEAMS:
        t = np.radians(q)
        ax.plot([c[0] + (R_SHEET + GROOVE_W) * np.cos(t), c[0] + R_OUT * np.cos(t)],
                [c[1] + (R_SHEET + GROOVE_W) * np.sin(t), c[1] + R_OUT * np.sin(t)], color="k", lw=0.8)
    # back column (120 deg about -y = 270 deg) and the sheet (the rest)
    ax.add_patch(Wedge(c, R_OUT, 270 - SPINE_ARC / 2, 270 + SPINE_ARC / 2, width=SPINE_T, fc="#5a6572", ec="k",
                       label=f"back column {SPINE_ARC:.0f} deg (2 pieces wide, seam under a centre rib)"))
    th = np.radians(np.linspace(270 + SPINE_ARC / 2, 270 + 360 - SPINE_ARC / 2, 200))
    ax.plot(c[0] + (R_SHEET + SHEET_T / 2) * np.cos(th), c[1] + (R_SHEET + SHEET_T / 2) * np.sin(th),
            color="#1f77b4", lw=2, label=f"clear sheet, {360 - SPINE_ARC:.0f} deg, ends tucked behind the column's edges")
    # head outline from above
    t = np.radians(ang)
    ax.fill(c[0] + rmax * np.cos(t), c[1] + rmax * np.sin(t), color="#c9c9c9", ec="#777", lw=0.8,
            label="head from above (sculpt wrap + mask)")
    # pedestal, M4 square, neck bore
    ax.add_patch(Circle(c, PEDESTAL[1] / 2, fc="none", ec="k", lw=0.8, ls="--"))
    s = P.NECK_BOLT_SQUARE / 2
    for sx in (-1, 1):
        for sy in (-1, 1):
            ax.add_patch(Circle((c[0] + sx * s, c[1] + sy * s), 2.2, fc="k"))
    ax.add_patch(Circle(c, 12.5, fc="w", ec="#d62728", lw=1.2, label="cable + air bore D 25 (reserve.py)"))
    # a print bed on one ring quadrant
    bx = Rectangle((c[0] + 4, c[1] + 4), BED, BED, fc="none", ec="#2ca02c", lw=1.2, ls="--",
                   label=f"P2S bed {BED:.0f} square: one ring quadrant fits")
    ax.add_patch(bx)
    ax.annotate("", xy=(c[0], c[1] + R_OUT + 30), xytext=(c[0], c[1] + R_OUT + 5), arrowprops=dict(arrowstyle="->"))
    ax.text(c[0] + 4, c[1] + R_OUT + 18, "front (+y)", fontsize=8)
    ax.set_xlim(c[0] - R_OUT - 30, c[0] + BED + 20)
    ax.set_ylim(c[1] - R_OUT - 30, c[1] + BED + 20)
    ax.set_aspect("equal")
    ax.set_title("plan view at the deck", fontsize=9)
    ax.set_xlabel("x")
    ax.set_ylabel("y")


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    stl = K.stl_dir()
    meshes = [trimesh.load(os.path.join(stl, f)) for f in ("sculpt_upper.stl", "sculpt_lower.stl", "face_mask.stl")]
    bins = np.arange(30.0, 360.0, 2.0)
    zs, ylo, yhi = silhouette(meshes, 1, bins)
    zs2, xlo, xhi = silhouette(meshes, 0, bins)
    ang, rmax = plan_outline(meshes, 0.0, AXIS_Y)

    out_dir = os.path.join(K.check_out(), "enclosure", "studies")
    os.makedirs(out_dir, exist_ok=True)
    fig, axs = plt.subplots(1, 3, figsize=(20, 11.5), gridspec_kw={"width_ratios": [1.15, 1, 1]})
    side_view(axs[0], zs, ylo, yhi)
    front_view(axs[1], zs2, xlo, xhi)
    plan_view(axs[2], ang, rmax)
    fig.suptitle("Enclosure concept: printed base and cap, a rolled clear sheet in slits, an opaque back column "
                 f"(D {2 * R_OUT:.0f} x {CAP_Z[1] - GROUND:.0f} tall)", fontsize=11)
    handles, labels = [], []
    for a in (axs[0], axs[2]):
        h, l = a.get_legend_handles_labels()
        handles += h
        labels += l
    fig.legend(handles, labels, loc="lower center", ncol=2, fontsize=7.5, framealpha=0.95)
    fig.subplots_adjust(left=0.04, right=0.99, top=0.92, bottom=0.26, wspace=0.18)
    png = os.path.join(out_dir, "enclosure_concept.png")
    fig.savefig(png, dpi=110)

    gap_f = R_SHEET - (yhi.max() - AXIS_Y)
    gap_b = R_SHEET - (AXIS_Y - ylo.min())
    gap_s = R_SHEET - max(-xlo.min(), xhi.max())
    arc_len = np.pi * (2 * R_SHEET + SHEET_T) * (360 - SPINE_ARC) / 360
    sheet_h = WINDOW_TOP + GROOVE_TOP - (BASE_Z[1] - GROOVE_LOW)
    lines = [
        "# Enclosure concept numbers", "",
        f"- Axis: x 0, y {AXIS_Y:.0f} (the neck's axis, SCULPT_NECK).",
        f"- Head about the axis: front r {yhi.max() - AXIS_Y:.0f}, back r {AXIS_Y - ylo.min():.0f}, "
        f"sides r {max(-xlo.min(), xhi.max()):.0f}; crown z {zs.max():.0f}.",
        f"- Sheet D {2 * R_SHEET:.0f} inside: clear {gap_f:.0f} at the face, {gap_b:.0f} at the back, {gap_s:.0f} at the ears.",
        f"- Sheet: {SHEET}, blank {arc_len:.0f} long x {sheet_h:.0f} tall ({360 - SPINE_ARC:.0f} deg of the circle).",
        f"- Rings D {2 * R_OUT:.0f} outside, 4 quadrants each (a quadrant's box is {R_OUT:.0f} x {R_OUT:.0f}, the bed is {BED:.0f}).",
        f"- Base {BASE_Z[1] - GROUND:.0f} tall (bay {BASE_Z[1] - DECK_T - BASE_Z[0] - FLOOR_T:.0f} clear inside), "
        f"window {WINDOW_TOP - BASE_Z[1]:.0f}, cap {CAP_Z[1] - CAP_Z[0]:.0f}; overall {CAP_Z[1] - GROUND:.0f}.",
        f"- Back column: {SPINE_ARC:.0f} deg arc, {SPINE_T:.0f} thick, 2 wide x 2 tall pieces "
        f"(each {2 * R_OUT * np.sin(np.radians(SPINE_ARC / 4)):.0f} chord x {(WINDOW_TOP - BASE_Z[1]) / 2:.0f} tall).",
        f"- Pedestal D {PEDESTAL[0]:.0f} to {PEDESTAL[1]:.0f}, {PEDESTAL[2]:.0f} tall, under the neck with "
        f"4 x M4 on a {P.NECK_BOLT_SQUARE:.0f} square and a D 25 bore.",
        f"- Neck (proposed, Q17): a D 100 column from z 0 to {COLUMN_TOP:.0f} (the open jaw's lowest point is z 88, 82 at "
        f"overtravel), then a {SPINE_Y[1] - SPINE_Y[0]:.0f} thick, {2 * SPINE_X:.0f} wide spine at y {SPINE_Y[0]:.0f}..{SPINE_Y[1]:.0f} "
        f"(the jaw's overtravel reaches y -92.5) up to z {SPINE_TOP:.0f}, bolted into the frame's nape ribs. "
        f"The jaw hangs from the frame and swings in front of the spine; the skin's neck stub covers it from z 40.",
        f"- Camera: Logitech 1080p webcam ({CAMERA[0]:.0f} x {CAMERA[1]:.0f} x {CAMERA[2]:.0f}, {CAMERA_FOV:.0f} deg) in a cradle "
        f"against the cap's front wall at z {CAMERA_Z:.0f}, lens behind a D {CAMERA_HOLE:.0f} hole among the vents, "
        f"{CAMERA_TILT:.0f} deg down; its 1.5 m USB lead runs round the cap ring and down the back column to the base. "
        f"Its two mics hear through the vent slots beside the lens, so the base needs no mic.",
        f"- Base bay: the power bank {BANK[0]:.0f} x {BANK[1]:.0f} x {BANK[2]:.0f}, the buck {BUCK[0]:.0f} x {BUCK[1]:.0f} x {BUCK[2]:.0f} "
        f"with the trigger, fuses, WAGOs and capacitor, and 2 boards {BOARD[0]:.0f} x {BOARD[1]:.0f} x {BOARD[2]:.0f}, all on the floor tray; "
        f"a back hatch under the column's foot for the bank and the leads out; the Sony SRS-XB12 (D {SPEAKER[0]:.0f} x {SPEAKER[1]:.0f}) on its side in a cradle at the front, "
        f"driver end at a {GRILLE[0]:.0f} x {GRILLE[1]:.0f} snap-out grille panel in the base's front (buttons and aux reached through it), "
        f"3.5 mm lead from the laptop, charged from the bank's USB-A port. The laptop stays outside.",
    ]
    with open(os.path.join(out_dir, "enclosure_concept.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print("\n".join(lines))
    print(f"wrote {png}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

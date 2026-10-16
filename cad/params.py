"""
Every tunable number of the Frankenstein head lives here, and only here.

Units: millimetres and degrees. Frame (docs/PLAN.md section 4, decision D2):
  x = 0  the facial midline (symmetry plane). +x is the CHARACTER'S LEFT, the
         viewer's right when looking at the face. Parts are named by the
         character's side: brow_L sits at +x.
  y = 0  the plane through both eyeball centres at rest. +y points out of the face.
  z = 0  the underside of the neck/base interface. +z is up.

Tags in comments (keep them honest; they tell the human what to measure):
  DATASHEET  - a published size; replace with a caliper measurement.
  ASSUMPTION - a decision nobody has confirmed yet.
  MEASURED   - calipered on the real part, or taken from a manufacturer model.
Derived values are computed here, never typed twice; the comment gives the
result so a reader can see it without running anything.
"""

# ---------------------------------------------------------------------------
# Printer and fits (2 x Bambu Lab P2S, 0.4 nozzle, 0.2 layers, PLA/PETG)
# ---------------------------------------------------------------------------
NOZZLE = 0.4
MIN_WALL = 2 * NOZZLE          # 0.8: thinnest wall that prints solid
SLIDE = 0.2                    # per side, parts slid together by hand (class 0.15..0.35)
CLEAR = 0.4                    # per side, printed parts that must never touch
EF_CHAMFER = 0.4               # elephant's foot: chamfer the bed-side edge and mating mouths

# ---------------------------------------------------------------------------
# Fasteners: M2.5 socket head screws into heat-set inserts. Kept for the
# calibration coupon until decision D6 picks the skull screw (PLAN Q7).
# ---------------------------------------------------------------------------
M25_CLEAR = 3.0                # clearance hole; prints ~0.1-0.2 small, still passes M2.5
M25_HEAD = (4.5, 2.5)          # socket head dia, height -- ASSUMPTION: the screws on hand
M25_CBORE = (5.5, 2.7)         # counterbore for that head
INSERT_HOLE_D = 4.0            # ruthex M2.5 x 5.7: hole diameter (coupon picks 3.9/4.0/4.1)
INSERT_L = 5.7
INSERT_HOLE_DEPTH = INSERT_L + 1.0   # 6.7: blind, 1 mm extra for melt overflow
INSERT_WALL = 1.6              # minimum plastic around the hole
INSERT_BOSS_D = INSERT_HOLE_D + 2 * INSERT_WALL   # 7.2

# ---------------------------------------------------------------------------
# Head size (decision D4)
# ---------------------------------------------------------------------------
# The proxy head below is an average adult at scale 1.0. The Cogley modules
# are real parts and never scale; the head scales around them.
HEAD_SCALE = 1.2               # ASSUMPTION (D4): EyeMech eye spacing 75.0 / adult 63 = 1.19
HEAD_SCALES_COMPARED = (1.0, 1.1, 1.2, 1.3)   # layout_check reports each, for D4

# ---------------------------------------------------------------------------
# Proxy head (stands in for the sculpt until M5)
# ---------------------------------------------------------------------------
# Horizontal sections at scale 1.0, z measured from the eye line (eye centres
# at z = 0 here). Each row: (z, half_width, y_front, y_widest, y_back, n_front)
#   half_width  half the width at its widest
#   y_front     the front of the face at the midline (no nose: the sculpt adds it)
#   y_widest    where the section is widest
#   y_back      the back of the head (or of the neck, below the skull). The nape and
#               neck are deliberately thick (neck ~144 x 128 at 1.2x): the open jaw swings
#               back toward them and the cable channel runs down between (2026-10-15)
#   n_front     superellipse exponent of the front half; > 2 = a flatter face,
#               < 2 = a pointed front (the chin in front of the neck)
# ASSUMPTION: rough adult male averages (head breadth ~156, glabella to back
# ~207 with skin, chin to crown ~237), to be replaced by the sculpt.
HEAD_SHAPE = "boxy_temples"   # ASSUMPTION (D4), 2026-10-15; was "average"
HEAD_SHAPES = {
    "average": (
        (+120.0, 20.0, -45.0, -75.0, -105.0, 2.0),   # crown cap
        (+110.0, 48.0, -20.0, -80.0, -140.0, 2.2),
        (+90.0, 66.0, +5.0, -85.0, -168.0, 2.3),
        (+60.0, 76.0, +18.0, -88.0, -182.0, 2.4),    # forehead
        (+30.0, 78.0, +24.0, -90.0, -183.0, 2.5),    # widest (head breadth 156)
        (+10.0, 74.0, +27.0, -90.0, -176.0, 2.6),    # brow ridge
        (0.0, 72.0, +24.0, -88.0, -170.0, 2.6),      # eye line (nose bridge at the midline)
        (-20.0, 70.0, +24.0, -80.0, -158.0, 2.6),    # cheekbones
        (-45.0, 62.0, +24.0, -72.0, -138.0, 2.5),    # nose base; the back is the skull base
        (-68.0, 55.0, +27.0, -60.0, -126.0, 2.4),    # mouth
        (-92.0, 52.0, +22.0, -62.0, -120.0, 2.0),    # jaw: the section runs back to the neck
        (-112.0, 56.0, +16.0, -66.0, -117.0, 1.5),    # chin: neck-wide behind, pointed in front
        (-130.0, 60.0, -10.0, -62.0, -117.0, 2.0),   # neck, just under the jaw
    ),
    # Frankenstein variant: the same heights and depths, with a flatter, wider
    # front half from the forehead to the cheekbones (higher n_front), so the
    # temples clear the EyeMech's side plates.
    "boxy_temples": (
        (+120.0, 20.0, -45.0, -75.0, -105.0, 2.0),
        (+110.0, 48.0, -20.0, -80.0, -140.0, 2.2),
        (+90.0, 66.0, +5.0, -85.0, -168.0, 2.4),
        (+60.0, 76.0, +18.0, -88.0, -182.0, 2.8),
        (+30.0, 78.0, +24.0, -90.0, -183.0, 3.2),
        (+10.0, 75.0, +27.0, -90.0, -176.0, 3.4),
        (0.0, 74.0, +24.0, -88.0, -170.0, 3.4),    # temples: +2 on average
        (-20.0, 72.0, +24.0, -80.0, -158.0, 3.0),
        (-45.0, 62.0, +24.0, -72.0, -138.0, 2.6),
        (-68.0, 55.0, +27.0, -60.0, -126.0, 2.4),
        (-92.0, 52.0, +22.0, -62.0, -120.0, 2.0),
        (-112.0, 56.0, +16.0, -66.0, -117.0, 1.5),
        (-130.0, 60.0, -10.0, -62.0, -117.0, 2.0),
    ),
}
HEAD_SECTIONS_1X = HEAD_SHAPES[HEAD_SHAPE]
NECK_BELOW_CHIN_1X = 60.0      # ASSUMPTION: neck stub from the chin (z -117) down to the base
CHIN_Z_1X = -117.0             # ASSUMPTION: chin bottom below the eye line
NECK_BASE_Z_1X = CHIN_Z_1X - NECK_BELOW_CHIN_1X   # -177: the base interface, z = 0 in the frame
assert HEAD_SECTIONS_1X[-1][0] > NECK_BASE_Z_1X, "the neck section must sit above the base"
EYE_Z = -NECK_BASE_Z_1X * HEAD_SCALE              # 212.4: eye line above the base at HEAD_SCALE
STOMION_DZ_1X = -70.5          # ASSUMPTION (D4), 2026-10-15; was -68.0 (adult ~65-70). The extra
                               # 3 mm at 1.2x opens the eye-to-mouth gap from 2.5 to 5.5, room for a skull shelf

# Skin and skull (decision D7 and Q11 refine these into zones)
SKIN_T = 5.0                   # ASSUMPTION: silicone thickness over the skull, one value for M1
LIP_SKIN_T = 8.0               # ASSUMPTION: silicone in front of the Cogley lip plates
SKULL_WALL = 2.4               # skull shell: 6 perimeters at 0.4

# ---------------------------------------------------------------------------
# Will Cogley modules (inputs/reference), placed whole: one rotation and one
# translation each. Source-frame values are MEASURED from the STEP files.
# ---------------------------------------------------------------------------
EYEMECH_FILE = "reference/eyemech/EyeMech_e3.1.step"
EYEMECH_ROT_Z = 180.0          # the file faces -y; ours faces +y
EYEMECH_EYE_SRC = (37.5, 0.0, 0.0)   # MEASURED: lid sphere centres (+-37.5, 0, 0), R 16.5 / 18.1
EYE_SPACING = 2 * EYEMECH_EYE_SRC[0]  # 75.0: centre to centre (adult ~63)
EYE_R = 16.0                   # MEASURED: eyeball part 32.0 across

MOUTH_FILE = "reference/mouth/MouthAssembly.step"
MOUTH_ROT_Z = 180.0            # the file faces -y
MOUTH_STOMION_SRC = (0.0, -92.6, -71.2)  # MEASURED: lip plates' front y; midway between the
                                         # upper plate bottom (z -65.2) and lower plate top (-77.2)
MOUTH_JAW_AXIS_SRC = (-2.4, -40.7)       # MEASURED: (y, z) of the jaw pivot (x axis): JawLink
                                         # bore R4.5/10.5 on the MG996R output spline
MOUTH_TOP_SRC_Z = -19.25                 # MEASURED: the mouth's top plate (TopBase), its highest point

# ---------------------------------------------------------------------------
# Motion (M1 pose sweeps). Joint angles in degrees from the pose the STEP
# files are modelled in (jaw closed, lids closed, eyes straight ahead).
# ASSUMPTION until Cogley's firmware limits and a bench test confirm them.
# ---------------------------------------------------------------------------
JAW_OPEN_DEG = 25.0            # ASSUMPTION: full open (shout); speech uses less
UPPER_LIP_PLATES = ("UpperLeftLip", "Part_34")   # Part_34: the mirrored upper plate
LOWER_LIP_PLATES = ("LowerLeftLip", "Part_37")   # Part_37: the mirrored lower plate
JAW_OVERTRAVEL_DEG = 10.0      # swept past the limit to learn the real margin
JAW_GROUP_CORE = ("JawBase", "JawLink", "Part_33", "Part_22")   # jaw base, both jaw links, and the
                               # tongue (Part_22: its servo sits on the jaw base)
JAW_HORN_R = 14.0              # MG996R output parts (horn, spline, horn screws) centred this close
JAW_HORN_X_MIN = 44.0          # to the jaw axis and outboard of the servo bodies (|x| 3..43) turn with it
JAW_GROUP_BELOW_AXIS = 30.0    # candidates: mouth solids centred this far below the jaw axis; each
                               # joins the jaw if it sits closer to the jaw's parts than the frame's
# EyeMech ranges: DATASHEET = Cogley's firmware servo limits (Code/NewFaceFollower.py,
# 2026-10-15): LR and UD 40..140, lids 90..170 / 90..10 / 90..160. Servo degrees, swept
# here as if the linkages were 1:1, which can only overstate the motion (a safe upper bound).
EYE_PAN_DEG = 50.0             # DATASHEET (upper bound): +- left/right
EYE_TILT_DEG = 50.0            # DATASHEET (upper bound): +- up/down
LID_TOP_OPEN_DEG = 80.0        # DATASHEET (upper bound): top lids, closed (as modelled) to open
LID_BOTTOM_OPEN_DEG = 80.0     # DATASHEET (upper bound): bottom lids
SWEEP_STEP_DEG = 5.0
MOTION_CLEAR_MIN = 1.0         # mm: least gap between a moving part and anything else, any pose
# Clashes the team accepts on bench evidence: ((moving label, static label), max mm3, why).
# Reported as info, not as a failure; anything larger, or any other pair, still fails.
ACCEPTED_CONTACTS = (
    (("Part_22", "MG90s_servo_FIX_v1_Mirror_"), 10.0,
     "D12: tongue corner vs a mouth servo (up to 8.6 mm3 in CAD); the team's printed mouth "
     "runs without trouble (2026-10-15)"),
)

# ---------------------------------------------------------------------------
# Reserved space: placeholders the later milestones design inside
# (absolute mm in the head frame at HEAD_SCALE)
# ---------------------------------------------------------------------------
# Brow mechanism, per side (M2): a servo bay above the EyeMech and a carrier
# band in front of it reaching down to the brow line, both trimmed by the
# skin's inner surface. Heights are mm above the eye line.
BROW_X = (14.0, 62.0)          # ASSUMPTION: |x| range, each side
BROW_BAY_Y = (-40.0, 60.0)     # front is trimmed by the skin
BROW_BAY_Z = (38.0, 75.0)      # ASSUMPTION: clear of the EyeMech's central pivot (top at +35.7)
BROW_BAND_Y_MIN = 8.0          # ASSUMPTION: the carrier band stays in front of the EyeMech pivots (front y +5)
BROW_BAND_Z = (20.0, 40.0)     # ASSUMPTION: eyebrow line ~24-30 above the eye centre at 1.2x
# Cable channel for every servo lead to the neck (M3 designs the real route)
CABLE_D = 25.0                 # ASSUMPTION: 19 three-wire leads with connectors and slack
CABLE_PATH = ((0.0, -140.0, 205.0), (0.0, -120.0, 140.0), (0.0, -114.0, 80.0),
              (0.0, -90.0, 25.0), (0.0, -90.0, 0.0))   # ASSUMPTION: behind the EyeMech, behind the mouth
                                   # and the open jaw, down the back of the neck, out square through the base

# ---------------------------------------------------------------------------
# Eyebrows (M2). Sizes in mm at HEAD_SCALE; heights above the eye line.
# Motion is measured along the skin at mid-brow.
# ---------------------------------------------------------------------------
BROW_LINE_Z = 26.0             # ASSUMPTION: brow line above the eye line (22 at 1.0x)
BROW_INNER_X = 14.0            # ASSUMPTION: |x| of the brow's inner end (matches BROW_X)
BROW_OUTER_X = 60.0            # ASSUMPTION: |x| of the outer end
BROW_PLATE_H = 16.0            # ASSUMPTION: height of the carrier plate under the skin
BROW_RAISE = 10.0              # ASSUMPTION: mid-brow up along the skin (8 at 1.0x)
BROW_LOWER = 5.0               # ASSUMPTION: mid-brow down (4 at 1.0x)
BROW_INNER_BIAS = 1.5          # ASSUMPTION (D5): the inner end travels this many times the outer end
BROW_GAP = 1.5                 # ASSUMPTION: carrier face to the skin's inner surface
BROW_PUSH_MAX = 1.0            # ASSUMPTION: a pad may move this much toward the skin (keeps 0.5 of the gap)
BROW_PULL_MAX = 3.0            # ASSUMPTION: and this much away from it (the snap brings the skin along)
BROW_PADS_X = (22.0, 52.0)     # ASSUMPTION (M4 sizes the snaps): |x| of the inner and outer snap pads
BROW_PAD = 10.0                # ASSUMPTION: pad face, square; the bar between the pads sits deeper
# Mechanism v1 (2026-10-15): the pads and their bar ride on a carrier that turns
# about a pivot on a printed bracket; an MG90S in the bay above drives it through
# a 2:1 four-bar (horn -> M2 ball-link pushrod -> carrier lever).
BROW_PIVOT_R = 45.0            # from the concept study: pivot behind mid-brow along the face normal
BROW_PIVOT_OFFSET = 4.0        # and this far up the face
BROW_PIVOT_SKEW = 12.0         # deg, axis turned in plan so the inner pad travels more (D5)
BROW_PAD_T = 3.0               # pad thickness behind its face
BROW_BAR_RECESS = 2.8          # the bar's front sits this far behind the pad faces (bites 0.2 into the pads)
BROW_BAR = (5.0, 4.0)          # bar height x depth
BROW_ARM = (5.0, 5.0)          # arm section
BROW_ARM_RISE = 34.0           # the arm arches over the lids at this height above the eye line
SHOULDER_D = 4.0               # DATASHEET: ISO 7379 M3 shoulder screw, shoulder diameter
SHOULDER_L = 10.0              # DATASHEET: a stock shoulder length (4, 5, 6, 8, 10, 12 ...)
SHOULDER_HEAD = (8.0, 4.0)     # ASSUMPTION: head diameter, height (caliper the screws bought)
SHOULDER_BORE = SHOULDER_D + 2 * 0.15   # 4.3: running fit on the shoulder
BROW_HUB_D = 10.0
PIVOT_PLAY = 0.4               # axial play of the hub between the screw head and the cheek
INSERT_RECESS = 0.3            # the cheek's insert sits in a recess this deep, so an insert left a
                               # little proud can't rub the hub; the shoulder seats on the insert
BROW_HUB_L = SHOULDER_L - INSERT_RECESS - PIVOT_PLAY   # 9.3
BROW_CHEEK_T = 7.0             # bracket cheek holding the pivot; 7 so an M3 x 4 heat-set insert fits with 2 behind
BROW_ROCKER_R = 18.0           # carrier lever: pivot to the pushrod ball
BROW_CRANK_R = 9.0             # servo horn: shaft to the pushrod ball (2:1)
BROW_COUPLER_L = 30.0          # ball to ball; the threaded ball links adjust it (neutral position)
BALL_LINK_D = 6.0              # ASSUMPTION: M2 ball link body, for clearance
BALL_STUD_H = 3.5              # ASSUMPTION: M2 ball stud, ball centre above its mounting face
BROW_FLANGE_T = 7.0            # top flange: 2 x M3 x 4 heat-set inserts from the top face
BROW_MOUNTS = ((15.0, 3.5), (15.0, -15.5))   # (x', y') of the flange inserts
# Hard stops (brief §4): two M3 set screws in a ledge under the flange, driven from above
# through key holes in the flange. One meets the double-arm horn's front arm (limits raise),
# the other its back arm near the hub (that arm rises when the brow lowers: limits lower).
BROW_STOP_LEDGE_Z = (40.0, 46.0)   # z' of the ledge
BROW_STOPS_Y = (-2.5, -24.0)      # y' of the raise stop (front arm) and the lower stop (back arm,
                                  # 15 out from the shaft, past the pushrod ball: 3.5 mm of motion)
BROW_STOP_MARGIN = 0.5            # stops set this far past the travel ends (adjust on the bench)
HORN_ARM_W = 5.0                  # ASSUMPTION: MG90S double-arm horn, arm width
HORN_BACK_R = 17.5                # ASSUMPTION: its back arm's length from the shaft (the stop meets it at 15)
HORN_FRONT_R = 9.5                # the front arm CUT to this length (flush cutters): full length hits the upright
M3_TAP = 2.5                      # self-tapping M3 set screw into PLA/PETG
HEX_KEY_D = 3.0                   # access for a 1.5 mm hex key

# MG90S (MEASURED from Adafruit's MG90D model, inputs/components; caliper the real ones)
MG90_W = 12.0                  # case width
MG90_CASE_L = 22.6             # case length; the shaft sits MG90_SHAFT_FROM_END from one end
MG90_SHAFT_FROM_END = 6.0
MG90_BELOW_TAB = 18.8          # case bottom below the tabs' underside
MG90_ABOVE_TAB = 3.88          # case top above the tabs' underside
MG90_TAB_SPAN = 31.3
MG90_TAB_T = 2.0
MG90_HOLE_SPACING = 29.7       # tab holes, d 1.7
MG90_HOLE_OFFSET = -9.7        # first tab hole from the shaft, along the case length
MG90_SPLINE_TOP = 11.88        # above the tabs' underside
MG90_HORN_Z = 10.4             # ASSUMPTION: horn mid-plane above the tabs' underside
M2_PILOT = 1.6                 # self-tapping M2 into PLA/PETG
M3_CLEAR = 3.4
M3_INSERT_HOLE = 4.0           # ASSUMPTION: M3 x 4 heat-set insert (coupon picks the size)
# Bench rig (M2): a printed forehead fragment around the left brow (head frame, mm)
BROW_RIG_X = (2.0, 74.0)       # inner wall clear of the shoulder screw head, outer wall 4.6 past the servo
BROW_RIG_Y = (-66.0, 45.0)     # back of the frame .. in front of the face (the shell is trimmed to the skin)
BROW_RIG_Z = (0.0, 82.0)       # above the eye line: base .. top of the forehead fragment (base clear of the clamp bosses)
BROW_RIG_T = 4.0               # base, walls, ceiling
BROW_RIG_WINDOW_CLEAR = 1.5    # around the pads' whole travel
BROW_RIG_WINDOW_OVER = 3.0     # extra window height at each end: room for overtravel if a stop is set loose
BROW_RIG_ACCESS_D = 9.0        # hole in the inner wall in line with the shoulder screw

# ---------------------------------------------------------------------------
# Skull (M3) v0: the shell between the skin's and the skull's inner surfaces,
# opened where the mechanisms meet the skin, split into printable pieces.
# ---------------------------------------------------------------------------
SKULL_SPLIT_Z = 186.0          # ASSUMPTION: front upper (eyes, brows) | front lower (mouth); just under the EyeMech
SKULL_SPLIT_Y = -60.0          # ASSUMPTION: front pieces | back pieces (each piece then fits the 256 bed)
EYE_OPEN_R = 20.0              # eye openings: lid outer radius 18.1 + 1.9 clearance, straight forward
MOUTH_OPEN_X = 46.0            # ASSUMPTION: half-width of the mouth opening (mouth module 112 wide)
MOUTH_OPEN_Z = (88.0, 168.0)   # ASSUMPTION: mouth opening from above the chin's curve (an edge on it left slivers) to above the upper lip plates (top 165.8)
SHELF_T = 2.4                  # the shelf between the EyeMech (above) and the mouth (below)
SHELF_GAP_BELOW = 1.0          # shelf underside above the mouth's top plate
SHELF_Y = (-118.0, 8.0)       # shelf from behind the EyeMech base to under the front of its side plates
BROW_MOUNT_T = 4.0             # plates the brow brackets bolt up into (like the bench rig's ceiling)
# Joints between the skull pieces: screwed tabs (code-cad shapes.md). A tab is a patch of
# thickened inner wall on one piece, reaching across the seam behind the other piece's wall;
# an M3 countersunk screw goes from outside through that wall into an insert in the tab, its
# head flush with the skull's outer surface (under the skin: no hard point).
SEAM_TAB_T = 5.5               # tab thickness inside the wall: M3 x 4 insert + 1.5
SEAM_TAB_W = 12.0              # tab size along the seam
SEAM_TAB_OVER = (6.0, 10.0)    # tab reach on its own side, and across the seam behind the other wall
SEAM_TAB_SPACING = 40.0        # mm along a seam between tabs (fewer where the wall is open or crowded)
SEAM_TAB_CLEAR = 1.5           # tabs keep this far from every module and brow part (1.0 + sample spacing)
M3_CSK = (6.3, 1.75)           # ISO 10642 M3 countersunk head: diameter, depth (90 deg)
# EyeMech cradle on the shelf (ASSUMPTION until the printed EyeMech is on the bench): pads
# under its feet, a stop behind its rear foot (shims there set the eye depth); the skull's
# temple walls (about 1 mm off its side plates) locate it sideways, and a printed strap 0.2
# over the back of its base plate keeps it down. The shelf bolts down onto four ledges on the
# side walls; the strap onto two ledges on the back upper piece.
CRADLE_PAD_MARGIN = 1.0        # pads overhang the feet by this all round
CRADLE_STOP = (2.4, 4.0)       # rear stop: thickness, height above the feet's underside
CRADLE_CLEAR = 0.4             # the stop to the EyeMech's rear foot (the 'clear' fit class)
STRAP_Y = (-113.0, -104.0)     # the strap's band across the back of the base plate (clear of its servos)
STRAP_GAP = 0.4                # above the base plate's top: it keeps it down (0.4 lift at most), without clamping
STRAP_T = 4.0
SHELF_LEDGES_Y = (-40.0, -95.0)   # ledges under the shelf on each side wall, one per skull piece
SHELF_LEDGE = (12.0, 24.0, 6.0)   # reach from the wall, length, depth under the shelf
# Neck base (M3): a plate closing the bottom of the neck, with a collar 0.4 inside the neck
# wall; countersunk M3 screws through the wall into inserts in the collar; M4 bolts down
# into the jar's stand (the stand isn't designed: the pattern is an ASSUMPTION to match).
NECK_PLATE_T = 6.0
NECK_COLLAR = (6.0, 18.0)      # collar thickness inside the wall, height above the base
NECK_SCREW_Z = 10.0            # height of the radial screws into the collar
NECK_SCREWS = 6                # around the neck, evenly by angle
NECK_BOLT_SQUARE = 50.0        # ASSUMPTION: 4 x M4 on this square, centred on the neck
M4_CLEAR = 4.5
CABLE_EXIT_CLEAR = 1.5         # around the cable channel where it leaves through the plate
# Rear access panel (brief §5): cut from the back of the head, resting on a narrow lip inside
# the opening, held by 4 countersunk M3 screws into inserts in pads on the lip.
PANEL_CENTRE_Z = 268.0         # ASSUMPTION: above the cable channel's top (205) and the EyeMech
PANEL_SIZE = (96.0, 74.0, 12.0)  # width (x), height (z), corner radius
PANEL_GAP = 0.3                # all round, between the panel and its opening
PANEL_LIP = (4.0, 5.5)         # the lip's reach behind the panel's edge, thickness
PANEL_SCREW_IN = 5.5           # screw axis in from the opening's edge: countersink 2 inside the panel
PANEL_PAD = 13.0               # square pad on the lip round each screw: 4.5 wall beside the insert

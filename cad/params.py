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
EYEMECH_EYE_R = (16.5, 18.1)   # MEASURED: the lids' inner and outer sphere radii
EYE_SPACING = 2 * EYEMECH_EYE_SRC[0]  # 75.0: centre to centre (adult ~63)
EYE_R = 16.0                   # MEASURED: eyeball part 32.0 across
EYE_SOCKET_FRONT = 8.0         # MEASURED: the eyeball's socket (the pivot's cavity) reaches this far in front of its centre
EYEBALL_FILL_FROM = 8.5        # the smooth eyeball (studies/cogley_eyeball.py): his front, iris dish and pupil hole,
                               # is filled out to EYE_R from this far in front of the centre

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
BACK_UPPER_OUT_DEG = 52.0      # the back upper piece comes off this far up from straight back; the tabs
                               # on its seams go on whichever piece they can't hook that way
# Service (service_check.py): the teardown's moves, after the back upper piece is off
SERVICE_EYE_OUT = ((0.0, -50.0, 0.0), (0.0, -50.0, 4.0), (0.0, -220.0, 4.0))   # EyeMech + both brows:
                               # back 50 (the brows' flanges slide off their plates), up 4 (over the
                               # back lower piece's rim), out
SERVICE_SHELF_OUT = ((0.0, 0.0, 8.0), (0.0, -250.0, 8.0))   # off its ledges, then out the back
SERVICE_TOL = 0.3              # mm a move may pass into a part (sampling noise; real contact slides)
SERVICE_KEY = (20.0, 65.0, 2.0)  # L hex key 2.5 (M3 socket heads): short arm, long arm, clearance radius
SERVICE_STUBBY_KEY = (12.0, 65.0, 2.0)  # the same key with its short arm cut to 12: the front brow
                               # flange screws have 16.3 mm under the crown
SERVICE_KEY_SWING = 60.0       # deg of clear swing a hex key needs per bite
SERVICE_HEAD_H = 3.0           # M3 socket head height: the key starts on its top
M3_CSK = (6.3, 1.75)           # ISO 10642 M3 countersunk head: diameter, depth (90 deg)
# EyeMech cradle (ASSUMPTION until the printed EyeMech is on the bench): pads on the shelf
# under its feet; the skull's temple walls (about 1 mm off its side plates) locate it
# sideways; a printed strap 0.4 over the back of its base plate keeps it down, and a stop
# hanging from the strap behind the base plate's rear lip sets the eye depth (with shims).
# The shelf bolts down onto four ledges on the side walls; the strap onto two ledges on the
# back upper piece, and comes off with it, so the EyeMech's way out straight back is clear.
CRADLE_PAD_MARGIN = 1.0        # pads overhang the feet by this all round
CRADLE_STOP = (2.4, 60.0)      # the strap's stop behind the base plate's rear lip (x +-38.7): thickness, width
CRADLE_CLEAR = 0.4             # the stop to the EyeMech's base plate (the 'clear' fit class)
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

# ---------------------------------------------------------------------------
# Sculpt base v2 (M5, D17: sculpt_base.py). A smooth wrap of Cogley's complete head (his
# outer shell, cheek bone, and the fronts of the eyes, brows and mouth) as a solid head the
# clay face is sculpted on, standing on a base plate. Whole head, normal proportions (D13).
SCULPT_MIN_SKIN = 3.0          # ASSUMPTION: thinnest skin over any of his parts
SCULPT_GRID = 1.0              # voxel size of the wrap
SCULPT_TIGHT = (7.0, 2.0)      # tight wrap: closing radius, blur (it hugs every part; at 6 and 1.5 it
                               # pinched shut in the narrow gaps between the brow bars and the lips)
SCULPT_SMOOTH = (32.0, 10.0)   # smooth wrap: closing radius, blur (a head-like form)
SCULPT_FACE_INFLATE = 11.0     # the smooth wrap grows this much at the face, so it swallows the
                               # mechanism's lumps there...
SCULPT_FACE_FADE_Y = (-50.0, 0.0)  # ...fading in from y -50 (behind the ears) to y 0 (the eyes)
SCULPT_MOVING_CLEAR = (8.0, 15.0)  # ...but not within 8 of the lips, brows and lids (full 15 further
                               # on), where the skin must stay thin enough to move with them
SCULPT_BLEND = 10.0            # soft union of the smooth and tight wraps
SCULPT_NECK = (50.0, 54.0, -70.0, 40.0)  # neck stub: semi-axes x, y; centre y; bottom z (ASSUMPTION, Q17)
SCULPT_SPLIT_Z = 186.0         # split for the bed (below the eyes)
SCULPT_GROOVE = 1.2            # width of the marking grooves (half as deep)
SCULPT_GROOVE_GAP = 2.0        # grooves stop this far short of the eye sockets
SCULPT_EYE_CAP = 4.0           # eye sockets go this far behind the lids' front, to show a cap of their sphere
SCULPT_PUPIL = 3.0             # dimple at the front pole of each eye
SCULPT_SOCKET_CEILING_DEG = 55.0  # the sockets' ceilings, above horizontal: prints upright without supports
SCULPT_PLATE = (8.0, 25.0)     # base plate: thickness, margin round the neck
SCULPT_PLATE_CBORE = (8.5, 4.5)  # M4 socket head counterbore under the plate: the head seats at z -3.5,
                               # so an M4 x 12 ends at z 8.5, inside the 10 deep insert hole
SCULPT_KEY = (12.0, 6.0)       # mold registration cones in the plate's top: diameter, depth
SCULPT_BOARD_SCREW = 5.0       # holes to screw the plate to a board or turntable
SCULPT_DOWEL = (6.3, 13.0)     # dowel holes across the split: diameter (6 x 24 dowels), depth each side
                               # (1 spare at each end: the printed hole ends sag, glue collects)
SCULPT_DOWELS_XY = ((40.0, -30.0), (-40.0, -30.0), (40.0, -120.0), (-40.0, -120.0))
M4_INSERT_HOLE = 5.6           # ASSUMPTION: M4 x 8 heat-set insert (check with the coupon's maker)
M4_INSERT_DEPTH = 10.0

# ---------------------------------------------------------------------------
# Face mask (M5, D19: face_mask.py). A thin shell of a man's face from the MakeHuman base
# mesh (CC0), warped so its features sit on the mechanism, clear of Cogley's head. Its skin is
# read as a radius over directions (azimuth, elevation, degrees) from a point in the head.
MASK_SCALE = 1.15              # MakeHuman's face scaled up like the head (HEAD_SCALE): it then spans
                               # Cogley's mechanism, and its eyes land within 0.5 of the EyeMech's
MASK_FEATURE_SCALE = 1.05      # the nose wings are held at MakeHuman's width times this
MASK_MOUTH_PAST = 1.0          # the mouth's corners sit this far past the ends of Cogley's lip plates
                               # (MakeHuman's lips scaled evenly to get there: team, 2026-10-16)
MASK_FINAL_SMOOTH = 2          # Taubin passes over the finished skin: prints smooth
                               # (the overall scale made them 20 % too wide)
MASK_MALE = (10.0, 4.0)        # a man's face: jaw angles this much wider each side; brow ridge forward
MASK_CENTRE_BACK = 75.0        # the directions start this far behind the eyes (15 below them)
MASK_GRID_DEG = 0.25           # direction grid (about 0.5 mm on the face)
MASK_IRIS = (4.0, 1.6, 0.8)    # iris ring radius, pupil radius, pupil depth: centred on the eye axis
                               # (inside the eye opening: 6.5 ran onto the lids)
MASK_HEAD_SMOOTH = 8           # Taubin passes over MakeHuman's subdivided head (its low-poly facets)
MASK_SKIN_SMOOTH = 0.9         # the plain skin (not the eyes, nose, lips) smoothed this much, degrees
MASK_LIP_ZONE = 8.0            # the gap between the lips is closed within this far above and below them (mm)
MASK_LIP_LINE = 0.7            # the line where the lips meet, cut this deep (mm)
MASK_LIP_MARKS = (9.0, 11.0, 0.5)  # the lips are flat, with a line round each: upper and lower
                               # lip height at the middle, line depth (mm)
MASK_LIP_FLAT = 18.0           # the mouth is flat this far above and below the parting line (mm)
MASK_EYE_FLAT = (21.0, 13.0)   # each eye flat (no eyeball, no lids) this far across and up/down (mm)
MASK_NOSE_KEEP = 0.35          # the nose kept at this share of its height: a guide to build on
MASK_PUSH_SMOOTH = 4.0         # and of the push out over Cogley's helmet, degrees
MASK_TOP_SMOOTH = 4.0          # the forehead and skull, smoothed hard above the brows, degrees
MASK_CORE_OK = 0.05            # the whole face moves forward until only this share of its middle
                               # still needs a local push
MASK_BULGE = 14.0              # pushes clear of Cogley's head spread this wide, degrees
MASK_LINE = (0.9, 0.55)        # the iris ring: depth, width (mm)
MASK_OUTLINE = (112.0, 55.0, -55.0, 0.0)  # egg outline: half width, top and bottom elevation (deg),
                               # widening toward the top; it reaches over the forehead onto the skull
MASK_T = 2.0                   # shell thickness, inward (thin: saves filament, team 2026-10-16)

# ---------------------------------------------------------------------------
# Mold base (M5, mold_base.py): the printed base the clay-covered face mask lies on, face up,
# while the plaster mold is made over it. It seats the mask exactly (a ledge under its rim and a
# lip inside it), closes the space under the rim with a skirt that flares down to a flat flange,
# and walls the flange in. The same base later holds the mask as the core for the silicone cast,
# so the mold's keys must find it again. Mold pose: X = x, Y = -z (chin toward +Y), Z = y + lift
# (face up), plate underside on the table at Z = 0.
MOLD_PLATE_T = 6.0             # base plate thickness
MOLD_RIM_LIFT = 8.0            # the mask's lowest rim point (by the ears) sits this far above the plate
MOLD_SEAT = (0.4, 2.4, 6.0)    # ASSUMPTION: gap to the printed mask, lip thickness, lip length up the
                               # inside of the mask (the print may differ from the STL by a few 0.1 mm)
MOLD_LIP_ROOT = 5.0            # the lip thickens to this at its root: its inside then stands steeper than 45 deg
                               # where the mask curves over at the forehead (2.4 all along leaned 49 deg)
MOLD_SEAT_DROP = 4.0           # the collar under the rim is this deep before the skirt's inside starts
MOLD_SKIRT = (4.0, 12.0)       # skirt thickness, draft (degrees from vertical; it flares out going down,
                               # so the plaster lifts straight off it)
MOLD_ROOM = 42.0               # the walls stand at least this far outside the mask seen from above:
                               # clay (ASSUMPTION up to 12) + plaster and burlap jacket (about 20) + margin
MOLD_FLANGE = 40.0             # and at least this far outside the skirt's foot: the mold's flat flange
MOLD_WALL = (45.0, 6.0)        # wall height above the plate, thickness. The walls are 4 separate L-shaped
                               # corners standing on the plate, clipped together: they come off outward
                               # before the plaster is lifted (mold boxes are always taken off first)
MOLD_RIB = (4.0, 4.0, 20.0)    # rib on the plate just inside the walls: width, height, inner face draft (deg);
                               # it locates the walls and stops plaster running under them
MOLD_EAR = (16.0, 4.0, 3.4, (12.0, 33.0))  # ears where the wall corners meet: reach out from the wall,
                               # thickness, hole (M3 bolt, zip tie) and hole heights above the plate;
                               # or one binder clip per joint (two don't fit on a 45 mm ear)
MOLD_KEY = (22.0, 12.0, 8.0)   # registration cones on the flange: base dia, top dia, height
MOLD_KEYS_X = 75.0             # two cones at each end of the flange, this far either side of the midline
MOLD_PRY = (18.0, 14.0, 14.0, 7.0, 5.0)  # loose pry wedges (separate prints, 8 off) standing in gaps in the
                               # rib against the walls: width at the wall, width inside, length in from the
                               # wall, height at the wall, height inside. Tapered every way, so once the
                               # walls are off each pulls straight out (an M3 screw in its end) and leaves
                               # a slot under the flange's edge for a screwdriver
MOLD_PRY_GAP = 0.2             # clearance per side in the rib gap the wedge stands in
MOLD_PRY_X = 40.0              # two on each end wall, this far either side of the midline
MOLD_PRY_Y = (-110.0, -290.0)  # and two on each side wall, at these Y
MOLD_POST_R = 12.0             # posts under the mask's forehead and cheeks: radius
MOLD_POST_GAP = 1.0            # pad top this far under the mask's inside (a pea of clay fills it)
MOLD_POSTS = ((40.0, -262.0), (-40.0, -262.0), (52.0, -168.0), (-52.0, -168.0))   # (X, Y) mold pose
MOLD_SPLIT_Y = -200.0          # the 4 pieces split at X = 0 and at this Y (= -z: through the ears,
                               # where the skirt is shortest), so each fits the 256 bed
MOLD_FIT = 0.15                # clearance per side in the joints between the pieces
MOLD_TAB = (10.0, 16.0, 12.0)  # plate dovetails: neck width, head width, depth
MOLD_TABS_X = (-22.0, -120.0, -285.0, -362.0)   # dovetails along X = 0, at these Y
MOLD_TABS_Y = (55.0, 128.0)    # dovetails along the Y split, at these |X|

# ---------------------------------------------------------------------------
# Enclosure (M8, D23-D26): a canister round the head, v1 (2026-10-29): thin prints plus two PETG
# sheets. Eleven prints: cap halves, top ring halves (the deck), bottom ring halves, the tray, the
# pedestal, the neck, two panels. The window is one clear 1 mm PETG sheet rolled into a full tube
# (the back is see-through: no column); the base's wall is a second PETG band, painted or black,
# between the two rings. cad/enclosure.py builds it, enclosure_check.py checks it. Axis: x 0,
# y ENC_AXIS_Y (the neck's axis); every radius is about it; z is the head frame (z 0 = the pedestal's
# top = the neck's foot). Angles: 0 deg = +x, 90 deg = +y (the front). Halves split on the y = 0
# line: F covers 0..180 deg, B 180..360.
# ---------------------------------------------------------------------------
ENC_AXIS_Y = SCULPT_NECK[2]        # -70
ENC_R_OUT = 146.0                  # the rims' and the cap skirt's outside (D 292); a half turned 45 deg on the bed spans 249
ENC_SHEET_R = 138.2                # inside face of the window sheet (D 276.4): 19 clear of the face, 21 of the nape
ENC_SHEET_T = 1.0                  # 1 mm clear PETG (D24)
ENC_LIP = (1.8, 8.0)               # the lips that make the window's channels: thickness, height; the channel is 2.4 wide
ENC_LIP_R = (136.0, 139.8)         # the inner lip's inner radius, the outer lip's inner radius (channel 137.8..139.8)
ENC_BAND_R = 144.0                 # inside face of the base's PETG band (D 288): it wraps the rings' rims
ENC_RIM = (2.0, 10.0)              # the rims the band wraps: thickness (r 142..144), height
ENC_PLATE_T = 1.6                  # the rings' plates (4 lines)
ENC_CAP_T = 1.2                    # the cap's top (6 layers of 0.2), ribbed
ENC_RIB = (1.6, 4.0)               # ribs under the plates: thickness, height
ENC_SEAM_WALL = (1.6, 8.0)         # the halves' seam walls, back to back, 2 x M3 + nut through both: thickness, height
ENC_FIT = 0.3
ENC_TRAY = (250.0, 2.5)            # tray: diameter, thickness; it is the floor, everything stands on it
ENC_TRAY_Z = -150.0                # the tray's underside (rubber feet below it)
ENC_TRAY_RIBS = ((120.0, 3.0, 6.0), (40.0, 3.0, 6.0))   # ring ribs on the tray: inner radius, thickness, height (the bottom
                                   # rings' ears screw into the outer one, the pedestal's inward flange into the inner one)
ENC_BOTTOM_RING = (136.0, 142.0)   # bottom ring halves: a narrow plate inside the rim, with 4 ears in to the tray's rib
ENC_BOTTOM_EAR = (117.5, 14.0)     # the ears: reach in to this radius (1.8 past their screw holes), width; the bay is open out to r 136 below them
ENC_EARS_DEG = (30.0, 150.0, 210.0, 330.0)   # where the ears (and the tray's outer rib's screw holes) sit: clear of the bank
ENC_TOP_RING = (46.0, 142.0)       # top ring halves (the deck): plate from r (round the pedestal's D 90 tube) to the rim
ENC_TOP_Z = -40.0                  # the deck's top face: the window stands on it
ENC_BAND_SCREWS_DEG = (30.0, 90.0, 150.0, 210.0, 270.0, 330.0)   # M3 + nut through each rim and the band
ENC_BAND_SCREW_Z = 5.0             # above the ring's top face, in the rim
ENC_WINDOW_TOP = 400.0             # the cap's skirt reaches down to here
ENC_CAP_Z = 440.0                  # the cap's underside; its top is ENC_CAP_T above
ENC_SHEET_TOP = 438.0              # the sheet's top edge, 6 inside the cap's channel
ENC_CAP_VENTS = (3.0, 60.0, 8.0, 5)   # vent slots in the cap's top: width, length, pitch, count per group (front and back)
ENC_WEBCAM = (94.0, 29.0, 24.0)    # ASSUMPTION: a Logitech C920-class body (w, h, d)
ENC_WEBCAM_Y = 127.0               # the body's front face (y'): inside the window, 11 behind the sheet, looking out through it;
                                   # its corners (x +-47) then clear the cap's inner lip (r 136)
ENC_PEDESTAL = 90.0                # a straight D 90 tube down to the tray (the neck's D 100 foot overhangs it 5); printed upside down
ENC_PEDESTAL_WALL = 1.6
ENC_PEDESTAL_TOP_T = 4.0           # the top plate under the neck's foot
ENC_PEDESTAL_FLANGE = (6.0, 3.0)   # the bottom flange, inward: reach, thickness; 4 x M3 self-tapping into the tray's inner rib
ENC_BORE = 25.0                    # cable + air bore through the neck's foot and the pedestal's top
ENC_OPENING = (110.0, 64.0, -104.0)   # the openings cut by hand in the band, front (speaker) and back (hatch): chord, height, centre z
ENC_PANEL = (126.0, 96.0, -102.0, 2.0)   # the grille and hatch panels over them: chord, height, centre z, thickness
ENC_PANEL_SCREWS = (59.0, -146.0, -58.0)  # 4 x M3 + nut through the panel and the band, at +-x and these z
ENC_PANEL_LEAD_NOTCH = (24.0, 8.0)
ENC_VENT = (3.0, 7.0)              # the panels' slots: height, pitch
ENC_BANK = (161.0, 55.0, 50.0)     # ASSUMPTION (listing): UGREEN Nexode 145 W power bank
ENC_BUCK = (85.0, 60.0, 28.0)      # ASSUMPTION (listing): ACEIRMC 20 A buck with its heatsink
ENC_BOARD = (95.0, 65.0, 20.0)     # ASSUMPTION: a Cogley mouth board with its Pico
ENC_SPEAKER = (74.0, 92.0)         # Sony SRS-XB12 (listing): diameter, length; lies along y at the front
ENC_LAYOUT = {"speaker": (0.0, 85.0, 90.0), "bank": (0.0, -80.0, 0.0), "buck": (-85.0, 8.0, 90.0),
              "board_1": (-50.0, -80.0, 0.0), "board_2": (50.0, -80.0, 0.0)}   # (x, y', turn): ASSUMPTION. The speaker
                                   # lies along x at the front; the bank across the back, the two boards flat on top of it
                                   # (standoffs or tape); the buck on its side at the left; the power box bits at the right
ENC_LAYOUT_Z = {"bank": 6.0, "buck": 6.0, "board_1": 56.0, "board_2": 56.0}   # heights above the tray: the bank and the buck
                                   # ride on the tray's ribs, the boards lie on the bank
ENC_SADDLE = (77.0, 3.0, 50.0, (-30.0, 30.0), 6.5)   # speaker saddle ribs: length (along y), thickness, height, x positions,
                                   # the seat's bottom above the tray (the belly clears the 6 mm ribs)
ENC_BANK_RAIL = (2.0, 10.0, 20.0)  # rails either side of the bank: thickness, height, shorter than the bank by
ENC_LEAD_SLOT = (12.0, 100.0, 130.0)   # the webcam lead's slot in the top ring's back half: width, r from, r to
M3_CLEAR = 3.4
M3_NUT = (5.7, 2.6)                # hex nut: across flats (plus fit), thickness
M3_SELF_TAP = 2.6                  # hole for an M3 screw cut into PLA
ENC_BOSS_D = 7.0                   # bosses round the tray's self-tapping holes (its ribs are 3 thick)
M3_INSERT_HOLE = 4.0               # ASSUMPTION: M3 x 4 heat-set insert (the coupon decides)
M3_INSERT_DEPTH = 6.7
M3_HEAD = (6.0, 3.2)
_sheet_c = 2 * 3.141592653589793 * (ENC_SHEET_R + ENC_SHEET_T / 2)   # 871.6: the window's circumference at its middle
ENC_SHEET_BLANK = (int(round(_sheet_c + 20.0)), int(ENC_SHEET_TOP - ENC_TOP_Z - 1.0))   # 892 x 477: a full tube, 20 overlap
_band_c = 2 * 3.141592653589793 * (ENC_BAND_R + ENC_SHEET_T / 2)     # 908: the band's circumference
ENC_BAND_BLANK = (int(round(_band_c + 20.0)), int(round((ENC_TOP_Z + ENC_RIM[1]) - (ENC_TRAY_Z + ENC_TRAY[1] + ENC_TRAY_RIBS[0][2] + ENC_PLATE_T) - 1.0)))
                                   # 928 x 110: from the bottom ring's plate to the top of the top ring's rim
# Neck (D25): a tube on the pedestal, then a spine behind the jaw's swing into Cogley's frame's nape
NECK_TUBE = (100.0, 2.5, 70.0)     # outer dia, wall, top z (the open jaw's lowest point is z 88, 82 at overtravel)
NECK_FOOT_T = 12.0                 # foot with 4 x M4 inserts on NECK_BOLT_SQUARE, bolted up through the pedestal's top
NECK_SPINE_Y = (-125.0, -95.0)     # the spine's y range in the head frame (the jaw's overtravel reaches y -92.5)
NECK_SPINE_X = 40.0                # half width
NECK_SPINE_TOP = 170.0             # just under the frame's nape members (measured from his mesh 2026-10-28: a cross member at
                               # y -101..-95, x +-24, underside z 172; two side rails at x +-36..40, y -125..-98, underside
                               # z 173..176). ASSUMPTION: 4 x M3 up into inserts heat-set into those members, shimmed
NECK_SPINE_NOTCH = ((29.0, 41.0), (-117.0, -94.0), 148.0)   # two of his ribs come down through the spine's footprint
                               # at x +-30..34, from z 169 (y -112) to 150 (y -95): notches (|x| range, y range, from z)
NECK_SPINE_SCREWS = ((18.0, -98.0), (-18.0, -98.0), (36.0, -121.5), (-36.0, -121.5))   # (x, y) of the 4 x M3 up into the frame
NECK_SPINE_WALL = 2.0              # hollow (the leads come down inside), with a 45 deg roof under its top plate
NECK_SPINE_HOLLOW_STEP = (140.0, 26.0)   # above this z the hollow narrows to this half width, clear of the notches
NECK_SPINE_TOP_T = 6.0
NECK_SPINE_TOP_OPENING = (40.0, 16.0, -112.0)   # the leads' way in: an opening in the top plate, x width, y depth, centre y
NECK_SPINE_JOIN_Z = (20.0, 70.0)   # the opening between the spine's inside and the tube's inside
assert NECK_TUBE[2] < 82.0, "the neck tube must stay under the jaw's overtravel sweep (z 82)"
assert NECK_SPINE_Y[1] < -92.5, "the spine must stay behind the jaw's overtravel sweep (y -92.5)"
assert ENC_R_OUT * (1 + 0.7071) <= 256.0, "a half turned 45 deg on the bed must fit 256"

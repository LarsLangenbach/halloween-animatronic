"""
The engine's channel contract (docs/FACE_ENGINE.md, "Frame and channels"). Every part imports
its names and ranges from here, so they agree.

Sides are the character's own: L is Frank's left (+x). Gaze follows eyes.py: yaw + to his left,
pitch + up.
"""

TAGS = ("neutral", "curious", "excited", "skeptical", "amused",
        "concentrating", "confused", "irritated", "surprised", "vulnerable")
STATES = ("idle", "person", "greeting", "listening", "thinking", "speaking", "interrupted", "farewell")
EVENTS = ("blink", "long_blink", "flinch", "greet", "beat", "phrase_end")

# Joint channels, the animator's output and the rig's input: name -> (low, high, rest).
JOINTS = {
    "gaze_x": (-1.0, 1.0, 0.0),        # +1 = fully to his left (eye_anim.LOOK_LR of servo travel)
    "gaze_y": (-1.0, 1.0, 0.0),        # +1 = fully up (eye_anim.LOOK_UD)
    "lid_top_L": (0.0, 1.0, 0.85),     # 0 = saved SHUT pose, 1 = saved OPEN pose
    "lid_top_R": (0.0, 1.0, 0.85),
    "lid_bot_L": (0.0, 1.0, 1.0),      # 1 = saved OPEN pose (down); lower = raised (squint)
    "lid_bot_R": (0.0, 1.0, 1.0),
    "brow_in_L": (-1.0, 1.0, 0.0),     # +1 raised by RAISE deg, -1 lowered by LOWER deg
    "brow_out_L": (-1.0, 1.0, 0.0),
    "brow_in_R": (-1.0, 1.0, 0.0),
    "brow_out_R": (-1.0, 1.0, 0.0),
    "smile": (-1.0, 1.0, 0.0),         # + smile, - frown (mouth.py corners)
    "smile_asym": (-1.0, 1.0, 0.0),    # + his left corner more, - his right corner more
    "jaw_floor": (0.0, 1.0, 0.0),      # jaw opened at least this much; speech can open it more
}
BROWS = ("brow_in_L", "brow_out_L", "brow_in_R", "brow_out_R")
LIDS_TOP = ("lid_top_L", "lid_top_R")
LIDS_BOT = ("lid_bot_L", "lid_bot_R")

# Face target, the synthesiser's output and the animator's input: name -> (low, high, rest).
FACE = {
    **{b: JOINTS[b] for b in BROWS},
    "smile": JOINTS["smile"], "smile_asym": JOINTS["smile_asym"], "jaw_floor": JOINTS["jaw_floor"],
    "lid_open": (-1.0, 1.0, 0.0),       # upper lids: + wider, - heavier, 0 = rest
    "lid_squint": (0.0, 1.0, 0.0),      # lower lids raised
    "lid_asym": (-1.0, 1.0, 0.0),       # + his left eye narrower than his right
    "gaze_bias_x": (-1.0, 1.0, 0.0),    # where the feeling pulls the eyes
    "gaze_bias_y": (-1.0, 1.0, 0.0),
    "gaze_steady": (0.0, 1.0, 0.0),     # fewer, smaller saccades
    "gaze_avert": (0.0, 1.0, 0.0),      # more and longer looks away
    "gaze_alternate": (0.0, 1.0, 0.0),  # brief alternating glances
    "arousal": (-1.0, 1.0, 0.0),        # the PAD point; arousal sets speed
    "valence": (-1.0, 1.0, 0.0),
    "dominance": (-1.0, 1.0, 0.0),
}


def rest_joints():
    return {k: v[2] for k, v in JOINTS.items()}


def rest_face():
    out = {k: v[2] for k, v in FACE.items()}
    out["weights"] = {t: 0.0 for t in TAGS}
    return out


def clamp(name, value, table=JOINTS):
    lo, hi, _ = table[name]
    return lo if value < lo else hi if value > hi else value


def blank_cue():
    return {"state": "idle", "target": None, "others": [], "talk": 0.0, "events": []}

"""
Slider window for setting the mouth's servo angles by hand from the PC.

Cogley's MouthMaster.py drives the mouth with a fixed angle per servo for each pose
(mouth_closed, mouth_open, lips_down, ...). Those angles depend on where each servo horn was
fitted, so the team's build needs its own. This window has one slider per mouth servo, named
by the part and by its socket on the mouth board (MouthMaster.py's names), and a table of his
poses: GO drives the mouth to a pose, SAVE stores the sliders as that pose. The poses live in
mouth_poses.json next to this file and start at Cogley's values.

The Pico can run either of two programs as main.py; the window asks the board which:
  - cogley_mouth_main.py, the TalkingHead mouth program (Machine Monks/LARS 9001/HeadTest).
    It answers `where`, so the window sends `set <servo> <deg>` and `relax`. That program
    glides every servo and clamps it to its own limits; a clamped command shows in the status
    line. It lets the servos go only all at once, so the per-servo Loose buttons are off and
    the sliders start at the angles the board reports.
  - pico_servo_ctl.py. It is silent; the window sends `<GP pin> <deg>` and `<GP pin> off`.
Run on the PC:
    uv run --no-project --with pyserial python firmware/mouth_controls.py [COM9] [--cogley]
--cogley skips the question. The port "demo" opens the window without a Pico and prints the
commands instead; "demo --selftest" (and "demo --cogley --selftest") presses every button once
and quits (used to check the program).
"""

import json
import os
import sys
import tempfile
import tkinter as tk

PORT = sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith("--") else "COM9"
SELFTEST = "--selftest" in sys.argv
COGLEY = "--cogley" in sys.argv   # otherwise set by the board's answer below

# (label, socket, GP pin). The sockets and pins are MouthMaster.py's. L and R are Cogley's
# names; which side of the face each one moves is not confirmed yet (wiggle it to see).
SERVOS = [
    ("Jaw, servo L", "JL", 4),
    ("Jaw, servo R", "JR", 5),
    ("Upper lip, servo L", "LUL", 6),
    ("Upper lip, servo R", "LUR", 7),
    ("Lower lip, servo L", "LLL", 8),
    ("Lower lip, servo R", "LLR", 9),
    ("Upper mouth corner, servo L", "CUL", 10),
    ("Upper mouth corner, servo R", "CUR", 11),
    ("Lower mouth corner, servo L", "CLL", 12),
    ("Lower mouth corner, servo R", "CLR", 13),
    ("Tongue", "TON", 14),
]
PIN = {socket: pin for _, socket, pin in SERVOS}
LO, HI = 20, 160  # slider range; Cogley's pose angles span 40..140, so 20 deg past them each way
WIGGLE = 15       # deg each way for the Wiggle button
GO_SECS = 0.4     # a GO eases the servos to the pose over this long (his code jumps)
TICK_MS = 20

# Cogley's poses from MouthMaster.py, keyed as his code keys them so the saved file maps
# straight onto his `poses` dict. "lips_rest" is ours: his code never sets the lips at rest.
# Each SAVE stores only the servos listed here for that pose.
POSE_LIST = [
    ("Mouth CLOSED", "mouth_closed", {"JL": 90, "JR": 90}),
    ("Mouth OPEN", "mouth_open", {"JL": 50, "JR": 130}),
    ("Lips REST", "lips_rest", {"LUL": 90, "LUR": 90, "LLL": 90, "LLR": 90}),
    ("Lips DOWN", "lips_down", {"LUL": 110, "LUR": 70, "LLL": 55, "LLR": 110}),
    ("Lips UP", "lips_up", {"LUL": 40, "LUR": 140, "LLL": 110, "LLR": 60}),
    ("Tongue DOWN", "tongue_down", {"TON": 130}),
    ("Tongue UP", "tongue_up", {"TON": 55}),
    ("Corners NARROW", "narrow", {"CUL": 90, "CUR": 80, "CLL": 90, "CLR": 90}),
    ("Corners WIDE", "wide", {"CUL": 65, "CUR": 105, "CLL": 120, "CLR": 65}),
    ("Smile", "smile", {"CUL": 60, "CUR": 105, "CLL": 90, "CLR": 90}),
    ("Frown", "frown", {"CUL": 100, "CUR": 75, "CLL": 90, "CLR": 90}),
]
REST = ("mouth_closed", "lips_rest", "tongue_down", "narrow")  # his start-up pose, plus the lips

POSES_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "mouth_poses.json")
if SELFTEST:
    POSES_FILE = os.path.join(tempfile.gettempdir(), "mouth_poses_selftest.json")
POSES = {key: dict(angles) for _, key, angles in POSE_LIST}
SAVED = set()   # poses read from the file; the others are defaults
if os.path.exists(POSES_FILE) and not SELFTEST:
    with open(POSES_FILE) as f:
        for key, angles in json.load(f).items():
            POSES.setdefault(key, {}).update(angles)
            SAVED.add(key)

# cogley_mouth_main.py's own limits (its LIMITS); a command past them is cut to the limit.
# The jaw's limits follow its jawdir and jawdeg, read from the board.
BOARD_LIMITS = {
    "LUL": (40, 110), "LUR": (70, 140), "LLL": (55, 110), "LLR": (60, 110),
    "CUL": (60, 100), "CUR": (75, 105), "CLL": (90, 120), "CLR": (65, 90), "TON": (55, 130),
}


class DemoSerial:
    """Stands in for the Pico: prints the commands (or just counts them in the self-test)."""

    in_waiting = 0

    def __init__(self):
        self.count = 0

    def write(self, data):
        self.count += 1
        if not SELFTEST:
            print(data.decode().strip())

    def read(self, n=1):
        return b""

    def reset_input_buffer(self):
        pass

    def close(self):
        pass


def ask(ser, cmd, prefix, secs=1.0):
    """Send `cmd`; return the first reply line that starts with `prefix`, or None."""
    import time

    ser.reset_input_buffer()
    ser.write(cmd.encode() + b"\n")
    reply, end = b"", time.time() + secs
    while time.time() < end:
        reply += ser.read(ser.in_waiting or 1)
        if prefix.encode() in reply and reply.endswith(b"\n"):
            break
    for line in reply.decode(errors="replace").splitlines():
        if line.startswith(prefix):
            return line.strip()
    return None


def ask_where(ser):
    """The board's answer to `where` as {servo: angle or None} if it runs cogley_mouth_main.py.
    Only that program answers; pico_servo_ctl.py and a bare REPL give no "JL=" line."""
    line = ask(ser, "where", "JL=")
    if line is None:
        return None
    angles = {}
    for item in line.split():
        name, _, value = item.partition("=")
        angles[name] = None if value == "off" else int(value)
    return angles


WHERE = {}
if PORT == "demo":
    ser = DemoSerial()
    PROGRAM = "cogley (demo)" if COGLEY else "pins (demo)"
else:
    import time
    import serial

    ser = serial.Serial(PORT, 115200, timeout=0)
    where = None if COGLEY else ask_where(ser)
    if where is None and not COGLEY:
        ser.write(b"\x03\x03")  # stop whatever runs (a REPL left by Thonny, for one)
        time.sleep(0.3)
        ser.write(b"\x04")      # soft reset: main.py starts again
        time.sleep(1.5)
        where = ask_where(ser)
    COGLEY = COGLEY or where is not None
    WHERE = where or {}
    PROGRAM = "cogley_mouth_main.py" if COGLEY else "pico_servo_ctl.py"
    if COGLEY:
        for cmd in ("jawdir", "jawdeg"):
            line = ask(ser, cmd, cmd + " ")
            if line:
                WHERE["_" + cmd] = float(line.split()[1])
    ser.reset_input_buffer()
    print(f"mouth_controls: {PORT}, board program {PROGRAM}")

# Slider range per servo: the board's limits on cogley_mouth_main.py, else LO..HI.
RANGE = {socket: (LO, HI) for socket in PIN}
if COGLEY:
    jaw_dir = -1 if WHERE.get("_jawdir", -1) < 0 else 1   # the board's defaults: -1, 40
    jaw_deg = WHERE.get("_jawdeg", 40)
    jl, jr = round(90 - jaw_dir * jaw_deg), round(90 + jaw_dir * jaw_deg)   # jaw fully open
    RANGE.update(BOARD_LIMITS)
    RANGE["JL"] = (min(90, jl), max(90, jl))
    RANGE["JR"] = (min(90, jr), max(90, jr))
    if "mouth_open" not in SAVED:
        POSES["mouth_open"] = {"JL": jl, "JR": jr}
    print(f"mouth_controls: jaw direction {jaw_dir}, travel {jaw_deg:g}: open is JL {jl}, JR {jr}")


def send(socket, value):
    """Move one servo (value: degrees) or let it go (value: "off")."""
    if COGLEY:
        ser.write(b"relax\n" if value == "off" else f"set {socket} {value}\n".encode())
    else:
        ser.write(f"{PIN[socket]} {value}\n".encode())
        ser.reset_input_buffer()


def loose_all():
    if COGLEY:
        ser.write(b"relax\n")
    else:
        for socket in PIN:
            send(socket, "off")


def rest_angle(socket):
    for key in REST:
        if socket in POSES[key]:
            return POSES[key][socket]
    return 90


def ease(x):
    x = min(1.0, max(0.0, x))
    return x * x * (3 - 2 * x)


ready = [False]   # Scale.set() fires the slider command; ignore it until the window is up
quiet = [False]   # ... and while the program itself moves a slider


def slide(socket, value):
    if ready[0] and not quiet[0]:
        send(socket, value)


root = tk.Tk()
root.title(f"Mouth servos  -  {PORT}, board program {PROGRAM}")
if SELFTEST:
    root.withdraw()
if COGLEY:
    top_text = ("Drag a slider to move that servo. This board's program glides each servo to the angle and "
                "clamps it to its limits (a clamp shows at the bottom). It lets servos go only all at once: ALL LOOSE.")
else:
    top_text = ("Drag a slider to move that servo. A servo stays loose until its slider is touched; "
                "Loose lets it go again.")
tk.Label(root, text=top_text, font=("Segoe UI", 10)).grid(row=0, column=0, columnspan=6, pady=(8, 0))
tk.Label(root, text="Go slowly near the ends: a servo that buzzes is pushing against a stop. Loose it. "
         "L and R are Cogley's names; Wiggle one to see which side moves.",
         font=("Segoe UI", 10), fg="#a33").grid(row=1, column=0, columnspan=6, pady=(0, 6))

by_socket = {}   # socket -> slider
jobs = []        # pending root.after ids of a running move


def cancel_jobs():
    for j in jobs:
        root.after_cancel(j)
    jobs.clear()


def set_servo(socket, a):
    s = by_socket[socket]
    lo, hi = RANGE[socket]
    a = round(max(lo, min(hi, a)))
    quiet[0] = True
    s.set(a)
    quiet[0] = False
    send(socket, a)


for row, (label, socket, pin) in enumerate(SERVOS, start=2):
    tk.Label(root, text=label, font=("Segoe UI", 11), anchor="w", width=28).grid(row=row, column=0, padx=8)
    lo, hi = RANGE[socket]
    tk.Label(root, text=f"{socket}  GP{pin}", font=("Segoe UI", 11, "bold"), width=9).grid(row=row, column=1)
    s = tk.Scale(root, from_=lo, to=hi, orient="horizontal", length=420, resolution=1,
                 command=lambda v, sk=socket: slide(sk, v))
    reported = WHERE.get(socket)
    s.set(reported if reported is not None else rest_angle(socket))
    s.grid(row=row, column=2, padx=4)
    by_socket[socket] = s

    def middle(s=s, sk=socket):
        s.set(90)
        send(sk, 90)

    def wiggle(s=s, sk=socket, lo=lo, hi=hi):
        cancel_jobs()
        start = s.get()
        steps = [min(hi, start + WIGGLE), max(lo, start - WIGGLE)] * 3 + [start]
        for i, a in enumerate(steps):
            jobs.append(root.after(400 * i, lambda a=a: (s.set(a), send(sk, a))))

    def loose(sk=socket):
        cancel_jobs()
        send(sk, "off")

    tk.Button(root, text="90", width=4, command=middle).grid(row=row, column=3, padx=2)
    tk.Button(root, text="Wiggle", width=7, command=wiggle).grid(row=row, column=4, padx=2)
    tk.Button(root, text="Loose", width=6, command=loose,
              state="disabled" if COGLEY else "normal").grid(row=row, column=5, padx=(2, 8))

root.update()
ready[0] = True


def go(targets, secs=GO_SECS, delay_ms=0):
    """Ease the servos in `targets` ({socket: angle}) from their sliders to the angles."""
    start = {socket: by_socket[socket].get() for socket in targets}
    n = max(1, round(secs * 1000 / TICK_MS))
    for i in range(1, n + 1):
        k = ease(i / n)

        def tick(k=k):
            for socket, a in targets.items():
                set_servo(socket, start[socket] + (a - start[socket]) * k)
        jobs.append(root.after(delay_ms + TICK_MS * i, tick))
    return delay_ms + TICK_MS * n


def angles_text(angles):
    return "  ".join(f"{k} {v}" for k, v in angles.items())


def go_pose(key):
    cancel_jobs()
    go(POSES[key])
    status.config(text=f"{pose_name[key]}: " + angles_text(POSES[key]))


def save_pose(key):
    POSES[key] = {socket: by_socket[socket].get() for socket in POSES[key]}
    with open(POSES_FILE, "w") as f:
        json.dump(POSES, f, indent=2)
    saved_label[key].config(text=angles_text(POSES[key]))
    status.config(text=f"Saved {pose_name[key]}: " + angles_text(POSES[key]))


def rest_face():
    cancel_jobs()
    # one group every 300 ms, so not every servo starts at once on the supply
    for i, key in enumerate(REST):
        go(POSES[key], delay_ms=300 * i)
    status.config(text="Rest: mouth closed, lips at rest, tongue down, corners narrow.")


def open_close():
    cancel_jobs()
    t = 0
    for _ in range(3):
        t = go(POSES["mouth_open"], delay_ms=t) + 300
        t = go(POSES["mouth_closed"], delay_ms=t) + 400
    status.config(text="Open and close three times, between the saved OPEN and CLOSED.")


def all_loose():
    cancel_jobs()
    loose_all()
    status.config(text="Every servo loose.")


# The pose table: name, the angles in use, GO and SAVE.
pose_name = {key: name for name, key, _ in POSE_LIST}
saved_label = {}
table = tk.LabelFrame(root, text="Poses (Cogley's angles until you SAVE your own)", font=("Segoe UI", 10),
                      padx=8, pady=4)
table.grid(row=len(SERVOS) + 2, column=0, columnspan=6, padx=8, pady=(10, 0), sticky="ew")
for r, (name, key, _) in enumerate(POSE_LIST):
    tk.Label(table, text=name, font=("Segoe UI", 10, "bold"), anchor="w", width=16).grid(row=r, column=0, sticky="w")
    saved_label[key] = tk.Label(table, text=angles_text(POSES[key]), font=("Consolas", 10), anchor="w", width=40)
    saved_label[key].grid(row=r, column=1, sticky="w")
    tk.Button(table, text="GO", width=6, command=lambda k=key: go_pose(k)).grid(row=r, column=2, padx=4, pady=1)
    tk.Button(table, text="SAVE sliders", width=12, command=lambda k=key: save_pose(k)).grid(row=r, column=3, padx=4)

bottom = tk.Frame(root)
bottom.grid(row=len(SERVOS) + 3, column=0, columnspan=6, pady=10)
tk.Button(bottom, text="REST FACE", font=("Segoe UI", 11, "bold"), bg="#c8e6c9", command=rest_face).pack(
    side="left", padx=8)
tk.Button(bottom, text="OPEN / CLOSE x3", font=("Segoe UI", 11, "bold"), bg="#c5d8f0", command=open_close).pack(
    side="left", padx=8)
tk.Button(bottom, text="ALL LOOSE", font=("Segoe UI", 11, "bold"), bg="#f4c7c3", command=all_loose).pack(
    side="left", padx=8)

status = tk.Label(root, text=f"Poses file: {POSES_FILE}", font=("Segoe UI", 10), fg="#444")
status.grid(row=len(SERVOS) + 4, column=0, columnspan=6, pady=(0, 8))

rx = [b""]


def read_board():
    """cogley_mouth_main.py answers every line. Drop its echoes; show a clamp or an error."""
    if COGLEY:
        rx[0] += ser.read(ser.in_waiting or 1)
        *lines, rx[0] = rx[0].split(b"\n")
        for raw in lines:
            line = raw.decode(errors="replace").strip()
            if line and not line.startswith("Received:"):
                status.config(text="Board: " + line)
    root.after(50, read_board)


def close():
    cancel_jobs()
    all_loose()
    ser.close()
    root.destroy()


def selftest():
    """Press every button once, let the moves run, then quit. Fails loudly on any exception."""
    for s in by_socket.values():
        s.set(100)
    for _, key, _ in POSE_LIST:
        go_pose(key)
        save_pose(key)
    with open(POSES_FILE) as f:
        saved = json.load(f)
    want = {k: by_socket[k].get() for k in ("JL", "JR")}
    assert saved["mouth_open"] == want, (saved["mouth_open"], want)
    assert set(saved) == {key for _, key, _ in POSE_LIST}
    rest_face()
    root.after(2500, open_close)
    root.after(7000, close)


root.protocol("WM_DELETE_WINDOW", close)
root.after(50, read_board)
if SELFTEST:
    root.after(100, selftest)
root.mainloop()
if SELFTEST:
    print(f"selftest ok ({PROGRAM}): {ser.count} commands sent, poses saved to {POSES_FILE}")

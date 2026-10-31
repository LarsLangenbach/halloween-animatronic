"""
Slider window for testing the eye and brow servos by hand from the PC.

The Pico needs pico_servo_ctl.py saved as main.py. Run on the PC:
    uv run --no-project --with pyserial python firmware/servo_controls.py [COM9] [--link]
--link: the port is the mouth board's; the eye board is reached through it over the link wires
(every line is sent as "e <pin> <angle>", which pico_servo_ctl.py passes on over UART0).

One slider per servo, labelled by part and by the mouth-board socket it plugs into
(eyes_brows_bench_test.py's layout). A servo stays loose until its slider is touched;
"Loose" lets it go again. Sides are as seen standing in front of the face.

EYES ALIVE runs eye_anim.py: the eyes look around at random and blink. It needs the lids'
SHUT and OPEN poses and the gaze CENTRE, set with the sliders and saved with the pose
buttons (eye_poses.json, next to this file).

The brow buttons play brow_anim.py's expressions (CHARACTER.md section 6) from the brows'
LEVEL pose, up to "Raise" and down to "Lower" degrees (the two boxes; "Save brows LEVEL"
stores the brow sliders and the two numbers in eye_poses.json). BROWS ALIVE adds small
random brow movements on top; BROW SHOW plays every expression in turn.
"""

import json
import os
import sys
import time
import tkinter as tk

import serial

from brow_anim import EXPRESSIONS, LOWER, ORDER, RAISE, SOCKETS as BROWS, BrowAnim
from eye_anim import BOTTOM_LIDS, LR, TOP_LIDS, UD, EyeAnim

ARGS = [a for a in sys.argv[1:] if not a.startswith("--")]
PORT = ARGS[0] if ARGS else "COM9"
# --link: the port is the MOUTH board's, and every line goes on to the eye board over the link
# wires as "e <pin> <angle>" (pico_servo_ctl.py forwards it over UART0, GP16 to GP17).
LINK = "--link" in sys.argv
PREFIX = "e " if LINK else ""

# (label, socket, GP pin, slider low, slider high). Eyes: Cogley's limits from eyes.py for the
# gaze; the lids get -9..189 (2026-10-29: the lids needed to go further than 30..160; the Pico
# program allows -27..207, 200..2800 us, but poses at 186 made the lids erratic, so the sliders
# stop at -9..189 again; go slowly near the ends and Loose a lid that buzzes against its stop).
# Brows: the full range; his Brows.py uses only 80..100, which barely shows (bench 2026-10-26).
SERVOS = [
    ("Both eyes: left / right", "LLL", 8, 40, 140),
    ("Both eyes: up / down", "LLR", 9, 60, 140),
    ("Eye on your RIGHT: top lid", "CUR", 11, -9, 189),
    ("Eye on your RIGHT: bottom lid", "CUL", 10, -9, 189),
    ("Eye on your LEFT: top lid", "CLR", 13, -9, 189),
    ("Eye on your LEFT: bottom lid", "CLL", 12, -9, 189),
    ("Brow on your LEFT: outer", "JL", 4, 0, 180),
    ("Brow on your RIGHT: outer", "JR", 5, 0, 180),
    ("Brow on your LEFT: inner", "LUL", 6, 0, 180),
    ("Brow on your RIGHT: inner", "LUR", 7, 0, 180),
]
WIGGLE = 20   # deg each way for the Wiggle button
LIDS = TOP_LIDS + BOTTOM_LIDS
GAZE = (LR, UD)

# Eye poses on the team's build, set on the sliders (MEASURED 2026-10-27, restored 2026-10-29
# evening: the afternoon's poses at 186 made the lids erratic). The pose buttons save all three
# to eye_poses.json, which overrides these. Never guess an OPEN pose: a wrong one could drive a
# lid into its stop.
POSES_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "eye_poses.json")
POSES = {
    "shut": {"CUR": 160, "CUL": 30, "CLR": 130, "CLL": 105},
    "open": {"CUR": 128, "CUL": 118, "CLR": 160, "CLL": 31},
    "centre": {"LLL": 84, "LLR": 67},
    "level": {s: 90 for s in BROWS},            # brows level (Brows.py rests at 90)
    "brow_travel": {"raise": RAISE, "lower": LOWER},   # deg up and down from level
}
if os.path.exists(POSES_FILE):
    with open(POSES_FILE) as f:
        POSES.update(json.load(f))


def neutral_angle(socket):
    # Neutral face for fitting the skin: eyes centred, lids shut, brows level (Brows.py rests at 90)
    for pose in ("shut", "centre", "level"):
        if socket in POSES[pose]:
            return POSES[pose][socket]
    return 90

ser = serial.serial_for_url(PORT, 115200, timeout=0)   # also socket:// (perform/body.py)
ser.write(b"\x03\x03")  # stop whatever runs
time.sleep(0.3)
ser.write(b"\x04")      # soft reset: main.py (pico_servo_ctl.py) starts
time.sleep(1.5)
ser.reset_input_buffer()


def send(pin, value):
    ser.write(f"{PREFIX}{pin} {value}\n".encode())
    ser.reset_input_buffer()


ready = [False]  # Scale.set() fires the slider command; ignore it until the window is up


def slide(pin, value):
    if ready[0]:
        send(pin, value)


root = tk.Tk()
root.title("Eye and brow servos")
tk.Label(root, text="Drag a slider to move that servo. 90 = middle. Loose = no power to it.",
         font=("Segoe UI", 10)).grid(row=0, column=0, columnspan=6, pady=(8, 4))

sliders = []
by_socket = {}
for row, (label, socket, pin, lo, hi) in enumerate(SERVOS, start=1):
    tk.Label(root, text=label, font=("Segoe UI", 11), anchor="w", width=30).grid(row=row, column=0, padx=8)
    tk.Label(root, text=socket, font=("Segoe UI", 11, "bold"), width=5).grid(row=row, column=1)
    s = tk.Scale(root, from_=lo, to=hi, orient="horizontal", length=420, resolution=1,
                 command=lambda v, p=pin: slide(p, v))
    s.set(90)
    s.grid(row=row, column=2, padx=4)
    sliders.append((s, pin, socket))
    by_socket[socket] = (s, pin, lo, hi)

    def middle(s=s, p=pin):
        s.set(90)
        send(p, 90)

    def wiggle(s=s, p=pin, lo=lo, hi=hi):
        start = s.get()
        steps = [min(hi, start + WIGGLE), max(lo, start - WIGGLE)] * 3 + [start]
        for i, a in enumerate(steps):
            root.after(400 * i, lambda a=a: (s.set(a), send(p, a)))

    tk.Button(root, text="90", width=4, command=middle).grid(row=row, column=3, padx=2)
    tk.Button(root, text="Wiggle", width=7, command=wiggle).grid(row=row, column=4, padx=2)
    tk.Button(root, text="Loose", width=6, command=lambda p=pin: send(p, "off")).grid(row=row, column=5, padx=(2, 8))

root.update()
ready[0] = True


sent = {}  # last angle set_servo sent to each socket


def set_servo(socket, a):
    s, pin, lo, hi = by_socket[socket]
    a = round(max(lo, min(hi, a)))
    if a != sent.get(socket):
        s.set(a)
        send(pin, a)
        sent[socket] = a


anim = [None]  # the running EyeAnim, or None


def eyes_tick():
    if anim[0] is None:
        return
    for socket, a in anim[0].step(time.monotonic()).items():
        set_servo(socket, a)
    root.after(20, eyes_tick)


def stop_eyes(rest=True):
    if anim[0] is None:
        return
    if rest:
        for socket, a in anim[0].rest().items():
            set_servo(socket, a)
    anim[0] = None
    alive_btn.config(text="EYES ALIVE")


def eyes_alive():
    if anim[0] is not None:
        stop_eyes()
        return
    if not POSES["open"]:
        status.config(text="Set the OPEN pose first: drag the four lid sliders open, then press Save lids OPEN.")
        return
    anim[0] = EyeAnim(POSES["shut"], POSES["open"], POSES["centre"], time.monotonic())
    sent.clear()
    alive_btn.config(text="STOP EYES")
    status.config(text="Eyes alive: looking around and blinking.")
    eyes_tick()


def save_pose(name, sockets):
    POSES[name] = {socket: by_socket[socket][0].get() for socket in sockets}
    write_poses()
    status.config(text=f"Saved {name.upper()}: " + ", ".join(f"{k} {v}" for k, v in POSES[name].items()))


def write_poses():
    with open(POSES_FILE, "w") as f:
        json.dump(POSES, f, indent=2)


# --- Brows: expressions and the idle layer (brow_anim.py) ---

brows = [None]   # the running BrowAnim, or None
show = [None]    # BROW SHOW's after() id while it runs, or None


def brow_travel():
    try:
        return float(raise_var.get()), float(lower_var.get())
    except ValueError:
        return RAISE, LOWER


def brows_running(t):
    """The BrowAnim, started from the saved LEVEL pose if it is not running yet."""
    if brows[0] is None:
        up, down = brow_travel()
        brows[0] = BrowAnim(POSES["level"], t, up, down, idle=alive_var.get())
        for socket in BROWS:
            sent.pop(socket, None)
        brow_tick()
    return brows[0]


def brow_tick():
    if brows[0] is None:
        return
    a = brows[0]
    a.raise_deg, a.lower_deg = brow_travel()
    a.idle = bool(alive_var.get())
    for socket, angle in a.step(time.monotonic()).items():
        set_servo(socket, angle)
    root.after(20, brow_tick)


def play_brows(name):
    t = time.monotonic()
    brows_running(t).play(name, t)
    status.config(text=f"Brows: {name}. If a brow goes the wrong way, flip its sign in brow_anim.DIR.")


def brows_alive():
    """BROWS ALIVE toggled: start the animation if it is not running (the idle flag is read each tick)."""
    brows_running(time.monotonic())
    status.config(text="Brows alive: small random movements on top of the expression." if alive_var.get()
                  else "Brows idle layer off.")


def brow_show(i=0):
    """Play every expression in turn, about 3 s each, then neutral."""
    if i >= len(ORDER):
        show[0] = None
        play_brows("neutral")
        return
    play_brows(ORDER[i])
    show_btn.config(text=f"SHOW: {ORDER[i]}")
    show[0] = root.after(3000, lambda: brow_show(i + 1))


def stop_brows(rest=True):
    if show[0] is not None:
        root.after_cancel(show[0])
        show[0] = None
    show_btn.config(text="BROW SHOW")
    if brows[0] is None:
        return
    if rest:
        for socket, a in brows[0].rest().items():
            set_servo(socket, a)
    brows[0] = None


def save_brow_level():
    stop_brows(rest=False)
    POSES["level"] = {socket: by_socket[socket][0].get() for socket in BROWS}
    up, down = brow_travel()
    POSES["brow_travel"] = {"raise": up, "lower": down}
    write_poses()
    status.config(text="Saved brows LEVEL: " + ", ".join(f"{k} {v}" for k, v in POSES["level"].items())
                  + f"; raise {up:g}, lower {down:g} deg")


def all_loose():
    stop_eyes(rest=False)
    stop_brows(rest=False)
    for _, pin, _ in sliders:
        send(pin, "off")


def neutral_face():
    stop_eyes(rest=False)
    stop_brows(rest=False)
    # one servo every 150 ms, so they don't all start at once on the supply
    for i, (s, pin, socket) in enumerate(sliders):
        a = neutral_angle(socket)
        root.after(150 * i, lambda s=s, pin=pin, a=a: (s.set(a), send(pin, a)))


def lid_dir(socket):
    """+1 or -1: which way a lid's slider goes to open it, from the saved poses (0 if they match)."""
    o, s = POSES["open"].get(socket, 90), POSES["shut"].get(socket, 90)
    return (o > s) - (o < s)


def eyes_open():
    """The saved OPEN pose with the eyes centred: eyes open, no blinking."""
    stop_eyes(rest=False)
    for i, (s, pin, socket) in enumerate(sliders):
        if socket in LIDS:
            a = POSES["open"].get(socket, 90)
        elif socket in GAZE:
            a = POSES["centre"].get(socket, 90)
        else:
            continue
        root.after(150 * i, lambda s=s, pin=pin, a=a: (s.set(a), send(pin, a)))
    status.config(text="Eyes open (the saved OPEN pose). LIDS WIDER pushes every lid 10 deg further; Lids OPEN saves it.")


def lids_wider(step=10):
    """Every lid `step` deg further open from where its slider is now (Loose a lid that buzzes)."""
    stop_eyes(rest=False)
    for i, (s, pin, socket) in enumerate(sliders):
        if socket not in LIDS:
            continue
        lo, hi = float(s.cget("from")), float(s.cget("to"))
        a = round(max(lo, min(hi, s.get() + step * lid_dir(socket))))
        root.after(150 * i, lambda s=s, pin=pin, a=a: (s.set(a), send(pin, a)))
    status.config(text="Lids 10 deg wider. A lid that buzzes without moving is at its stop: Loose it and move its horn.")


poses_row = tk.Frame(root)
poses_row.grid(row=len(SERVOS) + 1, column=0, columnspan=6, pady=(10, 0))
tk.Label(poses_row, text="Save the eye sliders as:", font=("Segoe UI", 10)).pack(side="left", padx=8)
tk.Button(poses_row, text="Lids SHUT", width=11, command=lambda: save_pose("shut", LIDS)).pack(side="left", padx=4)
tk.Button(poses_row, text="Lids OPEN", width=11, command=lambda: save_pose("open", LIDS)).pack(side="left", padx=4)
tk.Button(poses_row, text="Eyes CENTRE", width=11, command=lambda: save_pose("centre", GAZE)).pack(
    side="left", padx=4)

brows_row = tk.Frame(root)
brows_row.grid(row=len(SERVOS) + 2, column=0, columnspan=6, pady=(8, 0))
tk.Label(brows_row, text="Brows:", font=("Segoe UI", 10)).pack(side="left", padx=(8, 4))
for name in ORDER:
    tk.Button(brows_row, text=name, width=11, command=lambda n=name: play_brows(n)).pack(side="left", padx=2)

brows_row2 = tk.Frame(root)
brows_row2.grid(row=len(SERVOS) + 3, column=0, columnspan=6, pady=(4, 0))
alive_var = tk.IntVar(value=0)
tk.Checkbutton(brows_row2, text="BROWS ALIVE", font=("Segoe UI", 10, "bold"), variable=alive_var,
               command=brows_alive).pack(side="left", padx=8)
show_btn = tk.Button(brows_row2, text="BROW SHOW", width=18, command=lambda: brow_show(0))
show_btn.pack(side="left", padx=4)
tk.Button(brows_row2, text="furrow", width=7, command=lambda: play_brows("furrow")).pack(side="left", padx=2)
tk.Button(brows_row2, text="Brows LEVEL", width=11, command=lambda: stop_brows(rest=True)).pack(
    side="left", padx=4)
tk.Label(brows_row2, text="Raise deg:").pack(side="left", padx=(12, 2))
raise_var = tk.StringVar(value=f'{POSES["brow_travel"]["raise"]:g}')
tk.Spinbox(brows_row2, from_=0, to=90, increment=5, width=4, textvariable=raise_var).pack(side="left")
tk.Label(brows_row2, text="Lower deg:").pack(side="left", padx=(8, 2))
lower_var = tk.StringVar(value=f'{POSES["brow_travel"]["lower"]:g}')
tk.Spinbox(brows_row2, from_=0, to=90, increment=5, width=4, textvariable=lower_var).pack(side="left")
tk.Button(brows_row2, text="Save brows LEVEL", width=15, command=save_brow_level).pack(side="left", padx=(12, 8))

bottom = tk.Frame(root)
bottom.grid(row=len(SERVOS) + 4, column=0, columnspan=6, pady=10)
tk.Button(bottom, text="NEUTRAL FACE", font=("Segoe UI", 11, "bold"), bg="#c8e6c9", command=neutral_face).pack(
    side="left", padx=8)
alive_btn = tk.Button(bottom, text="EYES ALIVE", font=("Segoe UI", 11, "bold"), bg="#c5d8f0", width=12,
                      command=eyes_alive)
alive_btn.pack(side="left", padx=8)
tk.Button(bottom, text="EYES OPEN", font=("Segoe UI", 11, "bold"), bg="#fff3c4", command=eyes_open).pack(
    side="left", padx=8)
tk.Button(bottom, text="LIDS WIDER +10", font=("Segoe UI", 11, "bold"), bg="#ffe0b2", command=lids_wider).pack(
    side="left", padx=8)
tk.Button(bottom, text="ALL LOOSE", font=("Segoe UI", 11, "bold"), bg="#f4c7c3", command=all_loose).pack(
    side="left", padx=8)

status = tk.Label(root, text="", font=("Segoe UI", 10), fg="#444")
status.grid(row=len(SERVOS) + 5, column=0, columnspan=6, pady=(0, 8))


def close():
    all_loose()
    ser.close()
    root.destroy()


root.protocol("WM_DELETE_WINDOW", close)
root.mainloop()

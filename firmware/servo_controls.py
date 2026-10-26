"""
Slider window for testing the eye and brow servos by hand from the PC.

The Pico needs pico_servo_ctl.py saved as main.py. Run on the PC:
    uv run --no-project --with pyserial python firmware/servo_controls.py [COM9]

One slider per servo, labelled by part and by the mouth-board socket it plugs into
(eyes_brows_bench_test.py's layout). A servo stays loose until its slider is touched;
"Loose" lets it go again. Sides are as seen standing in front of the face.
"""

import sys
import time
import tkinter as tk

import serial

PORT = sys.argv[1] if len(sys.argv) > 1 else "COM9"

# (label, socket, GP pin)
SERVOS = [
    ("Both eyes: left / right", "LLL", 8),
    ("Both eyes: up / down", "LLR", 9),
    ("Eye on your RIGHT: top lid", "CUR", 11),
    ("Eye on your RIGHT: bottom lid", "CUL", 10),
    ("Eye on your LEFT: top lid", "CLR", 13),
    ("Eye on your LEFT: bottom lid", "CLL", 12),
    ("Brow on your LEFT: outer", "JL", 4),
    ("Brow on your RIGHT: outer", "JR", 5),
    ("Brow on your LEFT: inner", "LUL", 6),
    ("Brow on your RIGHT: inner", "LUR", 7),
]

ser = serial.Serial(PORT, 115200, timeout=0)
ser.write(b"\x03\x03")  # stop whatever runs
time.sleep(0.3)
ser.write(b"\x04")      # soft reset: main.py (pico_servo_ctl.py) starts
time.sleep(1.5)
ser.reset_input_buffer()


def send(pin, value):
    ser.write(f"{pin} {value}\n".encode())
    ser.reset_input_buffer()


ready = [False]  # Scale.set() fires the slider command; ignore it until the window is up


def slide(pin, value):
    if ready[0]:
        send(pin, value)


root = tk.Tk()
root.title("Eye and brow servos")
tk.Label(root, text="Drag a slider to move that servo. 90 = middle. Loose = no power to it.",
         font=("Segoe UI", 10)).grid(row=0, column=0, columnspan=5, pady=(8, 4))

sliders = []
for row, (label, socket, pin) in enumerate(SERVOS, start=1):
    tk.Label(root, text=label, font=("Segoe UI", 11), anchor="w", width=30).grid(row=row, column=0, padx=8)
    tk.Label(root, text=socket, font=("Segoe UI", 11, "bold"), width=5).grid(row=row, column=1)
    s = tk.Scale(root, from_=0, to=180, orient="horizontal", length=420, resolution=1,
                 command=lambda v, p=pin: slide(p, v))
    s.set(90)
    s.grid(row=row, column=2, padx=4)
    sliders.append((s, pin))

    def middle(s=s, p=pin):
        s.set(90)
        send(p, 90)

    tk.Button(root, text="90", width=4, command=middle).grid(row=row, column=3, padx=2)
    tk.Button(root, text="Loose", width=6, command=lambda p=pin: send(p, "off")).grid(row=row, column=4, padx=(2, 8))

root.update()
ready[0] = True


def all_loose():
    for _, pin in sliders:
        send(pin, "off")


tk.Button(root, text="ALL LOOSE", font=("Segoe UI", 11, "bold"), bg="#f4c7c3", command=all_loose).grid(
    row=len(SERVOS) + 1, column=0, columnspan=5, pady=10)


def close():
    all_loose()
    ser.close()
    root.destroy()


root.protocol("WM_DELETE_WINDOW", close)
root.mainloop()

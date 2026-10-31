# Firmware: two mouth boards run the head

Cogley's head uses three Raspberry Pi Pico boards (mouth, eyes, brows). The team has mouth boards only, and runs the head on two of them (the Head Power Wiring Build Guide, 2026-10-26):
- **Board 1, mouth**: 11 mouth servos, on the laptop's USB.
- **Board 2, eyes + brows**: the 6 eye servos and the 4 brow servos, reached from Board 1 over the link wires.

Board 2 runs `pico_servo_ctl.py` as `main.py`; Board 1 runs either that or TalkingHead's `cogley_mouth_main.py` (Lars's gliding version of Cogley's MouthMaster.py, found on the mouth board's Pico 2 on 2026-10-29 and kept in this folder with the link added). Both take lines `"<GP pin> <angle>"` over USB, and a line `"e <anything>"` is passed on over UART0 (GP16, 115200 baud) to the other board, which runs it as if it had come over USB (PLAN D28, 2026-10-29). So the laptop, plugged into Board 1, moves an eye servo with `e 8 90`. Each board still reads its own USB too, so two USB cables (one per board, no `e` prefix) work as well. Cogley's own programs are kept for reference (his eye and brow programs adapted to a mouth board: `eyes_mouthboard.py`, `brows_mouthboard.py`, PLAN D18); his `MouthMaster.py` and the 2-bit link they expect are not used, because the laptop needs every servo one by one.

## Where the servos plug in

Use the sockets by their pin. On a mouth board each socket is the one that mouth servo uses in `MouthMaster.py`. On Board 2 the eyes use these sockets and the brows the four jaw and upper-lip sockets (GP4 LO, GP5 RO, GP6 LI, GP7 RI; the bench layout below, which the slider window and `brow_anim.py` use):

| Pin | Mouth servo on that socket | Eyes board 2 | Brows board 3 |
|---|---|---|---|
| GP8 | LLL (lower lip, left) | LR: look left/right | LO: left brow, outer |
| GP9 | LLR (lower lip, right) | UD: look up/down | LI: left brow, inner |
| GP10 | CUL (upper corner, left) | BR: bottom-right lid | — |
| GP11 | CUR (upper corner, right) | TR: top-right lid | — |
| GP12 | CLL (lower corner, left) | BL: bottom-left lid | RO: right brow, outer |
| GP13 | CLR (lower corner, right) | TL: top-left lid | RI: right brow, inner |

## Bench test on one board

`eyes_brows_bench_test.py` runs the 6 eye servos and the 4 brow servos from one mouth board, one servo at a time, with no master board. The eyes use their usual sockets (GP8–GP13). The brows go on the free sockets instead:

| Pin | Mouth servo on that socket | Bench test |
|---|---|---|
| GP4 | JL (jaw, left) | LO: left brow, outer |
| GP5 | JR (jaw, right) | RO: right brow, outer |
| GP6 | LUL (upper lip, left) | LI: left brow, inner |
| GP7 | LUR (upper lip, right) | RI: right brow, inner |

Run it from Thonny without saving it as `main.py`. It centres every servo at 90, then `test_all()`, `wiggle()`, `sweep()`, `go()`, `center()` and `off()` work from the shell (commands listed at the top of the file).

**Sliders on the PC:** save `pico_servo_ctl.py` on the Pico as `main.py`, then run `uv run --no-project --with pyserial python firmware/servo_controls.py COM9` (use the Pico's port). On a Mac the Homebrew and venv Pythons have no tkinter, so use a uv-managed one: `uv run --no-project --managed-python --python 3.13 --with pyserial python firmware/servo_controls.py /dev/cu.usbmodemXXXX` (2026-10-29). A window opens with one slider per servo, named by part and socket. Every servo stays loose until its slider is touched; "Loose" and "ALL LOOSE" switch them off. "NEUTRAL FACE" sets the pose for fitting the skin: eyes centred and lids shut at the saved eye poses (below), brows level at 90.

**Eye poses and EYES ALIVE:** the row of save buttons stores the eye sliders as the lids' SHUT pose, the lids' OPEN pose or the eyes' CENTRE, in `firmware/eye_poses.json`. The defaults in `servo_controls.py` are the poses set by hand on 2026-10-29: shut CUR 186, CLR 112; open CUR 101, CLR 186 (matched by eye; CLR stalled buzzing at 196); the bottom lids hold CUL 182, CLL 86 in both; centre LLL 84, LLR 67. "EYES ALIVE" runs `eye_anim.py`: the eyes look around at random (small shifts, glances, returns to centre) and blink about 18 times a minute, with some double and slow blinks. Only the top lids blink; the bottom lids hold their OPEN angle (`MOVE_BOTTOM_LIDS` in `eye_anim.py`). The top lids rise when the eyes look up and drop when they look down. The lids only move between the saved SHUT and OPEN angles. The eyes open from shut when it starts, and "STOP EYES" puts them back to centre with the lids shut, as NEUTRAL FACE does. The look range, lid follow and blink timings are constants at the top of `eye_anim.py`. The file uses only `random`, so it can run on a Pico too.

**Brow expressions and BROWS ALIVE:** `brow_anim.py` plays the brow shapes of CHARACTER.md section 6 (neutral, curious, excited, skeptical, amused, concentrating, confused, irritated, surprised, vulnerable, greeting, plus a plain furrow) from the brows' LEVEL pose (90 each until "Save brows LEVEL" stores the brow sliders in `eye_poses.json`). A pose is a fraction per servo, +1 fully raised to -1 fully lowered, scaled by the "Raise deg" and "Lower deg" boxes (35 and 20 to start; Cogley's Brows.py uses 30 up and 10 down, which barely showed on the team's brows); the animation never goes past those two numbers, so set them with the sliders first and lower them if a bar hits anything. Which way each servo raises its end of the bar is `brow_anim.DIR`, taken from his Brows.py and not yet checked on the team's build: if a brow goes down on "curious", flip that servo's sign. An expression holds its last pose until the next one; "Brows LEVEL" brings them back. "BROWS ALIVE" adds small random brow movements on top (slow drifts, a quick flick of one brow, settling back); "BROW SHOW" plays every expression for 3 s each. The file uses only `random`, so it can run on a Pico too.

**Mouth sliders:** `mouth_controls.py` is the same kind of window for the mouth board's own servos, run the same way (`uv run --no-project --with pyserial python firmware/mouth_controls.py COM9`). The Pico keeps `pico_servo_ctl.py` as `main.py`; it now drives GP4–GP15, so copy it over again. The window also works with TalkingHead's `cogley_mouth_main.py` as `main.py`: it asks the board which program runs and sends that program's `set` commands, so no copying is needed between Bruce and the sliders (only one of them can hold the port at a time). With that program the board glides and clamps each servo, and only ALL LOOSE works. One slider per mouth servo, labelled by part and by its `MouthMaster.py` socket: JL GP4, JR GP5 (jaw), LUL GP6, LUR GP7 (upper lip), LLL GP8, LLR GP9 (lower lip), CUL GP10, CUR GP11 (upper corners), CLL GP12, CLR GP13 (lower corners), TON GP14 (tongue). Cogley's L and R are not yet matched to the sides of the face; Wiggle a servo to see which side it moves. Under the sliders is a table of his poses (mouth closed and open, lips rest, down and up, tongue down and up, corners narrow and wide, smile, frown) with the angles in use: GO eases the servos to the pose over 0.4 s, "SAVE sliders" stores the sliders as that pose in `firmware/mouth_poses.json`. Until a pose is saved its angles are Cogley's own from `MouthMaster.py`; they fit his horn positions, not necessarily ours, so go slowly near the ends of a slider and Loose a servo that buzzes. "REST FACE" is his start-up pose (mouth closed, tongue down, corners narrow) plus the lips at rest; "OPEN / CLOSE x3" chews between the saved OPEN and CLOSED. The file's keys are his pose names, so the numbers go straight into a copy of `MouthMaster.py`. The port `demo` opens the window without a Pico. Three more rows, Vowel AH (open), EE (wide) and OO (round), are the talking shapes for `frank/mouth.py`: GO shows the starting guess (made from his poses), shape the mouth on the sliders with the jaw at that vowel's opening, then SAVE; once all three are saved the talking blends between them.

**Pico 2:** the bench board's Pico is an RP2350 (Pico 2). It needs the RPI_PICO2 MicroPython build (v1.29.0 used), not the RP2040 `.uf2` from Cogley's folder.

## The link wires

Five jumpers from Board 1 to Board 2 on the Picos' outer header rows, pins 21-25 (GP16, GP17, GND, GP18, GP19), as the wiring guide says, with one change: **the GP16/GP17 pair must cross.** Board 1 sends on UART0 TX = GP16 (pin 21) and Board 2 listens on UART0 RX = GP17 (pin 22), so on Board 2 swap the yellow and green jumper ends (Board 1 pin 21 to Board 2 pin 22, Board 1 pin 22 to Board 2 pin 21). GND (pin 23) stays; GP18/GP19 are unused. A board only drives GP16 after its first `e` line over USB, so the board nobody talks to never drives the wire, and a straight 16-to-16 wire cannot put two outputs against each other; it just carries nothing. The link is one way: nothing comes back from Board 2, so the test is to send `e 8 90` and watch the eyes' left/right servo move. Both boards need a common ground (the one battery gives it).

Leave the small 4-pin CN1 and CN2 connectors and jumper H1 alone: with H1 fitted a cable between them would join the two Picos' 3.3 V rails.

## Flashing

1. MicroPython on each Pico. Board 1 is an RP2040 Pico (the RPI_PICO build); the bench board, now Board 2, is a Pico 2 (RP2350): it needs the RPI_PICO2 build (v1.29.0 used), not the RP2040 `.uf2` from Cogley's folder.
2. Copy the program as `main.py` over USB, one board at a time (the Mac's uv-managed Python has mpremote; on Windows Thonny does the same):

```
uv run --no-project --managed-python --python 3.13 --with mpremote mpremote connect /dev/cu.usbmodemXXXX fs cp firmware/pico_servo_ctl.py :main.py + reset
```

Cogley's programs (`eyes_mouthboard.py`, `brows_mouthboard.py`, his `MouthMaster.py`) also need his `servo` library on the Pico and use the GP28 switch (eyes: one position holds them centred; brows: closed runs a test sweep). `pico_servo_ctl.py` needs neither.

## Power

**Fit the BOARD POWER jumper on both boards.** It is the bare two-pin header by the Pico's USB end (the wiring guide's step 1.2). Without it the Pico is powered only by a USB cable: the servos still get 5 V, so the board looks alive and the eyes move whenever a laptop is plugged in, but the Pico is off the moment it is not, and the link does nothing (found 2026-10-29 after an evening of link tests). A cap, a wire wrapped round both pins or a solder bridge all do. The Pico's own LED (GP25) did not light on the eye board's Pico 2, so do not use it as a sign of life.


- Give each board 5 V through its XT60.
- An MG90S can draw about 0.7 A when stalled, and a board drives up to 10 servos. Cogley powers the whole head from 5 V 10 A.

**Source:** Cogley's α2.0.33 code (Patreon). The adapted copies are reference-derived; keep this repository private.

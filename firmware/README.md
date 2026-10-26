# Firmware: three mouth boards run the head

Cogley's head uses three Raspberry Pi Pico boards:
- one mouth board, the master
- one Eyes/Brow/Neck board for the eyes
- one Eyes/Brow/Neck board for the brows

The team has mouth boards only. A mouth board can stand in for each of the other two (PLAN D18): his eye and brow programs use servo pins that are also outputs on the mouth board (GP4–GP15). Only the mode switch pin differs.

| Board | Program | Comes from |
|---|---|---|
| Mouth board 1: mouth (master) | `MouthMaster.py` | his, unchanged (`inputs/reference/head_a2.0.33/Code/`) |
| Mouth board 2: eyes | `eyes_mouthboard.py` | his `eyes.py`, mode switch moved to GP28 |
| Mouth board 3: brows | `brows_mouthboard.py` | his `Brows.py`, mode switch moved to GP28 |

## Where the servos plug in

Use the sockets by their pin. On a mouth board each socket is the one that mouth servo uses in `MouthMaster.py`:

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

**Sliders on the PC:** save `pico_servo_ctl.py` on the Pico as `main.py`, then run `uv run --no-project --with pyserial python firmware/servo_controls.py COM9` (use the Pico's port). A window opens with one slider per servo, named by part and socket. Every servo stays loose until its slider is touched; "Loose" and "ALL LOOSE" switch them off.

**Pico 2:** the bench board's Pico is an RP2350 (Pico 2). It needs the RPI_PICO2 MicroPython build (v1.29.0 used), not the RP2040 `.uf2` from Cogley's folder.

## The link cables

The master tells the other two boards what to do over two wires each, through the small 4-pin connectors:
- **Eyes:** it drives GP16/GP17.
- **Brows:** it drives GP18/GP19.

Boards 2 and 3 both listen on their own GP16/GP17.

**Wiring:**
1. Run one cable from the master's eyes connector (GP16/17) to a connector on board 2.
2. Run one cable from the master's brows connector (GP18/19) to the same-numbered connector on board 3. It must land on GP16/17 there.
3. Before powering up, check each link with a multimeter (continuity). The connectors aren't labelled in the files we have.
4. All three boards need a common ground.

## Switch

Each board's mode switch is on GP28:
- **Eyes:** one position holds them centred (his calibration hold); flip it to run.
- **Brows:** switch open follows the master; switch closed runs a test sweep.

## Flashing

1. Install MicroPython on each Pico. Cogley's EyeMech GitHub has the `.uf2` in "Libraries and Software".
2. Copy his `servo` library onto it, from the same folder.
3. Save the board's program as `main.py` (Thonny makes this easy).

## Power

- Give each board 5 V through its XT60.
- An MG90S can draw about 0.7 A when stalled, and a board drives up to 10 servos. Cogley powers the whole head from 5 V 10 A.

**Source:** Cogley's α2.0.33 code (Patreon). The adapted copies are reference-derived; keep this repository private.

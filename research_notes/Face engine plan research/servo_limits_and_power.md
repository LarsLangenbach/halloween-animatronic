# Servo limits and power: protecting the head while getting the most out of it

2026-10-30. A companion to `animation_state_machines.md`. It covers how to find each servo's real limits, where those limits get enforced so nothing can overstep them, and how to stay inside the power budget without making Frank timid. Power figures come from the Head Power Wiring page (claude.ai, 2026-10-26); servo figures come from `docs/BOM.md` and the two board programs.

## The short version

- **Three things can get hurt.**
  - The servos: one pushing against a stop draws its stall current non-stop, heats up and strips or burns out.
  - The printed parts and the skin: a servo is stronger than a lid hinge.
  - The power chain: too many servos starting at once pulls the bus voltage down. The power bank can cut out and servos go weak or twitch.
- **Measure, don't guess.** One session with the bench supply (it shows current and can limit it), the slider windows and a phone in slow motion gives every servo's real end stops, its useful range, its speed under the skin and its holding current. Those numbers go into one file.
- **Enforce the numbers in four places**, so one bug can't break anything:
  1. printed stops;
  2. the board programs: hard caps per servo that no laptop command can get past, plus a speed limit;
  3. the laptop engine: smart limits, speed caps and a current budget;
  4. fuses and capacitors.
- **Best performance comes from the same measurements.** Once you know the real edge, you can run at about 90 % of it instead of half of it to be safe.

---

## 1. What can get hurt

| What | How it gets hurt | The sign |
|---|---|---|
| A servo | commanded past its end stop, or into the skin's limit, it pushes all the time at stall current (MG90S about 0.7 A measured, MG996R about 2–2.5 A). It heats up and the gears or motor wear out | a buzz or hum that doesn't stop; the servo warm to the touch |
| A servo | asked to move faster than it can, it runs at full power the whole way and overshoots | a clunk at the end of moves; current spikes |
| Printed parts, skin | a servo driven into a part that wasn't meant as a stop: a lid into the eyeball, the jaw shut too hard | a crack, a skin tear, a horn slipping on its spline |
| The bus | many servos starting a move in the same instant: each one draws close to stall current for a few milliseconds | the bus dips below 5 V; servos twitch; the power bank cuts out |
| The supply | a stall that goes on for seconds, on several servos | fuse F2 or F3 blows (it protects the wiring, not the servos) |
| Heat | 21 servos inside a closed skin inside a jar (PLAN R6) | servos too hot to hold after half an hour |

## 2. The power budget

| | Value | Source |
|---|---|---|
| Source | 20 V at up to 5 A = 100 W (the trigger can't ask for more than 20 V) | power page |
| Fuse F1 (20 V side) | 7.5 A | power page |
| Buck | 15 A continuous, 20 A peak, set to 5.30 V | power page |
| Fuses F2, F3 (one per board) | 10 A | power page |
| Bus capacitor C1 | 1000 µF, in the power box | power page |
| Voltage at the servos | 4.8–5.0 V, after the board's diode (SS1045) | power page |
| MG90S, stall | about 0.7 A (measured; vendor estimates go to 1.2–1.6 A at 6 V) | BOM |
| MG996R, stall | about 2.5 A at 6 V (TowerPro) | datasheet |

**Worst case if everything stalled at once:**

- Board 1: 2 MG996R × 2.5 A + 8 MG90S × 0.7 A (tongue off) = about 10.6 A, above its 10 A fuse.
- Board 2: 10 MG90S × 0.7 A = about 7 A.
- Together: about 17.6 A at 5.3 V = 93 W. Through the buck that is about 101 W at 20 V, right at the source's 100 W and above the buck's 15 A continuous.

**The normal case** is far lower. The power page estimates 3–8 A while talking, which fits easily.

So the supply is fine as long as nothing stalls for long and the big moves don't all start in the same instant. Both of those are the software's job. Fuses only save the wiring from a short. A 10 A fuse will happily feed a stalled servo for hours.

The servos also run at the bottom of their voltage range (4.8–5.0 V after the diode, against a rating of 4.8–6.0 V for the MG90S). Any dip under load takes them below it, which makes them slower and weaker and can make them twitch.

---

## 3. Problems already in the code

1. **Board 2 has no limits.** The eyes, lids and brows run on `pico_servo_ctl.py`, which accepts −27 … 207 degrees on every pin (200–2800 µs) and jumps there at once. That wide range was opened on purpose to find the left top lid's end (2026-10-29). But it means one wrong number from the laptop, a slider or a typo drives a lid or brow into its stop at full speed and holds it there. `cogley_mouth_main.py` on Board 1 already clamps every servo and glides; Board 2 needs the same.
2. **The two board programs mean different things by "degrees".**
   - `pico_servo_ctl.py` maps 0–180° to 500–2500 µs; `cogley_mouth_main.py` maps it to 544–2400 µs.
   - 90° is 1500 µs in one and 1472 µs in the other. Near the ends the gap grows to about 9°: 170° is 2389 µs in one and 2297 µs in the other.
   - So a limit or a pose found with one program is off with the other. The mouth poses can be saved under either program (`mouth_controls.py` talks to both).
   - Limits should be stored in microseconds, which is what the servo actually sees, or both programs should use one mapping.
3. **The jaw's "closed" pose is the most likely all-night stall.** If `mouth_closed` presses the lips or teeth together instead of just touching, both MG996Rs push against it whenever he isn't talking. `mouth.py` lets the jaw go after 3 s of silence, but only with `pico_servo_ctl.py`. With `cogley_mouth_main.py` the board holds its rest pose for as long as it runs.
4. **`mouth.py` asks for `speed 720`, but `cogley_mouth_main.py` caps `speed` at 600**, so the glide is quietly 600 deg/s. That is harmless, but the number in `mouth.GLIDE` is not what happens.
5. **The first pulse always jumps.** A servo doesn't know where it is. Its first pulse after power-up moves it at full speed from wherever the skin or a hand left it. `cogley_mouth_main.py` assumes 90 for everything at start.

---

## 4. Learning each servo's limits

### 4.1 Setup

- **Use the HANGELL bench supply instead of the power box.** It shows the current and has a current limit.
  - Set 5.30 V.
  - For one MG90S at a time, set the limit to 1.0 A; for the jaw pair, 3.0 A.
  - With that limit a stall during the test can't cook anything: the supply drops into current limiting and the servo goes weak.
- **The skin on, as it will run.** The skin decides most of the limits and nearly all of the holding load. Measure again whenever the skin changes (thickness, the Slacker mix, a new cast; PLAN R11).
- **One servo powered at a time.** Every other servo stays loose (no pulses), so the supply's current reading belongs to the servo under test. Note the board's own draw with everything loose first; that is the zero.
- The slider windows (`servo_controls.py` for Board 2, `mouth_controls.py` for Board 1), the multimeter, and a phone that films at 240 fps.

### 4.2 For every servo (about 5 minutes each)

1. **Rest and holding current.** Put the servo at its rest pose and wait 2 s. Read the current. Above the zero, that is the skin's pull at rest.
2. **Walk to each end, 1° at a time,** pausing on each step. Watch the current and listen:
   - the **useful end** is where another degree no longer changes the face (the skin is taut, or the part has stopped visibly moving);
   - the **stop** is where the current jumps and stays up (typically 0.3 A or more above holding) or the servo starts to buzz. Don't stay there more than a second or two.
3. **Set the limits:**
   - **hard cap:** 3° short of the stop (goes into the board programs);
   - **soft limit:** the useful end, or 2° short of the hard cap, whichever comes first (goes into the laptop engine).
   - Record them in microseconds as well as in the program's degrees.
4. **Holding current across the range,** at the soft limits and two points between. A high reading at one end means the skin fights the servo there, so the engine may visit that pose but shouldn't park there.
5. **Unpowered drift.** At rest, set it loose for 10 s and watch. If it stays within about 2°, it may be let go when idle (`relax_ok`). If it sags (lids or the jaw under the skin's pull), it has to keep holding.
6. **Direction.** Check that "up" is up (`brow_anim.DIR` is still Cogley's and unchecked; `eye_anim.UD_UP`).

### 4.3 Speed and latency

Film these servos in slow motion: one jaw MG996R, eye left/right, eye up/down, one top lid, one brow end and one corner. Servos of one type under similar load behave alike. For each:

- **Speed under load:** command a step from one soft limit to the other and count frames from the first movement to the stop (240 fps: one frame is 4.2 ms). Divide the angle by the time.
  - The engine's speed cap for that channel is about 85–90 % of this.
  - Commanding faster gains nothing: the servo can't follow, so it just runs flat out with the target ahead of it, drawing more current and overshooting.
- **Overshoot:** does it bounce at the end? If so, lower the cap or ease the end of moves.
- **Latency:** show something on the laptop screen in the same instant the command goes out, with the screen in the shot, and count frames until the servo starts moving. The engine leads the jaw by this much (open question in the engine design).
- **Smallest step:** the smallest command change that visibly moves it. This sets the smallest microsaccade and how finely slow drifts can step.

The datasheet's 0.1 s per 60° (600°/s, no load, 4.8 V) is the upper bound for an MG90S. Under the skin it will be slower.

### 4.4 Combined poses

Some limits only appear when two servos move together. Run the same kind of sweep as the CAD check, `pose_sweep.py`, on the real head:

- rest;
- each channel at both soft limits;
- the combined corners: eyes up + top lids open + brows up; eyes down + lids shut; jaw open + lips up + corners wide; and so on.

At each pose, watch for contact and for a current jump. Note the first pair that collides and what limits it (for example, "top lid open > 0.9 only while eyes UD > −5°"). These become coupled rules in the engine's safety layer.

### 4.5 Power-chain tests

On the real chain (bank or charger → trigger → buck → both boards):

1. **Worst plausible move:** a test clip that moves every servo from one soft limit to the other at its speed cap, all at once. Measure the bus at the board's XT60 with the multimeter on min/max if it has it. Pass: the bus stays at or above 5.0 V (the power page asks 5.1 V with everything moving), nothing resets and the bank stays on. Then run it again with the engine's staggering on and compare.
2. **Talking soak:** the power page's 30-minute runtime test, with Frank talking through the real engine. Afterwards touch every servo and the buck. Pass: warm, not too hot to hold (the MG90S is rated to 55 °C). Also note the air temperature inside the jar.
3. **Surge:** the power page's unplug-and-replug test, with the start-up sequence from 5.3.

### 4.6 The limits file

One file, read by everything that moves a servo: the engine, both slider windows and both board programs (copied to each Pico as `limits.json` when it's flashed).

```json
{
  "CLR": {
    "board": 2, "pin": 13, "part": "top lid, left eye",
    "stop_us": [1230, 2610],
    "hard_us": [1260, 2580],
    "soft_us": [1290, 2540],
    "rest_us": 1350,
    "speed_dps": 420,
    "hold_ma": {"1290": 40, "1900": 90, "2540": 210},
    "relax_ok": false,
    "measured": "2026-10-31", "skin": "FX-Pro cast 1"
  }
}
```

(The numbers are made up, to show the shape.) Tag it like `params.py`: every value is MEASURED with a date and the skin it was measured with, or ASSUMPTION until then. Per CLAUDE.md, the hard cap and the lower soft limit also go into the docs.

---

## 5. Enforcing the limits: four layers

Each layer assumes the one above it can fail.

### 5.1 Printed parts

- Where a mechanism can have a printed stop (the brows already do, from `brow_check.py`), the stop sits a little *outside* the hard cap. A runaway servo then meets plastic designed for it, not a lid hinge or the eyeball.
- The software limits are always inside the stop, so in normal running the servo never touches it.

### 5.2 The board programs (the last line, which the laptop can't bypass)

Both programs get the same protections:

- **A hard cap per pin** in microseconds, from `limits.json`. A command past it is cut to the cap and reported, as `cogley_mouth_main.py` already does with its `LIMITS`.
- **A speed limit per pin.** Even a garbage jump then moves at a safe speed. `cogley_mouth_main.py` glides already; `pico_servo_ctl.py` doesn't.
- **One mapping from degrees to microseconds**, or commands in microseconds, so a number means the same pulse on both boards.
- **A watchdog.** If no command arrives for a few seconds (the laptop crashed, the cable came out, Board 2's link dropped), glide slowly to the rest pose, then let go of the servos marked `relax_ok`.
- **A wide-range mode for calibration only.** The −27 … 207 range stays available behind an explicit command (for example `calibrate on`) that switches itself off after a minute. It is never the default.

### 5.3 The laptop engine (smart limits)

This is the output stage of the engine design, with these additions:

- **Soft limits** inside the hard caps, plus the coupled rules from 4.4.
- **Speed and acceleration caps** per channel from 4.3. They also stop the spring from asking for more than the servo can give.
- **A current budget.** Each tick, estimate each servo's current from the calibration:
  - holding current at its position (from `hold_ma`);
  - plus a moving share that grows with its speed;
  - plus a short bump when a move starts.

  Add them up per board and in total. If a tick's plan goes over budget, the engine doesn't clamp everything. It works through a priority list:
  1. delay the starts of low-priority moves by one or two ticks (20–40 ms, invisible);
  2. slow the idle drift;
  3. then the brows and corners;
  4. last of all the blink, the jaw and the gaze.

  Starting budgets, to be set from the tests in 4.5: about 6 A continuous for Board 1, 4 A for Board 2, 10 A in all, with short peaks allowed above that.
- **Staggered starts.** Even under budget, no more than about four servos start a large move in the same tick. A 10–20 ms spread can't be seen and cuts the dip on the bus.
- **A heat budget.** Each servo keeps a running total of its effort (current above zero over time) that slowly drains. If one fills up (the jaw in a long monologue, a lid parked at a high-load pose), the engine reduces that servo's amplitude a little or moves it to a lower-load pose until it drains. If the calibration is right this rarely happens. It is a safety net, not a style.
- **Letting go.** Servos marked `relax_ok` are let go when they've been still for a few seconds. That saves current, heat and hum. When they're needed again, the first command is the last angle they were holding, so they don't jump. The jaw should be let go after a few seconds of silence on either board program (problem 3).
- **Start-up and shutdown.**
  - On shutdown, glide every servo to its rest pose, save the angles to a file, then let go.
  - On start-up, send those saved angles one servo at a time about 100 ms apart, as `mouth.rest()` does now, then glide to rest.
  - That keeps the unavoidable first-pulse jump (problem 5) small and spread out.
- **Report it.** The engine posts its current estimate per board and any limit or budget it hit to the log and the web page. A limit hit on a servo that shouldn't be near its limit is a bug worth seeing.

### 5.4 Electrical

- Already in place: F1, F2, F3, 14 AWG leads, XT60 plugs, the 15 A buck and C1 on the bus.
- **Add a bulk capacitor at each board**, 1000–2200 µF 10–16 V, across the board's 5 V input (the 1000 µF 16 V capacitors already on hand will do; stripe to GND). C1 sits in the power box, at the far end of the XT60 lead. A capacitor at the board feeds the servos' start-up spikes from close by. First check whether Cogley's board already carries a large electrolytic near the XT60.
- Fuses protect the wiring. Protecting the servos from stalls is the software's job (5.2, 5.3).

### 5.5 Optional: measure the current live

An INA226 current-sense breakout (a few dollars, solder its header) in each board's 5 V lead, read by that board's Pico over I2C, would give the engine real board current instead of an estimate. It would also allow:

- **stall detection:** current high while nothing is moving means something is pushing; the engine can let suspects go one at a time and name the culprit in the log;
- **automatic calibration:** walk a servo towards its end until the current rises, the same idea as "sensorless homing" on 3D printers.

Board 1 can send readings back over USB. Board 2 can't yet, because the link is one way. Its GP16 is crossed to Board 1's GP17, so a return channel is possible once the crossed wiring is confirmed. This is not needed for Halloween; it is the upgrade if the estimates turn out to be poor.

---

## 6. Getting the best performance out of them

- **Use the measured edge, not a guess.** Range up to the useful end (no further, since past it there's only strain), speed at 85–90 % of the measured loaded speed. That is livelier than a cautious half-range and safer than the datasheet.
- **Spend the current where it shows.** Under budget pressure the blink, jaw and gaze keep full speed; idle drift gives way first.
- **Don't hold what doesn't need holding.** Every servo let go is current and heat saved for the ones that are moving.
- **Never ask for more speed than the servo has.** It looks the same, draws less and stops cleanly.
- **Finer steps for slow moves.** The board programs take fractional degrees (`pico_servo_ctl.py` parses a float), and the MG90S deadband is about 0.5°, so sending half degrees makes slow brow drifts smoother than whole degrees.
- **Keep the poses honest.** The jaw's "closed" should be just touching, and the lids' SHUT just closed. A pose that presses costs current all night.
- **Voltage, later and only with a reason.** The servos run at 4.8–5.0 V after the board's diode. Raising the buck would make them faster and stronger, since the MG90S is rated to 6 V and the MG996R to 7.2 V. It also means more current and more heat, and it changes the power design. Consider it only if the tests in 4.3 show servos too slow or too weak, and settle it in the power design first.

---

## 7. Order of work

1. **Board programs:** per-pin caps and speed limits on Board 2, one degree mapping on both, the watchdog and the calibration mode. Until this is done, keep Board 2's wide range for the slider window only.
2. **The calibration session** (4.1–4.4), about 2 hours for 19 servos with the skin on. Write `limits.json`.
3. **Flash the limits** onto both boards; make the slider windows read them too, so a slider can't pass a hard cap.
4. **Engine output stage** with soft limits, speed caps, staggering, letting go, start-up and shutdown.
5. **Power-chain tests** (4.5) with the engine; set the current budget from the results.
6. **Current budget and heat budget** in the engine.
7. Repeat steps 2–3 whenever the skin changes.

## 8. Open questions

- Does Cogley's board already carry a bulk capacitor at the servo rail?
- Which servos stay put when let go under the skin (4.2 step 5)?
- How hot does the jar get inside after an hour, with the head talking?
- Is a 2-hour calibration session with the skin on possible before the event, or should the first pass be done without the skin and repeated after?

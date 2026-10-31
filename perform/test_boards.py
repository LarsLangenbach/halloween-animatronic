"""
Offline tests for the board models and the body server's robot (no board, no network):
    python perform/test_boards.py [robots/frank/robot.json]
Last line: BOARDS OK, or BOARDS: n problem(s).
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import boards as B  # noqa: E402
from body import Robot  # noqa: E402

problems = []


def check(cond, what):
    if not cond:
        problems.append(what)


def run(board, secs):
    for _ in range(int(secs / 0.01)):
        board.tick(0.01)


# cogley_mouth: start-up pose, echo, clamps, glide, jaw, where, relax, link, reset
m = B.CogleyMouth(seed=1)
reply, fwd = m.line("where")
check(reply.startswith("Received: where") and "JL=90" in reply and "LUL=off" in reply and "TON=90" in reply,
      f"where at start: {reply!r}")
run(m, 1.0)
check(abs(m.j["TON"]["pos"] - 130) < 1e-6 and abs(m.j["CUR"]["pos"] - 80) < 1e-6, "REST glides TON to 130, CUR to 80")
reply, _ = m.line("set LUL 20")
check("past its limit; using 40" in reply, f"LUL clamps to 40: {reply!r}")
m.line("speed 600")
m.line("jaw 1")
run(m, 0.03)
check(90 < m.j["JL"]["pos"] < 130, "the jaw glides, it doesn't jump")
run(m, 0.5)
check(m.j["JL"]["pos"] == 130 and m.j["JR"]["pos"] == 50, "jaw 1 with JAW_DIR -1: JL 130, JR 50")
check(abs(m.pins[4]["us"] - (544 + 130 * (2400 - 544) / 180)) < 1e-6, "JL pulse on GP4 in his 544..2400 us map")
reply, fwd = m.line("e 8 120")
check(reply is None and fwd == "8 120", "e lines go on to the next board, no echo")
reply, _ = m.line("nonsense")
check(reply.endswith("Unknown command"), "unknown commands")
reply, _ = m.line("jaw x")
check("Error" in reply, "a bad number prints the error, as the board does")
m.line("relax")
check(not any(s["live"] for s in m.pins.values()), "relax: every servo loose")
m.where("JL=100 JR=off LUL=55")
check(m.j["JL"]["pos"] == 100 and not m.j["JR"]["live"] and m.j["LUL"]["pos"] == 55, "a real where reply is taken as true")
m.control(b"\x03")
check(m.line("jaw 1") == (None, None), "after Ctrl-C main.py is stopped")
check(m.control(b"\x04").startswith("Ready"), "Ctrl-D: the start-up line")
check(m.j["TON"]["live"] and m.j["JL"]["target"] == 90, "Ctrl-D: back to REST")
m.line("talk 0.7")
seen = set()
for _ in range(300):
    m.tick(0.01)
    seen.add(round(m.j["JL"]["target"]))
check(len(seen) > 2, "talk chatters the jaw")

# pico_servo_ctl: pins, off, clamp, link
p = B.PicoServoCtl()
check(not any(s["live"] for s in p.pins.values()), "pico: every servo loose at start")
p.line("8 90")
check(p.pins[8] == {"us": 1500.0, "live": True}, f"8 90 -> 1500 us: {p.pins[8]}")
p.line("9 300")
check(p.pins[9]["us"] == int(500 + 207 * 2000 / 180), "clamped to 207")
p.line("8 off")
check(not p.pins[8]["live"], "off")
check(p.line("e 8 90") == (None, "8 90"), "pico forwards e too")
check(p.line("3 90") == (None, None) and 3 not in p.pins, "pins outside GP4..15 ignored")

# the robot: a line to the mouth board reaches the eye board; servo speed limits the horn
robot = Robot(sys.argv[1] if len(sys.argv) > 1 else HERE.parent / "robots" / "frank" / "robot.json")
reply, reached = robot.feed("mouth", "e 11 183")
check(reached == [("mouth", "e 11 183"), ("eyes", "11 183")], f"e reaches the eye board: {reached}")
robot.tick(0.01)
f = robot.frame()
check(f["servos"]["TR"]["cmd"] == float(int(500 + 183 * 2000 / 180)), "TR (GP11) told 183")
robot.feed("mouth", "e 11 90")
robot.tick(0.05)
f = robot.frame()
deg_moved = (f["servos"]["TR"]["cmd"] - B.PicoServoCtl().pulse(183)) / (2000 / 180)
check(f["servos"]["TR"]["us"] > f["servos"]["TR"]["cmd"], "the horn lags the pulse (servo speed)")
check(robot.by_pin[("eyes", 11)] == "TR" and robot.by_pin[("mouth", 4)] == "JL", "servos by board and pin")

for x in problems:
    print("PROBLEM", x)
print(f"BOARDS: {len(problems)} problem(s)" if problems else "BOARDS OK")
sys.exit(1 if problems else 0)

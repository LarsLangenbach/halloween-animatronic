"""
Play a recorded performance (body.py --record FILE) back into the body server, with its timing:
onto the twin alone (body.py --sim) or onto the robot.

    uv run --no-project --with pyserial python perform/play.py FILE [--to socket://127.0.0.1:8811] [--speed 1.0]
        [--from SECONDS] [--board mouth] [--loop]

Lines go to the board they were sent to (a root board; the eye board's lines were sent to the
mouth board as "e ..." and are recorded that way). Ctrl-C stops; the servos hold where they are.
"""
import argparse
import json
import sys
import time


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("file")
    ap.add_argument("--to", default="socket://127.0.0.1:8811")
    ap.add_argument("--speed", type=float, default=1.0)
    ap.add_argument("--from", dest="start", type=float, default=0.0, help="skip the first SECONDS")
    ap.add_argument("--board", default=None, help="only the lines sent to this board")
    ap.add_argument("--loop", action="store_true")
    a = ap.parse_args()
    with open(a.file, encoding="utf-8") as f:
        rec = [json.loads(ln) for ln in f if ln.strip()]
    rec = [r for r in rec if a.board in (None, r["board"])]
    if not rec:
        sys.exit("nothing to play")
    t0 = rec[0]["t"] + a.start
    rec = [r for r in rec if r["t"] >= t0]
    import serial
    ser = serial.serial_for_url(a.to, 115200, timeout=0)
    print(f"playing {len(rec)} lines, {rec[-1]['t'] - t0:.1f} s, to {a.to}")
    try:
        while True:
            start = time.time()
            for r in rec:
                wait = (r["t"] - t0) / a.speed - (time.time() - start)
                if wait > 0:
                    time.sleep(wait)
                ser.write((r["line"] + "\n").encode())
                ser.reset_input_buffer()
            if not a.loop:
                break
    except KeyboardInterrupt:
        pass
    ser.close()


if __name__ == "__main__":
    main()

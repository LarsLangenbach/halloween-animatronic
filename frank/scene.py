"""
Frank's sense of the scene: now and then a snapshot goes to a vision model, which says
briefly what is there: costumes, what people hold and do, the room. eyes.py asks for one
when someone arrives, when Frank is set down somewhere new, and every so often, and turns
the answer into an "Observation:" note.

    uv run --no-project --with opencv-python --with anthropic python frank/scene.py photo.jpg

Snapshots are sent as JPEGs to the model's API and never saved. The sign at the jar has to
say that the camera's pictures go to an AI service. The key is ANTHROPIC_API_KEY in
frank/.env.
"""

import base64
import re
import sys
import threading
import time
from pathlib import Path

import cv2

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
import brain  # noqa: E402  (shares the key loading)

MODEL = "claude-haiku-5-5"  # fast, and only describes; Frank's own brain is chosen in brain.py
WIDTH = 1024                # snapshots are shrunk to this width

PROMPT = """You are the eyes of Frank, an animatronic head in a glass jar who talks with visitors. The picture is from a camera on top of his jar, looking out at the people in front of him. Left and right are Frank's: the left of the picture is his left.

Describe briefly what is clearly visible, for Frank to use in conversation:
- each person close to the camera: where they are, what they're wearing if it's worth remarking on (a costume, a mask, makeup, a striking hat), what they're holding, what they're doing;
- the surroundings: the room, the lighting and decorations, how busy it is, anything notable going on further back.

Never mention body shape or weight, attractiveness, skin colour, race or ethnicity, age, disability or health, and don't guess anyone's gender: say "a person". Never read out names from badges or lanyards, or text on anyone's screen or phone. Leave out anything you aren't sure of: omit a field rather than writing "unknown", "nothing" or "not visible". Keep every field under 15 words. Use the describe tool."""

TOOL = {
    "name": "describe",
    "description": "What Frank can see.",
    "input_schema": {
        "type": "object", "additionalProperties": False,
        "required": ["people", "surroundings", "new"],
        "properties": {
            "people": {"type": "array", "description": "People close to the camera, nearest first.",
                       "items": {"type": "object", "additionalProperties": False,
                                 "required": ["where"],
                                 "properties": {
                                     "where": {"type": "string", "description": "e.g. 'in front of you', 'on your left, further back'"},
                                     "wearing": {"type": "string"},
                                     "holding": {"type": "string"},
                                     "doing": {"type": "string"}}}},
            "surroundings": {"type": "string"},
            "new": {"type": "string",
                    "description": "What has changed since the previous description that's worth Frank noticing; empty if nothing."}}},
}


def jpeg(frame):
    h, w = frame.shape[:2]
    if w > WIDTH:
        frame = cv2.resize(frame, (WIDTH, round(h * WIDTH / w)), interpolation=cv2.INTER_AREA)
    return cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 80])[1].tobytes()


WHY = {"first": "your first look around", "arrival": "someone has just come up to you",
       "new place": "you've just been set down somewhere", "light": "your vision just came back",
       "look": "a regular look around"}


EMPTY = re.compile(r"<?\b(unknown|unclear|none|nothing|n/?a|not (clearly )?visible)\b>?", re.I)


def given(text):
    """A field's text, or "" if it's a placeholder for nothing."""
    text = (text or "").strip()
    return "" if not text or EMPTY.search(text) else text


def people_text(people):
    parts = []
    for p in people:
        wearing, holding = given(p.get("wearing")), given(p.get("holding"))
        bits = [wearing and f"wearing {wearing}", holding and f"holding {holding}", given(p.get("doing"))]
        bits = [b.strip() for b in bits if b and b.strip()]
        if bits:
            parts.append(f"{p['where']}, someone {', '.join(bits)}")
    return "; ".join(parts)


def note(seen, reason):
    """The "Observation:" note for a description, or None if there's nothing new to say."""
    people = people_text(seen.get("people", []))
    if reason in ("arrival", "new place", "first", "light"):
        text = ". ".join(t for t in (people, seen.get("surroundings", "").strip()) if t)
    else:
        text = seen.get("new", "").strip()
    return f"Observation: {text.rstrip('.')}." if text else None


class Describer:
    """Describes one snapshot at a time on its own thread, then calls on_result(reason,
    seen, note, seconds, error=None) from that thread. A request while one is running is
    dropped."""

    def __init__(self, on_result):
        import anthropic
        brain.load_env()
        self.client = anthropic.Anthropic(timeout=15.0, max_retries=1)
        self.on_result = on_result
        self.busy = False
        self.last, self.last_at = None, None

    def ask(self, frame, reason):
        if self.busy:
            return False
        self.busy = True
        threading.Thread(target=self._run, args=(jpeg(frame), reason), daemon=True).start()
        return True

    def describe(self, image, reason):
        text = f"Why you're looking now: {WHY.get(reason, reason)}."
        if self.last:
            text += (f"\nYour previous description, {time.time() - self.last_at:.0f} s ago: "
                     f"people: {people_text(self.last.get('people', [])) or 'nobody close'}; "
                     f"surroundings: {self.last.get('surroundings', '')}")
        msg = self.client.messages.create(
            model=MODEL, max_tokens=600, system=PROMPT, tools=[TOOL],
            tool_choice={"type": "tool", "name": "describe"},
            thinking={"type": "disabled"}, output_config={"effort": "low"},
            messages=[{"role": "user", "content": [
                {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg",
                                             "data": base64.b64encode(image).decode()}},
                {"type": "text", "text": text}]}])
        return next(b.input for b in msg.content if b.type == "tool_use")

    def _run(self, image, reason):
        t0 = time.time()
        try:
            seen = self.describe(image, reason)
            self.last, self.last_at = seen, time.time()
            self.on_result(reason, seen, note(seen, reason), time.time() - t0)
        except Exception as e:  # no network, say: he just doesn't get a description
            self.on_result(reason, None, None, time.time() - t0, error=f"{type(e).__name__}: {e}")
        finally:
            self.busy = False


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    done = threading.Event()

    def show(reason, seen, text, seconds, error=None):
        print(error or f"{seen}\n{text}\n({seconds:.1f} s)")
        done.set()

    frame = cv2.imread(sys.argv[1])
    if frame is None:
        sys.exit("usage: scene.py <image>")
    Describer(show).ask(frame, "first")
    done.wait(30)


if __name__ == "__main__":
    main()

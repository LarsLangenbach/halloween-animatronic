"""
Frank's eyes: the camera on top of his jar. Who is in front of him, who is talking, what
is around him, and what is happening to him (being picked up, his vision going dark), all
turned into context notes for the brain.

    uv run --no-project --with opencv-python --with mediapipe --with anthropic python frank/eyes.py
        a window shows what he sees (faces with names, match scores, distances and mouth
        movement, and whether he's being moved); his notes print in the terminal
    ... frank/eyes.py --enroll Anushhka --creator    store a creator's face: one person in view,
                                                     looking at the camera, turning a little
    ... frank/eyes.py --cameras                      which camera number is which
    ... frank/eyes.py --video clip.mp4               a recorded clip instead of the camera
    ... frank/eyes.py --no-scene                     no snapshots to the vision model

chat.py --see runs it in a process of its own (Eyes), so camera work never holds up the
audio. camera.json says which camera, its field of view and where it sits relative to
Frank's eyes. For every frame:
- Self-motion. Corners are followed across the whole picture. When they all move together,
  the camera, and so the jar, is moving; a person walking past moves only part of it. Once
  he has been still for a few seconds, the view is compared with the one from before he
  moved: the same place, or somewhere new.
- Sight. A black or blank picture means something covers the camera or the lights are off.
- Faces (faces.py). Each face is followed from frame to frame, given a distance from its
  size, and fingerprinted a few times a second until it is recognised. Someone is engaged
  once they are within ENGAGE_M and have faced him for ENGAGE_S; people further back are
  only counted. The first engaged person starts a session; SESSION_GAP_S with nobody
  engaged ends it.
- Mouths. MediaPipe's face landmarker measures how open each nearby mouth is. The face
  whose mouth moved most while someone talked is the speaker.
- The scene (scene.py). Now and then, and when someone arrives or he is set down somewhere
  new, a snapshot goes to a vision model for a short description: costumes, what people
  hold and do, the room. On an arrival he waits for it (up to STUDY_S) before reacting, so
  he studies a newcomer before greeting them.

Events are dicts: kind, notes (context notes for the brain) and prompt (react now, though
nobody spoke). Strangers' fingerprints stay in this process and are dropped when the
session ends; only the creators and visitors who said yes are stored (faces.py).
"""

import argparse
import json
import math
import queue
import sys
import threading
import time
from collections import deque
from pathlib import Path

import cv2
import numpy as np

try:
    cv2.utils.logging.setLogLevel(cv2.utils.logging.LOG_LEVEL_ERROR)
except AttributeError:
    pass

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
import faces  # noqa: E402

CONFIG = HERE / "camera.json"
DEFAULTS = dict(source=0, width=1920, height=1080, hfov_deg=78.0, mirrored=False,
                face_width_m=0.16, offset_mm=[0.0, 0.0, 250.0], tilt_deg=10.0)

# Presence
ENGAGE_M = 2.0       # within this distance and facing him ...
ENGAGE_S = 0.5       # ... for this long: someone has come to see him
LEAVE_M = 2.8        # an engaged person further than this for 2 s has left ...
LEAVE_S = 3.0        # ... and so has one out of sight this long
SESSION_GAP_S = 20.0  # nobody engaged this long: the conversation is over
FACING = 0.35        # nose offset from between the eyes, in eye spacings (about 30°): looking his way
STUDY_S = 1.5        # an arrival waits this long for the scene description (2.5 s if it had to queue)
# Faces
PRINT_PX = 60        # faces narrower than this aren't fingerprinted
PRINT_EVERY = 0.12   # s between fingerprints of a face until it is recognised (7 ms each) ...
PRINT_KNOWN = 2.0    # ... and after
ENROLL_Q = 0.6       # quality a fingerprint needs to be stored
ENROLL_MIN = 4       # stored fingerprints needed to remember someone
ENROLL_PX = 100      # eyes.py --enroll wants a face at least this wide (about 1.9 m at 1080p) ...
ENROLL_LEAD = 1.5    # ... and this many times wider than any other face in view: clearly the one
# Mouths
MOUTH_M = 3.0        # mouths are measured on the 4 nearest faces closer than this
MOUTH_ACTIVE = 0.1   # jawOpen change per second while talking. Real mouths at 0.4 m read 0.05-0.26 on
                     # lines that were real (2026-10-28); 0.4, from made-up test faces, dropped them all
MOUTH_STILL = 0.05   # ... and below this for MOUTH_STILL_S the speaker has stopped
MOUTH_STILL_S = 0.3
MOUTH_NEAR_M = 2.5   # whose mouths are checked for a line: everyone this close, engaged or not
OVERLAP_ACTIVE = 0.5  # a second mouth counts as talking over the first only above this and at
                      # least half the first (0.2 next to 0.85 was "two people talking", 2026-10-28)
MOUTH_EVIDENCE = 8   # mouth samples a face needs within a line before "still" means anything ...
TRACK_SETTLED_S = 1.0  # ... and the face must have been followed this long (a face that keeps
                       # being lost, 2026-10-28, had readings of 0.0 and dropped every real line)
ARRIVE_PROMPT_S = 15  # he reacts to a new arrival at most this often
FIGURE_S = 20        # a face that hasn't moved at all for this long is a figure (a printed head, a
FIGURE_DRIFT = 0.004  # poster), not a person: box drift under this share of the frame width (8 px) ...
FIGURE_MOUTH = 0.02   # ... and jawOpen range under this. People fidget, blink and breathe.
MOUTH_WINDOW = 0.6   # a line counts the busiest stretch of this long, so pauses don't dilute it
PERSON_CLOSE = 0.15  # people fill this much of the picture: someone is right there, even masked
# Self-motion and sight
MOVE_SHIFT = 0.06    # background shift per second, as a fraction of the width (about 5°/s) ...
MOVE_ROT = 3.0       # ... or rotation, degrees per second: the camera is moving ...
MOVE_HOLD_S = 0.8    # ... in 70 % of the frames for this long
BACKGROUND_MIN = 0.5  # less of the picture than this is background: can't tell, so say nothing
BLIND_LIGHT = 20     # mean brightness (0-255) below which he can't see ...
BLIND_DETAIL = 6.0   # ... or picture detail (variance of the Laplacian) below this: covered
SETTLE_S = 3.0       # still this long after a move before he's "set down"
PROMPT_GAP_S = 30    # reactions to being moved or blinded at most this often
SCENE_EVERY_S = 40   # a fresh scene description while someone is there ...
SCENE_IDLE_S = 150   # ... and while nobody is


def load_config():
    cfg = dict(DEFAULTS)
    if CONFIG.exists():
        cfg.update(json.loads(CONFIG.read_text(encoding="utf-8")))
    return cfg


def event(kind, notes=(), prompt=False, **extra):
    return dict(kind=kind, notes=[n for n in notes if n], prompt=prompt, t=time.time(), **extra)


def iou(a, b):
    ax, ay, aw, ah = a[:4]
    bx, by, bw, bh = b[:4]
    w = min(ax + aw, bx + bw) - max(ax, bx)
    h = min(ay + ah, by + bh) - max(ay, by)
    inter = max(0.0, w) * max(0.0, h)
    return inter / (aw * ah + bw * bh - inter + 1e-9)


class Camera:
    """The newest frame from a camera, or from a video file played at its own speed, read
    on a thread of its own. A camera that stops sending is reopened every 2 s."""

    def __init__(self, source, width=1920, height=1080):
        self.source, self.size = source, (width, height)
        self.file = not isinstance(source, int)
        self.cap = self._open()
        if not self.cap.isOpened():
            hint = "" if self.file else (": allow the app running this under System Settings > "
                                         "Privacy & Security > Camera, and check eyes.py --cameras")
            raise SystemExit(f"can't open camera {source}{hint}")
        self.period = 1 / (self.cap.get(cv2.CAP_PROP_FPS) or 30) if self.file else 0
        self.frame, self.t, self.seq = None, 0.0, 0
        self.ended = self.stopped = False
        self.cv = threading.Condition()
        threading.Thread(target=self._run, daemon=True).start()

    def _open(self):
        if self.file:
            return cv2.VideoCapture(str(self.source))
        cap = cv2.VideoCapture(self.source, cv2.CAP_AVFOUNDATION if sys.platform == "darwin" else cv2.CAP_ANY)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.size[0])
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.size[1])
        cap.set(cv2.CAP_PROP_FPS, 30)
        return cap

    def _run(self):
        due, failing = time.time(), None
        while not self.stopped:
            ok, frame = self.cap.read()
            if not ok:
                if self.file:
                    break
                failing = failing or time.time()
                if time.time() - failing > 2:
                    self.cap.release()
                    self.cap, failing = self._open(), time.time()
                time.sleep(0.02)
                continue
            failing = None
            if self.file:
                due += self.period
                time.sleep(max(0.0, due - time.time()))
            with self.cv:
                self.frame, self.t, self.seq = frame, time.time(), self.seq + 1
                self.cv.notify_all()
        self.cap.release()
        with self.cv:
            self.ended = True
            self.cv.notify_all()

    def read(self, after, timeout=2.0):
        """(seq, time, frame) for the first frame newer than seq `after`, or None."""
        with self.cv:
            self.cv.wait_for(lambda: self.seq > after or self.ended, timeout)
            return (self.seq, self.t, self.frame) if self.seq > after else None

    def stop(self):
        self.stopped = True


class Geometry:
    """Where a face is relative to Frank, from where it is in the picture. Directions are
    from the midpoint between his eyes in the head frame (PLAN §4): yaw + to his left,
    pitch + up."""

    def __init__(self, cfg, width, height):
        self.cx, self.cy = width / 2, height / 2
        self.f = self.cx / math.tan(math.radians(cfg["hfov_deg"]) / 2)  # focal length, px
        self.face_w = cfg["face_width_m"]
        self.offset = np.array(cfg["offset_mm"], float) / 1000
        self.tilt = math.radians(cfg["tilt_deg"])
        self.mirror = -1 if cfg["mirrored"] else 1

    def locate(self, face):
        """(distance m, yaw deg, pitch deg)."""
        x, y, w, h = face[:4]
        dist = self.f * self.face_w / max(w, 1.0)
        ray = np.array([self.mirror * (x + w / 2 - self.cx), y + h / 2 - self.cy, self.f])
        right, down, fwd = ray / np.linalg.norm(ray) * dist  # camera axes
        c, s = math.cos(self.tilt), math.sin(self.tilt)       # the camera looks down by tilt
        fwd, down = fwd * c - down * s, fwd * s + down * c
        # The picture's left is the camera's left, which is Frank's left (+x).
        px, py, pz = np.array([-right, fwd, -down]) + self.offset
        return dist, math.degrees(math.atan2(px, py)), math.degrees(math.atan2(pz, math.hypot(px, py)))


class Track:
    """One face followed from frame to frame."""

    def __init__(self, tid, face, t):
        self.id, self.face, self.first, self.seen = tid, face, t, t
        self.prints = deque(maxlen=60)   # (time, fingerprint, quality)
        self.mouth = deque(maxlen=400)   # (time, jawOpen)
        self.who = (None, None, 0.0)     # faces.identify(): level, person id, score
        self.stranger = None             # a number, for the preview
        self.engaged = False
        self.facing_since = self.far_since = self.gone_at = None
        self.last_print = 0.0
        self.dist, self.yaw, self.pitch, self.turn = 9.0, 0.0, 0.0, 0.0
        self.boxes = deque(maxlen=400)  # (time, cx, cy, w) for the figure check
        self.figure = False             # ruled not a person

    def mean_print(self):
        if not self.prints:
            return None
        m = np.mean([p for _, p, _ in list(self.prints)[-8:]], axis=0)
        return m / np.linalg.norm(m)

    def mouth_peak(self, t0, t1, window=MOUTH_WINDOW):
        """The most the mouth moved in any stretch of `window` s between t0 and t1 (jawOpen
        change per second), or None if it wasn't seen. A line's pauses and the wait for the
        end of the turn don't water it down."""
        pts = [(t, v) for t, v in self.mouth if t0 <= t <= t1]
        best = None
        for i, (ti, _) in enumerate(pts):
            seg = [v for t, v in pts[i:] if t - ti <= window]
            span = max(t for t, _ in pts[i:i + len(seg)]) - ti
            if len(seg) >= 4 and span >= 0.3:
                act = float(np.abs(np.diff(seg)).sum() / span)
                best = act if best is None else max(best, act)
        return best


class Mouths:
    """How open a mouth is (MediaPipe's jawOpen, 0 to 1) and how far the head is turned,
    from a crop around the face. Its turn holds steady down to small faces, where YuNet's
    five points don't (0.27-0.29 for one face 65-220 px wide, against YuNet's 0.22-0.41)."""

    def __init__(self):
        import mediapipe as mp
        from mediapipe.tasks.python import BaseOptions, vision
        self.mp = mp
        self.lm = vision.FaceLandmarker.create_from_options(vision.FaceLandmarkerOptions(
            base_options=BaseOptions(model_asset_path=faces.model("face_landmarker.task")),
            running_mode=vision.RunningMode.IMAGE, num_faces=1, output_face_blendshapes=True))

    def measure(self, frame, face):
        """(jawOpen, turn) or None; turn is YuNet's measure: nose offset from between the
        eyes, in eye spacings."""
        x, y, w, h = face[:4]
        half = 0.8 * max(w, h)
        cx, cy = x + w / 2, y + h / 2
        H, W = frame.shape[:2]
        x0, y0 = int(max(0, cx - half)), int(max(0, cy - half))
        x1, y1 = int(min(W, cx + half)), int(min(H, cy + half))
        if x1 - x0 < 20 or y1 - y0 < 20:
            return None
        crop = cv2.cvtColor(cv2.resize(frame[y0:y1, x0:x1], (256, 256)), cv2.COLOR_BGR2RGB)
        r = self.lm.detect(self.mp.Image(image_format=self.mp.ImageFormat.SRGB,
                                         data=np.ascontiguousarray(crop)))
        if not r.face_blendshapes:
            return None
        jaw = next((c.score for c in r.face_blendshapes[0] if c.category_name == "jawOpen"), 0.0)
        L = r.face_landmarks[0]
        right, left = (L[33].x + L[133].x) / 2, (L[263].x + L[362].x) / 2  # eye centres, from the corners
        return jaw, (L[1].x - (right + left) / 2) / ((left - right) or 1e-6)


class Bodies:
    """Which pixels are people (MediaPipe's selfie segmenter). Self-motion is judged only from
    the rest, and someone close counts as there even when no face is found (a mask)."""

    def __init__(self):
        import mediapipe as mp
        from mediapipe.tasks.python import BaseOptions, vision
        self.mp = mp
        self.seg = vision.ImageSegmenter.create_from_options(vision.ImageSegmenterOptions(
            base_options=BaseOptions(model_asset_path=faces.model("selfie_segmenter_landscape.tflite")),
            running_mode=vision.RunningMode.IMAGE, output_confidence_masks=True))

    def mask(self, small):
        """255 where a person is, at small's size (a BGR frame)."""
        rgb = cv2.cvtColor(small, cv2.COLOR_BGR2RGB)
        r = self.seg.segment(self.mp.Image(image_format=self.mp.ImageFormat.SRGB, data=np.ascontiguousarray(rgb)))
        conf = r.confidence_masks[0].numpy_view()
        if conf.shape[:2] != small.shape[:2]:
            conf = cv2.resize(conf, (small.shape[1], small.shape[0]))
        return (conf > 0.5).astype(np.uint8) * 255


class SelfMotion:
    """Whether the camera itself is moving, from how corners in the background (people cut
    out) move across the picture, and whether he ends up where he was."""

    def __init__(self):
        self.prev, self.prev_t = None, None
        self.hist = deque()   # (time, moved this frame)
        self.views = deque()  # (time, view) while still, to remember the view before a move
        self.moving, self.since, self.before = False, 0.0, None
        self.background = 1.0  # how much of the picture the last judgement could use
        self.orb = cv2.ORB_create(800)
        self.match = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)

    def update(self, gray, view, t, boxes, people=None):
        """gray: a 320-wide frame; view: a 640-wide one; boxes: faces and people: a mask of
        people (Bodies), both in gray's pixels. Returns "moved", "still" or None."""
        dt, self.prev_t = (t - self.prev_t if self.prev_t else 1 / 15), t
        moved = self._moved(gray, boxes, max(dt, 1e-3), people)
        self.hist.append((t, moved))
        while self.hist and self.hist[0][0] < t - 2:
            self.hist.popleft()
        if not self.moving:
            if not self.views or t - self.views[-1][0] >= 0.25:
                self.views.append((t, view))
                while self.views and self.views[0][0] < t - 2.5:
                    self.views.popleft()
            recent = [m for tt, m in self.hist if tt > t - MOVE_HOLD_S]
            if len(recent) >= 6 and sum(recent) >= 0.7 * len(recent):
                self.moving, self.since = True, t
                # The view from before: motion is only believed after MOVE_HOLD_S of it.
                self.before = next((v for tt, v in reversed(self.views) if tt <= t - MOVE_HOLD_S - 0.5),
                                   self.views[0][1] if self.views else None)
                self.views.clear()
                return "moved"
        elif t - self.since > 1.0 and not any(m for tt, m in self.hist if tt > t - 1.5):
            self.moving = False
            return "still"
        return None

    def _moved(self, gray, boxes, dt, people=None):
        prev, self.prev = self.prev, gray
        if prev is None:
            return False
        h, w = gray.shape
        # People move about; the room doesn't. Judge only the room: people cut out (with a
        # margin), and a box below each face for bodies the segmenter missed.
        mask = (cv2.bitwise_not(cv2.dilate(people, np.ones((9, 9), np.uint8))) if people is not None
                else np.full_like(gray, 255))
        for x, y, bw, bh in boxes:
            mask[max(0, int(y - 0.3 * bh)):, max(0, int(x - 0.5 * bw)):max(0, int(x + 1.5 * bw))] = 0
        self.background = float(mask.mean()) / 255
        if self.background < BACKGROUND_MIN:
            return False  # someone fills the picture (pulling on a sweater, up close): can't tell
        room = mask > 0
        diff = float(cv2.absdiff(prev, gray)[room].mean())
        pts = cv2.goodFeaturesToTrack(prev, 200, 0.01, 7, mask=mask)
        if pts is None or len(pts) < 20:
            return diff > 25 and self.background > 0.6  # a blank view: only a big change counts
        nxt, st, _ = cv2.calcOpticalFlowPyrLK(prev, gray, pts, None, winSize=(21, 21), maxLevel=3)
        ok = st.ravel() == 1
        if ok.sum() < 0.3 * len(pts):
            return diff > 15 and self.background > 0.6  # most corners lost: a fast swing blurs everything
        a, b = pts[ok].reshape(-1, 2), nxt[ok].reshape(-1, 2)
        M, inliers = cv2.estimateAffinePartial2D(a, b, method=cv2.RANSAC, ransacReprojThreshold=1.5)
        if M is None:
            return False
        inliers = inliers.ravel().astype(bool)
        if inliers.sum() < max(15, 0.5 * len(a)):
            return False  # no single motion: things moving about in the room
        p = a[inliers]
        if np.ptp(p[:, 0]) < 0.4 * w or np.ptp(p[:, 1]) < 0.3 * h:
            return False  # only one patch of the picture moved
        shift = math.hypot(M[0, 2], M[1, 2]) / w
        rot = abs(math.degrees(math.atan2(M[1, 0], M[0, 0])))
        zoom = abs(math.hypot(M[0, 0], M[1, 0]) - 1)
        return shift / dt > MOVE_SHIFT or rot / dt > MOVE_ROT or zoom / dt > 0.15

    def same_place(self, before, view):
        """Whether view shows the same place as before (None: can't tell)."""
        if before is None:
            return None
        k1, d1 = self.orb.detectAndCompute(before, None)
        k2, d2 = self.orb.detectAndCompute(view, None)
        if d1 is None or d2 is None or len(k1) < 30 or len(k2) < 30:
            return None
        m = self.match.match(d1, d2)
        if len(m) < 20:
            return False
        src = np.float32([k1[x.queryIdx].pt for x in m])
        dst = np.float32([k2[x.trainIdx].pt for x in m])
        H, inliers = cv2.findHomography(src, dst, cv2.RANSAC, 5.0)
        return H is not None and int(inliers.sum()) >= max(20, 0.25 * len(m))


class Sight:
    """Whether he can see at all: a black or blank picture means the camera is covered or
    the lights are off."""

    def __init__(self):
        self.blind, self.since, self.light, self.detail = False, None, 0.0, 0.0

    def update(self, gray, t):
        self.light = float(gray.mean())
        self.detail = float(cv2.Laplacian(gray, cv2.CV_64F).var())
        bad = self.light < BLIND_LIGHT or self.detail < BLIND_DETAIL
        if bad == self.blind:
            self.since = None
            return None
        self.since = self.since or t
        if t - self.since >= (1.0 if bad else 0.5):
            self.blind, self.since = bad, None
            return "dark" if bad else "light"
        return None


class Vision:
    """The whole pipeline, fed one frame at a time (step). emit(event) gets the events."""

    def __init__(self, cfg, emit, scene=True, gallery=None):
        self.cfg, self.emit = cfg, emit
        self.rec = faces.Recogniser()
        self.gallery = gallery or faces.Gallery()
        self.mouths, self.bodies = Mouths(), Bodies()
        self.motion, self.sight = SelfMotion(), Sight()
        self.people_share = 0.0  # how much of the picture is people (smoothed)
        self.geo = self.frame = None
        self.tracks, self.limbo = {}, {}  # live; engaged but out of sight (for LEAVE_S)
        self.next_id = self.next_stranger = 1
        self.session, self.empty_since, self.arrival = False, None, None
        self.paused_at = None      # last time faces were not watched (moving or blind)
        self.settle_at = None      # when a move counts as over
        self.handled_until = 0.0   # a move before this continues the last one
        self.close_before_move, self.view_before = [], None
        self.last_prompt, self.refreshed, self.far = {}, 0.0, 0
        self.recent_notes = deque(maxlen=4)
        self.scene_q = queue.Queue()
        self.describer = None
        if scene:
            import scene as scene_mod
            self.describer = scene_mod.Describer(lambda *a, **k: self.scene_q.put((a, k)))
        self.scene_next = time.time() + 2
        self.scene_error = None
        self.enrolling = None  # start_enrol's collection under way
        self.pending_arrivals = []  # (track id, deadline): mid-session arrivals waiting for recognition

    # ----- one frame -----

    def step(self, frame, t):
        h, w = frame.shape[:2]
        if self.geo is None:
            self.geo = Geometry(self.cfg, w, h)
        self.frame = frame
        small = cv2.resize(frame, (320, round(320 * h / w)), interpolation=cv2.INTER_AREA)
        gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
        change = self.sight.update(gray, t)
        if change:
            self._sight_changed(change, t)
        dets = [] if self.sight.blind else self.rec.detect(frame)
        if not self.sight.blind:
            view = cv2.cvtColor(cv2.resize(frame, (640, round(640 * h / w)), interpolation=cv2.INTER_AREA),
                                cv2.COLOR_BGR2GRAY)
            people = self.bodies.mask(small)
            self.people_share = 0.7 * self.people_share + 0.3 * float(people.mean()) / 255
            change = self.motion.update(gray, view, t, [d[:4] * (320 / w) for d in dets], people)
            if change:
                self._motion_changed(change, t)
            if self.settle_at and t >= self.settle_at:
                self._settled(view, t)
        if self.motion.moving or self.sight.blind:
            self.paused_at = t
        else:
            self._faces(frame, dets, t)
            self._presence(t)
            if self.enrolling:
                self._enrol_step(frame, t)
        self._scene(t)
        if t - self.refreshed > 2:
            self.gallery.refresh()  # faces.py forget, run while he's watching
            self.refreshed = t

    def _emit(self, kind, notes=(), prompt=False, t=None, **extra):
        if prompt and kind in ("moved", "still", "dark", "arrived"):  # these can flicker
            last = self.last_prompt.get(kind, -1e9)
            prompt = (t or time.time()) - last >= (ARRIVE_PROMPT_S if kind == "arrived" else PROMPT_GAP_S)
            if prompt:
                self.last_prompt[kind] = t or time.time()
        ev = event(kind, notes, prompt, **extra)
        self.recent_notes.extend(ev["notes"])
        self.emit(ev)

    # ----- faces -----

    def _faces(self, frame, dets, t):
        live = list(self.tracks.values())
        pairs = sorted(((iou(tr.face, d), i, j) for i, tr in enumerate(live) for j, d in enumerate(dets)),
                       key=lambda x: -x[0])
        used_t, used_d = set(), set()
        for o, i, j in pairs:
            if o < 0.25:
                break
            if i in used_t or j in used_d:
                continue
            used_t.add(i)
            used_d.add(j)
            live[i].face, live[i].seen = dets[j], t
        for j, d in enumerate(dets):
            if j not in used_d:
                self._new_track(d, t)
        for tr in live:
            if tr.seen < t - 0.5:  # out of sight
                del self.tracks[tr.id]
                if tr.engaged:
                    tr.gone_at = tr.seen
                    self.limbo[tr.id] = tr
        for tr in self.tracks.values():
            if tr.seen != t:
                continue
            f = tr.face
            tr.dist, tr.yaw, tr.pitch = self.geo.locate(f)
            tr.boxes.append((t, f[0] + f[2] / 2, f[1] + f[3] / 2, f[2]))
            self._figure_check(tr, t, frame.shape[1])
            eye_gap = math.hypot(f[6] - f[4], f[7] - f[5]) or 1.0
            tr.turn = (f[8] - (f[4] + f[6]) / 2) / eye_gap  # replaced by the landmarker's, close up
        for tr in sorted(self.tracks.values(), key=lambda tr: tr.dist)[:4]:
            if tr.seen == t and tr.dist <= MOUTH_M:
                got = self.mouths.measure(frame, tr.face)
                if got is not None:
                    tr.mouth.append((t, got[0]))
                    tr.turn = got[1]
        for tr in list(self.tracks.values()):
            if tr.seen == t:
                self._fingerprint(frame, tr, t)

    def _figure_check(self, tr, t, width):
        """A face that is pixel-still for FIGURE_S is a figure; it moves again, it's a person."""
        pts = [b for b in tr.boxes if b[0] >= t - FIGURE_S]
        if len(pts) < 10 or pts[-1][0] - pts[0][0] < FIGURE_S * 0.9:
            return
        xs, ys, ws = (np.array([p[i] for p in pts]) for i in (1, 2, 3))
        drift = max(np.ptp(xs), np.ptp(ys), np.ptp(ws)) / width
        mouth = [v for tt, v in tr.mouth if tt >= t - FIGURE_S]
        still = drift < FIGURE_DRIFT and (not mouth or np.ptp(mouth) < FIGURE_MOUTH)
        if still and not tr.figure:
            tr.figure, tr.engaged, tr.facing_since = True, False, None
        elif tr.figure and drift >= 3 * FIGURE_DRIFT:
            tr.figure = False

    def _new_track(self, face, t):
        tr = Track(self.next_id, face, t)
        self.next_id += 1
        self.tracks[tr.id] = tr
        # Someone who just turned away and back: take over their place.
        for old in list(self.limbo.values()):
            ow = old.face[2]
            if (t - old.gone_at < 1.5 and 0.7 < face[2] / ow < 1.4
                    and math.hypot(face[0] - old.face[0], face[1] - old.face[1]) < ow):
                self._inherit(tr, old)
                break

    def _inherit(self, tr, old, matched=False):
        """A new face takes over an engaged one that just vanished. Its identity and prints
        come along only when the faces matched: by place alone it's "someone's there", not
        "it's still Anushhka" (that made Lars her, 2026-10-28)."""
        del self.limbo[old.id]
        tr.engaged, tr.stranger = True, old.stranger
        if matched:
            if tr.who[0] != "known":
                tr.who = old.who
            tr.prints.extendleft(reversed(old.prints))

    def _fingerprint(self, frame, tr, t):
        w = tr.face[2]
        if w < PRINT_PX or t - tr.last_print < (PRINT_KNOWN if tr.who[0] == "known" else PRINT_EVERY):
            return
        tr.last_print = t
        # Full marks for a face 100 px wide, detected clearly, turned less than 0.2.
        quality = (min(1.0, w / 100) * min(1.0, float(tr.face[14]) / 0.85)
                   * min(1.0, max(0.0, (0.6 - abs(tr.turn)) / 0.4)))
        tr.prints.append((t, self.rec.fingerprint(frame, tr.face), quality))
        recent = [p for _, p, _ in list(tr.prints)[-8:]]
        level, pid, score = faces.identify(self.gallery.scores(recent), len(recent))
        before = tr.who
        if before[0] == "known" and level != "known" and score >= faces.POSSIBLE and pid == before[1]:
            level = "known"  # stays recognised through a poor look
        tr.who = (level, pid, score)
        if not tr.engaged and self.limbo:
            mine = tr.mean_print()
            for old in list(self.limbo.values()):
                theirs = old.mean_print()
                if theirs is not None and float(mine @ theirs) >= faces.KNOWN:
                    self._inherit(tr, old, matched=True)
                    break
        if level is None and tr.stranger is None and len(tr.prints) >= 3:
            tr.stranger, self.next_stranger = self.next_stranger, self.next_stranger + 1
        if tr.engaged and level == "known" and before[0] != "known" and not self.arrival:
            self._emit("recognised", [f"Recognised: the person {self.place(tr)} is "
                                      f"{self.gallery.name(pid)}.", self.present_note(),
                                      self.memory_note(tr)], t=t)

    # ----- presence -----

    def _presence(self, t):
        for tr in list(self.tracks.values()):
            if tr.figure:
                continue
            if tr.engaged:
                tr.far_since = (tr.far_since or t) if tr.dist > LEAVE_M else None
                if tr.far_since and t - tr.far_since > 2:
                    tr.engaged = False
                    self._left(tr, t)
            elif tr.dist <= ENGAGE_M and abs(tr.turn) < FACING:
                tr.facing_since = tr.facing_since or t
                if t - tr.facing_since >= ENGAGE_S:
                    self._engage(tr, t)
            else:
                tr.facing_since = None
        held = self.paused_at is not None and t - self.paused_at < LEAVE_S
        if not held:
            for old in list(self.limbo.values()):
                if t - old.gone_at > LEAVE_S:
                    del self.limbo[old.id]
                    self._left(old, t)
        engaged = [tr for tr in self.tracks.values() if tr.engaged]
        self.far = sum(1 for tr in self.tracks.values() if not tr.engaged and not tr.figure)
        if self.session and not engaged and not self.limbo and not held:
            self.empty_since = self.empty_since or t
            if t - self.empty_since >= SESSION_GAP_S:
                self.session, self.empty_since, self.arrival = False, None, None
                self.next_stranger = 1  # strangers are forgotten with the session
                self._emit("session_end", t=t)
        else:
            self.empty_since = None
        if self.arrival and t >= self.arrival["due"]:
            self._arrive(t)
        for tid, due in list(self.pending_arrivals):
            tr = self.tracks.get(tid)
            if tr is None or not tr.engaged:
                self.pending_arrivals.remove((tid, due))
            elif tr.who[0] == "known" or len(tr.prints) >= faces.KNOWN_PRINTS or t >= due:
                self.pending_arrivals.remove((tid, due))
                self._emit("arrived", [f"Arrived: {self.label(tr)}, {self.place(tr)}.", self.present_note(),
                                       self.memory_note(tr)], prompt=True, t=t)

    def _engage(self, tr, t):
        tr.engaged = True
        if not self.session:
            self.session = True
            self.arrival = dict(start=t, due=t + (STUDY_S if self.describer else 1.0),
                                observation=None, asked=False)
            if self.describer:  # if a look is under way, _scene asks again once it's done
                self.arrival["asked"] = self.describer.ask(self.frame, "arrival")
        elif not self.arrival:
            # Give recognition a moment: a greeting a second before the match completes called
            # Lars "someone you may have met" (2026-10-29). Holds until known, or 3 prints, or 1 s.
            self.pending_arrivals.append((tr.id, t + 1.0))

    def _arrive(self, t):
        """The first arrival of a session, once he has studied them."""
        engaged = [tr for tr in self.tracks.values() if tr.engaged]
        if not engaged:
            self.arrival = None
            return
        if len(engaged) == 1:
            who = f"{self.label(engaged[0])}, {self.place(engaged[0])}, about {engaged[0].dist:.1f} m away"
        else:
            who = ", ".join(f"{self.label(tr)} {self.place(tr)}" for tr in engaged)
        far = f" {self.far_text()}" if self.far else ""
        obs = self.arrival["observation"]
        self.arrival = None
        quiet = self.settle_at is not None or t < self.handled_until  # he's just been moved
        memories = [self.memory_note(tr) for tr in engaged]
        self._emit("arrived", [f"Arrived: {who}.{far}", obs, *memories], prompt=not quiet, t=t)

    def _left(self, tr, t):
        name = self.gallery.name(tr.who[1]) if tr.who[0] == "known" else "a stranger"
        self._emit("left", [f"Left: {name}.", self.present_note()], t=t)

    def label(self, tr):
        level, pid, _ = tr.who
        if level == "known":
            return f"{self.gallery.name(pid)} (recognised)"
        if level == "possible":  # no name: a wrong one would give away who else he knows
            return "someone you may have met before (not sure)"
        return "a stranger"

    def memory_note(self, tr):
        """His memory of a remembered visitor, sent with their arrival or recognition (None for
        strangers and creators). remember_person stores it (faces.Gallery.memory)."""
        level, pid, _ = tr.who
        return self.gallery.memory(pid) if level == "known" else None

    def place(self, tr):
        return "on your left" if tr.yaw > 12 else "on your right" if tr.yaw < -12 else "in front of you"

    def far_text(self):
        return f"About {self.far} more {'person' if self.far == 1 else 'people'} further back."

    def present_note(self):
        engaged = sorted((tr for tr in self.tracks.values() if tr.engaged), key=lambda tr: -tr.yaw)
        who = ", ".join(f"{self.label(tr)} {self.place(tr)}" for tr in engaged) or "nobody close by"
        return f"Present: {who}." + (f" {self.far_text()}" if self.far else "")

    # ----- being moved, and sight -----

    def _motion_changed(self, change, t):
        if change == "moved":
            self.settle_at = None
            continuing = t < self.handled_until  # picked up again soon after: the same bout
            self.handled_until = float("inf")
            if not continuing:
                self.view_before = self.motion.before
                self.close_before_move = [self.gallery.name(tr.who[1]) for tr in self.tracks.values()
                                          if tr.engaged and tr.dist <= 1.0 and tr.who[0] == "known"]
            for tr in self.tracks.values():  # they'll be somewhere else in the picture
                if tr.engaged:
                    tr.gone_at = t
                    self.limbo[tr.id] = tr
            self.tracks = {}
            if continuing:
                return
            self.bout_open = True  # a "Still again" is owed once this bout ends (not re-opened by a
                                   # continuing bout: that fired it four times in a minute, 2026-10-29)
            who = (f" Just before, {' and '.join(self.close_before_move)} "
                   f"{'was' if len(self.close_before_move) == 1 else 'were'} right in front of you."
                   if self.close_before_move else "")
            self._emit("moved", [f"Moved: you're being picked up or carried; your view is swinging about.{who}"],
                       prompt=True, t=t, background=round(self.motion.background, 2),
                       people=round(self.people_share, 2))
        else:
            self.settle_at = t + SETTLE_S

    def _settled(self, view, t):
        self.settle_at = None
        self.handled_until = t + 10
        if not getattr(self, "bout_open", False):
            return  # already said he'd been set down this bout (it fired five times, 2026-10-28)
        self.bout_open = False
        same = self.motion.same_place(self.view_before, view)
        where = (", in the same place as before." if same else
                 "; the view is different, so you're somewhere new." if same is False else ".")
        self._emit("still", [f"Still again: you've been set down{where}"], prompt=True, t=t)
        if same is False and self.describer:
            self.describer.ask(self.frame, "new place")

    def _sight_changed(self, change, t):
        if change == "dark":
            self._emit("dark", ["Dark: your vision has gone black. Something may be covering your "
                                "eyes, or the lights are off."], prompt=True, t=t)
        else:
            self._emit("light", ["Your vision is back."], t=t)
            self.scene_next = min(self.scene_next, t + 1)

    # ----- the scene -----

    def _scene(self, t):
        while not self.scene_q.empty():
            (reason, seen, note, seconds), kw = self.scene_q.get()
            self.scene_error = kw.get("error")
            if reason == "arrival" and self.arrival:
                self.arrival["observation"] = note
                self._arrive(t)
            elif note:
                self._emit("observation", [note], t=t, seconds=round(seconds, 1))
        if not self.describer or self.motion.moving or self.sight.blind or self.frame is None:
            return
        a = self.arrival
        if a and not a["asked"] and not self.describer.busy:  # the look before they came is done
            a["asked"] = self.describer.ask(self.frame, "arrival")
            a["due"] = min(a["start"] + 2.5, max(a["due"], t + 1.5))
        if t >= self.scene_next:
            first = self.describer.last is None
            self.describer.ask(self.frame, "first" if first else "look")
            self.scene_next = t + (SCENE_EVERY_S if self.session else SCENE_IDLE_S)

    # ----- asked by chat.py -----

    def _said(self, t0, t1):
        """The track of whoever spoke between t0 and t1, or None if it isn't clear."""
        found = self.speaker(t0, t1)
        tid = found["track"]
        return self.tracks.get(tid) or self.limbo.get(tid) if tid else None

    def speaker(self, t0, t1):
        """Who was talking between t0 and t1 (wall-clock seconds): dict(track, name, label,
        overlapping, engaged), where overlapping counts the mouths that moved as if talking
        and engaged the people in front of him."""
        pool = list(self.tracks.values()) + [tr for tr in self.limbo.values() if tr.gone_at >= t0]
        acts = sorted(((a, tr) for tr in pool if (a := tr.mouth_peak(t0, t1)) is not None),
                      key=lambda x: -x[0])
        engaged = [tr for tr in self.tracks.values() if tr.engaged]
        top = acts[0][0] if acts else 0.0
        talking = sum(1 for a, tr in acts if a >= MOUTH_ACTIVE and (a is top or (a >= OVERLAP_ACTIVE and a >= 0.5 * top))
                      and not any(iou(tr.face, o.face) > 0.3 for _, o in acts if o is not tr and o.id < tr.id))
        pick = None
        if acts and acts[0][0] >= MOUTH_ACTIVE and (len(acts) == 1 or acts[0][0] >= 1.5 * acts[1][0]):
            pick = acts[0][1]
        elif len(engaged) == 1:  # only one person there: them, unless their mouth stayed still
            a = engaged[0].mouth_peak(t0, t1)
            pick = engaged[0] if a is None or a >= MOUTH_ACTIVE / 3 else None
        if pick is None:
            return dict(track=None, name=None, label=None, overlapping=talking, engaged=len(engaged))
        name = self.gallery.name(pick.who[1]) if pick.who[0] == "known" else None
        return dict(track=pick.id, name=name, label=f"{self.label(pick)} {self.place(pick)}",
                    overlapping=talking, engaged=len(engaged))

    def heard(self, t0, t1):
        """Whether speech between t0 and t1 was said to Frank, judged by mouths: speaker()'s
        answer plus to_him, why and mouths (each engaged person's mouth_peak)."""
        who = self.speaker(t0, t1)
        if self.sight.blind or self.motion.moving or (self.paused_at and self.paused_at >= t0):
            return dict(who, to_him=True, why="he couldn't see properly during the line, so he listens", mouths={})
        # Everyone close, not only the engaged: someone introducing themselves from the side
        # (Lars, 2026-10-28) hasn't faced him for ENGAGE_S yet.
        near = [tr for tr in self.tracks.values() if (tr.engaged or tr.dist <= MOUTH_NEAR_M) and not tr.figure]
        near += [tr for tr in self.limbo.values() if tr.gone_at >= t0]  # turned away mid-line
        mouths = {tr.id: tr.mouth_peak(t0, t1) for tr in near}
        seen = [m for m in mouths.values() if m is not None]
        shown = {str(k): (round(v, 2) if v is not None else None) for k, v in mouths.items()}
        if any(m >= MOUTH_ACTIVE for m in seen):
            return dict(who, to_him=True, why="a mouth in front of him moved", mouths=shown)
        # "Still" needs evidence: a face followed for a while, read often during the line.
        solid = [tr for tr in near if mouths.get(tr.id) is not None and t1 - tr.first >= TRACK_SETTLED_S
                 and sum(1 for tt, _ in tr.mouth if t0 <= tt <= t1) >= MOUTH_EVIDENCE]
        if seen and all(m < MOUTH_STILL for m in seen) and solid and len(solid) == len(seen):
            return dict(who, to_him=False, why="the mouths in front of him stayed still", mouths=shown)
        if seen and all(m < MOUTH_STILL for m in seen):
            return dict(who, to_him=True, why="a face he'd only just found: too little to go on, so he listens",
                        mouths=shown)
        if seen:  # between the two: not sure, so he listens
            return dict(who, to_him=True, why="a mouth in front of him moved a little", mouths=shown)
        if near or self.people_share >= PERSON_CLOSE:  # a mask, a hand, a turned head
            return dict(who, to_him=True, why="someone's in front of him; their mouth can't be seen",
                        mouths=shown)
        return dict(who, to_him=False, why="nobody in front of him", mouths=shown)

    def mouth_still(self, t):
        """Whether every mouth in front of him has been still for MOUTH_STILL_S up to t: the
        visitor has finished, as far as the eyes can tell. None if no mouth is being read."""
        near = [tr for tr in self.tracks.values() if (tr.engaged or tr.dist <= MOUTH_NEAR_M) and tr.mouth and not tr.figure]
        acts = []
        for tr in near:
            pts = [(tt, v) for tt, v in tr.mouth if t - MOUTH_STILL_S - 0.1 <= tt <= t]
            if len(pts) >= 3 and pts[-1][0] - pts[0][0] >= MOUTH_STILL_S * 0.6:
                vals = np.array([v for _, v in pts])
                acts.append(float(np.abs(np.diff(vals)).sum() / (pts[-1][0] - pts[0][0])))
        if not acts:
            return None
        return all(a < MOUTH_STILL for a in acts)

    def enroll(self, name, role, t0, t1, consent="", note=""):
        tr = self._said(t0, t1)
        if tr is None:
            return dict(ok=False, why="ambiguous")
        good = [p for tt, p, q in tr.prints if q >= ENROLL_Q and tt >= t1 - 15]
        if len(good) < ENROLL_MIN:
            return dict(ok=False, why="unclear")
        good = good[-12:]
        level, pid, score = faces.identify(self.gallery.scores(good), len(good))
        if level == "known":
            self.gallery.add_prints(pid, good)  # a fresh look at them
            tr.who = ("known", pid, score)
            return dict(ok=True, already=True, name=self.gallery.name(pid))
        pid = self.gallery.add(name, role, good, consent, note)
        tr.who, tr.stranger = ("known", pid, 1.0), None
        return dict(ok=True, already=False, name=name)

    def forget(self, t0, t1):
        tr = self._said(t0, t1)
        if tr is None:
            return dict(ok=False, why="ambiguous")
        level, pid, _ = tr.who
        if level != "known":
            recent = [p for _, p, _ in list(tr.prints)[-8:]]
            level, pid, _ = faces.identify(self.gallery.scores(recent), len(recent))
        if level == "possible":
            return dict(ok=False, why="unclear")
        if level != "known":
            return dict(ok=False, why="nothing")
        name = self.gallery.name(pid)
        if self.gallery.role(pid) == "creator":
            return dict(ok=False, why="creator", name=name)
        self.gallery.forget(pid)
        for other in list(self.tracks.values()) + list(self.limbo.values()):
            if other.who[1] == pid:
                other.who = (None, None, 0.0)
        return dict(ok=True, name=name)

    def snapshot(self, t):
        """The state, for the face controller (later) and web.py: where everyone is."""
        people = []
        for tr in self.tracks.values():
            mouth = tr.mouth_peak(t - 1.0, t)
            people.append(dict(
                id=tr.id, engaged=tr.engaged, level=tr.who[0], stranger=tr.stranger, figure=tr.figure,
                name=self.gallery.name(tr.who[1]) if tr.who[0] == "known" else None,
                score=round(float(tr.who[2]), 2), dist=round(float(tr.dist), 2),
                yaw=round(float(tr.yaw), 1), pitch=round(float(tr.pitch), 1), place=self.place(tr),
                talking=mouth is not None and mouth >= MOUTH_ACTIVE,
                mouth=None if mouth is None else round(mouth, 2)))
        return dict(t=t, moving=self.motion.moving, settling=self.settle_at is not None,
                    background=round(self.motion.background, 2), people_share=round(self.people_share, 2),
                    blind=self.sight.blind, session=self.session, far=self.far, people=people,
                    enrolling=self.enrolling and dict(name=self.enrolling["name"],
                                                      got=len(self.enrolling["prints"])))

    # ----- enrolling someone while he watches (web.py) -----

    def start_enrol(self, name, role, need=20, within=40.0):
        """Collect `need` looks at the only face in view, then store them under name (added
        to the person if that name and role already exist). Progress comes as events."""
        self.enrolling = dict(name=name, role=role, need=need, prints=[], last=0.0,
                              until=time.time() + within, said="")
        return dict(ok=True)

    def _enrol_step(self, frame, t):
        e = self.enrolling
        face, msg = enrol_face([tr.face for tr in self.tracks.values() if tr.seen == t])
        if not msg and t - e["last"] >= 0.3:
            e["prints"].append(self.rec.fingerprint(frame, face))
            e["last"] = t
            if len(e["prints"]) % 5 == 0:
                self._emit("enrol", message=f"Enrolling {e['name']}: {len(e['prints'])} of {e['need']}.")
        elif msg and msg != e["said"]:
            self._emit("enrol", message=f"Enrolling {e['name']}: {msg}.")
        e["said"] = msg
        if len(e["prints"]) >= e["need"]:
            self.enrolling = None
            mine = [pid for pid in self.gallery.find(e["name"]) if self.gallery.role(pid) == e["role"]]
            if mine:
                self.gallery.add_prints(mine[0], e["prints"])
            else:
                self.gallery.add(e["name"], e["role"], e["prints"],
                                 consent=f"{e['role']}, enrolled from the web page")
            self._emit("enrol", message=f"Stored {e['need']} looks at {e['name']} ({e['role']}).", done=True)
        elif t > e["until"]:
            self.enrolling = None
            self._emit("enrol", message=f"Enrolling {e['name']} stopped: only {len(e['prints'])} good "
                                        f"looks in time. Nothing stored.", done=True)

    # ----- the preview -----

    def draw(self, fps):
        """Show the preview window; False once it's closed (q or Esc)."""
        cv2.imshow("Frank's eyes", self.render(fps))
        return cv2.waitKey(1) & 0xFF not in (ord("q"), 27)

    def render(self, fps):
        """The preview picture: faces with names, scores, distances and mouths, and the state."""
        f = self.frame
        s = 960 / f.shape[1]
        img = cv2.resize(f, (960, round(f.shape[0] * s)))
        now = time.time()
        for tr in self.tracks.values():
            x, y, w, h = (np.array(tr.face[:4]) * s).astype(int)
            level, pid, score = tr.who
            colour = ((80, 220, 80) if level == "known" else (0, 200, 255) if level == "possible"
                      else (255, 200, 0) if tr.engaged else (160, 160, 160))
            who = "figure" if tr.figure else self.gallery.name(pid) if level else f"stranger {tr.stranger or '?'}"
            act = tr.mouth_peak(now - 1.0, now)
            cv2.rectangle(img, (x, y), (x + w, y + h), colour, 3 if tr.engaged else 1)
            lines = [f"{who} {score:.2f}", f"{tr.dist:.1f} m  turn {tr.turn:+.2f}",
                     f"mouth {act:.2f}" if act is not None else ""]
            for i, line in enumerate(lines):
                _text(img, line, (x, y + h + 18 + 18 * i), colour)
        state = "MOVING" if self.motion.moving else "settling" if self.settle_at else "still"
        _text(img, f"{fps:.0f} fps  {state}  background {self.motion.background:.0%}  "
                   f"people {self.people_share:.0%}  {'BLIND  ' if self.sight.blind else ''}"
                   f"light {self.sight.light:.0f}  detail {self.sight.detail:.0f}  "
                   f"{'session' if self.session else 'nobody'}  further back {self.far}"
                   + (f"  scene: {self.scene_error[:40]}" if self.scene_error else ""), (10, 24))
        for i, note in enumerate(list(self.recent_notes)[-4:]):
            _text(img, note[:120], (10, img.shape[0] - 14 - 22 * (3 - i)), (220, 220, 220), 0.5)
        return img


def _text(img, text, org, colour=(255, 255, 255), size=0.55):
    """A label on a dark box. (An outline in thicker text doesn't line up: OpenCV spaces
    letters wider the thicker they are.)"""
    if not text:
        return
    (w, h), base = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, size, 1)
    x, y = org
    cv2.rectangle(img, (x - 3, y - h - 4), (x + w + 3, y + base + 2), (0, 0, 0), -1)
    cv2.putText(img, text, org, cv2.FONT_HERSHEY_SIMPLEX, size, colour, 1, cv2.LINE_AA)


def run(cfg, emit, preview=True, scene=True, between=None, state=None, frames=None):
    """Watch until the video ends, the preview window closes or between() returns False.
    between(vision) runs after every frame; state(snapshot) gets the state 5 times a second
    and frames(jpeg) the preview picture 10 times a second."""
    cam = Camera(cfg["source"], cfg["width"], cfg["height"])
    vision = Vision(cfg, emit, scene)
    seq, fps, last_state, last_frame = 0, 0.0, 0.0, 0.0
    try:
        while True:
            got = cam.read(seq)
            if got is None:
                if cam.ended:
                    return vision
                continue
            seq, t, frame = got
            t0 = time.perf_counter()
            vision.step(frame, t)
            fps = 0.9 * fps + 0.1 / max(time.perf_counter() - t0, 1e-3)
            if between and between(vision) is False:
                return vision
            if state and t - last_state >= 0.2:
                state(vision.snapshot(t))
                last_state = t
            if frames and t - last_frame >= 0.1:
                frames(cv2.imencode(".jpg", vision.render(fps), [cv2.IMWRITE_JPEG_QUALITY, 70])[1].tobytes())
                last_frame = t
            if preview and not vision.draw(fps):
                return vision
    finally:
        cam.stop()
        if preview:
            cv2.destroyAllWindows()


def _child(cfg, preview, scene, commands, out):
    """The vision process (Eyes): events, state and replies go back on `out`. The native
    libraries' own messages go to output/frank/eyes.log, not into the chat."""
    import os
    log = HERE.parent / "output" / "frank" / "eyes.log"
    log.parent.mkdir(parents=True, exist_ok=True)
    native = open(log, "a")  # kept open for the life of the process
    os.dup2(native.fileno(), 2)

    out.cancel_join_thread()  # never hang on exit waiting for a reader that has gone
    parent = os.getppid()

    def between(vision):
        if os.getppid() != parent:  # chat.py or web.py has died: don't linger
            return False
        while True:
            try:
                rid, name, args = commands.get_nowait()
            except queue.Empty:
                return True
            if name == "stop":
                return False
            try:
                result = getattr(vision, name)(*args) if vision else dict(ok=False, why="camera off")
            except Exception as e:
                result = dict(ok=False, why=f"error: {type(e).__name__}: {e}")
            out.put(("reply", rid, result))
    web = preview == "web"  # the picture goes to the browser (web.py), not a window
    said = None
    while True:
        try:
            run(cfg, lambda ev: out.put(("event", ev)), preview and not web, scene, between,
                lambda snap: out.put(("state", snap)), (lambda jpeg: out.put(("jpeg", jpeg))) if web else None)
            return  # stopped, or the video ended
        except SystemExit as e:  # the camera won't open: no permission yet, or unplugged
            if not isinstance(cfg["source"], int):
                return out.put(("error", str(e)))
            if str(e) != said:
                out.put(("error", f"{e} (trying again every 3 s)"))
                said = str(e)
        except Exception as e:
            return out.put(("error", f"{type(e).__name__}: {e}"))
        for _ in range(30):  # 3 s, still answering chat.py
            if between(None) is False:
                return
            time.sleep(0.1)


class Eyes:
    """chat.py's handle on the eyes, which run in a process of their own. on_event(event)
    is called from a reader thread. preview: True for a window, "web" for jpeg (the
    newest preview picture, for web.py), False for neither."""

    def __init__(self, on_event, preview=True, scene=True, source=None):
        import multiprocessing
        cfg = load_config()
        if source is not None:
            cfg["source"] = source
        ctx = multiprocessing.get_context("spawn")
        self.commands, self.out = ctx.Queue(), ctx.Queue()
        self.proc = ctx.Process(target=_child, args=(cfg, preview, scene, self.commands, self.out),
                                daemon=True)
        self.on_event = on_event
        self.state, self.jpeg, self.replies, self.next_id = None, None, {}, 0
        self.error = None  # the last thing that went wrong, until the eyes see again
        self.cv = threading.Condition()

    def start(self):
        self.proc.start()
        threading.Thread(target=self._read, daemon=True).start()
        return self

    def _read(self):
        while True:
            try:
                msg = self.out.get(timeout=1.0)
            except queue.Empty:
                if not self.proc.is_alive():
                    self.state = self.jpeg = None  # nothing seen any more
                    self.error = self.error or "the vision process has stopped"
                    self.on_event(event("error", error="the vision process has stopped"))
                    return
                continue
            if msg[0] == "event":
                self.on_event(msg[1])
            elif msg[0] == "state":
                self.state, self.error = msg[1], None
            elif msg[0] == "jpeg":
                self.jpeg = msg[1]
            elif msg[0] == "reply":
                with self.cv:
                    self.replies[msg[1]] = msg[2]
                    self.cv.notify_all()
            elif msg[0] == "error":
                self.error = msg[1]
                self.on_event(event("error", error=msg[1]))

    def _ask(self, name, *args, timeout=3.0):
        with self.cv:
            self.next_id += 1
            rid = self.next_id
        self.commands.put((rid, name, args))
        with self.cv:
            self.cv.wait_for(lambda: rid in self.replies, timeout)
            return self.replies.pop(rid, None)

    def speaker(self, t0, t1):  # on the way to Frank's reply: never wait long
        return (self._ask("speaker", t0, t1, timeout=0.5)
                or dict(track=None, name=None, label=None, overlapping=0, engaged=0))

    def heard(self, t0, t1):  # on the way to Frank's reply: never wait long; if unsure, listen
        return (self._ask("heard", t0, t1, timeout=0.5)
                or dict(track=None, name=None, label=None, overlapping=0, engaged=0, to_him=True,
                        why="no answer from the eyes, so he listens", mouths={}))

    def enroll(self, name, t0, t1, consent="", note=""):
        return self._ask("enroll", name, "visitor", t0, t1, consent, note) or dict(ok=False, why="no reply")

    def forget(self, t0, t1):
        return self._ask("forget", t0, t1) or dict(ok=False, why="no reply")

    def present_note(self):
        return self._ask("present_note")

    def start_enrol(self, name, role):
        return self._ask("start_enrol", name, role) or dict(ok=False, why="no reply")

    def mouth_still(self, t):
        return self._ask("mouth_still", t, timeout=0.3)

    def stop(self):
        self.commands.put((0, "stop", ()))
        self.proc.join(3)
        if self.proc.is_alive():
            self.proc.terminate()


def enrol_face(found):
    """The face to enrol among those in view, and what's wrong if there isn't one: the
    nearest, if it's big enough and clearly nearer than anyone else (people further back
    are fine)."""
    if not found:
        return None, "nobody in view"
    found = sorted(found, key=lambda f: -f[2])
    if len(found) > 1 and found[0][2] < ENROLL_LEAD * found[1][2]:
        return None, "only one person close to the camera, please"
    if found[0][2] < ENROLL_PX:
        return None, "come closer"
    return found[0], ""


def enroll_cli(cfg, name, role, need=20):
    """Store someone's face from the camera: one person in view, turning their head a little."""
    cam, rec, gallery = Camera(cfg["source"], cfg["width"], cfg["height"]), faces.Recogniser(), faces.Gallery()
    prints, seq, last = [], 0, 0.0
    print(f"Enrolling {name} ({role}). One person in view: look at the camera, then turn your head "
          f"a little left, right, up and down. q cancels.")
    try:
        while len(prints) < need:
            got = cam.read(seq)
            if got is None:
                if cam.ended:
                    print(f"the video ended after {len(prints)} of {need}: nothing stored")
                    return
                continue
            seq, t, frame = got
            dets = rec.detect(frame)
            face, msg = enrol_face(dets)
            if not msg and t - last >= 0.3:
                prints.append(rec.fingerprint(frame, face))
                last = t
            s = 960 / frame.shape[1]
            img = cv2.resize(frame, (960, round(frame.shape[0] * s)))
            for d in dets:
                x, y, w, h = (np.array(d[:4]) * s).astype(int)
                cv2.rectangle(img, (x, y), (x + w, y + h), (80, 220, 80), 2)
            _text(img, f"{name}: {len(prints)}/{need}  {msg}", (10, 30), size=0.8)
            cv2.imshow("Frank's eyes: enrol", img)
            if cv2.waitKey(1) & 0xFF in (ord("q"), 27):
                print("cancelled")
                return
    finally:
        cam.stop()
        cv2.destroyAllWindows()
    others = [(gallery.name(pid), s) for pid, s in gallery.scores(prints)]
    mine = [pid for pid in gallery.find(name) if gallery.role(pid) == role]
    if mine:
        gallery.add_prints(mine[0], prints)
    else:
        gallery.add(name, role, prints, consent=f"{role}, enrolled with eyes.py --enroll")
    P = np.array(prints)
    sims = (P @ P.T)[np.triu_indices(len(P), 1)]
    print(f"Stored {len(prints)} prints of {name}. Similarity among them: min {sims.min():.2f}, "
          f"mean {sims.mean():.2f}. Closest other people: "
          + (", ".join(f"{n} {s:.2f}" for n, s in others[:3] if n.casefold() != name.casefold()) or "none"))


def list_cameras():
    import subprocess
    if sys.platform == "darwin":
        names = subprocess.run(["system_profiler", "SPCameraDataType"], capture_output=True, text=True).stdout
        print("Cameras macOS knows:", ", ".join(line.strip().rstrip(":") for line in names.splitlines()
                                               if line.startswith("    ") and line.strip().endswith(":")) or "none")
    for i in range(5):
        cap = cv2.VideoCapture(i, cv2.CAP_AVFOUNDATION if sys.platform == "darwin" else cv2.CAP_ANY)
        if cap.isOpened():
            ok, frame = cap.read()
            print(f"  camera {i}: {'%dx%d' % (frame.shape[1], frame.shape[0]) if ok else 'no picture'}")
        cap.release()
    print('Put the number in frank/camera.json as "source", or try one with eyes.py --camera N.')


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="Frank's eyes")
    ap.add_argument("--camera", type=int, help="camera number (default: camera.json)")
    ap.add_argument("--video", help="a video file instead of the camera")
    ap.add_argument("--enroll", metavar="NAME", help="store this person's face")
    ap.add_argument("--creator", action="store_true", help="with --enroll: one of Frank's creators")
    ap.add_argument("--cameras", action="store_true", help="list the cameras")
    ap.add_argument("--no-scene", action="store_true", help="no snapshots to the vision model")
    ap.add_argument("--no-preview", action="store_true")
    args = ap.parse_args()
    cfg = load_config()
    if args.camera is not None:
        cfg["source"] = args.camera
    if args.video:
        cfg["source"] = args.video
    if args.cameras:
        return list_cameras()
    if args.enroll:
        return enroll_cli(cfg, args.enroll, "creator" if args.creator else "visitor")

    def show(ev):
        stamp = time.strftime("%H:%M:%S", time.localtime(ev["t"]))
        for note in ev["notes"] or [f"({ev['kind']})"]:
            print(f"{stamp}  {note}{'  [he reacts]' if ev['prompt'] else ''}")
    print("Watching. Close the window (q) or Ctrl+C to stop.")
    try:
        run(cfg, show, preview=not args.no_preview, scene=not args.no_scene)
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()

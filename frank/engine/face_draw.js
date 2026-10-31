/*
  Frank's face, drawn from the engine's joint channels (frank/engine/channels.py).

    drawFace(canvas, joints, opts)

  A schematic front view: we face him, so his LEFT is on the viewer's RIGHT.
  joints: gaze_x, gaze_y (-1..1; +x to his left, +y up), lid_top_L/R (0 shut .. 1 the OPEN
  pose), lid_bot_L/R (1 open/down, lower = raised), brow_in_L/R, brow_out_L/R (-1..1, + up),
  smile (-1..1), smile_asym (-1..1, + his left corner more), jaw_floor (0..1). Missing
  channels are drawn at rest.
  opts: talk (0..1, his voice loudness; the mouth opens max(jaw_floor, talk)),
        exaggerate (default 1.3: motion a little bigger than life, so it reads at a glance),
        labels (default true: "his right" / "his left" under the face),
        background (default "#0b0f0d").
  The canvas is drawn at its own pixel size (canvas.width/height); set those for the
  device pixel ratio before calling. No libraries.
*/
(function (root) {
  "use strict";

  const REST = {
    gaze_x: 0, gaze_y: 0, lid_top_L: 0.85, lid_top_R: 0.85, lid_bot_L: 1, lid_bot_R: 1,
    brow_in_L: 0, brow_out_L: 0, brow_in_R: 0, brow_out_R: 0, smile: 0, smile_asym: 0, jaw_floor: 0,
  };
  const SKIN = "#8aa184", SKIN_DARK = "#6c8467", SKIN_DEEP = "#4f6449", SKIN_LIGHT = "#9db497";
  const HAIR = "#141814", BROW = "#1b201a", LINE = "#3a4a37", SCLERA = "#e6e1cf";
  const IRIS = "#6f7f3e", IRIS_RING = "#2e3a1c", PUPIL = "#0a0c08", MOUTH_IN = "#240f12";
  const LIP = "#4d5f49", TEETH = "#d8d0b4", METAL = "#9aa2a6", METAL_DARK = "#596166";
  const W = 200, H = 250;   // design space; the face is fitted into the canvas

  const num = (v, d) => (typeof v === "number" && isFinite(v) ? v : d);
  const clamp = (v, lo, hi) => Math.max(lo, Math.min(hi, v));

  function drawFace(canvas, joints, opts) {
    const o = opts || {};
    const j = Object.assign({}, REST);
    for (const k in REST) j[k] = num(joints && joints[k], REST[k]);
    const ex = num(o.exaggerate, 1.3);
    const talk = clamp(num(o.talk, 0), 0, 1);

    const ctx = canvas.getContext("2d");
    const cw = canvas.width, ch = canvas.height;
    ctx.setTransform(1, 0, 0, 1, 0, 0);
    ctx.fillStyle = o.background || "#0b0f0d";
    ctx.fillRect(0, 0, cw, ch);
    const s = Math.min(cw / W, ch / H) * 0.96;
    ctx.setTransform(s, 0, 0, s, (cw - W * s) / 2, (ch - H * s) / 2);
    ctx.lineJoin = "round";
    ctx.lineCap = "round";

    const open = clamp(Math.max(j.jaw_floor, talk), 0, 1);
    const drop = open * 9 * ex;   // the chin comes down with the jaw

    neck(ctx, drop);
    head(ctx, drop);
    hair(ctx);
    forehead(ctx, j);
    // His right eye on the viewer's left (x = 72), his left on the viewer's right (x = 128).
    eye(ctx, 72, j.gaze_x, j.gaze_y, j.lid_top_R, j.lid_bot_R, ex);
    eye(ctx, 128, j.gaze_x, j.gaze_y, j.lid_top_L, j.lid_bot_L, ex);
    brow(ctx, 86, 54, j.brow_in_R, j.brow_out_R, ex);
    brow(ctx, 114, 146, j.brow_in_L, j.brow_out_L, ex);
    nose(ctx);
    mouth(ctx, j.smile, j.smile_asym, open, ex, drop);

    if (o.labels !== false) {
      ctx.fillStyle = "#5f6f67";
      ctx.font = "7px -apple-system, Segoe UI, sans-serif";
      ctx.textAlign = "left";
      ctx.fillText("his right", 4, H - 4);
      ctx.textAlign = "right";
      ctx.fillText("his left", W - 4, H - 4);
    }
    ctx.setTransform(1, 0, 0, 1, 0, 0);
  }

  function neck(ctx, drop) {
    ctx.fillStyle = SKIN_DARK;
    ctx.fillRect(68, 205, 64, 50);
    for (const x of [52, 134]) {   // the bolts
      ctx.fillStyle = METAL_DARK;
      ctx.fillRect(x, 226 + drop * 0.3, 14, 11);
      ctx.fillStyle = METAL;
      ctx.fillRect(x + (x < 100 ? -5 : 13), 224 + drop * 0.3, 6, 15);
    }
  }

  function head(ctx, drop) {
    ctx.beginPath();
    ctx.moveTo(40, 22);
    ctx.lineTo(160, 22);
    ctx.quadraticCurveTo(168, 22, 168, 32);
    ctx.lineTo(166, 150);
    ctx.quadraticCurveTo(164, 178, 142, 212 + drop);
    ctx.quadraticCurveTo(136, 226 + drop, 122, 228 + drop);
    ctx.lineTo(78, 228 + drop);
    ctx.quadraticCurveTo(64, 226 + drop, 58, 212 + drop);
    ctx.quadraticCurveTo(36, 178, 34, 150);
    ctx.lineTo(32, 32);
    ctx.quadraticCurveTo(32, 22, 40, 22);
    ctx.closePath();
    ctx.fillStyle = SKIN;
    ctx.fill();
    ctx.lineWidth = 1.5;
    ctx.strokeStyle = SKIN_DEEP;
    ctx.stroke();
    // ears
    ctx.fillStyle = SKIN_DARK;
    for (const x of [25, 167]) {
      ctx.beginPath();
      ctx.ellipse(x + 4, 122, 6, 15, 0, 0, Math.PI * 2);
      ctx.fill();
    }
    // cheek hollows
    ctx.fillStyle = "rgba(60, 78, 56, .28)";
    for (const x of [58, 142]) {
      ctx.beginPath();
      ctx.ellipse(x, 160, 11, 18, 0, 0, Math.PI * 2);
      ctx.fill();
    }
  }

  function hair(ctx) {
    ctx.beginPath();
    ctx.moveTo(30, 40);
    ctx.lineTo(30, 18);
    ctx.quadraticCurveTo(30, 12, 38, 12);
    ctx.lineTo(162, 12);
    ctx.quadraticCurveTo(170, 12, 170, 18);
    ctx.lineTo(170, 44);
    const teeth = 12;   // the ragged fringe
    for (let i = teeth; i >= 0; i--) {
      const x = 30 + (140 * i) / teeth;
      ctx.lineTo(x, i % 2 ? 50 + (i % 3) * 2 : 40);
    }
    ctx.closePath();
    ctx.fillStyle = HAIR;
    ctx.fill();
  }

  function forehead(ctx, j) {
    // the scar with its stitches, on his left
    ctx.strokeStyle = "#3c4a38";
    ctx.lineWidth = 1.6;
    ctx.beginPath();
    ctx.moveTo(116, 60);
    ctx.lineTo(152, 70);
    ctx.stroke();
    ctx.lineWidth = 1.1;
    for (let i = 0; i < 6; i++) {
      const x = 120 + i * 6, y = 61 + i * 1.7;
      ctx.beginPath();
      ctx.moveTo(x - 1, y - 3.5);
      ctx.lineTo(x + 1, y + 3.5);
      ctx.stroke();
    }
    // raised brows wrinkle the forehead; inner brows down make the furrow
    const up = Math.max(0, (j.brow_in_L + j.brow_in_R + j.brow_out_L + j.brow_out_R) / 4);
    const knit = Math.max(0, -(j.brow_in_L + j.brow_in_R) / 2);
    if (up > 0.05) {
      ctx.strokeStyle = `rgba(60, 76, 56, ${clamp(up * 0.9, 0, 0.75)})`;
      ctx.lineWidth = 1.2;
      for (const y of [64, 71]) {
        ctx.beginPath();
        ctx.moveTo(70, y + 2);
        ctx.quadraticCurveTo(100, y - 3, 130, y + 2);
        ctx.stroke();
      }
    }
    if (knit > 0.05) {
      ctx.strokeStyle = `rgba(52, 66, 48, ${clamp(knit, 0, 0.85)})`;
      ctx.lineWidth = 1.4;
      for (const x of [96, 104]) {
        ctx.beginPath();
        ctx.moveTo(x, 80);
        ctx.lineTo(x + (x < 100 ? 1 : -1), 92);
        ctx.stroke();
      }
    }
  }

  function eye(ctx, cx, gx, gy, top, bot, ex) {
    const cy = 112, rx = 17, ry = 12.5;
    // socket shadow
    ctx.fillStyle = "rgba(55, 72, 52, .4)";
    ctx.beginPath();
    ctx.ellipse(cx, cy - 1, rx + 6, ry + 7, 0, 0, Math.PI * 2);
    ctx.fill();

    ctx.save();
    ctx.beginPath();
    ctx.ellipse(cx, cy, rx, ry, 0, 0, Math.PI * 2);
    ctx.clip();
    ctx.fillStyle = SCLERA;
    ctx.fillRect(cx - rx, cy - ry, rx * 2, ry * 2);
    // iris and pupil: his left (+gaze_x) is our right; up (+gaze_y) is up
    const ix = cx + clamp(gx * 9 * ex, -14, 14), iy = cy - clamp(gy * 6 * ex, -10, 10);
    ctx.fillStyle = IRIS;
    ctx.beginPath();
    ctx.arc(ix, iy, 7.5, 0, Math.PI * 2);
    ctx.fill();
    ctx.strokeStyle = IRIS_RING;
    ctx.lineWidth = 1.2;
    ctx.stroke();
    ctx.fillStyle = PUPIL;
    ctx.beginPath();
    ctx.arc(ix, iy, 3.4, 0, Math.PI * 2);
    ctx.fill();
    ctx.fillStyle = "rgba(255, 255, 255, .7)";
    ctx.beginPath();
    ctx.arc(ix + 2.2, iy - 2.4, 1.3, 0, Math.PI * 2);
    ctx.fill();

    // lids: the upper edge from the top of the eye (1, OPEN) down to the lower lid (0, shut);
    // the lower edge from the bottom (1) up to a little past the middle (0)
    const t = clamp(top, 0, 1), b = clamp(bot, 0, 1);
    const yTop = cy - ry - 1, yBot = cy + ry + 1;
    let lower = yBot - Math.pow(1 - b, 0.9) * (2 * ry) * 0.6 * Math.min(ex, 1.2);
    let upper = yTop + Math.pow(1 - t, 0.85) * (2 * ry + 2) * Math.min(ex, 1.15);
    if (upper > lower - 0.5) upper = lower - 0.5;   // shut: the lids meet
    ctx.fillStyle = SKIN_DARK;
    // upper lid, its margin arching up in the middle
    ctx.beginPath();
    ctx.moveTo(cx - rx - 3, yTop - 4);
    ctx.lineTo(cx + rx + 3, yTop - 4);
    ctx.lineTo(cx + rx + 3, upper + 3);
    ctx.quadraticCurveTo(cx, upper - 3, cx - rx - 3, upper + 3);
    ctx.closePath();
    ctx.fill();
    ctx.strokeStyle = "#20281e";
    ctx.lineWidth = 1.8;
    ctx.beginPath();
    ctx.moveTo(cx + rx + 3, upper + 3);
    ctx.quadraticCurveTo(cx, upper - 3, cx - rx - 3, upper + 3);
    ctx.stroke();
    // lower lid, its margin sagging in the middle
    ctx.fillStyle = SKIN_DARK;
    ctx.beginPath();
    ctx.moveTo(cx - rx - 3, yBot + 4);
    ctx.lineTo(cx + rx + 3, yBot + 4);
    ctx.lineTo(cx + rx + 3, lower - 2);
    ctx.quadraticCurveTo(cx, lower + 3, cx - rx - 3, lower - 2);
    ctx.closePath();
    ctx.fill();
    ctx.strokeStyle = "rgba(32, 40, 30, .7)";
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(cx + rx + 3, lower - 2);
    ctx.quadraticCurveTo(cx, lower + 3, cx - rx - 3, lower - 2);
    ctx.stroke();
    ctx.restore();

    ctx.strokeStyle = SKIN_DEEP;
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.ellipse(cx, cy, rx, ry, 0, 0, Math.PI * 2);
    ctx.stroke();
  }

  function brow(ctx, xIn, xOut, bin, bout, ex) {
    // + raises by up to RAISE (35 deg), - lowers by up to LOWER (20 deg): drawn 11 and 7 units
    const base = 90;
    const lift = (v) => (v >= 0 ? v * 11 : v * 7) * ex;
    const yIn = base - lift(clamp(bin, -1, 1)), yOut = base - 2 - lift(clamp(bout, -1, 1));
    const mx = (xIn + xOut) / 2, my = (yIn + yOut) / 2 - 3;
    ctx.strokeStyle = BROW;
    ctx.lineWidth = 7.5;
    ctx.beginPath();
    ctx.moveTo(xIn, yIn);
    ctx.quadraticCurveTo(mx, my, xOut, yOut);
    ctx.stroke();
    ctx.lineWidth = 4;   // thinner at the tail
    ctx.beginPath();
    ctx.moveTo(xOut, yOut);
    ctx.lineTo(xOut + (xOut < xIn ? -4 : 4), yOut + 2);
    ctx.stroke();
  }

  function nose(ctx) {
    ctx.strokeStyle = "rgba(64, 82, 60, .8)";
    ctx.lineWidth = 1.6;
    ctx.beginPath();
    ctx.moveTo(96, 112);
    ctx.quadraticCurveTo(93, 136, 90, 148);
    ctx.quadraticCurveTo(100, 156, 110, 148);
    ctx.stroke();
    ctx.fillStyle = "rgba(40, 52, 38, .6)";
    for (const x of [94, 106]) {
      ctx.beginPath();
      ctx.ellipse(x, 150, 3, 1.6, 0, 0, Math.PI * 2);
      ctx.fill();
    }
  }

  function mouth(ctx, smile, asym, open, ex, drop) {
    const cx = 100, cy = 182, half = 27;
    // corner lift: his left corner is on our right
    const liftL = clamp(smile + asym * 0.8, -1.4, 1.4), liftR = clamp(smile - asym * 0.8, -1.4, 1.4);
    const xR = cx - half - Math.max(0, smile) * 3, xL = cx + half + Math.max(0, smile) * 3;
    const yR = cy - liftR * 9 * ex, yL = cy - liftL * 9 * ex;
    const upMid = cy - 1 - open * 3;
    const loMid = cy + 1 + open * 26 * ex + drop * 0.2;
    // control points that put the curve's middle where we want it
    const cUp = 2 * upMid - (yR + yL) / 2, cLo = 2 * loMid - (yR + yL) / 2;

    if (open > 0.03) {
      ctx.save();
      ctx.beginPath();
      ctx.moveTo(xR, yR);
      ctx.quadraticCurveTo(cx, cUp, xL, yL);
      ctx.quadraticCurveTo(cx, cLo, xR, yR);
      ctx.closePath();
      ctx.fillStyle = MOUTH_IN;
      ctx.fill();
      ctx.clip();
      ctx.fillStyle = TEETH;   // upper teeth
      ctx.fillRect(cx - 18, upMid - 4, 36, 4 + Math.min(5, open * 10));
      ctx.fillStyle = "#5a2a2e";   // tongue
      ctx.beginPath();
      ctx.ellipse(cx, loMid + 2, 15, 6 + open * 4, 0, 0, Math.PI * 2);
      ctx.fill();
      ctx.restore();
    }
    ctx.strokeStyle = LIP;
    ctx.lineWidth = 3.2;
    ctx.beginPath();
    ctx.moveTo(xR, yR);
    ctx.quadraticCurveTo(cx, cUp, xL, yL);
    ctx.stroke();
    ctx.lineWidth = open > 0.03 ? 2.6 : 3.2;
    ctx.beginPath();
    ctx.moveTo(xL, yL);
    ctx.quadraticCurveTo(cx, cLo, xR, yR);
    ctx.stroke();
    // corner creases for a smile, a chin line for a frown
    ctx.strokeStyle = "rgba(60, 76, 56, .7)";
    ctx.lineWidth = 1.2;
    for (const [x, y, lift, side] of [[xR, yR, liftR, -1], [xL, yL, liftL, 1]]) {
      if (lift > 0.25) {
        ctx.beginPath();
        ctx.moveTo(x + side * 2, y - 6);
        ctx.quadraticCurveTo(x + side * 6, y, x + side * 2, y + 6);
        ctx.stroke();
      } else if (lift < -0.25) {
        ctx.beginPath();
        ctx.moveTo(x, y + 2);
        ctx.lineTo(x + side * 2, y + 8);
        ctx.stroke();
      }
    }
    ctx.lineWidth = 1.2;
    ctx.strokeStyle = "rgba(60, 76, 56, .5)";
    ctx.beginPath();
    ctx.moveTo(cx - 9, 204 + drop);
    ctx.quadraticCurveTo(cx, 207 + drop, cx + 9, 204 + drop);
    ctx.stroke();
  }

  root.drawFace = drawFace;
  root.FACE_REST = REST;
})(typeof window !== "undefined" ? window : globalThis);

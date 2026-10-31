// The twin's linkage solver: servo horn angles -> a transform for every moving body of a rig
// (perform-rig/1, written by a robot's exporter, e.g. cad/twin_export.py for Frank).
// No three.js in here, so node can test it (test_kinematics.mjs). Matrices are 4x4, row-major,
// flat arrays of 16; points are [x, y, z] in the rig's units (mm).
//
// A rig is points and bodies, solved in the order the bodies are listed:
//   point "on"    a point fixed to a body: the body's transform times its rest position "at"
//   point "dyad"  a pin joining two links: in the plane through point a with normal "normal"
//                 (in the rest frame of body "frame"), the point at its rest distances from a
//                 and b, on the same side of a-b as at rest. When the two links can't reach,
//                 it is the nearest point they can reach, and the solve reports the gap as a
//                 fault (the real servo would stall there).
//   body "fixed"     stays put (frame, shell)
//   body "revolute"  turns about origin/axis by the mean of gain x horn angle of its servos
//   body "link"      rigid, placed by two points a, b (planar: the plane normal "normal")
//   body "bend"      a flexible part: its vertices blend between bodies a and b along pa -> pb
// A body with a "parent" moves with it: its motion is in the parent's rest frame.

export const I4 = () => [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1];

export function mul(A, B) {
  const C = new Array(16).fill(0);
  for (let r = 0; r < 4; r++)
    for (let c = 0; c < 4; c++)
      for (let k = 0; k < 4; k++) C[r * 4 + c] += A[r * 4 + k] * B[k * 4 + c];
  return C;
}

export function apply(M, p) {
  return [0, 1, 2].map(r => M[r * 4] * p[0] + M[r * 4 + 1] * p[1] + M[r * 4 + 2] * p[2] + M[r * 4 + 3]);
}

function applyDir(M, v) {
  return [0, 1, 2].map(r => M[r * 4] * v[0] + M[r * 4 + 1] * v[1] + M[r * 4 + 2] * v[2]);
}

export function invertRigid(M) {
  // rotation transposed, translation -R^T t
  const R = [M[0], M[1], M[2], M[4], M[5], M[6], M[8], M[9], M[10]];
  const t = [M[3], M[7], M[11]];
  const Rt = [R[0], R[3], R[6], R[1], R[4], R[7], R[2], R[5], R[8]];
  const ti = [0, 1, 2].map(r => -(Rt[r * 3] * t[0] + Rt[r * 3 + 1] * t[1] + Rt[r * 3 + 2] * t[2]));
  return [Rt[0], Rt[1], Rt[2], ti[0], Rt[3], Rt[4], Rt[5], ti[1], Rt[6], Rt[7], Rt[8], ti[2], 0, 0, 0, 1];
}

const sub = (a, b) => [a[0] - b[0], a[1] - b[1], a[2] - b[2]];
const add = (a, b) => [a[0] + b[0], a[1] + b[1], a[2] + b[2]];
const scale = (a, s) => [a[0] * s, a[1] * s, a[2] * s];
const dot = (a, b) => a[0] * b[0] + a[1] * b[1] + a[2] * b[2];
const cross = (a, b) => [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]];
const norm = a => Math.hypot(a[0], a[1], a[2]);
const unit = a => scale(a, 1 / (norm(a) || 1));
const inPlane = (v, n) => sub(v, scale(n, dot(v, n)));   // n a unit vector

// Rotation by deg about the line through origin o along axis (right hand)
export function rotAbout(o, axis, deg) {
  const [x, y, z] = unit(axis);
  const t = deg * Math.PI / 180, c = Math.cos(t), s = Math.sin(t), C = 1 - c;
  const R = [x * x * C + c, x * y * C - z * s, x * z * C + y * s,
    y * x * C + z * s, y * y * C + c, y * z * C - x * s,
    z * x * C - y * s, z * y * C + x * s, z * z * C + c];
  const Ro = [0, 1, 2].map(r => R[r * 3] * o[0] + R[r * 3 + 1] * o[1] + R[r * 3 + 2] * o[2]);
  return [R[0], R[1], R[2], o[0] - Ro[0], R[3], R[4], R[5], o[1] - Ro[1], R[6], R[7], R[8], o[2] - Ro[2], 0, 0, 0, 1];
}

const translate = v => [1, 0, 0, v[0], 0, 1, 0, v[1], 0, 0, 1, v[2], 0, 0, 0, 1];

// Planar rigid placement: the transform taking rest a0 to a and the in-plane direction a0->b0 to a->b
function placeLink(a0, b0, a, b, n) {
  const u0 = unit(inPlane(sub(b0, a0), n)), u = unit(inPlane(sub(b, a), n));
  const ang = Math.atan2(dot(n, cross(u0, u)), dot(u0, u)) * 180 / Math.PI;
  return mul(translate(a), mul(rotAbout([0, 0, 0], n, ang), translate(scale(a0, -1))));
}

export class Rig {
  constructor(rig) {
    this.rig = rig;
    this.points = rig.points;
    this.bodies = rig.bodies;
    this.byName = Object.fromEntries(rig.bodies.map(b => [b.name, b]));
  }

  // horn: {servo id: degrees, CCW about its shaft, 0 = the CAD pose}; a servo left out is at 0.
  // Returns {T: {body: matrix}, bends: {body: {A, B, pa, pb}}, faults: [{point, gap}], pins: {point: xyz}}
  solve(horn) {
    const T = { frame: I4(), shell: I4() };
    const pins = {}, faults = [], bends = {};
    const point = name => {
      if (pins[name]) return pins[name];
      const q = this.points[name];
      if (!q) throw new Error(`no point ${name}`);
      let w;
      if (q.on) {
        if (!T[q.on]) throw new Error(`point ${name} is on ${q.on}, which isn't solved yet`);
        w = apply(T[q.on], q.at);
      } else {
        w = this.dyad(name, q, point(q.dyad[0]), point(q.dyad[1]), q.frame ? T[q.frame] : null, faults);
      }
      return (pins[name] = w);
    };
    for (const b of this.bodies) {
      const P = b.parent ? T[b.parent] : I4();
      const m = b.motion;
      if (m.type === "fixed") T[b.name] = P;
      else if (m.type === "revolute") {
        let sum = 0;
        for (const s of m.servos) sum += s.gain * (horn[s.id] ?? 0);
        T[b.name] = mul(P, rotAbout(m.origin, m.axis, sum / m.servos.length));
      } else if (m.type === "link") {
        const Pi = invertRigid(P);
        const a = apply(Pi, point(m.a)), bb = apply(Pi, point(m.b));
        T[b.name] = mul(P, placeLink(this.points[m.a].at, this.points[m.b].at, a, bb, unit(m.normal)));
      } else if (m.type === "bend") {
        T[b.name] = P;
        bends[b.name] = { A: T[m.a], B: T[m.b], pa: m.pa, pb: m.pb };
      } else throw new Error(`body ${b.name}: unknown motion ${m.type}`);
    }
    return { T, bends, faults, pins };
  }

  dyad(name, q, aW, bW, F, faults) {
    const n = unit(q.normal);
    const a0 = this.points[q.dyad[0]].at, b0 = this.points[q.dyad[1]].at, c0 = q.at;
    const Fi = F ? invertRigid(F) : null;
    const a = Fi ? apply(Fi, aW) : aW, b = Fi ? apply(Fi, bW) : bW;
    const ra = norm(inPlane(sub(c0, a0), n)), rb = norm(inPlane(sub(c0, b0), n));
    const side = Math.sign(dot(cross(sub(b0, a0), sub(c0, a0)), n)) || 1;
    const ab = inPlane(sub(b, a), n);
    const d = norm(ab);
    const e = unit(ab), perp = cross(n, e);
    let x, h;
    if (d > ra + rb || d < Math.abs(ra - rb) || d < 1e-9) {
      const gap = d > ra + rb ? d - ra - rb : Math.abs(ra - rb) - d;
      faults.push({ point: name, gap });
      x = d > ra + rb ? ra : (ra > rb ? ra : -ra);
      h = 0;
    } else {
      x = (d * d + ra * ra - rb * rb) / (2 * d);
      h = Math.sqrt(Math.max(0, ra * ra - x * x));
    }
    // keep the triangle a, b, c turning the same way as at rest, and c's offset along n
    let c = add(add(a, scale(e, x)), scale(perp, side * h));
    c = add(c, scale(n, dot(sub(c0, a0), n)));
    return F ? apply(F, c) : c;
  }
}

// Bend weights along pa -> pb for the vertices of a flexible part (smoothstep, 0 at a, 1 at b)
export function bendWeight(v, pa, pb) {
  const ab = sub(pb, pa);
  let t = dot(sub(v, pa), ab) / dot(ab, ab);
  t = Math.min(1, Math.max(0, t));
  return t * t * (3 - 2 * t);
}

// A vertex of a flexible part, moved: (1 - w) A v + w B v
export function bendPoint(v, w, A, B) {
  const p = apply(A, v), q = apply(B, v);
  return [p[0] + w * (q[0] - p[0]), p[1] + w * (q[1] - p[1]), p[2] + w * (q[2] - p[2])];
}

// Horn angle of a servo from its pulse: sign x (us - us at zero) / us per degree. cal is the
// robot's servo entry ({zero, sign}); board is its board's pulse map ({us0, us_per_deg}).
export function hornAngle(us, cal, board, usPerHornDeg = 2000 / 180) {
  const zeroUs = board.us0 + (cal.zero ?? 90) * board.us_per_deg;
  return (cal.sign ?? 1) * (us - zeroUs) / usPerHornDeg;
}

export { applyDir };

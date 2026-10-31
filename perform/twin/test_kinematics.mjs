// Tests for the linkage solver on a robot's rig:
//   node perform/twin/test_kinematics.mjs [output/twin/frank_rig.json]
// 1. At rest (every horn at 0) every body is where the CAD has it.
// 2. Each servo swept -60..+60 deg in 5 deg steps: no NaN, and where its linkage first locks
//    (a pin the links can't reach, more than 0.05 mm), which tells the usable horn range.
// 3. Which way the parts it drives move at +-20 deg (the centre of what it moves).
// Last line: KINEMATICS OK, or KINEMATICS: n problem(s).
import { readFileSync } from "node:fs";
import { Rig, apply } from "./kinematics.js";

const path = process.argv[2] || "output/twin/frank_rig.json";
const spec = JSON.parse(readFileSync(path, "utf8"));
const rig = new Rig(spec);
const problems = [];

const rest = rig.solve({});
for (const [name, M] of Object.entries(rest.T)) {
  const I = [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1];
  const err = Math.max(...M.map((v, i) => Math.abs(v - I[i])));
  if (err > 1e-6) problems.push(`rest: ${name} is off its CAD pose by ${err.toExponential(2)}`);
}
if (rest.faults.length) problems.push(`rest: faults ${JSON.stringify(rest.faults)}`);

// the bodies a servo moves: those whose transform changes when only it turns
function moved(sid, deg) {
  const s = rig.solve({ [sid]: deg });
  const out = {};
  for (const b of spec.bodies) {
    const M = s.T[b.name];
    if (M.some(v => !Number.isFinite(v))) problems.push(`${sid} ${deg}: ${b.name} is not finite`);
    const c = centreOf(b.name);
    const p = apply(M, c);
    const d = [p[0] - c[0], p[1] - c[1], p[2] - c[2]];
    if (Math.hypot(...d) > 0.05) out[b.name] = d;
  }
  return { out, faults: s.faults };
}

// a body's rough centre: the mean of the pins on it, or its revolute origin
function centreOf(name) {
  const pts = Object.values(spec.points).filter(q => q.on === name).map(q => q.at);
  const b = rig.byName[name];
  if (b.motion.type === "link") {
    pts.push(spec.points[b.motion.a].at, spec.points[b.motion.b].at);
  }
  if (!pts.length && b.motion.origin) return b.motion.origin.map((v, i) => v + (i === 2 ? 0 : 0));
  if (!pts.length) return [0, 0, 0];
  return [0, 1, 2].map(i => pts.reduce((s, q) => s + q[i], 0) / pts.length);
}

const fmt = d => d.map(v => (v >= 0 ? "+" : "") + v.toFixed(1)).join(",");
for (const sid of Object.keys(spec.servos)) {
  let lo = null, hi = null;
  for (let deg = 0; deg <= 60; deg += 5) {
    if (hi === null && moved(sid, deg).faults.some(f => f.gap > 0.05)) hi = deg;
    if (lo === null && moved(sid, -deg).faults.some(f => f.gap > 0.05)) lo = -deg;
  }
  const plus = moved(sid, 20).out, minus = moved(sid, -20).out;
  const keys = Object.keys(plus).filter(k => !k.startsWith("horn_"));
  const main = keys.slice(0, 3).map(k => `${k} +20:(${fmt(plus[k])}) -20:(${fmt(minus[k] || [0, 0, 0])})`);
  console.log(`${sid.padEnd(4)} locks at ${lo ?? "<-60"} / ${hi ?? ">+60"} deg; moves ${keys.length} bodies: ${main.join("; ")}`);
}

for (const p of problems) console.log("PROBLEM " + p);
console.log(problems.length ? `KINEMATICS: ${problems.length} problem(s)` : "KINEMATICS OK");
process.exit(problems.length ? 1 : 0);

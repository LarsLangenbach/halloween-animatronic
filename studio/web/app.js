// The studio's shell: the four steps, the 3D twin beside them, and the status every page reads.
// Each page is a module with mount(el), unmount() and status(st) (called ten times a second).
import * as model from "./model.js";
import * as constraints from "./constraints.js";
import * as studio from "./studio.js";
import * as states from "./states.js";

const PAGES = { model, constraints, studio, states };
export const S = { robot: null, robots: null, meta: null, status: null, library: [] };
const $ = id => document.getElementById(id);
let current = null;

// ---------------------------------------------------------------------------------- helpers
export function h(tag, props = {}, ...kids) {
  const el = document.createElement(tag);
  for (const [k, v] of Object.entries(props || {})) {
    if (v == null || v === false) continue;
    if (k.startsWith("on")) el[k] = v;
    else if (k === "class") el.className = v;
    else if (k === "style" && typeof v === "object") Object.assign(el.style, v);
    else if (k in el && k !== "list" && typeof v !== "string") el[k] = v;
    else el.setAttribute(k, v === true ? "" : v);
  }
  for (const c of kids.flat(Infinity)) if (c != null && c !== false) el.append(c.nodeType ? c : String(c));
  return el;
}

export async function get(path) {
  const r = await fetch(path, { cache: "no-store" });
  const data = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(data.why || data.error || `${path}: ${r.status}`);
  return data;
}

export async function post(path, body = {}) {
  const r = await fetch(path, { method: "POST", headers: { "Content-Type": "application/json", "X-Studio": "1" },
                                body: JSON.stringify(body) });
  const data = await r.json().catch(() => ({}));
  if (!r.ok || data.ok === false) throw new Error(data.why || data.error || `${path}: ${r.status}`);
  return data;
}

export function fit(canvas) {
  const dpr = window.devicePixelRatio || 1, r = canvas.getBoundingClientRect();
  const w = Math.round(r.width * dpr), hgt = Math.round(r.height * dpr);
  if (canvas.width !== w || canvas.height !== hgt) { canvas.width = w; canvas.height = hgt; }
  return dpr;
}

export function css(name) { return getComputedStyle(document.documentElement).getPropertyValue(name).trim(); }

export async function loadLibrary() {
  S.library = (await get("/s/library")).animations;
  document.dispatchEvent(new CustomEvent("library"));
  return S.library;
}

export function describeKey(k) {
  return k.kind === "tag" ? `${k.tag} ${k.intensity.toFixed(2)}`
    : k.kind === "feel" ? `feel P ${k.p.toFixed(2)} A ${k.a.toFixed(2)} D ${k.d.toFixed(2)}`
    : k.kind === "event" ? k.event : `look ${Math.round(k.yaw)}° ${Math.round(k.pitch)}°`;
}

// ---------------------------------------------------------------------------------- steps
export function go(name) {
  if (!PAGES[name]) name = "model";
  if (name !== "model" && !S.robot) name = "model";
  if (current) PAGES[current].unmount?.();
  current = name;
  document.body.dataset.page = name;
  document.body.classList.toggle("no-stage", S.robot && S.robot !== "frank");
  for (const b of document.querySelectorAll(".steps button")) {
    b.classList.toggle("on", b.dataset.step === name);
    b.disabled = b.dataset.step !== "model" && !S.robot;
  }
  const el = $("page");
  el.replaceChildren();
  el.scrollTop = 0;
  PAGES[name].mount(el);
  if (location.hash !== `#${name}`) history.replaceState(null, "", `#${name}`);
}

export function useRobot(name) {
  S.robot = name;
  try { localStorage.setItem("studio.robot", name); } catch (e) { /* private window */ }
  $("robot-pill").textContent = name === "frank" ? "Frank (Cogley head a2.0.33)" : name;
  $("robot-pill").className = "pill on";
  if (name === "frank" && !$("twin").src) $("twin").src = "/twin/index.html?hero=1";
}

// ---------------------------------------------------------------------------------- status
function showStatus(st) {
  const snap = st.snapshot || {};
  $("si-state").textContent = st.runner && st.runner.running ? `${st.runner.name}: ${st.runner.state}` : (snap.state || "–");
  const w = snap.face && snap.face.weights ? Object.entries(snap.face.weights).sort((a, b) => b[1] - a[1])[0] : null;
  $("si-feel").textContent = w && w[1] > 0.08 ? `${w[0]} ${w[1].toFixed(2)}` : "neutral";
  const pf = snap.performance;
  $("si-play").textContent = pf && pf.playing ? `${pf.title} (${pf.elapsed.toFixed(1)} / ${pf.duration.toFixed(1)} s)`
    : snap.steered ? "steered by hand" : "nothing";
  const bad = Object.entries(st.servos || {}).filter(([, s]) => s.clamped).map(([k]) => k);
  $("si-clamped").textContent = bad.length ? `held at a soft limit: ${bad.join(", ")}` : "";
}

async function poll() {
  try {
    const st = await get("/s/status");
    S.status = st;
    $("conn").textContent = "live";
    $("conn").className = "pill on";
    showStatus(st);
    if (current) PAGES[current].status?.(st);
  } catch (e) {
    $("conn").textContent = "server down";
    $("conn").className = "pill warn";
  }
  setTimeout(poll, 100);
}

async function main() {
  for (const b of document.querySelectorAll(".steps button")) b.onclick = () => go(b.dataset.step);
  S.robots = await get("/s/robots");
  S.meta = await get("/engine/meta");
  $("key-pill").textContent = S.robots.key ? "claude: on" : "claude: no key";
  $("key-pill").className = S.robots.key ? "pill" : "pill warn";
  await loadLibrary();
  let saved = null;
  try { saved = localStorage.getItem("studio.robot"); } catch (e) { /* private window */ }
  if (saved === "frank" || (saved && S.robots.others.some(r => r.name === saved))) useRobot(saved);
  else $("twin").src = "/twin/index.html?hero=1";      // Frank on the stage while choosing
  go(location.hash.slice(1) || (S.robot ? "studio" : "model"));
  poll();
}

main().catch(e => { $("page").textContent = "The studio couldn't start: " + e.message; console.error(e); });

// Step 3, the animation studio. The emotion synthesiser: drag on the emotion map (pleasure left
// to right, arousal bottom to top, dominance on the slider) and the engine mixes the tags near
// the point; press a tag or an event to play it. Record captures all of that as a timeline.
// Prompt to animation: Claude writes a timeline from a sentence (frank/engine/animate.py). Either
// way the result lands in the draft, which plays, can be trimmed, and saves to the library the
// state machine draws from.
import { S, h, get, post, fit, css, loadLibrary, describeKey } from "./app.js";

const EVENTS = ["blink", "long_blink", "flinch", "greet", "beat"];
const LABEL = { skeptical: [1, 12, "left"], vulnerable: [-1, 12, "right"], irritated: [0, -8, "center"],
                concentrating: [0, 16, "center"], neutral: [0, 16, "center"] };
let root = null, snap = null, draft = null, rec = null, els = {};
let drag = false, lastSteer = 0, steerPt = null;
const trail = [];
const clamp1 = x => Math.max(-1, Math.min(1, x));

export function mount(el) {
  root = el;
  els = {};
  const map = els.map = h("canvas", { id: "map", "aria-label": "Emotion map: pleasant to the right, aroused at the top. Drag to steer." });
  const dom = els.dom = h("input", { type: "range", min: -1, max: 1, step: 0.05, value: 0.3 });
  const domv = h("span", {}, "0.30");
  dom.oninput = () => { domv.textContent = (+dom.value).toFixed(2); if (snap?.steered) steer(snap.steered[0], snap.steered[1], true); };
  const intensity = els.intensity = h("input", { type: "range", min: 0.1, max: 1, step: 0.05, value: 0.8 });
  const release = els.release = h("button", { disabled: true, onclick: () => { steerPt = null; post("/engine/steer", { release: true }); } }, "release");
  els.mapState = h("span", { class: "small muted" }, "drag to steer him");
  map.onpointerdown = e => { drag = true; map.setPointerCapture(e.pointerId); steer(...mapXY(e), true); };
  map.onpointermove = e => { if (drag) steer(...mapXY(e), false); };
  map.onpointerup = map.onpointercancel = () => {
    drag = false;
    if (steerPt) { steer(steerPt[0], steerPt[1], true); if (rec) addFeel(true); }
  };
  els.rec = h("button", { class: "rec", onclick: toggleRec, title: "Record the map, the tags and the events as a timeline" }, "● record");
  els.recInfo = h("span", { class: "small muted" }, "");

  const synth = h("div", { class: "card" },
    h("div", { class: "card-h" }, h("h2", {}, "emotion synthesiser"), h("span", { class: "row" }, els.recInfo, els.rec)),
    map,
    h("div", { class: "row" }, h("label", { class: "inline" }, "dominance ", dom, domv), els.mapState, release),
    h("div", { class: "row" }, h("h2", {}, "tags"), h("label", { class: "inline small" }, "intensity ", intensity)),
    h("div", { class: "buttons", style: { marginTop: "6px" } }, S.meta.tags.map(t => h("button", { onclick: () => tag(t) }, t))),
    h("div", { class: "row" }, h("h2", {}, "events")),
    h("div", { class: "buttons", style: { marginTop: "6px" } }, EVENTS.map(ev => h("button", { onclick: () => event(ev) }, ev.replace("_", " ")))));

  const prompt = els.prompt = h("textarea", { rows: 3, placeholder: "he hears a terrible pun, groans, then can't help smiling",
    onkeydown: e => { if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) generate(); } });
  els.gen = h("button", { class: "primary", onclick: generate }, "animate");
  els.genState = h("span", { class: "small muted" }, S.robots.online ? "online the examples below play; new prompts run in the laptop app" : S.robots.key ? "Claude writes it in about 10 s, then it plays" : "no key in frank/.env: only the examples play");
  const examples = S.library.filter(a => a.source === "example" && a.prompt).map(a =>
    h("button", { class: "chip", onclick: () => { prompt.value = a.prompt; generate(); } }, a.prompt));
  const promptCard = h("div", { class: "card" },
    h("div", { class: "card-h" }, h("h2", {}, "prompt to animation")),
    prompt, h("div", { class: "row" }, els.gen, els.genState),
    examples.length ? h("div", { class: "buttons", style: { marginTop: "8px" } }, examples) : null);

  els.title = h("input", { type: "text", placeholder: "name it", style: { flex: 1 } });
  els.timeline = h("canvas", { class: "timeline" });
  els.keys = h("ul", { class: "keys" });
  els.draftInfo = h("span", { class: "small muted" }, "");
  els.save = h("button", { class: "primary", onclick: save }, "save to library");
  const draftCard = els.draftCard = h("div", { class: "card" },
    h("div", { class: "card-h" }, h("h2", {}, "draft"), els.draftInfo),
    h("div", { class: "row" }, els.title),
    h("div", { style: { marginTop: "8px" } }, els.timeline),
    h("div", { class: "row" },
      h("button", { onclick: () => draft && post("/engine/play", { anim: draft }) }, "▶ play"),
      h("button", { onclick: () => post("/engine/stop") }, "■ stop"), els.save),
    els.keys);

  els.lib = h("ul", { class: "lib" });
  const libCard = h("div", { class: "card" },
    h("div", { class: "card-h" }, h("h2", {}, "library"), h("span", { class: "small muted" }, "drag into a state on the state machine page")),
    els.lib);

  el.append(h("div", { class: "cards" },
    h("div", {}, h("h1", {}, "Animation studio"),
      h("p", { class: "muted" }, "Steer his feeling, play tags and events, record a take or describe one, then save it.")),
    h("div", { class: "cols2" }, h("div", { class: "cards" }, synth), h("div", { class: "cards" }, promptCard, draftCard, libCard))));
  showDraft();
  showLibrary();
  document.addEventListener("library", showLibrary);
  window.addEventListener("resize", drawAll);
}

export function unmount() {
  document.removeEventListener("library", showLibrary);
  window.removeEventListener("resize", drawAll);
  if (rec) toggleRec();
  root = null;
}

export function status(st) {
  snap = st.snapshot;
  if (!root) return;
  drawAll();
  const pf = snap?.performance;
  for (const li of els.lib.children) li.classList.toggle("playing", !!(pf?.playing && pf.title === li.dataset.title));
  if (rec) els.recInfo.textContent = `${((performance.now() - rec.t0) / 1000).toFixed(1)} s, ${rec.keys.length} keys`;
}

function drawAll() { if (root) { drawMap(); drawTimeline(); } }

// ---------------------------------------------------------------------------------- the synthesiser
function mapXY(e) {
  const r = els.map.getBoundingClientRect();
  return [clamp1(((e.clientX - r.left) / r.width) * 2 - 1), clamp1(1 - ((e.clientY - r.top) / r.height) * 2)];
}

function steer(p, a, force) {
  steerPt = [p, a];
  if (rec) addFeel(false);
  const now = performance.now();
  if (!force && now - lastSteer < 33) return;   // about 30 a second while dragging
  lastSteer = now;
  post("/engine/steer", { p, a, d: +els.dom.value }).catch(() => {});
}

function tag(t) {
  const intensity = +els.intensity.value;
  post("/engine/tag", { name: t, intensity }).catch(e => alert(e.message));
  if (rec) rec.keys.push({ t: recT(), kind: "tag", tag: t, intensity });
}

function event(ev) {
  post("/engine/event", { name: ev }).catch(e => alert(e.message));
  if (rec) rec.keys.push({ t: recT(), kind: "event", event: ev });
}

function drawMap() {
  const c = els.map, dpr = fit(c), ctx = c.getContext("2d");
  const w = c.width, hh = c.height, X = p => (p + 1) / 2 * w, Y = a => (1 - a) / 2 * hh;
  ctx.clearRect(0, 0, w, hh);
  const quads = [[-1, 1, "#ff6b5e"], [0, 1, "#f0b44c"], [0, 0, "#9fe07a"], [-1, 0, "#7fb6ff"]];
  for (const [px, ay, col] of quads) { ctx.fillStyle = col + "14"; ctx.fillRect(X(px), Y(ay), w / 2, hh / 2); }
  ctx.strokeStyle = css("--line"); ctx.lineWidth = dpr;
  ctx.beginPath(); ctx.moveTo(X(0), 0); ctx.lineTo(X(0), hh); ctx.moveTo(0, Y(0)); ctx.lineTo(w, Y(0)); ctx.stroke();
  ctx.beginPath(); ctx.arc(X(0), Y(0), w / 2 - dpr, 0, Math.PI * 2); ctx.stroke();
  ctx.fillStyle = css("--faint"); ctx.font = `${11 * dpr}px ui-monospace, Menlo, Consolas, monospace`;
  ctx.textAlign = "center"; ctx.fillText("aroused", X(0), 14 * dpr); ctx.fillText("calm", X(0), hh - 6 * dpr);
  ctx.textAlign = "left"; ctx.fillText("unpleasant", 6 * dpr, Y(0) - 6 * dpr);
  ctx.textAlign = "right"; ctx.fillText("pleasant", w - 6 * dpr, Y(0) - 6 * dpr);
  const wts = snap?.face?.weights || {}, dNow = +els.dom.value;
  for (const [t, pos] of Object.entries(S.meta.map || {})) {
    const x = X(pos[0]), y = Y(pos[1]), k = Math.min(1, wts[t] || 0);
    ctx.globalAlpha = 0.35 + 0.65 * Math.exp(-((pos[2] - dNow) ** 2) / 0.35);
    if (k > 0.02) {
      ctx.fillStyle = css("--accent") + Math.round(40 + 140 * k).toString(16).padStart(2, "0");
      ctx.beginPath(); ctx.arc(x, y, (6 + 18 * k) * dpr, 0, Math.PI * 2); ctx.fill();
    }
    ctx.fillStyle = css("--text"); ctx.beginPath(); ctx.arc(x, y, 3.5 * dpr, 0, Math.PI * 2); ctx.fill();
    const [lx, ly, align] = LABEL[t] || [0, -8, "center"];
    ctx.fillStyle = k > 0.15 ? css("--text") : css("--muted"); ctx.textAlign = align;
    ctx.font = `${(k > 0.15 ? 12 : 11) * dpr}px ui-monospace, Menlo, Consolas, monospace`;
    ctx.fillText(t, x + lx * 7 * dpr, y + ly * dpr);
  }
  ctx.globalAlpha = 1;
  const m = Array.isArray(snap?.mood) ? snap.mood : null;
  if (m) {
    trail.push([m[0], m[1]]); if (trail.length > 45) trail.shift();
    ctx.strokeStyle = css("--hi") + "88"; ctx.lineWidth = 2 * dpr; ctx.beginPath();
    trail.forEach(([p, a], i) => (i ? ctx.lineTo(X(p), Y(a)) : ctx.moveTo(X(p), Y(a)))); ctx.stroke();
    ctx.strokeStyle = css("--hi"); ctx.lineWidth = 2.5 * dpr;
    ctx.beginPath(); ctx.arc(X(m[0]), Y(m[1]), 7 * dpr, 0, Math.PI * 2); ctx.stroke();
  }
  const s = snap?.steered;
  if (s) {
    const x = X(s[0]), y = Y(s[1]);
    ctx.strokeStyle = css("--warn"); ctx.lineWidth = 2 * dpr;
    ctx.beginPath(); ctx.moveTo(x - 12 * dpr, y); ctx.lineTo(x + 12 * dpr, y); ctx.moveTo(x, y - 12 * dpr); ctx.lineTo(x, y + 12 * dpr); ctx.stroke();
    ctx.beginPath(); ctx.arc(x, y, 9 * dpr, 0, Math.PI * 2); ctx.stroke();
  }
  els.mapState.textContent = s ? `P ${s[0].toFixed(2)}  A ${s[1].toFixed(2)}  D ${s[2].toFixed(2)}` : "drag to steer him";
  els.mapState.className = "small " + (s ? "warnt" : "muted");
  els.release.disabled = !s;
}

// ---------------------------------------------------------------------------------- recording
function recT() { return Math.round((performance.now() - rec.t0) / 10) / 100; }

function addFeel(final) {
  const t = recT();
  const last = rec.keys.filter(k => k.kind === "feel").pop();
  if (!final && last && t - last.t < 0.25) return;    // a key every quarter second while dragging
  if (final && last && t - last.t < 0.05) return;
  rec.keys.push({ t, kind: "feel", p: steerPt[0], a: steerPt[1], d: +els.dom.value });
}

function toggleRec() {
  if (!rec) {
    rec = { t0: performance.now(), keys: [] };
    if (snap?.steered) { steerPt = [snap.steered[0], snap.steered[1]]; addFeel(true); }
    els.rec.classList.add("on");
    els.rec.textContent = "■ stop";
    return;
  }
  const keys = rec.keys, duration = Math.min(20, recT() + 0.3);
  rec = null;
  els.rec.classList.remove("on");
  els.rec.textContent = "● record";
  els.recInfo.textContent = "";
  if (!keys.length) return;
  setDraft({ title: "recorded take", duration, keys: keys.filter(k => k.t <= 20).slice(0, 60) }, "recorded");
}

// ---------------------------------------------------------------------------------- prompt
async function generate() {
  const p = els.prompt.value.trim();
  if (!p) { els.prompt.focus(); return; }
  els.gen.disabled = true;
  els.genState.textContent = "Claude is writing it…";
  els.genState.className = "small warnt";
  try {
    const r = await post("/engine/animate", { prompt: p });
    setDraft(r.anim, "prompt", p);
    els.genState.textContent = r.note || `playing "${r.anim.title}"`;
    els.genState.className = "small muted";
  } catch (e) {
    els.genState.textContent = e.message;
    els.genState.className = "small warnt";
  }
  els.gen.disabled = false;
}

// ---------------------------------------------------------------------------------- the draft
function setDraft(anim, source, prompt, id) {
  draft = { title: anim.title, duration: anim.duration, keys: anim.keys.map(k => ({ ...k })) };
  draft.meta = { source, prompt, id };
  els.title.value = draft.title;
  showDraft();
}

function showDraft() {
  els.draftCard.style.opacity = draft ? 1 : 0.6;
  els.save.disabled = !draft;
  els.title.disabled = !draft;
  if (!draft) {
    els.draftInfo.textContent = "record a take or write a prompt";
    els.keys.replaceChildren();
    drawTimeline();
    return;
  }
  els.draftInfo.textContent = `${draft.duration.toFixed(1)} s, ${draft.keys.length} keys${draft.meta.id ? " · from the library" : ""}`;
  els.keys.replaceChildren(...draft.keys.map((k, i) => h("li", {},
    h("span", { class: "faint" }, `${k.t.toFixed(2).padStart(5)} s`), h("span", {}, k.kind), h("span", { class: "muted" }, describeKey(k)),
    h("button", { class: "x", title: "remove this key", onclick: () => { draft.keys.splice(i, 1); showDraft(); } }, "×"))));
  drawTimeline();
}

function drawTimeline() {
  const c = els.timeline;
  if (!c) return;
  const dpr = fit(c), ctx = c.getContext("2d"), w = c.width, hh = c.height;
  ctx.clearRect(0, 0, w, hh);
  if (!draft) return;
  const dur = Math.max(0.5, draft.duration), pad = 8 * dpr, X = t => pad + (t / dur) * (w - 2 * pad);
  const lanes = { feel: [0.05, 0.42], tag: [0.47, 0.66], event: [0.70, 0.84], look: [0.87, 0.98] };
  ctx.font = `${10 * dpr}px ui-monospace, Menlo, Consolas, monospace`;
  ctx.strokeStyle = css("--panel-2"); ctx.lineWidth = dpr;
  for (let s = 0; s <= dur; s += 1) { ctx.beginPath(); ctx.moveTo(X(s), 0); ctx.lineTo(X(s), hh); ctx.stroke(); }
  for (const [name, [a]] of Object.entries(lanes)) { ctx.fillStyle = css("--faint"); ctx.textAlign = "left"; ctx.fillText(name, 2 * dpr, a * hh + 9 * dpr); }
  // feel: pleasure and arousal as two lines across the lane
  const feels = draft.keys.filter(k => k.kind === "feel");
  const [f0, f1] = lanes.feel, fy = v => (f0 + (1 - (v + 1) / 2) * (f1 - f0)) * hh;
  for (const [key, col] of [["p", css("--accent")], ["a", css("--warn")]]) {
    if (!feels.length) break;
    ctx.strokeStyle = col; ctx.lineWidth = 1.5 * dpr; ctx.beginPath();
    feels.forEach((k, i) => (i ? ctx.lineTo(X(k.t), fy(k[key])) : ctx.moveTo(X(k.t), fy(k[key]))));
    ctx.lineTo(X(dur), fy(feels[feels.length - 1][key])); ctx.stroke();
  }
  // tags as blocks until the next tag
  const tags = draft.keys.filter(k => k.kind === "tag");
  tags.forEach((k, i) => {
    const end = i + 1 < tags.length ? tags[i + 1].t : dur, [a, b] = lanes.tag;
    ctx.fillStyle = css("--accent") + Math.round(40 + 120 * k.intensity).toString(16).padStart(2, "0");
    ctx.fillRect(X(k.t), a * hh, Math.max(2, X(end) - X(k.t) - dpr), (b - a) * hh);
    ctx.fillStyle = css("--hi"); ctx.textAlign = "left"; ctx.fillText(k.tag, X(k.t) + 3 * dpr, b * hh - 4 * dpr);
  });
  for (const kind of ["event", "look"]) {
    const [a, b] = lanes[kind];
    for (const k of draft.keys.filter(x => x.kind === kind)) {
      ctx.fillStyle = kind === "event" ? css("--cyan") : css("--muted");
      ctx.fillRect(X(k.t) - dpr, a * hh, 2 * dpr, (b - a) * hh);
      ctx.textAlign = "left"; ctx.fillText(kind === "event" ? k.event : `${Math.round(k.yaw)},${Math.round(k.pitch)}`, X(k.t) + 3 * dpr, b * hh - 2 * dpr);
    }
  }
  const pf = snap?.performance;
  if (pf?.playing && pf.title === draft.title) {
    ctx.strokeStyle = css("--hi"); ctx.lineWidth = 2 * dpr;
    ctx.beginPath(); ctx.moveTo(X(pf.elapsed), 0); ctx.lineTo(X(pf.elapsed), hh); ctx.stroke();
  }
}

async function save() {
  if (!draft) return;
  const title = els.title.value.trim() || draft.title;
  draft.title = title;
  const m = draft.meta;
  const { entry } = await post("/s/library", { id: m.id, title, source: m.id ? "edited" : m.source, prompt: m.prompt,
                                               anim: { title, duration: draft.duration, keys: draft.keys } });
  draft.meta.id = entry.id;
  await loadLibrary();
  els.draftInfo.textContent = `saved as "${entry.title}"`;
}

// ---------------------------------------------------------------------------------- library
function showLibrary() {
  if (!root) return;
  els.lib.replaceChildren(...S.library.map(a => h("li", {
    draggable: true, "data-title": a.title,
    ondragstart: e => { e.dataTransfer.setData("text/x-anim", a.id); e.dataTransfer.effectAllowed = "copy"; } },
    h("span", { class: "title", title: a.prompt || a.title }, a.title),
    h("span", { class: "tag-src" }, a.source),
    h("span", { class: "small faint" }, `${a.anim.duration.toFixed(1)} s`),
    h("button", { title: "play", onclick: () => post(`/s/library/${a.id}/play`) }, "▶"),
    h("button", { title: "open in the draft", onclick: () => setDraft(a.anim, a.source, a.prompt, a.id) }, "edit"),
    h("button", { title: "rename", onclick: async () => {
      const t = prompt("New name", a.title);
      if (t) { await post(`/s/library/${a.id}/rename`, { title: t }); loadLibrary(); } } }, "rename"),
    h("button", { class: "danger", title: "delete", onclick: async () => {
      if (confirm(`Delete "${a.title}" from the library?`)) { await post(`/s/library/${a.id}/delete`); loadLibrary(); } } }, "×"))));
  if (!S.library.length) els.lib.append(h("li", { class: "muted" }, "nothing saved yet"));
}

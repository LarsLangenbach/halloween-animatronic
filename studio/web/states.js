// Step 4, the state machine: Create state, name it, and it appears as a node. Drag from a node's
// right-hand dot onto another node to join them with an arrow; click the arrow to choose when it
// fires (when the animation is done, after some seconds, or on an event). Click a state to give
// it animations: drag them in from the library, or write a prompt and Claude makes one for it.
// A state with several animations plays one of them each time (at random or in turn): that's its
// variety. Run plays the machine on the face; the active state lights up.
import { S, h, get, post, loadLibrary } from "./app.js";

const NS = "http://www.w3.org/2000/svg";
const W = 176, H = 60;
let root = null, els = {}, M = null, name = null, problems = [], sel = null;
let view = { x: 0, y: 0 }, runner = null, prevState = null, fired = null, saveTimer = null, ghost = null;

const svg = (tag, attrs = {}, ...kids) => {
  const el = document.createElementNS(NS, tag);
  for (const [k, v] of Object.entries(attrs)) if (v != null) el.setAttribute(k, v);
  for (const c of kids.flat()) if (c != null) el.append(c.nodeType ? c : document.createTextNode(String(c)));
  return el;
};
const slug = s => s.toLowerCase().replace(/[^a-z0-9]+/g, "_").replace(/^_|_$/g, "").slice(0, 40) || "state";
const anim = id => S.library.find(a => a.id === id);
const onText = ln => ln.on === "after" ? `after ${ln.seconds} s` : ln.on === "event" ? `on ${ln.event}` : "when done";

export async function mount(el) {
  root = el;
  els = {};
  const names = (await get("/s/machines")).names;
  let want = null;
  try { want = localStorage.getItem("studio.machine"); } catch (e) { /* private window */ }
  name = names.includes(want) ? want : names[0] || "main";
  if (!names.length) await post(`/s/machine/${name}/save`, { machine: { name, states: {}, links: [] } });
  els.pick = h("select", { onchange: () => open(els.pick.value) });
  els.stateName = h("input", { type: "text", placeholder: "name the new state", style: { width: "14em" },
                               onkeydown: e => { if (e.key === "Enter") createState(); } });
  els.saved = h("span", { class: "small faint" }, "");
  els.run = h("button", { class: "primary", onclick: run }, "▶ run");
  els.stop = h("button", { onclick: stop, disabled: true }, "■ stop");
  els.svg = svg("svg", {});
  els.canvas = h("div", { class: "sm-canvas", tabindex: 0 }, els.svg);
  els.hint = h("div", { class: "empty-hint" }, "Name a state above and press Create state.");
  els.canvas.append(els.hint);
  els.side = h("div", { class: "sm-side" });
  el.append(h("div", { class: "sm" },
    h("div", { class: "sm-main" },
      h("div", { class: "sm-bar" },
        h("label", { class: "inline" }, "machine ", els.pick),
        h("button", { onclick: newMachine }, "new"),
        h("span", { class: "faint" }, "│"),
        els.stateName, h("button", { class: "primary", onclick: () => createState() }, "+ create state"),
        h("span", { class: "faint" }, "│"), els.run, els.stop, els.saved),
      els.canvas),
    els.side));
  wireCanvas();
  document.addEventListener("library", renderSide);
  document.addEventListener("keydown", onKey);
  await open(name, names);
}

export function unmount() {
  document.removeEventListener("library", renderSide);
  document.removeEventListener("keydown", onKey);
  flush();
  root = null;
}

async function open(n, names) {
  flush();
  name = n;
  try { localStorage.setItem("studio.machine", n); } catch (e) { /* private window */ }
  if (!names || !names.includes(n)) names = (await get("/s/machines")).names;
  els.pick.replaceChildren(...names.map(x => h("option", { value: x, selected: x === n }, x)));
  const r = await get(`/s/machine/${encodeURIComponent(n)}`);
  M = r.machine;
  problems = r.problems;
  sel = null;
  view = { x: 0, y: 0 };
  render();
}

async function newMachine() {
  const n = (prompt("Name the new machine (letters, digits, - and _)") || "").trim().replace(/\s+/g, "_");
  if (!n) return;
  await post(`/s/machine/${encodeURIComponent(n)}/save`, { machine: { name: n, states: {}, links: [] } });
  open(n);
}

// ---------------------------------------------------------------------------------- saving
function changed() {
  els.saved.textContent = "…";
  clearTimeout(saveTimer);
  saveTimer = setTimeout(flush, 400);
  render();
}

async function flush() {
  if (!saveTimer || !M) return;
  clearTimeout(saveTimer);
  saveTimer = null;
  try {
    const r = await post(`/s/machine/${encodeURIComponent(name)}/save`, { machine: M });
    problems = r.problems;
    if (els.saved) els.saved.textContent = runner?.running ? "saved (press run again to use it)" : "saved";
    if (root) renderSide();
  } catch (e) {
    if (els.saved) els.saved.textContent = "not saved: " + e.message;
  }
}

// ---------------------------------------------------------------------------------- editing
function createState(at) {
  const label = (els.stateName.value || "").trim() || `state ${Object.keys(M.states).length + 1}`;
  let id = slug(label), n = 2;
  while (M.states[id]) id = `${slug(label)}_${n++}`;
  const r = els.canvas.getBoundingClientRect(), k = Object.keys(M.states).length;
  const pos = at || { x: r.width / 2 - W / 2 - view.x + (k % 4) * 24 - 120 + (k % 3) * 60, y: r.height / 2 - H / 2 - view.y + (k % 5) * 30 - 60 };
  M.states[id] = { name: label, x: Math.round(pos.x), y: Math.round(pos.y), anims: [], pick: "random", loop: true };
  if (!M.start) M.start = id;
  els.stateName.value = "";
  sel = { kind: "state", id };
  changed();
}

function addLink(from, to) {
  if (from === to || !M.states[to]) return;
  const id = "l" + Date.now().toString(36);
  M.links.push({ id, from, to, on: "done" });
  sel = { kind: "link", id };
  changed();
}

function removeSel() {
  if (!sel) return;
  if (sel.kind === "state") {
    delete M.states[sel.id];
    M.links = M.links.filter(l => l.from !== sel.id && l.to !== sel.id);
    if (M.start === sel.id) M.start = Object.keys(M.states)[0] || null;
  } else {
    M.links = M.links.filter(l => l.id !== sel.id);
  }
  sel = null;
  changed();
}

function addAnim(sid, aid) {
  const s = M.states[sid];
  if (!s || !anim(aid) || s.anims.includes(aid)) return;
  s.anims.push(aid);
  changed();
}

function onKey(e) {
  if (!root || !sel || /INPUT|TEXTAREA|SELECT/.test(document.activeElement?.tagName)) return;
  if (e.key === "Delete" || e.key === "Backspace") { e.preventDefault(); removeSel(); }
  if (e.key === "Escape") { sel = null; render(); }
}

// ---------------------------------------------------------------------------------- the canvas
function wireCanvas() {
  const c = els.canvas;
  let pan = null;
  c.addEventListener("pointerdown", e => {
    if (e.target !== els.svg && e.target !== c) return;
    pan = { x: e.clientX - view.x, y: e.clientY - view.y, moved: false };
    c.setPointerCapture(e.pointerId);
  });
  c.addEventListener("pointermove", e => {
    if (!pan) return;
    view = { x: e.clientX - pan.x, y: e.clientY - pan.y };
    pan.moved = true;
    els.layer?.setAttribute("transform", `translate(${view.x},${view.y})`);
  });
  c.addEventListener("pointerup", () => {
    if (pan && !pan.moved && sel) { sel = null; render(); }
    pan = null;
  });
  c.addEventListener("dblclick", e => {
    if (e.target !== els.svg) return;
    const r = c.getBoundingClientRect();
    els.stateName.focus();
    if (els.stateName.value.trim()) createState({ x: e.clientX - r.left - view.x - W / 2, y: e.clientY - r.top - view.y - H / 2 });
  });
}

function render() {
  if (!root || !M) return;
  const layer = els.layer = svg("g", { transform: `translate(${view.x},${view.y})` });
  const defs = svg("defs", {},
    svg("marker", { id: "arrow", viewBox: "0 0 10 10", refX: 9, refY: 5, markerWidth: 8, markerHeight: 8, orient: "auto-start-reverse" },
      svg("path", { d: "M0,0 L10,5 L0,10 z", fill: "#4f9a6b" })),
    svg("marker", { id: "arrow-hi", viewBox: "0 0 10 10", refX: 9, refY: 5, markerWidth: 8, markerHeight: 8, orient: "auto-start-reverse" },
      svg("path", { d: "M0,0 L10,5 L0,10 z", fill: "#d4ffe2" })));
  els.svg.replaceChildren(defs, layer);
  for (const ln of M.links) layer.append(drawLink(ln));
  for (const [sid, s] of Object.entries(M.states)) layer.append(drawNode(sid, s));
  els.hint.hidden = Object.keys(M.states).length > 0;
  renderSide();
}

function centre(s) { return { x: s.x + W / 2, y: s.y + H / 2 }; }

function edgePoint(s, toward) {   // where the line from the box's centre to `toward` leaves the box
  const c = centre(s), dx = toward.x - c.x, dy = toward.y - c.y;
  const k = Math.min(Math.abs((W / 2 + 4) / (dx || 1e-6)), Math.abs((H / 2 + 4) / (dy || 1e-6)));
  return { x: c.x + dx * k, y: c.y + dy * k };
}

function drawLink(ln) {
  const a = M.states[ln.from], b = M.states[ln.to];
  const twin = M.links.some(o => o.from === ln.to && o.to === ln.from);
  const ca = centre(a), cb = centre(b), dx = cb.x - ca.x, dy = cb.y - ca.y, len = Math.hypot(dx, dy) || 1;
  const off = twin ? 18 : 0, nx = -dy / len * off, ny = dx / len * off;
  const p = edgePoint(a, { x: cb.x + nx, y: cb.y + ny }), q = edgePoint(b, { x: ca.x + nx, y: ca.y + ny });
  const p2 = { x: p.x + nx, y: p.y + ny }, q2 = { x: q.x + nx, y: q.y + ny };
  const m = { x: (p2.x + q2.x) / 2 + nx, y: (p2.y + q2.y) / 2 + ny };
  const d = `M${p2.x},${p2.y} Q${m.x},${m.y} ${q2.x},${q2.y}`;
  const isSel = sel?.kind === "link" && sel.id === ln.id, isFired = fired === ln.id;
  const label = onText(ln), tw = label.length * 6.6 + 8;
  const g = svg("g", { class: `link${isSel ? " sel" : ""}${isFired ? " fired" : ""}` },
    svg("path", { d, "marker-end": isSel || isFired ? "url(#arrow-hi)" : "url(#arrow)" }),
    svg("path", { d, class: "hit" }),
    svg("rect", { class: "lbl", x: m.x - tw / 2 + (p2.x + q2.x - 2 * m.x) / -4, y: m.y - 9 + (p2.y + q2.y - 2 * m.y) / -4, width: tw, height: 16 }),
    svg("text", { x: m.x + (p2.x + q2.x - 2 * m.x) / -4, y: m.y + 3 + (p2.y + q2.y - 2 * m.y) / -4, "text-anchor": "middle" }, label));
  g.addEventListener("pointerdown", e => { e.stopPropagation(); sel = { kind: "link", id: ln.id }; render(); });
  return g;
}

function drawNode(sid, s) {
  const active = runner?.running && runner.state === sid;
  const isSel = sel?.kind === "state" && sel.id === sid;
  const n = s.anims.length, missing = s.anims.filter(a => !anim(a)).length;
  const sub = n ? `${n} animation${n > 1 ? "s" : ""}${n > 1 ? (s.pick === "order" ? " · in turn" : " · random") : ""}${s.loop ? "" : " · once"}` : "no animation yet";
  const g = svg("g", { class: `node${isSel ? " sel" : ""}${active ? " active" : ""}`, transform: `translate(${s.x},${s.y})` },
    svg("rect", { class: "box", width: W, height: H }),
    M.start === sid ? svg("path", { class: "startmark", d: `M-14,${H / 2 - 7} L-3,${H / 2} L-14,${H / 2 + 7} z` }) : null,
    svg("text", { x: 12, y: 24 }, s.name.length > 19 ? s.name.slice(0, 18) + "…" : s.name),
    svg("text", { x: 12, y: 44, class: "sub" }, missing ? `${sub} · ${missing} missing` : sub));
  if (active && runner.duration) {
    const f = Math.min(1, (runner.elapsed || 0) / runner.duration);
    g.append(svg("rect", { class: "prog", x: 0, y: H - 4, width: W * f, height: 4 }));
  }
  const port = svg("circle", { class: "port", cx: W, cy: H / 2, r: 7 });
  g.append(port);
  // drag the node; a click without a move selects it
  g.addEventListener("pointerdown", e => {
    if (e.target === port) return;
    e.stopPropagation();
    const start = { x: e.clientX, y: e.clientY, sx: s.x, sy: s.y };
    let moved = false;
    const move = ev => {
      const dx = ev.clientX - start.x, dy = ev.clientY - start.y;
      if (!moved && Math.hypot(dx, dy) < 3) return;
      moved = true;
      s.x = Math.round(start.sx + dx); s.y = Math.round(start.sy + dy);
      g.setAttribute("transform", `translate(${s.x},${s.y})`);
    };
    const up = () => {
      window.removeEventListener("pointermove", move);
      window.removeEventListener("pointerup", up);
      if (moved) changed(); else { sel = { kind: "state", id: sid }; render(); }
    };
    window.addEventListener("pointermove", move);
    window.addEventListener("pointerup", up);
  });
  g.addEventListener("dblclick", e => { e.stopPropagation(); if (runner?.running) post("/s/run/goto", { state: sid }); });
  // drag from the port onto another node: an arrow
  port.addEventListener("pointerdown", e => {
    e.stopPropagation();
    const r = els.canvas.getBoundingClientRect();
    const from = { x: s.x + W, y: s.y + H / 2 };
    ghost = svg("path", { class: "ghost" });
    els.layer.append(ghost);
    const move = ev => {
      const x = ev.clientX - r.left - view.x, y = ev.clientY - r.top - view.y;
      ghost.setAttribute("d", `M${from.x},${from.y} L${x},${y}`);
    };
    const up = ev => {
      window.removeEventListener("pointermove", move);
      window.removeEventListener("pointerup", up);
      ghost.remove();
      ghost = null;
      const hit = document.elementFromPoint(ev.clientX, ev.clientY)?.closest?.(".node");
      const to = hit?.dataset.sid;
      if (to) addLink(sid, to);
    };
    window.addEventListener("pointermove", move);
    window.addEventListener("pointerup", up);
  });
  // drop an animation from the library onto the node
  g.dataset.sid = sid;
  g.addEventListener("dragover", e => { if (e.dataTransfer.types.includes("text/x-anim")) { e.preventDefault(); g.classList.add("drop"); } });
  g.addEventListener("dragleave", () => g.classList.remove("drop"));
  g.addEventListener("drop", e => { e.preventDefault(); g.classList.remove("drop"); addAnim(sid, e.dataTransfer.getData("text/x-anim")); sel = { kind: "state", id: sid }; render(); });
  return g;
}

// ---------------------------------------------------------------------------------- the side panel
function renderSide() {
  if (!root || !M) return;
  const parts = [];
  if (sel?.kind === "state" && M.states[sel.id]) parts.push(stateCard(sel.id));
  else if (sel?.kind === "link" && M.links.find(l => l.id === sel.id)) parts.push(linkCard(M.links.find(l => l.id === sel.id)));
  else parts.push(machineCard());
  parts.push(runCard(), libraryCard());
  els.side.replaceChildren(...parts);
}

function machineCard() {
  return h("div", { class: "card" },
    h("div", { class: "card-h" }, h("h2", {}, `machine: ${name}`)),
    h("p", { class: "small muted" }, "Create a state, then drag from its dot onto another state to connect them. Click a state to give it animations; click an arrow to choose when it fires. Double-click a state while running to jump there."),
    problems.length ? h("ul", { class: "problems" }, problems.map(p => h("li", {}, p))) : h("p", { class: "small" }, "No problems."),
    h("div", { class: "row" }, h("button", { class: "danger", onclick: async () => {
      if (!confirm(`Delete the machine "${name}"?`)) return;
      await post(`/s/machine/${encodeURIComponent(name)}/delete`);
      const names = (await get("/s/machines")).names;
      if (!names.length) await post("/s/machine/main/save", { machine: { name: "main", states: {}, links: [] } });
      open(names[0] || "main");
    } }, "delete machine")));
}

function stateCard(sid) {
  const s = M.states[sid];
  const nameIn = h("input", { type: "text", value: s.name, style: { width: "100%" },
                              onchange: e => { s.name = e.target.value.trim() || s.name; changed(); } });
  const now = runner?.running && runner.state === sid ? runner.anim : null;
  const variants = h("ul", { class: "variants" }, s.anims.map((aid, i) => {
    const a = anim(aid);
    return h("li", { class: (a ? "" : "missing ") + (now === aid ? "now" : "") },
      h("span", { class: "title", title: a?.prompt || "" }, a ? a.title : `${aid} (not in the library)`),
      a ? h("span", { class: "small faint" }, `${a.anim.duration.toFixed(1)} s`) : null,
      a ? h("button", { class: "chip", title: "play it now", onclick: () => post(`/s/library/${aid}/play`) }, "▶") : null,
      h("button", { class: "chip danger", title: "take it out of this state", onclick: () => { s.anims.splice(i, 1); changed(); } }, "×"));
  }));
  const drop = h("div", { class: "vdrop" }, "drag animations here from the library below");
  drop.ondragover = e => { if (e.dataTransfer.types.includes("text/x-anim")) { e.preventDefault(); drop.classList.add("over"); } };
  drop.ondragleave = () => drop.classList.remove("over");
  drop.ondrop = e => { e.preventDefault(); drop.classList.remove("over"); addAnim(sid, e.dataTransfer.getData("text/x-anim")); };
  const promptIn = h("textarea", { rows: 2, placeholder: `what he does in ${s.name}, e.g. "bored, looks around, sighs"` });
  const genState = h("span", { class: "small muted" }, "");
  const gen = h("button", { class: "primary", onclick: async () => {
    const p = promptIn.value.trim();
    if (!p) { promptIn.focus(); return; }
    gen.disabled = true;
    genState.textContent = "Claude is writing it…";
    genState.className = "small warnt";
    try {
      const r = await post("/engine/animate", { prompt: p });
      const { entry } = await post("/s/library", { title: r.anim.title, source: "prompt", prompt: p, anim: r.anim });
      await loadLibrary();
      s.anims.push(entry.id);
      changed();
    } catch (e) {
      genState.textContent = e.message;
      genState.className = "small warnt";
      gen.disabled = false;
    }
  } }, "animate into this state");
  const outs = M.links.filter(l => l.from === sid);
  return h("div", { class: "card" },
    h("div", { class: "card-h" }, h("h2", {}, "state"),
      M.start === sid ? h("span", { class: "pill on" }, "start") : h("button", { class: "chip", onclick: () => { M.start = sid; changed(); } }, "start here")),
    nameIn,
    h("div", { class: "row" }, h("h2", {}, `animations (${s.anims.length})`)),
    h("p", { class: "small faint" }, "Each time the state plays, it picks one: more animations, more variety."),
    variants, h("div", { style: { marginTop: "6px" } }, drop),
    h("div", { class: "row" },
      h("label", { class: "inline small" }, "pick ",
        h("select", { onchange: e => { s.pick = e.target.value; changed(); } },
          h("option", { value: "random", selected: s.pick !== "order" }, "at random"),
          h("option", { value: "order", selected: s.pick === "order" }, "in turn"))),
      h("label", { class: "inline small" }, h("input", { type: "checkbox", checked: s.loop, onchange: e => { s.loop = e.target.checked; changed(); } }), "keep playing until an arrow fires")),
    h("div", { class: "row" }, h("h2", {}, "prompt to animate")),
    h("div", { style: { marginTop: "6px" } }, promptIn),
    h("div", { class: "row" }, gen, genState),
    h("div", { class: "row" }, h("h2", {}, `arrows out (${outs.length})`)),
    outs.length ? h("ul", { class: "variants" }, outs.map(l => h("li", {},
      h("span", { class: "title" }, `${onText(l)} → ${M.states[l.to].name}`),
      h("button", { class: "chip", onclick: () => { sel = { kind: "link", id: l.id }; render(); } }, "edit")))) :
      h("p", { class: "small faint" }, "Drag from the state's dot to another state."),
    h("div", { class: "row" }, h("button", { class: "danger", onclick: removeSel }, "delete state")));
}

function linkCard(l) {
  const events = [...new Set([...(S.meta.engine_events || []), "hearing", "visitor", "frank_end", "go",
                              ...M.links.filter(x => x.on === "event").map(x => x.event)])];
  const on = h("select", { onchange: e => {
    l.on = e.target.value;
    if (l.on === "after" && !l.seconds) l.seconds = 5;
    if (l.on === "event" && !l.event) l.event = "arrived";
    changed();
  } }, [["done", "when its animation is done"], ["after", "after some seconds"], ["event", "on an event"]].map(([v, t]) =>
    h("option", { value: v, selected: l.on === v }, t)));
  const extra = l.on === "after"
    ? h("label", { class: "inline" }, h("input", { type: "number", min: 0.1, step: 0.5, value: l.seconds,
        onchange: e => { const v = parseFloat(e.target.value); if (v > 0) { l.seconds = v; changed(); } } }), " seconds in the state")
    : l.on === "event"
      ? h("label", { class: "inline" }, "event ", h("input", { type: "text", list: "sm-events", value: l.event,
          onchange: e => { l.event = e.target.value.trim().toLowerCase().replace(/\s+/g, "_") || "go"; changed(); } }),
          h("datalist", { id: "sm-events" }, events.map(ev => h("option", { value: ev }))))
      : h("p", { class: "small faint" }, "Fires when the animation playing in the state ends.");
  return h("div", { class: "card" },
    h("div", { class: "card-h" }, h("h2", {}, "arrow")),
    h("p", {}, `${M.states[l.from].name} → ${M.states[l.to].name}`),
    h("div", { class: "row" }, on), h("div", { class: "row" }, extra),
    h("div", { class: "row" },
      h("button", { onclick: () => { [l.from, l.to] = [l.to, l.from]; changed(); } }, "reverse"),
      h("button", { class: "danger", onclick: removeSel }, "delete arrow")));
}

function runCard() {
  const evs = [...new Set(M.links.filter(l => l.on === "event").map(l => l.event))];
  const free = h("input", { type: "text", placeholder: "any event", style: { width: "9em" },
                            onkeydown: e => { if (e.key === "Enter" && free.value.trim()) { send(free.value.trim()); free.value = ""; } } });
  els.log = h("ul", { class: "log" });
  els.runInfo = h("p", { class: "small muted" }, "Not running.");
  const card = h("div", { class: "card" },
    h("div", { class: "card-h" }, h("h2", {}, "run")),
    els.runInfo,
    evs.length ? h("div", { class: "buttons" }, evs.map(ev => h("button", { onclick: () => send(ev) }, `send ${ev}`))) : null,
    h("div", { class: "row" }, free, h("button", { onclick: () => free.value.trim() && send(free.value.trim()) }, "send")),
    els.log);
  showRunner();
  return card;
}

function libraryCard() {
  return h("div", { class: "card" },
    h("div", { class: "card-h" }, h("h2", {}, "library"), h("span", { class: "small faint" }, "drag onto a state")),
    h("ul", { class: "lib" }, S.library.map(a => h("li", {
      draggable: true, ondragstart: e => { e.dataTransfer.setData("text/x-anim", a.id); e.dataTransfer.effectAllowed = "copy"; } },
      h("span", { class: "title", title: a.prompt || a.title }, a.title),
      h("span", { class: "small faint" }, `${a.anim.duration.toFixed(1)} s`),
      h("button", { title: "play", onclick: () => post(`/s/library/${a.id}/play`) }, "▶"),
      sel?.kind === "state" ? h("button", { title: "add to the selected state", onclick: () => addAnim(sel.id, a.id) }, "+") : null))),
    S.library.length ? null : h("p", { class: "small muted" }, "Make animations on the Animation studio page."));
}

// ---------------------------------------------------------------------------------- running
async function run() {
  await flush();
  try {
    await post("/s/run/start", { machine: M });
  } catch (e) {
    alert(e.message);
  }
}

async function stop() { await post("/s/run/stop"); }

async function send(ev) {
  const r = await post("/s/run/event", { name: ev }).catch(e => ({ fired: false, why: e.message }));
  if (!r.fired && !runner?.running) els.runInfo.textContent = "Press run first.";
}

function showRunner() {
  if (!els.runInfo) return;
  const r = runner;
  els.run.disabled = !!r?.running;
  els.stop.disabled = !r?.running;
  els.runInfo.textContent = r?.running
    ? `in ${M.states[r.state]?.name || r.state} for ${r.in_state} s` + (r.anim ? `, playing ${anim(r.anim)?.title || r.anim}` : "")
    : "Not running. Run plays the machine on the face, from the start state.";
  els.log.replaceChildren(...(r?.log || []).slice().reverse().map(x => h("li", {}, `${x.t}  ${x.text}`)));
}

export function status(st) {
  if (!root || !M) return;
  const r = st.runner;
  const was = runner;
  runner = r;
  if (r?.running && prevState && r.state !== prevState) {
    const ln = M.links.find(l => l.from === prevState && l.to === r.state);
    fired = ln?.id || null;
    setTimeout(() => { fired = null; if (!ghost) render(); }, 700);
  }
  prevState = r?.running ? r.state : null;
  if (!ghost && (r?.running || was?.running)) render0();   // the active node and its progress bar
  showRunner();
}

function render0() {   // the canvas without the side panel (keeps typing in the side panel)
  if (!root || !M) return;
  const layer = els.layer = svg("g", { transform: `translate(${view.x},${view.y})` });
  els.svg.replaceChildren(els.svg.querySelector("defs") || svg("defs"), layer);
  for (const ln of M.links) layer.append(drawLink(ln));
  for (const [sid, s] of Object.entries(M.states)) layer.append(drawNode(sid, s));
}

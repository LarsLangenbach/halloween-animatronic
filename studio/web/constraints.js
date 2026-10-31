// Step 2, the constraints: the robot's degrees of freedom as its files describe them, at two
// levels. Animation channels are what the face engine moves (range, rest, smoothness, speed);
// servos are the hardware (what each one moves in the CAD rig, which ones share a body, the
// range its board allows, the soft limits and speed the animation must keep to). Every edit
// goes to the running engine at once, so the twin shows it. "try" sliders hold one channel or
// one servo while dragged. Another robot gets perform/onboard's page here: rig, limits, profile.
import { S, h, get, post } from "./app.js";

let C = null, tab = "channels", root = null, live = {};
const GROUPS = { eyes: "eyes", lids: "eyelids", brows: "eyebrows", mouth: "mouth (through mouth.py)" };
const fmt = (x, d = 2) => x == null ? "–" : (+x).toFixed(d).replace(/\.?0+$/, "") || "0";

export async function mount(el) {
  root = el;
  if (S.robot !== "frank") {
    el.append(h("div", { class: "cards" },
      h("div", {}, h("h1", {}, `Constraints: ${S.robot}`),
        h("p", { class: "muted" }, "Rig each servo (click the horn's hub, the parts it turns, each link), sweep it for its hard limits, then set soft limits, speeds and expressive controls. Export writes robots/" + S.robot + "/robot.json, the rig and the GLB.")),
      h("iframe", { class: "onboard-frame", src: `/onboard/?robot=${encodeURIComponent(S.robot)}`, title: "Onboarding: rig and limits" }),
      h("p", { class: "small muted" }, "The animation studio and the state machine run on the face engine, which drives Frank today. A robot onboarded here gets its controls mapped in the onboarding's Controls stage; the engine reading those controls is the next step.")));
    return;
  }
  C = await get("/s/constraints");
  render();
}

export function unmount() { post("/s/hold", { clear: true }).catch(() => {}); root = null; }

async function edit(change) {
  try {
    C = await post("/s/constraints", change);
  } catch (e) {
    alert(e.message);
  }
  render();
}

function num(value, onchange, opts = {}) {
  return h("input", { type: "number", step: opts.step ?? 0.05, min: opts.min, max: opts.max, value: value ?? "",
                      disabled: value == null && !opts.blank, title: opts.title,
                      onchange: e => { const v = parseFloat(e.target.value); if (Number.isFinite(v)) onchange(v); } });
}

function tryer(min, max, rest, hold) {
  const s = h("input", { type: "range", class: "try", min, max, step: (max - min) / 200, value: rest,
                         title: "drag to hold it there; let go to hand it back" });
  s.oninput = () => hold(+s.value);
  s.onpointerup = s.onpointercancel = s.onblur = () => { hold(null); s.value = rest; };
  s.onkeyup = () => { hold(null); s.value = rest; };
  return s;
}

function bar(lo, hi, segs) {
  // a bar from lo to hi with shaded segments [[a, b, cls]] and a "now" tick (live, by key)
  const span = hi - lo || 1, pct = v => `${((v - lo) / span) * 100}%`;
  const el = h("div", { class: "rangebar" });
  for (const [a, b, cls] of segs) if (a != null) el.append(h("div", { class: cls, style: { left: pct(Math.min(a, b)), width: `${Math.abs(b - a) / span * 100}%` } }));
  const now = h("div", { class: "now", style: { left: pct(lo) } });
  el.append(now);
  return { el, set: (v, bad) => { now.style.left = pct(Math.max(lo, Math.min(hi, v))); now.classList.toggle("bad", !!bad); } };
}

function render() {
  if (!root) return;
  live = {};
  const s = C.summary;
  const tabs = h("div", { class: "tabs" }, [["channels", "animation channels"], ["servos", "servos"], ["travel", "travel and poses"]].map(([k, label]) =>
    h("button", { class: tab === k ? "on" : "", onclick: () => { tab = k; render(); } }, label)));
  const body = tab === "channels" ? channels() : tab === "servos" ? servos() : travel();
  root.replaceChildren(h("div", { class: "cards" },
    h("div", {},
      h("h1", {}, `Constraints: ${C.robot}`),
      h("p", { class: "muted" }, `${s.servos} servos on ${Object.keys(C.boards).length} boards, ${s.channels} animation channels, ${s.bodies} moving bodies in the CAD rig; ${s.coupled} servos share a body with another.`),
      h("p", { class: "small faint" }, `Edits apply to the animation at once. Saved in ${C.saved}; soft limits go into robots/frank/robot.json for every tool.`)),
    h("div", { class: "card" }, tabs, body)));
}

function channels() {
  const rows = [];
  let group = null;
  for (const c of C.channels) {
    if (c.group !== group) { group = c.group; rows.push(h("tr", { class: "group" }, h("td", { colspan: 9 }, GROUPS[group] || group))); }
    const b = bar(c.contract[0], c.contract[1], [[c.low, c.high, "soft"]]);
    live[`ch:${c.name}`] = b;
    const angles = c.servos.map(sv => sv.at ? `${sv.id} ${fmt(sv.at[0], 1)}° · ${fmt(sv.at[1], 1)}° · ${fmt(sv.at[2], 1)}°` : sv.id).join(c.servos[0]?.at ? "; " : " ");
    const set = field => v => edit({ channel: c.name, field, value: v });
    rows.push(h("tr", { class: c.edited ? "edited" : "" },
      h("td", {}, h("div", { class: "nm" }, c.label), h("div", { class: "id" }, `${c.name} · ${c.meaning}`)),
      h("td", { class: "nowrap" }, num(c.low, set("low"), { min: c.contract[0], max: c.contract[1] }), " – ", num(c.high, set("high"), { min: c.contract[0], max: c.contract[1] })),
      h("td", {}, num(c.rest, set("rest"), { min: c.low, max: c.high })),
      h("td", {}, num(c.half_life, set("half_life"), { step: 0.01, min: 0, max: 2, title: "spring half-life, s: longer = smoother and slower" })),
      h("td", {}, num(c.speed_cap, set("speed_cap"), { step: 0.5, min: 0.1, max: 100, title: "speed cap, channel units per second" })),
      h("td", { class: "small" }, angles || h("span", { class: "faint" }, "–")),
      h("td", {}, b.el),
      h("td", {}, tryer(c.low, c.high, c.rest, v => post("/s/hold", { channel: c.name, value: v }).catch(() => {}))),
      h("td", {}, c.edited ? h("button", { class: "chip", onclick: () => edit({ reset: c.name }) }, "reset") : "")));
  }
  return h("div", {},
    h("p", { class: "small muted" }, "What the animator moves, 50 times a second. The range is where the animation may take it (inside the engine's own range); the servo angles are at low · rest · high."),
    h("div", { class: "legend" }, h("span", {}, h("i", { style: { background: "var(--faint)" } }), "allowed range"), h("span", {}, h("i", { style: { background: "var(--hi)" } }), "now")),
    h("table", { class: "grid" },
      h("thead", {}, h("tr", {}, ["channel", "range", "rest", "smooth s", "speed /s", "servo angles", "now", "try", ""].map(t => h("th", {}, t)))),
      h("tbody", {}, rows)));
}

function servos() {
  const rows = [];
  let board = null;
  for (const s of C.servos) {
    if (s.board !== board) {
      board = s.board;
      const b = C.boards[board] || {};
      rows.push(h("tr", { class: "group" }, h("td", { colspan: 9 }, `${b.label || board} · ${b.firmware || ""}`)));
    }
    const [flo, fhi] = s.firmware;
    const b = bar(flo, fhi, [[s.soft[0], s.soft[1], "soft"], [s.used?.[0], s.used?.[1], "used"]]);
    live[`sv:${s.id}`] = b;
    const soft = i => v => { const lim = [...s.soft]; lim[i] = v; edit({ servo: s.id, field: "soft", value: lim }); };
    rows.push(h("tr", { class: s.edited ? "edited" : "", "data-sid": s.id },
      h("td", {}, h("div", { class: "nm" }, s.label), h("div", { class: "id" }, `${s.id} · pin ${s.pin} · ${s.type}`)),
      h("td", { class: "small" }, s.moves.join(", ") || h("span", { class: "faint" }, "not in the rig")),
      h("td", { class: "small" }, s.coupled.length ? s.coupled.join(", ") : h("span", { class: "faint" }, "–")),
      h("td", { class: "small" }, `${fmt(flo, 1)}° – ${fmt(fhi, 1)}°`),
      h("td", { class: "nowrap" }, num(s.soft[0], soft(0), { step: 0.5, min: flo, max: fhi }), " – ", num(s.soft[1], soft(1), { step: 0.5, min: flo, max: fhi })),
      h("td", {}, b.el, h("div", { class: "id" }, s.used ? `animation: ${fmt(s.used[0], 1)}° – ${fmt(s.used[1], 1)}°` : "")),
      h("td", {}, num(s.speed, v => edit({ servo: s.id, field: "speed", value: v }), { step: 10, min: 5, max: 2000, title: `deg/s; the ${s.type} datasheet says ${s.speed_default}` })),
      h("td", {}, tryer(flo, fhi, s.zero ?? (flo + fhi) / 2, v => post("/s/hold", { servo: s.id, deg: v }).catch(() => {}))),
      h("td", {}, s.edited ? h("button", { class: "chip", onclick: () => edit({ reset: s.id }) }, "reset") : "")));
  }
  return h("div", {},
    h("p", { class: "small muted" }, "Each servo, in its board program's own degrees. Soft limits clamp where the horn moves: an animation that asks for more holds the servo at the limit, and its row turns red. Shares: servos whose parts meet in one body (the jaw's two servos, the brow bar between its two arms)."),
    h("div", { class: "legend" },
      h("span", {}, h("i", { style: { background: "var(--panel-2)", border: "1px solid var(--faint)" } }), "the board allows"),
      h("span", {}, h("i", { style: { background: "var(--faint)" } }), "soft limits"),
      h("span", {}, h("i", { style: { background: "var(--muted)" } }), "the animation uses"),
      h("span", {}, h("i", { style: { background: "var(--hi)" } }), "now")),
    h("table", { class: "grid" },
      h("thead", {}, h("tr", {}, ["servo", "moves", "shares", "board allows", "soft limits", "range", "speed °/s", "try", ""].map(t => h("th", {}, t)))),
      h("tbody", {}, rows)));
}

function travel() {
  const t = C.travel;
  const field = k => h("tr", {}, h("td", {}, h("div", { class: "nm" }, k), h("div", { class: "id" }, C.travel_doc[k])),
    h("td", {}, num(t[k], v => edit({ travel: k, value: v }), { step: 0.5, min: 0, max: 60 }), " °"));
  const poses = C.poses || {};
  const poseRows = Object.entries(poses).filter(([, v]) => v).map(([k, v]) =>
    h("tr", {}, h("td", { class: "nm" }, k), h("td", { class: "small" }, Object.entries(v).map(([s, a]) => `${s} ${a}°`).join("   "))));
  return h("div", { class: "cols2" },
    h("div", {}, h("p", { class: "small muted" }, "How far one unit of a channel turns its servos."),
      h("table", { class: "grid" }, h("tbody", {}, Object.keys(C.travel_doc).map(field))),
      h("div", { class: "row" }, h("button", { class: "chip", onclick: () => edit({ reset: "travel" }) }, "reset travels"))),
    h("div", {}, h("p", { class: "small muted" }, "The poses saved on the slider window (firmware/eye_poses.json): lids run from shut to open, the eyes around their centre, the brows from level. Change them there, on the real head."),
      h("table", { class: "grid" }, h("tbody", {}, poseRows))));
}

export function status(st) {
  if (!C || !root) return;
  const j = st.snapshot?.joints || {};
  for (const [k, v] of Object.entries(j)) live[`ch:${k}`]?.set(v);
  for (const [sid, s] of Object.entries(st.servos || {})) {
    live[`sv:${sid}`]?.set(s.deg, s.clamped);
    root.querySelector(`tr[data-sid="${sid}"]`)?.classList.toggle("clamped", !!s.clamped);
  }
}

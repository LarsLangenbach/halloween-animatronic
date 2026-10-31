// Step 1, the model: Frank's CAD (already rigged: his servos, linkages and limits are in his
// files), or your own CAD, which perform/onboard converts and rigs (mounted at /onboard/).
import { S, h, get, post, go, useRobot } from "./app.js";

const CAD = ".step,.stp,.stl,.obj,.3mf,.glb,.gltf,.ply";
let timer = null;

export function mount(el) {
  const f = S.robots.frank;
  const frank = h("div", { class: "card choice" },
    h("h2", {}, "use frank's cad"),
    h("div", { class: "big" }, "Frank, the Frankenstein head"),
    h("p", { class: "muted" }, "Will Cogley's Robot Head a2.0.33 with the team's eyes, lids and brows. Already rigged: every servo, linkage and saved pose comes from his files, so the constraints are read straight away."),
    h("dl", { class: "facts" },
      h("dt", {}, "servos"), h("dd", {}, `${f.servos} on ${f.boards} boards`),
      h("dt", {}, "brain"), h("dd", {}, "the face engine: emotion synthesiser, animator, rig"),
      h("dt", {}, "body"), h("dd", {}, "the 3D twin (no head needed)")),
    h("div", { class: "row", style: { marginTop: "auto" } },
      h("button", { class: "primary", onclick: () => { useRobot("frank"); go("constraints"); } }, "use frank →")));

  const name = h("input", { type: "text", placeholder: "robot name, e.g. creature-v2", value: "" });
  const list = h("ul", { class: "files" });
  const msg = h("p", { class: "small muted" }, "STEP is best: it keeps part names and the exact holes and shafts the pivots snap to. STL, OBJ, 3MF, GLB and PLY load too.");
  const next = h("button", { class: "primary", disabled: true }, "rig it →");
  const input = h("input", { type: "file", multiple: true, accept: CAD + ",.pdf,.json,.py,.txt,.md,.png,.jpg", hidden: true });
  const drop = h("div", { class: "drop", tabindex: 0, onclick: () => input.click(),
                          onkeydown: e => { if (e.key === "Enter") input.click(); } },
    "drop CAD files here, or click to choose");
  const upload = async files => {
    const n = name.value.trim();
    if (!n) { msg.textContent = "Give the robot a name first."; msg.className = "small warnt"; name.focus(); return; }
    if (!files.length) return;
    const slug = (await post("/api/robots", { name: n, title: n })).name;   // perform/onboard's workspace
    for (const file of files) {
      list.append(h("li", {}, h("span", {}, file.name), h("span", { class: "muted", id: `up-${file.name}` }, "uploading…")));
      await fetch(`/api/robot/${encodeURIComponent(slug)}/upload?name=${encodeURIComponent(file.name)}`, { method: "POST", body: file });
    }
    watch(slug, list, next, msg);
  };
  input.onchange = () => upload([...input.files]);
  drop.ondragover = e => { e.preventDefault(); drop.classList.add("over"); };
  drop.ondragleave = () => drop.classList.remove("over");
  drop.ondrop = e => { e.preventDefault(); drop.classList.remove("over"); upload([...e.dataTransfer.files]); };

  const mine = h("div", { class: "card choice" },
    h("h2", {}, "upload your cad"),
    h("div", { class: "big" }, "Another animatronic"),
    h("p", { class: "muted" }, "The onboarding tool converts the CAD, asks what the files don't say, and lets you click the mechanism together: each horn, the parts it turns, each link. That gives the twin, the limits and the servo map."),
    h("label", { class: "inline" }, "name ", name), drop, input, list, msg,
    h("div", { class: "row", style: { marginTop: "auto" } }, next));

  const others = S.robots.others.length ? h("div", { class: "card" },
    h("div", { class: "card-h" }, h("h2", {}, "robots already onboarded")),
    h("div", { class: "buttons" }, S.robots.others.map(r =>
      h("button", { onclick: () => { useRobot(r.name); go("constraints"); } }, r.title || r.name)))) : null;

  el.append(h("div", { class: "cards" },
    h("div", {}, h("h1", {}, "Pick the robot"),
      h("p", { class: "muted" }, "Then read its constraints, make animations for it, and wire them into states.")),
    h("div", { class: "cols2" }, frank, mine), others));
}

function watch(slug, list, next, msg) {
  clearInterval(timer);
  const tick = async () => {
    const st = await get(`/api/robot/${encodeURIComponent(slug)}`).catch(() => null);
    if (!st) return;
    list.replaceChildren(...st.files.map(f => h("li", {}, h("span", {}, f.name),
      h("span", { class: f.status === "error" ? "dangert" : "muted" },
        f.status === "working" && f.progress != null ? `converting ${Math.round(f.progress * 100)} %` : f.status))));
    const busy = st.files.some(f => f.status === "queued" || f.status === "working");
    const cad = st.models && st.models.length;
    next.disabled = busy || !cad;
    msg.textContent = busy ? "Converting…" : cad ? "Converted. Next: rig the mechanism and set its limits." : "No CAD in these files yet.";
    msg.className = "small " + (busy ? "warnt" : "muted");
    next.onclick = () => { useRobot(slug); go("constraints"); };
    if (!busy) clearInterval(timer);
  };
  timer = setInterval(tick, 800);
  tick();
}

export function unmount() { clearInterval(timer); }

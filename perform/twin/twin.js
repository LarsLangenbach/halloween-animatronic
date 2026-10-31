// The twin page: the robot's CAD model moving with the servo stream from body.py (/events).
// Robot-agnostic: everything robot-specific comes from /robot (robot.json), /rig (the rig the
// robot's exporter wrote) and /model (its GLB, one node "body:<name>" per body, its parts
// "part:<label>", static layers "layer:<layer>:<name>").
import * as THREE from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";
import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";
import { toCreasedNormals } from "three/addons/utils/BufferGeometryUtils.js";
import { Rig, hornAngle, bendWeight, apply } from "./kinematics.js";

const $ = s => document.querySelector(s);
const el = (tag, cls, text) => { const e = document.createElement(tag); if (cls) e.className = cls; if (text != null) e.textContent = text; return e; };
const CREASE = 35 * Math.PI / 180;      // normals are shared across edges flatter than this
const FAULT_MM = 0.05;                   // a pin further than this from where its links reach is a fault

const S = { frame: null, overrides: {}, selected: null, lastEvent: 0, faults: [] };

// ?hero=1: only the head, one camera looking him in the face from a little below his eyes, swaying
// gently from side to side (&spin=0 holds it still). No panel, no orbit; for an iframe.
const Q = new URLSearchParams(location.search);
const HERO = Q.get("hero") === "1";
const SPIN = HERO && Q.get("spin") !== "0";
const HERO_FOV = 28, HERO_BELOW_DEG = 7, HERO_MARGIN = 1.12;   // deg; how much room round the head
const SWAY_DEG = 14, SWAY_S = 16;                               // side to side, and one sway's period

async function main() {
  const [robot, rigSpec] = await Promise.all([getJSON("/robot"), getJSON("/rig")]);
  const cam = await getJSON("/camera").catch(() => null);
  S.robot = robot; S.rigSpec = rigSpec; S.rig = new Rig(rigSpec);
  $("#title").textContent = `${robot.name} — body twin`;
  document.title = `${robot.name} twin`;

  // ------------------------------------------------------------------ scene
  const view = $("#view");
  const renderer = new THREE.WebGLRenderer({ antialias: true });
  renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
  view.prepend(renderer.domElement);
  const scene = new THREE.Scene();
  scene.background = new THREE.Color(HERO ? 0x0b0c0e : 0x111316);
  const camera = new THREE.PerspectiveCamera(HERO ? HERO_FOV : 35, 1, 5, 20000);
  camera.up.set(...(rigSpec.up || [0, 0, 1]));
  const controls = new OrbitControls(camera, renderer.domElement);
  controls.enableDamping = !HERO;
  controls.enabled = !HERO;
  scene.add(new THREE.HemisphereLight(0xdfe6ee, 0x30281f, 1.6));
  const key = new THREE.DirectionalLight(0xffffff, 2.2); key.position.set(400, 900, 900); scene.add(key);
  const rim = new THREE.DirectionalLight(0x9fb6ff, 0.8); rim.position.set(-600, -500, 500); scene.add(rim);

  const gltf = await new GLTFLoader().loadAsync("/model");
  $("#loading").remove();
  const root = gltf.scene;
  root.updateMatrixWorld(true);
  const bodies = {}, layers = {}, partOf = new Map();
  root.traverse(o => {
    const name = o.userData.name || o.name;
    if (name.startsWith("body:")) { bodies[name.slice(5)] = o; o.matrixAutoUpdate = false; }
    if (o.isMesh) {
      o.geometry = toCreasedNormals(o.geometry, CREASE);
      o.material = o.material.clone();
      o.material.side = THREE.DoubleSide;
      if (name.startsWith("layer:")) {
        const layer = name.split(":")[1];
        (layers[layer] ||= []).push(o);
        o.material.transparent = true; o.material.opacity = layer === "skin" ? 0.35 : 0.22; o.material.depthWrite = false;
      } else {
        const body = o.parent && (o.parent.userData.name || o.parent.name).slice(5);
        const layer = (rigSpec.static[body] || rigSpec.bodies.find(b => b.name === body) || {}).layer || "mech";
        (layers[layer] ||= []).push(o);
        partOf.set(o, { part: name.slice(5), body });
      }
      o.userData.baseEmissive = o.material.emissive.clone();
    }
  });
  scene.add(root);

  // flexible parts: their rest vertices, and each vertex's weight along the part
  const bends = {};
  for (const b of rigSpec.bodies.filter(b => b.motion.type === "bend")) {
    const meshes = [];
    bodies[b.name]?.traverse(o => { if (o.isMesh) meshes.push(o); });
    for (const m of meshes) {
      const pos = m.geometry.attributes.position;
      const rest = Float32Array.from(pos.array), w = new Float32Array(pos.count);
      for (let i = 0; i < pos.count; i++) w[i] = bendWeight([rest[3 * i], rest[3 * i + 1], rest[3 * i + 2]], b.motion.pa, b.motion.pb);
      (bends[b.name] ||= []).push({ mesh: m, rest, w });
    }
  }

  // which bodies each servo moves: turn it alone and see what changes
  const moves = {};
  const restT = S.rig.solve({}).T;
  for (const sid of Object.keys(robot.servos)) {
    const T = S.rig.solve({ [sid]: 10 }).T;
    moves[sid] = Object.keys(T).filter(n => T[n].some((v, i) => Math.abs(v - restT[n][i]) > 1e-6));
  }
  const servoOfBody = {};
  for (const [sid, list] of Object.entries(moves)) for (const n of list) (servoOfBody[n] ||= []).push(sid);

  // the table, the webcam and the gaze: the head in its room
  const box = new THREE.Box3();
  for (const m of [...(layers.mech || []), ...(layers.enclosure || [])]) box.expandByObject(m);
  const grid = new THREE.GridHelper(1600, 32, 0x3a4048, 0x252a30);
  grid.rotation.x = Math.PI / 2; grid.position.z = box.min.z; grid.visible = !HERO; scene.add(grid);
  const eyeMid = (rigSpec.eye_centres || [[0, 0, 0]]).reduce((a, c) => a.map((v, i) => v + c[i] / rigSpec.eye_centres.length), [0, 0, 0]);
  if (cam) {
    const aspect = (cam.width || 16) / (cam.height || 9);
    const vfov = 2 * Math.atan(Math.tan((cam.hfov_deg || 70) * Math.PI / 360) / aspect) * 180 / Math.PI;
    const webcam = new THREE.PerspectiveCamera(vfov, aspect, 30, 1500);
    const p = eyeMid.map((v, i) => v + (cam.offset_mm || [0, 0, 0])[i]);
    webcam.position.set(...p); webcam.up.set(0, 0, 1);
    const t = (cam.tilt_deg || 0) * Math.PI / 180;
    webcam.lookAt(p[0], p[1] + Math.cos(t) * 1000, p[2] - Math.sin(t) * 1000);
    webcam.updateMatrixWorld(true);
    const helper = new THREE.CameraHelper(webcam);
    helper.setColors(new THREE.Color(0x58a6ff), new THREE.Color(0x58a6ff), new THREE.Color(0x58a6ff),
      new THREE.Color(0x2d5a8c), new THREE.Color(0x2d5a8c));
    helper.visible = !HERO;
    scene.add(helper);
  }
  const gazeLines = (rigSpec.gaze || []).map(g => {
    const geo = new THREE.BufferGeometry().setFromPoints([new THREE.Vector3(), new THREE.Vector3()]);
    const line = new THREE.Line(geo, new THREE.LineBasicMaterial({ color: 0xf0b429, transparent: true, opacity: 0.7 }));
    line.visible = !HERO;
    scene.add(line);
    return { g, line };
  });

  // ------------------------------------------------------------------ camera views
  const centre = box.getCenter(new THREE.Vector3());
  const headBox = new THREE.Box3(); for (const m of layers.mech || []) headBox.expandByObject(m);
  const hc = headBox.getCenter(new THREE.Vector3()), hs = headBox.getSize(new THREE.Vector3()).length();
  const VIEWS = {
    "Front": [0, 1, 0.08], "Three-quarter": [0.8, 1, 0.35], "Side": [1, 0, 0.05], "Top": [0, 0.15, 1], "Below": [0.3, 0.9, -0.5],
  };
  const setView = (name, k = 1.6) => {
    const d = new THREE.Vector3(...VIEWS[name]).normalize().multiplyScalar(hs * k);
    camera.position.copy(hc).add(d); controls.target.copy(hc); controls.update();
    for (const b of $("#views").children) b.classList.toggle("on", b.textContent === name);
  };
  for (const name of Object.keys(VIEWS)) {
    const b = el("button", "", name); b.onclick = () => setView(name); $("#views").append(b);
  }
  setView("Three-quarter");

  // hero: the whole head in view, square on, from HERO_BELOW_DEG below a point between its centre and
  // its eyes; refitted every frame, so a resized iframe keeps the head whole
  const hsz = headBox.getSize(new THREE.Vector3());
  const heroTarget = new THREE.Vector3(hc.x, hc.y, (hc.z + eyeMid[2]) / 2);
  const heroCamera = t => {
    const half = Math.tan(camera.fov * Math.PI / 360);
    const tall = Math.max(headBox.max.z - heroTarget.z, heroTarget.z - headBox.min.z) * HERO_MARGIN;
    const dist = Math.max(tall / half, hsz.x / 2 * HERO_MARGIN / (half * camera.aspect)) + hsz.y / 2;
    const yaw = SPIN ? SWAY_DEG * Math.PI / 180 * Math.sin(2 * Math.PI * t / SWAY_S) : 0;
    const down = HERO_BELOW_DEG * Math.PI / 180;
    camera.position.set(heroTarget.x + dist * Math.cos(down) * Math.sin(yaw), heroTarget.y + dist * Math.cos(down) * Math.cos(yaw),
      heroTarget.z - dist * Math.sin(down));
    camera.lookAt(heroTarget);
  };

  // ------------------------------------------------------------------ layers
  const on = new Set(rigSpec.layers_on || Object.keys(rigSpec.layers || {}));
  for (const [key, label] of Object.entries(rigSpec.layers || {})) {
    if (!layers[key]) continue;
    const row = el("label", "layer"); const cb = el("input"); cb.type = "checkbox"; cb.checked = on.has(key);
    const apply = () => layers[key].forEach(m => (m.visible = cb.checked));
    cb.onchange = apply; apply(); row.append(cb, el("span", "", label)); $("#layers").append(row);
  }

  // ------------------------------------------------------------------ servo list
  const rows = {};
  const byBoard = {};
  for (const [sid, s] of Object.entries(robot.servos)) (byBoard[s.board] ||= []).push(sid);
  for (const [board, sids] of Object.entries(byBoard)) {
    $("#servos").append(el("div", "sub", robot.boards[board]?.label || board));
    for (const sid of sids) {
      const r = el("div", "servo"); const dot = el("span", "dot"); const name = el("span", "name", robot.servos[sid].label || sid);
      const deg = el("span", "deg", "—"); const bar = el("div", "bar"); const cmd = el("i", "cmd"), now = el("i", "now");
      bar.append(cmd, now); r.append(dot, name, deg, bar); r.onclick = () => select(sid);
      $("#servos").append(r); rows[sid] = { r, dot, deg, cmd, now };
    }
  }

  // ------------------------------------------------------------------ calibration
  const cal = sid => ({ ...S.robot.servos[sid], ...(S.overrides[sid] || {}) });
  function select(sid) {
    S.selected = S.selected === sid ? null : sid;
    for (const [k, v] of Object.entries(rows)) v.r.classList.toggle("sel", k === S.selected);
    $("#cal").classList.toggle("show", !!S.selected);
    if (S.selected) showCal();
    highlight();
  }
  function showCal() {
    const sid = S.selected, s = S.robot.servos[sid], c = cal(sid);
    $("#calName").textContent = s.label || sid;
    $("#calSock").textContent = `${sid} · ${S.robot.boards[s.board]?.label || s.board} · GP${s.pin} · ${s.type || ""}`;
    $("#calZero").value = c.zero ?? 90;
    $("#calSign").textContent = (c.sign ?? 1) > 0 ? "datasheet (+1)" : "reversed (−1)";
    const dirty = S.overrides[sid] && Object.keys(S.overrides[sid]).length;
    $("#calState").textContent = dirty ? "not saved" : "";
    $("#calState").className = "hint" + (dirty ? " dirty" : "");
  }
  const setOverride = (k, v) => { (S.overrides[S.selected] ||= {})[k] = v; showCal(); };
  $("#calZero").oninput = e => setOverride("zero", parseFloat(e.target.value) || 0);
  for (const b of document.querySelectorAll("#cal [data-step]"))
    b.onclick = () => setOverride("zero", Math.round(((cal(S.selected).zero ?? 90) + parseFloat(b.dataset.step)) * 10) / 10);
  $("#calSign").onclick = () => setOverride("sign", -(cal(S.selected).sign ?? 1));
  $("#calRevert").onclick = () => { delete S.overrides[S.selected]; showCal(); };
  $("#calSave").onclick = async () => {
    const sid = S.selected, body = { [sid]: S.overrides[sid] || {} };
    const r = await fetch("/calibration", { method: "POST", headers: { "X-Perform": "1", "Content-Type": "application/json" }, body: JSON.stringify(body) });
    const j = await r.json();
    if (j.ok) { S.robot.servos = j.servos; delete S.overrides[sid]; showCal(); $("#calState").textContent = "saved"; }
    else $("#calState").textContent = "not saved: " + j.error;
  };

  function highlight() {
    const lit = new Set(S.selected ? moves[S.selected] : []);
    const bad = new Set(S.faultBodies || []);
    for (const [o, info] of partOf) {
      const e = o.material.emissive;
      if (bad.has(info.body)) e.setRGB(0.45, 0.02, 0.02);
      else if (lit.has(info.body)) e.setRGB(0.32, 0.22, 0.0);
      else e.copy(o.userData.baseEmissive);
    }
  }

  // ------------------------------------------------------------------ click: which part is this
  const ray = new THREE.Raycaster(), ptr = new THREE.Vector2();
  let down = null;
  if (!HERO) renderer.domElement.addEventListener("pointerdown", e => (down = [e.clientX, e.clientY]));
  renderer.domElement.addEventListener("pointerup", e => {
    if (!down || Math.hypot(e.clientX - down[0], e.clientY - down[1]) > 4) return;
    const r = renderer.domElement.getBoundingClientRect();
    ptr.set(((e.clientX - r.left) / r.width) * 2 - 1, -((e.clientY - r.top) / r.height) * 2 + 1);
    ray.setFromCamera(ptr, camera);
    const hit = ray.intersectObjects([...partOf.keys()].filter(o => o.visible), false)[0];
    if (!hit) { $("#pick").textContent = ""; return; }
    const info = partOf.get(hit.object), sids = servoOfBody[info.body] || [];
    $("#pick").textContent = `${info.part} · ${info.body}` + (sids.length ? ` · moved by ${sids.join(", ")}` : "");
    if (sids.length === 1 && S.selected !== sids[0]) select(sids[0]);
  });

  // ------------------------------------------------------------------ the stream
  const es = new EventSource("/events");
  es.onmessage = m => {
    const ev = JSON.parse(m.data);
    S.lastEvent = performance.now();
    if (ev.kind === "frame") { S.frame = ev; showFrame(ev); }
    else if (ev.kind === "note") log(ev.text, "note");
  };
  es.onerror = () => { S.lastEvent = 0; };

  function showFrame(f) {
    const ports = Object.entries(f.ports || {}).map(([b, p]) => `${b}: ${p.device}, ${p.programs} program${p.programs === 1 ? "" : "s"}`);
    $("#boards").textContent = Object.entries(f.boards).map(([b, x]) => `${b} runs ${x.firmware}${x.running ? "" : " (stopped)"}`).join(" · ")
      + (ports.length ? " — " + ports.join(" · ") : "");
    for (const ln of f.lines || []) log(`${ln.kind === "reply" ? "← " + ln.board : "→ " + ln.board}  ${ln.text}`, ln.kind);
  }

  const logEl = $("#log");
  function log(text, kind) {
    const atEnd = logEl.scrollTop + logEl.clientHeight >= logEl.scrollHeight - 4;
    const d = el("div", kind || "", text); logEl.append(d);
    while (logEl.childElementCount > 300) logEl.firstChild.remove();
    if (atEnd) logEl.scrollTop = logEl.scrollHeight;
  }

  // ------------------------------------------------------------------ every frame
  const M = new THREE.Matrix4();
  function update() {
    const f = S.frame;
    const horn = {};
    if (f) {
      for (const [sid, s] of Object.entries(f.servos)) {
        const board = f.boards[S.robot.servos[sid]?.board];
        if (!board) continue;
        horn[sid] = hornAngle(s.us, cal(sid), board);
        const row = rows[sid];
        if (row) {
          row.r.classList.toggle("live", s.live);
          row.dot.className = "dot" + (s.live ? " ok" : "");
          row.deg.textContent = s.deg.toFixed(0) + "°";
          const pct = us => Math.max(0, Math.min(100, (us - 500) / 20)) + "%";   // 500..2500 us across
          row.cmd.style.left = pct(s.cmd); row.now.style.left = pct(s.us);
        }
      }
    }
    const sol = S.rig.solve(horn);
    for (const [name, T] of Object.entries(sol.T)) {
      const o = bodies[name];
      if (!o) continue;
      M.set(...T); o.matrix.copy(M); o.matrixWorldNeedsUpdate = true;
    }
    for (const [name, list] of Object.entries(bends)) {
      const { A, B } = sol.bends[name];
      for (const { mesh, rest, w } of list) {
        const pos = mesh.geometry.attributes.position, a = pos.array;
        for (let i = 0; i < pos.count; i++) {
          const v = [rest[3 * i], rest[3 * i + 1], rest[3 * i + 2]];
          const p = apply(A, v), q = apply(B, v), k = w[i];
          a[3 * i] = p[0] + k * (q[0] - p[0]); a[3 * i + 1] = p[1] + k * (q[1] - p[1]); a[3 * i + 2] = p[2] + k * (q[2] - p[2]);
        }
        pos.needsUpdate = true; mesh.geometry.computeVertexNormals(); mesh.geometry.computeBoundingSphere();
      }
    }
    for (const { g, line } of gazeLines) {
      const T = sol.T[g.body]; if (!T) continue;
      const a = apply(T, g.from), d = apply(T, g.from.map((v, i) => v + g.dir[i] * 1500));
      line.geometry.attributes.position.setXYZ(0, ...a); line.geometry.attributes.position.setXYZ(1, ...d);
      line.geometry.attributes.position.needsUpdate = true;
    }
    // faults: a linkage that can't reach is a servo pushing against its own mechanism
    const faults = sol.faults.filter(x => x.gap > FAULT_MM);
    const faultBodies = [];
    for (const x of faults) for (const b of S.rigSpec.bodies) {
      const m = b.motion;
      if (m.type === "link" && (m.a === x.point || m.b === x.point)) faultBodies.push(b.name);
    }
    const faultServos = new Set(faultBodies.flatMap(b => servoOfBody[b] || []));
    for (const [sid, row] of Object.entries(rows)) row.r.classList.toggle("fault", faultServos.has(sid));
    if (faultBodies.join() !== (S.faultBodies || []).join()) { S.faultBodies = faultBodies; highlight(); }
    $("#faultChip").hidden = !faults.length;
    if (faults.length) $("#faultText").textContent = `can't reach: ${[...faultServos].join(", ")} (${Math.max(...faults.map(x => x.gap)).toFixed(1)} mm)`;
    // connection
    const live = performance.now() - S.lastEvent < 1500;
    $("#conn").className = "dot " + (live ? "ok" : "bad");
    $("#connText").textContent = live ? (Object.values(f?.ports || {}).some(p => p.device === "simulated") ? "simulated body" : "following the boards") : "no body server";
  }

  function resize() {
    const r = view.getBoundingClientRect();
    renderer.setSize(r.width, r.height, false);
    camera.aspect = r.width / Math.max(1, r.height); camera.updateProjectionMatrix();
  }
  new ResizeObserver(resize).observe(view); resize();
  renderer.setAnimationLoop(() => {
    update();
    if (HERO) heroCamera(performance.now() / 1000); else controls.update();
    renderer.render(scene, camera);
  });
  window.twin = { S, bodies, moves, setView };      // for poking at in the console
}

async function getJSON(url) {
  const r = await fetch(url);
  if (!r.ok) throw new Error(`${url}: ${r.status}`);
  return r.json();
}

main().catch(e => { const l = $("#loading"); if (l) l.textContent = "Couldn't start: " + e.message; console.error(e); });

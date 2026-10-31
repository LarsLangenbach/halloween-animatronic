/*
  Opens the face demo in headless Edge (or Chrome) and looks at it the way a visitor would.
  Prints one line of JSON: live (Python loaded and the page says "live"), seconds, engine (the
  pill: the real engine, or preview.py's stand-in when the engine didn't import), tags (tag
  buttons), state and strongest after pressing the third tag and Talk, lit (2D face pixels
  drawn), twin (the 3D twin when it is shown: loaded, and how many servos its frames say are
  driven), editor (the State machine tab: its back end's /api/info, and how much the editor drew
  once the tab is opened; the screenshot is taken on that tab) and errors (uncaught exceptions
  and console errors). watch.py decides what passes.
  WebGL runs on SwiftShader, so the check needs no GPU.

    node frank/online/check.mjs <browser.exe> <url> <debugging port> [screenshot.png]
*/
import { spawn } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";

const [browser, url, port, shotPath] = process.argv.slice(2);
const profile = fs.mkdtempSync(path.join(os.tmpdir(), "frank-check-"));
const proc = spawn(browser, ["--headless=new", "--use-angle=swiftshader", "--enable-unsafe-swiftshader",
  "--no-first-run", "--no-default-browser-check",
  `--user-data-dir=${profile}`, `--remote-debugging-port=${port}`, "--window-size=1400,1000", "about:blank"],
  { stdio: "ignore", windowsHide: true });
const out = { live: false, seconds: null, engine: null, tags: 0, state: null, strongest: null, lit: 0, twin: null,
  editor: null, errors: [] };
const wait = (ms) => new Promise((r) => setTimeout(r, ms));
const debug = `http://127.0.0.1:${port}`;
let ws = null;

async function finish(note) {
  if (note) out.errors.push(note);
  try {
    const { webSocketDebuggerUrl } = await (await fetch(`${debug}/json/version`)).json();
    const b = new WebSocket(webSocketDebuggerUrl);
    await new Promise((r) => b.addEventListener("open", r));
    b.send(JSON.stringify({ id: 1, method: "Browser.close" }));
    await wait(1500);
  } catch { /* already gone */ }
  proc.kill();
  console.log(JSON.stringify(out));
  try { fs.rmSync(profile, { recursive: true, force: true, maxRetries: 5, retryDelay: 500 }); } catch { /* the OS cleans tmp */ }
  process.exit(0);
}
setTimeout(() => finish("check timed out"), 180000);

let targets = null;
for (let i = 0; i < 60 && !targets; i++) {
  await wait(250);
  try { targets = (await (await fetch(`${debug}/json`)).json()).filter((t) => t.type === "page"); } catch { /* starting */ }
}
if (!targets || !targets.length) await finish("the browser did not start");

ws = new WebSocket(targets[0].webSocketDebuggerUrl);
await new Promise((r) => ws.addEventListener("open", r));
let id = 0;
const pending = new Map();
ws.addEventListener("message", (m) => {
  const msg = JSON.parse(m.data);
  if (msg.id && pending.has(msg.id)) { pending.get(msg.id)(msg.result || {}); pending.delete(msg.id); }
  if (msg.method === "Runtime.exceptionThrown") {
    const d = msg.params.exceptionDetails;
    out.errors.push((d.exception && d.exception.description) || d.text);
  }
  if (msg.method === "Runtime.consoleAPICalled" && msg.params.type === "error") {
    out.errors.push(msg.params.args.map((a) => a.value ?? a.description ?? "").join(" "));
  }
});
const send = (method, params = {}) => new Promise((r) => { const n = ++id; pending.set(n, r); ws.send(JSON.stringify({ id: n, method, params })); });
const ev = async (expr) => ((await send("Runtime.evaluate", { expression: expr, returnByValue: true, awaitPromise: true })).result || {}).value;
const text = (elId) => ev(`(document.getElementById(${JSON.stringify(elId)}) || {}).textContent || null`);

await send("Runtime.enable");
await send("Emulation.setDeviceMetricsOverride", { width: 1400, height: 1000, deviceScaleFactor: 1, mobile: false });
await send("Page.navigate", { url });
const t0 = Date.now();
while (Date.now() - t0 < 90000) {
  await wait(500);
  const conn = await text("conn");
  if (conn === "live") { out.live = true; break; }
  if (/failed/.test(conn || "")) break;
}
out.seconds = +((Date.now() - t0) / 1000).toFixed(1);
out.engine = await text("engine");
out.tags = await ev("document.querySelectorAll('#tags button').length");
const TWIN = `(() => { const f = document.getElementById("twin");
  if (!f || f.hidden || !f.contentWindow || !f.contentWindow.document) return null;
  const w = f.contentWindow, l = w.document.getElementById("loading");
  const servos = w.twin && w.twin.S.frame ? Object.values(w.twin.S.frame.servos) : [];
  return { loaded: !!w.twin && !l, note: l ? l.textContent : null, driven: servos.filter((s) => s.live).length }; })()`;
if (out.live) {
  for (let i = 0; i < 120; i++) {   // the GLB: up to a minute
    const t = await ev(TWIN);
    if (!t || t.loaded || /Couldn't/.test(t.note || "")) break;
    await wait(500);
  }
  await ev("(document.querySelectorAll('#tags button')[2] || { click() {} }).click()");
  await ev("(document.getElementById('talk') || { click() {} }).click()");
  await wait(2500);
  out.state = await text("state");
  out.strongest = await text("strongest");
  out.lit = await ev(`(() => { const c = document.getElementById("face"); if (!c || !c.width) return 0;
    const d = c.getContext("2d").getImageData(0, 0, c.width, c.height).data; let n = 0;
    for (let i = 0; i < d.length; i += 4) if (d[i] + d[i + 1] + d[i + 2] > 120) n++; return n; })()`);
  out.twin = await ev(TWIN);
  // the State machine tab: its back end answers, and the editor draws the chart in its frame
  out.editor = await ev(`window.frankEditor ? window.frankEditor("GET", "/api/info", "").then((t) => {
    const [s, d] = JSON.parse(t); return { status: s, charts: (d.charts || []).length, vibe: d.vibe }; }) : null`);
  if (out.editor) {
    const EDITOR = `(() => { const f = document.querySelector("iframe[src*='statechart']");
      const d = f && f.contentDocument; if (!d || !d.getElementById("svg")) return null;
      const t = d.getElementById("toast");
      return { drawn: d.getElementById("svg").querySelectorAll("*").length,
               error: t && /err/.test(t.className) ? t.textContent : null }; })()`;
    await ev(`([...document.querySelectorAll("header button")].find((b) => b.textContent === "State machine") || { click() {} }).click()`);
    for (let i = 0; i < 40; i++) {
      await wait(250);
      const p = await ev(EDITOR);
      if (p && p.drawn > 20) break;
    }
    out.editor.page = await ev(EDITOR);
  }
}
if (shotPath) {
  const shot = await send("Page.captureScreenshot", { format: "png" });
  if (shot.data) fs.writeFileSync(shotPath, Buffer.from(shot.data, "base64"));
}
await finish();

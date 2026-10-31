/*
  Opens the face demo in headless Edge (or Chrome) and looks at it the way a visitor would.
  Prints one line of JSON: live (Python loaded and the page says "live"), seconds, engine (the
  pill: the real engine, or preview.py's stand-in when the engine didn't import), tags (tag
  buttons), state and strongest after pressing the third tag and Talk, lit (face pixels drawn)
  and errors (uncaught exceptions and console errors). watch.py decides what passes.

    node frank/online/check.mjs <browser.exe> <url> <debugging port> [screenshot.png]
*/
import { spawn } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";

const [browser, url, port, shotPath] = process.argv.slice(2);
const profile = fs.mkdtempSync(path.join(os.tmpdir(), "frank-check-"));
const proc = spawn(browser, ["--headless=new", "--disable-gpu", "--no-first-run", "--no-default-browser-check",
  `--user-data-dir=${profile}`, `--remote-debugging-port=${port}`, "--window-size=1400,1000", "about:blank"],
  { stdio: "ignore", windowsHide: true });
const out = { live: false, seconds: null, engine: null, tags: 0, state: null, strongest: null, lit: 0, errors: [] };
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
setTimeout(() => finish("check timed out"), 120000);

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
if (out.live) {
  await ev("(document.querySelectorAll('#tags button')[2] || { click() {} }).click()");
  await ev("(document.getElementById('talk') || { click() {} }).click()");
  await wait(2500);
  out.state = await text("state");
  out.strongest = await text("strongest");
  out.lit = await ev(`(() => { const c = document.getElementById("face"); if (!c || !c.width) return 0;
    const d = c.getContext("2d").getImageData(0, 0, c.width, c.height).data; let n = 0;
    for (let i = 0; i < d.length; i += 4) if (d[i] + d[i + 1] + d[i + 2] > 120) n++; return n; })()`);
}
if (shotPath) {
  const shot = await send("Page.captureScreenshot", { format: "png" });
  if (shot.data) fs.writeFileSync(shotPath, Buffer.from(shot.data, "base64"));
}
await finish();

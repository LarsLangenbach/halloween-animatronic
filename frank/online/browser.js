/*
  Frank online: runs the face engine in the page with Pyodide and answers preview.html's
  requests from browser.py, which asks preview.Api, so the page works with no server behind
  it and any route preview.py answers works here too. Loaded in <head>, after pyodide.js and
  before the page's own script, so its fetch() is in place first. files.json (from build.py)
  lists the Python files to copy into Pyodide's file system. It fetches nothing but this site
  and Pyodide. The page's 3D twin is /twin/ here (build.py), fed by window.frankBody(), the
  board models' frames from browser.py (twin_shim.js).

  It also adds the tabs: Face (the page) and State machine (the statechart editor, /statechart/,
  whose /api calls come to window.frankEditor; statechart_shim.js). Charts a visitor saves are
  kept in their browser's localStorage (CHART_KEY + name) and copied into Pyodide's file system
  (saved_charts/) before browser.py loads, which runs the face on them.
*/
(function () {
  "use strict";

  const PYODIDE = "https://cdn.jsdelivr.net/pyodide/v0.27.2/full/";
  const ROOT = "/home/pyodide/";
  const HZ = 50;
  const TWIN_PROBE = { "/robot": "/twin/data/robot.json" };   // the page asks this to see if the twin is up
  const CHART_KEY = "frank-chart:";
  const CHART_NAME = /^[A-Za-z0-9_-]{1,60}$/;
  const realFetch = window.fetch.bind(window);
  window.frankBody = () => null;   // until Python is up

  function say(text, bad) {
    const pill = document.getElementById("conn");
    if (pill) { pill.textContent = text; pill.className = "pill " + (bad ? "danger" : "warn"); }
  }

  function savedCharts() {
    const out = {};
    try {
      for (let i = 0; i < localStorage.length; i++) {
        const k = localStorage.key(i);
        if (k && k.startsWith(CHART_KEY) && CHART_NAME.test(k.slice(CHART_KEY.length))) out[k.slice(CHART_KEY.length)] = localStorage.getItem(k);
      }
    } catch (e) { /* storage blocked: Frank's own charts only */ }
    return out;
  }
  window.frankSaveChart = (name, text) => { try { localStorage.setItem(CHART_KEY + name, text); } catch (e) { /* kept for this visit only */ } };

  let loaded = false;
  const ready = (async () => {
    const py = await loadPyodide({ indexURL: PYODIDE });
    const files = await (await realFetch("/files.json", { cache: "no-store" })).json();
    await Promise.all(files.map(async (f) => {
      const text = await (await realFetch("/" + f, { cache: "no-store" })).text();
      py.FS.mkdirTree(ROOT + f.split("/").slice(0, -1).join("/"));
      py.FS.writeFile(ROOT + f, text);
    }));
    py.FS.mkdirTree(ROOT + "saved_charts");
    for (const [name, text] of Object.entries(savedCharts())) py.FS.writeFile(`${ROOT}saved_charts/${name}.json`, text);
    py.runPython(`import sys; sys.path.insert(0, "${ROOT}frank/online")`);
    const B = py.pyimport("browser");
    setInterval(() => { try { B.tick(); } catch (e) { console.warn("tick", e); } }, 1000 / HZ);
    window.frankBody = () => B.body_frame();
    loaded = true;
    return B;
  })();
  ready.catch((e) => { console.error(e); loaded = true; say("Python failed to load", true); });
  window.frankEditor = async (method, path, body) => (await ready).editor(method, path, body || "");

  window.fetch = async (input, init) => {
    // Pyodide fetches its own files with URL objects, so take any kind of input.
    const url = new URL(input instanceof Request ? input.url : String(input), location.href);
    if (url.origin === new URL(PYODIDE).origin) return realFetch(input, init);
    // Nothing else: the page's 3D twin probe would otherwise reach for the visitor's own 127.0.0.1.
    if (url.origin !== location.origin) throw new TypeError(`the online page fetches nothing from ${url.origin}`);
    if (TWIN_PROBE[url.pathname]) return realFetch(TWIN_PROBE[url.pathname]);
    const B = await ready;
    const post = ((init && init.method) || "GET").toUpperCase() === "POST";
    const answer = JSON.parse(post ? B.post(url.pathname, (init && init.body) || "{}") : B.get(url.pathname));
    if (answer === null) return post ? new Response("not found", { status: 404 }) : realFetch(input, init);
    return new Response(JSON.stringify(answer[1]), { status: answer[0], headers: { "Content-Type": "application/json" } });
  };

  // ----- the tabs: Face (the page as it is) and State machine (the editor, in a frame) -----
  function tabs() {
    const bar = document.createElement("div");
    bar.className = "brand";
    const face = document.createElement("button"), chart = document.createElement("button");
    face.textContent = "Face"; chart.textContent = "State machine";
    const reset = document.createElement("button");
    reset.textContent = "Reset charts"; reset.title = "Forget the charts saved in this browser: Frank's own again";
    reset.hidden = true;
    reset.onclick = () => {
      if (!confirm("Forget the charts you saved in this browser and go back to Frank's own?")) return;
      for (const k of Object.keys(savedCharts())) try { localStorage.removeItem(CHART_KEY + k); } catch (e) { /* nothing kept */ }
      location.reload();
    };
    bar.append(face, chart, reset);
    document.querySelector("header").append(bar);

    const view = document.createElement("div");
    view.hidden = true;
    view.style.cssText = "padding: 0 16px 16px;";
    const frame = document.createElement("iframe");
    frame.title = "Frank's statechart editor";
    frame.style.cssText = "width: 100%; border: 1px solid var(--line); border-radius: var(--radius, 8px); background: var(--bg); display: block;";
    view.append(frame);
    document.querySelector("main").after(view);
    const fit = () => { if (!view.hidden) frame.style.height = Math.max(420, innerHeight - frame.getBoundingClientRect().top - 16) + "px"; };
    addEventListener("resize", fit);

    const show = (which) => {
      const editing = which === "statechart";
      // off-screen, not display: none, so the page's canvases keep their size while it draws on
      document.querySelector("main").style.cssText = editing
        ? "position: absolute; left: -300vw; top: 0; width: 100%; visibility: hidden;" : "";
      view.hidden = !editing;
      reset.hidden = !editing;
      face.classList.toggle("on", !editing);
      chart.classList.toggle("on", editing);
      if (editing && !frame.src) frame.src = "/statechart/index.html";
      // window.history: the page's own script has a global `history` (its chart's samples)
      window.history.replaceState(null, "", editing ? "#statechart" : location.pathname + location.search);
      fit();
    };
    face.onclick = () => show("face");
    chart.onclick = () => show("statechart");
    show(location.hash === "#statechart" ? "statechart" : "face");
  }

  document.addEventListener("DOMContentLoaded", () => {
    const note = document.createElement("div");
    note.className = "small muted";
    note.style.cssText = "padding: 10px 16px; border-bottom: 1px solid var(--line); background: var(--panel-2);";
    note.innerHTML = "Frank is a life-size animatronic Frankenstein head. This is his real face engine " +
      "(Python, <span class=\"mono\">frank/engine</span>) running in your browser through Pyodide: " +
      "no server and no head attached. Fire the tags (keys 1–0), press Talk (T) or Blink (B), " +
      "drag the emotion map and the visitor pad to make him look at you. His conversation states come " +
      "from a statechart: change it in the State machine tab, save, and his face follows it. The 3D head is " +
      "<a href=\"https://willcogley.notion.site/Robot-Head-2-0-33-1d724779b64d80568fd9cf1c7abd3e64\" " +
      "target=\"_blank\" rel=\"noopener\" style=\"color: var(--accent)\">Will Cogley's Robot Head α2.0.33</a>, " +
      "moved servo by servo through models of Frank's two boards.";
    document.querySelector("header").after(note);
    const hint = document.getElementById("twin-note");   // "run perform/body.py": not online
    if (hint) hint.hidden = true;
    tabs();
    if (!loaded) say("loading Python…");
  });
})();

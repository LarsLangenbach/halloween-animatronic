/*
  Frank online: runs the face engine in the page with Pyodide and answers preview.html's
  requests from browser.py, which asks preview.Api, so the page works with no server behind
  it and any route preview.py answers works here too. Loaded in <head>, after pyodide.js and
  before the page's own script, so its fetch() is in place first. files.json (from build.py)
  lists the Python files to copy into Pyodide's file system. It fetches nothing but this site
  and Pyodide, so the page's 3D twin (perform/body.py on 127.0.0.1) stays off.
*/
(function () {
  "use strict";

  const PYODIDE = "https://cdn.jsdelivr.net/pyodide/v0.27.2/full/";
  const ROOT = "/home/pyodide/";
  const HZ = 50;
  const realFetch = window.fetch.bind(window);

  function say(text, bad) {
    const pill = document.getElementById("conn");
    if (pill) { pill.textContent = text; pill.className = "pill " + (bad ? "danger" : "warn"); }
  }

  let loaded = false;
  const ready = (async () => {
    const py = await loadPyodide({ indexURL: PYODIDE });
    const files = await (await realFetch("/files.json", { cache: "no-store" })).json();
    await Promise.all(files.map(async (f) => {
      const text = await (await realFetch("/" + f, { cache: "no-store" })).text();
      py.FS.mkdirTree(ROOT + f.split("/").slice(0, -1).join("/"));
      py.FS.writeFile(ROOT + f, text);
    }));
    py.runPython(`import sys; sys.path.insert(0, "${ROOT}frank/online")`);
    const B = py.pyimport("browser");
    setInterval(() => { try { B.tick(); } catch (e) { console.warn("tick", e); } }, 1000 / HZ);
    loaded = true;
    return B;
  })();
  ready.catch((e) => { console.error(e); loaded = true; say("Python failed to load", true); });

  window.fetch = async (input, init) => {
    // Pyodide fetches its own files with URL objects, so take any kind of input.
    const url = new URL(input instanceof Request ? input.url : String(input), location.href);
    if (url.origin === new URL(PYODIDE).origin) return realFetch(input, init);
    // Nothing else: the page's 3D twin probe would otherwise reach for the visitor's own 127.0.0.1.
    if (url.origin !== location.origin) throw new TypeError(`the online page fetches nothing from ${url.origin}`);
    const B = await ready;
    const post = ((init && init.method) || "GET").toUpperCase() === "POST";
    const answer = JSON.parse(post ? B.post(url.pathname, (init && init.body) || "{}") : B.get(url.pathname));
    if (answer === null) return post ? new Response("not found", { status: 404 }) : realFetch(input, init);
    return new Response(JSON.stringify(answer[1]), { status: answer[0], headers: { "Content-Type": "application/json" } });
  };

  document.addEventListener("DOMContentLoaded", () => {
    const note = document.createElement("div");
    note.className = "small muted";
    note.style.cssText = "padding: 10px 16px; border-bottom: 1px solid var(--line); background: var(--panel-2);";
    note.innerHTML = "Frank is a life-size animatronic Frankenstein head. This is his real face engine " +
      "(Python, <span class=\"mono\">frank/engine</span>) running in your browser through Pyodide: " +
      "no server and no head attached. Fire the tags (keys 1–0), press Talk (T) or Blink (B), " +
      "drag the emotion map and the visitor pad to make him look at you.";
    document.querySelector("header").after(note);
    for (const id of ["stage-mode", "twin-note"]) {   // the 3D twin is Cogley's head: local only
      const el = document.getElementById(id);
      if (el) el.hidden = true;
    }
    if (!loaded) say("loading Python…");
  });
})();

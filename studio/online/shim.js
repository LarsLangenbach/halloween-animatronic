/*
  The studio online: runs studio/online/web.py and Frank's engine with Pyodide and answers the
  page's /s/... and /engine/... requests from it, so the page works with no server behind it.
  Loaded in <head>, after pyodide.js and before the page's own script. files.json (from build.py)
  lists the Python and data files to copy into Pyodide's file system. The 3D twin (/twin/, with
  frank/online/twin_shim.js) reads the board models' frames from window.frankBody().

  A visitor's saves (robots/frank/studio/... and the soft limits in robot.json) are copied into
  localStorage after every change and back into Pyodide before Python starts.
*/
(function () {
  "use strict";

  const PYODIDE = "https://cdn.jsdelivr.net/pyodide/v0.27.2/full/";
  const ROOT = "/home/pyodide/";
  const HZ = 50;
  const KEEP = "studio-file:";
  const KEPT = /^robots\/frank\/(robot\.json|studio\/[A-Za-z0-9_./-]+\.json)$/;
  const realFetch = window.fetch.bind(window);
  window.frankBody = () => null;   // until Python is up

  function kept() {
    const out = {};
    try {
      for (let i = 0; i < localStorage.length; i++) {
        const k = localStorage.key(i);
        if (k && k.startsWith(KEEP) && KEPT.test(k.slice(KEEP.length))) out[k.slice(KEEP.length)] = localStorage.getItem(k);
      }
    } catch (e) { /* storage blocked: this visit only */ }
    return out;
  }

  let py = null;
  function keep() {   // the saved files, into this browser
    const walk = dir => {
      let names = [];
      try { names = py.FS.readdir(ROOT + dir).filter(n => n !== "." && n !== ".."); } catch (e) { return; }
      for (const n of names) {
        const rel = `${dir}/${n}`, st = py.FS.stat(ROOT + rel);
        if (py.FS.isDir(st.mode)) walk(rel);
        else if (KEPT.test(rel)) try { localStorage.setItem(KEEP + rel, py.FS.readFile(ROOT + rel, { encoding: "utf8" })); } catch (e) { /* full or blocked */ }
      }
    };
    walk("robots/frank/studio");
    try { localStorage.setItem(KEEP + "robots/frank/robot.json", py.FS.readFile(ROOT + "robots/frank/robot.json", { encoding: "utf8" })); } catch (e) { /* blocked */ }
  }

  const ready = (async () => {
    py = await loadPyodide({ indexURL: PYODIDE });
    const files = await (await realFetch("/files.json", { cache: "no-store" })).json();
    await Promise.all(files.map(async f => {
      const text = await (await realFetch("/" + f, { cache: "no-store" })).text();
      py.FS.mkdirTree(ROOT + f.split("/").slice(0, -1).join("/"));
      py.FS.writeFile(ROOT + f, text);
    }));
    for (const [rel, text] of Object.entries(kept())) {
      py.FS.mkdirTree(ROOT + rel.split("/").slice(0, -1).join("/"));
      py.FS.writeFile(ROOT + rel, text);
    }
    py.runPython(`import sys; sys.path.insert(0, "${ROOT}studio/online")`);
    const W = py.pyimport("web");
    setInterval(() => { try { W.tick(); } catch (e) { console.warn("tick", e); } }, 1000 / HZ);
    window.frankBody = () => W.body_frame();
    return W;
  })();
  ready.catch(e => {
    console.error(e);
    const pill = document.getElementById("conn");
    if (pill) { pill.textContent = "Python failed to load"; pill.className = "pill warn"; }
  });

  window.fetch = async (input, init) => {
    const url = new URL(input instanceof Request ? input.url : String(input), location.href);
    if (url.origin !== location.origin) return realFetch(input, init);   // Pyodide's own files
    const path = decodeURIComponent(url.pathname);
    if (path.startsWith("/api/")) {
      return new Response(JSON.stringify({ ok: false, why: "Uploading CAD needs the laptop app (studio/app.py): it converts STEP with build123d." }),
                          { status: 501, headers: { "Content-Type": "application/json" } });
    }
    if (!path.startsWith("/s/") && !path.startsWith("/engine/")) return realFetch(input, init);
    const W = await ready;
    const method = ((init && init.method) || "GET").toUpperCase();
    const answer = JSON.parse(W.handle(method, path, (init && init.body) || ""));
    if (answer === null) return new Response("not found", { status: 404 });
    if (method === "POST" && answer[0] < 300 && !path.startsWith("/s/run/") && !path.startsWith("/s/hold")) keep();
    return new Response(JSON.stringify(answer[1]), { status: answer[0], headers: { "Content-Type": "application/json" } });
  };
})();

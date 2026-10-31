/*
  Frank online: the 3D twin (perform/twin) without perform/body.py. Loaded in the twin page's
  <head>, before twin.js. Its GETs for /robot, /rig, /camera and /model come from the files
  build.py copied into /twin/data/; its /events stream becomes a frame every 33 ms from the
  board models running in the parent page's Python (browser.py body_frame()). Calibration is
  read-only here: nothing is saved online.
*/
(function () {
  "use strict";

  const FILES = { "/robot": "/twin/data/robot.json", "/rig": "/twin/data/rig.json",
    "/camera": "/twin/data/camera.json", "/model": "/twin/data/model.glb" };
  const FRAME_MS = 1000 / 30;
  const realFetch = window.fetch.bind(window);

  window.fetch = async (input, init) => {
    const url = new URL(input instanceof Request ? input.url : String(input), location.href);
    if (url.origin === location.origin && FILES[url.pathname]) return realFetch(FILES[url.pathname]);
    if (url.origin === location.origin && url.pathname === "/calibration") {
      return new Response(JSON.stringify({ ok: false, error: "read-only online" }), { headers: { "Content-Type": "application/json" } });
    }
    return realFetch(input, init);
  };

  window.EventSource = class {
    constructor() {
      this.onmessage = null;
      this.onerror = null;
      this.timer = setInterval(() => {
        let data = null;
        try { data = window.parent.frankBody && window.parent.frankBody(); } catch (e) { /* the parent is loading */ }
        if (data && this.onmessage) this.onmessage({ data });
      }, FRAME_MS);
    }
    close() { clearInterval(this.timer); }
  };
})();

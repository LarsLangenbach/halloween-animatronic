/*
  Frank online: the statechart editor (frank/statechart/editor.html) without editor.py. Loaded
  in the editor page's <head>. Its /api/... calls go to statechart.api.handle in the parent
  page's Python (browser.js frankEditor), which also runs the face on the chart saved last.
  Asking Claude needs an API key, so the Vibe tab says it is not available online. RETRO puts
  the site's green terminal colours (preview.html's :root) on the editor's own variables.
*/
(function () {
  "use strict";

  if (window.parent === window) { location.replace("/#statechart"); return; }   // only inside the site
  const realFetch = window.fetch.bind(window);

  const RETRO = `html:root:not([data-retro-off]) {
    --bg:#020704; --panel:#040b06; --ink:#7cf0a0; --muted:#4f9a6b; --line:#2b6542; --soft:#08150c;
    --accent:#7cf0a0; --sel:#5ad1e6; --ok:#7cf0a0; --warn:#ffc857; --err:#ff5a4a;
    --dot:#123321; --state:#040b06; --box:#06100a; --active:#7cf0a0; --fired:#ffc857; --add:#7cf0a0; --chg:#ffc857;
    color-scheme: dark; }
  body { font: 13px/1.5 ui-monospace, Menlo, Monaco, "Cascadia Mono", Consolas, "Courier New", monospace; }
  button { border-radius: 0; }
  button.primary { color: #021006; }`;
  const style = document.createElement("style");
  style.textContent = RETRO;
  document.head.append(style);   // after the editor's own <style>, so these win

  window.fetch = async (input, init) => {
    const url = new URL(input instanceof Request ? input.url : String(input), location.href);
    if (url.origin !== location.origin || !url.pathname.startsWith("/api/")) return realFetch(input, init);
    const method = ((init && init.method) || "GET").toUpperCase();
    const [status, data] = JSON.parse(await window.parent.frankEditor(method, url.pathname, (init && init.body) || ""));
    if (status >= 400 && data && !data.error && data.why) data.error = data.why;
    return new Response(JSON.stringify(data), { status, headers: { "Content-Type": "application/json" } });
  };

  const OFF = "Asking Claude is not available online: it needs an API key, so it runs only in the " +
    "editor on Frank's laptop. Everything else works here: draw, simulate and save, and the face " +
    "on the Face tab follows the chart you save (kept in this browser only).";
  new MutationObserver(() => {
    for (const p of document.querySelectorAll("#p-vibe p.muted")) {
      if (p.textContent.startsWith("Asking Claude is off")) p.textContent = OFF;
    }
  }).observe(document.documentElement, { childList: true, subtree: true });
})();

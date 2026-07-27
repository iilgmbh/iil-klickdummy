/**
 * kd-nav.js — Hauptmenü-Link + optionaler Tour-Mode.
 *
 * In jeden Klickdummy einbinden via:
 *   <script src="<rel>/_shared/kd-nav.js"
 *           data-sitemap="<rel>/index.html"
 *           data-spec-id="<spec_id>"></script>
 *
 * Liest:
 *   - data-sitemap : relativer Pfad zur Sitemap (klickdummy/index.html)
 *   - data-spec-id : eigene Spec-ID; nur für Tour-Positionsbestimmung relevant
 *
 * Standard-Modus (ohne ?tour=1):
 *   - fügt einen festen Floating-Button "⌂ Hauptmenü" oben rechts ein
 *
 * Tour-Modus (mit ?tour=1):
 *   - lädt _shared/kd-tree.json (depth-first Reihenfolge)
 *   - blendet zusätzlich einen festen Tour-Footer ein:
 *       ← Tour-Schritt N-1   (Pos M/Total)   → Tour-Schritt N+1   × Tour beenden
 *   - prev/next halten ?tour=1 am href; "Tour beenden" entfernt es
 *
 * Konvention: keine externe Library; nur natives DOM.
 */
(function () {
  "use strict";

  const script = document.currentScript;
  if (!script) return;
  const sitemapHref = script.getAttribute("data-sitemap") || "index.html";
  const specId = script.getAttribute("data-spec-id") || "";
  const sharedDir = (function () {
    // ableiten: <prefix>/_shared/kd-nav.js → <prefix>/_shared/
    const src = script.getAttribute("src") || "";
    return src.replace(/kd-nav\.js$/, "");
  })();
  const treeJsUrl = sharedDir + "kd-tree.js";

  const isTour = (function () {
    try {
      return new URLSearchParams(window.location.search).get("tour") === "1";
    } catch (_e) {
      return false;
    }
  })();

  // --- Hauptmenü-Button (immer sichtbar) ---
  function injectHauptmenu() {
    const a = document.createElement("a");
    a.href = sitemapHref;
    a.setAttribute("data-testid", "nav-hauptmenu");
    a.textContent = "⌂ Hauptmenü";
    a.style.cssText = [
      "position:fixed",
      "top:8px",
      "right:8px",
      "z-index:9999",
      "padding:4px 10px",
      "background:#1f2937",
      "color:#fff",
      "border-radius:6px",
      "text-decoration:none",
      "font:600 11px/1.2 system-ui,sans-serif",
      "box-shadow:0 1px 3px rgba(0,0,0,0.2)",
    ].join(";");
    a.addEventListener("mouseenter", () => (a.style.background = "#374151"));
    a.addEventListener("mouseleave", () => (a.style.background = "#1f2937"));
    document.body.appendChild(a);
  }

  // --- Zurück-Link (history-aware, history.length > 1) ---
  function injectBackButton() {
    if (window.history.length <= 1) return; // keine Vorgängerseite
    const b = document.createElement("button");
    b.setAttribute("data-testid", "nav-back");
    b.textContent = "← Zurück";
    b.style.cssText = [
      "position:fixed",
      "top:8px",
      "right:110px",
      "z-index:9999",
      "padding:4px 10px",
      "background:#4b5563",
      "color:#fff",
      "border:0",
      "border-radius:6px",
      "cursor:pointer",
      "font:600 11px/1.2 system-ui,sans-serif",
      "box-shadow:0 1px 3px rgba(0,0,0,0.2)",
    ].join(";");
    b.addEventListener("click", () => window.history.back());
    document.body.appendChild(b);
  }

  // --- Tour-Mode ---
  function injectTourFooter(tree) {
    const order = (tree && tree.order) || [];
    const nodes = (tree && tree.nodes) || {};
    let pos = order.indexOf(specId);
    // Falls Spec-ID nicht in Tour-Reihenfolge: am Anfang einsteigen
    if (pos < 0) pos = 0;
    const prevId = pos > 0 ? order[pos - 1] : null;
    const nextId = pos < order.length - 1 ? order[pos + 1] : null;

    const tourOn = (rel) => {
      if (!rel) return null;
      const sep = rel.indexOf("?") >= 0 ? "&" : "?";
      return rel + sep + "tour=1";
    };

    // Pfad zu einem anderen Node, ausgehend von kd-tree.json-Wurzel klickdummy/
    // Wir liegen aktuell bei "currentDir/" → Sitemap liegt bei sitemapHref → klickdummy/-Wurzel.
    // Pfade in tree.json sind relativ zur klickdummy/-Wurzel.
    function nodePath(id) {
      const node = nodes[id];
      if (!node) return null;
      const sitemapDir = sitemapHref.replace(/index\.html$/, ""); // "" oder "../" etc.
      return sitemapDir + node.path;
    }

    const bar = document.createElement("div");
    bar.setAttribute("data-testid", "tour-footer");
    bar.style.cssText = [
      "position:fixed",
      "left:0",
      "right:0",
      "bottom:0",
      "z-index:9998",
      "padding:8px 16px",
      "background:#312e81",
      "color:#fff",
      "display:flex",
      "align-items:center",
      "gap:12px",
      "font:600 12px/1.4 system-ui,sans-serif",
      "box-shadow:0 -2px 8px rgba(0,0,0,0.25)",
    ].join(";");

    const prevHref = prevId ? tourOn(nodePath(prevId)) : null;
    const nextHref = nextId ? tourOn(nodePath(nextId)) : null;
    const currentTitle = (nodes[specId] && nodes[specId].title) || specId || "(unbekannt)";

    bar.innerHTML =
      `<span style="background:#fbbf24;color:#1f2937;padding:2px 6px;border-radius:4px;font-size:10px;">TOUR</span>` +
      `<span style="opacity:0.85;font-weight:400;" data-testid="tour-pos">Schritt ${pos + 1} / ${order.length}</span>` +
      `<span style="flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;" data-testid="tour-title">${currentTitle}</span>` +
      (prevHref
        ? `<a href="${prevHref}" data-testid="tour-prev" style="color:#fff;text-decoration:none;padding:4px 10px;background:#4338ca;border-radius:4px;">← Zurück</a>`
        : `<span data-testid="tour-prev" style="opacity:0.4;padding:4px 10px;">← Zurück</span>`) +
      (nextHref
        ? `<a href="${nextHref}" data-testid="tour-next" style="color:#fff;text-decoration:none;padding:4px 10px;background:#4338ca;border-radius:4px;">Weiter →</a>`
        : `<span data-testid="tour-next" style="opacity:0.4;padding:4px 10px;">Weiter →</span>`) +
      `<a href="${sitemapHref}" data-testid="tour-exit" style="color:#fff;text-decoration:none;padding:4px 10px;background:#dc2626;border-radius:4px;">× Tour beenden</a>`;
    document.body.appendChild(bar);

    // Body etwas Luft am Fuß geben, damit der Footer nichts überdeckt
    document.body.style.paddingBottom = "56px";
  }

  function loadTree(cb) {
    if (window.__KD_TREE__) {
      cb(window.__KD_TREE__);
      return;
    }
    // <script src> statt fetch() — file://-Browser blockt fetch auf lokale Dateien.
    const s = document.createElement("script");
    s.src = treeJsUrl;
    s.onload = () => cb(window.__KD_TREE__ || null);
    s.onerror = () => cb(null);
    document.head.appendChild(s);
  }

  function init() {
    injectHauptmenu();
    injectBackButton();
    if (isTour) {
      loadTree((tree) => {
        if (tree) injectTourFooter(tree);
      });
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();

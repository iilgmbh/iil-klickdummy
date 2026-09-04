/**
 * tailwind-tokens.js — mappt jede Tailwind-Farbfamilie (Play-CDN,
 * `_shared/tailwind.js`) auf `var(--kd-*)`-Tokens, BEVOR `tailwind.js`
 * geladen wird (dev-hub#320 Welle 4, iilgmbh/iil-klickdummy#232-Analogie).
 *
 * Hintergrund: vendorte Tailwind-Klickdummies (z. B. risk-hub, 24 KD auf
 * einem lokalen Play-CDN-Build) nutzen Tailwind-Utility-Farbklassen wie
 * `bg-indigo-700` — I5 Regel 2 verbietet das grundsätzlich (Farben nur aus
 * `var(--kd-*)`, keine zweite unkontrollierte Farbquelle im Markup). Dieses
 * Snippet löst den Widerspruch NICHT durch Regel-Aufweichung, sondern durch
 * echtes Token-Mapping: jede Tailwind-Palette-Farbe zeigt auf ein
 * `var(--kd-*)`-Token, sodass `bg-indigo-700` zur Laufzeit exakt dieselbe
 * Farbe zeichnet wie `var(--kd-primary)` — `check_i5.py` erkennt dieses
 * Mapping (Familien-Scan, s. dort) und lässt Tailwind-Farbklassen dann
 * durchgehen.
 *
 * Einbindung IMMER vor tailwind.js (Tailwind Play-CDN liest
 * `window.tailwind.config` beim Laden des Scripts, nicht danach):
 *   <script src="_shared/tailwind-tokens.js"></script>
 *   <script src="_shared/tailwind.js"></script>
 *
 * Mapping-Tabelle (Familie → Ziel-Tokens nach Shade-Schwelle):
 *
 *   Marken-Familien (indigo, blue, sky, violet, purple)
 *     50–300   → --kd-accent-1
 *     400–600  → --kd-primary
 *     700–950  → --kd-primary-dark
 *
 *   Grau-Familien (slate, gray, zinc, neutral, stone)
 *     50–100   → --kd-bg-light
 *     200      → --kd-zebra
 *     300      → --kd-border
 *     400      → --kd-line
 *     500–600  → --kd-text-muted
 *     700–950  → --kd-text
 *
 *   Status-Familien (Fallback-Kette auf ein Kern-Token, falls das Profil das
 *   optionale Status-Token nicht liefert — CSS-Fallback-Syntax
 *   `var(--kd-success, var(--kd-accent-2))`, nie ein Hex im Snippet):
 *     green, emerald, lime, teal   → --kd-success, sonst --kd-accent-2
 *     amber, yellow, orange        → --kd-warning, sonst --kd-accent-1
 *     red, rose, pink, fuchsia     → --kd-danger,  sonst --kd-primary-dark
 *     cyan                         → --kd-info,    sonst --kd-accent-1
 *
 * `check_i5.py` (Regel 2, Welle-4-Ausnahme) verlangt: jede in den geprüften
 * HTML-Dateien TATSÄCHLICH verwendete Tailwind-Farbfamilie muss hier als
 * Objekt-Schlüssel auftauchen (`<familie>: ...`) UND die Datei muss
 * insgesamt `var(--kd-` enthalten — sonst gilt die Familie als nicht
 * token-gemappt (Fehler mit Familienname). Deshalb bewusst KEINE
 * Kurzschreibweise, die Familiennamen dynamisch zusammensetzt.
 */
(function () {
  "use strict";

  // Tailwind-Standard-Shades (Play-CDN-Default-Palette).
  var SHADES = [50, 100, 200, 300, 400, 500, 600, 700, 800, 900, 950];

  // Baut ein Shade→Token-Objekt aus aufsteigenden [maxShade, tokenExpr]-Regeln
  // (letzte Regel ist der Fallback für alle größeren Shades).
  function shadeMap(rules) {
    var out = {};
    SHADES.forEach(function (shade) {
      for (var i = 0; i < rules.length; i++) {
        if (shade <= rules[i][0]) {
          out[shade] = rules[i][1];
          return;
        }
      }
      out[shade] = rules[rules.length - 1][1];
    });
    return out;
  }

  var MARKE = shadeMap([
    [300, "var(--kd-accent-1)"],
    [600, "var(--kd-primary)"],
    [950, "var(--kd-primary-dark)"],
  ]);
  var GRAU = shadeMap([
    [100, "var(--kd-bg-light)"],
    [200, "var(--kd-zebra)"],
    [300, "var(--kd-border)"],
    [400, "var(--kd-line)"],
    [600, "var(--kd-text-muted)"],
    [950, "var(--kd-text)"],
  ]);
  var ERFOLG = shadeMap([[950, "var(--kd-success, var(--kd-accent-2))"]]);
  var WARNUNG = shadeMap([[950, "var(--kd-warning, var(--kd-accent-1))"]]);
  var FEHLER = shadeMap([[950, "var(--kd-danger, var(--kd-primary-dark))"]]);
  var INFO = shadeMap([[950, "var(--kd-info, var(--kd-accent-1))"]]);

  var colors = {
    // Marken-Familien
    indigo: MARKE,
    blue: MARKE,
    sky: MARKE,
    violet: MARKE,
    purple: MARKE,
    // Grau-Familien
    slate: GRAU,
    gray: GRAU,
    zinc: GRAU,
    neutral: GRAU,
    stone: GRAU,
    // Status: Erfolg
    green: ERFOLG,
    emerald: ERFOLG,
    lime: ERFOLG,
    teal: ERFOLG,
    // Status: Warnung
    amber: WARNUNG,
    yellow: WARNUNG,
    orange: WARNUNG,
    // Status: Fehler
    red: FEHLER,
    rose: FEHLER,
    pink: FEHLER,
    fuchsia: FEHLER,
    // Status: Info
    cyan: INFO,
  };

  window.tailwind = window.tailwind || {};
  window.tailwind.config = window.tailwind.config || {};
  window.tailwind.config.theme = window.tailwind.config.theme || {};
  window.tailwind.config.theme.extend = window.tailwind.config.theme.extend || {};
  window.tailwind.config.theme.extend.colors = Object.assign(
    {},
    window.tailwind.config.theme.extend.colors || {},
    colors
  );
})();

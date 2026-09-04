/**
 * tailwind-tokens.js — mappt jede Tailwind-Farbfamilie (Play-CDN,
 * `_shared/tailwind.js`) auf `var(--kd-*)`-Tokens (dev-hub#320 Welle 4,
 * iilgmbh/iil-klickdummy#232-Analogie).
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
 * Einbindung — Reihenfolge zu `tailwind.js` ist seit #241 EGAL (s. u.),
 * empfohlen bleibt trotzdem "davor" für Lesbarkeit im Markup:
 *   <script src="_shared/tailwind-tokens.js"></script>
 *   <script src="_shared/tailwind.js"></script>
 *
 * ABWEICHUNG von 1.40.0 (iilgmbh/iil-klickdummy#238, #241,
 * risk-hub#736, dev-hub#320 Welle 4 Folgebefunde):
 *
 * (1) #238 — Kontrast: die 1.40.0-Karte hatte zwei Bugs, per Playwright in
 * risk-hub verifiziert (dsb-vorfaelle: Status-Spalte komplett unsichtbar) —
 * (a) Marken-Familien mappten Shade 50–300 auf `--kd-accent-1`, einen im
 * Profil "iil-extern" DUNKLEN Ton, wodurch das Idiom
 * `bg-indigo-100 text-indigo-700` (heller Chip + dunkler Text) zu
 * dunkel-auf-dunkel wurde; (b) jede Status-Familie mappte ALLE Shades auf
 * EIN Kern-Token, wodurch `bg-amber-100 text-amber-800` (Status-Badge) zu
 * Text-auf-gleicher-Farbe wurde. Fix: jede Familie bekommt DREI Shade-Bänder
 * (hell/mittel/dunkel) statt eines einzigen Ziels. Zusätzlich zieht `orange`
 * aus den Warnfarben zu den Marken-Familien (s. Tabelle unten) — Marken-KDs
 * mit Orange als Hauptfarbe landeten sonst komplett in `--kd-warning`.
 *
 * (2) #241 — Wirksamkeit: EMPIRISCH geprüft gegen den echten Play CDN
 * (cdn.tailwindcss.com, Version 3.4.17, nicht risk-hubs vorgepatchte lokale
 * Kopie): ein `window.tailwind.config`, das VOR dem Laden von `tailwind.js`
 * gesetzt wird, wird beim eigenen Bootstrap von `tailwind.js` VERWORFEN —
 * das Skript ersetzt `window.tailwind` durch ein frisches Objekt
 * (`config` danach wieder `{}`). Nur eine Zuweisung an `tailwind.config`
 * NACHDEM `tailwind.js` fertig geladen ist, löst den offiziell
 * unterstützten Re-Build der generierten Utilities aus (verifiziert:
 * `<script src="tailwind.js"></script><script>tailwind.config={...}</script>`
 * wirkt, die umgekehrte Reihenfolge nicht). Die bis 1.41.0 dokumentierte
 * Reihenfolge ("immer davor") war damit für einen frisch vom Play CDN
 * vendorten `tailwind.js` WIRKUNGSLOS — nur risk-hubs lokal vorgepatchte
 * `tailwind.js` (Default-Palette selbst auf `var(--kd-*)` umgehängt)
 * täuschte bislang eine Wirkung vor. Fix: das Snippet setzt die Config
 * weiterhin sofort (deckt "tailwind.js schon geladen" ab, d. h. Einbindung
 * NACH `tailwind.js`), UND hängt zusätzlich einen `load`-Listener an das
 * `<script src=".../tailwind.js">`-Geschwisterelement (gefunden über
 * `document.currentScript`), der die Config nach dessen Laden erneut
 * zuweist — deckt die dokumentierte Reihenfolge ("davor") ab. Findet sich
 * kein solches Geschwister-Element (z. B. dynamisch nachgeladenes
 * `tailwind.js`), pollt ein Sicherheitsnetz bis zu ~2s (Erkennungsmerkmal:
 * `window.tailwind.resolveConfig`, das nur die echte Engine anlegt) und
 * zieht sich danach mit `console.warn` zurück (kein endloses Polling).
 * `check_i5.py` Regel 2 verlangt entsprechend nur noch, dass
 * `tailwind-tokens.js` IRGENDWO im Dokument eingebunden ist, nicht mehr
 * "davor" (s. dort).
 *
 * Mapping-Tabelle (Familie → Ziel-Tokens nach Shade-Band; alle Bänder
 * folgen demselben Prinzip: helle Stufen 50–200 → Flächen-Token, mittlere
 * Stufen 300–500 → Rand-/Akzent-Token, dunkle Stufen 600–950 →
 * Text-/Primär-Token — damit bleiben `bg-<f>-100` + `text-<f>-700` derselben
 * Familie IMMER unterschiedliche, kontrastierende Tokens):
 *
 *   Marken-Familien (indigo, blue, violet, purple, fuchsia, pink, teal,
 *   orange — orange bewusst HIER statt bei den Warnfarben, s. o.)
 *     50–200   → --kd-bg-light
 *     300–500  → --kd-accent-1
 *     600–950  → --kd-primary
 *
 *   Grau-Familien (slate, gray, zinc, neutral, stone) — unverändert
 *     50–100   → --kd-bg-light
 *     200      → --kd-zebra
 *     300      → --kd-border
 *     400      → --kd-line
 *     500–600  → --kd-text-muted
 *     700–950  → --kd-text
 *
 *   Status-Familien — NUR die vier klassischen Ampel-/Info-Bedeutungen,
 *   je Familie drei Shade-Bänder mit CSS-Fallback-Kette (erst ein optionales
 *   `-bg`/`-dark`-Profil-Token, sonst ein garantiert vorhandenes Kern-Token
 *   — nie ein Hex im Snippet):
 *     green, emerald, lime          50–200 → --kd-success-bg, sonst --kd-bg-light
 *     (Erfolg)                      300–500 → --kd-success,   sonst --kd-accent-2
 *                                    600–950 → --kd-success-dark, sonst --kd-text
 *     yellow, amber                 50–200 → --kd-warning-bg, sonst --kd-bg-light
 *     (Warnung)                     300–500 → --kd-warning,   sonst --kd-accent-1
 *                                    600–950 → --kd-warning-dark, sonst --kd-text
 *     red, rose                     50–200 → --kd-danger-bg,  sonst --kd-bg-light
 *     (Fehler)                      300–500 → --kd-danger,    sonst --kd-primary-dark
 *                                    600–950 → --kd-danger-dark, sonst --kd-text
 *     cyan, sky                     50–200 → --kd-info-bg,    sonst --kd-bg-light
 *     (Info)                        300–500 → --kd-info,      sonst --kd-accent-1
 *                                    600–950 → --kd-info-dark, sonst --kd-text
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

  // Synchron sichern — nur während der ersten (synchronen) Ausführung des
  // eigenen <script>-Tags gültig, danach liefert document.currentScript null.
  // `typeof document` gecheckt statt direkt referenziert: robust in
  // Nicht-Browser-Testläufen (Node, s. tests/test_check_i5.py), ohne das
  // Browser-Verhalten zu ändern.
  var OWN_SCRIPT = typeof document !== "undefined" ? document.currentScript : null;

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

  // Marken-Familien (inkl. orange) — helle Stufen NICHT mehr auf einen
  // dunklen Akzent (Fix #238a): 50–200 auf die garantiert helle Fläche,
  // 600–950 auf die Primärfarbe (Text/Icons in Markenfarbe).
  var MARKE = shadeMap([
    [200, "var(--kd-bg-light)"],
    [500, "var(--kd-accent-1)"],
    [950, "var(--kd-primary)"],
  ]);
  var GRAU = shadeMap([
    [100, "var(--kd-bg-light)"],
    [200, "var(--kd-zebra)"],
    [300, "var(--kd-border)"],
    [400, "var(--kd-line)"],
    [600, "var(--kd-text-muted)"],
    [950, "var(--kd-text)"],
  ]);
  // Status-Familien: drei Shade-Bänder statt eines einzigen Kern-Tokens
  // (Fix #238b) — sonst wird z. B. `bg-amber-100 text-amber-800`
  // (Status-Badge) zu Text-auf-gleicher-Farbe. Fallback-Kette: erst ein
  // optionales `-bg`/`-dark`-Profil-Token, dann ein garantiert vorhandenes
  // Kern-Token (bg-light/text/accent/primary-dark).
  var ERFOLG = shadeMap([
    [200, "var(--kd-success-bg, var(--kd-bg-light))"],
    [500, "var(--kd-success, var(--kd-accent-2))"],
    [950, "var(--kd-success-dark, var(--kd-text))"],
  ]);
  var WARNUNG = shadeMap([
    [200, "var(--kd-warning-bg, var(--kd-bg-light))"],
    [500, "var(--kd-warning, var(--kd-accent-1))"],
    [950, "var(--kd-warning-dark, var(--kd-text))"],
  ]);
  var FEHLER = shadeMap([
    [200, "var(--kd-danger-bg, var(--kd-bg-light))"],
    [500, "var(--kd-danger, var(--kd-primary-dark))"],
    [950, "var(--kd-danger-dark, var(--kd-text))"],
  ]);
  var INFO = shadeMap([
    [200, "var(--kd-info-bg, var(--kd-bg-light))"],
    [500, "var(--kd-info, var(--kd-accent-1))"],
    [950, "var(--kd-info-dark, var(--kd-text))"],
  ]);

  var colors = {
    // Marken-Familien (orange gehört hier hin, nicht zu den Warnfarben —
    // s. Kopf-Kommentar)
    indigo: MARKE,
    blue: MARKE,
    violet: MARKE,
    purple: MARKE,
    fuchsia: MARKE,
    pink: MARKE,
    teal: MARKE,
    orange: MARKE,
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
    // Status: Warnung
    yellow: WARNUNG,
    amber: WARNUNG,
    // Status: Fehler
    red: FEHLER,
    rose: FEHLER,
    // Status: Info
    cyan: INFO,
    sky: INFO,
  };

  // Baut IMMER ein frisches config-Objekt (statt in `window.tailwind.config`
  // hinein zu mutieren) — eine neue Objekt-Referenz je Aufruf stellt sicher,
  // dass eine erneute Zuweisung `tailwind.config = ...` beim echten Play CDN
  // (das `.config` nach dem Laden als Setter mit Re-Build-Seiteneffekt
  // führt, s. Kopf-Kommentar #241) nicht an einer Referenzgleichheits-Prüfung
  // hängen bleibt. Bereits gesetzte fremde Config-Felder bleiben erhalten.
  function buildConfig() {
    var base = (window.tailwind && window.tailwind.config) || {};
    var baseTheme = base.theme || {};
    var baseExtend = baseTheme.extend || {};
    return Object.assign({}, base, {
      theme: Object.assign({}, baseTheme, {
        extend: Object.assign({}, baseExtend, {
          colors: Object.assign({}, baseExtend.colors || {}, colors),
        }),
      }),
    });
  }

  function applyConfig() {
    window.tailwind = window.tailwind || {};
    window.tailwind.config = buildConfig();
  }

  function isEngineReady() {
    // Play CDNs echte Engine legt `resolveConfig` (u. a.) an — unser eigener
    // Platzhalter (`window.tailwind = window.tailwind || {}` oben) hat das
    // nicht. Zuverlässigeres Merkmal als bloßes `window.tailwind`-Vorhandensein.
    return !!(window.tailwind && typeof window.tailwind.resolveConfig === "function");
  }

  // Sofort anwenden — deckt "tailwind.js ist beim Ausführen dieses Skripts
  // schon geladen" ab (Einbindung NACH tailwind.js; klassische <script>-Tags
  // laufen synchron in Dokumentreihenfolge, die Engine ist dann bereits da).
  applyConfig();
  if (isEngineReady()) {
    return;
  }

  var reapplied = false;
  function reapplyOnce() {
    if (reapplied) return;
    reapplied = true;
    applyConfig();
  }

  // Bevorzugter Pfad (kein Polling nötig): `load`-Event auf dem
  // `<script src=".../tailwind.js">`-Geschwisterelement — deckt die
  // dokumentierte Reihenfolge ("davor") ab.
  var foundSibling = false;
  if (OWN_SCRIPT && OWN_SCRIPT.parentNode) {
    var siblings = OWN_SCRIPT.parentNode.querySelectorAll("script[src]");
    for (var i = 0; i < siblings.length; i++) {
      var src = siblings[i].getAttribute("src") || "";
      if (/(^|\/)tailwind\.js(\?|#|$)/.test(src)) {
        foundSibling = true;
        siblings[i].addEventListener("load", reapplyOnce);
        break;
      }
    }
  }

  // Sicherheitsnetz: kein <script>-Geschwister gefunden (z. B. dynamisch
  // nachgeladenes tailwind.js) — bis ~2s pollen, dann aufgeben statt endlos
  // weiterzulaufen (#241). `window.__KD_TW_TOKENS_*` sind NUR ein Test-Knob
  // (schnelleres Polling in der Testsuite), kein Consumer-API.
  var pollMs = window.__KD_TW_TOKENS_POLL_MS || 50;
  var maxAttempts = window.__KD_TW_TOKENS_MAX_ATTEMPTS || 40; // 40 * 50ms = 2s
  var attempts = 0;
  var timer = setInterval(function () {
    attempts++;
    if (isEngineReady()) {
      clearInterval(timer);
      reapplyOnce();
      return;
    }
    if (attempts >= maxAttempts) {
      clearInterval(timer);
      if (!reapplied && typeof console !== "undefined" && console.warn) {
        console.warn(
          "tailwind-tokens.js: tailwind.js nicht innerhalb ~2s erkannt (" +
            (foundSibling
              ? "load-Event nicht ausgelöst"
              : 'kein <script src="tailwind.js"> gefunden') +
            ") — Farbmapping evtl. wirkungslos (iilgmbh/iil-klickdummy#241)."
        );
      }
    }
  }, pollMs);
})();

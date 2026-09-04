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
 * ABWEICHUNG von 1.40.0 (iilgmbh/iil-klickdummy#238, risk-hub#736,
 * dev-hub#320 Welle 4 Folgebefund): die 1.40.0-Karte hatte zwei Kontrast-
 * Bugs, per Playwright in risk-hub verifiziert (dsb-vorfaelle: Status-Spalte
 * komplett unsichtbar) — (a) Marken-Familien mappten Shade 50–300 auf
 * `--kd-accent-1`, einen im Profil "iil-extern" DUNKLEN Ton, wodurch das
 * Idiom `bg-indigo-100 text-indigo-700` (heller Chip + dunkler Text) zu
 * dunkel-auf-dunkel wurde; (b) jede Status-Familie mappte ALLE Shades auf
 * EIN Kern-Token, wodurch `bg-amber-100 text-amber-800` (Status-Badge) zu
 * Text-auf-gleicher-Farbe wurde. Fix (dieses Snippet): jede Familie bekommt
 * DREI Shade-Bänder (hell/mittel/dunkel) statt eines einzigen Ziels, analog
 * zum lokalen Fix in risk-hub — dort mit einer projektlokalen
 * `semantic.css`, hier mit den Paket-eigenen `--kd-*`-Tokens + Fallback-Kette.
 * Zusätzlich zieht `orange` aus den Warnfarben zu den Marken-Familien
 * (Begründung s. Tabelle unten) — Markenfarben von KDs, die Orange als
 * Hauptfarbe nutzen, landeten sonst komplett in `--kd-warning`.
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

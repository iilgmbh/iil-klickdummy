#!/usr/bin/env python3
"""I5 Laufzeit-Gate — keine fremden Skripte/Stylesheets, keine Tailwind-
Farbklassen (außer token-gemappt), keine Hex-Farben außerhalb der Token-
Dateien.

Kontext: iilgmbh/iil-klickdummy#232, achimdehnert/dev-hub#320 Welle 3/4.
`kd-nav.js` (und andere Snippets) sind seit Welle 2/3 auf `--kd-*`-Tokens
umgestellt statt CDN/Hex — I5 macht das als Laufzeit-Gate verbindlich, statt
sich auf Code-Review zu verlassen. Regel (4) (Hex-Farben) kam mit Welle 3
dazu, um die 11 Repo-eigenen Klickdummy-Shells zu gaten (dev-hub#320). Die
Regel-2-Ausnahme (token-gemapptes Tailwind) kam mit Welle 4 dazu, um
vendorte Tailwind-Klickdummies (z. B. risk-hub) zu entsperren, ohne
Regel 2 selbst aufzuweichen.

Prüft alle `*.html` unter den übergebenen Klickdummy-Verzeichnissen
(rekursiv, inkl. z. B. `sitemap/`), außer unter `dist/`, `_archiv/` und
`archive/` — das sind Build-Output bzw. bewusst eingefrorene Altstände, keine
aktiven Klickdummy-Screens. Regel (4) prüft zusätzlich `*.css` und `*.js`.

Vier Regeln:
  (1) kein `<script src="http(s)://...">` / `<link href="http(s)://...">`
      — keine CDN-/Fremd-Ressourcen zur Laufzeit (Datenschutz + Offline-
      Fähigkeit, ADR-211).
  (2) keine Tailwind-Farb-Utility-Klassen (`text-blue-600` etc.) — Farben
      kommen aus `var(--kd-*)`, nicht aus einer zweiten, unkontrollierten
      Farbquelle im Markup. AUSNAHME (Welle 4, dev-hub#320): liegt unter dem
      geprüften Wurzelverzeichnis ein `_shared/tailwind-tokens.js`
      (s. `snippets/_shared/tailwind-tokens.js`) UND ist jede tatsächlich verwendete
      Tailwind-Farbfamilie darin auf ein `var(--kd-*)`-Token gemappt, gelten
      Tailwind-Farbklassen als token-gemappt — kein Fehler, stattdessen eine
      Info-Zeile. Fehlt eine verwendete Familie im Mapping → Fehler mit
      Familienname. Zusätzlich muss jede HTML-Datei mit Tailwind-Farbklassen,
      die `tailwind.js` einbindet, `tailwind-tokens.js` IRGENDWO einbinden
      (Reihenfolge zu `tailwind.js` ist seit iilgmbh/iil-klickdummy#241 EGAL —
      das Snippet wirkt seither in beiden Reihenfolgen per `load`-Event +
      gedeckeltem Polling-Fallback, s. Kopf-Kommentar dort; „davor" reichte
      beim echten Play CDN nachweislich NICHT, s. #241) — fehlt die Einbindung
      ganz, Fehler „Mapping nicht geladen: <datei>". Ohne `tailwind-tokens.js`
      im Baum bleibt Regel 2 wie bisher: jede Klasse ein Fehler.
  (3) liegt `_shared/kd-nav.js` vor, muss `_shared/tokens.css` daneben
      existieren — sonst injiziert `kd-nav.js` beim ersten Aufruf einen toten
      `<link>` auf eine fehlende Datei (kd-nav.js hat bewusst keinen Hex-
      Fallback, s. Kommentar dort).
  (4) Farben nur aus Tokens: kein literaler Hex-Farbwert
      (`#abc`, `#a1b2c3`, optional `#a1b2c3d4`) in `*.html`/`*.css`/`*.js`
      — außer in `_shared/tokens.css`, `_shared/semantic.css`,
      `assets/tokens.css`, `assets/semantic.css` (Datei-Ausnahme: dort ist
      der Hex-Wert die Quelle). `sitemap/index.html` bettet `tokens.css`
      roh als ersten <style>-Block ein (s. `gen_sitemap.py`) — statt die
      ganze Datei auszunehmen (das würde eine von Hand gesetzte Farbe im
      selben File nie fangen), wird nur der EINE <style>-Block ausgeblendet,
      dessen Inhalt mit der Generator-Kopfzeile beginnt (`/* tokens.css —
      generiert aus design-hub-Profil`); der Rest der Datei bleibt im Scan.
      Ausgenommen von der Erkennung sind außerdem Issue-Referenzen wie
      `#320` (rein numerisch, kein a-f-Buchstabe, bei 3-stelligen Werten)
      und CSS-Anker wie `#fb-fab` (Bindestrich bricht die Hex-Ziffernfolge).

Aufruf:  python3 scripts/klickdummy/check_i5.py <klickdummy_dir_or_root> [...]
Exit:    0 = PASS, 1 = FAIL, 2 = Setup-Fehler
"""

from __future__ import annotations

import pathlib
import re
import sys

EXCLUDE_PATH_PARTS = {"dist", "_archiv", "archive"}

# <script ... src="http(s)://...">  bzw.  <link ... href="http(s)://...">
FOREIGN_SCRIPT_RE = re.compile(
    r"<script\b[^>]*\bsrc\s*=\s*[\"']https?://", re.IGNORECASE
)
FOREIGN_LINK_RE = re.compile(r"<link\b[^>]*\bhref\s*=\s*[\"']https?://", re.IGNORECASE)

# Tailwind-Palette — eine Liste, sowohl für den Klassen-Regex (Regel 2) als
# auch für den Familien-Scan in `tailwind-tokens.js` (Regel-2-Ausnahme,
# Welle 4), damit beide nie auseinanderdriften können.
TAILWIND_COLOUR_FAMILIES = (
    "slate",
    "gray",
    "zinc",
    "neutral",
    "stone",
    "red",
    "orange",
    "amber",
    "yellow",
    "lime",
    "green",
    "emerald",
    "teal",
    "cyan",
    "sky",
    "blue",
    "indigo",
    "violet",
    "purple",
    "fuchsia",
    "pink",
    "rose",
)

# Tailwind-Farb-Utility-Klassen (Farb-Prefixes × Tailwind-Palette × Shade).
TAILWIND_COLOUR_RE = re.compile(
    r"\b(?:hover:|focus:)?(?:text|bg|border|ring|from|to|via)-"
    rf"(?:{'|'.join(TAILWIND_COLOUR_FAMILIES)})"
    r"-\d{2,3}\b"
)
_TAILWIND_FAMILY_FROM_CLASS_RE = re.compile(
    rf"(?:{'|'.join(TAILWIND_COLOUR_FAMILIES)})(?=-\d{{2,3}}\b)"
)

# `_shared/tailwind.js` (Play-CDN, vendored) — Skript-Dateiname exakt, damit
# `tailwind-tokens.js` (endet nicht auf ".../tailwind.js") nicht mitmatcht.
_TAILWIND_JS_SCRIPT_RE = re.compile(
    r"<script\b[^>]*\bsrc\s*=\s*[\"'][^\"']*tailwind\.js[\"']", re.IGNORECASE
)
_TAILWIND_TOKENS_JS_SCRIPT_RE = re.compile(
    r"<script\b[^>]*\bsrc\s*=\s*[\"'][^\"']*tailwind-tokens\.js[\"']", re.IGNORECASE
)

# Literale Hex-Farbwerte: 3-, 6- und (optional) 8-stellig. Für den 3-stelligen
# Fall verlangt eine Lookahead mindestens einen a-f-Buchstaben unter den ersten
# 3 Zeichen — sonst würden rein numerische Kurzwerte wie Issue-Referenzen
# (`#320`) fälschlich als Hex-Farbe gelten. 6- und 8-stellige Treffer zählen
# immer (Issue-Nummern sind laut Konvention ≤ 4 Ziffern). `\b` am Ende
# erzwingt exakte Länge — ein CSS-Anker wie `#fb-fab` bricht ohnehin schon an
# dem Bindestrich (kein zusammenhängender Hex-Lauf von 3/6/8 Zeichen).
HEX_COLOUR_RE = re.compile(
    r"#(?:[0-9a-fA-F]{8}|[0-9a-fA-F]{6}|(?=[0-9a-fA-F]{0,2}[a-fA-F])[0-9a-fA-F]{3})\b"
)

# Dateien, in denen der Hex-Wert die Quelle ist, nicht der Verstoß.
HEX_GATE_AUSNAHMEN = {
    ("_shared", "tokens.css"),
    ("_shared", "semantic.css"),
    ("assets", "tokens.css"),
    ("assets", "semantic.css"),
}

# `sitemap/index.html` bettet `tokens.css` roh als ersten <style>-Block ein
# (dev-hub#320 Welle 0, Selbstenthaltung — s. gen_sitemap.py `_render_sitemap`).
# Eine pauschale Datei-Ausnahme wäre zu grob (eine von Hand gesetzte Farbe im
# selben File würde nie gefangen) — stattdessen wird nur der EINE <style>-Block
# ausgeblendet, dessen Inhalt mit der Generator-Kopfzeile beginnt; der Rest der
# Datei (weitere <style>-Blöcke, restliches Markup) bleibt im Scan.
_STYLE_BLOCK_RE = re.compile(
    r"(<style\b[^>]*>)(.*?)(</style>)", re.IGNORECASE | re.DOTALL
)
_GENERATED_TOKENS_MARKER = "/* tokens.css — generiert aus design-hub-Profil"


def _mask_generated_tokens_style_blocks(text: str) -> str:
    """Blendet <style>-Blöcke aus, deren Inhalt mit der Tokens-Generator-
    Kopfzeile beginnt — Zeilenzahl bleibt erhalten (Ersatz durch gleich viele
    Leerzeilen), damit Zeilennummern für den Rest der Datei stimmen."""

    def _mask(m: "re.Match[str]") -> str:
        open_tag, body, close_tag = m.group(1), m.group(2), m.group(3)
        if body.lstrip().startswith(_GENERATED_TOKENS_MARKER):
            return open_tag + ("\n" * body.count("\n")) + close_tag
        return m.group(0)

    return _STYLE_BLOCK_RE.sub(_mask, text)


def _is_excluded(path: pathlib.Path, root: pathlib.Path) -> bool:
    try:
        rel_parts = path.resolve().relative_to(root.resolve()).parts
    except ValueError:
        rel_parts = path.parts
    return any(part in EXCLUDE_PATH_PARTS for part in rel_parts)


def check_html_file(
    path: pathlib.Path, *, suppress_tailwind: bool = False
) -> list[tuple[int, str]]:
    """Gibt (zeilen_nr, hinweis)-Liste zurück; leer = ok.

    `suppress_tailwind`: Regel-2-Ausnahme (Welle 4) greift für diesen Wurzel-
    baum — Tailwind-Farbklassen werden hier NICHT als Fund gemeldet (die
    Familien-Abdeckung + Mapping-Einbindung wird separat in `main()` je Root/
    Datei geprüft, s. `_find_tailwind_tokens_mapping`)."""
    findings: list[tuple[int, str]] = []
    try:
        text = path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return findings
    for lineno, line in enumerate(text.splitlines(), start=1):
        if FOREIGN_SCRIPT_RE.search(line):
            findings.append((lineno, 'fremdes <script src="http(s)://...">'))
        if FOREIGN_LINK_RE.search(line):
            findings.append((lineno, 'fremdes <link href="http(s)://...">'))
        if not suppress_tailwind:
            for m in TAILWIND_COLOUR_RE.finditer(line):
                findings.append((lineno, f"Tailwind-Farbklasse {m.group(0)!r}"))
    return findings


def _used_tailwind_families(text: str) -> set[str]:
    """Farbfamilien, die tatsächlich in Tailwind-Utility-Klassen vorkommen."""
    return {m.group(0) for m in _TAILWIND_FAMILY_FROM_CLASS_RE.finditer(text)}


def _find_tailwind_tokens_mapping(root: pathlib.Path) -> pathlib.Path | None:
    """`_shared/tailwind-tokens.js` — Regel-2-Ausnahme (Welle 4). Erstes
    Vorkommen direkt unter einem `_shared/`-Verzeichnis, nicht ausgeschlossen."""
    for candidate in sorted(root.rglob("tailwind-tokens.js")):
        if candidate.parent.name == "_shared" and not _is_excluded(candidate, root):
            return candidate
    return None


def _mapped_tailwind_families(tokens_js_text: str) -> set[str]:
    """Farbfamilien, die in `tailwind-tokens.js` als Objekt-Schlüssel auf ein
    `var(--kd-*)`-Token gemappt sind. Regex-basiert wie der Rest von
    check_i5.py, kein JS-Parser: verlangt `<familie>:` als Objekt-Key UND
    mindestens ein `var(--kd-` irgendwo in der Datei (echtes Token-Mapping,
    kein Blindwert ohne Token-Bezug)."""
    if "var(--kd-" not in tokens_js_text:
        return set()
    return {
        fam
        for fam in TAILWIND_COLOUR_FAMILIES
        if re.search(rf"(?<![\w-]){fam}\s*:", tokens_js_text)
    }


def _tailwind_script_order_ok(text: str) -> bool:
    """`tailwind-tokens.js` muss als <script src> IRGENDWO im Dokument stehen,
    wenn `tailwind.js` eingebunden wird — die Reihenfolge zueinander ist seit
    iilgmbh/iil-klickdummy#241 EGAL. Empirisch am echten Play CDN geprüft:
    ein vorab gesetztes `window.tailwind.config` wird beim Bootstrap von
    `tailwind.js` verworfen, `tailwind-tokens.js` (ab 1.41.0) wendet die
    Config deshalb selbst per `load`-Event + gedeckeltem Polling-Fallback
    erneut an, sobald `tailwind.js` fertig geladen ist — unabhängig davon,
    in welcher Reihenfolge die beiden <script>-Tags stehen. Name der
    Funktion bewusst beibehalten (nur noch Existenz- statt Reihenfolge-
    Prüfung), um den Diff in `main()` klein zu halten."""
    m_tw = _TAILWIND_JS_SCRIPT_RE.search(text)
    if not m_tw:
        return True  # Datei bindet tailwind.js gar nicht ein — nichts zu prüfen
    return bool(_TAILWIND_TOKENS_JS_SCRIPT_RE.search(text))


def _is_hex_exempt(path: pathlib.Path) -> bool:
    """`_shared/tokens.css` u.ä. — dort ist der Hex-Wert die Quelle."""
    parts = path.parts
    return len(parts) >= 2 and (parts[-2], parts[-1]) in HEX_GATE_AUSNAHMEN


def check_hex_colours_file(path: pathlib.Path) -> list[tuple[int, str]]:
    """Gibt (zeilen_nr, hinweis)-Liste literaler Hex-Farbwerte zurück."""
    findings: list[tuple[int, str]] = []
    try:
        text = path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return findings
    text = _mask_generated_tokens_style_blocks(text)
    for lineno, line in enumerate(text.splitlines(), start=1):
        for m in HEX_COLOUR_RE.finditer(line):
            findings.append(
                (lineno, f"Hex-Farbwert {m.group(0)!r} (Regel 4: nur aus Tokens)")
            )
    return findings


def check_kd_nav_needs_tokens(root: pathlib.Path) -> list[str]:
    """`_shared/kd-nav.js` ohne `_shared/tokens.css` daneben = Fehler."""
    findings: list[str] = []
    for nav in sorted(root.rglob("kd-nav.js")):
        if nav.parent.name != "_shared" or _is_excluded(nav, root):
            continue
        tokens_css = nav.parent / "tokens.css"
        if not tokens_css.exists():
            findings.append(f"{tokens_css} fehlt neben {nav}")
    return findings


def main(argv: list[str]) -> int:
    if not argv:
        print("Usage: check_i5.py <klickdummy_dir_or_root> ...")
        return 2
    roots = [pathlib.Path(a) for a in argv]
    missing = [r for r in roots if not r.exists()]
    if missing:
        for r in missing:
            print(f"FAIL: Root fehlt: {r}")
        return 2

    print("== I5 Laufzeit-Gate (CDN/Farbklassen/Tokens/Hex) ==")
    errs = 0
    for root in roots:
        html_paths = [
            p for p in sorted(root.rglob("*.html")) if not _is_excluded(p, root)
        ]

        # Regel-2-Ausnahme (Welle 4): tailwind-tokens.js vorhanden? Dann
        # Familien-Abdeckung root-weit prüfen, bevor die Dateien einzeln
        # durchlaufen werden — kein Fund → Info-Zeile statt Fehlerliste.
        tw_tokens_path = _find_tailwind_tokens_mapping(root)
        tailwind_mapped_ok = False
        if tw_tokens_path is not None:
            try:
                tw_tokens_text = tw_tokens_path.read_text(encoding="utf-8")
            except (UnicodeDecodeError, OSError):
                tw_tokens_text = ""
            mapped_families = _mapped_tailwind_families(tw_tokens_text)
            used_families: set[str] = set()
            for p in html_paths:
                try:
                    used_families |= _used_tailwind_families(
                        p.read_text(encoding="utf-8")
                    )
                except (UnicodeDecodeError, OSError):
                    continue
            missing_families = sorted(used_families - mapped_families)
            if missing_families:
                for fam in missing_families:
                    print(
                        f"  ✗ Regel 2: Familie nicht in {tw_tokens_path} "
                        f"gemappt: {fam!r}"
                    )
                    errs += 1
            else:
                tailwind_mapped_ok = True
                print(
                    f"  Regel 2: Tailwind-Klassen token-gemappt "
                    f"({len(used_families)} Familien, {tw_tokens_path})"
                )

        for path in html_paths:
            findings = list(check_html_file(path, suppress_tailwind=tailwind_mapped_ok))
            if not _is_hex_exempt(path):
                findings += check_hex_colours_file(path)
            if tailwind_mapped_ok:
                try:
                    text = path.read_text(encoding="utf-8")
                except (UnicodeDecodeError, OSError):
                    text = ""
                if _used_tailwind_families(text) and not _tailwind_script_order_ok(
                    text
                ):
                    findings.append((0, f"Mapping nicht geladen: {path}"))
            if findings:
                findings.sort(key=lambda f: f[0])
                print(f"  · {path} ({len(findings)})")
                for lineno, hint in findings:
                    print(f"      ✗ Zeile {lineno}: {hint}")
                    errs += 1

        for path in sorted(list(root.rglob("*.css")) + list(root.rglob("*.js"))):
            if _is_excluded(path, root) or _is_hex_exempt(path):
                continue
            findings = check_hex_colours_file(path)
            if findings:
                print(f"  · {path} ({len(findings)})")
                for lineno, hint in findings:
                    print(f"      ✗ Zeile {lineno}: {hint}")
                    errs += 1

        for hint in check_kd_nav_needs_tokens(root):
            print(f"  ✗ {hint}")
            errs += 1

    if errs == 0:
        print("I5 → PASS")
        return 0
    print(
        f"I5 → FAIL ({errs}) — fremde Skripte/Stylesheets entfernen, "
        "Tailwind-Farbklassen durch var(--kd-*) ersetzen oder via "
        "_shared/tailwind-tokens.js token-mappen, tokens.css neben "
        "kd-nav.js bereitstellen, Hex-Farbwerte durch var(--kd-*) ersetzen "
        "(Ausnahme: tokens.css/semantic.css)"
    )
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))


def main_cli() -> int:
    """Console-Script entry (pyproject.toml [project.scripts])."""
    import sys

    return main(sys.argv[1:])

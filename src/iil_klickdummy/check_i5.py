#!/usr/bin/env python3
"""I5 Laufzeit-Gate — keine fremden Skripte/Stylesheets, keine Tailwind-Farbklassen.

Kontext: iilgmbh/iil-klickdummy#232, achimdehnert/dev-hub#320 Welle 3.
`kd-nav.js` (und andere Snippets) sind seit Welle 2/3 auf `--kd-*`-Tokens
umgestellt statt CDN/Hex — I5 macht das als Laufzeit-Gate verbindlich, statt
sich auf Code-Review zu verlassen.

Prüft alle `*.html` unter den übergebenen Klickdummy-Verzeichnissen
(rekursiv, inkl. z. B. `sitemap/`), außer unter `dist/`, `_archiv/` und
`archive/` — das sind Build-Output bzw. bewusst eingefrorene Altstände, keine
aktiven Klickdummy-Screens.

Drei Regeln:
  (1) kein `<script src="http(s)://...">` / `<link href="http(s)://...">`
      — keine CDN-/Fremd-Ressourcen zur Laufzeit (Datenschutz + Offline-
      Fähigkeit, ADR-211).
  (2) keine Tailwind-Farb-Utility-Klassen (`text-blue-600` etc.) — Farben
      kommen aus `var(--kd-*)`, nicht aus einer zweiten, unkontrollierten
      Farbquelle im Markup.
  (3) liegt `_shared/kd-nav.js` vor, muss `_shared/tokens.css` daneben
      existieren — sonst injiziert `kd-nav.js` beim ersten Aufruf einen toten
      `<link>` auf eine fehlende Datei (kd-nav.js hat bewusst keinen Hex-
      Fallback, s. Kommentar dort).

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

# Tailwind-Farb-Utility-Klassen (Farb-Prefixes × Tailwind-Palette × Shade).
TAILWIND_COLOUR_RE = re.compile(
    r"\b(?:hover:|focus:)?(?:text|bg|border|ring|from|to|via)-"
    r"(?:slate|gray|zinc|neutral|stone|red|orange|amber|yellow|lime|green|"
    r"emerald|teal|cyan|sky|blue|indigo|violet|purple|fuchsia|pink|rose)"
    r"-\d{2,3}\b"
)


def _is_excluded(path: pathlib.Path, root: pathlib.Path) -> bool:
    try:
        rel_parts = path.resolve().relative_to(root.resolve()).parts
    except ValueError:
        rel_parts = path.parts
    return any(part in EXCLUDE_PATH_PARTS for part in rel_parts)


def check_html_file(path: pathlib.Path) -> list[tuple[int, str]]:
    """Gibt (zeilen_nr, hinweis)-Liste zurück; leer = ok."""
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
        for m in TAILWIND_COLOUR_RE.finditer(line):
            findings.append((lineno, f"Tailwind-Farbklasse {m.group(0)!r}"))
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

    print("== I5 Laufzeit-Gate (CDN/Farbklassen/Tokens) ==")
    errs = 0
    for root in roots:
        for path in sorted(root.rglob("*.html")):
            if _is_excluded(path, root):
                continue
            findings = check_html_file(path)
            if findings:
                print(f"  · {path}")
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
        "Tailwind-Farbklassen durch var(--kd-*) ersetzen, tokens.css "
        "neben kd-nav.js bereitstellen"
    )
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))


def main_cli() -> int:
    """Console-Script entry (pyproject.toml [project.scripts])."""
    import sys

    return main(sys.argv[1:])

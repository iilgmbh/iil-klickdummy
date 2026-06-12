#!/usr/bin/env python3
"""I4 Namensraum — Cross-Repo-ADR-Refs nur als repo:ADR-NNN.

Heuristik:
  - Scannt klickdummy-Dateien (md/html/yaml/yml/json) rekursiv unter dem
    übergebenen Root-Verzeichnis.
  - Jeder Treffer auf 'ADR-NNN' muss eine der drei Formen haben:
      (a) repo-qualifiziert, z. B. `meiki:ADR-021` / `platform:ADR-211`
      (b) lokale meiki-ADR (Whitelist unten) — unqualifiziert erlaubt
      (c) in einem Code-/Pre-Block einer Schema-Beispielzeile

Whitelist lokaler ADRs wird aus docs/adr/ADR-NNN-*.md autoermittelt.

Aufruf:  python3 scripts/klickdummy/check_i4.py <root_dir>
Exit:    0 = PASS, 1 = FAIL, 2 = Setup-Fehler
"""
from __future__ import annotations
import pathlib, re, sys

# Erfasst sowohl 'ADR-021' als auch 'foo:ADR-021'
ADR_PATTERN = re.compile(r"(?P<prefix>[A-Za-z][A-Za-z0-9_-]*:)?(?P<adr>ADR-\d{3})")
SCAN_EXT = {".md", ".html", ".yaml", ".yml", ".json"}


def find_adr_dir(root: pathlib.Path) -> pathlib.Path | None:
    """ADR-Verzeichnis relativ zum Scan-Root finden, nicht zum CWD.

    Reihenfolge: <root>/docs/adr, <root>/adr (root=docs/), dann docs/adr
    in den Eltern-Verzeichnissen (Aufruf aus Sub-Pfad / fremdem CWD).
    """
    root = root.resolve()
    candidates = [root / "docs" / "adr", root / "adr"]
    candidates += [anc / "docs" / "adr" for anc in root.parents]
    for c in candidates:
        if c.is_dir():
            return c
    return None


def local_adr_set(root: pathlib.Path) -> set[str]:
    """Sammelt lokal vorhandene ADR-Nummern aus <repo>/docs/adr/ADR-NNN-*.md."""
    out: set[str] = set()
    adr_dir = find_adr_dir(root)
    if adr_dir is not None:
        for p in adr_dir.glob("ADR-*.md"):
            m = re.match(r"(ADR-\d{3})", p.name)
            if m:
                out.add(m.group(1))
    return out


def check_file(path: pathlib.Path, local: set[str]) -> list[tuple[int, str, str]]:
    """Gibt (zeilen_nr, treffer, hinweis)-Liste zurück; leer = ok."""
    findings: list[tuple[int, str, str]] = []
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return findings
    for lineno, line in enumerate(text.splitlines(), start=1):
        for m in ADR_PATTERN.finditer(line):
            adr = m.group("adr")
            prefix = m.group("prefix")
            if prefix:
                continue  # repo:ADR-NNN — ok
            if adr in local:
                continue  # lokale meiki-ADR — ok
            findings.append((lineno, adr, f"unqualifiziert (nicht in local-set, nicht repo:ADR-NNN)"))
    return findings


def main(argv: list[str]) -> int:
    if not argv:
        print("Usage: check_i4.py <root_dir>")
        return 2
    root = pathlib.Path(argv[0])
    if not root.exists():
        print(f"FAIL: Root fehlt: {root}")
        return 2
    local = local_adr_set(root)
    print(f"== I4 Namensraum == (root={root}, lokale ADRs: {len(local)})")
    errs = 0
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.suffix not in SCAN_EXT:
            continue
        findings = check_file(path, local)
        if findings:
            print(f"  · {path}")
            for lineno, adr, hint in findings:
                print(f"      ✗ Zeile {lineno}: {adr} — {hint}")
                errs += 1
    if errs == 0:
        print("I4 → PASS")
        return 0
    print(f"I4 → FAIL ({errs}) — Cross-Repo-Refs als 'repo:ADR-NNN' qualifizieren")
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))


def main_cli() -> int:
    """Console-Script entry (pyproject.toml [project.scripts])."""
    import sys
    return main(sys.argv[1:])

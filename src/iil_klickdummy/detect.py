#!/usr/bin/env python3
"""klickdummy-detect — Existenz-Detektor für das Auto-Brownfield-Gate (Issue #161).

Die org-weite Konvention (`platform/docs/conventions/mmd-kd-code-workflow.md`
§1) verlangt vor jeder Greenfield-Anlage einen Codebase-Evidenz-Check ("Kein
Modul ist neu, bevor die Codebase das bestätigt hat") — das Tooling erzwang
ihn bisher nicht. Realfall 2026-07-01 (risk-hub): ein Nav-Umbau über
existierender App wurde als Greenfield behandelt → Live-Patch-Treadmill,
Session weitgehend aufgezehrt.

Es gibt keine perfekte Punkt-Lösung für "existiert schon?" — Namensvarianz ist
der bekannte Blindfleck (Ordnername != fachlicher Name, z.B.
`gefahrstoff-kataster` vs. `src/gefahrstoffe`). Deshalb Schichten statt einem
Grep:

  L1 exakt (billig)   — Slug-Grep über src/ (Konvention Schritt 2), tolerant
                         gegenüber Bindestrich/Unterstrich/Zusammenschreibung.
  L2 strukturell (GT)  — Django-URL-/App-Introspektion (`from_django.py`,
                         statisches Parsing — keine Django-Runtime/-Settings
                         nötig, entgegen der ursprünglichen Annahme im Issue).
  L3 semantisch (warn) — optionaler Hook für eine pgvector-Query gegen
                         synchronisierte Specs (Anschlusspunkt klickdummy-sync).
                         Nur WARN, nie Gate, weil probabilistisch — dieses
                         Paket hat keine MCP-Dependency (Präzedenz:
                         sync_to_orchestrator.py), darum bleibt L3 hier ein
                         Extension-Point statt einer echten Implementierung.

Treffer in L1 oder L2 → Exit != 0 mit der Evidenz. Override:
`--force-greenfield "<Begründung>"` — die Begründung wird auf stdout als JSON
ausgegeben (Exit 0), damit ein aufrufendes Scaffold-Skript sie ins generierte
Artefakt übernehmen kann (dieses Paket erzeugt selbst kein Artefakt).

CLI:
    klickdummy-detect --repo . --slug gefahrstoffe
    klickdummy-detect --repo . --slug foo --force-greenfield "Bewusst neu, ADR-123"
"""

from __future__ import annotations

import argparse
import dataclasses
import json
import pathlib
import re
import subprocess
import sys

from .from_django import discover_app_dirs, parse_urls

_SKIP_DIRS = {"node_modules", ".venv", "venv", "__pycache__", "migrations"}


def _is_noise_path(rel: pathlib.Path) -> bool:
    """Build-/Cache-Artefakte sind nie Beleg für 'existiert schon' — versteckte
    Verzeichnisse, `__pycache__`/`node_modules`/`.venv`/`migrations` sowie
    `*.egg-info`-Pakete (nach lokalem `pip install -e .` im selben Checkout)."""
    parts = rel.parts
    if any(
        p.startswith(".") or p in _SKIP_DIRS or p.endswith(".egg-info") for p in parts
    ):
        return True
    return False


@dataclasses.dataclass
class Evidence:
    layer: str  # "L1" | "L2" | "L3"
    detail: str


def _slug_variants(slug: str) -> list[str]:
    """Normalisiert Bindestrich/Unterstrich/Zusammenschreibung (Pitfall aus
    Issue #161: `tom-pflege` vs. `test_parity_tom_pflege`, `gefahrstoff-kataster`
    vs. `GefahrstoffKataster`). Case-Normalisierung übernimmt der Caller
    (case-insensitive Grep bzw. `.lower()`-Vergleich)."""
    dash = slug.replace("_", "-")
    underscore = slug.replace("-", "_")
    collapsed = re.sub(r"[-_]", "", slug)
    return sorted({slug, dash, underscore, collapsed})


def _norm(s: str) -> str:
    return re.sub(r"[-_/]", "", s.lower())


def l1_grep(repo_root: pathlib.Path, slug: str) -> Evidence | None:
    """Slug-Grep über `src/` (Konvention Schritt 2) — case-insensitiv, alle
    Separator-Varianten. Prüft sowohl **Pfade** (Verzeichnis-/Dateinamen — der
    Modulname steckt oft primär in der Struktur, Pitfall: Testdatei
    `test_parity_tom_pflege.py` für Slug `tom-pflege`) als auch **Dateiinhalte**
    (Grep)."""
    src = repo_root / "src"
    if not src.exists():
        return None
    variants = [_norm(v) for v in _slug_variants(slug) if v]
    hits: set[str] = set()

    for p in src.rglob("*"):
        if not p.is_file():
            continue
        rel = p.relative_to(repo_root)
        if _is_noise_path(rel):
            continue
        rel_norm = _norm(rel.as_posix())
        if any(v in rel_norm for v in variants):
            hits.add(str(rel))

    pattern = "|".join(re.escape(v) for v in _slug_variants(slug))
    try:
        result = subprocess.run(
            ["grep", "-rlIi", "-E", pattern, str(src)],
            capture_output=True,
            text=True,
            timeout=15,
        )
        for line in result.stdout.splitlines():
            if not line.strip():
                continue
            rel = pathlib.Path(line).relative_to(repo_root)
            if not _is_noise_path(rel):
                hits.add(str(rel))
    except (OSError, subprocess.SubprocessError):
        pass

    if not hits:
        return None
    rel_hits = sorted(hits)[:5]
    return Evidence(
        layer="L1", detail=f"Slug-Grep-Treffer in src/: {', '.join(rel_hits)}"
    )


def l2_django(repo_root: pathlib.Path, slug: str) -> Evidence | None:
    """Django-Introspektion (Ground Truth): App-Name-/Routen-Treffer über alle
    Apps im Repo. Reuse von `from_django.parse_urls` als Detektor-Backend statt
    Neubau (Issue-Vorgabe)."""
    variants = [_norm(v) for v in _slug_variants(slug) if v]
    for app_dir in discover_app_dirs(repo_root):
        rel = app_dir.relative_to(repo_root)
        if _is_noise_path(rel):
            continue
        app_name, entries = parse_urls(app_dir)
        if _norm(app_name) in variants:
            return Evidence(
                layer="L2", detail=f"Django-App-Treffer: {rel} (app_name={app_name})"
            )
        for e in entries:
            route_norm = _norm(e["route"])
            if any(v in route_norm for v in variants):
                return Evidence(
                    layer="L2",
                    detail=f"Django-Route-Treffer: {rel} ({e['name']} → {e['route']})",
                )
    return None


def detect(repo_root: pathlib.Path, slug: str) -> list[Evidence]:
    """Layer-Orchestrierung: L1 zuerst (billig), dann L2. L3 ist bewusst kein
    Aufruf hier (Extension-Point, s. Modul-Docstring)."""
    hits = []
    l1 = l1_grep(repo_root, slug)
    if l1:
        hits.append(l1)
    l2 = l2_django(repo_root, slug)
    if l2:
        hits.append(l2)
    return hits


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--repo", default=".", help="Repo-Root (default: .)")
    ap.add_argument("--slug", required=True, help="Modul-/App-Slug, der geprüft wird")
    ap.add_argument(
        "--force-greenfield",
        metavar="BEGRUENDUNG",
        help="Override: Treffer ignorieren, Begründung wird auf stdout als JSON "
        "ausgegeben (Exit 0) — Übernahme ins Artefakt ist Sache des Callers",
    )
    args = ap.parse_args(argv)

    repo_root = pathlib.Path(args.repo).expanduser().resolve()
    evidence = detect(repo_root, args.slug)

    if not evidence:
        print(f"✓ Kein Treffer für Slug '{args.slug}' — Greenfield bestätigt.")
        return 0

    for e in evidence:
        print(f"  [{e.layer}] {e.detail}", file=sys.stderr)

    if args.force_greenfield:
        print(
            f"⚠ --force-greenfield trotz {len(evidence)} Evidenz-Treffer(n): "
            f"{args.force_greenfield}",
            file=sys.stderr,
        )
        print(
            json.dumps(
                {
                    "slug": args.slug,
                    "force_greenfield_reason": args.force_greenfield,
                    "evidence": [dataclasses.asdict(e) for e in evidence],
                },
                ensure_ascii=False,
            )
        )
        return 0

    print(
        f"✗ Gefunden: {len(evidence)} Evidenz-Treffer für '{args.slug}' — "
        f'behandle als Brownfield (Override: --force-greenfield "<Begründung>")',
        file=sys.stderr,
    )
    return 1


def main_cli() -> int:
    return main(sys.argv[1:])


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""Sync klickdummy-Specs zu GitHub-Issues + (optional) Org-Project.

Counter-A-Implementation (Genesor-Adversarial-Review 2026-05-24):
GitHub-Projects als System-of-Record für Pipeline/Lifecycle/Auth,
Genesor bleibt Spec-Visualisierungs-Tool.

Pfad-Konventionen (zwei werden gescannt):
  klickdummy/<name>/screens-spec.yaml                                  (Standard)
  docs/01-architektur/mockups/<name>-klickdummy/screens-spec.yaml      (meiki-Variante)

Aufruf (in einem GitHub-Actions-Workflow):
  GH_TOKEN=...  REPO=owner/repo  [PROJECT_URL=...]
  python3 klickdummy_sync.py [--dry-run]

Idempotent: Issues werden über Sentinel `<!-- klickdummy-sync:<kd> -->` im
Body gefunden und aktualisiert, nicht doppelt angelegt.

Heimat (Rev 13 §Distribution):
  iil-klickdummy/src/iil_klickdummy/snippets/genesor-sync/ — KANONISCHE QUELLE.
  Kopien in Konsumenten-Repos (.github/scripts/klickdummy_sync.py) nicht
  direkt editieren — Änderungen hier vornehmen, dann in die Repos verteilen.
"""

from __future__ import annotations

import argparse
import json
import os
import re as _re
import subprocess
import sys
from pathlib import Path

import yaml

REPO = os.environ.get("REPO", "")
PROJECT_URL = os.environ.get("PROJECT_URL", "").strip()
ROOT = Path(os.environ.get("GITHUB_WORKSPACE", ".")).resolve()


def sentinel(kd_name: str) -> str:
    return f"<!-- klickdummy-sync:{kd_name} -->"


# ---- Spec-Discovery ---------------------------------------------------------


def find_specs() -> list[tuple[str, Path]]:
    """Returnt Liste (kd_name, spec_path) — beide Konventionen."""
    out: list[tuple[str, Path]] = []
    for p in sorted(ROOT.glob("klickdummy/*/screens-spec.yaml")):
        out.append((p.parent.name, p))
    for p in sorted(
        ROOT.glob("docs/01-architektur/mockups/*-klickdummy/screens-spec.yaml")
    ):
        out.append((p.parent.name.removesuffix("-klickdummy"), p))
    return out


# ---- Issue-Body-Rendering ---------------------------------------------------


def render_body(kd_name: str, spec_path: Path, data: dict) -> str:
    title = (data.get("title") or kd_name).split("—")[0].strip()
    klass = data.get("class") or "?"
    role = data.get("spec_role") or "default"
    sunset = (data.get("off_ramp", {}) or {}).get("sunset_after", "—")
    n_screens = len(data.get("screens", []) or [])
    conforms_to = (data.get("adr", {}) or {}).get("conforms_to", "platform:ADR-211")

    personas_obj = data.get("personas") or {}
    if isinstance(personas_obj, dict):
        personas_list = list(personas_obj.keys())
    elif isinstance(personas_obj, list):
        personas_list = [
            p.get("id", str(p)) if isinstance(p, dict) else str(p) for p in personas_obj
        ]
    else:
        personas_list = []

    spec_rel = spec_path.relative_to(ROOT)

    # Beziehungen
    rel_lines = []
    for cf in data.get("consumes_from", []) or []:
        ref = cf.get("ref", "?") if isinstance(cf, dict) else str(cf)
        n_ent = len(cf.get("entities", []) or []) if isinstance(cf, dict) else 0
        rel_lines.append(f"- **consumes_from** `{ref}` ({n_ent} entities)")
    for pc in data.get("provides_contracts", []) or []:
        cid = pc.get("schema_ref") or pc.get("id", "?")
        rel_lines.append(f"- **provides_contracts** `{cid}`")
    for ac in data.get("accepts_contracts", []) or []:
        cid = ac.get("schema_ref") or ac.get("id", "?")
        rel_lines.append(f"- **accepts_contracts** `{cid}`")
    re_root = data.get("root_entities") or {}
    if re_root:
        n = len(re_root) if isinstance(re_root, dict) else len(list(re_root))
        rel_lines.append(f"- **root_entities** {n} exponiert")
    rel_md = (
        "\n".join(rel_lines)
        if rel_lines
        else "_standalone — keine Cross-KD-Beziehungen_"
    )

    # Screens
    screens = data.get("screens", []) or []
    screen_lines = []
    for s in screens[:12]:
        if not isinstance(s, dict):
            continue
        sid = s.get("id", "?")
        stitle = s.get("title", "")
        screen_lines.append(f"- `{sid}` — {stitle}")
    if len(screens) > 12:
        screen_lines.append(f"- _… +{len(screens) - 12} weitere_")
    screens_md = "\n".join(screen_lines) if screen_lines else "_keine_"

    return f"""{sentinel(kd_name)}

> **Klickdummy** · auto-synced from [`{spec_rel}`]({spec_rel}) · `platform:ADR-211` konform

| Feld | Wert |
|---|---|
| **KD-Name** | `{kd_name}` |
| **Titel** | {title} |
| **class** | `{klass}` |
| **spec_role** | `{role}` |
| **sunset_after** | `{sunset}` |
| **Screens** | {n_screens} |
| **Personas** | {", ".join(personas_list[:6]) or "—"} |
| **conforms_to** | `{conforms_to}` |

## 🖼 Screens

{screens_md}

## 🔗 Beziehungen

{rel_md}

---
_Dieses Issue wird automatisch durch [`klickdummy-sync.yml`](.github/workflows/klickdummy-sync.yml) aus der Spec
aktualisiert. Pipeline-Status, Zuweisungen, Kommentare bleiben in GitHub — sie überleben den nächsten Sync._
"""


# ---- gh-CLI-Wrapper ---------------------------------------------------------


def gh(
    *args: str, check: bool = True, capture: bool = True
) -> subprocess.CompletedProcess:
    return subprocess.run(["gh", *args], check=check, capture_output=capture, text=True)


_ISSUE_CACHE: list[dict] | None = None


def _list_klickdummy_issues() -> list[dict]:
    """Cached: alle klickdummy-Issues im Repo (open + closed)."""
    global _ISSUE_CACHE
    if _ISSUE_CACHE is not None:
        return _ISSUE_CACHE
    try:
        # gh issue list akzeptiert --state all (im Gegensatz zu gh search issues).
        # Sentinel-Match passiert client-side: HTML-Kommentare brechen die
        # GitHub-Search-Query-Syntax, daher list+filter statt search.
        result = gh(
            "issue",
            "list",
            "--repo",
            REPO,
            "--label",
            "klickdummy",
            "--state",
            "all",
            "--json",
            "number,title,body,labels,url",
            "--limit",
            "300",
        )
        _ISSUE_CACHE = json.loads(result.stdout) or []
    except subprocess.CalledProcessError as e:
        print(f"WARN: gh issue list failed: {e.stderr}", file=sys.stderr)
        _ISSUE_CACHE = []
    except json.JSONDecodeError:
        _ISSUE_CACHE = []
    return _ISSUE_CACHE


def find_existing_issue(kd_name: str) -> dict | None:
    """Sucht via Sentinel im Body (client-side über gecachte Issue-Liste)."""
    s = sentinel(kd_name)
    for issue in _list_klickdummy_issues():
        if s in (issue.get("body") or ""):
            return issue
    return None


def upsert_issue(
    kd_name: str, spec_path: Path, data: dict, dry_run: bool = False
) -> int | None:
    title = (data.get("title") or kd_name).split("—")[0].strip()[:60]
    issue_title = f"[Klickdummy] {kd_name} — {title}"
    body = render_body(kd_name, spec_path, data)
    klass = data.get("class") or ""
    role = data.get("spec_role") or ""

    labels = ["klickdummy"]
    if klass:
        labels.append(f"klickdummy/class:{klass}")
    if role in {"root", "hybrid"}:
        labels.append(f"klickdummy/role:{role}")

    existing = find_existing_issue(kd_name)

    if dry_run:
        action = "UPDATE" if existing else "CREATE"
        print(f"[dry-run] {action} {kd_name} ({issue_title})")
        return existing.get("number") if existing else None

    if existing:
        num = existing["number"]
        gh(
            "issue",
            "edit",
            str(num),
            "--repo",
            REPO,
            "--title",
            issue_title,
            "--body",
            body,
            "--add-label",
            ",".join(labels),
        )
        print(f"✓ updated #{num} for {kd_name}")
        return num
    else:
        # Labels müssen existieren — sonst Fehler. Wir legen sie lazy an.
        for lbl in labels:
            try:
                gh(
                    "label",
                    "create",
                    lbl,
                    "--repo",
                    REPO,
                    "--color",
                    "0E8A16" if lbl == "klickdummy" else "C5DEF5",
                    check=False,
                )
            except Exception:
                pass
        result = gh(
            "issue",
            "create",
            "--repo",
            REPO,
            "--title",
            issue_title,
            "--body",
            body,
            "--label",
            ",".join(labels),
        )
        url = result.stdout.strip().splitlines()[-1]
        num = int(url.rstrip("/").split("/")[-1])
        print(f"✓ created #{num} for {kd_name} ({url})")
        return num


_PROJECT_URL_RE = _re.compile(r"https://github\.com/orgs/([^/]+)/projects/(\d+)")


def add_to_project(issue_number: int, dry_run: bool = False) -> None:
    """Fügt Issue zum Org-Project hinzu (wenn PROJECT_URL gesetzt).

    Owner + Project-Number werden AUS PROJECT_URL extrahiert — NICHT aus
    REPO (Bug-Fix: Issue-Repo-Owner kann ein anderer Org sein als
    Project-Owner, z. B. Issues in meiki-lra/* → Project in iilgmbh).
    """
    if not PROJECT_URL:
        return
    if dry_run:
        print(f"[dry-run] add-to-project #{issue_number} → {PROJECT_URL}")
        return
    m = _PROJECT_URL_RE.match(PROJECT_URL)
    if not m:
        print(
            f"WARN: PROJECT_URL '{PROJECT_URL}' nicht im Format https://github.com/orgs/<owner>/projects/<n>",
            file=sys.stderr,
        )
        return
    project_owner = m.group(1)
    project_num = m.group(2)
    issue_url = f"https://github.com/{REPO}/issues/{issue_number}"
    result = gh(
        "project",
        "item-add",
        project_num,
        "--owner",
        project_owner,
        "--url",
        issue_url,
        check=False,
    )
    if result.returncode == 0:
        print(
            f"  → added #{issue_number} to project ({project_owner}/projects/{project_num})"
        )
    else:
        stderr = (result.stderr or "")[:200]
        if "already" not in stderr.lower():
            print(
                f"WARN: project item-add failed for #{issue_number}: {stderr}",
                file=sys.stderr,
            )


# ---- main -------------------------------------------------------------------


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Klickdummy → GitHub Issue + Project sync"
    )
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--only", type=str, default=None, help="Nur diesen KD-Namen syncen"
    )
    args = parser.parse_args()

    if not REPO:
        print("ERROR: REPO env var nicht gesetzt", file=sys.stderr)
        return 2

    specs = find_specs()
    if args.only:
        specs = [(n, p) for n, p in specs if n == args.only]
    if not specs:
        print("Keine screens-spec.yaml gefunden.")
        return 0

    print(f"Sync {len(specs)} KDs aus {REPO}" + (" (dry-run)" if args.dry_run else ""))
    for kd_name, spec_path in specs:
        try:
            data = yaml.safe_load(spec_path.read_text("utf-8")) or {}
        except yaml.YAMLError as e:
            print(f"SKIP {kd_name}: YAML-Parse-Fehler: {e}", file=sys.stderr)
            continue
        issue_num = upsert_issue(kd_name, spec_path, data, dry_run=args.dry_run)
        if issue_num and not args.dry_run:
            add_to_project(issue_num, dry_run=args.dry_run)

    return 0


if __name__ == "__main__":
    sys.exit(main())

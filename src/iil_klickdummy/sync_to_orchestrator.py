"""Push Klickdummy-Metadaten in den Orchestrator-pgvector-Memory.

Per platform:ADR-211 Rev 14 §Stufe-2. Stakeholder-Idee Iter. 8:
„verwaltung der Klickdummies cross-repo mit versionierten klickdummies"
→ Stufe-3-Cross-Repo via Orchestrator-Memory.

Mechanik:
  - registry.discover_klickdummies(repo_root) findet Specs
  - pro Klickdummy: 1 Memory-Entry (entry_type=repo_context)
  - pro Iteration (feedback-log.md): 1 Entry (entry_type=lesson_learned)
  - pro Klickdummy-ADR: 1 Entry (entry_type=decision)
  - Idempotent via content_hash (vom orchestrator selbst)

Multi-Tenant: Tags ['klickdummy', 'klickdummy:class:<cls>',
                    'klickdummy:org:<org>', 'klickdummy:repo:<repo>'].
Gov-Workloads (ttz-lif, meiki-lra): zusätzlich 'gov-data'-Tag.

Output ist NDJSON von Memory-Operationen (eine Zeile pro Entry).
Tatsächlicher Push erfolgt nicht in diesem Modul direkt — Konsument liest
NDJSON und ruft mcp__orchestrator__agent_memory_upsert auf (CC-Skill
oder MCP-Server). Begründung: dieses Paket hat keine MCP-Dependency und
ist trotzdem lauffähig als CLI ohne Orchestrator-Verbindung.

CLI:
    klickdummy-sync --repo .                # repo-lokal, NDJSON auf stdout
    klickdummy-sync --repo . --output sync.ndjson
    klickdummy-sync --cross-repo --base ~/github
    klickdummy-sync --repo . --dry-run      # nur Listen, kein NDJSON
"""
from __future__ import annotations

import argparse
import json
import os
import pathlib
import re
import sys
from datetime import datetime, timezone

from .registry import discover_klickdummies, discover_versions

# Gov-Orgs — extra Tag 'gov-data' für Search-Filter
GOV_ORGS = {"ttz-lif", "meiki-lra"}
DEFAULT_REPOS = ["meiki-hub", "writing-hub", "risk-hub", "pptx-hub", "dev-hub",
                 "ttz-hub", "iil-klickdummy"]


def _detect_org(repo_root: pathlib.Path) -> str:
    """Versucht Org aus git remote URL zu lesen, sonst Repo-Name als Fallback."""
    try:
        import subprocess
        result = subprocess.run(
            ["git", "-C", str(repo_root), "remote", "get-url", "origin"],
            capture_output=True, text=True, timeout=5,
        )
        if result.returncode == 0:
            # match owner/repo aus URL: github.com:OWNER/REPO oder github.com/OWNER/REPO
            m = re.search(r"github\.com[:/]([^/]+)/", result.stdout)
            if m:
                return m.group(1)
    except (OSError, subprocess.SubprocessError, ImportError):
        pass
    return "(unknown-org)"


def _detect_repo_name(repo_root: pathlib.Path) -> str:
    return repo_root.name


def klickdummy_entry(km, org: str, repo: str, repo_root: pathlib.Path) -> dict:
    """Erzeugt 1 Memory-Entry-Dict für einen Klickdummy.

    Returns: {entry_key, entry_type, title, content, tags, agent}
    """
    versions = discover_versions(repo_root / km.path, repo_root)
    versions_block = "\n".join(
        f"- {v.spec_version} ({v.commit_date[:10]} {v.commit_sha[:8]})"
        for v in versions
    ) or "- (keine Versions-History gefunden)"
    content = (
        f"# {km.title}\n\n"
        f"**Spec ID:** `{km.spec_id}`  \n"
        f"**Version:** {km.spec_version}  \n"
        f"**Klasse:** `{km.klickdummy_class}` (platform:ADR-211 I2)  \n"
        f"**ADR:** {km.adr_local or '_(kein lokaler ADR-Ref)_'}  \n"
        f"**Schwester-Implementations:** "
        + (", ".join(f"`{s}`" for s in km.sister_of) if km.sister_of else "_(keine)_")
        + "\n\n"
        f"## Pfad im Repo\n`{km.path}`\n\n"
        f"## Versions-History\n{versions_block}\n\n"
        f"## Sync-Quelle\n"
        f"- Repo: `{org}/{repo}`\n"
        f"- Sync-Zeit: {datetime.now(timezone.utc).isoformat()}\n"
    )
    tags = [
        "klickdummy",
        f"klickdummy:class:{km.klickdummy_class}",
        f"klickdummy:org:{org}",
        f"klickdummy:repo:{repo}",
    ]
    if org in GOV_ORGS:
        tags.append("gov-data")
    return dict(
        entry_key=f"klickdummy:{org}:{repo}:{km.name}",
        entry_type="repo_context",
        title=f"{repo}:{km.name} v{km.spec_version} [{km.klickdummy_class}]",
        content=content,
        tags=tags,
        agent="iil-klickdummy-sync",
    )


def iteration_entries_from_feedback_log(
    repo_root: pathlib.Path, org: str, repo: str
) -> list[dict]:
    """Liest feedback-log.md falls vorhanden + extrahiert Iterations-Einträge."""
    out: list[dict] = []
    for candidate in repo_root.rglob("feedback-log.md"):
        try:
            text = candidate.read_text(encoding="utf-8")
        except (OSError, UnicodeError):
            continue
        # Klickdummy-Name aus Pfad ableiten: <pfad>/<name>/feedback-log.md
        klickdummy_name = candidate.parent.name
        # Zeilen mit "| N | <datum> | <screen> | ..." extrahieren
        for line in text.splitlines():
            m = re.match(r"^\|\s*(\d+)\s*\|\s*([^|]+?)\s*\|\s*`?([^|`]+?)`?\s*\|", line)
            if not m:
                continue
            iter_n, when, screen = m.group(1), m.group(2).strip(), m.group(3).strip()
            if not iter_n.isdigit():
                continue
            entry_key = f"klickdummy-iter:{org}:{repo}:{klickdummy_name}:{iter_n}"
            out.append(dict(
                entry_key=entry_key,
                entry_type="lesson_learned",
                title=f"{repo}:{klickdummy_name} Iter.{iter_n} ({screen})",
                content=line,
                tags=["klickdummy", "klickdummy-iter",
                      f"klickdummy:org:{org}", f"klickdummy:repo:{repo}",
                      f"klickdummy:iter:{iter_n}"],
                agent="iil-klickdummy-sync",
            ))
    return out


def adr_entries(repo_root: pathlib.Path, org: str, repo: str) -> list[dict]:
    """Findet Klickdummy-ADRs (tags: [klickdummy] in Frontmatter) und erzeugt Entries."""
    out: list[dict] = []
    for candidate in repo_root.rglob("ADR-*.md"):
        try:
            text = candidate.read_text(encoding="utf-8")
        except (OSError, UnicodeError):
            continue
        # naive Frontmatter-Erkennung
        if not re.search(r"^tags:\s*\[.*klickdummy.*\]", text, re.MULTILINE):
            continue
        # ADR-Nummer aus Filename
        m = re.match(r"ADR-(\d+)-", candidate.name)
        if not m:
            continue
        adr_num = m.group(1)
        title_match = re.search(r"^title:\s*\"?([^\"\n]+)\"?", text, re.MULTILINE)
        title = title_match.group(1).strip() if title_match else candidate.stem
        out.append(dict(
            entry_key=f"klickdummy-adr:{org}:{repo}:ADR-{adr_num}",
            entry_type="decision",
            title=f"{repo}:ADR-{adr_num} — {title}",
            content=text[:8000],   # Body-Vorschau (Embeddings haben Token-Limit)
            tags=["klickdummy", "klickdummy-adr",
                  f"klickdummy:org:{org}", f"klickdummy:repo:{repo}",
                  f"klickdummy:adr:ADR-{adr_num}"],
            agent="iil-klickdummy-sync",
        ))
    return out


def sync_repo(repo_root: pathlib.Path) -> list[dict]:
    org = _detect_org(repo_root)
    repo = _detect_repo_name(repo_root)
    entries: list[dict] = []
    for km in discover_klickdummies(repo_root):
        entries.append(klickdummy_entry(km, org, repo, repo_root))
    entries.extend(iteration_entries_from_feedback_log(repo_root, org, repo))
    entries.extend(adr_entries(repo_root, org, repo))
    return entries


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", default=".", help="Repo-Root (Default: .)")
    parser.add_argument("--cross-repo", action="store_true",
                        help="Alle Repos unter --base scannen")
    parser.add_argument("--base", default=os.path.expanduser("~/github"))
    parser.add_argument("--repos", default=",".join(DEFAULT_REPOS),
                        help="Komma-Liste der Repo-Namen für --cross-repo")
    parser.add_argument("--output", default="-",
                        help="NDJSON-Output (- = stdout)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Nur Listen, kein NDJSON")
    args = parser.parse_args(argv)

    if args.cross_repo:
        base = pathlib.Path(args.base).expanduser()
        repo_roots = [base / r for r in args.repos.split(",") if (base / r).exists()]
    else:
        repo_roots = [pathlib.Path(args.repo).expanduser().resolve()]

    print(f"== Klickdummy-Sync → Orchestrator (v1.2) ==", file=sys.stderr)
    all_entries: list[dict] = []
    for rr in repo_roots:
        print(f"  · {rr}", file=sys.stderr)
        entries = sync_repo(rr)
        all_entries.extend(entries)
        if args.dry_run:
            kdm = sum(1 for e in entries if e["entry_type"] == "repo_context")
            itr = sum(1 for e in entries if e["entry_type"] == "lesson_learned")
            adr = sum(1 for e in entries if e["entry_type"] == "decision")
            print(f"    Klickdummies: {kdm} · Iterationen: {itr} · ADRs: {adr}",
                  file=sys.stderr)

    print(f"  Total: {len(all_entries)} Entries", file=sys.stderr)
    if args.dry_run:
        return 0

    output = sys.stdout if args.output == "-" else open(args.output, "w", encoding="utf-8")
    try:
        for e in all_entries:
            output.write(json.dumps(e, ensure_ascii=False) + "\n")
    finally:
        if output is not sys.stdout:
            output.close()
            print(f"  → {args.output}", file=sys.stderr)
    return 0


def main_cli() -> int:
    return main(sys.argv[1:])


if __name__ == "__main__":
    sys.exit(main_cli())

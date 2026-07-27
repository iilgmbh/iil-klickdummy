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

from .registry import discover_klickdummies, discover_versions

# Gov-Orgs — extra Tag 'gov-data' für Search-Filter
GOV_ORGS = {"ttz-lif", "meiki-lra"}
DEFAULT_REPOS = [
    "meiki-hub",
    "writing-hub",
    "risk-hub",
    "pptx-hub",
    "dev-hub",
    "ttz-hub",
    "iil-klickdummy",
]


def _is_ignored_source(rel: pathlib.Path) -> bool:
    """Pfade unter versteckten Verzeichnissen (`.claude/worktrees/`, `.git/`, …),
    `node_modules/` oder `klickdummy/archive/` sind keine Kanon-Quelle (Issue #163)
    — Realfall: stale Agent-Worktree `.claude/worktrees/agent-…/docs/adr/` liefert
    inhaltlich divergente ADR-Kopien, die per `rglob` sonst mit-gefunden werden."""
    rel_str = "/" + rel.as_posix() + "/"
    if any(part.startswith(".") for part in rel.parts):
        return True
    return "/node_modules/" in rel_str or "/klickdummy/archive/" in rel_str


def _version_sort_key(version: str) -> tuple:
    """Sortierschlüssel für `spec_version`-Strings — '0.2' > '0.1', '10' > '9'
    (reiner String-Vergleich würde '10' < '9' ordnen)."""
    parts: list[tuple[int, object]] = []
    for seg in re.split(r"[.\-]", str(version)):
        try:
            parts.append((0, int(seg)))
        except ValueError:
            parts.append((1, seg))
    return tuple(parts)


CONTENT_PREVIEW_LIMIT = 8000


def _content_preview(text: str, limit: int = CONTENT_PREVIEW_LIMIT) -> str:
    """Body-Vorschau für Embeddings (Token-Limit) — mit sichtbarem Truncation-
    Marker (Issue #188 Zweitbefund). Ohne Marker endete der Content mitten im
    Wort (`ADR-046` brach in "## Refe" ab) und Konsumenten konnten nicht
    unterscheiden, ob die Quelle kurz ist oder abgeschnitten wurde."""
    if len(text) <= limit:
        return text
    return f"{text[:limit]}\n\n… [gekürzt: {len(text) - limit} weitere Zeichen]"


def _dedup_entries(entries: list[dict]) -> list[dict]:
    """Dedupliziert Entries nach `entry_key` (Issue #163): rglob-Duplikate (ADR-
    Kopien in stale Agent-Worktrees) und Doppel-Emission (zwei Spec-Dateien im
    selben KD-Verzeichnis, z.B. `screens-spec.yaml` + alte `spec.yaml`) landen
    sonst reihenfolgeabhängig im Store (last-write-wins beim Upsert).

    Präzedenz: ADR (`entry_type="decision"`) → kürzester `_source_path` gewinnt
    (Kanon `docs/adr/` schlägt jede Kopie). Klickdummy (`entry_type="repo_context"`)
    → höchste `_precedence_version` gewinnt. Bei inhaltlicher Divergenz zwischen
    Kandidaten: WARN auf stderr mit beiden Pfaden — Symptom ist meist ein stale
    Worktree (Aufräum-Hinweis auf `worktree-reaper`)."""
    by_key: dict[str, list[dict]] = {}
    for e in entries:
        by_key.setdefault(e["entry_key"], []).append(e)

    out: list[dict] = []
    for key, group in by_key.items():
        if len(group) > 1 and any(g["content"] != group[0]["content"] for g in group):
            paths = ", ".join(g.get("_source_path", "?") for g in group)
            print(
                f"WARN: entry_key {key!r} inhaltlich divergent über {len(group)} "
                f"Quellen ({paths}) — evtl. stale Worktree (worktree-reaper).",
                file=sys.stderr,
            )
        if group[0].get("entry_type") == "decision":
            winner = min(group, key=lambda g: len(g.get("_source_path", "")))
        elif group[0].get("entry_type") == "repo_context":
            winner = max(
                group,
                key=lambda g: _version_sort_key(g.get("_precedence_version", "0")),
            )
        else:
            winner = group[0]
        out.append({k: v for k, v in winner.items() if not k.startswith("_")})
    return out


def _detect_org(repo_root: pathlib.Path) -> str:
    """Versucht Org aus git remote URL zu lesen, sonst Repo-Name als Fallback."""
    try:
        import subprocess

        result = subprocess.run(
            ["git", "-C", str(repo_root), "remote", "get-url", "origin"],
            capture_output=True,
            text=True,
            timeout=5,
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
    versions_block = (
        "\n".join(
            f"- {v.spec_version} ({v.commit_date[:10]} {v.commit_sha[:8]})"
            for v in versions
        )
        or "- (keine Versions-History gefunden)"
    )
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
        _source_path=km.path,
        _precedence_version=km.spec_version,
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
            iter_n, screen = m.group(1), m.group(3).strip()
            if not iter_n.isdigit():
                continue
            entry_key = f"klickdummy-iter:{org}:{repo}:{klickdummy_name}:{iter_n}"
            out.append(
                dict(
                    entry_key=entry_key,
                    entry_type="lesson_learned",
                    title=f"{repo}:{klickdummy_name} Iter.{iter_n} ({screen})",
                    content=line,
                    tags=[
                        "klickdummy",
                        "klickdummy-iter",
                        f"klickdummy:org:{org}",
                        f"klickdummy:repo:{repo}",
                        f"klickdummy:iter:{iter_n}",
                    ],
                    agent="iil-klickdummy-sync",
                )
            )
    return out


def adr_entries(repo_root: pathlib.Path, org: str, repo: str) -> list[dict]:
    """Findet Klickdummy-ADRs (tags: [klickdummy] in Frontmatter) und erzeugt Entries."""
    out: list[dict] = []
    for candidate in repo_root.rglob("ADR-*.md"):
        rel = candidate.relative_to(repo_root)
        if _is_ignored_source(rel):
            continue
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
        out.append(
            dict(
                entry_key=f"klickdummy-adr:{org}:{repo}:ADR-{adr_num}",
                entry_type="decision",
                title=f"{repo}:ADR-{adr_num} — {title}",
                content=_content_preview(text),
                tags=[
                    "klickdummy",
                    "klickdummy-adr",
                    f"klickdummy:org:{org}",
                    f"klickdummy:repo:{repo}",
                    f"klickdummy:adr:ADR-{adr_num}",
                ],
                agent="iil-klickdummy-sync",
                _source_path=str(rel),
            )
        )
    return out


def sync_repo(repo_root: pathlib.Path, *, dedup: bool = True) -> list[dict]:
    """Entries eines Repos sammeln.

    `dedup=False` liefert die Roh-Entries **inklusive** der internen
    `_source_path`/`_precedence_version`-Felder — nötig, damit ein späterer
    aggregierter `_dedup_entries()`-Lauf die Präzedenz noch auswerten kann
    (Issue #188). `main()` nutzt genau diesen Pfad; Einzel-Aufrufer behalten
    das bisherige Verhalten."""
    org = _detect_org(repo_root)
    repo = _detect_repo_name(repo_root)
    entries: list[dict] = []
    for km in discover_klickdummies(repo_root):
        entries.append(klickdummy_entry(km, org, repo, repo_root))
    entries.extend(iteration_entries_from_feedback_log(repo_root, org, repo))
    entries.extend(adr_entries(repo_root, org, repo))
    return _dedup_entries(entries) if dedup else entries


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", default=".", help="Repo-Root (Default: .)")
    parser.add_argument(
        "--cross-repo", action="store_true", help="Alle Repos unter --base scannen"
    )
    parser.add_argument("--base", default=os.path.expanduser("~/github"))
    parser.add_argument(
        "--repos",
        default=",".join(DEFAULT_REPOS),
        help="Komma-Liste der Repo-Namen für --cross-repo",
    )
    parser.add_argument("--output", default="-", help="NDJSON-Output (- = stdout)")
    parser.add_argument(
        "--dry-run", action="store_true", help="Nur Listen, kein NDJSON"
    )
    args = parser.parse_args(argv)

    if args.cross_repo:
        base = pathlib.Path(args.base).expanduser()
        repo_roots = [base / r for r in args.repos.split(",") if (base / r).exists()]
    else:
        repo_roots = [pathlib.Path(args.repo).expanduser().resolve()]

    print("== Klickdummy-Sync → Orchestrator (v1.2) ==", file=sys.stderr)
    all_entries: list[dict] = []
    for rr in repo_roots:
        print(f"  · {rr}", file=sys.stderr)
        entries = sync_repo(rr, dedup=False)
        all_entries.extend(entries)
        if args.dry_run:
            kdm = sum(1 for e in entries if e["entry_type"] == "repo_context")
            itr = sum(1 for e in entries if e["entry_type"] == "lesson_learned")
            adr = sum(1 for e in entries if e["entry_type"] == "decision")
            print(
                f"    Klickdummies: {kdm} · Iterationen: {itr} · ADRs: {adr}",
                file=sys.stderr,
            )

    # Dedup EINMAL über alle Repos (Issue #188): der bisherige Per-Repo-Dedup
    # in `sync_repo()` sah Duplikate nicht, die aus ZWEI Repo-Roots mit
    # identischem org/repo stammen (Kopie/stale Worktree in der --repos-Liste).
    # Die landeten reihenfolgeabhängig im NDJSON — Konsumenten upserten
    # last-write-wins, wodurch die ÄLTERE Variante gewann.
    raw_count = len(all_entries)
    all_entries = _dedup_entries(all_entries)
    dropped = raw_count - len(all_entries)
    if dropped:
        print(
            f"  Dedup: {dropped} Duplikat-Entry(s) verworfen "
            f"({raw_count} → {len(all_entries)})",
            file=sys.stderr,
        )
    print(f"  Total: {len(all_entries)} Entries", file=sys.stderr)
    if args.dry_run:
        return 0

    output = (
        sys.stdout if args.output == "-" else open(args.output, "w", encoding="utf-8")
    )
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

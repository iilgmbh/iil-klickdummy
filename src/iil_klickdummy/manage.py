"""klickdummy-manage — Verwaltungs-CLI für Klickdummies cross-repo (v1.4).

Konsolidiert inventory + registry + sync zu einer einheitlichen Mgmt-Ansicht.
Konsumiert die existierenden Bausteine, fügt **3 neue Achsen** hinzu:

  - **Repo**  (org + repo-name, schon vorhanden)
  - **Topic** (NEU: optionales meta.topic in screens-spec.yaml — frei wählbarer
               Cluster-Tag wie 'fristen', 'werkleiter', 'lecture', etc.)
  - **Version** (spec_version + Git-History — schon vorhanden, hier exponiert)

Sub-Commands:

    klickdummy-manage list      [filter]               # Aggregat-Übersicht
    klickdummy-manage status    [filter]               # Health (sunset_after, drift)
    klickdummy-manage topics                           # Topic-Cluster-Übersicht
    klickdummy-manage versions  <spec_id>              # Version-Historie 1 KD
    klickdummy-manage diff      <spec_id> <v1> <v2>    # Versions-Diff 1 KD

Filter (für list + status):
    --org <org>     --repo <repo>     --class <pattern>     --topic <topic>
    --sunset-due-in <days>     --base <path>     --repos <a,b,c>

Per ADR-211 Rev 14 §Multi-Klickdummy-Browser Stufe 1-3: dieses Modul ist
die textuelle/CLI-Schwester zum visuellen Browser (v1.1/v1.3) — gleiche
Datenquelle (registry.discover_cross_repo), andere Konsumenten-UX.

Topic ist OPTIONAL — bestehende Specs ohne `meta.topic` bleiben gültig.
"""

from __future__ import annotations

import argparse
import json
import os
import pathlib
import sys
from datetime import date

import yaml

from .read_model import load_spec_yaml
from .registry import (
    discover_cross_repo,
    discover_versions,
    KlickdummyMeta,
)


# ---------------------------------------------------------------------------
# Spec-Helpers (Topic + Frontmatter-Lesen)
# ---------------------------------------------------------------------------


def _load_spec_yaml(spec_path: pathlib.Path) -> dict:
    """A-04: Lesen/Parsen konsolidiert in read_model.load_spec_yaml; dieser
    Wrapper behält den lokalen Soft-Fail-Vertrag (leeres dict statt Exception,
    fürs Topic-Browsing/-Listing nicht fatal)."""
    try:
        return load_spec_yaml(spec_path) or {}
    except (OSError, yaml.YAMLError):
        return {}


def _spec_topic(spec_path: pathlib.Path) -> str | None:
    """Liest meta.topic aus screens-spec.yaml (v1.4 optionales Feld)."""
    spec = _load_spec_yaml(spec_path)
    meta = spec.get("meta") or {}
    return meta.get("topic")


def _adr_sunset_after(repo_root: pathlib.Path, adr_local: str | None) -> date | None:
    """Liest sunset_after aus Klickdummy-ADR (z. B. 'meiki:ADR-021')."""
    if not adr_local or ":" not in adr_local:
        return None
    _, adr_id = adr_local.split(":", 1)
    for candidate in repo_root.rglob(f"{adr_id}-*.md"):
        try:
            text = candidate.read_text(encoding="utf-8")
        except (OSError, UnicodeError):
            continue
        import re

        m = re.search(r"^sunset_after:\s*(\d{4}-\d{2}-\d{2})", text, re.MULTILINE)
        if m:
            try:
                return date.fromisoformat(m.group(1))
            except ValueError:
                continue
    return None


# ---------------------------------------------------------------------------
# Filter
# ---------------------------------------------------------------------------


def _passes_filter(
    org: str, repo: str, km: KlickdummyMeta, topic: str | None, args
) -> bool:
    if args.org and org != args.org:
        return False
    if args.repo and repo != args.repo:
        return False
    if getattr(args, "class_", None) and km.klickdummy_class != args.class_:
        return False
    if args.topic and (topic or "") != args.topic:
        return False
    return True


# ---------------------------------------------------------------------------
# Sub-Command: list
# ---------------------------------------------------------------------------


def cmd_list(args) -> int:
    base = pathlib.Path(args.base).expanduser().resolve()
    repos = [r.strip() for r in args.repos.split(",") if r.strip()]
    triples = discover_cross_repo(base, repos)
    if not triples:
        print("0 Klickdummies gefunden.", file=sys.stderr)
        return 0
    print("== klickdummy-manage list ==", file=sys.stderr)
    rows: list[tuple] = []
    for org, repo, km in triples:
        topic = _spec_topic(base / repo / km.path) or "—"
        if not _passes_filter(org, repo, km, topic, args):
            continue
        rows.append(
            (
                org,
                repo,
                km.name,
                km.spec_version,
                km.klickdummy_class,
                topic,
                km.adr_local or "—",
            )
        )
    if not rows:
        print("Keine Klickdummies passend zum Filter.", file=sys.stderr)
        return 0
    # Tabellen-Output
    headers = ("ORG", "REPO", "NAME", "VER", "CLASS", "TOPIC", "ADR")
    widths = [
        max(len(str(r[i])) for r in [headers, *rows]) for i in range(len(headers))
    ]
    if args.json:
        print(
            json.dumps(
                [dict(zip(headers, r)) for r in rows], ensure_ascii=False, indent=2
            )
        )
        return 0
    line = "  ".join(f"{h:<{w}}" for h, w in zip(headers, widths))
    print(line)
    print("-" * len(line))
    for r in rows:
        print("  ".join(f"{str(c):<{w}}" for c, w in zip(r, widths)))
    print()
    print(f"Total: {len(rows)} Klickdummies", file=sys.stderr)
    return 0


# ---------------------------------------------------------------------------
# Sub-Command: status (Health-Check)
# ---------------------------------------------------------------------------


def cmd_status(args) -> int:
    base = pathlib.Path(args.base).expanduser().resolve()
    repos = [r.strip() for r in args.repos.split(",") if r.strip()]
    triples = discover_cross_repo(base, repos)
    today = date.today()

    print("== klickdummy-manage status ==", file=sys.stderr)
    healthy = 0
    warnings: list[str] = []
    for org, repo, km in triples:
        topic = _spec_topic(base / repo / km.path)
        if not _passes_filter(org, repo, km, topic, args):
            continue
        msgs = []
        sunset = _adr_sunset_after(base / repo, km.adr_local)
        if sunset:
            days_left = sunset.toordinal() - today.toordinal()
            if days_left < 0:
                msgs.append(
                    f"⚠ sunset_after {sunset} ÜBERSCHRITTEN ({-days_left} Tage)"
                )
            elif days_left < (args.sunset_due_in or 30):
                msgs.append(f"⚠ sunset_after {sunset} fällig in {days_left} Tagen")
        else:
            msgs.append(
                f"⚠ kein sunset_after in ADR ({km.adr_local}) — Rev-11-Frontmatter-Verstoß"
            )
        if km.klickdummy_class not in ("mock", "stub-demo", "story", "spec-demo"):
            msgs.append(f"⚠ class={km.klickdummy_class!r} nicht in 4-Pattern")
        if not msgs:
            healthy += 1
            continue
        warnings.append(f"  {org}/{repo}:{km.name} (v{km.spec_version})")
        for m in msgs:
            warnings.append(f"    {m}")
    print(f"  Healthy:  {healthy}", file=sys.stderr)
    print(f"  Warnings: {(len(warnings) // 2) if warnings else 0}", file=sys.stderr)
    if warnings:
        print()
        for w in warnings:
            print(w)
        return 1
    return 0


# ---------------------------------------------------------------------------
# Sub-Command: topics
# ---------------------------------------------------------------------------


def cmd_topics(args) -> int:
    base = pathlib.Path(args.base).expanduser().resolve()
    repos = [r.strip() for r in args.repos.split(",") if r.strip()]
    triples = discover_cross_repo(base, repos)
    by_topic: dict = {}
    for org, repo, km in triples:
        topic = _spec_topic(base / repo / km.path) or "(kein topic)"
        by_topic.setdefault(topic, []).append((org, repo, km))
    print("== klickdummy-manage topics ==", file=sys.stderr)
    print(f"  Topics: {len(by_topic)}", file=sys.stderr)
    if args.json:
        out = {
            t: [
                {
                    "org": o,
                    "repo": r,
                    "name": k.name,
                    "spec_version": k.spec_version,
                    "class": k.klickdummy_class,
                }
                for o, r, k in items
            ]
            for t, items in by_topic.items()
        }
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return 0
    for topic, items in sorted(by_topic.items()):
        print(f"\n## {topic} ({len(items)} Klickdummy(ies))")
        for org, repo, km in items:
            print(
                f"  - {org}/{repo}:{km.name}  v{km.spec_version}  [{km.klickdummy_class}]"
            )
    print()
    return 0


# ---------------------------------------------------------------------------
# Sub-Command: versions
# ---------------------------------------------------------------------------


def cmd_versions(args) -> int:
    base = pathlib.Path(args.base).expanduser().resolve()
    repos = [r.strip() for r in args.repos.split(",") if r.strip()]
    triples = discover_cross_repo(base, repos)
    found = False
    for org, repo, km in triples:
        if km.spec_id != args.spec_id:
            continue
        found = True
        spec_path = base / repo / km.path
        versions = discover_versions(spec_path, base / repo)
        print(f"== Versionen von {km.spec_id} ({org}/{repo}) ==")
        for v in versions:
            print(f"  v{v.spec_version}  {v.commit_date[:10]}  {v.commit_sha[:8]}")
        if not versions:
            print(f"  (keine Versions-History — nur HEAD: v{km.spec_version})")
    if not found:
        print(f"FAIL: spec_id {args.spec_id!r} nicht gefunden", file=sys.stderr)
        return 1
    return 0


# ---------------------------------------------------------------------------
# Sub-Command: diff
# ---------------------------------------------------------------------------


def cmd_diff(args) -> int:
    import subprocess

    base = pathlib.Path(args.base).expanduser().resolve()
    repos = [r.strip() for r in args.repos.split(",") if r.strip()]
    triples = discover_cross_repo(base, repos)
    for org, repo, km in triples:
        if km.spec_id != args.spec_id:
            continue
        spec_path = base / repo / km.path
        versions = discover_versions(spec_path, base / repo)
        v1_commit = next(
            (v.commit_sha for v in versions if v.spec_version == args.v1), None
        )
        v2_commit = next(
            (v.commit_sha for v in versions if v.spec_version == args.v2), None
        )
        if not v1_commit or not v2_commit:
            print(
                f"FAIL: Version {args.v1} oder {args.v2} nicht in History",
                file=sys.stderr,
            )
            return 1
        print(f"== Diff {km.spec_id}  v{args.v1} ↔ v{args.v2}  ({org}/{repo}) ==")
        rel = spec_path.relative_to(base / repo)
        result = subprocess.run(
            [
                "git",
                "-C",
                str(base / repo),
                "diff",
                f"{v1_commit}..{v2_commit}",
                "--",
                str(rel),
            ],
            capture_output=True,
            text=True,
            timeout=15,
        )
        print(
            result.stdout
            or "  (keine Änderungen in der Spec-Datei zwischen den Versionen)"
        )
        return 0
    print(f"FAIL: spec_id {args.spec_id!r} nicht gefunden", file=sys.stderr)
    return 1


# ---------------------------------------------------------------------------
# Main + Sub-Parser
# ---------------------------------------------------------------------------


def _add_common_filters(p: argparse.ArgumentParser) -> None:
    p.add_argument("--base", default=os.path.expanduser("~/github"))
    p.add_argument(
        "--repos",
        default="meiki-hub,writing-hub,risk-hub,ttz-hub,pptx-hub,dev-hub,iil-klickdummy",
    )
    p.add_argument("--org", default=None)
    p.add_argument("--repo", default=None)
    p.add_argument(
        "--class",
        dest="class_",
        default=None,
        help="Filter klickdummy-class (mock|stub-demo|story|spec-demo)",
    )
    p.add_argument("--topic", default=None)
    p.add_argument("--json", action="store_true")
    p.add_argument(
        "--sunset-due-in",
        type=int,
        default=None,
        help="Warn-Schwelle für sunset_after (Tage)",
    )


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_list = sub.add_parser("list", help="Aggregat-Übersicht aller Klickdummies")
    _add_common_filters(p_list)

    p_status = sub.add_parser(
        "status", help="Health-Check (sunset_after, Klassen-Compliance)"
    )
    _add_common_filters(p_status)

    p_topics = sub.add_parser("topics", help="Topic-Cluster-Übersicht")
    _add_common_filters(p_topics)

    p_versions = sub.add_parser("versions", help="Versions-History eines Klickdummys")
    p_versions.add_argument("spec_id")
    _add_common_filters(p_versions)

    p_diff = sub.add_parser("diff", help="Diff Spec zwischen 2 Versionen")
    p_diff.add_argument("spec_id")
    p_diff.add_argument("v1")
    p_diff.add_argument("v2")
    _add_common_filters(p_diff)

    args = parser.parse_args(argv)
    return {
        "list": cmd_list,
        "status": cmd_status,
        "topics": cmd_topics,
        "versions": cmd_versions,
        "diff": cmd_diff,
    }[args.cmd](args)


def main_cli() -> int:
    return main(sys.argv[1:])


if __name__ == "__main__":
    sys.exit(main_cli())

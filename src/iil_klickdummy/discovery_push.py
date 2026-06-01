"""Klickdummy Discovery Push — Stage 1.5 (platform:ADR-215).

Erweitert sync_to_orchestrator.py um v1.5-Discovery-Felder + direkten
REST-Push zur Orchestrator-Discovery-API (statt nur NDJSON-Output).

Was v1.5 zusätzlich zu v1.2 macht:

1. Pro Klickdummy: ein discovery_entry mit:
   - genre ('forms' | 'conversation' | 'spec-demo' | 'story' | 'mock')
   - personas (aus screens-spec.personas Keys bzw. bot-spec.personas)
   - embedding_text (title + purpose + parity_acceptance-Texte verkettet)
   - last_seen (ISO-Timestamp)
2. Optional: direkter HTTPS-Push zu konfigurierbarem Endpoint
   (default: https://orchestrator.iil.pet/api/discovery/klickdummy/upsert).
3. Dry-Run-Mode: zeigt was gepusht würde, ohne Network-Call.

CLI (Sub-Commands):
    klickdummy-discovery list                   # listet alle Klickdummies
    klickdummy-discovery push                   # NDJSON auf stdout
    klickdummy-discovery push --to-orchestrator # HTTPS-Push
    klickdummy-discovery push --dry-run         # zeigt Payload, kein Push

Endpoint-Konfig:
    Default: ENV KLICKDUMMY_DISCOVERY_ENDPOINT
             oder https://orchestrator.iil.pet/api/discovery/klickdummy/upsert
    Auth:    ENV KLICKDUMMY_DISCOVERY_TOKEN (Bearer-Token, optional)

DSGVO-Vermerk (User-Klärung 2026-05-21):
    Discovery-Payload enthält keine personenbezogenen Daten außer
    Funktionsrollen-Bezeichnungen (Persona-Labels wie 'sachbearbeiter').
    Synthetische Operativ-Daten bleiben in den Klickdummies (class: mock).
    DSFA-Ergebnis: nicht kritisch.
"""
from __future__ import annotations

import argparse
import json
import os
import pathlib
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone

from .registry import discover_klickdummies


DEFAULT_ENDPOINT = (
    os.environ.get("KLICKDUMMY_DISCOVERY_ENDPOINT")
    or "https://orchestrator.iil.pet/api/discovery/klickdummy/upsert"
)


def _detect_genre(spec: dict) -> str:
    """Heuristik: forms (screens-spec) vs. conversation (bot-spec)."""
    if "topics" in spec:
        return "conversation"
    if "screens" in spec:
        return "forms"
    return "unknown"


def _build_embedding_text(spec: dict, max_chars: int = 4096) -> str:
    """Verkettet Titel + Purpose + Parity-Acceptance + Topic-Trigger.

    Liefert einen kompakten Text-Block, den der Orchestrator embedden kann.
    Length-Cap auf 4 KB — pgvector mag kompakte Embeddings.
    """
    parts: list[str] = []
    parts.append(str(spec.get("title", "")))

    # Forms: screens[].purpose + parity_acceptance[].check
    for s in spec.get("screens", []):
        if isinstance(s, dict):
            parts.append(str(s.get("title", "")))
            parts.append(str(s.get("purpose", "")))
            for pa in s.get("parity_acceptance", []) or []:
                if isinstance(pa, dict):
                    parts.append(str(pa.get("check", "")))

    # Conversation: topics[].triggers + topics[].description + paths
    for t in spec.get("topics", []):
        if isinstance(t, dict):
            parts.append(str(t.get("name", "")))
            parts.append(str(t.get("description", "")))
            for trig in t.get("triggers", []) or []:
                parts.append(str(trig))

    txt = " ".join(p for p in parts if p).strip()
    if len(txt) > max_chars:
        txt = txt[: max_chars - 1] + "…"
    return txt


def _extract_personas(spec: dict) -> list[str]:
    """Liefert Persona-Keys aus Spec (forms personas: oder bot personas:)."""
    p = spec.get("personas", {})
    if isinstance(p, dict):
        return sorted(p.keys())
    return []


def _detect_org_from_repo(repo_root: pathlib.Path) -> str:
    """Org aus git remote URL ableiten."""
    config = repo_root / ".git" / "config"
    if not config.exists():
        return "unknown"
    try:
        text = config.read_text(encoding="utf-8", errors="ignore")
        import re

        m = re.search(r"github\.com[/:](?P<org>[^/]+)/", text)
        if m:
            return m.group("org")
    except Exception:
        pass
    return "unknown"


def build_discovery_entry(repo_root: pathlib.Path, spec_path: pathlib.Path, spec: dict) -> dict:
    """Baut einen Discovery-Eintrag im v1.5-Schema."""
    repo_root = repo_root.resolve()
    rel = spec_path.resolve().relative_to(repo_root)
    org = _detect_org_from_repo(repo_root)
    repo_name = repo_root.name
    return {
        "schema_version": "v1.5",
        "spec_id": spec.get("spec_id") or spec.get("bot_id") or str(rel),
        "version": spec.get("spec_version") or spec.get("bot_version") or "?",
        "klickdummy_class": spec.get("class", "?"),
        "topic": (
            spec.get("render_meta", {}).get("konzept_id")
            or spec.get("grounding", {}).get("konzept_modell")
            or "?"
        ),
        "adr": (spec.get("adr") or {}).get("local", "?"),
        "conforms_to": (spec.get("adr") or {}).get("conforms_to", "platform:ADR-211"),
        "sister_of": (spec.get("adr") or {}).get("sister_of", []),
        "repo": f"{org}/{repo_name}",
        "path_rel": str(rel),
        "genre": _detect_genre(spec),
        "personas": _extract_personas(spec),
        "embedding_text": _build_embedding_text(spec),
        "last_seen": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "sunset_after": spec.get("sunset_after"),
    }


def collect_entries(base: pathlib.Path, repos: list[str] | None = None) -> list[dict]:
    """Sammelt Discovery-Einträge aus repo_root oder cross-repo.

    discover_klickdummies() liefert KlickdummyMeta-Dataclass-Instanzen (nicht
    Path-Objekte) — `.path` ist der relative Pfad zur Spec; wir lösen ihn
    relativ zum repo_root auf.
    """
    import yaml

    entries: list[dict] = []
    targets: list[tuple[pathlib.Path, list]] = []
    if repos:
        for repo_name in repos:
            repo_root = base / repo_name
            if repo_root.exists():
                targets.append((repo_root, discover_klickdummies(repo_root)))
    else:
        targets.append((base, discover_klickdummies(base)))

    for repo_root, metas in targets:
        for meta in metas:
            try:
                spec_path = repo_root / meta.path
                spec = yaml.safe_load(spec_path.read_text(encoding="utf-8"))
                if spec:
                    entries.append(build_discovery_entry(repo_root, spec_path, spec))
            except Exception as e:
                print(f"⚠ {meta.spec_id} ({meta.path}): {e}", file=sys.stderr)
    return entries


def push_to_endpoint(entries: list[dict], endpoint: str, token: str | None = None) -> dict:
    """POSTet Liste der Einträge als JSON-Batch an Discovery-Endpoint."""
    body = json.dumps({"entries": entries}).encode("utf-8")
    headers = {"Content-Type": "application/json", "User-Agent": "iil-klickdummy/v1.5"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(endpoint, data=body, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return {
                "status_code": resp.status,
                "body": resp.read().decode("utf-8", errors="replace")[:2000],
            }
    except urllib.error.HTTPError as e:
        return {"status_code": e.code, "body": e.read().decode("utf-8", errors="replace")[:2000]}
    except urllib.error.URLError as e:
        return {"status_code": 0, "body": f"URLError: {e.reason}"}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Klickdummy Discovery v1.5 (platform:ADR-215)")
    sub = ap.add_subparsers(dest="cmd", required=True)

    ap_list = sub.add_parser("list", help="Klickdummies als Tabelle auflisten")
    ap_list.add_argument("--repo", default=".", help="Repo-Root (default: .)")
    ap_list.add_argument("--cross-repo", action="store_true", help="cross-repo via --repos")
    ap_list.add_argument("--repos", help="Komma-getrennt repo-Namen (für --cross-repo)")
    ap_list.add_argument("--base", default=str(pathlib.Path.home() / "github"))

    ap_push = sub.add_parser("push", help="NDJSON oder direct-push")
    ap_push.add_argument("--repo", default=".")
    ap_push.add_argument("--cross-repo", action="store_true")
    ap_push.add_argument("--repos", help="Komma-getrennt repo-Namen")
    ap_push.add_argument("--base", default=str(pathlib.Path.home() / "github"))
    ap_push.add_argument("--to-orchestrator", action="store_true", help="Direct-Push zu Discovery-API")
    ap_push.add_argument("--endpoint", default=DEFAULT_ENDPOINT, help="Override Discovery-Endpoint")
    ap_push.add_argument("--dry-run", action="store_true", help="Zeigt Payload, kein Push")
    ap_push.add_argument("--output", "-o", help="NDJSON in Datei statt stdout")

    args = ap.parse_args(argv)

    base = pathlib.Path(args.base).expanduser()
    repos = [r.strip() for r in (args.repos or "").split(",") if r.strip()] if args.cross_repo else None
    repo_root = pathlib.Path(args.repo).resolve() if not args.cross_repo else base

    entries = collect_entries(repo_root if not args.cross_repo else base, repos)

    if args.cmd == "list":
        print("== klickdummy-discovery list ==")
        print(f"Total: {len(entries)} Klickdummies")
        print()
        print(f"{'ORG':<14} {'NAME':<32} {'VER':<5} {'GENRE':<12} {'CLASS':<10} {'ADR'}")
        print("-" * 100)
        for e in entries:
            org_name = e["repo"].split("/", 1)
            org = org_name[0] if len(org_name) > 1 else "?"
            name = pathlib.PurePath(e["path_rel"]).parent.name or e["spec_id"]
            print(
                f"{org:<14} {name:<32} {e['version']:<5} {e['genre']:<12} "
                f"{e['klickdummy_class']:<10} {e['adr']}"
            )
        return 0

    if args.cmd == "push":
        if args.dry_run:
            print(f"== DRY-RUN: {len(entries)} entries würden gepusht werden ==", file=sys.stderr)
            for e in entries:
                print(json.dumps(e, ensure_ascii=False))
            return 0

        if args.to_orchestrator:
            token = os.environ.get("KLICKDUMMY_DISCOVERY_TOKEN")
            print(
                f"→ POST {args.endpoint} ({len(entries)} entries, auth={'yes' if token else 'no'})",
                file=sys.stderr,
            )
            result = push_to_endpoint(entries, args.endpoint, token)
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return 0 if 200 <= result["status_code"] < 300 else 1

        # NDJSON-Output (Default)
        ndjson = "\n".join(json.dumps(e, ensure_ascii=False) for e in entries)
        if args.output:
            pathlib.Path(args.output).write_text(ndjson + "\n", encoding="utf-8")
            print(f"✓ {len(entries)} entries → {args.output}", file=sys.stderr)
        else:
            print(ndjson)
        return 0

    return 1


if __name__ == "__main__":
    sys.exit(main())

"""Klickdummy Discovery Push — Stage 1.5 (platform:ADR-215, accepted).

Erweitert sync_to_orchestrator.py um Discovery-Felder + direkten REST-Push zur
Orchestrator-Discovery-API. **Schema v1.6** arbeitet die Producer-seitigen
§Amendment-1-Auflagen ein (Härtung vor Produktiv-Aktivierung):

- **Provenance/Drift-Anker** (REC-1/6): `source_repo`, `source_ref`, `commit_sha`,
  `spec_sha256`, `generated_at` → jeder Eintrag ist ein *abgeleiteter Index* mit
  Rückführung auf seinen exakten Spec-Stand, kein System of Record.
- **Upsert-Identität** `registry_key` = org/repo + path_rel + spec_id (REC-2).
- **Ingestion-Guard** (REC-7): nur deklarierte I2-Klassen sind push-berechtigt.
- **Governance-Gate** `discovery.discoverable` (REC-14, Soft-Migrate-Default true).
- **Sichtbarkeit** `visibility_scope ∈ {repo,org,allowlist,public-demo}` (REC-6).
- **Filter/Lifecycle** `pipeline_status`, `off_ramp_status`, `tombstone` (REC-5/16).
- **Versionierter Push-Envelope** `{api_version, registry_schema_version, …}` (REC-4/10).
- **Signierter Fallback-Snapshot** mit `sha256` (REC-3, Producer-Hälfte).

NICHT hier (Orchestrator-/Consumer-Seite, separates Go): TTL/Tombstone-Enforcement,
Org-Filter/Visibility auf der Query, Audit-Storage, Picker-Snapshot-Konsum,
Search-Eval-Suite (bei `klickdummy-search`).

CLI (Sub-Commands):
    klickdummy-discovery list                      # listet alle Klickdummies
    klickdummy-discovery push                       # NDJSON auf stdout
    klickdummy-discovery push --to-orchestrator     # HTTPS-Push (versionierter Envelope)
    klickdummy-discovery push --dry-run             # zeigt Payload, kein Push
    klickdummy-discovery push --snapshot snap.json  # signierter Fallback-Snapshot

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
import hashlib
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

# platform:ADR-215 §Amendment 1 (Producer-Seite)
REGISTRY_SCHEMA_VERSION = "v1.6"   # v1.6 = + Provenance/registry_key/visibility/Lifecycle-Felder
API_VERSION = "v1"                 # Push-Envelope-Vertrag (REC-4/REC-10)
EMBEDDING_INPUT_SCHEMA = "v1"      # welche Spec-Felder embedding_text bilden (REC-17)
# Push-berechtigte I2-Klassen (REC-7 Ingestion-Guard) — kein vacuous push.
ALLOWED_CLASSES = {"mock", "stub-demo", "story", "spec-demo"}


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


def _git_provenance(repo_root: pathlib.Path) -> tuple[str | None, str | None]:
    """(source_ref, commit_sha) aus `.git` lesen — ohne Subprozess (REC-1).

    Tolerant: fehlt `.git`/HEAD/ref → (None, None). Keine Exception nach außen.
    """
    git = repo_root / ".git"
    head = git / "HEAD"
    if not head.exists():
        return (None, None)
    try:
        content = head.read_text(encoding="utf-8", errors="ignore").strip()
        if content.startswith("ref:"):
            ref = content[4:].strip()                      # z. B. refs/heads/main
            short = ref.split("/", 2)[-1]                  # main
            ref_file = git / ref
            sha = None
            if ref_file.exists():
                sha = ref_file.read_text(encoding="utf-8", errors="ignore").strip() or None
            else:
                packed = git / "packed-refs"
                if packed.exists():
                    for line in packed.read_text(encoding="utf-8", errors="ignore").splitlines():
                        if line.endswith(" " + ref):
                            sha = line.split(" ", 1)[0].strip() or None
                            break
            return (short, sha)
        # detached HEAD: HEAD enthält direkt den SHA
        return (None, content or None)
    except Exception:
        return (None, None)


def _spec_sha256(spec_path: pathlib.Path) -> str | None:
    """SHA256 der Spec-Bytes — Drift-Anker gegen die Quelle (REC-1/REC-6)."""
    try:
        return "sha256:" + hashlib.sha256(spec_path.read_bytes()).hexdigest()
    except Exception:
        return None


def _registry_key(org: str, repo_name: str, rel: pathlib.PurePath, spec_id: str) -> str:
    """Eindeutige Upsert-Identität (REC-2): org/repo + path_rel + spec_id."""
    return f"{org}/{repo_name}:{rel}#{spec_id}"


def _discovery_block(spec: dict) -> dict:
    """Optionaler `discovery:`-Block in der Spec (Governance-Quelle, REC-14)."""
    d = spec.get("discovery")
    return d if isinstance(d, dict) else {}


def _is_discoverable(spec: dict) -> tuple[bool, bool]:
    """(discoverable, soft_default) — `discovery.discoverable` aus Spec (REC-14).

    Nicht deklariert → Default True + soft_default=True (Soft-Migrate, analog I2
    Rev-12): sichtbar mit Warnung, statt die 8 Live-Klickdummies stumm zu droppen.
    """
    val = _discovery_block(spec).get("discoverable")
    if val is None:
        return (True, True)
    return (bool(val), False)


def _visibility_scope(spec: dict) -> str:
    """Sichtbarkeits-Scope (REC-6). Default `org` = geringste Exposition."""
    scope = _discovery_block(spec).get("visibility_scope")
    if scope in {"repo", "org", "allowlist", "public-demo"}:
        return scope
    return "org"


def _off_ramp_status(spec: dict) -> str:
    """Off-Ramp-Status für Lifecycle/Filter (REC-5/REC-16)."""
    return (spec.get("off_ramp") or {}).get("status_overall") or "static"


def _pipeline_status(spec: dict) -> str:
    """Pipeline-Status für Filter (REC-16). Default `klickdummy`."""
    return spec.get("pipeline_status") or "klickdummy"


def build_discovery_entry(repo_root: pathlib.Path, spec_path: pathlib.Path, spec: dict) -> dict:
    """Baut einen Discovery-Eintrag im v1.6-Schema (platform:ADR-215 §Amendment 1).

    Gegenüber v1.5 additiv: Provenance (`source_ref`/`commit_sha`/`spec_sha256`/
    `generated_at`), `registry_key`, `visibility_scope`, `discoverable`,
    `pipeline_status`/`off_ramp_status`, `tombstone`, `embedding_input_schema`.
    """
    repo_root = repo_root.resolve()
    rel = spec_path.resolve().relative_to(repo_root)
    org = _detect_org_from_repo(repo_root)
    repo_name = repo_root.name
    spec_id = spec.get("spec_id") or spec.get("bot_id") or str(rel)
    source_ref, commit_sha = _git_provenance(repo_root)
    discoverable, _soft = _is_discoverable(spec)
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    return {
        "schema_version": REGISTRY_SCHEMA_VERSION,
        "registry_key": _registry_key(org, repo_name, rel, spec_id),
        "spec_id": spec_id,
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
        # --- Filter-/Lifecycle-Felder (REC-5/REC-16) ---
        "pipeline_status": _pipeline_status(spec),
        "off_ramp_status": _off_ramp_status(spec),
        "visibility_scope": _visibility_scope(spec),
        "discoverable": discoverable,
        "tombstone": False,
        # --- Embedding (Input bleibt inspizierbar) ---
        "embedding_text": _build_embedding_text(spec),
        "embedding_input_schema": EMBEDDING_INPUT_SCHEMA,
        # --- Provenance / Drift-Anker (REC-1/REC-6) ---
        "source_repo": f"{org}/{repo_name}",
        "source_ref": source_ref,
        "commit_sha": commit_sha,
        "spec_sha256": _spec_sha256(spec_path),
        "generated_at": now,
        "last_seen": now,
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
                if not spec:
                    continue
                # Ingestion-Guard (REC-7): nur deklarierte I2-Klassen sind push-berechtigt.
                klass = spec.get("class", "?")
                if klass not in ALLOWED_CLASSES:
                    print(
                        f"⛔ {meta.spec_id}: class={klass!r} nicht push-berechtigt "
                        f"(erlaubt: {sorted(ALLOWED_CLASSES)}) — übersprungen.",
                        file=sys.stderr,
                    )
                    continue
                # Governance-Gate (REC-14): discovery.discoverable steuert Sichtbarkeit.
                discoverable, soft_default = _is_discoverable(spec)
                if not discoverable:
                    print(f"· {meta.spec_id}: discovery.discoverable=false — übersprungen.", file=sys.stderr)
                    continue
                if soft_default:
                    print(
                        f"⚠ {meta.spec_id}: `discovery.discoverable` nicht deklariert — "
                        f"Default true (Soft-Migrate). Explizit setzen, sonst greift später Strict-Mode.",
                        file=sys.stderr,
                    )
                entries.append(build_discovery_entry(repo_root, spec_path, spec))
            except Exception as e:
                print(f"⚠ {meta.spec_id} ({meta.path}): {e}", file=sys.stderr)
    return entries


def build_payload(entries: list[dict]) -> dict:
    """Versionierter Push-Envelope (REC-4/REC-10) — Vertrag mit der Discovery-API."""
    return {
        "api_version": API_VERSION,
        "registry_schema_version": REGISTRY_SCHEMA_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "entries": entries,
    }


def push_to_endpoint(
    entries: list[dict], endpoint: str, token: str | None = None, timeout: int = 10
) -> dict:
    """POSTet versionierten Envelope an Discovery-Endpoint. Stabile Error-Shape."""
    body = json.dumps(build_payload(entries)).encode("utf-8")
    headers = {
        "Content-Type": "application/json",
        "User-Agent": "iil-klickdummy",
        "X-Registry-Schema-Version": REGISTRY_SCHEMA_VERSION,
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(endpoint, data=body, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return {
                "status_code": resp.status,
                "body": resp.read().decode("utf-8", errors="replace")[:2000],
            }
    except urllib.error.HTTPError as e:
        return {"status_code": e.code, "body": e.read().decode("utf-8", errors="replace")[:2000]}
    except urllib.error.URLError as e:
        return {"status_code": 0, "body": f"URLError: {e.reason}"}


def build_snapshot(entries: list[dict]) -> dict:
    """Selbst-verifizierender Fallback-Snapshot (REC-3, Producer-Hälfte).

    Der Picker kann diesen Snapshot bei Orchestrator-Ausfall statt einer manuell
    gepflegten Konstante laden; `sha256` deckt Manipulation/Teil-Schreiben auf.
    """
    canonical = json.dumps(entries, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    digest = "sha256:" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return {
        "api_version": API_VERSION,
        "registry_schema_version": REGISTRY_SCHEMA_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "count": len(entries),
        "sha256": digest,
        "entries": entries,
    }


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
    ap_push.add_argument("--timeout", type=int, default=10, help="HTTP-Timeout in s (default 10)")
    ap_push.add_argument("--dry-run", action="store_true", help="Zeigt Payload, kein Push")
    ap_push.add_argument("--output", "-o", help="NDJSON in Datei statt stdout")
    ap_push.add_argument("--snapshot", help="Signierten Fallback-Snapshot (JSON) in Datei schreiben (REC-3)")

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
        # Fallback-Snapshot (REC-3) — unabhängig vom Push-Modus schreibbar.
        if args.snapshot:
            snap = build_snapshot(entries)
            pathlib.Path(args.snapshot).write_text(
                json.dumps(snap, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
            )
            print(f"✓ Snapshot ({snap['count']} entries, {snap['sha256'][:19]}…) → {args.snapshot}", file=sys.stderr)

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
            result = push_to_endpoint(entries, args.endpoint, token, timeout=args.timeout)
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

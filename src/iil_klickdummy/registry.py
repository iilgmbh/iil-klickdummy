"""Klickdummy Registry — Discovery von Klickdummies + Versionen (v1.1.0).

Scannt ein Repo (oder Cross-Repo) nach `klickdummy/<name>/screens-spec.yaml`
oder `*.yaml`-Specs, extrahiert Metadaten (name, class, title, spec_version,
ADR-Bezug), liest Versions-Historie aus Git und generiert eine statische
Browser-HTML.

Aufruf-Pfade:

    klickdummy-browser                     # repo-lokal, alle Klickdummies
    klickdummy-browser --output X.html     # eigenes Ausgabe-Ziel
    klickdummy-browser --repo <path>       # bestimmtes Repo scannen
    klickdummy-browser --cross-repo --base ~/github  # alle Repos

Pro platform:ADR-211 Rev 14 §Browser. Cross-Repo-Modus folgt in v1.2.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import subprocess
import sys
from dataclasses import dataclass, field
from importlib.resources import files

try:
    import yaml
except ImportError:
    print("FAIL (setup): PyYAML fehlt. pip install pyyaml")
    sys.exit(2)


@dataclass
class KlickdummyMeta:
    name: str
    path: str                  # relative Pfad zur Spec
    shell_path: str | None     # relative Pfad zur shell.html (oder None)
    spec_id: str
    spec_version: str
    klickdummy_class: str
    title: str
    adr_local: str | None
    sister_of: list[str] = field(default_factory=list)
    status: str = "active"     # aus ADR-Frontmatter, falls erreichbar
    sunset_after: str | None = None


@dataclass
class VersionInfo:
    spec_version: str          # aus Spec-File auf dem Commit
    commit_sha: str
    commit_date: str           # ISO


def _load_spec(path: pathlib.Path) -> dict:
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError):
        return {}


def discover_klickdummies(repo_root: pathlib.Path) -> list[KlickdummyMeta]:
    """Sucht klickdummy/<name>/screens-spec.yaml (Default-Konvention).

    Fallback: docs/01-architektur/mockups/<name>/screens-spec.yaml (meiki-hub).
    """
    out: list[KlickdummyMeta] = []
    candidates: list[pathlib.Path] = []
    for base in ("klickdummy", "docs/01-architektur/mockups"):
        d = repo_root / base
        if d.exists():
            candidates.extend(d.rglob("screens-spec.yaml"))
            candidates.extend(d.rglob("spec.yaml"))   # alt: writing-hub-Variante
    seen: set[pathlib.Path] = set()
    for spec_path in candidates:
        if spec_path in seen:
            continue
        seen.add(spec_path)
        spec = _load_spec(spec_path)
        if not spec or "spec_id" not in spec:
            continue
        rel = spec_path.relative_to(repo_root)
        name = rel.parent.name
        # shell.html im gleichen Verzeichnis?
        shell_candidate = spec_path.parent / "shell.html"
        shell_rel = (
            str(shell_candidate.relative_to(repo_root))
            if shell_candidate.exists() else None
        )
        adr = spec.get("adr", {}) or {}
        out.append(KlickdummyMeta(
            name=name,
            path=str(rel),
            shell_path=shell_rel,
            spec_id=spec.get("spec_id", "?"),
            spec_version=str(spec.get("spec_version", "0.0")),
            klickdummy_class=spec.get("class", spec.get("klickdummy_class", "?")),
            title=spec.get("title", name),
            adr_local=adr.get("local"),
            sister_of=adr.get("sister_of", []) or [],
        ))
    return sorted(out, key=lambda k: k.name)


def discover_versions(spec_path: pathlib.Path, repo_root: pathlib.Path) -> list[VersionInfo]:
    """Liest Git-History der Spec-Datei und extrahiert spec_version pro Commit.

    Nur Commits, die spec_version GEÄNDERT haben, kommen in die Liste.
    Sortiert: neueste zuerst.
    """
    if not (repo_root / ".git").exists():
        return []
    try:
        rel = spec_path.relative_to(repo_root)
        result = subprocess.run(
            ["git", "-C", str(repo_root), "log", "--pretty=%H|%cI", "--", str(rel)],
            capture_output=True, text=True, timeout=15,
        )
    except (OSError, subprocess.SubprocessError):
        return []
    if result.returncode != 0:
        return []
    versions: list[VersionInfo] = []
    seen_versions: set[str] = set()
    for line in result.stdout.splitlines():
        parts = line.strip().split("|")
        if len(parts) != 2:
            continue
        sha, date = parts
        try:
            blob = subprocess.run(
                ["git", "-C", str(repo_root), "show", f"{sha}:{rel}"],
                capture_output=True, text=True, timeout=5,
            )
            if blob.returncode != 0:
                continue
            data = yaml.safe_load(blob.stdout) or {}
        except (OSError, subprocess.SubprocessError, yaml.YAMLError):
            continue
        v = str(data.get("spec_version", ""))
        if v and v not in seen_versions:
            versions.append(VersionInfo(spec_version=v, commit_sha=sha, commit_date=date))
            seen_versions.add(v)
    return versions


def collect_versions_with_snapshots(
    klickdummies: list[KlickdummyMeta],
    repo_root: pathlib.Path,
    output_dir: pathlib.Path,
) -> dict[str, list[dict]]:
    """Historische Spec-Versionen je KD + shell.html-Snapshots aus Git.

    Schreibt für jede frühere spec_version (HEAD ausgenommen) den damaligen
    shell.html-Stand nach <output_dir>/klickdummy-versions/<kd>/<version>/
    und liefert {kd_name: [{spec_version, commit_sha, commit_date,
    shell_path|None}]} — shell_path relativ zu output_dir (= iframe-Basis).
    """
    out: dict[str, list[dict]] = {}
    for k in klickdummies:
        versions = discover_versions(repo_root / k.path, repo_root)
        entries: list[dict] = []
        for v in versions:
            if v.spec_version == k.spec_version:
                continue  # HEAD-Stand — iframe lädt das Live-shell.html
            shell_rel: str | None = None
            if k.shell_path:
                try:
                    blob = subprocess.run(
                        ["git", "-C", str(repo_root), "show",
                         f"{v.commit_sha}:{pathlib.PurePosixPath(k.shell_path)}"],
                        capture_output=True, text=True, timeout=5,
                    )
                except (OSError, subprocess.SubprocessError):
                    blob = None
                if blob is not None and blob.returncode == 0 and blob.stdout:
                    snap = (output_dir / "klickdummy-versions" / k.name
                            / v.spec_version / "shell.html")
                    snap.parent.mkdir(parents=True, exist_ok=True)
                    snap.write_text(blob.stdout, encoding="utf-8")
                    shell_rel = snap.relative_to(output_dir).as_posix()
            entries.append({
                "spec_version": v.spec_version,
                "commit_sha": v.commit_sha[:10],
                "commit_date": v.commit_date[:10],
                "shell_path": shell_rel,
            })
        if entries:
            out[k.name] = entries
    return out


def discover_cross_repo(
    base: pathlib.Path,
    repos: list[str],
) -> list[tuple[str, str, KlickdummyMeta]]:
    """Stufe-3 (v1.3): scan über mehrere Repos.

    Returns list of (org, repo_name, klickdummy) tuples.
    org wird aus git remote URL detektiert (Fallback: 'unknown-org').
    """
    import re as _re
    import subprocess as _sp
    out: list[tuple[str, str, KlickdummyMeta]] = []
    for repo in repos:
        repo_root = base / repo
        if not repo_root.exists() or not repo_root.is_dir():
            continue
        # org-Detect
        org = "unknown-org"
        try:
            res = _sp.run(
                ["git", "-C", str(repo_root), "remote", "get-url", "origin"],
                capture_output=True, text=True, timeout=5,
            )
            if res.returncode == 0:
                m = _re.search(r"github\.com[:/]([^/]+)/", res.stdout)
                if m:
                    org = m.group(1)
        except (OSError, _sp.SubprocessError):
            pass
        for km in discover_klickdummies(repo_root):
            out.append((org, repo, km))
    return out


def discover_cross_repo_stories(
    base: pathlib.Path,
    triples: list[tuple[str, str, KlickdummyMeta]],
) -> list[dict]:
    """Stories aller Repos einsammeln; step.kd_index auf die kombinierte
    Cross-Repo-KD-Liste (triples-Reihenfolge) remappen.

    Vorher wurden Stories im Cross-Repo-Modus gar nicht übergeben.
    """
    global_idx: dict[str, list[int]] = {}
    for i, (_org, repo, _km) in enumerate(triples):
        global_idx.setdefault(repo, []).append(i)
    out: list[dict] = []
    for repo in global_idx:
        repo_kds = [km for _o, r, km in triples if r == repo]
        for story in discover_stories(base / repo, repo_kds):
            for step in story["steps"]:
                step["kd_index"] = global_idx[repo][step["kd_index"]]
            out.append(story)
    return out


def discover_stories(
    repo_root: pathlib.Path,
    klickdummies: list[KlickdummyMeta],
) -> list[dict]:
    """Scannt klickdummy/stories/*.yaml und löst step.kd gegen KD-Liste auf.

    Gibt Liste von Story-Dicts zurück; Steps mit unbekanntem kd-Namen werden
    übersprungen (stderr-Warning, kein Abbruch). Kein stories/-Verzeichnis →
    leere Liste (rückwärtskompatibel).
    """
    stories_dir = repo_root / "klickdummy" / "stories"
    if not stories_dir.exists():
        return []
    kd_index = {k.name: i for i, k in enumerate(klickdummies)}
    out: list[dict] = []
    for p in sorted(stories_dir.glob("*.yaml")) + sorted(stories_dir.glob("*.yml")):
        try:
            raw = _load_spec(p)
        except Exception:
            continue
        if not raw or not raw.get("id") or not raw.get("title") or not raw.get("steps"):
            print(f"  ⚠ story {p.name}: id/title/steps fehlen — übersprungen", file=sys.stderr)
            continue
        resolved_steps: list[dict] = []
        for step in raw.get("steps") or []:
            kd_name = step.get("kd", "")
            idx = kd_index.get(kd_name)
            if idx is None:
                print(f"  ⚠ story {raw['id']}: kd={kd_name!r} nicht gefunden — Step übersprungen", file=sys.stderr)
                continue
            resolved_steps.append({"kd_name": kd_name, "label": step.get("label", kd_name), "kd_index": idx})
        if not resolved_steps:
            print(f"  ⚠ story {raw['id']}: keine gültigen Steps — übersprungen", file=sys.stderr)
            continue
        out.append({
            "id": raw["id"],
            "title": raw["title"],
            "description": raw.get("description", ""),
            "persona": raw.get("persona", ""),
            "steps": resolved_steps,
        })
    return out


def write_stories_manifest(
    output_dir: pathlib.Path,
    klickdummies: list[KlickdummyMeta],
    stories: list[dict],
) -> pathlib.Path | None:
    """Schreibt stories-manifest.json neben die Browser-HTML.

    Enthält eine `kd_to_stories`-Map: kd_name → Liste von Story-Kontexten mit
    step_index, step_total, prev/next KD-Namen + shell-Pfaden (repo-root-relativ).
    Renders laden diesen Manifest via fetch('../../stories-manifest.json')
    und bauen den Story-Banner. Gibt None zurück wenn keine Stories vorhanden.
    """
    if not stories:
        return None
    kd_shell: dict[str, str | None] = {k.name: k.shell_path for k in klickdummies}
    kd_to_stories: dict[str, list] = {}
    for story in stories:
        steps = story["steps"]
        total = len(steps)
        for idx, step in enumerate(steps):
            kd_name = step["kd_name"]
            prev_step = steps[idx - 1] if idx > 0 else None
            next_step = steps[idx + 1] if idx < total - 1 else None
            entry = {
                "story_id": story["id"],
                "story_title": story["title"],
                "step_index": idx,       # 0-basiert
                "step_total": total,
                "step_label": step["label"],
                "prev_kd": prev_step["kd_name"] if prev_step else None,
                "prev_label": prev_step["label"] if prev_step else None,
                "prev_shell": kd_shell.get(prev_step["kd_name"]) if prev_step else None,
                "next_kd": next_step["kd_name"] if next_step else None,
                "next_label": next_step["label"] if next_step else None,
                "next_shell": kd_shell.get(next_step["kd_name"]) if next_step else None,
            }
            kd_to_stories.setdefault(kd_name, []).append(entry)
    manifest = {"stories": stories, "kd_to_stories": kd_to_stories}
    out = output_dir / "stories-manifest.json"
    out.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return out


def _embed_json(obj) -> str:
    """JSON für die Einbettung in eine `<script>`-Insel serialisieren (S-01-Fix).

    Der HTML-Parser beendet JEDES `<script>`-Element (auch `type="application/json"`)
    an einem literalen `</script>`. Ein Klickdummy-Feld (z.B. `title`) mit Substring
    `</script>` bräche sonst aus dem Script-Kontext aus (XSS). `</` → `<\\/` neutralisiert
    das; JSON.parse liest `<\\/` wieder als `</`. Zusätzlich `<!--`/`-->` entschärfen,
    die einen HTML-Kommentar im Script öffnen/schließen könnten.
    """
    s = json.dumps(obj, ensure_ascii=False, indent=2)
    return s.replace("</", "<\\/").replace("<!--", "<\\!--").replace("-->", "--\\>")


def render_browser_html(
    klickdummies: list[KlickdummyMeta],
    output: pathlib.Path,
    repo_label: str = "(current repo)",
    stories: list[dict] | None = None,
    repo_root: pathlib.Path | None = None,
) -> None:
    """Schreibt statische Browser-HTML mit Listbox + iframe (Single-Repo).

    Mit repo_root wird die Git-Versionshistorie je KD eingebettet
    (Versions-Switcher) inkl. shell.html-Snapshots früherer Versionen.
    """
    output.parent.mkdir(parents=True, exist_ok=True)
    versions_map: dict[str, list[dict]] = {}
    if repo_root is not None:
        versions_map = collect_versions_with_snapshots(
            klickdummies, repo_root, output.parent
        )
    template = files("iil_klickdummy.snippets") / "browser" / "browser.html.tmpl"
    tmpl_text = template.read_text(encoding="utf-8")
    data = [
        {
            "name": k.name,
            "path": k.path,
            "shell_path": k.shell_path,
            "spec_id": k.spec_id,
            "spec_version": k.spec_version,
            "class": k.klickdummy_class,
            "title": k.title,
            "adr_local": k.adr_local,
            "sister_of": k.sister_of,
            "versions": versions_map.get(k.name, []),
        }
        for k in klickdummies
    ]
    html = tmpl_text.replace("__KLICKDUMMIES_JSON__", _embed_json(data))
    html = html.replace("__STORIES_JSON__", _embed_json(stories or []))
    html = html.replace("__REPO_LABEL__", repo_label)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(html, encoding="utf-8")
    write_stories_manifest(output.parent, klickdummies, stories or [])


def render_cross_repo_browser_html(
    triples: list[tuple[str, str, KlickdummyMeta]],
    output: pathlib.Path,
    base_label: str = "cross-repo",
    stories: list[dict] | None = None,
) -> None:
    """v1.3: Browser-HTML aus mehreren Repos. shell_path wird absolut/repo-prefixed.

    Klickdummy-Daten enthalten zusätzlich `org` und `repo` für UI-Gruppierung.
    """
    template = files("iil_klickdummy.snippets") / "browser" / "browser.html.tmpl"
    tmpl_text = template.read_text(encoding="utf-8")
    data = [
        {
            "name": k.name,
            "org": org,
            "repo": repo,
            "path": f"{repo}/{k.path}",
            # shell_path bleibt relative zum repo — iframe braucht ggf. file://-Präfix
            # bei Cross-Repo: kein direkter iframe-Link, stattdessen GitHub-Link
            "shell_path": k.shell_path,
            "github_shell_url": f"https://github.com/{org}/{repo}/blob/main/{k.shell_path}" if k.shell_path else None,
            "github_spec_url": f"https://github.com/{org}/{repo}/blob/main/{k.path}",
            "spec_id": k.spec_id,
            "spec_version": k.spec_version,
            "class": k.klickdummy_class,
            "title": k.title,
            "adr_local": k.adr_local,
            "sister_of": k.sister_of,
        }
        for org, repo, k in triples
    ]
    html = tmpl_text.replace("__KLICKDUMMIES_JSON__", _embed_json(data))
    html = html.replace("__STORIES_JSON__", _embed_json(stories or []))
    html = html.replace("__REPO_LABEL__", f"cross-repo · {base_label} · {len(data)} Klickdummies")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(html, encoding="utf-8")


# -- CLI ---------------------------------------------------------------------

DEFAULT_CROSS_REPOS = ["meiki-hub", "writing-hub", "risk-hub", "ttz-hub", "pptx-hub", "dev-hub"]


def _serve(html_path: pathlib.Path, port: int) -> int:
    """v1.3: lokaler HTTP-Server, öffnet Browser-HTML in nem Verzeichnis."""
    import http.server
    import socketserver
    import os
    import sys
    os.chdir(html_path.parent)
    handler = http.server.SimpleHTTPRequestHandler
    with socketserver.TCPServer(("", port), handler) as httpd:
        url = f"http://localhost:{port}/{html_path.name}"
        print("== Klickdummy-Browser (serve) ==", file=sys.stderr)
        print(f"  URL: {url}", file=sys.stderr)
        print("  Ctrl-C zum Beenden", file=sys.stderr)
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n  Server beendet.", file=sys.stderr)
    return 0


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", default=".", help="Repo-Root (single-repo modus)")
    parser.add_argument("--output", default="./klickdummy-browser.html",
                        help="Output-Pfad für Browser-HTML")
    parser.add_argument("--cross-repo", action="store_true",
                        help="v1.3: aggregiere mehrere Repos unter --base")
    parser.add_argument("--base", default="~/github",
                        help="Cross-Repo Base (default ~/github)")
    parser.add_argument("--repos", default=",".join(DEFAULT_CROSS_REPOS),
                        help="Komma-Liste der Repo-Namen für --cross-repo")
    parser.add_argument("--json", action="store_true",
                        help="Statt HTML JSON-Inventory auf stdout")
    parser.add_argument("--serve", type=int, default=None, metavar="PORT",
                        help="v1.3: HTML schreiben und HTTP-Server auf PORT starten")
    args = parser.parse_args(argv)

    if args.cross_repo:
        base = pathlib.Path(args.base).expanduser().resolve()
        repos = [r.strip() for r in args.repos.split(",") if r.strip()]
        triples = discover_cross_repo(base, repos)
        print("== Klickdummy-Registry Cross-Repo (v1.3) ==", file=sys.stderr)
        print(f"  Base : {base}", file=sys.stderr)
        print(f"  Repos: {len(repos)} configured · {len({r for _,r,_ in triples})} found Klickdummies", file=sys.stderr)
        # Gruppierung nach Repo für Output
        by_repo: dict = {}
        for org, repo, km in triples:
            by_repo.setdefault((org, repo), []).append(km)
        for (org, repo), kms in sorted(by_repo.items()):
            print(f"  · {org}/{repo} ({len(kms)} KD)", file=sys.stderr)
            if not args.json:
                for k in kms:
                    print(f"      - {k.name:30s}  v{k.spec_version}  [{k.klickdummy_class}]",
                          file=sys.stderr)
        print(f"  Total: {len(triples)} Klickdummies cross-repo", file=sys.stderr)

        if args.json:
            out = [{"org": o, "repo": r, "name": k.name, "spec_id": k.spec_id,
                    "spec_version": k.spec_version, "class": k.klickdummy_class,
                    "title": k.title, "adr_local": k.adr_local,
                    "sister_of": k.sister_of,
                    "shell_path": k.shell_path, "path": k.path}
                   for o, r, k in triples]
            print(json.dumps(out, ensure_ascii=False, indent=2))
            return 0

        if not triples:
            print("  → keine Klickdummies — keine Browser-HTML generiert.", file=sys.stderr)
            return 0

        out_path = pathlib.Path(args.output).expanduser().resolve()
        cr_stories = discover_cross_repo_stories(base, triples)
        if cr_stories:
            print(f"  Stories: {len(cr_stories)} gefunden cross-repo", file=sys.stderr)
        render_cross_repo_browser_html(triples, out_path, base_label=base.name,
                                       stories=cr_stories)
        print(f"  → Cross-Repo-Browser: {out_path}", file=sys.stderr)
        if args.serve is not None:
            return _serve(out_path, args.serve)
        return 0

    # Single-Repo-Modus (v1.1-Stand)
    repo_root = pathlib.Path(args.repo).expanduser().resolve()
    if not repo_root.exists():
        print(f"FAIL: Repo-Root nicht gefunden: {repo_root}", file=sys.stderr)
        return 2

    print("== Klickdummy-Registry (v1.3) ==", file=sys.stderr)
    print(f"  Repo : {repo_root}", file=sys.stderr)
    klickdummies = discover_klickdummies(repo_root)
    print(f"  Gefunden: {len(klickdummies)} Klickdummy(ies)", file=sys.stderr)
    for k in klickdummies:
        if not args.json:
            print(f"    · {k.name:35s}  v{k.spec_version}  [{k.klickdummy_class}]  ({k.adr_local or 'kein ADR-Ref'})", file=sys.stderr)

    if args.json:
        out = [
            {"name": k.name, "path": k.path, "shell_path": k.shell_path,
             "spec_id": k.spec_id, "spec_version": k.spec_version,
             "class": k.klickdummy_class, "title": k.title,
             "adr_local": k.adr_local, "sister_of": k.sister_of}
            for k in klickdummies
        ]
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return 0

    if not klickdummies:
        print("  → keine Klickdummies — keine Browser-HTML generiert.", file=sys.stderr)
        return 0

    stories = discover_stories(repo_root, klickdummies)
    if stories:
        print(f"  Stories: {len(stories)} gefunden ({', '.join(s['id'] for s in stories)})", file=sys.stderr)
    out_path = pathlib.Path(args.output).expanduser().resolve()
    render_browser_html(klickdummies, out_path, repo_label=repo_root.name,
                        stories=stories, repo_root=repo_root)
    print(f"  → Browser geschrieben: {out_path}", file=sys.stderr)
    if args.serve is not None:
        return _serve(out_path, args.serve)
    return 0


def main_cli() -> int:
    return main(sys.argv[1:])


if __name__ == "__main__":
    sys.exit(main_cli())

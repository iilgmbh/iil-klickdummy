#!/usr/bin/env python3
"""Stories-Manifest für den Genesor/Vendored-Layout schreiben.

Lücke (entdeckt 2026-06-02): der Genesor-Renderer (`lineage.py --genesor`) erzeugt
das Story-Banner-JS in jedem KD-Render (fetcht `../../stories-manifest.json`),
**schreibt das Manifest aber nicht** — `write_stories_manifest` lebt nur im
`klickdummy-browser`-Render (registry.py) und nutzt dessen Layout (`shell_path`).

Dieses Tool schließt die Lücke für den iil.pet-**Vendored-Layout**:
KD-Render liegt unter `kd/<repo>/klickdummy/<kd>/index.html` → `../../` =
`kd/<repo>/klickdummy/`. Darum: Manifest dorthin + prev/next_shell = `<kd>/index.html`.

Aufruf:  klickdummy-stories-manifest <repo_root> <out_dir> [shell_prefix]
  <repo_root>:   Consumer-Repo (mit klickdummy/stories/*.yaml + klickdummy/*/)
  <out_dir>:     Zielverzeichnis (wohin `../../` der Renders zeigt — beim
                 Vendored-Layout kd/<repo>/klickdummy/<kd>/index.html ist das
                 `kd/<repo>/`, NICHT `kd/<repo>/klickdummy/`).
  [shell_prefix]: Präfix für prev/next-Shell-Pfade relativ zu out_dir
                 (Vendored-Layout: `klickdummy/` → Link `klickdummy/<kd>/index.html`).
Exit:    0 (auch wenn keine Stories → kein Manifest, kein Fehler), 2 = Usage
"""
from __future__ import annotations

import json
import pathlib
import sys


def _shell(step: dict | None, prefix: str = "") -> str | None:
    # Nav-Ziel relativ zu out_dir (= ../../ der Renders): <prefix><kd>/index.html
    return (prefix + step["kd_name"] + "/index.html") if step else None


def build_manifest(repo_root: pathlib.Path, shell_prefix: str = "") -> dict | None:
    """Baut das stories-manifest (kd_to_stories) für den Vendored-Layout.

    shell_prefix: Pfad-Präfix der KD-Renders relativ zum Manifest-Verzeichnis
    (z.B. "klickdummy/", weil das Manifest in kd/<repo>/ liegt, die Renders aber
    in kd/<repo>/klickdummy/<kd>/). Gibt None zurück, wenn keine Stories da sind.
    """
    from iil_klickdummy.registry import discover_klickdummies, discover_stories

    kds = discover_klickdummies(repo_root)
    stories = discover_stories(repo_root, kds)
    if not stories:
        return None

    kd_to_stories: dict[str, list] = {}
    for story in stories:
        steps = story["steps"]
        total = len(steps)
        for idx, step in enumerate(steps):
            prev_step = steps[idx - 1] if idx > 0 else None
            next_step = steps[idx + 1] if idx < total - 1 else None
            kd_to_stories.setdefault(step["kd_name"], []).append({
                "story_id": story["id"],
                "story_title": story["title"],
                "step_index": idx,       # 0-basiert
                "step_total": total,
                "step_label": step["label"],
                "prev_kd": prev_step["kd_name"] if prev_step else None,
                "prev_label": prev_step["label"] if prev_step else None,
                "prev_shell": _shell(prev_step, shell_prefix),
                "next_kd": next_step["kd_name"] if next_step else None,
                "next_label": next_step["label"] if next_step else None,
                "next_shell": _shell(next_step, shell_prefix),
            })
    return {"stories": stories, "kd_to_stories": kd_to_stories}


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print("Usage: klickdummy-stories-manifest <repo_root> <out_dir> [shell_prefix]")
        return 2
    repo_root = pathlib.Path(argv[0])
    out_dir = pathlib.Path(argv[1])
    shell_prefix = argv[2] if len(argv) > 2 else ""
    manifest = build_manifest(repo_root, shell_prefix)
    if manifest is None:
        print(f"· {repo_root}: keine Stories — kein Manifest geschrieben.")
        return 0
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / "stories-manifest.json"
    out.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"✓ {out} ({len(manifest['kd_to_stories'])} KDs, {len(manifest['stories'])} Stories)")
    return 0


def main_cli() -> int:
    """Console-Script entry (pyproject.toml [project.scripts])."""
    return main(sys.argv[1:])


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

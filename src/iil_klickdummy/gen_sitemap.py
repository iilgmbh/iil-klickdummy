#!/usr/bin/env python3
"""Generator für die KD-Sitemap + kd-tree.json (Navigations-Index) eines Repos.

Scannt `<repo_root>/klickdummy/**/screens-spec.yaml`, baut die Hierarchie aus
spec_id + spec_role + kd_children, emittiert:

  - klickdummy/_shared/kd-tree.json + kd-tree.js  (von kd-nav.js eingelesen)
  - klickdummy/sitemap/index.html                 (Sitemap-HTML)
  - klickdummy/sitemap/screens-spec.yaml           (Sitemap-Spec, ADR-211 I1)

Neuanlauf bei jeder KD-Änderung (Make-Target `klickdummy-sitemap`, s. ADR-211).

Extrahiert aus risk-hub `scripts/gen_kd_sitemap.py` (Rev 13) — Konvention wie
`gen_stories_manifest.py`: repo-agnostisch, `<repo_root>` als CLI-Arg.

Konformität: platform:ADR-211.
"""

from __future__ import annotations

import datetime
import json
import pathlib
import sys
from typing import Any

import yaml


def _load_specs(kd_root: pathlib.Path) -> list[dict[str, Any]]:
    specs: list[dict[str, Any]] = []
    for p in sorted(kd_root.rglob("*.screens-spec.yaml")) + sorted(
        kd_root.rglob("screens-spec.yaml")
    ):
        # Sitemap-Spec selbst überspringen (würde sich rekursiv listen, Issue
        # #170): `generate()` schreibt sie nach `<kd_root>/sitemap/screens-
        # spec.yaml` — der alte Guard prüfte auf den nie geschriebenen
        # Dateinamen "index.screens-spec.yaml" und griff dadurch nie. Symptom:
        # die allererste Generierung (sitemap/ existiert noch nicht) zählt
        # sich selbst nicht mit, die zweite (Datei jetzt vorhanden) schon —
        # ein einmaliger Idempotenz-Sprung, der den Drift-Gate fälschlich rot
        # färbt, sobald der Erst-Stand committed wurde.
        if p.parent.name == "sitemap" and p.name == "screens-spec.yaml":
            continue
        try:
            data = yaml.safe_load(p.read_text(encoding="utf-8"))
        except yaml.YAMLError:
            continue
        if not isinstance(data, dict) or "spec_id" not in data:
            continue
        html_path = (
            p.with_suffix("").with_suffix(".html")
            if p.name.endswith(".screens-spec.yaml")
            else p.parent / "index.html"
        )
        if not html_path.exists():
            continue
        data["__path__"] = html_path
        data["__rel_to_kd__"] = html_path.relative_to(kd_root)
        specs.append(data)
    # Deduplikat: pro spec_id genau ein Eintrag (erste Datei gewinnt)
    seen: dict[str, dict[str, Any]] = {}
    for s in specs:
        sid = s["spec_id"]
        if sid not in seen:
            seen[sid] = s
    return list(seen.values())


def _build_tree(specs: list[dict[str, Any]]) -> dict[str, Any]:
    """Bauen: spec_id -> {role, title, class, off_ramp_status, path, parent, children, prev, next}"""
    by_id: dict[str, dict[str, Any]] = {}
    for s in specs:
        sid = s["spec_id"]
        screens = s.get("screens") or []
        off_ramp_overall = (s.get("off_ramp") or {}).get("status_overall", "")
        # off_ramp_status pro Screen aggregieren (worst case: static)
        statuses = [scr.get("off_ramp_status", "static") for scr in screens]
        worst = "static"
        for st in ["removed", "parity-green", "parity-staging", "static"]:
            if st in statuses:
                worst = st
                break
        by_id[sid] = {
            "spec_id": sid,
            "title": s.get("title", sid),
            "role": s.get("spec_role", "branch"),
            "class": s.get("class", "mock"),
            "screens_count": len(screens),
            "off_ramp_status": worst,
            "off_ramp_overall": off_ramp_overall,
            "path": str(s["__rel_to_kd__"]).replace("\\", "/"),
            "parent": None,
            "children": [],
            # kd_children = intra-repo Baum-Hierarchie (spec_ids). consumes_from
            # ist dagegen für den Cross-Repo-Drift-Checker reserviert (ADR-NNN-Refs).
            "kd_children": list(s.get("kd_children") or []),
        }
    # parent/children aus kd_children (spec_ids) ableiten
    for sid, node in by_id.items():
        for child_id in node["kd_children"]:
            if child_id in by_id and by_id[child_id]["parent"] is None:
                by_id[child_id]["parent"] = sid
                node["children"].append(child_id)
    # Tour-Reihenfolge: depth-first ab den Roots
    roots = sorted([sid for sid, n in by_id.items() if n["role"] == "root"])
    order: list[str] = []

    def _visit(sid: str) -> None:
        order.append(sid)
        for ch in by_id[sid]["children"]:
            _visit(ch)

    for r in roots:
        _visit(r)
    # prev/next setzen
    for i, sid in enumerate(order):
        by_id[sid]["prev"] = order[i - 1] if i > 0 else None
        by_id[sid]["next"] = order[i + 1] if i < len(order) - 1 else None
    return {"roots": roots, "order": order, "nodes": by_id}


def _write_kd_tree_json(shared_dir: pathlib.Path, tree: dict[str, Any]) -> None:
    shared_dir.mkdir(parents=True, exist_ok=True)
    # JSON-Variante für Tools (CLI, CI-Checks); JS-Variante für KD-Browser
    # (file:// erlaubt <script src>, blockt aber fetch() — daher beide Formen).
    body = json.dumps(tree, indent=2, ensure_ascii=False)
    (shared_dir / "kd-tree.json").write_text(body, encoding="utf-8")
    (shared_dir / "kd-tree.js").write_text(
        "// auto-generiert von klickdummy-gen-sitemap — bitte NICHT editieren\n"
        f"window.__KD_TREE__ = {body};\n",
        encoding="utf-8",
    )


STATUS_COLOR = {
    "static": "bg-gray-100 text-gray-700",
    "parity-staging": "bg-amber-100 text-amber-800",
    "parity-green": "bg-green-100 text-green-800",
    "removed": "bg-zinc-200 text-zinc-500 line-through",
}


def _render_sitemap(tree: dict[str, Any], repo_name: str) -> str:
    nodes = tree["nodes"]
    sections: list[str] = []

    # Sitemap liegt unter klickdummy/sitemap/index.html — Pfade zu anderen KDs
    # (relativ zur klickdummy/-Wurzel) brauchen ein "../" voran.
    def rel(p: str) -> str:
        return "../" + p

    for root_id in tree["roots"]:
        root = nodes[root_id]
        rows: list[str] = []
        rows.append(
            f'<tr class="border-b bg-orange-50" data-testid="row-{root_id.replace(":", "-").replace(".", "-")}">'
            f'<td class="py-2 pl-2"><b>{root["title"]}</b><div class="text-[10px] text-gray-400">{root["spec_id"]}</div></td>'
            f'<td class="text-[11px]">root</td>'
            f'<td><span class="text-[10px] px-1.5 py-0.5 rounded {STATUS_COLOR.get(root["off_ramp_status"], "")}">{root["off_ramp_status"]}</span></td>'
            f'<td class="text-[11px]">{root["screens_count"]}</td>'
            f'<td><a href="{rel(root["path"])}" data-testid="link-{root_id}" target="_blank" class="text-orange-600 hover:underline text-sm">→ öffnen</a></td>'
            f"</tr>"
        )
        for child_id in root["children"]:
            ch = nodes[child_id]
            rows.append(
                f'<tr class="border-b" data-testid="row-{child_id.replace(":", "-").replace(".", "-")}">'
                f'<td class="py-2 pl-6">↳ {ch["title"].split(" — ", 1)[-1] if " — " in ch["title"] else ch["title"]}<div class="text-[10px] text-gray-400">{ch["spec_id"]}</div></td>'
                f'<td class="text-[11px] text-gray-500">branch</td>'
                f'<td><span class="text-[10px] px-1.5 py-0.5 rounded {STATUS_COLOR.get(ch["off_ramp_status"], "")}">{ch["off_ramp_status"]}</span></td>'
                f'<td class="text-[11px]">{ch["screens_count"]}</td>'
                f'<td><a href="{rel(ch["path"])}" data-testid="link-{child_id}" target="_blank" class="text-gray-600 hover:underline text-sm">→ öffnen</a></td>'
                f"</tr>"
            )
        sections.append(
            f'<div class="bg-white rounded-lg shadow p-4 mb-4" data-testid="tree-{root_id.replace(":", "-").replace(".", "-")}">'
            f'<table class="w-full text-sm"><thead><tr class="text-left text-xs text-gray-500 border-b">'
            f'<th class="py-2 pl-2">Knoten</th><th>Rolle</th><th>Off-Ramp</th><th>Screens</th><th></th></tr></thead>'
            f"<tbody>{''.join(rows)}</tbody></table></div>"
        )

    # Orphans (Knoten ohne Parent und nicht root)
    orphans = [n for n in nodes.values() if n["role"] != "root" and n["parent"] is None]
    orphan_block = ""
    if orphans:
        rows = "".join(
            f'<li data-testid="orphan-{o["spec_id"].replace(":", "-")}" class="border-b py-1 flex justify-between">'
            f'<span>{o["title"]} <code class="text-[10px] text-gray-400">{o["spec_id"]}</code></span>'
            f'<a href="{rel(o["path"])}" class="text-xs text-orange-600">→ öffnen</a></li>'
            for o in orphans
        )
        orphan_block = (
            '<div class="bg-amber-50 border border-amber-200 rounded-lg p-4 mb-4" data-testid="orphans">'
            '<h3 class="font-semibold text-sm mb-2 text-amber-800">⚠ Waisen-Knoten (kein Eltern-Root)</h3>'
            f'<ul class="text-sm">{rows}</ul></div>'
        )

    return f"""<!DOCTYPE html>
<!--
  Klick-Dummy SITEMAP — automatisch generiert von `klickdummy-gen-sitemap`.
  Bei jeder KD-Änderung neu laufen lassen.
  Vertrag: klickdummy/sitemap/screens-spec.yaml
-->
<html lang="de"><head><meta charset="UTF-8"><meta name="klickdummy_class" content="mock">
<title>Klick-Dummy Sitemap — {repo_name}</title>
<script src="https://cdn.tailwindcss.com"></script><script src="https://unpkg.com/lucide@latest"></script></head>
<body class="bg-gray-50 min-h-screen">
<div class="bg-amber-50 border-b border-amber-200 px-6 py-2 text-xs text-amber-800">
 <strong>Klick-Dummy Sitemap</strong>&nbsp;auto-generiert · Hauptmenü aller KD-Bäume im {repo_name}
</div>
<div class="max-w-6xl mx-auto px-6 py-6">
 <h1 class="text-2xl font-bold text-orange-700 mb-2">Sitemap — {repo_name} Klickdummies</h1>
 <p class="text-sm text-gray-600 mb-6">Alle KD-Bäume mit Knoten-Hierarchie, Off-Ramp-Status (ADR-211 §I3) und Spec-ID (§I4).
  Tour-Mode: hänge <code class="text-xs bg-gray-200 px-1 rounded">?tour=1</code> an die URL eines Knotens, um den Walkthrough zu starten.</p>
 <div class="text-xs text-gray-500 mb-4" data-testid="stats">
  <b>{len(tree["roots"])}</b> Wurzeln · <b>{len(tree["order"])}</b> Knoten gesamt · {sum(1 for n in nodes.values() if n["off_ramp_status"] == "parity-green")} parity-green
 </div>
 {"".join(sections)}
 {orphan_block}
 <p class="text-xs text-gray-400 mt-6">Generiert: <code class="text-[10px]">klickdummy-gen-sitemap</code> (iil-klickdummy). Quelle: jede <code class="text-[10px]">screens-spec.yaml</code> im klickdummy/-Baum (ADR-211 I1).</p>
</div>
<script>
const PH=[{{id:"sitemap",t:"Sitemap"}}];
let idx=0;
function go(){{lucide.createIcons();}}
go();
</script>
<script src="../_shared/kd-nav.js" data-sitemap="index.html" data-spec-id="{repo_name}:klickdummy-spec-sitemap"></script>
</body></html>
"""


def _render_sitemap_spec(repo_name: str, adr_local: str, spec_date: str) -> str:
    return f"""# platform:ADR-211 — I1 Spec (maschinenlesbar) — Sitemap-Knoten (Top-Level)
# Konformität: klickdummy-i1 klickdummy/sitemap/screens-spec.yaml:<schema>
# HTML-Renderer: klickdummy/sitemap/index.html (auto-generiert von klickdummy-gen-sitemap)
$schema: https://raw.githubusercontent.com/achimdehnert/platform/main/packages/iil-klickdummy/src/iil_klickdummy/schemas/screens-spec.schema.json

spec_id: {repo_name}:klickdummy-spec-sitemap
spec_version: "0.1"
spec_date: "{spec_date}"
spec_role: root
title: "Klickdummy-Sitemap — Hauptmenü aller {repo_name} KD-Bäume"

adr:
  local: {adr_local}
  conforms_to: platform:ADR-211

class: mock
class_evidence:
  no_backend: true
  no_demo_param: true
  target_mocks_visible: true
  systemgrenzen:
    - "Auto-generiert aus allen screens-spec.yaml im Repo"
    - "Keine interaktive Logik außer Links + Tour-Mode-Footer (via kd-nav.js)"

grounding:
  konzept: "platform:ADR-211 §I4 Hierarchie"
  konzept_id: "platform:ADR-211"
  konzept_version: "n/a"
  pilot: "{repo_name} Klickdummy-Baum (alle Specs)"
  rechtsrahmen_kernnormen:
    organisatorisch: "Übersicht aller KDs als Navigations- und Off-Ramp-Hilfsmittel"

off_ramp:
  policy: "platform:ADR-211"
  unit: per-screen
  rule: "Sitemap selbst ist immer static (mock-Klasse, kein App-Counterpart)"
  doppelquell_grenze: prod-release
  staging_doppelquell: allowed
  parity_runner: "make klickdummy-i3"
  status_overall: "Phase A — Sitemap permanent"

personas:
  alle:
    label: "Alle Rollen"
    rolle: "Stakeholder, Entwickler, DSB — wer auch immer einen Überblick braucht"
    sieht:
      - "Pro KD-Baum Tabelle mit Knoten, Rolle (root/branch), Off-Ramp-Status, Screens-Anzahl, Sprung-Link"
      - "Waisen-Knoten (Branches ohne Root) als Warnung"
      - "Tour-Mode-Hinweis"

screens:
  - id: sitemap-overview
    title: "Sitemap-Übersicht aller KD-Bäume"
    personas: [alle]
    purpose: "Hauptmenü — auf einer Seite jeden Klickdummy mit Position im Baum, Off-Ramp-Status und Sprung-Link erreichen. Auto-generiert; spiegelt den aktuellen Stand der screens-spec.yaml-Dateien."
    konzept_ref: ["platform:ADR-211#I4"]
    parity_acceptance:
      - {{ id: sitemap.roots-rendered,    check: "Pro spec_role=root existiert eine eigene Tabelle (tree-<id>) mit den Branches darunter." }}
      - {{ id: sitemap.links-resolve,     check: "Alle Sprung-Links (link-<spec-id>) zeigen auf existierende Dateien." }}
      - {{ id: sitemap.orphans-flagged,   check: "Falls Branches ohne Root existieren, werden sie unter 'orphans' aufgelistet." }}
      - {{ id: sitemap.tour-hint-visible, check: "Hinweis auf Tour-Mode (?tour=1) ist sichtbar." }}
    off_ramp_status: static
"""


def generate(
    repo_root: pathlib.Path, adr_local: str, repo_name: str | None = None
) -> dict[str, Any]:
    """Baut Sitemap + kd-tree für `repo_root`, schreibt alle Artefakte. Gibt den Tree zurück (für Tests/CI-Diff)."""
    kd_root = repo_root / "klickdummy"
    name = repo_name or repo_root.name
    specs = _load_specs(kd_root)
    tree = _build_tree(specs)
    _write_kd_tree_json(kd_root / "_shared", tree)
    out_dir = kd_root / "sitemap"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "index.html").write_text(_render_sitemap(tree, name), encoding="utf-8")
    (out_dir / "screens-spec.yaml").write_text(
        _render_sitemap_spec(
            name, adr_local, _stable_spec_date(out_dir / "screens-spec.yaml")
        ),
        encoding="utf-8",
    )
    return tree


def _stable_spec_date(existing_spec_path: pathlib.Path) -> str:
    """Determinismus (ADR-211 §Executable-Parity-Bridge): ein Rerun ohne bewusste
    Content-Änderung darf `spec_date` NICHT auf 'heute' weiterdrehen — das ließe die
    Spec-SHA256 in abhängigen generierten Dateien (z.B. `klickdummy-gen-e2e`-Output)
    bei jedem CI-Lauf driften, ohne dass sich real etwas geändert hat. Erhält das
    Datum aus der bestehenden Datei, falls vorhanden; nur bei Erstanlage 'heute'."""
    if existing_spec_path.exists():
        try:
            existing = yaml.safe_load(existing_spec_path.read_text(encoding="utf-8"))
        except yaml.YAMLError:
            existing = None
        if isinstance(existing, dict) and existing.get("spec_date"):
            return str(existing["spec_date"])
    return datetime.date.today().isoformat()


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print(
            "Usage: klickdummy-gen-sitemap <repo_root> <adr_local> [repo_name]\n"
            "  <repo_root>:  Consumer-Repo (mit klickdummy/*/screens-spec.yaml)\n"
            "  <adr_local>:  lokale Klickdummy-ADR-Referenz, z.B. risk-hub:ADR-046\n"
            "  [repo_name]:  Anzeigename (Default: repo_root-Verzeichnisname)"
        )
        return 2
    repo_root = pathlib.Path(argv[0])
    adr_local = argv[1]
    repo_name = argv[2] if len(argv) > 2 else None
    tree = generate(repo_root, adr_local, repo_name)
    print(
        "  wrote klickdummy/sitemap/index.html + klickdummy/sitemap/screens-spec.yaml"
    )
    print(
        f"  wrote klickdummy/_shared/kd-tree.json ({len(tree['nodes'])} Knoten, {len(tree['roots'])} Wurzeln)"
    )
    return 0


def main_cli() -> int:
    """Console-Script entry (pyproject.toml [project.scripts])."""
    return main(sys.argv[1:])


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

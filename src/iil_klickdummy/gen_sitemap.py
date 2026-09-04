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
import os
import pathlib
import re
import subprocess
import sys
from importlib.resources import files
from typing import Any

import yaml

from iil_klickdummy import gen_tokens


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
        if p.name.endswith(".screens-spec.yaml"):
            html_path = p.with_suffix("").with_suffix(".html")
        else:
            # Zwei Renderer-Konventionen im Umlauf: ältere Repos (z.B. risk-hub,
            # ADR-046) schreiben index.html, die neuere /klickdummy-Skill-Kette
            # (genesor-Render) schreibt shell.html (Issue #181) — beide prüfen,
            # index.html zuerst (Rückwärtskompatibilität).
            html_path = p.parent / "index.html"
            if not html_path.exists():
                html_path = p.parent / "shell.html"
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
        dom = s.get("domain")
        by_id[sid] = {
            "spec_id": sid,
            "title": s.get("title", sid),
            "role": s.get("spec_role", "branch"),
            # Fachliche Domäne (optional, freier String) — gleiche Zeichenkette
            # = gleiche Sitemap-Gruppe. Bewusst KEIN Fallback aus spec_id oder
            # Verzeichnisnamen: eine geratene Domäne gruppiert falsch und sieht
            # dabei absichtlich aus.
            "domain": dom.strip() if isinstance(dom, str) and dom.strip() else None,
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
    # Tour-Reihenfolge: depth-first ab den Roots.
    #
    # `spec_role` ist optional und defaultet oben auf "branch". Ein Repo, dessen
    # Specs es gar nicht deklarieren, hatte deshalb KEINE Wurzel — `order` blieb
    # leer und die Sitemap renderte sichtbar "0 Wurzeln · 0 Knoten gesamt",
    # obwohl kd-tree.json Knoten enthielt (Realfall 2026-07-27: 8 von 10
    # ausgerollten Repos, u.a. trading-hub mit 2 Knoten). Fallback deshalb:
    # ohne explizite Wurzel sind alle elternlosen Knoten Wurzeln.
    # `declared_roots` und `roots` sind BEWUSST getrennt: nach Aktivierung des
    # Fallbacks bedeutet `roots` nicht mehr "explizit deklariert", sondern
    # "womit gerendert wird". Der Waisen-Block rechnet gegen `declared_roots` —
    # sonst waeren beide Mengen identisch und die Warnung koennte nie feuern
    # (Retro-Befund #8).
    declared_roots = sorted([sid for sid, n in by_id.items() if n["role"] == "root"])
    # Entdopplung (Realfall risk-hub 2026-08-02: 18 deklarierte Wurzeln, 9 davon
    # gleichzeitig `kd_children` eines anderen KDs — jede erschien doppelt, als
    # eigene Wurzel-Tabelle UND als Kind-Zeile): ein deklarierter Root, der von
    # einem anderen KD als Kind referenziert wird, ist ein legitimer Teilbaum
    # (Master-Flow bindet eigenständige KDs ein) und wird NUR verschachtelt
    # gerendert. `demoted_roots` hält die Herabstufung im Tree transparent fest.
    demoted_roots = sorted(
        [sid for sid in declared_roots if by_id[sid]["parent"] is not None]
    )
    roots = [sid for sid in declared_roots if by_id[sid]["parent"] is None]
    if not declared_roots:
        roots = sorted([sid for sid, n in by_id.items() if n["parent"] is None])
    if not roots and by_id:
        # Zyklus ohne deklarierte Wurzel: jeder Knoten hat einen Parent, also
        # ist keiner elternlos — der Fallback oben greift ins Leere und die
        # Sitemap bliebe erneut leer (Retro-Befund #7). Deterministisch alle
        # Knoten als Einstieg nehmen; der Zyklen-Schutz unten verhindert
        # Doppelungen.
        roots = sorted(by_id)
    order: list[str] = []
    seen: set[str] = set()

    def _visit(sid: str) -> None:
        # Zyklen-Schutz: `kd_children` ist frei editierbarer Spec-Inhalt, zwei
        # Specs koennen sich gegenseitig als Kind fuehren — ohne `seen` liefe
        # der DFS in eine RecursionError.
        if sid in seen:
            return
        seen.add(sid)
        order.append(sid)
        for ch in by_id[sid]["children"]:
            _visit(ch)

    for r in roots:
        _visit(r)
    # Bewusst KEIN "Waisen-Rescue" hier: elternlose Branches neben echten Roots
    # sind ein Spec-Fehler und werden vom Renderer als Warnblock ausgewiesen
    # (data-testid="orphans"). Sie zu Roots zu befoerdern wuerde die Warnung
    # stilllegen statt den Fehler zu zeigen.
    #
    # Zusaetzlich: `kd_children`-Eintraege, die auf eine unbekannte spec_id
    # zeigen (Tippfehler, geloeschter KD), sind ein Spec-Fehler, den die
    # Waisen-Heuristik NICHT sieht — sie faellt nur auf, wenn zufaellig auch
    # eine Wurzel deklariert ist. Deshalb direkt erfassen und rendern.
    dangling = sorted(
        {
            f"{sid} → {child_id}"
            for sid, node in by_id.items()
            for child_id in node["kd_children"]
            if child_id not in by_id
        }
    )
    # prev/next setzen
    for i, sid in enumerate(order):
        by_id[sid]["prev"] = order[i - 1] if i > 0 else None
        by_id[sid]["next"] = order[i + 1] if i < len(order) - 1 else None
    return {
        "roots": roots,
        "declared_roots": declared_roots,
        "demoted_roots": demoted_roots,
        "dangling": dangling,
        "order": order,
        "nodes": by_id,
    }


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


def _write_kd_nav_js(shared_dir: pathlib.Path) -> None:
    """`kd-nav.js` mit ausliefern.

    Die generierte Sitemap bindet unbedingt `../_shared/kd-nav.js` ein
    (Hauptmenue-Button + Tour-Modus). Die Datei lag aber nur historisch in
    risk-hub und wurde vom Paket NIE mitgeliefert — in allen anderen Repos war
    das `<script src>` ein 404 und die Navigation lief nie (gemessen 2026-07-27:
    9 von 10 ausgerollten Repos). Der Generator schreibt jetzt die Quelle mit,
    die er referenziert."""
    shared_dir.mkdir(parents=True, exist_ok=True)
    src = files("iil_klickdummy") / "snippets" / "kd-nav.js"
    (shared_dir / "kd-nav.js").write_text(
        src.read_text(encoding="utf-8"), encoding="utf-8"
    )


# dev-hub#320 Welle 0: keine Tailwind-Utility-Klassen mehr — nur noch
# Status-Klassennamen, die im eingebetteten <style>-Block (_SITEMAP_CSS) auf
# `var(--kd-*)`-Tokens abgebildet sind.
STATUS_CLASS = {
    "static": "kd-status-static",
    "parity-staging": "kd-status-parity-staging",
    "parity-green": "kd-status-parity-green",
    "removed": "kd-status-removed",
}

# Layout-CSS der Sitemap — ausschließlich `var(--kd-*)`-Tokens (mit Fallback-
# Ketten für optionale Profil-Keys), keine Hex-Werte, keine Farbnamen, keine
# externe Utility-Bibliothek (dev-hub#320 Welle 0, Ersatz für Tailwind-CDN).
_SITEMAP_CSS = """
*, *::before, *::after { box-sizing: border-box; }
body {
  margin: 0;
  background: var(--kd-bg-light);
  color: var(--kd-text);
  font-family: var(--kd-font-primary, system-ui, sans-serif);
}
.kd-topbar {
  padding: 0.5rem 1.5rem;
  font-size: 0.75rem;
  color: var(--kd-text-muted, var(--kd-text));
  border-bottom: 2px solid var(--kd-primary);
}
.kd-topbar strong { color: var(--kd-text); }
.kd-page { max-width: 72rem; margin: 0 auto; padding: 1.5rem; }
.kd-title { margin: 0 0 0.5rem; font-size: 1.5rem; font-weight: 700; color: var(--kd-primary); }
.kd-subtitle { margin: 0 0 1.5rem; font-size: 0.875rem; color: var(--kd-text-muted, var(--kd-text)); }
.kd-kbd {
  font-family: var(--kd-font-mono, monospace);
  font-size: 0.75rem;
  padding: 0 0.25rem;
  border: 1px solid var(--kd-border);
  border-radius: 3px;
}
.kd-stats { margin-bottom: 1rem; font-size: 0.75rem; color: var(--kd-text-muted, var(--kd-text)); }
.kd-section-heading {
  margin: 1.5rem 0 0.75rem;
  padding-bottom: 0.25rem;
  font-size: 1.125rem;
  font-weight: 600;
  color: var(--kd-text);
  border-bottom: 1px solid var(--kd-border);
}
.kd-card { margin-bottom: 1rem; padding: 1rem; border: 1px solid var(--kd-border); border-radius: 8px; }
.kd-table { width: 100%; border-collapse: collapse; font-size: 0.875rem; }
.kd-table thead th {
  padding: 0.5rem 0.5rem 0.5rem 0;
  text-align: left;
  font-size: 0.75rem;
  color: var(--kd-text-muted, var(--kd-text));
  border-bottom: 1px solid var(--kd-border);
}
.kd-row { border-bottom: 1px solid var(--kd-line, var(--kd-border)); }
.kd-row-root { border-left: 3px solid var(--kd-primary); }
.kd-row td { padding: 0.5rem 0.5rem 0.5rem 0; vertical-align: top; }
.kd-spec-id { font-family: var(--kd-font-mono, monospace); font-size: 0.625rem; color: var(--kd-text-muted, var(--kd-text)); }
.kd-role { font-size: 0.6875rem; color: var(--kd-text-muted, var(--kd-text)); }
.kd-count { font-size: 0.6875rem; }
.kd-link { color: var(--kd-primary); text-decoration: none; }
.kd-link:hover { color: var(--kd-primary-dark, var(--kd-primary)); text-decoration: underline; }
.kd-badge {
  display: inline-block;
  padding: 0.0625rem 0.375rem;
  font-size: 0.625rem;
  border-radius: 3px;
  border: 1px solid var(--kd-border);
}
.kd-status-static { color: var(--kd-text-muted, var(--kd-text)); }
.kd-status-parity-staging { color: var(--kd-accent-2, var(--kd-primary)); border-color: var(--kd-accent-2, var(--kd-primary)); }
.kd-status-parity-green { color: var(--kd-accent-1, var(--kd-primary)); border-color: var(--kd-accent-1, var(--kd-primary)); font-weight: 600; }
.kd-status-removed { color: var(--kd-text-muted, var(--kd-text)); text-decoration: line-through; }
.kd-alert { margin-bottom: 1rem; padding: 1rem; border: 1px solid var(--kd-border); border-radius: 8px; }
.kd-alert h3 { margin: 0 0 0.5rem; font-size: 0.875rem; font-weight: 600; }
.kd-alert ul, .kd-alert li { list-style: none; margin: 0; padding: 0; }
.kd-alert li { display: flex; justify-content: space-between; padding: 0.25rem 0; border-bottom: 1px solid var(--kd-border); }
.kd-alert-warning h3 { color: var(--kd-accent-2, var(--kd-primary)); }
.kd-alert-danger h3 { color: var(--kd-primary); }
.kd-footer { margin-top: 1.5rem; font-size: 0.75rem; color: var(--kd-text-muted, var(--kd-text)); }
"""


def _render_sitemap(
    tree: dict[str, Any], repo_name: str, tokens_css: str | None = None
) -> str:
    nodes = tree["nodes"]
    sections: list[str] = []

    # Sitemap liegt unter klickdummy/sitemap/index.html — Pfade zu anderen KDs
    # (relativ zur klickdummy/-Wurzel) brauchen ein "../" voran.
    def rel(p: str) -> str:
        return "../" + p

    # Jeder Knoten erscheint in genau EINER Tabelle: `rendered` ist global über
    # alle Sektionen, damit (a) verschachtelte Teilbäume nicht zusätzlich als
    # eigene Sektion auftauchen und (b) der Zyklus-Fallback (roots = alle
    # Knoten) nicht jeden Teilbaum mehrfach rendert.
    rendered: set[str] = set()

    def _rows(sid: str, depth: int) -> list[str]:
        if sid in rendered:
            return []
        rendered.add(sid)
        n = nodes[sid]
        tid = sid.replace(":", "-").replace(".", "-")
        if depth == 0:
            title_html = f"<b>{n['title']}</b>"
            row_cls, role = ("kd-row kd-row-root", "root")
            link_cls = "kd-link kd-link-root"
        else:
            short = (
                n["title"].split(" — ", 1)[-1] if " — " in n["title"] else n["title"]
            )
            title_html = f"↳ {short}"
            # Herabgestufte Roots (deklariert root, aber als kd_children
            # referenziert) bleiben als "sub-root" erkennbar.
            role = "sub-root" if n["role"] == "root" else "branch"
            row_cls = "kd-row"
            link_cls = "kd-link"
        status_cls = STATUS_CLASS.get(n["off_ramp_status"], "")
        out = [
            f'<tr class="{row_cls}" data-testid="row-{tid}">'
            f'<td style="padding-left:{0.5 + depth}rem">{title_html}<div class="kd-spec-id">{n["spec_id"]}</div></td>'
            f'<td class="kd-role">{role}</td>'
            f'<td><span class="kd-badge {status_cls}">{n["off_ramp_status"]}</span></td>'
            f'<td class="kd-count">{n["screens_count"]}</td>'
            f'<td><a href="{rel(n["path"])}" data-testid="link-{sid}" class="{link_cls}">→ öffnen</a></td>'
            f"</tr>"
        ]
        for child_id in n["children"]:
            out.extend(_rows(child_id, depth + 1))
        return out

    def _section(root_id: str) -> str:
        rows = _rows(root_id, 0)
        if not rows:
            # Teilbaum bereits vollständig in einer früheren Sektion gerendert
            # (nur im Zyklus-Fallback erreichbar).
            return ""
        return (
            f'<div class="kd-card" data-testid="tree-{root_id.replace(":", "-").replace(".", "-")}">'
            f'<table class="kd-table"><thead><tr>'
            f"<th>Knoten</th><th>Rolle</th><th>Off-Ramp</th><th>Screens</th><th></th></tr></thead>"
            f"<tbody>{''.join(rows)}</tbody></table></div>"
        )

    # Domänen-Gruppierung: nur aktiv, wenn mindestens eine Wurzel `domain:`
    # deklariert — ohne Deklaration bleibt die flache Liste (kein Verhaltens-
    # sprung für die ausgerollten Repos). Wurzeln ohne Domäne sammeln sich
    # unter "Weitere Bereiche" am Ende.
    root_domains = {rid: nodes[rid]["domain"] for rid in tree["roots"]}
    if any(root_domains.values()):
        grouped: dict[str, list[str]] = {}
        for rid in tree["roots"]:
            grouped.setdefault(root_domains[rid] or "Weitere Bereiche", []).append(rid)
        ordered = sorted([d for d in grouped if d != "Weitere Bereiche"])
        if "Weitere Bereiche" in grouped:
            ordered.append("Weitere Bereiche")
        for domain in ordered:
            slug = "".join(c if c.isalnum() else "-" for c in domain.lower()).strip("-")
            sections.append(
                f'<h2 class="kd-section-heading" data-testid="domain-{slug}">{domain}</h2>'
            )
            sections.extend(_section(rid) for rid in grouped[domain])
    else:
        sections.extend(_section(rid) for rid in tree["roots"])

    # Orphans: elternlose Knoten neben DEKLARIERTEN Wurzeln. Der Abgleich laeuft
    # gegen `declared_roots`, nicht gegen `roots` — nach Aktivierung des
    # Fallbacks sind `roots` und "elternlos" per Konstruktion dieselbe Menge,
    # die Differenz waere immer leer und die Warnung koennte nie feuern
    # (Retro-Befund #8). Ohne deklarierte Wurzel gibt es begrifflich keinen
    # "Waisen" — dort greift stattdessen der Dangling-Block unten.
    declared = set(tree.get("declared_roots") or [])
    orphans = (
        [
            n
            for n in nodes.values()
            if n["spec_id"] not in declared and n["parent"] is None
        ]
        if declared
        else []
    )
    orphan_block = ""
    if orphans:
        rows = "".join(
            f'<li data-testid="orphan-{o["spec_id"].replace(":", "-")}">'
            f'<span>{o["title"]} <code class="kd-spec-id">{o["spec_id"]}</code></span>'
            f'<a href="{rel(o["path"])}" class="kd-link">→ öffnen</a></li>'
            for o in orphans
        )
        orphan_block = (
            '<div class="kd-alert kd-alert-warning" data-testid="orphans">'
            "<h3>⚠ Waisen-Knoten (kein Eltern-Root)</h3>"
            f"<ul>{rows}</ul></div>"
        )

    # Dangling: `kd_children` zeigt auf eine spec_id, die es nicht gibt
    # (Tippfehler, geloeschter KD). Unabhaengig davon, ob eine Wurzel
    # deklariert ist — genau die Luecke, die die Waisen-Heuristik offen liess.
    dangling_block = ""
    if tree.get("dangling"):
        rows = "".join(
            f'<li><code class="kd-spec-id">{d}</code></li>' for d in tree["dangling"]
        )
        dangling_block = (
            '<div class="kd-alert kd-alert-danger" data-testid="dangling">'
            "<h3>⚠ kd_children zeigt ins Leere</h3>"
            f"<ul>{rows}</ul></div>"
        )
    orphan_block = dangling_block + orphan_block

    n_domains = len({d for d in root_domains.values() if d})
    domain_stat = f"<b>{n_domains}</b> Domänen · " if n_domains else ""

    # dev-hub#320 Welle 0: kein CDN mehr (weder Tailwind noch lucide) — Layout
    # kommt aus dem eingebetteten `_SITEMAP_CSS`, Farben/Schriften ausschließlich
    # aus `var(--kd-*)`-Tokens. Der Tokens-Block (falls vorhanden) steht als
    # ERSTER <style>-Tag, damit er self-contained bleibt (keine relativen
    # Pfad-Annahmen) und die Layout-Regeln seine `--kd-*`-Variablen sehen.
    tokens_style = f"<style>\n{tokens_css}\n</style>" if tokens_css else ""

    return f"""<!DOCTYPE html>
<!--
  Klick-Dummy SITEMAP — automatisch generiert von `klickdummy-gen-sitemap`.
  Bei jeder KD-Änderung neu laufen lassen.
  Vertrag: klickdummy/sitemap/screens-spec.yaml
-->
<html lang="de"><head><meta charset="UTF-8"><meta name="klickdummy_class" content="mock">
<title>Klick-Dummy Sitemap — {repo_name}</title>
{tokens_style}
<style>{_SITEMAP_CSS}</style>
</head>
<body>
<div class="kd-topbar">
 <strong>Klick-Dummy Sitemap</strong>&nbsp;auto-generiert · Hauptmenü aller KD-Bäume im {repo_name}
</div>
<div class="kd-page">
 <h1 class="kd-title">Sitemap — {repo_name} Klickdummies</h1>
 <p class="kd-subtitle">Alle KD-Bäume mit Knoten-Hierarchie, Off-Ramp-Status (platform:ADR-211 §I3) und Spec-ID (§I4).
  Tour-Mode: hänge <code class="kd-kbd">?tour=1</code> an die URL eines Knotens, um den Walkthrough zu starten.</p>
 <div class="kd-stats" data-testid="stats">
  {domain_stat}<b>{len(tree["roots"])}</b> Wurzeln · <b>{len(tree["order"])}</b> Knoten gesamt · {sum(1 for n in nodes.values() if n["off_ramp_status"] == "parity-green")} parity-green
 </div>
 {"".join(sections)}
 {orphan_block}
 <p class="kd-footer">Generiert: <code class="kd-spec-id">klickdummy-gen-sitemap</code> (iil-klickdummy). Quelle: jede <code class="kd-spec-id">screens-spec.yaml</code> im klickdummy/-Baum (platform:ADR-211 I1).</p>
</div>
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
      - {{ id: sitemap.roots-rendered,    check: "Pro effektiver Wurzel (spec_role=root, nicht als kd_children referenziert) existiert eine eigene Tabelle (tree-<id>) mit dem Teilbaum darunter." }}
      - {{ id: sitemap.no-duplicate-nodes, check: "Kein Knoten erscheint in mehr als einer Tabelle — als kd_children referenzierte Roots werden im Elternbaum verschachtelt (sub-root), nicht doppelt gerendert." }}
      - {{ id: sitemap.domains-grouped,   check: "Deklariert mindestens eine Wurzel-Spec domain:, gruppiert die Sitemap die Wurzeln unter Domänen-Überschriften (domain-<slug>); ohne domain: bleibt die flache Liste." }}
      - {{ id: sitemap.links-resolve,     check: "Alle Sprung-Links (link-<spec-id>) zeigen auf existierende Dateien." }}
      - {{ id: sitemap.orphans-flagged,   check: "Falls Branches ohne Root existieren, werden sie unter 'orphans' aufgelistet." }}
      - {{ id: sitemap.tour-hint-visible, check: "Hinweis auf Tour-Mode (?tour=1) ist sichtbar." }}
    off_ramp_status: static
"""


class RepoNameResolveError(Exception):
    """Repo-Name laesst sich nicht sicher bestimmen (leer/ungueltig nach allen
    Fallbacks). CLI: Exit 2."""


# Positivkontrolle fuer den `spec_id`, den `generate()` fuer die Sitemap-Spec
# selbst schreibt (`<repo>:klickdummy-spec-sitemap`) — dieselbe Konvention wie
# `screens-spec.schema.json`s `spec_id`-Pattern, hier zusaetzlich VOR dem
# Schreiben geprueft statt erst nachtraeglich von einem Consumer (Portal-
# Safety-Gate `kd_loss`, oder einem I1-Lauf, der die Sitemap-Spec ueberhaupt
# scannt) entdeckt zu werden. `_resolve_repo_name()` blockt `:`/Leerzeichen
# im Repo-Namen bereits, dieser Check ist die zweite, unabhaengige Huerde
# (z.B. gegen einen Repo-Namen, der nicht mit `[a-z0-9]` beginnt).
_SITEMAP_SPEC_ID_RE = re.compile(r"^[a-z0-9][a-z0-9_-]*:[a-z][a-z0-9_-]*$")


def _repo_name_from_git_remote(repo_root: pathlib.Path) -> str | None:
    """`origin`-Remote-Basename ohne `.git`, oder `None` (kein Git-Repo, kein
    `origin`, `git` fehlt). Bewusst still — der Aufrufer entscheidet, ob ein
    fehlender Remote-Name ein Fehler ist."""
    try:
        result = subprocess.run(
            ["git", "-C", str(repo_root), "remote", "get-url", "origin"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if result.returncode != 0:
        return None
    url = result.stdout.strip().rstrip("/")
    if not url:
        return None
    if url.endswith(".git"):
        url = url[:-4]
    name = url.rsplit("/", 1)[-1]
    return name or None


def _resolve_repo_name(repo_root: pathlib.Path, repo_name: str | None) -> str:
    """Robuste Bestimmung des Sitemap-Anzeigenamens (Teil von `spec_id`).

    Reihenfolge: explizites `repo_name`-Argument > `git remote get-url
    origin` (Basename ohne `.git`) > `repo_root.resolve().name`.

    Grund fuer die Reihenfolge: `repo_root.name` (ohne `.resolve()`) ist bei
    `repo_root == Path(".")` ein leerer String — Portal-Safety-Gate `kd_loss`,
    Realfall dms-hub 2026-09-04, `spec_id: :klickdummy-spec-sitemap`. Auch
    `repo_root.resolve().name` allein ist in einem Session-Worktree falsch
    (liefert den Worktree-Ordnernamen, nicht den Repo-Namen) — deshalb zuerst
    die Remote-URL, die in einem Worktree auf dasselbe Origin-Repo zeigt.

    Ergebnis leer oder enthaelt `:`/Leerzeichen (unbrauchbar als `spec_id`-
    Praefix) -> `RepoNameResolveError` statt eine kaputte Spec zu schreiben.
    """
    name: str | None
    if repo_name is not None and repo_name.strip():
        name = repo_name.strip()
    else:
        name = _repo_name_from_git_remote(repo_root)
        if not name:
            name = repo_root.resolve().name
    if not name or ":" in name or any(ch.isspace() for ch in name):
        raise RepoNameResolveError(
            f"Repo-Name leer oder ungueltig ({name!r}) - [repo_name] als "
            "drittes CLI-Argument angeben oder KLICKDUMMY_REPO_NAME setzen "
            "(vor `include gates.mk` im Adopter-Makefile)."
        )
    return name


def generate(
    repo_root: pathlib.Path,
    adr_local: str,
    repo_name: str | None = None,
    tokens_css: str | None = None,
) -> dict[str, Any]:
    """Baut Sitemap + kd-tree für `repo_root`, schreibt alle Artefakte. Gibt den Tree zurück (für Tests/CI-Diff).

    `tokens_css`: bereits aufgelöster Inhalt einer `tokens.css` (dev-hub#320
    Welle 0) — wird als erster `<style>`-Block in die Sitemap eingebettet.
    Die Auflösung selbst (`--tokens-css` / `--profile` / IIL-Fallback) liegt
    bei der CLI (`main()`), nicht hier — `generate()` bleibt so direkt aus
    Tests/anderen Aufrufern nutzbar, auch ohne design-hub verfügbar zu haben.
    """
    kd_root = repo_root / "klickdummy"
    name = _resolve_repo_name(repo_root, repo_name)
    sitemap_spec_id = f"{name}:klickdummy-spec-sitemap"
    if not _SITEMAP_SPEC_ID_RE.match(sitemap_spec_id):
        raise RepoNameResolveError(
            f"Repo-Name {name!r} ergibt eine ungueltige spec_id "
            f"({sitemap_spec_id!r}, erwartet <repo>:<slug>) - [repo_name] als "
            "drittes CLI-Argument angeben oder KLICKDUMMY_REPO_NAME setzen."
        )
    specs = _load_specs(kd_root)
    tree = _build_tree(specs)
    _write_kd_tree_json(kd_root / "_shared", tree)
    _write_kd_nav_js(kd_root / "_shared")
    out_dir = kd_root / "sitemap"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "index.html").write_text(
        _render_sitemap(tree, name, tokens_css), encoding="utf-8"
    )
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


class TokensResolveError(Exception):
    """Tokens-CSS lässt sich nicht auflösen (--tokens-css/--profile/Fallback). CLI: Exit 2."""


def _default_design_hub_dir() -> pathlib.Path:
    """`$GITHUB_DIR/design-hub`, sonst `~/github/design-hub` (dev-hub#320 Welle 0)."""
    github_dir = os.environ.get("GITHUB_DIR")
    base = pathlib.Path(github_dir) if github_dir else pathlib.Path.home() / "github"
    return base / "design-hub"


def _resolve_tokens_css(
    tokens_css_path: pathlib.Path | None,
    profile_path: pathlib.Path | None,
    design_hub_dir: pathlib.Path | None,
) -> str:
    """Löst den Inhalt der einzubettenden `tokens.css` auf — Priorität:
    `--tokens-css` (Datei roh einbetten) > `--profile` (design-hub-Profil ->
    `gen_tokens.generate()`) > IIL-Fallback (`<design-hub>/profiles/iil-extern.yaml`).
    Ohne alle drei Optionen: `--design-hub` (oder dessen Default) muss ein
    lesbares `profiles/iil-extern.yaml` enthalten, sonst `TokensResolveError`
    (CLI: Exit 2). Keine Kopie des IIL-Profils im Paket — design-hub bleibt
    einzige Quelle (Owner-Entscheid dev-hub#320 Welle 0)."""
    if tokens_css_path is not None:
        try:
            return tokens_css_path.read_text(encoding="utf-8")
        except OSError as e:
            raise TokensResolveError(
                f"--tokens-css nicht lesbar: {tokens_css_path} ({e})"
            ) from e

    if profile_path is not None:
        resolved_profile_path = profile_path
    else:
        design_hub = design_hub_dir or _default_design_hub_dir()
        resolved_profile_path = design_hub / "profiles" / "iil-extern.yaml"
        if not resolved_profile_path.is_file():
            raise TokensResolveError(
                f"IIL-Fallback braucht design-hub unter {design_hub}; "
                "--tokens-css oder --profile angeben"
            )

    try:
        profile = gen_tokens._load_profile(resolved_profile_path)
        return gen_tokens.generate(
            profile, generator_version=gen_tokens._generator_version()
        )
    except (OSError, yaml.YAMLError, gen_tokens.TokenGenError) as e:
        raise TokensResolveError(
            f"Profil {resolved_profile_path} nicht verwendbar: {e}"
        ) from e


def main(argv: list[str]) -> int:
    positional: list[str] = []
    tokens_css_path: pathlib.Path | None = None
    profile_path: pathlib.Path | None = None
    design_hub_dir: pathlib.Path | None = None

    i = 0
    while i < len(argv):
        arg = argv[i]
        if arg in ("--tokens-css", "--profile", "--design-hub"):
            i += 1
            if i >= len(argv):
                print(f"FEHLER: {arg} braucht einen Pfad", file=sys.stderr)
                return 2
            value = pathlib.Path(argv[i])
            if arg == "--tokens-css":
                tokens_css_path = value
            elif arg == "--profile":
                profile_path = value
            else:
                design_hub_dir = value
        else:
            positional.append(arg)
        i += 1

    if len(positional) < 2:
        print(
            "Usage: klickdummy-gen-sitemap <repo_root> <adr_local> [repo_name]\n"
            "  <repo_root>:  Consumer-Repo (mit klickdummy/*/screens-spec.yaml)\n"
            "  <adr_local>:  lokale Klickdummy-ADR-Referenz, z.B. risk-hub:ADR-046\n"
            "  [repo_name]:  Anzeigename (Default: git remote origin, sonst "
            "repo_root-Verzeichnisname; leer/ungueltig -> Exit 2)\n"
            "  --tokens-css <pfad>:  tokens.css roh als ersten <style>-Block einbetten\n"
            "  --profile <yaml>:     design-hub-Profil -> Tokens zur Laufzeit erzeugen\n"
            "  --design-hub <dir>:   design-hub-Checkout fuer den IIL-Fallback "
            "(Default: $GITHUB_DIR/design-hub, sonst ~/github/design-hub)\n"
            "  Ohne --tokens-css/--profile: IIL-Fallback aus "
            "<design-hub>/profiles/iil-extern.yaml (sonst Exit 2)."
        )
        return 2
    repo_root = pathlib.Path(positional[0])
    adr_local = positional[1]
    repo_name = positional[2] if len(positional) > 2 else None

    try:
        tokens_css = _resolve_tokens_css(tokens_css_path, profile_path, design_hub_dir)
    except TokensResolveError as e:
        print(f"FEHLER: {e}", file=sys.stderr)
        return 2

    try:
        tree = generate(repo_root, adr_local, repo_name, tokens_css=tokens_css)
    except RepoNameResolveError as e:
        print(f"FEHLER: {e}", file=sys.stderr)
        return 2
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

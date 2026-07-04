#!/usr/bin/env python3
"""klickdummy-from-django — Brownfield-Reverse-Onboarding (platform:ADR-211).

Leitet aus einer **existierenden Django-App** ein `screens-spec.yaml`-**Skelett**
ab: URLConf → Screens, Models → Entity-Katalog/datafields, app_name → spec_id.
Statisches Parsing (`ast` + Regex) — **keine** Django-Runtime/DB nötig, läuft
sicher gegen jeden Source-Tree.

Das Ergebnis ist ein **Startpunkt für menschliche Kuratierung**, kein fertiger
Spec: Purpose/Personas/konkrete Assertions sind TODO. Der nächste Schritt ist
`klickdummy-gen-e2e` gegen die echte App (Parity-Bridge) → iterieren bis
parity-grün = verifizierte Spec-Erfassung des Ist-Zustands.

Aufruf:
    klickdummy-from-django --repo ~/github/writing-hub --app outlines
    klickdummy-from-django --repo . --app outlines --out klickdummy/outlines/screens-spec.yaml

class = `spec-demo` (realer Code-Pfad existiert; demo-state via `?demo=` env-gegatet).
"""

from __future__ import annotations

import argparse
import ast
import pathlib
import re
import sys

# POST-/Aktions-Endpoints (kein eigener Screen → als fokus/next_screens kuratieren).
_ACTION_VERBS = {
    "delete",
    "update",
    "create",
    "add",
    "set_active",
    "save_version",
    "discard",
    "commit",
    "status",
    "score",
    "generate",
    "expand",
    "refine",
    "enrich",
    "filter",
    "import",
    "start",
    "remove",
    "toggle",
    "publish",
    "archive",
}
# Django-Field → semantischer Typ (für datafields).
_FIELD_TYPE = {
    "CharField": "string",
    "TextField": "text",
    "SlugField": "slug",
    "IntegerField": "int",
    "PositiveIntegerField": "int",
    "FloatField": "float",
    "DecimalField": "decimal",
    "BooleanField": "bool",
    "DateTimeField": "datetime",
    "DateField": "date",
    "UUIDField": "uuid",
    "EmailField": "email",
    "JSONField": "json",
    "ForeignKey": "ref",
    "OneToOneField": "ref",
    "ManyToManyField": "ref[]",
    "FileField": "file",
    "ImageField": "image",
    "URLField": "url",
}

_PATH_RE = re.compile(r"""path\(\s*['"]([^'"]*)['"]\s*,\s*([A-Za-z0-9_.]+)""")
_NAME_RE = re.compile(r"""name\s*=\s*['"]([a-z0-9_-]+)['"]""")


def _humanize(name: str) -> str:
    return name.replace("_", " ").replace("-", " ").strip().title() or name


def _is_action(name: str, view: str) -> bool:
    if view.endswith("DeleteView"):
        return True
    toks = set(re.split(r"[_-]", name.lower()))
    return bool(toks & _ACTION_VERBS)


def _url_modules(app_dir: pathlib.Path) -> list[pathlib.Path]:
    """Alle URL-Module einer App — nicht nur `urls.py` (Issue #82).

    Django-Apps splitten Routen oft über mehrere Module (`html_urls.py`,
    `api_urls.py`) und binden sie per `include()` in `urls.py`. `urls.py` allein
    zu parsen verfehlt die dort nicht direkt deklarierten Screens. Wir sammeln
    daher jedes `*urls*.py` der App-Ebene plus die Dateien eines `urls/`-Package.
    `urls.py` steht zuerst (liefert bevorzugt `app_name`)."""
    mods: list[pathlib.Path] = []
    primary = app_dir / "urls.py"
    if primary.exists():
        mods.append(primary)
    for p in sorted(app_dir.glob("*urls*.py")):
        if p != primary and p.is_file():
            mods.append(p)
    pkg = app_dir / "urls"
    if pkg.is_dir():
        for p in sorted(pkg.glob("*.py")):
            if p.name != "__init__.py" and p.is_file():
                mods.append(p)
    return mods


def _parse_url_module(text: str) -> list[dict]:
    """Route-Einträge aus dem Text EINES URL-Moduls (zeilenweise robust)."""
    entries: list[dict] = []
    # path(...) kann mehrzeilig sein → pro logischer path(-Stelle den Folgetext bis ')' scannen
    for pm in re.finditer(r"path\(", text):
        chunk = text[pm.start() : pm.start() + 400]
        route_m = _PATH_RE.search(chunk)
        name_m = _NAME_RE.search(chunk)
        view_m = re.search(r"views\.([A-Za-z0-9_]+)", chunk)
        if not (route_m and name_m):
            continue
        route = route_m.group(1)
        view = view_m.group(1) if view_m else "?"
        name = name_m.group(1)
        entries.append(
            {
                "name": name,
                "route": "/" + route if not route.startswith("/") else route,
                "view": view,
                "action": _is_action(name, view),
            }
        )
    return entries


def parse_urls(app_dir: pathlib.Path) -> tuple[str, list[dict]]:
    """(app_name, [{name, route, view, action}]) aus ALLEN URL-Modulen der App.

    Fix #82: früher wurde nur `urls.py` gelesen — Screens in separaten Modulen
    (`html_urls.py`) fehlten im Skelett. Jetzt über `_url_modules` gesammelt.
    """
    mods = _url_modules(app_dir)
    if not mods:
        return (app_dir.name, [])
    app_name = app_dir.name
    entries: list[dict] = []
    for mod in mods:
        text = mod.read_text(encoding="utf-8", errors="ignore")
        m = re.search(r"""app_name\s*=\s*['"]([^'"]+)['"]""", text)
        if m and app_name == app_dir.name:  # erste app_name-Deklaration gewinnt
            app_name = m.group(1)
        entries.extend(_parse_url_module(text))
    # Dedup nach name (erste Definition gewinnt — urls.py vor *_urls.py)
    seen, uniq = set(), []
    for e in entries:
        if e["name"] not in seen:
            seen.add(e["name"])
            uniq.append(e)
    return (app_name, uniq)


def parse_models(app_dir: pathlib.Path) -> list[dict]:
    """[{name, fields:[(fname, type)]}] aus models.py via ast."""
    models_py = app_dir / "models.py"
    if not models_py.exists():
        return []
    try:
        tree = ast.parse(models_py.read_text(encoding="utf-8", errors="ignore"))
    except SyntaxError:
        return []
    out: list[dict] = []
    for node in tree.body:
        if not isinstance(node, ast.ClassDef):
            continue
        if not any(
            (isinstance(b, ast.Attribute) and b.attr == "Model")
            or (isinstance(b, ast.Name) and b.id == "Model")
            for b in node.bases
        ):
            continue
        fields: list[tuple[str, str]] = []
        for stmt in node.body:
            if isinstance(stmt, ast.Assign) and isinstance(stmt.value, ast.Call):
                fn = stmt.value.func
                field_cls = (
                    fn.attr
                    if isinstance(fn, ast.Attribute)
                    else (fn.id if isinstance(fn, ast.Name) else "")
                )
                if (
                    field_cls in _FIELD_TYPE
                    and stmt.targets
                    and isinstance(stmt.targets[0], ast.Name)
                ):
                    fields.append((stmt.targets[0].id, _FIELD_TYPE[field_cls]))
        out.append({"name": node.name, "fields": fields})
    return out


def build_spec(
    app_name: str, entries: list[dict], models: list[dict], repo: str
) -> str:
    """Baut das screens-spec.yaml-Skelett (string mit Kuratier-Kommentaren)."""
    pages = [e for e in entries if not e["action"]]
    actions = [e for e in entries if e["action"]]
    ent_cat = (
        ", ".join(
            f"{m['name']}({', '.join(f'{n}:{t}' for n, t in m['fields'][:6])}{'…' if len(m['fields']) > 6 else ''})"
            for m in models
        )
        or "—"
    )
    lines: list[str] = []
    lines.append(
        "# Klickdummy-Spec-SKELETT — aus Django abgeleitet (klickdummy-from-django)."
    )
    lines.append("# Startpunkt für Kuratierung: Purpose/Personas/Assertions sind TODO.")
    lines.append(
        "# Nächster Schritt: klickdummy-gen-e2e gegen die echte App → parity-grün."
    )
    lines.append(f"spec_id: {repo}:klickdummy-spec-{app_name}")
    lines.append('spec_version: "0.1"')
    lines.append('spec_schema_version: "1.1"')
    lines.append('spec_date: "TODO"')
    lines.append(f"title: {app_name} — Klickdummy (Brownfield, aus Django abgeleitet)")
    lines.append("adr:")
    lines.append(f"  local: {repo}:ADR-NNN          # TODO: Repo-ADR anlegen")
    lines.append("  conforms_to: platform:ADR-211")
    lines.append("  sister_of: []")
    lines.append(
        "class: spec-demo               # realer Code-Pfad existiert (Brownfield)"
    )
    lines.append("class_evidence:")
    lines.append("  real_codepath: true")
    lines.append('  demo_gating: "?demo=<state> — TODO env-gaten"')
    lines.append("grounding:")
    lines.append('  konzept: "TODO"')
    lines.append('  pilot: "TODO"')
    lines.append("off_ramp:")
    lines.append("  policy: platform:ADR-211 Brownfield-Spec-Capture")
    lines.append("  unit: per-screen")
    lines.append(
        '  rule: "Spec ist SoR; Änderungen spec-first, via gen_e2e-Parity gegen die App verifiziert"'
    )
    lines.append("  doppelquell_grenze: prod-release")
    lines.append("  parity_runner: make klickdummy-i3")
    lines.append(
        "personas:                       # TODO: aus Django-Groups/Auth ableiten"
    )
    lines.append("  nutzer:")
    lines.append('    label: "TODO"')
    lines.append('    rolle: "TODO"')
    lines.append("    sieht: []")
    lines.append(
        "# Entity-Katalog (aus models.py) — pro Screen als konsumiert_entities/datafields kuratieren:"
    )
    lines.append(f"#   {ent_cat}")
    if actions:
        lines.append(
            "# Aktionen (POST-Endpoints — als fokus/next_screens an Screens kuratieren):"
        )
        lines.append("#   " + ", ".join(f"{a['name']} ({a['view']})" for a in actions))
    lines.append("screens:")
    if not pages:
        lines.append(
            "  []   # keine Page-Screens erkannt — urls.py prüfen / manuell ergänzen"
        )
    for e in pages:
        lines.append(f"  - id: {e['name']}")
        lines.append(f"    title: {_humanize(e['name'])}")
        lines.append(f"    route: {e['route']}")
        lines.append("    personas: [nutzer]")
        lines.append(f'    purpose: "TODO: Zweck dieses Screens (View: {e["view"]})"')
        lines.append("    konsumiert_entities: []   # TODO aus Entity-Katalog")
        lines.append("    parity_acceptance:")
        lines.append(f"      - id: {e['name']}.renders")
        lines.append(
            f'        check: "Screen {e["route"]} rendert erwartbar (TODO: konkrete Assertion)"'
        )
        lines.append(
            '        # assert: {action: visible, selector: "[data-testid=...]"}   # → gen_e2e-fähig'
        )
        lines.append("    off_ramp_status: static")
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="Django-App → screens-spec.yaml-Skelett (platform:ADR-211)"
    )
    ap.add_argument("--repo", default=".", help="Repo-Root (default: .)")
    ap.add_argument(
        "--app", required=True, help="Django-App (Verzeichnis unter apps/ oder Pfad)"
    )
    ap.add_argument("--out", help="Ziel-Datei (default: stdout)")
    args = ap.parse_args(argv)

    repo_root = pathlib.Path(args.repo).expanduser().resolve()
    repo_name = repo_root.name
    # App-Verzeichnis finden: apps/<app> oder <app> direkt
    candidates = [
        repo_root / "apps" / args.app,
        repo_root / args.app,
        pathlib.Path(args.app),
    ]
    # #82: eine App kann Routen ausschließlich in `*_urls.py` führen (kein urls.py).
    app_dir = next(
        (c for c in candidates if (c / "models.py").exists() or _url_modules(c)),
        None,
    )
    if not app_dir:
        print(f"✗ App nicht gefunden (urls.py/models.py): {args.app}", file=sys.stderr)
        return 2

    app_name, entries = parse_urls(app_dir)
    models = parse_models(app_dir)
    spec = build_spec(app_name, entries, models, repo_name)

    pages = sum(1 for e in entries if not e["action"])
    acts = sum(1 for e in entries if e["action"])
    print(
        f"→ {app_name}: {pages} Screen(s), {acts} Aktion(en), {len(models)} Model(s)",
        file=sys.stderr,
    )
    if args.out:
        outp = pathlib.Path(args.out)
        outp.parent.mkdir(parents=True, exist_ok=True)
        outp.write_text(spec, encoding="utf-8")
        print(f"✓ Skelett → {outp}", file=sys.stderr)
    else:
        print(spec)
    return 0


def main_cli() -> None:
    raise SystemExit(main())


if __name__ == "__main__":
    main_cli()

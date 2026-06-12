#!/usr/bin/env python3
"""Klickdummy-Lineage-Viewer + IIL-Genesor (Stufe 1a: Cross-Repo-Übersicht).

Zwei Modi:
  default:    Single-Repo-Lineage (meiki-hub) — Mermaid-Graph + Feedback-Widget
              → lineage.mmd + index.html        (Pfad-c-Output 2026-05-23)
  --genesor:  Cross-Repo-Übersicht (IIL-Genesor Stufe 1a, 2026-05-24)
              → genesor.html                    (Tabelle aller KDs in ~/github)

Selbst ein Klickdummy nach meiki:ADR-035 (Meta-KD, class: mock).

Konventionen (zwei Spec-Pfade je Repo werden gescannt):
  ~/github/<repo>/klickdummy/<name>/screens-spec.yaml
  ~/github/<repo>/docs/01-architektur/mockups/<name>-klickdummy/screens-spec.yaml

Aufruf:
  klickdummy-genesor                               # Single-Repo (meiki)
  klickdummy-genesor --genesor                     # + Cross-Repo Übersicht
  python3 -m iil_klickdummy.lineage --genesor      # äquivalent (Modul-Aufruf)

Seams (Default-Verhalten byte-identisch zu früher):
  --repos-root  (Default ~/github)        gescanntes Repo-Wurzelverzeichnis
  --out         (Default <root>/genesor)  Output-Verzeichnis
  --base-url    (Default "/")             URL-Präfix für Links + Skin-Pfade

Relocation 2026-05-28: aus meiki-hub/scripts/ in das Plattform-Paket
iil-klickdummy verlagert (cross-cutting Tooling, vgl. meiki:ADR-035).
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path



# --- Genesor-Sub-Package Imports (KONZ-003 Empf-1, PR2) ---
# config: GenesorConfig, _cfg-Singleton, set_cfg, Konstanten
# Backward-compat-Aliases (REPOS_ROOT etc.) re-exportiert für
# `from iil_klickdummy.lineage import X` ohne NameError.
from .genesor.config import (  # noqa: E402,F401
    GenesorConfig,
    _cfg,
    get_cfg,
    set_cfg,
    REPOS_ROOT,
    GENESOR_OUT,
    BASE_URL,
    SKIN_BASE,
    VENDORED_REPOS,
    _base_prefix,
    _skin_url,
    MOCKUP_PRIO_NAMES,
    SKIN_LIBRARY_REL,
    _DOMAIN_STYLES,
    _BUERGER_POOL,
    _AKTEN_PROFIL_POOL,
    _FRONTMATTER_RE,
)
# introspect_django: Django-Introspection-Helfer
from .genesor.introspect_django import (  # noqa: E402,F401
    _inspect_django_models,
    _detect_tenant_pattern,
    _detect_auth_user_model,
    _inspect_dev_run,
    _inspect_infra_context,
)
# export: UC-JSON-Export
from .genesor.export import build_uc_export_json  # noqa: E402,F401
# --- PR4-Split (KONZ-003 Empf-1): Renderer-Module ---
from .genesor.render_common import (  # noqa: E402,F401
    FEEDBACK_WIDGET_JS,
    SKIN_SWITCHER_JS,
    STORY_BANNER_JS,
    _OFFRAMP_CHIP_CLASS,
    _gh_issue_url,
    _screen_coverage,
    _screen_use_cases,
    build_skin_switcher_html,
    build_trace_strip,
    skin_library,
)
from .genesor.render_fallback import (  # noqa: E402,F401
    RENDER_FALLBACK_TEMPLATE,
    generate_render_fallback,
)
from .genesor.render_lineage import (  # noqa: E402,F401
    HTML_TEMPLATE,
    build_html,
    build_screen_lineage_html,
    generate_per_repo_lineages,
)
from .genesor.render_genesor import (  # noqa: E402,F401
    build_genesor_html,
)
from .genesor.render_uc import (  # noqa: E402,F401
    build_coverage_html,
    build_impl_brief,
    build_impl_brief_html,
    build_repo_uc_index_html,
)
# --- PR3-Split (KONZ-003 Empf-1): scan/synth/mermaid/validate/publish/ucs ---
from .genesor.scan import (  # noqa: E402,F401
    CONTRACTS_DIR,
    MOCKUPS_DIR,
    ROOT,
    _git_repo_meta,
    _load_iil_apps_index,
    _normalize_spec_aliases,
    _repo_meta_cached,
    adr_local,
    detect_org,
    find_all_repos_specs,
    find_contracts,
    find_contracts_in_dir,
    find_mockup_html,
    find_specs,
    find_use_cases,
    kunde_from,
    read_doc_profile,
    read_fv_inventur,
    read_kd_adr_meta,
    url_for_path,
)
from .genesor.synth import (  # noqa: E402,F401
    _AKTEN_ID_FIELDS,
    _AKTEN_LINK_FIELDS,
    _entities_lookup,
    _entity_def_from_spec,
    _entity_field_names,
    _persona_def_from_spec,
    _row_akte,
    _row_buerger,
    _synth_entity_table,
    _synth_value,
)
from .genesor.mermaid import (  # noqa: E402,F401
    _safe_mermaid_label,
    emit_mermaid,
    emit_screen_lineage,
    group_providers_by_contract,
    node_id,
    node_label,
)
from .genesor.validate import (  # noqa: E402,F401
    CROSS_REPO_REF_RE,
    _ACCEPTANCE_AXES,
    _ACCEPTANCE_STALE_DAYS,
    _compute_drift_status,
    _extract_screen_routes,
    build_kd_registry,
    compute_acceptance_status,
    compute_sunset_badge,
    merge_acceptance,
    validate_kd,
)
from .genesor.publish import (  # noqa: E402,F401
    _auto_publish_per_repo,
    _git_publish_changes,
    _github_delete_url,
    _github_edit_url,
    _repo_of_path,
)
from .genesor.ucs import (  # noqa: E402,F401
    _REPO_UC_PREFIX,
    _SCREEN_REF_RE,
    _UC_ID_PATTERN,
    _VALID_UC_STATUS,
    _kd_shortcode,
    _parse_uc_frontmatter,
    _prefix_to_repo,
    _repo_shortcode,
    _resolve_screen_ref,
    _uc_kd_targets,
    build_uc_coverage,
    find_all_repos_ucs,
    gen_uc_skeleton,
    generate_uc_skeletons,
    validate_ucs,
)


OUT_DIR = ROOT / "docs" / "01-architektur" / "lineage"           # Single-Repo-Lineage (Rückwärtskompat)


# _base_prefix, _skin_url, MOCKUP_PRIO_NAMES imported from .genesor.config above.

# ---- Mockup-HTML-Discovery (Stufe 1b: "Klickdummy klickbar") ---------------


# ---- Skin-Library (zentral in iil-klickdummy, via HTTP-Server-Root erreichbar)
# User-Feedback 2026-05-25: Style-Switcher als Demo-Werkzeug auch auf Root-Ebene
# (Genesor-Übersicht), mit localStorage-Persistenz cross-Render.

# SKIN_LIBRARY_REL imported from .genesor.config above.


# ---- ADR-Frontmatter-Reader (Rev-15-Vorgriff: realizes_use_cases + replaces_system_ref)

# _FRONTMATTER_RE imported from .genesor.config above.


# ---- FV-Inventur-Reader -----------------------------------------------------


# ---- Use-Case-Discovery -----------------------------------------------------


# ---- Render-Fallback (Spec → klickbare HTML wenn shell.html fehlt) ---------

# ---- Domain-Style + Synthetic-Data-Helpers (Render v2) ----------------------

# _DOMAIN_STYLES, _BUERGER_POOL, _AKTEN_PROFIL_POOL imported from .genesor.config above.


# ---- Spec-Layer (X-Ray) Trace-Strip ----------------------------------------
# ADR-211-konform: jeder Chip ist 1:1 aus der Spec abgeleitet. Fehlt das Feld,
# wird ein "nicht deklariert"-Chip mit dem exakten Spec-Feld zum Ergänzen
# gerendert (Evidenz-Disziplin: nie erfinden — vgl. akte_next-Muster). Sichtbar
# nur bei body.spec-view (globaler Toggle / Taste "s"), damit die Echt-App-
# Illusion für den Stakeholder-Walkthrough erhalten bleibt.


# ---- Render v2 Template ----------------------------------------------------


# ---- Org-Detection (Heuristik; später aus platform/registry) --------------


# ---- Spec-Discovery + Parsing ----------------------------------------------


# ---- Mermaid-Generierung ----------------------------------------------------


# ---- HTML-Wrapper mit Feedback-Widget --------------------------------------


# ---- Cross-Repo-Walker (IIL-Genesor Stufe 1a + 1b) -------------------------


# ---- Drift-Validierung (F3) ------------------------------------------------


# ---- Per-Repo-Lineage-Generator (Stufe 1b) ---------------------------------


# _inspect_django_models, _detect_tenant_pattern, _detect_auth_user_model,
# _inspect_dev_run, _inspect_infra_context — imported from .genesor.introspect_django above.


# build_uc_export_json — imported from .genesor.export above.


# ---- UC-Skelett-Generator (Workshop-Feedback 2026-05-26 #2) ---------------


# ---- main -------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(description="Klickdummy-Lineage-Viewer + IIL-Genesor")
    parser.add_argument("--genesor", action="store_true",
                        help="Cross-Repo-Übersicht (Stufe 1a/b) zusätzlich emittieren")
    parser.add_argument("--no-single", action="store_true",
                        help="Single-Repo-Output (meiki-hub) überspringen")
    parser.add_argument("--gen-uc-skeletons", action="store_true",
                        help="UC-Skelette aus Klickdummy-Specs erzeugen (ADR-211 Rev 16)")
    parser.add_argument("--prune-auto-ucs", action="store_true",
                        help="UC-Files mit `auto_generated: true` Frontmatter löschen (idempotent)")
    parser.add_argument("--validate-ucs", action="store_true",
                        help="UC-Validator (Layer A) standalone laufen — exit 1 bei errors")
    parser.add_argument("--strict", action="store_true",
                        help="--validate-ucs: warnings als FAIL behandeln (CI-Modus)")
    parser.add_argument("--gen-impl-brief", metavar="REPO:KD:SCREEN",
                        help="Implementation-Brief für 1 Screen erzeugen (Variante-3-Pilot)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Nur anzeigen was geschrieben/gelöscht würde, ohne Files anzufassen")
    parser.add_argument("--auto-publish", action="store_true",
                        help="Nach Gen/Prune: pro Repo Commit + Push der geänderten _auto/-Files")
    parser.add_argument("--allow-main-push", action="store_true",
                        help="Erlaube --auto-publish auch auf main/master (Default: skip mit Warning)")
    parser.add_argument("--repos-root", default=str(Path.home() / "github"),
                        help="Wurzelverzeichnis der gescannten Repos (Default: ~/github)")
    parser.add_argument("--out", default=None,
                        help="Genesor-Output-Verzeichnis (Default: <repos-root>/genesor)")
    parser.add_argument("--base-url", default="/",
                        help="URL-Präfix für generierte Links + Skin-Pfade (Default: '/')")
    parser.add_argument("--skin-base", default="",
                        help="Basis-URL für Skin-CSS (z. B. '/genesor/skins'). Leer (Default) → "
                             "Skins unter '/iil-klickdummy/.../skins/<name>.css' (byte-identisch zu früher); "
                             "gesetzt → '<skin-base>/<name>.css' für einen self-contained Build.")
    parser.add_argument("--vendored-repos", default="",
                        help="Komma-separierte Repo-Namen, deren echte Mockup-HTMLs einvendoriert "
                             "unter '/kd/<repo>/...' ausgeliefert werden (z. B. 'ausschreibungs-hub'). "
                             "Leer (Default) → keine Umschreibung (byte-identisch zu früher).")
    args = parser.parse_args()

    # Argparse → GenesorConfig (KONZ-003 Empf-1: keine bare-Global-Mutation mehr).
    # Defaults reproduzieren das bisherige Verhalten byte-identisch.
    global _cfg
    _repos_root = Path(args.repos_root).expanduser()
    _genesor_out = Path(args.out).expanduser() if args.out else None
    _cfg = GenesorConfig(
        repos_root=_repos_root,
        base_url=args.base_url,
        skin_base=args.skin_base,
        vendored_repos={r.strip() for r in args.vendored_repos.split(",") if r.strip()},
    )
    _cfg.genesor_out = _genesor_out
    # Sync: genesor-Sub-Module lesen _cfg via get_cfg() aus genesor.config —
    # set_cfg() aktualisiert diesen Singleton, damit beide Wege denselben Wert sehen.
    set_cfg(_cfg)

    if args.gen_impl_brief:
        try:
            repo_a, kd_a, screen_a = args.gen_impl_brief.split(":", 2)
        except ValueError:
            print(f"❌ Format: REPO:KD:SCREEN — '{args.gen_impl_brief}'")
            return 1
        records = find_all_repos_specs()
        rec = next((r for r in records if r["repo"] == repo_a and r["kd"] == kd_a), None)
        if not rec:
            print(f"❌ KD nicht gefunden: {repo_a}:{kd_a}")
            return 1
        brief_md = build_impl_brief(rec, screen_a)
        if brief_md is None:
            print(f"❌ Screen '{screen_a}' hat kein `implementation_brief`-Block ODER existiert nicht")
            return 1
        out_dir = _cfg.genesor_out / "impl-brief"
        out_dir.mkdir(parents=True, exist_ok=True)
        out_file = out_dir / f"{repo_a}-{kd_a}-{screen_a}.md"
        out_file.write_text(brief_md, encoding="utf-8")
        print(f"✓ {out_file} ({len(brief_md)} chars)")
        return 0

    if args.validate_ucs:
        records = find_all_repos_specs()
        ucs = find_all_repos_ucs()
        findings = validate_ucs(ucs, records)
        n_err = 0
        n_warn = 0
        for gid, items in sorted(findings.items()):
            for f in items:
                icon = "❌" if f["severity"] == "error" else "⚠"
                print(f'  {icon} {gid:<45} {f["code"]:<22} {f["msg"]}')
                if f["severity"] == "error":
                    n_err += 1
                else:
                    n_warn += 1
        n_clean = len(ucs) - len(findings)
        print(f"\nValidator (Layer A): {n_clean}/{len(ucs)} clean · {n_warn} warnings · {n_err} errors")
        if n_err > 0:
            return 1
        if args.strict and n_warn > 0:
            print("--strict: warnings als FAIL")
            return 1
        return 0

    if args.prune_auto_ucs:
        # UC-Cleanup (Workshop 2026-05-26 #3): löscht ausschließlich Files mit
        # `auto_generated: true` im Frontmatter — handgepflegte UCs bleiben.
        deleted: list[Path] = []
        for uc_path in _cfg.repos_root.glob("*/docs/use-cases/**/UC-*.md"):
            try:
                text = uc_path.read_text("utf-8")
            except OSError:
                continue
            fm = _parse_uc_frontmatter(text)
            if not fm or not fm.get("auto_generated"):
                continue
            if args.dry_run:
                deleted.append(uc_path)
            else:
                uc_path.unlink()
                deleted.append(uc_path)
        for p in deleted:
            print(f"{'(dry) ' if args.dry_run else ''}🗑️  {p}")
        print(f"\n{len(deleted)} UC-File(s) {'würden gelöscht' if args.dry_run else 'gelöscht'}.")
        if args.auto_publish and deleted:
            _auto_publish_per_repo(deleted, action="prune",
                                  dry_run=args.dry_run,
                                  allow_main=args.allow_main_push)
        elif deleted and not args.dry_run:
            print("\n💡 Tipp: --auto-publish für direkten Commit+Push der Löschung")
        return 0

    if args.gen_uc_skeletons:
        records = find_all_repos_specs()
        existing_ucs = find_all_repos_ucs()
        result = generate_uc_skeletons(records, existing_ucs, dry_run=args.dry_run)
        for p in result["written"]:
            print(f"{'(dry) ' if args.dry_run else ''}✓ {p}")
        print(f"\n{len(result['written'])} UC-Skelette {'würden geschrieben' if args.dry_run else 'geschrieben'} · {result['skipped']} übersprungen (existierend/abgedeckt)")
        if args.auto_publish and result["written"]:
            _auto_publish_per_repo(result["written"], action="gen",
                                  dry_run=args.dry_run,
                                  allow_main=args.allow_main_push)
        elif result["written"] and not args.dry_run:
            print("\n💡 Tipp: --auto-publish für direkten Commit+Push (Edit-Links sofort auf GitHub aktiv)")
        return 0

    if not args.no_single:
        specs = find_specs()
        contracts = find_contracts()
        if specs:
            print(f"Single-Repo · gefundene Klickdummies: {len(specs)} · Contracts: {len(contracts)}")
            mermaid_text = emit_mermaid(specs, contracts)
            html_text = build_html(mermaid_text, specs, contracts)
            OUT_DIR.mkdir(parents=True, exist_ok=True)
            (OUT_DIR / "lineage.mmd").write_text(mermaid_text, encoding="utf-8")
            (OUT_DIR / "index.html").write_text(html_text, encoding="utf-8")
            print(f"✓ {OUT_DIR / 'lineage.mmd'}")
            print(f"✓ {OUT_DIR / 'index.html'}")

    if args.genesor:
        records = find_all_repos_specs()
        if not records:
            print(f"WARN: Keine Klickdummies unter {_cfg.repos_root} gefunden.", file=sys.stderr)
            return 1
        _cfg.genesor_out.mkdir(parents=True, exist_ok=True)
        print(f"Genesor (Cross-Repo) · gefundene Klickdummies: {len(records)} aus "
              f"{len({(r['org'], r['repo']) for r in records})} Repos / "
              f"{len({r['org'] for r in records})} Orgs")
        # Cross-Repo-Lookup für Auto-KD-Linking in Akten-Zeilen:
        # Aktentyp (z. B. „wohngeld") wird gegen diesen Set gematcht; existiert
        # ein KD, bekommt die Tabellen-Zeile einen Sprung-CTA ins Ziel-FV-KD.
        # Lookup: {kd_name: (url, repo)}. Repo wird im Modal als Cross-Repo-Hinweis
        # angezeigt (z. B. „nl2cad → risk-hub / cad-analyse").
        known_kds: dict[str, str] = {}
        known_kd_repos: dict[str, str] = {}
        for r in records:
            if r.get("kind", "spec") != "spec":
                continue
            kd = r["kd"]
            known_kds[kd] = f"./{r['repo']}-{kd}.html"
            known_kd_repos[kd] = r["repo"]
        # Render-Fallback: für jeden KD ohne shell.html eine generierte HTML
        n_rendered = 0
        for rec in records:
            if rec.get("kind", "spec") != "spec":
                continue   # render-only KDs haben schon HTML, kein Fallback nötig
            kd_dir = rec["path"].parent
            if find_mockup_html(kd_dir, rec["kd"]) is None:
                generate_render_fallback(rec, _cfg.genesor_out,
                                         known_kds=known_kds,
                                         known_kd_repos=known_kd_repos)
                n_rendered += 1
        if n_rendered:
            print(f"✓ {n_rendered} Render-Fallback-HTMLs in {_cfg.genesor_out / 'render'}/")
        # Stufe 1b: Per-Repo-Lineages zuerst (damit Genesor sie verlinken kann)
        # Implementation-Briefs auto-emittieren (Pilot ADR-Variante-3) für alle
        # Screens mit implementation_brief-Block (User-Wunsch 2026-05-26: P2)
        impl_briefs_dir = _cfg.genesor_out / "impl-brief"
        n_briefs = 0
        for rec in records:
            if rec.get("kind", "spec") != "spec":
                continue
            for s in (rec.get("data") or {}).get("screens") or []:
                if not isinstance(s, dict) or not s.get("implementation_brief"):
                    continue
                sid = s.get("id")
                brief_md = build_impl_brief(rec, sid)
                if not brief_md:
                    continue
                impl_briefs_dir.mkdir(parents=True, exist_ok=True)
                out_file = impl_briefs_dir / f"{rec['repo']}-{rec['kd']}-{sid}.md"
                out_file.write_text(brief_md, encoding="utf-8")
                # HTML-Render daneben (CD aus doc-profile)
                profile_ib = read_doc_profile(_cfg.repos_root / rec["repo"])
                style_ib = _DOMAIN_STYLES.get(profile_ib, _DOMAIN_STYLES["default"])
                html_out_ib = build_impl_brief_html(brief_md, rec["repo"], rec["kd"], sid, profile_ib, style_ib)
                (_cfg.genesor_out / f"impl-brief-{rec['repo']}-{rec['kd']}-{sid}.html").write_text(html_out_ib, encoding="utf-8")
                n_briefs += 1
        if n_briefs:
            print(f"✓ {n_briefs} Implementation-Brief(s) in {impl_briefs_dir}/")

        # Per-KD Screen-Lineage (User-Feedback 2026-05-26 "vermisse das gesamt-lineage")
        n_screen_lineage = 0
        for rec in records:
            if rec.get("kind", "spec") != "spec":
                continue
            d = rec.get("data") or {}
            if not (d.get("screens") or []):
                continue
            repo_kd = rec["repo"]
            kd_kd = rec["kd"]
            profile_sl = read_doc_profile(_cfg.repos_root / repo_kd)
            style_sl = _DOMAIN_STYLES.get(profile_sl, _DOMAIN_STYLES["default"])
            html_out_sl = build_screen_lineage_html(repo_kd, kd_kd, d, profile_sl, style_sl)
            (_cfg.genesor_out / f"screen-lineage-{repo_kd}-{kd_kd}.html").write_text(html_out_sl, encoding="utf-8")
            n_screen_lineage += 1
        if n_screen_lineage:
            print(f"✓ {n_screen_lineage} Screen-Lineage-Pages in {_cfg.genesor_out}/")

        per_repo_files = generate_per_repo_lineages(records, _cfg.genesor_out)
        for p in per_repo_files:
            print(f"✓ {p}")
        # UC-Coverage (ADR-211 Rev 16 §UC-Coverage) — cross-repo Heatmap
        ucs = find_all_repos_ucs()
        coverage = build_uc_coverage(ucs, records)
        coverage_html = build_coverage_html(ucs, records, coverage)
        (_cfg.genesor_out / "coverage.html").write_text(coverage_html, encoding="utf-8")
        n_realized = sum(1 for v in coverage["uc_realized_count"].values() if v > 0)
        n_cells = sum(len(v) for v in coverage["matrix"].values())
        print(f"✓ {_cfg.genesor_out / 'coverage.html'} ({len(ucs)} UCs / {n_realized} realized / {n_cells} cells)")

        # UC-Validator (Layer A) — Workshop 2026-05-26
        uc_findings = validate_ucs(ucs, records)
        n_err = sum(1 for v in uc_findings.values() for f in v if f["severity"] == "error")
        n_warn = sum(1 for v in uc_findings.values() for f in v if f["severity"] == "warning")
        n_clean = len(ucs) - len(uc_findings)
        print(f"--- UC-Validator (Layer A): {n_clean}/{len(ucs)} clean · {n_warn}w · {n_err}e ---")

        # Pro-Repo UC-Index (Workshop-Feedback 2026-05-26 #1)
        ucs_by_repo: dict[str, list[dict]] = {}
        for u in ucs:
            ucs_by_repo.setdefault(u["repo"], []).append(u)
        for repo_name, ucs_for_repo in ucs_by_repo.items():
            uc_idx_html = build_repo_uc_index_html(repo_name, ucs_for_repo, coverage,
                                                  kds=records, validation=uc_findings)
            (_cfg.genesor_out / f"uc-{repo_name}.html").write_text(uc_idx_html, encoding="utf-8")
            print(f"✓ {_cfg.genesor_out / ('uc-' + repo_name + '.html')} ({len(ucs_for_repo)} UCs)")

        # JSON-Export (Workshop-Feedback 2026-05-26 #5) — strukturierter Snapshot
        # für externe Konsumenten (Backstage, Excel, Linear-Sync, PDF-Report).
        export_json = build_uc_export_json(ucs, records, coverage)
        (_cfg.genesor_out / "uc-export.json").write_text(export_json, encoding="utf-8")
        print(f"✓ {_cfg.genesor_out / 'uc-export.json'} ({len(export_json)} chars)")

        # Genesor-Übersicht
        genesor_html = build_genesor_html(records, uc_coverage=coverage, n_ucs=len(ucs))
        (_cfg.genesor_out / "index.html").write_text(genesor_html, encoding="utf-8")
        print(f"✓ {_cfg.genesor_out / 'index.html'}")

        # ---- Smoke-Test (Standard nach jeder --genesor-Run) ------------------
        # Verhalten als Standard integriert (User-Vorschlag 2026-05-25):
        # Pattern-basierte Smoke-Checks der generierten Render-Output-Files.
        # Kein Playwright-Browser nötig — curl-frei Pure-Python Pattern-Match.
        print("\n--- Smoke-Test (Render-Output) ---")
        smoke_pass = 0
        smoke_fail = 0
        smoke_results = []
        for rec in records:
            if rec.get("kind", "spec") != "spec":
                continue
            kd_name = rec["kd"]
            repo = rec["repo"]
            render_path = _cfg.genesor_out / "render" / f"{repo}-{kd_name}.html"
            if not render_path.is_file():
                continue
            content = render_path.read_text("utf-8")
            checks = [
                ("App-Frame vorhanden", '<div class="app-frame"' in content),
                ("ℹ Info-Button (Spec-Sicht)", 'ℹ Info' in content),
                ("❓ Hilfe-Button (End-User)", '❓ Hilfe' in content),
                ("Info-Modal-Global", 'id="info-modal-bg"' in content),
                ("Info-Hidden-Container", '<div class="screen-info" hidden' in content),
                ("Help-Hidden-Container", '<div class="screen-help" hidden' in content),
                ("Persona-Switcher", 'id="persona-select"' in content),
                ("Style-Switcher (Skin-Dropdown)", 'id="skin-select"' in content),
                ("Feedback-Widget (widget.js)", "KLICKDUMMY_FEEDBACK_REPO" in content),
                ("Spec-Sicht-Toggle", 'id="spec-toggle"' in content),
                ("Status-Bar", '<div class="app-statusbar">' in content),
                ("Layout-Modus aktiv (Sidebar oder Tab-Bar)", 'class="has-sidebar"' in content or 'class="has-tabs"' in content),
                ("Akte-Modal-Container vorhanden", '<div class="screen-akte" hidden' in content),
                ("Akten-Link in Tabellen (sofern Entity Aktenzeichen hat)",
                 'class="akten-link"' in content or 'aktenzeichen' not in content.lower()),
            ]
            failed = [name for name, ok in checks if not ok]
            if failed:
                smoke_fail += 1
                smoke_results.append(f"  ❌ {repo}-{kd_name}: {', '.join(failed)}")
            else:
                smoke_pass += 1
        print(f"Smoke: {smoke_pass} passed, {smoke_fail} failed")
        for r in smoke_results[:5]:
            print(r)
        if smoke_fail > 0:
            print(f"\n⚠ {smoke_fail} Render(s) mit fehlenden Pattern. Re-Generierung oder Code-Fix nötig.", file=sys.stderr)

    return 0


def main_cli() -> int:
    """Console-Script-Entry (klickdummy-genesor)."""
    return main()


if __name__ == "__main__":
    sys.exit(main_cli())

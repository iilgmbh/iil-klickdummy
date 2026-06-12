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
import html
import sys
from pathlib import Path


from .gen_e2e import is_fragile_selector, render_assertion

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

# Kanonisches Feedback-Widget (widget.js, PAT-Modal + GitHub-direct) — wird in den
# Render injiziert (platform:ADR-211 Rev 13), ersetzt das alte inline-Widget.
try:
    FEEDBACK_WIDGET_JS = (
        Path(__file__).resolve().parent / "snippets" / "feedback-widget" / "widget.js"
    ).read_text(encoding="utf-8")
except Exception:  # noqa: BLE001
    FEEDBACK_WIDGET_JS = "/* widget.js nicht gefunden */"

# Story-Banner-JS: lädt ../../stories-manifest.json (neben klickdummy-browser.html)
# und baut den Story-Banner im Render ein. Fetch scheitert bei file://-Protokoll
# oder fehlendem Manifest — dann bleibt der Banner versteckt (silent fail).
STORY_BANNER_JS = r"""
(function() {
  var KD_NAME = document.getElementById('story-banner-js')
    ? document.getElementById('story-banner-js').dataset.kd : null;
  if (!KD_NAME) return;
  var MANIFEST_PATH = '../../stories-manifest.json';
  var activeStoryIdx = 0;
  var entries = [];
  function dot(active) {
    return '<span style="width:8px;height:8px;border-radius:50%;background:' +
      (active ? '#fff' : 'rgba(255,255,255,.35)') + ';display:inline-block"></span>';
  }
  function showEntry(idx) {
    var e = entries[idx];
    if (!e) return;
    document.getElementById('sb-story-title').textContent = e.story_title;
    document.getElementById('sb-step-num').textContent = e.step_index + 1;
    document.getElementById('sb-step-total').textContent = e.step_total;
    var dots = '';
    for (var i = 0; i < e.step_total; i++) dots += dot(i === e.step_index);
    document.getElementById('sb-dots').innerHTML = dots;
    var prev = document.getElementById('sb-prev');
    var next = document.getElementById('sb-next');
    if (e.prev_shell) {
      prev.href = '../../' + e.prev_shell;
      document.getElementById('sb-prev-label').textContent = e.prev_label || '←';
      prev.style.display = '';
    } else { prev.style.display = 'none'; }
    if (e.next_shell) {
      next.href = '../../' + e.next_shell;
      document.getElementById('sb-next-label').textContent = e.next_label || '→';
      next.style.display = '';
    } else { next.style.display = 'none'; }
    if (entries.length > 1) {
      var sw = document.getElementById('sb-story-switch');
      sw.innerHTML = entries.map(function(en, i) {
        return i === idx
          ? '<strong>' + en.step_label + '</strong>'
          : '<a href="#" data-si="' + i + '" style="color:#9bb3d4">' + en.step_label + '</a>';
      }).join(' · ');
      sw.querySelectorAll('a[data-si]').forEach(function(a) {
        a.addEventListener('click', function(ev) {
          ev.preventDefault();
          activeStoryIdx = parseInt(a.dataset.si, 10);
          showEntry(activeStoryIdx);
        });
      });
    }
    document.getElementById('story-banner').style.display = 'flex';
  }
  fetch(MANIFEST_PATH)
    .then(function(r) { return r.ok ? r.json() : null; })
    .then(function(m) {
      if (!m) return;
      entries = m.kd_to_stories[KD_NAME] || [];
      if (entries.length > 0) showEntry(activeStoryIdx);
    })
    .catch(function() {});
})();
"""

OUT_DIR = ROOT / "docs" / "01-architektur" / "lineage"           # Single-Repo-Lineage (Rückwärtskompat)


# _base_prefix, _skin_url, MOCKUP_PRIO_NAMES imported from .genesor.config above.

# ---- Mockup-HTML-Discovery (Stufe 1b: "Klickdummy klickbar") ---------------


# ---- Skin-Library (zentral in iil-klickdummy, via HTTP-Server-Root erreichbar)
# User-Feedback 2026-05-25: Style-Switcher als Demo-Werkzeug auch auf Root-Ebene
# (Genesor-Übersicht), mit localStorage-Persistenz cross-Render.

# SKIN_LIBRARY_REL imported from .genesor.config above.


def skin_library() -> list[tuple[str, str]]:
    """Skin-Library mit finalen Skin-URLs.

    Default (SKIN_BASE leer, BASE_URL "/") → "/iil-klickdummy/..." (byte-identisch zu früher).
    Mit --skin-base → "<skin-base>/<name>.css".
    Der Sentinel "__greenfield" bleibt unverändert.
    """
    return [
        (value if value == "__greenfield" else _skin_url(value), label)
        for value, label in SKIN_LIBRARY_REL
    ]


def build_skin_switcher_html(initial_value: str = "__greenfield") -> str:
    """HTML-Snippet für das Skin-Switcher-Dropdown — wird in Topbar + Genesor verwendet."""
    options = []
    for value, label in skin_library():
        sel = ' selected' if value == initial_value else ''
        options.append(f'<option value="{html.escape(value)}"{sel}>{html.escape(label)}</option>')
    return (
        '<div class="style-switch">'
        '<label for="skin-select">🎨 Style</label>'
        f'<select id="skin-select">{"".join(options)}</select>'
        '</div>'
    )


SKIN_SWITCHER_JS = """
  // Style-Switcher (Cross-Render localStorage-Persistenz)
  const SKIN_KEY = 'genesor_skin';
  function applySkin(url) {
    document.querySelectorAll('link[data-skin="1"]').forEach(l => l.remove());
    if (url && url !== '__greenfield') {
      const link = document.createElement('link');
      link.rel = 'stylesheet';
      link.href = url;
      link.setAttribute('data-skin', '1');
      document.head.appendChild(link);
    }
    try { localStorage.setItem(SKIN_KEY, url || '__greenfield'); } catch (e) {}
  }
  (function initSkin() {
    let saved = null;
    try { saved = localStorage.getItem(SKIN_KEY); } catch (e) {}
    const initial = window.INITIAL_SKIN || '__greenfield';
    const chosen = saved || initial;
    const sel = document.getElementById('skin-select');
    if (sel) {
      // Falls Spec-default da war, aber User hat selbst etwas anderes gewählt: User-Wahl gewinnt
      if (chosen !== initial) applySkin(chosen);
      else if (initial !== '__greenfield') applySkin(initial);
      // Stelle Dropdown auf Aktiv-Wert
      sel.value = chosen;
      sel.addEventListener('change', e => applySkin(e.target.value));
    } else if (initial !== '__greenfield') {
      applySkin(initial);
    }
  })();
"""


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

_OFFRAMP_CHIP_CLASS = {
    "static": "tr-static",
    "parity-staging": "tr-staging",
    "parity-green": "tr-green",
    "removed": "tr-removed",
}


def _screen_use_cases(s: dict) -> tuple[list[str], str]:
    """Betroffene Use Cases + Quell-Feld.

    Priorität: use_cases[] (first-class) > konzept_ref[] > akte_next.uc.
    """
    uc = s.get("use_cases")
    if isinstance(uc, list) and uc:
        return [str(x) for x in uc], "use_cases"
    kr = s.get("konzept_ref")
    if isinstance(kr, list) and kr:
        return [str(x) for x in kr], "konzept_ref"
    if isinstance(kr, str) and kr:
        return [kr], "konzept_ref"
    an = s.get("akte_next")
    if isinstance(an, dict) and an.get("uc"):
        return [str(an["uc"])], "akte_next.uc"
    return [], ""


def _screen_coverage(s: dict) -> tuple[int, int, list[str], list[str]]:
    """Pro-Screen Parity-Coverage aus parity_acceptance.

    Selbe Klassifikation wie gen_e2e (render_assertion/is_fragile_selector) —
    eine SoR für "ausführbar vs. prose-only vs. fragil".
    Returnt (n_executable, n_prose, prose_ids, fragile_ids).
    """
    pa = s.get("parity_acceptance") or []
    n_exec = n_prose = 0
    prose_ids: list[str] = []
    fragile_ids: list[str] = []
    for item in pa:
        if not isinstance(item, dict):
            continue
        a = item.get("assert")
        if render_assertion(a) is not None:
            n_exec += 1
            if isinstance(a, dict) and is_fragile_selector(a.get("selector")):
                fragile_ids.append(str(item.get("id", "?")))
        else:
            n_prose += 1
            prose_ids.append(str(item.get("id", "?")))
    return n_exec, n_prose, prose_ids, fragile_ids


def _gh_issue_url(repo: str, sid: str, kd_name: str, s: dict, kind: str) -> str:
    """Vorausgefüllter GitHub-New-Issue-Link, um eine fehlende Spec-Angabe anzulegen.

    kind-Routing (2b, platform:ADR-211 §Co-Creation-Loop):
    - use-case  → uc-klickdummy.yml (GitHub Issue Form, required-Felder erzwingen Inhalt)
    - off-ramp / parity → thin-prefill (Markdown body) bis eigene Forms gebaut sind
    Org via detect_org(repo) — kein Hardcode.
    """
    from urllib.parse import quote

    org = detect_org(repo)
    persona_raw = s.get("personas") or s.get("persona") or []
    persona = ", ".join(persona_raw) if isinstance(persona_raw, list) else str(persona_raw or "—")

    if kind == "use-case":
        # Routet auf das strukturierte GitHub Issue Form (uc-klickdummy.yml).
        # title trägt den Spec-Anker (kd/screen); required-Felder erzwingen Inhalt.
        route = s.get("route", "")
        spec_id = s.get("spec_id", "")
        anker = f"kd={kd_name} · screen={sid} · route={route} · spec_id={spec_id}"
        daten = "; ".join(
            f"{f.get('name', '?')}:{f.get('type', '?')}"
            for f in (s.get("datafields") or [])[:6]
        )
        return (
            f"https://github.com/{org}/{repo}/issues/new"
            f"?template=uc-klickdummy.yml"
            f"&title={quote(f'UC: {kd_name}/{sid} — ')}"
            f"&labels={quote('uc-draft,needs-domain-review')}"
        )

    # off-ramp + parity: Markdown-body-Prefill bis eigene Forms existieren
    titles = {
        "off-ramp": f"off_ramp_status fehlt: {kd_name}/{sid}",
        "parity": f"parity_acceptance fehlt: {kd_name}/{sid}",
    }
    body = (
        f"Aus Klickdummy-Spec-Sicht (platform:ADR-211).\n\n"
        f"- **Klickdummy:** {kd_name}\n- **Screen:** `{sid}` — {s.get('title', '')}\n"
        f"- **Personas:** {persona}\n- **Zweck:** {s.get('purpose', '—')}\n\n"
        f"**Aufgabe ({kind}):** fehlende Spec-Angabe ergänzen.\n"
    )
    return (
        f"https://github.com/{org}/{repo}/issues/new"
        f"?labels={quote(kind)}&title={quote(titles.get(kind, kind))}&body={quote(body)}"
    )


def build_trace_strip(
    s: dict, klass: str, role: str, accept_status: dict, repo: str = "", kd_name: str = "", sid: str = ""
) -> str:
    """Gelabeltes Spec-Sicht-Panel pro Screen (X-Ray) — substanzielle Inhalte +
    aktionierbare „anlegen"-Buttons für fehlende Pflicht-Angaben (ADR-211 Co-Creation)."""
    rows: list[str] = []

    # Screen-Titel am Kopf des Spec-Sicht-Panels (zeigt welcher Tab/Screen aktiv ist)
    _title = s.get("title") or sid or ""
    _sid_display = sid or s.get("id", "")
    if _title or _sid_display:
        _title_html = (
            f'<span class="tr-screen-title">'
            f'<span class="tr-screen-id">{html.escape(_sid_display)}</span>'
            + (f' — {html.escape(str(_title))}' if _title and _title != _sid_display else "")
            + '<span class="tr-screen-subtab"></span>'
            + f'</span>'
        )
        rows.append(f'<div class="tr-row tr-row-title">{_title_html}</div>')

    def row(icon: str, key: str, value_html: str, missing: bool = False) -> None:
        cls = "tr-v tr-missing" if missing else "tr-v"
        rows.append(
            f'<div class="tr-row"><span class="tr-k">{icon} {html.escape(key)}</span>'
            f'<span class="{cls}">{value_html}</span></div>'
        )

    def act(kind: str, label: str) -> str:
        if not (repo and kd_name and sid):
            return ""
        ls_key = f"kd-uc-inflight:{repo}:{kd_name}:{sid}:{kind}"
        issue_url = html.escape(_gh_issue_url(repo, sid, kd_name, s, kind))
        # data-uc-key  — localStorage-Schlüssel (Screen-Level-Basis).
        # data-uc-subtab-selector — JS liest beim Click den aktiven Sub-Tab-Namen
        # aus dem nächsten .sub-tabs-Container und hängt ihn an Schlüssel + Issue-Titel.
        # Kein aktiver Sub-Tab → verhält sich wie bisher.
        return (
            f' <a class="tr-act" target="_blank" rel="noopener" '
            f'data-uc-key="{html.escape(ls_key)}" '
            f'data-uc-subtab-selector=".sub-tabs .sub-tab.active" '
            f'href="{issue_url}">{html.escape(label)}</a>'
        )

    # 📋 Use Cases — klappbare Liste oder anlegen-Button
    ucs, uc_src = _screen_use_cases(s)
    if ucs:
        items = "".join(f'<li>{html.escape(u)}</li>' for u in ucs)
        uc_val = (
            f'<details class="tr-uc-details"><summary>{len(ucs)} UC(s)'
            f' <span class="tr-dim">({html.escape(uc_src)})</span></summary>'
            f'<ul class="tr-uc-list">{items}</ul></details>'
        )
        row("📋", "Use Cases", uc_val)
    else:
        row("📋", "Use Cases", "nicht deklariert" + act("use-case", "+ UC anlegen"), missing=True)

    # 📦 Daten — Entities + Datenfelder mit Typ
    konsumiert = s.get("konsumiert_entities") or []
    lokal = s.get("lokale_entities") or []
    datafields = s.get("datafields") or []
    ent_names = [
        str(e.get("name") or e.get("entity") or "?") if isinstance(e, dict) else str(e)
        for e in list(konsumiert) + list(lokal)
    ]
    df_parts = []
    if isinstance(datafields, list):
        for d in datafields:
            if isinstance(d, dict):
                nm = d.get("name", "?")
                ty = d.get("type")
                df_parts.append(f"{nm}:{ty}" if ty else str(nm))
            else:
                df_parts.append(str(d))
    if ent_names or df_parts:
        val = "Entitäten: " + (html.escape(", ".join(ent_names)) or "—")
        if df_parts:
            val += ' · <span class="tr-dim">Felder:</span> ' + html.escape(", ".join(df_parts))
        row("📦", "Daten", val)
    else:
        row("📦", "Daten", "keine Entities/Datenfelder deklariert", missing=True)

    # 🏷 Status — class/role/off-ramp/pipeline
    ors = s.get("off_ramp_status")
    pipeline = s.get("pipeline_status") or "klickdummy"
    status_bits = [f"class <b>{html.escape(klass)}</b>", f"role <b>{html.escape(role)}</b>", f"pipeline <b>{html.escape(str(pipeline))}</b>"]
    if ors:
        status_bits.insert(2, f'off-ramp <b>{html.escape(str(ors))}</b>')
        row("🏷", "Status", " · ".join(status_bits))
    else:
        row("🏷", "Status", " · ".join(status_bits) + " · <span class='tr-miss-inline'>off-ramp fehlt</span>" + act("off-ramp", "+ off-ramp"))

    # ✓ Abnahme — who/when je Achse
    acc_parts = []
    for axis, info in (accept_status or {}).items():
        label = "PO-Sign-Off" if axis == "spec_signed" else "Workshop-Walk"
        st = info.get("status")
        if st == "signed":
            acc_parts.append(f'✓ {label}: {html.escape(info.get("latest_by") or "?")} · {info.get("latest_date")} ({info.get("age_days")}d)')
        elif st == "stale":
            acc_parts.append(f'⚠ {label}: {info.get("age_days")}d alt — neue Abnahme empfohlen')
    if acc_parts:
        row("✓", "Abnahme", " · ".join(acc_parts))
    else:
        row("✓", "Abnahme", "keine Sign-Offs", missing=True)

    # 🎯 Coverage — n/m + prose-only/fragil aufgeschlüsselt
    n_exec, n_prose, prose_ids, fragile_ids = _screen_coverage(s)
    total = n_exec + n_prose
    if total:
        val = f"{n_exec}/{total} ausführbar"
        if prose_ids:
            val += ' · <span class="tr-dim">prose-only:</span> ' + html.escape(", ".join(prose_ids))
        if fragile_ids:
            val += ' · <span class="tr-miss-inline">fragil:</span> ' + html.escape(", ".join(fragile_ids))
        row("🎯", "Coverage (I1)", val)
    else:
        row("🎯", "Coverage (I1)", "keine parity_acceptance-Checks" + act("parity", "+ Parity"), missing=True)

    # ❓ Validierungsfrage — echter Text
    vf = s.get("validierungsfrage")
    if vf:
        row("❓", "Validierung", f'»{html.escape(str(vf))}«')

    return (
        '<div class="trace-strip" aria-label="Spec-Sicht (X-Ray)">'
        '<div class="trace-label">🔍 Spec-Sicht <span class="tr-dim">— spec-abgeleitet, in Prod ausgeblendet</span></div>'
        + "".join(rows)
        + "</div>"
    )


# ---- Render v2 Template ----------------------------------------------------

RENDER_FALLBACK_TEMPLATE = """<!DOCTYPE html>
<html lang="de">
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><text y='.9em' font-size='85'>🌱</text></svg>">
<title>Klickdummy: {kd_name} — {title}</title>
<style>
  :root {{
    --accent: {style_accent};
    --accent-bg: {style_accent_bg};
    --font-h: {style_font_h};
  }}
  * {{ box-sizing: border-box; }}
  body {{ font-family: -apple-system, "Segoe UI", system-ui, sans-serif; margin: 0; color: #1f2937; background: #f5f7fa; }}
  header.topbar {{ background: #fff; padding: 14px 24px; border-bottom: 1px solid #e3e8ee; display: flex; align-items: center; gap: 16px; flex-wrap: wrap; }}
  header.topbar h1 {{ font-family: var(--font-h); margin: 0; font-size: 19px; flex: 1; color: var(--accent); min-width: 200px; }}
  header.topbar .meta {{ color: #6b7280; font-size: 12px; }}
  header.topbar .badges span {{ display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 11px; font-weight: 600; margin-right: 4px; background: var(--accent-bg); color: var(--accent); }}
  header.topbar .persona-switch label {{ font-size: 12px; color: #6b7280; margin-right: 6px; }}
  header.topbar .persona-switch select {{ padding: 5px 10px; border: 1px solid #e3e8ee; border-radius: 4px; font-size: 13px; background: #fff; }}
  nav.tabs {{ background: #fff; border-bottom: 1px solid #e3e8ee; padding: 0 24px; display: flex; gap: 4px; overflow-x: auto; }}
  nav.tabs button {{ background: none; border: 0; padding: 12px 14px; cursor: pointer; font-size: 13px; color: #6b7280; border-bottom: 3px solid transparent; white-space: nowrap; }}
  nav.tabs button:hover {{ color: var(--accent); background: var(--accent-bg); }}
  nav.tabs button.active {{ color: var(--accent); border-bottom-color: var(--accent); font-weight: 600; }}
  nav.tabs button.hidden {{ display: none; }}
  /* Sidebar-Layout (User-Feedback: Tab-Scrolling bei >5 Screens UX-unschön) */
  body.has-sidebar main {{ display: grid; grid-template-columns: 240px 1fr; gap: 0; padding: 0; max-width: none; min-height: calc(100vh - 110px); }}
  body.has-sidebar nav.tabs {{ display: none; }}
  aside.sidebar {{ display: none; background: #fff; border-right: 1px solid #e3e8ee; padding: 16px 0; overflow-y: auto; }}
  body.has-sidebar aside.sidebar {{ display: block; }}
  aside.sidebar h3 {{ font-family: var(--font-h); margin: 0 16px 8px; font-size: 11px; text-transform: uppercase; letter-spacing: 0.5px; color: #6b7280; padding-top: 12px; }}
  aside.sidebar h3:first-child {{ padding-top: 0; }}
  aside.sidebar button {{ display: block; width: 100%; text-align: left; background: none; border: 0; padding: 9px 16px 9px 24px; cursor: pointer; font-size: 13px; color: #1f2937; border-left: 3px solid transparent; white-space: normal; line-height: 1.3; }}
  aside.sidebar button:hover {{ background: var(--accent-bg); color: var(--accent); }}
  aside.sidebar button.active {{ background: var(--accent-bg); color: var(--accent); border-left-color: var(--accent); font-weight: 600; }}
  aside.sidebar button.hidden {{ display: none; }}
  aside.sidebar button small {{ display: block; color: #9ca3af; font-size: 10px; margin-top: 2px; }}
  body.has-sidebar section.screen {{ padding: 24px; max-width: 900px; }}
  main {{ padding: 24px; max-width: 1100px; margin: 0 auto; }}
  section.screen {{ display: none; }}
  section.screen.active {{ display: block; }}
  /* APP-FRAME — macht jeden Screen als "Bildschirm" einer App erkennbar */
  .app-frame {{ background: #fff; border: 1px solid #d0d5dd; border-radius: 8px; overflow: hidden; box-shadow: 0 4px 24px rgba(0,0,0,.08); }}
  .app-bar {{ background: var(--accent); color: #fff; padding: 8px 14px; display: flex; align-items: center; gap: 10px; font-family: var(--font-h); }}
  .app-bar .traffic {{ display: flex; gap: 5px; margin-right: 8px; }}
  .app-bar .traffic span {{ width: 11px; height: 11px; border-radius: 50%; display: inline-block; opacity: 0.85; }}
  .app-bar .traffic .r {{ background: #ed6a5e; }}
  .app-bar .traffic .y {{ background: #f5bf4f; }}
  .app-bar .traffic .g {{ background: #61c554; }}
  .app-bar .app-icon {{ font-size: 16px; }}
  .app-bar .app-name {{ font-size: 13px; font-weight: 600; flex: 1; }}
  .app-bar .app-user {{ font-size: 12px; opacity: 0.95; background: rgba(255,255,255,.15); padding: 3px 9px; border-radius: 12px; }}
  .app-toolbar {{ background: #f8fafc; border-bottom: 1px solid #e3e8ee; padding: 10px 16px; display: flex; align-items: center; gap: 12px; flex-wrap: wrap; }}
  .app-toolbar .breadcrumb {{ color: #6b7280; font-size: 12px; }}
  .app-toolbar .breadcrumb b {{ color: #1f2937; }}
  .app-toolbar h2 {{ font-family: var(--font-h); margin: 0; font-size: 18px; color: var(--accent); flex: 1; }}
  .app-toolbar .sid {{ font-family: monospace; font-size: 10px; color: #6b7280; background: var(--accent-bg); padding: 1px 5px; border-radius: 3px; }}
  .app-content {{ padding: 16px 20px; background: #fdfdfe; min-height: 280px; }}
  .app-actionbar {{ background: #f8fafc; border-top: 1px solid #e3e8ee; padding: 10px 16px; display: flex; gap: 8px; align-items: center; }}
  .app-actionbar .actions {{ display: flex; flex-wrap: wrap; gap: 8px; margin: 0; }}
  .app-statusbar {{ background: #eef1f5; border-top: 1px solid #d0d5dd; padding: 6px 16px; display: flex; justify-content: space-between; font-size: 11px; color: #6b7280; }}
  .app-statusbar code {{ background: rgba(0,0,0,.05); padding: 1px 5px; border-radius: 3px; font-size: 10px; }}
  .ac-chip {{ display: inline-block; padding: 1px 6px; border-radius: 3px; font-size: 10px; font-weight: 600; margin-right: 6px; cursor: help; }}
  .ac-signed {{ background: #d1fae5; color: #065f46; border: 1px solid #a7f3d0; }}
  .ac-stale  {{ background: #fef3c7; color: #92400e; border: 1px solid #fde68a; }}
  /* Info-Button + Modal (Funktionen vom Bildschirm getrennt) */
  .app-bar .info-btn, .app-bar .help-btn {{ background: rgba(255,255,255,.2); color: #fff; border: 1px solid rgba(255,255,255,.4); border-radius: 4px; padding: 2px 8px; font-size: 12px; cursor: pointer; }}
  .app-bar .info-btn:hover, .app-bar .help-btn:hover {{ background: rgba(255,255,255,.35); }}
  /* Style-Switcher in Topbar (User-Feedback 2026-05-25): live demo zwischen
     Greenfield- und Bestand-System-Looks ohne re-render */
  .style-switch {{ display: flex; align-items: center; gap: 6px; }}
  .style-switch label {{ font-size: 12px; color: #6b7280; }}
  .style-switch select {{ padding: 5px 10px; border: 1px solid #e3e8ee; border-radius: 4px; font-size: 13px; background: #fff; }}
  .info-modal-bg {{ display: none; position: fixed; inset: 0; background: rgba(0,0,0,.45); z-index: 200; align-items: center; justify-content: center; }}
  .info-modal-bg.show {{ display: flex; }}
  .info-modal {{ background: #fff; border-radius: 8px; box-shadow: 0 8px 32px rgba(0,0,0,.25); max-width: 600px; width: 90%; max-height: 80vh; overflow-y: auto; }}
  .info-modal-head {{ background: var(--accent); color: #fff; padding: 10px 18px; display: flex; justify-content: space-between; align-items: center; border-radius: 8px 8px 0 0; }}
  .info-modal-head h3 {{ margin: 0; font-family: var(--font-h); font-size: 15px; }}
  .info-modal-head .close-btn {{ background: rgba(255,255,255,.2); color: #fff; border: 0; padding: 2px 10px; border-radius: 4px; cursor: pointer; font-size: 16px; line-height: 1; }}
  .info-modal-body {{ padding: 16px 20px; font-size: 13px; }}
  .info-modal-body h4 {{ font-family: var(--font-h); font-size: 13px; color: var(--accent); margin: 12px 0 6px; text-transform: uppercase; letter-spacing: 0.5px; }}
  .info-modal-body ul {{ margin: 0 0 12px; padding-left: 20px; }}
  .info-modal-body li {{ margin-bottom: 4px; }}
  .info-modal-body code {{ background: var(--accent-bg); padding: 1px 5px; border-radius: 3px; font-size: 12px; }}
  /* Sub-Tabs im App-Content */
  .sub-tabs {{ display: flex; gap: 2px; border-bottom: 1px solid #e3e8ee; margin-bottom: 12px; overflow-x: auto; }}
  .sub-tabs button {{ background: none; border: 0; padding: 8px 12px; cursor: pointer; font-size: 12px; color: #6b7280; border-bottom: 2px solid transparent; white-space: nowrap; }}
  .sub-tabs button:hover {{ color: var(--accent); }}
  .sub-tabs button.active {{ color: var(--accent); border-bottom-color: var(--accent); font-weight: 600; background: var(--accent-bg); }}
  .sub-panel {{ display: none; }}
  .sub-panel.active {{ display: block; }}
  .persona-chip {{ display: inline-block; padding: 2px 8px; border-radius: 12px; background: var(--accent-bg); color: var(--accent); font-size: 11px; font-weight: 600; margin-right: 4px; }}
  .card {{ background: #fff; border: 1px solid #e3e8ee; border-radius: 8px; padding: 16px 18px; margin-bottom: 16px; box-shadow: 0 1px 2px rgba(0,0,0,.03); }}
  .card h3 {{ font-family: var(--font-h); margin: 0 0 10px; font-size: 13px; color: var(--accent); text-transform: uppercase; letter-spacing: 0.5px; }}
  .functions ul {{ margin: 0; padding-left: 20px; }}
  .functions li {{ margin-bottom: 6px; font-size: 14px; color: #1f2937; }}
  table.entity {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
  table.entity th {{ background: var(--accent-bg); color: var(--accent); padding: 6px 10px; text-align: left; font-weight: 600; border-bottom: 1px solid #e3e8ee; }}
  table.entity td {{ padding: 6px 10px; border-bottom: 1px solid #f0f3f6; }}
  table.entity tr:hover {{ background: #fafbfc; }}
  table.entity a.akten-link {{ color: var(--accent); text-decoration: underline dotted; cursor: pointer; font-weight: 500; }}
  table.entity a.akten-link:hover {{ background: var(--accent-bg); text-decoration: underline; }}
  a.akte-next-cta {{ display: inline-block; background: var(--accent); color: #fff !important; padding: 8px 14px; border-radius: 4px; text-decoration: none; font-weight: 600; margin-top: 8px; }}
  a.akte-next-cta:hover {{ opacity: 0.85; }}
  .entity-title {{ font-family: monospace; font-size: 11px; color: var(--accent); margin: 14px 0 4px; }}
  .actions {{ display: flex; flex-wrap: wrap; gap: 8px; margin-top: 4px; }}
  .actions button {{ padding: 8px 14px; border: 1px solid var(--accent); background: var(--accent); color: #fff; border-radius: 4px; cursor: pointer; font-size: 13px; font-weight: 600; }}
  .actions button.secondary {{ background: #fff; color: var(--accent); }}
  .cross-links {{ margin-top: 14px; display: flex; flex-wrap: wrap; gap: 6px; }}
  .cross-links a {{ display: inline-block; padding: 6px 12px; background: #fff; border: 1px dashed #cdd5dd; border-radius: 4px; color: var(--accent); text-decoration: none; font-size: 12px; }}
  .cross-links a:hover {{ border-color: var(--accent); background: var(--accent-bg); }}
  footer {{ background: #fff; border-top: 1px solid #e3e8ee; padding: 12px 24px; font-size: 12px; color: #6b7280; text-align: center; margin-top: 30px; }}
  footer a {{ color: var(--accent); }}
  footer code {{ font-size: 11px; background: var(--accent-bg); padding: 1px 5px; border-radius: 3px; }}
  .render-mode {{ font-size: 11px; color: #9ca3af; text-align: center; padding: 6px; background: #eef1f5; }}
  .empty-state {{ text-align: center; padding: 40px; color: #6b7280; }}
  .placeholder {{ background: #fef0d0; }}
  /* Spec-Layer (X-Ray) — gelabeltes Inhalts-Panel pro Screen, nur bei body.spec-view */
  .trace-strip {{ display: none; }}
  body.spec-view .trace-strip {{ display: block; margin-top: 8px; padding: 10px 14px; background: #1f2937; border-radius: 6px; font-size: 12.5px; line-height: 1.5; }}
  .trace-strip .trace-label {{ color: #93c5fd; font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: .5px; margin-bottom: 6px; }}
  .tr-row {{ display: flex; gap: 12px; padding: 4px 0; border-top: 1px solid #374151; align-items: baseline; }}
  .tr-k {{ color: #93c5fd; font-weight: 600; min-width: 140px; flex-shrink: 0; }}
  .tr-v {{ color: #e5e7eb; flex: 1; }}
  .tr-v b {{ color: #fff; }}
  .tr-v.tr-missing {{ color: #fca5a5; font-style: italic; }}
  .tr-dim {{ color: #9ca3af; }}
  .tr-miss-inline {{ color: #fca5a5; }}
  .tr-act {{ display: inline-block; margin-left: 8px; padding: 1px 8px; border: 1px solid #34d399; border-radius: 4px; color: #34d399 !important; text-decoration: none; font-size: 11px; font-weight: 600; font-style: normal; }}
  .tr-act:hover {{ background: #34d399; color: #06281d !important; }}
  .tr-act-inflight {{ display: inline-block; margin-left: 8px; padding: 1px 8px; border: 1px solid #f59e0b; border-radius: 4px; color: #92400e !important; background: #fef3c7; font-size: 11px; font-weight: 600; cursor: pointer; }}
  .tr-act-inflight:hover {{ background: #fde68a; }}
  .tr-row-title {{ padding: 4px 0 6px; border-bottom: 1px solid #334155; margin-bottom: 4px; }}
  .tr-screen-title {{ font-size: 13px; font-weight: 700; color: #e2e8f0; letter-spacing: .01em; }}
  .tr-screen-id {{ font-family: ui-monospace, monospace; color: #7dd3fc; font-size: 12px; }}
  .tr-screen-subtab {{ color: #93c5fd; font-weight: 600; }}
  details.tr-uc-details {{ display: inline; }}
  details.tr-uc-details > summary {{ display: inline; cursor: pointer; color: #06c; font-size: 12px; }}
  ul.tr-uc-list {{ margin: 4px 0 2px 16px; padding: 0; font-size: 11px; color: #374151; }}
  /* Spec-Sicht-Toggle im Header */
  .spec-toggle {{ display: inline-flex; align-items: center; gap: 6px; padding: 5px 12px; border: 1px solid #d0d5dd; border-radius: 4px; background: #fff; font-size: 13px; cursor: pointer; color: #374151; }}
  .spec-toggle.on {{ background: #1f2937; color: #fff; border-color: #1f2937; }}
  .spec-toggle .dot {{ width: 8px; height: 8px; border-radius: 50%; background: #cbd5e1; }}
  .spec-toggle.on .dot {{ background: #34d399; }}
  /* Keyboard-Fokus sichtbar machen (Tabs, Sidebar, Sub-Tabs) */
  nav.tabs button:focus-visible, aside.sidebar button:focus-visible,
  .sub-tabs button:focus-visible {{ outline: 2px solid var(--accent); outline-offset: -2px; }}
  /* Responsive: Sidebar-Grid + Abstände unter 768px (Mobil/Tablet hochkant) */
  @media (max-width: 768px) {{
    body.has-sidebar main {{ grid-template-columns: 1fr; min-height: 0; }}
    aside.sidebar {{ border-right: 0; border-bottom: 1px solid #e3e8ee; padding: 8px 0; }}
    body.has-sidebar section.screen {{ padding: 16px; }}
    main {{ padding: 16px; }}
    header.topbar {{ padding: 10px 16px; gap: 10px; }}
    header.topbar h1 {{ min-width: 0; font-size: 16px; }}
    .fb {{ width: calc(100vw - 32px); }}
  }}
  /* Custom-CSS-Hook — wenn spec.app_skin.custom_css gesetzt, lädt nach dem inline-Style ein zusätzliches CSS */
  /* Damit kann Bestand-System-Skin (OK.Wobis, eigene CI etc.) injiziert werden, ohne Render zu ändern */
</style>
{custom_css_link}
<style>
  /* Spacer-Style-Block — verhindert dass {{custom_css_link}} Format-Hole stört */
  .render-skin-applied {{ /* marker */ }}
  /* Feedback-Widget pro Screen */
  .fb {{ position: fixed; bottom: 16px; right: 16px; width: 320px; background: #fff; border: 1px solid var(--accent); border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,.12); font-size: 13px; z-index: 100; }}
  .fb-head {{ background: var(--accent); color: #fff; padding: 8px 12px; border-radius: 8px 8px 0 0; cursor: pointer; display: flex; justify-content: space-between; align-items: center; font-weight: 600; }}
  .fb-body {{ padding: 12px; }}
  .fb-body.hidden {{ display: none; }}
  .fb label {{ display: block; margin: 6px 0 2px; font-size: 12px; color: #555; }}
  .fb select, .fb textarea {{ width: 100%; box-sizing: border-box; padding: 4px 6px; border: 1px solid #ccc; border-radius: 4px; font-size: 13px; font-family: inherit; }}
  .fb textarea {{ height: 60px; resize: vertical; }}
  .fb .row {{ display: flex; gap: 6px; margin-top: 8px; }}
  .fb button {{ padding: 6px 10px; border: 1px solid var(--accent); background: var(--accent); color: #fff; border-radius: 4px; cursor: pointer; font-size: 13px; }}
  .fb button.secondary {{ background: #fff; color: var(--accent); }}
  .fb .status {{ margin-top: 6px; font-size: 12px; color: #060; }}
  .fb .screen-ctx {{ background: var(--accent-bg); padding: 4px 8px; border-radius: 3px; font-size: 11px; color: var(--accent); margin-bottom: 6px; }}
</style>
</head>
<body class="{body_class}">

<!-- Story-Banner: sichtbar wenn stories-manifest.json gefunden + KD in einer Story -->
<div id="story-banner" style="display:none;background:#1a3a6c;color:#fff;padding:8px 20px;font-size:13px;align-items:center;gap:12px;flex-wrap:wrap">
  <span style="font-weight:600">📖 <span id="sb-story-title"></span></span>
  <span style="opacity:.7;font-size:11px">Schritt <span id="sb-step-num"></span> / <span id="sb-step-total"></span></span>
  <span id="sb-dots" style="display:flex;gap:4px;align-items:center"></span>
  <a id="sb-prev" href="#" style="color:#fff;text-decoration:none;padding:3px 10px;border:1px solid rgba(255,255,255,.4);border-radius:4px;font-size:12px">← <span id="sb-prev-label"></span></a>
  <a id="sb-next" href="#" style="color:#fff;text-decoration:none;padding:3px 10px;border:1px solid rgba(255,255,255,.4);border-radius:4px;font-size:12px"><span id="sb-next-label"></span> →</a>
  <span id="sb-story-switch" style="margin-left:auto;font-size:11px;opacity:.8"></span>
</div>

<header class="topbar">
  <h1>{title}<span id="screen-title-dynamic" style="font-weight:400;font-size:13px;opacity:.7;margin-left:10px"></span></h1>
  <div>
    <div class="badges">
      <span>class: {klass}</span>
      <span>role: {role}</span>
      <span>sunset: {sunset}</span>
    </div>
    <div class="meta">KD <code>{kd_name}</code> · Repo <code>{repo}</code></div>
  </div>
  <div class="persona-switch">
    <label for="persona-select">👤 Persona</label>
    <select id="persona-select">
      <option value="__all__">— alle Personas —</option>
      {persona_options}
    </select>
  </div>
  {skin_switcher_html}
  <button class="spec-toggle" id="spec-toggle" aria-pressed="false" title="Spec-Sicht (X-Ray) ein/aus — Taste S. Zeigt UC, Daten, Status & Coverage pro Screen, direkt aus der Spec.">
    <span class="dot"></span> Spec-Sicht
  </button>
</header>
<script>window.INITIAL_SKIN = "{initial_skin}";</script>

<nav class="tabs" id="tabs" role="tablist" aria-label="Screens">
  {tab_buttons}
</nav>

<main>
  <aside class="sidebar" id="sidebar">
    {sidebar_content}
  </aside>
  <div class="screens-area">
    {screen_sections}
    <section class="screen" id="screen-__empty__">
      <div class="empty-state">
        <p>Keine Screens für die gewählte Persona — wähle eine andere Persona oben rechts.</p>
      </div>
    </section>
  </div>
</main>

<footer>
  Klickdummy <code>{kd_name}</code> (Spec-Render mit synthetischen Daten)
  · Spec: <a href="/{spec_rel}">{spec_rel}</a>
  · <a href="/genesor/screen-lineage-{repo}-{kd_name}.html">🕸 Screen-Lineage</a>
  · <a href="/genesor/">↩ zur Genesor-Übersicht</a>
</footer>

<!-- Globales Info-Modal (Funktionen / Verhalten vom Bildschirm getrennt) -->
<div class="info-modal-bg" id="info-modal-bg" onclick="if(event.target===this)closeInfoModal()">
  <div class="info-modal" role="dialog" aria-modal="true" aria-labelledby="info-modal-title">
    <div class="info-modal-head">
      <h3 id="info-modal-title">Funktionen / Verhalten</h3>
      <button class="close-btn" onclick="closeInfoModal()" aria-label="Dialog schließen">×</button>
    </div>
    <div class="info-modal-body" id="info-modal-body">—</div>
  </div>
</div>

<div class="render-mode">Render-Mode: Auto-Generator v2 aus screens-spec.yaml · synthetische Beispiel-Daten, kein Backend</div>

<!-- Feedback-Widget pro Screen — kanonisches widget.js (PAT-Modal + GitHub-direct),
     platform:ADR-211 Rev 13 §Co-Creation. Ersetzt das alte inline-Download/Clipboard-Widget. -->
<script>
  window.KLICKDUMMY_SPEC = {{ id: "{kd_name}", version: "1.0", klickdummy_class: "{klass}" }};
  window.KLICKDUMMY_FEEDBACK_REPO = "{feedback_repo}";
  window.KLICKDUMMY_FEEDBACK_FORCE = true;
</script>
<script>__FEEDBACK_WIDGET_JS_PLACEHOLDER__</script>
<!-- fb-current-subtab: hidden Tracker für aktiven Sub-Tab (Issue #34).
     JS (Sub-Tab-Switch-Handler) schreibt textContent; fbCollect() + UC-anlegen lesen es. -->
<span id="fb-current-subtab" style="display:none"></span>
<!-- fb-current-persona: hidden Tracker für aktiven Persona-Filter.
     applyPersonaFilter() schreibt textContent, fbCollect() liest es. War nie
     gerendert → applyPersonaFilter crashte (TypeError, UX-Test 2026-06-02). -->
<span id="fb-current-persona" style="display:none">alle</span>
<script id="story-banner-js" data-kd="{kd_name}">__STORY_BANNER_JS_PLACEHOLDER__</script>

<script>
  // Sowohl Top-Tabs als auch Sidebar-Buttons fungieren als Navigation
  const tabs = document.querySelectorAll('#tabs button, #sidebar button');
  const screens = document.querySelectorAll('section.screen');
  const personaSelect = document.getElementById('persona-select');

  function showScreen(id) {{
    screens.forEach(s => s.classList.toggle('active', s.id === 'screen-' + id));
    tabs.forEach(t => {{
      const on = t.dataset.screen === id;
      t.classList.toggle('active', on);
      if (t.getAttribute('role') === 'tab') {{
        t.setAttribute('aria-selected', on ? 'true' : 'false');
      }} else if (on) {{
        t.setAttribute('aria-current', 'true');
      }} else {{
        t.removeAttribute('aria-current');
      }}
    }});
    // Scroll-Reset: langer Screen A → kurzer Screen B ließ den Nutzer sonst
    // mitten im Leeren stehen
    window.scrollTo({{ top: 0 }});
    const ctx = document.getElementById('fb-current-screen');
    if (ctx) ctx.textContent = id;
    // Topbar-Untertitel: aktiven Screen-Namen anzeigen (Bug-Fix #40)
    const activeTab = document.querySelector(
      '#tabs button[data-screen="' + id + '"], #sidebar button[data-screen="' + id + '"]'
    );
    const titleEl = document.getElementById('screen-title-dynamic');
    if (titleEl && activeTab) {{
      const clone = activeTab.cloneNode(true);
      clone.querySelectorAll('small').forEach(function(el) {{ el.remove(); }});
      titleEl.textContent = clone.textContent.trim();
    }}
  }}

  tabs.forEach(t => {{
    t.addEventListener('click', () => showScreen(t.dataset.screen));
  }});

  // Pfeiltasten-Navigation: ←/→ in der Tab-Leiste, ↑/↓ in der Sidebar
  // (versteckte = persona-gefilterte Buttons werden übersprungen)
  tabs.forEach(t => {{
    t.addEventListener('keydown', e => {{
      const fwd = e.key === 'ArrowRight' || e.key === 'ArrowDown';
      const back = e.key === 'ArrowLeft' || e.key === 'ArrowUp';
      if (!fwd && !back) return;
      const root = t.closest('#tabs') || t.closest('#sidebar');
      if (!root) return;
      const list = [...root.querySelectorAll('button[data-screen]')]
        .filter(b => !b.classList.contains('hidden'));
      const i = list.indexOf(t);
      if (i < 0) return;
      e.preventDefault();
      const next = list[(i + (fwd ? 1 : -1) + list.length) % list.length];
      next.focus();
      showScreen(next.dataset.screen);
    }});
  }});

  function applyPersonaFilter() {{
    const p = personaSelect.value;
    const fbPersona = document.getElementById('fb-current-persona');
    if (fbPersona) fbPersona.textContent = p === '__all__' ? 'alle' : p;
    const visibleScreens = [];
    tabs.forEach(t => {{
      const screenPersonas = (t.dataset.personas || '').split(',').filter(Boolean);
      const visible = p === '__all__' || screenPersonas.includes(p);
      t.classList.toggle('hidden', !visible);
      if (visible) visibleScreens.push(t.dataset.screen);
    }});
    const activeTab = document.querySelector('#tabs button.active:not(.hidden)');
    if (!activeTab && visibleScreens.length) {{
      showScreen(visibleScreens[0]);
    }} else if (!visibleScreens.length) {{
      showScreen('__empty__');
    }}
  }}

  personaSelect.addEventListener('change', applyPersonaFilter);

  // Deep-Link: ?#screen-<id> aus URL respektieren (Cross-KD-Sprung)
  function _initialScreen(defaultId) {{
    if (location.hash.startsWith('#screen-')) {{
      const wanted = location.hash.substring('#screen-'.length);
      if (document.getElementById('screen-' + wanted)) return wanted;
    }}
    return defaultId;
  }}
  if (tabs.length) showScreen(_initialScreen(tabs[0].dataset.screen));
  // Reagiere auch wenn Hash sich ändert (z. B. weiter im Workflow)
  window.addEventListener('hashchange', () => {{
    if (location.hash.startsWith('#screen-')) {{
      const wanted = location.hash.substring('#screen-'.length);
      if (document.getElementById('screen-' + wanted)) showScreen(wanted);
    }}
  }});

  __SKIN_SWITCHER_JS_PLACEHOLDER__

  // Modal-Focus-Management: Fokus auf Schließen-Button, Rückgabe beim Schließen,
  // Tab bleibt im Dialog (leichter Focus-Trap)
  let _modalReturnFocus = null;
  function _modalShow() {{
    _modalReturnFocus = document.activeElement;
    document.getElementById('info-modal-bg').classList.add('show');
    const btn = document.querySelector('#info-modal-bg .close-btn');
    if (btn) btn.focus();
  }}
  document.getElementById('info-modal-bg').addEventListener('keydown', e => {{
    if (e.key !== 'Tab') return;
    const f = [...document.querySelectorAll(
      '#info-modal-bg .info-modal button, #info-modal-bg .info-modal a[href]'
    )].filter(el => el.offsetParent !== null);
    if (!f.length) return;
    const first = f[0], last = f[f.length - 1];
    if (e.shiftKey && document.activeElement === first) {{ e.preventDefault(); last.focus(); }}
    else if (!e.shiftKey && document.activeElement === last) {{ e.preventDefault(); first.focus(); }}
  }});

  // Zwei Modal-Funktionen — ℹ Info (Spec) + ❓ Hilfe (End-User)
  function _openModal(prefix, screenId) {{
    const tpl = document.getElementById(prefix + '-' + screenId);
    if (!tpl) return;
    const title = tpl.querySelector('.info-title')?.innerHTML || screenId;
    const content = tpl.querySelector('.info-content')?.innerHTML || '';
    document.getElementById('info-modal-title').innerHTML = title;
    document.getElementById('info-modal-body').innerHTML = content;
    _modalShow();
  }}
  function openInfoModal(screenId) {{ _openModal('info', screenId); }}
  function openHelpModal(screenId) {{ _openModal('help', screenId); }}
  // HTML-Escape für Werte, die per String-Konkatenation in innerHTML landen
  // (Spec-Daten sind nicht per se vertrauenswürdig, v. a. cross-repo).
  function _esc(s) {{
    return String(s).replace(/[&<>"']/g, c =>
      ({{'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'}})[c]);
  }}
  function openAkteModal(screenId, azs, aname, targetKd, targetUrl, targetRepo) {{
    const tpl = document.getElementById('akte-' + screenId);
    let title = '📁 Akte · ' + _esc(azs || '?');
    if (aname) title += ' · ' + _esc(aname);
    // Per-Row-CTA: existiert ein KD für diesen Aktentyp → Sprung-Link.
    // Cross-Repo-Sprünge bekommen einen sichtbaren Repo-Hinweis.
    let cta = '';
    if (targetKd && targetUrl) {{
      let repoHint = '';
      if (targetRepo && targetRepo !== KD_META.repo) {{
        repoHint = ' <span style="font-weight:normal;font-size:12px;opacity:.85;">(cross-repo: '
                 + _esc(targetRepo) + ')</span>';
      }}
      cta = '<p style="margin:0 0 10px;"><a href="' + _esc(targetUrl)
          + '" class="akte-next-cta">→ Klickdummy „' + _esc(targetKd) + '" öffnen</a>'
          + repoHint + '</p>';
    }} else if (targetKd) {{
      cta = '<p style="color:#9ca3af;font-size:13px;margin:0 0 10px;">'
          + '→ Klickdummy für „' + _esc(targetKd) + '" noch nicht vorhanden.</p>';
    }}
    let extras = '';
    if (tpl) {{
      extras = tpl.querySelector('.info-content')?.innerHTML || '';
    }} else {{
      extras = '<p>Hier würde die Akte/der Vorgang öffnen. Spec-seitig (<code>screen.akte_next:</code>) noch nicht deklariert.</p>';
    }}
    document.getElementById('info-modal-title').innerHTML = title;
    document.getElementById('info-modal-body').innerHTML = cta + extras;
    _modalShow();
  }}
  document.querySelectorAll('a.akten-link').forEach(a => {{
    a.addEventListener('click', e => {{
      e.preventDefault();
      openAkteModal(
        a.dataset.sid,
        a.dataset.azs || '',
        a.dataset.aname || '',
        a.dataset.targetKd || '',
        a.dataset.targetUrl || '',
        a.dataset.targetRepo || ''
      );
    }});
  }});
  function closeInfoModal() {{
    document.getElementById('info-modal-bg').classList.remove('show');
    if (_modalReturnFocus && _modalReturnFocus.focus) _modalReturnFocus.focus();
    _modalReturnFocus = null;
  }}
  document.addEventListener('keydown', e => {{
    if (e.key === 'Escape') closeInfoModal();
  }});

  // Spec-Layer (X-Ray): globaler Toggle + Taste 's' (außer in Eingabefeldern)
  const specToggle = document.getElementById('spec-toggle');
  function setSpecView(on) {{
    document.body.classList.toggle('spec-view', on);
    if (specToggle) {{
      specToggle.classList.toggle('on', on);
      specToggle.setAttribute('aria-pressed', on ? 'true' : 'false');
    }}
    // Bug-Fix (UX-Test 2026-06-02): Panel sitzt am Screen-Ende, oft unter dem
    // Fold → ohne Scroll sieht der Nutzer nach dem Toggle scheinbar nichts.
    if (on) requestAnimationFrame(() => {{
      const strip = [...document.querySelectorAll('.trace-strip')]
        .find(s => s.offsetParent !== null);
      if (strip) strip.scrollIntoView({{ behavior: 'smooth', block: 'nearest' }});
    }});
  }}
  if (specToggle) {{
    specToggle.addEventListener('click', () =>
      setSpecView(!document.body.classList.contains('spec-view')));
  }}
  document.addEventListener('keydown', e => {{
    if (e.key !== 's' && e.key !== 'S') return;
    const t = e.target;
    if (t && (t.tagName === 'INPUT' || t.tagName === 'TEXTAREA'
              || t.tagName === 'SELECT' || t.isContentEditable)) return;
    setSpecView(!document.body.classList.contains('spec-view'));
  }});

  // Sub-Tabs innerhalb des App-Content
  document.querySelectorAll('.sub-tabs button').forEach(btn => {{
    btn.addEventListener('click', () => {{
      const subId = btn.dataset.sub;
      const container = btn.closest('.app-content');
      if (!container) return;
      container.querySelectorAll('.sub-tabs button').forEach(b => {{
        b.classList.remove('active');
        b.setAttribute('aria-selected', 'false');
      }});
      container.querySelectorAll('.sub-panel').forEach(p => p.classList.remove('active'));
      btn.classList.add('active');
      btn.setAttribute('aria-selected', 'true');
      const panel = container.querySelector('#sub-' + subId);
      if (panel) panel.classList.add('active');
      // fb-current-subtab: Feedback-Widget + UC-anlegen können aktiven Sub-Tab lesen
      const subtabEl = document.getElementById('fb-current-subtab');
      if (subtabEl) subtabEl.textContent = btn.textContent.replace(/^📊\\s*/, '').trim();
      // Spec-Sicht-Heading: aktiven Sub-Tab spiegeln (Feedback 2026-06-02)
      const _sec = btn.closest('section.screen');
      const _trSub = _sec && _sec.querySelector('.trace-strip .tr-screen-subtab');
      if (_trSub) _trSub.textContent =
        (_sec.querySelectorAll('.sub-tabs button').length >= 2)
          ? (' › ' + btn.textContent.replace(/^📊\\s*/, '').trim()) : '';
    }});
  }});
  // Initial: ersten aktiven Sub-Tab setzen (falls Sub-Tabs vorhanden)
  (function() {{
    const first = document.querySelector('.sub-tabs .sub-tab.active');
    const subtabEl = document.getElementById('fb-current-subtab');
    if (first && subtabEl) subtabEl.textContent = first.textContent.replace(/^📊\\s*/, '').trim();
  }})();
  // Initial: Spec-Sicht-Heading je Screen mit aktivem Sub-Tab füllen (≥2 Sub-Tabs)
  document.querySelectorAll('section.screen').forEach(sec => {{
    if (sec.querySelectorAll('.sub-tabs button').length < 2) return;
    const act = sec.querySelector('.sub-tabs button.active') || sec.querySelector('.sub-tabs button');
    const trSub = sec.querySelector('.trace-strip .tr-screen-subtab');
    if (act && trSub) trSub.textContent = ' › ' + act.textContent.replace(/^📊\\s*/, '').trim();
  }});

  // Feedback-Widget — Payload kennt aktuellen Screen + Persona
  const KD_META = {{
    kd_name: "{kd_name}",
    repo: "{repo}",
    klass: "{klass}",
    role: "{role}"
  }};
  function fbCollect() {{
    return {{
      spec_id: KD_META.kd_name,
      repo: KD_META.repo,
      klickdummy_class: KD_META.klass,
      spec_role: KD_META.role,
      feedback_scope: "screen",
      acceptance_verdict: document.getElementById('fb-verdict')?.value || null,
      screen_id: document.getElementById('fb-current-screen').textContent,
      active_subtab: (document.getElementById('fb-current-subtab')?.textContent || null) || null,
      persona_filter: (document.getElementById('fb-current-persona')?.textContent || 'alle'),
      kategorie: document.getElementById('fb-cat').value,
      text: document.getElementById('fb-text').value,
      ts: new Date().toISOString(),
      generated_from: document.title,
      conforms_to: "platform:ADR-211 Rev 13 §Co-Creation-Loop Pfad A-light"
    }};
  }}
  function fbDownload() {{
    const payload = fbCollect();
    const blob = new Blob([JSON.stringify(payload, null, 2)], {{ type: 'application/json' }});
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `feedback-${{KD_META.kd_name}}-${{payload.screen_id}}-${{Date.now()}}.json`;
    document.body.appendChild(a); a.click(); a.remove();
    URL.revokeObjectURL(url);
    document.getElementById('fb-status').textContent = "✓ heruntergeladen.";
  }}
  async function fbClipboard() {{
    await navigator.clipboard.writeText(JSON.stringify(fbCollect(), null, 2));
    document.getElementById('fb-status').textContent = "✓ im Clipboard.";
  }}
</script>

<script>
// UC-anlegen "in Arbeit"-State via localStorage (Issue #25)
// Sub-Tab-Awareness (Issue #34): data-uc-subtab-selector → sub-tab-spezifischer Key + Titel
(function() {{
  var INFLIGHT = '⏳ UC anlegen in Arbeit';
  function makeInflightHtml(key) {{
    return '<span class="tr-act tr-act-inflight" data-uc-reset="' + key + '" '
      + 'title="Issue angelegt — noch nicht in Spec. Klicken zum Zurücksetzen.">' + INFLIGHT + '</span>';
  }}
  // Aktiven Sub-Tab-Namen ermitteln (null wenn kein Sub-Tab aktiv)
  function activeSubtab(el) {{
    var sel = el.dataset.ucSubtabSelector;
    if (!sel) return null;
    var btn = document.querySelector(sel);
    return btn ? btn.textContent.replace(/^📊\\s*/, '').trim() : null;
  }}
  // Key + Issue-URL um Sub-Tab-Suffix erweitern
  function resolveKeyAndUrl(el) {{
    var baseKey = el.dataset.ucKey;
    var href = el.href;
    var subtab = activeSubtab(el);
    if (subtab) {{
      var suffix = ':subtab:' + subtab;
      return {{
        key: baseKey + suffix,
        href: href + '&title=' + encodeURIComponent(' [' + subtab + ']')
      }};
    }}
    return {{ key: baseKey, href: href }};
  }}
  // Event-Delegation: ein einziger Handler für alle Inflight-Spans
  document.addEventListener('click', function(e) {{
    var t = e.target.closest ? e.target.closest('.tr-act-inflight[data-uc-reset]') : null;
    if (!t) return;
    try {{ localStorage.removeItem(t.dataset.ucReset); }} catch(err) {{}}
    location.reload();
  }});
  function markInflight(el, key, href) {{
    try {{ localStorage.setItem(key, '1'); }} catch(e) {{}}
    el.outerHTML = makeInflightHtml(key);
  }}
  function initInflight() {{
    document.querySelectorAll('a.tr-act[data-uc-key]').forEach(function(el) {{
      var resolved = resolveKeyAndUrl(el);
      try {{
        if (localStorage.getItem(resolved.key)) {{ el.outerHTML = makeInflightHtml(resolved.key); return; }}
      }} catch(e) {{}}
      el.addEventListener('click', function() {{ markInflight(el, resolved.key, resolved.href); }});
    }});
  }}
  if (document.readyState === 'loading') {{
    document.addEventListener('DOMContentLoaded', initInflight);
  }} else {{
    initInflight();
  }}
}})();
</script>

</body>
</html>
"""


def generate_render_fallback(record: dict, out_dir: Path,
                             known_kds: dict[str, str] | None = None,
                             known_kd_repos: dict[str, str] | None = None) -> Path:
    """Render v2 — multi-Screen klickbares Mockup aus Spec (synthetische Daten).

    ``known_kds`` ist ein optionaler Lookup ``{kd_name: render_url}`` (Genesor-
    weit, cross-repo). Wird an ``_synth_entity_table`` durchgereicht, damit
    Akten-Zeilen automatisch zum Ziel-Fachverfahrens-KD verlinken können.
    """
    d = record["data"]
    kd_name = record["kd"]
    repo = record["repo"]
    title = (d.get("title") or kd_name).split("—")[0].strip()
    klass = d.get("class") or "?"
    role = d.get("spec_role") or "default"
    sunset = (d.get("off_ramp", {}) or {}).get("sunset_after") or "—"

    # Domain-Styling aus doc-profile.yaml
    repo_dir = _cfg.repos_root / repo
    profile = read_doc_profile(repo_dir)
    style = _DOMAIN_STYLES.get(profile) or _DOMAIN_STYLES["default"]

    # Personas
    personas_obj = d.get("personas") or {}
    if isinstance(personas_obj, dict):
        ppairs = list(personas_obj.items())
    elif isinstance(personas_obj, list):
        ppairs = []
        for p in personas_obj:
            if isinstance(p, dict) and "id" in p:
                ppairs.append((p["id"], p))
            else:
                ppairs.append((str(p), {}))
    else:
        ppairs = []

    screens = d.get("screens", []) or []
    entities = _entities_lookup(d)

    # Persona-Optionen für Dropdown
    persona_options = "\n      ".join(
        f'<option value="{html.escape(pn)}">{html.escape(pn)}</option>'
        for pn, _ in ppairs
    )

    # App-Name aus Repo (heuristisch, mit Wappen-Icon je Domain)
    app_name_map = {
        "meiki-hub": "MEiKI · LRA-Plattform",
        "ausschreibungs-hub": "Bieterpilot",
        "writing-hub": "Writing-Hub",
        "risk-hub": "Risk-Hub",
        "ttz-hub": "TTZ-Hub",
        "sqf-hub": "SQF-Hub",
        "pg-hub": "PG-Hub",
    }
    app_name = app_name_map.get(repo, repo.replace("-hub", " · Hub").title())
    app_icon = "🏛" if profile in ("public-admin", "lra-pilot") else ("🏗" if "ausschreibungs" in repo else "📋")

    # Tab-Buttons + Sidebar-Buttons + Screen-Sections
    # User-Feedback 2026-05-25: bei >5 Screens horizontales Scrollen unschön → Sidebar
    SIDEBAR_THRESHOLD = 6
    use_sidebar = len([s for s in screens if isinstance(s, dict)]) >= SIDEBAR_THRESHOLD
    body_class = "has-sidebar" if use_sidebar else "has-tabs"

    tab_buttons = []
    sidebar_groups: dict[str, list[str]] = {}    # halbschicht -> [button_html]
    sidebar_ungrouped: list[str] = []
    screen_sections = []
    for s in screens:
        if not isinstance(s, dict):
            continue
        sid = s.get("id", "?")
        stitle = s.get("title", "")
        sper = s.get("persona") or s.get("personas") or []
        if isinstance(sper, str):
            sper = [sper]
        konsumiert = s.get("konsumiert_entities") or []
        if isinstance(konsumiert, str):
            konsumiert = [konsumiert]
        lokal = s.get("lokale_entities") or []
        if isinstance(lokal, str):
            lokal = [lokal]
        fokus = s.get("fokus") or []

        # Tab + Sidebar
        per_data = ",".join(html.escape(p) for p in sper)
        tab_buttons.append(
            f'<button role="tab" aria-selected="false" '
            f'aria-controls="screen-{html.escape(sid)}" '
            f'data-screen="{html.escape(sid)}" data-personas="{per_data}">'
            f'{html.escape(str(stitle) or sid)}</button>'
        )
        # Sidebar-Button (gruppiert nach halbschicht falls vorhanden);
        # kein role=tab (aside ist keine tablist) — aktiver Zustand via aria-current
        halbschicht = s.get("halbschicht") or ""
        sidebar_btn = (
            f'<button aria-controls="screen-{html.escape(sid)}" '
            f'data-screen="{html.escape(sid)}" data-personas="{per_data}">'
            f'{html.escape(str(stitle) or sid)}'
            f'<small>{html.escape(", ".join(sper[:2]))}</small>'
            f'</button>'
        )
        if halbschicht:
            sidebar_groups.setdefault(halbschicht, []).append(sidebar_btn)
        else:
            sidebar_ungrouped.append(sidebar_btn)

        # Persona-Anzeige in App-Bar (erste Persona)
        primary_persona = sper[0] if sper else "—"

        # Per-Chips für Toolbar
        per_chips = "".join(f'<span class="persona-chip">{html.escape(p)}</span>' for p in sper)

        # Self-Service-Detection: bei Bürger-Halbschicht zeigt der Screen die
        # Sicht *eines* eingeloggten Bürgers — alle Zeilen derselben Person.
        # Verwaltungs-Halbschicht hingegen rotiert (Sachbearbeiter sieht mehrere
        # Bürger). viewer_idx=0 → erster Bürger im Pool (Sabine Müller).
        is_self_service = str(halbschicht).lower() == "buerger"
        viewer_idx = 0 if is_self_service else None
        n_rows_for_screen = 3 if is_self_service else 4

        # Entity-Panels sammeln (für Sub-Tabs oder Single-Render)
        all_ent_names = list(konsumiert) + list(lokal)
        entity_panels = []  # Liste von (ename, has_table, panel_html)
        for ename in all_ent_names[:6]:
            ent_def = entities.get(ename)
            if ent_def is not None:
                ent_desc_html = ""
                if isinstance(ent_def, dict) and ent_def.get("description"):
                    ent_desc_html = f'<p style="color:#6b7280;font-size:12px;margin:0 0 8px;">{html.escape(str(ent_def["description"])[:120])}</p>'
                table_html = _synth_entity_table(ename, ent_def, n_rows=n_rows_for_screen,
                                                 screen_id=sid, known_kds=known_kds,
                                                 known_kd_repos=known_kd_repos,
                                                 viewer_idx=viewer_idx)
                entity_panels.append((ename, True, ent_desc_html + table_html))
            else:
                stub_html = (
                    '<p style="color:#6b7280;font-size:13px;">Konsumiert von externem Klickdummy '
                    '<code>(siehe consumes_from-Block)</code>. Beispiel-Daten via integriertem Cross-KD-Render.</p>'
                )
                entity_panels.append((ename, False, stub_html))

        # Sub-Tabs (Punkt 3) — bei ≥2 Entities, sonst Single-Panel
        content_blocks = []
        if len(entity_panels) >= 2:
            sub_tab_html = '<div class="sub-tabs" role="tablist" aria-label="Entitäten">'
            sub_panels_html = ''
            for i, (ename, _has, panel) in enumerate(entity_panels):
                active = ' active' if i == 0 else ''
                aria_sel = 'true' if i == 0 else 'false'
                sub_tab_html += (
                    f'<button class="sub-tab{active}" role="tab" aria-selected="{aria_sel}" '
                    f'aria-controls="sub-{html.escape(sid)}-{i}" '
                    f'data-sub="{html.escape(sid)}-{i}">📊 {html.escape(ename)}</button>'
                )
                sub_panels_html += f'<div class="sub-panel{active}" role="tabpanel" id="sub-{html.escape(sid)}-{i}">{panel}</div>'
            sub_tab_html += '</div>'
            content_blocks.append(sub_tab_html + sub_panels_html)
        elif len(entity_panels) == 1:
            ename, _has, panel = entity_panels[0]
            content_blocks.append(
                f'<div class="card"><h3>📊 {html.escape(ename)}</h3>{panel}</div>'
            )
        # ohne Entity-Tabellen: Hinweis
        if not entity_panels:
            content_blocks.append(
                '<p style="color:#6b7280;font-size:13px;text-align:center;padding:40px;">Keine Daten-Entities für diesen Screen deklariert.</p>'
            )

        # Workflow-Buttons aus next_screens (Screen-zu-Screen-Navigation)
        next_screens = s.get("next_screens") or []
        if isinstance(next_screens, str):
            next_screens = [next_screens]
        # Map next-screen-id → next-screen-title für Button-Label
        screen_titles = {(s2.get("id") if isinstance(s2, dict) else None): (s2.get("title") if isinstance(s2, dict) else "")
                         for s2 in screens}
        workflow_buttons = []
        for nsid in next_screens[:3]:
            ntitle = screen_titles.get(nsid) or nsid
            workflow_buttons.append(
                f'<button onclick="showScreen(\'{html.escape(nsid)}\')" title="Weiter zu {html.escape(ntitle)}">'
                f'→ {html.escape(ntitle)[:30]}</button>'
            )
        if workflow_buttons:
            action_buttons = "".join(workflow_buttons) + '<button class="secondary">Speichern</button><button class="secondary">Abbrechen</button>'
        else:
            action_buttons = '<button>Speichern</button><button class="secondary">Abbrechen</button><button class="secondary">Zurück</button>'
        # Cross-KD-Links als Buttons in Actionbar
        screen_ckl = s.get("cross_klickdummy_link") if isinstance(s.get("cross_klickdummy_link"), (list, dict)) else None
        cross_links_html = []
        if screen_ckl:
            ckl_list = screen_ckl if isinstance(screen_ckl, list) else [screen_ckl]
            for entry in ckl_list:
                if isinstance(entry, dict) and entry.get("target"):
                    target = entry["target"]
                    cross_links_html.append(
                        f'<a href="#" title="Cross-KD-Link">→ {html.escape(target)}</a>'
                    )
                elif isinstance(entry, dict) and entry.get("routes"):
                    for r2 in entry["routes"]:
                        if isinstance(r2, dict):
                            cross_links_html.append(
                                f'<a href="#" title="Routing-Link">→ {html.escape(r2.get("target", "?"))}</a>'
                            )
        cross_html = ""
        if cross_links_html:
            cross_html = f'<div class="cross-links" style="margin-left:auto;">{"".join(cross_links_html)}</div>'

        # ----- ℹ Info-Modal: SPEC-Sicht (Build/Workshop) ---------------------
        fokus_modal_html = ""
        if isinstance(fokus, list) and fokus:
            fokus_items = "".join(f"<li>{html.escape(str(f))}</li>" for f in fokus)
            fokus_modal_html = f'<h4>🎯 Funktionen / Verhalten</h4><ul>{fokus_items}</ul>'
        per_list = "".join(f"<li><code>{html.escape(p)}</code></li>" for p in sper) or "<li>—</li>"
        personas_modal_html = f'<h4>👥 Personas dieses Screens</h4><ul>{per_list}</ul>'
        ent_modal_lines = []
        for ename in all_ent_names[:8]:
            ent_def = entities.get(ename)
            if isinstance(ent_def, dict):
                desc = ent_def.get("description", "")
                ent_modal_lines.append(f'<li><code>{html.escape(ename)}</code>{(" — " + html.escape(desc[:80])) if desc else ""}</li>')
            else:
                ent_modal_lines.append(f'<li><code>{html.escape(ename)}</code> <span style="color:#6b7280;">(cross-KD)</span></li>')
        ent_modal_html = f'<h4>📦 Entity-Schema</h4><ul>{"".join(ent_modal_lines)}</ul>' if ent_modal_lines else ""
        info_modal_inner = (
            '<p style="font-size:11px;color:#9ca3af;margin-top:0;">(Spec-Sicht · in Prod ggf. nicht sichtbar)</p>'
            + fokus_modal_html + personas_modal_html + ent_modal_html
        )

        # ----- ❓ Hilfe-Modal: fachliche End-User-Sicht ----------------------
        # Override via screen.help_text (Markdown-String) ODER screen.help_sections (Liste{title,content})
        # Default: Auto-Generierung aus Title/Personas/UCs/next_screens
        help_text = s.get("help_text")
        help_sections = s.get("help_sections")
        if help_text and isinstance(help_text, str):
            # Markdown-Simple-Render: line-by-line, ** → <b>, - → li
            help_lines = []
            in_list = False
            for line in help_text.strip().splitlines():
                ll = line.strip()
                if ll.startswith("- "):
                    if not in_list:
                        help_lines.append("<ul>")
                        in_list = True
                    help_lines.append(f"<li>{html.escape(ll[2:])}</li>")
                else:
                    if in_list:
                        help_lines.append("</ul>")
                        in_list = False
                    if not ll:
                        continue
                    if ll.startswith("**") and ll.endswith("**"):
                        help_lines.append(f"<h4>{html.escape(ll[2:-2])}</h4>")
                    else:
                        help_lines.append(f"<p>{html.escape(ll)}</p>")
            if in_list:
                help_lines.append("</ul>")
            help_modal_inner = "".join(help_lines)
        elif help_sections and isinstance(help_sections, list):
            parts = []
            for sec in help_sections:
                if isinstance(sec, dict):
                    t = sec.get("title", "")
                    c = sec.get("content", "")
                    parts.append(f"<h4>{html.escape(str(t))}</h4><p>{html.escape(str(c))}</p>")
            help_modal_inner = "".join(parts)
        else:
            # Default-Hilfetext aus den Spec-Feldern (heuristisch, fachlich getönt)
            default_what = (
                f'<h4>Was sehen Sie hier?</h4>'
                f'<p>{html.escape(str(stitle) or sid)} — dieser Bildschirm ist für '
                f'{html.escape(", ".join(sper) or "alle Nutzer")} gedacht.</p>'
            )
            default_actions = ""
            if isinstance(fokus, list) and fokus:
                actions = "".join(f"<li>{html.escape(str(f))}</li>" for f in fokus[:5])
                default_actions = f"<h4>Was können Sie tun?</h4><ul>{actions}</ul>"
            default_next = ""
            if next_screens:
                next_titles = [screen_titles.get(n, n) for n in next_screens[:3]]
                next_items = "".join(f"<li>{html.escape(str(t))}</li>" for t in next_titles)
                default_next = f"<h4>Folge-Schritte</h4><ul>{next_items}</ul>"
            # validierungsfrage (Spec-Feld): was dieser Screen beim Stakeholder prüfen soll
            default_check = ""
            vfrage = s.get("validierungsfrage")
            if vfrage and isinstance(vfrage, str):
                default_check = f'<h4>Diese Ansicht soll prüfen</h4><p>{html.escape(vfrage)}</p>'
            help_modal_inner = (
                '<p style="font-size:11px;color:#9ca3af;margin-top:0;">(Auto-Hilfetext aus Spec — bei Bedarf in <code>screen.help_text:</code> überschreiben)</p>'
                + default_what + default_actions + default_next + default_check
            )

        # ----- 📁 Akte-Modal: Klick auf Aktenzeichen/-name in einer Tabelle --
        # Spec-Override via screen.akte_next: {label, hint, klickdummy, uc, repo}
        # Default: generischer Hinweis "Spec-seitig noch nicht deklariert"
        akte_next = s.get("akte_next") if isinstance(s.get("akte_next"), dict) else None
        if akte_next:
            label = str(akte_next.get("label") or "Weiter zur Akte")
            hint = str(akte_next.get("hint") or "")
            target_kd = akte_next.get("klickdummy")
            target_repo = akte_next.get("repo") or repo
            uc = akte_next.get("uc")
            target_url = ""
            if target_kd:
                target_url = f"./{target_repo}-{target_kd}.html"
            parts = ['<h4>Wie es weiter ginge</h4>']
            if hint:
                parts.append(f'<p>{html.escape(hint)}</p>')
            if target_url:
                parts.append(
                    f'<p><a href="{html.escape(target_url)}" class="akte-next-cta">'
                    f'→ {html.escape(label)}</a></p>'
                )
            else:
                parts.append(
                    f'<p><span style="color:#9ca3af;">→ {html.escape(label)} '
                    f'<em>(noch nicht als Klickdummy verlinkt)</em></span></p>'
                )
            if uc:
                parts.append(
                    f'<p style="color:#6b7280;font-size:12px;">Use Case: '
                    f'<code>{html.escape(str(uc))}</code></p>'
                )
            akte_modal_inner = "".join(parts)
        else:
            akte_modal_inner = (
                '<h4>Wie es weiter ginge</h4>'
                '<p>Klick auf einen Akten-Eintrag würde im Echt-Betrieb '
                'das jeweilige Fachverfahren öffnen (z. B. Wohngeld, UVG, Asyl).</p>'
                '<p style="color:#9ca3af;font-size:12px;">'
                'Spec-seitig noch nicht deklariert. Tipp: <code>screen.akte_next: '
                '{ label, hint, klickdummy, uc }</code> ergänzen.'
                '</p>'
            )

        # Acceptance-Status pro Screen (KD-Level + Screen-Level mergen)
        accept_merged = merge_acceptance(d.get("acceptance"), s.get("acceptance"))
        accept_status = compute_acceptance_status(accept_merged)
        accept_chips = []
        for axis, info in accept_status.items():
            label = "PO-Sign-Off" if axis == "spec_signed" else "Workshop-Walk"
            if info["status"] == "signed":
                accept_chips.append(
                    f'<span class="ac-chip ac-signed" title="{html.escape(label)}: '
                    f'{html.escape(info["latest_by"] or "?")} · {info["latest_date"]} · '
                    f'ref={html.escape(info["latest_ref"] or "—")}">'
                    f'✓ {axis}</span>'
                )
            elif info["status"] == "stale":
                accept_chips.append(
                    f'<span class="ac-chip ac-stale" title="{html.escape(label)}: '
                    f'letzter Eintrag {info["age_days"]}d alt ({info["latest_date"]}) '
                    f'— Spec-Drift möglich, neue Abnahme empfohlen">'
                    f'⚠ {axis}</span>'
                )
            # "missing" wird nicht gerendert — kein Rauschen
        accept_html = "".join(accept_chips)

        # Komplette App-Frame
        # (Fallback vorab — kein Backslash-Escape im f-string-Ausdruck → Python <3.12-kompatibel)
        content_html = "".join(content_blocks) or '<p style="color:#6b7280;">Keine Inhalte im Spec deklariert.</p>'
        frame_html = (
            f'<div class="app-frame">'
            f'  <div class="app-bar">'
            f'    <div class="traffic"><span class="r"></span><span class="y"></span><span class="g"></span></div>'
            f'    <span class="app-icon">{app_icon}</span>'
            f'    <span class="app-name">{html.escape(app_name)}</span>'
            f'    <button class="info-btn" onclick="openInfoModal(\'{html.escape(sid)}\')" title="Spec-Sicht: Funktionen / Personas / Entity-Schema (Build-/Workshop-Info)">ℹ Info</button>'
            f'    <button class="help-btn" onclick="openHelpModal(\'{html.escape(sid)}\')" title="Fachliche Hilfe für diesen Screen (End-User-Sicht)">❓ Hilfe</button>'
            f'    <span class="app-user">👤 {html.escape(primary_persona)}</span>'
            f'  </div>'
            f'  <div class="app-toolbar">'
            f'    <span class="breadcrumb">Klickdummy · <b>{html.escape(kd_name)}</b></span>'
            f'    <h2>{html.escape(str(stitle) or sid)}</h2>'
            f'    <span class="sid">{html.escape(sid)}</span>'
            f'    {per_chips}'
            f'  </div>'
            f'  <div class="app-content">{content_html}</div>'
            f'  <div class="app-actionbar">'
            f'    <div class="actions">{action_buttons}</div>'
            f'    {cross_html}'
            f'  </div>'
            f'  <div class="app-statusbar">'
            f'    <span>👤 <code>{html.escape(primary_persona)}</code> · class <code>{html.escape(klass)}</code> · role <code>{html.escape(role)}</code></span>'
            f'    <span>{accept_html}Sunset <code>{html.escape(sunset)}</code></span>'
            f'  </div>'
            f'</div>'
            # Zwei versteckte Modal-Inhalte pro Screen — ℹ Info (Spec) + ❓ Hilfe (End-User)
            f'<div class="screen-info" hidden id="info-{html.escape(sid)}">'
            f'<div class="info-title">ℹ Spec-Info · {html.escape(str(stitle) or sid)} <code style="font-size:11px;font-weight:normal;color:#6b7280;">({html.escape(sid)})</code></div>'
            f'<div class="info-content">{info_modal_inner}</div>'
            f'</div>'
            f'<div class="screen-help" hidden id="help-{html.escape(sid)}">'
            f'<div class="info-title">❓ Hilfe · {html.escape(str(stitle) or sid)}</div>'
            f'<div class="info-content">{help_modal_inner}</div>'
            f'</div>'
            f'<div class="screen-akte" hidden id="akte-{html.escape(sid)}">'
            f'<div class="info-content">{akte_modal_inner}</div>'
            f'</div>'
        )

        # Spec-Layer (X-Ray): kompakter, spec-abgeleiteter Trace-Strip pro Screen
        trace_html = build_trace_strip(s, klass, role, accept_status, repo=repo, kd_name=kd_name, sid=sid)

        screen_sections.append(
            f'<section class="screen" id="screen-{html.escape(sid)}" data-personas="{per_data}">'
            f'{frame_html}{trace_html}</section>'
        )

    # Spec-Pfad
    spec_rel = ""
    try:
        spec_rel = str(record["path"].relative_to(_cfg.repos_root))
    except (ValueError, KeyError):
        pass

    # Custom-CSS-Hook (Punkt 1 aus User-Feedback): app_skin.custom_css aus Spec ODER
    # aus FV-Inventur (replaces_system_ref → fv.custom_css), zusätzliches Stylesheet.
    # Initial-Skin wird als INITIAL_SKIN-JS-Variable für Style-Switcher bereitgestellt;
    # Switcher lädt das CSS dynamisch (link[data-skin=1]), Spec-link nur als Marker-Hinweis.
    custom_css_link = ""
    initial_skin = "__greenfield"
    app_skin = d.get("app_skin") or {}
    if isinstance(app_skin, dict):
        css_path = app_skin.get("custom_css")
        if css_path:
            # Relativ zum Repo → URL über repo-Pfad
            css_full = (repo_dir / css_path).resolve() if not str(css_path).startswith("/") else Path(str(css_path))
            css_url = url_for_path(css_full) if css_full.is_file() else None
            if css_url:
                # In Skin-Library suchen (zentraler Pfad bevorzugt für Cross-Render-Konsistenz)
                lib_url = None
                fname = Path(css_path).name
                for lib_value, _ in skin_library():
                    if lib_value.endswith("/" + fname):
                        lib_url = lib_value
                        break
                # Initial-Skin = zentraler Pfad falls in Library, sonst spec-pfad
                initial_skin = lib_url or css_url
                custom_css_link = f"<!-- Skin via Switcher (initial: {html.escape(initial_skin)}) -->"
            else:
                custom_css_link = f"<!-- custom_css '{html.escape(str(css_path))}' nicht erreichbar — ignoriert -->"

    skin_switcher = build_skin_switcher_html(initial_skin)

    # Sidebar-Content aggregieren (gruppiert nach halbschicht; ungrouped als "Alle")
    halbschicht_labels = {
        "buerger": "👤 Bürger-Halbschicht",
        "verwaltung": "🏛 Verwaltungs-Halbschicht",
        "bieter_intern": "🏗 Baubüro intern",
        "bieter": "🏗 Bieter",
        "auftraggeber": "🤝 Auftraggeber",
        "extern": "🌐 Externe",
    }
    sidebar_blocks = []
    for hs in sorted(sidebar_groups.keys()):
        label = halbschicht_labels.get(hs, hs.replace("_", " ").title())
        sidebar_blocks.append(f"<h3>{html.escape(label)}</h3>")
        sidebar_blocks.extend(sidebar_groups[hs])
    if sidebar_ungrouped:
        if sidebar_blocks:
            sidebar_blocks.append("<h3>weitere</h3>")
        sidebar_blocks.extend(sidebar_ungrouped)
    sidebar_content = "\n    ".join(sidebar_blocks) or '<p style="color:#9ca3af;padding:16px;font-size:12px;">(keine Screens)</p>'

    html_out = RENDER_FALLBACK_TEMPLATE.format(
        kd_name=html.escape(kd_name),
        title=html.escape(title),
        repo=html.escape(repo),
        klass=html.escape(klass),
        role=html.escape(role),
        sunset=html.escape(sunset),
        persona_options=persona_options or '<option disabled>(keine Personas)</option>',
        tab_buttons="\n  ".join(tab_buttons) or '<button class="active">(kein Screen)</button>',
        sidebar_content=sidebar_content,
        body_class=body_class,
        screen_sections="\n  ".join(screen_sections) or '<section class="screen active"><div class="empty-state"><p>Keine Screens in der Spec.</p></div></section>',
        spec_rel=html.escape(spec_rel),
        style_accent=style["accent"],
        style_accent_bg=style["accent_bg"],
        style_font_h=style["font_h"],
        custom_css_link=custom_css_link,
        skin_switcher_html=skin_switcher,
        initial_skin=html.escape(initial_skin),
        feedback_repo=html.escape(f"{detect_org(repo)}/{repo}"),
    )
    # JS-Inject (nach .format(), damit JS-{}-Klammern nicht als Format-Placeholder interpretiert werden)
    html_out = html_out.replace("__SKIN_SWITCHER_JS_PLACEHOLDER__", SKIN_SWITCHER_JS)
    html_out = html_out.replace("__FEEDBACK_WIDGET_JS_PLACEHOLDER__", FEEDBACK_WIDGET_JS)
    html_out = html_out.replace("__STORY_BANNER_JS_PLACEHOLDER__", STORY_BANNER_JS)
    render_dir = out_dir / "render"
    render_dir.mkdir(parents=True, exist_ok=True)
    out_path = render_dir / f"{repo}-{kd_name}.html"
    out_path.write_text(html_out, encoding="utf-8")
    return out_path


# ---- Org-Detection (Heuristik; später aus platform/registry) --------------


# ---- Spec-Discovery + Parsing ----------------------------------------------


# ---- Mermaid-Generierung ----------------------------------------------------


# ---- HTML-Wrapper mit Feedback-Widget --------------------------------------

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="de">
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Klickdummy-Lineage — meiki-hub (auto-generated)</title>
<style>
  body {{ font-family: -apple-system, system-ui, sans-serif; margin: 0; color: #222; background: #fafafa; }}
  header {{ padding: 14px 24px; background: #fff; border-bottom: 1px solid #e0e0e0; display: flex; justify-content: space-between; align-items: center; }}
  header h1 {{ margin: 0; font-size: 18px; font-weight: 600; }}
  header .meta {{ color: #888; font-size: 13px; }}
  main {{ padding: 20px 24px; }}
  .legend {{ background: #fff; border: 1px solid #e0e0e0; border-radius: 6px; padding: 12px 16px; margin-bottom: 16px; font-size: 13px; }}
  .legend code {{ background: #f0f0f0; padding: 1px 6px; border-radius: 3px; font-size: 12px; }}
  .legend table {{ border-collapse: collapse; width: 100%; }}
  .legend td {{ padding: 3px 8px; vertical-align: top; }}
  .legend td:first-child {{ width: 130px; white-space: nowrap; }}
  .graph-wrap {{ background: #fff; border: 1px solid #e0e0e0; border-radius: 6px; padding: 16px; overflow-x: auto; }}
  .stats {{ font-size: 13px; color: #666; margin-top: 8px; }}

  /* Feedback-Widget — A-light (download submit), per platform:ADR-211 Rev 13 §Co-Creation */
  .fb {{ position: fixed; bottom: 16px; right: 16px; width: 320px; background: #fff; border: 1px solid #06c; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,.12); font-size: 13px; }}
  .fb-head {{ background: #06c; color: #fff; padding: 8px 12px; border-radius: 8px 8px 0 0; cursor: pointer; display: flex; justify-content: space-between; }}
  .fb-body {{ padding: 12px; }}
  .fb-body.hidden {{ display: none; }}
  .fb label {{ display: block; margin: 6px 0 2px; font-size: 12px; color: #555; }}
  .fb select, .fb textarea, .fb input {{ width: 100%; box-sizing: border-box; padding: 4px 6px; border: 1px solid #ccc; border-radius: 4px; font-size: 13px; font-family: inherit; }}
  .fb textarea {{ height: 60px; resize: vertical; }}
  .fb .row {{ display: flex; gap: 6px; margin-top: 8px; }}
  .fb button {{ padding: 6px 10px; border: 1px solid #06c; background: #06c; color: #fff; border-radius: 4px; cursor: pointer; font-size: 13px; }}
  .fb button.secondary {{ background: #fff; color: #06c; }}
  .fb .status {{ margin-top: 6px; font-size: 12px; color: #060; }}
</style>
<script src="https://cdn.jsdelivr.net/npm/mermaid@10.9.1/dist/mermaid.min.js"></script>
</head>
<body>

<header>
  <h1>🌐 Klickdummy-Lineage · meiki-hub</h1>
  <span class="meta">{stats_inline} · auto-generated {date}</span>
</header>

<main>

<div class="legend">
  <table>
    <tr><td><b>spec_role: root</b></td><td>blau · exponiert <code>root_entities</code>, kein <code>consumes_from</code></td></tr>
    <tr><td><b>spec_role: hybrid</b></td><td>orange · konsumiert + exponiert (siehe platform:ADR-211 Rev 14 Finding #4)</td></tr>
    <tr><td><b>📜 Contract</b></td><td>magenta · zentraler Vertrag (provides/accepts), siehe Rev 14 Finding #6</td></tr>
    <tr><td><b>─→ solid</b></td><td><code>consumes_from</code> (Schema-Import, Drift-relevant)</td></tr>
    <tr><td><b>-.→ dashed</b></td><td><code>provides_contracts</code> / <code>accepts_contracts</code></td></tr>
    <tr><td><b>-..→ dotted</b></td><td><code>cross_klickdummy_link</code> (UX-Navigation, orthogonal, Rev 14 Finding #5)</td></tr>
  </table>
</div>

<div class="graph-wrap">
<pre class="mermaid">
{mermaid}
</pre>
<div class="stats">{stats_full}</div>
</div>

</main>

<!-- Feedback-Widget · A-light (download submit) -->
<div class="fb" id="fb-widget">
  <div class="fb-head" onclick="document.getElementById('fb-body').classList.toggle('hidden')">
    <span>💬 Feedback zur Lineage-Sicht</span>
    <span>▾</span>
  </div>
  <div class="fb-body" id="fb-body">
    <label>Scope <small>(Rev-12-Pflicht 6: <code>feedback_scope</code>)</small></label>
    <select id="fb-scope">
      <option value="klickdummy-tool">Auf die Lineage-Sicht selbst (Viewer-Bug, Layout, ...)</option>
      <option value="app">Auf einen Klickdummy im Graphen (Topologie, Beziehung, Naming, ...)</option>
    </select>

    <label>Kategorie</label>
    <select id="fb-cat">
      <option value="topology-error">Topologie falsch / Beziehung fehlt</option>
      <option value="naming">Bezeichnung ungenau / Klasse falsch</option>
      <option value="missing-link">cross_klickdummy_link fehlt</option>
      <option value="contract-drift">Contract-Mapping driftet</option>
      <option value="viewer-bug">Viewer-Bug (Rendering, Layout)</option>
      <option value="idea">Idee / Vorschlag</option>
    </select>

    <label>Acceptance</label>
    <select id="fb-verdict">
      <option value="">— wählen —</option>
      <option value="accepted">✓ Accepted</option>
      <option value="needs-change">✎ Needs-Change</option>
      <option value="rejected">✗ Rejected</option>
    </select>

    <label>Betroffener KD <small>(nur bei Scope „app")</small></label>
    <select id="fb-kd">
      <option value="">— alle / kein spezifischer —</option>
      {kd_options}
    </select>

    <label>Beschreibung</label>
    <textarea id="fb-text" placeholder="Was ist Dir aufgefallen? Was sollte anders sein?"></textarea>

    <div class="row">
      <button onclick="fbDownload()">📥 Download JSON</button>
      <button class="secondary" onclick="fbClipboard()">📋 In Clipboard</button>
    </div>
    <div class="status" id="fb-status"></div>
  </div>
</div>
<span id="fb-current-subtab" style="display:none"></span>

<script>
  // Mermaid render
  mermaid.initialize({{ startOnLoad: true, theme: 'default', flowchart: {{ curve: 'basis' }} }});

  // KD-Lookup-Tabelle für Feedback
  window.KLICKDUMMY_SPEC = {{ id: "lineage", version: "0.1", klickdummy_class: "mock" }};
  window.KLICKDUMMY_FEEDBACK_REPO = "achimdehnert/meiki-hub";

  function fbCollect() {{
    return {{
      spec_id: window.KLICKDUMMY_SPEC.id,
      spec_version: window.KLICKDUMMY_SPEC.version,
      klickdummy_class: window.KLICKDUMMY_SPEC.klickdummy_class,
      feedback_scope: document.getElementById('fb-scope').value,
      acceptance_verdict: document.getElementById('fb-verdict')?.value || null,
      active_subtab: (document.getElementById('fb-current-subtab')?.textContent || null) || null,
      kategorie: document.getElementById('fb-cat').value,
      betroffener_kd: document.getElementById('fb-kd').value || null,
      text: document.getElementById('fb-text').value,
      ts: new Date().toISOString(),
      generated_from: document.title,
      conforms_to: "platform:ADR-211 Rev 13 §Co-Creation-Loop Pfad A-light"
    }};
  }}

  function fbDownload() {{
    const payload = fbCollect();
    const blob = new Blob([JSON.stringify(payload, null, 2)], {{ type: 'application/json' }});
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `feedback-lineage-${{Date.now()}}.json`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
    document.getElementById('fb-status').textContent = "✓ JSON heruntergeladen. Manuell als Issue mit Label `klickdummy-feedback` anlegen.";
  }}

  async function fbClipboard() {{
    const payload = fbCollect();
    await navigator.clipboard.writeText(JSON.stringify(payload, null, 2));
    document.getElementById('fb-status').textContent = "✓ Im Clipboard.";
  }}
</script>

</body>
</html>
"""


def build_html(mermaid_text: str, specs: list[tuple[str, Path, dict]], contracts: dict) -> str:
    from datetime import date
    kd_options = "\n      ".join(
        f'<option value="{html.escape(kd_name)}">{html.escape(kd_name)}</option>'
        for kd_name, _p, _d in specs
    )
    n_kd = len(specs)
    n_root = sum(1 for _, _, d in specs if d.get("spec_role") == "root")
    n_hybrid = sum(1 for _, _, d in specs if d.get("spec_role") == "hybrid")
    n_default = n_kd - n_root - n_hybrid
    n_contracts = len(contracts)
    n_consumes = sum(len(d.get("consumes_from") or []) for _, _, d in specs)
    n_provides = sum(len(d.get("provides_contracts") or []) for _, _, d in specs)
    stats_inline = f"{n_kd} KDs · {n_contracts} Contracts · {n_consumes} consumes-Refs · {n_provides} provides"
    stats_full = (
        f"Statistik: {n_kd} Klickdummies "
        f"(root: {n_root}, hybrid: {n_hybrid}, default: {n_default}) · "
        f"{n_contracts} Cross-cutting Contracts · "
        f"{n_consumes} consumes_from-Einträge · "
        f"{n_provides} provides_contracts-Einträge"
    )
    return HTML_TEMPLATE.format(
        mermaid=mermaid_text,
        kd_options=kd_options,
        date=date.today().isoformat(),
        stats_inline=stats_inline,
        stats_full=stats_full,
    )


# ---- Cross-Repo-Walker (IIL-Genesor Stufe 1a + 1b) -------------------------



# ---- Drift-Validierung (F3) ------------------------------------------------


def build_genesor_html(records: list[dict],
                      uc_coverage: dict | None = None,
                      n_ucs: int = 0) -> str:
    """Cross-Repo Übersichts-HTML — klickbare Tabelle mit Detail-Panel pro KD.

    Optional: UC-Coverage-Summary in der Topbar + Link zu coverage.html
    (ADR-211 Rev 15 §UC-Coverage).
    """
    from datetime import date
    from collections import defaultdict

    # KD-ADR-Registry für Dangling-Ref-Check (F3)
    kd_registry = build_kd_registry(records)

    # Pro KD Warnings berechnen + Total-Counts
    all_warnings: dict[int, list[dict]] = {}
    n_errors = 0
    n_warns = 0
    for idx, r in enumerate(records):
        warns = validate_kd(r, kd_registry)
        all_warnings[idx] = warns
        n_errors += sum(1 for w in warns if w["severity"] == "error")
        n_warns += sum(1 for w in warns if w["severity"] == "warning")

    # Statistik
    n_kds = len(records)
    n_orgs = len({r["org"] for r in records})
    n_repos = len({(r["org"], r["repo"]) for r in records})
    classes = defaultdict(int)
    for r in records:
        classes[(r["data"].get("class") or "?")] += 1
    n_root = sum(1 for r in records if r["data"].get("spec_role") == "root")
    n_hybrid = sum(1 for r in records if r["data"].get("spec_role") == "hybrid")
    n_render_only = sum(1 for r in records if r.get("kind", "spec") != "spec")

    # Drift-Daten pro KD (Pilot-Memo 2026-05-26 — stabile Basis gegen Drift)
    drift_by_idx: dict[int, dict] = {}
    drift_counter = defaultdict(int)
    for idx, r in enumerate(records):
        drift_by_idx[idx] = _compute_drift_status(r)
        drift_counter[drift_by_idx[idx]["status"]] += 1
    n_pilot_kds = sum(1 for d in drift_by_idx.values() if d["n_expected_briefs"] > 0)
    n_briefs_total = sum(d["n_actual_briefs"] for d in drift_by_idx.values())
    n_briefs_expected = sum(d["n_expected_briefs"] for d in drift_by_idx.values())

    # Surface-Index aus iil-relaunch/apps.json (Pilot-Memo §Surface-Switcher)
    apps_index = _load_iil_apps_index()
    n_apps_indexed = len(apps_index)
    # Rev-15-Stats: UCs + Ablösungen
    n_ucs_total = sum(
        len(r.get("adr_meta", {}).get("realizes_use_cases") or [])
        for r in records
    )
    n_replaces = sum(
        1 for r in records
        if (r.get("adr_meta", {}) or {}).get("replaces_system_ref")
    )

    # Gruppieren nach Org → Repo
    by_org: dict[str, dict[str, list[dict]]] = defaultdict(lambda: defaultdict(list))
    for r in records:
        by_org[r["org"]][r["repo"]].append(r)

    org_chip = lambda o: f'<span class="org-chip org-{html.escape(o)}">{html.escape(o)}</span>'
    role_chip = lambda r: (
        f'<span class="role-{r}">{r}</span>' if r in {"root", "hybrid"}
        else '<span class="role-default">—</span>'
    )

    # ---- Detail-Panel-Renderer ----
    def render_detail(r: dict, idx: int) -> str:
        d = r["data"]
        warnings = all_warnings.get(idx, [])

        # Warnings-Block oben im Panel (F3/F4-Output)
        warn_html = ""
        if warnings:
            items = []
            for w in warnings:
                sev_class = "warn-error" if w["severity"] == "error" else "warn-warning"
                icon = "❌" if w["severity"] == "error" else "⚠"
                items.append(f'<li class="{sev_class}">{icon} <b>{w["code"]}</b> · {html.escape(w["msg"])}</li>')
            warn_html = f'<div class="warnings"><h4>Drift-Validierung ({len(warnings)})</h4><ul class="compact">{"".join(items)}</ul></div>'

        # F11 — Render-only-KDs: anderes Detail (kein Spec)
        if r.get("kind", "spec") != "spec":
            html_files = d.get("_html_files") or [d.get("_html_file")]
            html_files_str = ", ".join(f'<code>{html.escape(f)}</code>' for f in html_files if f)
            rel_path = ""
            try:
                rel_path = str(r["path"].relative_to(_cfg.repos_root))
            except (ValueError, KeyError):
                rel_path = str(r.get("path", "?"))
            # Mockup-URL: für render-only-inline ist der Pfad direkt der HTML, sonst gibt's mehrere
            if r["kind"] == "render-only-inline":
                mockup_url = url_for_path(r["path"])
                mockup_link = (
                    f'<div class="mockup-link"><a href="{mockup_url}" target="_blank">'
                    f'📱 → {html.escape(r["path"].name)} öffnen</a></div>'
                ) if mockup_url else ""
            else:
                # Subdir mit HTMLs — erste finden
                mh = find_mockup_html(r["path"].parent, r["kd"])
                mockup_link = (
                    f'<div class="mockup-link"><a href="{url_for_path(mh)}" target="_blank">'
                    f'📱 → {html.escape(mh.name)} öffnen</a></div>'
                ) if mh else ""
            return f"""
    <tr class="detail-row" id="detail-{idx}">
      <td colspan="13" class="detail-cell">
        {warn_html}
        <div class="muted">Render-only-KD (kein <code>screens-spec.yaml</code>) — gemäß <code>platform:ADR-211</code> I1 nicht konform.</div>
        <div class="small muted">HTML-Dateien: {html_files_str or "—"}</div>
        {mockup_link}
        <div class="spec-path small muted">Pfad: <code>~/github/{html.escape(rel_path)}</code></div>
      </td>
    </tr>"""

        # Personas
        personas_obj = d.get("personas") or {}
        if isinstance(personas_obj, dict):
            ppairs = personas_obj.items()
        elif isinstance(personas_obj, list):
            ppairs = []
            for p in personas_obj:
                if isinstance(p, dict) and "id" in p:
                    ppairs.append((p["id"], p))
                else:
                    ppairs.append((str(p), {}))
        else:
            ppairs = []
        persona_items = []
        for pname, pdata in ppairs:
            desc = pdata.get("description", "") if isinstance(pdata, dict) else ""
            rechte = pdata.get("rechte", []) if isinstance(pdata, dict) else []
            persona_items.append(
                f'<li><b>{html.escape(pname)}</b>'
                + (f' <span class="muted">— {html.escape(desc)}</span>' if desc else '')
                + (f'<br/><span class="small muted">Rechte: {html.escape(", ".join(rechte))}</span>' if rechte else '')
                + '</li>'
            )
        personas_html = f'<ul class="compact">{"".join(persona_items)}</ul>' if persona_items else '<span class="muted">—</span>'

        # Screens
        screens = d.get("screens", []) or []
        screen_items = []
        for s in screens:
            if not isinstance(s, dict):
                continue
            sid = s.get("id", "?")
            stitle = s.get("title", "")
            sper = s.get("persona") or s.get("personas") or []
            if isinstance(sper, str):
                sper = [sper]
            sper_str = ", ".join(sper) if sper else "—"
            screen_items.append(
                f'<li><code>{html.escape(sid)}</code> <b>{html.escape(str(stitle))}</b>'
                + f'<br/><span class="small muted">Personas: {html.escape(sper_str)}</span></li>'
            )
        screens_html = f'<ul class="compact">{"".join(screen_items)}</ul>' if screen_items else '<span class="muted">—</span>'

        # Beziehungen
        rel_lines = []
        cf = d.get("consumes_from") or []
        if cf:
            for entry in cf:
                ref = entry.get("ref", "?") if isinstance(entry, dict) else str(entry)
                entities = entry.get("entities", []) if isinstance(entry, dict) else []
                rel_lines.append(f'<li><span class="rel-tag rel-cf">consumes_from</span> <code>{html.escape(ref)}</code> ({len(entities)} entities)</li>')
        pc = d.get("provides_contracts") or []
        if pc:
            for entry in pc:
                cid = entry.get("schema_ref") or entry.get("id", "?")
                rel_lines.append(f'<li><span class="rel-tag rel-pc">provides_contracts</span> <code>{html.escape(cid)}</code></li>')
        ac = d.get("accepts_contracts") or []
        if ac:
            for entry in ac:
                cid = entry.get("schema_ref") or entry.get("id", "?")
                rel_lines.append(f'<li><span class="rel-tag rel-ac">accepts_contracts</span> <code>{html.escape(cid)}</code></li>')
        re_root = d.get("root_entities") or {}
        if re_root:
            n = len(re_root) if isinstance(re_root, dict) else len(list(re_root))
            rel_lines.append(f'<li><span class="rel-tag rel-rt">root_entities</span> {n} exponiert</li>')
        rel_html = f'<ul class="compact">{"".join(rel_lines)}</ul>' if rel_lines else '<span class="muted">standalone — keine Cross-KD-Beziehungen</span>'

        # Spec-Pfad + Mermaid-Detail-Link (wenn vorhanden)
        rel_path = ""
        try:
            rel_path = str(r["path"].relative_to(_cfg.repos_root))
        except (ValueError, KeyError):
            rel_path = str(r.get("path", "?"))

        # Per-Repo-Mermaid-Lineage (Stufe 1b, F12: nur wenn ≥2 KDs im Repo)
        repo_kd_count = sum(1 for x in records if x["repo"] == r["repo"] and x.get("kind", "spec") == "spec")
        if repo_kd_count >= 2:
            lineage_link = (
                '<div class="lineage-link">'
                f'🌐 Topologie für <code>{html.escape(r["repo"])}</code>: '
                f'<a href="lineage-{html.escape(r["repo"])}.html" target="_blank">→ Mermaid-Lineage öffnen</a>'
                '</div>'
            )
        else:
            lineage_link = (
                '<div class="lineage-link muted small">'
                f'ℹ Nur 1 KD in <code>{html.escape(r["repo"])}</code> — kein eigener Mermaid-Graph generiert.'
                '</div>'
            )

        # Mockup-HTML (Stufe 1b: "Klickdummy klickbar")
        mockup_html_path = find_mockup_html(r["path"].parent, r["kd"])
        if mockup_html_path:
            mockup_url = url_for_path(mockup_html_path)
            mockup_link = (
                '<div class="mockup-link">'
                f'📱 Klickdummy-Mockup: '
                f'<a href="{mockup_url}" target="_blank">→ {html.escape(mockup_html_path.name)} öffnen</a>'
                f' <span class="small muted">(echter klickbarer HTML-Render)</span>'
                '</div>'
            ) if mockup_url else ""
        else:
            # Render-Fallback: aus Spec generierte minimal-klickbare HTML
            mockup_link = (
                '<div class="mockup-link">'
                f'🔬 Auto-Render aus Spec: '
                f'<a href="/genesor/render/{html.escape(r["repo"])}-{html.escape(r["kd"])}.html" target="_blank">→ Spec-Render öffnen</a>'
                f' <span class="small muted">(klickbar — Persona-Filter, kein eigenes Design)</span>'
                '</div>'
            )

        # Grounding-Info
        g = d.get("grounding", {}) or {}
        ground_lines = []
        for k in ("domain", "achse", "pilot_stakeholder", "pilot_lra", "konzept_ref", "prozessmodell"):
            if k in g:
                v = g[k]
                v_str = ", ".join(v) if isinstance(v, list) else str(v)
                ground_lines.append(f'<li><b>{k}:</b> {html.escape(v_str[:120])}</li>')
        ground_html = f'<ul class="compact">{"".join(ground_lines)}</ul>' if ground_lines else ""

        # Use-Cases-Section + Replaces-Section (Rev-15-Vorgriff)
        adr_meta = r.get("adr_meta") or {}
        ucs_list = adr_meta.get("realizes_use_cases") or []
        replaces_ref = adr_meta.get("replaces_system_ref")
        ucs_html = ""
        # Link auf UC-Repo-Index mit Filter (Workshop 2026-05-26 #2)
        kd_filter_url = f'./uc-{html.escape(r["repo"])}.html?kd={html.escape(r["kd"])}'
        if ucs_list:
            uc_items = "".join(f"<li><code>{html.escape(uc)}</code></li>" for uc in ucs_list)
            ucs_html = (
                f'<h4>📋 Realisiert Use Cases ({len(ucs_list)}) '
                f'<a href="{kd_filter_url}" style="font-size:12px;font-weight:normal;color:#06c;">→ alle UCs für diesen KD</a></h4>'
                f'<ul class="compact">{uc_items}</ul>'
            )
        elif r.get("kind", "spec") == "spec":
            ucs_html = (
                f'<h4>📋 Use Cases</h4>'
                f'<span class="muted small">— keine <code>realizes_use_cases:</code> im ADR-Frontmatter · </span>'
                f'<a href="{kd_filter_url}" style="font-size:13px;color:#06c;">'
                f'→ UC-Liste für diesen KD öffnen</a>'
                f'<div class="muted small" style="margin-top:4px;">'
                f'(Per-Discovery-UCs werden auf der UC-Index-Page gezeigt, gefiltert nach diesem KD)'
                f'</div>'
            )
        replaces_html = ""
        if replaces_ref:
            replaces_html = f'<h4 style="margin-top:8px;">🔄 Löst ab</h4><code>{html.escape(replaces_ref)}</code> <span class="small muted">(siehe docs/inventur/fv-inventur.yaml)</span>'

        return f"""
    <tr class="detail-row" id="detail-{idx}">
      <td colspan="13" class="detail-cell">
        {warn_html}
        <div class="detail-grid">
          <div>
            <h4>👥 Personas ({len(persona_items)})</h4>
            {personas_html}
          </div>
          <div>
            <h4>🖼 Screens ({len(screens)})</h4>
            {screens_html}
          </div>
          <div>
            <h4>🔗 Beziehungen</h4>
            {rel_html}
            {ucs_html}
            {replaces_html}
            {('<h4 style="margin-top:12px;">📌 Grounding</h4>' + ground_html) if ground_html else ''}
          </div>
        </div>
        {mockup_link}
        {lineage_link}
        <div class="spec-path small muted">Spec: <code>~/github/{html.escape(rel_path)}</code></div>
      </td>
    </tr>"""

    rows: list[str] = []
    # idx muss konsistent zu den all_warnings-Keys sein (Reihenfolge wie records)
    by_record_idx = {id(r): i for i, r in enumerate(records)}
    iter_idx = 0
    for org in sorted(by_org):
        for repo in sorted(by_org[org]):
            kd_records = sorted(by_org[org][repo], key=lambda r: r["kd"])
            for r in kd_records:
                d = r["data"]
                idx = by_record_idx[id(r)]   # echter Index für warnings-Lookup
                is_render_only = r.get("kind", "spec") != "spec"

                if is_render_only:
                    title = "render-only (Spec fehlt)"
                    klass = "—"
                    role = "default"
                    sunset_cell_class, sunset_cell_text = "sunset-na", "—"
                    n_screens = 0
                    personas = "—"
                    kunde = kunde_from(d, org)
                else:
                    title = (d.get("title") or r["kd"]).split("—")[0].strip()[:55]
                    klass = d.get("class") or "?"
                    role = d.get("spec_role") or "default"
                    sunset_cell_class, sunset_cell_text = compute_sunset_badge(d)
                    n_screens = len(d.get("screens", []) or [])
                    personas_obj = d.get("personas") or {}
                    if isinstance(personas_obj, dict):
                        personas_list = list(personas_obj.keys())
                    elif isinstance(personas_obj, list):
                        personas_list = [p.get("id", str(p)) if isinstance(p, dict) else str(p) for p in personas_obj]
                    else:
                        personas_list = []
                    personas = ", ".join(personas_list[:3])
                    if len(personas_list) > 3:
                        personas += f" +{len(personas_list)-3}"
                    personas = personas or "—"
                    kunde = kunde_from(d, org)

                # Warning-Badge in der ersten Zelle
                warns_for_kd = all_warnings.get(idx, [])
                n_err = sum(1 for w in warns_for_kd if w["severity"] == "error")
                n_w = sum(1 for w in warns_for_kd if w["severity"] == "warning")
                badge = ""
                if n_err:
                    badge = f'<span class="warn-badge warn-error" title="{n_err} Errors">❌{n_err}</span>'
                elif n_w:
                    badge = f'<span class="warn-badge warn-warning" title="{n_w} Warnings">⚠{n_w}</span>'

                # Rev-15-Spalten: UCs + Replaces
                adr_meta = r.get("adr_meta") or {}
                ucs_list = adr_meta.get("realizes_use_cases") or []
                n_kd_ucs = len(ucs_list) if isinstance(ucs_list, list) else 0
                ucs_cell = (
                    f'<a href="./uc-{html.escape(r["repo"])}.html" style="color:#06c;font-weight:600;text-decoration:none;" title="Alle UCs in {html.escape(r["repo"])}">{n_kd_ucs}</a>'
                    if n_kd_ucs else
                    f'<a href="./uc-{html.escape(r["repo"])}.html" style="color:#999;text-decoration:none;" title="UC-Liste für {html.escape(r["repo"])} (leer für diesen KD)">—</a>'
                )
                replaces_ref = adr_meta.get("replaces_system_ref")
                replaces_cell = f'<code>{html.escape(replaces_ref)}</code>' if replaces_ref else '<span class="muted">—</span>'

                org_cell = org_chip(org)
                repo_cell = f'<code>{html.escape(repo)}</code>'

                # Surface-Switcher: KD / Dev / Staging / Stable (Pilot-Memo §Surface)
                app_info = apps_index.get(repo, {})
                surface_urls = app_info.get("urls", {})
                # KD-Spec ist immer da — entweder Mockup-HTML oder Auto-Render
                kd_mockup = find_mockup_html(r["path"].parent, r["kd"])
                kd_url = url_for_path(kd_mockup) if kd_mockup else (
                    f"/genesor/render/{html.escape(r['repo'])}-{html.escape(r['kd'])}.html"
                )
                # Sichtbarer Flag: KD ohne echtes Mockup-HTML → nur Spec-Render.
                mockup_missing_badge = (
                    '<span class="warn-badge warn-warning mockup-missing" '
                    'title="Kein echtes Mockup-HTML im KD-Verzeichnis — Link zeigt auf den '
                    'aus der Spec generierten Auto-Render.">⚠ Mockup fehlt · nur Spec-Render</span> '
                    if kd_mockup is None else ""
                )
                # Feature B: "🛠 Mockup generieren" — nur wenn kein echtes Mockup existiert.
                # Verlinkt auf ein vorausgefülltes GitHub-Issue (labels=klickdummy,auto).
                mockup_generate_btn = ""
                if kd_mockup is None:
                    from urllib.parse import quote as _quote
                    _issue_title = f'[klickdummy] {r["kd"]} bauen'
                    # Idempotenz-Schlüssel (KONZ-iil-klickdummy-001, Teil A): identisch zum
                    # Sentinel von klickdummy_sync.py (find_existing_issue) — so erkennt der Sync
                    # button-erzeugte Issues und legt keine Dublette an / kann sie rekonziliieren.
                    _issue_body = (
                        f'Mockup für {repo}:{r["kd"]} bauen gemäß ADR-211, '
                        f'angefordert über genesor.\n\n'
                        f'<!-- klickdummy-sync:{r["kd"]} -->'
                    )
                    _issue_url = (
                        f'https://github.com/{detect_org(repo)}/{repo}/issues/new'
                        f'?title={_quote(_issue_title)}'
                        f'&labels=klickdummy,auto'
                        f'&body={_quote(_issue_body)}'
                    )
                    mockup_generate_btn = (
                        f'<a class="mockup-gen-btn" href="{html.escape(_issue_url, quote=True)}" '
                        f'target="_blank" rel="noopener" '
                        f'title="GitHub-Issue zum Bau dieses Mockups vorausfüllen (labels=klickdummy,auto)" '
                        f'onclick="event.stopPropagation(); mockupGenStart(this);">'
                        f'🛠 Mockup generieren</a> '
                    )

                # Screen×Surface-Matrix als JSON-Datenstruktur fürs Modal
                screen_routes = _extract_screen_routes(r)
                import json as _json
                modal_payload = _json.dumps({
                    "repo": repo,
                    "kd": r["kd"],
                    "kd_title": title,
                    "kd_url": kd_url,
                    "surface_base": {
                        "dev": surface_urls.get("dev"),
                        "staging": surface_urls.get("staging"),
                        "prod": surface_urls.get("prod"),
                    },
                    "screens": screen_routes,
                }, ensure_ascii=False)

                surfaces = [
                    ("kd",      "📋 KD",  kd_url,                       "Klickdummy-Spec / Render"),
                    ("dev",     "🛠 Dev", surface_urls.get("dev"),      "Development-Environment"),
                    ("staging", "🧪 Stg", surface_urls.get("staging"),  "Staging-Environment"),
                    ("prod",    "✅ Prod", surface_urls.get("prod"),    "Production / Stable"),
                ]
                surface_pills = []
                for code, label, url, surface_title in surfaces:
                    if url:
                        surface_pills.append(
                            f'<button class="surface-pill surface-{code} active" '
                            f'data-surface="{code}" '
                            f'title="{html.escape(surface_title)} — Modal mit Screen-Liste öffnen" '
                            f'onclick="event.stopPropagation(); openSurfaceModal(this);">'
                            f'{label}</button>'
                        )
                    else:
                        surface_pills.append(
                            f'<span class="surface-pill surface-{code} disabled" '
                            f'title="{html.escape(surface_title)}: nicht verfügbar">{label}</span>'
                        )
                # Modal-Payload als data-Attribut nur EINMAL pro Zeile
                surface_cell = (
                    f'<div class="surface-tabs" data-modal-payload="{html.escape(modal_payload, quote=True)}">'
                    + "".join(surface_pills)
                    + '</div>'
                )

                # Drift-Status-Spalte (Pilot-Memo 2026-05-26)
                d_info = drift_by_idx.get(idx, {})
                d_status = d_info.get("status", "?")
                d_label = d_info.get("status_label", "?")
                d_color = d_info.get("status_color", "#999")
                d_compare = d_info.get("compare_url")
                d_cov = d_info.get("coverage_pct", 0)
                d_expected = d_info.get("n_expected_briefs", 0)
                if d_status == "no-spec-brief":
                    drift_cell = '<span class="muted small">—</span>'
                elif d_compare:
                    drift_cell = (
                        f'<span class="drift-badge" style="background:{d_color}20;color:{d_color};" title="Brief-Coverage: {d_cov}% ({d_info.get("n_actual_briefs",0)}/{d_expected})">'
                        f'● {html.escape(d_label)}</span> '
                        f'<a href="{html.escape(d_compare)}" target="_blank" class="compare-link" '
                        f'title="Brief §10 Drift-Sektion öffnen" onclick="event.stopPropagation();">🔍</a>'
                    )
                else:
                    drift_cell = (
                        f'<span class="drift-badge" style="background:{d_color}20;color:{d_color};" '
                        f'title="{d_expected} Screen(s) mit implementation_brief, aber noch keine Briefs generiert">'
                        f'○ {html.escape(d_label)}</span>'
                    )

                rows.append(f"""
    <tr class="kd-row {'render-only' if is_render_only else ''}" data-detail-id="detail-{idx}" data-drift-status="{d_status}" data-org="{html.escape(org)}" data-repo="{html.escape(repo)}" data-class="{html.escape(klass)}" data-role="{html.escape(role)}" onclick="toggleDetail(this)">
      <td class="org-cell">{org_cell}</td>
      <td class="repo-cell">{repo_cell}</td>
      <td><span class="toggle">▸</span> {badge} <b>{html.escape(r["kd"])}</b><br/>{mockup_missing_badge}{mockup_generate_btn}<span class="muted">{html.escape(title)}</span></td>
      <td>{role_chip(role)}</td>
      <td><span class="klass-{html.escape(klass)}">{html.escape(klass)}</span></td>
      <td class="num">{n_screens}</td>
      <td class="num">{ucs_cell}</td>
      <td class="surface-cell">{surface_cell}</td>
      <td class="small">{drift_cell}</td>
      <td class="small">{replaces_cell}</td>
      <td class="small {sunset_cell_class}">{html.escape(sunset_cell_text)}</td>
      <td class="small">{html.escape(personas)}</td>
      <td class="small">{html.escape(kunde)[:40]}</td>
    </tr>""")
                rows.append(render_detail(r, idx))
                iter_idx += 1

    table_body = "".join(rows)

    # ── Feature C2: Acceptance-Matrix (ADR-211 §Acceptance) ──────────────────
    # Eine Zeile pro KD, Spalten = die zwei Achsen spec_signed/ui_walked.
    # Liest die ECHTE acceptance-Sektion aus der Spec (KD-Level). Die meisten
    # KDs haben (noch) keinen Sign-Off → Status "none" / "offen" — genau das ist
    # der Sinn: sichtbar machen, wo eine Abnahme fehlt.
    _ac_axis_labels = {"spec_signed": "PO-Sign-Off", "ui_walked": "Workshop-Walk"}
    _am_rows: list[str] = []
    _am_open_count = 0  # KDs mit mindestens einer offenen Achse
    for r in records:
        ac_status = compute_acceptance_status((r.get("data") or {}).get("acceptance"))
        cells = []
        row_has_open = False
        for axis in _ACCEPTANCE_AXES:
            info = ac_status.get(axis, {})
            st = info.get("status", "missing")
            label = _ac_axis_labels.get(axis, axis)
            if st == "signed":
                chip = (
                    f'<span class="ac-chip ac-signed" title="{html.escape(label)}: '
                    f'{html.escape(str(info.get("latest_by") or "?"))} · '
                    f'{html.escape(str(info.get("latest_date") or ""))} · '
                    f'ref={html.escape(str(info.get("latest_ref") or "—"))}">'
                    f'✓ signed</span>'
                )
            elif st == "stale":
                chip = (
                    f'<span class="ac-chip ac-stale" title="{html.escape(label)}: '
                    f'letzter Eintrag {info.get("age_days")}d alt '
                    f'({html.escape(str(info.get("latest_date") or ""))}) — '
                    f'Spec-Drift möglich, neue Abnahme empfohlen">⚠ stale</span>'
                )
                row_has_open = True
            else:
                chip = (
                    f'<span class="ac-chip ac-none" title="{html.escape(label)}: '
                    f'keine Abnahme erfasst">offen</span>'
                )
                row_has_open = True
            cells.append(f'<td>{chip}</td>')
        if row_has_open:
            _am_open_count += 1
        repo = r["repo"]
        org = r.get("org") or detect_org(repo)
        _am_rows.append(
            f'<tr>'
            f'<td class="am-label">{org_chip(org)} <code>{html.escape(repo)}</code> · '
            f'<b>{html.escape(r["kd"])}</b></td>'
            f'{"".join(cells)}'
            f'</tr>'
        )
    acceptance_matrix_section = (
        '<details class="acceptance-matrix">'
        f'<summary>✍️ Acceptance-Matrix — {_am_open_count}/{len(records)} KD(s) mit '
        'offener Abnahme (klicken zum Aufklappen)</summary>'
        '<table>'
        '<thead><tr>'
        '<th>Repo · Klickdummy</th>'
        f'<th title="ADR-211 Achse spec_signed">{_ac_axis_labels["spec_signed"]}</th>'
        f'<th title="ADR-211 Achse ui_walked">{_ac_axis_labels["ui_walked"]}</th>'
        '</tr></thead>'
        f'<tbody>{"".join(_am_rows)}</tbody>'
        '</table>'
        '</details>'
    )

    # Skin-Switcher-Optionen für die Genesor-Topbar — aus skin_library() generiert,
    # damit sie --skin-base respektieren (statt hardcodierter /iil-klickdummy/...-URLs).
    # Kurze Labels (ohne Klammer-Zusatz) wie in der bisherigen Hardcoded-Variante.
    _genesor_skin_short_labels = {
        "okwobis-look.css": "OK.Wobis-Look",
        "prosoz-look.css": "Prosoz-Look",
        "arriba-look.css": "ARRIBA-Look",
        "bayernid-look.css": "BayernID-Look",
    }
    _genesor_skin_options = []
    for _value, _label in skin_library():
        if _value == "__greenfield":
            _genesor_skin_options.append('<option value="__greenfield">Greenfield (Default)</option>')
            continue
        _short = _genesor_skin_short_labels.get(_value.rsplit("/", 1)[-1], _label)
        _genesor_skin_options.append(
            f'<option value="{html.escape(_value)}">{html.escape(_short)}</option>'
        )
    genesor_skin_options = "\n      ".join(_genesor_skin_options)

    return f"""<!DOCTYPE html>
<html lang="de">
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><text y='.9em' font-size='85'>🌱</text></svg>">
<title>IIL-Genesor — Klickdummy-Übersicht (Cross-Repo)</title>
<style>
  body {{ font-family: -apple-system, system-ui, sans-serif; margin: 0; color: #222; background: #fafafa; }}
  header {{ padding: 14px 24px; background: linear-gradient(90deg,#06c,#48c); color:#fff; }}
  header h1 {{ margin: 0; font-size: 20px; }}
  header .sub {{ font-size: 13px; opacity: 0.9; margin-top: 4px; }}
  main {{ padding: 20px 24px; }}
  .stats {{ display: flex; gap: 18px; flex-wrap: wrap; background: #fff; border: 1px solid #e0e0e0; border-radius: 6px; padding: 12px 16px; margin-bottom: 16px; font-size: 14px; }}
  .stats .kv {{ display: flex; flex-direction: column; }}
  .stats .kv .n {{ font-size: 22px; font-weight: 600; color: #06c; }}
  .stats .kv .lbl {{ font-size: 11px; color: #888; text-transform: uppercase; letter-spacing: 0.5px; }}
  table {{ width: 100%; background: #fff; border-collapse: collapse; border: 1px solid #e0e0e0; border-radius: 6px; overflow: hidden; font-size: 13px; }}
  th {{ background: #f0f4f8; text-align: left; padding: 8px 10px; font-weight: 600; color: #444; border-bottom: 1px solid #d0d0d0; }}
  td {{ padding: 8px 10px; border-bottom: 1px solid #ececec; vertical-align: top; }}
  td.org-cell, td.repo-cell {{ background: #fafafa; }}
  td.num {{ text-align: right; }}
  .muted {{ color: #888; }}
  .small {{ font-size: 12px; }}
  code {{ background: #f0f0f0; padding: 1px 6px; border-radius: 3px; font-size: 12px; }}
  .org-chip {{ display: inline-block; padding: 2px 8px; border-radius: 12px; font-size: 11px; font-weight: 600; color: #fff; }}
  .org-chip.org-meiki-lra {{ background: #06c; }}
  .org-chip.org-ttz-lif {{ background: #093; }}
  .org-chip.org-bahn-sqf {{ background: #c40; }}
  .org-chip.org-iilgmbh {{ background: #639; }}
  .org-chip.org-achimdehnert {{ background: #555; }}
  .role-root {{ display: inline-block; padding: 2px 6px; background: #cef; border-radius: 4px; font-size: 11px; }}
  .role-hybrid {{ display: inline-block; padding: 2px 6px; background: #fec; border-radius: 4px; font-size: 11px; }}
  .role-default {{ color: #999; font-size: 11px; }}
  .klass-mock {{ display: inline-block; padding: 1px 6px; background: #fee; color: #a00; border-radius: 3px; font-size: 11px; }}
  .klass-stub-demo, .klass-spec-demo, .klass-story {{ display: inline-block; padding: 1px 6px; background: #efe; color: #060; border-radius: 3px; font-size: 11px; }}
  footer {{ padding: 12px 24px; color: #888; font-size: 12px; text-align: center; }}

  /* Klickbare KD-Zeilen + Detail-Panel */
  tr.kd-row {{ cursor: pointer; transition: background 0.1s; }}
  tr.kd-row:hover {{ background: #f5f9ff; }}
  tr.kd-row .toggle {{ color: #06c; font-weight: 600; display: inline-block; width: 12px; transition: transform 0.15s; }}
  tr.kd-row.open .toggle {{ transform: rotate(90deg); }}
  tr.detail-row {{ display: none; }}
  tr.detail-row.visible {{ display: table-row; }}
  td.detail-cell {{ background: #fbfdff; padding: 14px 20px; border-bottom: 2px solid #cce; }}
  .detail-grid {{ display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 18px; margin-bottom: 12px; }}
  .detail-cell h4 {{ margin: 0 0 6px 0; font-size: 13px; color: #06c; }}
  ul.compact {{ margin: 0; padding-left: 18px; }}
  ul.compact li {{ margin-bottom: 4px; font-size: 12px; }}
  .rel-tag {{ display: inline-block; padding: 1px 5px; border-radius: 3px; font-size: 10px; font-weight: 600; margin-right: 4px; }}
  .rel-cf {{ background: #def; color: #06c; }}
  .rel-pc {{ background: #fde; color: #c0c; }}
  .rel-ac {{ background: #efe; color: #060; }}
  .rel-rt {{ background: #fec; color: #c80; }}
  .lineage-link, .mockup-link {{ background: #fff; border: 1px solid #cce; border-radius: 4px; padding: 8px 12px; margin: 8px 0; font-size: 13px; }}
  .mockup-link {{ border-color: #c80; background: #fffbf0; }}
  .lineage-link a, .mockup-link a {{ color: #06c; text-decoration: none; font-weight: 600; }}
  .lineage-link a:hover, .mockup-link a:hover {{ text-decoration: underline; }}
  .spec-path {{ font-family: monospace; font-size: 11px; padding-top: 4px; }}

  /* Sortable Headers (Stufe 1b) */
  th.sortable {{ cursor: pointer; user-select: none; }}
  th.sortable:hover {{ background: #e0e8f0; }}
  th.sortable::after {{ content: " ⇅"; opacity: 0.3; font-size: 10px; }}
  th.sort-asc::after {{ content: " ▲"; opacity: 1; color: #06c; }}
  th.sort-desc::after {{ content: " ▼"; opacity: 1; color: #06c; }}

  /* Drift-Validierung (Paket A: F3) */
  .warn-badge {{ display: inline-block; padding: 1px 6px; border-radius: 3px; font-size: 11px; font-weight: 600; margin-right: 4px; }}
  .warn-error {{ background: #fee; color: #a00; }}
  .warn-warning {{ background: #fef0d0; color: #a60; }}
  .warnings {{ background: #fff8f0; border: 1px solid #fcc; border-left: 4px solid #c40; padding: 10px 14px; margin-bottom: 12px; border-radius: 4px; }}
  .warnings h4 {{ margin: 0 0 6px 0; color: #c40; font-size: 13px; }}
  .warnings li.warn-error {{ background: none; padding-left: 0; }}
  .warnings li.warn-warning {{ background: none; padding-left: 0; }}
  .n-err {{ color: #c40 !important; }}
  .n-warn {{ color: #b80 !important; }}
  /* Feature B: "Mockup generieren"-Button (nur auf mockup-missing-Zeilen) */
  .mockup-gen-btn {{ display: inline-block; padding: 1px 8px; border-radius: 3px; font-size: 11px; font-weight: 600; margin-right: 6px; text-decoration: none; background: #e0ecff; color: #1d4ed8; border: 1px solid #bcd2ff; cursor: pointer; }}
  .mockup-gen-btn:hover {{ background: #cfe0ff; }}
  .mockup-gen-btn.mockup-gen-running {{ background: #f3f4f6; color: #6b7280; border-color: #d1d5db; pointer-events: none; cursor: default; }}
  /* Feature C2: Acceptance-Matrix — .ac-chip im Genesor-Root (Render-Variante: L578) */
  .ac-chip {{ display: inline-block; padding: 1px 6px; border-radius: 3px; font-size: 10px; font-weight: 600; margin-right: 6px; cursor: help; }}
  .ac-signed {{ background: #d1fae5; color: #065f46; border: 1px solid #a7f3d0; }}
  .ac-stale  {{ background: #fef3c7; color: #92400e; border: 1px solid #fde68a; }}
  .ac-none   {{ background: #f3f4f6; color: #6b7280; border: 1px solid #e5e7eb; }}
  .acceptance-matrix {{ margin: 12px 0; border: 1px solid #e3e8ee; border-radius: 6px; background: #fff; }}
  .acceptance-matrix > summary {{ cursor: pointer; padding: 10px 14px; font-weight: 600; color: #1f2937; list-style: none; }}
  .acceptance-matrix > summary::-webkit-details-marker {{ display: none; }}
  .acceptance-matrix > summary:hover {{ background: #f8fafc; }}
  .acceptance-matrix table {{ margin: 0; width: 100%; }}
  .acceptance-matrix .am-label {{ font-size: 11px; }}

  /* Sunset-Aging (F4) */
  td.sunset-ok {{ color: #060; }}
  td.sunset-near {{ background: #fef0d0; color: #a60; font-weight: 600; }}
  td.sunset-overdue {{ background: #fee; color: #a00; font-weight: 600; }}
  td.sunset-na {{ color: #888; }}

  /* Render-only-KDs (F11) */
  tr.render-only td {{ background: #fafaf0 !important; }}
  tr.render-only .toggle {{ color: #c40; }}

  /* Drift-Center (Pilot-Memo 2026-05-26) */
  .drift-center {{ background: linear-gradient(135deg,#fff 0%,#f8fafc 100%); border: 1px solid #e0e7ef; border-radius: 8px; padding: 16px 20px; margin-bottom: 16px; }}
  .drift-hero h2 {{ margin: 0 0 4px 0; font-size: 18px; color: #1e293b; }}
  .drift-hero p {{ margin: 0 0 12px 0; }}
  .drift-kpis {{ display: flex; gap: 18px; flex-wrap: wrap; padding: 10px 0; border-top: 1px solid #e0e7ef; border-bottom: 1px solid #e0e7ef; margin-bottom: 12px; }}
  .drift-kpis .kv {{ display: flex; flex-direction: column; min-width: 70px; }}
  .drift-kpis .kv .n {{ font-size: 20px; font-weight: 700; color: #06c; }}
  .drift-kpis .kv .lbl {{ font-size: 11px; color: #64748b; text-transform: uppercase; letter-spacing: 0.3px; }}
  .drift-status-in-sync .n {{ color: #16a34a !important; }}
  .drift-status-stale .n {{ color: #ca8a04 !important; }}
  .drift-status-partial .n {{ color: #ea580c !important; }}
  .drift-status-no-brief .n {{ color: #94a3b8 !important; }}
  .drift-filters {{ display: flex; gap: 6px; flex-wrap: wrap; align-items: center; padding-top: 8px; }}
  .filter-label {{ font-size: 12px; color: #64748b; font-weight: 600; margin-right: 4px; }}
  .filter-chip {{ padding: 4px 10px; border: 1px solid #cbd5e1; background: #fff; border-radius: 14px; cursor: pointer; font-size: 12px; transition: all 0.15s; }}
  .filter-chip:hover {{ background: #f1f5f9; }}
  .filter-chip.active {{ background: #06c; color: #fff; border-color: #06c; }}
  #drift-search {{ padding: 5px 10px; border: 1px solid #cbd5e1; border-radius: 14px; font-size: 12px; min-width: 200px; margin-left: 8px; }}

  /* Drift-Badge in Tabellen-Zeile */
  .drift-badge {{ display: inline-block; padding: 2px 8px; border-radius: 10px; font-size: 11px; font-weight: 600; white-space: nowrap; }}
  .compare-link {{ margin-left: 4px; text-decoration: none; opacity: 0.7; transition: opacity 0.15s; }}
  .compare-link:hover {{ opacity: 1; }}

  /* Row-Filter — hidden via class */
  tr.kd-row.hidden, tr.detail-row.hidden {{ display: none; }}

  /* Surface-Switcher (Pilot-Memo §Surface) */
  td.surface-cell {{ padding: 4px 6px; }}
  .surface-tabs {{ display: inline-flex; gap: 2px; flex-wrap: nowrap; }}
  .surface-pill {{
    display: inline-block;
    padding: 3px 8px;
    border-radius: 4px;
    font-size: 11px;
    font-weight: 600;
    text-decoration: none;
    border: 1px solid transparent;
    white-space: nowrap;
    transition: all 0.1s;
  }}
  .surface-pill.active {{ cursor: pointer; }}
  .surface-pill.disabled {{ opacity: 0.32; cursor: not-allowed; }}
  .surface-pill.surface-kd.active      {{ background: #e0f2fe; color: #075985; border-color: #bae6fd; }}
  .surface-pill.surface-kd.active:hover {{ background: #bae6fd; }}
  .surface-pill.surface-dev.active     {{ background: #fef9c3; color: #854d0e; border-color: #fde047; }}
  .surface-pill.surface-dev.active:hover {{ background: #fde047; }}
  .surface-pill.surface-staging.active {{ background: #fed7aa; color: #9a3412; border-color: #fdba74; }}
  .surface-pill.surface-staging.active:hover {{ background: #fdba74; }}
  .surface-pill.surface-prod.active    {{ background: #dcfce7; color: #166534; border-color: #86efac; }}
  .surface-pill.surface-prod.active:hover {{ background: #86efac; }}
  .surface-pill.disabled.surface-kd      {{ background: #f1f5f9; color: #64748b; }}
  .surface-pill.disabled.surface-dev     {{ background: #f1f5f9; color: #64748b; }}
  .surface-pill.disabled.surface-staging {{ background: #f1f5f9; color: #64748b; }}
  .surface-pill.disabled.surface-prod    {{ background: #f1f5f9; color: #64748b; }}

  /* Master-Surface-Toggle im Hero */
  .surface-master {{ display: flex; gap: 6px; align-items: center; margin-top: 8px; padding-top: 8px; border-top: 1px solid #e0e7ef; }}
  .surface-master-label {{ font-size: 12px; color: #64748b; font-weight: 600; }}
  .surface-master button {{
    padding: 4px 12px;
    border: 1px solid #cbd5e1;
    background: #fff;
    border-radius: 14px;
    cursor: pointer;
    font-size: 12px;
    font-weight: 600;
  }}
  .surface-master button.active {{ background: #06c; color: #fff; border-color: #06c; }}
  /* Wenn Master gesetzt → nur passende Pills hervorheben, andere ausgrauen */
  .surface-tabs.master-kd      .surface-pill:not(.surface-kd) {{ opacity: 0.4; }}
  .surface-tabs.master-dev     .surface-pill:not(.surface-dev) {{ opacity: 0.4; }}
  .surface-tabs.master-staging .surface-pill:not(.surface-staging) {{ opacity: 0.4; }}
  .surface-tabs.master-prod    .surface-pill:not(.surface-prod) {{ opacity: 0.4; }}

  /* Surface-Pill als button (statt <a>) */
  button.surface-pill {{ font-family: inherit; cursor: pointer; }}

  /* Surface-Modal (Pilot-Memo §Surface-Modal) */
  .surface-modal {{ display: none; position: fixed; inset: 0; z-index: 9999; }}
  .surface-modal[aria-hidden="false"] {{ display: block; }}
  .surface-modal-backdrop {{
    position: absolute; inset: 0;
    background: rgba(15, 23, 42, 0.55);
    backdrop-filter: blur(2px);
  }}
  .surface-modal-dialog {{
    position: relative;
    max-width: 1000px; width: calc(100vw - 40px);
    max-height: calc(100vh - 60px); overflow-y: auto;
    margin: 30px auto;
    background: #fff;
    border-radius: 10px;
    box-shadow: 0 20px 60px rgba(0,0,0,0.4);
  }}
  .surface-modal header {{
    display: flex; align-items: center; justify-content: space-between;
    padding: 14px 20px;
    background: linear-gradient(90deg,#06c,#48c);
    color: #fff;
    border-radius: 10px 10px 0 0;
  }}
  .surface-modal header h2 {{ margin: 0; font-size: 16px; }}
  .surface-modal-close {{
    background: rgba(255,255,255,0.2); color: #fff;
    border: none; padding: 2px 12px;
    border-radius: 14px; cursor: pointer;
    font-size: 22px; line-height: 1;
  }}
  .surface-modal-close:hover {{ background: rgba(255,255,255,0.35); }}
  .surface-modal-body {{ padding: 16px 20px; }}
  table.surface-screen-table {{ font-size: 12px; width: 100%; border: 1px solid #e0e7ef; }}
  table.surface-screen-table th {{ background: #f1f5f9; padding: 6px 8px; text-align: left; font-weight: 600; font-size: 11px; }}
  table.surface-screen-table td {{ padding: 6px 8px; border-bottom: 1px solid #f1f5f9; vertical-align: top; }}
  table.surface-screen-table td.screen-id {{ font-weight: 600; color: #1e293b; white-space: nowrap; }}
  table.surface-screen-table td.route {{ color: #64748b; font-family: ui-monospace, monospace; font-size: 11px; }}
  .surface-screen-pill {{
    display: inline-block; padding: 2px 8px;
    border-radius: 10px; font-size: 11px; font-weight: 600;
    text-decoration: none;
    border: 1px solid transparent;
  }}
  .surface-screen-pill.kd      {{ background: #e0f2fe; color: #075985; border-color: #bae6fd; }}
  .surface-screen-pill.dev     {{ background: #fef9c3; color: #854d0e; border-color: #fde047; }}
  .surface-screen-pill.staging {{ background: #fed7aa; color: #9a3412; border-color: #fdba74; }}
  .surface-screen-pill.prod    {{ background: #dcfce7; color: #166534; border-color: #86efac; }}
  .surface-screen-pill.disabled {{ background: #f1f5f9; color: #94a3b8; cursor: not-allowed; opacity: 0.5; }}

  /* ── Repo-Rail Master-Detail (KONZ-iil-klickdummy-002) ───────────────── */
  .genesor-layout {{ display: grid; grid-template-columns: 232px 1fr; align-items: start; gap: 0; }}
  .genesor-layout > main {{ min-width: 0; overflow-x: auto; }}
  .repo-rail {{ position: sticky; top: 0; align-self: start; max-height: 100vh; overflow-y: auto;
    background: #fff; border-right: 1px solid #e3e8ee; padding: 14px 0; }}
  .repo-rail .rail-facet {{ padding: 0 14px 10px; display: flex; align-items: center; gap: 6px; }}
  .repo-rail .rail-facet label {{ font-size: 11px; color: #6b7280; text-transform: uppercase; letter-spacing: .5px; }}
  .repo-rail .rail-facet select {{ flex: 1; padding: 4px 8px; border: 1px solid #e3e8ee; border-radius: 6px; font-size: 13px; }}
  .repo-rail .rail-head {{ font-size: 11px; text-transform: uppercase; letter-spacing: .5px; color: #6b7280; padding: 6px 14px; }}
  .repo-rail .rail-item {{ display: flex; align-items: center; gap: 8px; width: 100%; text-align: left;
    border: 0; background: none; cursor: pointer; padding: 8px 14px; font-size: 13px; color: #1f2937;
    border-left: 3px solid transparent; }}
  .repo-rail .rail-item:hover {{ background: #eef2ff; }}
  .repo-rail .rail-item.active {{ background: #eef2ff; border-left-color: #1e3a8a; font-weight: 600; color: #1e3a8a; }}
  .repo-rail .rail-item .dot {{ width: 8px; height: 8px; border-radius: 50%; flex: 0 0 auto; }}
  .repo-rail .rail-item .glabel {{ flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }}
  .repo-rail .rail-item .count {{ font-size: 11px; color: #64748b; background: #f1f5f9; border-radius: 10px; padding: 1px 8px; }}
  .repo-rail .rail-item.active .count {{ background: #fff; }}
  @media (max-width: 900px) {{
    .genesor-layout {{ grid-template-columns: 1fr; }}
    .repo-rail {{ position: static; max-height: none; border-right: 0; border-bottom: 1px solid #e3e8ee; }}
  }}

  /* ── Repo-Linse ein-/ausklappen — mehr Platz für den Inhalt ───────────── */
  .rail-toggle {{ flex: 0 0 auto; border: 1px solid #e3e8ee; background: #fff; color: #6b7280;
    border-radius: 6px; cursor: pointer; font-size: 12px; line-height: 1; padding: 5px 7px; }}
  .rail-toggle:hover {{ background: #eef2ff; color: #1e3a8a; }}
  .genesor-layout.rail-collapsed {{ grid-template-columns: 0 1fr; }}
  .genesor-layout.rail-collapsed .repo-rail {{ overflow: hidden; visibility: hidden;
    min-width: 0; padding: 0; border-right: 0; }}
  .rail-expand {{ display: none; }}
  .genesor-layout.rail-collapsed .rail-expand {{ display: inline-flex; align-items: center; gap: 6px;
    position: sticky; top: 8px; margin: 0 0 10px; border: 1px solid #e3e8ee; background: #fff;
    color: #1e3a8a; border-radius: 6px; cursor: pointer; font-size: 12px; font-weight: 600; padding: 5px 10px; }}
  .rail-expand:hover {{ background: #eef2ff; }}
</style>
</head>
<body>

<header style="display:flex;align-items:center;gap:16px;flex-wrap:wrap;">
  <div style="flex:1;min-width:200px;">
    <h1 style="margin:0;">🌱 IIL-Genesor — Klickdummy-Übersicht</h1>
    <div class="sub">Cross-Repo · auto-generiert · {date.today().isoformat()} · Stufe 1a (statisch)</div>
    <div class="sub" style="margin-top:4px;"><a href="./coverage.html" style="color:#06c;text-decoration:none;">📊 UC ↔ KD Coverage</a> · {n_ucs} Use Cases erfasst</div>
  </div>
  <div style="display:flex;align-items:center;gap:6px;color:#fff;">
    <label for="skin-select" style="font-size:12px;opacity:0.9;">🎨 Demo-Style</label>
    <select id="skin-select" style="padding:5px 10px;border:1px solid rgba(255,255,255,.4);background:rgba(255,255,255,.1);color:#fff;border-radius:4px;font-size:13px;">
      {genesor_skin_options}
    </select>
  </div>
</header>
<script>
  // Skin-Switcher auf Root-Ebene (Genesor) — gleiche localStorage-Logik wie pro Render
  (function() {{
    const SKIN_KEY = 'genesor_skin';
    function applySkin(url) {{
      document.querySelectorAll('link[data-skin="1"]').forEach(l => l.remove());
      if (url && url !== '__greenfield') {{
        const link = document.createElement('link');
        link.rel = 'stylesheet';
        link.href = url;
        link.setAttribute('data-skin', '1');
        document.head.appendChild(link);
      }}
      try {{ localStorage.setItem(SKIN_KEY, url || '__greenfield'); }} catch(e) {{}}
    }}
    let saved = '__greenfield';
    try {{ saved = localStorage.getItem(SKIN_KEY) || '__greenfield'; }} catch(e) {{}}
    const sel = document.getElementById('skin-select');
    if (sel) {{
      sel.value = saved;
      applySkin(saved);
      sel.addEventListener('change', e => applySkin(e.target.value));
    }}
  }})();
</script>

<div class="genesor-layout">
<aside class="repo-rail" id="repo-rail">
  <div class="rail-facet">
    <label for="facet-select">Linse</label>
    <select id="facet-select">
      <option value="repo">Repo</option>
      <option value="org">Org</option>
      <option value="class">Class</option>
      <option value="role">Rolle</option>
    </select>
    <button type="button" id="rail-collapse" class="rail-toggle" title="Linse einklappen" aria-label="Linse einklappen">◀</button>
  </div>
  <div class="rail-head" id="rail-head">Repos</div>
  <nav id="rail-nav"></nav>
</aside>
<main>
<button type="button" id="rail-expand" class="rail-expand" title="Linse ausklappen" aria-label="Linse ausklappen">▶ Linse</button>

<div class="stats">
  <div class="kv"><span class="n">{n_kds}</span><span class="lbl">Klickdummies</span></div>
  <div class="kv"><span class="n">{n_orgs}</span><span class="lbl">Orgs / Kunden</span></div>
  <div class="kv"><span class="n">{n_repos}</span><span class="lbl">Repos</span></div>
  <div class="kv"><span class="n">{n_root}</span><span class="lbl">Root</span></div>
  <div class="kv"><span class="n">{n_hybrid}</span><span class="lbl">Hybrid</span></div>
  <div class="kv"><span class="n">{n_render_only}</span><span class="lbl">render-only</span></div>
  <div class="kv"><span class="n">{n_ucs_total}</span><span class="lbl">Use Cases</span></div>
  <div class="kv"><span class="n">{n_replaces}</span><span class="lbl">Ablösungen</span></div>
  <div class="kv"><span class="n n-err">{n_errors}</span><span class="lbl">Spec-Errors</span></div>
  <div class="kv"><span class="n n-warn">{n_warns}</span><span class="lbl">Warnings</span></div>
</div>

<!-- ── Drift-Center (Pilot-Memo 2026-05-26) ─────────────────── -->
<div class="drift-center">
  <div class="drift-hero">
    <h2>🛡️ Genesor als stabile Basis — Drift-Center</h2>
    <p class="muted small">
      Vergleich Klickdummy ↔ Implementierung — pro Zeile öffnet 🔍 die Brief-§10-Drift-Sektion ·
      Surface-Pills wechseln zwischen <b>📋 KD-Spec / 🛠 Dev / 🧪 Staging / ✅ Prod</b>
      ({n_apps_indexed} Apps in <code>iil-relaunch/apps.json</code> indiziert)
    </p>
  </div>
  <div class="surface-master">
    <span class="surface-master-label">Surface-Highlight:</span>
    <button data-master-surface="none" class="active">Alle anzeigen</button>
    <button data-master-surface="kd">📋 KD-Spec</button>
    <button data-master-surface="dev">🛠 Dev</button>
    <button data-master-surface="staging">🧪 Staging</button>
    <button data-master-surface="prod">✅ Prod</button>
  </div>
  <div class="drift-kpis">
    <div class="kv"><span class="n">{n_pilot_kds}</span><span class="lbl">KDs mit Pilot-Brief</span></div>
    <div class="kv"><span class="n">{n_briefs_total}</span><span class="lbl">Briefs generiert</span></div>
    <div class="kv"><span class="n">{n_briefs_expected}</span><span class="lbl">erwartet</span></div>
    <div class="kv drift-status-in-sync"><span class="n">{drift_counter['in-sync']}</span><span class="lbl">🟢 in-sync</span></div>
    <div class="kv drift-status-stale"><span class="n">{drift_counter['stale']}</span><span class="lbl">🟡 stale</span></div>
    <div class="kv drift-status-partial"><span class="n">{drift_counter['partial']}</span><span class="lbl">🟠 partial</span></div>
    <div class="kv drift-status-no-brief"><span class="n">{drift_counter['no-brief']}</span><span class="lbl">⚪ no-brief</span></div>
  </div>
  <div class="drift-filters">
    <span class="filter-label">Filter:</span>
    <button class="filter-chip active" data-filter-org="all">Alle Orgs</button>
    <button class="filter-chip" data-filter-org="achimdehnert">achimdehnert</button>
    <button class="filter-chip" data-filter-org="meiki-lra">meiki-lra</button>
    <button class="filter-chip" data-filter-org="ttz-lif">ttz-lif</button>
    <span class="filter-label" style="margin-left:14px;">Drift-Status:</span>
    <button class="filter-chip active" data-filter-drift="all">Alle</button>
    <button class="filter-chip" data-filter-drift="in-sync">🟢 in-sync</button>
    <button class="filter-chip" data-filter-drift="stale">🟡 stale</button>
    <button class="filter-chip" data-filter-drift="partial">🟠 partial</button>
    <button class="filter-chip" data-filter-drift="no-brief">⚪ no-brief</button>
    <input type="search" id="drift-search" placeholder="Suche Repo, KD, Persona…" />
  </div>
</div>

<p class="muted small">💡 Klick auf eine Zeile öffnet Detail-Panel · 🔍 öffnet Brief-§10 (Drift-Sektion KD↔Code).</p>

{acceptance_matrix_section}

<table id="genesor-table">
  <thead>
    <tr>
      <th class="sortable" data-col="0">Org / Kunde</th>
      <th class="sortable" data-col="1">Repo</th>
      <th class="sortable" data-col="2">Klickdummy</th>
      <th class="sortable" data-col="3">Rolle</th>
      <th class="sortable" data-col="4">Class</th>
      <th class="sortable" data-col="5" data-numeric="1">Screens</th>
      <th class="sortable" data-col="6" data-numeric="1">#UCs</th>
      <th data-col="7" title="Wechsel zwischen Klickdummy-Spec und Implementation-Environments">Surface</th>
      <th class="sortable" data-col="8" title="Drift-Status zwischen KD-Spec und generiertem Brief">Drift ↔ KD/Code</th>
      <th class="sortable" data-col="9">Replaces</th>
      <th class="sortable" data-col="10">Sunset</th>
      <th class="sortable" data-col="11">Personas</th>
      <th class="sortable" data-col="12">Stakeholder / LRA</th>
    </tr>
  </thead>
  <tbody>{table_body}
  </tbody>
</table>

</main>
</div><!-- /genesor-layout -->

<!-- ── Surface-Modal (Pilot-Memo §Surface-Modal) ──────────── -->
<div id="surface-modal" class="surface-modal" aria-hidden="true">
  <div class="surface-modal-backdrop" onclick="closeSurfaceModal()"></div>
  <div class="surface-modal-dialog" role="dialog" aria-labelledby="surface-modal-title">
    <header>
      <h2 id="surface-modal-title">Screen-Vergleich</h2>
      <button class="surface-modal-close" onclick="closeSurfaceModal()" title="Schließen (Esc)">×</button>
    </header>
    <div class="surface-modal-body">
      <p class="muted small" id="surface-modal-subtitle">…</p>
      <table class="surface-screen-table">
        <thead><tr>
          <th>Screen</th>
          <th>Route</th>
          <th>📋 KD</th>
          <th>🛠 Dev</th>
          <th>🧪 Stg</th>
          <th>✅ Prod</th>
        </tr></thead>
        <tbody id="surface-screen-tbody"></tbody>
      </table>
      <p class="muted small" style="margin-top:10px;">
        💡 Wenn Dev/Stg/Prod-Pill grau ist: entweder hat der KD-Screen kein <code>route:</code>-Feld
        in der Spec, oder das Environment ist noch nicht deployed. Spec ergänzen für 1:1-Matching.
      </p>
    </div>
  </div>
</div>

<footer>
  IIL-Genesor · Stufe 1a (cross-repo statisch) · <code>scripts/klickdummy_lineage.py --genesor</code>
</footer>

<script>
function toggleDetail(row) {{
  const detailId = row.dataset.detailId;
  const detail = document.getElementById(detailId);
  if (!detail) return;
  const isOpen = detail.classList.toggle('visible');
  row.classList.toggle('open', isOpen);
}}

// Feature B: "🛠 Mockup generieren" — Issue öffnet im neuen Tab (href/target),
// hier nur Sofort-Feedback: Label umschalten + Button entschärfen.
function mockupGenStart(btn) {{
  if (!btn || btn.dataset.genStarted === '1') return;
  btn.dataset.genStarted = '1';
  btn.textContent = '⏳ generieren läuft…';
  btn.classList.add('mockup-gen-running');
  btn.setAttribute('aria-disabled', 'true');
}}

// Surface-Modal (Pilot-Memo §Surface-Modal — Screen×Surface-Matrix pro KD)
function openSurfaceModal(pillBtn) {{
  const tabs = pillBtn.closest('.surface-tabs');
  if (!tabs) return;
  const raw = tabs.dataset.modalPayload;
  if (!raw) return;
  let payload;
  try {{ payload = JSON.parse(raw); }}
  catch (e) {{ console.error('Modal-Payload parse error', e); return; }}

  const modal = document.getElementById('surface-modal');
  const title = document.getElementById('surface-modal-title');
  const subtitle = document.getElementById('surface-modal-subtitle');
  const tbody = document.getElementById('surface-screen-tbody');

  title.textContent = `${{payload.repo}} / ${{payload.kd}}`;
  subtitle.innerHTML = `<b>${{payload.kd_title || ''}}</b> · Surface-Pill geklickt: <b>${{pillBtn.dataset.surface}}</b>`;

  // Pro Screen eine Zeile
  tbody.innerHTML = '';
  const screens = payload.screens || [];
  if (!screens.length) {{
    tbody.innerHTML = '<tr><td colspan="6" class="muted small" style="text-align:center;padding:20px;">Keine Screens im Spec gefunden.</td></tr>';
  }}
  // HTML-escape helper — wichtig für Routes mit <ausschreibung_id> u.ä.
  const esc = (s) => String(s || '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');

  screens.forEach(s => {{
    // route_example zuerst (hat konkrete IDs), sonst route mit Platzhaltern
    const displayRoute = s.route_example || s.route || '';
    const route = displayRoute;  // gleiche Datenbasis fürs URL-Bauen
    const apiHint = (s.api_paths && s.api_paths.length)
      ? `<br><span class="muted small">API: ${{s.api_paths.map(esc).join(', ')}}</span>`
      : '';
    // KD-Render mit Anchor zum Screen
    const kdUrl = payload.kd_url ? `${{payload.kd_url}}#screen-${{s.screen_id}}` : '';
    const kdPill = kdUrl
      ? `<a class="surface-screen-pill kd" href="${{kdUrl}}" target="_blank" title="KD-Render mit Screen-Anker">📋 KD</a>`
      : `<span class="surface-screen-pill kd disabled">📋 KD</span>`;

    // Dev/Stg/Prod: nur wenn route da UND base-URL gesetzt.
    // Wichtig: Route ist absolut (/submission/...), daher braucht es nur den Origin
    // (Protocol+Host+Port) der Base-URL, NICHT den ganzen Pfad.
    function makeImplPill(env, label) {{
      const base = (payload.surface_base || {{}})[env];
      if (!base || !route) {{
        const reason = !base ? `${{env}}-URL fehlt in apps.json` : 'kein route: im Spec';
        return `<span class="surface-screen-pill ${{env}} disabled" title="${{reason}}">${{label}}</span>`;
      }}
      let origin;
      try {{
        const u = new URL(base);
        origin = `${{u.protocol}}//${{u.host}}`;
      }} catch (e) {{
        // base ist relativ — als Fallback nehme den Server-Origin (Page-Origin)
        origin = window.location.origin;
      }}
      const path = (s.route_example || route).startsWith('/')
        ? (s.route_example || route)
        : `/${{s.route_example || route}}`;
      const full = origin + path;
      return `<a class="surface-screen-pill ${{env}}" href="${{full}}" target="_blank" title="${{full}}">${{label}}</a>`;
    }}

    const row = document.createElement('tr');
    row.innerHTML = `
      <td class="screen-id">${{esc(s.screen_id)}}<br><span class="muted small">${{esc(s.title || '')}}</span></td>
      <td class="route">${{displayRoute ? esc(displayRoute) : '<span class="muted">—</span>'}}${{apiHint}}</td>
      <td>${{kdPill}}</td>
      <td>${{makeImplPill('dev', '🛠 Dev')}}</td>
      <td>${{makeImplPill('staging', '🧪 Stg')}}</td>
      <td>${{makeImplPill('prod', '✅ Prod')}}</td>
    `;
    tbody.appendChild(row);
  }});

  modal.setAttribute('aria-hidden', 'false');
}}

function closeSurfaceModal() {{
  const modal = document.getElementById('surface-modal');
  if (modal) modal.setAttribute('aria-hidden', 'true');
}}

document.addEventListener('keydown', e => {{
  if (e.key === 'Escape') closeSurfaceModal();
}});

// Drift-Center Filter (Pilot-Memo 2026-05-26)
(function() {{
  const state = {{ org: 'all', drift: 'all', search: '', facet: 'repo', group: null }};

  function applyFilters() {{
    const rows = document.querySelectorAll('#genesor-table tbody tr.kd-row');
    let visible = 0;
    rows.forEach(row => {{
      const org = row.dataset.org || '';
      const drift = row.dataset.driftStatus || '';
      const text = row.innerText.toLowerCase();
      const matchOrg = state.org === 'all' || org === state.org;
      const matchDrift = state.drift === 'all' || drift === state.drift;
      const matchSearch = !state.search || text.includes(state.search);
      const groupVal = row.dataset[state.facet] || '';
      const matchGroup = !state.group || groupVal === state.group;
      const show = matchOrg && matchDrift && matchSearch && matchGroup;
      row.classList.toggle('hidden', !show);
      const detailId = row.dataset.detailId;
      const detail = detailId ? document.getElementById(detailId) : null;
      if (detail) detail.classList.toggle('hidden', !show);
      if (show) visible++;
    }});
    const url = new URL(window.location);
    if (state.org !== 'all') url.searchParams.set('org', state.org); else url.searchParams.delete('org');
    if (state.drift !== 'all') url.searchParams.set('drift', state.drift); else url.searchParams.delete('drift');
    history.replaceState({{}}, '', url);
  }}

  document.querySelectorAll('.filter-chip[data-filter-org]').forEach(btn => {{
    btn.addEventListener('click', () => {{
      document.querySelectorAll('.filter-chip[data-filter-org]').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      state.org = btn.dataset.filterOrg;
      applyFilters();
    }});
  }});
  document.querySelectorAll('.filter-chip[data-filter-drift]').forEach(btn => {{
    btn.addEventListener('click', () => {{
      document.querySelectorAll('.filter-chip[data-filter-drift]').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      state.drift = btn.dataset.filterDrift;
      applyFilters();
    }});
  }});
  const search = document.getElementById('drift-search');
  if (search) {{
    search.addEventListener('input', () => {{
      state.search = search.value.toLowerCase();
      applyFilters();
    }});
  }}

  // Master-Surface-Toggle (Pilot-Memo §Surface)
  function applyMasterSurface(surface) {{
    const allTabs = document.querySelectorAll('.surface-tabs');
    ['kd','dev','staging','prod'].forEach(s => {{
      allTabs.forEach(t => t.classList.remove(`master-${{s}}`));
    }});
    if (surface && surface !== 'none') {{
      allTabs.forEach(t => t.classList.add(`master-${{surface}}`));
    }}
    const url = new URL(window.location);
    if (surface && surface !== 'none') url.searchParams.set('surface', surface);
    else url.searchParams.delete('surface');
    history.replaceState({{}}, '', url);
  }}
  document.querySelectorAll('.surface-master button').forEach(btn => {{
    btn.addEventListener('click', () => {{
      document.querySelectorAll('.surface-master button').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      applyMasterSurface(btn.dataset.masterSurface);
    }});
  }});

  // ── Repo-Rail Master-Detail (KONZ-iil-klickdummy-002) ──────────────────
  const FACET_LABEL = {{ repo: 'Repos', org: 'Orgs', 'class': 'Klassen', role: 'Rollen' }};
  const DRIFT_RANK = {{ 'partial': 3, 'stale': 2, 'no-brief': 1, 'in-sync': 0 }};
  const DRIFT_DOT  = {{ 'partial': '#f97316', 'stale': '#eab308', 'no-brief': '#cbd5e1', 'in-sync': '#16a34a' }};

  function buildRail() {{
    const facet = state.facet;
    const rows = document.querySelectorAll('#genesor-table tbody tr.kd-row');
    const groups = {{}};
    rows.forEach(row => {{
      const g = row.dataset[facet] || '—';
      if (!groups[g]) groups[g] = {{ count: 0, worst: -1 }};
      groups[g].count++;
      const dr = DRIFT_RANK[row.dataset.driftStatus];
      if (dr !== undefined && dr > groups[g].worst) groups[g].worst = dr;
    }});
    const head = document.getElementById('rail-head');
    if (head) head.textContent = FACET_LABEL[facet] || facet;
    const nav = document.getElementById('rail-nav');
    if (!nav) return;
    const keys = Object.keys(groups).sort((a, b) => {{
      const d = groups[b].count - groups[a].count;
      return d !== 0 ? d : a.localeCompare(b);
    }});
    const esc = (s) => String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/"/g,'&quot;');
    let buf = '<button class="rail-item' + (state.group ? '' : ' active') + '" data-group="">'
      + '<span class="dot" style="background:#e2e8f0"></span>'
      + '<span class="glabel">Alle ' + (FACET_LABEL[facet] || '') + '</span>'
      + '<span class="count">' + rows.length + '</span></button>';
    keys.forEach(k => {{
      const worst = groups[k].worst;
      let color = '#e2e8f0';
      Object.keys(DRIFT_RANK).forEach(s => {{ if (DRIFT_RANK[s] === worst) color = DRIFT_DOT[s]; }});
      buf += '<button class="rail-item' + (k === state.group ? ' active' : '') + '" data-group="' + esc(k) + '">'
        + '<span class="dot" style="background:' + color + '"></span>'
        + '<span class="glabel">' + esc(k) + '</span>'
        + '<span class="count">' + groups[k].count + '</span></button>';
    }});
    nav.innerHTML = buf;
    nav.querySelectorAll('.rail-item').forEach(b => {{
      b.addEventListener('click', () => {{
        const g = b.dataset.group;
        location.hash = g ? ('#/' + facet + '/' + encodeURIComponent(g)) : ('#/' + facet + '/');
      }});
    }});
  }}

  function readHash() {{
    let h = location.hash || '';
    h = (h.indexOf('#/') === 0) ? h.substring(2) : '';
    const slash = h.indexOf('/');
    if (slash >= 0) {{
      const facet = h.substring(0, slash);
      const group = h.substring(slash + 1);
      if (['repo','org','class','role'].indexOf(facet) >= 0) {{
        state.facet = facet;
        state.group = group ? decodeURIComponent(group) : null;
        const sel = document.getElementById('facet-select');
        if (sel) sel.value = state.facet;
      }}
    }}
  }}

  function syncFromHash() {{ readHash(); buildRail(); applyFilters(); }}

  const facetSel = document.getElementById('facet-select');
  if (facetSel) facetSel.addEventListener('change', () => {{
    state.facet = facetSel.value;
    state.group = null;
    location.hash = '#/' + state.facet + '/';
    syncFromHash();
  }});
  window.addEventListener('hashchange', syncFromHash);
  syncFromHash();

  // Initial-State aus URL-Params
  const params = new URLSearchParams(window.location.search);
  const initialOrg = params.get('org');
  const initialDrift = params.get('drift');
  const initialSurface = params.get('surface');
  if (initialOrg) {{
    const btn = document.querySelector(`.filter-chip[data-filter-org="${{initialOrg}}"]`);
    if (btn) btn.click();
  }}
  if (initialDrift) {{
    const btn = document.querySelector(`.filter-chip[data-filter-drift="${{initialDrift}}"]`);
    if (btn) btn.click();
  }}
  if (initialSurface) {{
    const btn = document.querySelector(`.surface-master button[data-master-surface="${{initialSurface}}"]`);
    if (btn) btn.click();
  }}
}})();

// Click-to-Sort auf den Tabellen-Headern (Stufe 1b)
// Sortiert kd-row + zugehörige detail-row als Paar.
document.querySelectorAll('th.sortable').forEach(th => {{
  th.addEventListener('click', () => {{
    const col = parseInt(th.dataset.col, 10);
    const numeric = th.dataset.numeric === '1';
    const tbody = document.querySelector('#genesor-table tbody');
    const allRows = Array.from(tbody.querySelectorAll('tr'));
    // Paare bauen: kd-row + nachfolgende detail-row
    const pairs = [];
    for (let i = 0; i < allRows.length; i++) {{
      if (allRows[i].classList.contains('kd-row')) {{
        const detail = allRows[i + 1];
        pairs.push([allRows[i], detail && detail.classList.contains('detail-row') ? detail : null]);
      }}
    }}
    // Aktuelles Sort-Direction lesen
    const currentDir = th.classList.contains('sort-asc') ? 'asc' : (th.classList.contains('sort-desc') ? 'desc' : null);
    const newDir = currentDir === 'asc' ? 'desc' : 'asc';
    document.querySelectorAll('th.sortable').forEach(h => h.classList.remove('sort-asc', 'sort-desc'));
    th.classList.add('sort-' + newDir);
    // Werte extrahieren + sortieren
    pairs.sort(([rowA], [rowB]) => {{
      const cellA = rowA.cells[col].textContent.trim();
      const cellB = rowB.cells[col].textContent.trim();
      let cmp;
      if (numeric) cmp = parseFloat(cellA) - parseFloat(cellB);
      else cmp = cellA.localeCompare(cellB, 'de');
      return newDir === 'asc' ? cmp : -cmp;
    }});
    // Re-Append in neuer Reihenfolge
    pairs.forEach(([kd, detail]) => {{
      tbody.appendChild(kd);
      if (detail) tbody.appendChild(detail);
    }});
  }});
}});

// ── Repo-Linse ein-/ausklappen (localStorage-persistent) ─────────────────
(function() {{
  const KEY = 'genesor_rail_collapsed';
  const layout = document.querySelector('.genesor-layout');
  if (!layout) return;
  const btnCollapse = document.getElementById('rail-collapse');
  const btnExpand = document.getElementById('rail-expand');
  function apply(collapsed) {{
    layout.classList.toggle('rail-collapsed', collapsed);
    try {{ localStorage.setItem(KEY, collapsed ? '1' : '0'); }} catch(e) {{}}
  }}
  let saved = '0';
  try {{ saved = localStorage.getItem(KEY) || '0'; }} catch(e) {{}}
  apply(saved === '1');
  if (btnCollapse) btnCollapse.addEventListener('click', () => apply(true));
  if (btnExpand) btnExpand.addEventListener('click', () => apply(false));
}})();
</script>

</body>
</html>
"""


# ---- Per-Repo-Lineage-Generator (Stufe 1b) ---------------------------------


def generate_per_repo_lineages(records: list[dict], out_dir: Path) -> list[Path]:
    """Pro Repo eine Mermaid-Lineage-HTML generieren — nur wenn ≥2 KDs mit Spec (F12)."""
    from collections import defaultdict
    by_repo: dict[str, list[dict]] = defaultdict(list)
    for r in records:
        if r.get("kind", "spec") != "spec":
            continue   # render-only KDs ohne Spec im Lineage nichts beizutragen
        by_repo[r["repo"]].append(r)
    written: list[Path] = []
    for repo_name, repo_records in by_repo.items():
        if len(repo_records) < 2:
            continue   # F12: nur sinnvoll bei ≥2 KDs (sonst leerer Graph)
        specs_for_repo = [(r["kd"], r["path"], r["data"]) for r in repo_records]
        # Suche Contracts in zwei möglichen Pfaden:
        contracts_dir_a = _cfg.repos_root / repo_name / "docs" / "01-architektur" / "contracts"
        contracts_dir_b = _cfg.repos_root / repo_name / "contracts"
        repo_contracts: dict[str, Path] = {}
        for cd in (contracts_dir_a, contracts_dir_b):
            repo_contracts.update(find_contracts_in_dir(cd))
        # CD-Upgrade (2026-05-26): doc-profile-basierter Style + Click-Direktiven
        repo_dir = _cfg.repos_root / repo_name
        profile = read_doc_profile(repo_dir)
        style = _DOMAIN_STYLES.get(profile, _DOMAIN_STYLES["default"])
        mermaid = emit_mermaid(specs_for_repo, repo_contracts)
        # Mermaid Init mit themeVariables aus doc-profile.
        # Fix 2026-05-26: defaultRenderer:elk entfernt (ELK in Mermaid 10.9.1
        # opt-in Plugin, nicht überall geladen → Syntax Error). Dagre-Default
        # ist robuster. Plus: Click-Direktiven direkt nach Node-Defs, vor
        # classDef (Mermaid 10.x parst Reihenfolge strikt).
        # Font-Family entschärft (komplexe Quote-Stacks im JSON-Init können
        # Tokenizer verwirren).
        click_lines = []
        for kd_name, _p, _d in specs_for_repo:
            nid = node_id(kd_name)
            # Mermaid click-Syntax: click <nid> "<url>" "<tooltip>" _blank
            # Tooltip ohne deutsche Sonderzeichen halten — sicherer.
            click_lines.append(
                f'    click {nid} "./render/{repo_name}-{kd_name}.html" "Open mockup" _blank'
            )
        # Theme-Variables: Font-Family minimal halten (kein Quote-Mix)
        font_simple = '"sans-serif"' if "Georgia" not in style["font_h"] else '"Georgia, serif"'
        new_init = (
            '%%{init: {'
            '"theme":"base",'
            '"themeVariables":{'
            f'"primaryColor":"{style["accent_bg"]}",'
            '"primaryTextColor":"#1f2937",'
            f'"primaryBorderColor":"{style["accent"]}",'
            f'"lineColor":"{style["accent"]}",'
            '"secondaryColor":"#fef3c7",'
            '"tertiaryColor":"#f3f4f6",'
            f'"fontFamily":{font_simple}'
            '},'
            '"flowchart":{"curve":"basis"}'
            '}}%%'
        )
        # Click-Direktiven VOR classDef einfügen, damit Mermaid 10.9.1
        # die Knoten-Refs noch findet bevor Style-Block schliesst.
        mermaid_themed = mermaid.replace(
            '%%{init: {"flowchart": {"defaultRenderer": "elk"}} }%%',
            new_init,
        ).replace(
            "%% --- Styling ---",
            "%% --- Click-Direktiven (CD-Upgrade) ---\n" + "\n".join(click_lines) + "\n\n%% --- Styling ---",
        )

        html_out = build_html(mermaid_themed, specs_for_repo, repo_contracts)
        # Repo-spezifische Header-Beschriftung
        html_out = html_out.replace(
            "Klickdummy-Lineage · meiki-hub",
            f"Klickdummy-Lineage · {repo_name}",
        )

        # Quick-Stats für Header (KD-Count, Profile, Smoke-Status — wird beim Build berechnet)
        kd_count = len(specs_for_repo)
        kd_classes = sorted({(d.get("class") or "?") for _, _, d in specs_for_repo})
        stats_chip = (
            f'<span style="background:rgba(255,255,255,.15);padding:3px 10px;border-radius:4px;font-size:12px;">'
            f'{kd_count} KD · profile <code style="background:rgba(255,255,255,.2);padding:1px 5px;border-radius:3px;">{html.escape(profile)}</code>'
            f' · class {", ".join(html.escape(c) for c in kd_classes)}</span>'
        )

        # Cross-Genesor Nav-Banner direkt nach <body> mit Quick-Stats + Skin-Switcher
        accent_color = style["accent"]
        nav_banner = (
            f'<div style="background:{accent_color};color:#fff;padding:10px 18px;font-size:13px;'
            f'display:flex;gap:14px;align-items:center;flex-wrap:wrap;'
            f'font-family:{style["font_h"]};">'
            f'<a href="./index.html" style="color:#fff;text-decoration:none;font-weight:600;">🌱 Genesor</a>'
            f'<a href="./uc-{html.escape(repo_name)}.html" style="color:#fff;text-decoration:none;">'
            f'📋 Use Cases ({html.escape(repo_name)})</a>'
            f'<a href="./coverage.html" style="color:#fff;text-decoration:none;">'
            f'📊 Cross-Repo Coverage</a>'
            f'<span style="flex:1;"></span>'
            f'{stats_chip}'
            f'<select id="lineage-skin-select" '
            f'style="padding:4px 8px;border:1px solid rgba(255,255,255,.4);background:rgba(255,255,255,.1);color:#fff;border-radius:4px;font-size:12px;">'
            f'<option value="__default">🎨 Default</option>'
            f'<option value="__dark">Dark</option>'
            f'<option value="__print">Print (B/W)</option>'
            f'</select>'
            f'</div>'
            f'<script>'
            f'(function(){{'
            f'const K="lineage_skin";'
            f'function apply(v){{'
            f'document.body.classList.remove("skin-dark","skin-print");'
            f'if(v==="__dark")document.body.classList.add("skin-dark");'
            f'if(v==="__print")document.body.classList.add("skin-print");'
            f'try{{localStorage.setItem(K,v);}}catch(e){{}}'
            f'}}'
            f'let s="__default";try{{s=localStorage.getItem(K)||"__default";}}catch(e){{}}'
            f'const el=document.getElementById("lineage-skin-select");'
            f'if(el){{el.value=s;apply(s);el.addEventListener("change",e=>apply(e.target.value));}}'
            f'}})();'
            f'</script>'
            f'<style>'
            f'body.skin-dark{{background:#1f2937!important;color:#e5e7eb!important;}}'
            f'body.skin-dark .graph-wrap{{background:#111827!important;border-color:#374151!important;}}'
            f'body.skin-print *{{filter:grayscale(1);}}'
            f'</style>'
        )
        html_out = html_out.replace("<body>", "<body>" + nav_banner, 1)
        out_path = out_dir / f"lineage-{repo_name}.html"
        out_path.write_text(html_out, encoding="utf-8")
        written.append(out_path)
    return written


def build_screen_lineage_html(repo: str, kd_name: str, spec_data: dict,
                             profile: str, style: dict) -> str:
    """Standalone HTML-Page mit eingebettetem Mermaid-Screen-Lineage."""
    from datetime import date
    mermaid_body = emit_screen_lineage(spec_data)
    screens = spec_data.get("screens") or []
    n_screens = len([s for s in screens if isinstance(s, dict) and s.get("id")])
    title = (spec_data.get("title") or kd_name).split("—")[0].strip()
    klass = spec_data.get("class") or "?"

    # KEIN %%{init:}%% — Mermaid 10.9.6 strikt; mermaid.initialize() in JS reicht.
    # themeVariables werden im Init-JS unten gesetzt.
    accent = style["accent"]
    accent_bg = style["accent_bg"]
    return f"""<!DOCTYPE html>
<html lang="de"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Screen-Lineage · {html.escape(kd_name)} · {html.escape(repo)}</title>
<style>
  body {{ font-family: -apple-system, "Segoe UI", system-ui, sans-serif; margin: 0; padding: 0; background: #f5f7fa; color: #1f2937; }}
  .topbar {{ background: {accent}; color: #fff; padding: 12px 20px; display: flex; gap: 14px; align-items: center; flex-wrap: wrap; }}
  .topbar h1 {{ margin: 0; font-size: 18px; font-weight: 600; flex: 1; min-width: 200px; }}
  .topbar a {{ color: #fff; text-decoration: none; font-size: 13px; }}
  .topbar a:hover {{ text-decoration: underline; }}
  .topbar .badge {{ background: rgba(255,255,255,.15); padding: 3px 10px; border-radius: 4px; font-size: 12px; }}
  main {{ padding: 20px; max-width: 1300px; margin: 0 auto; }}
  .graph-wrap {{ background: #fff; border: 1px solid #e3e8ee; border-radius: 6px; padding: 18px; overflow-x: auto; }}
  .legend {{ background: #fff; border: 1px solid #e3e8ee; border-radius: 6px; padding: 12px 16px; margin-top: 12px; font-size: 13px; color: #4b5563; }}
  .legend table {{ border-collapse: collapse; }}
  .legend td {{ padding: 3px 12px; }}
  .legend code {{ background: #f3f4f6; padding: 1px 5px; border-radius: 3px; font-size: 12px; }}
</style>
<script src="https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js"></script>
</head><body>
<header class="topbar">
  <h1>🕸 Screen-Lineage · {html.escape(kd_name)}</h1>
  <a href="./render/{html.escape(repo)}-{html.escape(kd_name)}.html">📱 Mockup</a>
  <a href="./uc-{html.escape(repo)}.html?kd={html.escape(kd_name)}">📋 UCs</a>
  <a href="./lineage-{html.escape(repo)}.html">🌳 Repo-Lineage</a>
  <a href="./index.html">🌱 Genesor</a>
  <span style="flex:1;"></span>
  <span class="badge">{n_screens} Screens · class {html.escape(klass)} · profile {html.escape(profile)}</span>
</header>
<main>
<div class="graph-wrap">
<pre class="mermaid">
{mermaid_body}
</pre>
</div>
<div class="legend">
  <b>Legende:</b>
  <table>
    <tr><td><b>──→ solid</b></td><td><code>next_screens</code> (Workflow-Folge-Screen)</td></tr>
    <tr><td><b>-.-→ dashed</b></td><td><code>voraussetzung_screen</code> (Pre-Condition)</td></tr>
    <tr><td><b>-..→ dotted</b></td><td><code>cross_klickdummy_link</code> (Sprung zu anderem KD)</td></tr>
    <tr><td><b>Subgraph-Box</b></td><td>Halbschicht-Gruppierung</td></tr>
  </table>
</div>
<p style="color:#9ca3af;font-size:11px;margin-top:14px;">
  Auto-generiert aus <code>{html.escape(repo)}/klickdummy/{html.escape(kd_name)}/screens-spec.yaml</code>. Build: {date.today().isoformat()}.
</p>
</main>
<script>
  mermaid.initialize({{
    startOnLoad: true,
    theme: 'base',
    themeVariables: {{
      primaryColor: '{accent_bg}',
      primaryTextColor: '#1f2937',
      primaryBorderColor: '{accent}',
      lineColor: '{accent}',
      secondaryColor: '#fef3c7',
      tertiaryColor: '#f3f4f6',
      fontFamily: 'sans-serif'
    }},
    flowchart: {{ curve: 'basis' }}
  }});
</script>
</body></html>
"""


def build_repo_uc_index_html(repo: str, ucs_for_repo: list[dict], coverage: dict,
                            kds: list[dict] | None = None,
                            validation: dict[str, list[dict]] | None = None) -> str:
    """Pro-Repo UC-Index — Tabelle aller UCs des Repos mit Persona/Status/Coverage.

    Workshop-Feedback 2026-05-26: UCs sollten auf Repo-Ebene erreichbar sein,
    nicht nur cross-repo in der Heatmap. Diese Page ist von Genesor-Übersicht
    UND lineage-<repo>.html aus verlinkt.
    """
    from datetime import date
    ucs_sorted = sorted(ucs_for_repo, key=lambda u: u["uc_id"])
    real_count = coverage["uc_realized_count"]
    unres = coverage["uc_unresolved"]

    # ADR-Ref → KD-Name Lookup (cross-repo), damit data-kds saubere KD-Namen
    # enthält und der ?kd=-Filter matched (Bugfix Workshop 2026-05-26).
    adr_to_kd: dict[tuple[str, str], str] = {}
    for k in (kds or []):
        if k.get("kind", "spec") != "spec":
            continue
        adr_local = (k.get("data", {}).get("adr", {}) or {}).get("local") or ""  # noqa: F811
        if ":" in adr_local:
            adr_local = adr_local.split(":", 1)[1]
        if adr_local:
            adr_to_kd[(k["repo"], adr_local)] = k["kd"]

    validation = validation or {}
    rows = []
    for uc in ucs_sorted:
        gid = f"{uc['repo']}:{uc['uc_id']}"
        r = real_count.get(gid, 0)
        u_refs = unres.get(gid, [])
        findings = validation.get(gid, [])
        n_err = sum(1 for f in findings if f["severity"] == "error")
        n_warn = sum(1 for f in findings if f["severity"] == "warning")
        if n_err:
            health_chip = f'<details class="hf hf-err"><summary>❌ {n_err}e{(" " + str(n_warn) + "w") if n_warn else ""}</summary><ul>' + "".join(
                f'<li><b>{html.escape(f["code"])}</b>: {html.escape(f["msg"])}</li>' for f in findings
            ) + '</ul></details>'
        elif n_warn:
            health_chip = f'<details class="hf hf-warn"><summary>⚠ {n_warn}w</summary><ul>' + "".join(
                f'<li><b>{html.escape(f["code"])}</b>: {html.escape(f["msg"])}</li>' for f in findings
            ) + '</ul></details>'
        else:
            health_chip = '<span class="hf hf-ok" title="Validator-Layer A: alle Checks grün">✓</span>'
        status_chip = ""
        s = (uc.get("status") or "draft").lower()
        if s == "approved":
            status_chip = '<span class="st st-approved">approved</span>'
        elif s == "reviewed":
            status_chip = '<span class="st st-reviewed">reviewed</span>'
        else:
            status_chip = '<span class="st st-draft">draft</span>'
        cov_chip = (
            f'<span class="cov-{("high" if r >= 3 else "mid" if r == 2 else "low" if r == 1 else "none")}">'
            f'{r} Screen(s)</span>'
        )
        sek = uc.get("sekundaer") or []
        sek_str = ", ".join(sek) if isinstance(sek, list) else str(sek)
        # Frontmatter-Details collapsible
        details_inner = (
            f'<dt>FV-Bezug</dt><dd>{html.escape(uc.get("fv_bezug") or "—")}</dd>'
            f'<dt>Prio</dt><dd>{html.escape(uc.get("prio") or "—")}</dd>'
            f'<dt>Sekundäre Akteure</dt><dd>{html.escape(sek_str or "—")}</dd>'
            f'<dt>realisiert von</dt><dd><code>{html.escape(uc.get("realisiert_von") or "—")}</code></dd>'
            f'<dt>related_screens</dt><dd>'
            + (", ".join(f'<code>{html.escape(str(s))}</code>' for s in (uc.get("related_screens") or [])) or "—")
            + '</dd>'
        )
        if u_refs:
            details_inner += (
                '<dt style="color:#b91c1c;">⚠ unresolved</dt><dd style="color:#b91c1c;">'
                + ", ".join(f'<code>{html.escape(x)}</code>' for x in u_refs)
                + "</dd>"
            )
        try:
            rel_path = uc["source_file"].relative_to(_cfg.repos_root / repo)
            rel_path_str = str(rel_path)
            src_link = f'<a href="../{html.escape(repo)}/{html.escape(rel_path_str)}" target="_blank" class="src-link" title="Lokale MD-Datei">📄 source</a>'
            gh_edit = _github_edit_url(repo, rel_path_str)
            gh_delete = _github_delete_url(repo, rel_path_str)
            if gh_edit:
                edit_link = f'<a href="{html.escape(gh_edit)}" target="_blank" class="edit-link" title="In GitHub-Web-Editor öffnen">✏️ edit</a>'
                del_link = (
                    f'<a href="{html.escape(gh_delete)}" target="_blank" class="del-link" title="In GitHub löschen (Web-UI)">🗑️ delete</a>'
                    if gh_delete else ""
                )
                status_extra = '<span class="rem-ok" title="Datei ist in main getrackt">●&nbsp;remote</span>'
            else:
                edit_link = ""
                del_link = ""
                status_extra = '<span class="rem-local" title="Datei existiert nur lokal — erst commit+push für Edit-Link auf GitHub">⚠ lokal-only</span>'
        except (ValueError, KeyError):
            src_link = ""
            edit_link = ""
            del_link = ""
            status_extra = ""
        rows.append(
            f'<tr data-kds="{html.escape(",".join(_uc_kd_targets(uc, repo, adr_to_kd)))}">'
            f'<td><code>{html.escape(gid)}</code></td>'
            f'<td>{html.escape(uc["name"])}</td>'
            f'<td>{html.escape(str(uc.get("akteur") or "—"))}</td>'
            f'<td>{health_chip}</td>'
            f'<td>{status_chip} {status_extra}</td>'
            f'<td>{cov_chip}</td>'
            f'<td><details><summary>Details</summary><dl>{details_inner}</dl></details> {src_link} {edit_link} {del_link}</td>'
            f'</tr>'
        )

    n_realized = sum(1 for u in ucs_sorted if real_count.get(f"{u['repo']}:{u['uc_id']}", 0) > 0)

    return f"""<!DOCTYPE html>
<html lang="de"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>UC-Index · {html.escape(repo)} · Genesor</title>
<style>
  body {{ font-family: -apple-system, "Segoe UI", system-ui, sans-serif; margin: 0; padding: 20px; background: #f5f7fa; color: #1f2937; }}
  h1 {{ font-size: 20px; margin: 0 0 4px; }}
  .sub {{ font-size: 13px; color: #6b7280; margin-bottom: 14px; }}
  .sub a {{ color: #2563eb; text-decoration: none; }}
  .sub a:hover {{ text-decoration: underline; }}
  .badges span {{ display: inline-block; background: #eef2ff; color: #1e3a8a; padding: 3px 10px; border-radius: 4px; margin-right: 6px; font-size: 12px; }}
  table {{ width: 100%; border-collapse: collapse; background: #fff; font-size: 13px; border: 1px solid #e3e8ee; border-radius: 6px; overflow: hidden; }}
  th, td {{ border-bottom: 1px solid #e3e8ee; padding: 8px 10px; text-align: left; vertical-align: top; }}
  th {{ background: #f0f4f8; font-weight: 600; }}
  td code {{ background: #eef2ff; padding: 1px 5px; border-radius: 3px; font-size: 12px; }}
  .st {{ display: inline-block; padding: 1px 7px; border-radius: 3px; font-size: 11px; font-weight: 600; }}
  .st-draft    {{ background: #fef3c7; color: #92400e; }}
  .st-reviewed {{ background: #dbeafe; color: #1e40af; }}
  .st-approved {{ background: #d1fae5; color: #065f46; }}
  .cov-none {{ color: #9ca3af; }}
  .cov-low  {{ color: #92400e; font-weight: 600; }}
  .cov-mid  {{ color: #065f46; font-weight: 600; }}
  .cov-high {{ color: #064e3b; font-weight: 700; }}
  details {{ font-size: 12px; }}
  details summary {{ cursor: pointer; color: #2563eb; }}
  details dl {{ margin: 6px 0 0; padding-left: 6px; }}
  details dt {{ font-weight: 600; color: #374151; margin-top: 4px; font-size: 11px; }}
  details dd {{ margin: 1px 0 0 14px; color: #6b7280; font-size: 12px; }}
  .src-link {{ font-size: 11px; color: #6b7280; margin-left: 8px; text-decoration: none; }}
  .src-link:hover {{ text-decoration: underline; }}
  .edit-link {{ font-size: 11px; color: #2563eb; margin-left: 6px; text-decoration: none; background: #eef6ff; padding: 2px 6px; border-radius: 3px; }}
  .edit-link:hover {{ background: #dbeafe; }}
  .del-link {{ font-size: 11px; color: #b91c1c; margin-left: 4px; text-decoration: none; background: #fef2f2; padding: 2px 6px; border-radius: 3px; }}
  .del-link:hover {{ background: #fee2e2; }}
  .rem-ok {{ font-size: 10px; color: #16a34a; margin-left: 4px; }}
  .rem-local {{ font-size: 10px; color: #c2410c; margin-left: 4px; background: #fff7ed; padding: 1px 5px; border-radius: 3px; }}
  .hf {{ font-size: 11px; font-weight: 600; }}
  .hf-ok {{ color: #16a34a; }}
  .hf-warn summary {{ color: #92400e; cursor: pointer; }}
  .hf-err summary {{ color: #b91c1c; cursor: pointer; }}
  .hf ul {{ margin: 4px 0 0; padding-left: 18px; font-size: 11px; font-weight: normal; color: #374151; }}
  .hf li {{ margin-bottom: 2px; }}
</style></head><body>
<h1>📋 Use Cases · {html.escape(repo)}</h1>
<div class="sub">
  <a href="./index.html">← Genesor-Übersicht</a> ·
  <a href="./coverage.html">📊 Cross-Repo Coverage</a> ·
  <a href="./lineage-{html.escape(repo)}.html">🌳 Lineage</a>
</div>
<div class="badges" style="margin-bottom:14px;">
  <span>UCs in {html.escape(repo)}: {len(ucs_sorted)}</span>
  <span>mit Realisierung: {n_realized}/{len(ucs_sorted)}</span>
  <span>Konvention: ADR-211 Rev 16 §UC-Coverage</span>
</div>
<table>
  <thead><tr>
    <th>UC-ID</th><th>Name</th><th>Akteur</th><th title="Validator-Layer A: YAML, Pflichtfelder, Refs, Persona">Health</th><th>Status</th><th>Coverage</th><th>Details</th>
  </tr></thead>
  <tbody>{"".join(rows) or '<tr><td colspan="6" style="text-align:center;color:#9ca3af;padding:24px;">Noch keine UCs in diesem Repo. Generator: <code>python3 scripts/klickdummy_lineage.py --gen-uc-skeletons</code></td></tr>'}</tbody>
</table>
<p style="color:#9ca3af;font-size:11px;margin-top:14px;">
  UCs liegen unter <code>docs/use-cases/</code>. Frontmatter: <code>uc_id, name, primaer_akteur, related_screens</code> (ADR-211 Rev 16). Build: {date.today().isoformat()}
</p>
<script>
  // ?kd=<kd-name> Filter (Workshop 2026-05-26 #2)
  (function() {{
    const params = new URLSearchParams(location.search);
    const kd = params.get('kd');
    if (!kd) return;
    const rows = document.querySelectorAll('tbody tr');
    let hidden = 0, shown = 0;
    rows.forEach(tr => {{
      const targets = (tr.dataset.kds || '').split(',');
      // Matche auch ADR-Refs heuristisch — KD-Name passt zu KD oder Spec-ID
      const matches = targets.some(t => t === kd || t.endsWith('-' + kd) || t.startsWith(kd));
      if (matches) {{ shown++; }} else {{ tr.style.display = 'none'; hidden++; }}
    }});
    // Filter-Banner einblenden
    const banner = document.createElement('div');
    banner.style.cssText = 'background:#1e3a8a;color:#fff;padding:8px 14px;border-radius:4px;margin-bottom:12px;font-size:13px;display:flex;gap:14px;align-items:center;';
    banner.innerHTML = `<span>🔍 Filter: nur UCs für KD <code style="background:rgba(255,255,255,.2);padding:1px 6px;border-radius:3px;">${{kd}}</code> (${{shown}} sichtbar, ${{hidden}} ausgeblendet)</span><a href="?" style="color:#fff;text-decoration:underline;">× Filter entfernen</a>`;
    document.querySelector('h1').after(banner);
  }})();
</script>
</body></html>
"""


def build_coverage_html(ucs: list[dict], kds: list[dict], coverage: dict) -> str:
    """Cross-Repo UC × KD Coverage-Heatmap. ADR-211 Rev 15 §UC-Coverage.

    Zellen: Anzahl realized Screens pro (UC, KD). Klick auf Zelle zeigt die
    konkreten Screen-IDs. Footer listet UCs ohne Realisierung + unresolved Refs.
    """
    # KDs sortieren: nur spec-KDs, gruppiert nach repo
    spec_kds = sorted(
        [k for k in kds if k.get("kind", "spec") == "spec"],
        key=lambda k: (k["repo"], k["kd"]),
    )
    # UCs sortieren nach repo+uc_id
    ucs_sorted = sorted(ucs, key=lambda u: (u["repo"], u["uc_id"]))

    matrix = coverage["matrix"]
    uc_real_count = coverage["uc_realized_count"]
    uc_unresolved = coverage["uc_unresolved"]

    # Spalten-Header pro Repo gruppieren
    cols_by_repo: dict[str, list[dict]] = {}
    for k in spec_kds:
        cols_by_repo.setdefault(k["repo"], []).append(k)

    # Header-Rows (2 Reihen: repo, kd)
    repo_th = ['<th rowspan="2" class="uc-th">UC-ID</th>',
               '<th rowspan="2" class="uc-th">Name</th>',
               '<th rowspan="2" class="uc-th">Akteur</th>']
    for repo, kds_list in cols_by_repo.items():
        repo_th.append(f'<th colspan="{len(kds_list)}" class="repo-th">{html.escape(repo)}</th>')
    kd_th = []
    for repo, kds_list in cols_by_repo.items():
        for k in kds_list:
            kd_th.append(f'<th class="kd-th" title="{html.escape(k["kd"])}">{html.escape(k["kd"][:14])}</th>')

    # Body-Rows
    body_rows = []
    for uc in ucs_sorted:
        uc_gid = f"{uc['repo']}:{uc['uc_id']}"
        cells = [
            f'<td class="uc-id"><code>{html.escape(uc_gid)}</code></td>',
            f'<td class="uc-name">{html.escape(uc["name"][:60])}</td>',
            f'<td class="uc-akteur">{html.escape(str(uc["akteur"]))}</td>',
        ]
        for repo, kds_list in cols_by_repo.items():
            for k in kds_list:
                screens = matrix.get((uc_gid, k["repo"], k["kd"]), [])
                if not screens:
                    cells.append('<td class="cell cell-empty">·</td>')
                else:
                    n = len(screens)
                    cls = "cell-low" if n == 1 else ("cell-mid" if n == 2 else "cell-high")
                    sids = ", ".join(screens)
                    cells.append(
                        f'<td class="cell {cls}" title="Screens: {html.escape(sids)}">{n}</td>'
                    )
        body_rows.append(f'<tr>{"".join(cells)}</tr>')

    # Footer-Listen
    no_realized = [f"{uc['repo']}:{uc['uc_id']} — {uc['name']}"
                   for uc in ucs_sorted if uc_real_count.get(f"{uc['repo']}:{uc['uc_id']}", 0) == 0]
    unres_lines = []
    for gid, refs in sorted(uc_unresolved.items()):
        unres_lines.append(f"<li><code>{html.escape(gid)}</code>: {html.escape(', '.join(refs[:3]))}</li>")

    n_realized = sum(1 for v in uc_real_count.values() if v > 0)
    n_cells = sum(len(v) for v in matrix.values())

    from datetime import date
    return f"""<!DOCTYPE html>
<html lang="de"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>UC ↔ KD Coverage · Genesor</title>
<style>
  body {{ font-family: -apple-system, "Segoe UI", system-ui, sans-serif; margin: 0; padding: 20px; background: #f5f7fa; color: #1f2937; }}
  h1 {{ font-size: 20px; margin: 0 0 6px; }}
  .meta {{ font-size: 13px; color: #6b7280; margin-bottom: 16px; }}
  .nav a {{ font-size: 13px; color: #2563eb; text-decoration: none; }}
  .nav a:hover {{ text-decoration: underline; }}
  table {{ border-collapse: collapse; background: #fff; font-size: 12px; }}
  th, td {{ border: 1px solid #e3e8ee; padding: 5px 8px; text-align: left; }}
  th.uc-th {{ background: #f3f4f6; position: sticky; top: 0; z-index: 2; vertical-align: bottom; }}
  th.repo-th {{ background: #1e3a8a; color: #fff; text-align: center; font-size: 13px; }}
  th.kd-th {{ background: #e0e7ff; color: #1e3a8a; writing-mode: vertical-rl; transform: rotate(180deg); height: 100px; padding: 4px; font-size: 11px; }}
  td.uc-id code {{ background: #eef2ff; padding: 1px 4px; border-radius: 3px; }}
  td.uc-name {{ max-width: 280px; }}
  td.cell {{ text-align: center; font-weight: 600; width: 32px; cursor: help; }}
  .cell-empty {{ color: #d1d5db; }}
  .cell-low {{ background: #fef3c7; color: #92400e; }}
  .cell-mid {{ background: #d1fae5; color: #065f46; }}
  .cell-high {{ background: #6ee7b7; color: #064e3b; }}
  .badges span {{ display: inline-block; background: #eef2ff; color: #1e3a8a; padding: 3px 10px; border-radius: 4px; margin-right: 6px; font-size: 12px; }}
  .footer {{ margin-top: 20px; font-size: 12px; color: #6b7280; }}
  .footer h3 {{ font-size: 13px; color: #374151; margin: 12px 0 4px; }}
  .footer ul {{ margin: 0; padding-left: 18px; }}
  .info-banner {{ background: #eef6ff; border-left: 4px solid #2563eb; padding: 12px 14px; margin-bottom: 14px; border-radius: 4px; font-size: 13px; line-height: 1.5; }}
  .info-banner h3 {{ margin: 0 0 6px; font-size: 14px; color: #1e3a8a; }}
  .info-banner p {{ margin: 4px 0; }}
  .legend {{ display: inline-block; padding: 1px 7px; border-radius: 3px; font-weight: 600; font-size: 11px; margin: 0 4px; }}
  .legend.l-empty {{ background: #f3f4f6; color: #9ca3af; }}
  .legend.l-low {{ background: #fef3c7; color: #92400e; }}
  .legend.l-mid {{ background: #d1fae5; color: #065f46; }}
  .legend.l-high {{ background: #6ee7b7; color: #064e3b; }}
  details {{ margin-top: 14px; background: #fff; border: 1px solid #e3e8ee; border-radius: 4px; padding: 8px 12px; }}
  details summary {{ cursor: pointer; font-weight: 600; color: #2563eb; font-size: 13px; }}
  details[open] summary {{ margin-bottom: 8px; }}
  details dl {{ margin: 0; font-size: 12px; }}
  details dt {{ font-weight: 600; color: #374151; margin-top: 8px; }}
  details dd {{ margin: 2px 0 0 16px; color: #6b7280; }}
  details code {{ background: #f3f4f6; padding: 1px 4px; border-radius: 3px; font-size: 11px; }}
</style></head><body>
<h1>UC ↔ KD Coverage</h1>
<div class="info-banner">
  <h3>ℹ Was zeigt diese Heatmap?</h3>
  <p>Pro Zelle: <b>wie viele Screens</b> eines Klickdummies (Spalte) durch einen Use Case
     (Zeile) realisiert sind — aus <code>UC.related_screens</code> aufgelöst.</p>
  <p>Farbskala:
    <span class="legend l-empty">·</span> keine Zuordnung &nbsp;·&nbsp;
    <span class="legend l-low">1</span> ein Screen &nbsp;·&nbsp;
    <span class="legend l-mid">2</span> zwei Screens &nbsp;·&nbsp;
    <span class="legend l-high">3+</span> drei oder mehr Screens
  </p>
  <p style="color:#6b7280;font-size:12px;margin-top:6px;">
    Mouse-Over einer Zelle zeigt die konkreten Screen-IDs.
    UCs ohne Realisierung + nicht-auflösbare Refs siehe Footer.
  </p>
</div>
<details>
  <summary>📖 Glossar &amp; Konventionen (ADR-211 Rev 16 §UC-Coverage)</summary>
  <dl>
    <dt>Use Case (UC)</dt>
    <dd>Maschinen-lesbares Anforderungs-Artefakt im Repo, gespeichert als Markdown mit YAML-Frontmatter unter <code>docs/use-cases/</code>. Cross-Repo-Namespace: <code>&lt;repo&gt;:UC-NNN</code>.</dd>
    <dt>Klickdummy (KD)</dt>
    <dd>Renderer einer Klickdummy-Spec; aus <code>screens-spec.yaml</code> generiert. ADR-211.</dd>
    <dt>related_screens (UC-Feld)</dt>
    <dd>Liste von Refs im Format <code>&lt;prefix&gt;:ADR-NNN#screen-id</code> oder <code>&lt;prefix&gt;:&lt;spec-id&gt;#screen-id</code>. Wird bidirektional gegen Klickdummy-Specs gelintet.</dd>
    <dt>realisiert (Cell-Wert)</dt>
    <dd>Anzahl Screens des KDs, auf die der UC via <code>related_screens</code> verweist UND die im Klickdummy-Spec existieren.</dd>
    <dt>Unresolved Ref</dt>
    <dd>Eine <code>related_screens</code>-Ref zeigt auf einen Screen, der im Spec nicht (mehr) existiert — siehe Footer.</dd>
  </dl>
</details>
<div class="meta">
  <div class="nav"><a href="./index.html">← Genesor-Übersicht</a></div>
  <div class="badges" style="margin-top:8px;">
    <span>UCs: {len(ucs_sorted)}</span>
    <span>KDs: {len(spec_kds)}</span>
    <span>realisiert: {n_realized}/{len(ucs_sorted)}</span>
    <span>UC×Screen-Coverage-Zellen: {n_cells}</span>
  </div>
</div>
<table>
  <thead><tr>{"".join(repo_th)}</tr><tr>{"".join(kd_th)}</tr></thead>
  <tbody>{"".join(body_rows)}</tbody>
</table>
<div class="footer">
  <h3>UCs ohne Realisierung ({len(no_realized)})</h3>
  <ul>{"".join(f"<li>{html.escape(n)}</li>" for n in no_realized) or "<li>—</li>"}</ul>
  <h3>UCs mit nicht-auflösbaren Refs ({len(uc_unresolved)})</h3>
  <ul>{"".join(unres_lines) or "<li>—</li>"}</ul>
  <p style="margin-top:14px;">Coverage gemäß ADR-211 Rev 15 §UC-Coverage. Refs-Format: <code>&lt;prefix&gt;:ADR-NNN#screen-id</code>. Build: {date.today().isoformat()}</p>
</div>
</body></html>
"""


# _inspect_django_models, _detect_tenant_pattern, _detect_auth_user_model,
# _inspect_dev_run, _inspect_infra_context — imported from .genesor.introspect_django above.


def build_impl_brief(record: dict, screen_id: str) -> str | None:
    """Implementation-Brief für 1 Screen — LLM-Prompt-tauglich.

    Pilot ADR-211 Rev 17 §Implementation-Bridge (Variante 3, lokaler Pilot
    aus ausschreibungs-hub:docs/analysen/implementation-brief-konzept.md).

    Input: KD-Record + screen-id. Output: strukturiertes Markdown mit allen
    Bausteinen für End-to-End-Generierung (Klickdummy-Kontext, Datenmodell
    typisiert, API-Vertrag, User-Flow, Given/When/Then-Tests, Errors, NFRs,
    UI-Schema, Audit-Log, Existing-Models-Bezug, Tech-Stack).

    Returns None wenn der Screen kein implementation_brief-Block hat.
    """
    import yaml as _yaml
    from datetime import date
    repo = record["repo"]
    kd_name = record["kd"]
    d = record.get("data") or {}
    screens = d.get("screens") or []
    screen = next((s for s in screens if isinstance(s, dict) and s.get("id") == screen_id), None)
    if not screen:
        return None
    brief = screen.get("implementation_brief")
    if not brief:
        return None

    title = screen.get("title", screen_id)
    personas = screen.get("persona") or []
    if isinstance(personas, str):
        personas = [personas]
    halbschicht = screen.get("halbschicht") or "?"
    fokus = screen.get("fokus") or []
    konsumiert = screen.get("konsumiert_entities") or []
    next_screens = screen.get("next_screens") or []
    voraussetzung = screen.get("voraussetzung_screen") or "—"

    # Entity-Definitions für konsumierte Entities (typisiert wenn vorhanden)
    entities_local = (d.get("local_entities") or {})
    entities_root = (d.get("root_entities") or {})
    entities_all = {**entities_root, **entities_local}

    def _entity_block(ename: str) -> str:
        edef = entities_all.get(ename)
        if not isinstance(edef, dict):
            return f"### {ename}\n\n*Entity nicht im Spec deklariert.*\n"
        desc = edef.get("description", "")
        typed = edef.get("fields_typed")
        treat = edef.get("consumers_must_treat_as", "—")
        out = [f"### {ename}\n", f"**Description:** {desc}", f"**Consumer-Vertrag:** `{treat}`\n"]
        if typed and isinstance(typed, dict):
            out.append("**Django-Field-Types:**\n```yaml")
            out.append(_yaml.dump({ename: typed}, default_flow_style=False, sort_keys=False, allow_unicode=True).rstrip())
            out.append("```")
        else:
            fields = edef.get("fields") or []
            out.append("**Felder (untyped — `fields_typed` fehlt im Spec):**")
            for f in fields:
                if isinstance(f, str):
                    out.append(f"- `{f}`")
                elif isinstance(f, dict):
                    out.append(f"- `{f.get('name', '?')}`: {f}")
        return "\n".join(out) + "\n"

    # API-Block formatieren
    api_block_yaml = _yaml.dump({"api": brief.get("api", {})}, default_flow_style=False, sort_keys=False, allow_unicode=True).rstrip()
    tests_block_yaml = _yaml.dump({"tests": brief.get("tests", [])}, default_flow_style=False, sort_keys=False, allow_unicode=True).rstrip()
    nfrs_block_yaml = _yaml.dump({"nfrs": brief.get("nfrs", {})}, default_flow_style=False, sort_keys=False, allow_unicode=True).rstrip()
    ui_block_yaml = _yaml.dump({"ui": brief.get("ui", {})}, default_flow_style=False, sort_keys=False, allow_unicode=True).rstrip()
    audit_block_yaml = _yaml.dump({"audit_log": brief.get("audit_log", {})}, default_flow_style=False, sort_keys=False, allow_unicode=True).rstrip()

    tech = brief.get("tech_stack", {})
    existing_models_declared = brief.get("existing_models", [])
    out_of_scope = brief.get("out_of_pilot_scope", [])
    ki_rel = brief.get("ki_relevant")
    htmx_response = brief.get("htmx_response", "json")  # default — explizit machen!

    entities_section = "\n".join(_entity_block(e) for e in konsumiert)

    # Model-Introspection (Iter-v2, Lesson-Learned)
    inspected = _inspect_django_models(repo)
    tenant_info = _detect_tenant_pattern(inspected)
    auth_user_model = _detect_auth_user_model(repo)
    # Iter-v3: Dev-Run + Infra (Lessons #6/#7/#8)
    dev_run = _inspect_dev_run(repo)
    infra_ctx = _inspect_infra_context()

    # Existing-Models-Section mit AUTO-Field-Detail (statt User-Stub)
    existing_models_lines = []
    for decl in existing_models_declared:
        app = decl.get("app", "?")
        model = decl.get("model", "?")
        key = f"{app}.{model}"
        existing_models_lines.append(f"### `{key}`")
        existing_models_lines.append(f"\n**Relation:** {decl.get('relation', '—')}\n")
        live = inspected.get(key)
        if live:
            existing_models_lines.append(f"**Auto-introspectiert aus** `{live['source_path']}`:")
            existing_models_lines.append("\n| Field | Type | Args/Kwargs |")
            existing_models_lines.append("|---|---|---|")
            for fname, fdef in live["fields"].items():
                ftype = fdef["type"]
                args_str = ", ".join(fdef["args"][:3])
                kw_str = ", ".join(f"{k}={v}" for k, v in list(fdef["kwargs"].items())[:4])
                detail = " | ".join([s for s in [args_str, kw_str] if s])
                existing_models_lines.append(f"| `{fname}` | `{ftype}` | {detail or '—'} |")
            existing_models_lines.append("")
        else:
            existing_models_lines.append("⚠ **Im Repo NICHT gefunden** — Brief-Declaration ist möglicherweise falsch (Spec-Drift)\n")
    existing_models_section = "\n".join(existing_models_lines) or "*Keine.*"

    # Drift-Sektion: KD-Spec ↔ echtes Model — immer Output (auch wenn fields_typed fehlt)
    drift_lines = []
    for ename in konsumiert:
        edef = entities_all.get(ename) or {}
        spec_fields_typed = edef.get("fields_typed", {}) or {}
        spec_fields_untyped = [
            (f if isinstance(f, str) else (f.get("name", "?") if isinstance(f, dict) else str(f)))
            for f in (edef.get("fields") or [])
        ]
        # Match-Heuristik: snake_case → CamelCase
        candidates = [k for k in inspected.keys() if k.split(".", 1)[1].lower() == ename.lower()]
        if not candidates:
            candidates = [k for k in inspected.keys() if k.split(".", 1)[1].lower().rstrip("e") == ename.lower().rstrip("e")]
        if not candidates:
            drift_lines.append(f"### `{ename}` — KD-lokale Entity (kein passendes Real-Model)")
            if spec_fields_typed:
                drift_lines.append(f"\n*Spec hat `fields_typed` ({len(spec_fields_typed)} Felder) — Implementierung erzeugt Model neu in §3.*\n")
            else:
                drift_lines.append(f"\n*Spec hat nur `fields`-Liste ({len(spec_fields_untyped)} Felder) ohne Typen — Implementation muss Field-Types selbst wählen.*\n")
            continue
        real_key = candidates[0]
        real_fields = inspected[real_key]["fields"]
        real_keys = set(real_fields.keys())
        drift_lines.append(f"### `{ename}` ↔ `{real_key}`")
        drift_lines.append(f"\n**Real-Model-Pfad:** `{inspected[real_key]['source_path']}`")
        if spec_fields_typed:
            spec_keys = set(spec_fields_typed.keys())
            only_in_spec = spec_keys - real_keys
            only_in_real = real_keys - spec_keys
            common = spec_keys & real_keys
            drift_lines.append(f"\n**Gemeinsame Felder:** {', '.join(f'`{f}`' for f in sorted(common)) or '—'}")
            if only_in_spec:
                drift_lines.append(f"\n**Nur im KD-Spec (Spec-Drift, Real fehlt):** {', '.join(f'`{f}`' for f in sorted(only_in_spec))}")
            if only_in_real:
                drift_lines.append(f"\n**Nur im Real-Model (KD vereinfacht):** {', '.join(f'`{f}`' for f in sorted(only_in_real))}")
        else:
            # KD untyped — zeige Match + Real-Surplus
            spec_keys = set(spec_fields_untyped)
            only_in_spec = spec_keys - real_keys
            only_in_real = real_keys - spec_keys
            common = spec_keys & real_keys
            drift_lines.append("\n⚠ **KD-Spec hat keine `fields_typed`** (nur Field-Namen-Liste) — Drift-Check Field-Name-only.")
            drift_lines.append(f"\n**Match Spec ↔ Real (Name-only):** {', '.join(f'`{f}`' for f in sorted(common)) or '—'}")
            if only_in_spec:
                drift_lines.append(f"\n**KD nennt Felder die Real-Model NICHT hat:** {', '.join(f'`{f}`' for f in sorted(only_in_spec))} — Spec-Drift, ggf. Cleanup oder Mapping nötig")
            if only_in_real:
                drift_lines.append(f"\n**Real-Model hat {len(only_in_real)} Felder die KD-Spec NICHT erwähnt** (KD vereinfacht; Engineering ergänzt aus Real-Stand):")
                # Top-10 Felder zeigen
                for rfield in sorted(only_in_real)[:10]:
                    rtype = real_fields[rfield]["type"]
                    drift_lines.append(f"  - `{rfield}: {rtype}`")
                if len(only_in_real) > 10:
                    drift_lines.append(f"  - … +{len(only_in_real) - 10} weitere")
        drift_lines.append("")
    drift_section = "\n".join(drift_lines) or "*Keine konsumierten Entities deklariert — kein Drift-Check möglich.*"

    # Tenant-Hint
    tenant_hint = ""
    if tenant_info.get("active"):
        tenant_hint = (
            f"\n> 🚨 **Multi-Tenant-Repo** ({tenant_info['count']} Models mit `tenant_id`): "
            f"{tenant_info['rationale']}\n"
        )

    return f"""# Implementation-Brief — `{repo}:{kd_name}#{screen_id}`

> Auto-generiert via `klickdummy_lineage.py --gen-impl-brief` ({date.today().isoformat()})
> Pattern-Quelle: `ausschreibungs-hub:docs/analysen/implementation-brief-konzept.md` (Variante 3, Pilot)
> Konformität: `platform:ADR-211` Rev 16

## 1. Klickdummy-Kontext

| | |
|---|---|
| Repo | `{repo}` |
| Klickdummy | `{kd_name}` |
| Screen-ID | `{screen_id}` |
| Title | {title} |
| Personas | {", ".join(personas) or "—"} |
| Halbschicht | `{halbschicht}` |
| Voraussetzungs-Screen | `{voraussetzung}` |
| Folge-Screens | {", ".join(f"`{n}`" for n in next_screens) or "—"} |
| KI-relevant | `{ki_rel}` |

### Fokus-Bullets (Quelle: Klickdummy-Spec)

{chr(10).join("- " + str(f) for f in fokus) or "—"}

## 2. Tech-Stack

```yaml
{_yaml.dump(tech, default_flow_style=False, sort_keys=False, allow_unicode=True).rstrip()}
```

## 3. Datenmodell (typisiert)

{entities_section or "*Keine konsumierten Entities deklariert.*"}

## 4. API-Vertrag

```yaml
{api_block_yaml}
```

## 5. Akzeptanz-Tests (Given/When/Then)

```yaml
{tests_block_yaml}
```

## 6. Performance-NFRs

```yaml
{nfrs_block_yaml}
```

## 7. UI-Komponenten-Schema

```yaml
{ui_block_yaml}
```

## 8. Audit-Log + Compliance

```yaml
{audit_block_yaml}
```

## 9. Bezug zu bestehenden Django-Models (auto-introspectiert aus Repo)

{tenant_hint}
**`AUTH_USER_MODEL` im Repo:** `{auth_user_model}`

{existing_models_section}

## 10. §Genesor-vs-Realität-Drift (Spec ↔ Echtes Model)

Diese Sektion zeigt **systematisch**, wo Klickdummy-Spec und Implementierungs-
Realität abweichen — wertvoll für Brief-Iteration v2 und Spec-Pflege.

{drift_section}

## 11. Dev-Run (Pilot-Lesson #6 — wie startet die App?)

```yaml
{_yaml.dump({"dev_run": dev_run}, default_flow_style=False, sort_keys=False, allow_unicode=True).rstrip()}
```

**Schnellstart-Sequenz:**
1. `cd {dev_run.get("repo_path", "~/github/" + repo)}`
2. `{dev_run.get("requirements_install", "pip3 install --break-system-packages -r requirements.txt")}`
3. `{dev_run.get("start_command", "python3 manage.py runserver 0.0.0.0:" + str(dev_run.get("http_port", 8000)))}`
4. Test: `curl {dev_run.get("test_url", "http://localhost:8000/healthz/")}`
5. Pilot-Login: **admin / admin123** auf `http://<host>:{dev_run.get("http_port", 8000)}/admin/login/`

{"⚠ **Requirements-Drift:** pyproject.toml hat Deps die in requirements.txt fehlen: " + ", ".join("`" + d + "`" for d in dev_run.get("requirements_drift", [])) + chr(10) if dev_run.get("requirements_drift") else ""}

## 12. Infrastructure-Kontext (Pilot-Lessons #7 + #8)

```yaml
{_yaml.dump({"infra_context": infra_ctx}, default_flow_style=False, sort_keys=False, allow_unicode=True).rstrip()}
```

**Port-Konflikt-Check:** Brief-Port `{dev_run.get("http_port", "?")}` vs. live-Listener im Workspace —
{("⚠ **belegt!** durch " + ", ".join(p["app"] for p in (infra_ctx.get("port_neighbors") or []) if p.get("port") == dev_run.get("http_port"))) if any(p.get("port") == dev_run.get("http_port") for p in (infra_ctx.get("port_neighbors") or [])) else "✓ frei laut INFRASTRUCTURE.md"}

**Cloud-Firewall:** {("Public-Port `" + str(dev_run.get("http_port", "?")) + "` ist " + ("✓ bereits offen" if dev_run.get("http_port") in (infra_ctx.get("cloud_firewall_default_open") or []) else "❌ **muss geöffnet werden** via `~/github/bin/hetzner-fw-open.sh " + str(dev_run.get("http_port", "")) + "`")) if dev_run.get("http_port") and infra_ctx.get("cloud_firewall_id") else "—"}

## 13. NICHT im MVP-Pilot

{chr(10).join("- " + str(s) for s in out_of_scope) or "—"}

---

## LLM-Generierungs-Anweisung

Du baust eine **Django-App** namens `{tech.get("django_app", "submission_workflow")}` in `apps/{tech.get("django_app", "submission_workflow")}/`. Erzeuge ein Skelett mit:

1. **`models.py`** — neue Models exakt gemäß §3 Datenmodell + **Multi-Tenant-Felder** wo §9 das Pattern zeigt (z. B. `tenant_id: BigIntegerField(db_index=True)`).
2. **`views.py`** — gemäß §4 API-Vertrag. Multipart, SHA256, Error-Codes. **Berechtigungs-Check via Tenant-Membership** (siehe §9 Hint, NICHT direkter User-FK).
3. **`urls.py`** — Routen aus §4.
4. **`templates/{tech.get("django_app", "submission_workflow")}/{screen_id}.html`** — HTMX-Template gemäß §7. **`htmx_response: {htmx_response}`** — View MUSS entsprechend rendern (html-partial: Template-Render mit `_partial.html`; json: JsonResponse).
5. **`templates/{tech.get("django_app", "submission_workflow")}/_upload_status.html`** — nur wenn `htmx_response: html-partial`.
6. **`tests/test_{screen_id}.py`** — pytest-Django gemäß §5 Given/When/Then.
7. **`migrations/0001_initial.py`** — auto via `makemigrations`.
8. **`admin.py`** — Django-Admin-Registrierung.

**Constraints:**
- §9 zeigt **echte** Model-Field-Listen aus Repo-Introspection. **KEINE Halluzinationen** zu Feldnamen/Types — entweder aus §9 übernehmen oder TODO-Stub.
- §10 zeigt Spec↔Real-Drift. Wo Spec Felder vorsieht die im Real-Model fehlen: **neue Models bauen**, nicht in fremde Models reinpfuschen.
- Wo §9 ein Multi-Tenant-Pattern zeigt: **JEDES neue Model bekommt `tenant_id`** + Views filtern darauf.
- Out-of-Pilot-Scope-Features (§11): TODO-Stub.

**Output-Format:**
Pro Datei ein Code-Block mit Pfad im Header (`# apps/{tech.get("django_app", "submission_workflow")}/models.py`). Knapp halten.
"""


def build_impl_brief_html(brief_md: str, repo: str, kd_name: str, screen_id: str,
                          profile: str, style: dict) -> str:
    """Implementation-Brief Markdown → HTML mit CD + Genesor-Topbar + Side-Nav."""
    import markdown as _md
    from datetime import date
    body_html = _md.markdown(
        brief_md,
        extensions=["tables", "fenced_code", "attr_list", "sane_lists", "toc"],
    )
    accent = style["accent"]
    accent_bg = style["accent_bg"]
    font_h = style["font_h"]
    return f"""<!DOCTYPE html>
<html lang="de"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Impl-Brief · {html.escape(kd_name)}#{html.escape(screen_id)}</title>
<style>
  body {{ font-family: -apple-system, "Segoe UI", system-ui, sans-serif; margin: 0; padding: 0; background: #f5f7fa; color: #1f2937; line-height: 1.55; }}
  header.topbar {{ background: {accent}; color: #fff; padding: 12px 20px; display: flex; gap: 14px; align-items: center; flex-wrap: wrap; }}
  header.topbar h1 {{ margin: 0; font-size: 18px; font-weight: 600; flex: 1; min-width: 200px; }}
  header.topbar a {{ color: #fff; text-decoration: none; font-size: 13px; }}
  header.topbar a:hover {{ text-decoration: underline; }}
  header.topbar .badge {{ background: rgba(255,255,255,.15); padding: 3px 10px; border-radius: 4px; font-size: 12px; }}
  main {{ max-width: 1100px; margin: 0 auto; padding: 24px; background: #fff; }}
  main h1 {{ font-family: {font_h}; color: {accent}; font-size: 22pt; margin: 0 0 6pt; border-bottom: 2px solid {accent_bg}; padding-bottom: 6pt; }}
  main h2 {{ font-family: {font_h}; color: {accent}; font-size: 16pt; margin: 18pt 0 6pt; border-bottom: 1px solid {accent_bg}; padding-bottom: 3pt; }}
  main h3 {{ font-family: {font_h}; color: #374151; font-size: 13pt; margin: 12pt 0 4pt; }}
  main p, main li {{ font-size: 12pt; color: #1f2937; }}
  main code {{ background: #f3f4f6; padding: 1px 5px; border-radius: 3px; font-family: 'Menlo', 'Monaco', monospace; font-size: 11pt; }}
  main pre {{ background: #f8fafc; border: 1px solid #e3e8ee; padding: 12px; border-radius: 4px; overflow-x: auto; font-size: 11pt; }}
  main pre code {{ background: transparent; padding: 0; }}
  main table {{ border-collapse: collapse; width: 100%; margin: 8pt 0; }}
  main th, main td {{ border: 1px solid #d1dce8; padding: 6pt 10pt; text-align: left; vertical-align: top; }}
  main th {{ background: {accent_bg}; color: {accent}; font-weight: 600; }}
  blockquote {{ border-left: 4px solid {accent}; background: {accent_bg}; padding: 8px 14px; margin: 10pt 0; color: #374151; font-size: 11pt; }}
  hr {{ border: none; border-top: 1px solid #d1dce8; margin: 14pt 0; }}
  .copy-prompt-btn {{ position: fixed; bottom: 20px; right: 20px; background: {accent}; color: #fff; padding: 10px 18px; border-radius: 6px; cursor: pointer; font-size: 13px; box-shadow: 0 4px 12px rgba(0,0,0,.15); border: none; }}
  .copy-prompt-btn:hover {{ opacity: 0.9; }}
</style></head><body>
<header class="topbar">
  <h1>📑 Implementation-Brief · {html.escape(kd_name)}#{html.escape(screen_id)}</h1>
  <a href="./render/{html.escape(repo)}-{html.escape(kd_name)}.html">📱 Mockup</a>
  <a href="./screen-lineage-{html.escape(repo)}-{html.escape(kd_name)}.html">🕸 Screen-Lineage</a>
  <a href="./uc-{html.escape(repo)}.html?kd={html.escape(kd_name)}">📋 UCs</a>
  <a href="./impl-brief/{html.escape(repo)}-{html.escape(kd_name)}-{html.escape(screen_id)}.md">📄 Raw .md</a>
  <a href="./index.html">🌱 Genesor</a>
  <span class="badge">profile {html.escape(profile)} · {date.today().isoformat()}</span>
</header>
<main>
{body_html}
</main>
<button class="copy-prompt-btn" onclick="copyPrompt()">📋 Brief → Zwischenablage (für LLM-Prompt)</button>
<script>
  async function copyPrompt() {{
    try {{
      const resp = await fetch('./impl-brief/{html.escape(repo)}-{html.escape(kd_name)}-{html.escape(screen_id)}.md');
      const text = await resp.text();
      await navigator.clipboard.writeText(text);
      const btn = document.querySelector('.copy-prompt-btn');
      btn.textContent = '✓ kopiert!';
      setTimeout(() => btn.textContent = '📋 Brief → Zwischenablage (für LLM-Prompt)', 2000);
    }} catch (e) {{
      alert('Fehler beim Kopieren: ' + e.message);
    }}
  }}
</script>
</body></html>
"""


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

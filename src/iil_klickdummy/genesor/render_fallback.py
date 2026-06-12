"""Render-Fallback — generierter Mockup-HTML-Ersatz aus der Spec.

Extrahiert aus lineage.py (KONZ-003 Empf-1, PR4) — Code-Motion;
einzige Anpassungen: _cfg→get_cfg() (Importbindung) und __file__-Pfadtiefe.
"""
from __future__ import annotations

import html
from pathlib import Path
from .config import _DOMAIN_STYLES, get_cfg
from .scan import detect_org, get_org_registry, read_doc_profile, url_for_path
from .synth import _entities_lookup, _synth_entity_table
from .validate import compute_acceptance_status, merge_acceptance
from .render_common import FEEDBACK_WIDGET_JS, SKIN_SWITCHER_JS, STORY_BANNER_JS, build_skin_switcher_html, build_trace_strip, skin_library


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
    repo_dir = get_cfg().repos_root / repo
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

    # App-Name: platform-Registry-SSoT (meta.app_display_names, ADR-234) —
    # ohne platform-Checkout greift die Code-Map (gleiche Werte, Stand 2026-06).
    reg = get_org_registry()
    app_name_map = (reg or {}).get("app_display_names") or {
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
        spec_rel = str(record["path"].relative_to(get_cfg().repos_root))
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

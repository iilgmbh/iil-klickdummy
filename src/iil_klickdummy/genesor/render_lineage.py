"""Lineage-Seiten — Single-Repo-Graph, per-Repo-Lineages, Screen-Lineage.

Extrahiert aus lineage.py (KONZ-003 Empf-1, PR4) — Code-Motion;
einzige Anpassungen: _cfg→get_cfg() (Importbindung) und __file__-Pfadtiefe.
"""
from __future__ import annotations

import html
from pathlib import Path
from .config import _DOMAIN_STYLES, get_cfg
from .mermaid import emit_mermaid, emit_screen_lineage, node_id
from .scan import find_contracts_in_dir, read_doc_profile


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
        contracts_dir_a = get_cfg().repos_root / repo_name / "docs" / "01-architektur" / "contracts"
        contracts_dir_b = get_cfg().repos_root / repo_name / "contracts"
        repo_contracts: dict[str, Path] = {}
        for cd in (contracts_dir_a, contracts_dir_b):
            repo_contracts.update(find_contracts_in_dir(cd))
        # CD-Upgrade (2026-05-26): doc-profile-basierter Style + Click-Direktiven
        repo_dir = get_cfg().repos_root / repo_name
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

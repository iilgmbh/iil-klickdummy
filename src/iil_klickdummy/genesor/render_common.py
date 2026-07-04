"""Gemeinsame Render-Bausteine — Widget-/Banner-JS, Skin-Switcher, Trace-Strip.

Extrahiert aus lineage.py (KONZ-003 Empf-1, PR4) — Code-Motion;
einzige Anpassungen: _cfg→get_cfg() (Importbindung) und __file__-Pfadtiefe.
"""

from __future__ import annotations

import html
from pathlib import Path
from ..gen_e2e import is_fragile_selector, render_assertion
from .config import SKIN_LIBRARY_REL, _skin_url
from .scan import detect_org


# Kanonisches Feedback-Widget (widget.js, PAT-Modal + GitHub-direct) — wird in den
# Render injiziert (platform:ADR-211 Rev 13), ersetzt das alte inline-Widget.
try:
    FEEDBACK_WIDGET_JS = (
        # genesor/ liegt eine Ebene unter dem Paket → ein .parent mehr als in lineage.py
        Path(__file__).resolve().parent.parent
        / "snippets"
        / "feedback-widget"
        / "widget.js"
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
        sel = " selected" if value == initial_value else ""
        options.append(
            f'<option value="{html.escape(value)}"{sel}>{html.escape(label)}</option>'
        )
    return (
        '<div class="style-switch">'
        '<label for="skin-select">🎨 Style</label>'
        f'<select id="skin-select">{"".join(options)}</select>'
        "</div>"
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
    persona = (
        ", ".join(persona_raw)
        if isinstance(persona_raw, list)
        else str(persona_raw or "—")
    )

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
            f"&anker={quote(anker)}"
            f"&daten={quote(daten)}"
            f"&persona={quote(persona)}"
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
    s: dict,
    klass: str,
    role: str,
    accept_status: dict,
    repo: str = "",
    kd_name: str = "",
    sid: str = "",
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
            + (
                f" — {html.escape(str(_title))}"
                if _title and _title != _sid_display
                else ""
            )
            + '<span class="tr-screen-subtab"></span>'
            + "</span>"
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
        items = "".join(f"<li>{html.escape(u)}</li>" for u in ucs)
        uc_val = (
            f'<details class="tr-uc-details"><summary>{len(ucs)} UC(s)'
            f' <span class="tr-dim">({html.escape(uc_src)})</span></summary>'
            f'<ul class="tr-uc-list">{items}</ul></details>'
        )
        row("📋", "Use Cases", uc_val)
    else:
        row(
            "📋",
            "Use Cases",
            "nicht deklariert" + act("use-case", "+ UC anlegen"),
            missing=True,
        )

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
            val += ' · <span class="tr-dim">Felder:</span> ' + html.escape(
                ", ".join(df_parts)
            )
        row("📦", "Daten", val)
    else:
        row("📦", "Daten", "keine Entities/Datenfelder deklariert", missing=True)

    # 🏷 Status — class/role/off-ramp/pipeline
    ors = s.get("off_ramp_status")
    pipeline = s.get("pipeline_status") or "klickdummy"
    status_bits = [
        f"class <b>{html.escape(klass)}</b>",
        f"role <b>{html.escape(role)}</b>",
        f"pipeline <b>{html.escape(str(pipeline))}</b>",
    ]
    if ors:
        status_bits.insert(2, f"off-ramp <b>{html.escape(str(ors))}</b>")
        row("🏷", "Status", " · ".join(status_bits))
    else:
        row(
            "🏷",
            "Status",
            " · ".join(status_bits)
            + " · <span class='tr-miss-inline'>off-ramp fehlt</span>"
            + act("off-ramp", "+ off-ramp"),
        )

    # ✓ Abnahme — who/when je Achse
    acc_parts = []
    for axis, info in (accept_status or {}).items():
        label = "PO-Sign-Off" if axis == "spec_signed" else "Workshop-Walk"
        st = info.get("status")
        if st == "signed":
            acc_parts.append(
                f"✓ {label}: {html.escape(info.get('latest_by') or '?')} · {info.get('latest_date')} ({info.get('age_days')}d)"
            )
        elif st == "stale":
            acc_parts.append(
                f"⚠ {label}: {info.get('age_days')}d alt — neue Abnahme empfohlen"
            )
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
            val += ' · <span class="tr-dim">prose-only:</span> ' + html.escape(
                ", ".join(prose_ids)
            )
        if fragile_ids:
            val += ' · <span class="tr-miss-inline">fragil:</span> ' + html.escape(
                ", ".join(fragile_ids)
            )
        row("🎯", "Coverage (I1)", val)
    else:
        row(
            "🎯",
            "Coverage (I1)",
            "keine parity_acceptance-Checks" + act("parity", "+ Parity"),
            missing=True,
        )

    # ❓ Validierungsfrage — echter Text
    vf = s.get("validierungsfrage")
    if vf:
        row("❓", "Validierung", f"»{html.escape(str(vf))}«")

    return (
        '<div class="trace-strip" aria-label="Spec-Sicht (X-Ray)">'
        '<div class="trace-label">🔍 Spec-Sicht <span class="tr-dim">— spec-abgeleitet, in Prod ausgeblendet</span></div>'
        + "".join(rows)
        + "</div>"
    )

"""Genesor-Hauptansicht — build_genesor_html, zerlegt in Sub-Renderer (Empf-1c, PR5).

Extrahiert aus lineage.py (KONZ-003 Empf-1, PR4) — Code-Motion;
einzige Anpassungen: _cfg→get_cfg() (Importbindung) und __file__-Pfadtiefe.
"""

from __future__ import annotations

import html
from .config import get_cfg
from .scan import (
    _load_iil_apps_index,
    detect_org,
    find_mockup_html,
    kunde_from,
    url_for_path,
)
from .validate import (
    _ACCEPTANCE_AXES,
    _compute_drift_status,
    _extract_screen_routes,
    build_kd_registry,
    compute_acceptance_status,
    compute_sunset_badge,
    validate_kd,
)
from .render_common import skin_library


def _org_chip(o: str) -> str:
    return f'<span class="org-chip org-{html.escape(o)}">{html.escape(o)}</span>'


def _role_chip(r: str) -> str:
    return (
        f'<span class="role-{r}">{r}</span>'
        if r in {"root", "hybrid"}
        else '<span class="role-default">—</span>'
    )


# ---- Detail-Panel-Renderer ----
def _render_kd_detail(
    r: dict, idx: int, records: list[dict], all_warnings: dict[int, list[dict]]
) -> str:
    d = r["data"]
    warnings = all_warnings.get(idx, [])

    # Warnings-Block oben im Panel (F3/F4-Output)
    warn_html = ""
    if warnings:
        items = []
        for w in warnings:
            sev_class = "warn-error" if w["severity"] == "error" else "warn-warning"
            icon = "❌" if w["severity"] == "error" else "⚠"
            items.append(
                f'<li class="{sev_class}">{icon} <b>{w["code"]}</b> · {html.escape(w["msg"])}</li>'
            )
        warn_html = f'<div class="warnings"><h4>Drift-Validierung ({len(warnings)})</h4><ul class="compact">{"".join(items)}</ul></div>'

    # F11 — Render-only-KDs: anderes Detail (kein Spec)
    if r.get("kind", "spec") != "spec":
        html_files = d.get("_html_files") or [d.get("_html_file")]
        html_files_str = ", ".join(
            f"<code>{html.escape(f)}</code>" for f in html_files if f
        )
        rel_path = ""
        try:
            rel_path = str(r["path"].relative_to(get_cfg().repos_root))
        except (ValueError, KeyError):
            rel_path = str(r.get("path", "?"))
        # Mockup-URL: für render-only-inline ist der Pfad direkt der HTML, sonst gibt's mehrere
        if r["kind"] == "render-only-inline":
            mockup_url = url_for_path(r["path"])
            mockup_link = (
                (
                    f'<div class="mockup-link"><a href="{mockup_url}" target="_blank">'
                    f"📱 → {html.escape(r['path'].name)} öffnen</a></div>"
                )
                if mockup_url
                else ""
            )
        else:
            # Subdir mit HTMLs — erste finden
            mh = find_mockup_html(r["path"].parent, r["kd"])
            mockup_link = (
                (
                    f'<div class="mockup-link"><a href="{url_for_path(mh)}" target="_blank">'
                    f"📱 → {html.escape(mh.name)} öffnen</a></div>"
                )
                if mh
                else ""
            )
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
            f"<li><b>{html.escape(pname)}</b>"
            + (f' <span class="muted">— {html.escape(desc)}</span>' if desc else "")
            + (
                f'<br/><span class="small muted">Rechte: {html.escape(", ".join(rechte))}</span>'
                if rechte
                else ""
            )
            + "</li>"
        )
    personas_html = (
        f'<ul class="compact">{"".join(persona_items)}</ul>'
        if persona_items
        else '<span class="muted">—</span>'
    )

    # Screens
    screens = d.get("screens", []) or []
    # Mockup-Einstiegs-URL einmal früh (für klickbare Screen-Links F17 + Mockup-Button F15).
    _mockup_html_path = find_mockup_html(r["path"].parent, r["kd"])
    mockup_url = url_for_path(_mockup_html_path) if _mockup_html_path else None
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
        # F17: Screen klickbar → Deep-Link in den Mockup (#screen-<id>, Hash-Nav im KD).
        label = f"<code>{html.escape(sid)}</code> <b>{html.escape(str(stitle))}</b>"
        if mockup_url:
            label = (
                f'<a href="{html.escape(mockup_url)}#screen-{html.escape(sid)}" '
                f'target="_blank" title="Diesen Screen im Mockup öffnen">{label}</a>'
            )
        screen_items.append(
            f"<li>{label}"
            + f'<br/><span class="small muted">Personas: {html.escape(sper_str)}</span></li>'
        )
    screens_html = (
        f'<ul class="compact">{"".join(screen_items)}</ul>'
        if screen_items
        else '<span class="muted">—</span>'
    )

    # Beziehungen
    rel_lines = []
    cf = d.get("consumes_from") or []
    if cf:
        for entry in cf:
            ref = entry.get("ref", "?") if isinstance(entry, dict) else str(entry)
            entities = entry.get("entities", []) if isinstance(entry, dict) else []
            rel_lines.append(
                f'<li><span class="rel-tag rel-cf">consumes_from</span> <code>{html.escape(ref)}</code> ({len(entities)} entities)</li>'
            )
    pc = d.get("provides_contracts") or []
    if pc:
        for entry in pc:
            cid = entry.get("schema_ref") or entry.get("id", "?")
            rel_lines.append(
                f'<li><span class="rel-tag rel-pc">provides_contracts</span> <code>{html.escape(cid)}</code></li>'
            )
    ac = d.get("accepts_contracts") or []
    if ac:
        for entry in ac:
            cid = entry.get("schema_ref") or entry.get("id", "?")
            rel_lines.append(
                f'<li><span class="rel-tag rel-ac">accepts_contracts</span> <code>{html.escape(cid)}</code></li>'
            )
    re_root = d.get("root_entities") or {}
    if re_root:
        n = len(re_root) if isinstance(re_root, dict) else len(list(re_root))
        rel_lines.append(
            f'<li><span class="rel-tag rel-rt">root_entities</span> {n} exponiert</li>'
        )
    rel_html = (
        f'<ul class="compact">{"".join(rel_lines)}</ul>'
        if rel_lines
        else '<span class="muted">standalone — keine Cross-KD-Beziehungen</span>'
    )

    # Spec-Pfad + Mermaid-Detail-Link (wenn vorhanden)
    rel_path = ""
    try:
        rel_path = str(r["path"].relative_to(get_cfg().repos_root))
    except (ValueError, KeyError):
        rel_path = str(r.get("path", "?"))

    # Per-Repo-Mermaid-Lineage (Stufe 1b, F12: nur wenn ≥2 KDs im Repo)
    repo_kd_count = sum(
        1 for x in records if x["repo"] == r["repo"] and x.get("kind", "spec") == "spec"
    )
    repo_slug = html.escape(r["repo"])
    # Deep-Link in die gefilterte Genesor-Übersicht (Hash-Route #/repo/<slug>,
    # vom SPA-Router unterstützt: facets repo/org/class/role).
    genesor_link = f'<a href="index.html#/repo/{repo_slug}">→ im Genesor öffnen</a>'
    if repo_kd_count >= 2:
        # Beide Links: Genesor-Repo-Sicht UND standalone Mermaid-Topologie
        # (sonst wäre die Topologie-Seite aus der Zeile nicht mehr erreichbar).
        lineage_link = (
            '<div class="lineage-link">'
            f"🌐 Topologie für <code>{repo_slug}</code>: "
            f"{genesor_link}"
            f' · <a href="lineage-{repo_slug}.html" target="_blank">→ Mermaid-Topologie öffnen</a>'
            "</div>"
        )
    else:
        lineage_link = (
            '<div class="lineage-link muted small">'
            f"🌐 <code>{repo_slug}</code>: {genesor_link}"
            f" · ℹ Nur 1 KD — kein eigener Mermaid-Graph generiert."
            "</div>"
        )

    # Mockup-HTML (Stufe 1b: "Klickdummy klickbar") — mockup_url oben vorberechnet.
    if _mockup_html_path and mockup_url:
        mockup_link = (
            '<div class="mockup-link">'
            f"📱 Klickdummy-Mockup: "
            f'<a href="{mockup_url}" target="_blank">→ {html.escape(_mockup_html_path.name)} öffnen</a>'
            f' <span class="small muted">(echter klickbarer HTML-Render)</span>'
            "</div>"
        )
    else:
        # Render-Fallback: aus Spec generierte minimal-klickbare HTML
        mockup_link = (
            '<div class="mockup-link">'
            f"🔬 Auto-Render aus Spec: "
            f'<a href="/genesor/render/{html.escape(r["repo"])}-{html.escape(r["kd"])}.html" target="_blank">→ Spec-Render öffnen</a>'
            f' <span class="small muted">(klickbar — Persona-Filter, kein eigenes Design)</span>'
            "</div>"
        )

    # Grounding-Info
    g = d.get("grounding", {}) or {}
    ground_lines = []
    for k in (
        "domain",
        "achse",
        "pilot_stakeholder",
        "pilot_lra",
        "konzept_ref",
        "prozessmodell",
    ):
        if k in g:
            v = g[k]
            v_str = ", ".join(v) if isinstance(v, list) else str(v)
            ground_lines.append(f"<li><b>{k}:</b> {html.escape(v_str[:120])}</li>")
    ground_html = (
        f'<ul class="compact">{"".join(ground_lines)}</ul>' if ground_lines else ""
    )

    # Use-Cases-Section + Replaces-Section (Rev-15-Vorgriff)
    adr_meta = r.get("adr_meta") or {}
    ucs_list = adr_meta.get("realizes_use_cases") or []
    replaces_ref = adr_meta.get("replaces_system_ref")
    ucs_html = ""
    # Link auf UC-Repo-Index mit Filter (Workshop 2026-05-26 #2)
    kd_filter_url = f"./uc-{html.escape(r['repo'])}.html?kd={html.escape(r['kd'])}"
    if ucs_list:
        uc_items = "".join(
            f"<li><code>{html.escape(uc)}</code></li>" for uc in ucs_list
        )
        ucs_html = (
            f"<h4>📋 Realisiert Use Cases ({len(ucs_list)}) "
            f'<a href="{kd_filter_url}" style="font-size:12px;font-weight:normal;color:#06c;">→ alle UCs für diesen KD</a></h4>'
            f'<ul class="compact">{uc_items}</ul>'
        )
    elif r.get("kind", "spec") == "spec":
        ucs_html = (
            f"<h4>📋 Use Cases</h4>"
            f'<span class="muted small">— keine <code>realizes_use_cases:</code> im ADR-Frontmatter · </span>'
            f'<a href="{kd_filter_url}" style="font-size:13px;color:#06c;">'
            f"→ UC-Liste für diesen KD öffnen</a>"
            f'<div class="muted small" style="margin-top:4px;">'
            f"(Per-Discovery-UCs werden auf der UC-Index-Page gezeigt, gefiltert nach diesem KD)"
            f"</div>"
        )
    replaces_html = ""
    if replaces_ref:
        replaces_html = f'<h4 style="margin-top:8px;">🔄 Löst ab</h4><code>{html.escape(replaces_ref)}</code> <span class="small muted">(siehe docs/inventur/fv-inventur.yaml)</span>'

    return f"""
    <tr class="detail-row" id="detail-{idx}">
      <td colspan="13" class="detail-cell">
        {mockup_link}
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
            {('<h4 style="margin-top:12px;">📌 Grounding</h4>' + ground_html) if ground_html else ""}
          </div>
        </div>
        {lineage_link}
        <div class="spec-path small muted">Spec: <code>~/github/{html.escape(rel_path)}</code></div>
      </td>
    </tr>"""


def _render_table_body(
    records: list[dict],
    by_org: dict[str, dict[str, list[dict]]],
    all_warnings: dict[int, list[dict]],
    drift_by_idx: dict[int, dict],
    apps_index: dict[str, dict],
) -> str:
    """Tabellen-Body: eine sichtbare Zeile + Detail-Panel-Zeile pro KD."""
    rows: list[str] = []
    # idx muss konsistent zu den all_warnings-Keys sein (Reihenfolge wie records)
    by_record_idx = {id(r): i for i, r in enumerate(records)}
    iter_idx = 0
    for org in sorted(by_org):
        for repo in sorted(by_org[org]):
            kd_records = sorted(by_org[org][repo], key=lambda r: r["kd"])
            for r in kd_records:
                d = r["data"]
                idx = by_record_idx[id(r)]  # echter Index für warnings-Lookup
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
                        personas_list = [
                            p.get("id", str(p)) if isinstance(p, dict) else str(p)
                            for p in personas_obj
                        ]
                    else:
                        personas_list = []
                    personas = ", ".join(personas_list[:3])
                    if len(personas_list) > 3:
                        personas += f" +{len(personas_list) - 3}"
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
                    if n_kd_ucs
                    else f'<a href="./uc-{html.escape(r["repo"])}.html" style="color:#999;text-decoration:none;" title="UC-Liste für {html.escape(r["repo"])} (leer für diesen KD)">—</a>'
                )
                replaces_ref = adr_meta.get("replaces_system_ref")
                replaces_cell = (
                    f"<code>{html.escape(replaces_ref)}</code>"
                    if replaces_ref
                    else '<span class="muted">—</span>'
                )

                org_cell = _org_chip(org)
                repo_cell = f"<code>{html.escape(repo)}</code>"

                # Surface-Switcher: KD / Dev / Staging / Stable (Pilot-Memo §Surface)
                app_info = apps_index.get(repo, {})
                surface_urls = app_info.get("urls", {})
                # KD-Spec ist immer da — entweder Mockup-HTML oder Auto-Render
                kd_mockup = find_mockup_html(r["path"].parent, r["kd"])
                kd_url = (
                    url_for_path(kd_mockup)
                    if kd_mockup
                    else (
                        f"/genesor/render/{html.escape(r['repo'])}-{html.escape(r['kd'])}.html"
                    )
                )
                # Sichtbarer Flag: KD ohne echtes Mockup-HTML → nur Spec-Render.
                mockup_missing_badge = (
                    '<span class="warn-badge warn-warning mockup-missing" '
                    'title="Kein echtes Mockup-HTML im KD-Verzeichnis — Link zeigt auf den '
                    'aus der Spec generierten Auto-Render.">⚠ Mockup fehlt · nur Spec-Render</span> '
                    if kd_mockup is None
                    else ""
                )
                # Feature B: "🛠 Mockup generieren" — nur wenn kein echtes Mockup existiert.
                # Verlinkt auf ein vorausgefülltes GitHub-Issue (labels=klickdummy,auto).
                mockup_generate_btn = ""
                if kd_mockup is None:
                    from urllib.parse import quote as _quote

                    _issue_title = f"[klickdummy] {r['kd']} bauen"
                    # Idempotenz-Schlüssel (KONZ-iil-klickdummy-001, Teil A): identisch zum
                    # Sentinel von klickdummy_sync.py (find_existing_issue) — so erkennt der Sync
                    # button-erzeugte Issues und legt keine Dublette an / kann sie rekonziliieren.
                    _issue_body = (
                        f"Mockup für {repo}:{r['kd']} bauen gemäß ADR-211, "
                        f"angefordert über genesor.\n\n"
                        f"<!-- klickdummy-sync:{r['kd']} -->"
                    )
                    _issue_url = (
                        f"https://github.com/{detect_org(repo)}/{repo}/issues/new"
                        f"?title={_quote(_issue_title)}"
                        f"&labels=klickdummy,auto"
                        f"&body={_quote(_issue_body)}"
                    )
                    mockup_generate_btn = (
                        f'<a class="mockup-gen-btn" href="{html.escape(_issue_url, quote=True)}" '
                        f'target="_blank" rel="noopener" '
                        f'title="GitHub-Issue zum Bau dieses Mockups vorausfüllen (labels=klickdummy,auto)" '
                        f'onclick="event.stopPropagation(); mockupGenStart(this);">'
                        f"🛠 Mockup generieren</a> "
                    )

                # Screen×Surface-Matrix als JSON-Datenstruktur fürs Modal
                screen_routes = _extract_screen_routes(r)
                import json as _json

                modal_payload = _json.dumps(
                    {
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
                    },
                    ensure_ascii=False,
                )

                surfaces = [
                    ("kd", "📋 KD", kd_url, "Klickdummy-Spec / Render"),
                    (
                        "dev",
                        "🛠 Dev",
                        surface_urls.get("dev"),
                        "Development-Environment",
                    ),
                    (
                        "staging",
                        "🧪 Stg",
                        surface_urls.get("staging"),
                        "Staging-Environment",
                    ),
                    (
                        "prod",
                        "✅ Prod",
                        surface_urls.get("prod"),
                        "Production / Stable",
                    ),
                ]
                surface_pills = []
                for code, label, url, surface_title in surfaces:
                    if url:
                        surface_pills.append(
                            f'<button class="surface-pill surface-{code} active" '
                            f'data-surface="{code}" '
                            f'title="{html.escape(surface_title)} — Modal mit Screen-Liste öffnen" '
                            f'onclick="event.stopPropagation(); openSurfaceModal(this);">'
                            f"{label}</button>"
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
                    + "</div>"
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
                        f'<span class="drift-badge" style="background:{d_color}20;color:{d_color};" title="Brief-Coverage: {d_cov}% ({d_info.get("n_actual_briefs", 0)}/{d_expected})">'
                        f"● {html.escape(d_label)}</span> "
                        f'<a href="{html.escape(d_compare)}" target="_blank" class="compare-link" '
                        f'title="Brief §10 Drift-Sektion öffnen" onclick="event.stopPropagation();">🔍</a>'
                    )
                else:
                    drift_cell = (
                        f'<span class="drift-badge" style="background:{d_color}20;color:{d_color};" '
                        f'title="{d_expected} Screen(s) mit implementation_brief, aber noch keine Briefs generiert">'
                        f"○ {html.escape(d_label)}</span>"
                    )

                rows.append(f"""
    <tr class="kd-row {"render-only" if is_render_only else ""}" data-detail-id="detail-{idx}" data-drift-status="{d_status}" data-org="{html.escape(org)}" data-repo="{html.escape(repo)}" data-class="{html.escape(klass)}" data-role="{html.escape(role)}" onclick="toggleDetail(this)">
      <td class="org-cell">{org_cell}</td>
      <td class="repo-cell">{repo_cell}</td>
      <td><span class="toggle">▸</span> {badge} <b>{html.escape(r["kd"])}</b><br/>{mockup_missing_badge}{mockup_generate_btn}<span class="muted">{html.escape(title)}</span></td>
      <td>{_role_chip(role)}</td>
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
                rows.append(_render_kd_detail(r, idx, records, all_warnings))
                iter_idx += 1

    table_body = "".join(rows)
    return table_body


def _render_acceptance_matrix(records: list[dict]) -> str:
    """Acceptance-Matrix (ADR-211 §Acceptance) als <details>-Sektion."""
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
                    f"{html.escape(str(info.get('latest_by') or '?'))} · "
                    f"{html.escape(str(info.get('latest_date') or ''))} · "
                    f'ref={html.escape(str(info.get("latest_ref") or "—"))}">'
                    f"✓ signed</span>"
                )
            elif st == "stale":
                chip = (
                    f'<span class="ac-chip ac-stale" title="{html.escape(label)}: '
                    f"letzter Eintrag {info.get('age_days')}d alt "
                    f"({html.escape(str(info.get('latest_date') or ''))}) — "
                    f'Spec-Drift möglich, neue Abnahme empfohlen">⚠ stale</span>'
                )
                row_has_open = True
            else:
                chip = (
                    f'<span class="ac-chip ac-none" title="{html.escape(label)}: '
                    f'keine Abnahme erfasst">offen</span>'
                )
                row_has_open = True
            cells.append(f"<td>{chip}</td>")
        if row_has_open:
            _am_open_count += 1
        repo = r["repo"]
        org = r.get("org") or detect_org(repo)
        _am_rows.append(
            f"<tr>"
            f'<td class="am-label">{_org_chip(org)} <code>{html.escape(repo)}</code> · '
            f"<b>{html.escape(r['kd'])}</b></td>"
            f"{''.join(cells)}"
            f"</tr>"
        )
    acceptance_matrix_section = (
        '<details class="acceptance-matrix">'
        f"<summary>✍️ Acceptance-Matrix — {_am_open_count}/{len(records)} KD(s) mit "
        "offener Abnahme (klicken zum Aufklappen)</summary>"
        "<table>"
        "<thead><tr>"
        "<th>Repo · Klickdummy</th>"
        f'<th title="ADR-211 Achse spec_signed">{_ac_axis_labels["spec_signed"]}</th>'
        f'<th title="ADR-211 Achse ui_walked">{_ac_axis_labels["ui_walked"]}</th>'
        "</tr></thead>"
        f"<tbody>{''.join(_am_rows)}</tbody>"
        "</table>"
        "</details>"
    )
    return acceptance_matrix_section


def _render_skin_options() -> str:
    """Skin-Switcher-<option>s für die Genesor-Topbar."""
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
            _genesor_skin_options.append(
                '<option value="__greenfield">Greenfield (Default)</option>'
            )
            continue
        _short = _genesor_skin_short_labels.get(_value.rsplit("/", 1)[-1], _label)
        _genesor_skin_options.append(
            f'<option value="{html.escape(_value)}">{html.escape(_short)}</option>'
        )
    genesor_skin_options = "\n      ".join(_genesor_skin_options)
    return genesor_skin_options


# Statischer Kopf (CSS/Markup bis zur ersten Interpolation) — als Konstante,
# Braces hier UNGEDOPPELT (kein f-String mehr).
_GENESOR_HEAD = """<!DOCTYPE html>
<html lang="de">
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><text y='.9em' font-size='85'>🌱</text></svg>">
<title>IIL-Genesor — Klickdummy-Übersicht (Cross-Repo)</title>
<style>
  body { font-family: -apple-system, system-ui, sans-serif; margin: 0; color: #222; background: #fafafa; }
  header { padding: 14px 24px; background: linear-gradient(90deg,#06c,#48c); color:#fff; }
  header h1 { margin: 0; font-size: 20px; }
  header .sub { font-size: 13px; opacity: 0.9; margin-top: 4px; }
  main { padding: 20px 24px; }
  .stats { display: flex; gap: 18px; flex-wrap: wrap; background: #fff; border: 1px solid #e0e0e0; border-radius: 6px; padding: 12px 16px; margin-bottom: 16px; font-size: 14px; }
  .stats .kv { display: flex; flex-direction: column; }
  .stats .kv .n { font-size: 22px; font-weight: 600; color: #06c; }
  .stats .kv .lbl { font-size: 11px; color: #888; text-transform: uppercase; letter-spacing: 0.5px; }
  table { width: 100%; background: #fff; border-collapse: collapse; border: 1px solid #e0e0e0; border-radius: 6px; overflow: hidden; font-size: 13px; }
  th { background: #f0f4f8; text-align: left; padding: 8px 10px; font-weight: 600; color: #444; border-bottom: 1px solid #d0d0d0; }
  td { padding: 8px 10px; border-bottom: 1px solid #ececec; vertical-align: top; }
  td.org-cell, td.repo-cell { background: #fafafa; }
  td.num { text-align: right; }
  .muted { color: #888; }
  .small { font-size: 12px; }
  code { background: #f0f0f0; padding: 1px 6px; border-radius: 3px; font-size: 12px; }
  .org-chip { display: inline-block; padding: 2px 8px; border-radius: 12px; font-size: 11px; font-weight: 600; color: #fff; }
  .org-chip.org-meiki-lra { background: #06c; }
  .org-chip.org-ttz-lif { background: #093; }
  .org-chip.org-bahn-sqf { background: #c40; }
  .org-chip.org-iilgmbh { background: #639; }
  .org-chip.org-achimdehnert { background: #555; }
  .role-root { display: inline-block; padding: 2px 6px; background: #cef; border-radius: 4px; font-size: 11px; }
  .role-hybrid { display: inline-block; padding: 2px 6px; background: #fec; border-radius: 4px; font-size: 11px; }
  .role-default { color: #999; font-size: 11px; }
  .klass-mock { display: inline-block; padding: 1px 6px; background: #fee; color: #a00; border-radius: 3px; font-size: 11px; }
  .klass-stub-demo, .klass-spec-demo, .klass-story { display: inline-block; padding: 1px 6px; background: #efe; color: #060; border-radius: 3px; font-size: 11px; }
  footer { padding: 12px 24px; color: #888; font-size: 12px; text-align: center; }

  /* Klickbare KD-Zeilen + Detail-Panel */
  tr.kd-row { cursor: pointer; transition: background 0.1s; }
  tr.kd-row:hover { background: #f5f9ff; }
  tr.kd-row .toggle { color: #06c; font-weight: 600; display: inline-block; width: 12px; transition: transform 0.15s; }
  tr.kd-row.open .toggle { transform: rotate(90deg); }
  tr.detail-row { display: none; }
  tr.detail-row.visible { display: table-row; }
  td.detail-cell { background: #fbfdff; padding: 14px 20px; border-bottom: 2px solid #cce; }
  .detail-grid { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 18px; margin-bottom: 12px; }
  .detail-cell h4 { margin: 0 0 6px 0; font-size: 13px; color: #06c; }
  ul.compact { margin: 0; padding-left: 18px; }
  ul.compact li { margin-bottom: 4px; font-size: 12px; }
  .rel-tag { display: inline-block; padding: 1px 5px; border-radius: 3px; font-size: 10px; font-weight: 600; margin-right: 4px; }
  .rel-cf { background: #def; color: #06c; }
  .rel-pc { background: #fde; color: #c0c; }
  .rel-ac { background: #efe; color: #060; }
  .rel-rt { background: #fec; color: #c80; }
  .lineage-link, .mockup-link { background: #fff; border: 1px solid #cce; border-radius: 4px; padding: 8px 12px; margin: 8px 0; font-size: 13px; }
  .mockup-link { border-color: #c80; background: #fffbf0; }
  .lineage-link a, .mockup-link a { color: #06c; text-decoration: none; font-weight: 600; }
  .lineage-link a:hover, .mockup-link a:hover { text-decoration: underline; }
  .spec-path { font-family: monospace; font-size: 11px; padding-top: 4px; }

  /* Sortable Headers (Stufe 1b) */
  th.sortable { cursor: pointer; user-select: none; }
  th.sortable:hover { background: #e0e8f0; }
  th.sortable::after { content: " ⇅"; opacity: 0.3; font-size: 10px; }
  th.sort-asc::after { content: " ▲"; opacity: 1; color: #06c; }
  th.sort-desc::after { content: " ▼"; opacity: 1; color: #06c; }

  /* Drift-Validierung (Paket A: F3) */
  .warn-badge { display: inline-block; padding: 1px 6px; border-radius: 3px; font-size: 11px; font-weight: 600; margin-right: 4px; }
  .warn-error { background: #fee; color: #a00; }
  .warn-warning { background: #fef0d0; color: #a60; }
  .warnings { background: #fff8f0; border: 1px solid #fcc; border-left: 4px solid #c40; padding: 10px 14px; margin-bottom: 12px; border-radius: 4px; }
  .warnings h4 { margin: 0 0 6px 0; color: #c40; font-size: 13px; }
  .warnings li.warn-error { background: none; padding-left: 0; }
  .warnings li.warn-warning { background: none; padding-left: 0; }
  .n-err { color: #c40 !important; }
  .n-warn { color: #b80 !important; }
  /* Feature B: "Mockup generieren"-Button (nur auf mockup-missing-Zeilen) */
  .mockup-gen-btn { display: inline-block; padding: 1px 8px; border-radius: 3px; font-size: 11px; font-weight: 600; margin-right: 6px; text-decoration: none; background: #e0ecff; color: #1d4ed8; border: 1px solid #bcd2ff; cursor: pointer; }
  .mockup-gen-btn:hover { background: #cfe0ff; }
  .mockup-gen-btn.mockup-gen-running { background: #f3f4f6; color: #6b7280; border-color: #d1d5db; pointer-events: none; cursor: default; }
  /* Feature C2: Acceptance-Matrix — .ac-chip im Genesor-Root (Render-Variante: L578) */
  .ac-chip { display: inline-block; padding: 1px 6px; border-radius: 3px; font-size: 10px; font-weight: 600; margin-right: 6px; cursor: help; }
  .ac-signed { background: #d1fae5; color: #065f46; border: 1px solid #a7f3d0; }
  .ac-stale  { background: #fef3c7; color: #92400e; border: 1px solid #fde68a; }
  .ac-none   { background: #f3f4f6; color: #6b7280; border: 1px solid #e5e7eb; }
  .acceptance-matrix { margin: 12px 0; border: 1px solid #e3e8ee; border-radius: 6px; background: #fff; }
  .acceptance-matrix > summary { cursor: pointer; padding: 10px 14px; font-weight: 600; color: #1f2937; list-style: none; }
  .acceptance-matrix > summary::-webkit-details-marker { display: none; }
  .acceptance-matrix > summary:hover { background: #f8fafc; }
  .acceptance-matrix table { margin: 0; width: 100%; }
  .acceptance-matrix .am-label { font-size: 11px; }

  /* Sunset-Aging (F4) */
  td.sunset-ok { color: #060; }
  td.sunset-near { background: #fef0d0; color: #a60; font-weight: 600; }
  td.sunset-overdue { background: #fee; color: #a00; font-weight: 600; }
  td.sunset-na { color: #888; }

  /* Render-only-KDs (F11) */
  tr.render-only td { background: #fafaf0 !important; }
  tr.render-only .toggle { color: #c40; }

  /* Drift-Center (Pilot-Memo 2026-05-26) */
  .drift-center { background: linear-gradient(135deg,#fff 0%,#f8fafc 100%); border: 1px solid #e0e7ef; border-radius: 8px; padding: 16px 20px; margin-bottom: 16px; }
  .drift-hero h2 { margin: 0 0 4px 0; font-size: 18px; color: #1e293b; }
  .drift-hero p { margin: 0 0 12px 0; }
  .drift-kpis { display: flex; gap: 18px; flex-wrap: wrap; padding: 10px 0; border-top: 1px solid #e0e7ef; border-bottom: 1px solid #e0e7ef; margin-bottom: 12px; }
  .drift-kpis .kv { display: flex; flex-direction: column; min-width: 70px; }
  .drift-kpis .kv .n { font-size: 20px; font-weight: 700; color: #06c; }
  .drift-kpis .kv .lbl { font-size: 11px; color: #64748b; text-transform: uppercase; letter-spacing: 0.3px; }
  .drift-status-in-sync .n { color: #16a34a !important; }
  .drift-status-stale .n { color: #ca8a04 !important; }
  .drift-status-partial .n { color: #ea580c !important; }
  .drift-status-no-brief .n { color: #94a3b8 !important; }
  .drift-filters { display: flex; gap: 6px; flex-wrap: wrap; align-items: center; padding-top: 8px; }
  .filter-label { font-size: 12px; color: #64748b; font-weight: 600; margin-right: 4px; }
  .filter-chip { padding: 4px 10px; border: 1px solid #cbd5e1; background: #fff; border-radius: 14px; cursor: pointer; font-size: 12px; transition: all 0.15s; }
  .filter-chip:hover { background: #f1f5f9; }
  .filter-chip.active { background: #06c; color: #fff; border-color: #06c; }
  #drift-search { padding: 5px 10px; border: 1px solid #cbd5e1; border-radius: 14px; font-size: 12px; min-width: 200px; margin-left: 8px; }

  /* Drift-Badge in Tabellen-Zeile */
  .drift-badge { display: inline-block; padding: 2px 8px; border-radius: 10px; font-size: 11px; font-weight: 600; white-space: nowrap; }
  .compare-link { margin-left: 4px; text-decoration: none; opacity: 0.7; transition: opacity 0.15s; }
  .compare-link:hover { opacity: 1; }

  /* Row-Filter — hidden via class */
  tr.kd-row.hidden, tr.detail-row.hidden { display: none; }

  /* Surface-Switcher (Pilot-Memo §Surface) */
  td.surface-cell { padding: 4px 6px; }
  .surface-tabs { display: inline-flex; gap: 2px; flex-wrap: nowrap; }
  .surface-pill {
    display: inline-block;
    padding: 3px 8px;
    border-radius: 4px;
    font-size: 11px;
    font-weight: 600;
    text-decoration: none;
    border: 1px solid transparent;
    white-space: nowrap;
    transition: all 0.1s;
  }
  .surface-pill.active { cursor: pointer; }
  .surface-pill.disabled { opacity: 0.32; cursor: not-allowed; }
  .surface-pill.surface-kd.active      { background: #e0f2fe; color: #075985; border-color: #bae6fd; }
  .surface-pill.surface-kd.active:hover { background: #bae6fd; }
  .surface-pill.surface-dev.active     { background: #fef9c3; color: #854d0e; border-color: #fde047; }
  .surface-pill.surface-dev.active:hover { background: #fde047; }
  .surface-pill.surface-staging.active { background: #fed7aa; color: #9a3412; border-color: #fdba74; }
  .surface-pill.surface-staging.active:hover { background: #fdba74; }
  .surface-pill.surface-prod.active    { background: #dcfce7; color: #166534; border-color: #86efac; }
  .surface-pill.surface-prod.active:hover { background: #86efac; }
  .surface-pill.disabled.surface-kd      { background: #f1f5f9; color: #64748b; }
  .surface-pill.disabled.surface-dev     { background: #f1f5f9; color: #64748b; }
  .surface-pill.disabled.surface-staging { background: #f1f5f9; color: #64748b; }
  .surface-pill.disabled.surface-prod    { background: #f1f5f9; color: #64748b; }

  /* Master-Surface-Toggle im Hero */
  .surface-master { display: flex; gap: 6px; align-items: center; margin-top: 8px; padding-top: 8px; border-top: 1px solid #e0e7ef; }
  .surface-master-label { font-size: 12px; color: #64748b; font-weight: 600; }
  .surface-master button {
    padding: 4px 12px;
    border: 1px solid #cbd5e1;
    background: #fff;
    border-radius: 14px;
    cursor: pointer;
    font-size: 12px;
    font-weight: 600;
  }
  .surface-master button.active { background: #06c; color: #fff; border-color: #06c; }
  /* Wenn Master gesetzt → nur passende Pills hervorheben, andere ausgrauen */
  .surface-tabs.master-kd      .surface-pill:not(.surface-kd) { opacity: 0.4; }
  .surface-tabs.master-dev     .surface-pill:not(.surface-dev) { opacity: 0.4; }
  .surface-tabs.master-staging .surface-pill:not(.surface-staging) { opacity: 0.4; }
  .surface-tabs.master-prod    .surface-pill:not(.surface-prod) { opacity: 0.4; }

  /* Surface-Pill als button (statt <a>) */
  button.surface-pill { font-family: inherit; cursor: pointer; }

  /* Surface-Modal (Pilot-Memo §Surface-Modal) */
  .surface-modal { display: none; position: fixed; inset: 0; z-index: 9999; }
  .surface-modal[aria-hidden="false"] { display: block; }
  .surface-modal-backdrop {
    position: absolute; inset: 0;
    background: rgba(15, 23, 42, 0.55);
    backdrop-filter: blur(2px);
  }
  .surface-modal-dialog {
    position: relative;
    max-width: 1000px; width: calc(100vw - 40px);
    max-height: calc(100vh - 60px); overflow-y: auto;
    margin: 30px auto;
    background: #fff;
    border-radius: 10px;
    box-shadow: 0 20px 60px rgba(0,0,0,0.4);
  }
  .surface-modal header {
    display: flex; align-items: center; justify-content: space-between;
    padding: 14px 20px;
    background: linear-gradient(90deg,#06c,#48c);
    color: #fff;
    border-radius: 10px 10px 0 0;
  }
  .surface-modal header h2 { margin: 0; font-size: 16px; }
  .surface-modal-close {
    background: rgba(255,255,255,0.2); color: #fff;
    border: none; padding: 2px 12px;
    border-radius: 14px; cursor: pointer;
    font-size: 22px; line-height: 1;
  }
  .surface-modal-close:hover { background: rgba(255,255,255,0.35); }
  .surface-modal-body { padding: 16px 20px; }
  table.surface-screen-table { font-size: 12px; width: 100%; border: 1px solid #e0e7ef; }
  table.surface-screen-table th { background: #f1f5f9; padding: 6px 8px; text-align: left; font-weight: 600; font-size: 11px; }
  table.surface-screen-table td { padding: 6px 8px; border-bottom: 1px solid #f1f5f9; vertical-align: top; }
  table.surface-screen-table td.screen-id { font-weight: 600; color: #1e293b; white-space: nowrap; }
  table.surface-screen-table td.route { color: #64748b; font-family: ui-monospace, monospace; font-size: 11px; }
  .surface-screen-pill {
    display: inline-block; padding: 2px 8px;
    border-radius: 10px; font-size: 11px; font-weight: 600;
    text-decoration: none;
    border: 1px solid transparent;
  }
  .surface-screen-pill.kd      { background: #e0f2fe; color: #075985; border-color: #bae6fd; }
  .surface-screen-pill.dev     { background: #fef9c3; color: #854d0e; border-color: #fde047; }
  .surface-screen-pill.staging { background: #fed7aa; color: #9a3412; border-color: #fdba74; }
  .surface-screen-pill.prod    { background: #dcfce7; color: #166534; border-color: #86efac; }
  .surface-screen-pill.disabled { background: #f1f5f9; color: #94a3b8; cursor: not-allowed; opacity: 0.5; }

  /* ── Repo-Rail Master-Detail (KONZ-iil-klickdummy-002) ───────────────── */
  .genesor-layout { display: grid; grid-template-columns: 232px 1fr; align-items: start; gap: 0; }
  .genesor-layout > main { min-width: 0; overflow-x: auto; }
  .repo-rail { position: sticky; top: 0; align-self: start; max-height: 100vh; overflow-y: auto;
    background: #fff; border-right: 1px solid #e3e8ee; padding: 14px 0; }
  .repo-rail .rail-facet { padding: 0 14px 10px; display: flex; align-items: center; gap: 6px; }
  .repo-rail .rail-facet label { font-size: 11px; color: #6b7280; text-transform: uppercase; letter-spacing: .5px; }
  .repo-rail .rail-facet select { flex: 1; padding: 4px 8px; border: 1px solid #e3e8ee; border-radius: 6px; font-size: 13px; }
  .repo-rail .rail-head { font-size: 11px; text-transform: uppercase; letter-spacing: .5px; color: #6b7280; padding: 6px 14px; }
  .repo-rail .rail-item { display: flex; align-items: center; gap: 8px; width: 100%; text-align: left;
    border: 0; background: none; cursor: pointer; padding: 8px 14px; font-size: 13px; color: #1f2937;
    border-left: 3px solid transparent; }
  .repo-rail .rail-item:hover { background: #eef2ff; }
  .repo-rail .rail-item.active { background: #eef2ff; border-left-color: #1e3a8a; font-weight: 600; color: #1e3a8a; }
  .repo-rail .rail-item .dot { width: 8px; height: 8px; border-radius: 50%; flex: 0 0 auto; }
  .repo-rail .rail-item .glabel { flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .repo-rail .rail-item .count { font-size: 11px; color: #64748b; background: #f1f5f9; border-radius: 10px; padding: 1px 8px; }
  .repo-rail .rail-item.active .count { background: #fff; }
  @media (max-width: 900px) {
    .genesor-layout { grid-template-columns: 1fr; }
    .repo-rail { position: static; max-height: none; border-right: 0; border-bottom: 1px solid #e3e8ee; }
  }

  /* ── Repo-Linse ein-/ausklappen — mehr Platz für den Inhalt ───────────── */
  .rail-toggle { flex: 0 0 auto; border: 1px solid #e3e8ee; background: #fff; color: #6b7280;
    border-radius: 6px; cursor: pointer; font-size: 12px; line-height: 1; padding: 5px 7px; }
  .rail-toggle:hover { background: #eef2ff; color: #1e3a8a; }
  .genesor-layout.rail-collapsed { grid-template-columns: 0 1fr; }
  .genesor-layout.rail-collapsed .repo-rail { overflow: hidden; visibility: hidden;
    min-width: 0; padding: 0; border-right: 0; }
  .rail-expand { display: none; }
  .genesor-layout.rail-collapsed .rail-expand { display: inline-flex; align-items: center; gap: 6px;
    position: sticky; top: 8px; margin: 0 0 10px; border: 1px solid #e3e8ee; background: #fff;
    color: #1e3a8a; border-radius: 6px; cursor: pointer; font-size: 12px; font-weight: 600; padding: 5px 10px; }
  .rail-expand:hover { background: #eef2ff; }
</style>
</head>
<body>

<header style="display:flex;align-items:center;gap:16px;flex-wrap:wrap;">
  <div style="flex:1;min-width:200px;">
    <h1 style="margin:0;">🌱 IIL-Genesor — Klickdummy-Übersicht</h1>
"""


# Statischer Schluss (Tabellen-Ende + komplettes Seiten-JS) — Konstante,
# Braces UNGEDOPPELT.
_GENESOR_TAIL = """  </tbody>
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
function toggleDetail(row) {
  const detailId = row.dataset.detailId;
  const detail = document.getElementById(detailId);
  if (!detail) return;
  const isOpen = detail.classList.toggle('visible');
  row.classList.toggle('open', isOpen);
}

// Feature B: "🛠 Mockup generieren" — Issue öffnet im neuen Tab (href/target),
// hier nur Sofort-Feedback: Label umschalten + Button entschärfen.
function mockupGenStart(btn) {
  if (!btn || btn.dataset.genStarted === '1') return;
  btn.dataset.genStarted = '1';
  btn.textContent = '⏳ generieren läuft…';
  btn.classList.add('mockup-gen-running');
  btn.setAttribute('aria-disabled', 'true');
}

// Surface-Modal (Pilot-Memo §Surface-Modal — Screen×Surface-Matrix pro KD)
function openSurfaceModal(pillBtn) {
  const tabs = pillBtn.closest('.surface-tabs');
  if (!tabs) return;
  const raw = tabs.dataset.modalPayload;
  if (!raw) return;
  let payload;
  try { payload = JSON.parse(raw); }
  catch (e) { console.error('Modal-Payload parse error', e); return; }

  const modal = document.getElementById('surface-modal');
  const title = document.getElementById('surface-modal-title');
  const subtitle = document.getElementById('surface-modal-subtitle');
  const tbody = document.getElementById('surface-screen-tbody');

  title.textContent = `${payload.repo} / ${payload.kd}`;
  subtitle.innerHTML = `<b>${payload.kd_title || ''}</b> · Surface-Pill geklickt: <b>${pillBtn.dataset.surface}</b>`;

  // Pro Screen eine Zeile
  tbody.innerHTML = '';
  const screens = payload.screens || [];
  if (!screens.length) {
    tbody.innerHTML = '<tr><td colspan="6" class="muted small" style="text-align:center;padding:20px;">Keine Screens im Spec gefunden.</td></tr>';
  }
  // HTML-escape helper — wichtig für Routes mit <ausschreibung_id> u.ä.
  const esc = (s) => String(s || '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');

  screens.forEach(s => {
    // route_example zuerst (hat konkrete IDs), sonst route mit Platzhaltern
    const displayRoute = s.route_example || s.route || '';
    const route = displayRoute;  // gleiche Datenbasis fürs URL-Bauen
    const apiHint = (s.api_paths && s.api_paths.length)
      ? `<br><span class="muted small">API: ${s.api_paths.map(esc).join(', ')}</span>`
      : '';
    // KD-Render mit Anchor zum Screen
    const kdUrl = payload.kd_url ? `${payload.kd_url}#screen-${s.screen_id}` : '';
    const kdPill = kdUrl
      ? `<a class="surface-screen-pill kd" href="${kdUrl}" target="_blank" title="KD-Render mit Screen-Anker">📋 KD</a>`
      : `<span class="surface-screen-pill kd disabled">📋 KD</span>`;

    // Dev/Stg/Prod: nur wenn route da UND base-URL gesetzt.
    // Wichtig: Route ist absolut (/submission/...), daher braucht es nur den Origin
    // (Protocol+Host+Port) der Base-URL, NICHT den ganzen Pfad.
    function makeImplPill(env, label) {
      const base = (payload.surface_base || {})[env];
      if (!base || !route) {
        const reason = !base ? `${env}-URL fehlt in apps.json` : 'kein route: im Spec';
        return `<span class="surface-screen-pill ${env} disabled" title="${reason}">${label}</span>`;
      }
      let origin;
      try {
        const u = new URL(base);
        origin = `${u.protocol}//${u.host}`;
      } catch (e) {
        // base ist relativ — als Fallback nehme den Server-Origin (Page-Origin)
        origin = window.location.origin;
      }
      const path = (s.route_example || route).startsWith('/')
        ? (s.route_example || route)
        : `/${s.route_example || route}`;
      const full = origin + path;
      return `<a class="surface-screen-pill ${env}" href="${full}" target="_blank" title="${full}">${label}</a>`;
    }

    const row = document.createElement('tr');
    row.innerHTML = `
      <td class="screen-id">${esc(s.screen_id)}<br><span class="muted small">${esc(s.title || '')}</span></td>
      <td class="route">${displayRoute ? esc(displayRoute) : '<span class="muted">—</span>'}${apiHint}</td>
      <td>${kdPill}</td>
      <td>${makeImplPill('dev', '🛠 Dev')}</td>
      <td>${makeImplPill('staging', '🧪 Stg')}</td>
      <td>${makeImplPill('prod', '✅ Prod')}</td>
    `;
    tbody.appendChild(row);
  });

  modal.setAttribute('aria-hidden', 'false');
}

function closeSurfaceModal() {
  const modal = document.getElementById('surface-modal');
  if (modal) modal.setAttribute('aria-hidden', 'true');
}

document.addEventListener('keydown', e => {
  if (e.key === 'Escape') closeSurfaceModal();
});

// Drift-Center Filter (Pilot-Memo 2026-05-26)
(function() {
  const state = { org: 'all', drift: 'all', search: '', facet: 'repo', group: null };

  function applyFilters() {
    const rows = document.querySelectorAll('#genesor-table tbody tr.kd-row');
    let visible = 0;
    rows.forEach(row => {
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
    });
    const url = new URL(window.location);
    if (state.org !== 'all') url.searchParams.set('org', state.org); else url.searchParams.delete('org');
    if (state.drift !== 'all') url.searchParams.set('drift', state.drift); else url.searchParams.delete('drift');
    history.replaceState({}, '', url);
  }

  document.querySelectorAll('.filter-chip[data-filter-org]').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.filter-chip[data-filter-org]').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      state.org = btn.dataset.filterOrg;
      applyFilters();
    });
  });
  document.querySelectorAll('.filter-chip[data-filter-drift]').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.filter-chip[data-filter-drift]').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      state.drift = btn.dataset.filterDrift;
      applyFilters();
    });
  });
  const search = document.getElementById('drift-search');
  if (search) {
    search.addEventListener('input', () => {
      state.search = search.value.toLowerCase();
      applyFilters();
    });
  }

  // Master-Surface-Toggle (Pilot-Memo §Surface)
  function applyMasterSurface(surface) {
    const allTabs = document.querySelectorAll('.surface-tabs');
    ['kd','dev','staging','prod'].forEach(s => {
      allTabs.forEach(t => t.classList.remove(`master-${s}`));
    });
    if (surface && surface !== 'none') {
      allTabs.forEach(t => t.classList.add(`master-${surface}`));
    }
    const url = new URL(window.location);
    if (surface && surface !== 'none') url.searchParams.set('surface', surface);
    else url.searchParams.delete('surface');
    history.replaceState({}, '', url);
  }
  document.querySelectorAll('.surface-master button').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.surface-master button').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      applyMasterSurface(btn.dataset.masterSurface);
    });
  });

  // ── Repo-Rail Master-Detail (KONZ-iil-klickdummy-002) ──────────────────
  const FACET_LABEL = { repo: 'Repos', org: 'Orgs', 'class': 'Klassen', role: 'Rollen' };
  const DRIFT_RANK = { 'partial': 3, 'stale': 2, 'no-brief': 1, 'in-sync': 0 };
  const DRIFT_DOT  = { 'partial': '#f97316', 'stale': '#eab308', 'no-brief': '#cbd5e1', 'in-sync': '#16a34a' };

  function buildRail() {
    const facet = state.facet;
    const rows = document.querySelectorAll('#genesor-table tbody tr.kd-row');
    const groups = {};
    rows.forEach(row => {
      const g = row.dataset[facet] || '—';
      if (!groups[g]) groups[g] = { count: 0, worst: -1 };
      groups[g].count++;
      const dr = DRIFT_RANK[row.dataset.driftStatus];
      if (dr !== undefined && dr > groups[g].worst) groups[g].worst = dr;
    });
    const head = document.getElementById('rail-head');
    if (head) head.textContent = FACET_LABEL[facet] || facet;
    const nav = document.getElementById('rail-nav');
    if (!nav) return;
    const keys = Object.keys(groups).sort((a, b) => {
      const d = groups[b].count - groups[a].count;
      return d !== 0 ? d : a.localeCompare(b);
    });
    const esc = (s) => String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/"/g,'&quot;');
    let buf = '<button class="rail-item' + (state.group ? '' : ' active') + '" data-group="">'
      + '<span class="dot" style="background:#e2e8f0"></span>'
      + '<span class="glabel">Alle ' + (FACET_LABEL[facet] || '') + '</span>'
      + '<span class="count">' + rows.length + '</span></button>';
    keys.forEach(k => {
      const worst = groups[k].worst;
      let color = '#e2e8f0';
      Object.keys(DRIFT_RANK).forEach(s => { if (DRIFT_RANK[s] === worst) color = DRIFT_DOT[s]; });
      buf += '<button class="rail-item' + (k === state.group ? ' active' : '') + '" data-group="' + esc(k) + '">'
        + '<span class="dot" style="background:' + color + '"></span>'
        + '<span class="glabel">' + esc(k) + '</span>'
        + '<span class="count">' + groups[k].count + '</span></button>';
    });
    nav.innerHTML = buf;
    nav.querySelectorAll('.rail-item').forEach(b => {
      b.addEventListener('click', () => {
        const g = b.dataset.group;
        location.hash = g ? ('#/' + facet + '/' + encodeURIComponent(g)) : ('#/' + facet + '/');
      });
    });
  }

  function readHash() {
    let h = location.hash || '';
    h = (h.indexOf('#/') === 0) ? h.substring(2) : '';
    const slash = h.indexOf('/');
    if (slash >= 0) {
      const facet = h.substring(0, slash);
      const group = h.substring(slash + 1);
      if (['repo','org','class','role'].indexOf(facet) >= 0) {
        state.facet = facet;
        state.group = group ? decodeURIComponent(group) : null;
        const sel = document.getElementById('facet-select');
        if (sel) sel.value = state.facet;
      }
    }
  }

  function syncFromHash() { readHash(); buildRail(); applyFilters(); }

  const facetSel = document.getElementById('facet-select');
  if (facetSel) facetSel.addEventListener('change', () => {
    state.facet = facetSel.value;
    state.group = null;
    location.hash = '#/' + state.facet + '/';
    syncFromHash();
  });
  window.addEventListener('hashchange', syncFromHash);
  syncFromHash();

  // Initial-State aus URL-Params
  const params = new URLSearchParams(window.location.search);
  const initialOrg = params.get('org');
  const initialDrift = params.get('drift');
  const initialSurface = params.get('surface');
  if (initialOrg) {
    const btn = document.querySelector(`.filter-chip[data-filter-org="${initialOrg}"]`);
    if (btn) btn.click();
  }
  if (initialDrift) {
    const btn = document.querySelector(`.filter-chip[data-filter-drift="${initialDrift}"]`);
    if (btn) btn.click();
  }
  if (initialSurface) {
    const btn = document.querySelector(`.surface-master button[data-master-surface="${initialSurface}"]`);
    if (btn) btn.click();
  }
})();

// Click-to-Sort auf den Tabellen-Headern (Stufe 1b)
// Sortiert kd-row + zugehörige detail-row als Paar.
document.querySelectorAll('th.sortable').forEach(th => {
  th.addEventListener('click', () => {
    const col = parseInt(th.dataset.col, 10);
    const numeric = th.dataset.numeric === '1';
    const tbody = document.querySelector('#genesor-table tbody');
    const allRows = Array.from(tbody.querySelectorAll('tr'));
    // Paare bauen: kd-row + nachfolgende detail-row
    const pairs = [];
    for (let i = 0; i < allRows.length; i++) {
      if (allRows[i].classList.contains('kd-row')) {
        const detail = allRows[i + 1];
        pairs.push([allRows[i], detail && detail.classList.contains('detail-row') ? detail : null]);
      }
    }
    // Aktuelles Sort-Direction lesen
    const currentDir = th.classList.contains('sort-asc') ? 'asc' : (th.classList.contains('sort-desc') ? 'desc' : null);
    const newDir = currentDir === 'asc' ? 'desc' : 'asc';
    document.querySelectorAll('th.sortable').forEach(h => h.classList.remove('sort-asc', 'sort-desc'));
    th.classList.add('sort-' + newDir);
    // Werte extrahieren + sortieren
    pairs.sort(([rowA], [rowB]) => {
      const cellA = rowA.cells[col].textContent.trim();
      const cellB = rowB.cells[col].textContent.trim();
      let cmp;
      if (numeric) cmp = parseFloat(cellA) - parseFloat(cellB);
      else cmp = cellA.localeCompare(cellB, 'de');
      return newDir === 'asc' ? cmp : -cmp;
    });
    // Re-Append in neuer Reihenfolge
    pairs.forEach(([kd, detail]) => {
      tbody.appendChild(kd);
      if (detail) tbody.appendChild(detail);
    });
  });
});

// ── Repo-Linse ein-/ausklappen (localStorage-persistent) ─────────────────
(function() {
  const KEY = 'genesor_rail_collapsed';
  const layout = document.querySelector('.genesor-layout');
  if (!layout) return;
  const btnCollapse = document.getElementById('rail-collapse');
  const btnExpand = document.getElementById('rail-expand');
  function apply(collapsed) {
    layout.classList.toggle('rail-collapsed', collapsed);
    try { localStorage.setItem(KEY, collapsed ? '1' : '0'); } catch(e) {}
  }
  let saved = '0';
  try { saved = localStorage.getItem(KEY) || '0'; } catch(e) {}
  apply(saved === '1');
  if (btnCollapse) btnCollapse.addEventListener('click', () => apply(true));
  if (btnExpand) btnExpand.addEventListener('click', () => apply(false));
})();
</script>

</body>
</html>
"""


def build_genesor_html(
    records: list[dict], uc_coverage: dict | None = None, n_ucs: int = 0
) -> str:
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
        len(r.get("adr_meta", {}).get("realizes_use_cases") or []) for r in records
    )
    n_replaces = sum(
        1 for r in records if (r.get("adr_meta", {}) or {}).get("replaces_system_ref")
    )

    # Gruppieren nach Org → Repo
    by_org: dict[str, dict[str, list[dict]]] = defaultdict(lambda: defaultdict(list))
    for r in records:
        by_org[r["org"]][r["repo"]].append(r)

    table_body = _render_table_body(
        records, by_org, all_warnings, drift_by_idx, apps_index
    )
    acceptance_matrix_section = _render_acceptance_matrix(records)
    genesor_skin_options = _render_skin_options()

    return (
        _GENESOR_HEAD
        + f"""    <div class="sub">Cross-Repo · auto-generiert · {date.today().isoformat()} · Stufe 1a (statisch)</div>
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
    <div class="kv drift-status-in-sync"><span class="n">{drift_counter["in-sync"]}</span><span class="lbl">🟢 in-sync</span></div>
    <div class="kv drift-status-stale"><span class="n">{drift_counter["stale"]}</span><span class="lbl">🟡 stale</span></div>
    <div class="kv drift-status-partial"><span class="n">{drift_counter["partial"]}</span><span class="lbl">🟠 partial</span></div>
    <div class="kv drift-status-no-brief"><span class="n">{drift_counter["no-brief"]}</span><span class="lbl">⚪ no-brief</span></div>
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
"""
        + _GENESOR_TAIL
    )

"""UC-Render — Repo-UC-Index, Coverage-Matrix, Implementation-Briefs.

Extrahiert aus lineage.py (KONZ-003 Empf-1, PR4) — Code-Motion;
einzige Anpassungen: _cfg→get_cfg() (Importbindung) und __file__-Pfadtiefe.
"""
from __future__ import annotations

import html
from .config import get_cfg
from .introspect_django import _detect_auth_user_model, _detect_tenant_pattern, _inspect_dev_run, _inspect_django_models, _inspect_infra_context
from .publish import _github_delete_url, _github_edit_url
from .scan import find_mockup_html, url_for_path
from .ucs import _resolve_screen_ref, _uc_kd_targets


def _render_screen_ref(ref: str, adr_to_kd: dict, kd_mockup_url: dict) -> str:
    """related_screens-Ref → klickbare [KD]+[Mockup]-Links (platform:ADR-251 — vom UC
    in Screen-Lineage/Spec und per Deep-Link in den gerenderten Klickdummy springen).

    [KD]  = Screen-Lineage (immer vorhanden). [Mockup] = echter Klickdummy-Einstieg
    (``find_mockup_html``→``url_for_path``, identisch zur genesor-Index-Verlinkung)
    + ``#screen-<sid>`` (render_fallback/Klickdummy-JS aktiviert den Screen); nur
    emittiert, wenn ein Mockup existiert (Fallback-KDs ohne eigenen Render → kein toter Link).
    """
    resolved = _resolve_screen_ref(ref, adr_to_kd)
    if not resolved:
        return (f'<code>{html.escape(ref)}</code>'
                f'<span title="Screen nicht auflösbar" style="color:#b91c1c">&nbsp;⚠</span>')
    rp, kd, sid = resolved
    kd_url = f"./screen-lineage-{html.escape(rp)}-{html.escape(kd)}.html"
    out = (f'<span class="rs"><code>{html.escape(sid)}</code> '
           f'<a href="{kd_url}" title="Screen-Lineage / Spec">🕸 KD</a>')
    mock = kd_mockup_url.get((rp, kd))
    if mock:
        out += (f' <a href="{html.escape(mock)}#screen-{html.escape(sid)}" target="_blank" '
                f'title="Klickdummy-Screen (Mockup, Deep-Link)">🖼 Mockup</a>')
    return out + '</span>'


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
        adr_local = (k.get("data", {}).get("adr", {}) or {}).get("local") or ""
        if ":" in adr_local:
            adr_local = adr_local.split(":", 1)[1]
        if adr_local:
            adr_to_kd[(k["repo"], adr_local)] = k["kd"]

    # (repo, kd) → Mockup-Einstiegs-URL (für related_screens-[Mockup]-Deep-Links).
    # Identisch zur genesor-Index-Verlinkung; None, wenn der KD keinen eigenen Render hat.
    kd_mockup_url: dict[tuple[str, str], str] = {}
    for k in (kds or []):
        if k.get("kind", "spec") != "spec" or not k.get("path"):
            continue
        try:
            mh = find_mockup_html(k["path"].parent, k["kd"])
            mu = url_for_path(mh) if mh else None
        except (OSError, ValueError, KeyError):
            mu = None
        if mu:
            kd_mockup_url[(k["repo"], k["kd"])] = mu

    # Lineage-Link nur, wenn lineage-<repo>.html auch generiert wird: das passiert
    # in generate_per_repo_lineages NUR bei >=2 Spec-KDs (F12). Bei 1-KD-Repos
    # (z. B. apo-hub) sonst toter Nav-Link (404).
    n_repo_specs = sum(
        1 for k in (kds or []) if k.get("kind", "spec") == "spec" and k.get("repo") == repo
    )
    lineage_link = (
        f' ·\n  <a href="./lineage-{html.escape(repo)}.html">🌳 Lineage</a>'
        if n_repo_specs >= 2 else ""
    )

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
            + (" · ".join(_render_screen_ref(str(s), adr_to_kd, kd_mockup_url) for s in (uc.get("related_screens") or [])) or "—")
            + '</dd>'
        )
        if u_refs:
            details_inner += (
                '<dt style="color:#b91c1c;">⚠ unresolved</dt><dd style="color:#b91c1c;">'
                + ", ".join(f'<code>{html.escape(x)}</code>' for x in u_refs)
                + "</dd>"
            )
        try:
            rel_path = uc["source_file"].relative_to(get_cfg().repos_root / repo)
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
  <a href="./coverage.html">📊 Cross-Repo Coverage</a>{lineage_link}
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
        # S-02 (Issue #105): `description` ist Spec-Freitext und fließt via
        # `markdown.markdown(...)` (build_impl_brief_html) roh ins HTML — Python-
        # Markdown lässt eingebettetes Raw-HTML durch (kein Safe-Mode). Ein
        # `<script>` in der description wäre sonst aktiv. html.escape neutralisiert
        # das (beabsichtigtes Markdown in einer Entity-Description ist nicht erwartet;
        # der genesor-Pfad validiert die Spec nicht, daher hier escapen).
        desc = html.escape(str(edef.get("description", "")))
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

"""KD-Validierung — Acceptance-Status, Sunset-Badge, Drift, Registry.

Extrahiert aus lineage.py (KONZ-003 Empf-1, PR3) — reine Code-Motion.
"""
from __future__ import annotations

import re
from .config import get_cfg


# Per platform:ADR-213 (Cross-Repo-Ref-Format)
CROSS_REPO_REF_RE = re.compile(r"^[a-z][a-z0-9-]+:ADR-[0-9]{3}$")


_ACCEPTANCE_AXES = ("spec_signed", "ui_walked")


_ACCEPTANCE_STALE_DAYS = 60


def compute_acceptance_status(acceptance: dict | None) -> dict:
    """ADR-211 Rev 15 §Acceptance — 2 Achsen ``spec_signed`` + ``ui_walked``.

    Schema: ``{spec_signed: [{by, date, ref, scope?}], ui_walked: [{...}]}``.
    Append-only. Status pro Achse:
    - ``signed``: jüngster Eintrag ≤ 60 Tage alt
    - ``stale``:  jüngster Eintrag > 60 Tage alt (Spec-Drift-Verdacht)
    - ``missing``: keine Einträge
    Rückgabe: ``{axis: {status, latest_date, latest_by, latest_ref, age_days}}``.
    """
    from datetime import date, timedelta
    today = date.today()
    out: dict[str, dict] = {}
    accept = acceptance if isinstance(acceptance, dict) else {}
    for axis in _ACCEPTANCE_AXES:
        entries = accept.get(axis) or []
        if not isinstance(entries, list) or not entries:
            out[axis] = {"status": "missing", "latest_date": None,
                         "latest_by": None, "latest_ref": None, "age_days": None}
            continue
        # Jüngster Eintrag
        latest = None
        for e in entries:
            if not isinstance(e, dict) or not e.get("date"):
                continue
            try:
                d = date.fromisoformat(str(e["date"])[:10])
            except ValueError:
                continue
            if latest is None or d > latest["_d"]:
                latest = {**e, "_d": d}
        if latest is None:
            out[axis] = {"status": "missing", "latest_date": None,
                         "latest_by": None, "latest_ref": None, "age_days": None}
            continue
        age = (today - latest["_d"]).days
        status = "stale" if age > _ACCEPTANCE_STALE_DAYS else "signed"
        out[axis] = {
            "status": status,
            "latest_date": latest["_d"].isoformat(),
            "latest_by": str(latest.get("by") or "?"),
            "latest_ref": str(latest.get("ref") or ""),
            "age_days": age,
        }
    return out


def merge_acceptance(kd_level: dict | None, screen_level: dict | None) -> dict:
    """Screen-Acceptance erbt + extendet KD-Acceptance (append-only, beide Quellen)."""
    out: dict[str, list] = {}
    for axis in _ACCEPTANCE_AXES:
        merged = []
        for src in (kd_level or {}, screen_level or {}):
            v = src.get(axis) if isinstance(src, dict) else None
            if isinstance(v, list):
                merged.extend(v)
        if merged:
            out[axis] = merged
    return out


def build_kd_registry(records: list[dict]) -> set[str]:
    """{repo}:ADR-NNN für alle gefundenen KDs mit Spec — für Dangling-Ref-Check."""
    reg: set[str] = set()
    for r in records:
        if r.get("kind") != "spec":
            continue
        adr = (r["data"].get("adr", {}) or {}).get("local")
        if adr:
            reg.add(adr)
    return reg


def validate_kd(r: dict, kd_registry: set[str]) -> list[dict]:
    """Returnt Liste Warnings für einen KD: {severity, code, msg}."""
    warnings: list[dict] = []
    d = r["data"]

    # I1-Verstoß: render-only ohne Spec
    if r.get("kind", "spec") != "spec":
        warnings.append({
            "severity": "error", "code": "I1-NO-SPEC",
            "msg": "I1-Verstoß: klickbares HTML vorhanden, aber keine screens-spec.yaml — keine maschinenlesbare Spec, kein Vertrag.",
        })
        return warnings  # alle weiteren Checks brauchen Spec-Daten

    # I4-Format-Check für consumes_from-Refs
    for cf in d.get("consumes_from", []) or []:
        ref = (cf.get("ref") or "").strip() if isinstance(cf, dict) else ""
        if ref and not CROSS_REPO_REF_RE.match(ref):
            warnings.append({"severity": "error", "code": "I4-MALFORMED-REF",
                             "msg": f"Cross-Repo-Ref '{ref}' verletzt platform:ADR-213-Regex (^[a-z][a-z0-9-]+:ADR-[0-9]{{3}}$)."})
        elif ref and ref not in kd_registry:
            warnings.append({"severity": "warning", "code": "DANGLING-REF",
                             "msg": f"Cross-Repo-Ref '{ref}' zeigt auf keinen bekannten KD (Drift-Klasse klickdummy-adr180-collision)."})

    # I3-Sunset (F4)
    sunset_str = (d.get("off_ramp", {}) or {}).get("sunset_after")
    if sunset_str:
        try:
            from datetime import date
            yyyy_mm_dd = str(sunset_str)[:10]
            sunset = date.fromisoformat(yyyy_mm_dd)
            days_left = (sunset - date.today()).days
            if days_left < 0:
                warnings.append({"severity": "error", "code": "SUNSET-OVERDUE",
                                 "msg": f"Sunset {sunset_str} ist um {-days_left} Tage überfällig — platform:ADR-211 Rev 11 verlangt auto-deprecated."})
            elif days_left < 90:
                warnings.append({"severity": "warning", "code": "SUNSET-NEAR",
                                 "msg": f"Sunset in {days_left} Tagen — Extension via PR prüfen."})
        except ValueError:
            warnings.append({"severity": "warning", "code": "SUNSET-MALFORMED",
                             "msg": f"sunset_after '{sunset_str}' ist kein ISO-Datum."})
    elif d.get("class") in {"mock", "stub-demo", "story", "spec-demo"}:
        warnings.append({"severity": "warning", "code": "SUNSET-MISSING",
                         "msg": "class deklariert, aber kein sunset_after — Rev-11-Pflicht-Frontmatter fehlt."})

    return warnings


def compute_sunset_badge(d: dict) -> tuple[str, str]:
    """Returnt (css-class, text) für die Sunset-Spalte."""
    sunset_str = (d.get("off_ramp", {}) or {}).get("sunset_after") if isinstance(d, dict) else None
    if not sunset_str:
        return ("sunset-na", "—")
    try:
        from datetime import date
        yyyy_mm_dd = str(sunset_str)[:10]
        sunset = date.fromisoformat(yyyy_mm_dd)
        days_left = (sunset - date.today()).days
        if days_left < 0:
            return ("sunset-overdue", f"❌ {sunset_str} ({-days_left}d überfällig)")
        if days_left < 90:
            return ("sunset-near", f"⚠ {sunset_str} ({days_left}d)")
        return ("sunset-ok", sunset_str)
    except ValueError:
        return ("sunset-na", f"? {sunset_str}")


def _extract_screen_routes(record: dict) -> list[dict]:
    """Pilot-Memo §Surface-Modal: liefert pro Screen die Endpoint-Mapping-Info.

    Sucht in dieser Reihenfolge nach Routen:
      1. screens[].route (explizit)
      2. screens[].route_example (Beispiel-URL mit konkreter ID)
      3. screens[].implementation_brief.api.endpoints[].path (Fallback, primär API)

    Liefert: Liste von {screen_id, title, route, route_example, has_brief}.
    Wenn ``route`` fehlt → leere Route, Pills für Dev/Stg/Prod sind dann disabled.
    """
    d = record.get("data") or {}
    screens = d.get("screens") or []
    if not isinstance(screens, list):
        return []
    out: list[dict] = []
    for s in screens:
        if not isinstance(s, dict):
            continue
        sid = s.get("id") or ""
        if not sid:
            continue
        title = s.get("title", sid)
        route = s.get("route") or ""
        route_example = s.get("route_example") or route  # fallback
        # API-Fallback aus Brief
        brief = s.get("implementation_brief") or {}
        api_paths = []
        api_block = brief.get("api") or {}
        if isinstance(api_block, dict):
            for endpoint in (api_block.get("endpoints") or []):
                if isinstance(endpoint, dict) and endpoint.get("path"):
                    api_paths.append(endpoint["path"])
        out.append({
            "screen_id": sid,
            "title": title,
            "route": route,
            "route_example": route_example,
            "api_paths": api_paths[:3],
            "has_brief": bool(brief),
        })
    return out


def _compute_drift_status(record: dict) -> dict:
    """Pilot-Memo 2026-05-26 §0: Drift-Status pro KD.

    Berechnet:
      - brief_url + brief_age_days (falls .md/.html im genesor/impl-brief/ liegt)
      - n_screens_with_brief: wie viele Screens haben implementation_brief im Spec
      - coverage_pct: briefs_im_genesor / screens_with_brief_spec
      - drift_status:
          🟢 "in-sync"       — alle erwarteten Briefs da, brief_age <14d
          🟡 "stale"         — Briefs da aber älter als 14d
          🟠 "partial"       — nicht alle erwarteten Briefs generiert
          ⚪ "no-brief"      — Spec hat implementation_brief, aber noch keine Briefs im Genesor
          ⚫ "no-spec-brief" — Spec selbst hat keine implementation_brief-Blöcke (kein Pilot)
      - compare_url: Deep-Link zu Brief §10 (Drift-Sektion)
    """
    from datetime import datetime
    repo = record["repo"]
    kd_name = record["kd"]
    d = record.get("data") or {}
    screens = d.get("screens") or []
    if not isinstance(screens, list):
        screens = []

    # Erwartung: pro Screen mit implementation_brief-Block ein .md im genesor
    expected_briefs: list[str] = []
    for s in screens:
        if isinstance(s, dict) and s.get("implementation_brief"):
            sid = s.get("id")
            if sid:
                expected_briefs.append(sid)

    # Tatsächlich vorhandene Briefs prüfen
    actual_briefs: list[tuple[str, str, int]] = []  # (screen_id, brief_md_path, age_days)
    brief_dir = get_cfg().genesor_out / "impl-brief"
    today = datetime.now()
    for sid in expected_briefs:
        # Konvention: impl-brief/<repo>-<kd>-<screen>.md
        path = brief_dir / f"{repo}-{kd_name}-{sid}.md"
        if path.is_file():
            mtime = datetime.fromtimestamp(path.stat().st_mtime)
            age = (today - mtime).days
            actual_briefs.append((sid, str(path), age))

    n_expected = len(expected_briefs)
    n_actual = len(actual_briefs)
    coverage_pct = (n_actual / n_expected * 100) if n_expected else 0
    oldest_age = max((a for _, _, a in actual_briefs), default=0)

    # Status-Heuristik
    if n_expected == 0:
        status = "no-spec-brief"
        status_label = "kein Pilot"
        status_color = "#999"
    elif n_actual == 0:
        status = "no-brief"
        status_label = "kein Brief generiert"
        status_color = "#bbb"
    elif n_actual < n_expected:
        status = "partial"
        status_label = f"{n_actual}/{n_expected} Briefs"
        status_color = "#f59e0b"
    elif oldest_age > 14:
        status = "stale"
        status_label = f"Brief {oldest_age} d alt"
        status_color = "#eab308"
    else:
        status = "in-sync"
        status_label = "in-sync"
        status_color = "#22c55e"

    # Compare-Link: zum jüngsten Brief, anker §10 (Drift-Sektion)
    compare_url = None
    if actual_briefs:
        # nimm jüngsten (kleinstes Alter)
        sid, _path, _age = min(actual_briefs, key=lambda x: x[2])
        compare_url = f"/genesor/impl-brief-{repo}-{kd_name}-{sid}.html#§10-genesor-vs-realität-drift-spec--echtes-model"

    return {
        "n_expected_briefs": n_expected,
        "n_actual_briefs": n_actual,
        "coverage_pct": round(coverage_pct, 0),
        "oldest_brief_age_days": oldest_age,
        "status": status,
        "status_label": status_label,
        "status_color": status_color,
        "compare_url": compare_url,
    }

"""UC-JSON-Export für Genesor (KONZ-003 Empf-1).

Enthält:
  - build_uc_export_json — strukturierter JSON-Snapshot für externe Konsumenten.

Abhängigkeiten: stdlib (json, datetime) + .config (get_cfg).
Schema-Versionskonstante: read_model.UC_EXPORT_SCHEMA_VERSION (KONZ-003 Empf-3 S1).
"""

from __future__ import annotations

import json

from .config import get_cfg
from ..read_model import UC_EXPORT_SCHEMA_VERSION


def build_uc_export_json(ucs: list[dict], kds: list[dict], coverage: dict) -> str:
    """Strukturierter JSON-Export für Weiterverwendung (Workshop 2026-05-26 #5).

    Schema: ``{schema_version, generated_at, source, summary, kds, ucs, coverage}``.
    Maschinenlesbar — Konsumenten: Backstage-Plugin, Excel-Export, Linear-Sync,
    PDF-Reportgenerator. SSoT bleibt YAML im git; dieser Export ist Read-Only-
    Snapshot zum Build-Zeitpunkt.
    """
    from datetime import datetime, timezone

    cfg = get_cfg()
    real_count = coverage["uc_realized_count"]
    unres = coverage["uc_unresolved"]
    matrix = coverage["matrix"]

    # KDs (nur spec-KDs, vereinfacht)
    kds_out = []
    for kd in kds:
        if kd.get("kind", "spec") != "spec":
            continue
        d = kd.get("data", {}) or {}
        adr_local = (d.get("adr", {}) or {}).get("local") or ""
        kds_out.append(
            {
                "repo": kd["repo"],
                "kd_name": kd["kd"],
                "adr_local": adr_local,
                "klass": d.get("class"),
                "spec_role": d.get("spec_role") or "default",
                "sunset_after": (d.get("off_ramp", {}) or {}).get("sunset_after"),
                "n_screens": len(
                    [s for s in (d.get("screens") or []) if isinstance(s, dict)]
                ),
                "render_url": f"./render/{kd['repo']}-{kd['kd']}.html",
            }
        )

    # UCs (vollständig flat)
    ucs_out = []
    for uc in ucs:
        gid = f"{uc['repo']}:{uc['uc_id']}"
        try:
            rel_src = str(uc["source_file"].relative_to(cfg.repos_root))
        except (ValueError, KeyError):
            rel_src = str(uc.get("source_file", ""))
        ucs_out.append(
            {
                "uc_id_global": gid,
                "uc_id_local": uc["uc_id"],
                "repo": uc["repo"],
                "name": uc["name"],
                "primaer_akteur": uc.get("akteur") or None,
                "sekundaer_akteure": uc.get("sekundaer") or [],
                "realisiert_von_klickdummy": uc.get("realisiert_von") or None,
                "related_screens": uc.get("related_screens") or [],
                "fv_bezug": uc.get("fv_bezug") or None,
                "prio": uc.get("prio") or None,
                "status": uc.get("status") or "draft",
                "source_file": rel_src,
                "coverage": {
                    "realized_count": real_count.get(gid, 0),
                    "unresolved_refs": unres.get(gid, []),
                },
            }
        )

    # Coverage-Matrix als Liste (JSON kann keine tuple-keys)
    matrix_out = [
        {"uc_id_global": gid, "repo": r, "kd_name": k, "screens": screens}
        for (gid, r, k), screens in matrix.items()
    ]

    payload = {
        "schema_version": UC_EXPORT_SCHEMA_VERSION,
        "generated_at": datetime.now(timezone.utc)
        .isoformat(timespec="seconds")
        .replace("+00:00", "Z"),
        "source": "klickdummy_lineage.py --genesor (ADR-211 Rev 16)",
        "summary": {
            "n_ucs": len(ucs_out),
            "n_kds": len(kds_out),
            "n_realized_ucs": sum(1 for v in real_count.values() if v > 0),
            "n_coverage_cells": sum(len(v) for v in matrix.values()),
            "repos": sorted(
                {u["repo"] for u in ucs_out} | {k["repo"] for k in kds_out}
            ),
        },
        "kds": kds_out,
        "ucs": ucs_out,
        "coverage_matrix": matrix_out,
    }
    return json.dumps(payload, indent=2, ensure_ascii=False)

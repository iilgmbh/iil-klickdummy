"""genesor-Security-Sink-Fixes (Retro 2026-07-03, SI-3): S-02 raw-HTML + S-03 Path-Traversal
+ AD-6/#103 (weiche Schema-Validierung im genesor-Scan-Pfad).

Die zwei konkreten Sinks sind direkt gehärtet: `description`-Freitext (→ Markdown → HTML)
und `screens[].id` (→ Output-Dateiname) — das bleibt die primäre Verteidigungslinie,
unabhängig von der Spec-Konformität. AD-6/#103 ergänzt eine *weiche* Schema-Validierung
im genesor-Scan (`find_specs`/`find_all_repos_specs`): nicht-konforme Specs werden auf
stderr sichtbar (WARN), aber NIE ausgeschlossen — ein fataler Abbruch würde die
fleet-weite Cross-Repo-Lineage bei der ersten nicht-konformen Spec irgendeines Repos
reißen (dasselbe Regressionsrisiko wie M28-2, #122).
"""

from __future__ import annotations


# -- S-03: Path-Traversal via Screen-id im Dateinamen (Issue #106) ------------


def test_safe_seg_strips_path_traversal_chars():
    from iil_klickdummy import lineage

    assert "/" not in lineage._safe_seg("../../etc/passwd")
    assert "." not in lineage._safe_seg("../../etc/passwd")
    assert lineage._safe_seg("../../evil") == "______evil"  # '..','/' → '_'
    assert lineage._safe_seg("normal-id_1") == "normal-id_1"  # legit id unverändert
    assert lineage._safe_seg("") == "x"  # leer → sicherer Default


def test_safe_seg_prevents_directory_escape():
    """Ein bösartiger sid darf keinen Pfad-Separator ins Dateinamen-Segment bringen."""
    import pathlib
    from iil_klickdummy import lineage

    malicious = "../../../tmp/pwned"
    seg = f"repo-kd-{lineage._safe_seg(malicious)}"
    # Das Segment bleibt EIN Dateiname (kein Verzeichniswechsel).
    assert pathlib.Path(seg).name == seg
    assert ".." not in seg


# -- S-02: raw-HTML-Passthrough aus description (Issue #105) -------------------


def _rec(desc: str) -> dict:
    return {
        "repo": "demo",
        "kd": "x",
        "data": {
            "screens": [
                {
                    "id": "s1",
                    "title": "S1",
                    "implementation_brief": {"summary": "x"},
                    "konsumiert_entities": ["Evil"],
                }
            ],
            "local_entities": {"Evil": {"description": desc}},
        },
    }


def test_build_impl_brief_escapes_description_freetext():
    from iil_klickdummy.genesor.render_uc import build_impl_brief

    md = build_impl_brief(_rec("<script>window.__X__=1</script>"), "s1")
    assert md is not None
    # Der rohe Script-Tag darf NICHT im Markdown stehen — escaped als &lt;script&gt;.
    assert "<script>" not in md
    assert "&lt;script&gt;" in md


def test_impl_brief_html_has_no_raw_script_from_description():
    """End-to-End: description → build_impl_brief → build_impl_brief_html (markdown)
    darf kein aktives <script> im HTML erzeugen. `markdown` ist Paket-Runtime-Dep,
    aber der CI-Test-Job installiert es nicht separat → importorskip (wie T-01 bei
    playwright). Der Escape selbst ist markdown-frei via dem Unit-Test oben belegt."""
    import pytest

    pytest.importorskip("markdown")
    from iil_klickdummy.genesor.config import _DOMAIN_STYLES
    from iil_klickdummy.genesor.render_uc import build_impl_brief, build_impl_brief_html

    md = build_impl_brief(_rec("<script>alert(document.domain)</script>"), "s1")
    html_out = build_impl_brief_html(
        md, "demo", "x", "s1", "default", _DOMAIN_STYLES["default"]
    )
    assert "<script>alert" not in html_out
    assert "&lt;script&gt;" in html_out


# -- AD-6/#103: weiche Schema-Validierung im genesor-Scan-Pfad -----------------


def test_should_warn_on_schema_violation_without_raising(capsys):
    from pathlib import Path
    from iil_klickdummy.genesor.scan import _warn_schema_violations

    _warn_schema_violations(Path("/fake/screens-spec.yaml"), {"title": "unvollständig"})
    err = capsys.readouterr().err
    assert "WARN" in err
    assert "Schema-Verstoß" in err
    assert "/fake/screens-spec.yaml" in err


def test_should_not_warn_on_conforming_spec(capsys):
    from pathlib import Path
    from iil_klickdummy.genesor.scan import _warn_schema_violations

    conforming = {
        "spec_id": "repo:spec-test",
        "spec_version": "0.1",
        "spec_date": "2026-06-01",
        "adr": {"local": "repo:ADR-001", "conforms_to": "platform:ADR-211"},
        "class": "mock",
        "grounding": {"konzept": "-", "pilot": "-"},
        "off_ramp": {
            "policy": "-",
            "unit": "per-screen",
            "rule": "-",
            "doppelquell_grenze": "prod-release",
            "parity_runner": "-",
        },
        "personas": {"u": {"label": "U", "rolle": "u", "sieht": []}},
        "screens": [
            {
                "id": "s1",
                "title": "S1",
                "personas": ["u"],
                "purpose": "-",
                "off_ramp_status": "static",
                "parity_acceptance": [
                    {
                        "id": "s1.v",
                        "check": "visible c",
                        "assert": {"action": "visible", "selector": "[data-testid=x]"},
                    }
                ],
            }
        ],
    }
    _warn_schema_violations(Path("/fake/screens-spec.yaml"), conforming)
    assert capsys.readouterr().err == ""


def test_should_include_non_conforming_spec_in_fleet_scan_but_warn(capsys, tmp_path):
    """Fleet-weiter Scan darf bei einer kaputten Spec NICHT abbrechen oder sie
    ausschließen (M28-2-Risiko) — nur warnen. Die KD bleibt in der Ergebnisliste."""
    from iil_klickdummy.genesor import scan
    from iil_klickdummy.genesor.config import GenesorConfig, set_cfg

    kd_dir = tmp_path / "myrepo" / "klickdummy" / "broken-kd"
    kd_dir.mkdir(parents=True)
    (kd_dir / "screens-spec.yaml").write_text(
        "title: unvollständig\n", encoding="utf-8"
    )

    set_cfg(GenesorConfig(repos_root=tmp_path))
    try:
        results = scan.find_all_repos_specs()
    finally:
        set_cfg(GenesorConfig())

    kds = [r for r in results if r.get("kd") == "broken-kd"]
    assert len(kds) == 1  # NICHT ausgeschlossen
    err = capsys.readouterr().err
    assert "Schema-Verstoß" in err

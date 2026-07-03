"""genesor-Security-Sink-Fixes (Retro 2026-07-03, SI-3): S-02 raw-HTML + S-03 Path-Traversal.

Der genesor-Scan validiert Specs NICHT gegen das Schema (anders als der gen_e2e-Pfad),
darum werden die zwei konkreten Sinks direkt gehärtet: `description`-Freitext (→ Markdown → HTML)
und `screens[].id` (→ Output-Dateiname).
"""
from __future__ import annotations


# -- S-03: Path-Traversal via Screen-id im Dateinamen (Issue #106) ------------

def test_safe_seg_strips_path_traversal_chars():
    from iil_klickdummy import lineage
    assert "/" not in lineage._safe_seg("../../etc/passwd")
    assert "." not in lineage._safe_seg("../../etc/passwd")
    assert lineage._safe_seg("../../evil") == "______evil"   # '..','/' → '_'
    assert lineage._safe_seg("normal-id_1") == "normal-id_1"  # legit id unverändert
    assert lineage._safe_seg("") == "x"                        # leer → sicherer Default


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
        "repo": "demo", "kd": "x",
        "data": {
            "screens": [{
                "id": "s1", "title": "S1",
                "implementation_brief": {"summary": "x"},
                "konsumiert_entities": ["Evil"],
            }],
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
    darf kein aktives <script> im HTML erzeugen."""
    from iil_klickdummy.genesor.config import _DOMAIN_STYLES
    from iil_klickdummy.genesor.render_uc import build_impl_brief, build_impl_brief_html
    md = build_impl_brief(_rec("<script>alert(document.domain)</script>"), "s1")
    html_out = build_impl_brief_html(md, "demo", "x", "s1", "default", _DOMAIN_STYLES["default"])
    assert "<script>alert" not in html_out
    assert "&lt;script&gt;" in html_out

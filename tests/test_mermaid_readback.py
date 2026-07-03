"""M3 — Mermaid-Flow-Readback (KONZ-008, Struktur-Input-Kanal).

Der Helfer liest den vom Menschen editierten Mermaid-Flow zurück und difft ihn
gegen die Spec (SoR). Read-only: er schlägt Delta vor, schreibt nie die Spec.
"""
from __future__ import annotations

from iil_klickdummy import mermaid_readback as mr

_MMD = """flowchart TD
    a["1 — A"]
    b["2 — B"]
    c["3 — C"]

    a --> b --> c
    b -.zurück.-> a
    c -.zurück.-> b
"""


def test_should_parse_chained_solid_arrows_as_next_edges():
    nxt, back = mr.parse_flow(_MMD)
    assert ("a", "b") in nxt and ("b", "c") in nxt
    assert len(nxt) == 2


def test_should_parse_dotted_arrows_as_back_edges():
    nxt, back = mr.parse_flow(_MMD)
    assert back == {"b": "a", "c": "b"}


def test_should_report_zero_delta_when_flow_matches_spec():
    spec = {"screens": [
        {"id": "a", "next_screens": ["b"]},
        {"id": "b", "next_screens": ["c"], "back_screen": "a"},
        {"id": "c", "back_screen": "b"},
    ]}
    d = mr.diff(_MMD, spec)
    assert sum(len(v) for v in d.values()) == 0


def test_should_detect_next_edge_added_in_mermaid():
    """Mensch fügt im Mermaid eine Kante hinzu → als 'ergänzen' im Diff."""
    spec = {"screens": [
        {"id": "a"}, {"id": "b", "back_screen": "a"}, {"id": "c", "back_screen": "b"},
    ]}
    d = mr.diff(_MMD, spec)
    assert ("a", "b") in d["next_add"] and ("b", "c") in d["next_add"]


def test_should_detect_spec_edge_missing_in_mermaid():
    """Kante in Spec, aber nicht im Mermaid → als 'prüfen/entfernen'."""
    spec = {"screens": [
        {"id": "a", "next_screens": ["b", "z"]},   # a→z existiert im Mermaid nicht
        {"id": "b", "next_screens": ["c"], "back_screen": "a"},
        {"id": "c", "back_screen": "b"},
    ]}
    d = mr.diff(_MMD, spec)
    assert ("a", "z") in d["next_remove"]


def test_should_extract_mermaid_block_from_markdown_view():
    md = "# Ansicht\n\ntext\n\n```mermaid\nflowchart TD\n  a --> b\n```\n\nmehr text\n"
    import pathlib
    import tempfile
    p = pathlib.Path(tempfile.mkstemp(suffix=".md")[1])
    p.write_text(md, encoding="utf-8")
    nxt, _ = mr.parse_flow(mr._mermaid_text(p))
    assert ("a", "b") in nxt

"""Regressionstests für Issue #115 (S-04/S-05, /repo-optimize 2026-07-02).

- S-04: `date.today()` in generierten HTML-Artefakten (genesor render_lineage.py,
  render_uc.py, render_genesor.py — 7 Stellen) drehte bei jedem Rerun weiter,
  auch ohne inhaltliche Änderung → tägliches Diff-Rauschen im Auto-Publish-Pfad
  (ADR-211 §Executable-Parity-Bridge verlangt Determinismus). Fix analog zum
  `gen_sitemap._stable_spec_date`-Präzedenzfall (PR #145): ein `build_date`-
  Parameter (optional, Default `date.today()`) + `render_common.stable_build_date()`
  liest das Datum aus einem `<!-- build-date:YYYY-MM-DD -->`-Marker der
  vorhandenen Output-Datei zurück, statt es zu überschreiben.
- S-05: `sync_to_orchestrator.py` bettete einen Live-UTC-Timestamp direkt in
  `content` — das bricht die im Docstring behauptete content_hash-Idempotenz
  bei jedem Sync-Lauf. Fix: Timestamp-Zeile entfernt (kein Ersatz nötig, der
  Orchestrator selbst trackt Update-Zeiten außerhalb von content_hash).
"""

from __future__ import annotations

from iil_klickdummy.genesor.render_common import stable_build_date
from iil_klickdummy.genesor.render_genesor import build_genesor_html
from iil_klickdummy.genesor.render_lineage import build_html


# --------------------------------------------------------- stable_build_date (S-04)


def test_should_return_today_when_no_existing_file(tmp_path):
    from datetime import date

    missing = tmp_path / "index.html"
    assert stable_build_date(missing) == date.today().isoformat()


def test_should_reuse_marker_date_from_existing_file_instead_of_today(tmp_path):
    existing = tmp_path / "index.html"
    existing.write_text(
        "<html><body>content <!-- build-date:2020-01-01 --></body></html>",
        encoding="utf-8",
    )
    assert stable_build_date(existing) == "2020-01-01"


def test_should_fall_back_to_today_when_existing_file_has_no_marker(tmp_path):
    from datetime import date

    existing = tmp_path / "index.html"
    existing.write_text(
        "<html><body>legacy content, no marker</body></html>", encoding="utf-8"
    )
    assert stable_build_date(existing) == date.today().isoformat()


def test_should_build_html_embed_passed_build_date_not_today(tmp_path):
    """End-to-End: ein Rerun mit demselben `build_date` (aus stable_build_date
    einer 'gestrigen' Fixture-Datei) produziert byte-identischen Output —
    kein tägliches Diff-Rauschen mehr."""
    existing = tmp_path / "index.html"
    existing.write_text("<html><!-- build-date:2020-06-15 --></html>", encoding="utf-8")
    resolved = stable_build_date(existing)
    html_out = build_html("flowchart LR\nA-->B", [], {}, build_date=resolved)
    assert "2020-06-15" in html_out
    assert "<!-- build-date:2020-06-15 -->" in html_out


def test_should_build_genesor_html_embed_passed_build_date():
    html_out = build_genesor_html([], build_date="2019-03-03")
    assert "2019-03-03" in html_out
    assert "<!-- build-date:2019-03-03 -->" in html_out


def test_should_build_html_default_to_today_without_build_date_param():
    from datetime import date

    html_out = build_html("flowchart LR\nA-->B", [], {})
    assert date.today().isoformat() in html_out


# ------------------------------------------------------- sync_to_orchestrator (S-05)


def test_should_not_embed_live_timestamp_in_synced_content(tmp_path, monkeypatch):
    from iil_klickdummy import sync_to_orchestrator as sync_mod
    from iil_klickdummy.registry import KlickdummyMeta

    km = KlickdummyMeta(
        name="kd1",
        path="klickdummy/kd1/screens-spec.yaml",
        shell_path=None,
        spec_id="kd1",
        spec_version="0.1",
        klickdummy_class="mock",
        title="KD1",
        adr_local=None,
    )
    monkeypatch.setattr(sync_mod, "discover_versions", lambda spec_path, root: [])

    entry_a = sync_mod.klickdummy_entry(km, "org", "repo", tmp_path)
    entry_b = sync_mod.klickdummy_entry(km, "org", "repo", tmp_path)

    assert entry_a["content"] == entry_b["content"]  # keine Zeitstempel-Drift
    assert "Sync-Zeit" not in entry_a["content"]

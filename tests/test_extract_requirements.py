"""Tests für extract_requirements — v.a. das Lösch-Verhalten von gen_uc.

Regression: stale UC-*.md wurden vor v1.23 still per unlink() entfernt —
handeditierte UCs verschwanden kommentarlos. Jetzt: Warnliste + --dry-run.
"""
from __future__ import annotations

import textwrap

from iil_klickdummy import extract_requirements as xr


SPEC = textwrap.dedent("""
    spec_id: demo-spec
    spec_version: "0.1"
    screens:
      - id: uebersicht
        title: Übersicht
        personas: [Sachbearbeitung]
        purpose: Liste sehen
      - id: detail
        title: Detail
        personas: [Sachbearbeitung]
        purpose: Eintrag prüfen
""")


def _write_spec(tmp_path):
    spec = tmp_path / "screens-spec.yaml"
    spec.write_text(SPEC, encoding="utf-8")
    return spec


def test_should_write_all_requirement_skeletons(tmp_path):
    spec = _write_spec(tmp_path)
    assert xr.main([str(spec), str(tmp_path)]) == 0
    req = tmp_path / "requirements"
    assert (req / "use-cases" / "UC-01-uebersicht.md").exists()
    assert (req / "use-cases" / "UC-02-detail.md").exists()
    for name in ("fr.md", "nfr.md", "schnittstellen.md",
                 "lastenheft-skeleton.md", "pflichtenheft-skeleton.md"):
        assert (req / name).exists(), name


def test_should_delete_stale_uc_with_warning(tmp_path, capsys):
    spec = _write_spec(tmp_path)
    uc_dir = tmp_path / "requirements" / "use-cases"
    uc_dir.mkdir(parents=True)
    stale = uc_dir / "UC-99-alter-screen.md"
    stale.write_text("# handeditiert\n", encoding="utf-8")
    assert xr.main([str(spec), str(tmp_path)]) == 0
    out = capsys.readouterr().out
    assert not stale.exists()
    assert "UC-99-alter-screen.md" in out
    assert "⚠" in out  # Lösch-Warnliste, kein stilles unlink


def test_should_keep_regenerated_ucs_untouched_by_stale_cleanup(tmp_path):
    spec = _write_spec(tmp_path)
    assert xr.main([str(spec), str(tmp_path)]) == 0
    # Zweiter Lauf: aktuelle UCs werden überschrieben, nicht als stale gelöscht
    assert xr.main([str(spec), str(tmp_path)]) == 0
    uc_dir = tmp_path / "requirements" / "use-cases"
    assert sorted(p.name for p in uc_dir.glob("UC-*.md")) == [
        "UC-01-uebersicht.md", "UC-02-detail.md",
    ]


def test_dry_run_should_write_and_delete_nothing(tmp_path, capsys):
    spec = _write_spec(tmp_path)
    uc_dir = tmp_path / "requirements" / "use-cases"
    uc_dir.mkdir(parents=True)
    stale = uc_dir / "UC-99-alter-screen.md"
    stale.write_text("# handeditiert\n", encoding="utf-8")
    assert xr.main([str(spec), str(tmp_path), "--dry-run"]) == 0
    out = capsys.readouterr().out
    assert stale.exists(), "dry-run darf nicht löschen"
    assert not (tmp_path / "requirements" / "fr.md").exists(), "dry-run darf nicht schreiben"
    assert "UC-99-alter-screen.md" in out
    assert "dry-run" in out.lower()


def test_should_reject_unknown_flag(tmp_path):
    spec = _write_spec(tmp_path)
    assert xr.main([str(spec), "--nope"]) == 2

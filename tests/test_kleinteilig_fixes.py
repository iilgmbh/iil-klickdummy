"""Regressionstests für Issue #114 (A-02/A-03/A-05, /repo-optimize 2026-07-02).

- A-02: manage.py cmd_status zählte Warnings via `len(warnings) // 2` — falsch,
  sobald ein KD gleichzeitig Sunset- UND Klassen-Warnung hat (3 Zeilen/KD statt 2).
- A-03: check_i4.py dokumentierte eine Code-/Pre-Block-Ausnahme (c), implementierte
  sie aber nie → false FAILs bei ADR-Refs in Schema-Beispielzeilen.
- A-05: inventory.py DEFAULT_REPOS vergaß iil-klickdummy selbst — die eigenen
  Self-Scan-Exclusion-Patterns waren damit nie erreichbarer toter Code. Beim
  Aktivieren des Self-Scans stellte sich heraus, dass die *bestehenden*
  Exclusion-Patterns die eigenen LEGACY_PATTERN-Definitionen in inventory.py gar
  nicht abdecken (verifiziert: 8 False-Positives) — mitgefixt (Datei- statt
  Line-Pattern-Exclusion für inventory.py selbst + tests/).
"""

from __future__ import annotations

import argparse
import pathlib
from datetime import date, timedelta

from iil_klickdummy import check_i4, inventory, manage
from iil_klickdummy.registry import KlickdummyMeta


# ------------------------------------------------------------------ A-02 (manage.py)


def _km(**overrides) -> KlickdummyMeta:
    base = dict(
        name="kd1",
        path="klickdummy/kd1/screens-spec.yaml",
        shell_path=None,
        spec_id="kd1",
        spec_version="0.1",
        klickdummy_class="mock",
        title="KD1",
        adr_local="repo:ADR-001",
    )
    base.update(overrides)
    return KlickdummyMeta(**base)


def _status_args(**overrides) -> argparse.Namespace:
    base = dict(
        base=".",
        repos="repo",
        org=None,
        repo=None,
        class_=None,
        topic=None,
        sunset_due_in=30,
        json=False,
    )
    base.update(overrides)
    return argparse.Namespace(**base)


def test_should_count_warned_kds_not_warning_lines_when_kd_has_two_warnings(
    monkeypatch, capsys
):
    """Ein KD mit SOWOHL Sunset- ALS AUCH Klassen-Warnung erzeugt 3 Zeilen im
    internen `warnings`-Puffer (1 Header + 2 Messages) — `len(warnings) // 2`
    rundet das falsch auf 1 statt korrekt auf 1 KD (hier absichtlich 2 KDs mit
    je 2 Warnungen gebaut: alter Bug hätte `len(warnings)//2` = 3 gezählt statt
    korrekt 2)."""
    kds = [
        ("org", "repo", _km(name="kd1", klickdummy_class="legacy-not-allowed")),
        ("org", "repo", _km(name="kd2", klickdummy_class="also-not-allowed")),
    ]
    monkeypatch.setattr(manage, "discover_cross_repo", lambda base, repos: kds)
    # Beide KDs bekommen zusätzlich eine Sunset-Warnung (überschritten).
    monkeypatch.setattr(
        manage,
        "_adr_sunset_after",
        lambda repo_root, adr_local: date.today() - timedelta(days=5),
    )
    monkeypatch.setattr(manage, "_spec_topic", lambda spec_path: None)

    rc = manage.cmd_status(_status_args())

    err = capsys.readouterr().err
    assert rc == 1
    assert "Warnings: 2" in err  # 2 KDs mit Warnungen — nicht 3 (alter Bug)


def test_should_count_single_kd_with_one_warning_correctly(monkeypatch, capsys):
    kds = [("org", "repo", _km(name="kd1", klickdummy_class="not-allowed"))]
    monkeypatch.setattr(manage, "discover_cross_repo", lambda base, repos: kds)
    monkeypatch.setattr(manage, "_adr_sunset_after", lambda repo_root, adr_local: None)
    monkeypatch.setattr(manage, "_spec_topic", lambda spec_path: None)

    rc = manage.cmd_status(_status_args())

    err = capsys.readouterr().err
    assert rc == 1
    assert "Warnings: 1" in err


# ------------------------------------------------------------------- A-03 (check_i4.py)


def test_should_not_flag_unqualified_adr_inside_markdown_code_fence(tmp_path):
    md = tmp_path / "example.md"
    md.write_text(
        "Normal text.\n"
        "```yaml\n"
        "adr:\n"
        "  local: ADR-999\n"  # Beispielzeile im Fence — Ausnahme (c)
        "```\n",
        encoding="utf-8",
    )
    findings = check_i4.check_file(md, local=set())
    assert findings == []


def test_should_still_flag_unqualified_adr_outside_code_fence(tmp_path):
    md = tmp_path / "example.md"
    md.write_text("Siehe ADR-999 für Details.\n", encoding="utf-8")
    findings = check_i4.check_file(md, local=set())
    assert len(findings) == 1
    assert findings[0][1] == "ADR-999"


def test_should_not_flag_unqualified_adr_inside_html_pre_block_file(tmp_path):
    html = tmp_path / "example.html"
    html.write_text(
        "<p>Text</p>\n<pre><code>adr: ADR-999</code></pre>\n<p>ADR-999 unqualifiziert</p>\n",
        encoding="utf-8",
    )
    findings = check_i4.check_file(html, local=set())
    # Nur die freie Zeile außerhalb <pre><code> zählt.
    assert len(findings) == 1


# --------------------------------------------------------------------- A-05 (inventory.py)


def test_should_include_iil_klickdummy_itself_in_default_repos():
    assert "iil-klickdummy" in inventory.DEFAULT_REPOS


def test_should_self_scan_iil_klickdummy_without_false_positives():
    """Empirischer Beleg: die Exclusion-Patterns greifen jetzt auch auf die
    eigene Paket-Quelle (inventory.py definiert LEGACY_PATTERN literal als
    Regex-String — ohne Datei-Exclusion wäre das ein garantierter Self-Hit)."""
    repo_root = pathlib.Path(__file__).resolve().parents[1]
    hits = inventory._scan_repo(repo_root)
    assert hits == []

"""CLI-Fehlerzweige + main_cli()-Entry-Points (Issue #110, T-01+T-02+R12).

- T-01: install_snippets Kernlogik (Overwrite-Guard/--force/--symlink) hatte
  0 Funktions-Tests, nur hasattr (test_smoke.py::test_all_modules_present).
- T-02: check_i2 "kein vacuous pass"-Garantie (keine Klasse / nicht in ALLOWED
  / Datei fehlt) hatte keinen Regressionstest — nur die widersprüchliche-
  Doppel-Deklaration-Branche ist in test_analyse_reste.py abgedeckt.
- R12: main_cli() (der echte Console-Script-Entry-Point über sys.argv) wurde
  für check_i1/i3/i4, extract_requirements, gen_e2e, inventory nie tatsächlich
  aufgerufen (nur hasattr/callable-geprüft) — ein Arg-Parser-Fehler (z. B.
  falscher Flag-Name) wäre CI-blind gewesen.
"""

from __future__ import annotations

import json

from iil_klickdummy import check_i2, install_snippets


# ------------------------------------------------------------- install_snippets (T-01)


def test_should_refuse_overwrite_existing_target_without_force(tmp_path, capsys):
    target = tmp_path / "out"
    target.mkdir()
    (target / "stale.txt").write_text("old", encoding="utf-8")

    rc = install_snippets.main(["--target", str(target)])

    assert rc == 1
    assert "use --force" in capsys.readouterr().out
    assert (target / "stale.txt").exists()  # unangetastet


def test_should_overwrite_existing_target_with_force(tmp_path):
    target = tmp_path / "out"
    target.mkdir()
    (target / "stale.txt").write_text("old", encoding="utf-8")

    rc = install_snippets.main(["--target", str(target), "--force"])

    assert rc == 0
    assert not (target / "stale.txt").exists()  # Alt-Inhalt entfernt
    assert (target / "feedback-widget" / "widget.js").exists()


def test_should_symlink_instead_of_copy_when_flag_set(tmp_path):
    target = tmp_path / "out"

    rc = install_snippets.main(["--target", str(target), "--symlink"])

    assert rc == 0
    widget = target / "feedback-widget" / "widget.js"
    assert widget.is_symlink()
    assert widget.read_text(encoding="utf-8")  # Symlink zeigt auf echte Datei


def test_should_copy_by_default_not_symlink(tmp_path):
    target = tmp_path / "out"

    rc = install_snippets.main(["--target", str(target)])

    assert rc == 0
    widget = target / "feedback-widget" / "widget.js"
    assert widget.exists()
    assert not widget.is_symlink()


# ------------------------------------------------------------------ check_i2 (T-02)


def _i2_pair(tmp_path, body: dict) -> str:
    spec = tmp_path / "spec.json"
    spec.write_text(json.dumps(body), encoding="utf-8")
    return f"{spec}:unused.json"


def test_should_fail_when_no_class_declared(tmp_path, capsys):
    pair = _i2_pair(tmp_path, {"title": "no class here"})

    rc = check_i2.main([pair])

    assert rc == 1
    assert "keine Klasse deklariert" in capsys.readouterr().out


def test_should_fail_when_class_not_in_allowed_set(tmp_path, capsys):
    pair = _i2_pair(tmp_path, {"class": "not-a-real-class"})

    rc = check_i2.main([pair])

    assert rc == 1
    assert "nicht in" in capsys.readouterr().out


def test_should_fail_with_setup_error_when_spec_file_missing(tmp_path, capsys):
    missing = tmp_path / "does-not-exist.json"
    pair = f"{missing}:unused.json"

    rc = check_i2.main([pair])

    assert rc == 1
    assert "Datei fehlt" in capsys.readouterr().out


# --------------------------------------------------------------- main_cli() (R12)
# main() (argv-parametrisiert) ist an vielen Stellen bereits getestet — main_cli()
# selbst (der Console-Script-Entry-Point über sys.argv) nirgends. Ein defekter
# Flag-Name oder eine main()/main_cli()-Signatur-Divergenz wäre bisher CI-blind
# gewesen (nur hasattr/callable in test_smoke.py::test_all_main_cli_endpoints).


def test_should_check_i1_main_cli_return_usage_exit_code_without_args(
    monkeypatch, capsys
):
    from iil_klickdummy import check_i1

    monkeypatch.setattr("sys.argv", ["klickdummy-i1"])
    assert check_i1.main_cli() == 2
    assert "Usage" in capsys.readouterr().out


def test_should_check_i3_main_cli_return_usage_exit_code_without_args(
    monkeypatch, capsys
):
    from iil_klickdummy import check_i3

    monkeypatch.setattr("sys.argv", ["klickdummy-i3"])
    assert check_i3.main_cli() == 2
    assert "Usage" in capsys.readouterr().out


def test_should_check_i4_main_cli_return_usage_exit_code_without_args(
    monkeypatch, capsys
):
    from iil_klickdummy import check_i4

    monkeypatch.setattr("sys.argv", ["klickdummy-i4"])
    assert check_i4.main_cli() == 2
    assert "Usage" in capsys.readouterr().out


def test_should_extract_requirements_main_cli_return_usage_exit_code_without_args(
    monkeypatch, capsys
):
    from iil_klickdummy import extract_requirements

    monkeypatch.setattr("sys.argv", ["klickdummy-extract-requirements"])
    assert extract_requirements.main_cli() == 2
    assert "Usage" in capsys.readouterr().out


def test_should_gen_e2e_main_cli_return_usage_exit_code_without_args(
    monkeypatch, capsys
):
    from iil_klickdummy import gen_e2e

    monkeypatch.setattr("sys.argv", ["klickdummy-gen-e2e"])
    assert gen_e2e.main_cli() == 2
    assert "Usage" in capsys.readouterr().out


def test_should_inventory_main_cli_scan_isolated_tmp_base_cleanly(
    monkeypatch, tmp_path, capsys
):
    from iil_klickdummy import inventory

    # --base zeigt auf ein leeres tmp_path statt echtem ~/github (deterministisch,
    # keine Live-Filesystem-Abhängigkeit) — alle DEFAULT_REPOS fehlen dort =>
    # "NOT PRESENT (skip)" je Repo, 0 Treffer, Exit 0.
    monkeypatch.setattr("sys.argv", ["klickdummy-inventory", "--base", str(tmp_path)])
    assert inventory.main_cli() == 0
    assert "0 echte Drift-Treffer" in capsys.readouterr().out

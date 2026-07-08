"""Regressionstests für Issue #113 (A-01/A-04, /repo-optimize 2026-07-02).

- A-04: 7 Module (check_i1/i2/i3, manage, gen_e2e, extract_requirements,
  registry) hatten je eine fast-identische Ad-hoc-YAML/JSON-Loader-Funktion.
  Konsolidiert in `read_model.load_spec_yaml()` — jeder Aufrufer behält
  seinen eigenen Fail-Modus (fatal exit / soft {} / eigene Fehlermeldung).
- A-01: extract_requirements.load_spec hatte KEIN yaml.YAMLError-Handling,
  obwohl der Docstring-Kontrakt "Exit: 1 Schema-Fehler" das voraussetzt —
  ungültiges YAML riss vorher einen rohen Traceback statt eines FAIL-Exits.
"""

from __future__ import annotations

import pytest

from iil_klickdummy import extract_requirements as xr
from iil_klickdummy.read_model import load_spec_yaml


INVALID_YAML = "foo: [unclosed\n  bar: baz\n"


# --------------------------------------------------------- load_spec_yaml (A-04)


def test_should_parse_yaml_by_extension(tmp_path):
    p = tmp_path / "spec.yaml"
    p.write_text("a: 1\nb: [2, 3]\n", encoding="utf-8")
    assert load_spec_yaml(p) == {"a": 1, "b": [2, 3]}


def test_should_parse_yml_extension_too(tmp_path):
    p = tmp_path / "spec.yml"
    p.write_text("a: 1\n", encoding="utf-8")
    assert load_spec_yaml(p) == {"a": 1}


def test_should_parse_json_by_extension(tmp_path):
    p = tmp_path / "schema.json"
    p.write_text('{"a": 1, "b": [2, 3]}', encoding="utf-8")
    assert load_spec_yaml(p) == {"a": 1, "b": [2, 3]}


def test_should_accept_str_path_not_only_pathlib_path(tmp_path):
    p = tmp_path / "spec.yaml"
    p.write_text("a: 1\n", encoding="utf-8")
    assert load_spec_yaml(str(p)) == {"a": 1}


def test_should_raise_yaml_error_on_invalid_yaml_not_swallow_it(tmp_path):
    import yaml

    p = tmp_path / "spec.yaml"
    p.write_text(INVALID_YAML, encoding="utf-8")
    with pytest.raises(yaml.YAMLError):
        load_spec_yaml(p)


def test_should_raise_oserror_on_missing_file(tmp_path):
    missing = tmp_path / "does-not-exist.yaml"
    with pytest.raises(OSError):
        load_spec_yaml(missing)


# ----------------------------------------------------- Per-Aufrufer-Fail-Modus (A-04)


def test_should_check_i1_still_dispatch_yaml_vs_json_by_extension(tmp_path):
    from iil_klickdummy import check_i1

    yaml_p = tmp_path / "spec.yaml"
    yaml_p.write_text("a: 1\n", encoding="utf-8")
    json_p = tmp_path / "schema.json"
    json_p.write_text('{"a": 1}', encoding="utf-8")
    assert check_i1.load(str(yaml_p)) == {"a": 1}
    assert check_i1.load(str(json_p)) == {"a": 1}


def test_should_manage_load_spec_yaml_stay_soft_fail_on_missing_file(tmp_path):
    from iil_klickdummy import manage

    missing = tmp_path / "does-not-exist.yaml"
    assert manage._load_spec_yaml(missing) == {}  # weiterhin kein Exception-Raise


def test_should_manage_load_spec_yaml_stay_soft_fail_on_invalid_yaml(tmp_path):
    from iil_klickdummy import manage

    p = tmp_path / "spec.yaml"
    p.write_text(INVALID_YAML, encoding="utf-8")
    assert manage._load_spec_yaml(p) == {}  # weiterhin kein Exception-Raise


def test_should_registry_load_spec_stay_soft_fail_on_invalid_yaml(tmp_path):
    from iil_klickdummy import registry

    p = tmp_path / "spec.yaml"
    p.write_text(INVALID_YAML, encoding="utf-8")
    assert registry._load_spec(p) == {}  # weiterhin kein Exception-Raise


# ------------------------------------------------------------- extract_requirements (A-01)


def test_should_load_spec_exit_1_with_friendly_message_on_invalid_yaml(
    tmp_path, capsys
):
    """A-01: vorher riss das ungueltige YAML einen rohen yaml.YAMLError-
    Traceback statt des dokumentierten 'Exit: 1 Schema-Fehler'-Kontrakts."""
    p = tmp_path / "spec.yaml"
    p.write_text(INVALID_YAML, encoding="utf-8")
    with pytest.raises(SystemExit) as exc_info:
        xr.load_spec(p)
    assert exc_info.value.code == 1
    assert "Spec-YAML ungültig" in capsys.readouterr().out


def test_should_load_spec_exit_1_on_missing_file(tmp_path, capsys):
    missing = tmp_path / "does-not-exist.yaml"
    with pytest.raises(SystemExit) as exc_info:
        xr.load_spec(missing)
    assert exc_info.value.code == 1
    assert "Spec fehlt" in capsys.readouterr().out


def test_should_load_spec_parse_valid_yaml_unchanged(tmp_path):
    p = tmp_path / "spec.yaml"
    p.write_text("spec_id: demo\nscreens: []\n", encoding="utf-8")
    assert xr.load_spec(p) == {"spec_id": "demo", "screens": []}

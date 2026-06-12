"""Tests für die Invarianten-Checks I1/I3/I4 (check_i1, check_i3, check_i4).

Bisher hatten diese Gates nur Import-Smoke-Tests; hier werden die
Pass/Fail-Semantiken festgenagelt — inkl. der Regressionen:
  - I3: fehlendes `off_ramp_status` ist FAIL, kein stiller 'static'-Default
  - I4: ADR-Whitelist hängt am Scan-Root, nicht am CWD
"""
from __future__ import annotations

import json
import textwrap

from iil_klickdummy import check_i1, check_i3, check_i4


# ---------------------------------------------------------------- I1 helpers

SIMPLE_SCHEMA = {
    "type": "object",
    "required": ["spec_id"],
    "properties": {"spec_id": {"type": "string"}},
}


def _write_pair(tmp_path, spec_text: str, schema: dict = SIMPLE_SCHEMA):
    spec = tmp_path / "spec.yaml"
    spec.write_text(spec_text, encoding="utf-8")
    schema_p = tmp_path / "schema.json"
    schema_p.write_text(json.dumps(schema), encoding="utf-8")
    return f"{spec}:{schema_p}"


# ----------------------------------------------------------------------- I1

def test_i1_should_pass_on_schema_conformant_spec(tmp_path):
    pair = _write_pair(tmp_path, "spec_id: demo\n")
    assert check_i1.main([pair]) == 0


def test_i1_should_fail_on_schema_violation(tmp_path):
    pair = _write_pair(tmp_path, "spec_id: 42\n")  # int statt string
    assert check_i1.main([pair]) == 1


def test_i1_should_fail_on_empty_spec_file(tmp_path):
    pair = _write_pair(tmp_path, "")  # yaml.safe_load("") -> None
    assert check_i1.main([pair]) == 1


def test_i1_should_fail_on_missing_spec_file(tmp_path):
    schema_p = tmp_path / "schema.json"
    schema_p.write_text(json.dumps(SIMPLE_SCHEMA), encoding="utf-8")
    assert check_i1.main([f"{tmp_path / 'nope.yaml'}:{schema_p}"]) == 1


def test_i1_should_fail_on_entry_without_colon():
    assert check_i1.main(["just-a-path-no-colon"]) == 1


# ---------------------------------------------------------------- I3 helpers

def _i3_spec(tmp_path, body: str) -> str:
    spec = tmp_path / "spec.yaml"
    spec.write_text(textwrap.dedent(body), encoding="utf-8")
    # check_i3 nutzt nur den Teil vor dem ':'
    return f"{spec}:unused-schema.json"


# ----------------------------------------------------------------------- I3

def test_i3_should_pass_when_all_screens_have_valid_status(tmp_path):
    pair = _i3_spec(tmp_path, """
        off_ramp:
          policy: test
          doppelquell_grenze: prod-release
        screens:
          - id: s1
            off_ramp_status: static
          - id: s2
            off_ramp_status: parity-green
    """)
    assert check_i3.main([pair]) == 0


def test_i3_should_fail_when_off_ramp_status_missing(tmp_path):
    # Regression: vorher Default 'static' -> False-Pass
    pair = _i3_spec(tmp_path, """
        off_ramp:
          policy: test
          doppelquell_grenze: prod-release
        screens:
          - id: s1
            off_ramp_status: static
          - id: s2
            title: ohne Status
    """)
    assert check_i3.main([pair]) == 1


def test_i3_should_fail_on_invalid_status_value(tmp_path):
    pair = _i3_spec(tmp_path, """
        off_ramp:
          policy: test
          doppelquell_grenze: prod-release
        screens:
          - id: s1
            off_ramp_status: definitely-not-a-status
    """)
    assert check_i3.main([pair]) == 1


def test_i3_should_fail_without_off_ramp_block(tmp_path):
    pair = _i3_spec(tmp_path, """
        screens:
          - id: s1
            off_ramp_status: static
    """)
    assert check_i3.main([pair]) == 1


def test_i3_should_fail_on_wrong_doppelquell_grenze(tmp_path):
    pair = _i3_spec(tmp_path, """
        off_ramp:
          policy: test
          doppelquell_grenze: irgendwann
        screens: []
    """)
    assert check_i3.main([pair]) == 1


# ---------------------------------------------------------------- I4 helpers

def _make_repo(tmp_path, *, local_adr: str = "ADR-042"):
    repo = tmp_path / "repo"
    adr_dir = repo / "docs" / "adr"
    adr_dir.mkdir(parents=True)
    (adr_dir / f"{local_adr}-beispiel.md").write_text(
        f"# {local_adr} Beispiel\n", encoding="utf-8"
    )
    return repo


# ----------------------------------------------------------------------- I4

def test_i4_should_pass_local_adr_ref_regardless_of_cwd(tmp_path, monkeypatch):
    # Regression: ADR_DIR war CWD-relativ -> Whitelist leer bei fremdem CWD
    repo = _make_repo(tmp_path)
    (repo / "docs" / "uebersicht.md").write_text(
        "Siehe ADR-042 für Details.\n", encoding="utf-8"
    )
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    monkeypatch.chdir(elsewhere)
    assert check_i4.main([str(repo / "docs")]) == 0


def test_i4_should_fail_on_unqualified_foreign_adr(tmp_path):
    repo = _make_repo(tmp_path)
    (repo / "docs" / "uebersicht.md").write_text(
        "Siehe ADR-999 für Details.\n", encoding="utf-8"
    )
    assert check_i4.main([str(repo / "docs")]) == 1


def test_i4_should_pass_qualified_cross_repo_ref(tmp_path):
    repo = _make_repo(tmp_path)
    (repo / "docs" / "uebersicht.md").write_text(
        "Konform zu platform:ADR-211.\n", encoding="utf-8"
    )
    assert check_i4.main([str(repo / "docs")]) == 0


def test_i4_find_adr_dir_should_resolve_from_repo_root_and_docs(tmp_path):
    repo = _make_repo(tmp_path)
    assert check_i4.find_adr_dir(repo) == (repo / "docs" / "adr").resolve()
    assert check_i4.find_adr_dir(repo / "docs") == (repo / "docs" / "adr").resolve()


def test_i4_should_fail_setup_on_missing_root(tmp_path):
    assert check_i4.main([str(tmp_path / "missing")]) == 2

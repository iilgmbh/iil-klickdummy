"""Tests für read_model.py — Schema-Konstanten + TypedDict-Roundtrip (KONZ-003 Empf-3 S1, #70)."""

from __future__ import annotations

import json


def test_should_export_schema_version_constant_be_stable():
    from iil_klickdummy.read_model import UC_EXPORT_SCHEMA_VERSION

    assert UC_EXPORT_SCHEMA_VERSION == "1.0"


def test_should_discovery_schema_constants_be_stable():
    from iil_klickdummy.read_model import (
        API_VERSION,
        EMBEDDING_INPUT_SCHEMA,
        REGISTRY_SCHEMA_VERSION,
    )

    assert REGISTRY_SCHEMA_VERSION == "v1.6"
    assert API_VERSION == "v1"
    assert EMBEDDING_INPUT_SCHEMA == "v1"


def test_should_uc_export_envelope_typeddict_have_required_keys():
    from iil_klickdummy.read_model import UcExportEnvelope

    required = {
        "schema_version",
        "generated_at",
        "source",
        "summary",
        "kds",
        "ucs",
        "coverage_matrix",
    }
    assert required == set(UcExportEnvelope.__annotations__)


def test_should_discovery_typeddicts_have_required_keys():
    from iil_klickdummy.read_model import DiscoveryEnvelope, DiscoverySnapshot

    assert "entries" in DiscoveryEnvelope.__annotations__
    assert "api_version" in DiscoveryEnvelope.__annotations__
    assert "count" in DiscoverySnapshot.__annotations__
    assert "sha256" in DiscoverySnapshot.__annotations__


def test_should_build_uc_export_json_output_match_uc_export_envelope_schema(tmp_path):
    """Roundtrip: build_uc_export_json → JSON-parse → alle UcExportEnvelope-Felder vorhanden."""
    from iil_klickdummy.genesor.config import GenesorConfig, set_cfg
    from iil_klickdummy.genesor.export import build_uc_export_json
    from iil_klickdummy.read_model import UC_EXPORT_SCHEMA_VERSION, UcExportEnvelope

    set_cfg(GenesorConfig(repos_root=tmp_path))

    source_file = tmp_path / "test-repo" / "klickdummy" / "demo" / "screens-spec.yaml"
    source_file.parent.mkdir(parents=True)
    source_file.touch()

    ucs = [
        {
            "repo": "test-repo",
            "uc_id": "UC-01",
            "name": "Anmelden",
            "source_file": source_file,
        }
    ]
    kds = [
        {
            "repo": "test-repo",
            "kd": "demo",
            "kind": "spec",
            "data": {
                "adr": {"local": "ADR-001"},
                "class": "mock",
                "spec_role": "default",
                "screens": [],
            },
        }
    ]
    coverage = {
        "uc_realized_count": {},
        "uc_unresolved": {},
        "matrix": {},
    }

    result = build_uc_export_json(ucs, kds, coverage)
    payload = json.loads(result)

    # Alle UcExportEnvelope-Felder vorhanden
    for key in UcExportEnvelope.__annotations__:
        assert key in payload, f"Fehlendes Feld im Export: {key!r}"

    # Schema-Version stimmt mit Konstante überein
    assert payload["schema_version"] == UC_EXPORT_SCHEMA_VERSION

    # UC-Eintrag hat alle UcExportRow-Pflichtfelder
    from iil_klickdummy.read_model import UcExportRow

    assert len(payload["ucs"]) == 1
    uc_row = payload["ucs"][0]
    for key in UcExportRow.__annotations__:
        assert key in uc_row, f"Fehlendes UC-Feld im Export: {key!r}"

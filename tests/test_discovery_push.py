"""Tests für discovery_push.py (v1.5 PoC, platform:ADR-215)."""
from __future__ import annotations

import pathlib

import pytest

from iil_klickdummy import discovery_push


@pytest.fixture
def forms_spec(tmp_path: pathlib.Path) -> pathlib.Path:
    """Erzeugt minimale screens-spec.yaml (forms-Genre)."""
    repo_root = tmp_path / "meiki-hub"
    spec_dir = repo_root / "docs/01-architektur/mockups/test-klickdummy"
    spec_dir.mkdir(parents=True)
    (repo_root / ".git").mkdir()
    (repo_root / ".git" / "config").write_text(
        '[remote "origin"]\n  url = git@github.com:meiki-lra/meiki-hub.git\n',
        encoding="utf-8",
    )
    spec_path = spec_dir / "screens-spec.yaml"
    spec_path.write_text(
        """$schema: ./screens-spec.schema.json
spec_id: meiki:klickdummy-spec-test
spec_version: "0.1"
title: Test-Klickdummy
class: mock
sunset_after: "2027-05-21"
adr:
  local: meiki:ADR-999
  conforms_to: platform:ADR-211
  sister_of:
    - sqf-hub:ADR-003
personas:
  sachbearbeiter:
    label: Sachbearbeiter:in
  teamleitung:
    label: Teamleitung
screens:
  - id: cockpit
    title: Cockpit
    personas: [sachbearbeiter]
    purpose: Übersicht der Fristen
    parity_acceptance:
      - id: cockpit.ampel-vollstaendig
        check: Alle Ampel-Zustände summieren zu n_gesamt
""",
        encoding="utf-8",
    )
    return spec_path


@pytest.fixture
def bot_spec(tmp_path: pathlib.Path) -> pathlib.Path:
    """Erzeugt minimale bot-spec.yaml (conversation-Genre)."""
    repo_root = tmp_path / "sqf-hub"
    spec_dir = repo_root / "klickdummy/af1"
    spec_dir.mkdir(parents=True)
    (repo_root / ".git").mkdir()
    (repo_root / ".git" / "config").write_text(
        '[remote "origin"]\n  url = git@github.com:bahn-sqf/sqf-hub.git\n',
        encoding="utf-8",
    )
    spec_path = spec_dir / "bot-spec.yaml"
    spec_path.write_text(
        """bot_id: sqf-hub:af1-test
bot_version: "0.1"
title: Test-Bot
class: mock
sunset_after: "2027-05-21"
adr:
  local: sqf-hub:ADR-999
  conforms_to: platform:ADR-211
personas:
  regionalleiter:
    label: Regionalleiter
topics:
  - id: tages-summary
    name: Wie war der Tag?
    description: Verdichtete Tageslage
    triggers:
      - Wie war der Tag?
      - Tageslage
""",
        encoding="utf-8",
    )
    return spec_path


def test_should_detect_forms_genre_for_screens_spec(forms_spec, tmp_path):
    import yaml

    spec = yaml.safe_load(forms_spec.read_text(encoding="utf-8"))
    assert discovery_push._detect_genre(spec) == "forms"


def test_should_detect_conversation_genre_for_bot_spec(bot_spec, tmp_path):
    import yaml

    spec = yaml.safe_load(bot_spec.read_text(encoding="utf-8"))
    assert discovery_push._detect_genre(spec) == "conversation"


def test_should_build_embedding_text_from_forms_spec(forms_spec):
    import yaml

    spec = yaml.safe_load(forms_spec.read_text(encoding="utf-8"))
    text = discovery_push._build_embedding_text(spec)
    assert "Test-Klickdummy" in text
    assert "Cockpit" in text
    assert "Übersicht der Fristen" in text
    assert "Alle Ampel-Zustände" in text


def test_should_build_embedding_text_from_bot_spec(bot_spec):
    import yaml

    spec = yaml.safe_load(bot_spec.read_text(encoding="utf-8"))
    text = discovery_push._build_embedding_text(spec)
    assert "Test-Bot" in text
    assert "Wie war der Tag?" in text
    assert "Verdichtete Tageslage" in text


def test_should_extract_personas_from_spec(forms_spec):
    import yaml

    spec = yaml.safe_load(forms_spec.read_text(encoding="utf-8"))
    assert discovery_push._extract_personas(spec) == ["sachbearbeiter", "teamleitung"]


def test_should_detect_org_from_git_remote(forms_spec):
    # tmp_path / meiki-hub / docs / 01-architektur / mockups / test-klickdummy / spec
    repo_root = forms_spec.parents[4]
    org = discovery_push._detect_org_from_repo(repo_root)
    assert org == "meiki-lra"


def test_should_build_discovery_entry_with_v15_schema(forms_spec):
    import yaml

    repo_root = forms_spec.parents[4]
    spec = yaml.safe_load(forms_spec.read_text(encoding="utf-8"))
    entry = discovery_push.build_discovery_entry(repo_root, forms_spec, spec)

    # v1.5-Schema-Felder
    assert entry["schema_version"] == "v1.5"
    assert entry["spec_id"] == "meiki:klickdummy-spec-test"
    assert entry["version"] == "0.1"
    assert entry["klickdummy_class"] == "mock"
    assert entry["adr"] == "meiki:ADR-999"
    assert entry["conforms_to"] == "platform:ADR-211"
    assert entry["sister_of"] == ["sqf-hub:ADR-003"]
    assert entry["repo"] == "meiki-lra/meiki-hub"
    assert entry["genre"] == "forms"
    assert entry["personas"] == ["sachbearbeiter", "teamleitung"]
    assert "Test-Klickdummy" in entry["embedding_text"]
    assert entry["sunset_after"] == "2027-05-21"
    assert "T" in entry["last_seen"]  # ISO-Format


def test_should_build_conversation_entry_with_correct_genre(bot_spec):
    import yaml

    # tmp_path / sqf-hub / klickdummy / af1 / bot-spec.yaml
    repo_root = bot_spec.parents[2]
    spec = yaml.safe_load(bot_spec.read_text(encoding="utf-8"))
    entry = discovery_push.build_discovery_entry(repo_root, bot_spec, spec)

    assert entry["genre"] == "conversation"
    assert entry["spec_id"] == "sqf-hub:af1-test"
    assert entry["repo"] == "bahn-sqf/sqf-hub"
    assert entry["personas"] == ["regionalleiter"]


def test_should_cap_embedding_text_length():
    """Embedding-Text wird bei max_chars (default 4096) gecappt."""
    huge_spec = {
        "title": "x" * 10000,
        "screens": [
            {"title": "y" * 5000, "purpose": "z" * 5000}
        ],
    }
    text = discovery_push._build_embedding_text(huge_spec, max_chars=100)
    assert len(text) == 100
    assert text.endswith("…")


def test_should_use_default_endpoint_from_env(monkeypatch):
    monkeypatch.setenv("KLICKDUMMY_DISCOVERY_ENDPOINT", "https://custom.example.com/api")
    # discovery_push.DEFAULT_ENDPOINT is captured at import — re-import to test
    import importlib

    from iil_klickdummy import discovery_push as dp

    importlib.reload(dp)
    assert dp.DEFAULT_ENDPOINT == "https://custom.example.com/api"

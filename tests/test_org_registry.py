"""Org-Registry-Externalisierung (Codebase-Analyse 2026-06, KONZ-003-Beifang).

detect_org/app_display_names lesen platform/registry/canonical.yaml (SSoT,
ADR-234) unter --repos-root; ohne platform-Checkout greift die Code-Heuristik.
"""
from __future__ import annotations

import pytest
import yaml

from iil_klickdummy.genesor import scan
from iil_klickdummy.genesor.config import GenesorConfig, set_cfg


@pytest.fixture
def repos_root(tmp_path):
    """Frisches repos_root als aktive Config; Cache + Config danach zurücksetzen."""
    set_cfg(GenesorConfig(repos_root=tmp_path))
    scan._ORG_REGISTRY_CACHE.clear()
    yield tmp_path
    scan._ORG_REGISTRY_CACHE.clear()
    set_cfg(GenesorConfig())


def _write_canonical(root, meta: dict) -> None:
    reg_dir = root / "platform" / "registry"
    reg_dir.mkdir(parents=True)
    (reg_dir / "canonical.yaml").write_text(
        yaml.safe_dump({"meta": meta, "repos": {}}), encoding="utf-8")


_META = {
    "server": {"github_org": "achimdehnert"},
    "repo_owner": {"iil-klickdummy": "iilgmbh", "spezial-hub": "kunde-x"},
    "owner_prefix_rules": [
        {"prefix": "meiki-", "owner": "meiki-lra"},
        {"prefix": "ttz-", "owner": "ttz-lif"},
    ],
    "app_display_names": {"meiki-hub": "MEiKI · LRA-Plattform"},
}


def test_should_use_registry_repo_owner_before_prefix_rules(repos_root):
    _write_canonical(repos_root, _META)
    assert scan.detect_org("spezial-hub") == "kunde-x"
    assert scan.detect_org("iil-klickdummy") == "iilgmbh"


def test_should_apply_prefix_rules_for_unlisted_repos(repos_root):
    _write_canonical(repos_root, _META)
    assert scan.detect_org("meiki-hub") == "meiki-lra"
    assert scan.detect_org("ttz-irgendwas") == "ttz-lif"


def test_should_fall_back_to_default_owner_from_github_org(repos_root):
    _write_canonical(repos_root, _META)
    assert scan.detect_org("unbekanntes-repo") == "achimdehnert"


def test_should_use_code_heuristic_without_platform_checkout(repos_root):
    # kein platform/-Verzeichnis unter repos_root
    assert scan.get_org_registry() is None
    assert scan.detect_org("meiki-hub") == "meiki-lra"
    assert scan.detect_org("sqf-hub") == "bahn-sqf"
    assert scan.detect_org("unbekanntes-repo") == "achimdehnert"


def test_should_use_code_heuristic_when_prefix_rules_missing(repos_root):
    # Ältere platform-Version: repo_owner existiert (seit 2026-06-06), aber keine
    # owner_prefix_rules — Mapping ist unvollständig, meiki-* fiele auf den
    # Default durch. Muss komplett auf die Code-Heuristik zurückfallen.
    _write_canonical(repos_root, {
        "server": {"github_org": "achimdehnert"},
        "repo_owner": {"iil-relaunch": "iilgmbh"},
    })
    assert scan.get_org_registry() is None
    assert scan.detect_org("meiki-hub") == "meiki-lra"
    assert scan.detect_org("iil-testkit") == "iilgmbh"


def test_should_survive_broken_canonical_yaml(repos_root):
    reg_dir = repos_root / "platform" / "registry"
    reg_dir.mkdir(parents=True)
    (reg_dir / "canonical.yaml").write_text("{kaputt: [", encoding="utf-8")
    assert scan.get_org_registry() is None
    assert scan.detect_org("meiki-hub") == "meiki-lra"


def test_should_expose_app_display_names(repos_root):
    _write_canonical(repos_root, _META)
    reg = scan.get_org_registry()
    assert reg is not None
    assert reg["app_display_names"]["meiki-hub"] == "MEiKI · LRA-Plattform"


def test_should_cache_per_repos_root(repos_root):
    _write_canonical(repos_root, _META)
    first = scan.get_org_registry()
    # Datei nachträglich löschen — Cache liefert weiterhin das geladene Mapping
    (repos_root / "platform" / "registry" / "canonical.yaml").unlink()
    assert scan.get_org_registry() is first

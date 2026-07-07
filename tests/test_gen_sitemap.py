"""klickdummy-gen-sitemap — repo-agnostischer Sitemap-Generator (extrahiert aus risk-hub).

Deckt: Baum-Aufbau aus kd_children, Waisen-Erkennung, Artefakt-Schreiben
(kd-tree.json/.js, sitemap/index.html, sitemap/screens-spec.yaml) und
Repo-Name-Parametrisierung (kein hartkodiertes "risk-hub" mehr).
"""

from __future__ import annotations

import json
import pathlib

import yaml


def _write_spec(kd_root: pathlib.Path, name: str, spec: dict) -> None:
    d = kd_root / name
    d.mkdir(parents=True, exist_ok=True)
    (d / "screens-spec.yaml").write_text(
        yaml.safe_dump(spec, sort_keys=False), encoding="utf-8"
    )
    (d / "index.html").write_text("<html></html>", encoding="utf-8")


def _root_spec(spec_id: str, title: str, children: list[str] | None = None) -> dict:
    return {
        "spec_id": spec_id,
        "title": title,
        "spec_role": "root",
        "class": "mock",
        "kd_children": children or [],
        "off_ramp": {"status_overall": "Phase A"},
        "screens": [{"id": "s1", "off_ramp_status": "static"}],
    }


def test_gen_sitemap_module_present():
    from iil_klickdummy import gen_sitemap

    assert callable(getattr(gen_sitemap, "main_cli", None))
    assert callable(getattr(gen_sitemap, "generate", None))


def test_generate_builds_parent_child_tree_and_flags_orphan(tmp_path):
    from iil_klickdummy import gen_sitemap

    kd_root = tmp_path / "klickdummy"
    _write_spec(
        kd_root,
        "hub",
        _root_spec("acme:klickdummy-spec-hub", "Hub", ["acme:klickdummy-spec-child"]),
    )
    _write_spec(
        kd_root,
        "child",
        {**_root_spec("acme:klickdummy-spec-child", "Child"), "spec_role": "branch"},
    )
    _write_spec(
        kd_root,
        "lonely",
        {**_root_spec("acme:klickdummy-spec-lonely", "Lonely"), "spec_role": "branch"},
    )

    tree = gen_sitemap.generate(tmp_path, adr_local="acme:ADR-001", repo_name="acme")

    assert tree["roots"] == ["acme:klickdummy-spec-hub"]
    hub = tree["nodes"]["acme:klickdummy-spec-hub"]
    assert hub["children"] == ["acme:klickdummy-spec-child"]
    lonely = tree["nodes"]["acme:klickdummy-spec-lonely"]
    assert lonely["parent"] is None and lonely["role"] != "root"


def test_generate_writes_all_artifacts_with_repo_name_not_hardcoded(tmp_path):
    from iil_klickdummy import gen_sitemap

    kd_root = tmp_path / "klickdummy"
    _write_spec(kd_root, "hub", _root_spec("acme:klickdummy-spec-hub", "Hub"))

    gen_sitemap.generate(tmp_path, adr_local="acme:ADR-001", repo_name="acme")

    tree_json = json.loads((kd_root / "_shared" / "kd-tree.json").read_text())
    assert "acme:klickdummy-spec-hub" in tree_json["nodes"]
    assert (kd_root / "_shared" / "kd-tree.js").exists()

    html = (kd_root / "sitemap" / "index.html").read_text()
    assert "acme" in html
    assert "risk-hub" not in html

    spec = yaml.safe_load((kd_root / "sitemap" / "screens-spec.yaml").read_text())
    assert spec["spec_id"] == "acme:klickdummy-spec-sitemap"
    assert spec["adr"]["local"] == "acme:ADR-001"
    assert spec["adr"]["conforms_to"] == "platform:ADR-211"


def test_generate_defaults_repo_name_to_directory_name(tmp_path):
    from iil_klickdummy import gen_sitemap

    repo_root = tmp_path / "some-repo"
    kd_root = repo_root / "klickdummy"
    _write_spec(kd_root, "hub", _root_spec("some-repo:klickdummy-spec-hub", "Hub"))

    tree = gen_sitemap.generate(repo_root, adr_local="some-repo:ADR-001")

    assert tree["roots"] == ["some-repo:klickdummy-spec-hub"]
    html = (kd_root / "sitemap" / "index.html").read_text()
    assert "some-repo" in html


def test_main_cli_usage_without_args_returns_exit_code_2(capsys):
    from iil_klickdummy import gen_sitemap

    rc = gen_sitemap.main([])

    assert rc == 2
    assert "Usage" in capsys.readouterr().out

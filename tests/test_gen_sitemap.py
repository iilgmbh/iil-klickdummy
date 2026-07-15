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


def test_generate_finds_specs_rendered_as_shell_html(tmp_path):
    """Issue #181: die neuere /klickdummy-Skill-Kette (genesor-Render) schreibt
    shell.html statt index.html — der Scanner darf solche Specs nicht mehr
    lautlos überspringen (kd-tree.json blieb sonst leer, 0 Knoten)."""
    from iil_klickdummy import gen_sitemap

    kd_root = tmp_path / "klickdummy"
    d = kd_root / "hub"
    d.mkdir(parents=True)
    (d / "screens-spec.yaml").write_text(
        yaml.safe_dump(_root_spec("acme:klickdummy-spec-hub", "Hub"), sort_keys=False),
        encoding="utf-8",
    )
    (d / "shell.html").write_text("<html></html>", encoding="utf-8")

    tree = gen_sitemap.generate(tmp_path, adr_local="acme:ADR-001", repo_name="acme")

    assert tree["roots"] == ["acme:klickdummy-spec-hub"]


def test_rerun_without_content_change_is_byte_identical(tmp_path):
    """Determinismus-Regression: ein zweiter Lauf ohne Spec-Änderung darf
    screens-spec.yaml NICHT verändern (spec_date darf nicht auf 'heute'
    weiterdrehen) — sonst driftet die SHA256 in abhängigen generierten
    Dateien (klickdummy-gen-e2e) bei jedem CI-Rerun ohne echten Grund."""
    from iil_klickdummy import gen_sitemap

    kd_root = tmp_path / "klickdummy"
    _write_spec(kd_root, "hub", _root_spec("acme:klickdummy-spec-hub", "Hub"))

    gen_sitemap.generate(tmp_path, adr_local="acme:ADR-001", repo_name="acme")
    first = (kd_root / "sitemap" / "screens-spec.yaml").read_text()

    gen_sitemap.generate(tmp_path, adr_local="acme:ADR-001", repo_name="acme")
    second = (kd_root / "sitemap" / "screens-spec.yaml").read_text()

    assert first == second


def test_sitemap_does_not_include_itself_as_a_node(tmp_path):
    """Regression #170: der Skip-Guard in `_load_specs()` prüfte auf den nie
    geschriebenen Dateinamen "index.screens-spec.yaml" — die real erzeugte
    Datei heißt "screens-spec.yaml" unter `sitemap/`. Griff dadurch nie: der
    ERSTE Lauf zählt die Sitemap noch nicht mit (existiert ja noch nicht),
    der ZWEITE (Datei jetzt vorhanden) zählte sie faelschlich als
    zusätzlichen Knoten — ein einmaliger Idempotenz-Sprung, der den
    Sitemap-Freshness-Drift-Gate nach dem allerersten Commit faelschlich rot
    faerbt (Canary-Fund, ausschreibungs-hub 2026-07-13)."""
    from iil_klickdummy import gen_sitemap

    kd_root = tmp_path / "klickdummy"
    _write_spec(kd_root, "hub", _root_spec("acme:klickdummy-spec-hub", "Hub"))

    tree1 = gen_sitemap.generate(tmp_path, adr_local="acme:ADR-001", repo_name="acme")
    assert set(tree1["nodes"]) == {"acme:klickdummy-spec-hub"}

    # Zweiter Lauf: klickdummy/sitemap/screens-spec.yaml existiert jetzt bereits.
    tree2 = gen_sitemap.generate(tmp_path, adr_local="acme:ADR-001", repo_name="acme")
    assert set(tree2["nodes"]) == {"acme:klickdummy-spec-hub"}
    assert tree1 == tree2


def test_sitemap_stays_empty_across_reruns_with_no_real_specs(tmp_path):
    """Regression #170 (exakt der Canary-Fall in ausschreibungs-hub,
    2026-07-13): ohne echte Klickdummy-Specs muss die Sitemap über beliebig
    viele Reruns leer bleiben, statt sich selbst zu 'entdecken', sobald
    sitemap/ einmal existiert."""
    from iil_klickdummy import gen_sitemap

    tree1 = gen_sitemap.generate(tmp_path, adr_local="acme:ADR-001", repo_name="acme")
    assert tree1["nodes"] == {}

    tree2 = gen_sitemap.generate(tmp_path, adr_local="acme:ADR-001", repo_name="acme")
    assert tree2["nodes"] == {}


def test_rerun_preserves_original_spec_date_even_with_new_content(tmp_path):
    from iil_klickdummy import gen_sitemap

    kd_root = tmp_path / "klickdummy"
    _write_spec(kd_root, "hub", _root_spec("acme:klickdummy-spec-hub", "Hub"))
    gen_sitemap.generate(tmp_path, adr_local="acme:ADR-001", repo_name="acme")
    first_spec = yaml.safe_load((kd_root / "sitemap" / "screens-spec.yaml").read_text())

    # Neuer Knoten dazu — Baum ändert sich, aber spec_date der Sitemap selbst bleibt.
    _write_spec(kd_root, "hub2", _root_spec("acme:klickdummy-spec-hub2", "Hub2"))
    gen_sitemap.generate(tmp_path, adr_local="acme:ADR-001", repo_name="acme")
    second_spec = yaml.safe_load(
        (kd_root / "sitemap" / "screens-spec.yaml").read_text()
    )

    assert second_spec["spec_date"] == first_spec["spec_date"]


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

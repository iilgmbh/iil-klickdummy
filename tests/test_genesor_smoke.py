"""Smoke-Level-Start für 13 ungetestete genesor/-Module (Issue #109, R02 Carry-over).

Scope bewusst flach: Import + 1-2 Kernfunktions-Roundtrips pro Modul mit
deterministischen Minimal-Fixturen (tmp_path, kleine dicts/lists). Kein
Netzwerk, keine echten Scans von ~/github, keine Verhaltens-Vollabdeckung —
das ist Aufgabe der jeweiligen Feature-Tests (z. B. test_genesor_security.py,
test_read_model.py, test_smoke.py::test_v17_*).

export.py::build_uc_export_json hat bereits einen Test-Anker in
test_read_model.py — hier nur ein Import-Smoke-Test für Konsistenz mit den
übrigen 12 Modulen.
"""

from __future__ import annotations

import subprocess


# --- config.py ---------------------------------------------------------------


def test_should_import_config_module():
    from iil_klickdummy.genesor import config

    assert config is not None


def test_should_roundtrip_get_set_cfg_and_resolve_genesor_out(tmp_path):
    from iil_klickdummy.genesor.config import GenesorConfig, get_cfg, set_cfg

    default = get_cfg()
    try:
        set_cfg(GenesorConfig(repos_root=tmp_path))
        assert get_cfg().repos_root == tmp_path
        # genesor_out ist lazy: kein expliziter Wert → repos_root / "genesor"
        assert get_cfg().genesor_out == tmp_path / "genesor"
    finally:
        set_cfg(default)


def test_should_base_prefix_and_skin_url_reproduce_default_behavior():
    from iil_klickdummy.genesor.config import _base_prefix, _skin_url

    # Default BASE_URL "/" → Präfix leer, Skin-URL byte-identisch zu früher
    assert _base_prefix() == ""
    assert _skin_url("foo/bar.css") == "/foo/bar.css"


# --- export.py -----------------------------------------------------------
# build_uc_export_json ist bereits vollständig getestet in
# test_read_model.py::test_should_build_uc_export_json_output_match_uc_export_envelope_schema.
# Hier nur Import-Smoke für Konsistenz mit den übrigen Modulen.


def test_should_import_export_module():
    from iil_klickdummy.genesor import export

    assert callable(export.build_uc_export_json)


# --- introspect_django.py -----------------------------------------------


def test_should_inspect_django_models_parse_fields_via_ast(tmp_path):
    from iil_klickdummy.genesor.config import GenesorConfig, get_cfg, set_cfg
    from iil_klickdummy.genesor.introspect_django import _inspect_django_models

    default = get_cfg()
    apps_dir = tmp_path / "apps" / "foo"
    apps_dir.mkdir(parents=True)
    (apps_dir / "models.py").write_text(
        "from django.db import models\n"
        "class Foo(models.Model):\n"
        "    name = models.CharField(max_length=10)\n"
        "    tenant_id = models.BigIntegerField()\n",
        encoding="utf-8",
    )
    try:
        set_cfg(GenesorConfig(repos_root=tmp_path))
        result = _inspect_django_models("")
    finally:
        set_cfg(default)

    assert "foo.Foo" in result
    fields = result["foo.Foo"]["fields"]
    assert fields["name"]["type"] == "CharField"
    assert fields["tenant_id"]["type"] == "BigIntegerField"


def test_should_detect_tenant_pattern_active_with_3_plus_tenant_models():
    from iil_klickdummy.genesor.introspect_django import _detect_tenant_pattern

    models_inspected = {f"m{i}": {"fields": {"tenant_id": {}}} for i in range(3)}
    result = _detect_tenant_pattern(models_inspected)
    assert result["active"] is True
    assert result["count"] == 3


def test_should_detect_auth_user_model_fallback_to_django_default(tmp_path):
    from iil_klickdummy.genesor.config import GenesorConfig, get_cfg, set_cfg
    from iil_klickdummy.genesor.introspect_django import _detect_auth_user_model

    default = get_cfg()
    try:
        set_cfg(GenesorConfig(repos_root=tmp_path))
        # kein config/settings/*.py im Repo → Django-Default
        assert _detect_auth_user_model("nonexistent-repo") == "auth.User"
    finally:
        set_cfg(default)


# --- mermaid.py -----------------------------------------------------------


def test_should_node_id_sanitize_non_alnum_chars():
    from iil_klickdummy.genesor.mermaid import node_id

    assert node_id("foo-bar baz!") == "foo_bar_baz_"
    assert node_id("normal123") == "normal123"


def test_should_emit_screen_lineage_render_screens_and_next_edge():
    from iil_klickdummy.genesor.mermaid import emit_screen_lineage

    spec_data = {
        "screens": [
            {"id": "s1", "title": "S1", "next_screens": ["s2"]},
            {"id": "s2", "title": "S2"},
        ]
    }
    out = emit_screen_lineage(spec_data)
    assert out.startswith("flowchart TD")
    assert "s1" in out and "s2" in out
    assert "s1 --> s2" in out


# --- publish.py -------------------------------------------------------------


def test_should_repo_of_path_extract_repo_name_from_absolute_path(tmp_path):
    from iil_klickdummy.genesor.config import GenesorConfig, get_cfg, set_cfg
    from iil_klickdummy.genesor.publish import _repo_of_path

    default = get_cfg()
    try:
        set_cfg(GenesorConfig(repos_root=tmp_path))
        assert _repo_of_path(tmp_path / "myrepo" / "file.txt") == "myrepo"
        # außerhalb von repos_root → None
        assert _repo_of_path(tmp_path.parent / "elsewhere" / "f.txt") is None
    finally:
        set_cfg(default)


def test_should_git_publish_changes_dry_run_report_without_committing(tmp_path):
    """Minimaler lokaler Git-Repo-Fixture (git init + 1 Commit) — _git_publish_changes
    ist die zentrale Auto-Publish-Funktion, ein reiner Pfad-Test würde die
    tatsächliche git-Interaktion nicht abdecken. dry_run=True vermeidet echten
    commit/push."""
    from iil_klickdummy.genesor.config import GenesorConfig, get_cfg, set_cfg
    from iil_klickdummy.genesor.publish import _git_publish_changes

    repo_path = tmp_path / "myrepo"
    repo_path.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=repo_path, check=True)
    (repo_path / "f.txt").write_text("hi", encoding="utf-8")
    subprocess.run(
        ["git", "-c", "user.email=t@t.com", "-c", "user.name=t", "add", "f.txt"],
        cwd=repo_path,
        check=True,
    )
    subprocess.run(
        [
            "git",
            "-c",
            "user.email=t@t.com",
            "-c",
            "user.name=t",
            "commit",
            "-q",
            "-m",
            "init",
        ],
        cwd=repo_path,
        check=True,
    )

    default = get_cfg()
    try:
        set_cfg(GenesorConfig(repos_root=tmp_path))
        result = _git_publish_changes(
            "myrepo", [repo_path / "f.txt"], "test commit", dry_run=True
        )
    finally:
        set_cfg(default)

    assert result["committed"] is False
    assert result["pushed"] is False
    assert result["n_files"] == 1
    assert "dry-run" in result["skip_reason"]


# --- render_common.py --------------------------------------------------------


def test_should_skin_library_return_greenfield_first_plus_urls():
    from iil_klickdummy.genesor.render_common import skin_library

    lib = skin_library()
    assert lib[0] == ("__greenfield", "Greenfield (Default)")
    # weitere Einträge sind URL-präfixiert (default BASE_URL "/")
    assert all(value == "__greenfield" or value.startswith("/") for value, _ in lib)


def test_should_build_skin_switcher_html_mark_selected_option():
    from iil_klickdummy.genesor.render_common import build_skin_switcher_html

    out = build_skin_switcher_html("__greenfield")
    assert 'id="skin-select"' in out
    assert "selected" in out


# --- render_fallback.py -------------------------------------------------


def test_should_generate_render_fallback_write_clickable_html(tmp_path):
    """Direkter Aufruf des genesor-Moduls (statt der lineage-Fassade) —
    Duplikation zu tests/test_smoke.py ist hier bewusst in Kauf genommen
    (Smoke-Level-Start, Issue #109)."""
    from iil_klickdummy.genesor.render_fallback import generate_render_fallback

    spec = {
        "spec_id": "test-kd",
        "spec_version": "0.1",
        "spec_schema_version": "1.1",
        "title": "Test",
        "class": "mock",
        "off_ramp": {"unit": "per-screen", "rule": "test"},
        "screens": [{"id": "s1", "title": "S1", "route": "/s1/"}],
    }
    record = {
        "spec_id": "test-kd",
        "path": tmp_path / "spec.yaml",
        "data": spec,
        "repo": "test-repo",
        "kd": "test-kd",
    }
    out_path = generate_render_fallback(record, tmp_path)
    assert out_path.exists()
    content = out_path.read_text(encoding="utf-8")
    assert "test-kd" in content
    assert "Render-Mode" in content


# --- render_genesor.py --------------------------------------------------


def test_should_build_genesor_html_render_row_for_spec_kd(tmp_path):
    from iil_klickdummy.genesor.config import GenesorConfig, get_cfg, set_cfg
    from iil_klickdummy.genesor.render_genesor import build_genesor_html

    default = get_cfg()
    record = {
        "org": "achimdehnert",
        "repo": "test-repo",
        "kd": "test-kd",
        "path": tmp_path / "test-repo" / "klickdummy" / "test-kd" / "screens-spec.yaml",
        "data": {
            "class": "mock",
            "spec_role": "default",
            "screens": [],
            "personas": {},
            "adr": {"local": "test-repo:ADR-001"},
            "off_ramp": {},
        },
        "kind": "spec",
    }
    try:
        set_cfg(GenesorConfig(repos_root=tmp_path))
        html = build_genesor_html([record])
    finally:
        set_cfg(default)

    assert "test-kd" in html
    assert "<table" in html


def _genesor_record(tmp_path):
    return {
        "org": "achimdehnert",
        "repo": "test-repo",
        "kd": "test-kd",
        "path": tmp_path / "test-repo" / "klickdummy" / "test-kd" / "screens-spec.yaml",
        "data": {
            "class": "mock",
            "spec_role": "default",
            "screens": [],
            "personas": {},
            "adr": {"local": "test-repo:ADR-001"},
            "off_ramp": {},
        },
        "kind": "spec",
    }


def test_should_link_to_repo_sitemap_when_generated(tmp_path):
    """Cross-Link genesor -> klickdummy-gen-sitemap-Output (nur wenn im
    Ingest-Checkout tatsächlich vorhanden, sonst kein toter Link)."""
    from iil_klickdummy.genesor.config import GenesorConfig, get_cfg, set_cfg
    from iil_klickdummy.genesor.render_genesor import build_genesor_html

    sitemap_dir = tmp_path / "test-repo" / "klickdummy" / "sitemap"
    sitemap_dir.mkdir(parents=True)
    (sitemap_dir / "index.html").write_text("<html></html>", encoding="utf-8")

    default = get_cfg()
    try:
        set_cfg(GenesorConfig(repos_root=tmp_path))
        html = build_genesor_html([_genesor_record(tmp_path)])
    finally:
        set_cfg(default)

    assert "Repo-Sitemap" in html
    assert "/test-repo/klickdummy/sitemap/index.html" in html


def test_should_not_link_to_repo_sitemap_when_not_generated(tmp_path):
    """Kein Sitemap-Verzeichnis im Checkout -> kein toter Link im Output."""
    from iil_klickdummy.genesor.config import GenesorConfig, get_cfg, set_cfg
    from iil_klickdummy.genesor.render_genesor import build_genesor_html

    default = get_cfg()
    try:
        set_cfg(GenesorConfig(repos_root=tmp_path))
        html = build_genesor_html([_genesor_record(tmp_path)])
    finally:
        set_cfg(default)

    assert "Repo-Sitemap" not in html


def test_should_org_and_role_chip_escape_and_label():
    from iil_klickdummy.genesor.render_genesor import _org_chip, _role_chip

    assert "achimdehnert" in _org_chip("achimdehnert")
    assert "role-root" in _role_chip("root")
    assert "role-default" in _role_chip("unknown-role")


# --- render_lineage.py --------------------------------------------------


def test_should_build_html_embed_mermaid_and_kd_options():
    from pathlib import Path

    from iil_klickdummy.genesor.render_lineage import build_html

    specs = [
        (
            "kd1",
            Path("/fake/spec.yaml"),
            {"spec_role": "root", "consumes_from": [], "provides_contracts": []},
        )
    ]
    html = build_html("flowchart LR\nA-->B", specs, {})
    assert "flowchart LR" in html
    assert "kd1" in html


def test_should_build_screen_lineage_html_embed_screen_count():
    from iil_klickdummy.genesor.config import _DOMAIN_STYLES
    from iil_klickdummy.genesor.render_lineage import build_screen_lineage_html

    spec_data = {"screens": [{"id": "s1", "title": "S1"}], "class": "mock"}
    html = build_screen_lineage_html(
        "myrepo", "kd1", spec_data, "default", _DOMAIN_STYLES["default"]
    )
    assert "kd1" in html
    assert "flowchart TD" in html
    assert "1 Screens" in html


# --- render_uc.py -------------------------------------------------------
# build_impl_brief / build_impl_brief_html haben bereits Test-Anker in
# test_genesor_security.py (S-02 Escape-Härtung). Hier zusätzlich der
# UC-Index-Renderer, der dort nicht abgedeckt ist.


def test_should_build_repo_uc_index_html_render_uc_row():
    from iil_klickdummy.genesor.render_uc import build_repo_uc_index_html

    uc = {
        "repo": "test-repo",
        "uc_id": "UC-1",
        "name": "Testfall",
        "akteur": "Sachbearbeiter",
        "status": "draft",
    }
    coverage = {"uc_realized_count": {}, "uc_unresolved": {}}
    html = build_repo_uc_index_html("test-repo", [uc], coverage)
    assert "UC-1" in html
    assert "Testfall" in html


# --- scan.py --------------------------------------------------------------
# _warn_schema_violations / find_all_repos_specs / find_specs sind bereits
# ausführlich getestet in test_genesor_security.py. Hier die übrigen
# zentralen Discovery-Helfer.


def test_should_find_mockup_html_prefer_shell_over_other_html(tmp_path):
    from iil_klickdummy.genesor.scan import find_mockup_html

    kd_dir = tmp_path / "kd1"
    kd_dir.mkdir()
    (kd_dir / "shell.html").write_text("<html></html>", encoding="utf-8")
    (kd_dir / "other.html").write_text("<html></html>", encoding="utf-8")
    result = find_mockup_html(kd_dir, "kd1")
    assert result == kd_dir / "shell.html"


def test_should_url_for_path_prefix_with_base_url(tmp_path):
    from iil_klickdummy.genesor.config import GenesorConfig, get_cfg, set_cfg
    from iil_klickdummy.genesor.scan import url_for_path

    default = get_cfg()
    try:
        set_cfg(GenesorConfig(repos_root=tmp_path))
        assert url_for_path(tmp_path / "kd1" / "shell.html") == "/kd1/shell.html"
        # außerhalb repos_root → None
        assert url_for_path(tmp_path.parent / "elsewhere") is None
    finally:
        set_cfg(default)


def test_should_detect_org_fallback_heuristic_without_platform_checkout(tmp_path):
    from iil_klickdummy.genesor.config import GenesorConfig, get_cfg, set_cfg
    from iil_klickdummy.genesor.scan import detect_org

    default = get_cfg()
    try:
        # kein platform/-Checkout unter tmp_path → Code-Heuristik greift
        set_cfg(GenesorConfig(repos_root=tmp_path))
        assert detect_org("meiki-hub") == "meiki-lra"
        assert detect_org("ttz-hub") == "ttz-lif"
        assert detect_org("some-other-repo") == "achimdehnert"
    finally:
        set_cfg(default)


def test_should_adr_local_read_nested_field():
    from iil_klickdummy.genesor.scan import adr_local

    assert adr_local({"adr": {"local": "x:ADR-1"}}) == "x:ADR-1"
    assert adr_local({}) is None


# --- synth.py ---------------------------------------------------------------
# _synth_entity_table ist bereits via lineage._synth_entity_table getestet
# (test_smoke.py::test_v122_*). Hier zusätzlich die reinen Bausteine.


def test_should_entity_field_names_extract_up_to_6_names():
    from iil_klickdummy.genesor.synth import _entity_field_names

    assert _entity_field_names({"fields": ["a", "b", "c"]}) == ["a", "b", "c"]
    assert _entity_field_names({}) == []
    assert _entity_field_names("not-a-dict") == []


def test_should_synth_value_be_deterministic_for_known_field_names():
    from iil_klickdummy.genesor.synth import _synth_value

    # vorname/nachname sind row-konsistent aus dem festen _BUERGER_POOL —
    # row_idx=0 liefert immer denselben Wert (kein date.today()/random).
    assert _synth_value("vorname", 0) == "Sabine"
    assert _synth_value("nachname", 0) == "Müller"


# --- ucs.py -----------------------------------------------------------------


def test_should_build_uc_coverage_match_uc_to_realized_screen():
    from iil_klickdummy.genesor.ucs import build_uc_coverage

    kds = [
        {
            "repo": "r1",
            "kd": "kd1",
            "kind": "spec",
            "data": {"adr": {"local": "ADR-001"}, "screens": [{"id": "s1"}]},
        }
    ]
    ucs = [{"repo": "r1", "uc_id": "UC-1", "related_screens": ["r1:ADR-001#s1"]}]
    coverage = build_uc_coverage(ucs, kds)
    assert coverage["uc_realized_count"]["r1:UC-1"] == 1
    assert coverage["matrix"][("r1:UC-1", "r1", "kd1")] == ["s1"]
    assert coverage["uc_unresolved"] == {}


def test_should_parse_uc_frontmatter_extract_yaml_block():
    from iil_klickdummy.genesor.ucs import _parse_uc_frontmatter

    fm = _parse_uc_frontmatter("---\nuc_id: UC-1\nname: Test\n---\nbody")
    assert fm == {"uc_id": "UC-1", "name": "Test"}
    assert _parse_uc_frontmatter("kein frontmatter hier") is None


# --- validate.py --------------------------------------------------------


def test_should_compute_acceptance_status_classify_old_entry_as_stale():
    from iil_klickdummy.genesor.validate import compute_acceptance_status

    # 2020-01-01 ist garantiert >60 Tage alt, unabhängig vom Testlaufdatum.
    result = compute_acceptance_status(
        {"spec_signed": [{"by": "x", "date": "2020-01-01"}]}
    )
    assert result["spec_signed"]["status"] == "stale"
    assert result["ui_walked"]["status"] == "missing"


def test_should_merge_acceptance_combine_kd_and_screen_level():
    from iil_klickdummy.genesor.validate import merge_acceptance

    merged = merge_acceptance(
        {"spec_signed": [{"by": "a", "date": "2020-01-01"}]},
        {"ui_walked": [{"by": "b", "date": "2020-01-01"}]},
    )
    assert merged["spec_signed"][0]["by"] == "a"
    assert merged["ui_walked"][0]["by"] == "b"


def test_should_validate_kd_flag_missing_sunset_for_mock_class():
    from iil_klickdummy.genesor.validate import build_kd_registry, validate_kd

    registry = build_kd_registry(
        [{"kind": "spec", "data": {"adr": {"local": "r1:ADR-001"}}}]
    )
    warnings = validate_kd(
        {"kind": "spec", "data": {"class": "mock", "off_ramp": {}}}, registry
    )
    assert any(w["code"] == "SUNSET-MISSING" for w in warnings)


def test_should_compute_sunset_badge_classify_overdue_and_far_future():
    from iil_klickdummy.genesor.validate import compute_sunset_badge

    overdue_cls, overdue_text = compute_sunset_badge(
        {"off_ramp": {"sunset_after": "2020-01-01"}}
    )
    assert overdue_cls == "sunset-overdue"
    assert "überfällig" in overdue_text

    ok_cls, ok_text = compute_sunset_badge({"off_ramp": {"sunset_after": "2099-01-01"}})
    assert ok_cls == "sunset-ok"
    assert ok_text == "2099-01-01"

"""Tests für die Analyse-Reste (2026-06-12, Follow-up zu PR #57).

- check_i2: widersprüchliche Doppel-Deklaration class vs klickdummy_class
- inventory: Truncation-Hinweis, kein Früh-Abbruch, --strict = Exit-Gate
- discovery_push: per-Screen-Aggregation von off_ramp_status
- widget.js: Fallback-Rückfrage, Textarea-Feedback, aria-expanded, Token-Länge
- registry: Cross-Repo-Stories mit kd_index-Remap
- lineage.py: kompiliert ohne SyntaxWarning (\\s-Escapes)
"""

from __future__ import annotations

import json
import pathlib
import warnings
from importlib.resources import files

from iil_klickdummy import check_i2, discovery_push, inventory, registry


# ----------------------------------------------------------------- check_i2


def _i2_pair(tmp_path, body: dict) -> str:
    spec = tmp_path / "spec.json"
    spec.write_text(json.dumps(body), encoding="utf-8")
    return f"{spec}:unused.json"


def test_i2_should_fail_on_conflicting_class_keys(tmp_path):
    pair = _i2_pair(tmp_path, {"class": "mock", "klickdummy_class": "spec-demo"})
    assert check_i2.main([pair]) == 1


def test_i2_should_pass_on_redundant_but_identical_class_keys(tmp_path):
    pair = _i2_pair(tmp_path, {"class": "mock", "klickdummy_class": "mock"})
    assert check_i2.main([pair]) == 0


# ---------------------------------------------------------------- inventory


def _legacy_repo(base: pathlib.Path, name: str, n_hits: int) -> None:
    d = base / name / "docs"
    d.mkdir(parents=True)
    lines = "\n".join(
        f"- Zeile {i}: alter mock-prototyp Begriff" for i in range(n_hits)
    )
    (d / "alt.md").write_text(lines, encoding="utf-8")


def test_inventory_should_scan_all_repos_and_note_truncation(tmp_path, capsys):
    _legacy_repo(tmp_path, "repo-a", 12)
    _legacy_repo(tmp_path, "repo-b", 1)
    rc = inventory.main(
        ["--base", str(tmp_path), "--repos", "repo-a,repo-b", "--strict"]
    )
    out = capsys.readouterr().out
    assert rc == 1
    # kein Früh-Abbruch nach repo-a: repo-b erscheint trotzdem im Report
    assert "repo-b: 1 echte Drift-Treffer" in out
    assert "und 2 weitere" in out  # 12 Treffer, 10 angezeigt
    assert "13 Treffer" in out


def test_inventory_without_strict_should_report_but_exit_zero(tmp_path):
    _legacy_repo(tmp_path, "repo-a", 2)
    assert inventory.main(["--base", str(tmp_path), "--repos", "repo-a"]) == 0


# ----------------------------------------------------------- discovery_push


def test_off_ramp_status_explicit_overall_wins():
    spec = {
        "off_ramp": {"status_overall": "parity-green"},
        "screens": [{"off_ramp_status": "static"}],
    }
    assert discovery_push._off_ramp_status(spec) == "parity-green"


def test_off_ramp_status_uniform_screens_aggregate():
    spec = {
        "off_ramp": {},
        "screens": [{"off_ramp_status": "removed"}, {"off_ramp_status": "removed"}],
    }
    assert discovery_push._off_ramp_status(spec) == "removed"


def test_off_ramp_status_mixed_screens_yield_transition():
    spec = {
        "off_ramp": {},
        "screens": [{"off_ramp_status": "static"}, {"off_ramp_status": "removed"}],
    }
    assert discovery_push._off_ramp_status(spec) == "transition"


def test_off_ramp_status_defaults_to_static_without_screens():
    assert discovery_push._off_ramp_status({}) == "static"


# ---------------------------------------------------------------- widget.js


def test_widget_should_have_reste_fixes():
    js = (
        files("iil_klickdummy") / "snippets" / "feedback-widget" / "widget.js"
    ).read_text()
    assert 'aria-expanded="false"' in js and "setAttribute('aria-expanded'" in js
    assert 'role="dialog"' in js
    assert "fb-invalid" in js and "aria-invalid" in js
    assert "window.confirm" in js, (
        "GitHub-Fallback muss nachfragen, nicht auto-downloaden"
    )
    assert "[A-Za-z0-9_]{16,}$" in js, "Token-Validierung braucht Mindestlänge"


# ------------------------------------------------- registry cross-repo story


def test_cross_repo_stories_should_remap_kd_index(tmp_path):
    import textwrap

    for repo, kd in (("repo-x", "alpha"), ("repo-y", "beta")):
        d = tmp_path / repo / "klickdummy" / kd
        d.mkdir(parents=True)
        (d / "screens-spec.yaml").write_text(
            f'spec_id: {repo}:{kd}\nspec_version: "0.1"\nclass: mock\ntitle: {kd}\n',
            encoding="utf-8",
        )
        (d / "shell.html").write_text("<html></html>", encoding="utf-8")
    stories_dir = tmp_path / "repo-y" / "klickdummy" / "stories"
    stories_dir.mkdir()
    (stories_dir / "s1.yaml").write_text(
        textwrap.dedent("""
        id: s1
        title: Beta-Story
        steps:
          - kd: beta
            label: Schritt 1
    """),
        encoding="utf-8",
    )
    triples = registry.discover_cross_repo(tmp_path, ["repo-x", "repo-y"])
    assert [r for _, r, _ in triples] == ["repo-x", "repo-y"]
    stories = registry.discover_cross_repo_stories(tmp_path, triples)
    assert len(stories) == 1
    # beta ist global Index 1 (nach repo-x/alpha), nicht repo-lokal 0
    assert stories[0]["steps"][0]["kd_index"] == 1


# ------------------------------------------------------------------ lineage


def test_lineage_should_compile_without_syntax_warnings():
    src = (files("iil_klickdummy") / "lineage.py").read_text()
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        compile(src, "lineage.py", "exec")
    syn = [w for w in caught if issubclass(w.category, SyntaxWarning)]
    assert not syn, f"SyntaxWarnings: {[str(w.message) for w in syn]}"

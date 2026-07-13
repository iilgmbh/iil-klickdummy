"""Tests für den Auto-Brownfield-Existenz-Detektor (Issue #161).

`tests/detection_corpus/*.yaml` wächst monoton mit jedem real übersehenen
Brownfield-Fall (False Negative) — Misses werden zu Testfällen, nie nur zu
Hotfixes. Der Corpus-Recall-Test misst 100% auf allen bekannten Fällen.
"""

from __future__ import annotations

import json
import pathlib
import subprocess
import sys

import pytest
import yaml

from iil_klickdummy import detect as detect_mod

CORPUS_DIR = pathlib.Path(__file__).parent / "detection_corpus"


def _materialize(tmp_path: pathlib.Path, files: dict[str, str]) -> pathlib.Path:
    for rel, content in files.items():
        p = tmp_path / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
    return tmp_path


def _load_corpus_cases() -> list[tuple[str, dict]]:
    return [
        (p.stem, yaml.safe_load(p.read_text(encoding="utf-8")))
        for p in sorted(CORPUS_DIR.glob("*.yaml"))
    ]


# ------------------------------------------------------- _slug_variants


def test_should_include_dash_underscore_and_collapsed_variants():
    variants = detect_mod._slug_variants("gefahrstoff-kataster")
    assert "gefahrstoff-kataster" in variants
    assert "gefahrstoff_kataster" in variants
    assert "gefahrstoffkataster" in variants


# ------------------------------------------------------- l1_grep


def test_should_find_l1_hit_via_dash_underscore_variant(tmp_path):
    _materialize(tmp_path, {"src/tom_pflege/views.py": "def index(): pass\n"})
    ev = detect_mod.l1_grep(tmp_path, "tom-pflege")
    assert ev is not None
    assert ev.layer == "L1"


def test_should_return_none_when_no_src_dir(tmp_path):
    assert detect_mod.l1_grep(tmp_path, "anything") is None


def test_should_return_none_when_slug_absent(tmp_path):
    _materialize(tmp_path, {"src/foo/views.py": "def index(): pass\n"})
    assert detect_mod.l1_grep(tmp_path, "quantenkuehlschrank") is None


# ------------------------------------------------------- l2_django


def test_should_find_l2_hit_via_app_name(tmp_path):
    _materialize(
        tmp_path,
        {
            "src/dsb/models.py": "from django.db import models\n",
            "src/dsb/urls.py": (
                'from django.urls import path\napp_name = "dsb"\n'
                "urlpatterns = [path('', None, name='index')]\n"
            ),
        },
    )
    ev = detect_mod.l2_django(tmp_path, "dsb")
    assert ev is not None
    assert ev.layer == "L2"


def test_should_return_none_when_no_app_matches(tmp_path):
    _materialize(tmp_path, {"src/foo/models.py": "from django.db import models\n"})
    assert detect_mod.l2_django(tmp_path, "quantenkuehlschrank") is None


# ------------------------------------------------------- detect() orchestration


def test_should_combine_l1_and_l2_hits(tmp_path):
    _materialize(
        tmp_path,
        {
            "src/dsb/models.py": "from django.db import models\n",
            "src/dsb/urls.py": (
                'from django.urls import path\napp_name = "dsb"\n'
                "urlpatterns = [path('', None, name='index')]\n"
            ),
        },
    )
    hits = detect_mod.detect(tmp_path, "dsb")
    layers = {h.layer for h in hits}
    assert "L1" in layers
    assert "L2" in layers


def test_should_return_empty_list_for_true_greenfield(tmp_path):
    _materialize(tmp_path, {"src/foo/models.py": "from django.db import models\n"})
    assert detect_mod.detect(tmp_path, "quantenkuehlschrank-verwaltung") == []


# ------------------------------------------------------- Corpus-Recall (monoton wachsend)


@pytest.mark.parametrize(
    "name,case", _load_corpus_cases(), ids=[c[0] for c in _load_corpus_cases()]
)
def test_should_match_detection_corpus_expectation(tmp_path, name, case):
    _materialize(tmp_path, case["files"])
    hits = detect_mod.detect(tmp_path, case["slug"])
    assert bool(hits) == case["expect_hit"], (
        f"{name}: erwartet expect_hit={case['expect_hit']}, "
        f"tatsächlich {len(hits)} Treffer: {hits}"
    )


def test_corpus_has_at_least_one_positive_and_one_negative_case():
    cases = _load_corpus_cases()
    assert any(c["expect_hit"] for _, c in cases)
    assert any(not c["expect_hit"] for _, c in cases)


# ------------------------------------------------------- CLI (main())


def test_should_exit_nonzero_on_hit(tmp_path, capsys):
    _materialize(tmp_path, {"src/dsb/models.py": "from django.db import models\n"})
    rc = detect_mod.main(["--repo", str(tmp_path), "--slug", "dsb"])
    assert rc == 1
    assert "Gefunden" in capsys.readouterr().err


def test_should_exit_zero_on_no_hit(tmp_path, capsys):
    _materialize(tmp_path, {"src/foo/models.py": "from django.db import models\n"})
    rc = detect_mod.main(["--repo", str(tmp_path), "--slug", "quantenkuehlschrank"])
    assert rc == 0
    assert "bestätigt" in capsys.readouterr().out


def test_should_override_with_force_greenfield_and_emit_json(tmp_path, capsys):
    _materialize(tmp_path, {"src/dsb/models.py": "from django.db import models\n"})
    rc = detect_mod.main(
        [
            "--repo",
            str(tmp_path),
            "--slug",
            "dsb",
            "--force-greenfield",
            "Bewusst neu, ADR-123",
        ]
    )
    assert rc == 0
    captured = capsys.readouterr()
    assert "Bewusst neu, ADR-123" in captured.err
    payload = json.loads(captured.out.strip().splitlines()[-1])
    assert payload["force_greenfield_reason"] == "Bewusst neu, ADR-123"
    assert payload["slug"] == "dsb"
    assert len(payload["evidence"]) >= 1


def test_should_run_as_installed_cli_entrypoint(tmp_path):
    """Integration: `klickdummy-detect` läuft nach editable-install (pyproject
    [project.scripts]) als eigenständiges CLI, nicht nur importierbar."""
    _materialize(tmp_path, {"src/foo/models.py": "from django.db import models\n"})
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "iil_klickdummy.detect",
            "--repo",
            str(tmp_path),
            "--slug",
            "quantenkuehlschrank",
        ],
        capture_output=True,
        text=True,
        timeout=15,
    )
    assert result.returncode == 0

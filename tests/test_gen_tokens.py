"""Tests für `klickdummy-tokens` (dev-hub#320) — design-hub-Profil → tokens.css.

Fixture: tests/fixtures/tokens-profile-fixture.yaml (klein, synthetisch — keine
echten design-hub-Daten, keine Kontaktdaten).
"""

from __future__ import annotations

import copy
from pathlib import Path

import pytest
import yaml

from iil_klickdummy.gen_tokens import TokenGenError, generate, main

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "tokens-profile-fixture.yaml"


def _load_fixture() -> dict:
    return yaml.safe_load(FIXTURE_PATH.read_text(encoding="utf-8"))


# --------------------------------------------------------- generate()


def test_should_produce_byte_identical_output_across_two_runs():
    profile = _load_fixture()
    first = generate(profile, generator_version="1.36.0")
    second = generate(copy.deepcopy(profile), generator_version="1.36.0")
    assert first == second
    assert first.endswith("\n") and not first.endswith("\n\n")


def test_should_emit_dark_block_when_colours_dark_present():
    profile = _load_fixture()
    css = generate(profile, generator_version="1.36.0")
    assert '[data-theme="dark"] {' in css
    assert "--kd-text: #E8EAED;" in css


def test_should_omit_dark_block_when_colours_dark_absent():
    profile = _load_fixture()
    del profile["colours_dark"]
    css = generate(profile, generator_version="1.36.0")
    assert '[data-theme="dark"]' not in css


def test_should_render_font_primary_line_exactly_as_specified():
    profile = _load_fixture()
    css = generate(profile, generator_version="1.36.0")
    assert '--kd-font-primary: "Inter", "Noto Sans", "Arial", sans-serif;' in css
    assert '--kd-font-mono: "JetBrains Mono", monospace;' in css


def test_should_emit_optional_status_colours_when_present_in_profile():
    """dev-hub#320 Welle 3: colours.success/warning/danger/info sind KEIN
    Pflichtschlüssel und haben keine feste Sonderbehandlung im Generator
    (_colour_lines rendert generisch jeden Key) — legt ein Profil sie an,
    tauchen sie 1:1 als --kd-success etc. auf; kd-nav.js selbst braucht sie
    aktuell nicht (nur Kern-Tokens, s. Snippet-Kommentar)."""
    profile = _load_fixture()
    profile["colours"]["success"] = "#22C55E"
    profile["colours"]["danger"] = "#DC2626"
    css = generate(profile, generator_version="1.38.0")
    assert "--kd-success: #22C55E;" in css
    assert "--kd-danger: #DC2626;" in css


def test_should_omit_optional_status_colours_when_absent_from_profile():
    profile = _load_fixture()
    css = generate(profile, generator_version="1.38.0")
    assert "--kd-success" not in css
    assert "--kd-warning" not in css
    assert "--kd-danger" not in css
    assert "--kd-info" not in css


def test_should_raise_on_missing_required_key():
    profile = _load_fixture()
    del profile["colours"]["text"]
    with pytest.raises(TokenGenError, match="colours.text"):
        generate(profile, generator_version="1.36.0")


def test_should_raise_on_invalid_colour_value():
    profile = _load_fixture()
    profile["colours"]["primary"] = "blue"
    with pytest.raises(TokenGenError, match="colours.primary"):
        generate(profile, generator_version="1.36.0")


# --------------------------------------------------------- CLI (main)


def test_should_exit_0_and_write_file_on_first_run(tmp_path):
    out = tmp_path / "tokens.css"
    rc = main(["--profile", str(FIXTURE_PATH), "--out", str(out)])
    assert rc == 0
    assert out.exists()
    assert "--kd-primary: #1A4A7A;" in out.read_text(encoding="utf-8")


def test_should_check_exit_0_when_file_matches(tmp_path):
    out = tmp_path / "tokens.css"
    main(["--profile", str(FIXTURE_PATH), "--out", str(out)])
    rc = main(["--profile", str(FIXTURE_PATH), "--out", str(out), "--check"])
    assert rc == 0


def test_should_check_exit_1_when_file_missing(tmp_path):
    out = tmp_path / "tokens.css"
    rc = main(["--profile", str(FIXTURE_PATH), "--out", str(out), "--check"])
    assert rc == 1


def test_should_check_exit_1_when_file_differs(tmp_path):
    out = tmp_path / "tokens.css"
    out.write_text("/* stale */\n", encoding="utf-8")
    rc = main(["--profile", str(FIXTURE_PATH), "--out", str(out), "--check"])
    assert rc == 1


def test_should_exit_2_on_missing_required_key(tmp_path):
    bad_profile = tmp_path / "bad.yaml"
    profile = _load_fixture()
    del profile["fonts"]["primary"]
    bad_profile.write_text(yaml.safe_dump(profile), encoding="utf-8")
    out = tmp_path / "tokens.css"
    rc = main(["--profile", str(bad_profile), "--out", str(out)])
    assert rc == 2
    assert not out.exists()


def test_should_exit_2_on_invalid_colour_value(tmp_path):
    bad_profile = tmp_path / "bad.yaml"
    profile = _load_fixture()
    profile["colours"]["border"] = "not-a-colour"
    bad_profile.write_text(yaml.safe_dump(profile), encoding="utf-8")
    out = tmp_path / "tokens.css"
    rc = main(["--profile", str(bad_profile), "--out", str(out)])
    assert rc == 2

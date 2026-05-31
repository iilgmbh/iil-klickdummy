"""v1.6 Keystone — Spec → ausführbare E2E-Parity-Suite (platform:ADR-211 §Off-Ramp).

Beweist die These: *eine* Assertion-Menge validiert Renderer #1 (Klickdummy)
und Renderer #2 (echte App), und sie überlebt den I3-Off-Ramp.
"""
from __future__ import annotations

import pathlib

from importlib.resources import files

FIXTURE = pathlib.Path(__file__).parent / "fixtures" / "example-screens-spec.yaml"


def test_gen_e2e_module_present():
    from iil_klickdummy import gen_e2e
    assert callable(getattr(gen_e2e, "main_cli", None))
    assert callable(getattr(gen_e2e, "render_assertion", None))


def test_render_assertion_vocabulary():
    from iil_klickdummy import gen_e2e as g
    # Double-Quotes (ruff-format-konform), nicht repr/Single-Quotes
    assert g.render_assertion({"action": "text", "selector": "h1", "expect": "Anmelden"}) \
        == 'expect(page.locator("h1")).to_contain_text("Anmelden")'
    assert g.render_assertion({"action": "clickable", "selector": "button"}) \
        == 'expect(page.locator("button")).to_be_enabled()'
    assert g.render_assertion({"action": "visible", "selector": "#x"}) \
        == 'expect(page.locator("#x")).to_be_visible()'
    assert g.render_assertion({"action": "url", "expect": "/dashboard"}) \
        == 'assert "/dashboard" in page.url, page.url'
    assert g.render_assertion({"action": "count", "selector": "li", "expect": 3}) \
        == 'expect(page.locator("li")).to_have_count(3)'
    # nur-Prosa / unbekannt ⇒ None (nicht ausführbar)
    assert g.render_assertion(None) is None
    assert g.render_assertion({"action": "frobnicate"}) is None


def test_screen_route_convention():
    from iil_klickdummy import gen_e2e as g
    assert g.screen_route({"id": "login", "route": "/auth/login"}) == "/auth/login"
    assert g.screen_route({"id": "login"}) == "/login"          # Default-Konvention
    assert g.screen_route({"id": "x", "route": "bare"}) == "/bare"  # führender Slash erzwungen


def test_gen_e2e_generates_runnable_suite(tmp_path):
    from iil_klickdummy import gen_e2e
    out = tmp_path / "test_parity_login.py"
    rc = gen_e2e.main([str(FIXTURE), str(out)])
    assert rc == 0
    text = out.read_text(encoding="utf-8")

    # Dual-Renderer: BASE per renderer-neutralem Env umschaltbar (Renderer #1 ↔ #2)
    assert "SPEC_RENDERER_BASE_URL" in text
    assert "KLICKDUMMY_BASE_URL" not in text   # umbenannt (REC-10) — kein Sunset-Klebstoff
    assert "from playwright.sync_api import Page, expect" in text

    # ausführbare Checks → echte Assertions, an die Screen-route gebunden
    assert "def test_login__login_has_heading(page: Page):" in text
    assert 'page.goto(BASE + "/auth/login")' in text
    assert 'expect(page.locator("h1")).to_contain_text("Anmelden")' in text
    assert 'expect(page.locator("button[type=submit]")).to_be_enabled()' in text

    # nur-Prosa → sichtbarer skip, kein stilles Weglassen
    assert "@pytest.mark.skip" in text
    assert "def test_login__login_shows_error(page: Page):" in text


def test_gen_e2e_emits_manifest(tmp_path):
    """Manifest = reproduzierbarer Beleg + Coverage/Skip-Transparenz (REC-12/REC-4/REC-14)."""
    import json
    from iil_klickdummy import gen_e2e
    out = tmp_path / "test_parity_login.py"
    gen_e2e.main([str(FIXTURE), str(out)])
    manifest = json.loads((tmp_path / "test_parity_login.manifest.json").read_text())
    assert manifest["spec_id"] == "example:klickdummy-spec-login"
    assert len(manifest["spec_sha256"]) == 64          # Reproduzierbarkeit (M28-2)
    assert manifest["base_url_env"] == "SPEC_RENDERER_BASE_URL"
    assert manifest["parity_checks"] == 3
    assert manifest["executable"] == 2
    assert manifest["skipped"] == 1
    # Skip-Debt sichtbar mit Detail (kein verstecktes Schein-Grün)
    assert manifest["skipped_detail"][0]["id"] == "login.shows-error"
    # Scope-Transparenz: NFR/Security/A11y nicht von assert abgedeckt
    assert "NFR" in manifest["uncovered_note"]


def test_gen_e2e_flags_fragile_selectors(tmp_path):
    """Selektoren ohne data-* Anker werden als fragil markiert (REC-6/AD-7)."""
    import json
    from iil_klickdummy import gen_e2e
    out = tmp_path / "s.py"
    gen_e2e.main([str(FIXTURE), str(out)])
    manifest = json.loads((tmp_path / "s.manifest.json").read_text())
    # Fixture nutzt 'h1' und 'button[type=submit]' — beide ohne data-* → fragil
    fragile_ids = {f["id"] for f in manifest["fragile_selectors"]}
    assert "login.has-heading" in fragile_ids
    # Gegenprobe: ein data-testid-Selektor gilt nicht als fragil
    assert gen_e2e.is_fragile_selector("[data-testid=submit]") is False
    assert gen_e2e.is_fragile_selector("button.submit") is True


def test_generated_suite_is_valid_python(tmp_path):
    """Erzeugte Datei muss kompilieren (Syntax-Garantie der Generierung)."""
    from iil_klickdummy import gen_e2e
    out = tmp_path / "gen.py"
    gen_e2e.main([str(FIXTURE), str(out)])
    compile(out.read_text(encoding="utf-8"), str(out), "exec")


def test_generated_suite_is_ruff_format_clean(tmp_path):
    """Generierter Output muss `ruff format --check` bestehen — sonst bricht jeder
    Adopter mit Format-CI (real aufgetreten: risk-hub PR #146)."""
    import shutil
    import subprocess
    ruff = shutil.which("ruff")
    if not ruff:
        import pytest
        pytest.skip("ruff nicht verfügbar")
    from iil_klickdummy import gen_e2e
    out = tmp_path / "test_parity.py"
    gen_e2e.main([str(FIXTURE), str(out)])
    r = subprocess.run([ruff, "format", "--check", str(out)],
                       capture_output=True, text=True)
    assert r.returncode == 0, f"ruff format würde reformatieren:\n{r.stdout}\n{r.stderr}"


def test_generated_suite_is_deterministic(tmp_path):
    """Zwei Läufe ⇒ byte-identisches .py (kein Zeitstempel im File) — sonst
    rauscht der Drift-Check `klickdummy-parity-drift` (REC-1/REC-13/AD-14)."""
    from iil_klickdummy import gen_e2e
    # gleicher Output-Pfad (Basename) in zwei Läufen — wie der reale Drift-Check,
    # der immer auf dieselbe Zieldatei re-generiert.
    a = tmp_path / "run1" / "test_parity.py"
    b = tmp_path / "run2" / "test_parity.py"
    gen_e2e.main([str(FIXTURE), str(a)])
    gen_e2e.main([str(FIXTURE), str(b)])
    assert a.read_bytes() == b.read_bytes()
    # Spec-SHA steht deterministisch im File-Header (Anker für den Drift-Check)
    assert "Spec-SHA256:" in a.read_text(encoding="utf-8")
    assert "Erzeugt:" not in a.read_text(encoding="utf-8")  # kein Datum im File


def test_schema_allows_assert_and_route():
    import json
    schema = json.loads(
        files("iil_klickdummy.schemas").joinpath("screens-spec.schema.json").read_text()
    )
    screen_props = schema["properties"]["screens"]["items"]["properties"]
    assert "route" in screen_props
    pa_props = screen_props["parity_acceptance"]["items"]["properties"]
    assert "assert" in pa_props
    assert pa_props["assert"]["properties"]["action"]["enum"] == \
        ["visible", "text", "clickable", "url", "count"]
    # `check` bleibt Pflicht — Rückwärtskompatibilität
    assert screen_props["parity_acceptance"]["items"]["required"] == ["id", "check"]

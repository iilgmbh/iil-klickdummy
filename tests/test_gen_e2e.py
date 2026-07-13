"""v1.6 Keystone — Spec → ausführbare E2E-Parity-Suite (platform:ADR-211 §Off-Ramp).

Beweist die These: *eine* Assertion-Menge validiert Renderer #1 (Klickdummy)
und Renderer #2 (echte App), und sie überlebt den I3-Off-Ramp.
"""

from __future__ import annotations

import pathlib

from importlib.resources import files

FIXTURE = pathlib.Path(__file__).parent / "fixtures" / "example-screens-spec.yaml"


def _conform(spec: dict) -> dict:
    """Ergänzt die schema-pflichtigen Rahmenfelder, die diese bewusst minimalen
    Inline-Specs auslassen, damit `load_spec`s jsonschema-Validierung (B-1-Fix)
    greift, ohne zu verschleiern, was der jeweilige Test prüft. Überschreibt nur
    strukturelle Felder (grounding/off_ramp/personas) + füllt fehlende
    Screen-Pflichtfelder — kein Test asserted deren Inhalt."""
    spec = dict(spec)
    spec["grounding"] = {"konzept": "-", "pilot": "-"}
    spec["off_ramp"] = {
        "policy": "-",
        "unit": "per-screen",
        "rule": "-",
        "doppelquell_grenze": "prod-release",
        "parity_runner": "-",
    }
    spec["personas"] = {"user": {"label": "User", "rolle": "user", "sieht": []}}
    screens = []
    for sc in spec.get("screens", []):
        sc = dict(sc)
        sc.setdefault("personas", ["user"])
        sc.setdefault("purpose", "-")
        sc.setdefault("off_ramp_status", "static")
        pas = []
        for pa in sc.get("parity_acceptance", []):
            pa = dict(pa)
            # Schema verlangt `check` minLength 8 — kurze Inline-Checks padden.
            pa["check"] = f"{pa.get('check', '')}".ljust(8, ".")
            pas.append(pa)
        if pas:
            sc["parity_acceptance"] = pas
        screens.append(sc)
    spec["screens"] = screens
    return spec


def test_gen_e2e_module_present():
    from iil_klickdummy import gen_e2e

    assert callable(getattr(gen_e2e, "main_cli", None))
    assert callable(getattr(gen_e2e, "render_assertion", None))


def test_render_assertion_vocabulary():
    from iil_klickdummy import gen_e2e as g

    # Double-Quotes (ruff-format-konform), nicht repr/Single-Quotes.
    # Einzelelement-State-Asserts nutzen `.first` (Strict-Mode-robust gegen
    # legitim mehrfach matchende Kontrakt-Selektoren, z.B. data-testid pro Zeile).
    assert (
        g.render_assertion({"action": "text", "selector": "h1", "expect": "Anmelden"})
        == 'expect(page.locator("h1").first).to_contain_text("Anmelden")'
    )
    assert (
        g.render_assertion({"action": "clickable", "selector": "button"})
        == 'expect(page.locator("button").first).to_be_enabled()'
    )
    assert (
        g.render_assertion({"action": "visible", "selector": "#x"})
        == 'expect(page.locator("#x").first).to_be_visible()'
    )
    assert (
        g.render_assertion({"action": "url", "expect": "/dashboard"})
        == 'assert "/dashboard" in page.url, page.url'
    )
    # `count` prüft Kardinalität explizit — KEIN `.first`
    assert (
        g.render_assertion({"action": "count", "selector": "li", "expect": 3})
        == 'expect(page.locator("li")).to_have_count(3)'
    )
    # nur-Prosa / unbekannt ⇒ None (nicht ausführbar)
    assert g.render_assertion(None) is None
    assert g.render_assertion({"action": "frobnicate"}) is None


def test_screen_route_convention():
    from iil_klickdummy import gen_e2e as g

    assert g.screen_route({"id": "login", "route": "/auth/login"}) == (
        "/auth/login",
        False,
    )
    assert g.screen_route({"id": "login"}) == ("/login", False)
    assert g.screen_route({"id": "x", "route": "bare"}) == ("/bare", False)
    # route_example bevorzugt
    assert g.screen_route(
        {"id": "x", "route": "/items/<uuid:pk>/", "route_example": "/items/abc-123/"}
    ) == ("/items/abc-123/", False)
    # parametrisierte Route ohne route_example → is_parametrised=True
    assert g.screen_route({"id": "x", "route": "/items/<uuid:pk>/"}) == (
        "/items/<uuid:pk>/",
        True,
    )
    assert g.screen_route({"id": "x", "route": "/items/<int:pk>/detail/"}) == (
        "/items/<int:pk>/detail/",
        True,
    )


def test_gen_e2e_generates_runnable_suite(tmp_path):
    from iil_klickdummy import gen_e2e

    out = tmp_path / "test_parity_login.py"
    rc = gen_e2e.main([str(FIXTURE), str(out)])
    assert rc == 0
    text = out.read_text(encoding="utf-8")

    # Dual-Renderer: BASE per renderer-neutralem Env umschaltbar (Renderer #1 ↔ #2)
    assert "SPEC_RENDERER_BASE_URL" in text
    assert (
        "KLICKDUMMY_BASE_URL" not in text
    )  # umbenannt (REC-10) — kein Sunset-Klebstoff
    assert "from playwright.sync_api import Page, expect" in text

    # ausführbare Checks → echte Assertions, an die Screen-route gebunden
    assert "def test_login__login_has_heading(page: Page):" in text
    assert 'page.goto(BASE + "/auth/login")' in text
    assert 'expect(page.locator("h1").first).to_contain_text("Anmelden")' in text
    assert 'expect(page.locator("button[type=submit]").first).to_be_enabled()' in text

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
    assert len(manifest["spec_sha256"]) == 64  # Reproduzierbarkeit (M28-2)
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


def test_generated_suite_skips_without_playwright(tmp_path):
    """Suite muss `pytest.importorskip` VOR dem harten playwright-Import emittieren —
    Adopter ohne playwright überspringen, statt beim Sammeln zu brechen (T-01;
    risk-hub #146 entging dem nur per testpaths-Zufall)."""
    from iil_klickdummy import gen_e2e

    out = tmp_path / "test_parity_login.py"
    gen_e2e.main([str(FIXTURE), str(out)])
    text = out.read_text(encoding="utf-8")
    assert 'pytest.importorskip("playwright")' in text
    assert text.index('pytest.importorskip("playwright")') < text.index(
        "from playwright.sync_api import"
    )


def test_generated_suite_passes_ruff_check_e402(tmp_path):
    """Der späte playwright-Import (nach importorskip) braucht `# noqa: E402`,
    sonst bricht jeder Adopter mit `ruff check` (Linter, nicht nur Formatter)."""
    import shutil
    import subprocess

    ruff = shutil.which("ruff")
    if not ruff:
        import pytest

        pytest.skip("ruff nicht verfügbar")
    from iil_klickdummy import gen_e2e

    out = tmp_path / "test_parity.py"
    gen_e2e.main([str(FIXTURE), str(out)])
    r = subprocess.run(
        [ruff, "check", "--select", "E402", str(out)], capture_output=True, text=True
    )
    assert r.returncode == 0, f"E402 im generierten Output:\n{r.stdout}\n{r.stderr}"


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
    r = subprocess.run(
        [ruff, "format", "--check", str(out)], capture_output=True, text=True
    )
    assert r.returncode == 0, (
        f"ruff format würde reformatieren:\n{r.stdout}\n{r.stderr}"
    )


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
    assert "route_example" in screen_props  # Issue #28
    assert "login_required" in screen_props  # Issue #28
    assert "auth" in schema["properties"]  # Issue #28: Top-Level-Auth-Block
    pa_props = screen_props["parity_acceptance"]["items"]["properties"]
    assert "assert" in pa_props
    assert pa_props["assert"]["properties"]["action"]["enum"] == [
        "visible",
        "text",
        "clickable",
        "url",
        "count",
    ]
    # `check` bleibt Pflicht — Rückwärtskompatibilität
    assert screen_props["parity_acceptance"]["items"]["required"] == ["id", "check"]


def test_gen_e2e_route_example_used(tmp_path):
    """route_example ersetzt parametrisierte route in page.goto (Issue #28)."""
    import yaml
    from iil_klickdummy import gen_e2e

    spec = {
        "spec_id": "repo:spec-test",
        "spec_version": "0.1",
        "spec_date": "2026-06-01",
        "adr": {"local": "repo:ADR-001", "conforms_to": "platform:ADR-211"},
        "class": "mock",
        "grounding": "test",
        "off_ramp": {},
        "personas": {"user": {}},
        "screens": [
            {
                "id": "detail",
                "title": "Detail",
                "route": "/items/<uuid:pk>/",
                "route_example": "/items/abc-123-def/",
                "parity_acceptance": [
                    {
                        "id": "d.visible",
                        "check": "visible",
                        "assert": {
                            "action": "visible",
                            "selector": "[data-testid=item]",
                        },
                    }
                ],
            },
        ],
    }
    spec_file = tmp_path / "spec.yaml"
    spec_file.write_text(yaml.dump(_conform(spec)), encoding="utf-8")
    out = tmp_path / "test_parity.py"
    gen_e2e.main([str(spec_file), str(out)])
    code = out.read_text(encoding="utf-8")
    assert "/items/abc-123-def/" in code  # route_example genutzt
    assert "<uuid:pk>" not in code  # Platzhalter NICHT im Output


def test_gen_e2e_parametrised_route_skipped(tmp_path):
    """Parametrisierte route ohne route_example → skip mit klarem Grund (Issue #28)."""
    import yaml
    from iil_klickdummy import gen_e2e

    spec = {
        "spec_id": "repo:spec-test",
        "spec_version": "0.1",
        "spec_date": "2026-06-01",
        "adr": {"local": "repo:ADR-001", "conforms_to": "platform:ADR-211"},
        "class": "mock",
        "grounding": "test",
        "off_ramp": {},
        "personas": {"user": {}},
        "screens": [
            {
                "id": "detail",
                "title": "Detail",
                "route": "/items/<uuid:pk>/",
                "parity_acceptance": [
                    {
                        "id": "d.vis",
                        "check": "visible",
                        "assert": {"action": "visible", "selector": "[data-testid=x]"},
                    }
                ],
            },
        ],
    }
    spec_file = tmp_path / "spec.yaml"
    spec_file.write_text(yaml.dump(_conform(spec)), encoding="utf-8")
    out = tmp_path / "test_parity.py"
    gen_e2e.main([str(spec_file), str(out)])
    code = out.read_text(encoding="utf-8")
    assert "pytest.mark.skip" in code
    assert "route_example" in code  # Hinweis im skip-reason
    assert "page.goto" not in code  # kein goto gegen 404
    # Regression: der parametrisierte skip-reason MUSS valides Python sein. Der unquoted
    # `reason={skip_reason}` brach mit SyntaxError (U+2014 em-dash); Text-Marker allein
    # fingen das nicht (vgl. ADR-211 Rev 21: „gebaut, nie ausgeführt").
    compile(code, str(out), "exec")


def test_gen_e2e_login_required_skip(tmp_path):
    """login_required ohne auth-Block → skip mit klarem Grund (Issue #28)."""
    import yaml
    from iil_klickdummy import gen_e2e

    spec = {
        "spec_id": "repo:spec-test",
        "spec_version": "0.1",
        "spec_date": "2026-06-01",
        "adr": {"local": "repo:ADR-001", "conforms_to": "platform:ADR-211"},
        "class": "mock",
        "grounding": "test",
        "off_ramp": {},
        "personas": {"user": {}},
        "screens": [
            {
                "id": "dashboard",
                "title": "Dashboard",
                "login_required": True,
                "parity_acceptance": [
                    {
                        "id": "d.vis",
                        "check": "title visible",
                        "assert": {
                            "action": "visible",
                            "selector": "[data-testid=dash]",
                        },
                    }
                ],
            },
        ],
    }
    spec_file = tmp_path / "spec.yaml"
    spec_file.write_text(yaml.dump(_conform(spec)), encoding="utf-8")
    out = tmp_path / "test_parity.py"
    gen_e2e.main([str(spec_file), str(out)])
    code = out.read_text(encoding="utf-8")
    assert "pytest.mark.skip" in code
    assert "login_required" in code


def test_gen_e2e_auth_storage_state_uses_real_playwright_api(tmp_path):
    """auth.storage_state → `browser_context_args`-Override (einzige API, die
    pytest-playwright kennt). Regression: zuvor wurde ein autouse-Fixture mit
    `page.context.set_storage_state(path=...)` emittiert — eine NICHT existierende
    API; die Suite brach gegen jeden echten login_required-Renderer-#2 sofort mit
    TypeError. Der Bug überlebte nur, weil die Suite nie gegen Renderer #2 lief."""
    import yaml
    from iil_klickdummy import gen_e2e

    spec = {
        "spec_id": "repo:spec-test",
        "spec_version": "0.1",
        "spec_date": "2026-06-01",
        "adr": {"local": "repo:ADR-001", "conforms_to": "platform:ADR-211"},
        "class": "mock",
        "grounding": "test",
        "off_ramp": {},
        "personas": {"user": {}},
        "auth": {"storage_state": "/tmp/auth/storage.json"},
        "screens": [
            {
                "id": "dash",
                "title": "Dashboard",
                "login_required": True,
                "route": "/dashboard/",
                "route_example": "/dashboard/",
                "parity_acceptance": [
                    {
                        "id": "d.vis",
                        "check": "visible",
                        "assert": {
                            "action": "visible",
                            "selector": "[data-testid=dash]",
                        },
                    }
                ],
            },
        ],
    }
    spec_file = tmp_path / "spec.yaml"
    spec_file.write_text(yaml.dump(_conform(spec)), encoding="utf-8")
    out = tmp_path / "test_parity.py"
    gen_e2e.main([str(spec_file), str(out)])
    code = out.read_text(encoding="utf-8")
    # Korrekte API: browser_context_args-Override mit storage_state
    assert "def browser_context_args(browser_context_args):" in code
    assert '"storage_state": "/tmp/auth/storage.json"' in code
    # Der kaputte API-Aufruf darf NIE wieder emittiert werden
    assert "set_storage_state" not in code
    # login_required wird durch den auth-Block aufgelöst → KEIN skip mehr
    assert "login_required_no_auth" not in code
    assert 'expect(page.locator("[data-testid=dash]").first).to_be_visible()' in code
    # Generierte Datei muss kompilieren
    compile(code, str(out), "exec")


# -- F23/D2: semantischer Selektor-Fallback (KONZ-iil-klickdummy-007) ----------


def test_locator_expr_prefix_dispatch():
    """`selector`-Präfixe wählen die passende Playwright-Locator-API; ohne
    Präfix bleibt es CSS via page.locator (F23/D2)."""
    from iil_klickdummy import gen_e2e as g

    assert (
        g._locator_expr("testid=sds-review-row")
        == 'page.get_by_test_id("sds-review-row")'
    )
    assert g._locator_expr("label=E-Mail") == 'page.get_by_label("E-Mail")'
    assert g._locator_expr("text=Speichern") == 'page.get_by_text("Speichern")'
    assert g._locator_expr("role=button") == 'page.get_by_role("button")'
    assert (
        g._locator_expr("role=button[name=Verify]")
        == 'page.get_by_role("button", name="Verify")'
    )
    # Bare String bleibt CSS — unveränderte Bestandsbehandlung.
    assert g._locator_expr("button.submit") == 'page.locator("button.submit")'
    # Unvollständiges role= (kein Match) fällt sicher auf CSS zurück.
    assert g._locator_expr("role=") == 'page.locator("role=")'


def test_render_assertion_uses_prefix_dispatch():
    """render_assertion routet Präfix-Selektoren durch _locator_expr; CSS-Form
    bleibt bit-identisch zur Bestandsausgabe (Regressionsschutz)."""
    from iil_klickdummy import gen_e2e as g

    assert (
        g.render_assertion({"action": "visible", "selector": "testid=queue"})
        == 'expect(page.get_by_test_id("queue").first).to_be_visible()'
    )
    assert (
        g.render_assertion(
            {"action": "clickable", "selector": "role=button[name=Prüfen]"}
        )
        == 'expect(page.get_by_role("button", name="Prüfen").first).to_be_enabled()'
    )
    assert (
        g.render_assertion({"action": "count", "selector": "testid=row", "expect": 2})
        == 'expect(page.get_by_test_id("row")).to_have_count(2)'
    )
    # Bestands-CSS-Form unverändert.
    assert (
        g.render_assertion({"action": "visible", "selector": "#x"})
        == 'expect(page.locator("#x").first).to_be_visible()'
    )


def test_is_fragile_selector_prefixes():
    """testid=/role=/label= sind stabile Anker; text= und bare CSS bleiben fragil (F23/D2)."""
    from iil_klickdummy import gen_e2e as g

    assert g.is_fragile_selector("testid=row") is False
    assert g.is_fragile_selector("role=button[name=OK]") is False
    assert g.is_fragile_selector("label=E-Mail") is False
    # text= ist der i18n-fragile Fallback → bewusst weiterhin fragil.
    assert g.is_fragile_selector("text=Speichern") is True
    # Bestandsverhalten unverändert.
    assert g.is_fragile_selector("[data-testid=submit]") is False
    assert g.is_fragile_selector("button.submit") is True


# -- REC-2/AD-2: role=-Parser-Grenzfälle + definiertes Fehlerverhalten ---------


def test_role_prefix_roundtrip_edge_cases():
    """REC-2: die role=-Mini-DSL ist ein Parser mit definiertem Verhalten —
    Leerzeichen und Sonderzeichen im name-Wert sind gültig (Quoting via
    json.dumps), ohne [name=…] entsteht kein name-Argument."""
    from iil_klickdummy import gen_e2e as g

    assert (
        g._locator_expr("role=button[name=Speichern]")
        == 'page.get_by_role("button", name="Speichern")'
    )
    # Leerzeichen im name-Wert → gültig, korrekt gequotet.
    assert (
        g._locator_expr("role=button[name=Bitte klicken]")
        == 'page.get_by_role("button", name="Bitte klicken")'
    )
    # Sonderzeichen (Unicode) im name-Wert → gültig, korrekt gequotet.
    assert (
        g._locator_expr("role=link[name=Zum nächsten Schritt →]")
        == 'page.get_by_role("link", name="Zum nächsten Schritt →")'
    )
    assert g._locator_expr("role=button") == 'page.get_by_role("button")'


def test_role_prefix_fallthrough_edge_cases():
    """REC-2: unbekanntes Präfix (Tippfehler `rol=`) und kaputte role=-Syntax
    (leerer Wert, fehlende `]`) fallen definiert auf CSS zurück — fragil
    markiert, mit benanntem Hint, nie Exception."""
    from iil_klickdummy import gen_e2e as g

    # Tippfehler-Präfix → CSS-Fallthrough + fragil + Hint.
    assert g._locator_expr("rol=button") == 'page.locator("rol=button")'
    assert g.is_fragile_selector("rol=button") is True
    assert "unbekanntes Präfix 'rol='" in g.selector_fallthrough_hint("rol=button")
    # Leerer role=-Wert → Fallthrough + Hint.
    assert g._locator_expr("role=") == 'page.locator("role=")'
    assert g.is_fragile_selector("role=") is True
    assert "role=-Syntax ungültig" in g.selector_fallthrough_hint("role=")
    # Fehlende schließende `]` → Fallthrough + Hint.
    assert (
        g._locator_expr("role=button[name=Verify")
        == 'page.locator("role=button[name=Verify")'
    )
    assert g.is_fragile_selector("role=button[name=Verify") is True
    assert "role=-Syntax ungültig" in g.selector_fallthrough_hint(
        "role=button[name=Verify"
    )
    # Kein Hint für gültige Präfixe, bare CSS und text= (bekannt-fragil ≠ Tippfehler).
    assert g.selector_fallthrough_hint("role=button") is None
    assert g.selector_fallthrough_hint("testid=row") is None
    assert g.selector_fallthrough_hint("button.submit") is None
    assert g.selector_fallthrough_hint("text=Speichern") is None
    assert g.selector_fallthrough_hint("") is None


def test_fallthrough_hint_lands_in_manifest(tmp_path):
    """REC-2: der Fallthrough-Hint steht im Manifest (fragile_selectors[].hint),
    damit CI/Autoren den Tippfehler sehen statt nur 'fragil'."""
    import json
    import yaml
    from iil_klickdummy import gen_e2e

    spec_file = tmp_path / "spec.yaml"
    out = tmp_path / "t.py"
    spec_file.write_text(
        yaml.dump(_conform(_strict_spec("rol=button"))), encoding="utf-8"
    )
    assert gen_e2e.main([str(spec_file), str(out)]) == 0
    manifest = json.loads(out.with_suffix(".manifest.json").read_text())
    (entry,) = manifest["fragile_selectors"]
    assert entry["selector"] == "rol=button"
    assert "unbekanntes Präfix 'rol='" in entry["hint"]


def _strict_spec(selector: str) -> dict:
    return {
        "spec_id": "repo:spec-test",
        "spec_version": "0.1",
        "spec_date": "2026-06-01",
        "adr": {"local": "repo:ADR-001", "conforms_to": "platform:ADR-211"},
        "class": "mock",
        "grounding": "test",
        "off_ramp": {},
        "personas": {"user": {}},
        "screens": [
            {
                "id": "s",
                "title": "S",
                "route": "/s/",
                "route_example": "/s/",
                "parity_acceptance": [
                    {
                        "id": "s.vis",
                        "check": "visible",
                        "assert": {"action": "visible", "selector": selector},
                    }
                ],
            },
        ],
    }


def test_strict_selectors_gate_blocks_fragile(tmp_path):
    """F23/D1: `--strict-selectors` macht einen fragilen Selektor zum exit 3,
    während der Default-Lauf (nur Warnung) 0 bleibt — und ein stabiler Anker
    auch unter --strict-selectors grün ist."""
    import json
    import yaml
    from iil_klickdummy import gen_e2e

    spec_file = tmp_path / "spec.yaml"
    out = tmp_path / "t.py"

    # bare CSS = fragil → Default 0 (nur Warnung), strict 3 (Gate rot)
    spec_file.write_text(
        yaml.dump(_conform(_strict_spec("button.submit"))), encoding="utf-8"
    )
    assert gen_e2e.main([str(spec_file), str(out)]) == 0
    assert gen_e2e.main([str(spec_file), str(out), "--strict-selectors"]) == 3
    manifest = json.loads(out.with_suffix(".manifest.json").read_text())
    assert manifest["strict_selectors"] is True

    # stabiler Präfix-Anker → auch strict grün
    spec_file.write_text(
        yaml.dump(_conform(_strict_spec("testid=submit"))), encoding="utf-8"
    )
    assert gen_e2e.main([str(spec_file), str(out), "--strict-selectors"]) == 0


def test_strict_selectors_spec_attribute_without_cli_flag(tmp_path):
    """REC-1 (AD-1/M28-2): `strict_selectors: true` als Spec-Top-Level-Attribut
    aktiviert das Off-Ramp-Gate OHNE CLI-Flag — Enforcement ist spec-deklariert
    und hängt nicht daran, dass jede CI-Config das Flag korrekt setzt. Das
    CLI-Flag bleibt rückwärtskompatibel (Test oben deckt es ohne Spec-Attribut)."""
    import json
    import yaml
    from iil_klickdummy import gen_e2e

    spec_file = tmp_path / "spec.yaml"
    out = tmp_path / "t.py"

    # Spec-Attribut + fragiler Selektor → Gate rot (exit 3) ohne CLI-Flag
    spec = _strict_spec("button.submit")
    spec["strict_selectors"] = True
    spec_file.write_text(yaml.dump(_conform(spec)), encoding="utf-8")
    assert gen_e2e.main([str(spec_file), str(out)]) == 3
    manifest = json.loads(out.with_suffix(".manifest.json").read_text())
    assert manifest["strict_selectors"] is True

    # Spec-Attribut + stabiler Präfix-Anker → grün
    spec = _strict_spec("testid=submit")
    spec["strict_selectors"] = True
    spec_file.write_text(yaml.dump(_conform(spec)), encoding="utf-8")
    assert gen_e2e.main([str(spec_file), str(out)]) == 0

    # strict_selectors: false = Default-Verhalten (Warnung statt Gate)
    spec = _strict_spec("button.submit")
    spec["strict_selectors"] = False
    spec_file.write_text(yaml.dump(_conform(spec)), encoding="utf-8")
    assert gen_e2e.main([str(spec_file), str(out)]) == 0
    manifest = json.loads(out.with_suffix(".manifest.json").read_text())
    assert manifest["strict_selectors"] is False


# -- B-1/B-2: Input-Injection/RCE-Härtung (Spec = Vertrauensgrenze) ------------


def test_should_reject_newline_in_title_via_schema_validation(tmp_path):
    """B-1: ein `\\n` in screens[].title bräche sonst aus der `#`-Kommentarzeile
    der generierten Datei aus (aktive Python-Zeile bei pytest-collect, VOR
    importorskip → RCE). load_spec validiert jetzt gegen das Schema; der
    newline-verbietende title-Pattern macht das zum harten Fehler (exit 1)."""
    import pytest
    import yaml
    from iil_klickdummy import gen_e2e

    spec = _conform(
        {
            "spec_id": "repo:spec-test",
            "spec_version": "0.1",
            "spec_date": "2026-06-01",
            "adr": {"local": "repo:ADR-001", "conforms_to": "platform:ADR-211"},
            "class": "mock",
            "screens": [
                {
                    "id": "login",
                    "title": "Login\nimport os",
                    "route": "/login/",
                    "route_example": "/login/",
                    "parity_acceptance": [
                        {
                            "id": "l.vis",
                            "check": "visible check",
                            "assert": {
                                "action": "visible",
                                "selector": "[data-testid=x]",
                            },
                        }
                    ],
                },
            ],
        }
    )
    spec_file = tmp_path / "spec.yaml"
    spec_file.write_text(yaml.dump(spec), encoding="utf-8")
    with pytest.raises(SystemExit) as ei:
        gen_e2e.load_spec(spec_file)
    assert ei.value.code == 1


def test_should_reject_schema_invalid_spec_in_load_spec(tmp_path):
    """B-1: load_spec ruft jsonschema.validate — eine strukturell kaputte Spec
    (fehlendes Pflichtfeld) wird zum harten Fehler statt blind generiert."""
    import pytest
    import yaml
    from iil_klickdummy import gen_e2e

    spec = {"spec_id": "repo:x", "screens": []}  # viele Pflichtfelder fehlen
    spec_file = tmp_path / "spec.yaml"
    spec_file.write_text(yaml.dump(spec), encoding="utf-8")
    with pytest.raises(SystemExit) as ei:
        gen_e2e.load_spec(spec_file)
    assert ei.value.code == 1
    assert gen_e2e.validate_spec(spec)  # nicht-leere Fehlerliste


def test_should_escape_malicious_title_in_generated_comment(tmp_path):
    """B-1 Defense-in-Depth: selbst wenn ein `\\n`-Titel die Validierung umginge,
    darf gen_suite daraus KEINE aktive Codezeile machen — der Wert wird in der
    `#`-Kommentarzeile zu einem Space kollabiert; die Datei bleibt harmlos."""
    from iil_klickdummy import gen_e2e

    payload = "PWNED = __import__('os').system('touch /tmp/pwned')"
    spec = {
        "spec_id": "repo:x",
        "spec_version": "0.1",
        "screens": [
            {
                "id": "login",
                "title": f"Login\n{payload}",
                "route": "/login/",
                "route_example": "/login/",
                "parity_acceptance": [
                    {
                        "id": "l.vis",
                        "check": "visible check",
                        "assert": {"action": "visible", "selector": "[data-testid=x]"},
                    }
                ],
            },
        ],
    }
    spec_file = tmp_path / "spec.yaml"
    spec_file.write_text("sha-source", encoding="utf-8")  # nur für die SHA
    code, _ = gen_e2e.gen_suite(spec, spec_file, "test_parity.py")
    # Der Payload darf NUR innerhalb einer Kommentarzeile stehen, nie als Codezeile
    for ln in code.splitlines():
        if payload in ln:
            assert ln.lstrip().startswith("#"), f"Payload als aktive Zeile: {ln!r}"
    assert not any(ln.startswith("PWNED") for ln in code.splitlines())
    compile(code, "gen.py", "exec")  # muss valides, harmloses Python sein


def test_should_neutralise_docstring_backslash_and_triple_quote(tmp_path):
    """B-2: ein `check`, der `\"\"\"` enthält oder auf `\\` endet, darf den
    Docstring nicht schließen/escapen und die Folgezeile ausführbar machen.
    Härtung gegen `\"\"\"` UND trailing Backslash → die Datei kompiliert sauber."""
    from iil_klickdummy import gen_e2e

    payload = 'evil """ + __import__("os").system("id") + """ tail\\'
    spec = {
        "spec_id": "repo:x",
        "spec_version": "0.1",
        "screens": [
            {
                "id": "s",
                "title": "S",
                "route": "/s/",
                "route_example": "/s/",
                "parity_acceptance": [
                    {
                        "id": "s.vis",
                        "check": payload,
                        "assert": {"action": "visible", "selector": "[data-testid=x]"},
                    }
                ],
            },
        ],
    }
    spec_file = tmp_path / "spec.yaml"
    spec_file.write_text("sha-source", encoding="utf-8")
    code, _ = gen_e2e.gen_suite(spec, spec_file, "t.py")
    compile(code, "gen.py", "exec")  # kaputter Docstring → SyntaxError, hier nicht
    assert "evil ''' +" in code  # `"""` im check → `'''` neutralisiert
    assert 'tail"""' in code  # Docstring schließt sauber
    assert "tail\\" not in code  # trailing `\` entfernt (escaped Quote nicht)


def test_should_sanitize_login_fixture_into_safe_identifier(tmp_path):
    """B-1: auth.login_fixture wird als Funktions-Parametername emittiert; ein
    bösartiger Wert muss zu einem sicheren Python-Bezeichner gezwungen werden,
    sonst injiziert er ausführbaren Code in die Fixture-Signatur."""
    from iil_klickdummy import gen_e2e

    spec = {
        "spec_id": "repo:x",
        "spec_version": "0.1",
        "auth": {"login_fixture": "x): pass\nimport os  # evil"},
        "screens": [
            {
                "id": "s",
                "title": "S",
                "route": "/s/",
                "route_example": "/s/",
                "login_required": True,
                "parity_acceptance": [
                    {
                        "id": "s.vis",
                        "check": "visible check",
                        "assert": {"action": "visible", "selector": "[data-testid=x]"},
                    }
                ],
            },
        ],
    }
    spec_file = tmp_path / "spec.yaml"
    spec_file.write_text("sha-source", encoding="utf-8")
    code, _ = gen_e2e.gen_suite(spec, spec_file, "t.py")
    compile(code, "gen.py", "exec")
    assert "def _auth(x_pass_import_os_evil: Page):" in code
    assert "import os  # evil" not in code.split("def _auth")[1][:120]


# -- Follow-up-Härtungen zu PR #102 (externe Zweitmeinung AD-2/AD-3/AD-5/M28-3) --


def test_should_neutralise_docstring_trailing_single_quote(tmp_path):
    """AD-2: ein `check`, der auf einem einzelnen `"` endet, stieß sonst an das
    schließende `\"\"\"` (`…\"` + `\"\"\"` = vier Quotes → unterminated string).
    _doc_safe bricht die Quote-Adjacency; die generierte Datei kompiliert."""
    from iil_klickdummy import gen_e2e

    assert gen_e2e._doc_safe('foo"').endswith('" ')  # trailing " entschärft
    spec = {
        "spec_id": "repo:x",
        "spec_version": "0.1",
        "screens": [
            {
                "id": "s",
                "title": "S",
                "route": "/s/",
                "route_example": "/s/",
                "parity_acceptance": [
                    {
                        "id": "s.vis",
                        "check": 'ends with a quote "',
                        "assert": {"action": "visible", "selector": "[data-testid=x]"},
                    }
                ],
            },
        ],
    }
    spec_file = tmp_path / "spec.yaml"
    spec_file.write_text("sha-source", encoding="utf-8")
    code, _ = gen_e2e.gen_suite(spec, spec_file, "t.py")
    compile(code, "gen.py", "exec")  # vorher: SyntaxError


def test_should_reject_trailing_newline_in_title_via_schema(tmp_path):
    """AD-3: das bare `^[^\\n\\r]*$` ließ ein *trailing* `\\n` durch (`$` matcht vor
    End-`\\n`), während `\\r` fiel. Die Negative-Lookahead-Form lehnt beides ab."""
    from iil_klickdummy import gen_e2e

    base = {
        "spec_id": "repo:x",
        "spec_version": "0.1",
        "spec_date": "2026-06-01",
        "adr": {"local": "repo:ADR-001", "conforms_to": "platform:ADR-211"},
        "class": "mock",
    }
    # trailing \n im Screen-title → jetzt schema-invalid
    spec = _conform(
        {
            **base,
            "screens": [
                {
                    "id": "s",
                    "title": "Login\n",
                    "parity_acceptance": [
                        {
                            "id": "s.v",
                            "check": "visible c",
                            "assert": {
                                "action": "visible",
                                "selector": "[data-testid=x]",
                            },
                        }
                    ],
                }
            ],
        }
    )
    assert any("title" in e for e in gen_e2e.validate_spec(spec))
    # sauberer title bleibt valide
    ok = _conform(
        {
            **base,
            "screens": [
                {
                    "id": "s",
                    "title": "Login",
                    "parity_acceptance": [
                        {
                            "id": "s.v",
                            "check": "visible c",
                            "assert": {
                                "action": "visible",
                                "selector": "[data-testid=x]",
                            },
                        }
                    ],
                }
            ],
        }
    )
    assert not any("title" in e for e in gen_e2e.validate_spec(ok))


def _minimal_screen():
    return {
        "id": "s",
        "title": "Screen",
        "parity_acceptance": [
            {
                "id": "s.v",
                "check": "visible c",
                "assert": {"action": "visible", "selector": "[data-testid=x]"},
            }
        ],
    }


def test_should_accept_sister_of_referencing_klickdummy_spec_slug():
    """Issue #165: `sister_of` erlaubte bisher nur `<repo>:ADR-NNN` — real
    referenzieren Specs (risk-hub/explosionsschutz) Schwester-Specs direkt via
    `<repo>:klickdummy-spec-<slug>` (ohne eigene ADR)."""
    from iil_klickdummy import gen_e2e

    spec = _conform(
        {
            "spec_id": "repo:x",
            "spec_version": "0.1",
            "spec_date": "2026-06-01",
            "adr": {
                "local": "repo:ADR-001",
                "conforms_to": "platform:ADR-211",
                "sister_of": ["risk-hub:klickdummy-spec-ex-schutz-konzept"],
            },
            "class": "mock",
            "screens": [_minimal_screen()],
        }
    )
    assert not any("sister_of" in e for e in gen_e2e.validate_spec(spec))


def test_should_still_accept_sister_of_referencing_adr():
    """Rückwärtskompatibilität: die ursprüngliche `<repo>:ADR-NNN`-Form bleibt
    gültig, das Pattern wurde erweitert, nicht ersetzt."""
    from iil_klickdummy import gen_e2e

    spec = _conform(
        {
            "spec_id": "repo:x",
            "spec_version": "0.1",
            "spec_date": "2026-06-01",
            "adr": {
                "local": "repo:ADR-001",
                "conforms_to": "platform:ADR-211",
                "sister_of": ["other-repo:ADR-099"],
            },
            "class": "mock",
            "screens": [_minimal_screen()],
        }
    )
    assert not any("sister_of" in e for e in gen_e2e.validate_spec(spec))


def test_should_reject_sister_of_with_invalid_format():
    """Weder ADR- noch Slug-Form — z.B. fehlendes Repo-Präfix — bleibt abgelehnt."""
    from iil_klickdummy import gen_e2e

    spec = _conform(
        {
            "spec_id": "repo:x",
            "spec_version": "0.1",
            "spec_date": "2026-06-01",
            "adr": {
                "local": "repo:ADR-001",
                "conforms_to": "platform:ADR-211",
                "sister_of": ["not-a-valid-reference"],
            },
            "class": "mock",
            "screens": [_minimal_screen()],
        }
    )
    assert any("sister_of" in e for e in gen_e2e.validate_spec(spec))


def test_should_reject_non_identifier_login_fixture_via_schema(tmp_path):
    """AD-5: ein login_fixture, das kein gültiger Python-Bezeichner ist, wird
    fail-closed im Schema abgelehnt (statt still via ident() gecoerct)."""
    from iil_klickdummy import gen_e2e

    base = {
        "spec_id": "repo:x",
        "spec_version": "0.1",
        "spec_date": "2026-06-01",
        "adr": {"local": "repo:ADR-001", "conforms_to": "platform:ADR-211"},
        "class": "mock",
        "screens": [
            {
                "id": "s",
                "title": "S",
                "parity_acceptance": [
                    {
                        "id": "s.v",
                        "check": "visible c",
                        "assert": {"action": "visible", "selector": "[data-testid=x]"},
                    }
                ],
            }
        ],
    }
    bad = _conform({**base, "auth": {"login_fixture": "x): pass\nimport os"}})
    assert any("login_fixture" in e for e in gen_e2e.validate_spec(bad))
    good = _conform({**base, "auth": {"login_fixture": "as_admin"}})
    assert not any("login_fixture" in e for e in gen_e2e.validate_spec(good))


def test_should_cache_loaded_schema(tmp_path):
    """M28-3: _load_schema ist gecacht (unveränderliches Paket-Asset) — zwei
    Aufrufe liefern dasselbe Objekt statt zweimal von Disk zu lesen."""
    from iil_klickdummy import gen_e2e

    assert gen_e2e._load_schema() is gen_e2e._load_schema()

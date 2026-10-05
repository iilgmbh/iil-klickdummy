"""Browser-Tests für den Render-Fallback (generate_render_fallback).

Umgezogen aus meiki-lra/meiki-hub ``tests/test_render.py`` (meiki-hub#549):
dort liefen die acht Tests gegen Seiten vom Mai 2026, die der heutige
Generator nicht mehr erzeugt. Hier rendern sie aus zwei synthetischen Specs
und prüfen das Verhalten im echten Browser (Chromium via Playwright).

Ohne Playwright wird übersprungen. Mit ``KD_RENDER_BROWSER=1`` (CI-Job
``render-browser``) ist das ein Fehler, damit der Lauf nicht grün ohne Wirkung
bleibt.
"""

from __future__ import annotations

import functools
import os
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

import pytest

from iil_klickdummy import lineage
from iil_klickdummy.genesor.config import GenesorConfig, get_cfg, set_cfg

BROWSER_PFLICHT = os.environ.get("KD_RENDER_BROWSER") == "1"

if BROWSER_PFLICHT:
    from playwright.sync_api import Error as PlaywrightError
    from playwright.sync_api import sync_playwright
else:
    pytest.importorskip("playwright", reason="playwright nicht installiert")
    from playwright.sync_api import Error as PlaywrightError
    from playwright.sync_api import sync_playwright

REPO = "test-repo"
SKIN_DATEI = "skins/fixture-skin.css"
SKIN_MARKER = "--fixture-skin-geladen"
FOKUS_TEXT = "Vorgänge des Bürgers anzeigen"

ENTITIES = {
    "antrag": {"description": "Antrag", "fields": ["az", "status"]},
    "person": {"description": "Person", "fields": ["name", "ort"]},
    "bescheid": {"description": "Bescheid", "fields": ["nr", "datum"]},
}

PERSONAS = {
    "buerger": {"label": "Bürger"},
    "sachbearbeiter": {"label": "Sachbearbeiter"},
}

# 8 Screens → Sidebar-Layout (Schwelle im Renderer: 6)
PORTAL_SPEC = {
    "spec_id": "portal",
    "spec_version": "0.1",
    "title": "Portal",
    "class": "mock",
    "off_ramp": {"unit": "per-screen", "rule": "test"},
    "personas": PERSONAS,
    "local_entities": ENTITIES,
    "screens": [
        {
            "id": "dashboard_buerger",
            "title": "Übersicht",
            "halbschicht": "buerger",
            "personas": ["buerger"],
            "fokus": [FOKUS_TEXT],
            "next_screens": ["antrag_detail"],
            "lokale_entities": ["antrag"],
        },
        {
            "id": "antrag_detail",
            "title": "Vorgangs-Detail",
            "halbschicht": "buerger",
            "personas": ["buerger"],
        },
        {
            "id": "buerger_360view",
            "title": "Bürger-Sicht",
            "halbschicht": "verwaltung",
            "personas": ["sachbearbeiter"],
            "lokale_entities": ["antrag", "person", "bescheid"],
        },
        *(
            {
                "id": f"verwaltung_{n}",
                "title": f"Verwaltung {n}",
                "halbschicht": "verwaltung",
                "personas": ["sachbearbeiter"],
            }
            for n in range(1, 6)
        ),
    ],
}

# 5 Screens → Tab-Layout, mit eigenem Skin
FACHVERFAHREN_SPEC = {
    "spec_id": "fachverfahren",
    "spec_version": "0.1",
    "title": "Fachverfahren",
    "class": "mock",
    "off_ramp": {"unit": "per-screen", "rule": "test"},
    "app_skin": {"custom_css": SKIN_DATEI},
    "screens": [
        {"id": f"schritt_{n}", "title": f"Schritt {n}", "personas": ["sachbearbeiter"]}
        for n in range(1, 6)
    ],
}


class _LeiserHandler(SimpleHTTPRequestHandler):
    def log_message(self, *args):  # noqa: D401 — kein Rauschen im Testlauf
        pass


@pytest.fixture(scope="module")
def render_root(tmp_path_factory):
    """Rendert beide Specs in ein eigenes repos_root und liefert dessen Pfad."""
    root = tmp_path_factory.mktemp("repos")
    skin = root / REPO / SKIN_DATEI
    skin.parent.mkdir(parents=True)
    skin.write_text(f":root {{ {SKIN_MARKER}: 1; }}\n", encoding="utf-8")

    vorher = get_cfg()
    set_cfg(GenesorConfig(repos_root=root))
    try:
        for spec in (PORTAL_SPEC, FACHVERFAHREN_SPEC):
            record = {
                "spec_id": spec["spec_id"],
                "path": root / REPO / "screens-spec.yaml",
                "data": spec,
                "repo": REPO,
                "kd": spec["spec_id"],
            }
            lineage.generate_render_fallback(record, root / "genesor")
    finally:
        set_cfg(vorher)
    return root


@pytest.fixture(scope="module")
def base_url(render_root):
    """Eigener Server auf freiem Port — kein fremder Listener (meiki-hub#544)."""
    handler = functools.partial(_LeiserHandler, directory=str(render_root))
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{server.server_address[1]}"
    server.shutdown()
    server.server_close()


@pytest.fixture(scope="module")
def browser():
    with sync_playwright() as pw:
        try:
            chromium = pw.chromium.launch(headless=True)
        except PlaywrightError as exc:
            if BROWSER_PFLICHT:
                raise
            pytest.skip(f"Chromium nicht startbar: {exc}")
        yield chromium
        chromium.close()


@pytest.fixture
def page(browser):
    context = browser.new_context()
    page = context.new_page()
    page.set_default_timeout(5000)
    yield page
    context.close()


def _portal(page, base_url):
    page.goto(f"{base_url}/genesor/render/{REPO}-portal.html")
    return page


def _fachverfahren(page, base_url):
    page.goto(f"{base_url}/genesor/render/{REPO}-fachverfahren.html")
    return page


def test_should_use_sidebar_layout_with_halbschicht_groups(page, base_url):
    _portal(page, base_url)
    assert "has-sidebar" in page.evaluate("document.body.className")
    sidebar = page.locator("aside.sidebar")
    assert sidebar.is_visible()
    halbschichten = sidebar.locator("h3").all_text_contents()
    assert any("Bürger-Halbschicht" in h for h in halbschichten), halbschichten
    assert any("Verwaltungs-Halbschicht" in h for h in halbschichten), halbschichten


def test_should_use_tab_layout_for_five_screens(page, base_url):
    _fachverfahren(page, base_url)
    assert "has-tabs" in page.evaluate("document.body.className")
    assert page.locator("nav.tabs").is_visible()
    assert not page.locator("aside.sidebar").is_visible()


def test_should_open_info_modal_with_spec_content(page, base_url):
    _portal(page, base_url)
    modal = page.locator("#info-modal-bg")
    assert not modal.is_visible()
    page.locator("section.screen.active .info-btn").click()
    assert modal.is_visible()
    body_text = page.locator("#info-modal-body").text_content()
    assert body_text and FOKUS_TEXT in body_text, (
        f"Modal-Body leer/falsch: {body_text!r}"
    )


def test_should_close_modal_on_escape(page, base_url):
    _portal(page, base_url)
    page.locator("section.screen.active .info-btn").click()
    assert page.locator("#info-modal-bg").is_visible()
    page.keyboard.press("Escape")
    assert not page.locator("#info-modal-bg").is_visible()


def test_should_hide_screens_of_other_personas(page, base_url):
    _portal(page, base_url)
    page.locator("#persona-select").select_option("sachbearbeiter")
    fremd = page.locator('aside.sidebar button[data-screen="dashboard_buerger"]')
    eigen = page.locator('aside.sidebar button[data-screen="buerger_360view"]')
    assert "hidden" in (fremd.get_attribute("class") or "")
    assert "hidden" not in (eigen.get_attribute("class") or "")


def test_should_navigate_via_next_screens_button(page, base_url):
    _portal(page, base_url)
    page.locator('aside.sidebar button[data-screen="dashboard_buerger"]').click()
    page.locator("section#screen-dashboard_buerger .actions button").first.click()
    active = page.locator("section.screen.active").get_attribute("id")
    assert active == "screen-antrag_detail", (
        f"Screen-Wechsel nicht erfolgt, aktiv: {active}"
    )


def test_should_load_custom_css_skin(page, base_url):
    _fachverfahren(page, base_url)
    links = page.evaluate(
        "Array.from(document.querySelectorAll('link[rel=stylesheet]')).map(l => l.href)"
    )
    assert any(SKIN_DATEI in href for href in links), f"Skin nicht eingebunden: {links}"
    wert = page.evaluate(
        f"getComputedStyle(document.documentElement).getPropertyValue('{SKIN_MARKER}')"
    )
    assert wert.strip() == "1", "Skin eingebunden, aber nicht geladen"


def test_should_switch_entity_sub_tabs(page, base_url):
    _portal(page, base_url)
    page.locator('aside.sidebar button[data-screen="buerger_360view"]').click()
    section = page.locator("section#screen-buerger_360view.active")
    sub_tabs = section.locator(".sub-tabs button").all()
    assert len(sub_tabs) == 3, f"Erwartet 3 Sub-Tabs, ist {len(sub_tabs)}"
    sub_tabs[1].click()
    aktiv = section.locator(".sub-tabs button.active").all_text_contents()
    assert aktiv == [sub_tabs[1].text_content()]

"""A11y-/Responsive-Tests für den Render-Fallback (RENDER_FALLBACK_TEMPLATE).

Vorher: keine ARIA-Rollen auf Tabs/Sub-Tabs, kein Focus-Management in Modals,
keine @media-Query, kein Scroll-Reset bei Screen-Wechsel.
"""

from __future__ import annotations

from iil_klickdummy import lineage


SPEC = {
    "spec_id": "a11y-kd",
    "spec_version": "0.1",
    "title": "A11y-Test",
    "class": "mock",
    "off_ramp": {"unit": "per-screen", "rule": "test"},
    "local_entities": {
        "antrag": {"fields": ["az", "status"]},
        "person": {"fields": ["name", "ort"]},
    },
    "screens": [
        {
            "id": "liste",
            "title": "Liste",
            "personas": ["SB"],
            "lokale_entities": ["antrag", "person"],
        },
        {"id": "detail", "title": "Detail", "personas": ["SB"]},
    ],
}


def _render(tmp_path) -> str:
    record = {
        "spec_id": "a11y-kd",
        "path": tmp_path / "screens-spec.yaml",
        "data": SPEC,
        "repo": "test-repo",
        "kd": "a11y-kd",
    }
    return lineage.generate_render_fallback(record, tmp_path).read_text()


def test_tabs_should_have_tablist_and_tab_roles(tmp_path):
    html = _render(tmp_path)
    assert 'role="tablist" aria-label="Screens"' in html
    assert html.count('role="tab" aria-selected="false" aria-controls="screen-') == 2


def test_subtabs_should_have_tab_roles_and_panels(tmp_path):
    html = _render(tmp_path)
    assert 'role="tablist" aria-label="Entitäten"' in html
    assert 'aria-controls="sub-liste-0"' in html
    assert html.count('role="tabpanel"') == 2


def test_modal_should_be_dialog_with_focus_management(tmp_path):
    html = _render(tmp_path)
    assert 'role="dialog" aria-modal="true" aria-labelledby="info-modal-title"' in html
    assert 'aria-label="Dialog schließen"' in html
    assert "_modalReturnFocus" in html  # Fokus-Rückgabe + leichter Trap


def test_spec_toggle_should_expose_aria_pressed(tmp_path):
    html = _render(tmp_path)
    assert 'id="spec-toggle" aria-pressed="false"' in html
    assert "setAttribute('aria-pressed'" in html


def test_template_should_have_keyboard_nav_and_scroll_reset(tmp_path):
    html = _render(tmp_path)
    assert "ArrowRight" in html and "ArrowUp" in html  # Pfeiltasten-Nav
    assert "window.scrollTo" in html  # Scroll-Reset je Screen-Wechsel


def test_template_should_have_mobile_breakpoint(tmp_path):
    html = _render(tmp_path)
    assert "@media (max-width: 768px)" in html
    assert "focus-visible" in html


# --- KONZ-009: Content-Screen-Typ -------------------------------------------


def _render_spec(tmp_path, spec: dict) -> str:
    record = {
        "spec_id": spec["spec_id"],
        "path": tmp_path / "screens-spec.yaml",
        "data": spec,
        "repo": "test-repo",
        "kd": spec["spec_id"],
    }
    return lineage.generate_render_fallback(record, tmp_path).read_text()


def test_content_screen_should_render_blocks_instead_of_empty_hint(tmp_path):
    spec = {
        "spec_id": "content-kd",
        "spec_version": "0.1",
        "title": "Content-Test",
        "class": "mock",
        "off_ramp": {"unit": "per-screen", "rule": "test"},
        "screens": [
            {
                "id": "landing",
                "title": "Landing",
                "personas": ["besucher"],
                "off_route": True,
                "content": [
                    {
                        "type": "hero",
                        "headline": "Willkommen bei DriftTales",
                        "sub": "Reise-Story",
                        "label": "Jetzt starten",
                    },
                    {"type": "prose", "text": "Deine Reise wird zur Geschichte."},
                ],
            },
        ],
    }
    html_out = _render_spec(tmp_path, spec)
    assert "Willkommen bei DriftTales" in html_out
    assert "Deine Reise wird zur Geschichte." in html_out
    # der Leer-Hinweis darf für diesen Screen NICHT erscheinen
    assert "Keine Daten-Entities für diesen Screen deklariert." not in html_out


def test_content_screen_should_escape_spec_strings(tmp_path):
    spec = {
        "spec_id": "xss-kd",
        "spec_version": "0.1",
        "title": "XSS-Test",
        "class": "mock",
        "off_ramp": {"unit": "per-screen", "rule": "test"},
        "screens": [
            {
                "id": "landing",
                "title": "Landing",
                "personas": ["besucher"],
                "content": [{"type": "hero", "headline": "<script>alert(1)</script>"}],
            },
        ],
    }
    html_out = _render_spec(tmp_path, spec)
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in html_out
    assert "<script>alert(1)</script>" not in html_out

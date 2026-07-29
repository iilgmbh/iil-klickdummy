# AUTO-GENERATED — NICHT von Hand editieren (re-generieren: klickdummy-gen-e2e).
# Quelle: iil-klickdummy:klickdummy-spec-browser v0.2  (screens-spec.yaml)
# Spec-SHA256: 577a7cdeb496d81d83f7d73ecfa15395097d045f925de6fce66d60f9b317f25f  ·  platform:ADR-211 §Parity-Off-Ramp (I3-Gate)
# Deterministisch aus der Spec — KEIN Zeitstempel im File (sonst rauscht der
# Drift-Check `klickdummy-parity-drift`). Lauf-Metadaten stehen im Manifest.
#
# DUAL-RENDERER: dieselbe Assertion gegen Renderer #1 (Klickdummy) UND #2 (App).
# Env renderer-neutral benannt — die Suite überlebt den Klickdummy-Sunset:
#   SPEC_RENDERER_BASE_URL=http://localhost:8000 pytest test_parity_browser.py   # Renderer #1 (Klickdummy)
#   SPEC_RENDERER_BASE_URL=https://app.example   pytest test_parity_browser.py   # Renderer #2 (echte App)
# Parity-grün gegen #2 ⇒ Screen darf aus statischer Quelle (off_ramp_status: parity-green).
#
# WICHTIG — Drift-Check ≠ Parität: `make klickdummy-parity-drift` prüft NUR, ob diese
# Datei zur Spec passt (re-gen + diff). Es FÜHRT diese Assertions NICHT aus und belegt
# KEINE Parität. Parität entsteht erst, wenn diese Suite mit pytest + playwright gegen
# einen laufenden SPEC_RENDERER_BASE_URL läuft; „gegen Renderer #2" setzt eine echte,
# erreichbare App-Route voraus — fehlt sie, ist „Dual-Renderer" nur Renderer #1.
import os

import pytest

# Adopter ohne installiertes playwright überspringen die Suite, statt beim
# Sammeln zu brechen (T-01). Schützt CI ohne `testpaths`-Isolation (risk-hub
# #146 entging dem nur per Zufall) — platform:ADR-211 §Executable-Parity-Bridge.
pytest.importorskip("playwright")

from playwright.sync_api import Page, expect  # noqa: E402

BASE = os.environ.get("SPEC_RENDERER_BASE_URL", "http://localhost:8000").rstrip("/")


# ── Screen: browser-frei · Frei-Modus — Klickdummy auswählen & ansehen  (route /browser-frei) ──
def test_browser_frei__browser_frei_select_visible(page: Page):
    """[browser-frei] Das Klickdummy-Auswahl-Dropdown ist sichtbar und bedienbar."""
    page.goto(BASE + "/browser-frei")
    expect(page.get_by_test_id("kd-select").first).to_be_visible()


def test_browser_frei__browser_frei_detail_after_select(page: Page):
    """[browser-frei] Nach Auswahl erscheint das Detail-Panel mit Spec-ID, Klasse-Badge, ADR, Pfad."""
    page.goto(BASE + "/browser-frei")
    expect(page.get_by_test_id("kd-detail").first).to_be_visible()


def test_browser_frei__browser_frei_class_badge_stable(page: Page):
    """[browser-frei] Die Klasse wird als stabiler Badge-Anker gezeigt (nicht als fragiler CSS-Pfad)."""
    page.goto(BASE + "/browser-frei")
    expect(page.get_by_test_id("kd-class-badge").first).to_be_visible()


def test_browser_frei__browser_frei_frame_visible(page: Page):
    """[browser-frei] Der iframe wird nach einer Auswahl sichtbar (Leerzustand verschwindet)."""
    page.goto(BASE + "/browser-frei")
    expect(page.get_by_test_id("kd-frame").first).to_be_visible()


def test_browser_frei__browser_frei_no_injection(page: Page):
    """[browser-frei] N1/S-01: Ein Klickdummy mit title 'x</script><script>...' wird als Text gezeigt, kein Script läuft. ENTSCHIEDEN (ADR-002 AS-1): Titel-Sortierung bleibt Generierungsreihenfolge."""
    page.goto(BASE + "/browser-frei")
    expect(page.get_by_test_id("kd-select").first).to_be_visible()


def test_browser_frei__browser_frei_frame_error_visible(page: Page):
    """[browser-frei] N4: Lädt die Shell nicht (404/leere Seite/keine Antwort), erscheint eine sichtbare Fehlermeldung statt eines leeren iframes. Fehlerzustand — nur bei injiziertem Ladefehler sichtbar."""
    page.goto(BASE + "/browser-frei")
    expect(page.get_by_test_id("frame-load-error").first).to_be_visible()


# ── Screen: browser-story · Story-Walk — geführte Journey über mehrere Klickdummies  (route /browser-story) ──
def test_browser_story__browser_story_toggle_when_stories(page: Page):
    """[browser-story] Der Modus-Toggle ist sichtbar, wenn Stories vorhanden sind."""
    page.goto(BASE + "/browser-story")
    expect(page.get_by_test_id("mode-toggle").first).to_be_visible()


def test_browser_story__browser_story_stepper_count(page: Page):
    """[browser-story] Der Stepper listet genau so viele Einträge wie die Story Schritte hat."""
    page.goto(BASE + "/browser-story")
    expect(page.get_by_test_id("story-stepper").first).to_be_visible()


def test_browser_story__browser_story_next_enabled(page: Page):
    """[browser-story] Auf Schritt 1 einer mehrschrittigen Story ist Weiter bedienbar."""
    page.goto(BASE + "/browser-story")
    expect(page.get_by_test_id("btn-next").first).to_be_enabled()


def test_browser_story__browser_story_error_visible(page: Page):
    """[browser-story] N4: Ein Schritt mit fehlendem kd_index zeigt eine sichtbare Meldung, keinen leeren iframe. ENTSCHIEDEN (ADR-002 AS-2): Meldung statt Auto-Skip."""
    page.goto(BASE + "/browser-story")
    expect(page.get_by_test_id("step-load-error").first).to_be_visible()


def test_browser_story__browser_story_stepper_keyboard(page: Page):
    """[browser-story] N6: Jeder Stepper-Eintrag ist per Tastatur erreichbar und auslösbar (role=button, tabindex=0, Enter/Space) — nicht nur per Maus."""
    page.goto(BASE + "/browser-story")
    expect(page.get_by_test_id("story-stepper").first).to_be_enabled()


# ── Screen: browser-versionen · Versions-Historie — historische Spec-Version read-only ansehen  (route /browser-versionen) ──
def test_browser_versionen__browser_versionen_select_present(page: Page):
    """[browser-versionen] Das Versions-Dropdown ist vorhanden (disabled, wenn keine Historie)."""
    page.goto(BASE + "/browser-versionen")
    expect(page.get_by_test_id("ver-select").first).to_be_visible()


def test_browser_versionen__browser_versionen_readonly_marker(page: Page):
    """[browser-versionen] Eine gewählte historische Version ist als read-only gekennzeichnet."""
    page.goto(BASE + "/browser-versionen")
    expect(page.get_by_test_id("version-readonly").first).to_be_visible()


def test_browser_versionen__browser_versionen_no_snapshot_hint(page: Page):
    """[browser-versionen] Eine Version ohne Shell-Snapshot zeigt einen Hinweis statt eines iframes. ENTSCHIEDEN (ADR-002 AS-3): read-only-Kennzeichnung nur im Detail-Panel, kein iframe-Banner."""
    page.goto(BASE + "/browser-versionen")
    expect(page.get_by_test_id("version-no-snapshot").first).to_be_visible()


# ── Screen: browser-cross-repo · Cross-Repo-Modus — Klickdummies mehrerer Repos in einer Liste  (route /browser-cross-repo) ──
def test_browser_cross_repo__browser_cross_repo_optgroup_per_repo(page: Page):
    """[browser-cross-repo] Die Auswahlliste gruppiert Einträge nach `<org>/<repo>` (optgroup) statt sie flach zu mischen."""
    page.goto(BASE + "/browser-cross-repo")
    expect(page.get_by_test_id("kd-optgroup").first).to_be_visible()


def test_browser_cross_repo__browser_cross_repo_repo_in_detail(page: Page):
    """[browser-cross-repo] Das Detail-Panel zeigt bei Cross-Repo-Einträgen zusätzlich das Herkunfts-Repo."""
    page.goto(BASE + "/browser-cross-repo")
    expect(page.get_by_test_id("kd-repo").first).to_be_visible()


def test_browser_cross_repo__browser_cross_repo_notice_instead_of_frame(page: Page):
    """[browser-cross-repo] Statt eines toten iframes (shell_path ist repo-relativ und hier nicht auflösbar) erscheint ein Hinweis-Panel."""
    page.goto(BASE + "/browser-cross-repo")
    expect(page.get_by_test_id("cross-repo-notice").first).to_be_visible()


def test_browser_cross_repo__browser_cross_repo_github_shell_link(page: Page):
    """[browser-cross-repo] Der Hinweis verlinkt die Shell im Herkunfts-Repo auf GitHub (github_shell_url aus registry.py)."""
    page.goto(BASE + "/browser-cross-repo")
    expect(page.get_by_test_id("link-github-shell").first).to_be_visible()


def test_browser_cross_repo__browser_cross_repo_github_spec_link(page: Page):
    """[browser-cross-repo] Der Hinweis verlinkt zusätzlich die Spec im Herkunfts-Repo (github_spec_url)."""
    page.goto(BASE + "/browser-cross-repo")
    expect(page.get_by_test_id("link-github-spec").first).to_be_visible()

"""Smoke tests for iil-klickdummy package — every public surface importable + callable."""
from __future__ import annotations

import json
from importlib.resources import files


def test_package_version():
    import iil_klickdummy
    # Major bleibt 1; Minor wandert v1.0 → v1.1 → v1.2 …
    assert iil_klickdummy.__version__.startswith(("1.", "0.0.0+unknown"))


def test_all_modules_present():
    import iil_klickdummy
    for mod in ("check_i1", "check_i2", "check_i3", "check_i4",
                "extract_requirements", "gen_e2e", "inventory", "install_snippets"):
        assert hasattr(iil_klickdummy, mod), f"missing module: {mod}"


def test_all_main_cli_endpoints():
    import iil_klickdummy
    for mod_name in ("check_i1", "check_i2", "check_i3", "check_i4",
                     "extract_requirements", "gen_e2e", "inventory", "install_snippets"):
        mod = getattr(iil_klickdummy, mod_name)
        assert callable(getattr(mod, "main_cli", None)), f"{mod_name}.main_cli missing"


def test_schemas_resource():
    names = sorted(p.name for p in files("iil_klickdummy.schemas").iterdir())
    assert {"screens-spec.schema.json", "module-manifest.schema.json",
            "feedback-payload.schema.json"}.issubset(set(names))


def test_screens_spec_schema_strict_mode():
    schema = json.loads(files("iil_klickdummy.schemas").joinpath("screens-spec.schema.json").read_text())
    assert schema["properties"]["class"]["enum"] == ["mock", "stub-demo", "story", "spec-demo"]


def test_check_i2_strict_mode():
    from iil_klickdummy import check_i2
    assert check_i2.LEGACY == {}, "Strict-Mode: LEGACY must be empty per ADR-211 Rev 12/13"
    assert check_i2.ALLOWED == {"mock", "stub-demo", "story", "spec-demo"}


def test_snippets_resource():
    snippets = files("iil_klickdummy") / "snippets"
    names = []
    for d in snippets.iterdir():
        for f in d.iterdir():
            names.append(f.name)
    assert "widget.js" in names
    assert "klickdummy-feedback.md" in names
    assert "inject-widget.html" in names
    assert "screens-spec-template.yaml" in names


def test_widget_js_v05_features():
    """Widget v0.5 must have all v0.2-v0.4 features + GitHub-Direct-API."""
    js = (files("iil_klickdummy") / "snippets" / "feedback-widget" / "widget.js").read_text()
    # v0.2 features
    assert "populateRelated" in js
    assert "fb-rel-grid" in js
    # v0.3 features
    assert "domSnapshot" in js
    assert "FB_FILE_MAX_BYTES" in js
    assert "actionsInCurrentScreen" in js
    assert "fb-act-grid" in js
    # v0.4 features
    assert "feedback_scope" in js
    assert "fb-scope" in js
    assert "KLICKDUMMY_VERFAHREN_HOOK" in js
    # v0.5 (Rev 13 pivot B): GitHub-Direkt-API
    assert "submitGithub" in js
    assert "api.github.com" in js
    assert "klickdummy_github_token" in js
    # v0.5: Plugin-Hooks
    assert "KLICKDUMMY_CATEGORIES" in js
    assert "KLICKDUMMY_PERSONA_HOOK" in js


def test_inventory_runs_clean_on_nonexistent_base():
    from iil_klickdummy import inventory
    assert inventory.main(["--base", "/nonexistent/path"]) == 0


# --- v1.1 ------------------------------------------------------------------

def test_v11_registry_module_present():
    from iil_klickdummy import registry
    assert hasattr(registry, "discover_klickdummies")
    assert hasattr(registry, "discover_versions")
    assert hasattr(registry, "render_browser_html")
    assert hasattr(registry, "main_cli")


def test_v11_browser_template_present():
    tmpl = files("iil_klickdummy.snippets.browser").joinpath("browser.html.tmpl").read_text()
    assert "__KLICKDUMMIES_JSON__" in tmpl
    assert "__REPO_LABEL__" in tmpl


def test_v11_registry_discover_empty_repo(tmp_path):
    from iil_klickdummy import registry
    # leeres Verzeichnis → 0 Klickdummies
    result = registry.discover_klickdummies(tmp_path)
    assert result == []


def test_v11_registry_render_browser_html(tmp_path):
    from iil_klickdummy import registry
    fake = [registry.KlickdummyMeta(
        name="demo", path="klickdummy/demo/screens-spec.yaml",
        shell_path="klickdummy/demo/shell.html",
        spec_id="repo:klickdummy-spec-demo", spec_version="0.1",
        klickdummy_class="mock", title="Demo",
        adr_local="repo:ADR-100", sister_of=[],
    )]
    out = tmp_path / "browser.html"
    registry.render_browser_html(fake, out, repo_label="test-repo")
    html = out.read_text(encoding="utf-8")
    assert "test-repo" in html
    assert "Demo" in html
    assert "repo:klickdummy-spec-demo" in html
    assert "__KLICKDUMMIES_JSON__" not in html  # Template-Marker ersetzt


def test_version_consistency():
    """__version__ ist Single-Source via importlib.metadata — kein Mismatch zu pyproject."""
    import iil_klickdummy
    from importlib.metadata import version as pkg_version
    # Wenn als installiertes Paket: muss übereinstimmen.
    # Wenn als Source-Checkout ohne install: __version__ = '0.0.0+unknown'.
    if iil_klickdummy.__version__ != "0.0.0+unknown":
        assert iil_klickdummy.__version__ == pkg_version("iil-klickdummy"), (
            f"Mismatch: __init__={iil_klickdummy.__version__} vs "
            f"metadata={pkg_version('iil-klickdummy')}"
        )


# --- v1.2 ------------------------------------------------------------------

def test_v12_sync_module_present():
    from iil_klickdummy import sync_to_orchestrator
    assert hasattr(sync_to_orchestrator, "sync_repo")
    assert hasattr(sync_to_orchestrator, "klickdummy_entry")
    assert hasattr(sync_to_orchestrator, "main_cli")


def test_v12_sync_entry_schema(tmp_path):
    """klickdummy_entry produziert valides Memory-Entry-Dict."""
    from iil_klickdummy import sync_to_orchestrator as s, registry
    fake = registry.KlickdummyMeta(
        name="demo", path="klickdummy/demo/screens-spec.yaml",
        shell_path="klickdummy/demo/shell.html",
        spec_id="repo:klickdummy-spec-demo", spec_version="0.1",
        klickdummy_class="mock", title="Demo",
        adr_local="repo:ADR-100", sister_of=["other:ADR-099"],
    )
    entry = s.klickdummy_entry(fake, org="iilgmbh", repo="test-repo",
                                repo_root=tmp_path)
    assert entry["entry_key"] == "klickdummy:iilgmbh:test-repo:demo"
    assert entry["entry_type"] == "repo_context"
    assert entry["title"].startswith("test-repo:demo")
    assert "klickdummy" in entry["tags"]
    assert "klickdummy:class:mock" in entry["tags"]
    assert "klickdummy:org:iilgmbh" in entry["tags"]
    assert "gov-data" not in entry["tags"]   # iilgmbh ist nicht-gov


def test_v12_sync_gov_tag(tmp_path):
    """Gov-Orgs (ttz-lif, meiki-lra) bekommen 'gov-data' tag."""
    from iil_klickdummy import sync_to_orchestrator as s, registry
    fake = registry.KlickdummyMeta(
        name="x", path="x/spec.yaml", shell_path=None,
        spec_id="x:spec", spec_version="0.1", klickdummy_class="mock",
        title="X", adr_local=None,
    )
    entry = s.klickdummy_entry(fake, org="ttz-lif", repo="ttz-hub", repo_root=tmp_path)
    assert "gov-data" in entry["tags"]


def test_v12_sync_empty_repo_no_entries(tmp_path):
    from iil_klickdummy import sync_to_orchestrator as s
    entries = s.sync_repo(tmp_path)
    assert entries == []


# --- v1.3 ------------------------------------------------------------------

def test_v13_discover_cross_repo_present():
    from iil_klickdummy import registry
    assert hasattr(registry, "discover_cross_repo")
    assert hasattr(registry, "render_cross_repo_browser_html")


def test_v13_cross_repo_empty(tmp_path):
    from iil_klickdummy import registry
    # nonexistent repos → leere Liste
    triples = registry.discover_cross_repo(tmp_path, ["does-not-exist"])
    assert triples == []


def test_v13_cross_repo_render(tmp_path):
    from iil_klickdummy import registry
    fake = registry.KlickdummyMeta(
        name="x", path="klickdummy/x/screens-spec.yaml",
        shell_path="klickdummy/x/shell.html",
        spec_id="iilgmbh:klickdummy-spec-x", spec_version="0.1",
        klickdummy_class="mock", title="X",
        adr_local="iilgmbh:ADR-100", sister_of=[],
    )
    triples = [("iilgmbh", "test-repo", fake)]
    out = tmp_path / "cross.html"
    registry.render_cross_repo_browser_html(triples, out, base_label="test")
    html = out.read_text(encoding="utf-8")
    assert "cross-repo" in html
    assert "iilgmbh" in html
    assert "github.com/iilgmbh/test-repo" in html   # Cross-Repo-GitHub-Links


def test_v13_version_bumped():
    """Smoke-Test, dass v1.3.x installiert."""
    import iil_klickdummy
    assert iil_klickdummy.__version__.startswith(("1.", "0.0.0+unknown"))


# --- v1.4 ------------------------------------------------------------------

def test_v14_manage_module_present():
    from iil_klickdummy import manage
    assert hasattr(manage, "cmd_list")
    assert hasattr(manage, "cmd_status")
    assert hasattr(manage, "cmd_topics")
    assert hasattr(manage, "cmd_versions")
    assert hasattr(manage, "cmd_diff")
    assert hasattr(manage, "main_cli")


def test_v14_topic_reader(tmp_path):
    from iil_klickdummy import manage
    p = tmp_path / "spec.yaml"
    p.write_text("spec_id: x\nspec_version: '0.1'\nclass: mock\nmeta:\n  topic: fristen\nscreens:\n  - {id: x, title: X, parity_acceptance: []}\n")
    assert manage._spec_topic(p) == "fristen"


def test_v14_topic_missing(tmp_path):
    from iil_klickdummy import manage
    p = tmp_path / "spec.yaml"
    p.write_text("spec_id: x\nspec_version: '0.1'\nclass: mock\nscreens: []\n")
    assert manage._spec_topic(p) is None


# --- v1.7: Spec-Layer (X-Ray) Panel ----------------------------------------

def test_v17_trace_strip_declared_fields():
    """Deklarierte Spec-Felder erscheinen als gelabelte Panel-Zeilen mit echtem Inhalt."""
    from iil_klickdummy import lineage
    screen = {
        "id": "akte", "title": "Akte",
        "use_cases": ["vergabe-pruefen", "los-verwalten"],
        "konsumiert_entities": [{"name": "Vergabe"}, {"name": "Los"}],
        "datafields": [{"name": "az", "type": "string"}],
        "off_ramp_status": "parity-staging",
        "validierungsfrage": "Erkennt der Prüfer den Status?",
        "parity_acceptance": [
            {"id": "akte.title", "check": "Titel sichtbar",
             "assert": {"action": "visible", "selector": "[data-testid=title]"}},
        ],
    }
    out = lineage.build_trace_strip(screen, "stub-demo", "root", {})
    assert 'class="tr-row"' in out                  # Panel-Zeilen statt Chips
    assert "vergabe-pruefen" in out and "los-verwalten" in out  # echte UC-Namen (in <details>)
    assert "Vergabe, Los" in out                    # echte Entity-Namen
    assert "az:string" in out                       # Datenfeld mit Typ
    assert "parity-staging" in out                  # off-ramp im Status
    assert "Erkennt der Prüfer den Status?" in out  # Validierungsfrage-Text
    assert "1/1 ausführbar" in out


def test_v17_trace_strip_missing_fields_evidence_discipline():
    """Fehlt ein Feld → 'nicht deklariert' + (mit repo/kd/sid) anlegen-Button."""
    from iil_klickdummy import lineage
    out = lineage.build_trace_strip({"id": "leer", "title": "Leer"},
                                    "mock", "default", {})
    assert "tr-missing" in out
    assert "nicht deklariert" in out          # UC-Zeile
    assert "off-ramp fehlt" in out
    assert "keine parity_acceptance-Checks" in out


def test_v17_trace_strip_uc_create_button():
    """Fehlende UC + repo/kd/sid → vorausgefüllter GitHub-Issue-Link (Co-Creation)."""
    from iil_klickdummy import lineage
    out = lineage.build_trace_strip(
        {"id": "cockpit", "title": "Cockpit"}, "mock", "default", {},
        repo="meiki-hub", kd_name="buergerportal", sid="cockpit",
    )
    assert "tr-act" in out
    assert "issues/new" in out
    # kind=use-case → GitHub Issue Form (uc-klickdummy.yml), required-Felder, uc-draft-Label
    assert "template=uc-klickdummy.yml" in out
    assert "uc-draft" in out


def test_uc_button_inflight_markers():
    """UC-anlegen-Button trägt data-uc-key (Issue #25); Page-Level-Script übernimmt Init."""
    from iil_klickdummy import lineage
    out = lineage.build_trace_strip(
        {"id": "cockpit", "title": "Cockpit"}, "mock", "default", {},
        repo="meiki-hub", kd_name="buergerportal", sid="cockpit",
    )
    assert "kd-uc-inflight:meiki-hub:buergerportal:cockpit:use-case" in out
    assert 'data-uc-key=' in out             # Key auf dem Link, kein inline-JS


def test_v17_trace_strip_coverage_matches_gen_e2e():
    """Coverage-Klassifikation nutzt dieselbe SoR wie gen_e2e (executable vs prose vs fragil)."""
    from iil_klickdummy import lineage
    screen = {
        "id": "s", "title": "S",
        "parity_acceptance": [
            {"id": "s.ok", "check": "stabil",
             "assert": {"action": "visible", "selector": "[data-testid=x]"}},
            {"id": "s.fragile", "check": "fragil",
             "assert": {"action": "visible", "selector": ".css-klasse"}},
            {"id": "s.prosa", "check": "nur Prosa, kein assert"},
        ],
    }
    n_exec, n_prose, prose_ids, fragile_ids = lineage._screen_coverage(screen)
    assert n_exec == 2 and n_prose == 1
    assert prose_ids == ["s.prosa"]
    assert fragile_ids == ["s.fragile"]
    out = lineage.build_trace_strip(screen, "spec-demo", "default", {})
    assert "2/3 ausführbar" in out
    assert "prose-only:" in out and "s.prosa" in out
    assert "fragil:" in out and "s.fragile" in out


def test_v17_trace_strip_renders_into_screen_section(tmp_path):
    """Render-Pfad bettet je echtem Screen genau einen Trace-Strip + globalen Toggle ein."""
    import yaml
    from importlib.resources import files
    from iil_klickdummy import lineage
    spec = yaml.safe_load(
        files("iil_klickdummy.snippets.spec-templates")
        .joinpath("screens-spec-template.yaml").read_text())
    record = {"data": spec, "kd": "x", "repo": "iil-klickdummy",
              "path": tmp_path / "screens-spec.yaml"}
    out_html = lineage.generate_render_fallback(record, tmp_path).read_text()
    n_screens = len([s for s in spec.get("screens", []) if s.get("id")])
    assert out_html.count('class="trace-strip"') == n_screens
    assert 'id="spec-toggle"' in out_html
    assert "body.spec-view" in out_html


# --- v1.7.1: Feedback-Widget PAT-Modal (ersetzt window.prompt) --------------

def test_v171_widget_pat_modal_replaces_prompt():
    """Token-Abfrage läuft über gestyltes Modal, nicht über window.prompt()."""
    js = (files("iil_klickdummy") / "snippets" / "feedback-widget" / "widget.js").read_text()
    assert "injectPatModal" in js
    assert "function promptToken" in js
    assert "fb-pat-overlay" in js
    assert "await promptToken()" in js          # Modal ist im Submit-Pfad verdrahtet
    # kein nativer Token-Prompt-Aufruf mehr — Erwähnung nur in Kommentarzeilen erlaubt
    prompt_lines = [ln for ln in js.splitlines() if "window.prompt(" in ln]
    assert all(ln.lstrip().startswith("//") for ln in prompt_lines), prompt_lines


# --- v1.8: discovery_push (Stage 1.5 PoC, platform:ADR-215) -----------------

def test_v18_discovery_push_module_present():
    import iil_klickdummy
    assert hasattr(iil_klickdummy, "discovery_push")
    from iil_klickdummy import discovery_push
    assert callable(getattr(discovery_push, "main", None))


# --- v1.11: klickdummy-from-django (Brownfield-Reverse-Onboarding) ----------

def test_v111_from_django_parses_urls_and_models(tmp_path):
    """URLConf → Screens/Aktionen, models.py → Entity-Katalog (statisch, kein Django)."""
    from iil_klickdummy import from_django
    app = tmp_path / "outlines"
    app.mkdir()
    (app / "urls.py").write_text(
        'app_name = "outlines"\n'
        'urlpatterns = [\n'
        '  path("", views.OutlineListView.as_view(), name="list"),\n'
        '  path("<uuid:pk>/", views.OutlineDetailView.as_view(), name="detail"),\n'
        '  path("<uuid:pk>/delete/", views.OutlineDeleteView.as_view(), name="delete"),\n'
        ']\n', encoding="utf-8")
    (app / "models.py").write_text(
        "class Outline(models.Model):\n"
        "    title = models.CharField(max_length=200)\n"
        "    body = models.TextField()\n"
        "    owner = models.ForeignKey('auth.User', on_delete=models.CASCADE)\n",
        encoding="utf-8")
    name, entries = from_django.parse_urls(app)
    assert name == "outlines"
    pages = [e["name"] for e in entries if not e["action"]]
    actions = [e["name"] for e in entries if e["action"]]
    assert "list" in pages and "detail" in pages
    assert "delete" in actions          # DeleteView/verb → Aktion, kein Screen
    models = from_django.parse_models(app)
    assert models[0]["name"] == "Outline"
    assert ("title", "string") in models[0]["fields"]
    assert ("owner", "ref") in models[0]["fields"]


def test_v111_from_django_builds_spec_demo_skeleton(tmp_path):
    """Skelett ist class: spec-demo (Brownfield), enthält Screens + Entity-Katalog."""
    from iil_klickdummy import from_django
    entries = [
        {"name": "list", "route": "/", "view": "XListView", "action": False},
        {"name": "delete", "route": "/x/delete/", "view": "XDeleteView", "action": True},
    ]
    models = [{"name": "Outline", "fields": [("title", "string")]}]
    spec = from_django.build_spec("outlines", entries, models, "writing-hub")
    assert "spec_id: writing-hub:klickdummy-spec-outlines" in spec
    assert "class: spec-demo" in spec
    assert "conforms_to: platform:ADR-211" in spec
    assert "- id: list" in spec                 # Page → Screen
    assert "delete" not in spec.split("screens:")[1]  # Aktion NICHT als Screen
    assert "Outline(title:string)" in spec      # Entity-Katalog-Kommentar

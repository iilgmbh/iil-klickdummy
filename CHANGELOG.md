# Changelog

Alle nennenswerten Änderungen an `iil-klickdummy`. Format lose nach
[Keep a Changelog](https://keepachangelog.com/); Versionierung SemVer.

## [Unreleased]

### Fixed — UC-Issue-Form-Prefill war verloren gegangen

- `_gh_issue_url` (kind=use-case) berechnete `anker`/`daten`, hängte sie aber
  nie an die Form-URL — die Felder `anker`/`daten`/`persona` des
  `uc-klickdummy.yml`-Forms (Label: „aus Spec vorbefüllt") blieben leer.
  Jetzt als Query-Params prefillt. Gefunden über ruff F841 (unused variable);
  der bestehende Smoke-Test prüfte nur Marker-Präsenz (Memory
  `smoke-test-marker-presence-gap`) — jetzt Param-Name + Wert.

### Changed — Lint-Null-Linie

- ruff 29 → 0: F541/F401/E401 auto-fixt; 3 echte tote Variablen entfernt
  (`title` in render_lineage, `threshold` in manage, `when` in
  sync_to_orchestrator — je verifiziert, dass kein Verhalten dranhängt).
  Golden-HTML-Diff doppelt (Default + `--base-url /kdtest/`): 20/87 Dateien
  geändert, alle Änderungen vollständig durch die neuen Prefill-Params erklärt.

## [1.26.0] — 2026-06-12

### Added — Org-Mapping + App-Namen aus platform-Registry-SSoT (PR #63)

- `detect_org` und `app_name_map` lesen jetzt `platform/registry/canonical.yaml`
  (`meta.repo_owner` / `owner_prefix_rules` / `app_display_names`, platform#554)
  statt hartkodierter Heuristik. Die Code-Heuristik bleibt als Fallback für
  Installationen ohne platform-Checkout (PyPI).
- Vollständigkeits-Gate: Registry gilt nur mit `owner_prefix_rules` als
  nutzbar — platform-Stände mit bloßem `repo_owner` (vor platform#554) fallen
  sauber auf die Heuristik zurück statt meiki-/ttz-Repos falsch zu mappen.
- Netz: golden-HTML-Diff doppelt × beide Pfade (Fallback ohne Felder /
  Registry nach platform#554-Merge) — byte-identisch bis `generated_at`.
  8 neue Tests in `test_org_registry.py` (139 gesamt).

## [1.25.0] — 2026-06-12

### Changed — KONZ-003 Empf-1 komplett: lineage.py-Monolith zerlegt (PR #59/#60/#61)

Reiner Struktur-Refactor, **keine funktionale Änderung** — Output via
golden-HTML-Diff byte-identisch verifiziert (je doppelt: Default-Argumente
und `--repos-root`+`--base-url`-Nicht-Default).

- **PR #59 (Empf-1b/1):** 54 Funktionen + 9 Konstanten aus `lineage.py` in
  6 Module: `genesor/{scan,synth,mermaid,validate,publish,ucs}.py`.
  Inkl. Hotfix: `ROOT`-Pfadtiefe + `_cfg`-Importbindung (`set_cfg` rebindet
  → Module nutzen `get_cfg()`).
- **PR #60 (Empf-1b/2):** 19 Render-Definitionen in 5 Module:
  `genesor/render_{common,fallback,lineage,genesor,uc}.py` —
  `lineage.py` ist jetzt dünne CLI (6432 → 590 Zeilen).
- **PR #61 (Empf-1c):** `build_genesor_html` (1356 Z.) → 203-Z.-Orchestrator
  + 6 Sub-Renderer (`_render_kd_detail`, `_render_table_body`,
  `_render_acceptance_matrix`, `_render_skin_options`, `_org_chip`,
  `_role_chip`); literale Template-Teile als Konstanten
  `_GENESOR_HEAD`/`_GENESOR_TAIL`.
- Back-compat: alle bisherigen `from iil_klickdummy.lineage import X`
  funktionieren weiter (Re-Export-Block).

> Hinweis: v1.24.0 wurde nie getaggt/publiziert — die dortigen Fixes sind
> in diesem Release enthalten (erstes PyPI-Release nach 1.23.0).

## [1.24.0] — 2026-06-12

### Fixed — Analyse-Reste (Follow-up zur Codebase-Analyse, PR #57)

- **I2:** widersprüchliche Doppel-Deklaration (`class` ≠ `klickdummy_class`) ist
  jetzt FAIL statt stillem First-Key-Wins („genau EIN Pattern", ADR-211 I2).
- **inventory:** `--strict` bricht nicht mehr nach dem ersten Repo ab (Voll-Scan,
  Exit-Code am Ende); >10 Treffer zeigen „… und N weitere"; ohne `--strict` jetzt
  Report mit Exit 0 (Gate-Verhalten nur mit Flag — vorher war es für den
  Exit-Code wirkungslos).
- **discovery_push:** `off_ramp_status` aggregiert per-Screen-Status, wenn
  `status_overall` fehlt (uniform → Wert, gemischt → `transition`); vorher
  pauschal `static` — KDs mit removed-Screens erschienen im pgvector-Index als
  unangetastet.
- **lineage.py:** un-escapte `\s`-Sequenzen im Template-JS gedoppelt —
  SyntaxWarning beim Import beseitigt; emittiertes JS byte-identisch.

### Added — Widget-UX-Paket + Cross-Repo-Stories

- **widget.js:** GitHub-Submit-Fehler fragt per `confirm()` nach, statt still
  Download auszulösen; leere Textarea bekommt sichtbares Invalid-Feedback
  (`fb-invalid` + `aria-invalid` + Fokus, Reset bei Eingabe); FAB mit
  `aria-expanded`/`aria-controls`, Panel als `role=dialog`; Token-Validierung
  prüft Mindestlänge statt nur Präfix. Playwright-live verifiziert.
- **Browser:** Cross-Repo-Modus übergibt jetzt Stories
  (`discover_cross_repo_stories()` mit globalem `kd_index`-Remap) — vorher kam
  der Story-Walk dort nie an.
- 11 neue Tests (`tests/test_analyse_reste.py`); Suite 131 grün.

**Bewusst offen:** lineage-Modul-Split (KONZ-003, eigener Strang) und
orgs.yaml-Externalisierung von `detect_org`/`app_name_map` (platform-Entscheid).

## [1.23.0] — 2026-06-12

### Fixed — Gate-Integrität I3/I4 + UX-Sicherheit (Codebase-Analyse Items 1–2)

- **I3 False-Pass:** `check_i3` defaultete fehlendes `off_ramp_status` still auf
  `static` — ein Screen ohne das Schema-Pflichtfeld passierte das Gate. Jetzt FAIL
  je Screen.
- **I4 CWD-Abhängigkeit:** Die lokale ADR-Whitelist (`docs/adr/`) war CWD-relativ;
  Aufruf außerhalb des Repo-Roots ergab False-Fail/False-Pass. Jetzt via
  `find_adr_dir()` vom Scan-Root abgeleitet (`<root>/docs/adr`, `<root>/adr`,
  Eltern-Verzeichnisse).
- 15 neue Tests nageln die Pass/Fail-Semantik von I1/I3/I4 fest (vorher nur
  Import-Smoke).
- `<meta name="viewport">` in allen 8 generierten HTML-Heads (Output war mobil
  unbenutzbar); HTML-Escaping (`_esc`) für Spec-Werte im Akte-Modal-`innerHTML`;
  `URL.revokeObjectURL` nach Widget-Download.

### Added — extract-requirements `--dry-run` + Browser-Versions-Switcher (Items 3–4)

- `klickdummy-extract-requirements --dry-run`: zeigt alle Schreib-/Löschaktionen
  ohne auszuführen. Stale UC-Dateien werden nur noch mit sichtbarer ⚠-Warnliste
  gelöscht (vorher stilles `unlink` — handeditierte UCs verschwanden kommentarlos)
  und nur, wenn sie nicht mehr zum Screen-Set gehören.
- **Versions-Switcher funktionsfähig:** `#ver-select` im Browser war eine
  UI-Attrappe ohne Handler; `discover_versions()` wurde nie aufgerufen. Jetzt:
  `render_browser_html(repo_root=...)` bettet die Git-Historie je KD ein,
  `collect_versions_with_snapshots()` extrahiert frühere `shell.html`-Stände per
  `git show` nach `klickdummy-versions/<kd>/<version>/`; historische Versionen
  laden read-only (ohne `?feedback=on`), Detail-Card zeigt Version/Datum/SHA.

### Changed — A11y + Responsive im Render-Fallback (Item 5)

- Tabs/Sub-Tabs mit `role=tablist/tab/tabpanel` + `aria-selected`-Sync; Sidebar
  mit `aria-current`; Modal als `role=dialog` mit Fokus-Management (Fokus auf
  Schließen-Button, Rückgabe beim Schließen, leichter Tab-Trap); Spec-Toggle mit
  `aria-pressed`.
- Pfeiltasten-Navigation (←/→ Tabs, ↑/↓ Sidebar; persona-gefilterte Buttons
  übersprungen) + `:focus-visible`-Outline; Scroll-Reset bei Screen-Wechsel.
- `@media (max-width: 768px)`: Sidebar-Grid stapelt, kompaktere Paddings,
  Feedback-Widget passt sich der Viewport-Breite an.
- Live verifiziert per Playwright (ARIA-Sync, Pfeiltasten, Modal-Focus/Escape,
  Versions-Switcher-Roundtrip); 120 Tests grün.

## [1.22.2] — 2026-06-04

### Changed — Ehrlicher Header: Drift-Check ≠ Parität

- Der generierte Suite-Header stellt jetzt explizit klar, dass `make klickdummy-parity-drift`
  **nur Spec↔Datei-Drift** prüft (re-gen + diff) und die Assertions **nicht ausführt** — also
  **keine Parität belegt**. Echte Parität entsteht erst beim Lauf mit pytest + playwright gegen
  einen laufenden `SPEC_RENDERER_BASE_URL`; „gegen Renderer #2" setzt eine echte, erreichbare
  App-Route voraus.
- Hintergrund (empirisch, 2026-06-04): plattformweit lief noch nie eine Suite gegen einen
  Renderer #2 — alle Specs sind `mock`/`spec-demo`, kein Repo in Off-Ramp-Transition. Der
  irreführende Name `parity-drift` signalisierte „Parität geprüft", wo nur Drift geprüft wurde.
- Generierter Output bleibt deterministisch; Adopter sehen beim nächsten `parity-drift`-Lauf
  einmalig Drift → re-generieren.

## [1.22.1] — 2026-06-04

### Fixed — `gen_e2e` emittiert `pytest.importorskip("playwright")` (T-01)

- Die generierte Parity-Suite importierte `playwright` hart auf Modulebene. Bei
  Adoptern **ohne** `testpaths`-Isolation sammelt pytest die Suite mit und bricht
  beim Import, wenn `playwright` nicht installiert ist (Collection-Error statt Skip).
  Der erste Adopter (`risk-hub` #146) entging dem nur per `testpaths=["src"]`-Zufall.
- Fix: Der Generator setzt nun `pytest.importorskip("playwright")` **vor** den
  `from playwright.sync_api import …` (mit `# noqa: E402`, damit `ruff check` der
  Adopter grün bleibt). Suiten ohne installiertes playwright werden sauber
  übersprungen statt zu brechen. Output bleibt `ruff format`- und `ruff check`-clean.
- Regressionstests: Präsenz + Reihenfolge der `importorskip`-Zeile,
  `ruff check --select E402` auf dem generierten Output.

## [1.22.0] — 2026-06-03

### Added — Autoren-Beispielzeilen für Entity-Tabellen (`local_entities.<e>.examples`)

- Sub-Tab-Tabellen (`konsumiert_entities` → `local_entities`) konnten bisher nur
  **synthetische, domänen-blinde** Werte zeigen (`_synth_value`-Heuristik per
  Feldname → z.B. CAS/WGK/Lagerklasse wurden zu „Wert-A"). Für „am Beispiel
  schärfen" (ADR-211 Co-Creation) fehlten domänen-echte Werte.
- Neu: `local_entities.<entity>.examples: [[v1, v2, …], …]` — Liste von Zeilen,
  an `fields`-Reihenfolge ausgerichtet. Hat **Vorrang** vor der Synth-Heuristik;
  zu kurze Zeilen werden per Synth aufgefüllt, zu lange auf 6 Spalten gekappt.
  Ohne `examples` bleibt das bisherige Synth-Verhalten unverändert (abwärtskompatibel).
- Schema: bereits valide über `additionalProperties: true` am Top-Level — keine
  Schema-Änderung nötig. Erstnutzung: `risk-hub:gefahrstoff-kataster` (UC-004).

## [1.21.2] — 2026-06-03

### Changed — Story-Switcher zeigt Schritt-Label statt Story-Titel

- Bei KDs, die mehrere Story-Schritte teilen, zeigte der Switcher (`#sb-story-switch`)
  den Story-Titel **mehrfach** (redundant). Jetzt `en.step_label` (z.B.
  „5. Template/Gliederung erstellen") → die Schritte sind unterscheidbar.

## [1.21.1] — 2026-06-02

### Fixed — stories-manifest: korrekte relative Tiefe + Shell-Präfix

- v1.21.0 legte das Manifest nach `out_dir` mit Shells `<kd>/index.html` —
  aber `../../` aus `kd/<repo>/klickdummy/<kd>/index.html` zeigt auf
  **`kd/<repo>/`** (zwei Ebenen hoch), nicht `kd/<repo>/klickdummy/`. Folge:
  Banner-Fetch 404 → Story-Walk lud nicht (live verifiziert).
- `build_manifest(repo_root, shell_prefix="")` + 3. CLI-Arg `[shell_prefix]`:
  Manifest gehört nach `kd/<repo>/`, prev/next_shell = `klickdummy/<kd>/index.html`.
  Regen ruft mit `out_dir=kd/<repo>` + `shell_prefix=klickdummy/`.

## [1.21.0] — 2026-06-02

### Added — Stories-Manifest für den Genesor/Vendored-Layout (`klickdummy-stories-manifest`)

- **Lücke geschlossen:** der Genesor-Renderer erzeugt das Story-Banner-JS (fetcht
  `../../stories-manifest.json`), schrieb das Manifest aber **nie** —
  `write_stories_manifest` lag nur im `klickdummy-browser`-Render (registry.py,
  Browser-Layout). Folge: Story-Walk/Banner erschien auf iil.pet (Genesor-Deploy)
  **nicht**, egal wie oft regen lief.
- **`gen_stories_manifest.py` + Console-Script `klickdummy-stories-manifest`**:
  `<repo_root> <out_dir>` → schreibt `stories-manifest.json` mit `kd_to_stories`
  für den **Vendored-Layout** (`kd/<repo>/klickdummy/<kd>/index.html` → `../../` =
  `kd/<repo>/klickdummy/`); prev/next_shell = `<kd>/index.html` (statt `shell_path`).
  Wird vom iil-pet-portal-Regen je Story-Repo aufgerufen.
- 2 Tests. Dogfood ausschreibungs-hub: Bieter-Journey, 5 KDs, 11 Steps.

## [1.20.0] — 2026-06-02

### Added — Flow-Kohärenz-Lint `klickdummy-flow` (UC-Story-Line, KONZ-004 Move 2)

- **`check_flow.py` + Console-Script `klickdummy-flow`**: validiert den
  Screen-Flow-DAG (`screens[].next_screens` / `voraussetzung_screen`) je
  KD-Spec — heute vom Genesor als Lineage-Graph gerendert, aber **unvalidiert**
  (nicht im Schema). Findings:
  - **error**: dangling `next_screens`/`voraussetzung_screen` (Ziel kein Screen
    der Spec) → Exit≠0.
  - **warning**: Vorwärts/Rückwärts-Asymmetrie (next ↔ voraussetzung uneinig),
    Zyklus, **Flow-Schritt ohne `use_cases`** (Stringenz-Lücke der UC-Story-Line).
  - **info**: isolierter Screen, „kein Flow deklariert" (≥2 Screens, 0 Kanten).
- Dogfood ausschreibungs-hub: fand reale Asymmetrie (`lose_auswahl` ↔
  `ausschreibung_detail`) + 14 Flow-Schritte ohne `use_cases`. 5 neue Tests.
- Macht die UC-Story-Line **erzwingbar** (Consumer-CI ruft `klickdummy-flow`),
  ohne neues SoR-Artefakt — Flow bleibt in der Spec. Hintergrund: KONZ-004.

## [1.19.1] — 2026-06-02

### Fixed — Spec-Sicht-Heading spiegelt aktiven Sub-Tab (Feedback-Widget-Bug)

- Sub-Tab-Wechsel aktualisierte `fb-current-subtab` (für Feedback/UC-anlegen),
  aber **nicht** die sichtbare Spec-Sicht-Überschrift (`tr-screen-title`) — die
  blieb screen-statisch (z.B. „nachunternehmer — Nachunternehmer-Auswahl…").
  Jetzt hängt der Sub-Tab-Handler ` › <aktiver-subtab>` an die Heading des
  jeweiligen Screen-`.trace-strip` (nur bei ≥2 Sub-Tabs); Initial-Befüllung je
  Screen. Renderer-weit. Bug-Report via Feedback-Widget 2026-06-02
  (bau-beschaffung/nachunternehmer).

## [1.19.0] — 2026-06-02

### Added — Story-Validierung (Fail-Fast) statt render-zeitigem Silent-Skip (KONZ-004 A3)

- **`schemas/story.schema.json`** (neu): JSON-Schema für `klickdummy/stories/<slug>.yaml`
  (`id`-Pattern `repo:story-<slug>`, `title`+`steps` required, `steps[].kd` required,
  `additionalProperties:false`).
- **`check_stories.py` + Console-Script `klickdummy-stories`**: scannt
  `klickdummy/stories/*.yaml`, validiert gegen das Schema **und** löst `step.kd`
  gegen die KD-Liste auf. Sammelt **alle** Fehler, Exit≠0 — macht den bisherigen
  render-zeitigen stderr-Silent-Skip (`discover_stories`) zu einem harten Build-Gate.
  Kein `stories/`-Verzeichnis → PASS (rückwärtskompatibel).
- Hintergrund + Abwägung (UI-Tool abgelehnt): `docs/konzepte/KONZ-iil-klickdummy-004.md`.

### Fixed — Spec-Sicht: Panel beim Aktivieren in den Viewport scrollen

- `setSpecView(on)` scrollt jetzt beim Einschalten das sichtbare `.trace-strip`
  (Spec-Panel des aktiven Screens) per `scrollIntoView` in den Viewport. Vorher
  togglete es nur `body.spec-view` — das Panel sitzt am Screen-Ende, oft unter
  dem Fold (verifiziert: phase-unterlagen Panel-Top 730 bei Viewport 720,
  `scrollY` blieb 0) → Nutzer sah nach „Spec-Sicht"-Klick scheinbar keine
  Änderung. Renderer-weit (UX-Test-Befund 2026-06-02).

## [1.18.2] — 2026-06-02

### Fixed — Zwei UX-Bugs im KD-Render (Playwright-UX-Test)

- **Persona-Filter war funktionslos (P1):** `applyPersonaFilter()` schrieb auf
  `#fb-current-persona`, dieses Element wurde aber **nie gerendert** → `TypeError`
  in der ersten Zeile → der Tab-Filter-Code dahinter lief nie (Persona-Auswahl
  ohne jede Wirkung; auch der Feedback-Submit las dieselbe tote ID). Fix: hidden
  `#fb-current-persona`-Tracker ergänzt (analog `#fb-current-subtab`) + beide
  Zugriffe null-geguarded. Verifiziert: Persona „bieter" blendet jetzt korrekt
  die nicht-passenden Screens aus.
- **Story-Banner immer sichtbar & leer (P2):** der Inline-Style von
  `#story-banner` enthielt **zwei** `display:`-Deklarationen
  (`display:none;…;display:flex`) → `flex` gewann → leerer „📖 Schritt /"-Balken
  auf jedem Render ohne aktive Story (inkl. live). Fix: verirrtes `display:flex`
  aus dem Inline-Style entfernt; JS schaltet bei aktiver Story auf flex.
- Beide im `RENDER_FALLBACK_TEMPLATE` → galt für **alle** KD-Renders aller Repos.
  2 neue Regressionstests (74 grün); browser-verifiziert (Playwright).

## [1.18.1] — 2026-06-02

### Fixed — Story-Banner-JS leakte als sichtbarer Text im KD-Render

- `RENDER_FALLBACK_TEMPLATE` enthielt `__STORY_BANNER_JS_PLACEHOLDER__`
  **zweimal**: einmal korrekt in `<script id="story-banner-js">` (Body-Ende),
  einmal **roh** direkt nach dem Banner-Div (ohne `<script>`-Wrapper). Da
  `str.replace` alle Vorkommen ersetzt, wurde das JS oben im Body als
  sichtbarer Quelltext gerendert (Bug-Report 2026-06-02). Der nackte
  Platzhalter wurde entfernt — Banner-Div bleibt oben, Script am Body-Ende.
- Regressionstest verschärft: prüft jetzt, dass das Banner-JS genau **einmal**
  und ausschließlich **innerhalb** eines `<script>`-Tags vorkommt (Marker-
  Präsenz allein hätte den Leak nicht gefangen).

## [1.18.0] — 2026-06-02

### Added — Repo-Linse im Genesor einklappbar (mehr Platz für den Inhalt)

- Die Repo-Rail („Linse") im Genesor-Overview lässt sich per ◀-Button
  einklappen — der sichtbare Inhaltsbereich (`main`) wird dadurch voll breit,
  abgeschnittene Tabellenspalten (Replaces, Sunset, Personas) werden sichtbar.
  Eingeklappt erscheint ein `▶ Linse`-Button oben im Inhalt zum Ausklappen.
- Zustand persistiert in `localStorage` (`genesor_rail_collapsed`) — gleiches
  Muster wie der Skin-Switcher. Default: ausgeklappt (Verhalten wie bisher).
- Reine Template-Erweiterung in `lineage.py` (CSS + 2 Buttons + Toggle-IIFE),
  3.10-safe (alle Klammern verdoppelt, kein PEP-701). 72 Tests grün, keine
  neuen ruff-Befunde.

## [1.17.1] — 2026-06-02

### Fixed — Screen-Titel im Topbar dynamisch (Bug #40)

- `showScreen()` setzt jetzt `#screen-title-dynamic`-Span in der H1 auf den
  Namen des aktiven Screens (aus dem Tab-Button). Vorher war die H1 statisch
  (immer KD-Titel) → User sah keinen Hinweis welcher Screen aktiv ist.
  Kleines `font-weight:400`-Inline-Label neben dem KD-Titel; verschwindet
  beim ersten Screen ohne Namens-Match (silent, kein Fehler).

## [1.17.0] — 2026-06-02

### Added — Story-Banner im Render: KD kennt seine Story-Zugehörigkeit (approach b)

- **`write_stories_manifest(output_dir, kds, stories)`** in `registry.py`: erzeugt
  `stories-manifest.json` neben Browser-HTML. Enthält `kd_to_stories`-Map mit
  `step_index`, `step_total`, `prev/next_shell` (repo-root-relativ), Labels.
  `render_browser_html` schreibt Manifest automatisch wenn Stories vorhanden.
- **Story-Banner im Render** (`RENDER_FALLBACK_TEMPLATE` in `lineage.py`): jeder
  generierte KD-Render enthält einen hidden `#story-banner`-Div + Banner-JS.
  Das JS lädt `../../stories-manifest.json` via fetch — bei Erfolg blendet sich
  der Banner ein mit Story-Titel, Schritt-Zähler, ●-Dots, Weiter/Zurück-Links.
  Multi-Story-KD: Story-Switcher rechts im Banner. Silent fail bei `file://`
  oder fehlendem Manifest → Banner bleibt versteckt, kein Fehler.
- `data-kd="{kd_name}"` auf dem Banner-JS-Script-Tag — KD-Name für Manifest-Lookup.
- 2 neue Smoke-Tests; 43 grün; 3.10-safe.

## [1.16.0] — 2026-06-02

### Added — Story-Picker: geführte KD-Touren im Browser (platform:ADR-211 §Story-Navigation)

- **`discover_stories(repo_root, klickdummies)`** in `registry.py`: scannt
  `klickdummy/stories/*.yaml`, löst `step.kd` (Verzeichnisname) gegen die
  KD-Liste auf, gibt Story-Dicts mit `kd_index` zurück. Unbekannte Steps →
  stderr-Warning, kein Abbruch. Kein `stories/`-Verzeichnis → `[]` (rückwärtskompatibel).
- **`render_browser_html` / `render_cross_repo_browser_html`**: neuer optionaler
  `stories`-Parameter; setzt `__STORIES_JSON__`-Placeholder im Template.
- **`browser.html.tmpl` v1.2**: Mode-Toggle `🗂 Frei | 📖 Story-Walk` (nur sichtbar
  wenn ≥1 Story vorhanden), Story-Select-Dropdown, Stepper-Liste mit ✅/●/○-Icons,
  Weiter/Zurück-Buttons, Visited-State via localStorage — rückwärtskompatibel
  (ohne Stories: Toggle versteckt, Verhalten wie v1.1).
- **`snippets/spec-templates/story.yaml.example`**: Vorlage für Consumer-Repos.
- 4 neue Smoke-Tests; 41 grün; 3.10-safe.

## [1.15.1] — 2026-06-01

### Fixed — Sub-Tab-aware UC anlegen + Feedback-Widget (#34)

- **`build_trace_strip` `act()`:** UC-anlegen-Button trägt jetzt `data-uc-subtab-selector`
  → Page-Level-Script liest beim Click den aktiven Sub-Tab-Namen und hängt ihn an den
  localStorage-Key (sub-tab-spezifischer Inflight-State) und den Issue-Titel.
- **Sub-Tab-Switch-Handler:** setzt `fb-current-subtab`-Element (+ Initial-Sync bei Seitenlade).
- **`fbCollect()`** (beide Instanzen — Render-Template + lineage.py-Self-Render):
  `active_subtab: document.getElementById('fb-current-subtab')?.textContent || null`
  im Feedback-Payload.
- **`fb-current-subtab`:** hidden Span nach Widget-Placeholder-Inject im Template + lineage.py.
- 2 neue Smoke-Tests; 37 grün; 3.10-safe.

## [1.15.0] — 2026-06-01

### Added — gen_e2e: parametrisierte Routen + Auth für ausführbare Parity-Suite (#28)

- **`route_example`** (Screen-Feld): konkrete Beispiel-URL mit echten IDs/UUIDs. `klickdummy-gen-e2e` bevorzugt sie vor `route` → kein `<uuid:pk>`-404 mehr gegen Renderer #2 (echte App).
- **Parametrisierte `route` ohne `route_example`** → Check wird `@pytest.mark.skip` mit klarem Grund (statt 404-Rauschen); Manifest weist es als `skip_reason: parametrised_route` aus.
- **`auth`-Block** (Top-Level): `storage_state` / `login_fixture` / `required`. gen_e2e bindet ihn als `autouse`-Fixture ein. `login_required`-Screen ohne `auth` → skip mit Grund `login_required_no_auth`.
- `screen_route()` gibt jetzt `(url, is_parametrised)` zurück. Schema um `route_example`, `login_required`, `auth` erweitert (alle optional, rückwärtskompatibel). 4 neue Tests; 64 grün, 3.10-safe.

## [1.14.0] — 2026-06-01

### Added — Klickdummy-Capture-Gate: strukturiertes Issue-Form statt thin-prefill

- **`_gh_issue_url` kind-Routing (2b, platform:ADR-211 §Co-Creation-Loop):**
  `kind=use-case` routet auf `?template=uc-klickdummy.yml` (GitHub Issue Form mit
  `required`-Feldern — GitHub blockiert leeres Submit) statt thin-prefill. `kind=off-ramp`
  und `kind=parity` behalten den bisherigen Markdown-body-Prefill bis eigene Forms gebaut sind.
- **`snippets/issue-template/uc-klickdummy.yml`** — GitHub Issue Form (YAML): 5 Pflicht-
  felder (Anker, Persona, Ziel, Hauptszenario, Akzeptanz), spec-vorbefüllter Titel (`UC: kd/screen`),
  Labels `uc-draft`+`needs-domain-review`. Labels Route Issue direkt in den Co-Creation-Loop.
- **`snippets/issue-template/klickdummy-feedback.yml`** — ersetzt `.md`: GitHub Issue Form
  mit `Art`-Dropdown (Bug/Feature/Fehlende View/Spec-Korrektur) als Quell-Router; Pflicht-
  felder Art + Anker + Beschreibung.
- **`.github/ISSUE_TEMPLATE/uc-klickdummy.yml`** — repo-eigenes Template (Dogfood).
- Test `test_v17_trace_strip_uc_create_button` auf neues URL-Format aktualisiert.

## [1.13.4] — 2026-06-01

### Added
- Spec-Sicht: Screen-ID + Titel am Kopf jedes Panels (zeigt welcher Tab/Screen aktiv ist).
- Favicon 🌱 in Render- und Genesor-Seiten (behebt 404 für favicon.ico).

## [1.13.3] — 2026-06-01

### Fixed
- Inflight-Reset via Event-Delegation: `querySelector` nach `outerHTML` fand Spans in versteckten `has-tabs`-Sections nicht. Fix: `document.addEventListener('click')` + `closest()` fängt alle Inflight-Klicks zuverlässig ab.

## [1.13.2] — 2026-06-01

### Fixed
- Inflight-Span zurücksetzbar: Klick auf „⏳ UC anlegen in Arbeit" löscht localStorage-Key + Reload → Button wiederhergestellt.
- UC-Liste als `<details>/<summary>` klappbar (statt Freitext).

## [1.13.1] — 2026-06-01

### Fixed
- `spec-sicht`: UC-Button-Inflight-State Hotfix — erster Ansatz (#26) war durch doppelte HTML-Escaping-Stufen kaputt. Neuer Ansatz: `data-uc-key` auf dem Link + sauberes Page-Level-Script (kein `document.currentScript`, kein Inline-JS, echte Emoji-Zeichen).

## [1.13.0] — 2026-06-01

### Fixed
- `spec-sicht`: UC-Button-Zustand „⏳ UC anlegen in Arbeit" nach Klick — State via `localStorage` persistent nach Reload (#26).

### Refactored
- `lineage.py` Globals → `@dataclass GenesorConfig` (PR #23) + Teil-Split in `iil_klickdummy/genesor/` (config, introspect_django, export — PR #24). Vorbereitung für den Render-Kern-Split (#22).

## [1.12.0] — 2026-06-01

### Added — Genesor Repo-Ebenen-Einstieg (Master-Detail + Fassetten-Linse)

- `build_genesor_html` erhält eine **client-seitige Master-Detail-Schiene** in der
  bestehenden `index.html` (KONZ-iil-klickdummy-002): linke Repo-Schiene (alle Repos
  sichtbar, mit KD-Count + Drift-Punkt) + Hash-Routing `#/repo/<repo>` für teilbare
  Deep-Links. Adressiert den Übersichtlichkeits-Verlust bei wachsender KD-Zahl
  (49 KDs / 10 Repos, Long-Tail), ohne eine zweite Datei oder Server-Routing.
- **Fassetten-Linse** (Out-of-the-Box): Schiene umschaltbar nach `repo | org | class
  | role` — Repo ist nur die Default-Linse, nicht die einzige Achse. Schiene wird
  client-seitig aus den Zeilen-`data`-Attributen gebaut (kein N×-Server-Render).
- **Rein additiv & rückwärtskompatibel:** ohne Hash zeigt die Seite unverändert alle
  Zeilen; die neue Gruppen-Dimension UND-verknüpft mit den bestehenden Org-/Drift-/
  Such-Filtern. `render_detail`, Surface-Modal, Sort, Skin-Switcher unberührt.
- Verifiziert per Playwright (Master-Detail-Verengung exakt, Deep-Link beim Frisch-Load,
  Fassetten-Wechsel, Koexistenz, 0 Konsolen-Fehler) + 60 Tests grün.

## [1.11.0] — 2026-06-01

### Added — `klickdummy-from-django`: Brownfield-Reverse-Onboarding

- Neues Modul/CLI `from_django` (`klickdummy-from-django`): leitet aus einer
  **existierenden Django-App** ein `screens-spec.yaml`-**Skelett** ab — URLConf →
  Screens (Pages) + Aktionen (POST-Endpoints getrennt), `models.py` → Entity-
  Katalog mit Feldtypen, `app_name` → `spec_id`. **Statisches Parsing** (`ast` +
  Regex), **keine** Django-Runtime/DB nötig → läuft sicher gegen jeden Source-Tree.
- `class: spec-demo` (realer Code-Pfad existiert) + Kuratier-Kommentare
  (Entity-Katalog, Aktions-Liste, TODO-Marker). Startpunkt für menschliche
  Kuratierung; nächster Schritt `klickdummy-gen-e2e` gegen die echte App
  (Parity-Bridge) → iterieren bis parity-grün = verifizierte Spec-Erfassung.
- Macht Brownfield-Onboarding reproduzierbar (Blaupause „Schritt für Schritt
  alle Repos"). 2 neue Tests; gegen `writing-hub/outlines` gedogfoodt
  (4 Screens, 7 Aktionen, 2 Models).

## [1.10.0] — 2026-06-01

### Changed — Render: Spec-Sicht als Inhalts-Panel + kanonisches Widget

- **Spec-Sicht (X-Ray)** von dünner Chip-Reihe → **gelabeltes Inhalts-Panel** pro
  Screen: echte Werte statt Icon-Chips — Use-Case-Namen, Entitäten + Datenfelder
  (mit Typ), Status (class/role/off-ramp/pipeline), Abnahme (who/when/Frische),
  Coverage-Aufschlüsselung (executable/prose-only/fragil), Validierungsfrage-Text.
- **Co-Creation-Buttons:** fehlende Pflicht-Angaben (UC, off_ramp_status,
  parity_acceptance) bekommen einen `[+ anlegen]`-Button → vorausgefülltes
  GitHub-Issue (`detect_org`-Ziel, kein Hardcode). Schließt die „nicht
  deklariert"-Lücke aktionierbar (ADR-211 Co-Creation).
- **Feedback-Widget:** Render bettet jetzt das **kanonische `widget.js`**
  (GitHub-direct + PAT-Modal) ein statt des alten inline-Download/Clipboard-
  Widgets — via `__FEEDBACK_WIDGET_JS_PLACEHOLDER__`-Inject (analog Skin-Switcher),
  konfiguriert über `window.KLICKDUMMY_*`.
- Tests angepasst/ergänzt (Panel-Format, UC-Button); 58 grün, 3.10-Parse + ruff clean.

## [1.9.0] — 2026-06-01

### Added — discovery_push v1.6-Schema: Producer-Seite der ADR-215-§Amendment-1-Auflagen

Arbeitet die **Producer-seitigen** Härtungs-Auflagen aus `platform:ADR-215`
§Amendment 1 ein (ADR ist `accepted`; diese Auflagen sind verbindlich vor
Produktiv-Aktivierung). Discovery-Entry-Schema `v1.5` → **`v1.6`**, rein additiv:

- **Provenance/Drift-Anker** (REC-1/6): `source_repo`, `source_ref`, `commit_sha`,
  `spec_sha256`, `generated_at` — Registry-Eintrag ist abgeleiteter Index mit
  Rückführung auf den exakten Spec-Stand. `_git_provenance` liest `.git` ohne
  Subprozess (tolerant → null).
- **Upsert-Identität** `registry_key` = org/repo + path_rel + spec_id (REC-2).
- **Ingestion-Guard** (REC-7): nur die vier I2-Klassen sind push-berechtigt;
  andere werden mit Hinweis übersprungen (kein vacuous push).
- **Governance-Gate** `discovery.discoverable` (REC-14): Sichtbarkeit aus der
  Spec, nicht aus technischem Push. **Soft-Migrate** (analog I2 Rev-12): nicht
  deklariert → Default true mit Warnung.
- **Sichtbarkeit** `visibility_scope ∈ {repo,org,allowlist,public-demo}`,
  Default `org` = geringste Exposition (REC-6).
- **Filter/Lifecycle-Felder** `pipeline_status`, `off_ramp_status`, `tombstone`
  (REC-5/16).
- **Versionierter Push-Envelope** `{api_version, registry_schema_version,
  generated_at, entries}` + `X-Registry-Schema-Version`-Header + konfigurierbarer
  `--timeout` (REC-4/10).
- **Signierter Fallback-Snapshot** `--snapshot` mit selbst-verifizierendem
  `sha256` (REC-3, Producer-Hälfte).

**Bewusst NICHT hier** (Orchestrator-/Consumer-Seite, separates Go): TTL/Tombstone-
*Enforcement*, Org-Filter/Visibility auf der *Query*, Audit-*Storage*, Picker-
Snapshot-*Konsum* (meiki-hub), Search-Eval-Suite + Skalentest (bei
`klickdummy-search`). 9 neue Tests; 3.10-Parse verifiziert.

## [1.8.0] — 2026-06-01

### Added — `discovery_push`: Spec → pgvector-Discovery-Push (Stage 1.5 PoC)

- Neues Modul `discovery_push` (`platform:ADR-215`, `status: proposed`):
  sammelt Klickdummy-Discovery-Entries cross-repo (über `registry`) und pusht
  sie an einen Orchestrator-Endpoint (`KLICKDUMMY_DISCOVERY_ENDPOINT`, Bearer
  optional). Nur stdlib (`urllib`), keine neue Dependency. API-Vertrag in
  `docs/api/discovery.md`. **PoC/alpha** — Aktivierung erst nach
  Orchestrator-Schema-Migration.
- **Herkunft:** Substanz aus stale PR #5 (Stand v1.4.x) sauber auf aktuelles
  `main` extrahiert statt rebased — der literale Rebase hätte `gen_e2e` (v1.6
  Keystone) aus `__init__`/`test_smoke` regressiert, weil der Branch aus der
  Vor-`gen_e2e`-Ära stammt. Nur die genuin neuen Dateien übernommen
  (`discovery_push.py`, `test_discovery_push.py`, `docs/api/discovery.md`) +
  `__init__`-Export; `manage.py`/Circular-Import-Fixes waren auf `main` bereits
  eigenständig gelöst.

## [1.7.1] — 2026-06-01

### Fixed — Feedback-Widget: PAT-Eingabe als gestyltes Modal statt `window.prompt()`

- GitHub-Token-Abfrage beim Issue-Submit läuft jetzt über ein eingebettetes,
  promise-basiertes Modal (`injectPatModal` / `promptToken`) mit Erklärtext,
  Token-Format-Validierung und Hinweis auf `localStorage`-only-Speicherung —
  statt des nativen `window.prompt()`. Reine `widget.js`-Snippet-Änderung,
  additiv. (Substanz aus stale PR #6 extrahiert; dort war der Fix unter 71
  Editor-Config-Dateien begraben — PR #6 geschlossen.)

## [1.7.0] — 2026-06-01

### Added — Spec-Layer (X-Ray): per-Screen Trace-Strip

- Globaler Toggle **„Spec-Sicht"** (Header-Button + Taste `s`) blendet pro Screen
  einen kompakten, **spec-abgeleiteten** Chip-Streifen ein: betroffene Use Cases,
  Entities/Datenfelder, `class`/`role` (I2), `off_ramp_status` (I3), Acceptance
  (mit Frische), und **Parity-Coverage** (I1: `n/m` ausführbar, prose-only,
  fragile Selektoren). Toggle AUS = unveränderte Echt-App-Illusion für den
  Stakeholder-Walkthrough; AN = volle Nachvollziehbarkeit für Reviewer.
- **Evidenz-Disziplin in der UI:** fehlt ein Feld, rendert ein gestrichelter
  „nicht deklariert"-Chip mit dem **exakten Spec-Feld zum Ergänzen** (Muster aus
  `akte_next` generalisiert) — nie erfunden.
- Coverage nutzt **dieselbe SoR wie `gen_e2e`** (`render_assertion` /
  `is_fragile_selector`), keine Duplikat-Logik.
- Use-Case-Quelle: `screen.use_cases[]` (neu) > `konzept_ref[]` > `akte_next.uc`.
- **Schema:** `screen.use_cases[]` jetzt explizit in `screens-spec.schema.json`
  dokumentiert (vorher nur via `additionalProperties` toleriert). Schema-Generation
  **1.1** (Baseline 1.0 + `use_cases`); Template deklariert `spec_schema_version: "1.1"`.
- ADR-211-konform (rein additiv, spec-gespeist, I1–I3 unberührt) — kein neuer
  Platform-ADR (vgl. `adr-threshold.md`). Reversibel durch Entfernen des Toggles.

## [1.6.1] — 2026-05-31

### Fixed — `gen_e2e` Output `ruff format`-konform (Adopter-Blocker)

- Generierter Output nutzt jetzt **Double-Quotes** (via `json.dumps` statt
  `repr`/Single-Quotes) und **zwei Leerzeilen** zwischen Top-Level-Funktionen.
  Vorher brach jeder Adopter mit `ruff format --check`-CI — real aufgetreten beim
  ersten Adopter (risk-hub). Determinismus, Spec-SHA256-Header und
  Coverage-/Manifest-Verhalten unverändert; neuer Regressions-Test
  (`ruff format --check` auf generiertem Output, via `importorskip`-Äquivalent).

## [1.6.0] — 2026-05-31

### Added — Executable-Parity-Bridge (Keystone, `platform:ADR-211` Rev-18-Kandidat)

- **`klickdummy-gen-e2e`** (`gen_e2e`-Modul): forward-only, **deterministischer**
  Generator Spec → Playwright/pytest-Parity-Suite. Dieselbe Suite läuft per
  `SPEC_RENDERER_BASE_URL` gegen **Renderer #1 (Klickdummy)** und
  **Renderer #2 (echte App)** — parity-grün gegen #2 = I3-Off-Ramp-Gate. Die
  Tests überleben den Off-Ramp (Kontinuität liegt in Spec + Tests, nicht im
  Wegwerf-Renderer).
- **Schema** (`screens-spec.schema.json`): optionaler ausführbarer
  `parity_acceptance[].assert` (`action ∈ {visible,text,clickable,url,count}`,
  `selector`, `expect`) + `screens[].route` + `spec_schema_version`. Prosa-`check`
  bleibt **Pflicht** ⇒ voll rückwärtskompatibel.
- **Reproduzierbarkeits-Manifest** (`*.manifest.json`): `spec_sha256`,
  `generator_version`, Coverage (`executable`/`skipped`), `skipped_detail`
  (Skip-Debt mit Grund), `fragile_selectors`, `uncovered_note`.
- **Determinismus:** Spec-SHA256 statt Zeitstempel im generierten File → ermöglicht
  Drift-Check `klickdummy-parity-drift` (analog `requirements-drift`, ADR-211 S10).
- Selektor-Fragilitäts-Warnung (kein `data-*`-Anker) im Manifest + CLI.

### Provenance / bewusste Grenzen

- Durch **zwei externe LLM-Review-Runden** gehärtet (R1: 25 RECs zur Richtung;
  R2: 15 RECs zum Amendment-Text), Step-5-getaggt. Ein realer Determinismus-Bug
  (Zeitstempel im generierten File) wurde dabei gefunden und gefixt.
- Tag-Tabellen + ADR-211-Rev-18-Amendment-Entwurf laufen über einen **separaten
  platform-PR** (die Konvention lebt in `achimdehnert/platform`, nicht hier).
- **Nicht abgedeckt (bewusst):** NFR/Security/A11y/Performance/Audit
  (Requirements-Bridge-Asymmetrie); F4 nur „für inventarisierte Routen"
  (Alias-/Preview-Risiko offen, F20); plattform-externer Prod-Guard ungebaut (F11).

## [1.5.0] und früher

Siehe Git-History und `platform:ADR-211` Revisionshistorie (Rev ≤17).

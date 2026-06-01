# Changelog

Alle nennenswerten Änderungen an `iil-klickdummy`. Format lose nach
[Keep a Changelog](https://keepachangelog.com/); Versionierung SemVer.

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

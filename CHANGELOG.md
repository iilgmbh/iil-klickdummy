# Changelog

Alle nennenswerten Änderungen an `iil-klickdummy`. Format lose nach
[Keep a Changelog](https://keepachangelog.com/); Versionierung SemVer.

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

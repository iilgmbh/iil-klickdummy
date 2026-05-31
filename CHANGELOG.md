# Changelog

Alle nennenswerten Änderungen an `iil-klickdummy`. Format lose nach
[Keep a Changelog](https://keepachangelog.com/); Versionierung SemVer.

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

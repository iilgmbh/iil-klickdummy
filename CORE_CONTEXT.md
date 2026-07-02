# CORE_CONTEXT — iil-klickdummy

> Agenten-/Onboarding-Kontext. Single source of facts für dieses Repo; ergänzt
> README (Nutzung) und CHANGELOG (Historie). Stand: v1.29.0.

## Was es ist

`iil-klickdummy` ist die **geteilte Infrastruktur für platform:ADR-211 Klickdummy-Konformität** —
ein als PyPI-Paket verteiltes Bündel aus Invarianten-Checks, Requirements-Bridge, Co-Creation-Widget
und Multi-Klickdummy-Browser. Ein Klickdummy ist ein **Renderer einer maschinenlesbaren
Anforderungs-Spec** (`screens-spec.yaml`), nicht die Quelle und kein Produktionscode.

## Stack

- **Python ≥ 3.10**, reines Paket (KEIN Django, keine DB) — Tests laufen ohne Postgres (`pytest`, ~90 Tests).
- **Playwright** ist *optional* — nur für ausführbare Parity-Suites (`klickdummy-gen-e2e`). Der generierte
  Output emittiert `pytest.importorskip("playwright")`, bricht also ohne Installation nicht (T-01).
- Distribution: **PyPI via Trusted Publishing (OIDC)**, getriggert durch Tag `v*.*.*` (nicht durch Merge).

## Console-Scripts (Einstieg: `pip install iil-klickdummy`)

| Gruppe | Scripts |
|--------|---------|
| **Invarianten (ADR-211 I1–I4)** | `klickdummy-i1` (Spec↔Schema), `klickdummy-i2` (Prod-Sicherheits-Pattern), `klickdummy-i3` (Off-Ramp/TTL), `klickdummy-i4` (Namensraum) |
| **Stories & Flow** | `klickdummy-stories` (story.yaml-Validierung), `klickdummy-flow` (Screen-Flow-DAG-Lint), `klickdummy-stories-manifest` |
| **Generierung** | `klickdummy-gen-e2e` (Spec→Parity-Suite), `klickdummy-extract-requirements` (Spec→UC/FR/NFR-Skelett), `klickdummy-install-snippets` |
| **Rendering** | `klickdummy-genesor` (lineage-Renderer), `klickdummy-from-django`, `klickdummy-manage` |
| **Discovery** | `klickdummy-browser` (Registry), `klickdummy-sync` (Orchestrator-pgvector), `klickdummy-inventory` (Legacy-Class-Inventur). Stage-1.5-Push = Modul `discovery_push` (ADR-215, `python -m`, kein Console-Script) |

Vollständige Referenz: [`docs/reference/cli.md`](docs/reference/cli.md).

## Schemas (`src/iil_klickdummy/schemas/`)

`screens-spec.schema.json` · `story.schema.json` · `module-manifest.schema.json` · `feedback-payload.schema.json`

## Spec-as-SoR / Parity-Status (WICHTIG — Stand 2026-06-30)

Die **Executable-Parity-Bridge** (`klickdummy-gen-e2e`: eine Spec → Suite, die per
`SPEC_RENDERER_BASE_URL` gegen Renderer #1 *und* #2 prüft) ist **`dormant`** (platform:ADR-211
Rev 22, Scoreboard S13, `dormancy_review_by: 2026-12-04`):
- **Mechanismus belegt** (3/3 grün gegen risk-hub `/sds/review/`),
- aber **0 reale Renderer #2** plattformweit — F22 (Auth-Modell) noch offen.
- **`klickdummy-parity-drift`** (Make-Target in Adopter-Repos) prüft **nur Spec↔Datei-Drift**
  (re-gen + diff), **nicht** Parität gegen einen Renderer.

**F23 Selektor-Kontrakt (ADR-211 Rev 22, 2026-06-30 — GESCHLOSSEN):**
- `testid=foo` ist der kanonische Selektor (`[data-testid=foo]` deprecated, Warnung generiert).
- Präfix-Vokabular: `testid=`, `role=`, `label=` (stabil) · `text=` (fragil, Fallback).
  Dispatch: `testid=` → `get_by_test_id`, `role=` → `get_by_role`, `label=` → `get_by_label`, `text=` → `get_by_text`, sonst `page.locator()`.
- `--strict-selectors` Flag: bricht den Generator-Lauf ab, wenn ein Selektor als fragil klassifiziert
  wird. Gedacht für Off-Ramp-Gates in CI. Ohne Flag: fragile Selektoren erzeugen nur eine Warnung.
- F18 (Selector-Registry) bleibt deferred (Trigger: ≥2 Consumer-Specs müssen Selektor wegen App-Änderung ändern).

Aktiv/in Nutzung bleiben: I1, I2-Pattern-Deklaration, I4, Co-Creation, Requirements-Bridge, Discovery.

## Cross-Referenzen

- **platform:ADR-211** — Klickdummy-Rahmen (Mutter-ADR, vier Invarianten, Parity-Bridge, Rev 22 F23-closed)
- **platform:ADR-215** — pgvector-Discovery (Stage 1.5, vom Modul `discovery_push` bedient)
- **platform:ADR-216** — Klickdummy-Hosting auf iil.pet
- Konzepte: `docs/konzepte/KONZ-iil-klickdummy-00{1..7}.md`

## Tests & Release

- `pytest` (kein Django/Postgres nötig); CI-Matrix 3.10/3.11/3.12.
- Release: Version in `pyproject.toml` bumpen + CHANGELOG → Tag `vX.Y.Z` pushen (OIDC-Publish).

# Agent Handover — iil-klickdummy

**Kuratierter Einstieg für Coding-Agent-Sessions.** Der Session-Start-Hook
(`handover_prio_mirror.sh`) spiegelt die Tabelle unter `## Prioritäten`;
`NEXT.md` ist nur der git-log-Fallback. Pflege: bei `/session-ende` aktualisieren.

## ⚡ Aktueller Stand (2026-06-14, Session 2 abgeschlossen)

- **Session-Retro A2+A3 gemergt** (PR #75, `cfbf590`): Smoke-Test kanonische Quelle
  stärker (importlib, sentinel-Format, `find_specs` beide Konventionen); neues
  `tests/test_read_model.py` mit Roundtrip-Test `build_uc_export_json → JSON →
  TypedDict-Keys`. 82 Tests grün, ruff clean.
- **klickdummy_sync kanonische Quelle VOLLSTÄNDIG** (alle 3 Consumer-Repos):
  ausschreibungs-hub#124 + meiki-hub#64 + iil-klickdummy#71 — alle auf Stand v1.28.0.
  Memory `klickdummy-sync-kopien-nur-formatierung` = ✅ vollständig.
- **v1.28.0 auf PyPI** (PRs #71/#72/#73, PyPI-Workflow grün):
  - **#66 / PR #71**: `klickdummy_sync.py` kanonische Quelle in `snippets/genesor-sync/`.
  - **#70 / PR #72**: `read_model.py` zentralisiert alle Schema-Versionskonstanten
    + TypedDicts (KONZ-003 Empf-3 S1). S2/S3 trigger-gegatet per KONZ-003 §13.
- **Prio 1 (S13-Operationalisierung) abgeschlossen** — Drift-Gate `make
  klickdummy-parity-drift` als CI-Job in risk-hub `ci.yml` verdrahtet
  (**risk-hub PR #184**, admin-gemergt). Der Job macht `klickdummy-install`
  (pin `iil-klickdummy>=1.27`) ZUERST — ein stale Generator färbt den Gate sonst
  aus dem falschen Grund rot (Memory `klickdummy-gen-version-drift`).
- **Parity-These EINGELÖST (Weg A)** — generierte `gen_e2e`-Suite lief 3/3 grün
  gegen die echte risk-hub-App (`/sds/review/`) und rot bei injizierter Divergenz.
  ADR-211 Rev 21, F22 geschlossen (platform #563).
  Memory `parity-gate-never-run-vs-renderer2` = ✅ AUFGELÖST.
- **2 Generator-Bugs gefixt** (PR #67): `gen_e2e` emittierte nicht-existente API
  `set_storage_state` → `browser_context_args`; Strict-Mode-Bruch bei Mehrfach-
  Selektoren → `.first`. Memory `smoke-test-marker-presence-gap` (+2 Belege).
- **Codebase-Analyse 2026-06 komplett** (KONZ-003 Empf-1, PR #59–#61) — Strang zu.
  Code-Motion-Fallenkatalog (6 Fallen): CC-Memory `codebase-analyse-2026-06-offene-items`.

## Prioritäten

| Prio | Task | Tier |
|---|---|---|
| 1 | UX-Test-Rollout: **risk-hub + writing-hub + meiki-hub + nl2iot-hub erledigt 2026-06-24 — alle 20 KDs sauber** (kein Bug; 2 Pilot-Bugs renderer-weit behoben, Persona-Filter-Effekt definitiv falsifiziert). Genesor-Repos offen: apo/bahn-sqf-pg/design/pg/sqf/ttz-hub. Prozedur/Lehren: Memory `klickdummy-ux-test` | `[Sonnet]` |
| 2 | **Stufe 2 zu S13**: Live-Renderer-#2-Lauf in CI automatisieren — Auth-Automation (headless Login → `storage_state`) + Seed in CI-DB + Playwright gegen die echte App. Drift-Gate (Stufe 1) gemergt (risk-hub #184); descoped in `sds-verwalten/README.md` | `[Sonnet]` |
| 3 | Outline-Capture der Sessions 2026-06-12/13/14 nachholen (braucht Session mit Outline-MCP; Inhalt in pgvector `session:iil-klickdummy:20260612`) | `[/fast]` |
| 4 | F23 (ADR-211): stabiler UI-Testkontrakt (`data-testid`/Manifest) als Konvention vs. semantischere Selektoren — offene Designfrage | `[Opus]` |
| 5 | KONZ-003 Empf-3 S2/S3: Repository-Port + Multi-Adapter (pgvector/SQLite) — erst wenn zweiter Live-Konsument `uc-export.json` abfragt (Trigger-Gate §13) | `[Opus]` |

## Arbeitsregeln (repo-spezifisch)

- **Code-Motion/Refactor:** Fallenkatalog lesen (CC-Memory
  `codebase-analyse-2026-06-offene-items`); golden-HTML-Diff **doppelt**
  (Default + `--base-url /kdtest/`) ist das Pflicht-Netz.
- **f-Strings <3.12-safe halten** — lokal läuft nur 3.12, CI matrixt 3.10/3.11
  (Memory `lineage-py-312-only-parse`).
- **Smoke-Tests:** Marker-Präsenz (`"x" in html`) reicht nicht — Anzahl + Kontext
  prüfen (Memory `smoke-test-marker-presence-gap`; der Prefill-Bug ist der Beleg).
- **Schema-Konstanten:** immer aus `read_model.py` importieren, nie inline (KONZ-003 Empf-3 S1).
- Konvention: `platform:ADR-211` · Implementations-ADR `iilgmbh:iil-klickdummy:ADR-001`
  · Konzepte in `docs/konzepte/KONZ-iil-klickdummy-NNN.md`.

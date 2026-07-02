# Agent Handover — iil-klickdummy

**Kuratierter Einstieg für Coding-Agent-Sessions.** Der Session-Start-Hook
(`handover_prio_mirror.sh`) spiegelt die Tabelle unter `## Prioritäten`;
`NEXT.md` ist nur der git-log-Fallback. Pflege: bei `/session-ende` aktualisieren.

## ⚡ Aktueller Stand (2026-07-02)

- **F23 GESCHLOSSEN (ehem. Prio 3)** — KONZ-iil-klickdummy-007 (T2, Hybrid D1+D2+D3, PR #89)
  + Implementierung in PR #90 (gemergt 2026-06-30, **v1.29.0**): `--strict-selectors`-Off-Ramp-Gate
  (D1, Exit-Code 3) + Präfix-Dispatch `testid=`/`role=`/`label=`/`text=` (D2); Locator-Registry
  (F18) bleibt zurückgestellt, Trigger geschärft (D3). Ratifiziert als **ADR-211 Rev 22**
  (platform). 151 Tests grün. Offene Follow-ups aus externer Zweitmeinung: **REC-1**
  (Spec-Attribut `strict_selectors: true` zusätzlich zum CLI-Flag) + **REC-2** (Parser-Grenzfälle
  der `role=`-Syntax formal dokumentieren + Roundtrip-Tests Sonderzeichen/Whitespace).
- **Prio 1 ENTBLOCKT** — risk-hub#278 (Schema-Bootstrap + RLS + Playwright-Browser) am
  2026-06-24 als COMPLETED geschlossen; Port-/Prod-Kollision via KONZ-risk-hub-004 Ebene A
  gelöst (keine fixen Host-Ports mehr). Der Stufe-2-Job läuft weiterhin informational
  (`continue-on-error: true` auf risk-hub main, verifiziert 2026-07-02); Restschritt =
  Stabilität belegen (mehrere grüne Läufe), dann required schalten. **Nicht verifiziert:**
  aktuelle Grün-Quote des Jobs — billigster Check: `gh run list` auf den Job filtern.

## ⚡ Stand 2026-06-30

- **Zwei offene PRs gemergt** (Session-Start-Aufräumen, beide CI 3/3 grün + CLEAN):
  - **PR #83** — `gen_e2e` skip-reason quoten: parametrisierte Route brach mit `SyntaxError`.
  - **PR #87** — KONZ-iil-klickdummy-006: Spec-first-Durchsetzung + Roundtrip-als-Zähne (T2).
  - `main` jetzt @ `0c34167`; stale Worktree des #87-Session-Branches entfernt. Keine offenen PRs mehr.

## ⚡ Stand 2026-06-24

- **UX-Test-Rollout ABGESCHLOSSEN** (vormalige Prio 1) — auf iPad/claude.ai gefahren
  (geteiltes pgvector-Memory; auf Dev-Host daher keine lokalen Render-Artefakte/Commits).
  **~35 KDs / 11 Repos** (ausschreibungs-hub-Pilot, **risk-hub**, **writing-hub**, meiki-,
  nl2iot-, apo-, bahn-sqf-pg-, design-, pg-, sqf-, ttz-hub) — **alle sauber**, kein Renderer-
  oder KD-spezifischer Bug; die 2 Pilot-Bugs sind renderer-weit behoben (Propagierung bestätigt).
  Erkenntnis: **drei KD-Artefakt-Klassen** (A genesor-Render = Renderer-Hebel · B in-Repo-Shell
  bespoke · C conversational) — Renderer-weiter Hebel gilt nur für Klasse A; Klasse-A-Rollout
  damit erschöpft. Volltext + `offsetParent`-Probe-Falle: Memory `klickdummy-ux-test`.
- **S13 Stufe 2 GESTARTET, blockiert** — Live-Renderer-#2-Parity-Job als **informational**
  (`continue-on-error`) in risk-hub CI verdrahtet (**risk-hub PR #276**, gemergt): CI-Postgres →
  `migrate --fake-initial` → `seed_dsb_demo` + `seed_sds_review_demo --tenant-slug dsb-demo` →
  `runserver :8090` (DEBUG=1) → headless Login (`make_storage_state.py`) → generierte Suite. 3 echte
  Erstinbetriebnahme-Bugs gefixt. Job bleibt **rot** an strukturellem Schema-Bootstrap-Blocker
  (dual-tenancy-Migrationsgraph; der `test`-Job umgeht ihn mit `--no-migrations`) → Resthärtung
  getrackt in **risk-hub#278** (Schema-Bootstrap + RLS + Playwright-Browser). Retro: Memory
  [[ci-job-precheck-target-context]].

## ⚡ Stand 2026-06-14 (Session 2 abgeschlossen)

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
| 1 | **S13 Stufe 2 Abschluss**: Grün-Quote des informational-Jobs `klickdummy-parity-renderer2-live` messen; bei Stabilität `continue-on-error` entfernen + required check + README-Update (DoD aus risk-hub#278 — Blocker sind behoben, Issue COMPLETED 2026-06-24) | `[Sonnet]` |
| 2 | Outline-Capture der Sessions 2026-06-12/13/14 nachholen (Outline-MCP seit 2026-07-02 als `outline-knowledge` auf User-Scope registriert; Inhalt in pgvector `session:iil-klickdummy:20260612`) | `[/fast]` |
| 3 | **KONZ-007 Follow-ups**: REC-1 Spec-Attribut `strict_selectors: true` (zusätzlich zum CLI-Flag) + REC-2 `role=`-Parser-Grenzfälle formal dokumentieren + Roundtrip-Tests (Sonderzeichen/Whitespace) | `[Sonnet]` |
| 4 | KONZ-003 Empf-3 S2/S3: Repository-Port + Multi-Adapter (pgvector/SQLite) — erst wenn zweiter Live-Konsument `uc-export.json` abfragt (Trigger-Gate §13) | `[Opus]` |

> **Erledigt 2026-06-30:** ehem. Prio 3 *F23* — geschlossen via KONZ-007 (PR #89/#90, v1.29.0) + ADR-211 Rev 22 (s. „Aktueller Stand 2026-07-02").
> **Erledigt 2026-06-24:** ehem. Prio 1 *UX-Test-Rollout* — komplett, alle Repos sauber (s. „Stand 2026-06-24").

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

# Agent Handover — iil-klickdummy

**Kuratierter Einstieg für Coding-Agent-Sessions.** Der Session-Start-Hook
(`handover_prio_mirror.sh`) spiegelt die Tabelle unter `## Prioritäten`;
`NEXT.md` ist nur der git-log-Fallback. Pflege: bei `/session-ende` aktualisieren.

## ⚡ Aktueller Stand (2026-06-14)

- **Prio 1 (S13-Operationalisierung) abgeschlossen** — Drift-Gate `make
  klickdummy-parity-drift` als CI-Job in risk-hub `ci.yml` verdrahtet
  (**risk-hub PR #184**, admin-gemergt). Lief vorher in KEINEM Workflow.
  Der Job macht `klickdummy-install` (pin `iil-klickdummy>=1.27`) ZUERST —
  ein stale Generator färbt den Gate sonst aus dem falschen Grund rot
  (lokal real: `.venv-klickdummy@1.6.1` → false-positive; Memory
  `klickdummy-gen-version-drift`). Spec+Auth+Suite+Seed kamen schon mit
  risk-hub #182. **Rest = Stufe 2** (Live-Renderer-#2-Lauf in CI), descoped
  im `sds-verwalten/README.md`. Merge war BLOCKED durch 2 vorbestehende
  Runner-Infra-Failures (`libpangoft2`, `dj_database_url`) — NICHT durch die
  ci.yml-only-Änderung.
- **Parity-These EINGELÖST (Weg A, nicht descoped)** — Ur-Prio 1 erledigt.
  Ein billiger Cross-Repo-Sweep kippte die Descope-Prämisse: die generierte
  `gen_e2e`-Suite lief **3/3 grün gegen die echte risk-hub-App** (`/sds/review/`,
  login-gegatet, Auth via `storage_state`) und **rot bei injizierter Divergenz** →
  diskriminiert App↔Spec-Drift. ADR-211 **Rev 21** dreht S13 `dormant`→reaktiviert,
  **F22 geschlossen** (platform PR #563). Memory `parity-gate-never-run-vs-renderer2`
  = ✅ AUFGELÖST.
- **2 Generator-Bugs gefixt** (iil-klickdummy **PR #67**, dieser Branch): `gen_e2e`
  emittierte die nicht-existente API `set_storage_state` → `browser_context_args`;
  Strict-Mode-Bruch bei Mehrfach-Selektoren → `.first`. Beide bestanden Unit-Tests
  (nur Text-Marker — Memory `smoke-test-marker-presence-gap`, +2 Belege). 141 Tests grün.
- **v1.26.0 auf PyPI** (PR #64): Org-Registry-Anbindung aus #63.
- **Codebase-Analyse 2026-06 komplett** (KONZ-003 Empf-1, PR #59–#61) — Strang zu.
  Code-Motion-Fallenkatalog (6 Fallen): CC-Memory `codebase-analyse-2026-06-offene-items`.

## Prioritäten

| Prio | Task | Tier |
|---|---|---|
| 1 | KONZ-003 Empf-3: Read-Model (`uc-export.json` + `discovery_push`) → schema-stabile Repository-Schnittstelle (Nutzen hält, da These eingelöst statt descoped) | `[Opus→Sonnet]` |
| 2 | UX-Test-Rollout auf weitere Klickdummy-Repos (Prozedur: Memory `klickdummy-ux-test`; Pilot fand 2 renderer-weite Bugs) — Ziel-Repos vom User erfragen | `[Sonnet]` |
| 3 | **Stufe 2 zu S13** (Rest aus Ur-Prio 1): Live-Renderer-#2-Lauf in CI automatisieren — Auth-Automation (headless Login → `storage_state`) + Seed in CI-DB + Playwright gegen die echte App. Drift-Gate (Stufe 1) ist gemergt (risk-hub #184); descoped in `sds-verwalten/README.md` | `[Sonnet]` |
| 4 | Outline-Capture der Sessions 2026-06-12/13/14 nachholen (braucht Session mit Outline-MCP; Inhalt in pgvector `session:iil-klickdummy:20260612`) | `[/fast]` |
| 5 | F23 (ADR-211): stabiler UI-Testkontrakt (`data-testid`/Manifest) als Konvention vs. semantischere Selektoren — offene Designfrage | `[Opus]` |

## Arbeitsregeln (repo-spezifisch)

- **Code-Motion/Refactor:** Fallenkatalog lesen (CC-Memory
  `codebase-analyse-2026-06-offene-items`); golden-HTML-Diff **doppelt**
  (Default + `--base-url /kdtest/`) ist das Pflicht-Netz.
- **f-Strings <3.12-safe halten** — lokal läuft nur 3.12, CI matrixt 3.10/3.11
  (Memory `lineage-py-312-only-parse`).
- **Smoke-Tests:** Marker-Präsenz (`"x" in html`) reicht nicht — Anzahl + Kontext
  prüfen (Memory `smoke-test-marker-presence-gap`; der Prefill-Bug ist der Beleg).
- Konvention: `platform:ADR-211` · Implementations-ADR `iilgmbh:iil-klickdummy:ADR-001`
  · Konzepte in `docs/konzepte/KONZ-iil-klickdummy-NNN.md`.

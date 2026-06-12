# Agent Handover — iil-klickdummy

**Kuratierter Einstieg für Coding-Agent-Sessions.** Der Session-Start-Hook
(`handover_prio_mirror.sh`) spiegelt die Tabelle unter `## Prioritäten`;
`NEXT.md` ist nur der git-log-Fallback. Pflege: bei `/session-ende` aktualisieren.

## ⚡ Aktueller Stand (2026-06-12)

- **v1.26.0 auf PyPI** (PR #64): Org-Registry-Anbindung aus #63
  (`detect_org`/`app_name_map` lesen `platform/registry/canonical.yaml`,
  Code-Heuristik bleibt PyPI-Fallback).
- **Codebase-Analyse 2026-06 komplett** (KONZ-003 Empf-1, PR #59–#61) — Strang zu.
  Code-Motion-Fallenkatalog (6 Fallen): CC-Memory `codebase-analyse-2026-06-offene-items`.
- **Quality-Sweep** (dieser Branch): ruff 29→0; dabei echten Bug gefixt —
  UC-Issue-Form-Prefill (`anker`/`daten`/`persona`) wurde berechnet, aber nie an
  die URL gehängt. Golden-Diff doppelt: 20/87 Dateien geändert, 0 unerklärt.

## Prioritäten

| Prio | Task | Tier |
|---|---|---|
| 1 | Parity-Gate-Entscheidung: These an EINEM echten Renderer #2 beweisen (A) oder formal descopen (B) — S13 `dormant`, review_by 2026-12-04; Memory `parity-gate-never-run-vs-renderer2` | `[Opus]` |
| 2 | KONZ-003 Empf-3: Read-Model (`uc-export.json` + `discovery_push`) → schema-stabile Repository-Schnittstelle — erst NACH Prio 1 (bei B-Descope schrumpft der Nutzen) | `[Opus→Sonnet]` |
| 3 | UX-Test-Rollout auf weitere Klickdummy-Repos (Prozedur: Memory `klickdummy-ux-test`; Pilot fand 2 renderer-weite Bugs) — Ziel-Repos vom User erfragen | `[Sonnet]` |
| 4 | Outline-Capture der Sessions 2026-06-12 nachholen (braucht Session mit Outline-MCP; Inhalt liegt in pgvector `session:iil-klickdummy:20260612`) | `[/fast]` |

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

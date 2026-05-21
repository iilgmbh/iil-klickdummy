---
adr_id: ADR-001
title: "iil-klickdummy — Implementation of platform:ADR-211"
status: accepted
date: 2026-05-21
deciders: ["Achim Dehnert"]
tags: [klickdummy, implementation]
conforms_to: platform:ADR-211
sister_of:
  - meiki-hub:ADR-021
  - meiki-hub:ADR-020
  - writing-hub:ADR-180
  - risk-hub:ADR-046
  - ttz-hub:ADR-100
# Pflicht-Frontmatter (platform:ADR-211 Rev 11 §Frontmatter-Konvention)
class: mock
sunset_after: 2027-05-21
extension_review_required: false
---

# ADR-001 · iil-klickdummy — Implementation of platform:ADR-211

## Status
Accepted (2026-05-21) — Erst-ADR im neuen Repo `iilgmbh/iil-klickdummy`
nach Extraktion aus `achimdehnert/platform/packages/iil-klickdummy/`.

## Kontext

`platform:ADR-211` (Rev 14) ist der **Cross-Repo-Rahmen** für Klickdummies —
die Konvention (4 Invarianten, 4 Patterns, Distribution-Mechanik,
Co-Creation-Loop, Multi-Klickdummy-Browser). Sie gilt für alle Klickdummy-
Repos der iil/iilgmbh/achimdehnert-Org-Familie.

Dieses Repo (`iilgmbh/iil-klickdummy`) ist **eine** Implementation dieses
Rahmens — das pip-Paket `iil-klickdummy`, das Schemas, Checks (I1-I4),
Requirements-Bridge, Co-Creation-Widget und Multi-Klickdummy-Browser als
shared Infrastruktur bereitstellt.

## Entscheidung

1. **Trennung Konvention ↔ Implementation:**
   - **Konvention** lebt in `platform:ADR-211` (achimdehnert/platform).
     Sie wird von **allen** Klickdummy-Repos konsumiert.
   - **Implementation** lebt in `iilgmbh/iil-klickdummy`. Sie wird als
     pip-Paket via PyPI distribuiert.

2. **Klasse `mock`** für eigene `klickdummy/`-Beispiele (falls hier welche
   entstehen — z. B. zum Eigentest oder als Reference-Implementation).
   Aktuell hat das Repo keinen eigenen Klickdummy-Pfad.

3. **Cross-Repo-Bezug** über `platform:ADR-211`. Schwester-Implementations-
   ADRs verlinkt unter `sister_of`. Keine Re-Definition der Konvention hier.

## Konsequenzen

**Positiv**
- PyPI-Konsument:innen sehen ein fokussiertes Repo (Klickdummy-Tool), nicht
  das gesamte platform-Repo mit ~60 anderen Themen.
- Releases im Klickdummy-Lifecycle entkoppelt von platform-Release-Rhythmus.
- Issues hier sind **iil-klickdummy-spezifisch** — keine Vermischung mit
  platform-weiten Themen (ADRs, Infrastruktur, sonstige Pakete).
- Naming-Konsistenz: `iil-*`-Pakete unter `iildehnert`-PyPI-Account +
  `iilgmbh`-GitHub-Org.

**Negativ / Kosten**
- Cross-Repo-Verträge mit `platform:ADR-211` müssen konsistent gehalten
  werden (`adr_sunset.sh`-Lint + Auto-Memory-Sync gegen Orchestrator
  helfen — siehe Rev-14-Roadmap Stufe 2).
- PyPI-Trusted-Publisher musste 1× umkonfiguriert werden
  (`achimdehnert/platform` → `iilgmbh/iil-klickdummy`).

**Neutral**
- Git-Historie über `git filter-repo --path packages/iil-klickdummy/`
  vollständig erhalten (3 sichtbare Commits seit Trennung, Detail-Historie
  in den Subtree-Commits enthalten).

## Bezug

- `platform:ADR-211` (Rev 14) — Cross-Repo-Rahmen, **gilt unverändert**
- `meiki-hub:ADR-021` — Schwester (Fristenmanagement-Klickdummy)
- `meiki-hub:ADR-026` — Co-Creation-Loop + Requirements-Bridge-Anwendung
- `writing-hub:ADR-180` — Schwester (Lecture-Outline-Wizard)
- `risk-hub:ADR-046` — Schwester (Spec-Driven UI Convention)
- `ttz-hub:ADR-100` — Schwester (Werkleiter-Skizze)
- PyPI: https://pypi.org/project/iil-klickdummy/
- Trusted Publisher: GitHub-Action `publish-pypi.yml` in diesem Repo

---
concept_id: KONZ-iil-klickdummy-004
title: Story↔UC-Zuordnung — explizit & fail-fast statt Authoring-Tool
pipeline_status: idea
tier: T2
owner: achim                      # Annahme (Repo-/Plattform-Owner, ADR-211 deciders:[achim]) — bestätigen
spec_refs: []                     # betrifft Renderer-Tooling + story.yaml-Format, nicht eine konkrete Spec
conforms_to: platform:ADR-211
adr_threshold: kein ADR           # renderer-lokales story.yaml-Schema + Build-Gate, additiv/reversibel; Amendment NUR falls story↔UC zu Cross-Repo-PFLICHT würde
review_by: 2026-08-31             # created + 90 Tage; ohne Pflege Auto-Sunset (I3)
superseded_by_spec: null
kill_criteria: "Pilot (ausschreibungs-hub) zeigt: story.yaml-Schema + bidirektionaler UC-Lint fangen 0 reale Drift-/Tippfehler-Fälle, die nicht schon durch screens[].use_cases + Coverage sichtbar sind → nur stderr-Warning behalten, Schema+Lint verwerfen."
evidence_manifest:
  - {claim_id: C1, source_path: src/iil_klickdummy/schemas/screens-spec.schema.json, commit_or_pr: working-tree, opened_in_session: true}
  - {claim_id: C2, source_path: src/iil_klickdummy/registry.py, commit_or_pr: working-tree, opened_in_session: true}
  - {claim_id: C3, source_path: src/iil_klickdummy/lineage.py, commit_or_pr: working-tree, opened_in_session: true}
  - {claim_id: C4, source_path: src/iil_klickdummy/schemas/, commit_or_pr: working-tree, opened_in_session: true}
  - {claim_id: C5, source_path: ".claude-memory/spec-as-sor-keystone", commit_or_pr: memory, opened_in_session: true}
created: 2026-06-02
---

# KONZ-iil-klickdummy-004 — Story↔UC-Zuordnung: explizit & fail-fast statt Authoring-Tool

## Kernthese (1 Satz)
Die UC↔Screen-Zuordnung ist im Spec-Modell **bereits explizit** (`screens[].use_cases[]`); der reale Schmerz ist **nicht** ein fehlendes Authoring-Tool, sondern dass **`story.yaml` schemalos & nur render-zeitig (stderr) validiert** wird — daher: kleines **JSON-Schema + Build-Gate für story.yaml** und ein **bidirektionaler UC-Konsistenz-Lint**, **kein** UI/Tool.

## Erdungs-Befund (Root-Cause-Tiefe — die naheliegende Lösung war falsch)
Der Auftrag lautete „Tool zum Erstellen/Verwalten der UC-Zuordnung". Die Erdung falsifiziert die Prämisse, dass die Zuordnung fehlt:

| Zuordnung | Status heute | Beleg |
|---|---|---|
| **UC → Screen** | **explizit, first-class** `screens[].use_cases[]` (ab `spec_schema_version 1.1`); Fallback `konzept_ref[]`/`akte_next.uc` | C1 |
| **UC → KD (reverse)** | abgeleitet aus `uc.related_screens`-Refs + `adr_to_kd`-Lookup (Roh-Fallback wenn Lookup fehlt) | C3 |
| **KD → Story** | hand-editiertes `story.yaml`; **kein Schema** (nur screens-spec/feedback/module-manifest haben eins); `discover_stories` validiert **nur stderr-Warning + Silent-Skip**, kein Fail-Fast | C2, C4 |
| **Sichten** | `coverage.html`, Genesor-UC-Index, `uc-export.json` existieren read-only | C3 |

→ Ein „Authoring-Tool" würde eine **dritte Wahrheit** neben Spec + story.yaml schaffen. SoR ist laut ADR-211 die **Spec** (C5). Die Lücke ist **Validierung/Fail-Fast**, nicht **Erfassung**.

## Ledger

| id | Aussage | Typ | Evidenz / Falsifikation | Status |
|---|---|---|---|---|
| L1 | UC→Screen ist bereits explizit (`use_cases[]`) → kein neues Erfassungs-Feld nötig | Entscheidung | C1; falsifiziert durch: Schema ohne `use_cases` | belegt |
| L2 | `story.yaml` ist schemalos → Tippfehler/Strukturfehler erst zur Render-Zeit als stderr-Warning sichtbar | Annahme→belegt | C2, C4 | belegt |
| L3 | Fix = `story.schema.json` + Validierung in `discover_stories` (Fehler sammeln, am Make-Target hart) statt nur warnen | Entscheidung | MVC unten | offen (Pilot) |
| L4 | Drift screen.`use_cases` ↔ uc.`related_screens` ist heute nicht geprüft (kann auseinanderlaufen) | Risiko | C1+C3; bidirektionaler Join fehlt in `build_uc_coverage`/`validate_ucs` | offen |
| L5 | Ein UI/Authoring-Tool ist Über-Engineering (SoR=Spec; Editor=git/IDE) | Entscheidung | ADR-211 SoR (C5); AD-1 unten | belegt |
| L6 | `adr_to_kd`-Roh-Fallback verschleiert fehlende UC→KD-Auflösung (still „ADR-NNN" statt KD) | Risiko | C3 (Fallback-Zweig) | offen |

## MVC (konkret — Dateien/Felder/Gate; keine Anforderungsprosa)
1. **`src/iil_klickdummy/schemas/story.schema.json`** (neu): `id` (Pattern `^[a-z0-9-]+:story-[a-z0-9-]+$`), `title` (required), `steps[].kd` (required, string), `steps[].label`, optional `persona`/`description`. `additionalProperties:false`.
2. **`registry.discover_stories`** (C2): gegen das Schema validieren; **alle** Fehler je Datei sammeln und als Liste zurückgeben statt einzeln zu warnen + skippen. Verhalten bei fehlendem `stories/` unverändert (`[]`).
3. **Make-Target `klickdummy-stories-validate`** (Consumer-Repo, additiv): ruft die Validierung; **Exit≠0** bei (a) Schema-Verstoß, (b) `step.kd` ohne KD-Match. Macht den heutigen Silent-Skip zum harten Gate.
4. **Bidirektionaler UC-Lint** in `validate_ucs`/`build_uc_coverage` (C3): warnt, wenn ein `screens[].use_cases`-Eintrag keinen UC mit passendem `related_screens`-Rückbezug hat (und umgekehrt) — Drift L4 sichtbar, ohne neue Datenquelle.
5. **Kein** UI, **kein** neues Manifest, **kein** neues SoR-Feld. `stories-manifest.json` bleibt reines Derivat.

## Adversariat (T2 — inline)
**Steelman (für ein Tool):** Stakeholder/PO pflegen Stories/UCs ungern in YAML; ein Klick-Editor (Drag-Steps, UC-Dropdown aus vorhandenen UCs) senkt die Hürde, erhöht Adoption der Story-Walks und macht Drift unmöglich, weil nur valide Zuordnungen klickbar sind.

**Advocatus Diabolus:** (1) Ein Editor, der `story.yaml`/Spec schreibt, ist eine **zweite Schreibquelle** neben git — Merge-/Auth-/Hosting-Aufwand, und er kann valide Zuordnungen erzeugen, die fachlich falsch sind (formal erfüllt, praktisch umgangen). (2) „Verwalten" ohne Enforcement ist schwächer als ein **Build-Gate**, das Falsches *verhindert*. (3) Das Tool verschiebt faktisch die Boundary: wer das Tool kontrolliert, kontrolliert die Spec → SoR-Aufweichung. (4) F-Items: ein Tool berührt keine, ein Gate härtet L2/L4 messbar.

**Maintainer-2028:** Ein JSON-Schema + Make-Gate ist in 2 Jahren noch trivial wartbar (gleiches Muster wie screens-spec). Eine Editor-App (State, Auth, Hosting hinter Cloudflare Access) ist Wartungslast, die niemand anfasst → verrottet, während YAML+git weiterläuft.

**Konflikt:** Steelman (Adoption via UI) vs. Diabolus/Maintainer (UI = zweite Quelle + Wartungslast). **Synthese:** Adoptionsproblem ist real, aber durch **Fail-Fast + gute Fehlermeldung + `story.yaml.example`** günstiger lösbar als durch eine App; UI bleibt Backlog, nur falls Pilot echte Autoren-Hürde belegt.

## Alternativen
| # | Ansatz | Warum nicht (jetzt) |
|---|---|---|
| A1 | **Status quo** (nur stderr-Warning) | L2: Fehler bleiben unsichtbar bis Render; kein Gate |
| A2 | **Voller Authoring-UI/Editor** (gewählter Titel) | AD-1..4: zweite Schreibquelle, Boundary-/SoR-Aufweichung, Wartungslast; SoR=Spec |
| **A3 (Empfehlung)** | **story.schema.json + Build-Gate + bidir. UC-Lint** | additiv, reversibel, härtet L2/L4, keine neue Quelle |

## Entscheidung + Kill-Gate
**Empfehlung: A3.** Pilot in **ausschreibungs-hub** (hat Stories + viele UCs). 
**Kill-Gate (messbar):** Findet der Pilot **0** reale Drift-/Tippfehler-Fälle, die nicht schon durch `screens[].use_cases` + Coverage sichtbar wären → Schema+Lint verwerfen, nur stderr-Warning behalten. 
**Exception-Budget:** Re-Review bis **2026-08-31** (`review_by`); ohne Pflege Auto-Sunset (I3). 
**Eskalation:** Wird story↔UC zu einer **Cross-Repo-Pflicht** (alle Repos MÜSSEN) → hochstufen auf **T3 + ADR-211-Amendment**, nicht still in T2 lösen.

## Ehrliche Enforcement-Grenze
Dieses Doc trägt `review_by`/`kill_criteria`/`superseded_by_spec`, aber **kein** Lifecycle-Gate liest sie heute → Lifecycle ist **Review-Gate, kein Exit-Code**, bis ein solches Gate existiert.

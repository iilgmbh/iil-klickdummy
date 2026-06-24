---
concept_id: KONZ-iil-klickdummy-006
title: Dup-Topic-KD-Warn-Gate — neue KD-Dubletten zum selben Thema verhindern
pipeline_status: idea
tier: T2
owner: Achim Dehnert
spec_refs: []
adr_threshold: kein ADR (Erweiterung bestehender genesor-validate; wird es org-weit hartes required-Gate → Amendment ADR-211 §I1/I3 prüfen)
review_by: 2026-08-01
kill_criteria: "Lauf des DUP-TOPIC-Heuristik über alle ~11 KD-Repos: findet sie außer dem bekannten ex-schutz-Cluster 0 echte Cluster ODER hat FP-Rate >25% → Cluster-Heuristik verwerfen, nur das bestehende I1-NO-SPEC-Surfacing behalten."
superseded_by_spec: null
evidence_manifest:
  - {claim_id: C1, source_path: src/iil_klickdummy/genesor/scan.py, commit_or_pr: "Z.289/334-359 gelesen (F11 render-only-Erkennung)", opened_in_session: true}
  - {claim_id: C2, source_path: src/iil_klickdummy/genesor/validate.py, commit_or_pr: "Z.99-104 gelesen (I1-NO-SPEC)", opened_in_session: true}
  - {claim_id: C3, source_path: iilgmbh/risk-hub klickdummy/ (ex-schutz-konzept/ + 2 lose .html), commit_or_pr: "verifiziert 2026-06-24", opened_in_session: true}
created: 2026-06-24
---

# KONZ-iil-klickdummy-006 — Dup-Topic-KD-Warn-Gate

**Tier: T2** — neue Boundary (ein Warn-Gate) → Auto-Eskalation auf mind. T2; aber Erweiterung
bestehender genesor-Tooling, warn-only, reversibel → nicht T3. (Wird es ein **hartes, required**
org-weites Gate → re-tiern auf T3 + ADR-211-§I1/I3-Amendment prüfen.)

## Kernthese
Genesor **erkennt** spec-lose KDs bereits (`scan.py` F11, `validate.py` `I1-NO-SPEC`), macht das aber
nur im **Dashboard sichtbar** — es fehlt (a) die **Themen-Cluster-Erkennung** (mehrere KDs = ein Thema)
und (b) ein **Warn-Gate zum Anlege-/CI-Zeitpunkt**, das „zu diesem Thema gibt es schon ein spec-dir-KD
— aktualisiere das" sagt, *bevor* eine neue spec-lose Dublette entsteht.

## Ledger
| id | Aussage | Typ | Evidenz / Falsifikation | Status |
|----|---------|-----|--------------------------|--------|
| L1 | Spec-lose render-only-KDs werden bereits erkannt | Annahme→belegt | `scan.py` kinds `render-only-subdir/-inline` (C1); `validate.py` `I1-NO-SPEC` (C2) | bestätigt |
| L2 | Themen-Dubletten (3 KDs = 1 Thema) werden NICHT als Cluster erkannt | Annahme→belegt | risk-hub ex-schutz: 3 Artefakte, von genesor einzeln gelistet, nicht als „1 Thema" geclustert (C3) | bestätigt |
| L3 | Die Erkennung wird nur im Dashboard sichtbar, nicht als Gate beim Anlegen/CI | Annahme | dashboard-only (User-Report); kein make-Target/CI-Step der validate-Warnings hart surfaced | offen-plausibel |
| L4 | Ein **Warn**-Gate (nicht Block) ist richtig — Cluster-Heuristik kann FP haben | Entscheidung | Analogie test_claim_check.py (warn-only Phase SUGGEST) | gesetzt |
| L5 | Slug/Title-Normalisierung erkennt `ex-schutz`≈`exschutz`, `-prototype`/`-workflow`-Suffixe | Annahme | falsifizierbar im Pilot (Kill-Gate) | zu testen |
| R1 | Risiko: Cluster-Heuristik FP (zwei echte verschiedene Themen fälschlich geclustert) | Risiko | Kill-Gate FP>25% → verwerfen | mitigiert |
| R2 | Risiko: zweite Wahrheit — Gate widerspricht genesor-validate | Risiko | Mitigation: Gate RUFT validate_kd auf, definiert keine eigene I1-Logik | mitigiert |

## MVC (konkret)
1. **`scan.py`/`validate.py` erweitern:** neue Warnung `DUP-TOPIC` (severity warning). Heuristik:
   KDs gruppieren nach normalisiertem Schlüssel `norm(slug) ∪ norm(<title>)` — `norm` = lowercase,
   Bindestriche/Leerzeichen weg, Suffixe `-prototype|-workflow|-prototyp` strippen, `exschutz→ex-schutz`.
   Cluster mit ≥2 Mitgliedern, von denen ≥1 ein spec-dir und ≥1 spec-los ist → `DUP-TOPIC` mit
   Auflistung + Hinweis „kanonisch = das spec-dir; spec-lose Mitglieder einschmelzen + archivieren (I3)".
2. **Warn-Gate-Oberfläche:** Console-Script/Make-Target `klickdummy-dup-check` (warn-only, Exit 0),
   das `validate_kd`-Warnungen (`I1-NO-SPEC` + `DUP-TOPIC`) für das aktuelle Repo ausgibt; optional als
   CI-Step (opt-in pro Repo, Phase SUGGEST).
3. **Anlege-Zeitpunkt:** Die `klickdummy`-Skill (KD anlegen) ruft die Cluster-Prüfung gegen bestehende
   Specs zuerst auf → bei Treffer Warnung „Thema existiert als spec-dir <name> — aktualisiere dessen
   screens-spec.yaml statt neuer Datei" (Kopplung an Memory `klickdummy-update-not-regenerate`).

## Kill-Gate + Threshold
Pilot: `klickdummy-dup-check` über alle ~11 KD-Repos laufen lassen. **Verwerfen**, wenn außer dem
bekannten ex-schutz-Cluster **0** echte Cluster gefunden werden ODER FP-Rate **>25%**. Exception-Budget:
1× Verlängerung um 2 Wochen bis 2026-08-15, dann promote (warn→ggf. hart) | delete.

## Befunde + Adversariat (T2)
| # | Befund / Diabolus-Frage | Antwort |
|---|--------------------------|---------|
| B1 | Erkennung existiert, nur Hebel fehlt | Gate baut auf `validate_kd` auf, keine Dublette der I1-Logik (R2) |
| B2 | Wird „Tool" zur Boundary? | Ja, bewusst — warn-only + Kill-Gate halten es weich |
| AD1 | „Cluster-Heuristik ist unzuverlässig (FP)" | warn-only akzeptiert FP; Kill-Gate killt sie bei >25% |
| AD2 | „Warnung wird ignoriert wie ein Memo" | Anlege-Zeitpunkt-Kopplung (MVC-3) bringt sie an die Entstehung, nicht post-hoc |
| AD3 | „Verschlimmert I3?" | Nein — macht I3 (Off-Ramp max. 1 Impl) erst durchsetzbar, indem Cluster sichtbar werden |

## Alternativen
| # | Alternative | Warum nicht |
|---|-------------|-------------|
| A1 | Nur Dashboard (Status quo) | User-Feedback belegt: Dashboard-Sichtbarkeit verhinderte die 3er-Dublette nicht |
| A2 | Hartes Block-Gate sofort | verfrüht ohne FP-Validierung; Cluster-Heuristik unbewiesen → erst warn-only |

## Cross-Ref
Gleiche Gate-Familie/Philosophie wie KONZ-platform-009 (cheapest-check, achimdehnert/platform#654) —
„wiederkehrendes Muster → warn-only Gate, Phase SUGGEST→FAIL, Kill-Gate". Auslöser: User-Feedback
2026-06-24 + Memory `klickdummy-update-not-regenerate`.

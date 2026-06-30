---
concept_id: KONZ-iil-klickdummy-006
title: Spec-first-Durchsetzung + Roundtrip-als-Zähne — KD-Dubletten an der Wurzel verhindern
pipeline_status: idea
tier: T2
owner: Achim Dehnert
spec_refs: []
adr_threshold: kein ADR für den MVC (repo-Gate-Angleichung); wird die Spec-Pflicht org-weit verschärft → Amendment ADR-211 §I1 prüfen
review_by: 2026-08-01
kill_criteria: "Wenn die spec-first-Angleichung von risk-hubs klickdummy-i1 über 4 Wochen keinen einzigen spec-losen KD blockt/meldet (= es gab nie welche) → der Bypass existiert nicht, Konzept verwerfen. Phase-2-Roundtrip-Gate killt sich, wenn kein Topic je den Code-Stand erreicht (dann ist es verfrüht)."
superseded_by_spec: null
evidence_manifest:
  - {claim_id: C1, source_path: src/iil_klickdummy/genesor/validate.py, commit_or_pr: "Z.99 I1-NO-SPEC", opened_in_session: true}
  - {claim_id: C2, source_path: iilgmbh/risk-hub Makefile klickdummy-i1, commit_or_pr: "iteriert klickdummy/*.html, grep go()/verify_dummy — KEINE Spec-Pflicht", opened_in_session: true}
  - {claim_id: C3, source_path: iilgmbh/risk-hub klickdummy/ex-schutz-konzept/screens-spec.yaml, commit_or_pr: "keine assert/data-testid (Prosa-Spec)", opened_in_session: true}
  - {claim_id: C4, source_path: iilgmbh/risk-hub src/exschutzdokument/, commit_or_pr: "models-only: keine views.py/urls.py/templates, nicht in config/urls", opened_in_session: true}
  - {claim_id: C5, source_path: iilgmbh/risk-hub src/templates/global_sds/review_queue.html, commit_or_pr: "6 data-testid + /sds/review/ → sds-Roundtrip lief Rev 21", opened_in_session: true}
  - {claim_id: C6, source_path: src/iil_klickdummy/from_django.py, commit_or_pr: "klickdummy-from-django: Brownfield-Reverse-Onboarding, URLConf→Screens/Models→Entities, dann gen-e2e bis parity-grün", opened_in_session: true}
created: 2026-06-24
---

# KONZ-iil-klickdummy-006 — Spec-first-Durchsetzung + Roundtrip-als-Zähne

**Tier: T2** — tightening eines bestehenden Gates (risk-hub `klickdummy-i1`) + Phasen-Akzeptanz via
existierender S13-Parity-Bridge; reversibel. (Org-weite Verschärfung der Spec-Pflicht → re-tiern T3 +
ADR-211-§I1-Amendment.)

> **Revision 2026-06-24:** Ersetzt die erste Fassung („Dup-Topic-Warn-Detektor"). User-Einwand:
> *die Pipeline `workflow→UC→KD→mock→code`+Roundtrip verhindert Dubletten doch selbst* — korrekt.
> Ein Detektor behandelt das **Symptom**; der Wurzel-Fix ist, die **Pipeline durchzusetzen**
> (spec-first) und ihr mit dem **Roundtrip Zähne** zu geben.

## Kernthese
KD-Dubletten entstehen **nur durch Pipeline-Bypass**: spec-lose lose `.html` werden direkt in
`klickdummy/` abgelegt, ohne UC/Spec. Der Fix ist kein Detektor, sondern (a) **spec-first als Gate**
(nichts kann an der Spec vorbei entstehen) und (b) der **Roundtrip als Beweis**, dass Code+Spec
dieselbe Wahrheit sind — ein KD, das gegen die echte App geprüft wird, *kann* keine lose Dublette sein.

## Drei legitime Einstiegspfade in die Pipeline (jeder spec-first)
Ein KD entsteht **immer** über die Spec — nie als lose HTML. Es gibt drei gleichberechtigte Einstiege:

| Einstieg | Richtung | Werkzeug |
|----------|----------|----------|
| **Greenfield** | workflow → UC → KD → mock → code | `/use-case`, `klickdummy` |
| **Brownfield** (App existiert) | **code → KD extrahieren → optimieren → code angleichen** | **`klickdummy-from-django`** (C6) + `klickdummy-gen-e2e` |
| **Mockup-getrieben** | bestehende Prototyp-HTMLs → in **eine** Spec kuratieren | manuell, dann gen-e2e |

**Brownfield-Disziplin (der SoR-Flip — Kern, sonst Drift):** `klickdummy-from-django` leitet aus einer
existierenden Django-App ein `screens-spec.yaml`-**Skelett** ab (URLConf→Screens, Models→Entities) —
ein **einmaliger Seed**. Ab da ist die **Spec der System-of-Record**, nicht mehr der Code: KD
optimieren = Spec wird die bessere Wahrheit; „Code anpassen wenn KD optimal" = der **Roundtrip**
(`gen-e2e` Parity) zieht den Code an die Spec. **Wiederholt** aus dem Code zu extrahieren kippt die
Wahrheit zurück zum Code = Drift → genau einmal seeden, dann führt die Spec.

> **ex-schutz als Brownfield-Fall (geerdet, C4):** `exschutzdokument` ist models-only → `from_django`
> liefert den **Entity-Katalog**, aber **keine Screens** (keine URLConf/Views). Die Screens stecken in
> den bestehenden Prototyp-HTMLs → Mockup-getriebener Einstieg: in **eine** Spec kuratieren, nicht 3
> lose HTMLs. So *hätte* ex-schutz entstehen sollen; die Konsolidierung (an #241 gehängt) holt das nach.

## Ledger
| id | Aussage | Typ | Evidenz / Falsifikation | Status |
|----|---------|-----|--------------------------|--------|
| L1 | Dubletten = Bypass: 2 ex-schutz-KDs sind spec-lose lose `.html`, nie durch UC/Spec gelaufen | Annahme→belegt | C1 (I1-NO-SPEC) + verifizierter risk-hub-Stand | bestätigt |
| L2 | risk-hubs `klickdummy-i1` ist schwächer als ADR-211 I1 — prüft Render-Gate, **nicht** Spec-Präsenz | Annahme→belegt | C2 (Makefile-Target iteriert `*.html`, kein Spec-Check) | bestätigt |
| L3 | Roundtrip ist die stärkste Anti-Dublett-Stufe, existiert als Mechanismus bereits (S13) | Entscheidung | C5 (sds-verwalten Rev 21 lief 3/3 grün) | gesetzt |
| L4 | ex-schutz ist NICHT roundtrip-reif — Code-Ende fehlt | Annahme→belegt | C4 (exschutzdokument models-only) + C3 (Spec ohne asserts) | bestätigt |
| R1 | Risiko: spec-first hart erzwingen bricht den Legacy-`.html`-Bestand vieler Repos | Risiko | Mitigation: Phase SUGGEST (warn) → FAIL erst nach Bestand-Migration | mitigiert |
| R2 | Risiko: Roundtrip-Gate verfrüht, wo nie Code entsteht | Risiko | Kill-Gate Phase-2; Roundtrip nur als Akzeptanz *wenn* Code landet | mitigiert |

## MVC (zwei Phasen entlang der Pipeline)
**Phase 1 — spec-first-Gate (jetzt, Mock-Stadium):**
- risk-hubs `klickdummy-i1` an ADR-211 I1 angleichen: zusätzlich zur Render-Prüfung **Spec-Präsenz
  verlangen** — jedes klickbare Artefakt braucht eine `screens-spec.yaml` (lose spec-lose `.html` →
  WARN, Phase SUGGEST; nach Bestand-Migration → FAIL). Nutzt die bestehende genesor-`validate.py`
  (`I1-NO-SPEC`, C1) als Quelle — keine zweite I1-Wahrheit.
- Legacy-lose-`.html`-Authoring-Pfad ausmustern: neue KDs nur als spec-dir.

**Phase 2 — Roundtrip-als-Akzeptanz (wenn Code existiert):**
- Sobald ein Topic den Code-Stand erreicht (Django-UI mit Routen), wird die S13-Parity-Bridge das
  Akzeptanz-Gate: Spec bekommt ausführbare asserts (data-testid-Kontrakt), die echte App bekommt die
  data-testid, Suite läuft gegen Renderer #2. Damit ist „Spec = SoR" bewiesen, nicht behauptet.

**Worked Example ex-schutz (Stand verifiziert):** steht bei `KD→mock` (Spec ohne asserts; UI = nur
Modelle, C3/C4). → Phase 1: zu **einem** spec-dir konsolidieren (Dublett einschmelzen+archivieren,
I3). Phase 2 = **#241** (explosionsschutz Live-Parity-Spec, ADR-054 Phase-B/C): asserts+data-testid+UI
bauen → erster ex-schutz-Roundtrip. CI-Roundtrip weiter durch **#278** (Schema-Bootstrap) blockiert.

## Kill-Gate + Threshold
Phase 1: Wenn die spec-first-Angleichung über 4 Wo / alle KD-Repos **0** spec-lose KDs meldet → kein
Bypass vorhanden, verwerfen. Phase 2: pro Topic erst aktiv, wenn Code existiert; sonst N/A (kein
Zombie-Gate). Exception-Budget bis 2026-08-15.

## Befunde + Adversariat (T2)
| # | Diabolus-Frage | Antwort |
|---|----------------|---------|
| AD1 | „spec-first ist schon ADR-211 I1 — warum ein Konzept?" | Weil risk-hubs *lokales* Gate I1 nicht durchsetzt (C2); das Konzept schließt die Lücke Policy↔Repo-Gate |
| AD2 | „Roundtrip-Gate ist Overkill, wo kein Code ist" | Genau deshalb 2-phasig: Phase 2 nur *wenn* Code landet (L4/R2) |
| AD3 | „Zweite Wahrheit?" | Nein — Phase 1 ruft genesor-`validate.py`, Phase 2 nutzt S13-Bridge; beide bestehend |
| AD4 | „Verschlimmert es I3?" | Nein — macht I3 durchsetzbar: nur spec-dirs, eine lebende Impl/Topic |

## Alternativen
| # | Alternative | Warum nicht |
|---|-------------|-------------|
| A1 | Dup-Topic-Detektor (erste Fassung dieses Konzepts) | Symptom-Fix; findet Dubletten *nachdem* der Bypass sie erzeugt hat |
| A2 | Nur Doku/Memory | Bypass bleibt offen; User-Feedback belegt, dass das nicht hält |

## Cross-Ref
Gate-Familie wie KONZ-platform-009 (cheapest-check, achimdehnert/platform#654). Auslöser: User-Feedback
2026-06-24 (Pipeline verhindert Dubletten → Bypass schließen). Memory `klickdummy-update-not-regenerate`.

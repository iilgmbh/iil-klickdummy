---
concept_id: KONZ-iil-klickdummy-008
title: KD-Co-Creation-Loop — realisierungsnahe Klickdummies mit lückenlosem E2E (greenfield + brownfield)
pipeline_status: idea
tier: T2
owner: Achim Dehnert
spec_refs: [risk-hub:klickdummy-spec-ex-schutz-konzept, example:klickdummy-spec-login]
adr_threshold: kein ADR (Erweiterung nach ADR-211-Muster) — bedingt Amendment, s. Tier-Note
review_by: 2026-08-03
kill_criteria: "Assert-Inferenz-Pilot auf ex-schutz erreicht in ≤2 Iterationen NICHT manifest.skipped==0, ODER die Mensch-Bestätigungsquote inferierter assert-Kandidaten liegt <50% (mehr Nacharbeit als Handschrift) → Assert-Inferenz-Komponente killen, zurück auf manuelle assert-Kuratierung."
superseded_by_spec: null
evidence_manifest:
  - {claim_id: C1, source_path: "risk-hub/klickdummy/ex-schutz-konzept/test_parity_ex_schutz_konzept.manifest.json", commit_or_pr: "local@2026-06-29", opened_in_session: true}
  - {claim_id: C2, source_path: "risk-hub/klickdummy/ex-schutz-konzept/screens-spec.yaml", commit_or_pr: "local", opened_in_session: true}
  - {claim_id: C3, source_path: "risk-hub/klickdummy/ex-schutz-konzept/index.html", commit_or_pr: "local", opened_in_session: true}
  - {claim_id: C4, source_path: "risk-hub/klickdummy/ex-schutz-konzept/_flow.input.mmd + _flow.view.md", commit_or_pr: "local", opened_in_session: true}
  - {claim_id: C5, source_path: "risk-hub/klickdummy/ex-schutz-konzept/_module-skeleton.from-django.yaml", commit_or_pr: "local", opened_in_session: true}
  - {claim_id: C6, source_path: "src/iil_klickdummy/from_django.py:62", commit_or_pr: "#82", opened_in_session: true}
  - {claim_id: C7, source_path: "src/iil_klickdummy/genesor/mermaid.py", commit_or_pr: "main", opened_in_session: true}
  - {claim_id: C8, source_path: "src/iil_klickdummy/gen_e2e.py (Skip-Kategorien, _q/_embed_json)", commit_or_pr: "#102/#104", opened_in_session: true}
  - {claim_id: C9, source_path: "src/iil_klickdummy/snippets/feedback-widget/widget.js", commit_or_pr: "main", opened_in_session: true}
created: 2026-07-03
---

## Tier — T2 (bedingt T3)

**T2**, weil: neue lokale Konvention + neue Boundary (Assert-Inferenz-Komponente) in **einem**
Repo (iil-klickdummy-Tooling), reversibel durch Nicht-Ausliefern der Komponente, validiert an
**einem** Brownfield-Testbett (ex-schutz). **Bedingt T3**, *falls* der Loop als plattform-weite
Autoren-Pflicht gesetzt wird — das wäre Cross-Repo-Impact + berührte den SoR-Autorenfluss aller
Adopter → **Amendment an ADR-211** nötig. Diese Aufstufung ist eine **nachgelagerte** Rollout-
Entscheidung, nicht Teil dieses Konzepts. Auto-Eskalations-Trigger „Security-Perimeter" (Codegen
aus Nutzer-Input) ist adressiert, nicht ignoriert (RISK-3).

## Kernthese

Der Engpass „realisierungsnaher KD mit lückenlosem E2E" ist **nicht** die Input-Erfassung (Mermaid-
Roundtrip + Feedback-Widget existieren beide), sondern die **Umwandlung Prosa-`check` → ausführbarer
`assert` mit `testid=`** — belegt durch ex-schutz: `parity_checks:4 / executable:0 / skipped:4`, alle
`no_assert` (C1). Der Loop wird tragfähig, wenn eine **Assert-Inferenz** diese Lücke halb-automatisch
schließt und das **gen_e2e-Manifest zum objektiven Exit-Gate** wird (`skipped==0 && fragile==0` gegen
Renderer #1 in Phase A, gegen Renderer #2 in Phase C).

## Ledger

| id | Aussage | Typ | Evidenz / Falsifikation | Status |
|---|---|---|---|---|
| L1 | ex-schutz hat 4 Prosa-Checks, 0 ausführbar (alle `no_assert`) — der Loop wurde nie zu E2E geschlossen | Annahme→belegt | C1 (Manifest 0/4), C2 (`{id: ex.steps-render, check: "…step-1 … step-10 sichtbar."}` ohne assert) | ✅ verifiziert |
| L2 | Die Shell trägt bereits `data-testid`-Anker → Assert-Inferenz hat Rohmaterial | Annahme→belegt | C3 (`grep -c data-testid` = 82: btn-back/save/next, tenant-bar, tpl-*) | ✅ verifiziert |
| L3 | Aber: Check-Vokabular (`step-1…step-10`) ≠ vorhandene testids (btn-*/tpl-*) → Inferenz ist **semantisches Mapping**, kein Textabgleich; Mensch-Bestätigung Pflicht | Risiko | C2 vs C3 (Vokabular-Divergenz) | ⚠️ offen (Kill-Gate-relevant) |
| L4 | Mermaid ist reine Ausgabe; kein mmd→spec-Parser existiert | Annahme→belegt | C7 (`mermaid.py` = „Mermaid-Graph-Emission"; `grep mmd→spec` = 0) | ✅ verifiziert |
| L5 | Der GitHub-Roundtrip (`_flow.input.mmd`/`_flow.view.md` → gh read-back → Spec) ist bereits die funktionierende Konvention und umgeht die iil.pet-Cloudflare-Read-back-Sperre | Entscheidung | C4 (`_flow.view.md`: „Stift-Icon → Branch mmds/… → ich lese via gh zurück → gieße in Spec (SoR)") | ✅ übernommen |
| L6 | Das Feedback-Widget postet In-KD-Feedback als GitHub-Issue (scope, DOM-Snapshot, sichtbare ID) → zweiter Input-Kanal | Annahme→belegt | C9 (`widget.js:21` POST api.github.com/…/issues; feedback_scope, domSnapshot) | ✅ verifiziert |
| L7 | Greenfield ohne Zielsystem: Suite läuft gegen die KD-Shell selbst (Renderer #1, `SPEC_RENDERER_BASE_URL` Default) → Phase-A-Vertrag | Entscheidung | C8 (gen_e2e HEADER: SPEC_RENDERER_BASE_URL Default localhost = Renderer #1) | ✅ übernommen |
| L8 | Phase-A-Grün ist **teilweise zirkulär** (Autor schreibt Asserts UND Shell) → beweist Vollständigkeit/Widerspruchsfreiheit, NICHT Korrektheit-gegen-Realität | Risiko | Design-Analyse (D) | ⚠️ als RISK-1 geführt |
| L9 | from_django parst nur `<app>/urls.py` → Brownfield-Skelett verfehlt html_urls.py/include/nested; startet jede Iteration unvollständig | Annahme→belegt | C6 (`from_django.py:62` `urls = app_dir / "urls.py"`), Issue #82, C5 (Skelett mit TODO-Asserts) | ✅ verifiziert |
| L10 | Spec bleibt Vertrauensgrenze — fatale Schema-Validierung vor Codegen bleibt AN; Loop-Input (Mermaid/Widget) wird kuratiert-in-die-Spec, nie roh in Codegen | Entscheidung | C8 (#102/#104 load_spec fatal validate + Escaping) | ✅ übernommen |
| L11 | **Pilot ex-schutz (#121):** von 4 Checks ist **1** präsenz-/zähl-inferierbar (`ex.steps-render`), **3** sind Verhaltens-/State-Aussagen (`gate-blocks`/`audit-trail`/`versioning`) — nicht per visible/text/count ausdrückbar. Zusätzlich sind Shell-testids JS-templated (`step-${…}`) → ein Zähl-Assert braucht einen stabilen Container-testid | Annahme→belegt | infer_asserts-Lauf gegen ex-schutz (#121), 1 Kandidat + 3 behavioral-manual | ✅ verifiziert |
| L12 | **Entscheidung C+A jetzt, B Roadmap:** C (Gate) + `kind`-Feld erzwingt Abdeckung ehrlich (executable-Checks brauchen assert; behavioral/nfr getaggt, nicht still). A assistiert die einfache Klasse. C allein wäre eine Sackgasse (behavioral-Checks nicht ausdrückbar → das `kind`-Feld ist der Klebstoff). B (State-DSL) schrumpft die behavioral-manual-Menge — gegated an Portfolio-Wiederkehr (F17-Disziplin), nicht jetzt | Entscheidung | User-Abnahme 2026-07-03; #121 | ✅ übernommen |

## MVC (konkreter Plan — Dateien / Felder / Gate)

**M1 — Assert-Inferenz (Herzstück, neue Komponente).**
`src/iil_klickdummy/infer_asserts.py` (neu): Eingabe = (Spec mit Prosa-`check`s) + (gerenderte
`shell.html`/`index.html`, testid-Inventar via HTML-Parse). Ausgabe = **Kandidaten-`assert`-Blöcke**
(`action`/`selector`/`expect` mit `testid=`), als Diff-Vorschlag in die Spec — **nie** auto-committed.
Heuristiken: Zähl-Sprache („alle N …") → `count`; „sichtbar" → `visible`; benannte ID im Check →
`testid=<id>`-Match gegen das Inventar. CLI: `klickdummy-infer-asserts <spec> <shell> --emit-diff`.
Mensch bestätigt/editiert jeden Kandidaten. **Kill-Gate-gekoppelt** (Bestätigungsquote).

**M2 — Manifest-Exit-Gate (nutzt Vorhandenes, keine neue Wahrheit).**
Kein neues Feld — das bestehende `gen_e2e`-Manifest (`executable`/`skipped`/`fragile_selectors`)
ist die Metrik. Neuer Gate-Helfer `klickdummy-parity-gate <manifest> [--phase A|C]`: Exit 0 nur bei
`skipped==0 && fragile_selectors==0` (Phase A) **plus** `parity(#2)==grün` (Phase C, via
`SPEC_RENDERER_BASE_URL`). Off-Ramp (I3) je Screen an dieses Gate gekoppelt.

**M3 — Zwei-Kanal-Input als Tool-Konvention (dokumentieren + kleiner Helfer).**
Die ex-schutz-Konvention (`_flow.input.mmd`/`_flow.view.md` + `mmds/`-Branch) als Cookbook-Abschnitt
in der `/klickdummy`-Skill + `klickdummy-mermaid-readback <kd-dir>` (gh read-back des mmd-Branch,
Diff gegen `screens[].next_screens` der Spec). Widget bleibt wie ist (C9); Doku benennt die
Arbeitsteilung Struktur(Mermaid)/Inhalt(Widget)/Wahrheit(Spec).

**M4 — from_django #82.**
`parse_urls` auf mehrere URL-Module (`*_urls.py`, `include()`-Auflösung) erweitern; Regressionstest
mit `html_urls.py`-Fixture.

## Kill-Gate

**Messbar:** Pilot der Assert-Inferenz (M1) auf ex-schutz. **Abbruch, wenn** in ≤2 Iterationen
`manifest.skipped` **nicht** auf 0 fällt **oder** die Mensch-Bestätigungsquote inferierter Asserts
<50% liegt (Kandidaten kosten mehr Nacharbeit als Handschrift). Dann: M1 verwerfen, nur M2/M3/M4
behalten (Gate + Konvention + Brownfield-Fix ohne Auto-Inferenz). **Exception-Budget:** genau 2
Pilot-Iterationen bis `review_by: 2026-08-03`; danach Entscheid oder Auto-`stale`.

## Befunde (inkl. Advocatus Diabolus)

| id | Rolle | Befund | Schwere | Mitigation |
|---|---|---|---|---|
| B1 | Diabolus (Doppelquelle) | Mermaid könnte zweite Wahrheit werden, wenn Edits nicht strikt einbahnig in die Spec fließen | mittel | Read-back ist one-way → Spec; die `.view.md` wird IMMER aus der Spec regeneriert, nie manuell gepflegt (L5) |
| B2 | Diabolus (SSoT nur behauptet) | Wenn inferierte Asserts direkt in der generierten `test_parity_*.py` editiert werden, driftet die Spec | hoch | Asserts leben in der Spec; die generierte Datei ist wegwerfbar (deterministisch re-gen); Drift-Gate `klickdummy-parity-drift` fängt Divergenz |
| B3 | Diabolus (Tool wird Boundary) | Assert-Inferenz, die still Asserts erfindet, wird zu unreviewter Autorität | hoch | `--emit-diff` + Pflicht-Mensch-Bestätigung; nie auto-commit; Bestätigungsquote ist Kill-Kriterium (L3) |
| B4 | Diabolus (formal erfüllt, praktisch umgangen) | Team schreibt triviale Asserts (`visible` auf `body`), um `skipped==0` zu erschleichen | mittel | `fragile_selectors==0` + `parity(#2)==grün` entlarvt Fake-Asserts: ein trivialer/falscher Assert wird gegen die echte App NICHT grün (M2 Phase C) |
| B5 | Diabolus (F18 verschlimmert?) | Auto-generierte Selektoren könnten fragil sein | mittel | Inferenz bevorzugt `testid=` (F23-Kontrakt Rev 22); `fragile_selectors==0` ist Teil des Gates |
| B6 | Maintainer-2028 | „sichtbar machen" (Manifest zeigt Skips) ist schwächer als „verhindern" | mittel | Gate macht `skipped==0` zur **Bedingung** des Off-Ramp (I3), nicht nur zur Anzeige — verhindert, nicht nur sichtbar |
| B7 | Maintainer-2028 | Neue Komponente `infer_asserts.py` = mehr Wartungsfläche; wenn Bestätigungsquote mittelmäßig, dauerhafte Halb-Automatik-Reibung | mittel | Kill-Gate an Bestätigungsquote; bei <50% wird die Komponente entfernt statt gepflegt |

## Alternativen

| Alt | Ansatz | Vorteil | Nachteil / verworfen? |
|---|---|---|---|
| A1 | **mmd→spec-Parser** (Mermaid als echter Autoren-Input, Neubau Grammatik+Validierung) | Mermaid wäre erste Autoren-Fläche | **verworfen:** vergrößert die diese Session gehärtete RCE-/Codegen-Fläche (C8), langsamer, dupliziert SoR; GitHub-Roundtrip (L5) liefert dasselbe ohne Parser |
| A2 | **Keine Assert-Inferenz**, rein manuelle assert-Autorenschaft | null neue Komponente | **verworfen:** der Engpass (0/4, C1) ist genau, dass Menschen die Asserts NICHT von Hand nachziehen — reine Doku ändert das empirisch nicht |
| A3 (OOTB) | **LLM-in-KD** generiert Asserts zur Render-Zeit im Browser | kein CLI-Schritt | zurückgestellt: Nicht-Determinismus bricht das Drift-Gate (deterministische Re-Gen ist Pflicht); als Idee im Backlog |

## Out-of-the-Box

Statt Asserts zu *inferieren*: die **Shell-Autoren-Vorlage** zwingt schon beim Schreiben jeden
`check` an eine `testid`-Referenz (Schema-`required`: ein Prosa-`check` ohne begleitendes
`assert` ist I1-invalid, sobald Phase A gilt). Verschiebt die Arbeit nach vorn statt nachträglich
zu inferieren. Nachteil: härtere Autoren-Reibung am Anfang (Greenfield-Skizze wird langsamer).
Nicht verworfen — Kandidat für Phase-A-Verschärfung *nachdem* die Inferenz die Alt-Bestände
(ex-schutz) aufgeräumt hat.

## Entscheidung + 30/60/90

**Entscheidung:** T2 annehmen. Bauen in Reihenfolge **M4 → M1 (Pilot ex-schutz) → M2 → M3**,
greenfield als Primär-Zielfluss, ex-schutz als Validierungs-Testbett (einziger Ort mit echtem
Renderer #2 auf risk-hub :8090). **Bauen erst nach User-Konzept-Abnahme** (ADR-251-Muster).

- **30:** M4 (from_django #82) + M1-Prototyp; Pilot-Lauf auf ex-schutz → misst Bestätigungsquote + ob `skipped` fällt. Kill-Gate-Entscheid.
- **60:** M2 (Parity-Gate-Helfer) + I3-Kopplung je Screen; ex-schutz erreicht `skipped==0` gegen Renderer #1 und wird gegen :8090 (Renderer #2) gefahren.
- **90:** M3 (Zwei-Kanal-Konvention in `/klickdummy`-Cookbook); ein Greenfield-Durchlauf end-to-end (Skizze → Mermaid → Spec → Shell → Phase-A-grün → Übergabe als E2E-Spec).

**Kill-Gate** (s.o.) ist die Abbruchschwelle; `review_by: 2026-08-03` erzwingt Entscheid oder Auto-`stale`.

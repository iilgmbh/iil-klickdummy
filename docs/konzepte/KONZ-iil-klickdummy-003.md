---
concept_id: KONZ-iil-klickdummy-003
title: Strategie für IIL-Genesor — Self-Onboarding & Postgres-Migration (Entscheidungsvorlage)
pipeline_status: idea
tier: T3
owner: achim                      # Annahme (Repo-/Plattform-Owner) — bestätigen
spec_refs: []                     # betrifft Architektur/Strategie des Renderers, nicht eine Spec
conforms_to: platform:ADR-211
adr_threshold: org-weiter ADR     # SoR-Reversal-Frage berührt ADR-211 → Amendment prüfen, BEVOR umgesetzt
review_by: 2026-08-30             # created + 90 Tage
superseded_by_spec: null
kill_criteria: "Modul-Split (Empf-1) wird begonnen, aber ein golden-HTML-Diff zeigt nach dem Globals→Config-Schritt eine nicht-erklärbare Byte-Abweichung in genesor.html, die >1 Tag Debugging kostet → Split stoppen, Globals-Refactor reverten, Monolith behalten + nur build_genesor_html intern zerlegen"
evidence_manifest:
  - {claim_id: C1, source_path: "iil-klickdummy/src/iil_klickdummy/lineage.py:6355 (wc), 84 defs (grep) = 69% von 9218", commit_or_pr: "session-scan 2026-06-01", opened_in_session: true}
  - {claim_id: C2, source_path: "iil-klickdummy/src/iil_klickdummy/lineage.py:10 (Docstring: 'meiki:ADR-035, Meta-KD, class: mock')", commit_or_pr: "working-tree@main", opened_in_session: true}
  - {claim_id: C3, source_path: "iil-klickdummy: kein klickdummy/-Dir, keine eigene screens-spec.yaml (find leer)", commit_or_pr: "session-scan 2026-06-01", opened_in_session: true}
  - {claim_id: C4, source_path: "iil-klickdummy/src/iil_klickdummy/lineage.py:55-76 (Globals), :6072 (global …-Mutation in main)", commit_or_pr: "working-tree@main", opened_in_session: true}
  - {claim_id: C5, source_path: "iil-klickdummy/src/iil_klickdummy/lineage.py:2696-3906 (build_genesor_html ~1210 Z., eine Funktion)", commit_or_pr: "working-tree@main", opened_in_session: true}
  - {claim_id: C6, source_path: "snippets/genesor-sync/setup-project.sh:4-5 (GitHub-Projects=SoR, Counter-A 2026-05-24)", commit_or_pr: "working-tree@main", opened_in_session: true}
  - {claim_id: C7, source_path: "src/iil_klickdummy/discovery_push.py:9-11 (pgvector = abgeleiteter Index, KEIN SoR)", commit_or_pr: "working-tree@main", opened_in_session: true}
  - {claim_id: C8, source_path: "src/iil_klickdummy/lineage.py:6292 (uc-export.json = statisches Read-Model)", commit_or_pr: "working-tree@main", opened_in_session: true}
  - {claim_id: C9, source_path: "scan ~/github: 35 specs / 7 repos; ausschreibungs-hub 12 + risk-hub 11 = 66%", commit_or_pr: "session-scan 2026-06-01", opened_in_session: true}
  - {claim_id: C10, source_path: "tests/: test_smoke 34 + test_gen_e2e 12 + test_discovery_push 16 = 62 Tests", commit_or_pr: "session-scan 2026-06-01", opened_in_session: true}
  - {claim_id: C11, source_path: ".github/workflows/ci.yml (pip install pytest pyyaml jsonschema; KEIN Postgres/Secret/Service-Container) — Maintainer-Gutachten, nicht in dieser Session re-geöffnet", commit_or_pr: "H (Gutachter-Beleg)", opened_in_session: false}
created: 2026-06-01
off_ramp:                         # wird ADR-211-Amendment-Prüfung + Refactor-Issues in iil-klickdummy
---

# KONZ-iil-klickdummy-003 — Strategie für IIL-Genesor

> T3-Entscheidungsvorlage. Erzeugt mit `/konzept`. Adversariales Fan-out: drei unabhängige
> Gutachter (Steelman / Advocatus Diabolus / Maintainer-2028), die sich nicht sahen, danach
> Synthese + Konfliktmatrix. Verwandt: [[spec-as-sor-keystone]], KONZ-002 (Repo-Einstieg).

## 1 Executive Summary
Zwei gebündelte User-Ideen — **(A) genesor selbst als Klickdummy onboarden**, **(B) Umstieg auf
Python-App + Postgres** — werden in ihrer wörtlichen Form **beide abgelehnt**, ihr gemeinsamer
wahrer Kern aber übernommen. Diagnose der User-Intuition („Mächtigkeit ohne Strategie → ausufert")
ist **korrekt und belegt**: `lineage.py` = 6355 Z. / 84 Funktionen = **69%** des Pakets (C1), eine
Funktion (`build_genesor_html`) allein ~1210 Z. (C5). Aber **keine** der beiden Ideen trifft diesen
Schmerz; B verschlimmert ihn. Empfehlung: **(1) den Monolithen entschärfen** (Globals→Config, dann
Modul-Split, abgesichert durch golden-HTML-Diff), **(2) schmales, ehrliches Dogfooding** (eigene
Spec als Doku + gen_e2e-Parity-Ziel, *neue Rolle statt `class: mock`*), **(3) Postgres als
getriggerten Off-Ramp** definieren (Trigger-Metrik, keine Migration jetzt).

## 2 Scope & Evidenzbasis
Betroffen: nur `iil-klickdummy` (der genesor-Generator). Berührt **ADR-211** (Spec=SoR) bei der
SoR-Frage → `adr_threshold: org-weiter ADR` (Amendment prüfen). Evidenz: `evidence_manifest`
C1–C11; C11 ist **H** (Gutachter-Beleg, in dieser Session nicht re-geöffnet).

## 3 Infrastruktur-Fit (verifiziert)
- **Static-Modell:** genesor scannt `~/github`, rendert HTML, nginx liefert — null Runtime, keine DB.
- **Datenschichten heute (schon 3–4):** GitHub-Projects = deklarierter **SoR** (C6); pgvector =
  **ausdrücklich kein SoR**, abgeleiteter Index (C7); Filesystem-Scan = Render-Input;
  `uc-export.json` = statisches Read-Model (C8).
- **Skala:** 35 Specs / 7 Repos, Long-tail 66% in 2 Repos (C9).
- **Test-Netz:** 62 Tests (C10) — taugt als Refactor-Sicherheitsnetz, v.a. bei byte-diffbarem HTML.

## 4 Steelman (stärkste Pro-Version, bevor kritisiert wird)
- **A:** Der Docstring behauptet „Meta-KD, class: mock" (C2), aber es gibt keine Spec (C3) — eine
  **Behauptung ohne Artefakt**, also genau der I1-Verstoß, den genesor bei anderen ahndet. Onboarding
  repariert die Glaubwürdigkeitslücke und unterwirft den Sprawl der Spec-Disziplin; `gen_e2e` würde
  Parity-Regressionsschutz für die genesor-UI liefern. Additive, risikoarme Maßnahme.
- **B:** Die Render-Pipeline *ist faktisch schon eine Daten-Pipeline mit Schreibpfad* (Drift-Detektion,
  Coverage-Joins, Git-History-Reads, Publish-Mutationen) + `uc-export.json` + `discovery_push`-v1.6-
  Envelope (registry_key, spec_sha256, tombstone) = „ein DB-Schema in Verkleidung". Postgres wäre
  nicht der Bruch mit der Architektur, sondern ihr Eingeständnis.

## 5 Konzeptdefinition (die empfohlene Lösung)
Nicht A, nicht B wörtlich — sondern drei zusammengesetzte Maßnahmen, abgeleitet aus der
Gutachter-Synthese (§6): **Monolith entschärfen → schmaler Dogfood → Postgres-Trigger statt -Migration.**

## 6 Adversariale Analyse — Konfliktmatrix der drei Gutachter

| Streitpunkt | Steelman | Advocatus Diabolus | Maintainer-2028 | Auflösung (Synthese) |
|---|---|---|---|---|
| **Ist A überhaupt machbar?** | Ja, *jetzt* — aber als `class: spec-demo`, nicht `mock` | **Nein** (A-1, kritisch): genesor hat kein „Renderer #2" → Off-Ramp-Gate `static→parity-green` ist **strukturell unerreichbar**; A-2: eigener Validator würde `SUNSET-MISSING` werfen | Nur als **billige Doku-Spec**; „UI-aus-Spec-Engine" = negativ (betoniert den Hotspot) | **Wörtliches ADR-211-Onboarding ablehnen** (Diabolus A-1/A-2 entscheidend). **Schmales Dogfooding annehmen:** eigene Spec als Doku + gen_e2e-Parity-Ziel, **neue Rolle `self-hosted-tool`**, NICHT `class: mock`. Docstring-Falschaussage (C2) so oder so korrigieren. |
| **Klasse/Etikett** | spec-demo | `class: mock` ist Lüge im Index, fehlsteuert Discovery-Konsumenten (A-4) | mock falsch | Konsens: `mock` ist falsch. Keine KD-Klasse — eigene Rolle. |
| **Prämisse von A** | (nicht thematisiert) | **Neuer Fakt:** Docstring hängt an `meiki:ADR-035`, nicht ADR-211 (C2) → A baut auf ADR-Verwechslung | (nicht thematisiert) | In die Empfehlung aufnehmen: Self-Bezug auf eine ADR fixieren, die zum Tool-Charakter passt. |
| **Ist B machbar/sinnvoll?** | Bedingt — „~2 Größenordnungen zu früh", Trigger scharf stellen | **Nein** (B-2 kritisch: falscher Flaschenhals; B-1: SoR-Reversal/reopened decision; B-3: 35 Items; B-4: TCO-Sprung) | **Klar nein** — tauscht ein nicht-existentes Betriebsproblem gegen 5 neue stateful Pflichten | **B jetzt ablehnen.** Trigger definieren (§13). Konsens über alle drei. |
| **Was lindert den 6355-Z.-Schmerz?** | Read-Model-Schema hinter Repository-Interface ziehen | Weder A noch B (A-5) | **Globals→Config, dann Modul-Split** (neuer Fakt C4: Split heute unmöglich wegen mutierter Globals); golden-HTML-Diff als Netz | **Dies ist die eigentliche Empfehlung.** Maintainer liefert die *Reihenfolge* (Globals zuerst), Steelman die *Zielform* (Repository-Interface fürs Read-Model). |

**Dokumentierter Dissens:** Der *einzige* echte Konflikt ist die Machbarkeit von A. Steelman „jetzt
tun", Diabolus „strukturell unmöglich", Maintainer „nur billig-doku". Aufgelöst durch Trennung:
*wörtliches* Onboarding (Diabolus gewinnt — abgelehnt) vs. *schmales* Dogfooding mit neuer Rolle
(Steelman+Maintainer-tragbar — angenommen). Bei B: **kein Dissens** — alle drei lehnen jetzt ab.

## 7 Deep-Dive — der wahre Flaschenhals (C4, C5)
Der Grund, warum `lineage.py` nicht zerschnitten *werden kann*, ist nicht Größe allein, sondern
**Konfiguration über mutierte Modul-Globals**: `REPOS_ROOT, GENESOR_OUT, BASE_URL, SKIN_BASE,
VENDORED_REPOS` (Z. 55–76) werden in `main()` per `global …` überschrieben (Z. 6072); alle 84
Funktionen lesen diesen versteckten Zustand. Jeder Split ohne vorherige Entkopplung bricht stumm.
Daher die **Pflicht-Reihenfolge**: (1) Globals → `@dataclass GenesorConfig`, durchgereicht; (2) dann
Split entlang der ~8 Verantwortungen (`discovery / render_html / mermaid / introspect_django /
publish / validate / export / cli`); (3) `build_genesor_html` (~1210 Z.) in Sub-Renderer zerlegen.
Sicherheitsnetz: golden-file-HTML-Diff der erzeugten `genesor.html` (Static-Vorteil — eine
DB-App hätte dieses Netz nicht).

## 8 Alternativen (verworfen)
- **Alt-1 — A wörtlich (KD-Onboarding mit `class: mock` + `sunset_after`):** verworfen, Diabolus
  A-1/A-2 (Off-Ramp unerreichbar, Self-Fail im eigenen Validator).
- **Alt-2 — B jetzt (Postgres-App):** verworfen, falscher Flaschenhals (B-2) + SoR-Reversal (B-1) +
  TCO-Sprung (B-4); einstimmig.
- **Alt-3 — nichts tun:** verworfen, Sprawl wächst weiter unter falschem Etikett (gemeinsamer
  Gutachter-Kern: Diskrepanz deklarierte Identität ↔ gewachsene Realität).

## 9 Out-of-the-Box
Der wertvolle Kern *beider* User-Ideen ist dieselbe Diagnose aus zwei Richtungen: **das Tool hat
seine deklarierte Identität überholt.** Statt es unter falschem Etikett (Wegwerf-KD / mock /
Static-Generator) weiterwachsen zu lassen, wird die Identität **ehrlich neu deklariert**:
genesor = *spec-getriebenes, self-hosted Tool über einem kanonischen Read-Model-Schema*. Damit wird
Steelmans „DB-Schema in Verkleidung" zur **schema-stabilen Repository-Schnittstelle** (Empf-3) —
und falls je ein B-Trigger feuert, ist Postgres dann kein Rewrite, sondern ein Schema-Backfill.

## 10 Befunde
- **F1 (kritisch):** A wörtlich verletzt I3 konstruktiv (kein Off-Ramp-Ziel). Beleg: Diabolus A-1.
- **F2 (hoch):** Self-Onboarding mit `class: mock` triggert den eigenen Validator `SUNSET-MISSING`. A-2.
- **F3 (hoch):** B löst den realen Schmerz (Code) nicht, importiert SoR-Reversal + TCO. B-1/B-2/B-4.
- **F4 (hoch):** Splittbarkeit blockiert durch mutierte Globals (C4) — Refactor-Reihenfolge zwingend.
- **F5 (mittel):** Docstring-Falschaussage `class: mock` / `meiki:ADR-035` (C2) ist heute schon Drift.

## 11 Top-5-Risiken
1. **Refactor bricht Output stumm** (Globals-Kopplung) → Mitigation: golden-HTML-Diff + 62 Tests (C10), Globals zuerst.
2. **Scope-Creep „schmaler Dogfood" → „UI-aus-Spec-Engine"** → Mitigation: Rolle `self-hosted-tool`, Spec ist Doku/Parity-Ziel, kein Render-Input.
3. **B schleicht sich später ohne ADR-Amendment ein** → Mitigation: Trigger-Metrik + ADR-211-Amendment als Gate dokumentiert.
4. **Read-Model-Schema wird zweiter SoR** → Mitigation: explizit „abgeleitet", wie pgvector (C7).
5. **Konzept verstaubt** → `review_by` 2026-08-30; ohne Pflege Auto-`stale` (I3).

## 12 Empfehlungen (konkret)
- **Empf-1 (hoch, sofort):** `lineage.py` entschärfen — (a) Globals (Z. 55–76/6072) → `@dataclass
  GenesorConfig`; (b) Split in ~8 Module; (c) `build_genesor_html` in Sub-Renderer. Netz: golden-HTML-Diff.
- **Empf-2 (niedrig, optional):** Schmales Dogfooding — eigene `screens-spec.yaml` als **Doku +
  gen_e2e-Parity-Ziel**, Rolle `self-hosted-tool` (nicht `class: mock`); Docstring C2 korrigieren.
- **Empf-3 (mittel):** Das schon existierende Read-Model (`uc-export.json` C8 + `discovery_push`-
  Envelope) zur **schema-stabilen Repository-Schnittstelle** erheben — entkoppelt Logik vom Storage,
  ist die Brücke falls je ein B-Trigger feuert. Falls Lese-Last je beißt: **SQLite-FTS vor Server**.
- **Empf-4 (Ein-Zeilen-Entscheidung):** Postgres-Trigger dokumentieren (siehe §13). Keine Migration jetzt.

## 13 Entscheidung + Kill-Gate + 30/60/90
- **Entscheidung:** A & B wörtlich abgelehnt; Empf-1…4 angenommen. **B braucht ADR-211-Amendment, bevor es je umgesetzt wird.**
- **Postgres-Trigger (B-Off-Ramp scharf):** umsetzen erst wenn **mind. einer** feuert —
  (a) >300 KDs **ODER** Voll-Build >60 s; (b) zweiter Live-Konsument *fragt ab* statt `uc-export.json` zu lesen;
  (c) persistente Mutation muss über Builds gehalten werden (kollaboratives Editieren statt git-Specs);
  (d) transaktionale/konkurrenzsichere Provenance-Garantien nötig.
- **Kill-Gate (messbar):** siehe Frontmatter `kill_criteria` (golden-HTML-Diff-Abweichung >1 Tag → Split stoppen, Globals reverten).
- **30/60/90:** **30** — Empf-1a (Globals→Config) + golden-HTML-Baseline. **60** — Empf-1b/1c (Split) + Empf-2 (Doku-Spec). **90** — Empf-3 (Repository-Interface), `review_by`-Re-Check, Trigger-Status prüfen.

## Ehrliche Enforcement-Grenze
`/konzept` schreibt `review_by`/`kill_criteria`/`superseded_by_spec`, erzwingt sie aber nicht —
solange kein Lifecycle-Gate sie liest, ist die Kontrolle ein Review-Gate, kein Exit-Code.

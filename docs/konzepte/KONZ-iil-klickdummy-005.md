---
concept_id: KONZ-iil-klickdummy-005
title: Per-Repo-Sektion „Workflow → KD → UC" — kanonische 2-Ebenen-Sektion + optionale Modul-Ebene
pipeline_status: idea
tier: T2                          # bedingt T3 — nur wenn H1-Kante ein org-weites Spec-Feld braucht
owner: achim                      # Annahme (ADR-211 deciders:[achim]) — bestätigen
spec_refs: []                     # Renderer-Komposition; berührt Spec NUR im T3-Zweig (Opt B)
conforms_to: platform:ADR-211
adr_threshold: kein ADR           # renderer-lokal, additiv, reversibel — Amendment NUR im T3-Zweig
review_by: 2026-09-16             # created + 90 Tage; ohne Pflege Auto-stale (I3)
superseded_by_spec: null
kill_criteria: "MVC-Pilot zeigt: die komponierte Per-Repo-Sektion aus Repo-Lineage + Screen-Lineage bringt gegenüber der heutigen flachen Tabelle keinen sichtbaren UAT-Mehrwert → Komposition verwerfen, flache Tabelle + Empty-States behalten. SEPARATES Kill für die optionale Modul-Ebene: Route-Ableitung (Opt A) am Django-Pilot erreicht NICHT gleichzeitig (i) ≥50% KD→Modul-Kanten-Coverage UND (ii) ≥90% Präzision UND (iii) 0 schwere Fehlzuordnungen → Modul-Ebene NICHT via neuem Spec-Feld erzwingen; als optionalen Modul-Badge belassen oder streichen."
external_review:
  - {round: 1, date: 2026-06-18, provider: extern (Cross-Provider), file: "~/shared/adr-handoff-KONZ-iil-klickdummy-005-2026-06-18.md", verdict: "überarbeiten", applied_recs: "REC-1..11 valid, REC-12 out-of-scope"}
evidence_manifest:
  - {claim_id: C1, source_path: "src/iil_klickdummy/genesor/render_genesor.py:29 (_render_kd_detail), :1223 (build_genesor_html)", commit_or_pr: "working-tree@main", opened_in_session: true}
  - {claim_id: C2, source_path: "src/iil_klickdummy/genesor/mermaid.py:230 (emit_screen_lineage — 'Screen-Ablauf innerhalb eines KDs')", commit_or_pr: "working-tree@main", opened_in_session: true}
  - {claim_id: C3, source_path: "src/iil_klickdummy/genesor/render_lineage.py (generate_per_repo_lineages → lineage-<repo>.html; Click-Direktiven für klickbare Mermaid-Knoten)", commit_or_pr: "working-tree@main", opened_in_session: true}
  - {claim_id: C4, source_path: "src/iil_klickdummy/genesor/introspect_django.py:_inspect_django_models (AST apps/*/models.py → {app_label.ModelName})", commit_or_pr: "working-tree@main", opened_in_session: true}
  - {claim_id: C5, source_path: "src/iil_klickdummy/schemas/module-manifest.schema.json (MEiKI Fachverfahren — repo-spezifisch, nicht generisch)", commit_or_pr: "working-tree@main", opened_in_session: true}
  - {claim_id: C6, source_path: "genesor/index.html:2719-2733 (SPA-Hash-Router facets repo/org/class/role) — flache gefilterte Tabelle, keine Per-Repo-Sektion", commit_or_pr: "iil-pet-portal working-tree", opened_in_session: true}
  - {claim_id: C7, source_path: "screens-spec.schema.json — KEIN module:-Feld (KD→Modul-Zuordnung existiert heute nicht explizit)", commit_or_pr: "working-tree@main", opened_in_session: true}
  - {claim_id: C8, source_path: "docs/konzepte/KONZ-iil-klickdummy-004.md (Story↔UC — 'story' = geführte KD-Tour, NICHT H2)", commit_or_pr: "working-tree@main", opened_in_session: true}
created: 2026-06-18
---

# KONZ-iil-klickdummy-005 — Per-Repo-Sektion „Workflow → KD → UC"

> T2-Decision-Ledger (`/konzept`). Verwandt: KONZ-003 (genesor-Strategie), KONZ-004 (Story↔UC),
> platform:ADR-211 (Spec=SoR). Auslöser: UAT (pg-hub) + Owner-Klärung am Artefakt
> `lineage-meiki-hub.html`. **Rev 2 (2026-06-18):** Hierarchie-Mapping korrigiert (H2 = Repo-Lineage)
> + externes Cross-Provider-Review Runde 1 eingearbeitet (REC-1..11; siehe §Externes Review).

## Tier-Gate
**T2 (bedingt T3).** Per-Repo-Sektion = Renderer-Komposition bestehender Lineage-Artefakte,
additiv/reversibel → T2. **Auto-Eskalation zu T3 GENAU DANN**, wenn die Modul-Ebene ein neues
org-weites Spec-Feld (`module:`) braucht, um die Modul→KD-Kante zu ziehen (= ADR-211-Schema-
Amendment, SoR über alle Repos). Billigster Check: Django-Pilot mit Route-Ableitung — erreicht sie
Coverage **und** Präzision (siehe Kill-Gate)? Bis dahin: kein Spec-Feld, kein T3.

## Was „Workflow" hier bedeutet (Begriffsklärung — REC-2)
„Workflow" im UI ist **kein** Geschäftsprozess-Modell und **nicht** die KD-Tour („story", KONZ-004).
Gemeint ist der **Lineage-/Navigationszusammenhang**: wie Repo, KDs, Screens (und optional Module)
strukturell zusammenhängen, dargestellt als verlinkte Mermaid-Diagramme. (Disambiguierung: auch
`class: story` aus ADR-211 = Prod-Safety-Pattern/Storybook ist hier irrelevant.)

## Kernthese (1 Satz)
Die gewünschte „Workflow"-Ansicht ist **keine** spekulative 3-Ebenen-Hierarchie, sondern eine
**kanonische 2-Ebenen-Repo-Sektion** aus bereits existierenden Artefakten — **Repo-Lineage**
(`lineage-<repo>.html`) + **Screen-Lineage** — **optional ergänzt** um eine **evidenz-gegatete
Modul-Ebene**; der reale Schmerz ist die fehlende **Komposition zu EINER Sektion** plus
ersatzloses Verschwinden von Blöcken (= wahrgenommene „Inkonsistenz") → Lösung ist **Komposition +
maschinenprüfbarer Empty-State-Contract**, nicht ein neues Datenmodell.

## Reframing nach Review (REC-1, REC-7 — Owner-Bestätigung nötig)
Die ursprüngliche Owner-Rahmung war ein „3-stufiger Drill-down (H1→H2→H3)". Das externe Review
(AD-7) und die Erdung zeigen: eine **nominelle 3-Ebenen-Symmetrie** verspricht eine Struktur, die
die Datenlage **nicht** hergibt (H1 fehlt bei den meisten Repos). Daher umgerahmt zu **2 Ebenen +
optionale Modul-Ebene**. Die H1/H2/H3-Begriffe bleiben als **Denkmodell** gültig, aber das
UI verspricht keine Symmetrie. **⚠ Dies ändert die vom Owner gegebene Rahmung — vor Umsetzung
bestätigen.** Die offene Referenz „3 Hierarchien wie bereits besprochen" wird als **UAT-Hypothese**
behandelt; Pilot-Leitfrage ist **nicht** „Ist H1 korrekt umgesetzt?", sondern „**Brauchen Nutzer
die Modul-Ebene überhaupt, oder reicht Repo-Lineage + Screen-Lineage mit besserer Komposition?**".

## Das Modell (Owner-bestätigt am Artefakt `lineage-meiki-hub.html`)
Navigationszusammenhang grob → fein, als verlinkte Mermaids:

| Ebene | Was | Artefakt | Status |
|-------|-----|----------|--------|
| **Modul** (optional, ehem. H1) | Modulschaubild — Mermaid der Module; Knoten verlinkt in die Repo-Lineage | — | neu, gegated, opt-in |
| **Repo-Lineage** (H2) | KDs + ihre Beziehungen (= `lineage-meiki-hub.html`) | `lineage-<repo>.html` (C3) | ✅ existiert |
| **Screen-Lineage** (H3) | Ablauf innerhalb eines KD | `screen-lineage-<repo>-<kd>.html` (C2) | ✅ existiert |

Klick-Mechanik existiert bereits (Click-Direktiven, C3) → Verlinkung braucht kein neues Framework.

## Erdungs-Befund (Root-Cause)
Zwei Ebenen existieren, nur die Komposition fehlt:
- **Modul-Ebene:** Datenquellen nur `introspect_django` (Django-Apps `app_label`) bzw.
  `module-manifest` (Spezial-Repo); **kein generischer Pfad**; **KD→Modul-Kante fehlt** (kein
  `module:`-Feld, C7).
- **Repo-Lineage:** funktioniert, ist aber standalone, noch nicht als Sektion eingebettet.
- **Screen-Lineage:** funktioniert.
- **Komposition:** fehlt (flache Tabelle, C6).

## Ledger

| id | Aussage | Typ | Evidenz / Falsifikation | Status |
|----|---------|-----|--------------------------|--------|
| L1 | Repo-Lineage (`lineage-<repo>.html`) = Mittelschicht — existiert, Owner-bestätigt | Entscheidung (D) | C3 + Owner-UAT; „H2=story" verworfen | beschlossen |
| L2 | Screen-Lineage (`screen-lineage-*.html`) = Detailschicht — existiert | Entscheidung (D) | C2 | beschlossen |
| L3 | Sektion = Repo-Lineage + Screen-Lineage **jetzt** komponieren; reiner Reuse | Entscheidung (D) | C2/C3; A1 (CSS) zu schwach | vorgeschlagen |
| L4 | Modul-Ebene ist **optional, evidenz-gegated** (Django-only, ≥2 Module), NICHT für jedes Repo (YAGNI) | Entscheidung (D) | C4/C5/C7; Review AD-7/REC-1 stützt | beschlossen |
| L5 | Modul→KD-Kante via Route-Ableitung (Opt A); kein neues Spec-Feld; bleibt T2 | Annahme | C7; Falsifikation = Kill-Gate (ii)/(iii) | **offen — entscheidet Tier** |
| L6 | „Inkonsistenz" = ersatzloses Verschwinden von Blöcken, nicht abweichende Reihenfolge | Befund | C6 + Session-Render-Vergleich | belegt |
| L7 | Maschinenprüfbarer Empty-State je Slot (REC-6/REC-11): Status ∈ {`present`, `empty-valid`, `missing-input`, `not-applicable`}; fehlende Modul-Ebene = `not-applicable` mit schlankem Hinweis, KEINE leere Diagramm-Box | Entscheidung (D) | Alternative: Slots ausblenden = L6 | vorgeschlagen |
| L8 | Per-Repo-**Sektion** als neuer Render-Pfad im `#/repo/<slug>`-Zustand | Entscheidung (D) | C1/C6 | vorgeschlagen |
| L9 | **View-Model/Adapter** für die Sektion (REC-3/REC-9): Standalone-Lineage NICHT als HTML-Fragment direkt einbetten; Modul-Daten über austauschbare **Provider** (Django-Provider, Manifest-Provider), kein Repo-Typ-Switch im Renderer | Entscheidung (D) | KONZ-003 (Monolith nicht weiter verästeln); M28-1/M28-2 | vorgeschlagen |
| L10 | Route-abgeleitete Kanten werden als **`inferred`** markiert (Grund + Confidence-Klasse), im UI sichtbar von Spec-Kanten unterschieden (REC-4) | Entscheidung (D) | M28-3; ADR-211 (keine Pseudo-SoR) | vorgeschlagen |

## MVC (kleinster pilotierbarer Schnitt)
1. **Ein Django-Pilot-Repo** (≥2 KDs, echte Screen-Flows; Kandidat `risk-hub`).
2. `_render_repo_section(repo, records)` über ein **View-Model** (L9) für den `#/repo/<slug>`-Zustand,
   feste Schichtung: **Workflow** (Repo-Lineage + Screen-Lineage-Links) → **KD** (Mockup-Links) →
   **UC** (`uc-<repo>.html`-Links).
3. **Modul-Ebene nur am Django-Pilot** testen: `introspect_django` → Modul-Knoten; KD→Modul-Kante
   via Route-Ableitung (Opt A), Kanten als `inferred` markiert (L10). Render nur bei ≥2 Modulen.
4. **Empty-State-Contract maschinenprüfbar** (L7): jeder Slot trägt einen Status; fehlende
   Modul-Ebene = `not-applicable` + Hinweis „Keine belastbare Modul-Lineage für dieses Repo erkannt".
5. Golden-HTML-Baseline + **semantische Assertions** (REC-8): Slot-Reihenfolge `Workflow→KD→UC`,
   korrekte Linkziele (Repo-Lineage/Screen-Lineage/KD/UC), Empty-State-Gründe, An-/Abwesenheit
   der Modul-Ebene.

## Kill-Gate + Exception-Budget
- **Kill (messbar):** siehe Frontmatter — (a) Sektion bringt am Pilot keinen UAT-Mehrwert → verwerfen;
  (b) Modul-Ebene: Route-Ableitung erreicht NICHT gleichzeitig ≥50% Coverage, ≥90% Präzision,
  0 schwere Fehlzuordnungen (REC-5) → nicht per Spec-Feld erzwingen.
- **Exception-Budget mit Decision-Check (REC-10):** Modul-Ebene generisch fehlend bis **2026-08-15**;
  an diesem Datum **explizite Entscheidung** (nicht stiller Dauerzustand): (1) streichen,
  (2) als optionalen Modul-Badge stabilisieren, oder (3) mit T3/ADR-211-Amendment neu bewerten.

## Befunde (inkl. Advocatus Diabolus) + Alternativen

**Befunde**
- **B1 (hoch):** „Workflow neu bauen" würde Repo-/Screen-Lineage (C2/C3) ignorieren und Doppelmodelle
  schaffen (gegen ADR-211 SoR). → Komponieren.
- **B2 (hoch, YAGNI):** Modul-Ebene „für jedes Repo" = hoher Aufwand ohne universelle Daten; bei
  Repos ohne Modulstruktur eine leere/1-Knoten-Ebene = negativer Nutzen. → optional/opt-in.
- **B3 (hoch):** Modul→KD-Kante ist der Engpass (nicht die Modul-Liste); Route-Ableitung darf nicht
  wie SoR wirken → `inferred`-Markierung (L10).
- **B4 (mittel, Review M28-2):** Ohne View-Model verklebt die Sektion Standalone-HTML-Fragmente →
  Monolith-Verästelung. → L9.

**Advocatus Diabolus (intern + extern Runde 1)**
- *Doppelquelle?* Modul-`module:`-Feld → JA Doppelquelle zu Django-Code; deshalb L5/L10.
- *Symmetrie-Falle?* „3 Ebenen sind logisch" verführt zum Vollausbau (AD-7) → B2/Reframing.
- *Pseudo-SoR?* Route-Kanten könnten autoritativ wirken (M28-3) → L10 `inferred`.
- *„Tool→Boundary"?* Per-Repo-Sektion könnte „jedes Repo braucht Workflow" implizieren →
  Empty-State `not-applicable` ist valide, kein Drift-Finding.

**Alternativen**
| Alt | Inhalt | Warum nicht (jetzt) |
|-----|--------|---------------------|
| A1 | Nur CSS-Gruppierung der flachen Tabelle | Löst L6 nicht; kein Platz für Modul-Ebene |
| A2 (Opt B) | Org-weites Spec-Feld `module:` | SoR-Verschiebung = T3/Amendment; verfrüht vor L5-Auflösung |
| A3 | Nichts tun | „Inkonsistenz" bleibt; Bausteine bleiben ungenutzt |
| A4 (OOB-3) | Statt Modul-Lineage nur **Modul-Badge/Filter** je KD | **Fallback** wenn Modul-Pilot keinen UAT-Mehrwert bringt (Kill-Gate b) |
| A5 (OOB-4) | Nur Empty-State + feste Slots, keine eingebettete Lineage-Viz | **Fallback** wenn Komposition keinen UAT-Mehrwert bringt (Kill-Gate a) |

## Externes Review (Runde 1) — Rückfluss-Gate (Nachweis)
Quelle: `~/shared/adr-handoff-KONZ-iil-klickdummy-005-2026-06-18.md` · Verdikt extern: **überarbeiten**.

| REC | Verdikt | eingearbeitet als |
|-----|---------|-------------------|
| REC-1 Reframe 3-stufig→2 Ebenen+optional | valid (Owner-Bestätigung nötig) | §Reframing, Kernthese, Titel |
| REC-2 „Workflow"-Begriff definieren | valid | §Begriffsklärung |
| REC-3 View-Model statt HTML-Kleben | valid | L9 |
| REC-4 `inferred`-Markierung | valid | L10 |
| REC-5 Kill-Gate Präzision, nicht nur Coverage | valid | Frontmatter + Kill-Gate |
| REC-6 kein leerer H1-Kasten, schlanker Hinweis | valid | L7 (`not-applicable`) |
| REC-7 „3 Hierarchien" als UAT-Hypothese | valid | §Reframing, §Offene Annahme |
| REC-8 semantische Assertions | valid | MVC Schritt 5 |
| REC-9 Provider/Adapter, kein Repo-Typ-Switch | valid | L9 |
| REC-10 echter Decision-Check 2026-08-15 | valid | Exception-Budget |
| REC-11 maschinenprüfbarer Slot-Status (4 Werte) | valid | L7 |
| REC-12 zusätzliches `repo-dossier.md` | **out-of-scope** | geparkt — Risiko 2. Repräsentation; nicht für T2-Pilot; ggf. später als testbare View-Model-Serialisierung erwägen |

## Offene Annahme (ungeprüft)
„**3 Hierarchien — wie bereits besprochen**" ist in KONZ-003/004 **nicht** belegbar → als
**UAT-Hypothese** behandelt (REC-7), nicht als Architektur-Prämisse. Vor Umsetzung Owner-Abgleich,
inkl. der Reframing-Frage (3 Ebenen vs. 2 Ebenen + optionale Modul-Ebene).

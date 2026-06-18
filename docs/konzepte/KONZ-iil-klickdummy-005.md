---
concept_id: KONZ-iil-klickdummy-005
title: Per-Repo-Sektion „Workflow → KD → UC" als Lineage-Drill-down (H1→H2→H3)
pipeline_status: idea
tier: T2                          # bedingt T3 — nur wenn H1-Kante ein org-weites Spec-Feld braucht
owner: achim                      # Annahme (ADR-211 deciders:[achim]) — bestätigen
spec_refs: []                     # Renderer-Komposition; berührt Spec NUR im T3-Zweig (Opt B)
conforms_to: platform:ADR-211
adr_threshold: kein ADR           # renderer-lokal, additiv, reversibel — Amendment NUR im T3-Zweig
review_by: 2026-09-16             # created + 90 Tage; ohne Pflege Auto-stale (I3)
superseded_by_spec: null
kill_criteria: "MVC-Pilot zeigt: die komponierte Per-Repo-Sektion aus H2 (Repo-Lineage) + H3 (Screen-Lineage) bringt gegenüber der heutigen flachen Tabelle keinen sichtbaren Mehrwert (User-UAT am Pilot-Repo verneint) → Komposition verwerfen, flache Tabelle + Empty-States behalten. SEPARATES Kill für H1: liefert die Route-Ableitung (Opt A) am Django-Pilot <50% der KD→Modul-Kanten → H1 NICHT via neuem Spec-Feld erzwingen, H1 als Django-only-Beigabe belassen oder streichen."
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

# KONZ-iil-klickdummy-005 — Per-Repo-Sektion „Workflow → KD → UC" als Lineage-Drill-down

> T2-Decision-Ledger (`/konzept`). Verwandt: KONZ-003 (genesor-Strategie), KONZ-004 (Story↔UC),
> platform:ADR-211 (Spec=SoR). Auslöser: UAT (pg-hub) + Owner-Klärung am Artefakt
> `lineage-meiki-hub.html`. **Diese Rev korrigiert das Hierarchie-Mapping** (H2 = Repo-Lineage,
> nicht „story") nach Owner-Feedback 2026-06-18.

## Tier-Gate
**T2 (bedingt T3).** Per-Repo-Sektion = Renderer-Komposition bestehender Lineage-Artefakte,
additiv/reversibel → T2. **Auto-Eskalation zu T3 GENAU DANN**, wenn die H1-Ebene ein neues
org-weites Spec-Feld (`module:`) braucht, um die Modul→KD-Kante zu ziehen (= ADR-211-Schema-
Amendment, SSoT über alle Repos). Billigster Check: Django-Pilot mit Route-Ableitung (Opt A) —
deckt sie genug KD→Modul-Kanten ab? **Bis dahin: kein Spec-Feld, kein T3.**

## Kernthese (1 Satz)
Die gewünschte „Workflow"-Ansicht ist ein **3-stufiger Lineage-Drill-down (klickbare Mermaids)** —
**H2 (Repo-Lineage, `lineage-<repo>.html`) und H3 (Screen-Lineage) existieren bereits**, nur H1
(Modul-Lineage) ist neu; der reale Schmerz ist die fehlende **Komposition zu EINER Per-Repo-Sektion**
plus ersatzloses Verschwinden von Blöcken (= wahrgenommene „Inkonsistenz") → Lösung ist
**Komposition + Empty-State-Contract**, und H1 wird **evidenz-gegated** (Django-only, opt-in)
statt spekulativ für jedes Repo gebaut (YAGNI).

## Das Modell (Owner-bestätigt am Artefakt)
Drill-down grob → fein, durchgängig als verlinkte Mermaid-Diagramme:

| Ebene | Was | Artefakt | Status |
|-------|-----|----------|--------|
| **H1** | **Modul-Lineage / Modulschaubild** — Mermaid der Module; jeder Knoten verlinkt nach unten in die H2-Lineage | — | **neu, gegated** |
| **H2** | **Repo-/KD-Lineage** — KDs + ihre Beziehungen (= `lineage-meiki-hub.html`, Owner-bestätigt) | `lineage-<repo>.html` (C3) | ✅ existiert |
| **H3** | **Screen-Lineage** — Ablauf *innerhalb* eines KD | `screen-lineage-<repo>-<kd>.html` (C2) | ✅ existiert |

**Klick-Mechanik existiert schon:** `render_lineage.py` rendert klickbare Mermaid-Knoten
(Click-Direktiven, C3) → H1→H2→H3-Verlinkung braucht **kein** neues Klick-Framework.

## Erdungs-Befund (Root-Cause — die naheliegende Lösung war „neue Ansicht bauen")
Der Auftrag las sich als „Workflow-Ansicht existiert nicht → bauen". Die Erdung zeigt: **zwei der
drei Ebenen existieren**, nur die Komposition fehlt.

| Ebene | Existierender Baustein | Reife / Lücke | Beleg |
|---|---|---|---|
| H1 Modul | `introspect_django` (Django-Apps `app_label`) · `module-manifest` (MEiKI) | nur Django/MEiKI; **kein** generischer Pfad; **KD→Modul-Kante fehlt** (kein `module:`-Feld) | C4, C5, C7 |
| H2 Repo-Lineage | `lineage-<repo>.html` | **funktioniert** — ist standalone, noch nicht als Sektion eingebettet | C3 |
| H3 Screen-Lineage | `emit_screen_lineage` | **funktioniert** | C2 |
| Komposition | — | **fehlt** (flache Tabelle + Hash-Filter) | C6 |

→ „story" (KONZ-004, geführte KD-Tour) ist **nicht** H2 und fällt aus dem Mapping. (Begriffs-
Disambiguierung: `class: story` aus ADR-211 = Prod-Safety-Pattern/Storybook ≠ die KD-Tour.)

## Ledger

| id | Aussage | Typ | Evidenz / Falsifikation | Status |
|----|---------|-----|--------------------------|--------|
| L1 | H2 = Repo-Lineage (`lineage-<repo>.html`) — existiert, Owner-bestätigt am `lineage-meiki-hub.html` | Entscheidung (D) | C3 + Owner-UAT 2026-06-18; früheres Mapping „H2=story" verworfen | **beschlossen** |
| L2 | H3 = Screen-Lineage (`screen-lineage-*.html`) — existiert | Entscheidung (D) | C2 | beschlossen |
| L3 | „Workflow"-Slot der Sektion = H2+H3 **jetzt** komponieren; reiner Reuse, kein neues Datenmodell | Entscheidung (D) | C2/C3; Alternative A1 (CSS-Gruppierung) zu schwach | vorgeschlagen |
| L4 | „H1 für jedes Repo" ist YAGNI — H1 nur **Django-only/opt-in**, gerendert bei **≥2 Modulen**, sonst keine H1-Box | Entscheidung (D) | C4/C5/C7 — keine universelle Quelle; Symmetrie ist Pull, kein Requirement; Owner-Bauchgefühl bestätigt | **beschlossen** |
| L5 | Modul→KD-Kante via **Route-Ableitung (Opt A)** — kein neues Spec-Feld; bleibt T2 | Annahme | C7 — kein `module:`-Feld heute; Falsifikation: Django-Pilot deckt <50% Kanten → Opt B (T3) erwägen | **offen — entscheidet Tier** |
| L6 | Wahrgenommene „Inkonsistenz" = ersatzloses Verschwinden datengetriebener Blöcke, nicht abweichende Reihenfolge | Befund | C6 + Session-Render-Vergleich meiki/apo/risk (Detail-Top-Level-Order identisch) | belegt |
| L7 | Empty-State je Slot behebt L6; abwesende H1-Ebene (Repo ohne Module) ist VALIDE, kein erzwungener Leerzustand | Entscheidung (D) | Alternative: Slots ausblenden = heutiges Verhalten = L6 | vorgeschlagen |
| L8 | Per-Repo-**Sektion** im `#/repo/<slug>`-Zustand (neuer Render-Pfad in `build_genesor_html`) | Entscheidung (D) | C1/C6 — Router kennt facet `repo`; golden-HTML-Diff als Netz (KONZ-003-Lehre) | vorgeschlagen |

## MVC (kleinster pilotierbarer Schnitt)
1. **Ein Django-Pilot-Repo** mit ≥2 KDs und echten Screen-Flows (Kandidat: `risk-hub`).
2. `_render_repo_section(repo, records)` in `render_genesor.py` für den `#/repo/<slug>`-Zustand,
   feste Schichtung:
   - **Workflow (oben):** **H2** = eingebettete Repo-Lineage (Link + ggf. Inline-Graph); **H3** =
     Screen-Lineage-Links je KD. *(H2/H3 = reiner Reuse — sofort.)*
   - **KD (Mitte):** bestehende Mockup-/Spec-Render-Links.
   - **UC (unten):** bestehende `uc-<repo>.html`-Links.
3. **H1 nur am Django-Pilot testen:** `introspect_django` → Modul-Knoten; KD→Modul-Kante via
   Route-Ableitung (Opt A). Render H1 **nur bei ≥2 Modulen**, sonst weglassen.
4. **Empty-State-Contract:** H2/H3/KD/UC rendern immer (Inhalt oder expliziter Leerzustand);
   H1 ist optional/abwesend.
5. Golden-HTML-Baseline VOR dem Schnitt (KONZ-003-Netz), Diff nur für den Pilot-Repo.

## Kill-Gate + Exception-Budget
- **Kill (messbar):** siehe Frontmatter — (a) Sektion bringt am Pilot keinen UAT-Mehrwert → verwerfen;
  (b) Opt A deckt <50% KD→Modul-Kanten → H1 nicht per Spec-Feld erzwingen.
- **Exception-Budget:** H1 generisch fehlend (Nicht-Django-Repos) bis **2026-08-15** als bewusst
  abwesend akzeptiert; danach Entscheidung „H1 streichen oder generischen Modulbegriff" — nicht offen lassen.

## Befunde (inkl. Advocatus Diabolus) + Alternativen

**Befunde**
- **B1 (hoch):** „Workflow neu bauen" würde H2/H3 (C2/C3) ignorieren und Doppelmodelle schaffen
  (gegen ADR-211 SoR). → Komponieren.
- **B2 (hoch, YAGNI):** „H1 für jedes Repo" = hoher Aufwand (Spec-Feld/T3) für eine Ebene ohne
  universelle Daten; bei Repos ohne Modulstruktur eine **leere oder 1-Knoten-Ebene** = negativer
  Nutzen. → Django-only/opt-in, ≥2-Module-Gate.
- **B3 (mittel):** Modul→KD-Kante ist der **eigentliche Engpass** für H1 (nicht die Modul-Liste);
  ohne sie kein Drill-down-Edge.

**Advocatus Diabolus**
- *Doppelquelle?* H1-`module:`-Feld → JA Doppelquelle zu Django-Code; deshalb L5 (Route-Ableitung).
- *„Tool→Boundary"?* Per-Repo-Sektion könnte „jedes Repo braucht Workflow" implizieren — Gegenmittel:
  Empty-State/abwesende H1 ist valide, kein Drift-Finding.
- *Symmetrie-Falle?* „3 Ebenen sind logisch" verführt zum Vollausbau; B2 hält dagegen.

**Alternativen**
| Alt | Inhalt | Warum nicht (jetzt) |
|-----|--------|---------------------|
| A1 | Nur CSS-Gruppierung der flachen Tabelle | Löst L6 nicht; kein Platz für H1 |
| A2 (Opt B) | Org-weites Spec-Feld `module:` | SSoT-Verschiebung = T3/ADR-211-Amendment; verfrüht vor L5-Auflösung |
| A3 | Nichts tun | „Inkonsistenz" bleibt; H2/H3 bleiben ungenutzt nebeneinander |

## Offene Annahme (ungeprüft)
Die User-Referenz „**3 Hierarchien — wie bereits besprochen**" konnte in KONZ-003/004 **nicht**
verifiziert werden. Das H1/H2/H3-Mapping hier ist aus Session-Dialog + Owner-Bestätigung an
`lineage-meiki-hub.html` rekonstruiert. Falls es eine frühere, abweichende Festlegung gibt → vor
Umsetzung abgleichen.

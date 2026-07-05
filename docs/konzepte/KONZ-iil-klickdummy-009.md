---
concept_id: KONZ-iil-klickdummy-009
title: Content-Screen-Typ — Marketing/Landing-Screens im Klickdummy-Renderer
pipeline_status: idea
tier: T2
owner: Achim Dehnert
spec_refs: [travel-beat:klickdummy-spec-onboarding-journey]
adr_threshold: Amendment          # ADR-211 (org-weite KD-Konvention) — Enactment via /adr, nicht hier
review_by: 2026-10-05
kill_criteria: "Nach den ersten 2 Content-Screen-KDs binnen 30 T kein content-getaggtes Feedback über das Widget ODER 3. breaking Schema-Änderung am content-Block ⇒ additiven Feldzweig + Renderer-Branch entfernen."
superseded_by_spec: null
evidence_manifest:
  - {claim_id: C1, source_path: src/iil_klickdummy/genesor/render_fallback.py, commit_or_pr: L808-862, opened_in_session: true}
  - {claim_id: C2, source_path: src/iil_klickdummy/schemas/screens-spec.schema.json, commit_or_pr: "screens.anyOf + kind-enum", opened_in_session: true}
  - {claim_id: C3, source_path: klickdummy/onboarding-journey/screens-spec.yaml, commit_or_pr: "travel-beat#59", opened_in_session: true}
created: 2026-07-05
---

# KONZ-iil-klickdummy-009 — Content-Screen-Typ im KD-Renderer

**Tier: T2** — begründet: die Änderung ist **additiv, opt-in, reversibel** (ein Feld + ein
Renderer-Branch, entfernbar) und lebt im **einen** Renderer (`iil-klickdummy`). Sie sitzt aber an
der **T2/T3-Grenze**, weil das *Enactment* ein **ADR-211-Amendment** (org-weite KD-Konvention)
erfordert — dieser Governance-Schritt läuft über `/adr` und trägt dort die T3-Schärfe, nicht dieses
Konzept. Auto-Eskalations-Trigger getroffen: persistentes Artefakt · Cross-Repo (Renderer iil-klickdummy
+ ADR platform) · neue Modellierungs-Primitive ⇒ Floor **T2**. Kein SSoT-*Reversal* (Erweiterung,
keine Verschiebung), keine neue Dependency, kein neuer Lifecycle ⇒ nicht T3.

## Kernthese

Ein Klickdummy soll die **ganze** Eintritts-Journey abbilden (kalter Besucher → Value), damit
Stakeholder von Anfang an Feedback geben. Der heutige Renderer kann nur **Daten-Screens**
(datafields → Tabelle) — Content/Marketing-Screens (Landing/Pricing) rendern leer. Lösung: ein
**optionales `content:`-Block-Feld** am Screen + ein Renderer-Branch, der es an der bereits
existierenden Leerzustands-Stelle rendert. Kein neuer Screen-`kind`, keine neue Boundary.

## Steelman (die stärkste Form der Idee, vor der Kritik)

Der Dogfood (travel-beat #59, C3) hat es empirisch belegt, nicht behauptet: die 7-Screen-Journey
rendert als geordneter Walk mit Feedback-Widget je Schritt — der e2e-Nutzen ist **real und heute
da**. Es fehlt **exakt eine** Fähigkeit: die erste-Eindruck-Seite (Landing) sichtbar zu machen.
Genau die Seite, an der Conversion entsteht und an der Stakeholder-Feedback am wertvollsten ist,
ist die einzige, die durchfällt. Ein minimaler Content-Block schließt die Lücke an genau dem Punkt,
an dem der Renderer heute schon eine Fallback-Meldung setzt (C1, `render_fallback.py:840`) — der
Hook existiert bereits, es wird nur der leere Zweig gefüllt.

## Assumption-/Decision-Ledger

| id | Aussage | Typ | Evidenz / Falsifikation | Status |
|---|---|---|---|---|
| A1 | Renderer kann heute KEINE Content-Screens; leerer Screen = `render_fallback.py:840-843` | Annahme | **E2** C1 — Zeile geöffnet: `if not entity_panels: content_blocks.append('…Keine Daten-Entities…')` | verifiziert |
| A2 | Schema hat KEIN content/blocks/hero/cta; `kind` existiert, aber als Parity-Achse (`executable/behavioral-manual/nfr-out-of-band`), nicht Render-Typ | Annahme | **E2** C2 — Schema-anyOf + kind-enum geöffnet | verifiziert |
| A3 | Content-Screen hat keine App-`route` → verletzt I1 „jeder Screen ↔ Route" bidirektional | Risiko | **E1** ADR-211 I1; Schema-Screen-Klassen erlauben route-lose Flow-Knoten (C2) | offen → D2 löst |
| D1 | Modellierung: **`content:`-Block-Liste** am Screen (Typen: `hero\|prose\|cta\|media\|plan_table`), optional, additiv | Entscheidung | Alternative: neuer `kind`-Wert — verworfen (kind = Parity-Achse, A2) | gesetzt |
| D2 | Content-Screen = **Flow-Knoten** (kein `parity_acceptance`) + `content:`; explizit `off_route: true` → aus der Route↔Screen-Parity **ausgenommen** | Entscheidung | schließt A3; nutzt existierende Flow-Knoten-Klasse (C2) | gesetzt |
| D3 | Renderer: neue `render_content_blocks()` am Hook `render_fallback.py:840` — Content ODER Leer-Fallback | Entscheidung | C1 — Hook-Stelle geöffnet, additiver `elif s.get("content")` vor dem Fallback | gesetzt |
| A4 | I2-Pattern unberührt: Content-Screen erzeugt keinen neuen Prod-Datenpfad | Annahme | **E1** ADR-211 I2; class bleibt wie deklariert | plausibel |
| A5 | Feedback-Widget funktioniert auf Content-Screens wie auf Daten-Screens | Annahme | **E2** C3 — Widget im Dogfood auf jedem Screen aktiv (auch leerem Landing) | verifiziert |

## MVC (Minimal Viable Concept — konkret, keine Anforderungsprosa)

1. **Schema** (`src/iil_klickdummy/schemas/screens-spec.schema.json`): optionale Property
   `content: [{type: hero|prose|cta|media|plan_table, …}]` an der Screen-`items`-Definition; +
   optionales `off_route: boolean`. Additiv (bestehende Specs bleiben valide).
2. **Renderer** (`src/iil_klickdummy/genesor/render_fallback.py`, Hook L840): `elif s.get("content"):
   content_blocks.append(render_content_blocks(s["content"]))` **vor** dem Leer-Fallback. Neue Funktion
   rendert je Block-Typ minimal (hero = H1+Sub+CTA; plan_table = 2-Spalten; prose = Absatz).
3. **I1-Gate** (`check_i1`): Screens mit `off_route: true` aus der Route↔Screen-Bidirektionalität
   ausnehmen — sie brauchen `content:` (sonst weiterhin Verstoß). Kein neues Gate, Regel-Zusatz im bestehenden.
4. **Doku**: ADR-211-Amendment (org-weite Konvention) — separater `/adr`-Lauf; **dieses Konzept ist
   dessen Input, nicht der Amendment selbst**.
5. **Dogfood**: travel-beat `landing` + `pricing_teaser` mit `content:`-Blöcken nachrüsten → #59
   rendert nicht mehr leer.

## Adversariale Analyse (T2: Steelman ✓ oben · Diabolus · Maintainer-2028)

### Advocatus Diabolus
- **Doppelquelle?** Ein `content:`-Block dupliziert die *echte* Landing-Page (Marketing-Repo/Template).
  → Ja, latent. Mitigation: `off_ramp` gilt auch hier — Content-Screen ist Phase-A-Wegwerf; sobald die
  echte Landing existiert, Screen entfernen (per-screen Off-Ramp, kein Dauer-Zweitartefakt).
- **„Tool wird zur Boundary"?** Wird `render_content_blocks` zum Mini-Marketing-Builder, wächst es
  unkontrolliert (Themes, Bilder, A/B). → **Genau das ist die Kill-Gate-Schwelle** (s.u.): Block-Typen
  hart auf die 5 aus D1 begrenzt; jeder 6. Typ triggert Review, kein stilles Wachstum.
- **I1 nur behauptet?** `off_route: true` könnte als Schlupfloch missbraucht werden, um echte
  App-Screens der Parity zu entziehen. → Enforcement in `check_i1`: `off_route` **erlaubt nur** wenn
  `content:` present UND kein `parity_acceptance` — ein Daten-Screen kann sich nicht wegdefinieren.
- **F17/F18/F19 verschlimmert?** Content-Screens haben keine Locators/Routen → sie **entlasten**
  Locator-Fragilität (F18), erzeugen keine Skip-Debt (F19), keine DSL-Drift (F17). Kein Nachteil dort.

### Maintainer-2028
Öffnet in 18 Monaten `render_fallback.py`: findet einen zweiten Render-Pfad neben datafields. Risiko:
zwei divergierende Render-Logiken. Mitigation: `render_content_blocks` teilt den Card/Panel-Wrapper mit
dem Datenpfad (gleiche CSS-Klassen), nur der Panel-Inhalt unterscheidet sich — ein Wrapper, zwei Füllungen.

## Alternativen (verworfen)

| Alt | Beschreibung | Warum verworfen |
|---|---|---|
| **B: Landing außerhalb des KD** | echte statische Landing im Marketing-Repo, nur mit KD-Eintrittsscreen verlinkt | bricht den **einen** e2e-Walk + die Feedback-Fläche je Schritt; Stakeholder springt Tool-übergreifend |
| **C: Marketing-Page-Builder / Storybook** | vollwertiges Content-System (Themes, Media, A/B) | T3-Overkill + neue Dependency; der KD braucht nur „genug, um das Value-Prop zu vermitteln", nicht pixel-perfekt |

## Out-of-the-Box
Der `content:`-Block ist nicht nur für Landing nützlich — **Leerzustände, Onboarding-Hinweise,
Erfolgs-/Confirmation-Screens** (heute alle „Keine Daten-Entities") würden davon profitieren. Scope
bewusst zunächst auf Landing/Pricing begrenzen (Kill-Gate misst dort), Ausweitung erst nach Beleg.

## Top-3-Risiken

| # | Risiko | Gegenmaßnahme |
|---|---|---|
| R1 | `off_route` wird zum I1-Schlupfloch (Daten-Screens entziehen sich der Parity) | `check_i1`: `off_route` nur mit `content:` ∧ ohne `parity_acceptance` |
| R2 | `render_content_blocks` wuchert zum Marketing-Builder | Block-Typen hart auf 5 begrenzt; 6. Typ = Kill-Gate-Review |
| R3 | ADR-211-Amendment stockt → Feld gebaut, aber org-weit nicht ratifiziert (Konventions-Drift) | Feld bleibt `experimental` im Schema bis Amendment `accepted`; nur travel-beat als Pilot bis dahin |

## Entscheidung + Kill-Gate

**Empfehlung:** MVC bauen (Schema + Renderer-Branch + `check_i1`-Regel), an travel-beat #59
pilotieren, **parallel** ADR-211-Amendment via `/adr` einreichen. Feld bis Ratifizierung
`experimental`.

**Kill-Gate (messbar):** Nach den ersten **2** Content-Screen-KDs — wenn binnen **30 Tagen**
**kein** content-getaggtes Feedback über das Widget kommt (der behauptete Nutzen „besseres
Feedback von Anfang an" tritt nicht ein) **ODER** der `content:`-Block eine **3. breaking
Schema-Änderung** braucht (Modellierung trägt nicht) → additiven Feldzweig + Renderer-Branch
**entfernen** (reversibel by design). **Exception-Budget:** 1 nicht-breaking Schema-Revision
binnen 60 Tagen erlaubt.

**Enforcement-Grenze (ehrlich):** `review_by`/`kill_criteria` in diesem Doc wirken erst, wenn ein
Lifecycle-Gate sie liest — solange Review-Gate, kein Exit-Code.

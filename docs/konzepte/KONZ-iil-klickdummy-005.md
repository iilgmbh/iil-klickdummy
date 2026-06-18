---
concept_id: KONZ-iil-klickdummy-005
title: Per-Repo-Sektion „Workflow → KD → UC" — kanonische Schichtung über bestehende Bausteine
pipeline_status: idea
tier: T2                          # bedingt T3 — siehe Tier-Gate
owner: achim                      # Annahme (ADR-211 deciders:[achim]) — bestätigen
spec_refs: []                     # Renderer-Komposition; berührt Spec NUR falls neues Makroprozess-Feld nötig
conforms_to: platform:ADR-211
adr_threshold: kein ADR           # renderer-lokal, additiv, reversibel — Amendment NUR im T3-Zweig (neues org-weites Spec-Feld)
review_by: 2026-09-16             # created + 90 Tage; ohne Pflege Auto-stale (I3)
superseded_by_spec: null
kill_criteria: "Pilot (1 Repo) zeigt: die Per-Repo-Workflow-Sektion aus bestehenden Daten (screen-lineage H3 + lineage/introspect H1) ist für >50% der Repos leer ODER der nötige H2-Makroprozess lässt sich ohne neues Spec-Feld nicht darstellen → Komposition verwerfen, bei der flachen Tabelle + Empty-States bleiben (NICHT zu T3/Spec-Feld eskalieren ohne erneute Owner-Freigabe)."
evidence_manifest:
  - {claim_id: C1, source_path: "src/iil_klickdummy/genesor/render_genesor.py:29 (_render_kd_detail), :1223 (build_genesor_html)", commit_or_pr: "working-tree@main", opened_in_session: true}
  - {claim_id: C2, source_path: "src/iil_klickdummy/genesor/mermaid.py:230 (emit_screen_lineage — 'Screen-Ablauf innerhalb eines KDs')", commit_or_pr: "working-tree@main", opened_in_session: true}
  - {claim_id: C3, source_path: "src/iil_klickdummy/schemas/story.schema.json (props id/title/persona/steps[].kd) + render_common.py:26-83 (story-banner)", commit_or_pr: "working-tree@main", opened_in_session: true}
  - {claim_id: C4, source_path: "src/iil_klickdummy/genesor/introspect_django.py:_inspect_django_models (AST apps/*/models.py)", commit_or_pr: "working-tree@main", opened_in_session: true}
  - {claim_id: C5, source_path: "src/iil_klickdummy/schemas/module-manifest.schema.json (MEiKI Fachverfahren — repo-spezifisch)", commit_or_pr: "working-tree@main", opened_in_session: true}
  - {claim_id: C6, source_path: "find ~/github -name '*.story.y*ml'/'module-manifest*' → leer (kein Repo hat heute eine story.yaml/Modul-Manifest)", commit_or_pr: "session-scan 2026-06-18", opened_in_session: true}
  - {claim_id: C7, source_path: "genesor/index.html:2719-2733 (SPA-Hash-Router facets repo/org/class/role) — flache gefilterte Tabelle, keine Per-Repo-Sektion", commit_or_pr: "iil-pet-portal working-tree", opened_in_session: true}
  - {claim_id: C8, source_path: "docs/konzepte/KONZ-iil-klickdummy-004.md (Story↔UC — Story=geordnete KD-Tour, fail-fast)", commit_or_pr: "working-tree@main", opened_in_session: true}
created: 2026-06-18
---

# KONZ-iil-klickdummy-005 — Per-Repo-Sektion „Workflow → KD → UC"

> T2-Decision-Ledger (`/konzept`). Verwandt: KONZ-003 (genesor-Strategie / Monolith-Entschärfung),
> KONZ-004 (Story↔UC), platform:ADR-211 (Spec=SoR). Auslöser: UAT-Beobachtung (pg-hub),
> „inkonsistente Darstellung je Repo" in der gefilterten Genesor-Sicht.

## Tier-Gate
**T2 (bedingt T3).** Single-Repo-Renderer-Konvention, additiv/reversibel → T2. **Auto-Eskalation
zu T3 GENAU DANN**, wenn die H2-Makroprozess-Ebene ein **neues, org-weites Spec-Feld** braucht
(ADR-211-Schema-Amendment = SSoT-Verschiebung über alle Repos). Billigster Check zur Auflösung:
MVC-Pilot (unten) — komponiert die Sektion aus *bestehenden* Daten genug Substanz, oder ist H2 ohne
neues Feld leer? **Bis der Check vorliegt: nicht als T3 bauen.**

## Kernthese (1 Satz)
Die „Workflow"-Ansicht muss **nicht neu erfunden** werden — H3 (Screen-Flow) existiert als
`emit_screen_lineage` (C2), H2 (Makroprozess) als **unbenutztes** `story`-Schema (C3, C6), H1
(Module) via `introspect_django` / `module-manifest` (C4, C5) — der reale Schmerz ist (a) sie sind
**nicht zu EINER kanonischen Per-Repo-Sektion komponiert** (heute flache, gefilterte Tabelle, C7)
und (b) **datengetriebene Blöcke verschwinden ersatzlos** statt mit Leerzustand → daher wirkt es
„inkonsistent"; Lösung ist **Render-Komposition + Empty-State-Contract**, kein neues Spec-Feld.

## Erdungs-Befund (Root-Cause-Tiefe — die naheliegende Lösung war „neue Ansicht bauen")
Der Auftrag las sich als „die Workflow-Ansicht existiert nicht → bauen". Die Erdung falsifiziert,
dass nichts existiert; sie zeigt **drei reife/halbreife Bausteine ohne Komposition**:

| Ebene (User) | Bedeutung | Existierender Baustein | Reife | Beleg |
|---|---|---|---|---|
| **H1 Module/Pakete** | Struktur-Hierarchie | `introspect_django` (Django-Apps) · `module-manifest` (MEiKI) | nur Django/MEiKI; **kein** generischer Pfad | C4, C5 |
| **H2 Makro-Prozess/Workflow** | geordneter Fluss über KDs | `story` (geordnete KD-Tour, `steps[].kd`) | Schema da, **0 Repos** nutzen es | C3, C6, C8 |
| **H3 detaillierter Workflow** | Screen-Ablauf *innerhalb* eines KD (Swimlane-nah) | `emit_screen_lineage` → `screen-lineage-*.html` | **funktioniert** | C2 |
| Komposition | „eine Sektion je Repo" | — | **fehlt** (flache Tabelle + Hash-Filter) | C7 |

→ Eine „neue Workflow-Ansicht" als drittes Datenmodell schüfe eine **zweite/dritte Wahrheit** neben
Spec + story.yaml. SoR ist laut ADR-211 die **Spec**. Der Hebel ist **Komposition + Leerzustand**,
nicht **Neuerfassung** — solange H2 aus `story` darstellbar ist.

## Ledger

| id | Aussage | Typ | Evidenz / Falsifikation | Status |
|----|---------|-----|--------------------------|--------|
| L1 | H3 (Screen-Flow) ist bereits gerendert (`emit_screen_lineage`) und kann den „detaillierten Workflow"-Slot füllen | Annahme | C2 — Funktion existiert; Falsifikation: prüfen ob Swimlane-Personas-Lanes verlangt sind, die der Graph nicht kann | offen |
| L2 | H2 (Makroprozess) = `story` (geordnete KD-Tour); kein neues Feld nötig, NUR Autoren-Adoption | Annahme | C3/C6/C8 — Schema da, 0 Nutzung; Falsifikation: Pilot-Repo kann seinen Makroprozess nicht als story[] ausdrücken | **offen — entscheidet Tier** |
| L3 | H1 (Module) hat **keinen** repo-agnostischen Datenpfad (nur Django/MEiKI) | Befund | C4/C5 — zwei repo-spezifische Quellen; Falsifikation: ein generischer Modul-Begriff (z.B. KD-Gruppen aus `spec_id`-Präfix) genügt | offen |
| L4 | Wahrgenommene „Inkonsistenz" = ersatzloses Verschwinden datengetriebener Blöcke, nicht abweichende Reihenfolge | Befund | C7 + Session-Render-Vergleich meiki/apo/risk (Detail-Top-Level-Order war identisch) | belegt |
| L5 | Fixe Schichtung mit **Empty-State je Slot** beseitigt L4 ohne neue Daten | Entscheidung (D) | Alternative: Slots ausblenden wenn leer (= heutiges Verhalten, erzeugt L4) → verworfen | vorgeschlagen |
| L6 | Per-Repo-**Sektion** statt per-KD-Detail (User-Scope) → neuer Render-Pfad in `build_genesor_html` für den `#/repo/<slug>`-Zustand | Entscheidung (D) | C1/C7 — Router kennt facet `repo` bereits; Alternative: nur CSS-Gruppierung der Tabelle → zu schwach für H1/H2 | vorgeschlagen |
| L7 | Kein neues org-weites Spec-Feld im T2-Zweig; H2 bleibt opt-in via `story.yaml` (KONZ-004-Schema/Gate nutzen) | Entscheidung (D) | C8 — KONZ-004 liefert story-Validierung; Falsifikation = L2-Auflösung → dann T3 | vorgeschlagen |

## MVC (kleinster pilotierbarer Schnitt)
1. **Ein Pilot-Repo** mit echtem Mehrwert wählen: ≥2 KDs **und** vorhandenen Screen-Flows
   (Kandidat: `risk-hub` oder `ausschreibungs-hub` — multi-KD, echte Mockups).
2. In `render_genesor.py` eine Funktion `_render_repo_section(repo, records)` ergänzen, die im
   `#/repo/<slug>`-Zustand **eine** Sektion mit fixer Schichtung rendert:
   - **Workflow (oben):** H3 = bestehende `screen-lineage`-Links/Graph je KD; H2 = `story`-Stepper
     **falls** `story.yaml` vorhanden, sonst **Empty-State** „kein Makroprozess hinterlegt
     (→ `klickdummy/stories/<slug>.yaml`, KONZ-004)"; H1 = Modul-Liste **falls**
     Django/`module-manifest`, sonst Empty-State.
   - **KD (Mitte):** bestehende Mockup-/Spec-Render-Links (heutige `mockup_link`-Logik).
   - **UC (unten):** bestehende UC-Index-Links (`uc-<repo>.html`).
3. **Empty-State-Contract:** jeder der drei Slots rendert **immer** (Titel + Inhalt **oder**
   expliziter Leerzustand mit Pfad-Hinweis) — nie ersatzloses Weglassen (behebt L4).
4. Golden-HTML-Baseline VOR dem Schnitt ziehen (KONZ-003-Sicherheitsnetz), Diff nur für den
   Pilot-Repo erwarten.

## Kill-Gate + Exception-Budget
- **Kill (messbar):** siehe Frontmatter `kill_criteria` — Pilot leer für >50% Repos ODER H2 ohne
  neues Feld nicht darstellbar → Komposition verwerfen, flache Tabelle + Empty-States behalten.
- **Exception-Budget:** Wenn der Pilot Mehrwert zeigt, aber H1 generisch fehlt (L3) → H1-Slot
  **bis 2026-08-15** als Dauer-Empty-State akzeptiert; danach Entscheidung „H1 streichen oder
  generischen Modulbegriff definieren" — nicht offen lassen.

## Befunde (inkl. Advocatus Diabolus) + Alternativen

**Befunde**
- **B1 (hoch):** „Workflow-Ansicht neu bauen" würde drei vorhandene Bausteine (C2/C3/C4) ignorieren
  und Doppelmodelle schaffen — gegen ADR-211 SoR. → Komponieren, nicht neu erfassen.
- **B2 (mittel):** H2 ist heute toter Code-Pfad (Schema ohne Nutzung, C6) — die Sektion macht
  `story` erstmals sichtbar nützlich; Risiko: ohne Autoren bleibt H2 dauerhaft Empty-State.
- **B3 (mittel):** Per-Repo-Sektion ist ein **neuer Render-Pfad** (Boundary) → T2-Pflicht; golden-
  HTML-Diff als Netz, sonst stiller Byte-Drift in `genesor.html` (KONZ-003-Lehre).

**Advocatus Diabolus**
- *Wo Doppelquelle?* H2 als neues Spec-Feld → JA Doppelquelle zu `story.yaml`; deshalb L7 (kein
  Feld, story bleibt SoR-konform opt-in).
- *Wo „Tool→Boundary"?* Die Per-Repo-Sektion könnte zur impliziten Pflicht werden („jedes Repo
  braucht Workflow") — Gegenmittel: Empty-State ist **valide**, kein Drift-Finding.
- *Wo „sichtbar machen < verhindern"?* Empty-States machen Lücken sichtbar, erzwingen aber nichts —
  bewusst (Adoption, nicht Zwang); Enforcement wäre ein KONZ-004-Lint, nicht dieses Konzept.

**Alternativen**
| Alt | Inhalt | Warum nicht (jetzt) |
|-----|--------|---------------------|
| A1 | Nur CSS-Gruppierung der flachen Tabelle je Repo | Löst L4 nicht (Blöcke fehlen weiter); kein Platz für H1/H2 |
| A2 | Neues org-weites Spec-Feld `workflow:`/`macro_process:` | SSoT-Verschiebung über alle Repos = T3/ADR-211-Amendment; verfrüht bevor L2 belegt ist |
| A3 | Nichts tun | „Inkonsistenz"-Wahrnehmung bleibt; vorhandene Bausteine bleiben ungenutzt |

## Offene Annahme (ungeprüft)
Die User-Referenz „**3 Hierarchien — wie bereits besprochen**" konnte in KONZ-003/004 **nicht**
verifiziert werden (nicht dort dokumentiert). Diese Schichtung H1/H2/H3 ist hier aus der
Session-Vorgabe rekonstruiert — **vor Umsetzung mit dem Owner abgleichen**, ob es eine frühere
Festlegung gibt, die H1/H2/H3 anders definiert.

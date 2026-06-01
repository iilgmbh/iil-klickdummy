---
concept_id: KONZ-iil-klickdummy-002
title: Repo-Ebenen-Einstieg für IIL-Genesor (Master-Detail + Fassetten-Launcher)
pipeline_status: idea
tier: T2
owner: achim                      # Annahme (Repo-/Plattform-Owner, ADR-211 deciders:[achim]) — bestätigen
spec_refs: []                     # bewusst leer: betrifft den genesor-Renderer (Tooling), nicht eine konkrete Spec
conforms_to: platform:ADR-211
adr_threshold: kein ADR           # UI-Änderung am Renderer, reversibel durch Revert einer Funktion; CHANGELOG+PR
review_by: 2026-08-30             # created + 90 Tage
superseded_by_spec: null
kill_criteria: "Pilot (ausschreibungs-hub + risk-hub) zeigt: Master-Detail braucht für den Sprung KD→Mockup MEHR Klicks als die alte Tabelle (>2), ODER die eingebettete Daten-JS macht index.html >2× so groß wie heute → zurück zur Tabelle, nur Repo-Accordion behalten"
evidence_manifest:
  - {claim_id: C1, source_path: "iil-klickdummy/src/iil_klickdummy/lineage.py:6296-6297", commit_or_pr: "working-tree@main", opened_in_session: true}
  - {claim_id: C2, source_path: "iil-klickdummy/src/iil_klickdummy/lineage.py:2696,2994-2996", commit_or_pr: "working-tree@main", opened_in_session: true}
  - {claim_id: C3, source_path: "iil-klickdummy/src/iil_klickdummy/lineage.py:2805 (colspan=13)", commit_or_pr: "working-tree@main", opened_in_session: true}
  - {claim_id: C4, source_path: "iil-klickdummy/src/iil_klickdummy/lineage.py:4045 (lineage-<repo>.html), :6286 (uc-<repo>.html)", commit_or_pr: "working-tree@main", opened_in_session: true}
  - {claim_id: C5, source_path: "scan ~/github: 35 screens-spec.yaml über 7 Repos; ausschreibungs-hub 12 + risk-hub 11 = 66%", commit_or_pr: "session-scan 2026-06-01", opened_in_session: true}
  - {claim_id: C6, source_path: "grep lineage.py: kein repo-home/master-detail/#/repo/hash-Mechanismus (leer)", commit_or_pr: "session-grep 2026-06-01", opened_in_session: true}
  - {claim_id: C7, source_path: "iil-klickdummy/src/iil_klickdummy/lineage.py:79-150 (BASE_URL '/', relative Datei-Links, url_for_path)", commit_or_pr: "working-tree@main", opened_in_session: true}
  - {claim_id: C8, source_path: "iil-klickdummy/docs/konzepte/KONZ-iil-klickdummy-001.md (L7/L8 Drift durch kopierte Artefakte)", commit_or_pr: "working-tree@main", opened_in_session: true}
  - {claim_id: C9, source_path: "iil-klickdummy/genesor-repo-entry-mockup.html (Playwright-verifiziert: mockup-default.png, mockup-pipeline.png)", commit_or_pr: "working-tree (session)", opened_in_session: true}
created: 2026-06-01
off_ramp:                         # idea-Stufe; wird Issue/PR in iil-klickdummy (build_genesor_html)
---

# KONZ-iil-klickdummy-002 — Repo-Ebenen-Einstieg für IIL-Genesor

> Form: **T2-Ledger** (Option A) — strukturierte Records, kein Anforderungs-Freitext.
> Erzeugt mit `/konzept`. Evidenz im `evidence_manifest`; Claim-IDs `C1`–`C9`.
> Anschaubarer Mockup: `genesor-repo-entry-mockup.html` (C9).

## Kernthese
> Der genesor-Einstieg wird von einer flachen org→repo-Mega-Tabelle (C2) zu einem
> **client-seitigen Master-Detail in EINER `index.html`**: linke Repo-Schiene (alle Repos
> sichtbar) + Detail-Fläche pro Auswahl, deep-linkbar via `#/repo/<repo>`. **Repo ist die
> Default-Linse, nicht die einzige** — dieselben Daten sind nach `org | pipeline | class`
> umschaltbar. Null neue Drift-Fläche, weil die Daten ohnehin schon in der Seite stecken (C7).

## Steelman (der User-Vorschlag, in seiner stärksten Form)
Bei 35 KDs über 7 Repos mit Long-Tail (ausschreibungs-hub 12, risk-hub 11 = 66% — C5) ist eine
einzige Tabelle, die diese 23 Zeilen neben Repos mit je 2 KDs stapelt, kognitiv überladen. Ein
Repo-Einstieg gibt jedem Stakeholder genau seinen Ausschnitt und macht die URL teilbar
(„schau dir ausschreibungs-hub an" = eine Link-Zeile). Das ist die richtige Diagnose.

## Assumption-/Decision-Ledger

| id | Aussage | Typ | Evidenz / Falsifikation | Status |
|---|---|---|---|---|
| L1 | Einstieg `iil.pet/genesor/` = `index.html` = `build_genesor_html` = eine flache org→repo-Tabelle | Beobachtung | C1, C2 | verifiziert |
| L2 | Tabelle hat 13 Spalten → Breite ist eine *eigene* Clutter-Quelle, unabhängig vom Repo-Schnitt | Beobachtung | C3 | verifiziert |
| L3 | Per-Repo-Artefakte existieren bereits (`lineage-<repo>.html`, `uc-<repo>.html`), aber verstreut, ohne Repo-Heimat | Beobachtung | C4 | verifiziert |
| L4 | Clutter ist real + konzentriert: 2 Repos = 66% der KDs, Rest je 2 (Long-Tail) | Beobachtung | C5 | verifiziert |
| L5 | Es existiert noch KEIN Repo-Home/Master-Detail/Hash-Routing — der Mechanismus ist neu, nicht doppelt | Beobachtung (Root-Cause-Tiefe) | C6 | verifiziert |
| L6 | `genesor/repo=X` als **Query-String** kann statisch nicht routen — nginx ignoriert Query, liefert `index.html` | Entscheidung (Routing) | C7 | verifiziert → **Hash `#/repo/X` statt Query** |
| L7 | Reine Repo-**Landing** = Extra-Klick fürs Portfolio-Bild bei nur 7 Repos → Rückschritt | Risiko (UX) | C5 (nur 7 Repos) | adressiert durch Master-Detail (alle Repos in der Schiene sichtbar) |
| L8 | Client-seitig (1 Datei) = null neue Drift-Fläche; statische `repo-*.html` = N× Output + Sync-Pflicht | Entscheidung (Architektur) | C7, C8 (KONZ-001 L7/L8) | **client-seitig gewählt** (User 2026-06-01) |
| L9 | Repo ist *Default*-Linse, nicht *die* Achse — Fassetten-Launcher (repo/org/pipeline/class) | Entscheidung (OOTB) | C9 (Mockup zeigt Pipeline-Linse cross-repo) | verifiziert im Mockup |
| L10 | Eingriff ist repo-lokal: nur `build_genesor_html` (lineage.py), kein cross-repo verteilter Code | Entscheidung (Tier) | C1, C6 | verifiziert → **T2** (persistentes Prod-Artefakt + neue Boundary; aber 1 Repo/1 File) |
| L11 | genesor nutzt heute schon JS massiv (Filter, Persona-/Skin-Switch) → JS-Annahme ist kein neuer Bruch | Beobachtung | C7 (Umfeld) | verifiziert (kein no-JS-Regression-Argument) |

## Minimal Viable Concept (MVC)

| # | Ort | Änderung | Effekt |
|---|---|---|---|
| 1 | `lineage.py` `build_genesor_html` (:2696) | Statt einer Tabelle: (a) bestehenden `records`→`by_org`→`repo`-Aufbau (:2994) in ein **JS-Daten-Objekt** serialisieren; (b) Topbar-**Fassetten-Select** (repo/org/pipeline/class) + Suche; (c) **linke Repo-Schiene** (Counts + Reife-Punkt); (d) **Detail-Fläche** mit Sub-Tabs KDs/Lineage/UCs/Coverage; (e) **Hash-Router** `#/<facet>/<group>` + `#/kd/<repo>/<kd>` | Repo-Einstieg + at-a-glance + Deep-Links |
| 2 | dito | Sub-Tab „Lineage"/„UCs" **verlinken** auf die bereits erzeugten `lineage-<repo>.html` / `uc-<repo>.html` (C4) — kein Neubau, nur Konsolidierung | verstreute Artefakte bekommen eine Heimat |
| 3 | Portfolio-Stats-Strip | Stats (KDs/Repos/Orgs + Pipeline-Legende) bleiben **immer sichtbar** über der Schiene | Portfolio-Bild nicht versteckt (gegen L7) |
| 4 | `tests/` | Snapshot-/Struktur-Test: `index.html` enthält Daten-JS, `#/repo/`-Router, Fassetten-Select; Smoke-Marker bleibt grün | Regression-Schutz |

- **Vorbild im Repo:** der Mockup `genesor-repo-entry-mockup.html` (C9) ist die Referenz-Implementierung — Layout, Router, Fassetten 1:1 nachbaubar.
- **Nicht enthalten:** statische `repo-*.html`-Aliasse (verworfen, L8); Server-Routing; Änderung der Daten-/Scan-Logik (`find_all_repos_specs` bleibt unangetastet).
- **Rückbau:** `build_genesor_html` auf die Tabellen-Version reverten (eine Funktion, ein Diff).

## Befunde (inkl. Advocatus Diabolus)

| id | Befund | Schwere | Beleg | Auflösung im MVC |
|---|---|---|---|---|
| AD-1 | Doppelquelle? Die KD-Daten werden ins JS serialisiert — entsteht eine zweite Wahrheit neben der Spec? | mittel | D | Nein: JS ist Render-Cache aus `records`, exakt wie die Tabelle heute aus `records` baut (C2). Keine neue SoR. |
| AD-2 | „Sichtbar machen" statt „verhindern": löst Master-Detail den *Breiten*-Clutter (L2) oder nur den Mengen-Clutter? | mittel | C3 | Karten-Layout (nicht gefilterte 13-Spalten-Tabelle) löst beides; explizit im Kill-Gate verankert. |
| AD-3 | Client-Routing = JS-Pflicht; bei JS-aus leere Seite | niedrig | C7, L11 | genesor ist schon JS-abhängig (Filter/Skin/Persona) — kein Regress. `<noscript>`-Hinweis als Mini-Härtung. |
| AD-4 | Tisch-Tabelle ist suchmaschinen-/Strg-F-freundlich; SPA-Hash versteckt Inhalt vor Strg-F | niedrig | D | Detail rendert alle KDs der Gruppe als echtes DOM → Strg-F wirkt *innerhalb* der Gruppe; globale Suche ersetzt cross-repo-Strg-F. |
| AD-5 | Verschlimmert es F18 (Locator-Fragilität) für die genesor-eigenen Playwright-Smoke-Tests? | mittel | H (F18, nicht in Session geprüft) | MVC #4 fordert struktur-stabile Marker (`data-*`), nicht Text-Selektoren. **Restlücke: F18-Stand nicht verifiziert — billigster Check: tests/test_smoke.py lesen.** |
| AD-6 | Tier-Flucht? Als T1 gerahmt, obwohl Prod-Einstieg betroffen | mittel | C1 | Bewusst **T2** hochgestuft (persistentes Prod-Artefakt, L10). Kein T1. |

## Alternativen (verworfen)

| Alt | Beschreibung | Warum verworfen |
|---|---|---|
| A1 | Statische `repo-<repo>.html` pro Repo (wie `lineage-`/`uc-`) | Echte URLs, aber N× HTML-Output + Rebuild/Sync-Pflicht → mehr Drift-Fläche (C8, KONZ-001 L7/L8). User-Entscheid 2026-06-01: client-seitig. |
| A2 | Nur Accordion: bestehende Tabelle pro Repo aufklappbar/zuklappbar | Billigster Fix, aber löst die 13-Spalten-Breite (L2/AD-2) nicht und bietet keinen Deep-Link. Bleibt als Kill-Gate-Fallback. |

## Entscheidung + Kill-Gate
- **Entscheidung:** MVC umsetzen (client-seitig, 1 Datei), Mockup C9 als Referenz. Pilot auf `ausschreibungs-hub` + `risk-hub` (die Long-Tail-Repos, C5).
- **Kill-Gate (messbar):** Siehe Frontmatter `kill_criteria` — >2 Klicks KD→Mockup ODER `index.html` >2× heutige Größe → Rückbau auf Tabelle, nur Repo-Accordion (A2) behalten.
- **Exception-Budget:** bis `review_by` 2026-08-30; danach ohne Pflege Auto-`stale` (I3).

## Ehrliche Enforcement-Grenze
`/konzept` schreibt `review_by`/`kill_criteria`/`superseded_by_spec`, **erzwingt** sie aber nicht —
solange kein Lifecycle-Gate sie liest, ist das ein Review-Gate, kein Exit-Code.

---
concept_id: KONZ-iil-klickdummy-001
title: Idempotenz für genesor-erzeugte Klickdummy-Issues (Button ↔ Sync-Bot)
pipeline_status: idea
tier: T2
owner: achim                      # Annahme (Repo-/Plattform-Owner, ADR-211 deciders:[achim]) — bestätigen
spec_refs: []                     # bewusst leer: betrifft Issue-Erzeugung/Tooling, nicht eine konkrete Spec
conforms_to: platform:ADR-211
adr_threshold: kein ADR           # CHANGELOG+PR (Bugfix nach bestehendem Sentinel-Muster, reversibel)
review_by: 2026-08-30             # created + 90 Tage
superseded_by_spec: null
kill_criteria: "Reconcile schließt im Pilot >0 Issues mit fremden Kommentaren/Assignees → stop, nur Label statt Close"
evidence_manifest:
  - {claim_id: C1, source_path: "iil-klickdummy/src/iil_klickdummy/lineage.py:3079-3093", commit_or_pr: "working-tree@feat/spec-layer-xray", opened_in_session: true}
  - {claim_id: C2, source_path: "ausschreibungs-hub/.github/scripts/klickdummy_sync.py:40", commit_or_pr: "working-tree@main", opened_in_session: true}
  - {claim_id: C3, source_path: "ausschreibungs-hub/.github/scripts/klickdummy_sync.py:180-186", commit_or_pr: "working-tree@main", opened_in_session: true}
  - {claim_id: C4, source_path: "github:achimdehnert/ausschreibungs-hub#66,#67", commit_or_pr: "#66,#67", opened_in_session: true}
  - {claim_id: C5, source_path: "find klickdummy_sync.py → ausschreibungs-hub + meiki-hub", commit_or_pr: "working-tree", opened_in_session: true}
created: 2026-06-01
off_ramp:                         # idea-Stufe; wird Issue/PR in iil-klickdummy + konsumierenden Repos
---

# KONZ-iil-klickdummy-001 — Idempotenz für genesor-erzeugte Klickdummy-Issues

> Form: **T2-Ledger** (Option A, 2026-06-01) — strukturierte Records, kein Anforderungs-Freitext.
> Erzeugt mit `/konzept`. Evidenz im `evidence_manifest` (Frontmatter); Claim-IDs `C1`–`C5`.

## Kernthese
> Beide Issue-Erzeuger müssen denselben Idempotenz-Schlüssel (`<!-- klickdummy-sync:{kd} -->`)
> tragen, und der Bot rekonziliiert Mehrfach-Treffer — Idempotenz entkoppelt vom Klickzeitpunkt,
> nachgelagert selbstheilend.

## Annahmen-/Entscheidungs-Ledger

| id | Aussage | Typ | Evidenz / Falsifikation | Status |
|---|---|---|---|---|
| L1 | Der Bot `klickdummy_sync.py` ist bereits idempotent (Sentinel `<!-- klickdummy-sync:{kd} -->`, upsert) | Beobachtung | C2 | verifiziert |
| L2 | `find_existing_issue` liefert nur den **ersten** Treffer; keine Schließ-Logik für Mehrfach-Treffer | Beobachtung | C3 | verifiziert |
| L3 | Der „🛠 Mockup generieren"-Button baut blindes `issues/new` **ohne** Sentinel, menschen-geklickt | Beobachtung | C1 | verifiziert |
| L4 | #66/#67 sind byte-identische Dubletten (Button zweimal geklickt) | Beobachtung | C4 | verifiziert |
| L5 | Wurzel = zwei Erzeuger, ein Namensraum, kein gemeinsamer Idempotenz-Schlüssel (nicht „fehlendes Dedup") | Entscheidung (Root-Cause) | C1–C4 | verifiziert |
| L6 | Fix trifft das geteilte Package `iil-klickdummy` → Cross-Repo → **T2** | Entscheidung (Tier) | C1, C5 | verifiziert |
| L7 | `klickdummy_sync.py` ist pro-Repo kopiert (ausschreibungs-hub + meiki-hub) → Bot-Fix in N Kopien | Risiko (SSoT/Drift) | C5 | verifiziert |
| L8 | *Wie* `klickdummy_sync.py` verteilt wird (Sync-Mechanismus) | Annahme (offen) | nicht geöffnet — Check: Dist-Footer im Script-Kopf greppen | offen (H) |

## Minimal Viable Concept (zweiteilig, Cross-Repo)

| Teil | Ort | Änderung | Effekt |
|---|---|---|---|
| A | `lineage.py:3082` | `_issue_body` um `\n\n<!-- klickdummy-sync:{r["kd"]} -->` ergänzen (1 Zeile) | Bot findet button-Issues |
| B | `klickdummy_sync.py` `find_existing_issue`/`upsert` | **alle** Sentinel-Treffer sammeln; ältesten kanonisch behalten, übrige mit Kommentar schließen — **nur** wenn Ziel-Issue keine fremden Kommentare/Assignees hat, sonst `duplicate`-Label | Dubletten heilen deterministisch |

- **Erfolg:** Reconcile gegen #66/#67 → einer bleibt+sentinel-getaggt, einer geschlossen; Re-Run = kein Churn (Determinismus).
- **Nicht enthalten:** Verhinderung am Klickzeitpunkt (Alt-1/Alt-2); Vereinheitlichung der `klickdummy_sync.py`-Kopien (L7, eigenes Konzept).
- **Rückbau:** Body-Zeile + Reconcile-Block reverten (zwei kleine Diffs).

## Befunde (inkl. Advocatus Diabolus)

| ID | Rolle | Befund | Schweregrad | Bezug |
|---|---|---|---|---|
| PRO-1 | Proponent | Nutzt vorhandene Sentinel/upsert-Mechanik; kein neuer Service/Dependency; Button bleibt, wird harmlos | positiv | L1 |
| AD-1 | Diabolus (neuer Failure-Mode) | Auto-Close ist destruktiv — schließt der Bot ein Issue mit menschlicher Diskussion, geht Kontext verloren; „Label" sicherer als „Close" | hoch | MVC-B |
| AD-2 | Diabolus (SSoT) | Sentinel behandelt Symptom; Wurzel „zwei Erzeuger" bleibt — Reconcile ist eventual, nicht preventive | mittel | L5 |
| AD-3 | Diabolus (SSoT/I4-Ironie) | Dedup-Fix in pro-Repo kopiertem Script zu pflegen ist selbst eine Doppelquelle (N Kopien driften) | hoch | L7 |
| AD-4 | Diabolus (Governance) | Version-Skew: alte `lineage.py`-Konsumenten rendern wieder sentinel-lose Buttons | mittel | C1 |

## Alternativen

| ID | Idee | Vorteil | Nachteil |
|---|---|---|---|
| ALT-1 (kleiner) | Button → GitHub-**Such-Link** (`issues?q=…{kd}`) statt `issues/new` | verhindert Dubletten am Ursprung; kein Auto-Close; kein Bot-Teil-B | ein Klick mehr; Mensch kann trotzdem „New" |
| ALT-2 (technischer) | Button nur rendern, wenn zur Render-Zeit kein offenes Sentinel-Issue existiert | harte Verhinderung | neue Laufzeit-Dependency (GH-API beim Render), Rate-Limits, langsamer |

## Entscheidung + Kill-Gate

- **Empfehlung:** als MVP annehmen (MVC A+B). **Threshold:** kein ADR → CHANGELOG+PR in iil-klickdummy + konsumierenden Repos.
- **Kill-Gate:** Reconcile schließt im Pilot **>0** Issues mit fremden Kommentaren/Assignees → stop, Close-Pfad aus, nur `duplicate`-Label, manueller Review. Exception-Budget: keine.
- **Sofortmaßnahme:** Teil A (Sentinel in Body) — 1 Zeile. **Offene H:** L8 (Sync-Verteilung) vor Teil B klären.
- **30/60/90:** 30 = Teil A live + Reconcile dry-run gegen #66/#67; 60 = Pilot ausschreibungs-hub, False-Merge-Rate messen; 90 = Kill-Gate auswerten → meiki-hub ausrollen oder Reconcile in geteiltes Paket heben (L7/AD-3).

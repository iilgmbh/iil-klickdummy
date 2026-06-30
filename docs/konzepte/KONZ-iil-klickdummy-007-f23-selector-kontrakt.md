---
concept_id: KONZ-iil-klickdummy-007
title: F23 — Stabiler UI-Testkontrakt (data-testid härten vs. semantische Selektoren)
pipeline_status: idea
tier: T2
owner: achim.dehnert@iil.gmbh
spec_refs: [screens-spec.schema.json#parity_acceptance.assert]
adr_threshold: Amendment (ADR-211 — Ratifikation org-weit, Konzept repo-lokal)
review_by: 2026-09-30
kill_criteria: "Nach Bau des Strict-Selector-Gates: brauchen ≥2 reale Specs den semantischen Fallback (role=/label=), WEIL kein data-testid erreichbar ist → Konvention-A-als-primär ist widerlegt, B wird primär (re-charter). ODER F18-Trigger feuert (cross-repo UI-Refactor bricht ≥2 Suites TROTZ data-testid) → Manifest/Registry reaktivieren."
superseded_by_spec: null
evidence_manifest:
  - {claim_id: C1, source_path: src/iil_klickdummy/gen_e2e.py:94-120, commit_or_pr: "render_assertion emittiert page.locator(selector) verbatim, action-enum {visible,text,clickable,url,count}", opened_in_session: true}
  - {claim_id: C2, source_path: src/iil_klickdummy/gen_e2e.py:157-166+294-295+373-374, commit_or_pr: "STABLE_SELECTOR_HINTS + is_fragile_selector → NUR Manifest-Warnung (print ⚠), kein raise/exit≠0", opened_in_session: true}
  - {claim_id: C3, source_path: src/iil_klickdummy/schemas/screens-spec.schema.json, commit_or_pr: "parity_acceptance.assert.selector = freier string; action = enum; KEINE data-testid-Struktur erzwungen", opened_in_session: true}
  - {claim_id: C4, source_path: platform/docs/adr/ADR-211:478, commit_or_pr: "accepted Body trägt Selector-Konvention bereits: data-testid/data-acceptance-id bevorzugt, fragil markiert, ab Off-Ramp status-relevant", opened_in_session: true}
  - {claim_id: C5, source_path: platform/docs/adr/ADR-211:994-999, commit_or_pr: "F18: Locator-Registry bewusst zurückgestellt (Doppelquell-Risiko); Schließungs-Trigger = realer Cross-Repo-UI-Refactor", opened_in_session: true}
  - {claim_id: C6, source_path: platform/docs/adr/ADR-211:954, commit_or_pr: "Rev 21: einziger eingelöster E2E-Beweis lief über data-testid (sds-review-queue/-row/-verify-btn), 3/3 grün", opened_in_session: true}
  - {claim_id: C7, source_path: platform/docs/adr/ADR-211:952, commit_or_pr: "Rev 20: 0 data-testid in den Apps zum Zeitpunkt; nur 1 realer Renderer #2 plattformweit", opened_in_session: true}
created: 2026-06-30
---

# KONZ-iil-klickdummy-007 — F23: Stabiler UI-Testkontrakt

## Kernthese (ein Satz)

F23 ist **kein offenes „A oder B"** — Option A (data-testid-Konvention) ist bereits
*akzeptierter weicher Body* (C4) und die „Manifest"-Variante ist als Locator-Registry unter
**F18 bewusst zurückgestellt** (C5); die einzig wirklich offene Stellschraube ist, ob der
**bestehende weiche `is_fragile_selector`-Nudge zum Off-Ramp-gatenden Check gehärtet** wird und
ob **semantische Selektoren (B) als dokumentierter Fallback** für die Fälle zugelassen werden, in
denen kein `data-testid` erreichbar ist.

**Empfehlung:** **Hybrid** — A härten (Manifest-Warnung → Off-Ramp-Gate über `--strict-selectors`),
B als Präfix-Fallback (`role=`/`label=`/`testid=`) im Selektor-Vokabular zulassen (kein
Schema-Bruch, `selector` bleibt `string`), Manifest/Registry **unverändert zurückgestellt** (F18
steht) bis dessen messbarer Trigger feuert.

## Steelman je Option (vor Kritik)

- **A (data-testid härten):** Der einzige real grüne E2E-Pfad lief exakt so (C6). `data-testid`
  ist eindeutig, i18n-fest, markup-refactor-stabil, und im Generator + ADR-Body schon halb
  verankert (C2/C4). Härten = wenig neuer Code, maximale Wiederverwendung.
- **B (semantische Selektoren):** Braucht **keine** App-Kooperation — `get_by_role`/`get_by_label`
  hängt an der Accessibility-Tree, die viele Apps ohnehin (a11y-Pflicht) liefern. Koppelt Tests an
  *Benutzer-sichtbare* Semantik statt an Test-Hooks → testet näher am echten Nutzererlebnis.
- **Manifest/Registry (C):** Entkoppelt Spec-ID komplett vom App-Selektor; ein UI-Refactor ändert
  nur das Mapping, nicht jede Spec. Der sauberste Drift-Schutz bei *vielen* Konsumenten.

## Ledger

| id | Aussage | Typ | Evidenz / Falsifikation | Status |
|---|---|---|---|---|
| A1 | Generator nimmt rohen `selector`-String, emittiert `page.locator()` verbatim | Annahme | C1 — gelesen | belegt |
| A2 | `is_fragile_selector` warnt nur (Manifest + `⚠`-print), blockt/transformiert nie | Annahme | C2 — Z.373-374 ist `print`, kein `raise` | belegt |
| A3 | Schema erzwingt keinerlei data-testid-Struktur; `selector` ist freier String | Annahme | C3 — `{"type":"string"}` | belegt |
| A4 | Option A ist bereits akzeptierte weiche Konvention im ADR-Body | Annahme | C4 — ADR-211:478 | belegt |
| A5 | „Manifest" aus der F23-Frage = die unter F18 zurückgestellte Locator-Registry | Annahme | C5 — wortgleiche Beschreibung „Spec nennt fachliche ID, App mappt Selektor" | belegt |
| A6 | F18-Schließungs-Trigger (realer Cross-Repo-UI-Refactor) ist NICHT gefeuert | Annahme | C7 — nur 1 Renderer #2 existiert | belegt |
| A7 | Betroffene Oberfläche heute winzig: nur risk-hub/sds hat reale Asserts+testid | Annahme | C6/C7 | belegt |
| D1 | A bleibt primärer Kontrakt; Warnung wird zum Off-Ramp-Gate (`--strict-selectors`) | Entscheidung | reversibel durch Flag-Entfernung | vorgeschlagen |
| D2 | B als Selektor-Präfix-Fallback (`role=`/`label=`/`testid=`), kein Schema-Bruch | Entscheidung | `selector` bleibt `string`; `render_assertion` mappt Präfix→Locator-API | vorgeschlagen |
| D3 | Manifest/Registry bleibt zurückgestellt — F18 unverändert | Entscheidung | kein zweiter SSoT ohne gefeuerten Trigger (A6) | vorgeschlagen |
| R1 | Strict-Gate ohne erreichbares data-testid blockiert legitime Off-Ramps | Risiko | Mitigation: B-Fallback (D2) ist der Ausweg, nicht Registry | offen |
| R2 | Präfix-Vokabular wird zur Mini-DSL → F17-Lebenszyklus-Pflicht | Risiko | F17-Regel (RFC erzwingt Action/Selektor-Erweiterungsregel) greift | offen |

## MVC (konkret — Dateien/Felder/Gate)

1. **`src/iil_klickdummy/gen_e2e.py` · `render_assertion`** (C1): Präfix-Erkennung im `selector`
   ergänzen — `testid=foo` → `page.get_by_test_id("foo")`, `role=button[name=Verify]` →
   `page.get_by_role("button", name="Verify")`, `label=…` → `page.get_by_label(…)`; **bare String
   bleibt** `page.locator()` (CSS) **+** `is_fragile_selector`-Warnung. `.first`/Strict-Mode-Logik
   unverändert übernehmen.
2. **`src/iil_klickdummy/gen_e2e.py` · `gen_suite`** (C2): neues Flag `--strict-selectors`
   (Default aus). Gesetzt → `len(fragile_selectors) > 0` wird **exit≠0** statt nur `⚠`-print.
   Der Off-Ramp-Pfad (`off_ramp_status`-relevante Specs) setzt das Flag.
3. **`src/iil_klickdummy/schemas/screens-spec.schema.json`** (C3): **keine** strukturelle
   Änderung — `selector` bleibt `string`; das Präfix-Vokabular wird im Schema-`description` +
   `docs/reference/cli.md` dokumentiert (F17-konform).
4. **Tests:** `tests/test_gen_e2e.py` — je ein Mapping-Test pro Präfix + ein
   `--strict-selectors`-exit≠0-Test bei bare-CSS-Selektor.

## Alternativen (verworfen, mit Grund)

| Alt | Inhalt | Warum verworfen |
|---|---|---|
| Alt-1 | **Nur B** — Bridge ganz auf semantische Selektoren umstellen, data-testid raus | Wirft den einzigen real grünen Pfad (C6) weg; semantik bricht bei i18n/Wording-Änderung — verschiebt Fragilität, beseitigt sie nicht |
| Alt-2 | **Manifest/Registry jetzt bauen** | F18 hat das mit SSoT-Doppelquell-Begründung zurückgestellt (C5); Trigger ungefeuert (A6); bei 1 Konsument (A7) reiner Overhead |

## Adversariale Analyse (Advocatus Diabolus)

- **„Doppelquelle?"** D2 könnte eine zweite Wahrheit schaffen (Selektor-DSL neben CSS). Antwort:
  nein — der `selector`-String *bleibt die eine Quelle*, das Präfix ist nur ein Dispatch-Hint
  *innerhalb* desselben Feldes; keine zweite Datei, kein Mapping-Store (das wäre erst die Registry).
- **„Tool wird zur Boundary?"** `--strict-selectors` ist opt-in pro Lauf, der Off-Ramp-Pfad setzt
  es — kein globaler Zwang auf reine Mockup-Specs. Reversibel durch Flag-Entfernung.
- **„Sichtbar machen < verhindern?"** Genau der Punkt: heute ist fragile-count nur *sichtbar*
  (A2). D1 macht ihn am Off-Ramp *verhindernd* — das ist die eigentliche Härtung, die F23 will.
- **„Formal erfüllen, praktisch umgehen?"** Ein Team könnte `testid=`-Präfix setzen ohne echtes
  `data-testid` im Template → Suite wird rot beim Lauf (Locator findet nichts). Der **Ausführungs**-
  Check (nicht der Drift-Check) fängt das — deshalb bleibt „Parität = Suite real laufen lassen"
  (Rev 21 Lesson) der Schlussstein, nicht dieses Gate allein.
- **Verschlimmert es F11/F17/F18/F19?** F17: ja, das Präfix-Vokabular *braucht* die F17-Regel
  (R2) — kein Nettoschaden, sondern dessen erster echter Anwendungsfall. F18: unberührt (D3).

## Maintainer-2028

In 2 Jahren mit 5 echten Renderern #2: Wenn jeder Konsument data-testid liefert, war D1+D2 genug
und die Registry blieb zu Recht ungebaut. Wenn dagegen 3 Repos denselben Selektor bei jedem
UI-Refactor nachziehen müssen, hat F18s Trigger gefeuert → *dann* Registry, mit echtem Beleg statt
Spekulation. Das Konzept hält beide Türen offen und baut keine davon vorzeitig zu.

## Entscheidung + Kill-Gate

- **Entscheidung (vorgeschlagen, deine Ratifikation):** D1 + D2 + D3 (Hybrid). Mündet in eine
  **ADR-211-Revision** (Amendment, kein neuer ADR — verschiebt keine Invariante, härtet die
  bestehende Selector-Konvention + schließt F23, F18 bleibt offen).
- **Kill-Gate (messbar):** siehe `kill_criteria` im Frontmatter — zwei symmetrische Abbruchpfade
  (B-wird-primär ODER Registry-reaktivieren), beide an reale, zählbare Auslöser gebunden.
- **Exception-Budget:** `review_by: 2026-09-30`. Ohne gefeuerten Trigger bis dahin → Konzept
  `sunset`, Hybrid gilt als stabil bestätigt (kein stilles Verlängern).

---
adr_id: ADR-002
title: "iil-klickdummy — Klickdummy Browser-Redesign"
status: accepted
date: 2026-07-02
accepted_date: 2026-07-29
deciders: ["Achim Dehnert"]
tags: [klickdummy, ux, browser]
conforms_to: platform:ADR-211
class: mock
sunset_after: 2027-07-02
extension_review_required: true
sister_of: []
related:
  - iil-klickdummy:ADR-001
---

# ADR-002 — Klickdummy Browser-Redesign (Spec-first, Mock)

## Status

**accepted** (2026-07-29) — der User hat den Klickdummy abgenommen (ADR-251 UX-Gate);
die drei offenen Spec-Fragen sind entschieden (siehe *Abnahme-Entscheidungen*).
Die Reimplementierung war zu diesem Zeitpunkt bereits erfolgt (PR #101), lief aber
formal ohne Abnahme — mit dieser Fassung wird der **Off-Ramp gezogen**: die statische
Mock-Shell `klickdummy/browser/shell.html` entfällt, alle Screens stehen auf
`off_ramp_status: removed`, die Spec bleibt als UX-Vertrag über dem echten Renderer.

## Kontext

Der `klickdummy-browser` (die einzige echte interaktive UI-Fläche des Pakets) ist
heute ein handgeschriebenes HTML-Template mit drei Schulden, die im
`/repo-optimize`-Lauf 2026-07-02 belegt wurden:

1. **S-01 (XSS):** Alle Spec-Felder werden per String-Konkatenation in `innerHTML`
   bzw. `<script>const KLICKDUMMIES = …</script>` gesetzt (`registry.py:372,412`;
   `browser.html.tmpl`). Ein Feld mit `</script>` bricht den Kontext auf.
2. **ADR-048-Anti-Patterns:** durchgängig `onclick=`-Inline-Handler (AP-003),
   Hex-Farben (AP-007), Inline-`style=` (AP-004).
3. **Kein UX-Vertrag:** Das Verhalten existiert nur als Code, nicht als abgenommene Spec.

`/repo-ux-opt B` hat den Browser als Spec-first-Ziel gewählt, weil er echte
Interaktion trägt **und** der Neuaufbau die S-01-Schuld an der Wurzel löst.

## Entscheidung

Klasse **`mock`** — der Klickdummy ist ein Wegwerf-Prototyp zur UX-Abnahme, ohne
Backend/Persistenz. Drei Screens spiegeln die Use-Cases:

- `browser-frei` (UC-001) — Auswahl + Detail + Render
- `browser-story` (UC-002) — geführter Story-Walk mit Stepper
- `browser-versionen` (UC-003) — historische Spec-Version read-only

Hinzu kommt seit der Abnahme:

- `browser-cross-repo` (UC-004) — Sammelliste über mehrere Repos

Der Mock (`shell.html`) realisierte die drei Ziel-Korrekturen als Referenz für die
Implementierung; sie sind mit PR #101 in den echten Renderer übernommen und der Mock
ist mit der Abnahme entfallen (Off-Ramp). Die Korrekturen im Wortlaut:

- **N1 (löst S-01):** Daten als `<script type="application/json">`-Insel + `JSON.parse`;
  DOM aus Daten via `textContent` und geklonten `<template>`-Nodes, **kein**
  `innerHTML`-Concat. Ein Testeintrag mit `title = "x</script><script>…"` bleibt Text.
- **N2 (ADR-048/049):** `--pui-*`-Tokens statt Hex; `addEventListener` + delegierte
  Klicks statt `onclick`; keine Inline-`style=`.
- **N3 (ADR-040):** `data-testid` an jedem interaktiven Element (== Parity-Anker der Spec).

## Abnahme-Entscheidungen (2026-07-29)

| # | Offene Frage | Entscheidung |
|---|---|---|
| AS-1 | Sortierung der Klickdummy-Liste | **Generierungsreihenfolge bleibt** (`discover_klickdummies`). Im Cross-Repo-Modus zusätzlich nach `<org>/<repo>` gruppiert (`<optgroup>`), Reihenfolge innerhalb der Gruppe unverändert. |
| AS-2 | Fehlender `kd_index` im Story-Schritt: Auto-Skip oder Meldung? | **Sichtbare Meldung**, kein Auto-Skip — ein übersprungener Schritt verdeckt einen Spec-Fehler. Der Renderer setzt das um; `registry.py:discover_stories()` verwirft unbekannte Steps aber schon vorher still — als Restarbeit getrackt in [#200](https://github.com/iilgmbh/iil-klickdummy/issues/200). |
| AS-3 | read-only-Kennzeichnung historischer Versionen: Banner im iframe? | **Nur im Detail-Panel** (`testid=version-readonly`), kein iframe-Banner — der Banner überlagerte fremde Shell-Layouts. |
| AS-4 | iframe-Isolation via `sandbox`? | **Kein `sandbox`** — das Feedback-Widget braucht `localStorage`/`fetch` im Frame; `allow-same-origin` + `allow-scripts` wäre wirkungslose Halb-Isolation. Begründung, akzeptiertes Risiko und Neu-Bewertungs-Trigger: `docs/use-cases/NFR-browser.md` §N7. |
| AS-5 | Cross-Repo-Modus: ausbauen oder streichen? | **Ausbauen** als vierter Screen (UC-004): Repo-Gruppierung, Repo im Detail-Panel, GitHub-Links statt eines nicht auflösbaren iframes. |

## Konsequenzen

- **Positiv:** Abnahmefähiger Prototyp vor Code; der Refactor von
  `registry.py`/`browser.html.tmpl` hatte eine geprüfte Zielvorgabe; S-01/AP-Schuld
  wurde beim Neuaufbau strukturell erledigt statt gepatcht.
- **Off-Ramp gezogen (2026-07-29):** `off_ramp_status: removed` je Screen; die statische
  Mock-Shell ist gelöscht. Damit ist die Doppelquelle (Mock **und** echter Renderer)
  aufgelöst, die seit PR #101 bestand und mit Release 1.32.x die eigene
  Doppelquell-Grenze `prod-release` bereits überschritten hatte.
- **Neu ergänzt bei der Abnahme:** `frame-load-error` (N4 war nur zu 2/3 umgesetzt —
  der iframe-Ladefehler fehlte), Tastaturbedienung des Steppers (N6), Cross-Repo-Screen
  (UC-004, verwertet die in `registry.py` längst berechneten, bis dahin von keinem
  Template gelesenen Felder `org`/`repo`/`github_shell_url`/`github_spec_url`).
- **Negativ / Preis:** Der UX-Vertrag lebt jetzt ohne statisches Vorbild; Abweichungen
  fallen nur auf, wenn die Gates laufen. Deshalb fährt das Repo seine eigenen
  Invarianten-Gates ab sofort in CI (`make klickdummy-gates`, Job `klickdummy-gates`) —
  vorher wendete `iil-klickdummy` die Gates, die es an ~13 Repos ausliefert, auf sich
  selbst **nicht** an.

## Bezug

- `platform:ADR-211` (Klickdummy-Rahmen), `platform:ADR-251` (UX-Gate),
  `platform:ADR-048/049/040` (Design-System / Completeness-Gate)
- `iil-klickdummy:ADR-001` (Implementierung des Rahmens)
- Use-Cases: `docs/use-cases/UC-001..003` + `NFR-browser.md`
- `/repo-optimize`-Report 2026-07-02 (Befund S-01): `~/shared/repo-optimize-iil-klickdummy-2026-07-02.md`

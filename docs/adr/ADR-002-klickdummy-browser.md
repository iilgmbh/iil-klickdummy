---
adr_id: ADR-002
title: "iil-klickdummy — Klickdummy Browser-Redesign"
status: proposed
date: 2026-07-02
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

**proposed** — Klickdummy-Spec + Mock existieren; Abnahme durch den User steht aus
(ADR-251 UX-Gate). Erst nach Abnahme folgt die Reimplementierung von
`registry.py` / `snippets/browser/browser.html.tmpl`.

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

Der Mock (`shell.html`) realisiert die drei Ziel-Korrekturen bereits als Referenz
für die spätere Implementierung:

- **N1 (löst S-01):** Daten als `<script type="application/json">`-Insel + `JSON.parse`;
  DOM aus Daten via `textContent` und geklonten `<template>`-Nodes, **kein**
  `innerHTML`-Concat. Ein Testeintrag mit `title = "x</script><script>…"` bleibt Text.
- **N2 (ADR-048/049):** `--pui-*`-Tokens statt Hex; `addEventListener` + delegierte
  Klicks statt `onclick`; keine Inline-`style=`.
- **N3 (ADR-040):** `data-testid` an jedem interaktiven Element (== Parity-Anker der Spec).

## Konsequenzen

- **Positiv:** Abnahmefähiger Prototyp vor Code; der spätere Refactor von
  `registry.py`/`browser.html.tmpl` hat eine geprüfte Zielvorgabe; S-01/AP-Schuld
  wird beim Neuaufbau strukturell erledigt statt gepatcht.
- **Offen (bei Abnahme zu klären):** die `ASSUMPTION[unverified]`-Punkte je UC
  (Sortierung der KD-Liste, Auto-Skip vs. Meldung bei fehlendem Step, read-only-Banner).
- **Off-Ramp:** `off_ramp_status: static` je Screen; Parity-grün pro Screen ⇒ Screen
  in den echten Renderer migrieren (Doppelquell-Grenze: prod-release).

## Bezug

- `platform:ADR-211` (Klickdummy-Rahmen), `platform:ADR-251` (UX-Gate),
  `platform:ADR-048/049/040` (Design-System / Completeness-Gate)
- `iil-klickdummy:ADR-001` (Implementierung des Rahmens)
- Use-Cases: `docs/use-cases/UC-001..003` + `NFR-browser.md`
- `/repo-optimize`-Report 2026-07-02 (Befund S-01): `~/shared/repo-optimize-iil-klickdummy-2026-07-02.md`

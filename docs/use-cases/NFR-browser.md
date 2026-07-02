# NFR & Querschnitts-Anforderungen — `klickdummy-browser`

Gilt für UC-001..003. Diese Anforderungen sind der Grund, den Browser spec-first
neu aufzubauen statt zu patchen — sie adressieren die im Ist-Template verankerten
Schulden.

## N1 — Sicherheit: keine Injektion aus Spec-Daten (löst S-01)

- **Ist:** Alle dynamischen Felder werden per String-Konkatenation in `innerHTML` bzw.
  in ein `<script>const KLICKDUMMIES = …</script>` eingesetzt (`registry.py` +
  `browser.html.tmpl`). Ein Spec-Feld mit `</script>` oder HTML bricht aus dem Kontext.
- **Soll:**
  - JSON sicher einbetten: `<script type="application/json" id="kd-data">…</script>` +
    `JSON.parse`, **oder** `</`→`<\/` beim Serialisieren.
  - DOM aus Daten via `textContent` / geklonte `<template>`-Nodes bauen, **nicht** via `innerHTML`-Concat.
- **Nachweis:** Ein Klickdummy mit `title = 'x</script><script>alert(1)</script>'` und eine
  Entity-`description` mit `<img src=x onerror=alert(1)>` erzeugen sichtbaren Text, kein Script/Event.

## N2 — Design-System-Konformität (ADR-048/049)

- **Ist:** Hex-Farben (`#1a3a6c`, `#d8e0e8` …, AP-007), Inline-`style=` (AP-004),
  `onclick=`-Inline-Handler an jedem interaktiven Element (AP-003).
- **Soll:** Farben/Spacing/Radii über `--pui-*`-Tokens (`--pui-primary`, `--pui-surface`,
  `--pui-border`, `--pui-muted`, `--pui-space-*`); Event-Bindung via `addEventListener`
  (keine Inline-Handler); keine Inline-`style=` außer dynamischer Notwendigkeit.
- **Hinweis:** Der Browser ist ein **standalone, generiertes HTML-Snippet** ohne Django/HTMX-
  Kontext — die HTMX-Constraints des Skills (hx-*) greifen hier nicht; die Token-/AP-Regeln schon.

## N3 — Testbarkeit (ADR-040)

- Jedes interaktive Element via `data-testid` adressierbar (siehe Akzeptanzkriterien je UC).
- Element-Inventar Spec↔Template bei „fertig" vollständig (ADR-040 Frontend-Completeness-Gate).

## N4 — Kein stilles Scheitern

- Definierter, sichtbarer Fehlerzustand bei: fehlendem `kd_index` (UC-002 A2), fehlendem
  Shell-Snapshot (UC-003 A1), iframe-Ladefehler. Kein leerer iframe ohne Hinweis.

## N5 — Read-only-Integrität der Historie

- Historische Snapshots laden **nie** mit `?feedback=on` (kein Co-Creation-Feedback auf alten Ständen).
- Historische Ansicht ist als read-only erkennbar (Detail-Panel; ggf. Banner — offene Spec-Frage UC-003).

## Nicht in diesem Strang

- Der `genesor`-Viewer (Lineage/UC/Cross-Repo-HTML) ist eine **separate** UI-Fläche —
  eigener Modus-B-Strang, falls gewünscht (war Option 2 im `/repo-ux-opt`-Dialog).
- S-02 (Implementation-Brief-HTML) und S-03 (Path-Traversal) gehören zum genesor-Render,
  nicht zum Browser — separat als Issues getrackt (/repo-optimize 2026-07-02).

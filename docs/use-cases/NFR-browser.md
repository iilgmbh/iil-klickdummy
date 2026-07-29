# NFR & Querschnitts-Anforderungen — `klickdummy-browser`

Gilt für UC-001..003. Diese Anforderungen sind der Grund, den Browser spec-first
neu aufzubauen statt zu patchen — sie adressieren die im Ist-Template verankerten
Schulden.

## N1 — Sicherheit: keine Injektion aus Spec-Daten (löst S-01)

- **Ist:** Alle dynamischen Felder werden per String-Konkatenation in `innerHTML` bzw.
  in ein `<script>const KLICKDUMMIES = …</script>` eingesetzt (`registry.py` +
  `browser.html.tmpl`). Ein Spec-Feld mit `</script>` oder HTML bricht aus dem Kontext.
- **Soll:**
  - JSON in einer `<script type="application/json">`-Insel + `JSON.parse`.
  - **⚠️ Insel allein reicht NICHT:** der HTML-Parser beendet **jedes** `<script>`-Element
    (auch `type="application/json"`) an einem literalen `</script>`. Beim Serialisieren
    MUSS daher jedes `</` zu `<\/` escaped werden — `json.dumps(data, ensure_ascii=False).replace("</", "<\\/")`.
    JSON liest `\/` als `/`, der Parser sieht kein Ende-Tag. (Real belegt: die erste
    Mock-Fassung ohne dieses Escaping führte das Payload aus — Browser-Test, nicht Annahme.)
  - DOM aus Daten via `textContent` / geklonte `<template>`-Nodes bauen, **nicht** via `innerHTML`-Concat.
- **Nachweis (verifiziert 2026-07-02, headless):** Ein Klickdummy mit
  `title = 'x</script><script>window.__XSS__=1</script>'` erzeugt sichtbaren Text;
  `window.__XSS__` bleibt `undefined`; das Detail-Panel enthält kein `<script>`-Element.

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
- **Umgesetzt 2026-07-29** (`testid=frame-load-error`): Der iframe-Ladefehler war bis dahin
  als einziger der drei Fälle **nicht** implementiert — ein 404 zeigte einen leeren Rahmen.
  Ein 404 feuert im iframe **kein** `error`-Event (der Browser lädt eine Fehlerseite und
  feuert `load`), deshalb drei Sonden statt einer:
  1. `error`-Event — Netzwerk-/Schema-Fehler,
  2. Watchdog (6 s ohne `load`) — gar keine Antwort,
  3. Same-Origin-Probe nach `load` — leerer `body` ⇒ Fehler; wirft der Zugriff
     (cross-origin), gilt die Seite als geladen.
- Der Render-Bereich hat genau **einen** sichtbaren Zustand (`setMain()`): Leerzustand,
  Fehler, Cross-Repo-Hinweis oder iframe — nie zwei gleichzeitig, nie keinen.

## N6 — Tastaturbedienung (ADR-048 A11y)

- Jedes bedienbare Element muss ohne Maus erreichbar **und** auslösbar sein.
- Die Story-Stepper-Einträge sind `<li>` mit Klick-Handler; sie tragen deshalb
  `role="button"` + `tabindex="0"` und einen `keydown`-Handler für Enter/Space
  (Space mit `preventDefault`, sonst scrollt die Seite).
- Fokus muss sichtbar sein: `:focus-visible`-Ring auf Stepper, Story-Nav, Modus-Toggle,
  Selects und Links.
- Der aktive Schritt trägt `aria-current="step"`, jeder Eintrag ein `aria-label`
  („Schritt N von M: …(besucht)") — Position und Besucht-Status stecken sonst nur in
  Farbe und Icon.

## N7 — iframe-Isolation: bewusst KEIN `sandbox`

- **Entscheidung 2026-07-29 (ADR-002):** Der Klickdummy-iframe bleibt **ohne**
  `sandbox`-Attribut.
- **Grund:** Das Feedback-Widget (`snippets/feedback-widget/widget.js`) läuft *innerhalb*
  der geladenen Shell und braucht `localStorage` (User-PAT unter
  `localStorage.klickdummy_github_token`) sowie `fetch` gegen die GitHub-API. Ein
  `sandbox` ohne `allow-same-origin` nimmt der Shell den Storage-Zugriff und bricht die
  Feedback-Schleife; ein `sandbox` **mit** `allow-same-origin` und `allow-scripts` ist
  für gleichorigine Inhalte praktisch wirkungslos (der Frame kann das Attribut
  effektiv unterlaufen). Halbe Isolation, die Funktion kostet und keine Sicherheit
  bringt, ist schlechter als eine benannte Nicht-Isolation.
- **Damit akzeptiertes Risiko, ausdrücklich benannt:** jede im Browser geladene Shell
  läuft im selben Origin wie die Browser-Seite und kann den PAT aus dem `localStorage`
  lesen. Der Browser ist ein **lokales Review-Werkzeug** über selbst erzeugte Artefakte
  des eigenen Repos, kein Hoster fremden Codes — die Vertrauensgrenze ist das Repo.
- **Gegenmaßnahme statt Sandbox:** Cross-Repo-Inhalte werden **nicht** eingebettet,
  sondern verlinkt (UC-004) — fremde Repos kommen so gar nicht erst in den Origin.
- **Neu zu bewerten**, sobald einer dieser Trigger eintritt: der Browser wird öffentlich
  gehostet (kd.iil.pet o. ä.) **oder** er bettet Shells ein, die nicht aus dem eigenen
  Repo stammen. Dann ist die richtige Antwort ein eigener Origin für die Shells
  (Subdomain/`srcdoc`-Isolation), nicht ein `sandbox`-Attribut.

## N5 — Read-only-Integrität der Historie

- Historische Snapshots laden **nie** mit `?feedback=on` (kein Co-Creation-Feedback auf alten Ständen).
- Historische Ansicht ist als read-only erkennbar (Detail-Panel; ggf. Banner — offene Spec-Frage UC-003).

## Nicht in diesem Strang

- Der `genesor`-Viewer (Lineage/UC/Cross-Repo-HTML) ist eine **separate** UI-Fläche —
  eigener Modus-B-Strang, falls gewünscht (war Option 2 im `/repo-ux-opt`-Dialog).
- S-02 (Implementation-Brief-HTML) und S-03 (Path-Traversal) gehören zum genesor-Render,
  nicht zum Browser — separat als Issues getrackt (/repo-optimize 2026-07-02).

# Use-Cases — `klickdummy-browser`

Spec-first-Arbeitsstrang aus `/repo-ux-opt B` (2026-07-02). Ziel: die einzige echte
interaktive UI-Fläche des Pakets — den **Klickdummy-Browser** (`registry.py` →
`snippets/browser/browser.html.tmpl`) — spec-first neu aufbauen, statt das
gewachsene Inline-JS-Template weiter zu patchen.

## Warum dieser Strang

Der heutige Browser ist ein handgeschriebenes HTML-Template mit drei Eigenschaften,
die ihn zum Modus-B-Kandidaten machen:

1. **Sicherheits-Schuld (S-01, /repo-optimize 2026-07-02):** Alle Felder werden per
   String-Konkatenation in `innerHTML`/`<script>` eingesetzt (`k.title`, `k.spec_id`,
   `k.path`, `step.label` …) — ein Spec-Feld mit `</script>` oder HTML bricht aus.
   Ein Spec-first-Neuaufbau löst das an der Wurzel (sichere JSON-Einbettung +
   `textContent`/Template-Nodes statt `innerHTML`).
2. **Anti-Patterns (ADR-048):** durchgängig `onclick=`-Inline-Handler (AP-003),
   Hex-Farben statt `--pui-*`-Tokens (AP-007), Inline-`style=` (AP-004).
3. **Kein UX-Vertrag:** Verhalten existiert nur als Code, nicht als abgenommene Spec.

## Status & Gate (ADR-251)

⚠️ **Diese Use-Cases sind Entwürfe — noch NICHT abgenommen.** Nach ADR-251 wird
zuerst ein Klickdummy aus diesen UCs gebaut und **vom User abgenommen**, BEVOR
Views/Templates entstehen. Reihenfolge:

1. ✅ UC-Entwürfe (dieses Verzeichnis)
2. ✅ Klickdummy-Spec + Renderer via `/klickdummy`
3. ✅ Abnahme des Klickdummy durch den User (UX-Gate) — 2026-07-29, ADR-002 `accepted`
4. ✅ Implementierung strikt gegen die abgenommene KD-Spec — im echten Renderer
   (`registry.py` + `snippets/browser/browser.html.tmpl`); die statische Mock-Shell ist
   entfallen (Off-Ramp gezogen, alle Screens `off_ramp_status: removed`)

## Use-Cases

| ID | Titel | Kern-Flow |
|----|-------|-----------|
| [UC-001](UC-001-browser-frei-auswahl.md) | Klickdummy im Frei-Modus auswählen & ansehen | Auswahl → Detail → iframe-Render |
| [UC-002](UC-002-browser-story-walk.md) | Story-Walk geführt durchlaufen | Story wählen → Stepper → Prev/Next → Visited-State |
| [UC-003](UC-003-browser-versionen.md) | Historische Spec-Version ansehen | Versions-Dropdown → Snapshot (read-only) oder Hinweis |
| [UC-004](UC-004-browser-cross-repo.md) | Cross-Repo-Sammelliste sichten | `--cross-repo` → Repo-Gruppen → GitHub-Links statt iframe |

Querschnitt (alle UCs): [NFR-browser.md](NFR-browser.md) — Sicherheit, Design-System,
Testbarkeit, Fehlerzustände, Tastaturbedienung.

## Grounding

Verhalten 1:1 aus `src/iil_klickdummy/snippets/browser/browser.html.tmpl` (main @ b7951bb)
und den Render-Funktionen `registry.py:render_*_browser_html` extrahiert — kein erfundenes
Verhalten, sondern der Ist-Zustand als Vertrag formalisiert (plus die drei o.g. Korrekturen).

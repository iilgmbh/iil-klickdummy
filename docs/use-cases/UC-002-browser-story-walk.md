# UC-002 — Story-Walk geführt durchlaufen

- **Status:** Entwurf (nicht abgenommen — ADR-251-Gate offen)
- **Akteur:** Reviewer, der eine zusammenhängende Nutzer-Journey über mehrere Klickdummies abläuft
- **Auslöser:** Umschalten auf „📖 Story-Walk" (Toggle nur sichtbar, wenn `STORIES` nicht leer)
- **Bezug:** `platform:ADR-211` (`story.yaml`, geordnete Schritte über mehrere KDs)

## Vorbedingung

- `STORIES` enthält ≥1 Story mit `id`, `title`, `steps[]`; jeder Step: `label`, `kd_index`.

## Hauptablauf

1. Der Akteur klickt im Modus-Toggle auf **Story-Walk**; die Frei-Panel-Ansicht weicht der Story-Panel-Ansicht.
2. Das System zeigt das **Story**-Dropdown (Anzeige `Titel (N Schritte)`) und lädt die erste Story, Schritt 1.
3. Das System rendert den **Stepper**: je Schritt ein Listeneintrag mit Icon
   (`●` aktiv · `✅` besucht · `○` offen) und Label; darüber „Schritt m / n".
4. Das System lädt den Klickdummy des aktiven Schritts (`kd_index`) rechts ins iframe.
5. Der Akteur navigiert mit **Weiter →** / **← Zurück** oder per Klick auf einen Stepper-Eintrag.
6. Das System markiert besuchte Schritte persistent (localStorage) und aktualisiert die Prev/Next-Buttons
   (Prev disabled auf Schritt 1, Next disabled auf letztem Schritt).

## Alternativabläufe

- **A1 — Story ohne Schritte:** darf nicht in die Liste gelangen (Validierung `klickdummy-stories`);
  in der Spec als Vorbedingung festhalten.
- **A2 — Step referenziert fehlenden `kd_index`:** iframe bleibt leer; Spec muss definierten
  Fehlerzustand vorgeben (heute: stilles Nichtladen — **zu korrigieren**, NFR „kein stilles Scheitern").
- **A3 — localStorage nicht verfügbar:** Visited-State degradiert still (kein Fehler) — Ist-Verhalten, bestätigen.

## Nachbedingung

- Aktiver Schritt, Stepper-Markierung und iframe sind konsistent; Fortschritt überlebt Reload (localStorage).

## Akzeptanzkriterien (F23-Präfixe)

- `testid=mode-toggle` nur sichtbar bei vorhandenen Stories.
- `testid=story-stepper` listet genau `steps.length` Einträge; aktiver Schritt trägt `data-active`.
- `testid=btn-next` auf letztem Schritt `to_be_disabled`; `testid=btn-prev` auf erstem Schritt disabled.
- **A2-Fehlerzustand** zeigt eine sichtbare Meldung (`testid=step-load-error`), kein leerer iframe ohne Hinweis.

## Offene Spec-Fragen (für die Abnahme)

- Soll der Visited-State pro Browser dauerhaft sein (heute localStorage, überlebt Tab-Schließen) oder pro Session?
- A2: Reine Meldung, oder Skip auf den nächsten ladbaren Schritt?

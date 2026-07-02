# UC-001 — Klickdummy im Frei-Modus auswählen & ansehen

- **Status:** Entwurf (nicht abgenommen — ADR-251-Gate offen)
- **Akteur:** Reviewer / Fachbereich / Coding-Agent, der die Klickdummies eines Repos sichtet
- **Auslöser:** Öffnen der generierten `klickdummy-browser`-Seite eines Repos
- **Bezug:** `platform:ADR-211` (Multi-Klickdummy-Browser), `platform:ADR-048/049` (Design-System)

## Vorbedingung

- Der Browser wurde für ein Repo generiert; `KLICKDUMMIES` enthält ≥1 Eintrag mit
  `title`, `spec_id`, `spec_version`, `class`, `path`, optional `adr_local`, `sister_of`, `versions`.

## Hauptablauf

1. Der Akteur sieht links die Sidebar mit Titel, Repo-Label und dem Auswahl-Dropdown
   **Klickdummy** (Platzhalter „— wählen —"). Rechts der Leerzustand „Klickdummy links
   auswählen, um ihn rechts zu laden."
2. Der Akteur wählt einen Klickdummy aus der Liste (Anzeige je Eintrag: `Titel (vX.Y)`).
3. Das System zeigt im Detail-Panel: Spec-ID (`code`) + Version, Klasse als farbiges
   **Badge** (`mock`/`stub-demo`/`story`/`spec-demo`), ADR-Ref (oder „kein ADR-Ref"),
   Schwester-Klickdummies (falls vorhanden), Spec-Pfad.
4. Das System befüllt das **Spec-Version**-Dropdown (UC-003) mit „aktuell (HEAD)" als Default.
5. Das System lädt die aktuelle Shell des Klickdummy in das rechte `iframe`; der Leerzustand verschwindet.

## Alternativabläufe

- **A1 — Auswahl zurückgesetzt:** Wählt der Akteur den leeren Platzhalter, passiert nichts
  (kein Reset des bereits geladenen iframes) — Ist-Verhalten, in der Spec als bewusst zu bestätigen.
- **A2 — Kein ADR-Ref:** Feld zeigt „kein ADR-Ref" statt eines leeren Werts.

## Nachbedingung

- Genau ein Klickdummy ist aktiv; Detail-Panel + iframe spiegeln ihn konsistent.

## Akzeptanzkriterien (Parity-tauglich, F23-Präfixe)

- `testid=kd-select` sichtbar und bedienbar; nach Auswahl `testid=kd-detail` sichtbar.
- Badge trägt die Klasse als stabilen Anker (`testid=kd-class-badge`), Text == `class`.
- `testid=kd-frame` sichtbar (`visible`), nachdem eine Auswahl getroffen wurde.
- **Sicherheit (NFR):** Ein Klickdummy mit `title = 'x</script><script>alert(1)</script>'`
  wird als Text angezeigt, führt **kein** Script aus (Gegenprobe zu S-01).

## Offene Spec-Fragen (für die Abnahme)

- Soll A1 (leerer Platzhalter) den iframe zurücksetzen oder — wie heute — die letzte Auswahl halten?
- Reihenfolge/Sortierung der Klickdummy-Liste (heute: Generierungsreihenfolge) — fachlich sinnvoll?

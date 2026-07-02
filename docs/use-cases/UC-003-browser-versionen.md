# UC-003 — Historische Spec-Version eines Klickdummy ansehen

- **Status:** Entwurf (nicht abgenommen — ADR-251-Gate offen)
- **Akteur:** Reviewer, der die Entwicklung eines Klickdummy über Iterationen nachvollzieht
- **Auslöser:** Auswahl im **Spec-Version**-Dropdown (nach UC-001)
- **Bezug:** `platform:ADR-211` (Iterations-/Versions-Historie)

## Vorbedingung

- Ein Klickdummy ist aktiv (UC-001). `k.versions[]` kann leer sein oder Einträge mit
  `spec_version`, `commit_date`, `commit_sha`, optional `shell_path` enthalten.

## Hauptablauf

1. Das System zeigt „aktuell (HEAD, vX.Y)" als Default plus je historischer Version einen Eintrag
   `vX.Y · <Datum>` (Zusatz „(kein Shell-Snapshot)", wenn `shell_path` fehlt).
2. Der Akteur wählt eine historische Version.
3. Das System aktualisiert das Detail-Panel um „Angezeigte Version": Version, Commit-Datum,
   Commit-SHA (`code`) und den Hinweis **(historisch, read-only)**.
4. Falls ein `shell_path` existiert: iframe lädt den historischen Snapshot **bewusst ohne
   `?feedback=on`** (read-only — kein Co-Creation-Feedback auf alten Ständen).

## Alternativabläufe

- **A1 — Version ohne Shell-Snapshot:** Kein iframe; sichtbarer Hinweis
   „Kein shell.html-Snapshot für vX.Y (nur Spec versioniert)."
- **A2 — Keine Versionen:** Dropdown disabled, nur „aktuell (HEAD)".
- **A3 — Zurück auf „aktuell":** Detail-Panel ohne „Angezeigte Version"; aktuelle Shell lädt neu.

## Nachbedingung

- iframe und Detail-Panel zeigen konsistent entweder HEAD oder genau eine historische Version;
  historische Ansicht ist erkennbar read-only.

## Akzeptanzkriterien (F23-Präfixe)

- `testid=ver-select` disabled, wenn `versions` leer (A2).
- Nach Auswahl einer Version mit Snapshot: `testid=kd-frame` sichtbar; iframe-`src` ohne `feedback=on`.
- A1: `testid=version-no-snapshot` sichtbar, iframe versteckt.
- **Sicherheit (NFR):** `commit_sha`/`commit_date` werden als Text gerendert (kein `innerHTML`-Concat).

## Offene Spec-Fragen (für die Abnahme)

- Soll die read-only-Kennzeichnung auch visuell im iframe-Rahmen erscheinen (Banner), nicht nur im Detail-Panel?

# UC-004 — Klickdummies mehrerer Repos in einer Liste sichten (Cross-Repo-Modus)

- **Status:** abgenommen 2026-07-29 (ADR-002 accepted)
- **Akteur:** Reviewer oder Coding-Agent, der sich einen Überblick über alle Klickdummies
  der Plattform verschaffen will — nicht nur über die eines Repos
- **Auslöser:** `klickdummy-browser --cross-repo --base ~/github` (optional `--repos a,b,c`)
- **Bezug:** `platform:ADR-211`, `iil-klickdummy:ADR-002`; Renderer
  `registry.py:render_cross_repo_browser_html`

## Vorbedingung

- Mehrere Repos unterhalb `--base` enthalten `klickdummy/*/screens-spec.yaml`.
- `discover_cross_repo()` liefert Tripel `(org, repo, KlickdummyMeta)`; die eingebetteten
  Einträge tragen zusätzlich `org`, `repo`, `github_shell_url`, `github_spec_url`.
- `shell_path` bleibt **repo-relativ** und ist von der Sammel-Seite aus nicht auflösbar —
  das ist die zentrale Randbedingung dieses UC.

## Hauptablauf

1. Das System gruppiert die Auswahlliste nach `<org>/<repo>` (`<optgroup>`); innerhalb einer
   Gruppe bleibt die Generierungsreihenfolge erhalten (AS-1).
2. Der Akteur wählt einen Eintrag.
3. Das Detail-Panel zeigt zusätzlich zur Einzel-Repo-Ansicht eine Zeile **Repo** mit
   `<org>/<repo>` (`testid=kd-repo`).
4. Statt eines iframes erscheint im Render-Bereich ein Hinweis-Panel
   (`testid=cross-repo-notice`) mit zwei Links in das Herkunfts-Repo:
   - `testid=link-github-shell` → `github_shell_url` (die Shell auf GitHub)
   - `testid=link-github-spec` → `github_spec_url` (die Spec auf GitHub)
5. Links öffnen in einem neuen Tab (`target=_blank`, `rel=noopener noreferrer`).

## Alternativabläufe

- **A1 — Klickdummy ohne Shell:** `github_shell_url` ist `null`; nur der Spec-Link erscheint.
- **A2 — Weder Shell- noch Spec-URL:** sichtbarer Hinweis „Kein GitHub-Link verfügbar" —
  kein leeres Panel (N4).
- **A3 — Story-Walk im Cross-Repo-Modus:** Stories werden über `discover_cross_repo_stories()`
  eingebettet; ein Schritt, der auf einen Cross-Repo-Eintrag zeigt, führt zum selben
  Hinweis-Panel statt zu einem toten iframe.

## Nachbedingung

- Für jeden gewählten Cross-Repo-Eintrag ist entweder ein iframe **oder** ein Hinweis-Panel
  sichtbar — nie ein leerer Render-Bereich.

## Akzeptanzkriterien (F23-Präfixe)

- `testid=kd-optgroup` vorhanden, sobald Einträge ein `repo`-Feld tragen.
- `testid=kd-repo` im Detail-Panel sichtbar (nur im Cross-Repo-Modus).
- `testid=cross-repo-notice` sichtbar statt `testid=kd-frame`.
- `testid=link-github-shell` / `testid=link-github-spec` verweisen auf
  `https://github.com/<org>/<repo>/blob/main/<pfad>`.
- **Sicherheit (NFR N1):** Titel, Repo-Namen und URLs werden über `textContent` bzw.
  `a.href`/`optgroup.label` gesetzt — kein `innerHTML`-Concat.

## Historie

Vor der Abnahme berechnete `registry.py` `org`/`repo`/`github_shell_url`/`github_spec_url`
bereits, **kein** Template hat sie je gelesen (auch nicht vor dem Redesign-PR #101); der
iframe versuchte stattdessen den repo-relativen `shell_path` zu laden und blieb leer.
Dieser UC schließt genau diese Lücke.

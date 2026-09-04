# Changelog

Alle nennenswerten Änderungen an `iil-klickdummy`. Format lose nach
[Keep a Changelog](https://keepachangelog.com/); Versionierung SemVer.

## 1.41.1 — 2026-09-04

- fix(sitemap): `klickdummy-gen-sitemap` schrieb bei fehlendem 3. Argument (`[repo_name]`) und `repo_root == "."` eine Sitemap-Spec mit leerem Repo-Teil (`spec_id: :klickdummy-spec-sitemap`) — Portal-Ingest safety gate `kd_loss` blockte dms-hub (Run 33877638260). Ursache: `gates.mk`s `klickdummy-sitemap`-Target übergibt `$(KLICKDUMMY_REPO_NAME)` ungeprüft; ist die Variable nicht gesetzt, entfällt das 3. CLI-Argument komplett, und `generate()` fiel auf `repo_root.name` zurück — bei `Path(".").name` ist das `""`. `_resolve_repo_name()` ersetzt den Fallback durch eine Kette (explizites Argument > `git remote get-url origin`-Basename ohne `.git` > `repo_root.resolve().name`) und bricht mit `RepoNameResolveError` (CLI: Exit 2) ab, wenn das Ergebnis leer ist oder `:`/Leerzeichen enthält — nie mehr eine kaputte `spec_id` schreiben. `gates.mk` setzt `KLICKDUMMY_REPO_NAME` jetzt standardmäßig aus `git remote get-url origin`, damit der 3. CLI-Parameter in einem Session-Worktree (Ordnername ≠ Repo-Name) korrekt gefüllt wird. Zusätzliche Positivkontrolle in `generate()`: die geschriebene Sitemap-`spec_id` wird vor dem Schreiben gegen `^[a-z0-9][a-z0-9_-]*:[a-z][a-z0-9_-]*$` geprüft (iilgmbh/iil-klickdummy, dev-hub#320).

## 1.41.0 — 2026-09-04

- fix(snippets): `tailwind-tokens.js` mappt jede Farbfamilie jetzt auf drei Shade-Bänder (hell/mittel/dunkel) statt eines einzigen Kern-Tokens — vorher wurden Status-Badges wie `bg-amber-100 text-amber-800` Text-auf-gleicher-Farbe (unlesbar). `orange` zählt jetzt als Marken-Familie (→ `--kd-primary`/`--kd-accent-1`) statt als Warnfarbe, damit KDs mit Orange als Hauptfarbe nicht komplett in `--kd-warning` landen (iilgmbh/iil-klickdummy#238, risk-hub#736, dev-hub#320 Welle 4 Folgebefund).
- fix(snippets): `tailwind-tokens.js` wirkt jetzt tatsächlich mit dem echten Tailwind Play CDN, unabhängig von der Ladereihenfolge zu `tailwind.js` — empirisch (cdn.tailwindcss.com 3.4.17) geprüft, dass ein VOR dem Laden gesetztes `window.tailwind.config` beim Bootstrap von `tailwind.js` komplett verworfen wurde; die bis dahin dokumentierte „immer davor"-Reihenfolge war für einen frisch vom Play CDN vendorten `tailwind.js` wirkungslos. Fix: die Config wird jetzt zusätzlich per `load`-Event auf dem `tailwind.js`-Geschwister-Script erneut angewendet, mit einem auf ~2s gedeckelten Polling-Fallback + `console.warn`, falls kein solches Script gefunden wird. `check_i5.py` Regel 2 prüft entsprechend nur noch, ob `tailwind-tokens.js` überhaupt eingebunden ist, nicht mehr die Reihenfolge (iilgmbh/iil-klickdummy#241).

## 1.40.1 — 2026-09-04

- fix(snippets): `kd-nav.js` escapt Titel und Tour-Links vor `innerHTML` (CodeQL `js/xss-through-dom`, gemeldet in risk-hub#736; Stelle bestand seit v1.35.0).

## [Unreleased]

## [1.40.0] - 2026-09-04

### Added

- **Feedback-Widget (`widget.js`) und Klickdummy-Browser
  (`browser.html.tmpl`) auf `var(--kd-*)`-Tokens umgestellt — keine
  Hex-Literale mehr (dev-hub#320 Welle 3 Teil 3, Analogie zu `kd-nav.js`
  #233).** `widget.js` (55 Hex-Treffer vorher) lädt `tokens.css` relativ zum
  eigenen Skriptpfad nach (`document.currentScript.src`, wie `kd-nav.js`),
  bewusst kein Hex-Fallback. `browser.html.tmpl` (31 Hex-Treffer vorher) ist
  ein eigenständiges Dokument (kein Host-Skript) — ein Bootstrap-Script im
  `<head>` lädt `_shared/tokens.css` relativ zur eigenen Dokument-URL nach
  und setzt `[data-theme="dark"]` auf `<html>` anhand der OS-Präferenz
  (`matchMedia`), sodass die `--pui-*`-Bridge (ADR-049) weiter funktioniert
  und Dark Mode weiter automatisch reagiert — der Wert selbst kommt jetzt
  aus tokens.css' optionalem `[data-theme="dark"]`-Block statt aus einem
  zweiten hartkodierten Hex-Satz. Layout/Verhalten unverändert, bestehende
  Tests bleiben grün.
- **`klickdummy-i5`: Regel-2-Ausnahme für token-gemapptes Tailwind
  (iilgmbh/iil-klickdummy#232-Analogie, dev-hub#320 Welle 4).** Neues
  Snippet `snippets/_shared/tailwind-tokens.js` mappt vor dem Laden von
  `tailwind.js` jede Tailwind-Farbfamilie (Play-CDN-Palette, Stufen 50–950)
  auf `var(--kd-*)`-Tokens (Marken-Familien → primary/-dark/accent-1,
  Grau-Familien nach Shade → bg-light/zebra/border/line/text/-muted,
  Status-Familien → success/warning/danger/info mit CSS-Fallback-Kette auf
  ein Kern-Token). `check_i5.py` Regel 2 erkennt ein vorhandenes
  `_shared/tailwind-tokens.js`, prüft Familien-Abdeckung root-weit (fehlende
  Familie → Fehler mit Namen) und pro Datei die Script-Reihenfolge
  (`tailwind-tokens.js` muss vor `tailwind.js` laden, sonst „Mapping nicht
  geladen: <datei>") — sind beide erfüllt, gelten Tailwind-Farbklassen als
  token-gemappt statt als Fehler. Ohne `tailwind-tokens.js` im Baum bleibt
  Regel 2 unverändert scharf. Verifiziert gegen eine Kopie von
  risk-hub/klickdummy (24 KD, 10 tatsächlich genutzte Farbfamilien, 296
  Hex-Treffer aus Regel 4 unverändert rot): mit `_shared/tailwind-tokens.js`
  installiert und in `art15-vorgang/index.html` vor `tailwind.js`
  eingebunden meldet Regel 2 für diese Datei „token-gemappt (10 Familien)",
  für die übrigen 36 Dateien „Mapping nicht geladen".

## [1.39.0] - 2026-09-04

### Added

- **`klickdummy-i5`: Regel (4) „Farben nur aus Tokens" — Hex-Farbwerte
  gegated (iilgmbh/iil-klickdummy#232, dev-hub#320 Welle 3).** `check_i5.py`
  prüft jetzt zusätzlich alle `*.css`/`*.js` (neben `*.html`) unter den
  übergebenen Klickdummy-Verzeichnissen auf literale Hex-Farbwerte
  (`#abc`, `#a1b2c3`, optional `#a1b2c3d4`) — außer in `_shared/tokens.css`,
  `_shared/semantic.css`, `assets/tokens.css`, `assets/semantic.css` (dort
  ist der Hex-Wert die Quelle). Die Meldung nennt je Datei die Trefferanzahl,
  damit ein Repo den Umbau planen kann — gedacht für die Welle-3-Shells
  (eigene Klickdummy-Shells in 11 Repos, 10–55 Hex-Treffer je Datei).
  Issue-Referenzen (`#320`) und CSS-Anker (`#fb-fab`) lösen bewusst keinen
  Treffer aus: 3-stellige Hex-Kandidaten brauchen mindestens einen
  a-f-Buchstaben, 6-/8-stellige zählen immer (Issue-Nummern sind ≤ 4
  Ziffern), ein Bindestrich (`#fb-fab`) bricht die Hex-Ziffernfolge ohnehin.
  `sitemap/index.html` bettet `tokens.css` roh als ersten `<style>`-Block
  ein — statt die ganze Datei auszunehmen (das würde eine von Hand gesetzte
  Farbe im selben File nie fangen), wird nur der EINE `<style>`-Block
  ausgeblendet, dessen Inhalt mit der Generator-Kopfzeile beginnt
  (`/* tokens.css — generiert aus design-hub-Profil`); der Rest der Datei
  bleibt im Scan.

## [1.38.0] - 2026-09-04

### Added

- **`klickdummy-i5`: Laufzeit-Gate gegen CDN und Tailwind-Farbklassen
  (iilgmbh/iil-klickdummy#232, dev-hub#320 Welle 3).** Neuer Check
  `check_i5.py` (Console-Script `klickdummy-i5 <klickdummy_dir> [...]`) prüft
  alle `*.html` unter den übergebenen Klickdummy-Verzeichnissen (inkl.
  `sitemap/`, ohne `dist/`/`_archiv/`/`archive/`): (1) kein
  `<script src="http(s)://...">`/`<link href="http(s)://...">`, (2) keine
  Tailwind-Farb-Utility-Klassen (`text-blue-600` etc.), (3) liegt
  `_shared/kd-nav.js` vor, muss `_shared/tokens.css` daneben existieren.
  `snippets/gates.mk` bekommt dafür ein neues Target `klickdummy-i5`; der
  reusable Workflow `klickdummy-parity-gate.yml` ruft es automatisch mit auf
  (kein lokaler Makefile-Edit für Adopter dieses Workflows nötig). Der lokale
  `klickdummy:`-Composite-Target (I1-I4) bleibt dagegen handgepflegt je Repo
  — dort muss `klickdummy-i5` weiterhin manuell ergänzt werden.

### Changed

- **`kd-nav.js` auf `var(--kd-*)`-Tokens umgestellt (dev-hub#320 Welle 3).**
  Alle 8 vormals fest verdrahteten Hex-Farbwerte (Hauptmenü-/Zurück-Button,
  Tour-Footer, TOUR-Badge, prev/next/exit) sind durch Kern-Tokens ersetzt
  (`--kd-text[-muted]`, `--kd-bg-light`, `--kd-primary[-dark]`,
  `--kd-accent-1/-2`); keine Ampel-/Statusfarbe wird gebraucht (reines
  Navigations-Chrome). Beim Start prüft das Skript per `getComputedStyle`,
  ob `--kd-primary` auf `:root` definiert ist; fehlt sie, lädt es
  `_shared/tokens.css` relativ zum aufgelösten Skriptpfad
  (`document.currentScript.src`) nach — bewusst kein Hex-Fallback,
  `klickdummy-i5` macht ein fehlendes `tokens.css` sichtbar statt es zu
  kaschieren.
- **`gen_tokens.py`: optionale Ampel-/Statusfarben dokumentiert.**
  `colours.success/warning/danger/info` im design-hub-Profil werden — wie
  jeder andere `colours`-Key — generisch als `--kd-success` etc. gerendert
  (keine neue Sonderbehandlung nötig, `_colour_lines` war schon generisch);
  fehlen sie im Profil, gibt es die Variablen schlicht nicht.

## [1.37.0] - 2026-09-04

### Changed

- **`klickdummy-sitemap` ohne CDN — Tokens statt Tailwind/lucide (dev-hub#320
  Welle 0).** Die generierte Sitemap lud bisher `cdn.tailwindcss.com` und
  `unpkg.com/lucide` und färbte sich über Tailwind-Utility-Klassen
  (`text-orange-600` etc.). Jetzt ist die Sitemap self-contained: Layout aus
  einem eingebetteten `<style>`-Block, der ausschließlich `var(--kd-*)`-Tokens
  nutzt; Icons als Text-Marker (`→`, `↳`) statt Icon-Font. Neue
  `klickdummy-gen-sitemap`-Optionen `--tokens-css <pfad>` (Datei roh als
  ersten `<style>`-Block einbetten) und `--profile <yaml>` (design-hub-Profil
  zur Laufzeit über `gen_tokens.generate()` einbetten); ohne beide Optionen
  IIL-Fallback aus `<design-hub>/profiles/iil-extern.yaml`
  (`--design-hub <dir>`, Default `$GITHUB_DIR/design-hub` sonst
  `~/github/design-hub`) — fehlt die Datei, Exit 2 mit Meldung statt einer
  Sitemap ohne Farben. `generate()` bekommt dafür einen optionalen
  `tokens_css`-Parameter; die Auflösung selbst bleibt CLI-Sache.

## [1.36.0] - 2026-09-03

### Added

- **`klickdummy-tokens`: design-hub-Profil → `tokens.css` (dev-hub#320).**
  Neues CLI liest ein design-hub-Profil (`profiles/<slug>.yaml`, Source of
  Truth für Klickdummy-Corporate-Design) und erzeugt deterministische
  CSS-Custom-Properties (`--kd-*`). `--check` vergleicht byte-genau gegen
  eine bestehende Ausgabedatei (CI-Gate, Exit 1 bei Abweichung); fehlende
  Pflichtschlüssel oder ungültige Farbwerte enden mit Exit 2.

## [1.35.0] - 2026-08-02

### Changed

- **Sitemap entdoppelt verschachtelte Wurzeln und gruppiert nach Domäne.**
  Ein KD mit `spec_role: root`, der gleichzeitig als `kd_children` eines anderen
  KDs referenziert ist, erschien doppelt: als eigene Wurzel-Tabelle UND als
  Kind-Zeile (Realfall risk-hub 2026-08-02: 18 Wurzeln bei 27 Knoten, 9 doppelt).
  Solche Roots werden jetzt nur noch verschachtelt gerendert (Rolle `sub-root`,
  rekursiv über beliebige Tiefe — Kinder herabgestufter Roots waren vorher nur
  über deren eigene Tabelle sichtbar); `kd-tree.json` hält sie transparent in
  `demoted_roots` fest. Neu außerdem: optionales Spec-Feld `domain:` —
  deklariert mindestens eine Wurzel eine Domäne, gruppiert die Sitemap unter
  Domänen-Überschriften (`domain-<slug>`, alphabetisch, Rest unter „Weitere
  Bereiche"); ohne Deklaration bleibt die flache Liste unverändert.

## [1.34.0] - 2026-07-30

### Changed

- **`klickdummy-sync` chunkt lange ADRs, statt sie zu kappen ([#199](https://github.com/iilgmbh/iil-klickdummy/issues/199),
  [#207](https://github.com/iilgmbh/iil-klickdummy/pull/207)).** Bisher deckelte
  `_content_preview()` den Entry-Content bei 8000 Zeichen; im Lauf vom 2026-07-29
  verloren vier Entries Inhalt, bei `design-hub:ADR-007` zwei Drittel des Dokuments —
  und bei einem MADR liegen Rationale, Konsequenzen und Alternativen hinten, also genau
  der Teil, der die semantische Suche trägt. `_chunk_content()` schneidet jetzt an
  `##`-Sektionsgrenzen in mehrere Entries (`…:ADR-007`, `…:ADR-007#2`, Titel
  `(Teil 2/4)`). Alle Chunks tragen dieselben ADR-Tags und bleiben einzeln auffindbar.

  Der 8000er-Deckel **bleibt**, und das ist der Kern: der harte Constraint ist ein
  *Token*-Limit des Embedding-Providers, kein Zeichen-Limit. Der Store gibt den Content
  ungekürzt an `embed_with_retry()` weiter; scheitert das Embedding, wird der Entry
  trotzdem geschrieben — aber ohne Vektor, und `search()` filtert auf
  `embedding IS NOT NULL`. Überschreiten ist damit schlimmer als Kürzen. Gemessen
  (tiktoken `cl100k_base`): deutsches ADR-Markdown liegt bei 3,05–3,20 Zeichen/Token,
  und das größte bekannte ADR lag mit 7969 Token bereits bei 97,3 % des 8191er-Limits —
  ein bloß angehobener Deckel hätte 222 Token Reserve gehabt.

  **Kompatibilität:** Chunk 1 behält den unsuffixierten `entry_key`, die im Store
  liegenden Entries bleiben dieselben Objekte. Alle Contents, die schon bisher passten,
  bleiben byte-identisch — der `content_hash`-Dedup greift weiter, kein
  Re-Embedding-Churn.

  Verifiziert gegen echte Daten (20 Repos, 243 Entries): 0 Kürzungs-Marker, alle vier
  vormals gekappten ADRs verlustfrei, kein Chunk über 8191 Token. Nebenfund:
  `platform:ADR-211` (102 049 Zeichen) war zu 92 % unsichtbar und ergibt jetzt 17 Chunks.

  Bekannte Restlücke: schrumpft ein ADR wieder unter eine Chunk-Grenze, bleiben höhere
  `#N` stale im Store ([#205](https://github.com/iilgmbh/iil-klickdummy/issues/205)) —
  dieser Produzent emittiert nur Upserts, keine Soft-Deletes.

## [1.33.0] - 2026-07-29

### Added

- **Browser: Deep-Link (N9).** Auswahl und Story-Schritt stehen im URL-Fragment
  (`#kd=<name>`, `#story=<id>&step=<n>`); Reload landet dort wieder, ein Link auf
  „Schritt 3" ist teilbar. Geschrieben per `replaceState` (kein History-Spam).
  **Mit `hashchange`-Listener:** ein Wechsel nur des Fragments ist eine
  Same-Document-Navigation — ohne den Listener änderte sich real nur die URL,
  die Ansicht blieb stehen (im Browser beobachtet, nicht hergeleitet).
- **Browser: Textfilter über der Auswahlliste (N8).** Filtert über Titel, KD-Name,
  Spec-ID, Pfad, Repo/Org und Klasse, mit Trefferzahl und sichtbarer Meldung bei
  null Treffern. Die aktive Auswahl bleibt erhalten, solange sie durchkommt.
- **Browser: Fortschritt zurücksetzbar + repo-skopiert (N10).** Der Besucht-Status
  lag unter `kd-story-visited:<story>:<n>` ohne Repo-Bezug — mehrere Browser-Seiten
  unter derselben Origin (kd.iil.pet) überschrieben sich gegenseitig. Schlüssel
  trägt jetzt das Repo-Label; `↺ Fortschritt zurücksetzen` löscht nur dieses Präfix.
- **Browser: Responsive + Dark Mode (N11).** Unter 720px liegt die Sidebar oben
  statt links (vorher blieb neben 320px fixer Leiste kein Renderbereich); Dark Mode
  über `prefers-color-scheme`, umdefiniert werden nur die `--pui-*`-Tokens.
- **Browser: Cross-Repo-Modus ausgebaut (UC-004).** `registry.py` berechnete
  `org`/`repo`/`github_shell_url`/`github_spec_url` seit v1.3, **kein** Template hat
  sie je gelesen — der iframe versuchte stattdessen den repo-relativen `shell_path`
  zu laden und blieb leer. Neu: Auswahlliste nach `<org>/<repo>` gruppiert
  (`<optgroup>`), Repo-Zeile im Detail-Panel (`testid=kd-repo`) und ein Hinweis-Panel
  mit GitHub-Links zu Shell und Spec (`testid=cross-repo-notice`,
  `link-github-shell`, `link-github-spec`) statt eines toten iframes.
- **Browser: sichtbarer iframe-Ladefehler (N4, `testid=frame-load-error`).** Bisher
  war von den drei in NFR N4 geforderten Fehlerzuständen nur zwei umgesetzt; ein 404
  zeigte einen leeren Rahmen. Ein 404 feuert im iframe kein `error`-Event, deshalb
  vier Sonden: gleichoriginer `HEAD`-Vorabcheck (echter HTTP-Status), `error`-Event,
  Watchdog (6 s) und Same-Origin-Probe auf leeren Body. Der Render-Bereich hat jetzt
  genau einen sichtbaren Zustand (`setMain()`).
- **Browser: Tastaturbedienung des Story-Steppers (N6).** Stepper-Einträge waren
  klickbare `<li>` ohne `tabindex`/`role` — per Tastatur unerreichbar. Neu
  `role="button"` + `tabindex="0"` + Enter/Space-Handler, `aria-current="step"`,
  `aria-label` je Schritt und sichtbarer `:focus-visible`-Ring.
- **Eigene Klickdummy-Gates in CI** (`make klickdummy-gates`, Job `klickdummy-gates`):
  I1, I3 und Parity-Suiten-Drift laufen jetzt gegen `klickdummy/browser/`. Das Repo
  liefert diese Gates an ~13 Repos aus, wandte sie aber nicht auf sich selbst an. Der
  Drift-Check prüft zusätzlich auf **ungetrackte** Suiten (`git diff` sieht die nicht —
  Blind-Gate-Muster).

### Changed

- **ADR-002 `accepted`, Off-Ramp gezogen.** Die statische Mock-Shell
  `klickdummy/browser/shell.html` ist entfallen; alle Screens stehen auf
  `off_ramp_status: removed`. Der Mock und der echte Renderer waren seit PR #101
  inhaltsgleiche Doppelquellen ohne Drift-Gate — mit Release 1.32.x war die in der
  Spec deklarierte Doppelquell-Grenze `prod-release` bereits überschritten. Die
  Spec bleibt als UX-Vertrag über dem echten Renderer.
- Entschieden bei der Abnahme (ADR-002 AS-1…AS-5), vorher `ASSUMPTION[unverified]`:
  Sortierung der KD-Liste, Meldung statt Auto-Skip, read-only nur im Detail-Panel,
  **kein** `sandbox` am iframe (Begründung + Neu-Bewertungs-Trigger: NFR §N7),
  Cross-Repo ausbauen statt streichen.
- `klickdummy/browser/screens-spec.schema.json` war eine veraltete Kopie des
  Paket-Schemas (fehlende `description`s, alte `sister_of`/`title`-Pattern) — jetzt
  1:1 synchron.

### Fixed

- **`discover_stories()` verwarf Story-Steps mit unbekanntem `kd` still** (nur
  `stderr`-Warnung) — die Story wirkte im Browser vollständig und war nur kürzer.
  Das widersprach ADR-002 AS-2 („Meldung statt Auto-Skip"), weil der vorhandene
  sichtbare Fehlerzustand gar nicht mehr erreicht werden konnte. Steps bleiben
  jetzt mit `unresolved: true` erhalten; der Browser benennt die Ursache konkret
  („kein Klickdummy namens X in diesem Repo"). Im `stories-manifest.json` erzeugen
  sie keinen Banner-Eintrag und sind für Nachbar-Steps kein Navigationsziel. (#200)

## [1.32.6] - 2026-07-27

### Fixed

- `gen_sitemap.py`: **Sitemap renderte leer.** Wurzeln wurden nur aus Specs mit
  `spec_role: root` gesammelt; das Feld ist optional und defaultet auf
  `"branch"`. Repos ohne explizite Rolle hatten `roots=[]` → `order=[]` → die
  Seite zeigte sichtbar `0 Wurzeln · 0 Knoten gesamt` und keine einzige
  Tabellenzeile, obwohl `kd-tree.json` Knoten enthielt. Betroffen waren 8 von
  10 ausgerollten Repos. Neu: ohne explizite Wurzel gelten alle elternlosen
  Knoten als Wurzeln (explizite Wurzeln behalten Vorrang).
- `gen_sitemap.py`: Waisen-Warnblock wird gegen die tatsächlichen Wurzeln
  gerechnet statt gegen `spec_role` — sonst stünde bei aktivem Fallback
  dieselbe Spec gleichzeitig als Wurzel-Tabelle und als Fehler-Warnung da.
- `gen_sitemap.py`: Zyklen-Schutz im Tour-DFS. `kd_children` ist freier
  Spec-Inhalt; zwei Specs, die sich gegenseitig als Kind führen, lösten bisher
  einen `RecursionError` aus.

### Added

- `snippets/kd-nav.js` wird als Paket-Asset ausgeliefert und von
  `klickdummy-gen-sitemap` nach `klickdummy/_shared/kd-nav.js` geschrieben.
  Die generierte Sitemap band das Script schon immer ein, aber die Datei lag
  nur historisch in risk-hub — in 9 von 10 ausgerollten Repos war das
  `<script src>` ein 404 und Hauptmenü-Button + Tour-Modus liefen dort nie.

## [1.32.5] - 2026-07-27

### Fixed

- `screens-spec.schema.json` + `check_i4.py`: Repo-Teil von `spec_id`,
  `adr.local` und `adr.sister_of[]` darf mit einer **Ziffer** beginnen
  (`137-hub:ADR-002`). Bisher erzwang `^[a-z]` einen Buchstaben — echte
  Repo-Namen wie `achimdehnert/137-hub` waren dadurch nicht abbildbar und
  brauchten ad-hoc-Aliase ohne Konvention (Issue #179). Schema und I4-Checker
  wurden gemeinsam gelockert — sonst hätte das Schema `137-hub:ADR-002`
  akzeptiert, während I4 dieselbe Referenz als *lokale* ADR gelesen hätte.
- `sync_to_orchestrator.py`: `entry_key`-Dedup läuft jetzt **einmal über alle
  Repos** statt pro Repo. Duplikate aus zwei Repo-Roots mit identischem
  `org/repo` (Kopie oder stale Worktree in der `--repos`-Liste) überlebten
  bisher bis ins NDJSON; Konsumenten upserten in Dateireihenfolge
  (last-write-wins), wodurch die **ältere** Variante gewann (Issue #188,
  Lauf 2026-07-24: 143 Zeilen → 134 eindeutige Keys). `sync_repo()` bekommt
  dafür `dedup=False`, damit die Präzedenz-Felder bis zum Aggregat-Lauf
  erhalten bleiben.
- `sync_to_orchestrator.py`: ADR-Content-Vorschau schneidet nicht mehr
  markerlos bei 8000 Zeichen ab (`ADR-046` endete mitten in `## Refe`) —
  neu mit `… [gekürzt: N weitere Zeichen]` (Issue #188, Zweitbefund).

## [1.32.4] - 2026-07-15

### Added

- `render_genesor.py`: Cross-Link von der zentralen genesor-Übersicht auf die
  neue Pro-Repo-KD-Sitemap (`klickdummy-gen-sitemap`) — nur wenn im Ingest-
  Checkout tatsächlich generiert, sonst kein toter Link. Erster Schritt aus
  dem genesor/kd-Konsolidierungsvorschlag (KONZ folgt für Stufe 2).

## [1.32.3] - 2026-07-15

### Fixed

- `gen_sitemap.py`s Sitemap-Links (`→ öffnen`) öffneten via `target="_blank"` einen neuen
  Tab — auf iOS Safari (u.a. hinter Cloudflare Access) öffnet das oft einen stillen
  Hintergrund-Tab ohne sichtbare Reaktion, wirkt wie ein toter Link. Jetzt Same-Tab-Navigation.

## [1.32.2] - 2026-07-15

Sammeleintrag für PR #148–#158 (gemergt 2026-07-08) + PR #166–#172 (gemergt 2026-07-13,
`/issues-offen`-Lauf gegen den cross-repo Schema-WARN-Sammel-Issue #165) + den
`gen_sitemap.py`-shell.html-Fix (#181) — Versions-Bump jetzt bewusst getroffen (KD-Sitemap-
Rollout über 8 Repos brauchte den Fix als Release, nicht nur als Source-Änderung).

### Fixed

- `gen_sitemap.py` erkannte Specs mit `shell.html`-Renderer (neuere `/klickdummy`-Skill-Kette,
  genesor-Render) nicht — nur `index.html` wurde geprüft, betroffene Specs fielen lautlos aus
  dem Scan, `kd-tree.json` blieb leer (0 Knoten) in 8/8 Repos des Sitemap-Rollouts (#181)
- `manage.py`-Warnings-Zähler, `check_i4.py`-Code-Block-Ausnahme, `inventory.py`-Self-Scan (A-02/A-03/A-05, #155)
- `date.today()`-Determinismus in 7 genesor-Render-Funktionen + `sync_to_orchestrator.py`-Timestamp brach Sync-Idempotenz (S-04/S-05, #156)
- `install_snippets.py`-Deprecation-Pfad (im Zuge der CLI-Fehlerzweig-Tests, #152)
- `extract_requirements.py`-Fehlerbehandlung bei ungültigem YAML (im Zuge der Loader-Konsolidierung, #158)
- `gen_e2e`-Manifest `date.today()`-Determinismus, dritte Instanz desselben Musters nach #145/#156 (#160, #166)
- `klickdummy-sync` Duplikat-Keys — `adr_entries()` fand ADR-Kopien in versteckten Worktree-Verzeichnissen mit; Versions-Doppelemission bei zwei Spec-Dateien im selben KD-Verzeichnis (#163, #167)
- `gen_sitemap.py`s Selbstreferenz-Skip-Guard griff nie (Namens-Mismatch `index.screens-spec.yaml` vs. real geschriebenem `screens-spec.yaml`) — Idempotenz-Sprung 0→1 Knoten bei Sitemap-Erstanlage (#170, #171)
- `adr.sister_of`-Pattern zu eng — erlaubte nur `<repo>:ADR-NNN`, jetzt auch `<repo>:klickdummy-spec-<slug>` (#165 Teil, #172)

### Changed

- 7 unabhängige Spec-YAML-Loader zu einem konsolidiert (A-01, #158)
- Publish-Smoke-Test läuft gegen das gebaute Wheel statt `PYTHONPATH=src` (fängt Packaging-Bugs früher, #154)
- `pyproject.toml` package-data: `snippets/*`-Glob ergänzt — Top-Level-Dateien direkt unter `snippets/` fehlten im gebauten Wheel, obwohl jede editable-install-basierte lokale Prüfung sie fand (#162, #169)

### Added

- `Makefile` + `CONTRIBUTING.md` als kanonischer Test-/Lint-Einstieg (#149)
- 31 Smoke-Tests für 13 zuvor ungetestete `genesor/`-Module (#151)
- CLI-Fehlerzweig- + `main_cli()`-Entry-Point-Tests (T-01/T-02/R12, #152)
- Schema-Descriptions für Top-Level-Pflichtfelder + feedback-payload-Kernfelder (D-6, #157)
- Neues CLI `klickdummy-detect` — Auto-Brownfield-Existenzdetektor (L1 Slug-Grep über `src/`, L2 Django-App-/Routen-Introspektion via neue `from_django.discover_app_dirs()`), inkl. wachsendem Detection-Corpus für künftige False-Negative-Fälle (#161, #168)
- `gates.mk` + reusable GitHub-Actions-Workflow `klickdummy-parity-gate.yml` — ausrollbarer Parity-/Sitemap-Drift-Gate-Baustein für Adopter-Repos, Bootstrap-Target bewusst NICHT im `include`-baren Snippet (Bootstrapping-Paradox, `include` wird beim Parsen ausgewertet) (#162, #169)

### Security

- Third-Party-Actions in `publish-pypi.yml`/`stale.yml` auf Commit-SHA gepinnt (#148)

### CI

- `[tool.ruff]` + `pytest`-`filterwarnings`-Gate ergänzt (#150)

## [1.32.1] — 2026-07-07

### Fixed

- **`klickdummy-gen-sitemap` Determinismus-Bug** (gefunden bei der ersten
  echten Adoption in risk-hub, `klickdummy-parity-drift` schlug rot):
  `spec_date` wurde bei **jedem** Lauf auf `datetime.date.today()` gesetzt,
  auch ohne inhaltliche Änderung — das ließ die Spec-SHA256 im abhängigen
  `klickdummy-gen-e2e`-Output bei jedem CI-Rerun driften (ADR-211
  §Executable-Parity-Bridge verlangt Determinismus, kein Zeitstempel-Rauschen).
  Fix: `spec_date` wird aus einer bestehenden `sitemap/screens-spec.yaml`
  übernommen, wenn vorhanden — nur bei Erstanlage `heute`. Zwei Regressions-
  tests ergänzt (byte-identischer Rerun; Datum bleibt stabil auch wenn sich
  der KD-Baum ändert).

## [1.32.0] — 2026-07-07

### Added

- **`klickdummy-gen-sitemap`** (extrahiert aus risk-hub `scripts/gen_kd_sitemap.py`,
  Rev 13): repo-agnostischer Sitemap-/`kd-tree.json`-Generator. CLI:
  `klickdummy-gen-sitemap <repo_root> <adr_local> [repo_name]`. Baut die KD-Baum-
  Hierarchie aus `kd_children`, rendert `klickdummy/sitemap/index.html` +
  `screens-spec.yaml` (ADR-211 I1) + `klickdummy/_shared/kd-tree.{json,js}`.
  Repo-Name/ADR-Referenz sind jetzt Parameter statt hartkodiert (risk-hub hatte
  "risk-hub" + `risk-hub:ADR-046` fest verdrahtet) — folgt der Extraktions-
  Konvention aus Rev 15 (`gen_stories_manifest.py`-Vorbild). Motivation: risk-hub-
  Sitemap war 6 Wochen alt und fehlte die halbe DSB-KD-Welle, weil das Skript nur
  repo-lokal existierte und niemand zuverlässig daran dachte, es neu laufen zu
  lassen — Cross-Repo-Verfügbarkeit ist Vorbedingung für das geplante CI-Freshness-
  Gate (ADR-211 Amendment, separater platform-PR).

### Fixed

- **Retro-Nachtrag 2026-07-06 (Befunde 6/7/9/10):** `read_model.py` guardet den
  `jsonschema`-Import jetzt wieder (fatal mit freundlicher Setup-Meldung statt
  rohem Traceback) — betrifft insbesondere den Direkt-Source-Checkout-Aufruf
  aus `iil-pet-portal/scripts/regen-genesor-main.sh`. `gen_e2e.py`s
  Re-Export-Import von `_load_schema` ist jetzt präzise auf `noqa: F401`
  gescoped (nur der tatsächlich unbenutzte Name, `validate_spec` braucht die
  Ausnahme nicht). 3 fehlende Regressionstests ergänzt: `_warn_schema_violations`
  über die meiki-Konvention und `find_specs()` (vorher nur 1 von 3
  Aufrufstellen end-to-end getestet), sowie `render_cross_repo_browser_html`
  gegen einen bösartigen `base_label` (vorher nur `render_browser_html`
  regressionsgetestet).
- **`klickdummy_sync.py` Mindest-Sanity-Check (Issue #138):** eine Spec ohne
  `spec_id`/`screens` wird jetzt sichtbar übersprungen (`SKIP ... Pflichtfelder
  fehlen`) statt kommentarlos ein GitHub-Issue mit leerem Titel zu erzeugen.
  Bewusst **keine** `jsonschema`-Validierung — das Script bleibt Zero-Extra-
  Dependency (vendored in Consumer-Repos); dasselbe Präsenz-Check-Prinzip wie
  `registry.py._load_spec` nutzt bereits.

### Security

- **AD-6-Nachtrag (Retro 2026-07-06, Befund 8):** `registry.discover_klickdummies`
  validiert Specs jetzt ebenfalls weich gegen `screens-spec.schema.json` (warnt
  auf stderr, schließt die KD nie aus) — bisher deckte der AD-6-Fix (PR #136)
  nur den genesor-Scan-Pfad, nicht das `klickdummy-browser`-Tool. Bewusst NICHT
  angefasst: `klickdummy_sync.py` (Zero-Dependency-Standalone-Script, vendored
  in Consumer-Repos — Schema-Validierung dort wäre eine Architektur-Entscheidung,
  s. Issue #138).
- **AD-6 (Issue #103, Session-Retro 2026-07-03):** `genesor/scan.py` validiert
  Specs jetzt gegen `screens-spec.schema.json` (geteilter Helfer `validate_spec`,
  nach `read_model.py` verschoben, von `gen_e2e.load_spec` wiederverwendet) —
  vorher nur `yaml.safe_load` ohne jede Prüfung. Bewusst **nicht-fatal**: eine
  nicht-konforme Spec wird nur als `WARN` auf stderr sichtbar, aber nie aus dem
  Fleet-Scan ausgeschlossen (ein harter Abbruch hätte die Cross-Repo-Lineage bei
  der ersten kaputten Spec irgendeines Repos gerissen — dasselbe Risiko wie
  M28-2/#122). Die Sink-Härtung aus PR #125 (`html.escape`/`_safe_seg`) bleibt
  die eigentliche Verteidigungslinie gegen S-02/S-03; dies macht Verstöße
  zusätzlich sichtbar.

## [1.31.1] — 2026-07-05

### Changed

- **Content-Screen-Typ ratifiziert** — `content:`/`off_route` sind nicht mehr
  `EXPERIMENTAL`; Schema-Beschreibungen verweisen auf **platform:ADR-211 Rev 23**
  (KONZ-009, gemergt). Reine Doku-Angleichung, kein Verhaltens-/Schema-Bruch.

## [1.31.0] — 2026-07-05

### Added — KONZ-009: Content-Screen-Typ im Renderer

- **`content:`-Block-Feld am Screen** (`hero`/`prose`/`cta`/`media`/`plan_table`) —
  Screens ohne `datafields` (Landing/Pricing/Onboarding) rendern jetzt echte
  Content-/Marketing-Blöcke statt „Keine Daten-Entities…". Ermöglicht UX-e2e-Journey-KDs
  vom kalten Besucher bis zum Value-Moment. Additiv, opt-in; Feld `experimental` bis
  ADR-211-Amendment. Alle Spec-Strings `html.escape` (S-02/S-03-Härtung).
- **`off_route: bool`** — Vorwärts-Marker für route-lose Content-Screens.
- Renderer: `_render_content_blocks()` am bestehenden Leer-Fallback-Hook; geteilter
  `card`-Wrapper mit dem Datenpfad. Konzept: KONZ-iil-klickdummy-009 (#130), Impl: #132.

## [1.30.1] — 2026-07-03

### Added — KONZ-008 M3: Zwei-Kanal-Input (Struktur-Kanal)

- **`klickdummy-mermaid-readback`** — liest den vom Menschen im GitHub-Web-Editor
  editierten Mermaid-Screen-Flow zurück (`-->` = `next_screens`, `-.zurück.->` =
  `back_screen`, Verkettung `A --> B --> C`) und **difft** gegen die Spec. Read-only:
  schlägt die Delta vor, schreibt nie die Spec (Spec bleibt SoR; kein mmd→spec-Parser).
- **`docs/reference/cookbook-cocreation.md`** — die Zwei-Kanal-Konvention: Mermaid =
  Struktur (GitHub-Roundtrip), Feedback-Widget = Inhalt (GitHub-Issue), Spec = Wahrheit.
  Austausch über GitHub, nicht iil.pet (Cloudflare-Read-back blockiert).

## [1.30.0] — 2026-07-02

Erstes Release seit **1.28.4** — 1.29.0 (F23-Selektor-Kontrakt) wurde nie getaggt/
publiziert; dessen Inhalt ist in diesem Release enthalten (s. [1.29.0] unten). Kern
dieses Release: der **klickdummy-browser-Redesign** (spec-first, ADR-002) und eine
**Security-Serie** (S-01 XSS + gen_e2e-RCE), beide mit dem Prinzip *Spec/Daten sind
eine Vertrauensgrenze*.

### Added — klickdummy-browser Redesign (spec-first, iil-klickdummy:ADR-002)

- Neuaufbau des `klickdummy-browser` strikt gegen eine abgenommene Klickdummy-Spec
  (PR #100 UCs/Mock, PR #101 Renderer). `--pui-*`-Design-Tokens statt Hex (ADR-048/049),
  `addEventListener`/Event-Delegation statt inline `onclick`, `data-testid` an jedem
  interaktiven Element (ADR-040), definierte Fehlerzustände. Verhalten erhalten
  (shell-Laden mit `?feedback=on`, Versions-Switcher read-only, Story-Walk, cross-repo).
- `strict_selectors` als Spec-Attribut zusätzlich zum CLI-Flag `--strict-selectors`
  (REC-1, PR #91). `role=`-Präfix-Parser mit definiertem Fehlerverhalten + Roundtrip-Tests
  (REC-2, PR #92).

### Security

- **S-01 (XSS im klickdummy-browser geschlossen, PR #101):** Daten werden als
  `<script type="application/json">`-Insel + `JSON.parse` eingebettet und via
  `textContent`/`<template>` ins DOM gebaut (nie `innerHTML`-Concat). `registry`
  escaped beim Einbetten jedes `</` zu `<\/` — der HTML-Parser beendet sonst *jedes*
  `<script>` (auch `application/json`) an einem literalen `</script>`.
- **gen_e2e Input-Injection/RCE gehärtet (PR #102):** die Spec ist eine Vertrauensgrenze.
  `load_spec` validiert jetzt fatal gegen `screens-spec.schema.json` (exit 1 bei
  Verstoß), *bevor* ein Wert in generierten Code fließt; zusätzlich Runtime-Escaping
  (`_comment_safe`/`_doc_safe`/`ident`) als zweite, unabhängige Linie. Schloss den
  Vektor „`\n` im `title` bricht aus der Kommentarzeile aus und läuft bei pytest-collect".
- **Folge-Härtungen (PR #104):** `_doc_safe` gegen trailing `"` (Docstring-Bruch);
  `title`-Schema-Pattern lehnt trailing `\n` symmetrisch zu `\r` ab; `login_fixture`
  fail-closed als Python-Bezeichner; `_load_schema` gecacht.

### Fixed

- `is_fragile_selector` `role=`-Validierung + `load_spec` YAML-Fehlerbehandlung
  (KONZ-007/R01/R03, PR #93).
- `generate_uc_skeletons` liest `personas` (Schema-Plural) statt `persona` (war
  stiller No-Op); `discover_klickdummies` nutzt Ein-Ebenen-Glob statt `rglob`
  (verschachtelte Fixture-Specs nicht mehr als KDs) (PR #102).
- README-Git-Fallback-URL auf korrekte Org (`iilgmbh`); `datetime.utcnow()`-Deprecation;
  CHANGELOG-/Doku-Stale-Verweise (PR #99).

### Added — KONZ-008 KD-Co-Creation-Loop (greenfield + brownfield)

Macht das gen_e2e-Manifest zum objektiven Parity-Gate und schließt die Prosa→assert-Lücke
halb-automatisch. Konzept: `docs/konzepte/KONZ-iil-klickdummy-008.md`.

- **`kind`-Feld** (`parity_acceptance.kind ∈ executable | behavioral-manual | nfr-out-of-band`,
  Default `executable`) — klassifiziert, was das Gate fordert; Verhaltens-/NFR-Checks sind
  sichtbar getaggt statt still übersprungen (kein Schein-Grün). (PR #121)
  **Adopter-Migration:** Bestehende Specs ohne `kind`-Feld erhalten den Default
  `executable` — wer `klickdummy-parity-gate` bereits nutzt und Checks hat, die
  tatsächlich nur verhaltensbeschreibend/NFR sind, muss diese Screens einmalig auf
  `kind: behavioral-manual`/`kind: nfr-out-of-band` umstellen, sonst färbt das Gate
  neu rot (Session-Retro 2026-07-03, EF-5).
- **`klickdummy-parity-gate`** — Phase A rot, wenn ein `executable`-Check skipped ist ODER
  `fragile_selectors>0`; `behavioral-manual`/`nfr-out-of-band` ausgenommen. Nutzt das
  vorhandene Manifest, kein neues Wahrheitsfeld. (PR #121)
- **`klickdummy-infer-asserts`** — schlägt für die einfache Check-Klasse (Präsenz/Zähl/Text)
  aus dem testid-Inventar einen `assert`-Kandidaten vor (`--emit-diff`, nie Auto-Commit);
  Verhaltens-Checks werden getaggt statt geraten. (PR #121)
- **Flow-Knoten-Screen-Klasse** — `screens[].items` ist jetzt `anyOf(Assertions-Screen |
  Flow-Knoten weiterführend/terminal)`. Ein Navigations-Graph-Knoten (`next_screens`/
  `back_screen`, ohne `parity_acceptance`) muss keine Assertions-Pflichtfelder tragen.
  **Behebt einen Regressions-Blocker:** die fatale Spec-Validierung hätte sonst bestehende
  Multi-Screen-Flow-KDs abgelehnt. `check_i3` nimmt Flow-Knoten entsprechend aus. (PR #122)
- **`from_django`** parst alle URL-Module (`html_urls.py`, `*_urls.py`, `urls/`-Package)
  statt nur `urls.py` — Brownfield-Capture verfehlt keine Screens mehr (Closes #82, PR #120).

## [1.29.0] — 2026-06-30

### Added — F23 Selektor-Kontrakt: semantischer Fallback + Off-Ramp-Gate (KONZ-007)

Setzt die ratifizierte Hybrid-Entscheidung aus `KONZ-iil-klickdummy-007` um
(platform:ADR-211 F23). `gen_e2e`:
- **`assert.selector` akzeptiert ein Präfix-Vokabular** (D2): `testid=…` →
  `page.get_by_test_id(…)`, `role=…[name=…]` → `page.get_by_role(…)`, `label=…`
  → `page.get_by_label(…)`, `text=…` → `page.get_by_text(…)`. Ohne Präfix bleibt
  der String ein CSS-Selektor (`page.locator`). Kein Schema-Bruch — `selector`
  bleibt ein `string`.
- **`is_fragile_selector`** wertet `testid=`/`role=`/`label=` als stabile Anker;
  `text=` (i18n-fragil) und bare CSS bleiben fragil.
- **`--strict-selectors`** (D1): am Off-Ramp wird ein fragiler Selektor zum
  harten Fehler (exit 3) statt nur zur Manifest-Warnung; Default-Lauf unverändert
  (opt-in, reversibel). Manifest trägt `strict_selectors`.

Locator-Registry/Manifest bleibt zurückgestellt (F18 unverändert).

### Fixed (PR #93, vor Tag v1.29.0)

- **`is_fragile_selector`**: `role=<ungültig>` (kein `_ROLE_PATTERN`-Match) galt via
  `startswith("role=")` fälschlich als stabil, obwohl der Generator auf
  `page.locator()` degradiert — jetzt nur stabil bei echtem Pattern-Match.
- **`load_spec`**: kaputte Spec-YAML → saubere Fehlermeldung + `exit(1)` statt
  rohem `yaml.YAMLError`-Traceback.

## [1.28.4] — 2026-06-18

### Fixed — lineage-Seiten: meiki-hub-Identität leakte in JEDE lineage-<repo>.html

`render_lineage.py`: `HTML_TEMPLATE` hatte `meiki-hub` als Platzhalter an drei
Stellen hartkodiert; nur die H1 (`· meiki-hub`) wurde je Repo ersetzt. Dadurch
trugen **alle** `lineage-<repo>.html` (risk-hub, ttz-hub, pg-hub, …) den falschen
`<title>Klickdummy-Lineage — meiki-hub` und ein Feedback-Widget, das an
`achimdehnert/meiki-hub` statt an das eigene Repo zielte (fehlgeleitetes UAT-Feedback).
- `<title>` (em-dash-Form) und `KLICKDUMMY_FEEDBACK_REPO` werden jetzt ebenfalls
  je Repo ersetzt; Feedback-Ziel = `<org>/<repo>` (`detect_org` analog
  `render_fallback`).

### Changed — genesor KD-Detail: Topologie-Zeile mit Genesor-Deep-Link

`render_genesor.py` (KD-Detail-Karte, Topologie-Zeile):
- Zeile verlinkt jetzt **beide** Ziele: `→ im Genesor öffnen`
  (`index.html#/repo/<slug>`, vom SPA-Router unterstützt) **und** `→ Mermaid-Topologie`
  (`lineage-<slug>.html`) — die Topologie-Seite bleibt aus der Zeile erreichbar.
- 1-KD-Repos (kein eigener Mermaid-Graph) erhalten denselben `→ im Genesor`-Link
  für konsistente Repo-Navigation.

## [1.28.3] — 2026-06-18

### Changed — genesor KD-Detail: Screens klickbar + Mockup-Link nach oben (UAT)

`render_genesor.py` (KD-Detail-Karte):
- **F17:** Screen-Liste ist jetzt **klickbar** — jeder Screen verlinkt per Deep-Link
  `…/index.html#screen-<id>` in den Mockup (Hash-Nav im KD aktiviert den Screen).
- **F15:** Der **„📱 Klickdummy-Mockup öffnen"-Link** steht jetzt **oben** (vor der
  Drift-Validierung) für schnellere Erreichbarkeit; Mockup-URL einmal vorberechnet
  (`find_mockup_html`→`url_for_path`), für Screen-Links und Button geteilt.

## [1.28.2] — 2026-06-17

### Added — UC `related_screens` als klickbare [KD]+[Mockup]-Links (platform:ADR-251)

Im Pro-Repo-UC-Index (`render_uc.py`) werden `related_screens` jetzt als Hyperlinks
gerendert statt als reiner `<code>`-Text:
- **[🕸 KD]** → Screen-Lineage des KDs (immer vorhanden).
- **[🖼 Mockup]** → echter Klickdummy-Einstieg via `find_mockup_html`→`url_for_path`
  (identisch zur genesor-Index-Verlinkung; nur wenn der KD einen Render hat — kein
  toter Link bei Fallback-losen KDs) + `#screen-<sid>`-Deep-Link (springt, wo die
  KD-Render-JS Hash-Navigation unterstützt; sonst lädt der Klickdummy graceful).

Realisiert die ADR-251-Kette UC → KD → Mockup als durchklickbare Verbindung.
Unauflösbare Refs werden weiter mit ⚠ markiert (I1-Coverage).

## [1.28.1] — 2026-06-17

### Fixed — toter `lineage-<repo>.html`-Nav-Link bei 1-KD-Repos

`build_repo_uc_index_html` (`render_uc.py`) verlinkte unbedingt auf
`lineage-<repo>.html`. Diese Datei wird in `generate_per_repo_lineages` aber
**nur bei ≥2 Spec-KDs** generiert (F12). Repos mit genau einem Klickdummy
(z. B. `apo-hub`/apocenna-portale) bekamen so einen 404-Nav-Link auf ihrer
`uc-<repo>.html`-Seite. Der „🌳 Lineage"-Link wird jetzt nur emittiert, wenn das
Repo ≥2 Spec-KDs hat (gleiche Bedingung wie der Generator).

## [1.28.0] — 2026-06-14

### Refactored — Read-Model-Schema zentralisiert (KONZ-003 Empf-3 S1, #70)

Neues Modul `read_model.py` definiert die Feldverträge der zwei Read-Model-Flächen
(`uc-export.json` via `genesor/export.py`, Discovery-NDJSON via `discovery_push.py`)
als TypedDicts und zentralisiert die Schema-Versionskonstanten:

- `UC_EXPORT_SCHEMA_VERSION` (bisher Literal `"1.0"` in `export.py`)
- `REGISTRY_SCHEMA_VERSION`, `API_VERSION`, `EMBEDDING_INPUT_SCHEMA` (bisher
  inline-Kommentar-Konstanten in `discovery_push.py`)

Kein Verhaltensunterschied — ausschließlich Schema-Stabilisierung (S2/S3 trigger-gegatet
per KONZ-003 §13).

### Added — klickdummy_sync.py: kanonische Quelle in snippets/genesor-sync/ (Issue #66)

`src/iil_klickdummy/snippets/genesor-sync/klickdummy_sync.py` ist jetzt die kanonische
Quelle des Sync-Scripts (Counter-A, ADR-211 Rev 13 §Distribution). Bisher existierte es
nur als Kopie in Konsumenten-Repos ohne Single-Source-of-Truth. Kopien in Konsumenten-Repos
nicht direkt editieren — Änderungen hier vornehmen, dann verteilen.

## [1.27.0] — 2026-06-13

### Fixed — gen_e2e: Auth-Brücke + Strict-Mode (erstmals gegen echten Renderer #2 gefahren)

Beim ersten echten Renderer-#2-Lauf der Parity-Suite (risk-hub `sds-verwalten`
gegen die live `/sds/review/`-App, platform:ADR-211 S13) traten zwei Bugs zutage,
die zuvor nur überlebten, weil die Suite **nie** gegen eine echte, login-gated
App lief (Unit-Tests prüften bloß Text-Marker — Memory `smoke-test-marker-presence-gap`):

- **`auth.storage_state` emittierte eine nicht-existierende Playwright-API.**
  Der generierte autouse-`_auth`-Fixture rief `page.context.set_storage_state(path=…)`
  auf → `TypeError` gegen jeden `login_required`-Renderer-#2. Jetzt korrekt: das
  pytest-playwright-Fixture `browser_context_args` überschreiben, sodass der
  `page`-Context vor-authentifiziert startet (einzige API, die State lädt).
- **`visible`/`text`/`clickable` brachen an Playwrights Strict-Mode**, sobald ein
  Kontrakt-Selektor legitim mehrfach matchte (z.B. `data-testid` pro Tabellenzeile:
  „resolved to N elements"). Einzelelement-State-Asserts nutzen jetzt `.first`
  (Existenz-/State-Prüfung ≠ Eindeutigkeit); `count` bleibt kardinalitäts-exakt.

Beweis: dieselbe generierte Suite läuft grün gegen die echte App und wird rot,
sobald ein App-`data-testid` vom Spec-Kontrakt abweicht — die Wertthese des
Dual-Renderer-Parity-Gates ist damit erstmals empirisch eingelöst.

### Fixed — UC-Issue-Form-Prefill war verloren gegangen

- `_gh_issue_url` (kind=use-case) berechnete `anker`/`daten`, hängte sie aber
  nie an die Form-URL — die Felder `anker`/`daten`/`persona` des
  `uc-klickdummy.yml`-Forms (Label: „aus Spec vorbefüllt") blieben leer.
  Jetzt als Query-Params prefillt. Gefunden über ruff F841 (unused variable);
  der bestehende Smoke-Test prüfte nur Marker-Präsenz (Memory
  `smoke-test-marker-presence-gap`) — jetzt Param-Name + Wert.

### Changed — Lint-Null-Linie

- ruff 29 → 0: F541/F401/E401 auto-fixt; 3 echte tote Variablen entfernt
  (`title` in render_lineage, `threshold` in manage, `when` in
  sync_to_orchestrator — je verifiziert, dass kein Verhalten dranhängt).
  Golden-HTML-Diff doppelt (Default + `--base-url /kdtest/`): 20/87 Dateien
  geändert, alle Änderungen vollständig durch die neuen Prefill-Params erklärt.

## [1.26.0] — 2026-06-12

### Added — Org-Mapping + App-Namen aus platform-Registry-SSoT (PR #63)

- `detect_org` und `app_name_map` lesen jetzt `platform/registry/canonical.yaml`
  (`meta.repo_owner` / `owner_prefix_rules` / `app_display_names`, platform#554)
  statt hartkodierter Heuristik. Die Code-Heuristik bleibt als Fallback für
  Installationen ohne platform-Checkout (PyPI).
- Vollständigkeits-Gate: Registry gilt nur mit `owner_prefix_rules` als
  nutzbar — platform-Stände mit bloßem `repo_owner` (vor platform#554) fallen
  sauber auf die Heuristik zurück statt meiki-/ttz-Repos falsch zu mappen.
- Netz: golden-HTML-Diff doppelt × beide Pfade (Fallback ohne Felder /
  Registry nach platform#554-Merge) — byte-identisch bis `generated_at`.
  8 neue Tests in `test_org_registry.py` (139 gesamt).

## [1.25.0] — 2026-06-12

### Changed — KONZ-003 Empf-1 komplett: lineage.py-Monolith zerlegt (PR #59/#60/#61)

Reiner Struktur-Refactor, **keine funktionale Änderung** — Output via
golden-HTML-Diff byte-identisch verifiziert (je doppelt: Default-Argumente
und `--repos-root`+`--base-url`-Nicht-Default).

- **PR #59 (Empf-1b/1):** 54 Funktionen + 9 Konstanten aus `lineage.py` in
  6 Module: `genesor/{scan,synth,mermaid,validate,publish,ucs}.py`.
  Inkl. Hotfix: `ROOT`-Pfadtiefe + `_cfg`-Importbindung (`set_cfg` rebindet
  → Module nutzen `get_cfg()`).
- **PR #60 (Empf-1b/2):** 19 Render-Definitionen in 5 Module:
  `genesor/render_{common,fallback,lineage,genesor,uc}.py` —
  `lineage.py` ist jetzt dünne CLI (6432 → 590 Zeilen).
- **PR #61 (Empf-1c):** `build_genesor_html` (1356 Z.) → 203-Z.-Orchestrator
  + 6 Sub-Renderer (`_render_kd_detail`, `_render_table_body`,
  `_render_acceptance_matrix`, `_render_skin_options`, `_org_chip`,
  `_role_chip`); literale Template-Teile als Konstanten
  `_GENESOR_HEAD`/`_GENESOR_TAIL`.
- Back-compat: alle bisherigen `from iil_klickdummy.lineage import X`
  funktionieren weiter (Re-Export-Block).

> Hinweis: v1.24.0 wurde nie getaggt/publiziert — die dortigen Fixes sind
> in diesem Release enthalten (erstes PyPI-Release nach 1.23.0).

## [1.24.0] — 2026-06-12

### Fixed — Analyse-Reste (Follow-up zur Codebase-Analyse, PR #57)

- **I2:** widersprüchliche Doppel-Deklaration (`class` ≠ `klickdummy_class`) ist
  jetzt FAIL statt stillem First-Key-Wins („genau EIN Pattern", ADR-211 I2).
- **inventory:** `--strict` bricht nicht mehr nach dem ersten Repo ab (Voll-Scan,
  Exit-Code am Ende); >10 Treffer zeigen „… und N weitere"; ohne `--strict` jetzt
  Report mit Exit 0 (Gate-Verhalten nur mit Flag — vorher war es für den
  Exit-Code wirkungslos).
- **discovery_push:** `off_ramp_status` aggregiert per-Screen-Status, wenn
  `status_overall` fehlt (uniform → Wert, gemischt → `transition`); vorher
  pauschal `static` — KDs mit removed-Screens erschienen im pgvector-Index als
  unangetastet.
- **lineage.py:** un-escapte `\s`-Sequenzen im Template-JS gedoppelt —
  SyntaxWarning beim Import beseitigt; emittiertes JS byte-identisch.

### Added — Widget-UX-Paket + Cross-Repo-Stories

- **widget.js:** GitHub-Submit-Fehler fragt per `confirm()` nach, statt still
  Download auszulösen; leere Textarea bekommt sichtbares Invalid-Feedback
  (`fb-invalid` + `aria-invalid` + Fokus, Reset bei Eingabe); FAB mit
  `aria-expanded`/`aria-controls`, Panel als `role=dialog`; Token-Validierung
  prüft Mindestlänge statt nur Präfix. Playwright-live verifiziert.
- **Browser:** Cross-Repo-Modus übergibt jetzt Stories
  (`discover_cross_repo_stories()` mit globalem `kd_index`-Remap) — vorher kam
  der Story-Walk dort nie an.
- 11 neue Tests (`tests/test_analyse_reste.py`); Suite 131 grün.

**Bewusst offen:** lineage-Modul-Split (KONZ-003, eigener Strang) und
orgs.yaml-Externalisierung von `detect_org`/`app_name_map` (platform-Entscheid).

## [1.23.0] — 2026-06-12

### Fixed — Gate-Integrität I3/I4 + UX-Sicherheit (Codebase-Analyse Items 1–2)

- **I3 False-Pass:** `check_i3` defaultete fehlendes `off_ramp_status` still auf
  `static` — ein Screen ohne das Schema-Pflichtfeld passierte das Gate. Jetzt FAIL
  je Screen.
- **I4 CWD-Abhängigkeit:** Die lokale ADR-Whitelist (`docs/adr/`) war CWD-relativ;
  Aufruf außerhalb des Repo-Roots ergab False-Fail/False-Pass. Jetzt via
  `find_adr_dir()` vom Scan-Root abgeleitet (`<root>/docs/adr`, `<root>/adr`,
  Eltern-Verzeichnisse).
- 15 neue Tests nageln die Pass/Fail-Semantik von I1/I3/I4 fest (vorher nur
  Import-Smoke).
- `<meta name="viewport">` in allen 8 generierten HTML-Heads (Output war mobil
  unbenutzbar); HTML-Escaping (`_esc`) für Spec-Werte im Akte-Modal-`innerHTML`;
  `URL.revokeObjectURL` nach Widget-Download.

### Added — extract-requirements `--dry-run` + Browser-Versions-Switcher (Items 3–4)

- `klickdummy-extract-requirements --dry-run`: zeigt alle Schreib-/Löschaktionen
  ohne auszuführen. Stale UC-Dateien werden nur noch mit sichtbarer ⚠-Warnliste
  gelöscht (vorher stilles `unlink` — handeditierte UCs verschwanden kommentarlos)
  und nur, wenn sie nicht mehr zum Screen-Set gehören.
- **Versions-Switcher funktionsfähig:** `#ver-select` im Browser war eine
  UI-Attrappe ohne Handler; `discover_versions()` wurde nie aufgerufen. Jetzt:
  `render_browser_html(repo_root=...)` bettet die Git-Historie je KD ein,
  `collect_versions_with_snapshots()` extrahiert frühere `shell.html`-Stände per
  `git show` nach `klickdummy-versions/<kd>/<version>/`; historische Versionen
  laden read-only (ohne `?feedback=on`), Detail-Card zeigt Version/Datum/SHA.

### Changed — A11y + Responsive im Render-Fallback (Item 5)

- Tabs/Sub-Tabs mit `role=tablist/tab/tabpanel` + `aria-selected`-Sync; Sidebar
  mit `aria-current`; Modal als `role=dialog` mit Fokus-Management (Fokus auf
  Schließen-Button, Rückgabe beim Schließen, leichter Tab-Trap); Spec-Toggle mit
  `aria-pressed`.
- Pfeiltasten-Navigation (←/→ Tabs, ↑/↓ Sidebar; persona-gefilterte Buttons
  übersprungen) + `:focus-visible`-Outline; Scroll-Reset bei Screen-Wechsel.
- `@media (max-width: 768px)`: Sidebar-Grid stapelt, kompaktere Paddings,
  Feedback-Widget passt sich der Viewport-Breite an.
- Live verifiziert per Playwright (ARIA-Sync, Pfeiltasten, Modal-Focus/Escape,
  Versions-Switcher-Roundtrip); 120 Tests grün.

## [1.22.2] — 2026-06-04

### Changed — Ehrlicher Header: Drift-Check ≠ Parität

- Der generierte Suite-Header stellt jetzt explizit klar, dass `make klickdummy-parity-drift`
  **nur Spec↔Datei-Drift** prüft (re-gen + diff) und die Assertions **nicht ausführt** — also
  **keine Parität belegt**. Echte Parität entsteht erst beim Lauf mit pytest + playwright gegen
  einen laufenden `SPEC_RENDERER_BASE_URL`; „gegen Renderer #2" setzt eine echte, erreichbare
  App-Route voraus.
- Hintergrund (empirisch, 2026-06-04): plattformweit lief noch nie eine Suite gegen einen
  Renderer #2 — alle Specs sind `mock`/`spec-demo`, kein Repo in Off-Ramp-Transition. Der
  irreführende Name `parity-drift` signalisierte „Parität geprüft", wo nur Drift geprüft wurde.
- Generierter Output bleibt deterministisch; Adopter sehen beim nächsten `parity-drift`-Lauf
  einmalig Drift → re-generieren.

## [1.22.1] — 2026-06-04

### Fixed — `gen_e2e` emittiert `pytest.importorskip("playwright")` (T-01)

- Die generierte Parity-Suite importierte `playwright` hart auf Modulebene. Bei
  Adoptern **ohne** `testpaths`-Isolation sammelt pytest die Suite mit und bricht
  beim Import, wenn `playwright` nicht installiert ist (Collection-Error statt Skip).
  Der erste Adopter (`risk-hub` #146) entging dem nur per `testpaths=["src"]`-Zufall.
- Fix: Der Generator setzt nun `pytest.importorskip("playwright")` **vor** den
  `from playwright.sync_api import …` (mit `# noqa: E402`, damit `ruff check` der
  Adopter grün bleibt). Suiten ohne installiertes playwright werden sauber
  übersprungen statt zu brechen. Output bleibt `ruff format`- und `ruff check`-clean.
- Regressionstests: Präsenz + Reihenfolge der `importorskip`-Zeile,
  `ruff check --select E402` auf dem generierten Output.

## [1.22.0] — 2026-06-03

### Added — Autoren-Beispielzeilen für Entity-Tabellen (`local_entities.<e>.examples`)

- Sub-Tab-Tabellen (`konsumiert_entities` → `local_entities`) konnten bisher nur
  **synthetische, domänen-blinde** Werte zeigen (`_synth_value`-Heuristik per
  Feldname → z.B. CAS/WGK/Lagerklasse wurden zu „Wert-A"). Für „am Beispiel
  schärfen" (ADR-211 Co-Creation) fehlten domänen-echte Werte.
- Neu: `local_entities.<entity>.examples: [[v1, v2, …], …]` — Liste von Zeilen,
  an `fields`-Reihenfolge ausgerichtet. Hat **Vorrang** vor der Synth-Heuristik;
  zu kurze Zeilen werden per Synth aufgefüllt, zu lange auf 6 Spalten gekappt.
  Ohne `examples` bleibt das bisherige Synth-Verhalten unverändert (abwärtskompatibel).
- Schema: bereits valide über `additionalProperties: true` am Top-Level — keine
  Schema-Änderung nötig. Erstnutzung: `risk-hub:gefahrstoff-kataster` (UC-004).

## [1.21.2] — 2026-06-03

### Changed — Story-Switcher zeigt Schritt-Label statt Story-Titel

- Bei KDs, die mehrere Story-Schritte teilen, zeigte der Switcher (`#sb-story-switch`)
  den Story-Titel **mehrfach** (redundant). Jetzt `en.step_label` (z.B.
  „5. Template/Gliederung erstellen") → die Schritte sind unterscheidbar.

## [1.21.1] — 2026-06-02

### Fixed — stories-manifest: korrekte relative Tiefe + Shell-Präfix

- v1.21.0 legte das Manifest nach `out_dir` mit Shells `<kd>/index.html` —
  aber `../../` aus `kd/<repo>/klickdummy/<kd>/index.html` zeigt auf
  **`kd/<repo>/`** (zwei Ebenen hoch), nicht `kd/<repo>/klickdummy/`. Folge:
  Banner-Fetch 404 → Story-Walk lud nicht (live verifiziert).
- `build_manifest(repo_root, shell_prefix="")` + 3. CLI-Arg `[shell_prefix]`:
  Manifest gehört nach `kd/<repo>/`, prev/next_shell = `klickdummy/<kd>/index.html`.
  Regen ruft mit `out_dir=kd/<repo>` + `shell_prefix=klickdummy/`.

## [1.21.0] — 2026-06-02

### Added — Stories-Manifest für den Genesor/Vendored-Layout (`klickdummy-stories-manifest`)

- **Lücke geschlossen:** der Genesor-Renderer erzeugt das Story-Banner-JS (fetcht
  `../../stories-manifest.json`), schrieb das Manifest aber **nie** —
  `write_stories_manifest` lag nur im `klickdummy-browser`-Render (registry.py,
  Browser-Layout). Folge: Story-Walk/Banner erschien auf iil.pet (Genesor-Deploy)
  **nicht**, egal wie oft regen lief.
- **`gen_stories_manifest.py` + Console-Script `klickdummy-stories-manifest`**:
  `<repo_root> <out_dir>` → schreibt `stories-manifest.json` mit `kd_to_stories`
  für den **Vendored-Layout** (`kd/<repo>/klickdummy/<kd>/index.html` → `../../` =
  `kd/<repo>/klickdummy/`); prev/next_shell = `<kd>/index.html` (statt `shell_path`).
  Wird vom iil-pet-portal-Regen je Story-Repo aufgerufen.
- 2 Tests. Dogfood ausschreibungs-hub: Bieter-Journey, 5 KDs, 11 Steps.

## [1.20.0] — 2026-06-02

### Added — Flow-Kohärenz-Lint `klickdummy-flow` (UC-Story-Line, KONZ-004 Move 2)

- **`check_flow.py` + Console-Script `klickdummy-flow`**: validiert den
  Screen-Flow-DAG (`screens[].next_screens` / `voraussetzung_screen`) je
  KD-Spec — heute vom Genesor als Lineage-Graph gerendert, aber **unvalidiert**
  (nicht im Schema). Findings:
  - **error**: dangling `next_screens`/`voraussetzung_screen` (Ziel kein Screen
    der Spec) → Exit≠0.
  - **warning**: Vorwärts/Rückwärts-Asymmetrie (next ↔ voraussetzung uneinig),
    Zyklus, **Flow-Schritt ohne `use_cases`** (Stringenz-Lücke der UC-Story-Line).
  - **info**: isolierter Screen, „kein Flow deklariert" (≥2 Screens, 0 Kanten).
- Dogfood ausschreibungs-hub: fand reale Asymmetrie (`lose_auswahl` ↔
  `ausschreibung_detail`) + 14 Flow-Schritte ohne `use_cases`. 5 neue Tests.
- Macht die UC-Story-Line **erzwingbar** (Consumer-CI ruft `klickdummy-flow`),
  ohne neues SoR-Artefakt — Flow bleibt in der Spec. Hintergrund: KONZ-004.

## [1.19.1] — 2026-06-02

### Fixed — Spec-Sicht-Heading spiegelt aktiven Sub-Tab (Feedback-Widget-Bug)

- Sub-Tab-Wechsel aktualisierte `fb-current-subtab` (für Feedback/UC-anlegen),
  aber **nicht** die sichtbare Spec-Sicht-Überschrift (`tr-screen-title`) — die
  blieb screen-statisch (z.B. „nachunternehmer — Nachunternehmer-Auswahl…").
  Jetzt hängt der Sub-Tab-Handler ` › <aktiver-subtab>` an die Heading des
  jeweiligen Screen-`.trace-strip` (nur bei ≥2 Sub-Tabs); Initial-Befüllung je
  Screen. Renderer-weit. Bug-Report via Feedback-Widget 2026-06-02
  (bau-beschaffung/nachunternehmer).

## [1.19.0] — 2026-06-02

### Added — Story-Validierung (Fail-Fast) statt render-zeitigem Silent-Skip (KONZ-004 A3)

- **`schemas/story.schema.json`** (neu): JSON-Schema für `klickdummy/stories/<slug>.yaml`
  (`id`-Pattern `repo:story-<slug>`, `title`+`steps` required, `steps[].kd` required,
  `additionalProperties:false`).
- **`check_stories.py` + Console-Script `klickdummy-stories`**: scannt
  `klickdummy/stories/*.yaml`, validiert gegen das Schema **und** löst `step.kd`
  gegen die KD-Liste auf. Sammelt **alle** Fehler, Exit≠0 — macht den bisherigen
  render-zeitigen stderr-Silent-Skip (`discover_stories`) zu einem harten Build-Gate.
  Kein `stories/`-Verzeichnis → PASS (rückwärtskompatibel).
- Hintergrund + Abwägung (UI-Tool abgelehnt): `docs/konzepte/KONZ-iil-klickdummy-004.md`.

### Fixed — Spec-Sicht: Panel beim Aktivieren in den Viewport scrollen

- `setSpecView(on)` scrollt jetzt beim Einschalten das sichtbare `.trace-strip`
  (Spec-Panel des aktiven Screens) per `scrollIntoView` in den Viewport. Vorher
  togglete es nur `body.spec-view` — das Panel sitzt am Screen-Ende, oft unter
  dem Fold (verifiziert: phase-unterlagen Panel-Top 730 bei Viewport 720,
  `scrollY` blieb 0) → Nutzer sah nach „Spec-Sicht"-Klick scheinbar keine
  Änderung. Renderer-weit (UX-Test-Befund 2026-06-02).

## [1.18.2] — 2026-06-02

### Fixed — Zwei UX-Bugs im KD-Render (Playwright-UX-Test)

- **Persona-Filter war funktionslos (P1):** `applyPersonaFilter()` schrieb auf
  `#fb-current-persona`, dieses Element wurde aber **nie gerendert** → `TypeError`
  in der ersten Zeile → der Tab-Filter-Code dahinter lief nie (Persona-Auswahl
  ohne jede Wirkung; auch der Feedback-Submit las dieselbe tote ID). Fix: hidden
  `#fb-current-persona`-Tracker ergänzt (analog `#fb-current-subtab`) + beide
  Zugriffe null-geguarded. Verifiziert: Persona „bieter" blendet jetzt korrekt
  die nicht-passenden Screens aus.
- **Story-Banner immer sichtbar & leer (P2):** der Inline-Style von
  `#story-banner` enthielt **zwei** `display:`-Deklarationen
  (`display:none;…;display:flex`) → `flex` gewann → leerer „📖 Schritt /"-Balken
  auf jedem Render ohne aktive Story (inkl. live). Fix: verirrtes `display:flex`
  aus dem Inline-Style entfernt; JS schaltet bei aktiver Story auf flex.
- Beide im `RENDER_FALLBACK_TEMPLATE` → galt für **alle** KD-Renders aller Repos.
  2 neue Regressionstests (74 grün); browser-verifiziert (Playwright).

## [1.18.1] — 2026-06-02

### Fixed — Story-Banner-JS leakte als sichtbarer Text im KD-Render

- `RENDER_FALLBACK_TEMPLATE` enthielt `__STORY_BANNER_JS_PLACEHOLDER__`
  **zweimal**: einmal korrekt in `<script id="story-banner-js">` (Body-Ende),
  einmal **roh** direkt nach dem Banner-Div (ohne `<script>`-Wrapper). Da
  `str.replace` alle Vorkommen ersetzt, wurde das JS oben im Body als
  sichtbarer Quelltext gerendert (Bug-Report 2026-06-02). Der nackte
  Platzhalter wurde entfernt — Banner-Div bleibt oben, Script am Body-Ende.
- Regressionstest verschärft: prüft jetzt, dass das Banner-JS genau **einmal**
  und ausschließlich **innerhalb** eines `<script>`-Tags vorkommt (Marker-
  Präsenz allein hätte den Leak nicht gefangen).

## [1.18.0] — 2026-06-02

### Added — Repo-Linse im Genesor einklappbar (mehr Platz für den Inhalt)

- Die Repo-Rail („Linse") im Genesor-Overview lässt sich per ◀-Button
  einklappen — der sichtbare Inhaltsbereich (`main`) wird dadurch voll breit,
  abgeschnittene Tabellenspalten (Replaces, Sunset, Personas) werden sichtbar.
  Eingeklappt erscheint ein `▶ Linse`-Button oben im Inhalt zum Ausklappen.
- Zustand persistiert in `localStorage` (`genesor_rail_collapsed`) — gleiches
  Muster wie der Skin-Switcher. Default: ausgeklappt (Verhalten wie bisher).
- Reine Template-Erweiterung in `lineage.py` (CSS + 2 Buttons + Toggle-IIFE),
  3.10-safe (alle Klammern verdoppelt, kein PEP-701). 72 Tests grün, keine
  neuen ruff-Befunde.

## [1.17.1] — 2026-06-02

### Fixed — Screen-Titel im Topbar dynamisch (Bug #40)

- `showScreen()` setzt jetzt `#screen-title-dynamic`-Span in der H1 auf den
  Namen des aktiven Screens (aus dem Tab-Button). Vorher war die H1 statisch
  (immer KD-Titel) → User sah keinen Hinweis welcher Screen aktiv ist.
  Kleines `font-weight:400`-Inline-Label neben dem KD-Titel; verschwindet
  beim ersten Screen ohne Namens-Match (silent, kein Fehler).

## [1.17.0] — 2026-06-02

### Added — Story-Banner im Render: KD kennt seine Story-Zugehörigkeit (approach b)

- **`write_stories_manifest(output_dir, kds, stories)`** in `registry.py`: erzeugt
  `stories-manifest.json` neben Browser-HTML. Enthält `kd_to_stories`-Map mit
  `step_index`, `step_total`, `prev/next_shell` (repo-root-relativ), Labels.
  `render_browser_html` schreibt Manifest automatisch wenn Stories vorhanden.
- **Story-Banner im Render** (`RENDER_FALLBACK_TEMPLATE` in `lineage.py`): jeder
  generierte KD-Render enthält einen hidden `#story-banner`-Div + Banner-JS.
  Das JS lädt `../../stories-manifest.json` via fetch — bei Erfolg blendet sich
  der Banner ein mit Story-Titel, Schritt-Zähler, ●-Dots, Weiter/Zurück-Links.
  Multi-Story-KD: Story-Switcher rechts im Banner. Silent fail bei `file://`
  oder fehlendem Manifest → Banner bleibt versteckt, kein Fehler.
- `data-kd="{kd_name}"` auf dem Banner-JS-Script-Tag — KD-Name für Manifest-Lookup.
- 2 neue Smoke-Tests; 43 grün; 3.10-safe.

## [1.16.0] — 2026-06-02

### Added — Story-Picker: geführte KD-Touren im Browser (platform:ADR-211 §Story-Navigation)

- **`discover_stories(repo_root, klickdummies)`** in `registry.py`: scannt
  `klickdummy/stories/*.yaml`, löst `step.kd` (Verzeichnisname) gegen die
  KD-Liste auf, gibt Story-Dicts mit `kd_index` zurück. Unbekannte Steps →
  stderr-Warning, kein Abbruch. Kein `stories/`-Verzeichnis → `[]` (rückwärtskompatibel).
- **`render_browser_html` / `render_cross_repo_browser_html`**: neuer optionaler
  `stories`-Parameter; setzt `__STORIES_JSON__`-Placeholder im Template.
- **`browser.html.tmpl` v1.2**: Mode-Toggle `🗂 Frei | 📖 Story-Walk` (nur sichtbar
  wenn ≥1 Story vorhanden), Story-Select-Dropdown, Stepper-Liste mit ✅/●/○-Icons,
  Weiter/Zurück-Buttons, Visited-State via localStorage — rückwärtskompatibel
  (ohne Stories: Toggle versteckt, Verhalten wie v1.1).
- **`snippets/spec-templates/story.yaml.example`**: Vorlage für Consumer-Repos.
- 4 neue Smoke-Tests; 41 grün; 3.10-safe.

## [1.15.1] — 2026-06-01

### Fixed — Sub-Tab-aware UC anlegen + Feedback-Widget (#34)

- **`build_trace_strip` `act()`:** UC-anlegen-Button trägt jetzt `data-uc-subtab-selector`
  → Page-Level-Script liest beim Click den aktiven Sub-Tab-Namen und hängt ihn an den
  localStorage-Key (sub-tab-spezifischer Inflight-State) und den Issue-Titel.
- **Sub-Tab-Switch-Handler:** setzt `fb-current-subtab`-Element (+ Initial-Sync bei Seitenlade).
- **`fbCollect()`** (beide Instanzen — Render-Template + lineage.py-Self-Render):
  `active_subtab: document.getElementById('fb-current-subtab')?.textContent || null`
  im Feedback-Payload.
- **`fb-current-subtab`:** hidden Span nach Widget-Placeholder-Inject im Template + lineage.py.
- 2 neue Smoke-Tests; 37 grün; 3.10-safe.

## [1.15.0] — 2026-06-01

### Added — gen_e2e: parametrisierte Routen + Auth für ausführbare Parity-Suite (#28)

- **`route_example`** (Screen-Feld): konkrete Beispiel-URL mit echten IDs/UUIDs. `klickdummy-gen-e2e` bevorzugt sie vor `route` → kein `<uuid:pk>`-404 mehr gegen Renderer #2 (echte App).
- **Parametrisierte `route` ohne `route_example`** → Check wird `@pytest.mark.skip` mit klarem Grund (statt 404-Rauschen); Manifest weist es als `skip_reason: parametrised_route` aus.
- **`auth`-Block** (Top-Level): `storage_state` / `login_fixture` / `required`. gen_e2e bindet ihn als `autouse`-Fixture ein. `login_required`-Screen ohne `auth` → skip mit Grund `login_required_no_auth`.
- `screen_route()` gibt jetzt `(url, is_parametrised)` zurück. Schema um `route_example`, `login_required`, `auth` erweitert (alle optional, rückwärtskompatibel). 4 neue Tests; 64 grün, 3.10-safe.

## [1.14.0] — 2026-06-01

### Added — Klickdummy-Capture-Gate: strukturiertes Issue-Form statt thin-prefill

- **`_gh_issue_url` kind-Routing (2b, platform:ADR-211 §Co-Creation-Loop):**
  `kind=use-case` routet auf `?template=uc-klickdummy.yml` (GitHub Issue Form mit
  `required`-Feldern — GitHub blockiert leeres Submit) statt thin-prefill. `kind=off-ramp`
  und `kind=parity` behalten den bisherigen Markdown-body-Prefill bis eigene Forms gebaut sind.
- **`snippets/issue-template/uc-klickdummy.yml`** — GitHub Issue Form (YAML): 5 Pflicht-
  felder (Anker, Persona, Ziel, Hauptszenario, Akzeptanz), spec-vorbefüllter Titel (`UC: kd/screen`),
  Labels `uc-draft`+`needs-domain-review`. Labels Route Issue direkt in den Co-Creation-Loop.
- **`snippets/issue-template/klickdummy-feedback.yml`** — ersetzt `.md`: GitHub Issue Form
  mit `Art`-Dropdown (Bug/Feature/Fehlende View/Spec-Korrektur) als Quell-Router; Pflicht-
  felder Art + Anker + Beschreibung.
- **`.github/ISSUE_TEMPLATE/uc-klickdummy.yml`** — repo-eigenes Template (Dogfood).
- Test `test_v17_trace_strip_uc_create_button` auf neues URL-Format aktualisiert.

## [1.13.4] — 2026-06-01

### Added
- Spec-Sicht: Screen-ID + Titel am Kopf jedes Panels (zeigt welcher Tab/Screen aktiv ist).
- Favicon 🌱 in Render- und Genesor-Seiten (behebt 404 für favicon.ico).

## [1.13.3] — 2026-06-01

### Fixed
- Inflight-Reset via Event-Delegation: `querySelector` nach `outerHTML` fand Spans in versteckten `has-tabs`-Sections nicht. Fix: `document.addEventListener('click')` + `closest()` fängt alle Inflight-Klicks zuverlässig ab.

## [1.13.2] — 2026-06-01

### Fixed
- Inflight-Span zurücksetzbar: Klick auf „⏳ UC anlegen in Arbeit" löscht localStorage-Key + Reload → Button wiederhergestellt.
- UC-Liste als `<details>/<summary>` klappbar (statt Freitext).

## [1.13.1] — 2026-06-01

### Fixed
- `spec-sicht`: UC-Button-Inflight-State Hotfix — erster Ansatz (#26) war durch doppelte HTML-Escaping-Stufen kaputt. Neuer Ansatz: `data-uc-key` auf dem Link + sauberes Page-Level-Script (kein `document.currentScript`, kein Inline-JS, echte Emoji-Zeichen).

## [1.13.0] — 2026-06-01

### Fixed
- `spec-sicht`: UC-Button-Zustand „⏳ UC anlegen in Arbeit" nach Klick — State via `localStorage` persistent nach Reload (#26).

### Refactored
- `lineage.py` Globals → `@dataclass GenesorConfig` (PR #23) + Teil-Split in `iil_klickdummy/genesor/` (config, introspect_django, export — PR #24). Vorbereitung für den Render-Kern-Split (#22).

## [1.12.0] — 2026-06-01

### Added — Genesor Repo-Ebenen-Einstieg (Master-Detail + Fassetten-Linse)

- `build_genesor_html` erhält eine **client-seitige Master-Detail-Schiene** in der
  bestehenden `index.html` (KONZ-iil-klickdummy-002): linke Repo-Schiene (alle Repos
  sichtbar, mit KD-Count + Drift-Punkt) + Hash-Routing `#/repo/<repo>` für teilbare
  Deep-Links. Adressiert den Übersichtlichkeits-Verlust bei wachsender KD-Zahl
  (49 KDs / 10 Repos, Long-Tail), ohne eine zweite Datei oder Server-Routing.
- **Fassetten-Linse** (Out-of-the-Box): Schiene umschaltbar nach `repo | org | class
  | role` — Repo ist nur die Default-Linse, nicht die einzige Achse. Schiene wird
  client-seitig aus den Zeilen-`data`-Attributen gebaut (kein N×-Server-Render).
- **Rein additiv & rückwärtskompatibel:** ohne Hash zeigt die Seite unverändert alle
  Zeilen; die neue Gruppen-Dimension UND-verknüpft mit den bestehenden Org-/Drift-/
  Such-Filtern. `render_detail`, Surface-Modal, Sort, Skin-Switcher unberührt.
- Verifiziert per Playwright (Master-Detail-Verengung exakt, Deep-Link beim Frisch-Load,
  Fassetten-Wechsel, Koexistenz, 0 Konsolen-Fehler) + 60 Tests grün.

## [1.11.0] — 2026-06-01

### Added — `klickdummy-from-django`: Brownfield-Reverse-Onboarding

- Neues Modul/CLI `from_django` (`klickdummy-from-django`): leitet aus einer
  **existierenden Django-App** ein `screens-spec.yaml`-**Skelett** ab — URLConf →
  Screens (Pages) + Aktionen (POST-Endpoints getrennt), `models.py` → Entity-
  Katalog mit Feldtypen, `app_name` → `spec_id`. **Statisches Parsing** (`ast` +
  Regex), **keine** Django-Runtime/DB nötig → läuft sicher gegen jeden Source-Tree.
- `class: spec-demo` (realer Code-Pfad existiert) + Kuratier-Kommentare
  (Entity-Katalog, Aktions-Liste, TODO-Marker). Startpunkt für menschliche
  Kuratierung; nächster Schritt `klickdummy-gen-e2e` gegen die echte App
  (Parity-Bridge) → iterieren bis parity-grün = verifizierte Spec-Erfassung.
- Macht Brownfield-Onboarding reproduzierbar (Blaupause „Schritt für Schritt
  alle Repos"). 2 neue Tests; gegen `writing-hub/outlines` gedogfoodt
  (4 Screens, 7 Aktionen, 2 Models).

## [1.10.0] — 2026-06-01

### Changed — Render: Spec-Sicht als Inhalts-Panel + kanonisches Widget

- **Spec-Sicht (X-Ray)** von dünner Chip-Reihe → **gelabeltes Inhalts-Panel** pro
  Screen: echte Werte statt Icon-Chips — Use-Case-Namen, Entitäten + Datenfelder
  (mit Typ), Status (class/role/off-ramp/pipeline), Abnahme (who/when/Frische),
  Coverage-Aufschlüsselung (executable/prose-only/fragil), Validierungsfrage-Text.
- **Co-Creation-Buttons:** fehlende Pflicht-Angaben (UC, off_ramp_status,
  parity_acceptance) bekommen einen `[+ anlegen]`-Button → vorausgefülltes
  GitHub-Issue (`detect_org`-Ziel, kein Hardcode). Schließt die „nicht
  deklariert"-Lücke aktionierbar (ADR-211 Co-Creation).
- **Feedback-Widget:** Render bettet jetzt das **kanonische `widget.js`**
  (GitHub-direct + PAT-Modal) ein statt des alten inline-Download/Clipboard-
  Widgets — via `__FEEDBACK_WIDGET_JS_PLACEHOLDER__`-Inject (analog Skin-Switcher),
  konfiguriert über `window.KLICKDUMMY_*`.
- Tests angepasst/ergänzt (Panel-Format, UC-Button); 58 grün, 3.10-Parse + ruff clean.

## [1.9.0] — 2026-06-01

### Added — discovery_push v1.6-Schema: Producer-Seite der ADR-215-§Amendment-1-Auflagen

Arbeitet die **Producer-seitigen** Härtungs-Auflagen aus `platform:ADR-215`
§Amendment 1 ein (ADR ist `accepted`; diese Auflagen sind verbindlich vor
Produktiv-Aktivierung). Discovery-Entry-Schema `v1.5` → **`v1.6`**, rein additiv:

- **Provenance/Drift-Anker** (REC-1/6): `source_repo`, `source_ref`, `commit_sha`,
  `spec_sha256`, `generated_at` — Registry-Eintrag ist abgeleiteter Index mit
  Rückführung auf den exakten Spec-Stand. `_git_provenance` liest `.git` ohne
  Subprozess (tolerant → null).
- **Upsert-Identität** `registry_key` = org/repo + path_rel + spec_id (REC-2).
- **Ingestion-Guard** (REC-7): nur die vier I2-Klassen sind push-berechtigt;
  andere werden mit Hinweis übersprungen (kein vacuous push).
- **Governance-Gate** `discovery.discoverable` (REC-14): Sichtbarkeit aus der
  Spec, nicht aus technischem Push. **Soft-Migrate** (analog I2 Rev-12): nicht
  deklariert → Default true mit Warnung.
- **Sichtbarkeit** `visibility_scope ∈ {repo,org,allowlist,public-demo}`,
  Default `org` = geringste Exposition (REC-6).
- **Filter/Lifecycle-Felder** `pipeline_status`, `off_ramp_status`, `tombstone`
  (REC-5/16).
- **Versionierter Push-Envelope** `{api_version, registry_schema_version,
  generated_at, entries}` + `X-Registry-Schema-Version`-Header + konfigurierbarer
  `--timeout` (REC-4/10).
- **Signierter Fallback-Snapshot** `--snapshot` mit selbst-verifizierendem
  `sha256` (REC-3, Producer-Hälfte).

**Bewusst NICHT hier** (Orchestrator-/Consumer-Seite, separates Go): TTL/Tombstone-
*Enforcement*, Org-Filter/Visibility auf der *Query*, Audit-*Storage*, Picker-
Snapshot-*Konsum* (meiki-hub), Search-Eval-Suite + Skalentest (bei
`klickdummy-search`). 9 neue Tests; 3.10-Parse verifiziert.

## [1.8.0] — 2026-06-01

### Added — `discovery_push`: Spec → pgvector-Discovery-Push (Stage 1.5 PoC)

- Neues Modul `discovery_push` (`platform:ADR-215`, `status: proposed`):
  sammelt Klickdummy-Discovery-Entries cross-repo (über `registry`) und pusht
  sie an einen Orchestrator-Endpoint (`KLICKDUMMY_DISCOVERY_ENDPOINT`, Bearer
  optional). Nur stdlib (`urllib`), keine neue Dependency. API-Vertrag in
  `docs/api/discovery.md`. **PoC/alpha** — Aktivierung erst nach
  Orchestrator-Schema-Migration.
- **Herkunft:** Substanz aus stale PR #5 (Stand v1.4.x) sauber auf aktuelles
  `main` extrahiert statt rebased — der literale Rebase hätte `gen_e2e` (v1.6
  Keystone) aus `__init__`/`test_smoke` regressiert, weil der Branch aus der
  Vor-`gen_e2e`-Ära stammt. Nur die genuin neuen Dateien übernommen
  (`discovery_push.py`, `test_discovery_push.py`, `docs/api/discovery.md`) +
  `__init__`-Export; `manage.py`/Circular-Import-Fixes waren auf `main` bereits
  eigenständig gelöst.

## [1.7.1] — 2026-06-01

### Fixed — Feedback-Widget: PAT-Eingabe als gestyltes Modal statt `window.prompt()`

- GitHub-Token-Abfrage beim Issue-Submit läuft jetzt über ein eingebettetes,
  promise-basiertes Modal (`injectPatModal` / `promptToken`) mit Erklärtext,
  Token-Format-Validierung und Hinweis auf `localStorage`-only-Speicherung —
  statt des nativen `window.prompt()`. Reine `widget.js`-Snippet-Änderung,
  additiv. (Substanz aus stale PR #6 extrahiert; dort war der Fix unter 71
  Editor-Config-Dateien begraben — PR #6 geschlossen.)

## [1.7.0] — 2026-06-01

### Added — Spec-Layer (X-Ray): per-Screen Trace-Strip

- Globaler Toggle **„Spec-Sicht"** (Header-Button + Taste `s`) blendet pro Screen
  einen kompakten, **spec-abgeleiteten** Chip-Streifen ein: betroffene Use Cases,
  Entities/Datenfelder, `class`/`role` (I2), `off_ramp_status` (I3), Acceptance
  (mit Frische), und **Parity-Coverage** (I1: `n/m` ausführbar, prose-only,
  fragile Selektoren). Toggle AUS = unveränderte Echt-App-Illusion für den
  Stakeholder-Walkthrough; AN = volle Nachvollziehbarkeit für Reviewer.
- **Evidenz-Disziplin in der UI:** fehlt ein Feld, rendert ein gestrichelter
  „nicht deklariert"-Chip mit dem **exakten Spec-Feld zum Ergänzen** (Muster aus
  `akte_next` generalisiert) — nie erfunden.
- Coverage nutzt **dieselbe SoR wie `gen_e2e`** (`render_assertion` /
  `is_fragile_selector`), keine Duplikat-Logik.
- Use-Case-Quelle: `screen.use_cases[]` (neu) > `konzept_ref[]` > `akte_next.uc`.
- **Schema:** `screen.use_cases[]` jetzt explizit in `screens-spec.schema.json`
  dokumentiert (vorher nur via `additionalProperties` toleriert). Schema-Generation
  **1.1** (Baseline 1.0 + `use_cases`); Template deklariert `spec_schema_version: "1.1"`.
- ADR-211-konform (rein additiv, spec-gespeist, I1–I3 unberührt) — kein neuer
  Platform-ADR (vgl. `adr-threshold.md`). Reversibel durch Entfernen des Toggles.

## [1.6.1] — 2026-05-31

### Fixed — `gen_e2e` Output `ruff format`-konform (Adopter-Blocker)

- Generierter Output nutzt jetzt **Double-Quotes** (via `json.dumps` statt
  `repr`/Single-Quotes) und **zwei Leerzeilen** zwischen Top-Level-Funktionen.
  Vorher brach jeder Adopter mit `ruff format --check`-CI — real aufgetreten beim
  ersten Adopter (risk-hub). Determinismus, Spec-SHA256-Header und
  Coverage-/Manifest-Verhalten unverändert; neuer Regressions-Test
  (`ruff format --check` auf generiertem Output, via `importorskip`-Äquivalent).

## [1.6.0] — 2026-05-31

### Added — Executable-Parity-Bridge (Keystone, `platform:ADR-211` Rev-18-Kandidat)

- **`klickdummy-gen-e2e`** (`gen_e2e`-Modul): forward-only, **deterministischer**
  Generator Spec → Playwright/pytest-Parity-Suite. Dieselbe Suite läuft per
  `SPEC_RENDERER_BASE_URL` gegen **Renderer #1 (Klickdummy)** und
  **Renderer #2 (echte App)** — parity-grün gegen #2 = I3-Off-Ramp-Gate. Die
  Tests überleben den Off-Ramp (Kontinuität liegt in Spec + Tests, nicht im
  Wegwerf-Renderer).
- **Schema** (`screens-spec.schema.json`): optionaler ausführbarer
  `parity_acceptance[].assert` (`action ∈ {visible,text,clickable,url,count}`,
  `selector`, `expect`) + `screens[].route` + `spec_schema_version`. Prosa-`check`
  bleibt **Pflicht** ⇒ voll rückwärtskompatibel.
- **Reproduzierbarkeits-Manifest** (`*.manifest.json`): `spec_sha256`,
  `generator_version`, Coverage (`executable`/`skipped`), `skipped_detail`
  (Skip-Debt mit Grund), `fragile_selectors`, `uncovered_note`.
- **Determinismus:** Spec-SHA256 statt Zeitstempel im generierten File → ermöglicht
  Drift-Check `klickdummy-parity-drift` (analog `requirements-drift`, ADR-211 S10).
- Selektor-Fragilitäts-Warnung (kein `data-*`-Anker) im Manifest + CLI.

### Provenance / bewusste Grenzen

- Durch **zwei externe LLM-Review-Runden** gehärtet (R1: 25 RECs zur Richtung;
  R2: 15 RECs zum Amendment-Text), Step-5-getaggt. Ein realer Determinismus-Bug
  (Zeitstempel im generierten File) wurde dabei gefunden und gefixt.
- Tag-Tabellen + ADR-211-Rev-18-Amendment-Entwurf laufen über einen **separaten
  platform-PR** (die Konvention lebt in `achimdehnert/platform`, nicht hier).
- **Nicht abgedeckt (bewusst):** NFR/Security/A11y/Performance/Audit
  (Requirements-Bridge-Asymmetrie); F4 nur „für inventarisierte Routen"
  (Alias-/Preview-Risiko offen, F20); plattform-externer Prod-Guard ungebaut (F11).

## [1.5.0] und früher

Siehe Git-History und `platform:ADR-211` Revisionshistorie (Rev ≤17).

# `iil-klickdummy` — Shared Infrastructure for `platform:ADR-211` (Rev 22)

> Versioniertes pip-Paket mit allem, was Klickdummy-Konformität braucht:
> Schemas, Konformitäts-Checks (I1–I5), Requirements-Bridge, S11-Inventur,
> Feedback-Widget v0.5 (Co-Creation-Loop, GitHub-Direkt-API) **und** ab v1.1
> einen Multi-Klickdummy-Browser mit Versions-Switcher.

## Install

**Default (v1.29+):** public PyPI

```bash
pip install "iil-klickdummy>=1.29,<2.0"
```

**Fallback / Dev:** via Git-URL

```bash
pip install "iil-klickdummy @ git+https://github.com/iilgmbh/iil-klickdummy.git@v1.34.0"
```

**Workspace-Pattern (Development):**

```bash
pip install -e ../platform/packages/iil-klickdummy
```

## Console-Scripts

```bash
klickdummy-i1 <spec>:<schema> ...          # Spec ↔ Route Coverage
klickdummy-i2 <spec>:<schema> ...          # 4-Pattern (strict-mode)
klickdummy-i3 <spec>:<schema> ...          # Off-Ramp + Sunset
klickdummy-i4 docs/                        # Cross-Repo-Ref-Format
klickdummy-i5 klickdummy [...]             # Laufzeit-Gate: kein CDN, keine Tailwind-Farbklassen,
                                           #   tokens.css neben kd-nav.js (v1.38, Issue #232),
                                           #   keine Hex-Farben außerhalb Tokens (v1.39, dev-hub#320)
klickdummy-extract-requirements <spec>     # Spec → UC/FR/NFR/Lasten/Pflicht
klickdummy-gen-e2e <spec> [--output <dir>] [--strict-selectors]
                                           # Spec → ausführbare Playwright/pytest-Parity-Suite
                                           # --strict-selectors: bricht ab bei fragilen Selektoren
                                           #   Präfix-Vokabular: testid= (stabil, kanonisch),
                                           #   role=<name> (stabil), label= (stabil), text= (fragil)
klickdummy-stories <spec>                  # story.yaml-Validierung
klickdummy-flow <spec>                     # Screen-Flow-DAG-Lint
klickdummy-stories-manifest               # Stories-Manifest generieren
klickdummy-genesor                         # Lineage-Renderer (genesor)
klickdummy-inventory                       # S11 cross-repo legacy class scan
klickdummy-install-snippets [--symlink]    # HTML+JS+templates in <repo>/platform-snippets/
klickdummy-browser [--output X.html]       # v1.1: Multi-Klickdummy-Browser (Listbox + iframe)
klickdummy-sync                            # Klickdummy-Meta → pgvector-Orchestrator
klickdummy-manage                          # Verwaltungs-CLI (list/status/topics/versions/diff)
klickdummy-tokens --profile <p.yaml> --out tokens.css [--check]
                                           # design-hub-Profil → CSS-Tokens (v1.36)
klickdummy-gen-sitemap <repo_root> <adr_local> [repo_name]
             [--tokens-css <pfad> | --profile <yaml> | --design-hub <dir>]
                                           # Sitemap ohne CDN, Farben/Schriften aus Tokens (v1.37)
```

## v1.1 — Browser-Feature (Stufe 1+2)

Erzeugt eine statische `klickdummy-browser.html` mit:

- **Linke Sidebar:** Listbox „Klickdummy" (alle im Repo gefundenen) + Versions-Switcher (aus Git-History)
- **Detail-Card:** Spec-ID, Klasse-Badge, ADR-Ref, Schwester-Klickdummies, Pfad
- **Main:** iframe lädt aktive shell.html mit `?feedback=on`

Erzeugung:

```bash
cd <repo>
klickdummy-browser --output klickdummy-browser.html
# Browser: open klickdummy-browser.html
```

**Cross-Repo-Modus** (`--cross-repo --base ~/github`) ist v1.2-Roadmap.

## Feedback-Widget (v0.6, Tokens statt Hex seit dev-hub#320 Welle 3 Teil 3)

Browser-side, opt-in via `?feedback=on`. Farben ausschließlich `var(--kd-*)`
(kein Hex-Literal, wie `kd-nav.js`) — lädt `tokens.css` relativ zum eigenen
Skriptpfad nach, wenn `--kd-primary` noch nicht definiert ist. Submit-Modes:

| Mode | Was passiert |
|---|---|
| `download` | Markdown-Datei (offline-fähig, kein GitHub-Token nötig) |
| `clipboard` | navigator.clipboard.writeText |
| `github` | **POST direkt an `api.github.com/repos/.../issues`** mit User-PAT aus `localStorage.klickdummy_github_token`; Issue-Author = realer GitHub-User; Audit native |

**Konfiguration im Host (vor Widget-Script-Tag):**

```html
<script>
  window.KLICKDUMMY_SPEC = { id: "repo:klickdummy-spec-<name>", version: "0.1", klickdummy_class: "mock" };
  window.KLICKDUMMY_FEEDBACK_REPO = "owner/repo";        // GitHub-Zielrepo
  // optional Plugin-Hooks:
  window.KLICKDUMMY_CATEGORIES = [...];                  // override default 5
  window.KLICKDUMMY_PERSONA_HOOK = () => '...';
  window.KLICKDUMMY_VERFAHREN_HOOK = () => '...';
</script>
<script src="platform-snippets/klickdummy/feedback-widget/widget.js" defer></script>
```

## kd-nav.js — Tokens statt Hex (v1.38, dev-hub#320 Welle 3)

`_shared/kd-nav.js` (Hauptmenü-Button, Zurück-Button, Tour-Footer) verwendet
ausschließlich `var(--kd-*)`-Tokens, keine Hex-Literale. Beim Start prüft es,
ob `--kd-primary` bereits auf `:root` definiert ist (`getComputedStyle`);
falls nicht, lädt es `_shared/tokens.css` relativ zum eigenen, vom Browser
aufgelösten Skriptpfad (`document.currentScript.src`) nach. Bewusst KEIN
Hex-Fallback — fehlt `tokens.css`, bleibt die Chrome sichtbar ungestylt statt
geraten; `klickdummy-i5` prüft das als Laufzeit-Gate (siehe unten). Keine
Ampel-/Statusfarbe wird gebraucht (reines Navigations-Chrome) — die
optionalen `--kd-success/-warning/-danger/-info` (aus `colours.success/
warning/danger/info` im design-hub-Profil, `gen_tokens.py` rendert jeden
`colours`-Key generisch) bleiben dafür ungenutzt.

## I5 — Laufzeit-Gate: kein CDN, keine Tailwind-Farbklassen, keine Hex-Farben (v1.40, Issue #232, dev-hub#320 Welle 3/4)

```bash
klickdummy-i5 klickdummy [klickdummy/mod2 ...]
```

Prüft alle `*.html` unter den übergebenen Klickdummy-Verzeichnissen
(inkl. `sitemap/`, ohne `dist/`, `_archiv/`, `archive/`); Regel (4) prüft
zusätzlich `*.css`/`*.js`:

1. kein `<script src="http(s)://...">` / `<link href="http(s)://...">` (CDN)
2. keine Tailwind-Farb-Utility-Klassen (`text-blue-600` etc.) — AUSNAHME
   (v1.40, s. „Tailwind-Klickdummies" unten): token-gemapptes Tailwind via
   `_shared/tailwind-tokens.js`.
3. liegt `_shared/kd-nav.js` vor, muss `_shared/tokens.css` daneben existieren
4. **Farben nur aus Tokens (v1.39):** kein literaler Hex-Farbwert
   (`#abc`, `#a1b2c3`, optional `#a1b2c3d4`) in `*.html`/`*.css`/`*.js` —
   außer in `_shared/tokens.css`, `_shared/semantic.css`,
   `assets/tokens.css`, `assets/semantic.css` (Datei-Ausnahme: dort ist der
   Hex-Wert die Quelle). `sitemap/index.html` bettet `tokens.css` roh als
   ersten `<style>`-Block ein — statt die ganze Datei auszunehmen (das würde
   eine von Hand gesetzte Farbe im selben File nie fangen), wird nur der
   EINE `<style>`-Block ausgeblendet, dessen Inhalt mit der
   Generator-Kopfzeile beginnt (`/* tokens.css — generiert aus
   design-hub-Profil`); der Rest der Datei bleibt im Scan. Gedacht für die
   Welle-3-Shells (eigene Klickdummy-Shells in 11 Repos, dev-hub#320): die
   Meldung nennt je Datei die Trefferanzahl, damit ein Repo den Umbau auf
   Tokens planen kann. Issue-Referenzen (`#320`) und CSS-Anker (`#fb-fab`)
   lösen bewusst keinen Treffer aus.

Rollout: `snippets/gates.mk` definiert das Target `klickdummy-i5` (verteilt
über `klickdummy-install-snippets`); der reusable Workflow
`klickdummy-parity-gate.yml@main` ruft `make klickdummy-i5` automatisch mit
auf, sobald ein Repo ihn referenziert. Der lokale `klickdummy:`-Composite-
Target (I1-I4, siehe z. B. apo-hub/Makefile) lebt dagegen historisch
handgepflegt im jeweiligen Adopter-Makefile — dort muss `klickdummy-i5`
weiterhin manuell ergänzt werden, das Snippet holt das nicht automatisch nach.

### Tailwind-Klickdummies (v1.41, dev-hub#320 Welle 4)

Manche Repos (z. B. risk-hub, 24 Klickdummies) nutzen einen **vendorten**
`_shared/tailwind.js` (Play-CDN-Build, lokal, kein CDN-Zugriff zur Laufzeit)
mit Tailwind-Utility-Farbklassen (`bg-indigo-700` etc.). Regel 2 verbietet
das grundsätzlich (Farben nur aus `var(--kd-*)`) — statt die Regel
aufzuweichen, mappt `snippets/_shared/tailwind-tokens.js` jede
Tailwind-Farbfamilie auf ein `var(--kd-*)`-Token, mit je DREI Shade-Bändern
(hell/mittel/dunkel statt eines einzigen Kern-Tokens — Fix für
iilgmbh/iil-klickdummy#238: sonst wird z. B. `bg-amber-100 text-amber-800`
Text-auf-gleicher-Farbe):

| Familie | 50–200 (hell) | 300–500 (mittel) | 600–950 (dunkel) |
|---|---|---|---|
| Marken (indigo, blue, violet, purple, fuchsia, pink, teal, **orange**) | `--kd-bg-light` | `--kd-accent-1` | `--kd-primary` |
| Grau (slate, gray, zinc, neutral, stone) | `--kd-bg-light`/`-zebra` | `--kd-border`/`-line` | `--kd-text`/`-muted` |
| Erfolg (green, emerald, lime) | `--kd-success-bg` | `--kd-success` | `--kd-success-dark` |
| Warnung (yellow, amber) | `--kd-warning-bg` | `--kd-warning` | `--kd-warning-dark` |
| Fehler (red, rose) | `--kd-danger-bg` | `--kd-danger` | `--kd-danger-dark` |
| Info (cyan, sky) | `--kd-info-bg` | `--kd-info` | `--kd-info-dark` |

Status-Tokens haben eine CSS-Fallback-Kette auf ein garantiert vorhandenes
Kern-Token (`--kd-bg-light`/`--kd-text`/`--kd-accent-1`/`-2`/`--kd-primary-dark`),
falls das Profil das optionale `-bg`/`-dark`-Token nicht liefert. **`orange`
zählt bewusst als Marken-Familie, nicht als Warnfarbe** — sonst landen KDs,
die Orange als Hauptfarbe nutzen, komplett in `--kd-warning`. Volle Tabelle
inkl. Begründung: Kopf-Kommentar der Datei.

Einbindung: `_shared/tailwind-tokens.js` **vor** `_shared/tailwind.js` laden
(Tailwind Play-CDN liest `window.tailwind.config` beim Laden):

```html
<script src="_shared/tailwind-tokens.js"></script>
<script src="_shared/tailwind.js"></script>
```

`klickdummy-i5` erkennt ein vorhandenes `_shared/tailwind-tokens.js` und
prüft: (a) ist jede im Baum tatsächlich verwendete Farbfamilie darin
gemappt — fehlt eine, Fehler mit Familienname; (b) lädt jede HTML-Datei mit
Tailwind-Farbklassen das Mapping vor `tailwind.js` — sonst Fehler „Mapping
nicht geladen: <datei>". Sind beide Bedingungen erfüllt, gelten
Tailwind-Farbklassen als token-gemappt (Info-Zeile „Regel 2:
Tailwind-Klassen token-gemappt (N Familien)" statt Fehlerliste). Ohne
`tailwind-tokens.js` im Baum bleibt Regel 2 unverändert: jede Klasse ein
Fehler.

## Schemas (importlib.resources)

```python
from importlib.resources import files
import json
schema = json.loads(files("iil_klickdummy.schemas").joinpath("screens-spec.schema.json").read_text())
```

## Bezug

- `platform:ADR-211` (aktuell Rev 22) — Konvention + Distribution + Co-Creation-Pfade (seit Rev 13)
- `platform:ADR-212` — Traefik-Ingress (für künftige PyPI-Selbsthost)
- `platform:ADR-213` — Cross-Repo-Ref-Format (was `klickdummy-i4` prüft)
- `achimdehnert/dev-hub#320` (Welle 3) / `iilgmbh/iil-klickdummy#232` — `klickdummy-i5` Laufzeit-Gate + kd-nav.js auf Tokens

## v1.2 — klickdummy-sync (Stufe 2)

Per `platform:ADR-211` Rev 14 §Multi-Klickdummy-Browser Stufe 3 (Cross-Repo): pushe Klickdummy-Metadaten + Iterations-Logs + ADR-Bodies in den **Orchestrator pgvector-Memory** für semantische Cross-Repo-Suche.

### CLI

```bash
klickdummy-sync --repo .                   # repo-lokal, NDJSON auf stdout
klickdummy-sync --cross-repo               # alle 6 Klickdummy-Repos
klickdummy-sync --cross-repo --output sync.ndjson
klickdummy-sync --repo . --dry-run         # nur Listen
```

### Architektur — NDJSON-getrennt vom Push

Das Sync-Modul produziert **NDJSON** (eine Zeile pro Memory-Entry). Der eigentliche Push an Orchestrator-pgvector erfolgt in einem zweiten Schritt — entweder:

- via `claude-policy push --ndjson sync.ndjson` (SSH+docker-exec, kein MCP nötig)
- via CC/Cascade-Session mit gebundenem `orchestrator__agent_memory_upsert`
- via nightly GitHub-Action mit Orchestrator-API-Token

**Warum getrennt:** das Paket bleibt MCP-frei und unter PyPI-Standards. Auth zum Orchestrator ist Sache des Konsumenten (Org-spezifisch).

### Entry-Typen

| was | entry_type | entry_key-Schema |
|---|---|---|
| Klickdummy-Spec | `repo_context` | `klickdummy:<org>:<repo>:<name>` |
| Iteration (feedback-log) | `lesson_learned` | `klickdummy-iter:<org>:<repo>:<name>:<n>` |
| Klickdummy-ADR | `decision` | `klickdummy-adr:<org>:<repo>:ADR-<NNN>` |

### Tags (Multi-Tenant + Filter)

- `klickdummy` (alle)
- `klickdummy:class:<mock|stub-demo|story|spec-demo>`
- `klickdummy:org:<iilgmbh|achimdehnert|ttz-lif|meiki-lra>`
- `klickdummy:repo:<name>`
- `gov-data` für ttz-lif / meiki-lra-Workloads

### Dogfood

```
$ klickdummy-sync --cross-repo --dry-run
== Klickdummy-Sync → Orchestrator (v1.2) ==
  · meiki-hub:   1 KD · 7 Iter · 3 ADRs
  · writing-hub: 1 KD · 0 Iter · 1 ADR
  · risk-hub:    0 KD · 0 Iter · 1 ADR
  · ttz-hub:     2 KD · 0 Iter · 2 ADRs
  Total: 18 Entries
```

## v1.4 — klickdummy-manage (Repo + Topic + Version)

CLI für die einheitliche Verwaltungs-Sicht über alle Klickdummies:

```bash
klickdummy-manage list                          # Tabelle aller cross-repo
klickdummy-manage list --org iilgmbh --class mock
klickdummy-manage status --sunset-due-in 30     # Health-Check
klickdummy-manage topics                        # Topic-Cluster
klickdummy-manage versions <spec_id>            # Git-History 1 KD
klickdummy-manage diff <spec_id> v0.1 v0.2      # Versions-Diff
```

**Neues optionales Spec-Feld** `meta.topic` (freier String):

```yaml
spec_id: meiki:klickdummy-spec-fristenmanagement
spec_version: "0.1"
title: ...
class: mock
meta:
  topic: fristen          # ← NEU, optional, frei wählbar
  # weitere meta-Felder hier denkbar
screens: [...]
```

`klickdummy-manage topics` aggregiert Klickdummies nach diesem Feld. Specs
ohne `meta.topic` landen unter „(kein topic)" — kein Bruch zu v1.3.

**Status-Check** prüft:
- `sunset_after`-Datum überschritten? → Warnung
- `sunset_after` in <N Tagen fällig? → Warnung
- `class` in 4-Pattern (mock|stub-demo|story|spec-demo)? → sonst Warnung
- ADR-Frontmatter vollständig? → fehlt sunset_after → Warnung

## v1.36 — klickdummy-tokens (design-hub-Profil → CSS-Tokens)

Erzeugt eine deterministische `tokens.css` aus einem design-hub-Profil
(`profiles/<slug>.yaml`, Source of Truth für Klickdummy-Corporate-Design,
dev-hub#320) — keine Zeitstempel, keine Rechner-Pfade, zwei Läufe sind
byte-gleich:

```bash
klickdummy-tokens --profile design-hub/profiles/meiki-lra.yaml --out klickdummy/_shared/tokens.css
klickdummy-tokens --profile design-hub/profiles/meiki-lra.yaml --out klickdummy/_shared/tokens.css --check
                                           # CI-Gate: Exit 1 bei Abweichung/fehlender Datei
```

`fonts.*` → `--kd-font-primary`/`--kd-font-mono`; jeder Key unter `colours`
→ `--kd-<key mit _→->` (Reihenfolge wie im Profil); optionales `colours_dark`
→ derselbe Block unter `[data-theme="dark"]`. Fehlender Pflichtschlüssel oder
ungültiger Farbwert (kein `#RRGGBB`) → Exit 2 mit Schlüsselnennung.

Exit 1 bei Warnings (für CI-Hooks).

## v1.37 — `klickdummy-gen-sitemap` ohne CDN (Tokens statt Tailwind/lucide)

Die Sitemap lädt kein `cdn.tailwindcss.com`/`unpkg.com` mehr — Layout kommt
aus einem eingebetteten `<style>`-Block, der ausschließlich `var(--kd-*)`-
Tokens nutzt (dev-hub#320 Welle 0). Drei Wege, die Tokens einzubetten
(Priorität von oben nach unten):

```bash
klickdummy-gen-sitemap . repo:ADR-NNN --tokens-css klickdummy/_shared/tokens.css
klickdummy-gen-sitemap . repo:ADR-NNN --profile design-hub/profiles/meiki-lra.yaml
klickdummy-gen-sitemap . repo:ADR-NNN   # IIL-Fallback: <design-hub>/profiles/iil-extern.yaml
```

Ohne `--tokens-css`/`--profile` sucht der Generator `iil-extern.yaml` unter
`--design-hub <dir>` (Default `$GITHUB_DIR/design-hub`, sonst
`~/github/design-hub`); fehlt die Datei, bricht er mit Exit 2 ab, statt eine
Sitemap ohne jede Farbe zu schreiben. Keine Kopie des IIL-Profils im Paket —
design-hub bleibt einzige Quelle.

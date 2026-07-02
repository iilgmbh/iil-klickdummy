# `iil-klickdummy` — Shared Infrastructure for `platform:ADR-211` (Rev 22)

> Versioniertes pip-Paket mit allem, was Klickdummy-Konformität braucht:
> Schemas, Konformitäts-Checks (I1–I4), Requirements-Bridge, S11-Inventur,
> Feedback-Widget v0.5 (Co-Creation-Loop, GitHub-Direkt-API) **und** ab v1.1
> einen Multi-Klickdummy-Browser mit Versions-Switcher.

## Install

**Default (v1.29+):** public PyPI

```bash
pip install "iil-klickdummy>=1.29,<2.0"
```

**Fallback / Dev:** via Git-URL

```bash
pip install "iil-klickdummy @ git+https://github.com/achimdehnert/iil-klickdummy.git@v1.29.0"
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

## Feedback-Widget (v0.5)

Browser-side, opt-in via `?feedback=on`. Submit-Modes:

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

## Schemas (importlib.resources)

```python
from importlib.resources import files
import json
schema = json.loads(files("iil_klickdummy.schemas").joinpath("screens-spec.schema.json").read_text())
```

## Bezug

- `platform:ADR-211` Rev 13 — Konvention + Distribution + Co-Creation-Pfade
- `platform:ADR-212` — Traefik-Ingress (für künftige PyPI-Selbsthost)
- `platform:ADR-213` — Cross-Repo-Ref-Format (was `klickdummy-i4` prüft)

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

Exit 1 bei Warnings (für CI-Hooks).

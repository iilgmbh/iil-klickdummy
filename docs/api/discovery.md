# Klickdummy Discovery API v1.5 (PoC)

**Stage 1.5 aus** `platform:ADR-215` (proposed) — pgvector-Discovery
für Cross-Repo-Klickdummies.

**Status:** PoC, alpha. Endpoint-URL noch nicht fix; tatsächliche
Aktivierung erst nach Orchestrator-seitiger Schema-Migration.

## API-Vertrag

### Endpoint

```
POST {KLICKDUMMY_DISCOVERY_ENDPOINT}
```

Default: `https://orchestrator.iil.pet/api/discovery/klickdummy/upsert`

Authentifizierung optional via Bearer-Token (ENV
`KLICKDUMMY_DISCOVERY_TOKEN`).

### Request-Body

```json
{
  "entries": [
    { /* discovery_entry */ },
    ...
  ]
}
```

### `discovery_entry`-Schema (v1.5)

| Feld | Typ | Beispiel | Bemerkung |
|---|---|---|---|
| `schema_version` | string | `"v1.5"` | Schema-Version (für Forward-Compat) |
| `spec_id` | string | `"meiki:klickdummy-spec-fristenmanagement"` | qualifiziert mit Repo-Präfix |
| `version` | string | `"0.1"` | spec_version oder bot_version |
| `klickdummy_class` | string | `"mock"` | `mock` / `stub-demo` / `story` / `spec-demo` |
| `topic` | string | `"fristen"` \| `"lost-units"` | aus `render_meta.konzept_id` o.ä. |
| `adr` | string | `"meiki:ADR-021"` | repo-lokale ADR-Ref |
| `conforms_to` | string | `"platform:ADR-211"` | aus `adr.conforms_to` |
| `sister_of` | string[] | `["sqf-hub:ADR-003"]` | aus `adr.sister_of` |
| `repo` | string | `"meiki-lra/meiki-hub"` | abgeleitet aus `git remote` |
| `path_rel` | string | `"docs/01-architektur/mockups/.../screens-spec.yaml"` | relativ zu Repo-Root |
| `genre` | string | `"forms"` \| `"conversation"` \| `"spec-demo"` | Renderer-Heuristik |
| `personas` | string[] | `["sachbearbeiter", "teamleitung"]` | aus `personas`-Keys |
| `embedding_text` | string | `"Fristenmanagement Cockpit Worklist ..."` | max 4096 Zeichen, vom Orchestrator embedded |
| `last_seen` | string (ISO-datetime) | `"2026-05-21T13:45:00+00:00"` | Zeitpunkt des Push |
| `sunset_after` | string (date) | `"2027-05-21"` | aus Spec-Frontmatter |

### Response

```json
{
  "upserted": 8,
  "skipped": 0,
  "errors": []
}
```

## CLI-Verwendung

### Listen

```bash
python -m iil_klickdummy.discovery_push list \
    --cross-repo --base ~/github \
    --repos meiki-hub,ttz-hub,sqf-hub,pg-hub
```

Output: ASCII-Tabelle mit ORG · NAME · VER · GENRE · CLASS · ADR.

### NDJSON-Export (kein Push)

```bash
python -m iil_klickdummy.discovery_push push \
    --cross-repo --base ~/github \
    --repos meiki-hub,ttz-hub,sqf-hub,pg-hub \
    --output /tmp/discovery.ndjson
```

### Direct-Push (HTTPS)

```bash
export KLICKDUMMY_DISCOVERY_TOKEN=...    # optional
python -m iil_klickdummy.discovery_push push \
    --cross-repo --base ~/github \
    --repos meiki-hub,ttz-hub,sqf-hub,pg-hub \
    --to-orchestrator
```

Default-Endpoint: `https://orchestrator.iil.pet/api/discovery/klickdummy/upsert`. Override via `--endpoint URL` oder ENV `KLICKDUMMY_DISCOVERY_ENDPOINT`.

### Dry-Run

```bash
python -m iil_klickdummy.discovery_push push \
    --cross-repo --base ~/github \
    --repos meiki-hub,sqf-hub \
    --dry-run
```

Output: NDJSON aller Einträge auf stdout, kein Network-Call.

## Konsumenten

### Cross-Repo-Picker (Renderer-Side)

Statt `CROSS_REPO_INDEX` als JS-Konstante in `shell.html` zu pflegen:

```javascript
// Iter. 23 Pattern (Empirie #1)
async function loadCrossRepoIndex(){
  try {
    const resp = await fetch(
      'https://orchestrator.iil.pet/api/discovery/klickdummy/list',
      { signal: AbortSignal.timeout(2000) }
    );
    if(resp.ok) return await resp.json();
  } catch(e){ /* falls Orchestrator down, fallback */ }
  // Fallback: lokale Konstante (Stand: zum letzten Build)
  return CROSS_REPO_INDEX_FALLBACK;
}
```

### Semantische Search (Phase B)

```bash
curl -X POST https://orchestrator.iil.pet/api/discovery/klickdummy/search \
    -H "Content-Type: application/json" \
    -d '{"query": "Eskalation rote Frist Bauarbeiten", "limit": 5}'
```

Erwartete Top-Treffer: meiki:fristen.eskalation, sqf:af1.top-stoerfaelle, pg-hub:do-einstufung-risiko.

## DSGVO

DSFA 2026-05-21 (User-Klärung):

- Personendaten in Discovery-Entries: **keine** (außer Persona-Funktionsrolle-Labels wie `sachbearbeiter`)
- Operativ-Daten: bleiben in Klickdummies, durchgehend synthetisch (`class: mock`)
- Discovery-Embeddings: nur strukturelle Texte (Titel, Purpose, Parity-Anker)
- **Klassifikation:** nicht kritisch — Stage 1.5 (Discovery) und Stage 2 (iil.pet-Hosting) DSGVO-konform

## Open Loops

1. **Orchestrator-seitiges Schema** für `klickdummy-registry` Sub-Collection (Embedding-Modell, Index-Spalten)
2. **Search-Endpoint** (`POST /api/discovery/klickdummy/search`) — pgvector-Query-Wrapper
3. **MCP-Tool-Integration**: `mcp__orchestrator__klickdummy_discovery_*` für Claude-Code-Sessions
4. **CI-Push**: GitHub Action, die bei `main`-Merge eines Klickdummy-PRs den Push triggert
5. **Console-Script-Registration**: `klickdummy-discovery = "iil_klickdummy.discovery_push:main"` — kommt in v1.5-Release-PR (separate Iter.)

## Refs

- `platform:ADR-215` (proposed) — Discovery-Konzept
- `platform:ADR-211` Rev 12 — Klickdummy-Rahmen
- `platform:ADR-113` — Orchestrator pgvector
- `iilgmbh/iil-klickdummy` Issue #4 — v1.5-Roadmap

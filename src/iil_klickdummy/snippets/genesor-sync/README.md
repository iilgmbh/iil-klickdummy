# Genesor-Sync · Klickdummy → GitHub Issue + Project

**Heimat:** `iil-klickdummy/src/iil_klickdummy/snippets/genesor-sync/`
**Counter-A-Implementation** aus dem advocatus-diabolus-Review 2026-05-24

## Was es macht

Wandelt deinen `screens-spec.yaml` automatisch in ein **GitHub Issue** um
und fügt es (optional) zu einem **Org-level GitHub Project** hinzu. Damit
wird die Pipeline-/Lifecycle-Sicht in GitHub geführt, wo Auth, Audit-Log,
Mobile-App, Kommentar-Stream und Roadmap-View nativ vorhanden sind —
Genesor bleibt die Spec-Topologie-Sicht.

| Aspekt | wo |
|---|---|
| Spec (SSoT für Inhalt) | `screens-spec.yaml` im Repo |
| Pipeline-Status / Stakeholder-Assign / Kommentar | GitHub Issue + Project |
| Topologie-Visualisierung | Genesor (`klickdummy_lineage.py --genesor`) |

## Adoption (~5 min pro Repo)

1. **Skript kopieren:**
   ```bash
   mkdir -p .github/scripts .github/workflows
   cp <iil-klickdummy>/snippets/genesor-sync/klickdummy_sync.py .github/scripts/
   cp <iil-klickdummy>/snippets/genesor-sync/klickdummy-sync.yml .github/workflows/
   ```

2. **(Optional) Repo-Variable für Project-URL** (Settings → Variables → Actions):
   ```
   GENESOR_PROJECT_URL = 1   # oder die volle URL deines Org-Projects, z. B.
                              # https://github.com/orgs/achimdehnert/projects/<N>
   ```
   Ohne diese Variable läuft der Sync trotzdem — nur das Project-Add wird
   geskippt.

3. **(Optional) Repo-Secret für Project-Token** (Settings → Secrets → Actions):
   ```
   GENESOR_PROJECT_TOKEN = ghp_xxxx...   # Org-PAT mit 'project'-Scope
   ```
   Notwendig **nur** wenn du auch das Project-Add brauchst.
   `GITHUB_TOKEN` (Default) kann Issues, aber keine Projects-V2-Membership.

4. **Erster Lauf:** entweder direkt pushen oder manuell via UI:
   `Actions → Klickdummy Sync (Genesor) → Run workflow → dry_run: true`

5. **Idempotent:** Jedes Issue wird über den Sentinel
   `<!-- klickdummy-sync:<kd-name> -->` im Body wieder gefunden — kein
   Doppel-Anlegen, kein Pipeline-Status-Verlust beim nächsten Sync.

## Was kommt ins Issue

- **Titel:** `[Klickdummy] <kd-name> — <Title aus Spec>`
- **Body:** Markdown-Tabelle mit `class`, `spec_role`, `sunset_after`,
  Personas, Screens-Liste, Beziehungen (consumes_from / provides_contracts
  / accepts_contracts / root_entities), Spec-Link
- **Labels:** `klickdummy`, `klickdummy/class:<class>`, ggf.
  `klickdummy/role:<root|hybrid>`
- **Sentinel** (HTML-Kommentar) für Idempotenz

## Was bleibt menschlich pro Issue

Diese Felder werden **nicht** vom Sync überschrieben — sie sind die
Domäne der GitHub-Pipeline-Sicht:

- **Assignees** — wer ist verantwortlich?
- **Project-Felder** (`pipeline_status`, `stakeholder`, manueller `org`-Override)
- **Kommentare**, **Reaktionen**, **Links zu PRs**
- **Open/Closed-Status**

## Project-Setup (einmalig, optional)

Wenn du ein zentrales IIL-Genesor-Project willst:

1. Org-level Project anlegen: `Organization → Projects → New project`
2. **Custom Fields** (empfohlen):

   | Field | Type | Beispiel-Werte |
   |---|---|---|
   | `org` | Single-Select | meiki-lra · ttz-lif · bahn-sqf · achimdehnert · iilgmbh |
   | `pipeline_status` | Single-Select | idea · klickdummy · pilot · prod · sunset |
   | `class` | Single-Select | mock · stub-demo · story · spec-demo |
   | `spec_role` | Single-Select | root · hybrid · default |
   | `sunset_after` | Date | (ISO) |
   | `stakeholder` | Text | (frei) |

3. **Views erstellen:**
   - *Tabelle* (alle KDs, sortierbar)
   - *Kanban by pipeline_status* (Workshop-Ansicht)
   - *Roadmap by sunset_after* (Aging-Sicht)
   - *Filter „abgelaufen oder < 90d"*

4. URL kopieren → in Repo-Variable `GENESOR_PROJECT_URL`.

## Trade-offs (advocatus-diabolus)

| Pro | Contra |
|---|---|
| Native Auth / Audit / Mobile / Notifications | Stakeholder ohne GitHub-Account sehen nichts |
| Pipeline-Kanban + Roadmap built-in | Custom Fields müssen pro Org-Project manuell angelegt werden |
| Multi-User-Kollab (Kommentare, Reaktionen) | Org-Setup ist einmaliger Overhead |
| Spec bleibt SSoT für Inhalt | Bei Spec-Sync werden manuelle Body-Edits überschrieben |

## Bezug zu ADRs

- `platform:ADR-211` Rev 13 §Distribution — diese Heimat
- `platform:ADR-211` I1 — Spec bleibt SSoT (Sync, nicht Replace)
- `platform:ADR-211` I3 — `sunset_after` wird mitsyncysiert, GitHub kann Aging-Filter
- `platform:ADR-213` — Cross-Repo-Refs werden im Body wörtlich mitübernommen
- `meiki:ADR-035` (Lineage-Viewer-Meta) — Genesor bleibt Spec-Sicht-Tool, GitHub übernimmt Pipeline-Sicht

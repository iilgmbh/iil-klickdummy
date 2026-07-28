# Agent Handover — iil-klickdummy

**Kuratierter Einstieg für Coding-Agent-Sessions.** Der Session-Start-Hook
(`handover_prio_mirror.sh`) spiegelt die Tabelle unter `## Prioritäten`;
`NEXT.md` ist nur der git-log-Fallback. Pflege: bei `/session-ende` aktualisieren.

## ⚡ Aktueller Stand (2026-07-27, Sitemap-Konsistenz + coach-hub-Entstörung)

**Auslöser:** Frage, warum 137-hubs Klickdummy nirgends erreichbar ist. Daraus wurde ein
Strang über 8 Repos, weil an mehreren Stellen dieselbe Wurzel lag: **eine unterbrochene
Prüfkette**. Wo nichts prüfte, verrottete etwas unbemerkt.

**iil-klickdummy — zwei Releases:**
- **1.32.5**: `entry_key`-Dedup lief nur pro Repo, Duplikate aus zwei Roots mit gleichem
  `org/repo` überlebten bis ins NDJSON (Konsumenten upserten last-write-wins → die
  *ältere* Variante gewann, [#188](https://github.com/iilgmbh/iil-klickdummy/issues/188)).
  Plus Truncation-Marker und ziffern-präfigierte Repo-Namen im Schema
  ([#179](https://github.com/iilgmbh/iil-klickdummy/issues/179), entblockte 137-hub).
- **1.32.6**: `gen_sitemap` sammelte Wurzeln nur aus Specs mit `spec_role: root` — das Feld
  ist optional, also hatten **8 von 10** ausgerollten Repos `roots=[]` und rendeten sichtbar
  `0 Wurzeln · 0 Knoten gesamt`. Dazu Zyklen-Schutz im DFS und: `kd-nav.js` wurde von jeder
  Sitemap eingebunden, aber **nie ausgeliefert** (lag nur in risk-hub) — 404 in 9 Repos.

**Rollout:** 13 Repos regeneriert, Endzustand gegen `main` verifiziert (nicht gegen den
eigenen Generierungslauf): 13/13 mit `Wurzeln>0` und `kd-nav.js`. 137-hub, billing-hub und
recruiting-hub sind neu im genesor-Manifest ([iil-pet-portal#31](https://github.com/iilgmbh/iil-pet-portal/pull/31)),
Ingest + Pages-Deploy grün — `kd/137-hub/klickdummy/` ist live.

**Neues PyPI-Paket:** `iil-django-lms-lite` 0.1.1 (Trusted Publishing via OIDC,
Distributions-Guard gegen `tests/`-Leak). Schließt den offenen ADR-266-Punkt
„django-lms-lite … publizieren oder Registry-`pypi:`-Feld entfernen".

**coach-hub war seit dem 2026-07-18 nicht deploybar** und ist es wieder. Drei
Produktivdefekte, alle erst sichtbar, nachdem die Testkette wieder lief:
1. `requirements.txt` zog `django-lms-lite` per `git+https` aus einem privaten Repo, der
   Build-Token war ungültig → jetzt PyPI-Paket, Token-Kopplung ersatzlos weg.
2. `templates/base.html` reversete `module_shop:catalogue` ohne registrierten Namespace
   (seit `cc9b79a`, 2026-04-22) → `NoReverseMatch` auf eingeloggten Seiten. Link entfernt
   (Owner-Entscheid).
3. `apps/core/api.py:129` filterte `Course.objects.filter(is_active=True)` — Feld existiert
   nicht → `GET /api/learning/progress/` warf `FieldError`.

Testsuite von **21 rot auf 278 grün** (ADR-150-Migration in den Fixtures nachgezogen,
Scoring-Skala und `/healthz/`-Erwartung an den Produktivcode angeglichen, Cache-Leak
zwischen Tests geschlossen — der löste nebenbei ein `xfail` auf).

**Dev-DB-Kollision:** coach-hub *und* billing-hub hatten `postgres://…:5434/…` als Default,
auf 5434 läuft aber `writing_hub_db_dev`. Wer lokal ohne `DATABASE_URL` startete, schrieb in
die Dev-DB eines fremden Repos. Beide auf freie Ports gezogen (5438/5440), Belegung im Code
dokumentiert.

**Lehre für den nächsten Batch (korrigiert 2026-07-28 durch die Retro):** 9 Merges innerhalb von
~31 Sekunden → **6 von 9 Deploys scheiterten in Attempt 1**, mit **vier verschiedenen Ursachen**:
GHCR-`403` (research-hub, pptx-hub, 137-hub — nach Rerun grün), Host-Compose-Guard
(recruiting-hub, `docker-compose.prod.yml absent`), DNS (apo-hub, blieb rot), Migrate-Crashloop
(tax-hub, nie rerun).

Die ursprüngliche Fassung dieses Absatzes nannte „5 Deploys in `429`/`403`" und führte alle auf
GHCR zurück — beides falsch. Nachdem drei Logs GHCR zeigten, wurde nicht weitergelesen. Zwei der
Fehlschläge waren durch einen Rerun gar nicht heilbar.

**Zweifache Lehre:** (1) Gestaffelt mergen, nicht in einem Rutsch. (2) Bei Mehrfach-Fehlschlägen
jeden Lauf **einzeln** zuordnen, bevor eine gemeinsame Ursache benannt wird — und beachten, dass
`gh run rerun` die `conclusion` überschreibt: der Attempt-1-Fehler ist danach nur noch über
`gh api repos/<o>/<r>/actions/runs/<id>/attempts/1/jobs` sichtbar.
Beleg: Retro `session-retro-2026-07-27-iil-klickdummy-aa60bb` (platform#1503), Befund #9.

## ⚡ Aktueller Stand (2026-07-16, Folgesession — Issue #176 gegengecheckt, prod-server-RAM-Fund)

**Issue #176 gegengecheckt** (war 2 Tage veraltet): billing-hub#28 + recruiting-hub#15 wurden
2026-07-15 gemergt, aber **beide Deploy-Runs schlugen fehl** (kein Retry) — [Issue #176
aktualisiert](https://github.com/iilgmbh/iil-klickdummy/issues/176). wedding-hub#34 ist nicht
mehr CI-rot, aber weiterhin blockiert (Ruleset erwartet `ci / gate`, den das Repo nie erzeugt) —
Fix als [wedding-hub#36](https://github.com/achimdehnert/wedding-hub/pull/36) vorbereitet.

**Deploy-Rerun (explizit freigegeben) — beide erneut fehlgeschlagen**, gleiche Ursache: geteilter
Runner `prod-server` (billing-hub + recruiting-hub + ~7 weitere Hubs auf **einem** Host, RAM
strukturell überbucht — bereits als [platform#1078](https://github.com/achimdehnert/platform/issues/1078)
getrackt, 3,7-fache `Committed_AS`/`CommitLimit`-Überbuchung). "Warten bis Last sich beruhigt"
ist laut Memory bereits 2× widerlegt — kein 3. Retry ohne echten Fix.

**ADR-257 gefunden** (accepted, in-progress): entschied bereits einen dedizierten Non-Prod-Runner
(`ci-nonprod`), aber nur travel-beat (Pilot) hat ihn tatsächlich registriert — **`ci-nonprod` ist
PER-REPO registriert, nicht org-weit geteilt** (wichtige Korrektur einer ersten Fehlannahme).
PRs [billing-hub#30](https://github.com/achimdehnert/billing-hub/pull/30) / [recruiting-hub#17](https://github.com/achimdehnert/recruiting-hub/pull/17)
vorbereitet, aber **billing-hub#30 hängt aktuell auf `ubuntu-latest`** (Test lief nur gegen
`ci.yml`s harmlosen `ci`-Job grün — der eigentliche `deploy.yml`-Build-Job ist **ungetestet**,
da ein echter `workflow_dispatch`-Test bewusst nicht freigegeben wurde). recruiting-hub#17 steht
noch auf `ci-nonprod` (würde ohne eigenen Runner ewig `queued` bleiben).

**Entscheidung: kein Ad-hoc-Fix, sondern `/konzept`** — User stoppte die begonnene Konzept-
Arbeit mitten in dieser Session ("später eigene Session"). Tracking-Issue:
[platform#1217](https://github.com/achimdehnert/platform/issues/1217) — enthält die volle,
bereits gesammelte Evidenz (ADR-257, Runbook, #1078, Runner-API-Belege, Test-Ergebnis) für den
Direkteinstieg. **Nächste Session zu diesem Thema: `/konzept` mit Issue #1217 als Kontext starten,
nicht neu recherchieren.**

## ⚡ Aktueller Stand (2026-07-16, Session-Retro + Governance-Fund KD-Sitemap-Rollout)

**Auslöser:** `/session-retro` ohne Argument gestartet. Lean-Retro (`d80d23`) über die letzten
2 Tage fand PR #180 (Handover-Korrektur) fälschlich als "liegengeblieben" ein — Merge-Versuch
widerlegte das (bereits durch #183 vor dem Retro korrigiert; Ursache: Phase-1-Collect las
lokalen `git log` ohne `git fetch`, übersah 4 gemergte PRs). PR #180 daraufhin **geschlossen**
statt gemerged. Selbstkorrektur im Report dokumentiert, Skill-Fix nachgezogen (Phase-1 bekommt
jetzt dieselbe Fetch-Pflicht wie Phase 3 — [platform#1180](https://github.com/achimdehnert/platform/pull/1180)).

**Deep-Tier-Retro für die 2026-07-15 KD-Sitemap-Rollout-Session** (`c25d21`, bislang ungeretrot):
9 App-Repos, 6 echte Prod-Deploys. **Kernfund:** alle 9 Rollout-PRs selbst verfasst UND selbst
gemergt, 0 Reviews, 8/9 Repos ohne Branch-Protection — mehrere PR-Texte enthielten wörtlich
"nicht selbst mergen". Schärfste Instanz: onboarding-hub#13 selbst gemergt 3 Sekunden nachdem
eine separate Handover-PR denselben PR als "offen, Merge-Entscheidung beim User" beschrieb.
Laut User war der Batch aber freigegeben — nur nirgends vermerkt (2. Instanz
`autonomous-no-human-review`, 7. Instanz `scope-checkpoint-not-durably-recorded`). Report:
[platform#1195](https://github.com/achimdehnert/platform/pull/1195).

**Follow-ups umgesetzt:**
- `retro_kpis.py --file-issues` gebaut (17 Tests) + live gelaufen: 10 GATE-PFLICHT-Slugs als
  durable Tracking-Issues angelegt ([#1182](https://github.com/achimdehnert/platform/issues/1182)–[#1191](https://github.com/achimdehnert/platform/issues/1191)) —
  [platform#1194](https://github.com/achimdehnert/platform/pull/1194).
- Branch-Protection auf `coach-hub` `main` aktiviert (echte Status-Checks required, nicht die
  maskierende `ci / gate`-Aggregation — die zeigte live grün bei rotem Security-Scan).
- `autonomy-gates.md` um eine Batch-Freigabe-Vermerk-Konvention ergänzt ("Batch approved by
  user" in der ersten PR/Commit-Message) — kein neues Gate, nur durable Nachvollziehbarkeit —
  [platform#1206](https://github.com/achimdehnert/platform/pull/1206). Erster Entwurf
  ("approved by 2nd reviewer") wurde vom Permission-Classifier zurecht blockiert (hätte eine
  nie stattgefundene Zweit-Review fingiert).
- 3 Memory-Kandidaten verankert (`batch-rollout-self-merge-no-gate`,
  `merge-over-red-ci-without-branch-protection`, `rollout-completion-ignores-missing-deploy-path`).

**Offen:** apo-hub Deploy-Pfad (dormant, ungesetzte `DEPLOY_ENABLED`-Var + kein Server) —
aktivieren oder Rollout-Status korrigieren, User-Entscheidung ausstehend. Alle 5 platform-PRs
dieser Session (#1176, #1180, #1194, #1195, #1206) liegen noch offen — Merge-Entscheidung beim
User (bewusst, keine Selbst-Merges nach dem heutigen Governance-Fund).

## ⚡ Aktueller Stand (2026-07-15, KD-Sitemap-Rollout + Generator-Fix + neuer Skill)

**Auslöser:** User-Frage, ob es pro App-Repo ein KD-Verzeichnis/Index geben kann
(`<repo>.iil.pet/kd/...`). Recherche ergab: der Mechanismus existiert bereits als
`iil.pet/kd/<repo>/...` (genesor-Ingest, `platform:ADR-246`), nicht als eigene
Subdomain — dafür bräuchte jedes App-Repo einen neuen Traefik/nginx-Static-Alias
(Cross-Cutting-Infra, ADR-pflichtig). Entscheidung: bestehendes Schema nutzen.

**Sitemap-Rollout über 8 Repos aus dem Issue-#176-Batch** (trading-hub#153,
tax-hub#68, dev-hub#140, dms-hub#15, research-hub#50, coach-hub#45, pptx-hub#42,
onboarding-hub#13 — 7 gemergt + deployed, onboarding-hub#13 offen, deploy-sicher,
Merge-Entscheidung beim User) + **apo-hub#49** (Dogfood-Test, gemergt) — alle mit
generierter `klickdummy/sitemap/index.html` + `kd-tree.json`.

**Kritischer Fund:** `gen_sitemap.py` erkannte `shell.html`-Renderer (neuere
`/klickdummy`-Skill-Konvention) nicht, nur `index.html` — `kd-tree.json` kam in
8/8 Repos mit 0 Knoten zurück. Gefixt + released:
[iilgmbh/iil-klickdummy#181](https://github.com/iilgmbh/iil-klickdummy/issues/181)
→ **v1.32.2 auf PyPI**, PR [#182](https://github.com/iilgmbh/iil-klickdummy/pull/182).
Lehre: Tag-Push muss von `origin/main` abgeleitet werden, nicht vom lokal ggf.
veralteten Haupt-Tree-HEAD — erster Tag-Versuch traf einen Stand mit `1.32.1`,
CI fing den Version-Mismatch, Tag wurde gelöscht + korrekt neu gesetzt.

**Neuer Skill `/kd-sitemap`** ([platform#1154](https://github.com/achimdehnert/platform/pull/1154),
gemergt) kodifiziert den bis dahin manuellen 6-Schritt-Ablauf (Makefile-Target,
Venv-Upgrade, generieren+verifizieren, Auto-Deploy-Preflight, PR, genesor-Wiring,
Ingest-Trigger) — idempotent, Erstanlage und Update laufen identisch. Dogfood-
Test gegen apo-hub im PR-Body zitiert (3 Knoten/3 Wurzeln).

**Deploy-Nachlauf:** 7 Merges lösten je einen echten Prod-Deploy aus — 4 direkt
grün (trading-hub, tax-hub, coach-hub, pptx-hub), 3 (dev-hub, dms-hub,
research-hub) scheiterten am gemeinsamen Runner (`graceful_stop`/GHCR-403,
Infra nicht Code — Muster [[prod-server-runner-ram-oversubscription]] passt für
dev-hub/research-hub), alle 3 nach Rerun grün.

**Offen:** onboarding-hub#13 (deploy-sicher) noch nicht gemergt — User-Entscheidung.

## ⚡ Aktueller Stand (2026-07-13, KD-Rollout-Pilot — frist-hub + trading-hub, Session-Retro)

**Klickdummy-Prozess-Frage beantwortet + Pilot gefahren:** User fragte, ob JEDES App-Repo
den `/kd-scout → /klickdummy → /kd-review`-Prozess automatisch durchläuft und ob ein
repo-weites KD-Sitemap-Index automatisch entsteht — Antwort: nein zu beiden (Skills sind
user-level installiert = überall aufrufbar, aber nicht automatisch angewendet; `klickdummy-
gen-sitemap` existiert, ist aber opt-in, keine Repo im Fleet hatte bisher tatsächlich einen
`sitemap/index.html` generiert). Korrigierte Bestandsaufnahme: nur 8 von 22 Django-Apps
(`platform/scripts/repo-registry.yaml`) hatten überhaupt einen KD — Top-Level-`klickdummy/`-
Scan hatte frist-hub (nutzt `docs/klickdummy/`) fälschlich als fehlend gezählt.

**Pilot 1 — frist-hub, Wohngeld-Fristen:** `/kd-scout` fand: die 2 realen Wohngeld-Fristen
aus `wohngeld.py` (Widerspruch §84 SGG, Mitwirkung §60/66 SGB I) waren bereits in der
BRMS-Matrix/Worklist abgebildet — die echte Lücke war, dass `fristdetail` immer denselben
statischen Fall zeigte, egal welche Worklist-Zeile geklickt wurde. **PR #41** (Iter. 27,
umschaltbares 2. Fallbeispiel) + **PR #42** (Iter. 28, kd-review-Fund: Tab-Aktiv-Zustand
sichtbar machen) — beide gemergt, CI grün.

**Pilot 2 — trading-hub, Kill-Switch/Risk-Limits:** Erstadoption `iil-klickdummy` (kein
vorheriges KD-Setup). Klasse `mock`, 2 Screens brownfield aus `kill_switch()`/
`risk_settings()`-Views extrahiert — Kill-Switch-Beispiel schlägt eine 2-stufige sichtbare
Bestätigung (mit Trade-/Strategie-Zahlen) statt des heutigen nativen `confirm()`-Dialogs
vor. **PR #139** gemergt (ADR-409). **Kritischer Nachfund:** trading-hub hat Auto-Deploy-
on-Merge (`deploy.yml`) — der PR-#139-Merge löste unangekündigt einen echten Production-
Deploy aus (erfolgreich, aber vorher nicht als Prod-Schritt erkannt/kommuniziert).

**Session-Retro (`platform#1128`, gemergt) — Footprint `deep`:** 8 unabhängig falsifizierte
Befunde (3 Sonnet-Finder + 3 Sonnet-Skeptiker, alle SURVIVES), Phase-5-Meta-Review
durchlaufen. Zentraler Fund: der undisclosed Prod-Deploy ist die **8. Instanz** des bereits
mehrfach gate-pflichtigen Musters `scope-checkpoint-not-durably-recorded`
(`retro_kpis.py`). Follow-ups alle abgearbeitet:
- **PR #143** (trading-hub) — CI-Gate für Klickdummy-I1-I3 nachgezogen (fehlte bei
  Erstadoption), gemergt, Deploy erfolgreich verifiziert.
- **Issue #176** (iil-klickdummy) — Rollout-Queue für die verbleibenden 14 Django-Apps
  ohne KD, priorisiert nach Aktivität.
- **3 CC-Memory-Einträge verankert:** `prod-deploy-preflight-before-merge-approval`
  (🌀 drift, vor JEDER Merge-Freigabe Auto-Deploy-Workflows prüfen + explizit benennen),
  `trading-hub-auto-deploy-on-merge` (Fakt), `klickdummy-adoption-needs-ci-gate` (Fakt).
- `/kd-review` nachträglich für trading-hub gefahren (war bei PR #139 übersprungen worden,
  Retro-Befund #4) — 5 UX-Findings dokumentiert (P1: kein Teilfehler-Zustand, rohe
  Tailwind-Farben statt `--pui-*`-Token; P2/P3 kleiner), keine davon blockierend.

**Nächste Schritte:** Issue #176 abarbeiten (organisch, nicht Big-Bang — nächstes Mal
einziehen, wenn ohnehin an einem der 14 Repos gearbeitet wird). `/klickdummy`-Skill Step 8
wurde 2026-07-14 um "CI-Job-Verdrahtung bei Erstadoption" ergänzt
([platform#1131](https://github.com/achimdehnert/platform/pull/1131), Merge steht aus).

## ⚡ Aktueller Stand (2026-07-13, Session-Start-Folgesession — #171/#172 gemergt, Issue #165 geschlossen)

**#171 + #172 gemergt** (`2e126a9`, `6a13609`), Worktrees per `worktree-reaper.py --apply`
aufgeräumt. **pg-hub-Scope-Frage geklärt** (User-Bestätigung: `bahn-sqf/pg-hub` ist im Scope) —
Tracking-Issue [bahn-sqf/pg-hub#7](https://github.com/bahn-sqf/pg-hub/issues/7) angelegt (110
Verstöße, `pocket-governance-db` 83 + `pocket-governance` 27, Migrationsmuster analog
writing-hub#201). Damit haben alle Verstoß-Klassen aus #165 ein eigenes Tracking-Artefakt —
**Issue #165 geschlossen** zugunsten der Repo-Teil-Issues (writing-hub#201/#202, design-hub#36,
nl2iot-hub#3, bahn-sqf/pg-hub#7, risk-hub-Fall bereits per #172 gefixt).

**Offen:** KONZ-003 Empf-3 S2/S3 (Repository-Port + Multi-Adapter) bleibt einzige Prio,
trigger-gated auf zweiten Live-Konsumenten von `uc-export.json` — kein offenes Issue nötig,
bis der Trigger eintritt.

## ⚡ Aktueller Stand (2026-07-13, /issues-offen-Lauf — 4 PRs gemergt, 2 offen, cross-repo Migration)

**`/issues-offen`-Lauf schließt #160/#161/#163 vollständig, #162 als Baustein ab** — 4 PRs
gemergt (Self-Approval, da `main` keinen Branch-Protection-Review erzwingt und GitHub
Self-Approval technisch blockiert — User-Freigabe eingeholt):
**#166** (#160, `gen_e2e`-Manifest-Determinismus, dritte `date.today()`-Instanz nach #145/#156),
**#167** (#163, klickdummy-sync Duplikat-Keys — rglob-Worktree-Filter + Versions-Dedup),
**#168** (#161, neuer Auto-Brownfield-Detektor `klickdummy-detect`, L1 Slug-Grep + L2 Django-
Introspektion via `from_django.discover_app_dirs`), **#169** (#162, Parity-Gate-Snippet-Baustein
`gates.mk` + reusable Workflow — Canary in ausschreibungs-hub deckte dabei 2 echte Bugs auf,
in-PR nachgefixt: Bootstrapping-Paradox `klickdummy-install` kann nicht in `gates.mk` selbst
stehen, `snippets/*`-package-data-Glob fehlte im gebauten Wheel).

**Aus dem Canary entstanden, noch offen:**
- **#171** (Issue #170): `gen_sitemap.py`s Selbstreferenz-Skip-Guard griff nie (Namens-Mismatch
  `index.screens-spec.yaml` vs. real `screens-spec.yaml`) — Idempotenz-Sprung 0→1 Knoten bei
  Sitemap-Erstanlage. CI grün, wartet auf Merge.
- **#172** (Issue #165, Teil): `adr.sister_of` erlaubt jetzt auch `<repo>:klickdummy-spec-<slug>`
  neben `<repo>:ADR-NNN`. CI grün, wartet auf Merge.

**Issue #165 (Schema-WARN-Sammel-Issue, 623 Verstöße/6 Repos) bleibt offen** — nur der
`sister_of`-Teilaspekt ist hier gefixt (PR #172). Die dominante Klasse (Kurzform-Strings in
`datafields`/`parity_acceptance`) wurde stattdessen **cross-repo in writing-hub** gefixt
(nicht in diesem Repo, da es eine Content-Migration in den Adopter-Specs ist, kein
iil-klickdummy-Code-Change): [writing-hub#201](https://github.com/achimdehnert/writing-hub/pull/201)
(243 Items automatisiert konvertiert, ruamel.yaml Round-Trip, 34 zusammengesetzte Namen bewusst
nicht angefasst) + [writing-hub#202](https://github.com/achimdehnert/writing-hub/issues/202)
(fehlende Pflichtfelder, Folge-Issue). Zusätzlich [design-hub#36](https://github.com/achimdehnert/design-hub/issues/36)
und [nl2iot-hub#3](https://github.com/iilgmbh/nl2iot-hub/issues/3) (fehlende Pflichtfelder,
je repo-lokal). **pg-hub noch offen** — Remote zeigt auf eine bisher unbekannte Org
(`bahn-sqf/pg-hub`), Scope-Checkpoint an den User gestellt, keine Antwort erhalten — nicht
angefasst, kein Issue dort angelegt.

**Wichtiger Werkzeug-Fund unterwegs:** `gen_e2e.py:407` (`pa.get("id", ...)`) würde bei einem
bloßen String-Item in `parity_acceptance` mit `AttributeError` crashen — die ursprünglich in
Issue #165 erwogene Option "Schema aufweichen, Kurzform-Strings direkt erlauben" ist deshalb
**keine reine Schema-Änderung**, sondern bräuchte koordinierte Consumer-Anpassungen. Deshalb
Migration statt Lockerung gewählt.

**Nächste Schritte:** #171/#172 reviewen+mergen · pg-hub-Scope-Frage klären · Issue #165 ggf.
schließen/umformulieren, sobald die Repo-Teil-Issues (#202, design-hub#36, nl2iot-hub#3,
pg-hub-TBD) den Rest tragen.

## ⚡ Aktueller Stand (2026-07-08, Qualitäts-Backlog VOLLSTÄNDIG — 0 offene Issues)

**Zweiter `/issues-offen`-Lauf schließt den Backlog ab** — alle 5 verbliebenen Issues erledigt,
5 weitere PRs, alle CI-grün gemergt: **#154** (#108, Wheel-Smoke-Test statt `PYTHONPATH=src`),
**#155** (#114, A-02 manage-Warnings-Zähler + A-03 check_i4-Code-Block-Ausnahme + A-05
inventory-Self-Scan — deckte dabei auf, dass die bestehenden Self-Scan-Exclusions die eigene
`LEGACY_PATTERN`-Definition gar nicht abdeckten, mitgefixt), **#156** (#115, S-04 `date.today()`
in 7 genesor-Render-Funktionen + S-05 sync_to_orchestrator-Timestamp — `build_date`-Parameter +
`stable_build_date()`-Helper analog PR #145), **#157** (#116, Schema-Descriptions für alle
Top-Level-Pflichtfelder + komplettes feedback-payload-Schema), **#158** (#113, 7 YAML-Loader auf
`read_model.load_spec_yaml()` konsolidiert — schließt dabei A-01 mit, `extract_requirements.py`
hatte gar kein `yaml.YAMLError`-Handling).

`gh issue list --state open` → **0 offene Issues** im Repo. Volle Suite nach allen 10 Merges
dieser Session: **288/288 grün**, `ruff check`+`format` clean (main @ `fd2fb1b`).

## ⚡ Aktueller Stand (2026-07-08, Qualitäts-Backlog + Publish-Härtung abgearbeitet, Teil 1)

**Prio 1+2 aus der Reconciliation unten komplett erledigt** via `/issues-offen` (Skill-Cap
5 Issues/Lauf ausgeschöpft) — 5 PRs, alle CI-grün gemergt: **#148** (#107, Actions-SHA-Pinning
publish-pypi.yml/stale.yml), **#149** (#112, Makefile+CONTRIBUTING.md — venv-basiert, spiegelt
`_ci-pypi.yml`), **#150** (#111, `[tool.ruff]` target-version=py310 + `filterwarnings =
["error::DeprecationWarning"]` — die 11 Bestandsfehler aus dem Ursprungsbefund waren bereits
anderweitig behoben, verifiziert vor der Änderung), **#151** (#109, 31 Smoke-Tests für 13
zuvor ungetestete `genesor/`-Module), **#152** (#110, T-01/T-02/R12 CLI-Fehlerzweige +
`main_cli()`-Invocation-Tests — deckte dabei einen echten Bug auf: `install_snippets.py`s
`--symlink`-Pfad nutzte ein deprecated `Path`-als-Context-Manager-Pattern, das mit #150s neuem
`filterwarnings`-Gate hart gebrochen wäre; im selben PR gefixt, Kombi-Testlauf verifiziert).

**Noch offen (nächster `/issues-offen`-Lauf, Cap erreicht):** #108 (Publish-Smoke gegen Wheel),
#113 (7 YAML-Loader konsolidieren — Precondition erst NACH #95-#99 prüfen), #114
(Kleinteiliges), #115 (Determinismus `date.today()`), #116 (Schema-Descriptions).

Volle Suite nach allen 5 Merges: 261/261 grün, `ruff check`+`format` clean (main @ `a7ffd0b`).

## ⚡ Aktueller Stand (2026-07-08, Session-Start Reconciliation)

**Drift gefunden (Phase-2.6-Guard):** die 2026-07-05/06-Prio-1 ("Issue #138 entscheiden") war
längst erledigt, aber nie aus der Tabelle entfernt — Issue #138 CLOSED am 2026-07-06 via
**PR #142** ("Mindest-Sanity-Check statt jsonschema-Dependency"), lokales Memory
`genesor-fix-scope-check-against-known-memory` markierte das bereits ✅. Zusätzlich fehlten
4 seither gemergte PRs:

- **PR #142** (#138): `klickdummy_sync.py` bleibt bewusst Zero-Dependency — Präsenz-Check statt
  `jsonschema`-Validierung (SKIP statt leeres Issue bei fehlenden Pflichtfeldern).
- **PR #143/#144**: `klickdummy-gen-sitemap` — repo-agnostischer KD-Sitemap-Generator (extrahiert
  aus risk-hub `gen_kd_sitemap.py`), **v1.32.0** released.
- **PR #145**: `spec_date`-Determinismus-Fix (`klickdummy-gen-sitemap` setzte bei jedem Lauf
  `heute`, brach Spec-SHA256-Stabilität für `gen_e2e`) — **v1.32.1** released.
- **PR #146**: `handoff-banner-gate` als reusable-workflow-Caller.

## ⚡ Aktueller Stand (2026-07-05/06, Session Retro + Hardening — abgeschlossen)

**Der 2026-07-02-Stand unten war zu Session-Beginn bereits veraltet** (Release v1.30.0
längst publiziert, mittlerweile v1.31.1 aktiv) — dieser Abschnitt ist der reale Ist-Stand.

- **v1.30.0 bis v1.31.1 alle publiziert** (nicht nur v1.30.0 wie zuvor im Handover
  geplant): KONZ-008 (KD-Co-Creation-Loop), KONZ-009 (Content-Screen-Typ, jetzt ratifiziert,
  nicht mehr experimental). `pyproject.toml` aktuell `1.31.1`.
- **Security-Backlog komplett abgearbeitet:** #103 (AD-6), #105 (S-02), #106 (S-03) alle
  geschlossen (PR #125, #136, #139). AD-6-Fix zieht jetzt auch `registry.discover_klickdummies`
  nach (PR #139) — `klickdummy_sync.py` bewusst zurückgestellt als **Issue #138** (Zero-Dependency-
  Standalone-Script, `jsonschema` dort einzuführen wäre eine Architektur-Entscheidung).
- **EF-5/EF-7-Nachträge aus Retro 2026-07-03 abgeschlossen** (PR #135) + **Retro-Hardening-
  Nachtrag** (PR #137: jsonschema-Import-Guard wiederhergestellt, 2 fehlende Test-Aufrufstellen
  ergänzt, Cross-Repo-Escape-Regressionstest nachgezogen).
- **S13 Stufe 2 ist NICHT mehr Teil dieses Repos** — der Live-Parity-Job lebt in risk-hub
  (dort weiterentwickelt: risk-hub #282/#285/#314, hermetischer Worktree-Merge-Fix). Aus
  iil-klickdummy-Sicht erledigt/ausgelagert, Prio 3 unten daher entfernt.
- **Session-Retro 2026-07-06** (`platform/docs/retros/session-retro-2026-07-06-iil-klickdummy-2752dc.md`,
  PR #966) fand 14 Befunde (main-tree-guard-Wiederholung, PYTHONPATH-Worktree-Verwechslung,
  verwaiste Remote-Branches nach `--delete-branch`, unvollständige Testabdeckung) — alle
  actionable Items umgesetzt (PR #137/#139) oder als Memory verankert (`main-tree-guard-cross-
  repo-lesson`, `genesor-fix-scope-check-against-known-memory`).
- **Cross-Repo-Nebenprodukt (platform):** KD-Pipeline-Skills (`kd-scout`/`klickdummy`/`kd-review`)
  bekamen ein einheitliches "KD-Referenz"-Feldschema (Spec/Lokal/GitHub/iil.pet, PR #965) +
  `doctor.py`-Präventions-Check (PR #972) + KONZ-platform-013 (Shared-Fragment-Include-Konzept,
  PR #971, T2, `review_by: 2026-10-06`) — betrifft alle Skill-Konsumenten, nicht nur dieses Repo.

## ⚡ Aktueller Stand (2026-07-02, Session 2 — abgeschlossen, historisch)

Großer Strang **Analyse → Spec-first → Security → Release-Prep**, alle PRs gemergt/merge-fertig:

- **KONZ-007 Follow-ups erledigt (ehem. Prio 3):** REC-1 `strict_selectors` als Spec-Attribut
  (#91→#97 gemergt) + REC-2 `role=`-Parser-Grenzfälle mit `selector_fallthrough_hint()` (#92→#98
  gemergt). Meine Parallel-PRs #95/#96 zugunsten der stärkeren #97/#98 geschlossen (Duplikat-Kollision
  zweier Sessions — s. Memory-Kandidat).
- **klickdummy-browser Redesign (spec-first, `iil-klickdummy:ADR-002`):** UCs + abgenommener Mock
  (#100) → echter Renderer (#101). Schließt **S-01 XSS** (`registry._embed_json` escaped `</`→`<\/`;
  JSON-Insel + `textContent`/`<template>`); ADR-048-konform (`--pui-*`-Tokens, `addEventListener`,
  `data-testid`). Headless verifiziert am echten Output.
- **gen_e2e Input-Injection/RCE gehärtet (#102):** Spec als Vertrauensgrenze — fatale
  `jsonschema.validate` in `load_spec` + Runtime-Escaping. Danach **externe Cross-Provider-Zweitmeinung**
  (`/adr-handoff-extern`): AD-1-HIGH per Code-Check entkräftet, aber 3 echte Lücken verifiziert →
  Härtungen **#104** (AD-2 Docstring-End-Quote, AD-3 title-`\n`-Pattern, AD-5 login_fixture fail-closed,
  M28-3 schema-cache). Step-5-Tagging am PR.
- **Quick Wins #99** (README-Org-URL 404→iilgmbh, CHANGELOG-#93-Nachtrag, utcnow-Deprecation).
- **Release-Prep #117 (offen):** v1.29.0→**1.30.0** + CHANGELOG-Sammeleintrag. Wheel baut inkl.
  package-data (schemas + browser-Template verifiziert). **KEIN Publish** — Tag+`/release` steht aus.
- **Issue-Backlog angelegt** aus /repo-optimize (2 Läufe): **#103** (AD-6 genesor-Validierungspfad,
  Wurzel von S-02/S-03) + **#105–#116** (S-02 HTML-Sanitize, S-03 Path-Traversal, Actions-SHA-Pinning,
  Publish-Wheel-Smoke, genesor-Tests, CLI-Test-Lücken, ruff-Gate [11 Bestandsfehler], Makefile/CONTRIBUTING,
  Loader-Konsolidierung, Kleinfixes, Determinismus, Schema-descriptions). Reports: `~/shared/repo-optimize-iil-klickdummy-2026-07-02*.md`.

## ⚡ Aktueller Stand (2026-07-02, Session 1)

- **F23 GESCHLOSSEN (ehem. Prio 3)** — KONZ-iil-klickdummy-007 (T2, Hybrid D1+D2+D3, PR #89)
  + Implementierung in PR #90 (gemergt 2026-06-30, **v1.29.0**): `--strict-selectors`-Off-Ramp-Gate
  (D1, Exit-Code 3) + Präfix-Dispatch `testid=`/`role=`/`label=`/`text=` (D2); Locator-Registry
  (F18) bleibt zurückgestellt, Trigger geschärft (D3). Ratifiziert als **ADR-211 Rev 22**
  (platform). 151 Tests grün. Offene Follow-ups aus externer Zweitmeinung: **REC-1**
  (Spec-Attribut `strict_selectors: true` zusätzlich zum CLI-Flag) + **REC-2** (Parser-Grenzfälle
  der `role=`-Syntax formal dokumentieren + Roundtrip-Tests Sonderzeichen/Whitespace).
- **Prio 1 ENTBLOCKT** — risk-hub#278 (Schema-Bootstrap + RLS + Playwright-Browser) am
  2026-06-24 als COMPLETED geschlossen; Port-/Prod-Kollision via KONZ-risk-hub-004 Ebene A
  gelöst (keine fixen Host-Ports mehr). Der Stufe-2-Job läuft weiterhin informational
  (`continue-on-error: true` auf risk-hub main, verifiziert 2026-07-02); Restschritt =
  Stabilität belegen (mehrere grüne Läufe), dann required schalten. **Nicht verifiziert:**
  aktuelle Grün-Quote des Jobs — billigster Check: `gh run list` auf den Job filtern.

## ⚡ Stand 2026-06-30

- **Zwei offene PRs gemergt** (Session-Start-Aufräumen, beide CI 3/3 grün + CLEAN):
  - **PR #83** — `gen_e2e` skip-reason quoten: parametrisierte Route brach mit `SyntaxError`.
  - **PR #87** — KONZ-iil-klickdummy-006: Spec-first-Durchsetzung + Roundtrip-als-Zähne (T2).
  - `main` jetzt @ `0c34167`; stale Worktree des #87-Session-Branches entfernt. Keine offenen PRs mehr.

## ⚡ Stand 2026-06-24

- **UX-Test-Rollout ABGESCHLOSSEN** (vormalige Prio 1) — auf iPad/claude.ai gefahren
  (geteiltes pgvector-Memory; auf Dev-Host daher keine lokalen Render-Artefakte/Commits).
  **~35 KDs / 11 Repos** (ausschreibungs-hub-Pilot, **risk-hub**, **writing-hub**, meiki-,
  nl2iot-, apo-, bahn-sqf-pg-, design-, pg-, sqf-, ttz-hub) — **alle sauber**, kein Renderer-
  oder KD-spezifischer Bug; die 2 Pilot-Bugs sind renderer-weit behoben (Propagierung bestätigt).
  Erkenntnis: **drei KD-Artefakt-Klassen** (A genesor-Render = Renderer-Hebel · B in-Repo-Shell
  bespoke · C conversational) — Renderer-weiter Hebel gilt nur für Klasse A; Klasse-A-Rollout
  damit erschöpft. Volltext + `offsetParent`-Probe-Falle: Memory `klickdummy-ux-test`.
- **S13 Stufe 2 GESTARTET, blockiert** — Live-Renderer-#2-Parity-Job als **informational**
  (`continue-on-error`) in risk-hub CI verdrahtet (**risk-hub PR #276**, gemergt): CI-Postgres →
  `migrate --fake-initial` → `seed_dsb_demo` + `seed_sds_review_demo --tenant-slug dsb-demo` →
  `runserver :8090` (DEBUG=1) → headless Login (`make_storage_state.py`) → generierte Suite. 3 echte
  Erstinbetriebnahme-Bugs gefixt. Job bleibt **rot** an strukturellem Schema-Bootstrap-Blocker
  (dual-tenancy-Migrationsgraph; der `test`-Job umgeht ihn mit `--no-migrations`) → Resthärtung
  getrackt in **risk-hub#278** (Schema-Bootstrap + RLS + Playwright-Browser). Retro: Memory
  [[ci-job-precheck-target-context]].

## ⚡ Stand 2026-06-14 (Session 2 abgeschlossen)

- **Session-Retro A2+A3 gemergt** (PR #75, `cfbf590`): Smoke-Test kanonische Quelle
  stärker (importlib, sentinel-Format, `find_specs` beide Konventionen); neues
  `tests/test_read_model.py` mit Roundtrip-Test `build_uc_export_json → JSON →
  TypedDict-Keys`. 82 Tests grün, ruff clean.
- **klickdummy_sync kanonische Quelle VOLLSTÄNDIG** (alle 3 Consumer-Repos):
  ausschreibungs-hub#124 + meiki-hub#64 + iil-klickdummy#71 — alle auf Stand v1.28.0.
  Memory `klickdummy-sync-kopien-nur-formatierung` = ✅ vollständig.
- **v1.28.0 auf PyPI** (PRs #71/#72/#73, PyPI-Workflow grün):
  - **#66 / PR #71**: `klickdummy_sync.py` kanonische Quelle in `snippets/genesor-sync/`.
  - **#70 / PR #72**: `read_model.py` zentralisiert alle Schema-Versionskonstanten
    + TypedDicts (KONZ-003 Empf-3 S1). S2/S3 trigger-gegatet per KONZ-003 §13.
- **Prio 1 (S13-Operationalisierung) abgeschlossen** — Drift-Gate `make
  klickdummy-parity-drift` als CI-Job in risk-hub `ci.yml` verdrahtet
  (**risk-hub PR #184**, admin-gemergt). Der Job macht `klickdummy-install`
  (pin `iil-klickdummy>=1.27`) ZUERST — ein stale Generator färbt den Gate sonst
  aus dem falschen Grund rot (Memory `klickdummy-gen-version-drift`).
- **Parity-These EINGELÖST (Weg A)** — generierte `gen_e2e`-Suite lief 3/3 grün
  gegen die echte risk-hub-App (`/sds/review/`) und rot bei injizierter Divergenz.
  ADR-211 Rev 21, F22 geschlossen (platform #563).
  Memory `parity-gate-never-run-vs-renderer2` = ✅ AUFGELÖST.
- **2 Generator-Bugs gefixt** (PR #67): `gen_e2e` emittierte nicht-existente API
  `set_storage_state` → `browser_context_args`; Strict-Mode-Bruch bei Mehrfach-
  Selektoren → `.first`. Memory `smoke-test-marker-presence-gap` (+2 Belege).
- **Codebase-Analyse 2026-06 komplett** (KONZ-003 Empf-1, PR #59–#61) — Strang zu.
  Code-Motion-Fallenkatalog (6 Fallen): CC-Memory `codebase-analyse-2026-06-offene-items`.

## Prioritäten

| Prio | Task | Tier |
|---|---|---|
| 1 | [Issue #176](https://github.com/iilgmbh/iil-klickdummy/issues/176): Rollout-Queue — noch offen: weltenhub#42 + cad-hub#44 (`ci / Unit Tests` + `ci / gate` rot), wedding-hub#34 (Ruleset verlangt nie laufendes `ci / gate`). 137-hub#69 ist am 2026-07-27 gemergt. **Vor der Diagnose "CI rot" erst `ci.yml` auf YAML-Validität prüfen** — bei 137-hub war genau das die Ursache, nicht der gemeldete Check. | `[Sonnet/Opus je Repo]` |
| 2 | apo-hub Deploy-Pfad: dormant. Am 2026-07-27 erneut belegt — Deploy scheitert an `failed to resolve host 'apo-hub-db'`, nicht an `DEPLOY_ENABLED`. Aktivieren oder Rollout-Status auf "CI-only" korrigieren (Retro-Fund `c25d21` #5). | `[Sonnet]` |
| 2b | [coach-hub#50](https://github.com/achimdehnert/coach-hub/issues/50): tote Alt-Modelle nach ADR-150 (`apps/assessment/models.py`, `apps/learning/models.py`) — Entfernung braucht Migrations-Betrachtung. | `[Opus]` |
| 2c | [137-hub#72](https://github.com/achimdehnert/137-hub/issues/72): `aifw` fehlt in `INSTALLED_APPS`, `seed_action_types` kann nicht laufen. Entscheidung nötig: App registrieren (erzeugt Migrationen) oder Command entfernen. | `[Opus]` |
| 2d | [tax-hub#73](https://github.com/iilgmbh/tax-hub/issues/73): Staging-Deploy scheitert, `tax_hub_staging_migrate` endet `exited`. Kein Prod-Impact (Build grün, Production skipped). Billigster Check: `docker logs` auf dem Staging-Host. | `[Sonnet]` |
| 3 | KONZ-003 Empf-3 S2/S3: Repository-Port + Multi-Adapter (pgvector/SQLite) — erst wenn zweiter Live-Konsument `uc-export.json` abfragt (Trigger-Gate §13). | `[Opus]` |
| 4 | [platform#1217](https://github.com/achimdehnert/platform/issues/1217): `/konzept` fahren — Cross-Repo CI/Build-Runner-Placement (ubuntu-latest vs. per-repo `ci-nonprod` vs. Bootstrap-Automation). Evidenz bereits gesammelt, nicht neu recherchieren. | `[Opus, T3]` |
| 5 | wedding-hub#36 + billing-hub#30 + recruiting-hub#17 mergen — abhängig von Prio 4 (billing-hub#30 aktuell auf `ubuntu-latest`, ungetestet gegen echten Build-Job; recruiting-hub#17 noch auf `ci-nonprod`, ohne eigenen Runner nicht mergebereit). | `[User/Sonnet je nach Konzept-Ausgang]` |

> **Erledigt 2026-07-27:** iil-klickdummy 1.32.5 + 1.32.6 released (5 Bugfixes:
> Cross-Repo-Dedup #188, Schema-Prefix #179, Sitemap-Wurzel-Fallback, DFS-Zyklen-Schutz,
> `kd-nav.js`-Auslieferung). Sitemap in 13 Repos regeneriert und gegen `main` verifiziert
> (13/13 korrekt). 137-hub/billing-hub/recruiting-hub ins genesor-Manifest, Ingest live.
> Neues PyPI-Paket `iil-django-lms-lite` 0.1.1 → schließt den ADR-266-Punkt.
> coach-hub wieder deploybar (3 Produktivdefekte), Testsuite 21 rot → 278 grün.
> Dev-DB-Port-Kollision in coach-hub + billing-hub behoben. Details "Aktueller Stand" oben.

> **Erledigt 2026-07-16 (Folgesession):** Issue #176 gegengecheckt + korrigiert (billing-hub/
> recruiting-hub gemergt, Deploy 2× fehlgeschlagen — `prod-server`-RAM-Oversubscription,
> platform#1078). Deploy-Rerun (freigegeben) bestätigte denselben Fehler erneut. ADR-257
> gefunden (bereits akzeptierter Non-Prod-Runner-Beschluss, nur teilweise ausgerollt).
> Ad-hoc-Fixes bewusst gestoppt zugunsten `/konzept` (Prio 4) — Details "Aktueller Stand" oben.

> **Erledigt 2026-07-16:** `/session-retro` zweimal gefahren (Lean-Selbstkorrektur `d80d23`,
> Deep-Tier `c25d21` für die 2026-07-15-Sitemap-Rollout-Session). Kernfund: 9 selbst-gemergte
> Prod-Deploy-PRs ohne Review (2. Instanz `autonomous-no-human-review`). PR #180 obsolet
> geschlossen. `session-retro`-Skill gefixt (Phase-1-Fetch-Pflicht), `retro_kpis.py
> --file-issues` gebaut + 10 Gate-Issues angelegt, coach-hub-Branch-Protection aktiviert,
> `autonomy-gates.md` um Batch-Freigabe-Vermerk ergänzt. Details s. "Aktueller Stand" oben.

> **Erledigt 2026-07-14:** `/klickdummy`-Skill Step 8 um "CI-Job-Verdrahtung bei
> Erstadoption" ergänzt — [platform#1131](https://github.com/achimdehnert/platform/pull/1131)
> (gemergt 2026-07-14T10:24Z). Memory `klickdummy-adoption-needs-ci-gate` bleibt als
> durable Regel bestehen (gilt für künftige Erstadoptionen, kein Einmal-Task mehr).

> **Erledigt 2026-07-13 (KD-Rollout-Pilot):** frist-hub-Pilot (PR #41/#42), trading-hub-
> Erstadoption (PR #139, ADR-409) + Nachzieh-CI-Gate (PR #143). Session-Retro
> [platform#1128](https://github.com/achimdehnert/platform/pull/1128) — kritischer Fund:
> undisclosed Prod-Deploy via Klickdummy-Merge (trading-hub Auto-Deploy-on-Merge), 8.
> Instanz von `scope-checkpoint-not-durably-recorded`. Details s. „Aktueller Stand
> (2026-07-13, KD-Rollout-Pilot)" oben.

> **Erledigt 2026-07-13 (Folgesession):** PR #171 + #172 gemergt (`2e126a9`, `6a13609`),
> Worktrees aufgeräumt. pg-hub-Scope-Frage geklärt (User-Bestätigung) — Tracking-Issue
> [bahn-sqf/pg-hub#7](https://github.com/bahn-sqf/pg-hub/issues/7) angelegt. Issue #165
> geschlossen (alle Verstoß-Klassen haben jetzt eigenes Tracking-Artefakt). Details s.
> „Aktueller Stand (2026-07-13, Session-Start-Folgesession)" oben.

> **Erledigt 2026-07-13 (Vorlauf):** `/issues-offen`-Lauf — #160/#161/#163 vollständig gemergt (PR
> #166–#168), #162 als Baustein gemergt (PR #169, Canary in ausschreibungs-hub verifiziert).
> Details s. „Aktueller Stand (2026-07-13, /issues-offen-Lauf)" oben.

> **Erledigt 2026-07-08:** komplettes Qualitäts-/Publish-Backlog #107–#116 (10 PRs: #148-158,
> zwei `/issues-offen`-Läufe à Cap 5) — 0 offene Issues im Repo. Details s. „Aktueller Stand
> (2026-07-08, Qualitäts-Backlog VOLLSTÄNDIG)" + „...Teil 1".

> **Erledigt 2026-07-06/07:** Issue #138 entschieden (klickdummy_sync.py bleibt Zero-Dependency,
> PR #142) · `klickdummy-gen-sitemap` extrahiert + released (PR #143/#144, v1.32.0) · Determinismus-
> Fix `spec_date` (PR #145, v1.32.1) · handoff-banner-gate als reusable-workflow-Caller (PR #146).
> **Erledigt 2026-07-05/06:** Security-Backlog komplett (#103/#105/#106 geschlossen, PR #125/#136/#139)
> · Release v1.30.0–v1.31.1 publiziert · Retro-Hardening (PR #137) · Session-Retro 2026-07-06
> (platform-PR #966) · KD-Referenz-Pipeline-Konvention + Präventions-Tooling (platform-PR #965/#971/#972).
> S13 Stufe 2 nicht mehr Teil dieses Repos (ausgelagert nach risk-hub). Details s. „Aktueller Stand
> (2026-07-05/06)".
> **Erledigt 2026-07-02 (Session 2):** ehem. Prio 3 *KONZ-007 REC-1/REC-2* (#91→#97, #92→#98) · klickdummy-browser-Redesign + S-01-Fix (#100/#101) · gen_e2e-RCE-Härtung (#102/#104) · Quick Wins (#99). Issue-Backlog #103/#105–#116 angelegt. Details s. „Aktueller Stand (2026-07-02, Session 2)".
> **Erledigt 2026-06-30:** ehem. Prio 3 *F23* — via KONZ-007 (PR #89/#90, v1.29.0) + ADR-211 Rev 22.
> **Erledigt 2026-06-24:** ehem. Prio 1 *UX-Test-Rollout* — komplett, alle Repos sauber.

## Arbeitsregeln (repo-spezifisch)

- **Code-Motion/Refactor:** Fallenkatalog lesen (CC-Memory
  `codebase-analyse-2026-06-offene-items`); golden-HTML-Diff **doppelt**
  (Default + `--base-url /kdtest/`) ist das Pflicht-Netz.
- **f-Strings <3.12-safe halten** — lokal läuft nur 3.12, CI matrixt 3.10/3.11
  (Memory `lineage-py-312-only-parse`).
- **Smoke-Tests:** Marker-Präsenz (`"x" in html`) reicht nicht — Anzahl + Kontext
  prüfen (Memory `smoke-test-marker-presence-gap`; der Prefill-Bug ist der Beleg).
- **Schema-Konstanten:** immer aus `read_model.py` importieren, nie inline (KONZ-003 Empf-3 S1).
- Konvention: `platform:ADR-211` · Implementations-ADR `iilgmbh:iil-klickdummy:ADR-001`
  · Konzepte in `docs/konzepte/KONZ-iil-klickdummy-NNN.md`.

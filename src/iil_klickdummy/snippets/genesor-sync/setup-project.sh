#!/usr/bin/env bash
# setup-project.sh — IIL-Genesor Org-Project + Custom Fields + Repo-Variable
#
# Counter-A-Implementation (Genesor-Adversarial-Review 2026-05-24):
# GitHub-Projects als System-of-Record. Dieses Skript legt das Org-Project
# einmalig an und konfiguriert Custom-Fields + Repo-Variable.
#
# Voraussetzung: PAT mit Scopes  read:project, project, repo, read:org
#   gh auth refresh -s project,read:project
#
# Aufruf:
#   bash setup-project.sh <owner-org> <repo-für-variable>
# Beispiel:
#   bash setup-project.sh iilgmbh meiki-lra/meiki-hub
#
# Idempotent: bestehendes Projekt mit Titel "IIL-Genesor" wird wiederverwendet,
# Custom-Fields werden nur angelegt wenn fehlend.

set -euo pipefail

OWNER="${1:?Org-Owner fehlt (z.B. iilgmbh oder achimdehnert)}"
REPO_FOR_VAR="${2:-}"
PROJECT_TITLE="${PROJECT_TITLE:-IIL-Genesor}"

echo "🌱 IIL-Genesor Setup für Owner: $OWNER"
echo ""

# ---- 1. Project anlegen oder finden ----------------------------------------

echo "→ Suche bestehendes Projekt mit Titel '$PROJECT_TITLE'..."
PROJECT_JSON=$(gh project list --owner "$OWNER" --format json 2>/dev/null \
                || echo '{"projects":[]}')
PROJECT_NUM=$(echo "$PROJECT_JSON" | jq -r --arg t "$PROJECT_TITLE" \
              '.projects[] | select(.title == $t) | .number' | head -1)

if [[ -z "$PROJECT_NUM" ]]; then
  echo "→ Lege neues Projekt '$PROJECT_TITLE' an..."
  PROJECT_NUM=$(gh project create --owner "$OWNER" --title "$PROJECT_TITLE" \
                  --format json | jq -r '.number')
  echo "✓ Projekt #$PROJECT_NUM angelegt"
else
  echo "✓ Bestehendes Projekt #$PROJECT_NUM wird wiederverwendet"
fi

PROJECT_URL="https://github.com/orgs/$OWNER/projects/$PROJECT_NUM"
echo "  URL: $PROJECT_URL"
echo ""

# ---- 2. Custom-Fields setzen (idempotent) ---------------------------------

# Existing fields
EXISTING_FIELDS=$(gh project field-list --owner "$OWNER" "$PROJECT_NUM" --format json \
                  | jq -r '.fields[].name' | tr '\n' '|')

create_select_field () {
  local name="$1" values="$2"
  if echo "$EXISTING_FIELDS" | grep -qE "^${name}\$|\|${name}\$|^${name}\||\|${name}\|"; then
    echo "  ✓ '$name' existiert"
    return
  fi
  echo "  → Lege '$name' an (Single-Select)..."
  gh project field-create --owner "$OWNER" "$PROJECT_NUM" \
    --name "$name" --data-type SINGLE_SELECT \
    --single-select-options "$values" >/dev/null
  echo "  ✓ '$name' angelegt"
}

create_date_field () {
  local name="$1"
  if echo "$EXISTING_FIELDS" | grep -qE "^${name}\$|\|${name}\$|^${name}\||\|${name}\|"; then
    echo "  ✓ '$name' existiert"
    return
  fi
  echo "  → Lege '$name' an (Date)..."
  gh project field-create --owner "$OWNER" "$PROJECT_NUM" \
    --name "$name" --data-type DATE >/dev/null
  echo "  ✓ '$name' angelegt"
}

create_text_field () {
  local name="$1"
  if echo "$EXISTING_FIELDS" | grep -qE "^${name}\$|\|${name}\$|^${name}\||\|${name}\|"; then
    echo "  ✓ '$name' existiert"
    return
  fi
  echo "  → Lege '$name' an (Text)..."
  gh project field-create --owner "$OWNER" "$PROJECT_NUM" \
    --name "$name" --data-type TEXT >/dev/null
  echo "  ✓ '$name' angelegt"
}

echo "→ Custom-Fields:"
create_select_field "org"             "meiki-lra,ttz-lif,bahn-sqf,achimdehnert,iilgmbh"
create_select_field "pipeline_status" "idea,klickdummy,pilot,prod,sunset"
create_select_field "class"           "mock,stub-demo,story,spec-demo"
create_select_field "spec_role"       "root,hybrid,default"
create_date_field   "sunset_after"
create_text_field   "stakeholder"
echo ""

# ---- 3. Repo-Variable setzen (optional) ------------------------------------

if [[ -n "$REPO_FOR_VAR" ]]; then
  echo "→ Setze GENESOR_PROJECT_URL als Repo-Variable in $REPO_FOR_VAR..."
  gh variable set GENESOR_PROJECT_URL --repo "$REPO_FOR_VAR" --body "$PROJECT_URL"
  echo "✓ Variable gesetzt"
  echo ""
  echo "Workflow re-triggern (manuell):"
  echo "  gh workflow run klickdummy-sync.yml --repo $REPO_FOR_VAR --ref <branch>"
fi

echo ""
echo "🎉 Setup fertig."
echo "  Project: $PROJECT_URL"
echo ""
echo "Wenn Project-Add-Funktion gebraucht wird (gh project item-add), zusätzlich"
echo "ein Repo-Secret GENESOR_PROJECT_TOKEN setzen — Org-PAT mit 'project'-Scope:"
echo "  gh secret set GENESOR_PROJECT_TOKEN --repo $REPO_FOR_VAR"

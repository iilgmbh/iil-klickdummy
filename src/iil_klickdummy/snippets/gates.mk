# gates.mk — Klickdummy Parity-/Sitemap-Drift-Gate als ausrollbarer Baustein
# (platform:ADR-211 Rev 18/21/24 §S13/S14, Issue #162).
#
# 1:1 aus risk-hub Makefile (Zeilen 68-146, verifiziert 2026-07-13) generalisiert
# — dort ist dieser Gate seit ADR-211 Rev 21 im CI verdrahtet. Von 13 Repos mit
# klickdummy/-Verzeichnis fährt bisher nur risk-hub ihn; dieses Snippet macht
# den Rollout in weitere Repos zu einer Include-Zeile statt Copy-Paste-Drift.
#
# Nur Stufe 1 (Spec<->Suite-Drift + Sitemap-Freshness) — Stufe 2 (Live-Renderer-
# #2-Parity) ist repo-spezifisch (DB/Seed) und bleibt bewusst draussen.
#
# --- Verwendung im Adopter-Makefile --------------------------------------
# WICHTIG (per Canary in ausschreibungs-hub verifiziert, 2026-07-13): dieses
# File enthaelt bewusst KEIN `klickdummy-install`-Target. `include` wird beim
# Make-Parsing ausgewertet — BEVOR irgendein Target laeuft. Ein Bootstrap-
# Target, das gates.mk selbst erst per `klickdummy-install-snippets` holt,
# kann daher nicht IN gates.mk stehen (Henne-Ei: die Datei muesste sich selbst
# erzeugen, bevor sie eingelesen wird). Auf einem frischen CI-Checkout mit
# gitignoretem `platform-snippets/` (Standard in risk-hub UND ausschreibungs-
# hub) bricht ein direktes `include gates.mk` mit "Datei oder Verzeichnis
# nicht gefunden" ab, sobald `klickdummy-install` selbst darin steckt.
#
# Deshalb 2 Teile im Adopter-Makefile (siehe
# klickdummy-parity-gate-makefile-bootstrap.mk.example im selben Snippet-
# Ordner fuer die copy-paste-fertige Fassung):
#
#   KLICKDUMMY_ADR_REF := <repo>:ADR-NNN   # Pflicht — lokale Sitemap-ADR-Referenz
#
#   klickdummy-install: ## Bootstrap — bleibt lokal, holt u.a. gates.mk
#   	@test -d $(KLICKDUMMY_VENV) || python3 -m venv $(KLICKDUMMY_VENV)
#   	@$(KLICKDUMMY_VENV)/bin/pip install --quiet --upgrade "iil-klickdummy>=1.32.1,<2.0"
#   	@$(KLICKDUMMY_VENV)/bin/klickdummy-install-snippets --target ./platform-snippets/klickdummy --force
#
#   -include platform-snippets/klickdummy/gates.mk   # `-` = optional, fehlt beim allerersten Lauf
#
# Optionale Overrides (vor dem include setzen):
#   KLICKDUMMY_REPO_NAME     Anzeigename fuer die Sitemap (Default: Verzeichnisname)
#   KLICKDUMMY_VENV          venv-Pfad (Default: .venv-klickdummy)
#
# Pitfall (aus dem Issue, nicht vom Snippet automatisierbar): *.manifest.json in
# die Adopter-.gitignore aufnehmen, sonst Pseudo-Drift (Issue #160/#156-Muster).
# ---------------------------------------------------------------------------

KLICKDUMMY_VENV ?= .venv-klickdummy
# KLICKDUMMY_REPO_NAME bewusst ohne Default hier: klickdummy-gen-sitemap fällt
# selbst auf den Verzeichnisnamen zurück, wenn das 3. Arg fehlt/leer ist — ein
# Default via CURDIR hier würde bei leerem (statt fehlendem) CI-Env-Var
# (`?=` überschreibt keine bereits gesetzte — auch leere — Umgebungsvariable)
# in einer echten Leerstring-Übergabe enden statt im CLI-Fallback.

.PHONY: klickdummy-parity-drift klickdummy-sitemap klickdummy-sitemap-drift

klickdummy-parity-drift: ## ADR-211 S13: Executable-Parity-Suite-Drift — auto-discovers alle klickdummy/*/screens-spec.yaml
	@echo "ADR-211 S13 - Parity-Suite-Drift: re-generieren + git diff (alle Adopter)"
	@for spec in klickdummy/*/screens-spec.yaml; do \
	  mod=$$(basename $$(dirname $$spec)); \
	  out="klickdummy/$$mod/test_parity_$$(echo $$mod | tr - _).py"; \
	  $(KLICKDUMMY_VENV)/bin/klickdummy-gen-e2e "$$spec" "$$out" >/dev/null; \
	done
	@# Compile-Gate (analog risk-hub Retro 2026-06-23): generierte Files sind aus
	@# ruff+pytest exkludiert -> ein gen-e2e-SyntaxError erreicht sonst ungebremst
	@# main. "drift-clean" (diff) belegt NUR Spec<->Suite-Konsistenz, NICHT
	@# Importierbarkeit.
	@python3 -m py_compile klickdummy/*/test_parity_*.py \
	  && echo "ok Parity-Suiten kompilieren" \
	  || { echo "x Parity-Suite kompiliert nicht (gen-e2e-SyntaxError?)"; exit 1; }
	@git diff --exit-code -- klickdummy/*/test_parity_*.py \
	  && echo "ok Parity-Suiten aktuell (kein Drift)" \
	  || { echo "x Parity-Suite veraltet - re-generieren + committen"; exit 1; }

klickdummy-sitemap: ## ADR-211 Rev 24 (S14): KD-Sitemap + kd-tree.json neu generieren
	@test -n "$(KLICKDUMMY_ADR_REF)" || { echo "x KLICKDUMMY_ADR_REF nicht gesetzt (vor dem include definieren, z.B. <repo>:ADR-NNN)"; exit 1; }
	@$(KLICKDUMMY_VENV)/bin/klickdummy-gen-sitemap . $(KLICKDUMMY_ADR_REF) $(KLICKDUMMY_REPO_NAME)

klickdummy-sitemap-drift: klickdummy-sitemap ## ADR-211 Rev 24 (S14): Sitemap-Freshness — re-generieren + git diff (analog klickdummy-parity-drift)
	@echo "ADR-211 S14 - Sitemap-Freshness: re-generieren + git diff"
	@git diff --exit-code -- klickdummy/sitemap klickdummy/_shared/kd-tree.json klickdummy/_shared/kd-tree.js \
	  && echo "ok Sitemap aktuell (kein Drift)" \
	  || { echo "x Sitemap veraltet - re-generieren + committen (make klickdummy-sitemap)"; exit 1; }

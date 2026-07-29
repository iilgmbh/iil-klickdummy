VENV   := .venv
PYTHON := $(VENV)/bin/python
PIP    := $(VENV)/bin/pip
RUFF   := $(VENV)/bin/ruff

.PHONY: install test lint format clean \
        klickdummy-i1 klickdummy-i3 klickdummy-parity-drift klickdummy-gates

# Eigene Klickdummies dieses Repos (Selbst-Konsument). Bewusst NICHT via
# snippets/gates.mk: das Snippet ist für Adopter gebaut und zieht sich das
# Wheel in ein separates .venv-klickdummy — hier liegt das Paket schon als
# editable install im .venv, ein zweiter Bezugsweg wäre genau die
# Versions-Drift, vor der gates.mk warnt.
KD_SPECS := $(wildcard klickdummy/*/screens-spec.yaml)

install:
	python3 -m venv $(VENV)
	$(PIP) install -U pip
	$(PIP) install -e ".[dev]"
	$(PIP) install "ruff==0.15.4"

test:
	$(PYTHON) -m pytest tests/ -v --tb=short

lint:
	$(RUFF) check .
	$(RUFF) format --check .

format:
	$(RUFF) format .
	$(RUFF) check --fix .

klickdummy-i1: ## I1 Spec-first — eigene Specs gegen das Schema validieren
	@test -n "$(KD_SPECS)" || { echo "x keine klickdummy/*/screens-spec.yaml gefunden"; exit 1; }
	@$(VENV)/bin/klickdummy-i1 $(foreach s,$(KD_SPECS),$(s):$(dir $(s))screens-spec.schema.json)

klickdummy-i3: ## I3 Off-Ramp — Doppelquell-Grenze + off_ramp_status je Screen
	@test -n "$(KD_SPECS)" || { echo "x keine klickdummy/*/screens-spec.yaml gefunden"; exit 1; }
	@$(VENV)/bin/klickdummy-i3 $(foreach s,$(KD_SPECS),$(s):$(dir $(s))screens-spec.schema.json)

klickdummy-parity-drift: ## ADR-211 S13 — Parity-Suite neu generieren, kompilieren, Drift prüfen
	@for spec in $(KD_SPECS); do \
	  mod=$$(basename $$(dirname $$spec)); \
	  out="klickdummy/$$mod/test_parity_$$(echo $$mod | tr - _).py"; \
	  $(VENV)/bin/klickdummy-gen-e2e "$$spec" "$$out" >/dev/null; \
	done
	@$(PYTHON) -m py_compile klickdummy/*/test_parity_*.py \
	  && echo "ok Parity-Suiten kompilieren" \
	  || { echo "x Parity-Suite kompiliert nicht (gen-e2e-SyntaxError?)"; exit 1; }
	@# `git diff` sieht UNGETRACKTE Dateien nicht — eine nie committete Suite
	@# liefe sonst als "kein Drift" durch (Blind-Gate-Muster).
	@untracked=$$(git ls-files --others --exclude-standard -- 'klickdummy/*/test_parity_*.py'); \
	  test -z "$$untracked" \
	  || { echo "x Parity-Suite nicht versioniert: $$untracked - committen"; exit 1; }
	@git diff --exit-code -- klickdummy/*/test_parity_*.py \
	  && echo "ok Parity-Suiten aktuell (kein Drift)" \
	  || { echo "x Parity-Suite veraltet - 'make klickdummy-parity-drift' laufen lassen + committen"; exit 1; }

klickdummy-gates: klickdummy-i1 klickdummy-i3 klickdummy-parity-drift ## alle Selbst-Gates

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	rm -rf build/ dist/ .pytest_cache/

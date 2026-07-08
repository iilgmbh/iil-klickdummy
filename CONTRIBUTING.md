# Contributing — `iil-klickdummy`

## Quickstart

```bash
git clone https://github.com/iilgmbh/iil-klickdummy.git
cd iil-klickdummy
make install   # editable install + dev extras + pinned ruff
make test      # pytest tests/ -v --tb=short
make lint      # ruff check + ruff format --check (mirrors CI)
```

`make format` auto-fixes what `make lint` would flag (`ruff format` +
`ruff check --fix`).

## Konventionen

- **Tests**: `test_should_{expected_behavior}` (org-weite Konvention).
- **f-Strings**: `<3.12`-safe halten — lokal läuft nur 3.12, CI matrixt
  3.10/3.11/3.12 (`.github/workflows/ci.yml`).
- **Schema-Konstanten**: immer aus `src/iil_klickdummy/read_model.py`
  importieren, nie inline (KONZ-iil-klickdummy-003 Empf-3 S1).
- **Commits**: `[feat|fix|refactor|docs|test|chore](scope): description`.

## CI

`ci.yml` ist ein Thin-Caller auf `platform/.github/workflows/_ci-pypi.yml`
(Lint, Secret-Scan, Test+Coverage über Python 3.10/3.11/3.12, Build+Artefakt-
Scan, pip-audit). `make lint`/`make test` laufen mit denselben Befehlen lokal.

## Konzepte & ADRs

- Plattform-Konvention: `platform:ADR-211`.
- Implementations-ADR: `iilgmbh:iil-klickdummy:ADR-001`.
- Konzepte: `docs/konzepte/KONZ-iil-klickdummy-NNN.md`.

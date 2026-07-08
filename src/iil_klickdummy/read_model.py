"""Read-Model-Schema für iil-klickdummy (KONZ-003 Empf-3, Scheibe S1).

Definiert die **Feldverträge** der zwei Read-Model-Flächen als TypedDicts
und zentralisiert die Schema-Versionskonstanten.

**Abgeleiteter Index, KEIN System of Record** (KONZ-003 C7/Risiko #4).
Die kanonischen Quellen sind die YAML-Specs im git — dieses Modul beschreibt
nur die Form des davon abgeleiteten JSON-Outputs.

S2 (Repository-Port/Protocol) und S3 (Multi-Adapter: pgvector/SQLite/Postgres)
sind **trigger-gegatet** — erst wenn KONZ-003 §13 Postgres-Trigger (b) feuert
(zweiter Live-Konsument fragt uc-export.json ab statt die Datei zu lesen).
"""

from __future__ import annotations

import json
import pathlib
import sys
from functools import lru_cache
from importlib.resources import files
from typing import TypedDict

try:
    import yaml
except ImportError:
    print("FAIL (setup): PyYAML fehlt. pip install pyyaml")
    sys.exit(2)

try:
    import jsonschema
except ImportError:
    print("FAIL (setup): jsonschema fehlt. pip install jsonschema")
    sys.exit(2)

# ---------------------------------------------------------------------------
# Spec-YAML-Loader (A-04, Issue #113): 7 Module (check_i1/i2/i3, manage,
# gen_e2e, extract_requirements, registry) hatten je eine fast-identische
# Ad-hoc-Loader-Funktion mit sichtbarer Fehlerbehandlungs-Drift — u. a. hatte
# extract_requirements.py GAR KEIN yaml.YAMLError-Handling (A-01), obwohl der
# eigene Docstring-Kontrakt "Exit: 1" das voraussetzt. Diese Funktion bündelt
# nur das Lesen+Parsen (kein Error-Handling) — jeder Aufrufer entscheidet
# weiterhin selbst über seinen Fail-Modus (fatal exit / soft {}-Fallback /
# eigene Fehlermeldung), das bleibt bewusst bei den Aufrufern.
# ---------------------------------------------------------------------------


def load_spec_yaml(path: pathlib.Path | str):
    """Liest eine Spec-Datei und parsed sie als YAML (`.yaml`/`.yml`) oder
    JSON (jede andere Extension, z. B. ein `<spec>:<schema>`-Schema-Pfad).
    Wirft `yaml.YAMLError`/`json.JSONDecodeError`/`OSError` unverändert an
    den Aufrufer durch — kein Silent-Fallback hier."""
    p = pathlib.Path(path)
    text = p.read_text(encoding="utf-8")
    if p.suffix in (".yaml", ".yml"):
        return yaml.safe_load(text)
    return json.loads(text)


# ---------------------------------------------------------------------------
# Spec-Schema-Validierung (geteilt zwischen gen_e2e.load_spec und
# genesor/scan.py — Session-Retro 2026-07-03 AD-6/Issue #103: der
# genesor-Scan-Pfad validierte Specs bisher gar nicht gegen
# screens-spec.schema.json, nur `yaml.safe_load`. Ursprünglich in gen_e2e.py
# (B-1, M28-3); hierher verschoben, damit beide Aufrufer denselben
# Validierungs-Helfer nutzen statt ihn zu duplizieren.
# ---------------------------------------------------------------------------


@lru_cache(maxsize=1)
def _load_schema() -> dict:
    """Gebündeltes Screens-Spec-Schema (Single Source of Truth für Validierung).

    Gecacht (M28-3): das Schema ist ein unveränderliches Paket-Asset; ohne Cache
    las jeder `validate_spec`-Call es neu von Disk."""
    text = (files("iil_klickdummy") / "schemas" / "screens-spec.schema.json").read_text(
        encoding="utf-8"
    )
    return json.loads(text)


def validate_spec(spec: dict) -> list[str]:
    """Validiert eine Spec gegen ``screens-spec.schema.json``.

    Gibt eine Liste von Fehler-Strings zurück (leer = konform). Die Spec ist
    eine **Vertrauensgrenze**: ihre Werte landen in generiertem Python
    (Kommentare, Docstrings, Locator-Ausdrücke) bzw. in gerendertem HTML.
    Ohne Validierung konnte ein bösartiges/kaputtes Feld strukturell
    durchrutschen (B-1). Escaping an den Senken (``gen_suite``, ``render_uc``,
    ``lineage``) ist die zweite, unabhängige Verteidigungslinie — diese
    Funktion macht Verstöße zusätzlich *sichtbar*.
    """
    schema = _load_schema()
    return [
        f"{'/'.join(str(p) for p in e.absolute_path) or '(root)'}: {e.message}"
        for e in sorted(
            jsonschema.Draft7Validator(schema).iter_errors(spec),
            key=lambda x: list(x.absolute_path),
        )
    ]


# ---------------------------------------------------------------------------
# UC-Export (genesor/export.py → uc-export.json)
# ---------------------------------------------------------------------------

UC_EXPORT_SCHEMA_VERSION = "1.0"


class UcCoverage(TypedDict):
    realized_count: int
    unresolved_refs: list[str]


class UcExportRow(TypedDict):
    uc_id_global: str
    uc_id_local: str
    repo: str
    name: str
    primaer_akteur: str | None
    sekundaer_akteure: list[str]
    realisiert_von_klickdummy: str | None
    related_screens: list[str]
    fv_bezug: str | None
    prio: str | None
    status: str
    source_file: str
    coverage: UcCoverage


class KdExportRow(TypedDict):
    repo: str
    kd_name: str
    adr_local: str
    klass: str | None
    spec_role: str
    sunset_after: str | None
    n_screens: int
    render_url: str


class CoverageCell(TypedDict):
    uc_id_global: str
    repo: str
    kd_name: str
    screens: list[str]


class UcExportSummary(TypedDict):
    n_ucs: int
    n_kds: int
    n_realized_ucs: int
    n_coverage_cells: int
    repos: list[str]


class UcExportEnvelope(TypedDict):
    schema_version: str
    generated_at: str
    source: str
    summary: UcExportSummary
    kds: list[KdExportRow]
    ucs: list[UcExportRow]
    coverage_matrix: list[CoverageCell]


# ---------------------------------------------------------------------------
# Discovery (discovery_push.py → NDJSON / pgvector / Snapshot)
# ---------------------------------------------------------------------------

REGISTRY_SCHEMA_VERSION = "v1.6"
API_VERSION = "v1"
EMBEDDING_INPUT_SCHEMA = "v1"


class DiscoveryEntry(TypedDict):
    schema_version: str
    registry_key: str
    spec_id: str
    version: str
    klickdummy_class: str
    topic: str
    adr: str
    conforms_to: str
    sister_of: list[str]
    repo: str
    path_rel: str
    genre: str
    personas: list[str]
    pipeline_status: str
    off_ramp_status: str
    visibility_scope: str
    discoverable: bool
    tombstone: bool
    embedding_text: str
    embedding_input_schema: str
    source_repo: str
    source_ref: str | None
    commit_sha: str | None
    spec_sha256: str | None
    generated_at: str
    last_seen: str
    sunset_after: str | None


class DiscoveryEnvelope(TypedDict):
    api_version: str
    registry_schema_version: str
    generated_at: str
    entries: list[DiscoveryEntry]


class DiscoverySnapshot(TypedDict):
    api_version: str
    registry_schema_version: str
    generated_at: str
    count: int
    sha256: str
    entries: list[DiscoveryEntry]

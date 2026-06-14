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

from typing import TypedDict

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

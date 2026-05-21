"""iil-klickdummy — shared infrastructure for platform:ADR-211 Rev 14.

Public surface:
    check_i1, check_i2, check_i3, check_i4 — invariant checks
    extract_requirements                    — Spec → UC/FR/NFR/Lasten/Pflicht
    inventory                               — S11 Cross-Repo Legacy-Inventur
    install_snippets                        — copy/symlink HTML+JS+templates into a repo
    registry                                — Klickdummy-Discovery + Browser (v1.1)

Distribution: pip via public PyPI (v1.1+) oder Git-URL (Fallback).
ADR-211 Rev 14 §Distribution.

Snippets shipped as package_data; consumers install them via
`klickdummy-install-snippets` console-script.
"""

# Single source of truth: pyproject.toml → importlib.metadata.
# Vermeidet Mismatch wie in v1.1.0/v1.1.1 (pyproject != __init__).
try:
    from importlib.metadata import version as _pkg_version
    __version__ = _pkg_version("iil-klickdummy")
except Exception:                              # noqa: BLE001
    __version__ = "0.0.0+unknown"
__author__ = "iil GmbH"

from . import (  # noqa: F401
    check_i1, check_i2, check_i3, check_i4,
    extract_requirements, inventory, install_snippets, registry,
)

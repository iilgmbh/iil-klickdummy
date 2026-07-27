"""Regressionstests für Issue #179: ziffern-präfigierte Repo-Namen.

`screens-spec.schema.json` erzwang für den Repo-Teil von `spec_id`, `adr.local`
und `adr.sister_of[]` ein `^[a-z]`-Erstzeichen. Ein echter, existierender
Repo-Name wie `137-hub` (achimdehnert/137-hub) verletzte das — I1 (Spec-first)
schlug mit `does not match '^[a-z][a-z0-9_-]*:...'` fehl.

Der Workaround in achimdehnert/137-hub#69 war ein ad-hoc-Alias (`hub137`), für
den keine Konvention existierte: der nächste Adopter hätte erneut geraten
(`hub137` / `137hub` / `n137hub`), und Cross-Repo-Refs aus ANDEREN Repos auf
`137-hub:ADR-NNN` wären weiterhin am Schema gescheitert.

Fix: Ziffer als Erstzeichen des Repo-Teils erlauben. Der Namens-Teil hinter dem
`:` bleibt unverändert `^[a-z]`-gebunden — dort gibt es keinen Realfall.
"""

from __future__ import annotations

import re

from iil_klickdummy import check_i4
from iil_klickdummy.read_model import validate_spec


def _minimal_spec(spec_id: str, adr_local: str, sister_of: list[str] | None = None):
    adr: dict = {"local": adr_local, "conforms_to": "platform:ADR-211"}
    if sister_of is not None:
        adr["sister_of"] = sister_of
    return {
        "spec_id": spec_id,
        "spec_version": "0.1",
        "spec_date": "2026-07-27",
        "adr": adr,
        "class": "mock",
    }


# ------------------------------------------------- Schema


def test_should_accept_digit_prefixed_repo_in_spec_id():
    errors = validate_spec(
        _minimal_spec("137-hub:klickdummy-spec-demo", "137-hub:ADR-002")
    )

    assert not [e for e in errors if e.startswith(("spec_id", "adr/local"))], errors


def test_should_accept_digit_prefixed_repo_in_sister_of():
    errors = validate_spec(
        _minimal_spec(
            "137-hub:klickdummy-spec-demo",
            "137-hub:ADR-002",
            sister_of=["137-hub:ADR-003", "137-hub:klickdummy-spec-other"],
        )
    )

    assert not [e for e in errors if e.startswith("adr/sister_of")], errors


def test_should_still_accept_letter_prefixed_repo():
    """Die Lockerung darf den Normalfall nicht verändern."""
    errors = validate_spec(
        _minimal_spec("meiki:klickdummy-spec-fristen", "meiki:ADR-021")
    )

    assert not [e for e in errors if e.startswith(("spec_id", "adr/local"))], errors


def test_should_still_reject_uppercase_repo_prefix():
    """Nur Ziffern kommen dazu — Großbuchstaben bleiben verboten."""
    errors = validate_spec(_minimal_spec("Meiki:klickdummy-spec-x", "meiki:ADR-021"))

    assert [e for e in errors if e.startswith("spec_id")], errors


def test_should_still_reject_missing_colon():
    errors = validate_spec(_minimal_spec("137-hub", "137-hub:ADR-002"))

    assert [e for e in errors if e.startswith("spec_id")], errors


# ------------------------------------------------- I4-Checker


def test_should_treat_digit_prefixed_ref_as_repo_qualified():
    """Ohne den Fix matchte die Prefix-Gruppe nicht, `137-hub:ADR-002` wurde
    also wie eine unqualifizierte *lokale* ADR-Referenz bewertet."""
    m = check_i4.ADR_PATTERN.search("siehe 137-hub:ADR-002 für Details")

    assert m is not None
    assert m.group("prefix") == "137-hub:"
    assert m.group("adr") == "ADR-002"


def test_should_still_match_bare_adr_without_prefix():
    m = check_i4.ADR_PATTERN.search("siehe ADR-021")

    assert m is not None
    assert m.group("prefix") is None


def test_should_still_match_letter_prefixed_ref():
    m = check_i4.ADR_PATTERN.search("platform:ADR-211")

    assert m is not None
    assert m.group("prefix") == "platform:"


# ------------------------------------------------- Schema/Checker-Kohärenz


def test_schema_and_checker_agree_on_digit_prefix():
    """Beide Stellen mussten gemeinsam gelockert werden — driften sie
    auseinander, akzeptiert das Schema eine Ref, die I4 dann anders liest."""
    from iil_klickdummy.read_model import _load_schema

    pattern = _load_schema()["properties"]["adr"]["properties"]["local"]["pattern"]

    assert re.match(pattern, "137-hub:ADR-002")
    assert check_i4.ADR_PATTERN.search("137-hub:ADR-002").group("prefix") == "137-hub:"

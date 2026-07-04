"""Regressionstests für B-3 (persona→personas No-Op) und B-5 (rglob-Fehlklassifikation).

Aus dem /repo-optimize-Report runB. Beide Bugs waren stille Fehlverhalten:
- B-3: `generate_uc_skeletons` las `s.get("persona")` (Singular) statt des
  Schema-Feldes `personas` (Plural, required) → erzeugte NIE ein UC-Skelett.
- B-5: `discover_klickdummies` nutzte `rglob` → verschachtelte Fixture-Specs
  wurden als eigenständige Klickdummies fehl-erkannt.
"""

from __future__ import annotations

import yaml


def _spec_with_personas_plural() -> dict:
    return {
        "spec_id": "repo:demo",
        "spec_version": "0.1",
        "spec_date": "2026-06-01",
        "adr": {"local": "repo:ADR-001", "conforms_to": "platform:ADR-211"},
        "class": "mock",
        "personas": {
            "buerger": {
                "label": "Bürger",
                "rolle": "buerger",
                "description": "Antragsteller",
                "halbschicht": "buerger",
            }
        },
        "screens": [
            {
                "id": "antrag",
                "title": "Antrag stellen",
                "personas": ["buerger"],
                "purpose": "Antrag",
                "off_ramp_status": "static",
                "parity_acceptance": [],
            },
            {
                "id": "status",
                "title": "Status ansehen",
                "personas": ["buerger"],
                "purpose": "Status",
                "off_ramp_status": "static",
                "parity_acceptance": [],
            },
        ],
    }


def test_should_generate_uc_skeletons_from_plural_personas():
    """B-3: mit Schema-korrektem `personas` (Plural) erzeugt der Generator je
    Screen ein UC-Skelett. Vor dem Fix (`s.get('persona')`, Singular) war das ein
    stiller No-Op — `written` blieb leer, obwohl Personas vorhanden waren."""
    from iil_klickdummy.genesor.ucs import generate_uc_skeletons

    records = [
        {
            "kind": "spec",
            "repo": "iil-klickdummy",
            "kd": "demo",
            "data": _spec_with_personas_plural(),
        }
    ]
    result = generate_uc_skeletons(records, existing_ucs=[], dry_run=True)
    # zwei Screens × primäre Persona → zwei Skelette (kein No-Op mehr)
    assert len(result["written"]) == 2


def test_should_treat_singular_persona_as_backward_compat_fallback():
    """B-3: `persona` (Singular) bleibt als Rückwärtskompat-Fallback lesbar —
    angeglichen an render_genesor/render_fallback (`personas or persona`)."""
    from iil_klickdummy.genesor.ucs import generate_uc_skeletons

    spec = _spec_with_personas_plural()
    for sc in spec["screens"]:
        sc["persona"] = sc.pop("personas")  # nur Singular gesetzt
    records = [{"kind": "spec", "repo": "iil-klickdummy", "kd": "demo", "data": spec}]
    result = generate_uc_skeletons(records, existing_ucs=[], dry_run=True)
    assert len(result["written"]) == 2


def _write_spec(path, spec_id):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        yaml.dump({"spec_id": spec_id, "spec_version": "0.1", "title": "Demo"}),
        encoding="utf-8",
    )


def test_should_not_discover_nested_fixture_specs_as_klickdummies(tmp_path):
    """B-5: nur `klickdummy/<name>/screens-spec.yaml` (eine Ebene) ist ein KD.
    Eine verschachtelte Fixture-Spec (z.B. in `<name>/tests/…`) darf NICHT als
    eigenständiger Klickdummy erkannt werden. Vor dem Fix (`rglob`) tauchte sie
    fälschlich als zweiter KD in der Registry auf."""
    from iil_klickdummy.registry import discover_klickdummies

    _write_spec(tmp_path / "klickdummy" / "demo" / "screens-spec.yaml", "repo:demo")
    _write_spec(
        tmp_path / "klickdummy" / "demo" / "tests" / "fixtures" / "screens-spec.yaml",
        "repo:nested-fixture",
    )
    kds = discover_klickdummies(tmp_path)
    ids = {k.spec_id for k in kds}
    assert ids == {"repo:demo"}
    assert len(kds) == 1

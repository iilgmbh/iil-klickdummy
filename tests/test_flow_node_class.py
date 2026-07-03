"""Screen-Klassen: Assertions-Screen vs Flow-Knoten (KONZ-008, entschärft M28-2).

Ein Multi-Screen-Flow-KD (z.B. risk-hub ex-schutz) fährt `screens[]` auch als
Navigations-Graph: Flow-Knoten mit `next_screens`/`back_screen`, ohne
`parity_acceptance`. Vor dem Fix lehnte die fatale Schema-Validierung (#102)
solche Knoten ab (purpose/parity_acceptance/off_ramp_status Pflicht auf JEDEM
Screen) → 1.30 hätte bestehende Flow-KDs gebrochen.
"""
from __future__ import annotations

import json

from importlib.resources import files

from iil_klickdummy import gen_e2e


def _schema() -> dict:
    return json.loads(
        files("iil_klickdummy.schemas").joinpath("screens-spec.schema.json").read_text()
    )


def _base(screens: list[dict]) -> dict:
    return {
        "spec_id": "repo:spec-test", "spec_version": "0.1", "spec_date": "2026-06-01",
        "adr": {"local": "repo:ADR-001", "conforms_to": "platform:ADR-211"},
        "class": "mock", "grounding": {"konzept": "-", "pilot": "-"},
        "off_ramp": {"policy": "-", "unit": "per-screen", "rule": "-",
                     "doppelquell_grenze": "prod-release", "parity_runner": "-"},
        "personas": {"u": {"label": "U", "rolle": "u", "sieht": []}},
        "screens": screens,
    }


_ASSERT_SCREEN = {
    "id": "workflow", "title": "W", "personas": ["u"], "purpose": "-",
    "off_ramp_status": "static",
    "parity_acceptance": [{"id": "w.v", "check": "visible c",
                           "assert": {"action": "visible", "selector": "[data-testid=x]"}}],
}
_FLOW_FWD = {"id": "phase1", "title": "P1", "personas": ["u"], "next_screens": ["phase2"]}
_FLOW_TERM = {"id": "export", "title": "Export", "personas": ["u"], "back_screen": "phase1"}


def test_should_accept_forward_flow_node_without_parity_acceptance():
    """Flow-Knoten mit next_screens, ohne parity_acceptance/purpose/off_ramp_status → valide."""
    assert not gen_e2e.validate_spec(_base([_ASSERT_SCREEN, _FLOW_FWD]))


def test_should_accept_terminal_flow_node_with_back_screen():
    """Terminaler Flow-Knoten (nur back_screen) → valide (ex-schutz `export`)."""
    assert not gen_e2e.validate_spec(_base([_ASSERT_SCREEN, _FLOW_TERM]))


def test_should_still_reject_screen_that_is_neither_class():
    """Sicherheitsnetz erhalten: ein Screen ohne parity_acceptance UND ohne
    next_screens/back_screen ist weder Assertions-Screen noch Flow-Knoten → invalid
    (kein stiller Durchlass für vergessene parity_acceptance)."""
    orphan = {"id": "orphan", "title": "O", "personas": ["u"]}
    errs = gen_e2e.validate_spec(_base([_ASSERT_SCREEN, orphan]))
    assert any("orphan" in e or "screens/1" in e for e in errs)


def test_should_reject_parity_acceptance_screen_masquerading_as_flow_node():
    """EF-2 (Retro 2026-07-03): ein Screen, der `parity_acceptance` TRÄGT, aber
    `purpose`/`off_ramp_status` vergessen hat und nebenbei `next_screens` hat, darf
    NICHT als Flow-Knoten durchrutschen (sonst würde seine parity_acceptance vom
    Gate still ignoriert). Das `not: {required: [parity_acceptance]}` auf beiden
    Flow-Branches erzwingt: wer parity_acceptance hat, MUSS Assertions-Screen sein
    (purpose + off_ramp_status Pflicht) — sonst invalid."""
    masquerader = {
        "id": "sneaky", "title": "S", "personas": ["u"],
        "next_screens": ["phase2"],   # sähe wie Flow-Knoten aus …
        "parity_acceptance": [{"id": "s.v", "check": "visible c"}],  # … trägt aber Asserts
        # purpose + off_ramp_status FEHLEN → Assertions-Branch scheitert auch
    }
    errs = gen_e2e.validate_spec(_base([_ASSERT_SCREEN, masquerader]))
    assert any("sneaky" in e or "screens/1" in e for e in errs)


def test_should_pass_i3_for_flow_node_without_off_ramp_status(tmp_path):
    """I3 nimmt Flow-Knoten vom off_ramp_status-Zwang aus."""
    import yaml
    from iil_klickdummy import check_i3
    spec_file = tmp_path / "spec.yaml"
    spec_file.write_text(yaml.dump(_base([_ASSERT_SCREEN, _FLOW_FWD, _FLOW_TERM])), encoding="utf-8")
    rc = check_i3.main([str(spec_file)])
    assert rc == 0

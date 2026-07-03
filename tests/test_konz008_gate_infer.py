"""KONZ-iil-klickdummy-008 — C (parity_gate) + A (infer_asserts).

Gegründet am Pilot-Befund ex-schutz: von 4 Checks ist 1 präsenz-/zähl-inferierbar,
3 sind Verhaltens-/State-Aussagen (behavioral-manual). Die Tests fixieren genau
diese Arbeitsteilung und die zwei im Pilot gefundenen Heuristik-Fallen.
"""
from __future__ import annotations


# -- C: parity_gate ----------------------------------------------------------

def _manifest(skipped_detail=None, fragile=None):
    return {
        "executable": 0, "skipped": len(skipped_detail or []),
        "skipped_detail": skipped_detail or [],
        "fragile_selectors": fragile or [],
    }


def _spec(kinds: dict) -> dict:
    return {"screens": [{
        "id": "s",
        "parity_acceptance": [
            {"id": cid, "check": "x" * 8, **({"kind": k} if k else {})}
            for cid, k in kinds.items()
        ],
    }]}


def test_should_fail_gate_when_executable_check_is_skipped():
    from iil_klickdummy import parity_gate
    spec = _spec({"c1": "executable"})
    man = _manifest(skipped_detail=[{"screen": "s", "id": "c1", "skip_reason": "no_assert"}])
    ok, violations = parity_gate.evaluate(spec, man, "A")
    assert not ok and any("c1" in v for v in violations)


def test_should_exempt_behavioral_manual_check_from_gate():
    from iil_klickdummy import parity_gate
    spec = _spec({"c1": "behavioral-manual"})
    man = _manifest(skipped_detail=[{"screen": "s", "id": "c1", "skip_reason": "no_assert"}])
    ok, violations = parity_gate.evaluate(spec, man, "A")
    assert ok and not violations          # getaggt → kein Verstoß, aber sichtbar (nicht still)


def test_should_default_kind_to_executable_when_unset():
    from iil_klickdummy import parity_gate
    spec = _spec({"c1": None})            # kein kind → Default executable
    man = _manifest(skipped_detail=[{"screen": "s", "id": "c1", "skip_reason": "no_assert"}])
    ok, _ = parity_gate.evaluate(spec, man, "A")
    assert not ok


def test_should_fail_gate_on_fragile_selector():
    from iil_klickdummy import parity_gate
    spec = _spec({"c1": "executable"})
    man = _manifest(fragile=[{"screen": "s", "id": "c1", "selector": "button.submit"}])
    ok, violations = parity_gate.evaluate(spec, man, "A")
    assert not ok and any("fragil" in v.lower() for v in violations)


def test_should_pass_gate_when_all_executable_covered_and_no_fragile():
    from iil_klickdummy import parity_gate
    spec = _spec({"c1": "executable", "c2": "behavioral-manual"})
    man = _manifest(skipped_detail=[{"screen": "s", "id": "c2", "skip_reason": "no_assert"}])
    ok, violations = parity_gate.evaluate(spec, man, "A")
    assert ok and not violations          # c1 ausführbar, c2 getaggt


# -- A: infer_asserts --------------------------------------------------------

def test_should_tag_behavioral_check_manual_not_guess_assert():
    from iil_klickdummy import infer_asserts
    rec = infer_asserts.infer_one(
        "Übergangs-Gates blockieren weitere Phasen bis Vorbedingungen erfüllt sind.",
        concrete={"gate"}, templated=set())
    assert rec["kind"] == "behavioral-manual" and "assert" not in rec


def test_should_tag_templated_count_behavioral_manual_not_executable():
    """EF-3 (Retro 2026-07-03): ein templated testid (`step-${…}`) ist per exact-match
    NICHT zählbar → KEIN toter executable-Assert. behavioral-manual + Container-Hinweis,
    kein Selbstwiderspruch (Warnung + `executable` gleichzeitig)."""
    from iil_klickdummy import infer_asserts
    rec = infer_asserts.infer_one(
        "Alle 10 Phasen-Stepper-Einträge (step-1 … step-10) sichtbar.",
        concrete=set(), templated={"step"})
    assert rec["kind"] == "behavioral-manual"     # NICHT executable
    assert "assert" not in rec                     # kein funktional toter Kandidat
    assert "Container" in rec["note"] and "step-list" in rec["note"]  # wie es executable würde


def test_should_not_match_bar_inside_sichtbar_word_boundary():
    """Pilot-Falle: `tenant-bar` matchte via 'bar' in 'sicht·bar'. Wortgrenzen fixen das."""
    from iil_klickdummy import infer_asserts
    tid = infer_asserts._match_testid(
        "Alle 10 Einträge sichtbar.", concrete={"tenant-bar"}, templated=set())
    assert tid is None                    # kein Fehl-Match auf 'bar'


def test_should_infer_visible_from_presence_plus_concrete_testid():
    from iil_klickdummy import infer_asserts
    rec = infer_asserts.infer_one(
        "Der Bereich area-table ist sichtbar.", concrete={"area-table"}, templated=set())
    # 'protokolliert' fehlt → nicht behavioral; voller Anker area-table matcht
    assert rec["kind"] == "executable" and rec["assert"]["action"] == "visible"
    assert rec["assert"]["selector"] == "testid=area-table"


def test_should_split_concrete_and_templated_testids():
    from iil_klickdummy import infer_asserts
    html = '<div data-testid="area-table"></div><li data-testid="step-${p.id}"></li>'
    concrete, templated = infer_asserts.testid_inventory(html)
    assert "area-table" in concrete and "step" in templated

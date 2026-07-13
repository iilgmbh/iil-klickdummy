"""Tests für den Parity-Gate-Snippet-Baustein (Issue #162).

`gates.mk` (Makefile-Seite) + `klickdummy-parity-gate.yml` (reusable GH-Actions-
Workflow) + der Copy-Paste-Caller-Snippet müssen syntaktisch valide sein und
über `klickdummy-install-snippets` ausgeliefert werden — ohne dass
`install_snippets.py` selbst angefasst werden muss (der Snippet-Ordner wird
komplett kopiert).
"""

from __future__ import annotations

import pathlib
import subprocess

import yaml

from iil_klickdummy import install_snippets

REPO_ROOT = pathlib.Path(__file__).parent.parent
GATES_MK = REPO_ROOT / "src" / "iil_klickdummy" / "snippets" / "gates.mk"
WORKFLOW = REPO_ROOT / ".github" / "workflows" / "klickdummy-parity-gate.yml"
CALLER_SNIPPET = (
    REPO_ROOT
    / "src"
    / "iil_klickdummy"
    / "snippets"
    / "klickdummy-parity-gate-caller.yml.example"
)


# ------------------------------------------------------- gates.mk delivery


def test_should_deliver_gates_mk_via_install_snippets(tmp_path):
    target = tmp_path / "out"
    rc = install_snippets.main(["--target", str(target)])
    assert rc == 0
    assert (target / "gates.mk").read_text(encoding="utf-8") == GATES_MK.read_text(
        encoding="utf-8"
    )


def test_should_deliver_caller_snippet_via_install_snippets(tmp_path):
    target = tmp_path / "out"
    rc = install_snippets.main(["--target", str(target)])
    assert rc == 0
    assert (target / "klickdummy-parity-gate-caller.yml.example").exists()


# ------------------------------------------------------- gates.mk content


def test_gates_mk_declares_expected_targets():
    text = GATES_MK.read_text(encoding="utf-8")
    for target in (
        "klickdummy-install",
        "klickdummy-parity-drift",
        "klickdummy-sitemap",
        "klickdummy-sitemap-drift",
    ):
        assert f"{target}:" in text, f"Target {target} fehlt in gates.mk"


def test_gates_mk_does_not_hardcode_self_hosted_runner():
    """Pitfall aus Issue #162: gates.mk selbst ist Runner-agnostisch (kein
    `runs-on`-Konzept auf Make-Ebene, aber auch keine self-hosted-Annahmen wie
    feste Pfade/Labels)."""
    assert "self-hosted" not in GATES_MK.read_text(encoding="utf-8")


# ------------------------------------------------------- gates.mk syntax (make -n)


def _run_make_dry_run(tmp_path: pathlib.Path, target: str, extra_env=None) -> str:
    makefile = tmp_path / "Makefile"
    makefile.write_text(
        f"KLICKDUMMY_ADR_REF := test-repo:ADR-001\ninclude {GATES_MK}\n",
        encoding="utf-8",
    )
    (tmp_path / "klickdummy").mkdir(exist_ok=True)
    env = {"PATH": "/usr/bin:/bin"}
    if extra_env:
        env.update(extra_env)
    result = subprocess.run(
        ["make", "-n", "-f", str(makefile), target],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        env=env,
        timeout=15,
    )
    assert result.returncode == 0, (
        f"make -n {target} fehlgeschlagen:\nstdout={result.stdout}\nstderr={result.stderr}"
    )
    return result.stdout


def test_make_dry_run_parses_klickdummy_install(tmp_path):
    _run_make_dry_run(tmp_path, "klickdummy-install")


def test_make_dry_run_parses_klickdummy_parity_drift(tmp_path):
    _run_make_dry_run(tmp_path, "klickdummy-parity-drift")


def test_make_dry_run_parses_klickdummy_sitemap(tmp_path):
    out = _run_make_dry_run(tmp_path, "klickdummy-sitemap")
    assert "klickdummy-gen-sitemap" in out


def test_make_dry_run_parses_klickdummy_sitemap_drift(tmp_path):
    _run_make_dry_run(tmp_path, "klickdummy-sitemap-drift")


# ------------------------------------------------------- reusable workflow (YAML)


def test_workflow_is_valid_yaml_with_workflow_call():
    doc = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
    # YAML lädt den Top-Level-Key `on:` als bool True (YAML 1.1 "on"/"off"-
    # Sonderfall) — dasselbe Verhalten wie in echten GH-Actions-YAMLs.
    on_key = True if True in doc else "on"
    assert "workflow_call" in doc[on_key]


def test_workflow_requires_adr_ref_input():
    doc = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
    on_key = True if True in doc else "on"
    inputs = doc[on_key]["workflow_call"]["inputs"]
    assert inputs["adr_ref"]["required"] is True


def test_workflow_does_not_hardcode_self_hosted_runner():
    """Pitfall aus Issue #162: kein hartkodiertes self-hosted-Label — Default
    ist ein parametrisierbarer Input mit ubuntu-latest."""
    doc = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
    job = doc["jobs"]["klickdummy-parity-drift"]
    assert job["runs-on"] == "${{ inputs.runs_on }}"
    on_key = True if True in doc else "on"
    assert (
        doc[on_key]["workflow_call"]["inputs"]["runs_on"]["default"] == "ubuntu-latest"
    )


# ------------------------------------------------------- caller snippet


def test_caller_snippet_references_correct_workflow_path():
    text = CALLER_SNIPPET.read_text(encoding="utf-8")
    assert "iilgmbh/iil-klickdummy/.github/workflows/klickdummy-parity-gate.yml" in text
    assert "adr_ref:" in text

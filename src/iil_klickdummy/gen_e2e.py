#!/usr/bin/env python3
"""Klickdummy-Spec → ausführbare E2E-Parity-Suite (Playwright/pytest).

**Keystone des Spec-as-System-of-Record-Pfades (platform:ADR-211 §Parity-Off-Ramp).**

Forward-only, deterministisch — analog `extract_requirements`. Liest eine
Screens-Spec (YAML) und emittiert *eine* pytest+Playwright-Datei, in der jeder
`parity_acceptance`-Eintrag mit ausführbarem `assert`-Block zu *einem* Testfall
wird. Dieselbe Assertion validiert zwei Renderer:

  - **Renderer #1 (Klickdummy)** — frühe Validierung, stirbt per I3 planmäßig.
  - **Renderer #2 (echte App)** — parity-gegated gegen *dieselbe* Spec.

Das Ziel wird zur Laufzeit via `KLICKDUMMY_BASE_URL` umgeschaltet; die Suite
selbst ist identisch. **Parity-grün gegen Renderer #2 = das I3-Off-Ramp-Gate**:
sobald ein Screen grün ist, darf er aus der statischen Quelle entfernt werden
(`off_ramp_status: static → parity-green`). Die Tests überleben den Off-Ramp —
das ist die Kontinuität, die der Klickdummy selbst (als Wegwerf-Renderer) nicht
geben kann.

`parity_acceptance`-Einträge OHNE `assert`-Block bleiben sichtbar (als
`@pytest.mark.skip` mit der Prosa als Grund) — kein stilles Weglassen. Die
Zusammenfassung zählt ausführbar vs. nur-Prosa.

Aufruf:
    klickdummy-gen-e2e <spec.yaml> [<out-file>]
    # Default out-file: <spec-dir>/tests/test_parity_<spec-stem>.py

Exit: 0 ok, 1 Spec-Fehler, 2 Setup-Fehler.
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import re
import sys
from datetime import date

try:
    import yaml
except ImportError:
    print("FAIL (setup): PyYAML fehlt. pip install pyyaml")
    sys.exit(2)


# -- Helpers ------------------------------------------------------------------

def ident(s: str) -> str:
    """Python-sicherer Bezeichner-Fragment (für Testfunktionsnamen)."""
    out = re.sub(r"[^0-9a-zA-Z]+", "_", str(s)).strip("_").lower()
    return out or "x"


def load_spec(path: pathlib.Path) -> dict:
    if not path.exists():
        print(f"FAIL: Spec fehlt: {path}")
        sys.exit(1)
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def screen_route(sc: dict) -> str:
    """Explizite `route` oder Konvention `/<id>`."""
    r = sc.get("route")
    if r:
        return r if r.startswith("/") else "/" + r
    return "/" + str(sc.get("id", ""))


# -- Assertion-Vokabular ------------------------------------------------------
# Bewusst klein & standard-nah gehalten (Playwright sync_api). Ein `assert`-Block
# ist {action, selector?, expect?}. Unbekannte/fehlende action ⇒ nur-Prosa.

def _q(s) -> str:
    """Double-quoted Python-String-Literal — `ruff format`-konform (nicht `repr`,
    das Single-Quotes liefert und Adopter mit `ruff format --check` rot macht)."""
    return json.dumps(str(s), ensure_ascii=False)


def render_assertion(a: dict) -> str | None:
    """Eine Playwright-Assertion-Zeile oder None (= nicht ausführbar)."""
    if not isinstance(a, dict):
        return None
    action = str(a.get("action", "")).strip()
    sel = a.get("selector", "")
    exp = a.get("expect", "")
    if action == "visible":
        return f"expect(page.locator({_q(sel)})).to_be_visible()"
    if action == "text":
        return f"expect(page.locator({_q(sel)})).to_contain_text({_q(exp)})"
    if action == "clickable":
        # I2-Geist: kein toter Link — Element sichtbar UND bedienbar.
        return f"expect(page.locator({_q(sel)})).to_be_enabled()"
    if action == "url":
        return f"assert {_q(exp)} in page.url, page.url"
    if action == "count":
        try:
            n = int(exp)
        except (TypeError, ValueError):
            return None
        return f"expect(page.locator({_q(sel)})).to_have_count({n})"
    return None


# -- Generator ----------------------------------------------------------------

HEADER = '''# AUTO-GENERATED — NICHT von Hand editieren (re-generieren: klickdummy-gen-e2e).
# Quelle: {spec_id} v{spec_version}  ({spec_rel})
# Spec-SHA256: {sha}  ·  platform:ADR-211 §Parity-Off-Ramp (I3-Gate)
# Deterministisch aus der Spec — KEIN Zeitstempel im File (sonst rauscht der
# Drift-Check `klickdummy-parity-drift`). Lauf-Metadaten stehen im Manifest.
#
# DUAL-RENDERER: dieselbe Assertion gegen Renderer #1 (Klickdummy) UND #2 (App).
# Env renderer-neutral benannt — die Suite überlebt den Klickdummy-Sunset:
#   SPEC_RENDERER_BASE_URL=http://localhost:8000 pytest {this}   # Renderer #1 (Klickdummy)
#   SPEC_RENDERER_BASE_URL=https://app.example   pytest {this}   # Renderer #2 (echte App)
# Parity-grün gegen #2 ⇒ Screen darf aus statischer Quelle (off_ramp_status: parity-green).
import os

import pytest
from playwright.sync_api import Page, expect

BASE = os.environ.get("SPEC_RENDERER_BASE_URL", "http://localhost:8000").rstrip("/")
'''


# Stabile, fachliche Test-Anker statt fragiler CSS-/Text-Pfade (REC-6/M28-3).
STABLE_SELECTOR_HINTS = ("data-testid", "data-test", "data-acceptance-id", "data-qa")


def is_fragile_selector(sel) -> bool:
    """True, wenn ein Selektor an UI-Implementierungsdetails statt an einem
    stabilen `data-*`-Anker hängt — Wartungs-/Drift-Risiko (AD-7/AD-8)."""
    if not sel:
        return False
    return not any(h in str(sel) for h in STABLE_SELECTOR_HINTS)


def _gen_version() -> str:
    try:
        from iil_klickdummy import __version__
        return __version__
    except Exception:                              # noqa: BLE001
        return "0.0.0+unknown"


def gen_suite(spec: dict, spec_path: pathlib.Path, this_name: str) -> tuple[str, dict]:
    """Returns (file_text, stats).

    stats = {executable, skipped, skipped_detail[], fragile_selectors[]} —
    Coverage-/Skip-Transparenz (REC-4/REC-14) statt verstecktem Schein-Grün.
    """
    spec_id = spec.get("spec_id", "spec")
    ver = spec.get("spec_version", "?")
    screens = spec.get("screens", []) or []

    sha = hashlib.sha256(spec_path.read_bytes()).hexdigest()
    header = HEADER.format(
        spec_id=spec_id, spec_version=ver, spec_rel=spec_path.name,
        sha=sha, this=this_name,
    )
    n_exec = 0
    skipped: list[dict] = []
    fragile: list[dict] = []
    # Top-Level-Blöcke (Kommentar an erste Screen-Funktion attached); am Ende mit
    # genau zwei Leerzeilen verbunden ⇒ `ruff format`-konform (Adopter-CI grün).
    blocks: list[str] = []

    for sc in screens:
        sid = sc.get("id", "screen")
        stitle = sc.get("title", sid)
        route = screen_route(sc)
        screen_comment = f"# ── Screen: {sid} · {stitle}  (route {route}) ──"
        pas = sc.get("parity_acceptance", []) or []
        if not pas:
            blocks.append(f"{screen_comment}\n# (keine parity_acceptance im Screen {sid})")
            continue
        first = True
        for pa in pas:
            acc_id = pa.get("id", "check")
            check = str(pa.get("check", "")).replace('"""', "'''")
            fn = f"test_{ident(sid)}__{ident(acc_id)}"
            prefix = f"{screen_comment}\n" if first else ""
            first = False
            a = pa.get("assert")
            line = render_assertion(a)
            if line is None:
                skipped.append({"screen": sid, "id": acc_id, "check": pa.get("check", "")})
                blocks.append(
                    f'{prefix}@pytest.mark.skip(reason="kein ausführbares `assert` — Prosa-Parity")\n'
                    f"def {fn}(page: Page):\n"
                    f'    """[{sid}] {check}"""\n'
                    f"    page.goto(BASE + {_q(route)})\n"
                    f"    # TODO: `assert`-Block in der Spec ergänzen (action/selector/expect),\n"
                    f"    #       um diese Parity ausführbar zu machen."
                )
            else:
                n_exec += 1
                if isinstance(a, dict) and is_fragile_selector(a.get("selector")):
                    fragile.append({"screen": sid, "id": acc_id, "selector": a.get("selector")})
                blocks.append(
                    f"{prefix}def {fn}(page: Page):\n"
                    f'    """[{sid}] {check}"""\n'
                    f"    page.goto(BASE + {_q(route)})\n"
                    f"    {line}"
                )

    # header endet mit '\n' nach BASE; '\n\n' davor ⇒ zwei Leerzeilen vor dem
    # ersten Block; Blöcke mit '\n\n\n' (zwei Leerzeilen) verbunden; ein \n am Ende.
    body = (header + "\n\n" + "\n\n\n".join(blocks) + "\n") if blocks else header + "\n"
    stats = {
        "executable": n_exec,
        "skipped": len(skipped),
        "skipped_detail": skipped,
        "fragile_selectors": fragile,
    }
    return body, stats


# -- Main ---------------------------------------------------------------------

def main(argv: list[str]) -> int:
    if not argv:
        print("Usage: klickdummy-gen-e2e <spec.yaml> [<out-file>]")
        return 2
    spec_path = pathlib.Path(argv[0])
    spec = load_spec(spec_path)
    stem = re.sub(r"[^0-9a-z]+", "_", spec_path.stem.lower()).strip("_") or "spec"
    if len(argv) > 1:
        out = pathlib.Path(argv[1])
    else:
        out = spec_path.parent / "tests" / f"test_parity_{stem}.py"

    text, stats = gen_suite(spec, spec_path, out.name)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text, encoding="utf-8")

    n_exec = stats["executable"]
    n_prose = stats["skipped"]
    total = n_exec + n_prose

    # Manifest: reproduzierbarer Beleg (Spec-Hash, Generator-Version, Coverage,
    # Skip-Detail). M28-2/REC-12 + Coverage-Transparenz REC-4/REC-14.
    manifest = {
        "spec_id": spec.get("spec_id"),
        "spec_version": spec.get("spec_version"),
        "spec_schema_version": spec.get("spec_schema_version"),
        "spec_sha256": hashlib.sha256(spec_path.read_bytes()).hexdigest(),
        "generator": "klickdummy-gen-e2e",
        "generator_version": _gen_version(),
        "generated": date.today().isoformat(),
        "base_url_env": "SPEC_RENDERER_BASE_URL",
        "out_file": out.name,
        "parity_checks": total,
        "executable": n_exec,
        "skipped": n_prose,
        "skipped_detail": stats["skipped_detail"],
        "fragile_selectors": stats["fragile_selectors"],
        "uncovered_note": (
            "NFR/Security/Accessibility/Performance/Audit sind NICHT aus "
            "parity_acceptance.assert ableitbar — separat führen "
            "(platform:ADR-211 Requirements-Bridge-Asymmetrie)."
        ),
    }
    manifest_path = out.with_suffix(".manifest.json")
    manifest_path.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    print("== Generate E2E Parity-Suite ==")
    print(f"  Spec     : {spec_path}")
    print(f"  Out      : {out}")
    print(f"  Manifest : {manifest_path}")
    print(f"  Parity-Checks: {total}  ·  ausführbar: {n_exec}  ·  nur-Prosa (skip): {n_prose}")
    if n_prose:
        print(f"  ⚠ {n_prose} Check(s) ohne `assert`-Block bleiben als skip sichtbar (Skip-Debt).")
    if stats["fragile_selectors"]:
        print(f"  ⚠ {len(stats['fragile_selectors'])} fragile(r) Selektor(en) ohne data-* Anker "
              f"(REC-6) — UI-Refactor-Risiko.")
    print("  Dual-Renderer: SPEC_RENDERER_BASE_URL umschalten (Renderer #1 ↔ #2).")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))


def main_cli() -> int:
    """Console-Script entry (pyproject.toml [project.scripts])."""
    return main(sys.argv[1:])

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

`assert.selector` akzeptiert ein optionales Präfix-Vokabular (F23/D2,
KONZ-iil-klickdummy-007): `testid=…`, `role=…[name=…]`, `label=…`, `text=…`
wählen die passende Playwright-Locator-API; ohne Präfix bleibt der String ein
CSS-Selektor (`page.locator`) und wird als fragil markiert. Das ist ein
**Parser mit definiertem Fehlerverhalten** (REC-2/AD-2), keine lose String-
Konvention: unbekanntes Präfix (`rol=…`) oder ungültige `role=`-Syntax (leerer
Wert, fehlende `]`) → Fallthrough auf CSS + benannter Manifest-Hint, nie
Exception; Leerzeichen/Sonderzeichen im `name=`-Wert sind gültig (Quoting via
json.dumps).

Aufruf:
    klickdummy-gen-e2e <spec.yaml> [<out-file>] [--strict-selectors]
    # Default out-file: <spec-dir>/tests/test_parity_<spec-stem>.py
    # --strict-selectors: fragile Selektoren werden zum Fehler (exit 3) statt
    #   nur zur Manifest-Warnung — für den Off-Ramp-Pfad (F23/D1).
    # Alternativ deklariert die Spec selbst `strict_selectors: true` (Top-Level,
    # REC-1/AD-1): Enforcement hängt dann nicht an CI-Configs/Makefiles, die das
    # CLI-Flag vergessen können. CLI-Flag ODER Spec-Attribut genügt.

Exit: 0 ok, 1 Spec-Fehler, 2 Setup-Fehler, 3 Off-Ramp-Gate (fragile Selektoren
mit --strict-selectors bzw. Spec-Attribut `strict_selectors: true`).
"""

from __future__ import annotations

import hashlib
import json
import pathlib
import re
import sys

try:
    import yaml
except ImportError:
    print("FAIL (setup): PyYAML fehlt. pip install pyyaml")
    sys.exit(2)

# validate_spec/_load_schema sind nach read_model.py gewandert (AD-6/#103):
# genesor/scan.py braucht denselben Validierungs-Helfer, ohne ihn zu duplizieren.
from .read_model import validate_spec  # noqa: E402
from .read_model import _load_schema  # noqa: E402,F401 (Re-Export, s. test_gen_e2e.py M28-3-Cache-Test)
from .read_model import load_spec_yaml  # noqa: E402 (A-04: konsolidierter Loader)


# -- Helpers ------------------------------------------------------------------


def ident(s: str) -> str:
    """Python-sicherer Bezeichner-Fragment (für Testfunktionsnamen)."""
    out = re.sub(r"[^0-9a-zA-Z]+", "_", str(s)).strip("_").lower()
    return out or "x"


def load_spec(path: pathlib.Path) -> dict:
    if not path.exists():
        print(f"FAIL: Spec fehlt: {path}")
        sys.exit(1)
    try:
        spec = load_spec_yaml(path) or {}
    except yaml.YAMLError as exc:
        print(f"FAIL: Spec-YAML ungültig ({path}): {exc}")
        sys.exit(1)
    if not isinstance(spec, dict):
        print(f"FAIL: Spec-Top-Level ist kein Mapping ({path})")
        sys.exit(1)
    # Vertrauensgrenze: gegen Schema validieren, BEVOR irgendein Wert in
    # generierten Code eingebettet wird (B-1, platform:ADR-211 §I1-Spec-Schema).
    errors = validate_spec(spec)
    if errors:
        print(f"FAIL: Spec verletzt screens-spec.schema.json ({path}):")
        for e in errors:
            print(f"  ✗ {e}")
        sys.exit(1)
    return spec


_PARAM_PATTERN = re.compile(r"<[^>]+>")


def screen_route(sc: dict) -> tuple[str, bool]:
    """Gibt (url, is_parametrised) zurück.

    Bevorzugt `route_example` (konkrete URL mit echten IDs) vor `route`.
    Gibt `is_parametrised=True`, wenn `route` Django-Parameter enthält
    (`<uuid:pk>` etc.) und kein `route_example` gesetzt ist — der Caller
    erzeugt dann einen skip statt einer 404-URL.
    """
    example = sc.get("route_example")
    if example:
        r = str(example)
        return (r if r.startswith("/") else "/" + r), False
    r = sc.get("route")
    if r:
        full = r if r.startswith("/") else "/" + r
        return full, bool(_PARAM_PATTERN.search(full))
    return "/" + str(sc.get("id", "")), False


# -- Assertion-Vokabular ------------------------------------------------------
# Bewusst klein & standard-nah gehalten (Playwright sync_api). Ein `assert`-Block
# ist {action, selector?, expect?}. Unbekannte/fehlende action ⇒ nur-Prosa.


def _q(s) -> str:
    """Double-quoted Python-String-Literal — `ruff format`-konform (nicht `repr`,
    das Single-Quotes liefert und Adopter mit `ruff format --check` rot macht)."""
    return json.dumps(str(s), ensure_ascii=False)


def _comment_safe(s) -> str:
    """Ein Spec-Wert, der roh in eine `#`-Kommentarzeile eingebettet wird, darf
    NIE aus dieser Zeile ausbrechen (RCE-Härtung B-1). Ein `\\n` im Wert würde
    sonst eine aktive Python-Zeile öffnen, die bei `pytest`-collect läuft — noch
    VOR dem `importorskip`. Deshalb: jeden Whitespace-Lauf (inkl. Zeilenumbruch
    und Carriage-Return) zu genau einem Space kollabieren."""
    return re.sub(r"\s+", " ", str(s)).strip()


def _doc_safe(s) -> str:
    """Spec-Wert, der roh in einen `\"\"\"`-Docstring eingebettet wird, härten
    (B-1/B-2): Whitespace/Zeilenumbrüche kollabieren, `\"\"\"` neutralisieren und
    einen trailing Backslash entfernen — sonst escaped er die schließende Quote
    und die Folgezeile wird ausführbarer Code.

    AD-2: ein Wert, der auf `"` endet, stößt sonst an das schließende `\"\"\"`
    (`…\"` + `\"\"\"` = `\"\"\"\"` → unterminated string / SyntaxError). Daher nach
    dem Backslash-Strip auch ein trailing `\"` entschärfen (ein Space anhängen —
    innerhalb des Docstrings unsichtbar, aber die Quote-Adjacency ist gebrochen)."""
    out = re.sub(r"\s+", " ", str(s)).replace('"""', "'''").rstrip("\\")
    if out.endswith('"'):
        out += " "
    return out


# Semantischer Selektor-Fallback (KONZ-iil-klickdummy-007, F23/D2): ein optionales
# Präfix im `selector`-String wählt die passende Playwright-Locator-API, OHNE das
# Schema zu brechen (`selector` bleibt ein `string`). `testid=`/`role=`/`label=`
# sind stabile Anker (data-testid bzw. Accessibility-Tree); `text=` ist der
# i18n-fragile letzte Ausweg; ein präfixloser String bleibt CSS via `page.locator`.
_ROLE_PATTERN = re.compile(r"^([A-Za-z]+)(?:\[name=(.+)\])?$")


def _locator_expr(sel) -> str:
    """Playwright-Locator-Ausdruck (ohne `.first`/`expect`) für einen Selektor.

    Präfix-Vokabular (F23/D2): `testid=`→`get_by_test_id`, `role=`→`get_by_role`
    (optional `role=button[name=Speichern]`), `label=`→`get_by_label`,
    `text=`→`get_by_text`. Ohne Präfix: `page.locator(sel)` (CSS, fragil)."""
    s = str(sel)
    if s.startswith("testid="):
        return f"page.get_by_test_id({_q(s.removeprefix('testid='))})"
    if s.startswith("label="):
        return f"page.get_by_label({_q(s.removeprefix('label='))})"
    if s.startswith("text="):
        return f"page.get_by_text({_q(s.removeprefix('text='))})"
    if s.startswith("role="):
        m = _ROLE_PATTERN.match(s.removeprefix("role="))
        if m:
            role, name = m.group(1), m.group(2)
            if name:
                return f"page.get_by_role({_q(role)}, name={_q(name)})"
            return f"page.get_by_role({_q(role)})"
    return f"page.locator({_q(s)})"


def render_assertion(a: dict) -> str | None:
    """Eine Playwright-Assertion-Zeile oder None (= nicht ausführbar)."""
    if not isinstance(a, dict):
        return None
    action = str(a.get("action", "")).strip()
    sel = a.get("selector", "")
    exp = a.get("expect", "")
    loc = _locator_expr(sel)
    # Einzelelement-State-Asserts nutzen `.first`: ein Parity-Kontrakt-Selektor
    # (z.B. data-testid pro Tabellenzeile) matcht legitim mehrfach; ohne `.first`
    # bricht Playwrights Strict-Mode ("resolved to N elements"). Existenz-/State-
    # Prüfung ≠ Eindeutigkeit — Kardinalität deckt `count` separat ab.
    if action == "visible":
        return f"expect({loc}.first).to_be_visible()"
    if action == "text":
        return f"expect({loc}.first).to_contain_text({_q(exp)})"
    if action == "clickable":
        # I2-Geist: kein toter Link — Element sichtbar UND bedienbar.
        return f"expect({loc}.first).to_be_enabled()"
    if action == "url":
        return f"assert {_q(exp)} in page.url, page.url"
    if action == "count":
        try:
            n = int(exp)
        except (TypeError, ValueError):
            return None
        return f"expect({loc}).to_have_count({n})"
    return None


# -- Generator ----------------------------------------------------------------

HEADER = """# AUTO-GENERATED — NICHT von Hand editieren (re-generieren: klickdummy-gen-e2e).
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
#
# WICHTIG — Drift-Check ≠ Parität: `make klickdummy-parity-drift` prüft NUR, ob diese
# Datei zur Spec passt (re-gen + diff). Es FÜHRT diese Assertions NICHT aus und belegt
# KEINE Parität. Parität entsteht erst, wenn diese Suite mit pytest + playwright gegen
# einen laufenden SPEC_RENDERER_BASE_URL läuft; „gegen Renderer #2" setzt eine echte,
# erreichbare App-Route voraus — fehlt sie, ist „Dual-Renderer" nur Renderer #1.
import os

import pytest

# Adopter ohne installiertes playwright überspringen die Suite, statt beim
# Sammeln zu brechen (T-01). Schützt CI ohne `testpaths`-Isolation (risk-hub
# #146 entging dem nur per Zufall) — platform:ADR-211 §Executable-Parity-Bridge.
pytest.importorskip("playwright")

from playwright.sync_api import Page, expect  # noqa: E402

BASE = os.environ.get("SPEC_RENDERER_BASE_URL", "http://localhost:8000").rstrip("/")
"""


# Stabile, fachliche Test-Anker statt fragiler CSS-/Text-Pfade (REC-6/M28-3).
STABLE_SELECTOR_HINTS = ("data-testid", "data-test", "data-acceptance-id", "data-qa")
# Stabile Selektor-Präfixe (F23/D2): `testid=` = data-testid-Kontrakt, `role=`/
# `label=` = Accessibility-Tree-Anker. `text=` zählt bewusst NICHT als stabil
# (i18n-/Wording-Drift) — es bleibt der markierte Fallback.
STABLE_SELECTOR_PREFIXES = ("testid=", "role=", "label=")


def is_fragile_selector(sel) -> bool:
    """True, wenn ein Selektor an UI-Implementierungsdetails statt an einem
    stabilen Anker hängt — Wartungs-/Drift-Risiko (AD-7/AD-8). Stabil sind
    data-*-Attribute (CSS) und die semantischen Präfixe testid=/role=/label=
    (F23/D2); bare CSS und text= bleiben fragil.

    Wichtig: role= ist nur stabil, wenn _ROLE_PATTERN matched. Ein Wert wie
    `role=123button` startet mit "role=", aber der Parser degradiert auf
    page.locator() — ohne diesen Check würde er fälschlich als stabil gelten."""
    if not sel:
        return False
    s = str(sel)
    if s.startswith("testid=") or s.startswith("label="):
        return False
    if s.startswith("role="):
        return _ROLE_PATTERN.match(s.removeprefix("role=")) is None
    if s.startswith(("text=",)):
        return True
    return not any(h in s for h in STABLE_SELECTOR_HINTS)


# Präfix-Parser mit definiertem Fehlerverhalten (REC-2/AD-2): kein silenter
# Fail, keine Exception — ein nicht parsebares Präfix fällt IMMER auf CSS
# (`page.locator`) zurück und wird hier als benannter Hint sichtbar gemacht.
_PREFIX_LIKE = re.compile(r"^([A-Za-z][A-Za-z0-9_-]*)=")
_KNOWN_PREFIXES = ("testid", "role", "label", "text")


def selector_fallthrough_hint(sel) -> str | None:
    """Benennt, WARUM ein präfix-artiger Selektor auf CSS zurückfällt — oder None.

    Deckt die zwei Fehlerklassen der Mini-DSL ab (REC-2): (a) unbekanntes
    Präfix (Tippfehler wie `rol=`), (b) `role=` mit ungültiger Syntax (leerer
    Wert, fehlende schließende `]`). Beides sind legitime CSS-Selektoren aus
    Playwright-Sicht — aber fast immer Spec-Autor-Fehler, daher Warnung statt
    silentem Fallthrough. Bare CSS ohne `<wort>=`-Form gibt None (kein Hint)."""
    s = str(sel or "")
    m = _PREFIX_LIKE.match(s)
    if not m:
        return None
    prefix = m.group(1)
    if prefix == "role":
        if _ROLE_PATTERN.match(s.removeprefix("role=")) is None:
            return (
                "role=-Syntax ungültig (erwartet: role=<rolle> oder "
                "role=<rolle>[name=…]) — Fallthrough auf CSS (page.locator)"
            )
        return None
    if prefix not in _KNOWN_PREFIXES:
        return (
            f"unbekanntes Präfix '{prefix}=' (bekannt: testid=, role=, label=, "
            f"text=) — Fallthrough auf CSS (page.locator); Tippfehler?"
        )
    return None


def _gen_version() -> str:
    try:
        from iil_klickdummy import __version__

        return __version__
    except Exception:  # noqa: BLE001
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
        spec_id=spec_id,
        spec_version=ver,
        spec_rel=spec_path.name,
        sha=sha,
        this=this_name,
    )
    n_exec = 0
    skipped: list[dict] = []
    fragile: list[dict] = []
    # Top-Level-Blöcke (Kommentar an erste Screen-Funktion attached); am Ende mit
    # genau zwei Leerzeilen verbunden ⇒ `ruff format`-konform (Adopter-CI grün).
    blocks: list[str] = []

    # Auth-Fixture (optional): erzeugt Fixture wenn Spec einen `auth`-Block hat.
    # Playwright lädt einen storage_state NUR bei Context-Erzeugung — es gibt KEINE
    # `context.set_storage_state(path=...)`-API (das war ein nie ausgeführter Bug:
    # gegen einen echten login_required-Renderer-#2 lief die Suite zuvor nie).
    # Korrekt: das pytest-playwright-Fixture `browser_context_args` überschreiben,
    # damit der `page`-Context vor-authentifiziert startet.
    spec_auth = spec.get("auth") or {}
    auth_blocks: list[str] = []
    if spec_auth:
        storage = spec_auth.get("storage_state")
        login_fixture = spec_auth.get("login_fixture")
        if storage:
            auth_blocks.append(
                f'@pytest.fixture(scope="session")\n'
                f"def browser_context_args(browser_context_args):\n"
                f'    """Auth via storage_state aus Spec-Block — pytest-playwright lädt\n'
                f'    den State bei Context-Erzeugung (einzige funktionierende API)."""\n'
                f'    return {{**browser_context_args, "storage_state": {_q(storage)}}}'
            )
        elif login_fixture:
            # `login_fixture` wird als Funktions-Parametername emittiert — auf
            # einen sicheren Python-Bezeichner zwingen, sonst injiziert ein
            # bösartiger Name ausführbaren Code in die Signatur (B-1).
            fixture_ident = ident(login_fixture)
            auth_blocks.append(
                f"@pytest.fixture(autouse=True)\n"
                f"def _auth({fixture_ident}: Page):\n"
                f'    """Auth via Login-Fixture `{_doc_safe(login_fixture)}` aus Spec-Block."""\n'
                f"    pass  # Fixture übernimmt Login"
            )

    for sc in screens:
        sid = sc.get("id", "screen")
        stitle = sc.get("title", sid)
        route, is_parametrised = screen_route(sc)
        # Alle drei Werte kommen aus der Spec (Vertrauensgrenze) und landen roh in
        # einer `#`-Kommentarzeile — kollabieren, damit kein `\n` ausbricht (B-1).
        screen_comment = (
            f"# ── Screen: {_comment_safe(sid)} · {_comment_safe(stitle)}  "
            f"(route {_comment_safe(route)}) ──"
        )

        # Auth-Pflicht: `login_required` in Spec + kein auth-Block → alle Checks skip
        login_required = sc.get("login_required", False) or spec_auth.get(
            "required", False
        )
        auth_missing = login_required and not spec_auth

        pas = sc.get("parity_acceptance", []) or []
        if not pas:
            blocks.append(
                f"{screen_comment}\n# (keine parity_acceptance im Screen {sid})"
            )
            continue
        first = True
        for pa in pas:
            acc_id = pa.get("id", "check")
            # `check` ist ein freier Spec-String und landet roh im Docstring —
            # gegen `"""`-Ausbruch UND trailing `\`-Quote-Escape härten (B-1/B-2).
            check = _doc_safe(pa.get("check", ""))
            fn = f"test_{ident(sid)}__{ident(acc_id)}"
            prefix = f"{screen_comment}\n" if first else ""
            first = False

            # Skip-Grund bestimmen (Priorität: parametrisiert > login_required > kein assert)
            if is_parametrised:
                skip_reason = (
                    f"parametrisierte Route {route} — bitte `route_example` in der Spec "
                    f"ergänzen (konkrete URL mit echten IDs/UUIDs)"
                )
                skipped.append(
                    {
                        "screen": sid,
                        "id": acc_id,
                        "check": pa.get("check", ""),
                        "skip_reason": "parametrised_route",
                    }
                )
                blocks.append(
                    f"{prefix}@pytest.mark.skip(reason={_q(skip_reason)})\n"
                    f"def {fn}(page: Page):\n"
                    f'    """[{sid}] {check}"""\n'
                    f"    pass  # route_example fehlt — würde 404 produzieren"
                )
                continue

            if auth_missing:
                skip_reason = (
                    f"login_required=True für Screen {sid} — "
                    f"bitte `auth`-Block in der Spec ergänzen (storage_state oder login_fixture)"
                )
                skipped.append(
                    {
                        "screen": sid,
                        "id": acc_id,
                        "check": pa.get("check", ""),
                        "skip_reason": "login_required_no_auth",
                    }
                )
                blocks.append(
                    f"{prefix}@pytest.mark.skip(reason={_q(skip_reason)})\n"
                    f"def {fn}(page: Page):\n"
                    f'    """[{sid}] {check}"""\n'
                    f"    pass  # auth-Setup fehlt — kein Login möglich"
                )
                continue

            a = pa.get("assert")
            line = render_assertion(a)
            if line is None:
                skipped.append(
                    {
                        "screen": sid,
                        "id": acc_id,
                        "check": pa.get("check", ""),
                        "skip_reason": "no_assert",
                    }
                )
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
                    entry = {"screen": sid, "id": acc_id, "selector": a.get("selector")}
                    # REC-2: Fallthrough der Präfix-Mini-DSL benennen (Tippfehler-
                    # Präfix / kaputte role=-Syntax) statt nur "fragil" zu sagen.
                    hint = selector_fallthrough_hint(a.get("selector"))
                    if hint:
                        entry["hint"] = hint
                    fragile.append(entry)
                blocks.append(
                    f"{prefix}def {fn}(page: Page):\n"
                    f'    """[{sid}] {check}"""\n'
                    f"    page.goto(BASE + {_q(route)})\n"
                    f"    {line}"
                )

    # header endet mit '\n' nach BASE; '\n\n' davor ⇒ zwei Leerzeilen vor dem
    # ersten Block; Blöcke mit '\n\n\n' (zwei Leerzeilen) verbunden; ein \n am Ende.
    all_blocks = auth_blocks + blocks
    body = (
        (header + "\n\n" + "\n\n\n".join(all_blocks) + "\n")
        if all_blocks
        else header + "\n"
    )
    stats = {
        "executable": n_exec,
        "skipped": len(skipped),
        "skipped_detail": skipped,
        "fragile_selectors": fragile,
    }
    return body, stats


# -- Main ---------------------------------------------------------------------


def main(argv: list[str]) -> int:
    positional = [a for a in argv if not a.startswith("--")]
    if not positional:
        print("Usage: klickdummy-gen-e2e <spec.yaml> [<out-file>] [--strict-selectors]")
        return 2
    spec_path = pathlib.Path(positional[0])
    spec = load_spec(spec_path)
    # Off-Ramp-Gate (F23/D1): fragile Selektoren werden zum harten Fehler (exit 3)
    # statt nur zur Manifest-Warnung. Zwei gleichwertige Aktivierungswege (OR):
    # CLI-Flag `--strict-selectors` (der Off-Ramp-Pfad setzt es pro Lauf) ODER
    # Spec-Attribut `strict_selectors: true` (REC-1/AD-1: spec-deklariert, damit
    # ein vergessenes Flag in CI-Configs das Gate nicht stumm schaltet).
    strict_selectors = "--strict-selectors" in argv or bool(
        spec.get("strict_selectors", False)
    )
    stem = re.sub(r"[^0-9a-z]+", "_", spec_path.stem.lower()).strip("_") or "spec"
    if len(positional) > 1:
        out = pathlib.Path(positional[1])
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
        "base_url_env": "SPEC_RENDERER_BASE_URL",
        "out_file": out.name,
        "parity_checks": total,
        "executable": n_exec,
        "skipped": n_prose,
        "skipped_detail": stats["skipped_detail"],
        "fragile_selectors": stats["fragile_selectors"],
        "strict_selectors": strict_selectors,
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
    print(
        f"  Parity-Checks: {total}  ·  ausführbar: {n_exec}  ·  nur-Prosa (skip): {n_prose}"
    )
    if n_prose:
        print(
            f"  ⚠ {n_prose} Check(s) ohne `assert`-Block bleiben als skip sichtbar (Skip-Debt)."
        )
    n_fragile = len(stats["fragile_selectors"])
    if n_fragile:
        print(
            f"  ⚠ {n_fragile} fragile(r) Selektor(en) ohne stabilen Anker "
            f"(REC-6/F23) — bare CSS/text=; testid=/role=/label= bevorzugen."
        )
        # REC-2: Präfix-Parser-Fallthroughs (Tippfehler/kaputte Syntax) explizit
        # benennen — die sehen wie DSL aus, laufen aber als CSS.
        for f in stats["fragile_selectors"]:
            if f.get("hint"):
                print(f"    ↳ {f['screen']}/{f['id']} `{f['selector']}`: {f['hint']}")
    print("  Dual-Renderer: SPEC_RENDERER_BASE_URL umschalten (Renderer #1 ↔ #2).")
    # F23/D1: am Off-Ramp ist ein fragiler Selektor kein bloßer Hinweis mehr.
    if strict_selectors and n_fragile:
        print(
            f"  ✗ strict-selectors (CLI-Flag oder Spec-Attribut): {n_fragile} fragile(r) "
            f"Selektor(en) → Off-Ramp-Gate ROT (exit 3). Auf stabilen Anker umstellen."
        )
        return 3
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))


def main_cli() -> int:
    """Console-Script entry (pyproject.toml [project.scripts])."""
    return main(sys.argv[1:])

#!/usr/bin/env python3
"""Story-Validierung — story.yaml gegen Schema + step.kd-Auflösung (Fail-Fast).

KONZ-iil-klickdummy-004 (A3): macht den bisherigen render-zeitigen Silent-Skip
(registry.discover_stories warnt nur auf stderr) zu einem harten Build-Gate.

Aufruf:  klickdummy-stories [<repo_root>]      (Default: cwd)
Scope:   <repo_root>/klickdummy/stories/*.yaml|*.yml
Exit:    0 = PASS (oder kein stories/-Verzeichnis), 1 = FAIL, 2 = Setup-Fehler
Policy:  ~/.claude/policies/klickdummy.md · platform:ADR-211 §Story-Navigation
"""
from __future__ import annotations

import json
import pathlib
import sys
from importlib.resources import files

try:
    import yaml  # PyYAML
except ImportError:
    print("FAIL (setup): PyYAML fehlt. pip install pyyaml")
    sys.exit(2)

try:
    import jsonschema
except ImportError:
    print("FAIL (setup): jsonschema fehlt. pip install jsonschema")
    sys.exit(2)


def _load_schema() -> dict:
    text = (files("iil_klickdummy") / "schemas" / "story.schema.json").read_text(encoding="utf-8")
    return json.loads(text)


def validate_stories(repo_root: pathlib.Path) -> list[str]:
    """Validiert alle story.yaml gegen Schema + löst step.kd gegen KD-Liste auf.

    Gibt eine Liste von Fehler-Strings zurück (leer = alles ok). Kein
    stories/-Verzeichnis → leere Liste (rückwärtskompatibel, wie discover_stories).
    """
    from iil_klickdummy.registry import discover_klickdummies

    stories_dir = repo_root / "klickdummy" / "stories"
    if not stories_dir.exists():
        return []

    schema = _load_schema()
    kd_names = {k.name for k in discover_klickdummies(repo_root)}
    errors: list[str] = []
    paths = sorted(stories_dir.glob("*.yaml")) + sorted(stories_dir.glob("*.yml"))
    if not paths:
        return []

    for p in paths:
        rel = p.name
        try:
            raw = yaml.safe_load(p.read_text(encoding="utf-8"))
        except Exception as e:  # noqa: BLE001
            errors.append(f"{rel}: nicht ladbar ({type(e).__name__}: {e})")
            continue
        if not isinstance(raw, dict):
            errors.append(f"{rel}: Top-Level ist kein Mapping")
            continue
        # Schema
        for e in sorted(jsonschema.Draft7Validator(schema).iter_errors(raw),
                        key=lambda x: list(x.absolute_path)):
            loc = "/".join(str(x) for x in e.absolute_path) or "(root)"
            errors.append(f"{rel} @ {loc}: {e.message}")
        # step.kd-Auflösung (nur wenn steps strukturell ok sind)
        for i, step in enumerate(raw.get("steps") or []):
            if isinstance(step, dict) and step.get("kd") and step["kd"] not in kd_names:
                errors.append(f"{rel} @ steps/{i}: kd={step['kd']!r} ist kein bekannter Klickdummy")
    return errors


def main(argv: list[str]) -> int:
    repo_root = pathlib.Path(argv[0]).resolve() if argv else pathlib.Path.cwd()
    print(f"== Story-Validierung == ({repo_root}/klickdummy/stories)")
    errors = validate_stories(repo_root)
    if not errors:
        print("Story → PASS")
        return 0
    for e in errors:
        print(f"  ✗ {e}")
    print(f"Story → FAIL ({len(errors)})")
    return 1


def main_cli() -> int:
    """Console-Script entry (pyproject.toml [project.scripts])."""
    return main(sys.argv[1:])


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

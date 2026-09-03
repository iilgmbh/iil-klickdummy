#!/usr/bin/env python3
"""klickdummy-tokens — design-hub-Profil (YAML) → CSS-Custom-Properties.

Liest ein design-hub-Profil (`profiles/<slug>.yaml`, Schema siehe
`design-hub/profiles/_SCHEMA.md`) und erzeugt eine deterministische
`tokens.css`, damit Klickdummies dasselbe Corporate Design wie print_agent/
decks-hub nutzen (Source of Truth = design-hub, nicht der Klickdummy selbst).

Kontext: achimdehnert/dev-hub#320 (Klickdummies im Kunden-Design).

Aufruf:
    klickdummy-tokens --profile design-hub/profiles/meiki-lra.yaml --out tokens.css
    klickdummy-tokens --profile ... --out tokens.css --check   # nur vergleichen

Exit-Codes:
    0 — Erfolg (bzw. --check: Datei ist aktuell)
    1 — --check: Datei fehlt oder weicht ab
    2 — Profil-Fehler (Pflichtschlüssel fehlt / ungültiger Farbwert)
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Any

import yaml

_COLOR_RE = re.compile(r"^#[0-9A-Fa-f]{6}$")

# Dotted-Path-Notation für verschachtelte Pflichtschlüssel.
_REQUIRED_KEYS = (
    "name",
    "schema_version",
    "fonts.primary",
    "colours.primary",
    "colours.text",
    "colours.bg_light",
    "colours.border",
)

# CSS-generische Font-Familien — werden NICHT gequotet.
_GENERIC_FONT_FAMILIES = {
    "serif",
    "sans-serif",
    "monospace",
    "cursive",
    "fantasy",
    "system-ui",
}


class TokenGenError(Exception):
    """Profil-Fehler (fehlender Pflichtschlüssel / ungültiger Farbwert). CLI: Exit 2."""


def _dig(profile: dict[str, Any], dotted_key: str) -> Any:
    """Löst einen `a.b.c`-Pfad im Profil auf. Fehlt ein Segment oder ist der Wert
    leer (None/""), gilt der Pflichtschlüssel als fehlend (Exit 2)."""
    node: Any = profile
    for part in dotted_key.split("."):
        if not isinstance(node, dict) or part not in node:
            raise TokenGenError(f"Pflichtschlüssel fehlt: {dotted_key!r}")
        node = node[part]
    if node is None or node == "":
        raise TokenGenError(f"Pflichtschlüssel fehlt: {dotted_key!r}")
    return node


def _check_required_keys(profile: dict[str, Any]) -> None:
    for key in _REQUIRED_KEYS:
        _dig(profile, key)


def _quote_font_name(name: str) -> str:
    return name if name in _GENERIC_FONT_FAMILIES else f'"{name}"'


def _font_primary_value(fonts: dict[str, Any]) -> str:
    names = [fonts["primary"], *(fonts.get("fallbacks") or [])]
    return ", ".join(_quote_font_name(n) for n in names)


def _font_mono_value(fonts: dict[str, Any]) -> str | None:
    mono = fonts.get("mono")
    if not mono:
        return None
    return f"{_quote_font_name(mono)}, monospace"


def _colour_lines(colours: dict[str, Any]) -> list[str]:
    lines: list[str] = []
    for key, value in colours.items():
        if not isinstance(value, str) or not _COLOR_RE.match(value):
            raise TokenGenError(
                f"Ungültiger Farbwert bei colours.{key}: {value!r} (erwartet #RRGGBB)"
            )
        css_key = key.replace("_", "-")
        lines.append(f"  --kd-{css_key}: {value};")
    return lines


def generate(profile: dict[str, Any], *, generator_version: str) -> str:
    """Baut den Inhalt von `tokens.css` aus einem geparsten design-hub-Profil.

    Deterministisch: keine Zeitstempel, keine Pfade des ausführenden Rechners.
    Zwei Läufe mit demselben Profil + derselben `generator_version` sind
    byte-gleich.
    """
    _check_required_keys(profile)

    name = profile["name"]
    schema_version = profile["schema_version"]
    fonts = profile["fonts"]
    colours = profile["colours"]

    lines: list[str] = [
        f'/* tokens.css — generiert aus design-hub-Profil "{name}" '
        f"(schema_version {schema_version}) · nicht von Hand editieren */",
        f"/* Generator: iil-klickdummy klickdummy-tokens {generator_version} */",
        ":root {",
        f"  --kd-font-primary: {_font_primary_value(fonts)};",
    ]
    mono_value = _font_mono_value(fonts)
    if mono_value is not None:
        lines.append(f"  --kd-font-mono: {mono_value};")
    lines.extend(_colour_lines(colours))
    lines.append("}")

    colours_dark = profile.get("colours_dark")
    if colours_dark:
        lines.append('[data-theme="dark"] {')
        lines.extend(_colour_lines(colours_dark))
        lines.append("}")

    return "\n".join(lines) + "\n"


def _load_profile(profile_path: Path) -> dict[str, Any]:
    text = profile_path.read_text(encoding="utf-8")
    data = yaml.safe_load(text)
    if not isinstance(data, dict):
        raise TokenGenError(f"Profil ist kein YAML-Mapping: {profile_path}")
    return data


def _generator_version() -> str:
    from iil_klickdummy import __version__

    return __version__


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        prog="klickdummy-tokens",
        description=(
            "Erzeugt eine CSS-Token-Datei aus einem design-hub-Profil (dev-hub#320)."
        ),
    )
    parser.add_argument(
        "--profile", required=True, type=Path, help="Pfad zur design-hub-Profil-YAML"
    )
    parser.add_argument(
        "--out", required=True, type=Path, help="Ziel-Pfad der tokens.css"
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Nichts schreiben — nur gegen die bestehende --out-Datei vergleichen",
    )
    args = parser.parse_args(argv)

    try:
        profile = _load_profile(args.profile)
    except FileNotFoundError:
        print(f"FEHLER: Profil nicht gefunden: {args.profile}", file=sys.stderr)
        return 2
    except yaml.YAMLError as e:
        print(f"FEHLER: Profil ist kein gültiges YAML: {e}", file=sys.stderr)
        return 2

    try:
        css = generate(profile, generator_version=_generator_version())
    except TokenGenError as e:
        print(f"FEHLER: {e}", file=sys.stderr)
        return 2

    if args.check:
        if not args.out.exists():
            print(f"FEHLER (--check): Datei fehlt: {args.out}", file=sys.stderr)
            return 1
        existing = args.out.read_bytes()
        if existing != css.encode("utf-8"):
            print(
                f"FEHLER (--check): {args.out} weicht vom generierten Stand ab "
                "— mit `klickdummy-tokens --profile ... --out ...` neu erzeugen.",
                file=sys.stderr,
            )
            return 1
        print(f"OK — {args.out} ist aktuell.")
        return 0

    args.out.write_text(css, encoding="utf-8")
    print(f"  wrote {args.out}")
    return 0


def main_cli() -> int:
    """Console-Script entry (pyproject.toml [project.scripts])."""
    return main(sys.argv[1:])


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

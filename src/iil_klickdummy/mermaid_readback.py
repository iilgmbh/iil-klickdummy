"""Mermaid-Flow-Readback (KONZ-iil-klickdummy-008, Baustein M3).

Der Struktur-Input-Kanal des Co-Creation-Loops: der Mensch editiert den
Screen-Flow als Mermaid im GitHub-Web-Editor (`_flow.view.md` / `_flow.input.mmd`
auf einem `mmds/`-Branch), sagt „fertig"; dieses Modul liest den Flow via `gh`
zurück und **difft** ihn gegen `screens[].next_screens`/`back_screen` der Spec.

Bewusst **read-only** (nur Diff, kein Auto-Write): die Spec bleibt SoR (KONZ-008,
Mermaid = abgeleitete Sicht, KEIN mmd→Spec-Parser). Der Mensch gießt die Delta
in die Spec. Das Modul frisst KEINEN Mermaid-Text in Codegen — keine RCE-Fläche.

Aufruf:  klickdummy-mermaid-readback <mermaid.(mmd|md)> <spec.yaml>
Exit:    0 = kein Delta (Flow == Spec) · 1 = Delta gefunden · 2 = Setup-Fehler
"""

from __future__ import annotations

import pathlib
import re
import sys

try:
    import yaml
except ImportError:
    print("FAIL (setup): PyYAML fehlt. pip install pyyaml")
    sys.exit(2)

# `A -.label.-> B` (gestrichelt = Rücksprung). VOR der Solid-Prüfung matchen,
# da die gestrichelte Form ebenfalls `->` enthält.
_DOTTED = re.compile(r"([A-Za-z_][\w-]*)\s*-\.[^.]*\.->\s*([A-Za-z_][\w-]*)")
_ARROW = "-->"
_NODE_ID = re.compile(r"^\s*([A-Za-z_][\w-]*)")


def _mermaid_text(path: pathlib.Path) -> str:
    """Roher Mermaid-Text: aus einer `.mmd` direkt, aus einer `.md` der erste
    ```mermaid-Block."""
    text = path.read_text(encoding="utf-8", errors="ignore")
    if path.suffix == ".mmd":
        return text
    m = re.search(r"```mermaid\s*\n(.*?)```", text, re.DOTALL)
    return m.group(1) if m else text


def parse_flow(mermaid: str) -> tuple[set[tuple[str, str]], dict[str, str]]:
    """(next_edges, back_edges). next_edges = {(from, to)} aus Solid-Pfeilen
    (auch verkettet `A --> B --> C`); back_edges = {from: to} aus `-.->`."""
    next_edges: set[tuple[str, str]] = set()
    back_edges: dict[str, str] = {}
    for raw in mermaid.splitlines():
        line = raw.strip()
        if (
            not line
            or line.startswith("%%")
            or line.startswith("flowchart")
            or line.startswith("graph")
        ):
            continue
        dm = _DOTTED.search(line)
        if dm:
            back_edges[dm.group(1)] = dm.group(2)
            continue
        if _ARROW in line:
            # Verkettung: Token zwischen den Pfeilen; je Token die führende ID.
            parts = [p.strip() for p in line.split(_ARROW)]
            ids = []
            for p in parts:
                mm = _NODE_ID.match(p)
                if mm:
                    ids.append(mm.group(1))
            for a, b in zip(ids, ids[1:]):
                next_edges.add((a, b))
    return next_edges, back_edges


def spec_flow(spec: dict) -> tuple[set[tuple[str, str]], dict[str, str]]:
    """Denselben Graph aus der Spec: screens[].next_screens / back_screen."""
    next_edges: set[tuple[str, str]] = set()
    back_edges: dict[str, str] = {}
    for sc in spec.get("screens", []) or []:
        sid = str(sc.get("id", ""))
        for nxt in sc.get("next_screens", []) or []:
            next_edges.add((sid, str(nxt)))
        if sc.get("back_screen"):
            back_edges[sid] = str(sc["back_screen"])
    return next_edges, back_edges


def diff(mermaid: str, spec: dict) -> dict:
    mn, mb = parse_flow(mermaid)
    sn, sb = spec_flow(spec)
    return {
        "next_add": sorted(mn - sn),  # im Mermaid, nicht in Spec → ergänzen
        "next_remove": sorted(sn - mn),  # in Spec, nicht im Mermaid → prüfen/entfernen
        "back_add": sorted((k, v) for k, v in mb.items() if sb.get(k) != v),
        "back_remove": sorted((k, v) for k, v in sb.items() if mb.get(k) != v),
    }


def main(argv: list[str]) -> int:
    positional = [a for a in argv if not a.startswith("--")]
    if len(positional) < 2:
        print("Usage: klickdummy-mermaid-readback <mermaid.(mmd|md)> <spec.yaml>")
        return 2
    mpath, spath = pathlib.Path(positional[0]), pathlib.Path(positional[1])
    try:
        mermaid = _mermaid_text(mpath)
        spec = yaml.safe_load(spath.read_text(encoding="utf-8")) or {}
    except FileNotFoundError as e:
        print(f"FAIL (setup): Datei fehlt: {e.filename}")
        return 2

    d = diff(mermaid, spec)
    total = sum(len(v) for v in d.values())
    print(f"== Mermaid-Readback ==  Flow: {mpath.name}  Spec: {spath.name}")
    if total == 0:
        print("  ✓ Flow == Spec — keine Delta (next_screens/back_screen decken sich).")
        return 0
    print(
        f"  Δ {total} — die Spec ist SoR; diese Delta von Hand einpflegen (kein Auto-Write):"
    )
    for a, b in d["next_add"]:
        print(
            f"      + next: {a} → {b}   (im Mermaid, fehlt in Spec: screens[{a}].next_screens += {b})"
        )
    for a, b in d["next_remove"]:
        print(
            f"      - next: {a} → {b}   (in Spec, nicht im Mermaid: prüfen/entfernen)"
        )
    for a, b in d["back_add"]:
        print(
            f"      + back: {a} ⤺ {b}   (im Mermaid, fehlt/abweichend in Spec: screens[{a}].back_screen = {b})"
        )
    for a, b in d["back_remove"]:
        print(
            f"      - back: {a} ⤺ {b}   (in Spec, nicht im Mermaid: prüfen/entfernen)"
        )
    return 1


def main_cli() -> int:
    return main(sys.argv[1:])


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

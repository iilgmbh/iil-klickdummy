#!/usr/bin/env python3
"""Flow-Kohärenz-Lint — Screen-Flow-DAG (next_screens/voraussetzung_screen) prüfen.

KONZ-iil-klickdummy-004 §Move-2 / UC-Story-Line: der Screen-Flow lebt heute in
``screens[].next_screens`` + ``voraussetzung_screen`` (vom Genesor als
Lineage-Graph gerendert), ist aber **unvalidiert** (nicht im Schema). Dieser
Lint deckt die stille Drift auf: dangling Refs, Vorwärts/Rückwärts-Asymmetrie,
Zyklen, unerreichbare Screens und Flow-Schritte ohne Use-Case.

Aufruf:  klickdummy-flow [<repo_root>]      (Default: cwd)
Scope:   <repo_root>/klickdummy/*/screens-spec.yaml
Exit:    0 = PASS (nur warnings/infos), 1 = FAIL (≥1 error), 2 = Setup-Fehler
Policy:  ~/.claude/policies/klickdummy.md · platform:ADR-211
"""

from __future__ import annotations

import pathlib
import sys

try:
    import yaml  # PyYAML
except ImportError:
    print("FAIL (setup): PyYAML fehlt. pip install pyyaml")
    sys.exit(2)

ERROR, WARNING, INFO = "error", "warning", "info"


def _finding(sev: str, spec: str, code: str, msg: str) -> dict:
    return {"severity": sev, "spec": spec, "code": code, "msg": msg}


def _check_spec(spec_name: str, data: dict) -> list[dict]:
    out: list[dict] = []
    screens = [
        s for s in (data.get("screens") or []) if isinstance(s, dict) and s.get("id")
    ]
    if not screens:
        return out
    ids = {s["id"] for s in screens}
    nexts = {s["id"]: [n for n in (s.get("next_screens") or [])] for s in screens}
    voraus = {s["id"]: s.get("voraussetzung_screen") for s in screens}
    use_cases = {s["id"]: (s.get("use_cases") or []) for s in screens}
    has_flow = any(nexts.values()) or any(voraus.values())

    # 1. dangling Refs (error)
    for sid in ids:
        for n in nexts[sid]:
            if n not in ids:
                out.append(
                    _finding(
                        ERROR,
                        spec_name,
                        "dangling-next",
                        f"{sid}.next_screens → {n!r} ist kein Screen dieser Spec",
                    )
                )
        v = voraus[sid]
        if v and v not in ids:
            out.append(
                _finding(
                    ERROR,
                    spec_name,
                    "dangling-voraus",
                    f"{sid}.voraussetzung_screen → {v!r} ist kein Screen dieser Spec",
                )
            )

    # 2. Vorwärts/Rückwärts-Asymmetrie (warning)
    for sid in ids:
        for n in nexts[sid]:
            if (
                n in ids
                and voraus.get(n) not in (sid, None)
                and sid not in nexts.get(n, [])
            ):
                out.append(
                    _finding(
                        WARNING,
                        spec_name,
                        "edge-asymmetry",
                        f"{sid}.next_screens enthält {n!r}, aber {n}.voraussetzung_screen ≠ {sid}",
                    )
                )
        v = voraus[sid]
        if v in ids and sid not in nexts.get(v, []):
            out.append(
                _finding(
                    WARNING,
                    spec_name,
                    "edge-asymmetry",
                    f"{sid}.voraussetzung_screen={v!r}, aber {v}.next_screens enthält {sid!r} nicht",
                )
            )

    # 3. Zyklus (warning) — DFS über next_screens
    WHITE, GREY, BLACK = 0, 1, 2
    color = {sid: WHITE for sid in ids}

    def dfs(u: str) -> bool:
        color[u] = GREY
        for w in nexts.get(u, []):
            if w not in ids:
                continue
            if color[w] == GREY:
                return True
            if color[w] == WHITE and dfs(w):
                return True
        color[u] = BLACK
        return False

    if has_flow and any(color[sid] == WHITE and dfs(sid) for sid in ids):
        out.append(
            _finding(WARNING, spec_name, "cycle", "next_screens enthält einen Zyklus")
        )

    # 4. nur wenn ein Flow deklariert ist:
    if has_flow:
        targets = {n for ns in nexts.values() for n in ns if n in ids}
        for sid in ids:
            # unerreichbar: kein eingehender next + keine Vorbedingung, aber andere zeigen weg
            if sid not in targets and not voraus.get(sid) and not nexts.get(sid):
                out.append(
                    _finding(
                        INFO,
                        spec_name,
                        "isolated-screen",
                        f"{sid}: weder Ziel noch Quelle einer Flow-Kante (isoliert)",
                    )
                )
            # Flow-Schritt ohne Use-Case
            if (sid in targets or nexts.get(sid)) and not use_cases.get(sid):
                out.append(
                    _finding(
                        WARNING,
                        spec_name,
                        "step-without-uc",
                        f"{sid}: im Flow, aber ohne use_cases (Stringenz-Lücke)",
                    )
                )
    elif len(screens) >= 2:
        out.append(
            _finding(
                INFO,
                spec_name,
                "no-flow",
                f"{len(screens)} Screens, aber kein next_screens/voraussetzung_screen deklariert",
            )
        )
    return out


def validate_flow(repo_root: pathlib.Path) -> list[dict]:
    """Validiert den Screen-Flow aller KD-Specs. Gibt Findings zurück (leer = ok)."""
    base = repo_root / "klickdummy"
    if not base.exists():
        return []
    out: list[dict] = []
    for spec_path in sorted(base.glob("*/screens-spec.yaml")):
        try:
            data = yaml.safe_load(spec_path.read_text(encoding="utf-8"))
        except Exception as e:  # noqa: BLE001
            out.append(
                _finding(
                    ERROR,
                    spec_path.parent.name,
                    "unloadable",
                    f"{type(e).__name__}: {e}",
                )
            )
            continue
        if isinstance(data, dict):
            out.extend(_check_spec(spec_path.parent.name, data))
    return out


def main(argv: list[str]) -> int:
    repo_root = pathlib.Path(argv[0]).resolve() if argv else pathlib.Path.cwd()
    print(f"== Flow-Kohärenz == ({repo_root}/klickdummy/*/screens-spec.yaml)")
    findings = validate_flow(repo_root)
    icon = {ERROR: "✗", WARNING: "⚠", INFO: "·"}
    for f in findings:
        print(f"  {icon[f['severity']]} [{f['spec']}] {f['code']}: {f['msg']}")
    errors = sum(1 for f in findings if f["severity"] == ERROR)
    warns = sum(1 for f in findings if f["severity"] == WARNING)
    print(
        f"Flow → {'PASS' if errors == 0 else f'FAIL ({errors} error)'}"
        + (f" · {warns} warning" if warns else "")
    )
    return 0 if errors == 0 else 1


def main_cli() -> int:
    """Console-Script entry (pyproject.toml [project.scripts])."""
    return main(sys.argv[1:])


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

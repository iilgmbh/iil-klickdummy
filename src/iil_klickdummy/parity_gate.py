"""Parity-Exit-Gate (KONZ-iil-klickdummy-008, Baustein C+M2).

Macht das `gen_e2e`-Manifest zum objektiven Gate statt zur bloßen Anzeige:
ein `check` mit `kind: executable` MUSS ausführbar sein (nicht skipped), sonst
ist der Screen NICHT parity-fertig. `behavioral-manual`/`nfr-out-of-band` sind
ausgenommen — aber weil sie in der Spec sichtbar getaggt sind, kein Schlupfloch
(gegen erschlichenes Schein-Grün, Befund B4). Nutzt das vorhandene Manifest —
kein neues Wahrheitsfeld.

Phasen (ADR-211 I3):
  A  — gegen Renderer #1 (KD-Shell). Gate = kein executable-Check skipped
       UND fragile_selectors == 0.
  C  — zusätzlich Parität gegen Renderer #2 (echte App). Das ist der pytest-Lauf
       gegen SPEC_RENDERER_BASE_URL — dieses Skript prüft die manifest-belegbaren
       Fakten; den Live-Lauf muss die CI separat fahren (wird hier nur benannt).

Aufruf:  klickdummy-parity-gate <spec.yaml> <manifest.json> [--phase A|C]
Exit:    0 = Gate grün · 1 = Verstoß · 2 = Setup-Fehler
"""

from __future__ import annotations

import json
import pathlib
import sys

try:
    import yaml
except ImportError:
    print("FAIL (setup): PyYAML fehlt. pip install pyyaml")
    sys.exit(2)


def _kind_map(spec: dict) -> dict[tuple[str, str], str]:
    """(screen_id, check_id) → kind (default 'executable')."""
    out: dict[tuple[str, str], str] = {}
    for sc in spec.get("screens", []) or []:
        sid = str(sc.get("id", ""))
        for pa in sc.get("parity_acceptance", []) or []:
            out[(sid, str(pa.get("id", "")))] = str(pa.get("kind", "executable"))
    return out


def evaluate(spec: dict, manifest: dict, phase: str = "A") -> tuple[bool, list[str]]:
    """(ok, violations). Ein executable-Check, der skipped ist, ist ein Verstoß;
    behavioral-manual/nfr-out-of-band sind ausgenommen. fragile_selectors > 0 ist
    ein Verstoß (F23: nur stabile Anker am Off-Ramp)."""
    kinds = _kind_map(spec)
    violations: list[str] = []

    for sk in manifest.get("skipped_detail", []) or []:
        key = (str(sk.get("screen", "")), str(sk.get("id", "")))
        kind = kinds.get(key, "executable")
        if kind == "executable":
            violations.append(
                f"executable-Check skipped: {key[0]}/{key[1]} "
                f"(reason: {sk.get('skip_reason', '?')}) — assert ergänzen "
                f"ODER kind auf behavioral-manual/nfr-out-of-band setzen (getaggt, nicht still)."
            )

    fragile = manifest.get("fragile_selectors", []) or []
    for f in fragile:
        violations.append(
            f"fragiler Selektor: {f.get('screen', '?')}/{f.get('id', '?')} "
            f"= {f.get('selector', '?')!r} — stabilen testid=/role=/label=-Anker nutzen (F23)."
        )

    return (not violations, violations)


def main(argv: list[str]) -> int:
    phase = "A"
    positional: list[str] = []
    it = iter(argv)
    for a in it:
        if a == "--phase":
            phase = next(it, "A")
        elif a.startswith("--phase="):
            phase = a.split("=", 1)[1]
        elif not a.startswith("--"):
            positional.append(a)
    if len(positional) < 2:
        print("Usage: klickdummy-parity-gate <spec.yaml> <manifest.json> [--phase A|C]")
        return 2
    spec_path, manifest_path = pathlib.Path(positional[0]), pathlib.Path(positional[1])
    try:
        spec = yaml.safe_load(spec_path.read_text(encoding="utf-8")) or {}
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except FileNotFoundError as e:
        print(f"FAIL (setup): Datei fehlt: {e.filename}")
        return 2

    ok, violations = evaluate(spec, manifest, phase)
    print(f"== Parity-Gate (Phase {phase}) ==")
    print(f"  Spec     : {spec_path}")
    print(f"  Manifest : {manifest_path}")
    print(
        f"  executable={manifest.get('executable')} skipped={manifest.get('skipped')} "
        f"fragile={len(manifest.get('fragile_selectors', []) or [])}"
    )
    if ok:
        print(
            "  ✓ Gate GRÜN — alle executable-Checks ausführbar, keine fragilen Selektoren."
        )
        if phase.upper() == "C":
            print(
                "  ℹ Phase C: die Live-Parität gegen Renderer #2 (echte App) belegt der "
                "pytest-Lauf gegen SPEC_RENDERER_BASE_URL — separat in CI, nicht hier."
            )
        return 0
    print(f"  ✗ Gate ROT — {len(violations)} Verstoß/Verstöße:")
    for v in violations:
        print(f"      • {v}")
    return 1


def main_cli() -> int:
    return main(sys.argv[1:])


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

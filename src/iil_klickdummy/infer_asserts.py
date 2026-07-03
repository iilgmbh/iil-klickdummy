"""Assert-Inferenz (KONZ-iil-klickdummy-008, Baustein A).

**EXPERIMENTAL** — das Kill-Kriterium dieser Komponente (Mensch-Bestätigungsquote
der Kandidaten <50% ⇒ verwerfen, KONZ-008 Ledger L3, `review_by: 2026-08-03`) ist
NOCH NICHT gemessen. Bis dahin ist die Ausgabe ein Assistenz-Vorschlag, kein
verlässlicher Generator — jeden Kandidaten prüfen, nicht blind übernehmen.

Schlägt für Prosa-`check`s ohne `assert` einen Kandidaten vor — für die
**einfache Klasse** (Präsenz/Zähl/Text) gegen das testid-Inventar der Shell.
Verhaltens-/State-Checks werden NICHT geraten, sondern als `kind: behavioral-manual`
markiert (ehrlich getaggt statt Garbage-Assert). Ausgabe ist ein **Vorschlag**;
nie auto-committed (`--emit-diff` schreibt eine `.suggested.yaml` daneben).

Grenze (Pilot-Befund ex-schutz): Shell-testids sind oft JS-templated
(`data-testid="step-${p.id}"`). Ein statischer Parse liefert dann kein exakt
zählbares/anwählbares Anker — solche Fälle werden als „Container-testid nötig"
geflaggt, nicht falsch-positiv als grün verkauft. Für konkrete Anker ist das
gerenderte DOM (headless) die bessere Quelle; dieses Modul akzeptiert daher
optional ein vorab gerendertes testid-Inventar (`--testids <file>`, eine ID/Zeile).

Aufruf:  klickdummy-infer-asserts <spec.yaml> <shell.html> [--emit-diff] [--testids <file>]
Exit:    0 = Vorschläge erzeugt · 2 = Setup-Fehler
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

# State-/Interaktions-Verben → NICHT per visible/text/count ausdrückbar (heute).
_BEHAVIORAL = re.compile(
    r"blockier|protokollier|erzeug|wird\s+\w+\s+erzeug|release|committ?|"
    r"validier|gaten?\b|übergang|transition|persistier|speicher\w*\s+bei|"
    r"neu\s+erzeugt|verhindert|erzwingt",
    re.IGNORECASE,
)
_COUNT = re.compile(r"\b(?:alle\s+)?(\d+)\b.*?(sichtbar|angezeigt|einträge|schritte|zeilen|elemente)",
                    re.IGNORECASE)
_VISIBLE = re.compile(r"sichtbar|angezeigt|erscheint|vorhanden", re.IGNORECASE)
_TESTID_TAG = re.compile(r'data-testid="([^"]+)"')
_TEMPLATED = re.compile(r"\$\{|'\s*\+|\+\s*'")   # ${…} oder String-Concat = JS-interpoliert


def testid_inventory(shell_html: str) -> tuple[set[str], set[str]]:
    """(konkrete_testids, templated_prefixe). Templated → nur der stabile Präfix
    vor `${`/Concat (z.B. `step-${p.id}` → `step-`) für Zähl-Hinweise."""
    concrete, templated = set(), set()
    for tid in _TESTID_TAG.findall(shell_html):
        if _TEMPLATED.search(tid):
            prefix = re.split(r"\$\{|'\s*\+|\+\s*'", tid)[0].rstrip("-_")
            if prefix:
                templated.add(prefix)
        else:
            concrete.add(tid)
    return concrete, templated


def _match_testid(check: str, concrete: set[str], templated: set[str]) -> str | None:
    """Bestes testid-Match für Wörter im Check (konkret bevorzugt vor Präfix).

    Match, wenn die testid (bzw. ein Segment davon) als Substring im Check-Text
    vorkommt ODER umgekehrt — deckt `step` ↔ `step-1 … step-10 / Stepper` ab
    (Pilot-Befund: reine Token-Set-Gleichheit verfehlte das)."""
    low = check.lower()

    def _hit(anchor: str) -> bool:
        a = anchor.lower()
        # Voller Anker als Substring ist spezifisch genug (z.B. "tenant-bar").
        if a in low or a.replace("-", " ") in low:
            return True
        # Segmente NUR an Wortgrenzen — sonst matcht "bar" in "sicht·bar"
        # (Pilot-Befund: falsch-positiv tenant-bar). `\bstep\b` trifft `step-1`.
        segs = [s for s in re.split(r"[-_]", a) if len(s) >= 3]
        return any(re.search(rf"\b{re.escape(s)}\b", low) for s in segs)

    for tid in sorted(concrete, key=len, reverse=True):
        if _hit(tid):
            return tid
    for pfx in sorted(templated, key=len, reverse=True):
        if _hit(pfx):
            return f"{pfx}*"   # Präfix-Markierung → Container nötig
    return None


def infer_one(check: str, concrete: set[str], templated: set[str]) -> dict:
    """Kandidat für EINEN check. Rückgabe:
    {kind, assert?, note}. kind ∈ executable|behavioral-manual."""
    if _BEHAVIORAL.search(check):
        return {"kind": "behavioral-manual",
                "note": "State-/Interaktions-Aussage — nicht per visible/text/count ausdrückbar (heute). "
                        "Manuell ODER Roadmap-B (State-DSL)."}
    m = _COUNT.search(check)
    tid = _match_testid(check, concrete, templated)
    if m and tid:
        if tid.endswith("*"):
            # EF-3 (Retro 2026-07-03): templated testid (`step-${…}`) ist per exact-
            # match NICHT zählbar — `get_by_test_id("step")` trifft `step-1..N` nie.
            # KEIN executable-Assert emittieren (der wäre funktional tot und würde als
            # `kind:executable` das Gate täuschen); stattdessen behavioral-manual +
            # konkreter Hinweis, wie es executable würde (stabiler Container-testid).
            return {"kind": "behavioral-manual",
                    "note": f"testid '{tid[:-1]}…' ist JS-templated → nicht per exact-match zählbar. "
                            f"Executable machen: einen stabilen Container-testid ergänzen "
                            f"(z.B. testid={tid[:-1]}-list) und `count` dagegen setzen — dann `kind:executable`."}
        return {"kind": "executable",
                "assert": {"action": "count", "selector": f"testid={tid}", "expect": int(m.group(1))},
                "note": "Zähl-Kandidat aus Zahl + testid-Match."}
    if _VISIBLE.search(check) and tid and not tid.endswith("*"):
        return {"kind": "executable",
                "assert": {"action": "visible", "selector": f"testid={tid}"},
                "note": "Präsenz-Kandidat aus 'sichtbar' + testid-Match."}
    return {"kind": "behavioral-manual",
            "note": "Kein sicheres testid-Match / kein Präsenz-/Zähl-Muster — manuell prüfen "
            "(Kandidat ohne Beleg wäre Garbage; bewusst KEIN Assert geraten)."}


def analyse(spec: dict, concrete: set[str], templated: set[str]) -> list[dict]:
    """Pro parity_acceptance OHNE assert ein Vorschlags-Record."""
    out: list[dict] = []
    for sc in spec.get("screens", []) or []:
        sid = sc.get("id", "screen")
        for pa in sc.get("parity_acceptance", []) or []:
            if pa.get("assert"):
                continue   # hat schon einen Assert
            rec = {"screen": sid, "id": pa.get("id", "?"), "check": pa.get("check", "")}
            rec.update(infer_one(str(pa.get("check", "")), concrete, templated))
            out.append(rec)
    return out


def main(argv: list[str]) -> int:
    emit = "--emit-diff" in argv
    positional, testids_file = [], None
    it = iter(argv)
    for a in it:
        if a == "--testids":
            testids_file = next(it, None)
        elif not a.startswith("--"):
            positional.append(a)
    if len(positional) < 2:
        print("Usage: klickdummy-infer-asserts <spec.yaml> <shell.html> [--emit-diff] [--testids <file>]")
        return 2
    spec_path, shell_path = pathlib.Path(positional[0]), pathlib.Path(positional[1])
    try:
        spec = yaml.safe_load(spec_path.read_text(encoding="utf-8")) or {}
        shell = shell_path.read_text(encoding="utf-8", errors="ignore")
    except FileNotFoundError as e:
        print(f"FAIL (setup): Datei fehlt: {e.filename}")
        return 2

    concrete, templated = testid_inventory(shell)
    if testids_file:
        extra = pathlib.Path(testids_file).read_text(encoding="utf-8").split()
        concrete |= {t for t in extra if not _TEMPLATED.search(t)}

    recs = analyse(spec, concrete, templated)
    n_exec = sum(1 for r in recs if r["kind"] == "executable")
    n_behav = sum(1 for r in recs if r["kind"] == "behavioral-manual")

    print("⚗ EXPERIMENTAL: Kill-Gate (Bestätigungsquote) noch nicht gemessen "
          "(KONZ-008, review_by 2026-08-03) — Kandidaten prüfen, nicht blind übernehmen.",
          file=sys.stderr)
    print(f"== Assert-Inferenz ==  Spec: {spec_path.name}  Shell: {shell_path.name}")
    print(f"  testids: {len(concrete)} konkret · {len(templated)} templated (Präfixe: {sorted(templated)[:6]})")
    print(f"  Checks ohne assert: {len(recs)}  →  {n_exec} assert-Kandidat · {n_behav} behavioral-manual")
    for r in recs:
        head = f"  [{r['screen']}/{r['id']}] {r['kind']}"
        print(head)
        print(f"      check : {r['check']}")
        if r.get("assert"):
            print(f"      assert: {r['assert']}")
        print(f"      → {r['note']}")

    if emit:
        # Vorschlag NEBEN die Spec schreiben — NIE die Spec selbst überschreiben.
        sug = spec_path.with_suffix(".suggested.yaml")
        sug.write_text(yaml.safe_dump({"inferred": recs}, allow_unicode=True, sort_keys=False),
                       encoding="utf-8")
        print(f"  ✍ Vorschlag geschrieben: {sug}  (Mensch prüft + gießt in die Spec — kein Auto-Commit)")
    return 0


def main_cli() -> int:
    return main(sys.argv[1:])


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

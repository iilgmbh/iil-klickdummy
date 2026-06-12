"""Use-Case-Layer — Frontmatter-Parse, Coverage, Validator, Skeleton-Gen.

Extrahiert aus lineage.py (KONZ-003 Empf-1, PR3) — reine Code-Motion.
"""
from __future__ import annotations

import re
import yaml
from pathlib import Path
from .config import _cfg
from .scan import detect_org
from .synth import _entity_def_from_spec, _persona_def_from_spec


def _prefix_to_repo(prefix: str) -> str:
    """Maps Spec-Ref-Prefix → Repo-Name. ADR-211 Rev 15 Cross-Repo-Konvention.

    Beispiele: ``meiki`` → ``meiki-hub``, ``ausschreibungs-hub`` → unverändert,
    ``ttz`` → ``ttz-hub``. Heuristik: bereits Repo-Name akzeptieren, sonst
    ``<prefix>-hub`` testen, sonst Prefix wie eingegeben behalten.
    """
    if not prefix:
        return ""
    p = prefix.strip()
    if (_cfg.repos_root / p).is_dir():
        return p
    cand = f"{p}-hub"
    if (_cfg.repos_root / cand).is_dir():
        return cand
    return p


def _parse_uc_frontmatter(text: str) -> dict | None:
    """Liest YAML-Frontmatter zwischen den ersten zwei ``---``-Zeilen.

    Schema-A (Standard): ``uc_id, name, primaer_akteur, sekundaer_akteure,
    realisiert_von_klickdummy, related_screens, fv_bezug, prio, status``.
    Schema-B (Skelett): ``uc_id, source_spec, source_screen, status`` —
    wird auf Schema-A normalisiert.
    """
    if not text.startswith("---"):
        return None
    end = text.find("\n---", 4)
    if end < 0:
        return None
    try:
        fm = yaml.safe_load(text[4:end]) or {}
    except yaml.YAMLError:
        return None
    if not isinstance(fm, dict):
        return None
    # Normalisierung Schema-B → Schema-A
    if "source_screen" in fm and "related_screens" not in fm:
        src_spec = fm.get("source_spec") or ""
        src_screen = fm.get("source_screen") or ""
        if src_spec and src_screen:
            # source_spec kann sein: meiki:klickdummy-spec-fristenmanagement
            # → wir tagen das als <prefix>:<kd-name>#<screen>
            fm["related_screens"] = [f"{src_spec}#{src_screen}"]
    return fm


def find_all_repos_ucs() -> list[dict]:
    """Walks ~/github/*/docs/**/UC-*.md für maschinen-lesbare Use Cases.

    Rev 15 §UC-Coverage: jeder UC mit YAML-Frontmatter wird discovered.
    Markdown-only UCs ohne Frontmatter werden übersprungen (Iter-1-Scope).
    """
    out: list[dict] = []
    if not _cfg.repos_root.is_dir():
        return out
    for repo_dir in sorted(_cfg.repos_root.iterdir()):
        if not repo_dir.is_dir() or repo_dir.name.startswith("."):
            continue
        repo_name = repo_dir.name
        org = detect_org(repo_name)
        # Standard-Pfad + meiki-spezifischer Requirements-Subpath
        patterns = [
            "docs/use-cases/**/UC-*.md",
            "docs/use-cases/UC-*.md",
            "docs/**/use-cases/UC-*.md",
            "docs/**/requirements/use-cases/UC-*.md",
        ]
        seen: set[Path] = set()
        for pat in patterns:
            for uc_path in repo_dir.glob(pat):
                if uc_path in seen:
                    continue
                seen.add(uc_path)
                try:
                    text = uc_path.read_text("utf-8")
                except OSError:
                    continue
                fm = _parse_uc_frontmatter(text)
                if not fm or not fm.get("uc_id"):
                    continue
                out.append({
                    "org": org,
                    "repo": repo_name,
                    "uc_id": str(fm["uc_id"]),
                    "name": str(fm.get("name") or fm.get("uc_id")),
                    "akteur": fm.get("primaer_akteur") or fm.get("akteur") or "",
                    "sekundaer": fm.get("sekundaer_akteure") or [],
                    "realisiert_von": fm.get("realisiert_von_klickdummy") or fm.get("source_spec") or "",
                    "related_screens": fm.get("related_screens") or [],
                    "fv_bezug": fm.get("fv_bezug") or "",
                    "prio": fm.get("prio") or "",
                    "status": fm.get("status") or "draft",
                    "source_file": uc_path,
                })
    return out


_SCREEN_REF_RE = re.compile(r"^(?:([^:]+):)?([^#]+)(?:#(.+))?$")


def _resolve_screen_ref(ref: str, adr_to_kd: dict[tuple[str, str], str]) -> tuple[str, str, str] | None:
    """``<prefix>:ADR-NNN#screen-id`` oder ``<prefix>:<kd-or-spec-id>#screen-id``
    → ``(repo, kd_name, screen_id)``. Gibt ``None`` bei Auflösungs-Fehler.
    ``adr_to_kd``: Lookup ``{(repo, adr_id): kd_name}``.
    """
    if not ref:
        return None
    m = _SCREEN_REF_RE.match(str(ref).strip())
    if not m:
        return None
    prefix, target, screen = m.group(1) or "", m.group(2) or "", m.group(3) or ""
    repo = _prefix_to_repo(prefix) if prefix else ""
    if not repo or not screen:
        return None
    target = target.strip()
    if target.startswith("ADR-"):
        kd = adr_to_kd.get((repo, target), "")
        if not kd:
            return None
        return (repo, kd, screen)
    if target.startswith("klickdummy-spec-"):
        return (repo, target.removeprefix("klickdummy-spec-"), screen)
    return (repo, target, screen)


def build_uc_coverage(ucs: list[dict], kds: list[dict]) -> dict:
    """Cross-Ref UC ↔ Screen. Ergebnis:

    ``{
        'matrix': {(uc_id_global, repo, kd): [screen_ids]},
        'uc_realized_count': {uc_id_global: count_of_resolved_screens},
        'uc_unresolved': {uc_id_global: [unresolved_refs]},
        'screen_to_ucs': {(repo, kd, screen): [uc_id_global]},
    }``
    """
    # Bau adr_to_kd-Lookup aus KD-Specs. adr.local kann Prefix tragen
    # (z. B. ``meiki:ADR-032``) — wir indexieren ohne Prefix.
    adr_to_kd: dict[tuple[str, str], str] = {}
    for kd in kds:
        if kd.get("kind", "spec") != "spec":
            continue
        adr_local = (kd.get("data", {}).get("adr", {}) or {}).get("local") or ""
        if ":" in adr_local:
            adr_local = adr_local.split(":", 1)[1]
        if adr_local:
            adr_to_kd[(kd["repo"], adr_local)] = kd["kd"]
    # Bau set bekannter Screen-IDs pro KD
    kd_screens: dict[tuple[str, str], set[str]] = {}
    for kd in kds:
        if kd.get("kind", "spec") != "spec":
            continue
        scr_ids = {s.get("id") for s in (kd.get("data", {}).get("screens") or []) if isinstance(s, dict) and s.get("id")}
        kd_screens[(kd["repo"], kd["kd"])] = scr_ids

    matrix: dict[tuple[str, str, str], list[str]] = {}
    uc_realized_count: dict[str, int] = {}
    uc_unresolved: dict[str, list[str]] = {}
    screen_to_ucs: dict[tuple[str, str, str], list[str]] = {}
    for uc in ucs:
        uc_gid = f"{uc['repo']}:{uc['uc_id']}"
        realized = 0
        unresolved: list[str] = []
        for ref in uc["related_screens"]:
            resolved = _resolve_screen_ref(ref, adr_to_kd)
            if not resolved:
                unresolved.append(str(ref))
                continue
            r, kd, sid = resolved
            if sid not in kd_screens.get((r, kd), set()):
                unresolved.append(f"{ref} (screen-id existiert nicht in {r}/{kd})")
                continue
            matrix.setdefault((uc_gid, r, kd), []).append(sid)
            screen_to_ucs.setdefault((r, kd, sid), []).append(uc_gid)
            realized += 1
        uc_realized_count[uc_gid] = realized
        if unresolved:
            uc_unresolved[uc_gid] = unresolved
    return {
        "matrix": matrix,
        "uc_realized_count": uc_realized_count,
        "uc_unresolved": uc_unresolved,
        "screen_to_ucs": screen_to_ucs,
    }


def _uc_kd_targets(uc: dict, repo: str, adr_to_kd: dict[tuple[str, str], str] | None = None) -> list[str]:
    """Aus ``related_screens`` die KD-Namen extrahieren (für ?kd=-Filter).

    Ref-Formate: ``<prefix>:ADR-NNN#screen`` oder ``<prefix>:<spec-id>#screen``.
    ADR-Refs werden via ``adr_to_kd``-Lookup auf KD-Namen aufgelöst (z. B.
    ``meiki:ADR-030`` → ``buergerportal``). Spec-IDs werden vom
    ``klickdummy-spec-``-Präfix befreit.
    """
    adr_to_kd = adr_to_kd or {}
    out: list[str] = []
    for ref in uc.get("related_screens", []):
        m = _SCREEN_REF_RE.match(str(ref).strip())
        if not m:
            continue
        prefix = m.group(1) or ""
        target = m.group(2) or ""
        ref_repo = _prefix_to_repo(prefix) if prefix else repo
        if target.startswith("ADR-"):
            kd_name = adr_to_kd.get((ref_repo, target), "")
            if kd_name:
                out.append(kd_name)
            else:
                out.append(target)  # Fallback: roh, falls Lookup fehlt
        elif target.startswith("klickdummy-spec-"):
            out.append(target.removeprefix("klickdummy-spec-"))
        else:
            out.append(target)
    return out


_UC_ID_PATTERN = re.compile(r"^UC-[A-Za-z0-9][A-Za-z0-9_-]+$")


_VALID_UC_STATUS = {"draft", "reviewed", "approved"}


def validate_ucs(ucs: list[dict], kds: list[dict]) -> dict[str, list[dict]]:
    """ADR-211 Rev 16 §UC-Coverage: Stufe-A-Validator (Workshop 2026-05-26).

    Pro UC: Liste von Findings ``[{severity, code, msg}]``. severity ∈
    {error, warning}. Validiert: YAML-Strukturen (Pflichtfelder), uc_id-Pattern,
    status-enum, related_screens-Auflösung gegen Klickdummy-Specs, Persona-
    Existenz in mindestens einem Ziel-KD, keine doppelten uc_ids cross-repo.
    """
    out: dict[str, list[dict]] = {}
    # ADR→KD-Lookup + KD-Personas + KD-Screens
    adr_to_kd: dict[tuple[str, str], str] = {}
    kd_personas: dict[tuple[str, str], set[str]] = {}
    kd_screens: dict[tuple[str, str], set[str]] = {}
    for kd in kds:
        if kd.get("kind", "spec") != "spec":
            continue
        adr_local = (kd.get("data", {}).get("adr", {}) or {}).get("local") or ""
        if ":" in adr_local:
            adr_local = adr_local.split(":", 1)[1]
        if adr_local:
            adr_to_kd[(kd["repo"], adr_local)] = kd["kd"]
        d = kd.get("data", {}) or {}
        pers = d.get("personas") or {}
        if isinstance(pers, dict):
            kd_personas[(kd["repo"], kd["kd"])] = set(pers.keys())
        elif isinstance(pers, list):
            kd_personas[(kd["repo"], kd["kd"])] = {
                p.get("id") for p in pers if isinstance(p, dict) and p.get("id")
            }
        else:
            kd_personas[(kd["repo"], kd["kd"])] = set()
        kd_screens[(kd["repo"], kd["kd"])] = {
            s.get("id") for s in (d.get("screens") or [])
            if isinstance(s, dict) and s.get("id")
        }

    # Cross-Repo-Duplicate-Check
    seen_gids: dict[str, str] = {}  # gid → first source_file
    for uc in ucs:
        gid = f"{uc['repo']}:{uc['uc_id']}"
        findings: list[dict] = []

        # 1. uc_id-Pattern
        if not _UC_ID_PATTERN.match(uc["uc_id"]):
            findings.append({
                "severity": "warning",
                "code": "UC-ID-PATTERN",
                "msg": f"uc_id {uc['uc_id']!r} matched nicht ^UC-[A-Z0-9-]+$ (Konvention)",
            })

        # 2. Pflichtfelder
        if not uc.get("name"):
            findings.append({"severity": "error", "code": "MISSING-NAME",
                            "msg": "Pflichtfeld `name` fehlt"})
        if not uc.get("akteur"):
            findings.append({"severity": "warning", "code": "MISSING-PERSONA",
                            "msg": "Empfohlenes Feld `primaer_akteur` fehlt"})

        # 3. Status-enum
        st = (uc.get("status") or "").lower()
        if st and st not in _VALID_UC_STATUS:
            findings.append({
                "severity": "error", "code": "INVALID-STATUS",
                "msg": f"status={st!r} nicht in {sorted(_VALID_UC_STATUS)}",
            })

        # 4. related_screens-Auflösung
        rs_list = uc.get("related_screens") or []
        if not rs_list:
            findings.append({
                "severity": "warning", "code": "NO-REL-SCREENS",
                "msg": "Keine `related_screens` — UC ist nicht im Klickdummy realisiert",
            })
        else:
            target_kds: set[tuple[str, str]] = set()
            for ref in rs_list:
                resolved = _resolve_screen_ref(str(ref), adr_to_kd)
                if not resolved:
                    findings.append({
                        "severity": "warning", "code": "UNRESOLVED-REF",
                        "msg": f"related_screens-Ref {ref!r} nicht auflösbar",
                    })
                    continue
                r, k, sid = resolved
                if sid not in kd_screens.get((r, k), set()):
                    findings.append({
                        "severity": "error", "code": "MISSING-SCREEN",
                        "msg": f"Screen `{sid}` existiert nicht in {r}:{k}",
                    })
                    continue
                target_kds.add((r, k))

            # 5. Persona-Existenz (in mindestens einem Ziel-KD)
            akt = uc.get("akteur")
            if akt and target_kds:
                in_any = any(akt in kd_personas.get((r, k), set()) for r, k in target_kds)
                if not in_any:
                    findings.append({
                        "severity": "warning", "code": "PERSONA-NOT-IN-KD",
                        "msg": f"Persona `{akt}` nicht in Personas der related Klickdummies "
                               f"({', '.join(f'{r}:{k}' for r, k in target_kds)})",
                    })

        # 6. Doppelte uc_id cross-repo
        if gid in seen_gids:
            findings.append({
                "severity": "error", "code": "DUPLICATE-UC-ID",
                "msg": f"uc_id {gid} bereits in {seen_gids[gid]} verwendet",
            })
        else:
            try:
                seen_gids[gid] = str(uc["source_file"].relative_to(_cfg.repos_root))
            except (ValueError, KeyError):
                seen_gids[gid] = str(uc.get("source_file", "?"))

        if findings:
            out[gid] = findings
    return out


_REPO_UC_PREFIX = {
    "meiki-hub": "MEK",
    "ausschreibungs-hub": "AH",
    "ttz-hub": "TTZ",
    "risk-hub": "RH",
    "pg-hub": "PG",
}


def _repo_shortcode(repo: str) -> str:
    if repo in _REPO_UC_PREFIX:
        return _REPO_UC_PREFIX[repo]
    parts = [p for p in repo.replace("-hub", "").split("-") if p]
    if not parts:
        return repo.upper()[:3]
    return "".join(p[0] for p in parts).upper()[:4]


def _kd_shortcode(kd_name: str) -> str:
    """``buergerportal-bevollmaechtigte`` → ``BPB``, ``uvg`` → ``UVG``."""
    parts = [p for p in kd_name.split("-") if p]
    if not parts:
        return kd_name.upper()[:4]
    if len(parts) == 1:
        return parts[0].upper()[:4]
    return "".join(p[0] for p in parts).upper()[:5]


def gen_uc_skeleton(repo: str, kd_name: str, kd_adr_local: str | None,
                   spec_data: dict, screen: dict, persona: str, counter: int) -> tuple[str, str]:
    """Erzeugt UC-MD-Skelett aus Spec-Inhalten. Return (filename, content).

    Beschreibungen werden aus Spec abgeleitet (statt nur TODOs):
    - Kurzbeschreibung: aus screen.title + persona.description + halbschicht
    - Vorbedingung: aus persona.rechte + voraussetzung_screen
    - Hauptablauf: aus fokus-Bullets (als 1. Entwurf)
    - Postcondition: aus next_screens + entity-Effekten
    - Akzeptanzkriterien: aus konsumiert_entities.consumers_must_treat_as
    """
    sid = screen.get("id", "unknown")
    stitle = screen.get("title", sid)
    fokus = screen.get("fokus") or []
    halbschicht = screen.get("halbschicht") or "?"
    voraus = screen.get("voraussetzung_screen")
    next_screens = screen.get("next_screens") or []
    if isinstance(next_screens, str):
        next_screens = [next_screens]
    konsumiert = screen.get("konsumiert_entities") or []
    lokal = screen.get("local_entities") or []
    short = _repo_shortcode(repo)
    kd_slug = _kd_shortcode(kd_name)
    uc_id = f"UC-AUTO-{short}-{kd_slug}-{counter:03d}"
    filename = f"{uc_id}-{sid.replace('_', '-')}-{persona.replace('_', '-')}.md"
    realisiert_ref = f"{repo.replace('-hub','')}:{kd_adr_local.split(':',1)[1]}" if kd_adr_local and ':' in kd_adr_local else (kd_adr_local or f"{repo}:{kd_name}")
    related_ref = f"{realisiert_ref}#{sid}"

    # Persona-Kontext aus Spec
    persona_def = _persona_def_from_spec(spec_data, persona)
    persona_desc = persona_def.get("description", "")
    persona_rechte = persona_def.get("rechte") or []
    persona_halbschicht = persona_def.get("halbschicht", halbschicht)
    anlass_pflicht = persona_def.get("abteilungs_kontext_pflicht") or screen.get("voraussetzung_screen") == "anlass_modal"

    # 1. Kurzbeschreibung — abgeleitet
    halbschicht_de = {
        "buerger": "im Bürger-Self-Service-Bereich",
        "verwaltung": "im verwaltungs-internen Bereich",
    }.get(persona_halbschicht, "")
    desc_lines = [
        f"**{persona}** öffnet den Screen *{stitle}*{(' ' + halbschicht_de) if halbschicht_de else ''}.",
    ]
    if persona_desc:
        desc_lines.append(f"Persona-Kontext: {persona_desc}")
    if fokus:
        primary_goal = str(fokus[0])
        desc_lines.append(f"Primäres Ziel laut Spec: *{primary_goal}*.")
    desc_block = "\n\n".join(desc_lines)

    # 2. Vorbedingung — aus persona.rechte + voraussetzung_screen
    vor_items = ["Persona ist authentifiziert"]
    if persona_rechte:
        vor_items.append(f"Berechtigungen aktiv: `{', '.join(persona_rechte[:3])}`" + (" …" if len(persona_rechte) > 3 else ""))
    if voraus:
        vor_items.append(f"Vorgängiger Screen wurde durchlaufen: `{voraus}`")
    if anlass_pflicht:
        vor_items.append("**Anlass-Pflicht** (DSGVO/Cross-Abt-Zugriff) wurde erfasst")
    vor_block = "\n".join(f"- {x}" for x in vor_items)

    # 3. Hauptablauf — aus fokus, durchnumeriert
    if fokus:
        ablauf_items = [f"{i+1}. {str(f)}" for i, f in enumerate(fokus[:6])]
    else:
        ablauf_items = [
            f"1. {persona} öffnet *{stitle}*",
            "2. *TODO: konkrete Schritte ergänzen*",
            "3. Speichern oder Folge-Screen wählen",
        ]
    ablauf_block = "\n".join(ablauf_items)

    # 4. Postcondition — aus next_screens + entity-Effekten
    post_items = []
    if next_screens:
        screens_lookup = {s.get("id"): s.get("title") for s in (spec_data.get("screens") or []) if isinstance(s, dict)}
        for nsid in next_screens[:3]:
            ntitle = screens_lookup.get(nsid, nsid)
            post_items.append(f"Folge-Screen *{ntitle}* (`{nsid}`) ist erreichbar")
    if lokal:
        post_items.append(f"Lokale Entities ergänzt/aktualisiert: `{', '.join(str(e) for e in lokal[:3])}`")
    if not post_items:
        post_items = ["Screen-Inhalt wurde dargestellt; keine deklarierten Folge-Effekte in Spec"]
    post_block = "\n".join(f"- {x}" for x in post_items)

    # 5. Akzeptanzkriterien — aus entity-Constraints
    ak_items = []
    for ename in (list(konsumiert) + list(lokal))[:4]:
        edef = _entity_def_from_spec(spec_data, str(ename))
        treat = edef.get("consumers_must_treat_as")
        if treat == "read-only":
            ak_items.append(f"`{ename}`-Felder werden nur angezeigt, nicht editiert (read-only-Vertrag)")
        elif treat == "append-only":
            ak_items.append(f"`{ename}`-Einträge werden nur hinzugefügt, nie überschrieben (append-only-Vertrag)")
    if anlass_pflicht:
        ak_items.append("Cross-Abt-Zugriff schreibt **vor** Datensicht in `cross_abt_anlass_log` (audit-trail)")
    if persona_halbschicht == "buerger":
        ak_items.append(f"`{persona}` sieht **nur eigene** Vorgänge/Stammdaten (Self-Service-Constraint)")
    if not ak_items:
        ak_items = ["*TODO: AC-001 — fachliche Mindestanforderung*", "*TODO: AC-002 — Fehlerverhalten*"]
    ak_block = "\n".join(f"- {x}" for x in ak_items)

    content = f"""---
uc_id: {uc_id}
name: "{stitle} ({persona})"
primaer_akteur: {persona}
sekundaer_akteure: []
realisiert_von_klickdummy: {realisiert_ref}
related_screens:
  - {related_ref}
fv_bezug: ""           # TODO: Welches Fachverfahren wird ersetzt/integriert?
prio: mittel           # TODO: hoch | mittel | niedrig
status: draft          # auto-generiert — bei Review zu `reviewed` heben
auto_generated: true   # entfernen wenn handgepflegt
auto_source: "Generator aus screens-spec.yaml (Halbschicht: {persona_halbschicht}, Spec-Felder: title/fokus/personas/entities/next_screens)"
---

# {uc_id} · {stitle} ({persona})

> ⚠ **Auto-generiertes Skelett** — alle Texte wurden aus dem Klickdummy-Spec
> abgeleitet (siehe `auto_source:`). Bitte fachlich prüfen, Feinheiten
> ergänzen, dann `auto_generated:` und `auto_source:` aus dem Frontmatter
> entfernen.

## Kurzbeschreibung

{desc_block}

## Vorbedingung

{vor_block}

## Hauptablauf

{ablauf_block}

## Postcondition (Erfolg)

{post_block}

## Akzeptanz-Kriterien

{ak_block}

## Bezug

- Klickdummy: `{realisiert_ref}`
- Screen: `{sid}` (Halbschicht: `{persona_halbschicht}`)
- Persona: `{persona}`{(' · ' + str(persona_rechte)) if persona_rechte else ''}
- Generator-Stand: ADR-211 Rev 16 §UC-Coverage
"""
    return filename, content


def generate_uc_skeletons(records: list[dict], existing_ucs: list[dict],
                         dry_run: bool = False) -> dict:
    """Generiert UC-Skelette für (screen × primary_persona)-Kombis ohne Coverage.

    Idempotent: existierende UCs (via uc_id ODER realized_in matching) werden
    übersprungen. Output: ``docs/use-cases/_auto/UC-AUTO-<SHORT>-<NNN>-<slug>.md``.
    """
    # Set: welche (repo, kd, screen) sind schon durch existierende UCs abgedeckt?
    covered: set[tuple[str, str, str]] = set()
    adr_to_kd: dict[tuple[str, str], str] = {}
    for kd in records:
        if kd.get("kind", "spec") != "spec":
            continue
        adr_local = (kd.get("data", {}).get("adr", {}) or {}).get("local") or ""
        if ":" in adr_local:
            adr_local = adr_local.split(":", 1)[1]
        if adr_local:
            adr_to_kd[(kd["repo"], adr_local)] = kd["kd"]
    for uc in existing_ucs:
        for ref in uc.get("related_screens", []):
            resolved = _resolve_screen_ref(ref, adr_to_kd)
            if resolved:
                covered.add(resolved)

    written: list[Path] = []
    skipped: int = 0
    for kd in records:
        if kd.get("kind", "spec") != "spec":
            continue
        repo = kd["repo"]
        kd_name = kd["kd"]
        d = kd["data"] or {}
        kd_adr_local = (d.get("adr", {}) or {}).get("local")
        out_dir = _cfg.repos_root / repo / "docs" / "use-cases" / "_auto"
        if not dry_run:
            out_dir.mkdir(parents=True, exist_ok=True)

        screens = d.get("screens") or []
        # Bug-Fix 2026-05-26: Counter ab max(existing) + 1 starten — sonst
        # kollidieren neu hinzugefügte Screens mit bereits committed UC-IDs.
        # Pattern: UC-AUTO-<SHORT>-<KD>-<NNN>-*.md
        repo_short = _repo_shortcode(repo)
        kd_slug = _kd_shortcode(kd_name)
        existing_max = 0
        if out_dir.is_dir():
            prefix = f"UC-AUTO-{repo_short}-{kd_slug}-"
            for p in out_dir.glob(f"{prefix}*.md"):
                m = re.match(rf"{re.escape(prefix)}(\d+)-", p.name)
                if m:
                    n = int(m.group(1))
                    if n > existing_max:
                        existing_max = n
        counter = existing_max
        for s in screens:
            if not isinstance(s, dict):
                continue
            sid = s.get("id")
            if not sid:
                continue
            personas = s.get("persona") or []
            if isinstance(personas, str):
                personas = [personas]
            primary = personas[0] if personas else None
            if not primary:
                continue
            if (repo, kd_name, sid) in covered:
                skipped += 1
                continue
            counter += 1
            filename, content = gen_uc_skeleton(repo, kd_name, kd_adr_local, d, s, primary, counter)
            out_path = out_dir / filename
            if out_path.exists():
                skipped += 1
                continue
            if not dry_run:
                out_path.write_text(content, encoding="utf-8")
            written.append(out_path)
    return {"written": written, "skipped": skipped}

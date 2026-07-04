"""Synthetische Beispieldaten — Personas/Entities für Render-Tabellen.

Extrahiert aus lineage.py (KONZ-003 Empf-1, PR3) — reine Code-Motion.
"""

from __future__ import annotations

import html
from typing import Any
from .config import _AKTEN_PROFIL_POOL, _BUERGER_POOL


def _row_buerger(row_idx: int) -> dict:
    return _BUERGER_POOL[row_idx % len(_BUERGER_POOL)]


def _row_akte(row_idx: int) -> dict:
    return _AKTEN_PROFIL_POOL[row_idx % len(_AKTEN_PROFIL_POOL)]


def _synth_value(field_name: str, row_idx: int, viewer_idx: int | None = None) -> str:
    """Heuristische Beispiel-Daten — row-konsistent (Bürger + Akte gleichgeschaltet).

    ``viewer_idx``: wenn gesetzt (z. B. ``0`` für Bürger-Self-Service-Screens),
    werden ALLE Zeilen demselben Bürger zugeordnet (= „eingeloggter Nutzer").
    Akten-Profile rotieren weiterhin, sodass eine Person mehrere Akten-Typen
    haben kann. ``None`` (Default) = rotierender Bürger pro Zeile.
    """
    n = field_name.lower()
    suffixes = ["A", "B", "C", "D", "E"]
    s = suffixes[row_idx % len(suffixes)]
    p = (
        _BUERGER_POOL[viewer_idx % len(_BUERGER_POOL)]
        if viewer_idx is not None
        else _row_buerger(row_idx)
    )
    a = _row_akte(row_idx)
    if ("akten" in n or "vorgang" in n) and "name" in n:
        return f"{a['typ']} – {p['nachname']}"
    if "_id" in n or n.endswith("id") or "akten" in n:
        if "akten" in n or n == "akten_id":
            return f"{a['prefix']}-2026-{row_idx + 1:04d}"
        prefix = (
            "".join(
                c
                for c in n.upper().replace("_ID", "").replace("_REF", "")
                if c.isalpha()
            )[:3]
            or "ID"
        )
        return f"{prefix}-2026-{row_idx + 1:04d}"
    if (
        "date" in n
        or "datum" in n
        or n.endswith("_ts")
        or n.endswith("_bis")
        or n.endswith("_ab")
        or "_at" in n
    ):
        if "geb" in n or "geburts" in n:
            return p["gebdatum"]
        return f"2026-{(row_idx % 9) + 1:02d}-{(row_idx % 27) + 1:02d}"
    if (
        n in ("namen", "name", "vorname", "nachname")
        or "buerger" in n
        and "name" in n
        or "person" in n
        and "name" in n
    ):
        if n == "vorname":
            return p["vorname"]
        if n == "nachname":
            return p["nachname"]
        return f"{p['vorname']} {p['nachname']}"
    if "name" in n or "titel" in n or "title" in n:
        return f"Beispiel {s}"
    if "status" in n:
        return ["aktiv", "in_pruefung", "abgeschlossen", "wartet", "offen"][row_idx % 5]
    if (
        "betrag" in n
        or "preis" in n
        or "summe" in n
        or "kosten" in n
        or "menge" in n
        and "geld" in n
    ):
        v = (row_idx + 1) * 1234.56
        return f"{v:,.2f} €".replace(",", "X").replace(".", ",").replace("X", ".")
    if "menge" in n or "anzahl" in n or "count" in n:
        return str((row_idx + 1) * 10)
    if "kanal" in n or "bevorzugt" in n:
        return p["kanal"]
    if "konfidenz" in n or "score" in n:
        return f"0.{85 - row_idx * 3}"
    if "adresse" in n or "anschrift" in n or "strasse" in n:
        return p["adresse"]
    if "typ" in n or "kategorie" in n:
        return ["Erstantrag", "Folgeantrag", "Veränderung"][row_idx % 3]
    if "einheit" in n:
        return ["m²", "m³", "Stk", "psch"][row_idx % 4]
    return f"Wert-{s}"


def _entity_field_names(entity_def: Any) -> list[str]:
    """Extrahiert max. 6 Field-Namen aus Entity-Definition."""
    if not isinstance(entity_def, dict):
        return []
    fields = entity_def.get("fields", []) or []
    out = []
    for f in fields[:6]:
        if isinstance(f, str):
            out.append(f)
        elif isinstance(f, dict):
            out.append(f.get("name") or (list(f.keys())[0] if f else "?"))
    return out


_AKTEN_ID_FIELDS = {"aktenzeichen", "akten_id"}


_AKTEN_LINK_FIELDS = _AKTEN_ID_FIELDS | {"aktenname"}


def _synth_entity_table(
    entity_name: str,
    entity_def: Any,
    n_rows: int = 3,
    screen_id: str | None = None,
    known_kds: dict[str, str] | None = None,
    known_kd_repos: dict[str, str] | None = None,
    viewer_idx: int | None = None,
) -> str:
    """Render HTML-Tabelle mit synthetischen Beispiel-Zeilen.

    Wenn ``screen_id`` gesetzt ist UND die Entity ein Akten-ID-Feld
    (``aktenzeichen``/``akten_id``) hat, fügt eine synthetische
    ``aktenname``-Spalte direkt dahinter ein und macht beide Spalten klickbar
    (öffnet das Akte-Modal des jeweiligen Screens).

    ``known_kds`` ist ein Lookup ``{kd_name: render_url}``. Pro Zeile wird der
    Aktentyp gegen den Lookup gematcht: existiert der Ziel-KD, bekommt der
    Anchor ``data-target-kd`` + ``data-target-url`` und das Akte-Modal zeigt
    einen Sprung-CTA in den jeweiligen Fachverfahrens-KD.
    """
    fields = _entity_field_names(entity_def)
    if not fields:
        return f'<p style="color:#999;font-size:12px;">Entity <code>{html.escape(entity_name)}</code> ohne deklarierte Felder.</p>'

    has_akten = any(f in _AKTEN_ID_FIELDS for f in fields)
    has_aname = "aktenname" in fields
    if has_akten and not has_aname:
        injected = []
        for f in fields:
            injected.append(f)
            if f in _AKTEN_ID_FIELDS:
                injected.append("aktenname")
        fields = injected[:6]

    known_kds = known_kds or {}
    known_kd_repos = known_kd_repos or {}
    head = "".join(f"<th>{html.escape(f)}</th>" for f in fields)

    # Autoren-Beispielzeilen (local_entities.<e>.examples) haben Vorrang vor der
    # Synth-Heuristik: domänen-echte Werte fürs „am Beispiel schärfen" (ADR-211
    # Co-Creation). Jede Zeile = Liste, an `fields`-Reihenfolge ausgerichtet;
    # zu kurze Zeilen werden per Synth aufgefüllt, zu lange auf 6 Spalten gekappt.
    examples = entity_def.get("examples") if isinstance(entity_def, dict) else None
    if isinstance(examples, list) and examples:
        ex_rows = []
        for i, ex in enumerate(examples):
            vals = list(ex) if isinstance(ex, (list, tuple)) else [ex]
            cells = []
            for j, f in enumerate(fields):
                v = (
                    vals[j]
                    if j < len(vals) and vals[j] is not None
                    else _synth_value(f, i, viewer_idx=viewer_idx)
                )
                cells.append(f"<td>{html.escape(str(v))}</td>")
            ex_rows.append(f"<tr>{''.join(cells)}</tr>")
        return (
            f'<table class="entity"><thead><tr>{head}</tr></thead>'
            f"<tbody>{''.join(ex_rows)}</tbody></table>"
        )

    rows_html = []
    for i in range(n_rows):
        azs_val = ""
        aname_val = ""
        for f in fields:
            if f in _AKTEN_ID_FIELDS:
                azs_val = _synth_value(f, i, viewer_idx=viewer_idx)
            elif f == "aktenname":
                aname_val = _synth_value(f, i, viewer_idx=viewer_idx)
        # Per-Zeile: KD-Hint aus _AKTEN_PROFIL_POOL → Match gegen known_kds
        akte = _row_akte(i)
        target_kd = akte.get("kd_hint") or ""
        target_url = known_kds.get(target_kd, "") if target_kd else ""
        # Bei bestehender Akte: deep-link auf Detail-Screen statt Default
        # (sonst landet z. B. UVG-Klick auf „Antrags-Übernahme aus Post-Routing")
        entry = akte.get("entry") or ""
        if target_url and entry:
            target_url = f"{target_url}#screen-{entry}"

        cells = []
        for f in fields:
            v = _synth_value(f, i, viewer_idx=viewer_idx)
            if screen_id and f in _AKTEN_LINK_FIELDS and (azs_val or aname_val):
                extra = ""
                if target_kd:
                    target_repo = known_kd_repos.get(target_kd, "")
                    extra = (
                        f' data-target-kd="{html.escape(target_kd)}"'
                        f' data-target-url="{html.escape(target_url)}"'
                        f' data-target-repo="{html.escape(target_repo)}"'
                    )
                cells.append(
                    f'<td><a class="akten-link" '
                    f'data-sid="{html.escape(screen_id)}" '
                    f'data-azs="{html.escape(azs_val)}" '
                    f'data-aname="{html.escape(aname_val)}"'
                    f"{extra}>"
                    f"{html.escape(v)}</a></td>"
                )
            else:
                cells.append(f"<td>{html.escape(v)}</td>")
        rows_html.append(f"<tr>{''.join(cells)}</tr>")
    return f'<table class="entity"><thead><tr>{head}</tr></thead><tbody>{"".join(rows_html)}</tbody></table>'


def _entities_lookup(d: dict) -> dict[str, Any]:
    """Sammelt root_entities + local_entities zu einem Lookup-Dict."""
    out: dict[str, Any] = {}
    re_root = d.get("root_entities") or {}
    le_loc = d.get("local_entities") or {}
    if isinstance(re_root, dict):
        out.update(re_root)
    if isinstance(le_loc, dict):
        out.update(le_loc)
    return out


def _persona_def_from_spec(spec_data: dict, persona_id: str) -> dict:
    """Personas-Block kann dict (id→def) oder list[{id, ...}] sein."""
    p = spec_data.get("personas") or {}
    if isinstance(p, dict):
        return p.get(persona_id) or {}
    if isinstance(p, list):
        for entry in p:
            if isinstance(entry, dict) and entry.get("id") == persona_id:
                return entry
    return {}


def _entity_def_from_spec(spec_data: dict, entity_name: str) -> dict:
    """root_entities + local_entities zusammenfassen."""
    out = {}
    for src in (
        spec_data.get("root_entities") or {},
        spec_data.get("local_entities") or {},
    ):
        if isinstance(src, dict):
            out.update(src)
    return out.get(entity_name) or {}

#!/usr/bin/env python3
"""Klickdummy-Lineage-Viewer + IIL-Genesor (Stufe 1a: Cross-Repo-Übersicht).

Zwei Modi:
  default:    Single-Repo-Lineage (meiki-hub) — Mermaid-Graph + Feedback-Widget
              → lineage.mmd + index.html        (Pfad-c-Output 2026-05-23)
  --genesor:  Cross-Repo-Übersicht (IIL-Genesor Stufe 1a, 2026-05-24)
              → genesor.html                    (Tabelle aller KDs in ~/github)

Selbst ein Klickdummy nach meiki:ADR-035 (Meta-KD, class: mock).

Konventionen (zwei Spec-Pfade je Repo werden gescannt):
  ~/github/<repo>/klickdummy/<name>/screens-spec.yaml
  ~/github/<repo>/docs/01-architektur/mockups/<name>-klickdummy/screens-spec.yaml

Aufruf:
  klickdummy-genesor                               # Single-Repo (meiki)
  klickdummy-genesor --genesor                     # + Cross-Repo Übersicht
  python3 -m iil_klickdummy.lineage --genesor      # äquivalent (Modul-Aufruf)

Seams (Default-Verhalten byte-identisch zu früher):
  --repos-root  (Default ~/github)        gescanntes Repo-Wurzelverzeichnis
  --out         (Default <root>/genesor)  Output-Verzeichnis
  --base-url    (Default "/")             URL-Präfix für Links + Skin-Pfade

Relocation 2026-05-28: aus meiki-hub/scripts/ in das Plattform-Paket
iil-klickdummy verlagert (cross-cutting Tooling, vgl. meiki:ADR-035).
"""
from __future__ import annotations

import argparse
import html
import json
import sys
from pathlib import Path
from typing import Any

import yaml

from .gen_e2e import is_fragile_selector, render_assertion

ROOT = Path(__file__).resolve().parent.parent
MOCKUPS_DIR = ROOT / "docs" / "01-architektur" / "mockups"
CONTRACTS_DIR = ROOT / "docs" / "01-architektur" / "contracts"
OUT_DIR = ROOT / "docs" / "01-architektur" / "lineage"           # Single-Repo-Lineage (Rückwärtskompat)
REPOS_ROOT = Path.home() / "github"
GENESOR_OUT = REPOS_ROOT / "genesor"                              # Cross-Repo: top-level für HTTP-Root

# URL-Präfix für generierte Cross-Repo-Links + Skin-Library-Pfade.
# Default "/" reproduziert das bisherige Verhalten byte-identisch (HTTP-Root = ~/github).
# Wird via --base-url überschrieben (z. B. "/genesor-host/" für einen späteren Portal-Build).
BASE_URL = "/"

# Basis-URL für die Skin-CSS-Dateien. Default "" reproduziert das bisherige
# Verhalten byte-identisch: Skins werden unter ihrem REPOS_ROOT-relativen Pfad
# (iil-klickdummy/.../skins/<name>.css) ausgeliefert. Wird via --skin-base
# gesetzt (z. B. "/genesor/skins"), dann wird NUR der Basename verwendet:
# "<skin-base>/<name>.css" — für einen self-contained Portal-Build, bei dem die
# 4 Skin-CSS-Dateien neben dem Genesor-Site liegen.
SKIN_BASE = ""

# Repos, deren echte Mockup-HTMLs unter "/kd/<repo>/..." einvendoriert
# ausgeliefert werden (z. B. iil-pet-portal/kd/). Steht ein Repo hier, wird in
# url_for_path() dem ROOT-relativen Pfad ein "/kd"-Präfix vorangestellt, sodass
# der Link auf die vendored Kopie statt auf das (auf iil.pet nicht ausgelieferte)
# Original zeigt. Leere Menge (Default) → byte-identisch zu früher.
VENDORED_REPOS: set[str] = set()


def _base_prefix() -> str:
    """Normalisiert BASE_URL zu einem Präfix ohne Trailing-Slash ("/"→"")."""
    return BASE_URL.rstrip("/")


def _skin_url(rel: str) -> str:
    """Skin-Pfad (REPOS_ROOT-relativ) → finale URL.

    SKIN_BASE leer  → "<base_prefix>/<rel>"  (byte-identisch zu früher).
    SKIN_BASE gesetzt → "<skin_base>/<basename>"  (nur Dateiname, z. B.
                        "/genesor/skins/okwobis-look.css").
    """
    if SKIN_BASE:
        return SKIN_BASE.rstrip("/") + "/" + rel.rsplit("/", 1)[-1]
    return _base_prefix() + "/" + rel


# ---- Mockup-HTML-Discovery (Stufe 1b: "Klickdummy klickbar") ---------------

MOCKUP_PRIO_NAMES = ("index.html", "shell.html")

def find_mockup_html(kd_dir: Path, kd_name: str) -> Path | None:
    """Findet die klickbare HTML-Datei in einem KD-Verzeichnis."""
    for name in MOCKUP_PRIO_NAMES:
        p = kd_dir / name
        if p.is_file():
            return p
    p = kd_dir / f"{kd_name}.html"
    if p.is_file():
        return p
    # Erste .html-Datei (außer README, _TEMPLATE)
    htmls = sorted(
        f for f in kd_dir.glob("*.html")
        if not f.name.startswith(("README", "_TEMPLATE", "_"))
    )
    return htmls[0] if htmls else None


def url_for_path(p: Path) -> str | None:
    """Pfad → URL relativ zu REPOS_ROOT, präfixiert mit BASE_URL.

    Default BASE_URL "/" → _base_prefix()=="" → "/<relpath>" (byte-identisch zu früher).

    Vendoring: liegt das erste Pfad-Segment (das Repo) in VENDORED_REPOS, wird dem
    ROOT-relativen Pfad ein "/kd"-Präfix vorangestellt ("/<repo>/..." →
    "/kd/<repo>/..."), sodass der Link auf die einvendorierte Kopie zeigt. Leere
    Menge (Default) → byte-identisch zu früher.
    """
    try:
        rel = str(p.relative_to(REPOS_ROOT))
    except ValueError:
        return None
    if VENDORED_REPOS and rel.split("/", 1)[0] in VENDORED_REPOS:
        return _base_prefix() + "/kd/" + rel
    return _base_prefix() + "/" + rel


# ---- Skin-Library (zentral in iil-klickdummy, via HTTP-Server-Root erreichbar)
# User-Feedback 2026-05-25: Style-Switcher als Demo-Werkzeug auch auf Root-Ebene
# (Genesor-Übersicht), mit localStorage-Persistenz cross-Render.

# Skin-Pfade relativ zu REPOS_ROOT (ohne BASE_URL-Präfix). Der Sentinel
# "__greenfield" ist KEIN Pfad und wird nie präfixiert.
SKIN_LIBRARY_REL: list[tuple[str, str]] = [
    ("__greenfield", "Greenfield (Default)"),
    ("iil-klickdummy/src/iil_klickdummy/snippets/skins/okwobis-look.css", "OK.Wobis-Look (Win-Forms)"),
    ("iil-klickdummy/src/iil_klickdummy/snippets/skins/prosoz-look.css", "Prosoz-Look (Web-Verwaltung)"),
    ("iil-klickdummy/src/iil_klickdummy/snippets/skins/arriba-look.css", "ARRIBA-Look (AVA-Engineering)"),
    ("iil-klickdummy/src/iil_klickdummy/snippets/skins/bayernid-look.css", "BayernID-Look (Bürger-modern)"),
]


def skin_library() -> list[tuple[str, str]]:
    """Skin-Library mit finalen Skin-URLs.

    Default (SKIN_BASE leer, BASE_URL "/") → "/iil-klickdummy/..." (byte-identisch zu früher).
    Mit --skin-base → "<skin-base>/<name>.css".
    Der Sentinel "__greenfield" bleibt unverändert.
    """
    return [
        (value if value == "__greenfield" else _skin_url(value), label)
        for value, label in SKIN_LIBRARY_REL
    ]


def build_skin_switcher_html(initial_value: str = "__greenfield") -> str:
    """HTML-Snippet für das Skin-Switcher-Dropdown — wird in Topbar + Genesor verwendet."""
    options = []
    for value, label in skin_library():
        sel = ' selected' if value == initial_value else ''
        options.append(f'<option value="{html.escape(value)}"{sel}>{html.escape(label)}</option>')
    return (
        '<div class="style-switch">'
        '<label for="skin-select">🎨 Style</label>'
        f'<select id="skin-select">{"".join(options)}</select>'
        '</div>'
    )


SKIN_SWITCHER_JS = """
  // Style-Switcher (Cross-Render localStorage-Persistenz)
  const SKIN_KEY = 'genesor_skin';
  function applySkin(url) {
    document.querySelectorAll('link[data-skin="1"]').forEach(l => l.remove());
    if (url && url !== '__greenfield') {
      const link = document.createElement('link');
      link.rel = 'stylesheet';
      link.href = url;
      link.setAttribute('data-skin', '1');
      document.head.appendChild(link);
    }
    try { localStorage.setItem(SKIN_KEY, url || '__greenfield'); } catch (e) {}
  }
  (function initSkin() {
    let saved = null;
    try { saved = localStorage.getItem(SKIN_KEY); } catch (e) {}
    const initial = window.INITIAL_SKIN || '__greenfield';
    const chosen = saved || initial;
    const sel = document.getElementById('skin-select');
    if (sel) {
      // Falls Spec-default da war, aber User hat selbst etwas anderes gewählt: User-Wahl gewinnt
      if (chosen !== initial) applySkin(chosen);
      else if (initial !== '__greenfield') applySkin(initial);
      // Stelle Dropdown auf Aktiv-Wert
      sel.value = chosen;
      sel.addEventListener('change', e => applySkin(e.target.value));
    } else if (initial !== '__greenfield') {
      applySkin(initial);
    }
  })();
"""


# ---- ADR-Frontmatter-Reader (Rev-15-Vorgriff: realizes_use_cases + replaces_system_ref)

_FRONTMATTER_RE = __import__("re").compile(r"^---\s*\n(.*?)\n---", __import__("re").DOTALL | __import__("re").MULTILINE)

def read_kd_adr_meta(repo_dir: Path) -> dict[str, dict]:
    """Parsed ADR-Frontmatter aus docs/adr/ und sammelt Klickdummy-spezifische Felder.

    Returnt {adr_local_ref: {realizes_use_cases: [...], replaces_system_ref: ..., ...}}.
    """
    out: dict[str, dict] = {}
    adr_dir = repo_dir / "docs" / "adr"
    if not adr_dir.is_dir():
        return out
    for adr_path in sorted(adr_dir.glob("ADR-*.md")):
        try:
            text = adr_path.read_text("utf-8")
        except OSError:
            continue
        m = _FRONTMATTER_RE.match(text)
        if not m:
            continue
        try:
            fm = yaml.safe_load(m.group(1)) or {}
        except yaml.YAMLError:
            continue
        # ADR-local-ID konstruieren — wir nehmen 'meiki:<adr_id>' für meiki-hub etc.
        adr_id = fm.get("adr_id")
        if not adr_id:
            continue
        # Wir kennen das Org-Prefix nicht hier; konstruieren beide Varianten
        repo_short = repo_dir.name.removesuffix("-hub")
        for prefix in (f"{repo_short}:", f"{repo_dir.name}:"):
            out[f"{prefix}{adr_id}"] = {
                "realizes_use_cases": fm.get("realizes_use_cases") or [],
                "replaces_system_ref": fm.get("replaces_system_ref"),
                "integrates_with_ref": fm.get("integrates_with_ref"),
            }
    return out


# ---- FV-Inventur-Reader -----------------------------------------------------

def read_fv_inventur(repo_dir: Path) -> dict[str, dict]:
    """Returnt {fv_id: fv_dict} aus docs/inventur/fv-inventur.yaml."""
    path = repo_dir / "docs" / "inventur" / "fv-inventur.yaml"
    if not path.is_file():
        return {}
    try:
        data = yaml.safe_load(path.read_text("utf-8")) or {}
    except yaml.YAMLError:
        return {}
    return {fv["id"]: fv for fv in data.get("fachverfahren", []) if isinstance(fv, dict) and "id" in fv}


# ---- Use-Case-Discovery -----------------------------------------------------

def find_use_cases(repo_dir: Path) -> dict[str, dict]:
    """Returnt {uc_id: {persona, name, path, ...}} aus docs/use-cases/."""
    out: dict[str, dict] = {}
    uc_dir = repo_dir / "docs" / "use-cases"
    if not uc_dir.is_dir():
        return out
    for uc_path in sorted(uc_dir.rglob("UC-*.md")):
        try:
            text = uc_path.read_text("utf-8")
        except OSError:
            continue
        m = _FRONTMATTER_RE.match(text)
        if not m:
            continue
        try:
            fm = yaml.safe_load(m.group(1)) or {}
        except yaml.YAMLError:
            continue
        uc_id = fm.get("uc_id")
        if uc_id:
            out[uc_id] = {
                "name": fm.get("name", ""),
                "primaer_akteur": fm.get("primaer_akteur"),
                "realisiert_von_klickdummy": fm.get("realisiert_von_klickdummy"),
                "path": uc_path,
                "prio": fm.get("prio"),
                "status": fm.get("status"),
            }
    return out


# ---- Render-Fallback (Spec → klickbare HTML wenn shell.html fehlt) ---------

# ---- Domain-Style + Synthetic-Data-Helpers (Render v2) ----------------------

_DOMAIN_STYLES = {
    "public-admin": {"accent": "#0050a3", "accent_bg": "#e3f0ff", "font_h": "Georgia, 'Times New Roman', serif"},
    "saas":         {"accent": "#2563eb", "accent_bg": "#eff6ff", "font_h": "-apple-system, 'Segoe UI', system-ui, sans-serif"},
    "konzern-pilot":{"accent": "#7c2d12", "accent_bg": "#fff4ed", "font_h": "-apple-system, system-ui, sans-serif"},
    "forschung":    {"accent": "#0d9488", "accent_bg": "#f0fdfa", "font_h": "-apple-system, system-ui, sans-serif"},
    "default":      {"accent": "#374151", "accent_bg": "#f3f4f6", "font_h": "-apple-system, system-ui, sans-serif"},
    # Alias-Migration (siehe ADR-218 Rev 3)
    "lra-pilot":    {"accent": "#0050a3", "accent_bg": "#e3f0ff", "font_h": "Georgia, 'Times New Roman', serif"},
}


def read_doc_profile(repo_dir: Path) -> str:
    """Returnt doc-profile-Name oder 'default'."""
    path = repo_dir / "docs" / "doc-profile.yaml"
    if not path.is_file():
        return "default"
    try:
        data = yaml.safe_load(path.read_text("utf-8")) or {}
    except yaml.YAMLError:
        return "default"
    return str(data.get("profile") or "default")


_BUERGER_POOL = [
    {"vorname": "Sabine", "nachname": "Müller",  "gebdatum": "1972-03-14",
     "adresse": "Friedrichstr. 12, 79541 Lörrach",  "kanal": "postbox"},
    {"vorname": "Klaus",  "nachname": "Schmidt", "gebdatum": "1985-08-02",
     "adresse": "Bahnhofstr. 7, 79588 Efringen",    "kanal": "email"},
    {"vorname": "Ayşe",   "nachname": "Yilmaz",  "gebdatum": "1990-11-29",
     "adresse": "Hauinger Str. 33, 79541 Lörrach",  "kanal": "brief"},
    {"vorname": "Dimitri","nachname": "Petrov",  "gebdatum": "1968-05-21",
     "adresse": "Lindenplatz 2, 79576 Weil",        "kanal": "postbox"},
    {"vorname": "Maria",  "nachname": "Weber",   "gebdatum": "1978-09-09",
     "adresse": "Mühlenweg 18, 79585 Steinen",      "kanal": "email"},
    {"vorname": "Jens",   "nachname": "Lange",   "gebdatum": "1995-02-17",
     "adresse": "Im Sandgrund 5, 79540 Lörrach",    "kanal": "postbox"},
]

# Akten-Typ + KD-Hint: kd_hint wird zur Render-Zeit gegen die bekannten KDs
# gematcht. Wenn ein KD existiert (z. B. wohngeld), wird die Akten-Zeile mit
# data-target-kd + data-target-url versehen → Sprung-CTA im Akte-Modal.
_AKTEN_PROFIL_POOL = [
    # kd_hint = KD-Name (cross-repo möglich); entry = Spec-Screen-ID, auf die der
    # Ziel-KD bei externem Sprung initialisieren soll (für *bestehende* Akten;
    # statt Default = „neuer Antrag/Eingang"). Hash-Routing: ?#screen-<entry>.
    {"typ": "Antrag Wohngeld",     "prefix": "WOH", "kd_hint": "wohngeld", "entry": "antragsdaten"},
    {"typ": "Bauantrag",           "prefix": "BAU", "kd_hint": None,       "entry": None},
    {"typ": "UVG-Erstantrag",      "prefix": "UVG", "kd_hint": "uvg",      "entry": "antragsdaten_uvg"},
    {"typ": "Asyl-Folgeantrag",    "prefix": "ASY", "kd_hint": "asyl",     "entry": "vorgangs_uebersicht"},
    {"typ": "Bewohnerparkausweis", "prefix": "BPK", "kd_hint": None,       "entry": None},
    {"typ": "Hundesteuer",         "prefix": "HDS", "kd_hint": None,       "entry": None},
]


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
    p = _BUERGER_POOL[viewer_idx % len(_BUERGER_POOL)] if viewer_idx is not None else _row_buerger(row_idx)
    a = _row_akte(row_idx)
    if ("akten" in n or "vorgang" in n) and "name" in n:
        return f"{a['typ']} – {p['nachname']}"
    if "_id" in n or n.endswith("id") or "akten" in n:
        if "akten" in n or n == "akten_id":
            return f"{a['prefix']}-2026-{row_idx+1:04d}"
        prefix = "".join(c for c in n.upper().replace("_ID", "").replace("_REF", "") if c.isalpha())[:3] or "ID"
        return f"{prefix}-2026-{row_idx+1:04d}"
    if "date" in n or "datum" in n or n.endswith("_ts") or n.endswith("_bis") or n.endswith("_ab") or "_at" in n:
        if "geb" in n or "geburts" in n:
            return p["gebdatum"]
        return f"2026-{(row_idx%9)+1:02d}-{(row_idx%27)+1:02d}"
    if n in ("namen", "name", "vorname", "nachname") or "buerger" in n and "name" in n or "person" in n and "name" in n:
        if n == "vorname":
            return p["vorname"]
        if n == "nachname":
            return p["nachname"]
        return f"{p['vorname']} {p['nachname']}"
    if "name" in n or "titel" in n or "title" in n:
        return f"Beispiel {s}"
    if "status" in n:
        return ["aktiv", "in_pruefung", "abgeschlossen", "wartet", "offen"][row_idx % 5]
    if "betrag" in n or "preis" in n or "summe" in n or "kosten" in n or "menge" in n and "geld" in n:
        v = (row_idx + 1) * 1234.56
        return f"{v:,.2f} €".replace(",", "X").replace(".", ",").replace("X", ".")
    if "menge" in n or "anzahl" in n or "count" in n:
        return str((row_idx + 1) * 10)
    if "kanal" in n or "bevorzugt" in n:
        return p["kanal"]
    if "konfidenz" in n or "score" in n:
        return f"0.{85 - row_idx*3}"
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


def _synth_entity_table(entity_name: str, entity_def: Any, n_rows: int = 3,
                       screen_id: str | None = None,
                       known_kds: dict[str, str] | None = None,
                       known_kd_repos: dict[str, str] | None = None,
                       viewer_idx: int | None = None) -> str:
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
                    f'{extra}>'
                    f'{html.escape(v)}</a></td>'
                )
            else:
                cells.append(f'<td>{html.escape(v)}</td>')
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


# ---- Spec-Layer (X-Ray) Trace-Strip ----------------------------------------
# ADR-211-konform: jeder Chip ist 1:1 aus der Spec abgeleitet. Fehlt das Feld,
# wird ein "nicht deklariert"-Chip mit dem exakten Spec-Feld zum Ergänzen
# gerendert (Evidenz-Disziplin: nie erfinden — vgl. akte_next-Muster). Sichtbar
# nur bei body.spec-view (globaler Toggle / Taste "s"), damit die Echt-App-
# Illusion für den Stakeholder-Walkthrough erhalten bleibt.

_OFFRAMP_CHIP_CLASS = {
    "static": "tr-static",
    "parity-staging": "tr-staging",
    "parity-green": "tr-green",
    "removed": "tr-removed",
}


def _screen_use_cases(s: dict) -> tuple[list[str], str]:
    """Betroffene Use Cases + Quell-Feld.

    Priorität: use_cases[] (first-class) > konzept_ref[] > akte_next.uc.
    """
    uc = s.get("use_cases")
    if isinstance(uc, list) and uc:
        return [str(x) for x in uc], "use_cases"
    kr = s.get("konzept_ref")
    if isinstance(kr, list) and kr:
        return [str(x) for x in kr], "konzept_ref"
    if isinstance(kr, str) and kr:
        return [kr], "konzept_ref"
    an = s.get("akte_next")
    if isinstance(an, dict) and an.get("uc"):
        return [str(an["uc"])], "akte_next.uc"
    return [], ""


def _screen_coverage(s: dict) -> tuple[int, int, list[str], list[str]]:
    """Pro-Screen Parity-Coverage aus parity_acceptance.

    Selbe Klassifikation wie gen_e2e (render_assertion/is_fragile_selector) —
    eine SoR für "ausführbar vs. prose-only vs. fragil".
    Returnt (n_executable, n_prose, prose_ids, fragile_ids).
    """
    pa = s.get("parity_acceptance") or []
    n_exec = n_prose = 0
    prose_ids: list[str] = []
    fragile_ids: list[str] = []
    for item in pa:
        if not isinstance(item, dict):
            continue
        a = item.get("assert")
        if render_assertion(a) is not None:
            n_exec += 1
            if isinstance(a, dict) and is_fragile_selector(a.get("selector")):
                fragile_ids.append(str(item.get("id", "?")))
        else:
            n_prose += 1
            prose_ids.append(str(item.get("id", "?")))
    return n_exec, n_prose, prose_ids, fragile_ids


def build_trace_strip(s: dict, klass: str, role: str, accept_status: dict) -> str:
    """Kompakter, spec-abgeleiteter Chip-Streifen pro Screen (Spec-Sicht/X-Ray)."""
    chips: list[str] = []

    # 📋 Betroffene Use Cases
    ucs, uc_src = _screen_use_cases(s)
    if ucs:
        shown = ", ".join(html.escape(u) for u in ucs[:3])
        more = f" +{len(ucs) - 3}" if len(ucs) > 3 else ""
        chips.append(
            f'<span class="tr-chip" title="Betroffene Use Cases (Spec-Feld: {uc_src}): '
            f'{html.escape(", ".join(ucs))}">📋 UC: {shown}{more}</span>'
        )
    else:
        chips.append(
            '<span class="tr-chip tr-missing" title="Kein UC-Bezug in der Spec — '
            'ergänzen via screen.use_cases: [..] oder konzept_ref: [..]">'
            '📋 UC nicht deklariert</span>'
        )

    # 📦 Entities + Datenfelder
    konsumiert = s.get("konsumiert_entities") or []
    lokal = s.get("lokale_entities") or []
    datafields = s.get("datafields") or []
    ent_names: list[str] = []
    for e in list(konsumiert) + list(lokal):
        if isinstance(e, dict):
            ent_names.append(str(e.get("name") or e.get("entity") or "?"))
        else:
            ent_names.append(str(e))
    n_ent = len(ent_names)
    n_df = len(datafields) if isinstance(datafields, list) else 0
    if n_ent or n_df:
        title = "Entities: " + (", ".join(html.escape(x) for x in ent_names) or "—")
        if n_df:
            title += f" · {n_df} Datenfeld(er)"
        df_part = f" · {n_df} Feld(er)" if n_df else ""
        ent_word = "Entität" if n_ent == 1 else "Entitäten"
        chips.append(
            f'<span class="tr-chip" title="{title}">📦 {n_ent} {ent_word}{df_part}</span>'
        )
    else:
        chips.append(
            '<span class="tr-chip tr-missing" title="Keine Entities/Datenfelder '
            'deklariert — ergänzen via konsumiert_entities / lokale_entities / '
            'datafields">📦 keine Daten deklariert</span>'
        )

    # 🏷 class · role (I2)
    chips.append(
        f'<span class="tr-chip" title="Spec-Klasse (I2) · Spec-Rolle">'
        f'🏷 {html.escape(klass)} · {html.escape(role)}</span>'
    )

    # 🚦 Off-Ramp-Status (I3)
    ors = s.get("off_ramp_status")
    if ors:
        cls = _OFFRAMP_CHIP_CLASS.get(str(ors), "tr-static")
        chips.append(
            f'<span class="tr-chip {cls}" title="Off-Ramp-Status (I3, Spec-Feld: '
            f'off_ramp_status)">🚦 {html.escape(str(ors))}</span>'
        )
    else:
        chips.append(
            '<span class="tr-chip tr-missing" title="off_ramp_status fehlt '
            '(I3-Pflichtfeld) — Spec ergänzen">🚦 off-ramp fehlt</span>'
        )

    # ✓/⚠ Acceptance (kompakt, mit Frische)
    for axis, info in (accept_status or {}).items():
        label = "PO-Sign-Off" if axis == "spec_signed" else "Workshop-Walk"
        st = info.get("status")
        if st == "signed":
            chips.append(
                f'<span class="tr-chip tr-ok" title="{label}: '
                f'{html.escape(info.get("latest_by") or "?")} · {info.get("latest_date")}">'
                f'✓ {html.escape(axis)} {info.get("age_days")}d</span>'
            )
        elif st == "stale":
            chips.append(
                f'<span class="tr-chip tr-warn" title="{label}: letzter Eintrag '
                f'{info.get("age_days")}d alt — neue Abnahme empfohlen">'
                f'⚠ {html.escape(axis)} {info.get("age_days")}d</span>'
            )

    # 🎯 Parity-Coverage (I1, aus parity_acceptance — selbe Klassifikation wie gen_e2e)
    n_exec, n_prose, prose_ids, fragile_ids = _screen_coverage(s)
    total = n_exec + n_prose
    if total:
        extra = []
        if n_prose:
            extra.append(f"{n_prose} prose-only")
        if fragile_ids:
            extra.append(f"⚠{len(fragile_ids)} fragil")
        suffix = (" · " + " · ".join(extra)) if extra else ""
        tcls = "tr-ok" if (n_prose == 0 and not fragile_ids) else "tr-warn"
        title = f"Parity-Coverage (aus parity_acceptance): {n_exec}/{total} ausführbar"
        if prose_ids:
            title += " · prose-only: " + ", ".join(html.escape(x) for x in prose_ids)
        if fragile_ids:
            title += " · fragile Selektoren: " + ", ".join(html.escape(x) for x in fragile_ids)
        chips.append(
            f'<span class="tr-chip {tcls}" title="{title}">🎯 {n_exec}/{total} ausführbar{suffix}</span>'
        )
    else:
        chips.append(
            '<span class="tr-chip tr-missing" title="Keine parity_acceptance-Checks '
            '(I1) — Spec ergänzen">🎯 keine Parity-Checks</span>'
        )

    # ❓ Validierungsfrage
    vf = s.get("validierungsfrage")
    if vf:
        chips.append(
            f'<span class="tr-chip tr-q" title="{html.escape(str(vf))}">❓ Validierungsfrage</span>'
        )

    return (
        '<div class="trace-strip" aria-label="Spec-Sicht (X-Ray)">'
        '<span class="trace-label">🔍 Spec-Sicht</span>'
        + "".join(chips)
        + "</div>"
    )


# ---- Render v2 Template ----------------------------------------------------

RENDER_FALLBACK_TEMPLATE = """<!DOCTYPE html>
<html lang="de">
<head>
<meta charset="utf-8">
<title>Klickdummy: {kd_name} — {title}</title>
<style>
  :root {{
    --accent: {style_accent};
    --accent-bg: {style_accent_bg};
    --font-h: {style_font_h};
  }}
  * {{ box-sizing: border-box; }}
  body {{ font-family: -apple-system, "Segoe UI", system-ui, sans-serif; margin: 0; color: #1f2937; background: #f5f7fa; }}
  header.topbar {{ background: #fff; padding: 14px 24px; border-bottom: 1px solid #e3e8ee; display: flex; align-items: center; gap: 16px; flex-wrap: wrap; }}
  header.topbar h1 {{ font-family: var(--font-h); margin: 0; font-size: 19px; flex: 1; color: var(--accent); min-width: 200px; }}
  header.topbar .meta {{ color: #6b7280; font-size: 12px; }}
  header.topbar .badges span {{ display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 11px; font-weight: 600; margin-right: 4px; background: var(--accent-bg); color: var(--accent); }}
  header.topbar .persona-switch label {{ font-size: 12px; color: #6b7280; margin-right: 6px; }}
  header.topbar .persona-switch select {{ padding: 5px 10px; border: 1px solid #e3e8ee; border-radius: 4px; font-size: 13px; background: #fff; }}
  nav.tabs {{ background: #fff; border-bottom: 1px solid #e3e8ee; padding: 0 24px; display: flex; gap: 4px; overflow-x: auto; }}
  nav.tabs button {{ background: none; border: 0; padding: 12px 14px; cursor: pointer; font-size: 13px; color: #6b7280; border-bottom: 3px solid transparent; white-space: nowrap; }}
  nav.tabs button:hover {{ color: var(--accent); background: var(--accent-bg); }}
  nav.tabs button.active {{ color: var(--accent); border-bottom-color: var(--accent); font-weight: 600; }}
  nav.tabs button.hidden {{ display: none; }}
  /* Sidebar-Layout (User-Feedback: Tab-Scrolling bei >5 Screens UX-unschön) */
  body.has-sidebar main {{ display: grid; grid-template-columns: 240px 1fr; gap: 0; padding: 0; max-width: none; min-height: calc(100vh - 110px); }}
  body.has-sidebar nav.tabs {{ display: none; }}
  aside.sidebar {{ display: none; background: #fff; border-right: 1px solid #e3e8ee; padding: 16px 0; overflow-y: auto; }}
  body.has-sidebar aside.sidebar {{ display: block; }}
  aside.sidebar h3 {{ font-family: var(--font-h); margin: 0 16px 8px; font-size: 11px; text-transform: uppercase; letter-spacing: 0.5px; color: #6b7280; padding-top: 12px; }}
  aside.sidebar h3:first-child {{ padding-top: 0; }}
  aside.sidebar button {{ display: block; width: 100%; text-align: left; background: none; border: 0; padding: 9px 16px 9px 24px; cursor: pointer; font-size: 13px; color: #1f2937; border-left: 3px solid transparent; white-space: normal; line-height: 1.3; }}
  aside.sidebar button:hover {{ background: var(--accent-bg); color: var(--accent); }}
  aside.sidebar button.active {{ background: var(--accent-bg); color: var(--accent); border-left-color: var(--accent); font-weight: 600; }}
  aside.sidebar button.hidden {{ display: none; }}
  aside.sidebar button small {{ display: block; color: #9ca3af; font-size: 10px; margin-top: 2px; }}
  body.has-sidebar section.screen {{ padding: 24px; max-width: 900px; }}
  main {{ padding: 24px; max-width: 1100px; margin: 0 auto; }}
  section.screen {{ display: none; }}
  section.screen.active {{ display: block; }}
  /* APP-FRAME — macht jeden Screen als "Bildschirm" einer App erkennbar */
  .app-frame {{ background: #fff; border: 1px solid #d0d5dd; border-radius: 8px; overflow: hidden; box-shadow: 0 4px 24px rgba(0,0,0,.08); }}
  .app-bar {{ background: var(--accent); color: #fff; padding: 8px 14px; display: flex; align-items: center; gap: 10px; font-family: var(--font-h); }}
  .app-bar .traffic {{ display: flex; gap: 5px; margin-right: 8px; }}
  .app-bar .traffic span {{ width: 11px; height: 11px; border-radius: 50%; display: inline-block; opacity: 0.85; }}
  .app-bar .traffic .r {{ background: #ed6a5e; }}
  .app-bar .traffic .y {{ background: #f5bf4f; }}
  .app-bar .traffic .g {{ background: #61c554; }}
  .app-bar .app-icon {{ font-size: 16px; }}
  .app-bar .app-name {{ font-size: 13px; font-weight: 600; flex: 1; }}
  .app-bar .app-user {{ font-size: 12px; opacity: 0.95; background: rgba(255,255,255,.15); padding: 3px 9px; border-radius: 12px; }}
  .app-toolbar {{ background: #f8fafc; border-bottom: 1px solid #e3e8ee; padding: 10px 16px; display: flex; align-items: center; gap: 12px; flex-wrap: wrap; }}
  .app-toolbar .breadcrumb {{ color: #6b7280; font-size: 12px; }}
  .app-toolbar .breadcrumb b {{ color: #1f2937; }}
  .app-toolbar h2 {{ font-family: var(--font-h); margin: 0; font-size: 18px; color: var(--accent); flex: 1; }}
  .app-toolbar .sid {{ font-family: monospace; font-size: 10px; color: #6b7280; background: var(--accent-bg); padding: 1px 5px; border-radius: 3px; }}
  .app-content {{ padding: 16px 20px; background: #fdfdfe; min-height: 280px; }}
  .app-actionbar {{ background: #f8fafc; border-top: 1px solid #e3e8ee; padding: 10px 16px; display: flex; gap: 8px; align-items: center; }}
  .app-actionbar .actions {{ display: flex; flex-wrap: wrap; gap: 8px; margin: 0; }}
  .app-statusbar {{ background: #eef1f5; border-top: 1px solid #d0d5dd; padding: 6px 16px; display: flex; justify-content: space-between; font-size: 11px; color: #6b7280; }}
  .app-statusbar code {{ background: rgba(0,0,0,.05); padding: 1px 5px; border-radius: 3px; font-size: 10px; }}
  .ac-chip {{ display: inline-block; padding: 1px 6px; border-radius: 3px; font-size: 10px; font-weight: 600; margin-right: 6px; cursor: help; }}
  .ac-signed {{ background: #d1fae5; color: #065f46; border: 1px solid #a7f3d0; }}
  .ac-stale  {{ background: #fef3c7; color: #92400e; border: 1px solid #fde68a; }}
  /* Info-Button + Modal (Funktionen vom Bildschirm getrennt) */
  .app-bar .info-btn, .app-bar .help-btn {{ background: rgba(255,255,255,.2); color: #fff; border: 1px solid rgba(255,255,255,.4); border-radius: 4px; padding: 2px 8px; font-size: 12px; cursor: pointer; }}
  .app-bar .info-btn:hover, .app-bar .help-btn:hover {{ background: rgba(255,255,255,.35); }}
  /* Style-Switcher in Topbar (User-Feedback 2026-05-25): live demo zwischen
     Greenfield- und Bestand-System-Looks ohne re-render */
  .style-switch {{ display: flex; align-items: center; gap: 6px; }}
  .style-switch label {{ font-size: 12px; color: #6b7280; }}
  .style-switch select {{ padding: 5px 10px; border: 1px solid #e3e8ee; border-radius: 4px; font-size: 13px; background: #fff; }}
  .info-modal-bg {{ display: none; position: fixed; inset: 0; background: rgba(0,0,0,.45); z-index: 200; align-items: center; justify-content: center; }}
  .info-modal-bg.show {{ display: flex; }}
  .info-modal {{ background: #fff; border-radius: 8px; box-shadow: 0 8px 32px rgba(0,0,0,.25); max-width: 600px; width: 90%; max-height: 80vh; overflow-y: auto; }}
  .info-modal-head {{ background: var(--accent); color: #fff; padding: 10px 18px; display: flex; justify-content: space-between; align-items: center; border-radius: 8px 8px 0 0; }}
  .info-modal-head h3 {{ margin: 0; font-family: var(--font-h); font-size: 15px; }}
  .info-modal-head .close-btn {{ background: rgba(255,255,255,.2); color: #fff; border: 0; padding: 2px 10px; border-radius: 4px; cursor: pointer; font-size: 16px; line-height: 1; }}
  .info-modal-body {{ padding: 16px 20px; font-size: 13px; }}
  .info-modal-body h4 {{ font-family: var(--font-h); font-size: 13px; color: var(--accent); margin: 12px 0 6px; text-transform: uppercase; letter-spacing: 0.5px; }}
  .info-modal-body ul {{ margin: 0 0 12px; padding-left: 20px; }}
  .info-modal-body li {{ margin-bottom: 4px; }}
  .info-modal-body code {{ background: var(--accent-bg); padding: 1px 5px; border-radius: 3px; font-size: 12px; }}
  /* Sub-Tabs im App-Content */
  .sub-tabs {{ display: flex; gap: 2px; border-bottom: 1px solid #e3e8ee; margin-bottom: 12px; overflow-x: auto; }}
  .sub-tabs button {{ background: none; border: 0; padding: 8px 12px; cursor: pointer; font-size: 12px; color: #6b7280; border-bottom: 2px solid transparent; white-space: nowrap; }}
  .sub-tabs button:hover {{ color: var(--accent); }}
  .sub-tabs button.active {{ color: var(--accent); border-bottom-color: var(--accent); font-weight: 600; background: var(--accent-bg); }}
  .sub-panel {{ display: none; }}
  .sub-panel.active {{ display: block; }}
  .persona-chip {{ display: inline-block; padding: 2px 8px; border-radius: 12px; background: var(--accent-bg); color: var(--accent); font-size: 11px; font-weight: 600; margin-right: 4px; }}
  .card {{ background: #fff; border: 1px solid #e3e8ee; border-radius: 8px; padding: 16px 18px; margin-bottom: 16px; box-shadow: 0 1px 2px rgba(0,0,0,.03); }}
  .card h3 {{ font-family: var(--font-h); margin: 0 0 10px; font-size: 13px; color: var(--accent); text-transform: uppercase; letter-spacing: 0.5px; }}
  .functions ul {{ margin: 0; padding-left: 20px; }}
  .functions li {{ margin-bottom: 6px; font-size: 14px; color: #1f2937; }}
  table.entity {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
  table.entity th {{ background: var(--accent-bg); color: var(--accent); padding: 6px 10px; text-align: left; font-weight: 600; border-bottom: 1px solid #e3e8ee; }}
  table.entity td {{ padding: 6px 10px; border-bottom: 1px solid #f0f3f6; }}
  table.entity tr:hover {{ background: #fafbfc; }}
  table.entity a.akten-link {{ color: var(--accent); text-decoration: underline dotted; cursor: pointer; font-weight: 500; }}
  table.entity a.akten-link:hover {{ background: var(--accent-bg); text-decoration: underline; }}
  a.akte-next-cta {{ display: inline-block; background: var(--accent); color: #fff !important; padding: 8px 14px; border-radius: 4px; text-decoration: none; font-weight: 600; margin-top: 8px; }}
  a.akte-next-cta:hover {{ opacity: 0.85; }}
  .entity-title {{ font-family: monospace; font-size: 11px; color: var(--accent); margin: 14px 0 4px; }}
  .actions {{ display: flex; flex-wrap: wrap; gap: 8px; margin-top: 4px; }}
  .actions button {{ padding: 8px 14px; border: 1px solid var(--accent); background: var(--accent); color: #fff; border-radius: 4px; cursor: pointer; font-size: 13px; font-weight: 600; }}
  .actions button.secondary {{ background: #fff; color: var(--accent); }}
  .cross-links {{ margin-top: 14px; display: flex; flex-wrap: wrap; gap: 6px; }}
  .cross-links a {{ display: inline-block; padding: 6px 12px; background: #fff; border: 1px dashed #cdd5dd; border-radius: 4px; color: var(--accent); text-decoration: none; font-size: 12px; }}
  .cross-links a:hover {{ border-color: var(--accent); background: var(--accent-bg); }}
  footer {{ background: #fff; border-top: 1px solid #e3e8ee; padding: 12px 24px; font-size: 12px; color: #6b7280; text-align: center; margin-top: 30px; }}
  footer a {{ color: var(--accent); }}
  footer code {{ font-size: 11px; background: var(--accent-bg); padding: 1px 5px; border-radius: 3px; }}
  .render-mode {{ font-size: 11px; color: #9ca3af; text-align: center; padding: 6px; background: #eef1f5; }}
  .empty-state {{ text-align: center; padding: 40px; color: #6b7280; }}
  .placeholder {{ background: #fef0d0; }}
  /* Spec-Layer (X-Ray) — Trace-Strip pro Screen, nur bei body.spec-view sichtbar */
  .trace-strip {{ display: none; }}
  body.spec-view .trace-strip {{ display: flex; flex-wrap: wrap; align-items: center; gap: 6px; margin-top: 8px; padding: 8px 10px; background: #1f2937; border-radius: 6px; }}
  .trace-strip .trace-label {{ color: #93c5fd; font-size: 10px; font-weight: 700; text-transform: uppercase; letter-spacing: .5px; margin-right: 4px; }}
  .tr-chip {{ display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 11px; font-weight: 600; background: #374151; color: #e5e7eb; cursor: help; border: 1px solid #4b5563; }}
  .tr-chip.tr-missing {{ background: #4b5563; color: #fca5a5; border-color: #6b7280; border-style: dashed; }}
  .tr-chip.tr-ok {{ background: #065f46; color: #d1fae5; border-color: #047857; }}
  .tr-chip.tr-warn {{ background: #78350f; color: #fef3c7; border-color: #92400e; }}
  .tr-chip.tr-static {{ background: #374151; color: #d1d5db; }}
  .tr-chip.tr-staging {{ background: #1e3a8a; color: #bfdbfe; border-color: #1d4ed8; }}
  .tr-chip.tr-green {{ background: #065f46; color: #d1fae5; border-color: #047857; }}
  .tr-chip.tr-removed {{ background: #7f1d1d; color: #fecaca; border-color: #991b1b; }}
  .tr-chip.tr-q {{ background: #4c1d95; color: #ede9fe; border-color: #6d28d9; }}
  /* Spec-Sicht-Toggle im Header */
  .spec-toggle {{ display: inline-flex; align-items: center; gap: 6px; padding: 5px 12px; border: 1px solid #d0d5dd; border-radius: 4px; background: #fff; font-size: 13px; cursor: pointer; color: #374151; }}
  .spec-toggle.on {{ background: #1f2937; color: #fff; border-color: #1f2937; }}
  .spec-toggle .dot {{ width: 8px; height: 8px; border-radius: 50%; background: #cbd5e1; }}
  .spec-toggle.on .dot {{ background: #34d399; }}
  /* Custom-CSS-Hook — wenn spec.app_skin.custom_css gesetzt, lädt nach dem inline-Style ein zusätzliches CSS */
  /* Damit kann Bestand-System-Skin (OK.Wobis, eigene CI etc.) injiziert werden, ohne Render zu ändern */
</style>
{custom_css_link}
<style>
  /* Spacer-Style-Block — verhindert dass {{custom_css_link}} Format-Hole stört */
  .render-skin-applied {{ /* marker */ }}
  /* Feedback-Widget pro Screen */
  .fb {{ position: fixed; bottom: 16px; right: 16px; width: 320px; background: #fff; border: 1px solid var(--accent); border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,.12); font-size: 13px; z-index: 100; }}
  .fb-head {{ background: var(--accent); color: #fff; padding: 8px 12px; border-radius: 8px 8px 0 0; cursor: pointer; display: flex; justify-content: space-between; align-items: center; font-weight: 600; }}
  .fb-body {{ padding: 12px; }}
  .fb-body.hidden {{ display: none; }}
  .fb label {{ display: block; margin: 6px 0 2px; font-size: 12px; color: #555; }}
  .fb select, .fb textarea {{ width: 100%; box-sizing: border-box; padding: 4px 6px; border: 1px solid #ccc; border-radius: 4px; font-size: 13px; font-family: inherit; }}
  .fb textarea {{ height: 60px; resize: vertical; }}
  .fb .row {{ display: flex; gap: 6px; margin-top: 8px; }}
  .fb button {{ padding: 6px 10px; border: 1px solid var(--accent); background: var(--accent); color: #fff; border-radius: 4px; cursor: pointer; font-size: 13px; }}
  .fb button.secondary {{ background: #fff; color: var(--accent); }}
  .fb .status {{ margin-top: 6px; font-size: 12px; color: #060; }}
  .fb .screen-ctx {{ background: var(--accent-bg); padding: 4px 8px; border-radius: 3px; font-size: 11px; color: var(--accent); margin-bottom: 6px; }}
</style>
</head>
<body class="{body_class}">

<header class="topbar">
  <h1>{title}</h1>
  <div>
    <div class="badges">
      <span>class: {klass}</span>
      <span>role: {role}</span>
      <span>sunset: {sunset}</span>
    </div>
    <div class="meta">KD <code>{kd_name}</code> · Repo <code>{repo}</code></div>
  </div>
  <div class="persona-switch">
    <label for="persona-select">👤 Persona</label>
    <select id="persona-select">
      <option value="__all__">— alle Personas —</option>
      {persona_options}
    </select>
  </div>
  {skin_switcher_html}
  <button class="spec-toggle" id="spec-toggle" title="Spec-Sicht (X-Ray) ein/aus — Taste S. Zeigt UC, Daten, Status & Coverage pro Screen, direkt aus der Spec.">
    <span class="dot"></span> Spec-Sicht
  </button>
</header>
<script>window.INITIAL_SKIN = "{initial_skin}";</script>

<nav class="tabs" id="tabs">
  {tab_buttons}
</nav>

<main>
  <aside class="sidebar" id="sidebar">
    {sidebar_content}
  </aside>
  <div class="screens-area">
    {screen_sections}
    <section class="screen" id="screen-__empty__">
      <div class="empty-state">
        <p>Keine Screens für die gewählte Persona — wähle eine andere Persona oben rechts.</p>
      </div>
    </section>
  </div>
</main>

<footer>
  Klickdummy <code>{kd_name}</code> (Spec-Render mit synthetischen Daten)
  · Spec: <a href="/{spec_rel}">{spec_rel}</a>
  · <a href="/genesor/screen-lineage-{repo}-{kd_name}.html">🕸 Screen-Lineage</a>
  · <a href="/genesor/">↩ zur Genesor-Übersicht</a>
</footer>

<!-- Globales Info-Modal (Funktionen / Verhalten vom Bildschirm getrennt) -->
<div class="info-modal-bg" id="info-modal-bg" onclick="if(event.target===this)closeInfoModal()">
  <div class="info-modal">
    <div class="info-modal-head">
      <h3 id="info-modal-title">Funktionen / Verhalten</h3>
      <button class="close-btn" onclick="closeInfoModal()">×</button>
    </div>
    <div class="info-modal-body" id="info-modal-body">—</div>
  </div>
</div>

<div class="render-mode">Render-Mode: Auto-Generator v2 aus screens-spec.yaml · synthetische Beispiel-Daten, kein Backend</div>

<!-- Feedback-Widget pro Screen — per platform:ADR-211 Rev 13 §Co-Creation A-light -->
<div class="fb" id="fb-widget">
  <div class="fb-head" onclick="document.getElementById('fb-body').classList.toggle('hidden')">
    <span>💬 Feedback zu diesem Screen</span>
    <span>▾</span>
  </div>
  <div class="fb-body" id="fb-body">
    <div class="screen-ctx">Aktiver Screen: <b><span id="fb-current-screen">—</span></b> · Persona: <b><span id="fb-current-persona">alle</span></b></div>
    <label>Kategorie</label>
    <select id="fb-cat">
      <option value="missing-content">Inhalt fehlt / unvollständig</option>
      <option value="wrong-content">Inhalt falsch</option>
      <option value="layout">Layout / Reihenfolge</option>
      <option value="persona-missing">Persona-Sicht fehlt</option>
      <option value="data-unrealistic">Beispiel-Daten unrealistisch</option>
      <option value="idea">Vorschlag</option>
    </select>
    <label>Acceptance</label>
    <select id="fb-verdict">
      <option value="">— wählen —</option>
      <option value="accepted">✓ Accepted</option>
      <option value="needs-change">✎ Needs-Change</option>
      <option value="rejected">✗ Rejected</option>
    </select>
    <label>Was sollte anders sein?</label>
    <textarea id="fb-text" placeholder="Beschreibung — was hast Du erwartet? Was fehlt?"></textarea>
    <div class="row">
      <button onclick="fbDownload()">📥 Download JSON</button>
      <button class="secondary" onclick="fbClipboard()">📋 In Clipboard</button>
    </div>
    <div class="status" id="fb-status"></div>
  </div>
</div>

<script>
  // Sowohl Top-Tabs als auch Sidebar-Buttons fungieren als Navigation
  const tabs = document.querySelectorAll('#tabs button, #sidebar button');
  const screens = document.querySelectorAll('section.screen');
  const personaSelect = document.getElementById('persona-select');

  function showScreen(id) {{
    screens.forEach(s => s.classList.toggle('active', s.id === 'screen-' + id));
    tabs.forEach(t => t.classList.toggle('active', t.dataset.screen === id));
    const ctx = document.getElementById('fb-current-screen');
    if (ctx) ctx.textContent = id;
  }}

  tabs.forEach(t => {{
    t.addEventListener('click', () => showScreen(t.dataset.screen));
  }});

  function applyPersonaFilter() {{
    const p = personaSelect.value;
    document.getElementById('fb-current-persona').textContent = p === '__all__' ? 'alle' : p;
    const visibleScreens = [];
    tabs.forEach(t => {{
      const screenPersonas = (t.dataset.personas || '').split(',').filter(Boolean);
      const visible = p === '__all__' || screenPersonas.includes(p);
      t.classList.toggle('hidden', !visible);
      if (visible) visibleScreens.push(t.dataset.screen);
    }});
    const activeTab = document.querySelector('#tabs button.active:not(.hidden)');
    if (!activeTab && visibleScreens.length) {{
      showScreen(visibleScreens[0]);
    }} else if (!visibleScreens.length) {{
      showScreen('__empty__');
    }}
  }}

  personaSelect.addEventListener('change', applyPersonaFilter);

  // Deep-Link: ?#screen-<id> aus URL respektieren (Cross-KD-Sprung)
  function _initialScreen(defaultId) {{
    if (location.hash.startsWith('#screen-')) {{
      const wanted = location.hash.substring('#screen-'.length);
      if (document.getElementById('screen-' + wanted)) return wanted;
    }}
    return defaultId;
  }}
  if (tabs.length) showScreen(_initialScreen(tabs[0].dataset.screen));
  // Reagiere auch wenn Hash sich ändert (z. B. weiter im Workflow)
  window.addEventListener('hashchange', () => {{
    if (location.hash.startsWith('#screen-')) {{
      const wanted = location.hash.substring('#screen-'.length);
      if (document.getElementById('screen-' + wanted)) showScreen(wanted);
    }}
  }});

  __SKIN_SWITCHER_JS_PLACEHOLDER__

  // Zwei Modal-Funktionen — ℹ Info (Spec) + ❓ Hilfe (End-User)
  function _openModal(prefix, screenId) {{
    const tpl = document.getElementById(prefix + '-' + screenId);
    if (!tpl) return;
    const title = tpl.querySelector('.info-title')?.innerHTML || screenId;
    const content = tpl.querySelector('.info-content')?.innerHTML || '';
    document.getElementById('info-modal-title').innerHTML = title;
    document.getElementById('info-modal-body').innerHTML = content;
    document.getElementById('info-modal-bg').classList.add('show');
  }}
  function openInfoModal(screenId) {{ _openModal('info', screenId); }}
  function openHelpModal(screenId) {{ _openModal('help', screenId); }}
  function openAkteModal(screenId, azs, aname, targetKd, targetUrl, targetRepo) {{
    const tpl = document.getElementById('akte-' + screenId);
    let title = '📁 Akte · ' + (azs || '?');
    if (aname) title += ' · ' + aname;
    // Per-Row-CTA: existiert ein KD für diesen Aktentyp → Sprung-Link.
    // Cross-Repo-Sprünge bekommen einen sichtbaren Repo-Hinweis.
    let cta = '';
    if (targetKd && targetUrl) {{
      let repoHint = '';
      if (targetRepo && targetRepo !== KD_META.repo) {{
        repoHint = ' <span style="font-weight:normal;font-size:12px;opacity:.85;">(cross-repo: '
                 + targetRepo + ')</span>';
      }}
      cta = '<p style="margin:0 0 10px;"><a href="' + targetUrl
          + '" class="akte-next-cta">→ Klickdummy „' + targetKd + '" öffnen</a>'
          + repoHint + '</p>';
    }} else if (targetKd) {{
      cta = '<p style="color:#9ca3af;font-size:13px;margin:0 0 10px;">'
          + '→ Klickdummy für „' + targetKd + '" noch nicht vorhanden.</p>';
    }}
    let extras = '';
    if (tpl) {{
      extras = tpl.querySelector('.info-content')?.innerHTML || '';
    }} else {{
      extras = '<p>Hier würde die Akte/der Vorgang öffnen. Spec-seitig (<code>screen.akte_next:</code>) noch nicht deklariert.</p>';
    }}
    document.getElementById('info-modal-title').innerHTML = title;
    document.getElementById('info-modal-body').innerHTML = cta + extras;
    document.getElementById('info-modal-bg').classList.add('show');
  }}
  document.querySelectorAll('a.akten-link').forEach(a => {{
    a.addEventListener('click', e => {{
      e.preventDefault();
      openAkteModal(
        a.dataset.sid,
        a.dataset.azs || '',
        a.dataset.aname || '',
        a.dataset.targetKd || '',
        a.dataset.targetUrl || '',
        a.dataset.targetRepo || ''
      );
    }});
  }});
  function closeInfoModal() {{
    document.getElementById('info-modal-bg').classList.remove('show');
  }}
  document.addEventListener('keydown', e => {{
    if (e.key === 'Escape') closeInfoModal();
  }});

  // Spec-Layer (X-Ray): globaler Toggle + Taste 's' (außer in Eingabefeldern)
  const specToggle = document.getElementById('spec-toggle');
  function setSpecView(on) {{
    document.body.classList.toggle('spec-view', on);
    if (specToggle) specToggle.classList.toggle('on', on);
  }}
  if (specToggle) {{
    specToggle.addEventListener('click', () =>
      setSpecView(!document.body.classList.contains('spec-view')));
  }}
  document.addEventListener('keydown', e => {{
    if (e.key !== 's' && e.key !== 'S') return;
    const t = e.target;
    if (t && (t.tagName === 'INPUT' || t.tagName === 'TEXTAREA'
              || t.tagName === 'SELECT' || t.isContentEditable)) return;
    setSpecView(!document.body.classList.contains('spec-view'));
  }});

  // Sub-Tabs innerhalb des App-Content
  document.querySelectorAll('.sub-tabs button').forEach(btn => {{
    btn.addEventListener('click', () => {{
      const subId = btn.dataset.sub;
      const container = btn.closest('.app-content');
      if (!container) return;
      container.querySelectorAll('.sub-tabs button').forEach(b => b.classList.remove('active'));
      container.querySelectorAll('.sub-panel').forEach(p => p.classList.remove('active'));
      btn.classList.add('active');
      const panel = container.querySelector('#sub-' + subId);
      if (panel) panel.classList.add('active');
    }});
  }});

  // Feedback-Widget — Payload kennt aktuellen Screen + Persona
  const KD_META = {{
    kd_name: "{kd_name}",
    repo: "{repo}",
    klass: "{klass}",
    role: "{role}"
  }};
  function fbCollect() {{
    return {{
      spec_id: KD_META.kd_name,
      repo: KD_META.repo,
      klickdummy_class: KD_META.klass,
      spec_role: KD_META.role,
      feedback_scope: "screen",
      acceptance_verdict: document.getElementById('fb-verdict')?.value || null,
      screen_id: document.getElementById('fb-current-screen').textContent,
      persona_filter: document.getElementById('fb-current-persona').textContent,
      kategorie: document.getElementById('fb-cat').value,
      text: document.getElementById('fb-text').value,
      ts: new Date().toISOString(),
      generated_from: document.title,
      conforms_to: "platform:ADR-211 Rev 13 §Co-Creation-Loop Pfad A-light"
    }};
  }}
  function fbDownload() {{
    const payload = fbCollect();
    const blob = new Blob([JSON.stringify(payload, null, 2)], {{ type: 'application/json' }});
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `feedback-${{KD_META.kd_name}}-${{payload.screen_id}}-${{Date.now()}}.json`;
    document.body.appendChild(a); a.click(); a.remove();
    URL.revokeObjectURL(url);
    document.getElementById('fb-status').textContent = "✓ heruntergeladen.";
  }}
  async function fbClipboard() {{
    await navigator.clipboard.writeText(JSON.stringify(fbCollect(), null, 2));
    document.getElementById('fb-status').textContent = "✓ im Clipboard.";
  }}
</script>

</body>
</html>
"""


def generate_render_fallback(record: dict, out_dir: Path,
                             known_kds: dict[str, str] | None = None,
                             known_kd_repos: dict[str, str] | None = None) -> Path:
    """Render v2 — multi-Screen klickbares Mockup aus Spec (synthetische Daten).

    ``known_kds`` ist ein optionaler Lookup ``{kd_name: render_url}`` (Genesor-
    weit, cross-repo). Wird an ``_synth_entity_table`` durchgereicht, damit
    Akten-Zeilen automatisch zum Ziel-Fachverfahrens-KD verlinken können.
    """
    d = record["data"]
    kd_name = record["kd"]
    repo = record["repo"]
    title = (d.get("title") or kd_name).split("—")[0].strip()
    klass = d.get("class") or "?"
    role = d.get("spec_role") or "default"
    sunset = (d.get("off_ramp", {}) or {}).get("sunset_after") or "—"

    # Domain-Styling aus doc-profile.yaml
    repo_dir = REPOS_ROOT / repo
    profile = read_doc_profile(repo_dir)
    style = _DOMAIN_STYLES.get(profile) or _DOMAIN_STYLES["default"]

    # Personas
    personas_obj = d.get("personas") or {}
    if isinstance(personas_obj, dict):
        ppairs = list(personas_obj.items())
    elif isinstance(personas_obj, list):
        ppairs = []
        for p in personas_obj:
            if isinstance(p, dict) and "id" in p:
                ppairs.append((p["id"], p))
            else:
                ppairs.append((str(p), {}))
    else:
        ppairs = []

    screens = d.get("screens", []) or []
    entities = _entities_lookup(d)

    # Persona-Optionen für Dropdown
    persona_options = "\n      ".join(
        f'<option value="{html.escape(pn)}">{html.escape(pn)}</option>'
        for pn, _ in ppairs
    )

    # App-Name aus Repo (heuristisch, mit Wappen-Icon je Domain)
    app_name_map = {
        "meiki-hub": "MEiKI · LRA-Plattform",
        "ausschreibungs-hub": "Bieterpilot",
        "writing-hub": "Writing-Hub",
        "risk-hub": "Risk-Hub",
        "ttz-hub": "TTZ-Hub",
        "sqf-hub": "SQF-Hub",
        "pg-hub": "PG-Hub",
    }
    app_name = app_name_map.get(repo, repo.replace("-hub", " · Hub").title())
    app_icon = "🏛" if profile in ("public-admin", "lra-pilot") else ("🏗" if "ausschreibungs" in repo else "📋")

    # Tab-Buttons + Sidebar-Buttons + Screen-Sections
    # User-Feedback 2026-05-25: bei >5 Screens horizontales Scrollen unschön → Sidebar
    SIDEBAR_THRESHOLD = 6
    use_sidebar = len([s for s in screens if isinstance(s, dict)]) >= SIDEBAR_THRESHOLD
    body_class = "has-sidebar" if use_sidebar else "has-tabs"

    tab_buttons = []
    sidebar_groups: dict[str, list[str]] = {}    # halbschicht -> [button_html]
    sidebar_ungrouped: list[str] = []
    screen_sections = []
    for s in screens:
        if not isinstance(s, dict):
            continue
        sid = s.get("id", "?")
        stitle = s.get("title", "")
        sper = s.get("persona") or s.get("personas") or []
        if isinstance(sper, str):
            sper = [sper]
        konsumiert = s.get("konsumiert_entities") or []
        if isinstance(konsumiert, str):
            konsumiert = [konsumiert]
        lokal = s.get("lokale_entities") or []
        if isinstance(lokal, str):
            lokal = [lokal]
        fokus = s.get("fokus") or []

        # Tab + Sidebar
        per_data = ",".join(html.escape(p) for p in sper)
        tab_buttons.append(
            f'<button data-screen="{html.escape(sid)}" data-personas="{per_data}">'
            f'{html.escape(str(stitle) or sid)}</button>'
        )
        # Sidebar-Button (gruppiert nach halbschicht falls vorhanden)
        halbschicht = s.get("halbschicht") or ""
        sidebar_btn = (
            f'<button data-screen="{html.escape(sid)}" data-personas="{per_data}">'
            f'{html.escape(str(stitle) or sid)}'
            f'<small>{html.escape(", ".join(sper[:2]))}</small>'
            f'</button>'
        )
        if halbschicht:
            sidebar_groups.setdefault(halbschicht, []).append(sidebar_btn)
        else:
            sidebar_ungrouped.append(sidebar_btn)

        # Persona-Anzeige in App-Bar (erste Persona)
        primary_persona = sper[0] if sper else "—"

        # Per-Chips für Toolbar
        per_chips = "".join(f'<span class="persona-chip">{html.escape(p)}</span>' for p in sper)

        # Self-Service-Detection: bei Bürger-Halbschicht zeigt der Screen die
        # Sicht *eines* eingeloggten Bürgers — alle Zeilen derselben Person.
        # Verwaltungs-Halbschicht hingegen rotiert (Sachbearbeiter sieht mehrere
        # Bürger). viewer_idx=0 → erster Bürger im Pool (Sabine Müller).
        is_self_service = str(halbschicht).lower() == "buerger"
        viewer_idx = 0 if is_self_service else None
        n_rows_for_screen = 3 if is_self_service else 4

        # Entity-Panels sammeln (für Sub-Tabs oder Single-Render)
        all_ent_names = list(konsumiert) + list(lokal)
        entity_panels = []  # Liste von (ename, has_table, panel_html)
        for ename in all_ent_names[:6]:
            ent_def = entities.get(ename)
            if ent_def is not None:
                ent_desc_html = ""
                if isinstance(ent_def, dict) and ent_def.get("description"):
                    ent_desc_html = f'<p style="color:#6b7280;font-size:12px;margin:0 0 8px;">{html.escape(str(ent_def["description"])[:120])}</p>'
                table_html = _synth_entity_table(ename, ent_def, n_rows=n_rows_for_screen,
                                                 screen_id=sid, known_kds=known_kds,
                                                 known_kd_repos=known_kd_repos,
                                                 viewer_idx=viewer_idx)
                entity_panels.append((ename, True, ent_desc_html + table_html))
            else:
                stub_html = (
                    f'<p style="color:#6b7280;font-size:13px;">Konsumiert von externem Klickdummy '
                    f'<code>(siehe consumes_from-Block)</code>. Beispiel-Daten via integriertem Cross-KD-Render.</p>'
                )
                entity_panels.append((ename, False, stub_html))

        # Sub-Tabs (Punkt 3) — bei ≥2 Entities, sonst Single-Panel
        content_blocks = []
        if len(entity_panels) >= 2:
            sub_tab_html = '<div class="sub-tabs">'
            sub_panels_html = ''
            for i, (ename, _has, panel) in enumerate(entity_panels):
                active = ' active' if i == 0 else ''
                sub_tab_html += f'<button class="sub-tab{active}" data-sub="{html.escape(sid)}-{i}">📊 {html.escape(ename)}</button>'
                sub_panels_html += f'<div class="sub-panel{active}" id="sub-{html.escape(sid)}-{i}">{panel}</div>'
            sub_tab_html += '</div>'
            content_blocks.append(sub_tab_html + sub_panels_html)
        elif len(entity_panels) == 1:
            ename, _has, panel = entity_panels[0]
            content_blocks.append(
                f'<div class="card"><h3>📊 {html.escape(ename)}</h3>{panel}</div>'
            )
        # ohne Entity-Tabellen: Hinweis
        if not entity_panels:
            content_blocks.append(
                '<p style="color:#6b7280;font-size:13px;text-align:center;padding:40px;">Keine Daten-Entities für diesen Screen deklariert.</p>'
            )

        # Workflow-Buttons aus next_screens (Screen-zu-Screen-Navigation)
        next_screens = s.get("next_screens") or []
        if isinstance(next_screens, str):
            next_screens = [next_screens]
        # Map next-screen-id → next-screen-title für Button-Label
        screen_titles = {(s2.get("id") if isinstance(s2, dict) else None): (s2.get("title") if isinstance(s2, dict) else "")
                         for s2 in screens}
        workflow_buttons = []
        for nsid in next_screens[:3]:
            ntitle = screen_titles.get(nsid) or nsid
            workflow_buttons.append(
                f'<button onclick="showScreen(\'{html.escape(nsid)}\')" title="Weiter zu {html.escape(ntitle)}">'
                f'→ {html.escape(ntitle)[:30]}</button>'
            )
        if workflow_buttons:
            action_buttons = "".join(workflow_buttons) + '<button class="secondary">Speichern</button><button class="secondary">Abbrechen</button>'
        else:
            action_buttons = '<button>Speichern</button><button class="secondary">Abbrechen</button><button class="secondary">Zurück</button>'
        # Cross-KD-Links als Buttons in Actionbar
        screen_ckl = s.get("cross_klickdummy_link") if isinstance(s.get("cross_klickdummy_link"), (list, dict)) else None
        cross_links_html = []
        if screen_ckl:
            ckl_list = screen_ckl if isinstance(screen_ckl, list) else [screen_ckl]
            for entry in ckl_list:
                if isinstance(entry, dict) and entry.get("target"):
                    target = entry["target"]
                    cross_links_html.append(
                        f'<a href="#" title="Cross-KD-Link">→ {html.escape(target)}</a>'
                    )
                elif isinstance(entry, dict) and entry.get("routes"):
                    for r2 in entry["routes"]:
                        if isinstance(r2, dict):
                            cross_links_html.append(
                                f'<a href="#" title="Routing-Link">→ {html.escape(r2.get("target", "?"))}</a>'
                            )
        cross_html = ""
        if cross_links_html:
            cross_html = f'<div class="cross-links" style="margin-left:auto;">{"".join(cross_links_html)}</div>'

        # ----- ℹ Info-Modal: SPEC-Sicht (Build/Workshop) ---------------------
        fokus_modal_html = ""
        if isinstance(fokus, list) and fokus:
            fokus_items = "".join(f"<li>{html.escape(str(f))}</li>" for f in fokus)
            fokus_modal_html = f'<h4>🎯 Funktionen / Verhalten</h4><ul>{fokus_items}</ul>'
        per_list = "".join(f"<li><code>{html.escape(p)}</code></li>" for p in sper) or "<li>—</li>"
        personas_modal_html = f'<h4>👥 Personas dieses Screens</h4><ul>{per_list}</ul>'
        ent_modal_lines = []
        for ename in all_ent_names[:8]:
            ent_def = entities.get(ename)
            if isinstance(ent_def, dict):
                desc = ent_def.get("description", "")
                ent_modal_lines.append(f'<li><code>{html.escape(ename)}</code>{(" — " + html.escape(desc[:80])) if desc else ""}</li>')
            else:
                ent_modal_lines.append(f'<li><code>{html.escape(ename)}</code> <span style="color:#6b7280;">(cross-KD)</span></li>')
        ent_modal_html = f'<h4>📦 Entity-Schema</h4><ul>{"".join(ent_modal_lines)}</ul>' if ent_modal_lines else ""
        info_modal_inner = (
            '<p style="font-size:11px;color:#9ca3af;margin-top:0;">(Spec-Sicht · in Prod ggf. nicht sichtbar)</p>'
            + fokus_modal_html + personas_modal_html + ent_modal_html
        )

        # ----- ❓ Hilfe-Modal: fachliche End-User-Sicht ----------------------
        # Override via screen.help_text (Markdown-String) ODER screen.help_sections (Liste{title,content})
        # Default: Auto-Generierung aus Title/Personas/UCs/next_screens
        help_text = s.get("help_text")
        help_sections = s.get("help_sections")
        if help_text and isinstance(help_text, str):
            # Markdown-Simple-Render: line-by-line, ** → <b>, - → li
            help_lines = []
            in_list = False
            for line in help_text.strip().splitlines():
                ll = line.strip()
                if ll.startswith("- "):
                    if not in_list:
                        help_lines.append("<ul>")
                        in_list = True
                    help_lines.append(f"<li>{html.escape(ll[2:])}</li>")
                else:
                    if in_list:
                        help_lines.append("</ul>")
                        in_list = False
                    if not ll:
                        continue
                    if ll.startswith("**") and ll.endswith("**"):
                        help_lines.append(f"<h4>{html.escape(ll[2:-2])}</h4>")
                    else:
                        help_lines.append(f"<p>{html.escape(ll)}</p>")
            if in_list:
                help_lines.append("</ul>")
            help_modal_inner = "".join(help_lines)
        elif help_sections and isinstance(help_sections, list):
            parts = []
            for sec in help_sections:
                if isinstance(sec, dict):
                    t = sec.get("title", "")
                    c = sec.get("content", "")
                    parts.append(f"<h4>{html.escape(str(t))}</h4><p>{html.escape(str(c))}</p>")
            help_modal_inner = "".join(parts)
        else:
            # Default-Hilfetext aus den Spec-Feldern (heuristisch, fachlich getönt)
            default_what = (
                f'<h4>Was sehen Sie hier?</h4>'
                f'<p>{html.escape(str(stitle) or sid)} — dieser Bildschirm ist für '
                f'{html.escape(", ".join(sper) or "alle Nutzer")} gedacht.</p>'
            )
            default_actions = ""
            if isinstance(fokus, list) and fokus:
                actions = "".join(f"<li>{html.escape(str(f))}</li>" for f in fokus[:5])
                default_actions = f"<h4>Was können Sie tun?</h4><ul>{actions}</ul>"
            default_next = ""
            if next_screens:
                next_titles = [screen_titles.get(n, n) for n in next_screens[:3]]
                next_items = "".join(f"<li>{html.escape(str(t))}</li>" for t in next_titles)
                default_next = f"<h4>Folge-Schritte</h4><ul>{next_items}</ul>"
            # validierungsfrage (Spec-Feld): was dieser Screen beim Stakeholder prüfen soll
            default_check = ""
            vfrage = s.get("validierungsfrage")
            if vfrage and isinstance(vfrage, str):
                default_check = f'<h4>Diese Ansicht soll prüfen</h4><p>{html.escape(vfrage)}</p>'
            help_modal_inner = (
                '<p style="font-size:11px;color:#9ca3af;margin-top:0;">(Auto-Hilfetext aus Spec — bei Bedarf in <code>screen.help_text:</code> überschreiben)</p>'
                + default_what + default_actions + default_next + default_check
            )

        # ----- 📁 Akte-Modal: Klick auf Aktenzeichen/-name in einer Tabelle --
        # Spec-Override via screen.akte_next: {label, hint, klickdummy, uc, repo}
        # Default: generischer Hinweis "Spec-seitig noch nicht deklariert"
        akte_next = s.get("akte_next") if isinstance(s.get("akte_next"), dict) else None
        if akte_next:
            label = str(akte_next.get("label") or "Weiter zur Akte")
            hint = str(akte_next.get("hint") or "")
            target_kd = akte_next.get("klickdummy")
            target_repo = akte_next.get("repo") or repo
            uc = akte_next.get("uc")
            target_url = ""
            if target_kd:
                target_url = f"./{target_repo}-{target_kd}.html"
            parts = ['<h4>Wie es weiter ginge</h4>']
            if hint:
                parts.append(f'<p>{html.escape(hint)}</p>')
            if target_url:
                parts.append(
                    f'<p><a href="{html.escape(target_url)}" class="akte-next-cta">'
                    f'→ {html.escape(label)}</a></p>'
                )
            else:
                parts.append(
                    f'<p><span style="color:#9ca3af;">→ {html.escape(label)} '
                    f'<em>(noch nicht als Klickdummy verlinkt)</em></span></p>'
                )
            if uc:
                parts.append(
                    f'<p style="color:#6b7280;font-size:12px;">Use Case: '
                    f'<code>{html.escape(str(uc))}</code></p>'
                )
            akte_modal_inner = "".join(parts)
        else:
            akte_modal_inner = (
                '<h4>Wie es weiter ginge</h4>'
                '<p>Klick auf einen Akten-Eintrag würde im Echt-Betrieb '
                'das jeweilige Fachverfahren öffnen (z. B. Wohngeld, UVG, Asyl).</p>'
                '<p style="color:#9ca3af;font-size:12px;">'
                'Spec-seitig noch nicht deklariert. Tipp: <code>screen.akte_next: '
                '{ label, hint, klickdummy, uc }</code> ergänzen.'
                '</p>'
            )

        # Acceptance-Status pro Screen (KD-Level + Screen-Level mergen)
        accept_merged = merge_acceptance(d.get("acceptance"), s.get("acceptance"))
        accept_status = compute_acceptance_status(accept_merged)
        accept_chips = []
        for axis, info in accept_status.items():
            label = "PO-Sign-Off" if axis == "spec_signed" else "Workshop-Walk"
            if info["status"] == "signed":
                accept_chips.append(
                    f'<span class="ac-chip ac-signed" title="{html.escape(label)}: '
                    f'{html.escape(info["latest_by"] or "?")} · {info["latest_date"]} · '
                    f'ref={html.escape(info["latest_ref"] or "—")}">'
                    f'✓ {axis}</span>'
                )
            elif info["status"] == "stale":
                accept_chips.append(
                    f'<span class="ac-chip ac-stale" title="{html.escape(label)}: '
                    f'letzter Eintrag {info["age_days"]}d alt ({info["latest_date"]}) '
                    f'— Spec-Drift möglich, neue Abnahme empfohlen">'
                    f'⚠ {axis}</span>'
                )
            # "missing" wird nicht gerendert — kein Rauschen
        accept_html = "".join(accept_chips)

        # Komplette App-Frame
        # (Fallback vorab — kein Backslash-Escape im f-string-Ausdruck → Python <3.12-kompatibel)
        content_html = "".join(content_blocks) or '<p style="color:#6b7280;">Keine Inhalte im Spec deklariert.</p>'
        frame_html = (
            f'<div class="app-frame">'
            f'  <div class="app-bar">'
            f'    <div class="traffic"><span class="r"></span><span class="y"></span><span class="g"></span></div>'
            f'    <span class="app-icon">{app_icon}</span>'
            f'    <span class="app-name">{html.escape(app_name)}</span>'
            f'    <button class="info-btn" onclick="openInfoModal(\'{html.escape(sid)}\')" title="Spec-Sicht: Funktionen / Personas / Entity-Schema (Build-/Workshop-Info)">ℹ Info</button>'
            f'    <button class="help-btn" onclick="openHelpModal(\'{html.escape(sid)}\')" title="Fachliche Hilfe für diesen Screen (End-User-Sicht)">❓ Hilfe</button>'
            f'    <span class="app-user">👤 {html.escape(primary_persona)}</span>'
            f'  </div>'
            f'  <div class="app-toolbar">'
            f'    <span class="breadcrumb">Klickdummy · <b>{html.escape(kd_name)}</b></span>'
            f'    <h2>{html.escape(str(stitle) or sid)}</h2>'
            f'    <span class="sid">{html.escape(sid)}</span>'
            f'    {per_chips}'
            f'  </div>'
            f'  <div class="app-content">{content_html}</div>'
            f'  <div class="app-actionbar">'
            f'    <div class="actions">{action_buttons}</div>'
            f'    {cross_html}'
            f'  </div>'
            f'  <div class="app-statusbar">'
            f'    <span>👤 <code>{html.escape(primary_persona)}</code> · class <code>{html.escape(klass)}</code> · role <code>{html.escape(role)}</code></span>'
            f'    <span>{accept_html}Sunset <code>{html.escape(sunset)}</code></span>'
            f'  </div>'
            f'</div>'
            # Zwei versteckte Modal-Inhalte pro Screen — ℹ Info (Spec) + ❓ Hilfe (End-User)
            f'<div class="screen-info" hidden id="info-{html.escape(sid)}">'
            f'<div class="info-title">ℹ Spec-Info · {html.escape(str(stitle) or sid)} <code style="font-size:11px;font-weight:normal;color:#6b7280;">({html.escape(sid)})</code></div>'
            f'<div class="info-content">{info_modal_inner}</div>'
            f'</div>'
            f'<div class="screen-help" hidden id="help-{html.escape(sid)}">'
            f'<div class="info-title">❓ Hilfe · {html.escape(str(stitle) or sid)}</div>'
            f'<div class="info-content">{help_modal_inner}</div>'
            f'</div>'
            f'<div class="screen-akte" hidden id="akte-{html.escape(sid)}">'
            f'<div class="info-content">{akte_modal_inner}</div>'
            f'</div>'
        )

        # Spec-Layer (X-Ray): kompakter, spec-abgeleiteter Trace-Strip pro Screen
        trace_html = build_trace_strip(s, klass, role, accept_status)

        screen_sections.append(
            f'<section class="screen" id="screen-{html.escape(sid)}" data-personas="{per_data}">'
            f'{frame_html}{trace_html}</section>'
        )

    # Spec-Pfad
    spec_rel = ""
    try:
        spec_rel = str(record["path"].relative_to(REPOS_ROOT))
    except (ValueError, KeyError):
        pass

    # Custom-CSS-Hook (Punkt 1 aus User-Feedback): app_skin.custom_css aus Spec ODER
    # aus FV-Inventur (replaces_system_ref → fv.custom_css), zusätzliches Stylesheet.
    # Initial-Skin wird als INITIAL_SKIN-JS-Variable für Style-Switcher bereitgestellt;
    # Switcher lädt das CSS dynamisch (link[data-skin=1]), Spec-link nur als Marker-Hinweis.
    custom_css_link = ""
    initial_skin = "__greenfield"
    app_skin = d.get("app_skin") or {}
    if isinstance(app_skin, dict):
        css_path = app_skin.get("custom_css")
        if css_path:
            # Relativ zum Repo → URL über repo-Pfad
            css_full = (repo_dir / css_path).resolve() if not str(css_path).startswith("/") else Path(str(css_path))
            css_url = url_for_path(css_full) if css_full.is_file() else None
            if css_url:
                # In Skin-Library suchen (zentraler Pfad bevorzugt für Cross-Render-Konsistenz)
                lib_url = None
                fname = Path(css_path).name
                for lib_value, _ in skin_library():
                    if lib_value.endswith("/" + fname):
                        lib_url = lib_value
                        break
                # Initial-Skin = zentraler Pfad falls in Library, sonst spec-pfad
                initial_skin = lib_url or css_url
                custom_css_link = f"<!-- Skin via Switcher (initial: {html.escape(initial_skin)}) -->"
            else:
                custom_css_link = f"<!-- custom_css '{html.escape(str(css_path))}' nicht erreichbar — ignoriert -->"

    skin_switcher = build_skin_switcher_html(initial_skin)

    # Sidebar-Content aggregieren (gruppiert nach halbschicht; ungrouped als "Alle")
    halbschicht_labels = {
        "buerger": "👤 Bürger-Halbschicht",
        "verwaltung": "🏛 Verwaltungs-Halbschicht",
        "bieter_intern": "🏗 Baubüro intern",
        "bieter": "🏗 Bieter",
        "auftraggeber": "🤝 Auftraggeber",
        "extern": "🌐 Externe",
    }
    sidebar_blocks = []
    for hs in sorted(sidebar_groups.keys()):
        label = halbschicht_labels.get(hs, hs.replace("_", " ").title())
        sidebar_blocks.append(f"<h3>{html.escape(label)}</h3>")
        sidebar_blocks.extend(sidebar_groups[hs])
    if sidebar_ungrouped:
        if sidebar_blocks:
            sidebar_blocks.append("<h3>weitere</h3>")
        sidebar_blocks.extend(sidebar_ungrouped)
    sidebar_content = "\n    ".join(sidebar_blocks) or '<p style="color:#9ca3af;padding:16px;font-size:12px;">(keine Screens)</p>'

    html_out = RENDER_FALLBACK_TEMPLATE.format(
        kd_name=html.escape(kd_name),
        title=html.escape(title),
        repo=html.escape(repo),
        klass=html.escape(klass),
        role=html.escape(role),
        sunset=html.escape(sunset),
        persona_options=persona_options or '<option disabled>(keine Personas)</option>',
        tab_buttons="\n  ".join(tab_buttons) or '<button class="active">(kein Screen)</button>',
        sidebar_content=sidebar_content,
        body_class=body_class,
        screen_sections="\n  ".join(screen_sections) or '<section class="screen active"><div class="empty-state"><p>Keine Screens in der Spec.</p></div></section>',
        spec_rel=html.escape(spec_rel),
        style_accent=style["accent"],
        style_accent_bg=style["accent_bg"],
        style_font_h=style["font_h"],
        custom_css_link=custom_css_link,
        skin_switcher_html=skin_switcher,
        initial_skin=html.escape(initial_skin),
    )
    # JS-Inject (nach .format(), damit JS-{}-Klammern nicht als Format-Placeholder interpretiert werden)
    html_out = html_out.replace("__SKIN_SWITCHER_JS_PLACEHOLDER__", SKIN_SWITCHER_JS)
    render_dir = out_dir / "render"
    render_dir.mkdir(parents=True, exist_ok=True)
    out_path = render_dir / f"{repo}-{kd_name}.html"
    out_path.write_text(html_out, encoding="utf-8")
    return out_path


# ---- Org-Detection (Heuristik; später aus platform/registry) --------------

def detect_org(repo_name: str) -> str:
    """Erste Heuristik bis platform/registry/orgs.yaml existiert."""
    if repo_name.startswith("meiki-"):
        return "meiki-lra"
    if repo_name.startswith("ttz-"):
        return "ttz-lif"
    if repo_name.startswith(("sqf-", "pg-", "bahn-")):
        return "bahn-sqf"
    if repo_name in {"iil-klickdummy", "iil-relaunch", "iil-testkit"}:
        return "iilgmbh"
    return "achimdehnert"


def kunde_from(data: dict, fallback_org: str) -> str:
    """Kunden-Hint aus grounding.pilot_stakeholder / .pilot_lra / org-Fallback."""
    g = data.get("grounding", {}) or {}
    if "pilot_lra" in g:
        return ", ".join(g["pilot_lra"]) if isinstance(g["pilot_lra"], list) else str(g["pilot_lra"])
    if "pilot_stakeholder" in g:
        return str(g["pilot_stakeholder"])[:50]
    return fallback_org


# ---- Spec-Discovery + Parsing ----------------------------------------------

def find_specs() -> list[tuple[str, Path, dict]]:
    """Findet alle screens-spec.yaml unter mockups/*-klickdummy/."""
    out: list[tuple[str, Path, dict]] = []
    if not MOCKUPS_DIR.is_dir():
        return out
    for spec_path in sorted(MOCKUPS_DIR.glob("*-klickdummy/screens-spec.yaml")):
        kd_name = spec_path.parent.name.removesuffix("-klickdummy")
        try:
            data = yaml.safe_load(spec_path.read_text(encoding="utf-8")) or {}
        except yaml.YAMLError as exc:
            print(f"WARN: {spec_path}: YAML-Parse-Fehler: {exc}", file=sys.stderr)
            continue
        out.append((kd_name, spec_path, data))
    return out


def find_contracts() -> dict[str, Path]:
    """Findet zentrale Contracts. Returnt {contract_id: Path}."""
    out: dict[str, Path] = {}
    if not CONTRACTS_DIR.is_dir():
        return out
    for contract_path in sorted(CONTRACTS_DIR.glob("*.yaml")):
        try:
            data = yaml.safe_load(contract_path.read_text(encoding="utf-8")) or {}
        except yaml.YAMLError:
            continue
        cid = data.get("contract_id") or f"meiki:contracts/{contract_path.stem}"
        out[cid] = contract_path
    return out


# ---- Mermaid-Generierung ----------------------------------------------------

def node_id(name: str) -> str:
    """Mermaid-sicherer Node-Identifier (alphanumeric + underscore)."""
    out = []
    for ch in name:
        out.append(ch if ch.isalnum() else "_")
    return "".join(out)


def node_label(kd_name: str, data: dict) -> str:
    """Mehrzeiliges Label: Name + spec_role + class."""
    role = data.get("spec_role") or "default"
    klass = data.get("class") or "?"
    title = data.get("title") or kd_name
    short_title = title.split("—")[0].strip() if "—" in title else title
    return f"<b>{html.escape(kd_name)}</b><br/>role: {role}<br/>class: {klass}<br/><i>{html.escape(short_title[:40])}</i>"


def adr_local(data: dict) -> str | None:
    """Holt meiki:ADR-NNN aus adr.local."""
    adr = data.get("adr") or {}
    return adr.get("local")


def group_providers_by_contract(specs: list[tuple[str, Path, dict]]) -> dict[str, list[str]]:
    """Gruppiert KDs, die denselben Contract erfüllen — für Subgraph-Layout (FV-Familien sichtbar machen)."""
    from collections import defaultdict
    out: dict[str, list[str]] = defaultdict(list)
    for kd_name, _path, data in specs:
        for pc in data.get("provides_contracts", []) or []:
            cid = pc.get("schema_ref") or pc.get("id", "")
            if cid:
                out[cid].append(kd_name)
                break  # ein KD geht nur in die erste Provider-Gruppe (Heuristik für Layout, kein Vertrag)
    return dict(out)


def emit_mermaid(specs: list[tuple[str, Path, dict]], contracts: dict[str, Path]) -> str:
    """Baut Mermaid-Graph-Definition (flowchart LR) mit Provider-Subgraphen."""
    lines: list[str] = [
        "%% Auto-generated by scripts/klickdummy_lineage.py — DO NOT EDIT MANUALLY",
        "%% Quelle: docs/01-architektur/mockups/*/screens-spec.yaml",
        '%%{init: {"flowchart": {"defaultRenderer": "elk"}} }%%',
        "flowchart LR",
        "",
    ]

    # KDs in Provider-Gruppen aufteilen (nach contract_id);
    # ungruppe KDs werden separat oben emittiert.
    provider_groups = group_providers_by_contract(specs)
    grouped_kd_set = {kd for kds in provider_groups.values() for kd in kds}

    role_class = {"root": "rootNode", "hybrid": "hybridNode"}

    def emit_kd_node(kd_name: str, data: dict) -> None:
        nid = node_id(kd_name)
        lbl = node_label(kd_name, data)
        lines.append(f'    {nid}["{lbl}"]')
        role = data.get("spec_role")
        if role in role_class:
            lines.append(f"    class {nid} {role_class[role]}")

    # Ungroupte Knoten zuerst (Root, Hub-Konsumenten, Hybrid-Provider ohne Geschwister)
    lines.append("%% --- Ungroupte Klickdummy-Knoten ---")
    for kd_name, _path, data in specs:
        if kd_name not in grouped_kd_set:
            emit_kd_node(kd_name, data)

    # Subgraph je Contract-Provider-Familie (Wohngeld/UVG/Asyl als "Fachverfahren" sichtbar gruppiert)
    spec_by_name = {kd_name: data for kd_name, _p, data in specs}
    for cid, members in provider_groups.items():
        if len(members) < 2:
            # Single-Member-Gruppe: kein Subgraph nötig, normaler Knoten
            for kd_name in members:
                emit_kd_node(kd_name, spec_by_name[kd_name])
            continue
        sg_id = "fam_" + node_id(cid)
        short = cid.split("/")[-1]
        lines.append("")
        lines.append(f'    subgraph {sg_id} ["📋 Provider-Familie · {html.escape(short)}"]')
        lines.append("    direction TB")
        for kd_name in members:
            emit_kd_node(kd_name, spec_by_name[kd_name])
        lines.append("    end")
        lines.append(f"    class {sg_id} familyGroup")

    # Contract-Knoten (visuell separat)
    if contracts:
        lines.append("")
        lines.append("%% --- Contracts ---")
        for cid in contracts:
            nid = node_id(cid)
            short = cid.split("/")[-1]
            lines.append(f'    {nid}(("📜 {html.escape(short)}<br/>contract"))')
            lines.append(f"    class {nid} contractNode")

    # Kanten — consumes_from (solid)
    lines.append("")
    lines.append("%% --- consumes_from (Schema-Import, kontinuierlich) ---")
    spec_by_adr: dict[str, str] = {}
    for kd_name, _path, data in specs:
        adr = adr_local(data) or ""
        if adr:
            spec_by_adr[adr] = kd_name

    # Resolve-Helper: ``ref: <prefix>:ADR-NNN`` ODER ``kd: <name>`` (Alias)
    spec_by_kdname = {kd_name: kd_name for kd_name, _, _ in specs}
    for kd_name, _path, data in specs:
        for cf in data.get("consumes_from", []) or []:
            entities = cf.get("entities", []) or []
            target_kd = None
            ref = cf.get("ref", "")
            if ref:
                target_kd = spec_by_adr.get(ref)
            if not target_kd:
                # Alias-Format: kd: <name> (+ optional repo)
                kd_alias = cf.get("kd")
                if kd_alias:
                    target_kd = spec_by_kdname.get(kd_alias)
            if not target_kd:
                continue
            src = node_id(target_kd)
            dst = node_id(kd_name)
            label = f"{len(entities)} entities" if entities else "consumes"
            lines.append(f'    {src} -->|"{label}"| {dst}')

    # Kanten — provides_contracts (gestrichelt)
    lines.append("")
    lines.append("%% --- provides_contracts (Vertrags-Erfüllung) ---")
    for kd_name, _path, data in specs:
        for pc in data.get("provides_contracts", []) or []:
            cid = pc.get("schema_ref") or pc.get("id", "")
            if not cid:
                continue
            src = node_id(kd_name)
            dst = node_id(cid)
            lines.append(f"    {src} -.->|provides| {dst}")

    # Kanten — accepts_contracts (gestrichelt, zurück)
    lines.append("")
    lines.append("%% --- accepts_contracts (Vertrags-Konsum) ---")
    for kd_name, _path, data in specs:
        for ac in data.get("accepts_contracts", []) or []:
            cid = ac.get("schema_ref") or ac.get("id", "")
            if not cid:
                continue
            src = node_id(cid)
            dst = node_id(kd_name)
            lines.append(f"    {src} -.->|accepted by| {dst}")

    # Kanten — cross_klickdummy_link (gepunktet, UX-Achse)
    lines.append("")
    lines.append("%% --- cross_klickdummy_link (UX-Navigation, orthogonal) ---")
    for kd_name, _path, data in specs:
        # Top-level route-Tabelle
        ckl = data.get("cross_klickdummy_link") or {}
        if isinstance(ckl, dict) and ckl.get("routes"):
            for route in ckl["routes"]:
                target_adr = route.get("target", "")
                target_kd = spec_by_adr.get(target_adr)
                if target_kd:
                    src = node_id(kd_name)
                    dst = node_id(target_kd)
                    label = f"UX:{route.get('fv_adapter', '?')}"
                    lines.append(f'    {src} -..->|"{label}"| {dst}')
        # Top-level Einzelliste
        elif isinstance(ckl, list):
            for entry in ckl:
                target_adr = entry.get("target", "")
                target_kd = spec_by_adr.get(target_adr)
                if target_kd:
                    src = node_id(kd_name)
                    dst = node_id(target_kd)
                    lines.append(f"    {src} -..->|UX| {dst}")
        # Screen-Level cross_klickdummy_link (Fristenmgmt-Pattern)
        for screen in data.get("screens", []) or []:
            screen_ckl = screen.get("cross_klickdummy_link") if isinstance(screen, dict) else None
            if isinstance(screen_ckl, dict) and screen_ckl.get("routes"):
                for route in screen_ckl["routes"]:
                    target_adr = route.get("target", "")
                    target_kd = spec_by_adr.get(target_adr)
                    if target_kd:
                        src = node_id(kd_name)
                        dst = node_id(target_kd)
                        label = f"UX:{route.get('fv_adapter', '?')}"
                        lines.append(f'    {src} -..->|"{label}"| {dst}')
            elif isinstance(screen_ckl, list):
                for entry in screen_ckl:
                    target_adr = entry.get("target", "")
                    target_kd = spec_by_adr.get(target_adr)
                    if target_kd:
                        src = node_id(kd_name)
                        dst = node_id(target_kd)
                        lines.append(f"    {src} -..->|UX| {dst}")

    # Styling
    lines.append("")
    lines.append("%% --- Styling ---")
    lines.append("    classDef rootNode fill:#cef,stroke:#06c,stroke-width:2px,color:#000")
    lines.append("    classDef hybridNode fill:#fec,stroke:#c80,stroke-width:2px,color:#000")
    lines.append("    classDef contractNode fill:#fde,stroke:#c0c,stroke-width:2px,color:#000")
    lines.append("    classDef familyGroup fill:#f5f5f5,stroke:#888,stroke-dasharray:4 4,color:#444")
    lines.append("    classDef default fill:#fff,stroke:#888,color:#000")

    return "\n".join(lines) + "\n"


# ---- HTML-Wrapper mit Feedback-Widget --------------------------------------

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="de">
<head>
<meta charset="utf-8">
<title>Klickdummy-Lineage — meiki-hub (auto-generated)</title>
<style>
  body {{ font-family: -apple-system, system-ui, sans-serif; margin: 0; color: #222; background: #fafafa; }}
  header {{ padding: 14px 24px; background: #fff; border-bottom: 1px solid #e0e0e0; display: flex; justify-content: space-between; align-items: center; }}
  header h1 {{ margin: 0; font-size: 18px; font-weight: 600; }}
  header .meta {{ color: #888; font-size: 13px; }}
  main {{ padding: 20px 24px; }}
  .legend {{ background: #fff; border: 1px solid #e0e0e0; border-radius: 6px; padding: 12px 16px; margin-bottom: 16px; font-size: 13px; }}
  .legend code {{ background: #f0f0f0; padding: 1px 6px; border-radius: 3px; font-size: 12px; }}
  .legend table {{ border-collapse: collapse; width: 100%; }}
  .legend td {{ padding: 3px 8px; vertical-align: top; }}
  .legend td:first-child {{ width: 130px; white-space: nowrap; }}
  .graph-wrap {{ background: #fff; border: 1px solid #e0e0e0; border-radius: 6px; padding: 16px; overflow-x: auto; }}
  .stats {{ font-size: 13px; color: #666; margin-top: 8px; }}

  /* Feedback-Widget — A-light (download submit), per platform:ADR-211 Rev 13 §Co-Creation */
  .fb {{ position: fixed; bottom: 16px; right: 16px; width: 320px; background: #fff; border: 1px solid #06c; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,.12); font-size: 13px; }}
  .fb-head {{ background: #06c; color: #fff; padding: 8px 12px; border-radius: 8px 8px 0 0; cursor: pointer; display: flex; justify-content: space-between; }}
  .fb-body {{ padding: 12px; }}
  .fb-body.hidden {{ display: none; }}
  .fb label {{ display: block; margin: 6px 0 2px; font-size: 12px; color: #555; }}
  .fb select, .fb textarea, .fb input {{ width: 100%; box-sizing: border-box; padding: 4px 6px; border: 1px solid #ccc; border-radius: 4px; font-size: 13px; font-family: inherit; }}
  .fb textarea {{ height: 60px; resize: vertical; }}
  .fb .row {{ display: flex; gap: 6px; margin-top: 8px; }}
  .fb button {{ padding: 6px 10px; border: 1px solid #06c; background: #06c; color: #fff; border-radius: 4px; cursor: pointer; font-size: 13px; }}
  .fb button.secondary {{ background: #fff; color: #06c; }}
  .fb .status {{ margin-top: 6px; font-size: 12px; color: #060; }}
</style>
<script src="https://cdn.jsdelivr.net/npm/mermaid@10.9.1/dist/mermaid.min.js"></script>
</head>
<body>

<header>
  <h1>🌐 Klickdummy-Lineage · meiki-hub</h1>
  <span class="meta">{stats_inline} · auto-generated {date}</span>
</header>

<main>

<div class="legend">
  <table>
    <tr><td><b>spec_role: root</b></td><td>blau · exponiert <code>root_entities</code>, kein <code>consumes_from</code></td></tr>
    <tr><td><b>spec_role: hybrid</b></td><td>orange · konsumiert + exponiert (siehe platform:ADR-211 Rev 14 Finding #4)</td></tr>
    <tr><td><b>📜 Contract</b></td><td>magenta · zentraler Vertrag (provides/accepts), siehe Rev 14 Finding #6</td></tr>
    <tr><td><b>─→ solid</b></td><td><code>consumes_from</code> (Schema-Import, Drift-relevant)</td></tr>
    <tr><td><b>-.→ dashed</b></td><td><code>provides_contracts</code> / <code>accepts_contracts</code></td></tr>
    <tr><td><b>-..→ dotted</b></td><td><code>cross_klickdummy_link</code> (UX-Navigation, orthogonal, Rev 14 Finding #5)</td></tr>
  </table>
</div>

<div class="graph-wrap">
<pre class="mermaid">
{mermaid}
</pre>
<div class="stats">{stats_full}</div>
</div>

</main>

<!-- Feedback-Widget · A-light (download submit) -->
<div class="fb" id="fb-widget">
  <div class="fb-head" onclick="document.getElementById('fb-body').classList.toggle('hidden')">
    <span>💬 Feedback zur Lineage-Sicht</span>
    <span>▾</span>
  </div>
  <div class="fb-body" id="fb-body">
    <label>Scope <small>(Rev-12-Pflicht 6: <code>feedback_scope</code>)</small></label>
    <select id="fb-scope">
      <option value="klickdummy-tool">Auf die Lineage-Sicht selbst (Viewer-Bug, Layout, ...)</option>
      <option value="app">Auf einen Klickdummy im Graphen (Topologie, Beziehung, Naming, ...)</option>
    </select>

    <label>Kategorie</label>
    <select id="fb-cat">
      <option value="topology-error">Topologie falsch / Beziehung fehlt</option>
      <option value="naming">Bezeichnung ungenau / Klasse falsch</option>
      <option value="missing-link">cross_klickdummy_link fehlt</option>
      <option value="contract-drift">Contract-Mapping driftet</option>
      <option value="viewer-bug">Viewer-Bug (Rendering, Layout)</option>
      <option value="idea">Idee / Vorschlag</option>
    </select>

    <label>Acceptance</label>
    <select id="fb-verdict">
      <option value="">— wählen —</option>
      <option value="accepted">✓ Accepted</option>
      <option value="needs-change">✎ Needs-Change</option>
      <option value="rejected">✗ Rejected</option>
    </select>

    <label>Betroffener KD <small>(nur bei Scope „app")</small></label>
    <select id="fb-kd">
      <option value="">— alle / kein spezifischer —</option>
      {kd_options}
    </select>

    <label>Beschreibung</label>
    <textarea id="fb-text" placeholder="Was ist Dir aufgefallen? Was sollte anders sein?"></textarea>

    <div class="row">
      <button onclick="fbDownload()">📥 Download JSON</button>
      <button class="secondary" onclick="fbClipboard()">📋 In Clipboard</button>
    </div>
    <div class="status" id="fb-status"></div>
  </div>
</div>

<script>
  // Mermaid render
  mermaid.initialize({{ startOnLoad: true, theme: 'default', flowchart: {{ curve: 'basis' }} }});

  // KD-Lookup-Tabelle für Feedback
  window.KLICKDUMMY_SPEC = {{ id: "lineage", version: "0.1", klickdummy_class: "mock" }};
  window.KLICKDUMMY_FEEDBACK_REPO = "achimdehnert/meiki-hub";

  function fbCollect() {{
    return {{
      spec_id: window.KLICKDUMMY_SPEC.id,
      spec_version: window.KLICKDUMMY_SPEC.version,
      klickdummy_class: window.KLICKDUMMY_SPEC.klickdummy_class,
      feedback_scope: document.getElementById('fb-scope').value,
      acceptance_verdict: document.getElementById('fb-verdict')?.value || null,
      kategorie: document.getElementById('fb-cat').value,
      betroffener_kd: document.getElementById('fb-kd').value || null,
      text: document.getElementById('fb-text').value,
      ts: new Date().toISOString(),
      generated_from: document.title,
      conforms_to: "platform:ADR-211 Rev 13 §Co-Creation-Loop Pfad A-light"
    }};
  }}

  function fbDownload() {{
    const payload = fbCollect();
    const blob = new Blob([JSON.stringify(payload, null, 2)], {{ type: 'application/json' }});
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `feedback-lineage-${{Date.now()}}.json`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
    document.getElementById('fb-status').textContent = "✓ JSON heruntergeladen. Manuell als Issue mit Label `klickdummy-feedback` anlegen.";
  }}

  async function fbClipboard() {{
    const payload = fbCollect();
    await navigator.clipboard.writeText(JSON.stringify(payload, null, 2));
    document.getElementById('fb-status').textContent = "✓ Im Clipboard.";
  }}
</script>

</body>
</html>
"""


def build_html(mermaid_text: str, specs: list[tuple[str, Path, dict]], contracts: dict) -> str:
    from datetime import date
    kd_options = "\n      ".join(
        f'<option value="{html.escape(kd_name)}">{html.escape(kd_name)}</option>'
        for kd_name, _p, _d in specs
    )
    n_kd = len(specs)
    n_root = sum(1 for _, _, d in specs if d.get("spec_role") == "root")
    n_hybrid = sum(1 for _, _, d in specs if d.get("spec_role") == "hybrid")
    n_default = n_kd - n_root - n_hybrid
    n_contracts = len(contracts)
    n_consumes = sum(len(d.get("consumes_from") or []) for _, _, d in specs)
    n_provides = sum(len(d.get("provides_contracts") or []) for _, _, d in specs)
    stats_inline = f"{n_kd} KDs · {n_contracts} Contracts · {n_consumes} consumes-Refs · {n_provides} provides"
    stats_full = (
        f"Statistik: {n_kd} Klickdummies "
        f"(root: {n_root}, hybrid: {n_hybrid}, default: {n_default}) · "
        f"{n_contracts} Cross-cutting Contracts · "
        f"{n_consumes} consumes_from-Einträge · "
        f"{n_provides} provides_contracts-Einträge"
    )
    return HTML_TEMPLATE.format(
        mermaid=mermaid_text,
        kd_options=kd_options,
        date=date.today().isoformat(),
        stats_inline=stats_inline,
        stats_full=stats_full,
    )


# ---- Cross-Repo-Walker (IIL-Genesor Stufe 1a + 1b) -------------------------

import re

# Per platform:ADR-213 (Cross-Repo-Ref-Format)
CROSS_REPO_REF_RE = re.compile(r"^[a-z][a-z0-9-]+:ADR-[0-9]{3}$")


_ACCEPTANCE_AXES = ("spec_signed", "ui_walked")
_ACCEPTANCE_STALE_DAYS = 60


def compute_acceptance_status(acceptance: dict | None) -> dict:
    """ADR-211 Rev 15 §Acceptance — 2 Achsen ``spec_signed`` + ``ui_walked``.

    Schema: ``{spec_signed: [{by, date, ref, scope?}], ui_walked: [{...}]}``.
    Append-only. Status pro Achse:
    - ``signed``: jüngster Eintrag ≤ 60 Tage alt
    - ``stale``:  jüngster Eintrag > 60 Tage alt (Spec-Drift-Verdacht)
    - ``missing``: keine Einträge
    Rückgabe: ``{axis: {status, latest_date, latest_by, latest_ref, age_days}}``.
    """
    from datetime import date, timedelta
    today = date.today()
    out: dict[str, dict] = {}
    accept = acceptance if isinstance(acceptance, dict) else {}
    for axis in _ACCEPTANCE_AXES:
        entries = accept.get(axis) or []
        if not isinstance(entries, list) or not entries:
            out[axis] = {"status": "missing", "latest_date": None,
                         "latest_by": None, "latest_ref": None, "age_days": None}
            continue
        # Jüngster Eintrag
        latest = None
        for e in entries:
            if not isinstance(e, dict) or not e.get("date"):
                continue
            try:
                d = date.fromisoformat(str(e["date"])[:10])
            except ValueError:
                continue
            if latest is None or d > latest["_d"]:
                latest = {**e, "_d": d}
        if latest is None:
            out[axis] = {"status": "missing", "latest_date": None,
                         "latest_by": None, "latest_ref": None, "age_days": None}
            continue
        age = (today - latest["_d"]).days
        status = "stale" if age > _ACCEPTANCE_STALE_DAYS else "signed"
        out[axis] = {
            "status": status,
            "latest_date": latest["_d"].isoformat(),
            "latest_by": str(latest.get("by") or "?"),
            "latest_ref": str(latest.get("ref") or ""),
            "age_days": age,
        }
    return out


def merge_acceptance(kd_level: dict | None, screen_level: dict | None) -> dict:
    """Screen-Acceptance erbt + extendet KD-Acceptance (append-only, beide Quellen)."""
    out: dict[str, list] = {}
    for axis in _ACCEPTANCE_AXES:
        merged = []
        for src in (kd_level or {}, screen_level or {}):
            v = src.get(axis) if isinstance(src, dict) else None
            if isinstance(v, list):
                merged.extend(v)
        if merged:
            out[axis] = merged
    return out


def _prefix_to_repo(prefix: str) -> str:
    """Maps Spec-Ref-Prefix → Repo-Name. ADR-211 Rev 15 Cross-Repo-Konvention.

    Beispiele: ``meiki`` → ``meiki-hub``, ``ausschreibungs-hub`` → unverändert,
    ``ttz`` → ``ttz-hub``. Heuristik: bereits Repo-Name akzeptieren, sonst
    ``<prefix>-hub`` testen, sonst Prefix wie eingegeben behalten.
    """
    if not prefix:
        return ""
    p = prefix.strip()
    if (REPOS_ROOT / p).is_dir():
        return p
    cand = f"{p}-hub"
    if (REPOS_ROOT / cand).is_dir():
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
    if not REPOS_ROOT.is_dir():
        return out
    for repo_dir in sorted(REPOS_ROOT.iterdir()):
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


def _normalize_spec_aliases(data: dict) -> dict:
    """Field-Aliase für Cross-Repo-Kompatibilität (additiv, backward-compatible).

    ausschreibungs-hub nutzt `cross_kd_links`; lineage liest historisch
    `cross_klickdummy_link`. Normalisiert data- + screen-level, ohne vorhandene
    kanonische Keys zu überschreiben. Reine Ergänzung — bestehende Specs unberührt.
    """
    if not isinstance(data, dict):
        return data
    if "cross_klickdummy_link" not in data and "cross_kd_links" in data:
        data["cross_klickdummy_link"] = data["cross_kd_links"]
    for screen in data.get("screens", []) or []:
        if (
            isinstance(screen, dict)
            and "cross_klickdummy_link" not in screen
            and "cross_kd_links" in screen
        ):
            screen["cross_klickdummy_link"] = screen["cross_kd_links"]
    return data


def find_all_repos_specs() -> list[dict]:
    """Walks ~/github/*/ für screens-spec.yaml UND render-only-KDs ohne Spec (F11)."""
    out: list[dict] = []
    if not REPOS_ROOT.is_dir():
        return out
    for repo_dir in sorted(REPOS_ROOT.iterdir()):
        if not repo_dir.is_dir() or repo_dir.name.startswith("."):
            continue
        repo_name = repo_dir.name
        org = detect_org(repo_name)

        # Rev-15-Vorgriff: KD-ADR-Frontmatter lesen für realizes_use_cases +
        # replaces_system_ref (B+E-Pattern)
        adr_meta = read_kd_adr_meta(repo_dir)

        # 1. Standard-Konvention: klickdummy/<name>/screens-spec.yaml
        seen_kd_dirs: set[Path] = set()
        for spec_path in repo_dir.glob("klickdummy/*/screens-spec.yaml"):
            kd_name = spec_path.parent.name
            seen_kd_dirs.add(spec_path.parent)
            try:
                data = yaml.safe_load(spec_path.read_text("utf-8")) or {}
            except yaml.YAMLError:
                continue
            data = _normalize_spec_aliases(data)
            adr_local = (data.get("adr", {}) or {}).get("local")
            extra = adr_meta.get(adr_local, {}) if adr_local else {}
            out.append({"org": org, "repo": repo_name, "kd": kd_name,
                        "path": spec_path, "data": data, "kind": "spec",
                        "adr_meta": extra})

        # 2. meiki-Konvention: docs/01-architektur/mockups/<name>-klickdummy/screens-spec.yaml
        for spec_path in repo_dir.glob("docs/01-architektur/mockups/*-klickdummy/screens-spec.yaml"):
            kd_name = spec_path.parent.name.removesuffix("-klickdummy")
            seen_kd_dirs.add(spec_path.parent)
            try:
                data = yaml.safe_load(spec_path.read_text("utf-8")) or {}
            except yaml.YAMLError:
                continue
            data = _normalize_spec_aliases(data)
            adr_local = (data.get("adr", {}) or {}).get("local")
            extra = adr_meta.get(adr_local, {}) if adr_local else {}
            out.append({"org": org, "repo": repo_name, "kd": kd_name,
                        "path": spec_path, "data": data, "kind": "spec",
                        "adr_meta": extra})

        # 3. F11: Render-only-KDs ohne Spec (I1-Verstoß-Kandidaten)
        kd_root = repo_dir / "klickdummy"
        if kd_root.is_dir():
            # 3a. Subdirs ohne screens-spec.yaml
            for sub in sorted(kd_root.iterdir()):
                if not sub.is_dir() or sub in seen_kd_dirs or sub.name.startswith(("_", ".")):
                    continue
                # Hat das Subdir eine HTML-Datei? Dann ist es ein render-only-KD.
                htmls = [h for h in sub.glob("*.html") if not h.name.startswith(("_", "README"))]
                if htmls:
                    out.append({
                        "org": org, "repo": repo_name, "kd": sub.name,
                        "path": sub / "screens-spec.yaml",   # virtuell, existiert nicht
                        "data": {"_render_only": True, "_html_files": [str(h.name) for h in htmls]},
                        "kind": "render-only-subdir",
                    })
            # 3b. HTML direkt in klickdummy/ (risk-hub-Pattern)
            for html_file in sorted(kd_root.glob("*.html")):
                if html_file.name.startswith(("_", "README")):
                    continue
                kd_name = html_file.stem
                out.append({
                    "org": org, "repo": repo_name, "kd": kd_name,
                    "path": html_file,
                    "data": {"_render_only_inline": True, "_html_file": html_file.name},
                    "kind": "render-only-inline",
                })

    return out


# ---- Drift-Validierung (F3) ------------------------------------------------

def build_kd_registry(records: list[dict]) -> set[str]:
    """{repo}:ADR-NNN für alle gefundenen KDs mit Spec — für Dangling-Ref-Check."""
    reg: set[str] = set()
    for r in records:
        if r.get("kind") != "spec":
            continue
        adr = (r["data"].get("adr", {}) or {}).get("local")
        if adr:
            reg.add(adr)
    return reg


def validate_kd(r: dict, kd_registry: set[str]) -> list[dict]:
    """Returnt Liste Warnings für einen KD: {severity, code, msg}."""
    warnings: list[dict] = []
    d = r["data"]

    # I1-Verstoß: render-only ohne Spec
    if r.get("kind", "spec") != "spec":
        warnings.append({
            "severity": "error", "code": "I1-NO-SPEC",
            "msg": "I1-Verstoß: klickbares HTML vorhanden, aber keine screens-spec.yaml — keine maschinenlesbare Spec, kein Vertrag.",
        })
        return warnings  # alle weiteren Checks brauchen Spec-Daten

    # I4-Format-Check für consumes_from-Refs
    for cf in d.get("consumes_from", []) or []:
        ref = (cf.get("ref") or "").strip() if isinstance(cf, dict) else ""
        if ref and not CROSS_REPO_REF_RE.match(ref):
            warnings.append({"severity": "error", "code": "I4-MALFORMED-REF",
                             "msg": f"Cross-Repo-Ref '{ref}' verletzt platform:ADR-213-Regex (^[a-z][a-z0-9-]+:ADR-[0-9]{{3}}$)."})
        elif ref and ref not in kd_registry:
            warnings.append({"severity": "warning", "code": "DANGLING-REF",
                             "msg": f"Cross-Repo-Ref '{ref}' zeigt auf keinen bekannten KD (Drift-Klasse klickdummy-adr180-collision)."})

    # I3-Sunset (F4)
    sunset_str = (d.get("off_ramp", {}) or {}).get("sunset_after")
    if sunset_str:
        try:
            from datetime import date
            yyyy_mm_dd = str(sunset_str)[:10]
            sunset = date.fromisoformat(yyyy_mm_dd)
            days_left = (sunset - date.today()).days
            if days_left < 0:
                warnings.append({"severity": "error", "code": "SUNSET-OVERDUE",
                                 "msg": f"Sunset {sunset_str} ist um {-days_left} Tage überfällig — platform:ADR-211 Rev 11 verlangt auto-deprecated."})
            elif days_left < 90:
                warnings.append({"severity": "warning", "code": "SUNSET-NEAR",
                                 "msg": f"Sunset in {days_left} Tagen — Extension via PR prüfen."})
        except ValueError:
            warnings.append({"severity": "warning", "code": "SUNSET-MALFORMED",
                             "msg": f"sunset_after '{sunset_str}' ist kein ISO-Datum."})
    elif d.get("class") in {"mock", "stub-demo", "story", "spec-demo"}:
        warnings.append({"severity": "warning", "code": "SUNSET-MISSING",
                         "msg": "class deklariert, aber kein sunset_after — Rev-11-Pflicht-Frontmatter fehlt."})

    return warnings


def compute_sunset_badge(d: dict) -> tuple[str, str]:
    """Returnt (css-class, text) für die Sunset-Spalte."""
    sunset_str = (d.get("off_ramp", {}) or {}).get("sunset_after") if isinstance(d, dict) else None
    if not sunset_str:
        return ("sunset-na", "—")
    try:
        from datetime import date
        yyyy_mm_dd = str(sunset_str)[:10]
        sunset = date.fromisoformat(yyyy_mm_dd)
        days_left = (sunset - date.today()).days
        if days_left < 0:
            return ("sunset-overdue", f"❌ {sunset_str} ({-days_left}d überfällig)")
        if days_left < 90:
            return ("sunset-near", f"⚠ {sunset_str} ({days_left}d)")
        return ("sunset-ok", sunset_str)
    except ValueError:
        return ("sunset-na", f"? {sunset_str}")


def _extract_screen_routes(record: dict) -> list[dict]:
    """Pilot-Memo §Surface-Modal: liefert pro Screen die Endpoint-Mapping-Info.

    Sucht in dieser Reihenfolge nach Routen:
      1. screens[].route (explizit)
      2. screens[].route_example (Beispiel-URL mit konkreter ID)
      3. screens[].implementation_brief.api.endpoints[].path (Fallback, primär API)

    Liefert: Liste von {screen_id, title, route, route_example, has_brief}.
    Wenn ``route`` fehlt → leere Route, Pills für Dev/Stg/Prod sind dann disabled.
    """
    d = record.get("data") or {}
    screens = d.get("screens") or []
    if not isinstance(screens, list):
        return []
    out: list[dict] = []
    for s in screens:
        if not isinstance(s, dict):
            continue
        sid = s.get("id") or ""
        if not sid:
            continue
        title = s.get("title", sid)
        route = s.get("route") or ""
        route_example = s.get("route_example") or route  # fallback
        # API-Fallback aus Brief
        brief = s.get("implementation_brief") or {}
        api_paths = []
        api_block = brief.get("api") or {}
        if isinstance(api_block, dict):
            for endpoint in (api_block.get("endpoints") or []):
                if isinstance(endpoint, dict) and endpoint.get("path"):
                    api_paths.append(endpoint["path"])
        out.append({
            "screen_id": sid,
            "title": title,
            "route": route,
            "route_example": route_example,
            "api_paths": api_paths[:3],
            "has_brief": bool(brief),
        })
    return out


def _load_iil_apps_index() -> dict[str, dict]:
    """Pilot-Memo §0: lädt iil-relaunch/apps.json und indiziert by repo-Name.

    Liefert pro repo einen dict mit ``urls.{prod,staging,dev}`` + ``name``.
    Fallback bei fehlender Datei: leeres dict (kein Crash).
    """
    import json
    candidates = [
        REPOS_ROOT / "iil-relaunch" / "apps.json",
        REPOS_ROOT / "platform" / "static-sites" / "iil.pet" / "apps.json",
    ]
    for p in candidates:
        if not p.is_file():
            continue
        try:
            data = json.loads(p.read_text("utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(data, list):
            continue
        idx: dict[str, dict] = {}
        for entry in data:
            if not isinstance(entry, dict):
                continue
            repo = entry.get("repo")
            urls = entry.get("urls") or {}
            if repo and isinstance(urls, dict):
                idx[repo] = {
                    "name": entry.get("name", repo),
                    "urls": {k: v for k, v in urls.items() if v},
                    "status": entry.get("status", ""),
                    "source": str(p),
                }
        return idx
    return {}


def _compute_drift_status(record: dict) -> dict:
    """Pilot-Memo 2026-05-26 §0: Drift-Status pro KD.

    Berechnet:
      - brief_url + brief_age_days (falls .md/.html im genesor/impl-brief/ liegt)
      - n_screens_with_brief: wie viele Screens haben implementation_brief im Spec
      - coverage_pct: briefs_im_genesor / screens_with_brief_spec
      - drift_status:
          🟢 "in-sync"       — alle erwarteten Briefs da, brief_age <14d
          🟡 "stale"         — Briefs da aber älter als 14d
          🟠 "partial"       — nicht alle erwarteten Briefs generiert
          ⚪ "no-brief"      — Spec hat implementation_brief, aber noch keine Briefs im Genesor
          ⚫ "no-spec-brief" — Spec selbst hat keine implementation_brief-Blöcke (kein Pilot)
      - compare_url: Deep-Link zu Brief §10 (Drift-Sektion)
    """
    from datetime import datetime
    repo = record["repo"]
    kd_name = record["kd"]
    d = record.get("data") or {}
    screens = d.get("screens") or []
    if not isinstance(screens, list):
        screens = []

    # Erwartung: pro Screen mit implementation_brief-Block ein .md im genesor
    expected_briefs: list[str] = []
    for s in screens:
        if isinstance(s, dict) and s.get("implementation_brief"):
            sid = s.get("id")
            if sid:
                expected_briefs.append(sid)

    # Tatsächlich vorhandene Briefs prüfen
    actual_briefs: list[tuple[str, str, int]] = []  # (screen_id, brief_md_path, age_days)
    brief_dir = GENESOR_OUT / "impl-brief"
    today = datetime.now()
    for sid in expected_briefs:
        # Konvention: impl-brief/<repo>-<kd>-<screen>.md
        path = brief_dir / f"{repo}-{kd_name}-{sid}.md"
        if path.is_file():
            mtime = datetime.fromtimestamp(path.stat().st_mtime)
            age = (today - mtime).days
            actual_briefs.append((sid, str(path), age))

    n_expected = len(expected_briefs)
    n_actual = len(actual_briefs)
    coverage_pct = (n_actual / n_expected * 100) if n_expected else 0
    oldest_age = max((a for _, _, a in actual_briefs), default=0)

    # Status-Heuristik
    if n_expected == 0:
        status = "no-spec-brief"
        status_label = "kein Pilot"
        status_color = "#999"
    elif n_actual == 0:
        status = "no-brief"
        status_label = "kein Brief generiert"
        status_color = "#bbb"
    elif n_actual < n_expected:
        status = "partial"
        status_label = f"{n_actual}/{n_expected} Briefs"
        status_color = "#f59e0b"
    elif oldest_age > 14:
        status = "stale"
        status_label = f"Brief {oldest_age} d alt"
        status_color = "#eab308"
    else:
        status = "in-sync"
        status_label = "in-sync"
        status_color = "#22c55e"

    # Compare-Link: zum jüngsten Brief, anker §10 (Drift-Sektion)
    compare_url = None
    if actual_briefs:
        # nimm jüngsten (kleinstes Alter)
        sid, _path, _age = min(actual_briefs, key=lambda x: x[2])
        compare_url = f"/genesor/impl-brief-{repo}-{kd_name}-{sid}.html#§10-genesor-vs-realität-drift-spec--echtes-model"

    return {
        "n_expected_briefs": n_expected,
        "n_actual_briefs": n_actual,
        "coverage_pct": round(coverage_pct, 0),
        "oldest_brief_age_days": oldest_age,
        "status": status,
        "status_label": status_label,
        "status_color": status_color,
        "compare_url": compare_url,
    }


def build_genesor_html(records: list[dict],
                      uc_coverage: dict | None = None,
                      n_ucs: int = 0) -> str:
    """Cross-Repo Übersichts-HTML — klickbare Tabelle mit Detail-Panel pro KD.

    Optional: UC-Coverage-Summary in der Topbar + Link zu coverage.html
    (ADR-211 Rev 15 §UC-Coverage).
    """
    from datetime import date
    from collections import defaultdict

    # KD-ADR-Registry für Dangling-Ref-Check (F3)
    kd_registry = build_kd_registry(records)

    # Pro KD Warnings berechnen + Total-Counts
    all_warnings: dict[int, list[dict]] = {}
    n_errors = 0
    n_warns = 0
    for idx, r in enumerate(records):
        warns = validate_kd(r, kd_registry)
        all_warnings[idx] = warns
        n_errors += sum(1 for w in warns if w["severity"] == "error")
        n_warns += sum(1 for w in warns if w["severity"] == "warning")

    # Statistik
    n_kds = len(records)
    n_orgs = len({r["org"] for r in records})
    n_repos = len({(r["org"], r["repo"]) for r in records})
    classes = defaultdict(int)
    for r in records:
        classes[(r["data"].get("class") or "?")] += 1
    n_root = sum(1 for r in records if r["data"].get("spec_role") == "root")
    n_hybrid = sum(1 for r in records if r["data"].get("spec_role") == "hybrid")
    n_render_only = sum(1 for r in records if r.get("kind", "spec") != "spec")

    # Drift-Daten pro KD (Pilot-Memo 2026-05-26 — stabile Basis gegen Drift)
    drift_by_idx: dict[int, dict] = {}
    drift_counter = defaultdict(int)
    for idx, r in enumerate(records):
        drift_by_idx[idx] = _compute_drift_status(r)
        drift_counter[drift_by_idx[idx]["status"]] += 1
    n_pilot_kds = sum(1 for d in drift_by_idx.values() if d["n_expected_briefs"] > 0)
    n_briefs_total = sum(d["n_actual_briefs"] for d in drift_by_idx.values())
    n_briefs_expected = sum(d["n_expected_briefs"] for d in drift_by_idx.values())

    # Surface-Index aus iil-relaunch/apps.json (Pilot-Memo §Surface-Switcher)
    apps_index = _load_iil_apps_index()
    n_apps_indexed = len(apps_index)
    # Rev-15-Stats: UCs + Ablösungen
    n_ucs_total = sum(
        len(r.get("adr_meta", {}).get("realizes_use_cases") or [])
        for r in records
    )
    n_replaces = sum(
        1 for r in records
        if (r.get("adr_meta", {}) or {}).get("replaces_system_ref")
    )

    # Gruppieren nach Org → Repo
    by_org: dict[str, dict[str, list[dict]]] = defaultdict(lambda: defaultdict(list))
    for r in records:
        by_org[r["org"]][r["repo"]].append(r)

    org_chip = lambda o: f'<span class="org-chip org-{html.escape(o)}">{html.escape(o)}</span>'
    role_chip = lambda r: (
        f'<span class="role-{r}">{r}</span>' if r in {"root", "hybrid"}
        else '<span class="role-default">—</span>'
    )

    # ---- Detail-Panel-Renderer ----
    def render_detail(r: dict, idx: int) -> str:
        d = r["data"]
        warnings = all_warnings.get(idx, [])

        # Warnings-Block oben im Panel (F3/F4-Output)
        warn_html = ""
        if warnings:
            items = []
            for w in warnings:
                sev_class = "warn-error" if w["severity"] == "error" else "warn-warning"
                icon = "❌" if w["severity"] == "error" else "⚠"
                items.append(f'<li class="{sev_class}">{icon} <b>{w["code"]}</b> · {html.escape(w["msg"])}</li>')
            warn_html = f'<div class="warnings"><h4>Drift-Validierung ({len(warnings)})</h4><ul class="compact">{"".join(items)}</ul></div>'

        # F11 — Render-only-KDs: anderes Detail (kein Spec)
        if r.get("kind", "spec") != "spec":
            html_files = d.get("_html_files") or [d.get("_html_file")]
            html_files_str = ", ".join(f'<code>{html.escape(f)}</code>' for f in html_files if f)
            rel_path = ""
            try:
                rel_path = str(r["path"].relative_to(REPOS_ROOT))
            except (ValueError, KeyError):
                rel_path = str(r.get("path", "?"))
            # Mockup-URL: für render-only-inline ist der Pfad direkt der HTML, sonst gibt's mehrere
            if r["kind"] == "render-only-inline":
                mockup_url = url_for_path(r["path"])
                mockup_link = (
                    f'<div class="mockup-link"><a href="{mockup_url}" target="_blank">'
                    f'📱 → {html.escape(r["path"].name)} öffnen</a></div>'
                ) if mockup_url else ""
            else:
                # Subdir mit HTMLs — erste finden
                mh = find_mockup_html(r["path"].parent, r["kd"])
                mockup_link = (
                    f'<div class="mockup-link"><a href="{url_for_path(mh)}" target="_blank">'
                    f'📱 → {html.escape(mh.name)} öffnen</a></div>'
                ) if mh else ""
            return f"""
    <tr class="detail-row" id="detail-{idx}">
      <td colspan="13" class="detail-cell">
        {warn_html}
        <div class="muted">Render-only-KD (kein <code>screens-spec.yaml</code>) — gemäß <code>platform:ADR-211</code> I1 nicht konform.</div>
        <div class="small muted">HTML-Dateien: {html_files_str or "—"}</div>
        {mockup_link}
        <div class="spec-path small muted">Pfad: <code>~/github/{html.escape(rel_path)}</code></div>
      </td>
    </tr>"""

        # Personas
        personas_obj = d.get("personas") or {}
        if isinstance(personas_obj, dict):
            ppairs = personas_obj.items()
        elif isinstance(personas_obj, list):
            ppairs = []
            for p in personas_obj:
                if isinstance(p, dict) and "id" in p:
                    ppairs.append((p["id"], p))
                else:
                    ppairs.append((str(p), {}))
        else:
            ppairs = []
        persona_items = []
        for pname, pdata in ppairs:
            desc = pdata.get("description", "") if isinstance(pdata, dict) else ""
            rechte = pdata.get("rechte", []) if isinstance(pdata, dict) else []
            persona_items.append(
                f'<li><b>{html.escape(pname)}</b>'
                + (f' <span class="muted">— {html.escape(desc)}</span>' if desc else '')
                + (f'<br/><span class="small muted">Rechte: {html.escape(", ".join(rechte))}</span>' if rechte else '')
                + '</li>'
            )
        personas_html = f'<ul class="compact">{"".join(persona_items)}</ul>' if persona_items else '<span class="muted">—</span>'

        # Screens
        screens = d.get("screens", []) or []
        screen_items = []
        for s in screens:
            if not isinstance(s, dict):
                continue
            sid = s.get("id", "?")
            stitle = s.get("title", "")
            sper = s.get("persona") or s.get("personas") or []
            if isinstance(sper, str):
                sper = [sper]
            sper_str = ", ".join(sper) if sper else "—"
            screen_items.append(
                f'<li><code>{html.escape(sid)}</code> <b>{html.escape(str(stitle))}</b>'
                + f'<br/><span class="small muted">Personas: {html.escape(sper_str)}</span></li>'
            )
        screens_html = f'<ul class="compact">{"".join(screen_items)}</ul>' if screen_items else '<span class="muted">—</span>'

        # Beziehungen
        rel_lines = []
        cf = d.get("consumes_from") or []
        if cf:
            for entry in cf:
                ref = entry.get("ref", "?") if isinstance(entry, dict) else str(entry)
                entities = entry.get("entities", []) if isinstance(entry, dict) else []
                rel_lines.append(f'<li><span class="rel-tag rel-cf">consumes_from</span> <code>{html.escape(ref)}</code> ({len(entities)} entities)</li>')
        pc = d.get("provides_contracts") or []
        if pc:
            for entry in pc:
                cid = entry.get("schema_ref") or entry.get("id", "?")
                rel_lines.append(f'<li><span class="rel-tag rel-pc">provides_contracts</span> <code>{html.escape(cid)}</code></li>')
        ac = d.get("accepts_contracts") or []
        if ac:
            for entry in ac:
                cid = entry.get("schema_ref") or entry.get("id", "?")
                rel_lines.append(f'<li><span class="rel-tag rel-ac">accepts_contracts</span> <code>{html.escape(cid)}</code></li>')
        re_root = d.get("root_entities") or {}
        if re_root:
            n = len(re_root) if isinstance(re_root, dict) else len(list(re_root))
            rel_lines.append(f'<li><span class="rel-tag rel-rt">root_entities</span> {n} exponiert</li>')
        rel_html = f'<ul class="compact">{"".join(rel_lines)}</ul>' if rel_lines else '<span class="muted">standalone — keine Cross-KD-Beziehungen</span>'

        # Spec-Pfad + Mermaid-Detail-Link (wenn vorhanden)
        rel_path = ""
        try:
            rel_path = str(r["path"].relative_to(REPOS_ROOT))
        except (ValueError, KeyError):
            rel_path = str(r.get("path", "?"))

        # Per-Repo-Mermaid-Lineage (Stufe 1b, F12: nur wenn ≥2 KDs im Repo)
        repo_kd_count = sum(1 for x in records if x["repo"] == r["repo"] and x.get("kind", "spec") == "spec")
        if repo_kd_count >= 2:
            lineage_link = (
                '<div class="lineage-link">'
                f'🌐 Topologie für <code>{html.escape(r["repo"])}</code>: '
                f'<a href="lineage-{html.escape(r["repo"])}.html" target="_blank">→ Mermaid-Lineage öffnen</a>'
                '</div>'
            )
        else:
            lineage_link = (
                '<div class="lineage-link muted small">'
                f'ℹ Nur 1 KD in <code>{html.escape(r["repo"])}</code> — kein eigener Mermaid-Graph generiert.'
                '</div>'
            )

        # Mockup-HTML (Stufe 1b: "Klickdummy klickbar")
        mockup_html_path = find_mockup_html(r["path"].parent, r["kd"])
        if mockup_html_path:
            mockup_url = url_for_path(mockup_html_path)
            mockup_link = (
                '<div class="mockup-link">'
                f'📱 Klickdummy-Mockup: '
                f'<a href="{mockup_url}" target="_blank">→ {html.escape(mockup_html_path.name)} öffnen</a>'
                f' <span class="small muted">(echter klickbarer HTML-Render)</span>'
                '</div>'
            ) if mockup_url else ""
        else:
            # Render-Fallback: aus Spec generierte minimal-klickbare HTML
            mockup_link = (
                '<div class="mockup-link">'
                f'🔬 Auto-Render aus Spec: '
                f'<a href="/genesor/render/{html.escape(r["repo"])}-{html.escape(r["kd"])}.html" target="_blank">→ Spec-Render öffnen</a>'
                f' <span class="small muted">(klickbar — Persona-Filter, kein eigenes Design)</span>'
                '</div>'
            )

        # Grounding-Info
        g = d.get("grounding", {}) or {}
        ground_lines = []
        for k in ("domain", "achse", "pilot_stakeholder", "pilot_lra", "konzept_ref", "prozessmodell"):
            if k in g:
                v = g[k]
                v_str = ", ".join(v) if isinstance(v, list) else str(v)
                ground_lines.append(f'<li><b>{k}:</b> {html.escape(v_str[:120])}</li>')
        ground_html = f'<ul class="compact">{"".join(ground_lines)}</ul>' if ground_lines else ""

        # Use-Cases-Section + Replaces-Section (Rev-15-Vorgriff)
        adr_meta = r.get("adr_meta") or {}
        ucs_list = adr_meta.get("realizes_use_cases") or []
        replaces_ref = adr_meta.get("replaces_system_ref")
        ucs_html = ""
        # Link auf UC-Repo-Index mit Filter (Workshop 2026-05-26 #2)
        kd_filter_url = f'./uc-{html.escape(r["repo"])}.html?kd={html.escape(r["kd"])}'
        if ucs_list:
            uc_items = "".join(f"<li><code>{html.escape(uc)}</code></li>" for uc in ucs_list)
            ucs_html = (
                f'<h4>📋 Realisiert Use Cases ({len(ucs_list)}) '
                f'<a href="{kd_filter_url}" style="font-size:12px;font-weight:normal;color:#06c;">→ alle UCs für diesen KD</a></h4>'
                f'<ul class="compact">{uc_items}</ul>'
            )
        elif r.get("kind", "spec") == "spec":
            ucs_html = (
                f'<h4>📋 Use Cases</h4>'
                f'<span class="muted small">— keine <code>realizes_use_cases:</code> im ADR-Frontmatter · </span>'
                f'<a href="{kd_filter_url}" style="font-size:13px;color:#06c;">'
                f'→ UC-Liste für diesen KD öffnen</a>'
                f'<div class="muted small" style="margin-top:4px;">'
                f'(Per-Discovery-UCs werden auf der UC-Index-Page gezeigt, gefiltert nach diesem KD)'
                f'</div>'
            )
        replaces_html = ""
        if replaces_ref:
            replaces_html = f'<h4 style="margin-top:8px;">🔄 Löst ab</h4><code>{html.escape(replaces_ref)}</code> <span class="small muted">(siehe docs/inventur/fv-inventur.yaml)</span>'

        return f"""
    <tr class="detail-row" id="detail-{idx}">
      <td colspan="13" class="detail-cell">
        {warn_html}
        <div class="detail-grid">
          <div>
            <h4>👥 Personas ({len(persona_items)})</h4>
            {personas_html}
          </div>
          <div>
            <h4>🖼 Screens ({len(screens)})</h4>
            {screens_html}
          </div>
          <div>
            <h4>🔗 Beziehungen</h4>
            {rel_html}
            {ucs_html}
            {replaces_html}
            {('<h4 style="margin-top:12px;">📌 Grounding</h4>' + ground_html) if ground_html else ''}
          </div>
        </div>
        {mockup_link}
        {lineage_link}
        <div class="spec-path small muted">Spec: <code>~/github/{html.escape(rel_path)}</code></div>
      </td>
    </tr>"""

    rows: list[str] = []
    # idx muss konsistent zu den all_warnings-Keys sein (Reihenfolge wie records)
    by_record_idx = {id(r): i for i, r in enumerate(records)}
    iter_idx = 0
    for org in sorted(by_org):
        for repo in sorted(by_org[org]):
            kd_records = sorted(by_org[org][repo], key=lambda r: r["kd"])
            for r in kd_records:
                d = r["data"]
                idx = by_record_idx[id(r)]   # echter Index für warnings-Lookup
                is_render_only = r.get("kind", "spec") != "spec"

                if is_render_only:
                    title = "render-only (Spec fehlt)"
                    klass = "—"
                    role = "default"
                    sunset_cell_class, sunset_cell_text = "sunset-na", "—"
                    n_screens = 0
                    personas = "—"
                    kunde = kunde_from(d, org)
                else:
                    title = (d.get("title") or r["kd"]).split("—")[0].strip()[:55]
                    klass = d.get("class") or "?"
                    role = d.get("spec_role") or "default"
                    sunset_cell_class, sunset_cell_text = compute_sunset_badge(d)
                    n_screens = len(d.get("screens", []) or [])
                    personas_obj = d.get("personas") or {}
                    if isinstance(personas_obj, dict):
                        personas_list = list(personas_obj.keys())
                    elif isinstance(personas_obj, list):
                        personas_list = [p.get("id", str(p)) if isinstance(p, dict) else str(p) for p in personas_obj]
                    else:
                        personas_list = []
                    personas = ", ".join(personas_list[:3])
                    if len(personas_list) > 3:
                        personas += f" +{len(personas_list)-3}"
                    personas = personas or "—"
                    kunde = kunde_from(d, org)

                # Warning-Badge in der ersten Zelle
                warns_for_kd = all_warnings.get(idx, [])
                n_err = sum(1 for w in warns_for_kd if w["severity"] == "error")
                n_w = sum(1 for w in warns_for_kd if w["severity"] == "warning")
                badge = ""
                if n_err:
                    badge = f'<span class="warn-badge warn-error" title="{n_err} Errors">❌{n_err}</span>'
                elif n_w:
                    badge = f'<span class="warn-badge warn-warning" title="{n_w} Warnings">⚠{n_w}</span>'

                # Rev-15-Spalten: UCs + Replaces
                adr_meta = r.get("adr_meta") or {}
                ucs_list = adr_meta.get("realizes_use_cases") or []
                n_kd_ucs = len(ucs_list) if isinstance(ucs_list, list) else 0
                ucs_cell = (
                    f'<a href="./uc-{html.escape(r["repo"])}.html" style="color:#06c;font-weight:600;text-decoration:none;" title="Alle UCs in {html.escape(r["repo"])}">{n_kd_ucs}</a>'
                    if n_kd_ucs else
                    f'<a href="./uc-{html.escape(r["repo"])}.html" style="color:#999;text-decoration:none;" title="UC-Liste für {html.escape(r["repo"])} (leer für diesen KD)">—</a>'
                )
                replaces_ref = adr_meta.get("replaces_system_ref")
                replaces_cell = f'<code>{html.escape(replaces_ref)}</code>' if replaces_ref else '<span class="muted">—</span>'

                org_cell = org_chip(org)
                repo_cell = f'<code>{html.escape(repo)}</code>'

                # Surface-Switcher: KD / Dev / Staging / Stable (Pilot-Memo §Surface)
                app_info = apps_index.get(repo, {})
                surface_urls = app_info.get("urls", {})
                # KD-Spec ist immer da — entweder Mockup-HTML oder Auto-Render
                kd_mockup = find_mockup_html(r["path"].parent, r["kd"])
                kd_url = url_for_path(kd_mockup) if kd_mockup else (
                    f"/genesor/render/{html.escape(r['repo'])}-{html.escape(r['kd'])}.html"
                )
                # Sichtbarer Flag: KD ohne echtes Mockup-HTML → nur Spec-Render.
                mockup_missing_badge = (
                    '<span class="warn-badge warn-warning mockup-missing" '
                    'title="Kein echtes Mockup-HTML im KD-Verzeichnis — Link zeigt auf den '
                    'aus der Spec generierten Auto-Render.">⚠ Mockup fehlt · nur Spec-Render</span> '
                    if kd_mockup is None else ""
                )
                # Feature B: "🛠 Mockup generieren" — nur wenn kein echtes Mockup existiert.
                # Verlinkt auf ein vorausgefülltes GitHub-Issue (labels=klickdummy,auto).
                mockup_generate_btn = ""
                if kd_mockup is None:
                    from urllib.parse import quote as _quote
                    _issue_title = f'[klickdummy] {r["kd"]} bauen'
                    # Idempotenz-Schlüssel (KONZ-iil-klickdummy-001, Teil A): identisch zum
                    # Sentinel von klickdummy_sync.py (find_existing_issue) — so erkennt der Sync
                    # button-erzeugte Issues und legt keine Dublette an / kann sie rekonziliieren.
                    _issue_body = (
                        f'Mockup für {repo}:{r["kd"]} bauen gemäß ADR-211, '
                        f'angefordert über genesor.\n\n'
                        f'<!-- klickdummy-sync:{r["kd"]} -->'
                    )
                    _issue_url = (
                        f'https://github.com/{detect_org(repo)}/{repo}/issues/new'
                        f'?title={_quote(_issue_title)}'
                        f'&labels=klickdummy,auto'
                        f'&body={_quote(_issue_body)}'
                    )
                    mockup_generate_btn = (
                        f'<a class="mockup-gen-btn" href="{html.escape(_issue_url, quote=True)}" '
                        f'target="_blank" rel="noopener" '
                        f'title="GitHub-Issue zum Bau dieses Mockups vorausfüllen (labels=klickdummy,auto)" '
                        f'onclick="event.stopPropagation(); mockupGenStart(this);">'
                        f'🛠 Mockup generieren</a> '
                    )

                # Screen×Surface-Matrix als JSON-Datenstruktur fürs Modal
                screen_routes = _extract_screen_routes(r)
                import json as _json
                modal_payload = _json.dumps({
                    "repo": repo,
                    "kd": r["kd"],
                    "kd_title": title,
                    "kd_url": kd_url,
                    "surface_base": {
                        "dev": surface_urls.get("dev"),
                        "staging": surface_urls.get("staging"),
                        "prod": surface_urls.get("prod"),
                    },
                    "screens": screen_routes,
                }, ensure_ascii=False)

                surfaces = [
                    ("kd",      "📋 KD",  kd_url,                       "Klickdummy-Spec / Render"),
                    ("dev",     "🛠 Dev", surface_urls.get("dev"),      "Development-Environment"),
                    ("staging", "🧪 Stg", surface_urls.get("staging"),  "Staging-Environment"),
                    ("prod",    "✅ Prod", surface_urls.get("prod"),    "Production / Stable"),
                ]
                surface_pills = []
                for code, label, url, surface_title in surfaces:
                    if url:
                        surface_pills.append(
                            f'<button class="surface-pill surface-{code} active" '
                            f'data-surface="{code}" '
                            f'title="{html.escape(surface_title)} — Modal mit Screen-Liste öffnen" '
                            f'onclick="event.stopPropagation(); openSurfaceModal(this);">'
                            f'{label}</button>'
                        )
                    else:
                        surface_pills.append(
                            f'<span class="surface-pill surface-{code} disabled" '
                            f'title="{html.escape(surface_title)}: nicht verfügbar">{label}</span>'
                        )
                # Modal-Payload als data-Attribut nur EINMAL pro Zeile
                surface_cell = (
                    f'<div class="surface-tabs" data-modal-payload="{html.escape(modal_payload, quote=True)}">'
                    + "".join(surface_pills)
                    + '</div>'
                )

                # Drift-Status-Spalte (Pilot-Memo 2026-05-26)
                d_info = drift_by_idx.get(idx, {})
                d_status = d_info.get("status", "?")
                d_label = d_info.get("status_label", "?")
                d_color = d_info.get("status_color", "#999")
                d_compare = d_info.get("compare_url")
                d_cov = d_info.get("coverage_pct", 0)
                d_expected = d_info.get("n_expected_briefs", 0)
                if d_status == "no-spec-brief":
                    drift_cell = '<span class="muted small">—</span>'
                elif d_compare:
                    drift_cell = (
                        f'<span class="drift-badge" style="background:{d_color}20;color:{d_color};" title="Brief-Coverage: {d_cov}% ({d_info.get("n_actual_briefs",0)}/{d_expected})">'
                        f'● {html.escape(d_label)}</span> '
                        f'<a href="{html.escape(d_compare)}" target="_blank" class="compare-link" '
                        f'title="Brief §10 Drift-Sektion öffnen" onclick="event.stopPropagation();">🔍</a>'
                    )
                else:
                    drift_cell = (
                        f'<span class="drift-badge" style="background:{d_color}20;color:{d_color};" '
                        f'title="{d_expected} Screen(s) mit implementation_brief, aber noch keine Briefs generiert">'
                        f'○ {html.escape(d_label)}</span>'
                    )

                rows.append(f"""
    <tr class="kd-row {'render-only' if is_render_only else ''}" data-detail-id="detail-{idx}" data-drift-status="{d_status}" data-org="{html.escape(org)}" onclick="toggleDetail(this)">
      <td class="org-cell">{org_cell}</td>
      <td class="repo-cell">{repo_cell}</td>
      <td><span class="toggle">▸</span> {badge} <b>{html.escape(r["kd"])}</b><br/>{mockup_missing_badge}{mockup_generate_btn}<span class="muted">{html.escape(title)}</span></td>
      <td>{role_chip(role)}</td>
      <td><span class="klass-{html.escape(klass)}">{html.escape(klass)}</span></td>
      <td class="num">{n_screens}</td>
      <td class="num">{ucs_cell}</td>
      <td class="surface-cell">{surface_cell}</td>
      <td class="small">{drift_cell}</td>
      <td class="small">{replaces_cell}</td>
      <td class="small {sunset_cell_class}">{html.escape(sunset_cell_text)}</td>
      <td class="small">{html.escape(personas)}</td>
      <td class="small">{html.escape(kunde)[:40]}</td>
    </tr>""")
                rows.append(render_detail(r, idx))
                iter_idx += 1

    table_body = "".join(rows)

    # ── Feature C2: Acceptance-Matrix (ADR-211 §Acceptance) ──────────────────
    # Eine Zeile pro KD, Spalten = die zwei Achsen spec_signed/ui_walked.
    # Liest die ECHTE acceptance-Sektion aus der Spec (KD-Level). Die meisten
    # KDs haben (noch) keinen Sign-Off → Status "none" / "offen" — genau das ist
    # der Sinn: sichtbar machen, wo eine Abnahme fehlt.
    _ac_axis_labels = {"spec_signed": "PO-Sign-Off", "ui_walked": "Workshop-Walk"}
    _am_rows: list[str] = []
    _am_open_count = 0  # KDs mit mindestens einer offenen Achse
    for r in records:
        ac_status = compute_acceptance_status((r.get("data") or {}).get("acceptance"))
        cells = []
        row_has_open = False
        for axis in _ACCEPTANCE_AXES:
            info = ac_status.get(axis, {})
            st = info.get("status", "missing")
            label = _ac_axis_labels.get(axis, axis)
            if st == "signed":
                chip = (
                    f'<span class="ac-chip ac-signed" title="{html.escape(label)}: '
                    f'{html.escape(str(info.get("latest_by") or "?"))} · '
                    f'{html.escape(str(info.get("latest_date") or ""))} · '
                    f'ref={html.escape(str(info.get("latest_ref") or "—"))}">'
                    f'✓ signed</span>'
                )
            elif st == "stale":
                chip = (
                    f'<span class="ac-chip ac-stale" title="{html.escape(label)}: '
                    f'letzter Eintrag {info.get("age_days")}d alt '
                    f'({html.escape(str(info.get("latest_date") or ""))}) — '
                    f'Spec-Drift möglich, neue Abnahme empfohlen">⚠ stale</span>'
                )
                row_has_open = True
            else:
                chip = (
                    f'<span class="ac-chip ac-none" title="{html.escape(label)}: '
                    f'keine Abnahme erfasst">offen</span>'
                )
                row_has_open = True
            cells.append(f'<td>{chip}</td>')
        if row_has_open:
            _am_open_count += 1
        repo = r["repo"]
        org = r.get("org") or detect_org(repo)
        _am_rows.append(
            f'<tr>'
            f'<td class="am-label">{org_chip(org)} <code>{html.escape(repo)}</code> · '
            f'<b>{html.escape(r["kd"])}</b></td>'
            f'{"".join(cells)}'
            f'</tr>'
        )
    acceptance_matrix_section = (
        '<details class="acceptance-matrix">'
        f'<summary>✍️ Acceptance-Matrix — {_am_open_count}/{len(records)} KD(s) mit '
        'offener Abnahme (klicken zum Aufklappen)</summary>'
        '<table>'
        '<thead><tr>'
        '<th>Repo · Klickdummy</th>'
        f'<th title="ADR-211 Achse spec_signed">{_ac_axis_labels["spec_signed"]}</th>'
        f'<th title="ADR-211 Achse ui_walked">{_ac_axis_labels["ui_walked"]}</th>'
        '</tr></thead>'
        f'<tbody>{"".join(_am_rows)}</tbody>'
        '</table>'
        '</details>'
    )

    # Skin-Switcher-Optionen für die Genesor-Topbar — aus skin_library() generiert,
    # damit sie --skin-base respektieren (statt hardcodierter /iil-klickdummy/...-URLs).
    # Kurze Labels (ohne Klammer-Zusatz) wie in der bisherigen Hardcoded-Variante.
    _genesor_skin_short_labels = {
        "okwobis-look.css": "OK.Wobis-Look",
        "prosoz-look.css": "Prosoz-Look",
        "arriba-look.css": "ARRIBA-Look",
        "bayernid-look.css": "BayernID-Look",
    }
    _genesor_skin_options = []
    for _value, _label in skin_library():
        if _value == "__greenfield":
            _genesor_skin_options.append('<option value="__greenfield">Greenfield (Default)</option>')
            continue
        _short = _genesor_skin_short_labels.get(_value.rsplit("/", 1)[-1], _label)
        _genesor_skin_options.append(
            f'<option value="{html.escape(_value)}">{html.escape(_short)}</option>'
        )
    genesor_skin_options = "\n      ".join(_genesor_skin_options)

    return f"""<!DOCTYPE html>
<html lang="de">
<head>
<meta charset="utf-8">
<title>IIL-Genesor — Klickdummy-Übersicht (Cross-Repo)</title>
<style>
  body {{ font-family: -apple-system, system-ui, sans-serif; margin: 0; color: #222; background: #fafafa; }}
  header {{ padding: 14px 24px; background: linear-gradient(90deg,#06c,#48c); color:#fff; }}
  header h1 {{ margin: 0; font-size: 20px; }}
  header .sub {{ font-size: 13px; opacity: 0.9; margin-top: 4px; }}
  main {{ padding: 20px 24px; }}
  .stats {{ display: flex; gap: 18px; flex-wrap: wrap; background: #fff; border: 1px solid #e0e0e0; border-radius: 6px; padding: 12px 16px; margin-bottom: 16px; font-size: 14px; }}
  .stats .kv {{ display: flex; flex-direction: column; }}
  .stats .kv .n {{ font-size: 22px; font-weight: 600; color: #06c; }}
  .stats .kv .lbl {{ font-size: 11px; color: #888; text-transform: uppercase; letter-spacing: 0.5px; }}
  table {{ width: 100%; background: #fff; border-collapse: collapse; border: 1px solid #e0e0e0; border-radius: 6px; overflow: hidden; font-size: 13px; }}
  th {{ background: #f0f4f8; text-align: left; padding: 8px 10px; font-weight: 600; color: #444; border-bottom: 1px solid #d0d0d0; }}
  td {{ padding: 8px 10px; border-bottom: 1px solid #ececec; vertical-align: top; }}
  td.org-cell, td.repo-cell {{ background: #fafafa; }}
  td.num {{ text-align: right; }}
  .muted {{ color: #888; }}
  .small {{ font-size: 12px; }}
  code {{ background: #f0f0f0; padding: 1px 6px; border-radius: 3px; font-size: 12px; }}
  .org-chip {{ display: inline-block; padding: 2px 8px; border-radius: 12px; font-size: 11px; font-weight: 600; color: #fff; }}
  .org-chip.org-meiki-lra {{ background: #06c; }}
  .org-chip.org-ttz-lif {{ background: #093; }}
  .org-chip.org-bahn-sqf {{ background: #c40; }}
  .org-chip.org-iilgmbh {{ background: #639; }}
  .org-chip.org-achimdehnert {{ background: #555; }}
  .role-root {{ display: inline-block; padding: 2px 6px; background: #cef; border-radius: 4px; font-size: 11px; }}
  .role-hybrid {{ display: inline-block; padding: 2px 6px; background: #fec; border-radius: 4px; font-size: 11px; }}
  .role-default {{ color: #999; font-size: 11px; }}
  .klass-mock {{ display: inline-block; padding: 1px 6px; background: #fee; color: #a00; border-radius: 3px; font-size: 11px; }}
  .klass-stub-demo, .klass-spec-demo, .klass-story {{ display: inline-block; padding: 1px 6px; background: #efe; color: #060; border-radius: 3px; font-size: 11px; }}
  footer {{ padding: 12px 24px; color: #888; font-size: 12px; text-align: center; }}

  /* Klickbare KD-Zeilen + Detail-Panel */
  tr.kd-row {{ cursor: pointer; transition: background 0.1s; }}
  tr.kd-row:hover {{ background: #f5f9ff; }}
  tr.kd-row .toggle {{ color: #06c; font-weight: 600; display: inline-block; width: 12px; transition: transform 0.15s; }}
  tr.kd-row.open .toggle {{ transform: rotate(90deg); }}
  tr.detail-row {{ display: none; }}
  tr.detail-row.visible {{ display: table-row; }}
  td.detail-cell {{ background: #fbfdff; padding: 14px 20px; border-bottom: 2px solid #cce; }}
  .detail-grid {{ display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 18px; margin-bottom: 12px; }}
  .detail-cell h4 {{ margin: 0 0 6px 0; font-size: 13px; color: #06c; }}
  ul.compact {{ margin: 0; padding-left: 18px; }}
  ul.compact li {{ margin-bottom: 4px; font-size: 12px; }}
  .rel-tag {{ display: inline-block; padding: 1px 5px; border-radius: 3px; font-size: 10px; font-weight: 600; margin-right: 4px; }}
  .rel-cf {{ background: #def; color: #06c; }}
  .rel-pc {{ background: #fde; color: #c0c; }}
  .rel-ac {{ background: #efe; color: #060; }}
  .rel-rt {{ background: #fec; color: #c80; }}
  .lineage-link, .mockup-link {{ background: #fff; border: 1px solid #cce; border-radius: 4px; padding: 8px 12px; margin: 8px 0; font-size: 13px; }}
  .mockup-link {{ border-color: #c80; background: #fffbf0; }}
  .lineage-link a, .mockup-link a {{ color: #06c; text-decoration: none; font-weight: 600; }}
  .lineage-link a:hover, .mockup-link a:hover {{ text-decoration: underline; }}
  .spec-path {{ font-family: monospace; font-size: 11px; padding-top: 4px; }}

  /* Sortable Headers (Stufe 1b) */
  th.sortable {{ cursor: pointer; user-select: none; }}
  th.sortable:hover {{ background: #e0e8f0; }}
  th.sortable::after {{ content: " ⇅"; opacity: 0.3; font-size: 10px; }}
  th.sort-asc::after {{ content: " ▲"; opacity: 1; color: #06c; }}
  th.sort-desc::after {{ content: " ▼"; opacity: 1; color: #06c; }}

  /* Drift-Validierung (Paket A: F3) */
  .warn-badge {{ display: inline-block; padding: 1px 6px; border-radius: 3px; font-size: 11px; font-weight: 600; margin-right: 4px; }}
  .warn-error {{ background: #fee; color: #a00; }}
  .warn-warning {{ background: #fef0d0; color: #a60; }}
  .warnings {{ background: #fff8f0; border: 1px solid #fcc; border-left: 4px solid #c40; padding: 10px 14px; margin-bottom: 12px; border-radius: 4px; }}
  .warnings h4 {{ margin: 0 0 6px 0; color: #c40; font-size: 13px; }}
  .warnings li.warn-error {{ background: none; padding-left: 0; }}
  .warnings li.warn-warning {{ background: none; padding-left: 0; }}
  .n-err {{ color: #c40 !important; }}
  .n-warn {{ color: #b80 !important; }}
  /* Feature B: "Mockup generieren"-Button (nur auf mockup-missing-Zeilen) */
  .mockup-gen-btn {{ display: inline-block; padding: 1px 8px; border-radius: 3px; font-size: 11px; font-weight: 600; margin-right: 6px; text-decoration: none; background: #e0ecff; color: #1d4ed8; border: 1px solid #bcd2ff; cursor: pointer; }}
  .mockup-gen-btn:hover {{ background: #cfe0ff; }}
  .mockup-gen-btn.mockup-gen-running {{ background: #f3f4f6; color: #6b7280; border-color: #d1d5db; pointer-events: none; cursor: default; }}
  /* Feature C2: Acceptance-Matrix — .ac-chip im Genesor-Root (Render-Variante: L578) */
  .ac-chip {{ display: inline-block; padding: 1px 6px; border-radius: 3px; font-size: 10px; font-weight: 600; margin-right: 6px; cursor: help; }}
  .ac-signed {{ background: #d1fae5; color: #065f46; border: 1px solid #a7f3d0; }}
  .ac-stale  {{ background: #fef3c7; color: #92400e; border: 1px solid #fde68a; }}
  .ac-none   {{ background: #f3f4f6; color: #6b7280; border: 1px solid #e5e7eb; }}
  .acceptance-matrix {{ margin: 12px 0; border: 1px solid #e3e8ee; border-radius: 6px; background: #fff; }}
  .acceptance-matrix > summary {{ cursor: pointer; padding: 10px 14px; font-weight: 600; color: #1f2937; list-style: none; }}
  .acceptance-matrix > summary::-webkit-details-marker {{ display: none; }}
  .acceptance-matrix > summary:hover {{ background: #f8fafc; }}
  .acceptance-matrix table {{ margin: 0; width: 100%; }}
  .acceptance-matrix .am-label {{ font-size: 11px; }}

  /* Sunset-Aging (F4) */
  td.sunset-ok {{ color: #060; }}
  td.sunset-near {{ background: #fef0d0; color: #a60; font-weight: 600; }}
  td.sunset-overdue {{ background: #fee; color: #a00; font-weight: 600; }}
  td.sunset-na {{ color: #888; }}

  /* Render-only-KDs (F11) */
  tr.render-only td {{ background: #fafaf0 !important; }}
  tr.render-only .toggle {{ color: #c40; }}

  /* Drift-Center (Pilot-Memo 2026-05-26) */
  .drift-center {{ background: linear-gradient(135deg,#fff 0%,#f8fafc 100%); border: 1px solid #e0e7ef; border-radius: 8px; padding: 16px 20px; margin-bottom: 16px; }}
  .drift-hero h2 {{ margin: 0 0 4px 0; font-size: 18px; color: #1e293b; }}
  .drift-hero p {{ margin: 0 0 12px 0; }}
  .drift-kpis {{ display: flex; gap: 18px; flex-wrap: wrap; padding: 10px 0; border-top: 1px solid #e0e7ef; border-bottom: 1px solid #e0e7ef; margin-bottom: 12px; }}
  .drift-kpis .kv {{ display: flex; flex-direction: column; min-width: 70px; }}
  .drift-kpis .kv .n {{ font-size: 20px; font-weight: 700; color: #06c; }}
  .drift-kpis .kv .lbl {{ font-size: 11px; color: #64748b; text-transform: uppercase; letter-spacing: 0.3px; }}
  .drift-status-in-sync .n {{ color: #16a34a !important; }}
  .drift-status-stale .n {{ color: #ca8a04 !important; }}
  .drift-status-partial .n {{ color: #ea580c !important; }}
  .drift-status-no-brief .n {{ color: #94a3b8 !important; }}
  .drift-filters {{ display: flex; gap: 6px; flex-wrap: wrap; align-items: center; padding-top: 8px; }}
  .filter-label {{ font-size: 12px; color: #64748b; font-weight: 600; margin-right: 4px; }}
  .filter-chip {{ padding: 4px 10px; border: 1px solid #cbd5e1; background: #fff; border-radius: 14px; cursor: pointer; font-size: 12px; transition: all 0.15s; }}
  .filter-chip:hover {{ background: #f1f5f9; }}
  .filter-chip.active {{ background: #06c; color: #fff; border-color: #06c; }}
  #drift-search {{ padding: 5px 10px; border: 1px solid #cbd5e1; border-radius: 14px; font-size: 12px; min-width: 200px; margin-left: 8px; }}

  /* Drift-Badge in Tabellen-Zeile */
  .drift-badge {{ display: inline-block; padding: 2px 8px; border-radius: 10px; font-size: 11px; font-weight: 600; white-space: nowrap; }}
  .compare-link {{ margin-left: 4px; text-decoration: none; opacity: 0.7; transition: opacity 0.15s; }}
  .compare-link:hover {{ opacity: 1; }}

  /* Row-Filter — hidden via class */
  tr.kd-row.hidden, tr.detail-row.hidden {{ display: none; }}

  /* Surface-Switcher (Pilot-Memo §Surface) */
  td.surface-cell {{ padding: 4px 6px; }}
  .surface-tabs {{ display: inline-flex; gap: 2px; flex-wrap: nowrap; }}
  .surface-pill {{
    display: inline-block;
    padding: 3px 8px;
    border-radius: 4px;
    font-size: 11px;
    font-weight: 600;
    text-decoration: none;
    border: 1px solid transparent;
    white-space: nowrap;
    transition: all 0.1s;
  }}
  .surface-pill.active {{ cursor: pointer; }}
  .surface-pill.disabled {{ opacity: 0.32; cursor: not-allowed; }}
  .surface-pill.surface-kd.active      {{ background: #e0f2fe; color: #075985; border-color: #bae6fd; }}
  .surface-pill.surface-kd.active:hover {{ background: #bae6fd; }}
  .surface-pill.surface-dev.active     {{ background: #fef9c3; color: #854d0e; border-color: #fde047; }}
  .surface-pill.surface-dev.active:hover {{ background: #fde047; }}
  .surface-pill.surface-staging.active {{ background: #fed7aa; color: #9a3412; border-color: #fdba74; }}
  .surface-pill.surface-staging.active:hover {{ background: #fdba74; }}
  .surface-pill.surface-prod.active    {{ background: #dcfce7; color: #166534; border-color: #86efac; }}
  .surface-pill.surface-prod.active:hover {{ background: #86efac; }}
  .surface-pill.disabled.surface-kd      {{ background: #f1f5f9; color: #64748b; }}
  .surface-pill.disabled.surface-dev     {{ background: #f1f5f9; color: #64748b; }}
  .surface-pill.disabled.surface-staging {{ background: #f1f5f9; color: #64748b; }}
  .surface-pill.disabled.surface-prod    {{ background: #f1f5f9; color: #64748b; }}

  /* Master-Surface-Toggle im Hero */
  .surface-master {{ display: flex; gap: 6px; align-items: center; margin-top: 8px; padding-top: 8px; border-top: 1px solid #e0e7ef; }}
  .surface-master-label {{ font-size: 12px; color: #64748b; font-weight: 600; }}
  .surface-master button {{
    padding: 4px 12px;
    border: 1px solid #cbd5e1;
    background: #fff;
    border-radius: 14px;
    cursor: pointer;
    font-size: 12px;
    font-weight: 600;
  }}
  .surface-master button.active {{ background: #06c; color: #fff; border-color: #06c; }}
  /* Wenn Master gesetzt → nur passende Pills hervorheben, andere ausgrauen */
  .surface-tabs.master-kd      .surface-pill:not(.surface-kd) {{ opacity: 0.4; }}
  .surface-tabs.master-dev     .surface-pill:not(.surface-dev) {{ opacity: 0.4; }}
  .surface-tabs.master-staging .surface-pill:not(.surface-staging) {{ opacity: 0.4; }}
  .surface-tabs.master-prod    .surface-pill:not(.surface-prod) {{ opacity: 0.4; }}

  /* Surface-Pill als button (statt <a>) */
  button.surface-pill {{ font-family: inherit; cursor: pointer; }}

  /* Surface-Modal (Pilot-Memo §Surface-Modal) */
  .surface-modal {{ display: none; position: fixed; inset: 0; z-index: 9999; }}
  .surface-modal[aria-hidden="false"] {{ display: block; }}
  .surface-modal-backdrop {{
    position: absolute; inset: 0;
    background: rgba(15, 23, 42, 0.55);
    backdrop-filter: blur(2px);
  }}
  .surface-modal-dialog {{
    position: relative;
    max-width: 1000px; width: calc(100vw - 40px);
    max-height: calc(100vh - 60px); overflow-y: auto;
    margin: 30px auto;
    background: #fff;
    border-radius: 10px;
    box-shadow: 0 20px 60px rgba(0,0,0,0.4);
  }}
  .surface-modal header {{
    display: flex; align-items: center; justify-content: space-between;
    padding: 14px 20px;
    background: linear-gradient(90deg,#06c,#48c);
    color: #fff;
    border-radius: 10px 10px 0 0;
  }}
  .surface-modal header h2 {{ margin: 0; font-size: 16px; }}
  .surface-modal-close {{
    background: rgba(255,255,255,0.2); color: #fff;
    border: none; padding: 2px 12px;
    border-radius: 14px; cursor: pointer;
    font-size: 22px; line-height: 1;
  }}
  .surface-modal-close:hover {{ background: rgba(255,255,255,0.35); }}
  .surface-modal-body {{ padding: 16px 20px; }}
  table.surface-screen-table {{ font-size: 12px; width: 100%; border: 1px solid #e0e7ef; }}
  table.surface-screen-table th {{ background: #f1f5f9; padding: 6px 8px; text-align: left; font-weight: 600; font-size: 11px; }}
  table.surface-screen-table td {{ padding: 6px 8px; border-bottom: 1px solid #f1f5f9; vertical-align: top; }}
  table.surface-screen-table td.screen-id {{ font-weight: 600; color: #1e293b; white-space: nowrap; }}
  table.surface-screen-table td.route {{ color: #64748b; font-family: ui-monospace, monospace; font-size: 11px; }}
  .surface-screen-pill {{
    display: inline-block; padding: 2px 8px;
    border-radius: 10px; font-size: 11px; font-weight: 600;
    text-decoration: none;
    border: 1px solid transparent;
  }}
  .surface-screen-pill.kd      {{ background: #e0f2fe; color: #075985; border-color: #bae6fd; }}
  .surface-screen-pill.dev     {{ background: #fef9c3; color: #854d0e; border-color: #fde047; }}
  .surface-screen-pill.staging {{ background: #fed7aa; color: #9a3412; border-color: #fdba74; }}
  .surface-screen-pill.prod    {{ background: #dcfce7; color: #166534; border-color: #86efac; }}
  .surface-screen-pill.disabled {{ background: #f1f5f9; color: #94a3b8; cursor: not-allowed; opacity: 0.5; }}
</style>
</head>
<body>

<header style="display:flex;align-items:center;gap:16px;flex-wrap:wrap;">
  <div style="flex:1;min-width:200px;">
    <h1 style="margin:0;">🌱 IIL-Genesor — Klickdummy-Übersicht</h1>
    <div class="sub">Cross-Repo · auto-generiert · {date.today().isoformat()} · Stufe 1a (statisch)</div>
    <div class="sub" style="margin-top:4px;"><a href="./coverage.html" style="color:#06c;text-decoration:none;">📊 UC ↔ KD Coverage</a> · {n_ucs} Use Cases erfasst</div>
  </div>
  <div style="display:flex;align-items:center;gap:6px;color:#fff;">
    <label for="skin-select" style="font-size:12px;opacity:0.9;">🎨 Demo-Style</label>
    <select id="skin-select" style="padding:5px 10px;border:1px solid rgba(255,255,255,.4);background:rgba(255,255,255,.1);color:#fff;border-radius:4px;font-size:13px;">
      {genesor_skin_options}
    </select>
  </div>
</header>
<script>
  // Skin-Switcher auf Root-Ebene (Genesor) — gleiche localStorage-Logik wie pro Render
  (function() {{
    const SKIN_KEY = 'genesor_skin';
    function applySkin(url) {{
      document.querySelectorAll('link[data-skin="1"]').forEach(l => l.remove());
      if (url && url !== '__greenfield') {{
        const link = document.createElement('link');
        link.rel = 'stylesheet';
        link.href = url;
        link.setAttribute('data-skin', '1');
        document.head.appendChild(link);
      }}
      try {{ localStorage.setItem(SKIN_KEY, url || '__greenfield'); }} catch(e) {{}}
    }}
    let saved = '__greenfield';
    try {{ saved = localStorage.getItem(SKIN_KEY) || '__greenfield'; }} catch(e) {{}}
    const sel = document.getElementById('skin-select');
    if (sel) {{
      sel.value = saved;
      applySkin(saved);
      sel.addEventListener('change', e => applySkin(e.target.value));
    }}
  }})();
</script>

<main>

<div class="stats">
  <div class="kv"><span class="n">{n_kds}</span><span class="lbl">Klickdummies</span></div>
  <div class="kv"><span class="n">{n_orgs}</span><span class="lbl">Orgs / Kunden</span></div>
  <div class="kv"><span class="n">{n_repos}</span><span class="lbl">Repos</span></div>
  <div class="kv"><span class="n">{n_root}</span><span class="lbl">Root</span></div>
  <div class="kv"><span class="n">{n_hybrid}</span><span class="lbl">Hybrid</span></div>
  <div class="kv"><span class="n">{n_render_only}</span><span class="lbl">render-only</span></div>
  <div class="kv"><span class="n">{n_ucs_total}</span><span class="lbl">Use Cases</span></div>
  <div class="kv"><span class="n">{n_replaces}</span><span class="lbl">Ablösungen</span></div>
  <div class="kv"><span class="n n-err">{n_errors}</span><span class="lbl">Spec-Errors</span></div>
  <div class="kv"><span class="n n-warn">{n_warns}</span><span class="lbl">Warnings</span></div>
</div>

<!-- ── Drift-Center (Pilot-Memo 2026-05-26) ─────────────────── -->
<div class="drift-center">
  <div class="drift-hero">
    <h2>🛡️ Genesor als stabile Basis — Drift-Center</h2>
    <p class="muted small">
      Vergleich Klickdummy ↔ Implementierung — pro Zeile öffnet 🔍 die Brief-§10-Drift-Sektion ·
      Surface-Pills wechseln zwischen <b>📋 KD-Spec / 🛠 Dev / 🧪 Staging / ✅ Prod</b>
      ({n_apps_indexed} Apps in <code>iil-relaunch/apps.json</code> indiziert)
    </p>
  </div>
  <div class="surface-master">
    <span class="surface-master-label">Surface-Highlight:</span>
    <button data-master-surface="none" class="active">Alle anzeigen</button>
    <button data-master-surface="kd">📋 KD-Spec</button>
    <button data-master-surface="dev">🛠 Dev</button>
    <button data-master-surface="staging">🧪 Staging</button>
    <button data-master-surface="prod">✅ Prod</button>
  </div>
  <div class="drift-kpis">
    <div class="kv"><span class="n">{n_pilot_kds}</span><span class="lbl">KDs mit Pilot-Brief</span></div>
    <div class="kv"><span class="n">{n_briefs_total}</span><span class="lbl">Briefs generiert</span></div>
    <div class="kv"><span class="n">{n_briefs_expected}</span><span class="lbl">erwartet</span></div>
    <div class="kv drift-status-in-sync"><span class="n">{drift_counter['in-sync']}</span><span class="lbl">🟢 in-sync</span></div>
    <div class="kv drift-status-stale"><span class="n">{drift_counter['stale']}</span><span class="lbl">🟡 stale</span></div>
    <div class="kv drift-status-partial"><span class="n">{drift_counter['partial']}</span><span class="lbl">🟠 partial</span></div>
    <div class="kv drift-status-no-brief"><span class="n">{drift_counter['no-brief']}</span><span class="lbl">⚪ no-brief</span></div>
  </div>
  <div class="drift-filters">
    <span class="filter-label">Filter:</span>
    <button class="filter-chip active" data-filter-org="all">Alle Orgs</button>
    <button class="filter-chip" data-filter-org="achimdehnert">achimdehnert</button>
    <button class="filter-chip" data-filter-org="meiki-lra">meiki-lra</button>
    <button class="filter-chip" data-filter-org="ttz-lif">ttz-lif</button>
    <span class="filter-label" style="margin-left:14px;">Drift-Status:</span>
    <button class="filter-chip active" data-filter-drift="all">Alle</button>
    <button class="filter-chip" data-filter-drift="in-sync">🟢 in-sync</button>
    <button class="filter-chip" data-filter-drift="stale">🟡 stale</button>
    <button class="filter-chip" data-filter-drift="partial">🟠 partial</button>
    <button class="filter-chip" data-filter-drift="no-brief">⚪ no-brief</button>
    <input type="search" id="drift-search" placeholder="Suche Repo, KD, Persona…" />
  </div>
</div>

<p class="muted small">💡 Klick auf eine Zeile öffnet Detail-Panel · 🔍 öffnet Brief-§10 (Drift-Sektion KD↔Code).</p>

{acceptance_matrix_section}

<table id="genesor-table">
  <thead>
    <tr>
      <th class="sortable" data-col="0">Org / Kunde</th>
      <th class="sortable" data-col="1">Repo</th>
      <th class="sortable" data-col="2">Klickdummy</th>
      <th class="sortable" data-col="3">Rolle</th>
      <th class="sortable" data-col="4">Class</th>
      <th class="sortable" data-col="5" data-numeric="1">Screens</th>
      <th class="sortable" data-col="6" data-numeric="1">#UCs</th>
      <th data-col="7" title="Wechsel zwischen Klickdummy-Spec und Implementation-Environments">Surface</th>
      <th class="sortable" data-col="8" title="Drift-Status zwischen KD-Spec und generiertem Brief">Drift ↔ KD/Code</th>
      <th class="sortable" data-col="9">Replaces</th>
      <th class="sortable" data-col="10">Sunset</th>
      <th class="sortable" data-col="11">Personas</th>
      <th class="sortable" data-col="12">Stakeholder / LRA</th>
    </tr>
  </thead>
  <tbody>{table_body}
  </tbody>
</table>

</main>

<!-- ── Surface-Modal (Pilot-Memo §Surface-Modal) ──────────── -->
<div id="surface-modal" class="surface-modal" aria-hidden="true">
  <div class="surface-modal-backdrop" onclick="closeSurfaceModal()"></div>
  <div class="surface-modal-dialog" role="dialog" aria-labelledby="surface-modal-title">
    <header>
      <h2 id="surface-modal-title">Screen-Vergleich</h2>
      <button class="surface-modal-close" onclick="closeSurfaceModal()" title="Schließen (Esc)">×</button>
    </header>
    <div class="surface-modal-body">
      <p class="muted small" id="surface-modal-subtitle">…</p>
      <table class="surface-screen-table">
        <thead><tr>
          <th>Screen</th>
          <th>Route</th>
          <th>📋 KD</th>
          <th>🛠 Dev</th>
          <th>🧪 Stg</th>
          <th>✅ Prod</th>
        </tr></thead>
        <tbody id="surface-screen-tbody"></tbody>
      </table>
      <p class="muted small" style="margin-top:10px;">
        💡 Wenn Dev/Stg/Prod-Pill grau ist: entweder hat der KD-Screen kein <code>route:</code>-Feld
        in der Spec, oder das Environment ist noch nicht deployed. Spec ergänzen für 1:1-Matching.
      </p>
    </div>
  </div>
</div>

<footer>
  IIL-Genesor · Stufe 1a (cross-repo statisch) · <code>scripts/klickdummy_lineage.py --genesor</code>
</footer>

<script>
function toggleDetail(row) {{
  const detailId = row.dataset.detailId;
  const detail = document.getElementById(detailId);
  if (!detail) return;
  const isOpen = detail.classList.toggle('visible');
  row.classList.toggle('open', isOpen);
}}

// Feature B: "🛠 Mockup generieren" — Issue öffnet im neuen Tab (href/target),
// hier nur Sofort-Feedback: Label umschalten + Button entschärfen.
function mockupGenStart(btn) {{
  if (!btn || btn.dataset.genStarted === '1') return;
  btn.dataset.genStarted = '1';
  btn.textContent = '⏳ generieren läuft…';
  btn.classList.add('mockup-gen-running');
  btn.setAttribute('aria-disabled', 'true');
}}

// Surface-Modal (Pilot-Memo §Surface-Modal — Screen×Surface-Matrix pro KD)
function openSurfaceModal(pillBtn) {{
  const tabs = pillBtn.closest('.surface-tabs');
  if (!tabs) return;
  const raw = tabs.dataset.modalPayload;
  if (!raw) return;
  let payload;
  try {{ payload = JSON.parse(raw); }}
  catch (e) {{ console.error('Modal-Payload parse error', e); return; }}

  const modal = document.getElementById('surface-modal');
  const title = document.getElementById('surface-modal-title');
  const subtitle = document.getElementById('surface-modal-subtitle');
  const tbody = document.getElementById('surface-screen-tbody');

  title.textContent = `${{payload.repo}} / ${{payload.kd}}`;
  subtitle.innerHTML = `<b>${{payload.kd_title || ''}}</b> · Surface-Pill geklickt: <b>${{pillBtn.dataset.surface}}</b>`;

  // Pro Screen eine Zeile
  tbody.innerHTML = '';
  const screens = payload.screens || [];
  if (!screens.length) {{
    tbody.innerHTML = '<tr><td colspan="6" class="muted small" style="text-align:center;padding:20px;">Keine Screens im Spec gefunden.</td></tr>';
  }}
  // HTML-escape helper — wichtig für Routes mit <ausschreibung_id> u.ä.
  const esc = (s) => String(s || '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');

  screens.forEach(s => {{
    // route_example zuerst (hat konkrete IDs), sonst route mit Platzhaltern
    const displayRoute = s.route_example || s.route || '';
    const route = displayRoute;  // gleiche Datenbasis fürs URL-Bauen
    const apiHint = (s.api_paths && s.api_paths.length)
      ? `<br><span class="muted small">API: ${{s.api_paths.map(esc).join(', ')}}</span>`
      : '';
    // KD-Render mit Anchor zum Screen
    const kdUrl = payload.kd_url ? `${{payload.kd_url}}#screen-${{s.screen_id}}` : '';
    const kdPill = kdUrl
      ? `<a class="surface-screen-pill kd" href="${{kdUrl}}" target="_blank" title="KD-Render mit Screen-Anker">📋 KD</a>`
      : `<span class="surface-screen-pill kd disabled">📋 KD</span>`;

    // Dev/Stg/Prod: nur wenn route da UND base-URL gesetzt.
    // Wichtig: Route ist absolut (/submission/...), daher braucht es nur den Origin
    // (Protocol+Host+Port) der Base-URL, NICHT den ganzen Pfad.
    function makeImplPill(env, label) {{
      const base = (payload.surface_base || {{}})[env];
      if (!base || !route) {{
        const reason = !base ? `${{env}}-URL fehlt in apps.json` : 'kein route: im Spec';
        return `<span class="surface-screen-pill ${{env}} disabled" title="${{reason}}">${{label}}</span>`;
      }}
      let origin;
      try {{
        const u = new URL(base);
        origin = `${{u.protocol}}//${{u.host}}`;
      }} catch (e) {{
        // base ist relativ — als Fallback nehme den Server-Origin (Page-Origin)
        origin = window.location.origin;
      }}
      const path = (s.route_example || route).startsWith('/')
        ? (s.route_example || route)
        : `/${{s.route_example || route}}`;
      const full = origin + path;
      return `<a class="surface-screen-pill ${{env}}" href="${{full}}" target="_blank" title="${{full}}">${{label}}</a>`;
    }}

    const row = document.createElement('tr');
    row.innerHTML = `
      <td class="screen-id">${{esc(s.screen_id)}}<br><span class="muted small">${{esc(s.title || '')}}</span></td>
      <td class="route">${{displayRoute ? esc(displayRoute) : '<span class="muted">—</span>'}}${{apiHint}}</td>
      <td>${{kdPill}}</td>
      <td>${{makeImplPill('dev', '🛠 Dev')}}</td>
      <td>${{makeImplPill('staging', '🧪 Stg')}}</td>
      <td>${{makeImplPill('prod', '✅ Prod')}}</td>
    `;
    tbody.appendChild(row);
  }});

  modal.setAttribute('aria-hidden', 'false');
}}

function closeSurfaceModal() {{
  const modal = document.getElementById('surface-modal');
  if (modal) modal.setAttribute('aria-hidden', 'true');
}}

document.addEventListener('keydown', e => {{
  if (e.key === 'Escape') closeSurfaceModal();
}});

// Drift-Center Filter (Pilot-Memo 2026-05-26)
(function() {{
  const state = {{ org: 'all', drift: 'all', search: '' }};

  function applyFilters() {{
    const rows = document.querySelectorAll('#genesor-table tbody tr.kd-row');
    let visible = 0;
    rows.forEach(row => {{
      const org = row.dataset.org || '';
      const drift = row.dataset.driftStatus || '';
      const text = row.innerText.toLowerCase();
      const matchOrg = state.org === 'all' || org === state.org;
      const matchDrift = state.drift === 'all' || drift === state.drift;
      const matchSearch = !state.search || text.includes(state.search);
      const show = matchOrg && matchDrift && matchSearch;
      row.classList.toggle('hidden', !show);
      const detailId = row.dataset.detailId;
      const detail = detailId ? document.getElementById(detailId) : null;
      if (detail) detail.classList.toggle('hidden', !show);
      if (show) visible++;
    }});
    const url = new URL(window.location);
    if (state.org !== 'all') url.searchParams.set('org', state.org); else url.searchParams.delete('org');
    if (state.drift !== 'all') url.searchParams.set('drift', state.drift); else url.searchParams.delete('drift');
    history.replaceState({{}}, '', url);
  }}

  document.querySelectorAll('.filter-chip[data-filter-org]').forEach(btn => {{
    btn.addEventListener('click', () => {{
      document.querySelectorAll('.filter-chip[data-filter-org]').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      state.org = btn.dataset.filterOrg;
      applyFilters();
    }});
  }});
  document.querySelectorAll('.filter-chip[data-filter-drift]').forEach(btn => {{
    btn.addEventListener('click', () => {{
      document.querySelectorAll('.filter-chip[data-filter-drift]').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      state.drift = btn.dataset.filterDrift;
      applyFilters();
    }});
  }});
  const search = document.getElementById('drift-search');
  if (search) {{
    search.addEventListener('input', () => {{
      state.search = search.value.toLowerCase();
      applyFilters();
    }});
  }}

  // Master-Surface-Toggle (Pilot-Memo §Surface)
  function applyMasterSurface(surface) {{
    const allTabs = document.querySelectorAll('.surface-tabs');
    ['kd','dev','staging','prod'].forEach(s => {{
      allTabs.forEach(t => t.classList.remove(`master-${{s}}`));
    }});
    if (surface && surface !== 'none') {{
      allTabs.forEach(t => t.classList.add(`master-${{surface}}`));
    }}
    const url = new URL(window.location);
    if (surface && surface !== 'none') url.searchParams.set('surface', surface);
    else url.searchParams.delete('surface');
    history.replaceState({{}}, '', url);
  }}
  document.querySelectorAll('.surface-master button').forEach(btn => {{
    btn.addEventListener('click', () => {{
      document.querySelectorAll('.surface-master button').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      applyMasterSurface(btn.dataset.masterSurface);
    }});
  }});

  // Initial-State aus URL-Params
  const params = new URLSearchParams(window.location.search);
  const initialOrg = params.get('org');
  const initialDrift = params.get('drift');
  const initialSurface = params.get('surface');
  if (initialOrg) {{
    const btn = document.querySelector(`.filter-chip[data-filter-org="${{initialOrg}}"]`);
    if (btn) btn.click();
  }}
  if (initialDrift) {{
    const btn = document.querySelector(`.filter-chip[data-filter-drift="${{initialDrift}}"]`);
    if (btn) btn.click();
  }}
  if (initialSurface) {{
    const btn = document.querySelector(`.surface-master button[data-master-surface="${{initialSurface}}"]`);
    if (btn) btn.click();
  }}
}})();

// Click-to-Sort auf den Tabellen-Headern (Stufe 1b)
// Sortiert kd-row + zugehörige detail-row als Paar.
document.querySelectorAll('th.sortable').forEach(th => {{
  th.addEventListener('click', () => {{
    const col = parseInt(th.dataset.col, 10);
    const numeric = th.dataset.numeric === '1';
    const tbody = document.querySelector('#genesor-table tbody');
    const allRows = Array.from(tbody.querySelectorAll('tr'));
    // Paare bauen: kd-row + nachfolgende detail-row
    const pairs = [];
    for (let i = 0; i < allRows.length; i++) {{
      if (allRows[i].classList.contains('kd-row')) {{
        const detail = allRows[i + 1];
        pairs.push([allRows[i], detail && detail.classList.contains('detail-row') ? detail : null]);
      }}
    }}
    // Aktuelles Sort-Direction lesen
    const currentDir = th.classList.contains('sort-asc') ? 'asc' : (th.classList.contains('sort-desc') ? 'desc' : null);
    const newDir = currentDir === 'asc' ? 'desc' : 'asc';
    document.querySelectorAll('th.sortable').forEach(h => h.classList.remove('sort-asc', 'sort-desc'));
    th.classList.add('sort-' + newDir);
    // Werte extrahieren + sortieren
    pairs.sort(([rowA], [rowB]) => {{
      const cellA = rowA.cells[col].textContent.trim();
      const cellB = rowB.cells[col].textContent.trim();
      let cmp;
      if (numeric) cmp = parseFloat(cellA) - parseFloat(cellB);
      else cmp = cellA.localeCompare(cellB, 'de');
      return newDir === 'asc' ? cmp : -cmp;
    }});
    // Re-Append in neuer Reihenfolge
    pairs.forEach(([kd, detail]) => {{
      tbody.appendChild(kd);
      if (detail) tbody.appendChild(detail);
    }});
  }});
}});
</script>

</body>
</html>
"""


# ---- Per-Repo-Lineage-Generator (Stufe 1b) ---------------------------------

def find_contracts_in_dir(contracts_dir: Path) -> dict[str, Path]:
    """Find contracts in a given directory (parameterized version of find_contracts)."""
    out: dict[str, Path] = {}
    if not contracts_dir.is_dir():
        return out
    for contract_path in sorted(contracts_dir.glob("*.yaml")):
        try:
            data = yaml.safe_load(contract_path.read_text(encoding="utf-8")) or {}
        except yaml.YAMLError:
            continue
        cid = data.get("contract_id") or f"contracts/{contract_path.stem}"
        out[cid] = contract_path
    return out


def generate_per_repo_lineages(records: list[dict], out_dir: Path) -> list[Path]:
    """Pro Repo eine Mermaid-Lineage-HTML generieren — nur wenn ≥2 KDs mit Spec (F12)."""
    from collections import defaultdict
    by_repo: dict[str, list[dict]] = defaultdict(list)
    for r in records:
        if r.get("kind", "spec") != "spec":
            continue   # render-only KDs ohne Spec im Lineage nichts beizutragen
        by_repo[r["repo"]].append(r)
    written: list[Path] = []
    for repo_name, repo_records in by_repo.items():
        if len(repo_records) < 2:
            continue   # F12: nur sinnvoll bei ≥2 KDs (sonst leerer Graph)
        specs_for_repo = [(r["kd"], r["path"], r["data"]) for r in repo_records]
        # Suche Contracts in zwei möglichen Pfaden:
        contracts_dir_a = REPOS_ROOT / repo_name / "docs" / "01-architektur" / "contracts"
        contracts_dir_b = REPOS_ROOT / repo_name / "contracts"
        repo_contracts: dict[str, Path] = {}
        for cd in (contracts_dir_a, contracts_dir_b):
            repo_contracts.update(find_contracts_in_dir(cd))
        # CD-Upgrade (2026-05-26): doc-profile-basierter Style + Click-Direktiven
        repo_dir = REPOS_ROOT / repo_name
        profile = read_doc_profile(repo_dir)
        style = _DOMAIN_STYLES.get(profile, _DOMAIN_STYLES["default"])
        mermaid = emit_mermaid(specs_for_repo, repo_contracts)
        # Mermaid Init mit themeVariables aus doc-profile.
        # Fix 2026-05-26: defaultRenderer:elk entfernt (ELK in Mermaid 10.9.1
        # opt-in Plugin, nicht überall geladen → Syntax Error). Dagre-Default
        # ist robuster. Plus: Click-Direktiven direkt nach Node-Defs, vor
        # classDef (Mermaid 10.x parst Reihenfolge strikt).
        # Font-Family entschärft (komplexe Quote-Stacks im JSON-Init können
        # Tokenizer verwirren).
        click_lines = []
        for kd_name, _p, _d in specs_for_repo:
            nid = node_id(kd_name)
            # Mermaid click-Syntax: click <nid> "<url>" "<tooltip>" _blank
            # Tooltip ohne deutsche Sonderzeichen halten — sicherer.
            click_lines.append(
                f'    click {nid} "./render/{repo_name}-{kd_name}.html" "Open mockup" _blank'
            )
        # Theme-Variables: Font-Family minimal halten (kein Quote-Mix)
        font_simple = '"sans-serif"' if "Georgia" not in style["font_h"] else '"Georgia, serif"'
        new_init = (
            '%%{init: {'
            '"theme":"base",'
            '"themeVariables":{'
            f'"primaryColor":"{style["accent_bg"]}",'
            '"primaryTextColor":"#1f2937",'
            f'"primaryBorderColor":"{style["accent"]}",'
            f'"lineColor":"{style["accent"]}",'
            '"secondaryColor":"#fef3c7",'
            '"tertiaryColor":"#f3f4f6",'
            f'"fontFamily":{font_simple}'
            '},'
            '"flowchart":{"curve":"basis"}'
            '}}%%'
        )
        # Click-Direktiven VOR classDef einfügen, damit Mermaid 10.9.1
        # die Knoten-Refs noch findet bevor Style-Block schliesst.
        mermaid_themed = mermaid.replace(
            '%%{init: {"flowchart": {"defaultRenderer": "elk"}} }%%',
            new_init,
        ).replace(
            "%% --- Styling ---",
            "%% --- Click-Direktiven (CD-Upgrade) ---\n" + "\n".join(click_lines) + "\n\n%% --- Styling ---",
        )

        html_out = build_html(mermaid_themed, specs_for_repo, repo_contracts)
        # Repo-spezifische Header-Beschriftung
        html_out = html_out.replace(
            "Klickdummy-Lineage · meiki-hub",
            f"Klickdummy-Lineage · {repo_name}",
        )

        # Quick-Stats für Header (KD-Count, Profile, Smoke-Status — wird beim Build berechnet)
        kd_count = len(specs_for_repo)
        kd_classes = sorted({(d.get("class") or "?") for _, _, d in specs_for_repo})
        stats_chip = (
            f'<span style="background:rgba(255,255,255,.15);padding:3px 10px;border-radius:4px;font-size:12px;">'
            f'{kd_count} KD · profile <code style="background:rgba(255,255,255,.2);padding:1px 5px;border-radius:3px;">{html.escape(profile)}</code>'
            f' · class {", ".join(html.escape(c) for c in kd_classes)}</span>'
        )

        # Cross-Genesor Nav-Banner direkt nach <body> mit Quick-Stats + Skin-Switcher
        accent_color = style["accent"]
        nav_banner = (
            f'<div style="background:{accent_color};color:#fff;padding:10px 18px;font-size:13px;'
            f'display:flex;gap:14px;align-items:center;flex-wrap:wrap;'
            f'font-family:{style["font_h"]};">'
            f'<a href="./index.html" style="color:#fff;text-decoration:none;font-weight:600;">🌱 Genesor</a>'
            f'<a href="./uc-{html.escape(repo_name)}.html" style="color:#fff;text-decoration:none;">'
            f'📋 Use Cases ({html.escape(repo_name)})</a>'
            f'<a href="./coverage.html" style="color:#fff;text-decoration:none;">'
            f'📊 Cross-Repo Coverage</a>'
            f'<span style="flex:1;"></span>'
            f'{stats_chip}'
            f'<select id="lineage-skin-select" '
            f'style="padding:4px 8px;border:1px solid rgba(255,255,255,.4);background:rgba(255,255,255,.1);color:#fff;border-radius:4px;font-size:12px;">'
            f'<option value="__default">🎨 Default</option>'
            f'<option value="__dark">Dark</option>'
            f'<option value="__print">Print (B/W)</option>'
            f'</select>'
            f'</div>'
            f'<script>'
            f'(function(){{'
            f'const K="lineage_skin";'
            f'function apply(v){{'
            f'document.body.classList.remove("skin-dark","skin-print");'
            f'if(v==="__dark")document.body.classList.add("skin-dark");'
            f'if(v==="__print")document.body.classList.add("skin-print");'
            f'try{{localStorage.setItem(K,v);}}catch(e){{}}'
            f'}}'
            f'let s="__default";try{{s=localStorage.getItem(K)||"__default";}}catch(e){{}}'
            f'const el=document.getElementById("lineage-skin-select");'
            f'if(el){{el.value=s;apply(s);el.addEventListener("change",e=>apply(e.target.value));}}'
            f'}})();'
            f'</script>'
            f'<style>'
            f'body.skin-dark{{background:#1f2937!important;color:#e5e7eb!important;}}'
            f'body.skin-dark .graph-wrap{{background:#111827!important;border-color:#374151!important;}}'
            f'body.skin-print *{{filter:grayscale(1);}}'
            f'</style>'
        )
        html_out = html_out.replace("<body>", "<body>" + nav_banner, 1)
        out_path = out_dir / f"lineage-{repo_name}.html"
        out_path.write_text(html_out, encoding="utf-8")
        written.append(out_path)
    return written


def _safe_mermaid_label(text: str, max_len: int = 50) -> str:
    """Mermaid-10.9.x-sicheres Label: kein Apostroph, kein /, kein Unicode-Ellipsis."""
    if not text:
        return ""
    text = (
        text.replace("'", "")     # Apostroph bricht Mermaid-Tokenizer
            .replace('"', "")     # Quote im Label = String-Terminator
            .replace("/", " - ")  # Slash konflikt mit Shape-Syntax
            .replace("…", "...")  # Unicode-Ellipsis → ASCII
            .replace("—", "-")    # em-dash safer
            .replace("(", " ")    # Klammern können in komplexen Edges stören
            .replace(")", "")
    )
    if len(text) > max_len:
        text = text[:max_len].rstrip() + "..."
    return text


def emit_screen_lineage(spec_data: dict) -> str:
    """Mermaid-Graph für Screen-Ablauf innerhalb eines KDs.

    Mermaid 10.9.6 ist strikt — kein %%{init:}%% (JS-initialize macht es),
    keine Kommentare mit Unicode (em-dash, ellipsis), keine Pipes | in Labels
    (= Edge-Label-Syntax-Konflikt). Plus: minimaler Subgraph ohne direction.
    """
    lines: list[str] = [
        "flowchart TD",
        "",
    ]
    screens = spec_data.get("screens") or []
    sid_set = {s.get("id") for s in screens if isinstance(s, dict) and s.get("id")}
    # Knoten emittieren
    halbschicht_groups: dict[str, list[str]] = {}
    ungrouped: list[str] = []
    for s in screens:
        if not isinstance(s, dict):
            continue
        sid = s.get("id")
        if not sid:
            continue
        nid = node_id(sid)
        title_short = _safe_mermaid_label(s.get("title") or sid, max_len=50)
        personas = s.get("persona") or []
        if isinstance(personas, str):
            personas = [personas]
        per = ", ".join(personas[:2]) or "-"
        # Label OHNE HTML, OHNE Pipe (Pipe = Mermaid-Edge-Label-Syntax → Konflikt
        # auch in quoted Labels in 10.9.6). Bullet als Separator.
        label = f"{sid} • {title_short} • {per}"
        halb = s.get("halbschicht") or ""
        node_line = f'    {nid}["{label}"]'
        if halb:
            halbschicht_groups.setdefault(str(halb), []).append((nid, node_line))
        else:
            ungrouped.append(node_line)

    # Halbschicht-Subgraphen (ohne `direction` — Mermaid 10.9.6 strikt)
    for halb, items in halbschicht_groups.items():
        safe_halb = _safe_mermaid_label(str(halb), max_len=40)
        lines.append(f'    subgraph hs_{node_id(halb)} ["{safe_halb}"]')
        for _nid, node_line in items:
            lines.append("    " + node_line)
        lines.append("    end")
        lines.append("")
    for node_line in ungrouped:
        lines.append(node_line)

    # Edges: next_screens (solid)
    lines.append("")
    for s in screens:
        if not isinstance(s, dict):
            continue
        sid = s.get("id")
        if not sid:
            continue
        next_list = s.get("next_screens") or []
        if isinstance(next_list, str):
            next_list = [next_list]
        for nsid in next_list:
            if nsid in sid_set:
                lines.append(f"    {node_id(sid)} --> {node_id(nsid)}")

    # Edges: voraussetzung_screen (dashed, vom Vorgänger her)
    lines.append("")
    for s in screens:
        if not isinstance(s, dict):
            continue
        sid = s.get("id")
        if not sid:
            continue
        vor = s.get("voraussetzung_screen")
        if vor and vor in sid_set:
            lines.append(f"    {node_id(vor)} -.-> {node_id(sid)}")

    # Edges: cross_klickdummy_link (dotted, cross-KD)
    lines.append("")
    for s in screens:
        if not isinstance(s, dict):
            continue
        sid = s.get("id")
        if not sid:
            continue
        ckl = s.get("cross_klickdummy_link")
        if not ckl:
            continue
        items = ckl if isinstance(ckl, list) else [ckl]
        for entry in items:
            if not isinstance(entry, dict):
                continue
            target = entry.get("target") or entry.get("screen") or ""
            kd = entry.get("kd") or entry.get("repo") or "cross-kd"
            if target:
                target_id = node_id(f"ext_{kd}_{target}")
                # Rechteck-Shape (statt Trapezoid mit /), Label safe
                ext_label = _safe_mermaid_label(f"ext: {kd} - {target}", max_len=60)
                lines.append(f'    {target_id}["{ext_label}"]')
                lines.append(f"    {node_id(sid)} -..-> {target_id}")

    # Styling (minimal, kein Kommentar)
    lines.append("")
    lines.append("    classDef screenNode fill:#fff,stroke:#888,color:#000")
    lines.append("    classDef extNode fill:#fce7f3,stroke:#9f1239,stroke-dasharray:5 5,color:#000")
    return "\n".join(lines)


def build_screen_lineage_html(repo: str, kd_name: str, spec_data: dict,
                             profile: str, style: dict) -> str:
    """Standalone HTML-Page mit eingebettetem Mermaid-Screen-Lineage."""
    from datetime import date
    mermaid_body = emit_screen_lineage(spec_data)
    screens = spec_data.get("screens") or []
    n_screens = len([s for s in screens if isinstance(s, dict) and s.get("id")])
    title = (spec_data.get("title") or kd_name).split("—")[0].strip()
    klass = spec_data.get("class") or "?"

    # KEIN %%{init:}%% — Mermaid 10.9.6 strikt; mermaid.initialize() in JS reicht.
    # themeVariables werden im Init-JS unten gesetzt.
    accent = style["accent"]
    accent_bg = style["accent_bg"]
    return f"""<!DOCTYPE html>
<html lang="de"><head><meta charset="utf-8">
<title>Screen-Lineage · {html.escape(kd_name)} · {html.escape(repo)}</title>
<style>
  body {{ font-family: -apple-system, "Segoe UI", system-ui, sans-serif; margin: 0; padding: 0; background: #f5f7fa; color: #1f2937; }}
  .topbar {{ background: {accent}; color: #fff; padding: 12px 20px; display: flex; gap: 14px; align-items: center; flex-wrap: wrap; }}
  .topbar h1 {{ margin: 0; font-size: 18px; font-weight: 600; flex: 1; min-width: 200px; }}
  .topbar a {{ color: #fff; text-decoration: none; font-size: 13px; }}
  .topbar a:hover {{ text-decoration: underline; }}
  .topbar .badge {{ background: rgba(255,255,255,.15); padding: 3px 10px; border-radius: 4px; font-size: 12px; }}
  main {{ padding: 20px; max-width: 1300px; margin: 0 auto; }}
  .graph-wrap {{ background: #fff; border: 1px solid #e3e8ee; border-radius: 6px; padding: 18px; overflow-x: auto; }}
  .legend {{ background: #fff; border: 1px solid #e3e8ee; border-radius: 6px; padding: 12px 16px; margin-top: 12px; font-size: 13px; color: #4b5563; }}
  .legend table {{ border-collapse: collapse; }}
  .legend td {{ padding: 3px 12px; }}
  .legend code {{ background: #f3f4f6; padding: 1px 5px; border-radius: 3px; font-size: 12px; }}
</style>
<script src="https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js"></script>
</head><body>
<header class="topbar">
  <h1>🕸 Screen-Lineage · {html.escape(kd_name)}</h1>
  <a href="./render/{html.escape(repo)}-{html.escape(kd_name)}.html">📱 Mockup</a>
  <a href="./uc-{html.escape(repo)}.html?kd={html.escape(kd_name)}">📋 UCs</a>
  <a href="./lineage-{html.escape(repo)}.html">🌳 Repo-Lineage</a>
  <a href="./index.html">🌱 Genesor</a>
  <span style="flex:1;"></span>
  <span class="badge">{n_screens} Screens · class {html.escape(klass)} · profile {html.escape(profile)}</span>
</header>
<main>
<div class="graph-wrap">
<pre class="mermaid">
{mermaid_body}
</pre>
</div>
<div class="legend">
  <b>Legende:</b>
  <table>
    <tr><td><b>──→ solid</b></td><td><code>next_screens</code> (Workflow-Folge-Screen)</td></tr>
    <tr><td><b>-.-→ dashed</b></td><td><code>voraussetzung_screen</code> (Pre-Condition)</td></tr>
    <tr><td><b>-..→ dotted</b></td><td><code>cross_klickdummy_link</code> (Sprung zu anderem KD)</td></tr>
    <tr><td><b>Subgraph-Box</b></td><td>Halbschicht-Gruppierung</td></tr>
  </table>
</div>
<p style="color:#9ca3af;font-size:11px;margin-top:14px;">
  Auto-generiert aus <code>{html.escape(repo)}/klickdummy/{html.escape(kd_name)}/screens-spec.yaml</code>. Build: {date.today().isoformat()}.
</p>
</main>
<script>
  mermaid.initialize({{
    startOnLoad: true,
    theme: 'base',
    themeVariables: {{
      primaryColor: '{accent_bg}',
      primaryTextColor: '#1f2937',
      primaryBorderColor: '{accent}',
      lineColor: '{accent}',
      secondaryColor: '#fef3c7',
      tertiaryColor: '#f3f4f6',
      fontFamily: 'sans-serif'
    }},
    flowchart: {{ curve: 'basis' }}
  }});
</script>
</body></html>
"""


def _git_repo_meta(repo: str) -> dict:
    """Liefert ``{org, gh_repo, branch, has_upstream, tracked_files: set[str]}``.

    **Wichtig:** ``branch`` ist der **aktuell ausgecheckte** Branch (nicht der
    Default-Branch), weil der Edit-Link auf die tatsächlich gepushte Stelle
    zeigen muss. Wenn das Repo auf feat/X arbeitet und UCs nur dort liegen,
    zeigt der Default-Branch (main) einen 404.

    ``has_upstream`` ist True wenn der aktuelle Branch einen tracked upstream
    hat — sonst gibt es nichts auf GitHub zu zeigen und Edit-Link entfällt.

    ``tracked_files`` = ``git ls-files`` (lokal tracked); kombiniert mit
    ``has_upstream`` ist das eine pragmatische Annäherung an "auf GitHub
    sichtbar". Echter Remote-Check wäre per-PR-aware aber zu teuer.
    """
    import subprocess
    repo_path = REPOS_ROOT / repo
    if not (repo_path / ".git").exists():
        return {}
    try:
        url = subprocess.check_output(
            ["git", "-C", str(repo_path), "remote", "get-url", "origin"],
            stderr=subprocess.DEVNULL, text=True, timeout=2,
        ).strip()
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError):
        return {}
    m = re.match(r"(?:git@github\.com:|https://github\.com/)([^/]+)/([^/.]+?)(?:\.git)?$", url)
    if not m:
        return {}
    org, gh_repo = m.group(1), m.group(2)
    # Aktuell ausgecheckter Branch (= dort liegen die committed/pushed UCs)
    try:
        branch = subprocess.check_output(
            ["git", "-C", str(repo_path), "rev-parse", "--abbrev-ref", "HEAD"],
            stderr=subprocess.DEVNULL, text=True, timeout=2,
        ).strip()
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError):
        branch = "main"
    if branch == "HEAD":  # detached HEAD
        branch = "main"
    # Has-Upstream-Check: prüft ob ``refs/remotes/origin/<branch>`` lokal
    # existiert (wird durch ``git push`` automatisch angelegt, auch ohne ``-u``).
    # Robuster als ``@{u}``, das die branch.<name>.remote-Config braucht.
    has_upstream = subprocess.run(
        ["git", "-C", str(repo_path), "rev-parse", "--verify",
         f"refs/remotes/origin/{branch}"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=2,
    ).returncode == 0
    try:
        tracked = set(subprocess.check_output(
            ["git", "-C", str(repo_path), "ls-files"],
            stderr=subprocess.DEVNULL, text=True, timeout=10,
        ).strip().splitlines())
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError):
        tracked = set()
    return {"org": org, "gh_repo": gh_repo, "branch": branch,
            "has_upstream": has_upstream, "tracked_files": tracked}


_REPO_META_CACHE: dict[str, dict] = {}


def _repo_meta_cached(repo: str) -> dict:
    if repo not in _REPO_META_CACHE:
        _REPO_META_CACHE[repo] = _git_repo_meta(repo)
    return _REPO_META_CACHE[repo]


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


def _github_edit_url(repo: str, rel_path: str) -> str | None:
    """Editor-Deeplink für aktuell ausgecheckten Branch.

    Tracking-File-Check (lokal getrackt) ist Pflicht; remote-Branch-Existenz
    wird NICHT geprüft (ref-Verify ist in manchen Setups falsch-negativ;
    Netzwerk-Call wäre teuer). Bei nicht-gepushtem Branch kommt 404 → User
    macht ``git push`` und der Link funktioniert.
    """
    meta = _repo_meta_cached(repo)
    if not meta or rel_path not in meta.get("tracked_files", set()):
        return None
    return f"https://github.com/{meta['org']}/{meta['gh_repo']}/edit/{meta['branch']}/{rel_path}"


def _github_delete_url(repo: str, rel_path: str) -> str | None:
    """Delete-Deeplink — siehe ``_github_edit_url`` für Branch-Auswahl."""
    meta = _repo_meta_cached(repo)
    if not meta or rel_path not in meta.get("tracked_files", set()):
        return None
    return f"https://github.com/{meta['org']}/{meta['gh_repo']}/delete/{meta['branch']}/{rel_path}"


def build_repo_uc_index_html(repo: str, ucs_for_repo: list[dict], coverage: dict,
                            kds: list[dict] | None = None,
                            validation: dict[str, list[dict]] | None = None) -> str:
    """Pro-Repo UC-Index — Tabelle aller UCs des Repos mit Persona/Status/Coverage.

    Workshop-Feedback 2026-05-26: UCs sollten auf Repo-Ebene erreichbar sein,
    nicht nur cross-repo in der Heatmap. Diese Page ist von Genesor-Übersicht
    UND lineage-<repo>.html aus verlinkt.
    """
    from datetime import date
    ucs_sorted = sorted(ucs_for_repo, key=lambda u: u["uc_id"])
    real_count = coverage["uc_realized_count"]
    unres = coverage["uc_unresolved"]

    # ADR-Ref → KD-Name Lookup (cross-repo), damit data-kds saubere KD-Namen
    # enthält und der ?kd=-Filter matched (Bugfix Workshop 2026-05-26).
    adr_to_kd: dict[tuple[str, str], str] = {}
    for k in (kds or []):
        if k.get("kind", "spec") != "spec":
            continue
        adr_local = (k.get("data", {}).get("adr", {}) or {}).get("local") or ""
        if ":" in adr_local:
            adr_local = adr_local.split(":", 1)[1]
        if adr_local:
            adr_to_kd[(k["repo"], adr_local)] = k["kd"]

    validation = validation or {}
    rows = []
    for uc in ucs_sorted:
        gid = f"{uc['repo']}:{uc['uc_id']}"
        r = real_count.get(gid, 0)
        u_refs = unres.get(gid, [])
        findings = validation.get(gid, [])
        n_err = sum(1 for f in findings if f["severity"] == "error")
        n_warn = sum(1 for f in findings if f["severity"] == "warning")
        if n_err:
            health_chip = f'<details class="hf hf-err"><summary>❌ {n_err}e{(" " + str(n_warn) + "w") if n_warn else ""}</summary><ul>' + "".join(
                f'<li><b>{html.escape(f["code"])}</b>: {html.escape(f["msg"])}</li>' for f in findings
            ) + '</ul></details>'
        elif n_warn:
            health_chip = f'<details class="hf hf-warn"><summary>⚠ {n_warn}w</summary><ul>' + "".join(
                f'<li><b>{html.escape(f["code"])}</b>: {html.escape(f["msg"])}</li>' for f in findings
            ) + '</ul></details>'
        else:
            health_chip = '<span class="hf hf-ok" title="Validator-Layer A: alle Checks grün">✓</span>'
        status_chip = ""
        s = (uc.get("status") or "draft").lower()
        if s == "approved":
            status_chip = '<span class="st st-approved">approved</span>'
        elif s == "reviewed":
            status_chip = '<span class="st st-reviewed">reviewed</span>'
        else:
            status_chip = '<span class="st st-draft">draft</span>'
        cov_chip = (
            f'<span class="cov-{("high" if r >= 3 else "mid" if r == 2 else "low" if r == 1 else "none")}">'
            f'{r} Screen(s)</span>'
        )
        sek = uc.get("sekundaer") or []
        sek_str = ", ".join(sek) if isinstance(sek, list) else str(sek)
        # Frontmatter-Details collapsible
        details_inner = (
            f'<dt>FV-Bezug</dt><dd>{html.escape(uc.get("fv_bezug") or "—")}</dd>'
            f'<dt>Prio</dt><dd>{html.escape(uc.get("prio") or "—")}</dd>'
            f'<dt>Sekundäre Akteure</dt><dd>{html.escape(sek_str or "—")}</dd>'
            f'<dt>realisiert von</dt><dd><code>{html.escape(uc.get("realisiert_von") or "—")}</code></dd>'
            f'<dt>related_screens</dt><dd>'
            + (", ".join(f'<code>{html.escape(str(s))}</code>' for s in (uc.get("related_screens") or [])) or "—")
            + '</dd>'
        )
        if u_refs:
            details_inner += (
                f'<dt style="color:#b91c1c;">⚠ unresolved</dt><dd style="color:#b91c1c;">'
                + ", ".join(f'<code>{html.escape(x)}</code>' for x in u_refs)
                + "</dd>"
            )
        try:
            rel_path = uc["source_file"].relative_to(REPOS_ROOT / repo)
            rel_path_str = str(rel_path)
            src_link = f'<a href="../{html.escape(repo)}/{html.escape(rel_path_str)}" target="_blank" class="src-link" title="Lokale MD-Datei">📄 source</a>'
            gh_edit = _github_edit_url(repo, rel_path_str)
            gh_delete = _github_delete_url(repo, rel_path_str)
            if gh_edit:
                edit_link = f'<a href="{html.escape(gh_edit)}" target="_blank" class="edit-link" title="In GitHub-Web-Editor öffnen">✏️ edit</a>'
                del_link = (
                    f'<a href="{html.escape(gh_delete)}" target="_blank" class="del-link" title="In GitHub löschen (Web-UI)">🗑️ delete</a>'
                    if gh_delete else ""
                )
                status_extra = '<span class="rem-ok" title="Datei ist in main getrackt">●&nbsp;remote</span>'
            else:
                edit_link = ""
                del_link = ""
                status_extra = '<span class="rem-local" title="Datei existiert nur lokal — erst commit+push für Edit-Link auf GitHub">⚠ lokal-only</span>'
        except (ValueError, KeyError):
            src_link = ""
            edit_link = ""
            del_link = ""
            status_extra = ""
        rows.append(
            f'<tr data-kds="{html.escape(",".join(_uc_kd_targets(uc, repo, adr_to_kd)))}">'
            f'<td><code>{html.escape(gid)}</code></td>'
            f'<td>{html.escape(uc["name"])}</td>'
            f'<td>{html.escape(str(uc.get("akteur") or "—"))}</td>'
            f'<td>{health_chip}</td>'
            f'<td>{status_chip} {status_extra}</td>'
            f'<td>{cov_chip}</td>'
            f'<td><details><summary>Details</summary><dl>{details_inner}</dl></details> {src_link} {edit_link} {del_link}</td>'
            f'</tr>'
        )

    n_realized = sum(1 for u in ucs_sorted if real_count.get(f"{u['repo']}:{u['uc_id']}", 0) > 0)

    return f"""<!DOCTYPE html>
<html lang="de"><head><meta charset="utf-8">
<title>UC-Index · {html.escape(repo)} · Genesor</title>
<style>
  body {{ font-family: -apple-system, "Segoe UI", system-ui, sans-serif; margin: 0; padding: 20px; background: #f5f7fa; color: #1f2937; }}
  h1 {{ font-size: 20px; margin: 0 0 4px; }}
  .sub {{ font-size: 13px; color: #6b7280; margin-bottom: 14px; }}
  .sub a {{ color: #2563eb; text-decoration: none; }}
  .sub a:hover {{ text-decoration: underline; }}
  .badges span {{ display: inline-block; background: #eef2ff; color: #1e3a8a; padding: 3px 10px; border-radius: 4px; margin-right: 6px; font-size: 12px; }}
  table {{ width: 100%; border-collapse: collapse; background: #fff; font-size: 13px; border: 1px solid #e3e8ee; border-radius: 6px; overflow: hidden; }}
  th, td {{ border-bottom: 1px solid #e3e8ee; padding: 8px 10px; text-align: left; vertical-align: top; }}
  th {{ background: #f0f4f8; font-weight: 600; }}
  td code {{ background: #eef2ff; padding: 1px 5px; border-radius: 3px; font-size: 12px; }}
  .st {{ display: inline-block; padding: 1px 7px; border-radius: 3px; font-size: 11px; font-weight: 600; }}
  .st-draft    {{ background: #fef3c7; color: #92400e; }}
  .st-reviewed {{ background: #dbeafe; color: #1e40af; }}
  .st-approved {{ background: #d1fae5; color: #065f46; }}
  .cov-none {{ color: #9ca3af; }}
  .cov-low  {{ color: #92400e; font-weight: 600; }}
  .cov-mid  {{ color: #065f46; font-weight: 600; }}
  .cov-high {{ color: #064e3b; font-weight: 700; }}
  details {{ font-size: 12px; }}
  details summary {{ cursor: pointer; color: #2563eb; }}
  details dl {{ margin: 6px 0 0; padding-left: 6px; }}
  details dt {{ font-weight: 600; color: #374151; margin-top: 4px; font-size: 11px; }}
  details dd {{ margin: 1px 0 0 14px; color: #6b7280; font-size: 12px; }}
  .src-link {{ font-size: 11px; color: #6b7280; margin-left: 8px; text-decoration: none; }}
  .src-link:hover {{ text-decoration: underline; }}
  .edit-link {{ font-size: 11px; color: #2563eb; margin-left: 6px; text-decoration: none; background: #eef6ff; padding: 2px 6px; border-radius: 3px; }}
  .edit-link:hover {{ background: #dbeafe; }}
  .del-link {{ font-size: 11px; color: #b91c1c; margin-left: 4px; text-decoration: none; background: #fef2f2; padding: 2px 6px; border-radius: 3px; }}
  .del-link:hover {{ background: #fee2e2; }}
  .rem-ok {{ font-size: 10px; color: #16a34a; margin-left: 4px; }}
  .rem-local {{ font-size: 10px; color: #c2410c; margin-left: 4px; background: #fff7ed; padding: 1px 5px; border-radius: 3px; }}
  .hf {{ font-size: 11px; font-weight: 600; }}
  .hf-ok {{ color: #16a34a; }}
  .hf-warn summary {{ color: #92400e; cursor: pointer; }}
  .hf-err summary {{ color: #b91c1c; cursor: pointer; }}
  .hf ul {{ margin: 4px 0 0; padding-left: 18px; font-size: 11px; font-weight: normal; color: #374151; }}
  .hf li {{ margin-bottom: 2px; }}
</style></head><body>
<h1>📋 Use Cases · {html.escape(repo)}</h1>
<div class="sub">
  <a href="./index.html">← Genesor-Übersicht</a> ·
  <a href="./coverage.html">📊 Cross-Repo Coverage</a> ·
  <a href="./lineage-{html.escape(repo)}.html">🌳 Lineage</a>
</div>
<div class="badges" style="margin-bottom:14px;">
  <span>UCs in {html.escape(repo)}: {len(ucs_sorted)}</span>
  <span>mit Realisierung: {n_realized}/{len(ucs_sorted)}</span>
  <span>Konvention: ADR-211 Rev 16 §UC-Coverage</span>
</div>
<table>
  <thead><tr>
    <th>UC-ID</th><th>Name</th><th>Akteur</th><th title="Validator-Layer A: YAML, Pflichtfelder, Refs, Persona">Health</th><th>Status</th><th>Coverage</th><th>Details</th>
  </tr></thead>
  <tbody>{"".join(rows) or '<tr><td colspan="6" style="text-align:center;color:#9ca3af;padding:24px;">Noch keine UCs in diesem Repo. Generator: <code>python3 scripts/klickdummy_lineage.py --gen-uc-skeletons</code></td></tr>'}</tbody>
</table>
<p style="color:#9ca3af;font-size:11px;margin-top:14px;">
  UCs liegen unter <code>docs/use-cases/</code>. Frontmatter: <code>uc_id, name, primaer_akteur, related_screens</code> (ADR-211 Rev 16). Build: {date.today().isoformat()}
</p>
<script>
  // ?kd=<kd-name> Filter (Workshop 2026-05-26 #2)
  (function() {{
    const params = new URLSearchParams(location.search);
    const kd = params.get('kd');
    if (!kd) return;
    const rows = document.querySelectorAll('tbody tr');
    let hidden = 0, shown = 0;
    rows.forEach(tr => {{
      const targets = (tr.dataset.kds || '').split(',');
      // Matche auch ADR-Refs heuristisch — KD-Name passt zu KD oder Spec-ID
      const matches = targets.some(t => t === kd || t.endsWith('-' + kd) || t.startsWith(kd));
      if (matches) {{ shown++; }} else {{ tr.style.display = 'none'; hidden++; }}
    }});
    // Filter-Banner einblenden
    const banner = document.createElement('div');
    banner.style.cssText = 'background:#1e3a8a;color:#fff;padding:8px 14px;border-radius:4px;margin-bottom:12px;font-size:13px;display:flex;gap:14px;align-items:center;';
    banner.innerHTML = `<span>🔍 Filter: nur UCs für KD <code style="background:rgba(255,255,255,.2);padding:1px 6px;border-radius:3px;">${{kd}}</code> (${{shown}} sichtbar, ${{hidden}} ausgeblendet)</span><a href="?" style="color:#fff;text-decoration:underline;">× Filter entfernen</a>`;
    document.querySelector('h1').after(banner);
  }})();
</script>
</body></html>
"""


def build_coverage_html(ucs: list[dict], kds: list[dict], coverage: dict) -> str:
    """Cross-Repo UC × KD Coverage-Heatmap. ADR-211 Rev 15 §UC-Coverage.

    Zellen: Anzahl realized Screens pro (UC, KD). Klick auf Zelle zeigt die
    konkreten Screen-IDs. Footer listet UCs ohne Realisierung + unresolved Refs.
    """
    # KDs sortieren: nur spec-KDs, gruppiert nach repo
    spec_kds = sorted(
        [k for k in kds if k.get("kind", "spec") == "spec"],
        key=lambda k: (k["repo"], k["kd"]),
    )
    # UCs sortieren nach repo+uc_id
    ucs_sorted = sorted(ucs, key=lambda u: (u["repo"], u["uc_id"]))

    matrix = coverage["matrix"]
    uc_real_count = coverage["uc_realized_count"]
    uc_unresolved = coverage["uc_unresolved"]

    # Spalten-Header pro Repo gruppieren
    cols_by_repo: dict[str, list[dict]] = {}
    for k in spec_kds:
        cols_by_repo.setdefault(k["repo"], []).append(k)

    # Header-Rows (2 Reihen: repo, kd)
    repo_th = ['<th rowspan="2" class="uc-th">UC-ID</th>',
               '<th rowspan="2" class="uc-th">Name</th>',
               '<th rowspan="2" class="uc-th">Akteur</th>']
    for repo, kds_list in cols_by_repo.items():
        repo_th.append(f'<th colspan="{len(kds_list)}" class="repo-th">{html.escape(repo)}</th>')
    kd_th = []
    for repo, kds_list in cols_by_repo.items():
        for k in kds_list:
            kd_th.append(f'<th class="kd-th" title="{html.escape(k["kd"])}">{html.escape(k["kd"][:14])}</th>')

    # Body-Rows
    body_rows = []
    for uc in ucs_sorted:
        uc_gid = f"{uc['repo']}:{uc['uc_id']}"
        cells = [
            f'<td class="uc-id"><code>{html.escape(uc_gid)}</code></td>',
            f'<td class="uc-name">{html.escape(uc["name"][:60])}</td>',
            f'<td class="uc-akteur">{html.escape(str(uc["akteur"]))}</td>',
        ]
        for repo, kds_list in cols_by_repo.items():
            for k in kds_list:
                screens = matrix.get((uc_gid, k["repo"], k["kd"]), [])
                if not screens:
                    cells.append('<td class="cell cell-empty">·</td>')
                else:
                    n = len(screens)
                    cls = "cell-low" if n == 1 else ("cell-mid" if n == 2 else "cell-high")
                    sids = ", ".join(screens)
                    cells.append(
                        f'<td class="cell {cls}" title="Screens: {html.escape(sids)}">{n}</td>'
                    )
        body_rows.append(f'<tr>{"".join(cells)}</tr>')

    # Footer-Listen
    no_realized = [f"{uc['repo']}:{uc['uc_id']} — {uc['name']}"
                   for uc in ucs_sorted if uc_real_count.get(f"{uc['repo']}:{uc['uc_id']}", 0) == 0]
    unres_lines = []
    for gid, refs in sorted(uc_unresolved.items()):
        unres_lines.append(f"<li><code>{html.escape(gid)}</code>: {html.escape(', '.join(refs[:3]))}</li>")

    n_realized = sum(1 for v in uc_real_count.values() if v > 0)
    n_cells = sum(len(v) for v in matrix.values())

    from datetime import date
    return f"""<!DOCTYPE html>
<html lang="de"><head><meta charset="utf-8">
<title>UC ↔ KD Coverage · Genesor</title>
<style>
  body {{ font-family: -apple-system, "Segoe UI", system-ui, sans-serif; margin: 0; padding: 20px; background: #f5f7fa; color: #1f2937; }}
  h1 {{ font-size: 20px; margin: 0 0 6px; }}
  .meta {{ font-size: 13px; color: #6b7280; margin-bottom: 16px; }}
  .nav a {{ font-size: 13px; color: #2563eb; text-decoration: none; }}
  .nav a:hover {{ text-decoration: underline; }}
  table {{ border-collapse: collapse; background: #fff; font-size: 12px; }}
  th, td {{ border: 1px solid #e3e8ee; padding: 5px 8px; text-align: left; }}
  th.uc-th {{ background: #f3f4f6; position: sticky; top: 0; z-index: 2; vertical-align: bottom; }}
  th.repo-th {{ background: #1e3a8a; color: #fff; text-align: center; font-size: 13px; }}
  th.kd-th {{ background: #e0e7ff; color: #1e3a8a; writing-mode: vertical-rl; transform: rotate(180deg); height: 100px; padding: 4px; font-size: 11px; }}
  td.uc-id code {{ background: #eef2ff; padding: 1px 4px; border-radius: 3px; }}
  td.uc-name {{ max-width: 280px; }}
  td.cell {{ text-align: center; font-weight: 600; width: 32px; cursor: help; }}
  .cell-empty {{ color: #d1d5db; }}
  .cell-low {{ background: #fef3c7; color: #92400e; }}
  .cell-mid {{ background: #d1fae5; color: #065f46; }}
  .cell-high {{ background: #6ee7b7; color: #064e3b; }}
  .badges span {{ display: inline-block; background: #eef2ff; color: #1e3a8a; padding: 3px 10px; border-radius: 4px; margin-right: 6px; font-size: 12px; }}
  .footer {{ margin-top: 20px; font-size: 12px; color: #6b7280; }}
  .footer h3 {{ font-size: 13px; color: #374151; margin: 12px 0 4px; }}
  .footer ul {{ margin: 0; padding-left: 18px; }}
  .info-banner {{ background: #eef6ff; border-left: 4px solid #2563eb; padding: 12px 14px; margin-bottom: 14px; border-radius: 4px; font-size: 13px; line-height: 1.5; }}
  .info-banner h3 {{ margin: 0 0 6px; font-size: 14px; color: #1e3a8a; }}
  .info-banner p {{ margin: 4px 0; }}
  .legend {{ display: inline-block; padding: 1px 7px; border-radius: 3px; font-weight: 600; font-size: 11px; margin: 0 4px; }}
  .legend.l-empty {{ background: #f3f4f6; color: #9ca3af; }}
  .legend.l-low {{ background: #fef3c7; color: #92400e; }}
  .legend.l-mid {{ background: #d1fae5; color: #065f46; }}
  .legend.l-high {{ background: #6ee7b7; color: #064e3b; }}
  details {{ margin-top: 14px; background: #fff; border: 1px solid #e3e8ee; border-radius: 4px; padding: 8px 12px; }}
  details summary {{ cursor: pointer; font-weight: 600; color: #2563eb; font-size: 13px; }}
  details[open] summary {{ margin-bottom: 8px; }}
  details dl {{ margin: 0; font-size: 12px; }}
  details dt {{ font-weight: 600; color: #374151; margin-top: 8px; }}
  details dd {{ margin: 2px 0 0 16px; color: #6b7280; }}
  details code {{ background: #f3f4f6; padding: 1px 4px; border-radius: 3px; font-size: 11px; }}
</style></head><body>
<h1>UC ↔ KD Coverage</h1>
<div class="info-banner">
  <h3>ℹ Was zeigt diese Heatmap?</h3>
  <p>Pro Zelle: <b>wie viele Screens</b> eines Klickdummies (Spalte) durch einen Use Case
     (Zeile) realisiert sind — aus <code>UC.related_screens</code> aufgelöst.</p>
  <p>Farbskala:
    <span class="legend l-empty">·</span> keine Zuordnung &nbsp;·&nbsp;
    <span class="legend l-low">1</span> ein Screen &nbsp;·&nbsp;
    <span class="legend l-mid">2</span> zwei Screens &nbsp;·&nbsp;
    <span class="legend l-high">3+</span> drei oder mehr Screens
  </p>
  <p style="color:#6b7280;font-size:12px;margin-top:6px;">
    Mouse-Over einer Zelle zeigt die konkreten Screen-IDs.
    UCs ohne Realisierung + nicht-auflösbare Refs siehe Footer.
  </p>
</div>
<details>
  <summary>📖 Glossar &amp; Konventionen (ADR-211 Rev 16 §UC-Coverage)</summary>
  <dl>
    <dt>Use Case (UC)</dt>
    <dd>Maschinen-lesbares Anforderungs-Artefakt im Repo, gespeichert als Markdown mit YAML-Frontmatter unter <code>docs/use-cases/</code>. Cross-Repo-Namespace: <code>&lt;repo&gt;:UC-NNN</code>.</dd>
    <dt>Klickdummy (KD)</dt>
    <dd>Renderer einer Klickdummy-Spec; aus <code>screens-spec.yaml</code> generiert. ADR-211.</dd>
    <dt>related_screens (UC-Feld)</dt>
    <dd>Liste von Refs im Format <code>&lt;prefix&gt;:ADR-NNN#screen-id</code> oder <code>&lt;prefix&gt;:&lt;spec-id&gt;#screen-id</code>. Wird bidirektional gegen Klickdummy-Specs gelintet.</dd>
    <dt>realisiert (Cell-Wert)</dt>
    <dd>Anzahl Screens des KDs, auf die der UC via <code>related_screens</code> verweist UND die im Klickdummy-Spec existieren.</dd>
    <dt>Unresolved Ref</dt>
    <dd>Eine <code>related_screens</code>-Ref zeigt auf einen Screen, der im Spec nicht (mehr) existiert — siehe Footer.</dd>
  </dl>
</details>
<div class="meta">
  <div class="nav"><a href="./index.html">← Genesor-Übersicht</a></div>
  <div class="badges" style="margin-top:8px;">
    <span>UCs: {len(ucs_sorted)}</span>
    <span>KDs: {len(spec_kds)}</span>
    <span>realisiert: {n_realized}/{len(ucs_sorted)}</span>
    <span>UC×Screen-Coverage-Zellen: {n_cells}</span>
  </div>
</div>
<table>
  <thead><tr>{"".join(repo_th)}</tr><tr>{"".join(kd_th)}</tr></thead>
  <tbody>{"".join(body_rows)}</tbody>
</table>
<div class="footer">
  <h3>UCs ohne Realisierung ({len(no_realized)})</h3>
  <ul>{"".join(f"<li>{html.escape(n)}</li>" for n in no_realized) or "<li>—</li>"}</ul>
  <h3>UCs mit nicht-auflösbaren Refs ({len(uc_unresolved)})</h3>
  <ul>{"".join(unres_lines) or "<li>—</li>"}</ul>
  <p style="margin-top:14px;">Coverage gemäß ADR-211 Rev 15 §UC-Coverage. Refs-Format: <code>&lt;prefix&gt;:ADR-NNN#screen-id</code>. Build: {date.today().isoformat()}</p>
</div>
</body></html>
"""


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
                seen_gids[gid] = str(uc["source_file"].relative_to(REPOS_ROOT))
            except (ValueError, KeyError):
                seen_gids[gid] = str(uc.get("source_file", "?"))

        if findings:
            out[gid] = findings
    return out


def _inspect_django_models(repo: str) -> dict[str, dict]:
    """AST-Parse aller `apps/*/models.py` → ``{app_label.ModelName: {fields, file}}``.

    Liefert pro Model die Field-Definitionen mit Type-Name und kwargs (best-effort).
    Lesson learned Iter-1: ohne diesen Schritt rät der Brief Model-Namen und
    User-Owner-Pattern, was zu Refactor-Aufwand führt.
    """
    import ast
    result: dict[str, dict] = {}
    repo_path = REPOS_ROOT / repo
    apps_dir = repo_path / "apps"
    if not apps_dir.is_dir():
        return result
    for models_py in apps_dir.glob("*/models.py"):
        app_label = models_py.parent.name
        try:
            tree = ast.parse(models_py.read_text("utf-8"))
        except (SyntaxError, OSError):
            continue
        for node in ast.walk(tree):
            if not isinstance(node, ast.ClassDef):
                continue
            # Nur Models, die models.Model erben (best-effort heuristisch)
            is_model = any(
                (isinstance(b, ast.Attribute) and b.attr == "Model")
                or (isinstance(b, ast.Name) and b.id == "Model")
                for b in node.bases
            )
            if not is_model:
                continue
            fields: dict[str, dict] = {}
            for stmt in node.body:
                if not isinstance(stmt, ast.Assign):
                    continue
                if len(stmt.targets) != 1 or not isinstance(stmt.targets[0], ast.Name):
                    continue
                fname = stmt.targets[0].id
                if not isinstance(stmt.value, ast.Call):
                    continue
                # Field-Type-Name extrahieren (z. B. CharField, ForeignKey)
                ftype = None
                fn = stmt.value.func
                if isinstance(fn, ast.Attribute):
                    ftype = fn.attr
                elif isinstance(fn, ast.Name):
                    ftype = fn.id
                if not ftype:
                    continue
                # kwargs flachpressen (best-effort, ohne komplexe AST-Eval)
                kwargs = {}
                for kw in stmt.value.keywords:
                    if kw.arg:
                        try:
                            kwargs[kw.arg] = ast.unparse(kw.value)
                        except Exception:
                            kwargs[kw.arg] = "?"
                # Positional args (z. B. FK("auth.User"))
                args_pos = []
                for arg in stmt.value.args:
                    try:
                        args_pos.append(ast.unparse(arg))
                    except Exception:
                        args_pos.append("?")
                fields[fname] = {"type": ftype, "args": args_pos, "kwargs": kwargs}
            key = f"{app_label}.{node.name}"
            result[key] = {
                "app_label": app_label,
                "model_name": node.name,
                "fields": fields,
                "source_path": str(models_py.relative_to(repo_path)),
            }
    return result


def _detect_tenant_pattern(models_inspected: dict[str, dict]) -> dict:
    """Erkennt ADR-072 Multi-Tenant-Pattern (≥3 Models mit ``tenant_id``)."""
    with_tenant = [k for k, v in models_inspected.items() if "tenant_id" in v.get("fields", {})]
    return {
        "active": len(with_tenant) >= 3,
        "count": len(with_tenant),
        "models": with_tenant[:10],
        "rationale": (
            "ADR-072 Multi-Tenant via BigIntegerField (kein FK). Neue Models in diesem Repo "
            "sollten `tenant_id`-Field + Index ergänzen; Views filtern via "
            "`core.TenantUser.objects.filter(tenant_id=..., user=request.user, is_active=True)`."
        ) if len(with_tenant) >= 3 else "",
    }


def _detect_auth_user_model(repo: str) -> str:
    """Liest ``AUTH_USER_MODEL`` aus ``config/settings/base.py`` (oder Fallback)."""
    import re
    repo_path = REPOS_ROOT / repo
    candidates = [
        repo_path / "config" / "settings" / "base.py",
        repo_path / "config" / "settings.py",
        repo_path / "settings.py",
    ]
    for p in candidates:
        if not p.is_file():
            continue
        try:
            text = p.read_text("utf-8")
        except OSError:
            continue
        m = re.search(r'AUTH_USER_MODEL\s*=\s*["\']([^"\']+)["\']', text)
        if m:
            return m.group(1)
    return "auth.User"   # Django-Default


def _inspect_dev_run(repo: str) -> dict:
    """Pilot-Lesson-Learned #6 — extrahiert dev_run-Hinweise aus dem Repo.

    Sucht ``bin/start-dev.sh``, ``docker-compose*.yml``, ``requirements.txt``,
    ``pyproject.toml`` und gibt Port, Command, DB-Port, Deps-Drift zurück.
    Leere/teilweise Ergebnisse sind erlaubt — Brief zeigt nur was tatsächlich
    gefunden wurde.
    """
    import re
    repo_path = REPOS_ROOT / repo
    out: dict = {"repo_path": f"~/github/{repo}"}

    # start-dev.sh
    start_sh = repo_path / "bin" / "start-dev.sh"
    if start_sh.is_file():
        try:
            text = start_sh.read_text("utf-8")
        except OSError:
            text = ""
        out["start_command"] = "bin/start-dev.sh"
        # DEFAULT_PORT=8092 oder runserver 0.0.0.0:8092
        m = re.search(r"DEFAULT_PORT\s*=\s*(\d+)", text)
        if not m:
            m = re.search(r"runserver\s+0\.0\.0\.0:(\d+)", text)
        if m:
            out["http_port"] = int(m.group(1))
        # PID/LOG-Files
        m = re.search(r'LOG_FILE\s*=\s*"([^"]+)"', text)
        if m:
            out["log_file"] = m.group(1)
        m = re.search(r'PID_FILE\s*=\s*"([^"]+)"', text)
        if m:
            out["pid_file"] = m.group(1)
        # Stop-Script
        if (repo_path / "bin" / "stop-dev.sh").is_file():
            out["stop_command"] = "bin/stop-dev.sh"

    # docker-compose Mappings für 5432 (Postgres)
    for compose_name in ("docker-compose.dev.yml", "docker-compose.yml"):
        p = repo_path / compose_name
        if not p.is_file():
            continue
        try:
            text = p.read_text("utf-8")
        except OSError:
            continue
        m = re.search(r'"?(?:127\.0\.0\.1:)?(\d+):5432"?', text)
        if m:
            out["db_port"] = int(m.group(1))
        m = re.search(r'"?(?:127\.0\.0\.1:)?(\d+):6379"?', text)
        if m:
            out["redis_port"] = int(m.group(1))
        out["compose_file"] = compose_name
        break

    # Requirements-Drift: pyproject.toml-Deps vs requirements.txt
    pyproject = repo_path / "pyproject.toml"
    req_txt = repo_path / "requirements.txt"
    drift_warning = None
    if pyproject.is_file() and req_txt.is_file():
        try:
            pp_text = pyproject.read_text("utf-8")
            req_text = req_txt.read_text("utf-8")
        except OSError:
            pp_text = req_text = ""
        # Sehr einfache Heuristik: Package-Namen aus [tool.poetry.dependencies]-Section
        m = re.search(r'\[tool\.poetry\.dependencies\](.+?)(?:\n\[|\Z)', pp_text, re.S)
        if m:
            pp_deps = set()
            for line in m.group(1).splitlines():
                ln = line.strip()
                if not ln or ln.startswith("#") or ln.startswith("python"):
                    continue
                mm = re.match(r'([A-Za-z0-9_\-]+)\s*=', ln)
                if mm:
                    pp_deps.add(mm.group(1).lower().replace("_", "-"))
            req_deps = set()
            for line in req_text.splitlines():
                ln = line.strip()
                if not ln or ln.startswith("#"):
                    continue
                mm = re.match(r'([A-Za-z0-9_\-]+)', ln)
                if mm:
                    req_deps.add(mm.group(1).lower().replace("_", "-"))
            missing = pp_deps - req_deps
            # IIL-internal git-deps ignorieren
            missing = {d for d in missing if not d.startswith("iil-")}
            if missing:
                drift_warning = sorted(missing)
    if drift_warning:
        out["requirements_drift"] = drift_warning

    # requirements.txt install-Hint
    if req_txt.is_file():
        out["requirements_install"] = (
            "pip3 install --user --break-system-packages -r requirements.txt"
        )

    # Test-URLs ableiten — wenn http_port bekannt
    port = out.get("http_port")
    if port:
        # versuchen healthz-URL aus Spec-screen abzuleiten — Caller setzt das ggf. nach
        out["bind"] = "0.0.0.0"
        out["test_url"] = f"http://localhost:{port}/healthz/  # ggf. <app-mount>/healthz/"
        out["public_test_url"] = (
            f"http://88.99.38.75:{port}/healthz/  # ggf. <app-mount>/healthz/"
        )

    return out


def _inspect_infra_context(workspace_root: str = "~/github") -> dict:
    """Pilot-Lesson-Learned #7 + #8 — parsed INFRASTRUCTURE.md.

    Liefert: server_name/public_ipv4, port_neighbors (aus Service-Tabelle),
    cloud_firewall (ID + default_open_ports), live_listening_ports.
    Bei fehlender Datei: nur live_listening_ports aus ``ss``-Snapshot.
    """
    from pathlib import Path
    import re
    import subprocess

    out: dict = {"infra_doc": f"{workspace_root}/INFRASTRUCTURE.md"}
    infra = Path(workspace_root.replace("~", str(Path.home()))) / "INFRASTRUCTURE.md"
    if infra.is_file():
        try:
            text = infra.read_text("utf-8")
        except OSError:
            text = ""
        # Public-IP + Server-Name
        m = re.search(r'\*\*Public IPv4:\*\*\s*`([\d.]+)`', text)
        if m:
            out["server_public_ipv4"] = m.group(1)
        m = re.search(r'\*\*Server:\*\*\s*`?([\w\-]+)`?', text)
        if m:
            out["server_name"] = m.group(1)
        # Cloud-Provider
        m = re.search(r'\((Hetzner|AWS|GCP|Azure)[^)]*\)', text, re.I)
        if m:
            out["cloud_provider"] = m.group(1).lower() + "-cloud"
        # Cloud-Firewall-Block
        m = re.search(r'firewall[-_]?\d+\s*\(id=(\d+)\)', text)
        if m:
            out["cloud_firewall_id"] = int(m.group(1))
            out["cloud_firewall_name"] = "firewall-1"
        m = re.search(r'erlauben nur\s+\*\*([\d,\s\-+]+)', text)
        if m:
            ports = re.findall(r'\d+', m.group(1))
            out["cloud_firewall_default_open"] = [int(p) for p in ports]
        # Port-Tabelle parsen — Markdown-Zeilen mit | Port | Bind | Service | ...
        neighbors = []
        for line in text.splitlines():
            if "|" not in line or "---" in line or "Bind" in line:
                continue
            cells = [c.strip().strip("*` ") for c in line.split("|")]
            if len(cells) < 5:
                continue
            port_cell = cells[1] if len(cells) > 1 else ""
            if not port_cell.isdigit():
                continue
            port = int(port_cell)
            svc_cell = cells[3] if len(cells) > 3 else ""
            if svc_cell:
                neighbors.append({"port": port, "app": svc_cell})
        if neighbors:
            out["port_neighbors"] = neighbors[:20]

    # Live-Listening-Snapshot
    try:
        ss_out = subprocess.run(
            ["ss", "-tln"], capture_output=True, text=True, timeout=5
        )
        live = []
        for line in ss_out.stdout.splitlines():
            m = re.search(r'(\d+\.\d+\.\d+\.\d+):(80\d{2}|87\d{2}|85\d{2}|81\d{2})\s', line)
            if m:
                bind = m.group(1)
                p = int(m.group(2))
                live.append({"port": p, "bind": bind})
        if live:
            # Dedupe nach (bind, port)
            seen = set()
            out["live_listening_ports"] = [
                x for x in live if (x["bind"], x["port"]) not in seen
                and not seen.add((x["bind"], x["port"]))
            ][:25]
    except (OSError, subprocess.TimeoutExpired):
        pass
    return out


def build_impl_brief(record: dict, screen_id: str) -> str | None:
    """Implementation-Brief für 1 Screen — LLM-Prompt-tauglich.

    Pilot ADR-211 Rev 17 §Implementation-Bridge (Variante 3, lokaler Pilot
    aus ausschreibungs-hub:docs/analysen/implementation-brief-konzept.md).

    Input: KD-Record + screen-id. Output: strukturiertes Markdown mit allen
    Bausteinen für End-to-End-Generierung (Klickdummy-Kontext, Datenmodell
    typisiert, API-Vertrag, User-Flow, Given/When/Then-Tests, Errors, NFRs,
    UI-Schema, Audit-Log, Existing-Models-Bezug, Tech-Stack).

    Returns None wenn der Screen kein implementation_brief-Block hat.
    """
    import yaml as _yaml
    from datetime import date
    repo = record["repo"]
    kd_name = record["kd"]
    d = record.get("data") or {}
    screens = d.get("screens") or []
    screen = next((s for s in screens if isinstance(s, dict) and s.get("id") == screen_id), None)
    if not screen:
        return None
    brief = screen.get("implementation_brief")
    if not brief:
        return None

    title = screen.get("title", screen_id)
    personas = screen.get("persona") or []
    if isinstance(personas, str):
        personas = [personas]
    halbschicht = screen.get("halbschicht") or "?"
    fokus = screen.get("fokus") or []
    konsumiert = screen.get("konsumiert_entities") or []
    next_screens = screen.get("next_screens") or []
    voraussetzung = screen.get("voraussetzung_screen") or "—"

    # Entity-Definitions für konsumierte Entities (typisiert wenn vorhanden)
    entities_local = (d.get("local_entities") or {})
    entities_root = (d.get("root_entities") or {})
    entities_all = {**entities_root, **entities_local}

    def _entity_block(ename: str) -> str:
        edef = entities_all.get(ename)
        if not isinstance(edef, dict):
            return f"### {ename}\n\n*Entity nicht im Spec deklariert.*\n"
        desc = edef.get("description", "")
        typed = edef.get("fields_typed")
        treat = edef.get("consumers_must_treat_as", "—")
        out = [f"### {ename}\n", f"**Description:** {desc}", f"**Consumer-Vertrag:** `{treat}`\n"]
        if typed and isinstance(typed, dict):
            out.append("**Django-Field-Types:**\n```yaml")
            out.append(_yaml.dump({ename: typed}, default_flow_style=False, sort_keys=False, allow_unicode=True).rstrip())
            out.append("```")
        else:
            fields = edef.get("fields") or []
            out.append("**Felder (untyped — `fields_typed` fehlt im Spec):**")
            for f in fields:
                if isinstance(f, str):
                    out.append(f"- `{f}`")
                elif isinstance(f, dict):
                    out.append(f"- `{f.get('name', '?')}`: {f}")
        return "\n".join(out) + "\n"

    # API-Block formatieren
    api_block_yaml = _yaml.dump({"api": brief.get("api", {})}, default_flow_style=False, sort_keys=False, allow_unicode=True).rstrip()
    tests_block_yaml = _yaml.dump({"tests": brief.get("tests", [])}, default_flow_style=False, sort_keys=False, allow_unicode=True).rstrip()
    nfrs_block_yaml = _yaml.dump({"nfrs": brief.get("nfrs", {})}, default_flow_style=False, sort_keys=False, allow_unicode=True).rstrip()
    ui_block_yaml = _yaml.dump({"ui": brief.get("ui", {})}, default_flow_style=False, sort_keys=False, allow_unicode=True).rstrip()
    audit_block_yaml = _yaml.dump({"audit_log": brief.get("audit_log", {})}, default_flow_style=False, sort_keys=False, allow_unicode=True).rstrip()

    tech = brief.get("tech_stack", {})
    existing_models_declared = brief.get("existing_models", [])
    out_of_scope = brief.get("out_of_pilot_scope", [])
    ki_rel = brief.get("ki_relevant")
    htmx_response = brief.get("htmx_response", "json")  # default — explizit machen!

    entities_section = "\n".join(_entity_block(e) for e in konsumiert)

    # Model-Introspection (Iter-v2, Lesson-Learned)
    inspected = _inspect_django_models(repo)
    tenant_info = _detect_tenant_pattern(inspected)
    auth_user_model = _detect_auth_user_model(repo)
    # Iter-v3: Dev-Run + Infra (Lessons #6/#7/#8)
    dev_run = _inspect_dev_run(repo)
    infra_ctx = _inspect_infra_context()

    # Existing-Models-Section mit AUTO-Field-Detail (statt User-Stub)
    existing_models_lines = []
    for decl in existing_models_declared:
        app = decl.get("app", "?")
        model = decl.get("model", "?")
        key = f"{app}.{model}"
        existing_models_lines.append(f"### `{key}`")
        existing_models_lines.append(f"\n**Relation:** {decl.get('relation', '—')}\n")
        live = inspected.get(key)
        if live:
            existing_models_lines.append(f"**Auto-introspectiert aus** `{live['source_path']}`:")
            existing_models_lines.append("\n| Field | Type | Args/Kwargs |")
            existing_models_lines.append("|---|---|---|")
            for fname, fdef in live["fields"].items():
                ftype = fdef["type"]
                args_str = ", ".join(fdef["args"][:3])
                kw_str = ", ".join(f"{k}={v}" for k, v in list(fdef["kwargs"].items())[:4])
                detail = " | ".join([s for s in [args_str, kw_str] if s])
                existing_models_lines.append(f"| `{fname}` | `{ftype}` | {detail or '—'} |")
            existing_models_lines.append("")
        else:
            existing_models_lines.append(f"⚠ **Im Repo NICHT gefunden** — Brief-Declaration ist möglicherweise falsch (Spec-Drift)\n")
    existing_models_section = "\n".join(existing_models_lines) or "*Keine.*"

    # Drift-Sektion: KD-Spec ↔ echtes Model — immer Output (auch wenn fields_typed fehlt)
    drift_lines = []
    for ename in konsumiert:
        edef = entities_all.get(ename) or {}
        spec_fields_typed = edef.get("fields_typed", {}) or {}
        spec_fields_untyped = [
            (f if isinstance(f, str) else (f.get("name", "?") if isinstance(f, dict) else str(f)))
            for f in (edef.get("fields") or [])
        ]
        # Match-Heuristik: snake_case → CamelCase
        candidates = [k for k in inspected.keys() if k.split(".", 1)[1].lower() == ename.lower()]
        if not candidates:
            candidates = [k for k in inspected.keys() if k.split(".", 1)[1].lower().rstrip("e") == ename.lower().rstrip("e")]
        if not candidates:
            drift_lines.append(f"### `{ename}` — KD-lokale Entity (kein passendes Real-Model)")
            if spec_fields_typed:
                drift_lines.append(f"\n*Spec hat `fields_typed` ({len(spec_fields_typed)} Felder) — Implementierung erzeugt Model neu in §3.*\n")
            else:
                drift_lines.append(f"\n*Spec hat nur `fields`-Liste ({len(spec_fields_untyped)} Felder) ohne Typen — Implementation muss Field-Types selbst wählen.*\n")
            continue
        real_key = candidates[0]
        real_fields = inspected[real_key]["fields"]
        real_keys = set(real_fields.keys())
        drift_lines.append(f"### `{ename}` ↔ `{real_key}`")
        drift_lines.append(f"\n**Real-Model-Pfad:** `{inspected[real_key]['source_path']}`")
        if spec_fields_typed:
            spec_keys = set(spec_fields_typed.keys())
            only_in_spec = spec_keys - real_keys
            only_in_real = real_keys - spec_keys
            common = spec_keys & real_keys
            drift_lines.append(f"\n**Gemeinsame Felder:** {', '.join(f'`{f}`' for f in sorted(common)) or '—'}")
            if only_in_spec:
                drift_lines.append(f"\n**Nur im KD-Spec (Spec-Drift, Real fehlt):** {', '.join(f'`{f}`' for f in sorted(only_in_spec))}")
            if only_in_real:
                drift_lines.append(f"\n**Nur im Real-Model (KD vereinfacht):** {', '.join(f'`{f}`' for f in sorted(only_in_real))}")
        else:
            # KD untyped — zeige Match + Real-Surplus
            spec_keys = set(spec_fields_untyped)
            only_in_spec = spec_keys - real_keys
            only_in_real = real_keys - spec_keys
            common = spec_keys & real_keys
            drift_lines.append(f"\n⚠ **KD-Spec hat keine `fields_typed`** (nur Field-Namen-Liste) — Drift-Check Field-Name-only.")
            drift_lines.append(f"\n**Match Spec ↔ Real (Name-only):** {', '.join(f'`{f}`' for f in sorted(common)) or '—'}")
            if only_in_spec:
                drift_lines.append(f"\n**KD nennt Felder die Real-Model NICHT hat:** {', '.join(f'`{f}`' for f in sorted(only_in_spec))} — Spec-Drift, ggf. Cleanup oder Mapping nötig")
            if only_in_real:
                drift_lines.append(f"\n**Real-Model hat {len(only_in_real)} Felder die KD-Spec NICHT erwähnt** (KD vereinfacht; Engineering ergänzt aus Real-Stand):")
                # Top-10 Felder zeigen
                for rfield in sorted(only_in_real)[:10]:
                    rtype = real_fields[rfield]["type"]
                    drift_lines.append(f"  - `{rfield}: {rtype}`")
                if len(only_in_real) > 10:
                    drift_lines.append(f"  - … +{len(only_in_real) - 10} weitere")
        drift_lines.append("")
    drift_section = "\n".join(drift_lines) or "*Keine konsumierten Entities deklariert — kein Drift-Check möglich.*"

    # Tenant-Hint
    tenant_hint = ""
    if tenant_info.get("active"):
        tenant_hint = (
            f"\n> 🚨 **Multi-Tenant-Repo** ({tenant_info['count']} Models mit `tenant_id`): "
            f"{tenant_info['rationale']}\n"
        )

    return f"""# Implementation-Brief — `{repo}:{kd_name}#{screen_id}`

> Auto-generiert via `klickdummy_lineage.py --gen-impl-brief` ({date.today().isoformat()})
> Pattern-Quelle: `ausschreibungs-hub:docs/analysen/implementation-brief-konzept.md` (Variante 3, Pilot)
> Konformität: `platform:ADR-211` Rev 16

## 1. Klickdummy-Kontext

| | |
|---|---|
| Repo | `{repo}` |
| Klickdummy | `{kd_name}` |
| Screen-ID | `{screen_id}` |
| Title | {title} |
| Personas | {", ".join(personas) or "—"} |
| Halbschicht | `{halbschicht}` |
| Voraussetzungs-Screen | `{voraussetzung}` |
| Folge-Screens | {", ".join(f"`{n}`" for n in next_screens) or "—"} |
| KI-relevant | `{ki_rel}` |

### Fokus-Bullets (Quelle: Klickdummy-Spec)

{chr(10).join("- " + str(f) for f in fokus) or "—"}

## 2. Tech-Stack

```yaml
{_yaml.dump(tech, default_flow_style=False, sort_keys=False, allow_unicode=True).rstrip()}
```

## 3. Datenmodell (typisiert)

{entities_section or "*Keine konsumierten Entities deklariert.*"}

## 4. API-Vertrag

```yaml
{api_block_yaml}
```

## 5. Akzeptanz-Tests (Given/When/Then)

```yaml
{tests_block_yaml}
```

## 6. Performance-NFRs

```yaml
{nfrs_block_yaml}
```

## 7. UI-Komponenten-Schema

```yaml
{ui_block_yaml}
```

## 8. Audit-Log + Compliance

```yaml
{audit_block_yaml}
```

## 9. Bezug zu bestehenden Django-Models (auto-introspectiert aus Repo)

{tenant_hint}
**`AUTH_USER_MODEL` im Repo:** `{auth_user_model}`

{existing_models_section}

## 10. §Genesor-vs-Realität-Drift (Spec ↔ Echtes Model)

Diese Sektion zeigt **systematisch**, wo Klickdummy-Spec und Implementierungs-
Realität abweichen — wertvoll für Brief-Iteration v2 und Spec-Pflege.

{drift_section}

## 11. Dev-Run (Pilot-Lesson #6 — wie startet die App?)

```yaml
{_yaml.dump({"dev_run": dev_run}, default_flow_style=False, sort_keys=False, allow_unicode=True).rstrip()}
```

**Schnellstart-Sequenz:**
1. `cd {dev_run.get("repo_path", "~/github/" + repo)}`
2. `{dev_run.get("requirements_install", "pip3 install --break-system-packages -r requirements.txt")}`
3. `{dev_run.get("start_command", "python3 manage.py runserver 0.0.0.0:" + str(dev_run.get("http_port", 8000)))}`
4. Test: `curl {dev_run.get("test_url", "http://localhost:8000/healthz/")}`
5. Pilot-Login: **admin / admin123** auf `http://<host>:{dev_run.get("http_port", 8000)}/admin/login/`

{"⚠ **Requirements-Drift:** pyproject.toml hat Deps die in requirements.txt fehlen: " + ", ".join("`" + d + "`" for d in dev_run.get("requirements_drift", [])) + chr(10) if dev_run.get("requirements_drift") else ""}

## 12. Infrastructure-Kontext (Pilot-Lessons #7 + #8)

```yaml
{_yaml.dump({"infra_context": infra_ctx}, default_flow_style=False, sort_keys=False, allow_unicode=True).rstrip()}
```

**Port-Konflikt-Check:** Brief-Port `{dev_run.get("http_port", "?")}` vs. live-Listener im Workspace —
{("⚠ **belegt!** durch " + ", ".join(p["app"] for p in (infra_ctx.get("port_neighbors") or []) if p.get("port") == dev_run.get("http_port"))) if any(p.get("port") == dev_run.get("http_port") for p in (infra_ctx.get("port_neighbors") or [])) else "✓ frei laut INFRASTRUCTURE.md"}

**Cloud-Firewall:** {("Public-Port `" + str(dev_run.get("http_port", "?")) + "` ist " + ("✓ bereits offen" if dev_run.get("http_port") in (infra_ctx.get("cloud_firewall_default_open") or []) else "❌ **muss geöffnet werden** via `~/github/bin/hetzner-fw-open.sh " + str(dev_run.get("http_port", "")) + "`")) if dev_run.get("http_port") and infra_ctx.get("cloud_firewall_id") else "—"}

## 13. NICHT im MVP-Pilot

{chr(10).join("- " + str(s) for s in out_of_scope) or "—"}

---

## LLM-Generierungs-Anweisung

Du baust eine **Django-App** namens `{tech.get("django_app", "submission_workflow")}` in `apps/{tech.get("django_app", "submission_workflow")}/`. Erzeuge ein Skelett mit:

1. **`models.py`** — neue Models exakt gemäß §3 Datenmodell + **Multi-Tenant-Felder** wo §9 das Pattern zeigt (z. B. `tenant_id: BigIntegerField(db_index=True)`).
2. **`views.py`** — gemäß §4 API-Vertrag. Multipart, SHA256, Error-Codes. **Berechtigungs-Check via Tenant-Membership** (siehe §9 Hint, NICHT direkter User-FK).
3. **`urls.py`** — Routen aus §4.
4. **`templates/{tech.get("django_app", "submission_workflow")}/{screen_id}.html`** — HTMX-Template gemäß §7. **`htmx_response: {htmx_response}`** — View MUSS entsprechend rendern (html-partial: Template-Render mit `_partial.html`; json: JsonResponse).
5. **`templates/{tech.get("django_app", "submission_workflow")}/_upload_status.html`** — nur wenn `htmx_response: html-partial`.
6. **`tests/test_{screen_id}.py`** — pytest-Django gemäß §5 Given/When/Then.
7. **`migrations/0001_initial.py`** — auto via `makemigrations`.
8. **`admin.py`** — Django-Admin-Registrierung.

**Constraints:**
- §9 zeigt **echte** Model-Field-Listen aus Repo-Introspection. **KEINE Halluzinationen** zu Feldnamen/Types — entweder aus §9 übernehmen oder TODO-Stub.
- §10 zeigt Spec↔Real-Drift. Wo Spec Felder vorsieht die im Real-Model fehlen: **neue Models bauen**, nicht in fremde Models reinpfuschen.
- Wo §9 ein Multi-Tenant-Pattern zeigt: **JEDES neue Model bekommt `tenant_id`** + Views filtern darauf.
- Out-of-Pilot-Scope-Features (§11): TODO-Stub.

**Output-Format:**
Pro Datei ein Code-Block mit Pfad im Header (`# apps/{tech.get("django_app", "submission_workflow")}/models.py`). Knapp halten.
"""


def build_impl_brief_html(brief_md: str, repo: str, kd_name: str, screen_id: str,
                          profile: str, style: dict) -> str:
    """Implementation-Brief Markdown → HTML mit CD + Genesor-Topbar + Side-Nav."""
    import markdown as _md
    from datetime import date
    body_html = _md.markdown(
        brief_md,
        extensions=["tables", "fenced_code", "attr_list", "sane_lists", "toc"],
    )
    accent = style["accent"]
    accent_bg = style["accent_bg"]
    font_h = style["font_h"]
    return f"""<!DOCTYPE html>
<html lang="de"><head><meta charset="utf-8">
<title>Impl-Brief · {html.escape(kd_name)}#{html.escape(screen_id)}</title>
<style>
  body {{ font-family: -apple-system, "Segoe UI", system-ui, sans-serif; margin: 0; padding: 0; background: #f5f7fa; color: #1f2937; line-height: 1.55; }}
  header.topbar {{ background: {accent}; color: #fff; padding: 12px 20px; display: flex; gap: 14px; align-items: center; flex-wrap: wrap; }}
  header.topbar h1 {{ margin: 0; font-size: 18px; font-weight: 600; flex: 1; min-width: 200px; }}
  header.topbar a {{ color: #fff; text-decoration: none; font-size: 13px; }}
  header.topbar a:hover {{ text-decoration: underline; }}
  header.topbar .badge {{ background: rgba(255,255,255,.15); padding: 3px 10px; border-radius: 4px; font-size: 12px; }}
  main {{ max-width: 1100px; margin: 0 auto; padding: 24px; background: #fff; }}
  main h1 {{ font-family: {font_h}; color: {accent}; font-size: 22pt; margin: 0 0 6pt; border-bottom: 2px solid {accent_bg}; padding-bottom: 6pt; }}
  main h2 {{ font-family: {font_h}; color: {accent}; font-size: 16pt; margin: 18pt 0 6pt; border-bottom: 1px solid {accent_bg}; padding-bottom: 3pt; }}
  main h3 {{ font-family: {font_h}; color: #374151; font-size: 13pt; margin: 12pt 0 4pt; }}
  main p, main li {{ font-size: 12pt; color: #1f2937; }}
  main code {{ background: #f3f4f6; padding: 1px 5px; border-radius: 3px; font-family: 'Menlo', 'Monaco', monospace; font-size: 11pt; }}
  main pre {{ background: #f8fafc; border: 1px solid #e3e8ee; padding: 12px; border-radius: 4px; overflow-x: auto; font-size: 11pt; }}
  main pre code {{ background: transparent; padding: 0; }}
  main table {{ border-collapse: collapse; width: 100%; margin: 8pt 0; }}
  main th, main td {{ border: 1px solid #d1dce8; padding: 6pt 10pt; text-align: left; vertical-align: top; }}
  main th {{ background: {accent_bg}; color: {accent}; font-weight: 600; }}
  blockquote {{ border-left: 4px solid {accent}; background: {accent_bg}; padding: 8px 14px; margin: 10pt 0; color: #374151; font-size: 11pt; }}
  hr {{ border: none; border-top: 1px solid #d1dce8; margin: 14pt 0; }}
  .copy-prompt-btn {{ position: fixed; bottom: 20px; right: 20px; background: {accent}; color: #fff; padding: 10px 18px; border-radius: 6px; cursor: pointer; font-size: 13px; box-shadow: 0 4px 12px rgba(0,0,0,.15); border: none; }}
  .copy-prompt-btn:hover {{ opacity: 0.9; }}
</style></head><body>
<header class="topbar">
  <h1>📑 Implementation-Brief · {html.escape(kd_name)}#{html.escape(screen_id)}</h1>
  <a href="./render/{html.escape(repo)}-{html.escape(kd_name)}.html">📱 Mockup</a>
  <a href="./screen-lineage-{html.escape(repo)}-{html.escape(kd_name)}.html">🕸 Screen-Lineage</a>
  <a href="./uc-{html.escape(repo)}.html?kd={html.escape(kd_name)}">📋 UCs</a>
  <a href="./impl-brief/{html.escape(repo)}-{html.escape(kd_name)}-{html.escape(screen_id)}.md">📄 Raw .md</a>
  <a href="./index.html">🌱 Genesor</a>
  <span class="badge">profile {html.escape(profile)} · {date.today().isoformat()}</span>
</header>
<main>
{body_html}
</main>
<button class="copy-prompt-btn" onclick="copyPrompt()">📋 Brief → Zwischenablage (für LLM-Prompt)</button>
<script>
  async function copyPrompt() {{
    try {{
      const resp = await fetch('./impl-brief/{html.escape(repo)}-{html.escape(kd_name)}-{html.escape(screen_id)}.md');
      const text = await resp.text();
      await navigator.clipboard.writeText(text);
      const btn = document.querySelector('.copy-prompt-btn');
      btn.textContent = '✓ kopiert!';
      setTimeout(() => btn.textContent = '📋 Brief → Zwischenablage (für LLM-Prompt)', 2000);
    }} catch (e) {{
      alert('Fehler beim Kopieren: ' + e.message);
    }}
  }}
</script>
</body></html>
"""


def build_uc_export_json(ucs: list[dict], kds: list[dict], coverage: dict) -> str:
    """Strukturierter JSON-Export für Weiterverwendung (Workshop 2026-05-26 #5).

    Schema: ``{schema_version, generated_at, source, summary, kds, ucs, coverage}``.
    Maschinenlesbar — Konsumenten: Backstage-Plugin, Excel-Export, Linear-Sync,
    PDF-Reportgenerator. SSoT bleibt YAML im git; dieser Export ist Read-Only-
    Snapshot zum Build-Zeitpunkt.
    """
    from datetime import datetime
    real_count = coverage["uc_realized_count"]
    unres = coverage["uc_unresolved"]
    matrix = coverage["matrix"]

    # KDs (nur spec-KDs, vereinfacht)
    kds_out = []
    for kd in kds:
        if kd.get("kind", "spec") != "spec":
            continue
        d = kd.get("data", {}) or {}
        adr_local = (d.get("adr", {}) or {}).get("local") or ""
        kds_out.append({
            "repo": kd["repo"],
            "kd_name": kd["kd"],
            "adr_local": adr_local,
            "klass": d.get("class"),
            "spec_role": d.get("spec_role") or "default",
            "sunset_after": (d.get("off_ramp", {}) or {}).get("sunset_after"),
            "n_screens": len([s for s in (d.get("screens") or []) if isinstance(s, dict)]),
            "render_url": f"./render/{kd['repo']}-{kd['kd']}.html",
        })

    # UCs (vollständig flat)
    ucs_out = []
    for uc in ucs:
        gid = f"{uc['repo']}:{uc['uc_id']}"
        try:
            rel_src = str(uc["source_file"].relative_to(REPOS_ROOT))
        except (ValueError, KeyError):
            rel_src = str(uc.get("source_file", ""))
        ucs_out.append({
            "uc_id_global": gid,
            "uc_id_local": uc["uc_id"],
            "repo": uc["repo"],
            "name": uc["name"],
            "primaer_akteur": uc.get("akteur") or None,
            "sekundaer_akteure": uc.get("sekundaer") or [],
            "realisiert_von_klickdummy": uc.get("realisiert_von") or None,
            "related_screens": uc.get("related_screens") or [],
            "fv_bezug": uc.get("fv_bezug") or None,
            "prio": uc.get("prio") or None,
            "status": uc.get("status") or "draft",
            "source_file": rel_src,
            "coverage": {
                "realized_count": real_count.get(gid, 0),
                "unresolved_refs": unres.get(gid, []),
            },
        })

    # Coverage-Matrix als Liste (JSON kann keine tuple-keys)
    matrix_out = [
        {"uc_id_global": gid, "repo": r, "kd_name": k, "screens": screens}
        for (gid, r, k), screens in matrix.items()
    ]

    payload = {
        "schema_version": "1.0",
        "generated_at": datetime.utcnow().isoformat(timespec="seconds") + "Z",
        "source": "klickdummy_lineage.py --genesor (ADR-211 Rev 16)",
        "summary": {
            "n_ucs": len(ucs_out),
            "n_kds": len(kds_out),
            "n_realized_ucs": sum(1 for v in real_count.values() if v > 0),
            "n_coverage_cells": sum(len(v) for v in matrix.values()),
            "repos": sorted({u["repo"] for u in ucs_out} | {k["repo"] for k in kds_out}),
        },
        "kds": kds_out,
        "ucs": ucs_out,
        "coverage_matrix": matrix_out,
    }
    return json.dumps(payload, indent=2, ensure_ascii=False)


def _repo_of_path(p: Path) -> str | None:
    """Repo-Name aus absolutem Pfad: ``~/github/<repo>/...`` → ``<repo>``."""
    try:
        rel = p.relative_to(REPOS_ROOT)
        return rel.parts[0] if rel.parts else None
    except ValueError:
        return None


def _git_publish_changes(repo: str, paths: list[Path], commit_msg: str,
                        dry_run: bool = False, push: bool = True,
                        allow_main: bool = False) -> dict:
    """Stage + commit + push einer Path-Liste in einem Repo (Auto-Publish).

    Sicherheits-Konstraints:
    - Bei branch ∈ {main, master} wird push übersprungen (außer ``allow_main``)
    - Idempotent: wenn nichts zu committen, kein commit
    - Nur die übergebenen Pfade werden gestaged (kein ``git add .``)

    Returns: ``{committed, pushed, branch, sha, n_files, skip_reason}``.
    """
    import subprocess
    repo_path = REPOS_ROOT / repo
    try:
        branch = subprocess.check_output(
            ["git", "-C", str(repo_path), "rev-parse", "--abbrev-ref", "HEAD"],
            stderr=subprocess.DEVNULL, text=True, timeout=3,
        ).strip()
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError):
        return {"committed": False, "pushed": False, "branch": None, "sha": None,
                "n_files": 0, "skip_reason": "git-not-available"}

    rel_paths: list[str] = []
    for p in paths:
        try:
            rel_paths.append(str(p.relative_to(repo_path)))
        except ValueError:
            continue
    if not rel_paths:
        return {"committed": False, "pushed": False, "branch": branch, "sha": None,
                "n_files": 0, "skip_reason": "no-files"}

    if dry_run:
        return {"committed": False, "pushed": False, "branch": branch, "sha": None,
                "n_files": len(rel_paths),
                "skip_reason": f"dry-run · würde {len(rel_paths)} Files auf {branch} committen"}

    # Stage (auch deleted files — git add -A für die Pfade)
    subprocess.run(
        ["git", "-C", str(repo_path), "add", "-A", "--"] + rel_paths,
        check=True,
    )
    # Idempotent check
    if subprocess.run(
        ["git", "-C", str(repo_path), "diff", "--cached", "--quiet"],
        stderr=subprocess.DEVNULL,
    ).returncode == 0:
        return {"committed": False, "pushed": False, "branch": branch, "sha": None,
                "n_files": len(rel_paths), "skip_reason": "nothing-to-commit"}

    subprocess.run(
        ["git", "-C", str(repo_path), "commit", "-m", commit_msg],
        check=True,
    )
    sha = subprocess.check_output(
        ["git", "-C", str(repo_path), "rev-parse", "--short", "HEAD"],
        text=True,
    ).strip()

    if not push:
        return {"committed": True, "pushed": False, "branch": branch, "sha": sha,
                "n_files": len(rel_paths), "skip_reason": "push-disabled"}
    if branch in ("main", "master") and not allow_main:
        return {"committed": True, "pushed": False, "branch": branch, "sha": sha,
                "n_files": len(rel_paths),
                "skip_reason": f"branch={branch} (Schutz; --allow-main-push zum overriden)"}

    push_result = subprocess.run(
        ["git", "-C", str(repo_path), "push"],
        capture_output=True, text=True,
    )
    if push_result.returncode != 0:
        # Vermutlich: branch hat keinen upstream → -u nötig
        retry = subprocess.run(
            ["git", "-C", str(repo_path), "push", "-u", "origin", branch],
            capture_output=True, text=True,
        )
        if retry.returncode != 0:
            return {"committed": True, "pushed": False, "branch": branch, "sha": sha,
                    "n_files": len(rel_paths),
                    "skip_reason": f"push-failed: {retry.stderr.strip()[:200]}"}
    return {"committed": True, "pushed": True, "branch": branch, "sha": sha,
            "n_files": len(rel_paths), "skip_reason": None}


def _auto_publish_per_repo(paths: list[Path], action: str, dry_run: bool,
                          allow_main: bool) -> None:
    """Gruppiert Pfade pro Repo und publishet jedes Repo einzeln. Stdout-Report."""
    from collections import defaultdict
    by_repo: dict[str, list[Path]] = defaultdict(list)
    for p in paths:
        r = _repo_of_path(p)
        if r:
            by_repo[r].append(p)
    msg_map = {
        "gen":   "feat(use-cases): auto-generierte UC-Skelette (--auto-publish)",
        "prune": "chore(use-cases): prune auto-generierte UC-Skelette (--auto-publish)",
    }
    commit_msg = msg_map.get(action, "chore(use-cases): auto-publish")
    print(f"\n--- Auto-Publish ({action}) ---")
    for repo, paths_for_repo in by_repo.items():
        result = _git_publish_changes(repo, paths_for_repo, commit_msg,
                                     dry_run=dry_run, push=True,
                                     allow_main=allow_main)
        if result["committed"] and result["pushed"]:
            print(f"  ✓ {repo}: commit {result['sha']} auf {result['branch']} gepusht ({result['n_files']} Files)")
        elif result["committed"]:
            print(f"  ⚠ {repo}: commit {result['sha']} auf {result['branch']} — PUSH übersprungen ({result['skip_reason']})")
        elif result["skip_reason"]:
            print(f"  · {repo}: {result['skip_reason']}")


# ---- UC-Skelett-Generator (Workshop-Feedback 2026-05-26 #2) ---------------

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
    for src in (spec_data.get("root_entities") or {}, spec_data.get("local_entities") or {}):
        if isinstance(src, dict):
            out.update(src)
    return out.get(entity_name) or {}


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
        out_dir = REPOS_ROOT / repo / "docs" / "use-cases" / "_auto"
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


# ---- main -------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(description="Klickdummy-Lineage-Viewer + IIL-Genesor")
    parser.add_argument("--genesor", action="store_true",
                        help="Cross-Repo-Übersicht (Stufe 1a/b) zusätzlich emittieren")
    parser.add_argument("--no-single", action="store_true",
                        help="Single-Repo-Output (meiki-hub) überspringen")
    parser.add_argument("--gen-uc-skeletons", action="store_true",
                        help="UC-Skelette aus Klickdummy-Specs erzeugen (ADR-211 Rev 16)")
    parser.add_argument("--prune-auto-ucs", action="store_true",
                        help="UC-Files mit `auto_generated: true` Frontmatter löschen (idempotent)")
    parser.add_argument("--validate-ucs", action="store_true",
                        help="UC-Validator (Layer A) standalone laufen — exit 1 bei errors")
    parser.add_argument("--strict", action="store_true",
                        help="--validate-ucs: warnings als FAIL behandeln (CI-Modus)")
    parser.add_argument("--gen-impl-brief", metavar="REPO:KD:SCREEN",
                        help="Implementation-Brief für 1 Screen erzeugen (Variante-3-Pilot)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Nur anzeigen was geschrieben/gelöscht würde, ohne Files anzufassen")
    parser.add_argument("--auto-publish", action="store_true",
                        help="Nach Gen/Prune: pro Repo Commit + Push der geänderten _auto/-Files")
    parser.add_argument("--allow-main-push", action="store_true",
                        help="Erlaube --auto-publish auch auf main/master (Default: skip mit Warning)")
    parser.add_argument("--repos-root", default=str(Path.home() / "github"),
                        help="Wurzelverzeichnis der gescannten Repos (Default: ~/github)")
    parser.add_argument("--out", default=None,
                        help="Genesor-Output-Verzeichnis (Default: <repos-root>/genesor)")
    parser.add_argument("--base-url", default="/",
                        help="URL-Präfix für generierte Links + Skin-Pfade (Default: '/')")
    parser.add_argument("--skin-base", default="",
                        help="Basis-URL für Skin-CSS (z. B. '/genesor/skins'). Leer (Default) → "
                             "Skins unter '/iil-klickdummy/.../skins/<name>.css' (byte-identisch zu früher); "
                             "gesetzt → '<skin-base>/<name>.css' für einen self-contained Build.")
    parser.add_argument("--vendored-repos", default="",
                        help="Komma-separierte Repo-Namen, deren echte Mockup-HTMLs einvendoriert "
                             "unter '/kd/<repo>/...' ausgeliefert werden (z. B. 'ausschreibungs-hub'). "
                             "Leer (Default) → keine Umschreibung (byte-identisch zu früher).")
    args = parser.parse_args()

    # Argparse → modulweite Konfiguration (alle Funktionen lesen diese Globals).
    # Defaults reproduzieren das bisherige Verhalten byte-identisch.
    global REPOS_ROOT, GENESOR_OUT, BASE_URL, SKIN_BASE, VENDORED_REPOS
    REPOS_ROOT = Path(args.repos_root).expanduser()
    GENESOR_OUT = Path(args.out).expanduser() if args.out else REPOS_ROOT / "genesor"
    BASE_URL = args.base_url
    SKIN_BASE = args.skin_base
    VENDORED_REPOS = {r.strip() for r in args.vendored_repos.split(",") if r.strip()}

    if args.gen_impl_brief:
        try:
            repo_a, kd_a, screen_a = args.gen_impl_brief.split(":", 2)
        except ValueError:
            print(f"❌ Format: REPO:KD:SCREEN — '{args.gen_impl_brief}'")
            return 1
        records = find_all_repos_specs()
        rec = next((r for r in records if r["repo"] == repo_a and r["kd"] == kd_a), None)
        if not rec:
            print(f"❌ KD nicht gefunden: {repo_a}:{kd_a}")
            return 1
        brief_md = build_impl_brief(rec, screen_a)
        if brief_md is None:
            print(f"❌ Screen '{screen_a}' hat kein `implementation_brief`-Block ODER existiert nicht")
            return 1
        out_dir = GENESOR_OUT / "impl-brief"
        out_dir.mkdir(parents=True, exist_ok=True)
        out_file = out_dir / f"{repo_a}-{kd_a}-{screen_a}.md"
        out_file.write_text(brief_md, encoding="utf-8")
        print(f"✓ {out_file} ({len(brief_md)} chars)")
        return 0

    if args.validate_ucs:
        records = find_all_repos_specs()
        ucs = find_all_repos_ucs()
        findings = validate_ucs(ucs, records)
        n_err = 0
        n_warn = 0
        for gid, items in sorted(findings.items()):
            for f in items:
                icon = "❌" if f["severity"] == "error" else "⚠"
                print(f'  {icon} {gid:<45} {f["code"]:<22} {f["msg"]}')
                if f["severity"] == "error":
                    n_err += 1
                else:
                    n_warn += 1
        n_clean = len(ucs) - len(findings)
        print(f"\nValidator (Layer A): {n_clean}/{len(ucs)} clean · {n_warn} warnings · {n_err} errors")
        if n_err > 0:
            return 1
        if args.strict and n_warn > 0:
            print("--strict: warnings als FAIL")
            return 1
        return 0

    if args.prune_auto_ucs:
        # UC-Cleanup (Workshop 2026-05-26 #3): löscht ausschließlich Files mit
        # `auto_generated: true` im Frontmatter — handgepflegte UCs bleiben.
        deleted: list[Path] = []
        for uc_path in REPOS_ROOT.glob("*/docs/use-cases/**/UC-*.md"):
            try:
                text = uc_path.read_text("utf-8")
            except OSError:
                continue
            fm = _parse_uc_frontmatter(text)
            if not fm or not fm.get("auto_generated"):
                continue
            if args.dry_run:
                deleted.append(uc_path)
            else:
                uc_path.unlink()
                deleted.append(uc_path)
        for p in deleted:
            print(f"{'(dry) ' if args.dry_run else ''}🗑️  {p}")
        print(f"\n{len(deleted)} UC-File(s) {'würden gelöscht' if args.dry_run else 'gelöscht'}.")
        if args.auto_publish and deleted:
            _auto_publish_per_repo(deleted, action="prune",
                                  dry_run=args.dry_run,
                                  allow_main=args.allow_main_push)
        elif deleted and not args.dry_run:
            print("\n💡 Tipp: --auto-publish für direkten Commit+Push der Löschung")
        return 0

    if args.gen_uc_skeletons:
        records = find_all_repos_specs()
        existing_ucs = find_all_repos_ucs()
        result = generate_uc_skeletons(records, existing_ucs, dry_run=args.dry_run)
        for p in result["written"]:
            print(f"{'(dry) ' if args.dry_run else ''}✓ {p}")
        print(f"\n{len(result['written'])} UC-Skelette {'würden geschrieben' if args.dry_run else 'geschrieben'} · {result['skipped']} übersprungen (existierend/abgedeckt)")
        if args.auto_publish and result["written"]:
            _auto_publish_per_repo(result["written"], action="gen",
                                  dry_run=args.dry_run,
                                  allow_main=args.allow_main_push)
        elif result["written"] and not args.dry_run:
            print("\n💡 Tipp: --auto-publish für direkten Commit+Push (Edit-Links sofort auf GitHub aktiv)")
        return 0

    if not args.no_single:
        specs = find_specs()
        contracts = find_contracts()
        if specs:
            print(f"Single-Repo · gefundene Klickdummies: {len(specs)} · Contracts: {len(contracts)}")
            mermaid_text = emit_mermaid(specs, contracts)
            html_text = build_html(mermaid_text, specs, contracts)
            OUT_DIR.mkdir(parents=True, exist_ok=True)
            (OUT_DIR / "lineage.mmd").write_text(mermaid_text, encoding="utf-8")
            (OUT_DIR / "index.html").write_text(html_text, encoding="utf-8")
            print(f"✓ {OUT_DIR / 'lineage.mmd'}")
            print(f"✓ {OUT_DIR / 'index.html'}")

    if args.genesor:
        records = find_all_repos_specs()
        if not records:
            print(f"WARN: Keine Klickdummies unter {REPOS_ROOT} gefunden.", file=sys.stderr)
            return 1
        GENESOR_OUT.mkdir(parents=True, exist_ok=True)
        print(f"Genesor (Cross-Repo) · gefundene Klickdummies: {len(records)} aus "
              f"{len({(r['org'], r['repo']) for r in records})} Repos / "
              f"{len({r['org'] for r in records})} Orgs")
        # Cross-Repo-Lookup für Auto-KD-Linking in Akten-Zeilen:
        # Aktentyp (z. B. „wohngeld") wird gegen diesen Set gematcht; existiert
        # ein KD, bekommt die Tabellen-Zeile einen Sprung-CTA ins Ziel-FV-KD.
        # Lookup: {kd_name: (url, repo)}. Repo wird im Modal als Cross-Repo-Hinweis
        # angezeigt (z. B. „nl2cad → risk-hub / cad-analyse").
        known_kds: dict[str, str] = {}
        known_kd_repos: dict[str, str] = {}
        for r in records:
            if r.get("kind", "spec") != "spec":
                continue
            kd = r["kd"]
            known_kds[kd] = f"./{r['repo']}-{kd}.html"
            known_kd_repos[kd] = r["repo"]
        # Render-Fallback: für jeden KD ohne shell.html eine generierte HTML
        n_rendered = 0
        for rec in records:
            if rec.get("kind", "spec") != "spec":
                continue   # render-only KDs haben schon HTML, kein Fallback nötig
            kd_dir = rec["path"].parent
            if find_mockup_html(kd_dir, rec["kd"]) is None:
                generate_render_fallback(rec, GENESOR_OUT,
                                         known_kds=known_kds,
                                         known_kd_repos=known_kd_repos)
                n_rendered += 1
        if n_rendered:
            print(f"✓ {n_rendered} Render-Fallback-HTMLs in {GENESOR_OUT / 'render'}/")
        # Stufe 1b: Per-Repo-Lineages zuerst (damit Genesor sie verlinken kann)
        # Implementation-Briefs auto-emittieren (Pilot ADR-Variante-3) für alle
        # Screens mit implementation_brief-Block (User-Wunsch 2026-05-26: P2)
        impl_briefs_dir = GENESOR_OUT / "impl-brief"
        n_briefs = 0
        for rec in records:
            if rec.get("kind", "spec") != "spec":
                continue
            for s in (rec.get("data") or {}).get("screens") or []:
                if not isinstance(s, dict) or not s.get("implementation_brief"):
                    continue
                sid = s.get("id")
                brief_md = build_impl_brief(rec, sid)
                if not brief_md:
                    continue
                impl_briefs_dir.mkdir(parents=True, exist_ok=True)
                out_file = impl_briefs_dir / f"{rec['repo']}-{rec['kd']}-{sid}.md"
                out_file.write_text(brief_md, encoding="utf-8")
                # HTML-Render daneben (CD aus doc-profile)
                profile_ib = read_doc_profile(REPOS_ROOT / rec["repo"])
                style_ib = _DOMAIN_STYLES.get(profile_ib, _DOMAIN_STYLES["default"])
                html_out_ib = build_impl_brief_html(brief_md, rec["repo"], rec["kd"], sid, profile_ib, style_ib)
                (GENESOR_OUT / f"impl-brief-{rec['repo']}-{rec['kd']}-{sid}.html").write_text(html_out_ib, encoding="utf-8")
                n_briefs += 1
        if n_briefs:
            print(f"✓ {n_briefs} Implementation-Brief(s) in {impl_briefs_dir}/")

        # Per-KD Screen-Lineage (User-Feedback 2026-05-26 "vermisse das gesamt-lineage")
        n_screen_lineage = 0
        for rec in records:
            if rec.get("kind", "spec") != "spec":
                continue
            d = rec.get("data") or {}
            if not (d.get("screens") or []):
                continue
            repo_kd = rec["repo"]
            kd_kd = rec["kd"]
            profile_sl = read_doc_profile(REPOS_ROOT / repo_kd)
            style_sl = _DOMAIN_STYLES.get(profile_sl, _DOMAIN_STYLES["default"])
            html_out_sl = build_screen_lineage_html(repo_kd, kd_kd, d, profile_sl, style_sl)
            (GENESOR_OUT / f"screen-lineage-{repo_kd}-{kd_kd}.html").write_text(html_out_sl, encoding="utf-8")
            n_screen_lineage += 1
        if n_screen_lineage:
            print(f"✓ {n_screen_lineage} Screen-Lineage-Pages in {GENESOR_OUT}/")

        per_repo_files = generate_per_repo_lineages(records, GENESOR_OUT)
        for p in per_repo_files:
            print(f"✓ {p}")
        # UC-Coverage (ADR-211 Rev 16 §UC-Coverage) — cross-repo Heatmap
        ucs = find_all_repos_ucs()
        coverage = build_uc_coverage(ucs, records)
        coverage_html = build_coverage_html(ucs, records, coverage)
        (GENESOR_OUT / "coverage.html").write_text(coverage_html, encoding="utf-8")
        n_realized = sum(1 for v in coverage["uc_realized_count"].values() if v > 0)
        n_cells = sum(len(v) for v in coverage["matrix"].values())
        print(f"✓ {GENESOR_OUT / 'coverage.html'} ({len(ucs)} UCs / {n_realized} realized / {n_cells} cells)")

        # UC-Validator (Layer A) — Workshop 2026-05-26
        uc_findings = validate_ucs(ucs, records)
        n_err = sum(1 for v in uc_findings.values() for f in v if f["severity"] == "error")
        n_warn = sum(1 for v in uc_findings.values() for f in v if f["severity"] == "warning")
        n_clean = len(ucs) - len(uc_findings)
        print(f"--- UC-Validator (Layer A): {n_clean}/{len(ucs)} clean · {n_warn}w · {n_err}e ---")

        # Pro-Repo UC-Index (Workshop-Feedback 2026-05-26 #1)
        ucs_by_repo: dict[str, list[dict]] = {}
        for u in ucs:
            ucs_by_repo.setdefault(u["repo"], []).append(u)
        for repo_name, ucs_for_repo in ucs_by_repo.items():
            uc_idx_html = build_repo_uc_index_html(repo_name, ucs_for_repo, coverage,
                                                  kds=records, validation=uc_findings)
            (GENESOR_OUT / f"uc-{repo_name}.html").write_text(uc_idx_html, encoding="utf-8")
            print(f"✓ {GENESOR_OUT / f'uc-{repo_name}.html'} ({len(ucs_for_repo)} UCs)")

        # JSON-Export (Workshop-Feedback 2026-05-26 #5) — strukturierter Snapshot
        # für externe Konsumenten (Backstage, Excel, Linear-Sync, PDF-Report).
        export_json = build_uc_export_json(ucs, records, coverage)
        (GENESOR_OUT / "uc-export.json").write_text(export_json, encoding="utf-8")
        print(f"✓ {GENESOR_OUT / 'uc-export.json'} ({len(export_json)} chars)")

        # Genesor-Übersicht
        genesor_html = build_genesor_html(records, uc_coverage=coverage, n_ucs=len(ucs))
        (GENESOR_OUT / "index.html").write_text(genesor_html, encoding="utf-8")
        print(f"✓ {GENESOR_OUT / 'index.html'}")

        # ---- Smoke-Test (Standard nach jeder --genesor-Run) ------------------
        # Verhalten als Standard integriert (User-Vorschlag 2026-05-25):
        # Pattern-basierte Smoke-Checks der generierten Render-Output-Files.
        # Kein Playwright-Browser nötig — curl-frei Pure-Python Pattern-Match.
        print("\n--- Smoke-Test (Render-Output) ---")
        smoke_pass = 0
        smoke_fail = 0
        smoke_results = []
        for rec in records:
            if rec.get("kind", "spec") != "spec":
                continue
            kd_name = rec["kd"]
            repo = rec["repo"]
            render_path = GENESOR_OUT / "render" / f"{repo}-{kd_name}.html"
            if not render_path.is_file():
                continue
            content = render_path.read_text("utf-8")
            checks = [
                ("App-Frame vorhanden", '<div class="app-frame"' in content),
                ("ℹ Info-Button (Spec-Sicht)", 'ℹ Info' in content),
                ("❓ Hilfe-Button (End-User)", '❓ Hilfe' in content),
                ("Info-Modal-Global", 'id="info-modal-bg"' in content),
                ("Info-Hidden-Container", '<div class="screen-info" hidden' in content),
                ("Help-Hidden-Container", '<div class="screen-help" hidden' in content),
                ("Persona-Switcher", 'id="persona-select"' in content),
                ("Style-Switcher (Skin-Dropdown)", 'id="skin-select"' in content),
                ("Feedback-Widget", 'id="fb-widget"' in content),
                ("Status-Bar", '<div class="app-statusbar">' in content),
                ("Layout-Modus aktiv (Sidebar oder Tab-Bar)", 'class="has-sidebar"' in content or 'class="has-tabs"' in content),
                ("Akte-Modal-Container vorhanden", '<div class="screen-akte" hidden' in content),
                ("Akten-Link in Tabellen (sofern Entity Aktenzeichen hat)",
                 'class="akten-link"' in content or 'aktenzeichen' not in content.lower()),
            ]
            failed = [name for name, ok in checks if not ok]
            if failed:
                smoke_fail += 1
                smoke_results.append(f"  ❌ {repo}-{kd_name}: {', '.join(failed)}")
            else:
                smoke_pass += 1
        print(f"Smoke: {smoke_pass} passed, {smoke_fail} failed")
        for r in smoke_results[:5]:
            print(r)
        if smoke_fail > 0:
            print(f"\n⚠ {smoke_fail} Render(s) mit fehlenden Pattern. Re-Generierung oder Code-Fix nötig.", file=sys.stderr)

    return 0


def main_cli() -> int:
    """Console-Script-Entry (klickdummy-genesor)."""
    return main()


if __name__ == "__main__":
    sys.exit(main_cli())

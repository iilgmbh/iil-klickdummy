"""GenesorConfig — Konfigurationsmodul (KONZ-003 Empf-1).

Enthält:
  - GenesorConfig-Dataclass
  - Modul-weiten Singleton ``_cfg``
  - ``get_cfg()`` / ``set_cfg()`` — Thread-safe-Accessor (alle anderen Module
    rufen ``get_cfg()`` statt ``_cfg`` direkt zu importieren, damit main()
    den Singleton per ``set_cfg(new_cfg)`` austauschen kann ohne Circular-Import).
  - Backward-compat-Aliases REPOS_ROOT, GENESOR_OUT, BASE_URL, SKIN_BASE, VENDORED_REPOS
    (keine neuen Mutationen; für externe Leser die noch auf diese Namen referenzieren).
  - Helpers ``_base_prefix()``, ``_skin_url()`` die ausschließlich auf config stützen.
  - Modul-Konstanten MOCKUP_PRIO_NAMES, SKIN_LIBRARY_REL, _DOMAIN_STYLES,
    _BUERGER_POOL, _AKTEN_PROFIL_POOL, _FRONTMATTER_RE — haben keine Abhängigkeiten
    auf andere genesor-Module und werden von mehreren Modulen konsumiert.

Keine Rückabhängigkeiten — kann von jedem anderen genesor-Modul importiert werden.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

# ---------------------------------------------------------------------------
# Config-Dataclass
# ---------------------------------------------------------------------------


@dataclass
class GenesorConfig:
    """Explizite Konfiguration für den Genesor-Modus (KONZ-003 Empf-1).

    Ersetzt die mutierten Modul-Globals REPOS_ROOT, GENESOR_OUT, BASE_URL,
    SKIN_BASE, VENDORED_REPOS. Wird in main() aus argparse-Args instanziiert
    und als Modul-Global _cfg gesetzt — alle Funktionen lesen von _cfg statt
    von früheren bare Globals.

    Defaults reproduzieren das bisherige Verhalten byte-identisch.
    """

    repos_root: Path = field(default_factory=lambda: Path.home() / "github")
    # genesor_out None → wird lazy auf repos_root / "genesor" aufgelöst
    _genesor_out: Path | None = field(default=None, repr=False)
    # URL-Präfix für generierte Cross-Repo-Links + Skin-Library-Pfade.
    # Default "/" reproduziert das bisherige Verhalten byte-identisch (HTTP-Root = ~/github).
    # Wird via --base-url überschrieben (z. B. "/genesor-host/" für einen späteren Portal-Build).
    base_url: str = "/"
    # Basis-URL für die Skin-CSS-Dateien. Default "" reproduziert das bisherige
    # Verhalten byte-identisch: Skins werden unter ihrem REPOS_ROOT-relativen Pfad
    # (iil-klickdummy/.../skins/<name>.css) ausgeliefert. Wird via --skin-base
    # gesetzt (z. B. "/genesor/skins"), dann wird NUR der Basename verwendet:
    # "<skin-base>/<name>.css" — für einen self-contained Portal-Build, bei dem die
    # 4 Skin-CSS-Dateien neben dem Genesor-Site liegen.
    skin_base: str = ""
    # Repos, deren echte Mockup-HTMLs unter "/kd/<repo>/..." einvendoriert
    # ausgeliefert werden (z. B. iil-pet-portal/kd/). Steht ein Repo hier, wird in
    # url_for_path() dem ROOT-relativen Pfad ein "/kd"-Präfix vorangestellt, sodass
    # der Link auf die vendored Kopie statt auf das (auf iil.pet nicht ausgelieferte)
    # Original zeigt. Leere Menge (Default) → byte-identisch zu früher.
    vendored_repos: set = field(default_factory=set)

    @property
    def genesor_out(self) -> Path:
        if self._genesor_out is not None:
            return self._genesor_out
        return self.repos_root / "genesor"

    @genesor_out.setter
    def genesor_out(self, value: Path | None) -> None:
        self._genesor_out = value


# ---------------------------------------------------------------------------
# Modul-Singleton + Accessoren
# ---------------------------------------------------------------------------

# Modul-weite Konfigurationsinstanz. Wird in main() via set_cfg() neu gesetzt.
# Default: byte-identisches Verhalten zu den früheren bare Globals.
_cfg: GenesorConfig = GenesorConfig()


def get_cfg() -> GenesorConfig:
    """Gibt die aktuell aktive GenesorConfig-Instanz zurück.

    Alle genesor-Sub-Module rufen get_cfg() anstatt _cfg direkt zu importieren,
    damit main() den Singleton per set_cfg(new_cfg) austauschen kann ohne dass
    Sub-Module eine veraltete Referenz halten.
    """
    return _cfg


def set_cfg(new_cfg: GenesorConfig) -> None:
    """Ersetzt den Modul-Singleton (wird in main() nach argparse aufgerufen)."""
    global _cfg
    _cfg = new_cfg


# ---------------------------------------------------------------------------
# Backward-compat-Aliases (nicht mehr mutiert; für externe Leser)
# ---------------------------------------------------------------------------

REPOS_ROOT = _cfg.repos_root
GENESOR_OUT = _cfg.genesor_out
BASE_URL = _cfg.base_url
SKIN_BASE = _cfg.skin_base
VENDORED_REPOS: set[str] = _cfg.vendored_repos


# ---------------------------------------------------------------------------
# URL-Helpers (ausschließlich config-abhängig)
# ---------------------------------------------------------------------------


def _base_prefix() -> str:
    """Normalisiert BASE_URL zu einem Präfix ohne Trailing-Slash ("/"→"")."""
    return get_cfg().base_url.rstrip("/")


def _skin_url(rel: str) -> str:
    """Skin-Pfad (REPOS_ROOT-relativ) → finale URL.

    SKIN_BASE leer  → "<base_prefix>/<rel>"  (byte-identisch zu früher).
    SKIN_BASE gesetzt → "<skin_base>/<basename>"  (nur Dateiname, z. B.
                        "/genesor/skins/okwobis-look.css").
    """
    cfg = get_cfg()
    if cfg.skin_base:
        return cfg.skin_base.rstrip("/") + "/" + rel.rsplit("/", 1)[-1]
    return _base_prefix() + "/" + rel


# ---------------------------------------------------------------------------
# Modul-Konstanten (keine Abhängigkeiten; konsumiert von mehreren Modulen)
# ---------------------------------------------------------------------------

MOCKUP_PRIO_NAMES = ("index.html", "shell.html")

# Skin-Pfade relativ zu REPOS_ROOT (ohne BASE_URL-Präfix). Der Sentinel
# "__greenfield" ist KEIN Pfad und wird nie präfixiert.
SKIN_LIBRARY_REL: list[tuple[str, str]] = [
    ("__greenfield", "Greenfield (Default)"),
    (
        "iil-klickdummy/src/iil_klickdummy/snippets/skins/okwobis-look.css",
        "OK.Wobis-Look (Win-Forms)",
    ),
    (
        "iil-klickdummy/src/iil_klickdummy/snippets/skins/prosoz-look.css",
        "Prosoz-Look (Web-Verwaltung)",
    ),
    (
        "iil-klickdummy/src/iil_klickdummy/snippets/skins/arriba-look.css",
        "ARRIBA-Look (AVA-Engineering)",
    ),
    (
        "iil-klickdummy/src/iil_klickdummy/snippets/skins/bayernid-look.css",
        "BayernID-Look (Bürger-modern)",
    ),
]

_DOMAIN_STYLES = {
    "public-admin": {
        "accent": "#0050a3",
        "accent_bg": "#e3f0ff",
        "font_h": "Georgia, 'Times New Roman', serif",
    },
    "saas": {
        "accent": "#2563eb",
        "accent_bg": "#eff6ff",
        "font_h": "-apple-system, 'Segoe UI', system-ui, sans-serif",
    },
    "konzern-pilot": {
        "accent": "#7c2d12",
        "accent_bg": "#fff4ed",
        "font_h": "-apple-system, system-ui, sans-serif",
    },
    "forschung": {
        "accent": "#0d9488",
        "accent_bg": "#f0fdfa",
        "font_h": "-apple-system, system-ui, sans-serif",
    },
    "default": {
        "accent": "#374151",
        "accent_bg": "#f3f4f6",
        "font_h": "-apple-system, system-ui, sans-serif",
    },
    # Alias-Migration (siehe ADR-218 Rev 3)
    "lra-pilot": {
        "accent": "#0050a3",
        "accent_bg": "#e3f0ff",
        "font_h": "Georgia, 'Times New Roman', serif",
    },
}

_BUERGER_POOL = [
    {
        "vorname": "Sabine",
        "nachname": "Müller",
        "gebdatum": "1972-03-14",
        "adresse": "Friedrichstr. 12, 79541 Lörrach",
        "kanal": "postbox",
    },
    {
        "vorname": "Klaus",
        "nachname": "Schmidt",
        "gebdatum": "1985-08-02",
        "adresse": "Bahnhofstr. 7, 79588 Efringen",
        "kanal": "email",
    },
    {
        "vorname": "Ayşe",
        "nachname": "Yilmaz",
        "gebdatum": "1990-11-29",
        "adresse": "Hauinger Str. 33, 79541 Lörrach",
        "kanal": "brief",
    },
    {
        "vorname": "Dimitri",
        "nachname": "Petrov",
        "gebdatum": "1968-05-21",
        "adresse": "Lindenplatz 2, 79576 Weil",
        "kanal": "postbox",
    },
    {
        "vorname": "Maria",
        "nachname": "Weber",
        "gebdatum": "1978-09-09",
        "adresse": "Mühlenweg 18, 79585 Steinen",
        "kanal": "email",
    },
    {
        "vorname": "Jens",
        "nachname": "Lange",
        "gebdatum": "1995-02-17",
        "adresse": "Im Sandgrund 5, 79540 Lörrach",
        "kanal": "postbox",
    },
]

# Akten-Typ + KD-Hint: kd_hint wird zur Render-Zeit gegen die bekannten KDs
# gematcht. Wenn ein KD existiert (z. B. wohngeld), wird die Akten-Zeile mit
# data-target-kd + data-target-url versehen → Sprung-CTA im Akte-Modal.
_AKTEN_PROFIL_POOL = [
    # kd_hint = KD-Name (cross-repo möglich); entry = Spec-Screen-ID, auf die der
    # Ziel-KD bei externem Sprung initialisieren soll (für *bestehende* Akten;
    # statt Default = „neuer Antrag/Eingang"). Hash-Routing: ?#screen-<entry>.
    {
        "typ": "Antrag Wohngeld",
        "prefix": "WOH",
        "kd_hint": "wohngeld",
        "entry": "antragsdaten",
    },
    {"typ": "Bauantrag", "prefix": "BAU", "kd_hint": None, "entry": None},
    {
        "typ": "UVG-Erstantrag",
        "prefix": "UVG",
        "kd_hint": "uvg",
        "entry": "antragsdaten_uvg",
    },
    {
        "typ": "Asyl-Folgeantrag",
        "prefix": "ASY",
        "kd_hint": "asyl",
        "entry": "vorgangs_uebersicht",
    },
    {"typ": "Bewohnerparkausweis", "prefix": "BPK", "kd_hint": None, "entry": None},
    {"typ": "Hundesteuer", "prefix": "HDS", "kd_hint": None, "entry": None},
]

_FRONTMATTER_RE = __import__("re").compile(
    r"^---\s*\n(.*?)\n---",
    __import__("re").DOTALL | __import__("re").MULTILINE,
)

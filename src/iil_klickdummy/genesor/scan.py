"""Repo-/Spec-Discovery — Specs, Contracts, ADR-Meta, UCs, Git-Meta scannen.

Extrahiert aus lineage.py (KONZ-003 Empf-1, PR3) — reine Code-Motion.
"""

from __future__ import annotations

import re
import sys
import yaml
from pathlib import Path
from .config import MOCKUP_PRIO_NAMES, _FRONTMATTER_RE, _base_prefix, get_cfg
from ..read_model import validate_spec


def _warn_schema_violations(spec_path: Path, data: dict) -> None:
    """Warnt (stderr) bei Schema-Verstoessen, schliesst die KD NIE aus (AD-6/#103).

    Bewusst nicht-fatal: der genesor-Scan laeuft fleet-weit ueber alle Repos;
    ein `sys.exit` bei der ersten nicht-konformen Spec wuerde die Cross-Repo-
    Lineage fuer alle Repos gleichzeitig reissen (M28-2-Risiko). Die Sink-
    Haertung (html.escape/`_safe_seg` in render_uc.py/lineage.py, PR #125)
    bleibt die eigentliche Verteidigungslinie; das hier macht Verstoesse nur
    zusaetzlich sichtbar.
    """
    for err in validate_spec(data):
        print(f"WARN: {spec_path}: Schema-Verstoß: {err}", file=sys.stderr)


# Paket-Elternverzeichnis (src/ im Repo bzw. site-packages/ installiert) — diese
# Datei liegt eine Ebene tiefer als lineage.py, daher drei .parent statt zwei.
ROOT = Path(__file__).resolve().parent.parent.parent


MOCKUPS_DIR = ROOT / "docs" / "01-architektur" / "mockups"


CONTRACTS_DIR = ROOT / "docs" / "01-architektur" / "contracts"


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
        f
        for f in kd_dir.glob("*.html")
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
        rel = str(p.relative_to(get_cfg().repos_root))
    except ValueError:
        return None
    if get_cfg().vendored_repos and rel.split("/", 1)[0] in get_cfg().vendored_repos:
        return _base_prefix() + "/kd/" + rel
    return _base_prefix() + "/" + rel


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


def read_fv_inventur(repo_dir: Path) -> dict[str, dict]:
    """Returnt {fv_id: fv_dict} aus docs/inventur/fv-inventur.yaml."""
    path = repo_dir / "docs" / "inventur" / "fv-inventur.yaml"
    if not path.is_file():
        return {}
    try:
        data = yaml.safe_load(path.read_text("utf-8")) or {}
    except yaml.YAMLError:
        return {}
    return {
        fv["id"]: fv
        for fv in data.get("fachverfahren", [])
        if isinstance(fv, dict) and "id" in fv
    }


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


# Org-Registry-Cache, keyed nach canonical.yaml-Pfad (repos_root kann sich via
# set_cfg ändern — Tests!). None-Werte werden mitgecacht (kein platform-Checkout).
_ORG_REGISTRY_CACHE: dict[str, dict | None] = {}


def get_org_registry() -> dict | None:
    """Org-Mapping aus der platform-Registry-SSoT (ADR-234: canonical.yaml).

    Liest ``<repos_root>/platform/registry/canonical.yaml`` →
    ``{repo_owner, owner_prefix_rules, default_owner, app_display_names}``.
    ``None`` wenn kein platform-Checkout existiert ODER ``owner_prefix_rules``
    fehlen (ältere platform-Version: ``repo_owner`` allein ist ein unvollständiges
    Mapping — meiki-/ttz-/…-Repos fielen sonst auf den Default durch). Aufrufer
    nutzen dann ihre Code-Heuristik als Fallback.
    """
    path = get_cfg().repos_root / "platform" / "registry" / "canonical.yaml"
    key = str(path)
    if key in _ORG_REGISTRY_CACHE:
        return _ORG_REGISTRY_CACHE[key]
    reg: dict | None = None
    try:
        meta = (yaml.safe_load(path.read_text(encoding="utf-8")) or {}).get(
            "meta"
        ) or {}
        rules = meta.get("owner_prefix_rules") or []
        owners = meta.get("repo_owner") or {}
        if rules:
            reg = {
                "repo_owner": owners,
                "owner_prefix_rules": rules,
                "default_owner": (meta.get("server") or {}).get("github_org")
                or "achimdehnert",
                "app_display_names": meta.get("app_display_names") or {},
            }
    except (OSError, yaml.YAMLError):
        reg = None
    _ORG_REGISTRY_CACHE[key] = reg
    return reg


def detect_org(repo_name: str) -> str:
    """Org für ein Repo — aus platform/registry/canonical.yaml (SSoT, ADR-234).

    Ohne platform-Checkout greift die historische Code-Heuristik
    (:func:`_detect_org_fallback`); die Registry-Werte reproduzieren sie 1:1.
    """
    reg = get_org_registry()
    if reg is None:
        return _detect_org_fallback(repo_name)
    owner = reg["repo_owner"].get(repo_name)
    if owner:
        return str(owner)
    for rule in reg["owner_prefix_rules"]:
        if repo_name.startswith(str(rule.get("prefix") or "")):
            return str(rule.get("owner"))
    return str(reg["default_owner"])


def _detect_org_fallback(repo_name: str) -> str:
    """Code-Heuristik für Installationen ohne platform-Checkout (Stand 2026-06)."""
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
        return (
            ", ".join(g["pilot_lra"])
            if isinstance(g["pilot_lra"], list)
            else str(g["pilot_lra"])
        )
    if "pilot_stakeholder" in g:
        return str(g["pilot_stakeholder"])[:50]
    return fallback_org


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
        _warn_schema_violations(spec_path, data)
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


def adr_local(data: dict) -> str | None:
    """Holt meiki:ADR-NNN aus adr.local."""
    adr = data.get("adr") or {}
    return adr.get("local")


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
    if not get_cfg().repos_root.is_dir():
        return out
    for repo_dir in sorted(get_cfg().repos_root.iterdir()):
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
            _warn_schema_violations(spec_path, data)
            data = _normalize_spec_aliases(data)
            adr_local = (data.get("adr", {}) or {}).get("local")
            extra = adr_meta.get(adr_local, {}) if adr_local else {}
            out.append(
                {
                    "org": org,
                    "repo": repo_name,
                    "kd": kd_name,
                    "path": spec_path,
                    "data": data,
                    "kind": "spec",
                    "adr_meta": extra,
                }
            )

        # 2. meiki-Konvention: docs/01-architektur/mockups/<name>-klickdummy/screens-spec.yaml
        for spec_path in repo_dir.glob(
            "docs/01-architektur/mockups/*-klickdummy/screens-spec.yaml"
        ):
            kd_name = spec_path.parent.name.removesuffix("-klickdummy")
            seen_kd_dirs.add(spec_path.parent)
            try:
                data = yaml.safe_load(spec_path.read_text("utf-8")) or {}
            except yaml.YAMLError:
                continue
            _warn_schema_violations(spec_path, data)
            data = _normalize_spec_aliases(data)
            adr_local = (data.get("adr", {}) or {}).get("local")
            extra = adr_meta.get(adr_local, {}) if adr_local else {}
            out.append(
                {
                    "org": org,
                    "repo": repo_name,
                    "kd": kd_name,
                    "path": spec_path,
                    "data": data,
                    "kind": "spec",
                    "adr_meta": extra,
                }
            )

        # 3. F11: Render-only-KDs ohne Spec (I1-Verstoß-Kandidaten)
        kd_root = repo_dir / "klickdummy"
        if kd_root.is_dir():
            # 3a. Subdirs ohne screens-spec.yaml
            for sub in sorted(kd_root.iterdir()):
                if (
                    not sub.is_dir()
                    or sub in seen_kd_dirs
                    or sub.name.startswith(("_", "."))
                ):
                    continue
                # Hat das Subdir eine HTML-Datei? Dann ist es ein render-only-KD.
                htmls = [
                    h
                    for h in sub.glob("*.html")
                    if not h.name.startswith(("_", "README"))
                ]
                if htmls:
                    out.append(
                        {
                            "org": org,
                            "repo": repo_name,
                            "kd": sub.name,
                            "path": sub
                            / "screens-spec.yaml",  # virtuell, existiert nicht
                            "data": {
                                "_render_only": True,
                                "_html_files": [str(h.name) for h in htmls],
                            },
                            "kind": "render-only-subdir",
                        }
                    )
            # 3b. HTML direkt in klickdummy/ (risk-hub-Pattern)
            for html_file in sorted(kd_root.glob("*.html")):
                if html_file.name.startswith(("_", "README")):
                    continue
                kd_name = html_file.stem
                out.append(
                    {
                        "org": org,
                        "repo": repo_name,
                        "kd": kd_name,
                        "path": html_file,
                        "data": {
                            "_render_only_inline": True,
                            "_html_file": html_file.name,
                        },
                        "kind": "render-only-inline",
                    }
                )

    return out


def _load_iil_apps_index() -> dict[str, dict]:
    """Pilot-Memo §0: lädt iil-relaunch/apps.json und indiziert by repo-Name.

    Liefert pro repo einen dict mit ``urls.{prod,staging,dev}`` + ``name``.
    Fallback bei fehlender Datei: leeres dict (kein Crash).
    """
    import json

    candidates = [
        get_cfg().repos_root / "iil-relaunch" / "apps.json",
        get_cfg().repos_root / "platform" / "static-sites" / "iil.pet" / "apps.json",
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

    repo_path = get_cfg().repos_root / repo
    if not (repo_path / ".git").exists():
        return {}
    try:
        url = subprocess.check_output(
            ["git", "-C", str(repo_path), "remote", "get-url", "origin"],
            stderr=subprocess.DEVNULL,
            text=True,
            timeout=2,
        ).strip()
    except (
        subprocess.CalledProcessError,
        subprocess.TimeoutExpired,
        FileNotFoundError,
    ):
        return {}
    m = re.match(
        r"(?:git@github\.com:|https://github\.com/)([^/]+)/([^/.]+?)(?:\.git)?$", url
    )
    if not m:
        return {}
    org, gh_repo = m.group(1), m.group(2)
    # Aktuell ausgecheckter Branch (= dort liegen die committed/pushed UCs)
    try:
        branch = subprocess.check_output(
            ["git", "-C", str(repo_path), "rev-parse", "--abbrev-ref", "HEAD"],
            stderr=subprocess.DEVNULL,
            text=True,
            timeout=2,
        ).strip()
    except (
        subprocess.CalledProcessError,
        subprocess.TimeoutExpired,
        FileNotFoundError,
    ):
        branch = "main"
    if branch == "HEAD":  # detached HEAD
        branch = "main"
    # Has-Upstream-Check: prüft ob ``refs/remotes/origin/<branch>`` lokal
    # existiert (wird durch ``git push`` automatisch angelegt, auch ohne ``-u``).
    # Robuster als ``@{u}``, das die branch.<name>.remote-Config braucht.
    has_upstream = (
        subprocess.run(
            [
                "git",
                "-C",
                str(repo_path),
                "rev-parse",
                "--verify",
                f"refs/remotes/origin/{branch}",
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=2,
        ).returncode
        == 0
    )
    try:
        tracked = set(
            subprocess.check_output(
                ["git", "-C", str(repo_path), "ls-files"],
                stderr=subprocess.DEVNULL,
                text=True,
                timeout=10,
            )
            .strip()
            .splitlines()
        )
    except (
        subprocess.CalledProcessError,
        subprocess.TimeoutExpired,
        FileNotFoundError,
    ):
        tracked = set()
    return {
        "org": org,
        "gh_repo": gh_repo,
        "branch": branch,
        "has_upstream": has_upstream,
        "tracked_files": tracked,
    }


_REPO_META_CACHE: dict[str, dict] = {}


def _repo_meta_cached(repo: str) -> dict:
    if repo not in _REPO_META_CACHE:
        _REPO_META_CACHE[repo] = _git_repo_meta(repo)
    return _REPO_META_CACHE[repo]

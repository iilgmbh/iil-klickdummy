"""Auto-Publish — git commit/push generierter _auto/-Files, GitHub-URLs.

Extrahiert aus lineage.py (KONZ-003 Empf-1, PR3) — reine Code-Motion.
"""
from __future__ import annotations

from pathlib import Path
from .config import _cfg
from .scan import _repo_meta_cached


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


def _repo_of_path(p: Path) -> str | None:
    """Repo-Name aus absolutem Pfad: ``~/github/<repo>/...`` → ``<repo>``."""
    try:
        rel = p.relative_to(_cfg.repos_root)
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
    repo_path = _cfg.repos_root / repo
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

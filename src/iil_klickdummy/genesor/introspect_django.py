"""Django-Introspection-Helfer für Genesor Implementation-Briefs (KONZ-003 Empf-1).

Enthält:
  - _inspect_django_models  — AST-Parse aller apps/*/models.py
  - _detect_tenant_pattern  — ADR-072 Multi-Tenant-Erkennung
  - _detect_auth_user_model — AUTH_USER_MODEL aus settings lesen
  - _inspect_dev_run        — Dev-Run-Hinweise (Port, DB, compose)
  - _inspect_infra_context  — INFRASTRUCTURE.md parsed + ss-Snapshot

Abhängigkeiten: nur stdlib + .config (get_cfg).
Keine Rückabhängigkeiten auf andere genesor-Module.
"""

from __future__ import annotations

from .config import get_cfg


def _inspect_django_models(repo: str) -> dict[str, dict]:
    """AST-Parse aller `apps/*/models.py` → ``{app_label.ModelName: {fields, file}}``.

    Liefert pro Model die Field-Definitionen mit Type-Name und kwargs (best-effort).
    Lesson learned Iter-1: ohne diesen Schritt rät der Brief Model-Namen und
    User-Owner-Pattern, was zu Refactor-Aufwand führt.
    """
    import ast

    result: dict[str, dict] = {}
    repo_path = get_cfg().repos_root / repo
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
    with_tenant = [
        k for k, v in models_inspected.items() if "tenant_id" in v.get("fields", {})
    ]
    return {
        "active": len(with_tenant) >= 3,
        "count": len(with_tenant),
        "models": with_tenant[:10],
        "rationale": (
            "ADR-072 Multi-Tenant via BigIntegerField (kein FK). Neue Models in diesem Repo "
            "sollten `tenant_id`-Field + Index ergänzen; Views filtern via "
            "`core.TenantUser.objects.filter(tenant_id=..., user=request.user, is_active=True)`."
        )
        if len(with_tenant) >= 3
        else "",
    }


def _detect_auth_user_model(repo: str) -> str:
    """Liest ``AUTH_USER_MODEL`` aus ``config/settings/base.py`` (oder Fallback)."""
    import re

    repo_path = get_cfg().repos_root / repo
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
    return "auth.User"  # Django-Default


def _inspect_dev_run(repo: str) -> dict:
    """Pilot-Lesson-Learned #6 — extrahiert dev_run-Hinweise aus dem Repo.

    Sucht ``bin/start-dev.sh``, ``docker-compose*.yml``, ``requirements.txt``,
    ``pyproject.toml`` und gibt Port, Command, DB-Port, Deps-Drift zurück.
    Leere/teilweise Ergebnisse sind erlaubt — Brief zeigt nur was tatsächlich
    gefunden wurde.
    """
    import re

    repo_path = get_cfg().repos_root / repo
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
        m = re.search(r"\[tool\.poetry\.dependencies\](.+?)(?:\n\[|\Z)", pp_text, re.S)
        if m:
            pp_deps = set()
            for line in m.group(1).splitlines():
                ln = line.strip()
                if not ln or ln.startswith("#") or ln.startswith("python"):
                    continue
                mm = re.match(r"([A-Za-z0-9_\-]+)\s*=", ln)
                if mm:
                    pp_deps.add(mm.group(1).lower().replace("_", "-"))
            req_deps = set()
            for line in req_text.splitlines():
                ln = line.strip()
                if not ln or ln.startswith("#"):
                    continue
                mm = re.match(r"([A-Za-z0-9_\-]+)", ln)
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
        out["test_url"] = (
            f"http://localhost:{port}/healthz/  # ggf. <app-mount>/healthz/"
        )
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
        m = re.search(r"\*\*Public IPv4:\*\*\s*`([\d.]+)`", text)
        if m:
            out["server_public_ipv4"] = m.group(1)
        m = re.search(r"\*\*Server:\*\*\s*`?([\w\-]+)`?", text)
        if m:
            out["server_name"] = m.group(1)
        # Cloud-Provider
        m = re.search(r"\((Hetzner|AWS|GCP|Azure)[^)]*\)", text, re.I)
        if m:
            out["cloud_provider"] = m.group(1).lower() + "-cloud"
        # Cloud-Firewall-Block
        m = re.search(r"firewall[-_]?\d+\s*\(id=(\d+)\)", text)
        if m:
            out["cloud_firewall_id"] = int(m.group(1))
            out["cloud_firewall_name"] = "firewall-1"
        m = re.search(r"erlauben nur\s+\*\*([\d,\s\-+]+)", text)
        if m:
            ports = re.findall(r"\d+", m.group(1))
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
            m = re.search(
                r"(\d+\.\d+\.\d+\.\d+):(80\d{2}|87\d{2}|85\d{2}|81\d{2})\s", line
            )
            if m:
                bind = m.group(1)
                p = int(m.group(2))
                live.append({"port": p, "bind": bind})
        if live:
            # Dedupe nach (bind, port)
            seen = set()
            out["live_listening_ports"] = [
                x
                for x in live
                if (x["bind"], x["port"]) not in seen
                and not seen.add((x["bind"], x["port"]))
            ][:25]
    except (OSError, subprocess.TimeoutExpired):
        pass
    return out

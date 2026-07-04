"""Tests für den Browser-Versions-Switcher (registry: Snapshots aus Git-History).

Vorher war #ver-select eine UI-Attrappe: discover_versions() existierte,
wurde aber nie aufgerufen. Jetzt: render_browser_html(repo_root=...) bettet
die Historie ein und schreibt shell.html-Snapshots früherer Versionen.
"""

from __future__ import annotations

import subprocess
import textwrap

from iil_klickdummy import registry


def _git(repo, *args):
    subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        capture_output=True,
        text=True,
    )


def _spec(version: str) -> str:
    return textwrap.dedent(f"""
        spec_id: demo:klickdummy-spec-demo
        spec_version: "{version}"
        class: mock
        title: Demo-KD
    """)


def _make_repo_with_history(tmp_path):
    repo = tmp_path / "repo"
    kd = repo / "klickdummy" / "demo"
    kd.mkdir(parents=True)
    _git(repo, "init", "-q")
    _git(repo, "config", "user.email", "test@example.invalid")
    _git(repo, "config", "user.name", "Test")
    (kd / "screens-spec.yaml").write_text(_spec("0.1"), encoding="utf-8")
    (kd / "shell.html").write_text("<html>version-eins</html>", encoding="utf-8")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "v0.1")
    (kd / "screens-spec.yaml").write_text(_spec("0.2"), encoding="utf-8")
    (kd / "shell.html").write_text("<html>version-zwei</html>", encoding="utf-8")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "v0.2")
    return repo


def test_should_embed_version_history_and_write_snapshots(tmp_path):
    repo = _make_repo_with_history(tmp_path)
    kds = registry.discover_klickdummies(repo)
    assert len(kds) == 1 and kds[0].spec_version == "0.2"
    out = tmp_path / "site" / "browser.html"
    registry.render_browser_html(kds, out, repo_root=repo)

    snap = out.parent / "klickdummy-versions" / "demo" / "0.1" / "shell.html"
    assert snap.exists(), "shell.html-Snapshot der Vorversion fehlt"
    assert "version-eins" in snap.read_text(encoding="utf-8")

    html = out.read_text(encoding="utf-8")
    assert '"versions"' in html
    assert '"spec_version": "0.1"' in html
    assert "klickdummy-versions/demo/0.1/shell.html" in html


def test_head_version_should_not_become_snapshot(tmp_path):
    repo = _make_repo_with_history(tmp_path)
    kds = registry.discover_klickdummies(repo)
    out = tmp_path / "site" / "browser.html"
    registry.render_browser_html(kds, out, repo_root=repo)
    assert not (out.parent / "klickdummy-versions" / "demo" / "0.2").exists()


def test_should_render_without_git_history(tmp_path):
    # KD-Verzeichnis ohne .git → keine Versionen, kein Crash (Altverhalten)
    repo = tmp_path / "repo"
    kd = repo / "klickdummy" / "demo"
    kd.mkdir(parents=True)
    (kd / "screens-spec.yaml").write_text(_spec("0.1"), encoding="utf-8")
    (kd / "shell.html").write_text("<html>x</html>", encoding="utf-8")
    kds = registry.discover_klickdummies(repo)
    out = tmp_path / "browser.html"
    registry.render_browser_html(kds, out, repo_root=repo)
    html = out.read_text(encoding="utf-8")
    assert '"versions": []' in html
    assert not (tmp_path / "klickdummy-versions").exists()


def test_template_has_version_select_handler():
    tmpl = (
        registry.files("iil_klickdummy.snippets") / "browser" / "browser.html.tmpl"
    ).read_text(encoding="utf-8")
    assert "onSelectVersion" in tmpl
    assert "populateVersions" in tmpl
    # historische Snapshots laden read-only, ohne Feedback-Widget
    assert "ohne ?feedback=on" in tmpl


def test_should_neutralize_script_break_in_embedded_json(tmp_path):
    """S-01: ein Klickdummy-Titel mit `</script>` darf nicht aus der JSON-Insel
    ausbrechen. Der HTML-Parser beendet jedes <script> (auch application/json) an
    einem literalen </script>; registry escaped daher </ zu <\\/ beim Einbetten."""
    repo = tmp_path / "repo"
    kd = repo / "klickdummy" / "xss"
    kd.mkdir(parents=True)
    payload_title = "x</script><script>window.__XSS__=1</script>"
    spec = (
        "spec_id: demo:klickdummy-spec-xss\n"
        'spec_version: "0.1"\n'
        "class: mock\n"
        f'title: "{payload_title}"\n'
    )
    (kd / "screens-spec.yaml").write_text(spec, encoding="utf-8")
    (kd / "shell.html").write_text("<html>x</html>", encoding="utf-8")
    kds = registry.discover_klickdummies(repo)
    out = tmp_path / "browser.html"
    registry.render_browser_html(kds, out)
    html = out.read_text(encoding="utf-8")
    # Das rohe, ausbrechende Payload darf NICHT im Output stehen …
    assert "</script><script>window.__XSS__" not in html
    # … sondern nur in escapeter Form (</ → <\/).
    assert "<\\/script><script>window.__XSS__" in html


def test_should_use_json_island_not_inline_const(tmp_path):
    """N1: Daten stehen in einer <script type=application/json>-Insel + JSON.parse,
    nicht als `const KLICKDUMMIES = {…}`-Zuweisung (die alte, ausbruchsanfällige Form)."""
    repo = tmp_path / "repo"
    kd = repo / "klickdummy" / "demo"
    kd.mkdir(parents=True)
    (kd / "screens-spec.yaml").write_text(_spec("0.1"), encoding="utf-8")
    (kd / "shell.html").write_text("<html>x</html>", encoding="utf-8")
    kds = registry.discover_klickdummies(repo)
    out = tmp_path / "browser.html"
    registry.render_browser_html(kds, out)
    html = out.read_text(encoding="utf-8")
    assert 'type="application/json" data-testid="kd-data"' in html
    assert "JSON.parse(document.getElementById('kd-data')" in html

"""Regressionstests für Issue #163: klickdummy-sync Duplikat-Keys.

`adr_entries()` nutzte `repo_root.rglob("ADR-*.md")` ohne Pfad-Filter — Kopien in
versteckten Verzeichnissen (stale Agent-Worktrees unter `.claude/worktrees/`)
wurden mitgefunden. Zwei Spec-Dateien im selben KD-Verzeichnis (`screens-spec.yaml`
+ alte `spec.yaml`) erzeugen zusätzlich zwei Entries mit demselben `entry_key`.
Beides landete reihenfolgeabhängig (last-write-wins) im Orchestrator-Store.
"""

from __future__ import annotations

import pathlib

from iil_klickdummy import sync_to_orchestrator as sync_mod


# ------------------------------------------------- _is_ignored_source


def test_should_ignore_hidden_directory_components():
    assert sync_mod._is_ignored_source(
        pathlib.Path(".claude/worktrees/agent-x/docs/adr/ADR-100-foo.md")
    )


def test_should_ignore_node_modules():
    assert sync_mod._is_ignored_source(pathlib.Path("node_modules/pkg/ADR-1.md"))


def test_should_ignore_klickdummy_archive():
    assert sync_mod._is_ignored_source(
        pathlib.Path("klickdummy/archive/old/screens-spec.yaml")
    )


def test_should_not_ignore_canonical_adr_path():
    assert not sync_mod._is_ignored_source(pathlib.Path("docs/adr/ADR-100-foo.md"))


# ------------------------------------------------- _version_sort_key


def test_should_sort_semver_like_versions_numerically():
    assert sync_mod._version_sort_key("0.2") > sync_mod._version_sort_key("0.1")
    assert sync_mod._version_sort_key("10") > sync_mod._version_sort_key("9")


# ------------------------------------------------- adr_entries() rglob filter


def test_should_skip_adr_copy_in_worktree_directory(tmp_path):
    canon = tmp_path / "docs" / "adr"
    canon.mkdir(parents=True)
    (canon / "ADR-100-foo.md").write_text(
        'tags: [klickdummy]\ntitle: "Foo"\n\nKanon.', encoding="utf-8"
    )
    stale = tmp_path / ".claude" / "worktrees" / "agent-x" / "docs" / "adr"
    stale.mkdir(parents=True)
    (stale / "ADR-100-foo.md").write_text(
        'tags: [klickdummy]\ntitle: "Foo"\n\nStale (divergiert).', encoding="utf-8"
    )

    entries = sync_mod.adr_entries(tmp_path, "org", "repo")

    assert len(entries) == 1
    assert entries[0]["_source_path"] == "docs/adr/ADR-100-foo.md"


# ------------------------------------------------- _dedup_entries()


def _adr_entry(key, content, source_path):
    return dict(
        entry_key=key,
        entry_type="decision",
        title="t",
        content=content,
        tags=[],
        agent="a",
        _source_path=source_path,
    )


def _kd_entry(key, content, version):
    return dict(
        entry_key=key,
        entry_type="repo_context",
        title="t",
        content=content,
        tags=[],
        agent="a",
        _source_path="klickdummy/x/screens-spec.yaml",
        _precedence_version=version,
    )


def test_should_dedup_adr_entries_preferring_shortest_path():
    entries = [
        _adr_entry("k", "kanon", "docs/adr/ADR-100-foo.md"),
        _adr_entry("k", "stale", ".claude/worktrees/agent-x/docs/adr/ADR-100-foo.md"),
    ]
    out = sync_mod._dedup_entries(entries)
    assert len(out) == 1
    assert out[0]["content"] == "kanon"
    assert "_source_path" not in out[0]


def test_should_dedup_klickdummy_entries_preferring_highest_version():
    entries = [
        _kd_entry("k", "old", "0.1"),
        _kd_entry("k", "new", "0.2"),
    ]
    out = sync_mod._dedup_entries(entries)
    assert len(out) == 1
    assert out[0]["content"] == "new"


def test_should_warn_on_content_divergence(capsys):
    entries = [
        _adr_entry("k", "kanon", "docs/adr/ADR-100-foo.md"),
        _adr_entry("k", "stale", ".claude/worktrees/agent-x/docs/adr/ADR-100-foo.md"),
    ]
    sync_mod._dedup_entries(entries)
    captured = capsys.readouterr()
    assert "WARN" in captured.err
    assert "divergent" in captured.err


def test_should_not_warn_when_content_identical(capsys):
    entries = [
        _adr_entry("k", "same", "docs/adr/ADR-100-foo.md"),
        _adr_entry("k", "same", ".claude/worktrees/agent-x/docs/adr/ADR-100-foo.md"),
    ]
    sync_mod._dedup_entries(entries)
    captured = capsys.readouterr()
    assert "WARN" not in captured.err


def test_should_pass_through_unique_keys_unchanged():
    entries = [_adr_entry("a", "x", "p1"), _adr_entry("b", "y", "p2")]
    out = sync_mod._dedup_entries(entries)
    assert len(out) == 2


# --------------------------------------- Issue #188: Dedup über Repo-Grenzen
#
# `sync_repo()` deduplizierte pro Repo — zwei Repo-Roots, die dasselbe
# org/repo-Paar liefern (Kopie oder stale Worktree in der `--repos`-Liste),
# erzeugten trotzdem doppelte entry_keys im NDJSON. Lauf 2026-07-24: 143 Zeilen
# → 134 eindeutige Keys, und bei last-write-wins gewann jeweils die ÄLTERE Zeile.


def test_should_keep_internal_fields_when_dedup_disabled(tmp_path):
    """`dedup=False` muss die Präzedenz-Felder erhalten — sonst kann der
    aggregierte Lauf die neueste Version nicht mehr bestimmen."""
    (tmp_path / "docs" / "adr").mkdir(parents=True)
    (tmp_path / "docs" / "adr" / "ADR-100-foo.md").write_text(
        'tags: [klickdummy]\ntitle: "Foo"\n\nBody.', encoding="utf-8"
    )

    entries = sync_mod.sync_repo(tmp_path, dedup=False)

    assert entries, "Fixture sollte mindestens einen ADR-Entry liefern"
    assert all("_source_path" in e for e in entries)


def test_should_strip_internal_fields_when_dedup_enabled(tmp_path):
    (tmp_path / "docs" / "adr").mkdir(parents=True)
    (tmp_path / "docs" / "adr" / "ADR-100-foo.md").write_text(
        'tags: [klickdummy]\ntitle: "Foo"\n\nBody.', encoding="utf-8"
    )

    entries = sync_mod.sync_repo(tmp_path)

    assert entries
    assert all("_source_path" not in e for e in entries)


def test_should_dedup_across_repo_roots_preferring_newest_version():
    """Der Realfall aus Issue #188: derselbe Klickdummy-Key aus zwei Roots,
    v0.1 NACH v0.2 emittiert. Ohne Aggregat-Dedup gewinnt beim Upsert v0.1."""
    entries = [
        _kd_entry(
            "klickdummy:achimdehnert:illustration-hub:comic-erstellen", "v2", "0.2"
        ),
        _kd_entry(
            "klickdummy:achimdehnert:illustration-hub:comic-erstellen", "v1", "0.1"
        ),
    ]

    out = sync_mod._dedup_entries(entries)

    assert len(out) == 1
    assert out[0]["content"] == "v2"


# --------------------------------------- Issue #188 Zweitbefund: Truncation


def test_should_not_mark_content_below_limit():
    assert sync_mod._content_preview("kurz", limit=10) == "kurz"


def test_should_mark_truncated_content():
    out = sync_mod._content_preview("x" * 30, limit=10)

    assert out.startswith("x" * 10)
    assert "gekürzt: 20 weitere Zeichen" in out

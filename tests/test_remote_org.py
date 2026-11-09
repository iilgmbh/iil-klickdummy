"""Issue #2: remote host changes must preserve discovery and sync identity."""

import json
import shutil
import subprocess
from pathlib import Path

import pytest

from iil_klickdummy import registry
from iil_klickdummy import sync_to_orchestrator as sync


@pytest.mark.parametrize(
    "url",
    [
        "https://github.com/Mixed-owner/repo.git",
        "https://forger.iil.pet/Mixed-owner/repo.git\n",
        "https://forge.example.invalid:8443/Mixed-owner/repo/",
        "ssh://git@forger.iil.pet:2222/Mixed-owner/repo.git",
        "ssh://git@[::1]:2222/Mixed-owner/repo.git",
        "git@forger.iil.pet:Mixed-owner/repo.git",
        "forger.iil.pet:Mixed-owner/repo",
        "https://synthetic-user:synthetic-password@forge.invalid/Mixed-owner/repo",
    ],
)
def test_should_preserve_owner_for_network_git_urls(url):
    assert registry._org_from_remote_url(url) == "Mixed-owner"


@pytest.mark.parametrize(
    "url",
    [
        "",
        "/home/owner/repo",
        "../owner/repo",
        "owner/repo",
        "C:/owner/repo",
        "C:owner/repo",
        r"C:\owner\repo",
        "file:///owner/repo",
        "https:///owner/repo",
        "https://host/owner",
        "https://host//repo",
        "https://host/owner/repo/extra",
        "https://host/owner//repo",
        "https://host/owner/repo?x=1",
        "https://host/owner/repo?",
        "https://host/owner/repo#ref",
        "https://host/owner/repo#",
        "https://bad\\host/owner/repo",
        "https://bad\x00host/owner/repo",
        "https://bad\x7fhost/owner/repo",
        "https://host/owner/repo\x1c",
        "\thttps://host/owner/repo",
        "https://host/../repo",
        "https://host/%2e%2e/repo",
        "https://host/owner/.git",
        "https://host/owner/repo\nhttps://host/other/repo",
        "https://host/owner/repo\n\n",
        "ssh://host:bad/owner/repo",
        "git@host:/owner/repo",
        "git@host:owner/repo#ref",
        "owner has spaces",
    ],
)
def test_should_not_invent_owner_from_ambiguous_or_local_paths(url):
    assert registry._org_from_remote_url(url) == "(unknown-org)"


def _git(repo, *args):
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        capture_output=True,
        text=True,
    )


@pytest.fixture
def sample_repo(tmp_path):
    repo = tmp_path / "synthetic-repo"
    kd = repo / "klickdummy" / "demo"
    kd.mkdir(parents=True)
    _git(repo, "init", "-q")
    shutil.copyfile(
        Path(__file__).parent / "fixtures" / "example-screens-spec.yaml",
        kd / "screens-spec.yaml",
    )
    (kd / "feedback-log.md").write_text(
        "| 1 | 2026-01-01 | login | Synthetic feedback |\n", encoding="utf-8"
    )
    adr = repo / "docs" / "adr"
    adr.mkdir(parents=True)
    (adr / "ADR-001-synthetic.md").write_text(
        'tags: [klickdummy]\ntitle: "Synthetic"\n\nTest only.\n', encoding="utf-8"
    )
    return repo


@pytest.mark.parametrize("org", ["iilgmbh", "meiki-lra", "ttz-lif"])
def test_should_keep_complete_ndjson_and_registry_identity_after_host_move(
    sample_repo, capsys, org
):
    outputs = []
    for remote in [
        f"https://github.com/{org}/synthetic-repo.git",
        f"https://forger.iil.pet/{org}/synthetic-repo.git",
        f"git@forger.iil.pet:{org}/synthetic-repo.git",
        f"ssh://git@forger.iil.pet:2222/{org}/synthetic-repo.git",
    ]:
        _git(sample_repo, "config", "remote.origin.url", remote)
        triples = registry.discover_cross_repo(sample_repo.parent, [sample_repo.name])
        assert len(triples) == 1 and triples[0][0] == org
        assert (
            sync.main(
                [
                    "--cross-repo",
                    "--base",
                    str(sample_repo.parent),
                    "--repos",
                    sample_repo.name,
                ]
            )
            == 0
        )
        outputs.append(capsys.readouterr().out)
    assert all(output == outputs[0] for output in outputs)
    entries = [json.loads(line) for line in outputs[0].splitlines()]
    assert {entry["entry_type"] for entry in entries} == {
        "repo_context",
        "lesson_learned",
        "decision",
    }
    assert len(entries) == 3
    for entry in entries:
        assert f":{org}:synthetic-repo:" in entry["entry_key"]
        assert f"klickdummy:org:{org}" in entry["tags"]
        if entry["entry_type"] == "repo_context":
            assert ("gov-data" in entry["tags"]) == (org in {"meiki-lra", "ttz-lif"})


def test_should_share_sync_fallback_for_missing_origin(sample_repo):
    assert sync._detect_org(sample_repo) == "(unknown-org)"
    assert (
        registry.discover_cross_repo(sample_repo.parent, [sample_repo.name])[0][0]
        == "(unknown-org)"
    )


@pytest.mark.parametrize(
    "failure",
    [
        FileNotFoundError("synthetic"),
        subprocess.TimeoutExpired("git", 5),
        UnicodeDecodeError("utf-8", b"\xff", 0, 1, "synthetic"),
        subprocess.CompletedProcess([], 1, "https://host/wrong/repo", "synthetic"),
        subprocess.CompletedProcess([], 0, "malformed", ""),
    ],
)
def test_should_use_one_fallback_without_logging_remote_on_git_failure(
    monkeypatch, capsys, tmp_path, failure
):
    def run(command, **kwargs):
        assert command == ["git", "-C", str(tmp_path), "remote", "get-url", "origin"]
        assert kwargs == {
            "check": False,
            "capture_output": True,
            "text": True,
            "timeout": 5,
        }
        if isinstance(failure, Exception):
            raise failure
        return failure

    monkeypatch.setattr(registry.subprocess, "run", run)
    assert registry._detect_org(tmp_path) == "(unknown-org)"
    assert sync._detect_org(tmp_path) == "(unknown-org)"
    captured = capsys.readouterr()
    assert captured.out == captured.err == ""

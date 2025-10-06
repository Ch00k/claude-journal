# ABOUTME: Tests for CLI commands including init command for setting up
# ABOUTME: the journal repository with git initialization and remote configuration.

from pathlib import Path

import git
import pytest

from claude_journal.cli import init_command


def test_init_command_creates_journal_directory(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that init_command creates the journal directory."""
    journal_dir = tmp_path / "journal"
    monkeypatch.setattr("claude_journal.cli.get_journals_dir", lambda: journal_dir)

    result = init_command(None)

    assert result is True
    assert journal_dir.exists()
    assert journal_dir.is_dir()


def test_init_command_initializes_git_repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that init_command initializes a git repository."""
    journal_dir = tmp_path / "journal"
    monkeypatch.setattr("claude_journal.cli.get_journals_dir", lambda: journal_dir)

    result = init_command(None)

    assert result is True
    assert (journal_dir / ".git").exists()
    repo = git.Repo(journal_dir)
    assert repo.git_dir


def test_init_command_creates_global_journal_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that init_command creates global/journal.md."""
    journal_dir = tmp_path / "journal"
    monkeypatch.setattr("claude_journal.cli.get_journals_dir", lambda: journal_dir)

    result = init_command(None)

    assert result is True
    global_journal = journal_dir / "global" / "journal.md"
    assert global_journal.exists()


def test_init_command_creates_initial_commit(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that init_command creates an initial commit."""
    journal_dir = tmp_path / "journal"
    monkeypatch.setattr("claude_journal.cli.get_journals_dir", lambda: journal_dir)

    result = init_command(None)

    assert result is True
    repo = git.Repo(journal_dir)
    commits = list(repo.iter_commits())
    assert len(commits) == 1
    assert "Initialize journal repository" in commits[0].message


def test_init_command_adds_remote_when_provided(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that init_command adds git remote when URL is provided."""
    journal_dir = tmp_path / "journal"
    monkeypatch.setattr("claude_journal.cli.get_journals_dir", lambda: journal_dir)
    remote_url = "https://example.com/repo.git"

    result = init_command(remote_url)

    assert result is True
    repo = git.Repo(journal_dir)
    assert "origin" in [r.name for r in repo.remotes]
    assert repo.remote("origin").url == remote_url


def test_init_command_warns_if_directory_exists(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that init_command returns False if journal directory already exists."""
    journal_dir = tmp_path / "journal"
    journal_dir.mkdir(parents=True)
    monkeypatch.setattr("claude_journal.cli.get_journals_dir", lambda: journal_dir)

    result = init_command(None)

    assert result is False


def test_init_command_without_remote(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that init_command works without remote URL."""
    journal_dir = tmp_path / "journal"
    monkeypatch.setattr("claude_journal.cli.get_journals_dir", lambda: journal_dir)

    result = init_command(None)

    assert result is True
    repo = git.Repo(journal_dir)
    assert len(repo.remotes) == 0

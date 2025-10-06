# ABOUTME: Tests for git operations including repository initialization, remote checks,
# ABOUTME: pull, commit, and push operations with comprehensive error handling.

from pathlib import Path

import git

from claude_journal.git_ops import get_git_repo, git_commit, git_pull, git_push, is_remote_configured


def test_get_git_repo_returns_none_for_non_git_directory(tmp_path: Path) -> None:
    """Test that get_git_repo returns None for a non-git directory."""
    result = get_git_repo(tmp_path)

    assert result is None


def test_get_git_repo_returns_repo_for_git_directory(tmp_path: Path) -> None:
    """Test that get_git_repo returns a Repo object for a git directory."""
    git.Repo.init(tmp_path)

    result = get_git_repo(tmp_path)

    assert result is not None
    assert isinstance(result, git.Repo)


def test_is_remote_configured_returns_false_when_no_remote(tmp_path: Path) -> None:
    """Test that is_remote_configured returns False when no remote exists."""
    repo = git.Repo.init(tmp_path)

    result = is_remote_configured(repo)

    assert result is False


def test_is_remote_configured_returns_true_when_origin_exists(tmp_path: Path) -> None:
    """Test that is_remote_configured returns True when origin remote exists."""
    repo = git.Repo.init(tmp_path)
    repo.create_remote("origin", "https://example.com/repo.git")

    result = is_remote_configured(repo)

    assert result is True


def test_git_pull_returns_success_false_for_non_git_directory(tmp_path: Path) -> None:
    """Test that git_pull returns failure for non-git directory."""
    success, message = git_pull(tmp_path)

    assert success is False
    assert "not a git repository" in message.lower()


def test_git_pull_returns_success_true_when_no_remote(tmp_path: Path) -> None:
    """Test that git_pull returns success when no remote is configured."""
    git.Repo.init(tmp_path)

    success, message = git_pull(tmp_path)

    assert success is True
    assert "no remote" in message.lower()


def test_git_commit_returns_success_false_for_non_git_directory(tmp_path: Path) -> None:
    """Test that git_commit returns failure for non-git directory."""
    file_path = tmp_path / "test.txt"
    file_path.write_text("test")

    success, message = git_commit(tmp_path, file_path, "Test commit")

    assert success is False
    assert "not a git repository" in message.lower()


def test_git_commit_stages_and_commits_file(tmp_path: Path) -> None:
    """Test that git_commit stages and commits a file."""
    repo = git.Repo.init(tmp_path)
    repo.config_writer().set_value("user", "name", "Test User").release()
    repo.config_writer().set_value("user", "email", "test@example.com").release()

    file_path = tmp_path / "test.txt"
    file_path.write_text("test content")

    success, message = git_commit(tmp_path, file_path, "Test commit")

    assert success is True
    assert "committed" in message.lower()
    assert len(list(repo.iter_commits())) == 1
    assert repo.head.commit.message.strip() == "Test commit"


def test_git_push_returns_success_false_for_non_git_directory(tmp_path: Path) -> None:
    """Test that git_push returns failure for non-git directory."""
    success, message = git_push(tmp_path)

    assert success is False
    assert "not a git repository" in message.lower()


def test_git_push_returns_success_true_when_no_remote(tmp_path: Path) -> None:
    """Test that git_push returns success when no remote is configured."""
    git.Repo.init(tmp_path)

    success, message = git_push(tmp_path)

    assert success is True
    assert "no remote" in message.lower()

# ABOUTME: Git operations wrapper functions for managing journal repository,
# ABOUTME: including repo access, remote checks, pull, commit, and push operations.

from pathlib import Path

import git


def get_git_repo(path: Path) -> git.Repo | None:
    """Return GitPython repo object or None if path is not a git repository."""
    try:
        return git.Repo(path)
    except git.InvalidGitRepositoryError:
        return None


def is_remote_configured(repo: git.Repo) -> bool:
    """Check if origin remote exists."""
    try:
        repo.remote("origin")
        return True
    except ValueError:
        return False


def git_pull(journals_dir: Path) -> tuple[bool, str]:
    """Pull from remote, returns (success, message)."""
    repo = get_git_repo(journals_dir)
    if repo is None:
        return False, "Not a git repository"

    if not is_remote_configured(repo):
        return True, "No remote configured, skipping pull"

    try:
        origin = repo.remote("origin")
        origin.pull()
        return True, "Successfully pulled from remote"
    except git.GitCommandError as e:
        return False, f"Pull failed: {e}"


def git_commit(journals_dir: Path, file_path: Path, message: str) -> tuple[bool, str]:
    """Stage file and commit, returns (success, message)."""
    repo = get_git_repo(journals_dir)
    if repo is None:
        return False, "Not a git repository"

    try:
        # Convert to relative path if file is within the repo
        if file_path.is_relative_to(journals_dir):
            relative_path = file_path.relative_to(journals_dir)
            repo.index.add([str(relative_path)])
        else:
            repo.index.add([str(file_path)])
        repo.index.commit(message)
        return True, "Successfully committed"
    except git.GitCommandError as e:
        return False, f"Commit failed: {e}"


def git_push(journals_dir: Path) -> tuple[bool, str]:
    """Push to remote, returns (success, message)."""
    repo = get_git_repo(journals_dir)
    if repo is None:
        return False, "Not a git repository"

    if not is_remote_configured(repo):
        return True, "No remote configured, skipping push"

    try:
        origin = repo.remote("origin")
        origin.push()
        return True, "Successfully pushed to remote"
    except git.GitCommandError as e:
        return False, f"Push failed: {e}"

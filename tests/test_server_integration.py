# ABOUTME: Integration tests for MCP server handlers testing full JournalWrite and
# ABOUTME: JournalSearch flows with git integration and error handling.

from pathlib import Path

import git
import pytest

from claude_journal.server import handle_journal_search, handle_journal_write


@pytest.mark.asyncio
async def test_journal_write_project_scope_first_write(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test JournalWrite creates project ID and journal on first write."""
    journal_dir = tmp_path / "journal"
    journal_dir.mkdir(parents=True)
    repo = git.Repo.init(journal_dir)
    repo.config_writer().set_value("user", "name", "Test User").release()
    repo.config_writer().set_value("user", "email", "test@example.com").release()

    project_dir = tmp_path / "project"
    project_dir.mkdir()

    monkeypatch.setattr("claude_journal.server.get_journals_dir", lambda: journal_dir)
    monkeypatch.setattr("claude_journal.journal.get_journals_dir", lambda: journal_dir)
    monkeypatch.setattr("claude_journal.server.Path.cwd", lambda: project_dir)

    arguments = {"content": "Implemented caching layer for improved performance", "type": "insight", "scope": "project"}

    result = await handle_journal_write(arguments)

    assert len(result) == 1
    assert "Journal entry written" in result[0].text
    assert (project_dir / ".claude" / "journal.json").exists()


@pytest.mark.asyncio
async def test_journal_write_global_scope(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test JournalWrite with global scope."""
    journal_dir = tmp_path / "journal"
    journal_dir.mkdir(parents=True)
    repo = git.Repo.init(journal_dir)
    repo.config_writer().set_value("user", "name", "Test User").release()
    repo.config_writer().set_value("user", "email", "test@example.com").release()

    monkeypatch.setattr("claude_journal.server.get_journals_dir", lambda: journal_dir)
    monkeypatch.setattr("claude_journal.journal.get_journals_dir", lambda: journal_dir)

    arguments = {
        "content": "User prefers explicit error handling over exceptions",
        "type": "preference",
        "scope": "global",
    }

    result = await handle_journal_write(arguments)

    assert len(result) == 1
    assert "Journal entry written" in result[0].text
    global_journal = journal_dir / "global" / "journal.md"
    assert global_journal.exists()
    content = global_journal.read_text()
    assert "User prefers explicit error handling" in content
    assert "preference" in content


@pytest.mark.asyncio
async def test_journal_write_commits_to_git(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test JournalWrite creates git commits."""
    journal_dir = tmp_path / "journal"
    journal_dir.mkdir(parents=True)
    repo = git.Repo.init(journal_dir)
    repo.config_writer().set_value("user", "name", "Test User").release()
    repo.config_writer().set_value("user", "email", "test@example.com").release()

    monkeypatch.setattr("claude_journal.server.get_journals_dir", lambda: journal_dir)
    monkeypatch.setattr("claude_journal.journal.get_journals_dir", lambda: journal_dir)

    arguments = {"content": "Test commit entry", "type": "decision", "scope": "global"}

    await handle_journal_write(arguments)

    commits = list(repo.iter_commits())
    assert len(commits) == 1
    assert "[global] decision:" in commits[0].message


@pytest.mark.asyncio
async def test_journal_search_finds_entries(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test JournalSearch finds matching entries."""
    journal_dir = tmp_path / "journal"
    global_journal = journal_dir / "global" / "journal.md"
    global_journal.parent.mkdir(parents=True)
    global_journal.write_text(
        "## [2025-10-06T14:30:00Z] insight\n\n"
        "This is a test entry about authentication.\n\n"
        "---\n"
        "## [2025-10-06T15:00:00Z] decision\n\n"
        "Chose PostgreSQL for the database.\n\n"
        "---\n"
    )

    monkeypatch.setattr("claude_journal.server.get_journals_dir", lambda: journal_dir)

    arguments = {"query": "authentication", "scope": "global"}

    result = await handle_journal_search(arguments)

    assert len(result) == 1
    assert "authentication" in result[0].text
    assert "insight" in result[0].text


@pytest.mark.asyncio
async def test_journal_search_filters_by_type(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test JournalSearch filters by entry type."""
    journal_dir = tmp_path / "journal"
    global_journal = journal_dir / "global" / "journal.md"
    global_journal.parent.mkdir(parents=True)
    global_journal.write_text(
        "## [2025-10-06T14:30:00Z] insight\n\n"
        "This is an insight entry.\n\n"
        "---\n"
        "## [2025-10-06T15:00:00Z] decision\n\n"
        "This is a decision entry.\n\n"
        "---\n"
    )

    monkeypatch.setattr("claude_journal.server.get_journals_dir", lambda: journal_dir)

    arguments = {"query": "entry", "scope": "global", "type": "decision"}

    result = await handle_journal_search(arguments)

    assert len(result) == 1
    assert "decision" in result[0].text
    assert "insight" not in result[0].text


@pytest.mark.asyncio
async def test_journal_search_no_results(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test JournalSearch returns appropriate message when no results found."""
    journal_dir = tmp_path / "journal"
    global_journal = journal_dir / "global" / "journal.md"
    global_journal.parent.mkdir(parents=True)
    global_journal.write_text("## [2025-10-06T14:30:00Z] insight\n\nSome content\n\n---\n")

    monkeypatch.setattr("claude_journal.server.get_journals_dir", lambda: journal_dir)

    arguments = {"query": "nonexistent", "scope": "global"}

    result = await handle_journal_search(arguments)

    assert len(result) == 1
    assert "No matching journal entries found" in result[0].text


@pytest.mark.asyncio
async def test_journal_write_handles_git_not_initialized(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test JournalWrite handles case where git is not initialized."""
    journal_dir = tmp_path / "journal"
    journal_dir.mkdir(parents=True)

    monkeypatch.setattr("claude_journal.server.get_journals_dir", lambda: journal_dir)

    arguments = {"content": "Refactored module for better maintainability", "type": "insight", "scope": "global"}

    result = await handle_journal_write(arguments)

    assert len(result) == 1
    assert "Warning" in result[0].text or "not a git repository" in result[0].text.lower()

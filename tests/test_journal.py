# ABOUTME: Tests for journal file I/O operations including directory management,
# ABOUTME: entry formatting, and journal file read/write operations.

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from claude_journal.journal import (
    append_entry,
    ensure_journals_dir,
    format_entry,
    generate_project_id,
    get_journals_dir,
    get_or_create_project_id,
    get_project_config_path,
    get_project_journal_path,
    read_journal,
    read_project_id,
    resolve_journal_path,
    write_project_id,
)


def test_get_journals_dir_returns_expected_path() -> None:
    """Test that get_journals_dir returns ~/.claude/journal/."""
    result = get_journals_dir()
    expected = Path.home() / ".claude" / "journal"
    assert result == expected
    assert isinstance(result, Path)


def test_ensure_journals_dir_creates_directory(tmp_path: Path) -> None:
    """Test that ensure_journals_dir creates the directory if it doesn't exist."""
    test_dir = tmp_path / ".claude" / "journal"
    assert not test_dir.exists()

    ensure_journals_dir(test_dir)

    assert test_dir.exists()
    assert test_dir.is_dir()


def test_ensure_journals_dir_handles_existing_directory(tmp_path: Path) -> None:
    """Test that ensure_journals_dir works when directory already exists."""
    test_dir = tmp_path / ".claude" / "journal"
    test_dir.mkdir(parents=True)
    assert test_dir.exists()

    ensure_journals_dir(test_dir)

    assert test_dir.exists()
    assert test_dir.is_dir()


def test_format_entry_creates_correct_format() -> None:
    """Test that format_entry creates the correct markdown format."""
    content = "This is a test entry.\nWith multiple lines."
    entry_type = "insight"
    timestamp = datetime(2025, 10, 6, 14, 30, 45, tzinfo=UTC)

    result = format_entry(content, entry_type, timestamp)

    expected = "## [2025-10-06 14:30:45] insight\n\nThis is a test entry.\nWith multiple lines.\n\n---\n"
    assert result == expected


def test_format_entry_handles_single_line_content() -> None:
    """Test that format_entry works with single line content."""
    content = "Single line entry"
    entry_type = "decision"
    timestamp = datetime(2025, 1, 1, 0, 0, 0, tzinfo=UTC)

    result = format_entry(content, entry_type, timestamp)

    expected = "## [2025-01-01 00:00:00] decision\n\nSingle line entry\n\n---\n"
    assert result == expected


def test_append_entry_creates_file_and_appends(tmp_path: Path) -> None:
    """Test that append_entry creates file if it doesn't exist and appends entry."""
    journal_path = tmp_path / "journal.md"
    content = "First entry"
    entry_type = "insight"

    append_entry(journal_path, content, entry_type)

    assert journal_path.exists()
    file_content = journal_path.read_text()
    assert "insight" in file_content
    assert "First entry" in file_content
    assert "---" in file_content


def test_append_entry_appends_to_existing_file(tmp_path: Path) -> None:
    """Test that append_entry appends to existing file."""
    journal_path = tmp_path / "journal.md"
    journal_path.write_text("Existing content\n")

    content = "New entry"
    entry_type = "decision"

    append_entry(journal_path, content, entry_type)

    file_content = journal_path.read_text()
    assert "Existing content" in file_content
    assert "New entry" in file_content
    assert "decision" in file_content


def test_read_journal_returns_file_contents(tmp_path: Path) -> None:
    """Test that read_journal returns the entire journal file contents."""
    journal_path = tmp_path / "journal.md"
    expected_content = "## [2025-10-06 14:30:00] insight\n\nTest entry\n\n---\n"
    journal_path.write_text(expected_content)

    result = read_journal(journal_path)

    assert result == expected_content


def test_read_journal_returns_empty_string_for_nonexistent_file(tmp_path: Path) -> None:
    """Test that read_journal returns empty string if file doesn't exist."""
    journal_path = tmp_path / "nonexistent.md"

    result = read_journal(journal_path)

    assert result == ""


def test_generate_project_id_returns_8_char_hex() -> None:
    """Test that generate_project_id returns an 8-character hex string."""
    result = generate_project_id()

    assert len(result) == 8
    assert all(c in "0123456789abcdef" for c in result)


def test_generate_project_id_returns_unique_ids() -> None:
    """Test that generate_project_id returns different IDs on each call."""
    id1 = generate_project_id()
    id2 = generate_project_id()

    assert id1 != id2


def test_get_project_config_path_returns_correct_path(tmp_path: Path) -> None:
    """Test that get_project_config_path returns .claude/journal.json path."""
    result = get_project_config_path(tmp_path)

    expected = tmp_path / ".claude" / "journal.json"
    assert result == expected


def test_read_project_id_returns_none_for_nonexistent_file(tmp_path: Path) -> None:
    """Test that read_project_id returns None if config file doesn't exist."""
    result = read_project_id(tmp_path)

    assert result is None


def test_read_project_id_returns_id_from_file(tmp_path: Path) -> None:
    """Test that read_project_id reads ID from journal.json."""
    config_dir = tmp_path / ".claude"
    config_dir.mkdir()
    config_file = config_dir / "journal.json"
    config_file.write_text('{"id": "a3f8b2c9"}')

    result = read_project_id(tmp_path)

    assert result == "a3f8b2c9"


def test_write_project_id_creates_directory_and_file(tmp_path: Path) -> None:
    """Test that write_project_id creates .claude directory and writes journal.json."""
    project_id = "test1234"

    write_project_id(tmp_path, project_id)

    config_file = tmp_path / ".claude" / "journal.json"
    assert config_file.exists()
    content = config_file.read_text()
    assert "test1234" in content


def test_write_project_id_creates_valid_json(tmp_path: Path) -> None:
    """Test that write_project_id creates valid JSON with id field."""
    project_id = "a1b2c3d4"

    write_project_id(tmp_path, project_id)

    config_file = tmp_path / ".claude" / "journal.json"
    data = json.loads(config_file.read_text())
    assert data["id"] == "a1b2c3d4"


def test_get_or_create_project_id_creates_new_id(tmp_path: Path) -> None:
    """Test that get_or_create_project_id creates a new ID if none exists."""
    result = get_or_create_project_id(tmp_path)

    assert len(result) == 8
    assert all(c in "0123456789abcdef" for c in result)

    config_file = tmp_path / ".claude" / "journal.json"
    assert config_file.exists()


def test_get_or_create_project_id_returns_existing_id(tmp_path: Path) -> None:
    """Test that get_or_create_project_id returns existing ID if present."""
    config_dir = tmp_path / ".claude"
    config_dir.mkdir()
    config_file = config_dir / "journal.json"
    config_file.write_text('{"id": "existing1"}')

    result = get_or_create_project_id(tmp_path)

    assert result == "existing1"


def test_get_project_journal_path_returns_correct_path() -> None:
    """Test that get_project_journal_path returns the correct journal path."""
    project_id = "abc12345"

    result = get_project_journal_path(project_id)

    expected = Path.home() / ".claude" / "journal" / project_id / "journal.md"
    assert result == expected


def test_resolve_journal_path_global_scope(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that resolve_journal_path returns global journal path for global scope."""
    journal_dir = tmp_path / "journal"
    monkeypatch.setattr("claude_journal.journal.get_journals_dir", lambda: journal_dir)

    result = resolve_journal_path("global", Path.cwd())

    expected = journal_dir / "global" / "journal.md"
    assert result == expected
    assert result.parent.exists()
    assert result.parent.is_dir()


def test_resolve_journal_path_project_scope_creates_new_id(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that resolve_journal_path creates project ID for project scope."""
    journal_dir = tmp_path / "journal"
    monkeypatch.setattr("claude_journal.journal.get_journals_dir", lambda: journal_dir)

    result = resolve_journal_path("project", tmp_path)

    config_file = tmp_path / ".claude" / "journal.json"
    assert config_file.exists()

    assert result.parent.parent == journal_dir
    assert result.name == "journal.md"


def test_resolve_journal_path_project_scope_uses_existing_id(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that resolve_journal_path uses existing project ID."""
    journal_dir = tmp_path / "journal"
    monkeypatch.setattr("claude_journal.journal.get_journals_dir", lambda: journal_dir)

    config_dir = tmp_path / ".claude"
    config_dir.mkdir()
    config_file = config_dir / "journal.json"
    config_file.write_text('{"id": "existing1"}')

    result = resolve_journal_path("project", tmp_path)

    expected = journal_dir / "existing1" / "journal.md"
    assert result == expected


def test_resolve_journal_path_project_scope_creates_parent_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test that resolve_journal_path creates parent directory for project scope."""
    journal_dir = tmp_path / "journal"
    monkeypatch.setattr("claude_journal.journal.get_journals_dir", lambda: journal_dir)

    result = resolve_journal_path("project", tmp_path)

    assert result.parent.exists()
    assert result.parent.is_dir()

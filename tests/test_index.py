# ABOUTME: Tests for SQLite FTS5 index operations including index creation, updates,
# ABOUTME: search functionality, and automatic rebuilding from markdown.

from pathlib import Path

from claude_journal.index import (
    add_entry_to_index,
    create_index,
    ensure_index,
    get_index_path,
    is_index_stale,
    parse_entries_from_markdown,
    rebuild_index,
    search_index,
)


def test_get_index_path_returns_correct_path(tmp_path: Path) -> None:
    """Test that get_index_path returns journal.db in the same directory."""
    journal_path = tmp_path / "journal.md"
    result = get_index_path(journal_path)

    expected = tmp_path / "journal.db"
    assert result == expected


def test_is_index_stale_returns_true_when_index_missing(tmp_path: Path) -> None:
    """Test that is_index_stale returns True when index doesn't exist."""
    journal_path = tmp_path / "journal.md"
    index_path = tmp_path / "journal.db"

    journal_path.write_text("content")

    result = is_index_stale(journal_path, index_path)

    assert result is True


def test_is_index_stale_returns_false_when_journal_missing(tmp_path: Path) -> None:
    """Test that is_index_stale returns False when journal doesn't exist."""
    journal_path = tmp_path / "journal.md"
    index_path = tmp_path / "journal.db"

    index_path.touch()

    result = is_index_stale(journal_path, index_path)

    assert result is False


def test_is_index_stale_returns_true_when_journal_newer(tmp_path: Path) -> None:
    """Test that is_index_stale returns True when journal is modified after index."""
    import time

    journal_path = tmp_path / "journal.md"
    index_path = tmp_path / "journal.db"

    index_path.touch()
    time.sleep(0.01)
    journal_path.write_text("content")

    result = is_index_stale(journal_path, index_path)

    assert result is True


def test_is_index_stale_returns_false_when_index_newer(tmp_path: Path) -> None:
    """Test that is_index_stale returns False when index is modified after journal."""
    import time

    journal_path = tmp_path / "journal.md"
    index_path = tmp_path / "journal.db"

    journal_path.write_text("content")
    time.sleep(0.01)
    index_path.touch()

    result = is_index_stale(journal_path, index_path)

    assert result is False


def test_create_index_creates_fts5_table(tmp_path: Path) -> None:
    """Test that create_index creates an FTS5 table."""
    import sqlite3

    index_path = tmp_path / "journal.db"

    create_index(index_path)

    assert index_path.exists()

    conn = sqlite3.connect(index_path)
    cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='entries'")
    result = cursor.fetchone()
    conn.close()

    assert result is not None
    assert result[0] == "entries"


def test_add_entry_to_index_inserts_entry(tmp_path: Path) -> None:
    """Test that add_entry_to_index inserts an entry into the index."""
    import sqlite3

    index_path = tmp_path / "journal.db"
    create_index(index_path)

    timestamp = "2025-10-06T14:30:00Z"
    entry_type = "insight"
    content = "Test entry content"

    add_entry_to_index(index_path, timestamp, entry_type, content)

    conn = sqlite3.connect(index_path)
    cursor = conn.execute("SELECT timestamp, type, content FROM entries")
    result = cursor.fetchone()
    conn.close()

    assert result is not None
    assert result[0] == timestamp
    assert result[1] == entry_type
    assert result[2] == content


def test_parse_entries_from_markdown_parses_single_entry() -> None:
    """Test that parse_entries_from_markdown parses a single entry."""
    markdown = """## [2025-10-06T14:30:00Z] insight

Test content

---
"""

    result = parse_entries_from_markdown(markdown)

    assert len(result) == 1
    assert result[0][0] == "2025-10-06T14:30:00Z"
    assert result[0][1] == "insight"
    assert "Test content" in result[0][2]


def test_parse_entries_from_markdown_parses_multiple_entries() -> None:
    """Test that parse_entries_from_markdown parses multiple entries."""
    markdown = """## [2025-10-06T14:30:00Z] insight

First entry

---

## [2025-10-06T15:00:00Z] decision

Second entry

---
"""

    result = parse_entries_from_markdown(markdown)

    assert len(result) == 2
    assert result[0][1] == "insight"
    assert result[1][1] == "decision"


def test_parse_entries_from_markdown_handles_empty_content() -> None:
    """Test that parse_entries_from_markdown handles empty content."""
    result = parse_entries_from_markdown("")

    assert len(result) == 0


def test_parse_entries_from_markdown_skips_malformed_entries() -> None:
    """Test that parse_entries_from_markdown skips entries without proper headers."""
    markdown = """## [2025-10-06T14:30:00Z] insight

Valid entry

---

Some text without header

---
"""

    result = parse_entries_from_markdown(markdown)

    assert len(result) == 1
    assert result[0][1] == "insight"


def test_rebuild_index_creates_empty_index_for_missing_journal(tmp_path: Path) -> None:
    """Test that rebuild_index creates empty index if journal doesn't exist."""
    import sqlite3

    journal_path = tmp_path / "journal.md"
    index_path = tmp_path / "journal.db"

    rebuild_index(journal_path, index_path)

    assert index_path.exists()

    conn = sqlite3.connect(index_path)
    cursor = conn.execute("SELECT COUNT(*) FROM entries")
    count = cursor.fetchone()[0]
    conn.close()

    assert count == 0


def test_rebuild_index_indexes_all_entries(tmp_path: Path) -> None:
    """Test that rebuild_index indexes all entries from markdown."""
    import sqlite3

    journal_path = tmp_path / "journal.md"
    index_path = tmp_path / "journal.db"

    markdown = """## [2025-10-06T14:30:00Z] insight

First entry

---

## [2025-10-06T15:00:00Z] decision

Second entry

---
"""
    journal_path.write_text(markdown)

    rebuild_index(journal_path, index_path)

    conn = sqlite3.connect(index_path)
    cursor = conn.execute("SELECT COUNT(*) FROM entries")
    count = cursor.fetchone()[0]
    conn.close()

    assert count == 2


def test_rebuild_index_replaces_existing_index(tmp_path: Path) -> None:
    """Test that rebuild_index replaces existing index."""
    import sqlite3

    journal_path = tmp_path / "journal.md"
    index_path = tmp_path / "journal.db"

    # Create initial index with one entry
    create_index(index_path)
    add_entry_to_index(index_path, "2025-10-06T14:00:00Z", "insight", "Old entry")

    # Write different content to journal
    markdown = """## [2025-10-06T14:30:00Z] decision

New entry

---
"""
    journal_path.write_text(markdown)

    rebuild_index(journal_path, index_path)

    conn = sqlite3.connect(index_path)
    cursor = conn.execute("SELECT COUNT(*) FROM entries")
    count = cursor.fetchone()[0]
    cursor = conn.execute("SELECT type FROM entries")
    result = cursor.fetchone()
    conn.close()

    assert count == 1
    assert result[0] == "decision"


def test_rebuild_index_recovers_from_corrupted_database(tmp_path: Path) -> None:
    """Test that rebuild_index can recover from a corrupted database file."""
    import sqlite3

    journal_path = tmp_path / "journal.md"
    index_path = tmp_path / "journal.db"

    markdown = """## [2025-10-06T14:30:00Z] insight

Test entry

---
"""
    journal_path.write_text(markdown)

    # Create a corrupted database file (exists but missing schema)
    conn = sqlite3.connect(index_path)
    conn.execute("CREATE TABLE dummy (id INTEGER)")
    conn.commit()
    conn.close()

    # Rebuild should recover and create proper schema
    rebuild_index(journal_path, index_path)

    # Verify the index works correctly
    conn = sqlite3.connect(index_path)
    cursor = conn.execute("SELECT COUNT(*) FROM entries")
    count = cursor.fetchone()[0]
    conn.close()

    assert count == 1


def test_search_index_returns_empty_for_missing_index(tmp_path: Path) -> None:
    """Test that search_index returns empty list if index doesn't exist."""
    index_path = tmp_path / "journal.db"

    result = search_index(index_path, "test")

    assert result == []


def test_search_index_finds_matching_entries(tmp_path: Path) -> None:
    """Test that search_index finds entries matching the query."""
    index_path = tmp_path / "journal.db"
    create_index(index_path)

    add_entry_to_index(
        index_path,
        "2025-10-06T14:30:00Z",
        "insight",
        "## [2025-10-06T14:30:00Z] insight\n\nDatabase optimization\n\n---",
    )
    add_entry_to_index(
        index_path,
        "2025-10-06T15:00:00Z",
        "decision",
        "## [2025-10-06T15:00:00Z] decision\n\nUse PostgreSQL\n\n---",
    )

    result = search_index(index_path, "database")

    assert len(result) == 1
    assert "Database optimization" in result[0]


def test_search_index_filters_by_type(tmp_path: Path) -> None:
    """Test that search_index filters results by entry type."""
    index_path = tmp_path / "journal.db"
    create_index(index_path)

    add_entry_to_index(
        index_path,
        "2025-10-06T14:30:00Z",
        "insight",
        "## [2025-10-06T14:30:00Z] insight\n\nDatabase insight\n\n---",
    )
    add_entry_to_index(
        index_path,
        "2025-10-06T15:00:00Z",
        "decision",
        "## [2025-10-06T15:00:00Z] decision\n\nDatabase decision\n\n---",
    )

    result = search_index(index_path, "database", entry_type="insight")

    assert len(result) == 1
    assert "insight" in result[0]
    assert "decision" not in result[0]


def test_search_index_respects_max_results(tmp_path: Path) -> None:
    """Test that search_index respects max_results limit."""
    index_path = tmp_path / "journal.db"
    create_index(index_path)

    for i in range(10):
        add_entry_to_index(
            index_path,
            f"2025-10-06 14:{i:02d}:00 UTC",
            "insight",
            f"## [2025-10-06 14:{i:02d}:00 UTC] insight\n\nTest entry {i}\n\n---",
        )

    result = search_index(index_path, "test", max_results=5)

    assert len(result) == 5


def test_search_index_handles_stemming(tmp_path: Path) -> None:
    """Test that search_index uses porter stemming."""
    index_path = tmp_path / "journal.db"
    create_index(index_path)

    add_entry_to_index(
        index_path,
        "2025-10-06T14:30:00Z",
        "insight",
        "## [2025-10-06T14:30:00Z] insight\n\nImplementing features\n\n---",
    )

    # Search for "implement" should match "implementing"
    result = search_index(index_path, "implement")

    assert len(result) == 1
    assert "Implementing" in result[0]


def test_search_index_returns_empty_for_no_matches(tmp_path: Path) -> None:
    """Test that search_index returns empty list when no entries match."""
    index_path = tmp_path / "journal.db"
    create_index(index_path)

    add_entry_to_index(
        index_path,
        "2025-10-06T14:30:00Z",
        "insight",
        "## [2025-10-06T14:30:00Z] insight\n\nDatabase optimization\n\n---",
    )

    result = search_index(index_path, "nonexistent")

    assert result == []


def test_search_index_handles_corrupted_index(tmp_path: Path) -> None:
    """Test that search_index handles corrupted index gracefully."""
    index_path = tmp_path / "journal.db"
    index_path.write_text("corrupted data")

    result = search_index(index_path, "test")

    assert result == []


def test_ensure_index_creates_index_if_missing(tmp_path: Path) -> None:
    """Test that ensure_index creates index if it doesn't exist."""
    journal_path = tmp_path / "journal.md"
    journal_path.write_text("## [2025-10-06T14:30:00Z] insight\n\nTest\n\n---\n")

    result = ensure_index(journal_path)

    assert result.exists()
    assert result == get_index_path(journal_path)


def test_ensure_index_rebuilds_stale_index(tmp_path: Path) -> None:
    """Test that ensure_index rebuilds index if journal is newer."""
    import sqlite3
    import time

    journal_path = tmp_path / "journal.md"
    index_path = get_index_path(journal_path)

    # Create old index
    create_index(index_path)
    add_entry_to_index(index_path, "2025-10-06T14:00:00Z", "insight", "Old entry")

    time.sleep(0.01)

    # Update journal
    journal_path.write_text("## [2025-10-06T14:30:00Z] decision\n\nNew entry\n\n---\n")

    ensure_index(journal_path)

    # Verify index was rebuilt with new content
    conn = sqlite3.connect(index_path)
    cursor = conn.execute("SELECT type FROM entries")
    result = cursor.fetchone()
    conn.close()

    assert result[0] == "decision"


def test_ensure_index_does_not_rebuild_fresh_index(tmp_path: Path) -> None:
    """Test that ensure_index doesn't rebuild if index is up to date."""
    import time

    journal_path = tmp_path / "journal.md"
    index_path = get_index_path(journal_path)

    # Create journal
    journal_path.write_text("## [2025-10-06T14:30:00Z] insight\n\nTest\n\n---\n")

    time.sleep(0.01)

    # Create fresh index
    create_index(index_path)
    add_entry_to_index(index_path, "2025-10-06T14:30:00Z", "insight", "Test entry")

    initial_mtime = index_path.stat().st_mtime

    time.sleep(0.01)

    ensure_index(journal_path)

    # Index should not be rebuilt (mtime unchanged)
    assert index_path.stat().st_mtime == initial_mtime

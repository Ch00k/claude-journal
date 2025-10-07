# ABOUTME: SQLite FTS5 index operations for fast journal search with relevance ranking.
# ABOUTME: Provides index creation, updates, search, and automatic rebuilding from markdown.

import fcntl
import re
import sqlite3
from pathlib import Path


def get_index_path(journal_path: Path) -> Path:
    """Return the path to the SQLite index file for a given journal."""
    return journal_path.parent / "journal.db"


def is_index_stale(journal_path: Path, index_path: Path) -> bool:
    """Check if the index needs rebuilding based on file modification times."""
    if not index_path.exists():
        return True
    if not journal_path.exists():
        return False
    return journal_path.stat().st_mtime > index_path.stat().st_mtime


def create_index(index_path: Path) -> None:
    """Create a new FTS5 index database."""
    conn = sqlite3.connect(index_path, timeout=30.0)
    try:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.execute("PRAGMA temp_store=MEMORY")
        conn.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS entries USING fts5(
                timestamp,
                type,
                content,
                tokenize = 'porter unicode61'
            )
        """)
        conn.commit()
    finally:
        conn.close()


def add_entry_to_index(index_path: Path, timestamp: str, entry_type: str, content: str) -> None:
    """Add a single entry to the index."""
    conn = sqlite3.connect(index_path, timeout=30.0)
    try:
        conn.execute(
            "INSERT INTO entries (timestamp, type, content) VALUES (?, ?, ?)",
            (timestamp, entry_type, content),
        )
        conn.commit()
    finally:
        conn.close()


def parse_entries_from_markdown(markdown_content: str) -> list[tuple[str, str, str]]:
    """Parse journal entries from markdown. Returns list of (timestamp, type, content) tuples."""
    entries = []
    for raw_entry in markdown_content.split("\n---\n"):
        entry = raw_entry.strip()
        if not entry:
            continue

        # Extract timestamp and type from header: ## [YYYY-MM-DDTHH:MM:SSZ] type
        header_match = re.match(r"^## \[(.*?)\] (\w+)", entry)
        if not header_match:
            continue

        timestamp = header_match.group(1)
        entry_type = header_match.group(2)

        entries.append((timestamp, entry_type, entry))

    return entries


def rebuild_index(journal_path: Path, index_path: Path) -> None:
    """Rebuild the entire index from the markdown journal file."""
    # Read markdown content
    if not journal_path.exists():
        # Create empty index if journal doesn't exist yet
        create_index(index_path)
        return

    markdown_content = journal_path.read_text()

    # Ensure schema exists (handles corrupted or incomplete databases)
    create_index(index_path)

    # Parse all entries
    entries = parse_entries_from_markdown(markdown_content)

    # Clear and repopulate index atomically
    conn = sqlite3.connect(index_path, timeout=30.0)
    try:
        conn.execute("DELETE FROM entries")
        conn.executemany(
            "INSERT INTO entries (timestamp, type, content) VALUES (?, ?, ?)",
            entries,
        )
        conn.commit()
    finally:
        conn.close()


def search_index(
    index_path: Path,
    query: str,
    entry_type: str | None = None,
    max_results: int = 200,
) -> list[str]:
    """
    Search the index using FTS5. Returns list of entry content strings sorted by relevance.

    Args:
        index_path: Path to the SQLite index file
        query: FTS5 search query
        entry_type: Optional filter by entry type
        max_results: Maximum number of results to return

    Returns:
        List of matching entry content strings, sorted by relevance (best first)
    """
    if not index_path.exists():
        return []

    conn = sqlite3.connect(index_path, timeout=30.0)
    try:
        # Build query
        if entry_type:
            sql = """
                SELECT content
                FROM entries
                WHERE entries MATCH ? AND type = ?
                ORDER BY rank
                LIMIT ?
            """
            cursor = conn.execute(sql, (query, entry_type, max_results))
        else:
            sql = """
                SELECT content
                FROM entries
                WHERE entries MATCH ?
                ORDER BY rank
                LIMIT ?
            """
            cursor = conn.execute(sql, (query, max_results))

        return [row[0] for row in cursor.fetchall()]
    except (sqlite3.OperationalError, sqlite3.DatabaseError):
        # Index might be corrupted or query syntax invalid
        return []
    finally:
        conn.close()


def ensure_index(journal_path: Path) -> Path:
    """
    Ensure the index exists and is up to date. Returns the index path.

    Creates index if missing, rebuilds if stale. Uses file locking to prevent
    concurrent rebuilds.
    """
    index_path = get_index_path(journal_path)

    if is_index_stale(journal_path, index_path):
        # Use journal file as lock to coordinate rebuilds across processes
        lock_path = journal_path.parent / ".index.lock"
        lock_path.touch(exist_ok=True)

        with lock_path.open("r") as lock_file:
            try:
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
                # Check again after acquiring lock (another process may have rebuilt)
                if is_index_stale(journal_path, index_path):
                    rebuild_index(journal_path, index_path)
            finally:
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)

    return index_path

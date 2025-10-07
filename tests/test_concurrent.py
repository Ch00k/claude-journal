# ABOUTME: Tests for concurrent database access including parallel writes, reads,
# ABOUTME: and index rebuilds to ensure proper locking and data integrity.

import multiprocessing
import time
from pathlib import Path

from claude_journal.index import add_entry_to_index, create_index, ensure_index, search_index


def _concurrent_write_worker(index_path: Path, worker_id: int, num_writes: int) -> None:
    """Worker function for concurrent write test."""
    for i in range(num_writes):
        timestamp = f"2025-10-06T14:{worker_id:02d}:{i:02d}Z"
        entry_type = "insight"
        content = f"## [{timestamp}] {entry_type}\n\nWorker {worker_id} entry {i}\n\n---"
        add_entry_to_index(index_path, timestamp, entry_type, content)
        time.sleep(0.001)  # Small delay to increase contention


def test_concurrent_writes_do_not_corrupt_index(tmp_path: Path) -> None:
    """Test that concurrent writes to the same index don't cause corruption."""
    import sqlite3

    index_path = tmp_path / "journal.db"
    create_index(index_path)

    num_workers = 4
    writes_per_worker = 10

    # Start multiple processes writing concurrently
    processes = []
    for worker_id in range(num_workers):
        p = multiprocessing.Process(target=_concurrent_write_worker, args=(index_path, worker_id, writes_per_worker))
        p.start()
        processes.append(p)

    # Wait for all processes to complete
    for p in processes:
        p.join()

    # Verify all entries were written successfully
    conn = sqlite3.connect(index_path)
    cursor = conn.execute("SELECT COUNT(*) FROM entries")
    count = cursor.fetchone()[0]
    conn.close()

    expected_count = num_workers * writes_per_worker
    assert count == expected_count


def _concurrent_rebuild_worker(journal_path: Path, _worker_id: int) -> None:
    """Worker function for concurrent rebuild test."""
    for _ in range(3):
        ensure_index(journal_path)
        time.sleep(0.01)


def test_concurrent_rebuilds_do_not_corrupt_index(tmp_path: Path) -> None:
    """Test that concurrent rebuilds of the same index don't cause corruption."""
    import sqlite3

    journal_path = tmp_path / "journal.md"
    index_path = tmp_path / "journal.db"

    # Create journal with some entries
    markdown = """## [2025-10-06T14:30:00Z] insight

First entry

---

## [2025-10-06T15:00:00Z] decision

Second entry

---
"""
    journal_path.write_text(markdown)

    # Start multiple processes rebuilding concurrently
    num_workers = 4
    processes = []
    for worker_id in range(num_workers):
        p = multiprocessing.Process(target=_concurrent_rebuild_worker, args=(journal_path, worker_id))
        p.start()
        processes.append(p)

    # Wait for all processes to complete
    for p in processes:
        p.join()

    # Verify index is valid and contains correct entries
    assert index_path.exists()

    conn = sqlite3.connect(index_path)
    cursor = conn.execute("SELECT COUNT(*) FROM entries")
    count = cursor.fetchone()[0]
    conn.close()

    assert count == 2


def _concurrent_read_worker(index_path: Path, query: str, _expected_results: int) -> int:
    """Worker function for concurrent read test. Returns number of results found."""
    results = search_index(index_path, query)
    return len(results)


def test_concurrent_reads_return_consistent_results(tmp_path: Path) -> None:
    """Test that concurrent reads return consistent results."""
    index_path = tmp_path / "journal.db"
    create_index(index_path)

    # Add test entries
    for i in range(10):
        add_entry_to_index(
            index_path,
            f"2025-10-06T14:{i:02d}:00Z",
            "insight",
            f"## [2025-10-06T14:{i:02d}:00Z] insight\n\nTest entry {i}\n\n---",
        )

    # Perform concurrent reads
    num_workers = 8
    processes = []
    results: multiprocessing.Queue[int] = multiprocessing.Queue()

    def worker() -> None:
        count = _concurrent_read_worker(index_path, "test", 10)
        results.put(count)

    for _ in range(num_workers):
        p = multiprocessing.Process(target=worker)
        p.start()
        processes.append(p)

    # Wait for all processes to complete
    for p in processes:
        p.join()

    # Verify all reads returned consistent results
    counts = []
    while not results.empty():
        counts.append(results.get())

    assert len(counts) == num_workers
    assert all(count == 10 for count in counts)


def _concurrent_mixed_worker(index_path: Path, worker_id: int) -> None:
    """Worker function for mixed read/write test."""
    for i in range(5):
        # Write an entry
        timestamp = f"2025-10-06T{worker_id:02d}:{i:02d}:00Z"
        content = f"## [{timestamp}] insight\n\nWorker {worker_id} entry {i}\n\n---"
        add_entry_to_index(index_path, timestamp, "insight", content)

        # Search for entries
        search_index(index_path, "Worker")

        time.sleep(0.001)


def test_concurrent_mixed_operations_do_not_corrupt_index(tmp_path: Path) -> None:
    """Test that concurrent mixed read/write operations don't cause corruption."""
    import sqlite3

    index_path = tmp_path / "journal.db"
    create_index(index_path)

    num_workers = 4
    processes = []

    for worker_id in range(num_workers):
        p = multiprocessing.Process(target=_concurrent_mixed_worker, args=(index_path, worker_id))
        p.start()
        processes.append(p)

    # Wait for all processes to complete
    for p in processes:
        p.join()

    # Verify all entries were written successfully
    conn = sqlite3.connect(index_path)
    cursor = conn.execute("SELECT COUNT(*) FROM entries")
    count = cursor.fetchone()[0]
    conn.close()

    expected_count = num_workers * 5
    assert count == expected_count


def test_wal_mode_is_enabled(tmp_path: Path) -> None:
    """Test that WAL mode is enabled for the index."""
    import sqlite3

    index_path = tmp_path / "journal.db"
    create_index(index_path)

    conn = sqlite3.connect(index_path)
    cursor = conn.execute("PRAGMA journal_mode")
    mode = cursor.fetchone()[0]
    conn.close()

    assert mode.lower() == "wal"

# ABOUTME: Core journal operations including directory management, entry formatting,
# ABOUTME: and journal file read/write operations.

import json
import secrets
from datetime import UTC, datetime
from pathlib import Path


def get_journals_dir() -> Path:
    """Return the path to the journals directory (~/.claude/journal/)."""
    return Path.home() / ".claude" / "journal"


def ensure_journals_dir(path: Path) -> None:
    """Create the journals directory if it doesn't exist."""
    path.mkdir(parents=True, exist_ok=True)


def format_entry(content: str, entry_type: str, timestamp: datetime) -> str:
    """Format a journal entry with markdown header."""
    timestamp_str = timestamp.strftime("%Y-%m-%dT%H:%M:%SZ")
    return f"## [{timestamp_str}] {entry_type}\n\n{content}\n\n---\n"


def append_entry(journal_path: Path, content: str, entry_type: str) -> None:
    """Append a formatted entry to the journal file and update the search index."""
    from claude_journal.index import add_entry_to_index, ensure_index

    timestamp = datetime.now(tz=UTC)
    formatted_entry = format_entry(content, entry_type, timestamp)

    with journal_path.open("a") as f:
        f.write(formatted_entry)

    # Update search index
    index_path = ensure_index(journal_path)
    timestamp_str = timestamp.strftime("%Y-%m-%dT%H:%M:%SZ")
    add_entry_to_index(index_path, timestamp_str, entry_type, formatted_entry.strip())


def read_journal(journal_path: Path) -> str:
    """Read and return the entire journal file contents."""
    if not journal_path.exists():
        return ""
    return journal_path.read_text()


def generate_project_id() -> str:
    """Generate an 8-character hex ID."""
    return secrets.token_hex(4)


def get_project_config_path(cwd: Path) -> Path:
    """Return the path to .claude/journal.json in the given directory."""
    return cwd / ".claude" / "journal.json"


def read_project_id(cwd: Path) -> str | None:
    """Read the project ID from .claude/journal.json, or None if it doesn't exist."""
    config_path = get_project_config_path(cwd)
    if not config_path.exists():
        return None

    try:
        content = config_path.read_text()
        data = json.loads(content)

        if not isinstance(data, dict):
            msg = f"Invalid journal.json format: expected object, got {type(data).__name__}"
            raise TypeError(msg)

        if "id" not in data:
            msg = "Invalid journal.json format: missing 'id' field"
            raise ValueError(msg)

        project_id = data["id"]
        if not isinstance(project_id, str) or not project_id:
            msg = f"Invalid journal.json format: 'id' must be a non-empty string, got {type(project_id).__name__}"
            raise ValueError(msg)

        return project_id
    except json.JSONDecodeError as e:
        msg = f"Corrupted journal.json at {config_path}: {e}. Please delete the file or fix the JSON syntax."
        raise ValueError(msg) from e


def write_project_id(cwd: Path, project_id: str) -> None:
    """Create .claude directory and write project ID to journal.json."""
    config_path = get_project_config_path(cwd)
    config_path.parent.mkdir(parents=True, exist_ok=True)

    data = {"id": project_id}
    config_path.write_text(json.dumps(data, indent=2) + "\n")


def get_or_create_project_id(cwd: Path) -> tuple[str, bool]:
    """Get existing project ID or create a new one. Returns (id, is_new)."""
    existing_id = read_project_id(cwd)
    if existing_id is not None:
        return existing_id, False

    new_id = generate_project_id()
    write_project_id(cwd, new_id)
    return new_id, True


def get_project_journal_path(project_id: str) -> Path:
    """Return the path to the journal file for a given project ID."""
    return get_journals_dir() / project_id / "journal.md"


def resolve_journal_path(scope: str, cwd: Path) -> tuple[Path, bool]:
    """Resolve the journal path based on scope and ensure parent directories exist. Returns (path, is_new_project)."""
    is_new_project = False
    if scope == "global":
        journal_path = get_journals_dir() / "global" / "journal.md"
    else:
        project_id, is_new_project = get_or_create_project_id(cwd)
        journal_path = get_project_journal_path(project_id)

    journal_path.parent.mkdir(parents=True, exist_ok=True)
    return journal_path, is_new_project

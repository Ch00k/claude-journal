# ABOUTME: MCP server implementation providing JournalWrite and JournalSearch tools
# ABOUTME: for Claude Code to persist and retrieve journal entries across conversations.

import asyncio
from pathlib import Path

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

from claude_journal.git import git_commit, git_pull, git_push
from claude_journal.journal import (
    append_entry,
    get_journals_dir,
    get_or_create_project_id,
    get_project_journal_path,
    resolve_journal_path,
)

app = Server("claude-journal")


@app.list_tools()
async def list_tools() -> list[Tool]:
    """List available MCP tools."""
    return [
        Tool(
            name="JournalWrite",
            description="Write an entry to the journal. Entries are persisted across conversations.",
            inputSchema={
                "type": "object",
                "properties": {
                    "content": {
                        "type": "string",
                        "description": "The journal entry content",
                    },
                    "type": {
                        "type": "string",
                        "enum": ["insight", "failure", "decision", "preference", "todo"],
                        "description": "The type of journal entry",
                    },
                    "scope": {
                        "type": "string",
                        "enum": ["global", "project"],
                        "default": "project",
                        "description": "Scope of the journal entry (global or project-specific)",
                    },
                },
                "required": ["content", "type"],
            },
        ),
        Tool(
            name="JournalSearch",
            description="Search journal entries. Use this to recall past insights, decisions, and learnings.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Text or regex pattern to search for",
                    },
                    "scope": {
                        "type": "string",
                        "enum": ["global", "project", "both"],
                        "default": "both",
                        "description": "Which journal(s) to search",
                    },
                    "type": {
                        "type": "string",
                        "enum": ["insight", "failure", "decision", "preference", "todo"],
                        "description": "Filter by entry type (optional)",
                    },
                },
                "required": ["query"],
            },
        ),
    ]


@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Handle tool calls."""
    if name == "JournalWrite":
        return await handle_journal_write(arguments)
    if name == "JournalSearch":
        return await handle_journal_search(arguments)
    msg = f"Unknown tool: {name}"
    raise ValueError(msg)


async def handle_journal_write(arguments: dict) -> list[TextContent]:  # noqa: PLR0911
    """Handle JournalWrite tool call."""
    content = arguments["content"]
    entry_type = arguments["type"]
    scope = arguments.get("scope", "project")

    cwd = Path.cwd()
    journals_dir = get_journals_dir()

    # Check if journals directory exists
    if not journals_dir.exists():
        return [
            TextContent(
                type="text",
                text=(
                    f"Error: Journal directory not found at {journals_dir}. "
                    "Please run 'claude-journal init' to initialize the journal repository."
                ),
            )
        ]

    # Pull from git if remote configured
    pull_success, pull_msg = git_pull(journals_dir)
    if not pull_success and "Not a git repository" in pull_msg:
        return [
            TextContent(
                type="text",
                text=(
                    f"Error: {journals_dir} is not a git repository. "
                    "Please run 'claude-journal init' to initialize the journal repository."
                ),
            )
        ]

    # Resolve journal path and append entry
    try:
        journal_path, is_new_project = resolve_journal_path(scope, cwd)
        append_entry(journal_path, content, entry_type)
    except (OSError, ValueError, TypeError) as e:
        return [
            TextContent(
                type="text",
                text=f"Error: Failed to write journal entry: {e}",
            )
        ]

    # Commit to git
    commit_msg = f"[{scope}] {entry_type}: {content[:50]}"
    commit_success, commit_msg_result = git_commit(journals_dir, journal_path, commit_msg)
    if not commit_success:
        return [
            TextContent(
                type="text",
                text=f"Entry written to {journal_path} but commit failed: {commit_msg_result}",
            )
        ]

    # Push to git if remote configured
    push_success, push_msg = git_push(journals_dir)
    if not push_success and "skipping push" not in push_msg:
        return [
            TextContent(
                type="text",
                text=(
                    f"Entry written and committed locally, but push failed: {push_msg}. "
                    "The entry is saved and will be pushed on the next successful operation."
                ),
            )
        ]

    # Determine scope label for output
    scope_label = "global journal" if scope == "global" else f"project journal ({journal_path.parent.name})"

    # Add new project notification
    if is_new_project and scope == "project":
        config_path = cwd / ".claude" / "journal.json"
        return [
            TextContent(
                type="text",
                text=(
                    f"Created new project journal (ID: {journal_path.parent.name}) "
                    f"and saved to {config_path}. Journal entry written to {scope_label}"
                ),
            )
        ]

    return [
        TextContent(
            type="text",
            text=f"Journal entry written to {scope_label}",
        )
    ]


async def handle_journal_search(arguments: dict) -> list[TextContent]:
    """Handle JournalSearch tool call."""
    from claude_journal.index import ensure_index, search_index

    query = arguments["query"]
    scope = arguments.get("scope", "both")
    entry_type = arguments.get("type")

    cwd = Path.cwd()
    journals_dir = get_journals_dir()

    # Check if journals directory exists
    if not journals_dir.exists():
        return [
            TextContent(
                type="text",
                text=(
                    f"Error: Journal directory not found at {journals_dir}. "
                    "Please run 'claude-journal init' to initialize the journal repository."
                ),
            )
        ]

    # Pull from git if remote configured
    git_pull(journals_dir)

    # Determine which journals to search
    journals_to_search = []
    if scope in ("global", "both"):
        journals_to_search.append(journals_dir / "global" / "journal.md")
    if scope in ("project", "both"):
        try:
            project_id, _ = get_or_create_project_id(cwd)
            journals_to_search.append(get_project_journal_path(project_id))
        except (OSError, ValueError, TypeError) as e:
            return [
                TextContent(
                    type="text",
                    text=f"Error: Failed to access project journal: {e}",
                )
            ]

    # Search using FTS5 index
    max_results = 200
    results: list[str] = []

    for journal_path in journals_to_search:
        if not journal_path.exists():
            continue

        # Ensure index is up to date
        index_path = ensure_index(journal_path)

        # Search index
        index_results = search_index(index_path, query, entry_type, max_results - len(results))
        results.extend(index_results)

        if len(results) >= max_results:
            break

    if not results:
        search_scope = "global and project journals" if scope == "both" else f"{scope} journal"
        type_filter = f" with type '{entry_type}'" if entry_type else ""
        return [
            TextContent(
                type="text",
                text=f"No matching journal entries found in {search_scope}{type_filter} for query: {query}",
            )
        ]

    # Results are already sorted by relevance from FTS5
    result_text = f"Found {len(results)} matching entries"
    if len(results) >= max_results:
        result_text += f" (limited to {max_results} most relevant)"
    result_text += ":\n\n" + "\n\n---\n\n".join(results)

    return [
        TextContent(
            type="text",
            text=result_text,
        )
    ]


async def main() -> None:
    """Run the MCP server."""
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())


def run() -> None:
    """Entry point for running the server."""
    asyncio.run(main())

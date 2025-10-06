# ABOUTME: MCP server implementation providing JournalWrite and JournalSearch tools
# ABOUTME: for Claude Code to persist and retrieve journal entries across conversations.

import asyncio
import re
from pathlib import Path

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

from claude_journal.git_ops import git_commit, git_pull, git_push
from claude_journal.journal import (
    append_entry,
    get_journals_dir,
    get_or_create_project_id,
    get_project_journal_path,
    read_journal,
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


async def handle_journal_write(arguments: dict) -> list[TextContent]:
    """Handle JournalWrite tool call."""
    content = arguments["content"]
    entry_type = arguments["type"]
    scope = arguments.get("scope", "project")

    cwd = Path.cwd()
    journals_dir = get_journals_dir()

    # Pull from git if remote configured
    pull_success, pull_msg = git_pull(journals_dir)
    if not pull_success:
        return [
            TextContent(
                type="text",
                text=f"Warning: {pull_msg}",
            )
        ]

    # Resolve journal path and append entry
    journal_path = resolve_journal_path(scope, cwd)
    append_entry(journal_path, content, entry_type)

    # Commit to git
    commit_msg = f"[{scope}] {entry_type}: {content[:50]}"
    commit_success, commit_msg_result = git_commit(journals_dir, journal_path, commit_msg)
    if not commit_success:
        return [
            TextContent(
                type="text",
                text=f"Entry written but commit failed: {commit_msg_result}",
            )
        ]

    # Push to git if remote configured
    push_success, push_msg = git_push(journals_dir)
    if not push_success:
        return [
            TextContent(
                type="text",
                text=f"Entry written and committed, but push failed: {push_msg}",
            )
        ]

    return [
        TextContent(
            type="text",
            text=f"Journal entry written to {journal_path}",
        )
    ]


async def handle_journal_search(arguments: dict) -> list[TextContent]:
    """Handle JournalSearch tool call."""
    query = arguments["query"]
    scope = arguments.get("scope", "both")
    entry_type = arguments.get("type")

    cwd = Path.cwd()
    journals_dir = get_journals_dir()

    # Pull from git if remote configured
    git_pull(journals_dir)

    # Determine which journals to search
    journals_to_search = []
    if scope in ("global", "both"):
        journals_to_search.append(journals_dir / "global" / "journal.md")
    if scope in ("project", "both"):
        project_id = get_or_create_project_id(cwd)
        journals_to_search.append(get_project_journal_path(project_id))

    # Search journals
    results = []
    pattern = re.compile(query, re.IGNORECASE)

    for journal_path in journals_to_search:
        content = read_journal(journal_path)
        if not content:
            continue

        # Parse entries
        entries = content.split("\n---\n")
        for entry in entries:
            if not entry.strip():
                continue

            # Check if entry matches query
            if not pattern.search(entry):
                continue

            # Check if entry matches type filter
            if entry_type:
                # Extract type from header: ## [YYYY-MM-DD HH:MM:SS] type
                header_match = re.search(r"## \[.*?\] (\w+)", entry)
                if not header_match or header_match.group(1) != entry_type:
                    continue

            results.append(entry.strip())

    if not results:
        return [
            TextContent(
                type="text",
                text="No matching journal entries found",
            )
        ]

    return [
        TextContent(
            type="text",
            text="\n\n---\n\n".join(results),
        )
    ]


async def main() -> None:
    """Run the MCP server."""
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())


def run() -> None:
    """Entry point for running the server."""
    asyncio.run(main())

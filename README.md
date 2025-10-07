[![codecov](https://codecov.io/gh/Ch00k/claude-journal/graph/badge.svg?token=a8iDciRD0f)](https://codecov.io/gh/Ch00k/claude-journal) &nbsp;
[![PyPI - Version](https://img.shields.io/pypi/v/claude-journal)](https://pypi.org/project/claude-journal)

# Claude Journal

An MCP (Model Context Protocol) server that provides journaling capabilities for Claude Code, allowing Claude to persist
technical insights, failed approaches, architectural decisions, user preferences, and deferred work across
conversations.

## Overview

Claude Journal helps Claude remember important information across conversations by maintaining structured journal files.
Journals are stored in `~/.claude/journal/` as a git repository, providing backup, restore, and sync capabilities.

### Features

- **Per-project journals**: Each project gets its own journal with a unique ID
- **Global journal**: For cross-project insights and user preferences
- **Git integration**: Automatic commits and optional remote sync
- **Structured entries**: Five entry types (insight, failure, decision, preference, todo)
- **Powerful search**: Search journals by content and type

## Installation

```bash
uv tool install claude-journal
```

Add to Claude Code:

```bash
claude mcp add journal claude-journal
```

## Setup

Initialize the journal repository:

```bash
claude-journal init
```

This creates `~/.claude/journal/` as a git repository with a `global/journal.md` file.

For remote backup (optional):

```bash
claude-journal init --remote git@github.com:username/claude-journals.git
```

## How It Works

### Project Identification

On first journal write in a project, Claude Journal:
1. Generates a unique 8-character hex ID
2. Creates `.claude/journal.json` in your project with this ID
3. Creates `~/.claude/journal/<id>/journal.md`

Subsequent writes in that project use the same ID, even if you rename the directory.

### Entry Types

- `insight` - Technical insights about code/architecture
- `failure` - Failed approaches to avoid retrying
- `decision` - Architectural decisions and reasoning
- `preference` - User preferences and working style
- `todo` - Deferred work items

### Entry Format

```markdown
## [2025-10-06 14:23:45] insight

Content goes here.
Multiple lines supported.

---
```

## Usage

Claude uses the journal tools automatically when configured. You don't need to invoke them manually.

### Writing Entries

When Claude learns something important, it writes to the journal:

```
[Claude internally uses JournalWrite tool]
type: "decision"
scope: "project"
content: "Chose PostgreSQL over SQLite for multi-user support..."
```

### Searching

When Claude needs to recall information:

```
[Claude internally uses JournalSearch tool]
query: "authentication"
scope: "project"
```

## Git Integration

All journal operations include git commits:

- **Before read operations**: Pulls from remote (if configured)
- **After write operations**: Commits locally, pushes to remote (if configured)
- **Commit messages**: `[scope] type: brief summary`

If git operations fail (network issues, conflicts), the journal operation still succeeds locally and returns a warning.

## MCP Tools

Claude Journal provides two MCP tools:

### JournalWrite

**Parameters**:
- `content` (string, required) - The journal entry content
- `type` (enum, required) - One of: insight, failure, decision, preference, todo
- `scope` (enum, optional, default: project) - One of: global, project

### JournalSearch

**Parameters**:
- `query` (string, required) - Text or regex pattern to search for
- `scope` (enum, optional, default: both) - One of: global, project, both
- `type` (enum, optional) - Filter by entry type if specified

## Directory Structure

```
~/.claude/journal/              # Git repository
├── .git/
├── global/
│   └── journal.md              # Global journal
└── <project-id>/
    └── journal.md              # Per-project journal

<your-project>/.claude/
└── journal.json                # {"id": "a3f8b2c9"}
```


## Troubleshooting

### Journal directory missing after project ID exists

If `.claude/journal.json` exists but the journal directory is missing from `~/.claude/journal/<id>/`:

1. Check if journals repo needs restore: `cd ~/.claude/journal && git status`
2. Pull from remote: `git pull`
3. If journal was lost, the ID will be regenerated on next write

### Git conflicts

If you sync journals across machines and encounter conflicts:

```bash
cd ~/.claude/journal
git status
# Resolve conflicts manually
git add .
git commit
```

### Remote push failures

Push failures don't prevent journal writes. The entry is saved locally and will be pushed on the next successful
operation.

## Development

### Running tests

```bash
make test
```

### Linting, formatting, type checking

```bash
make lint
```

## License

This is free and unencumbered software released into the public domain. See the LICENSE file for details.

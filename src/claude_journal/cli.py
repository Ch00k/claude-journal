# ABOUTME: CLI commands for claude-journal including init command for repository setup
# ABOUTME: and main entry point for running the MCP server.

import argparse
import sys

import git

from claude_journal.journal import get_journals_dir


def init_command(remote_url: str | None) -> bool:
    """Initialize the journal repository with git."""
    journal_dir = get_journals_dir()

    if journal_dir.exists():
        print(f"Error: Journal directory already exists at {journal_dir}", file=sys.stderr)
        return False

    print(f"Creating journal directory at {journal_dir}")
    journal_dir.mkdir(parents=True)

    print("Initializing git repository")
    repo = git.Repo.init(journal_dir)

    repo.config_writer().set_value("user", "name", "Claude Journal").release()
    repo.config_writer().set_value("user", "email", "journal@claude.local").release()

    print("Creating global journal file")
    global_journal = journal_dir / "global" / "journal.md"
    global_journal.parent.mkdir(parents=True, exist_ok=True)
    global_journal.touch()

    if remote_url:
        print(f"Adding remote: {remote_url}")
        repo.create_remote("origin", remote_url)

    print("Creating initial commit")
    repo.index.add([str(global_journal)])
    repo.index.commit("Initialize journal repository")

    if remote_url:
        print("Pushing to remote")
        try:
            origin = repo.remote("origin")
            origin.push(refspec="HEAD:main")
        except git.GitCommandError as e:
            print(f"Warning: Failed to push to remote: {e}", file=sys.stderr)

    print("Journal repository initialized successfully")
    return True


def main() -> None:
    """Main entry point for claude-journal CLI."""
    parser = argparse.ArgumentParser(description="Claude Journal - Journaling for Claude Code")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Init command
    init_parser = subparsers.add_parser("init", help="Initialize the journal repository")
    init_parser.add_argument("--remote", type=str, help="Git remote URL (optional)")

    args = parser.parse_args()

    if args.command == "init":
        success = init_command(args.remote)
        sys.exit(0 if success else 1)
    elif args.command is None:
        # No command provided - run MCP server
        from claude_journal.server import run

        run()
    else:
        parser.print_help()
        sys.exit(1)

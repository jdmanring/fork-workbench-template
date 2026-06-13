#!/usr/bin/env python3
"""
Rollback to LKG (Last Known Good)

Rolls back the integration branch to a previous LKG tag created by the
upstream ingest pipeline. Use this when a bad upstream merge lands on
integration and you need to recover.

Usage:
    python3 tooling/sync-upstreams/rollback_to_lkg.py              # roll back to most recent LKG
    python3 tooling/sync-upstreams/rollback_to_lkg.py --tag LKG-20260523-1200  # specific tag
    python3 tooling/sync-upstreams/rollback_to_lkg.py --list        # list available LKG tags
"""

import argparse
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.parent.resolve()


def git_run(*args) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args], cwd=REPO_ROOT, capture_output=True, text=True
    )


def git_output(*args) -> str:
    result = git_run(*args)
    if result.returncode != 0:
        print(f"Error running git {' '.join(args)}:", file=sys.stderr)
        print(result.stderr.strip(), file=sys.stderr)
        sys.exit(1)
    return result.stdout.strip()


def list_lkg_tags() -> list[str]:
    """List all LKG tags sorted by date (newest first)."""
    tags = git_output("tag", "-l", "LKG-*").splitlines()
    return sorted(tags, reverse=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="Roll back integration to an LKG tag.")
    parser.add_argument("--tag", type=str, help="Specific LKG tag to roll back to")
    parser.add_argument("--list", action="store_true", help="List available LKG tags")
    args = parser.parse_args()

    if args.list:
        tags = list_lkg_tags()
        if not tags:
            print("No LKG tags found.")
            return
        print("Available LKG tags:")
        for tag in tags[:20]:
            # Show tag date and message
            msg = git_output("tag", "-n1", tag)
            date = git_output("log", "-1", "--format=%ci", tag)
            print(f"  {tag}  {date}  {msg}")
        return

    if args.tag:
        tag = args.tag
    else:
        tags = list_lkg_tags()
        if not tags:
            print("No LKG tags found. Cannot roll back.", file=sys.stderr)
            sys.exit(1)
        tag = tags[0]

    # Verify tag exists
    result = git_run("rev-parse", tag)
    if result.returncode != 0:
        print(f"Tag '{tag}' not found.", file=sys.stderr)
        sys.exit(1)

    # Show what we're about to do
    current = git_output("rev-parse", "HEAD")
    target = git_output("rev-parse", tag)
    current_msg = git_output("log", "-1", "--oneline", current)
    target_msg = git_output("log", "-1", "--oneline", target)

    print(f"Current: {current_msg}")
    print(f"Target:  {target_msg} ({tag})")
    print()
    print("This will run: git reset --hard", tag)
    print("This is DESTRUCTIVE — any uncommitted changes on integration will be lost.")
    print()

    confirm = input("Type 'yes' to confirm: ")
    if confirm != "yes":
        print("Aborted.")
        return

    # Perform rollback
    git_run("reset", "--hard", tag)
    print(f"Integration rolled back to {tag}.")
    print("To push: git push origin integration --force")
    print("To re-run the pipeline: python3 tooling/sync-upstreams/upstream_ingest_pipeline.py")


if __name__ == "__main__":
    main()

# Contributing to This Fork

This repository is a **contribution workbench** — a fork used to develop and stage upstream pull requests. It is not the upstream source.

## Reporting Bugs

If you found a bug:

1. **Check if it exists upstream first.** This fork may be behind the latest upstream release.
2. **File the issue on the upstream repo** if the bug exists there too.
3. **File the issue on this fork** if:
   - The bug was introduced by a fork-specific change
   - You're unsure whether it exists upstream
   - You want to help fix it in this fork before it goes upstream

## Submitting Fixes

All fixes default to **upstream-candidate** — they are staged as pull requests targeting the upstream repository.

### Workflow

1. Create an issue on this fork (or reference an existing one)
2. Branch from `upstream-mirror` (never from `develop`)
3. Make your changes — single clean commit preferred
4. Cherry-pick to `develop` so the fix is live in the working branch
5. Stay on the branch — it's the upstream PR staging
6. Update `docs/fork/upstream/pr-status.md`

### What NOT to include

- Fork-specific tooling or CI changes
- References to internal paths, usernames, or tokens
- Changes to `tooling/sync-upstreams/` or `docs/fork/`

## Fork-Only Work

A narrow category of work is fork-only (never goes upstream):
- Sync pipeline scripts and CI
- Fork management documentation
- Fork-specific configuration

If you're unsure whether something is fork-only, treat it as upstream-candidate.

## Branch Architecture

```
upstream/main → upstream-mirror → integration → develop → main
                                   ↑
                             contribution branches
```

See `FORK_WORKBENCH_TEMPLATE.md` for the full branch map and rules.

## Questions?

Open an issue with the `question` label.

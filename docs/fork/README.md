# Fork Management

> Navigation hub for fork-specific documentation. This directory contains files that manage the fork/upstream relationship. None of these files exist upstream.

## Files

| File | Purpose | Who reads it |
|------|---------|-------------|
| [issue-tracker.md](./issue-tracker.md) | Maps issues to branches, tracks labels and status | Agents and contributors filing upstream PRs |
| [changes-from-upstream.md](./changes-from-upstream.md) | Master record of every deliberate divergence from upstream | Pipeline maintainers, contributors checking if a file is protected |
| [upstream/pr-status.md](./upstream/pr-status.md) | Status of all staged upstream contributions | Agents preparing to file PRs |
| [upstream/pr-drafts/](./upstream/pr-drafts/) | PR draft files, one per staging branch — title, description, filing notes | Contributors filing upstream PRs |
| [upstream/issue-drafts/](./upstream/issue-drafts/) | Upstream issue drafts, one per staging branch — pre-written, ready to paste | Contributors filing upstream issues before PRs |

## Protected Files

The pipeline restores these files after every upstream merge. Do not remove them from `PROTECTED_FILES` unless the divergence is intentional and documented in `changes-from-upstream.md`.

## Branch Overview

```
upstream/main → upstream-mirror → integration → develop → main
                                   ↑
                             contribution branches
```

See the root [FORK_WORKBENCH_TEMPLATE.md](../FORK_WORKBENCH_TEMPLATE.md) for the full branch architecture and rules.

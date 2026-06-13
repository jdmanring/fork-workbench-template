# Issue Tracker

> Maps fork issues to branches and tracks upstream PR readiness.

## Labels

| Label | Meaning |
|-------|---------|
| `upstream-candidate` | This fix/feature targets an upstream PR |
| `fork-only` | This work manages the fork itself (never goes upstream) |
| `ready-to-file` | Branch is clean and ready for the contributor to file an upstream PR |
| `needs-work` | Branch needs more work before filing |
| `blocked` | Waiting on upstream review or dependency |

## Active Issues

| Issue | Branch | Label | Status | Upstream PR |
|-------|--------|-------|--------|-------------|
| (example) fix/agent-timeout | `fix/agent-timeout` | upstream-candidate | ready-to-file | — |
| (example) pnpm-migration | `chore/migrate-to-pnpm` | upstream-candidate | needs-work | — |
| (example) fork-docs | `fork/documentation` | fork-only | merged | N/A |

## How to Update

When creating a new contribution branch:
1. Create the issue on this fork's GitHub
2. Add the `upstream-candidate` or `fork-only` label
3. Add a row to the Active Issues table above

When the branch is ready to file:
1. Change status to `ready-to-file`
2. Verify with the health checks in FORK_WORKBENCH_TEMPLATE.md

When the upstream PR is filed:
1. Add the upstream PR link to the table
2. Change status to `filed`

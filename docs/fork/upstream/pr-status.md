# Upstream PR Status

> Tracks all staged upstream contributions and their PR status.

## PR Readiness Criteria

A branch is "ready to file" when:
- It starts from `upstream-mirror` (not `develop`)
- It has a single clean commit (or tightly related commits)
- The diff contains only files relevant to the fix/feature
- No hardcoded paths, usernames, or tokens
- Build, lint, and tests pass locally
- Commit message is clear and written for upstream reviewers

## Staged Contributions

| Branch | Issue | Status | Upstream PR | Notes |
|--------|-------|--------|-------------|-------|
| (example) fix/agent-timeout | #42 | Ready to file | — | Awaiting upstream issue creation |
| (example) chore/migrate-to-pnpm | #55 | Needs work | — | Needs conflict resolution after upstream sync |

## Filing an Upstream PR

1. Verify the branch with the health checks in FORK_WORKBENCH_TEMPLATE.md
2. Open `docs/fork/upstream/issue-drafts/<name>.md` — paste title and body into the upstream new-issue form
3. Fill the assigned issue number into `Fixes #` in the PR draft
4. Open PR: `<your-fork>:<branch>` → `<upstream-org>/<project>:<dev-branch>`
5. Add the upstream issue number and PR link to this table

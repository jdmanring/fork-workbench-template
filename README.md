# Fork Workbench

A structured system for maintaining a fork as a contribution platform — not a divergent product.

The premise: every fix and feature developed in a fork should be staged as a clean upstream contribution. That means the fork stays synchronized, each branch carries exactly one change, and when you're ready to file a PR, the issue body and PR description are already written and ready to paste. This template provides the full system — pipeline, branch rules, staging workflow, filing guide, and CI.

---

## The Problem This Solves

Maintaining a fork long-term is harder than it looks. The common failure mode: you patch something locally, upstream keeps moving, your branch accumulates unrelated changes, and six months later you have a fork that can't be contributed back without a full rewrite. Or you file a PR and the maintainers close it for missing test steps, no linked issue, or screenshots that weren't attached.

This template solves both problems:

1. **Drift** — a three-gate ingest pipeline keeps your fork synchronized with upstream daily. Protected files survive every merge automatically.
2. **Contribution quality** — a staging workflow that produces professional, reviewable PRs: standalone branches from `upstream-mirror`, pre-written issue drafts, pre-filled PR descriptions with all required sections.

---

## How It Works

```
upstream/main
    ↓  fetch + reset
upstream-mirror                 ← contribution branches start here
    ↓  merge into temp staging
sync/staging-TIMESTAMP
    ↓  Gate 1: Build check
    ↓  Gate 2: Lint
    ↓  Gate 3: Tests
integration  ← LKG-TIMESTAMP tag created here
    ↓  manual merge (after review)
develop
    ↑  contribution commits cherry-picked here too
```

Every upstream sync goes through staging first. `integration` is never touched until all three gates pass. On any failure, `integration` is left exactly as it was.

---

## Branch Rules

There are two kinds of work branches. Getting this wrong is the most common mistake.

| Work type | Branch from | Merge to | Goes upstream? |
|-----------|-------------|----------|----------------|
| Fix, feature, docs, refactor | `upstream-mirror` | `develop` (cherry-pick) | Yes — this is the default |
| Pipeline, fork CI, fork docs | `develop` | `develop` (merge) | No — narrow exception |

**The default is upstream-candidate.** Fork-only is the narrow exception. If you're unsure, it's upstream-candidate.

```bash
# Upstream-candidate branch
git fetch origin upstream-mirror
git checkout -b fix/thing origin/upstream-mirror
# ... make the change, single clean commit ...
git checkout develop && git cherry-pick <hash>
git checkout fix/thing   # branch stays — it's the upstream PR staging
```

---

## Contribution Workflow

Each contribution goes through five stages before it's filed:

```
1. Issue        Create a fork issue. No branch without an issue.
2. Branch       From upstream-mirror. One change per branch.
3. Cherry-pick  Get the fix into develop without contaminating the branch.
4. Draft        Write PR draft (docs/fork/upstream/pr-drafts/) and issue draft
                (docs/fork/upstream/issue-drafts/) while the work is fresh.
5. File         Issue first → get the number → fill into PR draft → open PR.
```

The issue draft and PR draft are separate files, both pre-written and ready to paste into GitHub. The two-step filing order (issue before PR) is enforced by most upstream projects' contribution guidelines — having both drafts ready means filing takes minutes, not an hour of writing.

See `docs/filing-guide.md` for the complete filing procedure, PR template sections, screenshot rules, and the upstream bot requirements.

---

## What's Included

```
FORK_WORKBENCH_TEMPLATE.md          Branch architecture, rules, pipeline reference
CHEAT_SHEET.md                      One-page daily operations reference
docs/
  filing-guide.md                   How to file professional upstream issues and PRs
  fork/
    issue-tracker.md                Issue-to-branch map
    changes-from-upstream.md        Record of every deliberate fork divergence
    upstream/
      pr-status.md                  Status of all staged upstream contributions
      pr-drafts/                    PR drafts, one file per branch
      issue-drafts/                 Issue drafts, one file per branch
  runbook.md                        Every pipeline failure mode with recovery steps
tooling/sync-upstreams/
  upstream_ingest_pipeline.py       Python pipeline (uv/ruff/pytest)
  upstream_ingest_pipeline.sh       Node.js pipeline (pnpm/eslint/vitest)
  rollback_to_lkg.py                Roll back integration to any previous LKG tag
  gate_failure_tests.py             Verify pipeline gates correctly block failures
.github/workflows/
  sync-upstream.yml                 Scheduled CI: daily ingest, standalone
  sync-upstream-reusable.yml        Reusable workflow for multi-schedule composability
```

---

## Setup

**1. Create the branch structure**

```bash
git checkout -b upstream-mirror origin/main
git checkout -b integration upstream-mirror
git checkout -b develop integration
git push origin upstream-mirror integration develop
```

**2. Configure the pipeline**

Open `tooling/sync-upstreams/upstream_ingest_pipeline.py` (or `.sh` for Node.js). Set:
- `UPSTREAM_REMOTE` — the upstream repo URL
- `UPSTREAM_BRANCH` — the branch to track (usually `main` or `dev`)
- `PROTECTED_FILES` — files to restore after every upstream merge
- Gate commands — uncomment the commands that match your ecosystem

**3. Set up CI**

Copy `.github/workflows/sync-upstream.yml` into your fork. Set the `UPSTREAM_REMOTE_URL` and uncomment your ecosystem's gate section. Create a `GH_PAT` secret (or configure GitHub App authentication — see the comments in the workflow file for both options).

**4. Verify**

```bash
git checkout integration
python3 tooling/sync-upstreams/upstream_ingest_pipeline.py --dry-run
```

**5. First sync**

```bash
python3 tooling/sync-upstreams/upstream_ingest_pipeline.py --push
```

---

## Ecosystem Support

| Ecosystem | Pipeline | Gate 1 | Gate 2 | Gate 3 |
|-----------|----------|--------|--------|--------|
| Python (uv) | `upstream_ingest_pipeline.py` | `uv lock --check` | `ruff check .` | `pytest` |
| Node.js (pnpm) | `upstream_ingest_pipeline.sh` | `pnpm install` | `eslint .` | `vitest run` |
| Rust | Adapt either script | `cargo check` | `cargo clippy` | `cargo test` |
| Go | Adapt either script | `go build ./...` | `golangci-lint run` | `go test ./...` |

---

## Design Decisions

**Staging branch isolation.** The pipeline never writes to `integration` directly. All work happens on `sync/staging-TIMESTAMP`. On any failure, `integration` is untouched and the staging branch is cleaned up. This is the same pattern used by Nixpkgs and Homebrew's update bots.

**LKG tags.** Every successful promotion tags `integration` with `LKG-YYYYMMDD-HHMM`. If a bad upstream merge lands, `rollback_to_lkg.py` resets `integration` to any previous tag in seconds. The tags accumulate as a rollback history.

**Protected files survive every sync.** Fork-specific files — the pipeline itself, CI, and anything with local patches — are listed in `PROTECTED_FILES`. After every upstream merge, the pipeline restores them to their `integration` state. Upstream can never silently overwrite them, and you never need to re-apply patches manually.

**Two-track branch classification.** Every branch is either upstream-candidate (the default) or fork-only (narrow exception). Upstream-candidate branches start from `upstream-mirror` so they contain no fork history — they are PR-ready from day one. Fork-only branches start from `develop` and stay there. Mixing these up produces PRs that can't be merged without rebasing hundreds of commits.

**Issue-first, always.** Every upstream PR needs a corresponding upstream issue filed first, even if a related issue already exists. This is what most upstream contribution guidelines require, and it produces better PR review conversations. Having the issue draft pre-written removes the friction that makes contributors skip this step.

**One PR per concern.** Each contribution branch carries exactly one logical change. This makes reviews faster, reverts safer, and cherry-picks to other branches trivial.

---

## CI Options

**Standalone** (`sync-upstream.yml`): A self-contained workflow that runs on a schedule. Copy it directly, configure it, and it works independently.

**Reusable** (`sync-upstream-reusable.yml`): A `workflow_call` workflow that can be called from other workflows with parameters. Use it when you want to run the sync on multiple schedules or compose it with other CI jobs.

```yaml
# Example caller
on:
  schedule:
    - cron: "0 */6 * * *"
jobs:
  sync:
    uses: ./.github/workflows/sync-upstream-reusable.yml
    with:
      upstream-remote: "https://github.com/upstream-org/project.git"
      ecosystem: python
    secrets:
      GH_PAT: ${{ secrets.GH_PAT }}
```

Both workflows support GitHub App token authentication (recommended over PATs — short-lived, permission-scoped, auto-revoked). See the commented-out section in each workflow file.

---

## Reference

- `FORK_WORKBENCH_TEMPLATE.md` — complete branch architecture, pipeline internals, pre-flight checklist, release procedure
- `docs/filing-guide.md` — upstream issue and PR filing: templates, bot requirements, screenshot rules, cross-platform notes
- `docs/runbook.md` — every pipeline failure mode with step-by-step recovery
- `CHEAT_SHEET.md` — daily operations in one page

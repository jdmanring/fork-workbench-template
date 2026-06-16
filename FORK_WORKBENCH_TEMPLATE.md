# Fork Workbench Template

> **The standard for contribution workbenches.** This document is the authoritative reference for the branch architecture, workflow rules, and operational procedures of this fork. Read it completely before touching any branch.

This fork is a contribution workbench. Every fix, feature, and document defaults to upstream-candidate unless it specifically manages the fork/upstream relationship.

---

## Branch Architecture

```
upstream/main → upstream-mirror → sync/staging-* → [gates] → integration → develop → main
                                      ↑
                                contribution branches
```

| Branch | Role | Push? | Description |
|--------|------|-------|-------------|
| `upstream/main` | Source of truth | Read-only | The upstream repo |
| `upstream-mirror` | Exact mirror | Fast-forward only | Always matches `upstream/main` HEAD |
| `integration` | Vetted upstream changes | Force-push | Only the pipeline writes here; never commit directly |
| `develop` | Primary working branch | Force-push | All fork work lands here eventually |
| `main` | Stable fork releases | Merge only | For downstream consumers; never pull back into workbench |
| `feat/*`, `fix/*`, `chore/*` | Contribution branches | Force-push | Individual PR candidates, based on `upstream-mirror` |
| `fork/*` | Fork infrastructure | Push | Fork-specific docs, tooling, PR drafts |
| `sync/staging-*` | Temporary pipeline branches | None | Created and deleted automatically by the pipeline |

---

## Two Kinds of Work Branches — Different Origins

This is the most important rule. There are two categories of work and they require different branch origins.

**The default is upstream-candidate.** Fork-only is the narrow exception.

### Category 1: Upstream-Candidate (the default — almost all work)

These branches are staging for upstream pull requests. They must:
- Contain **only the changes for that one fix or feature**
- Start from `upstream-mirror` so they have no fork history
- Have a **single clean commit** (or a small number of tightly related commits)

```bash
git fetch origin upstream-mirror
git checkout -b fix/short-description origin/upstream-mirror
# ... do work, commit ...
git checkout develop
git cherry-pick <commit-hash>
git checkout fix/short-description   # branch stays — it's the upstream PR staging
```

The branch stays permanently as the upstream PR staging. Do not delete it after cherry-picking to develop.

### Category 2: Fork-Only (narrow exception)

These branches will never go upstream. They branch from `develop` and merge back. Fork-only is **only**:
- The sync pipeline (`tooling/sync-upstreams/` or equivalent)
- Fork CI (`.github/workflows/sync-upstream.yml` or equivalent)
- Fork management docs (`docs/fork/`, workflow documentation)

If you are unsure whether something belongs here, it belongs in Category 1.

```bash
git checkout develop
git checkout -b feat/short-description
# ... do work, commit ...
git checkout develop
git merge feat/short-description
```

---

## Remotes

```
origin    → git@github.com:<you>/<project>.git          (your fork — normal dev target)
upstream  → git@github.com:<upstream-org>/<project>.git  (source — NEVER push here)
```

---

## Issue-First Workflow

Every piece of work starts with a GitHub issue. No exceptions.

```
1. Create issue on your fork's GitHub
   - Bug: include OS, numbered Steps to Reproduce, Expected/Actual Behaviour
   - Enhancement: include Area, Problem/Motivation, Proposed Solution

2. Determine work category:
   - Upstream-candidate → branch from upstream-mirror
   - Fork-only          → branch from develop

3. Do the work; commit cleanly

4. Cherry-pick (upstream-candidate) or merge (fork-only) to develop

5. If upstream-candidate:
   - Branch stays at single clean commit, ready to file a PR
   - Write PR draft in docs/fork/upstream/pr-drafts/ — must include "How to Test" steps
   - Write issue draft in docs/fork/upstream/issue-drafts/ — title and body ready to paste
   - Update docs/fork/upstream/pr-status.md
   - File: issue first (from issue-drafts/), then PR (from pr-drafts/)
   - See docs/filing-guide.md for complete upstream issue and PR filing instructions

6. Close the fork issue when the fix is confirmed working
```

---

## Upstream Ingest Pipeline

Upstream changes flow into this fork through a verified pipeline. **Never bypass it.**

```
upstream/main
    ↓  git fetch + reset
upstream-mirror
    ↓  merge into temp staging branch off integration
sync/staging-TIMESTAMP
    ↓  Gate 1: Build verification (compile / typecheck / lockfile check)
    ↓  Gate 2: Lint
    ↓  Gate 3: Tests (or project-specific verification)
integration  [ff-only merge + LKG-TIMESTAMP tag]
    ↓  manual merge
develop
```

### Running the pipeline

```bash
git checkout integration
python3 tooling/sync-upstreams/upstream_ingest_pipeline.py           # full run
python3 tooling/sync-upstreams/upstream_ingest_pipeline.py --dry-run  # gates only
python3 tooling/sync-upstreams/upstream_ingest_pipeline.py --skip-tests  # skip test gate
python3 tooling/sync-upstreams/upstream_ingest_pipeline.py --push     # push after success
```

### CI automation

Set up a scheduled CI workflow (daily is sufficient) that runs the pipeline automatically. See `.github/workflows/sync-upstream.yml` in this template for a starting point.

### Promoting integration to develop

The pipeline lands changes on `integration`. To get them into `develop`:

```bash
git checkout develop
git merge integration
```

This is a manual step — the pipeline does not auto-merge to `develop`.

---

## Gates — Customize to Your Project

The pipeline has three gates. **All three must pass** before upstream changes are promoted to `integration`. The gates must match your project's actual tech stack — a pipeline copied from a different project will fail.

### Gate 1: Build Verification (lockfile + compile)

Verifies dependencies are consistent and the project compiles. This is the most important gate — if this fails, nothing else matters.

**For Node.js projects (npm):**
```bash
npm ci --ignore-scripts
```
This installs exactly what's in `package-lock.json`. If the lockfile is out of sync with `package.json`, it fails. Never use `npm install` for this gate — it silently updates the lockfile.

**For Node.js projects (pnpm):**
```bash
pnpm install --frozen-lockfile
```

**For Python projects (uv):**
```bash
uv lock --check
```
Only works if a root `pyproject.toml` exists. If your project has no root `pyproject.toml` (e.g., a Node.js project with only a Python SDK sub-project), **do not use this gate** — use `npm ci` instead.

**For Rust projects:**
```bash
cargo check
```

### Gate 2: Lint

Verifies code style. Use whatever linter your project already uses — do not introduce a new one.

**For TypeScript/JavaScript projects:**
```bash
npx eslint . --ext .ts,.tsx --max-warnings 0
```

**Warning about `--max-warnings 0`:** This is strict. If the upstream codebase has pre-existing lint warnings (which is common), this gate will fail on every sync. Two strategies:

- **Strict (recommended for new projects):** Fix all warnings on `integration` before running the pipeline. The pipeline then catches any new warnings from upstream.
- **Lenient (for projects with lint debt):** Omit `--max-warnings 0` and use `--max-warnings <N>` with a threshold. Document the current warning count and fail only if it increases.

**For Python projects:**
```bash
ruff check .
```

### Gate 3: Tests

Verifies the test suite passes. This gate is the most likely to be slow, so it supports a `--skip-tests` flag for CI.

**For Node.js projects (Vitest):**
```bash
npx vitest run
```

**For Python projects:**
```bash
python -m pytest
```

### Adapting Gates When Copying the Pipeline

The pipeline scripts in `tooling/sync-upstreams/` are templates — they must be adapted to your project. The most common mistake is copying a pipeline from a different ecosystem (e.g., using `uv lock --check` on a Node.js project).

**Checklist when setting up the pipeline on a new fork:**

1. Identify your project's package manager: check for `package.json`, `pnpm-lock.yaml`, `uv.lock`, `Cargo.toml`
2. Set Gate 1 to the matching lockfile check command
3. Identify your linter: check for `eslint.config.js`, `pyproject.toml` (ruff config), `.golangci.yml`
4. Set Gate 2 to the matching lint command
5. Identify your test runner: check for `vitest.config.ts`, `pytest.ini`, `go.mod`
6. Set Gate 3 to the matching test command
7. Run `--dry-run` to verify all gates pass on the current state

**Do not skip Gate 1.** If your project has no lockfile, create one. The lockfile gate is the primary defense against "works on my machine" divergence.

---

## Last Known Good (LKG) Tags

Every successful pipeline promotion creates an annotated tag `LKG-YYYYMMDD-HHMM`. To roll back:

```bash
git tag -l "LKG-*" | sort -r | head -10          # list tags
git checkout LKG-20260523-1200                     # inspect
git checkout integration
git reset --hard LKG-20260523-1200                 # roll back (destructive)
```

A `rollback_to_lkg.py` script is provided in `tooling/sync-upstreams/` for safe rollback.

---

## Protected Files

The pipeline restores these files to their `integration` state after every upstream merge, preventing upstream from overwriting fork-specific code:

| Protected | Why |
|-----------|-----|
| `tooling/sync-upstreams/upstream_ingest_pipeline.py` | The pipeline itself |
| `.github/workflows/sync-upstream.yml` | Fork-only workflow — does not exist upstream |
| Fork-specific README sections | Fork may have different installation/setup instructions |
| Fork-specific config files | Fork may have local configuration upstream doesn't have |

To add a new fork-specific file to protection, add it to `PROTECTED_FILES` in the pipeline source.

---

## Pipeline Failure Recovery

See `docs/runbook.md` for detailed failure recovery procedures. Summary:

### Gate failure (build/lint/test)

Upstream introduced a regression. Do NOT bypass the gate. Investigate what broke. Options:
1. File an upstream issue; wait for them to fix it
2. Apply a minimal fix on the staging branch, then re-run gates
3. If urgent: run `--dry-run` to understand scope, then decide

### Merge conflict

The pipeline aborts and `integration` is untouched. The staging branch contains the conflict.

```bash
git checkout sync/staging-TIMESTAMP
# Resolve conflicts in the listed files
git add <resolved files>
git commit -m "chore(sync): resolve merge conflict with upstream"
git checkout integration
git merge --ff-only sync/staging-TIMESTAMP
git tag -a LKG-MANUAL -m "Last Known Good — manual conflict resolution"
git branch -D sync/staging-TIMESTAMP
```

### Pre-flight failure

| Cause | Fix |
|-------|-----|
| Not on `integration` branch | `git checkout integration` |
| Uncommitted changes | `git stash` or commit them |
| Missing `upstream` remote | `git remote add upstream <url>` |
| Missing tooling dependency | Install the required tool (see gate checklist above) |

### Upstream introduces type errors or lint warnings

Sometimes upstream merges code that doesn't pass its own typecheck or lint. This is not your fork's fault, but the pipeline gates will block on it.

**Diagnosis:** Run the failing gate locally on `upstream/main` (not your fork) to confirm the error exists upstream:
```bash
git fetch upstream
git stash
git checkout upstream/main
npx eslint . --ext .ts,.tsx  # or the failing gate
```

**If the error exists upstream:** You have three options:
1. **Wait for upstream to fix it.** File an upstream issue. Meanwhile, your fork is blocked.
2. **Apply a minimal fix on the staging branch.** Fix only what the gate requires, commit on the staging branch, and re-run. Document the fix so it can be reverted when upstream catches up.
3. **Lower the gate strictness temporarily.** For example, switch from `--max-warnings 0` to `--max-warnings <N>` where N is the current upstream warning count. Document the threshold so future agents know it's a workaround, not a standard.

**Never bypass a gate permanently.** If you lower a gate's strictness, create an issue to restore it once upstream is fixed.

### Merge conflict markers in upstream code

Occasionally, upstream merges code with unresolved merge conflict markers (`<<<<<<<`, `=======`, `>>>>>>>`). This happens when upstream maintainers resolve conflicts incorrectly or when a rebase goes wrong.

**Detection:** The build gate will fail with errors like `TS1185: Merge conflict marker encountered`.

**Resolution:**
```bash
# Find all files with conflict markers
grep -rl '<<<<<<<' src/ --include='*.ts' --include='*.tsx'

# For each file, resolve manually — there is no safe auto-resolution
# Choose the correct side (usually HEAD/theirs) and remove markers
# Then commit the fix on the staging branch
git add <resolved files>
git commit -m "chore(sync): resolve merge conflict markers from upstream"
```

**Prevention:** This is an upstream quality issue. If it happens repeatedly, consider filing an upstream issue about their merge process.

---

## Pre-Commit Hook Bypass for Pipeline Operations

The pipeline commits and tags on the `integration` branch. If your fork uses pre-commit hooks (husky, lint-staged, etc.), they may block pipeline commits — especially if the hooks require tooling that isn't installed in the current environment.

**The safe bypass:**

```bash
# For husky hooks:
HUSKY=0 git commit -m "chore(sync): ..."

# For git's built-in --no-verify (skips ALL hooks — pre-commit AND pre-push):
git commit --no-verify -m "chore(sync): ..."
```

**Rules:**
- Only bypass hooks during pipeline operations (sync commits, conflict resolution, protected file restoration)
- Never bypass hooks on `develop` or contribution branches
- If a hook fails because tooling is missing (e.g., `npm: command not found`), install the tool rather than bypassing — the hook is telling you something is wrong
- If a hook fails because of upstream-introduced lint warnings, that's a gate failure — fix it properly, don't bypass

---

## Pipeline Adaptation Guide

When setting up a new fork, the pipeline must be adapted to the project's tech stack. This is the most common source of pipeline failures.

### Step 1: Identify your project's toolchain

```bash
# Package manager
ls package.json pnpm-lock.yaml yarn.lock package-lock.json 2>/dev/null

# Linter
ls eslint.config.js .eslintrc.* pyproject.toml .golangci.yml 2>/dev/null

# Test runner
ls vitest.config.* jest.config.* pytest.ini go.mod Cargo.toml 2>/dev/null

# Build system
ls tsconfig.json Makefile Cargo.toml build.gradle 2>/dev/null
```

### Step 2: Configure the pipeline

Edit `tooling/sync-upstreams/upstream_ingest_pipeline.py` (or `.sh`) to use the correct commands. See the "Gates" section above for the mapping.

### Step 3: Verify with dry-run

```bash
git checkout integration
python3 tooling/sync-upstreams/upstream_ingest_pipeline.py --dry-run
```

All three gates should pass. If they don't, fix the issue before running a real sync.

### Step 4: Commit the adapted pipeline

```bash
git add tooling/sync-upstreams/
git commit -m "chore(pipeline): adapt gates for <ecosystem> project"
```

### Common adaptation mistakes

| Mistake | Symptom | Fix |
|---------|---------|-----|
| Using `uv lock --check` on a Node.js project | `error: No pyproject.toml found` | Switch to `npm ci --ignore-scripts` |
| Using `ruff` on a TypeScript project | `ruff: command not found` | Switch to `npx eslint . --ext .ts,.tsx` |
| Using `npm install` instead of `npm ci` | Lockfile silently updated, gate always passes | Switch to `npm ci` |
| Using `--max-warnings 0` on a project with lint debt | Gate fails on every sync | Use `--max-warnings <N>` with documented threshold |
| Copying a pipeline from a different fork without adaptation | Wrong tools, wrong commands | Run the adaptation checklist above |
| Missing tooling dependency | Install the required tool |

---

## Rebasing a Contribution Branch

When `upstream-mirror` advances (after a sync), contribution branches need rebasing so they apply cleanly on the current upstream code:

```bash
# Check if rebase is needed
git log --oneline fix/branch-name..upstream-mirror | wc -l   # if > 0, rebase needed
git checkout fix/branch-name
git rebase upstream-mirror
```

**Conflict resolution:** Keep your fix AND incorporate upstream's changes. Remove all conflict markers. `git add <file> && git rebase --continue`.

**If stuck:** `git rebase --abort` to return to pre-rebase state.

**After rebase:** Develop's cherry-picks may be stale. Verify with `git diff upstream-mirror develop -- <files>`. If develop shows regressions, re-cherry-pick the rebased commit.

## Releasing to Main

`main` is the stable distribution branch — upstream fully ingested, all patches applied, tested, and tagged. It has two distinct audiences:

- **Direct consumers** who want a patched version of the upstream project without managing the patches themselves. They pin to `main` and get stable, tested updates.
- **Downstream forks** that use your `main` as their own upstream source. A downstream project can run your fork's `main` through its own ingest pipeline, receiving your patches pre-applied. This composes naturally: `upstream → your fork's main → downstream project's integration → develop`.

`main` is a one-way output. Never pull it back into `develop` or use it as a branch origin for new work.

When ready to publish a stable release:

### Pre-release checklist

- [ ] `develop` branch is clean (`git status` shows nothing to commit)
- [ ] All intended contribution branches are merged to `develop`
- [ ] CI passes on `develop` (build, lint, tests)
- [ ] No uncommitted changes or unexpected files (`git diff --stat upstream-mirror..develop`)
- [ ] Changelog or release notes updated (if this fork maintains them)

### Release procedure

```bash
# 1. Ensure develop is ready
git checkout develop
git status
git log --oneline -5

# 2. Create a release tag (optional but recommended for tracking)
#    Use semantic versioning or date-based: v2026.06.12, v1.2.3, etc.
TAG="v$(date +%Y%m%d)"

# 3. Merge to main with --no-ff to preserve the merge commit as a record
git checkout main
git merge develop --no-ff -m "release: sync with upstream + contributions ${TAG}"

# 4. Tag the release
git tag -a "$TAG" -m "Release ${TAG} — upstream sync + fork contributions"

# 5. Push
git push origin main --follow-tags
```

**Why `--no-ff`:** The merge commit records when the release happened and what was included. This makes `git log --first-parent main` show a clean timeline of releases. (Pattern from Nixpkgs and most multi-branch projects.)

**When to release:**
- After a set of contribution branches has been merged to `develop` and tested
- After a major upstream version has been ingested and verified
- On a regular cadence (e.g., weekly, monthly) if this fork has downstream consumers

**What main should contain:**
- All upstream changes (via the ingest pipeline)
- All merged contribution branches (via develop)
- A clean, linear history that downstream consumers can rely on

**Never pull from main back into the workbench.** Main is a one-way release endpoint.

### Handling urgent patches when main has moved ahead

If a critical fix needs to land on main but develop has unreleasable changes:

```bash
# Create a hotfix branch from main (not develop)
git checkout -b hotfix/critical-fix main
# ... make the fix, commit ...
git checkout main
git merge hotfix/critical-fix --no-ff -m "hotfix: critical fix $(date +%Y%m%d)"
git push origin main

# Cherry-pick the fix back to develop so it stays in sync
git checkout develop
git cherry-pick <hotfix-commit-hash>
```

(Pattern from Homebrew: revert problematic PRs, release, then reapply.)

---

## Pre-Flight Checklist (before marking "Ready to File")

- [ ] Branch starts from `upstream-mirror` (not `develop`)
- [ ] Single clean commit (or tightly related commits)
- [ ] Diff contains only intended files — no fork-specific content
- [ ] No hardcoded paths, usernames, or tokens
- [ ] Commit message is clear and written for upstream reviewers
- [ ] Build verification passes
- [ ] Lint passes
- [ ] Tests pass locally
- [ ] Cross-platform considered: no platform-only assumptions in shared code

---

## Contribution Branch Health Checks

Before filing an upstream PR, verify your contribution branch is clean:

```bash
# Verify branch starts from upstream-mirror (not develop)
git merge-base fix/branch-name upstream-mirror
# Should return the same commit as: git rev-parse upstream-mirror

# Verify only your commits are on the branch
git log --oneline upstream-mirror..fix/branch-name
# Should show only your 1-3 commits

# Verify no fork-specific files in the diff
git diff upstream-mirror..fix/branch-name --name-only
# Should contain only files relevant to the fix/feature

# Verify the diff is clean (no conflict markers, no accidental whitespace)
git diff upstream-mirror..fix/branch-name --check
```

## Pre-Commit Hook Bypass

When the fork uses pre-commit hooks (husky, pre-commit, etc.) that require tooling not available in the current environment:

```bash
# Option A: Skip hooks for a single commit
HUSKY=0 git commit -m "your message"

# Option B: Use --no-verify (skips all hooks)
git commit --no-verify -m "your message"

# Option C: Skip specific hooks
SKIP=eslint,prettier git commit -m "your message"
```

**When to use this:** Only during pipeline operations (cherry-picks, sync commits). Never bypass hooks on direct development work.

## When Upstream Already Has the Change

Sometimes a contribution branch's changes have already been merged upstream. The pipeline handles this gracefully:

- **Cherry-pick produces empty commit:** `git cherry-pick <hash>` results in "nothing to commit". This means upstream already has the change. Skip it: `git cherry-pick --skip` or delete the contribution branch.
- **Gate passes but diff is empty:** If `git diff upstream-mirror..fix/branch-name` shows nothing, the branch has no unique content. Delete it — the work is already upstream.
- **Partial overlap:** If upstream has some but not all of your changes, rebase the branch and resolve the overlap: `git rebase upstream-mirror`, drop the duplicate commits, keep only what's still needed.

## Common Mistakes to Avoid

| Mistake | Why bad | Correct action |
|---------|---------|----------------|
| Classifying work as fork-only without a specific reason | Prevents valid upstream contributions | Default to upstream-candidate; fork-only is only the sync pipeline, fork CI, and fork management docs |
| Branching an upstream-candidate off `develop` | Pollutes branch with fork commits; PR would be unusable | Branch from `origin/upstream-mirror` |
| Committing to `upstream-mirror` | Commits destroyed on next sync | Use `upstream-mirror` as branch origin only; never commit there |
| Cherry-picking from `upstream/main` directly to `develop` | Bypasses gates; no verification | Run the ingest pipeline |
| Merging an upstream-candidate branch to `develop` | Would import upstream history into develop | Cherry-pick specific commits to develop |
| Closing an issue before verifying the fix works | Disrupts workflow tracking | Verify first, close after |
| Creating a branch without an issue | Untraceable work | Create issue first, always |
| Editing `develop` directly for upstream-candidate work | Creates untracked work with no branch/issue/PR | Branch from upstream-mirror, commit there, cherry-pick to develop |
| Forgetting to update docs | Future agents and contributors lack context | Update fork documentation for new/modified files |
| Copying a pipeline from a different fork without adaptation | Wrong tools, wrong commands, gates always fail | Run the Pipeline Adaptation Checklist — identify your toolchain first |
| Using `uv lock --check` on a Node.js project | `No pyproject.toml found` — pipeline can never pass | Use `npm ci --ignore-scripts` instead |
| Using `ruff` on a TypeScript project | `ruff: command not found` | Use `npx eslint . --ext .ts,.tsx` instead |

---

## Pipeline Invariants

The pipeline guarantees these properties on every run:

1. **Integration is never modified until all gates pass.** Work happens on a throwaway staging branch.
2. **On any failure, the pipeline returns to `integration`.** The finally block enforces this even if a failure occurs mid-sync.
3. **Staging branches are always cleaned up.** They do not accumulate.
4. **If already up to date, the pipeline exits cleanly** without creating branches or tags.
5. **Uncommitted changes to tracked files on integration are rejected at pre-flight.** They cannot accidentally be included in a promotion.

---

## Directory Structure for Fork Management

```
CONTRIBUTING.md                     # How upstream contributors interact with this fork
FORK_WORKBENCH_TEMPLATE.md          # This file — authoritative reference
docs/
  fork/
    README.md                       # Fork management hub — navigation
    issue-tracker.md                # Issue-to-branch mapping
    changes-from-upstream.md        # Master record of all fork divergence
    upstream/
      pr-status.md                  # Status of all staged upstream PRs
      pr-drafts/                    # PR draft files (see example-pr-draft.md for format)
      issue-drafts/                 # Upstream issue drafts (see example-issue-draft.md for format)
  filing-guide.md                   # How to file professional upstream issues and PRs
  runbook.md                        # Pipeline failure recovery procedures
tooling/
  sync-upstreams/
    upstream_ingest_pipeline.py     # Primary pipeline: fetch → stage → gate → promote
    upstream_ingest_pipeline.sh     # Node.js variant of the pipeline
    rollback_to_lkg.py              # Roll back integration to a previous LKG tag
    gate_failure_tests.py           # Verify pipeline gates correctly block failures
.github/
  workflows/
    sync-upstream.yml               # Scheduled CI: daily auto-ingest (standalone)
    sync-upstream-reusable.yml      # Reusable workflow (workflow_call) for composability
```

### Filing Guide

`docs/filing-guide.md` covers:
- Issue template (bug and feature request) — field-by-field walkthrough
- PR description bot — many projects auto-check sections; the guide lists what is typically required
- Full 8-section PR template in the correct order: Summary → Target branch → Linked Issue → Type of Change → Detail sections → Checklist → How to Test → Visual / UI changes
- Pre-filled checkboxes — how and why to pre-check Checklist and Type of Change in draft files
- "How to Test" requirements — numbered steps from a cold start; unit test results alone are not enough
- Screenshot rules — required for any UI change; must be from the running app; attach via drag-and-drop
- LLM agent policy — how to handle disclosure when filing work developed with AI assistance
- Cross-platform testing notes
- PR draft filing workflow (see `docs/fork/upstream/pr-drafts/example-pr-draft.md`)
- Issue draft workflow (see `docs/fork/upstream/issue-drafts/example-issue-draft.md`)
- Common mistakes that get PRs closed

# Fork Workbench Template

A comprehensive, multi-ecosystem template for managing a fork as a contribution workbench. Includes documentation, pipeline scripts, CI workflows, and a runbook — everything needed to operate a fork that:

1. Stays synchronized with upstream
2. Stages clean, individual upstream contributions
3. Releases a stable downstream product

## Project Structure

```
fork-workbench-template/
├── CONTRIBUTING.md                     # How upstream contributors interact with this fork
├── FORK_WORKBENCH_TEMPLATE.md          # Main guide — branch architecture, rules, workflow
├── README.md                           # This file
├── docs/
│   ├── fork/
│   │   ├── README.md                   # Fork management hub — navigation
│   │   ├── issue-tracker.md            # Issue-to-branch mapping
│   │   ├── changes-from-upstream.md    # Master record of all fork divergence
│   │   └── upstream/
│   │       └── pr-status.md            # Status of all staged upstream PRs
│   └── runbook.md                      # Pipeline failure recovery — every failure mode
├── tooling/
│   └── sync-upstreams/
│       ├── upstream_ingest_pipeline.py   # Python/uv pipeline
│       ├── upstream_ingest_pipeline.sh   # Node.js/pnpm pipeline
│       ├── rollback_to_lkg.py            # Roll back integration to a previous LKG tag
│       └── gate_failure_tests.py         # Verify pipeline gates correctly block failures
└── .github/
    └── workflows/
        ├── sync-upstream.yml             # Scheduled CI: daily auto-ingest (standalone)
        └── sync-upstream-reusable.yml    # Reusable workflow (workflow_call) for composability
```

## Quick Start

First time setting up the workbench? Do this in order:

```bash
# 1. Create the required branches
git checkout -b upstream-mirror origin/main   # or upstream's default branch
git checkout -b integration upstream-mirror
git checkout -b develop integration
git push origin upstream-mirror integration develop

# 2. Adapt the pipeline for your ecosystem
#    Python: edit tooling/sync-upstreams/upstream_ingest_pipeline.py
#    Node.js: edit tooling/sync-upstreams/upstream_ingest_pipeline.sh
#    Uncomment your gate commands, set PROTECTED_FILES

# 3. Set up CI
#    Copy .github/workflows/sync-upstream.yml
#    Uncomment your ecosystem section
#    Set the upstream remote URL
#    Create a GH_PAT secret (or GitHub App token — see "Authentication" below)

# 4. Verify
git checkout integration
python3 tooling/sync-upstreams/upstream_ingest_pipeline.py --dry-run
# or
bash tooling/sync-upstreams/upstream_ingest_pipeline.sh --dry-run

# 5. Run the first sync
python3 tooling/sync-upstreams/upstream_ingest_pipeline.py --push
```

## How to Use

1. Copy the files into your fork
2. Read `FORK_WORKBENCH_TEMPLATE.md` — it is the authoritative reference
3. Adapt the pipeline script for your ecosystem (Python or Node.js are provided)
4. Configure `PROTECTED_FILES` for your fork-specific files
5. Set up the CI workflow with your upstream remote URL
6. Create the required branches (`upstream-mirror`, `integration`, `develop`)
7. Run the pipeline once manually to verify: `python3 tooling/sync-upstreams/upstream_ingest_pipeline.py --dry-run`

## Ecosystem Support

| Ecosystem | Pipeline Script | Gate 1 (Build) | Gate 2 (Lint) | Gate 3 (Tests) |
|-----------|----------------|----------------|---------------|----------------|
| Python (uv) | `upstream_ingest_pipeline.py` | `uv lock --check` | `ruff check .` | `pytest` |
| Node.js | `upstream_ingest_pipeline.sh` | `pnpm install` | `npx eslint .` | `npx vitest run` |
| Rust | Adapt pipeline | `cargo check` | `cargo clippy` | `cargo test` |
| Go | Adapt pipeline | `go build ./...` | `golangci-lint run` | `go test ./...` |

## CI Workflows

Two options are provided:

### Standalone (`sync-upstream.yml`)
A self-contained scheduled workflow. Copy it, uncomment your ecosystem, set the upstream URL. Runs daily at 3am UTC.

### Reusable (`sync-upstream-reusable.yml`)
A `workflow_call` workflow designed to be called from another workflow. Use this when you want to:
- Call the sync from multiple schedules (e.g., 6h and 24h)
- Compose it with other workflows (e.g., run tests after sync)
- Pass parameters (ecosystem, branch names, skip-tests) from the caller

Example caller:
```yaml
# .github/workflows/sync-6h.yml
on:
  schedule:
    - cron: "0 */6 * * *"
jobs:
  sync:
    uses: ./.github/workflows/sync-upstream-reusable.yml
    with:
      upstream-remote: "https://github.com/QwenLM/qwen-code.git"
      ecosystem: node
    secrets:
      GH_PAT: ${{ secrets.GH_PAT }}
```

## Design Decisions

These choices are based on comparison of three real workbenches (qwen-code, odysseus, megalonyx-monorepo) and research into open-source fork patterns (Nixpkgs, Homebrew, and others).

### Staging branch isolation
The pipeline never modifies `integration` directly. All upstream changes merge into a throwaway `sync/staging-TIMESTAMP` branch first. Only after all gates pass does the pipeline fast-forward `integration`. On any failure, `integration` is untouched.

### LKG tags + rollback
Every successful promotion creates an annotated `LKG-YYYYMMDD-HHMM` tag. The `rollback_to_lkg.py` script provides safe rollback to any previous tag. This is the safety net — if a bad upstream merge lands, you can recover in seconds.

### Protected files
Fork-specific files (pipeline scripts, fork CI, docs) are restored to their `integration` version after every upstream merge, even when the merge produces no conflict. This prevents upstream from silently overwriting fork-specific patches.

### Two-category work classification
Every branch is either **upstream-candidate** (default — branches from `upstream-mirror`, cherry-picks to `develop`, targets upstream PR) or **fork-only** (narrow exception — branches from `develop`, merges back, never goes upstream). This prevents accidental fork-history pollution in upstream PRs.

### GitHub App token authentication (recommended)
The CI workflow supports both PAT and GitHub App token authentication. GitHub App tokens are short-lived (1 hour), scoped to specific permissions, and auto-revoked. This is superior to long-lived PATs. See the commented-out "Option A" section in `sync-upstream.yml`.

### Failure notification
The CI workflow can post a comment to a tracking issue when sync fails. Create an issue titled "Upstream Sync" and set the `SYNC_ISSUE_NUMBER` secret. This ensures you learn about sync failures even when away from the repo.

### Concurrency control
The CI workflow uses `concurrency` groups with `cancel-in-progress: true`. Only one sync runs at a time, and a manual re-run supersedes a stuck scheduled run.

### Draft PR on conflict
When the upstream merge creates complex conflicts, the runbook documents how to create a draft PR with conflict markers. This enables collaborative conflict resolution and provides visibility into what needs fixing.

## What This Template Does NOT Include

These are valid patterns but intentionally excluded because they add complexity without proportional benefit for most forks:

- **AI-assisted conflict resolution** — emerging pattern (vibegit, forksync) but not yet reliable enough for production use
- **Two-remote fork-as-filter** — megalonyx's architecture is specific to its constraint (private monorepo that can't be a GitHub fork). For normal forks, a single pipeline is sufficient
- **Merge queue gating** — Nixpkgs' two-stage merge queue is overkill for most forks. Staging branch isolation provides the same safety with less complexity
- **Auto-merge bots** — useful for dependency update PRs but not for upstream sync where human judgment is needed

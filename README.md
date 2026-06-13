# Fork Workbench

Most forks drift. You patch something locally, upstream keeps moving, your branch accumulates unrelated commits, and six months later you have a fork that can't be contributed back without a full rewrite. Meanwhile, the PRs you do file get closed: no linked issue, missing test steps, screenshots not attached, "we ask that you open an issue first."

This template solves both problems — keeping the fork synchronized and making every contribution file-ready from the start.

---

## The Core Idea

This template serves two purposes simultaneously, and they reinforce each other.

**As a contribution platform:** Every fix and feature is staged as a standalone upstream PR — clean branch from `upstream-mirror`, pre-written issue draft, pre-written PR description. Filing an upstream contribution takes minutes, not an afternoon.

**As a curated filter:** Your `main` branch is the output of passing upstream through your patches and verification gates. It represents a specific, known-good state — this version of the upstream project, with these fixes applied — that downstream consumers can track directly. Whether upstream eventually accepts your PRs or not, `main` provides a stable, tested distribution.

These aren't in conflict. The same workflow produces both: patches that are clean enough to file upstream are also clean enough to ship on `main`. The pipeline keeps everything synchronized so the filter output stays current without manual work.

**Synchronization:** A three-gate ingest pipeline fetches upstream, merges into a staging branch, runs build + lint + tests, and only promotes to `integration` after all gates pass. Fork-specific files are restored automatically after every merge. Last-known-good tags provide one-command rollback if something bad lands upstream.

**Contribution quality:** Each branch carries exactly one change, starts from `upstream-mirror` (so it contains no fork history), and comes with two pre-written files — an issue draft and a PR draft. When you're ready to file, the upstream issue title and body are ready to paste, and the PR description is fully filled in. The intended workflow is agent-assisted: an AI agent does the research, implements the fix, and writes both drafts while the context is fresh; the human author reviews and files. The agent never files — upstream projects prohibit agent-filed PRs, and a human author is required to stand behind the submission.

**Filter output:** `main` is a curated merge of upstream plus your patches, verified by the same gates as the ingest pipeline, tagged for downstream consumers to pin against.

---

## How It Works

There are two flows. They share a starting point — `upstream-mirror` — but move in opposite directions.

### Ingest: upstream → your fork

Keeps your fork synchronized with the upstream project.

```
upstream/main
    │  fetch + reset
    ▼
upstream-mirror
    │  merge into throwaway staging branch
    ▼
sync/staging-TIMESTAMP
    │  Gate 1: Build (uv lock --check, pnpm install, cargo check, ...)
    │  Gate 2: Lint  (ruff, eslint, clippy, ...)
    │  Gate 3: Tests (pytest, vitest, cargo test, ...)
    │  Protected files restored to integration state
    ▼
integration      ←── LKG-YYYYMMDD-HHMM tag created here
    │  manual merge after review
    ▼
develop
    │  --no-ff merge when releasing
    ▼
main             ←── tagged stable releases (v2026.06.12, v1.2.3, ...)
    │
    ▼
downstream consumers
```

`integration` is never touched until all three gates pass. On any failure, it is left exactly as it was and the staging branch is deleted.

### Contribute: your fork → upstream

Stages clean contributions and files them as upstream pull requests.

```
upstream-mirror
    │  branch from here — zero fork history
    ▼
fix/branch-name  (one logical change, one clean commit)
    │
    ├──► cherry-pick ──► develop   (fix is live in your working branch)
    │
    │  write drafts while context is fresh
    ▼
issue-drafts/<name>.md             pr-drafts/<name>.md
    │  title + body                    │  title + full description
    │  ready to paste                  │  all sections pre-filled
    │                                  │
    ▼                                  │
file upstream issue  ◄─────────────────┘
    │  receive issue number
    │  fill into Fixes # in PR draft
    ▼
file upstream PR: fix/branch-name → upstream:dev
    │
    ▼
upstream/main  (after acceptance)
```

The branch stays after the cherry-pick — it is the upstream PR staging target. One branch per concern. The issue is always filed before the PR.

---

## Branch Classification

There are exactly two kinds of work branches. This distinction is the most important thing to get right.

| Branch | Role | Direction |
|--------|------|-----------|
| `upstream-mirror` | Exact copy of upstream HEAD | Read-only input |
| `integration` | Gated, verified upstream changes | Pipeline output only |
| `develop` | Active working branch | Receives cherry-picks and fork-only merges |
| `main` | Stable releases — upstream + all patches applied | One-way output; never pulled back in |
| `feat/*` `fix/*` | Upstream-candidate contributions | Branch from `upstream-mirror`; cherry-pick to `develop` |
| Fork-only branches | Pipeline, CI, fork docs | Branch from `develop`; merge to `develop` |

**Contribution branches default to upstream-candidate.** Fork-only is the narrow exception: the sync pipeline, the CI workflow, and the docs in `docs/fork/`. Everything else — bug fixes, features, documentation, new files — defaults to upstream-candidate.

Upstream-candidate branches start from `upstream-mirror` and contain zero fork history. This is what makes them PR-ready from day one. Starting from `develop` instead is the most common mistake and produces branches that cannot be submitted without rebasing off hundreds of commits.

**`main` is a one-way output.** It is never pulled back into `develop` or used as a branch origin. Work only flows in one direction: upstream → develop → main → downstream consumers.

```bash
# The right way to start an upstream-candidate branch
git fetch origin upstream-mirror
git checkout -b fix/thing origin/upstream-mirror
# make the change — single clean commit
git checkout develop && git cherry-pick <hash>
git checkout fix/thing   # branch stays — it's the staging target for the upstream PR
```

---

## Contribution Lifecycle

```
Issue      →  Branch        →  Draft             →  File
────────────────────────────────────────────────────────
Create        From               Write              Issue first —
fork issue    upstream-mirror.   issue-drafts/      paste from draft,
first.        One change.        and pr-drafts/     get number, fill
No branch     No fork            while the work     into PR draft,
without       history.           is fresh.          then open PR.
an issue.
```

There are two separate issues involved and they serve different purposes. The **fork-side tracking issue** (first column) is filed on your own fork's issue tracker before you branch — it's how you track in-progress work and ensure no branch exists without a record. The **upstream issue** (last column) is filed against the upstream project at submission time, using a pre-written draft. They are filed at different points in the workflow and go to different places.

The issue draft and PR draft are separate files in `docs/fork/upstream/`. Both are pre-written with the upstream project's exact templates — issue body fully filled out, PR description with all required sections pre-checked. The two-step filing order (issue before PR) is what most upstream CONTRIBUTING.md files require, and having the drafts pre-written is the only way this step doesn't become a bottleneck.

When a related upstream issue already exists, file a new one scoped to your specific contribution and reference the existing issue in the body. "Fixes" goes on an issue you filed; `Related to #NNN` references an issue someone else filed.

---

## The Release Track

`develop` contains everything — upstream changes, applied patches, work in progress. `main` is the curated stable cut: upstream fully ingested, all patches applied, tested, tagged.

```bash
git checkout main
git merge develop --no-ff -m "release: upstream sync + patches v2026.06.12"
git tag -a "v2026.06.12" -m "Release v2026.06.12"
git push origin main --follow-tags
```

`--no-ff` is deliberate. The merge commit records exactly when the release happened and what it contained. `git log --first-parent main` gives a clean release timeline.

**Why this matters:** `main` is a distribution, not just a branch. It represents a known-good state: this version of the upstream project, with these specific patches applied, verified by the pipeline gates. That's something with standalone value.

Two concrete uses:

**People who want a patched version.** They can pin to `main`, track it like any dependency, and get stable updates when you release. They don't have to apply your patches themselves, and they're not riding the bleeding edge of `develop`.

**Downstream forks that want to build on your patches.** A downstream project can use your fork's `main` as its own upstream source — ingesting it through its own pipeline the same way you ingest from the original upstream. Your patches arrive pre-applied and pre-tested. The downstream project doesn't need to know how the patches were produced; it just tracks a clean, releasable branch.

```
upstream project
    ↓  (your ingest pipeline)
your fork's main  ←── tagged, stable, patched
    ↓  (downstream treats your main as their upstream remote)
downstream's upstream-mirror → sync/staging → [gates] → integration → develop
```

This chain works cleanly because `main` contains only what the downstream project needs: upstream changes plus your patches, with no fork-management state, no staging branches, no issue-drafts directory visible to the downstream pipeline.

**Hotfixes:** If a critical fix needs to land on `main` but `develop` has unreleased work, branch from `main`, fix it there, merge to `main`, then cherry-pick back to `develop`. Never let `main` drift ahead of `develop` without syncing the fix back. See `FORK_WORKBENCH_TEMPLATE.md` for the full hotfix procedure.

---

## What's Included

```
FORK_WORKBENCH_TEMPLATE.md          Complete branch architecture, pipeline internals,
                                    pre-flight checklist, release procedure
CHEAT_SHEET.md                      Daily operations in one page
docs/
  filing-guide.md                   Upstream issue and PR filing: templates, bot
                                    requirements, screenshot rules, LLM agent policy,
                                    cross-platform notes, two-step filing workflow
  fork/
    issue-tracker.md                Issue-to-branch map with labels and status
    changes-from-upstream.md        Every deliberate fork divergence, documented
    upstream/
      pr-status.md                  Status of all staged contributions
      pr-drafts/                    PR drafts — title, description, filing notes
      issue-drafts/                 Issue drafts — title and body, ready to paste
  runbook.md                        Every pipeline failure mode with recovery steps
tooling/sync-upstreams/
  upstream_ingest_pipeline.py       Python pipeline (uv / ruff / pytest)
  upstream_ingest_pipeline.sh       Node.js pipeline (pnpm / eslint / vitest)
  rollback_to_lkg.py                Roll back integration to any LKG tag
  gate_failure_tests.py             Verify gates correctly block bad states
.github/workflows/
  sync-upstream.yml                 Scheduled CI — daily ingest, self-contained
  sync-upstream-reusable.yml        Reusable workflow_call variant
```

---

## Setup

**1. Create the branch structure**

```bash
git remote add upstream <upstream-repo-url>   # the project you are forking
git fetch upstream

git checkout -b upstream-mirror upstream/main # track upstream's default branch
git checkout -b integration upstream-mirror
git checkout -b develop integration
git checkout -b main develop                  # stable release branch
git push origin upstream-mirror integration develop main
```

**2. Configure the pipeline**

Open `tooling/sync-upstreams/upstream_ingest_pipeline.py` (or `.sh` for Node.js). Three things to set:

- `UPSTREAM_REMOTE` — the upstream repo URL
- `UPSTREAM_BRANCH` — usually `main` or `dev`
- `PROTECTED_FILES` — files to restore after every upstream merge (the pipeline itself, your CI workflow, anything with local patches)

Uncomment the gate commands for your ecosystem.

**3. Set up CI**

Copy `.github/workflows/sync-upstream.yml` into your fork. Set `UPSTREAM_REMOTE_URL` and uncomment your ecosystem's gate section. Add a `GH_PAT` secret (or configure a GitHub App — see the comments in the workflow file; App tokens are short-lived and permission-scoped, which is preferable to a long-lived PAT).

**4. First sync**

```bash
git checkout integration
python3 tooling/sync-upstreams/upstream_ingest_pipeline.py --dry-run  # verify gates
python3 tooling/sync-upstreams/upstream_ingest_pipeline.py --push     # first real sync
```

---

## Ecosystem Support

| Ecosystem | Pipeline script | Gate 1 | Gate 2 | Gate 3 |
|-----------|----------------|--------|--------|--------|
| Python (uv) | `upstream_ingest_pipeline.py` | `uv lock --check` | `ruff check .` | `pytest` |
| Node.js (pnpm) | `upstream_ingest_pipeline.sh` | `pnpm install` | `eslint .` | `vitest run` |
| Rust | Adapt either script | `cargo check` | `cargo clippy` | `cargo test` |
| Go | Adapt either script | `go build ./...` | `golangci-lint run` | `go test ./...` |

---

## Design Decisions

**Staging branch isolation.** The pipeline merges into `sync/staging-TIMESTAMP`, not `integration`. `integration` is never touched until all gates pass. On any failure, it's left exactly as it was and the staging branch is deleted. This is the same isolation guarantee used by Nixpkgs' auto-update bots and Homebrew's CI: no partial states, no "partially merged upstream" situations.

**LKG tags and rollback.** Every successful promotion tags `integration` with `LKG-YYYYMMDD-HHMM`. `rollback_to_lkg.py` resets `integration` to any previous tag in one command. If upstream introduces a regression that slips through the gates, recovery takes seconds. The tag history also gives you a complete record of when each upstream batch landed.

**Protected files survive every sync.** Fork-specific files — the pipeline, the CI workflow, anything with local patches — are listed in `PROTECTED_FILES`. After every upstream merge, the pipeline restores them to their `integration` state before promoting. Upstream can never silently overwrite them. You never need to re-apply patches by hand.

**Two-track branch classification.** Upstream-candidate branches start from `upstream-mirror` and contain no fork history — a reviewer receiving the PR sees exactly the change, nothing else. Fork-only branches start from `develop` and stay there. The rule "when in doubt, upstream-candidate" makes the default the safe one: the worst case is a PR that doesn't get accepted, not a branch that can't be submitted.

**Pre-written drafts.** The issue draft and PR draft are written while the work is fresh — the context, root cause, and reasoning are clear in the author's head. Filing later, when the context has faded, is where vague problem descriptions and missing test steps come from. Drafts also enforce the filing order: you can't fill `Fixes #NNN` into the PR until the issue is filed and you have its number.

**One PR per concern.** Each contribution branch carries exactly one logical change. This makes reviews faster, reverts surgical, and cherry-picks to other branches trivial. A PR with five changes and a title like "various fixes" rarely gets merged quickly.

---

## What This Template Does Not Include

These patterns exist and are used in production, but are intentionally excluded because they add complexity without proportional benefit for most forks:

- **AI-assisted conflict resolution** — emerging tooling (vibegit, forksync) but not yet reliable enough for production use in a contribution workbench
- **Two-remote non-fork ingestion** — useful for private monorepos that cannot be GitHub forks of the upstream project and need to ingest from multiple sources; for a normal public fork, a single pipeline on one remote is simpler and sufficient
- **Merge queue gating** — Nixpkgs' two-stage merge queue is designed for a repo with thousands of contributors; staging branch isolation gives the same safety guarantee with far less infrastructure
- **Auto-merge bots** — appropriate for dependency updates but not for upstream sync, which requires human judgment about what landed and what conflicts need resolution

---

## Reference

- `FORK_WORKBENCH_TEMPLATE.md` — complete branch map, pipeline internals, pipeline invariants, pre-flight checklist, rebasing guide, release procedure
- `docs/filing-guide.md` — upstream issue templates, PR template sections, bot requirements, screenshot rules, LLM agent policy, two-step filing workflow, common mistakes
- `docs/runbook.md` — every pipeline failure mode with step-by-step recovery
- `CHEAT_SHEET.md` — daily operations in one page

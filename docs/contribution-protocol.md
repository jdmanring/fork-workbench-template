# Contribution Protocol (The "Zero-Defect" Manual)

This document defines the mandatory execution sequence for any agent (AI or human) performing work on this fork. Following this protocol is the primary mechanism for preventing contamination, orphaned branches, and technical debt.

## 1. The Golden Rule of Contributions
**Every single-purpose fix or feature must follow this lifecycle:**
`upstream-mirror` $\rightarrow$ `contribution-branch` $\rightarrow$ `develop` (via cherry-pick).

- **NEVER** branch an upstream contribution from `develop`.
- **NEVER** merge a contribution branch into `develop`.
- **NEVER** rebase onto a stale `upstream-mirror`.

---

## 2. Mandatory Execution Checklist

### Phase 0: Base Synchronization
Before starting any work or rebasing any existing branch:
1. [ ] **Check Sync Status**: Run `git rev-list origin/upstream-mirror..upstream/main`.
2. [ ] **Sync if Stale**: If the count is $> 0$, you MUST run the ingest pipeline to synchronize the mirror with the upstream source.
3. [ ] **Promote to Develop**: Merge the vetted integration branch into `develop` and verify the build.

### Phase 1: Contribution Audit (The "Cleanliness" Check)
Before integrating a branch, you must prove it is single-purpose.
1. [ ] **Analyze Commits**: Run `git log --oneline upstream-mirror..<branch>`.
2. [ ] **Detect Contamination**:
   - Does the branch contain both a fix AND dependency upgrades?
   - Does it contain unrelated "cleanup" commits?
   - Does it contain commits that are already on `develop`?
3. [ ] **Remediate Contamination**: If contaminated, you MUST NOT use the branch. Instead:
   - Identify the specific commit hashes of the "real" fix.
   - Create a NEW branch from the current `upstream-mirror`.
   - Cherry-pick ONLY the real fix commits.
   - Delete the contaminated local branch.

### Phase 2: Base & History Verification
1. [ ] **Verify Merge-Base**: Run `git merge-base <branch> upstream-mirror`.
2. [ ] **Handle Orphans**: If the merge-base is not a recent commit on `upstream-mirror` (i.e., it's an orphaned branch):
   - Do NOT attempt to rebase.
   - Re-create the contribution from the current `upstream-mirror` using cherry-picks of the original work.
3. [ ] **Rebase**: Perform `git rebase upstream-mirror`. Resolve conflicts manually; do not use `--skip`.

### Phase 3: Local Verification
1. [ ] **Pre-flight Check**: Run `git diff upstream-mirror..<branch> --check`.
2. [ ] **Build & Lint**: Run the project's build and lint commands.
3. [ ] **Targeted Testing**: Identify the specific tests covering the change and run them.

### Phase 4: Integration to Develop
1. [ ] **Switch to Develop**: `git checkout develop`.
2. [ ] **Cherry-pick**: `git cherry-pick <commit-hash>`.
3. [ ] **Final Verification**:
   - Run build and typecheck.
   - Run the targeted tests again on `develop`.
4. [ ] **Commit**: Use Conventional Commits (e.g., `fix(scope): ...`).

### Phase 5: Staging & Documentation
1. [ ] **Create Issue**: Draft the issue on the fork.
2. [ ] **Create PR Draft**: Create a PR draft in the designated documentation folder following the template.

---

## 3. Forbidden Shortcuts
- **NO** `git merge <branch> develop`.
- **NO** `git rebase` onto `develop` for upstream work.
- **NO** type-system bypasses (e.g., `as any`) to silence compiler errors during integration.
- **NO** bypassing lint/test gates because "the upstream is broken" (report it instead).

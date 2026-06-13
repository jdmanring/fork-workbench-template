# Fork Workbench Cheat Sheet

> One-page reference for daily operations. Print this. Pin it next to your monitor.

## Pipeline

```
upstream/main → upstream-mirror → sync/staging-* → [gates] → integration → develop → main
                                      ↑
                                contribution branches
```

## Daily Commands

```bash
# Sync upstream
git checkout integration
python3 tooling/sync-upstreams/upstream_ingest_pipeline.py --push

# Promote to develop
git checkout develop && git merge integration

# Check what's new upstream
git fetch upstream
git log --oneline upstream/main ^integration

# Check a contribution branch
git log --oneline upstream-mirror..fix/my-branch
git diff upstream-mirror..fix/my-branch --name-only

# Rebase a contribution branch after sync
git checkout fix/my-branch && git rebase upstream-mirror

# Roll back integration
python3 tooling/sync-upstreams/rollback_to_lkg.py

# Release to main
git checkout main && git merge develop --no-ff -m "release: $(date +%Y%m%d)"
git tag -a "v$(date +%Y%m%d)" -m "Release $(date +%Y%m%d)"
git push origin main --follow-tags
```

## Branch Origins

| Work type | Branch from | Merge to |
|-----------|-------------|----------|
| Upstream fix/feature | `upstream-mirror` | `develop` (cherry-pick) |
| Fork-only (CI, docs, pipeline) | `develop` | `develop` (merge) |

## Two Remotes

```
origin   → your fork (push here)
upstream → source (read-only, never push)
```

## Pre-Flight Checklist (before filing upstream PR)

- [ ] Branch from `upstream-mirror` (not `develop`)
- [ ] Single clean commit
- [ ] Diff has only intended files
- [ ] No hardcoded paths/tokens
- [ ] Build + lint + tests pass

## Failure Recovery

| Problem | Fix |
|---------|-----|
| Pre-flight fails | `git checkout integration && git stash` |
| Merge conflict | Resolve, commit, re-run pipeline |
| Gate fails | Fix upstream regression, re-run |
| Empty cherry-pick | Change is already upstream — skip |
| Need to roll back | `python3 tooling/sync-upstreams/rollback_to_lkg.py` |

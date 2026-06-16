#!/usr/bin/env bash
# ── Upstream Ingest Pipeline — Node.js / pnpm ────────────────────
#
# Propagates changes from upstream-mirror to integration through a
# verification pipeline: Sync → Gate(Build/Lint/Tests) → Promote.
#
# Usage:
#   bash tooling/sync-upstreams/upstream_ingest_pipeline.sh                        # full sync
#   bash tooling/sync-upstreams/upstream_ingest_pipeline.sh --dry-run              # gates only
#   bash tooling/sync-upstreams/upstream_ingest_pipeline.sh --skip-tests           # skip tests
#   bash tooling/sync-upstreams/upstream_ingest_pipeline.sh --push                 # push after success
#
# Adaptation guide:
#   1. Set INTEGRATION_BRANCH, MIRROR_BRANCH, UPSTREAM_BRANCH for your repo
#   2. Set REQUIRED_REMOTES to match your remote names
#   3. Edit PROTECTED_FILES to list your fork-specific files
#   4. Edit the gate commands to match your build/lint/test toolchain
#   5. Run --dry-run to verify
# ─────────────────────────────────────────────────────────────────

set -euo pipefail

# ── Configuration ────────────────────────────────────────────────
INTEGRATION_BRANCH="integration"
MIRROR_BRANCH="upstream-mirror"
UPSTREAM_BRANCH="main"  # upstream's default branch

# Fork-specific files that must not be overwritten by upstream merges
PROTECTED_FILES=(
    "tooling/sync-upstreams/upstream_ingest_pipeline.sh"
    ".github/workflows/sync-upstream.yml"
    # Add your fork-specific files here:
    # "package.json"
    # "pnpm-lock.yaml"
)

# Files that always conflict (e.g., lockfile format differences)
# Auto-resolved by keeping the fork's version
AUTO_RESOLVE_OURS=(
    "package-lock.json"  # if fork uses pnpm but upstream uses npm
    # "yarn.lock"
)

# ── Colors ──────────────────────────────────────────────────────
BLUE='\033[0;34m'
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[0;33m'
NC='\033[0m'

log_info()  { echo -e "${BLUE}[INFO]${NC} $*"; }
log_ok()    { echo -e "${GREEN}[OK]${NC} $*"; }
log_warn()  { echo -e "${YELLOW}[WARN]${NC} $*" >&2; }
log_error() { echo -e "${RED}[FAIL]${NC} $*" >&2; }

# ── Parse arguments ─────────────────────────────────────────────
DRY_RUN=false
SKIP_TESTS=false
PUSH=false

for arg in "$@"; do
    case "$arg" in
        --dry-run)    DRY_RUN=true ;;
        --skip-tests) SKIP_TESTS=true ;;
        --push)       PUSH=true ;;
        *)
            echo "Unknown argument: $arg"
            echo "Usage: $0 [--dry-run] [--skip-tests] [--push]"
            exit 1
            ;;
    esac
done

# ── Find repo root ──────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# ── Git helper ──────────────────────────────────────────────────
git_run() {
    (cd "$REPO_ROOT" && git "$@")
}

git_output() {
    (cd "$REPO_ROOT" && git "$@" 2>/dev/null)
}

current_branch() {
    git_output rev-parse --abbrev-ref HEAD
}

# ── Pre-flight ──────────────────────────────────────────────────
preflight() {
    log_info "Running pre-flight checks..."

    local branch
    branch=$(current_branch)
    if [[ "$branch" != "$INTEGRATION_BRANCH" ]]; then
        log_error "Must be on '$INTEGRATION_BRANCH' branch. Current: '$branch'"
        return 1
    fi

    if ! git_output remote | grep -q "^origin$"; then
        log_error "Missing required remote: origin"
        return 1
    fi
    if ! git_output remote | grep -q "^upstream$"; then
        log_error "Missing required remote: upstream"
        return 1
    fi

    if ! git_run diff --quiet HEAD 2>/dev/null; then
        log_error "Integration branch has uncommitted changes — stash or commit before syncing."
        return 1
    fi

    log_ok "Pre-flight passed."
    return 0
}

# ── Sync mirror ─────────────────────────────────────────────────
sync_mirror() {
    log_info "Fetching upstream/$UPSTREAM_BRANCH..."
    git_run fetch upstream "$UPSTREAM_BRANCH"

    local new_count
    new_count=$(git_output rev-list --count "upstream/$UPSTREAM_BRANCH" "^$INTEGRATION_BRANCH" 2>/dev/null || echo "0")

    if [[ "$new_count" == "0" ]]; then
        log_ok "Already up to date — nothing to sync."
        return 1  # nothing to do
    fi

    log_info "$new_count new upstream commit(s) to integrate."
    log_info "Resetting $MIRROR_BRANCH to upstream/$UPSTREAM_BRANCH..."
    git_run checkout -f "$MIRROR_BRANCH"
    git_run reset --hard "upstream/$UPSTREAM_BRANCH"
    git_run checkout "$INTEGRATION_BRANCH"
    log_ok "Mirror synchronized."
    return 0
}

# ── Create staging branch ───────────────────────────────────────
STAGING_BRANCH=""

create_staging() {
    local timestamp
    timestamp=$(date +%Y%m%d%H%M%S)
    STAGING_BRANCH="sync/staging-$timestamp"
    log_info "Creating staging branch: $STAGING_BRANCH"
    git_run checkout -b "$STAGING_BRANCH"
}

# ── Restore protected files ─────────────────────────────────────
restore_protected_files() {
    local integration_ref="$1"
    local restored=()

    for path in "${PROTECTED_FILES[@]}"; do
        git_run checkout "$integration_ref" -- "$path" 2>/dev/null || true
        restored+=("$path")
    done

    # Check if any protected files were staged
    local staged
    staged=$(git_output diff --cached --name-only 2>/dev/null || true)
    local found_protected=false
    for f in $staged; do
        for p in "${PROTECTED_FILES[@]}"; do
            if [[ "$f" == "$p" ]]; then
                found_protected=true
                break
            fi
        done
    done

    if [[ "$found_protected" == "true" ]]; then
        log_info "Restored ${#restored[@]} protected file(s): ${restored[*]}"
        # --no-verify may not exist on older git; HUSKY=0 covers husky hooks
        HUSKY=0 git_run commit -m "chore(sync): restore fork-owned files after upstream merge" --no-verify 2>/dev/null || \
        HUSKY=0 git_run commit -m "chore(sync): restore fork-owned files after upstream merge" 2>/dev/null || true
    else
        log_ok "Protected files unchanged by upstream — no restoration needed."
    fi
}

# ── Merge mirror into staging ───────────────────────────────────
merge_mirror_to_stage() {
    local integration_ref
    integration_ref=$(git_output rev-parse HEAD)

    log_info "Merging $MIRROR_BRANCH into $STAGING_BRANCH..."
    if git_run merge "$MIRROR_BRANCH" --no-edit 2>/dev/null; then
        log_ok "Merge clean."
        restore_protected_files "$integration_ref"
        return 0
    fi

    # Check for conflicts
    local conflict_files
    conflict_files=$(git_output diff --name-only --diff-filter=U 2>/dev/null || true)

    if [[ -z "$conflict_files" ]]; then
        # Merge failed but no conflicts — real error
        git_run merge --abort 2>/dev/null || true
        log_error "Merge failed with no conflicts — this is unexpected."
        return 1
    fi

    # Try auto-resolving known conflict files
    local has_unresolvable=false
    for f in $conflict_files; do
        local can_resolve=false
        for ar in "${AUTO_RESOLVE_OURS[@]}"; do
            if [[ "$f" == "$ar" ]]; then
                can_resolve=true
                break
            fi
        done
        if [[ "$can_resolve" == "false" ]]; then
            has_unresolvable=true
        fi
    done

    if [[ "$has_unresolvable" == "true" ]]; then
        git_run merge --abort 2>/dev/null || true
        log_error "Merge conflict — manual resolution required:"
        echo "$conflict_files" | while read -r f; do
            echo "  - $f"
        done
        echo ""
        echo "Resolve, commit, then re-run the ingest pipeline."
        return 1
    fi

    # Auto-resolve
    for f in $conflict_files; do
        for ar in "${AUTO_RESOLVE_OURS[@]}"; do
            if [[ "$f" == "$ar" ]]; then
                log_info "Auto-resolving $f (keeping ours)"
                git_run checkout --ours "$f"
                git_run add "$f"
            fi
        done
    done

    GIT_EDITOR=true git_run merge --continue 2>/dev/null || true
    log_ok "Merge clean (auto-resolved conflicts)."
    restore_protected_files "$integration_ref"
    return 0
}

# ── Cleanup staging ─────────────────────────────────────────────
cleanup_staging() {
    if [[ -z "$STAGING_BRANCH" ]]; then
        return 0
    fi
    local branch
    branch=$(current_branch)
    if [[ "$branch" == "$STAGING_BRANCH" ]]; then
        git_run checkout "$INTEGRATION_BRANCH" 2>/dev/null || true
    fi
    git_run branch -D "$STAGING_BRANCH" 2>/dev/null || true
    STAGING_BRANCH=""
}

# ── Gate 1: Build verification ──────────────────────────────────
#
# Uncomment ONE block based on your project's package manager.
# If your project has no lockfile, create one first.
#
gate_build() {
    log_info "Gate 1/3: Build verification..."

    # ── npm (Node.js) ────────────────────────────────────────────
    # Verifies package-lock.json is in sync and installs exactly
    # what's locked. Use --ignore-scripts to skip postinstall hooks
    # that may require build artifacts.
    if command -v npm &>/dev/null && [[ -f "package-lock.json" ]]; then
        if ! npm ci --ignore-scripts 2>/dev/null; then
            log_error "Build gate failed — npm ci failed."
            log_error "Fix: run 'npm install' to regenerate lockfile, then commit."
            return 1
        fi
    # ── pnpm (Node.js) ───────────────────────────────────────────
    # elif command -v pnpm &>/dev/null && [[ -f "pnpm-lock.yaml" ]]; then
    #     if ! pnpm install --frozen-lockfile 2>/dev/null; then
    #         log_error "Build gate failed — pnpm install failed."
    #         return 1
    #     fi
    # ── Python (uv) ──────────────────────────────────────────────
    # elif command -v uv &>/dev/null && [[ -f "pyproject.toml" ]]; then
    #     if ! uv lock --check 2>/dev/null; then
    #         log_error "Build gate failed — lockfile out of sync."
    #         log_error "Fix: run 'uv lock' to regenerate, then commit."
    #         return 1
    #     fi
    else
        log_error "No recognized package manager or lockfile found."
        log_error "Expected one of: package-lock.json, pnpm-lock.yaml, pyproject.toml"
        return 1
    fi

    log_ok "Build gate passed."
    return 0
}

# ── Gate 2: Lint ────────────────────────────────────────────────
#
# Uncomment ONE block based on your project's linter.
# Do NOT introduce a new linter — use whatever the project already has.
#
gate_lint() {
    log_info "Gate 2/3: Lint..."

    # ── ESLint (TypeScript/JavaScript) ──────────────────────────
    if command -v npx &>/dev/null && [[ -f "eslint.config.js" || -f ".eslintrc.js" || -f ".eslintrc.json" || -f ".eslintrc" ]]; then
        # --max-warnings 0 is strict. If upstream has pre-existing lint
        # warnings, use --max-warnings <N> where N is the current count.
        if ! npx eslint . --ext .ts,.tsx --max-warnings 0 2>/dev/null; then
            log_error "Lint gate failed."
            log_error "Fix: run 'npx eslint . --ext .ts,.tsx --fix' to auto-fix."
            return 1
        fi
    # ── Ruff (Python) ────────────────────────────────────────────
    # elif command -v ruff &>/dev/null || command -v uv &>/dev/null; then
    #     RUFF_CMD="ruff"
    #     command -v ruff &>/dev/null || RUFF_CMD="uv run ruff"
    #     if ! $RUFF_CMD check . 2>/dev/null; then
    #         log_error "Lint gate failed."
    #         return 1
    #     fi
    else
        log_warn "No recognized linter config found — skipping lint gate."
        log_warn "If your project has a linter, configure it in gate_lint()."
        return 0
    fi

    log_ok "Lint gate passed."
    return 0
}

# ── Gate 3: Tests ───────────────────────────────────────────────
#
# Uncomment ONE block based on your project's test runner.
# This gate supports --skip-tests for CI environments where tests
# are too slow or require services.
#
gate_tests() {
    if [[ "$SKIP_TESTS" == "true" ]]; then
        log_warn "Gate 3/3: Tests skipped (--skip-tests / CI mode)."
        return 0
    fi

    log_info "Gate 3/3: Tests..."

    # ── Vitest (Node.js) ─────────────────────────────────────────
    if command -v npx &>/dev/null && [[ -f "vitest.config.ts" || -f "vitest.config.js" ]]; then
        if ! npx vitest run 2>/dev/null; then
            log_error "Test gate failed."
            return 1
        fi
    # ── npm test (Node.js) ───────────────────────────────────────
    # elif [[ -f "package.json" ]]; then
    #     if ! npm test 2>/dev/null; then
    #         log_error "Test gate failed."
    #         return 1
    #     fi
    # ── pytest (Python) ──────────────────────────────────────────
    # elif command -v python3 &>/dev/null && [[ -f "pyproject.toml" || -f "pytest.ini" || -f "setup.cfg" ]]; then
    #     if ! python3 -m pytest 2>/dev/null; then
    #         log_error "Test gate failed."
    #         return 1
    #     fi
    else
        log_warn "No recognized test runner found — skipping test gate."
        return 0
    fi

    log_ok "Test gate passed."
    return 0
}

# ── Promotion ───────────────────────────────────────────────────
promote() {
    local staging_branch="$1"
    log_info "Promoting $staging_branch → $INTEGRATION_BRANCH..."
    git_run checkout "$INTEGRATION_BRANCH"
    git_run merge --ff-only "$staging_branch"

    local timestamp
    timestamp=$(date +%Y%m%d-%H%M)
    local tag="LKG-$timestamp"
    git_run tag -a "$tag" -m "Last Known Good — $timestamp"
    log_ok "Tagged as $tag."
    echo "$tag"
}

# ── Main pipeline ───────────────────────────────────────────────
main() {
    if [[ "$DRY_RUN" == "true" ]]; then
        log_warn "DRY RUN — gates will run against current state; no commits or tags."
    fi

    if ! preflight; then
        echo "PREFLIGHT"
        exit 1
    fi

    if [[ "$DRY_RUN" == "true" ]]; then
        log_info "[dry-run] Skipping sync and staging."
        if gate_build && gate_lint && gate_tests; then
            log_ok "[dry-run] All gates passed. Nothing promoted."
            echo "DRY_RUN"
            exit 0
        else
            echo "VERIFICATION"
            exit 1
        fi
    fi

    # Sync mirror
    if ! sync_mirror; then
        echo "UP_TO_DATE"
        exit 0
    fi

    # Create staging and merge
    create_staging

    if ! merge_mirror_to_stage; then
        cleanup_staging
        echo "PIPELINE_ERROR:Merge conflict"
        exit 1
    fi

    # Run gates
    if ! gate_build || ! gate_lint || ! gate_tests; then
        cleanup_staging
        echo "VERIFICATION"
        exit 1
    fi

    # Promote
    local tag
    tag=$(promote "$STAGING_BRANCH")

    # Push
    if [[ "$PUSH" == "true" ]]; then
        log_info "Pushing integration and tags to origin..."
        git_run push origin "$INTEGRATION_BRANCH"
        git_run push origin --tags
        log_ok "Pushed."
    else
        log_warn "Not pushing — run with --push or push manually: git push origin integration --follow-tags"
    fi

    echo "PROMOTION:$tag"
    exit 0
}

# Ensure cleanup on exit
trap cleanup_staging EXIT

main

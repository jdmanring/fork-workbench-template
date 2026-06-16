#!/usr/bin/env python3
"""
Upstream Ingest Pipeline
Propagates changes from upstream-mirror to integration through a
verification pipeline: Sync → Gate(Build/Lint/Tests) → Promote.

Usage:
    python3 tooling/sync-upstreams/upstream_ingest_pipeline.py                        # full sync
    python3 tooling/sync-upstreams/upstream_ingest_pipeline.py --dry-run              # gates only
    python3 tooling/sync-upstreams/upstream_ingest_pipeline.py --skip-tests           # sync, skip tests (CI mode)
    python3 tooling/sync-upstreams/upstream_ingest_pipeline.py --push                 # push after success

Adaptation guide (REQUIRED when setting up a new fork):
    1. Set INTEGRATION_BRANCH, MIRROR_BRANCH, UPSTREAM_BRANCH for your repo
    2. Set REQUIRED_REMOTES to match your remote names
    3. Edit PROTECTED_FILES to list your fork-specific files
    4. Edit the GateKeeper methods to match your build/lint/test commands
       — this is the most common source of pipeline failures
       — see detect_ecosystem() for auto-detection of common toolchains
    5. Run --dry-run to verify all gates pass

Tech stack detection:
    The detect_ecosystem() helper identifies your project's package manager,
    linter, and test runner from config files. Use it in your gate methods
    to auto-configure commands. If auto-detection is wrong, override manually.
"""

import argparse
import logging
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

LOG_FORMAT = "%(asctime)s [%(levelname)s] %(message)s"
logging.basicConfig(level=logging.INFO, format=LOG_FORMAT, stream=sys.stdout)
logger = logging.getLogger("upstream_ingest_pipeline")

REPO_ROOT = Path(__file__).parent.parent.parent.resolve()

# ── Branch names ──────────────────────────────────────────────────
INTEGRATION_BRANCH = "integration"
MIRROR_BRANCH = "upstream-mirror"
UPSTREAM_BRANCH = "main"  # upstream's default branch (often "main" or "master" or "dev")
REQUIRED_REMOTES = {"upstream", "origin"}

# ── Protected files ──────────────────────────────────────────────
# Files or directories owned by this fork that must not be overwritten
# by upstream merges. After each merge the pipeline restores these to
# their integration-branch state.
#
# - File paths restore the file via `git checkout ref -- <path>`
# - Directory paths (ending with "/") restore the entire tree and
#   remove any files upstream added that aren't in integration_ref
PROTECTED_FILES: list[str] = [
    "tooling/sync-upstreams/upstream_ingest_pipeline.py",
    ".github/workflows/sync-upstream.yml",
    # Add your fork-specific files here:
    # "README.md",
    # "pyproject.toml",
]

# ── Auto-resolve conflicts ───────────────────────────────────────
# Files that always conflict when merging upstream (e.g., lockfile
# format differences). The pipeline resolves these by keeping the
# fork's version ("--ours") automatically.
AUTO_RESOLVE_OURS: frozenset[str] = frozenset({
    "package-lock.json",  # if fork uses pnpm but upstream uses npm
    # Add your auto-resolve files here:
    # "Cargo.lock",
})


def detect_ecosystem(root: Path) -> dict[str, str]:
    """Detect the project's toolchain from config files.

    Returns a dict with keys: package_manager, linter, test_runner.
    Values are command strings suitable for subprocess, or "" if not detected.

    Use this in your gate methods to auto-configure commands:
        eco = detect_ecosystem(REPO_ROOT)
        if eco["package_manager"] == "npm":
            subprocess.run(["npm", "ci", "--ignore-scripts"], ...)
    """
    # Package manager
    if (root / "pnpm-lock.yaml").exists():
        pkg_mgr = "pnpm"
    elif (root / "package-lock.json").exists():
        pkg_mgr = "npm"
    elif (root / "yarn.lock").exists():
        pkg_mgr = "yarn"
    elif (root / "uv.lock").exists() or (root / "pyproject.toml").exists():
        pkg_mgr = "uv"
    elif (root / "Cargo.toml").exists():
        pkg_mgr = "cargo"
    elif (root / "go.mod").exists():
        pkg_mgr = "go"
    else:
        pkg_mgr = ""

    # Linter
    if (root / "eslint.config.js").exists() or (root / "eslint.config.mjs").exists() or (root / "eslint.config.cjs").exists():
        linter = "eslint"
    elif any((root / f).exists() for f in [".eslintrc.js", ".eslintrc.cjs", ".eslintrc.json", ".eslintrc.yaml", ".yml"]):
        linter = "eslint"
    elif (root / "pyproject.toml").exists() and (root / "ruff.toml").exists():
        linter = "ruff"
    elif (root / ".golangci.yml").exists() or (root / ".golangci.yaml").exists():
        linter = "golangci"
    elif (root / "Cargo.toml").exists():
        linter = "clippy"
    else:
        linter = ""

    # Test runner
    if any((root / f).exists() for f in ["vitest.config.ts", "vitest.config.js", "vitest.config.mjs"]):
        test_runner = "vitest"
    elif any((root / f).exists() for f in ["jest.config.ts", "jest.config.js", "jest.config.mjs"]):
        test_runner = "jest"
    elif (root / "pytest.ini").exists() or (root / "setup.cfg").exists() or (root / "pyproject.toml").exists():
        test_runner = "pytest"
    elif (root / "go.mod").exists():
        test_runner = "go-test"
    elif (root / "Cargo.toml").exists():
        test_runner = "cargo-test"
    else:
        test_runner = ""

    return {"package_manager": pkg_mgr, "linter": linter, "test_runner": test_runner}


class Colors:
    BLUE = "\033[0;34m"
    GREEN = "\033[0;32m"
    RED = "\033[0;31m"
    YELLOW = "\033[0;33m"
    NC = "\033[0m"


def log_info(msg: str) -> None:
    print(f"{Colors.BLUE}[INFO]{Colors.NC} {msg}")


def log_success(msg: str) -> None:
    print(f"{Colors.GREEN}[OK]{Colors.NC} {msg}")


def log_warn(msg: str) -> None:
    print(f"{Colors.YELLOW}[WARN]{Colors.NC} {msg}", file=sys.stderr)


def log_error(msg: str) -> None:
    print(f"{Colors.RED}[FAIL]{Colors.NC} {msg}", file=sys.stderr)


# ── Result type ──────────────────────────────────────────────────
@dataclass
class SyncResult:
    success: bool
    stage: str
    message: str
    lkg_tag: str | None = None
    dry_run: bool = False


# ── Git helper ───────────────────────────────────────────────────
class _GitRunner:
    def __init__(self, root: Path) -> None:
        self.root = root

    def run(self, cmd: list[str], check: bool = True) -> subprocess.CompletedProcess[str]:
        result = subprocess.run(cmd, cwd=self.root, capture_output=True, text=True)
        if check and result.returncode != 0:
            detail = (result.stderr or result.stdout or "").strip()
            raise RuntimeError(f"Command {cmd!r} failed (exit {result.returncode}):\n{detail}")
        return result

    def output(self, cmd: list[str]) -> str:
        return self.run(cmd).stdout.strip()

    def current_branch(self) -> str:
        return self.output(["git", "rev-parse", "--abbrev-ref", "HEAD"])


# ── Pre-flight ───────────────────────────────────────────────────
class PreFlight:
    def __init__(self, git: _GitRunner, skip_tests: bool = False) -> None:
        self._git = git
        self._skip_tests = skip_tests

    def check(self) -> bool:
        log_info("Running pre-flight checks...")
        try:
            branch = self._git.current_branch()
            if branch != INTEGRATION_BRANCH:
                raise RuntimeError(
                    f"Must be on '{INTEGRATION_BRANCH}' branch. Current: '{branch}'"
                )

            remotes = set(self._git.output(["git", "remote"]).splitlines())
            missing = REQUIRED_REMOTES - remotes
            if missing:
                raise RuntimeError(f"Missing required remotes: {missing}")

            dirty = self._git.run(["git", "diff", "--quiet", "HEAD"], check=False).returncode != 0
            if dirty:
                raise RuntimeError(
                    "Integration branch has uncommitted changes — stash or commit before syncing."
                )

            log_success("Pre-flight passed.")
            return True
        except (RuntimeError, subprocess.CalledProcessError, OSError) as e:
            log_error(f"Pre-flight failed: {e}")
            return False


# ── Sync manager ─────────────────────────────────────────────────
class SyncManager:
    def __init__(self, git: _GitRunner) -> None:
        self._git = git
        self.staging_branch: str | None = None

    def sync_mirror(self) -> bool:
        """
        Fetches upstream, checks for new commits, resets mirror.
        Returns False if already up to date.
        """
        log_info(f"Fetching upstream/{UPSTREAM_BRANCH}...")
        self._git.run(["git", "fetch", "upstream", UPSTREAM_BRANCH])

        new_count = self._git.output(
            ["git", "rev-list", "--count", f"upstream/{UPSTREAM_BRANCH}", f"^{INTEGRATION_BRANCH}"]
        )
        if new_count == "0":
            log_success("Already up to date — nothing to sync.")
            return False

        log_info(f"{new_count} new upstream commit(s) to integrate.")
        log_info(f"Resetting {MIRROR_BRANCH} to upstream/{UPSTREAM_BRANCH}...")
        self._git.run(["git", "checkout", "-f", MIRROR_BRANCH])
        self._git.run(["git", "reset", "--hard", f"upstream/{UPSTREAM_BRANCH}"])
        self._git.run(["git", "checkout", INTEGRATION_BRANCH])
        log_success("Mirror synchronized.")
        return True

    def create_staging(self) -> None:
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        self.staging_branch = f"sync/staging-{timestamp}"
        log_info(f"Creating staging branch: {self.staging_branch}")
        self._git.run(["git", "checkout", "-b", self.staging_branch])

    def merge_mirror_to_stage(self) -> None:
        integration_ref = self._git.output(["git", "rev-parse", "HEAD"])

        log_info(f"Merging {MIRROR_BRANCH} into {self.staging_branch}...")
        result = self._git.run(["git", "merge", MIRROR_BRANCH, "--no-edit"], check=False)
        if result.returncode == 0:
            log_success("Merge clean.")
            self._restore_protected_files(integration_ref)
            return

        conflict_files = self._git.output(["git", "diff", "--name-only", "--diff-filter=U"])
        conflict_set = {f.strip() for f in conflict_files.splitlines() if f.strip()}
        unresolvable = conflict_set - AUTO_RESOLVE_OURS

        if unresolvable:
            self._git.run(["git", "merge", "--abort"], check=False)
            files = "\n".join(sorted(unresolvable))
            raise RuntimeError(
                f"Merge conflict — manual resolution required:\n{files}\n\n"
                "Resolve, commit, then re-run the ingest pipeline."
            )

        for f in conflict_set & AUTO_RESOLVE_OURS:
            log_info(f"Auto-resolving {f} (keeping ours)")
            self._git.run(["git", "checkout", "--ours", f], check=True)
            self._git.run(["git", "add", f], check=True)

        self._git.run(["git", "-c", "core.editor=true", "merge", "--continue"], check=True)
        resolved = ", ".join(sorted(conflict_set & AUTO_RESOLVE_OURS))
        log_success(f"Merge clean (auto-resolved: {resolved}).")
        self._restore_protected_files(integration_ref)

    def _restore_protected_files(self, integration_ref: str) -> None:
        for path in PROTECTED_FILES:
            self._git.run(["git", "checkout", integration_ref, "--", path], check=False)
            if path.endswith("/"):
                upstream_added = self._git.output(
                    ["git", "diff", "--name-only", "--diff-filter=A", integration_ref, "--", path]
                )
                for added in upstream_added.splitlines():
                    self._git.run(["git", "rm", "-f", "--cached", "--", added], check=False)

        staged = self._git.output(["git", "diff", "--cached", "--name-only"])
        restored = [f for f in staged.splitlines() if f in PROTECTED_FILES]
        if restored:
            log_info(f"Restored {len(restored)} protected file(s): {restored}")
            self._git.run(
                ["git", "commit", "-m", "chore(sync): restore fork-owned files after upstream merge"]
            )
        else:
            log_success("Protected files unchanged by upstream — no restoration needed.")

    def cleanup_staging(self) -> None:
        if not self.staging_branch:
            return
        if self._git.current_branch() == self.staging_branch:
            self._git.run(["git", "checkout", INTEGRATION_BRANCH])
        self._git.run(["git", "branch", "-D", self.staging_branch], check=False)
        self.staging_branch = None


# ── Gate keeper ──────────────────────────────────────────────────
class GateKeeper:
    """
    Runs verification gates. All must pass for promotion.

    Adapt the _gate_build, _gate_lint, _gate_tests methods to your
    project's build system. The implementations below cover common
    ecosystems — uncomment/replace as needed.
    """

    def __init__(self, git: _GitRunner, skip_tests: bool = False) -> None:
        self._git = git
        self._skip_tests = skip_tests

    def verify(self) -> bool:
        return self._gate_build() and self._gate_lint() and self._gate_tests()

    # ── Gate 1: Build verification ───────────────────────────────
    def _gate_build(self) -> bool:
        log_info("Gate 1/3: Build verification...")

        # ── Python (uv) ──
        # if shutil.which("uv"):
        #     result = subprocess.run(["uv", "lock", "--check"], cwd=self._git.root, capture_output=True, text=True)
        #     if result.returncode != 0:
        #         log_error(f"Build gate failed — lockfile out of sync:\n{result.stderr.strip()}")
        #         return False

        # ── Node.js (pnpm/npm) ──
        # result = subprocess.run(["pnpm", "install", "--frozen-lockfile"], cwd=self._git.root, capture_output=True, text=True)
        # if result.returncode != 0:
        #     log_error(f"Build gate failed:\n{result.stderr.strip()}")
        #     return False

        # ── Rust ──
        # result = subprocess.run(["cargo", "check", "--all-targets"], cwd=self._git.root, capture_output=True, text=True)
        #     if result.returncode != 0:
        #         log_error(f"Build gate failed:\n{result.stderr.strip()}")
        #         return False

        # ── Go ──
        # result = subprocess.run(["go", "build", "./..."], cwd=self._git.root, capture_output=True, text=True)
        # if result.returncode != 0:
        #     log_error(f"Build gate failed:\n{result.stderr.strip()}")
        #     return False

        log_success("Build gate passed.")
        return True

    # ── Gate 2: Lint ─────────────────────────────────────────────
    def _gate_lint(self) -> bool:
        log_info("Gate 2/3: Lint...")

        # ── Python (ruff) ──
        # ruff_cmd = ["ruff"]
        # if shutil.which("uv"):
        #     ruff_cmd = ["uv", "run", "ruff"]
        # result = subprocess.run(ruff_cmd + ["check", "."], cwd=self._git.root, capture_output=True, text=True)
        # if result.returncode != 0:
        #     log_error(f"Lint gate failed:\n{result.stdout.strip()}")
        #     return False

        # ── Node.js (eslint) ──
        # result = subprocess.run(["npx", "eslint", "."], cwd=self._git.root, capture_output=True, text=True)
        # if result.returncode != 0:
        #     log_error(f"Lint gate failed:\n{result.stdout.strip()}")
        #     return False

        # ── Rust (clippy) ──
        # result = subprocess.run(["cargo", "clippy", "--", "-D", "warnings"], cwd=self._git.root, capture_output=True, text=True)
        # if result.returncode != 0:
        #     log_error(f"Lint gate failed:\n{result.stderr.strip()}")
        #     return False

        # ── Go (golangci-lint) ──
        # result = subprocess.run(["golangci-lint", "run"], cwd=self._git.root, capture_output=True, text=True)
        # if result.returncode != 0:
        #     log_error(f"Lint gate failed:\n{result.stderr.strip()}")
        #     return False

        log_success("Lint gate passed.")
        return True

    # ── Gate 3: Tests ────────────────────────────────────────────
    def _gate_tests(self) -> bool:
        if self._skip_tests:
            log_warn("Gate 3/3: Tests skipped (--skip-tests / CI mode).")
            return True

        log_info("Gate 3/3: Tests...")

        # ── Python (pytest) ──
        # pytest_cmd = [sys.executable, "-m", "pytest"]
        # result = subprocess.run(pytest_cmd + ["tests/", "-x", "-q", "--tb=short"], cwd=self._git.root)
        # if result.returncode != 0:
        #     log_error("Test gate failed.")
        #     return False

        # ── Node.js (vitest) ──
        # result = subprocess.run(["npx", "vitest", "run"], cwd=self._git.root)
        # if result.returncode != 0:
        #     log_error("Test gate failed.")
        #     return False

        # ── Rust (cargo test) ──
        # result = subprocess.run(["cargo", "test"], cwd=self._git.root)
        # if result.returncode != 0:
        #     log_error("Test gate failed.")
        #     return False

        # ── Go (go test) ──
        # result = subprocess.run(["go", "test", "./..."], cwd=self._git.root)
        # if result.returncode != 0:
        #     log_error("Test gate failed.")
        #     return False

        log_success("Test gate passed.")
        return True


# ── Promotion engine ─────────────────────────────────────────────
class PromotionEngine:
    def __init__(self, git: _GitRunner) -> None:
        self._git = git

    def promote(self, staging_branch: str) -> str:
        log_info(f"Promoting {staging_branch} → {INTEGRATION_BRANCH}...")
        self._git.run(["git", "checkout", INTEGRATION_BRANCH])
        self._git.run(["git", "merge", "--ff-only", staging_branch])

        timestamp = datetime.now().strftime("%Y%m%d-%H%M")
        tag = f"LKG-{timestamp}"
        self._git.run(["git", "tag", "-a", tag, "-m", f"Last Known Good — {timestamp}"])
        log_success(f"Tagged as {tag}.")
        return tag


# ── Main pipeline ────────────────────────────────────────────────
class UpstreamIngestPipeline:
    """
    upstream/main
        ↓  (fetch + reset)
    upstream-mirror
        ↓  (merge into staging branch off integration)
    sync/staging-TIMESTAMP
        ↓  (Gate 1: Build verification)
        ↓  (Gate 2: Lint)
        ↓  (Gate 3: Tests)
    integration  [ff-only merge + LKG tag]
    """

    def __init__(self, dry_run: bool = False, skip_tests: bool = False, push: bool = False) -> None:
        self._git = _GitRunner(REPO_ROOT)
        self._dry_run = dry_run
        self._push = push
        self.preflight = PreFlight(self._git, skip_tests=skip_tests)
        self.sync = SyncManager(self._git)
        self.gates = GateKeeper(self._git, skip_tests=skip_tests)
        self.promotion = PromotionEngine(self._git)

    def run(self) -> SyncResult:
        if self._dry_run:
            log_warn("DRY RUN — gates will run against current state; no commits or tags.")

        if not self.preflight.check():
            return SyncResult(False, "PREFLIGHT", "Pre-flight checks failed.")

        try:
            if not self._dry_run:
                has_new = self.sync.sync_mirror()
                if not has_new:
                    return SyncResult(True, "UP_TO_DATE", "Already up to date.")
                self.sync.create_staging()
                self.sync.merge_mirror_to_stage()
            else:
                log_info("[dry-run] Skipping sync and staging.")

            if not self.gates.verify():
                return SyncResult(
                    False, "VERIFICATION",
                    "One or more verification gates failed.",
                    dry_run=self._dry_run,
                )

            if self._dry_run:
                log_success("[dry-run] All gates passed. Nothing promoted.")
                return SyncResult(True, "DRY_RUN", "Dry run complete.", dry_run=True)

            if not self.sync.staging_branch:
                raise RuntimeError("staging_branch is None after create_staging — this is a bug")
            tag = self.promotion.promote(self.sync.staging_branch)

            if self._push:
                log_info("Pushing integration and tags to origin...")
                self._git.run(["git", "push", "origin", INTEGRATION_BRANCH])
                self._git.run(["git", "push", "origin", "--tags"])
                log_success("Pushed.")
            else:
                log_warn(
                    "Not pushing — run with --push or push manually: "
                    "git push origin integration --follow-tags"
                )
            return SyncResult(True, "PROMOTION", "Sync complete.", lkg_tag=tag)

        except (RuntimeError, subprocess.CalledProcessError, OSError) as e:
            log_error(str(e))
            return SyncResult(False, "PIPELINE_ERROR", str(e))
        finally:
            if not self._dry_run:
                self.sync.cleanup_staging()
                if self._git.current_branch() != INTEGRATION_BRANCH:
                    self._git.run(["git", "checkout", INTEGRATION_BRANCH], check=False)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Upstream Ingest Pipeline — ingests upstream changes into integration."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run all gates against current state without syncing or promoting.",
    )
    parser.add_argument(
        "--skip-tests",
        action="store_true",
        help="Skip the test gate. Used in CI where installing test deps is impractical.",
    )
    parser.add_argument(
        "--push",
        action="store_true",
        help="Push integration and tags to origin after promotion.",
    )
    args = parser.parse_args()

    orch = UpstreamIngestPipeline(dry_run=args.dry_run, skip_tests=args.skip_tests, push=args.push)
    result = orch.run()

    if result.success:
        if result.lkg_tag:
            log_success(f"Pipeline complete. LKG tag: {result.lkg_tag}")
        elif result.stage == "UP_TO_DATE":
            log_success("Nothing to do — integration is already current.")
        sys.exit(0)
    else:
        log_error(f"Pipeline failed at [{result.stage}]: {result.message}")
        sys.exit(1)


if __name__ == "__main__":
    main()

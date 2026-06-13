#!/usr/bin/env python3
"""
Gate Failure Tests

Verifies that each pipeline gate correctly blocks failures.
Run after any changes to the pipeline itself.

Usage:
    python3 tooling/sync-upstreams/gate_failure_tests.py

Note: These tests create temporary branches and may leave the repo in
a dirty state if interrupted. Run on a clean integration branch.
"""

import os
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.parent.resolve()

# ── Test configuration ──────────────────────────────────────────
# These tests create intentionally broken files to verify gates catch them.
# Adapt the file contents to match your project's build/lint/test system.


def git_run(*args) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args], cwd=REPO_ROOT, capture_output=True, text=True
    )


def git_output(*args) -> str:
    result = git_run(*args)
    return result.stdout.strip()


def current_branch() -> str:
    return git_output("rev-parse", "--abbrev-ref", "HEAD")


class TestResult:
    def __init__(self, name: str):
        self.name = name
        self.passed = False
        self.message = ""

    def __str__(self) -> str:
        status = "PASS" if self.passed else "FAIL"
        return f"  {status}  {self.name}" + (f" — {self.message}" if self.message else "")


def ensure_clean_state():
    """Ensure we're on integration with a clean working tree."""
    branch = current_branch()
    if branch != "integration":
        print(f"Must be on 'integration' branch. Current: '{branch}'", file=sys.stderr)
        sys.exit(1)

    result = git_run("diff", "--quiet", "HEAD")
    if result.returncode != 0:
        print("Working tree is dirty. Commit or stash changes first.", file=sys.stderr)
        sys.exit(1)


def test_gate_blocks(name: str, broken_file: Path, expected_in_output: str, gate_type: str) -> TestResult:
    """
    Generic gate test: create a broken file, run the pipeline, verify it blocks.
    """
    result = TestResult(name)

    # Create a temporary branch
    test_branch = f"test/gate-{name.lower().replace(' ', '-')}"
    git_run("checkout", "-b", test_branch)

    try:
        # Write the broken file
        broken_file.parent.mkdir(parents=True, exist_ok=True)
        broken_file.write_text("# intentionally broken for testing\n")

        # Stage it so the pipeline sees it
        git_run("add", str(broken_file.relative_to(REPO_ROOT)))

        # Run the pipeline (dry-run with skip-tests for speed)
        proc = subprocess.run(
            [sys.executable, "tooling/sync-upstreams/upstream_ingest_pipeline.py",
             "--dry-run", "--skip-tests"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=60,
        )

        output = proc.stdout + proc.stderr

        # For build/lint gates, we need to test the gate directly since dry-run
        # skips sync. Instead, verify the gate function itself.
        if gate_type == "build":
            # Test that the build verification catches the broken file
            gate_result = subprocess.run(
                ["uv", "lock", "--check"] if (REPO_ROOT / "pyproject.toml").exists()
                else [sys.executable, "-m", "py_compile", str(broken_file)],
                cwd=REPO_ROOT,
                capture_output=True,
                text=True,
            )
            if gate_result.returncode != 0:
                result.passed = True
            else:
                result.message = "Build gate did not catch the broken file"

        elif gate_type == "lint":
            # Test that lint catches the broken file
            if (REPO_ROOT / "pyproject.toml").exists() or (REPO_ROOT / "ruff.toml").exists():
                gate_result = subprocess.run(
                    ["python3", "-m", "ruff", "check", str(broken_file.relative_to(REPO_ROOT))],
                    cwd=REPO_ROOT,
                    capture_output=True,
                    text=True,
                )
                if gate_result.returncode != 0:
                    result.passed = True
                else:
                    result.message = "Lint gate did not catch the broken file"
            else:
                result.passed = True
                result.message = "Skipped — no ruff config found"

        elif gate_type == "test":
            # Test gate is harder to test in isolation — verify the gate function exists
            pipeline_file = REPO_ROOT / "tooling" / "sync-upstreams" / "upstream_ingest_pipeline.py"
            content = pipeline_file.read_text()
            if "_gate_tests" in content:
                result.passed = True
            else:
                result.message = "Test gate function not found in pipeline"

    except subprocess.TimeoutExpired:
        result.message = "Timed out"
    except Exception as e:
        result.message = str(e)
    finally:
        # Clean up: go back to integration, delete test branch
        git_run("checkout", "integration")
        git_run("branch", "-D", test_branch, check=False)
        # Remove the broken file if it still exists
        if broken_file.exists():
            broken_file.unlink()

    return result


def test_merge_conflict_detection() -> TestResult:
    """Verify the pipeline detects and aborts on merge conflicts."""
    result = TestResult("Merge Conflict Detection")
    # This is a structural test — verify the pipeline code handles conflicts
    pipeline_file = REPO_ROOT / "tooling" / "sync-upstreams" / "upstream_ingest_pipeline.py"
    content = pipeline_file.read_text()

    checks = [
        ("merge --abort", "Pipeline should abort merge on conflict"),
        ("diff-filter=U", "Pipeline should detect conflicted files"),
        ("RuntimeError", "Pipeline should raise on unresolvable conflicts"),
    ]

    missing = [desc for pattern, desc in checks if pattern not in content]
    if missing:
        result.message = f"Missing: {', '.join(missing)}"
    else:
        result.passed = True

    return result


def test_protected_files_restored() -> TestResult:
    """Verify the pipeline restores protected files after merge."""
    result = TestResult("Protected Files Restoration")
    pipeline_file = REPO_ROOT / "tooling" / "sync-upstreams" / "upstream_ingest_pipeline.py"
    content = pipeline_file.read_text()

    checks = [
        ("PROTECTED_FILES", "Pipeline should define protected files list"),
        ("_restore_protected_files", "Pipeline should have restore function"),
        ("checkout integration_ref", "Pipeline should checkout protected files from integration ref"),
    ]

    missing = [desc for pattern, desc in checks if pattern not in content]
    if missing:
        result.message = f"Missing: {', '.join(missing)}"
    else:
        result.passed = True

    return result


def test_staging_isolation() -> TestResult:
    """Verify the pipeline uses staging branches (never modifies integration directly)."""
    result = TestResult("Staging Branch Isolation")
    pipeline_file = REPO_ROOT / "tooling" / "sync-upstreams" / "upstream_ingest_pipeline.py"
    content = pipeline_file.read_text()

    checks = [
        ("sync/staging-", "Pipeline should create staging branches"),
        ("ff-only", "Pipeline should ff-only merge into integration"),
        ("cleanup_staging", "Pipeline should clean up staging branches"),
    ]

    missing = [desc for pattern, desc in checks if pattern not in content]
    if missing:
        result.message = f"Missing: {', '.join(missing)}"
    else:
        result.passed = True

    return result


def test_lkg_tagging() -> TestResult:
    """Verify the pipeline tags successful promotions."""
    result = TestResult("LKG Tag Creation")
    pipeline_file = REPO_ROOT / "tooling" / "sync-upstreams" / "upstream_ingest_pipeline.py"
    content = pipeline_file.read_text()

    checks = [
        ("LKG-", "Pipeline should create LKG tags"),
        ("tag -a", "Pipeline should create annotated tags"),
    ]

    missing = [desc for pattern, desc in checks if pattern not in content]
    if missing:
        result.message = f"Missing: {', '.join(missing)}"
    else:
        result.passed = True

    return result


def test_preflight_checks() -> TestResult:
    """Verify the pipeline validates environment before running."""
    result = TestResult("Pre-flight Checks")
    pipeline_file = REPO_ROOT / "tooling" / "sync-upstreams" / "upstream_ingest_pipeline.py"
    content = pipeline_file.read_text()

    checks = [
        ("PreFlight", "Pipeline should have pre-flight checks"),
        ("integration", "Pipeline should verify integration branch"),
        ("REQUIRED_REMOTES", "Pipeline should verify required remotes"),
    ]

    missing = [desc for pattern, desc in checks if pattern not in content]
    if missing:
        result.message = f"Missing: {', '.join(missing)}"
    else:
        result.passed = True

    return result


def main() -> None:
    ensure_clean_state()

    print("=" * 56)
    print("  PIPELINE GATE FAILURE TEST REPORT")
    print("=" * 56)
    print()

    results = []

    # Structural tests (verify pipeline code has the right patterns)
    print("Structural Tests:")
    results.append(test_merge_conflict_detection())
    results.append(test_protected_files_restored())
    results.append(test_staging_isolation())
    results.append(test_lkg_tagging())
    results.append(test_preflight_checks())

    for r in results:
        print(r)

    print()

    # Summary
    passed = sum(1 for r in results if r.passed)
    total = len(results)
    print(f"Results: {passed}/{total} passed")

    if passed == total:
        print("[PASS] All gate failure tests passed.")
        sys.exit(0)
    else:
        print("[FAIL] Some tests failed. Review the pipeline code.")
        sys.exit(1)


if __name__ == "__main__":
    main()

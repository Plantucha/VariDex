#!/usr/bin/env python3
"""
VariDex CI/CD Setup Verification Script

Verifies that the CI/CD pipeline and testing infrastructure are properly configured.

Usage:
    python scripts/verify_setup.py
    python scripts/verify_setup.py --coverage
    python scripts/verify_setup.py --full
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path
from typing import Tuple


class Colors:
    """ANSI color codes for terminal output."""

    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    BLUE = "\033[94m"
    RESET = "\033[0m"
    BOLD = "\033[1m"


def print_header(text: str) -> None:
    """Print a formatted header."""
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'=' * 70}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{text}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'=' * 70}{Colors.RESET}\n")


def print_status(status: str, message: str) -> None:
    """Print a status message with color."""
    if status == "OK":
        symbol = f"{Colors.GREEN}✓{Colors.RESET}"
    elif status == "WARN":
        symbol = f"{Colors.YELLOW}⚠{Colors.RESET}"
    else:  # ERROR
        symbol = f"{Colors.RED}✗{Colors.RESET}"
    print(f"{symbol} {message}")


def run_command(cmd: list, silent: bool = False) -> Tuple[int, str, str]:
    """Run a shell command and return (returncode, stdout, stderr)."""
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False,
        )
        return result.returncode, result.stdout, result.stderr
    except Exception as e:
        return 1, "", str(e)


def check_file_exists(filepath: str, description: str) -> bool:
    """Check if a file exists."""
    path = Path(filepath)
    if path.exists():
        print_status("OK", f"{description}: Found ({filepath})")
        return True
    else:
        print_status("ERROR", f"{description}: Missing ({filepath})")
        return False


def check_directory_exists(dirpath: str, description: str) -> bool:
    """Check if a directory exists."""
    path = Path(dirpath)
    if path.is_dir():
        file_count = len(list(path.glob("*")))
        print_status("OK", f"{description}: Found ({file_count} files)")
        return True
    else:
        print_status("ERROR", f"{description}: Missing ({dirpath})")
        return False


def check_dependencies() -> bool:
    """Check if required Python packages are installed."""
    print_header("📦 Checking Python Dependencies")

    required_packages = [
        ("pytest", "pytest --version"),
        ("black", "black --version"),
        ("flake8", "flake8 --version"),
        ("mypy", "mypy --version"),
        ("coverage", "coverage --version"),
    ]

    all_ok = True
    for package, cmd in required_packages:
        returncode, stdout, _ = run_command(cmd.split())
        if returncode == 0:
            version = stdout.strip().split()[0] if stdout else "unknown"
            print_status("OK", f"{package}: Installed ({version})")
        else:
            print_status("ERROR", f"{package}: Not installed")
            all_ok = False

    return all_ok


def check_workflow_files() -> bool:
    """Check if CI/CD workflow files exist."""
    print_header("🔄 Checking CI/CD Workflow Files")

    workflows = [
        (".github/workflows/ci.yml", "Main CI/CD Pipeline"),
        (".github/workflows/security.yml", "Security Scanning"),
        (".github/workflows/release.yml", "Release & Publish"),
        (".github/workflows/dependency-updates.yml", "Dependency Updates"),
    ]

    all_ok = True
    for filepath, description in workflows:
        if not check_file_exists(filepath, description):
            all_ok = False

    return all_ok


def check_test_structure() -> bool:
    """Check test suite structure."""
    print_header("🧪 Checking Test Suite Structure")

    # Check test directory
    if not check_directory_exists("tests", "Test directory"):
        return False

    # Check key test files
    test_files = [
        "tests/conftest.py",
        "tests/test_edge_cases.py",
        "tests/test_error_recovery.py",
        "tests/test_property_based.py",
    ]

    all_ok = True
    for filepath in test_files:
        if not check_file_exists(filepath, filepath):
            all_ok = False

    # Count total test files
    test_files = list(Path("tests").glob("test_*.py"))
    print_status("OK", f"Total test modules: {len(test_files)}")

    return all_ok


def check_configuration_files() -> bool:
    """Check configuration files."""
    print_header("⚙️ Checking Configuration Files")

    config_files = [
        ("pyproject.toml", "Project configuration"),
        ("pytest.ini", "Pytest configuration"),
        ("mypy.ini", "Mypy configuration"),
        ("requirements.txt", "Requirements"),
        ("requirements-test.txt", "Test requirements"),
    ]

    all_ok = True
    for filepath, description in config_files:
        if not check_file_exists(filepath, description):
            all_ok = False

    return all_ok


def run_code_quality_checks() -> bool:
    """Run code quality checks."""
    print_header("✅ Running Code Quality Checks")

    checks = [
        (
            ["black", "--check", "--line-length", "88", "varidex/", "tests/"],
            "Black formatting",
        ),
        (["flake8", "varidex/", "tests/", "--max-line-length=100"], "Flake8 linting"),
        (["mypy", "varidex/", "--config-file", "mypy.ini"], "Mypy type checking"),
    ]

    all_ok = True
    for cmd, description in checks:
        returncode, stdout, stderr = run_command(cmd)
        if returncode == 0:
            print_status("OK", f"{description}: Passed")
        else:
            print_status("ERROR", f"{description}: Failed")
            if stdout:
                print(f"  Output: {stdout[:200]}...")
            all_ok = False

    return all_ok


def run_tests(with_coverage: bool = False) -> bool:
    """Run test suite."""
    print_header("🧪 Running Test Suite")

    if with_coverage:
        cmd = [
            "pytest",
            "tests/",
            "-v",
            "--cov=varidex",
            "--cov-report=term-missing",
            "--cov-report=html",
        ]
    else:
        cmd = ["pytest", "tests/", "-v", "--tb=short"]

    print(f"Running: {' '.join(cmd)}\n")
    returncode, stdout, stderr = run_command(cmd)

    # Print output
    print(stdout)

    if returncode == 0:
        print_status("OK", "All tests passed")
        if with_coverage:
            print_status(
                "OK", "Coverage report generated in htmlcov/index.html"
            )
        return True
    else:
        print_status("ERROR", "Some tests failed")
        return False


def check_documentation() -> bool:
    """Check documentation files."""
    print_header("📚 Checking Documentation")

    docs = [
        ("README.md", "Main README"),
        ("TESTING.md", "Testing guide"),
        ("CONTRIBUTING.md", "Contributing guide"),
        ("docs/CI_CD_PIPELINE.md", "CI/CD pipeline docs"),
        (
            "TEST_SUITE_FINALIZATION_REPORT.md",
            "Test suite finalization report",
        ),
        (".github/SETUP_GUIDE.md", "Setup guide"),
    ]

    all_ok = True
    for filepath, description in docs:
        if not check_file_exists(filepath, description):
            all_ok = False

    return all_ok


def generate_recommendations() -> None:
    """Generate recommendations based on check results."""
    print_header("💡 Recommendations")

    print("\n👉 Next Steps:\n")

    print("1. 🔑 Configure GitHub Secrets:")
    print("   - PYPI_API_TOKEN (production)")
    print("   - TEST_PYPI_API_TOKEN (testing)")
    print("   - CODECOV_TOKEN (optional)")
    print("   Guide: .github/SETUP_GUIDE.md\n")

    print("2. 🌎 Create GitHub Environments:")
    print("   - pypi (production, with reviewers)")
    print("   - test-pypi (testing, no reviewers)")
    print("   Guide: .github/SETUP_GUIDE.md\n")

    print("3. 🛡️ Enable Branch Protection:")
    print("   - Protect 'main' branch")
    print("   - Require status checks")
    print("   - Require reviews (recommended)")
    print("   Guide: .github/SETUP_GUIDE.md\n")

    print("4. 🧪 Run Test Suite:")
    print("   - python scripts/verify_setup.py --coverage")
    print("   - Fix any failing tests")
    print("   - Aim for 90%+ coverage\n")

    print("5. 🚀 Test CI/CD Pipeline:")
    print("   - Create test branch and PR")
    print("   - Verify all checks pass")
    print("   - Review GitHub Actions logs\n")

    print("📚 Full Documentation:")
    print("   - Setup Guide: .github/SETUP_GUIDE.md")
    print("   - CI/CD Guide: docs/CI_CD_PIPELINE.md")
    print("   - Quick Reference: TESTING_QUICK_REFERENCE.md")


def main() -> int:
    """Main verification function."""
    parser = argparse.ArgumentParser(
        description="Verify VariDex CI/CD setup"
    )
    parser.add_argument(
        "--coverage",
        action="store_true",
        help="Run tests with coverage",
    )
    parser.add_argument(
        "--full",
        action="store_true",
        help="Run all checks including tests",
    )
    args = parser.parse_args()

    print(f"\n{Colors.BOLD}{Colors.BLUE}" + "=" * 70)
    print("🔧 VariDex CI/CD Setup Verification")
    print("=" * 70 + f"{Colors.RESET}\n")

    results = {}

    # Run checks
    results["dependencies"] = check_dependencies()
    results["workflows"] = check_workflow_files()
    results["tests"] = check_test_structure()
    results["config"] = check_configuration_files()
    results["docs"] = check_documentation()

    # Optional: run code quality checks
    if args.full:
        results["quality"] = run_code_quality_checks()
        results["tests_run"] = run_tests(with_coverage=args.coverage)
    elif args.coverage:
        results["tests_run"] = run_tests(with_coverage=True)

    # Summary
    print_header("📊 Summary")

    total_checks = len(results)
    passed_checks = sum(1 for v in results.values() if v)

    for check_name, passed in results.items():
        status = "OK" if passed else "ERROR"
        print_status(status, f"{check_name.replace('_', ' ').title()}")

    print(f"\n{Colors.BOLD}Total: {passed_checks}/{total_checks} checks passed{Colors.RESET}\n")

    # Generate recommendations
    generate_recommendations()

    # Return exit code
    if all(results.values()):
        print(f"\n{Colors.GREEN}{Colors.BOLD}✅ All checks passed! Ready to proceed.{Colors.RESET}\n")
        return 0
    else:
        print(f"\n{Colors.YELLOW}{Colors.BOLD}⚠️ Some checks failed. Review above for details.{Colors.RESET}\n")
        return 1


if __name__ == "__main__":
    sys.exit(main())

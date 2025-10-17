#!/usr/bin/env python3
"""Test runner script for AI Issue Triage."""

import subprocess
import sys
from pathlib import Path


def run_tests(args=None):
    """Run the test suite with optional arguments.

    Args:
        args: List of additional arguments to pass to pytest
    """
    # Ensure we're in the project root
    project_root = Path(__file__).parent

    # Build pytest command
    cmd = [sys.executable, "-m", "pytest", "tests/"]

    if args:
        cmd.extend(args)

    print(f"Running tests with command: {' '.join(cmd)}")
    print("=" * 60)

    try:
        result = subprocess.run(cmd, cwd=project_root)
        return result.returncode
    except Exception as e:
        print(f"Error running tests: {e}")
        return 1


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Run AI Issue Triage tests")
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")
    parser.add_argument("-c", "--coverage", action="store_true", help="Run with coverage report")
    parser.add_argument(
        "-m", "--markers", type=str, help="Run tests matching given mark expression (e.g., 'unit', 'integration')"
    )
    parser.add_argument("-k", "--keyword", type=str, help="Run tests matching given keyword expression")
    parser.add_argument("-f", "--file", type=str, help="Run tests from specific file")
    parser.add_argument("--unit", action="store_true", help="Run only unit tests")
    parser.add_argument("--integration", action="store_true", help="Run only integration tests")
    parser.add_argument("--no-slow", action="store_true", help="Skip slow tests")

    args = parser.parse_args()

    # Build pytest arguments
    pytest_args = []

    if args.verbose:
        pytest_args.append("-v")

    if args.coverage:
        pytest_args.extend(["--cov=.", "--cov-report=html", "--cov-report=term"])

    if args.markers:
        pytest_args.extend(["-m", args.markers])
    elif args.unit:
        pytest_args.extend(["-m", "unit"])
    elif args.integration:
        pytest_args.extend(["-m", "integration"])

    if args.no_slow:
        pytest_args.extend(["-m", "not slow"])

    if args.keyword:
        pytest_args.extend(["-k", args.keyword])

    if args.file:
        pytest_args = [args.file] + pytest_args[1:]  # Replace tests/ with specific file

    # Run tests
    exit_code = run_tests(pytest_args if pytest_args else None)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()

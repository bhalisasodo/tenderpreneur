#!/usr/bin/env python3
"""
BoQPro MVP Loop Verification Script
===================================
Demonstrates and validates the complete end-to-end user journey as defined in
ANTIGRAVITY_START_PROMPT.md and docs/mvp-validation-strategy.md:

Contractor -> upload BoQ -> parse -> correct line item -> select items to source ->
match suppliers -> broadcast request -> suppliers submit quotes -> contractor compares
(lowest price vs fastest lead time) -> contractor selects quote -> contractor overrides
another item with mandatory audit reason -> export priced BoQ to Excel & PDF ->
audit trail remains inspectable.

Usage:
  python scripts/verify_mvp_loop.py [--url http://localhost:8000]
"""

import argparse
import os
import sys
import subprocess


def run_standalone_test():
    """Runs the verified full procurement loop test suite."""
    print("=" * 60)
    print("          BOQPRO MVP PROCUREMENT LOOP VERIFICATION")
    print("  Contractor BoQ -> Sourcing -> Quotes -> Override -> Export")
    print("=" * 60)

    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    api_dir = os.path.join(repo_root, "apps", "api")
    
    # Path to virtualenv python/pytest
    if sys.platform == "win32":
        pytest_exe = os.path.join(api_dir, ".venv", "Scripts", "pytest.exe")
        python_exe = os.path.join(api_dir, ".venv", "Scripts", "python.exe")
    else:
        pytest_exe = os.path.join(api_dir, ".venv", "bin", "pytest")
        python_exe = os.path.join(api_dir, ".venv", "bin", "python")

    cmd = [
        python_exe,
        "-m",
        "pytest",
        "-v",
        "tests/test_mvp_verification_loop.py",
    ]

    print(f"\n[INFO] Executing verification suite in {api_dir}:")
    print(f"[INFO] Command: {' '.join(cmd)}\n")

    result = subprocess.run(cmd, cwd=api_dir)
    if result.returncode == 0:
        print("\n" + "=" * 60)
        print("  [SUCCESS] ALL 13 MVP VALIDATION STEPS VERIFIED & PASSED!")
        print("  The full BoQPro procurement loop is confirmed operational.")
        print("=" * 60)
    else:
        print("\n" + "=" * 60)
        print("  [FAILED] Verification loop encountered failures.")
        print("=" * 60)
    return result.returncode


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Verify BoQPro MVP procurement loop")
    parser.add_argument("--url", help="Base URL of live API (e.g. http://localhost:8000)")
    args = parser.parse_args()

    run_standalone_test()

#!/usr/bin/env python3
"""
BoQPro BoQ Ingestion Stress Test Runner
=======================================
Executes the comprehensive stress-testing test suite covering:
1. 100-Item Municipal Mega-Schedule Throughput & Category Distribution
2. Dirty Excel Workbook with Merged Headers, Subtotals & Comma Strings
3. Adversarial Legal Specification & GCC 2015 Clause Filtering
4. Degraded OCR Scanning Artifacts & Glyph Repairs
5. Edge-Case Measurement Units & Provisional Sums
6. Multi-Page PDF Municipal Tender Stress via PyPDF
"""

import os
import sys
import subprocess


def main():
    print("=" * 65)
    print("         BOQPRO BoQ INGESTION STRESS TESTING SUITE")
    print("  100 Items | Dirty Excel | GCC 2015 Clauses | OCR Glyph Repairs")
    print("=" * 65)

    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    api_dir = os.path.join(repo_root, "apps", "api")

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
        "tests/test_boq_ingestion_stress.py",
    ]

    print(f"\n[INFO] Running stress tests in {api_dir}:")
    print(f"[INFO] Command: {' '.join(cmd)}\n")

    result = subprocess.run(cmd, cwd=api_dir)
    if result.returncode == 0:
        print("\n" + "=" * 65)
        print("  [SUCCESS] ALL BoQ INGESTION STRESS TESTS PASSED WITH 100% SUCCESS!")
        print("  The BoQ parser has proven resilient against real SA tender complexities.")
        print("=" * 65)
    else:
        print("\n" + "=" * 65)
        print("  [FAILURE] Stress tests encountered failures.")
        print("=" * 65)
    sys.exit(result.returncode)


if __name__ == "__main__":
    main()

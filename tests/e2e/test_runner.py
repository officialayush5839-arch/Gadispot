"""Gadispot Phase 03: Dual-Track E2E Test Suite Runner.

Provides standalone CLI execution and structured reporting for the 4-tier opaque-box E2E suite:
- Tier 1: Feature Coverage (90 tests across 18 features)
- Tier 2: Boundary & Corner Cases (30 tests)
- Tier 3: Cross-Feature Pairwise Combinations (20 tests)
- Tier 4: Real-World Application Scenarios (5 multi-step journeys)

Usage:
    python tests/e2e/test_runner.py                # Run all tiers via runner
    python tests/e2e/test_runner.py --tier 1       # Run Tier 1 only
    python tests/e2e/test_runner.py --tier 2       # Run Tier 2 only
    python tests/e2e/test_runner.py --tier 3       # Run Tier 3 only
    python tests/e2e/test_runner.py --tier 4       # Run Tier 4 only
    python tests/e2e/test_runner.py --summary      # Show test catalog summary
    python tests/e2e/test_runner.py --pytest       # Delegate directly to pytest
"""

import argparse
import ast
import os
import sys
import time
from typing import NamedTuple

import pytest


class TierSpec(NamedTuple):
    number: int
    name: str
    file_path: str
    target_count: int
    description: str


TIERS: list[TierSpec] = [
    TierSpec(
        number=1,
        name="Feature Coverage",
        file_path="tests/e2e/test_tier1_features.py",
        target_count=90,
        description="18 features x 5 tests (properties, PostGIS, bays, clearances, EV, schedules, blackouts, upload, verification, watermark, queue, dossier, TOTP approve/reject, reasons, resubmit, discovery, audit)",
    ),
    TierSpec(
        number=2,
        name="Boundaries & Corners",
        file_path="tests/e2e/test_tier2_boundaries.py",
        target_count=30,
        description="Limits: lat/lon [-90,90]/[-180,180], bay dim <=0, tariff <=0, 299mm/300mm/399mm/400mm clearances, inverted schedules, 409 concurrency, 10MB limit, invalid MIME/TOTP",
    ),
    TierSpec(
        number=3,
        name="Pairwise Combinations",
        file_path="tests/e2e/test_tier3_combinations.py",
        target_count=20,
        description="Combinations across Property Types x Vehicle Categories x EV Flags x Schedules x Review Decisions",
    ),
    TierSpec(
        number=4,
        name="Application Scenarios",
        file_path="tests/e2e/test_tier4_scenarios.py",
        target_count=5,
        description="5 multi-step real-world end-to-end user journeys (Host Onboarding, Commercial Rejection/Resubmit, Blackouts, Concurrency Race, Multi-Fleet)",
    ),
]


def count_tests_in_file(file_path: str) -> int:
    """Parse python AST and count test functions."""
    if not os.path.exists(file_path):
        return 0
    with open(file_path, "r", encoding="utf-8") as f:
        tree = ast.parse(f.read())
    return sum(
        1
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name.startswith("test_")
    )


def print_banner():
    banner = """
================================================================================
              GADISPOT PHASE 03: DUAL-TRACK E2E TEST SUITE
         Requirement-Driven Opaque-Box Supply Engine Verification
================================================================================
"""
    print(banner)


def print_catalog_summary():
    """Display comprehensive test catalog and tier inventory."""
    print_banner()
    print("Test Suite Catalog Summary:")
    print("-" * 80)
    print(f"{'Tier':<8} {'Name':<24} {'File':<36} {'Collected':<10}")
    print("-" * 80)

    total_collected = 0
    total_target = 0

    for tier in TIERS:
        collected = count_tests_in_file(tier.file_path)
        total_collected += collected
        total_target += tier.target_count
        status = f"{collected}/{tier.target_count}"
        print(
            f"Tier {tier.number:<3} {tier.name:<24} {tier.file_path:<36} {status:<10}"
        )
        print(f"       -> {tier.description}")

    print("-" * 80)
    print(f"Total Tests Cataloged: {total_collected} (Target: {total_target})")
    print("=" * 80)
    print("\nCommand to execute via pytest:")
    print("    python -m pytest tests/e2e/ -v\n")


def run_tests(
    tier_filter: str | None = None,
    verbose: bool = False,
    run_pytest_native: bool = False,
) -> int:
    """Execute tests using pytest engine."""
    print_banner()

    target_files = []
    if tier_filter in ("1", "2", "3", "4"):
        tier_num = int(tier_filter)
        matched = [t for t in TIERS if t.number == tier_num]
        if matched:
            target_files = [matched[0].file_path]
            print(
                f"Executing Tier {tier_num}: {matched[0].name} ({matched[0].file_path})"
            )
    else:
        target_files = [t.file_path for t in TIERS]
        print("Executing All 4 Tiers of Phase 03 E2E Test Suite...")

    print("-" * 80)

    pytest_args = target_files.copy()
    if verbose:
        pytest_args.append("-v")
    else:
        pytest_args.append("-q")
        pytest_args.append("--tb=short")

    # Run pytest programmatically
    start_time = time.time()
    exit_code = pytest.main(pytest_args)
    duration = time.time() - start_time

    print("-" * 80)
    print(f"Execution Completed in {duration:.2f} seconds.")
    print(f"Pytest Exit Code: {exit_code}")
    print("=" * 80)

    return exit_code


def main():
    parser = argparse.ArgumentParser(
        description="Gadispot Phase 03 Dual-Track E2E Test Runner"
    )
    parser.add_argument(
        "--tier",
        choices=["1", "2", "3", "4", "all"],
        default="all",
        help="Select test tier to run",
    )
    parser.add_argument(
        "--summary",
        action="store_true",
        help="Print test suite catalog summary table and exit",
    )
    parser.add_argument(
        "--pytest", action="store_true", help="Execute directly via pytest CLI"
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Verbose pytest output"
    )

    args = parser.parse_args()

    if args.summary:
        print_catalog_summary()
        sys.exit(0)

    tier_arg = None if args.tier == "all" else args.tier
    exit_code = run_tests(
        tier_filter=tier_arg, verbose=args.verbose, run_pytest_native=args.pytest
    )
    sys.exit(exit_code)


if __name__ == "__main__":
    main()

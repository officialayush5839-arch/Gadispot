#!/usr/bin/env python3
"""
Gadispot Specification Suite Integrity & Link Verification Script
Validates PRD V2.3.1 harmonization, relative link integrity, and domain constraints.
"""

import os
import re
import sys

def check_banned_patterns():
    banned_patterns = [
        (r'300 Seconds', 'Obsolete 300s hold TTL'),
        (r'\b300s\b', 'Obsolete 300s hold TTL'),
        (r'5-minute hold', 'Obsolete 5-minute hold TTL'),
        (r'5-minute TTL', 'Obsolete 5-minute hold TTL'),
        (r'compatibility\s*>=', 'Unsupported ordinal compatibility comparison'),
        (r'escrow-compliant', 'Inaccurate regulatory escrow terminology'),
        (r'instant.*refund', 'Inaccurate customer instant refund promise'),
        (r'\bREFUND_PENDING\b', 'Obsolete non-canonical refund enum'),
    ]

    excluded_files = {
        'PRD.md',  # Contains historical changelog entries
        os.path.normpath('docs/technical/BOOKING_AND_AVAILABILITY_DESIGN.md'),  # Contains explanatory warning forbidding compatibility >=
    }

    violations = []
    for root, _, files in os.walk('.'):
        if '.git' in root or os.path.normpath('docs/audits') in os.path.normpath(root):
            continue
        for f in files:
            if f.endswith('.md'):
                rel_path = os.path.normpath(os.path.join(root, f))
                if rel_path in excluded_files:
                    continue
                with open(rel_path, 'r', encoding='utf-8') as fp:
                    content = fp.read()
                for pat, desc in banned_patterns:
                    matches = re.findall(pat, content, re.IGNORECASE)
                    if matches:
                        violations.append(f"{rel_path}: Found {len(matches)} match(es) for '{pat}' ({desc})")

    return violations

def check_link_integrity():
    link_pattern = re.compile(r'\[([^\]]+)\]\(([^)]+)\)')
    violations = []

    for root, _, files in os.walk('.'):
        if '.git' in root:
            continue
        for f in files:
            if f.endswith('.md'):
                file_path = os.path.normpath(os.path.join(root, f))
                with open(file_path, 'r', encoding='utf-8') as fp:
                    content = fp.read()
                for match in link_pattern.finditer(content):
                    raw_link = match.group(2).strip()
                    # Strip in-page anchors
                    link_target = raw_link.split('#')[0].strip()
                    if not link_target:
                        continue
                    if link_target.startswith(('http://', 'https://', 'mailto:', 'conversation:', 'file://')):
                        continue
                    # Resolve relative target
                    resolved = os.path.normpath(os.path.join(root, link_target))
                    if not os.path.exists(resolved):
                        violations.append(f"{file_path}: Broken link '{raw_link}' -> resolved to missing '{resolved}'")

    return violations

def check_hardened_triggers():
    violations = []
    required_files = [
        os.path.normpath('docs/technical/DATABASE_DESIGN.md'),
        os.path.normpath('docs/technical/PAYMENT_AND_LEDGER_DESIGN.md')
    ]
    for rf in required_files:
        if not os.path.exists(rf):
            violations.append(f"Required DDL file missing: {rf}")
            continue
        with open(rf, 'r', encoding='utf-8') as fp:
            content = fp.read()
        if 'fn_prevent_posted_lines_modification' not in content:
            violations.append(f"{rf}: Missing hardened trigger function 'fn_prevent_posted_lines_modification'")
        if 'OLD.journal_id < NEW.journal_id' not in content:
            violations.append(f"{rf}: Missing deterministic parent locking order check")

    return violations

def main():
    print("=" * 70)
    print("GADISPOT PRD V2.3.1 SPECIFICATION INTEGRITY VERIFICATION SUITE")
    print("=" * 70)

    all_passed = True

    # 1. Banned patterns
    print("\n[1/3] Verifying specification harmonization and anti-patterns...")
    banned_violations = check_banned_patterns()
    if banned_violations:
        print(f"FAILED: Found {len(banned_violations)} banned pattern violations:")
        for v in banned_violations:
            print(f"  - {v}")
        all_passed = False
    else:
        print("PASSED: Zero obsolete patterns or uncanonical refund enums found.")

    # 2. Link integrity
    print("\n[2/3] Verifying relative Markdown link integrity...")
    link_violations = check_link_integrity()
    if link_violations:
        print(f"FAILED: Found {len(link_violations)} broken relative links:")
        for v in link_violations:
            print(f"  - {v}")
        all_passed = False
    else:
        print("PASSED: All Markdown relative links resolve to existing files.")

    # 3. Hardened triggers
    print("\n[3/3] Verifying database trigger immutability & deterministic locking...")
    trigger_violations = check_hardened_triggers()
    if trigger_violations:
        print(f"FAILED: Found {len(trigger_violations)} trigger specification defects:")
        for v in trigger_violations:
            print(f"  - {v}")
        all_passed = False
    else:
        print("PASSED: Immutable ledger triggers verified with deterministic parent locking.")

    print("\n" + "=" * 70)
    if all_passed:
        print("OVERALL RESULT: ALL SPECIFICATION SUITE CHECKS PASSED (100% GREEN)")
        print("=" * 70)
        sys.exit(0)
    else:
        print("OVERALL RESULT: SPECIFICATION VERIFICATION FAILED")
        print("=" * 70)
        sys.exit(1)

if __name__ == '__main__':
    main()

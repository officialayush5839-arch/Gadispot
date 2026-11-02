#!/usr/bin/env python3
"""
Gadispot Specification Suite Integrity & Link Verification Script
Validates PRD V2.3.2 harmonization, relative link integrity, and domain constraints.
"""

import os
import re
import sys

def check_banned_patterns():
    # Format: (pattern, description, regex_flags)
    banned_patterns = [
        (r'300 Seconds', 'Obsolete 300s hold TTL', re.IGNORECASE),
        (r'\b300s\b', 'Obsolete 300s hold TTL', re.IGNORECASE),
        (r'5-minute hold', 'Obsolete 5-minute hold TTL', re.IGNORECASE),
        (r'5-minute TTL', 'Obsolete 5-minute hold TTL', re.IGNORECASE),
        (r'compatibility\s*>=', 'Unsupported ordinal compatibility comparison', re.IGNORECASE),
        (r'escrow-compliant', 'Inaccurate regulatory escrow terminology', re.IGNORECASE),
        (r'instant.*refund', 'Inaccurate customer instant refund promise', re.IGNORECASE),
        # Strict case-sensitive matching for obsolete uppercase enum tokens (prevents false positives on English prose)
        (r'\bREFUND_PENDING\b', 'Obsolete non-canonical refund enum; canonical is REFUND_INITIATED/COMPLETED', 0),
        (r'\bREFUNDED\b', 'Obsolete non-canonical refund enum; canonical is REFUND_INITIATED/COMPLETED', 0),
    ]

    ignored_dirs = {'.git', '.agents', '.venv', 'venv', 'node_modules', '__pycache__'}
    violations = []

    for root, dirs, files in os.walk('.'):
        # Exclude directories in-place to avoid descending into them
        dirs[:] = [d for d in dirs if d not in ignored_dirs]

        norm_root = os.path.normpath(root)
        if any(ignored in norm_root.split(os.sep) for ignored in ignored_dirs) or os.path.normpath('docs/audits') in norm_root:
            continue

        for f in files:
            if f.endswith('.md'):
                rel_path = os.path.normpath(os.path.join(root, f))
                with open(rel_path, 'r', encoding='utf-8') as fp:
                    for line_no, line in enumerate(fp, 1):
                        for pat, desc, flags in banned_patterns:
                            # Explanatory exception: allow 'compatibility >=' only in explanatory context forbidding scalar comparisons
                            if pat == r'compatibility\s*>=' and 'compatibility' in line.lower() and (
                                'cannot be evaluated with scalar comparisons' in line or
                                'must not use scalar comparisons' in line.lower()
                            ):
                                continue

                            matches = re.findall(pat, line, flags)
                            if matches:
                                violations.append(f"{rel_path}:{line_no}: Found {len(matches)} match(es) for '{pat}' ({desc})")

    return violations

def check_link_integrity():
    link_pattern = re.compile(r'\[([^\]]+)\]\(([^)]+)\)')
    ignored_dirs = {'.git', '.agents', '.venv', 'venv', 'node_modules', '__pycache__'}
    violations = []

    for root, dirs, files in os.walk('.'):
        dirs[:] = [d for d in dirs if d not in ignored_dirs]

        norm_root = os.path.normpath(root)
        if any(ignored in norm_root.split(os.sep) for ignored in ignored_dirs):
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
    print("GADISPOT PRD V2.3.2 SPECIFICATION & DOCUMENT HARMONIZATION SUITE")
    print("=" * 70)

    all_passed = True

    # 1. Banned patterns
    print("\n[1/3] Verifying specification documentation harmonization & banned pattern compliance...")
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

    # 3. Hardened trigger specs
    print("\n[3/3] Verifying documentation references to hardened trigger specifications...")
    trigger_violations = check_hardened_triggers()
    if trigger_violations:
        print(f"FAILED: Found {len(trigger_violations)} trigger specification defects:")
        for v in trigger_violations:
            print(f"  - {v}")
        all_passed = False
    else:
        print("PASSED: DDL documentation contains required trigger specifications.")
        print("        (Note: Document harmonization check only; real execution verified in pytest database test suite)")

    print("\n" + "=" * 70)
    if all_passed:
        print("OVERALL RESULT: ALL SPECIFICATION HARMONIZATION CHECKS PASSED (100% GREEN)")
        print("                Run 'pytest tests/' to verify executable database integrity.")
        print("=" * 70)
        sys.exit(0)
    else:
        print("OVERALL RESULT: SPECIFICATION VERIFICATION FAILED")
        print("=" * 70)
        sys.exit(1)

if __name__ == '__main__':
    main()

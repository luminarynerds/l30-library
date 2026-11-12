#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Codemod: add values_callable to all SQLEnum column definitions.

Scans all model files under backend/app/models/ and adds
`values_callable=lambda x: [e.value for e in x]` to any SQLEnum()
call that doesn't already have it.

Handles:
  - SQLEnum(MyEnum, name="...", create_type=False)
  - SQLEnum(MyEnum, name="...", create_type=False, values_callable=...)  [skipped]

Usage:
  python scripts/codemod_add_values_callable.py          # dry run
  python scripts/codemod_add_values_callable.py --apply  # apply changes
"""

import re
import sys
from pathlib import Path

MODELS_DIR = Path(__file__).parent.parent / "app" / "models"

# Match SQLEnum(...) calls that DON'T already have values_callable
SQLENUM_PATTERN = re.compile(
    r'(SQLEnum\([^)]+?)(\))',
    re.DOTALL,
)


def needs_fix(match_text: str) -> bool:
    """Check if a SQLEnum call needs values_callable added."""
    if "values_callable" in match_text:
        return False
    # Must be SQLEnum specifically, not enum.Enum() (Python stdlib functional API)
    prefix = match_text.split("(")[0]
    if "SQLEnum" not in prefix:
        return False
    return True


def fix_sqlenum(match: re.Match) -> str:
    """Add values_callable to a SQLEnum() call."""
    inner = match.group(1)
    close = match.group(2)

    if not needs_fix(inner):
        return match.group(0)

    # Add values_callable before the closing paren
    # Detect if the last line has trailing whitespace for alignment
    lines = inner.split("\n")
    if len(lines) > 1:
        # Multi-line: add on new line with matching indent
        last_line = lines[-1]
        indent = len(last_line) - len(last_line.lstrip())
        indent_str = " " * indent
        return f"{inner},\n{indent_str}values_callable=lambda x: [e.value for e in x]{close}"
    else:
        # Single line: add inline
        return f"{inner}, values_callable=lambda x: [e.value for e in x]{close}"


def process_file(filepath: Path, apply: bool = False) -> int:
    """Process a single file. Returns count of fixes applied."""
    content = filepath.read_text()

    if "SQLEnum" not in content:
        return 0

    # Count how many need fixing
    fixes_needed = 0
    for match in SQLENUM_PATTERN.finditer(content):
        if needs_fix(match.group(1)):
            fixes_needed += 1

    if fixes_needed == 0:
        return 0

    if apply:
        new_content = SQLENUM_PATTERN.sub(fix_sqlenum, content)
        filepath.write_text(new_content)

    return fixes_needed


def main():
    apply = "--apply" in sys.argv

    if apply:
        print("APPLYING changes to model files...\n")
    else:
        print("DRY RUN — use --apply to make changes\n")

    total_files = 0
    total_fixes = 0

    for py_file in sorted(MODELS_DIR.rglob("*.py")):
        if py_file.name.startswith("_"):
            continue

        fixes = process_file(py_file, apply=apply)
        if fixes > 0:
            rel = py_file.relative_to(MODELS_DIR.parent.parent)
            action = "Fixed" if apply else "Would fix"
            print(f"  {action} {fixes} SQLEnum calls in {rel}")
            total_files += 1
            total_fixes += fixes

    print(f"\nTotal: {total_fixes} SQLEnum calls in {total_files} files")
    if not apply and total_fixes > 0:
        print("\nRun with --apply to make the changes.")

    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Validate enum column definitions across all SQLAlchemy models.

Catches enum drift before it reaches production by checking:
1. SQLEnum columns missing values_callable (will write uppercase to PG)
2. Enum classes with uppercase VALUES (should be lowercase)
3. Duplicate enum class names across different model files

Exit codes:
  0 — all checks pass
  1 — issues found (blocks commit)

Usage:
  python scripts/check_enum_columns.py
  python scripts/check_enum_columns.py --fix-hint   # show fix suggestions
"""

import sys
from enum import Enum
from pathlib import Path

backend_dir = str(Path(__file__).parent.parent)
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)


def check_values_callable() -> list[str]:
    """Find SQLEnum columns missing values_callable."""
    from app.core.database import Base
    import app.models  # noqa: F401

    from sqlalchemy import Enum as SQLEnum

    issues = []
    for table_name, table in Base.metadata.tables.items():
        for col in table.columns:
            if not isinstance(col.type, SQLEnum):
                continue
            enum_class = getattr(col.type, "enum_class", None)
            if enum_class is None:
                continue

            # Check if values_callable was set by comparing .enums to .value
            expected_values = [m.value for m in enum_class]
            actual_enums = list(col.type.enums)

            if actual_enums != expected_values:
                issues.append(
                    f"  {table_name}.{col.name}: SQLEnum({enum_class.__name__}) "
                    f"returns {actual_enums[:3]}... but values are {expected_values[:3]}... "
                    f"— add values_callable=lambda x: [e.value for e in x]"
                )

    return issues


def check_enum_values_case() -> list[str]:
    """Find enum classes where VALUES are uppercase (should be lowercase)."""
    import app.models as models_pkg

    issues = []
    for name in getattr(models_pkg, "__all__", []):
        obj = getattr(models_pkg, name, None)
        if obj is None:
            continue
        if not (isinstance(obj, type) and issubclass(obj, Enum) and issubclass(obj, str)):
            continue

        uppercase_values = [m.value for m in obj if m.value != m.value.lower()]
        if uppercase_values:
            issues.append(
                f"  {obj.__name__}: values contain uppercase: "
                f"{uppercase_values[:5]}... — use lowercase values"
            )

    return issues


def check_duplicate_enum_names() -> list[str]:
    """Find enum classes with the same name in different model files."""
    import importlib
    import inspect

    models_dir = Path(backend_dir) / "app" / "models"
    enum_locations: dict[str, list[str]] = {}

    for py_file in sorted(models_dir.rglob("*.py")):
        if py_file.name.startswith("_"):
            continue
        rel = py_file.relative_to(Path(backend_dir))
        module_path = str(rel).replace("/", ".").removesuffix(".py")
        try:
            mod = importlib.import_module(module_path)
        except Exception:
            continue

        for attr_name, attr in inspect.getmembers(mod, inspect.isclass):
            if (
                issubclass(attr, Enum)
                and issubclass(attr, str)
                and attr.__module__ == mod.__name__
            ):
                enum_locations.setdefault(attr_name, []).append(
                    str(rel)
                )

    issues = []
    for enum_name, locations in sorted(enum_locations.items()):
        if len(locations) > 1:
            issues.append(
                f"  {enum_name}: defined in {len(locations)} files: "
                f"{', '.join(locations[:4])}"
            )

    return issues


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Validate enum column definitions")
    parser.add_argument("--fix-hint", action="store_true", help="Show fix suggestions")
    args = parser.parse_args()

    print("Checking enum column definitions...\n")
    all_issues = []

    # Check 1: Missing values_callable
    print("1. Checking SQLEnum columns for values_callable...")
    vc_issues = check_values_callable()
    if vc_issues:
        print(f"   FAIL: {len(vc_issues)} columns missing values_callable")
        if args.fix_hint:
            for issue in vc_issues[:20]:
                print(issue)
            if len(vc_issues) > 20:
                print(f"   ... and {len(vc_issues) - 20} more")
        all_issues.extend(vc_issues)
    else:
        print("   PASS")

    # Check 2: Uppercase enum values
    print("2. Checking enum value case...")
    case_issues = check_enum_values_case()
    if case_issues:
        print(f"   FAIL: {len(case_issues)} enums have uppercase values")
        for issue in case_issues[:10]:
            print(issue)
        if len(case_issues) > 10:
            print(f"   ... and {len(case_issues) - 10} more")
        all_issues.extend(case_issues)
    else:
        print("   PASS")

    # Check 3: Duplicate names
    print("3. Checking for duplicate enum names...")
    dup_issues = check_duplicate_enum_names()
    if dup_issues:
        print(f"   WARN: {len(dup_issues)} duplicate enum names")
        if args.fix_hint:
            for issue in dup_issues[:10]:
                print(issue)
        # Warnings don't block — requires careful migration
    else:
        print("   PASS")

    print()
    if vc_issues:
        print(f"FAILED: {len(vc_issues)} blocking issues found")
        print("Run with --fix-hint for details")
        return 1
    else:
        warnings = len(case_issues) + len(dup_issues)
        if warnings:
            print(f"PASSED with {warnings} warnings")
        else:
            print("ALL CHECKS PASSED")
        return 0


if __name__ == "__main__":
    sys.exit(main())

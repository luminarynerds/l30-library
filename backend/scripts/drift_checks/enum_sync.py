# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Drift check: compare Python (str, Enum) classes against Postgres enum types."""

import sys
from enum import Enum
from pathlib import Path
from typing import Dict, List, Set, Tuple

backend_dir = str(Path(__file__).parent.parent.parent)
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from drift_checks.suppressions import Rule, is_suppressed


def get_python_enums() -> list:
    """Import all (str, Enum) subclasses from app.models.__all__."""
    import app.models as models_pkg

    enums = []
    for name in models_pkg.__all__:
        obj = getattr(models_pkg, name, None)
        if obj is None:
            continue
        if isinstance(obj, type) and issubclass(obj, Enum) and issubclass(obj, str):
            enums.append(obj)
    return enums


def diff_enum_values(
    type_name: str, python_vals: Set[str], db_vals: Set[str]
) -> dict:
    """Compare Python enum values against DB enum values.

    Returns dict with missing_in_db, extra_in_db, and case_mismatches.
    """
    missing_in_db = python_vals - db_vals
    extra_in_db = db_vals - python_vals

    # Check for case mismatches among values that appear in both sides
    py_lower = {v.lower(): v for v in python_vals}
    db_lower = {v.lower(): v for v in db_vals}
    case_mismatches = []
    for key in set(py_lower) & set(db_lower):
        if py_lower[key] != db_lower[key]:
            case_mismatches.append((py_lower[key], db_lower[key]))

    return {
        "missing_in_db": missing_in_db,
        "extra_in_db": extra_in_db,
        "case_mismatches": case_mismatches,
    }


async def check_enum_sync(rules: List[Rule]) -> list:
    """Compare Python enum definitions against Postgres enum types."""
    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import create_async_engine

    from app.core.config import get_settings

    settings = get_settings()
    engine = create_async_engine(settings.database_url, echo=False)

    findings = []

    try:
        # Fetch all DB enum types and their values
        async with engine.connect() as conn:
            result = await conn.execute(
                text(
                    "SELECT t.typname, e.enumlabel "
                    "FROM pg_type t "
                    "JOIN pg_enum e ON e.enumtypid = t.oid "
                    "ORDER BY t.typname, e.enumsortorder"
                )
            )
            rows = result.fetchall()

        db_enums: Dict[str, Set[str]] = {}
        for type_name, label in rows:
            db_enums.setdefault(type_name, set()).add(label)

        # Compare each Python enum
        python_enums = get_python_enums()
        for enum_cls in python_enums:
            type_name = enum_cls.__name__.lower()

            if is_suppressed(rules, "enum_sync", "ignore_type", type_name):
                continue

            if type_name not in db_enums:
                # Not a real PG enum — probably stored as String(50)
                continue

            python_vals = {m.value for m in enum_cls}
            db_vals = db_enums[type_name]
            diff = diff_enum_values(type_name, python_vals, db_vals)

            if diff["missing_in_db"]:
                findings.append({
                    "level": "error",
                    "msg": f"enum '{type_name}': values in Python but not DB: {sorted(diff['missing_in_db'])}",
                })
            if diff["extra_in_db"]:
                findings.append({
                    "level": "warning",
                    "msg": f"enum '{type_name}': values in DB but not Python: {sorted(diff['extra_in_db'])}",
                })
            if diff["case_mismatches"]:
                findings.append({
                    "level": "warning",
                    "msg": f"enum '{type_name}': case mismatches: {diff['case_mismatches']}",
                })
    finally:
        await engine.dispose()

    return findings

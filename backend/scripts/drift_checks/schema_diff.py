# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Drift check: compare SQLAlchemy model metadata against live DB schema."""

import sys
from pathlib import Path
from typing import Dict, List, Set, Tuple

backend_dir = str(Path(__file__).parent.parent.parent)
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from drift_checks.suppressions import Rule, is_suppressed

DEFERRED_TABLES_PATH = Path(__file__).parent.parent / "deferred_tables.txt"


def _normalize_type(t: str) -> str:
    """Normalize SQL type strings for comparison."""
    t = t.upper().strip()
    aliases = {
        "CHARACTER VARYING": "VARCHAR",
        "TIMESTAMP WITH TIME ZONE": "TIMESTAMPTZ",
        "TIMESTAMP WITHOUT TIME ZONE": "TIMESTAMP",
        "DOUBLE PRECISION": "FLOAT",
        "BOOLEAN": "BOOL",
        "INTEGER": "INT",
    }
    for full, short in aliases.items():
        t = t.replace(full, short)
    if "(" in t:
        t = t[: t.index("(")]
    return t


def load_deferred_tables(path: str) -> Set[str]:
    """Parse deferred_tables.txt into a set of table names."""
    p = Path(path)
    if not p.exists():
        return set()
    tables = set()
    for line in p.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        # Lines starting with ## are commented-out (undeferred) tables
        if line.startswith("##"):
            continue
        tables.add(line)
    return tables


def compare_columns(
    table_name: str,
    model_cols: Dict[str, str],
    db_cols: Dict[str, str],
) -> Tuple[List[str], List[Tuple]]:
    """Compare model columns against DB columns.

    Returns:
        (missing_cols, type_mismatches)
        missing_cols: column names in model but not in DB
        type_mismatches: list of (col_name, model_type, db_type) tuples
    """
    missing = []
    mismatches = []

    for col_name, model_type in model_cols.items():
        if col_name not in db_cols:
            missing.append(col_name)
            continue
        norm_model = _normalize_type(model_type)
        norm_db = _normalize_type(db_cols[col_name])
        if norm_model != norm_db:
            mismatches.append((col_name, model_type, db_cols[col_name]))

    return missing, mismatches


async def check_schema_diff(rules: List[Rule]) -> list:
    """Compare SQLAlchemy model metadata against live DB schema."""
    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import create_async_engine

    from app.core.config import get_settings

    # Import models to register them with Base.metadata
    import app.models  # noqa: F401
    from app.core.database import Base

    settings = get_settings()
    engine = create_async_engine(settings.database_url, echo=False)

    findings = []
    deferred = load_deferred_tables(str(DEFERRED_TABLES_PATH))

    try:
        async with engine.connect() as conn:
            # Get all DB tables
            result = await conn.execute(
                text(
                    "SELECT tablename FROM pg_tables "
                    "WHERE schemaname = 'public'"
                )
            )
            db_tables = {row[0] for row in result.fetchall()}

            # Get all DB columns
            result = await conn.execute(
                text(
                    "SELECT table_name, column_name, data_type "
                    "FROM information_schema.columns "
                    "WHERE table_schema = 'public' "
                    "ORDER BY table_name, ordinal_position"
                )
            )
            db_columns: Dict[str, Dict[str, str]] = {}
            for table_name, col_name, data_type in result.fetchall():
                db_columns.setdefault(table_name, {})[col_name] = data_type

        # Compare each model table
        for table in Base.metadata.tables.values():
            table_name = table.name

            if table_name in deferred:
                continue

            if is_suppressed(rules, "schema_diff", "ignore_table", table_name):
                continue

            if table_name not in db_tables:
                findings.append({
                    "level": "error",
                    "msg": f"Model table '{table_name}' not found in database",
                })
                continue

            # Build model column dict
            model_cols: Dict[str, str] = {}
            for col in table.columns:
                # Get the SQL type as string
                try:
                    type_str = str(col.type)
                except Exception:
                    type_str = col.type.__class__.__name__
                model_cols[col.name] = type_str

            db_table_cols = db_columns.get(table_name, {})
            missing, mismatches = compare_columns(
                table_name, model_cols, db_table_cols
            )

            for col_name in missing:
                findings.append({
                    "level": "error",
                    "msg": f"Table '{table_name}': column '{col_name}' in model but not in DB",
                })

            for col_name, model_type, db_type in mismatches:
                findings.append({
                    "level": "warning",
                    "msg": (
                        f"Table '{table_name}': column '{col_name}' "
                        f"type mismatch — model={model_type}, db={db_type}"
                    ),
                })
    finally:
        await engine.dispose()

    return findings

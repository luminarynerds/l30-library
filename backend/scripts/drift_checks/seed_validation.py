# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Drift check: verify every table referenced in seed files exists in the DB."""

import re
import sys
from pathlib import Path
from typing import List, Set

backend_dir = str(Path(__file__).parent.parent.parent)
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from drift_checks.suppressions import Rule, is_suppressed

SEEDS_DIR = Path(__file__).parent.parent.parent / "app" / "seeds"

# SQL keywords to exclude from table name detection
_SQL_KEYWORDS = {
    "select", "where", "set", "values", "true", "false", "null", "cast",
    "as", "and", "or", "not", "in", "is", "on", "by", "order", "group",
    "having", "limit", "offset", "returning", "join", "left", "right",
    "inner", "outer", "cross", "full", "of",
}

# Patterns that capture table names from SQL statements
_FROM_PATTERN = re.compile(r'\bFROM\s+([a-z_][a-z0-9_]*)', re.IGNORECASE)
_INSERT_PATTERN = re.compile(r'\bINSERT\s+INTO\s+([a-z_][a-z0-9_]*)', re.IGNORECASE)
_UPDATE_PATTERN = re.compile(r'\bUPDATE\s+([a-z_][a-z0-9_]*)', re.IGNORECASE)
# seq_tables = ["table1", "table2", ...]
_SEQ_TABLE_PATTERN = re.compile(r'seq_tables\s*=\s*\[([^\]]*)\]', re.DOTALL)
_QUOTED_STR = re.compile(r'["\']([a-z_][a-z0-9_]*)["\']')


def _strip_sql_strings(sql: str) -> str:
    """Remove SQL string literals so prose inside them isn't parsed as SQL keywords."""
    # Handles standard SQL: single-quoted strings with '' escape
    import re as _re
    return _re.sub(r"'(?:''|[^'])*'", "''", sql, flags=_re.DOTALL)


def _extract_sql_blocks(code: str) -> str:
    """Extract just the SQL text from text('...') and text(\"\"\"...\"\"\") calls."""
    # Match text("...") and text("""...""") — only SQL content, not Python string data
    sql_blocks = []
    for m in re.finditer(r'text\(\s*(?:"""(.*?)"""|"([^"]*)"|\'{3}(.*?)\'{3}|\'([^\']*)\')', code, re.DOTALL):
        sql_blocks.append(m.group(1) or m.group(2) or m.group(3) or m.group(4) or "")
    return _strip_sql_strings("\n".join(sql_blocks))


def extract_table_refs(code: str) -> Set[str]:
    """Extract table names from SQL patterns in seed file code."""
    tables = set()

    # Only search inside text() SQL blocks, not arbitrary Python strings
    sql_content = _extract_sql_blocks(code)

    for pattern in (_FROM_PATTERN, _INSERT_PATTERN, _UPDATE_PATTERN):
        for match in pattern.finditer(sql_content):
            name = match.group(1).lower()
            if name not in _SQL_KEYWORDS and not name.startswith("pg_") and name != "information_schema":
                tables.add(name)

    # Also extract from seq_tables list (Python-side, not SQL)
    for seq_match in _SEQ_TABLE_PATTERN.finditer(code):
        inner = seq_match.group(1)
        for quoted in _QUOTED_STR.finditer(inner):
            name = quoted.group(1).lower()
            if name not in _SQL_KEYWORDS:
                tables.add(name)

    return tables


async def check_seed_validation(rules: List[Rule]) -> list:
    """Verify every table referenced in seed files exists in the DB."""
    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import create_async_engine

    from app.core.config import get_settings

    settings = get_settings()
    engine = create_async_engine(settings.database_url, echo=False)

    findings = []

    try:
        async with engine.connect() as conn:
            result = await conn.execute(
                text(
                    "SELECT tablename FROM pg_tables "
                    "WHERE schemaname = 'public'"
                )
            )
            db_tables = {row[0] for row in result.fetchall()}

        # Scan all seed files
        seed_files = sorted(SEEDS_DIR.glob("seed_*.py"))
        for seed_file in seed_files:
            code = seed_file.read_text()
            refs = extract_table_refs(code)
            for table in sorted(refs):
                if is_suppressed(rules, "seed_validation", "ignore_table", table):
                    continue
                if table not in db_tables:
                    findings.append({
                        "level": "error",
                        "msg": (
                            f"Seed '{seed_file.name}' references table "
                            f"'{table}' which does not exist in DB"
                        ),
                    })
    finally:
        await engine.dispose()

    return findings

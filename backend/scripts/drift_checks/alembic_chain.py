# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Drift check: verify migration chain integrity and DB stamp validity."""

import re
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

backend_dir = str(Path(__file__).parent.parent.parent)
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from drift_checks.suppressions import Rule, is_suppressed

VERSIONS_DIR = Path(__file__).parent.parent.parent / "alembic" / "versions"

_REV_PATTERN = re.compile(
    r'^revision(?:\s*:\s*[^=]+)?\s*=\s*["\']([^"\']+)["\']',
    re.MULTILINE,
)
_DOWN_REV_RHS_PATTERN = re.compile(
    r'^down_revision(?:\s*:\s*[^=]+)?\s*=\s*(.+?)(?:\n|$)',
    re.MULTILINE | re.DOTALL,
)
_QUOTED_STR_PATTERN = re.compile(r'["\']([^"\']+)["\']')


def parse_revision_file(path: str) -> Tuple[Optional[str], List[str]]:
    """Extract revision and down_revision(s) from a migration file.

    Returns (revision, down_revisions). down_revisions is empty list for
    the base. Merge migrations with tuple/sequence down_revisions return
    all parents.
    """
    content = Path(path).read_text()

    rev_match = _REV_PATTERN.search(content)
    revision = rev_match.group(1) if rev_match else None

    down_revisions: List[str] = []
    rhs_match = _DOWN_REV_RHS_PATTERN.search(content)
    if rhs_match:
        rhs = rhs_match.group(1).strip()
        # tuple/list across multiple lines: capture until matching close paren
        if rhs.startswith("(") or rhs.startswith("["):
            depth = 0
            end = 0
            full_content = content[rhs_match.start(1):]
            for i, ch in enumerate(full_content):
                if ch in "([":
                    depth += 1
                elif ch in ")]":
                    depth -= 1
                    if depth == 0:
                        end = i + 1
                        break
            rhs = full_content[:end] if end else rhs
        down_revisions = _QUOTED_STR_PATTERN.findall(rhs)

    return revision, down_revisions


def find_heads(revisions: Dict[str, List[str]]) -> List[str]:
    """Find revisions not referenced as down_revision by anyone else.

    These are the 'head' revisions in the migration chain. Handles merge
    migrations where down_revision is a tuple of parent revisions.
    """
    all_down_revs: set = set()
    for parents in revisions.values():
        all_down_revs.update(parents)
    heads = [rev for rev in revisions if rev not in all_down_revs]
    return sorted(heads)


async def check_alembic_chain(rules: List[Rule]) -> list:
    """Verify migration chain integrity and DB stamp validity."""
    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import create_async_engine

    from app.core.config import get_settings

    settings = get_settings()
    engine = create_async_engine(settings.database_url, echo=False)

    findings = []

    try:
        # Parse all migration files
        revisions: Dict[str, List[str]] = {}
        if VERSIONS_DIR.exists():
            for f in sorted(VERSIONS_DIR.glob("*.py")):
                if f.name == "__pycache__":
                    continue
                rev, down_revs = parse_revision_file(str(f))
                if rev:
                    revisions[rev] = down_revs

        if not revisions:
            findings.append({
                "level": "warning",
                "msg": "No migration revisions found",
            })
            return findings

        # Check for forked heads
        heads = find_heads(revisions)
        if len(heads) > 1:
            if not is_suppressed(rules, "alembic_chain", "ignore_fork", f"{len(heads)}_heads"):
                findings.append({
                    "level": "error",
                    "msg": f"Migration chain has {len(heads)} heads (forked): {heads}",
                })

        # Check DB stamp
        async with engine.connect() as conn:
            try:
                result = await conn.execute(
                    text("SELECT version_num FROM alembic_version")
                )
                rows = result.fetchall()
            except Exception:
                findings.append({
                    "level": "warning",
                    "msg": "alembic_version table not found — migrations may not be initialized",
                })
                return findings

        if not rows:
            findings.append({
                "level": "warning",
                "msg": "alembic_version table is empty — no stamp applied",
            })
            return findings

        for row in rows:
            db_stamp = row[0]

            if is_suppressed(rules, "alembic_chain", "ignore_stamp", db_stamp):
                continue

            if db_stamp not in revisions:
                findings.append({
                    "level": "error",
                    "msg": f"DB stamp '{db_stamp}' not found in migration files",
                })
                continue

            # Check for unapplied migrations
            if heads and db_stamp not in heads:
                findings.append({
                    "level": "warning",
                    "msg": (
                        f"DB stamp '{db_stamp}' is not at head. "
                        f"Head(s): {heads}. Unapplied migrations exist."
                    ),
                })
    finally:
        await engine.dispose()

    return findings

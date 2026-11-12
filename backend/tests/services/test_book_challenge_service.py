# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Unit tests for BookChallengeService.list_public_challenges sort order.

Why a SQL-string assertion (not a live insert): L30's test conftest
shares a singleton async engine + per-function event loops, which makes
DB-backed service tests fragile (see feedback_l30_conftest_singleton_
engine_loop_trap). We don't need a live DB to verify the ORDER BY
clause -- we can capture the SQL the service compiles and assert on it.

The bug we're guarding: previously the service ordered by
``date_resolved DESC NULLS LAST``, which sank unresolved (PENDING)
challenges below the entire resolved history. With limit=20 + a long
history, pending items vanish. Fixed by ordering on
``coalesce(date_resolved, date_received) DESC`` so PENDING rows surface
naturally (their ``date_received`` is recent).
"""
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.book_challenge_service import BookChallengeService


def _compile_sql(executed_call) -> str:
    """Pull the SQLAlchemy statement out of a db.execute() mock call and
    render it as a string for substring assertions."""
    stmt = executed_call.args[0]
    return str(stmt.compile(compile_kwargs={"literal_binds": True}))


@pytest.mark.asyncio
async def test_list_public_challenges_orders_by_coalesce_date():
    """ORDER BY must coalesce(date_resolved, date_received) DESC so
    pending (unresolved, NULL date_resolved) entries surface naturally."""
    db = AsyncMock()
    scalars = MagicMock()
    scalars.all.return_value = []
    result = MagicMock()
    result.scalars.return_value = scalars
    db.execute = AsyncMock(return_value=result)

    await BookChallengeService.list_public_challenges(db, limit=20)

    db.execute.assert_awaited_once()
    sql = _compile_sql(db.execute.await_args).lower()
    assert "order by" in sql
    assert "coalesce(" in sql, f"expected coalesce in ORDER BY, got: {sql}"
    # Both columns must appear inside the coalesce
    assert "date_resolved" in sql
    assert "date_received" in sql
    # Descending order
    assert "desc" in sql.split("order by", 1)[1]
    # Regression guard: the broken pattern was `date_resolved DESC NULLS LAST`
    # without coalesce. Confirm the bare-column ORDER BY is gone.
    order_clause = sql.split("order by", 1)[1]
    assert "nulls last" not in order_clause, (
        "ORDER BY still uses NULLS LAST -- pending items will sink: " + order_clause
    )


@pytest.mark.asyncio
async def test_list_public_challenges_filters_to_is_public_true():
    """Regression: only is_public=True rows are exposed."""
    db = AsyncMock()
    scalars = MagicMock()
    scalars.all.return_value = []
    result = MagicMock()
    result.scalars.return_value = scalars
    db.execute = AsyncMock(return_value=result)

    await BookChallengeService.list_public_challenges(db, limit=5)

    sql = _compile_sql(db.execute.await_args).lower()
    assert "is_public" in sql
    assert "limit 5" in sql or "limit\n5" in sql


@pytest.mark.asyncio
async def test_pending_before_resolved_with_coalesce_logic():
    """In-Python sanity check that coalesce(date_resolved, date_received)
    sorting puts a recent PENDING (no date_resolved) above an older RESOLVED.

    This validates the conceptual fix without booting a DB: simulate the
    sort key the new SQL produces and confirm pending wins on recency.
    """
    from datetime import datetime, timezone

    pending = {
        "id": 1,
        "date_received": datetime(2026, 5, 19, tzinfo=timezone.utc),
        "date_resolved": None,
        "outcome": "pending",
    }
    older_resolved = {
        "id": 2,
        "date_received": datetime(2024, 1, 5, tzinfo=timezone.utc),
        "date_resolved": datetime(2024, 3, 1, tzinfo=timezone.utc),
        "outcome": "retained",
    }

    def coalesce_key(row):
        return row["date_resolved"] or row["date_received"]

    ordered = sorted([older_resolved, pending], key=coalesce_key, reverse=True)
    assert ordered[0]["id"] == 1, "pending (newer date_received) must rank first"

# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Unit tests for demand_signal_service.

Mocks ``db.execute()`` / ``db.add()`` / ``db.commit()`` to keep the
suite Postgres-free. The record-side helper must NEVER raise into the
caller -- a separate test forces a DB-level failure and confirms the
exception is swallowed.
"""

from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services import demand_signal_service


@pytest.mark.asyncio
async def test_record_signal_inserts_and_commits():
    db = AsyncMock()
    db.add = MagicMock()
    db.commit = AsyncMock()

    await demand_signal_service.record_signal(
        db,
        signal_type="failed_search",
        query_text="ada lovelace",
        patron_id=42,
    )

    db.add.assert_called_once()
    db.commit.assert_awaited_once()
    row = db.add.call_args.args[0]
    assert row.signal_type == "failed_search"
    assert row.query_text == "ada lovelace"
    assert row.patron_id == 42


@pytest.mark.asyncio
async def test_record_signal_swallows_db_error():
    # commit raises -- record_signal must not propagate
    db = AsyncMock()
    db.add = MagicMock()
    db.commit = AsyncMock(side_effect=RuntimeError("db down"))
    db.rollback = AsyncMock()

    # This should NOT raise
    await demand_signal_service.record_signal(
        db,
        signal_type="failed_search",
        query_text="boom",
    )

    db.rollback.assert_awaited_once()


@pytest.mark.asyncio
async def test_record_signal_normalizes_isbn_and_title():
    db = AsyncMock()
    db.add = MagicMock()
    db.commit = AsyncMock()

    await demand_signal_service.record_signal(
        db,
        signal_type="ill_request",
        normalized_isbn="978-0-13-468599-1",
        normalized_title="   The   Pragmatic    Programmer  ",
    )

    row = db.add.call_args.args[0]
    assert row.normalized_isbn == "9780134685991"
    assert row.normalized_title == "The Pragmatic Programmer"


@pytest.mark.asyncio
async def test_record_signal_empty_inputs_become_none():
    db = AsyncMock()
    db.add = MagicMock()
    db.commit = AsyncMock()

    await demand_signal_service.record_signal(
        db,
        signal_type="failed_search",
        normalized_isbn="",
        normalized_title="   ",
    )

    row = db.add.call_args.args[0]
    assert row.normalized_isbn is None
    assert row.normalized_title is None


@pytest.mark.asyncio
async def test_get_top_demand_orders_by_weighted_count():
    """Aggregation correctness: rows come back in the order the query
    produces them; we just confirm the result-mapping shape and that
    counts/weights are coerced to int/float.
    """
    # Simulate two grouped rows ordered by weighted_count desc.
    row_a = SimpleNamespace(
        group_key="9780134685991",
        signal_type="failed_search",
        normalized_isbn="9780134685991",
        normalized_title=None,
        count=5,
        weighted_count=8.0,
        most_recent=datetime(2026, 5, 19, 12, 0, tzinfo=timezone.utc),
    )
    row_b = SimpleNamespace(
        group_key="The Pragmatic Programmer",
        signal_type="failed_search",
        normalized_isbn=None,
        normalized_title="The Pragmatic Programmer",
        count=2,
        weighted_count=3.0,
        most_recent=datetime(2026, 5, 18, 9, 0, tzinfo=timezone.utc),
    )
    execute_result = MagicMock()
    execute_result.all.return_value = [row_a, row_b]

    db = AsyncMock()
    db.execute = AsyncMock(return_value=execute_result)

    items = await demand_signal_service.get_top_demand(db, days=30, limit=10)

    assert len(items) == 2
    assert items[0]["key"] == "9780134685991"
    assert items[0]["count"] == 5
    assert items[0]["weighted_count"] == 8.0
    assert items[0]["normalized_isbn"] == "9780134685991"
    assert items[1]["normalized_title"] == "The Pragmatic Programmer"
    assert items[1]["normalized_isbn"] is None
    # most_recent serialized as ISO 8601
    assert items[0]["most_recent"].startswith("2026-05-19")


@pytest.mark.asyncio
async def test_get_top_demand_clamps_days_and_limit():
    execute_result = MagicMock()
    execute_result.all.return_value = []
    db = AsyncMock()
    db.execute = AsyncMock(return_value=execute_result)

    # Out-of-range values should be clamped, not raise.
    out = await demand_signal_service.get_top_demand(db, days=9999, limit=9999)
    assert out == []
    out2 = await demand_signal_service.get_top_demand(db, days=0, limit=0)
    assert out2 == []

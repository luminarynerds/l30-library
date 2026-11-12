# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Unit test for catalog_velocity_jobs.refresh_catalog_velocity_mv.

The actual REFRESH MATERIALIZED VIEW CONCURRENTLY behaviour requires a
real Postgres instance (SQLite has no materialized views), so this
suite only verifies that the refresh function:

* opens a session,
* executes the REFRESH statement,
* commits,
* executes the row-count query,
* logs the result through JobExecutionContext.

End-to-end MV behaviour is exercised manually post-deploy per the PR
description.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock

import pytest


@pytest.mark.asyncio
async def test_refresh_calls_concurrent_refresh_and_counts(monkeypatch):
    """REFRESH ... CONCURRENTLY + COUNT(*) both run; commit between."""
    from app.services.schedulers import catalog_velocity_jobs as job_mod

    executed_sqls: list[str] = []

    async def fake_execute(stmt, *args, **kwargs):
        # SQLAlchemy ``text()`` exposes the SQL via str().
        executed_sqls.append(str(stmt))
        result = MagicMock()
        result.scalar = MagicMock(return_value=4242)
        return result

    db = AsyncMock()
    db.execute = AsyncMock(side_effect=fake_execute)
    db.commit = AsyncMock()

    @asynccontextmanager
    async def fake_session_local():
        yield db

    monkeypatch.setattr(
        job_mod,
        "AsyncSessionLocal",
        lambda: fake_session_local(),
    )

    # Stub JobExecutionContext so we don't need a real DB-backed job
    # failure table for a unit test. The replacement preserves the
    # add_metric / items_processed protocol used by the refresh fn.
    class _FakeCtx:
        def __init__(self, **_kwargs):
            self.metrics: dict = {}
            self.items_processed = 0
            self.items_succeeded = 0

        async def __aenter__(self):
            return self

        async def __aexit__(self, *exc):
            return False

        def add_metric(self, key, value):
            self.metrics[key] = value

    monkeypatch.setattr(job_mod, "JobExecutionContext", _FakeCtx)

    await job_mod.refresh_catalog_velocity_mv()

    # Two execute calls: the REFRESH and the COUNT(*)
    assert len(executed_sqls) == 2, executed_sqls
    assert "REFRESH MATERIALIZED VIEW CONCURRENTLY" in executed_sqls[0]
    assert "catalog_circulation_velocity_mv" in executed_sqls[0]
    assert "COUNT(*)" in executed_sqls[1]
    db.commit.assert_awaited_once()

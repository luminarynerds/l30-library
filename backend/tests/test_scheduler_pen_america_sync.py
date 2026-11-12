# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Tests for the PEN America weekly sync job registration.

The wrapper itself is exercised end-to-end by the existing ban_tracker /
pen_america tests; here we verify the scheduler bootstrap actually wires
the job so a deploy doesn't silently lose the cron.
"""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core import scheduler as scheduler_module


def test_init_scheduler_registers_pen_america_weekly_job():
    """init_scheduler() must call add_job for the PEN America wrapper with a
    weekly CronTrigger (day_of_week='sun', hour=3, minute=0)."""
    # Reset the module-level singleton so a previous test run doesn't leak.
    scheduler_module.scheduler = None

    fake_scheduler = MagicMock()
    with patch.object(
        scheduler_module, "AsyncIOScheduler", return_value=fake_scheduler
    ):
        scheduler_module.init_scheduler()

    # Find the pen_america_weekly_sync add_job call.
    pen_calls = [
        call for call in fake_scheduler.add_job.call_args_list
        if call.kwargs.get("id") == "pen_america_weekly_sync"
    ]
    assert len(pen_calls) == 1, (
        f"Expected exactly one pen_america_weekly_sync registration, got {len(pen_calls)}. "
        f"All add_job ids: {[c.kwargs.get('id') for c in fake_scheduler.add_job.call_args_list]}"
    )

    call = pen_calls[0]
    # First positional arg is the wrapper function.
    fn = call.args[0]
    assert fn is scheduler_module._pen_america_weekly_sync, (
        f"add_job wired the wrong callable: {fn!r}"
    )

    # Second positional arg is the CronTrigger.
    trigger = call.args[1]
    # CronTrigger.fields is a list of fields; check via repr for stability.
    trigger_repr = repr(trigger)
    assert "day_of_week='sun'" in trigger_repr, (
        f"Expected Sunday trigger, got {trigger_repr}"
    )
    assert "hour='3'" in trigger_repr, f"Expected 03:00 hour, got {trigger_repr}"
    assert "minute='0'" in trigger_repr, f"Expected minute=0, got {trigger_repr}"

    # Job metadata.
    assert call.kwargs.get("replace_existing") is True
    # misfire_grace_time should be generous (deploys can push the run by
    # tens of minutes); accept anything >= 60s.
    assert (call.kwargs.get("misfire_grace_time") or 0) >= 60, (
        f"misfire_grace_time should be >=60s, got {call.kwargs.get('misfire_grace_time')}"
    )


@pytest.mark.asyncio
async def test_pen_america_wrapper_calls_sync_and_invalidates_cache():
    """The wrapper must invoke PenAmericaSyncService.sync inside a DB session
    and flush both stats caches."""
    fake_stats = {
        "new_reports": 3,
        "duplicates_skipped": 1,
        "matches_found": 2,
        "errors": 0,
    }

    with patch.object(
        scheduler_module, "AsyncSessionLocal"
    ) as mock_session_local, patch(
        "app.services.pen_america_sync_service.PenAmericaSyncService.sync",
        new_callable=AsyncMock,
        return_value=fake_stats,
    ) as mock_sync, patch(
        "app.core.cache.invalidate_cache", new_callable=AsyncMock, return_value=0
    ) as mock_invalidate:
        # AsyncSessionLocal() must yield a context manager.
        fake_db = MagicMock()
        mock_session_local.return_value.__aenter__ = AsyncMock(return_value=fake_db)
        mock_session_local.return_value.__aexit__ = AsyncMock(return_value=None)

        await scheduler_module._pen_america_weekly_sync()

    mock_sync.assert_awaited_once_with(fake_db)
    invalidated = {call.args[0] for call in mock_invalidate.call_args_list}
    assert "ban_tracker:stats*" in invalidated, (
        f"Expected ban_tracker stats invalidation, got {invalidated}"
    )
    assert "book_challenges:stats*" in invalidated, (
        f"Expected book_challenges stats invalidation, got {invalidated}"
    )


@pytest.mark.asyncio
async def test_pen_america_wrapper_swallows_exceptions():
    """A crash inside sync() must not propagate (would crash the scheduler)."""
    with patch.object(
        scheduler_module, "AsyncSessionLocal"
    ) as mock_session_local, patch(
        "app.services.pen_america_sync_service.PenAmericaSyncService.sync",
        new_callable=AsyncMock,
        side_effect=RuntimeError("upstream down"),
    ):
        fake_db = MagicMock()
        mock_session_local.return_value.__aenter__ = AsyncMock(return_value=fake_db)
        mock_session_local.return_value.__aexit__ = AsyncMock(return_value=None)

        # Must NOT raise.
        await scheduler_module._pen_america_weekly_sync()

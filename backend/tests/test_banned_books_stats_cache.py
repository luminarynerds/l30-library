# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Redis caching for public banned-books stats endpoints.

Covers both BanTrackerService.get_statistics and
BookChallengeService.get_statistics. The hot path is a public endpoint hit
by every page load of /banned-books — caching collapses 4-6 DB queries to
a single Redis read.

Tests run in pure-mock mode (no DB, no real Redis) because conftest's
singleton-engine bug bites hard on suites that mix DB fixtures and that
isn't what we're testing here.
"""
from unittest.mock import AsyncMock, patch

import pytest


# ---------------------------------------------------------------------------
# BookChallengeService
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_book_challenge_stats_caches_after_first_call():
    """First call runs _compute_statistics, second call returns cached value
    without touching the DB function."""
    from app.services import book_challenge_service as bc_svc

    fake_stats = {
        "total_challenges": 7,
        "pending_challenges": 2,
        "resolved_this_year": 1,
        "outcomes": {"RETAINED": 4, "REMOVED": 1},
        "reasons": {"OTHER": 5},
    }

    # Simulated Redis store: get returns None first, then the cached value.
    cache: dict = {}

    async def fake_get(key):
        return cache.get(key)

    async def fake_set(key, value, ttl_seconds=300):
        cache[key] = value

    with patch.object(
        bc_svc.BookChallengeService,
        "_compute_statistics",
        new_callable=AsyncMock,
        return_value=fake_stats,
    ) as mock_compute, patch.object(
        bc_svc, "get_cached", side_effect=fake_get
    ), patch.object(
        bc_svc, "set_cached", side_effect=fake_set
    ):
        fake_db = object()
        first = await bc_svc.BookChallengeService.get_statistics(fake_db)
        second = await bc_svc.BookChallengeService.get_statistics(fake_db)

    assert first == fake_stats
    assert second == fake_stats
    assert mock_compute.await_count == 1, (
        f"_compute_statistics should be called exactly once across two get_statistics "
        f"calls; got {mock_compute.await_count}"
    )


@pytest.mark.asyncio
async def test_book_challenge_create_invalidates_stats_cache():
    """Creating a challenge must drop the stats cache so the public stats
    card sees the new submission within seconds, not within an hour."""
    from app.services import book_challenge_service as bc_svc

    with patch.object(
        bc_svc, "invalidate_cache", new_callable=AsyncMock, return_value=0
    ) as mock_invalidate:
        await bc_svc._invalidate_stats_cache()

    mock_invalidate.assert_awaited_once_with("book_challenges:stats*")


@pytest.mark.asyncio
async def test_book_challenge_invalidate_helper_swallows_errors():
    """Invalidation must never raise — Redis outage shouldn't break writes."""
    from app.services import book_challenge_service as bc_svc

    with patch.object(
        bc_svc, "invalidate_cache",
        new_callable=AsyncMock,
        side_effect=RuntimeError("redis down"),
    ):
        # Must not raise.
        await bc_svc._invalidate_stats_cache()


# ---------------------------------------------------------------------------
# BanTrackerService
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_ban_tracker_stats_caches_after_first_call():
    """Same hit/miss assertion for the ban tracker stats endpoint."""
    from app.services import ban_tracker_service as bt_svc

    fake_stats = {
        "total_reports": 142,
        "total_states": 38,
        "total_catalog_matches": 17,
        "by_state": {"TX": 50, "FL": 40},
        "by_type": {"removed": 80, "challenged": 62},
        "by_reason": {"LGBTQ": 60, "RACE": 25},
    }

    cache: dict = {}

    async def fake_get(key):
        return cache.get(key)

    async def fake_set(key, value, ttl_seconds=300):
        cache[key] = value

    with patch.object(
        bt_svc.BanTrackerService,
        "_compute_statistics",
        new_callable=AsyncMock,
        return_value=fake_stats,
    ) as mock_compute, patch.object(
        bt_svc, "get_cached", side_effect=fake_get
    ), patch.object(
        bt_svc, "set_cached", side_effect=fake_set
    ):
        fake_db = object()
        first = await bt_svc.BanTrackerService.get_statistics(fake_db)
        second = await bt_svc.BanTrackerService.get_statistics(fake_db)
        third = await bt_svc.BanTrackerService.get_statistics(fake_db)

    assert first == second == third == fake_stats
    assert mock_compute.await_count == 1, (
        f"_compute_statistics should be called once across three reads; "
        f"got {mock_compute.await_count}"
    )


@pytest.mark.asyncio
async def test_ban_tracker_trigger_sync_invalidates_stats_cache():
    """The manual PEN America trigger must flush stats so post-sync totals
    show up on the next public stats fetch."""
    from app.services import ban_tracker_service as bt_svc

    with patch(
        "app.services.pen_america_sync_service.PenAmericaSyncService.sync",
        new_callable=AsyncMock,
        return_value={"new_reports": 5},
    ), patch.object(
        bt_svc, "invalidate_cache", new_callable=AsyncMock, return_value=0
    ) as mock_invalidate:
        fake_db = object()
        result = await bt_svc.BanTrackerService.trigger_pen_america_sync(fake_db)

    assert result == {"new_reports": 5}
    mock_invalidate.assert_awaited_once_with("ban_tracker:stats*")

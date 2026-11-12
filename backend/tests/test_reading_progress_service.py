# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Tests for ReadingProgressService and milestone integration."""

import pytest
from app.services.reading_progress_service import ReadingProgressService
from app.services.reading_milestone_service import ReadingMilestoneService
from app.services.reading_activity_service import ReadingActivityService


@pytest.mark.asyncio
async def test_log_progress_page_level(test_db, test_patron, test_catalog_item):
    """Logging progress with page numbers creates an entry."""
    entry, milestone = await ReadingProgressService.log_progress(
        test_db, test_patron.id, test_catalog_item.id,
        current_page=50, total_pages=300, percent=17,
    )
    assert entry.current_page == 50
    assert entry.total_pages == 300
    assert entry.percent == 17
    assert entry.note is None


@pytest.mark.asyncio
async def test_log_progress_percentage_fallback(test_db, test_patron, test_catalog_item):
    """Logging progress with only percent (no page numbers)."""
    entry, _ = await ReadingProgressService.log_progress(
        test_db, test_patron.id, test_catalog_item.id,
        current_page=None, total_pages=None, percent=50,
    )
    assert entry.percent == 50
    assert entry.current_page is None


@pytest.mark.asyncio
async def test_get_history(test_db, test_patron, test_catalog_item):
    """History returns entries in reverse chronological order."""
    for page in [10, 50, 100]:
        await ReadingProgressService.log_progress(
            test_db, test_patron.id, test_catalog_item.id,
            current_page=page, total_pages=300, percent=round(page / 300 * 100),
        )
    history = await ReadingProgressService.get_history(
        test_db, test_patron.id, test_catalog_item.id
    )
    assert len(history) == 3
    assert history[0].current_page == 100  # Most recent first


@pytest.mark.asyncio
async def test_get_latest(test_db, test_patron, test_catalog_item):
    """Latest returns the most recent entry."""
    await ReadingProgressService.log_progress(
        test_db, test_patron.id, test_catalog_item.id,
        current_page=10, total_pages=300, percent=3,
    )
    await ReadingProgressService.log_progress(
        test_db, test_patron.id, test_catalog_item.id,
        current_page=99, total_pages=300, percent=33,
    )
    latest = await ReadingProgressService.get_latest(
        test_db, test_patron.id, test_catalog_item.id
    )
    assert latest is not None
    assert latest.current_page == 99


@pytest.mark.asyncio
async def test_pace_requires_three_entries(test_db, test_patron, test_catalog_item):
    """Pace returns None with fewer than 3 entries."""
    await ReadingProgressService.log_progress(
        test_db, test_patron.id, test_catalog_item.id,
        current_page=10, total_pages=300, percent=3,
    )
    pace = await ReadingProgressService.compute_pace(
        test_db, test_patron.id, test_catalog_item.id
    )
    assert pace is None


@pytest.mark.asyncio
async def test_first_progress_triggers_milestone(test_db, test_patron, test_catalog_item):
    """First progress log ever should trigger first_progress milestone."""
    _, milestone_data = await ReadingProgressService.log_progress(
        test_db, test_patron.id, test_catalog_item.id,
        current_page=10, total_pages=300, percent=3,
    )
    assert milestone_data is not None
    assert milestone_data["milestone_key"] == "first_progress"


@pytest.mark.asyncio
async def test_progress_creates_activity(test_db, test_patron, test_catalog_item):
    """Logging progress creates an activity feed entry."""
    await ReadingProgressService.log_progress(
        test_db, test_patron.id, test_catalog_item.id,
        current_page=50, total_pages=300, percent=17,
    )
    activities, total = await ReadingActivityService.get_recent(
        test_db, test_patron.id, limit=10
    )
    # Should have at least a progress_logged entry (and possibly milestone_earned)
    progress_activities = [a for a in activities if a.activity_type == "progress_logged"]
    assert len(progress_activities) >= 1


@pytest.mark.asyncio
async def test_empty_patron_no_latest(test_db, test_patron):
    """Empty patron has no latest progress."""
    results = await ReadingProgressService.get_all_latest(test_db, test_patron.id)
    assert results == []

# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Tests for ReadingStatusService."""

import pytest
from app.models.reading_status import ShelfStatus
from app.services.reading_status_service import ReadingStatusService


@pytest.mark.asyncio
async def test_set_status_creates_new(test_db, test_patron, test_catalog_item):
    """Setting status on a new book creates a reading status."""
    result, _ = await ReadingStatusService.set_status(
        test_db, test_patron.id, test_catalog_item.id, ShelfStatus.want_to_read
    )
    assert result.status == ShelfStatus.want_to_read
    assert result.catalog_item_id == test_catalog_item.id
    assert result.started_at is None
    assert result.finished_at is None


@pytest.mark.asyncio
async def test_set_status_currently_reading_sets_started_at(test_db, test_patron, test_catalog_item):
    """Moving to currently_reading auto-sets started_at."""
    result, _ = await ReadingStatusService.set_status(
        test_db, test_patron.id, test_catalog_item.id, ShelfStatus.currently_reading
    )
    assert result.started_at is not None


@pytest.mark.asyncio
async def test_set_status_finished_sets_finished_at(test_db, test_patron, test_catalog_item):
    """Moving to finished auto-sets finished_at."""
    await ReadingStatusService.set_status(
        test_db, test_patron.id, test_catalog_item.id, ShelfStatus.currently_reading
    )
    result, _ = await ReadingStatusService.set_status(
        test_db, test_patron.id, test_catalog_item.id, ShelfStatus.finished
    )
    assert result.finished_at is not None
    assert result.started_at is not None


@pytest.mark.asyncio
async def test_set_status_upserts(test_db, test_patron, test_catalog_item):
    """Setting status twice updates, doesn't create duplicate."""
    await ReadingStatusService.set_status(
        test_db, test_patron.id, test_catalog_item.id, ShelfStatus.want_to_read
    )
    result, _ = await ReadingStatusService.set_status(
        test_db, test_patron.id, test_catalog_item.id, ShelfStatus.currently_reading
    )
    assert result.status == ShelfStatus.currently_reading

    statuses = await ReadingStatusService.get_user_statuses(test_db, test_patron.id)
    assert len(statuses) == 1


@pytest.mark.asyncio
async def test_set_status_invalid_item(test_db, test_patron):
    """Setting status on nonexistent item raises ValueError."""
    with pytest.raises(ValueError, match="Catalog item not found"):
        await ReadingStatusService.set_status(
            test_db, test_patron.id, 99999, ShelfStatus.want_to_read
        )


@pytest.mark.asyncio
async def test_remove_status(test_db, test_patron, test_catalog_item):
    """Removing status deletes the record."""
    await ReadingStatusService.set_status(
        test_db, test_patron.id, test_catalog_item.id, ShelfStatus.want_to_read
    )
    removed = await ReadingStatusService.remove_status(test_db, test_patron.id, test_catalog_item.id)
    assert removed is True

    statuses = await ReadingStatusService.get_user_statuses(test_db, test_patron.id)
    assert len(statuses) == 0


@pytest.mark.asyncio
async def test_remove_status_not_found(test_db, test_patron):
    """Removing nonexistent status returns False."""
    removed = await ReadingStatusService.remove_status(test_db, test_patron.id, 99999)
    assert removed is False


@pytest.mark.asyncio
async def test_get_stats(test_db, test_patron, test_catalog_item):
    """Stats reflect correct shelf counts."""
    await ReadingStatusService.set_status(
        test_db, test_patron.id, test_catalog_item.id, ShelfStatus.finished
    )
    stats = await ReadingStatusService.get_stats(test_db, test_patron.id)
    assert stats["finished"] == 1
    assert stats["finished_this_year"] == 1
    assert stats["want_to_read"] == 0


@pytest.mark.asyncio
async def test_filter_by_status(test_db, test_patron, test_catalog_item):
    """Filtering by status returns only matching items."""
    await ReadingStatusService.set_status(
        test_db, test_patron.id, test_catalog_item.id, ShelfStatus.want_to_read
    )
    results = await ReadingStatusService.get_user_statuses(
        test_db, test_patron.id, status_filter=ShelfStatus.currently_reading
    )
    assert len(results) == 0

    results = await ReadingStatusService.get_user_statuses(
        test_db, test_patron.id, status_filter=ShelfStatus.want_to_read
    )
    assert len(results) == 1


@pytest.mark.asyncio
async def test_private_notes(test_db, test_patron, test_catalog_item):
    """Private notes are saved and retrievable."""
    result, _ = await ReadingStatusService.set_status(
        test_db, test_patron.id, test_catalog_item.id, ShelfStatus.currently_reading,
        private_notes="Really enjoying chapter 3"
    )
    assert result.private_notes == "Really enjoying chapter 3"

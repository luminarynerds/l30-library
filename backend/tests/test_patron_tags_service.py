# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Tests for PatronTagsService."""

import pytest
from app.models.reading_status import ShelfStatus
from app.services.reading_status_service import ReadingStatusService
from app.services.patron_tags_service import PatronTagsService


@pytest.mark.asyncio
async def test_get_all_tags_empty(test_db, test_patron):
    """Empty patron has no tags."""
    tags = await PatronTagsService.get_all_tags(test_db, test_patron.id)
    assert tags == []


@pytest.mark.asyncio
async def test_get_all_tags(test_db, test_patron, test_catalog_item):
    """Tags are aggregated and deduplicated across entries."""
    await ReadingStatusService.set_status(
        test_db, test_patron.id, test_catalog_item.id,
        ShelfStatus.currently_reading,
        personal_tags=["sci-fi", "favorites"],
    )
    tags = await PatronTagsService.get_all_tags(test_db, test_patron.id)
    assert "sci-fi" in tags
    assert "favorites" in tags
    assert len(tags) == 2


@pytest.mark.asyncio
async def test_rename_tag(test_db, test_patron, test_catalog_item):
    """Renaming a tag updates across all entries."""
    await ReadingStatusService.set_status(
        test_db, test_patron.id, test_catalog_item.id,
        ShelfStatus.currently_reading,
        personal_tags=["scifi", "good"],
    )
    count = await PatronTagsService.rename_tag(
        test_db, test_patron.id, "scifi", "sci-fi"
    )
    assert count == 1

    tags = await PatronTagsService.get_all_tags(test_db, test_patron.id)
    assert "sci-fi" in tags
    assert "scifi" not in tags


@pytest.mark.asyncio
async def test_delete_tag(test_db, test_patron, test_catalog_item):
    """Deleting a tag removes it from all entries."""
    await ReadingStatusService.set_status(
        test_db, test_patron.id, test_catalog_item.id,
        ShelfStatus.currently_reading,
        personal_tags=["toremove", "keep"],
    )
    count = await PatronTagsService.delete_tag(test_db, test_patron.id, "toremove")
    assert count == 1

    tags = await PatronTagsService.get_all_tags(test_db, test_patron.id)
    assert "toremove" not in tags
    assert "keep" in tags

# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Tests for ReadingMilestoneService."""

from datetime import datetime, timezone

import pytest
from app.models.catalog import CatalogItem, ItemStatus
from app.models.reading_goal import ReadingGoal
from app.models.reading_status import ShelfStatus
from app.services.reading_milestone_service import ReadingMilestoneService
from app.services.reading_status_service import ReadingStatusService


# ==================== Fixtures for new milestone types ====================


@pytest.fixture
async def catalog_item_with_genre(test_db):
    """Catalog item with subjects set for genre milestone tests."""
    item = CatalogItem(
        title="Science Fiction Novel",
        author="Genre Author",
        isbn="978-0-111111-11-1",
        subjects="Science Fiction, Adventure",
        status=ItemStatus.available,
        publication_year=2024,
    )
    test_db.add(item)
    await test_db.commit()
    await test_db.refresh(item)
    return item


@pytest.fixture
async def catalog_item_mystery(test_db):
    """Catalog item with a different genre."""
    item = CatalogItem(
        title="Mystery Thriller",
        author="Mystery Author",
        isbn="978-0-222222-22-2",
        subjects="Mystery",
        status=ItemStatus.available,
        publication_year=2024,
    )
    test_db.add(item)
    await test_db.commit()
    await test_db.refresh(item)
    return item


@pytest.fixture
async def catalog_item_no_subjects(test_db):
    """Catalog item without subjects."""
    item = CatalogItem(
        title="Book Without Genre",
        author="No Genre Author",
        isbn="978-0-333333-33-3",
        status=ItemStatus.available,
        publication_year=2024,
    )
    test_db.add(item)
    await test_db.commit()
    await test_db.refresh(item)
    return item


@pytest.fixture
async def reading_goal(test_db, test_patron):
    """Create a reading goal of 4 books for the current year."""
    goal = ReadingGoal(
        user_id=test_patron.id,
        year=datetime.now(timezone.utc).year,
        target_books=4,
    )
    test_db.add(goal)
    await test_db.commit()
    await test_db.refresh(goal)
    return goal


@pytest.mark.asyncio
async def test_first_book_finished_milestone(test_db, test_patron, test_catalog_item):
    """Finishing first book triggers books_finished_1 milestone."""
    await ReadingStatusService.set_status(
        test_db, test_patron.id, test_catalog_item.id, ShelfStatus.finished
    )
    milestones = await ReadingMilestoneService.get_milestones(test_db, test_patron.id)
    keys = [m.milestone_key for m in milestones]
    assert "books_finished_1" in keys


@pytest.mark.asyncio
async def test_no_duplicate_milestones(test_db, test_patron, test_catalog_item):
    """Same milestone is not awarded twice."""
    # First finish
    await ReadingStatusService.set_status(
        test_db, test_patron.id, test_catalog_item.id, ShelfStatus.finished
    )
    milestones_before = await ReadingMilestoneService.get_milestones(test_db, test_patron.id)

    # Try to trigger again
    milestone = await ReadingMilestoneService.check_and_award(
        test_db, test_patron.id, trigger="status_change"
    )
    assert milestone is None  # No new milestone
    milestones_after = await ReadingMilestoneService.get_milestones(test_db, test_patron.id)
    assert len(milestones_after) == len(milestones_before)


@pytest.mark.asyncio
async def test_dismiss_milestone(test_db, test_patron, test_catalog_item):
    """Dismissed milestones are hidden from default queries."""
    await ReadingStatusService.set_status(
        test_db, test_patron.id, test_catalog_item.id, ShelfStatus.finished
    )
    milestones = await ReadingMilestoneService.get_milestones(test_db, test_patron.id)
    assert len(milestones) > 0

    await ReadingMilestoneService.dismiss_milestone(
        test_db, test_patron.id, milestones[0].id
    )

    visible = await ReadingMilestoneService.get_milestones(test_db, test_patron.id)
    assert len(visible) == len(milestones) - 1

    all_milestones = await ReadingMilestoneService.get_milestones(
        test_db, test_patron.id, include_dismissed=True
    )
    assert len(all_milestones) == len(milestones)


@pytest.mark.asyncio
async def test_dismiss_nonexistent_milestone(test_db, test_patron):
    """Dismissing a nonexistent milestone returns False."""
    result = await ReadingMilestoneService.dismiss_milestone(
        test_db, test_patron.id, 99999
    )
    assert result is False


# ==================== Genre Explored Tests ====================


@pytest.mark.asyncio
async def test_genre_explored_milestone_awarded(
    test_db, test_patron, catalog_item_with_genre
):
    """Finishing a book with subjects triggers genre_explored milestone."""
    await ReadingStatusService.set_status(
        test_db, test_patron.id, catalog_item_with_genre.id, ShelfStatus.finished
    )
    milestones = await ReadingMilestoneService.get_milestones(test_db, test_patron.id)
    keys = [m.milestone_key for m in milestones]
    assert "genre_explored_adventure" in keys or "genre_explored_science-fiction" in keys


@pytest.mark.asyncio
async def test_genre_explored_slug_format(
    test_db, test_patron, catalog_item_with_genre
):
    """Genre slugs are lowercase with spaces replaced by hyphens."""
    await ReadingStatusService.set_status(
        test_db, test_patron.id, catalog_item_with_genre.id, ShelfStatus.finished
    )
    milestones = await ReadingMilestoneService.get_milestones(test_db, test_patron.id)
    keys = [m.milestone_key for m in milestones]
    genre_keys = [k for k in keys if k.startswith("genre_explored_")]
    assert len(genre_keys) >= 1
    for gk in genre_keys:
        slug = gk.replace("genre_explored_", "")
        assert slug == slug.lower()
        assert " " not in slug


@pytest.mark.asyncio
async def test_genre_explored_no_duplicate(
    test_db, test_patron, catalog_item_with_genre
):
    """Same genre milestone is not awarded twice."""
    await ReadingStatusService.set_status(
        test_db, test_patron.id, catalog_item_with_genre.id, ShelfStatus.finished
    )
    milestones_before = await ReadingMilestoneService.get_milestones(
        test_db, test_patron.id
    )
    genre_keys_before = [
        m.milestone_key
        for m in milestones_before
        if m.milestone_type == "genre_explored"
    ]

    # Trigger check again
    await ReadingMilestoneService.check_and_award(
        test_db, test_patron.id, trigger="status_change"
    )
    milestones_after = await ReadingMilestoneService.get_milestones(
        test_db, test_patron.id
    )
    genre_keys_after = [
        m.milestone_key
        for m in milestones_after
        if m.milestone_type == "genre_explored"
    ]
    assert genre_keys_after == genre_keys_before


@pytest.mark.asyncio
async def test_genre_explored_different_genres(
    test_db, test_patron, catalog_item_with_genre, catalog_item_mystery
):
    """Finishing books in different genres awards separate milestones."""
    await ReadingStatusService.set_status(
        test_db, test_patron.id, catalog_item_with_genre.id, ShelfStatus.finished
    )
    await ReadingStatusService.set_status(
        test_db, test_patron.id, catalog_item_mystery.id, ShelfStatus.finished
    )
    milestones = await ReadingMilestoneService.get_milestones(test_db, test_patron.id)
    keys = [m.milestone_key for m in milestones]
    assert "genre_explored_mystery" in keys


@pytest.mark.asyncio
async def test_genre_explored_skipped_for_no_subjects(
    test_db, test_patron, catalog_item_no_subjects
):
    """Books without subjects do not trigger genre milestones."""
    await ReadingStatusService.set_status(
        test_db, test_patron.id, catalog_item_no_subjects.id, ShelfStatus.finished
    )
    milestones = await ReadingMilestoneService.get_milestones(test_db, test_patron.id)
    genre_milestones = [m for m in milestones if m.milestone_type == "genre_explored"]
    assert len(genre_milestones) == 0


@pytest.mark.asyncio
async def test_genre_explored_title_and_description(
    test_db, test_patron, catalog_item_mystery
):
    """Genre milestone has correct title and description text."""
    await ReadingStatusService.set_status(
        test_db, test_patron.id, catalog_item_mystery.id, ShelfStatus.finished
    )
    milestones = await ReadingMilestoneService.get_milestones(test_db, test_patron.id)
    genre_ms = [m for m in milestones if m.milestone_type == "genre_explored"]
    assert len(genre_ms) == 1
    assert genre_ms[0].title == "Genre Explorer: Mystery!"
    assert "Mystery" in genre_ms[0].description


# ==================== Goal Percentage Tests ====================


@pytest.mark.asyncio
async def test_goal_25_pct_milestone(test_db, test_patron, reading_goal):
    """Finishing 1 of 4 books (25%) triggers goal_25_pct milestone."""
    item = CatalogItem(
        title="Goal Book 1", author="Author", status=ItemStatus.available
    )
    test_db.add(item)
    await test_db.commit()
    await test_db.refresh(item)

    await ReadingStatusService.set_status(
        test_db, test_patron.id, item.id, ShelfStatus.finished
    )
    milestones = await ReadingMilestoneService.get_milestones(test_db, test_patron.id)
    keys = [m.milestone_key for m in milestones]
    assert "goal_25_pct" in keys


@pytest.mark.asyncio
async def test_goal_50_pct_milestone(test_db, test_patron, reading_goal):
    """Finishing 2 of 4 books (50%) triggers goal_50_pct milestone."""
    items = []
    for i in range(2):
        item = CatalogItem(
            title=f"Goal Book {i}", author="Author", status=ItemStatus.available
        )
        test_db.add(item)
        items.append(item)
    await test_db.commit()
    for item in items:
        await test_db.refresh(item)

    for item in items:
        await ReadingStatusService.set_status(
            test_db, test_patron.id, item.id, ShelfStatus.finished
        )

    milestones = await ReadingMilestoneService.get_milestones(test_db, test_patron.id)
    keys = [m.milestone_key for m in milestones]
    assert "goal_50_pct" in keys


@pytest.mark.asyncio
async def test_goal_100_pct_milestone(test_db, test_patron, reading_goal):
    """Finishing 4 of 4 books (100%) triggers goal_100_pct milestone."""
    items = []
    for i in range(4):
        item = CatalogItem(
            title=f"Goal Book {i}", author="Author", status=ItemStatus.available
        )
        test_db.add(item)
        items.append(item)
    await test_db.commit()
    for item in items:
        await test_db.refresh(item)

    for item in items:
        await ReadingStatusService.set_status(
            test_db, test_patron.id, item.id, ShelfStatus.finished
        )

    milestones = await ReadingMilestoneService.get_milestones(test_db, test_patron.id)
    keys = [m.milestone_key for m in milestones]
    assert "goal_100_pct" in keys
    assert "goal_25_pct" in keys
    assert "goal_50_pct" in keys
    assert "goal_75_pct" in keys


@pytest.mark.asyncio
async def test_goal_milestone_not_awarded_without_goal(
    test_db, test_patron, test_catalog_item
):
    """No goal milestones when patron has no reading goal set."""
    await ReadingStatusService.set_status(
        test_db, test_patron.id, test_catalog_item.id, ShelfStatus.finished
    )
    milestones = await ReadingMilestoneService.get_milestones(test_db, test_patron.id)
    goal_milestones = [m for m in milestones if m.milestone_type == "goal_percent"]
    assert len(goal_milestones) == 0


@pytest.mark.asyncio
async def test_goal_milestone_no_duplicate(test_db, test_patron, reading_goal):
    """Goal percentage milestone is not awarded twice."""
    item = CatalogItem(
        title="Goal Dup Book", author="Author", status=ItemStatus.available
    )
    test_db.add(item)
    await test_db.commit()
    await test_db.refresh(item)

    await ReadingStatusService.set_status(
        test_db, test_patron.id, item.id, ShelfStatus.finished
    )
    milestones_before = await ReadingMilestoneService.get_milestones(
        test_db, test_patron.id
    )
    goal_keys_before = [
        m.milestone_key
        for m in milestones_before
        if m.milestone_type == "goal_percent"
    ]

    # Trigger again
    await ReadingMilestoneService.check_and_award(
        test_db, test_patron.id, trigger="status_change"
    )
    milestones_after = await ReadingMilestoneService.get_milestones(
        test_db, test_patron.id
    )
    goal_keys_after = [
        m.milestone_key
        for m in milestones_after
        if m.milestone_type == "goal_percent"
    ]
    assert goal_keys_after == goal_keys_before


@pytest.mark.asyncio
async def test_goal_milestone_title_and_description(
    test_db, test_patron, reading_goal
):
    """Goal milestone has correct title and description with year and counts."""
    item = CatalogItem(
        title="Goal Desc Book", author="Author", status=ItemStatus.available
    )
    test_db.add(item)
    await test_db.commit()
    await test_db.refresh(item)

    await ReadingStatusService.set_status(
        test_db, test_patron.id, item.id, ShelfStatus.finished
    )
    milestones = await ReadingMilestoneService.get_milestones(test_db, test_patron.id)
    goal_ms = [m for m in milestones if m.milestone_key == "goal_25_pct"]
    assert len(goal_ms) == 1
    assert "25%" in goal_ms[0].title
    current_year = datetime.now(timezone.utc).year
    assert str(current_year) in goal_ms[0].description
    assert "1/4" in goal_ms[0].description

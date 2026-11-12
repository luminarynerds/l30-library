# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Tests for ReviewService."""

import pytest
from app.services.review_service import ReviewService


@pytest.mark.asyncio
async def test_patron_rating(test_db, test_patron, test_catalog_item):
    """Patron can submit a star rating."""
    review = await ReviewService.upsert_review(
        test_db, test_patron.id, test_catalog_item.id, rating=4
    )
    assert review.rating == 4
    assert review.is_staff_review is False
    assert review.title is None
    assert review.body is None


@pytest.mark.asyncio
async def test_patron_cannot_set_body(test_db, test_patron, test_catalog_item):
    """Patron's title and body are stripped by service."""
    review = await ReviewService.upsert_review(
        test_db, test_patron.id, test_catalog_item.id,
        rating=5, title="My Title", body="My Body", is_staff=False,
    )
    assert review.title is None
    assert review.body is None


@pytest.mark.asyncio
async def test_staff_review(test_db, test_staff, test_catalog_item):
    """Staff can submit rating, title, and body."""
    review = await ReviewService.upsert_review(
        test_db, test_staff.id, test_catalog_item.id,
        rating=5, title="Excellent Read", body="A wonderful story.", is_staff=True,
    )
    assert review.rating == 5
    assert review.title == "Excellent Read"
    assert review.body == "A wonderful story."
    assert review.is_staff_review is True
    assert review.is_published is False


@pytest.mark.asyncio
async def test_publish_unpublish(test_db, test_staff, test_catalog_item):
    """Staff can publish and unpublish their review."""
    review = await ReviewService.upsert_review(
        test_db, test_staff.id, test_catalog_item.id,
        rating=4, title="Good", body="Solid.", is_staff=True,
    )
    published = await ReviewService.publish_review(test_db, review.id, test_staff.id)
    assert published.is_published is True

    unpublished = await ReviewService.unpublish_review(test_db, review.id, test_staff.id)
    assert unpublished.is_published is False


@pytest.mark.asyncio
async def test_upsert_updates_existing(test_db, test_patron, test_catalog_item):
    """Upserting updates existing rating instead of creating duplicate."""
    await ReviewService.upsert_review(
        test_db, test_patron.id, test_catalog_item.id, rating=3
    )
    review = await ReviewService.upsert_review(
        test_db, test_patron.id, test_catalog_item.id, rating=5
    )
    assert review.rating == 5

    reviews = await ReviewService.get_user_reviews(test_db, test_patron.id)
    assert len(reviews) == 1


@pytest.mark.asyncio
async def test_delete_review(test_db, test_patron, test_catalog_item):
    """Deleting a review removes it."""
    await ReviewService.upsert_review(
        test_db, test_patron.id, test_catalog_item.id, rating=4
    )
    deleted = await ReviewService.delete_review(test_db, test_patron.id, test_catalog_item.id)
    assert deleted is True

    reviews = await ReviewService.get_user_reviews(test_db, test_patron.id)
    assert len(reviews) == 0


@pytest.mark.asyncio
async def test_aggregate_rating(test_db, test_patron, test_staff, test_catalog_item):
    """Aggregate includes all ratings (patron + staff)."""
    await ReviewService.upsert_review(
        test_db, test_patron.id, test_catalog_item.id, rating=4
    )
    await ReviewService.upsert_review(
        test_db, test_staff.id, test_catalog_item.id,
        rating=5, title="Great", body="Love it", is_staff=True,
    )
    agg = await ReviewService.get_aggregate_rating(test_db, test_catalog_item.id)
    assert agg["average_rating"] == 4.5
    assert agg["rating_count"] == 2


@pytest.mark.asyncio
async def test_get_item_reviews_with_user_rating(test_db, test_patron, test_staff, test_catalog_item):
    """get_item_reviews returns staff reviews, aggregate, and current user's rating."""
    await ReviewService.upsert_review(
        test_db, test_patron.id, test_catalog_item.id, rating=3
    )
    review = await ReviewService.upsert_review(
        test_db, test_staff.id, test_catalog_item.id,
        rating=5, title="Must Read", body="Incredible.", is_staff=True,
    )
    await ReviewService.publish_review(test_db, review.id, test_staff.id)

    data = await ReviewService.get_item_reviews(
        test_db, test_catalog_item.id, current_user_id=test_patron.id
    )
    assert data["user_rating"] == 3
    assert data["aggregate"]["rating_count"] == 2
    assert len(data["staff_reviews"]) == 1


@pytest.mark.asyncio
async def test_no_rating_no_body_raises(test_db, test_patron, test_catalog_item):
    """Must provide at least rating or body."""
    with pytest.raises(ValueError, match="Rating or review body required"):
        await ReviewService.upsert_review(
            test_db, test_patron.id, test_catalog_item.id
        )


@pytest.mark.asyncio
async def test_invalid_catalog_item(test_db, test_patron):
    """Rating nonexistent item raises ValueError."""
    with pytest.raises(ValueError, match="Catalog item not found"):
        await ReviewService.upsert_review(
            test_db, test_patron.id, 99999, rating=4
        )

# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Reviews API endpoints — staff reviews and patron ratings."""

from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.database import get_db
from ...models.user import User, UserRole
from ...schemas.reviews import (
    CatalogItemReviewsResponse,
    ReviewResponse,
    ReviewUpsert,
)
from ...services.review_service import ReviewService
from .auth import get_current_user, get_optional_user

router = APIRouter(tags=["reviews"])


@router.put("/reviews/{catalog_item_id}", response_model=ReviewResponse)
async def upsert_review(
    catalog_item_id: int,
    data: ReviewUpsert,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create or update a rating/review for a catalog item.

    Patrons: can set rating only (title/body ignored).
    Staff: can set rating, title, and body.
    """
    is_staff = current_user.role in (UserRole.STAFF, UserRole.ADMIN)
    try:
        review = await ReviewService.upsert_review(
            db, current_user.id, catalog_item_id,
            rating=data.rating, title=data.title, body=data.body, is_staff=is_staff,
        )
        return review
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.delete("/reviews/{catalog_item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_review(
    catalog_item_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Remove own rating/review for a catalog item."""
    deleted = await ReviewService.delete_review(db, current_user.id, catalog_item_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Review not found")


@router.get("/reviews/catalog-item/{catalog_item_id}", response_model=CatalogItemReviewsResponse)
async def get_catalog_item_reviews(
    catalog_item_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_optional_user),
):
    """Get staff reviews and aggregate rating for a catalog item (public)."""
    user_id = current_user.id if current_user else None
    data = await ReviewService.get_item_reviews(db, catalog_item_id, current_user_id=user_id)

    # Enrich staff reviews with reviewer names
    enriched_reviews = []
    for review in data["staff_reviews"]:
        enriched = ReviewResponse.model_validate(review)
        if review.user:
            enriched.reviewer_name = f"{review.user.first_name} {review.user.last_name}"
        enriched_reviews.append(enriched)

    return CatalogItemReviewsResponse(
        aggregate=data["aggregate"],
        staff_reviews=enriched_reviews,
        user_rating=data["user_rating"],
    )


@router.get("/reviews/me", response_model=List[ReviewResponse])
async def get_my_reviews(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get current user's ratings and reviews."""
    return await ReviewService.get_user_reviews(db, current_user.id, limit, offset)


@router.get("/reviews/staff", response_model=List[ReviewResponse])
async def get_all_staff_reviews(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """Browse all published staff reviews (public)."""
    reviews = await ReviewService.get_staff_reviews(db, limit, offset)
    enriched = []
    for review in reviews:
        r = ReviewResponse.model_validate(review)
        if review.user:
            r.reviewer_name = f"{review.user.first_name} {review.user.last_name}"
        enriched.append(r)
    return enriched


@router.post("/reviews/{review_id}/publish", response_model=ReviewResponse)
async def publish_review(
    review_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Publish a staff review (staff only)."""
    if current_user.role not in (UserRole.STAFF, UserRole.ADMIN, UserRole.SUPER_ADMIN, UserRole.DIRECTOR):
        raise HTTPException(status_code=403, detail="Staff only")
    try:
        return await ReviewService.publish_review(db, review_id, current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.post("/reviews/{review_id}/unpublish", response_model=ReviewResponse)
async def unpublish_review(
    review_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Unpublish a staff review (staff only)."""
    if current_user.role not in (UserRole.STAFF, UserRole.ADMIN, UserRole.SUPER_ADMIN, UserRole.DIRECTOR):
        raise HTTPException(status_code=403, detail="Staff only")
    try:
        return await ReviewService.unpublish_review(db, review_id, current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e

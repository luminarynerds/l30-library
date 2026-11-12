# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..models.catalog import CatalogItem
from ..models.review import Review
from ..models.user import User, UserRole


class ReviewService:

    @staticmethod
    async def upsert_review(
        db: AsyncSession,
        user_id: int,
        catalog_item_id: int,
        rating: Optional[int] = None,
        title: Optional[str] = None,
        body: Optional[str] = None,
        is_staff: bool = False,
    ) -> Review:
        # Check catalog item exists
        item = await db.execute(
            select(CatalogItem).where(CatalogItem.id == catalog_item_id)
        )
        if not item.scalar_one_or_none():
            raise ValueError("Catalog item not found")

        # Enforce: non-staff cannot set title/body
        if not is_staff:
            title = None
            body = None

        # Must have at least rating or body
        if rating is None and not body:
            raise ValueError("Rating or review body required")

        result = await db.execute(
            select(Review).where(
                Review.user_id == user_id,
                Review.catalog_item_id == catalog_item_id,
            )
        )
        review = result.scalar_one_or_none()

        if review:
            if rating is not None:
                review.rating = rating
            if is_staff:
                if title is not None:
                    review.title = title
                if body is not None:
                    review.body = body
        else:
            review = Review(
                user_id=user_id,
                catalog_item_id=catalog_item_id,
                rating=rating,
                title=title,
                body=body,
                is_staff_review=is_staff,
                is_published=False,
            )
            db.add(review)

        await db.commit()
        await db.refresh(review)

        result = await db.execute(
            select(Review)
            .options(selectinload(Review.catalog_item))
            .where(Review.id == review.id)
        )
        return result.scalar_one()

    @staticmethod
    async def publish_review(db: AsyncSession, review_id: int, user_id: int) -> Review:
        result = await db.execute(
            select(Review).where(
                Review.id == review_id,
                Review.user_id == user_id,
                Review.is_staff_review == True,
            )
        )
        review = result.scalar_one_or_none()
        if not review:
            raise ValueError("Staff review not found")
        review.is_published = True
        await db.commit()
        refreshed = await db.execute(
            select(Review)
            .options(selectinload(Review.catalog_item))
            .where(Review.id == review_id)
        )
        return refreshed.scalar_one()

    @staticmethod
    async def unpublish_review(db: AsyncSession, review_id: int, user_id: int) -> Review:
        result = await db.execute(
            select(Review).where(
                Review.id == review_id,
                Review.user_id == user_id,
                Review.is_staff_review == True,
            )
        )
        review = result.scalar_one_or_none()
        if not review:
            raise ValueError("Staff review not found")
        review.is_published = False
        await db.commit()
        refreshed = await db.execute(
            select(Review)
            .options(selectinload(Review.catalog_item))
            .where(Review.id == review_id)
        )
        return refreshed.scalar_one()

    @staticmethod
    async def delete_review(db: AsyncSession, user_id: int, catalog_item_id: int) -> bool:
        result = await db.execute(
            select(Review).where(
                Review.user_id == user_id,
                Review.catalog_item_id == catalog_item_id,
            )
        )
        review = result.scalar_one_or_none()
        if not review:
            return False
        await db.delete(review)
        await db.commit()
        return True

    @staticmethod
    async def get_item_reviews(
        db: AsyncSession,
        catalog_item_id: int,
        current_user_id: Optional[int] = None,
    ) -> dict:
        # Aggregate rating (all ratings, not just staff)
        agg = await db.execute(
            select(
                func.avg(Review.rating).label("avg"),
                func.count(Review.rating).label("cnt"),
            ).where(
                Review.catalog_item_id == catalog_item_id,
                Review.rating.isnot(None),
            )
        )
        row = agg.one()
        aggregate = {
            "average_rating": round(float(row.avg), 1) if row.avg else None,
            "rating_count": row.cnt or 0,
        }

        # Published staff reviews
        result = await db.execute(
            select(Review)
            .options(selectinload(Review.user), selectinload(Review.catalog_item))
            .where(
                Review.catalog_item_id == catalog_item_id,
                Review.is_staff_review == True,
                Review.is_published == True,
            )
            .order_by(Review.created_at.desc())
        )
        staff_reviews = result.scalars().all()

        # Current user's rating
        user_rating = None
        if current_user_id:
            result = await db.execute(
                select(Review.rating).where(
                    Review.catalog_item_id == catalog_item_id,
                    Review.user_id == current_user_id,
                )
            )
            r = result.scalar_one_or_none()
            if r is not None:
                user_rating = r

        return {
            "aggregate": aggregate,
            "staff_reviews": staff_reviews,
            "user_rating": user_rating,
        }

    @staticmethod
    async def get_user_reviews(
        db: AsyncSession, user_id: int, limit: int = 50, offset: int = 0
    ) -> list[Review]:
        result = await db.execute(
            select(Review)
            .options(selectinload(Review.catalog_item))
            .where(Review.user_id == user_id)
            .order_by(Review.updated_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())

    @staticmethod
    async def get_staff_reviews(
        db: AsyncSession, limit: int = 50, offset: int = 0
    ) -> list[Review]:
        result = await db.execute(
            select(Review)
            .options(selectinload(Review.catalog_item), selectinload(Review.user))
            .where(
                Review.is_staff_review == True,
                Review.is_published == True,
            )
            .order_by(Review.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())

    @staticmethod
    async def get_aggregate_rating(db: AsyncSession, catalog_item_id: int) -> dict:
        agg = await db.execute(
            select(
                func.avg(Review.rating).label("avg"),
                func.count(Review.rating).label("cnt"),
            ).where(
                Review.catalog_item_id == catalog_item_id,
                Review.rating.isnot(None),
            )
        )
        row = agg.one()
        return {
            "average_rating": round(float(row.avg), 1) if row.avg else None,
            "rating_count": row.cnt or 0,
        }

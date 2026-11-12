# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
import asyncio
from app.core.logging import get_logger
import secrets
from datetime import datetime, timezone, timedelta
from typing import Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..models.indie_ebook_borrow import (
    IndieEbook, IndieEbookBorrow, IndieEbookWaitlist, BorrowStatus,
    MetisLibSyncState,
)

logger = get_logger(__name__)

MAX_CONCURRENT_BORROWS = 5
DEFAULT_BORROW_DAYS = 21


class IndieLendingService:

    async def borrow_ebook(
        self,
        ebook_id: int,
        user_id: int,
        db: AsyncSession,
    ) -> IndieEbookBorrow:
        # Verify ebook exists
        ebook = await db.get(IndieEbook, ebook_id)
        if not ebook:
            raise ValueError("Ebook not found")

        # Check concurrent borrow limit
        active_count_result = await db.execute(
            select(func.count()).where(
                IndieEbookBorrow.user_id == user_id,
                IndieEbookBorrow.status == BorrowStatus.active,
            )
        )
        if active_count_result.scalar() >= MAX_CONCURRENT_BORROWS:
            raise ValueError(f"You can only borrow up to {MAX_CONCURRENT_BORROWS} indie ebooks at a time")

        # Check if already borrowing this ebook
        existing = await db.execute(
            select(IndieEbookBorrow).where(
                IndieEbookBorrow.ebook_id == ebook_id,
                IndieEbookBorrow.user_id == user_id,
                IndieEbookBorrow.status == BorrowStatus.active,
            )
        )
        if existing.scalar_one_or_none():
            raise ValueError("You have already borrowed this ebook")

        borrow = IndieEbookBorrow(
            ebook_id=ebook_id,
            user_id=user_id,
            due_at=datetime.now(timezone.utc) + timedelta(days=DEFAULT_BORROW_DAYS),
            access_token=secrets.token_urlsafe(32),
            status=BorrowStatus.active,
        )
        db.add(borrow)
        await db.flush()

        # Mirror to MetisLib. Best-effort for the patron (a MetisLib outage must
        # not block the local borrow) but NO LONGER silent: record the outcome so
        # the reconcile job can retry and circulation analytics stay accurate.
        if ebook.metislib_ebook_id:
            try:
                from .metislib_client import get_metislib_client
                from ..utils.patron_hash import generate_patron_hash
                client = get_metislib_client()
                result = await client.borrow_indie(ebook.metislib_ebook_id, generate_patron_hash(user_id))
                metislib_borrow_id = result.get("borrow_id")
                if metislib_borrow_id:
                    borrow.metislib_borrow_id = metislib_borrow_id
                    borrow.metislib_sync_state = MetisLibSyncState.synced
                else:
                    borrow.metislib_sync_state = MetisLibSyncState.borrow_failed
                    logger.warning("MetisLib borrow returned no borrow_id for ebook %s", ebook.metislib_ebook_id)
            except Exception as e:  # noqa: BLE001 - external integration boundary — MetisLib failure must not block local borrow
                borrow.metislib_sync_state = MetisLibSyncState.borrow_failed
                logger.warning("Failed to notify MetisLib of indie borrow: %s", e)
        else:
            borrow.metislib_sync_state = MetisLibSyncState.not_required

        await db.commit()
        await db.refresh(borrow)
        return borrow

    async def return_ebook(
        self,
        borrow: IndieEbookBorrow,
        rating: Optional[int],
        db: AsyncSession,
        *,
        review_text: Optional[str] = None,
    ) -> IndieEbookBorrow:
        if borrow.status != BorrowStatus.active:
            raise ValueError("This borrow is not active")

        borrow.status = BorrowStatus.returned
        borrow.returned_at = datetime.now(timezone.utc)
        if rating is not None:
            borrow.rating = rating
        if review_text is not None:
            borrow.review_text = review_text
        if rating is not None or review_text is not None:
            borrow.review_submitted_at = datetime.now(timezone.utc)

        # Mirror the return to MetisLib (best-effort, outcome recorded; see borrow).
        if borrow.metislib_borrow_id:
            try:
                from .metislib_client import get_metislib_client
                from ..utils.patron_hash import generate_patron_hash
                client = get_metislib_client()
                await client.return_indie(borrow.metislib_borrow_id, generate_patron_hash(borrow.user_id))
                borrow.metislib_sync_state = MetisLibSyncState.synced
            except Exception as e:  # noqa: BLE001 - external integration boundary — MetisLib failure must not block local return
                borrow.metislib_sync_state = MetisLibSyncState.return_failed
                logger.warning("Failed to notify MetisLib of indie return: %s", e)

        await db.commit()
        await db.refresh(borrow)
        return borrow

    async def get_ebook_reviews(self, ebook_id: int, db: AsyncSession) -> list[dict]:
        result = await db.execute(
            select(IndieEbookBorrow)
            .options(selectinload(IndieEbookBorrow.user))
            .where(
                IndieEbookBorrow.ebook_id == ebook_id,
                IndieEbookBorrow.rating.isnot(None),
                IndieEbookBorrow.review_submitted_at.isnot(None),
            )
            .order_by(IndieEbookBorrow.review_submitted_at.desc())
            .limit(50)
        )
        borrows = result.scalars().all()
        reviews = []
        for b in borrows:
            name = "A Reader"
            if b.user:
                name = getattr(b.user, 'display_name', None) or b.user.email.split("@")[0]
            reviews.append({
                "id": b.id,
                "rating": b.rating,
                "review_text": b.review_text,
                "reviewer_name": name,
                "created_at": b.review_submitted_at.isoformat(),
            })
        return reviews

    async def submit_review(
        self,
        borrow: IndieEbookBorrow,
        rating: int,
        review_text: Optional[str],
        db: AsyncSession,
    ) -> IndieEbookBorrow:
        if borrow.status not in (BorrowStatus.returned, BorrowStatus.expired):
            raise ValueError("You can only review books you have returned")

        if rating < 1 or rating > 5:
            raise ValueError("Rating must be between 1 and 5")

        borrow.rating = rating
        borrow.review_text = review_text
        borrow.review_submitted_at = datetime.now(timezone.utc)
        await db.commit()
        await db.refresh(borrow)
        return borrow

    async def get_active_borrows(self, user_id: int, db: AsyncSession) -> list[dict]:
        result = await db.execute(
            select(IndieEbookBorrow)
            .options(selectinload(IndieEbookBorrow.ebook))
            .where(
                IndieEbookBorrow.user_id == user_id,
                IndieEbookBorrow.status == BorrowStatus.active,
            )
            .order_by(IndieEbookBorrow.due_at.asc())
        )
        borrows = result.scalars().all()
        if not borrows:
            return []

        # Batch-fetch metadata from MetisLib
        metislib_ids = {b.ebook.metislib_ebook_id for b in borrows if b.ebook.metislib_ebook_id}
        metadata_map: dict[int, dict] = {}
        if metislib_ids:
            try:
                from .metislib_client import get_metislib_client
                client = get_metislib_client()
                tasks = {mid: client.get_ebook(mid, entry_type="indie_ebook") for mid in metislib_ids}
                results = await asyncio.gather(*tasks.values(), return_exceptions=True)
                for mid, res in zip(tasks.keys(), results):
                    if isinstance(res, dict):
                        metadata_map[mid] = res
            except Exception as e:  # noqa: BLE001 - external integration boundary — MetisLib metadata failure must not block borrow listing
                logger.warning("Failed to fetch MetisLib metadata for borrows: %s", e)

        # Build response
        items = []
        for b in borrows:
            meta = metadata_map.get(b.ebook.metislib_ebook_id, {}) if b.ebook.metislib_ebook_id else {}
            items.append({
                "id": b.id,
                "ebook_id": b.ebook.metislib_ebook_id or b.ebook_id,
                "indie_ebook_id": b.ebook_id,
                "ebook_title": meta.get("title", "Unavailable"),
                "ebook_cover_url": meta.get("cover_url"),
                "author_pen_name": meta.get("author_name", "Unknown"),
                "borrowed_at": b.borrowed_at.isoformat(),
                "due_at": b.due_at.isoformat(),
                "status": b.status.value if isinstance(b.status, BorrowStatus) else b.status,
                "download_count": b.download_count,
                "max_downloads": b.max_downloads,
            })
        return items

    async def join_waitlist(self, ebook_id: int, user_id: int, db: AsyncSession) -> IndieEbookWaitlist:
        # Check not already on waitlist
        existing = await db.execute(
            select(IndieEbookWaitlist).where(
                IndieEbookWaitlist.ebook_id == ebook_id,
                IndieEbookWaitlist.user_id == user_id,
            )
        )
        if existing.scalar_one_or_none():
            raise ValueError("Already on waitlist")

        max_pos_result = await db.execute(
            select(func.max(IndieEbookWaitlist.position)).where(
                IndieEbookWaitlist.ebook_id == ebook_id,
            )
        )
        max_pos = max_pos_result.scalar() or 0

        entry = IndieEbookWaitlist(
            ebook_id=ebook_id,
            user_id=user_id,
            position=max_pos + 1,
        )
        db.add(entry)
        await db.commit()
        await db.refresh(entry)
        return entry

    async def expire_overdue_borrows(self, db: AsyncSession) -> int:
        result = await db.execute(
            select(IndieEbookBorrow).where(
                IndieEbookBorrow.status == BorrowStatus.active,
                IndieEbookBorrow.due_at < datetime.now(timezone.utc),
            )
        )
        overdue = result.scalars().all()
        for borrow in overdue:
            borrow.status = BorrowStatus.expired
        if overdue:
            await db.commit()
            logger.info("Expired %d overdue indie ebook borrows", len(overdue))
        return len(overdue)


_service: IndieLendingService | None = None


def get_lending_service() -> IndieLendingService:
    global _service
    if _service is None:
        _service = IndieLendingService()
    return _service

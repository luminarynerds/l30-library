# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
from app.core.logging import get_logger
from sqlalchemy import func, select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.indie_ebook_borrow import IndieEbookBorrow

logger = get_logger(__name__)


async def get_recommendations_by_borrow_overlap(
    ebook_id: int,
    limit: int,
    db: AsyncSession,
) -> list[dict]:
    borrowers_stmt = (
        select(IndieEbookBorrow.user_id)
        .where(IndieEbookBorrow.ebook_id == ebook_id)
        .distinct()
    )

    co_borrowed_stmt = (
        select(
            IndieEbookBorrow.ebook_id,
            func.count(IndieEbookBorrow.user_id.distinct()).label("co_borrow_count"),
        )
        .where(
            and_(
                IndieEbookBorrow.user_id.in_(borrowers_stmt),
                IndieEbookBorrow.ebook_id != ebook_id,
            )
        )
        .group_by(IndieEbookBorrow.ebook_id)
        .order_by(func.count(IndieEbookBorrow.user_id.distinct()).desc())
        .limit(limit)
    )

    result = await db.execute(co_borrowed_stmt)
    rows = result.all()

    if not rows:
        return []

    max_count = rows[0].co_borrow_count if rows else 1
    return [
        {
            "ebook_id": row.ebook_id,
            "score": round(row.co_borrow_count / max_count, 2),
            "reason": "borrow_overlap",
        }
        for row in rows
    ]

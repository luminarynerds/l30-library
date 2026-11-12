# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from app.core.logging import get_logger
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from ...models.legal import (
    LegalContentAuditLog, LegalSearchLog, LegalResourceStatistics
)

logger = get_logger(__name__)


async def log_content_change(
    db: AsyncSession,
    content_type: str,
    content_id: int,
    action: str,
    changes: Optional[dict],
    user_id: Optional[int]
) -> None:
    log = LegalContentAuditLog(
        content_type=content_type,
        content_id=content_id,
        action=action,
        changes=changes,
        user_id=user_id
    )
    db.add(log)
    await db.commit()


async def log_search(
    db: AsyncSession,
    query: str,
    search_type: str,
    filters: dict
) -> None:
    log = LegalSearchLog(
        query=query,
        query_normalized=query.lower().strip(),
        search_type=search_type,
        filters_used=filters
    )
    db.add(log)
    await db.commit()


async def get_resource_statistics(
    db: AsyncSession,
    period_start,
    period_end,
    resource_type: Optional[str] = None
) -> list[LegalResourceStatistics]:
    from sqlalchemy import select

    query = select(LegalResourceStatistics).where(
        LegalResourceStatistics.period_date >= period_start,
        LegalResourceStatistics.period_date <= period_end
    )

    if resource_type:
        query = query.where(LegalResourceStatistics.resource_type == resource_type)

    query = query.order_by(LegalResourceStatistics.period_date)
    result = await db.execute(query)
    return result.scalars().all()


async def get_top_searches(
    db: AsyncSession,
    days: int = 30,
    limit: int = 20
) -> list[dict]:
    from datetime import timedelta
    from sqlalchemy import func, select

    since = datetime.now(timezone.utc) - timedelta(days=days)

    result = await db.execute(
        select(
            LegalSearchLog.query_normalized,
            func.count(LegalSearchLog.id).label("count")
        )
        .where(LegalSearchLog.searched_at >= since)
        .group_by(LegalSearchLog.query_normalized)
        .order_by(func.count(LegalSearchLog.id).desc())
        .limit(limit)
    )

    return [{"query": row[0], "count": row[1]} for row in result.all()]


async def get_zero_result_searches(
    db: AsyncSession,
    days: int = 30,
    limit: int = 20
) -> list[dict]:
    from datetime import timedelta
    from sqlalchemy import func, select

    since = datetime.now(timezone.utc) - timedelta(days=days)

    result = await db.execute(
        select(
            LegalSearchLog.query_normalized,
            func.count(LegalSearchLog.id).label("count")
        )
        .where(
            LegalSearchLog.searched_at >= since,
            LegalSearchLog.result_count == 0
        )
        .group_by(LegalSearchLog.query_normalized)
        .order_by(func.count(LegalSearchLog.id).desc())
        .limit(limit)
    )

    return [{"query": row[0], "count": row[1]} for row in result.all()]

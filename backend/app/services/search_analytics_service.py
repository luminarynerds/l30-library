# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from __future__ import annotations

from app.core.logging import get_logger
from datetime import datetime, timedelta, timezone

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.search_analytics import SearchClickLog, SearchQueryLog

logger = get_logger(__name__)


def normalize_query(query: str) -> str:
    return " ".join((query or "").lower().split())


async def log_query(
    db: AsyncSession,
    *,
    query: str,
    result_count: int,
    user_id: int | None,
) -> None:
    try:
        normalized = normalize_query(query)
        if not normalized:
            return
        db.add(
            SearchQueryLog(
                query=query[:500],
                normalized_query=normalized[:500],
                result_count=result_count,
                user_id=user_id,
            )
        )
        await db.flush()
    except SQLAlchemyError:
        logger.debug("Failed to log search query", exc_info=True)


async def log_click(
    db: AsyncSession,
    *,
    query: str,
    result_id: str,
    entity_type: str,
    position: int,
    user_id: int | None,
) -> None:
    try:
        normalized = normalize_query(query)
        if not normalized:
            return
        db.add(
            SearchClickLog(
                normalized_query=normalized[:500],
                result_id=result_id[:120],
                entity_type=entity_type[:40],
                position=position,
                user_id=user_id,
            )
        )
        await db.flush()
    except SQLAlchemyError:
        logger.debug("Failed to log search click", exc_info=True)


async def trending_queries(
    db: AsyncSession,
    *,
    limit: int = 10,
    days: int = 7,
) -> list[dict]:
    since = datetime.now(timezone.utc) - timedelta(days=days)
    try:
        stmt = text(
            """
            SELECT normalized_query AS q,
                   COUNT(*) AS n,
                   AVG(result_count) AS avg_results
            FROM search_query_log
            WHERE created_at >= :since
              AND result_count > 0
            GROUP BY normalized_query
            HAVING COUNT(*) >= 2
            ORDER BY n DESC
            LIMIT :limit
            """
        )
        rows = (await db.execute(stmt, {"since": since, "limit": limit})).all()
        return [{"query": r.q, "count": int(r.n), "avg_results": int(r.avg_results or 0)} for r in rows]
    except SQLAlchemyError:
        logger.debug("trending_queries failed", exc_info=True)
        return []


async def did_you_mean(db: AsyncSession, query: str, *, threshold: float = 0.4) -> str | None:
    normalized = normalize_query(query)
    if not normalized or len(normalized) < 3:
        return None
    try:
        stmt = text(
            """
            SELECT normalized_query AS q,
                   COUNT(*) AS n,
                   similarity(normalized_query, :q) AS sim
            FROM search_query_log
            WHERE result_count > 0
              AND normalized_query <> :q
              AND similarity(normalized_query, :q) >= :threshold
            GROUP BY normalized_query
            ORDER BY sim DESC, n DESC
            LIMIT 1
            """
        )
        row = (await db.execute(stmt, {"q": normalized, "threshold": threshold})).first()
        return row.q if row else None
    except SQLAlchemyError:
        logger.debug("did_you_mean failed (likely non-postgres or pg_trgm missing)", exc_info=True)
        return None


async def ctr_boosts_for_query(
    db: AsyncSession,
    query: str,
    *,
    limit: int = 100,
) -> dict[str, float]:
    normalized = normalize_query(query)
    if not normalized:
        return {}
    try:
        stmt = text(
            """
            SELECT result_id, COUNT(*) AS clicks
            FROM search_click_log
            WHERE normalized_query = :q
            GROUP BY result_id
            ORDER BY clicks DESC
            LIMIT :limit
            """
        )
        rows = (await db.execute(stmt, {"q": normalized, "limit": limit})).all()
    except SQLAlchemyError:
        logger.debug("ctr_boosts_for_query failed", exc_info=True)
        return {}

    import math

    boosts: dict[str, float] = {}
    for row in rows:
        boost = min(0.5, math.log1p(int(row.clicks)) * 0.1)
        boosts[row.result_id] = boost
    return boosts

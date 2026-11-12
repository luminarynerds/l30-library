# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from __future__ import annotations

import contextlib
from app.core.logging import get_logger
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from sqlalchemy import case, func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.database import AsyncSessionLocal
from ..models.catalog_demand_signal import CatalogDemandSignal

logger = get_logger(__name__)


def _normalize_isbn(raw: Optional[str]) -> Optional[str]:
    if not raw:
        return None
    cleaned = "".join(ch for ch in raw if ch.isdigit() or ch.upper() == "X")
    return cleaned.upper() or None


def _normalize_title(raw: Optional[str]) -> Optional[str]:
    if not raw:
        return None
    return " ".join(raw.strip().split())[:500] or None


async def record_signal(
    db: AsyncSession,
    *,
    signal_type: str,
    query_text: Optional[str] = None,
    normalized_title: Optional[str] = None,
    normalized_isbn: Optional[str] = None,
    normalized_subject: Optional[str] = None,
    patron_id: Optional[int] = None,
    metadata: Optional[dict[str, Any]] = None,
) -> None:
    try:
        row = CatalogDemandSignal(
            signal_type=signal_type,
            query_text=query_text[:8192] if query_text else None,
            normalized_title=_normalize_title(normalized_title),
            normalized_isbn=_normalize_isbn(normalized_isbn),
            normalized_subject=normalized_subject,
            patron_id=patron_id,
            metadata_=metadata or {},
        )
        db.add(row)
        await db.commit()
    except Exception:  # noqa: BLE001 -- fail-open: telemetry write must never break the caller's request
        logger.warning("demand_signal.record_failed", exc_info=True)
        with contextlib.suppress(Exception):  # noqa: BLE001
            await db.rollback()


async def record_signal_detached(
    *,
    signal_type: str,
    query_text: Optional[str] = None,
    normalized_title: Optional[str] = None,
    normalized_isbn: Optional[str] = None,
    normalized_subject: Optional[str] = None,
    patron_id: Optional[int] = None,
    metadata: Optional[dict[str, Any]] = None,
) -> None:
    try:
        async with AsyncSessionLocal() as session:
            await record_signal(
                session,
                signal_type=signal_type,
                query_text=query_text,
                normalized_title=normalized_title,
                normalized_isbn=normalized_isbn,
                normalized_subject=normalized_subject,
                patron_id=patron_id,
                metadata=metadata,
            )
    except SQLAlchemyError:  # pragma: no cover -- defensive
        logger.warning("demand_signal.detached_record_failed", exc_info=True)


async def get_top_demand(
    db: AsyncSession,
    *,
    days: int = 30,
    limit: int = 50,
    signal_type: Optional[str] = None,
) -> list[dict[str, Any]]:
    days = max(1, min(days, 365))
    limit = max(1, min(limit, 200))

    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    recent_cutoff = datetime.now(timezone.utc) - timedelta(days=7)

    group_key = func.coalesce(
        CatalogDemandSignal.normalized_isbn,
        CatalogDemandSignal.normalized_title,
    ).label("group_key")

    # Recency weighting: a signal inside the last 7 days counts double.
    weight = func.sum(
        case(
            (CatalogDemandSignal.recorded_at >= recent_cutoff, 2.0),
            else_=1.0,
        )
    ).label("weighted_count")

    stmt = (
        select(
            group_key,
            CatalogDemandSignal.signal_type,
            func.max(CatalogDemandSignal.normalized_isbn).label("normalized_isbn"),
            func.max(CatalogDemandSignal.normalized_title).label("normalized_title"),
            func.count().label("count"),
            weight,
            func.max(CatalogDemandSignal.recorded_at).label("most_recent"),
        )
        .where(CatalogDemandSignal.recorded_at >= cutoff)
        .where(group_key.isnot(None))
        .group_by(group_key, CatalogDemandSignal.signal_type)
        .order_by(weight.desc())
        .limit(limit)
    )
    if signal_type:
        stmt = stmt.where(CatalogDemandSignal.signal_type == signal_type)

    result = await db.execute(stmt)
    rows = result.all()
    return [
        {
            "key": r.group_key,
            "normalized_isbn": r.normalized_isbn,
            "normalized_title": r.normalized_title,
            "signal_type": r.signal_type,
            "count": int(r.count),
            "weighted_count": float(r.weighted_count),
            "most_recent": (
                r.most_recent.isoformat() if r.most_recent else None
            ),
        }
        for r in rows
    ]

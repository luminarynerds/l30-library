# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Site-wide search API - unified search across L30 catalog and MetisLib ebooks."""

from app.core.logging import get_logger
from typing import Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.database import get_db
from ...services import search_analytics_service as analytics
from ...services.site_search_service import get_site_search_service

logger = get_logger(__name__)

router = APIRouter(tags=["search"])


def _split_csv(value: Optional[str]) -> Optional[list[str]]:
    if not value:
        return None
    parts = [p.strip() for p in value.split(",") if p.strip()]
    return parts or None


@router.get("/search")
async def site_search(
    q: str = Query(..., min_length=1, max_length=200, description="Search query"),
    page: int = Query(1, ge=1, description="Page number (ignored if cursor supplied)"),
    per_page: int = Query(20, ge=1, le=100, description="Results per page"),
    cursor: Optional[str] = Query(None, description="Opaque cursor for keyset pagination"),
    entity_types: Optional[str] = Query(
        None,
        description="Comma-separated entity types to include (catalog,ebook,event,announcement,page)",
    ),
    db: AsyncSession = Depends(get_db),
):
    """Unified site search - returns results from catalog, ebooks, events, and announcements."""
    service = get_site_search_service(db)
    response = await service.search(
        q,
        page=page,
        per_page=per_page,
        cursor=cursor,
        entity_types=_split_csv(entity_types),
    )
    return response.to_dict()


class SearchClickPayload(BaseModel):
    query: str = Field(..., min_length=1, max_length=500)
    result_id: str = Field(..., min_length=1, max_length=120)
    entity_type: str = Field(..., min_length=1, max_length=40)
    position: int = Field(0, ge=0, le=10000)


@router.post("/search/click", status_code=204)
async def log_search_click(
    payload: SearchClickPayload,
    db: AsyncSession = Depends(get_db),
):
    """Record a result-click for CTR-based re-ranking."""
    await analytics.log_click(
        db,
        query=payload.query,
        result_id=payload.result_id,
        entity_type=payload.entity_type,
        position=payload.position,
        user_id=None,
    )
    return None


@router.get("/search/trending")
async def trending(
    limit: int = Query(10, ge=1, le=50),
    days: int = Query(7, ge=1, le=90),
    db: AsyncSession = Depends(get_db),
):
    """Most-frequent successful queries over the last N days."""
    return {"queries": await analytics.trending_queries(db, limit=limit, days=days)}


@router.get("/search/suggest")
async def suggest(
    q: str = Query(..., min_length=1, max_length=200),
    db: AsyncSession = Depends(get_db),
):
    """Trigram-based 'did you mean' suggestion against past popular queries."""
    suggestion = await analytics.did_you_mean(db, q)
    return {"query": q, "suggestion": suggestion}

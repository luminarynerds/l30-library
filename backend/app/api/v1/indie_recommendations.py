# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Indie ebook recommendation endpoints."""
from app.core.logging import get_logger

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.database import get_db
from ...services.indie_recommendation_service import get_recommendations_by_borrow_overlap
from ...services.metislib_client import get_metislib_client
from ...services.metislib_errors import MetisLibUnavailable

logger = get_logger(__name__)

router = APIRouter(prefix="/indie/books", tags=["indie-recommendations"])


class RecommendationItem(BaseModel):
    ebook_id: int
    title: str
    author_pen_name: str
    cover_url: str | None
    genre: str | None
    average_rating: float | None
    score: float
    reason: str


class RecommendationsResponse(BaseModel):
    items: list[RecommendationItem]
    algorithm: str


@router.get("/{ebook_id}/recommendations", response_model=RecommendationsResponse)
async def get_recommendations(
    ebook_id: int,
    limit: int = Query(6, ge=1, le=20),
    db: AsyncSession = Depends(get_db),
):
    recs = await get_recommendations_by_borrow_overlap(ebook_id, limit, db)
    algorithm = "borrow_overlap"

    if not recs:
        return RecommendationsResponse(items=[], algorithm="none")

    # Enrich with metadata from MetisLib
    items: list[RecommendationItem] = []
    try:
        client = get_metislib_client()
        if client:
            for rec in recs:
                try:
                    ebook_data = await client.get_ebook(rec["ebook_id"], entry_type="indie_ebook")
                    if ebook_data:
                        items.append(RecommendationItem(
                            ebook_id=rec["ebook_id"],
                            title=ebook_data.get("title", "Unknown"),
                            author_pen_name=ebook_data.get("author_pen_name", ebook_data.get("author_name", "Unknown")),
                            cover_url=ebook_data.get("cover_url"),
                            genre=ebook_data.get("genre"),
                            average_rating=ebook_data.get("average_rating"),
                            score=rec["score"],
                            reason=rec["reason"],
                        ))
                except Exception:  # noqa: BLE001  # per-rec enrichment best-effort — skip on failure
                    logger.warning("Failed to enrich recommendation ebook %s", rec["ebook_id"])
    except MetisLibUnavailable:
        logger.warning("MetisLib unavailable for recommendation enrichment")

    return RecommendationsResponse(items=items, algorithm=algorithm)

# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Unified Search API Endpoints.

Provides a single search endpoint that queries across all library content sources:
- Local physical catalog
- Streaming services
- Indie ebooks

Returns deduplicated, merged results with availability from all sources.
"""
from typing import Any

import asyncio
from app.core.logging import get_logger

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.database import get_db
from ...models.user import User
from ...services.demand_signal_service import record_signal_detached
from ...services.unified_search_service import (
    ContentFormat,
    ContentSource,
    UnifiedSearchService,
    get_unified_search_service,
)
from .auth import get_current_user_optional

logger = get_logger(__name__)
router = APIRouter(prefix="/search", tags=["search"])


# ==================== Schemas ====================


class RelatedSourceInfo(BaseModel):
    source: str
    source_id: str
    format: str
    is_available: bool
    formats_available: list[str] = []


class UnifiedSearchResultResponse(BaseModel):
    id: str
    source: str
    source_id: str
    title: str
    author: str | None = None
    authors: list[str] = []
    format: str
    format_details: list[str] = []
    description: str | None = None
    cover_url: str | None = None
    isbn: str | None = None
    publisher: str | None = None
    publication_year: int | None = None
    subjects: list[str] = []
    language: str | None = None
    is_available: bool = False
    copies_available: int | None = None
    copies_total: int | None = None
    hold_count: int | None = None
    estimated_wait_days: int | None = None
    download_formats: list[str] = []
    relevance_score: float = 1.0
    related_sources: list[RelatedSourceInfo] = []

    class Config:
        from_attributes = True


class UnifiedSearchResponse(BaseModel):
    query: str
    total_results: int
    results: list[UnifiedSearchResultResponse]
    sources_searched: list[str]
    source_counts: dict[str, int]
    search_time_ms: float
    has_more: bool = False


class QuickSearchResponse(BaseModel):
    query: str
    suggestions: list[dict[str, Any]]


# ==================== Endpoints ====================


@router.get("/unified", response_model=UnifiedSearchResponse)
async def unified_search(
    q: str = Query(..., min_length=1, max_length=500, description="Search query"),
    sources: str | None = Query(
        None,
        description="Comma-separated list of sources to search (local,palace,indie)",
    ),
    formats: str | None = Query(
        None,
        description="Comma-separated list of formats to filter (book,ebook,audiobook,dvd,bluray,cd,vinyl,magazine,game,equipment,kit,tool,video_streaming,music,comic)",
    ),
    available_only: bool = Query(
        False,
        description="Only return items that are currently available",
    ),
    deduplicate: bool = Query(
        True,
        description="Merge duplicate results (same ISBN) from different sources",
    ),
    limit: int = Query(50, ge=1, le=200, description="Maximum results to return"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    year_min: int | None = Query(None, description="Minimum publication year"),
    year_max: int | None = Query(None, description="Maximum publication year"),
    min_lexile: int | None = Query(None, ge=-400, le=2000, description="Minimum Lexile measure"),
    max_lexile: int | None = Query(None, ge=-400, le=2000, description="Maximum Lexile measure"),
    language: list[str] = Query(
        default=[],
        description="Filter by BIBFRAME work language (ISO 639-2/B code, e.g. eng, spa). Multi-select, OR within group. Max 20.",
    ),
    sort_by: str | None = Query(
        None,
        description="Local-source sort field (title, author, publication_year, created_at). Cross-source merge still relevance-scored.",
    ),
    sort_direction: str | None = Query(
        None,
        description="Sort direction (asc, desc). Default asc.",
    ),
    is_large_print: bool | None = Query(
        None,
        description="Restrict to large-print items. Drops indie source (indie has no large-print attribute).",
    ),
    publisher: str | None = Query(
        None,
        description="Free-text publisher contains-match. Local source only; indie source dropped when set (indie carries no publisher metadata).",
    ),
    location: str | None = Query(
        None,
        description="Free-text location/shelf contains-match. Local source only; indie source has no shelf location.",
    ),
    subject_facets: list[str] = Query(
        default=[],
        description="Filter by subject facets selected in the sidebar. Repeated key, AND-joined across facets. Local source only; indie carries no subject metadata. Max 20.",
    ),
    author_facets: list[str] = Query(
        default=[],
        description="Filter by author facets selected in the sidebar. Local source only. Max 20.",
    ),
    series_facets: list[str] = Query(
        default=[],
        description="Filter by series facets selected in the sidebar. Local source only. Max 20.",
    ),
    db: AsyncSession = Depends(get_db),
    current_user: User | None = Depends(get_current_user_optional),
):
    """
    Search across all library content sources.

    This endpoint provides unified search across:
    - **Local catalog**: Physical books, DVDs, CDs, etc.
    - **Palace Project**: Digital ebooks and audiobooks (open-source)
    - **Indie**: Staff-vetted indie author ebooks

    Results are automatically deduplicated by ISBN, so a title available
    in both physical and digital formats appears as one result with
    availability information for all sources.

    **Examples:**
    - `/search/unified?q=harry+potter` - Search all sources
    - `/search/unified?q=mystery&formats=ebook,audiobook` - Digital formats only
    - `/search/unified?q=cookbook&available_only=true` - Only available items
    - `/search/unified?q=python&sources=local,palace` - Specific sources
    """
    if len(language) > 20:
        raise HTTPException(status_code=400, detail="language is capped at 20 entries per request")
    for name, vals in (("subject_facets", subject_facets), ("author_facets", author_facets), ("series_facets", series_facets)):
        if len(vals) > 20:
            raise HTTPException(status_code=400, detail=f"{name} is capped at 20 entries per request")

    service = get_unified_search_service(db)

    # Parse source filter
    source_list = None
    if sources:
        source_list = []
        for s in sources.split(","):
            s = s.strip().lower()
            try:
                source_list.append(ContentSource(s))
            except ValueError:
                # Drift surface: enum widened in code but the FE/clients sent
                # a value we do not recognize. Logging keeps this from
                # masquerading as "the filter just did not match anything".
                logger.warning("unified_search.unknown_source", extra={"source": s})

    # Parse format filter
    format_list = None
    if formats:
        format_list = []
        for f in formats.split(","):
            f = f.strip().lower()
            try:
                format_list.append(ContentFormat(f))
            except ValueError:
                # Drift surface (see unknown_source comment above). The
                # equipment-vanishes-into-books bug (PR #935) lived here
                # silently for months; a log line surfaces it at first
                # request.
                logger.warning("unified_search.unknown_format", extra={"format": f})

    result = await service.search(
        query=q,
        sources=source_list,
        formats=format_list,
        available_only=available_only,
        limit=limit,
        offset=offset,
        deduplicate=deduplicate,
        year_min=year_min,
        year_max=year_max,
        min_lexile=min_lexile,
        max_lexile=max_lexile,
        language=language or None,
        sort_by=sort_by,
        sort_direction=sort_direction,
        is_large_print=is_large_print,
        publisher=publisher,
        location=location,
        subject_facets=subject_facets or None,
        author_facets=author_facets or None,
        series_facets=series_facets or None,
    )

    # Demand-signal capture: zero-result searches across all sources are
    # collection-development evidence. Fire-and-forget so the response
    # latency is unaffected; record_signal_detached opens its own
    # AsyncSession (this request-scoped one closes the moment we
    # return). Service swallows its own errors -- this hook must never
    # break search.
    if result.total_results == 0 and q.strip():
        asyncio.create_task(
            record_signal_detached(
                signal_type="failed_search",
                query_text=q,
                patron_id=current_user.id if current_user else None,
                metadata={
                    "sources": sources,
                    "formats": formats,
                    "available_only": available_only,
                },
            )
        )

    return result.to_dict()


@router.get("/unified/sources")
async def get_available_sources():
    """
    Get list of available search sources and their status.

    Returns information about which content sources are configured
    and available for searching.
    """
    return {
        "sources": [
            {
                "id": "local",
                "name": "Physical Catalog",
                "description": "Books, DVDs, CDs, and other physical items",
                "enabled": True,
            },
            {
                "id": "palace",
                "name": "Palace Project",
                "description": "Open-source ebooks and audiobooks",
                "enabled": True,
            },
            {
                "id": "indie",
                "name": "Indie Ebooks",
                "description": "Self-published and independent ebooks",
                "enabled": True,
            },
        ],
        "formats": [
            {"id": "book", "name": "Physical Book"},
            {"id": "ebook", "name": "eBook"},
            {"id": "audiobook", "name": "Audiobook"},
            {"id": "dvd", "name": "DVD"},
            {"id": "bluray", "name": "Blu-ray"},
            {"id": "cd", "name": "CD"},
            {"id": "magazine", "name": "Magazine"},
            {"id": "video_streaming", "name": "Streaming Video"},
            {"id": "music", "name": "Music"},
        ],
    }


@router.get("/unified/quick", response_model=QuickSearchResponse)
async def quick_search(
    q: str = Query(..., min_length=2, max_length=100, description="Search query"),
    limit: int = Query(10, ge=1, le=20, description="Maximum suggestions"),
    db: AsyncSession = Depends(get_db),
):
    """
    Quick search for autocomplete suggestions.

    Returns a lightweight list of title/author suggestions
    for use in search-as-you-type interfaces.
    """
    service = get_unified_search_service(db)

    # Do a quick search with minimal results
    result = await service.search(
        query=q,
        limit=limit,
        deduplicate=True,
    )

    suggestions = []
    for item in result.results:
        suggestions.append({
            "id": item.id,
            "title": item.title,
            "author": item.author,
            "format": str(item.format),
            "source": str(item.source),
            "is_available": item.is_available,
            "cover_url": item.cover_url,
        })

    return {
        "query": q,
        "suggestions": suggestions,
    }


@router.get("/unified/item/{source}/{source_id}")
async def get_unified_item_details(
    source: str,
    source_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Get detailed information about a specific item.

    Retrieves full details including availability across all sources
    for items that may have the same ISBN.
    """
    service = get_unified_search_service(db)

    # Search by the specific ID
    try:
        source_enum = ContentSource(source.lower())
    except ValueError:
        return {"error": f"Invalid source: {source}"}

    # For now, do a targeted search
    # In production, this would fetch directly by ID
    result = await service.search(
        query=source_id,
        sources=[source_enum],
        limit=1,
        deduplicate=False,
    )

    if not result.results:
        return {"error": "Item not found"}

    item = result.results[0]

    # If item has ISBN, search for it in other sources too
    if item.isbn:
        full_result = await service.search(
            query=item.isbn,
            deduplicate=True,
            limit=5,
        )
        if full_result.results:
            item = full_result.results[0]

    return {
        "item": item.to_dict(),
        "availability_summary": {
            "any_available": item.is_available or any(
                rs.get("is_available") for rs in item.related_sources
            ),
            "sources_with_item": [str(item.source)] + [
                rs.get("source") for rs in item.related_sources
            ],
        },
    }

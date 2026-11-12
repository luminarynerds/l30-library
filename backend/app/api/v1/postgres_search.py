# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
PostgreSQL Full-Text Search API Endpoints.

Native PostgreSQL search using tsvector/tsquery with GIN indexes:
- Weighted full-text search with stemming and prefix matching
- Trigram similarity for fuzzy/typo-tolerant search
- Faceted filtering (type, status, year range, location)
- Search suggestions with trigram similarity
- Optional hybrid mode integrating pgvector semantic search
- Replaces Elasticsearch as the default search engine
"""

from typing import Any, Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError

from ...core.config import get_settings
from ...core.database import get_db
from ...services.search import get_search_service

router = APIRouter(prefix="/search", tags=["postgres-search"])


# ==================== Response Schemas ====================


class SearchResultItem(BaseModel):
    id: int | None = None
    title: str
    author: str | None = None
    item_type: str | None = None
    status: str | None = None
    isbn: str | None = None
    publisher: str | None = None
    publication_year: int | None = None
    description: str | None = None
    subjects: str | None = None
    cover_url: str | None = None
    location: str | None = None
    is_available: bool | None = None
    relevance_score: float = 0.0
    matched_by: str = "fts"
    highlight_title: str | None = None
    highlight_description: str | None = None


class SearchFacetsResponse(BaseModel):
    item_types: dict[str, int] = {}
    statuses: dict[str, int] = {}
    year_ranges: dict[str, int] = {}
    locations: dict[str, int] = {}


class PgSearchResponse(BaseModel):
    query: str
    results: list[SearchResultItem]
    total_results: int
    facets: SearchFacetsResponse
    search_time_ms: float
    search_strategy: str
    page: int = 1
    per_page: int = 20
    has_more: bool = False


class SuggestionItem(BaseModel):
    id: int | None = None
    title: str | None = None
    author: str | None = None
    item_type: str | None = None
    cover_url: str | None = None
    is_available: bool | None = None
    similarity: float = 0.0
    suggestion_type: str = "title"  # title, author
    book_count: int | None = None


class SuggestionsResponse(BaseModel):
    query: str
    suggestions: list[SuggestionItem]
    search_time_ms: float


# ==================== Search Endpoints ====================


@router.get("/pg", response_model=PgSearchResponse)
async def postgres_search(
    q: str = Query(..., min_length=1, max_length=500, description="Search query"),
    item_type: Optional[str] = Query(None, description="Filter by item type (book, dvd, etc.)"),
    status: Optional[str] = Query(None, description="Filter by status (available, checked_out, etc.)"),
    available_only: bool = Query(False, description="Only show available items"),
    year_min: Optional[int] = Query(None, description="Minimum publication year"),
    year_max: Optional[int] = Query(None, description="Maximum publication year"),
    location: Optional[str] = Query(None, description="Filter by location"),
    hybrid: bool = Query(True, description="Include pgvector semantic results (hybrid mode)"),
    semantic_weight: float = Query(0.4, ge=0.0, le=1.0, description="Semantic weight for hybrid mode"),
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Results per page"),
    include_facets: bool = Query(True, description="Include facet counts"),
    db: AsyncSession = Depends(get_db),
):
    """
    Full-text search using PostgreSQL tsvector/tsquery with GIN indexes.

    This is the default search engine. Uses weighted ranking:
    - **Title** (weight A - highest)
    - **Author** (weight B)
    - **Subjects** (weight C)
    - **Description** (weight D - lowest)

    **Search strategy (automatic):**
    - Normal queries: Full-text search with stemming and prefix matching
    - Short/misspelled queries: Trigram similarity (pg_trgm) for typo tolerance
    - Hybrid mode: Merges FTS + pgvector semantic results via reciprocal rank fusion

    **Examples:**
    - `/search/pg?q=harry+potter` - full-text search
    - `/search/pg?q=hary+poter` - trigram fuzzy match (typo tolerant)
    - `/search/pg?q=space+exploration&hybrid=true` - hybrid FTS + semantic
    - `/search/pg?q=mystery&item_type=book&available_only=true` - with facets
    - `/search/pg?q=science&year_min=2020&year_max=2025` - year range filter
    """
    service = get_search_service(db)

    result = await service.search(
        query=q,
        item_type=item_type,
        status=status,
        available_only=available_only,
        year_min=year_min,
        year_max=year_max,
        location=location,
        page=page,
        per_page=per_page,
        include_facets=include_facets,
        hybrid=hybrid,
        semantic_weight=semantic_weight,
    )

    return result.to_dict()


@router.get("/pg/suggestions", response_model=SuggestionsResponse)
async def search_suggestions(
    q: str = Query(..., min_length=2, max_length=100, description="Query for suggestions"),
    limit: int = Query(10, ge=1, le=30, description="Maximum suggestions"),
    db: AsyncSession = Depends(get_db),
):
    """
    Search suggestions using trigram similarity.

    Returns fuzzy-matched title and author suggestions for typeahead/autocomplete.
    Uses pg_trgm GIN indexes for fast (~5-20ms) fuzzy matching.

    Handles typos: "hary poter" will suggest "Harry Potter".

    **Examples:**
    - `/search/pg/suggestions?q=tolk` - suggests "J.R.R. Tolkien"
    - `/search/pg/suggestions?q=hary` - suggests "Harry Potter" titles
    """
    import time
    start = time.time()

    service = get_search_service(db)
    suggestions = await service.suggest(query=q, limit=limit)

    elapsed_ms = (time.time() - start) * 1000

    return SuggestionsResponse(
        query=q,
        suggestions=[SuggestionItem(**s) for s in suggestions],
        search_time_ms=round(elapsed_ms, 2),
    )


@router.get("/pg/health")
async def postgres_search_health(db: AsyncSession = Depends(get_db)):
    """
    Health check for PostgreSQL search.

    Verifies that pg_trgm extension is available and tsvector columns exist.
    """
    from sqlalchemy import text as sql_text

    checks = {}

    # Check pg_trgm extension
    try:
        result = await db.execute(sql_text(
            "SELECT extname FROM pg_extension WHERE extname = 'pg_trgm'"
        ))
        checks["pg_trgm"] = result.scalar() is not None
    except SQLAlchemyError:
        checks["pg_trgm"] = False

    # Check tsvector columns exist
    try:
        result = await db.execute(sql_text("""
            SELECT column_name FROM information_schema.columns
            WHERE table_name = 'catalog_items' AND column_name = 'search_tsv'
        """))
        checks["tsvector_columns"] = result.scalar() is not None
    except SQLAlchemyError:
        checks["tsvector_columns"] = False

    # Check GIN indexes
    try:
        result = await db.execute(sql_text("""
            SELECT count(*) FROM pg_indexes
            WHERE tablename = 'catalog_items'
            AND indexdef LIKE '%gin%'
        """))
        gin_count = result.scalar() or 0
        checks["gin_indexes"] = gin_count
    except SQLAlchemyError:
        checks["gin_indexes"] = 0

    # Check catalog item count
    try:
        result = await db.execute(sql_text("SELECT count(*) FROM catalog_items"))
        checks["catalog_items_count"] = result.scalar() or 0
    except SQLAlchemyError:
        checks["catalog_items_count"] = 0

    settings = get_settings()
    all_ready = checks.get("pg_trgm", False) and checks.get("tsvector_columns", False)

    return {
        "status": "healthy" if all_ready else "initializing",
        "search_engine": settings.search_engine,
        "elasticsearch_enabled": settings.elasticsearch_enabled,
        "postgres_search_ready": all_ready,
        "checks": checks,
        "features": {
            "full_text_search": checks.get("tsvector_columns", False),
            "trigram_fuzzy": checks.get("pg_trgm", False),
            "faceted_filtering": checks.get("tsvector_columns", False),
            "hybrid_semantic": bool(settings.embedding_api_url),
            "search_suggestions": checks.get("pg_trgm", False),
        },
    }

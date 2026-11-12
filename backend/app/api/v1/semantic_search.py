# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Semantic Search API Endpoints

Provides AI-powered semantic search using pgvector embeddings:
- Pure semantic search with cosine similarity
- Hybrid search combining semantic + keyword (RRF fusion)
- Cross-collection discovery (local + Gutenberg)
- Intelligent autocomplete with typo tolerance (pg_trgm)
- Find similar items / "more like this"
- Hidden gem discovery (underrated books by subject similarity)
- Author-to-author similarity
- Embedding management (batch generation, progress, stats)
"""

from app.core.logging import get_logger
from typing import Optional

from fastapi import APIRouter, Depends, Query, BackgroundTasks

logger = get_logger(__name__)
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.database import get_db
from .dependencies import require_admin
from ...models.user import User
from ...schemas.embeddings import (
    SemanticSearchResponse,
    HybridSearchResponse,
    CrossCollectionSearchResponse,
    AutocompleteResponse,
    SemanticSuggestionsResponse,
    SimilarItemsResponse,
    HiddenGemsResponse,
    SimilarAuthorsResponse,
    EmbeddingProgress,
    EmbeddingStats,
    EmbeddingStatusResponse,
)
from ...services.semantic_search_service import get_semantic_search_service
from ...services.autocomplete_service_cached import get_cached_autocomplete_service as get_autocomplete_service
from ...services.discovery_service import get_discovery_service

router = APIRouter(prefix="/search", tags=["semantic-search"])


# ==================== Request Models ====================


class EmbeddingGenerationRequest(BaseModel):
    entity_types: list[str]
    batch_size: int = 100
    skip_existing: bool = True


class GemScoreRecalcRequest(BaseModel):
    source_collection: Optional[str] = None
    batch_size: int = 500


class AuthorEmbeddingRebuildRequest(BaseModel):
    batch_size: int = 100


# ==================== Semantic Search Endpoints ====================


@router.get("/semantic", response_model=SemanticSearchResponse)
async def semantic_search(
    q: str = Query(..., min_length=1, max_length=500, description="Search query"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    entity_types: Optional[str] = Query(
        None, description="Comma-separated entity types to search"
    ),
    sources: Optional[str] = Query(
        None, description="Comma-separated source collections (local,gutenberg)"
    ),
    min_similarity: float = Query(0.3, ge=0.0, le=1.0, description="Minimum similarity threshold"),
    db: AsyncSession = Depends(get_db),
):
    """
    Search using semantic/vector similarity with pgvector.

    Uses HNSW index for fast approximate nearest neighbor search.
    Supports cross-collection search across local catalog and Gutenberg.

    **Examples:**
    - `/search/semantic?q=books about space exploration`
    - `/search/semantic?q=cozy mystery novels&sources=local,gutenberg`
    - `/search/semantic?q=coming of age stories&min_similarity=0.5`
    """
    service = get_semantic_search_service(db)

    entity_type_list = None
    if entity_types:
        entity_type_list = [e.strip() for e in entity_types.split(",")]

    source_list = None
    if sources:
        source_list = [s.strip() for s in sources.split(",")]

    result = await service.search_semantic(
        query=q,
        limit=limit,
        offset=offset,
        entity_types=entity_type_list,
        source_collections=source_list,
        min_similarity=min_similarity,
    )

    return SemanticSearchResponse(
        query=q,
        search_type="semantic",
        total_results=result.get("total_results", 0),
        results=result.get("results", []),
        search_time_ms=result.get("search_time_ms", 0),
        embedding_time_ms=result.get("embedding_time_ms"),
        was_cached=result.get("was_cached", False),
        has_more=result.get("total_results", 0) > offset + limit,
    )


@router.get("/hybrid", response_model=HybridSearchResponse)
async def hybrid_search(
    q: str = Query(..., min_length=1, max_length=500),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    semantic_weight: float = Query(0.6, ge=0.0, le=1.0),
    keyword_weight: float = Query(0.4, ge=0.0, le=1.0),
    sources: Optional[str] = Query(None, description="Comma-separated source collections"),
    db: AsyncSession = Depends(get_db),
):
    """
    Hybrid search combining semantic + keyword with reciprocal rank fusion.

    Best for queries that benefit from both exact keyword matching and
    conceptual similarity. RRF ensures top results from either method
    surface appropriately.
    """
    service = get_semantic_search_service(db)

    source_list = None
    if sources:
        source_list = [s.strip() for s in sources.split(",")]

    result = await service.search_hybrid(
        query=q,
        limit=limit,
        offset=offset,
        semantic_weight=semantic_weight,
        keyword_weight=keyword_weight,
        source_collections=source_list,
    )

    return HybridSearchResponse(
        query=q,
        total_results=result.get("total_results", 0),
        merged_results=result.get("results", []),
        search_time_ms=result.get("search_time_ms", 0),
        semantic_time_ms=result.get("semantic_time_ms", 0),
        keyword_time_ms=result.get("keyword_time_ms", 0),
        merge_strategy="reciprocal_rank_fusion",
        has_more=result.get("total_results", 0) > offset + limit,
    )


@router.get("/cross-collection")
async def cross_collection_search(
    q: str = Query(..., min_length=1, max_length=500),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """
    Search across all collections using semantic similarity.

    Searches local catalog and Gutenberg public domain books
    in a single query with unified relevance scoring.
    """
    service = get_semantic_search_service(db)

    result = await service.search_cross_collection(
        query=q, limit=limit, offset=offset
    )

    # Compute source breakdown
    source_counts: dict[str, int] = {}
    for r in result.get("results", []):
        source = r.get("source", "unknown")
        source_counts[source] = source_counts.get(source, 0) + 1

    return {
        "query": q,
        "total_results": result.get("total_results", 0),
        "results": result.get("results", []),
        "source_breakdown": source_counts,
        "search_time_ms": result.get("search_time_ms", 0),
        "was_cached": result.get("was_cached", False),
    }


# ==================== Autocomplete Endpoints ====================


@router.get("/autocomplete", response_model=AutocompleteResponse)
async def autocomplete(
    q: str = Query(..., min_length=2, max_length=100, description="Autocomplete query"),
    limit: int = Query(10, ge=1, le=30),
    include_authors: bool = Query(True, description="Include author name matches"),
    include_gutenberg: bool = Query(True, description="Include Gutenberg results"),
    db: AsyncSession = Depends(get_db),
):
    """
    Intelligent autocomplete with typo tolerance.

    Uses pg_trgm trigram similarity for fuzzy matching. Handles:
    - Exact prefix matches (highest priority)
    - Typo-tolerant title matches ("hary poter" → "Harry Potter")
    - Author name matches ("tolk" → "J.R.R. Tolkien")
    - Cross-collection matches from Gutenberg

    **Performance:** ~5-20ms with GIN trigram indexes.
    """
    service = get_autocomplete_service(db)

    result = await service.autocomplete(
        query=q,
        limit=limit,
        include_authors=include_authors,
        include_gutenberg=include_gutenberg,
    )

    return AutocompleteResponse(
        query=q,
        suggestions=result.get("suggestions", []),
        search_time_ms=result.get("search_time_ms", 0),
        total_suggestions=result.get("total_suggestions", 0),
        strategy=result.get("strategy", "trigram+prefix"),
    )


@router.get("/semantic/suggestions", response_model=SemanticSuggestionsResponse)
async def semantic_suggestions(
    q: str = Query(..., min_length=2, max_length=100),
    limit: int = Query(10, ge=1, le=20),
    db: AsyncSession = Depends(get_db),
):
    """
    Get semantic search suggestions (concept-aware autocomplete).

    Unlike trigram autocomplete which matches character patterns, this
    uses embeddings to find conceptually related suggestions.
    Slower (~100-300ms) but better for natural language queries.
    """
    service = get_semantic_search_service(db)

    result = await service.search_semantic(query=q, limit=limit, offset=0)

    suggestions = [
        {
            "id": r.get("id"),
            "title": r.get("title"),
            "author": r.get("author"),
            "format": r.get("format"),
            "source": r.get("source"),
            "similarity_score": r.get("similarity_score", 0),
            "cover_url": r.get("cover_url"),
        }
        for r in result.get("results", [])[:limit]
    ]

    return SemanticSuggestionsResponse(
        query=q,
        suggestions=suggestions,
        search_time_ms=result.get("search_time_ms", 0),
        was_cached=result.get("was_cached", False),
    )


# ==================== Similar Items ====================


@router.get("/similar/{source}/{source_id}", response_model=SimilarItemsResponse)
async def find_similar_items(
    source: str,
    source_id: str,
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
):
    """
    Find items similar to a given item using pgvector similarity.

    Returns items from across all collections that are semantically
    similar to the specified item.

    **Example:** `/search/similar/local/123` - find books like item 123
    """
    service = get_semantic_search_service(db)

    try:
        item_id = int(source_id)
    except ValueError:
        return SimilarItemsResponse(
            item_id=source_id, item_title="", similar_items=[],
            similarity_metric="cosine_similarity", search_time_ms=0,
        )

    result = await service.find_similar_items(
        item_id=item_id, source=source, limit=limit
    )

    return SimilarItemsResponse(
        item_id=source_id,
        item_title=result.get("item_title", ""),
        similar_items=result.get("similar_items", []),
        similarity_metric="cosine_similarity",
        search_time_ms=result.get("search_time_ms", 0),
    )


# ==================== Hidden Gem Discovery ====================


@router.get("/hidden-gems", response_model=HiddenGemsResponse)
async def get_hidden_gems(
    subject: Optional[str] = Query(None, description="Filter by subject"),
    source: Optional[str] = Query(None, description="Filter by source (local, gutenberg)"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    min_score: float = Query(0.3, ge=0.0, description="Minimum gem score"),
    db: AsyncSession = Depends(get_db),
):
    """
    Discover hidden gem books - underrated titles with high subject similarity.

    A hidden gem has high semantic similarity to popular books but low
    circulation counts. These are books patrons would probably love but
    haven't discovered yet.

    **Scoring:** gem_score = avg_similarity_to_popular / (1 + log(circulation + 1))

    **Examples:**
    - `/search/hidden-gems?subject=science+fiction` - sci-fi hidden gems
    - `/search/hidden-gems?source=gutenberg` - overlooked public domain books
    """
    service = get_discovery_service(db)

    result = await service.get_hidden_gems(
        subject=subject,
        source_collection=source,
        limit=limit,
        offset=offset,
        min_gem_score=min_score,
    )

    return HiddenGemsResponse(
        gems=result.get("gems", []),
        total=result.get("total", 0),
        filters=result.get("filters", {}),
        search_time_ms=result.get("search_time_ms", 0),
    )


@router.post("/hidden-gems/recalculate")
async def recalculate_gem_scores(
    request: GemScoreRecalcRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    """
    Trigger recalculation of hidden gem scores (background task).

    Should be run periodically (e.g., weekly) after new items are added
    or embeddings are regenerated.
    """
    service = get_discovery_service(db)

    background_tasks.add_task(
        service.recalculate_gem_scores,
        source_collection=request.source_collection,
        batch_size=request.batch_size,
    )

    return {
        "message": "Hidden gem score recalculation started",
        "source_collection": request.source_collection or "all",
        "status": "pending",
    }


# ==================== Author Similarity ====================


@router.get("/similar-authors", response_model=SimilarAuthorsResponse)
async def find_similar_authors(
    author: str = Query(..., min_length=1, max_length=255, description="Author name"),
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
):
    """
    Find authors similar to a given author.

    Uses aggregated book embeddings (centroid approach) to compare
    authors thematically. Shows shared subjects and genres.

    **Example:** `/search/similar-authors?author=Isaac+Asimov`
    """
    service = get_discovery_service(db)

    result = await service.find_similar_authors(
        author_name=author, limit=limit
    )

    return SimilarAuthorsResponse(
        author=author,
        author_book_count=result.get("author_book_count", 0),
        author_genres=result.get("author_genres", []),
        similar_authors=result.get("similar_authors", []),
        search_time_ms=result.get("search_time_ms", 0),
    )


@router.post("/author-embeddings/rebuild")
async def rebuild_author_embeddings(
    request: AuthorEmbeddingRebuildRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    """
    Rebuild all author embeddings from book embeddings (background task).

    Should be run after batch embedding generation completes.
    """
    service = get_discovery_service(db)

    background_tasks.add_task(
        service.rebuild_author_embeddings,
        batch_size=request.batch_size,
    )

    return {
        "message": "Author embedding rebuild started",
        "status": "pending",
    }


# ==================== Embedding Management ====================


@router.post("/embeddings/generate")
async def generate_embeddings(
    request: EmbeddingGenerationRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    """
    Trigger embedding generation for catalog items.

    Generates vector embeddings in the background for semantic search.
    Uses batch API calls for efficiency (~100 embeddings per API call).

    **Entity Types:**
    - `catalog_item_combined` - Title + author + description + subjects
    - `catalog_item_title` - Title only
    - `gutenberg_combined` - Gutenberg book metadata
    - `library_document` - Newsletter/report document chunks

    **Cost:** ~$0.02 per 1M tokens with text-embedding-3-small
    """
    service = get_semantic_search_service(db)

    for entity_type in request.entity_types:
        background_tasks.add_task(
            service.generate_embeddings_batch,
            entity_type=entity_type,
            batch_size=request.batch_size,
            skip_existing=request.skip_existing,
        )

    return {
        "message": f"Started embedding generation for {len(request.entity_types)} entity types",
        "entity_types": request.entity_types,
        "status": "pending",
    }


@router.get("/embeddings/progress/{entity_type}")
async def embedding_progress(
    entity_type: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    """Get progress of embedding generation for an entity type."""
    from ...models.embeddings import EmbeddingMetadata
    from sqlalchemy import select

    stmt = select(EmbeddingMetadata).where(EmbeddingMetadata.entity_type == entity_type)
    result = await db.execute(stmt)
    metadata = result.scalar_one_or_none()

    if not metadata:
        return {"entity_type": entity_type, "status": "not_started", "progress": None}

    return {
        "entity_type": entity_type,
        "status": metadata.status,
        "progress": {
            "total_count": metadata.total_count,
            "embedded_count": metadata.embedded_count,
            "failed_count": metadata.failed_count,
            "progress_percent": metadata.progress_percent,
            "started_at": metadata.started_at,
            "completed_at": metadata.completed_at,
        },
    }


@router.get("/embeddings/stats")
async def embedding_stats(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    """Get overall embedding statistics across all entity types."""
    from sqlalchemy import select, func
    from ...models.embeddings import TextEmbedding, AuthorEmbedding

    total_stmt = select(func.count(TextEmbedding.id))
    total = (await db.execute(total_stmt)).scalar() or 0

    embedded_stmt = select(func.count(TextEmbedding.id)).where(TextEmbedding.is_generated == True)
    embedded = (await db.execute(embedded_stmt)).scalar() or 0

    failed_stmt = select(func.count(TextEmbedding.id)).where(TextEmbedding.error_message.isnot(None))
    failed = (await db.execute(failed_stmt)).scalar() or 0

    author_stmt = select(func.count(AuthorEmbedding.id)).where(AuthorEmbedding.is_generated == True)
    author_count = (await db.execute(author_stmt)).scalar() or 0

    latest_stmt = (
        select(TextEmbedding)
        .where(TextEmbedding.is_generated == True)
        .order_by(TextEmbedding.generated_at.desc())
        .limit(1)
    )
    latest = (await db.execute(latest_stmt)).scalar_one_or_none()

    return {
        "total_embeddings": total,
        "embedded_count": embedded,
        "failed_count": failed,
        "pending_count": total - embedded - failed,
        "author_embeddings_count": author_count,
        "embedding_coverage_percent": round(embedded / total * 100, 1) if total > 0 else 0,
        "average_embedding_dimension": 1536,
        "embedding_model": "text-embedding-3-small",
        "last_embedding_generated_at": latest.generated_at if latest else None,
    }


@router.get("/embeddings/health")
async def embedding_health(db: AsyncSession = Depends(get_db)):
    """Health check for semantic search system."""
    from sqlalchemy import select, func, text

    embedding_count = 0
    table_exists = False
    try:
        from ...models.embeddings import TextEmbedding
        stmt = select(func.count(TextEmbedding.id)).where(TextEmbedding.is_generated == True)
        embedding_count = (await db.execute(stmt)).scalar() or 0
        table_exists = True
    except Exception as e:  # noqa: BLE001  # embeddings probe — report not-ready if model unavailable
        logger.warning("Failed to query embedding count for semantic search status: %s", e)

    ready = table_exists and embedding_count > 100

    return {
        "status": "healthy" if ready else "initializing",
        "semantic_search_ready": ready,
        "embeddings_available": embedding_count,
        "table_exists": table_exists,
        "minimum_embeddings_required": 100,
        "features": {
            "semantic_search": ready,
            "hybrid_search": ready,
            "autocomplete": True,  # Trigram works without embeddings
            "similar_items": ready,
            "hidden_gems": ready,
            "author_similarity": ready,
            "cross_collection": ready,
        },
        "message": (
            "All semantic search features operational" if ready
            else "text_embeddings table not created yet" if not table_exists
            else f"Semantic search initializing ({embedding_count}/100 embeddings)"
        ),
    }

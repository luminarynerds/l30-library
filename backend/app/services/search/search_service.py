# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from app.core.logging import get_logger
import re
import time
from dataclasses import dataclass, field
from typing import Any, Optional

from sqlalchemy import and_, func, select, text, literal_column
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.config import get_settings
from ...models.catalog import CatalogItem, ItemStatus, ItemType

logger = get_logger(__name__)

# Defaults are kept for callers that import these names directly; the
# PostgresSearchService instance reads tunable values from settings at runtime.
FTS_MIN_QUERY_LENGTH = 3
TRIGRAM_THRESHOLD = 0.15
RRF_K = 60


@dataclass
class SearchFacets:
    item_types: dict[str, int] = field(default_factory=dict)
    statuses: dict[str, int] = field(default_factory=dict)
    year_ranges: dict[str, int] = field(default_factory=dict)
    locations: dict[str, int] = field(default_factory=dict)


@dataclass
class SearchResult:
    item: dict[str, Any]
    relevance_score: float = 0.0
    matched_by: str = "fts"  # fts, trigram, semantic, hybrid
    highlight_title: str | None = None
    highlight_description: str | None = None


@dataclass
class SearchResponse:
    query: str
    results: list[SearchResult]
    total_results: int
    facets: SearchFacets
    search_time_ms: float
    search_strategy: str  # "fts", "trigram", "hybrid"
    page: int = 1
    per_page: int = 20
    has_more: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "query": self.query,
            "results": [
                {
                    **r.item,
                    "relevance_score": round(r.relevance_score, 4),
                    "matched_by": r.matched_by,
                    "highlight_title": r.highlight_title,
                    "highlight_description": r.highlight_description,
                }
                for r in self.results
            ],
            "total_results": self.total_results,
            "facets": {
                "item_types": self.facets.item_types,
                "statuses": self.facets.statuses,
                "year_ranges": self.facets.year_ranges,
                "locations": self.facets.locations,
            },
            "search_time_ms": round(self.search_time_ms, 2),
            "search_strategy": self.search_strategy,
            "page": self.page,
            "per_page": self.per_page,
            "has_more": self.has_more,
        }


class PostgresSearchService:

    def __init__(self, db: AsyncSession):
        self.db = db
        self.settings = get_settings()
        self._ts_config = self.settings.search_text_config
        self._trigram_threshold = self.settings.search_trigram_threshold
        self._rank_normalization = self.settings.search_ts_rank_normalization
        self._rrf_k = self.settings.search_rrf_k
        self._fts_min_query_length = self.settings.search_fts_min_query_length

    # =========================================================================
    # Public API
    # =========================================================================

    async def search(
        self,
        query: str,
        *,
        item_type: Optional[str] = None,
        status: Optional[str] = None,
        language: Optional[str] = None,
        available_only: bool = False,
        year_min: Optional[int] = None,
        year_max: Optional[int] = None,
        location: Optional[str] = None,
        page: int = 1,
        per_page: int = 20,
        include_facets: bool = True,
        hybrid: bool = False,
        semantic_weight: float = 0.4,
    ) -> SearchResponse:
        start_time = time.time()
        query = query.strip()

        if not query:
            return SearchResponse(
                query=query, results=[], total_results=0,
                facets=SearchFacets(), search_time_ms=0,
                search_strategy="none", page=page, per_page=per_page,
            )

        # Determine search strategy
        use_trigram = len(query) < self._fts_min_query_length
        strategy = "trigram" if use_trigram else "fts"

        # Build filter conditions
        filters = self._build_filters(
            item_type=item_type, status=status, available_only=available_only,
            year_min=year_min, year_max=year_max, location=location,
        )

        # Execute primary search
        if use_trigram:
            results, total = await self._search_trigram(
                query, filters=filters, page=page, per_page=per_page,
            )
        else:
            results, total = await self._search_fts(
                query, filters=filters, page=page, per_page=per_page,
            )

        # If FTS returns no results, fall back to trigram
        if not results and not use_trigram:
            results, total = await self._search_trigram(
                query, filters=filters, page=page, per_page=per_page,
            )
            if results:
                strategy = "trigram_fallback"

        # Hybrid: merge with semantic search results via RRF
        if hybrid and self.settings.embedding_api_url:
            try:
                semantic_results = await self._search_semantic(query, limit=per_page * 2)
                if semantic_results:
                    results = self._merge_rrf(
                        results, semantic_results,
                        fts_weight=1.0 - semantic_weight,
                        semantic_weight=semantic_weight,
                    )
                    total = len(results)
                    # Re-paginate after merge
                    offset = (page - 1) * per_page
                    results = results[offset:offset + per_page]
                    strategy = "hybrid"
            except Exception as e:  # noqa: BLE001  # search fallback - semantic failure must not break hybrid mode
                logger.warning(f"Semantic search failed in hybrid mode: {e}")

        # Compute facets
        facets = SearchFacets()
        if include_facets and query:
            facets = await self._compute_facets(query, use_trigram=use_trigram)

        search_time_ms = (time.time() - start_time) * 1000

        return SearchResponse(
            query=query,
            results=results,
            total_results=total,
            facets=facets,
            search_time_ms=search_time_ms,
            search_strategy=strategy,
            page=page,
            per_page=per_page,
            has_more=total > page * per_page,
        )

    async def suggest(
        self,
        query: str,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        if not query or len(query) < 2:
            return []

        start_time = time.time()

        # OPTIMIZATION: Use % operator for index-accelerated filtering,
        # then calculate similarity() only for ordering.
        # The % operator uses the GIN trigram index on title_trgm.
        # Example: title % 'harry' scans only similar titles, not entire table.

        similarity_expr = func.similarity(CatalogItem.title, query)

        title_stmt = (
            select(
                CatalogItem.id,
                CatalogItem.title,
                CatalogItem.author,
                CatalogItem.item_type,
                CatalogItem.cover_url,
                CatalogItem.status,
                similarity_expr.label("sim"),
            )
            .where(
                # similarity() > threshold gives consistent recall regardless
                # of pg_trgm's session-level limit (default 0.3, often too high
                # for short queries against long titles).
                similarity_expr > self._trigram_threshold
            )
            .order_by(similarity_expr.desc())
            .limit(limit)
        )

        result = await self.db.execute(title_stmt)
        rows = result.all()

        suggestions = []
        seen_titles = set()

        for row in rows:
            title_lower = row.title.lower() if row.title else ""
            if title_lower in seen_titles:
                continue
            seen_titles.add(title_lower)

            suggestions.append({
                "id": row.id,
                "title": row.title,
                "author": row.author,
                "item_type": str(row.item_type) if row.item_type else None,
                "cover_url": row.cover_url,
                "is_available": row.status and str(row.status) == "available",
                "similarity": round(float(row.sim), 3),
                "suggestion_type": "title",
            })

        # Also search authors if we have room
        if len(suggestions) < limit:
            remaining = limit - len(suggestions)
            author_sim = func.similarity(CatalogItem.author, query)
            author_stmt = (
                select(
                    CatalogItem.author,
                    func.count(CatalogItem.id).label("book_count"),
                    func.max(author_sim).label("sim"),
                )
                .where(
                    and_(
                        CatalogItem.author.isnot(None),
                        func.similarity(CatalogItem.author, query) > self._trigram_threshold
                    )
                )
                .group_by(CatalogItem.author)
                .order_by(func.max(author_sim).desc())
                .limit(remaining)
            )

            author_result = await self.db.execute(author_stmt)
            author_rows = author_result.all()

            for row in author_rows:
                suggestions.append({
                    "id": None,
                    "title": row.author,
                    "author": None,
                    "item_type": None,
                    "cover_url": None,
                    "is_available": None,
                    "similarity": round(float(row.sim), 3),
                    "suggestion_type": "author",
                    "book_count": row.book_count,
                })

        elapsed_ms = (time.time() - start_time) * 1000
        logger.debug(f"Suggestions for '{query}': {len(suggestions)} results in {elapsed_ms:.1f}ms")

        return suggestions

    # =========================================================================
    # Full-Text Search (tsvector / tsquery)
    # =========================================================================

    async def _search_fts(
        self,
        query: str,
        *,
        filters: list,
        page: int = 1,
        per_page: int = 20,
    ) -> tuple[list[SearchResult], int]:
        tsquery = self._build_tsquery(query)

        # ts_rank_cd uses cover-density ranking which rewards phrase proximity.
        # Normalisation flag is configurable; see search_ts_rank_normalization.
        ts_config = self._ts_config
        rank_expr = func.ts_rank_cd(
            literal_column("search_tsv"),
            func.to_tsquery(ts_config, tsquery),
            self._rank_normalization,
        ).label("rank")

        headline_title = func.ts_headline(
            ts_config,
            CatalogItem.title,
            func.to_tsquery(ts_config, tsquery),
            "StartSel=<mark>, StopSel=</mark>, MaxFragments=1, MaxWords=50",
        ).label("headline_title")

        headline_desc = func.ts_headline(
            ts_config,
            func.coalesce(CatalogItem.description, ""),
            func.to_tsquery(ts_config, tsquery),
            "StartSel=<mark>, StopSel=</mark>, MaxFragments=2, MaxWords=40",
        ).label("headline_desc")

        match_condition = literal_column("search_tsv").op("@@")(
            func.to_tsquery(ts_config, tsquery)
        )

        # Count query
        count_stmt = (
            select(func.count(CatalogItem.id))
            .where(and_(match_condition, *filters))
        )
        count_result = await self.db.execute(count_stmt)
        total = count_result.scalar() or 0

        # Results query
        offset = (page - 1) * per_page
        results_stmt = (
            select(
                CatalogItem,
                rank_expr,
                headline_title,
                headline_desc,
            )
            .where(and_(match_condition, *filters))
            .order_by(text("rank DESC"))
            .offset(offset)
            .limit(per_page)
        )

        result = await self.db.execute(results_stmt)
        rows = result.all()

        results = []
        for row in rows:
            item = row[0]
            rank = float(row[1]) if row[1] else 0.0
            hl_title = row[2]
            hl_desc = row[3]

            results.append(SearchResult(
                item=self._item_to_dict(item),
                relevance_score=rank,
                matched_by="fts",
                highlight_title=hl_title,
                highlight_description=hl_desc,
            ))

        return results, total

    # =========================================================================
    # Trigram Similarity Search (pg_trgm)
    # =========================================================================

    async def _search_trigram(
        self,
        query: str,
        *,
        filters: list,
        page: int = 1,
        per_page: int = 20,
    ) -> tuple[list[SearchResult], int]:
        # Compute similarity across title and author
        title_sim = func.similarity(CatalogItem.title, query)
        author_sim = func.coalesce(func.similarity(CatalogItem.author, query), literal_column("0"))

        # Combined similarity score (title weighted higher)
        combined_sim = (title_sim * literal_column("0.7") + author_sim * literal_column("0.3")).label("sim")

        match_condition = (
            (func.similarity(CatalogItem.title, query) > self._trigram_threshold) |
            (func.similarity(CatalogItem.author, query) > self._trigram_threshold)
        )

        # Count
        count_stmt = (
            select(func.count(CatalogItem.id))
            .where(and_(match_condition, *filters))
        )
        count_result = await self.db.execute(count_stmt)
        total = count_result.scalar() or 0

        # Results
        offset = (page - 1) * per_page
        results_stmt = (
            select(CatalogItem, combined_sim)
            .where(and_(match_condition, *filters))
            .order_by(text("sim DESC"))
            .offset(offset)
            .limit(per_page)
        )

        result = await self.db.execute(results_stmt)
        rows = result.all()

        results = []
        for row in rows:
            item = row[0]
            sim = float(row[1]) if row[1] else 0.0

            results.append(SearchResult(
                item=self._item_to_dict(item),
                relevance_score=sim,
                matched_by="trigram",
            ))

        return results, total

    # =========================================================================
    # Semantic Search Integration (pgvector)
    # =========================================================================

    async def _search_semantic(
        self, query: str, limit: int = 50,
    ) -> list[SearchResult]:
        from ..semantic_search_service import get_semantic_search_service

        service = get_semantic_search_service(self.db)
        result = await service.search_semantic(
            query=query, limit=limit, offset=0, min_similarity=0.3,
        )

        semantic_results = []
        for r in result.get("results", []):
            semantic_results.append(SearchResult(
                item={
                    "id": r.get("source_id"),
                    "title": r.get("title", ""),
                    "author": r.get("author"),
                    "description": r.get("description"),
                    "cover_url": r.get("cover_url"),
                    "item_type": r.get("format"),
                    "is_available": r.get("is_available", False),
                    "source": r.get("source", "local"),
                },
                relevance_score=r.get("similarity_score", 0.0),
                matched_by="semantic",
            ))

        return semantic_results

    # =========================================================================
    # Hybrid Merge (Reciprocal Rank Fusion)
    # =========================================================================

    def _merge_rrf(
        self,
        fts_results: list[SearchResult],
        semantic_results: list[SearchResult],
        fts_weight: float = 0.6,
        semantic_weight: float = 0.4,
    ) -> list[SearchResult]:
        seen: dict[str, SearchResult] = {}
        k = self._rrf_k

        for i, result in enumerate(fts_results):
            key = str(result.item.get("id", f"fts_{i}"))
            rrf_score = fts_weight / (k + i)
            if key in seen:
                seen[key].relevance_score += rrf_score
                seen[key].matched_by = "hybrid"
            else:
                result.relevance_score = rrf_score
                result.matched_by = "fts"
                seen[key] = result

        for i, result in enumerate(semantic_results):
            key = str(result.item.get("id", f"sem_{i}"))
            rrf_score = semantic_weight / (k + i)
            if key in seen:
                seen[key].relevance_score += rrf_score
                seen[key].matched_by = "hybrid"
            else:
                result.relevance_score = rrf_score
                result.matched_by = "semantic"
                seen[key] = result

        merged = sorted(seen.values(), key=lambda x: x.relevance_score, reverse=True)
        return merged

    # =========================================================================
    # Faceted Filtering
    # =========================================================================

    async def _compute_facets(
        self, query: str, *, use_trigram: bool = False,
    ) -> SearchFacets:
        if use_trigram:
            params = {"q": query, "thr": self._trigram_threshold}
            match_sql = (
                "similarity(title, :q) > :thr OR "
                "similarity(author, :q) > :thr"
            )
        else:
            tsquery = self._build_tsquery(query)
            params = {"tsq": tsquery, "cfg": self._ts_config}
            match_sql = "search_tsv @@ to_tsquery(:cfg, :tsq)"

        sql = f"""
            WITH matches AS (
                SELECT item_type, status, publication_year, location
                FROM catalog_items
                WHERE {match_sql}
            ),
            type_counts AS (
                SELECT 'item_type'::text AS facet, item_type::text AS bucket,
                       COUNT(*)::bigint AS n
                FROM matches GROUP BY item_type
            ),
            status_counts AS (
                SELECT 'status'::text AS facet, status::text AS bucket,
                       COUNT(*)::bigint AS n
                FROM matches GROUP BY status
            ),
            year_counts AS (
                SELECT 'year'::text AS facet,
                       ((publication_year / 10) * 10)::text AS bucket,
                       COUNT(*)::bigint AS n
                FROM matches
                WHERE publication_year IS NOT NULL
                GROUP BY (publication_year / 10) * 10
            ),
            location_ranked AS (
                SELECT location, COUNT(*)::bigint AS n,
                       ROW_NUMBER() OVER (ORDER BY COUNT(*) DESC) AS rn
                FROM matches
                WHERE location IS NOT NULL
                GROUP BY location
            ),
            location_counts AS (
                SELECT 'location'::text AS facet, location AS bucket, n
                FROM location_ranked WHERE rn <= 20
            )
            SELECT facet, bucket, n FROM type_counts
            UNION ALL SELECT facet, bucket, n FROM status_counts
            UNION ALL SELECT facet, bucket, n FROM year_counts
            UNION ALL SELECT facet, bucket, n FROM location_counts
        """

        result = await self.db.execute(text(sql), params)

        item_types: dict[str, int] = {}
        statuses: dict[str, int] = {}
        year_ranges: dict[str, int] = {}
        locations: dict[str, int] = {}

        for facet, bucket, n in result.all():
            count = int(n)
            if facet == "item_type":
                item_types[bucket or "unknown"] = count
            elif facet == "status":
                statuses[bucket or "unknown"] = count
            elif facet == "year" and bucket is not None:
                year_ranges[f"{int(bucket)}s"] = count
            elif facet == "location" and bucket:
                locations[bucket] = count

        return SearchFacets(
            item_types=item_types,
            statuses=statuses,
            year_ranges=year_ranges,
            locations=locations,
        )

    # =========================================================================
    # Query Building
    # =========================================================================

    def _build_tsquery(self, query: str) -> str:
        # Remove characters that have special meaning in tsquery
        cleaned = re.sub(r"[!&|():*<>\\'\"]", " ", query)
        words = cleaned.split()

        if not words:
            return "''"

        if len(words) == 1:
            return f"{words[0]}:*"

        # Join with AND, prefix-match the last word for typeahead
        parts = [w for w in words[:-1]]
        parts.append(f"{words[-1]}:*")
        return " & ".join(parts)

    # =========================================================================
    # Filter Building
    # =========================================================================

    def _build_filters(
        self,
        *,
        item_type: Optional[str] = None,
        status: Optional[str] = None,
        available_only: bool = False,
        year_min: Optional[int] = None,
        year_max: Optional[int] = None,
        location: Optional[str] = None,
    ) -> list:
        filters = []

        if item_type:
            try:
                filters.append(CatalogItem.item_type == ItemType(item_type))
            except ValueError:
                logger.warning("Invalid item_type filter value: %s", item_type)

        if status:
            try:
                filters.append(CatalogItem.status == ItemStatus(status))
            except ValueError:
                logger.warning("Invalid status filter value: %s", status)

        if available_only:
            filters.append(CatalogItem.status == ItemStatus.available)

        if year_min is not None:
            filters.append(CatalogItem.publication_year >= year_min)

        if year_max is not None:
            filters.append(CatalogItem.publication_year <= year_max)

        if location:
            safe_location = location.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            filters.append(CatalogItem.location.ilike(f"%{safe_location}%"))

        return filters

    # =========================================================================
    # Helpers
    # =========================================================================

    def _looks_misspelled(self, query: str) -> bool:
        words = query.split()
        # Single very short word
        if len(words) == 1 and len(words[0]) <= 3:
            return True
        # Words with uncommon character patterns suggesting typos
        for word in words:
            consonant_cluster = re.search(r"[bcdfghjklmnpqrstvwxyz]{4,}", word.lower())
            if consonant_cluster:
                return True
        return False

    def _item_to_dict(self, item: CatalogItem) -> dict[str, Any]:
        return {
            "id": item.id,
            "title": item.title,
            "author": item.author,
            "item_type": str(item.item_type) if item.item_type else None,
            "status": str(item.status) if item.status else None,
            "isbn": item.isbn,
            "publisher": item.publisher,
            "publication_year": item.publication_year,
            "description": (item.description or "")[:300],
            "subjects": item.subjects,
            "cover_url": item.cover_url,
            "page_count": item.page_count,
            "location": item.location,
            "barcode": item.barcode,
            "is_available": item.status and str(item.status) == "available",
        }


def get_search_service(db: AsyncSession) -> PostgresSearchService:
    return PostgresSearchService(db)

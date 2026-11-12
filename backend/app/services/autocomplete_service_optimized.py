# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from app.core.logging import get_logger
import time
from typing import Any, Optional

from sqlalchemy import select, func, text, or_, literal_column, union_all
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.catalog import CatalogItem
from ..models.gutenberg import GutenbergBook
from ..models.embeddings import TextEmbedding

logger = get_logger(__name__)


class OptimizedAutocompleteService:

    def __init__(self, db: AsyncSession):
        self.db = db

    async def autocomplete(
        self,
        query: str,
        limit: int = 10,
        include_authors: bool = True,
        include_gutenberg: bool = True,
        min_similarity: float = 0.2,
    ) -> dict[str, Any]:
        start_time = time.time()
        query = query.strip()

        if len(query) < 2:
            return {
                "query": query,
                "suggestions": [],
                "search_time_ms": 0,
                "strategy": "too_short",
            }

        # Consolidated query using UNION
        suggestions = await self._consolidated_autocomplete(
            query, limit, include_authors, include_gutenberg, min_similarity
        )

        search_time_ms = (time.time() - start_time) * 1000

        return {
            "query": query,
            "suggestions": suggestions[:limit],
            "search_time_ms": round(search_time_ms, 2),
            "total_suggestions": len(suggestions),
            "strategy": "consolidated_union",
        }

    async def _consolidated_autocomplete(
        self,
        query: str,
        limit: int,
        include_authors: bool,
        include_gutenberg: bool,
        min_similarity: float,
    ) -> list[dict[str, Any]]:
        suggestions = []
        prefix_pattern = f"{query}%"

        # =====================================================================
        # CATALOG QUERIES - Consolidated into single execution
        # =====================================================================

        # Query 1: Prefix matches on titles (highest priority)
        prefix_stmt = (
            select(
                CatalogItem.id,
                CatalogItem.title,
                CatalogItem.author,
                CatalogItem.item_type,
                CatalogItem.cover_url,
                literal_column("'local'").label("source"),
                literal_column("1.0").label("match_score"),
                literal_column("'prefix'").label("match_type"),
            )
            .where(CatalogItem.title.ilike(prefix_pattern))
            .limit(limit)
        )

        # Query 2: Trigram similarity on titles (catch typos and fuzzy matches)
        trgm_stmt = (
            select(
                CatalogItem.id,
                CatalogItem.title,
                CatalogItem.author,
                CatalogItem.item_type,
                CatalogItem.cover_url,
                literal_column("'local'").label("source"),
                func.similarity(CatalogItem.title, query).label("match_score"),
                literal_column("'trigram'").label("match_type"),
            )
            .where(text("title % :query"))
            .where(~CatalogItem.title.ilike(prefix_pattern))  # Don't duplicate prefix results
            .order_by(text("similarity(title, :query) DESC"))
            .limit(limit)
        )

        # Query 3: Author trigram similarity (if enabled)
        author_statements = []
        if include_authors:
            author_stmt = (
                select(
                    CatalogItem.id,
                    CatalogItem.title,
                    CatalogItem.author,
                    CatalogItem.item_type,
                    CatalogItem.cover_url,
                    literal_column("'local'").label("source"),
                    func.similarity(CatalogItem.author, query).label("match_score"),
                    literal_column("'author'").label("match_type"),
                )
                .where(text("author % :query"))
                .order_by(text("similarity(author, :query) DESC"))
                .limit(limit // 2)
            )
            author_statements.append(author_stmt)

        # Query 4: Gutenberg books (if enabled)
        gutenberg_statements = []
        if include_gutenberg:
            gb_stmt = (
                select(
                    GutenbergBook.id,
                    GutenbergBook.title,
                    GutenbergBook.authors,
                    literal_column("'ebook'").label("item_type"),
                    GutenbergBook.cover_url,
                    literal_column("'gutenberg'").label("source"),
                    func.similarity(GutenbergBook.title, query).label("match_score"),
                    literal_column("'trigram'").label("match_type"),
                )
                .where(text("gutenberg_books.title % :query"))
                .order_by(text("similarity(gutenberg_books.title, :query) DESC"))
                .limit(limit // 2)
            )
            gutenberg_statements.append(gb_stmt)

        # Combine all queries with UNION for single execution
        combined_queries = [prefix_stmt, trgm_stmt] + author_statements + gutenberg_statements

        if len(combined_queries) > 1:
            union_stmt = union_all(*combined_queries)
        else:
            union_stmt = combined_queries[0]

        # Execute consolidated query
        result = await self.db.execute(union_stmt, {"query": query})
        rows = result.all()

        # Deduplicate results (single pass)
        seen_ids = set()
        for row in rows:
            if row.source == "gutenberg":
                item_id = f"gutenberg:{row.id}"
            else:
                item_id = f"local:{row.id}"

            if item_id in seen_ids:
                continue

            # Check similarity threshold
            if row.source != "local" and hasattr(row, "match_score"):
                if row.match_score < min_similarity and row.match_type != "prefix":
                    continue

            seen_ids.add(item_id)

            # Format result based on source
            if row.source == "gutenberg":
                import json
                authors_str = ""
                if row.authors:
                    try:
                        authors_list = json.loads(row.authors) if isinstance(row.authors, str) else row.authors
                        authors_str = ", ".join(a.get("name", "") for a in authors_list)
                    except (ValueError, TypeError) as e:
                        logger.warning("Failed to parse Gutenberg authors JSON: %s", e)

                suggestions.append({
                    "id": item_id,
                    "title": row.title,
                    "author": authors_str,
                    "format": "ebook",
                    "source": "gutenberg",
                    "cover_url": row.cover_url,
                    "match_type": row.match_type,
                    "similarity_score": round(float(row.match_score), 3) if hasattr(row, "match_score") else 1.0,
                })
            else:
                suggestions.append({
                    "id": item_id,
                    "title": row.title,
                    "author": row.author,
                    "format": str(row.item_type) if row.item_type else "book",
                    "source": row.source,
                    "cover_url": row.cover_url,
                    "match_type": row.match_type,
                    "similarity_score": round(float(row.match_score), 3) if hasattr(row, "match_score") else 1.0,
                })

        # Sort: prefix > trigram > author > source (once at end)
        type_priority = {"prefix": 0, "trigram": 1, "author": 2}
        suggestions.sort(
            key=lambda s: (
                type_priority.get(s["match_type"], 3),
                -s["similarity_score"],
            )
        )

        return suggestions


def get_optimized_autocomplete_service(db: AsyncSession) -> OptimizedAutocompleteService:
    return OptimizedAutocompleteService(db)

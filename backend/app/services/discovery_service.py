# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

import hashlib
import json
from app.core.logging import get_logger
import time
import numpy as np
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import select, func, and_, text, literal_column
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.embeddings import (
    TextEmbedding, AuthorEmbedding, HiddenGemScore, EMBEDDING_DIM,
)
from ..models.catalog import CatalogItem
from ..models.gutenberg import GutenbergBook
from ..core.config import get_settings

logger = get_logger(__name__)


class DiscoveryService:

    def __init__(self, db: AsyncSession):
        self.db = db
        self.settings = get_settings()

    # =========================================================================
    # Hidden Gem Discovery
    # =========================================================================

    async def get_hidden_gems(
        self,
        subject: Optional[str] = None,
        source_collection: Optional[str] = None,
        limit: int = 20,
        offset: int = 0,
        min_gem_score: float = 0.3,
    ) -> dict[str, Any]:
        start_time = time.time()

        stmt = (
            select(HiddenGemScore)
            .where(HiddenGemScore.gem_score >= min_gem_score)
        )

        if source_collection:
            stmt = stmt.where(HiddenGemScore.source_collection == source_collection)

        if subject:
            # JSON contains for subject filtering
            stmt = stmt.where(
                text("subjects::text ILIKE :subject_pattern")
            )

        stmt = (
            stmt
            .order_by(HiddenGemScore.gem_score.desc())
            .offset(offset)
            .limit(limit)
        )

        params = {}
        if subject:
            params["subject_pattern"] = f"%{subject}%"

        result = await self.db.execute(stmt, params)
        gems = result.scalars().all()

        search_time_ms = (time.time() - start_time) * 1000

        return {
            "gems": [g.to_dict() for g in gems],
            "total": len(gems),
            "filters": {
                "subject": subject,
                "source_collection": source_collection,
                "min_gem_score": min_gem_score,
            },
            "search_time_ms": round(search_time_ms, 2),
        }

    async def recalculate_gem_scores(
        self,
        source_collection: Optional[str] = None,
        batch_size: int = 500,
    ) -> dict[str, Any]:
        start_time = time.time()
        processed = 0
        errors = 0

        # Get popular items (top items by checkout count or download count)
        # For local items, use checkout count proxy; for gutenberg, use download_count
        popular_embeddings = await self._get_popular_embeddings(source_collection, top_n=50)

        if not popular_embeddings:
            return {
                "processed": 0,
                "errors": 0,
                "message": "No popular items found with embeddings",
            }

        # Get all items with embeddings
        stmt = (
            select(TextEmbedding)
            .where(
                and_(
                    TextEmbedding.is_generated == True,
                    TextEmbedding.entity_type.in_([
                        "catalog_item_combined", "gutenberg_combined"
                    ]),
                )
            )
        )
        if source_collection:
            stmt = stmt.where(TextEmbedding.source_collection == source_collection)

        result = await self.db.execute(stmt)
        all_embeddings = result.scalars().all()

        # Compute popular embedding vectors as numpy array for efficient batch similarity
        popular_vectors = []
        for pe in popular_embeddings:
            if pe.embedding is not None:
                popular_vectors.append(list(pe.embedding))

        if not popular_vectors:
            return {"processed": 0, "errors": 0, "message": "No valid popular embeddings"}

        pop_matrix = np.array(popular_vectors)
        pop_norms = np.linalg.norm(pop_matrix, axis=1, keepdims=True)
        pop_matrix_normalized = pop_matrix / np.maximum(pop_norms, 1e-10)

        for emb in all_embeddings:
            try:
                if emb.embedding is None:
                    continue

                emb_vec = np.array(list(emb.embedding))
                emb_norm = np.linalg.norm(emb_vec)
                if emb_norm < 1e-10:
                    continue
                emb_normalized = emb_vec / emb_norm

                # Cosine similarity to all popular items
                similarities = pop_matrix_normalized @ emb_normalized
                avg_similarity = float(np.mean(similarities))

                # Get circulation count
                circ_count = await self._get_circulation_count(
                    emb.entity_type, emb.entity_id, emb.source_collection
                )

                # Compute gem score: high similarity + low popularity = hidden gem
                import math
                popularity_score = min(1.0, circ_count / 100.0)  # Normalize to 0-1
                gem_score = avg_similarity / (1 + math.log(circ_count + 1))

                # Get item metadata
                title, author, subjects = await self._get_item_metadata(
                    emb.entity_type, emb.entity_id, emb.source_collection
                )

                # Upsert gem score
                existing_stmt = select(HiddenGemScore).where(
                    and_(
                        HiddenGemScore.entity_type == emb.entity_type,
                        HiddenGemScore.entity_id == emb.entity_id,
                    )
                )
                existing_result = await self.db.execute(existing_stmt)
                existing = existing_result.scalar_one_or_none()

                if existing:
                    existing.avg_similarity_to_popular = avg_similarity
                    existing.popularity_score = popularity_score
                    existing.circulation_count = circ_count
                    existing.gem_score = gem_score
                    existing.last_calculated_at = datetime.now(timezone.utc)
                    existing.title = title
                    existing.author = author
                    existing.subjects = subjects
                else:
                    new_gem = HiddenGemScore(
                        entity_type=emb.entity_type,
                        entity_id=emb.entity_id,
                        source_collection=emb.source_collection,
                        title=title,
                        author=author,
                        subjects=subjects,
                        avg_similarity_to_popular=avg_similarity,
                        popularity_score=popularity_score,
                        circulation_count=circ_count,
                        gem_score=gem_score,
                        last_calculated_at=datetime.now(timezone.utc),
                    )
                    self.db.add(new_gem)

                processed += 1

                if processed % batch_size == 0:
                    await self.db.commit()
                    logger.info(f"Gem scores: processed {processed}")

            except Exception as e:  # noqa: BLE001 - batch rebuild must skip one bad author, not die
                logger.error(
                    f"Error calculating gem score for {emb.entity_type}:{emb.entity_id}: {e}",
                    extra={
                        "error_type": type(e).__name__,
                        "entity_type": emb.entity_type,
                        "entity_id": emb.entity_id,
                    },
                )
                errors += 1

        await self.db.commit()
        elapsed_ms = (time.time() - start_time) * 1000

        return {
            "processed": processed,
            "errors": errors,
            "elapsed_ms": round(elapsed_ms, 2),
        }

    # =========================================================================
    # Author-to-Author Similarity
    # =========================================================================

    async def find_similar_authors(
        self,
        author_name: str,
        limit: int = 10,
    ) -> dict[str, Any]:
        start_time = time.time()
        normalized = author_name.strip().lower()

        # Get or create the author embedding
        author_emb = await self._get_or_build_author_embedding(normalized, author_name)

        if not author_emb or author_emb.embedding is None:
            return {
                "author": author_name,
                "similar_authors": [],
                "error": "Could not generate author embedding",
                "search_time_ms": (time.time() - start_time) * 1000,
            }

        # Find nearest author embeddings using pgvector
        distance_expr = AuthorEmbedding.embedding.cosine_distance(list(author_emb.embedding))
        similarity_expr = (literal_column("1") - distance_expr).label("similarity")

        stmt = (
            select(
                AuthorEmbedding.author_name,
                AuthorEmbedding.book_count,
                AuthorEmbedding.source_collections,
                AuthorEmbedding.genres,
                AuthorEmbedding.subjects,
                similarity_expr,
            )
            .where(
                and_(
                    AuthorEmbedding.is_generated == True,
                    AuthorEmbedding.author_name_normalized != normalized,
                )
            )
            .order_by(distance_expr.asc())
            .limit(limit)
        )

        result = await self.db.execute(stmt)
        rows = result.all()

        similar_authors = []
        for row in rows:
            similar_authors.append({
                "author_name": row.author_name,
                "book_count": row.book_count,
                "source_collections": row.source_collections or [],
                "genres": row.genres or [],
                "shared_subjects": self._find_shared_subjects(
                    author_emb.subjects or [], row.subjects or []
                ),
                "similarity_score": round(float(row.similarity), 4),
            })

        search_time_ms = (time.time() - start_time) * 1000

        return {
            "author": author_name,
            "author_book_count": author_emb.book_count,
            "author_genres": author_emb.genres or [],
            "similar_authors": similar_authors,
            "search_time_ms": round(search_time_ms, 2),
        }

    async def rebuild_author_embeddings(
        self, batch_size: int = 100
    ) -> dict[str, Any]:
        start_time = time.time()
        processed = 0
        errors = 0

        # Get all unique authors with embeddings
        authors_stmt = (
            select(
                func.lower(func.trim(
                    # For catalog items, use text_content to extract author
                    # but we can also query from catalog_items
                    CatalogItem.author
                )).label("author_norm"),
                CatalogItem.author,
                func.count().label("book_count"),
            )
            .where(CatalogItem.author.isnot(None))
            .group_by(func.lower(func.trim(CatalogItem.author)), CatalogItem.author)
            .having(func.count() >= 2)  # Only authors with 2+ books
        )

        result = await self.db.execute(authors_stmt)
        authors = result.all()

        for row in authors:
            try:
                author_normalized = row.author_norm
                author_name = row.author

                await self._build_single_author_embedding(
                    author_normalized, author_name
                )
                processed += 1

                if processed % batch_size == 0:
                    await self.db.commit()
                    logger.info(f"Author embeddings: processed {processed}")

            except Exception as e:  # noqa: BLE001 - batch rebuild must skip one bad author, not die
                logger.error(
                    f"Error building author embedding for {row.author}: {e}",
                    extra={
                        "error_type": type(e).__name__,
                        "author": row.author if hasattr(row, 'author') else "unknown",
                    },
                )
                errors += 1

        await self.db.commit()
        elapsed_ms = (time.time() - start_time) * 1000

        return {
            "processed": processed,
            "errors": errors,
            "elapsed_ms": round(elapsed_ms, 2),
        }

    # =========================================================================
    # Private Helpers
    # =========================================================================

    async def _get_popular_embeddings(
        self, source_collection: Optional[str], top_n: int = 50
    ) -> list[TextEmbedding]:
        # For now, get random sample of items with embeddings
        # In production, this would join with checkout/download counts
        stmt = (
            select(TextEmbedding)
            .where(
                and_(
                    TextEmbedding.is_generated == True,
                    TextEmbedding.entity_type.in_([
                        "catalog_item_combined", "gutenberg_combined"
                    ]),
                )
            )
            .limit(top_n)
        )
        if source_collection:
            stmt = stmt.where(TextEmbedding.source_collection == source_collection)

        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def _get_circulation_count(
        self, entity_type: str, entity_id: int, source_collection: str
    ) -> int:
        if source_collection == "gutenberg" or "gutenberg" in entity_type:
            stmt = select(GutenbergBook.download_count).where(
                GutenbergBook.id == entity_id
            )
            result = await self.db.execute(stmt)
            count = result.scalar()
            return count or 0

        # For local items, count checkouts
        from ..models.circulation import Checkout
        stmt = select(func.count(Checkout.id)).where(Checkout.item_id == entity_id)
        result = await self.db.execute(stmt)
        return result.scalar() or 0

    async def _get_item_metadata(
        self, entity_type: str, entity_id: int, source_collection: str
    ) -> tuple[str, Optional[str], Optional[list]]:
        if source_collection == "gutenberg" or "gutenberg" in entity_type:
            stmt = select(GutenbergBook).where(GutenbergBook.id == entity_id)
            result = await self.db.execute(stmt)
            book = result.scalar_one_or_none()
            if book:
                authors_str = ""
                if book.authors:
                    try:
                        al = json.loads(book.authors) if isinstance(book.authors, str) else book.authors
                        authors_str = ", ".join(a.get("name", "") for a in al)
                    except (ValueError, TypeError) as e:
                        logger.warning("Failed to parse authors JSON for book %s: %s", book.id, e)
                subjects = None
                if book.subjects:
                    try:
                        subjects = json.loads(book.subjects) if isinstance(book.subjects, str) else book.subjects
                    except (ValueError, TypeError) as e:
                        logger.warning("Failed to parse subjects JSON for book %s: %s", book.id, e)
                return book.title, authors_str, subjects
            return "Unknown", None, None

        stmt = select(CatalogItem).where(CatalogItem.id == entity_id)
        result = await self.db.execute(stmt)
        item = result.scalar_one_or_none()
        if item:
            subjects = None
            if item.subjects:
                if isinstance(item.subjects, str):
                    subjects = [s.strip() for s in item.subjects.split(",")]
                elif isinstance(item.subjects, list):
                    subjects = item.subjects
            return item.title, item.author, subjects
        return "Unknown", None, None

    async def _get_or_build_author_embedding(
        self, normalized: str, display_name: str
    ) -> Optional[AuthorEmbedding]:
        stmt = select(AuthorEmbedding).where(
            AuthorEmbedding.author_name_normalized == normalized
        )
        result = await self.db.execute(stmt)
        existing = result.scalar_one_or_none()

        if existing and existing.is_generated:
            return existing

        return await self._build_single_author_embedding(normalized, display_name)

    async def _build_single_author_embedding(
        self, normalized: str, display_name: str
    ) -> Optional[AuthorEmbedding]:
        # Find all books for this author (IDs + subjects in one query)
        books_stmt = (
            select(CatalogItem.id, CatalogItem.subjects)
            .where(func.lower(func.trim(CatalogItem.author)) == normalized)
        )
        books_result = await self.db.execute(books_stmt)
        books_rows = books_result.all()

        if not books_rows:
            return None

        book_ids = [row.id for row in books_rows]

        # Get embeddings for these books
        emb_stmt = (
            select(TextEmbedding.embedding)
            .where(
                and_(
                    TextEmbedding.entity_id.in_(book_ids),
                    TextEmbedding.entity_type == "catalog_item_combined",
                    TextEmbedding.is_generated == True,
                )
            )
        )
        emb_result = await self.db.execute(emb_stmt)
        embeddings = [row[0] for row in emb_result.all() if row[0] is not None]

        if not embeddings:
            return None

        # Compute centroid
        vectors = np.array([list(e) for e in embeddings])
        centroid = np.mean(vectors, axis=0).tolist()

        # Extract subjects from the already-fetched book rows
        all_subjects = set()
        for row in books_rows:
            if row.subjects:
                if isinstance(row.subjects, str):
                    for s in row.subjects.split(","):
                        all_subjects.add(s.strip())
                elif isinstance(row.subjects, list):
                    all_subjects.update(row.subjects)

        # Upsert author embedding
        stmt = select(AuthorEmbedding).where(
            AuthorEmbedding.author_name_normalized == normalized
        )
        result = await self.db.execute(stmt)
        author_emb = result.scalar_one_or_none()

        if author_emb:
            author_emb.embedding = centroid
            author_emb.is_generated = True
            author_emb.generated_at = datetime.now(timezone.utc)
            author_emb.book_count = len(book_ids)
            author_emb.subjects = list(all_subjects) if all_subjects else None
            author_emb.source_collections = ["local"]
        else:
            author_emb = AuthorEmbedding(
                author_name=display_name,
                author_name_normalized=normalized,
                embedding=centroid,
                book_count=len(book_ids),
                subjects=list(all_subjects) if all_subjects else None,
                source_collections=["local"],
                is_generated=True,
                generated_at=datetime.now(timezone.utc),
            )
            self.db.add(author_emb)

        await self.db.commit()
        return author_emb

    def _find_shared_subjects(
        self, subjects_a: list, subjects_b: list
    ) -> list[str]:
        if not subjects_a or not subjects_b:
            return []
        set_a = {s.lower().strip() for s in subjects_a if isinstance(s, str)}
        set_b = {s.lower().strip() for s in subjects_b if isinstance(s, str)}
        return sorted(set_a & set_b)


def get_discovery_service(db: AsyncSession) -> DiscoveryService:
    return DiscoveryService(db)

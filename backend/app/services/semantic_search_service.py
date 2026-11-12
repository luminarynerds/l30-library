# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

import hashlib
import asyncio
from app.core.logging import get_logger
import time
import json
from datetime import datetime, timedelta, timezone
from typing import Optional, Any

import httpx
from sqlalchemy import select, func, and_, text, literal_column
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.embeddings import (
    TextEmbedding, EmbeddingMetadata, SemanticSearchCache,
    EmbeddingEntityType, EmbeddingStatus, EMBEDDING_DIM,
)
from ..models.catalog import CatalogItem
from ..models.gutenberg import GutenbergBook
from ..models.library_document import LibraryDocument, LibraryDocumentChunk
from ..core.config import get_settings
from app.core.datetime_utils import utc_now

logger = get_logger(__name__)


class SemanticSearchService:

    def __init__(self, db: AsyncSession):
        self.db = db
        self.settings = get_settings()
        self.embedding_api_url = self.settings.embedding_api_url
        self.embedding_model = self.settings.embedding_model
        self.embedding_dimension = self.settings.embedding_dimension
        from ..core.cache_strategies import CacheTTL
        self.cache_ttl_seconds = CacheTTL.DAILY  # 24 hours

    # =========================================================================
    # Embedding Generation
    # =========================================================================

    def _build_headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.settings.openai_api_key:
            headers["Authorization"] = f"Bearer {self.settings.openai_api_key}"
        return headers

    def _apply_task_prefix(self, text: str, input_type: str) -> str:
        # nomic-embed-text is trained with task prefixes; without them retrieval
        # quality degrades. Other providers (e.g. OpenAI) expect no prefix, so gate on model.
        if "nomic" not in self.embedding_model.lower():
            return text
        prefix = "search_query: " if input_type == "query" else "search_document: "
        return f"{prefix}{text}"

    async def generate_embedding(self, text: str, input_type: str = "document") -> Optional[list[float]]:
        try:
            text = text[:32000].strip()
            if not text:
                return None
            text = self._apply_task_prefix(text, input_type)

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    self.embedding_api_url,
                    headers=self._build_headers(),
                    json={
                        "model": self.embedding_model,
                        "input": text,
                    },
                )
                response.raise_for_status()
                data = response.json()
                return data["data"][0]["embedding"]

        except Exception as e:  # noqa: BLE001 - external embedding API boundary: catches httpx errors, JSON parse failures, and KeyError on malformed response shape; returns None so caller can skip this text
            logger.error(f"Failed to generate embedding: {e}")
            return None

    async def generate_embeddings_batch_api(
        self, texts: list[str], input_type: str = "document"
    ) -> list[Optional[list[float]]]:
        try:
            cleaned = [self._apply_task_prefix(t[:32000].strip(), input_type) for t in texts]
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    self.embedding_api_url,
                    headers=self._build_headers(),
                    json={
                        "model": self.embedding_model,
                        "input": cleaned,
                    },
                )
                response.raise_for_status()
                data = response.json()
                # API returns embeddings sorted by index
                result = [None] * len(texts)
                for item in data["data"]:
                    result[item["index"]] = item["embedding"]
                return result

        except Exception as e:  # noqa: BLE001 - external embedding API boundary: catches httpx errors, JSON parse failures, and KeyError on malformed batch response; returns [None]*n so caller can skip failures item-by-item
            logger.error(f"Batch embedding generation failed: {e}")
            return [None] * len(texts)

    # =========================================================================
    # Core Semantic Search (pgvector cosine distance)
    # =========================================================================

    async def search_semantic(
        self,
        query: str,
        limit: int = 50,
        offset: int = 0,
        entity_types: Optional[list[str]] = None,
        source_collections: Optional[list[str]] = None,
        min_similarity: float = 0.3,
    ) -> dict[str, Any]:
        start_time = time.time()

        # Check cache
        cache_key = f"{query}|{json.dumps(entity_types)}|{json.dumps(source_collections)}"
        cached = await self._get_cached_search(cache_key, "semantic")
        if cached:
            cached["was_cached"] = True
            return cached

        # Generate query embedding
        query_embedding = await self.generate_embedding(query, input_type="query")
        if not query_embedding:
            return {
                "query": query,
                "results": [],
                "total_results": 0,
                "error": "Failed to generate query embedding",
                "search_time_ms": (time.time() - start_time) * 1000,
            }

        embedding_time_ms = (time.time() - start_time) * 1000

        # Build pgvector similarity query
        # <=> is cosine distance operator (1 - cosine_similarity)
        distance_expr = TextEmbedding.embedding.cosine_distance(query_embedding)
        similarity_expr = (literal_column("1") - distance_expr).label("similarity")

        query_stmt = (
            select(
                TextEmbedding.id,
                TextEmbedding.entity_type,
                TextEmbedding.entity_id,
                TextEmbedding.source_collection,
                TextEmbedding.text_content,
                similarity_expr,
            )
            .where(TextEmbedding.is_generated == True)
        )

        # Apply entity type filter
        if entity_types:
            query_stmt = query_stmt.where(TextEmbedding.entity_type.in_(entity_types))
        else:
            query_stmt = query_stmt.where(
                TextEmbedding.entity_type.in_([
                    "catalog_item_combined", "catalog_item_title",
                    "gutenberg_combined",
                    "library_document",
                ])
            )

        # Apply source collection filter
        if source_collections:
            query_stmt = query_stmt.where(
                TextEmbedding.source_collection.in_(source_collections)
            )

        # Filter by minimum similarity and order
        query_stmt = (
            query_stmt
            .where(text("1 - (embedding <=> :qe) >= :min_sim"))
            .order_by(distance_expr.asc())
            .limit(limit + offset)
        )

        result = await self.db.execute(
            query_stmt,
            {"qe": str(query_embedding), "min_sim": min_similarity}
        )
        rows = result.all()

        # Enrich results with catalog item details
        enriched = await self._enrich_search_results(rows[offset:offset + limit])

        search_time_ms = (time.time() - start_time) * 1000

        response = {
            "query": query,
            "results": enriched,
            "total_results": len(rows),
            "search_time_ms": round(search_time_ms, 2),
            "embedding_time_ms": round(embedding_time_ms, 2),
            "was_cached": False,
        }

        await self._cache_search(cache_key, response, "semantic")
        return response

    async def search_hybrid(
        self,
        query: str,
        limit: int = 50,
        offset: int = 0,
        semantic_weight: float = 0.6,
        keyword_weight: float = 0.4,
        source_collections: Optional[list[str]] = None,
    ) -> dict[str, Any]:
        start_time = time.time()

        # Run both searches in parallel
        semantic_task = self.search_semantic(
            query, limit=limit * 2, offset=0,
            source_collections=source_collections,
        )
        keyword_task = self._keyword_search(query, limit=limit * 2, offset=0)

        semantic_results, keyword_results = await asyncio.gather(
            semantic_task, keyword_task
        )

        # Merge with reciprocal rank fusion
        merged = self._merge_results_rrf(
            semantic_results.get("results", []),
            keyword_results.get("results", []),
            semantic_weight=semantic_weight,
            keyword_weight=keyword_weight,
        )

        total = len(merged)
        paginated = merged[offset:offset + limit]

        search_time_ms = (time.time() - start_time) * 1000

        return {
            "query": query,
            "search_type": "hybrid",
            "results": paginated,
            "total_results": total,
            "semantic_count": len(semantic_results.get("results", [])),
            "keyword_count": len(keyword_results.get("results", [])),
            "search_time_ms": round(search_time_ms, 2),
            "semantic_time_ms": semantic_results.get("search_time_ms", 0),
            "keyword_time_ms": keyword_results.get("search_time_ms", 0),
        }

    async def find_similar_items(
        self,
        item_id: int,
        source: str = "local",
        limit: int = 10,
    ) -> dict[str, Any]:
        start_time = time.time()

        # Get item
        stmt = select(CatalogItem).where(CatalogItem.id == item_id)
        result = await self.db.execute(stmt)
        item = result.scalar_one_or_none()

        if not item:
            return {"error": "Item not found", "similar_items": []}

        # Get or create embedding
        embedding_text = self._build_combined_text(
            item.title, item.author, item.description, item.subjects
        )
        item_embedding = await self._get_or_create_embedding(
            entity_type="catalog_item_combined",
            entity_id=item.id,
            text_content=embedding_text,
            source_collection="local",
        )

        if not item_embedding:
            return {"error": "Could not generate item embedding", "similar_items": []}

        # Find nearest neighbors (excluding the item itself)
        distance_expr = TextEmbedding.embedding.cosine_distance(item_embedding)
        similarity_expr = (literal_column("1") - distance_expr).label("similarity")

        query_stmt = (
            select(
                TextEmbedding.id,
                TextEmbedding.entity_type,
                TextEmbedding.entity_id,
                TextEmbedding.source_collection,
                TextEmbedding.text_content,
                similarity_expr,
            )
            .where(
                and_(
                    TextEmbedding.is_generated == True,
                    TextEmbedding.entity_type.in_([
                        "catalog_item_combined", "gutenberg_combined"
                    ]),
                    # Exclude the source item
                    ~and_(
                        TextEmbedding.entity_id == item_id,
                        TextEmbedding.source_collection == "local",
                    ),
                )
            )
            .order_by(distance_expr.asc())
            .limit(limit)
        )

        result = await self.db.execute(query_stmt)
        rows = result.all()

        similar = await self._enrich_search_results(rows)
        search_time_ms = (time.time() - start_time) * 1000

        return {
            "item_id": item_id,
            "item_title": item.title,
            "similar_items": similar,
            "count": len(similar),
            "search_time_ms": round(search_time_ms, 2),
        }

    # =========================================================================
    # Cross-Collection Search
    # =========================================================================

    async def search_cross_collection(
        self,
        query: str,
        limit: int = 50,
        offset: int = 0,
    ) -> dict[str, Any]:
        return await self.search_semantic(
            query=query,
            limit=limit,
            offset=offset,
            source_collections=["local", "gutenberg"],
        )

    # =========================================================================
    # Batch Embedding Pipeline
    # =========================================================================

    async def generate_embeddings_batch(
        self,
        entity_type: str,
        batch_size: int = 100,
        skip_existing: bool = True,
    ) -> dict[str, Any]:
        logger.info(f"Starting batch embedding generation for {entity_type}")

        metadata = await self._get_or_create_metadata(entity_type)
        metadata.status = "in_progress"
        metadata.started_at = utc_now()
        await self.db.commit()

        try:
            items = await self._get_items_to_embed(entity_type, skip_existing)
            total_items = len(items)

            if total_items == 0:
                metadata.status = "completed"
                metadata.completed_at = utc_now()
                await self.db.commit()
                return {
                    "entity_type": entity_type,
                    "total_items": 0,
                    "embedded_count": 0,
                    "failed_count": 0,
                    "message": "No items to embed",
                }

            embedded_count = 0
            failed_count = 0

            for i in range(0, total_items, batch_size):
                batch = items[i:i + batch_size]

                # Build text content for each item
                texts = []
                for item in batch:
                    text_content = self._build_combined_text(
                        item.get("title", ""),
                        item.get("author"),
                        item.get("description"),
                        item.get("subjects"),
                    )
                    texts.append(text_content)

                # Generate embeddings in a single API call
                embeddings = await self.generate_embeddings_batch_api(texts)

                # Store each embedding
                for j, (item, embedding) in enumerate(zip(batch, embeddings)):
                    try:
                        if embedding is None:
                            failed_count += 1
                            continue

                        text_content = texts[j]
                        text_hash = hashlib.sha256(text_content.encode()).hexdigest()
                        source = item.get("source_collection", "local")

                        # Upsert embedding
                        existing_stmt = select(TextEmbedding).where(
                            and_(
                                TextEmbedding.entity_type == entity_type,
                                TextEmbedding.entity_id == item["id"],
                                TextEmbedding.text_hash == text_hash,
                            )
                        )
                        existing_result = await self.db.execute(existing_stmt)
                        existing = existing_result.scalar_one_or_none()

                        if existing:
                            existing.embedding = embedding
                            existing.is_generated = True
                            existing.generated_at = datetime.now(timezone.utc)
                            existing.source_collection = source
                        else:
                            new_emb = TextEmbedding(
                                entity_type=entity_type,
                                entity_id=item["id"],
                                text_content=text_content,
                                text_hash=text_hash,
                                embedding=embedding,
                                embedding_model=self.embedding_model,
                                embedding_dimension=self.embedding_dimension,
                                is_generated=True,
                                generated_at=datetime.now(timezone.utc),
                                source_collection=source,
                            )
                            self.db.add(new_emb)

                        embedded_count += 1

                    except Exception as e:  # noqa: BLE001 - per-iteration boundary: one item's storage failure must not crash the batch (counted in failed_count for reporting)
                        logger.error(f"Failed to store embedding for item {item['id']}: {e}")
                        failed_count += 1

                await self.db.commit()

                # Update progress
                metadata.embedded_count = embedded_count
                metadata.failed_count = failed_count
                metadata.last_processed_id = batch[-1]["id"]
                await self.db.commit()

                logger.info(
                    f"Batch {i // batch_size + 1}: "
                    f"{embedded_count} success, {failed_count} failed "
                    f"({i + len(batch)}/{total_items})"
                )

                # Rate limit pause between batches
                await asyncio.sleep(0.2)

            metadata.status = "completed"
            metadata.completed_at = utc_now()
            await self.db.commit()

            return {
                "entity_type": entity_type,
                "total_items": total_items,
                "embedded_count": embedded_count,
                "failed_count": failed_count,
                "success_rate": round(embedded_count / total_items * 100, 1) if total_items else 0,
            }

        except Exception as e:
            logger.error(f"Batch embedding failed: {e}")
            metadata.status = "failed"
            metadata.error_message = str(e)
            await self.db.commit()
            raise

    # =========================================================================
    # Private Helpers
    # =========================================================================

    def _build_combined_text(
        self,
        title: str,
        author: Optional[str] = None,
        description: Optional[str] = None,
        subjects: Optional[str] = None,
    ) -> str:
        parts = [title]
        if author:
            parts.append(f"by {author}")
        if description:
            parts.append(description[:2000])
        if subjects:
            if isinstance(subjects, list):
                parts.append("subjects: " + ", ".join(subjects))
            elif isinstance(subjects, str):
                parts.append("subjects: " + subjects)
        return " ".join(parts).strip()

    async def _get_or_create_embedding(
        self,
        entity_type: str,
        entity_id: int,
        text_content: str,
        source_collection: str = "local",
    ) -> Optional[list[float]]:
        text_hash = hashlib.sha256(text_content.encode()).hexdigest()

        stmt = select(TextEmbedding).where(
            and_(
                TextEmbedding.entity_type == entity_type,
                TextEmbedding.entity_id == entity_id,
                TextEmbedding.text_hash == text_hash,
                TextEmbedding.is_generated == True,
            )
        )
        result = await self.db.execute(stmt)
        existing = result.scalar_one_or_none()

        if existing and existing.embedding is not None:
            return list(existing.embedding)

        embedding = await self.generate_embedding(text_content)
        if not embedding:
            return None

        if existing:
            existing.embedding = embedding
            existing.is_generated = True
            existing.generated_at = utc_now()
        else:
            new_emb = TextEmbedding(
                entity_type=entity_type,
                entity_id=entity_id,
                text_content=text_content,
                text_hash=text_hash,
                embedding=embedding,
                embedding_model=self.embedding_model,
                embedding_dimension=self.embedding_dimension,
                is_generated=True,
                generated_at=utc_now(),
                source_collection=source_collection,
            )
            self.db.add(new_emb)

        await self.db.commit()
        return embedding

    async def _enrich_search_results(
        self, rows: list
    ) -> list[dict[str, Any]]:
        results = []

        for row in rows:
            emb_id, entity_type, entity_id, source_collection, text_content, similarity = row

            item_data = None
            if source_collection == "local" or "catalog_item" in entity_type:
                item_stmt = select(CatalogItem).where(CatalogItem.id == entity_id)
                item_result = await self.db.execute(item_stmt)
                item = item_result.scalar_one_or_none()
                if item:
                    item_data = {
                        "id": f"local:{item.id}",
                        "source": "local",
                        "source_id": str(item.id),
                        "title": item.title,
                        "author": item.author,
                        "description": (item.description or "")[:300],
                        "cover_url": item.cover_url,
                        "format": str(item.item_type) if item.item_type else "book",
                        "subjects": item.subjects,
                        "is_available": item.status and str(item.status) == "available",
                    }

            elif source_collection == "gutenberg" or "gutenberg" in entity_type:
                gb_stmt = select(GutenbergBook).where(GutenbergBook.id == entity_id)
                gb_result = await self.db.execute(gb_stmt)
                gb = gb_result.scalar_one_or_none()
                if gb:
                    authors_str = ""
                    if gb.authors:
                        try:
                            authors_list = json.loads(gb.authors) if isinstance(gb.authors, str) else gb.authors
                            authors_str = ", ".join(a.get("name", "") for a in authors_list)
                        except (json.JSONDecodeError, TypeError):
                            authors_str = str(gb.authors)

                    item_data = {
                        "id": f"gutenberg:{gb.gutenberg_id}",
                        "source": "gutenberg",
                        "source_id": str(gb.gutenberg_id),
                        "title": gb.title,
                        "author": authors_str,
                        "description": "",
                        "cover_url": gb.cover_url,
                        "format": "ebook",
                        "subjects": gb.subjects,
                        "is_available": True,  # Gutenberg books are always available
                    }

            elif source_collection == "document" or entity_type == "library_document":
                chunk_stmt = select(LibraryDocumentChunk).where(
                    LibraryDocumentChunk.id == entity_id
                )
                chunk_result = await self.db.execute(chunk_stmt)
                chunk = chunk_result.scalar_one_or_none()
                if chunk:
                    # Load parent document for metadata
                    doc_stmt = select(LibraryDocument).where(
                        LibraryDocument.id == chunk.document_id
                    )
                    doc_result = await self.db.execute(doc_stmt)
                    doc = doc_result.scalar_one_or_none()
                    if doc:
                        item_data = {
                            "id": f"document:{chunk.id}",
                            "source": "document",
                            "source_id": str(chunk.id),
                            "title": doc.title,
                            "author": None,
                            "description": chunk.chunk_text[:300],
                            "cover_url": None,
                            "format": doc.document_type,
                            "subjects": doc.tags,
                            "is_available": True,
                            "document_id": doc.id,
                            "section_title": chunk.section_title,
                            "chunk_index": chunk.chunk_index,
                            "publish_date": doc.publish_date.isoformat() if doc.publish_date else None,
                        }

            if item_data:
                item_data["relevance_score"] = round(float(similarity), 4)
                item_data["similarity_score"] = round(float(similarity), 4)
                item_data["search_confidence"] = (
                    "high" if similarity > 0.7
                    else "medium" if similarity > 0.5
                    else "low"
                )
                item_data["matched_by"] = "semantic"
                results.append(item_data)

        return results

    async def _keyword_search(
        self,
        query: str,
        limit: int,
        offset: int,
    ) -> dict[str, Any]:
        start_time = time.time()

        from .unified_search_service import UnifiedSearchService
        unified_service = UnifiedSearchService(self.db)
        result = await unified_service.search(query, limit=limit, offset=offset)

        results = []
        for item in result.results:
            results.append({
                "id": item.id,
                "source": str(item.source),
                "source_id": item.source_id,
                "title": item.title,
                "author": item.author,
                "description": item.description,
                "cover_url": item.cover_url,
                "format": str(item.format),
                "is_available": item.is_available,
                "relevance_score": item.relevance_score,
                "search_confidence": "high",
                "matched_by": "keyword",
            })

        return {
            "query": query,
            "results": results,
            "search_time_ms": (time.time() - start_time) * 1000,
        }

    def _merge_results_rrf(
        self,
        semantic_results: list[dict],
        keyword_results: list[dict],
        semantic_weight: float = 0.6,
        keyword_weight: float = 0.4,
        k: int = 60,
    ) -> list[dict]:
        seen = {}

        for i, result in enumerate(semantic_results):
            key = f"{result.get('source', 'unknown')}:{result.get('source_id', i)}"
            seen[key] = {
                **result,
                "rrf_score": (1 / (k + i)) * semantic_weight,
                "matched_by": "semantic",
            }

        for i, result in enumerate(keyword_results):
            key = f"{result.get('source', 'unknown')}:{result.get('source_id', i)}"
            if key in seen:
                seen[key]["rrf_score"] += (1 / (k + i)) * keyword_weight
                seen[key]["matched_by"] = "both"
            else:
                seen[key] = {
                    **result,
                    "rrf_score": (1 / (k + i)) * keyword_weight,
                    "matched_by": "keyword",
                }

        merged = sorted(seen.values(), key=lambda x: x["rrf_score"], reverse=True)
        return merged

    async def _get_cached_search(
        self, query: str, search_type: str
    ) -> Optional[dict[str, Any]]:
        query_hash = hashlib.sha256(query.encode()).hexdigest()
        stmt = select(SemanticSearchCache).where(
            and_(
                SemanticSearchCache.query_hash == query_hash,
                SemanticSearchCache.search_type == search_type,
                SemanticSearchCache.expires_at > utc_now(),
            )
        )
        result = await self.db.execute(stmt)
        cache = result.scalar_one_or_none()
        if cache:
            cache.hit_count += 1
            await self.db.commit()
            return cache.results_json
        return None

    async def _cache_search(
        self, query: str, results: dict[str, Any], search_type: str
    ) -> None:
        query_hash = hashlib.sha256(query.encode()).hexdigest()
        cache = SemanticSearchCache(
            query_hash=query_hash,
            query_text=query[:500],
            search_type=search_type,
            results_count=len(results.get("results", [])),
            results_json=results,
            search_time_ms=results.get("search_time_ms", 0),
            expires_at=utc_now() + timedelta(seconds=self.cache_ttl_seconds),
        )
        self.db.add(cache)
        try:
            await self.db.commit()
        except SQLAlchemyError:
            await self.db.rollback()

    async def _get_or_create_metadata(self, entity_type: str) -> EmbeddingMetadata:
        stmt = select(EmbeddingMetadata).where(
            EmbeddingMetadata.entity_type == entity_type
        )
        result = await self.db.execute(stmt)
        metadata = result.scalar_one_or_none()

        if not metadata:
            if "catalog_item" in entity_type:
                count_stmt = select(func.count(CatalogItem.id))
                count_result = await self.db.execute(count_stmt)
                total = count_result.scalar() or 0
            elif "gutenberg" in entity_type:
                count_stmt = select(func.count(GutenbergBook.id))
                count_result = await self.db.execute(count_stmt)
                total = count_result.scalar() or 0
            elif entity_type == "library_document":
                count_stmt = select(func.count(LibraryDocumentChunk.id))
                count_result = await self.db.execute(count_stmt)
                total = count_result.scalar() or 0
            else:
                total = 0

            metadata = EmbeddingMetadata(
                entity_type=entity_type,
                total_count=total,
            )
            self.db.add(metadata)
            await self.db.commit()

        return metadata

    async def _get_items_to_embed(
        self, entity_type: str, skip_existing: bool
    ) -> list[dict[str, Any]]:
        if "catalog_item" in entity_type:
            stmt = select(CatalogItem)
            if skip_existing:
                # Subquery: IDs that already have embeddings
                embedded_ids = (
                    select(TextEmbedding.entity_id)
                    .where(
                        and_(
                            TextEmbedding.entity_type == entity_type,
                            TextEmbedding.is_generated == True,
                        )
                    )
                    .scalar_subquery()
                )
                stmt = stmt.where(~CatalogItem.id.in_(embedded_ids))

            result = await self.db.execute(stmt)
            items = result.scalars().all()
            return [
                {
                    "id": item.id,
                    "title": item.title,
                    "author": item.author,
                    "description": item.description,
                    "subjects": item.subjects,
                    "source_collection": "local",
                }
                for item in items
            ]

        elif "gutenberg" in entity_type:
            stmt = select(GutenbergBook)
            if skip_existing:
                embedded_ids = (
                    select(TextEmbedding.entity_id)
                    .where(
                        and_(
                            TextEmbedding.entity_type == entity_type,
                            TextEmbedding.is_generated == True,
                        )
                    )
                    .scalar_subquery()
                )
                stmt = stmt.where(~GutenbergBook.id.in_(embedded_ids))

            result = await self.db.execute(stmt.limit(10000))
            books = result.scalars().all()
            items = []
            for book in books:
                authors_str = ""
                if book.authors:
                    try:
                        authors_list = json.loads(book.authors) if isinstance(book.authors, str) else book.authors
                        authors_str = ", ".join(a.get("name", "") for a in authors_list)
                    except (json.JSONDecodeError, TypeError) as e:
                        logger.warning("Failed to parse Gutenberg authors JSON in semantic search: %s", e)
                items.append({
                    "id": book.id,
                    "title": book.title,
                    "author": authors_str,
                    "description": "",
                    "subjects": book.subjects,
                    "source_collection": "gutenberg",
                })
            return items

        elif entity_type == "library_document":
            # Library document chunks — each chunk gets its own embedding
            stmt = select(LibraryDocumentChunk)
            if skip_existing:
                embedded_ids = (
                    select(TextEmbedding.entity_id)
                    .where(
                        and_(
                            TextEmbedding.entity_type == "library_document",
                            TextEmbedding.is_generated == True,
                        )
                    )
                    .scalar_subquery()
                )
                stmt = stmt.where(~LibraryDocumentChunk.id.in_(embedded_ids))

            result = await self.db.execute(stmt)
            chunks = result.scalars().all()

            # Pre-load parent document titles for context
            doc_ids = list({c.document_id for c in chunks})
            doc_map = {}
            if doc_ids:
                doc_stmt = select(LibraryDocument).where(LibraryDocument.id.in_(doc_ids))
                doc_result = await self.db.execute(doc_stmt)
                for doc in doc_result.scalars().all():
                    doc_map[doc.id] = doc

            items = []
            for chunk in chunks:
                doc = doc_map.get(chunk.document_id)
                doc_title = doc.title if doc else "Unknown Document"
                doc_type = doc.document_type if doc else "other"
                # Prefix chunk with document context for richer embedding
                context_prefix = f"{doc_title} ({doc_type})"
                if chunk.section_title:
                    context_prefix += f" - {chunk.section_title}"
                items.append({
                    "id": chunk.id,
                    "title": context_prefix,
                    "author": None,
                    "description": chunk.chunk_text,
                    "subjects": doc.tags if doc and doc.tags else None,
                    "source_collection": "document",
                })
            return items

        return []


def get_semantic_search_service(db: AsyncSession) -> SemanticSearchService:
    return SemanticSearchService(db)

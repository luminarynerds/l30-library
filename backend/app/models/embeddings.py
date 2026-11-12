# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from datetime import datetime, timezone
from enum import StrEnum
from typing import Optional

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import relationship
from pgvector.sqlalchemy import Vector

from ..core.database import Base


class EmbeddingEntityType(StrEnum):
    CATALOG_ITEM_TITLE = "catalog_item_title"
    CATALOG_ITEM_AUTHOR = "catalog_item_author"
    CATALOG_ITEM_DESCRIPTION = "catalog_item_description"
    CATALOG_ITEM_COMBINED = "catalog_item_combined"
    CATALOG_ITEM_SUBJECT = "catalog_item_subject"
    GUTENBERG_COMBINED = "gutenberg_combined"
    LIBRARY_DOCUMENT = "library_document"
    AUTHOR_PROFILE = "author_profile"
    REVIEW_TEXT = "review_text"
    ANNOTATION = "annotation"
    SEARCH_QUERY = "search_query"


class SearchType(StrEnum):
    SEMANTIC = "semantic"
    HYBRID = "hybrid"
    KEYWORD = "keyword"


class EmbeddingStatus(StrEnum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    PARTIAL = "partial"


# Embedding dimension - configurable via EMBEDDING_DIMENSION env var
# Default 1536 matches OpenAI text-embedding-3-small.
# For Ollama models: nomic-embed-text=768, mxbai-embed-large=1024, all-minilm=384
import os
EMBEDDING_DIM = int(os.environ.get("EMBEDDING_DIMENSION", "1536"))


class TextEmbedding(Base):
    __tablename__ = "text_embeddings"

    id = Column(Integer, primary_key=True, index=True)

    # Entity reference
    entity_type = Column(String(50), nullable=False, index=True)
    entity_id = Column(Integer, nullable=False, index=True)

    # Source collection for cross-collection search
    source_collection = Column(String(30), nullable=False, default="local", index=True)

    # Text content
    text_content = Column(Text, nullable=False)
    text_hash = Column(String(64), nullable=False, index=True)  # SHA256

    # Vector embedding - real pgvector Vector column
    embedding = Column(Vector(EMBEDDING_DIM), nullable=True)
    embedding_model = Column(String(100), nullable=False, default="text-embedding-3-small")
    embedding_dimension = Column(Integer, nullable=False, default=EMBEDDING_DIM)

    # Status tracking
    is_generated = Column(Boolean, nullable=False, default=False, index=True)
    generated_at = Column(DateTime(timezone=True), nullable=True)
    error_message = Column(Text, nullable=True)
    retry_count = Column(Integer, nullable=False, default=0)

    # Timestamps, server_default=func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint("entity_type", "entity_id", "text_hash", name="unique_entity_embedding"),
        # HNSW index for fast approximate nearest neighbor search (cosine distance)
        Index(
            "ix_text_embeddings_hnsw_cosine",
            embedding,
            postgresql_using="hnsw",
            postgresql_with={"m": 16, "ef_construction": 64},
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
        # Composite index for filtered searches by entity_type + source
        Index("ix_text_embeddings_type_source", "entity_type", "source_collection"),
        Index("ix_text_embeddings_generated", "is_generated", "entity_type"),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "entity_type": self.entity_type,
            "entity_id": self.entity_id,
            "source_collection": self.source_collection,
            "text_content": self.text_content,
            "is_generated": self.is_generated,
            "generated_at": self.generated_at,
            "embedding_model": self.embedding_model,
            "embedding_dimension": self.embedding_dimension,
        }


class AuthorEmbedding(Base):
    __tablename__ = "author_embeddings"

    id = Column(Integer, primary_key=True, index=True)

    # Author identity (normalized lowercase)
    author_name = Column(String(255), nullable=False, index=True)
    author_name_normalized = Column(String(255), nullable=False, unique=True, index=True)

    # Aggregated embedding (centroid of all book embeddings)
    embedding = Column(Vector(EMBEDDING_DIM), nullable=True)
    embedding_model = Column(String(100), nullable=False, default="text-embedding-3-small")

    # Metadata for the aggregation
    book_count = Column(Integer, nullable=False, default=0)
    source_collections = Column(JSON, nullable=True)  # ["local", "gutenberg", "palace_project"]
    genres = Column(JSON, nullable=True)  # ["fiction", "mystery", "science fiction"]
    subjects = Column(JSON, nullable=True)  # ["space exploration", "robots"]

    # Status
    is_generated = Column(Boolean, nullable=False, default=False, index=True)
    generated_at = Column(DateTime(timezone=True), nullable=True)

    # Timestamps, server_default=func.now(), nullable=False)

    __table_args__ = (
        Index(
            "ix_author_embeddings_hnsw_cosine",
            embedding,
            postgresql_using="hnsw",
            postgresql_with={"m": 16, "ef_construction": 64},
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "author_name": self.author_name,
            "book_count": self.book_count,
            "source_collections": self.source_collections,
            "genres": self.genres,
            "subjects": self.subjects,
            "is_generated": self.is_generated,
        }


class HiddenGemScore(Base):
    __tablename__ = "hidden_gem_scores"

    id = Column(Integer, primary_key=True, index=True)

    # Entity reference (catalog_item, gutenberg_book, etc.)
    entity_type = Column(String(50), nullable=False, index=True)
    entity_id = Column(Integer, nullable=False, index=True)
    source_collection = Column(String(30), nullable=False, default="local", index=True)

    # Book metadata snapshot for fast display
    title = Column(String(500), nullable=False)
    author = Column(String(255), nullable=True)
    subjects = Column(JSON, nullable=True)

    # Scoring components
    avg_similarity_to_popular = Column(Float, nullable=False, default=0.0)
    popularity_score = Column(Float, nullable=False, default=0.0)  # normalized 0-1
    circulation_count = Column(Integer, nullable=False, default=0)
    gem_score = Column(Float, nullable=False, default=0.0, index=True)  # higher = more hidden gem

    # Recalculation tracking
    last_calculated_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint("entity_type", "entity_id", name="unique_gem_entity"),
        Index("ix_hidden_gems_score_desc", gem_score.desc()),
        Index("ix_hidden_gems_source_score", "source_collection", gem_score.desc()),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "entity_type": self.entity_type,
            "entity_id": self.entity_id,
            "source_collection": self.source_collection,
            "title": self.title,
            "author": self.author,
            "subjects": self.subjects,
            "gem_score": self.gem_score,
            "avg_similarity_to_popular": self.avg_similarity_to_popular,
            "popularity_score": self.popularity_score,
            "circulation_count": self.circulation_count,
        }


class EmbeddingMetadata(Base):
    __tablename__ = "embedding_metadata"

    id = Column(Integer, primary_key=True, index=True)

    # Entity type being embedded
    entity_type = Column(String(50), nullable=False, index=True, unique=True)

    # Progress tracking
    total_count = Column(Integer, nullable=False)
    embedded_count = Column(Integer, nullable=False, default=0)
    failed_count = Column(Integer, nullable=False, default=0)
    last_processed_id = Column(Integer, nullable=True)

    # Status
    status = Column(String(20), nullable=False, default="pending", index=True)

    # Timing
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    error_message = Column(Text, nullable=True)

    # Timestamps, server_default=func.now())

    @property
    def progress_percent(self) -> float:
        if self.total_count == 0:
            return 0.0
        return round((self.embedded_count / self.total_count) * 100, 2)

    def to_dict(self):
        return {
            "id": self.id,
            "entity_type": self.entity_type,
            "total_count": self.total_count,
            "embedded_count": self.embedded_count,
            "failed_count": self.failed_count,
            "progress_percent": self.progress_percent,
            "status": self.status,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
        }


class SemanticSearchCache(Base):
    __tablename__ = "semantic_search_cache"

    id = Column(Integer, primary_key=True, index=True)

    # Query information
    query_hash = Column(String(64), nullable=False, index=True)  # SHA256
    query_text = Column(Text, nullable=False)
    search_type = Column(String(20), nullable=False, default="semantic")

    # Results
    results_count = Column(Integer, nullable=False)
    results_json = Column(JSON, nullable=False)
    search_time_ms = Column(Float, nullable=False)

    # Cache management
    expires_at = Column(DateTime(timezone=True), nullable=False, index=True)
    hit_count = Column(Integer, nullable=False, default=0)

    # Timestamp, server_default=func.now())

    __table_args__ = (
        UniqueConstraint("query_hash", "search_type", name="unique_search_query_cache"),
    )

    def is_expired(self) -> bool:
        return datetime.now(timezone.utc) > self.expires_at

    def to_dict(self):
        return {
            "id": self.id,
            "query_text": self.query_text,
            "search_type": self.search_type,
            "results_count": self.results_count,
            "search_time_ms": self.search_time_ms,
            "hit_count": self.hit_count,
        }

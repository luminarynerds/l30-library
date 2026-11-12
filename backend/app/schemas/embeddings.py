# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field

from app.schemas._base import StrictInputSchema


# ==================== Semantic Search ====================


class SemanticSearchResult(BaseModel):
    id: str
    source: str  # "local", "gutenberg"
    source_id: str
    title: str
    author: Optional[str] = None
    description: Optional[str] = None
    cover_url: Optional[str] = None
    format: str
    subjects: Optional[Any] = None
    is_available: bool = False
    relevance_score: float = Field(..., ge=0.0, le=1.0)
    similarity_score: Optional[float] = Field(None, ge=0.0, le=1.0)
    search_confidence: str = Field(...)  # "high", "medium", "low"
    matched_by: str = Field(...)  # "semantic", "keyword", "both"


class SemanticSearchResponse(BaseModel):
    query: str
    search_type: str = "semantic"
    total_results: int
    results: list[SemanticSearchResult]
    search_time_ms: float
    embedding_time_ms: Optional[float] = None
    was_cached: bool = False
    has_more: bool = False

    class Config:
        from_attributes = True


class HybridSearchResponse(BaseModel):
    query: str
    total_results: int
    semantic_results: list[SemanticSearchResult] = []
    keyword_results: list[SemanticSearchResult] = []
    merged_results: list[SemanticSearchResult]
    search_time_ms: float
    semantic_time_ms: float = 0
    keyword_time_ms: float = 0
    merge_strategy: str = "reciprocal_rank_fusion"
    has_more: bool = False


class CrossCollectionSearchResponse(BaseModel):
    query: str
    total_results: int
    results: list[SemanticSearchResult]
    source_breakdown: dict[str, int] = {}
    search_time_ms: float
    was_cached: bool = False


# ==================== Autocomplete ====================


class AutocompleteSuggestion(BaseModel):
    id: str
    title: str
    author: Optional[str] = None
    format: str
    source: str
    cover_url: Optional[str] = None
    match_type: str  # "prefix", "fuzzy", "author_fuzzy"
    similarity_score: float = Field(..., ge=0.0, le=1.0)


class AutocompleteResponse(BaseModel):
    query: str
    suggestions: list[AutocompleteSuggestion]
    search_time_ms: float
    total_suggestions: int = 0
    strategy: str = "trigram+prefix"


# ==================== Similar Items ====================


class SimilarItemsResponse(BaseModel):
    item_id: str
    item_title: str
    similar_items: list[SemanticSearchResult]
    similarity_metric: str = "cosine_similarity"
    search_time_ms: float


# ==================== Hidden Gem Discovery ====================


class HiddenGemResult(BaseModel):
    entity_type: str
    entity_id: int
    source_collection: str
    title: str
    author: Optional[str] = None
    subjects: Optional[list[str]] = None
    gem_score: float = Field(..., ge=0.0)
    avg_similarity_to_popular: float
    popularity_score: float
    circulation_count: int


class HiddenGemsResponse(BaseModel):
    gems: list[HiddenGemResult]
    total: int
    filters: dict[str, Any] = {}
    search_time_ms: float


# ==================== Author Similarity ====================


class SimilarAuthor(BaseModel):
    author_name: str
    book_count: int
    source_collections: list[str] = []
    genres: list[str] = []
    shared_subjects: list[str] = []
    similarity_score: float = Field(..., ge=0.0, le=1.0)


class SimilarAuthorsResponse(BaseModel):
    author: str
    author_book_count: int = 0
    author_genres: list[str] = []
    similar_authors: list[SimilarAuthor]
    search_time_ms: float


# ==================== Embedding Management ====================


class EmbeddingProgress(BaseModel):
    entity_type: str
    total_count: int
    embedded_count: int
    failed_count: int
    progress_percent: float
    status: str
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    estimated_time_remaining_seconds: Optional[float] = None


class EmbeddingStats(BaseModel):
    total_embeddings: int
    embedded_count: int
    failed_count: int
    pending_count: int
    embedding_coverage_percent: float
    average_embedding_dimension: int
    embedding_model: str
    last_embedding_generated_at: Optional[datetime] = None


class EmbeddingRequest(StrictInputSchema):
    entity_types: list[str] = Field(...)
    batch_size: int = Field(default=100, ge=1, le=1000)
    skip_existing: bool = Field(default=True)


class EmbeddingStatusResponse(BaseModel):
    request_id: str
    started_at: datetime
    status: str
    progress: EmbeddingProgress
    message: Optional[str] = None


class SemanticSuggestion(BaseModel):
    id: str
    title: str
    author: Optional[str] = None
    format: str
    source: str
    similarity_score: float = Field(..., ge=0.0, le=1.0)
    cover_url: Optional[str] = None


class SemanticSuggestionsResponse(BaseModel):
    query: str
    suggestions: list[SemanticSuggestion]
    search_time_ms: float
    was_cached: bool = False


class SearchTypeSelectorResponse(BaseModel):
    available_types: list[dict[str, Any]]
    recommended_type: str
    explanation: str

    class Config:
        from_attributes = True

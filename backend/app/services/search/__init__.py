# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""PostgreSQL-native search service package.

Provides full-text search using tsvector/tsquery with GIN indexes,
trigram similarity for fuzzy matching, and hybrid integration with
pgvector semantic search.
"""

from .search_service import PostgresSearchService
from .search_service_cached import CachedPostgresSearchService, get_cached_search_service as get_search_service

__all__ = ["PostgresSearchService", "CachedPostgresSearchService", "get_search_service"]

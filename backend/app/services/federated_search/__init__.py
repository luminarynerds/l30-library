# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Federated Search — multi-source library catalog search with deduplication.

Provides protocol clients (SRU, Z39.50, local catalog) and an orchestration
service that fans out queries, deduplicates results, and merges metadata.
"""

from .base_client import (
    BaseSearchClient,
    NormalizedSearchResult,
    ProtocolType,
    ServerConfig,
)
from .config_manager import ServerConfigManager, config_manager
from .deduplication import DeduplicationEngine
from .federated_search_service import FederatedSearchService, FederatedSearchResponse
from .local_client import LocalCatalogClient
from .sru_client import SRUClient
from .z3950_client import Z3950Client

__all__ = [
    "BaseSearchClient",
    "NormalizedSearchResult",
    "ProtocolType",
    "ServerConfig",
    "ServerConfigManager",
    "config_manager",
    "DeduplicationEngine",
    "FederatedSearchService",
    "FederatedSearchResponse",
    "LocalCatalogClient",
    "SRUClient",
    "Z3950Client",
]

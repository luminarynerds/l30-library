# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from app.core.logging import get_logger
from typing import Any, List, Optional

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from .base_client import (
    BaseSearchClient,
    NormalizedSearchResult,
    ProtocolType,
    SearchResultType,
    ServerConfig,
)
from ..catalog_search_service import catalog_search_service
from ..catalog_subjects import parse_subjects_field

logger = get_logger(__name__)

# Virtual server config for local catalog
LOCAL_CONFIG = ServerConfig(
    id="local_catalog",
    name="L30 Library",
    host="localhost",
    port=0,
    protocol=ProtocolType.SRU_REST,  # Not really, but needs a value
    database="local",
    timeout_seconds=5,
    max_retries=0,
    description="Local library catalog",
    enabled=True,
)


class LocalCatalogClient(BaseSearchClient):

    def __init__(self, db: AsyncSession, config: Optional[ServerConfig] = None):
        super().__init__(config or LOCAL_CONFIG)
        self.db = db

    async def connect(self) -> None:
        self._connection = True

    async def disconnect(self) -> None:
        self._connection = None

    async def search(
        self,
        query: str,
        max_results: int = 10,
        result_type: SearchResultType = SearchResultType.BIBLIOGRAPHIC,
    ) -> List[NormalizedSearchResult]:
        self._validate_query(query)
        self._log_request(query, max_results)

        try:
            items = await catalog_search_service.advanced_search(
                self.db,
                title=query,
                per_page=max_results,
            )
            results = [self._to_normalized(item) for item in items]
            self._log_response(len(results), 0.0)
            return results
        except SQLAlchemyError as e:
            self.logger.error("Local catalog search failed: %s", e)
            return []

    async def search_by_fields(
        self,
        isbn: Optional[str] = None,
        title: Optional[str] = None,
        author: Optional[str] = None,
        max_results: int = 10,
    ) -> List[NormalizedSearchResult]:
        try:
            items = await catalog_search_service.advanced_search(
                self.db,
                title=title,
                author=author,
                isbn=isbn,
                per_page=max_results,
            )
            return [self._to_normalized(item) for item in items]
        except SQLAlchemyError as e:
            self.logger.error("Local catalog search failed: %s", e)
            return []

    async def _execute_request(self, query: str, max_results: int) -> Any:
        return await catalog_search_service.advanced_search(
            self.db, title=query, per_page=max_results,
        )

    async def _parse_response(self, response: Any) -> List[NormalizedSearchResult]:
        return [self._to_normalized(item) for item in response]

    def _to_normalized(self, item) -> NormalizedSearchResult:
        raw_subjects = getattr(item, "subjects", None)
        subjects = (
            raw_subjects if isinstance(raw_subjects, list)
            else parse_subjects_field(raw_subjects)
        )
        return NormalizedSearchResult(
            source_id="local_catalog",
            source_name=self.config.name,
            protocol=ProtocolType.SRU_REST,
            title=getattr(item, "title", None),
            author=getattr(item, "author", None),
            isbn=getattr(item, "isbn", None),
            publisher=getattr(item, "publisher", None),
            publication_year=getattr(item, "publication_year", None),
            description=getattr(item, "description", None) or getattr(item, "summary", None),
            subjects=subjects,
            lc_classification=getattr(item, "call_number", None),
            dewey_decimal=getattr(item, "dewey_decimal", None),
            edition=getattr(item, "edition", None),
            control_number=str(item.id) if hasattr(item, "id") else None,
            available_count=getattr(item, "available_copies", None),
            total_count=getattr(item, "total_copies", None),
        )

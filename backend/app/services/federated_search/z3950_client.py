# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from app.core.logging import get_logger
from typing import Any, List, Optional

from .base_client import (
    BaseSearchClient,
    ConnectionError,
    NormalizedSearchResult,
    ProtocolType,
    QueryError,
    SearchResultType,
    ServerConfig,
    TimeoutError,
)
from ..z3950_service import z3950_service, Z3950Error

logger = get_logger(__name__)


class Z3950Client(BaseSearchClient):

    def __init__(self, config: ServerConfig):
        super().__init__(config)
        # Map config to z3950_service source name
        self._source = self._resolve_source()

    def _resolve_source(self) -> str:
        host = self.config.host.lower()
        if "loc.gov" in host:
            return "loc"
        if "oclc" in host:
            return "oclc"
        # Default to the config id
        return self.config.id

    async def connect(self) -> None:
        if not z3950_service.available:
            raise ConnectionError(
                "Z39.50 service unavailable (PyZ3950 not installed, SRU fallback may work)"
            )
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
        await self.ensure_connected()
        self._log_request(query, max_results)

        try:
            # Parse structured query if it looks like "field:value" pairs
            isbn, title, author = self._parse_query(query)
            raw_results = await z3950_service.search_combined(
                isbn=isbn, title=title, author=author,
                source=self._source, max_results=max_results,
            )
            results = [self._to_normalized(r) for r in raw_results]
            self._log_response(len(results), 0.0)
            return results
        except Z3950Error as e:
            raise QueryError(f"Z39.50 search error: {e}") from e
        except Exception as e:
            self.logger.error("Z39.50 search failed: %s", e)
            raise ConnectionError(f"Z39.50 search failed: {e}") from e

    async def search_by_fields(
        self,
        isbn: Optional[str] = None,
        title: Optional[str] = None,
        author: Optional[str] = None,
        max_results: int = 10,
    ) -> List[NormalizedSearchResult]:
        await self.ensure_connected()

        try:
            raw_results = await z3950_service.search_combined(
                isbn=isbn, title=title, author=author,
                source=self._source, max_results=max_results,
            )
            return [self._to_normalized(r) for r in raw_results]
        except Z3950Error as e:
            raise QueryError(f"Z39.50 search error: {e}") from e

    async def _execute_request(self, query: str, max_results: int) -> Any:
        isbn, title, author = self._parse_query(query)
        return await z3950_service.search_combined(
            isbn=isbn, title=title, author=author,
            source=self._source, max_results=max_results,
        )

    async def _parse_response(self, response: Any) -> List[NormalizedSearchResult]:
        return [self._to_normalized(r) for r in response]

    def _to_normalized(self, record: dict) -> NormalizedSearchResult:
        return NormalizedSearchResult(
            source_id=self.config.id,
            source_name=self.config.name,
            protocol=ProtocolType.Z3950,
            title=record.get("title"),
            author=record.get("author"),
            isbn=record.get("isbn"),
            publisher=record.get("publisher"),
            publication_year=record.get("publication_year"),
            description=record.get("description"),
            subjects=record.get("subjects", []),
            lc_classification=record.get("lc_call_number"),
            dewey_decimal=record.get("dewey_decimal"),
            edition=record.get("edition"),
            extent=str(record["page_count"]) + " pages" if record.get("page_count") else None,
            control_number=record.get("control_number"),
        )

    @staticmethod
    def _parse_query(query: str) -> tuple:
        isbn = title = author = None

        # Check for field:value syntax
        if "isbn:" in query.lower() or "title:" in query.lower() or "author:" in query.lower():
            import re
            isbn_match = re.search(r"isbn:\s*([^\s]+)", query, re.IGNORECASE)
            title_match = re.search(r'title:\s*"([^"]+)"', query, re.IGNORECASE)
            if not title_match:
                title_match = re.search(r"title:\s*([^\s]+)", query, re.IGNORECASE)
            author_match = re.search(r'author:\s*"([^"]+)"', query, re.IGNORECASE)
            if not author_match:
                author_match = re.search(r"author:\s*([^\s]+)", query, re.IGNORECASE)

            isbn = isbn_match.group(1) if isbn_match else None
            title = title_match.group(1) if title_match else None
            author = author_match.group(1) if author_match else None
        else:
            # Treat as title search
            title = query

        return isbn, title, author

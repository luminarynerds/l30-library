# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

import asyncio
import logging
from app.core.logging import get_logger
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Any, Dict, List, Optional
from app.core.datetime_utils import utc_now

logger = get_logger(__name__)


class ProtocolType(StrEnum):
    Z3950 = "z3950"
    SRU = "sru"
    SRU_SOAP = "sru_soap"
    SRU_REST = "sru_rest"


class SearchResultType(StrEnum):
    BIBLIOGRAPHIC = "bibliographic"
    AUTHORITY = "authority"
    HOLDINGS = "holdings"


@dataclass
class ServerConfig:
    id: str
    name: str
    host: str
    port: int
    protocol: ProtocolType
    database: str
    requires_auth: bool = False
    username: Optional[str] = None
    password: Optional[str] = None
    timeout_seconds: int = 30
    max_retries: int = 3
    encoding: str = "UTF-8"
    description: str = ""
    enabled: bool = True

    def __post_init__(self):
        if not self.host:
            raise ValueError("Server host is required")
        if self.port < 0 or self.port > 65535:
            raise ValueError(f"Invalid port number: {self.port}")
        if self.timeout_seconds < 1:
            raise ValueError("Timeout must be positive")
        if self.max_retries < 0:
            raise ValueError("Max retries cannot be negative")


@dataclass
class NormalizedSearchResult:
    source_id: str
    source_name: str
    protocol: ProtocolType

    # Bibliographic data
    title: Optional[str] = None
    author: Optional[str] = None
    isbn: Optional[str] = None
    issn: Optional[str] = None
    publisher: Optional[str] = None
    publication_year: Optional[int] = None
    publication_date: Optional[str] = None
    description: Optional[str] = None
    subjects: List[str] = None

    # Classification
    lc_classification: Optional[str] = None
    dewey_decimal: Optional[str] = None

    # Physical description
    extent: Optional[str] = None  # e.g., "300 pages"
    language: Optional[str] = None
    physical_description: Optional[str] = None

    # Identifiers
    control_number: Optional[str] = None
    oclc_number: Optional[str] = None

    # Holdings info
    available_count: Optional[int] = None
    total_count: Optional[int] = None

    # Additional metadata
    work_type: Optional[str] = None
    edition: Optional[str] = None
    series: Optional[str] = None

    # Metadata quality indicators
    retrieved_at: datetime = None
    relevance_score: float = 1.0

    # Raw data (for debugging/future processing)
    raw_data: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        if self.subjects is None:
            self.subjects = []
        if self.retrieved_at is None:
            self.retrieved_at = utc_now()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source_id": self.source_id,
            "source_name": self.source_name,
            "protocol": str(self.protocol),
            "title": self.title,
            "author": self.author,
            "isbn": self.isbn,
            "issn": self.issn,
            "publisher": self.publisher,
            "publication_year": self.publication_year,
            "publication_date": self.publication_date,
            "description": self.description,
            "subjects": self.subjects,
            "lc_classification": self.lc_classification,
            "dewey_decimal": self.dewey_decimal,
            "extent": self.extent,
            "language": self.language,
            "physical_description": self.physical_description,
            "control_number": self.control_number,
            "oclc_number": self.oclc_number,
            "available_count": self.available_count,
            "total_count": self.total_count,
            "work_type": self.work_type,
            "edition": self.edition,
            "series": self.series,
            "retrieved_at": self.retrieved_at.isoformat(),
            "relevance_score": self.relevance_score,
        }


class ClientError(Exception):
    pass


class ConnectionError(ClientError):
    pass


class TimeoutError(ClientError):
    pass


class QueryError(ClientError):
    pass


class ParsingError(ClientError):
    pass


class AuthenticationError(ClientError):
    pass


class BaseSearchClient(ABC):

    def __init__(self, config: ServerConfig):
        if not config.enabled:
            raise ValueError(f"Server {config.id} is not enabled")

        self.config = config
        self.logger = logging.getLogger(f"{__name__}.{config.id}")
        self._connection = None
        self._last_query_time: Optional[datetime] = None

    # =========================================================================
    # Abstract Methods - Implementation Required
    # =========================================================================

    @abstractmethod
    async def connect(self) -> None:
        pass

    @abstractmethod
    async def disconnect(self) -> None:
        pass

    @abstractmethod
    async def search(
        self,
        query: str,
        max_results: int = 10,
        result_type: SearchResultType = SearchResultType.BIBLIOGRAPHIC,
    ) -> List[NormalizedSearchResult]:
        pass

    @abstractmethod
    async def _execute_request(self, query: str, max_results: int) -> Any:
        pass

    @abstractmethod
    async def _parse_response(self, response: Any) -> List[NormalizedSearchResult]:
        pass

    # =========================================================================
    # Common Retry Logic
    # =========================================================================

    async def _execute_with_retry(
        self,
        func,
        *args,
        max_retries: Optional[int] = None,
        **kwargs
    ) -> Any:
        max_retries = max_retries or self.config.max_retries
        last_exception = None

        for attempt in range(max_retries + 1):
            try:
                return await func(*args, **kwargs)
            except (ConnectionError, TimeoutError, asyncio.TimeoutError) as e:
                last_exception = e
                if attempt < max_retries:
                    # Exponential backoff: 1s, 2s, 4s, 8s...
                    wait_time = 2 ** attempt
                    self.logger.warning(
                        f"Attempt {attempt + 1}/{max_retries + 1} failed, "
                        f"retrying in {wait_time}s: {e}"
                    )
                    await asyncio.sleep(wait_time)
                else:
                    self.logger.error(
                        f"All {max_retries + 1} attempts failed for {self.config.id}"
                    )
            except QueryError:
                # Don't retry on query errors (syntax issues)
                raise
            except Exception as e:
                last_exception = e
                self.logger.error(f"Unexpected error: {e}", exc_info=True)
                raise

        if last_exception:
            raise last_exception

    # =========================================================================
    # Connection Management
    # =========================================================================

    async def ensure_connected(self) -> None:
        if self._connection is None:
            await self._execute_with_retry(self.connect)

        if not await self._check_connection():
            self.logger.info(f"Reconnecting to {self.config.id}")
            await self.disconnect()
            await self._execute_with_retry(self.connect)

    async def _check_connection(self) -> bool:
        return self._connection is not None

    async def __aenter__(self):
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.disconnect()
        return False

    # =========================================================================
    # Logging and Metrics
    # =========================================================================

    def _log_request(self, query: str, max_results: int) -> None:
        self.logger.debug(
            f"Query on {self.config.id}: {query[:100]} (max_results={max_results})"
        )

    def _log_response(self, result_count: int, elapsed_seconds: float) -> None:
        self.logger.debug(
            f"Retrieved {result_count} results in {elapsed_seconds:.2f}s "
            f"from {self.config.id}"
        )

    # =========================================================================
    # Validation Helpers
    # =========================================================================

    def _validate_query(self, query: str) -> None:
        if not query or not query.strip():
            raise QueryError("Query cannot be empty")

        if len(query) > 1000:
            raise QueryError("Query exceeds maximum length of 1000 characters")

    def _validate_results(self, results: int, max_results: int) -> None:
        if results < 0:
            raise ValueError("Result count cannot be negative")

        if max_results < 1 or max_results > 10000:
            raise ValueError("max_results must be between 1 and 10000")

    # =========================================================================
    # Cleanup
    # =========================================================================

    async def __del__(self):
        try:
            if self._connection is not None:
                await self.disconnect()
        except Exception as e:  # noqa: BLE001  # destructor cleanup must not raise
            self.logger.error(f"Error during cleanup: {e}")

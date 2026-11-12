# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from app.core.logging import get_logger
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Any

import httpx

from ..models.streaming import StreamingContentType, StreamingService

logger = get_logger(__name__)


class StreamingClientError(Exception):

    def __init__(self, message: str, status_code: int | None = None, response_data: dict | None = None):
        self.message = message
        self.status_code = status_code
        self.response_data = response_data
        super().__init__(self.message)


class StreamingAuthError(StreamingClientError):
    pass


class StreamingRateLimitError(StreamingClientError):
    pass


class StreamingNotFoundError(StreamingClientError):
    pass


@dataclass
class StreamingContent:
    external_id: str
    title: str
    content_type: StreamingContentType
    author: str | None = None
    description: str | None = None
    isbn: str | None = None
    duration_minutes: int | None = None
    release_year: int | None = None
    genres: list[str] | None = None
    cover_url: str | None = None
    rating: str | None = None
    is_available: bool = True
    available_until: datetime | None = None
    raw_data: dict | None = None  # Original API response


@dataclass
class StreamingCheckoutResult:
    success: bool
    external_checkout_id: str | None = None
    expires_at: datetime | None = None
    error_message: str | None = None
    access_url: str | None = None


@dataclass
class StreamingPatronInfo:
    external_patron_id: str
    checkouts_this_month: int
    checkout_limit: int
    remaining_checkouts: int


class BaseStreamingClient(ABC):

    def __init__(
        self,
        base_url: str,
        api_key: str | None = None,
        api_secret: str | None = None,
        library_id: str | None = None,
        timeout: float = 30.0,
    ):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.api_secret = api_secret
        self.library_id = library_id
        self.timeout = timeout
        self._client: httpx.AsyncClient | None = None

    @property
    @abstractmethod
    def service(self) -> StreamingService:
        pass

    @property
    @abstractmethod
    def service_name(self) -> str:
        pass

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=self.timeout,
                headers=self._get_default_headers(),
            )
        return self._client

    @abstractmethod
    def _get_default_headers(self) -> dict[str, str]:
        pass

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    async def _make_request(
        self,
        method: str,
        endpoint: str,
        params: dict | None = None,
        json_data: dict | None = None,
        headers: dict | None = None,
    ) -> dict[str, Any]:
        client = await self._get_client()
        request_headers = headers or {}

        try:
            response = await client.request(
                method=method,
                url=endpoint,
                params=params,
                json=json_data,
                headers=request_headers,
            )

            if response.status_code == 401:
                raise StreamingAuthError(
                    "Authentication failed",
                    status_code=response.status_code,
                )

            if response.status_code == 429:
                raise StreamingRateLimitError(
                    "Rate limit exceeded",
                    status_code=response.status_code,
                )

            if response.status_code == 404:
                raise StreamingNotFoundError(
                    "Resource not found",
                    status_code=response.status_code,
                )

            if response.status_code >= 400:
                error_data = None
                try:
                    error_data = response.json()
                except (ValueError, TypeError):
                    logger.debug("Could not parse error response body as JSON for status %s", response.status_code)
                raise StreamingClientError(
                    f"API error: {response.status_code}",
                    status_code=response.status_code,
                    response_data=error_data,
                )

            if response.status_code == 204:
                return {}

            return response.json()

        except httpx.TimeoutException as e:
            logger.error(f"Timeout calling {self.service_name} API: {e}")
            raise StreamingClientError(f"Request timeout: {e}") from e

        except httpx.RequestError as e:
            logger.error(f"Error calling {self.service_name} API: {e}")
            raise StreamingClientError(f"Request failed: {e}") from e

    @abstractmethod
    async def search(
        self,
        query: str,
        content_types: list[StreamingContentType] | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[StreamingContent], int]:
        pass

    @abstractmethod
    async def get_content(self, external_id: str) -> StreamingContent | None:
        pass

    @abstractmethod
    async def checkout(
        self,
        external_id: str,
        patron_barcode: str,
    ) -> StreamingCheckoutResult:
        pass

    @abstractmethod
    async def return_content(
        self,
        external_checkout_id: str,
        patron_barcode: str,
    ) -> bool:
        pass

    @abstractmethod
    async def get_patron_checkouts(
        self,
        patron_barcode: str,
    ) -> list[StreamingContent]:
        pass

    @abstractmethod
    async def get_patron_info(
        self,
        patron_barcode: str,
    ) -> StreamingPatronInfo | None:
        pass

    @abstractmethod
    def get_app_deep_link(self, external_id: str) -> str | None:
        pass

    @abstractmethod
    def get_web_deep_link(self, external_id: str) -> str | None:
        pass

    @abstractmethod
    def _map_content_type(self, raw_type: str) -> StreamingContentType:
        pass

    def _parse_genres(self, genres_data: Any) -> list[str] | None:
        if not genres_data:
            return None
        if isinstance(genres_data, list):
            return [str(g) for g in genres_data]
        if isinstance(genres_data, str):
            return [g.strip() for g in genres_data.split(",")]
        return None

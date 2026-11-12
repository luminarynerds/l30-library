# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

import json
from app.core.logging import get_logger
from dataclasses import dataclass
from datetime import datetime
from typing import Any

import httpx

logger = get_logger(__name__)

# Gutendex API base URL
GUTENDEX_BASE_URL = "https://gutendex.com"


class GutenbergClientError(Exception):

    def __init__(self, message: str, status_code: int | None = None):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)


class GutenbergRateLimitError(GutenbergClientError):
    pass


class GutenbergNotFoundError(GutenbergClientError):
    pass


@dataclass
class GutenbergAuthor:
    name: str
    birth_year: int | None = None
    death_year: int | None = None


@dataclass
class GutenbergBookData:
    id: int
    title: str
    authors: list[GutenbergAuthor]
    subjects: list[str]
    bookshelves: list[str]
    languages: list[str]
    copyright: bool  # True if copyrighted, False if public domain
    media_type: str
    formats: dict[str, str]  # mime_type -> url
    download_count: int

    @property
    def cover_url(self) -> str | None:
        # Try different image format keys
        for key in ["image/jpeg", "image/png"]:
            if key in self.formats:
                return self.formats[key]
        return None

    @property
    def epub_url(self) -> str | None:
        for key in ["application/epub+zip", "application/epub"]:
            if key in self.formats:
                return self.formats[key]
        return None

    @property
    def kindle_url(self) -> str | None:
        for key in ["application/x-mobipocket-ebook"]:
            if key in self.formats:
                return self.formats[key]
        return None

    @property
    def html_url(self) -> str | None:
        for key in ["text/html", "text/html; charset=utf-8"]:
            if key in self.formats:
                return self.formats[key]
        return None

    @property
    def text_url(self) -> str | None:
        for key in ["text/plain", "text/plain; charset=utf-8", "text/plain; charset=us-ascii"]:
            if key in self.formats:
                return self.formats[key]
        return None

    @property
    def primary_author(self) -> str | None:
        if self.authors:
            return self.authors[0].name
        return None

    @property
    def primary_language(self) -> str:
        if self.languages:
            return self.languages[0]
        return "en"


@dataclass
class GutenbergSearchResult:
    count: int  # Total number of results
    next_page: str | None  # URL for next page
    previous_page: str | None  # URL for previous page
    books: list[GutenbergBookData]


class GutenbergClient:

    def __init__(
        self,
        base_url: str = GUTENDEX_BASE_URL,
        timeout: float = 30.0,
    ):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self):
        await self._get_client()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                follow_redirects=True,
                base_url=self.base_url,
                timeout=self.timeout,
                headers={
                    "Accept": "application/json",
                    "User-Agent": "L30-Library/1.0 (Library System Catalog Integration)",
                },
            )
        return self._client

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    async def _make_request(
        self,
        endpoint: str,
        params: dict | None = None,
    ) -> dict[str, Any]:
        client = await self._get_client()

        try:
            response = await client.get(endpoint, params=params)

            if response.status_code == 429:
                raise GutenbergRateLimitError(
                    "Rate limit exceeded",
                    status_code=response.status_code,
                )

            if response.status_code == 404:
                raise GutenbergNotFoundError(
                    "Resource not found",
                    status_code=response.status_code,
                )

            if response.status_code >= 400:
                raise GutenbergClientError(
                    f"API error: {response.status_code}",
                    status_code=response.status_code,
                )

            return response.json()

        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON from Gutenberg API: {e}")
            raise GutenbergClientError(f"Invalid response from Gutenberg API: {e}") from e

        except httpx.TimeoutException as e:
            logger.error(f"Timeout calling Gutenberg API: {e}")
            raise GutenbergClientError(f"Request timeout: {e}") from e

        except httpx.RequestError as e:
            logger.error(f"Error calling Gutenberg API: {e}")
            raise GutenbergClientError(f"Request failed: {e}") from e

    def _parse_book(self, data: dict) -> GutenbergBookData:
        authors = []
        for author_data in data.get("authors", []):
            authors.append(GutenbergAuthor(
                name=author_data.get("name", "Unknown"),
                birth_year=author_data.get("birth_year"),
                death_year=author_data.get("death_year"),
            ))

        return GutenbergBookData(
            id=data.get("id", 0),
            title=data.get("title", "Unknown Title"),
            authors=authors,
            subjects=data.get("subjects", []),
            bookshelves=data.get("bookshelves", []),
            languages=data.get("languages", ["en"]),
            copyright=data.get("copyright", False),
            media_type=data.get("media_type", "Text"),
            formats=data.get("formats", {}),
            download_count=data.get("download_count", 0),
        )

    async def search(
        self,
        query: str | None = None,
        *,
        author: str | None = None,
        title: str | None = None,
        topic: str | None = None,
        languages: list[str] | None = None,
        copyright: bool | None = None,
        ids: list[int] | None = None,
        mime_type: str | None = None,
        sort: str | None = None,  # "ascending", "descending", or "popular" (default)
        page: int = 1,
    ) -> GutenbergSearchResult:
        params = {}

        if query:
            params["search"] = query
        if author:
            params["author"] = author
        if title:
            params["title"] = title
        if topic:
            params["topic"] = topic
        if languages:
            params["languages"] = ",".join(languages)
        if copyright is not None:
            params["copyright"] = "true" if copyright else "false"
        if ids:
            params["ids"] = ",".join(str(i) for i in ids)
        if mime_type:
            params["mime_type"] = mime_type
        if sort:
            params["sort"] = sort
        if page > 1:
            params["page"] = page

        response = await self._make_request("/books", params=params)

        books = [self._parse_book(book) for book in response.get("results", [])]

        return GutenbergSearchResult(
            count=response.get("count", 0),
            next_page=response.get("next"),
            previous_page=response.get("previous"),
            books=books,
        )

    async def get_book(self, gutenberg_id: int) -> GutenbergBookData | None:
        try:
            response = await self._make_request(f"/books/{gutenberg_id}")
            return self._parse_book(response)
        except GutenbergNotFoundError:
            return None

    async def get_popular_books(
        self,
        *,
        languages: list[str] | None = None,
        topic: str | None = None,
        page: int = 1,
    ) -> GutenbergSearchResult:
        return await self.search(
            languages=languages,
            topic=topic,
            sort="popular",
            page=page,
            copyright=False,  # Only public domain
        )

    async def get_books_by_author(
        self,
        author_name: str,
        *,
        page: int = 1,
    ) -> GutenbergSearchResult:
        return await self.search(author=author_name, page=page)

    async def get_books_by_subject(
        self,
        subject: str,
        *,
        languages: list[str] | None = None,
        page: int = 1,
    ) -> GutenbergSearchResult:
        return await self.search(topic=subject, languages=languages, page=page)

    async def get_books_by_ids(
        self,
        ids: list[int],
    ) -> GutenbergSearchResult:
        return await self.search(ids=ids)

    async def iter_all_books(
        self,
        *,
        languages: list[str] | None = None,
        batch_size: int = 32,
        max_pages: int | None = None,
    ):
        page = 1
        while True:
            if max_pages and page > max_pages:
                break

            result = await self.search(
                languages=languages,
                copyright=False,  # Only public domain
                page=page,
            )

            if not result.books:
                break

            yield result.books

            if not result.next_page:
                break

            page += 1

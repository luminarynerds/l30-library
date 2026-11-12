# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from app.core.logging import get_logger
from app.core.branding import branding
from dataclasses import dataclass, field
from typing import Any

import httpx

logger = get_logger(__name__)

OPEN_LIBRARY_BASE_URL = "https://openlibrary.org"
COVERS_BASE_URL = "https://covers.openlibrary.org"


class OpenLibraryClientError(Exception):
    def __init__(self, message: str, status_code: int | None = None):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)


class OpenLibraryRateLimitError(OpenLibraryClientError):
    pass


@dataclass
class OpenLibraryAuthor:
    name: str
    ol_id: str | None = None


@dataclass
class OpenLibraryBookData:
    ol_work_id: str
    title: str
    authors: list[OpenLibraryAuthor] = field(default_factory=list)
    subjects: list[str] = field(default_factory=list)
    languages: list[str] = field(default_factory=list)
    first_publish_year: int | None = None
    publisher: str | None = None
    isbn_13: str | None = None
    isbn_10: str | None = None
    has_fulltext: bool = False
    public_scan: bool = False
    cover_id: int | None = None
    cover_url: str | None = None
    edition_count: int = 0
    ol_edition_id: str | None = None
    ia_identifier: str | None = None
    ebook_access: str | None = None  # "public", "borrowable", "printdisabled", "no_ebook"

    @property
    def primary_author(self) -> str | None:
        if self.authors:
            return self.authors[0].name
        return None

    @property
    def read_url(self) -> str | None:
        if self.ia_identifier:
            return f"https://archive.org/details/{self.ia_identifier}"
        return None


@dataclass
class OpenLibrarySearchResult:
    count: int
    offset: int
    books: list[OpenLibraryBookData]


class OpenLibraryClient:

    def __init__(
        self,
        base_url: str = OPEN_LIBRARY_BASE_URL,
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
                timeout=self.timeout,
                headers={
                    "Accept": "application/json",
                    "User-Agent": f"L30-Library/1.0 (Library System Catalog; mailto:{branding.contact_email})",
                },
            )
        return self._client

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    async def _make_request(self, url: str, params: dict | None = None) -> dict[str, Any]:
        client = await self._get_client()
        try:
            response = await client.get(url, params=params)
            if response.status_code == 429:
                raise OpenLibraryRateLimitError("Rate limit exceeded", status_code=429)
            if response.status_code >= 400:
                raise OpenLibraryClientError(
                    f"API error: {response.status_code}", status_code=response.status_code
                )
            return response.json()
        except httpx.TimeoutException as e:
            logger.error(f"Timeout calling Open Library API: {e}")
            raise OpenLibraryClientError(f"Request timeout: {e}") from e
        except httpx.RequestError as e:
            logger.error(f"Error calling Open Library API: {e}")
            raise OpenLibraryClientError(f"Request failed: {e}") from e

    def _get_cover_url(self, cover_id: int | None, size: str = "M") -> str | None:
        if cover_id:
            return f"{COVERS_BASE_URL}/b/id/{cover_id}-{size}.jpg"
        return None

    def _parse_book(self, data: dict) -> OpenLibraryBookData:
        authors = []
        for name in data.get("author_name", []):
            ol_ids = data.get("author_key", [])
            ol_id = ol_ids[len(authors)] if len(authors) < len(ol_ids) else None
            authors.append(OpenLibraryAuthor(name=name, ol_id=ol_id))

        cover_id = data.get("cover_i")
        isbn_list = data.get("isbn", [])

        return OpenLibraryBookData(
            ol_work_id=data.get("key", "").replace("/works/", ""),
            title=data.get("title", "Unknown Title"),
            authors=authors,
            subjects=data.get("subject", [])[:20],
            languages=data.get("language", []),
            first_publish_year=data.get("first_publish_year"),
            publisher=data.get("publisher", [None])[0] if data.get("publisher") else None,
            isbn_13=next((i for i in isbn_list if len(i) == 13), None),
            isbn_10=next((i for i in isbn_list if len(i) == 10), None),
            has_fulltext=data.get("has_fulltext", False),
            public_scan=data.get("public_scan_b", False),
            cover_id=cover_id,
            cover_url=self._get_cover_url(cover_id),
            edition_count=data.get("edition_count", 0),
            ol_edition_id=data.get("cover_edition_key"),
            ia_identifier=data.get("ia", [None])[0] if data.get("ia") else None,
            ebook_access=data.get("ebook_access"),
        )

    async def search(
        self,
        query: str | None = None,
        *,
        author: str | None = None,
        title: str | None = None,
        subject: str | None = None,
        languages: list[str] | None = None,
        has_fulltext: bool | None = None,
        ebook_access: str | None = None,
        limit: int = 20,
        offset: int = 0,
        sort: str | None = None,
    ) -> OpenLibrarySearchResult:
        params: dict[str, Any] = {
            "limit": min(limit, 100),
            "offset": offset,
        }

        if query:
            params["q"] = query
        if author:
            params["author"] = author
        if title:
            params["title"] = title
        if subject:
            params["subject"] = subject
        if languages:
            params["language"] = ",".join(languages)
        if has_fulltext is not None:
            params["has_fulltext"] = "true" if has_fulltext else "false"
        if ebook_access:
            params["ebook_access"] = ebook_access
        if sort:
            params["sort"] = sort

        params["fields"] = "key,title,author_name,author_key,subject,language,first_publish_year,publisher,isbn,has_fulltext,public_scan_b,cover_i,edition_count,cover_edition_key,ia,ebook_access"

        response = await self._make_request(f"{self.base_url}/search.json", params=params)

        books = [self._parse_book(doc) for doc in response.get("docs", [])]

        return OpenLibrarySearchResult(
            count=response.get("numFound", 0),
            offset=response.get("start", 0),
            books=books,
        )

    async def search_free_ebooks(
        self,
        query: str | None = None,
        *,
        limit: int = 20,
        offset: int = 0,
    ) -> OpenLibrarySearchResult:
        return await self.search(
            query=query,
            has_fulltext=True,
            ebook_access="public",
            limit=limit,
            offset=offset,
        )

    async def get_work(self, work_id: str) -> dict[str, Any] | None:
        try:
            return await self._make_request(f"{self.base_url}/works/{work_id}.json")
        except OpenLibraryClientError:
            return None

    async def get_subjects(
        self,
        subject: str,
        *,
        ebooks: bool = True,
        limit: int = 20,
        offset: int = 0,
    ) -> OpenLibrarySearchResult:
        params: dict[str, Any] = {"limit": limit, "offset": offset}
        if ebooks:
            params["ebooks"] = "true"

        subject_slug = subject.lower().replace(" ", "_")
        response = await self._make_request(
            f"{self.base_url}/subjects/{subject_slug}.json", params=params
        )

        books = []
        for work in response.get("works", []):
            authors = [
                OpenLibraryAuthor(name=a.get("name", "Unknown"))
                for a in work.get("authors", [])
            ]
            cover_id = work.get("cover_id")
            books.append(OpenLibraryBookData(
                ol_work_id=work.get("key", "").replace("/works/", ""),
                title=work.get("title", "Unknown"),
                authors=authors,
                cover_id=cover_id,
                cover_url=self._get_cover_url(cover_id),
                has_fulltext=work.get("has_fulltext", False),
                edition_count=work.get("edition_count", 0),
                ia_identifier=work.get("ia"),
                ebook_access=work.get("ebook_access"),
            ))

        return OpenLibrarySearchResult(
            count=response.get("work_count", len(books)),
            offset=offset,
            books=books,
        )

    async def iter_free_ebooks(
        self,
        *,
        subject: str | None = None,
        batch_size: int = 50,
        max_batches: int | None = None,
    ):
        offset = 0
        batch_count = 0

        while True:
            if max_batches and batch_count >= max_batches:
                break

            if subject:
                result = await self.get_subjects(
                    subject, ebooks=True, limit=batch_size, offset=offset
                )
            else:
                result = await self.search_free_ebooks(limit=batch_size, offset=offset)

            if not result.books:
                break

            yield result.books

            offset += batch_size
            batch_count += 1

            if offset >= result.count:
                break

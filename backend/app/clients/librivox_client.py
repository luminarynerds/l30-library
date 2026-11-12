# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

import contextlib
from app.core.logging import get_logger
from dataclasses import dataclass, field
from typing import Any

import httpx

logger = get_logger(__name__)

LIBRIVOX_BASE_URL = "https://librivox.org/api/feed"


class LibriVoxClientError(Exception):
    def __init__(self, message: str, status_code: int | None = None):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)


@dataclass
class LibriVoxAuthor:
    first_name: str
    last_name: str
    dob: str | None = None
    dod: str | None = None

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}".strip()


@dataclass
class LibriVoxSection:
    section_number: int
    title: str
    listen_url: str | None = None
    reader: str | None = None
    language: str | None = None
    playtime: str | None = None


@dataclass
class LibriVoxAudiobookData:
    librivox_id: int
    title: str
    authors: list[LibriVoxAuthor] = field(default_factory=list)
    description: str | None = None
    genres: list[str] = field(default_factory=list)
    language: str | None = None
    book_type: str = "solo"  # solo, group, dramatic, poetry
    total_time: str | None = None
    num_sections: int = 0
    copyright_year: int | None = None
    url_librivox: str | None = None
    url_project: str | None = None
    url_rss: str | None = None
    url_zip: str | None = None
    sections: list[LibriVoxSection] = field(default_factory=list)
    readers: list[dict] = field(default_factory=list)
    totaltime_secs: int = 0
    gutenberg_id: int | None = None

    @property
    def primary_author(self) -> str | None:
        if self.authors:
            return self.authors[0].full_name
        return None

    @property
    def cover_url(self) -> str | None:
        if self.url_librivox:
            # LibriVox cover images follow a pattern
            return None  # Cover URLs from extended API
        return None


@dataclass
class LibriVoxSearchResult:
    count: int
    books: list[LibriVoxAudiobookData]


class LibriVoxClient:

    def __init__(
        self,
        base_url: str = LIBRIVOX_BASE_URL,
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
        url = f"{self.base_url}/{endpoint}"

        # Always request JSON
        if params is None:
            params = {}
        params["format"] = "json"

        try:
            response = await client.get(url, params=params)
            if response.status_code == 429:
                raise LibriVoxClientError("Rate limit exceeded", status_code=429)
            if response.status_code >= 400:
                raise LibriVoxClientError(
                    f"API error: {response.status_code}", status_code=response.status_code
                )
            return response.json()
        except httpx.TimeoutException as e:
            logger.error(f"Timeout calling LibriVox API: {e}")
            raise LibriVoxClientError(f"Request timeout: {e}") from e
        except httpx.RequestError as e:
            logger.error(f"Error calling LibriVox API: {e}")
            raise LibriVoxClientError(f"Request failed: {e}") from e

    def _parse_audiobook(self, data: dict) -> LibriVoxAudiobookData:
        authors = []
        for author in data.get("authors", []):
            authors.append(LibriVoxAuthor(
                first_name=author.get("first_name", ""),
                last_name=author.get("last_name", ""),
                dob=author.get("dob"),
                dod=author.get("dod"),
            ))

        # Parse genres
        genres = []
        for genre in data.get("genres", []):
            if isinstance(genre, dict):
                genres.append(genre.get("name", ""))
            elif isinstance(genre, str):
                genres.append(genre)

        # Parse sections
        sections = []
        for section in data.get("sections", []):
            sections.append(LibriVoxSection(
                section_number=int(section.get("section_number", 0)),
                title=section.get("title", ""),
                listen_url=section.get("listen_url"),
                reader=section.get("readers", [{}])[0].get("display_name") if section.get("readers") else None,
                language=section.get("language"),
                playtime=section.get("playtime"),
            ))

        # Try to extract Gutenberg ID from URL
        gutenberg_id = None
        url_text = data.get("url_text_source", "")
        if "gutenberg.org" in url_text:
            # Best-effort Gutenberg ID extraction; unparseable URLs leave None.
            with contextlib.suppress(ValueError, IndexError):
                gutenberg_id = int(url_text.rstrip("/").split("/")[-1])

        return LibriVoxAudiobookData(
            librivox_id=int(data.get("id", 0)),
            title=data.get("title", "Unknown Title"),
            authors=authors,
            description=data.get("description"),
            genres=genres,
            language=data.get("language", "English"),
            total_time=data.get("totaltime"),
            num_sections=int(data.get("num_sections", 0)),
            copyright_year=int(data["copyright_year"]) if data.get("copyright_year") else None,
            url_librivox=data.get("url_librivox"),
            url_project=data.get("url_project"),
            url_rss=data.get("url_rss"),
            url_zip=data.get("url_zip_file"),
            sections=sections,
            totaltime_secs=int(data.get("totaltimesecs", 0)),
            gutenberg_id=gutenberg_id,
        )

    async def search(
        self,
        query: str | None = None,
        *,
        title: str | None = None,
        author: str | None = None,
        genre: str | None = None,
        limit: int = 50,
        offset: int = 0,
        extended: bool = True,
    ) -> LibriVoxSearchResult:
        params: dict[str, Any] = {
            "limit": limit,
            "offset": offset,
        }

        if extended:
            params["extended"] = 1
            params["coverart"] = 1

        endpoint = "audiobooks"

        if title or query:
            search_term = title or query
            params["title"] = f"^{search_term}"
        if author:
            params["author"] = author
        if genre:
            params["genre"] = genre

        response = await self._make_request(endpoint, params=params)

        books_data = response.get("books", [])
        if not isinstance(books_data, list):
            books_data = []

        books = []
        for book in books_data:
            try:
                books.append(self._parse_audiobook(book))
            except Exception as e:  # noqa: BLE001  # skip malformed feed entries; continue parsing
                logger.warning(f"Failed to parse LibriVox audiobook: {e}")

        return LibriVoxSearchResult(
            count=len(books),
            books=books,
        )

    async def get_audiobook(self, librivox_id: int) -> LibriVoxAudiobookData | None:
        try:
            response = await self._make_request("audiobooks", {"id": librivox_id, "extended": 1, "coverart": 1})
            books = response.get("books", [])
            if books:
                return self._parse_audiobook(books[0])
            return None
        except LibriVoxClientError:
            return None

    async def get_recent(self, *, limit: int = 50) -> LibriVoxSearchResult:
        return await self.search(limit=limit)

    async def iter_all_audiobooks(
        self,
        *,
        batch_size: int = 50,
        max_batches: int | None = None,
    ):
        offset = 0
        batch_count = 0

        while True:
            if max_batches and batch_count >= max_batches:
                break

            result = await self.search(limit=batch_size, offset=offset)
            if not result.books:
                break

            yield result.books

            offset += batch_size
            batch_count += 1

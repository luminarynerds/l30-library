# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from app.core.logging import get_logger
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from typing import Any

import httpx

logger = get_logger(__name__)

MANYBOOKS_BASE_URL = "https://manybooks.net"
MANYBOOKS_OPDS_URL = f"{MANYBOOKS_BASE_URL}/opds"

ATOM_NS = "http://www.w3.org/2005/Atom"
DC_NS = "http://purl.org/dc/terms/"
OPDS_NS = "http://opds-spec.org/2010/catalog"
OPENSEARCH_NS = "http://a9.com/-/spec/opensearch/1.1/"


class ManyBooksClientError(Exception):
    def __init__(self, message: str, status_code: int | None = None):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)


@dataclass
class ManyBooksAuthor:
    name: str


@dataclass
class ManyBooksBookData:
    manybooks_id: str
    title: str
    authors: list[ManyBooksAuthor] = field(default_factory=list)
    summary: str | None = None
    categories: list[str] = field(default_factory=list)
    language: str = "en"
    publication_year: int | None = None
    rating: float | None = None
    rating_count: int = 0
    formats: dict[str, str] = field(default_factory=dict)  # format -> url
    cover_url: str | None = None
    source_url: str | None = None
    gutenberg_id: int | None = None

    @property
    def primary_author(self) -> str | None:
        if self.authors:
            return self.authors[0].name
        return None


@dataclass
class ManyBooksSearchResult:
    count: int
    books: list[ManyBooksBookData]
    next_url: str | None = None


class ManyBooksClient:

    def __init__(self, timeout: float = 30.0):
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
                    "User-Agent": "L30-Library/1.0 (Library System Catalog Integration)",
                    "Accept": "application/atom+xml, application/xml, text/xml",
                },
                follow_redirects=True,
            )
        return self._client

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    async def _fetch_feed(self, url: str, params: dict | None = None) -> str:
        client = await self._get_client()
        try:
            response = await client.get(url, params=params)
            if response.status_code >= 400:
                raise ManyBooksClientError(
                    f"Feed fetch failed: {response.status_code}",
                    status_code=response.status_code,
                )
            return response.text
        except httpx.TimeoutException as e:
            raise ManyBooksClientError(f"Request timeout: {e}") from e
        except httpx.RequestError as e:
            raise ManyBooksClientError(f"Request failed: {e}") from e

    def _parse_entry(self, entry: ET.Element) -> ManyBooksBookData:
        entry_id = entry.findtext(f"{{{ATOM_NS}}}id", "")
        manybooks_id = entry_id.rstrip("/").split("/")[-1] if entry_id else ""

        title = entry.findtext(f"{{{ATOM_NS}}}title", "Unknown Title")

        authors = []
        for author_el in entry.findall(f"{{{ATOM_NS}}}author"):
            name = author_el.findtext(f"{{{ATOM_NS}}}name", "Unknown")
            authors.append(ManyBooksAuthor(name=name))

        summary = entry.findtext(f"{{{ATOM_NS}}}summary")

        categories = []
        for cat in entry.findall(f"{{{ATOM_NS}}}category"):
            label = cat.get("label") or cat.get("term")
            if label:
                categories.append(label)

        language = entry.findtext(f"{{{DC_NS}}}language", "en")

        # Download links
        formats = {}
        cover_url = None
        source_url = None

        for link in entry.findall(f"{{{ATOM_NS}}}link"):
            rel = link.get("rel", "")
            href = link.get("href", "")
            link_type = link.get("type", "")

            if "application/epub+zip" in link_type:
                formats["epub"] = href
            elif "application/x-mobipocket-ebook" in link_type:
                formats["mobi"] = href
            elif "application/pdf" in link_type:
                formats["pdf"] = href
            elif "text/plain" in link_type and "acquisition" in rel:
                formats["txt"] = href
            elif rel == "http://opds-spec.org/image":
                cover_url = href
            elif rel == "http://opds-spec.org/image/thumbnail":
                if not cover_url:
                    cover_url = href
            elif rel == "alternate":
                source_url = href

        return ManyBooksBookData(
            manybooks_id=manybooks_id,
            title=title,
            authors=authors,
            summary=summary,
            categories=categories,
            language=language,
            formats=formats,
            cover_url=cover_url,
            source_url=source_url,
        )

    def _parse_feed(self, xml_text: str) -> ManyBooksSearchResult:
        root = ET.fromstring(xml_text)

        books = []
        for entry in root.findall(f"{{{ATOM_NS}}}entry"):
            try:
                books.append(self._parse_entry(entry))
            except Exception as e:  # noqa: BLE001  # skip malformed feed entries; continue parsing
                logger.warning(f"Failed to parse ManyBooks entry: {e}")

        next_url = None
        for link in root.findall(f"{{{ATOM_NS}}}link"):
            if link.get("rel") == "next":
                next_url = link.get("href")
                break

        total_str = root.findtext(f"{{{OPENSEARCH_NS}}}totalResults")
        total = int(total_str) if total_str else len(books)

        return ManyBooksSearchResult(count=total, books=books, next_url=next_url)

    async def get_popular(self, *, page: int = 1) -> ManyBooksSearchResult:
        params: dict[str, Any] = {}
        if page > 1:
            params["page"] = page
        xml_text = await self._fetch_feed(f"{MANYBOOKS_OPDS_URL}/popular", params=params)
        return self._parse_feed(xml_text)

    async def get_recent(self, *, page: int = 1) -> ManyBooksSearchResult:
        params: dict[str, Any] = {}
        if page > 1:
            params["page"] = page
        xml_text = await self._fetch_feed(f"{MANYBOOKS_OPDS_URL}/recent", params=params)
        return self._parse_feed(xml_text)

    async def search(self, query: str, *, page: int = 1) -> ManyBooksSearchResult:
        params: dict[str, Any] = {"q": query}
        if page > 1:
            params["page"] = page
        xml_text = await self._fetch_feed(f"{MANYBOOKS_OPDS_URL}/search", params=params)
        return self._parse_feed(xml_text)

    async def get_by_category(self, category: str, *, page: int = 1) -> ManyBooksSearchResult:
        params: dict[str, Any] = {}
        if page > 1:
            params["page"] = page
        category_slug = category.lower().replace(" ", "-")
        xml_text = await self._fetch_feed(
            f"{MANYBOOKS_OPDS_URL}/category/{category_slug}", params=params
        )
        return self._parse_feed(xml_text)

    async def iter_catalog(self, *, max_pages: int | None = None):
        page = 1
        while True:
            if max_pages and page > max_pages:
                break

            result = await self.get_popular(page=page)
            if not result.books:
                break

            yield result.books

            if not result.next_url:
                break

            page += 1

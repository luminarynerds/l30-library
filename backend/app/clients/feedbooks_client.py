# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

import contextlib
from app.core.logging import get_logger
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

import httpx

logger = get_logger(__name__)

FEEDBOOKS_BASE_URL = "https://www.feedbooks.com"
FEEDBOOKS_PUBLIC_DOMAIN = f"{FEEDBOOKS_BASE_URL}/books/top.atom"
FEEDBOOKS_RECENT = f"{FEEDBOOKS_BASE_URL}/books/recent.atom"
FEEDBOOKS_SEARCH = f"{FEEDBOOKS_BASE_URL}/books/search.atom"

ATOM_NS = "http://www.w3.org/2005/Atom"
OPDS_NS = "http://opds-spec.org/2010/catalog"
DC_NS = "http://purl.org/dc/terms/"
OPENSEARCH_NS = "http://a9.com/-/spec/opensearch/1.1/"


class FeedbooksClientError(Exception):
    def __init__(self, message: str, status_code: int | None = None):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)


@dataclass
class FeedbooksAuthor:
    name: str
    uri: str | None = None


@dataclass
class FeedbooksBookData:
    feedbooks_id: str
    title: str
    authors: list[FeedbooksAuthor] = field(default_factory=list)
    summary: str | None = None
    content: str | None = None
    categories: list[str] = field(default_factory=list)
    language: str = "en"
    published_at: datetime | None = None
    publisher: str | None = None
    rights: str | None = None
    epub_url: str | None = None
    mobi_url: str | None = None
    pdf_url: str | None = None
    cover_url: str | None = None
    thumbnail_url: str | None = None
    source_url: str | None = None

    @property
    def primary_author(self) -> str | None:
        if self.authors:
            return self.authors[0].name
        return None


@dataclass
class FeedbooksSearchResult:
    count: int
    books: list[FeedbooksBookData]
    next_url: str | None = None


class FeedbooksClient:

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
                raise FeedbooksClientError(
                    f"Feed fetch failed: {response.status_code}",
                    status_code=response.status_code,
                )
            return response.text
        except httpx.TimeoutException as e:
            raise FeedbooksClientError(f"Request timeout: {e}") from e
        except httpx.RequestError as e:
            raise FeedbooksClientError(f"Request failed: {e}") from e

    def _parse_entry(self, entry: ET.Element) -> FeedbooksBookData:
        # ID
        entry_id = entry.findtext(f"{{{ATOM_NS}}}id", "")
        feedbooks_id = entry_id.rstrip("/").split("/")[-1] if entry_id else ""

        title = entry.findtext(f"{{{ATOM_NS}}}title", "Unknown Title")

        # Authors
        authors = []
        for author_el in entry.findall(f"{{{ATOM_NS}}}author"):
            name = author_el.findtext(f"{{{ATOM_NS}}}name", "Unknown")
            uri = author_el.findtext(f"{{{ATOM_NS}}}uri")
            authors.append(FeedbooksAuthor(name=name, uri=uri))

        # Description
        summary = entry.findtext(f"{{{ATOM_NS}}}summary")
        content_el = entry.find(f"{{{ATOM_NS}}}content")
        content = content_el.text if content_el is not None else None

        # Categories
        categories = []
        for cat in entry.findall(f"{{{ATOM_NS}}}category"):
            label = cat.get("label") or cat.get("term")
            if label:
                categories.append(label)

        # Language and publisher
        language = entry.findtext(f"{{{DC_NS}}}language", "en")
        publisher = entry.findtext(f"{{{DC_NS}}}publisher")
        rights = entry.findtext(f"{{{ATOM_NS}}}rights") or entry.findtext(f"{{{DC_NS}}}rights")

        # Published date
        published_str = entry.findtext(f"{{{ATOM_NS}}}published") or entry.findtext(f"{{{DC_NS}}}issued")
        published_at = None
        if published_str:
            # Unparseable feed dates fall back to None.
            with contextlib.suppress(ValueError, TypeError):
                published_at = datetime.fromisoformat(published_str.replace("Z", "+00:00"))

        # Links
        epub_url = None
        mobi_url = None
        pdf_url = None
        cover_url = None
        thumbnail_url = None
        source_url = None

        for link in entry.findall(f"{{{ATOM_NS}}}link"):
            rel = link.get("rel", "")
            href = link.get("href", "")
            link_type = link.get("type", "")

            if "application/epub+zip" in link_type:
                epub_url = href
            elif "application/x-mobipocket-ebook" in link_type:
                mobi_url = href
            elif "application/pdf" in link_type:
                pdf_url = href
            elif rel == "http://opds-spec.org/image":
                cover_url = href
            elif rel == "http://opds-spec.org/image/thumbnail":
                thumbnail_url = href
            elif rel == "alternate" and "text/html" in link_type:
                source_url = href

        return FeedbooksBookData(
            feedbooks_id=feedbooks_id,
            title=title,
            authors=authors,
            summary=summary,
            content=content,
            categories=categories,
            language=language,
            published_at=published_at,
            publisher=publisher,
            rights=rights,
            epub_url=epub_url,
            mobi_url=mobi_url,
            pdf_url=pdf_url,
            cover_url=cover_url,
            thumbnail_url=thumbnail_url,
            source_url=source_url,
        )

    def _parse_feed(self, xml_text: str) -> FeedbooksSearchResult:
        root = ET.fromstring(xml_text)

        books = []
        for entry in root.findall(f"{{{ATOM_NS}}}entry"):
            try:
                books.append(self._parse_entry(entry))
            except Exception as e:  # noqa: BLE001  # skip malformed feed entries; continue parsing
                logger.warning(f"Failed to parse Feedbooks entry: {e}")

        # Find next page link
        next_url = None
        for link in root.findall(f"{{{ATOM_NS}}}link"):
            if link.get("rel") == "next":
                next_url = link.get("href")
                break

        # Total results
        total_str = root.findtext(f"{{{OPENSEARCH_NS}}}totalResults")
        total = int(total_str) if total_str else len(books)

        return FeedbooksSearchResult(count=total, books=books, next_url=next_url)

    async def get_popular(self, *, page: int = 1) -> FeedbooksSearchResult:
        url = FEEDBOOKS_PUBLIC_DOMAIN
        params = {}
        if page > 1:
            params["page"] = page
        xml_text = await self._fetch_feed(url, params=params)
        return self._parse_feed(xml_text)

    async def get_recent(self, *, page: int = 1) -> FeedbooksSearchResult:
        params = {}
        if page > 1:
            params["page"] = page
        xml_text = await self._fetch_feed(FEEDBOOKS_RECENT, params=params)
        return self._parse_feed(xml_text)

    async def search(self, query: str, *, page: int = 1) -> FeedbooksSearchResult:
        params: dict[str, Any] = {"query": query}
        if page > 1:
            params["page"] = page
        xml_text = await self._fetch_feed(FEEDBOOKS_SEARCH, params=params)
        return self._parse_feed(xml_text)

    async def iter_catalog(
        self,
        *,
        max_pages: int | None = None,
    ):
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

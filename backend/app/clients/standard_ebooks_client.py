# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from app.core.logging import get_logger
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

import httpx

logger = get_logger(__name__)

SE_BASE_URL = "https://standardebooks.org"
SE_ATOM_FEED_URL = f"{SE_BASE_URL}/feeds/atom"
SE_RSS_FEED_URL = f"{SE_BASE_URL}/feeds/rss"
SE_OPDS_FEED_URL = f"{SE_BASE_URL}/feeds/opds"

# Atom namespace
ATOM_NS = "http://www.w3.org/2005/Atom"
DC_NS = "http://purl.org/dc/terms/"
SCHEMA_NS = "http://schema.org/"


class StandardEbooksClientError(Exception):
    def __init__(self, message: str, status_code: int | None = None):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)


@dataclass
class StandardEbookAuthor:
    name: str
    url: str | None = None


@dataclass
class StandardEbookData:
    se_identifier: str  # URL path like "jane-austen/pride-and-prejudice"
    title: str
    authors: list[StandardEbookAuthor] = field(default_factory=list)
    description: str | None = None
    long_description: str | None = None
    subjects: list[str] = field(default_factory=list)
    language: str = "en"
    published_at: datetime | None = None
    updated_at: datetime | None = None
    word_count: int | None = None
    epub_url: str | None = None
    azw3_url: str | None = None
    kepub_url: str | None = None
    cover_url: str | None = None
    thumbnail_url: str | None = None
    source_url: str | None = None

    @property
    def primary_author(self) -> str | None:
        if self.authors:
            return self.authors[0].name
        return None


@dataclass
class StandardEbooksSearchResult:
    count: int
    books: list[StandardEbookData]


class StandardEbooksClient:

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
                },
            )
        return self._client

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    async def _fetch_feed(self, url: str) -> str:
        client = await self._get_client()
        try:
            response = await client.get(url)
            if response.status_code >= 400:
                raise StandardEbooksClientError(
                    f"Feed fetch failed: {response.status_code}",
                    status_code=response.status_code,
                )
            return response.text
        except httpx.TimeoutException as e:
            raise StandardEbooksClientError(f"Request timeout: {e}") from e
        except httpx.RequestError as e:
            raise StandardEbooksClientError(f"Request failed: {e}") from e

    def _parse_atom_entry(self, entry: ET.Element) -> StandardEbookData:
        # Extract identifier from entry ID or link
        entry_id = entry.findtext(f"{{{ATOM_NS}}}id", "")
        se_identifier = entry_id.replace(f"{SE_BASE_URL}/ebooks/", "").strip("/")
        source_url = entry_id

        title = entry.findtext(f"{{{ATOM_NS}}}title", "Unknown Title")

        # Authors
        authors = []
        for author_el in entry.findall(f"{{{ATOM_NS}}}author"):
            name = author_el.findtext(f"{{{ATOM_NS}}}name", "Unknown")
            uri = author_el.findtext(f"{{{ATOM_NS}}}uri")
            authors.append(StandardEbookAuthor(name=name, url=uri))

        # Description
        summary = entry.findtext(f"{{{ATOM_NS}}}summary")
        content_el = entry.find(f"{{{ATOM_NS}}}content")
        long_description = content_el.text if content_el is not None else None

        # Subjects/categories
        subjects = []
        for cat in entry.findall(f"{{{ATOM_NS}}}category"):
            term = cat.get("term") or cat.get("label")
            if term:
                subjects.append(term)

        # Language
        language = entry.findtext(f"{{{DC_NS}}}language", "en")

        # Dates
        published_str = entry.findtext(f"{{{ATOM_NS}}}published")
        updated_str = entry.findtext(f"{{{ATOM_NS}}}updated")
        published_at = self._parse_datetime(published_str)
        updated_at = self._parse_datetime(updated_str)

        # Links (download URLs and cover)
        epub_url = None
        azw3_url = None
        kepub_url = None
        cover_url = None
        thumbnail_url = None

        for link in entry.findall(f"{{{ATOM_NS}}}link"):
            rel = link.get("rel", "")
            href = link.get("href", "")
            link_type = link.get("type", "")

            if "application/epub+zip" in link_type:
                if "kobo" in href.lower() or "kepub" in href.lower():
                    kepub_url = href
                elif "advanced" not in href.lower():
                    epub_url = href
            elif "application/x-mobipocket-ebook" in link_type or href.endswith(".azw3"):
                azw3_url = href
            elif rel == "http://opds-spec.org/image" or "image" in rel:
                cover_url = href
            elif rel == "http://opds-spec.org/image/thumbnail":
                thumbnail_url = href

        # If no direct download links, construct them from identifier
        if not epub_url and se_identifier:
            epub_url = f"{SE_BASE_URL}/ebooks/{se_identifier}/downloads/{se_identifier.split('/')[-1]}.epub"

        if not cover_url and se_identifier:
            cover_url = f"{SE_BASE_URL}/ebooks/{se_identifier}/downloads/cover.jpg"

        return StandardEbookData(
            se_identifier=se_identifier,
            title=title,
            authors=authors,
            description=summary,
            long_description=long_description,
            subjects=subjects,
            language=language,
            published_at=published_at,
            updated_at=updated_at,
            epub_url=epub_url,
            azw3_url=azw3_url,
            kepub_url=kepub_url,
            cover_url=cover_url,
            thumbnail_url=thumbnail_url,
            source_url=source_url,
        )

    def _parse_datetime(self, dt_str: str | None) -> datetime | None:
        if not dt_str:
            return None
        try:
            # Try ISO format
            return datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
        except (ValueError, TypeError):
            return None

    async def get_new_releases(self) -> list[StandardEbookData]:
        xml_text = await self._fetch_feed(SE_ATOM_FEED_URL)
        root = ET.fromstring(xml_text)

        books = []
        for entry in root.findall(f"{{{ATOM_NS}}}entry"):
            try:
                book = self._parse_atom_entry(entry)
                books.append(book)
            except Exception as e:  # noqa: BLE001  # skip malformed feed entries; continue parsing
                logger.warning(f"Failed to parse Standard Ebooks entry: {e}")
                continue

        return books

    async def get_catalog(self) -> list[StandardEbookData]:
        try:
            xml_text = await self._fetch_feed(f"{SE_OPDS_FEED_URL}/all")
            root = ET.fromstring(xml_text)

            books = []
            for entry in root.findall(f"{{{ATOM_NS}}}entry"):
                try:
                    book = self._parse_atom_entry(entry)
                    books.append(book)
                except Exception as e:  # noqa: BLE001  # skip malformed feed entries; continue parsing
                    logger.warning(f"Failed to parse Standard Ebooks entry: {e}")
                    continue

            return books

        except StandardEbooksClientError:
            logger.info("Full OPDS catalog unavailable, using new releases feed")
            return await self.get_new_releases()

    async def search(self, query: str) -> list[StandardEbookData]:
        catalog = await self.get_catalog()
        query_lower = query.lower()

        return [
            book for book in catalog
            if query_lower in book.title.lower()
            or (book.primary_author and query_lower in book.primary_author.lower())
            or any(query_lower in s.lower() for s in book.subjects)
        ]

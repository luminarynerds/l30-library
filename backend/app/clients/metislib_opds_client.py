# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Read MetisLib's public OPDS `/indie` acquisition feed and fetch EPUB bytes.

Mirrors the `StandardEbooksClient` pattern (httpx + stdlib ElementTree). The feed
is public; only `fetch_ebook_bytes` carries L30's library API key. Used by the
Phase 1 `MetisLibOpdsImporter` to own the indie catalog locally.
"""
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime

import httpx

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)

ATOM_NS = "http://www.w3.org/2005/Atom"
DC_NS = "http://purl.org/dc/terms/"
OPDS_NS = "http://opds-spec.org/2010/catalog"

_ID_PREFIX = "urn:metislib:indie_ebook:"
_OPEN_ACCESS_REL = "http://opds-spec.org/acquisition/open-access"
_IMAGE_REL = "http://opds-spec.org/image"


class MetisLibOpdsClientError(Exception):
    def __init__(self, message: str, status_code: int | None = None):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)


@dataclass
class IndieFeedEntry:
    metislib_ebook_id: int
    title: str
    author_pen_name: str | None = None
    description: str | None = None
    language: str | None = None
    genre: str | None = None
    publication_year: int | None = None
    cover_url: str | None = None
    acquisition_href: str = ""
    copies_total: int | None = None
    copies_available: int | None = None
    source_updated_at: datetime | None = None


class MetisLibOpdsClient:
    def __init__(self, timeout: float = 30.0):
        self.timeout = timeout

    def parse_feed(self, xml: str) -> tuple[list[IndieFeedEntry], str | None]:
        root = ET.fromstring(xml)

        entries: list[IndieFeedEntry] = []
        for entry_el in root.findall(f"{{{ATOM_NS}}}entry"):
            try:
                parsed = self._parse_entry(entry_el)
                if parsed is not None:
                    entries.append(parsed)
            except Exception as exc:  # noqa: BLE001
                logger.warning(f"Failed to parse MetisLib OPDS indie entry: {exc}")
                continue

        next_href = None
        for link in root.findall(f"{{{ATOM_NS}}}link"):
            if link.get("rel") == "next":
                next_href = link.get("href")
                break

        return entries, next_href

    def _parse_entry(self, entry: ET.Element) -> IndieFeedEntry | None:
        entry_id = entry.findtext(f"{{{ATOM_NS}}}id", "") or ""
        if not entry_id.startswith(_ID_PREFIX):
            return None
        metislib_ebook_id = int(entry_id[len(_ID_PREFIX):])

        title = entry.findtext(f"{{{ATOM_NS}}}title", "") or ""

        author_el = entry.find(f"{{{ATOM_NS}}}author")
        author_pen_name = (
            author_el.findtext(f"{{{ATOM_NS}}}name") if author_el is not None else None
        )

        description = entry.findtext(f"{{{ATOM_NS}}}summary")
        language = entry.findtext(f"{{{DC_NS}}}language")

        category_el = entry.find(f"{{{ATOM_NS}}}category")
        genre = category_el.get("term") if category_el is not None else None

        publication_year = None
        issued = entry.findtext(f"{{{DC_NS}}}issued")
        if issued:
            try:
                publication_year = int(issued[:4])
            except (ValueError, TypeError):
                publication_year = None

        cover_url = None
        acquisition_href = ""
        copies_total = None
        copies_available = None
        for link in entry.findall(f"{{{ATOM_NS}}}link"):
            rel = link.get("rel", "")
            href = link.get("href", "")
            if rel == _IMAGE_REL:
                cover_url = href
            elif rel == _OPEN_ACCESS_REL:
                acquisition_href = href
                copies_el = link.find(f"{{{OPDS_NS}}}copies")
                if copies_el is not None:
                    copies_total = _to_int(copies_el.get("total"))
                    copies_available = _to_int(copies_el.get("available"))

        source_updated_at = _parse_datetime(entry.findtext(f"{{{ATOM_NS}}}updated"))

        return IndieFeedEntry(
            metislib_ebook_id=metislib_ebook_id,
            title=title,
            author_pen_name=author_pen_name,
            description=description,
            language=language,
            genre=genre,
            publication_year=publication_year,
            cover_url=cover_url,
            acquisition_href=acquisition_href,
            copies_total=copies_total,
            copies_available=copies_available,
            source_updated_at=source_updated_at,
        )

    async def fetch_indie_feed(
        self, page: int = 1, limit: int = 20
    ) -> tuple[list[IndieFeedEntry], str | None]:
        settings = get_settings()
        url = (
            f"{settings.metislib_public_url.rstrip('/')}"
            f"/api/v1/opds/indie?page={page}&limit={limit}"
        )
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.get(url)
        except (httpx.TimeoutException, httpx.ConnectError, httpx.RequestError) as exc:
            raise MetisLibOpdsClientError(f"OPDS feed unreachable: {exc}") from exc
        if resp.status_code >= 400:
            raise MetisLibOpdsClientError(
                f"OPDS feed fetch failed: {resp.status_code}",
                status_code=resp.status_code,
            )
        return self.parse_feed(resp.text)

    async def fetch_ebook_bytes(self, metislib_ebook_id: int) -> bytes:
        settings = get_settings()
        url = (
            f"{settings.metislib_base_url.rstrip('/')}"
            f"/opds/borrow/{metislib_ebook_id}"
        )
        headers = {
            "Authorization": f"Bearer {settings.metislib_api_key}",
            "X-Library-Id": settings.metislib_library_id,
        }
        try:
            async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True) as client:
                resp = await client.get(url, headers=headers)
        except (httpx.TimeoutException, httpx.ConnectError, httpx.RequestError) as exc:
            raise MetisLibOpdsClientError(
                f"EPUB fetch unreachable for {metislib_ebook_id}: {exc}"
            ) from exc
        if resp.status_code >= 400:
            raise MetisLibOpdsClientError(
                f"EPUB fetch failed for {metislib_ebook_id}: {resp.status_code}",
                status_code=resp.status_code,
            )
        return resp.content


def _to_int(value: str | None) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (ValueError, TypeError):
        return None


def _parse_datetime(dt_str: str | None) -> datetime | None:
    if not dt_str:
        return None
    try:
        return datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return None

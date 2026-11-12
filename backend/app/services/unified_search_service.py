# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
import asyncio
import contextlib
import hashlib
from app.core.logging import get_logger
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from ..core.tracing import get_tracer, add_span_attributes
from .catalog_subjects import parse_subjects_field
from app.core.datetime_utils import utc_now
from app.models.catalog import ItemStatus

logger = get_logger(__name__)
tracer = get_tracer(__name__)


class ContentSource(StrEnum):
    LOCAL = "local"
    PALACE = "palace"
    INDIE = "indie"


class ContentFormat(StrEnum):
    BOOK = "book"
    EBOOK = "ebook"
    AUDIOBOOK = "audiobook"
    DVD = "dvd"
    BLURAY = "bluray"
    CD = "cd"
    VINYL = "vinyl"
    MAGAZINE = "magazine"
    GAME = "game"
    EQUIPMENT = "equipment"
    KIT = "kit"
    TOOL = "tool"
    VIDEO_STREAMING = "video_streaming"
    MUSIC = "music"
    COMIC = "comic"
    OTHER = "other"


MAX_MERGE_WINDOW = 5000  # bound cross-source pagination depth (offset+limit); high enough to cover the full local+indie catalog so browse totals stay reachable


def _dedup_key(r: "UnifiedSearchResult") -> str:
    if r.isbn:
        return r.isbn.strip().lower()
    return f"{(r.title or '').strip().lower()}:{(r.author or '').strip().lower()}"


def _result_sort_key(sort_by: str | None):
    """Return (key_func, reverse_default) for the requested browse sort.

    relevance (or unset) -> sort by relevance_score descending (search behavior).
    popularity / recently_added are DB-ordered by the local source
    (total_checkouts / created_at); UnifiedSearchResult does not carry those
    columns, so we return a constant key and rely on Python's stable sort to
    preserve the per-source order the local query already produced (local
    results are appended first in _merge_and_paginate). Indie/MetisLib rows,
    which have no circulation signal, trail the local set in their own order.
    """
    if sort_by == "title":
        return (lambda r: (r.title or "").lower(), False)
    if sort_by == "author":
        return (lambda r: (r.author or "").lower(), False)
    if sort_by == "year":
        return (lambda r: r.publication_year if r.publication_year is not None else -1, False)
    if sort_by in ("popularity", "recently_added"):
        return (lambda r: 0, False)
    return (lambda r: r.relevance_score, True)


def _merge_and_paginate(
    sources: "list[tuple[list[UnifiedSearchResult], int]]",
    *,
    offset: int,
    limit: int,
    sort_by: str | None,
    sort_direction: str | None,
    deduplicate: bool,
) -> "tuple[list[UnifiedSearchResult], int, bool]":
    """Merge per-source (results, total) into one sorted, paginated page.

    - merged total = sum of per-source totals (dedup overcount accepted).
    - results deduped by ISBN/title+author when deduplicate=True.
    - sorted by the requested key; relevance path preserved for search.
    - has_more bounded by MAX_MERGE_WINDOW.
    """
    merged_total = sum(total for _results, total in sources)

    merged: list = []
    for results, _total in sources:
        merged.extend(results)

    key_func, reverse_default = _result_sort_key(sort_by)
    reverse = reverse_default
    if sort_by in ("title", "author", "year"):
        reverse = (sort_direction == "desc")
    merged.sort(key=key_func, reverse=reverse)

    if deduplicate:
        seen: set = set()
        deduped: list = []
        for r in merged:
            k = _dedup_key(r)
            if k in seen:
                continue
            seen.add(k)
            deduped.append(r)
        merged = deduped

    page = merged[offset:offset + limit]
    reachable = min(merged_total, MAX_MERGE_WINDOW)
    has_more = (offset + limit) < reachable
    return page, merged_total, has_more


@dataclass
class UnifiedSearchResult:
    # Identification
    id: str  # Unique ID (source:source_id)
    source: ContentSource
    source_id: str  # ID in source system

    # Core metadata
    title: str
    author: str | None = None
    authors: list[str] = field(default_factory=list)
    format: ContentFormat = ContentFormat.OTHER
    format_details: list[str] = field(default_factory=list)  # Specific formats available

    # Descriptive metadata
    description: str | None = None
    cover_url: str | None = None
    isbn: str | None = None
    publisher: str | None = None
    publication_year: int | None = None
    subjects: list[str] = field(default_factory=list)
    language: str | None = None

    # Availability
    is_available: bool = False
    copies_available: int | None = None
    copies_total: int | None = None
    hold_count: int | None = None
    estimated_wait_days: int | None = None

    # For digital content
    download_formats: list[str] = field(default_factory=list)

    # Scoring
    relevance_score: float = 1.0

    # Deduplication
    dedup_key: str | None = None  # ISBN or title+author hash for dedup

    # Related items (for grouped results)
    related_sources: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "source": self.source.value,
            "source_id": self.source_id,
            "title": self.title,
            "author": self.author,
            "authors": self.authors,
            "format": self.format.value,
            "format_details": self.format_details,
            "description": self.description,
            "cover_url": self.cover_url,
            "isbn": self.isbn,
            "publisher": self.publisher,
            "publication_year": self.publication_year,
            "subjects": self.subjects,
            "language": self.language,
            "is_available": self.is_available,
            "copies_available": self.copies_available,
            "copies_total": self.copies_total,
            "hold_count": self.hold_count,
            "estimated_wait_days": self.estimated_wait_days,
            "download_formats": self.download_formats,
            "relevance_score": self.relevance_score,
            "related_sources": self.related_sources,
        }


@dataclass
class UnifiedSearchResponse:
    query: str
    total_results: int
    results: list[UnifiedSearchResult]
    sources_searched: list[str]
    source_counts: dict[str, int]
    search_time_ms: float
    has_more: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "query": self.query,
            "total_results": self.total_results,
            "results": [r.to_dict() for r in self.results],
            "sources_searched": self.sources_searched,
            "source_counts": self.source_counts,
            "search_time_ms": self.search_time_ms,
            "has_more": self.has_more,
        }


class UnifiedSearchService:

    _FORMAT_MAP = {
        "book": ContentFormat.BOOK,
        "ebook": ContentFormat.EBOOK,
        "audiobook": ContentFormat.AUDIOBOOK,
        "dvd": ContentFormat.DVD,
        "bluray": ContentFormat.BLURAY,
        "cd": ContentFormat.CD,
        "vinyl": ContentFormat.VINYL,
        "magazine": ContentFormat.MAGAZINE,
        "game": ContentFormat.GAME,
        "equipment": ContentFormat.EQUIPMENT,
        "kit": ContentFormat.KIT,
        "tool": ContentFormat.TOOL,
    }

    def __init__(self, db: AsyncSession):
        self.db = db

    # =========================================================================
    # Main Search Method
    # =========================================================================

    async def search(
        self,
        query: str,
        sources: list[ContentSource] | None = None,
        formats: list[ContentFormat] | None = None,
        available_only: bool = False,
        limit: int = 50,
        offset: int = 0,
        deduplicate: bool = True,
        year_min: int | None = None,
        year_max: int | None = None,
        min_lexile: int | None = None,
        max_lexile: int | None = None,
        language: list[str] | None = None,
        sort_by: str | None = None,
        sort_direction: str | None = None,
        is_large_print: bool | None = None,
        publisher: str | None = None,
        location: str | None = None,
        subject_facets: list[str] | None = None,
        author_facets: list[str] | None = None,
        series_facets: list[str] | None = None,
    ) -> UnifiedSearchResponse:
        with tracer.start_as_current_span("unified_search.search"):
            add_span_attributes(
                **{"search.query": query, "search.limit": limit, "search.offset": offset,
                   "search.available_only": available_only, "search.deduplicate": deduplicate}
            )
            start_time = utc_now()

            # Default to all sources
            if sources is None:
                sources = [ContentSource.LOCAL, ContentSource.INDIE]

            # Indie/MetisLib cannot honor two filters and is dropped entirely
            # when either is active (drop-source rule):
            #  - lexile: MetisLib carries no lexile data at all
            #  - language: MetisLib uses ISO 639-1 codes (e.g. "en"); the API
            #    contract + local BIBFRAME use ISO 639-2/B (e.g. "eng"), so
            #    indie cannot satisfy the documented language filter.
            indie_cannot_filter = (
                bool(is_large_print)
                or bool(publisher)
                or bool(location)
                or min_lexile is not None
                or max_lexile is not None
                or language
            )
            if indie_cannot_filter:
                sources = [s for s in sources if s != ContentSource.INDIE]

            add_span_attributes(**{"search.sources": [s.value for s in sources]})

            # Run searches in parallel
            search_tasks = []

            if ContentSource.LOCAL in sources:
                search_tasks.append(
                    self._search_local_catalog(
                        query, formats, limit + offset,
                        year_min=year_min, year_max=year_max,
                        min_lexile=min_lexile, max_lexile=max_lexile,
                        language=language,
                        available_only=available_only,
                        sort_by=sort_by,
                        sort_direction=sort_direction,
                        is_large_print=is_large_print,
                        publisher=publisher,
                        location=location,
                        subject_facets=subject_facets,
                        author_facets=author_facets,
                        series_facets=series_facets,
                    )
                )

            if ContentSource.INDIE in sources:
                search_tasks.append(
                    self._search_indie_ebooks(
                        query, formats, limit + offset,
                        year_min=year_min, year_max=year_max,
                        language=language,
                    )
                )

            # Run sources sequentially inside an overall 30 s timeout. They
            # share one AsyncSession (self.db), which is NOT safe for
            # concurrent use: gathering them raced on connection provisioning
            # and silently dropped local catalog results (SQLAlchemy
            # InvalidRequestError "session is provisioning a new connection").
            # Sequential keeps the shared session correct; two local DB queries
            # on one connection cannot truly parallelize anyway. The timeout
            # still bounds a slow source per issue #1306.
            with tracer.start_as_current_span("unified_search.sources"):
                raw_results = []

                async def _run_sources():
                    for coro in search_tasks:
                        raw_results.append(await coro)

                try:
                    await asyncio.wait_for(_run_sources(), timeout=30)
                except asyncio.TimeoutError:
                    logger.warning(
                        "unified_search timeout",
                        extra={
                            "completed": len(raw_results),
                            "total": len(search_tasks),
                        },
                    )
                    # Close source coroutines that never started, then pad so
                    # downstream zip/merge stays aligned with searched_sources.
                    for coro in search_tasks[len(raw_results):]:
                        coro.close()
                    while len(raw_results) < len(search_tasks):
                        raw_results.append(([], 0))

            # Same order tasks were appended to search_tasks above: local then indie.
            searched_sources: list[ContentSource] = []
            if ContentSource.LOCAL in sources:
                searched_sources.append(ContentSource.LOCAL)
            if ContentSource.INDIE in sources:
                searched_sources.append(ContentSource.INDIE)

            # raw_results is a list of (results, total) tuples, in task order
            per_source: list[tuple[list[UnifiedSearchResult], int]] = list(raw_results)

            sources_searched: list[str] = [s.value for s in searched_sources]
            source_counts: dict[str, int] = {
                s.value: total for s, (_results, total) in zip(searched_sources, per_source)
            }

            paginated, total_results, has_more = _merge_and_paginate(
                per_source,
                offset=offset,
                limit=limit,
                sort_by=sort_by,
                sort_direction=sort_direction,
                deduplicate=deduplicate,
            )

            elapsed_ms = (utc_now() - start_time).total_seconds() * 1000

            return UnifiedSearchResponse(
                query=query,
                total_results=total_results,
                results=paginated,
                sources_searched=sources_searched,
                source_counts=source_counts,
                search_time_ms=round(elapsed_ms, 1),
                has_more=has_more,
            )

    # =========================================================================
    # Local Catalog Search
    # =========================================================================

    async def _search_local_catalog(
        self,
        query: str,
        formats: list[ContentFormat] | None,
        limit: int,
        *,
        year_min: int | None = None,
        year_max: int | None = None,
        min_lexile: int | None = None,
        max_lexile: int | None = None,
        language: list[str] | None = None,
        available_only: bool = False,
        sort_by: str | None = None,
        sort_direction: str | None = None,
        is_large_print: bool | None = None,
        publisher: str | None = None,
        location: str | None = None,
        subject_facets: list[str] | None = None,
        author_facets: list[str] | None = None,
        series_facets: list[str] | None = None,
    ) -> tuple[list[UnifiedSearchResult], int]:
        try:
            # Imported inside the method to avoid a circular import (catalog.helpers imports back into services).
            from ..api.v1.catalog.helpers import _execute_catalog_search
            from ..models.catalog import ItemType as _ItemType

            item_types_sql: list[_ItemType] | None = None
            if formats:
                item_types_sql = []
                for f in formats:
                    # Skip unknown formats; the enum has been extended without DB sync at times.
                    with contextlib.suppress(ValueError):
                        item_types_sql.append(_ItemType(f.value))
                item_types_sql = item_types_sql or None

            is_browse = query in ("", "*")
            result = await _execute_catalog_search(
                self.db,
                q=None if is_browse else query,
                item_types=item_types_sql,
                year_min=year_min,
                year_max=year_max,
                min_lexile=min_lexile,
                max_lexile=max_lexile,
                language=language,
                status=ItemStatus.available if available_only else None,
                publisher=publisher,
                location=location,
                subject_facets=subject_facets,
                author_facets=author_facets,
                series_facets=series_facets,
                sort_by=sort_by,
                sort_direction=sort_direction,
                is_large_print=is_large_print,
                page=1,
                per_page=min(limit, MAX_MERGE_WINDOW),  # cap; cross-source pagination drift is a documented known limitation
                current_user=None,  # anonymous: PUBLIC + CATALOGED only
            )
            items = result.get("items", [])
            total = int(result.get("total", len(items)))

            results: list[UnifiedSearchResult] = []
            for item in items:
                raw_type = item.get("item_type")
                content_format = self._FORMAT_MAP.get(
                    raw_type if isinstance(raw_type, str) else "other",
                    ContentFormat.OTHER,
                )
                # No Python post-filter on `content_format` here: the
                # `formats` filter is now SQL-authoritative via item_types
                # push-down. Keeping a redundant Python check would be a
                # new silent-drop vector if _FORMAT_MAP and ItemType drift
                # apart again (a ContentFormat without a _FORMAT_MAP entry
                # would coerce to OTHER, fail the post-filter, and the row
                # would vanish despite SQL having approved it).

                subjects_val = item.get("subjects")
                if isinstance(subjects_val, list):
                    subjects = subjects_val
                elif isinstance(subjects_val, str) and subjects_val:
                    # Shared parser handles comma, semicolon, and legacy
                    # array-literal shapes -- the previous comma-only split
                    # dropped both semicolon-delimited rows and the
                    # ``"['Fiction','Memoir']"`` shape entirely.
                    subjects = parse_subjects_field(subjects_val)
                else:
                    subjects = []

                isbn = item.get("isbn")
                dedup_key = isbn or hashlib.md5(
                    f"{item.get('title','')}:{item.get('author','') or ''}".lower().encode()
                ).hexdigest()

                results.append(UnifiedSearchResult(
                    id=f"local:{item.get('id')}",
                    source=ContentSource.LOCAL,
                    source_id=str(item.get("id")),
                    title=item.get("title", ""),
                    author=item.get("author"),
                    authors=[item["author"]] if item.get("author") else [],
                    format=content_format,
                    description=item.get("description"),
                    cover_url=item.get("cover_url"),
                    isbn=isbn,
                    publisher=item.get("publisher"),
                    publication_year=item.get("publication_year"),
                    subjects=subjects,
                    is_available=(item.get("status") == "available"),
                    relevance_score=1.0,
                    dedup_key=dedup_key,
                ))
            return results, total
        except Exception:
            logger.exception("Local catalog search failed for query: %s", query)
            return [], 0


    # =========================================================================
    # Indie Ebook Search (MetisLib)
    # =========================================================================

    async def _search_indie_ebooks(
        self,
        query: str,
        formats: list[ContentFormat] | None,
        limit: int,
        *,
        year_min: int | None = None,
        year_max: int | None = None,
        language: list[str] | None = None,
    ) -> tuple[list[UnifiedSearchResult], int]:
        """Read owned indie_ebooks table. MetisLib client call removed (Tier-3 cutover)."""
        if formats and ContentFormat.EBOOK not in formats:
            return [], 0
        try:
            from sqlalchemy import func, or_, select
            from ..models.indie_ebook_borrow import IndieEbook

            is_browse = query in ("", "*")
            stmt = select(IndieEbook).where(
                IndieEbook.title.isnot(None),
                IndieEbook.copies_owned > 0,
            )
            if not is_browse and query.strip():
                pattern = f"%{query.strip()}%"
                stmt = stmt.where(
                    or_(
                        IndieEbook.title.ilike(pattern),
                        IndieEbook.author_pen_name.ilike(pattern),
                        IndieEbook.description.ilike(pattern),
                    )
                )

            count_stmt = select(func.count()).select_from(stmt.subquery())
            total = int((await self.db.execute(count_stmt)).scalar() or 0)

            rows = (await self.db.execute(stmt.limit(min(limit, MAX_MERGE_WINDOW)))).scalars().all()

            results = []
            for row in rows:
                isbn = row.isbn
                title = row.title or ""
                author = row.author_pen_name or None
                dedup_key = isbn or hashlib.md5(
                    f"{title}:{author or ''}".lower().encode()
                ).hexdigest()
                results.append(UnifiedSearchResult(
                    id=f"indie:{row.id}",
                    source=ContentSource.INDIE,
                    source_id=str(row.id),
                    title=title,
                    author=author,
                    authors=[author] if author else [],
                    format=ContentFormat.EBOOK,
                    format_details=["epub"],
                    description=row.description,
                    cover_url=row.cover_url,
                    isbn=isbn,
                    publication_year=row.publication_year,
                    subjects=[],
                    language=row.language or "en",
                    is_available=(row.copies_available or 0) > 0,
                    download_formats=["epub"],
                    relevance_score=0.9,
                    dedup_key=dedup_key,
                ))

            if year_min is not None:
                results = [r for r in results
                           if r.publication_year is not None
                           and r.publication_year >= year_min]
            if year_max is not None:
                results = [r for r in results
                           if r.publication_year is not None
                           and r.publication_year <= year_max]
            return results, total
        except Exception:
            logger.exception("Indie ebook search failed for query: %s", query)
            return [], 0

def get_unified_search_service(db):
    return UnifiedSearchService(db)

# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

import base64
import binascii
import re
import json
from app.core.logging import get_logger
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import and_, or_, select, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.config import get_settings
from ..core.branding import branding
from ..models.announcements import Announcement, AnnouncementStatus
from ..models.catalog import CatalogItem, CatalogingStatus
from ..models.event import Event
from ..services.organization_features_service import OrganizationFeaturesService
from . import search_analytics_service as analytics

logger = get_logger(__name__)

# Curated list of patron-facing pages for navigation search.
# Each entry: (title, url, description, keywords, feature_flag)
# feature_flag is None for always-on pages.
# Add new pages here when new public routes are created.
_STATIC_PAGES: list[tuple[str, str, str, list[str], str | None]] = [
    ("Events", "/events", "Library events, workshops, classes, and programs", ["calendar", "classes", "workshops", "programs", "activities", "things to do"], "events_enabled"),
    ("Catalog", "/catalog", "Search and browse books, DVDs, and other library materials", ["books", "search", "browse", "borrow", "checkout", "holds", "dvd", "music"], None),
    ("Digital Resources", "/digital", "Online databases, ebooks, and digital library resources", ["online", "databases", "digital", "resources", "remote access"], None),
    ("eBooks", "/digital", "Borrow digital books and ebooks", ["ebooks", "kindle", "palace project", "digital books", "download"], None),
    ("Streaming", "/streaming", "Stream movies, music, and video content", ["movies", "video", "music", "stream", "palace project"], "streaming_enabled"),
    ("AI Tools", "/ai", "Artificial intelligence tools and resources for library patrons", ["ai", "artificial intelligence", "chatgpt", "chatbot"], "ai_tools_enabled"),
    ("FAQ", "/faq", "Frequently asked questions about library services", ["faq", "questions", "help", "how to", "information"], None),
    ("About", "/about/library", f"About {branding.library_name}", ["about", "library", "history", "mission", "hours", "location"], None),
    ("Contact", "/contact", "Contact the library, hours, and location", ["contact", "address", "phone", "email", "hours", "location", "directions"], None),
    ("Programs", "/programs", "Reading programs and challenges", ["reading programs", "summer reading", "challenges", "reading logs"], "reading_programs_enabled"),
    ("Room Booking", "/rooms", "Reserve a meeting room or study room", ["room", "meeting room", "study room", "reserve", "book a room", "conference"], "meeting_rooms_enabled"),
    ("Makerspace", "/makerspace", "3D printing, equipment, and makerspace workshops", ["makerspace", "3d printing", "laser", "equipment", "workshop", "make"], "makerspace_enabled"),
    ("WiFi", "/wifi", "Library WiFi access and hotspot information", ["wifi", "internet", "wireless", "hotspot", "network"], None),
    ("Tech Support", "/tech", "Technology help and support for library patrons", ["tech", "technology", "computer", "help", "support", "printing", "wifi"], None),
    ("Donate", "/donate", "Donate to the library", ["donate", "donation", "support", "give", "fundraise"], None),
    ("Get a Library Card", "/card-application", "Apply for a library card", ["library card", "card", "apply", "sign up", "register", "membership"], None),
    ("Announcements", "/announcements", "Library news and announcements", ["announcements", "news", "updates", "notices"], None),
    ("Youth Services", "/youth", "Programs and resources for children and teens", ["youth", "kids", "children", "teen", "homework", "after school"], "community_features_enabled"),
    ("Book Clubs", "/book-clubs", "Library book clubs and reading groups", ["book club", "reading group", "discussion", "group"], "book_clubs_enabled"),
    ("Interlibrary Loan", "/interlibrary-loan", "Request books from other libraries", ["interlibrary loan", "ill", "request", "borrow from other library"], "ill_enabled"),
    ("Careers", "/careers", "Job openings at the library", ["careers", "jobs", "employment", "hiring", "work"], None),
    ("Guides", "/guides", "How-to guides for library services", ["guides", "how to", "tutorial", "instructions", "help"], None),
    ("Indie Authors", "/indie", "Local and independent author ebooks and audiobooks", ["indie", "independent", "local authors", "self-published"], "indie_platform_enabled"),
    ("Genealogy", "/genealogy", "Genealogy resources and research help", ["genealogy", "family history", "ancestry", "records", "family tree"], "genealogy_enabled"),
    ("Business Resources", "/business", "Resources for local businesses and entrepreneurs", ["business", "entrepreneur", "small business", "research", "economic"], None),
    ("Community Resources", "/community", "Community programs and social services", ["community", "social services", "resources", "nonprofit", "assistance"], "community_features_enabled"),
    ("Ask a Librarian", "/ask-librarian", "Get help from a librarian", ["ask", "librarian", "reference", "help", "question", "research help"], None),
    ("Privacy Policy", "/privacy", "Library privacy policy", ["privacy", "data", "policy"], None),
    ("Strategic Plan", "/strategic-plan", "Library strategic plan and goals", ["strategic plan", "goals", "mission", "future"], "strategic_planning_enabled"),
    ("Reading Challenge", "/reading-challenge", "Reading challenges and gamification", ["reading challenge", "gamification", "badges", "achievements"], "gamification_enabled"),
    ("Learning Paths", "/learning-paths", "Structured learning paths and courses", ["learning", "courses", "education", "training", "skills"], "learning_platform_enabled"),
]

# Caps the popularity contribution to score so a popular item can't drown out
# a clearly more-relevant unpopular item. ln(1+checkouts) * coeff, capped.
_POPULARITY_COEFF = 0.05
_POPULARITY_CAP = 0.4


@dataclass
class SiteSearchResult:

    id: str
    entity_type: str
    title: str
    snippet: str | None
    url: str
    score: float
    source: str

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "entity_type": self.entity_type,
            "title": self.title,
            "snippet": self.snippet,
            "url": self.url,
            "score": round(self.score, 3),
            "source": self.source,
        }


@dataclass
class SiteSearchResponse:

    query: str
    total_results: int
    results: list[SiteSearchResult]
    page: int
    per_page: int
    has_more: bool
    facets: dict[str, int] = field(default_factory=dict)
    next_cursor: str | None = None
    did_you_mean: str | None = None

    def to_dict(self) -> dict:
        return {
            "query": self.query,
            "total_results": self.total_results,
            "results": [result.to_dict() for result in self.results],
            "page": self.page,
            "per_page": self.per_page,
            "has_more": self.has_more,
            "facets": self.facets,
            "next_cursor": self.next_cursor,
            "did_you_mean": self.did_you_mean,
        }


def _encode_cursor(score: float, result_id: str) -> str:
    payload = json.dumps({"s": round(score, 6), "id": result_id})
    return base64.urlsafe_b64encode(payload.encode()).decode().rstrip("=")


def _decode_cursor(cursor: str | None) -> tuple[float, str] | None:
    if not cursor:
        return None
    try:
        padding = "=" * (-len(cursor) % 4)
        raw = base64.urlsafe_b64decode((cursor + padding).encode()).decode()
        data = json.loads(raw)
        return float(data["s"]), str(data["id"])
    except (binascii.Error, json.JSONDecodeError, UnicodeDecodeError, ValueError, TypeError, KeyError) as exc:
        fingerprint = f"len={len(cursor)} prefix={cursor[:8]!r}"
        logger.warning("Malformed site-search cursor (%s): %s; falling back to page 1", type(exc).__name__, fingerprint)
        return None


class SiteSearchService:

    def __init__(self, db: AsyncSession):
        self.db = db
        # Default False when the engine is not bound yet: the FTS branch issues
        # Postgres-specific tsquery SQL, while ILIKE is dialect-portable. Graceful
        # degradation matches the module-level contract.
        self._is_postgres = bool(db.bind) and db.bind.dialect.name == "postgresql"

    async def search(
        self,
        query: str,
        *,
        page: int = 1,
        per_page: int = 20,
        cursor: str | None = None,
        entity_types: list[str] | None = None,
        user_id: int | None = None,
    ) -> SiteSearchResponse:
        query = query.strip()
        if not query:
            return SiteSearchResponse(
                query=query,
                total_results=0,
                results=[],
                page=page,
                per_page=per_page,
                has_more=False,
            )

        search_term = f"%{query}%"

        catalog_results = await self._search_catalog(search_term, query, limit=per_page * 2)
        ebook_results = await self._search_ebooks(query, limit=per_page)

        events_results: list[SiteSearchResult] = []
        if await OrganizationFeaturesService.is_feature_enabled(self.db, "events_enabled"):
            events_results = await self._search_events(search_term, query, limit=per_page)

        announcement_results = await self._search_announcements(search_term, query, limit=per_page)
        page_results = await self._search_pages(query)

        merged = [
            *catalog_results,
            *ebook_results,
            *events_results,
            *announcement_results,
            *page_results,
        ]

        # Dedup ebooks by title — same title can appear from both L30 local and MetisLib network
        seen_ebook_titles: dict[str, SiteSearchResult] = {}
        deduped: list[SiteSearchResult] = []
        for item in merged:
            if item.entity_type == "ebook":
                key = (item.title or "").lower()
                if key in seen_ebook_titles:
                    if item.score > seen_ebook_titles[key].score:
                        seen_ebook_titles[key] = item
                else:
                    seen_ebook_titles[key] = item
            else:
                deduped.append(item)
        deduped.extend(seen_ebook_titles.values())

        # Apply CTR boosts from past clicks on this query.
        boosts = await analytics.ctr_boosts_for_query(self.db, query)
        if boosts:
            for item in deduped:
                bump = boosts.get(item.id)
                if bump:
                    item.score += bump

        # Facets are computed BEFORE entity_type filtering so the user can
        # see counts in other buckets they could click into.
        facets = dict(Counter(item.entity_type for item in deduped))

        if entity_types:
            allowed = set(entity_types)
            deduped = [item for item in deduped if item.entity_type in allowed]

        deduped.sort(key=lambda item: (-item.score, item.id))
        total = len(deduped)

        # Pagination: cursor takes precedence over page when supplied.
        decoded = _decode_cursor(cursor)
        if decoded is not None:
            anchor_score, anchor_id = decoded
            page_items: list[SiteSearchResult] = []
            for item in deduped:
                if (-item.score, item.id) > (-anchor_score, anchor_id):
                    page_items.append(item)
                    if len(page_items) >= per_page:
                        break
            paginated = page_items
            has_more = False
            if paginated:
                last = paginated[-1]
                # has_more if any item ranks strictly after the last returned item
                has_more = any(
                    (-i.score, i.id) > (-last.score, last.id) for i in deduped
                )
            next_cursor = (
                _encode_cursor(paginated[-1].score, paginated[-1].id)
                if paginated and has_more
                else None
            )
            response_page = page
        else:
            offset = (page - 1) * per_page
            paginated = deduped[offset: offset + per_page]
            has_more = total > (offset + per_page)
            next_cursor = (
                _encode_cursor(paginated[-1].score, paginated[-1].id)
                if paginated and has_more
                else None
            )
            response_page = page

        # Suggest a similar past query when this one underperformed.
        suggestion: str | None = None
        if total < 3:
            suggestion = await analytics.did_you_mean(self.db, query)
            if suggestion and suggestion == analytics.normalize_query(query):
                suggestion = None

        await analytics.log_query(
            self.db, query=query, result_count=total, user_id=user_id
        )

        return SiteSearchResponse(
            query=query,
            total_results=total,
            results=paginated,
            page=response_page,
            per_page=per_page,
            has_more=has_more,
            facets=facets,
            next_cursor=next_cursor,
            did_you_mean=suggestion,
        )

    async def _search_pages(self, query: str) -> list[SiteSearchResult]:
        q = query.lower()
        results = []
        for title, url, description, keywords, feature_flag in _STATIC_PAGES:
            if feature_flag and not await OrganizationFeaturesService.is_feature_enabled(self.db, feature_flag):
                continue
            title_lower = title.lower()
            desc_lower = description.lower()
            matched = (
                q in title_lower
                or q in desc_lower
                or any(q in kw for kw in keywords)
            )
            if matched:
                score = 1.0 if q == title_lower else 0.9
                results.append(SiteSearchResult(
                    id=f"page:{url}",
                    entity_type="page",
                    title=title,
                    snippet=description,
                    url=url,
                    score=score,
                    source="pages",
                ))
        return results

    async def _search_catalog(self, search_term: str, query: str, *, limit: int) -> list[SiteSearchResult]:
        if self._is_postgres:
            try:
                results = await self._search_catalog_fts(query, limit=limit)
                if results:
                    return results
            except SQLAlchemyError:
                logger.debug("FTS catalog search failed, falling back to ILIKE", exc_info=True)
        return await self._search_catalog_ilike(search_term, query, limit=limit)

    async def _search_catalog_fts(self, query: str, *, limit: int) -> list[SiteSearchResult]:
        tsquery = _build_tsquery(query)
        stmt = text(
            """
            WITH q AS (SELECT to_tsquery('english', :tsquery) AS tsq)
            SELECT
                ci.id,
                ci.title,
                ci.author,
                ci.description,
                ci.total_checkouts,
                ts_rank_cd(ci.search_tsv, q.tsq) AS rank
            FROM catalog_items ci, q
            WHERE ci.cataloging_status = 'cataloged'
              AND ci.search_tsv @@ q.tsq
            ORDER BY rank DESC, ci.total_checkouts DESC NULLS LAST
            LIMIT :limit
            """
        )
        rows = (await self.db.execute(stmt, {"tsquery": tsquery, "limit": limit})).all()

        import math

        results: list[SiteSearchResult] = []
        for row in rows:
            popularity = min(
                _POPULARITY_CAP,
                math.log1p(int(row.total_checkouts or 0)) * _POPULARITY_COEFF,
            )
            base = 0.8 + min(0.5, float(row.rank or 0.0))
            snippet = row.description or row.author
            results.append(
                SiteSearchResult(
                    id=f"catalog:{row.id}",
                    entity_type="catalog",
                    title=row.title,
                    snippet=_truncate(snippet),
                    url=f"/catalog/{row.id}",
                    score=base + popularity,
                    source="catalog",
                )
            )

        return results

    async def _search_catalog_ilike(self, search_term: str, query: str, *, limit: int) -> list[SiteSearchResult]:
        stmt = (
            select(
                CatalogItem.id,
                CatalogItem.title,
                CatalogItem.author,
                CatalogItem.description,
                CatalogItem.total_checkouts,
            )
            .where(
                and_(
                    CatalogItem.cataloging_status == CatalogingStatus.CATALOGED,
                    or_(
                        CatalogItem.title.ilike(search_term),
                        CatalogItem.author.ilike(search_term),
                        CatalogItem.description.ilike(search_term),
                    ),
                )
            )
            .order_by(CatalogItem.total_checkouts.desc().nullslast(), CatalogItem.title.asc())
            .limit(limit)
        )
        rows = (await self.db.execute(stmt)).all()

        import math

        results: list[SiteSearchResult] = []
        for row in rows:
            popularity = min(
                _POPULARITY_CAP,
                math.log1p(int(row.total_checkouts or 0)) * _POPULARITY_COEFF,
            )
            snippet = row.description or row.author
            results.append(
                SiteSearchResult(
                    id=f"catalog:{row.id}",
                    entity_type="catalog",
                    title=row.title,
                    snippet=_truncate(snippet),
                    url=f"/catalog/{row.id}",
                    score=0.8 + _score_text(query, row.title, row.description) + popularity,
                    source="catalog",
                )
            )

        return results

    async def _search_ebooks(self, query: str, *, limit: int) -> list[SiteSearchResult]:
        settings = get_settings()
        if not settings.metislib_enabled:
            return []
        try:
            from .metislib_client import get_metislib_client
            client = get_metislib_client()
            data = await client.search_catalog(query=query, per_page=limit)
            items = data.get("items", [])
        except Exception:  # noqa: BLE001 -- federated source optional: skip MetisLib results on any failure, other sources continue
            logger.debug("MetisLib search unavailable, skipping ebooks", exc_info=True)
            return []

        results: list[SiteSearchResult] = []
        for item in items:
            title = item.get("title", "")
            author = item.get("author_name", "")
            desc = item.get("description", "")
            snippet = desc or author
            results.append(
                SiteSearchResult(
                    id=f"ebook:{item.get('id')}",
                    entity_type="ebook",
                    title=title,
                    snippet=_truncate(snippet),
                    url=f"/ebooks/{item.get('id')}",
                    score=0.75 + _score_text(query, title, desc),
                    source="ebooks",
                )
            )
        return results

    async def _search_events(self, search_term: str, query: str, *, limit: int) -> list[SiteSearchResult]:
        now = datetime.now(timezone.utc)
        stmt = (
            select(
                Event.id,
                Event.title,
                Event.description,
                Event.location,
                Event.start_time
            )
            .where(
                and_(
                    Event.is_published.is_(True),
                    or_(
                        Event.title.ilike(search_term),
                        Event.description.ilike(search_term),
                        Event.location.ilike(search_term),
                    ),
                    or_(
                        Event.end_time >= now,
                        and_(Event.end_time.is_(None), Event.start_time >= now),
                    ),
                )
            )
            .order_by(Event.start_time.asc())
            .limit(limit)
        )
        rows = (await self.db.execute(stmt)).all()

        results: list[SiteSearchResult] = []
        for row in rows:
            snippet = row.description or row.location
            results.append(
                SiteSearchResult(
                    id=f"event:{row.id}",
                    entity_type="event",
                    title=row.title,
                    snippet=_truncate(snippet),
                    url=f"/events/detail/{row.id}",
                    score=0.6 + _score_text(query, row.title, row.description),
                    source="events",
                )
            )
        return results

    async def _search_announcements(self, search_term: str, query: str, *, limit: int) -> list[SiteSearchResult]:
        now = datetime.now(timezone.utc)
        stmt = (
            select(
                Announcement.id,
                Announcement.title,
                Announcement.content
            )
            .where(
                and_(
                    Announcement.active.is_(True),
                    Announcement.status == AnnouncementStatus.PUBLISHED,
                    or_(
                        Announcement.starts_at.is_(None),
                        Announcement.starts_at <= now,
                    ),
                    or_(
                        Announcement.ends_at.is_(None),
                        Announcement.ends_at >= now,
                    ),
                    or_(
                        Announcement.title.ilike(search_term),
                        Announcement.content.ilike(search_term),
                    ),
                )
            )
            .order_by(Announcement.updated_at.desc())
            .limit(limit)
        )
        rows = (await self.db.execute(stmt)).all()

        results: list[SiteSearchResult] = []
        for row in rows:
            results.append(
                SiteSearchResult(
                    id=f"announcement:{row.id}",
                    entity_type="announcement",
                    title=row.title,
                    snippet=_truncate(row.content),
                    url=f"/announcements#announcement-{row.id}",
                    score=0.5 + _score_text(query, row.title, row.content),
                    source="announcements",
                )
            )
        return results


def _truncate(value: Optional[str], max_len: int = 180) -> str | None:
    if not value:
        return None
    compact = " ".join(value.split())
    if len(compact) <= max_len:
        return compact
    return f"{compact[: max_len - 1].rstrip()}…"


def get_site_search_service(db: AsyncSession) -> SiteSearchService:
    return SiteSearchService(db)


def _score_text(query: str, title: Optional[str], body: Optional[str]) -> float:
    query_lower = query.lower()
    title_lower = (title or "").lower()
    body_lower = (body or "").lower()

    if query_lower == title_lower:
        return 1.0
    if title_lower.startswith(query_lower):
        return 0.85
    if query_lower in title_lower:
        return 0.7
    if query_lower in body_lower:
        return _score_body_match(body_lower)
    return 0.2


# Body-match scoring: short focused bodies score higher than long ones with
# the same hit. Caps at 0.45 (preserving title-match dominance: any title
# hit is >= 0.7). Decays as 1/sqrt(words/_BODY_REFERENCE_WORDS), floored at
# 0.225 so a long-body hit still outranks a no-match (0.2).
_BODY_REFERENCE_WORDS = 50  # ~paragraph; bodies at/below this score the cap
_BODY_SCORE_FLOOR = 0.225
_BODY_SCORE_CAP = 0.45


def _score_body_match(body_lower: str) -> float:
    import math

    word_count = len(body_lower.split()) or 1
    ratio = word_count / _BODY_REFERENCE_WORDS
    if ratio <= 1.0:
        return _BODY_SCORE_CAP
    decayed = _BODY_SCORE_FLOOR + (_BODY_SCORE_CAP - _BODY_SCORE_FLOOR) / math.sqrt(ratio)
    return max(_BODY_SCORE_FLOOR, min(_BODY_SCORE_CAP, decayed))


def _build_tsquery(query: str) -> str:
    cleaned = re.sub(r"[!&|():*<>\\\'\"]", " ", query)
    words = cleaned.split()
    if not words:
        return "''"
    if len(words) == 1:
        return f"{words[0]}:*"
    parts = list(words[:-1])
    parts.append(f"{words[-1]}:*")
    return " & ".join(parts)

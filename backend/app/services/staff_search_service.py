# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional
from difflib import SequenceMatcher

from sqlalchemy import and_, or_, select, func, cast, String, false
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from ..api.v1.staff.patrons_schemas import CardStatusFilter
from ..models.user import User, PatronStatus, UserRole, name_search_clause, name_or_email_clause, email_match_clause
from ..models.catalog import CatalogItem, ItemStatus
from ..models.circulation import Checkout, CheckoutStatus
from ..models.event import Event
from ..models.recent_search import RecentSearch


def _card_status_clause(card_status: CardStatusFilter, now: Optional[datetime] = None):
    if card_status == CardStatusFilter.any:
        return None
    anchor = now or datetime.now(timezone.utc)
    today_date = anchor.date()
    today_start = datetime.combine(today_date, datetime.min.time(), tzinfo=timezone.utc)
    plus_30d_end = datetime.combine(today_date + timedelta(days=30), datetime.max.time(), tzinfo=timezone.utc)
    plus_90d_end = datetime.combine(today_date + timedelta(days=90), datetime.max.time(), tzinfo=timezone.utc)
    if card_status == CardStatusFilter.expired:
        return User.card_expires_at < today_start
    if card_status == CardStatusFilter.expiring_30d:
        return and_(
            User.card_expires_at >= today_start,
            User.card_expires_at <= plus_30d_end,
        )
    if card_status == CardStatusFilter.expiring_90d:
        return and_(
            User.card_expires_at >= today_start,
            User.card_expires_at <= plus_90d_end,
        )
    if card_status == CardStatusFilter.active:
        return or_(
            User.card_expires_at >= today_start,
            User.card_expires_at.is_(None),
        )
    return None


@dataclass
class StaffSearchResult:

    id: str
    entity_type: str  # 'patron', 'item', 'checkout', 'event'
    title: str
    subtitle: str | None = None
    snippet: str | None = None
    url: str | None = None
    score: float = 0.0
    source: str = "local"
    metadata: dict | None = None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "entity_type": self.entity_type,
            "title": self.title,
            "subtitle": self.subtitle,
            "snippet": self.snippet,
            "url": self.url,
            "score": round(self.score, 3),
            "source": self.source,
            "metadata": self.metadata or {},
        }


@dataclass
class StaffSearchResponse:

    query: str
    total_results: int
    results: list[StaffSearchResult]
    page: int
    per_page: int
    has_more: bool
    suggestions: list[str] | None = None

    def to_dict(self) -> dict:
        return {
            "query": self.query,
            "total_results": self.total_results,
            "results": [result.to_dict() for result in self.results],
            "page": self.page,
            "per_page": self.per_page,
            "has_more": self.has_more,
            "suggestions": self.suggestions or [],
        }


def _escape_ilike(value: str) -> str:
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def _normalized_contact_search(column, search_text: str):
    safe_text = _escape_ilike(search_text)
    return func.replace(
        func.replace(
            func.replace(
                func.replace(
                    func.replace(func.lower(func.coalesce(column, "")), "-", ""),
                    "(",
                    "",
                ),
                ")",
                "",
            ),
            " ",
            "",
        ),
        ".",
        "",
    ).ilike(f"%{safe_text}%")


_STAFF_ROLES = [
    UserRole.STAFF,
    UserRole.ADMIN,
    UserRole.SUPER_ADMIN,
    UserRole.DIRECTOR,
    UserRole.LEGAL,
]


class StaffSearchService:

    def __init__(self, db: AsyncSession):
        self.db = db

    async def search(
        self,
        query: str,
        *,
        user_id: int | None = None,
        page: int = 1,
        per_page: int = 20,
        entity_types: list[str] | None = None,
        card_status: CardStatusFilter = CardStatusFilter.any,
    ) -> StaffSearchResponse:
        query = query.strip()
        if not query:
            return StaffSearchResponse(
                query=query,
                total_results=0,
                results=[],
                page=page,
                per_page=per_page,
                has_more=False,
                suggestions=[],
            )

        # Track recent search
        if user_id:
            await self._track_recent_search(user_id, query)

        # Determine which entity types to search
        search_all = not entity_types or len(entity_types) == 0
        search_patrons = search_all or "patron" in entity_types
        search_staff = search_all or "staff" in entity_types
        search_items = search_all or "item" in entity_types
        search_checkouts = search_all or "checkout" in entity_types
        search_events = search_all or "event" in entity_types

        # Run parallel searches
        patron_results = (
            await self._search_patrons(query, limit=per_page * 2, card_status=card_status)
            if search_patrons
            else []
        )
        staff_results = (
            await self._search_staff(query, limit=per_page * 2)
            if search_staff
            else []
        )
        item_results = (
            await self._search_items(query, limit=per_page * 2)
            if search_items
            else []
        )
        checkout_results = (
            await self._search_checkouts(query, limit=per_page * 2)
            if search_checkouts
            else []
        )
        event_results = (
            await self._search_events(query, limit=per_page * 2)
            if search_events
            else []
        )

        # Merge and sort by score
        merged = [
            *patron_results,
            *staff_results,
            *item_results,
            *checkout_results,
            *event_results,
        ]
        merged.sort(key=lambda item: item.score, reverse=True)

        # Get suggestions for misspellings
        suggestions = self._get_suggestions(query, merged)

        total = len(merged)
        offset = (page - 1) * per_page
        paginated = merged[offset : offset + per_page]

        return StaffSearchResponse(
            query=query,
            total_results=total,
            results=paginated,
            page=page,
            per_page=per_page,
            has_more=total > (offset + per_page),
            suggestions=suggestions,
        )

    async def _search_patrons(
        self,
        query: str,
        *,
        limit: int,
        card_status: CardStatusFilter = CardStatusFilter.any,
    ) -> list[StaffSearchResult]:
        search_normalized = query.strip().lower()
        safe_search = _escape_ilike(search_normalized)
        search_term = f"%{safe_search}%"
        compact_search = "".join(ch for ch in search_normalized if ch.isalnum())

        # Names encrypted at rest: ilike on ciphertext is meaningless. Match
        # names via exact/last-prefix blind index instead of substring.
        text_filters = [
            User.phone_last4.ilike(search_term),
            User.library_card.ilike(search_term),
            User.city.ilike(search_term),
            User.state.ilike(search_term),
            User.zip_code.ilike(search_term),
        ]
        _name_clause = name_search_clause(search_normalized)
        if _name_clause is not None:
            text_filters.append(_name_clause)
        # Email encrypted: exact-match via hash, not substring.
        _email_clause = email_match_clause(search_normalized)
        if _email_clause is not None:
            text_filters.append(_email_clause)

        if compact_search:
            text_filters.extend([
                User.phone_last4.contains(compact_search[-4:]) if len(compact_search) >= 4 else User.phone_last4.contains(compact_search),
                _normalized_contact_search(User.library_card, compact_search),
            ])

        where_clauses = [
            User.role == UserRole.PATRON,
            or_(*text_filters),
        ]
        card_clause = _card_status_clause(card_status)
        if card_clause is not None:
            where_clauses.append(card_clause)

        stmt = (
            select(
                User.id,
                User.first_name,
                User.last_name,
                User.email,
                User.phone_last4,
                User.library_card,
                User.patron_status,
            )
            .where(and_(*where_clauses))
            .limit(limit)
        )
        rows = (await self.db.execute(stmt)).all()

        results: list[StaffSearchResult] = []
        for row in rows:
            full_name = f"{row.first_name} {row.last_name}".strip()
            score = self._score_match(query, full_name, row.email, row.phone_last4)

            results.append(
                StaffSearchResult(
                    id=f"patron:{row.id}",
                    entity_type="patron",
                    title=full_name,
                    subtitle=f"ID: {row.library_card}" if row.library_card else None,
                    snippet=row.email,
                    url=f"/staff/patrons/{row.id}",
                    score=score,
                    source="patrons",
                    metadata={
                        "status": row.patron_status,
                        "email": row.email,
                        "phone_last4": row.phone_last4,
                        "library_card": row.library_card,
                    },
                )
            )

        return results

    async def _search_staff(self, query: str, *, limit: int) -> list[StaffSearchResult]:
        safe_search = _escape_ilike(query.strip().lower())
        search_term = f"%{safe_search}%"

        stmt = (
            select(
                User.id,
                User.first_name,
                User.last_name,
                User.email,
                User.role,
                User.is_active,
            )
            .where(
                and_(
                    User.role.in_(_STAFF_ROLES),
                    # Names + email encrypted: blind-index match, not substring.
                    name_or_email_clause(query) if name_or_email_clause(query) is not None else false(),
                )
            )
            .limit(limit)
        )
        rows = (await self.db.execute(stmt)).all()

        results: list[StaffSearchResult] = []
        for row in rows:
            full_name = f"{row.first_name} {row.last_name}".strip()
            score = self._score_match(query, full_name, row.email)

            results.append(
                StaffSearchResult(
                    id=f"staff:{row.id}",
                    entity_type="staff",
                    title=full_name,
                    subtitle=row.role,
                    snippet=row.email,
                    url=f"/staff/directory",
                    score=score * 0.90,
                    source="staff",
                    metadata={
                        "role": row.role,
                        "email": row.email,
                        "is_active": row.is_active,
                    },
                )
            )

        return results

    async def _search_items(self, query: str, *, limit: int) -> list[StaffSearchResult]:
        safe_search = _escape_ilike(query.strip().lower())
        search_term = f"%{safe_search}%"

        stmt = (
            select(
                CatalogItem.id,
                CatalogItem.title,
                CatalogItem.author,
                CatalogItem.isbn,
                CatalogItem.barcode,
                CatalogItem.item_type,
                CatalogItem.status,
                CatalogItem.publisher,
            )
            .where(
                or_(
                    CatalogItem.title.ilike(search_term),
                    CatalogItem.author.ilike(search_term),
                    CatalogItem.isbn.ilike(search_term),
                    CatalogItem.barcode.ilike(search_term),
                    CatalogItem.subjects.ilike(search_term),
                    CatalogItem.description.ilike(search_term),
                )
            )
            .limit(limit)
        )
        rows = (await self.db.execute(stmt)).all()

        results: list[StaffSearchResult] = []
        for row in rows:
            score = self._score_match(
                query, row.title, row.author or "", row.isbn or "", row.barcode or ""
            )

            snippet = f"ISBN: {row.isbn}" if row.isbn else (f"Barcode: {row.barcode}" if row.barcode else None)

            results.append(
                StaffSearchResult(
                    id=f"item:{row.id}",
                    entity_type="item",
                    title=row.title,
                    subtitle=row.author,
                    snippet=snippet,
                    url=f"/staff/catalog/{row.id}",
                    score=score * 0.95,  # Slightly lower priority than patrons
                    source="items",
                    metadata={
                        "isbn": row.isbn,
                        "barcode": row.barcode,
                        "item_type": row.item_type,
                        "status": row.status,
                        "publisher": row.publisher,
                    },
                )
            )

        return results

    async def _search_checkouts(
        self, query: str, *, limit: int
    ) -> list[StaffSearchResult]:
        search_term = f"%{query}%"

        stmt = (
            select(
                Checkout.id,
                Checkout.user_id,
                Checkout.item_id,
                Checkout.checked_out_at,
                Checkout.due_date,
                Checkout.status,
                User.first_name,
                User.last_name,
                User.email,
                CatalogItem.title,
                CatalogItem.author,
            )
            .join(User, Checkout.user_id == User.id, isouter=True)
            .join(CatalogItem, Checkout.item_id == CatalogItem.id, isouter=True)
            .where(
                or_(
                    CatalogItem.title.ilike(search_term),
                    CatalogItem.author.ilike(search_term),
                    # Patron name encrypted: blind-index match, not substring.
                    *([name_search_clause(query)] if name_search_clause(query) is not None else []),
                )
            )
            .limit(limit)
        )
        rows = (await self.db.execute(stmt)).all()

        results: list[StaffSearchResult] = []
        for row in rows:
            patron_name = (
                f"{row.first_name} {row.last_name}".strip() if row.first_name else "Unknown"
            )
            score = self._score_match(
                query, patron_name, row.title or "", row.author or ""
            )

            results.append(
                StaffSearchResult(
                    id=f"checkout:{row.id}",
                    entity_type="checkout",
                    title=f"{row.title or 'Unknown Item'}" if row.title else "Unknown Item",
                    subtitle=patron_name,
                    snippet=f"Due: {row.due_date.strftime('%m/%d/%Y') if row.due_date else 'N/A'}",
                    url=f"/staff/checkouts/{row.id}",
                    score=score * 0.85,  # Lower priority
                    source="checkouts",
                    metadata={
                        "checkout_status": row.status,
                        "due_date": row.due_date.isoformat() if row.due_date else None,
                        "patron_email": row.email,
                    },
                )
            )

        return results

    async def _search_events(self, query: str, *, limit: int) -> list[StaffSearchResult]:
        search_term = f"%{query}%"
        now = datetime.now(timezone.utc)

        stmt = (
            select(
                Event.id,
                Event.title,
                Event.description,
                Event.location,
                Event.start_time,
                Event.is_published,
            )
            .where(
                or_(
                    Event.title.ilike(search_term),
                    Event.description.ilike(search_term),
                    Event.location.ilike(search_term),
                )
            )
            .order_by(Event.start_time.desc())
            .limit(limit)
        )
        rows = (await self.db.execute(stmt)).all()

        results: list[StaffSearchResult] = []
        for row in rows:
            score = self._score_match(
                query, row.title, row.description or "", row.location or ""
            )

            results.append(
                StaffSearchResult(
                    id=f"event:{row.id}",
                    entity_type="event",
                    title=row.title,
                    subtitle=row.location,
                    snippet=_truncate(row.description),
                    url="/staff/events",
                    score=score * 0.80,  # Lower priority
                    source="events",
                    metadata={
                        "start_time": row.start_time.isoformat() if row.start_time else None,
                        "location": row.location,
                    },
                )
            )

        return results

    async def _track_recent_search(self, user_id: int, query: str) -> None:
        try:
            recent_search = RecentSearch(
                user_id=user_id,
                query=query,
                search_type="unified",
                result_count=0,
            )
            self.db.add(recent_search)
            await self.db.flush()
        except SQLAlchemyError:
            pass

    def _score_match(
        self, query: str, *fields: str
    ) -> float:
        query_lower = query.lower()
        best_score = 0.0

        for field in fields:
            if not field:
                continue

            field_lower = field.lower()

            # Exact match
            if query_lower == field_lower:
                best_score = max(best_score, 1.0)
                continue

            # Starts with match
            if field_lower.startswith(query_lower):
                best_score = max(best_score, 0.9)
                continue

            # Contains match
            if query_lower in field_lower:
                best_score = max(best_score, 0.75)
                continue

            # Fuzzy match using SequenceMatcher
            ratio = SequenceMatcher(None, query_lower, field_lower).ratio()
            if ratio > 0.6:  # Only count if >60% similar
                best_score = max(best_score, ratio * 0.7)  # Cap fuzzy matches at 0.7

        return best_score

    def _get_suggestions(
        self, query: str, results: list[StaffSearchResult]
    ) -> list[str]:
        suggestions = []

        if not results:
            return suggestions

        # Extract titles from results
        titles = [result.title for result in results if result.title]

        # Check for potential misspellings using fuzzy matching
        query_lower = query.lower()
        for title in titles[:5]:  # Check top 5 results
            title_lower = title.lower()

            # Check if query is similar to this title (typo detection)
            similarity = SequenceMatcher(None, query_lower, title_lower).ratio()
            if 0.7 < similarity < 0.95:  # Similar but not exact
                if title not in suggestions:
                    suggestions.append(title)

            # Check for partial matches that might be better
            if query_lower in title_lower and len(suggestions) < 3:
                if title not in suggestions:
                    suggestions.append(title)

        return suggestions[:3]  # Return top 3 suggestions


async def get_recent_searches(db: AsyncSession, user_id: int, limit: int = 10) -> list[str]:
    from sqlalchemy import func
    # Use subquery to get latest search per unique query text
    subq = (
        select(
            RecentSearch.query,
            func.max(RecentSearch.created_at).label("latest"),
        )
        .where(RecentSearch.user_id == user_id)
        .group_by(RecentSearch.query)
        .subquery()
    )
    stmt = (
        select(subq.c.query)
        .order_by(subq.c.latest.desc())
        .limit(limit)
    )
    rows = (await db.execute(stmt)).all()
    return [row.query for row in rows]


def get_staff_search_service(db: AsyncSession) -> StaffSearchService:
    return StaffSearchService(db)


def _truncate(value: str | None, max_len: int = 180) -> str | None:
    if not value:
        return None
    compact = " ".join(value.split())
    if len(compact) <= max_len:
        return compact
    return f"{compact[: max_len - 1].rstrip()}…"

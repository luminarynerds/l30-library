# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Staff - Patron Core Operations API Endpoints

This module provides endpoints for:
- Patron listing and search (with advanced filters)
- Patron details view
- Patron profile updates
- Patron context card (for card scanning)
- Patron statistics (dashboard)
"""

import contextlib
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from difflib import SequenceMatcher
from enum import StrEnum
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, Field
from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ....core.database import get_db
from ....core.pii_scope import filter_patron_data
from ....middleware.pii_filter import pii_filtered
from ....core.shortcuts import get_or_404
from ....core.rate_limit import limiter
from ....models.catalog import CatalogItem
from ....models.circulation import Checkout, CheckoutStatus, Hold, HoldStatus
from ....models.fine import Fine, FineStatus
from ....models.user import (
    User,
    UserRole,
    PatronStatus,
    name_blind_hash,
    name_search_clause,
    email_match_clause,
    email_blind_hash,
)
from ....schemas.circulation import CheckoutResponse, HoldResponse
from ....schemas.fine import FineResponse
from ....schemas.user import UserResponse, UserUpdate
from ..dependencies import require_staff
from ....services.reports.cache_invalidator import invalidate_patron_reports


from typing import List  # noqa: F401  (added by staff-main split)
from ....models.audit_log import AuditAction, AuditLog
from ....models.outreach import OutreachPartner
from ....models.patron_communication import MessageChannel, MessageStatus, PatronMessage  # noqa: F401
from ....services.patron_context_service import (
    AccountAlert,
    CheckoutSummary,
    HoldSummary,
    LoyaltyStatus,
    PatronContextCardResponse,
    RecentGenre,
    StaffNote,
    assemble_patron_context_card,
    assemble_patron_detail_fields,
)
from .patrons_schemas import (
    AtRiskCounts,
    AtRiskPatron,
    CardStatusFilter,
    ExpiringCardsCounts,
    LinkedAccountInfo,
    OverdueFilter,
    PatronActivityListResponse,
    PatronActivityResponse,
    PatronBlock,
    PatronExportData,
    PatronExportResponse,
    PatronFamilyResponse,
    PatronPhotoResponse,
    PatronPhotoUpload,
    PatronStatisticsResponse,
    PatronStatusUpdate,
)
from .patron_bulk_routes import router as patron_bulk_router
from .patron_circulation_routes import router as patron_circulation_router


def _cardholder_filter():
    return or_(User.role == UserRole.PATRON, User.library_card.isnot(None))


router = APIRouter(prefix="/staff/patrons", tags=["staff-patron-operations"])


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


def _card_status_today_bounds(now: Optional[datetime] = None):
    anchor = now or datetime.now(timezone.utc)
    today_date = anchor.date()
    today_start = datetime.combine(today_date, datetime.min.time(), tzinfo=timezone.utc)
    plus_30d_end = datetime.combine(
        today_date + timedelta(days=30), datetime.max.time(), tzinfo=timezone.utc
    )
    plus_90d_end = datetime.combine(
        today_date + timedelta(days=90), datetime.max.time(), tzinfo=timezone.utc
    )
    return today_start, plus_30d_end, plus_90d_end


def _card_status_clause(card_status: CardStatusFilter, now: Optional[datetime] = None):
    if card_status == CardStatusFilter.any:
        return None
    today_start, plus_30d_end, plus_90d_end = _card_status_today_bounds(now)
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


def _build_patron_search_filter(search: str):
    search_normalized = search.strip().lower()
    safe_search = _escape_ilike(search_normalized)
    compact_search = "".join(ch for ch in search_normalized if ch.isalnum())

    # first_name/last_name are encrypted at rest: ilike on ciphertext can't
    # work. Name matching is now exact-first/exact-last/last-name-prefix via
    # blind index (substring-anywhere dropped). The remaining fields are not
    # encrypted and keep substring search.
    fields = [
        User.library_card,
        User.phone_last4,
        User.city,
        User.state,
        User.zip_code,
    ]

    text_filters = [field.ilike(f"%{safe_search}%") for field in fields]

    name_clause = name_search_clause(search_normalized)
    if name_clause is not None:
        text_filters.append(name_clause)

    # Email encrypted: exact-match via hash (substring email search dropped).
    email_clause = email_match_clause(search_normalized)
    if email_clause is not None:
        text_filters.append(email_clause)

    if compact_search:
        text_filters.extend(
            [
                User.phone_last4.contains(compact_search[-4:])
                if len(compact_search) >= 4
                else User.phone_last4.contains(compact_search),
                _normalized_contact_search(User.library_card, compact_search),
            ]
        )

    return or_(*text_filters)


# =============================================================================
# Pydantic Schemas
# =============================================================================


class PatronDetailResponse(UserResponse):
    checkouts: list[CheckoutResponse] = []
    holds: list[HoldResponse] = []
    fines: list[FineResponse] = []
    total_fines_owed: Decimal = Decimal("0.00")
    patron_status: Optional[PatronStatus] = None
    card_expires_at: Optional[datetime] = None


class PatronListResponse(BaseModel):
    patrons: list[UserResponse]
    total_count: int


class PatronSortField(StrEnum):
    name = "name"
    member_date = "member_date"
    fines_balance = "fines_balance"
    checkout_count = "checkout_count"


class SortDirection(StrEnum):
    asc = "asc"
    desc = "desc"


class OverdueFilter(StrEnum):
    all = "all"
    has_overdue = "has_overdue"
    no_overdue = "no_overdue"


class AtRiskCounts(BaseModel):
    patrons_with_many_overdue: int = 0  # 3+ overdue items
    patrons_with_high_fines: int = 0  # Fines over $25
    inactive_patrons: int = 0  # No activity in 90+ days


class AtRiskPatron(BaseModel):
    id: int
    first_name: str
    last_name: str
    email: str
    library_card: str | None = None
    overdue_count: int = 0
    fines_balance: Decimal = Decimal("0.00")
    last_activity_date: datetime | None = None


class PatronStatisticsResponse(BaseModel):
    total_patrons: int
    active_patrons: int
    blocked_patrons: int
    new_this_week: int
    new_this_month: int
    total_fines_outstanding: Decimal
    total_overdue_items: int
    at_risk_counts: AtRiskCounts
    expiring_cards_counts: ExpiringCardsCounts = ExpiringCardsCounts()
    # Lists of at-risk patrons (limited to top 10 each)
    patrons_with_many_overdue: list[AtRiskPatron] = []
    patrons_with_high_fines: list[AtRiskPatron] = []
    inactive_patrons: list[AtRiskPatron] = []


# =============================================================================
# Patron Management Endpoints
# =============================================================================


@router.get("", response_model=PatronListResponse)
@pii_filtered
async def list_patrons(
    search: Optional[str] = Query(None, description="Search by name, email, or card number"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    # Advanced filters
    member_since_from: Optional[date] = Query(
        None, description="Filter patrons who joined on or after this date"
    ),
    member_since_to: Optional[date] = Query(
        None, description="Filter patrons who joined on or before this date"
    ),
    fines_min: Optional[float] = Query(None, ge=0, description="Minimum fines balance"),
    fines_max: Optional[float] = Query(None, ge=0, description="Maximum fines balance"),
    checkout_count_min: Optional[int] = Query(
        None, ge=0, description="Minimum total checkout count"
    ),
    has_overdue: Optional[OverdueFilter] = Query(
        None, description="Filter by overdue items status"
    ),
    card_status: CardStatusFilter = Query(
        CardStatusFilter.any,
        alias="cardStatus",
        description=(
            "Filter by library-card expiration status. "
            "Bands are nested: expiring_90d includes the expiring_30d window. "
            "`active` includes patrons with no expiry set (NULL). "
            "All comparisons in UTC."
        ),
    ),
    # Sorting
    sort_by: PatronSortField = Query(PatronSortField.name, description="Field to sort by"),
    sort_direction: SortDirection = Query(SortDirection.asc, description="Sort direction"),
    # Pagination
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """
    Search and list all patrons with advanced filtering and sorting.

    Supports:
    - Text search by name, email, or library card
    - Date range filter for membership date
    - Fines balance range filter
    - Minimum checkout count filter
    - Overdue items filter
    - Multiple sort options with direction control
    """
    # Base query for patrons
    query = select(User).where(_cardholder_filter())
    count_query = select(func.count(User.id)).where(_cardholder_filter())

    # Text search filter
    normalized_search = search.strip() if search else None

    if normalized_search:
        search_filter = _build_patron_search_filter(normalized_search)
        query = query.where(search_filter)
        count_query = count_query.where(search_filter)

    # Active status filter
    if is_active is not None:
        query = query.where(User.is_active == is_active)
        count_query = count_query.where(User.is_active == is_active)

    # Card-status (expiration band) filter
    card_status_clause = _card_status_clause(card_status)
    if card_status_clause is not None:
        query = query.where(card_status_clause)
        count_query = count_query.where(card_status_clause)

    # Member since date range filter
    if member_since_from:
        query = query.where(
            User.created_at >= datetime.combine(member_since_from, datetime.min.time())
        )
        count_query = count_query.where(
            User.created_at >= datetime.combine(member_since_from, datetime.min.time())
        )

    if member_since_to:
        query = query.where(
            User.created_at <= datetime.combine(member_since_to, datetime.max.time())
        )
        count_query = count_query.where(
            User.created_at <= datetime.combine(member_since_to, datetime.max.time())
        )

    # Fines balance range filter - requires subquery for computed field
    if fines_min is not None or fines_max is not None:
        # Subquery to calculate fines balance
        fines_subquery = (
            select(
                Fine.user_id,
                func.coalesce(func.sum(Fine.amount - Fine.amount_paid), Decimal("0.00")).label(
                    "fines_balance"
                ),
            )
            .where(Fine.status.in_([FineStatus.unpaid, FineStatus.partial]))
            .group_by(Fine.user_id)
            .subquery()
        )

        query = query.outerjoin(fines_subquery, User.id == fines_subquery.c.user_id)
        count_query_base = (
            select(func.count(User.id))
            .where(_cardholder_filter())
            .outerjoin(fines_subquery, User.id == fines_subquery.c.user_id)
        )

        if fines_min is not None:
            fines_min_decimal = Decimal(str(fines_min))
            query = query.where(
                func.coalesce(fines_subquery.c.fines_balance, Decimal("0.00")) >= fines_min_decimal
            )
            count_query = count_query_base.where(
                func.coalesce(fines_subquery.c.fines_balance, Decimal("0.00")) >= fines_min_decimal
            )

        if fines_max is not None:
            fines_max_decimal = Decimal(str(fines_max))
            query = query.where(
                func.coalesce(fines_subquery.c.fines_balance, Decimal("0.00")) <= fines_max_decimal
            )
            if fines_min is not None:
                count_query = count_query.where(
                    func.coalesce(fines_subquery.c.fines_balance, Decimal("0.00"))
                    <= fines_max_decimal
                )
            else:
                count_query = count_query_base.where(
                    func.coalesce(fines_subquery.c.fines_balance, Decimal("0.00"))
                    <= fines_max_decimal
                )

    # Checkout count threshold filter - requires subquery
    if checkout_count_min is not None:
        checkout_subquery = (
            select(Checkout.user_id, func.count(Checkout.id).label("total_checkouts"))
            .group_by(Checkout.user_id)
            .subquery()
        )

        query = query.outerjoin(checkout_subquery, User.id == checkout_subquery.c.user_id)
        query = query.where(
            func.coalesce(checkout_subquery.c.total_checkouts, 0) >= checkout_count_min
        )

        count_query = (
            select(func.count(User.id))
            .where(_cardholder_filter())
            .outerjoin(checkout_subquery, User.id == checkout_subquery.c.user_id)
            .where(func.coalesce(checkout_subquery.c.total_checkouts, 0) >= checkout_count_min)
        )

    # Overdue items filter
    if has_overdue and has_overdue != OverdueFilter.all:
        overdue_subquery = (
            select(Checkout.user_id)
            .where(and_(Checkout.status == CheckoutStatus.overdue, Checkout.returned_at.is_(None)))
            .distinct()
            .subquery()
        )

        if has_overdue == OverdueFilter.has_overdue:
            query = query.where(User.id.in_(select(overdue_subquery.c.user_id)))
            count_query = (
                select(func.count(User.id))
                .where(_cardholder_filter())
                .where(User.id.in_(select(overdue_subquery.c.user_id)))
            )
        elif has_overdue == OverdueFilter.no_overdue:
            query = query.where(User.id.notin_(select(overdue_subquery.c.user_id)))
            count_query = (
                select(func.count(User.id))
                .where(_cardholder_filter())
                .where(User.id.notin_(select(overdue_subquery.c.user_id)))
            )

    # Apply sorting
    sort_name_app_side = False
    if sort_by == PatronSortField.name:
        # Names are encrypted: DB order_by would sort ciphertext. Paginate on a
        # stable id order and sort the returned PAGE app-side by decrypted name.
        # This means name-sort is per-page (global cross-page order shifts).
        sort_name_app_side = True
        query = query.order_by(User.id.asc())
    elif sort_by == PatronSortField.member_date:
        if sort_direction == SortDirection.asc:
            query = query.order_by(User.created_at.asc())
        else:
            query = query.order_by(User.created_at.desc())
    elif sort_by == PatronSortField.fines_balance:
        # For fines sorting, we need the fines subquery if not already joined
        if fines_min is None and fines_max is None:
            fines_sort_subquery = (
                select(
                    Fine.user_id,
                    func.coalesce(func.sum(Fine.amount - Fine.amount_paid), Decimal("0.00")).label(
                        "fines_balance"
                    ),
                )
                .where(Fine.status.in_([FineStatus.unpaid, FineStatus.partial]))
                .group_by(Fine.user_id)
                .subquery()
            )
            query = query.outerjoin(fines_sort_subquery, User.id == fines_sort_subquery.c.user_id)
            fines_col = func.coalesce(fines_sort_subquery.c.fines_balance, Decimal("0.00"))
        else:
            fines_col = func.coalesce(fines_subquery.c.fines_balance, Decimal("0.00"))

        if sort_direction == SortDirection.asc:
            query = query.order_by(fines_col.asc())
        else:
            query = query.order_by(fines_col.desc())
    elif sort_by == PatronSortField.checkout_count:
        # For checkout count sorting, we need the checkout subquery if not already joined
        if checkout_count_min is None:
            checkout_sort_subquery = (
                select(Checkout.user_id, func.count(Checkout.id).label("total_checkouts"))
                .group_by(Checkout.user_id)
                .subquery()
            )
            query = query.outerjoin(
                checkout_sort_subquery, User.id == checkout_sort_subquery.c.user_id
            )
            checkout_col = func.coalesce(checkout_sort_subquery.c.total_checkouts, 0)
        else:
            checkout_col = func.coalesce(checkout_subquery.c.total_checkouts, 0)

        if sort_direction == SortDirection.asc:
            query = query.order_by(checkout_col.asc())
        else:
            query = query.order_by(checkout_col.desc())

    # Execute count query
    total_result = await db.execute(count_query)
    total_count = total_result.scalar() or 0

    # Execute main query with pagination
    result = await db.execute(query.offset(offset).limit(limit))
    patrons = list(result.scalars().all())

    if sort_name_app_side:
        patrons.sort(
            key=lambda p: ((p.last_name or "").lower(), (p.first_name or "").lower()),
            reverse=(sort_direction == SortDirection.desc),
        )

    # Fuzzy fallback for minor misspellings in names when normal search has no results.
    if not patrons and normalized_search and len(normalized_search) >= 3:
        fuzzy_base_query = select(User).where(_cardholder_filter())
        if is_active is not None:
            fuzzy_base_query = fuzzy_base_query.where(User.is_active == is_active)
        if card_status_clause is not None:
            fuzzy_base_query = fuzzy_base_query.where(card_status_clause)

        # Names are encrypted: prefilter fuzzy candidates by last-name first-char
        # via the prefix blind index (first_name has no prefix index, so
        # first-name-only misspellings narrow slightly — acceptable for a
        # best-effort fuzzy fallback).
        first_char_hash = name_blind_hash(normalized_search[0].lower())
        candidate_query = fuzzy_base_query.where(
            User.last_name_prefix_hash.op("?")(first_char_hash)
        ).limit(50)

        candidate_result = await db.execute(candidate_query)
        candidates = candidate_result.scalars().all()

        fuzzy_matches = []
        for candidate in candidates:
            full_name = f"{candidate.first_name} {candidate.last_name}".lower()
            first_ratio = SequenceMatcher(
                None, normalized_search.lower(), candidate.first_name.lower()
            ).ratio()
            last_ratio = SequenceMatcher(
                None, normalized_search.lower(), candidate.last_name.lower()
            ).ratio()
            full_ratio = SequenceMatcher(None, normalized_search.lower(), full_name).ratio()
            score = max(first_ratio, last_ratio, full_ratio)
            if score >= 0.72:
                fuzzy_matches.append((score, candidate))

        fuzzy_matches.sort(key=lambda item: item[0], reverse=True)
        fuzzy_patrons = [candidate for _, candidate in fuzzy_matches]
        total_count = len(fuzzy_patrons)
        patrons = fuzzy_patrons[offset : offset + limit]

    # Fetch aggregated counts for the current page in three constant queries
    # (one each for checkouts, holds, fines) keyed on the page patron ids.
    # Mirrors the filter conditions in patron_context_service so list numbers
    # agree with the detail page.
    page_ids = [p.id for p in patrons]
    checkout_counts: dict[int, int] = {}
    hold_counts: dict[int, int] = {}
    fines_balances: dict[int, Decimal] = {}

    if page_ids:
        co_rows = await db.execute(
            select(Checkout.user_id, func.count(Checkout.id).label("n"))
            .where(
                Checkout.user_id.in_(page_ids),
                Checkout.status.in_([CheckoutStatus.active, CheckoutStatus.overdue]),
            )
            .group_by(Checkout.user_id)
        )
        checkout_counts = {uid: n for uid, n in co_rows.all()}

        hold_rows = await db.execute(
            select(Hold.user_id, func.count(Hold.id).label("n"))
            .where(
                Hold.user_id.in_(page_ids),
                Hold.status.in_([HoldStatus.pending, HoldStatus.ready]),
            )
            .group_by(Hold.user_id)
        )
        hold_counts = {uid: n for uid, n in hold_rows.all()}

        fine_rows = await db.execute(
            select(
                Fine.user_id,
                func.coalesce(func.sum(Fine.amount - Fine.amount_paid), Decimal("0.00")).label(
                    "balance"
                ),
            )
            .where(
                Fine.user_id.in_(page_ids),
                Fine.status.in_([FineStatus.unpaid, FineStatus.partial]),
            )
            .group_by(Fine.user_id)
        )
        fines_balances = {uid: bal for uid, bal in fine_rows.all()}

    # Apply PII masking based on requesting user's role
    filtered_patrons = []
    for p in patrons:
        patron_dict = UserResponse.model_validate(p).model_dump(mode="json")
        patron_dict["current_checkouts"] = checkout_counts.get(p.id, 0)
        patron_dict["current_holds"] = hold_counts.get(p.id, 0)
        patron_dict["fines_balance"] = float(fines_balances.get(p.id, Decimal("0.00")))
        filtered_patrons.append(filter_patron_data(patron_dict, current_user.role))

    return {"patrons": filtered_patrons, "total_count": total_count}


# =============================================================================
# Literal-prefix routes (declared before /{patron_id} so FastAPI matches them
# verbatim instead of trying to parse the literal segment as an int patron_id)
# =============================================================================


@router.get("/statistics", response_model=PatronStatisticsResponse)
async def get_patron_statistics(
    range_start: Optional[date] = Query(
        None,
        description="Anchor date for new_this_week/new_this_month counts. "
        "Both range_start and range_end must be provided together. "
        "When omitted, behavior is relative to now (this week / this month).",
    ),
    range_end: Optional[date] = Query(
        None,
        description="End-of-range anchor (inclusive). See range_start.",
    ),
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Get aggregated patron statistics for the dashboard."""
    if (range_start is None) != (range_end is None):
        raise HTTPException(
            status_code=400,
            detail="range_start and range_end must be provided together",
        )
    if range_start is not None and range_end is not None and range_start > range_end:
        raise HTTPException(
            status_code=400,
            detail="range_start must be on or before range_end",
        )

    now = datetime.now(timezone.utc)
    if range_end is not None:
        anchor = datetime.combine(range_end, datetime.max.time(), tzinfo=timezone.utc)
    else:
        anchor = now
    week_ago = anchor - timedelta(days=7)
    month_ago = anchor - timedelta(days=30)
    ninety_days_ago = now - timedelta(days=90)

    if range_start is not None:
        range_floor = datetime.combine(range_start, datetime.min.time(), tzinfo=timezone.utc)
        if week_ago < range_floor:
            week_ago = range_floor
        if month_ago < range_floor:
            month_ago = range_floor

    total_result = await db.execute(select(func.count(User.id)).where(User.role == UserRole.PATRON))
    total_patrons = total_result.scalar() or 0

    active_result = await db.execute(
        select(func.count(User.id)).where(User.role == UserRole.PATRON, User.is_active == True)
    )
    active_patrons = active_result.scalar() or 0
    blocked_patrons = total_patrons - active_patrons

    new_week_result = await db.execute(
        select(func.count(User.id)).where(
            User.role == UserRole.PATRON,
            User.created_at >= week_ago,
            User.created_at <= anchor,
        )
    )
    new_this_week = new_week_result.scalar() or 0

    new_month_result = await db.execute(
        select(func.count(User.id)).where(
            User.role == UserRole.PATRON,
            User.created_at >= month_ago,
            User.created_at <= anchor,
        )
    )
    new_this_month = new_month_result.scalar() or 0

    fines_result = await db.execute(
        select(func.coalesce(func.sum(Fine.amount - Fine.amount_paid), Decimal("0.00"))).where(
            Fine.status.in_([FineStatus.unpaid, FineStatus.partial])
        )
    )
    total_fines_outstanding = fines_result.scalar() or Decimal("0.00")

    overdue_result = await db.execute(
        select(func.count(Checkout.id)).where(
            Checkout.status == CheckoutStatus.overdue, Checkout.returned_at.is_(None)
        )
    )
    total_overdue_items = overdue_result.scalar() or 0

    overdue_subquery = (
        select(Checkout.user_id, func.count(Checkout.id).label("overdue_count"))
        .where(Checkout.status == CheckoutStatus.overdue, Checkout.returned_at.is_(None))
        .group_by(Checkout.user_id)
        .having(func.count(Checkout.id) >= 3)
        .subquery()
    )

    many_overdue_result = await db.execute(
        select(User, overdue_subquery.c.overdue_count)
        .join(overdue_subquery, User.id == overdue_subquery.c.user_id)
        .where(User.role == UserRole.PATRON)
        .order_by(overdue_subquery.c.overdue_count.desc())
        .limit(10)
    )
    patrons_with_many_overdue_rows = many_overdue_result.all()

    many_overdue_count_result = await db.execute(select(func.count()).select_from(overdue_subquery))
    patrons_with_many_overdue_count = many_overdue_count_result.scalar() or 0

    high_fines_subquery = (
        select(Fine.user_id, func.sum(Fine.amount - Fine.amount_paid).label("fines_balance"))
        .where(Fine.status.in_([FineStatus.unpaid, FineStatus.partial]))
        .group_by(Fine.user_id)
        .having(func.sum(Fine.amount - Fine.amount_paid) > Decimal("25.00"))
        .subquery()
    )

    high_fines_result = await db.execute(
        select(User, high_fines_subquery.c.fines_balance)
        .join(high_fines_subquery, User.id == high_fines_subquery.c.user_id)
        .where(User.role == UserRole.PATRON)
        .order_by(high_fines_subquery.c.fines_balance.desc())
        .limit(10)
    )
    patrons_with_high_fines_rows = high_fines_result.all()

    high_fines_count_result = await db.execute(
        select(func.count()).select_from(high_fines_subquery)
    )
    patrons_with_high_fines_count = high_fines_count_result.scalar() or 0

    last_activity_expr = func.coalesce(User.last_activity_at, User.created_at)

    inactive_result = await db.execute(
        select(User, last_activity_expr.label("last_activity"))
        .where(
            User.role == UserRole.PATRON,
            User.is_active == True,
            last_activity_expr < ninety_days_ago,
        )
        .order_by(last_activity_expr.asc())
        .limit(10)
    )
    inactive_patrons_rows = inactive_result.all()

    inactive_count_result = await db.execute(
        select(func.count(User.id)).where(
            User.role == UserRole.PATRON,
            User.is_active == True,
            last_activity_expr < ninety_days_ago,
        )
    )
    inactive_patrons_count = inactive_count_result.scalar() or 0

    # Card-expiration band counts for the dashboard tile. Bands are nested:
    # a card expiring in 15d is in both expiring_within_30d and expiring_within_90d.
    today_start, plus_30d_end, plus_90d_end = _card_status_today_bounds(now)
    cardholder_filter = _cardholder_filter()

    expiring_30d_count_result = await db.execute(
        select(func.count(User.id)).where(
            cardholder_filter,
            User.card_expires_at.isnot(None),
            User.card_expires_at >= today_start,
            User.card_expires_at <= plus_30d_end,
        )
    )
    expiring_within_30d = expiring_30d_count_result.scalar() or 0

    expiring_90d_count_result = await db.execute(
        select(func.count(User.id)).where(
            cardholder_filter,
            User.card_expires_at.isnot(None),
            User.card_expires_at >= today_start,
            User.card_expires_at <= plus_90d_end,
        )
    )
    expiring_within_90d = expiring_90d_count_result.scalar() or 0

    expired_count_result = await db.execute(
        select(func.count(User.id)).where(
            cardholder_filter,
            User.card_expires_at.isnot(None),
            User.card_expires_at < today_start,
        )
    )
    expired_count = expired_count_result.scalar() or 0

    return PatronStatisticsResponse(
        total_patrons=total_patrons,
        active_patrons=active_patrons,
        blocked_patrons=blocked_patrons,
        new_this_week=new_this_week,
        new_this_month=new_this_month,
        total_fines_outstanding=total_fines_outstanding,
        total_overdue_items=total_overdue_items,
        at_risk_counts=AtRiskCounts(
            patrons_with_many_overdue=patrons_with_many_overdue_count,
            patrons_with_high_fines=patrons_with_high_fines_count,
            inactive_patrons=inactive_patrons_count,
        ),
        expiring_cards_counts=ExpiringCardsCounts(
            expiring_within_30d=expiring_within_30d,
            expiring_within_90d=expiring_within_90d,
            expired=expired_count,
        ),
        patrons_with_many_overdue=[
            AtRiskPatron(
                id=patron.id,
                first_name=patron.first_name,
                last_name=patron.last_name,
                email=patron.email,
                library_card=patron.library_card,
                overdue_count=overdue_count,
            )
            for patron, overdue_count in patrons_with_many_overdue_rows
        ],
        patrons_with_high_fines=[
            AtRiskPatron(
                id=patron.id,
                first_name=patron.first_name,
                last_name=patron.last_name,
                email=patron.email,
                library_card=patron.library_card,
                fines_balance=fines_balance or Decimal("0.00"),
            )
            for patron, fines_balance in patrons_with_high_fines_rows
        ],
        inactive_patrons=[
            AtRiskPatron(
                id=patron.id,
                first_name=patron.first_name,
                last_name=patron.last_name,
                email=patron.email,
                library_card=patron.library_card,
                last_activity_date=last_activity,
            )
            for patron, last_activity in inactive_patrons_rows
        ],
    )


router.include_router(patron_bulk_router)

@router.get("/export", response_model=PatronExportResponse)
async def export_patrons(
    patron_ids: Optional[str] = Query(
        None, description="Comma-separated patron IDs to export (exports all if not provided)"
    ),
    status_filter: Optional[str] = Query(
        None, description="Filter by status: active, blocked, or all"
    ),
    format: str = Query("json", description="Export format: json, csv"),
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Export patron data for reporting purposes."""
    from fastapi.responses import Response
    import csv
    import io

    query = select(User).where(User.role == UserRole.PATRON)

    if patron_ids:
        try:
            ids = [int(i.strip()) for i in patron_ids.split(",") if i.strip()]
            if ids:
                query = query.where(User.id.in_(ids))
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid patron IDs format"
            ) from None

    if status_filter == "active":
        query = query.where(User.is_active == True)
    elif status_filter == "blocked":
        query = query.where(User.is_active == False)

    current_checkouts_sq = (
        select(Checkout.user_id, func.count(Checkout.id).label("cnt"))
        .where(Checkout.status.in_([CheckoutStatus.active, CheckoutStatus.overdue]))
        .group_by(Checkout.user_id)
    ).subquery()

    total_checkouts_sq = (
        select(Checkout.user_id, func.count(Checkout.id).label("cnt")).group_by(Checkout.user_id)
    ).subquery()

    current_holds_sq = (
        select(Hold.user_id, func.count(Hold.id).label("cnt"))
        .where(Hold.status.in_([HoldStatus.pending, HoldStatus.ready]))
        .group_by(Hold.user_id)
    ).subquery()

    fines_balance_sq = (
        select(Fine.user_id, func.sum(Fine.amount - Fine.amount_paid).label("balance"))
        .where(Fine.status.in_([FineStatus.unpaid, FineStatus.partial]))
        .group_by(Fine.user_id)
    ).subquery()

    export_query = (
        query.outerjoin(current_checkouts_sq, User.id == current_checkouts_sq.c.user_id)
        .outerjoin(total_checkouts_sq, User.id == total_checkouts_sq.c.user_id)
        .outerjoin(current_holds_sq, User.id == current_holds_sq.c.user_id)
        .outerjoin(fines_balance_sq, User.id == fines_balance_sq.c.user_id)
        .add_columns(
            func.coalesce(current_checkouts_sq.c.cnt, 0).label("current_checkouts"),
            func.coalesce(total_checkouts_sq.c.cnt, 0).label("total_checkouts"),
            func.coalesce(current_holds_sq.c.cnt, 0).label("current_holds"),
            func.coalesce(fines_balance_sq.c.balance, Decimal("0.00")).label("fines_balance"),
        )
        .order_by(User.last_name, User.first_name)
    )

    result = await db.execute(export_query)
    rows = result.all()

    patron_data = []
    for row in rows:
        patron = row[0]
        patron_data.append(
            PatronExportData(
                id=patron.id,
                first_name=patron.first_name,
                last_name=patron.last_name,
                email=patron.email,
                library_card=patron.library_card,
                phone=patron.phone,
                address=patron.address,
                is_active=patron.is_active,
                created_at=patron.created_at.isoformat(),
                fines_balance=row.fines_balance,
                current_checkouts=row.current_checkouts,
                current_holds=row.current_holds,
                total_checkouts=row.total_checkouts,
            )
        )

    if format == "csv":
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(
            [
                "ID",
                "First Name",
                "Last Name",
                "Email",
                "Library Card",
                "Phone",
                "Address",
                "Status",
                "Member Since",
                "Fines Balance",
                "Current Checkouts",
                "Current Holds",
                "Total Checkouts",
            ]
        )
        for p in patron_data:
            writer.writerow(
                [
                    p.id,
                    p.first_name,
                    p.last_name,
                    p.email,
                    p.library_card or "",
                    p.phone or "",
                    p.address or "",
                    "Active" if p.is_active else "Blocked",
                    p.created_at,
                    f"${p.fines_balance:.2f}",
                    p.current_checkouts,
                    p.current_holds,
                    p.total_checkouts,
                ]
            )
        csv_content = output.getvalue()
        return Response(
            content=csv_content,
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=patrons_export.csv"},
        )

    return PatronExportResponse(
        patrons=patron_data,
        total_count=len(patron_data),
        exported_at=datetime.now(timezone.utc).isoformat(),
    )


@router.get("/{patron_id}", response_model=PatronDetailResponse)
@pii_filtered
async def get_patron_detail(
    patron_id: int,
    request: Request,
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Get detailed patron info including checkouts, holds, and fines."""
    patron = await get_or_404(db, User, patron_id, "Patron not found")

    # Audit log: staff viewed patron record
    from ....models.audit_log import AuditAction, AuditLog

    db.add(
        AuditLog(
            admin_id=current_user.id,
            target_user_id=patron.id,
            action=AuditAction.VIEWED,
            details={"resource_type": "patron_record", "endpoint": "get_patron_detail"},
            ip_address=request.client.host if request.client else None,
        )
    )
    await db.flush()

    checkouts, holds, fines, total_owed = await assemble_patron_detail_fields(patron_id, db)

    # Build from the ORM object rather than hand-listing kwargs. The old explicit
    # list passed 15 of UserResponse's ~30 fields, and pydantic silently defaulted
    # the rest -- so patron_type, language_preference and parental_consent_given
    # (COPPA consent) always read back as None/False to staff regardless of what
    # was actually on the record, and the detail view showed LESS than the list
    # view, which already does exactly this (see get_patrons above).
    return PatronDetailResponse(
        **UserResponse.model_validate(patron).model_dump(),
        checkouts=checkouts,
        holds=holds,
        fines=fines,
        total_fines_owed=total_owed,
    )


@router.get("/{patron_id}/context-card", response_model=PatronContextCardResponse)
@pii_filtered
async def get_patron_context_card(
    patron_id: int,
    request: Request,
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """
    Get patron context card data for instant display when card is scanned.

    Provides comprehensive patron information for staff to deliver personalized service:
    - Photo for verification
    - Preferred name and pronouns
    - Account alerts (fines, blocks, notes)
    - Last visit and checkout frequency
    - Current checkouts and holds
    - Reading preferences and recent genres
    - Staff notes
    - Loyalty program status
    """
    patron = await get_or_404(db, User, patron_id, "Patron not found")

    # Audit log: staff viewed patron context card
    from ....models.audit_log import AuditAction, AuditLog

    db.add(
        AuditLog(
            admin_id=current_user.id,
            target_user_id=patron.id,
            action=AuditAction.VIEWED,
            details={"resource_type": "patron_record", "endpoint": "get_patron_context_card"},
            ip_address=request.client.host if request.client else None,
        )
    )
    await db.flush()

    return await assemble_patron_context_card(patron_id, patron, db)


class PatronStatusFilterOption(BaseModel):
    key: str
    label: str
    filter_type: str


@router.get("/status-filters", response_model=list[PatronStatusFilterOption])
@limiter.limit("60/minute")
async def get_patron_status_filters(
    request: Request,
    staff_user: User = Depends(require_staff),
):
    """Get all available patron status filter options for search forms.

    Returns the standard patron status filters used in patron search and management interfaces.
    These filters determine which patron records are displayed based on their account status.

    Filter Types:
    - none: Shows all patrons regardless of status
    - exclude_blocked: Shows only patrons who are not blocked
    - only_blocked: Shows only patrons who are blocked
    """
    filters = [
        PatronStatusFilterOption(key="all", label="All Patrons", filter_type="none"),
        PatronStatusFilterOption(key="active", label="Active Only", filter_type="exclude_blocked"),
        PatronStatusFilterOption(key="blocked", label="Blocked Only", filter_type="only_blocked"),
    ]
    return filters


class ApprovalStatusOption(BaseModel):
    key: str
    label: str
    description: str | None = None


@router.get("/config/approval-statuses", response_model=list[ApprovalStatusOption])
@limiter.limit("60/minute")
async def get_approval_statuses(
    request: Request,
    current_user: User = Depends(require_staff),
):
    """Get available approval status options for patron requests.

    Returns the standard approval statuses used for patron-related decisions
    and requests (e.g., card applications, policy exceptions).
    """
    return [
        ApprovalStatusOption(
            key="pending",
            label="Pending",
            description="Awaiting review and decision",
        ),
        ApprovalStatusOption(
            key="approved",
            label="Approved",
            description="Request has been approved",
        ),
        ApprovalStatusOption(
            key="rejected",
            label="Rejected",
            description="Request has been rejected",
        ),
    ]


@router.put("/{patron_id}", response_model=UserResponse)
@limiter.limit("30/minute")
@pii_filtered
async def update_patron(
    request: Request,
    patron_id: int,
    patron_update: UserUpdate,
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Update patron information."""
    from datetime import datetime, timezone
    from ....models.audit_log import AuditAction, AuditLog

    if patron_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot edit your own patron record through staff tools",
        )

    patron = await get_or_404(db, User, patron_id, "Patron not found")

    update_data = patron_update.model_dump(exclude_unset=True)

    # Capture before state for audit trail
    changes = {}
    for field, new_value in update_data.items():
        old_value = getattr(patron, field, None)
        old_str = str(old_value) if old_value is not None else None
        new_str = str(new_value) if new_value is not None else None
        if old_str != new_str:
            changes[field] = {"old": old_str, "new": new_str}

    # Apply updates
    for field, value in update_data.items():
        setattr(patron, field, value)

    # Audit log if any changes detected
    if changes:
        audit_log = AuditLog(
            admin_id=current_user.id,
            target_user_id=patron.id,
            action=AuditAction.UPDATE_USER,
            details={"changes": changes, "edited_by": current_user.email},
        )
        db.add(audit_log)

    await db.commit()

    # Re-fetch to avoid MissingGreenlet
    # error during UserResponse serialization
    from sqlalchemy import select as sa_select

    result = await db.execute(sa_select(User).where(User.id == patron_id))
    patron = result.scalar_one()

    # Invalidate patron report cache after profile update
    await invalidate_patron_reports()

    return patron


# =============================================================================
# STOLEN CARD WORKFLOW (Exploit #2 countermeasure)
# =============================================================================


class StolenCardReport(BaseModel):
    notes: str = ""
    issue_replacement: bool = True


@router.post("/{patron_id}/report-stolen-card", status_code=status.HTTP_200_OK)
@limiter.limit("10/minute")
async def report_stolen_card(
    request: Request,
    patron_id: int,
    report: StolenCardReport,
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Report a patron's library card as stolen.

    Deactivates the current card, issues a replacement, and flags recent
    charges for staff review. Creates a full audit trail with timestamps
    so charges can be categorized as pre/post the stolen card report.
    """
    from ....services.fraud_detection_service import report_card_stolen

    result = await report_card_stolen(
        patron_id=patron_id,
        db=db,
        staff_id=staff_user.id,
        notes=report.notes,
        issue_replacement=report.issue_replacement,
    )
    await db.commit()

    return {
        "message": "Card reported stolen. Review flagged charges below.",
        "patron_id": result["patron_id"],
        "old_card": result["old_card"],
        "new_card": result["new_card"],
        "report_timestamp": result["report_timestamp"].isoformat(),
        "flagged_checkouts": result["flagged_checkouts"],
        "flagged_fines": result["flagged_fines"],
    }


# =============================================================================
# FRAUD DETECTION ALERTS (Exploits #6, #1 countermeasures)
# =============================================================================


@router.get("/{patron_id}/fraud-alerts", status_code=status.HTTP_200_OK)
async def get_patron_fraud_alerts(
    patron_id: int,
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Get all fraud detection alerts for a patron.

    Returns waiver-frequency alerts, claims-returned escalations,
    stolen card reports, and bounced check records.
    """
    from ....models.audit_log import AuditAction, AuditLog

    result = await db.execute(
        select(AuditLog)
        .where(
            AuditLog.target_user_id == patron_id,
            AuditLog.action.in_(
                [
                    AuditAction.WAIVER_FREQUENCY_ALERT,
                    AuditAction.CLAIMS_RETURNED_ESCALATION,
                    AuditAction.CARD_REPORTED_STOLEN,
                    AuditAction.CHECK_BOUNCED,
                ]
            ),
        )
        .order_by(AuditLog.created_at.desc())
    )
    alerts = result.scalars().all()

    return {
        "patron_id": patron_id,
        "alerts": [
            {
                "id": alert.id,
                "type": str(alert.action),
                "details": alert.details,
                "created_at": alert.created_at.isoformat() if alert.created_at else None,
                "staff_id": alert.admin_id,
            }
            for alert in alerts
        ],
        "total": len(alerts),
    }


# =============================================================================
# PATRON ONBOARDING STATUS (Staff view)
# =============================================================================


@router.get("/{patron_id}/onboarding-status", status_code=status.HTTP_200_OK)
async def get_patron_onboarding_status(
    patron_id: int,
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Get onboarding status for a patron (staff only)."""
    from ....models.patron_onboarding import PatronOnboardingProgress

    patron = await get_or_404(db, User, patron_id, "Patron not found")

    result = await db.execute(
        select(PatronOnboardingProgress).where(PatronOnboardingProgress.patron_id == patron_id)
    )
    progress = result.scalar_one_or_none()

    if not progress:
        return {
            "patron_id": patron_id,
            "status": "not_started",
            "current_step": 0,
            "total_steps": 5,
            "steps": {},
            "skipped": False,
            "completed_at": None,
            "started_at": None,
            "onboarding_completed_at": patron.onboarding_completed_at.isoformat()
            if patron.onboarding_completed_at
            else None,
            "onboarding_skipped": patron.onboarding_skipped,
        }

    steps = {
        "welcome": progress.step_welcome_completed,
        "preferences": progress.step_preferences_completed,
        "branch": progress.step_branch_completed,
        "tour": progress.step_tour_completed,
        "complete": progress.step_complete_completed,
    }

    if progress.completed_at:
        status_label = "completed"
    elif progress.skipped:
        status_label = "skipped"
    else:
        status_label = "in_progress"

    return {
        "patron_id": patron_id,
        "status": status_label,
        "current_step": progress.current_step,
        "total_steps": 5,
        "steps": steps,
        "skipped": progress.skipped,
        "completed_at": progress.completed_at.isoformat() if progress.completed_at else None,
        "started_at": progress.started_at.isoformat() if progress.started_at else None,
        "onboarding_completed_at": patron.onboarding_completed_at.isoformat()
        if patron.onboarding_completed_at
        else None,
        "onboarding_skipped": patron.onboarding_skipped,
    }


@router.post("/{patron_id}/onboarding/reset", status_code=status.HTTP_200_OK)
async def reset_patron_onboarding(
    patron_id: int,
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Reset onboarding for a patron so they can redo the setup wizard (staff only)."""
    from ....models.patron_onboarding import PatronOnboardingProgress

    patron = await get_or_404(db, User, patron_id, "Patron not found")

    result = await db.execute(
        select(PatronOnboardingProgress).where(PatronOnboardingProgress.patron_id == patron_id)
    )
    progress = result.scalar_one_or_none()

    if progress:
        progress.step_welcome_completed = False
        progress.step_preferences_completed = False
        progress.step_branch_completed = False
        progress.step_tour_completed = False
        progress.step_complete_completed = False
        progress.current_step = 1
        progress.skipped = False
        progress.skipped_at = None
        progress.completed_at = None

    patron.onboarding_completed_at = None
    patron.onboarding_skipped = False

    await db.flush()
    return {"status": "ok", "message": "Onboarding reset for patron"}


# =============================================================================
# Staff: Register New Patron (in-person walk-in registration)
# =============================================================================


class StaffCreatePatronRequest(BaseModel):
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    email: Optional[str] = Field(None, max_length=255)
    phone: Optional[str] = Field(None, max_length=50)
    address: Optional[str] = Field(None, max_length=500)


class StaffCreatePatronResponse(BaseModel):
    id: int
    first_name: str
    last_name: str
    email: str
    library_card: str
    temporary_password: str


def _generate_temp_credential() -> str:
    import secrets

    words = (
        "Heron",
        "Maple",
        "River",
        "Cedar",
        "Willow",
        "Robin",
        "Sparrow",
        "Birch",
        "Otter",
        "Falcon",
        "Aspen",
        "Pine",
        "Lark",
        "Ember",
        "Hazel",
        "Quill",
        "Sage",
        "Coral",
        "Dune",
        "Fern",
    )
    w1 = secrets.choice(words)
    w2 = secrets.choice(words)
    digits = "".join(str(secrets.randbelow(10)) for _ in range(4))
    return f"{w1}-{digits}-{w2}"


async def _generate_unique_library_card(db: AsyncSession) -> str:
    from ....core.security import generate_library_card

    for _ in range(8):
        candidate = generate_library_card()
        existing = await db.execute(select(User.id).where(User.library_card == candidate))
        if existing.scalar_one_or_none() is None:
            return candidate
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Could not allocate a unique library card. Try again.",
    )


@router.post(
    "",
    response_model=StaffCreatePatronResponse,
    status_code=status.HTTP_201_CREATED,
)
async def staff_create_patron(
    payload: StaffCreatePatronRequest,
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Staff endpoint: register a new patron in person.

    Generates a library card and a one-time temporary credential that is
    returned in the response only (never stored in plaintext). Staff hand
    the credential to the patron physically. No email verification or
    welcome email is sent automatically.
    """
    from ....core.security import hash_password_async
    from ....models.audit_log import AuditAction, AuditLog

    submitted_email = payload.email.strip().lower() if payload.email else None
    if submitted_email == "":
        submitted_email = None

    if submitted_email:
        existing = await db.execute(
            select(User.id).where(User.email_hash == email_blind_hash(submitted_email))
        )
        if existing.scalar_one_or_none() is not None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A patron with that email already exists.",
            )
        email_for_record = submitted_email
        email_verified = False
    else:
        import secrets as _secrets

        email_for_record = f"walkin+{_secrets.token_hex(6)}@no-email.local"
        email_verified = False

    library_card = await _generate_unique_library_card(db)
    temp_credential = _generate_temp_credential()

    patron = User(
        email=email_for_record,
        password_hash=await hash_password_async(temp_credential),
        first_name=payload.first_name.strip(),
        last_name=payload.last_name.strip(),
        role=UserRole.PATRON,
        patron_status=PatronStatus.ACTIVE,
        is_active=True,
        library_card=library_card,
        card_type="full",
        email_verified=email_verified,
    )
    if payload.address and payload.address.strip():
        patron.address = payload.address.strip()
    if payload.phone and payload.phone.strip():
        patron.set_phone(payload.phone.strip())

    db.add(patron)
    await db.flush()

    db.add(
        AuditLog(
            admin_id=staff_user.id,
            target_user_id=patron.id,
            action=AuditAction.CREATE_USER,
            details={
                "method": "staff_walkin_registration",
                "library_card": library_card,
                "email_provided": submitted_email is not None,
                "created_by": staff_user.email,
            },
        )
    )

    await db.commit()
    await db.refresh(patron)

    with contextlib.suppress(Exception):  # noqa: BLE001 - best-effort cache invalidation
        await invalidate_patron_reports()

    return StaffCreatePatronResponse(
        id=patron.id,
        first_name=patron.first_name,
        last_name=patron.last_name,
        email=patron.email,
        library_card=library_card,
        temporary_password=temp_credential,
    )


# =============================================================================
# Patron lifecycle / circulation action routes (per-patron)
# Moved from staff/main.py during package-split refactor.
# =============================================================================


@router.post("/{patron_id}/block", response_model=UserResponse)
@limiter.limit("10/minute")
async def block_unblock_patron(
    request: Request,
    patron_id: int,
    block_data: PatronBlock,
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Block or unblock a patron account (legacy endpoint).

    For more granular control including suspension, use POST /patrons/{patron_id}/status instead.
    """
    from ....services.suspension_service import block_patron, unblock_patron

    patron = await get_or_404(db, User, patron_id, "Patron not found")

    try:
        if block_data.blocked:
            await block_patron(
                patron=patron,
                db=db,
                reason=block_data.reason or "Blocked by staff",
                blocked_by_id=staff_user.id,
            )
        else:
            await unblock_patron(
                patron=patron,
                db=db,
                unblocked_by_id=staff_user.id,
            )

        await db.commit()
        await db.refresh(patron)
        return patron
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@router.post("/{patron_id}/status", response_model=UserResponse)
@limiter.limit("10/minute")
async def update_patron_status(
    request: Request,
    patron_id: int,
    status_data: PatronStatusUpdate,
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Update patron account status (block/unblock/suspend/unsuspend).

    Note: Deceased patrons cannot be blocked, suspended, or have their status changed.
    """
    from ....services.suspension_service import (
        block_patron,
        unblock_patron,
        suspend_patron,
        lift_suspension,
    )

    patron = await get_or_404(db, User, patron_id, "Patron not found")

    try:
        if status_data.action == "block":
            if not status_data.reason:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Reason is required for blocking a patron",
                )
            await block_patron(
                patron=patron,
                db=db,
                reason=status_data.reason,
                blocked_by_id=staff_user.id,
            )

        elif status_data.action == "unblock":
            await unblock_patron(
                patron=patron,
                db=db,
                unblocked_by_id=staff_user.id,
            )

        elif status_data.action == "suspend":
            if not status_data.reason:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Reason is required for suspending a patron",
                )
            await suspend_patron(
                patron=patron,
                db=db,
                reason=status_data.reason,
                suspended_by_id=staff_user.id,
                suspended_until=status_data.suspended_until,
            )

        elif status_data.action == "unsuspend":
            await lift_suspension(
                patron=patron,
                db=db,
                lifted_by_id=staff_user.id,
            )

        await db.commit()
        await db.refresh(patron)
        return patron

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@router.get("/{patron_id}/activity", response_model=PatronActivityListResponse)
async def get_patron_activity(
    patron_id: int,
    activity_type: Optional[str] = Query(None, description="Filter by activity type"),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Get activity timeline for a patron."""
    patron = await get_or_404(db, User, patron_id, "Patron not found")

    activities: list[PatronActivityResponse] = []

    checkouts_result = await db.execute(
        select(Checkout, CatalogItem)
        .outerjoin(CatalogItem, Checkout.item_id == CatalogItem.id)
        .where(Checkout.user_id == patron_id)
        .order_by(Checkout.checked_out_at.desc())
    )
    for checkout, item in checkouts_result.all():
        title = item.title if item else "Unknown Item"
        author = item.author if item else None
        activities.append(
            PatronActivityResponse(
                id=checkout.id * 10000,
                patron_id=patron_id,
                activity_type="checkout",
                description=f"Checked out: {title}",
                item_id=checkout.item_id,
                item_title=item.title if item else None,
                item_author=author,
                checkout_id=checkout.id,
                created_at=checkout.checked_out_at,
            )
        )
        if checkout.returned_at:
            activities.append(
                PatronActivityResponse(
                    id=checkout.id * 10000 + 1,
                    patron_id=patron_id,
                    activity_type="return",
                    description=f"Returned: {title}",
                    item_id=checkout.item_id,
                    item_title=item.title if item else None,
                    item_author=author,
                    checkout_id=checkout.id,
                    created_at=checkout.returned_at,
                )
            )
        if checkout.renewal_count > 0:
            activities.append(
                PatronActivityResponse(
                    id=checkout.id * 10000 + 2,
                    patron_id=patron_id,
                    activity_type="renewal",
                    description=f"Renewed ({checkout.renewal_count}x): {title}",
                    item_id=checkout.item_id,
                    item_title=item.title if item else None,
                    item_author=author,
                    checkout_id=checkout.id,
                    created_at=checkout.due_date - timedelta(days=14 * checkout.renewal_count),
                )
            )

    holds_result = await db.execute(
        select(Hold, CatalogItem)
        .outerjoin(CatalogItem, Hold.item_id == CatalogItem.id)
        .where(Hold.user_id == patron_id)
        .order_by(Hold.created_at.desc())
    )
    for hold, item in holds_result.all():
        title = item.title if item else "Unknown Item"
        author = item.author if item else None
        activities.append(
            PatronActivityResponse(
                id=hold.id * 10000 + 5000,
                patron_id=patron_id,
                activity_type="hold_placed",
                description=f"Placed hold: {title}",
                item_id=hold.item_id,
                item_title=item.title if item else None,
                item_author=author,
                hold_id=hold.id,
                created_at=hold.created_at,
            )
        )
        _hold_status_map = {
            HoldStatus.fulfilled: ("hold_fulfilled", "Hold fulfilled", hold.notified_at),
            HoldStatus.cancelled: ("hold_cancelled", "Hold cancelled", hold.expires_at),
            HoldStatus.expired: ("hold_expired", "Hold expired", hold.expires_at),
        }
        if hold.status in _hold_status_map:
            act_type, act_desc, fallback_date = _hold_status_map[hold.status]
            activities.append(
                PatronActivityResponse(
                    id=hold.id * 10000 + 5001 + list(_hold_status_map.keys()).index(hold.status),
                    patron_id=patron_id,
                    activity_type=act_type,
                    description=f"{act_desc}: {title}",
                    item_id=hold.item_id,
                    item_title=item.title if item else None,
                    item_author=author,
                    hold_id=hold.id,
                    created_at=fallback_date or hold.created_at,
                )
            )

    fines_result = await db.execute(
        select(Fine).where(Fine.user_id == patron_id).order_by(Fine.created_at.desc())
    )
    for fine in fines_result.scalars().all():
        activities.append(
            PatronActivityResponse(
                id=fine.id * 10000 + 8000,
                patron_id=patron_id,
                activity_type="fine_created",
                description=f"Fine assessed: ${fine.amount:.2f} - {fine.description or fine.fine_type}",
                fine_id=fine.id,
                fine_amount=str(fine.amount),
                checkout_id=fine.checkout_id,
                created_at=fine.created_at,
            )
        )
        if fine.paid_at:
            activities.append(
                PatronActivityResponse(
                    id=fine.id * 10000 + 8001,
                    patron_id=patron_id,
                    activity_type="fine_paid",
                    description=f"Fine paid: ${fine.amount_paid:.2f}",
                    fine_id=fine.id,
                    fine_amount=str(fine.amount_paid),
                    created_at=fine.paid_at,
                )
            )
        if fine.waived_at:
            activities.append(
                PatronActivityResponse(
                    id=fine.id * 10000 + 8002,
                    patron_id=patron_id,
                    activity_type="fine_waived",
                    description=f"Fine waived: ${fine.amount - fine.amount_paid:.2f}",
                    fine_id=fine.id,
                    fine_amount=str(fine.amount - fine.amount_paid),
                    staff_id=fine.waived_by_id,
                    created_at=fine.waived_at,
                )
            )

    activities.append(
        PatronActivityResponse(
            id=patron_id * 10000 + 9000,
            patron_id=patron_id,
            activity_type="account_created",
            description="Account created",
            created_at=patron.created_at,
        )
    )

    if activity_type:
        activities = [a for a in activities if a.activity_type == activity_type]

    activities.sort(key=lambda x: x.created_at, reverse=True)
    total = len(activities)
    offset = (page - 1) * per_page
    paginated_activities = activities[offset : offset + per_page]
    has_more = offset + per_page < total

    return PatronActivityListResponse(
        activities=paginated_activities,
        total=total,
        page=page,
        per_page=per_page,
        has_more=has_more,
    )


@router.post("/{patron_id}/photo", response_model=PatronPhotoResponse)
@limiter.limit("10/minute")
async def upload_patron_photo(
    request: Request,
    patron_id: int,
    photo_data: PatronPhotoUpload,
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Upload a base64-encoded photo for a patron. Max 5MB."""
    import base64

    patron = await get_or_404(db, User, patron_id, "Patron not found")

    try:
        photo_str = photo_data.photo_data
        if "," in photo_str:
            photo_str = photo_str.split(",")[1]
        decoded = base64.b64decode(photo_str)
        if len(decoded) > 5 * 1024 * 1024:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Photo size exceeds 5MB limit"
            )
        if photo_data.content_type not in ["image/jpeg", "image/png", "image/gif", "image/webp"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid image format. Supported: JPEG, PNG, GIF, WebP",
            )
        photo_url = f"data:{photo_data.content_type};base64,{photo_str}"
    except HTTPException:
        raise
    except Exception:  # noqa: BLE001  # photo decode — translates to HTTP 400
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid photo data"
        ) from None

    patron.photo_url = photo_url
    await db.commit()
    await db.refresh(patron)

    return PatronPhotoResponse(photo_url=photo_url, message="Photo uploaded successfully")


@router.delete("/{patron_id}/photo", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("10/minute")
async def delete_patron_photo(
    request: Request,
    patron_id: int,
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Delete a patron's photo."""
    patron = await get_or_404(db, User, patron_id, "Patron not found")
    patron.photo_url = None
    await db.commit()


router.include_router(patron_circulation_router)

@router.get("/{patron_id}/family", response_model=PatronFamilyResponse)
async def get_patron_family(
    patron_id: int,
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Get family/linked accounts for a patron."""
    patron = await get_or_404(db, User, patron_id, "Patron not found")

    parent_guardian = None
    if patron.parent_guardian_id:
        parent_result = await db.execute(select(User).where(User.id == patron.parent_guardian_id))
        parent = parent_result.scalar_one_or_none()
        if parent:
            parent_guardian = LinkedAccountInfo(
                id=parent.id,
                first_name=parent.first_name,
                last_name=parent.last_name,
                email=parent.email,
                library_card=parent.library_card,
                is_active=parent.is_active,
            )

    children_result = await db.execute(select(User).where(User.parent_guardian_id == patron_id))
    children_list = children_result.scalars().all()
    children = [
        LinkedAccountInfo(
            id=child.id,
            first_name=child.first_name,
            last_name=child.last_name,
            email=child.email,
            library_card=child.library_card,
            is_active=child.is_active,
        )
        for child in children_list
    ]

    return PatronFamilyResponse(
        patron_id=patron_id,
        parent_guardian=parent_guardian,
        children=children,
    )


# =============================================================================
# Active Holds for Patron (flattened view; backs librarian-agent templates)
# =============================================================================


class PatronActiveHold(BaseModel):
    hold_id: int
    hold_status: str
    queue_position: Optional[int] = None
    hold_created_at: datetime
    hold_notified_at: Optional[datetime] = None
    hold_expires_at: Optional[datetime] = None
    pickup_location_id: Optional[int] = None
    pickup_branch_name: Optional[str] = None
    catalog_item_id: int
    hold_title: str
    hold_author: Optional[str] = None
    hold_item_type: Optional[str] = None
    hold_cover_url: Optional[str] = None


class PatronActiveHoldsResponse(BaseModel):
    patron_id: int
    holds: list[PatronActiveHold]


@router.get(
    "/{patron_id}/active-holds",
    response_model=PatronActiveHoldsResponse,
)
async def list_patron_active_holds(
    patron_id: int,
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Active holds (pending or ready) for one patron, flattened with bib title."""
    from sqlalchemy import text

    rows = (
        (
            await db.execute(
                text(
                    "SELECT hold_id, hold_status, queue_position, hold_created_at, "
                    "       hold_notified_at, hold_expires_at, pickup_location_id, "
                    "       pickup_branch_name, catalog_item_id, hold_title, "
                    "       hold_author, hold_item_type, hold_cover_url "
                    "FROM patron_active_holds "
                    "WHERE user_id = :uid "
                    "ORDER BY hold_created_at ASC"
                ),
                {"uid": patron_id},
            )
        )
        .mappings()
        .all()
    )

    holds = [
        PatronActiveHold(
            hold_id=row["hold_id"],
            hold_status=str(row["hold_status"]),
            queue_position=row["queue_position"],
            hold_created_at=row["hold_created_at"],
            hold_notified_at=row["hold_notified_at"],
            hold_expires_at=row["hold_expires_at"],
            pickup_location_id=row["pickup_location_id"],
            pickup_branch_name=row["pickup_branch_name"],
            catalog_item_id=row["catalog_item_id"],
            hold_title=row["hold_title"],
            hold_author=row["hold_author"],
            hold_item_type=row["hold_item_type"],
            hold_cover_url=row["hold_cover_url"],
        )
        for row in rows
    ]
    return PatronActiveHoldsResponse(patron_id=patron_id, holds=holds)


# =============================================================================
# Teacher card management
# =============================================================================


class TeacherCardUpdate(BaseModel):
    school_id: int | None = None


@router.patch("/{patron_id}/teacher-card", response_model=UserResponse)
@limiter.limit("20/minute")
async def update_teacher_card(
    request: Request,
    patron_id: int,
    body: TeacherCardUpdate,
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Grant or revoke a patron's teacher card.

    Audited via AuditAction.CHANGE_ROLE.
    """
    patron = await get_or_404(db, User, patron_id, "Patron not found")

    previous_role = patron.role
    previous_school_id = patron.school_id

    if body.school_id is not None:
        school = await db.get(OutreachPartner, body.school_id)
        if school is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="School (outreach partner) not found",
            )
        patron.role = UserRole.TEACHER
        patron.school_id = body.school_id
        action_detail = "grant"
    else:
        patron.role = UserRole.PATRON
        patron.school_id = None
        action_detail = "revoke"

    db.add(
        AuditLog(
            admin_id=staff_user.id,
            target_user_id=patron.id,
            action=AuditAction.CHANGE_ROLE,
            details={
                "feature": "teacher_card",
                "action": action_detail,
                "previous_role": str(previous_role),
                "new_role": str(patron.role),
                "previous_school_id": previous_school_id,
                "new_school_id": patron.school_id,
            },
        )
    )

    await db.commit()
    await db.refresh(patron)
    return patron

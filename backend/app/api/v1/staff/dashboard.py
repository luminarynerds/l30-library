# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Staff Dashboard API endpoints.

Provides aggregate metrics for the staff dashboard:
- /staff/dashboard/stats    - key operational stats (flat)
- /staff/dashboard/metrics  - complete dashboard metrics (nested, for frontend)
- /staff/dashboard/activity - recent activity feed
- /staff/dashboard/outreach - outreach program metrics
- /staff/dashboard/circulation - circulation snapshot
- /staff/dashboard/overdue  - paginated overdue items
- /staff/dashboard/popular-items - popular items ranking
- /staff/dashboard/theme-velocity - theme circulation velocity
- /staff/dashboard/holds-queue - hold queue status
- /staff/dashboard/alerts   - system operational alerts
- /staff/dashboard/collection-health - collection health score
- /staff/dashboard/quick-actions - staff quick actions
"""
from app.core.logging import get_logger
from datetime import date, datetime, timedelta, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from ....core.database import get_db
from ....models.user import User
from ....api.v1.dependencies import require_staff
from ....services.dashboard_service import DashboardMetricsService
from ....schemas.dashboard import (
    DashboardMetricsResponse,
    CirculationSnapshot,
    OverdueItemsResponse,
    PopularItemsResponse,
    ThemeVelocityResponse,
    HoldQueueStatus as HoldQueueStatusSchema,
    SystemAlertsResponse,
    CollectionHealthResponse,
    QuickActionRequest,
    QuickActionResponse,
)

router = APIRouter(prefix="/staff/dashboard", tags=["staff-dashboard"])
logger = get_logger(__name__)


# ── Response schemas ──────────────────────────────────────────────────────────

class DashboardStats(BaseModel):
    # Circulation
    active_checkouts: int
    overdue_count: int
    checkouts_today: int
    returns_today: int
    # Holds
    pending_holds: int
    ready_holds: int
    # Patrons
    total_patrons: int
    active_patrons_30d: int
    # Fines
    outstanding_fines_total: float
    patrons_with_fines: int
    # Lost & damaged
    lost_items_total: int
    lost_items_this_month: int
    damaged_items_pending: int
    items_in_mending: int
    claims_returned_pending: int
    lost_item_charges_outstanding: float
    # Outreach
    active_outreach_partners: int
    upcoming_visits: int
    overdue_bulk_checkouts: int
    deposits_held_total: float


class ActivityItem(BaseModel):
    activity_type: str
    description: str
    timestamp: datetime
    item_title: Optional[str] = None


class ActivityFeed(BaseModel):
    activities: List[ActivityItem]


class OutreachStats(BaseModel):
    total_partners: int
    active_partners: int
    upcoming_visits_this_week: int
    active_bulk_checkouts: int


class ComparisonStats(BaseModel):
    checkouts_today: int
    checkouts_last_week: int
    checkouts_last_year: int
    returns_today: int
    returns_last_week: int
    returns_last_year: int
    checkout_trend_percent: float  # % change from last week
    return_trend_percent: float


class TrendingItem(BaseModel):
    item_id: int
    title: str
    author: Optional[str]
    item_type: str
    checkout_count_today: int
    checkout_count_week: int
    hold_count: int
    velocity_score: float


class TrendingItemsResponse(BaseModel):
    items: List[TrendingItem]
    timestamp: datetime


class BusiestHour(BaseModel):
    hour: int
    activity_count: int
    activity_type: str  # "checkouts", "returns", "holds"
    is_peak_now: bool
    upcoming_peak_in_minutes: Optional[int]


class ActivePatronsData(BaseModel):
    active_today: int
    active_this_hour: int
    peak_hour_expected: Optional[int]


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/metrics", response_model=DashboardMetricsResponse)
async def get_complete_metrics(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_staff),
) -> DashboardMetricsResponse:
    """Get complete dashboard metrics in nested format for the frontend."""
    service = DashboardMetricsService(db)
    return await service.get_complete_metrics()


@router.get("/circulation", response_model=CirculationSnapshot)
async def get_circulation_snapshot(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_staff),
) -> CirculationSnapshot:
    """Get current circulation snapshot."""
    service = DashboardMetricsService(db)
    return await service.get_circulation_snapshot()


@router.get("/overdue", response_model=OverdueItemsResponse)
async def get_overdue_items(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_staff),
) -> OverdueItemsResponse:
    """Get paginated overdue items with details."""
    service = DashboardMetricsService(db)
    return await service.get_overdue_items(skip=skip, limit=limit)


@router.get("/popular-items", response_model=PopularItemsResponse)
async def get_popular_items(
    days: int = Query(90, ge=1, le=365),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_staff),
) -> PopularItemsResponse:
    """Get most popular items by checkout count."""
    service = DashboardMetricsService(db)
    return await service.get_popular_items(days=days, limit=limit)


@router.get("/theme-velocity", response_model=ThemeVelocityResponse)
async def get_theme_velocity(
    days: int = Query(90, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_staff),
) -> ThemeVelocityResponse:
    """Get circulation velocity by theme/subject."""
    service = DashboardMetricsService(db)
    return await service.get_theme_velocity(days=days)


@router.get("/holds-queue", response_model=HoldQueueStatusSchema)
async def get_holds_queue_status(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_staff),
) -> HoldQueueStatusSchema:
    """Get hold queue analytics."""
    service = DashboardMetricsService(db)
    return await service.get_holds_queue_status()


@router.get("/alerts", response_model=SystemAlertsResponse)
async def get_system_alerts(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_staff),
) -> SystemAlertsResponse:
    """Get system operational alerts."""
    service = DashboardMetricsService(db)
    return await service.get_system_alerts()


@router.get("/collection-health", response_model=CollectionHealthResponse)
async def get_collection_health(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_staff),
) -> CollectionHealthResponse:
    """Get collection health score and breakdown."""
    service = DashboardMetricsService(db)
    return await service.calculate_collection_health()


@router.post("/quick-actions", response_model=QuickActionResponse)
async def execute_quick_action(
    action: QuickActionRequest,
    db: AsyncSession = Depends(get_db),
    staff_user: User = Depends(require_staff),
) -> QuickActionResponse:
    """Execute quick dashboard actions (mark returned, send notice, waive fine)."""
    service = DashboardMetricsService(db)
    return await service.execute_quick_action(action, staff_user.id)


@router.get("/stats", response_model=DashboardStats)
async def get_dashboard_stats(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_staff),
) -> DashboardStats:
    """Get aggregate operational statistics for the staff dashboard.

    Split into independent queries so that a failure in auxiliary tables
    (lost/damaged, outreach) does not zero out core circulation stats.
    """
    now = datetime.now(timezone.utc)
    today = now.date()
    thirty_days_ago = now - timedelta(days=30)
    month_start = today.replace(day=1)

    # --- Core circulation, holds, patrons, fines (essential tables) ---
    try:
        core_results = await db.execute(
            text("""
        SELECT
            (SELECT COUNT(*) FROM checkouts WHERE status = 'active') AS active_checkouts,
            (SELECT COUNT(*) FROM checkouts WHERE status IN ('active', 'overdue')
                AND due_date < CURRENT_DATE) AS overdue_count,
            (SELECT COUNT(*) FROM checkouts WHERE DATE(checked_out_at) = :today) AS checkouts_today,
            (SELECT COUNT(*) FROM checkouts WHERE status = 'returned'
                AND DATE(returned_at) = :today) AS returns_today,
            (SELECT COUNT(*) FROM holds WHERE status = 'pending') AS pending_holds,
            (SELECT COUNT(*) FROM holds WHERE status = 'ready') AS ready_holds,
            (SELECT COUNT(*) FROM users WHERE role = 'patron') AS total_patrons,
            (SELECT COUNT(DISTINCT user_id) FROM checkouts
                WHERE checked_out_at >= :thirty_days_ago) AS active_patrons_30d,
            (SELECT COALESCE(SUM(amount), 0) FROM fines
                WHERE status IN ('unpaid', 'partial')) AS outstanding_fines_total,
            (SELECT COUNT(DISTINCT user_id) FROM fines
                WHERE status IN ('unpaid', 'partial')) AS patrons_with_fines
        """),
            {"today": today, "thirty_days_ago": thirty_days_ago},
        )
        core = core_results.fetchone()
    except SQLAlchemyError:
        # A failed statement leaves the whole transaction aborted in
        # Postgres until rolled back -- without this, every later query on
        # this session (the "independent" aux queries below, and anything
        # else the caller does with this request's db session) would also
        # raise InFailedSqlTransactionError, defeating the point of splitting
        # these into independent try/excepts.
        await db.rollback()
        logger.exception("Failed to load core dashboard stats")
        core = None

    active_checkouts = (core[0] or 0) if core else 0
    overdue_count = (core[1] or 0) if core else 0
    checkouts_today = (core[2] or 0) if core else 0
    returns_today = (core[3] or 0) if core else 0
    pending_holds = (core[4] or 0) if core else 0
    ready_holds = (core[5] or 0) if core else 0
    total_patrons = (core[6] or 0) if core else 0
    active_patrons_30d = (core[7] or 0) if core else 0
    outstanding_fines_total = float(core[8] or 0) if core else 0.0
    patrons_with_fines = (core[9] or 0) if core else 0

    # --- Lost & damaged (auxiliary tables, may not exist) ---
    lost_items_total = 0
    lost_items_this_month = 0
    damaged_items_pending = 0
    items_in_mending = 0
    claims_returned_pending = 0
    lost_item_charges_outstanding = 0.0
    try:
        ld_results = await db.execute(
            text("""
        SELECT
            (SELECT COUNT(*) FROM lost_item_records
                WHERE status NOT IN ('found', 'written_off')),
            (SELECT COUNT(*) FROM lost_item_records
                WHERE created_at >= :month_start),
            (SELECT COUNT(*) FROM damaged_item_records
                WHERE status IN ('reported', 'assessment_pending', 'repairable')),
            (SELECT COUNT(*) FROM damaged_item_records
                WHERE status = 'in_mending'),
            (SELECT COUNT(*) FROM claims_returned_disputes
                WHERE status IN ('pending', 'under_review', 'search_in_progress')),
            (SELECT COALESCE(SUM(f.amount), 0) FROM fines f
                WHERE f.fine_type = 'lost_item'
                AND f.status IN ('unpaid', 'partial'))
        """),
            {"month_start": month_start},
        )
        ld = ld_results.fetchone()
        if ld:
            lost_items_total = ld[0] or 0
            lost_items_this_month = ld[1] or 0
            damaged_items_pending = ld[2] or 0
            items_in_mending = ld[3] or 0
            claims_returned_pending = ld[4] or 0
            lost_item_charges_outstanding = float(ld[5] or 0)
    except SQLAlchemyError:
        # Roll back so the aborted transaction doesn't poison the next
        # (independent) query block on this same session -- see the core
        # stats except block above.
        await db.rollback()
        logger.warning("Lost/damaged tables not available, defaulting to zero")

    # --- Outreach (auxiliary tables, may not exist) ---
    active_outreach_partners = 0
    upcoming_visits = 0
    overdue_bulk_checkouts = 0
    deposits_held_total = 0.0
    try:
        or_results = await db.execute(
            text("""
        SELECT
            (SELECT COUNT(*) FROM outreach_partners
                WHERE status = 'active'),
            (SELECT COUNT(*) FROM outreach_visits
                WHERE status IN ('scheduled', 'confirmed')
                AND scheduled_date >= :today),
            (SELECT COUNT(*) FROM bulk_checkouts
                WHERE status = 'overdue'),
            (SELECT COALESCE(SUM(amount), 0) FROM outreach_deposits
                WHERE status IN ('held', 'partially_applied'))
        """),
            {"today": today},
        )
        or_row = or_results.fetchone()
        if or_row:
            active_outreach_partners = or_row[0] or 0
            upcoming_visits = or_row[1] or 0
            overdue_bulk_checkouts = or_row[2] or 0
            deposits_held_total = float(or_row[3] or 0)
    except SQLAlchemyError:
        # See the core stats except block above for why this rollback
        # matters -- an aborted transaction otherwise poisons every later
        # query on this session.
        await db.rollback()
        logger.warning("Outreach tables not available, defaulting to zero")

    return DashboardStats(
        active_checkouts=active_checkouts,
        overdue_count=overdue_count,
        checkouts_today=checkouts_today,
        returns_today=returns_today,
        pending_holds=pending_holds,
        ready_holds=ready_holds,
        total_patrons=total_patrons,
        active_patrons_30d=active_patrons_30d,
        outstanding_fines_total=outstanding_fines_total,
        patrons_with_fines=patrons_with_fines,
        lost_items_total=lost_items_total,
        lost_items_this_month=lost_items_this_month,
        damaged_items_pending=damaged_items_pending,
        items_in_mending=items_in_mending,
        claims_returned_pending=claims_returned_pending,
        lost_item_charges_outstanding=lost_item_charges_outstanding,
        active_outreach_partners=active_outreach_partners,
        upcoming_visits=upcoming_visits,
        overdue_bulk_checkouts=overdue_bulk_checkouts,
        deposits_held_total=deposits_held_total,
    )



class EnhancedDashboardStats(BaseModel):
    checkouts_today: int = 0
    returns_today: int = 0
    total_transactions_today: int = 0
    pending_holds: int = 0
    ready_holds: int = 0
    items_on_hold_shelf: int = 0
    total_items_on_hold: int = 0
    active_checkouts: int = 0
    overdue_count: int = 0
    busiest_hour: int = 0
    busiest_hour_activity: int = 0
    hourly_breakdown: list = []
    comparison: Optional[ComparisonStats] = None
    trending_items: list = []
    total_patrons: int = 0
    active_patrons_30d: int = 0


@router.get("/stats/enhanced", response_model=EnhancedDashboardStats)
async def get_enhanced_dashboard_stats(
    db: AsyncSession = Depends(get_db),
    staff_user: User = Depends(require_staff),
) -> EnhancedDashboardStats:
    """Get enhanced dashboard stats combining core stats with comparison and trending data."""
    # Get core stats by calling existing function
    core = await get_dashboard_stats(db=db, _=staff_user)

    # Get busiest hour
    busiest = await get_busiest_hour(db=db, _=staff_user)

    # Get comparison stats
    try:
        comparison = await get_comparison_stats(db=db, _=staff_user)
    except Exception:  # noqa: BLE001  # dashboard widget — degrade gracefully if comparison unavailable
        comparison = None

    # Get trending items
    try:
        trending = await get_trending_items(db=db, _=staff_user)
        trending_list = [item.dict() for item in trending.items]
    except Exception:  # noqa: BLE001  # dashboard widget — degrade gracefully if trending unavailable
        trending_list = []

    return EnhancedDashboardStats(
        checkouts_today=core.checkouts_today,
        returns_today=core.returns_today,
        total_transactions_today=core.checkouts_today + core.returns_today,
        pending_holds=core.pending_holds,
        ready_holds=core.ready_holds,
        items_on_hold_shelf=core.ready_holds,
        total_items_on_hold=core.pending_holds + core.ready_holds,
        active_checkouts=core.active_checkouts,
        overdue_count=core.overdue_count,
        busiest_hour=busiest.hour,
        busiest_hour_activity=busiest.activity_count,
        comparison=comparison,
        trending_items=trending_list,
        total_patrons=core.total_patrons,
        active_patrons_30d=core.active_patrons_30d,
    )

@router.get("/activity", response_model=ActivityFeed)
async def get_dashboard_activity(
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_staff),
) -> ActivityFeed:
    """Get recent circulation activity for the staff dashboard feed."""
    try:
        result = await db.execute(
            text("""
        SELECT
            'checkout' AS activity_type,
            COALESCE(ci.title, ci2.title, 'Unknown Item') AS item_title,
            c.checked_out_at AS timestamp
        FROM checkouts c
        LEFT JOIN catalog_items ci ON c.item_id = ci.id
        LEFT JOIN item_copies ic ON c.item_copy_id = ic.id
        LEFT JOIN catalog_items ci2 ON ic.catalog_item_id = ci2.id
        WHERE COALESCE(ci.id, ci2.id) IS NOT NULL
        ORDER BY c.checked_out_at DESC
        LIMIT :limit
            """),
            {"limit": limit},
        )

        rows = result.fetchall()

        activities = [
            ActivityItem(
                activity_type=row[0],
                description=f"Checked out: {row[1]}",
                item_title=row[1],
                timestamp=row[2],
            )
            for row in rows
        ]

        return ActivityFeed(activities=activities)
    except SQLAlchemyError:
        # See get_dashboard_stats' core-stats except block for why this
        # rollback matters -- an aborted transaction otherwise poisons any
        # later query on this same request's db session.
        await db.rollback()
        logger.exception("Failed to load dashboard activity")
        return ActivityFeed(activities=[])


@router.get("/outreach", response_model=OutreachStats)
async def get_outreach_stats(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_staff),
) -> OutreachStats:
    """Get outreach program statistics for the staff dashboard."""
    today = date.today()
    week_end = today + timedelta(days=7)

    result = await db.execute(
        text("""
        SELECT
            (SELECT COUNT(*) FROM outreach_partners) AS total_partners,
            (SELECT COUNT(*) FROM outreach_partners WHERE status = 'active') AS active_partners,
            (SELECT COUNT(*) FROM outreach_visits
                WHERE status IN ('scheduled', 'confirmed')
                AND scheduled_date BETWEEN :today AND :week_end) AS upcoming_visits_this_week,
            (SELECT COUNT(*) FROM bulk_checkouts
                WHERE status = 'active') AS active_bulk_checkouts
        """),
        {"today": today, "week_end": week_end},
    )

    row = result.fetchone()

    return OutreachStats(
        total_partners=row[0] or 0,
        active_partners=row[1] or 0,
        upcoming_visits_this_week=row[2] or 0,
        active_bulk_checkouts=row[3] or 0,
    )


@router.get("/comparison", response_model=ComparisonStats)
async def get_comparison_stats(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_staff),
) -> ComparisonStats:
    """Get today's stats compared to last week and last year."""
    now = datetime.now(timezone.utc)
    today = now.date()
    last_week = today - timedelta(days=7)
    last_year = today - timedelta(days=365)

    result = await db.execute(
        text("""
        SELECT
            -- Today
            (SELECT COUNT(*) FROM checkouts WHERE DATE(checked_out_at) = :today) AS checkouts_today,
            (SELECT COUNT(*) FROM checkouts WHERE status = 'returned'
                AND DATE(returned_at) = :today) AS returns_today,
            -- Last week same day
            (SELECT COUNT(*) FROM checkouts WHERE DATE(checked_out_at) = :last_week) AS checkouts_last_week,
            (SELECT COUNT(*) FROM checkouts WHERE status = 'returned'
                AND DATE(returned_at) = :last_week) AS returns_last_week,
            -- Last year same day
            (SELECT COUNT(*) FROM checkouts WHERE DATE(checked_out_at) = :last_year) AS checkouts_last_year,
            (SELECT COUNT(*) FROM checkouts WHERE status = 'returned'
                AND DATE(returned_at) = :last_year) AS returns_last_year
        """),
        {
            "today": today,
            "last_week": last_week,
            "last_year": last_year,
        },
    )

    row = result.fetchone()
    checkouts_today = row[0] or 0
    returns_today = row[1] or 0
    checkouts_last_week = row[2] or 0
    returns_last_week = row[3] or 0
    checkouts_last_year = row[4] or 0
    returns_last_year = row[5] or 0

    # Calculate trend percentages
    checkout_trend = (
        ((checkouts_today - checkouts_last_week) / checkouts_last_week * 100)
        if checkouts_last_week > 0
        else 0
    )
    return_trend = (
        ((returns_today - returns_last_week) / returns_last_week * 100)
        if returns_last_week > 0
        else 0
    )

    return ComparisonStats(
        checkouts_today=checkouts_today,
        checkouts_last_week=checkouts_last_week,
        checkouts_last_year=checkouts_last_year,
        returns_today=returns_today,
        returns_last_week=returns_last_week,
        returns_last_year=returns_last_year,
        checkout_trend_percent=checkout_trend,
        return_trend_percent=return_trend,
    )


@router.get("/trending", response_model=TrendingItemsResponse)
async def get_trending_items(
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_staff),
) -> TrendingItemsResponse:
    """Get trending items based on recent checkout activity."""
    now = datetime.now(timezone.utc)
    today = now.date()
    week_ago = today - timedelta(days=7)

    result = await db.execute(
        text("""
        SELECT
            ci.id,
            ci.title,
            ci.author,
            ci.item_type,
            (SELECT COUNT(*) FROM checkouts c2
                LEFT JOIN item_copies ic2 ON c2.item_copy_id = ic2.id
                WHERE COALESCE(c2.item_id, ic2.catalog_item_id) = ci.id
                AND DATE(c2.checked_out_at) = :today) AS checkouts_today,
            (SELECT COUNT(*) FROM checkouts c3
                LEFT JOIN item_copies ic3 ON c3.item_copy_id = ic3.id
                WHERE COALESCE(c3.item_id, ic3.catalog_item_id) = ci.id
                AND DATE(c3.checked_out_at) >= :week_ago) AS checkouts_week,
            (SELECT COUNT(*) FROM holds WHERE item_id = ci.id
                AND status = 'pending') AS hold_count
        FROM catalog_items ci
        WHERE EXISTS (
            SELECT 1 FROM checkouts c
            LEFT JOIN item_copies ic ON c.item_copy_id = ic.id
            WHERE COALESCE(c.item_id, ic.catalog_item_id) = ci.id
            AND DATE(c.checked_out_at) >= :week_ago
        )
        ORDER BY checkouts_week DESC, hold_count DESC
        LIMIT :limit
        """),
        {
            "today": today,
            "week_ago": week_ago,
            "limit": limit,
        },
    )

    rows = result.fetchall()
    items = []

    for row in rows:
        checkouts_week = row[5] or 0
        checkouts_today = row[4] or 0
        # Velocity score: recent checkouts weighted higher
        velocity_score = (checkouts_today * 2) + (checkouts_week * 0.5)

        items.append(
            TrendingItem(
                item_id=row[0],
                title=row[1],
                author=row[2],
                item_type=row[3],
                checkout_count_today=checkouts_today,
                checkout_count_week=checkouts_week,
                hold_count=row[6] or 0,
                velocity_score=velocity_score,
            )
        )

    return TrendingItemsResponse(items=items, timestamp=now)


@router.get("/busiest-hour", response_model=BusiestHour)
async def get_busiest_hour(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_staff),
) -> BusiestHour:
    """Get prediction for busiest hour of the day based on patterns."""
    now = datetime.now(timezone.utc)
    current_hour = now.hour
    today = now.date()
    week_ago = today - timedelta(days=7)

    result = await db.execute(
        text("""
        SELECT
            EXTRACT(HOUR FROM c.checked_out_at) AS hour,
            COUNT(*) AS activity_count,
            'checkouts' AS activity_type
        FROM checkouts c
        WHERE DATE(c.checked_out_at) >= :week_ago
        GROUP BY EXTRACT(HOUR FROM c.checked_out_at)
        ORDER BY activity_count DESC
        LIMIT 1
        """),
        {"week_ago": week_ago},
    )

    row = result.fetchone()

    if not row:
        # Default fallback
        return BusiestHour(
            hour=current_hour,
            activity_count=0,
            activity_type="checkouts",
            is_peak_now=False,
            upcoming_peak_in_minutes=None,
        )

    peak_hour = int(row[0])
    activity_count = row[1] or 0
    is_peak_now = peak_hour == current_hour

    # Calculate minutes until peak
    if not is_peak_now:
        if peak_hour > current_hour:
            minutes_to_peak = (peak_hour - current_hour) * 60 - now.minute
        else:
            minutes_to_peak = ((24 - current_hour) + peak_hour) * 60 - now.minute
    else:
        minutes_to_peak = None

    return BusiestHour(
        hour=peak_hour,
        activity_count=activity_count,
        activity_type="checkouts",
        is_peak_now=is_peak_now,
        upcoming_peak_in_minutes=minutes_to_peak if not is_peak_now else None,
    )


@router.get("/active-patrons", response_model=ActivePatronsData)
async def get_active_patrons(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_staff),
) -> ActivePatronsData:
    """Get active patrons currently using the library."""
    now = datetime.now(timezone.utc)
    today = now.date()
    hour_ago = now - timedelta(hours=1)

    result = await db.execute(
        text("""
        SELECT
            -- Active patrons today (has activity in last 24 hours)
            (SELECT COUNT(DISTINCT user_id) FROM checkouts
                WHERE DATE(checked_out_at) = :today
                OR (DATE(returned_at) = :today AND returned_at IS NOT NULL)) AS active_today,
            -- Active this hour
            (SELECT COUNT(DISTINCT user_id) FROM checkouts
                WHERE checked_out_at >= :hour_ago
                OR returned_at >= :hour_ago) AS active_this_hour,
            -- Peak hour prediction
            (SELECT EXTRACT(HOUR FROM checked_out_at) AS peak_hour
                FROM checkouts c
                WHERE DATE(c.checked_out_at) >= :today - interval '7 days'
                GROUP BY EXTRACT(HOUR FROM checked_out_at)
                ORDER BY COUNT(*) DESC
                LIMIT 1) AS peak_hour
        """),
        {
            "today": today,
            "hour_ago": hour_ago,
        },
    )

    row = result.fetchone()

    return ActivePatronsData(
        active_today=row[0] or 0,
        active_this_hour=row[1] or 0,
        peak_hour_expected=int(row[2]) if row[2] else None,
    )

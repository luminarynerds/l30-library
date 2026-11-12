# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Role-calibrated staff dashboard endpoints.

Four landing pages tuned to staff role:
- /staff/dashboard/desk   -- circulation (front desk)
- /staff/dashboard/tech   -- system health
- /staff/dashboard/youth  -- programs / events
- /staff/dashboard/admin-overview  -- governance / compliance

All endpoints require staff authentication but are not restricted
to specific staff_role values -- the frontend decides which to show.
"""

from app.core.logging import get_logger
import time
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.database import get_db
from ...models.user import User
from .dependencies import require_staff

router = APIRouter(prefix="/staff/dashboard", tags=["staff-dashboards"])
logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------

# -- Desk (circulation) --


class RecentTransaction(BaseModel):
    transaction_type: str  # "checkout" or "return"
    item_title: str
    patron_name: str
    timestamp: datetime


class DeskDashboardResponse(BaseModel):
    items_checked_out_today: int = 0
    items_returned_today: int = 0
    active_holds_count: int = 0
    overdue_items_count: int = 0
    patrons_served_today: int = 0
    recent_transactions: List[RecentTransaction] = Field(default_factory=list)


# -- Tech (system health) --


class SystemHealthSummary(BaseModel):
    postgres_status: str = "unknown"
    postgres_latency_ms: Optional[float] = None
    redis_status: str = "unknown"
    redis_latency_ms: Optional[float] = None


class BibframeSyncStatus(BaseModel):
    last_sync_at: Optional[datetime] = None
    total_works: int = 0
    total_instances: int = 0
    error_count: int = 0


class RecentError(BaseModel):
    title: str
    component: Optional[str] = None
    reported_at: datetime


class TechDashboardResponse(BaseModel):
    system_health: SystemHealthSummary = Field(default_factory=SystemHealthSummary)
    bibframe_sync: BibframeSyncStatus = Field(default_factory=BibframeSyncStatus)
    database_size_mb: Optional[float] = None
    active_connections: int = 0
    recent_errors: List[RecentError] = Field(default_factory=list)


# -- Youth (programs / events) --


class UpcomingEvent(BaseModel):
    id: int
    title: str
    start_time: datetime
    audience: Optional[str] = None
    registration_count: int = 0


class ReadingChallengeStats(BaseModel):
    active_programs: int = 0
    active_participants: int = 0
    books_logged: int = 0


class RecentRegistration(BaseModel):
    patron_name: str
    program_title: str
    registered_at: datetime


class YouthDashboardResponse(BaseModel):
    active_programs_count: int = 0
    total_registrations: int = 0
    upcoming_events: List[UpcomingEvent] = Field(default_factory=list)
    reading_challenge_stats: ReadingChallengeStats = Field(default_factory=ReadingChallengeStats)
    recent_registrations: List[RecentRegistration] = Field(default_factory=list)


# -- Admin (governance / compliance) --


class NextBoardMeeting(BaseModel):
    id: int
    title: str
    scheduled_date: datetime
    meeting_type: str


class AdminDashboardResponse(BaseModel):
    next_board_meeting: Optional[NextBoardMeeting] = None
    open_action_items_count: int = 0
    pending_policy_reviews: int = 0
    staff_count: int = 0
    active_patrons_30d: int = 0
    legal_holds_active: int = 0
    retention_schedules_count: int = 0


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("/desk", response_model=DeskDashboardResponse)
async def get_desk_dashboard(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_staff),
) -> DeskDashboardResponse:
    """Circulation-focused dashboard for front desk staff."""
    today = datetime.now(timezone.utc).date()

    # Core counts
    counts = None
    try:
        result = await db.execute(
            text("""
            SELECT
                (SELECT COUNT(*) FROM checkouts
                    WHERE DATE(checked_out_at) = :today) AS checked_out_today,
                (SELECT COUNT(*) FROM checkouts
                    WHERE status = 'returned' AND DATE(returned_at) = :today) AS returned_today,
                (SELECT COUNT(*) FROM holds
                    WHERE status IN ('pending', 'ready')) AS active_holds,
                (SELECT COUNT(*) FROM checkouts
                    WHERE status IN ('active', 'overdue')
                    AND due_date < CURRENT_TIMESTAMP) AS overdue_items,
                (SELECT COUNT(DISTINCT user_id) FROM checkouts
                    WHERE DATE(checked_out_at) = :today
                    OR (status = 'returned' AND DATE(returned_at) = :today)) AS patrons_served
            """),
            {"today": today},
        )
        counts = result.fetchone()
    except SQLAlchemyError:
        logger.exception("Desk dashboard: failed to load core counts")

    # Recent transactions (last 10)
    recent: List[RecentTransaction] = []
    try:
        result = await db.execute(
            text("""
            (
                SELECT
                    'checkout' AS tx_type,
                    COALESCE(ci.title, 'Unknown') AS item_title,
                    CONCAT(u.first_name, ' ', u.last_name) AS patron_name,
                    c.checked_out_at AS ts
                FROM checkouts c
                JOIN users u ON c.user_id = u.id
                LEFT JOIN catalog_items ci ON c.item_id = ci.id
                WHERE DATE(c.checked_out_at) = :today
                ORDER BY c.checked_out_at DESC
                LIMIT 5
            )
            UNION ALL
            (
                SELECT
                    'return' AS tx_type,
                    COALESCE(ci.title, 'Unknown') AS item_title,
                    CONCAT(u.first_name, ' ', u.last_name) AS patron_name,
                    c.returned_at AS ts
                FROM checkouts c
                JOIN users u ON c.user_id = u.id
                LEFT JOIN catalog_items ci ON c.item_id = ci.id
                WHERE c.status = 'returned'
                    AND DATE(c.returned_at) = :today
                ORDER BY c.returned_at DESC
                LIMIT 5
            )
            ORDER BY ts DESC
            LIMIT 10
            """),
            {"today": today},
        )
        for row in result.fetchall():
            recent.append(
                RecentTransaction(
                    transaction_type=row[0],
                    item_title=row[1],
                    patron_name=row[2],
                    timestamp=row[3],
                )
            )
    except SQLAlchemyError:
        logger.exception("Desk dashboard: failed to load recent transactions")

    return DeskDashboardResponse(
        items_checked_out_today=(counts[0] or 0) if counts else 0,
        items_returned_today=(counts[1] or 0) if counts else 0,
        active_holds_count=(counts[2] or 0) if counts else 0,
        overdue_items_count=(counts[3] or 0) if counts else 0,
        patrons_served_today=(counts[4] or 0) if counts else 0,
        recent_transactions=recent,
    )


@router.get("/tech", response_model=TechDashboardResponse)
async def get_tech_dashboard(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_staff),
) -> TechDashboardResponse:
    """System health dashboard for tech staff."""
    from ...core.cache import get_redis

    # -- Postgres health --
    pg_status = "unknown"
    pg_latency: Optional[float] = None
    active_conns = 0
    db_size_mb: Optional[float] = None
    try:
        start = time.perf_counter()
        await db.execute(text("SELECT 1"))
        pg_latency = round((time.perf_counter() - start) * 1000, 2)
        pg_status = "healthy" if pg_latency < 500 else "degraded"

        # Database size
        size_result = await db.execute(
            text("SELECT pg_database_size(current_database()) / (1024.0 * 1024.0)")
        )
        row = size_result.scalar()
        db_size_mb = round(float(row), 1) if row else None

        # Active connections
        conn_result = await db.execute(
            text("SELECT COUNT(*) FROM pg_stat_activity WHERE state = 'active'")
        )
        active_conns = conn_result.scalar() or 0
    except SQLAlchemyError:
        pg_status = "unhealthy"
        logger.exception("Tech dashboard: postgres check failed")

    # -- Redis health --
    redis_status = "unknown"
    redis_latency: Optional[float] = None
    try:
        redis = await get_redis()
        if redis:
            start = time.perf_counter()
            await redis.ping()
            redis_latency = round((time.perf_counter() - start) * 1000, 2)
            redis_status = "healthy"
        else:
            redis_status = "not_configured"
    except Exception:
        redis_status = "unhealthy"
        logger.exception("Tech dashboard: redis check failed")

    # -- BIBFRAME sync status --
    bf_sync = BibframeSyncStatus()
    try:
        bf_result = await db.execute(
            text("""
            SELECT
                (SELECT COUNT(*) FROM bibframe_works) AS total_works,
                (SELECT COUNT(*) FROM bibframe_instances) AS total_instances
            """)
        )
        bf_row = bf_result.fetchone()
        if bf_row:
            bf_sync.total_works = bf_row[0] or 0
            bf_sync.total_instances = bf_row[1] or 0
    except SQLAlchemyError:
        logger.warning("Tech dashboard: BIBFRAME tables not available")

    # -- Recent system issues --
    recent_errors: List[RecentError] = []
    try:
        err_result = await db.execute(
            text("""
            SELECT title, component, reported_at
            FROM system_status_logs
            WHERE status IN ('degraded', 'major_outage', 'partial_outage')
            ORDER BY reported_at DESC
            LIMIT 10
            """)
        )
        for row in err_result.fetchall():
            recent_errors.append(RecentError(title=row[0], component=row[1], reported_at=row[2]))
    except SQLAlchemyError:
        logger.warning("Tech dashboard: system_status_logs not available")

    return TechDashboardResponse(
        system_health=SystemHealthSummary(
            postgres_status=pg_status,
            postgres_latency_ms=pg_latency,
            redis_status=redis_status,
            redis_latency_ms=redis_latency,
        ),
        bibframe_sync=bf_sync,
        database_size_mb=db_size_mb,
        active_connections=active_conns,
        recent_errors=recent_errors,
    )


@router.get("/youth", response_model=YouthDashboardResponse)
async def get_youth_dashboard(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_staff),
) -> YouthDashboardResponse:
    """Programs and events dashboard for youth services staff."""
    now = datetime.now(timezone.utc)
    today = now.date()
    week_out = today + timedelta(days=7)

    # Core program counts
    active_programs = 0
    total_regs = 0
    try:
        result = await db.execute(
            text("""
            SELECT
                (SELECT COUNT(*) FROM programs
                    WHERE status IN ('planned', 'scheduled', 'in_progress')) AS active_count,
                (SELECT COUNT(*) FROM program_registrations
                    WHERE status IN ('registered', 'waitlisted')) AS total_regs
            """)
        )
        row = result.fetchone()
        if row:
            active_programs = row[0] or 0
            total_regs = row[1] or 0
    except SQLAlchemyError:
        logger.exception("Youth dashboard: failed to load program counts")

    # Upcoming events (next 7 days)
    upcoming: List[UpcomingEvent] = []
    try:
        week_end_dt = datetime.combine(week_out, datetime.min.time()).replace(tzinfo=timezone.utc)
        result = await db.execute(
            text("""
            SELECT e.id, e.title, e.start_time, e.audience,
                (SELECT COUNT(*) FROM program_registrations pr
                    JOIN programs p ON pr.program_id = p.id
                    WHERE p.title = e.title
                    AND pr.status IN ('registered', 'waitlisted')) AS reg_count
            FROM events e
            WHERE e.is_published = true
                AND e.start_time >= :now
                AND e.start_time < :week_end
            ORDER BY e.start_time ASC
            LIMIT 15
            """),
            {"now": now, "week_end": week_end_dt},
        )
        for row in result.fetchall():
            upcoming.append(
                UpcomingEvent(
                    id=row[0],
                    title=row[1],
                    start_time=row[2],
                    audience=row[3],
                    registration_count=row[4] or 0,
                )
            )
    except SQLAlchemyError:
        logger.exception("Youth dashboard: failed to load upcoming events")

    # Reading challenge stats
    rc = ReadingChallengeStats()
    try:
        result = await db.execute(
            text("""
            SELECT
                (SELECT COUNT(*) FROM reading_programs
                    WHERE is_active = true
                    AND start_date <= :today AND end_date >= :today) AS active_progs,
                (SELECT COUNT(*) FROM reading_registrations rr
                    JOIN reading_programs rp ON rr.program_id = rp.id
                    WHERE rp.is_active = true
                    AND rp.start_date <= :today AND rp.end_date >= :today) AS participants,
                (SELECT COUNT(*) FROM reading_log_entries rle
                    JOIN reading_registrations rr2 ON rle.registration_id = rr2.id
                    JOIN reading_programs rp2 ON rr2.program_id = rp2.id
                    WHERE rp2.is_active = true
                    AND rp2.start_date <= :today AND rp2.end_date >= :today) AS books_logged
            """),
            {"today": today},
        )
        row = result.fetchone()
        if row:
            rc.active_programs = row[0] or 0
            rc.active_participants = row[1] or 0
            rc.books_logged = row[2] or 0
    except SQLAlchemyError:
        logger.warning("Youth dashboard: reading programs tables not available")

    # Recent registrations (last 10)
    recent_regs: List[RecentRegistration] = []
    try:
        result = await db.execute(
            text("""
            SELECT
                CONCAT(u.first_name, ' ', u.last_name) AS patron_name,
                p.title AS program_title,
                pr.registered_at
            FROM program_registrations pr
            JOIN users u ON pr.user_id = u.id
            JOIN programs p ON pr.program_id = p.id
            WHERE pr.status = 'registered'
            ORDER BY pr.registered_at DESC
            LIMIT 10
            """)
        )
        for row in result.fetchall():
            recent_regs.append(
                RecentRegistration(
                    patron_name=row[0],
                    program_title=row[1],
                    registered_at=row[2],
                )
            )
    except SQLAlchemyError:
        logger.warning("Youth dashboard: failed to load recent registrations")

    return YouthDashboardResponse(
        active_programs_count=active_programs,
        total_registrations=total_regs,
        upcoming_events=upcoming,
        reading_challenge_stats=rc,
        recent_registrations=recent_regs,
    )


@router.get("/admin-overview", response_model=AdminDashboardResponse)
async def get_admin_dashboard(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_staff),
) -> AdminDashboardResponse:
    """Governance and compliance dashboard for admin staff."""
    now = datetime.now(timezone.utc)
    today = now.date()
    thirty_days_ago = now - timedelta(days=30)

    # Next board meeting
    next_meeting: Optional[NextBoardMeeting] = None
    try:
        result = await db.execute(
            text("""
            SELECT id, title, scheduled_date, meeting_type
            FROM board_meetings
            WHERE scheduled_date >= :now
                AND is_cancelled = false
            ORDER BY scheduled_date ASC
            LIMIT 1
            """),
            {"now": now},
        )
        row = result.fetchone()
        if row:
            next_meeting = NextBoardMeeting(
                id=row[0], title=row[1], scheduled_date=row[2], meeting_type=row[3]
            )
    except SQLAlchemyError:
        logger.warning("Admin dashboard: board_meetings not available")

    # Action items + policy reviews
    action_items = 0
    policy_reviews = 0
    try:
        result = await db.execute(
            text("""
            SELECT
                (SELECT COUNT(*) FROM meeting_action_items
                    WHERE status IN ('not_started', 'in_progress')) AS open_actions,
                (SELECT COUNT(*) FROM policy_reviews
                    WHERE status = 'pending_review'
                    OR next_review_due <= :today) AS pending_policies
            """),
            {"today": today},
        )
        row = result.fetchone()
        if row:
            action_items = row[0] or 0
            policy_reviews = row[1] or 0
    except SQLAlchemyError:
        logger.warning("Admin dashboard: action_items/policy_reviews not available")

    # Staff and patron counts
    staff_count = 0
    active_patrons = 0
    try:
        result = await db.execute(
            text("""
            SELECT
                (SELECT COUNT(*) FROM users
                    WHERE role IN ('staff', 'admin', 'super_admin', 'director')
                    AND is_active = true) AS staff_count,
                (SELECT COUNT(DISTINCT user_id) FROM checkouts
                    WHERE checked_out_at >= :thirty_days_ago) AS active_patrons
            """),
            {"thirty_days_ago": thirty_days_ago},
        )
        row = result.fetchone()
        if row:
            staff_count = row[0] or 0
            active_patrons = row[1] or 0
    except SQLAlchemyError:
        logger.exception("Admin dashboard: failed to load staff/patron counts")

    # Legal holds + retention schedules
    legal_holds = 0
    retention_count = 0
    try:
        result = await db.execute(
            text("""
            SELECT
                (SELECT COUNT(*) FROM board_legal_holds
                    WHERE is_active = true) AS legal_holds,
                (SELECT COUNT(*) FROM board_record_retention_schedules) AS retention_count
            """)
        )
        row = result.fetchone()
        if row:
            legal_holds = row[0] or 0
            retention_count = row[1] or 0
    except SQLAlchemyError:
        logger.warning("Admin dashboard: legal holds/retention not available")

    return AdminDashboardResponse(
        next_board_meeting=next_meeting,
        open_action_items_count=action_items,
        pending_policy_reviews=policy_reviews,
        staff_count=staff_count,
        active_patrons_30d=active_patrons,
        legal_holds_active=legal_holds,
        retention_schedules_count=retention_count,
    )

# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, List

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.logging import get_logger
from ...models.circulation import Checkout, CheckoutStatus, Hold, HoldStatus
from ...models.event import Event
from ...models.multi_branch import TransitRequest, TransitStatus
from ...models.user import User, UserRole

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class AlertItem:
    category: str
    severity: str  # "critical", "warning", "info"
    description: str
    count: int = 0
    details: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class MorningDashboard:
    generated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    alerts: List[AlertItem] = field(default_factory=list)
    items_due_today: int = 0
    holds_expiring_soon: int = 0
    new_patrons_today: int = 0
    events_today: int = 0
    staff_birthdays: List[Dict[str, Any]] = field(default_factory=list)
    staff_anniversaries: List[Dict[str, Any]] = field(default_factory=list)
    items_in_transit_long: int = 0
    overdue_buckets: Dict[str, int] = field(default_factory=dict)

    @property
    def total_alerts(self) -> int:
        return sum(a.count for a in self.alerts)

    def to_dict(self) -> Dict[str, Any]:
        by_severity: Dict[str, int] = {"critical": 0, "warning": 0, "info": 0}
        for alert in self.alerts:
            by_severity[alert.severity] = (
                by_severity.get(alert.severity, 0) + alert.count
            )
        return {
            "generated_at": self.generated_at.isoformat(),
            "total_alerts": self.total_alerts,
            "alerts_by_severity": by_severity,
            "items_due_today": self.items_due_today,
            "holds_expiring_soon": self.holds_expiring_soon,
            "new_patrons_today": self.new_patrons_today,
            "events_today": self.events_today,
            "staff_birthdays": self.staff_birthdays,
            "staff_anniversaries": self.staff_anniversaries,
            "items_in_transit_long": self.items_in_transit_long,
            "overdue_buckets": self.overdue_buckets,
        }


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------

class DailyAlertsService:

    @staticmethod
    async def generate_morning_dashboard(db: AsyncSession) -> MorningDashboard:
        dashboard = MorningDashboard()
        today = date.today()
        now = datetime.now(timezone.utc)

        # Start-of-day and end-of-day boundaries (UTC)
        day_start = datetime.combine(today, datetime.min.time()).replace(
            tzinfo=timezone.utc
        )
        day_end = day_start + timedelta(days=1)

        queries = [
            ("items due today", DailyAlertsService._query_items_due_today(db, dashboard, day_start, day_end)),
            ("expiring holds", DailyAlertsService._query_holds_expiring_soon(db, dashboard, now)),
            ("new patrons", DailyAlertsService._query_new_patrons(db, dashboard, day_start, day_end)),
            ("today's events", DailyAlertsService._query_events_today(db, dashboard, day_start, day_end)),
            ("staff birthdays", DailyAlertsService._query_staff_birthdays_anniversaries(db, dashboard, today)),
            ("transit items", DailyAlertsService._query_long_transit_items(db, dashboard, now)),
            ("overdue buckets", DailyAlertsService._query_overdue_buckets(db, dashboard, now)),
        ]

        for label, coro in queries:
            try:
                await coro
            except Exception as e:
                logger.error(f"Error querying {label}: {e}", exc_info=True)
                await db.rollback()

        logger.info(
            "Morning dashboard generated",
            extra={"total_alerts": dashboard.total_alerts},
        )
        return dashboard

    # ------------------------------------------------------------------
    # Individual query helpers
    # ------------------------------------------------------------------

    @staticmethod
    async def _query_items_due_today(
        db: AsyncSession,
        dashboard: MorningDashboard,
        day_start: datetime,
        day_end: datetime,
    ) -> None:
        result = await db.execute(
            select(func.count(Checkout.id)).where(
                and_(
                    Checkout.status == CheckoutStatus.active,
                    Checkout.due_date >= day_start,
                    Checkout.due_date < day_end,
                )
            )
        )
        count = result.scalar() or 0
        dashboard.items_due_today = count
        if count > 0:
            dashboard.alerts.append(
                AlertItem(
                    category="circulation",
                    severity="info",
                    description="Items due today (reminder calls)",
                    count=count,
                )
            )

    @staticmethod
    async def _query_holds_expiring_soon(
        db: AsyncSession,
        dashboard: MorningDashboard,
        now: datetime,
    ) -> None:
        expiry_window = now + timedelta(hours=48)
        result = await db.execute(
            select(func.count(Hold.id)).where(
                and_(
                    Hold.status == HoldStatus.ready,
                    Hold.expires_at.isnot(None),
                    Hold.expires_at <= expiry_window,
                    Hold.expires_at > now,
                )
            )
        )
        count = result.scalar() or 0
        dashboard.holds_expiring_soon = count
        if count > 0:
            dashboard.alerts.append(
                AlertItem(
                    category="holds",
                    severity="warning",
                    description="Holds expiring within 48 hours",
                    count=count,
                )
            )

    @staticmethod
    async def _query_new_patrons(
        db: AsyncSession,
        dashboard: MorningDashboard,
        day_start: datetime,
        day_end: datetime,
    ) -> None:
        result = await db.execute(
            select(func.count(User.id)).where(
                and_(
                    User.role == UserRole.PATRON,
                    User.created_at >= day_start,
                    User.created_at < day_end,
                )
            )
        )
        count = result.scalar() or 0
        dashboard.new_patrons_today = count
        if count > 0:
            dashboard.alerts.append(
                AlertItem(
                    category="patrons",
                    severity="info",
                    description="New patron registrations today",
                    count=count,
                )
            )

    @staticmethod
    async def _query_events_today(
        db: AsyncSession,
        dashboard: MorningDashboard,
        day_start: datetime,
        day_end: datetime,
    ) -> None:
        result = await db.execute(
            select(func.count(Event.id)).where(
                and_(
                    Event.is_published == True,  # noqa: E712
                    Event.start_time >= day_start,
                    Event.start_time < day_end,
                )
            )
        )
        count = result.scalar() or 0
        dashboard.events_today = count
        if count > 0:
            dashboard.alerts.append(
                AlertItem(
                    category="events",
                    severity="info",
                    description="Events happening today",
                    count=count,
                )
            )

    @staticmethod
    async def _query_staff_birthdays_anniversaries(
        db: AsyncSession,
        dashboard: MorningDashboard,
        today: date,
    ) -> None:
        staff_result = await db.execute(
            select(User).where(
                and_(
                    User.role.in_([UserRole.STAFF, UserRole.ADMIN]),
                    User.is_active == True,  # noqa: E712
                )
            )
        )
        staff_members = staff_result.scalars().all()

        birthdays: List[Dict[str, Any]] = []
        anniversaries: List[Dict[str, Any]] = []

        for staff in staff_members:
            # Birthday check
            if staff.date_of_birth:
                if (
                    staff.date_of_birth.month == today.month
                    and staff.date_of_birth.day == today.day
                ):
                    birthdays.append(
                        {
                            "name": f"{staff.first_name} {staff.last_name}",
                            "user_id": staff.id,
                        }
                    )

            # Work anniversary check (year boundary of created_at)
            if staff.created_at:
                hire_date = staff.created_at.date()
                if (
                    hire_date.month == today.month
                    and hire_date.day == today.day
                    and hire_date.year < today.year
                ):
                    years = today.year - hire_date.year
                    anniversaries.append(
                        {
                            "name": f"{staff.first_name} {staff.last_name}",
                            "user_id": staff.id,
                            "years": years,
                        }
                    )

        dashboard.staff_birthdays = birthdays
        dashboard.staff_anniversaries = anniversaries

        total_celebrations = len(birthdays) + len(anniversaries)
        if total_celebrations > 0:
            parts = []
            if birthdays:
                parts.append(f"{len(birthdays)} birthday(s)")
            if anniversaries:
                parts.append(f"{len(anniversaries)} anniversary(ies)")
            dashboard.alerts.append(
                AlertItem(
                    category="staff",
                    severity="info",
                    description=f"Staff celebrations today: {', '.join(parts)}",
                    count=total_celebrations,
                )
            )

    @staticmethod
    async def _query_long_transit_items(
        db: AsyncSession,
        dashboard: MorningDashboard,
        now: datetime,
    ) -> None:
        cutoff = now - timedelta(days=7)
        result = await db.execute(
            select(func.count(TransitRequest.id)).where(
                and_(
                    TransitRequest.status == TransitStatus.IN_TRANSIT,
                    TransitRequest.shipped_at.isnot(None),
                    TransitRequest.shipped_at <= cutoff,
                )
            )
        )
        count = result.scalar() or 0
        dashboard.items_in_transit_long = count
        if count > 0:
            dashboard.alerts.append(
                AlertItem(
                    category="transit",
                    severity="warning",
                    description="Items in transit for 7+ days",
                    count=count,
                )
            )

    @staticmethod
    async def _query_overdue_buckets(
        db: AsyncSession,
        dashboard: MorningDashboard,
        now: datetime,
    ) -> None:
        buckets = {
            "1_day": (timedelta(days=0), timedelta(days=1)),
            "7_days": (timedelta(days=1), timedelta(days=7)),
            "14_days": (timedelta(days=7), timedelta(days=14)),
            "30_plus_days": (timedelta(days=30), None),
        }
        overdue_totals: Dict[str, int] = {}

        for label, (min_delta, max_delta) in buckets.items():
            upper_bound = now - min_delta
            conditions = [
                Checkout.status == CheckoutStatus.overdue,
                Checkout.due_date < upper_bound,
            ]
            if max_delta is not None:
                lower_bound = now - max_delta
                conditions.append(Checkout.due_date >= lower_bound)

            result = await db.execute(
                select(func.count(Checkout.id)).where(and_(*conditions))
            )
            count = result.scalar() or 0
            overdue_totals[label] = count

        dashboard.overdue_buckets = overdue_totals
        total_overdue = sum(overdue_totals.values())

        if total_overdue > 0:
            # 30+ day overdues are critical
            if overdue_totals.get("30_plus_days", 0) > 0:
                dashboard.alerts.append(
                    AlertItem(
                        category="overdues",
                        severity="critical",
                        description="Items overdue 30+ days",
                        count=overdue_totals["30_plus_days"],
                    )
                )
            # 14-day overdues are warnings
            if overdue_totals.get("14_days", 0) > 0:
                dashboard.alerts.append(
                    AlertItem(
                        category="overdues",
                        severity="warning",
                        description="Items overdue 7-14 days",
                        count=overdue_totals["14_days"],
                    )
                )
            # 7-day overdues are warnings
            if overdue_totals.get("7_days", 0) > 0:
                dashboard.alerts.append(
                    AlertItem(
                        category="overdues",
                        severity="warning",
                        description="Items overdue 1-7 days",
                        count=overdue_totals["7_days"],
                    )
                )
            # 1-day overdues are info
            if overdue_totals.get("1_day", 0) > 0:
                dashboard.alerts.append(
                    AlertItem(
                        category="overdues",
                        severity="info",
                        description="Items overdue since yesterday",
                        count=overdue_totals["1_day"],
                    )
                )

    # ------------------------------------------------------------------
    # Summary compiler
    # ------------------------------------------------------------------

    @staticmethod
    async def compile_alerts_summary(
        dashboard: MorningDashboard,
    ) -> Dict[str, Any]:
        by_severity: Dict[str, int] = {"critical": 0, "warning": 0, "info": 0}
        for alert in dashboard.alerts:
            by_severity[alert.severity] = (
                by_severity.get(alert.severity, 0) + alert.count
            )

        return {
            "alert_count": dashboard.total_alerts,
            "critical": by_severity["critical"],
            "warning": by_severity["warning"],
            "info": by_severity["info"],
            "items_due_today": dashboard.items_due_today,
            "holds_expiring_soon": dashboard.holds_expiring_soon,
            "new_patrons_today": dashboard.new_patrons_today,
            "events_today": dashboard.events_today,
            "staff_birthdays": len(dashboard.staff_birthdays),
            "staff_anniversaries": len(dashboard.staff_anniversaries),
            "items_in_transit_long": dashboard.items_in_transit_long,
            "overdue_buckets": dashboard.overdue_buckets,
        }

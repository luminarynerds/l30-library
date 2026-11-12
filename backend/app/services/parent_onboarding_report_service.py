# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from __future__ import annotations

import csv
import io
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta, timezone
from typing import Optional

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..core.config import get_settings
from ..models.parent_onboarding import (
    CareCoordinatorAssignment,
    CareCoordinatorCheckIn,
    HomeVisitStatus,
    ParentHomeVisit,
    ParentOnboardingSession,
    ParentOnboardingStatus,
    ServiceEnrollmentFacilitation,
    EnrollmentFacilitationStatus,
)
from ..models.parent_onboarding_export_log import ParentOnboardingExportLog
from ..models.user import User


SMALL_CELL_THRESHOLD = 5
WINDOW_DAYS = 7


@dataclass
class ActivityRow:

    row_date: date
    record_type: str  # "Session" | "Home visit" | "Check-in" | "Enrollment"
    patron_initials: str
    coordinator_name: str
    status: str
    outcome: str


@dataclass
class WeeklySummary:

    start_date: date
    end_date: date
    library_name: str
    coordinator_label: str
    generated_at: datetime

    # Aggregate counts
    sessions_held: int = 0
    sessions_cancelled: int = 0
    check_ins_logged: int = 0
    home_visits_completed: int = 0
    home_visits_cancelled: int = 0
    enrollments_facilitated: int = 0
    enrollments_denied: int = 0
    active_families_period_end: int = 0
    new_care_assignments: int = 0

    activity: list[ActivityRow] = field(default_factory=list)

    # True iff the coordinator-scoped report should redact small cells.
    small_cell_suppress: bool = False


def redact_initials(first_name: Optional[str], last_name: Optional[str]) -> str:
    fn = (first_name or "").strip()
    ln = (last_name or "").strip()
    if not fn and not ln:
        return "Unknown patron"
    fi = f"{fn[0].upper()}." if fn else "."
    li = f"{ln[0].upper()}." if ln else ""
    return f"{fi}{li}"


def _format_cell(value: int, suppress: bool) -> str:
    if suppress and 1 <= value <= SMALL_CELL_THRESHOLD:
        return f"<={SMALL_CELL_THRESHOLD}"
    return str(value)


def _coordinator_label(coordinator: Optional[User]) -> str:
    if coordinator is None:
        return "All coordinators"
    fn = (coordinator.first_name or "").strip()
    ln = (coordinator.last_name or "").strip()
    full = " ".join(p for p in (fn, ln) if p)
    return full or coordinator.email or f"Coordinator #{coordinator.id}"


def _coordinator_display_name(coordinator: Optional[User]) -> str:
    if coordinator is None:
        return "Unassigned"
    return _coordinator_label(coordinator)


def _patron_initials_from_user(user: Optional[User]) -> Optional[str]:
    if user is None:
        return None
    return redact_initials(user.first_name, user.last_name)


async def compute_weekly_summary(
    db: AsyncSession,
    end_date: date,
    coordinator: Optional[User] = None,
) -> WeeklySummary:
    start_date = end_date - timedelta(days=WINDOW_DAYS)
    # Use UTC midnight bounds; the route normalizes incoming date to a
    # library-tz day boundary in the caller. Mixed datetime/date columns
    # are handled per-query below.
    start_dt = datetime.combine(start_date, time.min, tzinfo=timezone.utc)
    end_dt = datetime.combine(end_date, time.min, tzinfo=timezone.utc)

    settings = get_settings()
    coordinator_label = _coordinator_label(coordinator)

    summary = WeeklySummary(
        start_date=start_date,
        end_date=end_date,
        library_name=settings.library_name,
        coordinator_label=coordinator_label,
        generated_at=datetime.now(timezone.utc),
    )

    coord_id = coordinator.id if coordinator else None

    # ------------------------------------------------------------------
    # Sessions: filter by completed_at within window (datetime column).
    # ------------------------------------------------------------------
    sess_q = select(ParentOnboardingSession).options(
        selectinload(ParentOnboardingSession.patron),
        selectinload(ParentOnboardingSession.staff),
    )
    sess_q = sess_q.where(
        and_(
            ParentOnboardingSession.completed_at.isnot(None),
            ParentOnboardingSession.completed_at >= start_dt,
            ParentOnboardingSession.completed_at < end_dt,
        )
    )
    if coord_id is not None:
        sess_q = sess_q.where(ParentOnboardingSession.staff_id == coord_id)
    sessions = (await db.execute(sess_q)).scalars().all()

    for s in sessions:
        if s.status == ParentOnboardingStatus.completed.value or s.status == "completed":
            summary.sessions_held += 1
        elif s.status in ("cancelled", "no_show"):
            summary.sessions_cancelled += 1
        # Build activity row only if a patron is attached
        initials = _patron_initials_from_user(s.patron)
        if initials is None:
            continue
        if s.completed_at is None:
            continue
        summary.activity.append(
            ActivityRow(
                row_date=s.completed_at.date(),
                record_type="Session",
                patron_initials=initials,
                coordinator_name=_coordinator_display_name(s.staff),
                status=s.status or "completed",
                outcome="",
            )
        )

    # ------------------------------------------------------------------
    # Check-ins: filter by scheduled_date (Date column). The completed
    # flag is implicit via completed_date; we count check-ins logged
    # in the window using the scheduled_date column to keep the window
    # boundary semantics consistent.
    # ------------------------------------------------------------------
    chk_q = (
        select(CareCoordinatorCheckIn)
        .options(
            selectinload(CareCoordinatorCheckIn.assignment).selectinload(
                CareCoordinatorAssignment.patron
            ),
            selectinload(CareCoordinatorCheckIn.assignment).selectinload(
                CareCoordinatorAssignment.coordinator
            ),
        )
        .where(
            and_(
                CareCoordinatorCheckIn.scheduled_date >= start_date,
                CareCoordinatorCheckIn.scheduled_date < end_date,
            )
        )
    )
    if coord_id is not None:
        chk_q = chk_q.join(CareCoordinatorAssignment).where(
            CareCoordinatorAssignment.coordinator_id == coord_id
        )
    check_ins = (await db.execute(chk_q)).scalars().all()
    summary.check_ins_logged = len(check_ins)
    for c in check_ins:
        assignment = c.assignment
        if assignment is None or assignment.patron is None:
            continue
        initials = _patron_initials_from_user(assignment.patron)
        if initials is None:
            continue
        summary.activity.append(
            ActivityRow(
                row_date=c.scheduled_date,
                record_type="Check-in",
                patron_initials=initials,
                coordinator_name=_coordinator_display_name(assignment.coordinator),
                status="completed" if c.completed_date is not None else "scheduled",
                outcome="",
            )
        )

    # ------------------------------------------------------------------
    # Home visits: filter by scheduled_date.
    # ------------------------------------------------------------------
    hv_q = (
        select(ParentHomeVisit)
        .options(
            selectinload(ParentHomeVisit.patron),
            selectinload(ParentHomeVisit.visitor),
        )
        .where(
            and_(
                ParentHomeVisit.scheduled_date >= start_date,
                ParentHomeVisit.scheduled_date < end_date,
            )
        )
    )
    if coord_id is not None:
        hv_q = hv_q.where(ParentHomeVisit.visitor_id == coord_id)
    home_visits = (await db.execute(hv_q)).scalars().all()
    for v in home_visits:
        if v.status == HomeVisitStatus.completed.value or v.status == "completed":
            summary.home_visits_completed += 1
        elif v.status in ("cancelled", "rescheduled", "no_show"):
            summary.home_visits_cancelled += 1
        initials = _patron_initials_from_user(v.patron)
        if initials is None:
            continue
        summary.activity.append(
            ActivityRow(
                row_date=v.scheduled_date,
                record_type="Home visit",
                patron_initials=initials,
                coordinator_name=_coordinator_display_name(v.visitor),
                status=v.status or "scheduled",
                outcome="",
            )
        )

    # ------------------------------------------------------------------
    # Enrollments: filter by enrollment_date (Date column).
    # Records with enrollment_date NULL are not counted in this window.
    # ------------------------------------------------------------------
    enr_q = (
        select(ServiceEnrollmentFacilitation)
        .options(
            selectinload(ServiceEnrollmentFacilitation.patron),
            selectinload(ServiceEnrollmentFacilitation.staff),
        )
        .where(
            and_(
                ServiceEnrollmentFacilitation.enrollment_date.isnot(None),
                ServiceEnrollmentFacilitation.enrollment_date >= start_date,
                ServiceEnrollmentFacilitation.enrollment_date < end_date,
            )
        )
    )
    if coord_id is not None:
        enr_q = enr_q.where(ServiceEnrollmentFacilitation.staff_id == coord_id)
    enrollments = (await db.execute(enr_q)).scalars().all()
    for e in enrollments:
        if e.status == EnrollmentFacilitationStatus.enrolled.value or e.status == "enrolled":
            summary.enrollments_facilitated += 1
        elif e.status == EnrollmentFacilitationStatus.denied.value or e.status == "denied":
            summary.enrollments_denied += 1
        initials = _patron_initials_from_user(e.patron)
        if initials is None:
            continue
        summary.activity.append(
            ActivityRow(
                row_date=e.enrollment_date,
                record_type="Enrollment",
                patron_initials=initials,
                coordinator_name=_coordinator_display_name(e.staff),
                status=e.status or "enrolled",
                outcome="",
            )
        )

    # ------------------------------------------------------------------
    # Active families at period end + new assignments in window.
    # ------------------------------------------------------------------
    afp_q = select(func.count(func.distinct(CareCoordinatorAssignment.patron_id))).where(
        and_(
            CareCoordinatorAssignment.status == "active",
            CareCoordinatorAssignment.start_date < end_date,
        )
    )
    if coord_id is not None:
        afp_q = afp_q.where(CareCoordinatorAssignment.coordinator_id == coord_id)
    summary.active_families_period_end = (await db.execute(afp_q)).scalar() or 0

    new_q = select(func.count(CareCoordinatorAssignment.id)).where(
        and_(
            CareCoordinatorAssignment.start_date >= start_date,
            CareCoordinatorAssignment.start_date < end_date,
        )
    )
    if coord_id is not None:
        new_q = new_q.where(CareCoordinatorAssignment.coordinator_id == coord_id)
    summary.new_care_assignments = (await db.execute(new_q)).scalar() or 0

    # ------------------------------------------------------------------
    # Sort activity by date, then by record-type ordering. NOT by patron.
    # ------------------------------------------------------------------
    type_order = {"Session": 0, "Home visit": 1, "Check-in": 2, "Enrollment": 3}
    summary.activity.sort(
        key=lambda r: (r.row_date, type_order.get(r.record_type, 99))
    )

    # ------------------------------------------------------------------
    # Small-cell suppression decision: coordinator-scoped AND
    # the coordinator has < 5 distinct patrons in the window's activity.
    # ------------------------------------------------------------------
    if coord_id is not None:
        distinct_patrons = {r.patron_initials for r in summary.activity}
        summary.small_cell_suppress = len(distinct_patrons) < SMALL_CELL_THRESHOLD

    return summary


def render_csv(summary: WeeklySummary) -> str:
    suppress = summary.small_cell_suppress
    out = io.StringIO()
    writer = csv.writer(out)

    # Header section
    writer.writerow(["Parent Onboarding - Weekly Summary"])
    writer.writerow(
        ["Date range", f"{summary.start_date.isoformat()} to {summary.end_date.isoformat()}"]
    )
    writer.writerow(["Library", summary.library_name])
    writer.writerow(["Coordinator", summary.coordinator_label])
    writer.writerow(
        ["Generated", summary.generated_at.strftime("%Y-%m-%dT%H:%M:%SZ")]
    )
    writer.writerow([])

    # Aggregate counts
    writer.writerow(["Aggregate counts"])
    writer.writerow(["Sessions held", _format_cell(summary.sessions_held, suppress)])
    writer.writerow(
        [
            "Sessions cancelled or no-show",
            _format_cell(summary.sessions_cancelled, suppress),
        ]
    )
    writer.writerow(
        ["Care check-ins logged", _format_cell(summary.check_ins_logged, suppress)]
    )
    writer.writerow(
        [
            "Home visits completed",
            _format_cell(summary.home_visits_completed, suppress),
        ]
    )
    writer.writerow(
        [
            "Home visits cancelled or rescheduled",
            _format_cell(summary.home_visits_cancelled, suppress),
        ]
    )
    writer.writerow(
        [
            "Service enrollments facilitated",
            _format_cell(summary.enrollments_facilitated, suppress),
        ]
    )
    writer.writerow(
        [
            "Service enrollments denied",
            _format_cell(summary.enrollments_denied, suppress),
        ]
    )
    writer.writerow(
        [
            "Active families (period end)",
            _format_cell(summary.active_families_period_end, suppress),
        ]
    )
    writer.writerow(
        ["New care assignments", _format_cell(summary.new_care_assignments, suppress)]
    )
    writer.writerow([])

    # Activity log
    writer.writerow(["Activity log (anonymized)"])
    writer.writerow(
        ["Date", "Type", "Patron (initials)", "Coordinator", "Status", "Outcome"]
    )
    for r in summary.activity:
        writer.writerow(
            [
                r.row_date.isoformat(),
                r.record_type,
                r.patron_initials,
                r.coordinator_name,
                r.status,
                r.outcome,
            ]
        )

    return out.getvalue()


def filename_for(summary: WeeklySummary, fmt: str) -> str:
    return f"parent-onboarding-weekly-{summary.end_date.isoformat()}.{fmt}"


async def write_export_audit_log(
    db: AsyncSession,
    *,
    user_id: int,
    fmt: str,
    start_date: date,
    end_date: date,
    coordinator_id: Optional[int],
    row_count: int,
) -> None:
    db.add(
        ParentOnboardingExportLog(
            exported_by_id=user_id,
            format=fmt,
            start_date=start_date,
            end_date=end_date,
            coordinator_id=coordinator_id,
            row_count=row_count,
        )
    )
    await db.commit()

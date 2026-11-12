# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Parent-onboarding dashboard service."""
from datetime import date, datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ...models.parent_onboarding import (
    CareAssignmentStatus, CareCoordinatorAssignment, ChildcareSession,
    ChildcareSessionStatus, EnrollmentFacilitationStatus,
    HomeVisitStatus, ParentConnectionGroup, ParentHomeVisit,
    ParentOnboardingSession, ParentOnboardingStatus,
    ServiceEnrollmentFacilitation,
)
from ...models.user import User
from .sessions import CareCoordinatorService


class ParentOnboardingDashboardService:

    @staticmethod
    async def get_dashboard(db: AsyncSession) -> dict:
        today = date.today()

        active_families = (await db.execute(
            select(func.count(CareCoordinatorAssignment.id))
            .where(CareCoordinatorAssignment.status == CareAssignmentStatus.active)
        )).scalar() or 0

        upcoming_sessions = (await db.execute(
            select(func.count(ParentOnboardingSession.id))
            .where(
                ParentOnboardingSession.status == ParentOnboardingStatus.scheduled,
                ParentOnboardingSession.scheduled_at >= datetime.now(timezone.utc),
            )
        )).scalar() or 0

        overdue_check_ins = len(await CareCoordinatorService.get_overdue_check_ins(db))

        active_childcare = (await db.execute(
            select(func.count(ChildcareSession.id))
            .where(
                ChildcareSession.status.in_([
                    ChildcareSessionStatus.available,
                    ChildcareSessionStatus.in_progress,
                ]),
                ChildcareSession.date >= today,
            )
        )).scalar() or 0

        active_groups = (await db.execute(
            select(func.count(ParentConnectionGroup.id))
            .where(ParentConnectionGroup.is_active.is_(True))
        )).scalar() or 0

        pending_enrollments = (await db.execute(
            select(func.count(ServiceEnrollmentFacilitation.id))
            .where(ServiceEnrollmentFacilitation.status.in_([
                EnrollmentFacilitationStatus.identified,
                EnrollmentFacilitationStatus.contacted,
                EnrollmentFacilitationStatus.application_started,
                EnrollmentFacilitationStatus.application_submitted,
            ]))
        )).scalar() or 0

        upcoming_visits_count = (await db.execute(
            select(func.count(ParentHomeVisit.id))
            .where(
                ParentHomeVisit.status.in_([HomeVisitStatus.scheduled, HomeVisitStatus.confirmed]),
                ParentHomeVisit.scheduled_date >= today,
            )
        )).scalar() or 0

        recent_session_rows = (await db.execute(
            select(ParentOnboardingSession)
            .options(selectinload(ParentOnboardingSession.patron))
            .order_by(ParentOnboardingSession.scheduled_at.desc())
            .limit(5)
        )).scalars().all()

        recent_sessions = [
            {
                "id": s.id,
                "patron_id": s.patron_id,
                "patron_name": f"{s.patron.first_name} {s.patron.last_name}".strip() if s.patron else None,
                "staff_id": s.staff_id,
                "scheduled_date": s.scheduled_at,
                "status": s.status,
            }
            for s in recent_session_rows
        ]

        overdue_assignment_rows = (await db.execute(
            select(CareCoordinatorAssignment)
            .options(
                selectinload(CareCoordinatorAssignment.patron),
                selectinload(CareCoordinatorAssignment.check_ins),
            )
            .where(CareCoordinatorAssignment.status == CareAssignmentStatus.active)
        )).scalars().all()

        overdue_assignments: list[dict] = []
        for a in overdue_assignment_rows:
            last_ci = max(a.check_ins, key=lambda c: c.scheduled_date) if a.check_ins else None
            is_overdue = (not a.check_ins) or (
                last_ci is not None
                and last_ci.next_check_in_date is not None
                and last_ci.next_check_in_date < today
            )
            if not is_overdue:
                continue
            overdue_assignments.append({
                "id": a.id,
                "patron_id": a.patron_id,
                "patron_name": f"{a.patron.first_name} {a.patron.last_name}".strip() if a.patron else None,
                "coordinator_id": a.coordinator_id,
                "next_check_in_due": last_ci.next_check_in_date if last_ci else None,
                "risk_level": a.risk_level,
            })

        upcoming_visit_rows = (await db.execute(
            select(ParentHomeVisit)
            .options(
                selectinload(ParentHomeVisit.patron),
                selectinload(ParentHomeVisit.visitor),
            )
            .where(
                ParentHomeVisit.status.in_([HomeVisitStatus.scheduled, HomeVisitStatus.confirmed]),
                ParentHomeVisit.scheduled_date >= today,
            )
            .order_by(ParentHomeVisit.scheduled_date.asc())
            .limit(10)
        )).scalars().all()

        upcoming_visits = [
            {
                "id": v.id,
                "patron_id": v.patron_id,
                "patron_name": f"{v.patron.first_name} {v.patron.last_name}".strip() if v.patron else None,
                "visitor_id": v.visitor_id,
                "visitor_name": f"{v.visitor.first_name} {v.visitor.last_name}".strip() if v.visitor else None,
                "scheduled_date": v.scheduled_date,
                "scheduled_time": v.scheduled_time,
                "purpose": v.purpose,
                "status": v.status,
            }
            for v in upcoming_visit_rows
        ]

        return {
            "active_families": active_families,
            "upcoming_sessions": upcoming_sessions,
            "overdue_check_ins": len(overdue_assignments),
            "active_childcare_sessions": active_childcare,
            "active_connection_groups": active_groups,
            "pending_enrollments": pending_enrollments,
            "upcoming_home_visits": upcoming_visits_count,
            "recent_sessions": recent_sessions,
            "overdue_assignments": overdue_assignments,
            "upcoming_visits": upcoming_visits,
        }

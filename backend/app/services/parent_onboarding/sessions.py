# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
from app.core.logging import get_logger
from datetime import date, datetime, timezone
from typing import Optional

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ...core.pii_audit import log_pii_access
from ...models.parent_onboarding import (
    CareAssignmentStatus, CareCoordinatorAssignment, CareCoordinatorCheckIn,
    ChildcareRegistration, ChildcareRegistrationStatus, ChildcareSession,
    ChildcareSessionStatus, EnrollmentFacilitationStatus, GroupMemberStatus,
    HomeVisitStatus, HomeVisitStatusHistory, MeetingFrequency,
    ParentConnectionGroup, ParentConnectionGroupMeeting,
    ParentConnectionGroupMember, ParentHomeVisit, ParentOnboardingSession,
    ParentOnboardingStatus, ServiceEnrollmentFacilitation,
)
from ...models.user import User

logger = get_logger(__name__)



class ParentOnboardingSessionService:

    @staticmethod
    async def create_session(
        db: AsyncSession, data: dict
    ) -> ParentOnboardingSession:
        session = ParentOnboardingSession(**data)
        db.add(session)
        await db.flush()
        await db.refresh(session)
        logger.info("Created parent onboarding session %s for patron %s", session.id, data.get("patron_id"))
        return session

    @staticmethod
    async def get_session(db: AsyncSession, session_id: int) -> Optional[ParentOnboardingSession]:
        result = await db.execute(
            select(ParentOnboardingSession)
            .where(ParentOnboardingSession.id == session_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def list_sessions(
        db: AsyncSession,
        *,
        status: Optional[ParentOnboardingStatus] = None,
        branch_id: Optional[int] = None,
        staff_id: Optional[int] = None,
        patron_id: Optional[int] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[ParentOnboardingSession], int]:
        query = select(ParentOnboardingSession)
        count_query = select(func.count(ParentOnboardingSession.id))

        if status:
            query = query.where(ParentOnboardingSession.status == status)
            count_query = count_query.where(ParentOnboardingSession.status == status)
        if branch_id:
            query = query.where(ParentOnboardingSession.branch_id == branch_id)
            count_query = count_query.where(ParentOnboardingSession.branch_id == branch_id)
        if staff_id:
            query = query.where(ParentOnboardingSession.staff_id == staff_id)
            count_query = count_query.where(ParentOnboardingSession.staff_id == staff_id)
        if patron_id:
            query = query.where(ParentOnboardingSession.patron_id == patron_id)
            count_query = count_query.where(ParentOnboardingSession.patron_id == patron_id)

        total = (await db.execute(count_query)).scalar() or 0
        query = query.order_by(ParentOnboardingSession.scheduled_at.desc()).limit(limit).offset(offset)
        result = await db.execute(query)
        return list(result.scalars().all()), total

    @staticmethod
    async def complete_session(
        db: AsyncSession, session: ParentOnboardingSession, data: dict
    ) -> ParentOnboardingSession:
        session.status = ParentOnboardingStatus.completed
        session.completed_at = datetime.now(timezone.utc)
        for key, value in data.items():
            if hasattr(session, key):
                setattr(session, key, value)
        await db.flush()
        await db.refresh(session)
        logger.info("Completed parent onboarding session %s", session.id)
        return session


class CareCoordinatorService:

    @staticmethod
    async def create_assignment(
        db: AsyncSession, data: dict
    ) -> CareCoordinatorAssignment:
        assignment = CareCoordinatorAssignment(**data)
        db.add(assignment)
        await db.flush()
        await db.refresh(assignment)
        logger.info("Created care assignment %s for patron %s", assignment.id, data.get("patron_id"))
        return assignment

    @staticmethod
    async def get_assignment(db: AsyncSession, assignment_id: int) -> Optional[CareCoordinatorAssignment]:
        result = await db.execute(
            select(CareCoordinatorAssignment)
            .options(selectinload(CareCoordinatorAssignment.check_ins))
            .where(CareCoordinatorAssignment.id == assignment_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def list_assignments(
        db: AsyncSession,
        *,
        status: Optional[CareAssignmentStatus] = None,
        coordinator_id: Optional[int] = None,
        patron_id: Optional[int] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[CareCoordinatorAssignment], int]:
        query = select(CareCoordinatorAssignment)
        count_query = select(func.count(CareCoordinatorAssignment.id))

        if status:
            query = query.where(CareCoordinatorAssignment.status == status)
            count_query = count_query.where(CareCoordinatorAssignment.status == status)
        if coordinator_id:
            query = query.where(CareCoordinatorAssignment.coordinator_id == coordinator_id)
            count_query = count_query.where(CareCoordinatorAssignment.coordinator_id == coordinator_id)
        if patron_id:
            query = query.where(CareCoordinatorAssignment.patron_id == patron_id)
            count_query = count_query.where(CareCoordinatorAssignment.patron_id == patron_id)

        total = (await db.execute(count_query)).scalar() or 0
        query = query.order_by(CareCoordinatorAssignment.created_at.desc()).limit(limit).offset(offset)
        result = await db.execute(query)
        return list(result.scalars().all()), total

    @staticmethod
    async def create_check_in(
        db: AsyncSession, assignment_id: int, data: dict
    ) -> CareCoordinatorCheckIn:
        check_in = CareCoordinatorCheckIn(assignment_id=assignment_id, **data)
        db.add(check_in)
        await db.flush()
        await db.refresh(check_in)
        logger.info("Created check-in %s for assignment %s", check_in.id, assignment_id)
        return check_in

    @staticmethod
    async def get_overdue_check_ins(
        db: AsyncSession,
    ) -> list[CareCoordinatorAssignment]:
        today = date.today()
        result = await db.execute(
            select(CareCoordinatorAssignment)
            .where(
                CareCoordinatorAssignment.status == CareAssignmentStatus.active,
            )
            .options(selectinload(CareCoordinatorAssignment.check_ins))
        )
        assignments = result.scalars().all()

        overdue = []
        for assignment in assignments:
            if not assignment.check_ins:
                overdue.append(assignment)
                continue
            last_check_in = max(assignment.check_ins, key=lambda c: c.scheduled_date)
            if last_check_in.next_check_in_date and last_check_in.next_check_in_date < today:
                overdue.append(assignment)

        return overdue



# ServiceEnrollmentService moved to service_enrollments.py


# ResourceGuideService moved to resource_guide.py


# ParentOnboardingDashboardService moved to reports.py

# ============================================================================
# Component 8: Session follow-ups + referrals
# ============================================================================
#
# Service classes for the first-class follow-up and referral records.
#
# Conventions in this module (consistent with the older services above):
#   - Static methods on a per-noun service class.
#   - Callers commit; services flush + refresh.
#   - List endpoints return (rows, total) so the route can shape pagination.
#   - All session-scoped lookups go through the noun service, not the
#     ParentOnboardingSessionService, so the surface stays cohesive.

from ...models.parent_onboarding import (  # noqa: E402  (extends the imports above)
    FollowupStatus, ParentOnboardingFollowup, ParentOnboardingReferral,
    PartnerAgency,
)
from ...models.user import User  # noqa: E402


# PartnerAgencyService moved to service_enrollments.py


class FollowupService:

    @staticmethod
    async def list_for_session(
        db: AsyncSession, session_id: int,
    ) -> tuple[list[ParentOnboardingFollowup], int]:
        # selectinload the assignee so response composition doesn't trigger
        # MissingGreenlet on .assignee.first_name access (see
        # feedback_l30_async_property_landmine). The N here is bounded by
        # follow-ups-per-session (low cardinality), so eager-loading is cheap.
        query = (
            select(ParentOnboardingFollowup)
            .where(ParentOnboardingFollowup.session_id == session_id)
            .options(selectinload(ParentOnboardingFollowup.assignee))
            .order_by(ParentOnboardingFollowup.due_date.asc())
        )
        rows = list((await db.execute(query)).scalars().all())
        return rows, len(rows)

    @staticmethod
    async def get(
        db: AsyncSession, followup_id: int,
    ) -> Optional[ParentOnboardingFollowup]:
        result = await db.execute(
            select(ParentOnboardingFollowup)
            .where(ParentOnboardingFollowup.id == followup_id)
            .options(selectinload(ParentOnboardingFollowup.assignee))
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def create(
        db: AsyncSession,
        *,
        session_id: int,
        data: dict,
        created_by_id: Optional[int] = None,
    ) -> ParentOnboardingFollowup:
        followup = ParentOnboardingFollowup(
            session_id=session_id,
            created_by_id=created_by_id,
            **data,
        )
        db.add(followup)
        await db.flush()
        await db.refresh(followup)
        return followup

    @staticmethod
    async def update(
        db: AsyncSession,
        followup: ParentOnboardingFollowup,
        data: dict,
    ) -> ParentOnboardingFollowup:
        for key, value in data.items():
            if hasattr(followup, key):
                setattr(followup, key, value)
        await db.flush()
        await db.refresh(followup)
        return followup

    @staticmethod
    async def complete(
        db: AsyncSession,
        followup: ParentOnboardingFollowup,
        *,
        completed_by: User,
        completion_note: Optional[str] = None,
    ) -> ParentOnboardingFollowup:
        # Idempotent: re-completing a follow-up just updates the note +
        # timestamp. The status moves to "completed" regardless of prior
        # state so an "in_progress -> completed" transition works.
        followup.status = FollowupStatus.completed.value
        followup.completed_at = datetime.now(timezone.utc)
        followup.completed_by_id = completed_by.id
        if completion_note is not None:
            followup.completion_note = completion_note
        await db.flush()
        await db.refresh(followup)
        return followup

    @staticmethod
    async def delete(
        db: AsyncSession, followup: ParentOnboardingFollowup,
    ) -> None:
        await db.delete(followup)
        await db.flush()

    @staticmethod
    async def list_due_on(
        db: AsyncSession, target_date: date,
    ) -> list[ParentOnboardingFollowup]:
        query = (
            select(ParentOnboardingFollowup)
            .where(
                ParentOnboardingFollowup.due_date == target_date,
                ParentOnboardingFollowup.status.in_(
                    [FollowupStatus.open.value, FollowupStatus.in_progress.value]
                ),
                ParentOnboardingFollowup.assignee_id.isnot(None),
            )
            .options(
                selectinload(ParentOnboardingFollowup.assignee),
                selectinload(ParentOnboardingFollowup.session),
            )
            .order_by(ParentOnboardingFollowup.assignee_id)
        )
        return list((await db.execute(query)).scalars().all())


class ReferralService:

    @staticmethod
    async def list_for_session(
        db: AsyncSession, session_id: int,
    ) -> tuple[list[ParentOnboardingReferral], int]:
        query = (
            select(ParentOnboardingReferral)
            .where(ParentOnboardingReferral.session_id == session_id)
            .options(selectinload(ParentOnboardingReferral.partner_agency))
            .order_by(ParentOnboardingReferral.made_at.desc())
        )
        rows = list((await db.execute(query)).scalars().all())
        return rows, len(rows)

    @staticmethod
    async def get(
        db: AsyncSession, referral_id: int,
    ) -> Optional[ParentOnboardingReferral]:
        result = await db.execute(
            select(ParentOnboardingReferral)
            .where(ParentOnboardingReferral.id == referral_id)
            .options(selectinload(ParentOnboardingReferral.partner_agency))
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def create(
        db: AsyncSession,
        *,
        session_id: int,
        data: dict,
        made_by_id: Optional[int] = None,
    ) -> ParentOnboardingReferral:
        referral = ParentOnboardingReferral(
            session_id=session_id,
            made_by_id=made_by_id,
            **data,
        )
        db.add(referral)
        await db.flush()
        # Re-fetch with eager-loaded partner agency so the response
        # composition can read agency.name without triggering a lazy load.
        return await ReferralService.get(db, referral.id) or referral

    @staticmethod
    async def update(
        db: AsyncSession,
        referral: ParentOnboardingReferral,
        data: dict,
    ) -> ParentOnboardingReferral:
        for key, value in data.items():
            if hasattr(referral, key):
                setattr(referral, key, value)
        await db.flush()
        await db.refresh(referral)
        return referral

    @staticmethod
    async def delete(
        db: AsyncSession, referral: ParentOnboardingReferral,
    ) -> None:
        await db.delete(referral)
        await db.flush()


# ----------------------------------------------------------------------------
# Component 9: Session resource handouts (catalog + per-session assignments)
# ----------------------------------------------------------------------------
#
# Two services, kept independent so the catalog one can be reused by other
# session-style features (home-visits will want the same picker eventually).

from ...models.parent_onboarding import (  # noqa: E402
    ParentOnboardingSessionHandout, ResourceHandout,
)


class ResourceHandoutService:

    @staticmethod
    async def list_catalog(
        db: AsyncSession,
        *,
        language: Optional[str] = None,
        category: Optional[str] = None,
        search: Optional[str] = None,
        is_active: bool = True,
        limit: int = 25,
        offset: int = 0,
    ) -> tuple[list[ResourceHandout], int]:
        base = select(ResourceHandout)
        if is_active:
            base = base.where(ResourceHandout.is_active.is_(True))
        if language:
            base = base.where(ResourceHandout.language == language)
        if category:
            base = base.where(ResourceHandout.category == category)
        if search:
            # Match title prefix + description fragment + tag membership.
            # ILIKE is fine here; the catalog is small (<100 rows expected
            # for v1) and a trigram index is over-engineering.
            pattern = f"%{search.strip()}%"
            base = base.where(
                (ResourceHandout.title.ilike(pattern))
                | (ResourceHandout.description.ilike(pattern))
            )

        # Count BEFORE pagination so the FE can render "(47)".
        count_q = select(func.count()).select_from(base.subquery())
        total = (await db.execute(count_q)).scalar_one()

        rows_q = (
            base.order_by(ResourceHandout.title.asc())
            .limit(limit)
            .offset(offset)
        )
        rows = list((await db.execute(rows_q)).scalars().all())
        return rows, total

    @staticmethod
    async def get(
        db: AsyncSession, handout_id: int,
    ) -> Optional[ResourceHandout]:
        result = await db.execute(
            select(ResourceHandout).where(ResourceHandout.id == handout_id)
        )
        return result.scalar_one_or_none()


class SessionHandoutService:

    @staticmethod
    async def list_for_session(
        db: AsyncSession, session_id: int,
    ) -> tuple[list[ParentOnboardingSessionHandout], int]:
        query = (
            select(ParentOnboardingSessionHandout)
            .where(
                ParentOnboardingSessionHandout.session_id == session_id,
            )
            .options(
                selectinload(
                    ParentOnboardingSessionHandout.resource_handout,
                ),
                selectinload(
                    ParentOnboardingSessionHandout.community_resource_link,
                ),
                selectinload(
                    ParentOnboardingSessionHandout.given_by,
                ),
            )
            .order_by(ParentOnboardingSessionHandout.given_at.asc())
        )
        rows = list((await db.execute(query)).scalars().all())
        return rows, len(rows)

    @staticmethod
    async def get(
        db: AsyncSession, assignment_id: int,
    ) -> Optional[ParentOnboardingSessionHandout]:
        result = await db.execute(
            select(ParentOnboardingSessionHandout)
            .where(
                ParentOnboardingSessionHandout.id == assignment_id,
            )
            .options(
                selectinload(
                    ParentOnboardingSessionHandout.resource_handout,
                ),
                selectinload(
                    ParentOnboardingSessionHandout.community_resource_link,
                ),
                selectinload(
                    ParentOnboardingSessionHandout.given_by,
                ),
            )
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def create(
        db: AsyncSession,
        *,
        session_id: int,
        data: dict,
        given_by_id: Optional[int] = None,
    ) -> ParentOnboardingSessionHandout:
        # Drop given_at when None so the server_default (now()) applies
        # rather than landing a NULL.
        clean = dict(data)
        if clean.get("given_at") is None:
            clean.pop("given_at", None)

        assignment = ParentOnboardingSessionHandout(
            session_id=session_id,
            given_by_id=given_by_id,
            **clean,
        )
        db.add(assignment)
        await db.flush()
        # Re-fetch with relationships loaded so the response composer
        # never triggers a lazy load.
        return await SessionHandoutService.get(db, assignment.id) or assignment

    @staticmethod
    async def delete(
        db: AsyncSession, assignment: ParentOnboardingSessionHandout,
    ) -> None:
        await db.delete(assignment)
        await db.flush()

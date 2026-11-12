# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Home-visit service classes for the parent-onboarding subdomain.

Extracted from services/parent_onboarding/_legacy.py (pure move, no logic changes).
"""
from app.core.logging import get_logger
from datetime import date, datetime, timezone
from typing import Optional

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ...core.pii_audit import log_pii_access
from ...models.parent_onboarding import (
    HomeVisitStatus, HomeVisitStatusHistory,
    ParentHomeVisit,
)
from ...models.user import User

logger = get_logger(__name__)


# Valid status transitions; anything not in this map raises HTTP 409.
# Keep terminal states (completed/cancelled/rescheduled) as no-out edges so
# accidental re-mutation fails loudly rather than silently rewriting history.
_HOME_VISIT_TRANSITIONS: dict[HomeVisitStatus, set[HomeVisitStatus]] = {
    HomeVisitStatus.scheduled: {
        HomeVisitStatus.confirmed,
        HomeVisitStatus.completed,
        HomeVisitStatus.cancelled,
        HomeVisitStatus.rescheduled,
    },
    HomeVisitStatus.confirmed: {
        HomeVisitStatus.completed,
        HomeVisitStatus.cancelled,
        HomeVisitStatus.rescheduled,
    },
    HomeVisitStatus.completed: set(),
    HomeVisitStatus.cancelled: set(),
    HomeVisitStatus.rescheduled: set(),
}


class InvalidHomeVisitTransitionError(Exception):

    def __init__(self, from_status: HomeVisitStatus, to_status: HomeVisitStatus) -> None:
        self.from_status = from_status
        self.to_status = to_status
        super().__init__(
            f"Invalid home visit transition: {from_status} -> {to_status}"
        )


class HomeVisitService:

    @staticmethod
    async def create_visit(
        db: AsyncSession, data: dict
    ) -> ParentHomeVisit:
        visit = ParentHomeVisit(**data)
        db.add(visit)
        await db.flush()
        await db.refresh(visit)
        logger.info("Created home visit %s for patron %s", visit.id, data.get("patron_id"))
        return visit

    @staticmethod
    async def get_visit(db: AsyncSession, visit_id: int) -> Optional[ParentHomeVisit]:
        result = await db.execute(
            select(ParentHomeVisit).where(ParentHomeVisit.id == visit_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def list_visits(
        db: AsyncSession,
        *,
        patron_id: Optional[int] = None,
        visitor_id: Optional[int] = None,
        status: Optional[HomeVisitStatus] = None,
        from_date: Optional[date] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[ParentHomeVisit], int]:
        query = select(ParentHomeVisit)
        count_query = select(func.count(ParentHomeVisit.id))

        if patron_id:
            query = query.where(ParentHomeVisit.patron_id == patron_id)
            count_query = count_query.where(ParentHomeVisit.patron_id == patron_id)
        if visitor_id:
            query = query.where(ParentHomeVisit.visitor_id == visitor_id)
            count_query = count_query.where(ParentHomeVisit.visitor_id == visitor_id)
        if status:
            query = query.where(ParentHomeVisit.status == status)
            count_query = count_query.where(ParentHomeVisit.status == status)
        if from_date:
            query = query.where(ParentHomeVisit.scheduled_date >= from_date)
            count_query = count_query.where(ParentHomeVisit.scheduled_date >= from_date)

        total = (await db.execute(count_query)).scalar() or 0
        query = query.order_by(ParentHomeVisit.scheduled_date.desc()).limit(limit).offset(offset)
        result = await db.execute(query)
        return list(result.scalars().all()), total

    @staticmethod
    async def complete_visit(
        db: AsyncSession, visit: ParentHomeVisit, data: dict
    ) -> ParentHomeVisit:
        visit.status = HomeVisitStatus.completed
        visit.actual_end = datetime.now(timezone.utc)
        for key, value in data.items():
            if hasattr(visit, key):
                setattr(visit, key, value)
        await db.flush()
        await db.refresh(visit)
        logger.info("Completed home visit %s", visit.id)
        return visit

    # ------------------------------------------------------------------
    # Status-mutation methods (home_visit_mutations_001)
    #
    # All four methods share the same shape:
    #   1. enforce a valid transition (raise InvalidHomeVisitTransitionError)
    #   2. update the visit row in place
    #   3. write a HomeVisitStatusHistory row
    #   4. write a pii_access_log row tagged HOME_VISIT_STATUS_CHANGE
    #
    # The caller's session is flushed but NOT committed -- the router owns
    # the transaction boundary so that any failure rolls back the entire
    # mutation (visit + history + audit).
    # ------------------------------------------------------------------

    @staticmethod
    async def _record_transition(
        db: AsyncSession,
        *,
        visit: ParentHomeVisit,
        from_status: HomeVisitStatus,
        to_status: HomeVisitStatus,
        changed_by: User,
        reason: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> HomeVisitStatusHistory:
        history = HomeVisitStatusHistory(
            visit_id=visit.id,
            from_status=from_status.value if isinstance(from_status, HomeVisitStatus) else from_status,
            to_status=to_status.value if isinstance(to_status, HomeVisitStatus) else to_status,
            changed_by_id=changed_by.id,
            reason=reason,
            metadata_json=metadata,
        )
        db.add(history)
        await db.flush()

        # Audit log -- home visits touch addresses + family composition, so
        # every status change against a patron's visit is a PII surface
        # event even when the staff didn't open the address pane.
        try:
            await log_pii_access(
                db=db,
                user_id=changed_by.id,
                user_role=changed_by.role,
                endpoint="HOME_VISIT_STATUS_CHANGE",
                fields_accessed=["status"],
                fields_redacted=[],
                patron_ids_accessed=[visit.patron_id],
                additional_context={
                    "visit_id": visit.id,
                    "from_status": history.from_status,
                    "to_status": history.to_status,
                    "history_id": history.id,
                },
            )
        except Exception as exc:  # noqa: BLE001
            # PII audit failure should not block the mutation -- the
            # business action is more important than the audit row.
            # Sentry will pick this up via the logger handler.
            logger.warning(
                "pii_access_log write failed during home_visit status change: %s",
                exc,
            )

        return history

    @staticmethod
    async def confirm_visit(
        db: AsyncSession,
        visit: ParentHomeVisit,
        *,
        changed_by: User,
        reason: Optional[str] = None,
    ) -> ParentHomeVisit:
        current = HomeVisitStatus(visit.status)
        target = HomeVisitStatus.confirmed
        if target not in _HOME_VISIT_TRANSITIONS.get(current, set()):
            raise InvalidHomeVisitTransitionError(current, target)
        visit.status = target.value
        await db.flush()

        await HomeVisitService._record_transition(
            db,
            visit=visit,
            from_status=current,
            to_status=target,
            changed_by=changed_by,
            reason=reason,
        )
        logger.info("Confirmed home visit %s by user %s", visit.id, changed_by.id)
        return visit

    @staticmethod
    async def mark_complete(
        db: AsyncSession,
        visit: ParentHomeVisit,
        *,
        changed_by: User,
        outcomes: str,
        resources_delivered: list[str],
        follow_up_needed: bool = False,
        follow_up_date: Optional[date] = None,
        follow_up_notes: Optional[str] = None,
        referrals: Optional[list[str]] = None,
    ) -> ParentHomeVisit:
        current = HomeVisitStatus(visit.status)
        target = HomeVisitStatus.completed
        if target not in _HOME_VISIT_TRANSITIONS.get(current, set()):
            raise InvalidHomeVisitTransitionError(current, target)

        visit.status = target.value
        visit.actual_end = datetime.now(timezone.utc)
        visit.outcomes = outcomes
        visit.resources_delivered = list(resources_delivered or [])
        visit.follow_up_needed = bool(follow_up_needed)
        if follow_up_needed:
            visit.follow_up_date = follow_up_date
        else:
            visit.follow_up_date = None
        # Follow-up notes + referrals don't have dedicated columns yet; they
        # live in history metadata so audit can still reconstruct them.
        await db.flush()

        await HomeVisitService._record_transition(
            db,
            visit=visit,
            from_status=current,
            to_status=target,
            changed_by=changed_by,
            metadata={
                "outcomes": outcomes,
                "resources_delivered": list(resources_delivered or []),
                "follow_up_needed": bool(follow_up_needed),
                "follow_up_date": follow_up_date.isoformat() if follow_up_date else None,
                "follow_up_notes": follow_up_notes,
                "referrals": list(referrals or []),
            },
        )
        logger.info("Completed home visit %s by user %s", visit.id, changed_by.id)
        return visit

    @staticmethod
    async def cancel_visit(
        db: AsyncSession,
        visit: ParentHomeVisit,
        *,
        changed_by: User,
        cancelled_reason: str,
        notify_acknowledged: bool = False,
    ) -> ParentHomeVisit:
        current = HomeVisitStatus(visit.status)
        target = HomeVisitStatus.cancelled
        if target not in _HOME_VISIT_TRANSITIONS.get(current, set()):
            raise InvalidHomeVisitTransitionError(current, target)
        visit.status = target.value
        visit.cancelled_reason = cancelled_reason
        await db.flush()

        await HomeVisitService._record_transition(
            db,
            visit=visit,
            from_status=current,
            to_status=target,
            changed_by=changed_by,
            reason=cancelled_reason,
            metadata={"notify_acknowledged": bool(notify_acknowledged)},
        )
        logger.info("Cancelled home visit %s by user %s", visit.id, changed_by.id)
        return visit

    @staticmethod
    async def reschedule_visit(
        db: AsyncSession,
        visit: ParentHomeVisit,
        *,
        changed_by: User,
        new_scheduled_date: date,
        new_scheduled_time: Optional[str] = None,
        duration_minutes: Optional[int] = None,
        reason: str,
    ) -> tuple[ParentHomeVisit, ParentHomeVisit]:
        current = HomeVisitStatus(visit.status)
        target = HomeVisitStatus.rescheduled
        if target not in _HOME_VISIT_TRANSITIONS.get(current, set()):
            raise InvalidHomeVisitTransitionError(current, target)

        # Create the replacement visit row first so we have its id for the
        # back-link before we flush the original's status change.
        replacement = ParentHomeVisit(
            patron_id=visit.patron_id,
            visitor_id=visit.visitor_id,
            parent_session_id=visit.parent_session_id,
            purpose=visit.purpose,
            status=HomeVisitStatus.scheduled.value,
            scheduled_date=new_scheduled_date,
            scheduled_time=new_scheduled_time,
            address=visit.address,
        )
        db.add(replacement)
        await db.flush()

        # Original now points at the replacement.
        visit.status = target.value
        visit.rescheduled_to_id = replacement.id
        await db.flush()

        await HomeVisitService._record_transition(
            db,
            visit=visit,
            from_status=current,
            to_status=target,
            changed_by=changed_by,
            reason=reason,
            metadata={
                "replacement_visit_id": replacement.id,
                "new_scheduled_date": new_scheduled_date.isoformat(),
                "new_scheduled_time": new_scheduled_time,
                "duration_minutes": duration_minutes,
            },
        )
        # Initial-state row for the replacement so the new visit's history
        # is non-empty from the start; from_status=None means "created".
        await HomeVisitService._record_transition(
            db,
            visit=replacement,
            from_status=None,
            to_status=HomeVisitStatus.scheduled,
            changed_by=changed_by,
            reason=f"Rescheduled from visit {visit.id}",
            metadata={"source_visit_id": visit.id},
        )
        logger.info(
            "Rescheduled home visit %s -> new visit %s by user %s",
            visit.id,
            replacement.id,
            changed_by.id,
        )
        return visit, replacement

    @staticmethod
    async def get_history(
        db: AsyncSession,
        visit_id: int,
        *,
        limit: int = 50,
    ) -> tuple[list[HomeVisitStatusHistory], int]:
        # selectinload the changed_by user so the response serializer
        # doesn't hit the MissingGreenlet trap when computing a display
        # name (memory: feedback_l30_async_property_landmine).
        query = (
            select(HomeVisitStatusHistory)
            .options(selectinload(HomeVisitStatusHistory.changed_by))
            .where(HomeVisitStatusHistory.visit_id == visit_id)
            .order_by(HomeVisitStatusHistory.changed_at.desc())
            .limit(limit)
        )
        result = await db.execute(query)
        rows = list(result.scalars().all())

        count_query = (
            select(func.count(HomeVisitStatusHistory.id))
            .where(HomeVisitStatusHistory.visit_id == visit_id)
        )
        total = (await db.execute(count_query)).scalar() or 0
        return rows, total

    @staticmethod
    async def check_conflicts(
        db: AsyncSession,
        *,
        visitor_id: int,
        scheduled_date: date,
        exclude_visit_id: Optional[int] = None,
    ) -> list[ParentHomeVisit]:
        query = (
            select(ParentHomeVisit)
            .options(selectinload(ParentHomeVisit.patron))
            .where(
                ParentHomeVisit.visitor_id == visitor_id,
                ParentHomeVisit.scheduled_date == scheduled_date,
                ParentHomeVisit.status.notin_(
                    [
                        HomeVisitStatus.cancelled.value,
                        HomeVisitStatus.rescheduled.value,
                    ]
                ),
            )
            .order_by(ParentHomeVisit.scheduled_time.asc().nullsfirst())
        )
        if exclude_visit_id is not None:
            query = query.where(ParentHomeVisit.id != exclude_visit_id)
        result = await db.execute(query)
        return list(result.scalars().all())


# Module-level constants for the lone-worker safety mechanic. Kept local
# to this service rather than promoted to settings: tuning these requires
# code review + library policy alignment, not a runtime toggle.
SAFETY_GRACE_PERIOD_MINUTES = 15
SAFETY_DEFAULT_DURATION_MINUTES = 60


class HomeVisitSafetyService:

    @staticmethod
    async def mark_safe_arrival(
        db: AsyncSession,
        visit: ParentHomeVisit,
        *,
        visit_duration_minutes: int,
        now: Optional[datetime] = None,
    ) -> ParentHomeVisit:
        from datetime import timedelta
        if now is None:
            now = datetime.now(timezone.utc)
        visit.safety_checkin_at = now
        visit.safety_checkout_due_at = now + timedelta(
            minutes=visit_duration_minutes + SAFETY_GRACE_PERIOD_MINUTES
        )
        # A re-checkin (e.g. staff hit the button twice or visit ran long
        # and they extended) clears the prior overdue flag so the scanner
        # can re-flag if the new deadline passes. Without this, a single
        # overdue flag would suppress future alerts permanently.
        visit.safety_overdue_flagged_at = None
        # If staff hadn't started the visit yet, treat checkin as start.
        if visit.actual_start is None:
            visit.actual_start = now
        await db.flush()
        await db.refresh(visit)
        logger.info(
            "Safety check-in recorded for home visit %s (due %s)",
            visit.id,
            visit.safety_checkout_due_at.isoformat(),
        )
        return visit

    @staticmethod
    async def mark_safe_departure(
        db: AsyncSession,
        visit: ParentHomeVisit,
        *,
        now: Optional[datetime] = None,
    ) -> ParentHomeVisit:
        if now is None:
            now = datetime.now(timezone.utc)
        visit.safety_checkout_at = now
        if visit.actual_end is None:
            visit.actual_end = now
        await db.flush()
        await db.refresh(visit)
        logger.info("Safety check-out recorded for home visit %s", visit.id)
        return visit

    @staticmethod
    async def list_overdue(
        db: AsyncSession,
        *,
        include_flagged: bool = True,
        now: Optional[datetime] = None,
    ) -> list[ParentHomeVisit]:
        if now is None:
            now = datetime.now(timezone.utc)
        query = (
            select(ParentHomeVisit)
            .where(
                and_(
                    ParentHomeVisit.safety_checkin_at.isnot(None),
                    ParentHomeVisit.safety_checkout_at.is_(None),
                    ParentHomeVisit.safety_checkout_due_at.isnot(None),
                    ParentHomeVisit.safety_checkout_due_at < now,
                )
            )
            .options(
                selectinload(ParentHomeVisit.safety_buddy),
                selectinload(ParentHomeVisit.visitor),
            )
            .order_by(ParentHomeVisit.safety_checkout_due_at.asc())
        )
        if not include_flagged:
            query = query.where(ParentHomeVisit.safety_overdue_flagged_at.is_(None))
        result = await db.execute(query)
        return list(result.scalars().all())

    @staticmethod
    async def flag_overdue(
        db: AsyncSession,
        visit: ParentHomeVisit,
        *,
        now: Optional[datetime] = None,
    ) -> ParentHomeVisit:
        if now is None:
            now = datetime.now(timezone.utc)
        visit.safety_overdue_flagged_at = now
        await db.flush()
        await db.refresh(visit)
        return visit

# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Parent Onboarding — ConnectionGroupService.

Pure move from services/parent_onboarding/_legacy.py.  No behaviour change.
"""
from app.core.logging import get_logger
from datetime import date, datetime, timezone
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ...models.parent_onboarding import (
    GroupMemberStatus,
    MeetingFrequency,
    ParentConnectionGroup,
    ParentConnectionGroupMeeting,
    ParentConnectionGroupMember,
)

logger = get_logger(__name__)

class ConnectionGroupService:

    @staticmethod
    async def create_group(
        db: AsyncSession, data: dict
    ) -> ParentConnectionGroup:
        group = ParentConnectionGroup(**data)
        db.add(group)
        await db.flush()
        await db.refresh(group)
        return group

    @staticmethod
    async def get_group(db: AsyncSession, group_id: int) -> Optional[ParentConnectionGroup]:
        result = await db.execute(
            select(ParentConnectionGroup)
            .options(selectinload(ParentConnectionGroup.members))
            .where(ParentConnectionGroup.id == group_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def list_groups(
        db: AsyncSession,
        *,
        branch_id: Optional[int] = None,
        group_type: Optional[str] = None,
        active_only: bool = True,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[ParentConnectionGroup], int]:
        query = select(ParentConnectionGroup).options(selectinload(ParentConnectionGroup.members))
        count_query = select(func.count(ParentConnectionGroup.id))

        if branch_id:
            query = query.where(ParentConnectionGroup.branch_id == branch_id)
            count_query = count_query.where(ParentConnectionGroup.branch_id == branch_id)
        if group_type:
            query = query.where(ParentConnectionGroup.group_type == group_type)
            count_query = count_query.where(ParentConnectionGroup.group_type == group_type)
        if active_only:
            query = query.where(ParentConnectionGroup.is_active.is_(True))
            count_query = count_query.where(ParentConnectionGroup.is_active.is_(True))

        total = (await db.execute(count_query)).scalar() or 0
        query = query.order_by(ParentConnectionGroup.name).limit(limit).offset(offset)
        result = await db.execute(query)
        return list(result.unique().scalars().all()), total

    @staticmethod
    async def staff_enroll(
        db: AsyncSession,
        *,
        group_id: int,
        patron_id: int,
        enrolled_by_id: int,
        consent_note: Optional[str] = None,
        capacity_override: bool = False,
        override_justification: Optional[str] = None,
        caller_is_facilitator_or_admin: bool = False,
    ) -> dict:
        from ...models.user import User as _User  # local import; user model

        group = await ConnectionGroupService.get_group(db, group_id)
        if not group:
            raise ValueError("Connection group not found")
        if not group.is_active:
            raise ValueError("Connection group is not active")

        # Spec interaction rule: capacity override is disabled for confidential
        # groups. Override exists for capacity, not for skipping consent.
        if getattr(group, "confidential", False) and capacity_override:
            raise ValueError(
                "Capacity override is not allowed for confidential groups"
            )

        # Already-an-active-member check.
        existing_q = await db.execute(
            select(ParentConnectionGroupMember).where(
                ParentConnectionGroupMember.group_id == group_id,
                ParentConnectionGroupMember.patron_id == patron_id,
                ParentConnectionGroupMember.status == GroupMemberStatus.active,
            )
        )
        if existing_q.scalar_one_or_none() is not None:
            raise ValueError("Patron is already an active member of this group")

        # Patron must exist + not be deactivated.
        patron_q = await db.execute(select(_User).where(_User.id == patron_id))
        patron = patron_q.scalar_one_or_none()
        if patron is None:
            raise ValueError("Patron not found")
        if getattr(patron, "is_active", True) is False:
            raise ValueError("Patron account is deactivated")

        # Capacity check. group.members was loaded by get_group via selectinload.
        active_count = sum(
            1 for m in (group.members or []) if m.status == GroupMemberStatus.active
        )
        is_full = active_count >= (group.max_members or 0)
        is_confidential = bool(getattr(group, "confidential", False))

        decided_at_val = None
        decided_by_id_val = None

        if is_confidential and not caller_is_facilitator_or_admin:
            # General staff acting on a confidential group: pending approval.
            status_val = GroupMemberStatus.pending_approval
            capacity_override_eff = False
        elif is_full and not capacity_override:
            status_val = GroupMemberStatus.waitlisted
            capacity_override_eff = False
        elif is_full and capacity_override:
            status_val = GroupMemberStatus.active
            capacity_override_eff = True
        else:
            status_val = GroupMemberStatus.active
            capacity_override_eff = False

        # Confidential + caller-can-approve → auto-decide.
        if is_confidential and caller_is_facilitator_or_admin and status_val == GroupMemberStatus.active:
            decided_at_val = datetime.now(timezone.utc)
            decided_by_id_val = enrolled_by_id

        member = ParentConnectionGroupMember(
            group_id=group_id,
            patron_id=patron_id,
            joined_date=date.today(),
            status=status_val,
            enrolled_by_id=enrolled_by_id,
            enrollment_consent_note=consent_note,
            capacity_override=capacity_override_eff,
            override_justification=override_justification if capacity_override_eff else None,
            decided_by_id=decided_by_id_val,
            decided_at=decided_at_val,
        )
        db.add(member)
        await db.flush()
        await db.refresh(member)

        # Enroller name lookup (we already know patron's name from above).
        enroller_q = await db.execute(
            select(_User).where(_User.id == enrolled_by_id)
        )
        enroller = enroller_q.scalar_one_or_none()

        def _name(u) -> Optional[str]:
            if u is None:
                return None
            first = getattr(u, "first_name", None) or ""
            last = getattr(u, "last_name", None) or ""
            full = (first + " " + last).strip()
            return full or getattr(u, "email", None)

        logger.info(
            "Staff %s enrolled patron %s in connection group %s (status=%s, override=%s)",
            enrolled_by_id, patron_id, group_id, status_val, capacity_override_eff,
        )
        return {
            "id": member.id,
            "group_id": member.group_id,
            "patron_id": member.patron_id,
            "patron_name": _name(patron),
            "status": member.status,
            "joined_date": member.joined_date,
            "enrolled_by_id": member.enrolled_by_id,
            "enrolled_by_name": _name(enroller),
            "consent_note_recorded": bool(consent_note),
            "capacity_overridden": capacity_override_eff,
        }

    @staticmethod
    async def staff_remove(
        db: AsyncSession,
        *,
        group_id: int,
        patron_id: int,
        removed_by_id: int,
        reason: str,
    ) -> ParentConnectionGroupMember:
        result = await db.execute(
            select(ParentConnectionGroupMember).where(
                ParentConnectionGroupMember.group_id == group_id,
                ParentConnectionGroupMember.patron_id == patron_id,
            )
        )
        member = result.scalar_one_or_none()
        if member is None:
            raise ValueError("Member not found")
        member.status = GroupMemberStatus.inactive
        member.left_date = date.today()
        member.removed_by_id = removed_by_id
        member.removal_reason = reason
        await db.flush()
        await db.refresh(member)
        logger.info(
            "Staff %s removed patron %s from connection group %s (reason=%s)",
            removed_by_id, patron_id, group_id, reason,
        )
        return member

    @staticmethod
    async def list_members(
        db: AsyncSession, group_id: int
    ) -> list[dict]:
        from ...models.user import User as _User
        q = (
            select(ParentConnectionGroupMember)
            .where(
                ParentConnectionGroupMember.group_id == group_id,
                ParentConnectionGroupMember.status.in_([
                    GroupMemberStatus.active,
                    GroupMemberStatus.waitlisted,
                ]),
            )
            .options(
                selectinload(ParentConnectionGroupMember.patron),
                selectinload(ParentConnectionGroupMember.enrolled_by),
            )
        )
        result = await db.execute(q)
        rows = list(result.scalars().all())

        def _name(u) -> Optional[str]:
            if u is None:
                return None
            first = getattr(u, "first_name", None) or ""
            last = getattr(u, "last_name", None) or ""
            full = (first + " " + last).strip()
            return full or getattr(u, "email", None)

        return [
            {
                "id": m.id,
                "group_id": m.group_id,
                "patron_id": m.patron_id,
                "patron_name": _name(m.patron),
                "status": m.status,
                "joined_date": m.joined_date,
                "left_date": m.left_date,
                "attendance_count": m.attendance_count,
                "enrolled_by_id": m.enrolled_by_id,
                "enrolled_by_name": _name(m.enrolled_by),
                "capacity_override": bool(m.capacity_override),
            }
            for m in rows
        ]

    # ------------------------------------------------------------------
    # Confidentiality + approval-gated waitlist (cg_confidential_001)
    # ------------------------------------------------------------------

    @staticmethod
    async def request_join(
        db: AsyncSession,
        *,
        group_id: int,
        patron_id: int,
        requested_by_id: int,
        request_message: Optional[str] = None,
        consent_to_share_contact: bool = False,
    ) -> dict:
        from ...models.user import User as _User

        group = await ConnectionGroupService.get_group(db, group_id)
        if not group:
            raise ValueError("Connection group not found")
        if not group.is_active:
            raise ValueError("Connection group is not active")
        if not getattr(group, "confidential", False):
            raise ValueError(
                "This group does not require approval; use the enroll endpoint."
            )

        patron_q = await db.execute(select(_User).where(_User.id == patron_id))
        patron = patron_q.scalar_one_or_none()
        if patron is None:
            raise ValueError("Patron not found")
        if getattr(patron, "is_active", True) is False:
            raise ValueError("Patron account is deactivated")

        # Already active? Don't create a duplicate request.
        for m in group.members or []:
            if m.patron_id == patron_id and m.status == GroupMemberStatus.active:
                raise ValueError("Patron is already an active member of this group")

        existing_q = await db.execute(
            select(ParentConnectionGroupMember).where(
                ParentConnectionGroupMember.group_id == group_id,
                ParentConnectionGroupMember.patron_id == patron_id,
                ParentConnectionGroupMember.status == GroupMemberStatus.pending_approval,
            )
        )
        existing = existing_q.scalar_one_or_none()
        if existing is not None:
            return {
                "id": existing.id,
                "group_id": existing.group_id,
                "patron_id": existing.patron_id,
                "status": existing.status,
                "requested_at": existing.created_at,
                "requested_by_id": existing.enrolled_by_id or requested_by_id,
                "estimated_response_window_hours": group.estimated_response_window_hours,
            }

        member = ParentConnectionGroupMember(
            group_id=group_id,
            patron_id=patron_id,
            joined_date=date.today(),
            status=GroupMemberStatus.pending_approval,
            enrolled_by_id=requested_by_id,
            request_message=request_message,
            consent_to_share_contact=consent_to_share_contact,
        )
        db.add(member)
        await db.flush()
        await db.refresh(member)
        logger.info(
            "Patron %s requested approval to join confidential group %s (req_by=%s)",
            patron_id, group_id, requested_by_id,
        )
        return {
            "id": member.id,
            "group_id": member.group_id,
            "patron_id": member.patron_id,
            "status": member.status,
            "requested_at": member.created_at,
            "requested_by_id": requested_by_id,
            "estimated_response_window_hours": group.estimated_response_window_hours,
        }

    @staticmethod
    async def list_approval_queue(
        db: AsyncSession, group_id: int
    ) -> dict:
        from ...models.user import User as _User
        from datetime import datetime as _dt, timezone as _tz

        group = await ConnectionGroupService.get_group(db, group_id)
        if group is None:
            raise ValueError("Connection group not found")
        if not getattr(group, "confidential", False):
            # Spec: approval queue only exists for confidential groups.
            raise ValueError("Approval queue not applicable for this group")

        pending_q = (
            select(ParentConnectionGroupMember)
            .where(
                ParentConnectionGroupMember.group_id == group_id,
                ParentConnectionGroupMember.status == GroupMemberStatus.pending_approval,
            )
            .options(selectinload(ParentConnectionGroupMember.patron))
            .order_by(ParentConnectionGroupMember.created_at.asc())
        )
        pending_rows = list((await db.execute(pending_q)).scalars().all())

        decided_q = (
            select(ParentConnectionGroupMember)
            .where(
                ParentConnectionGroupMember.group_id == group_id,
                ParentConnectionGroupMember.decided_at.is_not(None),
            )
            .options(
                selectinload(ParentConnectionGroupMember.patron),
                selectinload(ParentConnectionGroupMember.decided_by),
            )
            .order_by(ParentConnectionGroupMember.decided_at.desc())
            .limit(20)
        )
        decided_rows = list((await db.execute(decided_q)).scalars().all())

        def _name(u) -> Optional[str]:
            if u is None:
                return None
            first = getattr(u, "first_name", None) or ""
            last = getattr(u, "last_name", None) or ""
            full = (first + " " + last).strip()
            return full or getattr(u, "email", None)

        now = _dt.now(_tz.utc)

        def _days_pending(created_at) -> int:
            if created_at is None:
                return 0
            ca = created_at
            if ca.tzinfo is None:
                ca = ca.replace(tzinfo=_tz.utc)
            return max(0, (now - ca).days)

        pending = []
        for m in pending_rows:
            visible = bool(m.consent_to_share_contact)
            pending.append({
                "id": m.id,
                "group_id": m.group_id,
                "group_name": group.name,
                "patron_id": m.patron_id,
                "patron_name": _name(m.patron),
                "patron_contact_visible": visible,
                "patron_email": getattr(m.patron, "email", None) if visible else None,
                "patron_phone": getattr(m.patron, "phone", None) if visible else None,
                "request_message": m.request_message,
                "requested_at": m.created_at,
                "days_pending": _days_pending(m.created_at),
            })

        decision_log = [
            {
                "id": m.id,
                "patron_name": _name(m.patron),
                "decision": m.status,
                "decided_at": m.decided_at,
                "decided_by_id": m.decided_by_id,
                "decided_by_name": _name(m.decided_by),
            }
            for m in decided_rows
        ]
        return {"pending": pending, "approval_decision_log": decision_log}

    @staticmethod
    async def decide_request(
        db: AsyncSession,
        *,
        group_id: int,
        member_id: int,
        decision: str,
        decided_by_id: int,
        decision_note: Optional[str] = None,
        patron_message: Optional[str] = None,
    ) -> dict:
        group = await ConnectionGroupService.get_group(db, group_id)
        if group is None:
            raise ValueError("Connection group not found")
        if not getattr(group, "confidential", False):
            raise ValueError("Approval queue not applicable for this group")

        member_q = await db.execute(
            select(ParentConnectionGroupMember).where(
                ParentConnectionGroupMember.id == member_id,
                ParentConnectionGroupMember.group_id == group_id,
            )
        )
        member = member_q.scalar_one_or_none()
        if member is None:
            raise ValueError("Request not found")

        if member.status != GroupMemberStatus.pending_approval:
            # Idempotency: re-decide is a 409 at the route layer.
            return {
                "id": member.id,
                "group_id": member.group_id,
                "patron_id": member.patron_id,
                "status": member.status,
                "decided_at": member.decided_at,
                "decided_by_id": member.decided_by_id or decided_by_id,
                "already_decided": True,
            }

        if decision == "approve":
            # Capacity check at approval time, not request time.
            active_count = sum(
                1 for m in (group.members or [])
                if m.status == GroupMemberStatus.active and m.id != member.id
            )
            if active_count >= (group.max_members or 0):
                member.status = GroupMemberStatus.waitlisted
            else:
                member.status = GroupMemberStatus.active
        elif decision == "deny":
            member.status = GroupMemberStatus.denied
            member.left_date = date.today()
        else:
            raise ValueError("decision must be 'approve' or 'deny'")

        member.decided_by_id = decided_by_id
        member.decided_at = datetime.now(timezone.utc)
        member.decision_note = decision_note
        member.decision_patron_message = patron_message
        await db.flush()
        await db.refresh(member)
        logger.info(
            "Staff %s %s request %s on confidential group %s (final status=%s)",
            decided_by_id, decision, member_id, group_id, member.status,
        )
        return {
            "id": member.id,
            "group_id": member.group_id,
            "patron_id": member.patron_id,
            "status": member.status,
            "decided_at": member.decided_at,
            "decided_by_id": member.decided_by_id,
            "already_decided": False,
        }

    # ------------------------------------------------------------------
    # Lifecycle: archive / unarchive / meeting instances (cg_lifecycle_001).
    # ------------------------------------------------------------------
    #
    # Why these live on the same service: the methods below all reach
    # through the same group_id and share the same admin-role contract.
    # Splitting them into a separate "ConnectionGroupLifecycleService"
    # would duplicate the get_group + active-membership lookups.

    @staticmethod
    async def count_active_members(db: AsyncSession, group_id: int) -> int:
        q = select(func.count(ParentConnectionGroupMember.id)).where(
            ParentConnectionGroupMember.group_id == group_id,
            ParentConnectionGroupMember.status == GroupMemberStatus.active,
        )
        return int((await db.execute(q)).scalar() or 0)

    @staticmethod
    async def active_member_ids(db: AsyncSession, group_id: int) -> list[int]:
        q = select(ParentConnectionGroupMember.id).where(
            ParentConnectionGroupMember.group_id == group_id,
            ParentConnectionGroupMember.status == GroupMemberStatus.active,
        )
        result = await db.execute(q)
        return [int(r) for r in result.scalars().all()]

    @staticmethod
    async def archive_group(
        db: AsyncSession,
        *,
        group: ParentConnectionGroup,
        archived_by_id: int,
        archive_reason: str,
        archive_notes: Optional[str] = None,
    ) -> ParentConnectionGroup:
        group.is_active = False
        group.archived_at = datetime.now(timezone.utc)
        group.archived_by_id = archived_by_id
        group.archive_reason = archive_reason
        group.archive_notes = archive_notes
        await db.flush()
        await db.refresh(group)
        logger.info(
            "Admin %s archived connection group %s (reason=%s)",
            archived_by_id, group.id, archive_reason,
        )
        return group

    @staticmethod
    async def unarchive_group(
        db: AsyncSession,
        *,
        group: ParentConnectionGroup,
    ) -> ParentConnectionGroup:
        group.is_active = True
        group.archived_at = None
        group.archived_by_id = None
        group.archive_reason = None
        group.archive_notes = None
        await db.flush()
        await db.refresh(group)
        logger.info("Connection group %s unarchived", group.id)
        return group

    # ------- Meeting instances -------

    # Day-of-week → Python weekday() index. Matches the lowercase strings the
    # group model uses. ISO weekday would 1-index Monday; Python's
    # datetime.date.weekday() 0-indexes Monday, which matches our usage below.
    _DAY_OF_WEEK_MAP = {
        "monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3,
        "friday": 4, "saturday": 5, "sunday": 6,
    }

    @classmethod
    def _frequency_step_days(cls, frequency: Optional[str]) -> int:
        if frequency == MeetingFrequency.biweekly:
            return 14
        if frequency == MeetingFrequency.monthly:
            return 28
        return 7  # weekly default

    @classmethod
    def _next_meeting_dates(
        cls,
        *,
        from_date: date,
        day_of_week: Optional[str],
        frequency: Optional[str],
        count: int,
    ) -> list[date]:
        anchor_day = cls._DAY_OF_WEEK_MAP.get(
            (day_of_week or "").strip().lower(),
            from_date.weekday(),
        )
        # Walk forward to the first qualifying weekday.
        offset = (anchor_day - from_date.weekday()) % 7
        first = from_date.fromordinal(from_date.toordinal() + offset)

        step = cls._frequency_step_days(frequency)
        return [
            first.fromordinal(first.toordinal() + step * i)
            for i in range(count)
        ]

    @staticmethod
    async def list_meetings(
        db: AsyncSession,
        *,
        group: ParentConnectionGroup,
        materialize_count: int = 8,
        from_date: Optional[date] = None,
    ) -> list[ParentConnectionGroupMeeting]:
        from_date = from_date or date.today()

        # Read existing.
        q = (
            select(ParentConnectionGroupMeeting)
            .where(ParentConnectionGroupMeeting.group_id == group.id)
            .order_by(ParentConnectionGroupMeeting.meeting_date)
        )
        existing = list((await db.execute(q)).scalars().all())
        existing_dates = {m.meeting_date for m in existing}

        # How many UPCOMING scheduled rows exist?
        upcoming_scheduled = [
            m for m in existing
            if m.meeting_date >= from_date and m.status == "scheduled"
        ]
        needed = max(0, materialize_count - len(upcoming_scheduled))
        if needed > 0:
            # Anchor generation on whichever is later: today or the last
            # persisted upcoming meeting. Avoids materializing dates that
            # are already in the past or that conflict with persisted rows.
            anchor = from_date
            if upcoming_scheduled:
                last_date = max(m.meeting_date for m in upcoming_scheduled)
                # Step ONE frequency past the last persisted upcoming.
                step = ConnectionGroupService._frequency_step_days(group.meeting_frequency)
                anchor = last_date.fromordinal(last_date.toordinal() + step)

            candidates = ConnectionGroupService._next_meeting_dates(
                from_date=anchor,
                day_of_week=group.meeting_day_of_week,
                frequency=group.meeting_frequency,
                # Generate a few extras in case some collide with already-
                # materialized historical rows (e.g. rescheduled).
                count=needed + len(existing_dates),
            )
            fresh = []
            for d in candidates:
                if len(fresh) >= needed:
                    break
                if d in existing_dates:
                    continue
                fresh.append(d)
                existing_dates.add(d)

            for d in fresh:
                m = ParentConnectionGroupMeeting(
                    group_id=group.id,
                    meeting_date=d,
                    scheduled_time=group.meeting_time,
                    location=group.location,
                    status="scheduled",
                )
                db.add(m)
            if fresh:
                await db.flush()

            # Re-read so caller gets the canonical ordering + ids.
            existing = list((await db.execute(q)).scalars().all())

        return existing

    @staticmethod
    async def cancel_meeting(
        db: AsyncSession,
        *,
        meeting: ParentConnectionGroupMeeting,
        cancelled_by_id: int,
        reason: str,
        staff_notes: Optional[str] = None,
        patron_message: Optional[str] = None,
    ) -> ParentConnectionGroupMeeting:
        meeting.status = "cancelled"
        meeting.cancelled_at = datetime.now(timezone.utc)
        meeting.cancelled_by_id = cancelled_by_id
        meeting.cancelled_reason = reason
        if staff_notes is not None:
            meeting.staff_notes = staff_notes
        if patron_message is not None:
            meeting.patron_message = patron_message
        await db.flush()
        await db.refresh(meeting)
        logger.info(
            "Admin %s cancelled meeting %s (group=%s, reason=%s)",
            cancelled_by_id, meeting.id, meeting.group_id, reason,
        )
        return meeting

    @staticmethod
    async def reschedule_meeting(
        db: AsyncSession,
        *,
        group: ParentConnectionGroup,
        meeting: ParentConnectionGroupMeeting,
        rescheduled_by_id: int,
        new_date: date,
        new_time: Optional[str] = None,
        new_location: Optional[str] = None,
        staff_notes: Optional[str] = None,
        patron_message: Optional[str] = None,
    ) -> tuple[ParentConnectionGroupMeeting, ParentConnectionGroupMeeting]:
        new_meeting = ParentConnectionGroupMeeting(
            group_id=group.id,
            meeting_date=new_date,
            scheduled_time=new_time if new_time is not None else meeting.scheduled_time,
            location=new_location if new_location is not None else meeting.location,
            status="scheduled",
            patron_message=patron_message,
            staff_notes=staff_notes,
        )
        db.add(new_meeting)
        await db.flush()
        await db.refresh(new_meeting)

        meeting.status = "rescheduled"
        meeting.rescheduled_to_meeting_id = new_meeting.id
        # Carry the patron-facing message on the *new* row but the staff
        # notes on the *old* row (admins read history; patrons read the
        # current schedule).
        if staff_notes is not None:
            meeting.staff_notes = staff_notes
        meeting.cancelled_by_id = rescheduled_by_id  # acted-by audit
        meeting.cancelled_at = datetime.now(timezone.utc)
        await db.flush()
        await db.refresh(meeting)

        logger.info(
            "Admin %s rescheduled meeting %s (group=%s) to %s as meeting %s",
            rescheduled_by_id, meeting.id, group.id, new_date, new_meeting.id,
        )
        return meeting, new_meeting

    @staticmethod
    async def active_member_emails(
        db: AsyncSession, group_id: int
    ) -> list[tuple[int, str, str]]:
        from ...models.user import User as _User
        q = (
            select(ParentConnectionGroupMember.patron_id, _User.email, _User.first_name)
            .join(_User, _User.id == ParentConnectionGroupMember.patron_id)
            .where(
                ParentConnectionGroupMember.group_id == group_id,
                ParentConnectionGroupMember.status == GroupMemberStatus.active,
                _User.is_active.is_(True),
            )
        )
        rows = (await db.execute(q)).all()
        return [(int(pid), email or "", first or "") for (pid, email, first) in rows if email]

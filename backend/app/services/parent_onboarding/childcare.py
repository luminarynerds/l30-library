# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Parent Onboarding — ChildcareService + PickupNotAuthorized.

Extracted from _legacy.py. Zero behaviour change — pure file move.
"""
from datetime import date
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ...models.parent_onboarding import (
    ChildcareRegistration, ChildcareRegistrationStatus, ChildcareSession,
    ChildcareSessionStatus,
)


class ChildcareService:

    @staticmethod
    async def create_session(
        db: AsyncSession, data: dict
    ) -> ChildcareSession:
        session = ChildcareSession(**data)
        db.add(session)
        await db.flush()
        await db.refresh(session)
        return session

    @staticmethod
    async def get_session(db: AsyncSession, session_id: int) -> Optional[ChildcareSession]:
        result = await db.execute(
            select(ChildcareSession)
            .options(selectinload(ChildcareSession.registrations))
            .where(ChildcareSession.id == session_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def list_sessions(
        db: AsyncSession,
        *,
        branch_id: Optional[int] = None,
        from_date: Optional[date] = None,
        to_date: Optional[date] = None,
        status: Optional[ChildcareSessionStatus] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[ChildcareSession], int]:
        query = select(ChildcareSession).options(selectinload(ChildcareSession.registrations))
        count_query = select(func.count(ChildcareSession.id))

        if branch_id:
            query = query.where(ChildcareSession.branch_id == branch_id)
            count_query = count_query.where(ChildcareSession.branch_id == branch_id)
        if from_date:
            query = query.where(ChildcareSession.date >= from_date)
            count_query = count_query.where(ChildcareSession.date >= from_date)
        if to_date:
            query = query.where(ChildcareSession.date <= to_date)
            count_query = count_query.where(ChildcareSession.date <= to_date)
        if status:
            query = query.where(ChildcareSession.status == status)
            count_query = count_query.where(ChildcareSession.status == status)

        total = (await db.execute(count_query)).scalar() or 0
        query = query.order_by(ChildcareSession.date, ChildcareSession.start_time).limit(limit).offset(offset)
        result = await db.execute(query)
        return list(result.unique().scalars().all()), total

    @staticmethod
    async def update_session(
        db: AsyncSession, session_id: int, updates: dict
    ) -> ChildcareSession:
        session = await ChildcareService.get_session(db, session_id)
        if not session:
            raise ValueError("Childcare session not found")

        # Capacity floor: an admin cannot under-cut their already-registered
        # families. Status transitions to ``cancelled`` are allowed even
        # with active registrations -- that's the librarian's call to make.
        if "max_children" in updates and updates["max_children"] is not None:
            active_count = sum(
                1 for r in (session.registrations or [])
                if r.status in (
                    ChildcareRegistrationStatus.registered,
                    ChildcareRegistrationStatus.checked_in,
                )
            )
            if updates["max_children"] < active_count:
                raise ValueError(
                    f"max_children below active count "
                    f"({updates['max_children']} < {active_count})"
                )

        for key, value in updates.items():
            setattr(session, key, value)

        await db.flush()
        await db.refresh(session)
        return session

    @staticmethod
    async def register_child(
        db: AsyncSession, session_id: int, patron_id: int, data: dict
    ) -> ChildcareRegistration:
        # Check capacity
        session = await ChildcareService.get_session(db, session_id)
        if not session:
            raise ValueError("Childcare session not found")
        if session.status != ChildcareSessionStatus.available:
            raise ValueError("Childcare session is not available")

        active_count = sum(
            1 for r in session.registrations
            if r.status in (ChildcareRegistrationStatus.registered, ChildcareRegistrationStatus.checked_in)
        )
        if active_count >= session.max_children:
            raise ValueError("Childcare session is full")

        registration = ChildcareRegistration(
            session_id=session_id, patron_id=patron_id, **data
        )
        db.add(registration)
        await db.flush()
        await db.refresh(registration)
        return registration

    @staticmethod
    def validate_pickup_authorization(
        registration: ChildcareRegistration,
        *,
        picked_up_by_name: str,
        picked_up_by_phone: str,
        staff_override_reason: Optional[str],
    ) -> Optional[dict]:
        authorized = list(registration.authorized_pickup or [])
        has_list = len(authorized) > 0

        # Try to match an entry: case-insensitive name + exact digits-only
        # phone so "(555) 222-3333" matches "5552223333".
        def _digits(s: str) -> str:
            return "".join(ch for ch in (s or "") if ch.isdigit())

        target_name = (picked_up_by_name or "").strip().lower()
        target_phone = _digits(picked_up_by_phone)

        for entry in authorized:
            if not isinstance(entry, dict):
                continue
            entry_name = str(entry.get("name", "")).strip().lower()
            entry_phone = _digits(str(entry.get("phone", "")))
            if entry_name == target_name and entry_phone == target_phone:
                return entry

        # No match. Staff override path?
        if staff_override_reason and staff_override_reason.strip():
            return None

        # Reject. Surface who IS authorized so staff sees the allowlist.
        if has_list:
            names = ", ".join(
                str(e.get("name", "?")) for e in authorized if isinstance(e, dict)
            )
            detail = (
                f"'{picked_up_by_name}' is not on the authorized pickup list. "
                f"Authorized adults: {names}. Provide staff_override_reason "
                f"to override."
            )
        else:
            detail = (
                "This registration has no authorized pickup list on file. "
                "Provide staff_override_reason to check the child out."
            )
        raise PickupNotAuthorized(detail=detail, has_authorized_list=has_list)


class PickupNotAuthorized(Exception):

    def __init__(self, detail: str, *, has_authorized_list: bool) -> None:
        super().__init__(detail)
        self.detail = detail
        self.has_authorized_list = has_authorized_list

# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
from __future__ import annotations
from datetime import date, timedelta
from decimal import Decimal
from typing import Optional

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.staff_pay_rate import StaffPayRate
from ..models.user import User, UserRole

# Roles that can clock in/out and so can carry an hourly rate. Mirrors
# EMPLOYEE_ROLES in StaffTimesheetEditorPage.tsx.
CLOCK_CAPABLE_ROLES = (
    UserRole.STAFF,
    UserRole.ADMIN,
    UserRole.DIRECTOR,
    UserRole.SUPER_ADMIN,
    UserRole.BOOKMOBILE,
)


class PayRateService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_rate_for_date(self, staff_id: int, target_date: date) -> Optional[Decimal]:
        result = await self.db.execute(
            select(StaffPayRate.hourly_rate)
            .where(and_(
                StaffPayRate.staff_id == staff_id,
                StaffPayRate.effective_from <= target_date,
                (StaffPayRate.effective_to.is_(None)) | (StaffPayRate.effective_to >= target_date),
            ))
            .order_by(StaffPayRate.effective_from.desc())
            .limit(1)
        )
        rate = result.scalar_one_or_none()
        return Decimal(rate) if rate is not None else None

    async def set_rate(
        self, staff_id: int, hourly_rate: Decimal, effective_from: date,
        notes: Optional[str], set_by_id: int,
    ) -> StaffPayRate:
        if hourly_rate <= 0:
            raise ValueError("hourly_rate must be > 0")

        open_q = await self.db.execute(
            select(StaffPayRate).where(and_(
                StaffPayRate.staff_id == staff_id,
                StaffPayRate.effective_to.is_(None),
            ))
        )
        for prior in open_q.scalars().all():
            prior.effective_to = effective_from - timedelta(days=1)

        row = StaffPayRate(
            staff_id=staff_id,
            hourly_rate=hourly_rate,
            effective_from=effective_from,
            effective_to=None,
            notes=notes,
            created_by_id=set_by_id,
        )
        self.db.add(row)
        await self.db.flush()
        return row

    async def list_history(self, staff_id: int) -> list[StaffPayRate]:
        result = await self.db.execute(
            select(StaffPayRate)
            .where(StaffPayRate.staff_id == staff_id)
            .order_by(StaffPayRate.effective_from.desc())
        )
        return list(result.scalars().all())

    async def list_current(self) -> list[tuple[User, Optional[StaffPayRate]]]:
        users_q = await self.db.execute(
            select(User)
            .where(and_(
                User.is_active.is_(True),
                User.role.in_(CLOCK_CAPABLE_ROLES),
            ))
            .order_by(User.first_name)
        )
        users = list(users_q.scalars().all())

        today = date.today()
        rates_q = await self.db.execute(
            select(StaffPayRate).where(and_(
                StaffPayRate.staff_id.in_([u.id for u in users]),
                StaffPayRate.effective_from <= today,
                (StaffPayRate.effective_to.is_(None)) | (StaffPayRate.effective_to >= today),
            ))
        )
        by_staff = {r.staff_id: r for r in rates_q.scalars().all()}
        return [(u, by_staff.get(u.id)) for u in users]

# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import List

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.learning import Enrollment
from ..models.onboarding import StaffOnboarding
from ..models.user import User
from ..schemas.learning import TeamMemberProgress


async def is_report_of(
    db: AsyncSession, *, manager_id: int, target_user_id: int
) -> bool:
    if manager_id == target_user_id:
        # A manager cannot self-assign via the manager workflow — they have
        # the regular self-enroll route for that.
        return False

    stmt = (
        select(StaffOnboarding.id)
        .where(StaffOnboarding.user_id == target_user_id)
        .where(StaffOnboarding.manager_id == manager_id)
        .limit(1)
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none() is not None


async def get_team_progress(
    db: AsyncSession, manager_id: int
) -> List[TeamMemberProgress]:
    now = datetime.now(timezone.utc)
    soon = now + timedelta(days=7)

    completed_pred = Enrollment.completed_at.isnot(None)
    open_pred = Enrollment.completed_at.is_(None)
    overdue_pred = and_(
        Enrollment.due_at.isnot(None),
        Enrollment.due_at < now,
        open_pred,
    )
    due_soon_pred = and_(
        Enrollment.due_at.isnot(None),
        Enrollment.due_at >= now,
        Enrollment.due_at <= soon,
        open_pred,
    )

    stmt = (
        select(
            User.id.label("user_id"),
            User.first_name,
            User.last_name,
            User.email,
            func.count(Enrollment.id).label("courses_total"),
            func.count(Enrollment.id).filter(completed_pred).label("courses_completed"),
            func.count(Enrollment.id).filter(overdue_pred).label("overdue_count"),
            func.count(Enrollment.id).filter(due_soon_pred).label("due_soon_count"),
        )
        .select_from(StaffOnboarding)
        .join(User, User.id == StaffOnboarding.user_id)
        .outerjoin(Enrollment, Enrollment.user_id == User.id)
        .where(StaffOnboarding.manager_id == manager_id)
        .group_by(User.id, User.first_name, User.last_name, User.email)
        .order_by(User.first_name, User.last_name)
    )

    result = await db.execute(stmt)
    rows = result.all()

    out: List[TeamMemberProgress] = []
    for row in rows:
        total = int(row.courses_total or 0)
        completed = int(row.courses_completed or 0)
        completion_rate = (completed / total * 100.0) if total > 0 else 0.0

        # Resolve display name: "First Last" if both are set, else email fallback.
        first = (row.first_name or "").strip()
        last = (row.last_name or "").strip()
        full = f"{first} {last}".strip()
        name = full if full else (row.email or "")

        out.append(
            TeamMemberProgress(
                user_id=row.user_id,
                name=name,
                email=row.email or "",
                courses_total=total,
                courses_completed=completed,
                overdue_count=int(row.overdue_count or 0),
                due_soon_count=int(row.due_soon_count or 0),
                completion_rate=round(completion_rate, 1),
            )
        )

    return out

# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User, UserRole
from app.models.multi_branch import SystemSettings, LibrarySystem


async def is_setup_required(db: AsyncSession) -> bool:
    result = await db.execute(
        select(func.count()).select_from(User).where(
            User.role.in_([UserRole.SUPER_ADMIN, UserRole.ADMIN])
        )
    )
    return result.scalar_one() == 0


async def is_demo_mode(db: AsyncSession) -> bool:
    result = await db.execute(
        select(SystemSettings.setup_complete).order_by(SystemSettings.id.desc()).limit(1)
    )
    row = result.scalar_one_or_none()
    return row is False


async def is_setup_complete(db: AsyncSession) -> bool:
    """Return True if the setup wizard has been marked complete."""
    result = await db.execute(
        select(SystemSettings.setup_complete).order_by(SystemSettings.id.desc()).limit(1)
    )
    row = result.scalar_one_or_none()
    return row is True


async def get_default_library_system_id(db: AsyncSession) -> int | None:
    """Return the id of the first (and normally only) LibrarySystem row, or None."""
    return await db.scalar(select(LibrarySystem.id).order_by(LibrarySystem.id).limit(1))

# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Parent Onboarding — ResourceGuideService (Component 3).

Pure move from _legacy.py; no behaviour change.
"""
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ...models.parent_onboarding import (
    ParentResourceGuideFlag, ParentResourceGuideItem, ParentResourceGuideSection,
    ResourceGuideFlagReason, ResourceGuideFlagResolution, ResourceGuideFlagStatus,
)
from ...models.user import User


class ResourceGuideService:

    @staticmethod
    async def list_sections(
        db: AsyncSession,
        *,
        branch_id: Optional[int] = None,
        active_only: bool = True,
    ) -> list[ParentResourceGuideSection]:
        query = select(ParentResourceGuideSection).options(
            selectinload(ParentResourceGuideSection.items).selectinload(
                ParentResourceGuideItem.verified_by
            ),
            selectinload(ParentResourceGuideSection.items).selectinload(
                ParentResourceGuideItem.flags
            ),
        )

        if active_only:
            query = query.where(ParentResourceGuideSection.is_active.is_(True))

        if branch_id is not None:
            query = query.where(
                (ParentResourceGuideSection.branch_id.is_(None)) |
                (ParentResourceGuideSection.branch_id == branch_id)
            )

        query = query.order_by(ParentResourceGuideSection.display_order)
        result = await db.execute(query)
        return list(result.unique().scalars().all())

    @staticmethod
    async def create_section(
        db: AsyncSession, data: dict
    ) -> ParentResourceGuideSection:
        section = ParentResourceGuideSection(**data)
        db.add(section)
        await db.flush()
        await db.refresh(section)
        return section

    @staticmethod
    async def create_item(
        db: AsyncSession, section_id: int, data: dict
    ) -> ParentResourceGuideItem:
        item = ParentResourceGuideItem(section_id=section_id, **data)
        db.add(item)
        await db.flush()
        await db.refresh(item)
        return item

    @staticmethod
    async def get_item(
        db: AsyncSession, item_id: int
    ) -> Optional[ParentResourceGuideItem]:
        query = (
            select(ParentResourceGuideItem)
            .options(
                selectinload(ParentResourceGuideItem.verified_by),
                selectinload(ParentResourceGuideItem.flags),
            )
            .where(ParentResourceGuideItem.id == item_id)
        )
        result = await db.execute(query)
        return result.scalar_one_or_none()

    @staticmethod
    async def verify_item(
        db: AsyncSession,
        item_id: int,
        user: User,
    ) -> Optional[ParentResourceGuideItem]:
        item = await ResourceGuideService.get_item(db, item_id)
        if not item:
            return None

        now = datetime.now(timezone.utc)
        item.last_verified_at = now
        item.verified_by_id = user.id
        item.verified_by = user

        for flag in item.flags:
            if flag.status == ResourceGuideFlagStatus.open.value:
                flag.status = ResourceGuideFlagStatus.resolved.value
                flag.resolution = ResourceGuideFlagResolution.verified_current.value
                flag.resolved_by_id = user.id
                flag.resolved_at = now

        await db.flush()
        return await ResourceGuideService.get_item(db, item_id)

    @staticmethod
    async def flag_item(
        db: AsyncSession,
        item_id: int,
        flagged_by: User,
        reason_code: ResourceGuideFlagReason,
        comment: Optional[str] = None,
    ) -> Optional[ParentResourceGuideFlag]:
        item_exists = await db.execute(
            select(ParentResourceGuideItem.id).where(
                ParentResourceGuideItem.id == item_id
            )
        )
        if item_exists.scalar_one_or_none() is None:
            return None

        flag = ParentResourceGuideFlag(
            item_id=item_id,
            flagged_by_id=flagged_by.id,
            reason_code=reason_code.value,
            comment=comment,
            status=ResourceGuideFlagStatus.open.value,
        )
        db.add(flag)
        await db.flush()
        await db.refresh(flag)
        return flag

    @staticmethod
    async def list_flags(
        db: AsyncSession,
        *,
        status: Optional[ResourceGuideFlagStatus] = None,
    ) -> list[ParentResourceGuideFlag]:
        query = (
            select(ParentResourceGuideFlag)
            .options(
                selectinload(ParentResourceGuideFlag.item),
                selectinload(ParentResourceGuideFlag.flagged_by),
                selectinload(ParentResourceGuideFlag.resolved_by),
            )
            .order_by(ParentResourceGuideFlag.created_at.asc())
        )
        if status is not None:
            query = query.where(ParentResourceGuideFlag.status == status.value)
        result = await db.execute(query)
        return list(result.scalars().all())

    @staticmethod
    async def resolve_flag(
        db: AsyncSession,
        flag_id: int,
        user: User,
        new_status: ResourceGuideFlagStatus,
        resolution: Optional[ResourceGuideFlagResolution] = None,
        resolution_notes: Optional[str] = None,
    ) -> Optional[ParentResourceGuideFlag]:
        result = await db.execute(
            select(ParentResourceGuideFlag)
            .options(
                selectinload(ParentResourceGuideFlag.item),
                selectinload(ParentResourceGuideFlag.flagged_by),
                selectinload(ParentResourceGuideFlag.resolved_by),
            )
            .where(ParentResourceGuideFlag.id == flag_id)
        )
        flag = result.scalar_one_or_none()
        if not flag:
            return None

        flag.status = new_status.value
        if new_status in (
            ResourceGuideFlagStatus.resolved,
            ResourceGuideFlagStatus.dismissed,
        ):
            flag.resolved_by_id = user.id
            flag.resolved_at = datetime.now(timezone.utc)
            if resolution is not None:
                flag.resolution = resolution.value
            if resolution_notes is not None:
                flag.resolution_notes = resolution_notes
        else:
            flag.resolved_by_id = None
            flag.resolved_at = None
            flag.resolution = None

        await db.flush()
        await db.refresh(flag)
        return flag

    @staticmethod
    def is_item_stale(
        item: ParentResourceGuideItem, stale_after_months: int
    ) -> bool:
        if item.last_verified_at is None:
            return True
        now = datetime.now(timezone.utc)
        last = item.last_verified_at
        if last.tzinfo is None:
            last = last.replace(tzinfo=timezone.utc)
        return (now - last).days > stale_after_months * 30

    @staticmethod
    def count_open_flags(item: ParentResourceGuideItem) -> int:
        return sum(
            1 for f in item.flags if f.status == ResourceGuideFlagStatus.open.value
        )
